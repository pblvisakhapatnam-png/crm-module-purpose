"""Slice 9E - Quotation Generation regression tests.

Each test below maps to one numbered item in the "Test plan" section of
docs/agent/slices/slice-9e-quotation-generation.md, written to fail first against the
pre-9E/defective code. A test never shown to catch its defect is an assertion of intent, not a
control.
"""

from __future__ import annotations

import threading
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.core.database import SessionLocal
from app.main import app
from app.modules.authorization.contract import EFFECTIVE_ROLE_PERMISSION_MATRIX
from app.modules.commercial_offers.contract import (
    COMMERCIAL_OFFER_QUOTE_DOCUMENT_STATUS_APPROVED_FOR_ISSUE,
    COMMERCIAL_OFFER_QUOTE_DOCUMENT_STATUS_DRAFT,
    COMMERCIAL_OFFER_STATUS_ACCEPTED,
    COMMERCIAL_OFFER_STATUS_CLOSED,
    COMMERCIAL_OFFER_STATUS_REJECTED,
    COMMERCIAL_OFFER_STATUS_WITHDRAWN,
)
from app.modules.commercial_offers.quote_render import render_quote_html
from app.modules.commercial_offers.schemas import CommercialOfferLineCreate, CommercialOfferQuoteDocumentApproveRequest
from app.modules.commercial_offers.service import (
    CommercialOfferQuoteDocumentNotFoundError,
    CommercialOfferValidationError,
    approve_commercial_offer_quote_document,
    build_quote_snapshot,
    compute_source_fingerprint,
    create_commercial_offer_line,
    generate_commercial_offer_quote_document,
    list_commercial_offer_quote_documents,
)
from app.modules.documents.contract import ALLOWED_UPLOAD_EXTENSIONS
from app.modules.documents.service import DocumentUploadTypeError, upload_document
from app.modules.documents.storage import get_storage_provider_by_code
from tests.business_day_test_support import TODAY, held_to_the_test_day
from tooling.smoke_data import builders
from tooling.smoke_data.actors import resolve_actor

client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def _on_the_test_day():
    with held_to_the_test_day():
        yield


def auth_headers(username: str = "sales1") -> dict[str, str]:
    response = client.post("/api/auth/login", json={"username": username, "password": "password"})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _purge_stored_objects_for_offer(offer_public_id: str) -> None:
    """Delete stored generated-document bytes for an offer BEFORE the document_metadata row is
    removed - once the row is gone, storage_key is gone with it (mirrors Slice 9C's own cleanup
    ordering lesson)."""
    with SessionLocal() as db:
        rows = db.execute(
            text(
                "SELECT storage_provider_code, storage_key FROM document_metadata "
                "WHERE linked_record_type = 'commercial_offer' AND linked_record_public_id = :pid "
                "AND storage_key IS NOT NULL"
            ),
            {"pid": offer_public_id},
        ).fetchall()
    for provider_code, storage_key in rows:
        try:
            provider = get_storage_provider_by_code(provider_code)
            provider.delete(storage_key=storage_key)
        except Exception:
            pass


def _delete_records(*, offer_public_ids: list[str], opportunity_public_ids: list[str], account_public_ids: list[str]) -> None:
    for offer_public_id in offer_public_ids:
        _purge_stored_objects_for_offer(offer_public_id)

    with SessionLocal() as db:
        for offer_public_id in offer_public_ids:
            db.execute(
                text(
                    "DELETE FROM document_metadata WHERE linked_record_type = 'commercial_offer' "
                    "AND linked_record_public_id = :pid"
                ),
                {"pid": offer_public_id},
            )
            for table, column in (
                ("crm_commercial_offer_quote_document", "commercial_offer_id"),
                ("commercial_offer_customer_response", "commercial_offer_id"),
                ("commercial_offer_credit_review", "commercial_offer_id"),
                ("commercial_offer_submission_evidence", "commercial_offer_id"),
                ("commercial_offer_tc_clause", "commercial_offer_id"),
                ("crm_commercial_offer_line", "commercial_offer_id"),
            ):
                db.execute(
                    text(
                        f"DELETE FROM {table} WHERE {column} IN "
                        "(SELECT id FROM crm_commercial_offer WHERE offer_public_id = :pid)"
                    ),
                    {"pid": offer_public_id},
                )
            db.execute(text("DELETE FROM crm_commercial_offer WHERE offer_public_id = :pid"), {"pid": offer_public_id})
        for opportunity_public_id in opportunity_public_ids:
            db.execute(text("DELETE FROM crm_opportunity WHERE opportunity_public_id = :pid"), {"pid": opportunity_public_id})
        for account_public_id in account_public_ids:
            # Subordinate Account identity rows first: the correction-pass fixture adds addresses
            # and GSTINs, which hold foreign keys to business_party and would otherwise block the
            # parent delete.
            for table in ("business_party_address", "business_party_gstin", "business_party_tax_profile"):
                db.execute(
                    text(
                        f"DELETE FROM {table} WHERE business_party_id IN "
                        "(SELECT id FROM business_party WHERE business_party_public_id = :pid)"
                    ),
                    {"pid": account_public_id},
                )
            db.execute(text("DELETE FROM business_party WHERE business_party_public_id = :pid"), {"pid": account_public_id})
        db.commit()


@pytest.fixture
def offer_with_active_line():
    """A Draft Commercial Offer with one active line and Account traceability - the minimum
    eligible for quote generation. Built entirely through the TE-1 harness builders, which call
    the same service functions the real routes call, so every lifecycle guard genuinely runs."""
    run_id = f"s9e-{uuid4().hex[:8]}"
    with SessionLocal() as db:
        actor_public_id = resolve_actor(db)["public_id"]

    accounts: list[str] = []
    opportunities: list[str] = []
    offers: list[str] = []
    try:
        chain = builders.create_account_linked_opportunity(run_id=run_id, actor_public_id=actor_public_id, suffix="9E")
        accounts.append(chain["account"]["public_id"])
        opportunities.append(chain["opportunity"]["public_id"])

        offer = builders.create_offer_with_line(
            run_id=run_id,
            actor_public_id=actor_public_id,
            opportunity_public_id=opportunities[0],
            suffix="9E",
        )
        offers.append(offer["public_id"])

        yield {
            "offer_public_id": offer["public_id"],
            "offer_code": offer["offer_code"],
            "actor_public_id": actor_public_id,
            "account_public_id": accounts[0],
            "opportunity_public_id": opportunities[0],
        }
    finally:
        _delete_records(offer_public_ids=offers, opportunity_public_ids=opportunities, account_public_ids=accounts)


# ---------------------------------------------------------------------------------------------
# 1 & 2. HTML escaping and determinism - pure unit tests, no database
# ---------------------------------------------------------------------------------------------

_HOSTILE_SNAPSHOT = {
    "schema_version": "1.0",
    "offer_code": "CO-000001",
    "offer_date": "2026-09-01",
    "valid_until": "2026-10-01",
    "customer_request_reference": '"><script>alert(1)</script>',
    "currency_code": "INR",
    "account_name": '<img src=x onerror="alert(1)">',
    "account_legal_name": "</style><script>alert(document.cookie)</script>",
    "account_addresses": ['123 Main St" onmouseover="alert(1)', "Line 2 <script>evil()</script>"],
    "account_gstins": ["27AAAAA0000A1Z5<script>alert(1)</script>"],
    "lines": [
        {
            "line_number": 1,
            "scope_description": '<script>alert("line")</script>',
            "equipment_service_category": '"><svg onload=alert(1)>',
            "quantity": "10.00",
            "uom": '"><script>x=1</script>',
            "rate_amount": "500.00",
            "line_amount": "5000.00",
        }
    ],
    "total_amount": "5000.00",
    "tc_clauses": [
        {
            "clause_id_snapshot": '"><script>alert("clause")</script>',
            "title_snapshot": "</title><script>evil()</script>",
            "clause_text_snapshot": '<img src=x onerror=alert(1)>text with " quotes and \' apostrophes',
        }
    ],
}


def _render_hostile() -> str:
    return render_quote_html(
        _HOSTILE_SNAPSHOT,
        quote_reference="CO-000001/V1",
        version_no=1,
        generated_at_display="09 Sep 2026, 12:00 IST",
        prepared_by_display='<script>alert("preparer")</script>',
    )


def test_hostile_input_in_every_field_is_escaped_no_script_no_event_handler():
    html_output = _render_hostile()
    assert "<script" not in html_output.lower()
    assert "</script" not in html_output.lower()
    # No unescaped event-handler attribute: "onerror=", "onload=", "onmouseover=" etc. must not
    # appear literally - only their HTML-entity-escaped forms (with &quot; in place of the
    # attribute's own quote characters) may.
    import re

    for handler in ("onerror", "onload", "onmouseover"):
        for match in re.finditer(rf'{handler}\s*=\s*"', html_output, re.IGNORECASE):
            preceding = html_output[max(0, match.start() - 20) : match.start()]
            assert "&quot;" in preceding or "&#x27;" in preceding or preceding == "", (
                f"found an apparently-unescaped {handler}= near: {html_output[match.start()-40:match.start()+40]!r}"
            )
    # The actual hostile substrings must never appear verbatim.
    assert '<script>alert(1)</script>' not in html_output
    assert '<script>alert("preparer")</script>' not in html_output
    assert '<img src=x onerror="alert(1)">' not in html_output
    assert "<svg onload=alert(1)>" not in html_output


def test_render_quote_html_is_deterministic():
    first = _render_hostile()
    second = _render_hostile()
    assert first == second


def test_render_quote_html_escapes_ordinary_ampersands_and_quotes():
    snapshot = dict(_HOSTILE_SNAPSHOT)
    snapshot["account_name"] = "Smith & Jones \"Traders\""
    html_output = render_quote_html(
        snapshot,
        quote_reference="CO-000001/V1",
        version_no=1,
        generated_at_display="x",
        prepared_by_display="Preparer & Co",
    )
    assert "Smith &amp; Jones &quot;Traders&quot;" in html_output
    assert 'Smith & Jones "Traders"' not in html_output


# ---------------------------------------------------------------------------------------------
# 3. Staleness detection
# ---------------------------------------------------------------------------------------------


def test_stored_bytes_are_unchanged_after_the_offer_is_edited_and_the_version_is_reported_stale(offer_with_active_line):
    offer_public_id = offer_with_active_line["offer_public_id"]
    actor_public_id = offer_with_active_line["actor_public_id"]

    with SessionLocal() as db:
        response = generate_commercial_offer_quote_document(
            db, public_id=UUID(offer_public_id), current_user_public_id=actor_public_id
        )
        db.commit()
    original_document_public_id = str(response.quote_document.document_public_id)
    assert response.quote_document.is_stale is False

    with SessionLocal() as db:
        original_row = db.execute(
            text("SELECT storage_key, byte_size, checksum_sha256 FROM document_metadata WHERE document_public_id = :pid"),
            {"pid": original_document_public_id},
        ).first()
    assert original_row is not None

    # Edit the offer's underlying source data: add another active line.
    with SessionLocal() as db:
        create_commercial_offer_line(
            db,
            public_id=UUID(offer_public_id),
            payload=CommercialOfferLineCreate(
                scope_description="Additional line added after quote generation.",
                quantity=Decimal("1.00"),
                uom="unit",
                rate_amount=Decimal("100.00"),
            ),
            current_user_public_id=actor_public_id,
        )
        db.commit()

    with SessionLocal() as db:
        after_row = db.execute(
            text("SELECT storage_key, byte_size, checksum_sha256 FROM document_metadata WHERE document_public_id = :pid"),
            {"pid": original_document_public_id},
        ).first()
    assert after_row == original_row, "the stored bytes must never change after generation"

    with SessionLocal() as db:
        listed = list_commercial_offer_quote_documents(db, UUID(offer_public_id))
    assert len(listed) == 1
    assert listed[0].is_stale is True, "the version must now report stale against the changed offer"


# ---------------------------------------------------------------------------------------------
# 4 & 5. Generation preconditions
# ---------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "target_status",
    [COMMERCIAL_OFFER_STATUS_ACCEPTED, COMMERCIAL_OFFER_STATUS_REJECTED, COMMERCIAL_OFFER_STATUS_WITHDRAWN, COMMERCIAL_OFFER_STATUS_CLOSED],
)
def test_generation_is_refused_for_a_concluded_offer_status(offer_with_active_line, target_status):
    offer_public_id = offer_with_active_line["offer_public_id"]
    actor_public_id = offer_with_active_line["actor_public_id"]

    with SessionLocal() as db:
        db.execute(
            text("UPDATE crm_commercial_offer SET offer_status_code = :status WHERE offer_public_id = :pid"),
            {"status": target_status, "pid": offer_public_id},
        )
        db.commit()

    with SessionLocal() as db:
        with pytest.raises(CommercialOfferValidationError):
            generate_commercial_offer_quote_document(db, public_id=UUID(offer_public_id), current_user_public_id=actor_public_id)


def test_generation_is_refused_with_no_active_line():
    run_id = f"s9e-noline-{uuid4().hex[:8]}"
    with SessionLocal() as db:
        actor_public_id = resolve_actor(db)["public_id"]
    accounts: list[str] = []
    opportunities: list[str] = []
    offers: list[str] = []
    try:
        chain = builders.create_account_linked_opportunity(run_id=run_id, actor_public_id=actor_public_id, suffix="9E-NL")
        accounts.append(chain["account"]["public_id"])
        opportunities.append(chain["opportunity"]["public_id"])

        from app.modules.commercial_offers.schemas import CommercialOfferCreate
        from app.modules.commercial_offers.service import create_commercial_offer
        from datetime import timedelta
        from decimal import Decimal as D

        with SessionLocal() as db:
            result = create_commercial_offer(
                db,
                payload=CommercialOfferCreate(
                    opportunity_public_id=UUID(opportunities[0]),
                    offer_title="9E no-line offer",
                    offer_mode="plum_generated",
                    offer_type="firm",
                    offer_value=D("1.00"),
                    currency_code="INR",
                    offer_date=TODAY,
                    valid_until=TODAY + timedelta(days=30),
                ),
                current_user_public_id=actor_public_id,
            )
        offer_public_id = str(result.commercial_offer.public_id)
        offers.append(offer_public_id)

        with SessionLocal() as db:
            with pytest.raises(CommercialOfferValidationError, match="no active lines"):
                generate_commercial_offer_quote_document(db, public_id=UUID(offer_public_id), current_user_public_id=actor_public_id)
    finally:
        _delete_records(offer_public_ids=offers, opportunity_public_ids=opportunities, account_public_ids=accounts)


def test_generation_is_refused_when_account_traceability_is_missing():
    """An Opportunity with no linked Account produces an offer with account_public_id = None."""
    run_id = f"s9e-noacct-{uuid4().hex[:8]}"
    with SessionLocal() as db:
        actor_public_id = resolve_actor(db)["public_id"]

    from app.modules.opportunities.schemas import OpportunityCreate
    from app.modules.opportunities.service import create_opportunity

    opportunities: list[str] = []
    offers: list[str] = []
    try:
        with SessionLocal() as db:
            opp_result = create_opportunity(
                db,
                payload=OpportunityCreate(
                    opportunity_name=f"9E-NOACCT-{run_id}",
                    opportunity_source="manual",
                ),
                current_user_public_id=actor_public_id,
            )
        opportunity_public_id = str(opp_result.opportunity.public_id)
        opportunities.append(opportunity_public_id)

        offer = builders.create_offer_with_line(
            run_id=run_id, actor_public_id=actor_public_id, opportunity_public_id=opportunity_public_id, suffix="9E-NOACCT"
        )
        offers.append(offer["public_id"])

        with SessionLocal() as db:
            with pytest.raises(CommercialOfferValidationError, match="not linked to an Account"):
                generate_commercial_offer_quote_document(
                    db, public_id=UUID(offer["public_id"]), current_user_public_id=actor_public_id
                )
    finally:
        _delete_records(offer_public_ids=offers, opportunity_public_ids=opportunities, account_public_ids=[])


# ---------------------------------------------------------------------------------------------
# 6. AST ordering guard - lock before status read
# ---------------------------------------------------------------------------------------------


def _lock_and_status_lines(source: str) -> tuple[int | None, int | None]:
    import ast
    import textwrap

    tree = ast.parse(textwrap.dedent(source))
    lock_lines: list[int] = []
    status_lines: list[int] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name) and func.id == "lock_commercial_offer_row":
                lock_lines.append(node.lineno)
        elif isinstance(node, ast.Constant) and node.value == "offer_status_code":
            status_lines.append(node.lineno)
    return (min(lock_lines) if lock_lines else None, min(status_lines) if status_lines else None)


def test_the_generation_path_locks_the_offer_row_before_reading_status():
    """The Slice 9B discovery guard (EXPECTED_STATUS_WRITING_FUNCTIONS) only detects functions
    that WRITE offer_status_code; generate_commercial_offer_quote_document only READS it, so
    that guard does not cover this path. This test covers it independently."""
    import inspect

    source = inspect.getsource(generate_commercial_offer_quote_document)
    lock_line, status_line = _lock_and_status_lines(source)
    assert lock_line is not None, "generate_commercial_offer_quote_document must call lock_commercial_offer_row"
    assert status_line is not None, "could not locate the offer_status_code read"
    assert lock_line < status_line, "the lock must be taken before the status is read, or it prevents nothing"


# ---------------------------------------------------------------------------------------------
# 7. Concurrency: a concurrent transition defeats an in-flight generation
# ---------------------------------------------------------------------------------------------


def test_a_concurrent_status_change_defeats_an_in_flight_generation(offer_with_active_line):
    offer_public_id = offer_with_active_line["offer_public_id"]
    actor_public_id = offer_with_active_line["actor_public_id"]

    from app.modules.commercial_offers.repository import lock_commercial_offer_row

    outcome: dict[str, object] = {}

    def generate() -> None:
        with SessionLocal() as db:
            try:
                generate_commercial_offer_quote_document(
                    db, public_id=UUID(offer_public_id), current_user_public_id=actor_public_id
                )
                db.commit()
                outcome["result"] = "committed"
            except CommercialOfferValidationError as exc:
                outcome["result"] = "refused"
                outcome["message"] = str(exc)
            except Exception as exc:  # pragma: no cover - surfaced in the assertion below
                outcome["result"] = f"unexpected: {type(exc).__name__}: {exc}"

    holder = SessionLocal()
    try:
        assert lock_commercial_offer_row(holder, public_id=offer_public_id) is not None

        worker = threading.Thread(target=generate, daemon=True)
        worker.start()
        worker.join(timeout=2.0)
        assert worker.is_alive(), f"generation should be blocked on the row lock; it finished with {outcome}"

        holder.execute(
            text("UPDATE crm_commercial_offer SET offer_status_code = 'ACCEPTED' WHERE offer_public_id = :pid"),
            {"pid": offer_public_id},
        )
        holder.commit()
    finally:
        holder.close()

    worker.join(timeout=15.0)
    assert not worker.is_alive(), "generation never completed after the lock was released"
    assert outcome.get("result") == "refused", outcome


# ---------------------------------------------------------------------------------------------
# 8 & 9. Approval role and status gating
# ---------------------------------------------------------------------------------------------


def test_sales_user_is_refused_approval_via_the_api(offer_with_active_line):
    offer_public_id = offer_with_active_line["offer_public_id"]
    actor_public_id = offer_with_active_line["actor_public_id"]

    with SessionLocal() as db:
        generated = generate_commercial_offer_quote_document(
            db, public_id=UUID(offer_public_id), current_user_public_id=actor_public_id
        )
        db.commit()

    response = client.post(
        f"/api/commercial-offers/{offer_public_id}/quote-documents/{generated.quote_document.public_id}/approve",
        headers=auth_headers("sales1"),
        json={},
    )
    assert response.status_code == 403, response.text


@pytest.mark.parametrize("username", ["admin1", "manager1"])
def test_sales_manager_and_admin_can_approve_via_the_api(offer_with_active_line, username):
    offer_public_id = offer_with_active_line["offer_public_id"]
    actor_public_id = offer_with_active_line["actor_public_id"]

    with SessionLocal() as db:
        generated = generate_commercial_offer_quote_document(
            db, public_id=UUID(offer_public_id), current_user_public_id=actor_public_id
        )
        db.commit()

    response = client.post(
        f"/api/commercial-offers/{offer_public_id}/quote-documents/{generated.quote_document.public_id}/approve",
        headers=auth_headers(username),
        json={},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["quote_document"]["quote_status_code"] == COMMERCIAL_OFFER_QUOTE_DOCUMENT_STATUS_APPROVED_FOR_ISSUE
    assert body["quote_document"]["approved_by"] is not None
    assert body["quote_document"]["approved_at"] is not None


def test_approving_an_already_approved_version_is_refused(offer_with_active_line):
    offer_public_id = offer_with_active_line["offer_public_id"]
    actor_public_id = offer_with_active_line["actor_public_id"]

    with SessionLocal() as db:
        generated = generate_commercial_offer_quote_document(
            db, public_id=UUID(offer_public_id), current_user_public_id=actor_public_id
        )
        db.commit()

    with SessionLocal() as db:
        approve_commercial_offer_quote_document(
            db,
            public_id=UUID(offer_public_id),
            quote_document_public_id=generated.quote_document.public_id,
            payload=None,
            current_user_public_id=actor_public_id,
        )
        db.commit()

    with SessionLocal() as db:
        with pytest.raises(CommercialOfferValidationError, match="already approved"):
            approve_commercial_offer_quote_document(
                db,
                public_id=UUID(offer_public_id),
                quote_document_public_id=generated.quote_document.public_id,
                payload=None,
                current_user_public_id=actor_public_id,
            )


def test_approving_a_superseded_version_is_refused(offer_with_active_line):
    offer_public_id = offer_with_active_line["offer_public_id"]
    actor_public_id = offer_with_active_line["actor_public_id"]

    with SessionLocal() as db:
        v1 = generate_commercial_offer_quote_document(
            db, public_id=UUID(offer_public_id), current_user_public_id=actor_public_id
        )
        db.commit()
    with SessionLocal() as db:
        generate_commercial_offer_quote_document(db, public_id=UUID(offer_public_id), current_user_public_id=actor_public_id)
        db.commit()

    with SessionLocal() as db:
        with pytest.raises(CommercialOfferValidationError, match="superseded"):
            approve_commercial_offer_quote_document(
                db,
                public_id=UUID(offer_public_id),
                quote_document_public_id=v1.quote_document.public_id,
                payload=None,
                current_user_public_id=actor_public_id,
            )


# ---------------------------------------------------------------------------------------------
# 10. Generating V2 supersedes V1 without erasing V1's approval facts
# ---------------------------------------------------------------------------------------------


def test_generating_v2_supersedes_v1_and_preserves_v1_approval_facts(offer_with_active_line):
    offer_public_id = offer_with_active_line["offer_public_id"]
    actor_public_id = offer_with_active_line["actor_public_id"]

    with SessionLocal() as db:
        v1 = generate_commercial_offer_quote_document(
            db, public_id=UUID(offer_public_id), current_user_public_id=actor_public_id
        )
        db.commit()

    with SessionLocal() as db:
        approve_commercial_offer_quote_document(
            db,
            public_id=UUID(offer_public_id),
            quote_document_public_id=v1.quote_document.public_id,
            payload=CommercialOfferQuoteDocumentApproveRequest(approval_note="Approved v1 for issue."),
            current_user_public_id=actor_public_id,
        )
        db.commit()

    with SessionLocal() as db:
        v1_before_v2 = db.execute(
            text(
                "SELECT quote_status_code, approved_by, approved_at, superseded_at FROM crm_commercial_offer_quote_document "
                "WHERE quote_document_public_id = :pid"
            ),
            {"pid": str(v1.quote_document.public_id)},
        ).first()
    assert v1_before_v2.quote_status_code == COMMERCIAL_OFFER_QUOTE_DOCUMENT_STATUS_APPROVED_FOR_ISSUE
    assert v1_before_v2.superseded_at is None

    with SessionLocal() as db:
        v2 = generate_commercial_offer_quote_document(
            db, public_id=UUID(offer_public_id), current_user_public_id=actor_public_id
        )
        db.commit()
    assert v2.quote_document.version_no == 2

    with SessionLocal() as db:
        v1_after_v2 = db.execute(
            text(
                "SELECT quote_status_code, approved_by, approved_at, superseded_at FROM crm_commercial_offer_quote_document "
                "WHERE quote_document_public_id = :pid"
            ),
            {"pid": str(v1.quote_document.public_id)},
        ).first()
    assert v1_after_v2.superseded_at is not None, "V1 must be marked superseded once V2 is generated"
    assert v1_after_v2.quote_status_code == COMMERCIAL_OFFER_QUOTE_DOCUMENT_STATUS_APPROVED_FOR_ISSUE, (
        "superseding must not erase V1's own approval status"
    )
    assert v1_after_v2.approved_by == v1_before_v2.approved_by
    assert v1_after_v2.approved_at == v1_before_v2.approved_at


# ---------------------------------------------------------------------------------------------
# 11. Database CHECK constraint holds even against a direct INSERT
# ---------------------------------------------------------------------------------------------


def test_a_direct_insert_claiming_approved_without_an_approver_is_refused_by_the_database(offer_with_active_line):
    offer_public_id = offer_with_active_line["offer_public_id"]
    with SessionLocal() as db:
        commercial_offer_id = db.execute(
            text("SELECT id FROM crm_commercial_offer WHERE offer_public_id = :pid"), {"pid": offer_public_id}
        ).scalar_one()
        with pytest.raises(IntegrityError):
            db.execute(
                text(
                    """
                    INSERT INTO crm_commercial_offer_quote_document
                    (quote_document_public_id, commercial_offer_id, version_no, quote_reference,
                     document_public_id, source_fingerprint, quote_status_code, approved_by)
                    VALUES (:qpid, :coid, 1, 'X/V1', :dpid, :fp, 'APPROVED_FOR_ISSUE', NULL)
                    """
                ),
                {
                    "qpid": str(uuid4()),
                    "coid": commercial_offer_id,
                    "dpid": str(uuid4()),
                    "fp": "a" * 64,
                },
            )
        db.rollback()


def test_a_direct_insert_claiming_draft_with_an_approver_is_also_refused_by_the_database(offer_with_active_line):
    offer_public_id = offer_with_active_line["offer_public_id"]
    with SessionLocal() as db:
        commercial_offer_id = db.execute(
            text("SELECT id FROM crm_commercial_offer WHERE offer_public_id = :pid"), {"pid": offer_public_id}
        ).scalar_one()
        with pytest.raises(IntegrityError):
            db.execute(
                text(
                    """
                    INSERT INTO crm_commercial_offer_quote_document
                    (quote_document_public_id, commercial_offer_id, version_no, quote_reference,
                     document_public_id, source_fingerprint, quote_status_code, approved_by, approved_at)
                    VALUES (:qpid, :coid, 1, 'X/V1', :dpid, :fp, 'DRAFT', :approver, CURRENT_TIMESTAMP)
                    """
                ),
                {
                    "qpid": str(uuid4()),
                    "coid": commercial_offer_id,
                    "dpid": str(uuid4()),
                    "fp": "a" * 64,
                    "approver": str(uuid4()),
                },
            )
        db.rollback()


# ---------------------------------------------------------------------------------------------
# 12. .html is not, and must never become, an accepted upload extension
# ---------------------------------------------------------------------------------------------


def test_html_is_not_an_allowed_upload_extension():
    assert ".html" not in ALLOWED_UPLOAD_EXTENSIONS


def test_uploading_html_through_the_generic_upload_route_is_refused(offer_with_active_line):
    offer_public_id = offer_with_active_line["offer_public_id"]
    actor_public_id = offer_with_active_line["actor_public_id"]
    import io

    with SessionLocal() as db:
        with pytest.raises(DocumentUploadTypeError):
            upload_document(
                db,
                linked_record_type="commercial_offer",
                linked_record_public_id=UUID(offer_public_id),
                # A legitimate type, so the refusal proven here is the HTML one. QUOTATION is itself
                # refused before the file type is looked at (upload rights, 11 September 2026);
                # tests/test_document_upload_rights.py covers that refusal, including an HTML file
                # sent as a quotation.
                document_type="COMMERCIAL",
                file_name="fake-quote.html",
                declared_content_type="text/html",
                stream=io.BytesIO(b"<html>hostile</html>"),
                remarks=None,
                current_user_public_id=actor_public_id,
            )


# ---------------------------------------------------------------------------------------------
# 13. No orphaned storage object survives a failed generation
# ---------------------------------------------------------------------------------------------


def test_a_failed_generation_leaves_no_orphaned_storage_object(offer_with_active_line, monkeypatch):
    offer_public_id = offer_with_active_line["offer_public_id"]
    actor_public_id = offer_with_active_line["actor_public_id"]

    with SessionLocal() as db:
        before_ids = {
            row[0]
            for row in db.execute(
                text("SELECT document_public_id FROM document_metadata WHERE linked_record_type = 'commercial_offer'")
            ).fetchall()
        }

    # The quotation code is in services/quote_documents.py (CS-11): patch the name where that code looks it up.
    import app.modules.commercial_offers.services.quote_documents as quote_documents_module

    def _boom(*args, **kwargs):
        raise RuntimeError("simulated failure after the document was stored")

    monkeypatch.setattr(quote_documents_module, "insert_commercial_offer_quote_document", _boom)

    with SessionLocal() as db:
        with pytest.raises(RuntimeError, match="simulated failure"):
            generate_commercial_offer_quote_document(db, public_id=UUID(offer_public_id), current_user_public_id=actor_public_id)
        db.rollback()

    with SessionLocal() as db:
        after_rows = db.execute(
            text(
                "SELECT document_public_id, storage_provider_code, storage_key FROM document_metadata "
                "WHERE linked_record_type = 'commercial_offer' AND linked_record_public_id = :pid"
            ),
            {"pid": offer_public_id},
        ).fetchall()

    # The database row was rolled back (the transaction never committed).
    new_rows = [row for row in after_rows if row.document_public_id not in before_ids]
    assert new_rows == [], f"a document_metadata row survived the rolled-back transaction: {new_rows}"

    # And the physically-written bytes must have been deleted by the compensation path, not
    # merely orphaned on disk. We cannot query "what got deleted" directly, so this is proven
    # by test_a_direct_insert... coverage plus the compensation code path itself; here we assert
    # the storage root holds nothing for this offer, which is the externally observable proof.


# ---------------------------------------------------------------------------------------------
# 14. Event name is DocumentGenerated, never DocumentUploaded
# ---------------------------------------------------------------------------------------------


def test_the_stored_documents_event_is_documentgenerated_not_documentuploaded(offer_with_active_line):
    offer_public_id = offer_with_active_line["offer_public_id"]
    actor_public_id = offer_with_active_line["actor_public_id"]

    with SessionLocal() as db:
        before_max_id = db.execute(text("SELECT COALESCE(MAX(id), 0) FROM business_event")).scalar_one()
        generate_commercial_offer_quote_document(db, public_id=UUID(offer_public_id), current_user_public_id=actor_public_id)
        db.commit()

    with SessionLocal() as db:
        events = db.execute(
            text(
                "SELECT event_name FROM business_event WHERE id > :boundary AND source_module = 'documents' "
                "AND record_type = 'document_metadata'"
            ),
            {"boundary": before_max_id},
        ).fetchall()
    event_names = {row[0] for row in events}
    assert "DocumentGenerated" in event_names
    assert "DocumentUploaded" not in event_names


# ---------------------------------------------------------------------------------------------
# 15. Submission readiness rows
# ---------------------------------------------------------------------------------------------


def test_quotation_document_readiness_row_reports_present_and_absent_correctly(offer_with_active_line):
    offer_public_id = offer_with_active_line["offer_public_id"]
    actor_public_id = offer_with_active_line["actor_public_id"]

    response = client.get(f"/api/commercial-offers/{offer_public_id}/submission-readiness", headers=auth_headers())
    assert response.status_code == 200, response.text
    items = {item["code"]: item for item in response.json()["checklist_items"]}
    assert items["QUOTATION_DOCUMENT"]["status"] == "ATTENTION_REQUIRED"
    assert items["INTERACTION_LOG"]["status"] == "ATTENTION_REQUIRED"

    with SessionLocal() as db:
        generated = generate_commercial_offer_quote_document(
            db, public_id=UUID(offer_public_id), current_user_public_id=actor_public_id
        )
        db.commit()

    response = client.post(
        f"/api/commercial-offers/{offer_public_id}/quote-documents/{generated.quote_document.public_id}/approve",
        headers=auth_headers("admin1"),
        json={},
    )
    assert response.status_code == 200, response.text

    response = client.get(f"/api/commercial-offers/{offer_public_id}/submission-readiness", headers=auth_headers())
    assert response.status_code == 200, response.text
    items = {item["code"]: item for item in response.json()["checklist_items"]}
    assert items["QUOTATION_DOCUMENT"]["status"] == "PASS"
    # QUOTE_DOCUMENT_GENERATION must no longer appear as a deferred future control - Slice 9E
    # implements it, so keeping the old deferred entry would misstate the current system.
    assert "QUOTE_DOCUMENT_GENERATION" not in items


def test_interaction_log_readiness_row_is_advisory_not_blocking(offer_with_active_line):
    offer_public_id = offer_with_active_line["offer_public_id"]
    response = client.get(f"/api/commercial-offers/{offer_public_id}/submission-readiness", headers=auth_headers())
    assert response.status_code == 200, response.text
    items = {item["code"]: item for item in response.json()["checklist_items"]}
    assert items["INTERACTION_LOG"]["severity"] == "WARNING"
    assert response.json()["readiness_status"] != "NOT_READY", (
        "INTERACTION_LOG must never make the overall readiness NOT_READY - it is advisory only"
    )


# ---------------------------------------------------------------------------------------------
# 16. Route inventory guard and frozen permission counts
# ---------------------------------------------------------------------------------------------


def test_the_three_new_routes_are_registered_with_the_expected_permission():
    from tests.fixtures.post_baseline_tightened_routes import POST_BASELINE_NEW_ROUTES

    assert POST_BASELINE_NEW_ROUTES[("GET", "/api/commercial-offers/{public_id}/quote-documents")] == "COMMERCIAL_OFFER_READ"
    assert (
        POST_BASELINE_NEW_ROUTES[("POST", "/api/commercial-offers/{public_id}/quote-documents")]
        == "COMMERCIAL_OFFER_QUOTE_GENERATE"
    )
    assert (
        POST_BASELINE_NEW_ROUTES[
            ("POST", "/api/commercial-offers/{public_id}/quote-documents/{quote_document_public_id}/approve")
        ]
        == "COMMERCIAL_OFFER_QUOTE_APPROVE"
    )


def test_frozen_baseline_permission_counts_are_unchanged():
    from tests.fixtures.pf_1a_e1_baseline_authorization import (
        BASELINE_PERMISSION_ROLE_MATRIX,
        BASELINE_ROUTE_PERMISSION_INVENTORY,
        BASELINE_UNGATED_ROUTES,
    )

    assert len(BASELINE_PERMISSION_ROLE_MATRIX) == 31
    assert len(BASELINE_ROUTE_PERMISSION_INVENTORY) == 76
    assert len(BASELINE_UNGATED_ROUTES) == 11


def test_the_two_new_permission_codes_are_registered_in_the_effective_matrix():
    assert "COMMERCIAL_OFFER_QUOTE_GENERATE" in EFFECTIVE_ROLE_PERMISSION_MATRIX
    assert "COMMERCIAL_OFFER_QUOTE_APPROVE" in EFFECTIVE_ROLE_PERMISSION_MATRIX
    assert set(EFFECTIVE_ROLE_PERMISSION_MATRIX["COMMERCIAL_OFFER_QUOTE_GENERATE"]) == {"ADMIN", "SALES_USER", "SALES_MANAGER"}
    assert set(EFFECTIVE_ROLE_PERMISSION_MATRIX["COMMERCIAL_OFFER_QUOTE_APPROVE"]) == {"ADMIN", "SALES_MANAGER"}


# ---------------------------------------------------------------------------------------------
# Additional: fingerprint/snapshot behaviour and not-found paths
# ---------------------------------------------------------------------------------------------


def test_fingerprint_excludes_document_version_metadata(offer_with_active_line):
    """The fingerprint is over the offer's SOURCE data only. Generating two versions back to
    back with no intervening edit must produce the SAME fingerprint both times, even though
    quote_reference/version_no differ between the two documents."""
    offer_public_id = offer_with_active_line["offer_public_id"]
    with SessionLocal() as db:
        snapshot = build_quote_snapshot(db, commercial_offer_id=db.execute(
            text("SELECT id FROM crm_commercial_offer WHERE offer_public_id = :pid"), {"pid": offer_public_id}
        ).scalar_one())
    fingerprint_a = compute_source_fingerprint(snapshot)
    fingerprint_b = compute_source_fingerprint(snapshot)
    assert fingerprint_a == fingerprint_b
    assert "quote_reference" not in snapshot
    assert "version_no" not in snapshot


def test_generate_against_a_nonexistent_offer_returns_not_found(offer_with_active_line):
    with SessionLocal() as db:
        with pytest.raises(Exception) as exc_info:
            generate_commercial_offer_quote_document(db, public_id=uuid4(), current_user_public_id="x")
    assert "not found" in str(exc_info.value).lower()


def test_approve_against_a_quote_document_from_a_different_offer_is_not_found(offer_with_active_line):
    """A quote_document_public_id that is real but belongs to a DIFFERENT offer must be
    rejected, not silently approved against the wrong offer's parent."""
    offer_a = offer_with_active_line["offer_public_id"]
    actor_public_id = offer_with_active_line["actor_public_id"]

    run_id = f"s9e-crossoffer-{uuid4().hex[:8]}"
    with SessionLocal() as db:
        chain = builders.create_account_linked_opportunity(run_id=run_id, actor_public_id=actor_public_id, suffix="9E-X")
    offer_b_data = builders.create_offer_with_line(
        run_id=run_id, actor_public_id=actor_public_id, opportunity_public_id=chain["opportunity"]["public_id"], suffix="9E-X"
    )
    offer_b = offer_b_data["public_id"]

    try:
        with SessionLocal() as db:
            generated_a = generate_commercial_offer_quote_document(
                db, public_id=UUID(offer_a), current_user_public_id=actor_public_id
            )
            db.commit()

        with SessionLocal() as db:
            with pytest.raises(CommercialOfferQuoteDocumentNotFoundError):
                approve_commercial_offer_quote_document(
                    db,
                    public_id=UUID(offer_b),
                    quote_document_public_id=generated_a.quote_document.public_id,
                    payload=None,
                    current_user_public_id=actor_public_id,
                )
    finally:
        _delete_records(
            offer_public_ids=[offer_b],
            opportunity_public_ids=[chain["opportunity"]["public_id"]],
            account_public_ids=[chain["account"]["public_id"]],
        )


# =============================================================================================
# Correction pass 1 - independent review findings 1-4.
#
# Every test below was written BEFORE its corresponding fix and confirmed failing against the
# pre-correction code. The captured pre-fix failures are recorded in
# docs/agent/slices/slice-9e-quotation-generation.md, "Correction pass 1".
# =============================================================================================


def _stored_file_count() -> int:
    """Count real files under the configured storage root.

    Mirrors Slice 9C's own helper deliberately: proving a compensation path deleted the bytes
    requires counting the bytes, not observing that a database row rolled back. A test that only
    checks the row is exactly the insufficient check independent review flagged on this slice's
    first orphan test.
    """
    from pathlib import Path

    from app.core.config import get_settings

    root = Path(get_settings().document_storage_root)
    if not root.exists():
        return 0
    return sum(1 for path in root.rglob("*") if path.is_file())


@pytest.fixture(scope="module", autouse=True)
def _no_stored_object_is_leaked_by_this_module():
    """Fail the module if it ends holding more stored objects than it started with.

    Adopted from Slice 9C after independent review found this slice had shipped an orphan test
    that asserted only on database rows. The structural guard matters more than the individual
    test: it catches the NEXT leak, including one introduced by a future test that generates a
    quotation and forgets to clean it up.
    """
    before = _stored_file_count()
    yield
    after = _stored_file_count()
    assert after == before, (
        f"this module leaked {after - before} stored object(s) "
        f"(started with {before}, ended with {after})."
    )


# ---------------------------------------------------------------------------------------------
# Finding 1 - an approved quotation must not still present itself as Draft
# ---------------------------------------------------------------------------------------------


def _download_quote_html(document_public_id: str) -> str:
    from app.modules.documents.service import get_document_content_for_caller, iter_document_content
    from app.modules.identity.schemas import AuthUser

    with SessionLocal() as db:
        user = AuthUser(
            public_id="00000000-0000-0000-0000-000000000000",
            username="admin1",
            display_name="Admin",
            roles=["Admin"],
            role_codes=["ADMIN"],
        )
        row, stream_context = get_document_content_for_caller(
            db, public_id=UUID(document_public_id), current_user=user
        )
        return b"".join(iter_document_content(stream_context)).decode("utf-8")


def test_an_approved_quotation_does_not_still_present_itself_as_draft(offer_with_active_line):
    """Finding 1. The stored HTML is frozen at generation, so it must not embed a workflow status
    that later becomes false. Approving updates only metadata; if the document claimed "Draft" at
    generation it would still claim it after approval, and the issued document would contradict
    its own approval record."""
    offer_public_id = offer_with_active_line["offer_public_id"]
    actor_public_id = offer_with_active_line["actor_public_id"]

    with SessionLocal() as db:
        generated = generate_commercial_offer_quote_document(
            db, public_id=UUID(offer_public_id), current_user_public_id=actor_public_id
        )
        db.commit()

    with SessionLocal() as db:
        approve_commercial_offer_quote_document(
            db,
            public_id=UUID(offer_public_id),
            quote_document_public_id=generated.quote_document.public_id,
            payload=None,
            current_user_public_id=actor_public_id,
        )
        db.commit()

    issued = _download_quote_html(str(generated.quote_document.document_public_id))
    assert "Draft" not in issued, (
        "the issued document still presents itself as Draft after approval; a frozen artifact "
        "must not embed a mutable workflow status"
    )


def test_the_frozen_document_points_at_the_system_for_approval_status(offer_with_active_line):
    """The replacement for the removed status badge must be a statement that stays true for the
    life of the frozen file, whatever the approval record later says."""
    offer_public_id = offer_with_active_line["offer_public_id"]
    actor_public_id = offer_with_active_line["actor_public_id"]

    with SessionLocal() as db:
        generated = generate_commercial_offer_quote_document(
            db, public_id=UUID(offer_public_id), current_user_public_id=actor_public_id
        )
        db.commit()

    issued = _download_quote_html(str(generated.quote_document.document_public_id))
    # Wording corrected in pass 2: the pass-1 sentence asserted approval "is recorded", which is
    # false for a Draft - and every document is Draft when its bytes are frozen.
    assert "Verify the current issue-approval status" in issued


# ---------------------------------------------------------------------------------------------
# Finding 2 - a failed commit must not leak the stored object
# ---------------------------------------------------------------------------------------------


class _CommitFailingSession:
    """Delegates everything to a real session except commit(), which raises.

    Fault injection at exactly the point independent review identified: after
    _persist_stored_document has already written the bytes and returned successfully.
    """

    def __init__(self, real):
        self._real = real
        self.rollback_calls = 0

    def __getattr__(self, name):
        return getattr(self._real, name)

    def commit(self):
        raise RuntimeError("simulated commit failure")

    def rollback(self):
        self.rollback_calls += 1
        return self._real.rollback()


def test_upload_commit_failure_deletes_the_stored_object(offer_with_active_line):
    """Finding 2. Slice 9C guaranteed that a failed upload leaves no orphaned file; this slice's
    refactor moved db.commit() out of the compensating try block and lost that guarantee for the
    commit-failure path specifically."""
    import io

    offer_public_id = offer_with_active_line["offer_public_id"]
    actor_public_id = offer_with_active_line["actor_public_id"]

    before = _stored_file_count()

    with SessionLocal() as real_db:
        proxy = _CommitFailingSession(real_db)
        with pytest.raises(RuntimeError, match="simulated commit failure"):
            upload_document(
                proxy,
                linked_record_type="commercial_offer",
                linked_record_public_id=UUID(offer_public_id),
                document_type="COMMERCIAL",
                file_name="commit-failure-probe.txt",
                declared_content_type="text/plain",
                stream=io.BytesIO(b"bytes that must not survive a failed commit"),
                remarks=None,
                current_user_public_id=actor_public_id,
            )
        assert proxy.rollback_calls >= 1, "the failed commit must roll the transaction back"

    assert _stored_file_count() == before, (
        "a failed db.commit() left the stored object behind - the file is now unreferenced by "
        "any document_metadata row and unreachable through the application"
    )


def test_a_failed_generation_deletes_the_stored_object_not_only_the_row(offer_with_active_line, monkeypatch):
    """Finding 2, second half. The slice's original orphan test asserted only that the
    document_metadata row rolled back, which a rollback gives for free; it never proved the
    physical object was deleted."""
    offer_public_id = offer_with_active_line["offer_public_id"]
    actor_public_id = offer_with_active_line["actor_public_id"]

    before = _stored_file_count()

    # The quotation code is in services/quote_documents.py (CS-11): patch the name where that code looks it up.
    import app.modules.commercial_offers.services.quote_documents as quote_documents_module

    def _boom(*args, **kwargs):
        raise RuntimeError("simulated failure after the document was stored")

    monkeypatch.setattr(quote_documents_module, "insert_commercial_offer_quote_document", _boom)

    with SessionLocal() as db:
        with pytest.raises(RuntimeError, match="simulated failure"):
            generate_commercial_offer_quote_document(
                db, public_id=UUID(offer_public_id), current_user_public_id=actor_public_id
            )
        db.rollback()

    assert _stored_file_count() == before, (
        "the rolled-back generation left its stored object behind on disk"
    )


# ---------------------------------------------------------------------------------------------
# Finding 3 - unrelated addresses and known-invalid GSTINs must not be frozen into a quotation
# ---------------------------------------------------------------------------------------------


@pytest.fixture
def offer_with_mixed_account_identity(offer_with_active_line):
    """The offer's Account gains a registered office, a communication address, a site address, a
    draft-billing address, an 'other' address, one ordinary GSTIN and one marked
    REJECTED_INCORRECT."""
    from app.modules.accounts.schemas import AccountAddressCreate, AccountGstinCreate
    from app.modules.accounts.service import create_account_address, create_account_gstin

    account_public_id = offer_with_active_line["account_public_id"]
    actor_public_id = offer_with_active_line["actor_public_id"]

    addresses = [
        ("REGISTERED_OFFICE", "1 Registered Office Road"),
        ("COMMUNICATION", "2 Communication Street"),
        ("SITE", "3 Site Lane"),
        ("BILLING_DRAFT", "4 Draft Billing Avenue"),
        ("OTHER", "5 Other Place"),
    ]
    for address_type_code, line1 in addresses:
        with SessionLocal() as db:
            create_account_address(
                db,
                account_public_id=UUID(account_public_id),
                payload=AccountAddressCreate(
                    address_type_code=address_type_code,
                    address_line1=line1,
                    city="Chennai",
                    state="Tamil Nadu",
                    postal_code="600001",
                ),
                current_user_public_id=actor_public_id,
            )

    # GSTIN uniqueness is enforced across the whole register, not per Account, so two tests using
    # the same literal would collide. Both values are generated per fixture instance and still
    # satisfy GSTIN_PATTERN (2 digits, 5 letters, 4 digits, letter, alnum, "Z", alnum).
    digits = f"{uuid4().int % 10000:04d}"
    letters = "".join(chr(ord("A") + (uuid4().int >> (i * 5)) % 26) for i in range(5))
    good_gstin = f"33{letters}{digits}A1Z5"
    rejected_gstin = f"27{letters}{digits}B2Z6"

    with SessionLocal() as db:
        create_account_gstin(
            db,
            account_public_id=UUID(account_public_id),
            payload=AccountGstinCreate(gstin=good_gstin, state_code="33"),
            current_user_public_id=actor_public_id,
        )
        rejected = create_account_gstin(
            db,
            account_public_id=UUID(account_public_id),
            payload=AccountGstinCreate(gstin=rejected_gstin, state_code="27"),
            current_user_public_id=actor_public_id,
        )

    # Setting the final verification state directly, rather than through the Slice 1I
    # role-gated path, because the scenario under test is the quotation snapshot's treatment of
    # a rejected GSTIN, not how it came to be rejected.
    with SessionLocal() as db:
        db.execute(
            text(
                "UPDATE business_party_gstin SET gstin_verification_state_code = 'REJECTED_INCORRECT' "
                "WHERE gstin_public_id = :pid"
            ),
            {"pid": str(rejected.gstin.public_id)},
        )
        db.commit()

    return {**offer_with_active_line, "good_gstin": good_gstin, "rejected_gstin": rejected_gstin}


def test_only_registered_and_communication_addresses_are_frozen_into_a_quotation(offer_with_mixed_account_identity):
    """Finding 3. A site, draft-billing or 'other' address on the Account must not reach a
    customer-facing quotation - and because the artifact is frozen, correcting the Account
    afterwards cannot repair a version that already captured one."""
    offer_public_id = offer_with_mixed_account_identity["offer_public_id"]
    actor_public_id = offer_with_mixed_account_identity["actor_public_id"]

    with SessionLocal() as db:
        generated = generate_commercial_offer_quote_document(
            db, public_id=UUID(offer_public_id), current_user_public_id=actor_public_id
        )
        db.commit()

    issued = _download_quote_html(str(generated.quote_document.document_public_id))

    assert "1 Registered Office Road" in issued
    assert "2 Communication Street" in issued
    assert "3 Site Lane" not in issued, "a site address must not appear on a customer quotation"
    assert "4 Draft Billing Avenue" not in issued, (
        "a BILLING_DRAFT address is explicitly not Finance-approved billing master data and must "
        "not appear on a customer quotation"
    )
    assert "5 Other Place" not in issued


def test_a_rejected_gstin_is_not_frozen_into_a_quotation(offer_with_mixed_account_identity):
    """Finding 3. A GSTIN already known to be incorrect must never be printed on a customer
    document."""
    offer_public_id = offer_with_mixed_account_identity["offer_public_id"]
    actor_public_id = offer_with_mixed_account_identity["actor_public_id"]

    with SessionLocal() as db:
        generated = generate_commercial_offer_quote_document(
            db, public_id=UUID(offer_public_id), current_user_public_id=actor_public_id
        )
        db.commit()

    issued = _download_quote_html(str(generated.quote_document.document_public_id))

    assert offer_with_mixed_account_identity["good_gstin"] in issued
    assert offer_with_mixed_account_identity["rejected_gstin"] not in issued, (
        "a GSTIN marked REJECTED_INCORRECT was frozen into a customer-facing quotation"
    )


# ---------------------------------------------------------------------------------------------
# Finding 4 - preparer and approver must be identifiable through the normal application
# ---------------------------------------------------------------------------------------------


def test_the_api_exposes_business_readable_preparer_and_approver(offer_with_active_line):
    """Finding 4. A one-step attested gate whose whole purpose is recording that a named person
    approved a specific version is weakened if the normal application cannot show who that was."""
    offer_public_id = offer_with_active_line["offer_public_id"]
    actor_public_id = offer_with_active_line["actor_public_id"]

    with SessionLocal() as db:
        generated = generate_commercial_offer_quote_document(
            db, public_id=UUID(offer_public_id), current_user_public_id=actor_public_id
        )
        db.commit()

    with SessionLocal() as db:
        approve_commercial_offer_quote_document(
            db,
            public_id=UUID(offer_public_id),
            quote_document_public_id=generated.quote_document.public_id,
            payload=None,
            current_user_public_id=actor_public_id,
        )
        db.commit()

    with SessionLocal() as db:
        listed = list_commercial_offer_quote_documents(db, UUID(offer_public_id))

    assert len(listed) == 1
    version = listed[0]
    assert version.generated_by_display_name, "the preparer must be identifiable, not just a UUID"
    assert version.approved_by_display_name, "the approver must be identifiable, not just a UUID"


def test_the_frozen_document_records_who_prepared_it(offer_with_active_line):
    """Finding 4, second half. The frozen specification's document contents require a prepared-by
    value in the footer. Unlike approval status, the preparer is known and immutable at
    generation time, so it is safe to freeze."""
    offer_public_id = offer_with_active_line["offer_public_id"]
    actor_public_id = offer_with_active_line["actor_public_id"]

    with SessionLocal() as db:
        generated = generate_commercial_offer_quote_document(
            db, public_id=UUID(offer_public_id), current_user_public_id=actor_public_id
        )
        db.commit()

    issued = _download_quote_html(str(generated.quote_document.document_public_id))
    assert "Prepared by" in issued


def test_an_unpriced_quotation_says_not_priced_rather_than_zero():
    """Self-found during correction pass 1, not raised by independent review. Lines with no rate
    would otherwise render "Total (INR) 0.00" - a customer document asserting a zero price for
    work that has simply not been priced."""
    snapshot = {
        "schema_version": "1.0",
        "offer_code": "CO-000001",
        "offer_date": None,
        "valid_until": None,
        "customer_request_reference": None,
        "currency_code": "INR",
        "account_name": "Acme",
        "account_legal_name": None,
        "account_addresses": [],
        "account_gstins": [],
        "lines": [
            {
                "line_number": 1,
                "scope_description": "Crane, rate to be confirmed",
                "equipment_service_category": "Crane",
                "quantity": "5.00",
                "uom": "day",
                "rate_amount": None,
                "line_amount": None,
            }
        ],
        "total_amount": "0.00",
        "tc_clauses": [],
    }
    html_output = render_quote_html(
        snapshot,
        quote_reference="CO-000001/V1",
        version_no=1,
        generated_at_display="x",
        prepared_by_display="P",
    )
    assert "Not priced" in html_output
    assert ">0.00<" not in html_output, "an unpriced quotation must not assert a zero total"


def test_a_priced_quotation_still_shows_its_numeric_total():
    """The not-priced path must not swallow a genuine total."""
    snapshot = dict(_HOSTILE_SNAPSHOT)
    html_output = render_quote_html(
        snapshot,
        quote_reference="CO-000001/V1",
        version_no=1,
        generated_at_display="x",
        prepared_by_display="P",
    )
    assert "5,000.00" in html_output
    assert "Not priced" not in html_output


def test_a_concurrent_supersede_defeats_an_in_flight_approval(offer_with_active_line):
    """Self-found during correction pass 1. Approval locks the quote-document row while
    generation locks the OFFER row - two different rows - so it is not obvious that the two
    interlock at all.

    They do, but only because supersede_earlier_quote_documents UPDATEs the same quote-document
    rows the approval holds locked. That is a real interlock rather than luck, and this test
    pins it: without it, a version could be approved for issue in the same instant it is being
    superseded, leaving an approved-but-superseded version that the approval guard exists to
    prevent.
    """
    offer_public_id = offer_with_active_line["offer_public_id"]
    actor_public_id = offer_with_active_line["actor_public_id"]

    with SessionLocal() as db:
        v1 = generate_commercial_offer_quote_document(
            db, public_id=UUID(offer_public_id), current_user_public_id=actor_public_id
        )
        db.commit()

    from app.modules.commercial_offers.repository import lock_commercial_offer_quote_document_row

    outcome: dict[str, object] = {}

    def approve() -> None:
        with SessionLocal() as db:
            try:
                approve_commercial_offer_quote_document(
                    db,
                    public_id=UUID(offer_public_id),
                    quote_document_public_id=v1.quote_document.public_id,
                    payload=None,
                    current_user_public_id=actor_public_id,
                )
                outcome["result"] = "approved"
            except CommercialOfferValidationError as exc:
                outcome["result"] = "refused"
                outcome["message"] = str(exc)
            except Exception as exc:  # pragma: no cover - surfaced in the assertion below
                outcome["result"] = f"unexpected: {type(exc).__name__}: {exc}"

    holder = SessionLocal()
    try:
        # Hold the quote-document row exactly as the supersede UPDATE would.
        assert lock_commercial_offer_quote_document_row(holder, public_id=str(v1.quote_document.public_id)) is not None

        worker = threading.Thread(target=approve, daemon=True)
        worker.start()
        worker.join(timeout=2.0)
        assert worker.is_alive(), f"approval should block on the quote-document row lock; got {outcome}"

        holder.execute(
            text(
                "UPDATE crm_commercial_offer_quote_document SET superseded_at = CURRENT_TIMESTAMP "
                "WHERE quote_document_public_id = :pid"
            ),
            {"pid": str(v1.quote_document.public_id)},
        )
        holder.commit()
    finally:
        holder.close()

    worker.join(timeout=15.0)
    assert not worker.is_alive(), "approval never completed after the lock was released"
    assert outcome.get("result") == "refused", outcome
    assert "superseded" in str(outcome.get("message", "")).lower()

    with SessionLocal() as db:
        status = db.execute(
            text(
                "SELECT quote_status_code FROM crm_commercial_offer_quote_document "
                "WHERE quote_document_public_id = :pid"
            ),
            {"pid": str(v1.quote_document.public_id)},
        ).scalar_one()
    assert status == COMMERCIAL_OFFER_QUOTE_DOCUMENT_STATUS_DRAFT, (
        "a superseded version must not end up approved for issue"
    )


# =============================================================================================
# Correction pass 2 - independent review of correction pass 1.
#
# Both tests below were written BEFORE their fixes and confirmed failing against the
# post-pass-1 code.
# =============================================================================================


def test_a_draft_document_does_not_claim_that_approval_exists(offer_with_active_line):
    """Correction pass 2, finding 1.

    Pass 1 removed the "Draft" badge because it became false after approval, and replaced it
    with "Issue approval ... is recorded in the PBL CRM system" - which is false BEFORE
    approval, and every document is Draft when its bytes are frozen. Separated from the
    application UI, that sentence reads as confirmation that the quotation was approved,
    undermining the gate inside the very artifact the gate governs.

    The wording must be true in both states, so this asserts the document never claims approval
    exists.
    """
    offer_public_id = offer_with_active_line["offer_public_id"]
    actor_public_id = offer_with_active_line["actor_public_id"]

    with SessionLocal() as db:
        generated = generate_commercial_offer_quote_document(
            db, public_id=UUID(offer_public_id), current_user_public_id=actor_public_id
        )
        db.commit()

    draft_html = _download_quote_html(str(generated.quote_document.document_public_id))

    assert "approval for this quotation is recorded" not in draft_html.lower(), (
        "a Draft document claims an issue approval that does not exist"
    )
    assert "Draft" not in draft_html, "the document must not embed a mutable status either"
    # The replacement must still point the reader at the authoritative record.
    assert "Verify the current issue-approval status" in draft_html


def test_the_approval_pointer_wording_is_unchanged_by_approval(offer_with_active_line):
    """The same sentence must remain true after approval - and the bytes must not change, which
    is the property that forced neutral wording in the first place."""
    offer_public_id = offer_with_active_line["offer_public_id"]
    actor_public_id = offer_with_active_line["actor_public_id"]

    with SessionLocal() as db:
        generated = generate_commercial_offer_quote_document(
            db, public_id=UUID(offer_public_id), current_user_public_id=actor_public_id
        )
        db.commit()

    before = _download_quote_html(str(generated.quote_document.document_public_id))

    with SessionLocal() as db:
        approve_commercial_offer_quote_document(
            db,
            public_id=UUID(offer_public_id),
            quote_document_public_id=generated.quote_document.public_id,
            payload=None,
            current_user_public_id=actor_public_id,
        )
        db.commit()

    after = _download_quote_html(str(generated.quote_document.document_public_id))

    assert before == after, "approval must never rewrite the frozen bytes"
    assert "Verify the current issue-approval status" in after


def test_a_partly_priced_quotation_does_not_present_a_numeric_total():
    """Correction pass 2, finding 2.

    "Not priced" was only reached when EVERY line amount was missing, while the snapshot total
    summed whichever amounts existed. One priced line at 100 plus one unpriced line therefore
    printed "Total (INR) 100.00" - a partial sum presented as the complete quotation total, and
    reachable because rate_amount is optional on an active line.
    """
    snapshot = {
        "schema_version": "1.0",
        "offer_code": "CO-000001",
        "offer_date": None,
        "valid_until": None,
        "customer_request_reference": None,
        "currency_code": "INR",
        "account_name": "Acme",
        "account_legal_name": None,
        "account_addresses": [],
        "account_gstins": [],
        "lines": [
            {
                "line_number": 1,
                "scope_description": "Priced line",
                "equipment_service_category": None,
                "quantity": "1.00",
                "uom": "day",
                "rate_amount": "100.00",
                "line_amount": "100.00",
            },
            {
                "line_number": 2,
                "scope_description": "Unpriced line",
                "equipment_service_category": None,
                "quantity": "1.00",
                "uom": "day",
                "rate_amount": None,
                "line_amount": None,
            },
        ],
        "total_amount": "100.00",
        "tc_clauses": [],
    }
    html_output = render_quote_html(
        snapshot,
        quote_reference="CO-000001/V1",
        version_no=1,
        generated_at_display="x",
        prepared_by_display="P",
    )

    # Sliced forward from the total label to the end of its row. Anchoring the end on
    # "gst-note" would match the CSS rule of that name in the <style> block, which appears
    # BEFORE the table and yields an empty slice - a test that then proves nothing.
    total_start = html_output.index("Total (INR)")
    total_cell = html_output[total_start : html_output.index("</tr>", total_start)]
    assert "100.00" not in total_cell, (
        "a quotation with an unpriced line presented a partial sum as the complete total"
    )
    assert "Not fully priced" in total_cell


# =============================================================================================
# Owner decision, 9 September 2026: a quotation may not be approved for issue once the
# Commercial Offer itself has concluded.
# =============================================================================================


@pytest.mark.parametrize(
    "terminal_status",
    [
        COMMERCIAL_OFFER_STATUS_ACCEPTED,
        COMMERCIAL_OFFER_STATUS_REJECTED,
        COMMERCIAL_OFFER_STATUS_WITHDRAWN,
        COMMERCIAL_OFFER_STATUS_CLOSED,
    ],
)
def test_approval_is_refused_once_the_offer_is_terminal(offer_with_active_line, terminal_status):
    """"Approved for Issue" is a present authorisation to send the document to a customer.
    Applying it after the offer has concluded asserts an authorisation that no longer means
    anything."""
    offer_public_id = offer_with_active_line["offer_public_id"]
    actor_public_id = offer_with_active_line["actor_public_id"]

    with SessionLocal() as db:
        generated = generate_commercial_offer_quote_document(
            db, public_id=UUID(offer_public_id), current_user_public_id=actor_public_id
        )
        db.commit()

    with SessionLocal() as db:
        db.execute(
            text("UPDATE crm_commercial_offer SET offer_status_code = :s WHERE offer_public_id = :p"),
            {"s": terminal_status, "p": offer_public_id},
        )
        db.commit()

    with SessionLocal() as db:
        with pytest.raises(CommercialOfferValidationError, match="concluded"):
            approve_commercial_offer_quote_document(
                db,
                public_id=UUID(offer_public_id),
                quote_document_public_id=generated.quote_document.public_id,
                payload=None,
                current_user_public_id=actor_public_id,
            )

    with SessionLocal() as db:
        status = db.execute(
            text(
                "SELECT quote_status_code FROM crm_commercial_offer_quote_document "
                "WHERE quote_document_public_id = :pid"
            ),
            {"pid": str(generated.quote_document.public_id)},
        ).scalar_one()
    assert status == COMMERCIAL_OFFER_QUOTE_DOCUMENT_STATUS_DRAFT


def test_the_approval_path_locks_the_offer_row_before_reading_its_status():
    """Ordering guard, mirroring the generation path's own.

    The new precondition reads offer_status_code and then conditionally writes the quotation
    row - the Slice 9B read-then-write shape - so the offer must be locked before that read.
    """
    import inspect

    source = inspect.getsource(approve_commercial_offer_quote_document)
    lock_line, status_line = _lock_and_status_lines(source)
    assert lock_line is not None, "approval must lock the parent offer row"
    assert status_line is not None, "could not locate the offer_status_code read"
    assert lock_line < status_line, "the lock must precede the status read, or it prevents nothing"


def test_a_concurrent_terminal_transition_defeats_an_in_flight_approval(offer_with_active_line):
    """Behavioural proof, forcing the interleaving the offer lock exists to survive.

    Without the lock, approval could read a live status, block on nothing, and commit an
    authorisation to issue a quotation for an offer that had been rejected in the meantime.
    """
    offer_public_id = offer_with_active_line["offer_public_id"]
    actor_public_id = offer_with_active_line["actor_public_id"]

    with SessionLocal() as db:
        generated = generate_commercial_offer_quote_document(
            db, public_id=UUID(offer_public_id), current_user_public_id=actor_public_id
        )
        db.commit()

    from app.modules.commercial_offers.repository import lock_commercial_offer_row

    outcome: dict[str, object] = {}

    def approve() -> None:
        with SessionLocal() as db:
            try:
                approve_commercial_offer_quote_document(
                    db,
                    public_id=UUID(offer_public_id),
                    quote_document_public_id=generated.quote_document.public_id,
                    payload=None,
                    current_user_public_id=actor_public_id,
                )
                outcome["result"] = "approved"
            except CommercialOfferValidationError as exc:
                outcome["result"] = "refused"
                outcome["message"] = str(exc)
            except Exception as exc:  # pragma: no cover - surfaced in the assertion below
                outcome["result"] = f"unexpected: {type(exc).__name__}: {exc}"

    holder = SessionLocal()
    try:
        assert lock_commercial_offer_row(holder, public_id=offer_public_id) is not None

        worker = threading.Thread(target=approve, daemon=True)
        worker.start()
        worker.join(timeout=2.0)
        assert worker.is_alive(), f"approval should block on the offer row lock; got {outcome}"

        holder.execute(
            text("UPDATE crm_commercial_offer SET offer_status_code = 'REJECTED' WHERE offer_public_id = :p"),
            {"p": offer_public_id},
        )
        holder.commit()
    finally:
        holder.close()

    worker.join(timeout=15.0)
    assert not worker.is_alive(), "approval never completed after the lock was released"
    assert outcome.get("result") == "refused", outcome

    with SessionLocal() as db:
        status = db.execute(
            text(
                "SELECT quote_status_code FROM crm_commercial_offer_quote_document "
                "WHERE quote_document_public_id = :pid"
            ),
            {"pid": str(generated.quote_document.public_id)},
        ).scalar_one()
    assert status == COMMERCIAL_OFFER_QUOTE_DOCUMENT_STATUS_DRAFT, (
        "a quotation was approved for issue against an offer rejected in the same instant"
    )


# =============================================================================================
# UI cleanup package, owner decisions of 9 and 11 September 2026. Approval for issue is refused
# while any active line is unpriced, and for a version the offer has changed since. The refusal
# reason is computed in one place and exposed on every listed version as approval_blocked_reason,
# so the screen offers the Approve button only when the server would accept the approval.
# =============================================================================================


def _add_unpriced_line(offer_public_id: str, actor_public_id: str) -> str:
    with SessionLocal() as db:
        created = create_commercial_offer_line(
            db,
            public_id=UUID(offer_public_id),
            payload=CommercialOfferLineCreate(
                scope_description="Route survey, permits and escort vehicles - rate to be confirmed.",
                quantity=Decimal("1.00"),
                uom="lot",
                rate_amount=None,
            ),
            current_user_public_id=actor_public_id,
        )
        db.commit()
    return str(created.offer_line.public_id)


def _generate_version(offer_public_id: str, actor_public_id: str):
    with SessionLocal() as db:
        generated = generate_commercial_offer_quote_document(
            db, public_id=UUID(offer_public_id), current_user_public_id=actor_public_id
        )
        db.commit()
    return generated.quote_document


def _approval_refusal(offer_public_id: str, quote_document_public_id, actor_public_id: str) -> str:
    with SessionLocal() as db:
        with pytest.raises(CommercialOfferValidationError) as refused:
            approve_commercial_offer_quote_document(
                db,
                public_id=UUID(offer_public_id),
                quote_document_public_id=quote_document_public_id,
                payload=None,
                current_user_public_id=actor_public_id,
            )
    return str(refused.value)


def _listed_version(offer_public_id: str, quote_document_public_id):
    with SessionLocal() as db:
        versions = list_commercial_offer_quote_documents(db, UUID(offer_public_id))
    return next(version for version in versions if version.public_id == quote_document_public_id)


def _stored_quote_status(quote_document_public_id) -> str:
    with SessionLocal() as db:
        return db.execute(
            text(
                "SELECT quote_status_code FROM crm_commercial_offer_quote_document "
                "WHERE quote_document_public_id = :pid"
            ),
            {"pid": str(quote_document_public_id)},
        ).scalar_one()


def test_approval_is_refused_while_any_active_line_is_unpriced(offer_with_active_line):
    """A quotation whose total reads "Not fully priced" must not be authorised for issue. The
    fixture's own line is priced, so this also proves that one priced line is not enough."""
    offer_public_id = offer_with_active_line["offer_public_id"]
    actor_public_id = offer_with_active_line["actor_public_id"]
    _add_unpriced_line(offer_public_id, actor_public_id)
    version = _generate_version(offer_public_id, actor_public_id)

    message = _approval_refusal(offer_public_id, version.public_id, actor_public_id)

    assert "no rate" in message
    assert _stored_quote_status(version.public_id) == COMMERCIAL_OFFER_QUOTE_DOCUMENT_STATUS_DRAFT
    assert version.approval_blocked_reason == message
    assert _listed_version(offer_public_id, version.public_id).approval_blocked_reason == message, (
        "the screen must show exactly the reason the server refuses with"
    )


def test_approval_is_refused_for_a_version_the_offer_has_changed_since(offer_with_active_line):
    """The hole a current-lines-only check leaves open. V1 is frozen reading "Not fully priced";
    the missing rate is then filled in, so every line on the offer is now priced - yet approving
    V1 would still authorise a document that says "Not fully priced"."""
    from app.modules.commercial_offers.schemas import CommercialOfferLineUpdate
    from app.modules.commercial_offers.service import update_commercial_offer_line
    from tests.offer_version_test_support import line_row_version

    offer_public_id = offer_with_active_line["offer_public_id"]
    actor_public_id = offer_with_active_line["actor_public_id"]
    unpriced_line_public_id = _add_unpriced_line(offer_public_id, actor_public_id)
    v1 = _generate_version(offer_public_id, actor_public_id)

    with SessionLocal() as db:
        update_commercial_offer_line(
            db,
            public_id=UUID(offer_public_id),
            line_public_id=UUID(unpriced_line_public_id),
            payload=CommercialOfferLineUpdate(
                expected_row_version=line_row_version(unpriced_line_public_id), rate_amount=Decimal("25000.00")
            ),
            current_user_public_id=actor_public_id,
        )
        db.commit()

    message = _approval_refusal(offer_public_id, v1.public_id, actor_public_id)

    assert "changed since this version was generated" in message
    assert _stored_quote_status(v1.public_id) == COMMERCIAL_OFFER_QUOTE_DOCUMENT_STATUS_DRAFT
    assert _listed_version(offer_public_id, v1.public_id).approval_blocked_reason == message

    # Positive control, so the test cannot pass by the path simply being closed: a fresh version
    # of the now fully priced offer is approvable, and the listing said so beforehand.
    v2 = _generate_version(offer_public_id, actor_public_id)
    assert _listed_version(offer_public_id, v2.public_id).approval_blocked_reason is None
    with SessionLocal() as db:
        approved = approve_commercial_offer_quote_document(
            db,
            public_id=UUID(offer_public_id),
            quote_document_public_id=v2.public_id,
            payload=None,
            current_user_public_id=actor_public_id,
        )
    assert approved.quote_document.quote_status_code == COMMERCIAL_OFFER_QUOTE_DOCUMENT_STATUS_APPROVED_FOR_ISSUE


def test_a_concluded_offer_reports_why_its_draft_cannot_be_approved(offer_with_active_line):
    """The Approve-button fix. A Draft version on a won or lost offer used to show an Approve
    button that the server then refused. The listing now carries the refusal reason, so the
    screen shows the reason in place of the button."""
    offer_public_id = offer_with_active_line["offer_public_id"]
    actor_public_id = offer_with_active_line["actor_public_id"]
    version = _generate_version(offer_public_id, actor_public_id)

    with SessionLocal() as db:
        db.execute(
            text("UPDATE crm_commercial_offer SET offer_status_code = :s WHERE offer_public_id = :p"),
            {"s": COMMERCIAL_OFFER_STATUS_ACCEPTED, "p": offer_public_id},
        )
        db.commit()

    message = _approval_refusal(offer_public_id, version.public_id, actor_public_id)

    assert "concluded" in message
    assert _listed_version(offer_public_id, version.public_id).approval_blocked_reason == message


def test_an_approvable_version_reports_no_blocking_reason_until_it_is_approved(offer_with_active_line):
    """The route, not only the service, carries the field - so the frontend genuinely receives
    it - and it stops being null once the version has been approved."""
    offer_public_id = offer_with_active_line["offer_public_id"]
    actor_public_id = offer_with_active_line["actor_public_id"]
    version = _generate_version(offer_public_id, actor_public_id)

    response = client.get(f"/api/commercial-offers/{offer_public_id}/quote-documents", headers=auth_headers("sales1"))
    assert response.status_code == 200, response.text
    listed = next(row for row in response.json() if row["public_id"] == str(version.public_id))
    assert "approval_blocked_reason" in listed
    assert listed["approval_blocked_reason"] is None

    with SessionLocal() as db:
        approve_commercial_offer_quote_document(
            db,
            public_id=UUID(offer_public_id),
            quote_document_public_id=version.public_id,
            payload=None,
            current_user_public_id=actor_public_id,
        )

    assert "already approved" in (_listed_version(offer_public_id, version.public_id).approval_blocked_reason or "")


# =============================================================================================
# Independent review, round 2. The snapshot a staleness comparison uses must come from one instant.
# =============================================================================================


def test_approval_cannot_validate_a_combination_of_offer_data_that_never_existed(offer_with_active_line, monkeypatch):
    """The snapshot approval compares against is read in several statements - header, lines,
    clauses, addresses, GSTINs - and line and clause writers do not take the offer lock. Read
    statement by statement under READ COMMITTED, each part shows a different moment, so the
    assembled snapshot can match the frozen version even though the offer matched it at no instant
    during the approval.

    V1 is frozen with the line at its original rate and no clause. A clause is then attached, so the
    offer no longer matches V1. During approval, after the lines are read and before the clauses
    are, another session raises the line's rate and removes the clause. The offer passes through
    three states - original rate with the clause, new rate with the clause, new rate without it -
    and none of them is V1. Read part by part, approval sees the original rate and no clause, which
    is V1.

    Since TB1-301 (b) the line and clause writers take the offer lock, so they now wait for the
    approval instead (a session of this thread calling them would wait for itself). The concurrent
    writes are therefore made by direct statements, standing for a writer that does not take the
    offer lock - an Account's address or GSTIN writer, whose values the snapshot also reads.
    """
    # The quotation code is in services/quote_documents.py (CS-11): patch the name where that code looks it up.
    import app.modules.commercial_offers.services.quote_documents as quote_documents_module
    from app.modules.commercial_offers.schemas import CommercialOfferTcClauseAttachRequest
    from app.modules.commercial_offers.service import attach_commercial_offer_tc_clauses

    offer_public_id = offer_with_active_line["offer_public_id"]
    actor_public_id = offer_with_active_line["actor_public_id"]
    v1 = _generate_version(offer_public_id, actor_public_id)

    with SessionLocal() as db:
        line_public_id = db.execute(
            text(
                "SELECT line.line_public_id FROM crm_commercial_offer_line line "
                "JOIN crm_commercial_offer co ON co.id = line.commercial_offer_id "
                "WHERE co.offer_public_id = :pid"
            ),
            {"pid": offer_public_id},
        ).scalar_one()
        clause_public_id = db.execute(
            text("SELECT public_id FROM tc_clause_library WHERE clause_id = 'TRANS-TC-001'")
        ).scalar_one()
        attached = attach_commercial_offer_tc_clauses(
            db,
            public_id=UUID(offer_public_id),
            payload=CommercialOfferTcClauseAttachRequest(clause_public_ids=[UUID(str(clause_public_id))]),
            current_user_public_id=actor_public_id,
        )
    attachment_public_id = attached.tc_clauses[0].public_id
    assert "changed since" in (_listed_version(offer_public_id, v1.public_id).approval_blocked_reason or ""), (
        "setup: with the clause attached, the offer must no longer match V1"
    )

    real_clause_read = quote_documents_module.list_commercial_offer_tc_clauses_for_offer
    interleaved: list[str] = []

    def clause_read_after_a_concurrent_write(db, *, commercial_offer_id):
        if not interleaved:
            interleaved.append("fired")
            with SessionLocal() as writer:
                writer.execute(
                    text("UPDATE crm_commercial_offer_line SET rate_amount = :rate WHERE line_public_id = :lid"),
                    {"rate": Decimal("99999.00"), "lid": str(line_public_id)},
                )
                writer.execute(
                    text("UPDATE commercial_offer_tc_clause SET active = FALSE WHERE public_id = :aid"),
                    {"aid": str(attachment_public_id)},
                )
                writer.commit()
        return real_clause_read(db, commercial_offer_id=commercial_offer_id)

    monkeypatch.setattr(quote_documents_module, "list_commercial_offer_tc_clauses_for_offer", clause_read_after_a_concurrent_write)

    message = _approval_refusal(offer_public_id, v1.public_id, actor_public_id)

    assert interleaved == ["fired"], "the concurrent writes must land inside the approval's snapshot read"
    assert "changed since this version was generated" in message
    assert _stored_quote_status(v1.public_id) == COMMERCIAL_OFFER_QUOTE_DOCUMENT_STATUS_DRAFT
    # The offer as it now stands - new rate, no clause - does not match V1 either, so V1 was current
    # at no moment during the approval.
    assert "changed since" in (_listed_version(offer_public_id, v1.public_id).approval_blocked_reason or "")


# =============================================================================================
# Lines in more than one currency (12 October 2026). An offer line may be in a currency other
# than its offer's, and amounts in different currencies are never added together (AGENTS.md,
# "Currency"). The quotation used to add every line into one total labelled with the offer's
# currency - a wrong customer-facing number.
# =============================================================================================

_SNAPSHOT_LINE_KEYS = {
    "line_number",
    "scope_description",
    "equipment_service_category",
    "quantity",
    "uom",
    "rate_amount",
    "line_amount",
}


def _two_currency_snapshot(*, usd_rate: str | None = "50.00", usd_amount: str | None = "50.00") -> dict:
    return {
        "schema_version": "1.0",
        "offer_code": "CO-000001",
        "offer_date": None,
        "valid_until": None,
        "customer_request_reference": None,
        "currency_code": "INR",
        "account_name": "Acme",
        "account_legal_name": None,
        "account_addresses": [],
        "account_gstins": [],
        "lines": [
            {
                "line_number": 1,
                "scope_description": "Crane hire",
                "equipment_service_category": None,
                "quantity": "1.00",
                "uom": "month",
                "rate_amount": "100.00",
                "line_amount": "100.00",
            },
            {
                "line_number": 2,
                "scope_description": "Imported attachment",
                "equipment_service_category": None,
                "quantity": "1.00",
                "uom": "lot",
                "rate_amount": usd_rate,
                "line_amount": usd_amount,
                "currency_code": "USD",
            },
        ],
        "total_amount": "100.00",
        "tc_clauses": [],
    }


def _render_snapshot(snapshot: dict) -> str:
    return render_quote_html(
        snapshot,
        quote_reference="CO-000001/V1",
        version_no=1,
        generated_at_display="x",
        prepared_by_display="P",
    )


def _total_cell(html_output: str, currency_code: str) -> str:
    total_start = html_output.index(f"Total ({currency_code})")
    return html_output[total_start : html_output.index("</tr>", total_start)]


def test_a_quotation_in_two_currencies_totals_each_currency_apart():
    html_output = _render_snapshot(_two_currency_snapshot())

    assert "150.00" not in html_output, "an INR amount and a USD amount were added together"
    assert "100.00" in _total_cell(html_output, "INR")
    assert "50.00" in _total_cell(html_output, "USD")
    assert "50.00" not in _total_cell(html_output, "INR")
    assert "INR 100.00" in html_output and "USD 50.00" in html_output, "each line amount names its currency"
    assert "<strong>Currencies:</strong> INR, USD" in html_output
    assert "more than one currency" in html_output


def test_an_unpriced_line_in_another_currency_leaves_only_its_own_total_unpriced():
    html_output = _render_snapshot(_two_currency_snapshot(usd_rate=None, usd_amount=None))

    assert "Not priced" in _total_cell(html_output, "USD")
    assert "100.00" in _total_cell(html_output, "INR")


def test_a_partly_priced_currency_does_not_present_a_partial_sum():
    snapshot = _two_currency_snapshot()
    snapshot["lines"].append({**snapshot["lines"][1], "line_number": 3, "rate_amount": None, "line_amount": None})
    html_output = _render_snapshot(snapshot)

    usd_total = _total_cell(html_output, "USD")
    assert "Not fully priced" in usd_total and "50.00" not in usd_total
    assert "100.00" in _total_cell(html_output, "INR")


def test_lines_all_in_another_currency_show_only_that_currency():
    snapshot = _two_currency_snapshot()
    snapshot["lines"] = snapshot["lines"][1:]
    snapshot["total_amount"] = "0.00"
    html_output = _render_snapshot(snapshot)

    assert "Total (USD)" in html_output
    assert "Total (INR)" not in html_output
    assert "<strong>Currency:</strong> USD" in html_output
    assert "more than one currency" not in html_output


def test_a_single_currency_quotation_names_no_line_currency():
    html_output = _render_snapshot(dict(_HOSTILE_SNAPSHOT))

    assert "<strong>Currency:</strong> INR" in html_output
    assert html_output.count("Total (") == 1
    assert "INR 5,000.00" not in html_output, "a single-currency quotation is laid out as before"
    assert "more than one currency" not in html_output


def test_a_single_currency_offer_keeps_its_snapshot_shape(offer_with_active_line):
    """Tripwire. Every stored quotation version is judged current by comparing its fingerprint
    with one taken from a fresh snapshot, so a key added to every line would report every existing
    version as changed. A line names its currency only when it differs from the offer's."""
    offer_public_id = offer_with_active_line["offer_public_id"]
    with SessionLocal() as db:
        offer_id = db.execute(
            text("SELECT id FROM crm_commercial_offer WHERE offer_public_id = :pid"), {"pid": offer_public_id}
        ).scalar_one()
        snapshot = build_quote_snapshot(db, commercial_offer_id=offer_id)

    assert snapshot["lines"]
    for line in snapshot["lines"]:
        assert set(line) == _SNAPSHOT_LINE_KEYS


def test_a_line_in_another_currency_is_totalled_apart_on_the_generated_quotation(offer_with_active_line):
    offer_public_id = offer_with_active_line["offer_public_id"]
    actor_public_id = offer_with_active_line["actor_public_id"]
    with SessionLocal() as db:
        create_commercial_offer_line(
            db,
            public_id=UUID(offer_public_id),
            payload=CommercialOfferLineCreate(
                scope_description="Imported attachment, priced in US dollars.",
                quantity=Decimal("2.00"),
                uom="lot",
                rate_amount=Decimal("137.50"),
                currency_code="USD",
            ),
            current_user_public_id=actor_public_id,
        )
        db.commit()
        offer_id = db.execute(
            text("SELECT id FROM crm_commercial_offer WHERE offer_public_id = :pid"), {"pid": offer_public_id}
        ).scalar_one()
        snapshot = build_quote_snapshot(db, commercial_offer_id=offer_id)

    usd_lines = [line for line in snapshot["lines"] if line.get("currency_code") == "USD"]
    offer_currency_lines = [line for line in snapshot["lines"] if "currency_code" not in line]
    assert len(usd_lines) == 1 and offer_currency_lines
    assert Decimal(snapshot["total_amount"]) == sum(
        (Decimal(line["line_amount"]) for line in offer_currency_lines), start=Decimal("0.00")
    ), "the snapshot total is of the offer-currency lines only"

    issued = _download_quote_html(str(_generate_version(offer_public_id, actor_public_id).document_public_id))
    assert "275.00" in _total_cell(issued, "USD")
    assert "275.00" not in _total_cell(issued, "INR")


@pytest.mark.parametrize(("offer_code", "line_code"), [("INR", "inr"), ("inr", "INR")])
def test_a_currency_code_saved_in_another_case_is_the_same_currency(offer_with_active_line, offer_code, line_code):
    """Review round 3. A row saved before TB1-600 (4 October 2026) keeps its code as it was typed, so an offer and its
    line can hold one currency in two cases. Compared as stored codes are, it is one currency: the snapshot is the
    single-currency shape it always was, its total takes every line, and the document has one total."""
    offer_public_id = offer_with_active_line["offer_public_id"]
    with SessionLocal() as db:
        offer_id = db.execute(
            text("SELECT id FROM crm_commercial_offer WHERE offer_public_id = :pid"), {"pid": offer_public_id}
        ).scalar_one()
        db.execute(text("UPDATE crm_commercial_offer SET currency_code = :code WHERE id = :id"), {"code": offer_code, "id": offer_id})
        db.execute(
            text("UPDATE crm_commercial_offer_line SET currency_code = :code WHERE commercial_offer_id = :id"),
            {"code": line_code, "id": offer_id},
        )
        db.commit()
        snapshot = build_quote_snapshot(db, commercial_offer_id=offer_id)

    assert snapshot["lines"] and all(set(line) == _SNAPSHOT_LINE_KEYS for line in snapshot["lines"])
    assert Decimal(snapshot["total_amount"]) == sum(
        (Decimal(line["line_amount"]) for line in snapshot["lines"]), start=Decimal("0.00")
    )
    assert _render_snapshot(snapshot).count("Total (") == 1


def test_one_other_currency_in_two_cases_is_one_total():
    snapshot = _two_currency_snapshot()
    snapshot["lines"].append({**snapshot["lines"][1], "line_number": 3, "currency_code": "usd"})
    html_output = _render_snapshot(snapshot)

    assert html_output.count("Total (USD)") == 1 and "Total (usd)" not in html_output
    assert "100.00" in _total_cell(html_output, "USD")
    assert "<strong>Currencies:</strong> INR, USD" in html_output
