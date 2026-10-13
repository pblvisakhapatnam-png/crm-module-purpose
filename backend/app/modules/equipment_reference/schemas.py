"""Equipment Reference request and response shapes.

The structure (classes, types, capabilities) changes only by migration. Models, machines, the import and
the Fleet Admin's corrections (ERT-1), and the detachable kit held for crane models (ERT-2), are below it. Unknown request fields are refused with 422
throughout; a capability's unit is never sent - it is the capability's, fixed by the structure.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.modules.equipment_reference.contract import (
    MAKER_MAX_LENGTH,
    MAKER_PART_NUMBER_MAX_LENGTH,
    MAX_KIT_COUNT,
    MODEL_NAME_MAX_LENGTH,
    REASON_MAX_LENGTH,
    SERIAL_NUMBER_MAX_LENGTH,
    TEXT_VALUE_MAX_LENGTH,
)

# The largest value the integer columns hold: a nonsense number is refused with a 422, not a 500.
_WHOLE = {"ge": 1, "le": 2_147_483_647}


class EquipmentTaxonomyVersionResponse(BaseModel):
    version_number: int
    version_label: str
    source_note: str
    loaded_at: datetime
    # How many levels a machine's fitted parts may nest to under this version: the machine is level 1
    # (structure version 3, ERT-2; owner, Q9).
    component_depth: int


class EquipmentUnitResponse(BaseModel):
    unit_code: str
    unit_label: str
    unit_symbol: str
    whole_numbers_only: bool


class EquipmentTypeResponse(BaseModel):
    type_code: str
    type_label: str
    display_order: int
    introduced_in_version: int
    retired_in_version: int | None = None
    is_active: bool


class EquipmentClassCapabilityResponse(BaseModel):
    """A capability as it applies to one class. `is_key` marks the one planners compare first."""

    capability_code: str
    capability_label: str
    unit_code: str | None = None
    unit_symbol: str | None = None
    whole_numbers_only: bool
    value_kind_code: str
    allowed_values: list[str] | None = None
    is_key: bool
    display_order: int
    is_active: bool


class EquipmentClassResponse(BaseModel):
    class_code: str
    class_label: str
    # MACHINE, or PART for a class of parts (a crane's carrier; a kind of kit). Structure version 2.
    class_kind_code: str
    # SINGLE: each piece is a record of its own; COUNTED: a record holds a counted set (ERT-2, Q3).
    tracking_code: str
    # For a part class, the classes it may be fitted to by a dated link - a machine class, or a part class
    # within the depth setting; empty for a machine class.
    fits_class_codes: list[str]
    # For a kind of kit, the machine classes it is kit for: held for the models it fits, never linked
    # (ERT-2).
    kit_for_class_codes: list[str]
    display_order: int
    # The business lines that deploy this class to customers; empty when neither does.
    business_line_codes: list[str]
    introduced_in_version: int
    retired_in_version: int | None = None
    is_active: bool
    # Every type and capability, retired ones included and marked, so anything saved with them still reads.
    types: list[EquipmentTypeResponse]
    capabilities: list[EquipmentClassCapabilityResponse]


class EquipmentCapabilityResponse(BaseModel):
    capability_code: str
    capability_label: str
    unit_code: str | None = None
    value_kind_code: str
    allowed_values: list[str] | None = None
    introduced_in_version: int
    retired_in_version: int | None = None
    is_active: bool


class EquipmentTermAliasResponse(BaseModel):
    term: str
    normalized_term: str
    source_code: str
    class_code: str
    type_code: str | None = None
    is_active: bool


class EquipmentStructureResponse(BaseModel):
    """The whole structure as it stands: the current version, every version loaded, the units, the
    classes with their types and capabilities, every capability, and the aliases."""

    taxonomy_version: int
    # The depth setting in force: the current version's (owner, Q9).
    component_depth: int
    versions: list[EquipmentTaxonomyVersionResponse]
    units: list[EquipmentUnitResponse]
    classes: list[EquipmentClassResponse]
    capabilities: list[EquipmentCapabilityResponse]
    aliases: list[EquipmentTermAliasResponse]


# --- ERT-1: requests ----------------------------------------------------------------------------------


class _Request(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CapabilityValueInput(_Request):
    """A measured value in the capability's own unit, or the value of a capability with a fixed list -
    never both, and never a unit."""

    capability_code: str = Field(min_length=1, max_length=50)
    value: Decimal | None = Field(default=None, gt=0, max_digits=12, decimal_places=3, allow_inf_nan=False)
    choice_value: str | None = Field(default=None, max_length=50)


class EquipmentModelFields(_Request):
    maker: str = Field(max_length=MAKER_MAX_LENGTH)
    model_name: str = Field(max_length=MODEL_NAME_MAX_LENGTH)
    class_code: str = Field(min_length=1, max_length=50)
    # Blank: the model says nothing about the type within its class.
    type_code: str | None = Field(default=None, max_length=50)
    capabilities: list[CapabilityValueInput] = Field(default_factory=list, max_length=50)
    # The maker's own number for this kind of piece (owner, Q13). Blank: none recorded.
    maker_part_number: str | None = Field(default=None, max_length=MAKER_PART_NUMBER_MAX_LENGTH)
    # A kit model's crane models, one or more (owner, Q12); refused on any other model.
    fits_model_public_ids: list[UUID] = Field(default_factory=list, max_length=100)


class EquipmentModelCreate(EquipmentModelFields):
    """`create_request_key` is the form's own UUID: sending the same request twice records one model, not two, and
    the key with any other request is refused."""

    create_request_key: UUID


class EquipmentModelUpdate(EquipmentModelFields):
    """A whole replacement, guarded by the version the Fleet Admin read. A retired model keeps its machines
    but cannot be newly mapped."""

    is_retired: bool = False
    expected_model_version: int = Field(**_WHOLE)


class ModelMappingInput(_Request):
    """Map a Plum model name to a model, or, with no model, remove its mapping."""

    source_name: str = Field(min_length=1, max_length=TEXT_VALUE_MAX_LENGTH)
    model_public_id: UUID | None = None


class _AssetWrite(_Request):
    expected_asset_version: int = Field(**_WHOLE)


class MachineDetailsInput(_AssetWrite):
    """Facts Plum does not hold, entered on the platform (design section 5A). Blank clears one.

    For a piece of kit only (ERT-2), and left out to keep what it is: `quantity` raises a counted set's count
    (a count recorded too low - a set shrinks only by retiring pieces, with the reason), and
    `model_public_id` names another model of the same kind."""

    serial_number: str | None = Field(default=None, max_length=SERIAL_NUMBER_MAX_LENGTH)
    year_of_manufacture: int | None = Field(default=None, ge=1900, le=2200)
    quantity: int | None = Field(default=None, **_WHOLE)
    model_public_id: UUID | None = None


class MachineOwnCapabilityInput(CapabilityValueInput):
    reason: str = Field(max_length=REASON_MAX_LENGTH)


class MachineCapabilitiesInput(_AssetWrite):
    """The Fleet Admin's own values for one machine, as a whole: a capability left out takes its model's
    rating again."""

    capabilities: list[MachineOwnCapabilityInput] = Field(default_factory=list, max_length=50)


class MachineCorrectionInput(_AssetWrite):
    """Correct one field of one machine. The Plum value it replaces is the one the platform holds now."""

    field_code: str = Field(min_length=1, max_length=30)
    corrected_value: str = Field(max_length=TEXT_VALUE_MAX_LENGTH)
    reason: str = Field(max_length=REASON_MAX_LENGTH)


class MachineCorrectionCloseInput(_AssetWrite):
    pass


class FitPartInput(_AssetWrite):
    """Both records change, so both are guarded: the machine by `expected_asset_version`, the part by
    `expected_part_version`."""

    part_public_id: UUID
    expected_part_version: int = Field(**_WHOLE)
    fitted_on: date


class RemovePartInput(_AssetWrite):
    expected_part_version: int = Field(**_WHOLE)
    removed_on: date


class KitAddInput(_Request):
    """Pieces of one kit model (ERT-2). For a kind tracked one by one, `count` records of one piece each - a
    number of its own only when `count` is 1; for a counted kind, one record of `count` pieces. The form's
    own `create_request_key`: sending the same request twice records once, and the key with any other request is
    refused.

    Kit is added from a machine's page, so the request names that machine and the versions of it and of the kit
    model the page showed: if either changed since, or the kit model no longer fits the machine's model, it is
    refused rather than added on a premise that no longer holds (independent review, round 1, ERT2-R1-001)."""

    create_request_key: UUID
    machine_public_id: UUID
    expected_asset_version: int = Field(**_WHOLE)
    kit_model_public_id: UUID
    expected_model_version: int = Field(**_WHOLE)
    count: int = Field(ge=1, le=MAX_KIT_COUNT)
    serial_number: str | None = Field(default=None, max_length=SERIAL_NUMBER_MAX_LENGTH)
    year_of_manufacture: int | None = Field(default=None, ge=1900, le=2200)


class KitRetireInput(_AssetWrite):
    """Retire a piece of kit - or, from a counted set, `count` of its pieces - with the reason and the day
    (owner, Q8 and Q14). A note is required with OTHER."""

    reason_code: str = Field(min_length=1, max_length=30)
    note: str | None = Field(default=None, max_length=REASON_MAX_LENGTH)
    retired_on: date
    count: int | None = Field(default=None, **_WHOLE)


class ValueRuleInput(_Request):
    """How a Plum value is read wherever it appears in a column (design section 5B)."""

    column_code: str = Field(min_length=1, max_length=30)
    plum_value: str = Field(min_length=1, max_length=TEXT_VALUE_MAX_LENGTH)
    action_code: str = Field(min_length=1, max_length=30)
    result_number: Decimal | None = Field(default=None, gt=0, max_digits=12, decimal_places=3, allow_inf_nan=False)
    result_unit_code: str | None = Field(default=None, max_length=50)
    result_class_code: str | None = Field(default=None, max_length=50)
    result_type_code: str | None = Field(default=None, max_length=50)
    reason: str = Field(max_length=REASON_MAX_LENGTH)
    # The preview the Fleet Admin recorded it from, if any.
    import_public_id: UUID | None = None


class ImportRefreshInput(_Request):
    expected_preview_version: int = Field(**_WHOLE)


class ImportPairInput(_Request):
    """Fit a part in the report to a machine, by Plum's machine numbers, when the report is confirmed."""

    part_machine_number: str = Field(min_length=1, max_length=TEXT_VALUE_MAX_LENGTH)
    machine_machine_number: str = Field(min_length=1, max_length=TEXT_VALUE_MAX_LENGTH)


class ImportPublishInput(_Request):
    expected_preview_version: int = Field(**_WHOLE)
    pairs: list[ImportPairInput] = Field(default_factory=list, max_length=1000)


class ImportDiscardInput(_Request):
    expected_preview_version: int = Field(**_WHOLE)


# --- ERT-1: responses ---------------------------------------------------------------------------------


class CapabilityValueResponse(BaseModel):
    capability_code: str
    capability_label: str
    unit_code: str | None = None
    unit_symbol: str | None = None
    value_kind_code: str
    is_key: bool
    value: Decimal | None = None
    choice_value: str | None = None


class ModelReference(BaseModel):
    model_public_id: UUID
    label: str


class EquipmentModelResponse(BaseModel):
    model_public_id: UUID
    maker: str
    model_name: str
    label: str
    class_code: str
    class_label: str
    class_kind_code: str
    type_code: str | None = None
    type_label: str | None = None
    maker_part_number: str | None = None
    capabilities: list[CapabilityValueResponse]
    # The Plum model names mapped to it.
    mapped_names: list[str]
    # Every record of it: machines, parts and pieces of kit.
    machine_count: int
    # ERT-2. A kit model: the crane models it fits, the pieces held (active sets counted by their quantity),
    # and whether none of the models it fits has an active machine left (kit left behind; owner, Q7).
    is_kit: bool = False
    fits_models: list[ModelReference] = Field(default_factory=list)
    pieces_held: int = 0
    fits_no_active_crane: bool = False
    # A machine model: its active machines, which share the kit held for it.
    active_unit_count: int = 0
    model_version: int
    is_retired: bool
    created_at: datetime
    updated_at: datetime


class EquipmentModelActionResponse(BaseModel):
    model: EquipmentModelResponse
    # None when nothing was recorded: an identical save, or a create repeated with the same request key.
    event: dict[str, Any] | None = None
    # True when a create was the very request its key first made: the model that made, nothing recorded again.
    replayed: bool = False


class ModelMappingActionResponse(BaseModel):
    source_name: str
    model_public_id: UUID | None = None
    event: dict[str, Any] | None = None


class MachineFlagResponse(BaseModel):
    flag_code: str
    subject_code: str
    raised_at: datetime
    raised_by_import_public_id: UUID | None = None


class MachineCapabilityResponse(CapabilityValueResponse):
    # OWN: the Fleet Admin's value for this machine; MODEL: its model's rating; NONE: neither.
    source_code: str
    reason: str | None = None
    set_by_display_name: str | None = None
    set_at: datetime | None = None


class MachineCorrectionResponse(BaseModel):
    correction_public_id: UUID
    field_code: str
    # Withheld (None, with `values_withheld`) for an engine or chassis number the caller may not see.
    plum_value: str | None = None
    corrected_value: str | None = None
    corrected_value_label: str | None = None
    values_withheld: bool = False
    # Withheld (None) with the values: the reason for an engine or chassis number may repeat it.
    reason: str | None = None
    correction_status_code: str
    closed_reason_code: str | None = None
    closed_by_display_name: str | None = None
    closed_at: datetime | None = None
    recorded_by_display_name: str | None = None
    recorded_at: datetime


class AssetReference(BaseModel):
    asset_public_id: UUID
    asset_reference: str
    machine_number: str
    class_code: str
    # The version a fit or removal is guarded by.
    asset_version: int


class MachineLinkResponse(BaseModel):
    link_public_id: UUID
    machine: AssetReference
    part: AssetReference
    fitted_on: date
    removed_on: date | None = None


class MachineSummaryResponse(BaseModel):
    asset_public_id: UUID
    asset_reference: str
    asset_kind_code: str
    # PLUM, or PLATFORM for a piece of kit the Fleet Admin recorded (ERT-2).
    origin_code: str
    # Plum's machine number; None for a piece of kit, which has no Plum row.
    machine_number: str | None = None
    # 1, or a counted set's count.
    quantity: int
    class_code: str
    class_label: str
    type_code: str | None = None
    type_label: str | None = None
    model_public_id: UUID | None = None
    model_label: str | None = None
    key_capability: CapabilityValueResponse | None = None
    asset_status_code: str
    flag_codes: list[str]
    # A platform fact is still to be entered: a machine's serial number or year of manufacture, or the
    # number of a piece of kit tracked one by one.
    details_missing: bool
    # The date of the report the Plum facts came from.
    facts_report_date: date | None = None
    asset_version: int


class PlumSourceWords(BaseModel):
    """How Plum's last confirmed report recorded the machine, in Plum's words, for the Fleet Admin."""

    category: str | None = None
    model_name: str | None = None
    capacity: str | None = None


class KitHeldResponse(BaseModel):
    """One kit model fitting a machine's model, and what is held of it for every machine of those models."""

    kit_model_public_id: UUID
    label: str
    class_code: str
    class_label: str
    type_code: str | None = None
    type_label: str | None = None
    tracking_code: str
    key_capability: CapabilityValueResponse | None = None
    # Pieces held (active records, counted sets by their quantity), and the records holding them.
    pieces_held: int
    records_held: int
    fits_models: list[ModelReference]


class MachineResponse(MachineSummaryResponse):
    # Confidential: None for a caller without EQUIPMENT_IDENTITY_READ, with `identity_numbers_withheld` set.
    engine_number: str | None = None
    chassis_number: str | None = None
    identity_numbers_withheld: bool
    commenced_year: int | None = None
    owning_company: str | None = None
    serial_number: str | None = None
    year_of_manufacture: int | None = None
    capabilities: list[MachineCapabilityResponse]
    flags: list[MachineFlagResponse]
    corrections: list[MachineCorrectionResponse]
    fitted_parts: list[MachineLinkResponse]
    fitted_to: MachineLinkResponse | None = None
    link_history: list[MachineLinkResponse]
    plum: PlumSourceWords | None = None
    reconciliation_status_code: str | None = None
    last_import_public_id: UUID | None = None
    # ERT-2. A machine: the kit held for its model, and how many active machines of the model share it.
    kit: list[KitHeldResponse] = Field(default_factory=list)
    model_active_unit_count: int | None = None
    # A piece of kit: the crane models its model fits, and, once retired, when and why.
    fits_models: list[ModelReference] = Field(default_factory=list)
    retired_on: date | None = None
    retirement_reason_code: str | None = None
    retirement_note: str | None = None
    created_at: datetime
    updated_at: datetime


class MachineActionResponse(BaseModel):
    machine: MachineResponse
    # None when nothing was recorded (an identical save).
    event: dict[str, Any] | None = None


class KitAddResponse(BaseModel):
    """The records one request made. On a repeat of the same request key, the same records with `replayed`
    and no events."""

    pieces: list[MachineSummaryResponse]
    replayed: bool = False
    events: list[dict[str, Any]] = Field(default_factory=list)


class ValueRuleResponse(BaseModel):
    rule_public_id: UUID
    column_code: str
    # Withheld (None, with `value_withheld`) in the engine or chassis number column for a caller who may
    # not see those numbers.
    plum_value: str | None = None
    value_withheld: bool = False
    action_code: str
    result_number: Decimal | None = None
    result_unit_code: str | None = None
    result_class_code: str | None = None
    result_type_code: str | None = None
    # Withheld (None) with the values: the reason for an engine or chassis number may repeat it.
    reason: str | None = None
    rule_status_code: str
    closed_reason_code: str | None = None
    closed_by_display_name: str | None = None
    closed_at: datetime | None = None
    recorded_during_import_public_id: UUID | None = None
    recorded_by_display_name: str | None = None
    recorded_at: datetime
    # How many rows of the latest confirmed report carry the value; None before any report is confirmed.
    rows_in_latest_report: int | None = None


class ValueRuleActionResponse(BaseModel):
    rule: ValueRuleResponse
    event: dict[str, Any] | None = None


class CorrectionToSendResponse(BaseModel):
    correction_public_id: UUID
    asset_public_id: UUID
    asset_reference: str
    machine_number: str
    field_code: str
    # Withheld (None, with `values_withheld`) for an engine or chassis number the caller may not see.
    plum_value: str | None = None
    corrected_value: str | None = None
    corrected_value_label: str | None = None
    values_withheld: bool = False
    # Withheld (None) with the values: the reason for an engine or chassis number may repeat it.
    reason: str | None = None
    recorded_by_display_name: str | None = None
    recorded_at: datetime
    # Plum now holds a third value where this correction was recorded against another.
    plum_changed: bool


class CorrectionsToSendResponse(BaseModel):
    """Every open value rule and machine correction: the request to fix at source (ADR-037, route A)."""

    value_rules: list[ValueRuleResponse]
    corrections: list[CorrectionToSendResponse]


class CategoryRuleResponse(BaseModel):
    category: str
    class_code: str
    class_label: str
    check_code: str
    capability_code: str | None = None
    capability_label: str | None = None
    plum_unit_code: str | None = None
    plausible_low: Decimal | None = None
    plausible_high: Decimal | None = None


class ImportSummaryResponse(BaseModel):
    import_public_id: UUID
    import_status_code: str
    report_date: date
    row_count: int
    # The start of the file's SHA-256 fingerprint, enough to tell two reports apart on screen.
    fingerprint_prefix: str
    uploaded_by_display_name: str | None = None
    uploaded_at: datetime
    published_by_display_name: str | None = None
    published_at: datetime | None = None
    discarded_by_display_name: str | None = None
    discarded_at: datetime | None = None
    discard_reason_code: str | None = None
    counts: dict[str, int]


class ImportResponse(ImportSummaryResponse):
    preview_version: int
    preview_computed_at: datetime
    # A preview can be confirmed only while nothing it was computed from has changed since.
    is_current: bool
    stale_reason: str | None = None
    based_on_import_public_id: UUID | None = None
    preview: dict[str, Any]


class ImportActionResponse(BaseModel):
    equipment_import: ImportResponse
    # True when the same report was already waiting as a preview and that preview is returned.
    replayed: bool = False
    event: dict[str, Any] | None = None
