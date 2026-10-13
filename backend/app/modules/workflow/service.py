from __future__ import annotations

from sqlalchemy.orm import Session

from app.modules.workflow.repository import list_workflow_modules, list_workflow_statuses
from app.modules.workflow.schemas import WorkflowStatusSummary


def get_workflow_statuses(
    db: Session,
    *,
    module: str | None = None,
    active_only: bool = True,
) -> list[WorkflowStatusSummary]:
    return list_workflow_statuses(db, module=module, active_only=active_only)


def get_workflow_modules(db: Session, *, active_only: bool = True) -> list[str]:
    return list_workflow_modules(db, active_only=active_only)