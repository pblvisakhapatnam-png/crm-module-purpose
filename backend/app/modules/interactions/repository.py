"""Interaction repository - raw SQL against the `interaction` / `interaction_participant`
tables, following the pattern already used by leads/opportunities/commercial_offers
repositories in this codebase rather than SQLAlchemy ORM models.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.modules.interactions.contract import (
    INTERACTION_PARTICIPANT_TABLE,
    INTERACTION_TABLE,
    LINKED_RECORD_EXISTENCE_LOOKUP,
)


def linked_record_exists(db: Session, *, linked_record_type: str, linked_record_public_id: str) -> bool:
    """Prove the polymorphic link target actually exists.

    A direct, minimal, read-only lookup against the owning module's own public-id column -
    never through that module's repository or service layer. See the LINKED_RECORD_EXISTENCE_
    LOOKUP docstring in contract.py for why this is the deliberate shape rather than a
    cross-module import.
    """
    mapping = LINKED_RECORD_EXISTENCE_LOOKUP.get(linked_record_type)
    if mapping is None:
        return False
    table, column = mapping
    row = db.execute(
        text(f"SELECT 1 FROM {table} WHERE {column} = :public_id"),  # noqa: S608 - table/column from a closed allowlist, never caller input
        {"public_id": linked_record_public_id},
    ).first()
    return row is not None


def contact_exists(db: Session, *, contact_public_id: str) -> bool:
    row = db.execute(
        text("SELECT 1 FROM business_party_contact WHERE contact_public_id = :public_id"),
        {"public_id": contact_public_id},
    ).first()
    return row is not None


def app_user_exists(db: Session, *, app_user_public_id: str) -> bool:
    row = db.execute(
        text("SELECT 1 FROM app_user WHERE public_id = :public_id"),
        {"public_id": app_user_public_id},
    ).first()
    return row is not None


def _row_to_interaction(row: Any) -> dict[str, Any]:
    data = row._mapping if hasattr(row, "_mapping") else row
    return dict(data)


def insert_interaction(db: Session, *, public_id: str, values: dict[str, Any]) -> dict[str, Any]:
    db.execute(
        text(
            f"""
            INSERT INTO {INTERACTION_TABLE} (
                interaction_public_id,
                linked_record_type,
                linked_record_public_id,
                channel_code,
                direction_code,
                occurred_at,
                subject,
                body_text,
                body_stored,
                external_system,
                external_message_id,
                idempotency_key,
                request_fingerprint,
                external_reference_url,
                geo_latitude,
                geo_longitude,
                outcome,
                next_follow_up_at,
                recorded_by,
                created_at,
                updated_at
            ) VALUES (
                :interaction_public_id,
                :linked_record_type,
                :linked_record_public_id,
                :channel_code,
                :direction_code,
                :occurred_at,
                :subject,
                :body_text,
                :body_stored,
                :external_system,
                :external_message_id,
                :idempotency_key,
                :request_fingerprint,
                :external_reference_url,
                :geo_latitude,
                :geo_longitude,
                :outcome,
                :next_follow_up_at,
                :recorded_by,
                CURRENT_TIMESTAMP,
                CURRENT_TIMESTAMP
            )
            """
        ),
        {"interaction_public_id": public_id, **values},
    )
    return get_interaction_by_public_id(db, public_id)


def insert_interaction_participant(
    db: Session, *, public_id: str, interaction_id: int, values: dict[str, Any]
) -> dict[str, Any]:
    db.execute(
        text(
            f"""
            INSERT INTO {INTERACTION_PARTICIPANT_TABLE} (
                participant_public_id,
                interaction_id,
                party_role_code,
                contact_public_id,
                app_user_public_id,
                display_name,
                address_or_number,
                created_at
            ) VALUES (
                :participant_public_id,
                :interaction_id,
                :party_role_code,
                :contact_public_id,
                :app_user_public_id,
                :display_name,
                :address_or_number,
                CURRENT_TIMESTAMP
            )
            """
        ),
        {"participant_public_id": public_id, "interaction_id": interaction_id, **values},
    )
    row = db.execute(
        text(
            f"""
            SELECT participant_public_id, party_role_code, contact_public_id, app_user_public_id,
                   display_name, address_or_number
            FROM {INTERACTION_PARTICIPANT_TABLE}
            WHERE participant_public_id = :public_id
            """
        ),
        {"public_id": public_id},
    ).first()
    return _row_to_interaction(row) if row is not None else {}


def get_interaction_id_by_public_id(db: Session, public_id: str) -> int | None:
    row = db.execute(
        text(f"SELECT id FROM {INTERACTION_TABLE} WHERE interaction_public_id = :public_id AND is_deleted IS FALSE"),
        {"public_id": public_id},
    ).first()
    return int(row[0]) if row is not None else None


def get_interaction_by_public_id(db: Session, public_id: str) -> dict[str, Any] | None:
    row = db.execute(
        text(
            f"""
            SELECT id, interaction_public_id, linked_record_type, linked_record_public_id,
                   channel_code, direction_code, occurred_at, subject, body_text, body_stored,
                   external_system, external_message_id, idempotency_key,
                   external_reference_url, geo_latitude, geo_longitude, outcome,
                   next_follow_up_at, recorded_by, created_at, updated_at
            FROM {INTERACTION_TABLE}
            WHERE interaction_public_id = :public_id AND is_deleted IS FALSE
            """
        ),
        {"public_id": public_id},
    ).first()
    return _row_to_interaction(row) if row is not None else None


_INTERACTION_COLUMNS = """
    id, interaction_public_id, linked_record_type, linked_record_public_id,
    channel_code, direction_code, occurred_at, subject, body_text, body_stored,
    external_system, external_message_id, idempotency_key, request_fingerprint,
    external_reference_url, geo_latitude, geo_longitude, outcome,
    next_follow_up_at, recorded_by, created_at, updated_at, is_deleted
"""


def get_interaction_by_idempotency_key(db: Session, *, idempotency_key: str) -> dict[str, Any] | None:
    """Resolve an existing row by its caller-supplied idempotency key, for retry replay.

    Deliberately does NOT filter on is_deleted: a retry of a command whose row was later
    soft-deleted must still resolve to that row rather than be answered as a fresh write, which
    would resurrect the conversation under a new public id.
    """
    row = db.execute(
        text(
            f"""
            SELECT {_INTERACTION_COLUMNS}
            FROM {INTERACTION_TABLE}
            WHERE idempotency_key = :idempotency_key
            """
        ),
        {"idempotency_key": idempotency_key},
    ).first()
    return _row_to_interaction(row) if row is not None else None


def get_interaction_by_external_message(
    db: Session, *, external_system: str, external_message_id: str
) -> dict[str, Any] | None:
    """Resolve an existing row by the provider's own message identity, for retry replay.

    Same is_deleted reasoning as get_interaction_by_idempotency_key: re-syncing a mailbox must
    not recreate a message an operator deliberately removed.
    """
    row = db.execute(
        text(
            f"""
            SELECT {_INTERACTION_COLUMNS}
            FROM {INTERACTION_TABLE}
            WHERE external_system = :external_system
              AND external_message_id = :external_message_id
            """
        ),
        {"external_system": external_system, "external_message_id": external_message_id},
    ).first()
    return _row_to_interaction(row) if row is not None else None


def list_interaction_participants(db: Session, *, interaction_id: int) -> list[dict[str, Any]]:
    rows = db.execute(
        text(
            f"""
            SELECT participant_public_id, party_role_code, contact_public_id, app_user_public_id,
                   display_name, address_or_number
            FROM {INTERACTION_PARTICIPANT_TABLE}
            WHERE interaction_id = :interaction_id
            ORDER BY id
            """
        ),
        {"interaction_id": interaction_id},
    ).fetchall()
    return [_row_to_interaction(r) for r in rows]


def list_participants_for_interactions(db: Session, *, interaction_ids: list[int]) -> dict[int, list[dict[str, Any]]]:
    """Batch participant lookup for a list of interaction rows, avoiding N+1 queries on list."""
    if not interaction_ids:
        return {}
    rows = db.execute(
        text(
            f"""
            SELECT interaction_id, participant_public_id, party_role_code, contact_public_id,
                   app_user_public_id, display_name, address_or_number
            FROM {INTERACTION_PARTICIPANT_TABLE}
            WHERE interaction_id = ANY(:interaction_ids)
            ORDER BY interaction_id, id
            """
        ),
        {"interaction_ids": interaction_ids},
    ).fetchall()
    result: dict[int, list[dict[str, Any]]] = {iid: [] for iid in interaction_ids}
    for row in rows:
        data = _row_to_interaction(row)
        result[data["interaction_id"]].append(data)
    return result


def list_interactions(
    db: Session,
    *,
    linked_record_type: str,
    linked_record_public_id: str,
    channel_code: str | None = None,
    direction_code: str | None = None,
    occurred_from: Any = None,
    occurred_to: Any = None,
    limit: int = 20,
    offset: int = 0,
) -> list[dict[str, Any]]:
    """Rows recorded directly against this exact record. Never resolves inheritance - see
    service.list_interactions_with_inheritance for the include_inherited=true behaviour."""
    clauses = ["linked_record_type = :linked_record_type", "linked_record_public_id = :linked_record_public_id", "is_deleted IS FALSE"]
    params: dict[str, Any] = {
        "linked_record_type": linked_record_type,
        "linked_record_public_id": linked_record_public_id,
        "limit": limit,
        "offset": offset,
    }
    if channel_code is not None:
        clauses.append("channel_code = :channel_code")
        params["channel_code"] = channel_code
    if direction_code is not None:
        clauses.append("direction_code = :direction_code")
        params["direction_code"] = direction_code
    if occurred_from is not None:
        clauses.append("occurred_at >= :occurred_from")
        params["occurred_from"] = occurred_from
    if occurred_to is not None:
        clauses.append("occurred_at <= :occurred_to")
        params["occurred_to"] = occurred_to

    where = " AND ".join(clauses)
    rows = db.execute(
        text(
            f"""
            SELECT id, interaction_public_id, linked_record_type, linked_record_public_id,
                   channel_code, direction_code, occurred_at, subject, body_text, body_stored,
                   external_system, external_message_id, idempotency_key,
                   external_reference_url, geo_latitude, geo_longitude, outcome,
                   next_follow_up_at, recorded_by, created_at, updated_at
            FROM {INTERACTION_TABLE}
            WHERE {where}
            ORDER BY occurred_at DESC, id DESC
            LIMIT :limit OFFSET :offset
            """
        ),
        params,
    ).fetchall()
    return [_row_to_interaction(r) for r in rows]


UPDATABLE_INTERACTION_COLUMNS = ("outcome", "next_follow_up_at")


def update_interaction(db: Session, *, interaction_id: int, values: dict[str, Any]) -> dict[str, Any] | None:
    """Write only the columns the caller actually supplied.

    `values` must contain only keys the caller explicitly set - see
    service.update_interaction, which builds it with Pydantic's exclude_unset. Writing the full
    column set unconditionally would mean `PUT {"outcome": "..."}` silently nulls
    next_follow_up_at, destroying a scheduled follow-up the caller never mentioned.
    """
    unknown = set(values) - set(UPDATABLE_INTERACTION_COLUMNS)
    if unknown:
        # Defensive: the column names below are interpolated into SQL, so they must come from
        # this closed tuple and never from caller-controlled keys.
        raise ValueError(f"not an updatable interaction column: {sorted(unknown)}")

    if not values:
        # Nothing supplied: touch nothing, not even updated_at. A no-op PUT should not look like
        # an edit in the audit trail.
        return get_interaction_by_public_id(
            db,
            db.execute(
                text(f"SELECT interaction_public_id FROM {INTERACTION_TABLE} WHERE id = :interaction_id"),
                {"interaction_id": interaction_id},
            ).scalar_one(),
        )

    assignments = ", ".join(f"{column} = :{column}" for column in values)
    db.execute(
        text(
            f"""
            UPDATE {INTERACTION_TABLE}
            SET {assignments},
                updated_at = CURRENT_TIMESTAMP
            WHERE id = :interaction_id
            """
        ),
        {"interaction_id": interaction_id, **values},
    )
    row = db.execute(
        text(f"SELECT interaction_public_id FROM {INTERACTION_TABLE} WHERE id = :interaction_id"),
        {"interaction_id": interaction_id},
    ).first()
    if row is None:
        return None
    return get_interaction_by_public_id(db, row[0])


def soft_delete_interaction(db: Session, *, interaction_id: int) -> None:
    db.execute(
        text(f"UPDATE {INTERACTION_TABLE} SET is_deleted = TRUE, updated_at = CURRENT_TIMESTAMP WHERE id = :interaction_id"),
        {"interaction_id": interaction_id},
    )


# --- Inheritance support -----------------------------------------------------------------
# These two functions resolve, respectively, the source Lead of an Opportunity and the
# source Lead(s) of an Account, so the service layer can build the derived (never copied)
# inherited-history read described in the slice document.


def get_opportunity_source_lead_public_id(db: Session, *, opportunity_public_id: str) -> str | None:
    row = db.execute(
        text(
            """
            SELECT l.lead_public_id
            FROM crm_opportunity o
            JOIN crm_lead l ON l.id = o.source_lead_id
            WHERE o.opportunity_public_id = :opportunity_public_id
            """
        ),
        {"opportunity_public_id": opportunity_public_id},
    ).first()
    return row[0] if row is not None else None


def get_account_source_lead_public_ids(db: Session, *, account_public_id: str) -> list[str]:
    rows = db.execute(
        text(
            """
            SELECT DISTINCT l.lead_public_id
            FROM crm_opportunity o
            JOIN crm_lead l ON l.id = o.source_lead_id
            JOIN business_party bp ON bp.id = o.business_party_id
            WHERE bp.business_party_public_id = :account_public_id
              AND o.source_lead_id IS NOT NULL
            """
        ),
        {"account_public_id": account_public_id},
    ).fetchall()
    return [row[0] for row in rows]
