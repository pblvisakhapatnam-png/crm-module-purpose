from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.modules.opportunities.contract import OPPORTUNITY_TABLE, OPPORTUNITY_WORKFLOW_MODULE
from app.modules.opportunities.schemas import OpportunityResponse


OPPORTUNITY_SELECT_COLUMNS = """
    o.opportunity_public_id AS public_id,
    o.opportunity_name,
    o.opportunity_source,
    o.source_reference,
    bp.business_party_public_id AS account_public_id,
    l.lead_public_id AS source_lead_public_id,
    o.customer_requirement_summary,
    o.estimated_value,
    o.expected_close_date,
    o.opportunity_status_code,
    o.owner_user_public_id,
    opportunity_owner.display_name AS owner_display_name,
    o.created_by,
    opportunity_creator.display_name AS created_by_display_name,
    o.created_at,
    o.updated_at
"""

# Read-only display names for the owner/creator ids, resolved in the same query so a list stays one
# round trip. LEFT JOINs, following QUOTE_DOCUMENT_ACTOR_JOINS in the commercial_offers repository:
# an Opportunity whose id matches no app_user row still lists, with a NULL name.
OPPORTUNITY_ACTOR_JOINS = """
    LEFT JOIN app_user opportunity_owner ON opportunity_owner.public_id = o.owner_user_public_id
    LEFT JOIN app_user opportunity_creator ON opportunity_creator.public_id = o.created_by
"""

OPPORTUNITY_UPDATE_COLUMNS = (
    "opportunity_name",
    "opportunity_source",
    "source_reference",
    "customer_requirement_summary",
    "estimated_value",
    "expected_close_date",
    "opportunity_status_code",
    "owner_user_public_id",
)


def _row_mapping(row: Any) -> Any:
    return row._mapping if hasattr(row, "_mapping") else row


def _row_to_opportunity(row: Any) -> OpportunityResponse:
    data = _row_mapping(row)
    return OpportunityResponse(
        public_id=data["public_id"],
        opportunity_name=data["opportunity_name"],
        opportunity_source=data["opportunity_source"],
        source_reference=data.get("source_reference"),
        account_public_id=data.get("account_public_id"),
        source_lead_public_id=data.get("source_lead_public_id"),
        customer_requirement_summary=data.get("customer_requirement_summary"),
        estimated_value=data.get("estimated_value"),
        expected_close_date=data.get("expected_close_date"),
        opportunity_status_code=data["opportunity_status_code"],
        owner_user_public_id=data.get("owner_user_public_id"),
        owner_display_name=data.get("owner_display_name"),
        created_by=data.get("created_by"),
        created_by_display_name=data.get("created_by_display_name"),
        created_at=data["created_at"],
        updated_at=data["updated_at"],
    )


def active_opportunity_status_exists(db: Session, status_code: str) -> bool:
    exists = db.execute(
        text(
            """
            SELECT 1
            FROM workflow_status
            WHERE module = :module
              AND status_code = :status_code
              AND is_active IS TRUE
            """
        ),
        {"module": OPPORTUNITY_WORKFLOW_MODULE, "status_code": status_code},
    ).scalar()
    return exists == 1


def insert_opportunity(
    db: Session,
    *,
    public_id: str,
    values: dict[str, Any],
) -> OpportunityResponse:
    db.execute(
        text(
            f"""
            INSERT INTO {OPPORTUNITY_TABLE} (
                opportunity_public_id,
                opportunity_name,
                opportunity_source,
                source_reference,
                business_party_id,
                source_lead_id,
                customer_requirement_summary,
                estimated_value,
                expected_close_date,
                opportunity_status_code,
                owner_user_public_id,
                created_by,
                created_at,
                updated_at
            ) VALUES (
                :opportunity_public_id,
                :opportunity_name,
                :opportunity_source,
                :source_reference,
                :business_party_id,
                :source_lead_id,
                :customer_requirement_summary,
                :estimated_value,
                :expected_close_date,
                :opportunity_status_code,
                :owner_user_public_id,
                :created_by,
                CURRENT_TIMESTAMP,
                CURRENT_TIMESTAMP
            )
            """
        ),
        {"opportunity_public_id": public_id, **values},
    )
    opportunity = get_opportunity_by_public_id(db, public_id)
    if opportunity is None:
        raise RuntimeError("Inserted Opportunity could not be reloaded.")
    return opportunity


def update_opportunity_by_public_id(
    db: Session,
    *,
    public_id: str,
    values: dict[str, Any],
) -> OpportunityResponse:
    assignments = [f"{column} = :{column}" for column in OPPORTUNITY_UPDATE_COLUMNS if column in values]
    if not assignments:
        opportunity = get_opportunity_by_public_id(db, public_id)
        if opportunity is None:
            raise RuntimeError("Opportunity could not be reloaded.")
        return opportunity

    assignments.append("updated_at = CURRENT_TIMESTAMP")
    db.execute(
        text(
            f"""
            UPDATE {OPPORTUNITY_TABLE}
            SET {', '.join(assignments)}
            WHERE opportunity_public_id = :public_id
            """
        ),
        {"public_id": public_id, **values},
    )
    opportunity = get_opportunity_by_public_id(db, public_id)
    if opportunity is None:
        raise RuntimeError("Updated Opportunity could not be reloaded.")
    return opportunity


def get_opportunity_account_repair_context(db: Session, public_id: str) -> dict[str, Any] | None:
    row = db.execute(
        text(
            f"""
            SELECT
                o.id AS opportunity_id,
                o.opportunity_public_id,
                o.opportunity_name,
                o.opportunity_status_code,
                o.business_party_id,
                bp.business_party_public_id AS account_public_id
            FROM {OPPORTUNITY_TABLE} o
            LEFT JOIN business_party bp ON bp.id = o.business_party_id
            WHERE o.opportunity_public_id = :public_id
            LIMIT 1
            """
        ),
        {"public_id": public_id},
    ).first()
    return dict(_row_mapping(row)) if row else None


def link_opportunity_business_party_if_unlinked(
    db: Session,
    *,
    opportunity_public_id: str,
    business_party_id: int,
) -> OpportunityResponse | None:
    result = db.execute(
        text(
            f"""
            UPDATE {OPPORTUNITY_TABLE}
            SET business_party_id = :business_party_id,
                updated_at = CURRENT_TIMESTAMP
            WHERE opportunity_public_id = :opportunity_public_id
              AND business_party_id IS NULL
            """
        ),
        {
            "opportunity_public_id": opportunity_public_id,
            "business_party_id": business_party_id,
        },
    )
    if result.rowcount != 1:
        return None
    return get_opportunity_by_public_id(db, opportunity_public_id)


def get_opportunity_by_public_id(db: Session, public_id: str) -> OpportunityResponse | None:
    row = db.execute(
        text(
            f"""
            SELECT
                {OPPORTUNITY_SELECT_COLUMNS}
            FROM {OPPORTUNITY_TABLE} o
            LEFT JOIN business_party bp ON bp.id = o.business_party_id
            LEFT JOIN crm_lead l ON l.id = o.source_lead_id
            {OPPORTUNITY_ACTOR_JOINS}
            WHERE o.opportunity_public_id = :public_id
            """
        ),
        {"public_id": public_id},
    ).first()
    return _row_to_opportunity(row) if row else None


def list_recent_opportunities(
    db: Session,
    *,
    limit: int = 20,
    offset: int = 0,
    status_code: str | None = None,
    opportunity_source: str | None = None,
) -> list[OpportunityResponse]:
    safe_limit = max(1, min(limit, 100))
    safe_offset = max(0, offset)
    filters: list[str] = []
    params: dict[str, Any] = {}

    if status_code:
        filters.append("o.opportunity_status_code = :status_code")
        params["status_code"] = status_code

    if opportunity_source:
        filters.append("o.opportunity_source = :opportunity_source")
        params["opportunity_source"] = opportunity_source

    where_clause = ""
    if filters:
        where_clause = "WHERE " + " AND ".join(filters)

    rows = db.execute(
        text(
            f"""
            SELECT
                {OPPORTUNITY_SELECT_COLUMNS}
            FROM {OPPORTUNITY_TABLE} o
            LEFT JOIN business_party bp ON bp.id = o.business_party_id
            LEFT JOIN crm_lead l ON l.id = o.source_lead_id
            {OPPORTUNITY_ACTOR_JOINS}
            {where_clause}
            ORDER BY o.created_at DESC, o.id DESC
            LIMIT {safe_limit} OFFSET {safe_offset}
            """
        ),
        params,
    ).fetchall()
    return [_row_to_opportunity(row) for row in rows]



def get_opportunity_by_source_lead_id(db: Session, source_lead_id: int) -> OpportunityResponse | None:
    row = db.execute(
        text(
            f"""
            SELECT
                {OPPORTUNITY_SELECT_COLUMNS}
            FROM {OPPORTUNITY_TABLE} o
            LEFT JOIN business_party bp ON bp.id = o.business_party_id
            LEFT JOIN crm_lead l ON l.id = o.source_lead_id
            {OPPORTUNITY_ACTOR_JOINS}
            WHERE o.source_lead_id = :source_lead_id
            """
        ),
        {"source_lead_id": source_lead_id},
    ).first()
    return _row_to_opportunity(row) if row else None
