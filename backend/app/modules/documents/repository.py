"""Document metadata repository - raw SQL against `document_metadata`, following the pattern
already used by leads/opportunities/commercial_offers/interactions repositories in this codebase
rather than SQLAlchemy ORM models (Slice 9C).
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import bindparam, text
from sqlalchemy.orm import Session

from app.modules.documents.contract import DOCUMENT_METADATA_TABLE

_DOCUMENT_COLUMNS = """
    id, document_public_id, document_type, linked_record_type, linked_record_public_id,
    file_name, original_file_name, storage_mode, storage_path_or_url, version_no, status,
    storage_provider_code, storage_key, content_type, byte_size, checksum_sha256,
    retention_due_at, uploaded_by, uploaded_at, remarks
"""


def _row_to_document(row: Any) -> dict[str, Any]:
    data = row._mapping if hasattr(row, "_mapping") else row
    return dict(data)


def insert_document_metadata(db: Session, *, public_id: str, values: dict[str, Any]) -> dict[str, Any]:
    db.execute(
        text(
            f"""
            INSERT INTO {DOCUMENT_METADATA_TABLE} (
                document_public_id,
                document_type,
                linked_record_type,
                linked_record_public_id,
                file_name,
                original_file_name,
                storage_mode,
                storage_path_or_url,
                version_no,
                status,
                storage_provider_code,
                storage_key,
                content_type,
                byte_size,
                checksum_sha256,
                retention_due_at,
                uploaded_by,
                uploaded_at,
                created_at,
                remarks
            ) VALUES (
                :document_public_id,
                :document_type,
                :linked_record_type,
                :linked_record_public_id,
                :file_name,
                :original_file_name,
                :storage_mode,
                :storage_path_or_url,
                :version_no,
                :status,
                :storage_provider_code,
                :storage_key,
                :content_type,
                :byte_size,
                :checksum_sha256,
                :retention_due_at,
                :uploaded_by,
                CURRENT_TIMESTAMP,
                CURRENT_TIMESTAMP,
                :remarks
            )
            """
        ),
        {"document_public_id": public_id, **values},
    )
    return get_document_by_public_id(db, public_id)  # type: ignore[return-value]


def get_document_by_public_id(db: Session, public_id: str) -> dict[str, Any] | None:
    row = db.execute(
        text(
            f"""
            SELECT {_DOCUMENT_COLUMNS}
            FROM {DOCUMENT_METADATA_TABLE}
            WHERE document_public_id = :public_id
            """
        ),
        {"public_id": public_id},
    ).first()
    return _row_to_document(row) if row is not None else None


def list_recent_documents(db: Session, *, limit: int) -> list[dict[str, Any]]:
    """The most recent `limit` rows, unfiltered by caller permission.

    The service layer applies the record-scoped, fail-closed authorization check per row AFTER
    this returns, and therefore passes a fetch limit larger than the number of rows it will
    actually return to the caller - see service.list_recent_documents_for_caller for the exact
    bound. This function has no opinion about that; it fetches exactly what it is asked for.
    """
    rows = db.execute(
        text(
            f"""
            SELECT {_DOCUMENT_COLUMNS}
            FROM {DOCUMENT_METADATA_TABLE}
            ORDER BY uploaded_at DESC, id DESC
            LIMIT :limit
            """
        ),
        {"limit": limit},
    ).fetchall()
    return [_row_to_document(r) for r in rows]


def list_documents_for_record(
    db: Session, *, linked_record_type: str, linked_record_public_id: str
) -> list[dict[str, Any]]:
    rows = db.execute(
        text(
            f"""
            SELECT {_DOCUMENT_COLUMNS}
            FROM {DOCUMENT_METADATA_TABLE}
            WHERE linked_record_type = :linked_record_type
              AND linked_record_public_id = :linked_record_public_id
            ORDER BY uploaded_at DESC, id DESC
            """
        ),
        {
            "linked_record_type": linked_record_type,
            "linked_record_public_id": linked_record_public_id,
        },
    ).fetchall()
    return [_row_to_document(r) for r in rows]


def list_linked_record_ids_with_documents(
    db: Session,
    *,
    linked_record_type: str,
    linked_record_public_ids: list[str],
    document_type: str | None,
    storage_mode: str | None,
) -> set[str]:
    """Which of these records have a document linked to them, of the type and storage mode where given, and not
    rejected or archived (ELG-1)."""
    if not linked_record_public_ids:
        return set()
    statement = text(
        f"""
        SELECT DISTINCT linked_record_public_id
        FROM {DOCUMENT_METADATA_TABLE}
        WHERE linked_record_type = :linked_record_type AND linked_record_public_id IN :ids
          AND (CAST(:document_type AS varchar) IS NULL OR document_type = :document_type)
          AND (CAST(:storage_mode AS varchar) IS NULL OR storage_mode = :storage_mode)
          AND status NOT IN ('Rejected', 'Archived')
        """
    ).bindparams(bindparam("ids", expanding=True))
    rows = db.execute(
        statement,
        {
            "linked_record_type": linked_record_type,
            "ids": linked_record_public_ids,
            "document_type": document_type,
            "storage_mode": storage_mode,
        },
    ).fetchall()
    return {str(row[0]) for row in rows}


def list_documents_linked_to_records(
    db: Session,
    *,
    linked_record_type: str,
    linked_record_public_ids: list[str],
    document_type: str,
) -> list[dict[str, Any]]:
    """The documents of one type linked to these records, not rejected or archived, oldest first (Slice 4G: a market
    rate's quote copies)."""
    if not linked_record_public_ids:
        return []
    statement = text(
        f"""
        SELECT document_public_id, linked_record_public_id, COALESCE(original_file_name, file_name) AS file_name,
               uploaded_at
        FROM {DOCUMENT_METADATA_TABLE}
        WHERE linked_record_type = :linked_record_type AND linked_record_public_id IN :ids
          AND document_type = :document_type
          AND status NOT IN ('Rejected', 'Archived')
        ORDER BY uploaded_at NULLS LAST, id
        """
    ).bindparams(bindparam("ids", expanding=True))
    rows = db.execute(
        statement,
        {"linked_record_type": linked_record_type, "ids": linked_record_public_ids, "document_type": document_type},
    ).mappings()
    return [dict(row) for row in rows]
