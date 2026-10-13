"""CS-05a (TB-1 finding TB1-303, the offer part): a stale form can no longer overwrite a Commercial Offer or an offer
line.

Before, two people with the same offer or line open saved over each other without a word: the second save wrote every
field the first had changed, the offer's status and prices included, and a line's amount could be neither user's
quantity times rate. Now each edit carries the `row_version` the screen loaded, compared under the offer's row lock;
any other is refused with 409 and nothing is written. Every write of the offer's row - an edit, marking it submitted,
a customer response that sets its status - and every edit of a line raises its version, and the response returns it.
A line's amount is computed from the line as locked for the write.
"""

from __future__ import annotations

import ast
import re
import threading
from decimal import Decimal
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.core.database import SessionLocal
from app.modules.commercial_offers.contract import (
    COMMERCIAL_OFFER_EVENT_LINE_UPDATED,
    COMMERCIAL_OFFER_EVENT_UPDATED,
)
from app.modules.commercial_offers.repository import lock_commercial_offer_row
from app.modules.commercial_offers.schemas import CommercialOfferLineUpdate, CommercialOfferUpdate
from app.modules.commercial_offers.service import (
    CommercialOfferConflictError,
    update_commercial_offer,
    update_commercial_offer_line,
)
from tests.offer_version_test_support import line_row_version, offer_row_version
from tests.test_commercial_offers_api import (
    auth_headers,
    cleanup_test_records,
    client,
    count_commercial_offer_business_events_by_name,
    create_account_linked_test_opportunity,
    create_test_commercial_offer,
    create_test_opportunity,
    create_test_submission_evidence,
)
from tooling.smoke_data.actors import resolve_actor

OFFER_CONFLICT = "Someone else changed this Commercial Offer after you opened it, so your change was not saved."
LINE_CONFLICT = "Someone else changed this Commercial Offer line after you opened it, so your change was not saved."


@pytest.fixture()
def draft_offer():
    """A draft offer with one line: quantity 2, rate 1000."""
    opportunity_public_ids: list[str] = []
    offer_public_ids: list[str] = []
    try:
        opportunity = create_test_opportunity()
        opportunity_public_ids.append(str(opportunity["public_id"]))
        offer = create_test_commercial_offer(str(opportunity["public_id"]))
        offer_public_ids.append(str(offer["public_id"]))
        line = client.post(
            f"/api/commercial-offers/{offer['public_id']}/lines",
            headers=auth_headers(),
            json={"scope_description": "CS-05a crane", "quantity": "2.00", "uom": "day", "rate_amount": "1000.00"},
        )
        assert line.status_code == 201, line.text
        yield {"offer": offer, "line": line.json()["offer_line"]}
    finally:
        cleanup_test_records(opportunity_public_ids=opportunity_public_ids, offer_public_ids=offer_public_ids)


@pytest.fixture()
def submittable_offer():
    """A draft offer with an Account, a line and submission evidence, ready to be marked submitted."""
    opportunity_public_ids: list[str] = []
    offer_public_ids: list[str] = []
    account_public_ids: list[str] = []
    lead_public_ids: list[str] = []
    try:
        linked = create_account_linked_test_opportunity()
        lead_public_ids.append(str(linked["lead"]["public_id"]))
        account_public_ids.append(str(linked["account"]["public_id"]))
        opportunity_public_ids.append(str(linked["opportunity"]["public_id"]))
        offer = create_test_commercial_offer(str(linked["opportunity"]["public_id"]))
        offer_public_ids.append(str(offer["public_id"]))
        line = client.post(
            f"/api/commercial-offers/{offer['public_id']}/lines",
            headers=auth_headers(),
            json={"scope_description": "CS-05a crane", "quantity": "1.00", "uom": "job"},
        )
        assert line.status_code == 201, line.text
        evidence = create_test_submission_evidence(str(offer["public_id"]))
        yield {"offer": offer, "line": line.json()["offer_line"], "evidence": evidence}
    finally:
        cleanup_test_records(
            opportunity_public_ids=opportunity_public_ids,
            offer_public_ids=offer_public_ids,
            account_public_ids=account_public_ids,
            lead_public_ids=lead_public_ids,
        )


def _offer_url(offer: dict) -> str:
    return f"/api/commercial-offers/{offer['public_id']}"


def _line_url(offer: dict, line: dict) -> str:
    return f"/api/commercial-offers/{offer['public_id']}/lines/{line['public_id']}"


def _offer_row(public_id: object) -> dict:
    with SessionLocal() as db:
        return dict(
            db.execute(
                text(
                    "SELECT offer_title, remarks, offer_value, offer_status_code, row_version "
                    "FROM crm_commercial_offer WHERE offer_public_id = :p"
                ),
                {"p": str(public_id)},
            ).one()._mapping
        )


def _line_row(public_id: object) -> dict:
    with SessionLocal() as db:
        return dict(
            db.execute(
                text(
                    "SELECT quantity, rate_amount, line_amount, remarks, row_version "
                    "FROM crm_commercial_offer_line WHERE line_public_id = :p"
                ),
                {"p": str(public_id)},
            ).one()._mapping
        )


def _actor_public_id() -> str:
    with SessionLocal() as db:
        return resolve_actor(db)["public_id"]


# --- The database (migration 20260908_0051) -------------------------------------------------------------------


def test_every_offer_and_line_starts_at_version_one_and_never_below_it(draft_offer) -> None:
    assert draft_offer["offer"]["row_version"] == 1
    assert draft_offer["line"]["row_version"] == 1
    assert client.get(_offer_url(draft_offer["offer"]), headers=auth_headers()).json()["row_version"] == 1
    listed = client.get(f"{_offer_url(draft_offer['offer'])}/lines", headers=auth_headers()).json()
    assert [line["row_version"] for line in listed] == [1]
    for table, key, public_id in (
        ("crm_commercial_offer", "offer_public_id", draft_offer["offer"]["public_id"]),
        ("crm_commercial_offer_line", "line_public_id", draft_offer["line"]["public_id"]),
    ):
        with SessionLocal() as db, pytest.raises(IntegrityError, match="row_version"):
            db.execute(text(f"UPDATE {table} SET row_version = 0 WHERE {key} = :p"), {"p": public_id})


# --- The offer's edit -------------------------------------------------------------------------------------------


def test_a_save_raises_the_version_and_returns_it(draft_offer) -> None:
    offer = draft_offer["offer"]
    saved = client.put(_offer_url(offer), headers=auth_headers(), json={"expected_row_version": 1, "remarks": "First."})
    assert saved.status_code == 200, saved.text
    body = saved.json()
    assert body["commercial_offer"]["row_version"] == 2
    updated_event = next(event for event in body["events"] if event["event_name"] == COMMERCIAL_OFFER_EVENT_UPDATED)
    assert updated_event["event_payload"]["row_version"] == 2
    again = client.put(_offer_url(offer), headers=auth_headers(), json={"expected_row_version": 2, "remarks": "Second."})
    assert again.status_code == 200, again.text
    assert again.json()["commercial_offer"]["row_version"] == 3


def test_a_save_from_a_form_opened_before_someone_elses_is_refused_and_changes_nothing(draft_offer) -> None:
    """Two tabs open at version 1. The first saves a new title; the second, still at version 1, saves remarks and is
    refused, so nothing it sent is written - and the first save's title stands."""
    offer = draft_offer["offer"]
    first = client.put(
        _offer_url(offer), headers=auth_headers(), json={"expected_row_version": 1, "offer_title": "Title from tab one"}
    )
    assert first.status_code == 200, first.text
    events_before = count_commercial_offer_business_events_by_name(str(offer["public_id"]), COMMERCIAL_OFFER_EVENT_UPDATED)

    stale = client.put(
        _offer_url(offer),
        headers=auth_headers("manager1"),
        json={"expected_row_version": 1, "remarks": "From tab two", "offer_value": "1.00"},
    )

    assert stale.status_code == 409, stale.text
    assert stale.json()["detail"].startswith(OFFER_CONFLICT)
    assert "Reload the page" in stale.json()["detail"]
    row = _offer_row(offer["public_id"])
    assert row["offer_title"] == "Title from tab one"
    assert row["remarks"] == offer["remarks"]
    assert row["offer_value"] == Decimal(str(offer["offer_value"]))
    assert row["row_version"] == 2
    assert count_commercial_offer_business_events_by_name(
        str(offer["public_id"]), COMMERCIAL_OFFER_EVENT_UPDATED
    ) == events_before


def test_a_stale_save_is_refused_before_its_content_is_judged(draft_offer) -> None:
    """A stale form whose values pass the request schema is told to reload, not that they break a rule of an offer
    it no longer sees (the contract's order of checks: the version before the rules about the values)."""
    offer = draft_offer["offer"]
    assert client.put(_offer_url(offer), headers=auth_headers(), json={"expected_row_version": 1, "remarks": "x"}).status_code == 200
    stale = client.put(
        _offer_url(offer), headers=auth_headers(), json={"expected_row_version": 1, "offer_status_code": "ACCEPTED"}
    )
    assert stale.status_code == 409, stale.text


def test_a_request_the_schema_refuses_is_refused_whatever_its_version(draft_offer) -> None:
    """The contract's order of checks: what the request schema declares - here a negative offer value and a quantity
    of zero - is refused (422) before the record is read, stale or not, and nothing is written. Corrected, the same
    stale save is then 409."""
    offer, line = draft_offer["offer"], draft_offer["line"]
    assert client.put(_offer_url(offer), headers=auth_headers(), json={"expected_row_version": 1, "remarks": "x"}).status_code == 200
    assert client.put(_line_url(offer, line), headers=auth_headers(), json={"expected_row_version": 1, "remarks": "x"}).status_code == 200
    offer_events = count_commercial_offer_business_events_by_name(str(offer["public_id"]), COMMERCIAL_OFFER_EVENT_UPDATED)
    line_events = count_commercial_offer_business_events_by_name(str(offer["public_id"]), COMMERCIAL_OFFER_EVENT_LINE_UPDATED)

    for url, body in (
        (_offer_url(offer), {"expected_row_version": 1, "offer_value": "-1.00"}),
        (_line_url(offer, line), {"expected_row_version": 1, "quantity": "0"}),
    ):
        refused = client.put(url, headers=auth_headers(), json=body)
        assert refused.status_code == 422, refused.text
        assert isinstance(refused.json()["detail"], list), refused.text  # FastAPI's validation list, not a rule's text

    assert client.put(_offer_url(offer), headers=auth_headers(), json={"expected_row_version": 1, "offer_value": "1.00"}).status_code == 409
    assert client.put(_line_url(offer, line), headers=auth_headers(), json={"expected_row_version": 1, "quantity": "3"}).status_code == 409
    assert _offer_row(offer["public_id"])["row_version"] == 2
    assert _offer_row(offer["public_id"])["offer_value"] == Decimal(str(offer["offer_value"]))
    assert (_line_row(line["public_id"])["row_version"], _line_row(line["public_id"])["quantity"]) == (2, Decimal("2.00"))
    assert count_commercial_offer_business_events_by_name(str(offer["public_id"]), COMMERCIAL_OFFER_EVENT_UPDATED) == offer_events
    assert count_commercial_offer_business_events_by_name(
        str(offer["public_id"]), COMMERCIAL_OFFER_EVENT_LINE_UPDATED
    ) == line_events


def test_a_stale_line_save_on_a_final_offer_is_told_the_offer_is_final(submittable_offer) -> None:
    """The contract's order of checks for a line: an Accepted offer's content cannot change at all (TB1-301 (b)), and
    that is said before the version - reloading would not help."""
    offer, line = submittable_offer["offer"], submittable_offer["line"]
    assert client.post(f"{_offer_url(offer)}/mark-submitted", headers=auth_headers()).status_code == 200
    accepted = client.post(
        f"{_offer_url(offer)}/customer-responses",
        headers=auth_headers(),
        json={
            "response_outcome": "ACCEPTED_AWARDED",
            "response_channel": "EMAIL",
            "response_received_at": "2026-07-12T10:00:00Z",
            "response_reference": f"CS05A-{uuid4()}",
        },
    )
    assert accepted.status_code == 201, accepted.text

    stale = client.put(_line_url(offer, line), headers=auth_headers(), json={"expected_row_version": 7, "remarks": "x"})

    assert stale.status_code == 422, stale.text
    assert "can no longer change" in stale.json()["detail"]
    assert _line_row(line["public_id"])["row_version"] == 1


def test_a_version_ahead_of_the_offer_is_refused_too(draft_offer) -> None:
    ahead = client.put(_offer_url(draft_offer["offer"]), headers=auth_headers(), json={"expected_row_version": 7, "remarks": "x"})
    assert ahead.status_code == 409, ahead.text
    assert _offer_row(draft_offer["offer"]["public_id"])["row_version"] == 1


@pytest.mark.parametrize("body", [{"remarks": "No version"}, {"expected_row_version": 0, "remarks": "x"}, {"expected_row_version": None}])
def test_a_save_without_a_version_is_refused(draft_offer, body) -> None:
    response = client.put(_offer_url(draft_offer["offer"]), headers=auth_headers(), json=body)
    assert response.status_code == 422, response.text
    assert _offer_row(draft_offer["offer"]["public_id"])["row_version"] == 1


def test_a_version_alone_is_not_a_change(draft_offer) -> None:
    response = client.put(_offer_url(draft_offer["offer"]), headers=auth_headers(), json={"expected_row_version": 1})
    assert response.status_code == 422, response.text
    assert "At least one Commercial Offer field" in response.json()["detail"]
    assert _offer_row(draft_offer["offer"]["public_id"])["row_version"] == 1


def test_marking_submitted_raises_the_version_so_a_form_opened_before_is_refused(submittable_offer) -> None:
    """A tab opened while the offer was a draft offers Withdrawn; once someone else has marked it submitted, its save
    must not withdraw the submitted offer unseen."""
    offer = submittable_offer["offer"]
    opened_at = offer_row_version(offer["public_id"])
    submitted = client.post(f"{_offer_url(offer)}/mark-submitted", headers=auth_headers())
    assert submitted.status_code == 200, submitted.text
    assert submitted.json()["commercial_offer"]["row_version"] == opened_at + 1

    stale = client.put(
        _offer_url(offer), headers=auth_headers(), json={"expected_row_version": opened_at, "offer_status_code": "WITHDRAWN"}
    )
    assert stale.status_code == 409, stale.text
    assert _offer_row(offer["public_id"])["offer_status_code"] == "SUBMITTED"


def test_a_customer_response_that_sets_the_status_raises_the_version_and_one_that_does_not_leaves_it(
    submittable_offer,
) -> None:
    offer = submittable_offer["offer"]
    assert client.post(f"{_offer_url(offer)}/mark-submitted", headers=auth_headers()).status_code == 200
    submitted_at = offer_row_version(offer["public_id"])

    def respond(outcome: str) -> dict:
        response = client.post(
            f"{_offer_url(offer)}/customer-responses",
            headers=auth_headers(),
            json={
                "response_outcome": outcome,
                "response_channel": "EMAIL",
                "response_received_at": "2026-07-12T10:00:00Z",
                "response_reference": f"CS05A-{uuid4()}",
                "response_notes": "CS-05a",
            },
        )
        assert response.status_code == 201, response.text
        return response.json()

    respond("CLARIFICATION_REQUESTED")
    assert offer_row_version(offer["public_id"]) == submitted_at
    accepted = respond("ACCEPTED_AWARDED")
    assert accepted["commercial_offer"]["row_version"] == submitted_at + 1
    stale = client.put(
        _offer_url(offer), headers=auth_headers(), json={"expected_row_version": submitted_at, "remarks": "Stale"}
    )
    assert stale.status_code == 409, stale.text


def test_two_saves_from_the_same_version_at_once_make_one_change(draft_offer) -> None:
    """Both wait on the offer's row lock; the first through raises the version, so the second is refused."""
    offer_public_id = str(draft_offer["offer"]["public_id"])
    actor_public_id = _actor_public_id()
    outcomes: list[str] = []
    guard = threading.Lock()

    def save(remarks: str) -> None:
        with SessionLocal() as db:
            try:
                update_commercial_offer(
                    db,
                    public_id=UUID(offer_public_id),
                    payload=CommercialOfferUpdate(expected_row_version=1, remarks=remarks),
                    current_user_public_id=actor_public_id,
                )
                result = "saved"
            except CommercialOfferConflictError:
                result = "conflict"
            except Exception as exc:  # pragma: no cover - surfaced in the assertion below
                result = f"unexpected: {type(exc).__name__}: {exc}"
        with guard:
            outcomes.append(result)

    holder = SessionLocal()
    try:
        assert lock_commercial_offer_row(holder, public_id=offer_public_id) is not None
        workers = [threading.Thread(target=save, args=(f"Tab {n}",), daemon=True) for n in (1, 2)]
        for worker in workers:
            worker.start()
        for worker in workers:
            worker.join(timeout=2.0)
            assert worker.is_alive(), f"each save should wait on the offer's row lock; outcomes so far {outcomes}"
        holder.rollback()
    finally:
        holder.close()
    for worker in workers:
        worker.join(timeout=15.0)
        assert not worker.is_alive()

    assert sorted(outcomes) == ["conflict", "saved"], outcomes
    assert _offer_row(offer_public_id)["row_version"] == 2


# --- A line's edit ----------------------------------------------------------------------------------------------


def test_a_line_save_raises_its_version_and_returns_it(draft_offer) -> None:
    offer, line = draft_offer["offer"], draft_offer["line"]
    saved = client.put(_line_url(offer, line), headers=auth_headers(), json={"expected_row_version": 1, "rate_amount": "1500.00"})
    assert saved.status_code == 200, saved.text
    body = saved.json()
    assert body["offer_line"]["row_version"] == 2
    assert Decimal(body["offer_line"]["line_amount"]) == Decimal("3000.00")
    assert body["event"]["event_payload"]["row_version"] == 2
    # A line's save is not a write of the offer's row.
    assert offer_row_version(offer["public_id"]) == 1


def test_a_line_save_from_a_form_opened_before_someone_elses_is_refused(draft_offer) -> None:
    """TB1-303's own case: one user changes only the quantity, another - with the line open since before - only the
    rate. The second is refused; before, it stored an amount that was neither user's quantity times rate."""
    offer, line = draft_offer["offer"], draft_offer["line"]
    first = client.put(_line_url(offer, line), headers=auth_headers(), json={"expected_row_version": 1, "quantity": "5.00"})
    assert first.status_code == 200, first.text
    events_before = count_commercial_offer_business_events_by_name(str(offer["public_id"]), COMMERCIAL_OFFER_EVENT_LINE_UPDATED)

    stale = client.put(
        _line_url(offer, line), headers=auth_headers("manager1"), json={"expected_row_version": 1, "rate_amount": "9.00"}
    )

    assert stale.status_code == 409, stale.text
    assert stale.json()["detail"].startswith(LINE_CONFLICT)
    row = _line_row(line["public_id"])
    assert (row["quantity"], row["rate_amount"], row["line_amount"], row["row_version"]) == (
        Decimal("5.00"),
        Decimal("1000.00"),
        Decimal("5000.00"),
        2,
    )
    assert count_commercial_offer_business_events_by_name(
        str(offer["public_id"]), COMMERCIAL_OFFER_EVENT_LINE_UPDATED
    ) == events_before


def test_a_line_save_without_a_version_is_refused(draft_offer) -> None:
    response = client.put(_line_url(draft_offer["offer"], draft_offer["line"]), headers=auth_headers(), json={"remarks": "x"})
    assert response.status_code == 422, response.text
    assert _line_row(draft_offer["line"]["public_id"])["row_version"] == 1


def test_a_line_amount_is_computed_from_the_line_it_writes(draft_offer) -> None:
    """A writer outside the edit route changes the line's quantity and holds its row while a rate-only edit runs. The
    edit reads the line locked, so it waits and computes the amount from the quantity it then writes over - never from
    the quantity it would have read before that writer committed."""
    offer_public_id = str(draft_offer["offer"]["public_id"])
    line_public_id = str(draft_offer["line"]["public_id"])
    actor_public_id = _actor_public_id()
    outcome: dict[str, object] = {}

    def rate_only_edit() -> None:
        with SessionLocal() as db:
            try:
                saved = update_commercial_offer_line(
                    db,
                    public_id=UUID(offer_public_id),
                    line_public_id=UUID(line_public_id),
                    payload=CommercialOfferLineUpdate(expected_row_version=1, rate_amount=Decimal("100.00")),
                    current_user_public_id=actor_public_id,
                )
                outcome["result"] = "saved"
                outcome["line_amount"] = saved.offer_line.line_amount
            except Exception as exc:  # pragma: no cover - surfaced in the assertion below
                outcome["result"] = f"unexpected: {type(exc).__name__}: {exc}"

    writer = SessionLocal()
    try:
        writer.execute(
            text("UPDATE crm_commercial_offer_line SET quantity = 7 WHERE line_public_id = :p"), {"p": line_public_id}
        )
        worker = threading.Thread(target=rate_only_edit, daemon=True)
        worker.start()
        worker.join(timeout=2.0)
        assert worker.is_alive(), f"the edit should wait on the line's row; it finished with {outcome}"
        writer.commit()
    finally:
        writer.close()
    worker.join(timeout=15.0)
    assert not worker.is_alive()

    assert outcome.get("result") == "saved", outcome
    row = _line_row(line_public_id)
    assert row["quantity"] == Decimal("7.00")
    assert row["line_amount"] == row["quantity"] * row["rate_amount"] == Decimal("700.00")
    assert outcome["line_amount"] == Decimal("700.00")


# --- Every write of the two rows raises the version ---------------------------------------------------------------


_TABLES = ("crm_commercial_offer", "crm_commercial_offer_line")
_APP_ROOT = Path(__file__).resolve().parents[1] / "app"


def _table_name_constants(sources: dict[Path, str]) -> set[str]:
    """Every module-level name in the application bound to either table's name, whatever it is called."""
    names: set[str] = set()
    for source in sources.values():
        for node in ast.parse(source).body:
            targets = node.targets if isinstance(node, ast.Assign) else [node.target] if isinstance(node, ast.AnnAssign) else []
            value = getattr(node, "value", None)
            if isinstance(value, ast.Constant) and value.value in _TABLES:
                names |= {target.id for target in targets if isinstance(target, ast.Name)}
    return names


def _writers(sources: dict[Path, str]) -> list[tuple[str, str, str]]:
    """(where, the function's source, the text from the UPDATE on) for every UPDATE of either table in a function,
    found by the table's name or by any constant bound to it, in any letter case."""
    names = sorted(_table_name_constants(sources))
    targets = "|".join([*(rf"\{{{re.escape(name)}\}}" for name in names), r"crm_commercial_offer(?:_line)?\b"])
    update = re.compile(rf"\bUPDATE\s+(?:ONLY\s+)?(?:{targets})", re.IGNORECASE)
    found: list[tuple[str, str, str]] = []
    for path, source in sources.items():
        for node in ast.walk(ast.parse(source)):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            body = ast.get_source_segment(source, node) or ""
            for match in update.finditer(body):
                found.append((f"{path.relative_to(_APP_ROOT).as_posix()}::{node.name}", body, body[match.start():]))
    return found


def test_every_application_write_of_an_offer_or_a_line_raises_its_version() -> None:
    """A later writer that forgot the version would let a stale form overwrite its change unseen. Each function in the
    application that updates either table - named directly or through any constant bound to its name - must raise
    row_version; the one exception is the offer code a new offer is given straight after its insert."""
    sources = {path: path.read_text(encoding="utf-8-sig") for path in sorted(_APP_ROOT.rglob("*.py"))}
    assert _table_name_constants(sources) == {"COMMERCIAL_OFFER_TABLE", "COMMERCIAL_OFFER_LINE_TABLE"}
    writers = _writers(sources)

    # The offer's write, a line's write, and the new offer's code - so a scan that found nothing cannot pass.
    assert sorted(where for where, _, _ in writers) == [
        "modules/commercial_offers/repository.py::insert_commercial_offer",
        "modules/commercial_offers/repository.py::update_commercial_offer_by_public_id",
        "modules/commercial_offers/repository.py::update_commercial_offer_line_by_public_id",
    ], writers
    for where, function_source, statement_onwards in writers:
        if where.endswith("::insert_commercial_offer"):
            assert re.match(r"UPDATE\s+\{COMMERCIAL_OFFER_TABLE\}\s+SET\s+offer_code\s*=", statement_onwards), where
            continue
        assert '"row_version = row_version + 1"' in function_source, where


def test_the_writer_scan_finds_a_writer_however_it_names_the_table() -> None:
    """The scan above is only as good as what it can see: a writer in lower case, through another constant, or with
    ONLY is found too."""
    sources = {
        _APP_ROOT / "modules" / "planted.py": (
            'OFFERS = "crm_commercial_offer"\n'
            "def lower_case(db):\n    db.execute('update crm_commercial_offer_line set remarks = null')\n"
            "def through_another_constant(db):\n    db.execute(f'UPDATE {OFFERS} SET remarks = NULL')\n"
            "def with_only(db):\n    db.execute('UPDATE ONLY crm_commercial_offer SET remarks = NULL')\n"
            "def another_table(db):\n    db.execute('UPDATE crm_commercial_offer_revision SET remarks = NULL')\n"
        )
    }
    assert sorted(where for where, _, _ in _writers(sources)) == [
        "modules/planted.py::lower_case",
        "modules/planted.py::through_another_constant",
        "modules/planted.py::with_only",
    ]


def test_no_orm_model_maps_an_offer_or_a_line() -> None:
    """The application writes these tables only through the SQL the scan reads; an ORM model would be a writer the
    scan cannot see."""
    import app.models_metadata  # noqa: F401 - registers every model on Base.metadata
    from app.core.database import Base

    assert not set(_TABLES) & set(Base.metadata.tables)
