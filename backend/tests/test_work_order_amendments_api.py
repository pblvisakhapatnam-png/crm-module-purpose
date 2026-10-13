"""Slice 6O.2 - Work Order Amendment intake foundation tests.

These tests reuse the existing helper functions from test_commercial_offers_api.py
(auth_headers, client, cleanup_test_records, cleanup_test_work_orders,
create_account_linked_test_opportunity, create_test_commercial_offer,
create_test_offer_line, create_test_work_order, mark_test_commercial_offer_submitted,
record_test_customer_response) rather than duplicating that setup logic, following the
same pattern test_commercial_offer_related_offers_api.py established for Slice 6O.1.

A Work Order Amendment is an intake/review record only. It must never be applied to
the Work Order or its lines; that is verified explicitly in several tests below.
"""

from uuid import uuid4

from sqlalchemy import text

from app.core.database import SessionLocal

from tests.test_commercial_offer_related_offers_api import _null_related_work_order_links
from tests.test_commercial_offers_api import (
    auth_headers,
    client,
    cleanup_test_records,
    cleanup_test_work_orders,
    create_account_linked_test_opportunity,
    create_test_commercial_offer,
    create_test_work_order,
    mark_test_commercial_offer_submitted,
    record_test_customer_response,
)


def _cleanup_amendments(work_order_public_ids: list[str]) -> None:
    if not work_order_public_ids:
        return
    with SessionLocal() as db:
        for public_id in work_order_public_ids:
            db.execute(
                text(
                    """
                    DELETE FROM crm_work_order_amendment_line wal
                    USING crm_work_order_amendment wa, crm_work_order wo
                    WHERE wa.id = wal.amendment_id
                      AND wo.id = wa.work_order_id
                      AND wo.work_order_public_id = :public_id
                    """
                ),
                {"public_id": public_id},
            )
            db.execute(
                text(
                    """
                    DELETE FROM crm_work_order_amendment wa
                    USING crm_work_order wo
                    WHERE wo.id = wa.work_order_id
                      AND wo.work_order_public_id = :public_id
                    """
                ),
                {"public_id": public_id},
            )
        db.commit()


def _build_accepted_work_order_chain() -> dict[str, object]:
    """Account -> Opportunity -> accepted Base Offer (with one line) -> Work Order shell."""
    linked = create_account_linked_test_opportunity()
    opportunity_public_id = str(linked["opportunity"]["public_id"])
    base_offer = create_test_commercial_offer(opportunity_public_id)
    base_offer_public_id = str(base_offer["public_id"])
    mark_test_commercial_offer_submitted(base_offer_public_id)
    record_test_customer_response(base_offer_public_id, "ACCEPTED_AWARDED", received_at="2026-07-13T10:00:00Z")
    work_order = create_test_work_order(base_offer_public_id)
    return {
        "lead": linked["lead"],
        "account": linked["account"],
        "opportunity": linked["opportunity"],
        "base_offer_public_id": base_offer_public_id,
        "work_order": work_order,
    }


def _create_related_offer(
    base_offer_public_id: str,
    *,
    offer_purpose: str,
    work_order_public_id: str | None = None,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "offer_purpose": offer_purpose,
        "customer_request_summary": f"Customer requested a {offer_purpose.lower()} change.",
    }
    if work_order_public_id:
        payload["related_work_order_public_id"] = work_order_public_id
    response = client.post(
        f"/api/commercial-offers/{base_offer_public_id}/related-offers",
        headers=auth_headers("sales1"),
        json=payload,
    )
    assert response.status_code == 201
    return response.json()["commercial_offer"]


def _accept_related_offer(offer_public_id: str) -> dict[str, object]:
    mark_test_commercial_offer_submitted(offer_public_id)
    result = record_test_customer_response(offer_public_id, "ACCEPTED_AWARDED", received_at="2026-07-13T11:00:00Z")
    return result["commercial_offer"]


def _get_work_order_line_public_id(work_order_public_id: str) -> str:
    response = client.get(f"/api/work-orders/{work_order_public_id}/lines", headers=auth_headers("sales1"))
    assert response.status_code == 200
    lines = response.json()
    assert len(lines) >= 1
    return lines[0]["public_id"]


def _work_order_line_snapshot(work_order_public_id: str) -> list[dict[str, object]]:
    response = client.get(f"/api/work-orders/{work_order_public_id}/lines", headers=auth_headers("readonly1"))
    assert response.status_code == 200
    return response.json()


def _teardown(
    *,
    work_order_public_ids: list[str],
    offer_public_ids: list[str],
    opportunity_public_ids: list[str],
    account_public_ids: list[str],
    lead_public_ids: list[str],
) -> None:
    _cleanup_amendments(work_order_public_ids)
    _null_related_work_order_links(offer_public_ids)
    cleanup_test_work_orders(work_order_public_ids)
    cleanup_test_records(
        opportunity_public_ids=opportunity_public_ids,
        offer_public_ids=offer_public_ids,
        account_public_ids=account_public_ids,
        lead_public_ids=lead_public_ids,
    )


# --- Creation and compatibility -----------------------------------------------------------


def test_administrative_amendment_created_as_received_and_leaves_work_order_unchanged() -> None:
    work_order_public_ids: list[str] = []
    offer_public_ids: list[str] = []
    opportunity_public_ids: list[str] = []
    account_public_ids: list[str] = []
    lead_public_ids: list[str] = []
    try:
        chain = _build_accepted_work_order_chain()
        opportunity_public_ids.append(str(chain["opportunity"]["public_id"]))
        account_public_ids.append(str(chain["account"]["public_id"]))
        lead_public_ids.append(str(chain["lead"]["public_id"]))
        offer_public_ids.append(chain["base_offer_public_id"])
        work_order_public_id = str(chain["work_order"]["public_id"])
        work_order_public_ids.append(work_order_public_id)

        before_lines = _work_order_line_snapshot(work_order_public_id)
        before_wo = client.get(f"/api/work-orders/{work_order_public_id}", headers=auth_headers("sales1")).json()

        response = client.post(
            f"/api/work-orders/{work_order_public_id}/amendments",
            headers=auth_headers("sales1"),
            json={
                "amendment_type_code": "ADMINISTRATIVE",
                "received_date": "2026-07-13",
                "amendment_reason": "Customer requested a mobilisation date change.",
                "administrative_change_summary": "Mobilisation date moved to next week.",
                "customer_amendment_reference": f"CUST-AMD-{uuid4()}",
            },
        )
        assert response.status_code == 201
        body = response.json()
        amendment = body["amendment"]
        assert amendment["amendment_type_code"] == "ADMINISTRATIVE"
        assert amendment["amendment_status_code"] == "RECEIVED"
        assert amendment["amendment_sequence_no"] == 1
        assert amendment["work_order_public_id"] == work_order_public_id
        assert body["event"]["event_name"] == "WorkOrderAmendmentRecorded"

        with SessionLocal() as db:
            event_count = db.execute(
                text(
                    "SELECT COUNT(*) FROM business_event WHERE record_type = 'work_order' AND record_public_id = "
                    ":work_order_public_id AND event_name = 'WorkOrderAmendmentRecorded'"
                ),
                {"work_order_public_id": work_order_public_id},
            ).scalar_one()
        assert int(event_count) == 1

        after_wo = client.get(f"/api/work-orders/{work_order_public_id}", headers=auth_headers("sales1")).json()
        after_lines = _work_order_line_snapshot(work_order_public_id)
        assert after_wo == before_wo
        assert after_lines == before_lines

        list_response = client.get(f"/api/work-orders/{work_order_public_id}", headers=auth_headers("sales1"))
        assert list_response.status_code == 200
        lines_response = client.get(f"/api/work-orders/{work_order_public_id}/lines", headers=auth_headers("sales1"))
        assert lines_response.status_code == 200
    finally:
        _teardown(
            work_order_public_ids=work_order_public_ids,
            offer_public_ids=offer_public_ids,
            opportunity_public_ids=opportunity_public_ids,
            account_public_ids=account_public_ids,
            lead_public_ids=lead_public_ids,
        )


def test_commercial_amendment_requires_commercial_change_summary() -> None:
    work_order_public_ids: list[str] = []
    offer_public_ids: list[str] = []
    opportunity_public_ids: list[str] = []
    account_public_ids: list[str] = []
    lead_public_ids: list[str] = []
    try:
        chain = _build_accepted_work_order_chain()
        opportunity_public_ids.append(str(chain["opportunity"]["public_id"]))
        account_public_ids.append(str(chain["account"]["public_id"]))
        lead_public_ids.append(str(chain["lead"]["public_id"]))
        offer_public_ids.append(chain["base_offer_public_id"])
        work_order_public_id = str(chain["work_order"]["public_id"])
        work_order_public_ids.append(work_order_public_id)

        missing_summary_response = client.post(
            f"/api/work-orders/{work_order_public_id}/amendments",
            headers=auth_headers("sales1"),
            json={
                "amendment_type_code": "COMMERCIAL",
                "received_date": "2026-07-13",
                "amendment_reason": "Customer requested additional scope.",
            },
        )
        assert missing_summary_response.status_code == 422
        assert "Commercial change summary" in missing_summary_response.json()["detail"]

        with SessionLocal() as db:
            count = db.execute(
                text("SELECT COUNT(*) FROM crm_work_order_amendment wa INNER JOIN crm_work_order wo ON wo.id = wa.work_order_id WHERE wo.work_order_public_id = :public_id"),
                {"public_id": work_order_public_id},
            ).scalar_one()
        assert int(count) == 0

        response = client.post(
            f"/api/work-orders/{work_order_public_id}/amendments",
            headers=auth_headers("sales1"),
            json={
                "amendment_type_code": "COMMERCIAL",
                "received_date": "2026-07-13",
                "amendment_reason": "Customer requested additional scope.",
                "commercial_change_summary": "One additional crane requested.",
            },
        )
        assert response.status_code == 201
        assert response.json()["amendment"]["amendment_type_code"] == "COMMERCIAL"
    finally:
        _teardown(
            work_order_public_ids=work_order_public_ids,
            offer_public_ids=offer_public_ids,
            opportunity_public_ids=opportunity_public_ids,
            account_public_ids=account_public_ids,
            lead_public_ids=lead_public_ids,
        )


def test_mixed_amendment_creation_and_sequence_increments_per_work_order() -> None:
    work_order_public_ids: list[str] = []
    offer_public_ids: list[str] = []
    opportunity_public_ids: list[str] = []
    account_public_ids: list[str] = []
    lead_public_ids: list[str] = []
    try:
        chain = _build_accepted_work_order_chain()
        opportunity_public_ids.append(str(chain["opportunity"]["public_id"]))
        account_public_ids.append(str(chain["account"]["public_id"]))
        lead_public_ids.append(str(chain["lead"]["public_id"]))
        offer_public_ids.append(chain["base_offer_public_id"])
        work_order_public_id = str(chain["work_order"]["public_id"])
        work_order_public_ids.append(work_order_public_id)

        first = client.post(
            f"/api/work-orders/{work_order_public_id}/amendments",
            headers=auth_headers("sales1"),
            json={
                "amendment_type_code": "MIXED",
                "received_date": "2026-07-13",
                "amendment_reason": "Customer requested a scope and price change together.",
                "commercial_change_summary": "Add one line and revise price.",
                "administrative_change_summary": "Also update the site contact.",
            },
        )
        assert first.status_code == 201
        assert first.json()["amendment"]["amendment_type_code"] == "MIXED"
        assert first.json()["amendment"]["amendment_sequence_no"] == 1

        second = client.post(
            f"/api/work-orders/{work_order_public_id}/amendments",
            headers=auth_headers("sales1"),
            json={
                "amendment_type_code": "ADMINISTRATIVE",
                "received_date": "2026-07-14",
                "amendment_reason": "Second, unrelated administrative change.",
            },
        )
        assert second.status_code == 201
        assert second.json()["amendment"]["amendment_sequence_no"] == 2
    finally:
        _teardown(
            work_order_public_ids=work_order_public_ids,
            offer_public_ids=offer_public_ids,
            opportunity_public_ids=opportunity_public_ids,
            account_public_ids=account_public_ids,
            lead_public_ids=lead_public_ids,
        )


def test_duplicate_customer_reference_rejected_same_work_order_but_allowed_on_another() -> None:
    work_order_public_ids: list[str] = []
    offer_public_ids: list[str] = []
    opportunity_public_ids: list[str] = []
    account_public_ids: list[str] = []
    lead_public_ids: list[str] = []
    try:
        chain_one = _build_accepted_work_order_chain()
        chain_two = _build_accepted_work_order_chain()
        for chain in (chain_one, chain_two):
            opportunity_public_ids.append(str(chain["opportunity"]["public_id"]))
            account_public_ids.append(str(chain["account"]["public_id"]))
            lead_public_ids.append(str(chain["lead"]["public_id"]))
            offer_public_ids.append(chain["base_offer_public_id"])
            work_order_public_ids.append(str(chain["work_order"]["public_id"]))

        shared_reference = f"CUST-AMD-SHARED-{uuid4()}"
        work_order_one_public_id = str(chain_one["work_order"]["public_id"])
        work_order_two_public_id = str(chain_two["work_order"]["public_id"])

        first = client.post(
            f"/api/work-orders/{work_order_one_public_id}/amendments",
            headers=auth_headers("sales1"),
            json={
                "amendment_type_code": "ADMINISTRATIVE",
                "received_date": "2026-07-13",
                "amendment_reason": "First reference use.",
                "customer_amendment_reference": shared_reference,
            },
        )
        assert first.status_code == 201

        duplicate = client.post(
            f"/api/work-orders/{work_order_one_public_id}/amendments",
            headers=auth_headers("sales1"),
            json={
                "amendment_type_code": "ADMINISTRATIVE",
                "received_date": "2026-07-13",
                "amendment_reason": "Second attempt with same reference on same Work Order.",
                "customer_amendment_reference": shared_reference,
            },
        )
        assert duplicate.status_code == 422
        assert "already used" in duplicate.json()["detail"]

        other_work_order = client.post(
            f"/api/work-orders/{work_order_two_public_id}/amendments",
            headers=auth_headers("sales1"),
            json={
                "amendment_type_code": "ADMINISTRATIVE",
                "received_date": "2026-07-13",
                "amendment_reason": "Same reference, different Work Order - allowed.",
                "customer_amendment_reference": shared_reference,
            },
        )
        assert other_work_order.status_code == 201
    finally:
        _teardown(
            work_order_public_ids=work_order_public_ids,
            offer_public_ids=offer_public_ids,
            opportunity_public_ids=opportunity_public_ids,
            account_public_ids=account_public_ids,
            lead_public_ids=lead_public_ids,
        )


# --- Related Commercial Offer (commercial basis) linkage ----------------------------------


def test_accepted_change_quotation_and_supplementary_offer_may_be_linked() -> None:
    work_order_public_ids: list[str] = []
    offer_public_ids: list[str] = []
    opportunity_public_ids: list[str] = []
    account_public_ids: list[str] = []
    lead_public_ids: list[str] = []
    try:
        chain = _build_accepted_work_order_chain()
        opportunity_public_ids.append(str(chain["opportunity"]["public_id"]))
        account_public_ids.append(str(chain["account"]["public_id"]))
        lead_public_ids.append(str(chain["lead"]["public_id"]))
        offer_public_ids.append(chain["base_offer_public_id"])
        work_order_public_id = str(chain["work_order"]["public_id"])
        work_order_public_ids.append(work_order_public_id)

        change_quotation = _create_related_offer(
            chain["base_offer_public_id"], offer_purpose="CHANGE_QUOTATION", work_order_public_id=work_order_public_id
        )
        offer_public_ids.insert(0, str(change_quotation["public_id"]))
        _accept_related_offer(change_quotation["public_id"])

        response = client.post(
            f"/api/work-orders/{work_order_public_id}/amendments",
            headers=auth_headers("sales1"),
            json={
                "amendment_type_code": "COMMERCIAL",
                "received_date": "2026-07-13",
                "amendment_reason": "Customer requested a revised price.",
                "commercial_change_summary": "Revised day rate for crane hire.",
                "related_commercial_offer_public_id": change_quotation["public_id"],
            },
        )
        assert response.status_code == 201
        amendment = response.json()["amendment"]
        assert amendment["related_commercial_offer_public_id"] == change_quotation["public_id"]
        assert amendment["related_commercial_offer_purpose"] == "CHANGE_QUOTATION"
        assert amendment["related_commercial_offer_status_code"] == "ACCEPTED"

        supplementary = _create_related_offer(
            chain["base_offer_public_id"], offer_purpose="SUPPLEMENTARY", work_order_public_id=work_order_public_id
        )
        offer_public_ids.insert(0, str(supplementary["public_id"]))
        _accept_related_offer(supplementary["public_id"])

        response_two = client.post(
            f"/api/work-orders/{work_order_public_id}/amendments",
            headers=auth_headers("sales1"),
            json={
                "amendment_type_code": "COMMERCIAL",
                "received_date": "2026-07-13",
                "amendment_reason": "Customer requested one additional crane.",
                "commercial_change_summary": "One additional 80T crane for two weeks.",
                "related_commercial_offer_public_id": supplementary["public_id"],
                "customer_amendment_reference": f"CUST-AMD-{uuid4()}",
            },
        )
        assert response_two.status_code == 201
        assert response_two.json()["amendment"]["related_commercial_offer_purpose"] == "SUPPLEMENTARY"
    finally:
        _teardown(
            work_order_public_ids=work_order_public_ids,
            offer_public_ids=offer_public_ids,
            opportunity_public_ids=opportunity_public_ids,
            account_public_ids=account_public_ids,
            lead_public_ids=lead_public_ids,
        )


def test_draft_related_offer_recorded_as_pending_basis_but_blocks_validation() -> None:
    work_order_public_ids: list[str] = []
    offer_public_ids: list[str] = []
    opportunity_public_ids: list[str] = []
    account_public_ids: list[str] = []
    lead_public_ids: list[str] = []
    try:
        chain = _build_accepted_work_order_chain()
        opportunity_public_ids.append(str(chain["opportunity"]["public_id"]))
        account_public_ids.append(str(chain["account"]["public_id"]))
        lead_public_ids.append(str(chain["lead"]["public_id"]))
        offer_public_ids.append(chain["base_offer_public_id"])
        work_order_public_id = str(chain["work_order"]["public_id"])
        work_order_public_ids.append(work_order_public_id)

        change_quotation = _create_related_offer(
            chain["base_offer_public_id"], offer_purpose="CHANGE_QUOTATION", work_order_public_id=work_order_public_id
        )
        offer_public_ids.insert(0, str(change_quotation["public_id"]))
        assert change_quotation["offer_status_code"] == "DRAFT"

        create_response = client.post(
            f"/api/work-orders/{work_order_public_id}/amendments",
            headers=auth_headers("sales1"),
            json={
                "amendment_type_code": "COMMERCIAL",
                "received_date": "2026-07-13",
                "amendment_reason": "Customer requested a revised price; basis not yet accepted.",
                "commercial_change_summary": "Revised day rate pending Change Quotation acceptance.",
                "related_commercial_offer_public_id": change_quotation["public_id"],
            },
        )
        assert create_response.status_code == 201
        amendment_public_id = create_response.json()["amendment"]["public_id"]

        readiness = client.get(
            f"/api/work-orders/{work_order_public_id}/amendments/{amendment_public_id}/readiness",
            headers=auth_headers("sales1"),
        ).json()
        assert readiness["related_offer_linked"] is True
        assert readiness["related_offer_accepted"] is False

        under_review = client.post(
            f"/api/work-orders/{work_order_public_id}/amendments/{amendment_public_id}/decision",
            headers=auth_headers("sales1"),
            json={"target_status_code": "UNDER_REVIEW"},
        )
        assert under_review.status_code == 200

        blocked_validate = client.post(
            f"/api/work-orders/{work_order_public_id}/amendments/{amendment_public_id}/decision",
            headers=auth_headers("sales1"),
            json={"target_status_code": "VALIDATED"},
        )
        assert blocked_validate.status_code == 422
        assert "Accepted" in blocked_validate.json()["detail"]
    finally:
        _teardown(
            work_order_public_ids=work_order_public_ids,
            offer_public_ids=offer_public_ids,
            opportunity_public_ids=opportunity_public_ids,
            account_public_ids=account_public_ids,
            lead_public_ids=lead_public_ids,
        )


def test_related_offer_lineage_and_purpose_rejections() -> None:
    work_order_public_ids: list[str] = []
    offer_public_ids: list[str] = []
    opportunity_public_ids: list[str] = []
    account_public_ids: list[str] = []
    lead_public_ids: list[str] = []
    try:
        chain_one = _build_accepted_work_order_chain()
        chain_two = _build_accepted_work_order_chain()
        for chain in (chain_one, chain_two):
            opportunity_public_ids.append(str(chain["opportunity"]["public_id"]))
            account_public_ids.append(str(chain["account"]["public_id"]))
            lead_public_ids.append(str(chain["lead"]["public_id"]))
            offer_public_ids.append(chain["base_offer_public_id"])
            work_order_public_ids.append(str(chain["work_order"]["public_id"]))

        work_order_one_public_id = str(chain_one["work_order"]["public_id"])
        work_order_two_public_id = str(chain_two["work_order"]["public_id"])

        # Base Offer cannot be used as the commercial basis.
        base_offer_response = client.post(
            f"/api/work-orders/{work_order_one_public_id}/amendments",
            headers=auth_headers("sales1"),
            json={
                "amendment_type_code": "COMMERCIAL",
                "received_date": "2026-07-13",
                "amendment_reason": "Attempt to cite the Base Offer as commercial basis.",
                "commercial_change_summary": "Should be rejected.",
                "related_commercial_offer_public_id": chain_one["base_offer_public_id"],
            },
        )
        assert base_offer_response.status_code == 422
        assert "Base Offer" in base_offer_response.json()["detail"]

        # A related offer linked to a different Work Order (or not linked to any Work
        # Order) cannot be used as chain_one's amendment's commercial basis.
        unrelated_supplementary = _create_related_offer(chain_two["base_offer_public_id"], offer_purpose="SUPPLEMENTARY")
        offer_public_ids.insert(0, str(unrelated_supplementary["public_id"]))
        _accept_related_offer(unrelated_supplementary["public_id"])

        cross_wo_response = client.post(
            f"/api/work-orders/{work_order_one_public_id}/amendments",
            headers=auth_headers("sales1"),
            json={
                "amendment_type_code": "COMMERCIAL",
                "received_date": "2026-07-13",
                "amendment_reason": "Attempt to cite an offer not linked to this Work Order.",
                "commercial_change_summary": "Should be rejected.",
                "related_commercial_offer_public_id": unrelated_supplementary["public_id"],
            },
        )
        assert cross_wo_response.status_code == 422
        assert "not linked to this Work Order" in cross_wo_response.json()["detail"]

        change_quotation_for_two = _create_related_offer(
            chain_two["base_offer_public_id"],
            offer_purpose="CHANGE_QUOTATION",
            work_order_public_id=work_order_two_public_id,
        )
        offer_public_ids.insert(0, str(change_quotation_for_two["public_id"]))
        _accept_related_offer(change_quotation_for_two["public_id"])

        wrong_wo_response = client.post(
            f"/api/work-orders/{work_order_one_public_id}/amendments",
            headers=auth_headers("sales1"),
            json={
                "amendment_type_code": "COMMERCIAL",
                "received_date": "2026-07-13",
                "amendment_reason": "Attempt to cite chain_two's own Change Quotation for chain_one's Work Order.",
                "commercial_change_summary": "Should be rejected.",
                "related_commercial_offer_public_id": change_quotation_for_two["public_id"],
            },
        )
        assert wrong_wo_response.status_code == 422
        assert "not linked to this Work Order" in wrong_wo_response.json()["detail"]
    finally:
        _teardown(
            work_order_public_ids=work_order_public_ids,
            offer_public_ids=offer_public_ids,
            opportunity_public_ids=opportunity_public_ids,
            account_public_ids=account_public_ids,
            lead_public_ids=lead_public_ids,
        )


# --- Amendment lines ------------------------------------------------------------------------


def test_add_line_succeeds_without_source_and_requires_description() -> None:
    work_order_public_ids: list[str] = []
    offer_public_ids: list[str] = []
    opportunity_public_ids: list[str] = []
    account_public_ids: list[str] = []
    lead_public_ids: list[str] = []
    try:
        chain = _build_accepted_work_order_chain()
        opportunity_public_ids.append(str(chain["opportunity"]["public_id"]))
        account_public_ids.append(str(chain["account"]["public_id"]))
        lead_public_ids.append(str(chain["lead"]["public_id"]))
        offer_public_ids.append(chain["base_offer_public_id"])
        work_order_public_id = str(chain["work_order"]["public_id"])
        work_order_public_ids.append(work_order_public_id)

        amendment = client.post(
            f"/api/work-orders/{work_order_public_id}/amendments",
            headers=auth_headers("sales1"),
            json={
                "amendment_type_code": "COMMERCIAL",
                "received_date": "2026-07-13",
                "amendment_reason": "Customer requested one additional crane.",
                "commercial_change_summary": "Add one additional crane line.",
            },
        ).json()["amendment"]
        amendment_public_id = amendment["public_id"]

        missing_description = client.post(
            f"/api/work-orders/{work_order_public_id}/amendments/{amendment_public_id}/lines",
            headers=auth_headers("sales1"),
            json={"action_code": "ADD_LINE"},
        )
        assert missing_description.status_code == 422

        response = client.post(
            f"/api/work-orders/{work_order_public_id}/amendments/{amendment_public_id}/lines",
            headers=auth_headers("sales1"),
            json={
                "action_code": "ADD_LINE",
                "proposed_scope_description": "Provide one additional 80T crane with operator.",
                "proposed_quantity": "5.00",
                "proposed_uom": "day",
                "proposed_rate_amount": "25000.00",
            },
        )
        assert response.status_code == 201
        line = response.json()["amendment_line"]
        assert line["action_code"] == "ADD_LINE"
        assert line["source_work_order_line_public_id"] is None
        assert line["proposed_amount"] == "125000.00"
        assert response.json()["event"]["event_name"] == "WorkOrderAmendmentLineAdded"
    finally:
        _teardown(
            work_order_public_ids=work_order_public_ids,
            offer_public_ids=offer_public_ids,
            opportunity_public_ids=opportunity_public_ids,
            account_public_ids=account_public_ids,
            lead_public_ids=lead_public_ids,
        )


def test_change_line_and_cancel_line_require_source_line_from_same_work_order() -> None:
    work_order_public_ids: list[str] = []
    offer_public_ids: list[str] = []
    opportunity_public_ids: list[str] = []
    account_public_ids: list[str] = []
    lead_public_ids: list[str] = []
    try:
        chain_one = _build_accepted_work_order_chain()
        chain_two = _build_accepted_work_order_chain()
        for chain in (chain_one, chain_two):
            opportunity_public_ids.append(str(chain["opportunity"]["public_id"]))
            account_public_ids.append(str(chain["account"]["public_id"]))
            lead_public_ids.append(str(chain["lead"]["public_id"]))
            offer_public_ids.append(chain["base_offer_public_id"])
            work_order_public_ids.append(str(chain["work_order"]["public_id"]))

        work_order_one_public_id = str(chain_one["work_order"]["public_id"])
        work_order_two_public_id = str(chain_two["work_order"]["public_id"])
        own_line_public_id = _get_work_order_line_public_id(work_order_one_public_id)
        other_work_order_line_public_id = _get_work_order_line_public_id(work_order_two_public_id)

        amendment = client.post(
            f"/api/work-orders/{work_order_one_public_id}/amendments",
            headers=auth_headers("sales1"),
            json={
                "amendment_type_code": "COMMERCIAL",
                "received_date": "2026-07-13",
                "amendment_reason": "Customer requested a rate change on the existing line.",
                "commercial_change_summary": "Revise rate on existing line.",
            },
        ).json()["amendment"]
        amendment_public_id = amendment["public_id"]

        missing_source = client.post(
            f"/api/work-orders/{work_order_one_public_id}/amendments/{amendment_public_id}/lines",
            headers=auth_headers("sales1"),
            json={"action_code": "CHANGE_LINE", "change_summary": "Missing source line."},
        )
        assert missing_source.status_code == 422
        assert "requires a source Work Order line" in missing_source.json()["detail"]

        wrong_work_order_source = client.post(
            f"/api/work-orders/{work_order_one_public_id}/amendments/{amendment_public_id}/lines",
            headers=auth_headers("sales1"),
            json={
                "action_code": "CHANGE_LINE",
                "source_work_order_line_public_id": other_work_order_line_public_id,
                "change_summary": "Source line belongs to a different Work Order.",
            },
        )
        assert wrong_work_order_source.status_code == 422
        assert "not found" in wrong_work_order_source.json()["detail"]

        change_line = client.post(
            f"/api/work-orders/{work_order_one_public_id}/amendments/{amendment_public_id}/lines",
            headers=auth_headers("sales1"),
            json={
                "action_code": "CHANGE_LINE",
                "source_work_order_line_public_id": own_line_public_id,
                "change_summary": "Revise the day rate for this line.",
                "proposed_rate_amount": "27500.00",
            },
        )
        assert change_line.status_code == 201
        change_body = change_line.json()["amendment_line"]
        assert change_body["source_work_order_line_public_id"] == own_line_public_id
        assert change_body["original_scope_description"] is not None
        assert change_body["original_quantity"] is not None

        cancel_line = client.post(
            f"/api/work-orders/{work_order_two_public_id}/amendments",
            headers=auth_headers("sales1"),
            json={
                "amendment_type_code": "COMMERCIAL",
                "received_date": "2026-07-13",
                "amendment_reason": "Customer requested cancellation of the existing line.",
                "commercial_change_summary": "Cancel existing line entirely.",
            },
        ).json()["amendment"]
        cancel_amendment_public_id = cancel_line["public_id"]
        cancel_response = client.post(
            f"/api/work-orders/{work_order_two_public_id}/amendments/{cancel_amendment_public_id}/lines",
            headers=auth_headers("sales1"),
            json={
                "action_code": "CANCEL_LINE",
                "source_work_order_line_public_id": other_work_order_line_public_id,
                "change_summary": "Customer no longer requires this line.",
            },
        )
        assert cancel_response.status_code == 201
        assert cancel_response.json()["amendment_line"]["action_code"] == "CANCEL_LINE"
    finally:
        _teardown(
            work_order_public_ids=work_order_public_ids,
            offer_public_ids=offer_public_ids,
            opportunity_public_ids=opportunity_public_ids,
            account_public_ids=account_public_ids,
            lead_public_ids=lead_public_ids,
        )


def test_amendment_line_snapshot_preserved_and_work_order_line_unchanged() -> None:
    work_order_public_ids: list[str] = []
    offer_public_ids: list[str] = []
    opportunity_public_ids: list[str] = []
    account_public_ids: list[str] = []
    lead_public_ids: list[str] = []
    try:
        chain = _build_accepted_work_order_chain()
        opportunity_public_ids.append(str(chain["opportunity"]["public_id"]))
        account_public_ids.append(str(chain["account"]["public_id"]))
        lead_public_ids.append(str(chain["lead"]["public_id"]))
        offer_public_ids.append(chain["base_offer_public_id"])
        work_order_public_id = str(chain["work_order"]["public_id"])
        work_order_public_ids.append(work_order_public_id)

        before_lines = _work_order_line_snapshot(work_order_public_id)
        source_line_public_id = before_lines[0]["public_id"]

        amendment = client.post(
            f"/api/work-orders/{work_order_public_id}/amendments",
            headers=auth_headers("sales1"),
            json={
                "amendment_type_code": "COMMERCIAL",
                "received_date": "2026-07-13",
                "amendment_reason": "Customer requested a quantity change.",
                "commercial_change_summary": "Increase quantity on existing line.",
            },
        ).json()["amendment"]
        amendment_public_id = amendment["public_id"]

        line_response = client.post(
            f"/api/work-orders/{work_order_public_id}/amendments/{amendment_public_id}/lines",
            headers=auth_headers("sales1"),
            json={
                "action_code": "CHANGE_LINE",
                "source_work_order_line_public_id": source_line_public_id,
                "change_summary": "Increase quantity from source snapshot.",
                "proposed_quantity": "20.00",
            },
        )
        assert line_response.status_code == 201
        snapshot = line_response.json()["amendment_line"]
        assert snapshot["original_scope_description"] == before_lines[0]["scope_description"]
        assert snapshot["original_quantity"] == before_lines[0]["quantity"]
        assert snapshot["original_uom"] == before_lines[0]["uom"]
        assert snapshot["original_source_offer_line_public_id"] == before_lines[0]["source_offer_line_public_id"]

        after_lines = _work_order_line_snapshot(work_order_public_id)
        assert after_lines == before_lines
    finally:
        _teardown(
            work_order_public_ids=work_order_public_ids,
            offer_public_ids=offer_public_ids,
            opportunity_public_ids=opportunity_public_ids,
            account_public_ids=account_public_ids,
            lead_public_ids=lead_public_ids,
        )


def test_amendment_lines_blocked_after_terminal_status() -> None:
    work_order_public_ids: list[str] = []
    offer_public_ids: list[str] = []
    opportunity_public_ids: list[str] = []
    account_public_ids: list[str] = []
    lead_public_ids: list[str] = []
    try:
        chain = _build_accepted_work_order_chain()
        opportunity_public_ids.append(str(chain["opportunity"]["public_id"]))
        account_public_ids.append(str(chain["account"]["public_id"]))
        lead_public_ids.append(str(chain["lead"]["public_id"]))
        offer_public_ids.append(chain["base_offer_public_id"])
        work_order_public_id = str(chain["work_order"]["public_id"])
        work_order_public_ids.append(work_order_public_id)

        amendment = client.post(
            f"/api/work-orders/{work_order_public_id}/amendments",
            headers=auth_headers("sales1"),
            json={
                "amendment_type_code": "ADMINISTRATIVE",
                "received_date": "2026-07-13",
                "amendment_reason": "Administrative note to be rejected.",
            },
        ).json()["amendment"]
        amendment_public_id = amendment["public_id"]

        rejected = client.post(
            f"/api/work-orders/{work_order_public_id}/amendments/{amendment_public_id}/decision",
            headers=auth_headers("sales1"),
            json={"target_status_code": "REJECTED", "reason": "Customer withdrew the request."},
        )
        assert rejected.status_code == 200
        assert rejected.json()["amendment"]["amendment_status_code"] == "REJECTED"

        blocked_line = client.post(
            f"/api/work-orders/{work_order_public_id}/amendments/{amendment_public_id}/lines",
            headers=auth_headers("sales1"),
            json={"action_code": "ADD_LINE", "proposed_scope_description": "Should be blocked."},
        )
        assert blocked_line.status_code == 422
    finally:
        _teardown(
            work_order_public_ids=work_order_public_ids,
            offer_public_ids=offer_public_ids,
            opportunity_public_ids=opportunity_public_ids,
            account_public_ids=account_public_ids,
            lead_public_ids=lead_public_ids,
        )


# --- Lifecycle and validation ---------------------------------------------------------------


def test_administrative_amendment_full_lifecycle_to_validated() -> None:
    work_order_public_ids: list[str] = []
    offer_public_ids: list[str] = []
    opportunity_public_ids: list[str] = []
    account_public_ids: list[str] = []
    lead_public_ids: list[str] = []
    try:
        chain = _build_accepted_work_order_chain()
        opportunity_public_ids.append(str(chain["opportunity"]["public_id"]))
        account_public_ids.append(str(chain["account"]["public_id"]))
        lead_public_ids.append(str(chain["lead"]["public_id"]))
        offer_public_ids.append(chain["base_offer_public_id"])
        work_order_public_id = str(chain["work_order"]["public_id"])
        work_order_public_ids.append(work_order_public_id)

        amendment = client.post(
            f"/api/work-orders/{work_order_public_id}/amendments",
            headers=auth_headers("sales1"),
            json={
                "amendment_type_code": "ADMINISTRATIVE",
                "received_date": "2026-07-13",
                "amendment_reason": "Customer contact update.",
            },
        ).json()["amendment"]
        amendment_public_id = amendment["public_id"]

        readiness_received = client.get(
            f"/api/work-orders/{work_order_public_id}/amendments/{amendment_public_id}/readiness",
            headers=auth_headers("sales1"),
        ).json()
        assert readiness_received["can_move_to_under_review"] is True
        assert readiness_received["can_move_to_validated"] is False
        assert readiness_received["applied_to_work_order"] is False

        under_review = client.post(
            f"/api/work-orders/{work_order_public_id}/amendments/{amendment_public_id}/decision",
            headers=auth_headers("sales1"),
            json={"target_status_code": "UNDER_REVIEW"},
        )
        assert under_review.status_code == 200
        assert under_review.json()["event"]["event_name"] == "WorkOrderAmendmentMovedUnderReview"

        readiness_under_review = client.get(
            f"/api/work-orders/{work_order_public_id}/amendments/{amendment_public_id}/readiness",
            headers=auth_headers("sales1"),
        ).json()
        assert readiness_under_review["can_move_to_validated"] is True
        assert readiness_under_review["blocking_reasons"] == []

        validated = client.post(
            f"/api/work-orders/{work_order_public_id}/amendments/{amendment_public_id}/decision",
            headers=auth_headers("sales1"),
            json={"target_status_code": "VALIDATED"},
        )
        assert validated.status_code == 200
        assert validated.json()["amendment"]["amendment_status_code"] == "VALIDATED"
        assert validated.json()["event"]["event_name"] == "WorkOrderAmendmentValidated"

        # VALIDATED is terminal.
        further = client.post(
            f"/api/work-orders/{work_order_public_id}/amendments/{amendment_public_id}/decision",
            headers=auth_headers("sales1"),
            json={"target_status_code": "REJECTED", "reason": "Too late."},
        )
        assert further.status_code == 422

        # Generic header edit cannot bypass the transition; it's read-only now.
        edit_attempt = client.put(
            f"/api/work-orders/{work_order_public_id}/amendments/{amendment_public_id}",
            headers=auth_headers("sales1"),
            json={"remarks": "Trying to edit a terminal amendment."},
        )
        assert edit_attempt.status_code == 422
    finally:
        _teardown(
            work_order_public_ids=work_order_public_ids,
            offer_public_ids=offer_public_ids,
            opportunity_public_ids=opportunity_public_ids,
            account_public_ids=account_public_ids,
            lead_public_ids=lead_public_ids,
        )


def test_commercial_and_mixed_amendments_cannot_validate_without_accepted_basis_or_change_detail() -> None:
    work_order_public_ids: list[str] = []
    offer_public_ids: list[str] = []
    opportunity_public_ids: list[str] = []
    account_public_ids: list[str] = []
    lead_public_ids: list[str] = []
    try:
        chain = _build_accepted_work_order_chain()
        opportunity_public_ids.append(str(chain["opportunity"]["public_id"]))
        account_public_ids.append(str(chain["account"]["public_id"]))
        lead_public_ids.append(str(chain["lead"]["public_id"]))
        offer_public_ids.append(chain["base_offer_public_id"])
        work_order_public_id = str(chain["work_order"]["public_id"])
        work_order_public_ids.append(work_order_public_id)

        change_quotation = _create_related_offer(
            chain["base_offer_public_id"], offer_purpose="CHANGE_QUOTATION", work_order_public_id=work_order_public_id
        )
        offer_public_ids.insert(0, str(change_quotation["public_id"]))
        _accept_related_offer(change_quotation["public_id"])

        # Commercial amendment: accepted basis linked, but zero amendment lines -> blocked.
        commercial = client.post(
            f"/api/work-orders/{work_order_public_id}/amendments",
            headers=auth_headers("sales1"),
            json={
                "amendment_type_code": "COMMERCIAL",
                "received_date": "2026-07-13",
                "amendment_reason": "Customer requested a revised price.",
                "commercial_change_summary": "Revise the day rate.",
                "related_commercial_offer_public_id": change_quotation["public_id"],
            },
        ).json()["amendment"]
        commercial_public_id = commercial["public_id"]
        client.post(
            f"/api/work-orders/{work_order_public_id}/amendments/{commercial_public_id}/decision",
            headers=auth_headers("sales1"),
            json={"target_status_code": "UNDER_REVIEW"},
        )
        no_lines_validate = client.post(
            f"/api/work-orders/{work_order_public_id}/amendments/{commercial_public_id}/decision",
            headers=auth_headers("sales1"),
            json={"target_status_code": "VALIDATED"},
        )
        assert no_lines_validate.status_code == 422
        assert "amendment line" in no_lines_validate.json()["detail"]

        client.post(
            f"/api/work-orders/{work_order_public_id}/amendments/{commercial_public_id}/lines",
            headers=auth_headers("sales1"),
            json={
                "action_code": "ADD_LINE",
                "proposed_scope_description": "Additional scope for revised price.",
            },
        )
        now_validate = client.post(
            f"/api/work-orders/{work_order_public_id}/amendments/{commercial_public_id}/decision",
            headers=auth_headers("sales1"),
            json={"target_status_code": "VALIDATED"},
        )
        assert now_validate.status_code == 200

        # Mixed amendment: no related offer at all -> blocked even with a line present.
        mixed = client.post(
            f"/api/work-orders/{work_order_public_id}/amendments",
            headers=auth_headers("sales1"),
            json={
                "amendment_type_code": "MIXED",
                "received_date": "2026-07-13",
                "amendment_reason": "Customer requested a mixed change with no basis yet.",
                "commercial_change_summary": "Add scope and change contact.",
                "customer_amendment_reference": f"CUST-AMD-{uuid4()}",
            },
        ).json()["amendment"]
        mixed_public_id = mixed["public_id"]
        client.post(
            f"/api/work-orders/{work_order_public_id}/amendments/{mixed_public_id}/lines",
            headers=auth_headers("sales1"),
            json={"action_code": "ADD_LINE", "proposed_scope_description": "Proposed additional scope."},
        )
        client.post(
            f"/api/work-orders/{work_order_public_id}/amendments/{mixed_public_id}/decision",
            headers=auth_headers("sales1"),
            json={"target_status_code": "UNDER_REVIEW"},
        )
        no_basis_validate = client.post(
            f"/api/work-orders/{work_order_public_id}/amendments/{mixed_public_id}/decision",
            headers=auth_headers("sales1"),
            json={"target_status_code": "VALIDATED"},
        )
        assert no_basis_validate.status_code == 422
        assert "commercial basis" in no_basis_validate.json()["detail"]
    finally:
        _teardown(
            work_order_public_ids=work_order_public_ids,
            offer_public_ids=offer_public_ids,
            opportunity_public_ids=opportunity_public_ids,
            account_public_ids=account_public_ids,
            lead_public_ids=lead_public_ids,
        )


def test_invalid_transitions_and_reason_required_for_reject_and_cancel() -> None:
    work_order_public_ids: list[str] = []
    offer_public_ids: list[str] = []
    opportunity_public_ids: list[str] = []
    account_public_ids: list[str] = []
    lead_public_ids: list[str] = []
    try:
        chain = _build_accepted_work_order_chain()
        opportunity_public_ids.append(str(chain["opportunity"]["public_id"]))
        account_public_ids.append(str(chain["account"]["public_id"]))
        lead_public_ids.append(str(chain["lead"]["public_id"]))
        offer_public_ids.append(chain["base_offer_public_id"])
        work_order_public_id = str(chain["work_order"]["public_id"])
        work_order_public_ids.append(work_order_public_id)

        amendment = client.post(
            f"/api/work-orders/{work_order_public_id}/amendments",
            headers=auth_headers("sales1"),
            json={
                "amendment_type_code": "ADMINISTRATIVE",
                "received_date": "2026-07-13",
                "amendment_reason": "Administrative change.",
            },
        ).json()["amendment"]
        amendment_public_id = amendment["public_id"]

        # RECEIVED cannot jump straight to VALIDATED.
        skip_to_validated = client.post(
            f"/api/work-orders/{work_order_public_id}/amendments/{amendment_public_id}/decision",
            headers=auth_headers("sales1"),
            json={"target_status_code": "VALIDATED"},
        )
        assert skip_to_validated.status_code == 422

        # Reason required to reject.
        reject_no_reason = client.post(
            f"/api/work-orders/{work_order_public_id}/amendments/{amendment_public_id}/decision",
            headers=auth_headers("sales1"),
            json={"target_status_code": "REJECTED"},
        )
        assert reject_no_reason.status_code == 422
        assert "reason is required" in reject_no_reason.json()["detail"]

        reject = client.post(
            f"/api/work-orders/{work_order_public_id}/amendments/{amendment_public_id}/decision",
            headers=auth_headers("sales1"),
            json={"target_status_code": "REJECTED", "reason": "Customer withdrew the request."},
        )
        assert reject.status_code == 200
        assert reject.json()["amendment"]["amendment_status_code"] == "REJECTED"

        # REJECTED is terminal.
        further = client.post(
            f"/api/work-orders/{work_order_public_id}/amendments/{amendment_public_id}/decision",
            headers=auth_headers("sales1"),
            json={"target_status_code": "CANCELLED", "reason": "No longer relevant."},
        )
        assert further.status_code == 422

        # Separate amendment: RECEIVED -> CANCELLED requires a reason too.
        second_amendment = client.post(
            f"/api/work-orders/{work_order_public_id}/amendments",
            headers=auth_headers("sales1"),
            json={
                "amendment_type_code": "ADMINISTRATIVE",
                "received_date": "2026-07-13",
                "amendment_reason": "Will be cancelled.",
            },
        ).json()["amendment"]
        cancel_no_reason = client.post(
            f"/api/work-orders/{work_order_public_id}/amendments/{second_amendment['public_id']}/decision",
            headers=auth_headers("sales1"),
            json={"target_status_code": "CANCELLED"},
        )
        assert cancel_no_reason.status_code == 422
        cancel = client.post(
            f"/api/work-orders/{work_order_public_id}/amendments/{second_amendment['public_id']}/decision",
            headers=auth_headers("sales1"),
            json={"target_status_code": "CANCELLED", "reason": "Superseded by a later request."},
        )
        assert cancel.status_code == 200
        assert cancel.json()["amendment"]["amendment_status_code"] == "CANCELLED"
    finally:
        _teardown(
            work_order_public_ids=work_order_public_ids,
            offer_public_ids=offer_public_ids,
            opportunity_public_ids=opportunity_public_ids,
            account_public_ids=account_public_ids,
            lead_public_ids=lead_public_ids,
        )


def test_rejected_operations_leave_data_and_events_unchanged() -> None:
    work_order_public_ids: list[str] = []
    offer_public_ids: list[str] = []
    opportunity_public_ids: list[str] = []
    account_public_ids: list[str] = []
    lead_public_ids: list[str] = []
    try:
        chain = _build_accepted_work_order_chain()
        opportunity_public_ids.append(str(chain["opportunity"]["public_id"]))
        account_public_ids.append(str(chain["account"]["public_id"]))
        lead_public_ids.append(str(chain["lead"]["public_id"]))
        offer_public_ids.append(chain["base_offer_public_id"])
        work_order_public_id = str(chain["work_order"]["public_id"])
        work_order_public_ids.append(work_order_public_id)

        amendment = client.post(
            f"/api/work-orders/{work_order_public_id}/amendments",
            headers=auth_headers("sales1"),
            json={
                "amendment_type_code": "ADMINISTRATIVE",
                "received_date": "2026-07-13",
                "amendment_reason": "Administrative change.",
            },
        ).json()["amendment"]
        amendment_public_id = amendment["public_id"]

        with SessionLocal() as db:
            events_before = int(
                db.execute(
                    text(
                        "SELECT COUNT(*) FROM business_event WHERE record_type = 'work_order' AND record_public_id = :wo"
                    ),
                    {"wo": work_order_public_id},
                ).scalar_one()
            )

        invalid = client.post(
            f"/api/work-orders/{work_order_public_id}/amendments/{amendment_public_id}/decision",
            headers=auth_headers("sales1"),
            json={"target_status_code": "VALIDATED"},
        )
        assert invalid.status_code == 422

        with SessionLocal() as db:
            events_after = int(
                db.execute(
                    text(
                        "SELECT COUNT(*) FROM business_event WHERE record_type = 'work_order' AND record_public_id = :wo"
                    ),
                    {"wo": work_order_public_id},
                ).scalar_one()
            )
        assert events_after == events_before

        unchanged = client.get(
            f"/api/work-orders/{work_order_public_id}/amendments/{amendment_public_id}", headers=auth_headers("sales1")
        ).json()
        assert unchanged["amendment_status_code"] == "RECEIVED"
    finally:
        _teardown(
            work_order_public_ids=work_order_public_ids,
            offer_public_ids=offer_public_ids,
            opportunity_public_ids=opportunity_public_ids,
            account_public_ids=account_public_ids,
            lead_public_ids=lead_public_ids,
        )


def test_reads_create_no_event() -> None:
    work_order_public_ids: list[str] = []
    offer_public_ids: list[str] = []
    opportunity_public_ids: list[str] = []
    account_public_ids: list[str] = []
    lead_public_ids: list[str] = []
    try:
        chain = _build_accepted_work_order_chain()
        opportunity_public_ids.append(str(chain["opportunity"]["public_id"]))
        account_public_ids.append(str(chain["account"]["public_id"]))
        lead_public_ids.append(str(chain["lead"]["public_id"]))
        offer_public_ids.append(chain["base_offer_public_id"])
        work_order_public_id = str(chain["work_order"]["public_id"])
        work_order_public_ids.append(work_order_public_id)

        amendment = client.post(
            f"/api/work-orders/{work_order_public_id}/amendments",
            headers=auth_headers("sales1"),
            json={
                "amendment_type_code": "ADMINISTRATIVE",
                "received_date": "2026-07-13",
                "amendment_reason": "Administrative change.",
            },
        ).json()["amendment"]
        amendment_public_id = amendment["public_id"]

        with SessionLocal() as db:
            before = int(
                db.execute(
                    text("SELECT COUNT(*) FROM business_event WHERE record_type = 'work_order' AND record_public_id = :wo"),
                    {"wo": work_order_public_id},
                ).scalar_one()
            )

        client.get(f"/api/work-orders/{work_order_public_id}/amendments", headers=auth_headers("readonly1"))
        client.get(
            f"/api/work-orders/{work_order_public_id}/amendments/{amendment_public_id}", headers=auth_headers("readonly1")
        )
        client.get(
            f"/api/work-orders/{work_order_public_id}/amendments/{amendment_public_id}/lines",
            headers=auth_headers("readonly1"),
        )
        client.get(
            f"/api/work-orders/{work_order_public_id}/amendments/{amendment_public_id}/readiness",
            headers=auth_headers("readonly1"),
        )

        with SessionLocal() as db:
            after = int(
                db.execute(
                    text("SELECT COUNT(*) FROM business_event WHERE record_type = 'work_order' AND record_public_id = :wo"),
                    {"wo": work_order_public_id},
                ).scalar_one()
            )
        assert after == before
    finally:
        _teardown(
            work_order_public_ids=work_order_public_ids,
            offer_public_ids=offer_public_ids,
            opportunity_public_ids=opportunity_public_ids,
            account_public_ids=account_public_ids,
            lead_public_ids=lead_public_ids,
        )


def test_validation_creates_no_work_order_line_offer_or_amendment_application() -> None:
    work_order_public_ids: list[str] = []
    offer_public_ids: list[str] = []
    opportunity_public_ids: list[str] = []
    account_public_ids: list[str] = []
    lead_public_ids: list[str] = []
    try:
        chain = _build_accepted_work_order_chain()
        opportunity_public_ids.append(str(chain["opportunity"]["public_id"]))
        account_public_ids.append(str(chain["account"]["public_id"]))
        lead_public_ids.append(str(chain["lead"]["public_id"]))
        offer_public_ids.append(chain["base_offer_public_id"])
        work_order_public_id = str(chain["work_order"]["public_id"])
        work_order_public_ids.append(work_order_public_id)

        with SessionLocal() as db:
            wo_line_count_before = int(
                db.execute(
                    text(
                        "SELECT COUNT(*) FROM crm_work_order_line wol INNER JOIN crm_work_order wo ON wo.id = "
                        "wol.work_order_id WHERE wo.work_order_public_id = :wo"
                    ),
                    {"wo": work_order_public_id},
                ).scalar_one()
            )
            offer_count_before = int(db.execute(text("SELECT COUNT(*) FROM crm_commercial_offer")).scalar_one())
            work_order_count_before = int(db.execute(text("SELECT COUNT(*) FROM crm_work_order")).scalar_one())

        amendment = client.post(
            f"/api/work-orders/{work_order_public_id}/amendments",
            headers=auth_headers("sales1"),
            json={
                "amendment_type_code": "ADMINISTRATIVE",
                "received_date": "2026-07-13",
                "amendment_reason": "Administrative change.",
            },
        ).json()["amendment"]
        amendment_public_id = amendment["public_id"]
        client.post(
            f"/api/work-orders/{work_order_public_id}/amendments/{amendment_public_id}/decision",
            headers=auth_headers("sales1"),
            json={"target_status_code": "UNDER_REVIEW"},
        )
        validated = client.post(
            f"/api/work-orders/{work_order_public_id}/amendments/{amendment_public_id}/decision",
            headers=auth_headers("sales1"),
            json={"target_status_code": "VALIDATED"},
        )
        assert validated.status_code == 200
        assert validated.json()["event"]["event_payload"]["applied_to_work_order"] is False

        with SessionLocal() as db:
            wo_line_count_after = int(
                db.execute(
                    text(
                        "SELECT COUNT(*) FROM crm_work_order_line wol INNER JOIN crm_work_order wo ON wo.id = "
                        "wol.work_order_id WHERE wo.work_order_public_id = :wo"
                    ),
                    {"wo": work_order_public_id},
                ).scalar_one()
            )
            offer_count_after = int(db.execute(text("SELECT COUNT(*) FROM crm_commercial_offer")).scalar_one())
            work_order_count_after = int(db.execute(text("SELECT COUNT(*) FROM crm_work_order")).scalar_one())

        assert wo_line_count_after == wo_line_count_before
        assert offer_count_after == offer_count_before
        assert work_order_count_after == work_order_count_before
    finally:
        _teardown(
            work_order_public_ids=work_order_public_ids,
            offer_public_ids=offer_public_ids,
            opportunity_public_ids=opportunity_public_ids,
            account_public_ids=account_public_ids,
            lead_public_ids=lead_public_ids,
        )


# --- Read APIs and authorization -------------------------------------------------------------


def test_amendment_list_and_detail_expose_work_order_and_commercial_basis_context() -> None:
    work_order_public_ids: list[str] = []
    offer_public_ids: list[str] = []
    opportunity_public_ids: list[str] = []
    account_public_ids: list[str] = []
    lead_public_ids: list[str] = []
    try:
        chain = _build_accepted_work_order_chain()
        opportunity_public_ids.append(str(chain["opportunity"]["public_id"]))
        account_public_ids.append(str(chain["account"]["public_id"]))
        lead_public_ids.append(str(chain["lead"]["public_id"]))
        offer_public_ids.append(chain["base_offer_public_id"])
        work_order_public_id = str(chain["work_order"]["public_id"])
        work_order_public_ids.append(work_order_public_id)

        change_quotation = _create_related_offer(
            chain["base_offer_public_id"], offer_purpose="CHANGE_QUOTATION", work_order_public_id=work_order_public_id
        )
        offer_public_ids.insert(0, str(change_quotation["public_id"]))
        _accept_related_offer(change_quotation["public_id"])

        created = client.post(
            f"/api/work-orders/{work_order_public_id}/amendments",
            headers=auth_headers("sales1"),
            json={
                "amendment_type_code": "COMMERCIAL",
                "received_date": "2026-07-13",
                "amendment_reason": "Customer requested a revised price.",
                "commercial_change_summary": "Revise the day rate.",
                "related_commercial_offer_public_id": change_quotation["public_id"],
            },
        ).json()["amendment"]
        amendment_public_id = created["public_id"]
        line = client.post(
            f"/api/work-orders/{work_order_public_id}/amendments/{amendment_public_id}/lines",
            headers=auth_headers("sales1"),
            json={"action_code": "ADD_LINE", "proposed_scope_description": "Additional scope."},
        ).json()["amendment_line"]

        list_response = client.get(f"/api/work-orders/{work_order_public_id}/amendments", headers=auth_headers("sales1"))
        assert list_response.status_code == 200
        assert any(item["public_id"] == amendment_public_id for item in list_response.json())

        detail_response = client.get(
            f"/api/work-orders/{work_order_public_id}/amendments/{amendment_public_id}", headers=auth_headers("sales1")
        )
        assert detail_response.status_code == 200
        detail = detail_response.json()
        assert detail["work_order_public_id"] == work_order_public_id
        assert detail["related_commercial_offer_public_id"] == change_quotation["public_id"]
        assert detail["related_commercial_offer_purpose"] == "CHANGE_QUOTATION"

        lines_response = client.get(
            f"/api/work-orders/{work_order_public_id}/amendments/{amendment_public_id}/lines",
            headers=auth_headers("sales1"),
        )
        assert lines_response.status_code == 200
        assert lines_response.json()[0]["public_id"] == line["public_id"]
    finally:
        _teardown(
            work_order_public_ids=work_order_public_ids,
            offer_public_ids=offer_public_ids,
            opportunity_public_ids=opportunity_public_ids,
            account_public_ids=account_public_ids,
            lead_public_ids=lead_public_ids,
        )


def test_readiness_endpoint_reports_blockers_correctly() -> None:
    work_order_public_ids: list[str] = []
    offer_public_ids: list[str] = []
    opportunity_public_ids: list[str] = []
    account_public_ids: list[str] = []
    lead_public_ids: list[str] = []
    try:
        chain = _build_accepted_work_order_chain()
        opportunity_public_ids.append(str(chain["opportunity"]["public_id"]))
        account_public_ids.append(str(chain["account"]["public_id"]))
        lead_public_ids.append(str(chain["lead"]["public_id"]))
        offer_public_ids.append(chain["base_offer_public_id"])
        work_order_public_id = str(chain["work_order"]["public_id"])
        work_order_public_ids.append(work_order_public_id)

        amendment = client.post(
            f"/api/work-orders/{work_order_public_id}/amendments",
            headers=auth_headers("sales1"),
            json={
                "amendment_type_code": "COMMERCIAL",
                "received_date": "2026-07-13",
                "amendment_reason": "Customer requested additional scope.",
                "commercial_change_summary": "Add scope.",
            },
        ).json()["amendment"]
        amendment_public_id = amendment["public_id"]
        client.post(
            f"/api/work-orders/{work_order_public_id}/amendments/{amendment_public_id}/decision",
            headers=auth_headers("sales1"),
            json={"target_status_code": "UNDER_REVIEW"},
        )

        readiness = client.get(
            f"/api/work-orders/{work_order_public_id}/amendments/{amendment_public_id}/readiness",
            headers=auth_headers("sales1"),
        ).json()
        assert readiness["commercial_basis_required"] is True
        assert readiness["related_offer_linked"] is False
        assert readiness["has_required_change_detail"] is False
        assert readiness["can_move_to_validated"] is False
        assert len(readiness["blocking_reasons"]) >= 2
        assert readiness["applied_to_work_order"] is False
    finally:
        _teardown(
            work_order_public_ids=work_order_public_ids,
            offer_public_ids=offer_public_ids,
            opportunity_public_ids=opportunity_public_ids,
            account_public_ids=account_public_ids,
            lead_public_ids=lead_public_ids,
        )


def test_read_only_user_can_view_but_cannot_create_edit_or_transition() -> None:
    work_order_public_ids: list[str] = []
    offer_public_ids: list[str] = []
    opportunity_public_ids: list[str] = []
    account_public_ids: list[str] = []
    lead_public_ids: list[str] = []
    try:
        chain = _build_accepted_work_order_chain()
        opportunity_public_ids.append(str(chain["opportunity"]["public_id"]))
        account_public_ids.append(str(chain["account"]["public_id"]))
        lead_public_ids.append(str(chain["lead"]["public_id"]))
        offer_public_ids.append(chain["base_offer_public_id"])
        work_order_public_id = str(chain["work_order"]["public_id"])
        work_order_public_ids.append(work_order_public_id)

        amendment = client.post(
            f"/api/work-orders/{work_order_public_id}/amendments",
            headers=auth_headers("sales1"),
            json={
                "amendment_type_code": "ADMINISTRATIVE",
                "received_date": "2026-07-13",
                "amendment_reason": "Administrative change.",
            },
        ).json()["amendment"]
        amendment_public_id = amendment["public_id"]

        view_list = client.get(f"/api/work-orders/{work_order_public_id}/amendments", headers=auth_headers("readonly1"))
        assert view_list.status_code == 200

        create_attempt = client.post(
            f"/api/work-orders/{work_order_public_id}/amendments",
            headers=auth_headers("readonly1"),
            json={
                "amendment_type_code": "ADMINISTRATIVE",
                "received_date": "2026-07-13",
                "amendment_reason": "Should be forbidden.",
            },
        )
        assert create_attempt.status_code == 403

        edit_attempt = client.put(
            f"/api/work-orders/{work_order_public_id}/amendments/{amendment_public_id}",
            headers=auth_headers("readonly1"),
            json={"remarks": "Should be forbidden."},
        )
        assert edit_attempt.status_code == 403

        transition_attempt = client.post(
            f"/api/work-orders/{work_order_public_id}/amendments/{amendment_public_id}/decision",
            headers=auth_headers("readonly1"),
            json={"target_status_code": "UNDER_REVIEW"},
        )
        assert transition_attempt.status_code == 403

        line_attempt = client.post(
            f"/api/work-orders/{work_order_public_id}/amendments/{amendment_public_id}/lines",
            headers=auth_headers("readonly1"),
            json={"action_code": "ADD_LINE", "proposed_scope_description": "Should be forbidden."},
        )
        assert line_attempt.status_code == 403

        unauthenticated = client.get(f"/api/work-orders/{work_order_public_id}/amendments")
        assert unauthenticated.status_code in (401, 403)
    finally:
        _teardown(
            work_order_public_ids=work_order_public_ids,
            offer_public_ids=offer_public_ids,
            opportunity_public_ids=opportunity_public_ids,
            account_public_ids=account_public_ids,
            lead_public_ids=lead_public_ids,
        )
