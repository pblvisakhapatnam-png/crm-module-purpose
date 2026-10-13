"""Equipment Reference codes and the canonical shapes its source adapter produces (ADR-037, ERT-1, ERT-2).

The codes of the structure itself - classes, types, capabilities - are data, loaded by migration and
read from the database. What lives here is the small fixed vocabulary around them: business lines,
units, value kinds, alias sources, (ERT-1) the kinds, statuses, flags, corrections and events of models
and machines, and (ERT-2) how kit hangs off a class, how its pieces are tracked, where an asset comes
from and why a piece is retired.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Final
from uuid import UUID, uuid5

EQUIPMENT_REFERENCE_MODULE_NAME: Final = "equipment_reference"

# Which business lines deploy a class to customers (owner, Q14). A class with neither is recorded but
# never offered where Operations plans hiring - light vehicles and workshop assets, for example.
BUSINESS_LINE_HIRING: Final = "HIRING"
BUSINESS_LINE_TRANSPORTATION: Final = "TRANSPORTATION"
BUSINESS_LINE_CODES: Final = (BUSINESS_LINE_HIRING, BUSINESS_LINE_TRANSPORTATION)

# A MINIMUM capability is stated as the least value a machine must reach, in the capability's own
# unit. A CHOICE capability is one of a fixed list (axle configuration) and has no unit.
VALUE_KIND_MINIMUM: Final = "MINIMUM"
VALUE_KIND_CHOICE: Final = "CHOICE"
VALUE_KIND_CODES: Final = (VALUE_KIND_MINIMUM, VALUE_KIND_CHOICE)

# Where an alias comes from.
ALIAS_SOURCE_PLUM_CATEGORY: Final = "PLUM_CATEGORY"
ALIAS_SOURCE_ANNEXURE_21: Final = "ANNEXURE_21"
ALIAS_SOURCE_TRADE_TERM: Final = "TRADE_TERM"
ALIAS_SOURCE_CODES: Final = (ALIAS_SOURCE_PLUM_CATEGORY, ALIAS_SOURCE_ANNEXURE_21, ALIAS_SOURCE_TRADE_TERM)


@dataclass(frozen=True)
class EquipmentUnit:
    unit_code: str
    unit_label: str
    unit_symbol: str
    # A count is a whole number; every other unit takes decimals.
    whole_numbers_only: bool


# Every capability has exactly one of these, fixed by the structure: a value is never sent with its
# unit, so "80000" cannot mean kilograms for one crane and tonnes for another. The database refuses any
# other code (ck_equipment_capability_unit).
EQUIPMENT_UNITS: Final = (
    EquipmentUnit("TONNE", "tonne", "t", False),
    EquipmentUnit("KILOGRAM", "kilogram", "kg", False),
    EquipmentUnit("METRE", "metre", "m", False),
    EquipmentUnit("CUBIC_METRE", "cubic metre", "m³", False),
    EquipmentUnit("KILOWATT", "kilowatt", "kW", False),
    EquipmentUnit("KILOVOLT_AMPERE", "kilovolt-ampere", "kVA", False),
    EquipmentUnit("COUNT", "count", "", True),
)
EQUIPMENT_UNITS_BY_CODE: Final = {unit.unit_code: unit for unit in EQUIPMENT_UNITS}


def normalize_term(value: str | None) -> str:
    """The form every alias is matched in: whitespace collapsed, trimmed, upper case.

    Must agree with ck_equipment_term_alias_normalized, which fixes the stored form in the database.
    """
    if value is None:
        return ""
    return " ".join(value.split()).upper()


# --- What a class is, and what an asset is (ERT-1, structure version 2) ------------------------------

# A class describes either machines or the parts fitted to them. A part class is offered to no business
# line, so it never appears where Operations asks for machines.
CLASS_KIND_MACHINE: Final = "MACHINE"
CLASS_KIND_PART: Final = "PART"
CLASS_KIND_CODES: Final = (CLASS_KIND_MACHINE, CLASS_KIND_PART)

# An asset's kind is always its class's kind (fk_equipment_asset_class_kind).
ASSET_KIND_MACHINE: Final = CLASS_KIND_MACHINE
ASSET_KIND_PART: Final = CLASS_KIND_PART

ASSET_STATUS_ACTIVE: Final = "ACTIVE"
ASSET_STATUS_RETIRED: Final = "RETIRED"
ASSET_STATUS_CODES: Final = (ASSET_STATUS_ACTIVE, ASSET_STATUS_RETIRED)

# Only fitted parts are linked to a machine. Detachable kit (ERT-2) is never linked: it is held for the
# crane models it fits, and shared by every crane of them (owner, Q6).
LINK_KIND_FITTED: Final = "FITTED"

# How a part class hangs off a class (equipment_part_fit.fit_kind_code, structure version 3): FITTED - always
# part of the machine, by a dated link; KIT - held for the models it fits, picked per job.
FIT_KIND_FITTED: Final = "FITTED"
FIT_KIND_KIT: Final = "KIT"

# Whether a kind's pieces are recorded one by one or as a counted set (equipment_class.tracking_code; owner, Q3).
TRACKING_SINGLE: Final = "SINGLE"
TRACKING_COUNTED: Final = "COUNTED"

# Where an asset comes from (equipment_asset.origin_code): Plum's report, or the platform, where the Fleet
# Admin records the kit Plum does not list (ERT-1 design, comment 5).
ORIGIN_PLUM: Final = "PLUM"
ORIGIN_PLATFORM: Final = "PLATFORM"

# Why a piece of kit was retired (owner, Q8 and Q14); OTHER needs a note.
RETIREMENT_SCRAPPED: Final = "SCRAPPED"
RETIREMENT_LOST: Final = "LOST"
RETIREMENT_SOLD: Final = "SOLD"
RETIREMENT_RECORDED_BY_MISTAKE: Final = "RECORDED_BY_MISTAKE"
RETIREMENT_OTHER: Final = "OTHER"
RETIREMENT_REASON_CODES: Final = (
    RETIREMENT_SCRAPPED,
    RETIREMENT_LOST,
    RETIREMENT_SOLD,
    RETIREMENT_RECORDED_BY_MISTAKE,
    RETIREMENT_OTHER,
)

# "Add several alike" makes at most this many records, or a counted set of at most this many, at once.
MAX_KIT_COUNT: Final = 50

PROVIDER_PLUM: Final = "PLUM"

# --- Data-quality flags (design section 8) -----------------------------------------------------------
#
# Why a value could not be taken in as it stood. Kept on the asset until an import no longer raises it or
# the Fleet Admin removes its cause - never a silent correction (ADR-037).
DATA_QUALITY_UNIT_UNCLEAR: Final = "UNIT_UNCLEAR"
DATA_QUALITY_NOT_A_NUMBER: Final = "NOT_A_NUMBER"
DATA_QUALITY_VALUE_MISSING: Final = "VALUE_MISSING"
DATA_QUALITY_CATEGORY_NOT_MAPPED: Final = "CATEGORY_NOT_MAPPED"
DATA_QUALITY_OUT_OF_PATTERN: Final = "OUT_OF_PATTERN"
DATA_QUALITY_MODEL_NOT_MAPPED: Final = "MODEL_NOT_MAPPED"
DATA_QUALITY_CLASS_DISAGREES: Final = "CLASS_DISAGREES"
DATA_QUALITY_DIFFERS_FROM_MODEL: Final = "DIFFERS_FROM_MODEL"
DATA_QUALITY_NOT_IN_LATEST_REPORT: Final = "NOT_IN_LATEST_REPORT"
DATA_QUALITY_POSSIBLY_RENUMBERED: Final = "POSSIBLY_RENUMBERED"
DATA_QUALITY_PART_NOT_FITTED: Final = "PART_NOT_FITTED"
DATA_QUALITY_DUPLICATE_SOURCE_KEY: Final = "DUPLICATE_SOURCE_KEY"
DATA_QUALITY_PLUM_CHANGED_CORRECTED_VALUE: Final = "PLUM_CHANGED_CORRECTED_VALUE"
DATA_QUALITY_CODES: Final = (
    DATA_QUALITY_UNIT_UNCLEAR,
    DATA_QUALITY_NOT_A_NUMBER,
    DATA_QUALITY_VALUE_MISSING,
    DATA_QUALITY_CATEGORY_NOT_MAPPED,
    DATA_QUALITY_OUT_OF_PATTERN,
    DATA_QUALITY_MODEL_NOT_MAPPED,
    DATA_QUALITY_CLASS_DISAGREES,
    DATA_QUALITY_DIFFERS_FROM_MODEL,
    DATA_QUALITY_NOT_IN_LATEST_REPORT,
    DATA_QUALITY_POSSIBLY_RENUMBERED,
    DATA_QUALITY_PART_NOT_FITTED,
    DATA_QUALITY_DUPLICATE_SOURCE_KEY,
    DATA_QUALITY_PLUM_CHANGED_CORRECTED_VALUE,
)
# Raised by a report as a whole, not by a machine's own row: re-deriving one machine after a correction
# leaves these as they are.
REPORT_LEVEL_FLAG_CODES: Final = frozenset(
    {
        DATA_QUALITY_NOT_IN_LATEST_REPORT,
        DATA_QUALITY_POSSIBLY_RENUMBERED,
        DATA_QUALITY_PART_NOT_FITTED,
        DATA_QUALITY_DUPLICATE_SOURCE_KEY,
    }
)

# --- The Fleet Admin's corrections (design section 5B) -----------------------------------------------

# One machine's field. The machine number is not among them: it is the key Plum and the platform share.
CORRECTION_FIELD_CATEGORY: Final = "CATEGORY"
CORRECTION_FIELD_MODEL: Final = "MODEL"
CORRECTION_FIELD_ENGINE_NUMBER: Final = "ENGINE_NUMBER"
CORRECTION_FIELD_CHASSIS_NUMBER: Final = "CHASSIS_NUMBER"
CORRECTION_FIELD_COMMENCED_YEAR: Final = "COMMENCED_YEAR"
CORRECTION_FIELD_OWNING_COMPANY: Final = "OWNING_COMPANY"
CORRECTION_FIELD_STATUS: Final = "STATUS"
CORRECTION_FIELD_CAPACITY: Final = "CAPACITY"
CORRECTION_FIELDS: Final = (
    CORRECTION_FIELD_CATEGORY,
    CORRECTION_FIELD_MODEL,
    CORRECTION_FIELD_ENGINE_NUMBER,
    CORRECTION_FIELD_CHASSIS_NUMBER,
    CORRECTION_FIELD_COMMENCED_YEAR,
    CORRECTION_FIELD_OWNING_COMPANY,
    CORRECTION_FIELD_STATUS,
    CORRECTION_FIELD_CAPACITY,
)

# Confidential (owner, 25 September 2026): shown only to a holder of EQUIPMENT_IDENTITY_READ - on a
# machine, and in any correction or value rule of these fields, whose values are withheld from others.
IDENTITY_FIELDS: Final = frozenset({CORRECTION_FIELD_ENGINE_NUMBER, CORRECTION_FIELD_CHASSIS_NUMBER})

# The columns a value rule may read, wherever the value appears in them.
VALUE_RULE_COLUMNS: Final = (
    CORRECTION_FIELD_CAPACITY,
    CORRECTION_FIELD_COMMENCED_YEAR,
    CORRECTION_FIELD_ENGINE_NUMBER,
    CORRECTION_FIELD_CHASSIS_NUMBER,
    CORRECTION_FIELD_OWNING_COMPANY,
)
VALUE_RULE_SPLIT_NUMBER_AND_UNIT: Final = "SPLIT_NUMBER_AND_UNIT"
VALUE_RULE_REASSIGN_TO_TYPE: Final = "REASSIGN_TO_TYPE"
VALUE_RULE_NOT_A_VALUE: Final = "NOT_A_VALUE"
VALUE_RULE_ACTIONS: Final = (VALUE_RULE_SPLIT_NUMBER_AND_UNIT, VALUE_RULE_REASSIGN_TO_TYPE, VALUE_RULE_NOT_A_VALUE)
# Splitting and reassigning apply to the capacity figure only; "not a value" to any rule column.
CAPACITY_ONLY_ACTIONS: Final = frozenset({VALUE_RULE_SPLIT_NUMBER_AND_UNIT, VALUE_RULE_REASSIGN_TO_TYPE})

STATUS_OPEN: Final = "OPEN"
STATUS_CLOSED: Final = "CLOSED"
CLOSED_BY_FLEET_ADMIN: Final = "BY_FLEET_ADMIN"
CLOSED_SUPERSEDED: Final = "SUPERSEDED"
CLOSED_PLUM_AGREES: Final = "PLUM_AGREES"

# --- What Plum's capacity figure means in each category (design section 6) --------------------------
CATEGORY_CHECKED: Final = "CHECKED"
CATEGORY_UNIT_UNCLEAR: Final = "UNIT_UNCLEAR"
CATEGORY_NOT_CHECKED: Final = "NOT_CHECKED"

# --- Imports -------------------------------------------------------------------------------------------
IMPORT_STATUS_PREVIEWED: Final = "PREVIEWED"
IMPORT_STATUS_PUBLISHED: Final = "PUBLISHED"
IMPORT_STATUS_DISCARDED: Final = "DISCARDED"
DISCARDED_BY_FLEET_ADMIN: Final = "BY_FLEET_ADMIN"
DISCARDED_SUPERSEDED: Final = "SUPERSEDED"

# The upload is refused above this size, counted as the bytes arrive (design section 5, step 1).
MAX_REPORT_BYTES: Final = 5 * 1024 * 1024
# The most any equipment-reference request body may carry: a report at the limit plus room for the
# form's other fields and its multipart framing.
MAX_EQUIPMENT_REQUEST_BYTES: Final = MAX_REPORT_BYTES + 256 * 1024
# A sanity bound, far above Plum's 681 rows of 24 September 2026.
MAX_REPORT_ROWS: Final = 20_000

# --- Events (design section 11) ----------------------------------------------------------------------
EQUIPMENT_EVENT_IMPORT_PUBLISHED: Final = "EQUIPMENT_IMPORT_PUBLISHED"
EQUIPMENT_EVENT_ASSET_REGISTERED: Final = "EQUIPMENT_ASSET_REGISTERED"
EQUIPMENT_EVENT_ASSET_CHANGED: Final = "EQUIPMENT_ASSET_CHANGED"
EQUIPMENT_EVENT_ASSET_RETIRED: Final = "EQUIPMENT_ASSET_RETIRED"
EQUIPMENT_EVENT_ASSET_REACTIVATED: Final = "EQUIPMENT_ASSET_REACTIVATED"
EQUIPMENT_EVENT_MODEL_RECORDED: Final = "EQUIPMENT_MODEL_RECORDED"
EQUIPMENT_EVENT_MODEL_CHANGED: Final = "EQUIPMENT_MODEL_CHANGED"
EQUIPMENT_EVENT_MODEL_MAPPED: Final = "EQUIPMENT_MODEL_MAPPED"
EQUIPMENT_EVENT_PART_FITTED: Final = "EQUIPMENT_PART_FITTED"
EQUIPMENT_EVENT_PART_REMOVED: Final = "EQUIPMENT_PART_REMOVED"
EQUIPMENT_EVENT_MACHINE_CAPABILITY_SET: Final = "EQUIPMENT_MACHINE_CAPABILITY_SET"
EQUIPMENT_EVENT_MACHINE_DETAILS_SET: Final = "EQUIPMENT_MACHINE_DETAILS_SET"
EQUIPMENT_EVENT_VALUE_RULE_RECORDED: Final = "EQUIPMENT_VALUE_RULE_RECORDED"
EQUIPMENT_EVENT_VALUE_RULE_CLOSED: Final = "EQUIPMENT_VALUE_RULE_CLOSED"
EQUIPMENT_EVENT_CORRECTION_RECORDED: Final = "EQUIPMENT_CORRECTION_RECORDED"
EQUIPMENT_EVENT_CORRECTION_CLOSED: Final = "EQUIPMENT_CORRECTION_CLOSED"

# The record types events are written under - what the test harness's cleanup matches them by.
RECORD_TYPE_IMPORT: Final = "equipment_import"
RECORD_TYPE_ASSET: Final = "equipment_asset"
RECORD_TYPE_MODEL: Final = "equipment_model"
RECORD_TYPE_VALUE_RULE: Final = "equipment_value_rule"
RECORD_TYPE_MODEL_MAPPING: Final = "equipment_model_mapping"

# A Plum model name's mapping is keyed by its provider and normalized name, and has no other identity; its
# public id is derived from that key (UUID v5 in this namespace), so the same name always has the same id -
# whoever maps it, to whichever model - and the harness can name a run's mappings from the names alone
# (independent review, round 3, ERT1-R3-004).
MODEL_MAPPING_NAMESPACE: Final = UUID("96bf217b-8366-4a3f-963a-c99e230afae5")


def model_mapping_public_id(provider_code: str, source_name: str) -> str:
    return str(uuid5(MODEL_MAPPING_NAMESPACE, f"{provider_code}:{normalize_term(source_name)}"))

# --- Limits --------------------------------------------------------------------------------------------
REASON_MAX_LENGTH: Final = 1000
TEXT_VALUE_MAX_LENGTH: Final = 200
MAKER_MAX_LENGTH: Final = 100
MODEL_NAME_MAX_LENGTH: Final = 100
SERIAL_NUMBER_MAX_LENGTH: Final = 100
MAKER_PART_NUMBER_MAX_LENGTH: Final = 100
EARLIEST_YEAR: Final = 1900


# --- What the source adapter must hand the platform ----------------------------------------------------
#
# Canonical shapes only. The adapter keeps which source row a machine came from, the import and the raw
# values it was built from in its own Source Binding, never here; Plum's PAN and insurance-policy numbers
# are not carried at all (ERT-1 design, Q8).


@dataclass(frozen=True)
class CanonicalCapabilityValue:
    """One capability of a machine, in the capability's own unit: the Fleet Admin's own value for this
    machine where one is set, otherwise its model's rating."""

    capability_code: str
    value: Decimal | None
    choice_value: str | None = None


@dataclass(frozen=True)
class DataQualityFlag:
    flag_code: str
    capability_code: str | None
    message: str


@dataclass(frozen=True)
class CanonicalMachine:
    """One physical machine in the platform's terms. Its identity is the platform's own public id and
    reference; the source record it was built from is the adapter's to keep. A part Plum holds as a
    separate record - a crane's carrier - is not a second machine: it is the machine's fitted part in the
    component hierarchy, and is not in a snapshot of machines.

    `facts_as_of` is the date of the report its Plum facts came from - the freshness indicator of
    PF-1F-HR, section H. What staleness blocks is decided by the consumer that needs it (8A), not here.
    """

    machine_public_id: str
    machine_reference: str
    class_code: str
    type_code: str | None
    model_public_id: str | None
    status_code: str
    master_version: int
    facts_as_of: date | None
    capabilities: tuple[CanonicalCapabilityValue, ...]
    flags: tuple[DataQualityFlag, ...]


@dataclass(frozen=True)
class EquipmentSourceSnapshot:
    taxonomy_version: int
    snapshot_at: datetime
    machines: tuple[CanonicalMachine, ...]
