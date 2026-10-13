"""Slice 4G: market rates per offer line, each line's basis rate and basis history, and a rate's quote copy.

Owner's answers, 11 October 2026: the readiness checklist warns about a line with no rate or no basis rate and never
blocks; rates are entered per line; a basis rate is never removed, only replaced with a reason, the earlier choice
becoming history; a rate's currency may differ from its line's. A broker's quote is attached to one rate, and other
lines' rates may refer to that rate for it.
"""

from __future__ import annotations

import contextlib
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.core.database import SessionLocal
from app.main import app
from app.modules.documents.schemas import DocumentMetadataCreate
from app.modules.documents.service import DocumentValidationError, create_document_metadata
from app.modules.documents.storage import get_storage_provider_by_code
from tests.offer_version_test_support import line_row_version
from tests.test_commercial_offers_api import (
    auth_headers,
    cleanup_test_records,
    client,
    create_account_linked_test_opportunity,
    create_test_commercial_offer,
    create_test_submission_evidence,
)

RATE = {
    "evidence_type": "market_rate",
    "source_name": "4G Crane Vendor",
    "equipment_service_description": "80T crawler crane with operator",
    "rate_amount": "95000.00",
    "currency_code": "INR",
    "rate_basis": "per_day",
}


class _Records:
    def __init__(self) -> None:
        self.opportunities: list[str] = []
        self.offers: list[str] = []
        self.accounts: list[str] = []
        self.leads: list[str] = []
        self.documents: list[str] = []

    def offer(self) -> str:
        linked = create_account_linked_test_opportunity()
        self.leads.append(str(linked["lead"]["public_id"]))
        self.accounts.append(str(linked["account"]["public_id"]))
        self.opportunities.append(str(linked["opportunity"]["public_id"]))
        offer_public_id = str(create_test_commercial_offer(str(linked["opportunity"]["public_id"]))["public_id"])
        self.offers.append(offer_public_id)
        return offer_public_id

    def cleanup(self) -> None:
        """Stored files first, then their rows and events (review 4G-R1-007), then the offers."""
        with SessionLocal() as db:
            documents = db.execute(
                text(
                    "SELECT document_public_id, storage_provider_code, storage_key FROM document_metadata "
                    "WHERE linked_record_type IN ('commercial_offer_market_rate', 'commercial_offer') "
                    "AND linked_record_public_id IN (SELECT pe.evidence_public_id FROM crm_commercial_offer_pricing_evidence pe "
                    "JOIN crm_commercial_offer co ON co.id = pe.commercial_offer_id WHERE co.offer_public_id = ANY(:ids) "
                    "UNION SELECT offer_public_id FROM crm_commercial_offer WHERE offer_public_id = ANY(:ids))"
                ),
                {"ids": self.offers},
            ).fetchall()
        for _, provider_code, storage_key in documents:
            if storage_key:
                with contextlib.suppress(Exception):
                    get_storage_provider_by_code(provider_code).delete(storage_key=storage_key)
        uploaded = list(_UPLOADED)
        _UPLOADED.clear()
        document_ids = sorted({str(row[0]) for row in documents} | set(uploaded))
        with SessionLocal() as db:
            db.execute(
                text("DELETE FROM business_event WHERE record_type = 'document_metadata' AND record_public_id = ANY(:ids)"),
                {"ids": document_ids},
            )
            db.execute(text("DELETE FROM document_metadata WHERE document_public_id = ANY(:ids)"), {"ids": document_ids})
            db.commit()
            # Asked again, independently of the list above: nothing linked to the offers or their rates is left, and
            # every document a test uploaded is gone with its events.
            assert db.execute(
                text(
                    "SELECT COUNT(*) FROM document_metadata WHERE document_public_id = ANY(:uploaded) "
                    "OR linked_record_public_id IN (SELECT pe.evidence_public_id FROM crm_commercial_offer_pricing_evidence pe "
                    "JOIN crm_commercial_offer co ON co.id = pe.commercial_offer_id WHERE co.offer_public_id = ANY(:offers)) "
                    "OR linked_record_public_id = ANY(:offers)"
                ),
                {"uploaded": uploaded, "offers": self.offers},
            ).scalar_one() == 0
            assert db.execute(
                text("SELECT COUNT(*) FROM business_event WHERE record_type = 'document_metadata' AND record_public_id = ANY(:ids)"),
                {"ids": uploaded},
            ).scalar_one() == 0
        cleanup_test_records(
            opportunity_public_ids=self.opportunities,
            offer_public_ids=list(reversed(self.offers)),
            account_public_ids=self.accounts,
            lead_public_ids=self.leads,
        )


@pytest.fixture()
def records():
    made = _Records()
    try:
        yield made
    finally:
        made.cleanup()


def _line(offer_public_id: str, scope: str = "80T crawler crane", status: int = 201) -> dict:
    response = client.post(
        f"/api/commercial-offers/{offer_public_id}/lines",
        headers=auth_headers("sales1"),
        json={"scope_description": scope, "quantity": "1.00", "uom": "month", "rate_amount": "100000.00"},
    )
    assert response.status_code == status, response.text
    return response.json()["offer_line"]


def _rate(offer_public_id: str, line_public_id: str | None, **extra) -> object:
    payload = {**RATE, **extra}
    if line_public_id is not None:
        payload["line_public_id"] = line_public_id
    return client.post(f"/api/commercial-offers/{offer_public_id}/pricing-evidence", headers=auth_headers("ops1"), json=payload)


def _choose(offer_public_id: str, rate_public_id: str, reason: str | None, user: str = "sales1"):
    return client.post(
        f"/api/commercial-offers/{offer_public_id}/pricing-evidence/{rate_public_id}/select-basis",
        headers=auth_headers(user),
        json={"selection_reason": reason},
    )


def _rates(offer_public_id: str) -> dict[str, dict]:
    response = client.get(f"/api/commercial-offers/{offer_public_id}/pricing-evidence", headers=auth_headers("finance1"))
    assert response.status_code == 200, response.text
    return {row["public_id"]: row for row in response.json()}


# Every document a test uploads, so the cleanup can show each is gone (review 4G-R3-003).
_UPLOADED: list[str] = []


def _upload_quote(rate_public_id: str, *, user: str = "ops1", document_type: str = "VENDOR_QUOTE"):
    response = _post_quote(rate_public_id, user=user, document_type=document_type)
    if response.status_code == 201:
        _UPLOADED.append(str(response.json()["document"]["public_id"]))
    return response


def _post_quote(rate_public_id: str, *, user: str, document_type: str):
    return client.post(
        "/api/documents/upload",
        headers=auth_headers(user),
        data={
            "linked_record_type": "commercial_offer_market_rate",
            "linked_record_public_id": rate_public_id,
            "document_type": document_type,
        },
        files={"file": ("broker-quote.png", b"\x89PNG\r\n\x1a\n" + b"\x00" * 64, "image/png")},
    )


def test_a_rate_names_an_active_line_of_its_own_offer(records) -> None:
    offer = records.offer()
    other_offer = records.offer()
    other_line = _line(other_offer)

    missing = _rate(offer, None)
    assert missing.status_code == 422, "the line is required by the request schema (review 4G-R2-003)"
    assert any(error["loc"][-1] == "line_public_id" for error in missing.json()["detail"])
    foreign = _rate(offer, other_line["public_id"])
    assert foreign.status_code == 422 and "not a line of this Commercial Offer" in foreign.json()["detail"]
    assert _rates(offer) == {}

    line = _line(offer)
    added = _rate(offer, line["public_id"], currency_code="USD")
    assert added.status_code == 201, added.text
    body = added.json()
    assert body["pricing_evidence"]["line_public_id"] == line["public_id"]
    assert body["pricing_evidence"]["line_number"] == line["line_number"]
    assert body["pricing_evidence"]["currency_code"] == "USD", "a rate's currency may differ from its line's"
    assert body["events"][0]["event_payload"]["line_public_id"] == line["public_id"]
    assert body["events"][0]["event_payload"]["line_number"] == line["line_number"]


def test_the_database_refuses_a_new_rate_without_a_line_or_on_another_offers_line(records) -> None:
    offer = records.offer()
    other_line = _line(records.offer())
    with SessionLocal() as db:
        offer_id = db.execute(
            text("SELECT id FROM crm_commercial_offer WHERE offer_public_id = :p"), {"p": offer}
        ).scalar_one()
        other_line_id = db.execute(
            text("SELECT id FROM crm_commercial_offer_line WHERE line_public_id = :p"), {"p": other_line["public_id"]}
        ).scalar_one()
        for line_id in (None, other_line_id):
            with pytest.raises(IntegrityError):
                db.execute(
                    text(
                        "INSERT INTO crm_commercial_offer_pricing_evidence (evidence_public_id, commercial_offer_id, "
                        "commercial_offer_line_id, evidence_type, equipment_service_description, rate_amount, rate_basis) "
                        "VALUES (:p, :o, :l, 'market_rate', 'x', 1, 'per_day')"
                    ),
                    {"p": str(uuid4()), "o": offer_id, "l": line_id},
                )
            db.rollback()


def test_each_line_keeps_its_own_basis_rate_and_its_history(records) -> None:
    offer = records.offer()
    crane, manlift = _line(offer, "80T crawler crane"), _line(offer, "Manlift 18 m")
    crane_low = _rate(offer, crane["public_id"], rate_amount="90000.00").json()["pricing_evidence"]["public_id"]
    crane_high = _rate(offer, crane["public_id"], rate_amount="94000.00").json()["pricing_evidence"]["public_id"]
    manlift_rate = _rate(offer, manlift["public_id"], rate_amount="12000.00").json()["pricing_evidence"]["public_id"]

    assert _choose(offer, crane_low, None).status_code == 422, "a reason is required"
    assert _choose(offer, crane_low, "Lowest, available for the whole period.").status_code == 200
    manlift_choice = _choose(offer, manlift_rate, "Only manlift quote.")
    assert manlift_choice.status_code == 200, manlift_choice.text
    assert manlift_choice.json()["event"]["event_payload"]["line_public_id"] == manlift["public_id"]

    rates = _rates(offer)
    assert rates[crane_low]["is_selected_basis"] and rates[manlift_rate]["is_selected_basis"], "one basis per line"

    again = _choose(offer, crane_low, "Same again.")
    assert again.status_code == 422 and "already the basis rate for line" in again.json()["detail"]

    moved = _choose(offer, crane_high, "Lowest vendor withdrew the machine.")
    assert moved.status_code == 200, moved.text
    assert moved.json()["previous_basis_rate_public_id"] == crane_low
    assert moved.json()["event"]["event_payload"]["previous_basis_pricing_evidence_public_id"] == crane_low

    rates = _rates(offer)
    earlier, current = rates[crane_low], rates[crane_high]
    assert earlier["is_selected_basis"] is False and current["is_selected_basis"] is True
    assert earlier["selection_reason"] is None, "an earlier choice's reason must not read as current"
    assert current["selection_reason"] == "Lowest vendor withdrew the machine."
    [past] = earlier["basis_history"]
    assert past["selection_reason"] == "Lowest, available for the whole period."
    assert past["is_current"] is False and past["ended_at"] is not None and past["ended_by_display_name"]
    assert past["chosen_by_display_name"]
    [now] = current["basis_history"]
    assert now["is_current"] is True and now["ended_at"] is None
    assert rates[manlift_rate]["is_selected_basis"] is True, "another line's basis is untouched"

    with SessionLocal() as db:
        kept = db.execute(
            text(
                "SELECT COUNT(*) FROM crm_commercial_offer_line_basis_choice choice "
                "JOIN crm_commercial_offer_line line ON line.id = choice.commercial_offer_line_id "
                "WHERE line.line_public_id = :p"
            ),
            {"p": crane["public_id"]},
        ).scalar_one()
    assert kept == 2, "nothing about an earlier choice is deleted"


def test_the_database_holds_one_current_choice_per_line_and_no_separate_marker(records) -> None:
    offer = records.offer()
    line = _line(offer)
    first = _rate(offer, line["public_id"]).json()["pricing_evidence"]["public_id"]
    second = _rate(offer, line["public_id"]).json()["pricing_evidence"]["public_id"]
    assert _choose(offer, first, "First.").status_code == 200
    with SessionLocal() as db:
        # A line's basis is its open choice: the old marker is refused on a line's rate (review 4G-R1-002).
        with pytest.raises(IntegrityError):
            db.execute(
                text("UPDATE crm_commercial_offer_pricing_evidence SET is_selected_basis = TRUE WHERE evidence_public_id = :p"),
                {"p": second},
            )
        db.rollback()
        with pytest.raises(IntegrityError):
            db.execute(
                text(
                    "INSERT INTO crm_commercial_offer_line_basis_choice (choice_public_id, commercial_offer_line_id, "
                    "pricing_evidence_id, selection_reason, chosen_at) SELECT :c, pe.commercial_offer_line_id, pe.id, "
                    "'Second open choice', CURRENT_TIMESTAMP FROM crm_commercial_offer_pricing_evidence pe "
                    "WHERE pe.evidence_public_id = :p"
                ),
                {"c": str(uuid4()), "p": second},
            )
        db.rollback()


def test_a_cancelled_line_keeps_its_rates_as_history_and_takes_no_change(records) -> None:
    offer = records.offer()
    line = _line(offer)
    _line(offer, "Second line, so the offer keeps an active line")
    rate = _rate(offer, line["public_id"]).json()["pricing_evidence"]["public_id"]
    other = _rate(offer, line["public_id"]).json()["pricing_evidence"]["public_id"]
    assert _choose(offer, rate, "Chosen before the line was cancelled.").status_code == 200
    cancelled = client.put(
        f"/api/commercial-offers/{offer}/lines/{line['public_id']}",
        headers=auth_headers("sales1"),
        json={"expected_row_version": line_row_version(line["public_id"]), "line_status_code": "CANCELLED"},
    )
    assert cancelled.status_code == 200, cancelled.text

    kept = _rates(offer)
    assert kept[rate]["line_status_code"] == "CANCELLED" and kept[rate]["is_selected_basis"] is True
    added = _rate(offer, line["public_id"])
    assert added.status_code == 422 and "is cancelled" in added.json()["detail"]
    moved = _choose(offer, other, "After cancelling.")
    assert moved.status_code == 422 and "is cancelled" in moved.json()["detail"]
    attached = _upload_quote(rate)
    assert attached.status_code == 422 and "is cancelled" in attached.json()["detail"]


def test_a_rate_recorded_for_the_whole_offer_stays_visible_and_unchanged(records) -> None:
    offer = records.offer()
    _line(offer)
    legacy = str(uuid4())
    with SessionLocal() as db:
        db.execute(
            text(
                "INSERT INTO crm_commercial_offer_pricing_evidence (evidence_public_id, commercial_offer_id, "
                "recorded_for_whole_offer, evidence_type, equipment_service_description, rate_amount, rate_basis, "
                "is_selected_basis, selection_reason) SELECT :p, id, TRUE, 'market_rate', 'Before 4G', 1000, 'per_day', "
                "TRUE, 'Chosen for the whole offer' FROM crm_commercial_offer WHERE offer_public_id = :o"
            ),
            {"p": legacy, "o": offer},
        )
        db.commit()

    row = _rates(offer)[legacy]
    assert row["recorded_for_whole_offer"] is True and row["line_public_id"] is None
    assert row["selection_reason"] == "Chosen for the whole offer"
    refused = _choose(offer, legacy, "Again.")
    assert refused.status_code == 422 and "recorded for the whole offer" in refused.json()["detail"]
    assert _upload_quote(legacy).status_code == 422

    readiness = client.get(f"/api/commercial-offers/{offer}/submission-readiness", headers=auth_headers("sales1")).json()
    pricing = {item["code"]: item for item in readiness["checklist_items"]}["PRICING_EVIDENCE"]
    assert pricing["evidence"]["lines_without_rates"] == [1], "a whole-offer rate counts for no line"


def test_the_checklist_warns_per_line_and_never_blocks_sending(records) -> None:
    offer = records.offer()
    first, second = _line(offer), _line(offer, "Manlift 18 m")

    def pricing() -> dict:
        readiness = client.get(f"/api/commercial-offers/{offer}/submission-readiness", headers=auth_headers("sales1"))
        assert readiness.status_code == 200, readiness.text
        return {item["code"]: item for item in readiness.json()["checklist_items"]}["PRICING_EVIDENCE"]

    item = pricing()
    assert item["status"] == "ATTENTION_REQUIRED" and item["severity"] == "WARNING"
    assert item["evidence"]["lines_without_rates"] == [first["line_number"], second["line_number"]]

    rate = _rate(offer, first["public_id"]).json()["pricing_evidence"]["public_id"]
    item = pricing()
    assert item["evidence"]["lines_without_rates"] == [second["line_number"]]
    assert item["evidence"]["lines_without_basis"] == [first["line_number"]]
    assert "No basis rate chosen on line(s)" in item["message"]

    assert _choose(offer, rate, "Only quote.").status_code == 200
    item = pricing()
    assert item["evidence"]["lines_without_basis"] == [] and item["status"] == "ATTENTION_REQUIRED"

    # Warn only (owner, 11 October 2026): the offer is still recorded as sent with line 2 unpriced.
    create_test_submission_evidence(offer)
    sent = client.post(f"/api/commercial-offers/{offer}/mark-submitted", headers=auth_headers("sales1"))
    assert sent.status_code == 200, sent.text

    refused = _rate(offer, second["public_id"])
    assert refused.status_code == 422 and "can no longer change" in refused.json()["detail"]


def test_a_quote_copy_is_attached_to_one_rate_and_referred_to_by_another(records) -> None:
    offer = records.offer()
    crane_a, crane_b = _line(offer, "Crane at site A"), _line(offer, "Crane at site B")
    first = _rate(offer, crane_a["public_id"]).json()["pricing_evidence"]["public_id"]

    assert _upload_quote(first, user="finance1").status_code == 403, "only those who record rates attach their quotes"
    wrong_type = _upload_quote(first, document_type="OTHER")
    assert wrong_type.status_code == 422 and "VENDOR_QUOTE" in wrong_type.json()["detail"]
    uploaded = _upload_quote(first)
    assert uploaded.status_code == 201, uploaded.text
    document_public_id = uploaded.json()["document"]["public_id"]

    referring = _rate(offer, crane_b["public_id"], quote_copy_rate_public_id=first)
    assert referring.status_code == 201, referring.text
    second = referring.json()["pricing_evidence"]["public_id"]
    assert referring.json()["events"][0]["event_payload"]["quote_copy_pricing_evidence_public_id"] == first

    rates = _rates(offer)
    [own] = rates[first]["quote_copies"]
    assert own["document_public_id"] == document_public_id and own["attached_here"] is True
    [shared] = rates[second]["quote_copies"]
    assert shared["document_public_id"] == document_public_id and shared["attached_here"] is False
    assert shared["attached_to_line_number"] == crane_a["line_number"]
    assert rates[second]["quote_copy_rate_public_id"] == first

    download = client.get(f"/api/documents/{document_public_id}/content", headers=auth_headers("finance1"))
    assert download.status_code == 200, "whoever reads the offer's rates reads their quotes"

    create_test_submission_evidence(offer)
    assert client.post(f"/api/commercial-offers/{offer}/mark-submitted", headers=auth_headers("sales1")).status_code == 200
    locked = _upload_quote(first)
    assert locked.status_code == 422 and "can no longer change" in locked.json()["detail"]

    # A new version's rates still show the quote, attached on version 1 (review 4G-R1-009).
    version = client.post(
        f"/api/commercial-offers/{offer}/versions", headers=auth_headers("sales1"), json={"version_reason": "SCOPE_CHANGE"}
    )
    assert version.status_code == 201, version.text
    v2 = str(version.json()["commercial_offer"]["public_id"])
    records.offers.append(v2)
    # Exactly the two rates, on their matching copied lines, before each is checked (review 4G-R4-001).
    copied = sorted(_rates(v2).values(), key=lambda row: row["line_number"])
    assert [row["line_number"] for row in copied] == [crane_a["line_number"], crane_b["line_number"]]
    assert [row["equipment_service_description"] for row in copied] == [RATE["equipment_service_description"]] * 2
    for row in copied:
        assert row["quote_copy_rate_public_id"] is None, "a copy carries no user reference; it links to its source"
        [carried] = row["quote_copies"]
        assert carried["document_public_id"] == document_public_id
        assert carried["attached_to_line_number"] == crane_a["line_number"]
        assert carried["attached_to_offer_version_number"] == 1 and carried["attached_here"] is False
    assert client.get(f"/api/documents/{document_public_id}/content", headers=auth_headers("finance1")).status_code == 200


def test_a_vendor_quote_is_refused_on_any_other_record(records) -> None:
    """VENDOR_QUOTE belongs on a market rate only, on both document routes (review 4G-R1-001)."""
    offer = records.offer()
    for linked_record_type, linked_id in (("commercial_offer", offer), ("business_party", records.accounts[-1])):
        uploaded = client.post(
            "/api/documents/upload",
            headers=auth_headers("admin1"),
            data={"linked_record_type": linked_record_type, "linked_record_public_id": linked_id, "document_type": "VENDOR_QUOTE"},
            files={"file": ("quote.png", b"\x89PNG\r\n\x1a\n" + b"\x00" * 64, "image/png")},
        )
        assert uploaded.status_code == 422, uploaded.text
        recorded = client.post(
            "/api/documents/metadata",
            headers=auth_headers("admin1"),
            json={
                "document_type": "vendor_quote",
                "linked_record_type": linked_record_type,
                "linked_record_public_id": linked_id,
                "file_name": "quote.pdf",
                "storage_mode": "external_link",
                "storage_path_or_url": "https://example.invalid/quote.pdf",
                "status": "Linked",
            },
        )
        assert recorded.status_code == 422, recorded.text
    with SessionLocal() as db:
        assert db.execute(
            text("SELECT COUNT(*) FROM document_metadata WHERE linked_record_public_id IN (:o, :a)"),
            {"o": offer, "a": records.accounts[-1]},
        ).scalar_one() == 0


def test_a_long_chain_of_quote_references_still_finds_the_quote(records) -> None:
    """Twenty-five rates, each referring to the one before, the first holding the quote: the last still shows it
    (review 4G-R3-001)."""
    offer = records.offer()
    line = _line(offer)
    previous = _rate(offer, line["public_id"]).json()["pricing_evidence"]["public_id"]
    document = _upload_quote(previous).json()["document"]["public_id"]
    for _ in range(25):
        response = _rate(offer, line["public_id"], quote_copy_rate_public_id=previous)
        assert response.status_code == 201, response.text
        previous = response.json()["pricing_evidence"]["public_id"]
    [copy] = _rates(offer)[previous]["quote_copies"]
    assert copy["document_public_id"] == document and copy["attached_here"] is False


def test_the_database_lets_a_rate_refer_only_to_an_earlier_rate(records) -> None:
    offer = records.offer()
    line = _line(offer)
    earlier, later = (_rate(offer, line["public_id"]).json()["pricing_evidence"]["public_id"] for _ in range(2))
    with SessionLocal() as db:
        for referrer, referred in ((earlier, later), (earlier, earlier)):
            with pytest.raises(IntegrityError):
                db.execute(
                    text(
                        "UPDATE crm_commercial_offer_pricing_evidence SET quote_copy_evidence_id = "
                        "(SELECT id FROM crm_commercial_offer_pricing_evidence WHERE evidence_public_id = :referred) "
                        "WHERE evidence_public_id = :referrer"
                    ),
                    {"referrer": referrer, "referred": referred},
                )
            db.rollback()


def test_the_database_holds_each_quote_link_to_where_it_may_point(records) -> None:
    """A user's reference stays within its offer; a copy's link goes only to the offer its version was made from; a
    rate has at most one of the two (review 4G-R4-005). The permitted cases are proven by the quote tests above."""
    other_offer = records.offer()
    other_rate = _rate(other_offer, _line(other_offer)["public_id"]).json()["pricing_evidence"]["public_id"]
    offer = records.offer()
    rate = _rate(offer, _line(offer)["public_id"]).json()["pricing_evidence"]["public_id"]
    statements = (
        # a reference to another offer's rate
        "UPDATE crm_commercial_offer_pricing_evidence SET quote_copy_evidence_id = (SELECT id FROM "
        "crm_commercial_offer_pricing_evidence WHERE evidence_public_id = :other) WHERE evidence_public_id = :rate",
        # a copy's link to a rate of an offer this one was not made from
        "UPDATE crm_commercial_offer_pricing_evidence SET copied_from_evidence_id = src.id, "
        "copied_from_offer_id = src.commercial_offer_id FROM crm_commercial_offer_pricing_evidence src "
        "WHERE src.evidence_public_id = :other AND crm_commercial_offer_pricing_evidence.evidence_public_id = :rate",
        # half a copy link
        "UPDATE crm_commercial_offer_pricing_evidence SET copied_from_evidence_id = (SELECT id FROM "
        "crm_commercial_offer_pricing_evidence WHERE evidence_public_id = :other) WHERE evidence_public_id = :rate",
    )
    with SessionLocal() as db:
        for statement in statements:
            with pytest.raises(IntegrityError):
                db.execute(text(statement), {"other": other_rate, "rate": rate})
            db.rollback()


def test_a_padded_record_type_cannot_skip_the_rates_check(records) -> None:
    """A trusted caller of the documents service, with a type padded by a space, is still refused (review 4G-R4-002)."""
    offer = records.offer()
    rate = _rate(offer, _line(offer)["public_id"]).json()["pricing_evidence"]["public_id"]
    for document_type in ("VENDOR_QUOTE", "OTHER"):
        with SessionLocal() as db:
            with pytest.raises(DocumentValidationError):
                create_document_metadata(
                    db,
                    payload=DocumentMetadataCreate(
                        document_type=document_type,
                        linked_record_type="commercial_offer_market_rate ",
                        linked_record_public_id=rate,
                        file_name="quote.pdf",
                        storage_mode="external_link",
                        storage_path_or_url="https://example.invalid/quote.pdf",
                        status="Linked",
                    ),
                    current_user_public_id=None,
                )
            db.rollback()
    with SessionLocal() as db:
        assert db.execute(
            text("SELECT COUNT(*) FROM document_metadata WHERE linked_record_public_id = :p"), {"p": rate}
        ).scalar_one() == 0


def test_the_published_requests_mark_the_line_and_the_reason_required() -> None:
    """What generated clients read (reviews 4G-R2-003, 4G-R4-003)."""
    schemas = app.openapi()["components"]["schemas"]
    assert "line_public_id" in schemas["CommercialOfferPricingEvidenceCreate"]["required"]
    assert "selection_reason" in schemas["CommercialOfferPricingEvidenceBasisSelection"]["required"]


def test_a_quote_reference_must_lead_to_an_attached_quote(records) -> None:
    offer = records.offer()
    first = _rate(offer, _line(offer)["public_id"]).json()["pricing_evidence"]["public_id"]
    refused = _rate(offer, _line(offer, "Second site")["public_id"], quote_copy_rate_public_id=first)
    assert refused.status_code == 422 and "has no quote attached yet" in refused.json()["detail"]


def test_a_quote_copy_must_be_a_rate_of_the_same_offer(records) -> None:
    offer = records.offer()
    other_offer = records.offer()
    other_rate = _rate(other_offer, _line(other_offer)["public_id"]).json()["pricing_evidence"]["public_id"]
    refused = _rate(offer, _line(offer)["public_id"], quote_copy_rate_public_id=other_rate)
    assert refused.status_code == 422 and "not a rate of this Commercial Offer" in refused.json()["detail"]
