from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.authorization.contract import (
    COMMERCIAL_OFFER_READ as COMMERCIAL_OFFER_READ_PERMISSION,
    OPPORTUNITY_READ as OPPORTUNITY_READ_PERMISSION,
    WORK_ORDER_READ as WORK_ORDER_READ_PERMISSION,
)
from app.modules.authorization.dependencies import require_permission
from app.modules.identity.schemas import AuthUser
from app.modules.reports.contract import (
    HANDOFF_RECENT_DEFAULT_LIMIT,
    HANDOFF_RECENT_MAX_LIMIT,
)
from app.modules.reports.schemas import (
    AcceptedOffersReport,
    OpenOffersReport,
    PipelineReport,
    WorkOrderHandoffReport,
)
from app.modules.reports.service import (
    build_accepted_offers_report,
    build_open_offers_report,
    build_pipeline_report,
    build_work_order_handoff_report,
)

router = APIRouter(prefix="/api/reports", tags=["reports"])

# Authorization note (PF-1A-E1 seam).
#
# These reports deliberately reuse the existing per-module read permissions
# rather than introducing new REPORT_* codes. Two reasons:
#
# 1. It preserves the current effective access matrix exactly. All five
#    business read permissions (ACCOUNT_READ, LEAD_READ, OPPORTUNITY_READ,
#    COMMERCIAL_OFFER_READ, WORK_ORDER_READ) map to the identical six-role
#    set, so no access is widened or narrowed by this slice.
# 2. New permission codes would require an Alembic migration to seed
#    `authz_permission` / `authz_role_permission`, which would put this slice
#    in contention for the single linear migration head.
#
# The pipeline report spans Leads and Opportunities and requests
# OPPORTUNITY_READ. That is safe only while LEAD_READ and OPPORTUNITY_READ
# carry the same role set. `test_reports_api.py` asserts that equality
# directly (`test_lead_and_opportunity_read_have_identical_role_sets`), so
# narrowing either one later fails loudly instead of silently
# leaking Lead counts to a role that may no longer read Leads.


@router.get("/pipeline", response_model=PipelineReport)
def get_pipeline_report(
    db: Session = Depends(get_db),
    _user: AuthUser = Depends(require_permission(OPPORTUNITY_READ_PERMISSION)),
) -> PipelineReport:
    return build_pipeline_report(db)


@router.get("/open-offers", response_model=OpenOffersReport)
def get_open_offers_report(
    db: Session = Depends(get_db),
    _user: AuthUser = Depends(require_permission(COMMERCIAL_OFFER_READ_PERMISSION)),
) -> OpenOffersReport:
    return build_open_offers_report(db)


@router.get("/accepted-offers", response_model=AcceptedOffersReport)
def get_accepted_offers_report(
    db: Session = Depends(get_db),
    _user: AuthUser = Depends(require_permission(COMMERCIAL_OFFER_READ_PERMISSION)),
) -> AcceptedOffersReport:
    return build_accepted_offers_report(db)


@router.get("/work-order-handoff", response_model=WorkOrderHandoffReport)
def get_work_order_handoff_report(
    limit: int = Query(
        default=HANDOFF_RECENT_DEFAULT_LIMIT, ge=1, le=HANDOFF_RECENT_MAX_LIMIT
    ),
    db: Session = Depends(get_db),
    _user: AuthUser = Depends(require_permission(WORK_ORDER_READ_PERMISSION)),
) -> WorkOrderHandoffReport:
    return build_work_order_handoff_report(db, limit)
