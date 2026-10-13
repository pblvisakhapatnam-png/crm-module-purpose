"""Shared helper for the ELG-1 and ELG-2 tests: remove exactly the eligibility records a test created - "seen" marks
and reminder setting versions (ELG-2), decisions and their results, "not applicable" marks, certificates with their
copies (stored files first, then rows), and rules - before the equipment records they key on are removed.
"""

from __future__ import annotations

import contextlib
from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import text

from app.core.database import SessionLocal
from app.modules.documents.storage import get_storage_provider_by_code
from tests.equipment_test_support import equipment_created_here

_TABLES = (
    "eligibility_certificate",
    "eligibility_not_applicable",
    "eligibility_rule",
    "eligibility_decision",
    "eligibility_alert_setting",
    "eligibility_alert_acknowledgement",
)


def eligibility_boundaries() -> dict[str, int]:
    with SessionLocal() as db:
        return {table: int(db.execute(text(f"SELECT COALESCE(MAX(id), 0) FROM {table}")).scalar_one()) for table in _TABLES}


def remove_eligibility_created_after(boundaries: dict[str, int]) -> None:
    params = {
        "certificate": boundaries["eligibility_certificate"],
        "mark": boundaries["eligibility_not_applicable"],
        "rule": boundaries["eligibility_rule"],
        "decision": boundaries["eligibility_decision"],
        "setting": boundaries["eligibility_alert_setting"],
        "seen": boundaries["eligibility_alert_acknowledgement"],
    }
    with SessionLocal() as db:
        stored = db.execute(
            text(
                "SELECT d.storage_provider_code, d.storage_key FROM document_metadata d "
                "INNER JOIN eligibility_certificate c ON c.certificate_public_id = d.linked_record_public_id "
                "WHERE d.linked_record_type = 'eligibility_certificate' AND c.id > :certificate AND d.storage_key IS NOT NULL"
            ),
            params,
        ).fetchall()
    for provider_code, storage_key in stored:
        with contextlib.suppress(Exception):
            get_storage_provider_by_code(provider_code).delete(storage_key=storage_key)
    statements = (
        "DELETE FROM eligibility_alert_acknowledgement WHERE id > :seen",
        "DELETE FROM eligibility_alert_band WHERE setting_id > :setting",
        "DELETE FROM eligibility_alert_step WHERE setting_id > :setting",
        "DELETE FROM eligibility_alert_setting WHERE id > :setting",
        "DELETE FROM document_metadata d USING eligibility_certificate c WHERE d.linked_record_type = 'eligibility_certificate' "
        "AND c.certificate_public_id = d.linked_record_public_id AND c.id > :certificate",
        "DELETE FROM eligibility_decision_result WHERE decision_id > :decision OR certificate_id > :certificate "
        "OR mark_id > :mark OR rule_id > :rule",
        "DELETE FROM eligibility_decision WHERE id > :decision",
        "DELETE FROM eligibility_not_applicable WHERE id > :mark OR allowed_by_rule_id > :rule",
        "DELETE FROM eligibility_certificate WHERE id > :certificate",
        "DELETE FROM eligibility_rule WHERE id > :rule",
    )
    with SessionLocal() as db:
        for sql in statements:
            db.execute(text(sql), params)
        db.commit()


@contextmanager
def eligibility_created_here() -> Iterator[None]:
    """Everything a test made, eligibility first, then the invented machines it keyed them on."""
    with equipment_created_here():
        boundaries = eligibility_boundaries()
        try:
            yield
        finally:
            remove_eligibility_created_after(boundaries)
