from __future__ import annotations

from typing import Any

from sqlalchemy import bindparam, text
from sqlalchemy.orm import Session

from app.core.database import SessionLocal

from .cleanup import (
    _ACCOUNT_SUB_RECORD_TABLES,
    CleanupValidationError,
    _collect_ids,
    _event_record_pairs,
    _expand_ownership_closure,
    _owned_record_pairs,
    _select_where_pairs,
)
from .manifest import validate_manifest_dict


# The five groups `expected` and `found` cover. Status reports on anchors; anything else a
# manifest names is subordinate to one of them.
_STATUS_ANCHOR_GROUPS = (
    "account_public_ids",
    "opportunity_public_ids",
    "offer_public_ids",
    "work_order_public_ids",
    "lead_public_ids",
    # ERT-1: a run's equipment models and the Plum report imports it confirmed.
    "equipment_model_public_ids",
    "equipment_import_public_ids",
)

# Derived from cleanup's single descriptor, so the two cannot drift.
_STATUS_ACCOUNT_SUB_TABLES = tuple(
    (table, count_key.removeprefix("account_"))
    for table, _id_column, _group, count_key in _ACCOUNT_SUB_RECORD_TABLES
)


def _exists_count(db: Session, sql: str, ids: list[str]) -> int:
    if not ids:
        return 0
    statement = text(sql).bindparams(bindparam("ids", expanding=True))
    return db.execute(statement, {"ids": ids}).scalar() or 0


def _count_where_pairs(db: Session, sql: str, pairs: list[tuple[str, str]]) -> int:
    if not pairs:
        return 0
    statement = text(sql).bindparams(bindparam("pairs", expanding=True))
    return db.execute(statement, {"pairs": pairs}).scalar() or 0


def check_manifest_status(manifest: dict[str, Any]) -> dict[str, Any]:
    """Read-only check of whether a manifest's anchor records (account/opportunity/offer/
    work_order/lead) still exist, plus a residue check for the record types that can outlive them.

    Never mutates anything. Used by scripts/vendor-demo.ps1 status/preflight to decide whether a
    reset is recommended before a demonstration, and by the UAT runbook.

    **It cannot certify that a targeted cleanup left nothing behind, and must not be described as
    doing so.** Residue is found through each record's parent, so once a record the manifest never
    named has been deleted, anything still attached to it is unreachable. A mechanism to close that
    - a durable record of every id a cleanup deleted - was built and then removed; see
    docs/agent/technical-enablement/TE_4_CLEANUP_PROVENANCE.md.

    Residue is checked at all because not everything a run creates is foreign-key bound to its
    anchor. Slice 9C documents and Slice 9D interactions link by `linked_record_public_id`, and
    Slice 9E quote documents by an application-enforced `commercial_offer_id` with no declared
    constraint. Those can survive their parent silently. Records that ARE foreign-key enforced
    (offer lines, related offers, amendments, pricing evidence) need no check: if the anchor is
    gone, so are they.
    """
    validate_manifest_dict(manifest)
    ids = _collect_ids(manifest)
    # Guarded on the ANCHOR groups only, because `expected` and `found` below cover exactly
    # those five. A manifest naming only activities passed a wider guard and then reported 0/0 as
    # "All anchor records are present" - a confident answer about nothing.
    if not any(ids[group] for group in _STATUS_ANCHOR_GROUPS):
        raise CleanupValidationError(
            "Manifest names no account/opportunity/offer/work-order/lead record or equipment model/import, "
            "so there is nothing for a status check to report on."
        )


    with SessionLocal() as db:
        # The closure runs FIRST, before anything is counted: `found` and `expected` must come
        # from the same id set or the comparison is meaningless.
        ids = _expand_ownership_closure(db, ids)

        found = {
            "accounts": _exists_count(
                db,
                "SELECT COUNT(*) FROM business_party WHERE business_party_public_id IN :ids",
                ids["account_public_ids"],
            ),
            "opportunities": _exists_count(
                db,
                "SELECT COUNT(*) FROM crm_opportunity WHERE opportunity_public_id IN :ids",
                ids["opportunity_public_ids"],
            ),
            "commercial_offers": _exists_count(
                db,
                "SELECT COUNT(*) FROM crm_commercial_offer WHERE offer_public_id IN :ids",
                ids["offer_public_ids"],
            ),
            "work_orders": _exists_count(
                db,
                "SELECT COUNT(*) FROM crm_work_order WHERE work_order_public_id IN :ids",
                ids["work_order_public_ids"],
            ),
            "leads": _exists_count(
                db, "SELECT COUNT(*) FROM crm_lead WHERE lead_public_id IN :ids", ids["lead_public_ids"]
            ),
            "equipment_models": _exists_count(
                db, "SELECT COUNT(*) FROM equipment_model WHERE model_public_id IN :ids", ids["equipment_model_public_ids"]
            ),
            "equipment_imports": _exists_count(
                db,
                "SELECT COUNT(*) FROM equipment_source_import WHERE import_public_id IN :ids",
                ids["equipment_import_public_ids"],
            ),
        }

        # Records that can outlive their parent.
        #
        # `status` runs the SAME ownership closure cleanup runs, so the two consider identical
        # record sets by construction rather than by two lists kept in step by hand. The pairs
        # below are built from records that still EXIST, so after a cleanup they are empty - which
        # is why residue is checked at all, and why it cannot see past a deleted parent.
        owned_pairs = _owned_record_pairs(ids, [])
        interaction_ids = [
            row["interaction_public_id"]
            for row in _select_where_pairs(
                db,
                """
                SELECT interaction_public_id FROM interaction
                WHERE (linked_record_type, linked_record_public_id) IN :pairs
                """,
                owned_pairs,
            )
        ]
        document_pairs = _owned_record_pairs(ids, interaction_ids)

        residue = {
            "quote_documents": _exists_count(
                db,
                """
                SELECT COUNT(*) FROM crm_commercial_offer_quote_document q
                JOIN crm_commercial_offer o ON o.id = q.commercial_offer_id
                WHERE o.offer_public_id IN :ids
                """,
                ids["offer_public_ids"],
            ),
            # ...or attached to nothing at all. Deliberately NOT run-scoped - a quote document
            # whose offer is gone cannot be traced back to the run that made it - and therefore
            # deliberately NOT part of residue_clear either. Folding it in made one pre-existing
            # orphan from any source report every subsequent reset as having left it behind, which
            # would teach an operator to ignore the one signal this check exists to give. It is a
            # database-wide integrity warning, reported separately and attributed to nobody.
            "orphaned_quote_documents": db.execute(
                text(
                    """
                    SELECT COUNT(*) FROM crm_commercial_offer_quote_document q
                    LEFT JOIN crm_commercial_offer o ON o.id = q.commercial_offer_id
                    WHERE o.id IS NULL
                    """
                )
            ).scalar()
            or 0,
            "documents": _count_where_pairs(
                db,
                """
                SELECT COUNT(*) FROM document_metadata
                WHERE (linked_record_type, linked_record_public_id) IN :pairs
                """,
                document_pairs,
            ),
            "interactions": _count_where_pairs(
                db,
                """
                SELECT COUNT(*) FROM interaction
                WHERE (linked_record_type, linked_record_public_id) IN :pairs
                """,
                owned_pairs,
            ),
            # All four sub-tables, not the two an earlier version happened to check.
            **{
                f"account_{count_key}": _exists_count(
                    db,
                    f"""
                    SELECT COUNT(*) FROM {table} sub
                    JOIN business_party bp ON bp.id = sub.business_party_id
                    WHERE bp.business_party_public_id IN :ids
                    """,
                    ids["account_public_ids"],
                )
                for table, count_key in _STATUS_ACCOUNT_SUB_TABLES
            },
            # 8A core: the request keys of the run's allocations and kit, by the run's requirements.
            "resource_assignment_requests": _exists_count(
                db,
                "SELECT COUNT(*) FROM resource_assignment_request WHERE resource_requirement_public_id IN :ids",
                ids["resource_requirement_public_ids"],
            ),
            "lead_activities": _exists_count(
                db,
                """
                SELECT COUNT(*) FROM crm_lead_activity la
                JOIN crm_lead l ON l.id = la.lead_id
                WHERE l.lead_public_id IN :ids
                """,
                ids["lead_public_ids"],
            ),
            # Audit rows for every id this run owns, including the ones keyed by a record's own
            # public id rather than its parent's - the case that left a live-created Lead
            # activity's event behind.
            # The SAME typed pairs cleanup deletes by. Counting on the id alone made status
            # report another record type's surviving event as this run's residue, disagreeing
            # with a cleanup that had behaved correctly (independent review, seventh pass).
            "business_events": _count_where_pairs(
                db,
                """
                SELECT COUNT(*) FROM business_event
                WHERE (record_type, record_public_id) IN :pairs
                """,
                _event_record_pairs({**ids, "interaction_public_ids": sorted(interaction_ids)}),
            ),
        }

    expected = {
        "accounts": len(ids["account_public_ids"]),
        "opportunities": len(ids["opportunity_public_ids"]),
        "commercial_offers": len(ids["offer_public_ids"]),
        "work_orders": len(ids["work_order_public_ids"]),
        "leads": len(ids["lead_public_ids"]),
        "equipment_models": len(ids["equipment_model_public_ids"]),
        "equipment_imports": len(ids["equipment_import_public_ids"]),
    }
    all_present = all(found[key] == expected[key] for key in expected)
    all_absent = all(count == 0 for count in found.values())
    return {
        "expected": expected,
        "found": found,
        "all_present": all_present,
        "residue": residue,
        # No run-scoped residue was found THROUGH RECORDS THAT STILL EXIST. Deliberately not the
        # same claim as "the reset finished the job": residue hanging off a record the cleanup
        # discovered and deleted, and the manifest never named, cannot be reached from here. See
        # this function's docstring.
        # Run-scoped only. "orphaned_quote_documents" is excluded because it counts rows this
        # run cannot be shown to have created; it is surfaced on its own so an operator can act on
        # it without it contaminating the verdict on their own reset.
        "residue_clear": all(
            count == 0 for key, count in residue.items() if key != "orphaned_quote_documents"
        ),
        "all_absent": all_absent,
    }
