from __future__ import annotations

import re
from typing import Any

from sqlalchemy import bindparam, text
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.modules.equipment_reference.contract import PROVIDER_PLUM, model_mapping_public_id, normalize_term
from app.modules.documents.storage import get_storage_provider_by_code
from app.modules.resource_assignments.repository import mark_service_write
from app.modules.opportunities.contract import (
    OPPORTUNITY_EVENT_ACCOUNT_REPAIRED,
    OPPORTUNITY_RECORD_TYPE,
)

from .manifest import is_uuid_like, validate_manifest_dict

# Generous: the longest real chain is lead -> opportunity -> offer -> work order -> offer, so a
# handful of passes settles any manifest. A high bound costs nothing (each pass is a few indexed
# selects and the loop exits as soon as a pass adds nothing) and only exists to turn a
# non-converging edge into a loud failure rather than an infinite loop.
_CLOSURE_MAX_PASSES = 25

# The two shapes a manifest record may carry an owned id in, each mapping its record key to the
# id group it feeds. _collect_ids both VALIDATES and READS from these, in one pass, so a record
# shape cannot be validated without being collected or collected without being validated. The
# fourth review found the collections validated nowhere precisely because validation and reading
# were written as separate hand-maintained lists of keys, and one of them was shorter.
#
# Note `related_offers` and `commercial_offer` share a target: a related offer is an offer.
#
# `amendments` is deliberately absent, and its absence is not an oversight of the same kind. A
# manifest carries that key for readability and URLs only; nothing here reads it, because Slice
# 6O.2 amendments are discovered by Work Order ownership instead (see the delete steps below). A
# malformed entry there therefore cannot cause a partial cleanup, which is the harm this
# validation exists to prevent - so validating it would refuse manifests for no gain.
_MANIFEST_ANCHOR_TARGETS = {
    "account": "account_public_ids",
    "opportunity": "opportunity_public_ids",
    "commercial_offer": "offer_public_ids",
    "lead": "lead_public_ids",
}
_MANIFEST_COLLECTION_TARGETS = {
    "work_orders": "work_order_public_ids",
    "related_offers": "offer_public_ids",
    "activities": "lead_activity_public_ids",
    # ERT-1: the models a run records and the Plum report imports it confirms.
    "equipment_models": "equipment_model_public_ids",
    "equipment_imports": "equipment_import_public_ids",
    # HOL-1: the years of PBL's holiday calendar a run starts - far ahead, in the harness's own years - and removes
    # with everything in them, whoever changed them later, as a run's Work Orders are (TE-4: by provenance).
    "holiday_calendar_years": "holiday_calendar_year_public_ids",
}

# ERT-1: the SHA-256 fingerprints of the invented reports a run wrote for someone to upload later, from
# the screen. Only this run's file has its fingerprint, so an import carrying one is this run's by
# provenance, not by reachability - the TE-4 rule for a parent. They are not public ids and are
# validated as fingerprints.
_MANIFEST_FINGERPRINT_KEY = "equipment_report_fingerprints"
_FINGERPRINT_GROUP = "equipment_report_fingerprints"
_FINGERPRINT_RE = re.compile(r"^[0-9a-f]{64}$")

# ERT-1: the Plum model names a run's invented reports carry, each with the run's token. A mapping of one
# of them is the run's by provenance - whoever made it, the harness or a tester on the screen - since only
# the run's reports hold the name. A mapping of any other name is not the run's, even when it points at a
# run's model (independent review, round 2, ERT1-R2-001). Kept in the stored, normalized form.
_MANIFEST_SOURCE_NAMES_KEY = "equipment_source_names"
_SOURCE_NAME_GROUP = "equipment_source_names"
_SOURCE_NAME_MAX_LENGTH = 200

# The repair_mode value opportunities/service.py writes when the Opportunity Account repair flow
# CREATES an Account rather than linking an existing one. A bare literal there rather than a
# shared constant, so it is pinned here by
# test_cleanup_removes_an_account_the_repair_flow_created_for_an_owned_opportunity, which performs
# a real repair and fails if the two ever disagree.
_REPAIR_MODE_CREATED_MINIMAL_ACCOUNT = "created_minimal_account"


class CleanupValidationError(ValueError):
    """Raised when the manifest/record ids do not look safe to delete."""


class CleanupStorageError(RuntimeError):
    """Raised when the database cleanup committed but stored files could not be removed.

    Deliberately an exception rather than a count in the result: the rows are already gone by the
    time this is known, and a count returned alongside a successful exit would be printed as just
    another line of a report nobody reads closely.

    The rows are gone by the time this is known, so the keys are not recoverable from the database
    and are not persisted anywhere else - this message is the only record of them. That is a
    deliberate trade (see store.py): the retry machinery it would take to avoid it guards a failure
    the only real provider cannot produce."""


def _require_uuid(public_id: str) -> str:
    if not is_uuid_like(public_id):
        raise CleanupValidationError(f"Refusing to clean up a non-UUID-looking id: {public_id!r}")
    return public_id


def _collect_ids(manifest: dict[str, Any]) -> dict[str, list[str]]:
    ids: dict[str, set[str]] = {
        "account_public_ids": set(),
        "opportunity_public_ids": set(),
        "offer_public_ids": set(),
        "work_order_public_ids": set(),
        "lead_public_ids": set(),
        "lead_activity_public_ids": set(),
        # WRR-001: never named by a manifest, only discovered below Work Order lines by the closure.
        "resource_requirement_public_ids": set(),
        # 8A core: never named by a manifest; an allocation is the run's by the run's requirement it fills,
        # and a kit line by the run's allocation it is on.
        "resource_assignment_public_ids": set(),
        "resource_assignment_kit_public_ids": set(),
        # ERT-1: models and imports are named by the manifest; imports are also found by fingerprint,
        # and machines and value rules only by the import that made them.
        "equipment_model_public_ids": set(),
        "equipment_import_public_ids": set(),
        "equipment_asset_public_ids": set(),
        "equipment_value_rule_public_ids": set(),
        _FINGERPRINT_GROUP: set(),
        _SOURCE_NAME_GROUP: set(),
        # ERT-1: each of the run's names' mapping, by the identity its events are recorded under.
        "equipment_mapping_public_ids": set(),
        # ELG-1: never named by a manifest; found only by the run's assets.
        "eligibility_certificate_public_ids": set(),
        "eligibility_mark_public_ids": set(),
        "eligibility_decision_public_ids": set(),
        # HOL-1: named by the manifest only.
        "holiday_calendar_year_public_ids": set(),
        # Slice 4G: never named by a manifest; a market rate is the run's by the offer it is on.
        "market_rate_public_ids": set(),
    }

    # A damaged record is refused, never skipped: a manifest that cannot be read in full must not
    # be acted on in part, or cleanup removes half of itself and reports success.
    #
    # Validation and collection are ONE pass over the same two mappings, so neither can cover a
    # record shape the other misses. Two hand-maintained lists is what failed before - the
    # collections were validated nowhere.
    #
    # Absence is fine, malformation is not: a Lead closed as unqualified never produces an Account
    # or an offer.
    for record_key, record in manifest.get("records", {}).items():
        if not isinstance(record, dict):
            raise CleanupValidationError(
                f"Manifest record {record_key!r} is {type(record).__name__}, not an object. "
                "Refusing to clean up part of a manifest that cannot be read in full."
            )

        for anchor_key, target in _MANIFEST_ANCHOR_TARGETS.items():
            anchor = record.get(anchor_key)
            if anchor is None:
                continue
            if not isinstance(anchor, dict) or not anchor.get("public_id"):
                raise CleanupValidationError(
                    f"Manifest record {record_key!r} has a malformed {anchor_key!r} entry with no "
                    "usable public_id. Refusing to clean up part of a manifest that cannot be "
                    "read in full."
                )
            ids[target].add(str(anchor["public_id"]))

        for collection_key, target in _MANIFEST_COLLECTION_TARGETS.items():
            entries = record.get(collection_key)
            if entries is None:
                continue
            if not isinstance(entries, list):
                raise CleanupValidationError(
                    f"Manifest record {record_key!r} has a {collection_key!r} entry that is "
                    f"{type(entries).__name__}, not a list. Refusing to clean up part of a "
                    "manifest that cannot be read in full."
                )
            for entry in entries:
                if not isinstance(entry, dict) or not entry.get("public_id"):
                    raise CleanupValidationError(
                        f"Manifest record {record_key!r} has a malformed {collection_key!r} entry "
                        "with no usable public_id. Refusing to clean up part of a manifest that "
                        "cannot be read in full."
                    )
                ids[target].add(str(entry["public_id"]))

        fingerprints = record.get(_MANIFEST_FINGERPRINT_KEY)
        if fingerprints is not None:
            if not isinstance(fingerprints, list) or not all(
                isinstance(item, str) and _FINGERPRINT_RE.match(item) for item in fingerprints
            ):
                raise CleanupValidationError(
                    f"Manifest record {record_key!r} has a malformed {_MANIFEST_FINGERPRINT_KEY!r} entry: each "
                    "must be a lower-case SHA-256 hex string. Refusing to clean up part of a manifest that "
                    "cannot be read in full."
                )
            ids[_FINGERPRINT_GROUP].update(fingerprints)

        names = record.get(_MANIFEST_SOURCE_NAMES_KEY)
        if names is not None:
            if not isinstance(names, list) or not all(
                isinstance(item, str) and item.strip() and len(item) <= _SOURCE_NAME_MAX_LENGTH for item in names
            ):
                raise CleanupValidationError(
                    f"Manifest record {record_key!r} has a malformed {_MANIFEST_SOURCE_NAMES_KEY!r} entry: each "
                    f"must be a model name of up to {_SOURCE_NAME_MAX_LENGTH} characters. Refusing to clean up part "
                    "of a manifest that cannot be read in full."
                )
            # The stored, normalized form (contract.normalize_term is the rule the database computes).
            ids[_SOURCE_NAME_GROUP].update(normalize_term(item) for item in names)
            ids["equipment_mapping_public_ids"].update(model_mapping_public_id(PROVIDER_PLUM, item) for item in names)

    collected = {key: sorted(value) for key, value in ids.items()}
    for group_key, group in collected.items():
        if group_key in (_FINGERPRINT_GROUP, _SOURCE_NAME_GROUP):
            continue
        for public_id in group:
            _require_uuid(public_id)
    return collected


def _delete_where_in(db: Session, sql: str, ids: list[str]) -> int:
    if not ids:
        return 0
    statement = text(sql).bindparams(bindparam("ids", expanding=True))
    result = db.execute(statement, {"ids": ids})
    return result.rowcount or 0


def _select_where_in(
    db: Session, sql: str, ids: list[str], params: dict[str, str] | None = None
) -> list[str]:
    """`params` carries the extra binds an ownership edge needs beyond `:ids` - currently only the
    repair edge, which has to name an event and a repair mode. Passed as binds rather than
    interpolated into the SQL string: every value is a module constant here, but a deletion path
    is the last place to establish the habit of building SQL by formatting."""
    if not ids:
        return []
    statement = text(sql).bindparams(bindparam("ids", expanding=True))
    return [str(row[0]) for row in db.execute(statement, {"ids": ids, **(params or {})}).fetchall()]


def _null_out_related_work_order_links(db: Session, offer_ids: list[str]) -> None:
    """Breaks crm_commercial_offer.related_work_order_id -> crm_work_order.id (Slice 6O.1)
    before any crm_work_order row is deleted. This FK runs the opposite direction from the
    existing crm_work_order.commercial_offer_id -> crm_commercial_offer.id FK, so without this
    step, deleting a Work Order that a Change Quotation still links to would fail."""
    if not offer_ids:
        return
    statement = text(
        "UPDATE crm_commercial_offer SET related_work_order_id = NULL WHERE offer_public_id IN :ids"
    ).bindparams(bindparam("ids", expanding=True))
    db.execute(statement, {"ids": offer_ids})


# Each account sub-record table, its id column, and the id group its ids belong to. Kept SEPARATE
# rather than pooled: pooling them and then pairing every id with all four record types would
# recreate the type-blind audit matching that the typed pairs exist to prevent.
# One descriptor for each account sub-record table: table, id column, id group, and the key its
# delete is counted under. Discovery, deletion and status all read it, because keeping the same
# four facts in three places is where the drift in this file has repeatedly started.
#
# All four are siblings referencing business_party, so no order among them matters.
_ACCOUNT_SUB_RECORD_TABLES: tuple[tuple[str, str, str, str], ...] = (
    ("business_party_address", "address_public_id", "account_address_public_ids", "account_addresses"),
    ("business_party_gstin", "gstin_public_id", "account_gstin_public_ids", "account_gstins"),
    ("business_party_tax_profile", "tax_profile_public_id", "account_tax_profile_public_ids", "account_tax_profiles"),
    ("business_party_contact", "contact_public_id", "account_contact_public_ids", "account_contacts"),
)


def _find_owned_account_sub_record_ids(
    db: Session, account_ids: list[str]
) -> dict[str, list[str]]:
    """Public ids of the address / GSTIN / tax-profile / contact rows on owned Accounts, by type.

    Collected before those rows are deleted, because each one's creation wrote a business_event
    keyed by its OWN public id, not the Account's."""
    found: dict[str, list[str]] = {group: [] for _t, _c, group, _k in _ACCOUNT_SUB_RECORD_TABLES}
    if not account_ids:
        return found
    for table, id_column, group, _count_key in _ACCOUNT_SUB_RECORD_TABLES:
        found[group] = sorted(
            set(
                _select_where_in(
                    db,
                    f"""
                    SELECT sub.{id_column}
                    FROM {table} sub
                    INNER JOIN business_party bp ON bp.id = sub.business_party_id
                    WHERE bp.business_party_public_id IN :ids
                    """,
                    account_ids,
                )
            )
        )
    return found


# Each entry expands one owned set into another by following a real relationship in the schema:
# (source key, target key, SQL selecting target public ids from source public ids).
#
# A CLOSURE, not a fixed sequence of discovery calls: the edges are followed repeatedly until the
# owned set stops growing. The previous design failed six times in one shape - a relationship
# followed one level and not the next - and each fix had another case behind it.
#
# The trade-off is deliberate: a wider closure reaches records a user attached to seeded data (an
# offer raised on a seeded Opportunity). Those should go; they exist only because the practice data
# did. The boundary is that nothing is reached except through a real relationship to something this
# run owns.
#
# An entry is (source key, target key, SQL) or (source key, target key, SQL, extra binds); the
# fourth slot exists only for the repair edge below and is optional so the other eight read
# unchanged.
_OWNERSHIP_EDGES: tuple[tuple[str, str, str] | tuple[str, str, str, dict[str, str]], ...] = (
    # A Lead converted live (Slice 3D) creates an Opportunity the manifest never saw.
    (
        "lead_public_ids",
        "opportunity_public_ids",
        """
        SELECT o.opportunity_public_id FROM crm_opportunity o
        INNER JOIN crm_lead l ON l.id = o.source_lead_id
        WHERE l.lead_public_id IN :ids
        """,
    ),
    # ...and the Account that conversion created with it.
    #
    # Sourced from the LEAD, not from every owned Opportunity, and that distinction is the whole
    # point. An earlier version of this closure followed Opportunity -> Account for any owned
    # Opportunity, which treats "linked to" as "created by": independent review reproduced one
    # run deleting another run's pre-existing Account, simply because its own Opportunity had been
    # repaired onto it. An Account is a PARENT that several runs may point at, not a child of our
    # Opportunity, so reachability is not ownership here.
    #
    # Joining through crm_lead restricts this to the conversion case, where the Account genuinely
    # was created by us: `source_lead_id` is set once at conversion and only a conversion sets it.
    # An Account merely repaired onto one of our Opportunities is not reached.
    (
        "lead_public_ids",
        "account_public_ids",
        """
        SELECT bp.business_party_public_id FROM business_party bp
        INNER JOIN crm_opportunity o ON o.business_party_id = bp.id
        INNER JOIN crm_lead l ON l.id = o.source_lead_id
        WHERE l.lead_public_id IN :ids
        """,
    ),
    # An Account the Opportunity Account REPAIR flow created for an Opportunity we own (Slice
    # 6B.1). Sourced from PROVENANCE, not reachability: the repair records `repair_mode` against
    # the Opportunity, so `created_minimal_account` is ours - the Account had no prior existence -
    # while `existing_account` is somebody else's and is deliberately NOT matched. Two tests hold
    # that boundary and neither means anything without the other:
    # ..._the_repair_flow_created_for_an_owned_opportunity and
    # ..._does_not_delete_an_account_another_run_already_owned.
    #
    # Knock-on, stated rather than found later: once such an Account is ours, the downward edge
    # below takes any Opportunity someone else repaired onto it - the cascade the owner accepted
    # on 10 September 2026, reached through a wider set of owned Accounts, not a new rule.
    #
    # `::json ->>` on a text column follows audit_events.py. Every payload is json.dumps output so
    # the cast is total; the IS NOT NULL guard stops a missing key becoming the string "None".
    (
        "opportunity_public_ids",
        "account_public_ids",
        """
        SELECT (NULLIF(e.event_payload_json, '')::json ->> 'account_public_id')
        FROM business_event e
        WHERE e.record_public_id IN :ids
          AND e.event_name = :repair_event_name
          AND e.record_type = :opportunity_record_type
          AND (NULLIF(e.event_payload_json, '')::json ->> 'repair_mode') = :created_mode
          AND (NULLIF(e.event_payload_json, '')::json ->> 'account_public_id') IS NOT NULL
        """,
        {
            "repair_event_name": OPPORTUNITY_EVENT_ACCOUNT_REPAIRED,
            "opportunity_record_type": OPPORTUNITY_RECORD_TYPE,
            "created_mode": _REPAIR_MODE_CREATED_MINIMAL_ACCOUNT,
        },
    ),
    # Downward from an Account we own to its Opportunities - including one a user created against
    # it, or repaired onto it, after seeding. Without this the Account delete fails on its foreign
    # key.
    #
    # Owner decision, 10 September 2026: cascade downward without asking. "If the enquiry is being
    # deleted, why even ask - they can be deleted." The accepted consequence is that an
    # Opportunity someone else repaired onto an Account we own goes with that Account. That is a
    # genuine possibility rather than a theoretical one, and it is accepted rather than guarded:
    # if it ever causes a problem, a confirmation route is added then. Note this is the safe
    # direction - the dangerous one is the reverse, constrained above.
    (
        "account_public_ids",
        "opportunity_public_ids",
        """
        SELECT o.opportunity_public_id FROM crm_opportunity o
        INNER JOIN business_party bp ON bp.id = o.business_party_id
        WHERE bp.business_party_public_id IN :ids
        """,
    ),
    # Any offer on an owned Opportunity - not only related offers, which was the previous gap.
    (
        "opportunity_public_ids",
        "offer_public_ids",
        """
        SELECT co.offer_public_id FROM crm_commercial_offer co
        INNER JOIN crm_opportunity o ON o.id = co.opportunity_id
        WHERE o.opportunity_public_id IN :ids
        """,
    ),
    # A Supplementary Offer or Change Quotation raised against an owned Base Offer (Slice 6O.1).
    (
        "offer_public_ids",
        "offer_public_ids",
        """
        SELECT related.offer_public_id FROM crm_commercial_offer related
        INNER JOIN crm_commercial_offer base_offer ON base_offer.id = related.base_offer_id
        WHERE base_offer.offer_public_id IN :ids
        """,
    ),
    # A Work Order handed off from an owned offer (frozen Slice 6D.1 contract).
    (
        "offer_public_ids",
        "work_order_public_ids",
        """
        SELECT wo.work_order_public_id FROM crm_work_order wo
        INNER JOIN crm_commercial_offer o ON o.id = wo.commercial_offer_id
        WHERE o.offer_public_id IN :ids
        """,
    ),
    # An offer whose Change Quotation points at an owned Work Order (the opposite-direction link).
    (
        "work_order_public_ids",
        "offer_public_ids",
        """
        SELECT co.offer_public_id FROM crm_commercial_offer co
        INNER JOIN crm_work_order wo ON wo.id = co.related_work_order_id
        WHERE wo.work_order_public_id IN :ids
        """,
    ),
    # WRR-001 resource requirements on an owned Work Order's lines, seeded or added through the UI
    # afterwards. Found through the declared foreign key to the line, so a requirement is reached only
    # through the line it belongs to. Collected so their audit rows can be matched by type below.
    (
        "work_order_public_ids",
        "resource_requirement_public_ids",
        """
        SELECT rr.requirement_public_id FROM resource_requirement rr
        INNER JOIN crm_work_order_line wol ON wol.id = rr.work_order_line_id
        INNER JOIN crm_work_order wo ON wo.id = wol.work_order_id
        WHERE wo.work_order_public_id IN :ids
        """,
    ),
    # 8A core. An allocation fills one requirement and never moves to another: it is the run's by the run's
    # requirement, whoever made it - the harness, a tester or a Playwright test. Its kit lines go with it, and so do
    # the eligibility decisions stored for it and for its kit lines (requested for them), whatever asset each is
    # about. An allocation of someone else's requirement using the run's machines or kit is refused below.
    (
        "resource_requirement_public_ids",
        "resource_assignment_public_ids",
        "SELECT assignment_public_id FROM resource_assignment WHERE resource_requirement_public_id IN :ids",
    ),
    (
        "resource_assignment_public_ids",
        "resource_assignment_kit_public_ids",
        """
        SELECT k.kit_line_public_id FROM resource_assignment_kit k
        INNER JOIN resource_assignment a ON a.id = k.resource_assignment_id
        WHERE a.assignment_public_id IN :ids
        """,
    ),
    (
        "resource_assignment_public_ids",
        "eligibility_decision_public_ids",
        """
        SELECT decision_public_id FROM eligibility_decision
        WHERE requested_for_type = 'resource_assignment' AND requested_for_public_id IN :ids
        """,
    ),
    (
        "resource_assignment_kit_public_ids",
        "eligibility_decision_public_ids",
        """
        SELECT decision_public_id FROM eligibility_decision
        WHERE requested_for_type = 'resource_assignment_kit' AND requested_for_public_id IN :ids
        """,
    ),
    # Activities logged against an owned Lead after seeding. Previously only manifest-recorded
    # activity ids were known, so a live-created activity's audit row was left behind.
    (
        "lead_public_ids",
        "lead_activity_public_ids",
        """
        SELECT la.activity_public_id FROM crm_lead_activity la
        INNER JOIN crm_lead l ON l.id = la.lead_id
        WHERE l.lead_public_id IN :ids
        """,
    ),
    # ERT-1. Each edge is provenance, not reachability (TE-4): an import uploaded from a file only this run
    # wrote; a machine the run's own import brought in (registered_by_import_id is set once, when the
    # machine is first brought in); a value rule recorded on the run's own import's preview. A machine an
    # owned import merely updated, or a rule merely applied to one, is not reached.
    (
        _FINGERPRINT_GROUP,
        "equipment_import_public_ids",
        "SELECT import_public_id FROM equipment_source_import WHERE fingerprint IN :ids",
    ),
    (
        "equipment_import_public_ids",
        "equipment_asset_public_ids",
        """
        SELECT a.asset_public_id FROM equipment_asset a
        INNER JOIN equipment_source_import i ON i.id = a.registered_by_import_id
        WHERE i.import_public_id IN :ids
        """,
    ),
    (
        "equipment_import_public_ids",
        "equipment_value_rule_public_ids",
        """
        SELECT r.rule_public_id FROM equipment_source_value_rule r
        INNER JOIN equipment_source_import i ON i.id = r.recorded_during_import_id
        WHERE i.import_public_id IN :ids
        """,
    ),
    # ERT-2. A piece of kit is the run's when it was added as one of the run's kit models - from the screen
    # later too, and moved to another model since or not. Judged by the model its request asked for, which
    # never changes, not by the model it carries now (independent review, round 3, ERT2-R3-002): a piece
    # added as someone else's model and moved onto a run's is not the run's, and the refusal below stops
    # cleanup rather than delete it.
    (
        "equipment_model_public_ids",
        "equipment_asset_public_ids",
        """
        SELECT a.asset_public_id FROM equipment_asset a
        INNER JOIN equipment_model m ON m.id = a.create_request_model_id
        WHERE a.origin_code = 'PLATFORM' AND m.model_public_id IN :ids
        """,
    ),
    # Slice 4G. A market rate is the run's by its offer, whoever entered it, so the quote copies attached to it go
    # with it.
    (
        "offer_public_ids",
        "market_rate_public_ids",
        """
        SELECT pe.evidence_public_id FROM crm_commercial_offer_pricing_evidence pe
        INNER JOIN crm_commercial_offer o ON o.id = pe.commercial_offer_id
        WHERE o.offer_public_id IN :ids
        """,
    ),
    # ELG-1. A certificate, a "not applicable" mark and a stored decision are each about one asset and never
    # move to another: each is the run's by the asset it is on, whoever recorded it - the harness, a tester or
    # a Playwright test on the screen - as a piece of kit is the run's by its model.
    (
        "equipment_asset_public_ids",
        "eligibility_certificate_public_ids",
        "SELECT certificate_public_id FROM eligibility_certificate WHERE equipment_asset_public_id IN :ids",
    ),
    (
        "equipment_asset_public_ids",
        "eligibility_mark_public_ids",
        "SELECT mark_public_id FROM eligibility_not_applicable WHERE equipment_asset_public_id IN :ids",
    ),
    (
        "equipment_asset_public_ids",
        "eligibility_decision_public_ids",
        "SELECT decision_public_id FROM eligibility_decision WHERE equipment_asset_public_id IN :ids",
    ),
)


def _expand_ownership_closure(db: Session, ids: dict[str, list[str]]) -> dict[str, list[str]]:
    """Follows every relationship in _OWNERSHIP_EDGES repeatedly until no set grows.

    Terminates because each pass can only add ids, the id space is finite, and the loop exits the
    first time a full pass adds nothing. The bound is a safety net for a future edge that somehow
    cycles without converging; reaching it means an edge is wrong, so it raises rather than
    silently returning a partial closure that would look like a successful cleanup."""
    owned = {key: set(value) for key, value in ids.items()}
    for _ in range(_CLOSURE_MAX_PASSES):
        grew = False
        for source_key, target_key, sql, *extra_binds in _OWNERSHIP_EDGES:
            source_ids = sorted(owned[source_key])
            if not source_ids:
                continue
            found = set(_select_where_in(db, sql, source_ids, extra_binds[0] if extra_binds else None))
            new = found - owned[target_key]
            if new:
                # Every id the closure adds is re-validated, not only the ones the manifest
                # supplied. Most edges select a public_id column and cannot produce anything else,
                # but the repair edge reads an id out of a JSON payload, and an id that reaches a
                # DELETE without passing the same check as a manifest id would be a hole opened by
                # the very edge that closed one.
                for public_id in new:
                    _require_uuid(public_id)
                owned[target_key].update(new)
                grew = True
        if not grew:
            return {key: sorted(value) for key, value in owned.items()}
    raise CleanupValidationError(
        "Ownership discovery did not settle within "
        f"{_CLOSURE_MAX_PASSES} passes. An edge in _OWNERSHIP_EDGES is probably wrong; refusing "
        "to delete against an incomplete record set."
    )


def _owned_record_pairs(ids: dict[str, list[str]], interaction_ids: list[str]) -> list[tuple[str, str]]:
    """The (linked_record_type, public_id) pairs this run owns.

    Documents and interactions are matched on these pairs rather than on the id alone. The earlier
    design matched id-only, arguing that enumerating types risks a future link type escaping
    cleanup. Independent review rebutted that: a new OWNED type already requires updating
    discovery, so the enumeration is the same maintenance, not extra - and id-only matching in a
    shared database promises exact deletion while relying on uuid4 luck across tables that share
    no constraint. Both Account spellings are included deliberately: existing document rows say
    "account" while Slice 9D's canonical type is "business_party", and documents/contract.py maps
    both for exactly that reason."""
    pairs: list[tuple[str, str]] = []
    for account_public_id in ids["account_public_ids"]:
        pairs.append(("account", account_public_id))
        pairs.append(("business_party", account_public_id))
    for type_name, key in (
        ("opportunity", "opportunity_public_ids"),
        ("commercial_offer", "offer_public_ids"),
        ("work_order", "work_order_public_ids"),
        ("lead", "lead_public_ids"),
    ):
        pairs.extend((type_name, public_id) for public_id in ids[key])
    pairs.extend(("interaction", public_id) for public_id in interaction_ids)
    # ELG-1: a certificate's copies, which go with it.
    pairs.extend(("eligibility_certificate", public_id) for public_id in ids.get("eligibility_certificate_public_ids", []))
    # Slice 4G: a market rate's quote copies, which go with it.
    pairs.extend(("commercial_offer_market_rate", public_id) for public_id in ids.get("market_rate_public_ids", []))
    return pairs


def _delete_where_pairs(db: Session, sql: str, pairs: list[tuple[str, str]]) -> int:
    if not pairs:
        return 0
    statement = text(sql).bindparams(bindparam("pairs", expanding=True))
    return db.execute(statement, {"pairs": pairs}).rowcount or 0


def _select_where_pairs(db: Session, sql: str, pairs: list[tuple[str, str]]) -> list[dict[str, Any]]:
    if not pairs:
        return []
    statement = text(sql).bindparams(bindparam("pairs", expanding=True))
    return [dict(row._mapping) for row in db.execute(statement, {"pairs": pairs}).fetchall()]


# Which business_event.record_type each owned id group is written under. Matching on the id
# alone deletes another record type's event that happens to share it - reproduced by independent
# review, which created an unrelated event carrying an owned Account's id under a different type
# and watched cleanup remove it. Documents and interactions were already pair-matched; audit rows
# were not.
#
# `business_party` only: unlike the DOCUMENT link type, which genuinely appears as both `account`
# and `business_party`, no code writes a business_event with record_type "account" - accounts/
# service.py uses BUSINESS_PARTY_RECORD_TYPE throughout. Carrying the alias here was justified by
# the wrong evidence (independent review, ninth pass).
_EVENT_RECORD_TYPES: dict[str, tuple[str, ...]] = {
    "account_public_ids": ("business_party",),
    "opportunity_public_ids": ("opportunity",),
    "offer_public_ids": ("commercial_offer",),
    "work_order_public_ids": ("work_order",),
    "lead_public_ids": ("lead",),
    "lead_activity_public_ids": ("lead_activity",),
    "interaction_public_ids": ("interaction",),
    "document_public_ids": ("document_metadata",),
    "quote_document_public_ids": ("commercial_offer_quote_document",),
    "account_address_public_ids": ("business_party_address",),
    "account_gstin_public_ids": ("business_party_gstin",),
    "account_tax_profile_public_ids": ("business_party_tax_profile",),
    "account_contact_public_ids": ("business_party_contact",),
    "resource_requirement_public_ids": ("resource_requirement",),
    # 8A core: resource_assignments/contract.py's RESOURCE_ASSIGNMENT_RECORD_TYPE.
    "resource_assignment_public_ids": ("resource_assignment",),
    # ERT-1: equipment_reference/contract.py's RECORD_TYPE_* constants.
    "equipment_import_public_ids": ("equipment_import",),
    "equipment_asset_public_ids": ("equipment_asset",),
    "equipment_model_public_ids": ("equipment_model",),
    "equipment_value_rule_public_ids": ("equipment_value_rule",),
    "equipment_mapping_public_ids": ("equipment_model_mapping",),
    # ELG-1: eligibility/contract.py's RECORD_TYPE_* constants.
    "eligibility_certificate_public_ids": ("eligibility_certificate",),
    "eligibility_mark_public_ids": ("eligibility_not_applicable",),
    "eligibility_decision_public_ids": ("eligibility_decision",),
    # HOL-1: holiday_calendar/contract.py's RECORD_TYPE_YEAR.
    "holiday_calendar_year_public_ids": ("holiday_calendar_year",),
}


def _event_record_pairs(owned_ids: dict[str, list[str]]) -> list[tuple[str, str]]:
    """The (record_type, public_id) pairs this run's audit rows are written under.

    Shared with `status`, which counts residue against the same pairs. Two lists kept in step by
    hand is how cleanup and status came to disagree about what residue even was."""
    return [
        (record_type, public_id)
        for group, record_types in _EVENT_RECORD_TYPES.items()
        for public_id in owned_ids.get(group, [])
        for record_type in record_types
    ]


def _delete_events(db: Session, owned_ids: dict[str, list[str]]) -> int:
    pairs = _event_record_pairs(owned_ids)
    return _delete_where_pairs(
        db,
        "DELETE FROM business_event WHERE (record_type, record_public_id) IN :pairs",
        pairs,
    )


def _refuse_equipment_entanglement(db: Session, ids: dict[str, list[str]]) -> None:
    """Refuse, before deleting anything, when a record this run did NOT make depends on one it did: a
    machine of another run using one of this run's models, or bound to or corrected by one of its imports; a
    fitted-part link joining one of this run's assets to one it did not bring in; a mapping of a name the
    run's reports do not carry to one of its models; an import - a waiting preview included - that was
    compared with one of its imports. Deleting would break or silently change that record; leaving the run's
    record would leave the cleanup half-done. Neither is right, so nothing is done and the operator is told.
    It cannot arise from the harness's own records - their machine numbers and model names carry the run's
    token - so it means a person mapped a real name to a test model, or uploaded a report while a test's
    was the latest confirmed."""
    checks = (
        (
            "equipment_model_public_ids",
            """
            SELECT COUNT(*) FROM equipment_asset a
            INNER JOIN equipment_model m ON m.id = a.equipment_model_id
            WHERE m.model_public_id IN :ids AND NOT (a.asset_public_id = ANY(:owned_assets))
            """,
            "machines this run did not bring in use its models",
        ),
        (
            "equipment_import_public_ids",
            """
            SELECT COUNT(*) FROM equipment_source_binding b
            INNER JOIN equipment_asset a ON a.id = b.equipment_asset_id
            INNER JOIN equipment_source_import i ON i.id IN (b.first_import_id, b.last_import_id)
            WHERE i.import_public_id IN :ids AND NOT (a.asset_public_id = ANY(:owned_assets))
            """,
            "machines this run did not bring in were last read from its imports",
        ),
        (
            "equipment_import_public_ids",
            """
            SELECT COUNT(*) FROM equipment_asset_correction c
            INNER JOIN equipment_asset a ON a.id = c.equipment_asset_id
            INNER JOIN equipment_source_import i ON i.id = c.closed_by_import_id
            WHERE i.import_public_id IN :ids AND NOT (a.asset_public_id = ANY(:owned_assets))
            """,
            "corrections of machines this run did not bring in were closed by its imports",
        ),
    )
    params = {
        "owned_assets": ids["equipment_asset_public_ids"],
        "owned_imports": ids["equipment_import_public_ids"],
        "owned_names": ids[_SOURCE_NAME_GROUP],
    }
    for group, sql, what in checks:
        if not ids[group]:
            continue
        statement = text(sql).bindparams(bindparam("ids", expanding=True))
        found = db.execute(statement, {"ids": ids[group], "owned_assets": params["owned_assets"]}).scalar() or 0
        if found:
            raise CleanupValidationError(
                f"Refusing to clean up: {found} {what}. Remove that dependency by hand first; nothing was deleted."
            )
    # A fitted-part link, open or removed, with one end this run's and the other not: the link was made by a
    # person or another run, so it is not this run's to delete, and the run's asset cannot go without it
    # (independent review, round 1, ERT1-R1-001).
    owned_assets = ids["equipment_asset_public_ids"]
    if owned_assets:
        statement = text(
            """
            SELECT COUNT(*) FROM equipment_asset_link l
            INNER JOIN equipment_asset p ON p.id = l.parent_asset_id
            INNER JOIN equipment_asset c ON c.id = l.child_asset_id
            WHERE (p.asset_public_id IN :ids) <> (c.asset_public_id IN :ids)
            """
        ).bindparams(bindparam("ids", expanding=True))
        crossing = db.execute(statement, {"ids": owned_assets}).scalar() or 0
        if crossing:
            raise CleanupValidationError(
                f"Refusing to clean up: {crossing} fitted-part link(s) join this run's machines or parts to ones it "
                "did not bring in. Remove those links by hand first; nothing was deleted."
            )
    # A mapping of a name the run's reports do not carry, pointing at a run's model, is someone's own
    # configuration: deleting the model would delete it (independent review, round 2, ERT1-R2-001).
    if ids["equipment_model_public_ids"]:
        statement = text(
            """
            SELECT COUNT(*) FROM equipment_model_source_key k
            INNER JOIN equipment_model m ON m.id = k.equipment_model_id
            WHERE m.model_public_id IN :ids AND NOT (k.normalized_source_name = ANY(:owned_names))
            """
        ).bindparams(bindparam("ids", expanding=True))
        mapped = db.execute(statement, {"ids": ids["equipment_model_public_ids"], "owned_names": params["owned_names"]}).scalar() or 0
        if mapped:
            raise CleanupValidationError(
                f"Refusing to clean up: {mapped} Plum model name(s) this run's reports do not carry are mapped to its "
                "models. Map them to another model by hand first; nothing was deleted."
            )
    # ERT-2. A kit model the run did not make, fitting one of the run's crane models, is someone's own
    # configuration: deleting the crane model would take the fit with it.
    if ids["equipment_model_public_ids"]:
        statement = text(
            """
            SELECT COUNT(*) FROM equipment_model_fit f
            INNER JOIN equipment_model c ON c.id = f.crane_model_id
            INNER JOIN equipment_model k ON k.id = f.kit_model_id
            WHERE c.model_public_id IN :ids AND NOT (k.model_public_id = ANY(:owned_models))
            """
        ).bindparams(bindparam("ids", expanding=True))
        fitted = db.execute(statement, {"ids": ids["equipment_model_public_ids"], "owned_models": ids["equipment_model_public_ids"]}).scalar() or 0
        if fitted:
            raise CleanupValidationError(
                f"Refusing to clean up: {fitted} kit model(s) this run did not make fit its crane models. Take those "
                "crane models off them by hand first; nothing was deleted."
            )
    # An import of someone else's compared with one of the run's: deleting the run's import would change it,
    # and could make a waiting preview look current against a fleet it was not computed from (ERT1-R2-001).
    if ids["equipment_import_public_ids"]:
        statement = text(
            """
            SELECT COUNT(*) FROM equipment_source_import o
            INNER JOIN equipment_source_import b ON b.id = o.based_on_import_id
            WHERE b.import_public_id IN :ids AND NOT (o.import_public_id = ANY(:owned_imports))
            """
        ).bindparams(bindparam("ids", expanding=True))
        compared = db.execute(statement, {"ids": ids["equipment_import_public_ids"], "owned_imports": params["owned_imports"]}).scalar() or 0
        if compared:
            raise CleanupValidationError(
                f"Refusing to clean up: {compared} import(s) this run did not make were compared with its imports. "
                "Discard or confirm them first, or clean up after the next report is confirmed; nothing was deleted."
            )


def _refuse_eligibility_entanglement(db: Session, ids: dict[str, list[str]]) -> None:
    """ELG-1. Refuse, before deleting anything, when a stored decision about an asset this run did not bring in
    used one of the run's assets, or a certificate or mark on one - a part fitted to that machine when it was
    judged, or the carrier whose papers met the machine's rule - since deleting it would break that decision's
    record. A result names the asset of the unit it is about and, separately, the certificate or mark that met it
    (independent review, round 3, ELG1-R3-004). The run's own certificates, marks and decisions are the run's by
    their asset and go with it."""
    owned_assets = ids["equipment_asset_public_ids"]
    if not owned_assets:
        return
    statement = text(
        """
        SELECT COUNT(DISTINCT d.id) FROM eligibility_decision_result r
        INNER JOIN eligibility_decision d ON d.id = r.decision_id
        LEFT JOIN eligibility_certificate c ON c.id = r.certificate_id
        LEFT JOIN eligibility_not_applicable m ON m.id = r.mark_id
        WHERE NOT (d.equipment_asset_public_id = ANY(:owned_assets))
          AND (r.equipment_asset_public_id IN :ids OR c.equipment_asset_public_id IN :ids OR m.equipment_asset_public_id IN :ids)
        """
    ).bindparams(bindparam("ids", expanding=True))
    used = db.execute(statement, {"ids": owned_assets, "owned_assets": owned_assets}).scalar() or 0
    if used:
        raise CleanupValidationError(
            f"Refusing to clean up: {used} eligibility decision(s) about machines this run did not bring in used its "
            "machines or parts. Remove them by hand first; nothing was deleted."
        )


def _refuse_allocation_entanglement(db: Session, ids: dict[str, list[str]]) -> None:
    """8A core. Refuse, before deleting anything, when an allocation this run did not make - of someone else's
    requirement - holds or held one of the run's machines, or lists or listed one of its pieces of kit: a replaced
    or freed allocation keeps its machine and kit on the Work Order's history, so deleting the machine or piece
    would break that record, and leaving it would leave the cleanup half-done. The harness allocates only to its
    own requirements, so this means a person allocated a test machine to a real Work Order."""
    owned_assets = ids["equipment_asset_public_ids"]
    if not owned_assets:
        return
    statement = text(
        """
        SELECT COUNT(DISTINCT a.id) FROM resource_assignment a
        LEFT JOIN resource_assignment_kit k ON k.resource_assignment_id = a.id
        WHERE NOT (a.assignment_public_id = ANY(:owned_assignments))
          AND (a.equipment_asset_public_id IN :ids OR k.equipment_asset_public_id IN :ids)
        """
    ).bindparams(bindparam("ids", expanding=True))
    used = db.execute(statement, {"ids": owned_assets, "owned_assignments": ids["resource_assignment_public_ids"]}).scalar() or 0
    if used:
        raise CleanupValidationError(
            f"Refusing to clean up: {used} allocation(s) of requirements this run did not make hold or held its "
            "machines or kit, and keep them on their Work Orders' history. Nothing was deleted."
        )


def _delete_allocations(db: Session, ids: dict[str, list[str]]) -> dict[str, int]:
    """8A core: the run's allocations - their kit lines and trips first, and each replacement's link to the one it
    replaced - before the eligibility decisions they keep and the machines they hold."""
    assignments = ids["resource_assignment_public_ids"]
    counts: dict[str, int] = {}
    counts["resource_assignment_kit_lines"] = _delete_where_in(
        db,
        """
        DELETE FROM resource_assignment_kit k USING resource_assignment a
        WHERE a.id = k.resource_assignment_id AND a.assignment_public_id IN :ids
        """,
        assignments,
    )
    counts["resource_assignment_trips"] = _delete_where_in(
        db,
        """
        DELETE FROM resource_assignment_trip t USING resource_assignment a
        WHERE a.id = t.resource_assignment_id AND a.assignment_public_id IN :ids
        """,
        assignments,
    )
    # The run's allocations go with their requirements, so no status is left behind: marked as the service's own
    # write, which the database requires of any allocation write (8A-FA2-001).
    mark_service_write(db)
    _delete_where_in(
        db, "UPDATE resource_assignment SET replaces_assignment_id = NULL WHERE assignment_public_id IN :ids", assignments
    )
    counts["resource_assignments"] = _delete_where_in(
        db, "DELETE FROM resource_assignment WHERE assignment_public_id IN :ids", assignments
    )
    # The request keys that made them, and any refused or replayed use of those keys: by the run's requirements.
    counts["resource_assignment_requests"] = _delete_where_in(
        db,
        "DELETE FROM resource_assignment_request WHERE resource_requirement_public_id IN :ids",
        ids["resource_requirement_public_ids"],
    )
    return counts


def _delete_eligibility(db: Session, ids: dict[str, list[str]]) -> dict[str, int]:
    """ELG-1: the run's decisions with their results, marks and certificates, before the assets they are on.
    Their copies are documents, deleted with the run's other documents; the rules are the platform's and stay."""
    decisions = ids["eligibility_decision_public_ids"]
    counts: dict[str, int] = {}
    # ELG-2: the "seen" marks on reminders about the run's assets, allocations and kit lines, whoever made them - a
    # tester or a Playwright test on the Alerts page. A mark is a person's own view of a reminder, kept only for it,
    # so it goes with what it is about.
    counts["eligibility_alert_acknowledgements"] = _delete_where_in(
        db, "DELETE FROM eligibility_alert_acknowledgement WHERE equipment_asset_public_id IN :ids", ids["equipment_asset_public_ids"]
    ) + _delete_where_in(
        db,
        "DELETE FROM eligibility_alert_acknowledgement WHERE subject_public_id IN :ids",
        [*ids["resource_assignment_public_ids"], *ids["resource_assignment_kit_public_ids"]],
    )
    counts["eligibility_decision_results"] = _delete_where_in(
        db,
        """
        DELETE FROM eligibility_decision_result r USING eligibility_decision d
        WHERE d.id = r.decision_id AND d.decision_public_id IN :ids
        """,
        decisions,
    )
    counts["eligibility_decisions"] = _delete_where_in(
        db, "DELETE FROM eligibility_decision WHERE decision_public_id IN :ids", decisions
    )
    counts["eligibility_marks"] = _delete_where_in(
        db, "DELETE FROM eligibility_not_applicable WHERE mark_public_id IN :ids", ids["eligibility_mark_public_ids"]
    )
    counts["eligibility_certificates"] = _delete_where_in(
        db, "DELETE FROM eligibility_certificate WHERE certificate_public_id IN :ids", ids["eligibility_certificate_public_ids"]
    )
    return counts


def _delete_equipment(db: Session, ids: dict[str, list[str]]) -> dict[str, int]:
    """ERT-1: delete this run's models, imports, machines and value rules, children first - and (ERT-2) its
    kit models' fits and pieces of kit, which are its assets by their model. Flags a run's
    import raised on other machines (NOT_IN_LATEST_REPORT on a machine missing from an invented report)
    go with the import that raised them. Mappings are the run's by the names its reports carry, whichever
    model they point at. Everything else another run made is left: what would be changed or broken by
    these deletions was refused beforehand (_refuse_equipment_entanglement)."""
    assets, imports = ids["equipment_asset_public_ids"], ids["equipment_import_public_ids"]
    models, rules = ids["equipment_model_public_ids"], ids["equipment_value_rule_public_ids"]
    counts: dict[str, int] = {}
    counts["equipment_asset_flags"] = _delete_where_in(
        db,
        """
        DELETE FROM equipment_asset_flag f USING equipment_asset a
        WHERE a.id = f.equipment_asset_id AND a.asset_public_id IN :ids
        """,
        assets,
    ) + _delete_where_in(
        db,
        """
        DELETE FROM equipment_asset_flag f USING equipment_source_import i
        WHERE i.id = f.raised_by_import_id AND i.import_public_id IN :ids
        """,
        imports,
    )
    for table, key in (
        ("equipment_asset_correction", "equipment_asset_corrections"),
        ("equipment_asset_capability", "equipment_asset_capabilities"),
        ("equipment_source_binding", "equipment_source_bindings"),
    ):
        counts[key] = _delete_where_in(
            db,
            f"""
            DELETE FROM {table} t USING equipment_asset a
            WHERE a.id = t.equipment_asset_id AND a.asset_public_id IN :ids
            """,
            assets,
        )
    counts["equipment_asset_links"] = _delete_where_in(
        db,
        """
        DELETE FROM equipment_asset_link l USING equipment_asset a
        WHERE a.id IN (l.parent_asset_id, l.child_asset_id) AND a.asset_public_id IN :ids
        """,
        assets,
    )
    counts["equipment_assets"] = _delete_where_in(db, "DELETE FROM equipment_asset WHERE asset_public_id IN :ids", assets)
    counts["equipment_value_rules"] = _delete_where_in(
        db, "DELETE FROM equipment_source_value_rule WHERE rule_public_id IN :ids", rules
    )
    counts["equipment_model_mappings"] = _delete_where_in(
        db, "DELETE FROM equipment_model_source_key WHERE normalized_source_name IN :ids", ids[_SOURCE_NAME_GROUP]
    ) + _delete_where_in(
        # Only the run's names can still point at its models: any other was refused above.
        db,
        """
        DELETE FROM equipment_model_source_key t USING equipment_model m
        WHERE m.id = t.equipment_model_id AND m.model_public_id IN :ids
        """,
        models,
    )
    # ERT-2: the run's kit models' fits, and any fit to one of its crane models - only a run's kit model can
    # still hold one, since any other was refused above.
    counts["equipment_model_fits"] = _delete_where_in(
        db,
        """
        DELETE FROM equipment_model_fit f USING equipment_model m
        WHERE m.id IN (f.kit_model_id, f.crane_model_id) AND m.model_public_id IN :ids
        """,
        models,
    )
    for table, key in (("equipment_model_capability", "equipment_model_capabilities"),):
        counts[key] = _delete_where_in(
            db,
            f"""
            DELETE FROM {table} t USING equipment_model m
            WHERE m.id = t.equipment_model_id AND m.model_public_id IN :ids
            """,
            models,
        )
    counts["equipment_models"] = _delete_where_in(db, "DELETE FROM equipment_model WHERE model_public_id IN :ids", models)
    counts["equipment_import_rows"] = _delete_where_in(
        db,
        """
        DELETE FROM equipment_source_import_row r USING equipment_source_import i
        WHERE i.id = r.equipment_source_import_id AND i.import_public_id IN :ids
        """,
        imports,
    )
    counts["equipment_imports"] = _delete_where_in(
        db, "DELETE FROM equipment_source_import WHERE import_public_id IN :ids", imports
    )
    return counts


def _delete_holiday_calendar_years(db: Session, ids: dict[str, list[str]]) -> dict[str, int]:
    """HOL-1: the run's years of PBL's calendar, with their holidays and the states those name. Nothing else holds a key
    to them: a Work Order's changes refer to a date, not to the calendar."""
    years = ids.get("holiday_calendar_year_public_ids", [])
    counts: dict[str, int] = {}
    counts["holiday_calendar_holiday_states"] = _delete_where_in(
        db,
        """
        DELETE FROM holiday_calendar_holiday_state s
        USING holiday_calendar_holiday h, holiday_calendar_year y
        WHERE h.id = s.holiday_id AND y.id = h.year_id AND y.year_public_id IN :ids
        """,
        years,
    )
    counts["holiday_calendar_holidays"] = _delete_where_in(
        db,
        """
        DELETE FROM holiday_calendar_holiday h
        USING holiday_calendar_year y
        WHERE y.id = h.year_id AND y.year_public_id IN :ids
        """,
        years,
    )
    counts["holiday_calendar_years"] = _delete_where_in(
        db, "DELETE FROM holiday_calendar_year WHERE year_public_id IN :ids", years
    )
    return counts


def cleanup_manifest(manifest: dict[str, Any]) -> dict[str, int]:
    """Deletes this run's records in FK-safe child-to-parent order, reporting rows removed per
    table.

    NOT only the records the manifest names: the manifest's anchors are the starting point, and
    the ownership closure then takes what descends from them - including records a user or another
    run created there afterwards. That downward cascade is deliberate (owner decision, 10 September
    2026). See `_OWNERSHIP_EDGES` for what is and is not reached.

    Idempotent: re-running against an already-cleaned manifest reports zero deletions everywhere
    and does not raise, since "nothing left to delete" is success, not failure."""
    validate_manifest_dict(manifest)
    ids = _collect_ids(manifest)
    if not any(ids.values()):
        raise CleanupValidationError(
            "Manifest contains no recognizable account/opportunity/offer/work-order ids; "
            "refusing to run a cleanup that would be a no-op against an unrecognized manifest shape."
        )

    counts: dict[str, int] = {}
    with SessionLocal() as db:
        # One closure over every ownership relationship, replacing the sequence of one-level
        # discovery calls that two reviews found incomplete in six different places.
        ids = _expand_ownership_closure(db, ids)
        owned_work_order_ids = ids["work_order_public_ids"]

        # ---------------------------------------------------------------------------------
        # Discover EVERYTHING first, then delete.
        #
        # The four selects below used to sit further down, interleaved with the deletes, and the
        # scope recorded only the six closure groups. The fifth review showed what that costs: a
        # document attached to an INTERACTION is reachable through no surviving record once the
        # interaction is deleted, so `status` could not see it and certified the reset as clean.
        # The same argument applies to quote documents and the account sub-records, whose parents
        # are also gone by the time anyone asks.
        #
        # None of these selects depends on a delete below - each is derived from the closure ids,
        # and every table they read is deleted later - so collecting them first changes nothing
        # about what is found.
        # ---------------------------------------------------------------------------------
        owned_quote_document_ids = _select_where_in(
            db,
            """
            SELECT q.quote_document_public_id
            FROM crm_commercial_offer_quote_document q
            INNER JOIN crm_commercial_offer o ON o.id = q.commercial_offer_id
            WHERE o.offer_public_id IN :ids
            """,
            ids["offer_public_ids"],
        )
        owned_interaction_ids = [
            row["interaction_public_id"]
            for row in _select_where_pairs(
                db,
                """
                SELECT interaction_public_id FROM interaction
                WHERE (linked_record_type, linked_record_public_id) IN :pairs
                """,
                _owned_record_pairs(ids, []),
            )
        ]

        # A document can be attached to an INTERACTION as well as to the five anchor types -
        # `interaction` is a first-class link type with its own extra content permission
        # (documents/contract.py, DOCUMENT_LINK_EXTRA_CONTENT_PERMISSION). A pilot user attaching
        # a file to a call they logged is therefore ordinary use, not an edge case, and its
        # document hangs off the interaction's public id rather than the offer's. Deleting the
        # interaction without this would orphan that document AND leak its bytes.
        document_pairs = _owned_record_pairs(ids, owned_interaction_ids)
        document_rows = _select_where_pairs(
            db,
            """
            SELECT document_public_id, storage_provider_code, storage_key
            FROM document_metadata
            WHERE (linked_record_type, linked_record_public_id) IN :pairs
            """,
            document_pairs,
        )
        owned_account_sub_records = _find_owned_account_sub_record_ids(db, ids["account_public_ids"])

        # Every id this run owns, by record type, held in memory for the deletes below and for
        # the audit rows - which are matched on (record_type, public_id) because a public id is
        # not unique across record types.
        owned_ids = {
            **ids,
            "interaction_public_ids": sorted(owned_interaction_ids),
            "document_public_ids": sorted(str(row["document_public_id"]) for row in document_rows),
            "quote_document_public_ids": sorted(owned_quote_document_ids),
            **owned_account_sub_records,
        }

        # ERT-1 equipment records hold no foreign key to any CRM table and none to them, so they go first -
        # ELG-1 eligibility records before the assets they are on -
        # after the check that nothing another run made depends on them.
        _refuse_equipment_entanglement(db, ids)
        _refuse_eligibility_entanglement(db, ids)
        _refuse_allocation_entanglement(db, ids)
        # 8A core: allocations keep eligibility decisions and hold machines, so they go before both.
        counts.update(_delete_allocations(db, ids))
        counts.update(_delete_eligibility(db, ids))
        counts.update(_delete_equipment(db, ids))
        counts.update(_delete_holiday_calendar_years(db, ids))

        # Break crm_commercial_offer.related_work_order_id -> crm_work_order.id (Slice 6O.1)
        # before crm_work_order rows are deleted below, or that opposite-direction FK
        # would block deleting a Work Order a Change Quotation still links to.
        _null_out_related_work_order_links(db, ids["offer_public_ids"])

        # Slice 6O.2 Work Order Amendments are discovered by Work Order ownership, exactly
        # like crm_work_order_line below (their own manifest key, "amendments", is metadata
        # for readability/URLs only, not the cleanup safety key) - every amendment's
        # work_order_id is NOT NULL, so any amendment attached to an owned Work Order is
        # unambiguously this run's to clean up, including ones a Playwright test creates
        # live and the seed-time manifest never knew about. Amendment lines must be deleted
        # first (they FK to both crm_work_order_amendment and crm_work_order_line), then
        # amendments (they FK to crm_work_order and, optionally, crm_commercial_offer) -
        # both before crm_work_order_line / crm_work_order below.
        counts["work_order_amendment_lines"] = _delete_where_in(
            db,
            """
            DELETE FROM crm_work_order_amendment_line wal
            USING crm_work_order_amendment wa, crm_work_order wo
            WHERE wa.id = wal.amendment_id
              AND wo.id = wa.work_order_id
              AND wo.work_order_public_id IN :ids
            """,
            owned_work_order_ids,
        )
        counts["work_order_amendments"] = _delete_where_in(
            db,
            """
            DELETE FROM crm_work_order_amendment wa
            USING crm_work_order wo
            WHERE wo.id = wa.work_order_id
              AND wo.work_order_public_id IN :ids
            """,
            owned_work_order_ids,
        )

        # WRR-001 resource requirements: each carries a declared FK to crm_work_order_line, each item to
        # its requirement and each capability to its item, so they go in that order, before the lines.
        # Found by Work Order ownership through the line, like the 7C and 7D rows below.
        counts["resource_requirement_item_capabilities"] = _delete_where_in(
            db,
            """
            DELETE FROM resource_requirement_item_capability c
            USING resource_requirement_item i, resource_requirement rr, crm_work_order_line wol, crm_work_order wo
            WHERE i.id = c.resource_requirement_item_id
              AND rr.id = i.resource_requirement_id
              AND wol.id = rr.work_order_line_id
              AND wo.id = wol.work_order_id
              AND wo.work_order_public_id IN :ids
            """,
            owned_work_order_ids,
        )
        counts["resource_requirement_items"] = _delete_where_in(
            db,
            """
            DELETE FROM resource_requirement_item i
            USING resource_requirement rr, crm_work_order_line wol, crm_work_order wo
            WHERE rr.id = i.resource_requirement_id
              AND wol.id = rr.work_order_line_id
              AND wo.id = wol.work_order_id
              AND wo.work_order_public_id IN :ids
            """,
            owned_work_order_ids,
        )
        counts["resource_requirements"] = _delete_where_in(
            db,
            """
            DELETE FROM resource_requirement rr
            USING crm_work_order_line wol, crm_work_order wo
            WHERE wol.id = rr.work_order_line_id
              AND wo.id = wol.work_order_id
              AND wo.work_order_public_id IN :ids
            """,
            owned_work_order_ids,
        )

        # Slice 7C line operational detail: one row per Work Order line, recorded after handoff
        # (seeded or through the UI), found by Work Order ownership like the lines themselves. It
        # carries a declared FK to crm_work_order_line and to the Account's address and GSTIN
        # public ids, so it must go before the lines here and before the Account sub-records later.
        # Slice 7D billing terms: one row per period per line, with a declared FK to the line.
        counts["work_order_line_billing_terms"] = _delete_where_in(
            db,
            """
            DELETE FROM crm_work_order_line_billing_term t
            USING crm_work_order_line wol, crm_work_order wo
            WHERE wol.id = t.work_order_line_id
              AND wo.id = wol.work_order_id
              AND wo.work_order_public_id IN :ids
            """,
            owned_work_order_ids,
        )
        counts["work_order_line_details"] = _delete_where_in(
            db,
            """
            DELETE FROM crm_work_order_line_detail d
            USING crm_work_order_line wol, crm_work_order wo
            WHERE wol.id = d.work_order_line_id
              AND wo.id = wol.work_order_id
              AND wo.work_order_public_id IN :ids
            """,
            owned_work_order_ids,
        )
        counts["work_order_lines"] = _delete_where_in(
            db,
            """
            DELETE FROM crm_work_order_line wol
            USING crm_work_order wo
            WHERE wo.id = wol.work_order_id
              AND wo.work_order_public_id IN :ids
            """,
            owned_work_order_ids,
        )
        # Slice 7D Part 3: the contract period and its extensions carry a declared FK to
        # crm_work_order itself, so they go after the lines and before the Work Order. Found by Work
        # Order ownership, like everything else here: whether a row was seeded or added through the
        # UI afterwards makes no difference to whose it is.
        counts["work_order_contract_extensions"] = _delete_where_in(
            db,
            """
            DELETE FROM crm_work_order_contract_extension e
            USING crm_work_order wo
            WHERE wo.id = e.work_order_id
              AND wo.work_order_public_id IN :ids
            """,
            owned_work_order_ids,
        )
        counts["work_order_contract_periods"] = _delete_where_in(
            db,
            """
            DELETE FROM crm_work_order_contract_period p
            USING crm_work_order wo
            WHERE wo.id = p.work_order_id
              AND wo.work_order_public_id IN :ids
            """,
            owned_work_order_ids,
        )
        # Slice 7D Part 4: the holidays a Work Order names. Each date carries a declared FK to its list,
        # and the list one to crm_work_order, so the dates go first, then the list, then the Work Order.
        # Found by Work Order ownership like Part 3's rows: a list entered through the UI after seeding
        # still belongs to the run that owns the Work Order.
        counts["work_order_holidays"] = _delete_where_in(
            db,
            """
            DELETE FROM crm_work_order_holiday h
            USING crm_work_order_holiday_list l, crm_work_order wo
            WHERE l.id = h.work_order_holiday_list_id
              AND wo.id = l.work_order_id
              AND wo.work_order_public_id IN :ids
            """,
            owned_work_order_ids,
        )
        counts["work_order_holiday_lists"] = _delete_where_in(
            db,
            """
            DELETE FROM crm_work_order_holiday_list l
            USING crm_work_order wo
            WHERE wo.id = l.work_order_id
              AND wo.work_order_public_id IN :ids
            """,
            owned_work_order_ids,
        )
        counts["work_orders"] = _delete_where_in(
            db, "DELETE FROM crm_work_order WHERE work_order_public_id IN :ids", owned_work_order_ids
        )
        counts["customer_responses"] = _delete_where_in(
            db,
            """
            DELETE FROM commercial_offer_customer_response r
            USING crm_commercial_offer o
            WHERE o.id = r.commercial_offer_id
              AND o.offer_public_id IN :ids
            """,
            ids["offer_public_ids"],
        )
        counts["revisions"] = _delete_where_in(
            db,
            """
            DELETE FROM commercial_offer_revision rv
            USING crm_commercial_offer o
            WHERE o.id = rv.commercial_offer_id
              AND o.offer_public_id IN :ids
            """,
            ids["offer_public_ids"],
        )
        counts["credit_reviews"] = _delete_where_in(
            db,
            """
            DELETE FROM commercial_offer_credit_review cr
            USING crm_commercial_offer o
            WHERE o.id = cr.commercial_offer_id
              AND o.offer_public_id IN :ids
            """,
            ids["offer_public_ids"],
        )
        counts["submission_evidence"] = _delete_where_in(
            db,
            """
            DELETE FROM commercial_offer_submission_evidence se
            USING crm_commercial_offer o
            WHERE o.id = se.commercial_offer_id
              AND o.offer_public_id IN :ids
            """,
            ids["offer_public_ids"],
        )
        counts["tc_clause_attachments"] = _delete_where_in(
            db,
            """
            DELETE FROM commercial_offer_tc_clause tc
            USING crm_commercial_offer o
            WHERE o.id = tc.commercial_offer_id
              AND o.offer_public_id IN :ids
            """,
            ids["offer_public_ids"],
        )
        # Slice 4G: each line's basis history, before the rates and lines it names.
        counts["line_basis_choices"] = _delete_where_in(
            db,
            """
            DELETE FROM crm_commercial_offer_line_basis_choice choice
            USING crm_commercial_offer_line ol, crm_commercial_offer o
            WHERE ol.id = choice.commercial_offer_line_id
              AND o.id = ol.commercial_offer_id
              AND o.offer_public_id IN :ids
            """,
            ids["offer_public_ids"],
        )
        counts["pricing_evidence"] = _delete_where_in(
            db,
            """
            DELETE FROM crm_commercial_offer_pricing_evidence pe
            USING crm_commercial_offer o
            WHERE o.id = pe.commercial_offer_id
              AND o.offer_public_id IN :ids
            """,
            ids["offer_public_ids"],
        )
        counts["offer_lines"] = _delete_where_in(
            db,
            """
            DELETE FROM crm_commercial_offer_line ol
            USING crm_commercial_offer o
            WHERE o.id = ol.commercial_offer_id
              AND o.offer_public_id IN :ids
            """,
            ids["offer_public_ids"],
        )
        # Quote documents, documents and interactions attach to owned records with NO declared
        # foreign key (application-enforced `commercial_offer_id`; `linked_record_public_id`).
        # The parent DELETE therefore does not fail - it succeeds and orphans the child. Each also
        # writes its business_event keyed by its OWN public id, which is why discovery runs above,
        # before anything is deleted.
        counts["quote_documents"] = _delete_where_in(
            db,
            """
            DELETE FROM crm_commercial_offer_quote_document q
            USING crm_commercial_offer o
            WHERE o.id = q.commercial_offer_id
              AND o.offer_public_id IN :ids
            """,
            ids["offer_public_ids"],
        )

        # The rows were read above and are deleted here; their stored bytes are removed only
        # AFTER the transaction commits - see the loop below the `with` block for why that
        # ordering is the safe one. Matching is on (linked_record_type, public_id) pairs; see
        # _owned_record_pairs for why type-blind matching was rejected.
        counts["documents"] = _delete_where_pairs(
            db,
            "DELETE FROM document_metadata WHERE (linked_record_type, linked_record_public_id) IN :pairs",
            document_pairs,
        )

        interaction_pairs = _owned_record_pairs(ids, [])
        counts["interaction_participants"] = _delete_where_pairs(
            db,
            """
            DELETE FROM interaction_participant p
            USING interaction i
            WHERE i.id = p.interaction_id
              AND (i.linked_record_type, i.linked_record_public_id) IN :pairs
            """,
            interaction_pairs,
        )
        counts["interactions"] = _delete_where_pairs(
            db,
            "DELETE FROM interaction WHERE (linked_record_type, linked_record_public_id) IN :pairs",
            interaction_pairs,
        )

        counts["commercial_offers"] = _delete_where_in(
            db, "DELETE FROM crm_commercial_offer WHERE offer_public_id IN :ids", ids["offer_public_ids"]
        )
        counts["opportunities"] = _delete_where_in(
            db, "DELETE FROM crm_opportunity WHERE opportunity_public_id IN :ids", ids["opportunity_public_ids"]
        )
        # Lead cleanup (Slice 6P vendor-demo-bundle is the first scenario to seed Leads) must run
        # after opportunities are deleted above: crm_opportunity.source_lead_id -> crm_lead.id
        # (Slice 3D's filtered unique index) would otherwise block deleting a converted Lead.
        # Two paths, because the manifest can name an activity without naming its Lead. Deleting
        # only through the Lead meant such a manifest passed the guard above, removed the
        # activity's AUDIT EVENT, left the row, and reported success (independent review, ninth
        # pass). In the ordinary case the closure has already found the activity from its Lead, so
        # the second delete matches nothing.
        counts["lead_activities"] = _delete_where_in(
            db,
            """
            DELETE FROM crm_lead_activity la
            USING crm_lead l
            WHERE l.id = la.lead_id
              AND l.lead_public_id IN :ids
            """,
            ids["lead_public_ids"],
        )
        counts["lead_activities"] += _delete_where_in(
            db,
            "DELETE FROM crm_lead_activity WHERE activity_public_id IN :ids",
            ids["lead_activity_public_ids"],
        )
        counts["leads"] = _delete_where_in(
            db, "DELETE FROM crm_lead WHERE lead_public_id IN :ids", ids["lead_public_ids"]
        )
        # A practice customer carrying a registered address, several GSTINs and a PAN is the whole
        # point of the UAT dataset, and every one of these tables FKs to business_party with no
        # ondelete clause. Unlike the three above, this one fails loudly - the accounts DELETE
        # raises a ForeignKeyViolation and aborts the entire cleanup - so it is the more visible
        # half of the same gap, not the more dangerous half. Ids are collected first because each
        # row's creation wrote a business_event keyed by its own public id, not the Account's; they
        # are collected above with everything else, before anything is deleted.
        for table, _id_column, _group, count_key in _ACCOUNT_SUB_RECORD_TABLES:
            counts[count_key] = _delete_where_in(
                db,
                f"""
                DELETE FROM {table} sub
                USING business_party bp
                WHERE bp.id = sub.business_party_id
                  AND bp.business_party_public_id IN :ids
                """,
                ids["account_public_ids"],
            )

        counts["accounts"] = _delete_where_in(
            db, "DELETE FROM business_party WHERE business_party_public_id IN :ids", ids["account_public_ids"]
        )
        counts["business_events"] = _delete_events(db, owned_ids)
        db.commit()

    # Stored bytes are removed only now, AFTER the transaction has committed.
    #
    # The obvious ordering - delete the file, then the row - is the wrong way round. Everything
    # above runs in one transaction with a single commit, and any failure rolls the rows back but
    # nothing rolls a file back. That would leave live `document_metadata` rows whose `storage_key`
    # points at nothing. Committing first puts the residual risk on the recoverable side: the rows
    # are gone and some bytes may remain. Those keys are named in CleanupStorageError below and
    # nowhere else - which is exactly what the E2E and runbook recovery instructions say.
    #
    # Driven by this pass's discovered rows. The keys are deliberately NOT persisted, so an
    # interrupted cleanup cannot retry them automatically - CleanupStorageError names them and they
    # are removed by hand.
    leaked: list[str] = []
    storage_deleted = 0
    for document_row in document_rows:
        provider_code = document_row.get("storage_provider_code")
        storage_key = document_row.get("storage_key")
        if not provider_code or not storage_key:
            # A metadata-only row (an external link) has no bytes of its own to remove.
            continue
        leak_id = f"{provider_code}:{storage_key}"
        try:
            provider = get_storage_provider_by_code(provider_code)
        except Exception:  # noqa: BLE001 - an unresolvable provider is a failed deletion
            leaked.append(leak_id)
            continue

        # `exists` is a counter, not a gate, and the two are separated so a failing probe cannot
        # skip the delete. A comment here once claimed `delete` was "always called" while this
        # probe sat in the same try block ahead of it - the fifth such prose/code contradiction in
        # this package, and a real leak for any provider that cannot answer but can delete.
        try:
            existed = provider.exists(storage_key=storage_key)
        except Exception:  # noqa: BLE001 - cannot tell; proceed to the delete regardless
            existed = None

        try:
            provider.delete(storage_key=storage_key)
        except Exception:  # noqa: BLE001 - an invalid key or a provider that is down
            leaked.append(leak_id)
            continue

        # Confirm removal. `delete` returning without raising is not proof: the local provider
        # reports False from `exists` for a key it refuses, so a refused deletion and a successful
        # one look identical without an after-check.
        try:
            if provider.exists(storage_key=storage_key):
                leaked.append(leak_id)
                continue
        except Exception:  # noqa: BLE001 - cannot confirm removal, so do not claim it
            leaked.append(leak_id)
            continue

        if existed:
            storage_deleted += 1

    counts["documents_storage_deleted"] = storage_deleted

    if leaked:
        raise CleanupStorageError(
            "Database cleanup committed successfully, but "
            f"{len(leaked)} stored file(s) could not be deleted and are now unreferenced. "
            "Their rows are gone, so nothing can find them again from the database - these keys "
            "are the only remaining record of them and must be removed by hand:\n  "
            + "\n  ".join(sorted(leaked))
        )

    return counts
