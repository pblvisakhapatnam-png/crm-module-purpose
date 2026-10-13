from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.modules.terms_and_conditions.contract import TC_CLAUSE_LIBRARY_TABLE
from app.modules.terms_and_conditions.schemas import TermsAndConditionsClauseResponse


TC_CLAUSE_SELECT_COLUMNS = """
    public_id,
    clause_id,
    business_line,
    clause_category,
    source_clause_number,
    title,
    clause_text,
    mandatory_default,
    risk_category,
    applies_to_header,
    applies_to_line,
    requires_approval_if_omitted,
    requires_approval_if_modified,
    active,
    source_reference,
    created_at,
    updated_at
"""


def _row_mapping(row: Any) -> Any:
    return row._mapping if hasattr(row, "_mapping") else row


def _row_to_clause(row: Any) -> TermsAndConditionsClauseResponse:
    data = _row_mapping(row)
    return TermsAndConditionsClauseResponse(
        public_id=data["public_id"],
        clause_id=data["clause_id"],
        business_line=data["business_line"],
        clause_category=data["clause_category"],
        source_clause_number=data.get("source_clause_number"),
        title=data["title"],
        clause_text=data["clause_text"],
        mandatory_default=bool(data["mandatory_default"]),
        risk_category=data.get("risk_category"),
        applies_to_header=bool(data["applies_to_header"]),
        applies_to_line=bool(data["applies_to_line"]),
        requires_approval_if_omitted=bool(data["requires_approval_if_omitted"]),
        requires_approval_if_modified=bool(data["requires_approval_if_modified"]),
        active=bool(data["active"]),
        source_reference=data.get("source_reference"),
        created_at=data["created_at"],
        updated_at=data["updated_at"],
    )


def list_tc_clauses(
    db: Session,
    *,
    limit: int = 50,
    offset: int = 0,
    business_line: str | None = None,
    clause_category: str | None = None,
    active: bool | None = None,
    applies_to_header: bool | None = None,
    applies_to_line: bool | None = None,
    search: str | None = None,
) -> list[TermsAndConditionsClauseResponse]:
    safe_limit = max(1, min(limit, 100))
    safe_offset = max(0, offset)
    filters: list[str] = []
    params: dict[str, object] = {}

    if business_line:
        filters.append("business_line = :business_line")
        params["business_line"] = business_line

    if clause_category:
        filters.append("clause_category = :clause_category")
        params["clause_category"] = clause_category

    if active is not None:
        filters.append("active = :active")
        params["active"] = bool(active)

    if applies_to_header is not None:
        filters.append("applies_to_header = :applies_to_header")
        params["applies_to_header"] = bool(applies_to_header)

    if applies_to_line is not None:
        filters.append("applies_to_line = :applies_to_line")
        params["applies_to_line"] = bool(applies_to_line)

    if search:
        filters.append(
            """
            (
                LOWER(clause_id) LIKE :search
                OR LOWER(title) LIKE :search
                OR LOWER(clause_text) LIKE :search
            )
            """
        )
        params["search"] = f"%{search.lower()}%"

    where_clause = ""
    if filters:
        where_clause = "WHERE " + " AND ".join(filters)

    rows = db.execute(
        text(
            f"""
            SELECT
                {TC_CLAUSE_SELECT_COLUMNS}
            FROM {TC_CLAUSE_LIBRARY_TABLE}
            {where_clause}
            ORDER BY business_line, clause_id
            LIMIT {safe_limit} OFFSET {safe_offset}
            """
        ),
        params,
    ).fetchall()
    return [_row_to_clause(row) for row in rows]


def get_tc_clause_by_public_id(db: Session, public_id: str) -> TermsAndConditionsClauseResponse | None:
    row = db.execute(
        text(
            f"""
            SELECT
                {TC_CLAUSE_SELECT_COLUMNS}
            FROM {TC_CLAUSE_LIBRARY_TABLE}
            WHERE public_id = :public_id
            """
        ),
        {"public_id": public_id},
    ).first()
    return _row_to_clause(row) if row else None

