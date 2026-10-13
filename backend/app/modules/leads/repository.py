from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.modules.leads.contract import LEAD_ACTIVITY_TABLE, LEAD_TABLE, LEAD_WORKFLOW_MODULE
from app.modules.leads.schemas import LeadActivityResponse, LeadResponse


# Qualified with the table name because LEAD_ACTOR_JOINS brings app_user into the same FROM clause
# (app_user also has id, created_at and updated_at), and because the correlated subqueries below
# already reference crm_lead by name.
LEAD_SELECT_COLUMNS = """
    crm_lead.lead_public_id AS public_id,
    crm_lead.lead_source,
    crm_lead.source_reference,
    crm_lead.company_name,
    crm_lead.contact_name,
    crm_lead.contact_phone,
    crm_lead.contact_email,
    crm_lead.requirement_summary,
    crm_lead.lead_status_code,
    crm_lead.assigned_to_user_public_id,
    lead_assignee.display_name AS assigned_to_display_name,
    crm_lead.qualification_decision_notes,
    crm_lead.qualification_reason,
    crm_lead.qualification_decided_by,
    crm_lead.qualification_decided_at,
    (
        SELECT bp.business_party_public_id
        FROM crm_opportunity o
        INNER JOIN business_party bp ON bp.id = o.business_party_id
        WHERE o.source_lead_id = crm_lead.id
        ORDER BY o.created_at DESC, o.id DESC
        LIMIT 1
    ) AS converted_account_public_id,
    (
        SELECT o.opportunity_public_id
        FROM crm_opportunity o
        WHERE o.source_lead_id = crm_lead.id
        ORDER BY o.created_at DESC, o.id DESC
        LIMIT 1
    ) AS converted_opportunity_public_id,
    crm_lead.created_by,
    lead_creator.display_name AS created_by_display_name,
    crm_lead.created_at,
    crm_lead.updated_at
"""

# Read-only display names for the assignee/creator ids, resolved in the same query so a list stays
# one round trip. LEFT JOINs, following QUOTE_DOCUMENT_ACTOR_JOINS in the commercial_offers
# repository: a Lead whose id matches no app_user row still lists, with a NULL name.
LEAD_ACTOR_JOINS = """
    LEFT JOIN app_user lead_assignee ON lead_assignee.public_id = crm_lead.assigned_to_user_public_id
    LEFT JOIN app_user lead_creator ON lead_creator.public_id = crm_lead.created_by
"""

LEAD_UPDATE_COLUMNS = (
    "lead_source",
    "source_reference",
    "company_name",
    "contact_name",
    "contact_phone",
    "contact_email",
    "requirement_summary",
    "lead_status_code",
    "assigned_to_user_public_id",
)

LEAD_QUALIFICATION_UPDATE_COLUMNS = (
    "lead_status_code",
    "qualification_decision_notes",
    "qualification_reason",
    "qualification_decided_by",
    "qualification_decided_at",
)

LEAD_CONVERSION_UPDATE_COLUMNS = (
    "lead_status_code",
)


def _row_mapping(row: Any) -> Any:
    return row._mapping if hasattr(row, "_mapping") else row


def _row_to_lead(row: Any) -> LeadResponse:
    data = _row_mapping(row)
    return LeadResponse(
        public_id=data["public_id"],
        lead_source=data["lead_source"],
        source_reference=data.get("source_reference"),
        company_name=data["company_name"],
        contact_name=data.get("contact_name"),
        contact_phone=data.get("contact_phone"),
        contact_email=data.get("contact_email"),
        requirement_summary=data.get("requirement_summary"),
        lead_status_code=data["lead_status_code"],
        assigned_to_user_public_id=data.get("assigned_to_user_public_id"),
        assigned_to_display_name=data.get("assigned_to_display_name"),
        qualification_decision_notes=data.get("qualification_decision_notes"),
        qualification_reason=data.get("qualification_reason"),
        qualification_decided_by=data.get("qualification_decided_by"),
        qualification_decided_at=data.get("qualification_decided_at"),
        converted_account_public_id=data.get("converted_account_public_id"),
        converted_opportunity_public_id=data.get("converted_opportunity_public_id"),
        created_by=data.get("created_by") or data.get("activity_created_by"),
        created_by_display_name=data.get("created_by_display_name"),
        created_at=data.get("created_at") or data.get("activity_created_at"),
        updated_at=data["updated_at"],
    )


def _row_to_lead_activity(row: Any) -> LeadActivityResponse:
    data = _row_mapping(row)
    # Some explicit activity queries used activity_created_by/activity_created_at
    # aliases to avoid ambiguity with Lead columns. Normalize both alias styles
    # here so insert reloads, direct gets and list queries all map consistently.
    created_by = data.get("created_by") or data.get("activity_created_by")
    created_at = data.get("created_at") or data.get("activity_created_at")
    return LeadActivityResponse(
        public_id=data["public_id"],
        lead_public_id=data["lead_public_id"],
        activity_type=data["activity_type"],
        activity_at=data["activity_at"],
        notes=data.get("notes"),
        outcome=data.get("outcome"),
        next_follow_up_at=data.get("next_follow_up_at"),
        created_by=created_by,
        created_at=created_at,
    )


def active_lead_status_exists(db: Session, status_code: str) -> bool:
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
        {"module": LEAD_WORKFLOW_MODULE, "status_code": status_code},
    ).scalar()
    return exists == 1


def get_lead_id_by_public_id(db: Session, public_id: str) -> int | None:
    value = db.execute(
        text(
            f"""
            SELECT id
            FROM {LEAD_TABLE}
            WHERE lead_public_id = :public_id
            """
        ),
        {"public_id": public_id},
    ).scalar()
    return int(value) if value is not None else None


def lock_lead_row(db: Session, public_id: str) -> int | None:
    """Take the Lead's row lock for the rest of the transaction; its id, or None when there is no such Lead."""
    value = db.execute(
        text(
            f"""
            SELECT id
            FROM {LEAD_TABLE}
            WHERE lead_public_id = :public_id
            FOR UPDATE
            """
        ),
        {"public_id": public_id},
    ).scalar()
    return int(value) if value is not None else None


def insert_lead(
    db: Session,
    *,
    public_id: str,
    values: dict[str, Any],
) -> LeadResponse:
    db.execute(
        text(
            f"""
            INSERT INTO {LEAD_TABLE} (
                lead_public_id,
                lead_source,
                source_reference,
                company_name,
                contact_name,
                contact_phone,
                contact_email,
                requirement_summary,
                lead_status_code,
                assigned_to_user_public_id,
                created_by,
                created_at,
                updated_at
            ) VALUES (
                :lead_public_id,
                :lead_source,
                :source_reference,
                :company_name,
                :contact_name,
                :contact_phone,
                :contact_email,
                :requirement_summary,
                :lead_status_code,
                :assigned_to_user_public_id,
                :created_by,
                CURRENT_TIMESTAMP,
                CURRENT_TIMESTAMP
            )
            """
        ),
        {"lead_public_id": public_id, **values},
    )
    lead = get_lead_by_public_id(db, public_id)
    if lead is None:
        raise RuntimeError("Inserted Lead could not be reloaded.")
    return lead


def update_lead_by_public_id(
    db: Session,
    *,
    public_id: str,
    values: dict[str, Any],
) -> LeadResponse:
    assignments = [f"{column} = :{column}" for column in LEAD_UPDATE_COLUMNS if column in values]
    if not assignments:
        lead = get_lead_by_public_id(db, public_id)
        if lead is None:
            raise RuntimeError("Lead could not be reloaded.")
        return lead

    assignments.append("updated_at = CURRENT_TIMESTAMP")
    db.execute(
        text(
            f"""
            UPDATE {LEAD_TABLE}
            SET {', '.join(assignments)}
            WHERE lead_public_id = :public_id
            """
        ),
        {"public_id": public_id, **values},
    )
    lead = get_lead_by_public_id(db, public_id)
    if lead is None:
        raise RuntimeError("Updated Lead could not be reloaded.")
    return lead


def update_lead_qualification_by_public_id(
    db: Session,
    *,
    public_id: str,
    values: dict[str, Any],
) -> LeadResponse:
    assignments = [f"{column} = :{column}" for column in LEAD_QUALIFICATION_UPDATE_COLUMNS if column in values]
    if not assignments:
        lead = get_lead_by_public_id(db, public_id)
        if lead is None:
            raise RuntimeError("Lead could not be reloaded.")
        return lead

    assignments.append("updated_at = CURRENT_TIMESTAMP")
    db.execute(
        text(
            f"""
            UPDATE {LEAD_TABLE}
            SET {', '.join(assignments)}
            WHERE lead_public_id = :public_id
            """
        ),
        {"public_id": public_id, **values},
    )
    lead = get_lead_by_public_id(db, public_id)
    if lead is None:
        raise RuntimeError("Updated Lead qualification decision could not be reloaded.")
    return lead


def update_lead_conversion_by_public_id(
    db: Session,
    *,
    public_id: str,
    values: dict[str, Any],
) -> LeadResponse:
    assignments = [f"{column} = :{column}" for column in LEAD_CONVERSION_UPDATE_COLUMNS if column in values]
    if not assignments:
        lead = get_lead_by_public_id(db, public_id)
        if lead is None:
            raise RuntimeError("Lead could not be reloaded.")
        return lead

    assignments.append("updated_at = CURRENT_TIMESTAMP")
    db.execute(
        text(
            f"""
            UPDATE {LEAD_TABLE}
            SET {', '.join(assignments)}
            WHERE lead_public_id = :public_id
            """
        ),
        {"public_id": public_id, **values},
    )
    lead = get_lead_by_public_id(db, public_id)
    if lead is None:
        raise RuntimeError("Converted Lead could not be reloaded.")
    return lead


def get_lead_by_public_id(db: Session, public_id: str) -> LeadResponse | None:
    row = db.execute(
        text(
            f"""
            SELECT
                {LEAD_SELECT_COLUMNS}
            FROM {LEAD_TABLE}
            {LEAD_ACTOR_JOINS}
            WHERE crm_lead.lead_public_id = :public_id
            """
        ),
        {"public_id": public_id},
    ).first()
    return _row_to_lead(row) if row else None


def list_recent_leads(
    db: Session,
    *,
    limit: int = 20,
    offset: int = 0,
    status_code: str | None = None,
    lead_source: str | None = None,
) -> list[LeadResponse]:
    safe_limit = max(1, min(limit, 100))
    safe_offset = max(0, offset)
    filters: list[str] = []
    params: dict[str, Any] = {}

    if status_code:
        filters.append("crm_lead.lead_status_code = :status_code")
        params["status_code"] = status_code

    if lead_source:
        filters.append("crm_lead.lead_source = :lead_source")
        params["lead_source"] = lead_source

    where_clause = ""
    if filters:
        where_clause = "WHERE " + " AND ".join(filters)

    rows = db.execute(
        text(
            f"""
            SELECT
                {LEAD_SELECT_COLUMNS}
            FROM {LEAD_TABLE}
            {LEAD_ACTOR_JOINS}
            {where_clause}
            ORDER BY crm_lead.created_at DESC, crm_lead.id DESC
            LIMIT {safe_limit} OFFSET {safe_offset}
            """
        ),
        params,
    ).fetchall()
    return [_row_to_lead(row) for row in rows]


def insert_lead_activity(
    db: Session,
    *,
    public_id: str,
    lead_id: int,
    values: dict[str, Any],
) -> LeadActivityResponse:
    db.execute(
        text(
            f"""
            INSERT INTO {LEAD_ACTIVITY_TABLE} (
                activity_public_id,
                lead_id,
                activity_type,
                activity_at,
                notes,
                outcome,
                next_follow_up_at,
                created_by,
                created_at
            ) VALUES (
                :activity_public_id,
                :lead_id,
                :activity_type,
                :activity_at,
                :notes,
                :outcome,
                :next_follow_up_at,
                :created_by,
                CURRENT_TIMESTAMP
            )
            """
        ),
        {"activity_public_id": public_id, "lead_id": lead_id, **values},
    )
    activity = get_lead_activity_by_public_id(db, public_id)
    if activity is None:
        raise RuntimeError("Inserted Lead Activity could not be reloaded.")
    return activity


def get_lead_activity_by_public_id(db: Session, public_id: str) -> LeadActivityResponse | None:
    row = db.execute(
        text(
            f"""
            SELECT
                a.activity_public_id AS public_id,
                l.lead_public_id,
                a.activity_type,
                a.activity_at,
                a.notes,
                a.outcome,
                a.next_follow_up_at,
                a.created_by AS created_by,
                a.created_at AS created_at
            FROM {LEAD_ACTIVITY_TABLE} a
            INNER JOIN {LEAD_TABLE} l ON l.id = a.lead_id
            WHERE a.activity_public_id = :public_id
            """
        ),
        {"public_id": public_id},
    ).first()
    return _row_to_lead_activity(row) if row else None


def list_lead_activities(
    db: Session,
    *,
    lead_public_id: str,
    limit: int = 20,
) -> list[LeadActivityResponse]:
    safe_limit = max(1, min(limit, 100))
    rows = db.execute(
        text(
            f"""
            SELECT
                a.activity_public_id AS public_id,
                l.lead_public_id,
                a.activity_type,
                a.activity_at,
                a.notes,
                a.outcome,
                a.next_follow_up_at,
                a.created_by AS created_by,
                a.created_at AS created_at
            FROM {LEAD_ACTIVITY_TABLE} a
            INNER JOIN {LEAD_TABLE} l ON l.id = a.lead_id
            WHERE l.lead_public_id = :lead_public_id
            ORDER BY a.activity_at DESC, a.created_at DESC, a.id DESC
            LIMIT {safe_limit}
            """
        ),
        {"lead_public_id": lead_public_id},
    ).fetchall()
    return [_row_to_lead_activity(row) for row in rows]


