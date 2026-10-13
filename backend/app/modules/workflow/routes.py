from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.identity.dependencies import get_current_user
from app.modules.identity.schemas import AuthUser
from app.modules.workflow.schemas import WorkflowStatusSummary
from app.modules.workflow.service import get_workflow_modules, get_workflow_statuses

router = APIRouter(prefix="/api/workflow", tags=["workflow"])


@router.get("/statuses", response_model=list[WorkflowStatusSummary])
def workflow_statuses(
    module: str | None = Query(default=None, min_length=1, max_length=100),
    active_only: bool = True,
    db: Session = Depends(get_db),
    _: AuthUser = Depends(get_current_user),
) -> list[WorkflowStatusSummary]:
    return get_workflow_statuses(db, module=module, active_only=active_only)


@router.get("/modules", response_model=list[str])
def workflow_modules(
    active_only: bool = True,
    db: Session = Depends(get_db),
    _: AuthUser = Depends(get_current_user),
) -> list[str]:
    return get_workflow_modules(db, active_only=active_only)