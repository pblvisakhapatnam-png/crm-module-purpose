from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.modules.workflow.schemas import WorkflowStatusSummary


def _row_to_summary(row: object) -> WorkflowStatusSummary:
    data = row._mapping
    return WorkflowStatusSummary(
        public_id=data["public_id"],
        module=data["module"],
        status_code=data["status_code"],
        status_name=data["status_name"],
        is_active=bool(data["is_active"]),
        sort_order=int(data["sort_order"]),
    )


def list_workflow_statuses(
    db: Session,
    *,
    module: str | None = None,
    active_only: bool = True,
) -> list[WorkflowStatusSummary]:
    where_clauses: list[str] = []
    params: dict[str, object] = {}

    if module:
        where_clauses.append("module = :module")
        params["module"] = module

    if active_only:
        where_clauses.append("is_active IS TRUE")

    where_sql = ""
    if where_clauses:
        where_sql = "WHERE " + " AND ".join(where_clauses)

    rows = db.execute(
        text(
            f"""
            SELECT public_id, module, status_code, status_name, is_active, sort_order
            FROM workflow_status
            {where_sql}
            ORDER BY module, sort_order, status_name
            """
        ),
        params,
    ).all()
    return [_row_to_summary(row) for row in rows]


def list_workflow_modules(db: Session, *, active_only: bool = True) -> list[str]:
    where_sql = "WHERE is_active IS TRUE" if active_only else ""
    rows = db.execute(
        text(
            f"""
            SELECT DISTINCT module
            FROM workflow_status
            {where_sql}
            ORDER BY module
            """
        )
    ).scalars().all()
    return [str(row) for row in rows]