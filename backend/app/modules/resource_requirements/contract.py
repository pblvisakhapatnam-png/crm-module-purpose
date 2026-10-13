"""Resource Requirement codes, events and warnings (WRR-001).

See docs/agent/slices/wrr-001-resource-requirement-foundation.md, sections 7 to 12, and
docs/agent/contracts/resource-requirement-api-contract.md.
"""

from __future__ import annotations

from typing import Final

RESOURCE_REQUIREMENT_MODULE_NAME: Final = "resource_requirements"
RESOURCE_REQUIREMENT_RECORD_TYPE: Final = "resource_requirement"

# OPEN: no machine held on any of its units. PARTLY_FULFILLED and FULFILLED come into use with 8A core: some
# units, or every unit, covered by machines held for them (worked out from Assignment, through the port).
# COMPLETED stays reserved: nothing in 8A core ends a job (8E). CANCELLED is final.
REQUIREMENT_STATUS_OPEN: Final = "OPEN"
REQUIREMENT_STATUS_PARTLY_FULFILLED: Final = "PARTLY_FULFILLED"
REQUIREMENT_STATUS_FULFILLED: Final = "FULFILLED"
REQUIREMENT_STATUS_CANCELLED: Final = "CANCELLED"
REQUIREMENT_STATUS_CODES: Final = (
    REQUIREMENT_STATUS_OPEN,
    REQUIREMENT_STATUS_PARTLY_FULFILLED,
    REQUIREMENT_STATUS_FULFILLED,
    REQUIREMENT_STATUS_CANCELLED,
)
# The statuses a requirement can still be changed, cancelled and allocated in.
REQUIREMENT_LIVE_STATUS_CODES: Final = (
    REQUIREMENT_STATUS_OPEN,
    REQUIREMENT_STATUS_PARTLY_FULFILLED,
    REQUIREMENT_STATUS_FULFILLED,
)
# The planning list's filter for what still needs machines: open and partly allocated.
STATUS_FILTER_NEEDS_MACHINES: Final = "NEEDS_MACHINES"
NEEDS_MACHINES_STATUS_CODES: Final = (REQUIREMENT_STATUS_OPEN, REQUIREMENT_STATUS_PARTLY_FULFILLED)

# Sorts the planning list: urgent first, then earliest start.
PRIORITY_NORMAL: Final = "NORMAL"
PRIORITY_URGENT: Final = "URGENT"
PRIORITY_CODES: Final = (PRIORITY_NORMAL, PRIORITY_URGENT)

# A Work Order requirement may use only a class Hiring deploys (design section 7).
REQUIREMENT_BUSINESS_LINE: Final = "HIRING"

# Exactly one item per requirement in this slice (owner, Q15); the data holds several so combinations
# fit later. ck_rr_item_single_item_this_slice enforces the same in the database.
ITEMS_PER_REQUIREMENT_THIS_SLICE: Final = 1

CREW_NOTES_MAX_LENGTH: Final = 2000
PLANNING_NOTES_MAX_LENGTH: Final = 4000
SPECIFICATION_MAX_LENGTH: Final = 1000
CANCELLATION_REASON_MAX_LENGTH: Final = 2000

# The largest value the integer columns hold. Not a business rule - a nonsense number is refused with a
# 422 rather than failing in the database with a 500 (the Slice 7D lesson).
LARGEST_WHOLE_NUMBER: Final = 2_147_483_647

RESOURCE_REQUIREMENT_EVENT_CREATED: Final = "ResourceRequirementCreated"
RESOURCE_REQUIREMENT_EVENT_UPDATED: Final = "ResourceRequirementUpdated"
RESOURCE_REQUIREMENT_EVENT_CANCELLED: Final = "ResourceRequirementCancelled"
# 8A core: the status moved because machines were held, replaced or freed, or the requirement changed.
RESOURCE_REQUIREMENT_EVENT_FULFILMENT_CHANGED: Final = "ResourceRequirementFulfilmentChanged"

# Computed on every read of a requirement that is not cancelled. Never a refusal (design section 7).
WARNING_SITE_NOT_RECORDED: Final = "SITE_NOT_RECORDED"
WARNING_OUTSIDE_CONTRACT: Final = "OUTSIDE_CONTRACT"
WARNING_CREW_DIFFERS_FROM_WORK_ORDER: Final = "CREW_DIFFERS_FROM_WORK_ORDER"
WARNING_KEY_CAPABILITY_NOT_STATED: Final = "KEY_CAPABILITY_NOT_STATED"
WARNING_CODES: Final = (
    WARNING_SITE_NOT_RECORDED,
    WARNING_OUTSIDE_CONTRACT,
    WARNING_CREW_DIFFERS_FROM_WORK_ORDER,
    WARNING_KEY_CAPABILITY_NOT_STATED,
)

# The fields a change compares, in the order `changed_fields` lists them. "items" stands for the whole
# item list, capabilities included.
REQUIREMENT_COMPARED_FIELDS: Final = (
    "units_required",
    "required_from",
    "required_to",
    "crew_operators_required",
    "crew_helpers_required",
    "crew_notes",
    "priority_code",
    "planning_notes",
    "items",
)
