"""CS-05c/9F: a submitted Commercial Offer is immutable; the database holds one active Base Offer per
Opportunity; and a duplicate two requests make at once is answered with the module's own refusal, never a 500.

The owner's decisions of 9 October 2026, which close TB-1 findings TB1-301 parts (b2) and (d), TB1-304 for the offer
constraints, and the deferred "Database-level uniqueness for the one-active-Base-Offer rule":

1. A sent Commercial Offer version never changes. Its lines, pricing evidence and basis rate, T&C clauses, credit
   reviews and submission evidence are refused (422). A later Draft version receives copied commercial content and is
   edited independently. Every writer takes that version's row lock, as do abandonment and submission.
2. The database enforces the one-active-Base-Offer rule, refined by migration 20260908_0054 for preparation versions.
3. A double click is quite possible, so a duplicate the database refuses gets a clear message.
"""

from __future__ import annotations

import logging
import threading
from typing import Any, Callable
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.core.database import SessionLocal
from app.modules.commercial_offers.contract import (
    COMMERCIAL_OFFER_ACTIVE_TC_CLAUSE_INDEX,
    COMMERCIAL_OFFER_CURRENT_CREDIT_REVIEW_INDEX,
    COMMERCIAL_OFFER_INACTIVE_FOR_NEW_OFFER_STATUSES,
    COMMERCIAL_OFFER_ONE_ACTIVE_BASE_OFFER_INDEX,
    COMMERCIAL_OFFER_ONE_OPEN_BASIS_CHOICE_INDEX,
)
from app.modules.commercial_offers.repository import lock_commercial_offer_row
from app.modules.commercial_offers.schemas import (
    CommercialOfferCreditReviewCreate,
    CommercialOfferLineUpdate,
    CommercialOfferTcClauseAttachRequest,
)
from app.modules.commercial_offers.service import (
    CommercialOfferValidationError,
    abandon_commercial_offer_version,
    attach_commercial_offer_tc_clauses,
    create_commercial_offer_credit_review,
    mark_commercial_offer_submitted,
    update_commercial_offer_line,
)
from tests.offer_version_test_support import line_row_version, offer_row_version
from tests.test_commercial_offers_api import (
    auth_headers,
    cleanup_test_records,
    client,
    count_active_commercial_offer_tc_attachments,
    count_commercial_offer_business_events,
    create_account_linked_test_opportunity,
    create_test_commercial_offer,
    create_test_offer_line,
    create_test_opportunity,
    create_test_submission_evidence,
    get_seeded_tc_clause_public_id,
    mark_test_commercial_offer_submitted,
    record_test_customer_response,
)
from tooling.smoke_data.actors import resolve_actor

MAKE_NEW_VERSION = "Make a new version"
FINAL = "can no longer change"
MARKET_RATE = {
    "evidence_type": "market_rate",
    "source_name": "CS-05c Crane Vendor",
    "equipment_service_description": "80T crane day shift with operator",
    "rate_amount": "95000.00",
    "currency_code": "INR",
    "rate_basis": "per_day",
    "collected_by_name": "Operations User",
    "collected_at": "2026-08-03T10:30:00Z",
}


def _market_rate(base: str, **extra: object) -> dict[str, object]:
    """MARKET_RATE for the offer's first active line, added if it has none: every rate names an active line of its offer
    (Slice 4G)."""
    lines = [line for line in client.get(f"{base}/lines", headers=auth_headers("sales1")).json() if line["line_status_code"] == "ACTIVE"]
    line_public_id = lines[0]["public_id"] if lines else create_test_offer_line(base.rsplit("/", 1)[1])["public_id"]
    return {**MARKET_RATE, "line_public_id": str(line_public_id), **extra}


class _Records:
    def __init__(self) -> None:
        self.opportunities: list[str] = []
        self.offers: list[str] = []
        self.accounts: list[str] = []
        self.leads: list[str] = []

    def linked_offer(self) -> str:
        linked = create_account_linked_test_opportunity()
        self.leads.append(str(linked["lead"]["public_id"]))
        self.accounts.append(str(linked["account"]["public_id"]))
        self.opportunities.append(str(linked["opportunity"]["public_id"]))
        offer_public_id = str(create_test_commercial_offer(str(linked["opportunity"]["public_id"]))["public_id"])
        self.offers.append(offer_public_id)
        return offer_public_id

    def cleanup(self) -> None:
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


@pytest.fixture()
def submitted(records):
    """A submitted offer with one line, one market rate (not selected) and one T&C clause attached."""
    offer_public_id = records.linked_offer()
    base = f"/api/commercial-offers/{offer_public_id}"
    rate = client.post(f"{base}/pricing-evidence", headers=auth_headers("ops1"), json=_market_rate(base))
    assert rate.status_code == 201, rate.text
    attached = client.post(
        f"{base}/tc-clauses",
        headers=auth_headers("sales1"),
        json={"clause_public_ids": [get_seeded_tc_clause_public_id("TRANS-TC-001")]},
    )
    assert attached.status_code == 201, attached.text
    assert mark_test_commercial_offer_submitted(offer_public_id)["offer_status_code"] == "SUBMITTED"
    lines = client.get(f"{base}/lines", headers=auth_headers("sales1")).json()
    return {
        "offer": offer_public_id,
        "base": base,
        "line": str(lines[0]["public_id"]),
        "rate": str(rate.json()["pricing_evidence"]["public_id"]),
        "attachment": str(attached.json()["tc_clauses"][0]["public_id"]),
    }


def _writes(offer: dict[str, str]) -> list[tuple[str, str, Callable[[], dict[str, Any] | None]]]:
    """Every writer of the offer's content, as the page calls it: lines (add, edit, cancel), pricing evidence and the
    basis rate, T&C clauses (attach, attach the recommended ones, remove), credit reviews and submission evidence. Each
    body is made when it is sent, so a line's edit carries the line's version as it is then."""
    base = offer["base"]
    line = offer["line"]
    return [
        ("post", f"{base}/lines", lambda: {"scope_description": "Added after submission", "quantity": "1.00", "uom": "job"}),
        ("put", f"{base}/lines/{line}", lambda: {"expected_row_version": line_row_version(line), "rate_amount": "99999.00"}),
        ("post", f"{base}/pricing-evidence", lambda: _market_rate(base)),
        ("post", f"{base}/pricing-evidence/{offer['rate']}/select-basis", lambda: {"selection_reason": "After submission."}),
        ("put", f"{base}/lines/{line}", lambda: {"expected_row_version": line_row_version(line), "line_status_code": "CANCELLED"}),
        ("post", f"{base}/tc-clauses", lambda: {"clause_public_ids": [get_seeded_tc_clause_public_id("TRANS-TC-002")]}),
        ("post", f"{base}/tc-clauses/attach-recommended", lambda: {"recommendation_basis": "HIRING"}),
        ("delete", f"{base}/tc-clauses/{offer['attachment']}", lambda: None),
        ("post", f"{base}/credit-review", lambda: {"review_status": "WITHIN_LIMIT_AS_PER_MANUAL_REVIEW", "reviewed_at": "2026-07-13T10:00:00Z"}),
        ("post", f"{base}/submission-evidence", lambda: {
            "submission_reference": f"SUB-CS05C-{uuid4()}",
            "submission_channel": "EMAIL",
            "submitted_at": "2026-07-13T10:00:00Z",
        }),
    ]


def _send(method: str, url: str, body: dict[str, Any] | None | Callable[[], dict[str, Any] | None], user: str = "sales1"):
    kwargs: dict[str, Any] = {"headers": auth_headers(user)}
    made = body() if callable(body) else body
    if made is not None:
        kwargs["json"] = made
    return getattr(client, method)(url, **kwargs)


def _content(offer: dict[str, str]) -> dict[str, Any]:
    """Everything the writers write, as the reads return it."""
    base = offer["base"]
    reads = ("lines", "pricing-evidence", "tc-clauses", "credit-review", "submission-evidence")
    return {read: client.get(f"{base}/{read}", headers=auth_headers("sales1")).json() for read in reads}


def _make_version(offer: dict[str, str], records: _Records) -> dict[str, str]:
    made = client.post(
        f"{offer['base']}/versions",
        headers=auth_headers("sales1"),
        json={"version_reason": "SCOPE_CHANGE", "version_note": "Customer changed the scope."},
    )
    assert made.status_code == 201, made.text
    version = made.json()["commercial_offer"]
    version_id = str(version["public_id"])
    records.offers.append(version_id)
    base = f"/api/commercial-offers/{version_id}"
    lines = client.get(f"{base}/lines", headers=auth_headers("sales1")).json()
    rates = client.get(f"{base}/pricing-evidence", headers=auth_headers("sales1")).json()
    clauses = client.get(f"{base}/tc-clauses", headers=auth_headers("sales1")).json()
    return {
        "offer": version_id,
        "base": base,
        "line": str(lines[0]["public_id"]),
        "rate": str(rates[0]["public_id"]),
        "attachment": str(clauses[0]["public_id"]),
    }


def _actor_public_id() -> str:
    with SessionLocal() as db:
        return resolve_actor(db)["public_id"]


# --- 1. A submitted offer is immutable; changes belong to a new version -----------------------------------------


def test_a_submitted_offer_refuses_every_content_writer(submitted) -> None:
    content_before = _content(submitted)
    events_before = count_commercial_offer_business_events(submitted["offer"])

    for method, url, body in _writes(submitted):
        refused = _send(method, url, body)
        assert refused.status_code == 422, (method, url, refused.status_code, refused.text)
        detail = refused.json()["detail"]
        assert detail.startswith("This Commercial Offer is Submitted, so its lines, prices, T&C"), (method, url, detail)
        assert MAKE_NEW_VERSION in detail

    assert _content(submitted) == content_before
    assert count_commercial_offer_business_events(submitted["offer"]) == events_before


def test_a_new_version_lets_every_writer_change_its_own_draft_until_it_is_sent(submitted, records) -> None:
    version = _make_version(submitted, records)
    source_before = _content(submitted)
    for method, url, body in _writes(version):
        allowed = _send(method, url, body)
        assert allowed.status_code in (200, 201), (method, url, allowed.status_code, allowed.text)

    sent = client.post(f"{version['base']}/mark-submitted", headers=auth_headers("sales1"))
    assert sent.status_code == 200, sent.text
    assert sent.json()["commercial_offer"]["version_number"] == 2

    refused = _send("post", f"{version['base']}/lines", {"scope_description": "After sending", "quantity": "1.00", "uom": "job"})
    assert refused.status_code == 422, refused.text
    assert MAKE_NEW_VERSION in refused.json()["detail"]
    assert _content(submitted) == source_before


def test_an_abandoned_version_keeps_its_history_but_is_read_only(submitted, records) -> None:
    version = _make_version(submitted, records)
    line = _send("post", f"{version['base']}/lines", {"scope_description": "While version 2 is prepared", "quantity": "2.00", "uom": "job"})
    assert line.status_code == 201, line.text
    abandoned = client.post(f"{version['base']}/abandon-version", headers=auth_headers("sales1"))
    assert abandoned.status_code == 200, abandoned.text

    refused = _send("post", f"{version['base']}/lines", {"scope_description": "After abandonment", "quantity": "1.00", "uom": "job"})
    assert refused.status_code == 422, refused.text
    assert "can no longer change" in refused.json()["detail"]
    lines = client.get(f"{version['base']}/lines", headers=auth_headers("sales1")).json()
    assert [entry["scope_description"] for entry in lines].count("While version 2 is prepared") == 1


def test_a_final_offer_stays_refused(submitted) -> None:
    record_test_customer_response(submitted["offer"], "ACCEPTED_AWARDED", received_at="2026-07-12T09:00:00Z")
    events_before = count_commercial_offer_business_events(submitted["offer"])

    for method, url, body in _writes(submitted):
        refused = _send(method, url, body)
        assert refused.status_code == 422, (method, url, refused.status_code, refused.text)
        assert refused.json()["detail"].startswith("This Commercial Offer is Accepted") and FINAL in refused.json()["detail"]
    assert count_commercial_offer_business_events(submitted["offer"]) == events_before


def test_an_offer_before_submission_still_takes_changes(records) -> None:
    offer_public_id = records.linked_offer()
    base = f"/api/commercial-offers/{offer_public_id}"
    assert _send("post", f"{base}/lines", {"scope_description": "Draft line", "quantity": "1.00", "uom": "job"}).status_code == 201
    ready = client.put(
        base,
        headers=auth_headers("sales1"),
        json={"expected_row_version": offer_row_version(offer_public_id), "offer_status_code": "READY_FOR_REVIEW"},
    )
    assert ready.status_code == 200, ready.text
    assert _send("post", f"{base}/lines", {"scope_description": "Ready line", "quantity": "1.00", "uom": "job"}).status_code == 201
    assert _send("post", f"{base}/pricing-evidence", _market_rate(base), user="ops1").status_code == 201


# --- Races: every party takes the offer's row lock ------------------------------------------------------------


def _race(first: Callable[[], str], second: Callable[[], str], offer_public_id: str) -> list[str]:
    """Run `first` and then `second`, each in its own session, while a holder keeps the offer's row lock; each must
    wait on it. Released, they run in the order they queued. Returns their outcomes in that order."""
    outcomes: dict[str, str] = {}

    def run(name: str, work: Callable[[], str]) -> None:
        try:
            outcomes[name] = work()
        except CommercialOfferValidationError as exc:
            outcomes[name] = f"refused: {exc}"
        except Exception as exc:  # pragma: no cover - surfaced in the assertions
            outcomes[name] = f"unexpected: {type(exc).__name__}: {exc}"

    holder = SessionLocal()
    try:
        assert lock_commercial_offer_row(holder, public_id=offer_public_id) is not None
        workers = []
        for name, work in (("first", first), ("second", second)):
            worker = threading.Thread(target=run, args=(name, work), daemon=True)
            worker.start()
            worker.join(timeout=2.0)
            assert worker.is_alive(), f"{name} should wait on the offer's row lock; outcomes so far {outcomes}"
            workers.append(worker)
        holder.rollback()
    finally:
        holder.close()
    for worker in workers:
        worker.join(timeout=20.0)
        assert not worker.is_alive()
    return [outcomes["first"], outcomes["second"]]


def _mark_submitted(offer_public_id: str, actor: str) -> Callable[[], str]:
    def work() -> str:
        with SessionLocal() as db:
            mark_commercial_offer_submitted(db, public_id=UUID(offer_public_id), current_user_public_id=actor)
        return "submitted"

    return work


def _cancel_line(offer_public_id: str, line_public_id: str, actor: str) -> Callable[[], str]:
    version = line_row_version(line_public_id)

    def work() -> str:
        with SessionLocal() as db:
            update_commercial_offer_line(
                db,
                public_id=UUID(offer_public_id),
                line_public_id=UUID(line_public_id),
                payload=CommercialOfferLineUpdate(expected_row_version=version, line_status_code="CANCELLED"),
                current_user_public_id=actor,
            )
        return "line cancelled"

    return work


def _hold_credit(offer_public_id: str, actor: str) -> Callable[[], str]:
    def work() -> str:
        with SessionLocal() as db:
            create_commercial_offer_credit_review(
                db,
                public_id=UUID(offer_public_id),
                payload=CommercialOfferCreditReviewCreate(
                    review_status="REJECTED_OR_ON_HOLD", reviewed_at="2026-07-13T10:00:00Z"
                ),
                current_user_public_id=actor,
            )
        return "credit on hold"

    return work


def _offer_state(offer_public_id: str) -> tuple[str, int, str | None]:
    """The offer's status, its active lines, and its current credit review's status."""
    with SessionLocal() as db:
        return tuple(
            db.execute(
                text(
                    """
                    SELECT co.offer_status_code,
                           (SELECT COUNT(*) FROM crm_commercial_offer_line line
                            WHERE line.commercial_offer_id = co.id AND line.line_status_code = 'ACTIVE'),
                           (SELECT review.review_status FROM commercial_offer_credit_review review
                            WHERE review.commercial_offer_id = co.id AND review.active IS TRUE)
                    FROM crm_commercial_offer co WHERE co.offer_public_id = :p
                    """
                ),
                {"p": offer_public_id},
            ).one()
        )


@pytest.fixture()
def submittable(records):
    """A draft offer with an Account, one line and submission evidence, ready to be marked submitted."""
    offer_public_id = records.linked_offer()
    line = create_test_offer_line(offer_public_id)
    create_test_submission_evidence(offer_public_id)
    return {"offer": offer_public_id, "line": str(line["public_id"])}


def test_mark_submitted_first_then_a_line_cancellation_is_refused(submittable) -> None:
    """TB1-301 (d): the cancellation waits on the offer's lock; once the offer is submitted it is refused, so a submitted
    offer never ends with no active line."""
    actor = _actor_public_id()
    outcomes = _race(
        _mark_submitted(submittable["offer"], actor),
        _cancel_line(submittable["offer"], submittable["line"], actor),
        submittable["offer"],
    )
    assert outcomes[0] == "submitted"
    assert outcomes[1].startswith("refused:") and MAKE_NEW_VERSION in outcomes[1]
    assert _offer_state(submittable["offer"])[:2] == ("SUBMITTED", 1)


def test_a_line_cancellation_first_then_mark_submitted_is_refused(submittable) -> None:
    actor = _actor_public_id()
    outcomes = _race(
        _cancel_line(submittable["offer"], submittable["line"], actor),
        _mark_submitted(submittable["offer"], actor),
        submittable["offer"],
    )
    assert outcomes[0] == "line cancelled"
    assert outcomes[1].startswith("refused:") and "At least one active Commercial Offer line" in outcomes[1]
    assert _offer_state(submittable["offer"])[:2] == ("DRAFT", 0)


def test_mark_submitted_first_then_a_credit_hold_is_refused(submittable) -> None:
    actor = _actor_public_id()
    outcomes = _race(
        _mark_submitted(submittable["offer"], actor),
        _hold_credit(submittable["offer"], actor),
        submittable["offer"],
    )
    assert outcomes[0] == "submitted"
    assert outcomes[1].startswith("refused:") and MAKE_NEW_VERSION in outcomes[1]
    assert _offer_state(submittable["offer"]) == ("SUBMITTED", 1, None)


def test_a_credit_hold_first_then_mark_submitted_is_refused(submittable) -> None:
    actor = _actor_public_id()
    outcomes = _race(
        _hold_credit(submittable["offer"], actor),
        _mark_submitted(submittable["offer"], actor),
        submittable["offer"],
    )
    assert outcomes[0] == "credit on hold"
    assert outcomes[1].startswith("refused:") and "Rejected or On Hold" in outcomes[1]
    assert _offer_state(submittable["offer"]) == ("DRAFT", 1, "REJECTED_OR_ON_HOLD")


def _abandon_version(offer_public_id: str, actor: str) -> Callable[[], str]:
    def work() -> str:
        with SessionLocal() as db:
            abandon_commercial_offer_version(db, public_id=UUID(offer_public_id), current_user_public_id=actor)
        return "version abandoned"

    return work


def _attach_clause(offer_public_id: str, clause_id: str, actor: str) -> Callable[[], str]:
    clause_public_id = get_seeded_tc_clause_public_id(clause_id)

    def work() -> str:
        with SessionLocal() as db:
            attach_commercial_offer_tc_clauses(
                db,
                public_id=UUID(offer_public_id),
                payload=CommercialOfferTcClauseAttachRequest(clause_public_ids=[clause_public_id]),
                current_user_public_id=actor,
            )
        return "attached"

    return work


def test_a_change_waiting_behind_version_abandonment_is_refused(submitted, records) -> None:
    """Abandoning a version takes its row lock, so a change queued behind it reads the version as read-only."""
    actor = _actor_public_id()
    version = _make_version(submitted, records)
    outcomes = _race(
        _abandon_version(version["offer"], actor),
        _attach_clause(version["offer"], "TRANS-TC-002", actor),
        version["offer"],
    )
    assert outcomes[0] == "version abandoned"
    assert outcomes[1].startswith("refused:") and FINAL in outcomes[1]
    assert count_active_commercial_offer_tc_attachments(version["offer"]) == 1


def test_a_change_ahead_of_version_abandonment_is_kept_in_its_history(submitted, records) -> None:
    actor = _actor_public_id()
    version = _make_version(submitted, records)
    outcomes = _race(
        _attach_clause(version["offer"], "TRANS-TC-002", actor),
        _abandon_version(version["offer"], actor),
        version["offer"],
    )
    assert outcomes == ["attached", "version abandoned"]
    assert count_active_commercial_offer_tc_attachments(version["offer"]) == 2


def test_two_attaches_of_one_clause_at_once_make_one_attachment(records) -> None:
    """A double click on Attach: the second waits on the offer's lock and is told the clause is attached."""
    offer_public_id = records.linked_offer()
    actor = _actor_public_id()
    outcomes = _race(
        _attach_clause(offer_public_id, "TRANS-TC-002", actor),
        _attach_clause(offer_public_id, "TRANS-TC-002", actor),
        offer_public_id,
    )
    assert outcomes[0] == "attached"
    assert outcomes[1].startswith("refused:") and "is already attached to this Commercial Offer" in outcomes[1]
    assert count_active_commercial_offer_tc_attachments(offer_public_id) == 1


# --- 3. The database's backstop is answered, not a 500 ------------------------------------------------------------


def _behind_an_uncommitted_write(statement: str, params: dict[str, Any], request: Callable[[], Any]):
    """A writer that takes no offer lock - a direct statement - holds the duplicate uncommitted while the request runs.
    The request passes its own check (it cannot see the uncommitted row), reaches the database rule and waits; the
    writer commits; the rule refuses the request. Returns the request's response."""
    outcome: dict[str, Any] = {}

    def run() -> None:
        try:
            outcome["response"] = request()
        except Exception as exc:  # pragma: no cover - surfaced in the assertion
            outcome["error"] = exc

    writer = SessionLocal()
    try:
        assert writer.execute(text(statement), params).rowcount == 1
        worker = threading.Thread(target=run, daemon=True)
        worker.start()
        worker.join(timeout=3.0)
        assert worker.is_alive(), f"the request should wait on the database rule; it finished with {outcome}"
        writer.commit()
    finally:
        writer.close()
    worker.join(timeout=20.0)
    assert not worker.is_alive()
    assert "error" not in outcome, outcome
    return outcome["response"]


def _logged_without_the_key(caplog, constraint: str) -> None:
    lines = [record.getMessage() for record in caplog.records if "duplicate made at the same time" in record.getMessage()]
    assert len(lines) == 1, lines
    assert f"constraint={constraint}" in lines[0] and "sqlstate=23505" in lines[0]
    # Never the database's own text: its DETAIL line repeats the duplicated key.
    assert "Key (" not in lines[0] and "DETAIL" not in lines[0] and "already exists" not in lines[0]


# A complete basis choice made by a writer that takes no offer lock (Slice 4G, review 4G-R1-003): the line's open choice,
# with its reason, which is all a line's basis is.
THEIR_CHOICE = (
    "INSERT INTO crm_commercial_offer_line_basis_choice (choice_public_id, commercial_offer_line_id, pricing_evidence_id, "
    "selection_reason, chosen_at) SELECT :c, pe.commercial_offer_line_id, pe.id, 'Theirs.', CURRENT_TIMESTAMP "
    "FROM crm_commercial_offer_pricing_evidence pe WHERE pe.evidence_public_id = :p"
)


def _the_basis_is_theirs(base: str, first: str) -> None:
    rows = client.get(f"{base}/pricing-evidence", headers=auth_headers("ops1")).json()
    assert [row["public_id"] for row in rows if row["is_selected_basis"]] == [first]
    [winner] = [row for row in rows if row["public_id"] == first]
    assert winner["selection_reason"] == "Theirs."
    assert [choice["is_current"] for choice in winner["basis_history"]] == [True]


def test_a_basis_rate_selected_at_the_same_time_is_answered_409(records, caplog) -> None:
    offer_public_id = records.linked_offer()
    base = f"/api/commercial-offers/{offer_public_id}"
    first, second = (
        client.post(f"{base}/pricing-evidence", headers=auth_headers("ops1"), json=_market_rate(base)).json()["pricing_evidence"]["public_id"]
        for _ in range(2)
    )
    headers = auth_headers("ops1")
    caplog.set_level(logging.WARNING)

    response = _behind_an_uncommitted_write(
        THEIR_CHOICE,
        {"c": str(uuid4()), "p": str(first)},
        lambda: client.post(f"{base}/pricing-evidence/{second}/select-basis", headers=headers, json={"selection_reason": "Mine."}),
    )

    assert response.status_code == 409, response.text
    assert response.json()["detail"].startswith("Someone else chose a basis rate for this line at the same time")
    _the_basis_is_theirs(base, str(first))
    _logged_without_the_key(caplog, COMMERCIAL_OFFER_ONE_OPEN_BASIS_CHOICE_INDEX)


def test_a_selected_market_rate_added_at_the_same_time_is_answered_409(records) -> None:
    offer_public_id = records.linked_offer()
    base = f"/api/commercial-offers/{offer_public_id}"
    first = client.post(f"{base}/pricing-evidence", headers=auth_headers("ops1"), json=_market_rate(base)).json()["pricing_evidence"]["public_id"]
    headers = auth_headers("ops1")
    events_before = count_commercial_offer_business_events(offer_public_id)

    response = _behind_an_uncommitted_write(
        THEIR_CHOICE,
        {"c": str(uuid4()), "p": str(first)},
        lambda: client.post(
            f"{base}/pricing-evidence",
            headers=headers,
            json=_market_rate(base, is_selected_basis=True, selection_reason="Mine."),
        ),
    )

    assert response.status_code == 409, response.text
    assert len(client.get(f"{base}/pricing-evidence", headers=headers).json()) == 1
    _the_basis_is_theirs(base, str(first))
    assert count_commercial_offer_business_events(offer_public_id) == events_before


def test_two_basis_choices_through_the_offer_lock_are_taken_in_turn_and_both_kept(records) -> None:
    """Two writers that both take the offer's lock (Slice 4G): the second waits for the first, then replaces its choice;
    the line keeps both, the first ended and the second current."""
    offer_public_id = records.linked_offer()
    base = f"/api/commercial-offers/{offer_public_id}"
    first, second = (
        client.post(f"{base}/pricing-evidence", headers=auth_headers("ops1"), json=_market_rate(base)).json()["pricing_evidence"]["public_id"]
        for _ in range(2)
    )
    headers = auth_headers("sales1")
    outcome: dict[str, Any] = {}

    def run() -> None:
        outcome["response"] = client.post(
            f"{base}/pricing-evidence/{second}/select-basis", headers=headers, json={"selection_reason": "Second."}
        )

    writer = SessionLocal()
    try:
        assert lock_commercial_offer_row(writer, public_id=offer_public_id) is not None
        writer.execute(text(THEIR_CHOICE), {"c": str(uuid4()), "p": str(first)})
        worker = threading.Thread(target=run, daemon=True)
        worker.start()
        worker.join(timeout=3.0)
        assert worker.is_alive(), "the second choice should wait for the offer's lock"
        writer.commit()
    finally:
        writer.close()
    worker.join(timeout=20.0)
    assert not worker.is_alive()
    assert outcome["response"].status_code == 200, outcome["response"].text
    assert outcome["response"].json()["previous_basis_rate_public_id"] == str(first)

    rows = {row["public_id"]: row for row in client.get(f"{base}/pricing-evidence", headers=headers).json()}
    assert rows[str(second)]["is_selected_basis"] and not rows[str(first)]["is_selected_basis"]
    [ended] = rows[str(first)]["basis_history"]
    assert ended["selection_reason"] == "Theirs." and ended["ended_at"] is not None and not ended["is_current"]
    [current] = rows[str(second)]["basis_history"]
    assert current["selection_reason"] == "Second." and current["is_current"]


def test_a_credit_review_recorded_at_the_same_time_is_answered_409(records, caplog) -> None:
    offer_public_id = records.linked_offer()
    base = f"/api/commercial-offers/{offer_public_id}"
    for status in ("NOT_ASSESSED", "APPROVAL_REQUIRED"):  # the second supersedes the first
        assert _send("post", f"{base}/credit-review", {"review_status": status, "reviewed_at": "2026-07-10T10:00:00Z"}).status_code == 201
    reviews = client.get(f"{base}/credit-review", headers=auth_headers("sales1")).json()
    older = next(review["public_id"] for review in reviews if review["review_status"] == "NOT_ASSESSED")
    with SessionLocal() as db:  # no review current, so the writer below can make the older one current again
        db.execute(
            text(
                "UPDATE commercial_offer_credit_review SET active = FALSE "
                "WHERE commercial_offer_id = (SELECT id FROM crm_commercial_offer WHERE offer_public_id = :p)"
            ),
            {"p": offer_public_id},
        )
        db.commit()
    headers = auth_headers("sales1")
    caplog.set_level(logging.WARNING)

    response = _behind_an_uncommitted_write(
        "UPDATE commercial_offer_credit_review SET active = TRUE WHERE public_id = :p",
        {"p": str(older)},
        lambda: client.post(
            f"{base}/credit-review",
            headers=headers,
            json={"review_status": "WITHIN_LIMIT_AS_PER_MANUAL_REVIEW", "reviewed_at": "2026-07-13T10:00:00Z"},
        ),
    )

    assert response.status_code == 409, response.text
    assert response.json()["detail"].startswith("Someone else recorded a credit review for this Commercial Offer at the same time")
    assert len(client.get(f"{base}/credit-review", headers=headers).json()) == 2
    _logged_without_the_key(caplog, COMMERCIAL_OFFER_CURRENT_CREDIT_REVIEW_INDEX)


def test_a_clause_attached_at_the_same_time_is_answered_as_already_attached(records, caplog) -> None:
    offer_public_id = records.linked_offer()
    base = f"/api/commercial-offers/{offer_public_id}"
    clause = get_seeded_tc_clause_public_id("TRANS-TC-002")
    attached = _send("post", f"{base}/tc-clauses", {"clause_public_ids": [clause]})
    attachment = attached.json()["tc_clauses"][0]["public_id"]
    assert _send("delete", f"{base}/tc-clauses/{attachment}", None).status_code == 200
    headers = auth_headers("sales1")
    caplog.set_level(logging.WARNING)

    response = _behind_an_uncommitted_write(
        "UPDATE commercial_offer_tc_clause SET active = TRUE WHERE public_id = :p",
        {"p": str(attachment)},
        lambda: client.post(f"{base}/tc-clauses", headers=headers, json={"clause_public_ids": [clause]}),
    )

    assert response.status_code == 422, response.text
    assert response.json()["detail"] == "T&C clause TRANS-TC-002 is already attached to this Commercial Offer."
    assert count_active_commercial_offer_tc_attachments(offer_public_id) == 1
    _logged_without_the_key(caplog, COMMERCIAL_OFFER_ACTIVE_TC_CLAUSE_INDEX)


def test_a_base_offer_made_active_at_the_same_time_is_answered_with_the_check_s_refusal(records, caplog) -> None:
    opportunity_public_id = str(create_test_opportunity()["public_id"])
    records.opportunities.append(opportunity_public_id)
    withdrawn = create_test_commercial_offer(opportunity_public_id)
    records.offers.append(str(withdrawn["public_id"]))
    put = client.put(
        f"/api/commercial-offers/{withdrawn['public_id']}",
        headers=auth_headers("sales1"),
        json={"expected_row_version": offer_row_version(withdrawn["public_id"]), "offer_status_code": "WITHDRAWN"},
    )
    assert put.status_code == 200, put.text
    headers = auth_headers("sales1")
    caplog.set_level(logging.WARNING)
    body = {"opportunity_public_id": opportunity_public_id, "offer_title": "CS-05c second Base Offer"}

    response = _behind_an_uncommitted_write(
        "UPDATE crm_commercial_offer SET offer_status_code = 'DRAFT' WHERE offer_public_id = :p",
        {"p": str(withdrawn["public_id"])},
        lambda: client.post("/api/commercial-offers", headers=headers, json=body),
    )

    assert response.status_code == 422, response.text
    detail = response.json()["detail"]
    assert detail.startswith("An active/actionable Commercial Offer already exists for this Opportunity.")
    assert str(withdrawn["offer_code"]) in detail
    _logged_without_the_key(caplog, COMMERCIAL_OFFER_ONE_ACTIVE_BASE_OFFER_INDEX)
    with SessionLocal() as db:
        assert db.execute(
            text(
                "SELECT COUNT(*) FROM crm_commercial_offer co JOIN crm_opportunity o ON o.id = co.opportunity_id "
                "WHERE o.opportunity_public_id = :p"
            ),
            {"p": opportunity_public_id},
        ).scalar_one() == 1


def test_a_database_error_on_another_rule_is_not_answered_as_a_duplicate() -> None:
    """Only the named rules are answered; anything else is raised as it came, for the server's own handler."""
    from app.modules.commercial_offers.services.common import _refuse_duplicate

    class _Diag:
        constraint_name = "some_other_rule"

    class _Orig(Exception):
        diag = _Diag()

    error = IntegrityError("INSERT ...", {}, _Orig())
    with pytest.raises(IntegrityError) as raised:
        _refuse_duplicate(error, {COMMERCIAL_OFFER_ACTIVE_TC_CLAUSE_INDEX: lambda: CommercialOfferValidationError("x")})
    assert raised.value is error


# --- 2. The database holds one active Base Offer per Opportunity (migration 20260908_0053) ------------------------


def _migration(revision: str = "20260908_0054"):
    """A Commercial Offer migration module, as Alembic loads it."""
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    return ScriptDirectory.from_config(Config("alembic.ini")).get_revision(revision).module


def test_the_index_holds_exactly_the_service_s_rule() -> None:
    migration = _migration()
    assert _migration("20260908_0053").INACTIVE_STATUSES == ("WITHDRAWN", "REJECTED", "CLOSED")
    assert migration.ACTIVE_BASE_INDEX == COMMERCIAL_OFFER_ONE_ACTIVE_BASE_OFFER_INDEX
    assert migration.INACTIVE_STATUSES == COMMERCIAL_OFFER_INACTIVE_FOR_NEW_OFFER_STATUSES
    with SessionLocal() as db:
        definition = db.execute(
            text("SELECT indexdef FROM pg_indexes WHERE tablename = 'crm_commercial_offer' AND indexname = :name"),
            {"name": COMMERCIAL_OFFER_ONE_ACTIVE_BASE_OFFER_INDEX},
        ).scalar_one()
    assert definition.startswith("CREATE UNIQUE INDEX") and "(opportunity_id)" in definition
    assert "offer_purpose)::text = 'BASE'" in definition
    assert "previous_version_offer_id IS NULL" in definition
    for status in COMMERCIAL_OFFER_INACTIVE_FOR_NEW_OFFER_STATUSES:
        assert f"'{status}'" in definition


_COPY_OFFER = (
    "INSERT INTO crm_commercial_offer (offer_public_id, opportunity_id, offer_status_code, offer_purpose, base_offer_id) "
    "SELECT CAST(gen_random_uuid() AS VARCHAR), opportunity_id, :status, CAST(:purpose AS VARCHAR), "
    "CASE WHEN CAST(:purpose AS VARCHAR) = 'BASE' THEN NULL ELSE id END FROM crm_commercial_offer WHERE offer_public_id = :p"
)


def _refused_by(statement: str, params: dict[str, Any]) -> str | None:
    with SessionLocal() as db:
        try:
            db.execute(text(statement), params)
            return None
        except IntegrityError as exc:
            return getattr(getattr(exc.orig, "diag", None), "constraint_name", None)
        finally:
            db.rollback()


def test_the_database_refuses_a_second_active_base_offer_and_nothing_else(records) -> None:
    opportunity_public_id = str(create_test_opportunity()["public_id"])
    records.opportunities.append(opportunity_public_id)
    offer = create_test_commercial_offer(opportunity_public_id)
    records.offers.append(str(offer["public_id"]))
    params = {"p": str(offer["public_id"])}

    for active in ("DRAFT", "READY_FOR_REVIEW", "SUBMITTED", "ACCEPTED"):
        assert _refused_by(_COPY_OFFER, {**params, "status": active, "purpose": "BASE"}) == COMMERCIAL_OFFER_ONE_ACTIVE_BASE_OFFER_INDEX
    for inactive in COMMERCIAL_OFFER_INACTIVE_FOR_NEW_OFFER_STATUSES:
        assert _refused_by(_COPY_OFFER, {**params, "status": inactive, "purpose": "BASE"}) is None
    for related in ("SUPPLEMENTARY", "CHANGE_QUOTATION"):
        assert _refused_by(_COPY_OFFER, {**params, "status": "DRAFT", "purpose": related}) is None


# What a database from before migration 20260908_0053 may hold, in temporary tables named as the real ones - PostgreSQL
# reads a session's temporary tables first - dropped when the transaction ends: OPP-A with a Draft and an Accepted Base
# Offer (a Withdrawn one beside them); OPP-B with one Base Offer and an active Supplementary Offer; OPP-C with a Revised
# and a Submitted one; OPP-D with one active Base Offer and a Rejected and a Closed one.
_BEFORE_THE_MIGRATION = (
    "CREATE TEMP TABLE crm_opportunity (id int, opportunity_name text, opportunity_public_id text) ON COMMIT DROP",
    "CREATE TEMP TABLE crm_commercial_offer (id int, opportunity_id int, offer_code text, offer_public_id text, "
    "offer_purpose text, offer_status_code text) ON COMMIT DROP",
    "INSERT INTO crm_opportunity VALUES (1, 'OPP-A', 'a-1'), (2, 'OPP-B', 'b-2'), (3, 'OPP-C', 'c-3'), (4, 'OPP-D', 'd-4')",
    "INSERT INTO crm_commercial_offer VALUES "
    "(10, 1, 'CO-10', 'p10', 'BASE', 'DRAFT'), (11, 1, 'CO-11', 'p11', 'BASE', 'WITHDRAWN'), "
    "(12, 1, NULL, 'p12', 'BASE', 'ACCEPTED'), "
    "(20, 2, 'CO-20', 'p20', 'BASE', 'SUBMITTED'), (21, 2, 'CO-21', 'p21', 'SUPPLEMENTARY', 'DRAFT'), "
    "(30, 3, 'CO-30', 'p30', 'BASE', 'REVISED'), (31, 3, 'CO-31', 'p31', 'BASE', 'SUBMITTED'), "
    "(40, 4, 'CO-40', 'p40', 'BASE', 'READY_FOR_REVIEW'), (41, 4, 'CO-41', 'p41', 'BASE', 'REJECTED'), "
    "(42, 4, 'CO-42', 'p42', 'BASE', 'CLOSED')",
)


def test_the_migration_stops_on_an_opportunity_with_two_active_base_offers_and_names_them() -> None:
    migration = _migration("20260908_0053")
    with SessionLocal() as db:
        try:
            for statement in _BEFORE_THE_MIGRATION:
                db.execute(text(statement))
            stopped = migration.refusal(db.connection())
        finally:
            db.rollback()
    assert stopped is not None and stopped.startswith("20260908_0053 stopped, changing nothing")
    assert "Opportunity OPP-A (a-1) has CO-10 (DRAFT), p12 (ACCEPTED)" in stopped
    assert "Opportunity OPP-C (c-3) has CO-30 (REVISED), CO-31 (SUBMITTED)" in stopped
    assert "OPP-B" not in stopped and "OPP-D" not in stopped and "CO-11" not in stopped
