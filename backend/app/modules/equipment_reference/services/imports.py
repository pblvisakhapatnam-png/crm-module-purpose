"""The Plum report import: upload, preview, refresh, confirm, discard (ERT-1 design, section 5).

Nothing changes until the Fleet Admin confirms. An upload reads the file in memory - it is never kept
(Q8) - stores only the used values of each row, and computes a preview. A refresh recomputes the preview
from those rows after the Fleet Admin maps a name, records a rule or corrects a machine. Confirmation
recomputes it once more and applies it in one transaction; it is refused if another report was confirmed
since the preview was made, or if anything the preview was computed from has changed since (the change
count). A second click publishes nothing twice (ADR-023).
"""

from __future__ import annotations

import hashlib
from datetime import date, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from app.modules.equipment_reference import repository as repo
from app.modules.equipment_reference.contract import (
    ASSET_KIND_PART,
    CLOSED_PLUM_AGREES,
    DATA_QUALITY_NOT_IN_LATEST_REPORT,
    DATA_QUALITY_PART_NOT_FITTED,
    DISCARDED_BY_FLEET_ADMIN,
    DISCARDED_SUPERSEDED,
    EQUIPMENT_EVENT_ASSET_CHANGED,
    EQUIPMENT_EVENT_ASSET_REACTIVATED,
    EQUIPMENT_EVENT_ASSET_REGISTERED,
    EQUIPMENT_EVENT_ASSET_RETIRED,
    EQUIPMENT_EVENT_CORRECTION_CLOSED,
    EQUIPMENT_EVENT_IMPORT_PUBLISHED,
    EQUIPMENT_EVENT_PART_FITTED,
    IDENTITY_FIELDS,
    IMPORT_STATUS_DISCARDED,
    IMPORT_STATUS_PREVIEWED,
    IMPORT_STATUS_PUBLISHED,
    PROVIDER_PLUM,
    RECORD_TYPE_ASSET,
    RECORD_TYPE_IMPORT,
    normalize_term,
)
from app.modules.equipment_reference.plum_report import (
    CORRECTION_PLUM_AGREES,
    OUTCOME_CHANGED,
    OUTCOME_NEW,
    OUTCOME_NOT_BROUGHT_IN,
    OUTCOME_REACTIVATED,
    OUTCOME_RETIRED,
    OUTCOME_SET_ASIDE,
    ClosingLink,
    KnownAsset,
    Preview,
    PreviewRow,
    ReportReadError,
    ReportRow,
    ValueRule,
    compute_preview,
    model_key_of,
    read_report,
    row_from_values,
)
from app.modules.equipment_reference.schemas import (
    ImportActionResponse,
    ImportDiscardInput,
    ImportPublishInput,
    ImportRefreshInput,
    ImportResponse,
    ImportSummaryResponse,
)
from app.modules.equipment_reference.service import find_class, find_type, get_equipment_structure
from app.modules.equipment_reference.services.common import (
    EquipmentConflictError,
    EquipmentNotFoundError,
    EquipmentValidationError,
    ModelRecords,
    begin_write,
    bump_versions,
    check_can_fit,
    close_fitted_link,
    corrected_value_label,
    known_assets,
    load_models,
    now,
    record_event,
    require_user,
    transform_context,
    write_derived_facts,
)
from app.shared import business_time
from app.shared.transactions import rollback_on_error

FINGERPRINT_PREFIX_LENGTH = 12

STALE_ANOTHER_CONFIRMED = "Another report was confirmed since this preview was made. Refresh it."
STALE_CONTEXT_CHANGED = (
    "Models, mappings, value rules, corrections or pairs changed since this preview was made. Refresh it."
)
STALE_VERSION = "This preview was refreshed after you opened it. Reload it to see the latest."


def _long_date(value: date) -> str:
    return f"{value.day} {value.strftime('%B %Y')}"


# --- The preview, as stored and shown ---------------------------------------------------------------


def _preview_json(
    preview: Preview,
    *,
    models: ModelRecords,
    structure: Any,
    known: list[tuple[dict[str, Any], KnownAsset]],
    value_rules: tuple[ValueRule, ...],
) -> dict[str, Any]:
    """What the preview screen shows, and what a confirmed import keeps as its record. Only the used
    values of each row (design section 3)."""
    display: dict[str, str] = {}
    references: dict[str, str] = {}
    rules_by_id = {rule.rule_public_id: rule for rule in value_rules}
    for _, asset in known:
        display[asset.normalized_key] = asset.machine_number
        references[asset.normalized_key] = asset.asset_reference
    rows: list[dict[str, Any]] = []
    for row in preview.rows:
        rows.append(_row_json(row, models=models, structure=structure, value_rules=rules_by_id))
        if row.derived.row.machine_number:
            display.setdefault(normalize_term(row.derived.row.machine_number), row.derived.row.machine_number)
    return {
        "counts": preview.counts(),
        "rows": rows,
        "missing": [
            {
                "asset_public_id": asset.asset_public_id,
                "asset_reference": asset.asset_reference,
                "machine_number": asset.machine_number,
            }
            for asset in preview.missing
        ],
        "unmapped_model_names": list(preview.unmapped_model_names),
        "closing_links": [_closing_json(link) for link in preview.closing_links],
        "pair_proposals": [
            {
                "part_machine_number": display.get(proposal.part_key, proposal.part_key),
                "proposed_machine_number": display.get(proposal.proposed_machine_key, proposal.proposed_machine_key)
                if proposal.proposed_machine_key
                else None,
                # A machine the report brings in has no reference until the report is confirmed.
                "candidates": [
                    {"machine_number": display.get(key, key), "asset_reference": references.get(key)}
                    for key in proposal.candidate_machine_keys
                ],
            }
            for proposal in preview.pair_proposals
        ],
    }


def _closing_json(link: ClosingLink) -> dict[str, Any]:
    return {
        "machine_asset_public_id": link.machine_public_id,
        "machine_machine_number": link.machine_number,
        "part_asset_public_id": link.part_public_id,
        "part_machine_number": link.part_number,
        "because": link.because,
    }


def _rule_json(rule: ValueRule) -> dict[str, Any]:
    """A reading of a Plum value, as the preview names it. An engine or chassis number is never repeated:
    the stored preview is kept as the import's record, and those numbers are shown only to whoever may see
    them (EQUIPMENT_IDENTITY_READ)."""
    return {
        "rule_public_id": rule.rule_public_id,
        "column_code": rule.column_code,
        "action_code": rule.action_code,
        "plum_value": None if rule.column_code in IDENTITY_FIELDS else rule.plum_value,
        "result_number": str(rule.result_number) if rule.result_number is not None else None,
        "result_unit_code": rule.result_unit_code,
        "result_class_code": rule.result_class_code,
        "result_type_code": rule.result_type_code,
    }


def _row_json(row: PreviewRow, *, models: ModelRecords, structure: Any, value_rules: dict[str, ValueRule]) -> dict[str, Any]:
    source = row.derived.row
    facts = row.derived.facts
    equipment_class = find_class(structure, facts.class_code) if facts else None
    equipment_type = find_type(equipment_class, facts.type_code) if equipment_class and facts and facts.type_code else None
    model = models.by_public_id.get(facts.model_public_id) if facts and facts.model_public_id else None
    corrected = {item.correction_public_id: item for item in row.known.corrections} if row.known else {}
    corrections = []
    for effect in row.derived.corrections:
        correction = corrected.get(effect.correction_public_id)
        withheld = effect.field_code in IDENTITY_FIELDS
        corrections.append(
            {
                "correction_public_id": effect.correction_public_id,
                "field_code": effect.field_code,
                "effect_code": effect.effect_code,
                "corrected_value_label": None
                if withheld or correction is None
                else corrected_value_label(effect.field_code, correction.corrected_value, structure, models.by_public_id),
            }
        )
    rules = [_rule_json(value_rules[rule_id]) for rule_id in row.derived.rules_applied if rule_id in value_rules]
    closing = [_closing_json(link) for link in row.closing_links]
    # A row read with a correction or a reading is shown by default even with no flag left: Admin confirms
    # knowing where the platform does not take Plum's value as it stands (independent review, round 1,
    # ERT1-R1-006).
    needs_attention = bool(row.flags) or bool(corrections) or bool(rules) or bool(closing) or row.outcome_code in (
        OUTCOME_SET_ASIDE,
        OUTCOME_NEW,
        OUTCOME_CHANGED,
        OUTCOME_RETIRED,
        OUTCOME_REACTIVATED,
    )
    return {
        "row_number": source.row_number,
        "machine_number": source.machine_number,
        "outcome_code": row.outcome_code,
        "reason_code": row.reason_code,
        "asset_public_id": row.known.asset_public_id if row.known else None,
        "asset_reference": row.known.asset_reference if row.known else None,
        "kind_code": facts.kind_code if facts else None,
        "class_code": facts.class_code if facts else None,
        "class_label": equipment_class.class_label if equipment_class else None,
        "type_code": facts.type_code if facts else None,
        "type_label": equipment_type.type_label if equipment_type else None,
        "model_public_id": facts.model_public_id if facts else None,
        "model_label": model.label if model else None,
        "status_code": facts.status_code if facts else None,
        "changed_facts": list(row.changed_facts) if row.outcome_code != OUTCOME_NEW else [],
        "flags": [{"flag_code": flag.flag_code, "subject_code": flag.subject_code} for flag in row.flags],
        "rules_applied": rules,
        "corrections": corrections,
        # Fitted-part links of this asset that confirmation will close (ERT1-R3-001).
        "closing_links": closing,
        "plum": {
            "category": source.category,
            "model_name": model_key_of(source),
            "capacity": source.capacity or source.load_capacity,
            "commenced_year": source.commenced_year,
            "status": source.status_text,
        },
        "needs_attention": needs_attention,
    }


def _compute(db: Session, rows: list[ReportRow], *, report_date: date) -> tuple[dict[str, Any], int | None, int]:
    """The preview of these rows against everything the platform holds now, the confirmed import it is
    compared with, and the change count it was computed at. Called under the write lock, so no change can
    fall between reading the count and reading what it counts."""
    change_number = repo.current_change_number(db)
    latest = repo.latest_published_import(db)
    structure = get_equipment_structure(db)
    models = load_models(db)
    known = known_assets(db, models)
    ctx = transform_context(db, report_year=report_date.year, structure=structure, models=models, known=known)
    preview = compute_preview(rows, ctx)
    record = _preview_json(preview, models=models, structure=structure, known=known, value_rules=ctx.value_rules)
    return record, (int(latest["id"]) if latest else None), change_number


def _stored_rows(db: Session, import_id: int) -> list[ReportRow]:
    return [
        row_from_values(int(values["row_number"]), values, too_long=bool(values["value_too_long"]))
        for values in repo.list_import_row_values(db, import_id=import_id)
    ]


# --- Reading imports -------------------------------------------------------------------------------


def _summary_fields(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "import_public_id": row["import_public_id"],
        "import_status_code": row["import_status_code"],
        "report_date": row["report_date"],
        "row_count": int(row["row_count"]),
        "fingerprint_prefix": str(row["fingerprint"])[:FINGERPRINT_PREFIX_LENGTH],
        "uploaded_by_display_name": row["uploaded_by_display_name"],
        "uploaded_at": row["uploaded_at"],
        "published_by_display_name": row["published_by_display_name"],
        "published_at": row["published_at"],
        "discarded_by_display_name": row["discarded_by_display_name"],
        "discarded_at": row["discarded_at"],
        "discard_reason_code": row["discard_reason_code"],
        "counts": {str(key): int(value) for key, value in (row["counts"] or {}).items()},
    }


def list_imports(db: Session, *, limit: int = 20, offset: int = 0) -> list[ImportSummaryResponse]:
    return [ImportSummaryResponse(**_summary_fields(row)) for row in repo.list_import_summary_rows(db, limit=limit, offset=offset)]


def _staleness(db: Session, row: dict[str, Any]) -> str | None:
    """Why a preview can no longer be confirmed as it stands, or None when it can."""
    if row["import_status_code"] != IMPORT_STATUS_PREVIEWED:
        return None
    latest = repo.latest_published_import(db)
    latest_id = int(latest["id"]) if latest else None
    based_on = int(row["based_on_import_id"]) if row["based_on_import_id"] is not None else None
    if latest_id != based_on:
        return STALE_ANOTHER_CONFIRMED
    if repo.current_change_number(db) != int(row["preview_change_number"]):
        return STALE_CONTEXT_CHANGED
    return None


def get_import(db: Session, public_id: UUID | str) -> ImportResponse:
    row = repo.get_import_row(db, public_id=str(public_id))
    if row is None:
        raise EquipmentNotFoundError("Import not found.")
    stale = _staleness(db, row)
    return ImportResponse(
        **_summary_fields(row),
        preview_version=int(row["preview_version"]),
        preview_computed_at=row["preview_computed_at"],
        is_current=row["import_status_code"] == IMPORT_STATUS_PREVIEWED and stale is None,
        stale_reason=stale,
        based_on_import_public_id=row["based_on_import_public_id"],
        preview=repo.get_import_preview(db, import_id=int(row["id"])) or {},
    )


# --- Upload, refresh, discard ------------------------------------------------------------------------


def upload_report(db: Session, *, content: bytes, report_date: date, user_public_id: str | None) -> ImportActionResponse:
    """Read the report and compute its preview. The file is read in memory and discarded; its fingerprint,
    row count and the date given are kept. The same report again is refused once it has been confirmed,
    and returns the waiting preview while it has not."""
    actor = require_user(user_public_id)
    if report_date > business_time.india_today():
        raise EquipmentValidationError("The report's date cannot be in the future.")
    fingerprint = hashlib.sha256(content).hexdigest()
    try:
        rows = read_report(content)
    except ReportReadError as exc:
        raise EquipmentValidationError(str(exc)) from exc
    with rollback_on_error(db):
        begin_write(db)
        # Any confirmed import of the same file, not only the latest: confirming it again after a newer
        # report would bring older facts back (independent review, round 1, ERT1-R1-002).
        confirmed = repo.find_published_import_by_fingerprint(db, fingerprint=fingerprint)
        if confirmed is not None:
            confirmed_on = business_time.india_date(confirmed["published_at"])
            raise EquipmentConflictError(f"This report was already imported on {_long_date(confirmed_on)}.")
        waiting = repo.find_previewed_import_by_fingerprint(db, fingerprint=fingerprint)
        if waiting is not None:
            db.rollback()
            return ImportActionResponse(equipment_import=get_import(db, waiting["import_public_id"]), replayed=True)
        preview, based_on_id, change_number = _compute(db, rows, report_date=report_date)
        public_id = str(uuid4())
        import_id = repo.insert_import(
            db,
            values={
                "import_public_id": public_id,
                "provider_code": PROVIDER_PLUM,
                "fingerprint": fingerprint,
                "row_count": len(rows),
                "report_date": report_date,
                "import_status_code": IMPORT_STATUS_PREVIEWED,
                "based_on_import_id": based_on_id,
                "preview": preview,
                "preview_version": 1,
                "preview_change_number": change_number,
                "preview_computed_at": now(),
                "uploaded_by": actor,
            },
        )
        repo.insert_import_row_values(
            db,
            import_id=import_id,
            rows=[{"row_number": row.row_number, "value_too_long": row.too_long, **row.values()} for row in rows],
        )
        db.commit()
    return ImportActionResponse(equipment_import=get_import(db, public_id))


def _locked_preview(db: Session, public_id: UUID, expected_version: int, *, action: str) -> dict[str, Any]:
    locked = repo.lock_import_row(db, public_id=str(public_id))
    if locked is None:
        raise EquipmentNotFoundError("Import not found.")
    if locked["import_status_code"] == IMPORT_STATUS_PUBLISHED:
        raise EquipmentValidationError(f"This report has been confirmed, so it can no longer be {action}.")
    if locked["import_status_code"] == IMPORT_STATUS_DISCARDED:
        raise EquipmentValidationError(f"This preview was discarded, so it can no longer be {action}. Upload the report again.")
    if int(locked["preview_version"]) != expected_version:
        raise EquipmentConflictError(STALE_VERSION)
    return locked


def refresh_import(db: Session, *, public_id: UUID, payload: ImportRefreshInput) -> ImportActionResponse:
    """Recompute the preview from the rows already read, against everything as it stands now."""
    with rollback_on_error(db):
        begin_write(db)
        locked = _locked_preview(db, public_id, payload.expected_preview_version, action="refreshed")
        preview, based_on_id, change_number = _compute(db, _stored_rows(db, int(locked["id"])), report_date=locked["report_date"])
        repo.store_preview(
            db, import_id=int(locked["id"]), preview=preview, change_number=change_number, based_on_import_id=based_on_id, at=now()
        )
        db.commit()
    return ImportActionResponse(equipment_import=get_import(db, public_id))


def discard_import(
    db: Session, *, public_id: UUID, payload: ImportDiscardInput, user_public_id: str | None
) -> ImportActionResponse:
    """Discard a preview. Nothing it would have done is done; its rows stay with it as the record."""
    actor = require_user(user_public_id)
    with rollback_on_error(db):
        begin_write(db)
        locked = repo.lock_import_row(db, public_id=str(public_id))
        if locked is None:
            raise EquipmentNotFoundError("Import not found.")
        if locked["import_status_code"] == IMPORT_STATUS_DISCARDED:
            db.rollback()
            return ImportActionResponse(equipment_import=get_import(db, public_id))
        _locked_preview(db, public_id, payload.expected_preview_version, action="discarded")
        repo.discard_imports(db, import_ids=[int(locked["id"])], reason_code=DISCARDED_BY_FLEET_ADMIN, user_public_id=actor, at=now())
        db.commit()
    return ImportActionResponse(equipment_import=get_import(db, public_id))


# --- Confirmation ----------------------------------------------------------------------------------------


def publish_import(
    db: Session, *, public_id: UUID, payload: ImportPublishInput, user_public_id: str | None
) -> ImportActionResponse:
    actor = require_user(user_public_id)
    with rollback_on_error(db):
        begin_write(db)
        locked = repo.lock_import_row(db, public_id=str(public_id))
        if locked is None:
            raise EquipmentNotFoundError("Import not found.")
        if locked["import_status_code"] == IMPORT_STATUS_PUBLISHED:
            # A second click, or a retry: the first confirmation stands and nothing is done twice.
            db.rollback()
            return ImportActionResponse(equipment_import=get_import(db, public_id), replayed=True)
        _locked_preview(db, public_id, payload.expected_preview_version, action="confirmed")
        row = repo.get_import_row(db, public_id=str(public_id))
        assert row is not None
        stale = _staleness(db, row)
        if stale is not None:
            raise EquipmentConflictError(stale)
        event = _apply(db, import_id=int(locked["id"]), import_public_id=str(public_id), locked=locked, payload=payload, actor=actor)
        db.commit()
    return ImportActionResponse(equipment_import=get_import(db, public_id), event=event)


def _apply(
    db: Session,
    *,
    import_id: int,
    import_public_id: str,
    locked: dict[str, Any],
    payload: ImportPublishInput,
    actor: str,
) -> dict[str, Any]:
    report_date: date = locked["report_date"]
    at = now()
    structure = get_equipment_structure(db)
    models = load_models(db)
    known = known_assets(db, models)
    asset_rows = {str(row["asset_public_id"]): row for row, _ in known}
    ctx = transform_context(db, report_year=report_date.year, structure=structure, models=models, known=known)
    preview = compute_preview(_stored_rows(db, import_id), ctx)

    asset_ids_by_key: dict[str, int] = {asset.normalized_key: int(asset_rows[asset.asset_public_id]["id"]) for _, asset in known}
    in_report: list[int] = []
    # Every asset the platform already held that this confirmation changes in any way - facts, flags,
    # corrections, links, what its latest report says of it - has its version moved on exactly once, at the
    # end, so a draft made against the version before is refused (independent review, round 1,
    # ERT1-R1-004). A machine brought in now starts at version 1 and is not moved.
    changed: set[int] = set()
    new_ids: set[int] = set()
    closed_corrections = 0
    # The links the preview showed closing are closed first, and only those, so what is confirmed is what
    # was shown; each row's facts are then written without closing any other (ERT1-R3-001).
    ids_by_public_id = {asset.asset_public_id: int(asset_rows[asset.asset_public_id]["id"]) for _, asset in known}
    for closing in preview.closing_links:
        machine_id, part_id = ids_by_public_id[closing.machine_public_id], ids_by_public_id[closing.part_public_id]
        for link in repo.list_open_links_of(db, asset_id=part_id):
            if int(link["parent_asset_id"]) == machine_id and int(link["child_asset_id"]) == part_id:
                close_fitted_link(db, link=link, removal_date=report_date, because=closing.because, user_public_id=actor, at=at)
                changed.update({machine_id, part_id})
    for preview_row in preview.rows:
        if preview_row.outcome_code in (OUTCOME_SET_ASIDE, OUTCOME_NOT_BROUGHT_IN):
            continue
        key = normalize_term(preview_row.derived.row.machine_number)
        if preview_row.outcome_code == OUTCOME_NEW:
            asset_ids_by_key[key] = _register(db, preview_row, import_id=import_id, import_public_id=import_public_id, report_date=report_date, models=models, actor=actor, at=at)
            new_ids.add(asset_ids_by_key[key])
        else:
            assert preview_row.known is not None
            closed, touched = _update_known(
                db,
                preview_row,
                preview_row.known,
                asset_id=asset_ids_by_key[key],
                import_id=import_id,
                import_public_id=import_public_id,
                report_date=report_date,
                models=models,
                actor=actor,
                at=at,
            )
            closed_corrections += closed
            changed.update(touched)
        in_report.append(asset_ids_by_key[key])

    for asset, flag in preview.set_aside_known:
        asset_id = asset_ids_by_key[asset.normalized_key]
        removed = repo.delete_asset_flag(db, asset_id=asset_id, flag_code=DATA_QUALITY_NOT_IN_LATEST_REPORT)
        raised = repo.insert_asset_flag(db, asset_id=asset_id, flag_code=flag.flag_code, subject_code=flag.subject_code, import_id=import_id, at=at)
        rebound = repo.update_binding(db, asset_id=asset_id, reconciliation_status_code="AMBIGUOUS")
        if removed or raised or rebound:
            changed.add(asset_id)
    for asset in preview.missing:
        asset_id = asset_ids_by_key[asset.normalized_key]
        raised = repo.insert_asset_flag(db, asset_id=asset_id, flag_code=DATA_QUALITY_NOT_IN_LATEST_REPORT, subject_code="", import_id=import_id, at=at)
        rebound = repo.update_binding(db, asset_id=asset_id, reconciliation_status_code="UNMATCHED")
        if raised or rebound:
            changed.add(asset_id)
    # How fresh the Plum facts are is not a change of facts: it moves no version by itself.
    repo.set_facts_report_date(db, asset_ids=in_report, report_date=report_date)

    fitted, paired = _fit_pairs(db, payload, preview, asset_ids_by_key, structure=structure, report_date=report_date, actor=actor, at=at)
    changed.update(paired)
    unfitted = repo.list_unfitted_part_ids(db)
    for asset_id in unfitted:
        if repo.insert_asset_flag(db, asset_id=asset_id, flag_code=DATA_QUALITY_PART_NOT_FITTED, subject_code="", import_id=import_id, at=at):
            changed.add(asset_id)
    changed.update(repo.delete_part_not_fitted_flags_except(db, asset_ids=unfitted))
    bump_versions(db, changed - new_ids, user_public_id=actor, at=at)

    record = _preview_json(preview, models=models, structure=structure, known=known, value_rules=ctx.value_rules)
    if repo.mark_import_published(db, import_id=import_id, preview=record, user_public_id=actor, at=at) != 1:
        raise EquipmentConflictError(STALE_VERSION)
    repo.discard_imports(
        db,
        import_ids=repo.list_previewed_import_ids(db, except_id=import_id),
        reason_code=DISCARDED_SUPERSEDED,
        user_public_id=actor,
        at=at,
    )
    repo.bump_change_number(db)
    return record_event(
        db,
        event_name=EQUIPMENT_EVENT_IMPORT_PUBLISHED,
        record_type=RECORD_TYPE_IMPORT,
        record_public_id=import_public_id,
        user_public_id=actor,
        payload={
            "provider_code": PROVIDER_PLUM,
            "report_date": report_date.isoformat(),
            "fingerprint_prefix": str(locked["fingerprint"])[:FINGERPRINT_PREFIX_LENGTH],
            "row_count": int(locked["row_count"]),
            "counts": preview.counts(),
            "parts_fitted": fitted,
            "corrections_closed": closed_corrections,
        },
        reason="Plum vehicle report confirmed.",
        status_before=IMPORT_STATUS_PREVIEWED,
        status_after=IMPORT_STATUS_PUBLISHED,
    )


def _asset_event(
    db: Session,
    *,
    event_name: str,
    asset_public_id: str,
    payload: dict[str, Any],
    actor: str,
    reason: str,
    status_before: str | None,
    status_after: str,
) -> None:
    record_event(
        db,
        event_name=event_name,
        record_type=RECORD_TYPE_ASSET,
        record_public_id=asset_public_id,
        user_public_id=actor,
        payload=payload,
        reason=reason,
        status_before=status_before,
        status_after=status_after,
    )


def _register(
    db: Session,
    preview_row: PreviewRow,
    *,
    import_id: int,
    import_public_id: str,
    report_date: date,
    models: ModelRecords,
    actor: str,
    at: datetime,
) -> int:
    facts = preview_row.derived.facts
    assert facts is not None
    source = preview_row.derived.row
    public_id = str(uuid4())
    asset_id = repo.insert_asset(
        db,
        values={
            "asset_public_id": public_id,
            "asset_kind_code": facts.kind_code,
            "class_code": facts.class_code,
            "type_code": facts.type_code,
            "equipment_model_id": models.id_by_public_id.get(facts.model_public_id) if facts.model_public_id else None,
            "machine_number": source.machine_number,
            "engine_number": facts.engine_number,
            "chassis_number": facts.chassis_number,
            "commenced_year": facts.commenced_year,
            "owning_company": facts.owning_company,
            "asset_status_code": facts.status_code,
            "facts_report_date": report_date,
            "registered_by_import_id": import_id,
            "created_by": actor,
            "updated_by": actor,
        },
    )
    repo.insert_binding(db, asset_id=asset_id, provider_key=source.machine_number or "", source_values=source.values(), import_id=import_id)
    for flag in preview_row.flags:
        repo.insert_asset_flag(db, asset_id=asset_id, flag_code=flag.flag_code, subject_code=flag.subject_code, import_id=import_id, at=at)
    _asset_event(
        db,
        event_name=EQUIPMENT_EVENT_ASSET_REGISTERED,
        asset_public_id=public_id,
        payload={
            "import_public_id": import_public_id,
            "report_date": report_date.isoformat(),
            "asset_kind_code": facts.kind_code,
            "class_code": facts.class_code,
            "type_code": facts.type_code,
            "model_public_id": facts.model_public_id,
            "asset_version": 1,
            "flag_codes": sorted({flag.flag_code for flag in preview_row.flags}),
        },
        actor=actor,
        reason="Machine brought in from Plum's report.",
        status_before=None,
        status_after=facts.status_code,
    )
    return asset_id


def _update_known(
    db: Session,
    preview_row: PreviewRow,
    known: KnownAsset,
    *,
    asset_id: int,
    import_id: int,
    import_public_id: str,
    report_date: date,
    models: ModelRecords,
    actor: str,
    at: datetime,
) -> tuple[int, set[int]]:
    """Apply a report row to a machine the platform already holds. Returns the corrections it closed, and
    the assets it changed: this one, whenever anything about it changed, and the other end of any link a
    change of kind closed."""
    facts = preview_row.derived.facts
    assert facts is not None
    written = write_derived_facts(
        db,
        asset_id=asset_id,
        current=known,
        facts=facts,
        models=models,
        user_public_id=actor,
        at=at,
        removal_date=report_date,
        reconcile_links=False,
    )
    rebound = repo.update_binding(
        db, asset_id=asset_id, reconciliation_status_code="CONFIRMED", source_values=preview_row.derived.row.values(), import_id=import_id
    )
    reflagged = repo.set_asset_flags(
        db,
        asset_id=asset_id,
        flags={(flag.flag_code, flag.subject_code) for flag in preview_row.flags},
        # Recomputed for every part once the report's pairs are fitted.
        keep_codes=frozenset({DATA_QUALITY_PART_NOT_FITTED}),
        import_id=import_id,
        at=at,
    )
    closed = 0
    for effect in preview_row.derived.corrections:
        if effect.effect_code != CORRECTION_PLUM_AGREES:
            continue
        correction = repo.get_correction_row(db, asset_id=asset_id, public_id=effect.correction_public_id)
        if correction is None or repo.close_correction(
            db, correction_id=int(correction["id"]), reason_code=CLOSED_PLUM_AGREES, user_public_id=None, import_id=import_id, at=at
        ) != 1:
            continue
        closed += 1
        _asset_event(
            db,
            event_name=EQUIPMENT_EVENT_CORRECTION_CLOSED,
            asset_public_id=known.asset_public_id,
            payload={
                "correction_public_id": effect.correction_public_id,
                "field_code": effect.field_code,
                "closed_reason_code": CLOSED_PLUM_AGREES,
                "import_public_id": import_public_id,
            },
            actor=actor,
            reason="Correction closed: Plum now agrees.",
            status_before=known.status_code,
            status_after=facts.status_code,
        )
    if written.changed_facts:
        event_name = {
            OUTCOME_RETIRED: EQUIPMENT_EVENT_ASSET_RETIRED,
            OUTCOME_REACTIVATED: EQUIPMENT_EVENT_ASSET_REACTIVATED,
        }.get(preview_row.outcome_code, EQUIPMENT_EVENT_ASSET_CHANGED)
        _asset_event(
            db,
            event_name=event_name,
            asset_public_id=known.asset_public_id,
            payload={
                "import_public_id": import_public_id,
                "report_date": report_date.isoformat(),
                "changed_facts": list(written.changed_facts),
                "asset_kind_code": facts.kind_code,
                "class_code": facts.class_code,
                "type_code": facts.type_code,
                "model_public_id": facts.model_public_id,
                "removed_capability_codes": list(written.removed_capability_codes),
                "closed_link_public_ids": list(written.closed_link_public_ids),
            },
            actor=actor,
            reason={
                EQUIPMENT_EVENT_ASSET_RETIRED: "Machine retired: Plum marks it inactive.",
                EQUIPMENT_EVENT_ASSET_REACTIVATED: "Machine reactivated: Plum marks it active again.",
            }.get(event_name, "Machine's facts changed in Plum's report."),
            status_before=known.status_code,
            status_after=facts.status_code,
        )
    touched = set(written.other_linked_asset_ids)
    if written.changed_facts or rebound or reflagged or closed:
        touched.add(asset_id)
    return closed, touched


def _fit_pairs(
    db: Session,
    payload: ImportPublishInput,
    preview: Preview,
    asset_ids_by_key: dict[str, int],
    *,
    structure: Any,
    report_date: date,
    actor: str,
    at: datetime,
) -> tuple[int, set[int]]:
    """Fit each pair the Fleet Admin confirmed, dated the report's date. A pair names a part in this report
    and a machine the platform holds or this report brings in; the rules are the machine page's. Returns
    how many were fitted and the assets they changed."""
    paired: set[int] = set()
    parts_in_report = {
        normalize_term(row.derived.row.machine_number)
        for row in preview.rows_to_take_in()
        if row.derived.facts is not None and row.derived.facts.kind_code == ASSET_KIND_PART
    }
    seen: set[str] = set()
    for pair in payload.pairs:
        part_key, machine_key = normalize_term(pair.part_machine_number), normalize_term(pair.machine_machine_number)
        if part_key in seen:
            raise EquipmentValidationError(f"{pair.part_machine_number} is paired twice. Pair each part once.")
        seen.add(part_key)
        if part_key not in parts_in_report:
            raise EquipmentValidationError(f"{pair.part_machine_number} is not a part this report brings in or updates.")
        machine_id = asset_ids_by_key.get(machine_key)
        if machine_id is None:
            raise EquipmentValidationError(f"{pair.machine_machine_number} is not a machine the platform holds or this report brings in.")
        machine_row = repo.get_asset_row_by_id(db, asset_id=machine_id)
        part_row = repo.get_asset_row_by_id(db, asset_id=asset_ids_by_key[part_key])
        try:
            check_can_fit(db, machine_row, part_row, structure)
        except EquipmentValidationError as exc:
            raise EquipmentValidationError(f"{pair.part_machine_number} and {pair.machine_machine_number}: {exc}") from exc
        # Dated the report's date, but never before the part's last removal - which may be this very
        # confirmation's, clamped to the day the part was fitted - so no two links overlap (ERT1-R4-004).
        earliest = repo.earliest_fitting_date(db, part_id=int(part_row["id"]), machine_id=machine_id, part_class_code=part_row["class_code"])
        fitted_on = max(report_date, earliest) if earliest is not None else report_date
        link_public_id = str(uuid4())
        repo.insert_link(
            db,
            public_id=link_public_id,
            parent_asset_id=machine_id,
            child_asset_id=int(part_row["id"]),
            fitted_on=fitted_on,
            user_public_id=actor,
            at=at,
        )
        paired.update({machine_id, int(part_row["id"])})
        _asset_event(
            db,
            event_name=EQUIPMENT_EVENT_PART_FITTED,
            asset_public_id=str(machine_row["asset_public_id"]),
            payload={
                "link_public_id": link_public_id,
                "part_asset_public_id": str(part_row["asset_public_id"]),
                "part_class_code": part_row["class_code"],
                "fitted_on": fitted_on.isoformat(),
            },
            actor=actor,
            reason="Part fitted to its machine when Plum's report was confirmed.",
            status_before=None,
            status_after=machine_row["asset_status_code"],
        )
    return len(seen), paired
