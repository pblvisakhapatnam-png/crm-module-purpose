"""Reading allocations (8A core): the site, finding machines, answers, and how an allocation is shown.

Design: docs/agent/slices/8a-core-equipment-allocation.md, sections 6.1, 6.2, 6.4, 6.10 and 6.13. Other modules
are read only through their services: the requirement (and, through it, its Work Order line) from Resource
Requirements, machines and kit from the Equipment Reference, answers from Eligibility. Nothing here writes.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any, Iterable
from uuid import UUID

from sqlalchemy.orm import Session

from app.modules.eligibility.ports import AllocatedAsset
from app.modules.eligibility.schemas import EligibilityCheckResponse, StoredDecision
from app.modules.eligibility.service import (
    EligibilityValidationError,
    evaluate_asset,
    get_stored_decisions,
    jurisdiction_for_state_text,
)
from app.modules.equipment_reference.service import (
    AllocationAsset,
    allocation_asset,
    kit_for_machine,
    machines_for_allocation,
)
from app.modules.resource_assignments import repository as repo
from app.modules.resource_assignments.contract import (
    COMPLIANCE_BLOCKED,
    COMPLIANCE_CLEAR,
    COMPLIANCE_SITE_UNKNOWN,
    COMPLIANCE_WARNING,
    DECISION_FOR_ASSIGNMENT,
    DECISION_FOR_KIT_LINE,
    KIT_LINE_LISTED,
    LEFT_OUT_COUNTED,
    SITE_CENTRAL_NOT_ANSWERED,
    SITE_NOT_RECORDED,
    SITE_STATE_NOT_RECOGNISED,
    STATUS_CODES,
    STATUS_HELD,
    WARNING_ANSWER_CHANGED,
    WARNING_BILLING_CYCLE_NOT_STATED,
    WARNING_KIT_DOES_NOT_FIT,
    WARNING_NO_LONGER_MATCHES,
    WARNING_OUTSIDE_CONTRACT,
    WARNING_OUTSIDE_REQUIREMENT,
    WARNING_SITE_CHANGED,
    WARNING_UNIT_NOT_REQUIRED,
)
from app.modules.resource_assignments.errors import AssignmentNotFoundError, AssignmentValidationError
from app.modules.resource_assignments.rules import (
    Asked,
    Days,
    busy_days,
    candidate_order,
    effective_end,
    first_uncovered_day,
    left_out_reason,
    most_in_use,
)
from app.modules.resource_assignments.schemas import (
    Answer,
    AnswerResult,
    AssetBrief,
    AssignmentLink,
    AssignmentResponse,
    Candidate,
    CandidatesResponse,
    CapabilityBrief,
    Conflict,
    KitLineResponse,
    KitOption,
    KitOptionsResponse,
    RequirementBrief,
    SiteFacts,
    TripResponse,
)
from app.modules.resource_requirements.schemas import ResourceRequirementResponse
from app.modules.resource_requirements.service import (
    ResourceRequirementNotFoundError,
    get_resource_requirement,
    requirement_planned_end,
)
from app.modules.work_orders.contract_period_rules import (
    CONTRACT_DATE_OUTSIDE_OUTCOMES,
    ContractGap,
    classify_date_against_contract,
    format_contract_date,
)
from app.shared import business_time

BLOCKING_ANSWERS = ("BLOCKED", "OVERRIDE_REQUIRED")
OUTCOME_WORDS = {
    "MISSING": "is missing",
    "COPY_MISSING": "has no copy attached",
    "RUN_OUT": "ran out",
    "RUNS_OUT_BEFORE_START": "runs out before the job starts",
    "RUNS_OUT_IN_PERIOD": "runs out during the job",
    "RUNS_OUT_SOON": "runs out within 15 days",
    "RETIRED": "is retired",
}


# --- The requirement --------------------------------------------------------------------------------------


def load_requirement(db: Session, public_id: UUID | str) -> ResourceRequirementResponse:
    try:
        return get_resource_requirement(db, UUID(str(public_id)))
    except ResourceRequirementNotFoundError as exc:
        raise AssignmentNotFoundError("Resource requirement not found.") from exc


def planned_end(requirement: ResourceRequirementResponse) -> date | None:
    return requirement_planned_end(requirement.required_to, requirement.line)


def asked_of(requirement: ResourceRequirementResponse) -> tuple[str, str | None, list[Asked]]:
    """The requirement's one item (WRR-001): its class, type and the capabilities asked for."""
    item = requirement.items[0]
    return (
        item.equipment_class_code,
        item.equipment_type_code,
        [Asked(cap.capability_code, cap.minimum_value, cap.choice_value) for cap in item.capabilities],
    )


def requirement_brief(requirement: ResourceRequirementResponse) -> RequirementBrief:
    item = requirement.items[0]
    return RequirementBrief(
        requirement_public_id=requirement.requirement_public_id,
        requirement_reference=requirement.requirement_reference,
        requirement_status_code=requirement.requirement_status_code,
        requirement_version=requirement.requirement_version,
        units_required=requirement.units_required,
        units_covered=requirement.units_covered,
        units_remaining=requirement.units_remaining,
        required_from=requirement.required_from,
        required_to=requirement.required_to,
        planned_end=planned_end(requirement),
        equipment_class_code=item.equipment_class_code,
        equipment_class_label=item.equipment_class_label,
        equipment_type_code=item.equipment_type_code,
        equipment_type_label=item.equipment_type_label,
        capabilities=[
            {
                "capability_code": cap.capability_code,
                "capability_label": cap.capability_label,
                "unit_symbol": cap.unit_symbol,
                "minimum_value": str(cap.minimum_value) if cap.minimum_value is not None else None,
                "choice_value": cap.choice_value,
            }
            for cap in item.capabilities
        ],
        work_order_status_code=requirement.line.work_order_status_code,
    )


# --- The site (design section 6.1) --------------------------------------------------------------------------


def site_facts(db: Session, requirement: ResourceRequirementResponse) -> SiteFacts:
    """The line's site: its state matched to a state or union territory, and whether it is a central-government
    site. What is missing is named, so the allocation is refused with it."""
    line_number = requirement.work_order_line_number
    site = requirement.line.site
    central = requirement.line.site_central_government
    if site is None:
        return SiteFacts(
            site_public_id=None,
            site_label=None,
            state_text=None,
            state_code=None,
            state_label=None,
            central_government_site=central,
            problem_code=SITE_NOT_RECORDED,
            problem_message=f"Record the site on line {line_number}'s details first.",
        )
    label = ", ".join(part for part in (site.address_line1, site.city) if part)
    state = jurisdiction_for_state_text(db, site.state)
    problem_code = problem_message = None
    if state is None:
        problem_code = SITE_STATE_NOT_RECOGNISED
        problem_message = (
            f"The site's state '{site.state or ''}' is not a state or union territory the platform knows. Correct the "
            "site address on the Account."
        )
    elif central is None:
        problem_code = SITE_CENTRAL_NOT_ANSWERED
        problem_message = (
            f"Say on line {line_number}'s details whether its site is a central-government site: a central public "
            "sector plant, a railway or metro, a major port, an oil field or a mine, including work there as a "
            "contractor."
        )
    return SiteFacts(
        site_public_id=site.public_id,
        site_label=label or None,
        state_text=site.state,
        state_code=state.jurisdiction_code if state else None,
        state_label=state.jurisdiction_label if state else None,
        central_government_site=central,
        problem_code=problem_code,
        problem_message=problem_message,
    )


def require_site(site: SiteFacts) -> tuple[str, bool]:
    if site.problem_message is not None or site.state_code is None or site.central_government_site is None:
        raise AssignmentValidationError(site.problem_message or "The site cannot be judged yet.")
    return site.state_code, site.central_government_site


# --- Assets and answers -------------------------------------------------------------------------------------


def _capability_brief(item: Any) -> CapabilityBrief:
    return CapabilityBrief(
        capability_code=item.capability_code,
        capability_label=item.capability_label,
        unit_symbol=item.unit_symbol,
        value=item.value,
        choice_value=item.choice_value,
        is_key=item.is_key,
    )


def asset_brief(asset: AllocationAsset) -> AssetBrief:
    key = asset.key_capability()
    return AssetBrief(
        asset_public_id=asset.asset_public_id,
        asset_reference=asset.asset_reference,
        asset_kind_code=asset.asset_kind_code,
        machine_number=asset.machine_number,
        serial_number=asset.serial_number,
        class_code=asset.class_code,
        class_label=asset.class_label,
        type_code=asset.type_code,
        type_label=asset.type_label,
        model_public_id=asset.model_public_id,
        model_label=asset.model_label,
        asset_status_code=asset.asset_status_code,
        asset_version=asset.asset_version,
        quantity=asset.quantity,
        tracking_code=asset.tracking_code,
        key_capability=_capability_brief(key) if key else None,
        capabilities=[_capability_brief(item) for item in asset.capabilities],
        flag_codes=list(asset.flag_codes),
    )


def answer_from_check(check: EligibilityCheckResponse, *, decision_public_id: str | None = None) -> Answer:
    return Answer(
        decision_public_id=decision_public_id,
        overall_code=check.overall_code,
        valid_until=check.valid_until,
        evaluated_on=check.evaluated_on,
        site_state_code=check.site_state_code,
        site_state_label=check.site_state_label,
        central_government_site=check.central_government_site,
        period_from=check.period_from,
        period_to=check.period_to,
        results=[
            AnswerResult(
                asset_public_id=result.asset_public_id,
                asset_reference=result.asset_reference,
                kind_code=result.kind_code,
                kind_label=result.kind_label,
                outcome_code=result.outcome_code,
                effect_code=result.effect_code,
                cover_ends_on=result.cover_ends_on,
            )
            for result in check.results
        ],
    )


def answer_from_stored(stored: StoredDecision | None) -> Answer | None:
    if stored is None:
        return None
    return Answer(
        decision_public_id=stored.decision_public_id,
        overall_code=stored.overall_code,
        valid_until=stored.valid_until,
        evaluated_on=stored.evaluated_on,
        site_state_code=stored.site_state_code,
        site_state_label=stored.site_state_label,
        central_government_site=stored.central_government_site,
        period_from=stored.period_from,
        period_to=stored.period_to,
        results=[AnswerResult(**result.model_dump()) for result in stored.results],
    )


def describe_problems(answer: Answer, *, asset_public_id: str) -> str:
    """The results that stop or warn, in words: "Insurance runs out during the job (cover ends 5 October 2026)".
    A result about a fitted part names it ("on EQ-000124", the crane's carrier)."""
    parts: list[str] = []
    for result in answer.results:
        if result.effect_code == "NONE":
            continue
        subject = result.kind_label or "The asset"
        words = OUTCOME_WORDS.get(result.outcome_code, result.outcome_code.lower().replace("_", " "))
        where = f" on {result.asset_reference}" if result.asset_public_id != asset_public_id else ""
        until = f" (cover ends {format_contract_date(result.cover_ends_on)})" if result.cover_ends_on else ""
        approval = ", which needs an approval that cannot be given yet" if result.effect_code == "OVERRIDE" else ""
        parts.append(f"{subject}{where} {words}{until}{approval}")
    return "; ".join(parts) if parts else "no certificate is in order"


def today_answer(
    db: Session, *, asset_public_id: str, site: SiteFacts, period_from: date, period_to: date | None
) -> Answer | None:
    """Today's answer, worked out now and never stored, or None when it cannot be asked: the site cannot be judged,
    the period is over, or Eligibility refuses the asset."""
    if site.problem_code is not None or site.state_code is None or site.central_government_site is None:
        return None
    if period_to is not None and period_to < business_time.india_today():
        return None
    try:
        check = evaluate_asset(
            db,
            asset_public_id=asset_public_id,
            state_code=site.state_code,
            central_government_site=site.central_government_site,
            period_from=period_from,
            period_to=period_to,
        )
    except EligibilityValidationError:
        return None
    return answer_from_check(check)


def _compliance(answers: Iterable[Answer | None]) -> str:
    codes = {answer.overall_code for answer in answers if answer is not None}
    if codes & set(BLOCKING_ANSWERS):
        return COMPLIANCE_BLOCKED
    if "WARNING" in codes:
        return COMPLIANCE_WARNING
    return COMPLIANCE_CLEAR


# --- Conflicts ----------------------------------------------------------------------------------------------


def conflict_of_assignment(row: dict[str, Any]) -> Conflict:
    days = busy_days(row["planned_from"], row["planned_to"], row["ended_on"])
    return Conflict(
        assignment_public_id=str(row["assignment_public_id"]),
        assignment_reference=row["assignment_reference"],
        work_order_code=row["work_order_code"],
        unit_number=int(row["unit_number"]),
        assignment_status_code=row["assignment_status_code"],
        busy_from=days.start if days else row["planned_from"],
        busy_to=days.end if days else row["planned_from"],
    )


def conflict_of_kit_line(row: dict[str, Any], assignments: dict[int, dict[str, Any]]) -> Conflict:
    assignment = assignments.get(int(row["resource_assignment_id"]), {})
    return Conflict(
        assignment_public_id=str(row["assignment_public_id"]),
        assignment_reference=row["assignment_reference"],
        work_order_code=row["work_order_code"],
        unit_number=int(assignment.get("unit_number", 0)),
        assignment_status_code=assignment.get("assignment_status_code", STATUS_HELD),
        busy_from=row["busy_from"],
        busy_to=row["busy_to"],
    )


def describe_conflict(asset_reference: str, conflict: Conflict) -> str:
    until = f" to {format_contract_date(conflict.busy_to)}" if conflict.busy_to else " with no end date"
    return (
        f"{asset_reference} is allocated to {conflict.work_order_code} ({conflict.assignment_reference}) from "
        f"{format_contract_date(conflict.busy_from)}{until}."
    )


# --- An allocation, shown -----------------------------------------------------------------------------------


@dataclass
class _Context:
    """What several allocations on one page share, each read once."""

    requirements: dict[str, ResourceRequirementResponse]
    sites: dict[str, SiteFacts]
    assets: dict[str, AllocationAsset | None]
    kit_fits: dict[str, set[str]]


def _requirement(db: Session, ctx: _Context, public_id: str) -> ResourceRequirementResponse:
    if public_id not in ctx.requirements:
        ctx.requirements[public_id] = load_requirement(db, public_id)
        ctx.sites[public_id] = site_facts(db, ctx.requirements[public_id])
    return ctx.requirements[public_id]


def _asset(db: Session, ctx: _Context, public_id: str) -> AllocationAsset | None:
    if public_id not in ctx.assets:
        ctx.assets[public_id] = allocation_asset(db, public_id)
    return ctx.assets[public_id]


def _link(row: dict[str, Any] | None, ctx: _Context) -> AssignmentLink | None:
    if row is None:
        return None
    machine = ctx.assets.get(str(row["equipment_asset_public_id"]))
    return AssignmentLink(
        assignment_public_id=str(row["assignment_public_id"]),
        assignment_reference=row["assignment_reference"],
        asset_reference=machine.asset_reference if machine else "",
        machine_number=row["allocated_machine_number"],
        planned_from=row["planned_from"],
        effective_to=effective_end(row["planned_to"], row["ended_on"]),
    )


def _outside_contract(days: Days, facts: Any) -> bool:
    """Whether any day of an allocation is outside its Work Order's contract (design section 6.13): its first or last
    day, as Slice 7D Part 3's rule classifies them, a gap between extensions anywhere inside it - its ends may both
    be inside the contract (8A-R7-002) - or an open end under a fixed contract end."""
    gaps = tuple(ContractGap(gap.first_day, gap.last_day, gap.extension_sequence_no) for gap in facts.contract_gaps)
    ends = [value for value in (days.start, days.end) if value is not None]
    if any(
        classify_date_against_contract(
            value, contract_start=facts.contract_start_date, contract_end=facts.contract_end_date, gaps=gaps
        )
        in CONTRACT_DATE_OUTSIDE_OUTCOMES
        for value in ends
    ):
        return True
    if days.end is None and facts.contract_end_date is not None:
        return True
    return any(days.overlaps(Days(gap.first_day, gap.last_day)) for gap in gaps)


def _warnings(
    row: dict[str, Any],
    *,
    requirement: ResourceRequirementResponse,
    site: SiteFacts,
    machine: AllocationAsset | None,
    decision: Answer | None,
    today: Answer | None,
    kit_misfit: bool,
) -> list[str]:
    warnings: list[str] = []
    if decision is not None and site.problem_code is None and (
        decision.site_state_code != site.state_code or decision.central_government_site != site.central_government_site
    ):
        warnings.append(WARNING_SITE_CHANGED)
    end = effective_end(row["planned_to"], row["ended_on"])
    bound = planned_end(requirement)
    if row["planned_from"] < requirement.required_from or (bound is not None and (end is None or end > bound)):
        warnings.append(WARNING_OUTSIDE_REQUIREMENT)
    class_code, type_code, asked = asked_of(requirement)
    if machine is None or left_out_reason(machine, class_code=class_code, type_code=type_code, asked=asked) is not None:
        warnings.append(WARNING_NO_LONGER_MATCHES)
    if int(row["unit_number"]) > requirement.units_required:
        warnings.append(WARNING_UNIT_NOT_REQUIRED)
    if _outside_contract(Days(row["planned_from"], end), requirement.line):
        warnings.append(WARNING_OUTSIDE_CONTRACT)
    if row["billing_cycle_code"] is None:
        warnings.append(WARNING_BILLING_CYCLE_NOT_STATED)
    if kit_misfit:
        warnings.append(WARNING_KIT_DOES_NOT_FIT)
    if today is not None and decision is not None and today.overall_code != decision.overall_code:
        warnings.append(WARNING_ANSWER_CHANGED)
    return warnings


def build_assignments(db: Session, rows: list[dict[str, Any]], *, detail: bool) -> list[AssignmentResponse]:
    """One serializer for the list and the page. Both judge a held allocation by its machine and its listed kit -
    today's answers, and whether each piece still fits (8A-R1-005); the page (`detail`) adds the trips and kit lines,
    with each piece's stored and today's answers."""
    if not rows:
        return []
    ctx = _Context({}, {}, {}, {})
    ids = [int(row["id"]) for row in rows]
    replaced = {int(item["id"]): item for item in repo.list_assignment_rows_by_ids(
        db, ids=[int(row["replaces_assignment_id"]) for row in rows if row["replaces_assignment_id"]]
    )}
    replacers = {int(item["replaces_assignment_id"]): item for item in repo.list_replacer_rows(db, replaced_ids=ids)}
    kit_rows: dict[int, list[dict[str, Any]]] = {}
    for item in repo.list_kit_rows(db, assignment_ids=ids):
        kit_rows.setdefault(int(item["resource_assignment_id"]), []).append(item)
    trips: dict[int, list[dict[str, Any]]] = {}
    if detail:
        for item in repo.list_trip_rows(db, assignment_ids=ids):
            trips.setdefault(int(item["resource_assignment_id"]), []).append(item)
    decision_ids = [str(row["decision_public_id"]) for row in rows]
    if detail:
        decision_ids += [str(item["decision_public_id"]) for items in kit_rows.values() for item in items]
    kit_today: dict[int, Answer | None] = {}
    decisions = get_stored_decisions(db, decision_ids)
    for row in list(rows) + list(replaced.values()) + list(replacers.values()):
        _asset(db, ctx, str(row["equipment_asset_public_id"]))

    today = business_time.india_today()
    responses: list[AssignmentResponse] = []
    for row in rows:
        requirement = _requirement(db, ctx, str(row["resource_requirement_public_id"]))
        site = ctx.sites[str(row["resource_requirement_public_id"])]
        machine = ctx.assets[str(row["equipment_asset_public_id"])]
        end = effective_end(row["planned_to"], row["ended_on"])
        held = row["assignment_status_code"] == STATUS_HELD
        decision = answer_from_stored(decisions.get(str(row["decision_public_id"])))
        machine_today = (
            today_answer(
                db, asset_public_id=str(row["equipment_asset_public_id"]), site=site, period_from=row["planned_from"],
                period_to=end,
            )
            if held
            else None
        )
        listed = [item for item in kit_rows.get(int(row["id"]), []) if item["line_status_code"] == KIT_LINE_LISTED]
        fits = _kit_fits(db, ctx, str(row["equipment_asset_public_id"])) if listed or detail else set()
        kit_misfit = held and any(str(item["equipment_asset_public_id"]) not in fits for item in listed)
        for item in listed:
            kit_today[int(item["id"])] = (
                today_answer(
                    db, asset_public_id=str(item["equipment_asset_public_id"]), site=site,
                    period_from=item["busy_from"], period_to=item["busy_to"],
                )
                if held and not (item["busy_to"] is not None and item["busy_to"] < item["busy_from"])
                else None
            )
        kit_answers = [kit_today[int(item["id"])] for item in listed]
        trip_responses: list[TripResponse] = []
        if detail:
            lines_by_trip: dict[int, list[KitLineResponse]] = {}
            for item in kit_rows.get(int(row["id"]), []):
                piece = _asset(db, ctx, str(item["equipment_asset_public_id"]))
                fits_machine = str(item["equipment_asset_public_id"]) in fits
                piece_today = kit_today.get(int(item["id"]))
                lines_by_trip.setdefault(int(item["trip_number"]), []).append(
                    KitLineResponse(
                        kit_line_public_id=str(item["kit_line_public_id"]),
                        trip_number=int(item["trip_number"]),
                        piece=asset_brief(piece) if piece else None,
                        piece_public_id=str(item["equipment_asset_public_id"]),
                        quantity=int(item["quantity"]),
                        line_status_code=item["line_status_code"],
                        removed_by=item["removed_by"],
                        removed_by_display_name=item["removed_by_display_name"],
                        removed_at=item["removed_at"],
                        busy_from=item["busy_from"],
                        busy_to=item["busy_to"],
                        fits_machine=fits_machine,
                        decision=answer_from_stored(decisions.get(str(item["decision_public_id"]))),
                        today=piece_today,
                    )
                )
            for trip in trips.get(int(row["id"]), []):
                trip_responses.append(
                    TripResponse(
                        trip_public_id=str(trip["trip_public_id"]),
                        trip_number=int(trip["trip_number"]),
                        goes_on=trip["goes_on"] or row["planned_from"],
                        note=trip["note"],
                        kit=lines_by_trip.get(int(trip["trip_number"]), []),
                    )
                )
        compliance: str | None = None
        if held and not (end is not None and end < today):
            compliance = (
                COMPLIANCE_SITE_UNKNOWN if site.problem_code is not None else _compliance([machine_today, *kit_answers])
            )
        responses.append(
            AssignmentResponse(
                assignment_public_id=str(row["assignment_public_id"]),
                assignment_reference=row["assignment_reference"],
                assignment_status_code=row["assignment_status_code"],
                requirement=requirement_brief(requirement),
                unit_number=int(row["unit_number"]),
                work_order_public_id=row["work_order_public_id"],
                work_order_code=row["work_order_code"],
                work_order_line_public_id=row["work_order_line_public_id"],
                work_order_line_number=int(row["work_order_line_number"]),
                source_offer_line_public_id=row["source_offer_line_public_id"],
                machine=asset_brief(machine) if machine else None,
                allocated_machine_number=row["allocated_machine_number"],
                allocated_class_code=row["allocated_class_code"],
                allocated_type_code=row["allocated_type_code"],
                allocated_model_public_id=row["allocated_model_public_id"],
                allocated_asset_version=int(row["allocated_asset_version"]),
                planned_from=row["planned_from"],
                planned_to=row["planned_to"],
                ended_on=row["ended_on"],
                effective_to=end,
                billing_cycle_code=row["billing_cycle_code"],
                billing_cycle_set_by=row["billing_cycle_set_by"],
                billing_cycle_set_by_display_name=row["billing_cycle_set_by_display_name"],
                billing_cycle_set_at=row["billing_cycle_set_at"],
                decision=decision,
                today=machine_today,
                compliance_state_code=compliance,
                warnings=(
                    _warnings(
                        row, requirement=requirement, site=site, machine=machine, decision=decision,
                        today=machine_today, kit_misfit=kit_misfit,
                    )
                    if held
                    else []
                ),
                site=site,
                replaces=_link(replaced.get(int(row["replaces_assignment_id"])) if row["replaces_assignment_id"] else None, ctx),
                replaced_by=_link(replacers.get(int(row["id"])), ctx),
                end_reason_code=row["end_reason_code"],
                end_note=row["end_note"],
                ended_by=row["ended_by"],
                ended_by_display_name=row["ended_by_display_name"],
                ended_at=row["ended_at"],
                trips=trip_responses,
                kit_pieces_listed=sum(int(item["quantity"]) for item in listed),
                notes=row["notes"],
                assignment_version=int(row["assignment_version"]),
                created_by=row["created_by"],
                created_by_display_name=row["created_by_display_name"],
                created_at=row["created_at"],
                updated_by=row["updated_by"],
                updated_by_display_name=row["updated_by_display_name"],
                updated_at=row["updated_at"],
            )
        )
    return responses


def _kit_fits(db: Session, ctx: _Context, machine_public_id: str) -> set[str]:
    if machine_public_id not in ctx.kit_fits:
        pieces = kit_for_machine(db, machine_public_id)
        for piece in pieces:
            ctx.assets.setdefault(piece.asset_public_id, piece)
        ctx.kit_fits[machine_public_id] = {piece.asset_public_id for piece in pieces}
    return ctx.kit_fits[machine_public_id]


def _day_recorded(value: datetime) -> date:
    return business_time.india_date(value)


def held_for_reminders(db: Session, *, today: date) -> list[AllocatedAsset]:
    """What Eligibility's reminders judge (ELG-2, through `eligibility.ports.AllocationSource`): every held allocation
    whose last day has not passed - its machine, over its days - and each piece listed on its trips with days left, over
    the kit line's days, each with the site as it now is. The same machine, days and site the allocation's own "today's
    answer" uses. A read: nothing is written and no lock is taken."""
    rows = repo.list_held_rows_for_reminders(db, today=today)
    if not rows:
        return []
    ctx = _Context({}, {}, {}, {})
    kit_rows: dict[int, list[dict[str, Any]]] = {}
    for item in repo.list_kit_rows(db, assignment_ids=[int(row["id"]) for row in rows]):
        kit_rows.setdefault(int(item["resource_assignment_id"]), []).append(item)
    found: list[AllocatedAsset] = []
    for row in rows:
        _requirement(db, ctx, str(row["resource_requirement_public_id"]))
        site = ctx.sites[str(row["resource_requirement_public_id"])]
        shared = {
            "assignment_public_id": str(row["assignment_public_id"]),
            "assignment_reference": row["assignment_reference"],
            "work_order_public_id": str(row["work_order_public_id"]),
            "work_order_code": row["work_order_code"],
            "work_order_line_number": int(row["work_order_line_number"]),
            "unit_number": int(row["unit_number"]),
            "site_state_code": site.state_code if site.problem_code is None else None,
            "central_government_site": site.central_government_site if site.problem_code is None else None,
            "site_label": site.site_label,
            "site_problem_code": site.problem_code,
        }
        found.append(
            AllocatedAsset(
                subject_type=DECISION_FOR_ASSIGNMENT,
                subject_public_id=str(row["assignment_public_id"]),
                trip_number=None,
                asset_public_id=str(row["equipment_asset_public_id"]),
                period_from=row["planned_from"],
                period_to=row["planned_to"],
                began_on=_day_recorded(row["created_at"]),
                **shared,
            )
        )
        for item in kit_rows.get(int(row["id"]), []):
            if item["line_status_code"] != KIT_LINE_LISTED:
                continue
            # A line cut off by its allocation ending early has no days, and one whose days are over is history.
            if item["busy_to"] is not None and (item["busy_to"] < item["busy_from"] or item["busy_to"] < today):
                continue
            found.append(
                AllocatedAsset(
                    subject_type=DECISION_FOR_KIT_LINE,
                    subject_public_id=str(item["kit_line_public_id"]),
                    trip_number=int(item["trip_number"]),
                    asset_public_id=str(item["equipment_asset_public_id"]),
                    period_from=item["busy_from"],
                    period_to=item["busy_to"],
                    began_on=_day_recorded(item["created_at"]),
                    **shared,
                )
            )
    return found


def get_assignment(db: Session, public_id: UUID | str) -> AssignmentResponse:
    row = repo.get_assignment_row(db, public_id=str(public_id))
    if row is None:
        raise AssignmentNotFoundError("Allocation not found.")
    return build_assignments(db, [row], detail=True)[0]


def list_assignments(
    db: Session,
    *,
    work_order_public_id: UUID | None = None,
    requirement_public_id: UUID | None = None,
    machine_public_id: UUID | None = None,
    status_code: str | None = None,
    starts_from: date | None = None,
    starts_to: date | None = None,
    limit: int = 100,
    offset: int = 0,
    after: UUID | None = None,
) -> list[AssignmentResponse]:
    """Allocations in the order they were recorded - every allocation of a Work Order is its history (FRS 2.6.1) -
    and with `after`, only those recorded after that one: the next page (8A-FB-004)."""
    status = (status_code or "").strip().upper() or None
    if status is not None and status not in STATUS_CODES:
        raise AssignmentValidationError("Status must be Held, Replaced or Freed.")
    if after is not None and repo.get_assignment_row(db, public_id=str(after)) is None:
        raise AssignmentValidationError("There is no such allocation to list after.")
    rows = repo.list_assignment_rows(
        db,
        work_order_public_id=str(work_order_public_id) if work_order_public_id else None,
        requirement_public_id=str(requirement_public_id) if requirement_public_id else None,
        machine_public_id=str(machine_public_id) if machine_public_id else None,
        status_code=status,
        starts_from=starts_from,
        starts_to=starts_to,
        limit=limit,
        offset=offset,
        after_public_id=str(after) if after is not None else None,
    )
    return build_assignments(db, rows, detail=False)


# --- Finding machines (design section 6.2) -----------------------------------------------------------------


def check_period(requirement: ResourceRequirementResponse, planned_from: date, planned_to: date | None) -> date | None:
    """The period must sit inside the requirement's: from its start to its end, else its line's, else the
    contract's fixed end. An empty end means until the requirement ends, which is what is stored. Returns the end
    to store."""
    bound = planned_end(requirement)
    reference = requirement.requirement_reference
    if planned_from < requirement.required_from:
        raise AssignmentValidationError(
            f"This allocation starts on {format_contract_date(planned_from)}, before {reference} starts on "
            f"{format_contract_date(requirement.required_from)}."
        )
    end = planned_to if planned_to is not None else bound
    if end is not None and end < planned_from:
        raise AssignmentValidationError(
            f"This allocation cannot end on {format_contract_date(end)}, before it starts on "
            f"{format_contract_date(planned_from)}."
        )
    if bound is not None and end is not None and end > bound:
        raise AssignmentValidationError(
            f"This allocation ends on {format_contract_date(end)}, after {reference} ends on {format_contract_date(bound)}."
        )
    return end


def held_days_by_unit(db: Session, requirement_public_id: str, *, excluding: Iterable[int] = ()) -> dict[int, list[Days]]:
    """The days each unit has had a machine, from every allocation - held, replaced or freed."""
    skip = set(excluding)
    held: dict[int, list[Days]] = {}
    for row in repo.list_rows_for_requirements(db, requirement_public_ids=[requirement_public_id]):
        if int(row["id"]) in skip:
            continue
        days = busy_days(row["planned_from"], row["planned_to"], row["ended_on"])
        if days is not None:
            held.setdefault(int(row["unit_number"]), []).append(days)
    return held


def find_candidates(
    db: Session,
    *,
    requirement_public_id: UUID,
    unit_number: int,
    period_from: date | None = None,
    period_to: date | None = None,
    replacing_assignment_public_id: UUID | None = None,
) -> CandidatesResponse:
    requirement = load_requirement(db, requirement_public_id)
    if requirement.requirement_status_code == "CANCELLED":
        raise AssignmentValidationError(f"{requirement.requirement_reference} is cancelled, so no machine can be allocated to it.")
    if not 1 <= unit_number <= requirement.units_required:
        raise AssignmentValidationError(
            f"{requirement.requirement_reference} asks for {requirement.units_required} machine(s); unit {unit_number} is not one of them."
        )
    excluding: list[int] = []
    if replacing_assignment_public_id is not None:
        replacing = repo.get_assignment_row(db, public_id=str(replacing_assignment_public_id))
        if replacing is None or str(replacing["resource_requirement_public_id"]) != str(requirement.requirement_public_id):
            raise AssignmentNotFoundError("Allocation not found on this requirement.")
        # A replacement fills the replaced allocation's own unit, and only a held allocation is replaced (8A-R4-002).
        if int(replacing["unit_number"]) != unit_number:
            raise AssignmentValidationError(
                f"{replacing['assignment_reference']} is on unit {replacing['unit_number']}, not unit {unit_number}."
            )
        if replacing["assignment_status_code"] != STATUS_HELD:
            raise AssignmentValidationError(
                f"{replacing['assignment_reference']} is no longer held, so it cannot be replaced."
            )
        excluding.append(int(replacing["id"]))
        if period_from is None:
            # A replacement takes over the replaced allocation's own days (8A-R3-003), to its end. Before its first
            # day, from that day. Once started (its first day on or before today, the test the server applies), the
            # allocation keeps its first day (owner, 1 October 2026): from today, or its last day if that has passed,
            # and never earlier than the day after its first.
            old_end = effective_end(replacing["planned_to"], replacing["ended_on"])
            today = business_time.india_today()
            if replacing["planned_from"] <= today:
                latest = today if old_end is None else min(today, old_end)
                period_from = max(latest, replacing["planned_from"] + timedelta(days=1))
            else:
                period_from = replacing["planned_from"]
            if period_to is None:
                period_to = old_end
    bound = planned_end(requirement)
    start = period_from or first_uncovered_day(
        held_days_by_unit(db, str(requirement.requirement_public_id), excluding=excluding).get(unit_number, []),
        requirement.required_from,
        bound,
    ) or requirement.required_from
    end = check_period(requirement, start, period_to)
    site = site_facts(db, requirement)
    unit_conflicts = [
        conflict_of_assignment(row)
        for row in repo.list_unit_overlaps(
            db, requirement_public_id=str(requirement.requirement_public_id), unit_number=unit_number, start=start,
            end=end, excluding=excluding,
        )
    ]
    class_code, type_code, asked = asked_of(requirement)
    left_out = {code: 0 for code in LEFT_OUT_COUNTED}
    fitting: list[AllocationAsset] = []
    for machine in machines_for_allocation(db, class_code=class_code):
        reason = left_out_reason(machine, class_code=class_code, type_code=type_code, asked=asked)
        if reason is None:
            fitting.append(machine)
        elif reason in left_out:
            left_out[reason] += 1
    busy: dict[str, list[Conflict]] = {}
    for row in repo.list_machines_overlaps(
        db, machine_public_ids=[machine.asset_public_id for machine in fitting], start=start, end=end
    ):
        busy.setdefault(str(row["equipment_asset_public_id"]), []).append(conflict_of_assignment(row))
    candidates: list[Candidate] = []
    for machine in fitting:
        conflicts = busy.get(machine.asset_public_id, [])
        answer = (
            None
            if conflicts
            else today_answer(db, asset_public_id=machine.asset_public_id, site=site, period_from=start, period_to=end)
        )
        candidates.append(Candidate(machine=asset_brief(machine), available=not conflicts, conflicts=conflicts, answer=answer))
    candidates.sort(
        key=lambda item: candidate_order(
            available=item.available,
            overall_code=item.answer.overall_code if item.answer else None,
            key_value=item.machine.key_capability.value if item.machine.key_capability else None,
            machine_number=item.machine.machine_number,
        )
    )
    return CandidatesResponse(
        requirement=requirement_brief(requirement),
        unit_number=unit_number,
        period_from=start,
        period_to=end,
        site=site,
        unit_conflicts=unit_conflicts,
        candidates=candidates,
        left_out=left_out,
    )


# --- The kit going to site (design section 6.10) ------------------------------------------------------------


def kit_window(row: dict[str, Any], trip: dict[str, Any]) -> Days:
    """The days a trip's kit is busy: from the trip's day (trip 1: the allocation's first) to the allocation's end.
    A trip after the allocation's last day - one ended early by replacing or freeing it - has none: refused, never
    an inverted range (8A-R1-004)."""
    start = trip["goes_on"] or row["planned_from"]
    end = effective_end(row["planned_to"], row["ended_on"])
    if end is not None and end < start:
        raise AssignmentValidationError(
            f"Trip {trip['trip_number']} goes on {format_contract_date(start)}, after {row['assignment_reference']} ends: "
            "no kit can be listed on it."
        )
    return Days(start, end)


def piece_availability(
    db: Session, pieces: list[AllocationAsset], window: Days, *, excluding: list[int] = ()
) -> dict[str, tuple[int, list[Conflict]]]:
    """Each piece's free quantity over the window, and the listed lines taking it: a piece tracked one by one is
    free (1) or not (0); a counted set has its quantity less the most listed on any one day."""
    overlapping = repo.list_listed_kit_overlaps(
        db, piece_public_ids=[piece.asset_public_id for piece in pieces], start=window.start, end=window.end,
        excluding=list(excluding),
    )
    assignments = {
        int(row["id"]): row
        for row in repo.list_assignment_rows_by_ids(db, ids=sorted({int(row["resource_assignment_id"]) for row in overlapping}))
    }
    by_piece: dict[str, list[dict[str, Any]]] = {}
    for row in overlapping:
        by_piece.setdefault(str(row["equipment_asset_public_id"]), []).append(row)
    result: dict[str, tuple[int, list[Conflict]]] = {}
    for piece in pieces:
        lines = by_piece.get(piece.asset_public_id, [])
        conflicts = [conflict_of_kit_line(row, assignments) for row in lines]
        in_use = most_in_use(
            ((Days(row["busy_from"], row["busy_to"]), int(row["quantity"])) for row in lines), window
        )
        result[piece.asset_public_id] = (max(piece.quantity - in_use, 0), conflicts)
    return result


def kit_options(db: Session, *, assignment_public_id: UUID, trip_number: int) -> KitOptionsResponse:
    row = repo.get_assignment_row(db, public_id=str(assignment_public_id))
    if row is None:
        raise AssignmentNotFoundError("Allocation not found.")
    if row["assignment_status_code"] != STATUS_HELD:
        raise AssignmentValidationError(f"{row['assignment_reference']} has ended, so no kit can be added to it.")
    trip = next((item for item in repo.list_trip_rows(db, assignment_ids=[int(row["id"])]) if int(item["trip_number"]) == trip_number), None)
    if trip is None:
        raise AssignmentNotFoundError(f"Trip (Own Load) {trip_number} not found on {row['assignment_reference']}.")
    window = kit_window(row, trip)
    machine = allocation_asset(db, str(row["equipment_asset_public_id"]))
    pieces = kit_for_machine(db, str(row["equipment_asset_public_id"]))
    site = site_facts(db, load_requirement(db, str(row["resource_requirement_public_id"])))
    availability = piece_availability(db, pieces, window)
    options: list[KitOption] = []
    for piece in pieces:
        free, conflicts = availability[piece.asset_public_id]
        options.append(
            KitOption(
                piece=asset_brief(piece),
                available=free > 0,
                quantity_free=free,
                conflicts=conflicts,
                answer=(
                    today_answer(db, asset_public_id=piece.asset_public_id, site=site, period_from=window.start, period_to=window.end)
                    if free > 0
                    else None
                ),
            )
        )
    options.sort(key=lambda item: (item.piece.class_label, item.piece.model_label or "", item.piece.asset_reference))
    return KitOptionsResponse(
        assignment_public_id=str(row["assignment_public_id"]),
        assignment_version=int(row["assignment_version"]),
        trip_number=trip_number,
        window_from=window.start,
        window_to=window.end,
        machine_has_model=bool(machine and machine.model_public_id),
        pieces=options,
    )
