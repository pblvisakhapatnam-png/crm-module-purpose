"""Slice 6O.1 - Supplementary Offer / Change Quotation related-offer foundation tests.

These tests reuse the existing helper functions from test_commercial_offers_api.py
(login, auth_headers, create_account_linked_test_opportunity, create_test_commercial_offer,
mark_test_commercial_offer_submitted, record_test_customer_response, create_test_work_order,
cleanup_test_records, cleanup_test_work_orders) rather than duplicating that setup logic.
"""

from uuid import uuid4

from sqlalchemy import text

from app.core.database import SessionLocal

from tests.test_commercial_offers_api import (
    auth_headers,
    client,
    cleanup_test_records,
    cleanup_test_work_orders,
    create_account_linked_test_opportunity,
    create_test_commercial_offer,
    create_test_offer_line,
    create_test_work_order,
    mark_test_commercial_offer_submitted,
    record_test_customer_response,
)


def _null_related_work_order_links(offer_public_ids: list[str]) -> None:
    """Breaks the crm_commercial_offer.related_work_order_id -> crm_work_order.id link
    before crm_work_order rows are deleted, avoiding the cross-table FK cycle introduced
    by Slice 6O.1 (the existing crm_work_order.commercial_offer_id -> crm_commercial_offer.id
    FK runs the opposite direction)."""
    if not offer_public_ids:
        return
    with SessionLocal() as db:
        for public_id in offer_public_ids:
            db.execute(
                text(
                    """
                    UPDATE crm_commercial_offer
                    SET related_work_order_id = NULL
                    WHERE offer_public_id = :public_id
                    """
                ),
                {"public_id": public_id},
            )
        db.commit()


def _accept_offer_with_line(offer_public_id: str) -> None:
    # mark_test_commercial_offer_submitted already creates one active offer line.
    mark_test_commercial_offer_submitted(offer_public_id)
    record_test_customer_response(offer_public_id, "ACCEPTED_AWARDED", received_at="2026-07-12T10:00:00Z")


def _build_accepted_base_chain(*, with_work_order: bool = False) -> dict[str, object]:
    linked = create_account_linked_test_opportunity()
    opportunity_public_id = str(linked["opportunity"]["public_id"])
    base_offer = create_test_commercial_offer(opportunity_public_id)
    base_offer_public_id = str(base_offer["public_id"])
    _accept_offer_with_line(base_offer_public_id)

    work_order = None
    if with_work_order:
        work_order = create_test_work_order(base_offer_public_id)

    return {
        "lead": linked["lead"],
        "account": linked["account"],
        "opportunity": linked["opportunity"],
        "base_offer_public_id": base_offer_public_id,
        "work_order": work_order,
    }


def _get_offer_row(offer_public_id: str) -> dict[str, object]:
    with SessionLocal() as db:
        row = db.execute(
            text(
                """
                SELECT offer_status_code, offer_purpose
                FROM crm_commercial_offer
                WHERE offer_public_id = :public_id
                """
            ),
            {"public_id": offer_public_id},
        ).first()
    assert row is not None
    return dict(row._mapping)


def test_ordinary_commercial_offer_is_created_as_base_purpose() -> None:
    opportunity_public_ids: list[str] = []
    offer_public_ids: list[str] = []
    try:
        linked = create_account_linked_test_opportunity()
        opportunity_public_id = str(linked["opportunity"]["public_id"])
        opportunity_public_ids.append(opportunity_public_id)
        offer = create_test_commercial_offer(opportunity_public_id)
        offer_public_ids.append(str(offer["public_id"]))

        assert offer["offer_purpose"] == "BASE"
        assert offer["base_offer_public_id"] is None
        assert offer["related_work_order_public_id"] is None
    finally:
        cleanup_test_records(
            opportunity_public_ids=opportunity_public_ids,
            offer_public_ids=offer_public_ids,
            account_public_ids=[str(linked["account"]["public_id"])],
            lead_public_ids=[str(linked["lead"]["public_id"])],
        )


def test_supplementary_offer_created_from_accepted_base_with_no_copied_data() -> None:
    opportunity_public_ids: list[str] = []
    offer_public_ids: list[str] = []
    account_public_ids: list[str] = []
    lead_public_ids: list[str] = []
    try:
        chain = _build_accepted_base_chain()
        opportunity_public_ids.append(str(chain["opportunity"]["public_id"]))
        account_public_ids.append(str(chain["account"]["public_id"]))
        lead_public_ids.append(str(chain["lead"]["public_id"]))
        base_offer_public_id = str(chain["base_offer_public_id"])
        offer_public_ids.append(base_offer_public_id)

        response = client.post(
            f"/api/commercial-offers/{base_offer_public_id}/related-offers",
            headers=auth_headers("sales1"),
            json={
                "offer_purpose": "SUPPLEMENTARY",
                "customer_request_summary": "Customer requested one additional crane for the same site.",
                "customer_request_reference": "CUST-REQ-001",
            },
        )
        assert response.status_code == 201
        body = response.json()
        related_offer = body["commercial_offer"]
        offer_public_ids.insert(0, str(related_offer["public_id"]))

        assert related_offer["offer_purpose"] == "SUPPLEMENTARY"
        assert related_offer["offer_status_code"] == "DRAFT"
        assert related_offer["base_offer_public_id"] == base_offer_public_id
        assert related_offer["related_work_order_public_id"] is None
        assert related_offer["opportunity_public_id"] == chain["opportunity"]["public_id"]
        assert related_offer["account_public_id"] == chain["account"]["public_id"]
        assert related_offer["customer_request_summary"] == "Customer requested one additional crane for the same site."
        assert body["event"]["event_name"] == "CommercialOfferRelatedOfferCreated"

        lines_response = client.get(
            f"/api/commercial-offers/{related_offer['public_id']}/lines",
            headers=auth_headers("sales1"),
        )
        assert lines_response.status_code == 200
        assert lines_response.json() == []

        # Base Offer itself is untouched.
        base_row = _get_offer_row(base_offer_public_id)
        assert base_row["offer_status_code"] == "ACCEPTED"
        assert base_row["offer_purpose"] == "BASE"

        # Exactly one business event recorded for the related offer's creation.
        with SessionLocal() as db:
            event_count = db.execute(
                text(
                    "SELECT COUNT(*) FROM business_event WHERE record_type = 'commercial_offer' "
                    "AND record_public_id = :public_id AND event_name = 'CommercialOfferRelatedOfferCreated'"
                ),
                {"public_id": related_offer["public_id"]},
            ).scalar_one()
        assert int(event_count) == 1
    finally:
        cleanup_test_records(
            opportunity_public_ids=opportunity_public_ids,
            offer_public_ids=offer_public_ids,
            account_public_ids=account_public_ids,
            lead_public_ids=lead_public_ids,
        )


def test_related_offer_listing_shows_multiple_independent_series() -> None:
    opportunity_public_ids: list[str] = []
    offer_public_ids: list[str] = []
    account_public_ids: list[str] = []
    lead_public_ids: list[str] = []
    work_order_public_ids: list[str] = []
    try:
        chain = _build_accepted_base_chain(with_work_order=True)
        opportunity_public_ids.append(str(chain["opportunity"]["public_id"]))
        account_public_ids.append(str(chain["account"]["public_id"]))
        lead_public_ids.append(str(chain["lead"]["public_id"]))
        base_offer_public_id = str(chain["base_offer_public_id"])
        offer_public_ids.append(base_offer_public_id)
        work_order_public_id = str(chain["work_order"]["public_id"])
        work_order_public_ids.append(work_order_public_id)

        supplementary_one = client.post(
            f"/api/commercial-offers/{base_offer_public_id}/related-offers",
            headers=auth_headers("sales1"),
            json={
                "offer_purpose": "SUPPLEMENTARY",
                "customer_request_summary": "First distinct additional-scope request.",
            },
        ).json()["commercial_offer"]
        supplementary_two = client.post(
            f"/api/commercial-offers/{base_offer_public_id}/related-offers",
            headers=auth_headers("sales1"),
            json={
                "offer_purpose": "SUPPLEMENTARY",
                "customer_request_summary": "Second, unrelated additional-scope request.",
            },
        ).json()["commercial_offer"]
        change_quotation = client.post(
            f"/api/commercial-offers/{base_offer_public_id}/related-offers",
            headers=auth_headers("sales1"),
            json={
                "offer_purpose": "CHANGE_QUOTATION",
                "related_work_order_public_id": work_order_public_id,
                "customer_request_summary": "Customer requested a revised price before an amendment.",
            },
        ).json()["commercial_offer"]
        for related in (supplementary_one, supplementary_two, change_quotation):
            offer_public_ids.insert(0, str(related["public_id"]))

        assert change_quotation["offer_purpose"] == "CHANGE_QUOTATION"
        assert change_quotation["related_work_order_public_id"] == work_order_public_id

        listing_response = client.get(
            f"/api/commercial-offers/{base_offer_public_id}/related-offers",
            headers=auth_headers("readonly1"),
        )
        assert listing_response.status_code == 200
        listed_ids = {row["public_id"] for row in listing_response.json()}
        assert listed_ids == {
            supplementary_one["public_id"],
            supplementary_two["public_id"],
            change_quotation["public_id"],
        }

        opportunity_offers = client.get(
            "/api/commercial-offers",
            headers=auth_headers("sales1"),
            params={"opportunity_public_id": chain["opportunity"]["public_id"], "limit": 20},
        ).json()
        purposes = {row["public_id"]: row["offer_purpose"] for row in opportunity_offers}
        assert purposes[base_offer_public_id] == "BASE"
        assert purposes[supplementary_one["public_id"]] == "SUPPLEMENTARY"
        assert purposes[change_quotation["public_id"]] == "CHANGE_QUOTATION"

        wo_related_response = client.get(
            f"/api/work-orders/{work_order_public_id}/related-offers",
            headers=auth_headers("sales1"),
        )
        assert wo_related_response.status_code == 200
        wo_related = wo_related_response.json()
        assert len(wo_related) == 1
        assert wo_related[0]["public_id"] == change_quotation["public_id"]
        assert wo_related[0]["offer_purpose"] == "CHANGE_QUOTATION"
        assert wo_related[0]["base_offer_public_id"] == base_offer_public_id
    finally:
        _null_related_work_order_links(offer_public_ids)
        cleanup_test_work_orders(work_order_public_ids)
        cleanup_test_records(
            opportunity_public_ids=opportunity_public_ids,
            offer_public_ids=offer_public_ids,
            account_public_ids=account_public_ids,
            lead_public_ids=lead_public_ids,
        )


def test_change_quotation_requires_linked_work_order() -> None:
    opportunity_public_ids: list[str] = []
    offer_public_ids: list[str] = []
    account_public_ids: list[str] = []
    lead_public_ids: list[str] = []
    try:
        chain = _build_accepted_base_chain()
        opportunity_public_ids.append(str(chain["opportunity"]["public_id"]))
        account_public_ids.append(str(chain["account"]["public_id"]))
        lead_public_ids.append(str(chain["lead"]["public_id"]))
        base_offer_public_id = str(chain["base_offer_public_id"])
        offer_public_ids.append(base_offer_public_id)

        response = client.post(
            f"/api/commercial-offers/{base_offer_public_id}/related-offers",
            headers=auth_headers("sales1"),
            json={
                "offer_purpose": "CHANGE_QUOTATION",
                "customer_request_summary": "Customer requested a revised price for the existing Work Order.",
            },
        )
        assert response.status_code == 422
        assert "Work Order" in response.json()["detail"]
    finally:
        cleanup_test_records(
            opportunity_public_ids=opportunity_public_ids,
            offer_public_ids=offer_public_ids,
            account_public_ids=account_public_ids,
            lead_public_ids=lead_public_ids,
        )


def test_related_offer_rejects_cross_opportunity_work_order_lineage() -> None:
    opportunity_public_ids: list[str] = []
    offer_public_ids: list[str] = []
    account_public_ids: list[str] = []
    lead_public_ids: list[str] = []
    work_order_public_ids: list[str] = []
    try:
        chain_one = _build_accepted_base_chain()
        chain_two = _build_accepted_base_chain(with_work_order=True)
        for chain in (chain_one, chain_two):
            opportunity_public_ids.append(str(chain["opportunity"]["public_id"]))
            account_public_ids.append(str(chain["account"]["public_id"]))
            lead_public_ids.append(str(chain["lead"]["public_id"]))
            offer_public_ids.append(str(chain["base_offer_public_id"]))
        work_order_public_ids.append(str(chain_two["work_order"]["public_id"]))

        response = client.post(
            f"/api/commercial-offers/{chain_one['base_offer_public_id']}/related-offers",
            headers=auth_headers("sales1"),
            json={
                "offer_purpose": "CHANGE_QUOTATION",
                "related_work_order_public_id": chain_two["work_order"]["public_id"],
                "customer_request_summary": "Attempted cross-Opportunity linkage.",
            },
        )
        assert response.status_code == 422
        assert "Opportunity" in response.json()["detail"]
    finally:
        _null_related_work_order_links(offer_public_ids)
        cleanup_test_work_orders(work_order_public_ids)
        cleanup_test_records(
            opportunity_public_ids=opportunity_public_ids,
            offer_public_ids=offer_public_ids,
            account_public_ids=account_public_ids,
            lead_public_ids=lead_public_ids,
        )


def test_related_offer_rejects_invalid_purpose_and_blank_summary_and_missing_base() -> None:
    opportunity_public_ids: list[str] = []
    offer_public_ids: list[str] = []
    account_public_ids: list[str] = []
    lead_public_ids: list[str] = []
    try:
        chain = _build_accepted_base_chain()
        opportunity_public_ids.append(str(chain["opportunity"]["public_id"]))
        account_public_ids.append(str(chain["account"]["public_id"]))
        lead_public_ids.append(str(chain["lead"]["public_id"]))
        base_offer_public_id = str(chain["base_offer_public_id"])
        offer_public_ids.append(base_offer_public_id)

        invalid_purpose = client.post(
            f"/api/commercial-offers/{base_offer_public_id}/related-offers",
            headers=auth_headers("sales1"),
            json={"offer_purpose": "BASE", "customer_request_summary": "Not a valid related-offer purpose."},
        )
        assert invalid_purpose.status_code == 422

        blank_summary = client.post(
            f"/api/commercial-offers/{base_offer_public_id}/related-offers",
            headers=auth_headers("sales1"),
            json={"offer_purpose": "SUPPLEMENTARY", "customer_request_summary": "   "},
        )
        assert blank_summary.status_code == 422

        missing_base = client.post(
            f"/api/commercial-offers/{uuid4()}/related-offers",
            headers=auth_headers("sales1"),
            json={"offer_purpose": "SUPPLEMENTARY", "customer_request_summary": "Valid summary."},
        )
        assert missing_base.status_code == 404

        forbidden = client.post(
            f"/api/commercial-offers/{base_offer_public_id}/related-offers",
            headers=auth_headers("readonly1"),
            json={"offer_purpose": "SUPPLEMENTARY", "customer_request_summary": "Valid summary."},
        )
        assert forbidden.status_code == 403
    finally:
        cleanup_test_records(
            opportunity_public_ids=opportunity_public_ids,
            offer_public_ids=offer_public_ids,
            account_public_ids=account_public_ids,
            lead_public_ids=lead_public_ids,
        )


def test_related_offer_cannot_be_created_from_draft_or_non_accepted_base() -> None:
    opportunity_public_ids: list[str] = []
    offer_public_ids: list[str] = []
    try:
        linked = create_account_linked_test_opportunity()
        opportunity_public_id = str(linked["opportunity"]["public_id"])
        opportunity_public_ids.append(opportunity_public_id)
        draft_offer = create_test_commercial_offer(opportunity_public_id)
        draft_offer_public_id = str(draft_offer["public_id"])
        offer_public_ids.append(draft_offer_public_id)

        response = client.post(
            f"/api/commercial-offers/{draft_offer_public_id}/related-offers",
            headers=auth_headers("sales1"),
            json={"offer_purpose": "SUPPLEMENTARY", "customer_request_summary": "Should be rejected; base is DRAFT."},
        )
        assert response.status_code == 422
        assert "Accepted" in response.json()["detail"]
    finally:
        cleanup_test_records(
            opportunity_public_ids=opportunity_public_ids,
            offer_public_ids=offer_public_ids,
            account_public_ids=[str(linked["account"]["public_id"])],
            lead_public_ids=[str(linked["lead"]["public_id"])],
        )


def test_related_offer_cannot_be_created_from_another_related_offer() -> None:
    opportunity_public_ids: list[str] = []
    offer_public_ids: list[str] = []
    account_public_ids: list[str] = []
    lead_public_ids: list[str] = []
    try:
        chain = _build_accepted_base_chain()
        opportunity_public_ids.append(str(chain["opportunity"]["public_id"]))
        account_public_ids.append(str(chain["account"]["public_id"]))
        lead_public_ids.append(str(chain["lead"]["public_id"]))
        base_offer_public_id = str(chain["base_offer_public_id"])
        offer_public_ids.append(base_offer_public_id)

        supplementary = client.post(
            f"/api/commercial-offers/{base_offer_public_id}/related-offers",
            headers=auth_headers("sales1"),
            json={"offer_purpose": "SUPPLEMENTARY", "customer_request_summary": "First-level related offer."},
        ).json()["commercial_offer"]
        offer_public_ids.insert(0, str(supplementary["public_id"]))

        chained_response = client.post(
            f"/api/commercial-offers/{supplementary['public_id']}/related-offers",
            headers=auth_headers("sales1"),
            json={"offer_purpose": "SUPPLEMENTARY", "customer_request_summary": "Attempted chain, must be rejected."},
        )
        assert chained_response.status_code == 422
        assert "Base Offer" in chained_response.json()["detail"]
    finally:
        cleanup_test_records(
            opportunity_public_ids=opportunity_public_ids,
            offer_public_ids=offer_public_ids,
            account_public_ids=account_public_ids,
            lead_public_ids=lead_public_ids,
        )


def test_actionable_base_offer_guard_ignores_related_offers_and_names_base_offer() -> None:
    """Slice 6B.1's one-active-Base-Offer-per-Opportunity guard must scope its scan to
    offer_purpose = BASE. Before this fix, the guard scanned every offer for the
    Opportunity regardless of purpose, so once a Supplementary Offer existed it could be
    reported (by created_at recency) as the blocking record instead of the real Base
    Offer."""
    opportunity_public_ids: list[str] = []
    offer_public_ids: list[str] = []
    account_public_ids: list[str] = []
    lead_public_ids: list[str] = []
    try:
        chain = _build_accepted_base_chain()
        opportunity_public_id = str(chain["opportunity"]["public_id"])
        opportunity_public_ids.append(opportunity_public_id)
        account_public_ids.append(str(chain["account"]["public_id"]))
        lead_public_ids.append(str(chain["lead"]["public_id"]))
        base_offer_public_id = str(chain["base_offer_public_id"])
        offer_public_ids.append(base_offer_public_id)

        supplementary = client.post(
            f"/api/commercial-offers/{base_offer_public_id}/related-offers",
            headers=auth_headers("sales1"),
            json={"offer_purpose": "SUPPLEMENTARY", "customer_request_summary": "Newer record than the Base Offer."},
        ).json()["commercial_offer"]
        offer_public_ids.insert(0, str(supplementary["public_id"]))

        blocked_response = client.post(
            "/api/commercial-offers",
            headers=auth_headers("sales1"),
            json={"opportunity_public_id": opportunity_public_id, "offer_title": "Should be blocked by Base Offer."},
        )
        assert blocked_response.status_code == 422
        detail = blocked_response.json()["detail"]
        # The guard must point at the actual (older) Base Offer, not the newer Supplementary Offer.
        with SessionLocal() as db:
            base_code = db.execute(
                text("SELECT offer_code FROM crm_commercial_offer WHERE offer_public_id = :public_id"),
                {"public_id": base_offer_public_id},
            ).scalar_one()
        assert base_code in detail
        assert supplementary["offer_code"] not in detail
    finally:
        cleanup_test_records(
            opportunity_public_ids=opportunity_public_ids,
            offer_public_ids=offer_public_ids,
            account_public_ids=account_public_ids,
            lead_public_ids=lead_public_ids,
        )


def test_related_offer_has_independent_lifecycle_and_does_not_mutate_base_offer() -> None:
    opportunity_public_ids: list[str] = []
    offer_public_ids: list[str] = []
    account_public_ids: list[str] = []
    lead_public_ids: list[str] = []
    try:
        chain = _build_accepted_base_chain()
        opportunity_public_ids.append(str(chain["opportunity"]["public_id"]))
        account_public_ids.append(str(chain["account"]["public_id"]))
        lead_public_ids.append(str(chain["lead"]["public_id"]))
        base_offer_public_id = str(chain["base_offer_public_id"])
        offer_public_ids.append(base_offer_public_id)

        supplementary = client.post(
            f"/api/commercial-offers/{base_offer_public_id}/related-offers",
            headers=auth_headers("sales1"),
            json={"offer_purpose": "SUPPLEMENTARY", "customer_request_summary": "Independent lifecycle test."},
        ).json()["commercial_offer"]
        related_offer_public_id = str(supplementary["public_id"])
        offer_public_ids.insert(0, related_offer_public_id)

        _accept_offer_with_line(related_offer_public_id)

        related_row = _get_offer_row(related_offer_public_id)
        assert related_row["offer_status_code"] == "ACCEPTED"

        base_row = _get_offer_row(base_offer_public_id)
        assert base_row["offer_status_code"] == "ACCEPTED"

        base_lines = client.get(
            f"/api/commercial-offers/{base_offer_public_id}/lines",
            headers=auth_headers("sales1"),
        ).json()
        assert len(base_lines) == 1

        # No Work Order was auto-created for either offer by the acceptance itself.
        with SessionLocal() as db:
            wo_count = db.execute(
                text(
                    """
                    SELECT COUNT(*) FROM crm_work_order wo
                    INNER JOIN crm_commercial_offer co ON co.id = wo.commercial_offer_id
                    WHERE co.offer_public_id IN (:base_offer_public_id, :related_offer_public_id)
                    """
                ),
                {"base_offer_public_id": base_offer_public_id, "related_offer_public_id": related_offer_public_id},
            ).scalar_one()
        assert int(wo_count) == 0

        guidance = client.get(
            f"/api/commercial-offers/{related_offer_public_id}/lifecycle-guidance",
            headers=auth_headers("sales1"),
        )
        assert guidance.status_code == 200
        assert guidance.json()["lifecycle_state"] == "ACCEPTED_READY_FOR_HANDOFF"
    finally:
        cleanup_test_records(
            opportunity_public_ids=opportunity_public_ids,
            offer_public_ids=offer_public_ids,
            account_public_ids=account_public_ids,
            lead_public_ids=lead_public_ids,
        )


def test_related_offer_creation_is_unreachable_without_account_traceability() -> None:
    """The related-offer eligibility check requires the Base Offer to be ACCEPTED, and
    ACCEPTED is only reachable through the Slice 6L Customer Response action, which
    itself is blocked by the Slice 6A.1 Account traceability guard. So an Opportunity
    with no Account link can never produce an eligible Base Offer in the first place;
    this test proves that upstream guard still holds after this slice's changes,
    which is what makes create_related_commercial_offer's own defensive Account check
    unreachable through the real API today."""
    opportunity_public_ids: list[str] = []
    offer_public_ids: list[str] = []
    try:
        from tests.test_commercial_offers_api import create_test_opportunity, create_test_submission_evidence

        unlinked_opportunity = create_test_opportunity()
        opportunity_public_id = str(unlinked_opportunity["public_id"])
        opportunity_public_ids.append(opportunity_public_id)
        base_offer = create_test_commercial_offer(opportunity_public_id)
        base_offer_public_id = str(base_offer["public_id"])
        offer_public_ids.append(base_offer_public_id)

        create_test_offer_line(base_offer_public_id)
        create_test_submission_evidence(base_offer_public_id)
        mark_submitted_response = client.post(
            f"/api/commercial-offers/{base_offer_public_id}/mark-submitted",
            headers=auth_headers("sales1"),
        )
        assert mark_submitted_response.status_code == 422
        assert "Account" in mark_submitted_response.json()["detail"]
    finally:
        cleanup_test_records(
            opportunity_public_ids=opportunity_public_ids,
            offer_public_ids=offer_public_ids,
        )
