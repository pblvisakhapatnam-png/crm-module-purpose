from __future__ import annotations

import hashlib
import os
from datetime import date, timedelta
from decimal import Decimal
from typing import Any, Callable

from app.core.database import SessionLocal

from app.modules.work_orders.contract import WORK_ORDER_LINE_UPKEEP_CELLS
from app.modules.work_orders.service import WorkOrderValidationError
from app.shared import business_time

from .actors import resolve_actor
from .builders import (
    add_account_address,
    add_account_gstin,
    add_amendment_line,
    add_credit_review,
    add_lead_activity,
    add_lead_activity_detailed,
    add_market_rate,
    add_offer_line,
    add_pricing_evidence,
    add_submission_evidence,
    add_work_order_line_billing_terms_period,
    add_equipment_kit,
    allocate_machine,
    equipment_asset_public_id,
    free_harness_calendar_year,
    list_kit_on_trip,
    mark_certificate_not_applicable,
    record_equipment_certificate,
    approve_quote_document,
    attach_recommended_tc_clauses,
    generate_quote_document,
    invented_plum_report,
    log_interaction,
    map_equipment_model_name,
    set_account_tax_profile,
    convert_lead_to_account_opportunity,
    create_account_linked_opportunity,
    create_lead,
    create_lead_detailed,
    create_offer_no_line,
    create_offer_with_line,
    create_related_offer,
    create_equipment_model,
    create_holiday_calendar_year,
    create_resource_requirement,
    create_work_order,
    create_work_order_amendment,
    decide_amendment,
    make_commercial_offer_version,
    mark_offer_submitted,
    qualify_lead,
    record_customer_response,
    select_basis_rate,
    set_work_order_contract_period,
    set_work_order_line_detail,
    require_no_equipment_fleet,
    submit_offer,
    upload_and_publish_equipment_report,
    upload_customer_document,
)
from .manifest import Manifest, new_run_id, utc_now_iso

FRONTEND_BASE_URL = os.environ.get("SMOKE_DATA_FRONTEND_BASE_URL", "http://localhost:3000").rstrip("/")

# Fictional heavy-lift/equipment-hiring customer story used only by the vendor-demo-bundle
# scenario (Slice 6P). Never a real customer, employee, vendor or tender name.
VENDOR_DEMO_CUSTOMER_NAME = "Meridian Bay Refinery Expansion"


def _offer_url(offer_public_id: str) -> str:
    return f"{FRONTEND_BASE_URL}/commercial-offers/{offer_public_id}"


def _work_order_url(work_order_public_id: str) -> str:
    return f"{FRONTEND_BASE_URL}/work-orders/{work_order_public_id}"


def _amendment_url(work_order_public_id: str, amendment_public_id: str) -> str:
    # Anticipates the Part 2 frontend route (not yet built in Part 1), matching the API path.
    return f"{FRONTEND_BASE_URL}/work-orders/{work_order_public_id}/amendments/{amendment_public_id}"


def _lead_url(lead_public_id: str) -> str:
    return f"{FRONTEND_BASE_URL}/leads/{lead_public_id}"


def _account_url(account_public_id: str) -> str:
    return f"{FRONTEND_BASE_URL}/accounts/{account_public_id}"


def _opportunity_url(opportunity_public_id: str) -> str:
    return f"{FRONTEND_BASE_URL}/opportunities/{opportunity_public_id}"


def _build_accepted_offer(
    *,
    run_id: str,
    actor_public_id: str,
    suffix: str,
    with_work_order: bool,
    extra_lines: tuple[dict[str, Any], ...] = (),
) -> dict[str, Any]:
    """An accepted offer with one line, and `extra_lines` (add_offer_line's keyword arguments) added before it is
    submitted: once accepted, its lines cannot change (TB-1 finding TB1-301 (b))."""
    chain = create_account_linked_opportunity(run_id=run_id, actor_public_id=actor_public_id, suffix=suffix)
    offer = create_offer_with_line(
        run_id=run_id,
        actor_public_id=actor_public_id,
        opportunity_public_id=chain["opportunity"]["public_id"],
        suffix=suffix,
    )
    for line in extra_lines:
        add_offer_line(actor_public_id=actor_public_id, offer_public_id=offer["public_id"], **line)
    submit_offer(run_id=run_id, actor_public_id=actor_public_id, offer_public_id=offer["public_id"])
    record_customer_response(
        actor_public_id=actor_public_id, offer_public_id=offer["public_id"], outcome="ACCEPTED_AWARDED"
    )

    record: dict[str, Any] = {
        "account": chain["account"],
        "opportunity": chain["opportunity"],
        "commercial_offer": offer,
        "commercial_offer_status": "ACCEPTED",
        "work_orders": [],
    }
    if with_work_order:
        record["work_orders"].append(
            create_work_order(actor_public_id=actor_public_id, offer_public_id=offer["public_id"])
        )
    return record


def _build_rejected_offer(*, run_id: str, actor_public_id: str, suffix: str) -> dict[str, Any]:
    chain = create_account_linked_opportunity(run_id=run_id, actor_public_id=actor_public_id, suffix=suffix)
    offer = create_offer_with_line(
        run_id=run_id,
        actor_public_id=actor_public_id,
        opportunity_public_id=chain["opportunity"]["public_id"],
        suffix=suffix,
    )
    submit_offer(run_id=run_id, actor_public_id=actor_public_id, offer_public_id=offer["public_id"])
    record_customer_response(
        actor_public_id=actor_public_id, offer_public_id=offer["public_id"], outcome="REJECTED_LOST"
    )
    return {
        "account": chain["account"],
        "opportunity": chain["opportunity"],
        "commercial_offer": offer,
        "commercial_offer_status": "REJECTED",
        "work_orders": [],
    }


def _build_revision_requested_offer(*, run_id: str, actor_public_id: str, suffix: str) -> dict[str, Any]:
    chain = create_account_linked_opportunity(run_id=run_id, actor_public_id=actor_public_id, suffix=suffix)
    offer = create_offer_with_line(
        run_id=run_id,
        actor_public_id=actor_public_id,
        opportunity_public_id=chain["opportunity"]["public_id"],
        suffix=suffix,
    )
    submit_offer(run_id=run_id, actor_public_id=actor_public_id, offer_public_id=offer["public_id"])
    record_customer_response(
        actor_public_id=actor_public_id, offer_public_id=offer["public_id"], outcome="REVISION_REQUESTED"
    )
    return {
        "account": chain["account"],
        "opportunity": chain["opportunity"],
        "commercial_offer": offer,
        "commercial_offer_status": "SUBMITTED",
        "work_orders": [],
    }


def _build_blocked_handoff(*, run_id: str, actor_public_id: str, suffix: str) -> dict[str, Any]:
    """Deliberately stops at SUBMITTED (no customer response yet) and then proves the
    real Work Order handoff guard rejects it. If the guard ever stops rejecting this,
    that is a genuine regression in the handoff precondition, not a harness bug, so
    this raises loudly instead of silently recording a made-up blocker message."""
    chain = create_account_linked_opportunity(run_id=run_id, actor_public_id=actor_public_id, suffix=suffix)
    offer = create_offer_with_line(
        run_id=run_id,
        actor_public_id=actor_public_id,
        opportunity_public_id=chain["opportunity"]["public_id"],
        suffix=suffix,
    )
    submit_offer(run_id=run_id, actor_public_id=actor_public_id, offer_public_id=offer["public_id"])

    try:
        create_work_order(actor_public_id=actor_public_id, offer_public_id=offer["public_id"])
    except WorkOrderValidationError as exc:
        # Narrowed to the specific precondition-violation type the handoff guard raises, so an
        # unrelated failure (DB error, bad public_id, a future exception-type change) surfaces as
        # a real harness crash instead of being silently relabeled as the expected blocker.
        blocked_reason = str(exc)
    else:
        raise RuntimeError(
            "blocked-handoff scenario expected Work Order creation to be rejected while the offer is "
            "SUBMITTED (not yet ACCEPTED), but it succeeded. This indicates a real regression in the "
            "Work Order handoff guard, not a harness bug."
        )

    return {
        "account": chain["account"],
        "opportunity": chain["opportunity"],
        "commercial_offer": offer,
        "commercial_offer_status": "SUBMITTED",
        "work_orders": [],
        "blocked_reason": blocked_reason,
    }


def _build_supplementary_offer_draft(*, run_id: str, actor_public_id: str, suffix: str) -> dict[str, Any]:
    """Accepted Base Offer with no Work Order, plus one DRAFT Supplementary Offer with
    no copied lines/prices/terms/evidence and no automatic Work Order."""
    record = _build_accepted_offer(run_id=run_id, actor_public_id=actor_public_id, suffix=suffix, with_work_order=False)
    related_offer = create_related_offer(
        run_id=run_id,
        actor_public_id=actor_public_id,
        base_offer_public_id=record["commercial_offer"]["public_id"],
        offer_purpose="SUPPLEMENTARY",
        related_work_order_public_id=None,
        customer_request_summary="Customer requested one additional line against the same enquiry.",
    )
    record["related_offers"] = [related_offer]
    return record


def _build_change_quotation_draft(*, run_id: str, actor_public_id: str, suffix: str) -> dict[str, Any]:
    """Accepted Base Offer with an existing Work Order, plus one DRAFT Change Quotation
    linked to that Work Order. No Work Order Amendment is created."""
    record = _build_accepted_offer(run_id=run_id, actor_public_id=actor_public_id, suffix=suffix, with_work_order=True)
    work_order_public_id = record["work_orders"][0]["public_id"]
    related_offer = create_related_offer(
        run_id=run_id,
        actor_public_id=actor_public_id,
        base_offer_public_id=record["commercial_offer"]["public_id"],
        offer_purpose="CHANGE_QUOTATION",
        related_work_order_public_id=work_order_public_id,
        customer_request_summary="Customer requested a revised price before a Work Order amendment.",
    )
    record["related_offers"] = [related_offer]
    return record


def _build_supplementary_offer_lifecycle(*, run_id: str, actor_public_id: str, suffix: str) -> dict[str, Any]:
    """Accepted Base Offer (unchanged throughout) plus a Supplementary Offer taken through
    its own independent lifecycle: line -> submitted -> accepted. Proves the related offer's
    lifecycle never mutates the Base Offer and creates no Work Order automatically."""
    record = _build_accepted_offer(run_id=run_id, actor_public_id=actor_public_id, suffix=suffix, with_work_order=False)
    related_offer = create_related_offer(
        run_id=run_id,
        actor_public_id=actor_public_id,
        base_offer_public_id=record["commercial_offer"]["public_id"],
        offer_purpose="SUPPLEMENTARY",
        related_work_order_public_id=None,
        customer_request_summary="Customer requested additional scope, taken through its own lifecycle.",
    )
    add_offer_line(actor_public_id=actor_public_id, offer_public_id=related_offer["public_id"])
    submit_offer(run_id=run_id, actor_public_id=actor_public_id, offer_public_id=related_offer["public_id"])
    record_customer_response(
        actor_public_id=actor_public_id, offer_public_id=related_offer["public_id"], outcome="ACCEPTED_AWARDED"
    )
    related_offer["commercial_offer_status"] = "ACCEPTED"
    record["related_offers"] = [related_offer]
    return record


def _build_opportunity_with_multiple_related_offers(*, run_id: str, actor_public_id: str, suffix: str) -> dict[str, Any]:
    """One accepted Base Offer with an existing Work Order, plus one distinct Supplementary
    Offer and one distinct Change Quotation - so the Opportunity shows three separate offer
    series (BASE, SUPPLEMENTARY, CHANGE_QUOTATION), none of which are revisions of each other."""
    record = _build_accepted_offer(run_id=run_id, actor_public_id=actor_public_id, suffix=suffix, with_work_order=True)
    work_order_public_id = record["work_orders"][0]["public_id"]
    supplementary = create_related_offer(
        run_id=run_id,
        actor_public_id=actor_public_id,
        base_offer_public_id=record["commercial_offer"]["public_id"],
        offer_purpose="SUPPLEMENTARY",
        related_work_order_public_id=None,
        customer_request_summary="First, distinct additional-scope request for regression coverage.",
    )
    change_quotation = create_related_offer(
        run_id=run_id,
        actor_public_id=actor_public_id,
        base_offer_public_id=record["commercial_offer"]["public_id"],
        offer_purpose="CHANGE_QUOTATION",
        related_work_order_public_id=work_order_public_id,
        customer_request_summary="Second, distinct change-quotation request for regression coverage.",
    )
    record["related_offers"] = [supplementary, change_quotation]
    return record


def _build_work_order_amendment_received(*, run_id: str, actor_public_id: str, suffix: str) -> dict[str, Any]:
    """Accepted Base Offer with a Work Order shell, plus one ADMINISTRATIVE amendment left
    in RECEIVED status with a clear customer reference and summary. No Work Order mutation."""
    record = _build_accepted_offer(run_id=run_id, actor_public_id=actor_public_id, suffix=suffix, with_work_order=True)
    work_order_public_id = record["work_orders"][0]["public_id"]
    amendment = create_work_order_amendment(
        run_id=run_id,
        actor_public_id=actor_public_id,
        work_order_public_id=work_order_public_id,
        amendment_type_code="ADMINISTRATIVE",
    )
    record["amendments"] = [amendment]
    return record


def _build_commercial_amendment_with_change_quotation(*, run_id: str, actor_public_id: str, suffix: str) -> dict[str, Any]:
    """Accepted Base Offer with a Work Order, an accepted Change Quotation linked to that
    Work Order, and a Commercial amendment (with one amendment line) taken all the way to
    VALIDATED - proving the original Work Order and its lines remain unchanged throughout."""
    record = _build_accepted_offer(run_id=run_id, actor_public_id=actor_public_id, suffix=suffix, with_work_order=True)
    work_order_public_id = record["work_orders"][0]["public_id"]

    change_quotation = create_related_offer(
        run_id=run_id,
        actor_public_id=actor_public_id,
        base_offer_public_id=record["commercial_offer"]["public_id"],
        offer_purpose="CHANGE_QUOTATION",
        related_work_order_public_id=work_order_public_id,
        customer_request_summary="Customer requested a revised price before a Work Order amendment.",
    )
    add_offer_line(actor_public_id=actor_public_id, offer_public_id=change_quotation["public_id"])
    submit_offer(run_id=run_id, actor_public_id=actor_public_id, offer_public_id=change_quotation["public_id"])
    record_customer_response(
        actor_public_id=actor_public_id, offer_public_id=change_quotation["public_id"], outcome="ACCEPTED_AWARDED"
    )
    change_quotation["commercial_offer_status"] = "ACCEPTED"
    record["related_offers"] = [change_quotation]

    amendment = create_work_order_amendment(
        run_id=run_id,
        actor_public_id=actor_public_id,
        work_order_public_id=work_order_public_id,
        amendment_type_code="COMMERCIAL",
        commercial_change_summary="Revise the day rate per the accepted Change Quotation.",
        related_commercial_offer_public_id=change_quotation["public_id"],
    )
    add_amendment_line(
        actor_public_id=actor_public_id,
        work_order_public_id=work_order_public_id,
        amendment_public_id=amendment["public_id"],
    )
    decide_amendment(
        actor_public_id=actor_public_id,
        work_order_public_id=work_order_public_id,
        amendment_public_id=amendment["public_id"],
        target_status_code="UNDER_REVIEW",
    )
    decide_amendment(
        actor_public_id=actor_public_id,
        work_order_public_id=work_order_public_id,
        amendment_public_id=amendment["public_id"],
        target_status_code="VALIDATED",
    )
    amendment["amendment_status_code"] = "VALIDATED"
    record["amendments"] = [amendment]
    return record


def _build_commercial_amendment_create_target(*, run_id: str, actor_public_id: str, suffix: str) -> dict[str, Any]:
    """Accepted Base Offer with a Work Order and an accepted Change Quotation linked to it,
    but with no amendment yet - so Part 2 Playwright coverage can interactively create,
    line-propose and validate a Commercial amendment end-to-end through the UI (distinct
    from commercial_amendment_with_basis above, which is already taken to VALIDATED)."""
    record = _build_accepted_offer(run_id=run_id, actor_public_id=actor_public_id, suffix=suffix, with_work_order=True)
    work_order_public_id = record["work_orders"][0]["public_id"]

    change_quotation = create_related_offer(
        run_id=run_id,
        actor_public_id=actor_public_id,
        base_offer_public_id=record["commercial_offer"]["public_id"],
        offer_purpose="CHANGE_QUOTATION",
        related_work_order_public_id=work_order_public_id,
        customer_request_summary="Customer requested a revised price for interactive amendment testing.",
    )
    add_offer_line(actor_public_id=actor_public_id, offer_public_id=change_quotation["public_id"])
    submit_offer(run_id=run_id, actor_public_id=actor_public_id, offer_public_id=change_quotation["public_id"])
    record_customer_response(
        actor_public_id=actor_public_id, offer_public_id=change_quotation["public_id"], outcome="ACCEPTED_AWARDED"
    )
    change_quotation["commercial_offer_status"] = "ACCEPTED"
    record["related_offers"] = [change_quotation]
    record["amendments"] = []
    return record


def _build_blocked_validation_target(*, run_id: str, actor_public_id: str, suffix: str) -> dict[str, Any]:
    """Accepted Base Offer with a Work Order, a DRAFT (not yet accepted) Change Quotation
    linked to it, and a COMMERCIAL amendment citing that Change Quotation as its commercial
    basis, moved to UNDER_REVIEW with one amendment line already proposed. Validation is
    blocked only by the basis not being Accepted yet - proving the readiness/blocking-reason
    UI without a hand-scripted fake blocker."""
    record = _build_accepted_offer(run_id=run_id, actor_public_id=actor_public_id, suffix=suffix, with_work_order=True)
    work_order_public_id = record["work_orders"][0]["public_id"]

    change_quotation = create_related_offer(
        run_id=run_id,
        actor_public_id=actor_public_id,
        base_offer_public_id=record["commercial_offer"]["public_id"],
        offer_purpose="CHANGE_QUOTATION",
        related_work_order_public_id=work_order_public_id,
        customer_request_summary="Customer requested a revised price; basis not yet accepted.",
    )
    record["related_offers"] = [change_quotation]

    amendment = create_work_order_amendment(
        run_id=run_id,
        actor_public_id=actor_public_id,
        work_order_public_id=work_order_public_id,
        amendment_type_code="COMMERCIAL",
        commercial_change_summary="Revise the day rate pending Change Quotation acceptance.",
        related_commercial_offer_public_id=change_quotation["public_id"],
    )
    add_amendment_line(
        actor_public_id=actor_public_id,
        work_order_public_id=work_order_public_id,
        amendment_public_id=amendment["public_id"],
    )
    decide_amendment(
        actor_public_id=actor_public_id,
        work_order_public_id=work_order_public_id,
        amendment_public_id=amendment["public_id"],
        target_status_code="UNDER_REVIEW",
    )
    amendment["amendment_status_code"] = "UNDER_REVIEW"
    record["amendments"] = [amendment]
    return record


def _build_work_order_amendment_regression_bundle(*, run_id: str, actor_public_id: str) -> dict[str, Any]:
    """Independent record sets for future Playwright coverage of Slice 6O.2, mirroring the
    core-regression-bundle isolation principle - no two Playwright tests mutate the same
    Work Order or amendment."""
    administrative_create_target = _build_accepted_offer(
        run_id=run_id, actor_public_id=actor_public_id, suffix="AmdAdminCreate", with_work_order=True
    )

    commercial_with_basis = _build_commercial_amendment_with_change_quotation(
        run_id=run_id, actor_public_id=actor_public_id, suffix="AmdCommercialBasis"
    )

    line_delta_target = _build_accepted_offer(
        run_id=run_id, actor_public_id=actor_public_id, suffix="AmdLineDelta", with_work_order=True
    )
    line_delta_amendment = create_work_order_amendment(
        run_id=run_id,
        actor_public_id=actor_public_id,
        work_order_public_id=line_delta_target["work_orders"][0]["public_id"],
        amendment_type_code="ADMINISTRATIVE",
    )
    line_delta_target["amendments"] = [line_delta_amendment]

    read_only_view = _build_work_order_amendment_received(
        run_id=run_id, actor_public_id=actor_public_id, suffix="AmdReadOnly"
    )

    terminal_display = _build_accepted_offer(
        run_id=run_id, actor_public_id=actor_public_id, suffix="AmdTerminal", with_work_order=True
    )
    terminal_amendment = create_work_order_amendment(
        run_id=run_id,
        actor_public_id=actor_public_id,
        work_order_public_id=terminal_display["work_orders"][0]["public_id"],
        amendment_type_code="ADMINISTRATIVE",
    )
    decide_amendment(
        actor_public_id=actor_public_id,
        work_order_public_id=terminal_display["work_orders"][0]["public_id"],
        amendment_public_id=terminal_amendment["public_id"],
        target_status_code="REJECTED",
        reason="Customer withdrew the request.",
    )
    terminal_amendment["amendment_status_code"] = "REJECTED"
    terminal_display["amendments"] = [terminal_amendment]

    commercial_create_target = _build_commercial_amendment_create_target(
        run_id=run_id, actor_public_id=actor_public_id, suffix="AmdCommercialCreate"
    )

    blocked_validation_target = _build_blocked_validation_target(
        run_id=run_id, actor_public_id=actor_public_id, suffix="AmdBlockedValidation"
    )

    return {
        "administrative_amendment_create_target": administrative_create_target,
        "commercial_amendment_with_basis": commercial_with_basis,
        "line_delta_target": line_delta_target,
        "amendment_read_only_view": read_only_view,
        "terminal_amendment_display": terminal_display,
        "commercial_amendment_create_target": commercial_create_target,
        "blocked_validation_target": blocked_validation_target,
    }


def _demo_meta(
    *,
    track: str,
    purpose: str,
    interactive: bool,
    presenter_role: str,
    presenter_action: str,
    expected_result: str,
    fallback_of: str | None = None,
) -> dict[str, Any]:
    """Backward-compatible, additive manifest metadata used only by the Slice 6P
    vendor-demo-bundle scenario. Existing manifest consumers (cleanup, Playwright fixtures,
    prior scenarios' tests) never read this key and are unaffected by its presence."""
    return {
        "track": track,
        "fictional_customer": VENDOR_DEMO_CUSTOMER_NAME,
        "purpose": purpose,
        "interactive": interactive,
        "fallback_of": fallback_of,
        "presenter_role": presenter_role,
        "presenter_action": presenter_action,
        "expected_result": expected_result,
    }


def _build_lead_interactive(*, run_id: str, actor_public_id: str, suffix: str) -> dict[str, Any]:
    """Track A: a Lead left in NEW status with one activity recorded, ready for a presenter to
    qualify and convert live. Never qualifies or converts itself - that is the interactive step."""
    lead = create_lead(run_id=run_id, actor_public_id=actor_public_id, suffix=suffix)
    activity = add_lead_activity(actor_public_id=actor_public_id, lead_public_id=lead["public_id"])
    return {"lead": lead, "activities": [activity]}


def _build_lead_fallback_converted(*, run_id: str, actor_public_id: str, suffix: str) -> dict[str, Any]:
    """Track A fallback: same Lead shape as _build_lead_interactive, but already qualified and
    converted to Account + Opportunity, for a presenter who wants to skip ahead or recover."""
    lead = create_lead(run_id=run_id, actor_public_id=actor_public_id, suffix=suffix)
    activity = add_lead_activity(actor_public_id=actor_public_id, lead_public_id=lead["public_id"])
    qualify_lead(actor_public_id=actor_public_id, lead_public_id=lead["public_id"], decision_status_code="QUALIFIED")
    conversion = convert_lead_to_account_opportunity(actor_public_id=actor_public_id, lead_public_id=lead["public_id"])
    lead["lead_status_code"] = "CONVERTED"
    return {
        "lead": lead,
        "activities": [activity],
        "account": conversion["account"],
        "opportunity": conversion["opportunity"],
    }


def _build_offer_ready_to_submit(*, run_id: str, actor_public_id: str, suffix: str) -> dict[str, Any]:
    """Track B interactive: an offer with lines, pricing evidence, recommended header T&C,
    submission evidence and a clean credit review already in place, but NOT yet marked
    Submitted - ready for a presenter to click Mark Submitted live."""
    chain = create_account_linked_opportunity(run_id=run_id, actor_public_id=actor_public_id, suffix=suffix)
    offer = create_offer_with_line(
        run_id=run_id, actor_public_id=actor_public_id, opportunity_public_id=chain["opportunity"]["public_id"], suffix=suffix
    )
    add_pricing_evidence(
        actor_public_id=actor_public_id, offer_public_id=offer["public_id"], line_public_id=offer["line_public_id"]
    )
    attach_recommended_tc_clauses(actor_public_id=actor_public_id, offer_public_id=offer["public_id"], recommendation_basis="HIRING")
    add_submission_evidence(actor_public_id=actor_public_id, offer_public_id=offer["public_id"])
    add_credit_review(actor_public_id=actor_public_id, offer_public_id=offer["public_id"])
    return {
        "account": chain["account"],
        "opportunity": chain["opportunity"],
        "commercial_offer": offer,
        "commercial_offer_status": "DRAFT",
        "work_orders": [],
    }


def _build_offer_fallback_submitted(*, run_id: str, actor_public_id: str, suffix: str) -> dict[str, Any]:
    """Track B fallback: identical preparation to _build_offer_ready_to_submit, already
    marked Submitted, for a presenter who wants to skip ahead."""
    chain = create_account_linked_opportunity(run_id=run_id, actor_public_id=actor_public_id, suffix=suffix)
    offer = create_offer_with_line(
        run_id=run_id, actor_public_id=actor_public_id, opportunity_public_id=chain["opportunity"]["public_id"], suffix=suffix
    )
    add_pricing_evidence(
        actor_public_id=actor_public_id, offer_public_id=offer["public_id"], line_public_id=offer["line_public_id"]
    )
    attach_recommended_tc_clauses(actor_public_id=actor_public_id, offer_public_id=offer["public_id"], recommendation_basis="HIRING")
    submit_offer(run_id=run_id, actor_public_id=actor_public_id, offer_public_id=offer["public_id"])
    return {
        "account": chain["account"],
        "opportunity": chain["opportunity"],
        "commercial_offer": offer,
        "commercial_offer_status": "SUBMITTED",
        "work_orders": [],
    }


def _build_offer_blocker_no_active_line(*, run_id: str, actor_public_id: str, suffix: str) -> dict[str, Any]:
    """Track B blocker: an offer with zero lines. Demonstrates the real, backend-enforced
    'at least one active line' precondition (submission readiness / mark-submitted rejection),
    never a fabricated UI-only message."""
    chain = create_account_linked_opportunity(run_id=run_id, actor_public_id=actor_public_id, suffix=suffix)
    offer = create_offer_no_line(
        run_id=run_id, actor_public_id=actor_public_id, opportunity_public_id=chain["opportunity"]["public_id"], suffix=suffix
    )
    return {
        "account": chain["account"],
        "opportunity": chain["opportunity"],
        "commercial_offer": offer,
        "commercial_offer_status": "DRAFT",
        "work_orders": [],
    }


def _build_on_hold_offer(*, run_id: str, actor_public_id: str, suffix: str) -> dict[str, Any]:
    """Track D: submitted offer recorded as ON_HOLD (status stays SUBMITTED, matching the
    Slice 6L 'other outcomes preserve status' rule)."""
    chain = create_account_linked_opportunity(run_id=run_id, actor_public_id=actor_public_id, suffix=suffix)
    offer = create_offer_with_line(
        run_id=run_id, actor_public_id=actor_public_id, opportunity_public_id=chain["opportunity"]["public_id"], suffix=suffix
    )
    submit_offer(run_id=run_id, actor_public_id=actor_public_id, offer_public_id=offer["public_id"])
    record_customer_response(actor_public_id=actor_public_id, offer_public_id=offer["public_id"], outcome="ON_HOLD")
    return {
        "account": chain["account"],
        "opportunity": chain["opportunity"],
        "commercial_offer": offer,
        "commercial_offer_status": "SUBMITTED",
        "work_orders": [],
    }


def _build_revised_resubmitted_offer(*, run_id: str, actor_public_id: str, suffix: str) -> dict[str, Any]:
    """Track D: immutable v1 submitted, then copied to an independently submitted v2."""
    chain = create_account_linked_opportunity(run_id=run_id, actor_public_id=actor_public_id, suffix=suffix)
    offer = create_offer_with_line(
        run_id=run_id, actor_public_id=actor_public_id, opportunity_public_id=chain["opportunity"]["public_id"], suffix=suffix
    )
    submit_offer(run_id=run_id, actor_public_id=actor_public_id, offer_public_id=offer["public_id"])
    version = make_commercial_offer_version(actor_public_id=actor_public_id, offer_public_id=offer["public_id"])
    submit_offer(run_id=run_id, actor_public_id=actor_public_id, offer_public_id=version["public_id"])
    return {
        "account": chain["account"],
        "opportunity": chain["opportunity"],
        "commercial_offer": version,
        "commercial_offer_status": "SUBMITTED",
        "work_orders": [],
        "offer_versions": [offer, version],
    }


def _build_related_offers_chain(*, run_id: str, actor_public_id: str, suffix: str) -> dict[str, Any]:
    """Track E: accepted Base Offer + Work Order (unchanged throughout), one Draft
    Supplementary Offer, and one Change Quotation taken to ACCEPTED - so the accepted Change
    Quotation is available as a commercial basis for the Track F amendment scenarios."""
    record = _build_accepted_offer(run_id=run_id, actor_public_id=actor_public_id, suffix=suffix, with_work_order=True)
    work_order_public_id = record["work_orders"][0]["public_id"]

    supplementary = create_related_offer(
        run_id=run_id,
        actor_public_id=actor_public_id,
        base_offer_public_id=record["commercial_offer"]["public_id"],
        offer_purpose="SUPPLEMENTARY",
        related_work_order_public_id=None,
        customer_request_summary="Customer requested additional lifting scope for the refinery expansion (vendor demo).",
    )
    change_quotation = create_related_offer(
        run_id=run_id,
        actor_public_id=actor_public_id,
        base_offer_public_id=record["commercial_offer"]["public_id"],
        offer_purpose="CHANGE_QUOTATION",
        related_work_order_public_id=work_order_public_id,
        customer_request_summary="Customer requested a revised day rate before a Work Order amendment (vendor demo).",
    )
    add_offer_line(actor_public_id=actor_public_id, offer_public_id=change_quotation["public_id"])
    submit_offer(run_id=run_id, actor_public_id=actor_public_id, offer_public_id=change_quotation["public_id"])
    record_customer_response(
        actor_public_id=actor_public_id, offer_public_id=change_quotation["public_id"], outcome="ACCEPTED_AWARDED"
    )
    change_quotation["commercial_offer_status"] = "ACCEPTED"
    record["related_offers"] = [supplementary, change_quotation]
    return record


def _build_amendment_commercial_interactive(*, run_id: str, actor_public_id: str, suffix: str) -> dict[str, Any]:
    """Track F interactive: accepted Base Offer + Work Order + an accepted Change Quotation as
    commercial basis + a Commercial amendment with one line, moved to UNDER_REVIEW - ready for a
    presenter to click Validate live. Distinct from
    _build_commercial_amendment_with_change_quotation, which is already taken to VALIDATED."""
    record = _build_accepted_offer(run_id=run_id, actor_public_id=actor_public_id, suffix=suffix, with_work_order=True)
    work_order_public_id = record["work_orders"][0]["public_id"]

    change_quotation = create_related_offer(
        run_id=run_id,
        actor_public_id=actor_public_id,
        base_offer_public_id=record["commercial_offer"]["public_id"],
        offer_purpose="CHANGE_QUOTATION",
        related_work_order_public_id=work_order_public_id,
        customer_request_summary="Customer requested a revised day rate before a Work Order amendment (vendor demo).",
    )
    add_offer_line(actor_public_id=actor_public_id, offer_public_id=change_quotation["public_id"])
    submit_offer(run_id=run_id, actor_public_id=actor_public_id, offer_public_id=change_quotation["public_id"])
    record_customer_response(
        actor_public_id=actor_public_id, offer_public_id=change_quotation["public_id"], outcome="ACCEPTED_AWARDED"
    )
    change_quotation["commercial_offer_status"] = "ACCEPTED"
    record["related_offers"] = [change_quotation]

    amendment = create_work_order_amendment(
        run_id=run_id,
        actor_public_id=actor_public_id,
        work_order_public_id=work_order_public_id,
        amendment_type_code="COMMERCIAL",
        commercial_change_summary="Revise the day rate per the accepted Change Quotation (vendor demo).",
        related_commercial_offer_public_id=change_quotation["public_id"],
    )
    add_amendment_line(
        actor_public_id=actor_public_id, work_order_public_id=work_order_public_id, amendment_public_id=amendment["public_id"]
    )
    decide_amendment(
        actor_public_id=actor_public_id,
        work_order_public_id=work_order_public_id,
        amendment_public_id=amendment["public_id"],
        target_status_code="UNDER_REVIEW",
    )
    amendment["amendment_status_code"] = "UNDER_REVIEW"
    record["amendments"] = [amendment]
    return record


def scenario_vendor_demo_bundle(run_id: str, actor: dict[str, str]) -> dict[str, Any]:
    """Slice 6P vendor-demo scenario bundle. Reuses the exact same builders/service-layer
    actions as every other TE-1 scenario - no status bypass, no fabricated blocker other than
    the genuine zero-active-line precondition. Every live-mutation record has a paired,
    already-completed fallback record so a presenter can recover if a step is performed early,
    skipped, or the browser session is lost. Fictional customer story only: no real customer,
    employee, vendor or tender data. Every record still uses the existing account/opportunity/
    commercial_offer/work_orders/related_offers/amendments manifest shape, so the existing
    cleanup ownership-discovery logic (cleanup.py) requires no change to clean this bundle up."""
    actor_public_id = actor["public_id"]

    records: dict[str, Any] = {
        "lead_interactive": {
            **_build_lead_interactive(run_id=run_id, actor_public_id=actor_public_id, suffix="DemoLeadReady"),
            "demo_meta": _demo_meta(
                track="A",
                purpose="Lead ready for the presenter to qualify and convert live.",
                interactive=True,
                presenter_role="Sales User",
                presenter_action="Record a Qualified decision, then Convert to Account + Opportunity.",
                expected_result=(
                    "Lead status becomes CONVERTED; a new Account (Qualified Prospect) and Opportunity "
                    "are created and linked back to this Lead."
                ),
            ),
        },
        "lead_fallback_converted": {
            **_build_lead_fallback_converted(run_id=run_id, actor_public_id=actor_public_id, suffix="DemoLeadFallback"),
            "demo_meta": _demo_meta(
                track="A",
                purpose="Already-qualified and converted Lead for fallback/reference.",
                interactive=False,
                presenter_role="Sales User",
                presenter_action="View only (fallback).",
                expected_result="Lead already shows CONVERTED with linked Account/Opportunity.",
                fallback_of="lead_interactive",
            ),
        },
        "offer_ready_to_submit": {
            **_build_offer_ready_to_submit(run_id=run_id, actor_public_id=actor_public_id, suffix="DemoOfferReady"),
            "demo_meta": _demo_meta(
                track="B",
                purpose=(
                    "Base Offer fully prepared (lines, pricing evidence, recommended header T&C, "
                    "submission evidence, clean credit review) but not yet marked Submitted."
                ),
                interactive=True,
                presenter_role="Sales User",
                presenter_action="Open the Submission tab and click Mark Submitted.",
                expected_result="Offer status becomes Submitted / commercially committed.",
            ),
        },
        "offer_fallback_submitted": {
            **_build_offer_fallback_submitted(run_id=run_id, actor_public_id=actor_public_id, suffix="DemoOfferFallback"),
            "demo_meta": _demo_meta(
                track="B",
                purpose="Same preparation as offer_ready_to_submit, already marked Submitted, for fallback.",
                interactive=False,
                presenter_role="Sales User",
                presenter_action="View only (fallback).",
                expected_result="Offer already shows Submitted / commercially committed.",
                fallback_of="offer_ready_to_submit",
            ),
        },
        "offer_blocker_no_active_line": {
            **_build_offer_blocker_no_active_line(run_id=run_id, actor_public_id=actor_public_id, suffix="DemoOfferBlocker"),
            "demo_meta": _demo_meta(
                track="B",
                purpose="Genuine backend-enforced blocker: offer has zero active lines.",
                interactive=True,
                presenter_role="Sales User",
                presenter_action="Open Submission Readiness (or attempt Mark Submitted).",
                expected_result=(
                    "Submission Readiness reports NOT_READY / mark-submitted is rejected because no "
                    "active offer line exists yet - a real backend guard, not a scripted UI message."
                ),
            ),
        },
        "offer_accepted_no_wo": {
            **_build_accepted_offer(run_id=run_id, actor_public_id=actor_public_id, suffix="DemoAcceptedNoWo", with_work_order=False),
            "demo_meta": _demo_meta(
                track="C",
                purpose="Accepted/awarded offer with no Work Order shell yet.",
                interactive=True,
                presenter_role="Sales User",
                presenter_action="Create Work Order shell.",
                expected_result=(
                    "A new Work Order shell is created, preserving source offer-line traceability. "
                    "No Work Order is created automatically before this explicit action."
                ),
            ),
        },
        "offer_accepted_with_wo": {
            **_build_accepted_offer(run_id=run_id, actor_public_id=actor_public_id, suffix="DemoAcceptedWithWo", with_work_order=True),
            "demo_meta": _demo_meta(
                track="C",
                purpose="Accepted/awarded offer with the frozen handoff already performed, for traceability/fallback.",
                interactive=False,
                presenter_role="Sales User / Management Read Only",
                presenter_action="Open the linked Work Order shell and review provenance/line traceability.",
                expected_result=(
                    "Work Order shell already exists; Commercial Offer <-> Work Order navigation and "
                    "line traceability are visible."
                ),
                fallback_of="offer_accepted_no_wo",
            ),
        },
        "offer_revision_requested": {
            **_build_revision_requested_offer(run_id=run_id, actor_public_id=actor_public_id, suffix="DemoRevisionRequested"),
            "demo_meta": _demo_meta(
                track="D",
                purpose="Submitted offer with a Revision Requested customer response.",
                interactive=False,
                presenter_role="Sales User",
                presenter_action="View lifecycle guidance / customer response history.",
                expected_result="Offer stays Submitted; lifecycle guidance shows Revision Requested as the latest customer response.",
            ),
        },
        "offer_rejected": {
            **_build_rejected_offer(run_id=run_id, actor_public_id=actor_public_id, suffix="DemoRejected"),
            "demo_meta": _demo_meta(
                track="D",
                purpose="Submitted offer recorded as Rejected/Lost.",
                interactive=False,
                presenter_role="Sales User",
                presenter_action="View lifecycle guidance / terminal status guard.",
                expected_result="Offer status is Rejected (terminal); generic status edit is blocked, matching the Slice 6M.1 guard.",
            ),
        },
        "offer_on_hold": {
            **_build_on_hold_offer(run_id=run_id, actor_public_id=actor_public_id, suffix="DemoOnHold"),
            "demo_meta": _demo_meta(
                track="D",
                purpose="Submitted offer recorded as On Hold.",
                interactive=False,
                presenter_role="Sales User",
                presenter_action="View lifecycle guidance.",
                expected_result="Offer stays Submitted; lifecycle guidance shows On Hold as the latest customer response.",
            ),
        },
        "offer_revised_resubmitted": {
            **_build_revised_resubmitted_offer(run_id=run_id, actor_public_id=actor_public_id, suffix="DemoRevised"),
            "demo_meta": _demo_meta(
                track="D",
                purpose="Submitted Commercial Offer v1 replaced by independently submitted v2 (Slice 9F).",
                interactive=False,
                presenter_role="Sales User",
                presenter_action="View the Commercial Offer version history.",
                expected_result=(
                    "Version history shows v1 as Replaced and v2 as Submitted, with separate submission evidence."
                ),
            ),
        },
        "related_offers_chain": {
            **_build_related_offers_chain(run_id=run_id, actor_public_id=actor_public_id, suffix="DemoRelatedOffers"),
            "demo_meta": _demo_meta(
                track="E",
                purpose="Accepted Base Offer + Work Order, one Draft Supplementary Offer, one accepted Change Quotation.",
                interactive=False,
                presenter_role="Sales User",
                presenter_action="Open the Opportunity or Work Order to view all three offer-purpose badges.",
                expected_result=(
                    "Base Offer and original Work Order are unchanged; Supplementary Offer and Change "
                    "Quotation each show their own independent lifecycle."
                ),
            ),
        },
        "amendment_administrative_received": {
            **_build_work_order_amendment_received(run_id=run_id, actor_public_id=actor_public_id, suffix="DemoAmendmentAdmin"),
            "demo_meta": _demo_meta(
                track="F",
                purpose="Administrative Work Order Amendment left in Received status.",
                interactive=False,
                presenter_role="Operations User / Sales User",
                presenter_action="Open the Work Order Amendments section.",
                expected_result="Amendment shows type Administrative, status Received, with original values captured at proposal time.",
            ),
        },
        "amendment_commercial_interactive": {
            **_build_amendment_commercial_interactive(run_id=run_id, actor_public_id=actor_public_id, suffix="DemoAmendmentInteractive"),
            "demo_meta": _demo_meta(
                track="F",
                purpose="Commercial Amendment citing an accepted Change Quotation, moved to Under Review, ready to Validate.",
                interactive=True,
                presenter_role="Operations User / Sales User",
                presenter_action="Open the amendment detail page and click Validate.",
                expected_result=(
                    "Amendment status becomes Validated. The advisory clearly states Validated does not "
                    "mean applied - the Work Order and its lines remain unchanged."
                ),
            ),
        },
        "amendment_commercial_fallback_validated": {
            **_build_commercial_amendment_with_change_quotation(
                run_id=run_id, actor_public_id=actor_public_id, suffix="DemoAmendmentFallback"
            ),
            "demo_meta": _demo_meta(
                track="F",
                purpose="Same shape as amendment_commercial_interactive, already Validated, for fallback/reference.",
                interactive=False,
                presenter_role="Operations User / Sales User / Management Read Only",
                presenter_action="View only (fallback); also usable for Track G role-visibility demonstration.",
                expected_result="Amendment already shows Validated; Work Order and its lines are unchanged.",
                fallback_of="amendment_commercial_interactive",
            ),
        },
    }
    return records


def scenario_accepted_offer_no_work_order(run_id: str, actor: dict[str, str]) -> dict[str, Any]:
    return {
        "handoff_target": _build_accepted_offer(
            run_id=run_id, actor_public_id=actor["public_id"], suffix="A", with_work_order=False
        )
    }


def scenario_accepted_offer_with_work_order(run_id: str, actor: dict[str, str]) -> dict[str, Any]:
    return {
        "accepted_with_work_order": _build_accepted_offer(
            run_id=run_id, actor_public_id=actor["public_id"], suffix="B", with_work_order=True
        )
    }


def scenario_rejected_offer(run_id: str, actor: dict[str, str]) -> dict[str, Any]:
    return {"rejected_offer": _build_rejected_offer(run_id=run_id, actor_public_id=actor["public_id"], suffix="C")}


def scenario_revision_requested(run_id: str, actor: dict[str, str]) -> dict[str, Any]:
    return {
        "revision_requested": _build_revision_requested_offer(
            run_id=run_id, actor_public_id=actor["public_id"], suffix="D"
        )
    }


def scenario_blocked_handoff(run_id: str, actor: dict[str, str]) -> dict[str, Any]:
    return {"blocked_handoff": _build_blocked_handoff(run_id=run_id, actor_public_id=actor["public_id"], suffix="E")}


def _build_document_upload_target(*, run_id: str, actor_public_id: str, suffix: str) -> dict[str, Any]:
    """An Account, an Opportunity linked to it, and a DRAFT Commercial Offer with one active line.

    Nothing is submitted, awarded or handed off: the upload-rights Playwright spec only needs an
    Account and an offer to attach files to, and attaching a file changes neither. Those files
    arrive after seeding, so the manifest never names them; cleanup finds them through the
    (linked_record_type, public_id) pairs of the records it owns and deletes their stored bytes
    too (cleanup._owned_record_pairs)."""
    return _build_draft_offer_with_line(run_id=run_id, actor_public_id=actor_public_id, suffix=suffix)


def _build_draft_offer_with_line(*, run_id: str, actor_public_id: str, suffix: str) -> dict[str, Any]:
    """An Account, an Opportunity linked to it, and a DRAFT Commercial Offer with one active line, all still open to
    change."""
    chain = create_account_linked_opportunity(run_id=run_id, actor_public_id=actor_public_id, suffix=suffix)
    offer = create_offer_with_line(
        run_id=run_id,
        actor_public_id=actor_public_id,
        opportunity_public_id=chain["opportunity"]["public_id"],
        suffix=suffix,
    )
    return {
        "account": chain["account"],
        "opportunity": chain["opportunity"],
        "commercial_offer": offer,
        "commercial_offer_status": "DRAFT",
        "work_orders": [],
    }


def _build_submitted_offer_with_line(*, run_id: str, actor_public_id: str, suffix: str) -> dict[str, Any]:
    """A draft offer with one line, then submitted: its content can change only on a new version (Slice 9F)."""
    record = _build_draft_offer_with_line(run_id=run_id, actor_public_id=actor_public_id, suffix=suffix)
    submit_offer(run_id=run_id, actor_public_id=actor_public_id, offer_public_id=record["commercial_offer"]["public_id"])
    record["commercial_offer_status"] = "SUBMITTED"
    return record


def scenario_core_regression_bundle(run_id: str, actor: dict[str, str]) -> dict[str, Any]:
    """Twelve independent record sets so the Playwright suite never has two tests
    mutating the same Commercial Offer: a target for the create-Work-Order test, a
    rejected offer for the terminal-status UI guard, two separate accepted+WO
    offers for the traceability and read-only-role tests, a DRAFT offer whose
    Account and offer the upload-rights test attaches files to, an accepted+WO
    offer whose line the resource-requirement test (WRR-001) adds a requirement to,
    and invented machines with a second invented Plum report for the equipment
    import test (ERT-1), (8A core) a Work Order whose requirement the allocation test fills, (ELG-2) a held
    allocation whose papers run out, for the certificate reminders' test, (HOL-1) a year of PBL's holiday
    calendar far ahead with a Work Order over it, for the holiday calendar's test, (CS-05a) a DRAFT offer with
    one line that the stale-save test edits in two tabs, and (Slice 9F) a submitted offer whose content the
    submitted-offer test finds locked before it makes v2."""
    actor_public_id = actor["public_id"]
    equipment = _build_equipment_reference_target(run_id=run_id, actor_public_id=actor_public_id)
    return {
        "handoff_target": _build_accepted_offer(
            run_id=run_id, actor_public_id=actor_public_id, suffix="Handoff", with_work_order=False
        ),
        "terminal_guard": _build_rejected_offer(run_id=run_id, actor_public_id=actor_public_id, suffix="TermGuard"),
        "existing_traceability": _build_accepted_offer(
            run_id=run_id, actor_public_id=actor_public_id, suffix="Traceability", with_work_order=True
        ),
        "read_only_view": _build_accepted_offer(
            run_id=run_id, actor_public_id=actor_public_id, suffix="ReadOnly", with_work_order=True
        ),
        "document_upload_target": _build_document_upload_target(
            run_id=run_id, actor_public_id=actor_public_id, suffix="Upload"
        ),
        "resource_requirement_target": _build_accepted_offer(
            run_id=run_id, actor_public_id=actor_public_id, suffix="ResourceReq", with_work_order=True
        ),
        "equipment_reference_target": equipment,
        # 8A core: a Work Order whose requirement the allocation test allocates the run's crawlers to.
        "allocation_target": _build_allocation_target(
            run_id=run_id, actor_public_id=actor_public_id, suffix="Allocation", equipment=equipment["equipment_allocation"]
        ),
        # ELG-2: a held allocation for the certificate reminders' Playwright test.
        "reminder_target": _build_reminder_target(
            run_id=run_id, actor_public_id=actor_public_id, suffix="Reminders", equipment=equipment["equipment_reminders"]
        ),
        # HOL-1: a year of PBL's holiday calendar the run starts, far ahead, and a Work Order over it for the holiday
        # calendar's Playwright test.
        "holiday_calendar_target": _build_holiday_calendar_target(
            run_id=run_id, actor_public_id=actor_public_id, suffix="Holidays", calendar_year=free_harness_calendar_year()
        ),
        # CS-05a: a draft offer with one line, which the stale-save test edits from two tabs.
        "stale_save_target": _build_draft_offer_with_line(run_id=run_id, actor_public_id=actor_public_id, suffix="StaleSave"),
        # Slice 9F: a submitted v1 with one line; the submitted-offer test makes and sends v2.
        "submitted_lock_target": _build_submitted_offer_with_line(
            run_id=run_id, actor_public_id=actor_public_id, suffix="SubmittedLock"
        ),
    }


def scenario_supplementary_offer_draft(run_id: str, actor: dict[str, str]) -> dict[str, Any]:
    return {
        "supplementary_offer_draft": _build_supplementary_offer_draft(
            run_id=run_id, actor_public_id=actor["public_id"], suffix="SuppDraft"
        )
    }


def scenario_change_quotation_draft(run_id: str, actor: dict[str, str]) -> dict[str, Any]:
    return {
        "change_quotation_draft": _build_change_quotation_draft(
            run_id=run_id, actor_public_id=actor["public_id"], suffix="ChangeQuoteDraft"
        )
    }


def scenario_supplementary_offer_lifecycle(run_id: str, actor: dict[str, str]) -> dict[str, Any]:
    return {
        "supplementary_offer_lifecycle": _build_supplementary_offer_lifecycle(
            run_id=run_id, actor_public_id=actor["public_id"], suffix="SuppLifecycle"
        )
    }


def scenario_related_offer_regression_bundle(run_id: str, actor: dict[str, str]) -> dict[str, Any]:
    """Independent record sets for the Slice 6O.1 Playwright coverage: an Opportunity
    showing all three offer purposes, and separate clean accepted-Base-Offer targets for
    live Supplementary Offer creation, live Change Quotation creation and a read-only view -
    each its own Base Offer so no two Playwright tests mutate the same Commercial Offer
    (matching the TE-1 core-regression-bundle isolation principle)."""
    actor_public_id = actor["public_id"]
    return {
        "multi_series_target": _build_opportunity_with_multiple_related_offers(
            run_id=run_id, actor_public_id=actor_public_id, suffix="MultiSeries"
        ),
        "supplementary_offer_create_target": _build_accepted_offer(
            run_id=run_id, actor_public_id=actor_public_id, suffix="SuppCreate", with_work_order=False
        ),
        "change_quotation_create_target": _build_accepted_offer(
            run_id=run_id, actor_public_id=actor_public_id, suffix="ChangeQuoteCreate", with_work_order=True
        ),
        "related_offer_read_only_view": _build_supplementary_offer_draft(
            run_id=run_id, actor_public_id=actor_public_id, suffix="RelatedReadOnly"
        ),
    }


def scenario_work_order_amendment_received(run_id: str, actor: dict[str, str]) -> dict[str, Any]:
    return {
        "work_order_amendment_received": _build_work_order_amendment_received(
            run_id=run_id, actor_public_id=actor["public_id"], suffix="AmdReceived"
        )
    }


def scenario_commercial_amendment_with_change_quotation(run_id: str, actor: dict[str, str]) -> dict[str, Any]:
    return {
        "commercial_amendment_with_change_quotation": _build_commercial_amendment_with_change_quotation(
            run_id=run_id, actor_public_id=actor["public_id"], suffix="AmdChangeQuote"
        )
    }


def scenario_work_order_amendment_regression_bundle(run_id: str, actor: dict[str, str]) -> dict[str, Any]:
    return _build_work_order_amendment_regression_bundle(run_id=run_id, actor_public_id=actor["public_id"])




# --- UAT synthetic data pack ------------------------------------------------------------------
#
# Seeded practice data for the PBL CRM pilot. Two things distinguish it from every scenario above,
# both deliberate:
#
#   1. It is SYNTHETIC BY DECISION, not by convenience (owner decision, 8 September 2026). The
#      pilot runs on invented data so that the unresolved retention-purge and download-audit
#      policy items - recorded in docs/agent/DEFERRED_REQUIREMENTS.md as "required before
#      production" - do not gate it. That reasoning only holds while the data really is synthetic
#      and really is removable, which is why the cleanup corrections shipped alongside this pack
#      are part of the same package rather than a follow-up.
#
#   2. The customers, equipment and work are modelled on PBL's own published project pages
#      (www.pbltransport.co.in) and on the BOQ shape of a real equipment-hiring RFQ. Names are
#      altered to be recognisably fictional - the owner's rule, 9 September 2026: "Vizag Steel
#      Plant can become Kakinada Steel, Larsen & Toubro can become Carson & Two Bros. It gives a
#      familiar ring and at the same time fictional." No real customer name appears anywhere.
#      Crane models are PBL's own fleet and are used unaltered; a model number identifies
#      equipment, not a customer.
#
# The OT-hours line paired with almost every crane-hire line is not invented either. It is how the
# real RFQ is structured - each hire line has a matching overtime line at its own rate - and it is
# the kind of shape that only shows up in real documents.

UAT_TAG = "UAT"

# Andhra Pradesh / Telangana / Odisha / Gujarat / Tamil Nadu / Karnataka.
UAT_GST_STATES = {
    "37": "Andhra Pradesh",
    "36": "Telangana",
    "21": "Odisha",
    "24": "Gujarat",
    "33": "Tamil Nadu",
    "29": "Karnataka",
}


def _uat_pan(run_id: str, customer_index: int) -> str:
    """Format-valid, deliberately un-issuable (owner decision, 9 September 2026).

    PAN is ^[A-Z]{5}[0-9]{4}[A-Z]$ and its FOURTH character encodes entity type - C company,
    P individual, H HUF, F firm, A AOP, T trust, B BOI, L local authority, J artificial juridical
    person, G government. 'Z' is not one of them, so a ZZZZ-prefixed PAN passes every format check
    the application makes while naming no entity that could exist. That matters because SurePass
    validation is still deferred (ADR-015): nothing checks these against the real registry, so an
    invented but plausible PAN could silently coincide with a real business's statutory number.

    The digits come from the run id so two runs never collide on the globally unique
    ux_business_party_gstin index built over the GSTINs derived from this PAN.

    The FIFTH character is the customer index, so this dataset only ever produces A-J. That is a
    reservation, not an accident: the testers' sheets in `docs/uat/` and `docs/uat-hiring/` give hand-typed
    practice customers an `M` there (and their own data a `P`), so a pilot user keying in the data sheet can never collide
    with a seeded customer on the GST register - which rejects a duplicate GSTIN outright and
    would look to them like a defect. Keep the two blocks disjoint if either side gains more
    customers."""
    digits = int(run_id.split("-")[-1], 16) % 10000
    return f"ZZZZ{chr(ord('A') + customer_index)}{digits:04d}Z"


def _uat_gstin(run_id: str, customer_index: int, state_code: str) -> str:
    """GSTIN is ^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]$ - a state code followed by the
    entity's PAN. Multiple state registrations therefore SHARE one PAN, which is why a customer
    with several GSTINs is a realistic shape rather than a contrived one."""
    return f"{state_code}{_uat_pan(run_id, customer_index)}1ZZ"


# Each entry: the customer, its identity records, its enquiry, and the offer lines that answer it.
# `lines` are (scope_description, equipment_service_category, quantity, uom, rate_amount);
# a rate of None is an ACTIVE but unpriced line, which is a reachable application state and makes
# the generated quotation read "Not fully priced" instead of showing a partial sum as a total.
UAT_CUSTOMERS: list[dict[str, Any]] = [
    {
        "key": "kakinada_steel",
        "stage": "submitted_awaiting_response",
        "name": f"{UAT_TAG}-Kakinada Steel & Ferro Alloys",
        # Deliberately near the 255-character legal_name ceiling: a PSU's full registered style
        # with division and enterprise qualifiers is genuinely this long, and it is the case that
        # breaks table columns, page headers and the generated quotation's letterhead.
        "legal_name": (
            "Kakinada Steel and Ferro Alloys Corporation of India Limited - Visakhapatnam "
            "Integrated Works and Coastal Logistics Division (A Government of India Enterprise "
            "under the administrative control of the Ministry of Steel)"
        ),
        "segment": "Key Account",
        "industry": "Iron and Steel",
        "gst_states": ["37", "36", "21", "24"],
        "addresses": [
            {
                "address_type_code": "REGISTERED_OFFICE",
                "address_line1": "Administrative Building, Steel Plant Complex",
                "city": "Visakhapatnam",
                "district": "Visakhapatnam",
                "state": "Andhra Pradesh",
                "postal_code": "530031",
                "is_primary": True,
            }
        ],
        "opportunity_name": "Crane hire for structures and erection works - Vizag works",
        "requirement": (
            "Hiring of various capacity telescopic cranes for structures and erection works "
            "across multiple projects at the Visakhapatnam works. Cranes required on both call "
            "basis and continuous basis, with overtime billed separately."
        ),
        "estimated_value": "8500000.00",
        "offer_title": "Crane hire - structures and erection works, Vizag works",
        "lines": [
            ("Hiring of 250mt tyre-mounted telescopic crane on call basis, excluding Sundays and public holidays", "Crane", "8", "Days", "145000.00"),
            ("Overtime hours for 250mt crane, billed beyond the 10-hour working day", "Crane", "8", "Hrs", "18500.00"),
            ("Hiring of 200mt tyre-mounted telescopic crane on continuous basis (26 working days per month)", "Crane", "3", "Mon", "2850000.00"),
            ("Overtime hours for 200mt crane", "Crane", "60", "Hrs", "14500.00"),
            ("Mobilisation and demobilisation of cranes with hooks, jibs and fixtures", "Mobilisation", "1", "Lot", "375000.00"),
        ],
    },
    {
        "key": "aurum_infra",
        "stage": "won_with_work_order",
        "name": f"{UAT_TAG}-Aurum Infra Projects Private Limited",
        "legal_name": "Aurum Infra Projects Private Limited",
        "segment": "Infrastructure",
        "industry": "Marine and Port Construction",
        "gst_states": ["37"],
        "addresses": [
            {
                "address_type_code": "REGISTERED_OFFICE",
                "address_line1": "8-2-120/112, Road No. 2, Banjara Hills",
                "city": "Hyderabad",
                "district": "Hyderabad",
                "state": "Telangana",
                "postal_code": "500034",
                "is_primary": True,
            },
            {
                "address_type_code": "SITE",
                "address_line1": "Jetty Construction Site, Package J-2",
                "address_line2": "Coastal Approach Road, Near Fishing Harbour",
                "city": "Annavaram",
                "district": "Kakinada",
                "state": "Andhra Pradesh",
                "postal_code": "533406",
            },
        ],
        "opportunity_name": "Jetty construction - heavy lifting support, Annavaram",
        "requirement": (
            "Heavy-duty lifting and precise installation of structural components for jetty "
            "construction in a marine environment. Deep piling requires sustained crane "
            "availability; tide fluctuation and site space constraints affect scheduling."
        ),
        "estimated_value": "4200000.00",
        "offer_title": "150mt crane hire - jetty construction, Annavaram",
        "lines": [
            ("Hiring of 150mt crane including operator and rigging crew, for jetty piling and beam placement", "Crane", "2", "Mon", "1950000.00"),
            ("Overtime hours for 150mt crane", "Crane", "45", "Hrs", "12500.00"),
            ("Mobilisation and demobilisation to Annavaram jetty site", "Mobilisation", "1", "Lot", "285000.00"),
        ],
    },
    {
        "key": "macdiarmid_offshore",
        "stage": "draft_two_quote_versions",
        "name": f"{UAT_TAG}-MacDiarmid Offshore Engineering India Private Limited",
        "legal_name": "MacDiarmid Offshore Engineering India Private Limited",
        "segment": "Key Account",
        "industry": "Offshore Oil and Gas",
        "gst_states": ["37", "24"],
        "addresses": [
            {
                "address_type_code": "COMMUNICATION",
                "address_line1": "Offshore Supply Base, Kakinada Deepwater Port",
                "address_line2": "Berth 4, Port Access Road",
                "city": "Kakinada",
                "district": "Kakinada",
                "state": "Andhra Pradesh",
                "postal_code": "533007",
                "is_primary": True,
            }
        ],
        "opportunity_name": "Offshore project cargo handling - Kakinada",
        "requirement": (
            "Handling and transportation of offshore equipment for subsea pipeline installation, "
            "including cable reel discharge at Kakinada port. Requires coordination with port "
            "authorities and vessel crews."
        ),
        "estimated_value": "1850000.00",
        "offer_title": "Project cargo handling and access equipment - Kakinada offshore",
        "lines": [
            ("Project cargo handling at Kakinada port - cable reel discharge and stuffing", "Handling", "480", "MT", "1450.00"),
            ("Manlift 20m aerial work platform on monthly hire", "Manlift", "2", "Mon", "165000.00"),
            ("Forklift 5T with operator", "Forklift", "26", "Days", "8500.00"),
        ],
    },
    {
        "key": "vedansha_resources",
        "stage": "revision_requested",
        "name": f"{UAT_TAG}-Vedansha Aluminium & Resources Limited",
        "legal_name": "Vedansha Aluminium and Resources Limited",
        "segment": "Key Account",
        "industry": "Metals and Mining",
        "gst_states": ["21", "37"],
        "addresses": [
            {
                # The multi-line site address: line 2 and a district that differs from the city,
                # which is what exposes address rendering that assumes a single line.
                "address_type_code": "SITE",
                "address_line1": "Alumina Refinery Expansion Site, Plot R-7, Phase III",
                "address_line2": "Near Weighbridge Gate No. 4, Lanjigarh Industrial Area",
                "city": "Lanjigarh",
                "district": "Kalahandi",
                "state": "Odisha",
                "postal_code": "766027",
                "is_primary": True,
            }
        ],
        "opportunity_name": "Crawler crane hire - refinery expansion, Lanjigarh",
        "requirement": (
            "Erection of heavy columns, reactors and structural components for plant expansion. "
            "Site has rough terrain and tight assembly zones, so crawler crane manoeuvrability "
            "and rigging capability are decisive."
        ),
        "estimated_value": "13500000.00",
        "offer_title": "XCMG XGC 150 crawler crane - column and reactor erection",
        "lines": [
            ("XCMG XGC 150 crawler crane on monthly hire for column and reactor erection", "Crane", "3", "Mon", "4250000.00"),
            ("Overtime hours for crawler crane", "Crane", "90", "Hrs", "19500.00"),
            ("Rigging crew and lifting tackles including slings and D-shackles", "Crew", "3", "Mon", "285000.00"),
        ],
    },
    {
        "key": "ntpg_power",
        "stage": "lost",
        "name": f"{UAT_TAG}-NTPG Power Generation Corporation Limited",
        "legal_name": "NTPG Power Generation Corporation Limited",
        "segment": "Public Sector",
        "industry": "Power Generation",
        "gst_states": ["37"],
        "addresses": [
            {
                "address_type_code": "REGISTERED_OFFICE",
                "address_line1": "Corporate Centre, Plot 12, Energy Estate",
                "city": "Visakhapatnam",
                "state": "Andhra Pradesh",
                "postal_code": "530003",
                "is_primary": True,
            }
        ],
        "opportunity_name": "Crawler crane hire - power plant structural erection",
        "requirement": (
            "Precision lifting and placement of large structural components for power "
            "infrastructure construction, in challenging terrain."
        ),
        "estimated_value": "8500000.00",
        "offer_title": "Crawler crane hire - power plant erection",
        "lines": [
            ("Crawler crane 150T on continuous basis for structural erection", "Crane", "2", "Mon", "3850000.00"),
            ("Overtime hours for crawler crane", "Crane", "40", "Hrs", "18000.00"),
        ],
    },
    {
        "key": "godavari_paper",
        "stage": "on_hold",
        "name": f"{UAT_TAG}-Godavari Paper Mills Limited",
        "legal_name": "Godavari Paper Mills Limited",
        "segment": "Manufacturing",
        "industry": "Pulp and Paper",
        "gst_states": ["37"],
        "addresses": [
            {
                "address_type_code": "SITE",
                "address_line1": "Mill Premises, Kadiyam Road",
                "city": "Rajahmundry",
                "district": "East Godavari",
                "state": "Andhra Pradesh",
                "postal_code": "533105",
                "is_primary": True,
            }
        ],
        "opportunity_name": "Digester hoist and access equipment - mill upgrade",
        "requirement": (
            "Infrastructure upgrade at the mill requiring a high-capacity crane to hoist a "
            "digester vessel into position, with scaffolding and safety coordination."
        ),
        "estimated_value": "2700000.00",
        "offer_title": "Crane hire - digester hoist, Rajahmundry mill upgrade",
        "lines": [
            ("Hiring of 250mt crane for digester vessel hoist and positioning", "Crane", "12", "Days", "155000.00"),
            ("Sany STC 800 telescopic truck crane on 8-hour shift basis", "Crane", "20", "Shift", "42000.00"),
        ],
    },
    {
        "key": "saint_guilbert",
        "stage": "draft_partly_priced",
        "name": f"{UAT_TAG}-Saint-Guilbert Glass India Private Limited",
        "legal_name": "Saint-Guilbert Glass India Private Limited",
        "segment": "Manufacturing",
        "industry": "Glass and Advanced Materials",
        "gst_states": ["36"],
        "addresses": [
            {
                "address_type_code": "COMMUNICATION",
                "address_line1": "Survey No. 214, Industrial Development Area",
                "address_line2": "Bollaram, Jinnaram Mandal",
                "city": "Hyderabad",
                "district": "Sangareddy",
                "state": "Telangana",
                "postal_code": "502325",
                "is_primary": True,
            }
        ],
        "opportunity_name": "Covered transport - industrial logistics, Hyderabad",
        "requirement": (
            "Movement of high-value manufacturing materials requiring covered transport to "
            "protect against environmental exposure during transit."
        ),
        "estimated_value": "1100000.00",
        "offer_title": "Covered trailer movements - Hyderabad industrial logistics",
        "lines": [
            ("40ft covered trailer movement, plant to distribution point", "Trailer", "14", "Trip", "68000.00"),
            # Deliberately unpriced: the rate is still being worked out. Makes the generated
            # quotation read "Not fully priced" rather than showing the priced line's total as if
            # it were the whole quotation.
            ("Route survey, statutory permits and escort vehicles - rate to be confirmed", "Logistics", "1", "Lot", None),
        ],
    },
    {
        "key": "sri_nookaraju",
        "stage": "won_with_amendment",
        "name": f"{UAT_TAG}-Sri Nookaraju Constructions",
        "legal_name": "Sri Nookaraju Constructions",
        "segment": "Regional Contractor",
        "industry": "Civil Construction",
        "gst_states": ["37"],
        "addresses": [
            {
                "address_type_code": "REGISTERED_OFFICE",
                "address_line1": "D. No. 12-4-18, Gandhi Nagar",
                "city": "Vizianagaram",
                "district": "Vizianagaram",
                "state": "Andhra Pradesh",
                "postal_code": "535002",
                "is_primary": True,
            }
        ],
        "opportunity_name": "Girder movement to Vizianagaram - hydraulic axles",
        "requirement": (
            "Transportation of a fabricated girder using multi-axle hydraulic trailer and puller. "
            "Route requires survey for low-clearance bridges and sharp turns, escort vehicles and "
            "statutory permissions."
        ),
        "estimated_value": "1150000.00",
        "offer_title": "ODC girder movement - Vizianagaram",
        "lines": [
            ("Multi-axle hydraulic trailer with puller for girder movement to Vizianagaram", "Trailer", "1", "Trip", "985000.00"),
            ("Escort vehicles, route survey and statutory permits for ODC movement", "Logistics", "1", "Lot", "165000.00"),
        ],
    },
    {
        "key": "carson_two_bros",
        "stage": "accepted_with_related_offers",
        "name": f"{UAT_TAG}-Carson & Two Bros Limited",
        "legal_name": "Carson and Two Bros Limited",
        "segment": "Key Account",
        "industry": "Engineering and Construction",
        "gst_states": ["36", "37", "33"],
        "addresses": [
            {
                "address_type_code": "REGISTERED_OFFICE",
                "address_line1": "Construction Division, Mount Poonamallee Road",
                "city": "Chennai",
                "district": "Chennai",
                "state": "Tamil Nadu",
                "postal_code": "600089",
                "is_primary": True,
            }
        ],
        "opportunity_name": "Multi-capacity crane hire - plant erection package",
        "requirement": (
            "Cranes of 80mt and 40mt capacity required on a mix of continuous and call basis for "
            "a plant erection package, with overtime billed separately and a 10-hour working day."
        ),
        "estimated_value": "4800000.00",
        "offer_title": "80mt and 40mt crane hire - plant erection package",
        "lines": [
            ("Hiring of 80mt crane on 30-day continuous basis (two tenures of 15 days)", "Crane", "30", "Days", "96000.00"),
            ("Overtime hours for 80mt crane", "Crane", "20", "Hrs", "9500.00"),
            ("Hiring of 40mt crane on call basis, 10 hours reckoned as one day", "Crane", "226", "Hrs", "4200.00"),
        ],
    },
    {
        "key": "harshita_projects",
        "stage": "submitted_no_quotation",
        "name": f"{UAT_TAG}-Harshita Projects",
        "legal_name": "Harshita Projects",
        "segment": "Regional Contractor",
        "industry": "Industrial Fabrication",
        "gst_states": ["36", "21"],
        "addresses": [
            {
                "address_type_code": "COMMUNICATION",
                "address_line1": "Fabrication Yard, Plot 47, Cherlapally Industrial Estate",
                "city": "Hyderabad",
                "district": "Medchal-Malkajgiri",
                "state": "Telangana",
                "postal_code": "500051",
                "is_primary": True,
            }
        ],
        "opportunity_name": "Column transportation - Hyderabad to Odisha",
        "requirement": (
            "Transportation of oversized fabricated columns across state boundaries, requiring "
            "route surveys, permits and coordination with local authorities."
        ),
        "estimated_value": "2550000.00",
        "offer_title": "ODC column movement - Hyderabad to Odisha",
        "lines": [
            ("Transportation of fabricated columns, Hyderabad to Odisha, including lashing and securing", "Trailer", "6", "Trip", "425000.00"),
        ],
    },
]


def _seed_uat_customer(
    *,
    run_id: str,
    actor: dict[str, str],
    approver_public_id: str,
    customer: dict[str, Any],
    index: int,
) -> dict[str, Any]:
    """Seeds one practice customer end to end: Account with full statutory identity, Opportunity,
    Commercial Offer with its real BOQ lines, and whatever lifecycle stage the entry asks for.

    Stages are ordered deliberately. A quotation can only be generated while the offer is DRAFT,
    READY_FOR_REVIEW or SUBMITTED, and can only be approved for issue while the offer is not
    ACCEPTED/REJECTED/WITHDRAWN/CLOSED (Slice 9E preconditions), so every stage that ends in a
    final customer response generates and approves BEFORE recording it."""
    actor_public_id = actor["public_id"]
    stage = customer["stage"]

    pair = create_account_linked_opportunity(
        run_id=run_id,
        actor_public_id=actor_public_id,
        suffix=customer["key"],
        account_name=customer["name"],
        legal_name=customer["legal_name"],
        segment=customer["segment"],
        industry=customer["industry"],
        opportunity_name=customer["opportunity_name"],
        source_reference=f"UAT pilot dataset, run {run_id}",
        customer_requirement_summary=customer["requirement"],
        estimated_value=Decimal(customer["estimated_value"]),
    )
    account_public_id = pair["account"]["public_id"]

    addresses = [
        add_account_address(
            actor_public_id=actor_public_id, account_public_id=account_public_id, **address
        )
        for address in customer["addresses"]
    ]
    gstins = [
        add_account_gstin(
            actor_public_id=actor_public_id,
            account_public_id=account_public_id,
            gstin=_uat_gstin(run_id, index, state_code),
            state_code=state_code,
            state_name=UAT_GST_STATES[state_code],
            legal_name=customer["legal_name"][:255],
            is_primary=(position == 0),
            # A multi-state customer realistically has registrations at different stages of
            # verification rather than uniformly one state.
            gstin_verification_state_code="VERIFIED" if position == 0 else "ENTERED_NOT_VERIFIED",
        )
        for position, state_code in enumerate(customer["gst_states"])
    ]
    set_account_tax_profile(
        actor_public_id=actor_public_id,
        account_public_id=account_public_id,
        pan=_uat_pan(run_id, index),
        pan_legal_name=customer["legal_name"][:255],
    )

    offer = create_offer_no_line(
        run_id=run_id,
        actor_public_id=actor_public_id,
        opportunity_public_id=pair["opportunity"]["public_id"],
        suffix=customer["key"],
        offer_title=customer["offer_title"],
        offer_value=Decimal(customer["estimated_value"]),
        remarks=f"UAT pilot practice data, run {run_id}. Synthetic customer and synthetic values.",
    )
    offer_public_id = offer["public_id"]

    line_public_ids = [
        add_offer_line(
            actor_public_id=actor_public_id,
            offer_public_id=offer_public_id,
            scope_description=description,
            equipment_service_category=category,
            quantity=Decimal(quantity),
            uom=uom,
            rate_amount=Decimal(rate) if rate is not None else None,
            remarks=None,
        )["line_public_id"]
        for description, category, quantity, uom, rate in customer["lines"]
    ]

    attach_recommended_tc_clauses(actor_public_id=actor_public_id, offer_public_id=offer_public_id)
    # Three vendor quotes and an explicit choice between them, rather than a single rate with
    # nothing to compare it against. Alternating by index means roughly half the practice
    # customers were quoted on the lowest rate and half on the second-lowest with a recorded
    # reason - both of which happen, and only one of which is visible if every offer has one rate.
    pricing = _seed_market_rates_and_choice(
        actor_public_id=actor_public_id,
        offer_public_id=offer_public_id,
        lines=[
            (line_public_id, line[0], Decimal(line[4] or "50000.00"))
            for line_public_id, line in zip(line_public_ids, customer["lines"])
        ],
        choose_lowest=(index % 2 == 0),
    )

    record: dict[str, Any] = {
        "account": pair["account"],
        "opportunity": pair["opportunity"],
        "commercial_offer": {**offer, "line_public_ids": line_public_ids},
        "addresses": addresses,
        "gstins": gstins,
        "pricing_evidence": pricing,
        "work_orders": [],
        "quote_documents": [],
        "interactions": [],
        "revisions": [],
        "uploads": [],
    }

    def _generate(approve: bool, note: str | None = None) -> dict[str, Any]:
        quote = generate_quote_document(
            actor_public_id=actor_public_id, offer_public_id=offer_public_id
        )
        if approve:
            quote = {
                **quote,
                **approve_quote_document(
                    actor_public_id=approver_public_id,
                    offer_public_id=offer_public_id,
                    quote_document_public_id=quote["public_id"],
                    approval_note=note,
                ),
            }
        record["quote_documents"].append(quote)
        return quote

    def _talk(channel: str, direction: str, subject: str, body: str | None = None) -> None:
        record["interactions"].append(
            log_interaction(
                actor_public_id=actor_public_id,
                actor_username=actor["username"],
                linked_record_type="commercial_offer",
                linked_record_public_id=offer_public_id,
                channel_code=channel,
                direction_code=direction,
                subject=subject,
                body_text=body,
            )
        )

    if stage == "draft_partly_priced":
        # Left in DRAFT on purpose, with one line still unpriced, so the generated quotation
        # shows "Not fully priced" rather than a partial sum dressed up as a total.
        _generate(approve=False)
        _talk("EMAIL", "INBOUND", "Rate query on escort vehicle and permit scope")

    elif stage == "draft_two_quote_versions":
        # Two versions on one offer: V1 is superseded by V2 in the same transaction, but keeps its
        # own history. Gives the pilot a version list with more than one row in it.
        _generate(approve=False)
        _generate(approve=False)
        _talk("MEETING", "OUTBOUND", "Site walk-through at Kakinada supply base")

    elif stage == "submitted_no_quotation":
        # Deliberately no quotation: the submission-readiness QUOTATION_DOCUMENT row should read
        # ATTENTION_REQUIRED here while INTERACTION_LOG reads PASS, so the pilot sees both states
        # of the advisory checklist rather than only the happy one.
        submit_offer(run_id=run_id, actor_public_id=actor_public_id, offer_public_id=offer_public_id)
        _talk("CALL", "OUTBOUND", "Confirmed column dimensions and loading sequence")
        _talk("WHATSAPP", "INBOUND", "Customer shared revised despatch window")

    elif stage == "submitted_awaiting_response":
        _generate(approve=True, note="Approved for issue to customer against tender enquiry.")
        submit_offer(run_id=run_id, actor_public_id=actor_public_id, offer_public_id=offer_public_id)
        # A negotiation is a conversation over days, not one message. Several entries in sequence
        # are what the interaction log is for, and what a single entry cannot show.
        _talk("EMAIL", "OUTBOUND", "Quotation issued for crane hire package",
              "Sent the approved quotation with the rate breakup and mobilisation terms.")
        _talk("CALL", "INBOUND", "Customer purchase team called on the 200mt monthly rate",
              "Said our monthly rate is above their budget estimate. Asked whether the rate improves if they commit to three months instead of two.")
        _talk("NOTE", "OUTBOUND", "Checked the three-month commitment internally",
              "Operations confirmed the machine can be committed for three months. A small reduction is possible if mobilisation is billed once instead of twice.")
        _talk("EMAIL", "OUTBOUND", "Offered single mobilisation against a three-month commitment",
              "Explained that mobilisation would be charged once rather than per tenure if they commit to three months.")

    elif stage == "revision_requested":
        _generate(approve=True, note="Approved for issue.")
        submit_offer(run_id=run_id, actor_public_id=actor_public_id, offer_public_id=offer_public_id)
        _talk("EMAIL", "OUTBOUND", "Quotation issued for crawler crane package")
        record_customer_response(
            actor_public_id=actor_public_id,
            offer_public_id=offer_public_id,
            outcome="REVISION_REQUESTED",
        )
        _talk("EMAIL", "INBOUND", "Customer asked for a revised crawler crane monthly rate",
              "Their technical team reduced the erection scope. Asked us to requote on the reduced scope.")
        _talk("MEETING", "OUTBOUND", "Met the project team to agree the reduced scope",
              "Agreed the third month is no longer required. Rigging crew stays as quoted.")

        # Make an independently editable v2 from the sent v1. The quotation and submission
        # evidence belong to v2; sending it moves v1 to Replaced without changing v1's content.
        first_version = record["commercial_offer"]
        next_version = make_commercial_offer_version(
            actor_public_id=actor_public_id, offer_public_id=offer_public_id
        )
        offer_public_id = next_version["public_id"]
        record["commercial_offer"] = next_version
        record["offer_versions"] = [first_version, next_version]
        _generate(approve=True, note="Revised quotation approved for issue after scope reduction.")
        submit_offer(run_id=run_id, actor_public_id=actor_public_id, offer_public_id=offer_public_id)
        _talk("EMAIL", "OUTBOUND", "Revised quotation sent",
              "Sent the revised quotation covering two months instead of three.")

    elif stage == "on_hold":
        _generate(approve=True, note="Approved for issue.")
        submit_offer(run_id=run_id, actor_public_id=actor_public_id, offer_public_id=offer_public_id)
        record_customer_response(
            actor_public_id=actor_public_id, offer_public_id=offer_public_id, outcome="ON_HOLD"
        )

    elif stage == "lost":
        _generate(approve=True, note="Approved for issue.")
        submit_offer(run_id=run_id, actor_public_id=actor_public_id, offer_public_id=offer_public_id)
        record_customer_response(
            actor_public_id=actor_public_id, offer_public_id=offer_public_id, outcome="REJECTED_LOST"
        )
        _talk("EMAIL", "INBOUND", "Order placed elsewhere on price")

    elif stage in {"won_with_work_order", "won_with_amendment", "accepted_with_related_offers"}:
        _generate(approve=True, note="Approved for issue.")
        submit_offer(run_id=run_id, actor_public_id=actor_public_id, offer_public_id=offer_public_id)
        record_customer_response(
            actor_public_id=actor_public_id,
            offer_public_id=offer_public_id,
            outcome="ACCEPTED_AWARDED",
        )
        # A file that arrived from the customer, uploaded through the real Slice 9C path. The
        # generated quotation exercises document GENERATION; this exercises document UPLOAD, which
        # is a different route with different code behind it and is what a user does far more
        # often. Attached to the offer before the Work Order exists, which is the real sequence.
        record["uploads"].append(
            upload_customer_document(
                actor_public_id=actor_public_id,
                linked_record_type="commercial_offer",
                linked_record_public_id=offer_public_id,
                document_type="COMMERCIAL",
                file_name="customer-work-order-copy.txt",
                body_text=(
                    "Customer work order copy (practice data).\n"
                    f"Against offer: {offer['offer_code']}\n"
                    "Scope and rates as per our quotation. Mobilisation to be advised.\n"
                ),
                remarks="Copy of the customer work order received by email.",
            )
        )
        work_order = create_work_order(
            actor_public_id=actor_public_id, offer_public_id=offer_public_id
        )
        record["work_orders"].append(work_order)
        _talk("LETTER", "INBOUND", "Work order received from customer")

        if stage == "won_with_amendment":
            amendment = create_work_order_amendment(
                run_id=run_id,
                actor_public_id=actor_public_id,
                work_order_public_id=work_order["public_id"],
                amendment_type_code="ADMINISTRATIVE",
            )
            add_amendment_line(
                actor_public_id=actor_public_id,
                work_order_public_id=work_order["public_id"],
                amendment_public_id=amendment["public_id"],
            )
            record["amendments"] = [amendment]

        if stage == "accepted_with_related_offers":
            supplementary = create_related_offer(
                run_id=run_id,
                actor_public_id=actor_public_id,
                base_offer_public_id=offer_public_id,
                offer_purpose="SUPPLEMENTARY",
                related_work_order_public_id=None,
                customer_request_summary=(
                    "Customer requires an additional 40mt crane on call basis for the second "
                    "erection front."
                ),
            )
            add_offer_line(
                actor_public_id=actor_public_id,
                offer_public_id=supplementary["public_id"],
                scope_description="Additional 40mt crane on call basis, second erection front",
                equipment_service_category="Crane",
                quantity=Decimal("90"),
                uom="Hrs",
                rate_amount=Decimal("4200.00"),
            )
            change_quotation = create_related_offer(
                run_id=run_id,
                actor_public_id=actor_public_id,
                base_offer_public_id=offer_public_id,
                offer_purpose="CHANGE_QUOTATION",
                related_work_order_public_id=work_order["public_id"],
                customer_request_summary=(
                    "Customer requested revised monthly rate for the 80mt crane following an "
                    "extension of the erection window."
                ),
            )
            record["related_offers"] = [supplementary, change_quotation]

    else:  # pragma: no cover - guards against a typo in UAT_CUSTOMERS
        raise ValueError(f"Unknown UAT stage {stage!r} for customer {customer['key']!r}")

    return record


# --- the sales journey before the offer -------------------------------------------------------
#
# Added after the owner asked whether the practice data covered what a sales executive actually
# does. It did not: every customer began life as an Account with an Opportunity already attached,
# which is the middle of the story. These records cover the beginning - an enquiry arriving as a
# lead, being worked with calls and notes, and then either becoming an Opportunity or being closed
# because it is not worth pursuing.

UAT_LEADS: list[dict[str, Any]] = [
    {
        "key": "lead_converted",
        "outcome": "converted",
        "company_name": f"{UAT_TAG}-Trident Marine Works Private Limited",
        "contact_name": "R. Satyanarayana",
        "contact_phone": "+91-98480-11223",
        "contact_email": "satya@trident-marine.invalid",
        "lead_source": "email",
        "requirement_summary": (
            "Enquiry for crane support during breakwater block placement at a fishing harbour "
            "project. Duration not confirmed; customer asked what capacity would be suitable."
        ),
        "activities": [
            ("CALL", "First call. Customer described breakwater block placement, blocks around 40T. Asked what capacity we would recommend.", "Interested. Asked us to suggest a crane and indicative rate."),
            ("EMAIL", "Sent capacity note recommending a 150mt crane for the reach and block weight, with an indicative day rate.", "Customer acknowledged; said their engineer would review."),
            # MEETING, not SITE_VISIT: the Lead activity vocabulary (CALL/EMAIL/WHATSAPP/MEETING/
            # NOTE/OTHER) is narrower than the interaction channel list, which does have
            # SITE_VISIT. The two are separate contracts and do not share values.
            ("MEETING", "Site visit with the Operations Executive. Access road can take the crane. Tide window limits working hours to about 8 per day.", "Confirmed feasible. Customer asked for a formal quotation."),
            ("NOTE", "Site photographs and the access road measurement filed with the enquiry.", None),
        ],
        "opportunity_name": "Breakwater block placement - crane support",
        "requirement": (
            "Crane support for breakwater block placement, approximately 40T blocks, working "
            "within a tide-limited window of about 8 hours per day."
        ),
        "estimated_value": "2400000.00",
        "offer_title": "150mt crane hire - breakwater block placement",
        "lines": [
            ("Hiring of 150mt crane with operator for breakwater block placement", "Crane", "20", "Days", "108000.00"),
            ("Overtime hours for 150mt crane beyond the tide-limited working day", "Crane", "24", "Hrs", "11500.00"),
        ],
    },
    {
        "key": "lead_closed",
        "outcome": "closed",
        "company_name": f"{UAT_TAG}-Ravindra Builders",
        "contact_name": "K. Ravindra",
        "contact_phone": "+91-99490-55667",
        "contact_email": "ravindra@ravindra-builders.invalid",
        "lead_source": "phone",
        "requirement_summary": (
            "Enquiry for a small crane for a two-day slab lift at a residential site in the town "
            "centre."
        ),
        "activities": [
            ("CALL", "Customer needs a crane for two days for a residential slab lift. Site is a narrow town-centre street.", "Noted requirement. Said we would check access."),
            ("NOTE", "Street width and overhead cable clearance would not allow our smallest crane to set up safely.", "Not feasible with our fleet."),
            ("CALL", "Explained the access problem to the customer and suggested a local hydra operator instead.", "Customer understood and thanked us."),
        ],
        "closure_reason": (
            "Site access cannot take our smallest crane safely, and the two-day value does not "
            "justify a special arrangement. Customer advised to use a local hydra operator."
        ),
    },
    {
        "key": "lead_in_progress",
        "outcome": "open",
        "company_name": f"{UAT_TAG}-Coastal Wind Energy Limited",
        "contact_name": "Meera Prasad",
        "contact_phone": "+91-90000-33445",
        "contact_email": "meera.prasad@coastal-wind.invalid",
        "lead_source": "rfq",
        "requirement_summary": (
            "RFQ for transportation of turbine blades and tower sections from the port to a wind "
            "farm site. Blade length approximately 62 metres. Quantities not yet confirmed."
        ),
        "activities": [
            ("EMAIL", "RFQ received for blade and tower section movement from port to site. Blade length about 62 metres.", "Acknowledged. Asked for the delivery schedule and total quantity."),
            ("CALL", "Customer confirmed 12 blades and 9 tower sections, deliveries starting next quarter. Route survey will be needed.", "Awaiting written confirmation of the schedule."),
        ],
        # Deliberately left open: no qualification decision recorded, so a tester has a live lead
        # to work through themselves rather than only finished ones to look at.
    },
]


def _seed_uat_lead(
    *, run_id: str, actor: dict[str, str], approver_public_id: str, lead: dict[str, Any], index: int
) -> dict[str, Any]:
    """One lead worked the way a sales executive works one: created, then a sequence of calls,
    emails, site visits and notes, and only then a decision. Whether it becomes an Opportunity or
    is closed is the outcome of that work, not a shortcut around it - qualification and conversion
    always go through their real actions."""
    actor_public_id = actor["public_id"]
    created = create_lead_detailed(
        run_id=run_id,
        actor_public_id=actor_public_id,
        company_name=lead["company_name"],
        contact_name=lead["contact_name"],
        contact_phone=lead["contact_phone"],
        contact_email=lead["contact_email"],
        requirement_summary=lead["requirement_summary"],
        lead_source=lead["lead_source"],
    )
    activities = [
        add_lead_activity_detailed(
            actor_public_id=actor_public_id,
            lead_public_id=created["public_id"],
            activity_type=activity_type,
            notes=notes,
            outcome=outcome,
        )
        for activity_type, notes, outcome in lead["activities"]
    ]

    record: dict[str, Any] = {"lead": created, "activities": activities, "work_orders": []}

    if lead["outcome"] == "open":
        return record

    if lead["outcome"] == "closed":
        closed = qualify_lead(
            actor_public_id=actor_public_id,
            lead_public_id=created["public_id"],
            decision_status_code="UNQUALIFIED",
            reason=lead["closure_reason"],
        )
        # The manifest must report where the lead ENDED, not the status it was created with -
        # otherwise every lead reads NEW and the record is useless for telling them apart.
        record["lead"]["lead_status_code"] = closed["lead_status_code"]
        return record

    # Converted: qualification first, then the real Slice 3D conversion action, which creates the
    # Account and the Opportunity together and links both back to this lead.
    qualify_lead(actor_public_id=actor_public_id, lead_public_id=created["public_id"])
    converted = convert_lead_to_account_opportunity(
        actor_public_id=actor_public_id, lead_public_id=created["public_id"]
    )
    record["lead"]["lead_status_code"] = "CONVERTED"
    record["account"] = converted["account"]
    record["opportunity"] = converted["opportunity"]

    offer = create_offer_no_line(
        run_id=run_id,
        actor_public_id=actor_public_id,
        opportunity_public_id=converted["opportunity"]["public_id"],
        suffix=lead["key"],
        offer_title=lead["offer_title"],
        offer_value=Decimal(lead["estimated_value"]),
        remarks=f"UAT pilot practice data, run {run_id}. Converted from a lead.",
    )
    line_public_ids = [
        add_offer_line(
            actor_public_id=actor_public_id,
            offer_public_id=offer["public_id"],
            scope_description=description,
            equipment_service_category=category,
            quantity=Decimal(quantity),
            uom=uom,
            rate_amount=Decimal(rate),
        )["line_public_id"]
        for description, category, quantity, uom, rate in lead["lines"]
    ]
    record["commercial_offer"] = {**offer, "line_public_ids": line_public_ids}

    rates = _seed_market_rates_and_choice(
        actor_public_id=actor_public_id,
        offer_public_id=offer["public_id"],
        lines=[
            (line_public_id, line[0], Decimal(line[4]))
            for line_public_id, line in zip(line_public_ids, lead["lines"])
        ],
        choose_lowest=True,
    )
    record["pricing_evidence"] = rates
    attach_recommended_tc_clauses(actor_public_id=actor_public_id, offer_public_id=offer["public_id"])
    return record


def _seed_market_rates_and_choice(
    *,
    actor_public_id: str,
    offer_public_id: str,
    lines: list[tuple[str, str, Decimal]],
    choose_lowest: bool,
) -> dict[str, Any]:
    """Three vendor quotes collected by Operations for each offer line, then one chosen as that
    line's basis for our own (Slices 4D and 4G). `lines` gives each line's id, its scope and the
    rate the quotes are spread around.

    Both outcomes appear in the dataset. Choosing the lowest is the ordinary case. Choosing the
    second-lowest is the interesting one, and it is the reason `selection_reason` exists: the
    Commercial Offer contract states plainly that the selected rate need not be the lowest, and a
    quotation built on a higher rate is only defensible if the reason was recorded when the choice
    was made rather than reconstructed afterwards."""
    # Three vendors, three different Operations Executives. `collected_by_name` is free text - it
    # records WHO went and got the rate, which is not necessarily the person keying it in - while
    # `created_by` separately records the authenticated user who entered the row. Varying both is
    # the realistic shape: rate discovery is usually shared out across the Operations desk rather
    # than done by one person.
    if choose_lowest:
        chosen_index = 0
        reason = "Lowest of the three quotes received, and the vendor confirmed availability for the full period."
    else:
        chosen_index = 1
        reason = (
            "Not the lowest quote. The lowest bidder could not confirm a machine for the whole "
            "period and has had two breakdowns on our sites this year. This vendor confirmed "
            "availability in writing and supplied valid load test certificates."
        )
    priced_lines = []
    for line_public_id, scope_description, base_rate in lines:
        quotes = [
            ("Sagar Equipment Hire", base_rate * Decimal("0.92"), "B. Srinivas (Ops)"),
            ("Konaseema Cranes & Logistics", base_rate * Decimal("0.96"), "P. Lakshmi (Ops)"),
            ("Deccan Heavy Lift Services", base_rate * Decimal("1.04"), "M. Anand (Ops)"),
        ]
        collected = [
            add_market_rate(
                actor_public_id=actor_public_id,
                offer_public_id=offer_public_id,
                line_public_id=line_public_id,
                source_name=source,
                equipment_service_description=scope_description[:1000],
                rate_amount=amount.quantize(Decimal("0.01")),
                rate_basis="per day",
                collected_by_name=collector,
                comparison_notes="Quote collected by Operations against this enquiry.",
            )
            for source, amount, collector in quotes
        ]
        selected = select_basis_rate(
            actor_public_id=actor_public_id,
            offer_public_id=offer_public_id,
            evidence_public_id=collected[chosen_index]["public_id"],
            selection_reason=reason,
        )
        priced_lines.append({"line_public_id": line_public_id, "quotes": collected, "selected": selected})
    return {"lines": priced_lines, "chose_lowest": choose_lowest}


def scenario_uat_pilot_seeded(run_id: str, actor: dict[str, str]) -> dict[str, Any]:
    """The seeded half of the UAT pilot data pack.

    Three leads at different points of their life, then ten customers spread across every
    Commercial Offer lifecycle stage, all with full statutory identity and real BOQ line shapes.

    Approval-for-issue needs COMMERCIAL_OFFER_QUOTE_APPROVE, which SALES_USER does not hold
    (Slice 9E, owner decision 4), so a second seeded actor with the SALES_MANAGER role performs
    every approval. That is not a workaround - it is the segregation the slice deliberately
    built, and seeding through a single actor would quietly bypass it."""
    with SessionLocal() as db:
        approver = resolve_actor(db, "manager1")

    records: dict[str, Any] = {
        lead["key"]: _seed_uat_lead(
            run_id=run_id,
            actor=actor,
            approver_public_id=approver["public_id"],
            lead=lead,
            index=index,
        )
        for index, lead in enumerate(UAT_LEADS)
    }
    records.update(
        {
            customer["key"]: _seed_uat_customer(
                run_id=run_id,
                actor=actor,
                approver_public_id=approver["public_id"],
                customer=customer,
                index=index,
            )
            for index, customer in enumerate(UAT_CUSTOMERS)
        }
    )
    return records


# --- Slice 7D Part 3: the contract period, extensions and copying terms between lines -------------


def _build_work_order_contract_period(*, run_id: str, actor_public_id: str, suffix: str) -> dict[str, Any]:
    """A Work Order set up so every Part 3 screen has something real to show.

    Deliberately shaped for the owner's screen check: three lines, the first with two billing-terms
    periods so copying carries more than one, the second with terms of its own so replacing asks for
    confirmation, and the third with none so it is ticked to begin with. The contract dates and one
    extension are left for the tester to record, so the empty state and the first save are both seen.

    Since Slice 7D Part 5 the first line also shows the shift pattern and the crew's food, accommodation
    and travel, answered in full: two shifts each at its own rate, then three shifts at one rate from
    1 July 2027, and one operator and one helper whose upkeep differs (_MONTHLY_TERMS_PART_5).
    """
    # create_offer_with_line leaves one line; two more give the three the screen check needs.
    record = _build_accepted_offer(
        run_id=run_id, actor_public_id=actor_public_id, suffix=suffix, with_work_order=False, extra_lines=({}, {})
    )
    offer_public_id = record["commercial_offer"]["public_id"]
    work_order = create_work_order(actor_public_id=actor_public_id, offer_public_id=offer_public_id)
    record["work_orders"].append(work_order)
    work_order_public_id = work_order["public_id"]
    line_public_ids = work_order["line_public_ids"]

    # Line 1: a monthly line, with a second period starting part-way through, so "Apply these terms
    # to other lines" has two periods to carry (owner decision 20c).
    add_work_order_line_billing_terms_period(
        actor_public_id=actor_public_id,
        work_order_public_id=work_order_public_id,
        line_public_id=line_public_ids[0],
        **_MONTHLY_TERMS_PART_5,
        **_LINE_ONCE_TERMS,
    )
    add_work_order_line_billing_terms_period(
        actor_public_id=actor_public_id,
        work_order_public_id=work_order_public_id,
        line_public_id=line_public_ids[0],
        expected_period_count=1,
        expected_latest_term_revision=1,
        effective_from=date(2027, 7, 1),
        **_MONTHLY_TERMS_PART_5_FROM_JULY,
    )

    # Line 2 already has terms, on a different basis and rate, so replacing it asks for confirmation
    # and the difference is visible before and after (owner decision 20a and 20b).
    if len(line_public_ids) > 1:
        add_work_order_line_billing_terms_period(
            actor_public_id=actor_public_id,
            work_order_public_id=work_order_public_id,
            line_public_id=line_public_ids[1],
            **_SHIFT_TERMS,
            **_LINE_ONCE_TERMS,
        )

    # Line 3 is left with no terms at all: it is what the copy is for, and is ticked to begin with.
    record["contract_period_demo"] = {
        "work_order_public_id": work_order_public_id,
        "line_public_ids": line_public_ids,
        "lines_with_terms": line_public_ids[:2],
        "lines_without_terms": line_public_ids[2:],
        "source_line_public_id": line_public_ids[0],
        "source_period_count": 2,
        "part_5_line_public_id": line_public_ids[0],
    }
    return record


# A complete monthly term set and a complete shift one, so both lines read "Terms complete" and the
# difference between them is obvious on screen. Shaped like the Annexure-10 examples the Part 1 tests
# use, without importing from a test module.
_MONTHLY_TERMS: dict[str, Any] = {
    "billing_uom_code": "MONTH",
    "contracted_hours_per_billing_unit": Decimal("260.00"),
    "contracted_working_days_per_month": Decimal("26.00"),
    "normal_rate_amount": Decimal("100000.00"),
    "weekly_off_day_codes": ["SUN"],
    "off_day_work_treatment_code": "OVERTIME_RATE",
    "overtime_rate_method_code": "PERCENT_OF_NORMAL",
    "overtime_rate_percent": Decimal("125.00"),
    "month_overtime_hours_basis_code": "AVAILABLE_HOURS",
    "month_overtime_counting_code": "WHOLE_MONTH",
    "breakdown_treatment_code": "REDUCE_BILLED_HOURS",
    "customer_idle_treatment_code": "AS_WORKING_HOURS",
    "part_month_basis_code": "CALENDAR_DAYS",
    # Slice 7D Part 5's shift pattern, where Part 2's night shift was: not in the Work Order.
    "shift_pattern_code": "NONE",
    "fuel_treatment_code": "NONE",
    # Slice 7D Part 4's two terms, answered, so the line still reads "Terms complete".
    "extra_km_allowance_code": "NONE",
    "crew_code": "NONE",
}
_SHIFT_TERMS: dict[str, Any] = {
    "billing_uom_code": "SHIFT",
    "contracted_hours_per_billing_unit": Decimal("8.00"),
    "normal_rate_amount": Decimal("12000.00"),
    "weekly_off_day_codes": ["SUN"],
    "off_day_work_treatment_code": "OVERTIME_RATE",
    "overtime_rate_method_code": "RATE_PER_HOUR",
    "overtime_rate_amount": Decimal("1800.00"),
    "breakdown_treatment_code": "REDUCE_BILLED_HOURS",
    "customer_idle_treatment_code": "AS_WORKING_HOURS",
    "minimum_guarantee_code": "NONE",
    # Slice 7D Part 5's shift pattern, where Part 2's night shift was: not in the Work Order.
    "shift_pattern_code": "NONE",
    "fuel_treatment_code": "NONE",
    "extra_km_allowance_code": "NONE",
    "crew_code": "NONE",
}
# Mobilisation and demobilisation belong to the line's first period only (Part 2, owner decision 8).
_LINE_ONCE_TERMS: dict[str, Any] = {
    "mobilisation_charge_code": "NONE",
    "demobilisation_charge_code": "NONE",
}

# Slice 7D Part 5: once the crew is stated its food, accommodation and travel are asked, so a term set stating its crew
# answers them - here every item "not in the Work Order" - to stay complete.
_UPKEEP_NOT_IN_WORK_ORDER: dict[str, Any] = {str(cell["code"]): "NONE" for cell in WORK_ORDER_LINE_UPKEEP_CELLS}

# Slice 7D Part 5's screen check, on the contract-period scenario's monthly line: a 10-hour first shift at
# the Work Order rate and an 8-hour second shift at 90% of it, 26 days a month; one operator and one helper,
# their food and accommodation provided by the customer's camp, except the helper's accommodation at
# INR 3,000 a month billed to PBL separately; the trip to and from the job at INR 2,500 a trip for the
# operator, deducted from PBL's invoice; daily travel not in the Work Order.
_UPKEEP_ANSWERED: dict[str, Any] = {
    "upkeep_food_operator_code": "PROVIDED",
    "upkeep_food_helper_code": "PROVIDED",
    "upkeep_accommodation_operator_code": "PROVIDED",
    "upkeep_accommodation_helper_code": "PROVIDED_AT_COST",
    "upkeep_accommodation_helper_amount": Decimal("3000.00"),
    "upkeep_accommodation_helper_unit_code": "PER_PERSON_PER_MONTH",
    "upkeep_accommodation_helper_recovery_code": "BILLED_SEPARATELY",
    "upkeep_job_travel_operator_code": "PROVIDED_AT_COST",
    "upkeep_job_travel_operator_amount": Decimal("2500.00"),
    "upkeep_job_travel_operator_unit_code": "PER_PERSON_PER_TRIP",
    "upkeep_job_travel_operator_recovery_code": "DEDUCTED_FROM_INVOICE",
    "upkeep_job_travel_helper_code": "NONE",
    "upkeep_daily_travel_operator_code": "NONE",
    "upkeep_daily_travel_helper_code": "NONE",
}
_MONTHLY_TERMS_PART_5: dict[str, Any] = {
    **_MONTHLY_TERMS,
    "shift_pattern_code": "TWO_SHIFTS",
    "shift_1_hours": Decimal("10.00"),
    "shift_2_hours": Decimal("8.00"),
    "shift_rate_code": "PER_SHIFT",
    "shift_2_rate_method_code": "PERCENT_OF_NORMAL",
    "shift_2_rate_percent": Decimal("90.00"),
    "shift_2_working_days_per_month": Decimal("26.00"),
    # Overtime is charged on these two shifts, counted over the whole month, and per shift.
    "overtime_counted_per_code": "PER_SHIFT",
    "crew_code": "STATED",
    "crew_operators_per_unit": 1,
    "crew_helpers_per_unit": 1,
    "extra_crew_charge_code": "NONE",
    **_UPKEEP_ANSWERED,
}
# From 1 July 2027: three 8-hour shifts at one rate for all of them, overtime counted day by day and for the whole day.
_MONTHLY_TERMS_PART_5_FROM_JULY: dict[str, Any] = {
    **{key: value for key, value in _MONTHLY_TERMS_PART_5.items() if not key.startswith("shift_2_rate")},
    "normal_rate_amount": Decimal("112000.00"),
    "contracted_hours_per_billing_unit": Decimal("624.00"),
    "month_overtime_counting_code": "DAY_BY_DAY",
    "shift_pattern_code": "THREE_SHIFTS",
    "shift_1_hours": Decimal("8.00"),
    "shift_2_hours": Decimal("8.00"),
    "shift_3_hours": Decimal("8.00"),
    "shift_rate_code": "SAME_FOR_ALL_SHIFTS",
    "shift_2_working_days_per_month": None,
    "overtime_counted_per_code": "PER_DAY",
}


def scenario_work_order_contract_period(run_id: str, actor: dict[str, str]) -> dict[str, Any]:
    return {
        "contract_period_target": _build_work_order_contract_period(
            run_id=run_id, actor_public_id=actor["public_id"], suffix="ContractPeriod"
        )
    }


# --- Slice 7D Part 4: extra kilometres, crew, and the holidays a Work Order names ------------------


def _build_work_order_billing_terms_part_4(*, run_id: str, actor_public_id: str, suffix: str) -> dict[str, Any]:
    """A Work Order set up for the owner's Part 4 screen check.

    Three lines. Line 1 has complete Part 1 to 3 terms saved as a period recorded before Part 4 would
    be: extra kilometres and crew not answered, so the line shows exactly those two still needed. Line
    2 has every Part 4 term answered - an allowance per day, two operators and two helpers, and a rate
    for each extra person - so the new cards read "Answered". Line 3 has no terms at all.

    The contract runs from 1 October 2026 to 30 September 2027, so a holiday can be listed inside it
    and one outside it is refused, naming both dates. The holiday list itself is left unanswered, so
    the "not answered yet" state and the first save are both seen.
    """
    record = _build_accepted_offer(
        run_id=run_id, actor_public_id=actor_public_id, suffix=suffix, with_work_order=False, extra_lines=({}, {})
    )
    offer_public_id = record["commercial_offer"]["public_id"]
    work_order = create_work_order(actor_public_id=actor_public_id, offer_public_id=offer_public_id)
    record["work_orders"].append(work_order)
    work_order_public_id = work_order["public_id"]
    line_public_ids = work_order["line_public_ids"]

    set_work_order_contract_period(
        actor_public_id=actor_public_id,
        work_order_public_id=work_order_public_id,
        contract_start_date="2026-10-01",
        contract_end_basis_code="FIXED_DATE",
        contract_end_date="2027-09-30",
    )

    # Line 1: every term Parts 1 and 2 know, and neither Part 4 term.
    before_part_4 = {
        key: value for key, value in _SHIFT_TERMS.items() if key not in ("extra_km_allowance_code", "crew_code")
    }
    add_work_order_line_billing_terms_period(
        actor_public_id=actor_public_id,
        work_order_public_id=work_order_public_id,
        line_public_id=line_public_ids[0],
        **{**before_part_4, "billing_uom_code": "DAY", "contracted_hours_per_billing_unit": Decimal("12.00")},
        **_LINE_ONCE_TERMS,
    )

    # Line 2: Part 4 answered in full.
    if len(line_public_ids) > 1:
        add_work_order_line_billing_terms_period(
            actor_public_id=actor_public_id,
            work_order_public_id=work_order_public_id,
            line_public_id=line_public_ids[1],
            **{
                **_SHIFT_TERMS,
                "extra_km_allowance_code": "KM_PER_DAY",
                "extra_km_included_km": Decimal("100.00"),
                "extra_km_rate_amount": Decimal("45.00"),
                "crew_code": "STATED",
                "crew_operators_per_unit": 2,
                "crew_helpers_per_unit": 2,
                "extra_crew_charge_code": "RATE_PER_PERSON",
                "extra_crew_operator_rate_amount": Decimal("1800.00"),
                "extra_crew_helper_rate_amount": Decimal("900.00"),
                # Slice 7D Part 5: the crew's upkeep answered, so the line still reads complete.
                **_UPKEEP_NOT_IN_WORK_ORDER,
            },
            **_LINE_ONCE_TERMS,
        )

    record["billing_terms_part_4_demo"] = {
        "work_order_public_id": work_order_public_id,
        "line_public_ids": line_public_ids,
        "line_without_part_4_terms": line_public_ids[0],
        "line_with_part_4_terms": line_public_ids[1] if len(line_public_ids) > 1 else None,
        "contract_start_date": "2026-10-01",
        "contract_end_date": "2027-09-30",
    }
    return record


def scenario_work_order_billing_terms_part_4(run_id: str, actor: dict[str, str]) -> dict[str, Any]:
    return {
        "billing_terms_part_4_target": _build_work_order_billing_terms_part_4(
            run_id=run_id, actor_public_id=actor["public_id"], suffix="BillingTermsPart4"
        )
    }


# --- HOL-1: PBL's holiday calendar, and a Work Order's changes to it ----------------------------------------------

# A day line with an overtime rate per hour, and its terms answered in full, so its line reads "Terms complete".
_DAY_TERMS_WITH_OVERTIME: dict[str, Any] = {
    **_SHIFT_TERMS,
    "billing_uom_code": "DAY",
    "contracted_hours_per_billing_unit": Decimal("10.00"),
    "extra_km_allowance_code": "NONE",
    "crew_code": "NONE",
}


def _build_holiday_work_order(
    *, run_id: str, actor_public_id: str, suffix: str, contract_start: str, contract_end: str
) -> dict[str, Any]:
    """A Work Order with three lines for the holidays that apply: line 1's site in Gujarat and line 2's in Maharashtra,
    both on a day basis with an overtime rate; line 3 with no site, billed by the hour - which has no overtime - so a
    working day at the overtime rate shows that it records none. The holidays are left unanswered."""
    record = _build_accepted_offer(
        run_id=run_id, actor_public_id=actor_public_id, suffix=suffix, with_work_order=False, extra_lines=({}, {})
    )
    offer_public_id = record["commercial_offer"]["public_id"]
    work_order = create_work_order(actor_public_id=actor_public_id, offer_public_id=offer_public_id)
    record["work_orders"].append(work_order)
    work_order_public_id = work_order["public_id"]
    lines = work_order["line_public_ids"]
    set_work_order_contract_period(
        actor_public_id=actor_public_id,
        work_order_public_id=work_order_public_id,
        contract_start_date=contract_start,
        contract_end_basis_code="FIXED_DATE",
        contract_end_date=contract_end,
    )
    for line_public_id, (state, place) in zip(lines, (("Gujarat", "Dahej"), ("Maharashtra", "Chakan"))):
        site = add_account_address(
            actor_public_id=actor_public_id,
            account_public_id=record["account"]["public_id"],
            address_type_code="SITE",
            address_line1=f"Plot 7, Invented Industrial Estate ({suffix})",
            city=place,
            state=state,
        )
        set_work_order_line_detail(
            actor_public_id=actor_public_id,
            work_order_public_id=work_order_public_id,
            line_public_id=line_public_id,
            site_address_public_id=site["public_id"],
        )
        add_work_order_line_billing_terms_period(
            actor_public_id=actor_public_id,
            work_order_public_id=work_order_public_id,
            line_public_id=line_public_id,
            **_DAY_TERMS_WITH_OVERTIME,
            **_LINE_ONCE_TERMS,
        )
    if len(lines) > 2:
        add_work_order_line_billing_terms_period(
            actor_public_id=actor_public_id,
            work_order_public_id=work_order_public_id,
            line_public_id=lines[2],
            billing_uom_code="HOUR",
            normal_rate_amount=Decimal("2500.00"),
        )
    record["holiday_demo"] = {
        "work_order_public_id": work_order_public_id,
        "line_public_ids": lines,
        "contract_start_date": contract_start,
        "contract_end_date": contract_end,
    }
    return record


def _build_holiday_calendar_target(*, run_id: str, actor_public_id: str, suffix: str, calendar_year: int) -> dict[str, Any]:
    """A year of PBL's calendar far ahead - Republic Day and Holi for all of India, 1 May as Gujarat Day (festival,
    Gujarat) and as Maharashtra Day (national, Maharashtra) - not marked complete, and a Work Order over the whole year.
    The year is the run's by provenance (`holiday_calendar_years`), and its cleanup removes it."""
    year = create_holiday_calendar_year(
        actor_public_id=actor_public_id,
        calendar_year=calendar_year,
        holidays=[
            ("01-26", "NATIONAL", "Republic Day", []),
            ("03-22", "FESTIVAL", "Holi", []),
            ("05-01", "FESTIVAL", "Gujarat Day", ["IN-GJ"]),
            ("05-01", "NATIONAL", "Maharashtra Day", ["IN-MH"]),
        ],
    )
    record = _build_holiday_work_order(
        run_id=run_id,
        actor_public_id=actor_public_id,
        suffix=suffix,
        contract_start=f"{calendar_year}-01-01",
        contract_end=f"{calendar_year}-12-31",
    )
    record["holiday_calendar_years"] = [year]
    record["holiday_demo"]["calendar_year"] = calendar_year
    return record


def scenario_holiday_calendar(run_id: str, actor: dict[str, str]) -> dict[str, Any]:
    """HOL-1 screen check: the Work Order of design section 6 - contract 1 December 2026 to 30 November 2027 - with no
    calendar started by the run: the tester sets up 2027 (on a test site, never on PBL's own)."""
    return {
        "holiday_target": _build_holiday_work_order(
            run_id=run_id,
            actor_public_id=actor["public_id"],
            suffix="HolidayCalendar",
            contract_start="2026-12-01",
            contract_end="2027-11-30",
        )
    }


# --- WRR-001: what Work Order lines need on site -----------------------------------------------------


def _build_work_order_resource_requirements(*, run_id: str, actor_public_id: str, suffix: str) -> dict[str, Any]:
    """A Work Order set up for the owner's WRR-001 screen check.

    Three lines: a crane line with a site, crew terms of one operator and one helper, and an urgent
    requirement for one crawler crane of at least 250 t; a manlift line with no site and a requirement
    for two articulating-boom platforms of at least 26 m working height, so its site warning shows; and a
    forklift line with no requirement, left for the tester to add one. The contract runs from 1 October
    2026 to 30 September 2027, so a date outside it is refused, naming both dates.
    """
    record = _build_accepted_offer(
        run_id=run_id,
        actor_public_id=actor_public_id,
        suffix=suffix,
        with_work_order=False,
        extra_lines=(
            {
                "scope_description": "Articulating boom manlift, 26 m working height",
                "equipment_service_category": "Manlifts",
                "quantity": Decimal("2.00"),
                "uom": "Mon",
            },
            {
                "scope_description": "5 t forklift for yard handling",
                "equipment_service_category": "Forklift",
                "quantity": Decimal("30.00"),
                "uom": "Days",
            },
        ),
    )
    offer_public_id = record["commercial_offer"]["public_id"]
    work_order = create_work_order(actor_public_id=actor_public_id, offer_public_id=offer_public_id)
    record["work_orders"].append(work_order)
    work_order_public_id = work_order["public_id"]
    crane_line, manlift_line, forklift_line = work_order["line_public_ids"][:3]

    set_work_order_contract_period(
        actor_public_id=actor_public_id,
        work_order_public_id=work_order_public_id,
        contract_start_date="2026-10-01",
        contract_end_basis_code="FIXED_DATE",
        contract_end_date="2027-09-30",
    )
    site = add_account_address(
        actor_public_id=actor_public_id,
        account_public_id=record["account"]["public_id"],
        address_type_code="SITE",
        address_line1="Berth 4, Fishing Harbour",
        city="Kakinada",
        state="Andhra Pradesh",
    )
    set_work_order_line_detail(
        actor_public_id=actor_public_id,
        work_order_public_id=work_order_public_id,
        line_public_id=crane_line,
        site_address_public_id=site["public_id"],
    )
    add_work_order_line_billing_terms_period(
        actor_public_id=actor_public_id,
        work_order_public_id=work_order_public_id,
        line_public_id=crane_line,
        **{
            **_SHIFT_TERMS,
            "crew_code": "STATED",
            "crew_operators_per_unit": 1,
            "crew_helpers_per_unit": 1,
            "extra_crew_charge_code": "NONE",
        },
        **_LINE_ONCE_TERMS,
    )

    crane = create_resource_requirement(
        actor_public_id=actor_public_id,
        work_order_public_id=work_order_public_id,
        line_public_id=crane_line,
        units_required=1,
        required_from="2026-10-15",
        equipment_class_code="CRANE",
        equipment_type_code="CRAWLER",
        capabilities=[("RATED_CAPACITY", Decimal("250"))],
        crew_operators_required=1,
        crew_helpers_required=1,
        priority_code="URGENT",
    )
    manlift = create_resource_requirement(
        actor_public_id=actor_public_id,
        work_order_public_id=work_order_public_id,
        line_public_id=manlift_line,
        units_required=2,
        required_from="2026-11-01",
        equipment_class_code="AERIAL_WORK_PLATFORM",
        equipment_type_code="ARTICULATING_BOOM",
        capabilities=[("WORKING_HEIGHT", Decimal("26"))],
        crew_operators_required=1,
    )
    record["resource_requirement_demo"] = {
        "work_order_public_id": work_order_public_id,
        "crane_line_public_id": crane_line,
        "manlift_line_public_id": manlift_line,
        "forklift_line_public_id": forklift_line,
        "crane_requirement": crane,
        "manlift_requirement": manlift,
        "contract_start_date": "2026-10-01",
        "contract_end_date": "2027-09-30",
    }
    return record


def _build_equipment_reference_target(*, run_id: str, actor_public_id: str) -> dict[str, Any]:
    """ERT-1: invented machines brought in from an invented Plum report, and a second invented report
    for the Playwright test and the screen check to upload, map, read, pair and confirm.

    Every machine number, model name and odd value carries the run's own token, so nothing here can meet
    a real report's machines, names or values. Plum's report itself is never used here (design, section
    16); the dummified copy under backend/tests/fixtures is for the transformer's own test.

    Cleanup finds what this run made by provenance (TE-4): the models and the first import are named
    here; the second report's import - uploaded later, from the screen - is this run's because only this
    run's file has its fingerprint; machines by the import that brought them in; value rules by the
    import they were recorded on; mappings by the model names this run's reports carry, listed in the
    manifest - a mapping of any other name to a run's model makes cleanup refuse.

    ERT-2 adds a second crane model with two cranes of it, in both reports, and kit held for it: a boom
    insert model with two pieces, a counterweight model with a counted set of four, and a hook block model
    with none, for the Playwright test and the screen check to add to. The cranes are of their own model so
    the carrier's pair proposal above stays unambiguous. Kit models are named in the manifest like every
    model; pieces of them are the run's by their model, including pieces added later from the screen.
    """
    token = run_id.rsplit("-", 1)[-1].upper()
    crane = create_equipment_model(
        actor_public_id=actor_public_id,
        maker="ACME",
        model_name=f"AC 100 {token}",
        class_code="CRANE",
        type_code="ALL_TERRAIN",
        capabilities=[("RATED_CAPACITY", Decimal("100")), ("MAIN_BOOM_LENGTH", Decimal("60"))],
    )
    carrier = create_equipment_model(
        actor_public_id=actor_public_id, maker="ACME", model_name=f"AC 100 {token}", class_code="CRANE_CARRIER"
    )
    manlift = create_equipment_model(
        actor_public_id=actor_public_id,
        maker="LIFTCO",
        model_name=f"LX 18 {token}",
        class_code="AERIAL_WORK_PLATFORM",
        type_code="SCISSOR",
        capabilities=[("WORKING_HEIGHT", Decimal("18")), ("PLATFORM_CAPACITY", Decimal("230"))],
    )
    kit_crane = create_equipment_model(
        actor_public_id=actor_public_id,
        maker="ACME",
        model_name=f"CC 100 {token}",
        class_code="CRANE",
        type_code="CRAWLER",
        capabilities=[("RATED_CAPACITY", Decimal("100")), ("MAIN_BOOM_LENGTH", Decimal("50"))],
    )
    super_name, chassis_name, manlift_name = f"{token} ACME AC 100 SUPER", f"{token} ACME AC 100 CHASSIS", f"{token} LIFTCO LX 18"
    kit_crane_name = f"{token} ACME CC 100"
    # 8A core: four crawler cranes of a 250 t model, for allocating - two that can be allocated, one with a
    # warning, one that cannot - and kit held for their model.
    allocation_crane = create_equipment_model(
        actor_public_id=actor_public_id,
        maker="ACME",
        model_name=f"CC 250 {token}",
        class_code="CRANE",
        type_code="CRAWLER",
        capabilities=[("RATED_CAPACITY", Decimal("250")), ("MAIN_BOOM_LENGTH", Decimal("72"))],
    )
    allocation_crane_name = f"{token} ACME CC 250"
    map_equipment_model_name(actor_public_id=actor_public_id, source_name=allocation_crane_name, model_public_id=allocation_crane["public_id"])
    # ELG-2: two crawler cranes of an 80 t model for the certificate reminders - one whose papers run out in 20, 10
    # and 5 days with a load test already run out, and one held on a job of its own (reminder_target) - with a sling
    # held for them. Below the 200 t the allocation requirement asks for, so the allocation test never meets them.
    reminder_crane = create_equipment_model(
        actor_public_id=actor_public_id,
        maker="ACME",
        model_name=f"CC 80 {token}",
        class_code="CRANE",
        type_code="CRAWLER",
        capabilities=[("RATED_CAPACITY", Decimal("80")), ("MAIN_BOOM_LENGTH", Decimal("48"))],
    )
    reminder_crane_name = f"{token} ACME CC 80"
    map_equipment_model_name(actor_public_id=actor_public_id, source_name=reminder_crane_name, model_public_id=reminder_crane["public_id"])
    # ELG-1: a second wheeled crane, held by Plum as superstructure and carrier and paired when the first report
    # is confirmed, for certificates on a crane and its carrier.
    wheeled = create_equipment_model(
        actor_public_id=actor_public_id,
        maker="ACME",
        model_name=f"AC 250 {token}",
        class_code="CRANE",
        type_code="ALL_TERRAIN",
        capabilities=[("RATED_CAPACITY", Decimal("250")), ("MAIN_BOOM_LENGTH", Decimal("70"))],
    )
    wheeled_carrier = create_equipment_model(
        actor_public_id=actor_public_id, maker="ACME", model_name=f"AC 250 {token}", class_code="CRANE_CARRIER"
    )
    wheeled_super_name, wheeled_chassis_name = f"{token} ACME AC 250 SUPER", f"{token} ACME AC 250 CHASSIS"
    map_equipment_model_name(actor_public_id=actor_public_id, source_name=wheeled_super_name, model_public_id=wheeled["public_id"])
    map_equipment_model_name(actor_public_id=actor_public_id, source_name=wheeled_chassis_name, model_public_id=wheeled_carrier["public_id"])
    map_equipment_model_name(actor_public_id=actor_public_id, source_name=super_name, model_public_id=crane["public_id"])
    map_equipment_model_name(actor_public_id=actor_public_id, source_name=manlift_name, model_public_id=manlift["public_id"])
    map_equipment_model_name(actor_public_id=actor_public_id, source_name=kit_crane_name, model_public_id=kit_crane["public_id"])

    def number(label: str) -> str:
        return f"TEST-{token}-{label}"

    def row(label: str, **values: str) -> dict[str, str]:
        return {
            "VehicleNo": number(label),
            "Status": "Active",
            "Owner": "TEST OWNER",
            "EngineNo": f"ENG-{token}-{label}",
            "ChassisNo": f"CHS-{token}-{label}",
            "PAN": "AAAAA0000A",
            **values,
        }

    crane_row = row("CR1", ScheduleMaintanceType=super_name, VehCategory="CRANES", Capacity="100", CommencedYear="2015")
    manlift_row = row("ML1", ScheduleMaintanceType=manlift_name, VehCategory="MAN LIFTS", Capacity="230", CommencedYear="2019")
    mystery_row = row("CR2", ScheduleMaintanceType=f"{token} MYSTERY CRANE", VehCategory="CRANES", Capacity="60", CommencedYear="2012")
    kit_crane_rows = [
        row("KC1", ScheduleMaintanceType=kit_crane_name, VehCategory="CRANES", Capacity="100", CommencedYear="2018"),
        row("KC2", ScheduleMaintanceType=kit_crane_name, VehCategory="CRANES", Capacity="100", CommencedYear="2019"),
    ]
    wheeled_rows = [
        row("WC1", ScheduleMaintanceType=wheeled_super_name, VehCategory="CRANES", Capacity="250", CommencedYear="2017"),
        row("WC1C", ScheduleMaintanceType=wheeled_chassis_name, VehCategory="CRANES", Capacity="250", CommencedYear="2017"),
    ]
    allocation_rows = [
        row(label, ScheduleMaintanceType=allocation_crane_name, VehCategory="CRANES", Capacity="250", CommencedYear="2020")
        for label in ("CW1", "CW2", "CW3", "CW4")
    ]
    reminder_rows = [
        row(label, ScheduleMaintanceType=reminder_crane_name, VehCategory="CRANES", Capacity="80", CommencedYear="2021")
        for label in ("RM1", "RM2")
    ]
    first = invented_plum_report(
        [crane_row, manlift_row, mystery_row, *kit_crane_rows, *wheeled_rows, *allocation_rows, *reminder_rows],
        title=f"Own Vehicle Complete Information Report (test {token})",
    )
    first_import = upload_and_publish_equipment_report(
        actor_public_id=actor_public_id, content=first, report_date=business_time.india_today(), pairs=[(number("WC1C"), number("WC1"))]
    )

    # ERT-2: kit held for the second crane model, shared by its two cranes.
    fits = [kit_crane["public_id"]]
    insert = create_equipment_model(
        actor_public_id=actor_public_id,
        maker="ACME",
        model_name=f"CC 100 insert 6 m {token}",
        class_code="BOOM_JIB_SECTION",
        type_code="MAIN_BOOM_INSERT",
        capabilities=[("LENGTH", Decimal("6")), ("WEIGHT", Decimal("0.75"))],
        fits_model_public_ids=fits,
        maker_part_number=f"PN-INS-{token}",
    )
    counterweight = create_equipment_model(
        actor_public_id=actor_public_id,
        maker="ACME",
        model_name=f"CC 100 block 3.7 t {token}",
        class_code="COUNTERWEIGHT",
        type_code="UPPER_COUNTERWEIGHT",
        capabilities=[("WEIGHT", Decimal("3.7"))],
        fits_model_public_ids=fits,
    )
    hook = create_equipment_model(
        actor_public_id=actor_public_id,
        maker="ACME",
        model_name=f"CC 100 hook block 100 t {token}",
        class_code="HOOK_BLOCK",
        type_code="HOOK_BLOCK",
        capabilities=[("RATED_CAPACITY", Decimal("100")), ("WEIGHT", Decimal("1.2"))],
        fits_model_public_ids=fits,
    )
    kc1 = number("KC1")
    inserts = add_equipment_kit(
        actor_public_id=actor_public_id, kit_model_public_id=insert["public_id"], count=2, from_machine_number=kc1
    )
    blocks = add_equipment_kit(
        actor_public_id=actor_public_id, kit_model_public_id=counterweight["public_id"], count=4, from_machine_number=kc1
    )
    # ELG-1: a sling held for the crawler cranes, examined five months ago - slings every 6 months (IS 12735).
    sling = create_equipment_model(
        actor_public_id=actor_public_id,
        maker="LIFTCO",
        model_name=f"Sling 10 t {token}",
        class_code="LIFTING_TACKLE",
        type_code="SLING",
        capabilities=[("RATED_CAPACITY", Decimal("10")), ("WEIGHT", Decimal("0.02"))],
        fits_model_public_ids=fits,
    )
    [sling_piece] = add_equipment_kit(actor_public_id=actor_public_id, kit_model_public_id=sling["public_id"], count=1, from_machine_number=kc1)
    eligibility = _seed_certificates(
        actor_public_id=actor_public_id,
        token=token,
        crane_number=number("WC1"),
        carrier_number=number("WC1C"),
        marked_crawler_number=number("KC2"),
        sling_public_id=sling_piece["public_id"],
    )

    allocation = _seed_allocation_equipment(
        actor_public_id=actor_public_id, token=token, crane_model_public_id=allocation_crane["public_id"], numbers=[number(label) for label in ("CW1", "CW2", "CW3", "CW4")]
    )
    reminders = _seed_reminder_equipment(
        actor_public_id=actor_public_id, token=token, crane_model_public_id=reminder_crane["public_id"], numbers=[number("RM1"), number("RM2")]
    )

    odd_capacity = f"230 KG {token}"
    second = invented_plum_report(
        [
            crane_row,
            manlift_row,
            mystery_row,
            *kit_crane_rows,
            *wheeled_rows,
            *allocation_rows,
            *reminder_rows,
            row("CR1C", ScheduleMaintanceType=chassis_name, VehCategory="CRANES", Capacity="100", CommencedYear="2015"),
            row("ML2", ScheduleMaintanceType=manlift_name, VehCategory="MAN LIFTS", Capacity=odd_capacity, CommencedYear="2021"),
        ],
        title=f"Own Vehicle Complete Information Report (test {token}, second)",
    )
    return {
        "equipment_models": [
            crane,
            carrier,
            manlift,
            kit_crane,
            insert,
            counterweight,
            hook,
            wheeled,
            wheeled_carrier,
            sling,
            allocation_crane,
            *allocation.pop("models"),
            reminder_crane,
            *reminders.pop("models"),
        ],
        "equipment_imports": [{"public_id": first_import["public_id"]}],
        "equipment_report_fingerprints": [hashlib.sha256(second.encode("utf-8")).hexdigest()],
        # Every Plum model name the run's two reports carry: a mapping of one is the run's, whoever made it.
        "equipment_source_names": [
            super_name,
            chassis_name,
            manlift_name,
            f"{token} MYSTERY CRANE",
            kit_crane_name,
            wheeled_super_name,
            wheeled_chassis_name,
            allocation_crane_name,
            reminder_crane_name,
        ],
        "equipment_allocation": {**allocation, "crane_model_label": allocation_crane["label"]},
        "equipment_reminders": reminders,
        "equipment_kit": {
            "crane_model_public_id": kit_crane["public_id"],
            "crane_model_label": kit_crane["label"],
            "crane_machine_numbers": [number("KC1"), number("KC2")],
            "insert_model_label": insert["label"],
            "insert_references": [item["reference"] for item in inserts],
            "counterweight_model_label": counterweight["label"],
            "counterweight_reference": blocks[0]["reference"],
            "hook_model_public_id": hook["public_id"],
            "hook_model_label": hook["label"],
        },
        "equipment_eligibility": {
            **eligibility,
            "crane_machine_number": number("WC1"),
            "carrier_machine_number": number("WC1C"),
            # ERT-2's CC 100 cranes are crawlers: the second has its road papers marked not applicable; the first
            # is left for the tester and the Playwright test to mark.
            "marked_crawler_machine_number": number("KC2"),
            "open_crawler_machine_number": number("KC1"),
            "unmapped_crane_machine_number": number("CR2"),
            "sling_reference": sling_piece["reference"],
            "sling_public_id": sling_piece["public_id"],
        },
        "equipment_demo": {
            "token": token,
            "crane_machine_number": number("CR1"),
            "carrier_machine_number": number("CR1C"),
            "new_manlift_machine_number": number("ML2"),
            "unmapped_machine_number": number("CR2"),
            "chassis_model_name": chassis_name,
            "carrier_model_label": carrier["label"],
            "carrier_model_public_id": carrier["public_id"],
            "odd_capacity_value": odd_capacity,
            "second_report_file_name": f"plum-report-test-{token}.csv",
            "second_report_csv": second,
        },
    }


def _seed_allocation_equipment(*, actor_public_id: str, token: str, crane_model_public_id: str, numbers: list[str]) -> dict[str, Any]:
    """8A core: the four 250 t crawler cranes' papers, and kit held for their model.

    Their road papers are marked not applicable - a crawler crane is very likely not a motor vehicle (ELG-1) -
    and: the first two have both examinations, so they can be allocated; the third was examined 350 days ago
    under the 12-month rule, so its cover runs out during the job - a warning; the fourth has none, so it
    cannot be allocated. Kit: a hook block with its examinations, a counted set of four counterweight blocks,
    two boom inserts, and a sling never examined, which cannot go. Every number carries the run's token."""
    ok_1, ok_2, warns, bare = (equipment_asset_public_id(item) for item in numbers)
    today = business_time.india_today()
    competent_person = "Invented Competent Person (recognition TEST)"
    reason = "Crawler crane: not equipped to travel on public roads on its own power (invented test mark)."
    for crane in (ok_1, ok_2, warns):
        for kind in ("REGISTRATION", "INSURANCE", "POLLUTION_UNDER_CONTROL", "ROAD_TAX"):
            mark_certificate_not_applicable(actor_public_id=actor_public_id, asset_public_id=crane, kind_code=kind, reason=reason)
    for label, crane, examined in (("1", ok_1, 30), ("2", ok_2, 45), ("3", warns, 350)):
        record_equipment_certificate(
            actor_public_id=actor_public_id,
            asset_public_id=crane,
            kind_code="THOROUGH_EXAMINATION",
            number=f"CW-TE-{label}-{token}",
            issued_by=competent_person,
            issued_on=today - timedelta(days=examined),
            valid_from=today - timedelta(days=examined),
            valid_until=None,
        )
        record_equipment_certificate(
            actor_public_id=actor_public_id,
            asset_public_id=crane,
            kind_code="LOAD_TEST",
            number=f"CW-LT-{label}-{token}",
            issued_by=competent_person,
            issued_on=today - timedelta(days=400),
            valid_from=today - timedelta(days=400),
            valid_until=None,
        )
    fits = [crane_model_public_id]
    hook_model = create_equipment_model(
        actor_public_id=actor_public_id,
        maker="ACME",
        model_name=f"CC 250 hook block 250 t {token}",
        class_code="HOOK_BLOCK",
        type_code="HOOK_BLOCK",
        capabilities=[("RATED_CAPACITY", Decimal("250")), ("WEIGHT", Decimal("3.1"))],
        fits_model_public_ids=fits,
    )
    weight_model = create_equipment_model(
        actor_public_id=actor_public_id,
        maker="ACME",
        model_name=f"CC 250 block 10 t {token}",
        class_code="COUNTERWEIGHT",
        type_code="UPPER_COUNTERWEIGHT",
        capabilities=[("WEIGHT", Decimal("10"))],
        fits_model_public_ids=fits,
    )
    insert_model = create_equipment_model(
        actor_public_id=actor_public_id,
        maker="ACME",
        model_name=f"CC 250 insert 9 m {token}",
        class_code="BOOM_JIB_SECTION",
        type_code="MAIN_BOOM_INSERT",
        capabilities=[("LENGTH", Decimal("9")), ("WEIGHT", Decimal("1.1"))],
        fits_model_public_ids=fits,
    )
    sling_model = create_equipment_model(
        actor_public_id=actor_public_id,
        maker="LIFTCO",
        model_name=f"Sling 20 t {token}",
        class_code="LIFTING_TACKLE",
        type_code="SLING",
        capabilities=[("RATED_CAPACITY", Decimal("20")), ("WEIGHT", Decimal("0.03"))],
        fits_model_public_ids=fits,
    )
    [hook] = add_equipment_kit(actor_public_id=actor_public_id, kit_model_public_id=hook_model["public_id"], count=1, from_machine_number=numbers[0])
    [weights] = add_equipment_kit(actor_public_id=actor_public_id, kit_model_public_id=weight_model["public_id"], count=4, from_machine_number=numbers[0])
    inserts = add_equipment_kit(actor_public_id=actor_public_id, kit_model_public_id=insert_model["public_id"], count=2, from_machine_number=numbers[0])
    [sling] = add_equipment_kit(actor_public_id=actor_public_id, kit_model_public_id=sling_model["public_id"], count=1, from_machine_number=numbers[0])
    for kind, number in (("THOROUGH_EXAMINATION", "KIT-HB-TE"), ("LOAD_TEST", "KIT-HB-LT")):
        record_equipment_certificate(
            actor_public_id=actor_public_id,
            asset_public_id=hook["public_id"],
            kind_code=kind,
            number=f"{number}-{token}",
            issued_by=competent_person,
            issued_on=today - timedelta(days=60),
            valid_from=today - timedelta(days=60),
            valid_until=None,
        )
    return {
        "models": [hook_model, weight_model, insert_model, sling_model],
        "machine_numbers": {"ok_1": numbers[0], "ok_2": numbers[1], "warns": numbers[2], "bare": numbers[3]},
        "machines": {"ok_1": ok_1, "ok_2": ok_2, "warns": warns, "bare": bare},
        "kit": {
            "hook": hook["reference"],
            "counterweight": weights["reference"],
            "inserts": [item["reference"] for item in inserts],
            "sling": sling["reference"],
        },
    }


def _seed_reminder_equipment(*, actor_public_id: str, token: str, crane_model_public_id: str, numbers: list[str]) -> dict[str, Any]:
    """ELG-2: the certificate reminders' cranes and a sling.

    The first crane's registration and road tax are marked not applicable, as a crawler's may be (ELG-1), and its
    insurance runs out in 20 days, its pollution certificate in 10, its thorough examination in 5, and its load test
    ran out 2 days ago: on the standard paths, Admin sees all four, Operations the last three, Management the last
    two. The second crane, held on reminder_target's job from 12 days ahead, has its insurance running out in 6 days -
    before the job starts - and a sling listed on its first Trip (Own Load), whose examination runs out in 25 days,
    during the job. Every number carries the run's token; cleanup removes them, and every "seen" mark on them, with
    the run's assets."""
    running_out, on_job = (equipment_asset_public_id(item) for item in numbers)
    today = business_time.india_today()
    competent_person = "Invented Competent Person (recognition TEST)"
    reason = "Crawler crane: not equipped to travel on public roads on its own power (invented test mark)."

    def certificate(asset: str, kind: str, label: str, issued_by: str, issued_on: date, valid_until: date | None) -> None:
        record_equipment_certificate(
            actor_public_id=actor_public_id,
            asset_public_id=asset,
            kind_code=kind,
            number=f"RM-{label}-{token}",
            issued_by=issued_by,
            issued_on=issued_on,
            valid_from=issued_on,
            valid_until=valid_until,
        )

    for kind in ("REGISTRATION", "ROAD_TAX"):
        mark_certificate_not_applicable(actor_public_id=actor_public_id, asset_public_id=running_out, kind_code=kind, reason=reason)
    certificate(running_out, "INSURANCE", "INS-1", "Invented Insurance Co", today - timedelta(days=30), today + timedelta(days=20))
    certificate(running_out, "POLLUTION_UNDER_CONTROL", "PUC-1", "Invented Testing Centre", today - timedelta(days=30), today + timedelta(days=10))
    certificate(running_out, "THOROUGH_EXAMINATION", "TE-1", competent_person, today - timedelta(days=30), today + timedelta(days=5))
    certificate(running_out, "LOAD_TEST", "LT-1", competent_person, today - timedelta(days=400), today - timedelta(days=2))
    for kind in ("REGISTRATION", "POLLUTION_UNDER_CONTROL", "ROAD_TAX"):
        mark_certificate_not_applicable(actor_public_id=actor_public_id, asset_public_id=on_job, kind_code=kind, reason=reason)
    certificate(on_job, "INSURANCE", "INS-2", "Invented Insurance Co", today - timedelta(days=30), today + timedelta(days=6))
    certificate(on_job, "THOROUGH_EXAMINATION", "TE-2", competent_person, today - timedelta(days=30), None)
    certificate(on_job, "LOAD_TEST", "LT-2", competent_person, today - timedelta(days=400), None)
    sling_model = create_equipment_model(
        actor_public_id=actor_public_id,
        maker="LIFTCO",
        model_name=f"Sling 8 t {token}",
        class_code="LIFTING_TACKLE",
        type_code="SLING",
        capabilities=[("RATED_CAPACITY", Decimal("8")), ("WEIGHT", Decimal("0.02"))],
        fits_model_public_ids=[crane_model_public_id],
    )
    [sling] = add_equipment_kit(actor_public_id=actor_public_id, kit_model_public_id=sling_model["public_id"], count=1, from_machine_number=numbers[1])
    certificate(sling["public_id"], "THOROUGH_EXAMINATION", "SL-TE", competent_person, today - timedelta(days=30), today + timedelta(days=25))
    certificate(sling["public_id"], "LOAD_TEST", "SL-LT", competent_person, today - timedelta(days=30), None)
    return {
        "models": [sling_model],
        "machine_numbers": {"running_out": numbers[0], "on_job": numbers[1]},
        "machines": {"running_out": running_out, "on_job": on_job},
        "sling": {"public_id": sling["public_id"], "reference": sling["reference"]},
    }


def _build_reminder_target(*, run_id: str, actor_public_id: str, suffix: str, equipment: dict[str, Any]) -> dict[str, Any]:
    """ELG-2: a Work Order with a held allocation for the allocation reminders - one crawler crane of at least 50 t at
    a site in Gujarat (not a central-government site) from 12 days ahead for about seven weeks, filled by the run's
    second 80 t crawler, with the run's sling on its first Trip (Own Load). Warnings are accepted, as a user who ticked
    them: the crane's insurance runs out before the job starts, the sling's examination during it. Cleanup finds the
    allocation by the run's requirement, as for allocation_target."""
    record = _build_accepted_offer(run_id=run_id, actor_public_id=actor_public_id, suffix=suffix, with_work_order=True)
    work_order = record["work_orders"][0]
    work_order_public_id = work_order["public_id"]
    line = work_order["line_public_ids"][0]
    today = business_time.india_today()
    set_work_order_contract_period(
        actor_public_id=actor_public_id,
        work_order_public_id=work_order_public_id,
        contract_start_date=(today - timedelta(days=1)).isoformat(),
        contract_end_basis_code="FIXED_DATE",
        contract_end_date=(today + timedelta(days=365)).isoformat(),
    )
    site = add_account_address(
        actor_public_id=actor_public_id,
        account_public_id=record["account"]["public_id"],
        address_type_code="SITE",
        address_line1="Jetty 4, Invented Port",
        city="Dahej",
        state="Gujarat",
    )
    set_work_order_line_detail(
        actor_public_id=actor_public_id,
        work_order_public_id=work_order_public_id,
        line_public_id=line,
        site_address_public_id=site["public_id"],
        site_central_government=False,
    )
    starts, ends = today + timedelta(days=12), today + timedelta(days=60)
    requirement = create_resource_requirement(
        actor_public_id=actor_public_id,
        work_order_public_id=work_order_public_id,
        line_public_id=line,
        units_required=1,
        required_from=starts.isoformat(),
        required_to=ends.isoformat(),
        equipment_class_code="CRANE",
        equipment_type_code="CRAWLER",
        capabilities=[("RATED_CAPACITY", Decimal("50"))],
        crew_operators_required=1,
        crew_helpers_required=1,
    )
    held = allocate_machine(
        actor_public_id=actor_public_id,
        requirement_public_id=requirement["public_id"],
        machine_public_id=equipment["machines"]["on_job"],
        planned_from=starts,
        planned_to=ends,
    )
    kit_line = list_kit_on_trip(
        actor_public_id=actor_public_id,
        assignment_public_id=held["public_id"],
        assignment_version=held["version"],
        piece_public_id=equipment["sling"]["public_id"],
    )
    record["reminder_demo"] = {
        "work_order_public_id": work_order_public_id,
        "requirement_public_id": requirement["public_id"],
        "assignment_public_id": held["public_id"],
        "assignment_reference": held["reference"],
        "kit_line_public_id": kit_line["public_id"],
        "machine_numbers": equipment["machine_numbers"],
        "machines": equipment["machines"],
        "sling_reference": equipment["sling"]["reference"],
    }
    return record


def _build_allocation_target(*, run_id: str, actor_public_id: str, suffix: str, equipment: dict[str, Any]) -> dict[str, Any]:
    """8A core: a Work Order ready to allocate to - one crane line, its site in Maharashtra (not a central-
    government site), a contract from yesterday for a year, and a requirement for two crawler cranes of at least
    200 t from five days ahead for about two months, which the run's 250 t crawlers meet. Nothing is allocated:
    the tester, or Playwright, allocates. Cleanup finds allocations by the run's requirements."""
    record = _build_accepted_offer(run_id=run_id, actor_public_id=actor_public_id, suffix=suffix, with_work_order=True)
    work_order = record["work_orders"][0]
    work_order_public_id = work_order["public_id"]
    line = work_order["line_public_ids"][0]
    today = business_time.india_today()
    set_work_order_contract_period(
        actor_public_id=actor_public_id,
        work_order_public_id=work_order_public_id,
        contract_start_date=(today - timedelta(days=1)).isoformat(),
        contract_end_basis_code="FIXED_DATE",
        contract_end_date=(today + timedelta(days=365)).isoformat(),
    )
    site = add_account_address(
        actor_public_id=actor_public_id,
        account_public_id=record["account"]["public_id"],
        address_type_code="SITE",
        address_line1="Jetty 2, Invented Port",
        city="Mumbai",
        state="Maharashtra",
    )
    set_work_order_line_detail(
        actor_public_id=actor_public_id,
        work_order_public_id=work_order_public_id,
        line_public_id=line,
        site_address_public_id=site["public_id"],
        site_central_government=False,
    )
    requirement = create_resource_requirement(
        actor_public_id=actor_public_id,
        work_order_public_id=work_order_public_id,
        line_public_id=line,
        units_required=2,
        required_from=(today + timedelta(days=5)).isoformat(),
        required_to=(today + timedelta(days=60)).isoformat(),
        equipment_class_code="CRANE",
        equipment_type_code="CRAWLER",
        capabilities=[("RATED_CAPACITY", Decimal("200"))],
        crew_operators_required=1,
        crew_helpers_required=1,
    )
    record["allocation_demo"] = {
        "work_order_public_id": work_order_public_id,
        "line_public_id": line,
        "requirement_public_id": requirement["public_id"],
        "requirement_reference": requirement["requirement_reference"],
        "machines": equipment["machines"],
        "machine_numbers": equipment["machine_numbers"],
        "kit": equipment["kit"],
        "crane_model_label": equipment["crane_model_label"],
    }
    return record


def _seed_certificates(
    *, actor_public_id: str, token: str, crane_number: str, carrier_number: str, marked_crawler_number: str, sling_public_id: str
) -> dict[str, Any]:
    """ELG-1: the wheeled crane's road papers on its carrier and its thorough examination on the crane, each with
    a copy - but no load test, so the crane cannot be allocated until one is recorded; the second crawler
    crane's road papers marked not applicable; and the sling's examinations. Every number is invented and
    carries the run's token; cleanup removes them all with the run's assets."""
    today = business_time.india_today()
    crane, carrier = equipment_asset_public_id(crane_number), equipment_asset_public_id(carrier_number)
    marked = equipment_asset_public_id(marked_crawler_number)

    def years(count: int, day: date = today) -> date:
        # 29 February has no match in most years: the day before.
        try:
            return day.replace(year=day.year + count)
        except ValueError:
            return day.replace(year=day.year + count, day=28)

    def certificate(asset: str, kind: str, number: str, issued_by: str, issued_on: date, valid_until: date | None, **extra: Any) -> dict[str, Any]:
        return record_equipment_certificate(
            actor_public_id=actor_public_id,
            asset_public_id=asset,
            kind_code=kind,
            number=f"{number}-{token}",
            issued_by=issued_by,
            issued_on=issued_on,
            valid_from=issued_on,
            valid_until=valid_until,
            **extra,
        )

    three_years_ago = years(-3)
    competent_person = "Invented Competent Person (recognition TEST)"
    recorded = [
        certificate(carrier, "REGISTRATION", "RC-TEST", "Invented RTO", three_years_ago, years(12, three_years_ago) - timedelta(days=1), registered_as_code="NON_TRANSPORT"),
        certificate(carrier, "INSURANCE", "POLICY-TEST", "Invented Insurance Co", today - timedelta(days=30), today + timedelta(days=334)),
        certificate(carrier, "POLLUTION_UNDER_CONTROL", "PUC-TEST", "Invented Testing Centre", today - timedelta(days=30), today + timedelta(days=150)),
        certificate(carrier, "ROAD_TAX", "TAX-TEST", "Invented Transport Department", three_years_ago, None),
        certificate(crane, "THOROUGH_EXAMINATION", "TE-TEST", competent_person, today - timedelta(days=60), None),
        certificate(sling_public_id, "THOROUGH_EXAMINATION", "SL-TE-TEST", competent_person, today - timedelta(days=150), None),
        certificate(sling_public_id, "LOAD_TEST", "SL-LT-TEST", competent_person, today - timedelta(days=150), None),
    ]
    marks = [
        mark_certificate_not_applicable(
            actor_public_id=actor_public_id,
            asset_public_id=marked,
            kind_code=kind,
            reason="Crawler crane: not equipped to travel on public roads on its own power (invented test mark).",
        )
        for kind in ("REGISTRATION", "INSURANCE", "POLLUTION_UNDER_CONTROL", "ROAD_TAX")
    ]
    return {
        "crane_public_id": crane,
        "carrier_public_id": carrier,
        "marked_crawler_public_id": marked,
        "certificates": recorded,
        "marks": marks,
    }


def scenario_equipment_plum_import(run_id: str, actor: dict[str, str]) -> dict[str, Any]:
    return {"equipment_reference_target": _build_equipment_reference_target(run_id=run_id, actor_public_id=actor["public_id"])}


def scenario_equipment_allocation(run_id: str, actor: dict[str, str]) -> dict[str, Any]:
    equipment = _build_equipment_reference_target(run_id=run_id, actor_public_id=actor["public_id"])
    return {
        "equipment_reference_target": equipment,
        "allocation_target": _build_allocation_target(
            run_id=run_id, actor_public_id=actor["public_id"], suffix="Allocation", equipment=equipment["equipment_allocation"]
        ),
        # ELG-2: a held allocation whose machine's and kit's papers run out before and during the job.
        "reminder_target": _build_reminder_target(
            run_id=run_id, actor_public_id=actor["public_id"], suffix="Reminders", equipment=equipment["equipment_reminders"]
        ),
    }


def scenario_work_order_resource_requirements(run_id: str, actor: dict[str, str]) -> dict[str, Any]:
    return {
        "resource_requirements_target": _build_work_order_resource_requirements(
            run_id=run_id, actor_public_id=actor["public_id"], suffix="ResourceRequirements"
        )
    }


# The scenarios that confirm invented Plum reports: they seed only where no machine is held.
# TE-7: the Hiring user test's practice data, in its own module (it reuses the UAT customers' helper above).
# The user-test restart (9 October 2026): the Hiring site's pre-load, the fleet and the holiday calendar only.
from .hiring_uat import (  # noqa: E402
    FLEET_SCENARIO_NAME as HIRING_UAT_FLEET_SCENARIO,
    SCENARIO_NAME as HIRING_UAT_SCENARIO,
    require_fleet_calendar_years_free,
    scenario_hiring_uat_fleet,
    scenario_hiring_uat_seeded,
)

SCENARIOS_CONFIRMING_EQUIPMENT_REPORTS = frozenset(
    {"equipment-plum-import", "equipment-allocation", "core-regression-bundle", HIRING_UAT_SCENARIO, HIRING_UAT_FLEET_SCENARIO}
)

SCENARIOS: dict[str, Callable[[str, dict[str, str]], dict[str, Any]]] = {
    "accepted-offer-no-work-order": scenario_accepted_offer_no_work_order,
    "accepted-offer-with-work-order": scenario_accepted_offer_with_work_order,
    "rejected-offer": scenario_rejected_offer,
    "revision-requested": scenario_revision_requested,
    "blocked-handoff": scenario_blocked_handoff,
    "core-regression-bundle": scenario_core_regression_bundle,
    "supplementary-offer-draft": scenario_supplementary_offer_draft,
    "change-quotation-draft": scenario_change_quotation_draft,
    "supplementary-offer-lifecycle": scenario_supplementary_offer_lifecycle,
    "related-offer-regression-bundle": scenario_related_offer_regression_bundle,
    "work-order-amendment-received": scenario_work_order_amendment_received,
    "commercial-amendment-with-change-quotation": scenario_commercial_amendment_with_change_quotation,
    "work-order-amendment-regression-bundle": scenario_work_order_amendment_regression_bundle,
    "vendor-demo-bundle": scenario_vendor_demo_bundle,
    "uat-pilot-seeded": scenario_uat_pilot_seeded,
    "work-order-contract-period": scenario_work_order_contract_period,
    "work-order-billing-terms-part-4": scenario_work_order_billing_terms_part_4,
    "work-order-resource-requirements": scenario_work_order_resource_requirements,
    "holiday-calendar": scenario_holiday_calendar,
    "equipment-plum-import": scenario_equipment_plum_import,
    "equipment-allocation": scenario_equipment_allocation,
    HIRING_UAT_SCENARIO: scenario_hiring_uat_seeded,
    HIRING_UAT_FLEET_SCENARIO: scenario_hiring_uat_fleet,
}

SCENARIO_DESCRIPTIONS: dict[str, str] = {
    "accepted-offer-no-work-order": "Accepted/awarded offer with no Work Order shell yet.",
    "accepted-offer-with-work-order": "Accepted/awarded offer with the frozen handoff already performed.",
    "rejected-offer": "Submitted offer recorded as REJECTED_LOST via Customer Response.",
    "revision-requested": "Submitted offer with a REVISION_REQUESTED customer response (status stays SUBMITTED).",
    "blocked-handoff": "Submitted (not yet accepted) offer; proves Work Order handoff is genuinely blocked.",
    "core-regression-bundle": (
        "Twelve independent record sets for the Playwright regression suite, including a DRAFT offer "
        "whose Account and offer the upload-rights test attaches files to, a Work Order the "
        "resource-requirement test adds a requirement to, invented machines with a second "
        "invented Plum report for the equipment import test, a Work Order the allocation test "
        "allocates the invented crawler cranes to, a held allocation whose papers run out, for "
        "the certificate reminders' test, a year of PBL's holiday calendar far ahead with a "
        "Work Order over it, for the holiday calendar's test, a DRAFT offer the stale-save test "
        "edits in two tabs, and a submitted offer the submitted-offer test finds locked."
    ),
    "supplementary-offer-draft": "Accepted Base Offer plus one DRAFT Supplementary Offer, no copied data.",
    "change-quotation-draft": "Accepted Base Offer with a Work Order plus one DRAFT Change Quotation linked to it.",
    "supplementary-offer-lifecycle": "Accepted Base Offer plus a Supplementary Offer taken to ACCEPTED independently.",
    "related-offer-regression-bundle": "Independent record sets for the Slice 6O.1 Playwright regression suite.",
    "work-order-amendment-received": "Accepted Base Offer + Work Order plus one ADMINISTRATIVE amendment in RECEIVED.",
    "commercial-amendment-with-change-quotation": (
        "Accepted Base Offer + Work Order + accepted Change Quotation + a COMMERCIAL amendment taken to VALIDATED."
    ),
    "work-order-amendment-regression-bundle": "Independent record sets for the Slice 6O.2 Playwright regression suite.",
    "vendor-demo-bundle": (
        "Slice 6P vendor-demo scenario pack covering Lead-to-Work Order-Amendment tracks A-F, each "
        "with an interactive record and, where a live mutation is involved, a paired fallback record."
    ),
    "uat-pilot-seeded": (
        "UAT pilot practice data: ten synthetic customers with full PAN/GSTIN/address identity and "
        "real BOQ line shapes, spread across every Commercial Offer lifecycle stage, including "
        "approved and draft quotations, a superseded version, an unpriced line and logged "
        "interactions. Synthetic by decision - see docs/uat/."
    ),
    "work-order-contract-period": (
        "Work Order with three lines for the Slice 7D Part 3 and Part 5 screen checks: line 1 has two "
        "billing-terms periods - two shifts each at its own rate, then three at one rate from 1 July 2027 - "
        "with one operator and one helper whose food, accommodation and travel are answered; line 2 has "
        "terms on a different basis, line 3 has none, and the contract dates are left for the tester."
    ),
    "work-order-billing-terms-part-4": (
        "Work Order with three lines for the Slice 7D Part 4 screen check: contract 1 October 2026 to "
        "30 September 2027; line 1 has terms with extra kilometres and crew not answered, line 2 has "
        "them answered in full, line 3 has none; the holiday list is left for the tester to answer."
    ),
    "work-order-resource-requirements": (
        "Work Order with three lines for the WRR-001 screen check: contract 1 October 2026 to 30 September "
        "2027; a crane line with a site, crew terms and an urgent crawler-crane requirement; a manlift line "
        "with no site and an articulating-boom requirement; a forklift line left for the tester."
    ),
    "holiday-calendar": (
        "HOL-1 screen check: a Work Order with a contract from 1 December 2026 to 30 November 2027 - line 1's site in "
        "Gujarat and line 2's in Maharashtra, both by the day with an overtime rate; line 3 with no site, by the hour - "
        "its holidays unanswered, and no holiday calendar started: the tester sets up 2027."
    ),
    "equipment-plum-import": (
        "ERT-1 screen check: three invented models (an all-terrain crane, its carrier, a scissor manlift), "
        "an invented Plum report already confirmed (two mapped machines and one whose name is not mapped), "
        "and a second invented report in the manifest for the tester to upload: a crane carrier to map "
        "and pair, a new manlift whose capacity reads '230 KG <token>'."
    ),
    "equipment-allocation": (
        "8A core screen check: the equipment-plum-import records, with four invented 250 t crawler cranes (two "
        "that can be allocated, one with a warning, one that cannot) and kit held for their model, and a Work "
        "Order whose line's site is in Maharashtra with a requirement for two crawler cranes of at least 200 t "
        "from five days ahead, for the tester to allocate, replace, free and list kit. ELG-2 adds two invented 80 t "
        "crawlers - one whose papers run out in 20, 10 and 5 days with a load test run out, one held on a Work Order "
        "in Gujarat from 12 days ahead whose insurance runs out before the job and whose sling's examination runs out "
        "during it - for the certificate reminders' screen check."
    ),
    HIRING_UAT_SCENARIO: (
        "The Hiring user test's practice data (TE-7), on the Hiring test site's own database: four customers through "
        "accepted offers to Work Orders with sites in Gujarat, Maharashtra and at central-government sites, billing "
        "terms on four bases, a contract with an extension and holidays, resource requirements, an invented fleet from "
        "an invented Plum report whose papers show each eligibility rule, allocations held, replaced and freed with "
        "kit on trips, and reminders of every kind at every stage. Fixed invented machine numbers; seeds once, on a "
        "database with no machine."
    ),
    HIRING_UAT_FLEET_SCENARIO: (
        "The Hiring test site's pre-load for the user-test restart (9 October 2026): the invented fleet of "
        f"{HIRING_UAT_SCENARIO} - the same machines, papers and kit - and PBL's holiday calendar for this year and the "
        "next, marked complete. No customer, offer, Work Order, requirement or allocation: the testers enter those. "
        "Seeds once, on a database with no machine and neither calendar year started."
    ),
}


def _urls_for_records(records: dict[str, Any]) -> dict[str, str]:
    urls: dict[str, str] = {}
    for key, record in records.items():
        lead = record.get("lead")
        if lead:
            urls[f"{key}.lead"] = _lead_url(lead["public_id"])
        account = record.get("account")
        if account:
            urls[f"{key}.account"] = _account_url(account["public_id"])
        opportunity = record.get("opportunity")
        if opportunity:
            urls[f"{key}.opportunity"] = _opportunity_url(opportunity["public_id"])
        offer = record.get("commercial_offer")
        if offer:
            urls[f"{key}.commercial_offer"] = _offer_url(offer["public_id"])
        for index, work_order in enumerate(record.get("work_orders", []) or []):
            suffix = "" if index == 0 else f"_{index + 1}"
            urls[f"{key}.work_order{suffix}"] = _work_order_url(work_order["public_id"])
        for index, related_offer in enumerate(record.get("related_offers", []) or []):
            suffix = "" if index == 0 else f"_{index + 1}"
            urls[f"{key}.related_offer{suffix}"] = _offer_url(related_offer["public_id"])
        work_orders = record.get("work_orders") or []
        if work_orders:
            for index, amendment in enumerate(record.get("amendments", []) or []):
                suffix = "" if index == 0 else f"_{index + 1}"
                urls[f"{key}.amendment{suffix}"] = _amendment_url(work_orders[0]["public_id"], amendment["public_id"])
    return urls


def run_scenario(scenario_name: str) -> dict[str, Any]:
    if scenario_name not in SCENARIOS:
        raise ValueError(f"Unknown scenario {scenario_name!r}. Known scenarios: {sorted(SCENARIOS)}")

    # Checked before any record set is written, so a refusal leaves nothing behind (ERT1-R4-001) - before the actor
    # too, whom resolve_actor may create (TE-8 round 1).
    if scenario_name in SCENARIOS_CONFIRMING_EQUIPMENT_REPORTS:
        require_no_equipment_fleet()
    if scenario_name == HIRING_UAT_FLEET_SCENARIO:
        require_fleet_calendar_years_free()

    run_id = new_run_id()
    with SessionLocal() as db:
        actor = resolve_actor(db)

    records = SCENARIOS[scenario_name](run_id, actor)

    manifest = Manifest(
        manifest_version=1,
        run_id=run_id,
        scenario=scenario_name,
        created_at=utc_now_iso(),
        actor=actor,
        records=records,
        urls=_urls_for_records(records),
    )
    return manifest.to_dict()
