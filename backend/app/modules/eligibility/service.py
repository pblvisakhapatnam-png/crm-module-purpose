"""Eligibility: machines' certificates, "not applicable" marks, the rules, and the decision (ELG-1, ELA-001).

Design: docs/agent/slices/elg-1-machine-eligibility.md; the API is docs/agent/contracts/eligibility-api-contract.md.

- The Equipment Reference is read only through its service: an asset with its fitted parts, and every active
  asset. Its tables are never read or written here, and it never reads this module.
- Certificates and marks are never edited: a mistake is withdrawn and recorded again. Rules are never edited
  either: one is ended on a date and another added. So every decision can be explained by the evidence and
  rule versions it names.
- The decision itself is `evaluation.py`'s, pure. This module reads the records, the day in Asia/Kolkata and
  whether each certificate has its copy, and hands them in.
- Copies are Slice 9C documents linked to a certificate. Whether one is attached is shown to everyone who sees
  the certificate; the copy and the certificate's number only to EQUIPMENT_IDENTITY_READ (Q6).
- For 8A: `evaluate_asset` is the check, and `record_decision` stores it in the caller's transaction.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.authorization.contract import EQUIPMENT_IDENTITY_READ
from app.modules.authorization.service import has_permission
from app.modules.documents.contract import STORAGE_MODE_LOCAL_UPLOAD
from app.modules.documents.service import AttachRequest, linked_record_ids_with_documents, register_attach_check
from app.modules.eligibility import evaluation
from app.modules.eligibility import repository as repo
from app.modules.eligibility.contract import (
    APPLIES_ALWAYS,
    APPLIES_WHEN_CODES,
    BAND_CODES,
    BASIS_CODES,
    BASIS_STATUTORY,
    CERTIFICATE_STATUS_WITHDRAWN,
    COPY_DOCUMENT_TYPE,
    ELIGIBILITY_MODULE_NAME,
    EVENT_CERTIFICATE_RECORDED,
    EVENT_CERTIFICATE_WITHDRAWN,
    EVENT_EVALUATED,
    EVENT_NOT_APPLICABLE_RECORDED,
    EVENT_NOT_APPLICABLE_WITHDRAWN,
    EVENT_RULE_ENDED,
    EVENT_RULE_RECORDED,
    JURISDICTION_CENTRAL,
    JURISDICTION_KIND_CENTRAL,
    KIND_REGISTRATION,
    LAPSE_CODES,
    LAPSE_NOT_REQUIRED,
    MARK_STATUS_WITHDRAWN,
    NOT_APPLICABLE_ALLOWED,
    NOT_APPLICABLE_CODES,
    RECORD_TYPE_CERTIFICATE,
    RECORD_TYPE_DECISION,
    RECORD_TYPE_NOT_APPLICABLE,
    RECORD_TYPE_RULE,
    REGISTERED_AS_CODES,
    STATUTORY_LAPSE_CODES,
)
from app.modules.eligibility.schemas import (
    AssetCertificatesResponse,
    AssetSummary,
    CertificateActionResponse,
    CertificateInput,
    CertificateKindResponse,
    CertificateResponse,
    CertificatesDueResponse,
    CheckResult,
    DueItem,
    EligibilityCheckResponse,
    JurisdictionResponse,
    KindStatus,
    MarkableKind,
    MarkResponse,
    NotApplicableInput,
    RuleActionResponse,
    RuleEndInput,
    RuleInput,
    RuleResponse,
    RuleSummary,
    StoredDecision,
    StoredResult,
    WithdrawInput,
)
from app.modules.equipment_reference.contract import ASSET_KIND_PART, ASSET_STATUS_ACTIVE, ORIGIN_PLATFORM
from app.modules.equipment_reference.service import (
    AssetFacts,
    AssetWithFittedParts,
    asset_references,
    find_class,
    find_type,
    get_asset_with_fitted_parts,
    get_equipment_structure,
    list_active_assets_with_fitted_parts,
)
from app.modules.events.service import record_business_event
from app.modules.identity.schemas import AuthUser
from app.shared import business_time
from app.shared.transactions import rollback_on_error

MAX_DUE_LIMIT = 500


class EligibilityNotFoundError(LookupError):
    pass


class EligibilityValidationError(ValueError):
    pass


class EligibilityConflictError(ValueError):
    """Someone changed the record since it was read, or a request key was used for something else."""


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = " ".join(value.split())
    return cleaned or None


def _required_text(value: str | None, *, what: str) -> str:
    cleaned = _clean(value)
    if cleaned is None:
        raise EligibilityValidationError(f"Give {what}.")
    return cleaned


def _require_request_key(value: str) -> None:
    """A form's request key of only spaces cannot be stored - the database refuses a blank key - so it is refused
    here, before anything is looked up or written (independent review, round 6, ELG1-R6-002)."""
    if not value.strip():
        raise EligibilityValidationError("The form sent a blank request key, so nothing was recorded. Reload the page and try again.")


def _require_user(user_public_id: str | None) -> str:
    if not user_public_id:
        raise EligibilityValidationError("The signed-in user could not be identified, so nothing was recorded.")
    return user_public_id


def _date(value: date | None) -> str | None:
    return value.isoformat() if value is not None else None


def _long_date(value: date) -> str:
    return f"{value.day} {value.strftime('%B %Y')}"


def can_see_numbers(db: Session, user: AuthUser) -> bool:
    """Whether the signed-in user may see certificate numbers and copies: EQUIPMENT_IDENTITY_READ, Admin only for
    now (owner, 27 September 2026, Q6). Resolved here, as the Equipment Reference resolves its own, so routes
    never read roles."""
    return has_permission(db, user.role_codes, EQUIPMENT_IDENTITY_READ)


def _event(
    db: Session,
    *,
    event_name: str,
    record_type: str,
    record_public_id: str,
    user_public_id: str | None,
    payload: dict[str, Any],
    reason: str,
    status_before: str | None = None,
    status_after: str | None = None,
) -> dict[str, Any]:
    """Payloads carry public ids, references, codes, versions, counts and dates only: never a certificate or
    machine number, an issuer's name, a source text or a reason's text (design section 11)."""
    event = record_business_event(
        db,
        event_name=event_name,
        source_module=ELIGIBILITY_MODULE_NAME,
        record_type=record_type,
        record_public_id=record_public_id,
        user_public_id=user_public_id,
        status_before=status_before,
        status_after=status_after,
        reason=reason,
        event_payload=payload,
    )
    return event.model_dump(mode="json")


# --- Reference data ---------------------------------------------------------------------------------------


def list_jurisdictions(db: Session) -> list[JurisdictionResponse]:
    return [JurisdictionResponse(**{key: row[key] for key in JurisdictionResponse.model_fields}) for row in repo.list_jurisdiction_rows(db)]


def list_certificate_kinds(db: Session) -> list[CertificateKindResponse]:
    return [CertificateKindResponse(**{key: row[key] for key in CertificateKindResponse.model_fields}) for row in repo.list_kind_rows(db)]


def _kinds(db: Session) -> dict[str, evaluation.Kind]:
    return {row["kind_code"]: evaluation.Kind(**row) for row in repo.list_kind_rows(db)}


def _jurisdictions(db: Session) -> dict[str, dict[str, Any]]:
    return {row["jurisdiction_code"]: row for row in repo.list_jurisdiction_rows(db)}


def _state_key(value: str | None) -> str:
    """A state as written, compared ignoring case, spaces and punctuation, with "&" read as "and"."""
    text = (value or "").upper().replace("&", " AND ")
    return " ".join("".join(character if character.isalnum() else " " for character in text).split())


def jurisdiction_for_state_text(db: Session, text: str | None) -> JurisdictionResponse | None:
    """The state or union territory an address's free-text state names - by its name ("Gujarat") or its code
    ("GJ", "IN-GJ"), ignoring case, spaces and punctuation - or None when it names none, so that the caller asks
    for the address to be corrected rather than guess (8A core, section 6.1). The central government's sites are
    never a state."""
    key = _state_key(text)
    if not key:
        return None
    for row in repo.list_jurisdiction_rows(db):
        if row["jurisdiction_kind_code"] == JURISDICTION_KIND_CENTRAL:
            continue
        code = row["jurisdiction_code"]
        if key in (_state_key(row["jurisdiction_label"]), _state_key(code), _state_key(code.split("-", 1)[-1])):
            return JurisdictionResponse(**{name: row[name] for name in JurisdictionResponse.model_fields})
    return None


def get_stored_decisions(db: Session, public_ids: list[str]) -> dict[str, StoredDecision]:
    """Stored decisions by public id, each with its results, for the allocations that asked for them (8A core).
    Read-only: a stored decision is never edited."""
    wanted = sorted({public_id for public_id in public_ids if public_id})
    if not wanted:
        return {}
    rows = repo.list_decision_rows(db, public_ids=wanted)
    results: dict[int, list[dict[str, Any]]] = {}
    for row in repo.list_result_rows_of_decisions(db, decision_ids=[int(row["id"]) for row in rows]):
        results.setdefault(int(row["decision_id"]), []).append(row)
    kinds = _kinds(db)
    jurisdictions = _jurisdictions(db)
    references = asset_references(
        db, [item["equipment_asset_public_id"] for items in results.values() for item in items]
        + [row["equipment_asset_public_id"] for row in rows]
    )
    return {
        row["decision_public_id"]: StoredDecision(
            decision_public_id=row["decision_public_id"],
            asset_public_id=row["equipment_asset_public_id"],
            site_state_code=row["site_state_code"],
            site_state_label=jurisdictions[row["site_state_code"]]["jurisdiction_label"],
            central_government_site=bool(row["central_government_site"]),
            period_from=row["period_from"],
            period_to=row["period_to"],
            evaluated_on=row["evaluated_on"],
            evaluated_at=row["evaluated_at"],
            overall_code=row["overall_code"],
            valid_until=row["valid_until"],
            results=[
                StoredResult(
                    asset_public_id=item["equipment_asset_public_id"],
                    asset_reference=references.get(item["equipment_asset_public_id"], ""),
                    kind_code=item["kind_code"],
                    kind_label=kinds[item["kind_code"]].kind_label if item["kind_code"] else None,
                    outcome_code=item["outcome_code"],
                    effect_code=item["effect_code"],
                    cover_ends_on=item["cover_ends_on"],
                )
                for item in results.get(int(row["id"]), [])
            ],
        )
        for row in rows
    }


def _rule(row: dict[str, Any]) -> evaluation.Rule:
    return evaluation.Rule(
        rule_id=row["id"],
        rule_public_id=row["rule_public_id"],
        kind_code=row["kind_code"],
        class_code=row["class_code"],
        type_code=row["type_code"],
        applies_when_code=row["applies_when_code"],
        jurisdiction_code=row["jurisdiction_code"],
        effective_from=row["effective_from"],
        effective_to=row["effective_to"],
        renew_every_months=row["renew_every_months"],
        basis_code=row["basis_code"],
        lapse_code=row["lapse_code"],
        not_applicable_code=row["not_applicable_code"],
        not_applicable_max_months=row["not_applicable_max_months"],
    )


def _rule_summary(rule: evaluation.Rule, rows_by_id: dict[int, dict[str, Any]]) -> RuleSummary:
    row = rows_by_id[rule.rule_id]
    return RuleSummary(
        rule_public_id=rule.rule_public_id,
        jurisdiction_code=rule.jurisdiction_code,
        basis_code=rule.basis_code,
        lapse_code=rule.lapse_code,
        renew_every_months=rule.renew_every_months,
        not_applicable_code=rule.not_applicable_code,
        not_applicable_max_months=rule.not_applicable_max_months,
        source=row["source"],
        note=row["note"],
    )


# --- Loading what a decision reads --------------------------------------------------------------------------


@dataclass(frozen=True)
class _Loaded:
    evidence: evaluation.Evidence
    rule_rows: dict[int, dict[str, Any]]
    certificate_rows: dict[int, dict[str, Any]]
    mark_rows: dict[int, dict[str, Any]]


def _load(db: Session, asset_public_ids: list[str] | None) -> _Loaded:
    """The kinds, every rule, and the certificates and marks of these assets (None: of every asset), each
    certificate with whether its copy is attached."""
    rule_rows = repo.list_rule_rows(db)
    certificate_rows = repo.list_certificate_rows(db, asset_public_ids=asset_public_ids)
    mark_rows = repo.list_mark_rows(db, asset_public_ids=asset_public_ids)
    # Only an uploaded CERTIFICATE document is a copy (Q5): not a file of another type, and not a link to one
    # kept elsewhere.
    with_copy = linked_record_ids_with_documents(
        db,
        linked_record_type=RECORD_TYPE_CERTIFICATE,
        linked_record_public_ids=[row["certificate_public_id"] for row in certificate_rows],
        document_type=COPY_DOCUMENT_TYPE,
        storage_mode=STORAGE_MODE_LOCAL_UPLOAD,
    )
    evidence = evaluation.Evidence(
        kinds=_kinds(db),
        rules=tuple(_rule(row) for row in rule_rows),
        certificates=tuple(
            evaluation.Certificate(
                certificate_id=row["id"],
                certificate_public_id=row["certificate_public_id"],
                asset_public_id=row["equipment_asset_public_id"],
                kind_code=row["kind_code"],
                issued_on=row["issued_on"],
                valid_from=row["valid_from"],
                valid_until=row["valid_until"],
                valid_in_code=row["valid_in_code"],
                registered_as_code=row["registered_as_code"],
                withdrawn=row["certificate_status_code"] == CERTIFICATE_STATUS_WITHDRAWN,
                has_copy=row["certificate_public_id"] in with_copy,
            )
            for row in certificate_rows
        ),
        marks=tuple(
            evaluation.Mark(
                mark_id=row["id"],
                mark_public_id=row["mark_public_id"],
                asset_public_id=row["equipment_asset_public_id"],
                kind_code=row["kind_code"],
                until_date=row["until_date"],
                recorded_on=row["recorded_on"],
                withdrawn=row["mark_status_code"] == MARK_STATUS_WITHDRAWN,
                withdrawn_on=business_time.india_date(row["withdrawn_at"]) if row["withdrawn_at"] else None,
            )
            for row in mark_rows
        ),
    )
    return _Loaded(
        evidence,
        {row["id"]: row for row in rule_rows},
        {row["id"]: {**row, "has_copy": row["certificate_public_id"] in with_copy} for row in certificate_rows},
        {row["id"]: row for row in mark_rows},
    )


def _eval_asset(facts: AssetFacts) -> evaluation.Asset:
    return evaluation.Asset(facts.asset_public_id, facts.class_code, facts.type_code, facts.asset_status_code == ASSET_STATUS_ACTIVE)


def _members(unit: AssetWithFittedParts) -> tuple[evaluation.Member, ...]:
    """The asset and every active part fitted below it, each with the assets whose certificates meet its rules:
    itself and the active parts fitted below it. A retired part's certificates never count for its machine."""
    children: dict[str, list[AssetFacts]] = {}
    for part, parent_public_id in unit.fitted_parts:
        if part.asset_status_code == ASSET_STATUS_ACTIVE:
            children.setdefault(parent_public_id, []).append(part)

    def subtree(public_id: str) -> tuple[str, ...]:
        below = [public_id]
        for child in children.get(public_id, []):
            below.extend(subtree(child.asset_public_id))
        return tuple(below)

    ordered = [unit.asset]
    frontier = [unit.asset]
    while frontier:
        frontier = [child for item in frontier for child in children.get(item.asset_public_id, [])]
        ordered.extend(frontier)
    return tuple(evaluation.Member(_eval_asset(item), subtree(item.asset_public_id)) for item in ordered)


def _unit(db: Session, asset_public_id: str) -> AssetWithFittedParts:
    unit = get_asset_with_fitted_parts(db, asset_public_id)
    if unit is None:
        raise EligibilityNotFoundError("No machine, part or piece of kit was found with that id.")
    return unit


def _summary(facts: AssetFacts, structure: Any) -> AssetSummary:
    equipment_class = find_class(structure, facts.class_code)
    equipment_type = find_type(equipment_class, facts.type_code) if equipment_class and facts.type_code else None
    return AssetSummary(
        asset_public_id=facts.asset_public_id,
        asset_reference=facts.asset_reference,
        asset_kind_code=facts.asset_kind_code,
        origin_code=facts.origin_code,
        class_code=facts.class_code,
        class_label=equipment_class.class_label if equipment_class else facts.class_code,
        type_code=facts.type_code,
        type_label=equipment_type.type_label if equipment_type else None,
        machine_number=facts.machine_number,
        serial_number=facts.serial_number,
        asset_status_code=facts.asset_status_code,
    )


# --- An asset's certificates (its page) ------------------------------------------------------------------


def _certificate_response(
    row: dict[str, Any],
    *,
    references: dict[str, str],
    kinds: dict[str, evaluation.Kind],
    jurisdictions: dict[str, dict[str, Any]],
    in_force: set[int],
    show_numbers: bool,
) -> CertificateResponse:
    valid_in = jurisdictions.get(row["valid_in_code"]) if row["valid_in_code"] else None
    return CertificateResponse(
        certificate_public_id=row["certificate_public_id"],
        asset_public_id=row["equipment_asset_public_id"],
        asset_reference=references.get(row["equipment_asset_public_id"], ""),
        kind_code=row["kind_code"],
        kind_label=kinds[row["kind_code"]].kind_label,
        number=row["certificate_number"] if show_numbers else None,
        number_withheld=not show_numbers,
        issued_by=row["issued_by"],
        issued_on=row["issued_on"],
        valid_from=row["valid_from"],
        valid_until=row["valid_until"],
        valid_in_code=row["valid_in_code"],
        valid_in_label=valid_in["jurisdiction_label"] if valid_in else None,
        registered_as_code=row["registered_as_code"],
        certificate_status_code=row["certificate_status_code"],
        has_copy=row["has_copy"],
        in_force=row["id"] in in_force,
        recorded_by_display_name=row["recorded_by_display_name"],
        recorded_at=row["recorded_at"],
        withdrawn_reason=row["withdrawn_reason"] if show_numbers else None,
        withdrawn_by_display_name=row["withdrawn_by_display_name"],
        withdrawn_at=row["withdrawn_at"],
    )


def _mark_response(
    row: dict[str, Any], *, references: dict[str, str], kinds: dict[str, evaluation.Kind], show_numbers: bool
) -> MarkResponse:
    """A mark's reasons are the Fleet Admin's free text, which may repeat a certificate number: withheld with the
    numbers, as a certificate's withdrawal reason is (independent review, round 6, ELG1-R6-003)."""
    return MarkResponse(
        mark_public_id=row["mark_public_id"],
        asset_public_id=row["equipment_asset_public_id"],
        asset_reference=references.get(row["equipment_asset_public_id"], ""),
        kind_code=row["kind_code"],
        kind_label=kinds[row["kind_code"]].kind_label,
        reason=row["reason"] if show_numbers else None,
        reason_withheld=not show_numbers,
        until_date=row["until_date"],
        recorded_on=row["recorded_on"],
        mark_status_code=row["mark_status_code"],
        allowed_by_rule_public_id=row["allowed_by_rule_public_id"],
        recorded_by_display_name=row["recorded_by_display_name"],
        recorded_at=row["recorded_at"],
        withdrawn_reason=row["withdrawn_reason"] if show_numbers else None,
        withdrawn_by_display_name=row["withdrawn_by_display_name"],
        withdrawn_at=row["withdrawn_at"],
    )


def _in_force_ids(certificates: tuple[evaluation.Certificate, ...], today: date) -> set[int]:
    """The certificate in force today for each asset, kind and place."""
    groups: dict[tuple[str, str, str | None], list[evaluation.Certificate]] = {}
    for item in certificates:
        groups.setdefault((item.asset_public_id, item.kind_code, item.valid_in_code), []).append(item)
    current = (evaluation.in_force(items, today) for items in groups.values())
    return {item.certificate_id for item in current if item is not None}


def get_asset_certificates(db: Session, asset_public_id: str, *, show_numbers: bool) -> AssetCertificatesResponse:
    return _asset_certificates(db, _unit(db, asset_public_id), show_numbers=show_numbers, today=business_time.india_today())


def _asset_certificates(db: Session, unit: AssetWithFittedParts, *, show_numbers: bool, today: date) -> AssetCertificatesResponse:
    structure = get_equipment_structure(db)
    members = _members(unit)
    root = members[0]
    parts = [part for part, _parent in unit.fitted_parts]
    references = {item.asset_public_id: item.asset_reference for item in [unit.asset, *parts]}
    loaded = _load(db, list(references))
    evidence = loaded.evidence
    kinds = evidence.kinds
    jurisdictions = _jurisdictions(db)
    in_force = _in_force_ids(evidence.certificates, today)
    certificate_rows = loaded.certificate_rows

    def certificate(certificate_id: int | None) -> CertificateResponse | None:
        if certificate_id is None:
            return None
        return _certificate_response(
            certificate_rows[certificate_id],
            references=references,
            kinds=kinds,
            jurisdictions=jurisdictions,
            in_force=in_force,
            show_numbers=show_numbers,
        )

    # This asset's own rules, met by its certificates or its fitted parts'. The kinds of the parts' own rules
    # show on their own pages.
    results = evaluation.baseline_results((root,), evidence, today=today)
    statuses = [
        KindStatus(
            kind_code=result.kind_code,
            kind_label=kinds[result.kind_code].kind_label,
            required=True,
            rule=_rule_summary(result.rule, loaded.rule_rows),
            outcome_code=result.outcome_code,
            cover_ends_on=result.cover_ends_on,
            certificate=certificate(result.certificate.certificate_id if result.certificate else None),
            mark=_mark_response(loaded.mark_rows[result.mark.mark_id], references=references, kinds=kinds, show_numbers=show_numbers) if result.mark else None,
        )
        for result in results
        if result.kind_code is not None and result.rule is not None
    ]
    # Kinds recorded on the asset itself that it is not required to hold - a carrier's road papers, which count
    # for its crane.
    required = {status.kind_code for status in statuses}
    recorded_here = sorted(
        {item.kind_code for item in evidence.certificates if item.asset_public_id == unit.asset.asset_public_id and not item.withdrawn}
        - required,
        key=lambda code: kinds[code].display_order,
    )
    for kind_code in recorded_here:
        current = evaluation.in_force(
            [item for item in evidence.certificates if item.asset_public_id == unit.asset.asset_public_id and item.kind_code == kind_code],
            today,
        )
        statuses.append(
            KindStatus(
                kind_code=kind_code,
                kind_label=kinds[kind_code].kind_label,
                required=False,
                rule=None,
                outcome_code=None,
                cover_ends_on=evaluation.cover_end(current, None) if current else None,
                certificate=certificate(current.certificate_id if current else None),
                mark=None,
            )
        )

    equipment_class = find_class(structure, unit.asset.class_code)
    fits = equipment_class.fits_class_codes if equipment_class else []
    recordable = evaluation.recordable_kinds(
        evidence.rules, class_code=unit.asset.class_code, type_code=unit.asset.type_code, fits_class_codes=fits
    )
    markable: list[MarkableKind] = []
    # A kind already carrying a mark is not offered again: the server refuses a second until the first is
    # withdrawn (independent review, round 1, ELG1-R1-007).
    marked = {item.kind_code for item in evidence.marks if item.asset_public_id == unit.asset.asset_public_id and not item.withdrawn}
    if unit.asset.asset_status_code == ASSET_STATUS_ACTIVE:
        for kind_code in sorted(set(kinds) - marked, key=lambda code: kinds[code].display_order):
            rule = evaluation.rule_allowing_mark(evidence.rules, kind_code=kind_code, asset=root.asset, today=today)
            if rule is not None:
                markable.append(
                    MarkableKind(
                        kind_code=kind_code,
                        kind_label=kinds[kind_code].kind_label,
                        rule=_rule_summary(rule, loaded.rule_rows),
                        latest_until=evaluation.mark_limit(rule, today),
                    )
                )

    return AssetCertificatesResponse(
        asset=_summary(unit.asset, structure),
        fitted_to=_summary(unit.fitted_to, structure) if unit.fitted_to else None,
        fitted_parts=[_summary(part, structure) for part in parts],
        numbers_withheld=not show_numbers,
        statuses=statuses,
        certificates=[
            certificate(row_id)
            for row_id in sorted(
                certificate_rows, key=lambda row_id: (certificate_rows[row_id]["valid_from"], row_id), reverse=True
            )
        ],
        marks=[
            _mark_response(row, references=references, kinds=kinds, show_numbers=show_numbers)
            for row in sorted(loaded.mark_rows.values(), key=lambda row: row["id"], reverse=True)
        ],
        recordable_kind_codes=sorted(recordable, key=lambda code: kinds[code].display_order),
        markable_kinds=markable,
    )


# --- Recording and withdrawing certificates ------------------------------------------------------------------


def _begin_write(db: Session) -> None:
    repo.take_write_lock(db)


def _code_or_none(value: str | None) -> str | None:
    return (value or "").strip().upper() or None


def _is_repeat(existing: dict[str, Any], asked: dict[str, Any]) -> bool:
    """Whether a request carrying a used request key asks for exactly what the key first made. Only an exact
    repeat is answered with that record; a key reused for anything else is refused, never answered with a record
    the caller did not ask for (as ERT-2's kit, refinement 13)."""
    return all(existing[column] == value for column, value in asked.items())


def _certificate_request(asset_public_id: str, payload: CertificateInput) -> dict[str, Any]:
    return {
        "equipment_asset_public_id": asset_public_id,
        "kind_code": _code_or_none(payload.kind_code),
        "certificate_number": _clean(payload.number),
        "issued_by": _clean(payload.issued_by),
        "issued_on": payload.issued_on,
        "valid_from": payload.valid_from,
        "valid_until": payload.valid_until,
        "valid_in_code": _code_or_none(payload.valid_in_code),
        "registered_as_code": _code_or_none(payload.registered_as_code),
    }


def _mark_request(asset_public_id: str, payload: NotApplicableInput) -> dict[str, Any]:
    return {
        "equipment_asset_public_id": asset_public_id,
        "kind_code": _code_or_none(payload.kind_code),
        "reason": _clean(payload.reason),
        "until_date": payload.until,
    }


def _rule_request(payload: RuleInput) -> dict[str, Any]:
    return {
        "kind_code": _code_or_none(payload.kind_code),
        "class_code": _code_or_none(payload.class_code),
        "type_code": _code_or_none(payload.type_code),
        "applies_when_code": _code_or_none(payload.applies_when_code),
        "jurisdiction_code": _code_or_none(payload.jurisdiction_code),
        "effective_from": payload.effective_from,
        "renew_every_months": payload.renew_every_months,
        "basis_code": _code_or_none(payload.basis_code),
        "lapse_code": _code_or_none(payload.lapse_code),
        "not_applicable_code": _code_or_none(payload.not_applicable_code),
        "not_applicable_max_months": payload.not_applicable_max_months,
        "source": _clean(payload.source),
        "note": _clean(payload.note),
    }


def _active_unit(db: Session, asset_public_id: str, *, what: str) -> AssetWithFittedParts:
    unit = _unit(db, asset_public_id)
    if unit.asset.asset_status_code != ASSET_STATUS_ACTIVE:
        raise EligibilityValidationError(f"{unit.asset.asset_reference} is retired, so no {what} is recorded for it.")
    return unit


def _asset_payload(unit: AssetWithFittedParts) -> dict[str, Any]:
    return {"asset_public_id": unit.asset.asset_public_id, "asset_reference": unit.asset.asset_reference}


def record_certificate(
    db: Session, *, asset_public_id: str, payload: CertificateInput, user_public_id: str | None, show_numbers: bool
) -> CertificateActionResponse:
    with rollback_on_error(db):
        user = _require_user(user_public_id)
        _begin_write(db)
        unit = _unit(db, asset_public_id)
        _require_request_key(payload.create_request_key)
        existing = repo.find_certificate_by_create_request_key(db, create_request_key=payload.create_request_key)
        if existing is not None:
            if not _is_repeat(existing, _certificate_request(asset_public_id, payload)):
                raise EligibilityConflictError("This request was already used to record another certificate.")
            db.rollback()
            return CertificateActionResponse(
                certificates=_asset_certificates(db, unit, show_numbers=show_numbers, today=business_time.india_today()),
                certificate_public_id=existing["certificate_public_id"],
                replayed=True,
            )
        unit = _active_unit(db, asset_public_id, what="certificate")
        today = business_time.india_today()
        values = _validated_certificate(db, unit, payload, today=today)
        public_id = str(uuid4())
        try:
            repo.insert_certificate(
                db,
                values={
                    "certificate_public_id": public_id,
                    "equipment_asset_public_id": asset_public_id,
                    **values,
                    "create_request_key": payload.create_request_key,
                    "recorded_by": user,
                    "recorded_at": _now(),
                },
            )
        except IntegrityError as exc:
            raise EligibilityValidationError("The certificate was refused by the database's own checks.") from exc
        event = _event(
            db,
            event_name=EVENT_CERTIFICATE_RECORDED,
            record_type=RECORD_TYPE_CERTIFICATE,
            record_public_id=public_id,
            user_public_id=user,
            status_after="RECORDED",
            reason="Certificate recorded.",
            payload={
                **_asset_payload(unit),
                "kind_code": values["kind_code"],
                "issued_on": _date(values["issued_on"]),
                "valid_from": _date(values["valid_from"]),
                "valid_until": _date(values["valid_until"]),
                "valid_in_code": values["valid_in_code"],
                "registered_as_code": values["registered_as_code"],
            },
        )
        db.commit()
    return CertificateActionResponse(
        certificates=_asset_certificates(db, unit, show_numbers=show_numbers, today=today),
        certificate_public_id=public_id,
        event=event,
    )


def _validated_certificate(db: Session, unit: AssetWithFittedParts, payload: CertificateInput, *, today: date) -> dict[str, Any]:
    kinds = _kinds(db)
    kind_code = (payload.kind_code or "").strip().upper()
    kind = kinds.get(kind_code)
    if kind is None:
        raise EligibilityValidationError("Choose a kind of certificate from the list.")
    structure = get_equipment_structure(db)
    equipment_class = find_class(structure, unit.asset.class_code)
    rules = tuple(_rule(row) for row in repo.list_rule_rows(db))
    recordable = evaluation.recordable_kinds(
        rules,
        class_code=unit.asset.class_code,
        type_code=unit.asset.type_code,
        fits_class_codes=equipment_class.fits_class_codes if equipment_class else [],
    )
    if kind_code not in recordable:
        label = equipment_class.class_label.lower() if equipment_class else unit.asset.class_code
        raise EligibilityValidationError(f"No rule requires a {kind.kind_label.lower()} of a {label}, so it is not recorded here.")
    number = _required_text(payload.number, what="the certificate's number, as printed")
    issued_by = _required_text(payload.issued_by, what="who issued it")
    if payload.issued_on > today:
        raise EligibilityValidationError("The day it was issued cannot be in the future.")
    if payload.valid_until is None and not kind.end_date_optional:
        raise EligibilityValidationError(f"Give the day the {kind.kind_label.lower()} runs until.")
    if payload.valid_until is not None and payload.valid_until < payload.valid_from:
        raise EligibilityValidationError("It cannot run out before it starts.")
    valid_in_code = (payload.valid_in_code or "").strip().upper() or None
    if kind.valid_in_required:
        jurisdiction = _jurisdictions(db).get(valid_in_code or "")
        if jurisdiction is None:
            raise EligibilityValidationError("Give where the permit is valid: a state, or all India for a national permit.")
    elif valid_in_code is not None:
        raise EligibilityValidationError("Only a permit says where it is valid.")
    registered_as_code = (payload.registered_as_code or "").strip().upper() or None
    if kind.states_registration:
        if registered_as_code not in REGISTERED_AS_CODES:
            raise EligibilityValidationError("Say whether the registration is as a transport or a non-transport vehicle.")
    elif registered_as_code is not None:
        raise EligibilityValidationError("Only a registration says how the vehicle is registered.")
    return {
        "kind_code": kind_code,
        "end_date_optional": kind.end_date_optional,
        "valid_in_required": kind.valid_in_required,
        "states_registration": kind.states_registration,
        "certificate_number": number,
        "issued_by": issued_by,
        "issued_on": payload.issued_on,
        "valid_from": payload.valid_from,
        "valid_until": payload.valid_until,
        "valid_in_code": valid_in_code,
        "registered_as_code": registered_as_code,
    }


def withdraw_certificate(
    db: Session, *, certificate_public_id: str, payload: WithdrawInput, user_public_id: str | None, show_numbers: bool
) -> CertificateActionResponse:
    """Withdraw a certificate recorded by mistake. The one before it is then in force again. Withdrawing one
    already withdrawn changes nothing."""
    with rollback_on_error(db):
        user = _require_user(user_public_id)
        _begin_write(db)
        row = repo.lock_certificate_row(db, public_id=certificate_public_id)
        if row is None:
            raise EligibilityNotFoundError("No certificate was found with that id.")
        unit = _unit(db, row["equipment_asset_public_id"])
        event = None
        if row["certificate_status_code"] != CERTIFICATE_STATUS_WITHDRAWN:
            reason = _required_text(payload.reason, what="the reason for withdrawing it")
            repo.withdraw_certificate(db, certificate_id=row["id"], reason=reason, user_public_id=user, at=_now())
            event = _event(
                db,
                event_name=EVENT_CERTIFICATE_WITHDRAWN,
                record_type=RECORD_TYPE_CERTIFICATE,
                record_public_id=certificate_public_id,
                user_public_id=user,
                status_before="RECORDED",
                status_after=CERTIFICATE_STATUS_WITHDRAWN,
                # Not the Fleet Admin's reason, which may repeat the certificate's number: that stays on the
                # certificate, shown only with EQUIPMENT_IDENTITY_READ (independent review, round 1, ELG1-R1-005).
                reason="Certificate withdrawn as recorded by mistake.",
                payload={**_asset_payload(unit), "kind_code": row["kind_code"]},
            )
        db.commit()
    return CertificateActionResponse(
        certificates=_asset_certificates(db, unit, show_numbers=show_numbers, today=business_time.india_today()),
        certificate_public_id=certificate_public_id,
        event=event,
    )


def certificate_copy_refusal(db: Session, request: AttachRequest) -> str | None:
    """Why this file may not be attached to a certificate, or None: the documents module asks before storing one.
    A certificate takes only its copy - an uploaded file of type CERTIFICATE - and none once withdrawn."""
    if request.document_type != COPY_DOCUMENT_TYPE:
        return "A certificate takes only its copy: choose the document type Certificate."
    if request.storage_mode != STORAGE_MODE_LOCAL_UPLOAD:
        return "A certificate's copy must be uploaded here, not recorded as a link to a file kept elsewhere."
    # The module's write lock, held until the documents module's transaction ends: a withdrawal cannot slip in
    # between this read and the copy being stored (independent review, round 2, ELG1-R2-001).
    _begin_write(db)
    row = repo.get_certificate_row(db, public_id=request.linked_record_public_id)
    if row is None:
        return "No certificate was found with that id, so the copy was not attached."
    if row["certificate_status_code"] == CERTIFICATE_STATUS_WITHDRAWN:
        return "This certificate was withdrawn, so no copy is attached to it."
    return None


register_attach_check(RECORD_TYPE_CERTIFICATE, certificate_copy_refusal)


# --- "Not applicable" -------------------------------------------------------------------------------------


def record_not_applicable(
    db: Session, *, asset_public_id: str, payload: NotApplicableInput, user_public_id: str | None, show_numbers: bool
) -> CertificateActionResponse:
    """Mark one kind "not applicable" for one asset, where a rule in force today allows it - only where the law is
    unclear (owner, 27 September 2026)."""
    with rollback_on_error(db):
        user = _require_user(user_public_id)
        _begin_write(db)
        unit = _unit(db, asset_public_id)
        _require_request_key(payload.create_request_key)
        existing = repo.find_mark_by_create_request_key(db, create_request_key=payload.create_request_key)
        if existing is not None:
            if not _is_repeat(existing, _mark_request(asset_public_id, payload)):
                raise EligibilityConflictError("This request was already used for another 'not applicable' mark.")
            db.rollback()
            return CertificateActionResponse(
                certificates=_asset_certificates(db, unit, show_numbers=show_numbers, today=business_time.india_today()),
                mark_public_id=existing["mark_public_id"],
                replayed=True,
            )
        unit = _active_unit(db, asset_public_id, what="mark")
        today = business_time.india_today()
        kinds = _kinds(db)
        kind_code = (payload.kind_code or "").strip().upper()
        kind = kinds.get(kind_code)
        if kind is None:
            raise EligibilityValidationError("Choose a kind of certificate from the list.")
        rules = tuple(_rule(row) for row in repo.list_rule_rows(db))
        rule = evaluation.rule_allowing_mark(rules, kind_code=kind_code, asset=_eval_asset(unit.asset), today=today)
        if rule is None:
            raise EligibilityValidationError(
                f"The law is clear that this machine needs its {kind.kind_label.lower()}, so it cannot be marked not applicable."
            )
        reason = _required_text(payload.reason, what="the reason it does not apply")
        limit = evaluation.mark_limit(rule, today)
        if payload.until is not None and payload.until < today:
            raise EligibilityValidationError("The day it stops applying cannot be in the past.")
        if limit is not None and (payload.until is None or payload.until > limit):
            raise EligibilityValidationError(
                f"This mark may run for at most {rule.not_applicable_max_months} months: give an end no later than {_long_date(limit)}."
            )
        if repo.find_mark_in_force(db, asset_public_id=asset_public_id, kind_code=kind_code) is not None:
            raise EligibilityConflictError(f"The {kind.kind_label.lower()} is already marked not applicable. Withdraw that mark first.")
        public_id = str(uuid4())
        repo.insert_mark(
            db,
            values={
                "mark_public_id": public_id,
                "equipment_asset_public_id": asset_public_id,
                "kind_code": kind_code,
                "allowed_by_rule_id": rule.rule_id,
                "reason": reason,
                "until_date": payload.until,
                "recorded_on": today,
                "create_request_key": payload.create_request_key,
                "recorded_by": user,
                "recorded_at": _now(),
            },
        )
        event = _event(
            db,
            event_name=EVENT_NOT_APPLICABLE_RECORDED,
            record_type=RECORD_TYPE_NOT_APPLICABLE,
            record_public_id=public_id,
            user_public_id=user,
            status_after="IN_FORCE",
            reason="Marked not applicable where a rule allows it.",
            payload={**_asset_payload(unit), "kind_code": kind_code, "until": _date(payload.until), "rule_public_id": rule.rule_public_id},
        )
        db.commit()
    return CertificateActionResponse(
        certificates=_asset_certificates(db, unit, show_numbers=show_numbers, today=today), mark_public_id=public_id, event=event
    )


def withdraw_not_applicable(
    db: Session, *, mark_public_id: str, payload: WithdrawInput, user_public_id: str | None, show_numbers: bool
) -> CertificateActionResponse:
    with rollback_on_error(db):
        user = _require_user(user_public_id)
        _begin_write(db)
        row = repo.lock_mark_row(db, public_id=mark_public_id)
        if row is None:
            raise EligibilityNotFoundError("No 'not applicable' mark was found with that id.")
        unit = _unit(db, row["equipment_asset_public_id"])
        event = None
        if row["mark_status_code"] != MARK_STATUS_WITHDRAWN:
            reason = _required_text(payload.reason, what="the reason for withdrawing it")
            repo.withdraw_mark(db, mark_id=row["id"], reason=reason, user_public_id=user, at=_now())
            full = repo.get_mark_row(db, public_id=mark_public_id)
            event = _event(
                db,
                event_name=EVENT_NOT_APPLICABLE_WITHDRAWN,
                record_type=RECORD_TYPE_NOT_APPLICABLE,
                record_public_id=mark_public_id,
                user_public_id=user,
                status_before="IN_FORCE",
                status_after=MARK_STATUS_WITHDRAWN,
                reason="'Not applicable' mark withdrawn.",
                payload={
                    **_asset_payload(unit),
                    "kind_code": row["kind_code"],
                    "until": _date(full["until_date"]),
                    "rule_public_id": full["allowed_by_rule_public_id"],
                },
            )
        db.commit()
    return CertificateActionResponse(
        certificates=_asset_certificates(db, unit, show_numbers=show_numbers, today=business_time.india_today()),
        mark_public_id=mark_public_id,
        event=event,
    )


# --- The check (section 6) --------------------------------------------------------------------------------


@dataclass(frozen=True)
class _Judged:
    unit: AssetWithFittedParts
    decision: evaluation.Decision
    loaded: _Loaded
    site: evaluation.Site
    period: evaluation.Period
    today: date
    references: dict[str, str]


def _judge(
    db: Session,
    *,
    asset_public_id: str,
    state_code: str,
    central_government_site: bool,
    period_from: date,
    period_to: date | None,
    today: date | None,
) -> _Judged:
    today = today or business_time.india_today()
    state = _jurisdictions(db).get((state_code or "").strip().upper())
    if state is None or state["jurisdiction_kind_code"] == JURISDICTION_KIND_CENTRAL:
        raise EligibilityValidationError("Choose the site's state or union territory.")
    if period_to is not None and period_to < period_from:
        raise EligibilityValidationError("The period cannot end before it starts.")
    unit = _unit(db, asset_public_id)
    if unit.asset.asset_kind_code == ASSET_KIND_PART and unit.asset.origin_code != ORIGIN_PLATFORM:
        where = f", {unit.fitted_to.asset_reference}" if unit.fitted_to else ""
        raise EligibilityValidationError(f"A part is checked with the machine it is fitted to{where}.")
    members = _members(unit)
    references = {unit.asset.asset_public_id: unit.asset.asset_reference}
    references.update({part.asset_public_id: part.asset_reference for part, _parent in unit.fitted_parts})
    loaded = _load(db, list(references))
    site = evaluation.Site(state["jurisdiction_code"], central_government_site)
    period = evaluation.Period(period_from, period_to)
    decision = evaluation.evaluate(members, loaded.evidence, site=site, period=period, today=today)
    return _Judged(unit, decision, loaded, site, period, today, references)


def _check_response(db: Session, judged: _Judged) -> EligibilityCheckResponse:
    structure = get_equipment_structure(db)
    kinds = judged.loaded.evidence.kinds
    jurisdictions = _jurisdictions(db)
    results = [
        CheckResult(
            asset_public_id=result.asset_public_id,
            asset_reference=judged.references.get(result.asset_public_id, ""),
            kind_code=result.kind_code,
            kind_label=kinds[result.kind_code].kind_label if result.kind_code else None,
            outcome_code=result.outcome_code,
            effect_code=result.effect_code,
            lapse_code=result.rule.lapse_code if result.rule else None,
            basis_code=result.rule.basis_code if result.rule else None,
            rule_public_id=result.rule.rule_public_id if result.rule else None,
            rule_jurisdiction_code=result.rule.jurisdiction_code if result.rule else None,
            certificate_public_id=result.certificate.certificate_public_id if result.certificate else None,
            certificate_asset_reference=judged.references.get(result.certificate.asset_public_id) if result.certificate else None,
            mark_public_id=result.mark.mark_public_id if result.mark else None,
            cover_ends_on=result.cover_ends_on,
        )
        for result in judged.decision.results
    ]
    return EligibilityCheckResponse(
        asset=_summary(judged.unit.asset, structure),
        site_state_code=judged.site.state_code,
        site_state_label=jurisdictions[judged.site.state_code]["jurisdiction_label"],
        central_government_site=judged.site.central_government_site,
        period_from=judged.period.starts_on,
        period_to=judged.period.ends_on,
        evaluated_on=judged.today,
        overall_code=judged.decision.overall_code,
        valid_until=judged.decision.valid_until,
        outcome_counts=dict(Counter(result.outcome_code for result in judged.decision.results)),
        results=results,
    )


def evaluate_asset(
    db: Session,
    *,
    asset_public_id: str,
    state_code: str,
    central_government_site: bool,
    period_from: date,
    period_to: date | None,
    today: date | None = None,
) -> EligibilityCheckResponse:
    """May this machine (with its fitted parts), or this piece of kit, work at this site over this period?
    Nothing is kept and no event is recorded: the screen's check (section 6, step 5)."""
    return _check_response(
        db,
        _judge(
            db,
            asset_public_id=asset_public_id,
            state_code=state_code,
            central_government_site=central_government_site,
            period_from=period_from,
            period_to=period_to,
            today=today,
        ),
    )


def record_decision(
    db: Session,
    *,
    asset_public_id: str,
    state_code: str,
    central_government_site: bool,
    period_from: date,
    period_to: date | None,
    requested_by: str,
    requested_for_type: str | None = None,
    requested_for_public_id: str | None = None,
) -> tuple[str, EligibilityCheckResponse]:
    """The check, stored with its results inside the caller's transaction, and ELIGIBILITY_EVALUATED recorded - for
    8A, which keeps the returned decision public id with its allocation (ELA-001, RPA-001). The caller commits,
    and cannot turn BLOCKED into an allocation. No route calls it."""
    if (requested_for_type is None) != (requested_for_public_id is None):
        raise EligibilityValidationError("Name both what asked for the decision and its id, or neither.")
    # The module's write lock, held until the caller commits or rolls back: no certificate, mark or rule changes
    # between the evidence read and the decision stored on it.
    _begin_write(db)
    judged = _judge(
        db,
        asset_public_id=asset_public_id,
        state_code=state_code,
        central_government_site=central_government_site,
        period_from=period_from,
        period_to=period_to,
        today=None,
    )
    public_id = str(uuid4())
    decision = judged.decision
    decision_id = repo.insert_decision(
        db,
        values={
            "decision_public_id": public_id,
            "equipment_asset_public_id": asset_public_id,
            "asset_version": judged.unit.asset.asset_version,
            "site_state_code": judged.site.state_code,
            "central_government_site": judged.site.central_government_site,
            "period_from": period_from,
            "period_to": period_to,
            "evaluated_on": judged.today,
            "evaluated_at": _now(),
            "requested_by": requested_by,
            "requested_for_type": requested_for_type,
            "requested_for_public_id": requested_for_public_id,
            "overall_code": decision.overall_code,
            "valid_until": decision.valid_until,
        },
    )
    repo.insert_decision_results(
        db,
        decision_id=decision_id,
        rows=[
            {
                "result_number": number,
                "equipment_asset_public_id": result.asset_public_id,
                "kind_code": result.kind_code,
                "rule_id": result.rule.rule_id if result.rule else None,
                "rule_jurisdiction_code": result.rule.jurisdiction_code if result.rule else None,
                "certificate_id": result.certificate.certificate_id if result.certificate else None,
                "mark_id": result.mark.mark_id if result.mark else None,
                "outcome_code": result.outcome_code,
                "lapse_code": result.rule.lapse_code if result.rule else None,
                "effect_code": result.effect_code,
                "cover_ends_on": result.cover_ends_on,
            }
            for number, result in enumerate(decision.results, 1)
        ],
    )
    _event(
        db,
        event_name=EVENT_EVALUATED,
        record_type=RECORD_TYPE_DECISION,
        record_public_id=public_id,
        user_public_id=requested_by,
        status_after=decision.overall_code,
        reason="Eligibility evaluated.",
        payload={
            "decision_public_id": public_id,
            "asset_public_id": asset_public_id,
            "asset_reference": judged.unit.asset.asset_reference,
            "asset_version": judged.unit.asset.asset_version,
            "site_state_code": judged.site.state_code,
            "central_government_site": judged.site.central_government_site,
            "period_from": _date(period_from),
            "period_to": _date(period_to),
            "overall_code": decision.overall_code,
            "valid_until": _date(decision.valid_until),
            "outcome_counts": dict(Counter(result.outcome_code for result in decision.results)),
            "requested_for_type": requested_for_type,
            "requested_for_public_id": requested_for_public_id,
        },
    )
    return public_id, _check_response(db, judged)


# --- The whole fleet, read once (Certificates due; the reminders of ELG-2) ------------------------------------


@dataclass(frozen=True)
class FleetReading:
    """Every active asset with the parts fitted below it, and the evidence for all of them, read once and judged in
    memory: Certificates due, and the reminders, which also judge each allocation for its own site and days (ELG-2,
    section 5.7)."""

    today: date
    units: tuple[AssetWithFittedParts, ...]
    by_asset: dict[str, AssetWithFittedParts]
    loaded: _Loaded
    references: dict[str, str]
    structure: Any
    jurisdictions: dict[str, dict[str, Any]]

    @property
    def evidence(self) -> evaluation.Evidence:
        return self.loaded.evidence


def read_fleet(db: Session, *, today: date | None = None) -> FleetReading:
    units = tuple(list_active_assets_with_fitted_parts(db))
    references: dict[str, str] = {}
    for unit in units:
        references[unit.asset.asset_public_id] = unit.asset.asset_reference
        references.update({part.asset_public_id: part.asset_reference for part, _parent in unit.fitted_parts})
    return FleetReading(
        today=today or business_time.india_today(),
        units=units,
        by_asset={unit.asset.asset_public_id: unit for unit in units},
        loaded=_load(db, None),
        references=references,
        structure=get_equipment_structure(db),
        jurisdictions=_jurisdictions(db),
    )


def member_assets(unit: AssetWithFittedParts) -> dict[str, tuple[str, ...]]:
    """For each asset of the unit, the assets whose certificates meet its rules: itself and the active parts fitted
    below it."""
    return {member.asset.asset_public_id: member.subtree for member in _members(unit)}


def added_on(unit: AssetWithFittedParts) -> dict[str, date]:
    """The day each asset of the unit was added to the Equipment Master."""
    days = {part.asset_public_id: part.added_on for part, _parent in unit.fitted_parts}
    days[unit.asset.asset_public_id] = unit.asset.added_on
    return days


def baseline_of(reading: FleetReading, unit: AssetWithFittedParts) -> list[evaluation.Result]:
    """What the baseline rules require of the asset today, and how each stands: a row of Certificates due."""
    return evaluation.baseline_results((_members(unit)[0],), reading.evidence, today=reading.today)


def judge_in_fleet(
    reading: FleetReading,
    unit: AssetWithFittedParts,
    *,
    state_code: str,
    central_government_site: bool,
    period_from: date,
    period_to: date | None,
) -> evaluation.Decision | None:
    """The check of one unit for a site and days, against the fleet's one reading of the evidence - what
    `evaluate_asset` answers, without reading the evidence again. None where the check refuses: a state it does not
    know, or a Plum part, which is checked with its machine."""
    state = reading.jurisdictions.get((state_code or "").strip().upper())
    if state is None or state["jurisdiction_kind_code"] == JURISDICTION_KIND_CENTRAL:
        return None
    if period_to is not None and period_to < period_from:
        return None
    if unit.asset.asset_kind_code == ASSET_KIND_PART and unit.asset.origin_code != ORIGIN_PLATFORM:
        return None
    return evaluation.evaluate(
        _members(unit),
        reading.evidence,
        site=evaluation.Site(state["jurisdiction_code"], central_government_site),
        period=evaluation.Period(period_from, period_to),
        today=reading.today,
    )


def asset_summary(reading: FleetReading, facts: AssetFacts) -> AssetSummary:
    return _summary(facts, reading.structure)


def kind_label(reading: FleetReading, kind_code: str) -> str:
    return reading.evidence.kinds[kind_code].kind_label


# --- Certificates due (section 7) --------------------------------------------------------------------------


def list_certificates_due(
    db: Session,
    *,
    band_code: str | None,
    class_code: str | None,
    kind_code: str | None,
    search: str | None,
    limit: int,
    offset: int,
) -> CertificatesDueResponse:
    """Everything missing, without its copy, run out, or running out within 60, 30 or 15 days, by the baseline
    rules; and every "not applicable" mark ending within them. Worked out each time it is read: nothing is
    stored and nothing is sent (section 7)."""
    if band_code is not None and band_code not in BAND_CODES:
        raise EligibilityValidationError("Choose a band from the list.")
    reading = read_fleet(db)
    today = reading.today
    structure = reading.structure
    evidence = reading.evidence
    references = reading.references
    needle = (search or "").strip().lower()

    items: list[DueItem] = []
    for unit in reading.units:
        facts = unit.asset
        if class_code and facts.class_code != class_code:
            continue
        if needle and not any(needle in (value or "").lower() for value in (facts.machine_number, facts.asset_reference, facts.serial_number)):
            continue
        for result in baseline_of(reading, unit):
            if kind_code and result.kind_code != kind_code:
                continue
            band = evaluation.due_band(result, today)
            if band is None:
                continue
            certificate_asset = result.certificate.asset_public_id if result.certificate else None
            items.append(
                DueItem(
                    asset=_summary(facts, structure),
                    kind_code=result.kind_code,
                    kind_label=evidence.kinds[result.kind_code].kind_label,
                    band_code=band,
                    outcome_code=result.outcome_code,
                    cover_ends_on=result.cover_ends_on,
                    certificate_public_id=result.certificate.certificate_public_id if result.certificate else None,
                    certificate_asset_reference=references.get(certificate_asset) if certificate_asset and certificate_asset != facts.asset_public_id else None,
                    mark_public_id=result.mark.mark_public_id if result.mark else None,
                )
            )
    band_order = {band: index for index, band in enumerate(BAND_CODES)}
    items.sort(key=lambda item: (band_order[item.band_code], item.cover_ends_on or date.min, item.asset.asset_reference, evidence.kinds[item.kind_code].display_order))
    counts = {band: 0 for band in BAND_CODES}
    for item in items:
        counts[item.band_code] += 1
    shown = [item for item in items if band_code is None or item.band_code == band_code]
    limit = max(1, min(limit, MAX_DUE_LIMIT))
    return CertificatesDueResponse(
        today=today,
        band_counts=counts,
        total=len(shown),
        limit=limit,
        offset=offset,
        items=shown[offset : offset + limit],
    )


# --- Rules (Q7) ----------------------------------------------------------------------------------------------


def _rule_state(row: dict[str, Any], today: date) -> str:
    if row["effective_to"] is not None and row["effective_to"] < today:
        return "ENDED"
    if row["effective_from"] > today:
        return "NOT_YET"
    return "IN_EFFECT"


def _rule_response(row: dict[str, Any], *, structure: Any, kinds: dict[str, evaluation.Kind], jurisdictions: dict[str, dict[str, Any]], today: date) -> RuleResponse:
    equipment_class = find_class(structure, row["class_code"])
    equipment_type = find_type(equipment_class, row["type_code"]) if equipment_class and row["type_code"] else None
    jurisdiction = jurisdictions.get(row["jurisdiction_code"]) if row["jurisdiction_code"] else None
    return RuleResponse(
        rule_public_id=row["rule_public_id"],
        kind_code=row["kind_code"],
        kind_label=kinds[row["kind_code"]].kind_label,
        class_code=row["class_code"],
        class_label=equipment_class.class_label if equipment_class else row["class_code"],
        type_code=row["type_code"],
        type_label=equipment_type.type_label if equipment_type else None,
        applies_when_code=row["applies_when_code"],
        jurisdiction_code=row["jurisdiction_code"],
        jurisdiction_label=jurisdiction["jurisdiction_label"] if jurisdiction else None,
        effective_from=row["effective_from"],
        effective_to=row["effective_to"],
        renew_every_months=row["renew_every_months"],
        basis_code=row["basis_code"],
        lapse_code=row["lapse_code"],
        not_applicable_code=row["not_applicable_code"],
        not_applicable_max_months=row["not_applicable_max_months"],
        source=row["source"],
        note=row["note"],
        state_code=_rule_state(row, today),
        recorded_by_display_name=row["recorded_by_display_name"],
        recorded_at=row["recorded_at"],
        ended_by_display_name=row["ended_by_display_name"],
        ended_at=row["ended_at"],
        end_reason=row["end_reason"],
    )


def list_rules(
    db: Session, *, jurisdiction_code: str | None, kind_code: str | None, class_code: str | None, in_effect_on: date | None
) -> list[RuleResponse]:
    """Every rule, or those of one jurisdiction (`BASELINE` for the rules for all of India), kind or class, or in
    effect on a day. Ended rules are kept and listed: past decisions are explained by them."""
    today = business_time.india_today()
    structure = get_equipment_structure(db)
    kinds = _kinds(db)
    jurisdictions = _jurisdictions(db)
    rows = []
    for row in repo.list_rule_rows(db):
        if jurisdiction_code == "BASELINE" and row["jurisdiction_code"] is not None:
            continue
        if jurisdiction_code not in (None, "BASELINE") and row["jurisdiction_code"] != jurisdiction_code:
            continue
        if kind_code and row["kind_code"] != kind_code:
            continue
        if class_code and row["class_code"] != class_code:
            continue
        if in_effect_on is not None and not _rule(row).in_effect_on(in_effect_on):
            continue
        rows.append(row)
    return [_rule_response(row, structure=structure, kinds=kinds, jurisdictions=jurisdictions, today=today) for row in rows]


def _rule_event_payload(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "kind_code": row["kind_code"],
        "class_code": row["class_code"],
        "type_code": row["type_code"],
        "applies_when_code": row["applies_when_code"],
        "jurisdiction_code": row["jurisdiction_code"],
        "effective_from": _date(row["effective_from"]),
        "effective_to": _date(row["effective_to"]),
        "renew_every_months": row["renew_every_months"],
        "basis_code": row["basis_code"],
        "lapse_code": row["lapse_code"],
        "not_applicable_code": row["not_applicable_code"],
        "not_applicable_max_months": row["not_applicable_max_months"],
    }


def _one_rule_response(db: Session, row: dict[str, Any]) -> RuleResponse:
    return _rule_response(row, structure=get_equipment_structure(db), kinds=_kinds(db), jurisdictions=_jurisdictions(db), today=business_time.india_today())


def record_rule(db: Session, *, payload: RuleInput, user_public_id: str | None) -> RuleActionResponse:
    """Add a rule, in effect from its date (Q7). Where it would be in effect on a day another rule for the same
    kind, class, type, "applies when" and jurisdiction is, it is refused: end that one first."""
    with rollback_on_error(db):
        user = _require_user(user_public_id)
        _begin_write(db)
        _require_request_key(payload.create_request_key)
        existing = repo.find_rule_by_create_request_key(db, create_request_key=payload.create_request_key)
        if existing is not None:
            if not _is_repeat(existing, _rule_request(payload)):
                raise EligibilityConflictError("This request was already used to add another rule.")
            db.rollback()
            return RuleActionResponse(rule=_one_rule_response(db, existing), replayed=True)
        values = _validated_rule(db, payload)
        candidate = evaluation.Rule(
            rule_id=0,
            rule_public_id="",
            kind_code=values["kind_code"],
            class_code=values["class_code"],
            type_code=values["type_code"],
            applies_when_code=values["applies_when_code"],
            jurisdiction_code=values["jurisdiction_code"],
            effective_from=values["effective_from"],
            effective_to=None,
            renew_every_months=values["renew_every_months"],
            basis_code=values["basis_code"],
            lapse_code=values["lapse_code"],
            not_applicable_code=values["not_applicable_code"],
            not_applicable_max_months=values["not_applicable_max_months"],
        )
        clash = next((row for row in repo.list_rule_rows(db) if evaluation.overlaps(candidate, _rule(row))), None)
        if clash is not None:
            until = f" until {_long_date(clash['effective_to'])}" if clash["effective_to"] else " with no end"
            raise EligibilityConflictError(
                f"Another rule for the same certificate, kind of machine and place is in effect from "
                f"{_long_date(clash['effective_from'])}{until}. End it first, then add this one from the next day."
            )
        public_id = str(uuid4())
        try:
            repo.insert_rule(
                db,
                values={"rule_public_id": public_id, **values, "create_request_key": payload.create_request_key, "recorded_by": user},
            )
        except IntegrityError as exc:
            raise EligibilityConflictError("Another rule for the same certificate, kind of machine and place is in effect then.") from exc
        row = repo.get_rule_row(db, public_id=public_id)
        event = _event(
            db,
            event_name=EVENT_RULE_RECORDED,
            record_type=RECORD_TYPE_RULE,
            record_public_id=public_id,
            user_public_id=user,
            status_after="RECORDED",
            reason="Eligibility rule recorded.",
            payload=_rule_event_payload(row),
        )
        db.commit()
    return RuleActionResponse(rule=_one_rule_response(db, row), event=event)


def _validated_rule(db: Session, payload: RuleInput) -> dict[str, Any]:
    kinds = _kinds(db)
    kind_code = payload.kind_code.strip().upper()
    kind = kinds.get(kind_code)
    if kind is None:
        raise EligibilityValidationError("Choose a kind of certificate from the list.")
    structure = get_equipment_structure(db)
    class_code = payload.class_code.strip().upper()
    equipment_class = find_class(structure, class_code)
    if equipment_class is None or not equipment_class.is_active:
        raise EligibilityValidationError("Choose a kind of machine, part or kit from the list.")
    type_code = (payload.type_code or "").strip().upper() or None
    if type_code is not None:
        equipment_type = find_type(equipment_class, type_code)
        if equipment_type is None or not equipment_type.is_active:
            raise EligibilityValidationError(f"Choose a type of {equipment_class.class_label.lower()} from the list, or none for every type.")
    applies_when = payload.applies_when_code.strip().upper()
    if applies_when not in APPLIES_WHEN_CODES:
        raise EligibilityValidationError("Say whether the rule applies always or only to transport vehicles.")
    if kind_code == KIND_REGISTRATION and applies_when != APPLIES_ALWAYS:
        raise EligibilityValidationError("The registration decides whether a machine is a transport vehicle, so its rule applies always.")
    jurisdiction_code = (payload.jurisdiction_code or "").strip().upper() or None
    if jurisdiction_code is not None and jurisdiction_code not in _jurisdictions(db):
        raise EligibilityValidationError("Choose where the rule applies: all of India, the central government's sites, or a state.")
    if jurisdiction_code == JURISDICTION_CENTRAL and not kind.is_examination:
        # At a central-government site the examinations follow IN's rules and road papers the state's (evaluation.py,
        # rule_jurisdiction), so an IN rule for a road paper would never be used (independent review, round 5).
        raise EligibilityValidationError(
            f"At central government sites only the examinations have rules of their own; a {kind.kind_label.lower()} follows the site's state."
        )
    basis = payload.basis_code.strip().upper()
    if basis not in BASIS_CODES:
        raise EligibilityValidationError("Say whether the rule is the law or PBL's own rule.")
    lapse = payload.lapse_code.strip().upper()
    if lapse not in LAPSE_CODES:
        raise EligibilityValidationError("Say what a lapse does.")
    if basis == BASIS_STATUTORY and lapse not in STATUTORY_LAPSE_CODES:
        raise EligibilityValidationError("The law always stops the machine when it lapses: a statutory rule blocks, or says it is not required.")
    not_applicable = payload.not_applicable_code.strip().upper()
    if not_applicable not in NOT_APPLICABLE_CODES:
        raise EligibilityValidationError("Say whether 'not applicable' may be claimed.")
    if lapse == LAPSE_NOT_REQUIRED and not_applicable == NOT_APPLICABLE_ALLOWED:
        raise EligibilityValidationError("Nothing is required, so there is nothing to mark not applicable.")
    if payload.not_applicable_max_months is not None and not_applicable != NOT_APPLICABLE_ALLOWED:
        raise EligibilityValidationError("A limit on how long a mark runs needs 'not applicable' to be allowed.")
    if payload.renew_every_months is not None and not kind.is_examination:
        raise EligibilityValidationError(f"A {kind.kind_label.lower()} states its own end, so the rule sets no interval.")
    if kind.is_examination and lapse != LAPSE_NOT_REQUIRED and payload.renew_every_months is None:
        raise EligibilityValidationError(f"Give how often the {kind.kind_label.lower()} must be renewed, in months.")
    source = _required_text(payload.source, what="the rule's source: the Act, rule, form and notification, or PBL's decision and its date")
    return {
        "kind_code": kind_code,
        "kind_is_examination": kind.is_examination,
        "class_code": class_code,
        "type_code": type_code,
        "applies_when_code": applies_when,
        "jurisdiction_code": jurisdiction_code,
        "effective_from": payload.effective_from,
        "renew_every_months": payload.renew_every_months,
        "basis_code": basis,
        "lapse_code": lapse,
        "not_applicable_code": not_applicable,
        "not_applicable_max_months": payload.not_applicable_max_months,
        "source": source,
        "note": _clean(payload.note),
    }


def end_rule(db: Session, *, rule_public_id: str, payload: RuleEndInput, user_public_id: str | None) -> RuleActionResponse:
    """End a rule on its last day (Q7). Ending it again on the same day changes nothing."""
    with rollback_on_error(db):
        user = _require_user(user_public_id)
        _begin_write(db)
        row = repo.get_rule_row(db, public_id=rule_public_id)
        if row is None:
            raise EligibilityNotFoundError("No rule was found with that id.")
        if row["effective_to"] is not None:
            if row["effective_to"] == payload.effective_to:
                db.rollback()
                return RuleActionResponse(rule=_one_rule_response(db, row), replayed=True)
            raise EligibilityConflictError(f"This rule was already ended on {_long_date(row['effective_to'])}.")
        if payload.effective_to < row["effective_from"]:
            raise EligibilityValidationError(f"A rule cannot end before it starts, on {_long_date(row['effective_from'])}.")
        reason = _required_text(payload.reason, what="the reason for ending it")
        repo.end_rule(db, rule_id=row["id"], effective_to=payload.effective_to, reason=reason, user_public_id=user, at=_now())
        row = repo.get_rule_row(db, public_id=rule_public_id)
        event = _event(
            db,
            event_name=EVENT_RULE_ENDED,
            record_type=RECORD_TYPE_RULE,
            record_public_id=rule_public_id,
            user_public_id=user,
            status_before="IN_EFFECT",
            status_after="ENDED",
            reason=reason,
            payload=_rule_event_payload(row),
        )
        db.commit()
    return RuleActionResponse(rule=_one_rule_response(db, row), event=event)


