"""Reporting contract: report identifiers and status groupings.

The set of offer statuses that are not "open" is imported from the Commercial
Offer contract, so it follows that module. Two status values are restated as
literals instead: `ACCEPTED` here and `SUBMITTED` in `repository.py`. A change to
either in the Commercial Offer module must be made here too (the Reports
contract, `docs/agent/contracts/reports-contract.md`, "When a source changes").
"""

from __future__ import annotations

from app.modules.commercial_offers.contract import (
    COMMERCIAL_OFFER_GENERIC_UPDATE_CANNOT_LEAVE_STATUSES,
)

REPORT_PIPELINE = "PIPELINE"
REPORT_OPEN_OFFERS = "OPEN_OFFERS"
REPORT_ACCEPTED_OFFERS = "ACCEPTED_OFFERS"
REPORT_WORK_ORDER_HANDOFF = "WORK_ORDER_HANDOFF"

ALL_REPORT_CODES: tuple[str, ...] = (
    REPORT_PIPELINE,
    REPORT_OPEN_OFFERS,
    REPORT_ACCEPTED_OFFERS,
    REPORT_WORK_ORDER_HANDOFF,
)

# An offer is "open" when it is still commercially in play: neither accepted
# nor in a terminal or superseded state. This is exactly the set the Commercial Offer module
# already treats as unreachable-from by generic update - ACCEPTED, WITHDRAWN, REJECTED, CLOSED,
# REVISED and ABANDONED - so the definition is derived, not invented.
COMMERCIAL_OFFER_OPEN_EXCLUDED_STATUSES: tuple[str, ...] = tuple(
    COMMERCIAL_OFFER_GENERIC_UPDATE_CANNOT_LEAVE_STATUSES
)

COMMERCIAL_OFFER_ACCEPTED_STATUS = "ACCEPTED"

# Ageing buckets, in days, applied to an open offer's effective date
# (offer_date where recorded, otherwise the created date).
OFFER_AGEING_BUCKETS: tuple[tuple[str, int | None, int | None], ...] = (
    ("0-7 days", None, 7),
    ("8-30 days", 8, 30),
    ("31-90 days", 31, 90),
    ("Over 90 days", 91, None),
)

# Horizon, in days, for the "expiring soon" count on open offers.
OFFER_EXPIRY_HORIZON_DAYS = 30

# Default and maximum number of rows returned by the handoff detail listing.
HANDOFF_RECENT_DEFAULT_LIMIT = 20
HANDOFF_RECENT_MAX_LIMIT = 100
