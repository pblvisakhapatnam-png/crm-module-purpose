"""Resource Assignment codes, reasons, warnings and events (8A core).

Design: docs/agent/slices/8a-core-equipment-allocation.md; the API is
docs/agent/contracts/resource-assignment-api-contract.md. The code says assignment, `RPA-001`'s word; the screens
say allocation, the word Eligibility's answers already use ("can be allocated").
"""

from __future__ import annotations

from typing import Final

RESOURCE_ASSIGNMENT_MODULE_NAME: Final = "resource_assignments"
RESOURCE_ASSIGNMENT_RECORD_TYPE: Final = "resource_assignment"
# What asked Eligibility for a stored decision (`record_decision`'s requested_for_type).
DECISION_FOR_ASSIGNMENT: Final = "resource_assignment"
DECISION_FOR_KIT_LINE: Final = "resource_assignment_kit"

# Before the Work Order is released, an allocation holds the machine (owner, Q1, 28 September 2026). Replaced
# and freed ("released") allocations stay as history. ALLOCATED (firm, 7B) and COMPLETED (8E) are reserved and
# not accepted by the database yet.
STATUS_HELD: Final = "HELD"
STATUS_REPLACED: Final = "REPLACED"
STATUS_RELEASED: Final = "RELEASED"
STATUS_CODES: Final = (STATUS_HELD, STATUS_REPLACED, STATUS_RELEASED)
ACTIVE_STATUS_CODES: Final = (STATUS_HELD,)

REPLACEMENT_REASON_CODES: Final = ("BREAKDOWN", "COMPLIANCE", "CUSTOMER_REQUEST", "PLANNING", "OTHER")
# The reasons a user may choose when freeing a machine; REQUIREMENT_CANCELLED is set only by a requirement's
# cancellation, never chosen.
RELEASE_RECORDED_BY_MISTAKE: Final = "RECORDED_BY_MISTAKE"
RELEASE_REASON_CODES: Final = ("NOT_NEEDED", RELEASE_RECORDED_BY_MISTAKE, "MACHINE_UNAVAILABLE", "OTHER")
RELEASE_REQUIREMENT_CANCELLED: Final = "REQUIREMENT_CANCELLED"
REASON_OTHER: Final = "OTHER"

BILLING_CYCLE_WEEKLY: Final = "WEEKLY"
BILLING_CYCLE_MONTHLY: Final = "MONTHLY"
BILLING_CYCLE_CODES: Final = (BILLING_CYCLE_WEEKLY, BILLING_CYCLE_MONTHLY)

KIT_LINE_LISTED: Final = "LISTED"
KIT_LINE_REMOVED: Final = "REMOVED"

# Today's answer on a held allocation, the worst of the machine's and its listed kit's (design section 6.4).
COMPLIANCE_CLEAR: Final = "CLEAR"
COMPLIANCE_WARNING: Final = "WARNING"
COMPLIANCE_BLOCKED: Final = "BLOCKED"
COMPLIANCE_SITE_UNKNOWN: Final = "SITE_UNKNOWN"

# What stops the site being judged (design section 6.1).
SITE_NOT_RECORDED: Final = "SITE_NOT_RECORDED"
SITE_STATE_NOT_RECOGNISED: Final = "STATE_NOT_RECOGNISED"
SITE_CENTRAL_NOT_ANSWERED: Final = "CENTRAL_NOT_ANSWERED"

# Why a machine of the requirement's class is not offered (design section 6.2).
LEFT_OUT_TYPE_UNKNOWN: Final = "TYPE_UNKNOWN"
LEFT_OUT_TYPE_DIFFERS: Final = "TYPE_DIFFERS"
LEFT_OUT_RATING_UNKNOWN: Final = "RATING_UNKNOWN"
LEFT_OUT_BELOW_REQUIREMENT: Final = "BELOW_REQUIREMENT"
LEFT_OUT_CLASS_DIFFERS: Final = "CLASS_DIFFERS"
# Counted and shown on the finder; a machine of another type is simply not what was asked for.
LEFT_OUT_COUNTED: Final = (LEFT_OUT_TYPE_UNKNOWN, LEFT_OUT_RATING_UNKNOWN, LEFT_OUT_BELOW_REQUIREMENT)

# Computed on every read of a held allocation; advisory only (design section 6.13).
WARNING_SITE_CHANGED: Final = "SITE_CHANGED"
WARNING_OUTSIDE_REQUIREMENT: Final = "OUTSIDE_REQUIREMENT"
WARNING_NO_LONGER_MATCHES: Final = "NO_LONGER_MATCHES"
WARNING_UNIT_NOT_REQUIRED: Final = "UNIT_NOT_REQUIRED"
WARNING_OUTSIDE_CONTRACT: Final = "OUTSIDE_CONTRACT"
WARNING_BILLING_CYCLE_NOT_STATED: Final = "BILLING_CYCLE_NOT_STATED"
WARNING_KIT_DOES_NOT_FIT: Final = "KIT_DOES_NOT_FIT"
WARNING_ANSWER_CHANGED: Final = "ANSWER_CHANGED"

# The allocations list's preset: held allocations starting within this many days (design section 6.4).
STARTING_SOON_DAYS: Final = 15

NOTES_MAX_LENGTH: Final = 2000
TRIP_NOTE_MAX_LENGTH: Final = 500
REQUEST_KEY_MAX_LENGTH: Final = 100
KIT_PIECES_PER_REQUEST: Final = 50
LARGEST_WHOLE_NUMBER: Final = 2_147_483_647

EVENT_HELD: Final = "RESOURCE_ASSIGNMENT_HELD"
EVENT_REPLACED: Final = "RESOURCE_ASSIGNMENT_REPLACED"
EVENT_RELEASED: Final = "RESOURCE_ASSIGNMENT_RELEASED"
EVENT_DATES_CHANGED: Final = "RESOURCE_ASSIGNMENT_DATES_CHANGED"
EVENT_CHECKED: Final = "RESOURCE_ASSIGNMENT_CHECKED"
EVENT_BILLING_CYCLE_SET: Final = "RESOURCE_ASSIGNMENT_BILLING_CYCLE_SET"
EVENT_TRIP_ADDED: Final = "RESOURCE_ASSIGNMENT_TRIP_ADDED"
EVENT_TRIP_NOTE_CHANGED: Final = "RESOURCE_ASSIGNMENT_TRIP_NOTE_CHANGED"
EVENT_KIT_LISTED: Final = "RESOURCE_ASSIGNMENT_KIT_LISTED"
EVENT_KIT_REMOVED: Final = "RESOURCE_ASSIGNMENT_KIT_REMOVED"

# The kinds of request a request key can make, once across all three (8A-R2-002): resource_assignment_request.
REQUEST_ALLOCATE: Final = "ALLOCATE"
REQUEST_REPLACE: Final = "REPLACE"
REQUEST_KIT: Final = "KIT"
