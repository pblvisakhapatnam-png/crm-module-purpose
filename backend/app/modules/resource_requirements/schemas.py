"""Resource Requirement request and response shapes (WRR-001).

Unknown request fields are refused with 422 throughout. In particular a capability's unit cannot be
sent: the unit is the capability's, fixed by the Equipment Reference.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.modules.resource_requirements.contract import (
    CANCELLATION_REASON_MAX_LENGTH,
    CREW_NOTES_MAX_LENGTH,
    LARGEST_WHOLE_NUMBER,
    PLANNING_NOTES_MAX_LENGTH,
    PRIORITY_NORMAL,
    SPECIFICATION_MAX_LENGTH,
)

_WHOLE = {"le": LARGEST_WHOLE_NUMBER}


# --- Requests ----------------------------------------------------------------------------------------


class ResourceRequirementCapabilityInput(BaseModel):
    """One capability the item must have. A least value for a measured capability, or the value for a
    capability with a fixed list (axle configuration) - never both, and never a unit."""

    model_config = ConfigDict(extra="forbid")

    capability_code: str = Field(min_length=1, max_length=50)
    minimum_value: Decimal | None = Field(
        default=None, gt=0, max_digits=12, decimal_places=3, allow_inf_nan=False
    )
    choice_value: str | None = Field(default=None, max_length=50)


class ResourceRequirementItemInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    equipment_class_code: str = Field(min_length=1, max_length=50)
    # Blank: any type in the class.
    equipment_type_code: str | None = Field(default=None, max_length=50)
    equipment_specification: str | None = Field(default=None, max_length=SPECIFICATION_MAX_LENGTH)
    capabilities: list[ResourceRequirementCapabilityInput] = Field(default_factory=list, max_length=50)


class ResourceRequirementFields(BaseModel):
    """Everything a requirement records. A change is a whole replacement of these."""

    model_config = ConfigDict(extra="forbid")

    units_required: int = Field(ge=1, **_WHOLE)
    required_from: date
    # Blank: until the line ends.
    required_to: date | None = None
    crew_operators_required: int = Field(ge=0, **_WHOLE)
    crew_helpers_required: int = Field(ge=0, **_WHOLE)
    crew_notes: str | None = Field(default=None, max_length=CREW_NOTES_MAX_LENGTH)
    priority_code: str = Field(default=PRIORITY_NORMAL, max_length=20)
    planning_notes: str | None = Field(default=None, max_length=PLANNING_NOTES_MAX_LENGTH)
    # Exactly one in this slice; the service refuses none or several with a message that says so.
    items: list[ResourceRequirementItemInput] = Field(max_length=10)


class ResourceRequirementCreate(ResourceRequirementFields):
    """A new requirement for one line. Both the Work Order and the line are named, so a form cannot pair
    a line with a Work Order it does not belong to. `create_request_key` is the form's own UUID: sending
    the same request twice creates one requirement, not two, and the key with any other request is refused."""

    work_order_public_id: UUID
    work_order_line_public_id: UUID
    create_request_key: UUID


class ResourceRequirementUpdate(ResourceRequirementFields):
    expected_requirement_version: int = Field(ge=1, **_WHOLE)


class ResourceRequirementCancel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_requirement_version: int = Field(ge=1, **_WHOLE)
    cancellation_reason: str = Field(max_length=CANCELLATION_REASON_MAX_LENGTH)


# --- Responses ---------------------------------------------------------------------------------------


class ResourceRequirementCapabilityResponse(BaseModel):
    capability_code: str
    capability_label: str
    unit_code: str | None = None
    unit_symbol: str | None = None
    value_kind_code: str
    is_key: bool
    minimum_value: Decimal | None = None
    choice_value: str | None = None


class ResourceRequirementItemResponse(BaseModel):
    item_number: int
    equipment_class_code: str
    equipment_class_label: str
    equipment_type_code: str | None = None
    equipment_type_label: str | None = None
    equipment_specification: str | None = None
    capabilities: list[ResourceRequirementCapabilityResponse]


class ResourceRequirementSite(BaseModel):
    public_id: UUID
    address_line1: str | None = None
    city: str | None = None
    state: str | None = None
    postal_code: str | None = None


class ResourceRequirementContractGap(BaseModel):
    first_day: date
    last_day: date
    extension_sequence_no: int


class ResourceRequirementLineFacts(BaseModel):
    """The Work Order line as it stands now, read live through the Work Order module - never copied.

    The billing basis, shifts a day and crew are the line's terms in force on the requirement's start (or
    today, where there is no start yet). No rate, amount or commercial term is given (WRR-001)."""

    work_order_status_code: str
    scope_description: str
    equipment_service_category: str | None = None
    # Billing units ("8 Days", "3 Mon") for reference only: not a number of machines (Q2).
    quantity: Decimal
    uom: str
    site: ResourceRequirementSite | None = None
    line_start_date: date | None = None
    line_end_date: date | None = None
    contract_start_date: date | None = None
    contract_end_basis_code: str | None = None
    contract_end_date: date | None = None
    contract_gaps: list[ResourceRequirementContractGap]
    billing_terms_period_number: int | None = None
    billing_uom_code: str | None = None
    # Slice 7D Part 5: 1, 2 or 3 shifts a day as the Work Order states them; null when it states none ("not in
    # the Work Order"), when not recorded, or on an hourly line.
    shifts_per_day: int | None = None
    # Part 4: NONE is equipment only; STATED carries the numbers; null means not answered yet.
    work_order_crew_code: str | None = None
    work_order_crew_operators: int | None = None
    work_order_crew_helpers: int | None = None
    # 8A core: whether the site is a central-government site, from the line's details; null is not answered.
    site_central_government: bool | None = None


class ResourceRequirementResponse(BaseModel):
    requirement_public_id: UUID
    requirement_reference: str
    work_order_public_id: UUID
    work_order_code: str
    work_order_line_public_id: UUID
    work_order_line_number: int
    source_offer_line_public_id: UUID | None = None
    account_public_id: UUID | None = None
    units_required: int
    required_from: date
    required_to: date | None = None
    crew_operators_required: int
    crew_helpers_required: int
    crew_notes: str | None = None
    priority_code: str
    planning_notes: str | None = None
    requirement_status_code: str
    requirement_version: int
    taxonomy_version: int
    # 8A core, worked out from the machines held for it (through Assignment): units whose machines cover every
    # day of its period, and units required less those (RPA-001: "the remaining quantity stays visible").
    units_covered: int
    units_remaining: int
    # 8A core: the units whose machines cover every day; allocation is offered on the others.
    covered_unit_numbers: list[int]
    items: list[ResourceRequirementItemResponse]
    # Advisory, computed on every read of an open requirement; never stored and never a refusal.
    warnings: list[str]
    line: ResourceRequirementLineFacts
    cancellation_reason: str | None = None
    cancelled_by: UUID | None = None
    cancelled_by_display_name: str | None = None
    cancelled_at: datetime | None = None
    created_by: UUID | None = None
    created_by_display_name: str | None = None
    created_at: datetime
    updated_by: UUID | None = None
    updated_by_display_name: str | None = None
    updated_at: datetime


class ResourceRequirementActionResponse(BaseModel):
    resource_requirement: ResourceRequirementResponse
    # None when nothing was recorded: an identical save, or a create repeated with the same request key.
    event: dict[str, Any] | None = None
    # 8A core: how many held machines a cancellation freed; 0 for every other action.
    machines_freed: int = 0
    # True when a create was the very request its key first made: the requirement that made, nothing recorded again.
    replayed: bool = False


class ResourceRequirementSuggestedValues(BaseModel):
    units_required: int
    required_from: date | None = None
    required_to: date | None = None
    crew_operators_required: int | None = None
    crew_helpers_required: int | None = None
    priority_code: str
    equipment_class_code: str | None = None
    equipment_type_code: str | None = None
    # The word in the line's category that suggested the class, so the form can say why.
    equipment_class_matched_term: str | None = None


class ResourceRequirementDefaultsResponse(BaseModel):
    """What a new requirement for one line starts from. The server owns what the defaults are."""

    work_order_public_id: UUID
    work_order_code: str
    work_order_line_public_id: UUID
    work_order_line_number: int
    source_offer_line_public_id: UUID | None = None
    account_public_id: UUID | None = None
    taxonomy_version: int
    line: ResourceRequirementLineFacts
    suggested: ResourceRequirementSuggestedValues
    existing_requirement_count: int
