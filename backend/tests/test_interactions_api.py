"""Slice 9D - Interaction Foundation API tests.

Reuses the existing fixture helpers from test_commercial_offers_api.py (auth_headers, client,
create_account_linked_test_opportunity, create_test_commercial_offer, mark_test_commercial_offer_
submitted, record_test_customer_response, create_test_work_order), following the reuse pattern
already established by test_work_order_amendments_api.py, rather than duplicating that chain
setup.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import text

from app.core.database import SessionLocal

from tests.test_commercial_offers_api import (
    auth_headers,
    client,
    create_account_linked_test_opportunity,
    create_test_commercial_offer,
    create_test_work_order,
    mark_test_commercial_offer_submitted,
    record_test_customer_response,
)


def _cleanup_interactions(interaction_public_ids: list[str]) -> None:
    if not interaction_public_ids:
        return
    with SessionLocal() as db:
        db.execute(
            text(
                """
                DELETE FROM interaction_participant
                WHERE interaction_id IN (
                    SELECT id FROM interaction WHERE interaction_public_id = ANY(:ids)
                )
                """
            ),
            {"ids": interaction_public_ids},
        )
        db.execute(
            text("DELETE FROM interaction WHERE interaction_public_id = ANY(:ids)"),
            {"ids": interaction_public_ids},
        )
        db.commit()


def _teardown_full_chain(
    *,
    interaction_public_ids: list[str],
    work_order_public_ids: list[str],
    offer_public_ids: list[str],
    opportunity_public_ids: list[str],
    account_public_ids: list[str],
    lead_public_ids: list[str],
) -> None:
    _cleanup_interactions(interaction_public_ids)
    from tests.test_commercial_offers_api import cleanup_test_records

    # Ownership-based contact cleanup: any Account Contact belonging to an Account this run
    # created, discovered rather than tracked, so a test that creates one through the API does
    # not have to remember to list it. cleanup_test_records deletes the Account itself and would
    # otherwise hit fk_business_party_contact_business_party.
    if account_public_ids:
        with SessionLocal() as db:
            db.execute(
                text(
                    "DELETE FROM business_party_contact c USING business_party bp "
                    "WHERE bp.id = c.business_party_id "
                    "AND bp.business_party_public_id = ANY(:ids)"
                ),
                {"ids": account_public_ids},
            )
            db.commit()

    with SessionLocal() as db:
        for public_id in work_order_public_ids:
            db.execute(
                text(
                    "DELETE FROM crm_work_order_line wol USING crm_work_order wo "
                    "WHERE wo.id = wol.work_order_id AND wo.work_order_public_id = :public_id"
                ),
                {"public_id": public_id},
            )
            db.execute(
                text("DELETE FROM crm_work_order WHERE work_order_public_id = :public_id"),
                {"public_id": public_id},
            )
        db.commit()

    cleanup_test_records(
        opportunity_public_ids=opportunity_public_ids,
        offer_public_ids=offer_public_ids,
        account_public_ids=account_public_ids,
        lead_public_ids=lead_public_ids,
    )


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


# --- Happy path: create, list, get, on an Opportunity ---------------------------------------


def test_create_and_read_an_interaction_against_an_opportunity() -> None:
    lead_ids: list[str] = []
    account_ids: list[str] = []
    opportunity_ids: list[str] = []
    interaction_ids: list[str] = []
    try:
        chain = create_account_linked_test_opportunity()
        lead_ids.append(str(chain["lead"]["public_id"]))
        account_ids.append(str(chain["account"]["public_id"]))
        opportunity_public_id = str(chain["opportunity"]["public_id"])
        opportunity_ids.append(opportunity_public_id)

        response = client.post(
            "/api/interactions",
            headers=auth_headers("sales1"),
            json={
                "linked_record_type": "opportunity",
                "linked_record_public_id": opportunity_public_id,
                "channel_code": "CALL",
                "direction_code": "OUTBOUND",
                "occurred_at": _iso_now(),
                "subject": "Follow-up call",
                "body_text": "Discussed crane rates for the site.",
                "outcome": "Customer requested a quote.",
            },
        )
        assert response.status_code == 201
        body = response.json()
        interaction = body["interaction"]
        interaction_ids.append(interaction["public_id"])

        assert interaction["linked_record_type"] == "opportunity"
        assert interaction["linked_record_public_id"] == opportunity_public_id
        assert interaction["body_text"] == "Discussed crane rates for the site."
        assert interaction["body_stored"] is True
        assert interaction["body_redacted"] is False
        assert body["event"]["event_name"] == "InteractionRecorded"

        detail = client.get(
            f"/api/interactions/{interaction['public_id']}",
            headers=auth_headers("sales1"),
        )
        assert detail.status_code == 200
        assert detail.json()["body_text"] == "Discussed crane rates for the site."

        listing = client.get(
            "/api/interactions",
            headers=auth_headers("sales1"),
            params={
                "linked_record_type": "opportunity",
                "linked_record_public_id": opportunity_public_id,
            },
        )
        assert listing.status_code == 200
        assert len(listing.json()) == 1
        assert listing.json()[0]["public_id"] == interaction["public_id"]
    finally:
        _teardown_full_chain(
            interaction_public_ids=interaction_ids,
            work_order_public_ids=[],
            offer_public_ids=[],
            opportunity_public_ids=opportunity_ids,
            account_public_ids=account_ids,
            lead_public_ids=lead_ids,
        )


# --- Validation: unknown linked_record_type, nonexistent target -----------------------------


def test_create_rejects_an_unknown_linked_record_type() -> None:
    response = client.post(
        "/api/interactions",
        headers=auth_headers("sales1"),
        json={
            "linked_record_type": "not_a_real_type",
            "linked_record_public_id": str(uuid4()),
            "channel_code": "CALL",
            "direction_code": "OUTBOUND",
            "occurred_at": _iso_now(),
        },
    )
    assert response.status_code == 422


def test_create_rejects_a_well_formed_but_nonexistent_target() -> None:
    response = client.post(
        "/api/interactions",
        headers=auth_headers("sales1"),
        json={
            "linked_record_type": "lead",
            "linked_record_public_id": str(uuid4()),
            "channel_code": "CALL",
            "direction_code": "OUTBOUND",
            "occurred_at": _iso_now(),
        },
    )
    assert response.status_code == 422
    assert "No lead record exists" in response.json()["detail"]


def test_create_rejects_an_unknown_channel_or_direction() -> None:
    lead_ids: list[str] = []
    account_ids: list[str] = []
    opportunity_ids: list[str] = []
    try:
        chain = create_account_linked_test_opportunity()
        lead_ids.append(str(chain["lead"]["public_id"]))
        account_ids.append(str(chain["account"]["public_id"]))
        opportunity_public_id = str(chain["opportunity"]["public_id"])
        opportunity_ids.append(opportunity_public_id)

        bad_channel = client.post(
            "/api/interactions",
            headers=auth_headers("sales1"),
            json={
                "linked_record_type": "opportunity",
                "linked_record_public_id": opportunity_public_id,
                "channel_code": "CARRIER_PIGEON",
                "direction_code": "OUTBOUND",
                "occurred_at": _iso_now(),
            },
        )
        assert bad_channel.status_code == 422

        bad_direction = client.post(
            "/api/interactions",
            headers=auth_headers("sales1"),
            json={
                "linked_record_type": "opportunity",
                "linked_record_public_id": opportunity_public_id,
                "channel_code": "CALL",
                "direction_code": "SIDEWAYS",
                "occurred_at": _iso_now(),
            },
        )
        assert bad_direction.status_code == 422
    finally:
        _teardown_full_chain(
            interaction_public_ids=[],
            work_order_public_ids=[],
            offer_public_ids=[],
            opportunity_public_ids=opportunity_ids,
            account_public_ids=account_ids,
            lead_public_ids=lead_ids,
        )


# --- Permission: Finance sees metadata, not content (redaction on both list and detail) ------


def test_finance_role_sees_the_interaction_but_not_its_content() -> None:
    lead_ids: list[str] = []
    account_ids: list[str] = []
    opportunity_ids: list[str] = []
    interaction_ids: list[str] = []
    try:
        chain = create_account_linked_test_opportunity()
        lead_ids.append(str(chain["lead"]["public_id"]))
        account_ids.append(str(chain["account"]["public_id"]))
        opportunity_public_id = str(chain["opportunity"]["public_id"])
        opportunity_ids.append(opportunity_public_id)

        create_response = client.post(
            "/api/interactions",
            headers=auth_headers("sales1"),
            json={
                "linked_record_type": "opportunity",
                "linked_record_public_id": opportunity_public_id,
                "channel_code": "EMAIL",
                "direction_code": "INBOUND",
                "occurred_at": _iso_now(),
                "subject": "RFQ",
                "body_text": "Please quote for 2 mobile cranes at Site B.",
                "participants": [
                    {"party_role_code": "FROM", "display_name": "Customer", "address_or_number": "customer@example.com"},
                ],
            },
        )
        assert create_response.status_code == 201
        interaction_public_id = create_response.json()["interaction"]["public_id"]
        interaction_ids.append(interaction_public_id)

        # Finance: detail redaction.
        finance_detail = client.get(
            f"/api/interactions/{interaction_public_id}",
            headers=auth_headers("finance1"),
        )
        assert finance_detail.status_code == 200
        finance_body = finance_detail.json()
        assert finance_body["body_text"] is None
        assert finance_body["body_redacted"] is True
        assert finance_body["subject"] == "RFQ"  # metadata remains visible
        assert finance_body["participants"][0]["address_or_number"] is None
        assert finance_body["participants"][0]["display_name"] == "Customer"

        # Finance: list redaction. This is the classic failure mode - hiding content on detail
        # but forgetting the list - proved explicitly rather than assumed from the shared
        # serializer's existence.
        finance_list = client.get(
            "/api/interactions",
            headers=auth_headers("finance1"),
            params={
                "linked_record_type": "opportunity",
                "linked_record_public_id": opportunity_public_id,
            },
        )
        assert finance_list.status_code == 200
        assert finance_list.json()[0]["body_text"] is None
        assert finance_list.json()[0]["body_redacted"] is True

        # Sales: full content, both routes.
        sales_detail = client.get(
            f"/api/interactions/{interaction_public_id}",
            headers=auth_headers("sales1"),
        )
        assert sales_detail.json()["body_text"] == "Please quote for 2 mobile cranes at Site B."
        assert sales_detail.json()["body_redacted"] is False
        assert sales_detail.json()["participants"][0]["address_or_number"] == "customer@example.com"

        sales_list = client.get(
            "/api/interactions",
            headers=auth_headers("sales1"),
            params={
                "linked_record_type": "opportunity",
                "linked_record_public_id": opportunity_public_id,
            },
        )
        assert sales_list.json()[0]["body_text"] == "Please quote for 2 mobile cranes at Site B."
    finally:
        _teardown_full_chain(
            interaction_public_ids=interaction_ids,
            work_order_public_ids=[],
            offer_public_ids=[],
            opportunity_public_ids=opportunity_ids,
            account_public_ids=account_ids,
            lead_public_ids=lead_ids,
        )


# --- Permission: read-only role cannot create --------------------------------------------


def test_readonly_role_can_read_but_not_create() -> None:
    lead_ids: list[str] = []
    account_ids: list[str] = []
    opportunity_ids: list[str] = []
    try:
        chain = create_account_linked_test_opportunity()
        lead_ids.append(str(chain["lead"]["public_id"]))
        account_ids.append(str(chain["account"]["public_id"]))
        opportunity_public_id = str(chain["opportunity"]["public_id"])
        opportunity_ids.append(opportunity_public_id)

        create_response = client.post(
            "/api/interactions",
            headers=auth_headers("readonly1"),
            json={
                "linked_record_type": "opportunity",
                "linked_record_public_id": opportunity_public_id,
                "channel_code": "CALL",
                "direction_code": "OUTBOUND",
                "occurred_at": _iso_now(),
            },
        )
        assert create_response.status_code == 403

        list_response = client.get(
            "/api/interactions",
            headers=auth_headers("readonly1"),
            params={
                "linked_record_type": "opportunity",
                "linked_record_public_id": opportunity_public_id,
            },
        )
        assert list_response.status_code == 200
    finally:
        _teardown_full_chain(
            interaction_public_ids=[],
            work_order_public_ids=[],
            offer_public_ids=[],
            opportunity_public_ids=opportunity_ids,
            account_public_ids=account_ids,
            lead_public_ids=lead_ids,
        )


# --- Immutability ---------------------------------------------------------------------------


def test_update_can_change_only_outcome_and_follow_up() -> None:
    lead_ids: list[str] = []
    account_ids: list[str] = []
    opportunity_ids: list[str] = []
    interaction_ids: list[str] = []
    try:
        chain = create_account_linked_test_opportunity()
        lead_ids.append(str(chain["lead"]["public_id"]))
        account_ids.append(str(chain["account"]["public_id"]))
        opportunity_public_id = str(chain["opportunity"]["public_id"])
        opportunity_ids.append(opportunity_public_id)

        create_response = client.post(
            "/api/interactions",
            headers=auth_headers("sales1"),
            json={
                "linked_record_type": "opportunity",
                "linked_record_public_id": opportunity_public_id,
                "channel_code": "CALL",
                "direction_code": "OUTBOUND",
                "occurred_at": _iso_now(),
                "subject": "Original subject",
                "body_text": "Original body.",
            },
        )
        interaction_public_id = create_response.json()["interaction"]["public_id"]
        interaction_ids.append(interaction_public_id)

        update_response = client.put(
            f"/api/interactions/{interaction_public_id}",
            headers=auth_headers("sales1"),
            json={"outcome": "Customer will revert next week.", "next_follow_up_at": _iso_now()},
        )
        assert update_response.status_code == 200
        updated = update_response.json()["interaction"]
        assert updated["outcome"] == "Customer will revert next week."
        # Immutable fields unchanged by a legitimate update. That the schema also *refuses* an
        # attempt to change them is a separate property, proved in
        # test_update_refuses_an_immutable_field_and_changes_nothing - declaring no field is not
        # the same as refusing one, which is exactly the defect that test exists for.
        assert updated["subject"] == "Original subject"
        assert updated["body_text"] == "Original body."
    finally:
        _teardown_full_chain(
            interaction_public_ids=interaction_ids,
            work_order_public_ids=[],
            offer_public_ids=[],
            opportunity_public_ids=opportunity_ids,
            account_public_ids=account_ids,
            lead_public_ids=lead_ids,
        )


def test_the_request_schemas_declare_only_their_own_fields_and_forbid_extras() -> None:
    """Two properties, and the second is the one that matters.

    Declaring no field for an immutable column is NOT sufficient on its own: under Pydantic's
    default extra="ignore" a PUT carrying that field is accepted and silently discarded. This
    test previously asserted only the field list and was, by itself, evidence of nothing. It now
    also pins extra="forbid" on all three request schemas, which is what actually refuses the
    attempt. The behavioural proof is
    test_update_refuses_an_immutable_field_and_changes_nothing.
    """
    from app.modules.interactions.schemas import (
        InteractionCreate,
        InteractionParticipantCreate,
        InteractionUpdate,
    )

    assert set(InteractionUpdate.model_fields.keys()) == {"outcome", "next_follow_up_at"}

    for model in (InteractionUpdate, InteractionCreate, InteractionParticipantCreate):
        assert model.model_config.get("extra") == "forbid", (
            f"{model.__name__} does not forbid extra fields, so an unrecognised or immutable "
            "field sent by a caller would be silently discarded rather than refused"
        )


# --- Idempotency -----------------------------------------------------------------------------


def test_duplicate_external_message_id_replays_the_original() -> None:
    lead_ids: list[str] = []
    account_ids: list[str] = []
    opportunity_ids: list[str] = []
    interaction_ids: list[str] = []
    try:
        chain = create_account_linked_test_opportunity()
        lead_ids.append(str(chain["lead"]["public_id"]))
        account_ids.append(str(chain["account"]["public_id"]))
        opportunity_public_id = str(chain["opportunity"]["public_id"])
        opportunity_ids.append(opportunity_public_id)

        message_id = f"outlook-msg-{uuid4()}"
        payload = {
            "linked_record_type": "opportunity",
            "linked_record_public_id": opportunity_public_id,
            "channel_code": "EMAIL",
            "direction_code": "INBOUND",
            "occurred_at": _iso_now(),
            "external_system": "OUTLOOK",
            "external_message_id": message_id,
        }

        first = client.post("/api/interactions", headers=auth_headers("sales1"), json=payload)
        assert first.status_code == 201
        assert first.json()["replayed"] is False
        first_public_id = first.json()["interaction"]["public_id"]
        interaction_ids.append(first_public_id)

        # MCF-001 retry safety: a re-sync of the same provider message REPLAYS the original
        # record rather than erroring. An ingestion job whose call timed out after the row
        # committed must be able to retry without a 409 it would have to reconcile by hand.
        second = client.post("/api/interactions", headers=auth_headers("sales1"), json=payload)
        assert second.status_code == 201
        assert second.json()["replayed"] is True
        assert second.json()["interaction"]["public_id"] == first_public_id

        with SessionLocal() as db:
            count = db.execute(
                text("SELECT COUNT(*) FROM interaction WHERE external_message_id = :mid"),
                {"mid": message_id},
            ).scalar_one()
        assert count == 1, "the retry must not have created a second row"
    finally:
        _teardown_full_chain(
            interaction_public_ids=interaction_ids,
            work_order_public_ids=[],
            offer_public_ids=[],
            opportunity_public_ids=opportunity_ids,
            account_public_ids=account_ids,
            lead_public_ids=lead_ids,
        )


def test_duplicate_idempotency_key_replays_the_original() -> None:
    lead_ids: list[str] = []
    account_ids: list[str] = []
    opportunity_ids: list[str] = []
    interaction_ids: list[str] = []
    try:
        chain = create_account_linked_test_opportunity()
        lead_ids.append(str(chain["lead"]["public_id"]))
        account_ids.append(str(chain["account"]["public_id"]))
        opportunity_public_id = str(chain["opportunity"]["public_id"])
        opportunity_ids.append(opportunity_public_id)

        key = f"idem-{uuid4()}"
        payload = {
            "linked_record_type": "opportunity",
            "linked_record_public_id": opportunity_public_id,
            "channel_code": "WHATSAPP",
            "direction_code": "INBOUND",
            "occurred_at": _iso_now(),
            "idempotency_key": key,
        }

        first = client.post("/api/interactions", headers=auth_headers("sales1"), json=payload)
        assert first.status_code == 201
        assert first.json()["replayed"] is False
        first_public_id = first.json()["interaction"]["public_id"]
        interaction_ids.append(first_public_id)

        second = client.post("/api/interactions", headers=auth_headers("sales1"), json=payload)
        assert second.status_code == 201
        assert second.json()["replayed"] is True
        assert second.json()["interaction"]["public_id"] == first_public_id

        with SessionLocal() as db:
            count = db.execute(
                text("SELECT COUNT(*) FROM interaction WHERE idempotency_key = :key"),
                {"key": key},
            ).scalar_one()
        assert count == 1, "the retry must not have created a second row"
    finally:
        _teardown_full_chain(
            interaction_public_ids=interaction_ids,
            work_order_public_ids=[],
            offer_public_ids=[],
            opportunity_public_ids=opportunity_ids,
            account_public_ids=account_ids,
            lead_public_ids=lead_ids,
        )


# --- Inherited history: derived read, never a copy -------------------------------------------


def test_opportunity_inherits_interactions_from_its_source_lead() -> None:
    lead_ids: list[str] = []
    account_ids: list[str] = []
    opportunity_ids: list[str] = []
    interaction_ids: list[str] = []
    try:
        chain = create_account_linked_test_opportunity()
        lead_public_id = str(chain["lead"]["public_id"])
        lead_ids.append(lead_public_id)
        account_public_id = str(chain["account"]["public_id"])
        account_ids.append(account_public_id)
        opportunity_public_id = str(chain["opportunity"]["public_id"])
        opportunity_ids.append(opportunity_public_id)

        lead_interaction = client.post(
            "/api/interactions",
            headers=auth_headers("sales1"),
            json={
                "linked_record_type": "lead",
                "linked_record_public_id": lead_public_id,
                "channel_code": "CALL",
                "direction_code": "INBOUND",
                "occurred_at": _iso_now(),
                "subject": "Initial enquiry call",
            },
        )
        assert lead_interaction.status_code == 201
        interaction_ids.append(lead_interaction.json()["interaction"]["public_id"])

        # Without include_inherited: the Opportunity sees nothing recorded directly against it.
        without_inherited = client.get(
            "/api/interactions",
            headers=auth_headers("sales1"),
            params={
                "linked_record_type": "opportunity",
                "linked_record_public_id": opportunity_public_id,
            },
        )
        assert without_inherited.json() == []

        # With include_inherited: the Lead's interaction appears, marked with provenance.
        with_inherited = client.get(
            "/api/interactions",
            headers=auth_headers("sales1"),
            params={
                "linked_record_type": "opportunity",
                "linked_record_public_id": opportunity_public_id,
                "include_inherited": "true",
            },
        )
        assert with_inherited.status_code == 200
        rows = with_inherited.json()
        assert len(rows) == 1
        assert rows[0]["subject"] == "Initial enquiry call"
        assert rows[0]["inherited_from"] is not None
        assert rows[0]["inherited_from"]["record_type"] == "lead"
        assert rows[0]["inherited_from"]["public_id"] == lead_public_id

        # Same check for the Account, which inherits through the Opportunity's source Lead.
        account_inherited = client.get(
            "/api/interactions",
            headers=auth_headers("sales1"),
            params={
                "linked_record_type": "business_party",
                "linked_record_public_id": account_public_id,
                "include_inherited": "true",
            },
        )
        assert account_inherited.status_code == 200
        assert len(account_inherited.json()) == 1
        assert account_inherited.json()[0]["inherited_from"]["public_id"] == lead_public_id

        # Conversion writes no interaction rows: the total row count is exactly the one we
        # created directly against the Lead. This is what catches a future copy-on-convert
        # regression.
        with SessionLocal() as db:
            total = db.execute(
                text("SELECT COUNT(*) FROM interaction WHERE interaction_public_id = ANY(:ids)"),
                {"ids": interaction_ids},
            ).scalar_one()
        assert total == 1
    finally:
        _teardown_full_chain(
            interaction_public_ids=interaction_ids,
            work_order_public_ids=[],
            offer_public_ids=[],
            opportunity_public_ids=opportunity_ids,
            account_public_ids=account_ids,
            lead_public_ids=lead_ids,
        )


# --- Event payload must never carry restricted content ----------------------------------------


def test_the_recorded_event_payload_carries_no_message_content() -> None:
    lead_ids: list[str] = []
    account_ids: list[str] = []
    opportunity_ids: list[str] = []
    interaction_ids: list[str] = []
    try:
        chain = create_account_linked_test_opportunity()
        lead_ids.append(str(chain["lead"]["public_id"]))
        account_ids.append(str(chain["account"]["public_id"]))
        opportunity_public_id = str(chain["opportunity"]["public_id"])
        opportunity_ids.append(opportunity_public_id)

        marker_body = "PROBE-BODY-MARKER: customer bank details discussed here."
        marker_subject = "PROBE-SUBJECT-MARKER"
        marker_address = "probe-address-marker@example.com"

        response = client.post(
            "/api/interactions",
            headers=auth_headers("sales1"),
            json={
                "linked_record_type": "opportunity",
                "linked_record_public_id": opportunity_public_id,
                "channel_code": "EMAIL",
                "direction_code": "INBOUND",
                "occurred_at": _iso_now(),
                "subject": marker_subject,
                "body_text": marker_body,
                "participants": [
                    {"party_role_code": "FROM", "address_or_number": marker_address},
                ],
            },
        )
        assert response.status_code == 201
        interaction_ids.append(response.json()["interaction"]["public_id"])

        with SessionLocal() as db:
            payload_row = db.execute(
                text(
                    "SELECT event_payload_json FROM business_event "
                    "WHERE event_name = 'InteractionRecorded' "
                    "AND record_public_id = :public_id"
                ),
                {"public_id": response.json()["interaction"]["public_id"]},
            ).first()
        assert payload_row is not None
        payload_text = payload_row[0]
        assert marker_body not in payload_text
        assert marker_subject not in payload_text
        assert marker_address not in payload_text
    finally:
        _teardown_full_chain(
            interaction_public_ids=interaction_ids,
            work_order_public_ids=[],
            offer_public_ids=[],
            opportunity_public_ids=opportunity_ids,
            account_public_ids=account_ids,
            lead_public_ids=lead_ids,
        )


# --- Soft delete -----------------------------------------------------------------------------


def test_soft_deleted_interaction_is_hidden_but_not_removed() -> None:
    lead_ids: list[str] = []
    account_ids: list[str] = []
    opportunity_ids: list[str] = []
    interaction_ids: list[str] = []
    try:
        chain = create_account_linked_test_opportunity()
        lead_ids.append(str(chain["lead"]["public_id"]))
        account_ids.append(str(chain["account"]["public_id"]))
        opportunity_public_id = str(chain["opportunity"]["public_id"])
        opportunity_ids.append(opportunity_public_id)

        create_response = client.post(
            "/api/interactions",
            headers=auth_headers("sales1"),
            json={
                "linked_record_type": "opportunity",
                "linked_record_public_id": opportunity_public_id,
                "channel_code": "NOTE",
                "direction_code": "INTERNAL",
                "occurred_at": _iso_now(),
                "subject": "Recorded in error",
            },
        )
        interaction_public_id = create_response.json()["interaction"]["public_id"]
        interaction_ids.append(interaction_public_id)

        # INTERACTION_DELETE deliberately excludes SALES_USER - deleting a recorded
        # conversation removes evidence, so it is narrower than recording or correcting one.
        # manager1 is the seeded SALES_MANAGER user.
        delete_response = client.delete(
            f"/api/interactions/{interaction_public_id}",
            headers=auth_headers("manager1"),
        )
        assert delete_response.status_code == 200
        assert delete_response.json()["event"]["event_name"] == "InteractionDeleted"

        detail_after_delete = client.get(
            f"/api/interactions/{interaction_public_id}",
            headers=auth_headers("sales1"),
        )
        assert detail_after_delete.status_code == 404

        list_after_delete = client.get(
            "/api/interactions",
            headers=auth_headers("sales1"),
            params={
                "linked_record_type": "opportunity",
                "linked_record_public_id": opportunity_public_id,
            },
        )
        assert list_after_delete.json() == []

        with SessionLocal() as db:
            row = db.execute(
                text("SELECT is_deleted FROM interaction WHERE interaction_public_id = :public_id"),
                {"public_id": interaction_public_id},
            ).first()
        assert row is not None
        assert row[0] is True
    finally:
        _teardown_full_chain(
            interaction_public_ids=interaction_ids,
            work_order_public_ids=[],
            offer_public_ids=[],
            opportunity_public_ids=opportunity_ids,
            account_public_ids=account_ids,
            lead_public_ids=lead_ids,
        )


def test_readonly_role_cannot_delete() -> None:
    lead_ids: list[str] = []
    account_ids: list[str] = []
    opportunity_ids: list[str] = []
    interaction_ids: list[str] = []
    try:
        chain = create_account_linked_test_opportunity()
        lead_ids.append(str(chain["lead"]["public_id"]))
        account_ids.append(str(chain["account"]["public_id"]))
        opportunity_public_id = str(chain["opportunity"]["public_id"])
        opportunity_ids.append(opportunity_public_id)

        create_response = client.post(
            "/api/interactions",
            headers=auth_headers("sales1"),
            json={
                "linked_record_type": "opportunity",
                "linked_record_public_id": opportunity_public_id,
                "channel_code": "NOTE",
                "direction_code": "INTERNAL",
                "occurred_at": _iso_now(),
            },
        )
        interaction_public_id = create_response.json()["interaction"]["public_id"]
        interaction_ids.append(interaction_public_id)

        delete_response = client.delete(
            f"/api/interactions/{interaction_public_id}",
            headers=auth_headers("readonly1"),
        )
        assert delete_response.status_code == 403
    finally:
        _teardown_full_chain(
            interaction_public_ids=interaction_ids,
            work_order_public_ids=[],
            offer_public_ids=[],
            opportunity_public_ids=opportunity_ids,
            account_public_ids=account_ids,
            lead_public_ids=lead_ids,
        )


# --- Commercial Offer and Work Order as linked_record_type ------------------------------------


def test_interaction_can_be_recorded_against_a_commercial_offer_and_a_work_order() -> None:
    lead_ids: list[str] = []
    account_ids: list[str] = []
    opportunity_ids: list[str] = []
    offer_ids: list[str] = []
    work_order_ids: list[str] = []
    interaction_ids: list[str] = []
    try:
        chain = create_account_linked_test_opportunity()
        lead_ids.append(str(chain["lead"]["public_id"]))
        account_ids.append(str(chain["account"]["public_id"]))
        opportunity_public_id = str(chain["opportunity"]["public_id"])
        opportunity_ids.append(opportunity_public_id)

        offer = create_test_commercial_offer(opportunity_public_id)
        offer_public_id = str(offer["public_id"])
        offer_ids.append(offer_public_id)
        mark_test_commercial_offer_submitted(offer_public_id)
        record_test_customer_response(offer_public_id, "ACCEPTED_AWARDED", received_at=_iso_now())

        work_order = create_test_work_order(offer_public_id)
        work_order_public_id = str(work_order["public_id"])
        work_order_ids.append(work_order_public_id)

        offer_interaction = client.post(
            "/api/interactions",
            headers=auth_headers("sales1"),
            json={
                "linked_record_type": "commercial_offer",
                "linked_record_public_id": offer_public_id,
                "channel_code": "EMAIL",
                "direction_code": "OUTBOUND",
                "occurred_at": _iso_now(),
                "subject": "Offer sent",
            },
        )
        assert offer_interaction.status_code == 201
        interaction_ids.append(offer_interaction.json()["interaction"]["public_id"])

        work_order_interaction = client.post(
            "/api/interactions",
            headers=auth_headers("sales1"),
            json={
                "linked_record_type": "work_order",
                "linked_record_public_id": work_order_public_id,
                "channel_code": "SITE_VISIT",
                "direction_code": "OUTBOUND",
                "occurred_at": _iso_now(),
                "geo_latitude": "19.076000",
                "geo_longitude": "72.877700",
            },
        )
        assert work_order_interaction.status_code == 201
        interaction_ids.append(work_order_interaction.json()["interaction"]["public_id"])
        assert work_order_interaction.json()["interaction"]["geo_latitude"] == "19.076000"
    finally:
        _teardown_full_chain(
            interaction_public_ids=interaction_ids,
            work_order_public_ids=work_order_ids,
            offer_public_ids=offer_ids,
            opportunity_public_ids=opportunity_ids,
            account_public_ids=account_ids,
            lead_public_ids=lead_ids,
        )


# --- Correction pass 1: data-integrity and redaction findings from independent review ---------


def test_partial_update_does_not_wipe_the_field_it_did_not_mention() -> None:
    """Regression for a real data-loss defect: PUT {"outcome": ...} used to null
    next_follow_up_at, because both columns were written unconditionally from a schema whose
    fields both default to None. A scheduled follow-up the caller never mentioned vanished."""
    lead_ids: list[str] = []
    account_ids: list[str] = []
    opportunity_ids: list[str] = []
    interaction_ids: list[str] = []
    try:
        chain = create_account_linked_test_opportunity()
        lead_ids.append(str(chain["lead"]["public_id"]))
        account_ids.append(str(chain["account"]["public_id"]))
        opportunity_public_id = str(chain["opportunity"]["public_id"])
        opportunity_ids.append(opportunity_public_id)

        follow_up = "2026-10-01T09:30:00+00:00"
        created = client.post(
            "/api/interactions",
            headers=auth_headers("sales1"),
            json={
                "linked_record_type": "opportunity",
                "linked_record_public_id": opportunity_public_id,
                "channel_code": "CALL",
                "direction_code": "OUTBOUND",
                "occurred_at": _iso_now(),
                "outcome": "Original outcome.",
                "next_follow_up_at": follow_up,
            },
        )
        assert created.status_code == 201
        interaction_public_id = created.json()["interaction"]["public_id"]
        interaction_ids.append(interaction_public_id)
        assert created.json()["interaction"]["next_follow_up_at"] is not None

        # Mention only outcome. The follow-up must survive.
        updated = client.put(
            f"/api/interactions/{interaction_public_id}",
            headers=auth_headers("sales1"),
            json={"outcome": "Revised outcome."},
        )
        assert updated.status_code == 200
        body = updated.json()["interaction"]
        assert body["outcome"] == "Revised outcome."
        assert body["next_follow_up_at"] is not None, (
            "next_follow_up_at was wiped by a PUT that never mentioned it"
        )

        # Explicit null still clears it - "omitted" and "set to null" must stay distinguishable.
        cleared = client.put(
            f"/api/interactions/{interaction_public_id}",
            headers=auth_headers("sales1"),
            json={"next_follow_up_at": None},
        )
        assert cleared.status_code == 200
        assert cleared.json()["interaction"]["next_follow_up_at"] is None
        assert cleared.json()["interaction"]["outcome"] == "Revised outcome."
    finally:
        _teardown_full_chain(
            interaction_public_ids=interaction_ids,
            work_order_public_ids=[],
            offer_public_ids=[],
            opportunity_public_ids=opportunity_ids,
            account_public_ids=account_ids,
            lead_public_ids=lead_ids,
        )


def test_external_reference_fields_are_redacted_with_the_body() -> None:
    """Regression for a real leak: a caller denied body_text still received
    external_reference_url (a deep link straight to the message) and external_message_id (the
    provider key that retrieves it). Redaction defeated by a pointer rather than a copy."""
    lead_ids: list[str] = []
    account_ids: list[str] = []
    opportunity_ids: list[str] = []
    interaction_ids: list[str] = []
    try:
        chain = create_account_linked_test_opportunity()
        lead_ids.append(str(chain["lead"]["public_id"]))
        account_ids.append(str(chain["account"]["public_id"]))
        opportunity_public_id = str(chain["opportunity"]["public_id"])
        opportunity_ids.append(opportunity_public_id)

        reference_url = "https://outlook.example.invalid/message/probe-reference-marker"
        message_id = f"outlook-probe-{uuid4()}"
        created = client.post(
            "/api/interactions",
            headers=auth_headers("sales1"),
            json={
                "linked_record_type": "opportunity",
                "linked_record_public_id": opportunity_public_id,
                "channel_code": "EMAIL",
                "direction_code": "INBOUND",
                "occurred_at": _iso_now(),
                "body_text": "Confidential customer message.",
                "external_system": "OUTLOOK",
                "external_message_id": message_id,
                "external_reference_url": reference_url,
            },
        )
        assert created.status_code == 201
        interaction_public_id = created.json()["interaction"]["public_id"]
        interaction_ids.append(interaction_public_id)

        finance_detail = client.get(
            f"/api/interactions/{interaction_public_id}", headers=auth_headers("finance1")
        )
        finance_list = client.get(
            "/api/interactions",
            headers=auth_headers("finance1"),
            params={
                "linked_record_type": "opportunity",
                "linked_record_public_id": opportunity_public_id,
            },
        )

        for label, row in (
            ("detail", finance_detail.json()),
            ("list", finance_list.json()[0]),
        ):
            assert row["body_redacted"] is True
            assert row["body_text"] is None
            assert row["external_reference_url"] is None, (
                f"{label}: reference URL leaked past redaction"
            )
            assert row["external_message_id"] is None, (
                f"{label}: provider message id leaked past redaction"
            )
            # external_system stays visible: it names the channel, it does not address content.
            assert row["external_system"] == "OUTLOOK"

        # A content-permitted role still receives both.
        sales_detail = client.get(
            f"/api/interactions/{interaction_public_id}", headers=auth_headers("sales1")
        )
        assert sales_detail.json()["external_reference_url"] == reference_url
        assert sales_detail.json()["external_message_id"] == message_id
    finally:
        _teardown_full_chain(
            interaction_public_ids=interaction_ids,
            work_order_public_ids=[],
            offer_public_ids=[],
            opportunity_public_ids=opportunity_ids,
            account_public_ids=account_ids,
            lead_public_ids=lead_ids,
        )


def test_coordinates_must_be_paired_and_within_range() -> None:
    lead_ids: list[str] = []
    account_ids: list[str] = []
    opportunity_ids: list[str] = []
    try:
        chain = create_account_linked_test_opportunity()
        lead_ids.append(str(chain["lead"]["public_id"]))
        account_ids.append(str(chain["account"]["public_id"]))
        opportunity_public_id = str(chain["opportunity"]["public_id"])
        opportunity_ids.append(opportunity_public_id)

        def post(extra: dict) -> int:
            return client.post(
                "/api/interactions",
                headers=auth_headers("sales1"),
                json={
                    "linked_record_type": "opportunity",
                    "linked_record_public_id": opportunity_public_id,
                    "channel_code": "SITE_VISIT",
                    "direction_code": "OUTBOUND",
                    "occurred_at": _iso_now(),
                    **extra,
                },
            ).status_code

        assert post({"geo_latitude": "19.076000"}) == 422, "a lone latitude is not a location"
        assert post({"geo_longitude": "72.877700"}) == 422, "a lone longitude is not a location"
        assert post({"geo_latitude": "91.000000", "geo_longitude": "0.000000"}) == 422
        assert post({"geo_latitude": "-91.000000", "geo_longitude": "0.000000"}) == 422
        assert post({"geo_latitude": "0.000000", "geo_longitude": "181.000000"}) == 422
        assert post({"geo_latitude": "0.000000", "geo_longitude": "-181.000000"}) == 422
    finally:
        _teardown_full_chain(
            interaction_public_ids=[],
            work_order_public_ids=[],
            offer_public_ids=[],
            opportunity_public_ids=opportunity_ids,
            account_public_ids=account_ids,
            lead_public_ids=lead_ids,
        )


def test_participant_references_must_resolve_and_must_identify_someone() -> None:
    lead_ids: list[str] = []
    account_ids: list[str] = []
    opportunity_ids: list[str] = []
    interaction_ids: list[str] = []
    try:
        chain = create_account_linked_test_opportunity()
        lead_ids.append(str(chain["lead"]["public_id"]))
        account_ids.append(str(chain["account"]["public_id"]))
        opportunity_public_id = str(chain["opportunity"]["public_id"])
        opportunity_ids.append(opportunity_public_id)

        def post(participant: dict):
            return client.post(
                "/api/interactions",
                headers=auth_headers("sales1"),
                json={
                    "linked_record_type": "opportunity",
                    "linked_record_public_id": opportunity_public_id,
                    "channel_code": "EMAIL",
                    "direction_code": "INBOUND",
                    "occurred_at": _iso_now(),
                    "participants": [participant],
                },
            )

        # Names nobody at all.
        assert post({"party_role_code": "FROM"}).status_code == 422

        # Well-formed but unresolvable references.
        assert post({"party_role_code": "FROM", "contact_public_id": str(uuid4())}).status_code == 422
        assert post({"party_role_code": "FROM", "app_user_public_id": str(uuid4())}).status_code == 422

        # An external person with no system identity at all remains valid - that is the case the
        # nullable, non-foreign-key columns exist to support.
        accepted = post({"party_role_code": "FROM", "display_name": "External person"})
        assert accepted.status_code == 201
        interaction_ids.append(accepted.json()["interaction"]["public_id"])
    finally:
        _teardown_full_chain(
            interaction_public_ids=interaction_ids,
            work_order_public_ids=[],
            offer_public_ids=[],
            opportunity_public_ids=opportunity_ids,
            account_public_ids=account_ids,
            lead_public_ids=lead_ids,
        )


# --- Correction pass 1: MCF-001 conventions ---------------------------------------------------


def test_correlation_id_is_honoured_when_supplied_and_generated_when_not() -> None:
    """MCF-001 correlation. A caller-supplied chain is carried onto the business event; when the
    caller supplies none, one is generated so a correlation reference always exists."""
    lead_ids: list[str] = []
    account_ids: list[str] = []
    opportunity_ids: list[str] = []
    interaction_ids: list[str] = []
    try:
        chain = create_account_linked_test_opportunity()
        lead_ids.append(str(chain["lead"]["public_id"]))
        account_ids.append(str(chain["account"]["public_id"]))
        opportunity_public_id = str(chain["opportunity"]["public_id"])
        opportunity_ids.append(opportunity_public_id)

        supplied = f"probe-correlation-{uuid4()}"
        body = {
            "linked_record_type": "opportunity",
            "linked_record_public_id": opportunity_public_id,
            "channel_code": "CALL",
            "direction_code": "OUTBOUND",
            "occurred_at": _iso_now(),
        }

        with_header = client.post(
            "/api/interactions",
            headers={**auth_headers("sales1"), "X-Correlation-Id": supplied},
            json=body,
        )
        assert with_header.status_code == 201
        assert with_header.json()["correlation_id"] == supplied
        with_header_id = with_header.json()["interaction"]["public_id"]
        interaction_ids.append(with_header_id)

        without_header = client.post("/api/interactions", headers=auth_headers("sales1"), json=body)
        assert without_header.status_code == 201
        generated = without_header.json()["correlation_id"]
        assert generated, "a correlation id must always be present, supplied or generated"
        assert generated != supplied
        interaction_ids.append(without_header.json()["interaction"]["public_id"])

        # The supplied value reached the durable business event, not just the response.
        with SessionLocal() as db:
            stored = db.execute(
                text(
                    "SELECT correlation_id FROM business_event "
                    "WHERE event_name = 'InteractionRecorded' AND record_public_id = :public_id"
                ),
                {"public_id": with_header_id},
            ).scalar_one()
        assert stored == supplied
    finally:
        _teardown_full_chain(
            interaction_public_ids=interaction_ids,
            work_order_public_ids=[],
            offer_public_ids=[],
            opportunity_public_ids=opportunity_ids,
            account_public_ids=account_ids,
            lead_public_ids=lead_ids,
        )


def test_responses_carry_the_contract_version_and_events_carry_a_schema_version() -> None:
    """MCF-001 "explicit contract/schema version". A consumer reads the version rather than
    inferring compatibility from which fields happen to be present."""
    from app.modules.interactions.contract import (
        INTERACTION_CONTRACT_VERSION,
        INTERACTION_EVENT_SCHEMA_VERSION,
    )

    lead_ids: list[str] = []
    account_ids: list[str] = []
    opportunity_ids: list[str] = []
    interaction_ids: list[str] = []
    try:
        chain = create_account_linked_test_opportunity()
        lead_ids.append(str(chain["lead"]["public_id"]))
        account_ids.append(str(chain["account"]["public_id"]))
        opportunity_public_id = str(chain["opportunity"]["public_id"])
        opportunity_ids.append(opportunity_public_id)

        created = client.post(
            "/api/interactions",
            headers=auth_headers("sales1"),
            json={
                "linked_record_type": "opportunity",
                "linked_record_public_id": opportunity_public_id,
                "channel_code": "NOTE",
                "direction_code": "INTERNAL",
                "occurred_at": _iso_now(),
            },
        )
        assert created.status_code == 201
        assert created.json()["contract_version"] == INTERACTION_CONTRACT_VERSION
        interaction_public_id = created.json()["interaction"]["public_id"]
        interaction_ids.append(interaction_public_id)

        updated = client.put(
            f"/api/interactions/{interaction_public_id}",
            headers=auth_headers("sales1"),
            json={"outcome": "Noted."},
        )
        assert updated.json()["contract_version"] == INTERACTION_CONTRACT_VERSION

        with SessionLocal() as db:
            payload_text = db.execute(
                text(
                    "SELECT event_payload_json FROM business_event "
                    "WHERE event_name = 'InteractionRecorded' AND record_public_id = :public_id"
                ),
                {"public_id": interaction_public_id},
            ).scalar_one()
        assert f'"schema_version": "{INTERACTION_EVENT_SCHEMA_VERSION}"' in payload_text.replace(
            '"schema_version":"', '"schema_version": "'
        )
    finally:
        _teardown_full_chain(
            interaction_public_ids=interaction_ids,
            work_order_public_ids=[],
            offer_public_ids=[],
            opportunity_public_ids=opportunity_ids,
            account_public_ids=account_ids,
            lead_public_ids=lead_ids,
        )


def test_a_replayed_retry_emits_no_second_business_event() -> None:
    """A replay must not look like a second business fact. MCF-001: a retry does not create a
    duplicate business effect - and an event is a business effect."""
    lead_ids: list[str] = []
    account_ids: list[str] = []
    opportunity_ids: list[str] = []
    interaction_ids: list[str] = []
    try:
        chain = create_account_linked_test_opportunity()
        lead_ids.append(str(chain["lead"]["public_id"]))
        account_ids.append(str(chain["account"]["public_id"]))
        opportunity_public_id = str(chain["opportunity"]["public_id"])
        opportunity_ids.append(opportunity_public_id)

        payload = {
            "linked_record_type": "opportunity",
            "linked_record_public_id": opportunity_public_id,
            "channel_code": "EMAIL",
            "direction_code": "INBOUND",
            "occurred_at": _iso_now(),
            "idempotency_key": f"probe-replay-{uuid4()}",
        }

        first = client.post("/api/interactions", headers=auth_headers("sales1"), json=payload)
        assert first.status_code == 201
        interaction_public_id = first.json()["interaction"]["public_id"]
        interaction_ids.append(interaction_public_id)

        for _ in range(3):
            retry = client.post("/api/interactions", headers=auth_headers("sales1"), json=payload)
            assert retry.status_code == 201
            assert retry.json()["replayed"] is True

        with SessionLocal() as db:
            event_count = db.execute(
                text(
                    "SELECT COUNT(*) FROM business_event "
                    "WHERE event_name = 'InteractionRecorded' AND record_public_id = :public_id"
                ),
                {"public_id": interaction_public_id},
            ).scalar_one()
        assert event_count == 1, "each replay emitted a duplicate business event"
    finally:
        _teardown_full_chain(
            interaction_public_ids=interaction_ids,
            work_order_public_ids=[],
            offer_public_ids=[],
            opportunity_public_ids=opportunity_ids,
            account_public_ids=account_ids,
            lead_public_ids=lead_ids,
        )


# --- Correction pass 2: immutable fields must be refused, not silently ignored ----------------


def test_update_refuses_an_immutable_field_and_changes_nothing() -> None:
    """Regression for a P1: InteractionUpdate used Pydantic's default extra="ignore", so a PUT
    carrying body_text returned 200, silently discarded the attempted replacement, applied any
    other supplied field, and still emitted an InteractionUpdated event - a false audit record
    of a change that never happened.

    INT-001 claims immutability is structural. This test is what makes that claim true.
    """
    lead_ids: list[str] = []
    account_ids: list[str] = []
    opportunity_ids: list[str] = []
    interaction_ids: list[str] = []
    try:
        chain = create_account_linked_test_opportunity()
        lead_ids.append(str(chain["lead"]["public_id"]))
        account_ids.append(str(chain["account"]["public_id"]))
        opportunity_public_id = str(chain["opportunity"]["public_id"])
        opportunity_ids.append(opportunity_public_id)

        original_body = "Original body that must survive."
        created = client.post(
            "/api/interactions",
            headers=auth_headers("sales1"),
            json={
                "linked_record_type": "opportunity",
                "linked_record_public_id": opportunity_public_id,
                "channel_code": "CALL",
                "direction_code": "OUTBOUND",
                "occurred_at": _iso_now(),
                "subject": "Original subject",
                "body_text": original_body,
                "outcome": "Original outcome.",
            },
        )
        assert created.status_code == 201
        interaction_public_id = created.json()["interaction"]["public_id"]
        interaction_ids.append(interaction_public_id)

        def event_count() -> int:
            with SessionLocal() as db:
                return db.execute(
                    text(
                        "SELECT COUNT(*) FROM business_event "
                        "WHERE event_name = 'InteractionUpdated' AND record_public_id = :public_id"
                    ),
                    {"public_id": interaction_public_id},
                ).scalar_one()

        events_before = event_count()

        # Every immutable field, each rejected on its own.
        for field, value in (
            ("body_text", "Replacement body."),
            ("subject", "Replacement subject"),
            ("channel_code", "EMAIL"),
            ("direction_code", "INBOUND"),
            ("occurred_at", _iso_now()),
            ("external_message_id", "replacement-message-id"),
            ("linked_record_type", "lead"),
            ("participants", []),
            ("not_a_field_at_all", "x"),
        ):
            response = client.put(
                f"/api/interactions/{interaction_public_id}",
                headers=auth_headers("sales1"),
                json={field: value},
            )
            assert response.status_code == 422, (
                f"PUT carrying immutable/unknown field {field!r} was not refused"
            )

        # Mixed request: an allowed field alongside an immutable one must be refused whole,
        # never partially applied.
        mixed = client.put(
            f"/api/interactions/{interaction_public_id}",
            headers=auth_headers("sales1"),
            json={"outcome": "Should not be applied.", "body_text": "Replacement body."},
        )
        assert mixed.status_code == 422

        # The row is untouched: body preserved, and the allowed field from the mixed request
        # was not applied either.
        current = client.get(
            f"/api/interactions/{interaction_public_id}", headers=auth_headers("sales1")
        ).json()
        assert current["body_text"] == original_body
        assert current["subject"] == "Original subject"
        assert current["outcome"] == "Original outcome."
        assert current["channel_code"] == "CALL"
        assert current["direction_code"] == "OUTBOUND"

        # No InteractionUpdated event was emitted by any refused request.
        assert event_count() == events_before, (
            "a refused update emitted an InteractionUpdated event"
        )

        # A legitimate update still works, so the guard refuses the wrong thing only.
        allowed = client.put(
            f"/api/interactions/{interaction_public_id}",
            headers=auth_headers("sales1"),
            json={"outcome": "Legitimately revised."},
        )
        assert allowed.status_code == 200
        assert allowed.json()["interaction"]["outcome"] == "Legitimately revised."
        assert allowed.json()["interaction"]["body_text"] == original_body
        assert event_count() == events_before + 1
    finally:
        _teardown_full_chain(
            interaction_public_ids=interaction_ids,
            work_order_public_ids=[],
            offer_public_ids=[],
            opportunity_public_ids=opportunity_ids,
            account_public_ids=account_ids,
            lead_public_ids=lead_ids,
        )


# --- Correction pass 2: idempotency scope, DB coordinate integrity, participant identity ------


def _post_interaction(opportunity_public_id: str, **overrides):
    body = {
        "linked_record_type": "opportunity",
        "linked_record_public_id": opportunity_public_id,
        "channel_code": "EMAIL",
        "direction_code": "INBOUND",
        "occurred_at": "2026-09-01T10:00:00+00:00",
        "subject": "Original command",
    }
    body.update(overrides)
    return client.post("/api/interactions", headers=auth_headers("sales1"), json=body)


def test_replay_is_refused_when_the_key_is_reused_for_a_different_command() -> None:
    """Regression for a P1: the service returned whichever row owned the key without comparing
    the retry against the original command. A caller reusing a key with a different subject
    received the ORIGINAL record reported as their own successful create."""
    lead_ids: list[str] = []
    account_ids: list[str] = []
    opportunity_ids: list[str] = []
    interaction_ids: list[str] = []
    try:
        chain = create_account_linked_test_opportunity()
        lead_ids.append(str(chain["lead"]["public_id"]))
        account_ids.append(str(chain["account"]["public_id"]))
        opportunity_public_id = str(chain["opportunity"]["public_id"])
        opportunity_ids.append(opportunity_public_id)

        key = f"probe-scope-{uuid4()}"

        first = _post_interaction(opportunity_public_id, idempotency_key=key)
        assert first.status_code == 201
        assert first.json()["replayed"] is False
        first_public_id = first.json()["interaction"]["public_id"]
        interaction_ids.append(first_public_id)

        # Identical command: replays.
        identical = _post_interaction(opportunity_public_id, idempotency_key=key)
        assert identical.status_code == 201
        assert identical.json()["replayed"] is True
        assert identical.json()["interaction"]["public_id"] == first_public_id

        # Same key, different command: refused, and the original is NOT handed back.
        for changed in (
            {"subject": "Different command using the same key"},
            {"body_text": "A body the original did not have"},
            {"channel_code": "CALL"},
            {"direction_code": "OUTBOUND"},
            {"occurred_at": "2026-09-02T10:00:00+00:00"},
            {"outcome": "A different outcome"},
        ):
            conflicting = _post_interaction(opportunity_public_id, idempotency_key=key, **changed)
            assert conflicting.status_code == 409, (
                f"key reuse with changed {sorted(changed)} was not refused"
            )
            assert "already been used for a different command" in conflicting.json()["detail"]

        # Still exactly one row for that key.
        with SessionLocal() as db:
            count = db.execute(
                text("SELECT COUNT(*) FROM interaction WHERE idempotency_key = :key"),
                {"key": key},
            ).scalar_one()
        assert count == 1
    finally:
        _teardown_full_chain(
            interaction_public_ids=interaction_ids,
            work_order_public_ids=[],
            offer_public_ids=[],
            opportunity_public_ids=opportunity_ids,
            account_public_ids=account_ids,
            lead_public_ids=lead_ids,
        )


def test_replay_is_refused_when_the_key_is_reused_against_a_different_record() -> None:
    """Scope: the same key against a different linked record is a different command, because
    linked_record_public_id is part of the fingerprint."""
    lead_ids: list[str] = []
    account_ids: list[str] = []
    opportunity_ids: list[str] = []
    interaction_ids: list[str] = []
    try:
        first_chain = create_account_linked_test_opportunity()
        lead_ids.append(str(first_chain["lead"]["public_id"]))
        account_ids.append(str(first_chain["account"]["public_id"]))
        first_opportunity = str(first_chain["opportunity"]["public_id"])
        opportunity_ids.append(first_opportunity)

        second_chain = create_account_linked_test_opportunity()
        lead_ids.append(str(second_chain["lead"]["public_id"]))
        account_ids.append(str(second_chain["account"]["public_id"]))
        second_opportunity = str(second_chain["opportunity"]["public_id"])
        opportunity_ids.append(second_opportunity)

        key = f"probe-crossrecord-{uuid4()}"

        first = _post_interaction(first_opportunity, idempotency_key=key)
        assert first.status_code == 201
        interaction_ids.append(first.json()["interaction"]["public_id"])

        crossed = _post_interaction(second_opportunity, idempotency_key=key)
        assert crossed.status_code == 409, (
            "the same key against a different Opportunity was accepted, so one record's key "
            "could return another record's conversation"
        )
    finally:
        _teardown_full_chain(
            interaction_public_ids=interaction_ids,
            work_order_public_ids=[],
            offer_public_ids=[],
            opportunity_public_ids=opportunity_ids,
            account_public_ids=account_ids,
            lead_public_ids=lead_ids,
        )


def test_replay_of_a_soft_deleted_original_is_refused_not_resurrected() -> None:
    """A retry whose original was deleted must not receive deleted content reported as an
    active record, and must not silently recreate the conversation somebody removed."""
    lead_ids: list[str] = []
    account_ids: list[str] = []
    opportunity_ids: list[str] = []
    interaction_ids: list[str] = []
    try:
        chain = create_account_linked_test_opportunity()
        lead_ids.append(str(chain["lead"]["public_id"]))
        account_ids.append(str(chain["account"]["public_id"]))
        opportunity_public_id = str(chain["opportunity"]["public_id"])
        opportunity_ids.append(opportunity_public_id)

        key = f"probe-deleted-{uuid4()}"
        first = _post_interaction(
            opportunity_public_id, idempotency_key=key, body_text="Content that was removed."
        )
        assert first.status_code == 201
        interaction_public_id = first.json()["interaction"]["public_id"]
        interaction_ids.append(interaction_public_id)

        deleted = client.delete(
            f"/api/interactions/{interaction_public_id}", headers=auth_headers("manager1")
        )
        assert deleted.status_code == 200

        retry = _post_interaction(
            opportunity_public_id, idempotency_key=key, body_text="Content that was removed."
        )
        assert retry.status_code == 409
        assert "has since been deleted" in retry.json()["detail"]
        # The refusal must not leak the deleted content back to the caller.
        assert "Content that was removed." not in retry.text

        # And nothing was resurrected or duplicated.
        with SessionLocal() as db:
            rows = db.execute(
                text("SELECT is_deleted FROM interaction WHERE idempotency_key = :key"),
                {"key": key},
            ).fetchall()
        assert len(rows) == 1
        assert rows[0][0] is True
    finally:
        _teardown_full_chain(
            interaction_public_ids=interaction_ids,
            work_order_public_ids=[],
            offer_public_ids=[],
            opportunity_public_ids=opportunity_ids,
            account_public_ids=account_ids,
            lead_public_ids=lead_ids,
        )


def test_the_database_itself_rejects_impossible_coordinates() -> None:
    """API validation protects the HTTP path and nothing else. A direct insert with
    latitude 999 succeeded during review; these CHECK constraints are what actually stop it,
    and they must be proved at the database, not through the API that already validates."""
    from sqlalchemy.exc import IntegrityError

    lead_ids: list[str] = []
    account_ids: list[str] = []
    opportunity_ids: list[str] = []
    try:
        chain = create_account_linked_test_opportunity()
        lead_ids.append(str(chain["lead"]["public_id"]))
        account_ids.append(str(chain["account"]["public_id"]))
        opportunity_public_id = str(chain["opportunity"]["public_id"])
        opportunity_ids.append(opportunity_public_id)

        def direct_insert(latitude, longitude) -> None:
            with SessionLocal() as db:
                db.execute(
                    text(
                        """
                        INSERT INTO interaction (
                            interaction_public_id, linked_record_type, linked_record_public_id,
                            channel_code, direction_code, occurred_at,
                            geo_latitude, geo_longitude, created_at, updated_at
                        ) VALUES (
                            :public_id, 'opportunity', :linked, 'SITE_VISIT', 'OUTBOUND',
                            CURRENT_TIMESTAMP, :lat, :lon, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                        )
                        """
                    ),
                    {
                        "public_id": str(uuid4()),
                        "linked": opportunity_public_id,
                        "lat": latitude,
                        "lon": longitude,
                    },
                )
                db.commit()

        for latitude, longitude, label in (
            (999, -999, "far out of range"),
            (91, 0, "latitude just above 90"),
            (-91, 0, "latitude just below -90"),
            (0, 181, "longitude just above 180"),
            (0, -181, "longitude just below -180"),
            (19.076, None, "latitude without longitude"),
            (None, 72.8777, "longitude without latitude"),
        ):
            try:
                direct_insert(latitude, longitude)
            except IntegrityError:
                continue
            raise AssertionError(
                f"the database accepted a direct insert with {label} "
                f"(lat={latitude}, lon={longitude})"
            )

        # A legitimate pair is still accepted, so the constraints reject only what they should.
        direct_insert(19.076000, 72.877700)
        with SessionLocal() as db:
            db.execute(
                text(
                    "DELETE FROM interaction WHERE linked_record_public_id = :linked "
                    "AND channel_code = 'SITE_VISIT'"
                ),
                {"linked": opportunity_public_id},
            )
            db.commit()
    finally:
        _teardown_full_chain(
            interaction_public_ids=[],
            work_order_public_ids=[],
            offer_public_ids=[],
            opportunity_public_ids=opportunity_ids,
            account_public_ids=account_ids,
            lead_public_ids=lead_ids,
        )


def test_a_participant_may_not_be_both_an_account_contact_and_a_pbl_user() -> None:
    """Decided in correction pass 2: the two identifiers address different populations - a
    person at the customer's Account, and a PBL staff login. One participant is one of them.
    Two people on a conversation are two participant rows."""
    lead_ids: list[str] = []
    account_ids: list[str] = []
    opportunity_ids: list[str] = []
    interaction_ids: list[str] = []
    try:
        chain = create_account_linked_test_opportunity()
        lead_ids.append(str(chain["lead"]["public_id"]))
        account_ids.append(str(chain["account"]["public_id"]))
        account_public_id = str(chain["account"]["public_id"])
        opportunity_public_id = str(chain["opportunity"]["public_id"])
        opportunity_ids.append(opportunity_public_id)

        contact = client.post(
            f"/api/accounts/{account_public_id}/contacts",
            headers=auth_headers("sales1"),
            json={"contact_name": "Customer Contact"},
        )
        assert contact.status_code == 201
        contact_public_id = contact.json()["contact"]["public_id"]

        with SessionLocal() as db:
            app_user_public_id = db.execute(
                text("SELECT public_id FROM app_user WHERE lower(username) = 'sales1'")
            ).scalar_one()

        both = _post_interaction(
            opportunity_public_id,
            participants=[
                {
                    "party_role_code": "FROM",
                    "contact_public_id": contact_public_id,
                    "app_user_public_id": str(app_user_public_id),
                }
            ],
        )
        assert both.status_code == 422
        assert "not both" in both.json()["detail"] or "not both" in both.text

        # Either one alone is accepted, and both people together are two rows.
        two_rows = _post_interaction(
            opportunity_public_id,
            idempotency_key=f"probe-two-participants-{uuid4()}",
            participants=[
                {"party_role_code": "FROM", "contact_public_id": contact_public_id},
                {"party_role_code": "TO", "app_user_public_id": str(app_user_public_id)},
            ],
        )
        assert two_rows.status_code == 201
        interaction_ids.append(two_rows.json()["interaction"]["public_id"])
        assert len(two_rows.json()["interaction"]["participants"]) == 2
    finally:
        _teardown_full_chain(
            interaction_public_ids=interaction_ids,
            work_order_public_ids=[],
            offer_public_ids=[],
            opportunity_public_ids=opportunity_ids,
            account_public_ids=account_ids,
            lead_public_ids=lead_ids,
        )


# --- Correction pass 3: the fingerprint must be an unambiguous encoding -----------------------


def _fingerprint_of(**overrides):
    """Build an InteractionCreate and return its fingerprint, without touching the database."""
    from app.modules.interactions.schemas import InteractionCreate
    from app.modules.interactions.service import compute_request_fingerprint

    body = {
        "linked_record_type": "opportunity",
        "linked_record_public_id": "22222222-2222-2222-2222-222222222222",
        "channel_code": "EMAIL",
        "direction_code": "INBOUND",
        "occurred_at": "2026-09-01T10:00:00+00:00",
    }
    body.update(overrides)
    return compute_request_fingerprint(InteractionCreate(**body))


def test_delimiter_injection_cannot_forge_a_matching_fingerprint() -> None:
    """The exact collision found in review. The first implementation joined `name=value` pairs
    with U+001F, which is not an injective encoding: a value containing the delimiter forges a
    field boundary. These two genuinely different commands produced identical bytes, so a retry
    could replay an incompatible command despite the comparison being present."""
    unit_separator = "\x1f"

    first = _fingerprint_of(subject="u", body_text=f"v{unit_separator}body_text=")
    second = _fingerprint_of(subject=f"u{unit_separator}body_text=v", body_text="")

    assert first != second, (
        "two different commands produced the same fingerprint - the encoding is ambiguous again"
    )

    # A few more shapes in the same family, so the property is tested rather than the one example.
    for a, b in (
        ({"subject": "a", "body_text": "b"}, {"subject": "a\x1fbody_text=b", "body_text": None}),
        ({"subject": '"', "body_text": "x"}, {"subject": "", "body_text": '"x'}),
        ({"subject": "x", "body_text": None}, {"subject": "x", "body_text": ""}),
        ({"outcome": "a,b"}, {"outcome": "a", "subject": "b"}),
    ):
        assert _fingerprint_of(**a) != _fingerprint_of(**b), f"collision between {a} and {b}"


def test_external_message_id_is_part_of_command_identity() -> None:
    """Excluding it let a retry change which provider message a record claimed to be while
    still matching the stored fingerprint."""
    base = {"external_system": "OUTLOOK", "external_message_id": "msg-one"}
    changed = {"external_system": "OUTLOOK", "external_message_id": "msg-two"}
    assert _fingerprint_of(**base) != _fingerprint_of(**changed)


def test_idempotency_key_is_not_part_of_command_identity() -> None:
    """The key identifies the request; it is not part of what the command says."""
    assert _fingerprint_of(idempotency_key="k1") == _fingerprint_of(idempotency_key="k2")
    assert _fingerprint_of(idempotency_key="k1") == _fingerprint_of()


def test_omitted_external_system_matches_explicit_manual() -> None:
    """The service stores MANUAL either way, so the two are the same command and a retry that
    spells the default out must still replay rather than 409."""
    assert _fingerprint_of() == _fingerprint_of(external_system="MANUAL")


def test_equivalent_timezone_offsets_are_the_same_command() -> None:
    """The same instant written in two offsets is one command."""
    utc = _fingerprint_of(occurred_at="2026-09-01T10:00:00+00:00")
    ist = _fingerprint_of(occurred_at="2026-09-01T15:30:00+05:30")
    assert utc == ist

    different_instant = _fingerprint_of(occurred_at="2026-09-01T11:00:00+00:00")
    assert utc != different_instant


def test_decimal_trailing_zeros_do_not_change_command_identity() -> None:
    assert _fingerprint_of(geo_latitude="19.076", geo_longitude="72.8777") == _fingerprint_of(
        geo_latitude="19.076000", geo_longitude="72.877700"
    )


def test_participant_order_does_not_change_command_identity() -> None:
    one = [
        {"party_role_code": "FROM", "display_name": "Alice"},
        {"party_role_code": "TO", "display_name": "Bob"},
    ]
    other = [
        {"party_role_code": "TO", "display_name": "Bob"},
        {"party_role_code": "FROM", "display_name": "Alice"},
    ]
    assert _fingerprint_of(participants=one) == _fingerprint_of(participants=other)

    # But a genuinely different participant set is a different command.
    changed = [
        {"party_role_code": "FROM", "display_name": "Alice"},
        {"party_role_code": "TO", "display_name": "Carol"},
    ]
    assert _fingerprint_of(participants=one) != _fingerprint_of(participants=changed)


def test_the_fingerprint_covers_every_declared_field() -> None:
    """Guard against a field being added to the command but forgotten in the fingerprint: every
    name in INTERACTION_FINGERPRINT_FIELDS must actually change the result."""
    from app.modules.interactions.contract import INTERACTION_FINGERPRINT_FIELDS

    probes = {
        "linked_record_type": "lead",
        "linked_record_public_id": "33333333-3333-3333-3333-333333333333",
        "channel_code": "CALL",
        "direction_code": "OUTBOUND",
        "occurred_at": "2026-09-05T10:00:00+00:00",
        "subject": "probe",
        "body_text": "probe",
        "external_system": "OUTLOOK",
        "external_message_id": "probe",
        "external_reference_url": "https://example.invalid/probe",
        "geo_latitude": "1.5",
        "geo_longitude": "2.5",
        "outcome": "probe",
        "next_follow_up_at": "2026-10-05T10:00:00+00:00",
    }
    assert set(probes) == set(INTERACTION_FINGERPRINT_FIELDS), (
        "this test's probe set has drifted from the declared fingerprint field list"
    )

    baseline = _fingerprint_of()
    for field, value in probes.items():
        if field in ("geo_latitude", "geo_longitude"):
            # Coordinates must be supplied as a pair, so probe them together.
            continue
        assert _fingerprint_of(**{field: value}) != baseline, (
            f"changing {field} did not change the fingerprint"
        )
    assert _fingerprint_of(geo_latitude="1.5", geo_longitude="2.5") != baseline


def test_replay_is_refused_when_only_the_external_message_id_changes() -> None:
    """The API-level proof of the identity fix: same key, different provider message, refused."""
    lead_ids: list[str] = []
    account_ids: list[str] = []
    opportunity_ids: list[str] = []
    interaction_ids: list[str] = []
    try:
        chain = create_account_linked_test_opportunity()
        lead_ids.append(str(chain["lead"]["public_id"]))
        account_ids.append(str(chain["account"]["public_id"]))
        opportunity_public_id = str(chain["opportunity"]["public_id"])
        opportunity_ids.append(opportunity_public_id)

        key = f"probe-msgid-{uuid4()}"
        first = _post_interaction(
            opportunity_public_id,
            idempotency_key=key,
            external_system="OUTLOOK",
            external_message_id=f"msg-one-{uuid4()}",
        )
        assert first.status_code == 201
        interaction_ids.append(first.json()["interaction"]["public_id"])

        changed = _post_interaction(
            opportunity_public_id,
            idempotency_key=key,
            external_system="OUTLOOK",
            external_message_id=f"msg-two-{uuid4()}",
        )
        assert changed.status_code == 409, (
            "reusing an idempotency key with a different provider message identity was accepted"
        )
    finally:
        _teardown_full_chain(
            interaction_public_ids=interaction_ids,
            work_order_public_ids=[],
            offer_public_ids=[],
            opportunity_public_ids=opportunity_ids,
            account_public_ids=account_ids,
            lead_public_ids=lead_ids,
        )


def test_equivalent_offsets_and_reordered_participants_still_replay_over_the_api() -> None:
    """The permissive half, proved end to end: a retry that is the same command written
    differently must still replay, not 409."""
    lead_ids: list[str] = []
    account_ids: list[str] = []
    opportunity_ids: list[str] = []
    interaction_ids: list[str] = []
    try:
        chain = create_account_linked_test_opportunity()
        lead_ids.append(str(chain["lead"]["public_id"]))
        account_ids.append(str(chain["account"]["public_id"]))
        opportunity_public_id = str(chain["opportunity"]["public_id"])
        opportunity_ids.append(opportunity_public_id)

        key = f"probe-equivalent-{uuid4()}"
        participants_one = [
            {"party_role_code": "FROM", "display_name": "Alice"},
            {"party_role_code": "TO", "display_name": "Bob"},
        ]
        participants_reordered = [
            {"party_role_code": "TO", "display_name": "Bob"},
            {"party_role_code": "FROM", "display_name": "Alice"},
        ]

        first = _post_interaction(
            opportunity_public_id,
            idempotency_key=key,
            occurred_at="2026-09-01T10:00:00+00:00",
            participants=participants_one,
        )
        assert first.status_code == 201
        first_public_id = first.json()["interaction"]["public_id"]
        interaction_ids.append(first_public_id)

        equivalent = _post_interaction(
            opportunity_public_id,
            idempotency_key=key,
            occurred_at="2026-09-01T15:30:00+05:30",   # same instant, different offset
            participants=participants_reordered,        # same people, different order
            external_system="MANUAL",                   # explicit spelling of the default
        )
        assert equivalent.status_code == 201, (
            "an equivalent restatement of the same command was refused instead of replayed"
        )
        assert equivalent.json()["replayed"] is True
        assert equivalent.json()["interaction"]["public_id"] == first_public_id
    finally:
        _teardown_full_chain(
            interaction_public_ids=interaction_ids,
            work_order_public_ids=[],
            offer_public_ids=[],
            opportunity_public_ids=opportunity_ids,
            account_public_ids=account_ids,
            lead_public_ids=lead_ids,
        )
