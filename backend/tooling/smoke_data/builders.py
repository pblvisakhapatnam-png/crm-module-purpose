from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import text

from app.core.database import SessionLocal
from app.modules.accounts import service as accounts_service
from app.modules.accounts.schemas import (
    AccountAddressCreate,
    AccountCreate,
    AccountGstinCreate,
    AccountTaxProfileUpsert,
)
from app.modules.commercial_offers import service as offers_service
from app.modules.commercial_offers.schemas import (
    CommercialOfferCreate,
    CommercialOfferCreditReviewCreate,
    CommercialOfferCustomerResponseCreate,
    CommercialOfferLineCreate,
    CommercialOfferPricingEvidenceBasisSelection,
    CommercialOfferPricingEvidenceCreate,
    CommercialOfferQuoteDocumentApproveRequest,
    CommercialOfferRelatedOfferCreate,
    CommercialOfferSubmissionEvidenceCreate,
    CommercialOfferTcClauseAttachRecommendedRequest,
    CommercialOfferVersionCreate,
)
from app.modules.documents import service as documents_service
from app.modules.holiday_calendar import service as holiday_calendar_service
from app.modules.holiday_calendar.schemas import HolidayCalendarHolidayInput, HolidayCalendarYearInput
from app.modules.identity.repository import get_user_with_roles_by_username
from app.modules.identity.service import to_auth_user
from app.modules.interactions import service as interactions_service
from app.modules.interactions.schemas import InteractionCreate
from app.modules.leads import service as leads_service
from app.modules.leads.schemas import (
    LeadActivityCreate,
    LeadConversionCreate,
    LeadCreate,
    LeadQualificationDecision,
)
from app.modules.opportunities import service as opportunities_service
from app.modules.opportunities.schemas import (
    OpportunityAccountRepairRequest,
    OpportunityCreate,
)
# 8A core: loaded for its registration. Resource Requirements reads a requirement's coverage, and frees its machines
# when it is cancelled, through the port this module registers when imported; with none registered it fails closed.
# The API loads it through app.main; the harness runs without app.main, so it loads it here.
from app.modules.resource_assignments import service as _resource_assignments_service  # noqa: F401
from app.modules.resource_requirements import service as resource_requirements_service
from app.modules.resource_requirements.schemas import (
    ResourceRequirementCapabilityInput,
    ResourceRequirementCreate,
    ResourceRequirementItemInput,
)
from app.modules.work_orders import service as work_orders_service
from app.modules.work_orders.schemas import (
    WorkOrderContractExtensionCreate,
    WorkOrderContractPeriodUpdate,
    WorkOrderAmendmentCreate,
    WorkOrderAmendmentDecision,
    WorkOrderAmendmentLineCreate,
    WorkOrderCreateFromCommercialOffer,
    WorkOrderHolidayChangeInput,
    WorkOrderHolidayListUpdate,
    WorkOrderLineBillingTermsPeriodCreate,
    WorkOrderLineDetailUpdate,
)
from app.shared import business_time

from .manifest import data_tag

# Every builder function opens its own short-lived session and lets the service
# function commit, mirroring how each HTTP request gets its own request-scoped
# session in the real routes. This is deliberate: it keeps each step's success/
# failure isolated and matches production request semantics instead of inventing
# a third session-lifetime pattern.


def _now() -> datetime:
    return datetime.now(timezone.utc)


class _Unset:
    """Distinguishes "argument not supplied" from "supplied as None".

    Needed because an offer line with NO rate is a real, reachable application state - Slice 4E
    makes rate_amount optional on an ACTIVE line - and the UAT dataset must produce one so the
    quotation renders "Not fully priced" rather than a partial sum presented as a total. Without
    this sentinel an explicit rate_amount=None would be indistinguishable from the default and
    silently priced, which is precisely the defect Slice 9E was corrected for."""

    def __repr__(self) -> str:  # pragma: no cover - debugging aid only
        return "<unset>"


UNSET = _Unset()


def create_account(
    *,
    run_id: str,
    actor_public_id: str,
    suffix: str,
    account_name: str | None = None,
    legal_name: str | None = None,
    segment: str | None = None,
    industry: str | None = None,
) -> dict[str, Any]:
    """Every argument after `suffix` is optional and defaults to the original behaviour, so the
    regression scenarios that predate the UAT data pack are unchanged.

    `account_name`, when given, is used VERBATIM - it is not prefixed with `data_tag(run_id)`.
    That is deliberate rather than an oversight. The UAT datasets need plausible customer names
    of realistic length (one of them deliberately near the 255-character legal-name limit), and
    a `TE1-SMOKE-te1-xxxxxxxx ` prefix in front of every one would both destroy that realism and
    consume characters the long-name case exists to test. Those scenarios carry their own visible
    `UAT-` marker instead, and the run id still reaches the row through `source_remarks` below,
    so a seeded record remains identifiable both on screen and in the database."""
    with SessionLocal() as db:
        payload = AccountCreate(
            account_name=account_name or f"{data_tag(run_id)} Account {suffix}",
            legal_name=legal_name,
            account_status_code="QUALIFIED_PROSPECT",
            qualification_source="manual",
            segment=segment or "Smoke Test",
            industry=industry or "Equipment Hiring",
            source_remarks=f"Created by the TE-1 smoke-data harness, run {run_id}.",
        )
        result = accounts_service.create_account(db, payload=payload, current_user_public_id=actor_public_id)
        return {
            "public_id": str(result.account.public_id),
            "account_name": result.account.account_name,
        }


def create_account_linked_opportunity(
    *,
    run_id: str,
    actor_public_id: str,
    suffix: str,
    account_name: str | None = None,
    legal_name: str | None = None,
    segment: str | None = None,
    industry: str | None = None,
    opportunity_name: str | None = None,
    source_reference: str | None = None,
    customer_requirement_summary: str | None = None,
    estimated_value: Decimal | None = None,
) -> dict[str, Any]:
    """Optional arguments all default to the original behaviour; see create_account above for why
    an explicit `account_name` is used verbatim rather than tag-prefixed."""
    account = create_account(
        run_id=run_id,
        actor_public_id=actor_public_id,
        suffix=suffix,
        account_name=account_name,
        legal_name=legal_name,
        segment=segment,
        industry=industry,
    )

    with SessionLocal() as db:
        payload = OpportunityCreate(
            opportunity_name=opportunity_name or f"{data_tag(run_id)} Opportunity {suffix}",
            opportunity_source="manual",
            source_reference=source_reference or f"TE-1 smoke-data harness run {run_id}",
            customer_requirement_summary=(
                customer_requirement_summary
                or "Equipment hiring requirement seeded for automated regression testing."
            ),
            estimated_value=estimated_value if estimated_value is not None else Decimal("250000.00"),
        )
        opportunity_result = opportunities_service.create_opportunity(
            db, payload=payload, current_user_public_id=actor_public_id
        )
        opportunity_public_id = opportunity_result.opportunity.public_id

    with SessionLocal() as db:
        repair_payload = OpportunityAccountRepairRequest(account_public_id=UUID(account["public_id"]))
        repair_result = opportunities_service.repair_opportunity_account(
            db,
            public_id=opportunity_public_id,
            payload=repair_payload,
            current_user_public_id=actor_public_id,
        )

    return {
        "account": account,
        "opportunity": {
            "public_id": str(repair_result.opportunity.public_id),
            "opportunity_name": repair_result.opportunity.opportunity_name,
        },
    }


def create_lead(*, run_id: str, actor_public_id: str, suffix: str) -> dict[str, Any]:
    """Creates a Lead in NEW status (Slice 2A). Deliberately does not qualify or convert it -
    that is a separate, explicit step (qualify_lead / convert_lead_to_account_opportunity) so a
    scenario can leave a Lead ready for a presenter to qualify live."""
    with SessionLocal() as db:
        payload = LeadCreate(
            lead_source="rfq",
            source_reference=f"{data_tag(run_id)} lead reference",
            company_name=f"{data_tag(run_id)} Company {suffix}",
            contact_name="Demo Contact",
            contact_phone="+91-9800000000",
            contact_email="demo.contact@example.invalid",
            requirement_summary="Heavy-lift crane and trailer mobilisation requirement, seeded for vendor demo.",
        )
        result = leads_service.create_lead(db, payload=payload, current_user_public_id=actor_public_id)
        return {
            "public_id": str(result.lead.public_id),
            "company_name": result.lead.company_name,
            "lead_status_code": result.lead.lead_status_code,
        }


def add_lead_activity(*, actor_public_id: str, lead_public_id: str) -> dict[str, Any]:
    with SessionLocal() as db:
        payload = LeadActivityCreate(
            activity_type="CALL",
            activity_at=_now(),
            notes="Discussed heavy-lift crane requirement and mobilisation timeline with the customer.",
            outcome="Customer confirmed interest; requested a formal quotation.",
        )
        result = leads_service.create_lead_activity(
            db, public_id=UUID(lead_public_id), payload=payload, current_user_public_id=actor_public_id
        )
    return {"public_id": str(result.activity.public_id)}


def qualify_lead(
    *, actor_public_id: str, lead_public_id: str, decision_status_code: str = "QUALIFIED", reason: str | None = None
) -> dict[str, Any]:
    """Performs the Slice 2E qualification/closure decision action. Never sets lead_status_code
    directly - always goes through decide_lead_qualification, matching the real button."""
    with SessionLocal() as db:
        payload = LeadQualificationDecision(
            decision_status_code=decision_status_code,
            decision_notes="Recorded for the vendor demo scenario pack.",
            reason=reason,
        )
        result = leads_service.decide_lead_qualification(
            db, public_id=UUID(lead_public_id), payload=payload, current_user_public_id=actor_public_id
        )
    return {"lead_status_code": result.lead.lead_status_code}


def convert_lead_to_account_opportunity(*, actor_public_id: str, lead_public_id: str) -> dict[str, Any]:
    """Performs the Slice 3D Lead conversion action. Requires the Lead to already be QUALIFIED
    (via qualify_lead) - never bypasses that precondition."""
    with SessionLocal() as db:
        payload = LeadConversionCreate(conversion_notes="Converted for the vendor demo scenario pack.")
        result = leads_service.convert_lead(
            db, public_id=UUID(lead_public_id), payload=payload, current_user_public_id=actor_public_id
        )
    return {
        "account": {
            "public_id": str(result.account.public_id),
            "account_name": result.account.account_name,
        },
        "opportunity": {
            "public_id": str(result.opportunity.public_id),
            "opportunity_name": result.opportunity.opportunity_name,
        },
    }


def create_offer_with_line(
    *, run_id: str, actor_public_id: str, opportunity_public_id: str, suffix: str
) -> dict[str, Any]:
    today = business_time.india_today()
    with SessionLocal() as db:
        payload = CommercialOfferCreate(
            opportunity_public_id=UUID(opportunity_public_id),
            offer_title=f"{data_tag(run_id)} Commercial Offer {suffix}",
            offer_mode="plum_generated",
            offer_type="firm",
            offer_value=Decimal("250000.00"),
            currency_code="INR",
            offer_date=today,
            valid_until=today + timedelta(days=30),
            remarks=f"Seeded by the TE-1 smoke-data harness, run {run_id}.",
        )
        offer_result = offers_service.create_commercial_offer(
            db, payload=payload, current_user_public_id=actor_public_id
        )
        offer_public_id = offer_result.commercial_offer.public_id
        offer_code = offer_result.commercial_offer.offer_code

    with SessionLocal() as db:
        line_payload = CommercialOfferLineCreate(
            scope_description="80T crawler crane with operator, seeded for TE-1 smoke/regression testing.",
            equipment_service_category="Crane",
            quantity=Decimal("10.00"),
            uom="day",
            rate_amount=Decimal("25000.00"),
            currency_code="INR",
            remarks="TE-1 smoke-data harness line.",
        )
        line_result = offers_service.create_commercial_offer_line(
            db,
            public_id=offer_public_id,
            payload=line_payload,
            current_user_public_id=actor_public_id,
        )

    return {
        "public_id": str(offer_public_id),
        "offer_code": offer_code,
        "line_public_id": str(line_result.offer_line.public_id),
    }


def add_offer_line(
    *,
    actor_public_id: str,
    offer_public_id: str,
    scope_description: str | None = None,
    equipment_service_category: str | None = None,
    quantity: Decimal | None = None,
    uom: str | None = None,
    rate_amount: Decimal | None | _Unset = UNSET,
    remarks: str | None = None,
) -> dict[str, Any]:
    """Adds one more active line to an already-existing Commercial Offer (Base or related).
    Distinct from create_offer_with_line, which creates a brand-new offer and its first line
    together; this is used when a related offer already exists and needs its own line.

    Every argument after `offer_public_id` is optional and defaults to the original values, so
    the pre-existing scenarios are unchanged. The UAT datasets pass real BOQ shapes through them:
    `rate_amount=None` is meaningful rather than lazy, because an active line with no rate is
    reachable in the application and is what makes a quotation read "Not fully priced"."""
    with SessionLocal() as db:
        line_payload = CommercialOfferLineCreate(
            scope_description=(
                scope_description or "Related offer line, seeded for TE-1 smoke/regression testing."
            ),
            equipment_service_category=equipment_service_category or "Crane",
            quantity=quantity if quantity is not None else Decimal("5.00"),
            uom=uom or "day",
            rate_amount=Decimal("22000.00") if isinstance(rate_amount, _Unset) else rate_amount,
            currency_code="INR",
            remarks=remarks if remarks is not None else "TE-1 smoke-data harness related-offer line.",
        )
        line_result = offers_service.create_commercial_offer_line(
            db,
            public_id=UUID(offer_public_id),
            payload=line_payload,
            current_user_public_id=actor_public_id,
        )
    return {"line_public_id": str(line_result.offer_line.public_id)}


def create_offer_no_line(
    *,
    run_id: str,
    actor_public_id: str,
    opportunity_public_id: str,
    suffix: str,
    offer_title: str | None = None,
    offer_mode: str | None = None,
    offer_type: str | None = None,
    offer_value: Decimal | None = None,
    remarks: str | None = None,
) -> dict[str, Any]:
    """Creates a Commercial Offer with zero lines. Used by the regression scenarios to demonstrate
    the real, backend-enforced 'at least one active line' precondition (submission readiness /
    mark-submitted), not a fabricated UI-only blocker - and by the UAT datasets as the starting
    point for an offer whose lines are then added individually with their own BOQ values.

    Optional arguments default to the original values, so existing scenarios are unchanged."""
    today = business_time.india_today()
    with SessionLocal() as db:
        payload = CommercialOfferCreate(
            opportunity_public_id=UUID(opportunity_public_id),
            offer_title=offer_title or f"{data_tag(run_id)} Commercial Offer {suffix}",
            offer_mode=offer_mode or "plum_generated",
            offer_type=offer_type or "firm",
            offer_value=offer_value if offer_value is not None else Decimal("250000.00"),
            currency_code="INR",
            offer_date=today,
            valid_until=today + timedelta(days=30),
            remarks=(
                remarks
                if remarks is not None
                else f"Seeded by the TE-1 smoke-data harness, run {run_id}. Deliberately has no lines yet."
            ),
        )
        offer_result = offers_service.create_commercial_offer(
            db, payload=payload, current_user_public_id=actor_public_id
        )
    return {
        "public_id": str(offer_result.commercial_offer.public_id),
        "offer_code": offer_result.commercial_offer.offer_code,
    }


def add_pricing_evidence(*, actor_public_id: str, offer_public_id: str, line_public_id: str) -> dict[str, Any]:
    """Adds one market-rate pricing evidence entry to one offer line and selects it as that line's
    basis rate in the same call (Slices 4D and 4G), matching the real 'add as basis' path rather
    than a separate select-basis call."""
    with SessionLocal() as db:
        payload = CommercialOfferPricingEvidenceCreate(
            line_public_id=UUID(line_public_id),
            evidence_type="market_rate",
            source_name="Vendor demo market-rate reference (fictional)",
            equipment_service_description="80T crawler crane with operator, day rate.",
            rate_amount=Decimal("24500.00"),
            currency_code="INR",
            rate_basis="per day",
            collected_by_name="Operations (demo)",
            collected_at=_now(),
            is_selected_basis=True,
            selection_reason="Selected for equipment availability and prior reliability, not lowest rate.",
            comparison_notes="Seeded for the vendor demo scenario pack.",
        )
        result = offers_service.create_commercial_offer_pricing_evidence(
            db, public_id=UUID(offer_public_id), payload=payload, current_user_public_id=actor_public_id
        )
    return {"public_id": str(result.pricing_evidence.public_id)}


def attach_recommended_tc_clauses(
    *, actor_public_id: str, offer_public_id: str, recommendation_basis: str = "HIRING"
) -> dict[str, Any]:
    """Attaches every currently-missing recommended header clause (Slice 6G) for the given
    basis. Idempotent, matching the real action."""
    with SessionLocal() as db:
        payload = CommercialOfferTcClauseAttachRecommendedRequest(recommendation_basis=recommendation_basis)
        result = offers_service.attach_recommended_commercial_offer_tc_clauses(
            db, public_id=UUID(offer_public_id), payload=payload, current_user_public_id=actor_public_id
        )
    return {"attached_count": result.attached_count}


def create_related_offer(
    *,
    run_id: str,
    actor_public_id: str,
    base_offer_public_id: str,
    offer_purpose: str,
    related_work_order_public_id: str | None,
    customer_request_summary: str,
) -> dict[str, Any]:
    """Performs the Slice 6O.1 related-offer creation action (Supplementary Offer /
    Change Quotation). Never bypasses create_related_commercial_offer's own guards
    (Base Offer must be ACCEPTED, Work Order lineage validated, etc.)."""
    with SessionLocal() as db:
        payload = CommercialOfferRelatedOfferCreate(
            offer_purpose=offer_purpose,
            related_work_order_public_id=UUID(related_work_order_public_id) if related_work_order_public_id else None,
            customer_request_reference=f"{data_tag(run_id)} request reference",
            customer_request_summary=customer_request_summary,
        )
        result = offers_service.create_related_commercial_offer(
            db,
            base_offer_public_id=UUID(base_offer_public_id),
            payload=payload,
            current_user_public_id=actor_public_id,
        )
    related_offer = result.commercial_offer
    return {
        "public_id": str(related_offer.public_id),
        "offer_code": related_offer.offer_code,
        "offer_purpose": related_offer.offer_purpose,
        "base_offer_public_id": str(related_offer.base_offer_public_id) if related_offer.base_offer_public_id else None,
        "related_work_order_public_id": (
            str(related_offer.related_work_order_public_id) if related_offer.related_work_order_public_id else None
        ),
    }


def add_submission_evidence(*, actor_public_id: str, offer_public_id: str, label: str | None = None) -> dict[str, Any]:
    with SessionLocal() as db:
        evidence_payload = CommercialOfferSubmissionEvidenceCreate(
            submission_channel="EMAIL",
            submitted_at=_now(),
            recipient_summary="Customer procurement contact (seeded for vendor demo/regression testing).",
            document_reference_label=label or "TE-1 smoke-data harness submission",
        )
        result = offers_service.create_commercial_offer_submission_evidence(
            db,
            public_id=UUID(offer_public_id),
            payload=evidence_payload,
            current_user_public_id=actor_public_id,
        )
    return {"public_id": str(result.submission_evidence.public_id)}


def add_credit_review(
    *, actor_public_id: str, offer_public_id: str, review_status: str = "WITHIN_LIMIT_AS_PER_MANUAL_REVIEW"
) -> dict[str, Any]:
    with SessionLocal() as db:
        credit_payload = CommercialOfferCreditReviewCreate(
            review_status=review_status,
            reviewed_at=_now(),
            review_basis="TE-1 smoke-data harness manual review.",
        )
        result = offers_service.create_commercial_offer_credit_review(
            db,
            public_id=UUID(offer_public_id),
            payload=credit_payload,
            current_user_public_id=actor_public_id,
        )
    return {"public_id": str(result.credit_review.public_id)}


def mark_offer_submitted(*, actor_public_id: str, offer_public_id: str) -> None:
    """Performs the Slice 6J controlled mark-submitted action directly. Callers must have
    already recorded submission evidence and a non-rejected credit review, exactly like the
    real button's own preconditions - this never bypasses those guards."""
    with SessionLocal() as db:
        offers_service.mark_commercial_offer_submitted(
            db, public_id=UUID(offer_public_id), current_user_public_id=actor_public_id
        )


def submit_offer(*, run_id: str, actor_public_id: str, offer_public_id: str) -> dict[str, Any]:
    """Records submission evidence + a clean manual credit review, then calls the
    Slice 6J mark-submitted action. This exercises the same guards
    (Account/Opportunity traceability, active line, evidence, credit review) that
    the real submission button enforces -- the harness never sets offer_status_code
    directly. Composed from add_submission_evidence / add_credit_review / mark_offer_submitted
    so a scenario can instead stop after preparation (leaving the offer ready for a presenter
    to click "Mark Submitted" live)."""
    evidence = add_submission_evidence(actor_public_id=actor_public_id, offer_public_id=offer_public_id)
    add_credit_review(actor_public_id=actor_public_id, offer_public_id=offer_public_id)
    mark_offer_submitted(actor_public_id=actor_public_id, offer_public_id=offer_public_id)
    return {"submission_evidence_public_id": evidence["public_id"]}


def make_commercial_offer_version(
    *, actor_public_id: str, offer_public_id: str, reason: str = "CUSTOMER_CLARIFICATION"
) -> dict[str, Any]:
    """Copies the latest sent offer into the next editable immutable-version row (Slice 9F)."""
    with SessionLocal() as db:
        result = offers_service.create_commercial_offer_version(
            db,
            public_id=UUID(offer_public_id),
            payload=CommercialOfferVersionCreate(
                version_reason=reason,
                version_note="Customer requested a revised commercial position before resubmission.",
            ),
            current_user_public_id=actor_public_id,
        )
        line_public_ids = [
            str(row[0])
            for row in db.execute(
                text(
                    "SELECT line_public_id FROM crm_commercial_offer_line "
                    "WHERE commercial_offer_id = (SELECT id FROM crm_commercial_offer WHERE offer_public_id = :p) "
                    "ORDER BY line_number, id"
                ),
                {"p": str(result.commercial_offer.public_id)},
            ).fetchall()
        ]
    offer = result.commercial_offer
    return {
        "public_id": str(offer.public_id),
        "offer_code": offer.offer_code,
        "version_number": offer.version_number,
        "previous_version_offer_public_id": str(offer.previous_version_offer_public_id),
        "line_public_ids": line_public_ids,
    }


def record_customer_response(*, actor_public_id: str, offer_public_id: str, outcome: str) -> None:
    """Uses the Slice 6L Customer Response action -- the only supported path to
    ACCEPTED/REJECTED since the Slice 6M.1 terminal-status guard. The harness must
    never bypass this by setting offer_status_code through a generic update path."""
    with SessionLocal() as db:
        payload = CommercialOfferCustomerResponseCreate(
            response_outcome=outcome,
            response_received_at=_now(),
            response_channel="EMAIL",
            customer_response_notes="Recorded by the TE-1 smoke-data harness.",
        )
        offers_service.create_commercial_offer_customer_response(
            db,
            public_id=UUID(offer_public_id),
            payload=payload,
            current_user_public_id=actor_public_id,
        )


def create_work_order(*, actor_public_id: str, offer_public_id: str) -> dict[str, Any]:
    """Performs the frozen Slice 6D.1 Accepted Offer -> Work Order shell handoff, with the customer's Work Order
    reference it has required since CS-04 part 1: an invented one, unique to this call."""
    with SessionLocal() as db:
        payload = WorkOrderCreateFromCommercialOffer(
            commercial_offer_public_id=UUID(offer_public_id),
            customer_wo_reference=f"CUST-WO-{uuid4().hex[:8].upper()}",
            remarks="Created by the TE-1 smoke-data harness (frozen Slice 6D.1 handoff route).",
        )
        result = work_orders_service.create_work_order_from_commercial_offer(
            db, payload=payload, current_user_public_id=actor_public_id
        )
    return {
        "public_id": str(result.work_order.public_id),
        "work_order_code": result.work_order.work_order_code,
        "line_public_ids": [str(line.public_id) for line in result.lines],
    }


def create_work_order_amendment(
    *,
    run_id: str,
    actor_public_id: str,
    work_order_public_id: str,
    amendment_type_code: str,
    commercial_change_summary: str | None = None,
    related_commercial_offer_public_id: str | None = None,
) -> dict[str, Any]:
    """Performs the Slice 6O.2 Work Order Amendment intake action
    (create_work_order_amendment). This is an intake/review record only - the harness
    never applies it to the Work Order or its lines, matching the real service's own
    boundary."""
    with SessionLocal() as db:
        payload = WorkOrderAmendmentCreate(
            amendment_type_code=amendment_type_code,
            received_date=business_time.india_today(),
            amendment_reason=f"Customer amendment request seeded by the TE-1 smoke-data harness, run {run_id}.",
            commercial_change_summary=commercial_change_summary,
            related_commercial_offer_public_id=(
                UUID(related_commercial_offer_public_id) if related_commercial_offer_public_id else None
            ),
            customer_amendment_reference=f"{data_tag(run_id)} amendment reference",
        )
        result = work_orders_service.create_work_order_amendment(
            db,
            work_order_public_id=UUID(work_order_public_id),
            payload=payload,
            current_user_public_id=actor_public_id,
        )
    amendment = result.amendment
    return {
        "public_id": str(amendment.public_id),
        "amendment_type_code": amendment.amendment_type_code,
        "amendment_status_code": amendment.amendment_status_code,
        "amendment_sequence_no": amendment.amendment_sequence_no,
    }


def add_amendment_line(*, actor_public_id: str, work_order_public_id: str, amendment_public_id: str) -> dict[str, Any]:
    """Adds one ADD_LINE proposal to an existing Work Order Amendment. This is a proposal
    only; it never creates or changes a Work Order line."""
    with SessionLocal() as db:
        payload = WorkOrderAmendmentLineCreate(
            action_code="ADD_LINE",
            proposed_scope_description="Additional scope proposed for TE-1 smoke/regression testing.",
            proposed_quantity=Decimal("5.00"),
            proposed_uom="day",
            proposed_rate_amount=Decimal("22000.00"),
        )
        result = work_orders_service.create_work_order_amendment_line(
            db,
            work_order_public_id=UUID(work_order_public_id),
            amendment_public_id=UUID(amendment_public_id),
            payload=payload,
            current_user_public_id=actor_public_id,
        )
    return {"public_id": str(result.amendment_line.public_id)}


def decide_amendment(
    *,
    actor_public_id: str,
    work_order_public_id: str,
    amendment_public_id: str,
    target_status_code: str,
    reason: str | None = None,
) -> dict[str, Any]:
    """Performs the Slice 6O.2 controlled decision action (RECEIVED -> UNDER_REVIEW ->
    VALIDATED / REJECTED / CANCELLED). Never bypasses decide_work_order_amendment's own
    transition/readiness guards."""
    with SessionLocal() as db:
        payload = WorkOrderAmendmentDecision(target_status_code=target_status_code, reason=reason)
        result = work_orders_service.decide_work_order_amendment(
            db,
            work_order_public_id=UUID(work_order_public_id),
            amendment_public_id=UUID(amendment_public_id),
            payload=payload,
            current_user_public_id=actor_public_id,
        )
    return {"amendment_status_code": result.amendment.amendment_status_code}


def set_work_order_line_detail(
    *,
    actor_public_id: str,
    work_order_public_id: str,
    line_public_id: str,
    site_address_public_id: str | None = None,
    billing_gstin_public_id: str | None = None,
    billing_address_public_id: str | None = None,
    customer_line_reference: str | None = None,
    expected_detail_version: int | None = None,
    site_central_government: bool | None = None,
) -> dict[str, Any]:
    """Slice 7C: record a Work Order line's site and billing detail through the real service, so
    the Account-ownership and version checks all run. The billing basis is a billing term since
    Slice 7D; see add_work_order_line_billing_terms_period. 8A core: `site_central_government` is sent
    only when given, so a caller that does not name it keeps what is recorded, as the route does."""
    with SessionLocal() as db:
        result = work_orders_service.save_work_order_line_detail(
            db,
            work_order_public_id=UUID(work_order_public_id),
            line_public_id=UUID(line_public_id),
            payload=WorkOrderLineDetailUpdate(
                expected_detail_version=expected_detail_version,
                site_address_public_id=UUID(site_address_public_id) if site_address_public_id else None,
                billing_gstin_public_id=UUID(billing_gstin_public_id) if billing_gstin_public_id else None,
                billing_address_public_id=UUID(billing_address_public_id) if billing_address_public_id else None,
                customer_line_reference=customer_line_reference,
                **({} if site_central_government is None else {"site_central_government": site_central_government}),
            ),
            current_user_public_id=actor_public_id,
        )
    return {
        "detail_public_id": str(result.line_detail.detail_public_id),
        "detail_version": result.line_detail.detail_version,
        "is_complete": result.line_detail.is_complete,
    }


def add_work_order_line_billing_terms_period(
    *,
    actor_public_id: str,
    work_order_public_id: str,
    line_public_id: str,
    expected_period_count: int = 0,
    expected_latest_term_revision: int | None = None,
    **terms: Any,
) -> dict[str, Any]:
    """Slice 7D: add a billing-terms period to a Work Order line through the real service, so every
    term rule, the period-date rules and the conflict check run. `terms` are the request's term fields
    (for example billing_uom_code="MONTH", normal_rate_amount=Decimal("100000"))."""
    with SessionLocal() as db:
        result = work_orders_service.add_work_order_line_billing_terms_period(
            db,
            work_order_public_id=UUID(work_order_public_id),
            line_public_id=UUID(line_public_id),
            payload=WorkOrderLineBillingTermsPeriodCreate(
                expected_period_count=expected_period_count,
                expected_latest_term_revision=expected_latest_term_revision,
                **terms,
            ),
            current_user_public_id=actor_public_id,
        )
    entry = result.line_billing_terms
    return {
        "term_public_id": str(entry.periods[-1].term_public_id),
        "period_number": entry.periods[-1].period_number,
        "terms_complete": entry.terms_complete,
    }


# --- UAT data pack builders -------------------------------------------------------------------
#
# Everything below was added for the synthetic UAT data pack. Three of these cover slices that
# landed after this harness was written (9C documents, 9D interactions, 9E quote documents); the
# account-identity ones cover fields create_account has never populated. All follow the same rule
# as every builder above: call the real service function, let it commit, never write SQL directly,
# so business validation and lifecycle guards fire exactly as they do for a user on the screen.


def add_account_address(
    *,
    actor_public_id: str,
    account_public_id: str,
    address_type_code: str,
    address_line1: str,
    city: str,
    state: str,
    address_line2: str | None = None,
    district: str | None = None,
    postal_code: str | None = None,
    is_primary: bool = False,
) -> dict[str, Any]:
    with SessionLocal() as db:
        result = accounts_service.create_account_address(
            db,
            account_public_id=UUID(account_public_id),
            payload=AccountAddressCreate(
                address_type_code=address_type_code,
                address_line1=address_line1,
                address_line2=address_line2,
                city=city,
                district=district,
                state=state,
                postal_code=postal_code,
                is_primary=is_primary,
            ),
            current_user_public_id=actor_public_id,
        )
        return {
            "public_id": str(result.address.public_id),
            "address_type_code": result.address.address_type_code,
        }


def add_account_gstin(
    *,
    actor_public_id: str,
    account_public_id: str,
    gstin: str,
    state_code: str,
    state_name: str,
    gstin_verification_state_code: str = "ENTERED_NOT_VERIFIED",
    legal_name: str | None = None,
    is_primary: bool = False,
) -> dict[str, Any]:
    """One row per state registration. A single customer legitimately holds several - Slice 1I
    allows even two in the same state - which is exactly the shape the UAT dataset must carry."""
    with SessionLocal() as db:
        result = accounts_service.create_account_gstin(
            db,
            account_public_id=UUID(account_public_id),
            payload=AccountGstinCreate(
                gstin=gstin,
                state_code=state_code,
                state_name=state_name,
                gstin_verification_state_code=gstin_verification_state_code,
                legal_name=legal_name,
                is_primary=is_primary,
            ),
            current_user_public_id=actor_public_id,
        )
        return {"public_id": str(result.gstin.public_id), "gstin": result.gstin.gstin}


def set_account_tax_profile(
    *,
    actor_public_id: str,
    account_public_id: str,
    pan: str,
    pan_verification_state_code: str = "ENTERED_NOT_VERIFIED",
    pan_legal_name: str | None = None,
) -> dict[str, Any]:
    with SessionLocal() as db:
        result = accounts_service.upsert_account_tax_profile(
            db,
            account_public_id=UUID(account_public_id),
            payload=AccountTaxProfileUpsert(
                pan=pan,
                pan_verification_state_code=pan_verification_state_code,
                pan_legal_name=pan_legal_name,
            ),
            current_user_public_id=actor_public_id,
        )
        return {"pan": result.tax_profile.pan}


def log_interaction(
    *,
    actor_public_id: str,
    actor_username: str,
    linked_record_type: str,
    linked_record_public_id: str,
    channel_code: str,
    direction_code: str,
    subject: str,
    body_text: str | None = None,
    occurred_at: datetime | None = None,
    outcome: str | None = None,
    next_follow_up_at: datetime | None = None,
) -> dict[str, Any]:
    """Slice 9D. create_interaction needs a full AuthUser, not just a public id, because it
    resolves INTERACTION_CONTENT_READ to decide whether the response body is redacted. The roles
    are read from the database through identity's own repository rather than asserted here, so the
    harness never invents an authority the seed user does not actually hold."""
    with SessionLocal() as db:
        user_row = get_user_with_roles_by_username(db, actor_username)
        if user_row is None:
            raise RuntimeError(f"Seed user {actor_username!r} was not found in app_user.")
        result = interactions_service.create_interaction(
            db,
            payload=InteractionCreate(
                linked_record_type=linked_record_type,
                linked_record_public_id=UUID(linked_record_public_id),
                channel_code=channel_code,
                direction_code=direction_code,
                occurred_at=occurred_at or _now(),
                subject=subject,
                body_text=body_text,
                outcome=outcome,
                next_follow_up_at=next_follow_up_at,
            ),
            current_user_public_id=actor_public_id,
            current_user=to_auth_user(user_row),
        )
        return {
            "public_id": str(result.interaction.public_id),
            "channel_code": channel_code,
            "subject": subject,
        }


def generate_quote_document(*, actor_public_id: str, offer_public_id: str) -> dict[str, Any]:
    """Slice 9E. Requires the offer to be DRAFT, READY_FOR_REVIEW or SUBMITTED, to resolve an
    Account, and to have at least one ACTIVE line - a concluded offer is refused by its own
    precondition, so scenarios must generate before recording a final customer response."""
    with SessionLocal() as db:
        result = offers_service.generate_commercial_offer_quote_document(
            db,
            public_id=UUID(offer_public_id),
            current_user_public_id=actor_public_id,
        )
        return {
            "public_id": str(result.quote_document.public_id),
            "version_no": result.quote_document.version_no,
            "quote_reference": result.quote_document.quote_reference,
            "document_public_id": str(result.quote_document.document_public_id),
            "quote_status_code": result.quote_document.quote_status_code,
        }


def approve_quote_document(
    *,
    actor_public_id: str,
    offer_public_id: str,
    quote_document_public_id: str,
    approval_note: str | None = None,
) -> dict[str, Any]:
    """Slice 9E approval-for-issue. Deliberately takes its own actor argument: approval requires
    COMMERCIAL_OFFER_QUOTE_APPROVE, which SALES_USER does not hold, so a scenario approving a
    version must pass a manager's public id rather than the harness default actor."""
    with SessionLocal() as db:
        result = offers_service.approve_commercial_offer_quote_document(
            db,
            public_id=UUID(offer_public_id),
            quote_document_public_id=UUID(quote_document_public_id),
            payload=CommercialOfferQuoteDocumentApproveRequest(approval_note=approval_note),
            current_user_public_id=actor_public_id,
        )
        return {
            "public_id": str(result.quote_document.public_id),
            "version_no": result.quote_document.version_no,
            "quote_status_code": result.quote_document.quote_status_code,
        }


# --- sales-journey builders -------------------------------------------------------------------
#
# Added for the UAT data pack after the owner asked whether the practice data covered the work a
# sales executive actually does - nurturing a lead with calls and notes, closing the ones not worth
# pursuing, collecting several market rates through Operations, choosing which one to quote on,
# negotiating, and revising. It did not. These builders cover that ground.


def add_market_rate(
    *,
    actor_public_id: str,
    offer_public_id: str,
    line_public_id: str,
    source_name: str,
    equipment_service_description: str,
    rate_amount: Decimal,
    rate_basis: str,
    collected_by_name: str = "Operations Executive",
    comparison_notes: str | None = None,
) -> dict[str, Any]:
    """One market rate collected from a vendor for one offer line (Slice 4G), recorded WITHOUT
    selecting it as the line's basis.

    Distinct from `add_pricing_evidence`, which adds a single entry and selects it in the same
    call. Real rate discovery collects several quotes and then chooses between them, and the
    choice is only visible if more than one rate exists to choose from - so the two steps are
    separate here."""
    with SessionLocal() as db:
        payload = CommercialOfferPricingEvidenceCreate(
            line_public_id=UUID(line_public_id),
            evidence_type="market_rate",
            source_name=source_name,
            equipment_service_description=equipment_service_description,
            rate_amount=rate_amount,
            currency_code="INR",
            rate_basis=rate_basis,
            collected_by_name=collected_by_name,
            collected_at=_now(),
            is_selected_basis=False,
            comparison_notes=comparison_notes,
        )
        result = offers_service.create_commercial_offer_pricing_evidence(
            db, public_id=UUID(offer_public_id), payload=payload, current_user_public_id=actor_public_id
        )
    return {
        "public_id": str(result.pricing_evidence.public_id),
        "line_public_id": line_public_id,
        "source_name": source_name,
        "rate_amount": str(rate_amount),
    }


def select_basis_rate(
    *, actor_public_id: str, offer_public_id: str, evidence_public_id: str, selection_reason: str
) -> dict[str, Any]:
    """Chooses one collected rate as the basis for the quotation (Slice 4D).

    `selection_reason` is required by the service, and deliberately so: the contract states the
    chosen rate need NOT be the lowest, and a choice that is not the lowest is only defensible if
    the reason is recorded at the time. The dataset uses this both ways - lowest for some
    customers, second-lowest for others where availability or reliability decided it."""
    with SessionLocal() as db:
        result = offers_service.select_commercial_offer_basis_rate(
            db,
            public_id=UUID(offer_public_id),
            evidence_public_id=UUID(evidence_public_id),
            payload=CommercialOfferPricingEvidenceBasisSelection(selection_reason=selection_reason),
            current_user_public_id=actor_public_id,
        )
    return {"public_id": str(result.pricing_evidence.public_id), "selection_reason": selection_reason}


def create_lead_detailed(
    *,
    run_id: str,
    actor_public_id: str,
    company_name: str,
    contact_name: str,
    contact_phone: str,
    contact_email: str,
    requirement_summary: str,
    lead_source: str = "rfq",
    source_reference: str | None = None,
) -> dict[str, Any]:
    """A Lead with real contact and requirement detail, as distinct from `create_lead`'s fixed
    demo values. Starts in the initial status; qualification and conversion remain separate,
    explicit steps so the practice data can show a lead at each stage of its life."""
    with SessionLocal() as db:
        payload = LeadCreate(
            lead_source=lead_source,
            source_reference=source_reference or f"UAT pilot dataset, run {run_id}",
            company_name=company_name,
            contact_name=contact_name,
            contact_phone=contact_phone,
            contact_email=contact_email,
            requirement_summary=requirement_summary,
        )
        result = leads_service.create_lead(db, payload=payload, current_user_public_id=actor_public_id)
        return {
            "public_id": str(result.lead.public_id),
            "company_name": result.lead.company_name,
            "lead_status_code": result.lead.lead_status_code,
        }


def add_lead_activity_detailed(
    *,
    actor_public_id: str,
    lead_public_id: str,
    activity_type: str,
    notes: str,
    outcome: str | None = None,
    activity_at: datetime | None = None,
    next_follow_up_at: datetime | None = None,
) -> dict[str, Any]:
    """One call, note, email or meeting recorded against a Lead. Several of these in sequence are
    what a nurtured lead actually looks like, which a single activity does not show."""
    with SessionLocal() as db:
        payload = LeadActivityCreate(
            activity_type=activity_type,
            activity_at=activity_at or _now(),
            notes=notes,
            outcome=outcome,
            next_follow_up_at=next_follow_up_at,
        )
        result = leads_service.create_lead_activity(
            db, public_id=UUID(lead_public_id), payload=payload, current_user_public_id=actor_public_id
        )
    return {"public_id": str(result.activity.public_id), "activity_type": activity_type}


def upload_customer_document(
    *,
    actor_public_id: str,
    linked_record_type: str,
    linked_record_public_id: str,
    document_type: str,
    file_name: str,
    body_text: str,
    remarks: str | None = None,
) -> dict[str, Any]:
    """Uploads a small text file through the real Slice 9C upload path, storage provider and all.

    Practice data needs uploaded documents, not only generated ones. A customer purchase order, a
    signed acceptance or a work order copy arrives as a file from outside; the quotation the system
    produces itself is a different path with different code behind it, and exercising only the
    second leaves the first untested. The content is deliberately plain text so no binary fixture
    has to be committed to the repository."""
    import io as _io

    with SessionLocal() as db:
        result = documents_service.upload_document(
            db,
            linked_record_type=linked_record_type,
            linked_record_public_id=UUID(linked_record_public_id),
            document_type=document_type,
            file_name=file_name,
            declared_content_type="text/plain",
            stream=_io.BytesIO(body_text.encode("utf-8")),
            remarks=remarks,
            current_user_public_id=actor_public_id,
        )
    return {
        "public_id": str(result.document.public_id),
        "file_name": file_name,
        "document_type": document_type,
    }


def set_work_order_contract_period(
    *,
    actor_public_id: str,
    work_order_public_id: str,
    contract_start_date: str | None = None,
    contract_end_basis_code: str | None = None,
    contract_end_date: str | None = None,
    contract_notes: str | None = None,
    expected_period_version: int | None = None,
) -> dict[str, Any]:
    """Slice 7D Part 3: record a Work Order's contract dates through the real service, so the date
    rules against the lines' own dates and their billing periods all run."""
    with SessionLocal() as db:
        result = work_orders_service.save_work_order_contract_period(
            db,
            work_order_public_id=UUID(work_order_public_id),
            payload=WorkOrderContractPeriodUpdate(
                expected_period_version=expected_period_version,
                contract_start_date=date.fromisoformat(contract_start_date) if contract_start_date else None,
                contract_end_basis_code=contract_end_basis_code,
                contract_end_date=date.fromisoformat(contract_end_date) if contract_end_date else None,
                contract_notes=contract_notes,
            ),
            current_user_public_id=actor_public_id,
        )
    period = result.contract_period
    return {
        "period_public_id": str(period.period_public_id),
        "period_version": period.period_version,
        "contract_state_code": period.contract_state_code,
        "is_complete": period.is_complete,
        "needs_firm_end_date": period.needs_firm_end_date,
    }


def add_work_order_contract_extension(
    *,
    actor_public_id: str,
    work_order_public_id: str,
    new_end_date: str,
    received_date: str,
    customer_reference: str | None = None,
    extension_notes: str | None = None,
) -> dict[str, Any]:
    """Slice 7D Part 3: record one extension, moving the contract end date and keeping the previous
    one as history."""
    with SessionLocal() as db:
        result = work_orders_service.create_work_order_contract_extension(
            db,
            work_order_public_id=UUID(work_order_public_id),
            payload=WorkOrderContractExtensionCreate(
                new_end_date=date.fromisoformat(new_end_date),
                received_date=date.fromisoformat(received_date),
                customer_reference=customer_reference,
                extension_notes=extension_notes,
            ),
            current_user_public_id=actor_public_id,
        )
    period = result.contract_period
    latest = period.extensions[-1]
    return {
        "extension_public_id": str(latest.extension_public_id),
        "extension_sequence_no": latest.extension_sequence_no,
        "contract_end_date": period.contract_end_date.isoformat() if period.contract_end_date else None,
    }


def set_work_order_holidays(
    *,
    actor_public_id: str,
    work_order_public_id: str,
    holidays_answer_code: str,
    holidays: list[tuple[str, str, str | None]] | None = None,
    working_days: list[tuple[str, str, str | None]] | None = None,
    expected_list_version: int | None = None,
) -> dict[str, Any]:
    """Slice 7D Part 4, and since HOL-1 the Work Order's changes to PBL's calendar: recorded through the real service,
    so the answer rule and each date's check against the contract run. `holidays` are the holidays the Work Order adds,
    as (ISO date, kind, description); `working_days` the calendar holidays it works, as (ISO date, rate, note)."""
    changes = [
        WorkOrderHolidayChangeInput(
            change_code="HOLIDAY_ADDED", holiday_date=date.fromisoformat(day), holiday_kind_code=kind, description=description
        )
        for day, kind, description in (holidays or [])
    ] + [
        WorkOrderHolidayChangeInput(
            change_code="WORKING_DAY", holiday_date=date.fromisoformat(day), working_day_rate_code=rate, description=note
        )
        for day, rate, note in (working_days or [])
    ]
    with SessionLocal() as db:
        result = work_orders_service.save_work_order_holidays(
            db,
            work_order_public_id=UUID(work_order_public_id),
            payload=WorkOrderHolidayListUpdate(
                expected_list_version=expected_list_version,
                holidays_answer_code=holidays_answer_code,
                changes=changes,
            ),
            current_user_public_id=actor_public_id,
        )
    holiday_list = result.holiday_list
    return {
        "holiday_list_public_id": str(holiday_list.holiday_list_public_id),
        "list_version": holiday_list.list_version,
        "holiday_count": sum(1 for change in holiday_list.changes if change.change_code == "HOLIDAY_ADDED"),
        "working_day_count": sum(1 for change in holiday_list.changes if change.change_code == "WORKING_DAY"),
        "is_complete": holiday_list.is_complete,
    }


# HOL-1: the years a run may start in PBL's holiday calendar - far ahead, so never one anyone keeps for real, and apart
# from the 2090 to 2094 the backend tests use (tests/holiday_calendar_test_support.py).
HARNESS_CALENDAR_YEARS = range(2099, 2094, -1)


def free_harness_calendar_year() -> int:
    """The latest harness year not started in PBL's calendar. Refused, before anything is written, when every one is
    taken - by runs not cleaned up - rather than writing into a year another run owns."""
    with SessionLocal() as db:
        started = {
            int(row[0])
            for row in db.execute(
                text("SELECT calendar_year FROM holiday_calendar_year WHERE calendar_year BETWEEN :low AND :high"),
                {"low": min(HARNESS_CALENDAR_YEARS), "high": max(HARNESS_CALENDAR_YEARS)},
            ).fetchall()
        }
    for year in HARNESS_CALENDAR_YEARS:
        if year not in started:
            return year
    raise RuntimeError(
        f"Every holiday calendar year the harness may use ({min(HARNESS_CALENDAR_YEARS)} to {max(HARNESS_CALENDAR_YEARS)}) "
        "is already started, by runs not cleaned up. Clean them up first; nothing was written."
    )


def create_holiday_calendar_year(
    *,
    actor_public_id: str,
    calendar_year: int,
    holidays: list[tuple[str, str, str, list[str]]],
    complete: bool = False,
) -> dict[str, Any]:
    """HOL-1: start a year of PBL's holiday calendar through the real service, so every rule runs. `holidays` are
    (month-day, kind, name, state codes - empty for all of India)."""
    with SessionLocal() as db:
        result = holiday_calendar_service.save_year(
            db,
            calendar_year=calendar_year,
            payload=HolidayCalendarYearInput(
                expected_version=None,
                is_complete=complete,
                holidays=[
                    HolidayCalendarHolidayInput(
                        holiday_date=date.fromisoformat(f"{calendar_year}-{month_day}"),
                        holiday_kind_code=kind,
                        holiday_name=name,
                        applies_to_code="STATES" if states else "ALL_INDIA",
                        state_codes=states,
                    )
                    for month_day, kind, name, states in holidays
                ],
            ),
            user_public_id=actor_public_id,
        )
    year = result.year
    return {"public_id": year.year_public_id, "calendar_year": year.calendar_year, "year_version": year.year_version}


def create_resource_requirement(
    *,
    actor_public_id: str,
    work_order_public_id: str,
    line_public_id: str,
    units_required: int,
    required_from: str,
    equipment_class_code: str,
    equipment_type_code: str | None = None,
    capabilities: list[tuple[str, Decimal | str]] | None = None,
    required_to: str | None = None,
    crew_operators_required: int = 0,
    crew_helpers_required: int = 0,
    priority_code: str = "NORMAL",
    equipment_specification: str | None = None,
    planning_notes: str | None = None,
) -> dict[str, Any]:
    """WRR-001: record what a Work Order line needs on site through the real service, so the Equipment
    Reference checks and the dates against the contract and the line all run. `capabilities` is
    (capability code, least value) for measured capabilities, or (code, value) for a fixed list."""
    with SessionLocal() as db:
        result = resource_requirements_service.create_resource_requirement(
            db,
            payload=ResourceRequirementCreate(
                work_order_public_id=UUID(work_order_public_id),
                work_order_line_public_id=UUID(line_public_id),
                create_request_key=uuid4(),
                units_required=units_required,
                required_from=date.fromisoformat(required_from),
                required_to=date.fromisoformat(required_to) if required_to else None,
                crew_operators_required=crew_operators_required,
                crew_helpers_required=crew_helpers_required,
                priority_code=priority_code,
                planning_notes=planning_notes,
                items=[
                    ResourceRequirementItemInput(
                        equipment_class_code=equipment_class_code,
                        equipment_type_code=equipment_type_code,
                        equipment_specification=equipment_specification,
                        capabilities=[
                            ResourceRequirementCapabilityInput(
                                capability_code=code,
                                minimum_value=value if isinstance(value, Decimal) else None,
                                choice_value=value if isinstance(value, str) else None,
                            )
                            for code, value in (capabilities or [])
                        ],
                    )
                ],
            ),
            current_user_public_id=actor_public_id,
        )
    requirement = result.resource_requirement
    return {
        "public_id": str(requirement.requirement_public_id),
        "requirement_reference": requirement.requirement_reference,
        "work_order_line_public_id": str(requirement.work_order_line_public_id),
        "requirement_status_code": requirement.requirement_status_code,
        "warnings": list(requirement.warnings),
    }


# --- ERT-1: Plum's machines into the Equipment Reference ---------------------------------------------

# Plum's report as it arrives: a title line, then these 32 columns in this order (the report of 24
# September 2026). The transformer reads thirteen of them; the rest are carried here only so an invented
# report has the real shape.
PLUM_REPORT_HEADER = (
    "VehicleNo",
    "ScheduleMaintanceType",
    "BedNo",
    "EngineNo",
    "ChassisNo",
    "Make",
    "Model",
    "Capacity",
    "TankCapacity",
    "Manufacturer",
    "CommencedYear",
    "Owner",
    "PAN",
    "InsPolicyNo",
    "InsuranceCo",
    "DateOfPurchase",
    "InvoiceNo",
    "InvoiceDt",
    "VehCategory",
    "Status",
    "ConsPostingAcc",
    "TollTagAcc",
    "MaintAcc",
    "DieselAcc",
    "TollPostingAcc",
    "PostingAccount",
    "GPS",
    "StandardTyre",
    "StepneyTyre",
    "GrossVehicleWeight",
    "UnladenWeight",
    "LoadCapacity",
)


def invented_plum_report(rows: list[dict[str, str]], *, title: str) -> str:
    """A CSV in the shape of Plum's report, from invented rows (column name -> value). Every machine in it
    is made up; no row or model name of the real report is used (ERT-1 design, section 16)."""
    import csv
    import io

    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow([title] + [""] * (len(PLUM_REPORT_HEADER) - 1))
    writer.writerow(PLUM_REPORT_HEADER)
    for row in rows:
        writer.writerow([row.get(column, "") for column in PLUM_REPORT_HEADER])
    return buffer.getvalue()


def create_equipment_model(
    *,
    actor_public_id: str,
    maker: str,
    model_name: str,
    class_code: str,
    type_code: str | None = None,
    capabilities: list[tuple[str, Decimal]] | None = None,
    fits_model_public_ids: list[str] | None = None,
    maker_part_number: str | None = None,
) -> dict[str, Any]:
    """ERT-1: record a model through the real service, so the structure's rules all run. ERT-2: a kit
    model names the crane models it fits."""
    from app.modules.equipment_reference.schemas import CapabilityValueInput, EquipmentModelCreate
    from app.modules.equipment_reference.services import models as equipment_models_service

    with SessionLocal() as db:
        result = equipment_models_service.create_model(
            db,
            payload=EquipmentModelCreate(
                maker=maker,
                model_name=model_name,
                class_code=class_code,
                type_code=type_code,
                capabilities=[CapabilityValueInput(capability_code=code, value=value) for code, value in (capabilities or [])],
                fits_model_public_ids=[UUID(item) for item in (fits_model_public_ids or [])],
                maker_part_number=maker_part_number,
                create_request_key=uuid4(),
            ),
            user_public_id=actor_public_id,
        )
    model = result.model
    return {"public_id": str(model.model_public_id), "label": model.label, "class_code": model.class_code}


def add_equipment_kit(
    *, actor_public_id: str, kit_model_public_id: str, count: int, from_machine_number: str
) -> list[dict[str, Any]]:
    """ERT-2: add pieces of a kit model through the real service - several alike, or a counted set - from the
    page of a machine the kit model fits, at the versions that page would show."""
    from app.modules.equipment_reference import repository as equipment_repository
    from app.modules.equipment_reference.schemas import KitAddInput
    from app.modules.equipment_reference.services import machines as equipment_machines_service

    with SessionLocal() as db:
        machine = db.execute(
            text("SELECT asset_public_id, asset_version FROM equipment_asset WHERE machine_number = :number"),
            {"number": from_machine_number},
        ).one()
        model = equipment_repository.get_model_row(db, public_id=kit_model_public_id)
        result = equipment_machines_service.add_kit(
            db,
            payload=KitAddInput(
                create_request_key=uuid4(),
                machine_public_id=UUID(str(machine.asset_public_id)),
                expected_asset_version=int(machine.asset_version),
                kit_model_public_id=UUID(kit_model_public_id),
                expected_model_version=int(model["model_version"]),
                count=count,
            ),
            user_public_id=actor_public_id,
        )
    return [{"public_id": str(piece.asset_public_id), "reference": piece.asset_reference, "quantity": piece.quantity} for piece in result.pieces]


def map_equipment_model_name(*, actor_public_id: str, source_name: str, model_public_id: str) -> None:
    from app.modules.equipment_reference.schemas import ModelMappingInput
    from app.modules.equipment_reference.services import models as equipment_models_service

    with SessionLocal() as db:
        equipment_models_service.map_model_name(
            db,
            payload=ModelMappingInput(source_name=source_name, model_public_id=UUID(model_public_id)),
            user_public_id=actor_public_id,
        )


class EquipmentSeedRefused(RuntimeError):
    """The equipment scenarios would change records no run of theirs made."""


def require_no_equipment_fleet() -> None:
    """The equipment scenarios confirm invented Plum reports, and a confirmed report is the whole fleet:
    every machine already held that it does not name is flagged missing, re-read as unmatched and moved
    to a new version, and every waiting preview is discarded - changes cleanup cannot undo. So they seed
    only where no machine is held and no preview waits, and refuse before anything is written otherwise
    (independent review, round 4, ERT1-R4-001). A database with real machines is not theirs to run on."""
    with SessionLocal() as db:
        held = int(db.execute(text("SELECT COUNT(*) FROM equipment_asset")).scalar_one())
        waiting = int(db.execute(text("SELECT COUNT(*) FROM equipment_source_import WHERE import_status_code = 'PREVIEWED'")).scalar_one())
    if held or waiting:
        raise EquipmentSeedRefused(
            f"Refusing to seed: {held} machine(s) are held and {waiting} Plum report preview(s) wait in this database. "
            "The equipment scenarios confirm invented reports, which would mark every held machine missing and "
            "discard every waiting preview. Run them on a database with no machines; nothing was written."
        )


def upload_and_publish_equipment_report(
    *, actor_public_id: str, content: str, report_date: date, pairs: list[tuple[str, str]] | None = None
) -> dict[str, Any]:
    """Upload an invented report and confirm it through the real services - the preview, its checks and
    the confirmation all run as they do from the screen. `pairs` confirms fitted parts with it, as (part
    machine number, machine machine number)."""
    from app.modules.equipment_reference.schemas import ImportPublishInput
    from app.modules.equipment_reference.services import imports as equipment_imports_service

    with SessionLocal() as db:
        uploaded = equipment_imports_service.upload_report(
            db, content=content.encode("utf-8"), report_date=report_date, user_public_id=actor_public_id
        ).equipment_import
    with SessionLocal() as db:
        published = equipment_imports_service.publish_import(
            db,
            public_id=uploaded.import_public_id,
            payload=ImportPublishInput(
                expected_preview_version=uploaded.preview_version,
                pairs=[{"part_machine_number": part, "machine_machine_number": machine} for part, machine in pairs or []],
            ),
            user_public_id=actor_public_id,
        ).equipment_import
    return {"public_id": str(published.import_public_id), "counts": dict(published.counts)}


# --- ELG-1: certificates and "not applicable" marks ---------------------------------------------------

# A copy's bytes: the smallest file the upload's content check accepts as a PDF. Invented; no real paper.
_CERTIFICATE_COPY = b"%PDF-1.4\n% invented certificate copy for a test run\n%%EOF\n"


def equipment_asset_public_id(machine_number: str) -> str:
    with SessionLocal() as db:
        return str(db.execute(text("SELECT asset_public_id FROM equipment_asset WHERE machine_number = :number"), {"number": machine_number}).scalar_one())


def record_equipment_certificate(
    *,
    actor_public_id: str,
    asset_public_id: str,
    kind_code: str,
    number: str,
    issued_by: str,
    issued_on: date,
    valid_from: date,
    valid_until: date | None,
    valid_in_code: str | None = None,
    registered_as_code: str | None = None,
    with_copy: bool = True,
) -> dict[str, Any]:
    """Record a certificate through the real service, and attach a copy through the real upload path, as the
    Fleet Admin does from a machine's page."""
    import io as _io

    from app.modules.eligibility import service as eligibility_service
    from app.modules.eligibility.schemas import CertificateInput

    with SessionLocal() as db:
        result = eligibility_service.record_certificate(
            db,
            asset_public_id=asset_public_id,
            payload=CertificateInput(
                create_request_key=str(uuid4()),
                kind_code=kind_code,
                number=number,
                issued_by=issued_by,
                issued_on=issued_on,
                valid_from=valid_from,
                valid_until=valid_until,
                valid_in_code=valid_in_code,
                registered_as_code=registered_as_code,
            ),
            user_public_id=actor_public_id,
            show_numbers=False,
        )
    certificate_public_id = str(result.certificate_public_id)
    if with_copy:
        with SessionLocal() as db:
            documents_service.upload_document(
                db,
                linked_record_type="eligibility_certificate",
                linked_record_public_id=UUID(certificate_public_id),
                document_type="CERTIFICATE",
                file_name=f"{kind_code.lower()}-copy.pdf",
                declared_content_type="application/pdf",
                stream=_io.BytesIO(_CERTIFICATE_COPY),
                remarks=None,
                current_user_public_id=actor_public_id,
            )
    return {"public_id": certificate_public_id, "kind_code": kind_code, "with_copy": with_copy}


def mark_certificate_not_applicable(
    *, actor_public_id: str, asset_public_id: str, kind_code: str, reason: str, until: date | None = None
) -> dict[str, Any]:
    from app.modules.eligibility import service as eligibility_service
    from app.modules.eligibility.schemas import NotApplicableInput

    with SessionLocal() as db:
        result = eligibility_service.record_not_applicable(
            db,
            asset_public_id=asset_public_id,
            payload=NotApplicableInput(create_request_key=str(uuid4()), kind_code=kind_code, reason=reason, until=until),
            user_public_id=actor_public_id,
            show_numbers=False,
        )
    return {"public_id": str(result.mark_public_id), "kind_code": kind_code}


def allocate_machine(
    *,
    actor_public_id: str,
    requirement_public_id: str,
    machine_public_id: str,
    planned_from: date,
    planned_to: date | None,
    unit_number: int = 1,
) -> dict[str, Any]:
    """8A core: hold one machine on one unit of a requirement through the real service, so the site, the dates and
    eligibility are all checked; warnings are accepted, as a user who ticked "I have seen these warnings" (ELG-2's
    reminders need a held allocation whose papers run out)."""
    from app.modules.resource_assignments import service as assignments_service
    from app.modules.resource_assignments.schemas import AssignmentCreate

    with SessionLocal() as db:
        result = assignments_service.create_assignment(
            db,
            payload=AssignmentCreate(
                create_request_key=str(uuid4()),
                requirement_public_id=UUID(requirement_public_id),
                unit_number=unit_number,
                machine_public_id=UUID(machine_public_id),
                planned_from=planned_from,
                planned_to=planned_to,
                accept_warnings=True,
            ),
            user_public_id=actor_public_id,
            may_set_billing_cycle=False,
        )
    assignment = result.assignment
    return {
        "public_id": assignment.assignment_public_id,
        "reference": assignment.assignment_reference,
        "version": assignment.assignment_version,
    }


def list_kit_on_trip(
    *,
    actor_public_id: str,
    assignment_public_id: str,
    assignment_version: int,
    piece_public_id: str,
    trip_number: int = 1,
    quantity: int = 1,
) -> dict[str, Any]:
    """8A core: list one piece of kit on an allocation's trip through the real service, warnings accepted. A counted
    set (counterweight blocks) is listed by how many of it go (`quantity`)."""
    from app.modules.resource_assignments import service as assignments_service
    from app.modules.resource_assignments.schemas import KitAdd, KitPieceInput

    with SessionLocal() as db:
        result = assignments_service.add_kit(
            db,
            public_id=UUID(assignment_public_id),
            payload=KitAdd(
                create_request_key=str(uuid4()),
                expected_assignment_version=assignment_version,
                trip_number=trip_number,
                pieces=[KitPieceInput(piece_public_id=UUID(piece_public_id), quantity=quantity)],
                accept_warnings=True,
            ),
            user_public_id=actor_public_id,
        )
    assignment = result.assignment
    line = next(item for trip in assignment.trips for item in trip.kit if item.piece_public_id == piece_public_id)
    return {"public_id": line.kit_line_public_id, "assignment_version": assignment.assignment_version}


def replace_allocation(
    *,
    actor_public_id: str,
    assignment_public_id: str,
    assignment_version: int,
    machine_public_id: str,
    replace_from: date,
    reason_code: str,
    note: str | None = None,
) -> dict[str, Any]:
    """8A core: replace an allocation's machine from a day through the real service, warnings accepted; the replaced
    allocation stays on the history (TE-7, the Hiring user test's practice data)."""
    from app.modules.resource_assignments import service as assignments_service
    from app.modules.resource_assignments.schemas import AssignmentReplace

    with SessionLocal() as db:
        result = assignments_service.replace_assignment(
            db,
            public_id=UUID(assignment_public_id),
            payload=AssignmentReplace(
                create_request_key=str(uuid4()),
                expected_assignment_version=assignment_version,
                machine_public_id=UUID(machine_public_id),
                replace_from=replace_from,
                reason_code=reason_code,
                note=note,
                accept_warnings=True,
            ),
            user_public_id=actor_public_id,
            may_set_billing_cycle=False,
        )
    assignment = result.assignment
    return {
        "public_id": assignment.assignment_public_id,
        "reference": assignment.assignment_reference,
        "version": assignment.assignment_version,
    }


def free_allocation(
    *, actor_public_id: str, assignment_public_id: str, assignment_version: int, reason_code: str, last_day: date | None = None, note: str | None = None
) -> dict[str, Any]:
    """8A core: free a held machine through the real service; `last_day` empty when it never went to the job
    (TE-7)."""
    from app.modules.resource_assignments import service as assignments_service
    from app.modules.resource_assignments.schemas import AssignmentRelease

    with SessionLocal() as db:
        result = assignments_service.release_assignment(
            db,
            public_id=UUID(assignment_public_id),
            payload=AssignmentRelease(
                expected_assignment_version=assignment_version, last_day=last_day, reason_code=reason_code, note=note
            ),
            user_public_id=actor_public_id,
        )
    assignment = result.assignment
    return {"public_id": assignment.assignment_public_id, "reference": assignment.assignment_reference, "version": assignment.assignment_version}


def add_allocation_trip(
    *, actor_public_id: str, assignment_public_id: str, assignment_version: int, goes_on: date, note: str | None = None
) -> dict[str, Any]:
    """8A core: another Trip (Own Load) for an allocation, through the real service (TE-7)."""
    from app.modules.resource_assignments import service as assignments_service
    from app.modules.resource_assignments.schemas import TripCreate

    with SessionLocal() as db:
        result = assignments_service.add_trip(
            db,
            public_id=UUID(assignment_public_id),
            payload=TripCreate(expected_assignment_version=assignment_version, goes_on=goes_on, note=note),
            user_public_id=actor_public_id,
        )
    assignment = result.assignment
    return {"trip_number": max(trip.trip_number for trip in assignment.trips), "assignment_version": assignment.assignment_version}


def date_equipment_assets_added(*, days_ago_by_asset: dict[str, int]) -> None:
    """TE-7: date machines as added to the Equipment Master some days earlier than they were seeded - each asset
    public id with its number of days - in one UPDATE.

    The one step in this harness that writes a table directly rather than through a service, recorded as a
    deviation in TE_7_HIRING_USER_TEST_PACK.md. A machine is added on the day its Plum report is confirmed (its
    `created_at`), and "A certificate not yet recorded" reaches Operations 7 days after that and Management 14 days
    after (ELG-2, Q19a). Seeded the day before the test, no tester would see those stages for a week or two; dating
    a few machines earlier shows every stage on the first day. Nothing else reads the day a machine was added."""
    assets, days = list(days_ago_by_asset), list(days_ago_by_asset.values())
    with SessionLocal() as db:
        updated = db.execute(
            text(
                "UPDATE equipment_asset AS a SET created_at = a.created_at - make_interval(days => d.days) "
                "FROM unnest(CAST(:assets AS varchar[]), CAST(:days AS integer[])) AS d(asset, days) "
                "WHERE a.asset_public_id = d.asset"
            ),
            {"assets": assets, "days": days},
        ).rowcount
        if updated != len(assets):
            db.rollback()
            raise RuntimeError(f"Dated {updated} of {len(assets)} machines as added earlier; nothing was changed.")
        db.commit()
