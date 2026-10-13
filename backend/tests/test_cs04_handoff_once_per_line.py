"""CS-04 part 1 (TB-1 G-103, HOF-2): what may be handed off to a Work Order, and how often.

The owner's decisions of 8 October 2026 (docs/continuity/TB1_103_WORK_ORDER_HANDOFF_ONCE_PER_LINE.md, and the dated
amendment of the frozen handoff contract): an accepted offer line's quantity goes onto Work Orders once, whole or in
parts; a Base Offer or a Supplementary Offer makes a Work Order, a Change Quotation never does; the offer's latest
customer response must be the acceptance; an offer with a Work Order is not recorded lost. Two handoffs at once never
together pass a line's quantity - when both cannot fit, one is made and one refused - and the database holds the quantity
even for a writer that skips the handoff's checks. Since the owner's rule after review round 3, every Work Order
carries the customer's Work Order reference, once per offer, so a repeated request - whole line or part - is refused.
"""

from __future__ import annotations

import json
import re
import threading
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.core.database import SessionLocal
from app.modules.work_orders.schemas import WorkOrderCreateFromCommercialOffer
from app.modules.work_orders.service import WorkOrderHandoffConflictError, create_work_order_from_commercial_offer
from app.modules.work_orders.services import handoff
from tests.test_commercial_offer_related_offers_api import _accept_offer_with_line, _null_related_work_order_links
from tests.test_commercial_offers_api import (
    auth_headers,
    client,
    cleanup_test_records,
    cleanup_test_work_orders,
    create_account_linked_test_opportunity,
    create_test_commercial_offer,
    mark_test_commercial_offer_submitted,
    record_test_customer_response,
)
from tests.test_hiring_uat_smoke_data import DOCS

NOTE = DOCS / "continuity" / "TB1_103_WORK_ORDER_HANDOFF_ONCE_PER_LINE.md"


@pytest.fixture
def chain():
    """An accepted Base Offer with two lines: line 1, quantity 10 at 25,000; line 2, quantity 1 with no rate."""
    linked = create_account_linked_test_opportunity()
    record: dict[str, object] = {"offers": [], "work_orders": []}
    try:
        offer_public_id = str(create_test_commercial_offer(str(linked["opportunity"]["public_id"]))["public_id"])
        record["offers"].append(offer_public_id)
        ten = client.post(
            f"/api/commercial-offers/{offer_public_id}/lines",
            headers=auth_headers("sales1"),
            json={"scope_description": "80T crane", "quantity": "10.00", "uom": "Days", "rate_amount": "25000.00"},
        )
        assert ten.status_code == 201
        mark_test_commercial_offer_submitted(offer_public_id)
        record_test_customer_response(offer_public_id, "ACCEPTED_AWARDED", received_at="2026-08-05T09:00:00Z")
        lines = client.get(f"/api/commercial-offers/{offer_public_id}/lines", headers=auth_headers("sales1")).json()
        record["offer"] = offer_public_id
        record["ten"] = ten.json()["offer_line"]["public_id"]
        record["one"] = next(line["public_id"] for line in lines if line["public_id"] != record["ten"])
        yield record
    finally:
        _null_related_work_order_links(record["offers"])
        cleanup_test_work_orders(record["work_orders"])
        cleanup_test_records(
            opportunity_public_ids=[str(linked["opportunity"]["public_id"])],
            offer_public_ids=record["offers"],
            account_public_ids=[str(linked["account"]["public_id"])],
            lead_public_ids=[str(linked["lead"]["public_id"])],
        )


def _hand_off(chain, offer_public_id: str | None = None, **body):
    """A handoff as the Create page sends it; a customer order reference of its own unless the test gives one."""
    body.setdefault("customer_wo_reference", f"CUST-{uuid4()}")
    response = client.post(
        "/api/work-orders/from-commercial-offer",
        headers=auth_headers("sales1"),
        json={"commercial_offer_public_id": offer_public_id or chain["offer"], **body},
    )
    if response.status_code == 201:
        chain["work_orders"].append(response.json()["work_order"]["public_id"])
    return response


def _parts(*pairs: tuple[str, str]) -> list[dict[str, str]]:
    return [{"offer_line_public_id": line, "quantity": quantity} for line, quantity in pairs]


def _guidance(offer_public_id: str) -> dict:
    response = client.get(f"/api/commercial-offers/{offer_public_id}/lifecycle-guidance", headers=auth_headers("sales1"))
    assert response.status_code == 200
    return response.json()


def _work_order_count(offer_public_id: str) -> int:
    with SessionLocal() as db:
        return int(
            db.execute(
                text(
                    "SELECT COUNT(*) FROM crm_work_order wo JOIN crm_commercial_offer co ON co.id = wo.commercial_offer_id "
                    "WHERE co.offer_public_id = :public_id"
                ),
                {"public_id": offer_public_id},
            ).scalar_one()
        )


def _quantity_on_work_orders(offer_line_public_id: str) -> Decimal:
    with SessionLocal() as db:
        return Decimal(
            db.execute(
                text(
                    "SELECT COALESCE(SUM(wol.quantity), 0) FROM crm_work_order_line wol "
                    "JOIN crm_commercial_offer_line col ON col.id = wol.commercial_offer_line_id "
                    "WHERE col.line_public_id = :public_id"
                ),
                {"public_id": offer_line_public_id},
            ).scalar_one()
        )


def test_a_line_is_handed_off_in_parts_but_never_past_its_quantity(chain) -> None:
    first = _hand_off(chain, selected_offer_line_public_ids=[chain["ten"]], selected_offer_line_quantities=_parts((chain["ten"], "6")))
    assert first.status_code == 201, first.text
    first_code = first.json()["work_order"]["work_order_code"]
    [line] = first.json()["lines"]
    assert (Decimal(line["quantity"]), Decimal(line["line_amount"])) == (Decimal("6"), Decimal("150000"))
    assert _guidance(chain["offer"])["work_order_handoff_available"] is True

    # The same request again - a second tab, a Create pressed after a timeout - finds only 4 left and is refused.
    again = _hand_off(chain, selected_offer_line_public_ids=[chain["ten"]], selected_offer_line_quantities=_parts((chain["ten"], "6")))
    assert again.status_code == 409
    assert "Line 1 has 4 of 10 left to hand off" in again.json()["detail"] and first_code in again.json()["detail"]

    # What is left of line 1, and line 2 whole, on a second Work Order: a partial award.
    second = _hand_off(chain, selected_offer_line_public_ids=[chain["ten"], chain["one"]])
    assert second.status_code == 201, second.text
    second_code = second.json()["work_order"]["work_order_code"]
    quantities = sorted((Decimal(item["quantity"]), item["line_amount"]) for item in second.json()["lines"])
    assert quantities == [(Decimal("1"), None), (Decimal("4"), "100000.00")]
    assert _quantity_on_work_orders(chain["ten"]) == Decimal("10")

    for body in ({}, {"selected_offer_line_public_ids": [chain["ten"]]}):
        refused = _hand_off(chain, **body)
        assert refused.status_code == 409
        assert first_code in refused.json()["detail"] and second_code in refused.json()["detail"]
    assert "Line 1 is already on a Work Order in full" in refused.json()["detail"]
    assert _work_order_count(chain["offer"]) == 2

    guidance = _guidance(chain["offer"])
    assert guidance["work_order_handoff_available"] is False
    assert "Every line of this offer is already on a Work Order in full." in guidance["work_order_handoff_blocked_reasons"]


def test_with_no_line_chosen_a_work_order_takes_what_is_left(chain) -> None:
    assert _hand_off(chain, selected_offer_line_public_ids=[chain["ten"]], selected_offer_line_quantities=_parts((chain["ten"], "3"))).status_code == 201
    rest = _hand_off(chain)
    assert rest.status_code == 201, rest.text
    assert sorted(Decimal(item["quantity"]) for item in rest.json()["lines"]) == [Decimal("1"), Decimal("7")]
    refused = _hand_off(chain)
    assert refused.status_code == 409
    assert "Every line of this offer is already on a Work Order in full" in refused.json()["detail"]


def _stored_payload(event_public_id: str) -> dict:
    with SessionLocal() as db:
        return json.loads(
            db.execute(
                text("SELECT event_payload_json FROM business_event WHERE public_id = :public_id"),
                {"public_id": event_public_id},
            ).scalar_one()
        )


def test_the_handoff_event_names_each_line_its_quantity_and_amount(chain) -> None:
    """CS-04 part 2, item c (the frozen handoff contract's amendment of 12 October 2026). `CommercialOfferConvertedToWorkOrder`
    is what credit exposure's Potential-to-Firm transfer reads (CEX-001), so it says, for each Work Order line, the offer
    line it came from, how much, and its amount - a part's amount, not the whole line's. Both events and the Work Order
    name the offer's version."""
    first = _hand_off(chain, selected_offer_line_public_ids=[chain["ten"]], selected_offer_line_quantities=_parts((chain["ten"], "6")))
    assert first.status_code == 201, first.text
    work_order = first.json()["work_order"]
    assert work_order["commercial_offer_version_number"] == 1
    assert work_order["work_order_title"] == f"Work Order from {work_order['commercial_offer_code']}"
    events = {event["event_name"]: event for event in first.json()["events"]}
    assert events["WorkOrderCreated"]["event_payload"]["commercial_offer_version_number"] == 1
    converted = events["CommercialOfferConvertedToWorkOrder"]
    [line] = first.json()["lines"]
    assert converted["event_payload"]["commercial_offer_version_number"] == 1
    assert converted["event_payload"]["lines"] == [
        {
            "offer_line_public_id": chain["ten"],
            "work_order_line_public_id": line["public_id"],
            "line_number": line["line_number"],
            "quantity": "6.00",
            "uom": "Days",
            "currency_code": "INR",
            "line_amount": "150000.00",
        }
    ]
    assert _stored_payload(converted["public_id"]) == converted["event_payload"], "the stored event is what was returned"

    # The rest: line 1's remaining 4, and line 2 whole, which has no rate.
    rest = _hand_off(chain)
    assert rest.status_code == 201, rest.text
    event_lines = next(
        event["event_payload"] for event in rest.json()["events"] if event["event_name"] == "CommercialOfferConvertedToWorkOrder"
    )["lines"]
    # One entry per Work Order line made, in the response's order, each once.
    assert [(item["work_order_line_public_id"], item["offer_line_public_id"]) for item in event_lines] == [
        (line["public_id"], line["source_offer_line_public_id"]) for line in rest.json()["lines"]
    ]
    assert len(event_lines) == 2
    by_offer_line = {item["offer_line_public_id"]: item for item in event_lines}
    assert set(by_offer_line) == {chain["ten"], chain["one"]}
    assert (by_offer_line[chain["ten"]]["quantity"], by_offer_line[chain["ten"]]["line_amount"]) == ("4.00", "100000.00")
    assert (by_offer_line[chain["one"]]["quantity"], by_offer_line[chain["one"]]["line_amount"]) == ("1.00", None)


def test_the_parts_of_a_line_add_up_to_its_amount(chain) -> None:
    """Quantity 1.50 at 10.01 is 15.02 (15.015 rounded). Three parts of 0.50 rounded alone would make 5.01 each, 15.03;
    each part is the line's amount up to its end less the amount up to its start - 5.01, 10.01 - 5.01, 15.02 - 10.01 -
    so the Work Orders hold 15.02, as the offer does."""
    created = client.post(
        f"/api/commercial-offers/{chain['offer']}/related-offers",
        headers=auth_headers("sales1"),
        json={"offer_purpose": "SUPPLEMENTARY", "customer_request_summary": "CS-04 rounding test."},
    )
    assert created.status_code == 201, created.text
    supplementary = str(created.json()["commercial_offer"]["public_id"])
    chain["offers"].insert(0, supplementary)
    line = client.post(
        f"/api/commercial-offers/{supplementary}/lines",
        headers=auth_headers("sales1"),
        json={"scope_description": "Rigger", "quantity": "1.50", "uom": "Mon", "rate_amount": "10.01"},
    )
    assert line.status_code == 201 and line.json()["offer_line"]["line_amount"] == "15.02"
    line_public_id = line.json()["offer_line"]["public_id"]
    _accept_offer_with_line(supplementary)

    amounts = []
    for _ in range(3):
        part = _hand_off(
            chain,
            supplementary,
            selected_offer_line_public_ids=[line_public_id],
            selected_offer_line_quantities=_parts((line_public_id, "0.50")),
        )
        assert part.status_code == 201, part.text
        amounts.append(Decimal(part.json()["lines"][0]["line_amount"]))
    assert amounts == [Decimal("5.01"), Decimal("5.00"), Decimal("5.01")]
    assert sum(amounts) == Decimal("15.02")


@pytest.mark.parametrize(
    ("rate", "quantity", "line_amount", "parts", "expected"),
    [
        ("0.01", "2.00", "0.02", ["0.50"] * 4, ["0.01", "0.00", "0.01", "0.00"]),
        ("10.01", "1.50", "15.02", ["1.00", "0.50"], ["10.01", "5.01"]),
        ("25000.00", "10.00", "250000.00", ["10.00"], ["250000.00"]),
    ],
)
def test_a_part_is_worth_the_line_up_to_its_end_less_up_to_its_start(rate, quantity, line_amount, parts, expected) -> None:
    """Never below zero, and the parts add up to the line's amount however small the rate: rounding each part alone
    would give 0.01 four times, 0.04, for a 0.02 line."""
    line = {"quantity": Decimal(quantity), "rate_amount": Decimal(rate), "line_amount": Decimal(line_amount)}
    taken = Decimal("0")
    amounts = []
    for part in parts:
        amounts.append(handoff._part_amount(line, Decimal(part), taken))
        taken += Decimal(part)
    assert amounts == [Decimal(value) for value in expected]
    assert sum(amounts) == Decimal(line_amount)
    assert all(amount >= 0 for amount in amounts)


def test_quantities_must_name_selected_lines_once_and_be_above_zero(chain) -> None:
    other_line = _hand_off(chain, selected_offer_line_public_ids=[chain["ten"]], selected_offer_line_quantities=_parts((chain["one"], "1")))
    assert other_line.status_code == 422 and "not selected" in other_line.json()["detail"]
    twice = _hand_off(chain, selected_offer_line_quantities=_parts((chain["ten"], "1"), (chain["ten"], "2")))
    assert twice.status_code == 422 and "twice" in twice.json()["detail"]
    assert _hand_off(chain, selected_offer_line_quantities=_parts((chain["ten"], "0"))).status_code == 422
    assert _work_order_count(chain["offer"]) == 0


def test_a_change_quotation_never_makes_a_work_order_and_a_supplementary_offer_may(chain) -> None:
    base_work_order = _hand_off(chain)
    assert base_work_order.status_code == 201
    base_work_order_public_id = base_work_order.json()["work_order"]["public_id"]

    related: dict[str, str] = {}
    for purpose in ("CHANGE_QUOTATION", "SUPPLEMENTARY"):
        created = client.post(
            f"/api/commercial-offers/{chain['offer']}/related-offers",
            headers=auth_headers("sales1"),
            json={
                "offer_purpose": purpose,
                "customer_request_summary": f"CS-04 {purpose} test.",
                "related_work_order_public_id": base_work_order_public_id,
            },
        )
        assert created.status_code == 201, created.text
        related[purpose] = str(created.json()["commercial_offer"]["public_id"])
        chain["offers"].insert(0, related[purpose])
        _accept_offer_with_line(related[purpose])

    change = _hand_off(chain, related["CHANGE_QUOTATION"])
    assert change.status_code == 422
    assert change.json()["detail"].startswith("This is a Change Quotation.")
    guidance = _guidance(related["CHANGE_QUOTATION"])
    assert guidance["work_order_handoff_available"] is False
    assert any("Change Quotation" in reason for reason in guidance["work_order_handoff_blocked_reasons"])

    assert _guidance(related["SUPPLEMENTARY"])["work_order_handoff_available"] is True
    supplementary = _hand_off(chain, related["SUPPLEMENTARY"])
    assert supplementary.status_code == 201, supplementary.text

    # The database holds the rule too: a Work Order cannot be moved onto the Change Quotation.
    with SessionLocal() as db:
        with pytest.raises(IntegrityError) as refused:
            db.execute(
                text(
                    "UPDATE crm_work_order SET commercial_offer_id = "
                    "(SELECT id FROM crm_commercial_offer WHERE offer_public_id = :offer) WHERE work_order_public_id = :wo"
                ),
                {"offer": related["CHANGE_QUOTATION"], "wo": base_work_order_public_id},
            )
        db.rollback()
    assert refused.value.orig.diag.constraint_name == "ck_crm_work_order_not_from_change_quotation"


def test_the_latest_customer_response_must_be_the_acceptance(chain) -> None:
    record_test_customer_response(chain["offer"], "ON_HOLD", received_at="2026-08-06T09:00:00Z")
    held = _hand_off(chain)
    assert held.status_code == 422
    assert held.json()["detail"].startswith("The customer's latest response is On hold.")
    assert _guidance(chain["offer"])["work_order_handoff_available"] is False

    record_test_customer_response(chain["offer"], "ACCEPTED_AWARDED", received_at="2026-08-07T09:00:00Z")
    assert _hand_off(chain, selected_offer_line_public_ids=[chain["ten"]]).status_code == 201

    # "Latest" is by the date the customer responded, as on the offer page: a pending decision dated before the
    # acceptance, entered after it, does not hold the rest back.
    record_test_customer_response(chain["offer"], "PENDING_CUSTOMER_DECISION", received_at="2026-08-02T09:00:00Z")
    assert _guidance(chain["offer"])["work_order_handoff_available"] is True
    assert _hand_off(chain).status_code == 201


def test_the_offer_page_names_the_latest_response_whatever_else_blocks_it(chain) -> None:
    """Review round 7: with every line on a Work Order in full, a later On hold is still named on the offer page - as
    the handoff names it - beside the lines being taken; the view once showed only the first reason it found."""
    assert _hand_off(chain).status_code == 201
    record_test_customer_response(chain["offer"], "ON_HOLD", received_at="2026-08-06T09:00:00Z")
    held = _hand_off(chain)
    assert held.status_code == 422
    assert held.json()["detail"] == (
        "The customer's latest response is On hold. Record the customer's acceptance or award first, then create the "
        "Work Order."
    )
    guidance = _guidance(chain["offer"])
    assert guidance["work_order_handoff_available"] is False
    assert guidance["work_order_handoff_blocked_reasons"] == [
        held.json()["detail"],
        "Every line of this offer is already on a Work Order in full.",
    ]


def test_an_offer_with_a_work_order_is_not_recorded_lost(chain) -> None:
    work_order = _hand_off(chain, selected_offer_line_public_ids=[chain["one"]])
    assert work_order.status_code == 201
    response = client.post(
        f"/api/commercial-offers/{chain['offer']}/customer-responses",
        headers=auth_headers("sales1"),
        json={"response_outcome": "REJECTED_LOST", "response_received_at": "2026-08-08T09:00:00Z", "response_channel": "EMAIL"},
    )
    assert response.status_code == 422
    assert work_order.json()["work_order"]["work_order_code"] in response.json()["detail"]
    offer = client.get(f"/api/commercial-offers/{chain['offer']}", headers=auth_headers("sales1")).json()
    assert offer["offer_status_code"] == "ACCEPTED"
    responses = client.get(f"/api/commercial-offers/{chain['offer']}/customer-responses", headers=auth_headers("sales1"))
    assert [item["response_outcome"] for item in responses.json()] == ["ACCEPTED_AWARDED"]

    # A response that is not final is still recorded; it holds back the rest until an acceptance is recorded again.
    record_test_customer_response(chain["offer"], "ON_HOLD", received_at="2026-08-08T10:00:00Z")
    assert _hand_off(chain).status_code == 422


def test_an_accepted_offer_without_a_work_order_may_still_be_recorded_lost(chain) -> None:
    lost = record_test_customer_response(chain["offer"], "REJECTED_LOST", received_at="2026-08-08T09:00:00Z")
    assert lost["commercial_offer"]["offer_status_code"] == "REJECTED"


def _actor() -> str:
    with SessionLocal() as db:
        return str(db.execute(text("SELECT public_id FROM app_user WHERE username = 'sales1'")).scalar_one())


def _two_at_once(chain, references: tuple[str, str], **body) -> list[tuple[str, object]]:
    """Two handoffs started at the same moment, each with its own customer order reference."""
    payloads = [
        WorkOrderCreateFromCommercialOffer(commercial_offer_public_id=UUID(chain["offer"]), customer_wo_reference=reference, **body)
        for reference in references
    ]
    actor = _actor()
    barrier = threading.Barrier(2, timeout=30)
    results: list[tuple[str, object]] = [("not run", None), ("not run", None)]

    def run(index: int) -> None:
        barrier.wait()
        with SessionLocal() as db:
            try:
                created = create_work_order_from_commercial_offer(db, payload=payloads[index], current_user_public_id=actor)
                results[index] = ("created", created)
                chain["work_orders"].append(str(created.work_order.public_id))
            except Exception as exc:  # noqa: BLE001 - the test reports what each thread met
                results[index] = ("refused", exc)

    threads = [threading.Thread(target=run, args=(index,)) for index in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=60)
    return results


def _three_of_ten(chain) -> dict:
    return {
        "selected_offer_line_public_ids": [UUID(chain["ten"])],
        "selected_offer_line_quantities": [{"offer_line_public_id": UUID(chain["ten"]), "quantity": Decimal("3")}],
    }


def test_two_parts_at_once_for_one_customer_order_give_one_work_order(chain) -> None:
    """Review round 1's finding 3, fixed (the owner, 8 October 2026): two requests at once for 3 of line 1's 10 both
    fit, but they carry the same customer order, so one is made and the other refused, naming it."""
    results = _two_at_once(chain, ("PO-ONE", "po-one "), **_three_of_ten(chain))
    assert sorted(kind for kind, _ in results) == ["created", "refused"], results
    refusal = next(value for kind, value in results if kind == "refused")
    assert isinstance(refusal, WorkOrderHandoffConflictError) and "is already on" in str(refusal), refusal
    assert _quantity_on_work_orders(chain["ten"]) == Decimal("3")


def test_two_customer_orders_at_once_for_parts_that_fit_are_both_made(chain) -> None:
    """Two customer orders for 3 each are two awards: both are made, and together they never pass the line."""
    results = _two_at_once(chain, ("PO-ONE", "PO-TWO"), **_three_of_ten(chain))
    assert sorted(kind for kind, _ in results) == ["created", "created"], results
    assert _quantity_on_work_orders(chain["ten"]) == Decimal("6")


def test_two_handoffs_at_once_give_one_work_order_and_one_refusal(chain) -> None:
    """Two customer orders each asking for the whole offer: only one can have it."""
    results = _two_at_once(chain, ("PO-ONE", "PO-TWO"))
    assert sorted(kind for kind, _ in results) == ["created", "refused"], results
    refusal = next(value for kind, value in results if kind == "refused")
    assert isinstance(refusal, WorkOrderHandoffConflictError), refusal
    assert _work_order_count(chain["offer"]) == 1


def test_the_database_holds_the_quantity_when_two_writers_skip_the_offer_lock(chain, monkeypatch) -> None:
    """Both requests skip the offer lock and both read the line as free; the trigger still lets only one through, and
    the other gets the handoff's own refusal, not a server error."""
    monkeypatch.setattr(handoff, "lock_commercial_offer_row", lambda db, *, commercial_offer_public_id: 1)
    original = handoff.list_offer_line_work_order_parts
    barrier = threading.Barrier(2, timeout=30)
    waited: set[int] = set()
    guard = threading.Lock()

    def read_then_wait(db, *, commercial_offer_line_ids):
        found = original(db, commercial_offer_line_ids=commercial_offer_line_ids)
        with guard:
            first = threading.get_ident() not in waited
            waited.add(threading.get_ident())
        if first:
            barrier.wait()
        return found

    monkeypatch.setattr(handoff, "list_offer_line_work_order_parts", read_then_wait)
    results = _two_at_once(chain, ("PO-ONE", "PO-TWO"))
    assert sorted(kind for kind, _ in results) == ["created", "refused"], results
    refusal = next(value for kind, value in results if kind == "refused")
    assert isinstance(refusal, WorkOrderHandoffConflictError), refusal
    assert isinstance(refusal.__cause__ or refusal.__context__, IntegrityError)
    assert _work_order_count(chain["offer"]) == 1
    assert _quantity_on_work_orders(chain["ten"]) == Decimal("10")


def test_the_database_refuses_work_order_lines_past_the_quantity(chain) -> None:
    assert _hand_off(chain, selected_offer_line_public_ids=[chain["ten"]], selected_offer_line_quantities=_parts((chain["ten"], "9"))).status_code == 201
    copy_line = """
        INSERT INTO crm_work_order_line (work_order_line_public_id, work_order_id, commercial_offer_line_id, line_number,
            line_status_code, scope_description, quantity, uom, currency_code, created_at, updated_at)
        SELECT gen_random_uuid(), wol.work_order_id, wol.commercial_offer_line_id, wol.line_number, wol.line_status_code,
            wol.scope_description, :quantity, wol.uom, wol.currency_code, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
        FROM crm_work_order_line wol JOIN crm_commercial_offer_line col ON col.id = wol.commercial_offer_line_id
        WHERE col.line_public_id = :line
    """
    shrink_line = "UPDATE crm_commercial_offer_line SET quantity = :quantity WHERE line_public_id = :line"
    for statement, quantity in (
        (copy_line, "2"),
        (
            "UPDATE crm_work_order_line SET quantity = :quantity WHERE commercial_offer_line_id = "
            "(SELECT id FROM crm_commercial_offer_line WHERE line_public_id = :line)",
            "11",
        ),
        # Review round 2: the offer line's own quantity cannot go below what its Work Orders hold.
        (shrink_line, "8.99"),
    ):
        with SessionLocal() as db:
            with pytest.raises(IntegrityError) as refused:
                db.execute(text(statement), {"quantity": quantity, "line": chain["ten"]})
            db.rollback()
        assert refused.value.orig.diag.constraint_name == "ck_crm_work_order_line_within_offer_quantity"
    with SessionLocal() as db:
        db.execute(text(copy_line), {"quantity": "1", "line": chain["ten"]})
        db.execute(text(shrink_line), {"quantity": "10", "line": chain["ten"]})
        db.rollback()
    with SessionLocal() as db:
        db.execute(text(shrink_line), {"quantity": "9", "line": chain["ten"]})
        db.rollback()
    assert _quantity_on_work_orders(chain["ten"]) == Decimal("9")


def test_an_offer_line_cannot_shrink_under_a_work_order_line_written_at_the_same_time(chain) -> None:
    """Review round 2: a Work Order line written but not yet committed holds the offer line's row lock, so an update
    lowering the offer line's quantity waits for it and then counts it - and is refused."""
    assert _hand_off(chain, selected_offer_line_public_ids=[chain["ten"]], selected_offer_line_quantities=_parts((chain["ten"], "6"))).status_code == 201
    outcome: list[object] = []

    def shrink() -> None:
        with SessionLocal() as db:
            try:
                db.execute(text("UPDATE crm_commercial_offer_line SET quantity = 9 WHERE line_public_id = :line"), {"line": chain["ten"]})
                outcome.append("updated")
            except IntegrityError as exc:
                outcome.append(exc.orig.diag.constraint_name)
            db.rollback()

    with SessionLocal() as writer:
        writer.execute(
            text(
                """
                INSERT INTO crm_work_order_line (work_order_line_public_id, work_order_id, commercial_offer_line_id,
                    line_number, line_status_code, scope_description, quantity, uom, currency_code, created_at, updated_at)
                SELECT gen_random_uuid(), wol.work_order_id, wol.commercial_offer_line_id, wol.line_number,
                    wol.line_status_code, wol.scope_description, 4, wol.uom, wol.currency_code, CURRENT_TIMESTAMP,
                    CURRENT_TIMESTAMP
                FROM crm_work_order_line wol JOIN crm_commercial_offer_line col ON col.id = wol.commercial_offer_line_id
                WHERE col.line_public_id = :line
                """
            ),
            {"line": chain["ten"]},
        )
        other = threading.Thread(target=shrink)
        other.start()
        other.join(timeout=2)
        assert other.is_alive(), "the update did not wait for the Work Order line holding the offer line"
        writer.commit()
    other.join(timeout=30)
    assert outcome == ["ck_crm_work_order_line_within_offer_quantity"]
    assert _quantity_on_work_orders(chain["ten"]) == Decimal("10")


def test_the_lifecycle_view_counts_every_line_against_every_work_order(chain) -> None:
    """Review rounds 1 and 2: what the Create page offers comes from the server, counted in one statement over every
    Work Order of the offer - 21 here, more than the Work Order list's 20 a page."""
    for _ in range(21):
        part = _hand_off(chain, selected_offer_line_public_ids=[chain["ten"]], selected_offer_line_quantities=_parts((chain["ten"], "0.40")))
        assert part.status_code == 201, part.text
    guidance = _guidance(chain["offer"])
    lines = {entry["offer_line_public_id"]: entry for entry in guidance["line_handoff"]}
    assert (lines[chain["ten"]]["quantity_on_work_orders"], lines[chain["ten"]]["quantity_left"]) == ("8.40", "1.60")
    assert len(lines[chain["ten"]]["work_orders"]) == 21
    assert {part["quantity"] for part in lines[chain["ten"]]["work_orders"]} == {"0.40"}
    assert (lines[chain["one"]]["quantity_on_work_orders"], lines[chain["one"]]["quantity_left"]) == ("0", "1.00")
    assert len(guidance["linked_work_orders"]) == 21
    assert guidance["work_order_handoff_available"] is True


def _related_offer(chain, purpose: str, *, work_order_public_id: str | None = None, accept: bool = True) -> str:
    body = {"offer_purpose": purpose, "customer_request_summary": f"CS-04 {purpose} test."}
    if work_order_public_id:
        body["related_work_order_public_id"] = work_order_public_id
    created = client.post(f"/api/commercial-offers/{chain['offer']}/related-offers", headers=auth_headers("sales1"), json=body)
    assert created.status_code == 201, created.text
    offer_public_id = str(created.json()["commercial_offer"]["public_id"])
    chain["offers"].insert(0, offer_public_id)
    if accept:
        _accept_offer_with_line(offer_public_id)
    return offer_public_id


def _refused_by(statement: str, values: dict) -> str:
    with SessionLocal() as db:
        with pytest.raises(IntegrityError) as refused:
            db.execute(text(statement), values)
        db.rollback()
    return refused.value.orig.diag.constraint_name


def test_a_work_order_line_comes_from_its_own_offer(chain) -> None:
    """Review round 3: a Work Order line cannot be pointed at another offer's line - a Change Quotation's included - nor
    a Work Order moved to another offer while its lines come from its own."""
    base = _hand_off(chain, selected_offer_line_public_ids=[chain["ten"]], selected_offer_line_quantities=_parts((chain["ten"], "5")))
    assert base.status_code == 201
    work_order = base.json()["work_order"]["public_id"]
    change = _related_offer(chain, "CHANGE_QUOTATION", work_order_public_id=work_order)
    supplementary = _related_offer(chain, "SUPPLEMENTARY", accept=False)
    other_line = (
        "(SELECT col.id FROM crm_commercial_offer_line col JOIN crm_commercial_offer co ON co.id = col.commercial_offer_id "
        "WHERE co.offer_public_id = :offer LIMIT 1)"
    )
    values = {"offer": change, "wo": work_order}
    assert _refused_by(
        f"UPDATE crm_work_order_line SET commercial_offer_line_id = {other_line} "
        "WHERE work_order_id = (SELECT id FROM crm_work_order WHERE work_order_public_id = :wo)",
        values,
    ) == "ck_crm_work_order_line_from_its_offer"
    assert _refused_by(
        "INSERT INTO crm_work_order_line (work_order_line_public_id, work_order_id, commercial_offer_line_id, line_number, "
        "line_status_code, scope_description, quantity, uom, currency_code, created_at, updated_at) "
        f"SELECT gen_random_uuid(), wo.id, {other_line}, 9, 'HANDOFF_CREATED', 'Moved scope', 1, 'Days', 'INR', "
        "CURRENT_TIMESTAMP, CURRENT_TIMESTAMP FROM crm_work_order wo WHERE wo.work_order_public_id = :wo",
        values,
    ) == "ck_crm_work_order_line_from_its_offer"
    assert _refused_by(
        "UPDATE crm_work_order SET commercial_offer_id = (SELECT id FROM crm_commercial_offer WHERE offer_public_id = :offer) "
        "WHERE work_order_public_id = :wo",
        {"offer": supplementary, "wo": work_order},
    ) == "ck_crm_work_order_line_from_its_offer"


def test_an_offer_with_a_work_order_cannot_become_a_change_quotation(chain) -> None:
    """Review round 3: the purpose rule held from the offer's side - directly, and against a Work Order written at the
    same time, which the change of purpose waits for and then counts."""
    supplementary = _related_offer(chain, "SUPPLEMENTARY")
    assert _hand_off(chain, supplementary).status_code == 201
    to_change_quotation = "UPDATE crm_commercial_offer SET offer_purpose = 'CHANGE_QUOTATION' WHERE offer_public_id = :offer"
    assert _refused_by(to_change_quotation, {"offer": supplementary}) == "ck_crm_work_order_not_from_change_quotation"

    second = _related_offer(chain, "SUPPLEMENTARY", accept=False)
    outcome: list[object] = []

    def change_purpose() -> None:
        with SessionLocal() as db:
            try:
                db.execute(text(to_change_quotation), {"offer": second})
                outcome.append("changed")
            except IntegrityError as exc:
                outcome.append(exc.orig.diag.constraint_name)
            db.rollback()

    with SessionLocal() as writer:
        written = writer.execute(
            text(
                "INSERT INTO crm_work_order (work_order_public_id, commercial_offer_id, opportunity_id, source_offer_status_code, "
                "customer_wo_reference) "
                "SELECT CAST(gen_random_uuid() AS VARCHAR), id, opportunity_id, 'ACCEPTED', 'LOI-RAW' FROM crm_commercial_offer "
                "WHERE offer_public_id = :offer RETURNING work_order_public_id"
            ),
            {"offer": second},
        ).scalar_one()
        chain["work_orders"].append(str(written))
        other = threading.Thread(target=change_purpose)
        other.start()
        other.join(timeout=2)
        assert other.is_alive(), "the change of purpose did not wait for the Work Order being written"
        writer.commit()
    other.join(timeout=30)
    assert outcome == ["ck_crm_work_order_not_from_change_quotation"]


def test_a_work_order_needs_the_customer_order_reference_once_per_offer(chain) -> None:
    """The owner's decision after review round 3: one customer order - its order number, or the Letter of Intent's -
    makes one Work Order. Required, refused when already on a Work Order of the offer (without case or surrounding
    spaces), and allowed on another offer: one customer order may cover a Base Offer and its Supplementary Offer."""
    for missing in ({"customer_wo_reference": None}, {"customer_wo_reference": "   "}):
        refused = _hand_off(chain, **missing)
        assert refused.status_code == 422
        assert refused.json()["detail"].startswith("Enter the customer's Work Order reference")
    first = _hand_off(chain, selected_offer_line_public_ids=[chain["one"]], customer_wo_reference="LOI/2026/17")
    assert first.status_code == 201
    code = first.json()["work_order"]["work_order_code"]
    again = _hand_off(chain, selected_offer_line_public_ids=[chain["ten"]], customer_wo_reference=" loi/2026/17")
    assert again.status_code == 409
    assert again.json()["detail"].startswith(f"Customer reference loi/2026/17 is already on {code} for this offer.")
    supplementary = _related_offer(chain, "SUPPLEMENTARY")
    assert _hand_off(chain, supplementary, customer_wo_reference="LOI/2026/17").status_code == 201
    assert _work_order_count(chain["offer"]) == 1

    # The database holds it for any writer: a Work Order written without a reference, or with this offer's again.
    copy_work_order = (
        "INSERT INTO crm_work_order (work_order_public_id, commercial_offer_id, opportunity_id, source_offer_status_code, "
        "customer_wo_reference) SELECT CAST(gen_random_uuid() AS VARCHAR), commercial_offer_id, opportunity_id, "
        "'ACCEPTED', :reference FROM crm_work_order WHERE work_order_public_id = :wo"
    )
    work_order = first.json()["work_order"]["public_id"]
    assert _refused_by(copy_work_order, {"reference": " ", "wo": work_order}) == "ck_crm_work_order_has_customer_reference"
    assert _refused_by(copy_work_order, {"reference": "LOI/2026/17 ", "wo": work_order}) == "ux_crm_work_order_customer_reference"
    assert _refused_by(
        "UPDATE crm_work_order SET customer_wo_reference = NULL WHERE work_order_public_id = :wo", {"wo": work_order}
    ) == "ck_crm_work_order_has_customer_reference"


def test_the_database_holds_the_customer_reference_when_two_writers_skip_the_offer_lock(chain, monkeypatch) -> None:
    """Both requests skip the offer lock and both find the reference unused; the unique index still lets only one
    through, and the other gets the handoff's own refusal naming the Work Order, not a server error."""
    monkeypatch.setattr(handoff, "lock_commercial_offer_row", lambda db, *, commercial_offer_public_id: 1)
    original = handoff.find_work_order_with_customer_reference
    barrier = threading.Barrier(2, timeout=30)
    waited: set[int] = set()
    guard = threading.Lock()

    def read_then_wait(db, *, commercial_offer_id, reference):
        found = original(db, commercial_offer_id=commercial_offer_id, reference=reference)
        with guard:
            first = threading.get_ident() not in waited
            waited.add(threading.get_ident())
        if first:
            barrier.wait()
        return found

    monkeypatch.setattr(handoff, "find_work_order_with_customer_reference", read_then_wait)
    results = _two_at_once(chain, ("PO-ONE", "PO-ONE"), **_three_of_ten(chain))
    assert sorted(kind for kind, _ in results) == ["created", "refused"], results
    refusal = next(value for kind, value in results if kind == "refused")
    assert isinstance(refusal, WorkOrderHandoffConflictError) and "is already on" in str(refusal), refusal
    assert isinstance(refusal.__cause__ or refusal.__context__, IntegrityError)
    assert _quantity_on_work_orders(chain["ten"]) == Decimal("3")


MOVE_OFFER_LINE = (
    "UPDATE crm_commercial_offer_line SET commercial_offer_id = (SELECT id FROM crm_commercial_offer WHERE "
    "offer_public_id = :offer) WHERE line_public_id = :line"
)
WRITE_WORK_ORDER_LINE = (
    "INSERT INTO crm_work_order_line (work_order_line_public_id, work_order_id, commercial_offer_line_id, line_number, "
    "line_status_code, scope_description, quantity, uom, currency_code, created_at, updated_at) "
    "SELECT gen_random_uuid(), wo.id, col.id, 9, 'HANDOFF_CREATED', 'Written directly', 1, 'Days', 'INR', "
    "CURRENT_TIMESTAMP, CURRENT_TIMESTAMP FROM crm_work_order wo, crm_commercial_offer_line col "
    "WHERE wo.work_order_public_id = :wo AND col.line_public_id = :line"
)


def _offer_line_race(first_sql: str, first_values: dict, second_sql: str, second_values: dict) -> list[object]:
    """The first statement left uncommitted in one session; the second, in another, must wait for it, then is refused or
    goes through."""
    outcome: list[object] = []

    def second() -> None:
        with SessionLocal() as db:
            try:
                db.execute(text(second_sql), second_values)
                outcome.append("done")
            except IntegrityError as exc:
                outcome.append(exc.orig.diag.constraint_name)
            db.rollback()

    with SessionLocal() as first:
        first.execute(text(first_sql), first_values)
        other = threading.Thread(target=second)
        other.start()
        other.join(timeout=2)
        assert other.is_alive(), "the second statement did not wait for the first"
        first.commit()
    other.join(timeout=30)
    return outcome


def test_an_offer_line_on_a_work_order_cannot_move_to_another_offer(chain) -> None:
    """Review round 4: the line-from-its-own-offer rule held from the offer line's side - directly, and against a Work
    Order line written at the same time, which the move waits for and then counts."""
    held = _hand_off(chain, selected_offer_line_public_ids=[chain["ten"]], selected_offer_line_quantities=_parts((chain["ten"], "5")))
    assert held.status_code == 201
    work_order = held.json()["work_order"]["public_id"]
    change = _related_offer(chain, "CHANGE_QUOTATION", work_order_public_id=work_order, accept=False)
    assert _refused_by(MOVE_OFFER_LINE, {"offer": change, "line": chain["ten"]}) == "ck_crm_work_order_line_from_its_offer"
    outcome = _offer_line_race(
        WRITE_WORK_ORDER_LINE, {"wo": work_order, "line": chain["one"]},
        MOVE_OFFER_LINE, {"offer": change, "line": chain["one"]},
    )
    assert outcome == ["ck_crm_work_order_line_from_its_offer"]


def test_a_work_order_line_waits_for_its_offer_line_moving_and_is_refused(chain) -> None:
    """Review round 4, the other order: an offer line not yet on a Work Order is moved to another offer and the move left
    uncommitted; a Work Order line written from it at the same time waits, then sees the line's new offer, and is
    refused."""
    held = _hand_off(chain, selected_offer_line_public_ids=[chain["ten"]], selected_offer_line_quantities=_parts((chain["ten"], "5")))
    assert held.status_code == 201
    work_order = held.json()["work_order"]["public_id"]
    change = _related_offer(chain, "CHANGE_QUOTATION", work_order_public_id=work_order, accept=False)
    outcome = _offer_line_race(
        MOVE_OFFER_LINE, {"offer": change, "line": chain["one"]},
        WRITE_WORK_ORDER_LINE, {"wo": work_order, "line": chain["one"]},
    )
    assert outcome == ["ck_crm_work_order_line_from_its_offer"]


def _migration():
    """Migration 20260908_0049's module, as Alembic loads it."""
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    return ScriptDirectory.from_config(Config("alembic.ini")).get_revision("20260908_0049").module


def test_a_blank_or_repeated_reference_means_the_application_s_whitespace() -> None:
    """Review round 5: the database's blank and duplicate comparison use exactly the whitespace the handoff strips -
    every character str.isspace() accepts - not btrim()'s spaces alone; and the migration holds the same class."""
    from app.modules.work_orders.contract import WORK_ORDER_REFERENCE_SPACE

    migration = _migration()
    assert migration.REFERENCE_SPACE == WORK_ORDER_REFERENCE_SPACE
    every_space = [chr(code) for code in range(0x110000) if chr(code).isspace()]
    pattern = f"^[{WORK_ORDER_REFERENCE_SPACE}]+$"
    with SessionLocal() as db:
        matched = db.execute(
            text("SELECT array_agg(c ~ :pattern) FROM unnest(CAST(:chars AS text[])) AS c"),
            {"pattern": pattern, "chars": every_space + ["a", "/", "0", "-", "\u200b"]},
        ).scalar_one()
    assert matched == [True] * len(every_space) + [False] * 5


def test_the_database_refuses_a_reference_of_whitespace_alone_or_one_differing_only_by_it(chain) -> None:
    """Review round 5: tabs, line breaks and other whitespace are blank to the database too, and a reference that
    differs from one already on the offer only by surrounding whitespace is the same reference."""
    first = _hand_off(chain, selected_offer_line_public_ids=[chain["one"]], customer_wo_reference="LOI/2026/18")
    assert first.status_code == 201
    copy_work_order = (
        "INSERT INTO crm_work_order (work_order_public_id, commercial_offer_id, opportunity_id, source_offer_status_code, "
        "customer_wo_reference) SELECT CAST(gen_random_uuid() AS VARCHAR), commercial_offer_id, opportunity_id, "
        "'ACCEPTED', :reference FROM crm_work_order WHERE work_order_public_id = :wo"
    )
    work_order = first.json()["work_order"]["public_id"]
    for blank in ("\t", "\n", " \r\n ", "\u00a0", "\u3000"):
        assert _refused_by(copy_work_order, {"reference": blank, "wo": work_order}) == "ck_crm_work_order_has_customer_reference"
    for same in ("\tLOI/2026/18", "loi/2026/18\n", "\u00a0LOI/2026/18\u2003"):
        assert _refused_by(copy_work_order, {"reference": same, "wo": work_order}) == "ux_crm_work_order_customer_reference"
    # And the handoff's own lookup treats them alike, naming the Work Order.
    again = _hand_off(chain, selected_offer_line_public_ids=[chain["ten"]], customer_wo_reference="\u00a0loi/2026/18\t")
    assert again.status_code == 409
    assert first.json()["work_order"]["work_order_code"] in again.json()["detail"]
    # A reference stored with surrounding whitespace by a direct write is found by the handoff's lookup too.
    with SessionLocal() as db:
        stored = db.execute(
            text(
                "INSERT INTO crm_work_order (work_order_public_id, commercial_offer_id, opportunity_id, "
                "source_offer_status_code, customer_wo_reference) SELECT CAST(gen_random_uuid() AS VARCHAR), "
                "commercial_offer_id, opportunity_id, 'ACCEPTED', :reference FROM crm_work_order "
                "WHERE work_order_public_id = :wo RETURNING work_order_public_id, "
                "COALESCE(work_order_code, CAST(work_order_public_id AS VARCHAR))"
            ),
            {"reference": "\tLOI/2026/19　", "wo": work_order},
        ).one()
        db.commit()
    chain["work_orders"].append(str(stored[0]))
    typed = _hand_off(chain, selected_offer_line_public_ids=[chain["ten"]], customer_wo_reference="LOI/2026/19")
    assert typed.status_code == 409
    assert f"is already on {stored[1]}" in typed.json()["detail"]


# What a database from before migration 20260908_0049 may hold and the migration stops on: offer CO-A's line 1
# (quantity 10) on two Work Orders for 6 and 5; offer CO-B's line 1 on a Work Order of CO-A; and on CO-A one reference
# on two Work Orders differing only by case, a tab and an ideographic space. Not stopped on: the same reference on
# another offer, and references of whitespace alone or none.
WOULD_STOP = ({("CO-A", 1)}, {("WO-6", 2, "CO-B")}, {("CO-A", "WO-1, WO-2")})


def _would_stop(db, over_quantity: str, from_another_offer: str, reference_twice: str) -> tuple[set, set, set]:
    """What three queries find on that data, held in temporary tables named as the real ones - PostgreSQL reads a
    session's temporary tables first - and dropped when the transaction ends."""
    for statement in (
        "CREATE TEMP TABLE crm_commercial_offer (id int, offer_code text) ON COMMIT DROP",
        "CREATE TEMP TABLE crm_commercial_offer_line "
        "(id int, commercial_offer_id int, line_number int, quantity numeric) ON COMMIT DROP",
        "CREATE TEMP TABLE crm_work_order (id int, commercial_offer_id int, work_order_code text, "
        "work_order_public_id uuid, customer_wo_reference text) ON COMMIT DROP",
        "CREATE TEMP TABLE crm_work_order_line "
        "(work_order_id int, commercial_offer_line_id int, line_number int, quantity numeric) ON COMMIT DROP",
        "INSERT INTO crm_commercial_offer VALUES (1, 'CO-A'), (2, 'CO-B')",
        "INSERT INTO crm_commercial_offer_line VALUES (11, 1, 1, 10), (12, 1, 2, 4), (21, 2, 1, 5)",
        "INSERT INTO crm_work_order_line VALUES (1, 11, 1, 6), (2, 11, 1, 5), (6, 12, 1, 4), (6, 21, 2, 1), (7, 21, 1, 3)",
    ):
        db.execute(text(statement))
    db.execute(
        text(
            "INSERT INTO crm_work_order VALUES "
            "(:id, :offer, 'WO-' || CAST(:id AS text), gen_random_uuid(), CAST(:reference AS text))"
        ),
        [
            {"id": 1, "offer": 1, "reference": "PO-77"},
            {"id": 2, "offer": 1, "reference": "\tpo-77　"},
            {"id": 3, "offer": 1, "reference": None},
            {"id": 4, "offer": 1, "reference": "\t"},
            {"id": 5, "offer": 1, "reference": " "},
            {"id": 6, "offer": 1, "reference": "PO-78"},
            {"id": 7, "offer": 2, "reference": "PO-77"},
            {"id": 8, "offer": 2, "reference": "   "},
        ],
    )
    return (
        {(row[0], row[1]) for row in db.execute(text(over_quantity))},
        {(row[0], row[1], row[2]) for row in db.execute(text(from_another_offer))},
        {(row[0], row[2]) for row in db.execute(text(reference_twice))},
    )


def test_the_migration_stops_on_a_reference_differing_only_by_case_or_whitespace() -> None:
    """Review round 6: the upgrade's look before it adds the rules finds what the rules would refuse - a reference
    repeated on an offer with a tab and an ideographic space around it among them - and nothing else."""
    migration = _migration()
    with SessionLocal() as db:
        try:
            found = _would_stop(
                db, migration.LINES_OVER_THEIR_QUANTITY, migration.LINES_FROM_ANOTHER_OFFER, migration.REFERENCES_USED_TWICE
            )
        finally:
            db.rollback()
    assert found == WOULD_STOP


@pytest.mark.skipif(
    not NOTE.is_file(),
    reason="docs/ is not mounted in the backend container; CI runs pytest from the checkout, where it is (or set PBL_DOCS_DIR)",
)
def test_the_note_s_pilot_checks_find_what_the_migration_stops_on() -> None:
    """Review round 6: checks 1, 4 and 5 that the package note gives the owner to run before deploying, exactly as
    printed there, find what the migration stops on - check 5 once compared with btrim() and missed a tab."""
    note = NOTE.read_text(encoding="utf-8").replace("\r\n", "\n")
    block = note.split("## Before deploying to a pilot\n", 1)[1].split("```sql\n", 1)[1].split("```", 1)[0]
    checks = dict(re.findall(r"^-- (\d)\.[^\n]*\n(.*?)(?=^-- \d\.|\Z)", block, re.M | re.S))
    assert sorted(checks) == ["1", "2", "3", "4", "5"]
    with SessionLocal() as db:
        try:
            found = _would_stop(db, checks["1"], checks["4"], checks["5"])
        finally:
            db.rollback()
    assert found == WOULD_STOP
