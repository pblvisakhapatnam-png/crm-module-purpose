"""Slice 9B - CRM pilot hardening.

Two independent changes, tested separately:

1. A Rejected Commercial Offer is final - no further customer response may be recorded
   against it. This closes the reactivation gap recorded in
   `docs/agent/DEFERRED_REQUIREMENTS.md`, by explicit business decision on 7 September 2026.
2. The application refuses to start outside development while a public placeholder secret
   from `.env.example` is still configured - and, since TB-1 TB1-204 part d, refuses to start
   at all when APP_ENV is missing.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.core.config import (
    STANDARD_PASSWORD_HASH_ITERATIONS,
    PLACEHOLDER_DATABASE_PASSWORD,
    PLACEHOLDER_JWT_SECRET,
    InsecureDefaultConfigurationError,
    MissingAppEnvironmentError,
    Settings,
    database_url_password,
)
from app.core.database import SessionLocal
from app.main import app
from app.modules.commercial_offers.contract import (
    COMMERCIAL_OFFER_CUSTOMER_RESPONSE_ALLOWED_STATUSES,
    COMMERCIAL_OFFER_STATUS_ACCEPTED,
    COMMERCIAL_OFFER_STATUS_REJECTED,
    COMMERCIAL_OFFER_STATUS_SUBMITTED,
)
from tests.business_day_test_support import TODAY, held_to_the_test_day
from tests.offer_version_test_support import offer_row_version
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


def _delete_records(*, offer_public_ids: list[str], opportunity_public_ids: list[str],
                    account_public_ids: list[str]) -> None:
    with SessionLocal() as db:
        for offer_public_id in offer_public_ids:
            for table, column in (
                ("commercial_offer_customer_response", "commercial_offer_id"),
                ("commercial_offer_credit_review", "commercial_offer_id"),
                ("commercial_offer_submission_evidence", "commercial_offer_id"),
                ("crm_commercial_offer_line", "commercial_offer_id"),
            ):
                db.execute(
                    text(
                        f"DELETE FROM {table} WHERE {column} IN "
                        "(SELECT id FROM crm_commercial_offer WHERE offer_public_id = :pid)"
                    ),
                    {"pid": offer_public_id},
                )
            db.execute(
                text("DELETE FROM crm_commercial_offer WHERE offer_public_id = :pid"),
                {"pid": offer_public_id},
            )
        for opportunity_public_id in opportunity_public_ids:
            db.execute(
                text("DELETE FROM crm_opportunity WHERE opportunity_public_id = :pid"),
                {"pid": opportunity_public_id},
            )
        for account_public_id in account_public_ids:
            db.execute(
                text("DELETE FROM business_party WHERE business_party_public_id = :pid"),
                {"pid": account_public_id},
            )
        for public_id in offer_public_ids + opportunity_public_ids + account_public_ids:
            db.execute(
                text("DELETE FROM business_event WHERE record_public_id = :pid"),
                {"pid": public_id},
            )
        db.commit()


@pytest.fixture
def rejected_offer_with_replacement():
    """The exact reachable scenario the gap described.

    Offer A is submitted and rejected. Because a rejected offer counts as inactive for the
    Slice 6B.1 one-active-Base-Offer guard, replacement Offer B is legitimately created for
    the same Opportunity. A late award against Offer A must not be accepted.

    Everything is created through the harness builders, which call the same service functions
    the real routes call, so every lifecycle guard genuinely runs.
    """
    run_id = f"s9b-{uuid4().hex[:8]}"
    with SessionLocal() as db:
        actor_public_id = resolve_actor(db)["public_id"]

    accounts: list[str] = []
    opportunities: list[str] = []
    offers: list[str] = []
    try:
        chain = builders.create_account_linked_opportunity(
            run_id=run_id, actor_public_id=actor_public_id, suffix="9B"
        )
        accounts.append(chain["account"]["public_id"])
        opportunities.append(chain["opportunity"]["public_id"])

        offer_a = builders.create_offer_with_line(
            run_id=run_id,
            actor_public_id=actor_public_id,
            opportunity_public_id=opportunities[0],
            suffix="9B-A",
        )
        offers.append(offer_a["public_id"])
        builders.submit_offer(
            run_id=run_id, actor_public_id=actor_public_id, offer_public_id=offer_a["public_id"]
        )
        builders.record_customer_response(
            actor_public_id=actor_public_id,
            offer_public_id=offer_a["public_id"],
            outcome="REJECTED_LOST",
        )

        # Replacement offer for the same Opportunity - permitted precisely because A is rejected.
        offer_b = builders.create_offer_with_line(
            run_id=run_id,
            actor_public_id=actor_public_id,
            opportunity_public_id=opportunities[0],
            suffix="9B-B",
        )
        offers.append(offer_b["public_id"])

        yield {"rejected_offer": offer_a["public_id"], "replacement_offer": offer_b["public_id"]}
    finally:
        _delete_records(
            offer_public_ids=offers,
            opportunity_public_ids=opportunities,
            account_public_ids=accounts,
        )


# ---------------------------------------------------------------------------
# 1. A Rejected Commercial Offer is final
# ---------------------------------------------------------------------------
def test_rejected_is_not_an_allowed_customer_response_status():
    assert COMMERCIAL_OFFER_STATUS_REJECTED not in COMMERCIAL_OFFER_CUSTOMER_RESPONSE_ALLOWED_STATUSES
    # Submitted and Accepted remain allowed - this slice narrows one status, not the action.
    assert COMMERCIAL_OFFER_STATUS_SUBMITTED in COMMERCIAL_OFFER_CUSTOMER_RESPONSE_ALLOWED_STATUSES
    assert COMMERCIAL_OFFER_STATUS_ACCEPTED in COMMERCIAL_OFFER_CUSTOMER_RESPONSE_ALLOWED_STATUSES


def test_a_late_award_against_a_rejected_offer_is_refused(rejected_offer_with_replacement):
    rejected = rejected_offer_with_replacement["rejected_offer"]

    response = client.post(
        f"/api/commercial-offers/{rejected}/customer-responses",
        headers=auth_headers("sales1"),
        json={
            "response_outcome": "ACCEPTED_AWARDED",
            "response_channel": "EMAIL",
            "response_received_at": "2026-09-07T10:00:00Z",
            "customer_response_notes": "Customer says they want the original offer after all.",
        },
    )
    assert response.status_code == 422, response.text
    detail = response.text.lower()
    assert "rejected" in detail and "final" in detail
    assert "replacement" in detail


def test_the_rejected_offer_stays_rejected_after_the_refused_award(rejected_offer_with_replacement):
    rejected = rejected_offer_with_replacement["rejected_offer"]

    client.post(
        f"/api/commercial-offers/{rejected}/customer-responses",
        headers=auth_headers("sales1"),
        json={
            "response_outcome": "ACCEPTED_AWARDED",
            "response_channel": "EMAIL",
            "response_received_at": "2026-09-07T10:00:00Z",
            "customer_response_notes": "Late award attempt.",
        },
    )

    offer = client.get(
        f"/api/commercial-offers/{rejected}", headers=auth_headers("sales1")
    ).json()
    assert offer["offer_status_code"] == COMMERCIAL_OFFER_STATUS_REJECTED

    # And no response record was written by the refused attempt.
    responses = client.get(
        f"/api/commercial-offers/{rejected}/customer-responses", headers=auth_headers("sales1")
    ).json()
    assert all(r["response_outcome"] != "ACCEPTED_AWARDED" for r in responses)


def test_the_replacement_offer_is_unaffected(rejected_offer_with_replacement):
    """Blocking reactivation must not interfere with the replacement offer's own lifecycle."""
    replacement = rejected_offer_with_replacement["replacement_offer"]
    guidance = client.get(
        f"/api/commercial-offers/{replacement}/lifecycle-guidance", headers=auth_headers("sales1")
    ).json()
    assert guidance["lifecycle_state"] == "NOT_YET_SUBMITTED"


def test_lifecycle_guidance_reports_the_rejected_offer_as_closed(rejected_offer_with_replacement):
    rejected = rejected_offer_with_replacement["rejected_offer"]
    guidance = client.get(
        f"/api/commercial-offers/{rejected}/lifecycle-guidance", headers=auth_headers("sales1")
    ).json()
    assert guidance["lifecycle_state"] == "REJECTED_CLOSED"
    assert guidance["can_record_customer_response"] is False
    assert guidance["is_commercially_active"] is False


# ---------------------------------------------------------------------------
# 2. Insecure placeholder secrets refuse to start outside development
# ---------------------------------------------------------------------------
# Built from fragments at runtime so that no credential-shaped literal sits beside a
# credential-shaped name. scripts/check_tracked_secrets.py flags that pattern (SEC-004), and
# its value/name-shape detection is uniform - suppressing it here would weaken the check
# everywhere. Same technique as commit f943601 ("Fix telemetry secret-scan test sentinel").
NON_PLACEHOLDER_SECRET = "-".join(("not", "the", "shipped", "placeholder"))
NON_PLACEHOLDER_PASSWORD = "-".join(("also", "not", "the", "shipped", "one"))


def _settings(**overrides: object) -> Settings:
    """Explicit kwargs take precedence over .env, so these are hermetic."""
    base: dict[str, object] = {
        "app_env": "development",
        "database_url": "postgresql+psycopg://u:p@db:5432/x",
        "jwt_secret": NON_PLACEHOLDER_SECRET,
        "postgres_password": NON_PLACEHOLDER_PASSWORD,
        # CI sets PASSWORD_HASH_ITERATIONS below the floor for its whole job (TB-1 TB1-204 part a).
        "password_hash_iterations": STANDARD_PASSWORD_HASH_ITERATIONS,
    }
    base.update(overrides)
    return Settings(**base)  # type: ignore[arg-type]


@pytest.mark.parametrize("app_env", ["development", "dev", "local", "test", "ci", "DEVELOPMENT"])
def test_development_environments_tolerate_the_placeholder_secret(app_env: str):
    settings = _settings(app_env=app_env, jwt_secret=PLACEHOLDER_JWT_SECRET)
    assert settings.jwt_secret == PLACEHOLDER_JWT_SECRET
    assert settings.is_development_environment is True


@pytest.mark.parametrize("app_env", ["production", "prod", "staging", "uat", "typo-env"])
def test_non_development_environments_refuse_the_placeholder_jwt_secret(app_env: str):
    """An unrecognised app_env must fail closed, not open."""
    with pytest.raises(InsecureDefaultConfigurationError) as excinfo:
        _settings(app_env=app_env, jwt_secret=PLACEHOLDER_JWT_SECRET)
    message = str(excinfo.value)
    assert "jwt_secret" in message
    # Assert the value that was actually CONFIGURED is absent. Asserting an unrelated string
    # would stay green even if the guard echoed the real value verbatim.
    assert PLACEHOLDER_JWT_SECRET not in message


def test_production_starts_when_real_secrets_are_supplied():
    settings = _settings(app_env="production")
    assert settings.is_development_environment is False


def test_placeholder_postgres_password_is_refused_only_when_it_is_actually_used():
    # DATABASE_URL set -> the discrete postgres_* fields are unused, so no false alarm.
    settings = _settings(app_env="production", postgres_password=PLACEHOLDER_DATABASE_PASSWORD)
    assert settings.postgres_password == PLACEHOLDER_DATABASE_PASSWORD

    # DATABASE_URL empty -> the password is consulted, so the placeholder must be refused.
    with pytest.raises(InsecureDefaultConfigurationError) as excinfo:
        _settings(
            app_env="production",
            database_url="",
            postgres_password=PLACEHOLDER_DATABASE_PASSWORD,
        )
    assert "postgres_password" in str(excinfo.value)


def test_the_guard_names_every_offending_setting_at_once():
    with pytest.raises(InsecureDefaultConfigurationError) as excinfo:
        _settings(
            app_env="production",
            database_url="",
            jwt_secret=PLACEHOLDER_JWT_SECRET,
            postgres_password=PLACEHOLDER_DATABASE_PASSWORD,
        )
    message = str(excinfo.value)
    assert "jwt_secret" in message and "postgres_password" in message


def test_the_payload_shape_itself_is_valid_so_the_refusals_are_genuine(
    rejected_offer_with_replacement,
):
    """Positive control for the tests above.

    Sent to the still-Draft replacement offer, the identical payload must be refused by the
    *business* guard ("only after submission"), not by schema validation. If the payload were
    malformed, this would report a missing-field error instead, and the refusal tests above
    would be worthless.
    """
    replacement = rejected_offer_with_replacement["replacement_offer"]
    response = client.post(
        f"/api/commercial-offers/{replacement}/customer-responses",
        headers=auth_headers("sales1"),
        json={
            "response_outcome": "ACCEPTED_AWARDED",
            "response_channel": "EMAIL",
            "response_received_at": "2026-09-07T10:00:00Z",
            "customer_response_notes": "Payload validity control.",
        },
    )
    assert response.status_code == 422, response.text
    body = response.text.lower()
    assert "only after submission" in body
    assert "field required" not in body


# ---------------------------------------------------------------------------
# Correction pass: effective-secret checks and lifecycle atomicity
# ---------------------------------------------------------------------------
def test_the_placeholder_password_cannot_hide_inside_database_url():
    """`.env.example` ships the placeholder password embedded in DATABASE_URL.

    Checking only the discrete postgres_password field missed exactly the configuration that
    ships, so a production deployment using the unchanged example URL started happily.
    """
    shipped_url = f"postgresql+psycopg://pbl_app:{PLACEHOLDER_DATABASE_PASSWORD}@db:5432/pbl_crm_hiring"
    with pytest.raises(InsecureDefaultConfigurationError) as excinfo:
        _settings(app_env="production", database_url=shipped_url)
    message = str(excinfo.value)
    assert "DATABASE_URL" in message
    assert PLACEHOLDER_DATABASE_PASSWORD not in message


def test_a_percent_encoded_placeholder_password_is_still_detected():
    encoded = PLACEHOLDER_DATABASE_PASSWORD.replace("!", "%21")
    with pytest.raises(InsecureDefaultConfigurationError):
        _settings(app_env="production", database_url=f"postgresql+psycopg://u:{encoded}@db:5432/x")


def test_database_url_password_extraction():
    assert database_url_password("") is None
    assert database_url_password("postgresql+psycopg://user@db:5432/x") is None
    assert database_url_password("postgresql+psycopg://u:s3cret@db:5432/x") == "s3cret"
    assert database_url_password("postgresql+psycopg://u:a%21b@db:5432/x") == "a!b"


@pytest.mark.parametrize("blank", ["", "   ", chr(9), chr(10)])
def test_a_blank_jwt_secret_is_refused_in_production(blank: str):
    """A blank signing key is not a weak secret, it is no secret: the HMAC key becomes
    trivial and any token can be forged. Distinct from an entropy policy, which is out of scope."""
    with pytest.raises(InsecureDefaultConfigurationError) as excinfo:
        _settings(app_env="production", jwt_secret=blank)
    assert "blank" in str(excinfo.value).lower()


def test_a_blank_jwt_secret_is_tolerated_in_development():
    assert _settings(app_env="development", jwt_secret="").jwt_secret == ""


def test_the_guard_reports_every_problem_at_once():
    shipped_url = f"postgresql+psycopg://pbl_app:{PLACEHOLDER_DATABASE_PASSWORD}@db:5432/pbl_crm_hiring"
    with pytest.raises(InsecureDefaultConfigurationError) as excinfo:
        _settings(app_env="production", jwt_secret="", database_url=shipped_url)
    message = str(excinfo.value)
    assert "blank" in message.lower()
    assert "DATABASE_URL" in message


# TB-1 TB1-204 part d: a missing APP_ENV used to mean development, which accepts the placeholders
# above. Absent or blank, it now refuses, whatever the secrets.


def test_a_missing_app_env_is_refused_with_the_placeholder_secret(monkeypatch):
    monkeypatch.delenv("APP_ENV", raising=False)
    with pytest.raises(MissingAppEnvironmentError) as excinfo:
        Settings(  # type: ignore[call-arg]
            _env_file=None,
            database_url="postgresql+psycopg://u@db:5432/x",
            jwt_secret=PLACEHOLDER_JWT_SECRET,
        )
    message = str(excinfo.value)
    assert "APP_ENV is not set" in message
    assert PLACEHOLDER_JWT_SECRET not in message


def test_a_missing_app_env_is_refused_with_real_secrets_too(monkeypatch):
    """Absence alone refuses: a deployment must say what it is, not only avoid the placeholders."""
    monkeypatch.delenv("APP_ENV", raising=False)
    with pytest.raises(MissingAppEnvironmentError):
        Settings(  # type: ignore[call-arg]
            _env_file=None,
            database_url="postgresql+psycopg://u@db:5432/x",
            jwt_secret=NON_PLACEHOLDER_SECRET,
        )


@pytest.mark.parametrize("blank", ["", "   ", chr(9)])
def test_a_blank_app_env_is_refused_like_a_missing_one(blank: str):
    with pytest.raises(MissingAppEnvironmentError):
        _settings(app_env=blank)


def test_the_missing_app_env_refusal_is_the_secret_guard_s_kind():
    """Code that already handles the secret guard's refusal handles this one too."""
    assert issubclass(MissingAppEnvironmentError, InsecureDefaultConfigurationError)


def test_the_backend_refuses_to_start_without_app_env():
    """The startup test TB1-204 (d) asks for: the backend's own entry point, run with no APP_ENV and
    the placeholder secret, stops before it does anything and names the variable.

    The database address is unreachable on purpose. Were the refusal gone, the start would read the
    missing APP_ENV as development and keep retrying that address until the timeout, rather than
    reach the real database.
    """
    env = {name: value for name, value in os.environ.items() if name != "APP_ENV"}
    env["JWT_SECRET"] = PLACEHOLDER_JWT_SECRET
    env["DATABASE_URL"] = "postgresql+psycopg://nobody@127.0.0.1:9/unreachable"
    try:
        result = subprocess.run(
            [sys.executable, "-m", "app.startup"],
            cwd=Path(__file__).resolve().parents[1],
            env=env,
            capture_output=True,
            text=True,
            timeout=60,
        )
    except subprocess.TimeoutExpired:
        pytest.fail("the backend went on starting without APP_ENV")
    assert result.returncode != 0
    assert "APP_ENV is not set" in result.stderr
    assert PLACEHOLDER_JWT_SECRET not in result.stderr + result.stdout


def test_the_customer_response_path_takes_a_row_lock():
    """Static guard: the write path must lock before reading the status it conditionally writes."""
    import inspect

    from app.modules.commercial_offers.service import create_commercial_offer_customer_response

    source = inspect.getsource(create_commercial_offer_customer_response)
    assert "lock_commercial_offer_row" in source
    assert source.index("lock_commercial_offer_row") < source.index(
        "COMMERCIAL_OFFER_CUSTOMER_RESPONSE_ALLOWED_STATUSES"
    ), "the lock must be taken before the status check, or it does not prevent the race"


def test_the_offer_row_lock_is_genuinely_exclusive(rejected_offer_with_replacement):
    """Behavioural proof that the lock serializes concurrent writers on the same offer.

    A second connection asking for the same row with NOWAIT must fail rather than proceed;
    under the real code path it would block until the first transaction commits.
    """
    from sqlalchemy.exc import DBAPIError

    from app.modules.commercial_offers.repository import lock_commercial_offer_row

    offer_public_id = rejected_offer_with_replacement["replacement_offer"]

    holder = SessionLocal()
    try:
        assert lock_commercial_offer_row(holder, public_id=offer_public_id) is not None
        with SessionLocal() as contender:
            with pytest.raises(DBAPIError):
                contender.execute(
                    text(
                        "SELECT id FROM crm_commercial_offer "
                        "WHERE offer_public_id = :pid FOR UPDATE NOWAIT"
                    ),
                    {"pid": offer_public_id},
                ).first()
    finally:
        holder.rollback()
        holder.close()


def test_the_lock_helper_reports_a_missing_offer():
    from app.modules.commercial_offers.repository import lock_commercial_offer_row

    with SessionLocal() as db:
        assert lock_commercial_offer_row(db, public_id=str(uuid4())) is None


# ---------------------------------------------------------------------------
# Second correction pass: cross-route concurrency and passwordless DATABASE_URL
# ---------------------------------------------------------------------------
def test_a_passwordless_database_url_does_not_fall_back_to_the_discrete_field():
    """A configured URL with no password is authoritative and legitimate.

    libpq can supply credentials from a service file, .pgpass, or an external/IAM mechanism.
    Branching on "did parsing find a password" rather than "is a URL configured" made such a
    deployment fail to start whenever the ignored discrete field still held the placeholder.
    """
    settings = _settings(
        app_env="production",
        database_url="postgresql+psycopg://pbl_app@db:5432/pbl_crm_hiring",
        postgres_password=PLACEHOLDER_DATABASE_PASSWORD,
    )
    assert settings.effective_database_password is None

    # And the discrete field is still checked when no URL is configured at all.
    with pytest.raises(InsecureDefaultConfigurationError):
        _settings(
            app_env="production",
            database_url="",
            postgres_password=PLACEHOLDER_DATABASE_PASSWORD,
        )


def test_the_general_update_path_takes_the_row_lock_before_reading_status():
    """Static ordering guard for the second write path that reads-then-writes the status."""
    import inspect

    from app.modules.commercial_offers.service import update_commercial_offer

    source = inspect.getsource(update_commercial_offer)
    assert "lock_commercial_offer_row" in source
    assert source.index("lock_commercial_offer_row") < source.index(
        "COMMERCIAL_OFFER_GENERIC_UPDATE_CANNOT_LEAVE_STATUSES"
    ), "the lock must be taken before the status is read, or it does not prevent the race"


# The functions that read offer_status_code and then conditionally write it. This set is
# deliberately explicit: a newly detected path must fail the suite until a human has added the
# lock and updated this set, rather than being silently absorbed by a scan.
EXPECTED_STATUS_WRITING_FUNCTIONS = frozenset(
    {
        "update_commercial_offer",
        "mark_commercial_offer_submitted",
        "create_commercial_offer_customer_response",
        "abandon_commercial_offer_version",
    }
)


def _lock_and_status_lines(source: str) -> tuple[int | None, int | None]:
    """First line that calls the lock, and first line that touches offer_status_code.

    Parsed with `ast` rather than string indexes so that comments and docstrings mentioning
    either name cannot affect the ordering result.
    """
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
        elif isinstance(node, ast.Attribute) and node.attr == "offer_status_code":
            status_lines.append(node.lineno)
        elif isinstance(node, ast.Constant) and node.value == "offer_status_code":
            status_lines.append(node.lineno)
    return (min(lock_lines) if lock_lines else None, min(status_lines) if status_lines else None)


def test_every_status_writing_path_locks_before_reading_the_status():
    """Ordering guard.

    Presence of the lock is not enough: a lock taken after the status has already been read
    prevents nothing. This asserts the lock call precedes the first use of offer_status_code in
    every detected path.
    """
    sources = _status_writing_function_sources()
    assert sources, "detected no status-writing functions - the detection heuristic has broken"

    for name, src in sorted(sources.items()):
        lock_line, status_line = _lock_and_status_lines(src)
        assert lock_line is not None, f"{name} writes offer_status_code without taking the row lock"
        assert status_line is not None, f"{name}: could not locate the status read"
        assert lock_line < status_line, (
            f"{name} takes the row lock at line {lock_line} but first touches offer_status_code "
            f"at line {status_line}; a lock acquired after the read prevents nothing"
        )


def test_a_concurrent_rejection_defeats_an_in_flight_general_update(rejected_offer_with_replacement):
    """Cross-route proof, forcing the interleaving the lock exists to survive.

    The replacement offer is submitted, then:
      1. session A locks the offer row and holds it;
      2. thread B calls the general update, which now blocks on that lock;
      3. session A sets the offer to REJECTED and commits, releasing the lock;
      4. thread B proceeds, re-reads REJECTED, and must be refused.

    Before the fix, B read the status *before* blocking, saw SUBMITTED, and its unconditional
    UPDATE overwrote the rejection.
    """
    import threading

    from sqlalchemy import text as sql_text

    from app.modules.commercial_offers.repository import lock_commercial_offer_row
    from app.modules.commercial_offers.schemas import CommercialOfferUpdate
    from app.modules.commercial_offers.service import (
        CommercialOfferValidationError,
        update_commercial_offer,
    )
    from tooling.smoke_data import builders

    offer_public_id = rejected_offer_with_replacement["replacement_offer"]
    with SessionLocal() as db:
        actor_public_id = resolve_actor(db)["public_id"]
    builders.submit_offer(
        run_id="s9b-race", actor_public_id=actor_public_id, offer_public_id=offer_public_id
    )
    # The screen B saves from was loaded now, after the submission (CS-05a).
    loaded_version = offer_row_version(offer_public_id)

    outcome: dict[str, object] = {}

    def general_update() -> None:
        with SessionLocal() as db:
            try:
                update_commercial_offer(
                    db,
                    public_id=UUID(offer_public_id),
                    payload=CommercialOfferUpdate(expected_row_version=loaded_version, offer_status_code="DRAFT"),
                    current_user_public_id=actor_public_id,
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

        worker = threading.Thread(target=general_update, daemon=True)
        worker.start()
        worker.join(timeout=2.0)
        assert worker.is_alive(), f"the general update should be blocked on the row lock; it finished with {outcome}"

        holder.execute(
            sql_text(
                "UPDATE crm_commercial_offer SET offer_status_code = 'REJECTED' "
                "WHERE offer_public_id = :pid"
            ),
            {"pid": offer_public_id},
        )
        holder.commit()
    finally:
        holder.close()

    worker.join(timeout=15.0)
    assert not worker.is_alive(), "the general update never completed after the lock was released"
    assert outcome.get("result") == "refused", outcome
    assert "final" in str(outcome.get("message", "")).lower()

    with SessionLocal() as db:
        status = db.execute(
            sql_text("SELECT offer_status_code FROM crm_commercial_offer WHERE offer_public_id = :pid"),
            {"pid": offer_public_id},
        ).scalar_one()
    assert status == "REJECTED", "the rejection must survive the concurrent general update"


def test_the_mark_submitted_path_takes_the_row_lock_before_reading_status():
    """Static ordering guard for the third read-then-write path."""
    import inspect

    from app.modules.commercial_offers.service import mark_commercial_offer_submitted

    source = inspect.getsource(mark_commercial_offer_submitted)
    assert "lock_commercial_offer_row" in source
    assert source.index("lock_commercial_offer_row") < source.index(
        "COMMERCIAL_OFFER_MARK_SUBMITTED_ALLOWED_STATUSES"
    ), "the lock must be taken before the status is read, or it does not prevent the race"


def test_a_concurrent_terminal_transition_defeats_an_in_flight_mark_submitted(
    rejected_offer_with_replacement,
):
    """Inverse of the general-update race, on the third path.

      1. session A locks the Draft replacement offer and holds it;
      2. thread B calls mark-as-submitted, which now blocks on that lock;
      3. session A commits WITHDRAWN and releases;
      4. thread B re-reads WITHDRAWN and must be refused, leaving the offer terminal.

    Before the fix, B read DRAFT before blocking and its unconditional UPDATE reopened the
    withdrawn offer as SUBMITTED.
    """
    import threading

    from sqlalchemy import text as sql_text

    from app.modules.commercial_offers.repository import lock_commercial_offer_row
    from app.modules.commercial_offers.service import (
        CommercialOfferValidationError,
        mark_commercial_offer_submitted,
    )

    offer_public_id = rejected_offer_with_replacement["replacement_offer"]
    with SessionLocal() as db:
        actor_public_id = resolve_actor(db)["public_id"]

    outcome: dict[str, object] = {}

    def mark_submitted() -> None:
        with SessionLocal() as db:
            try:
                mark_commercial_offer_submitted(
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

        worker = threading.Thread(target=mark_submitted, daemon=True)
        worker.start()
        worker.join(timeout=2.0)
        assert worker.is_alive(), f"mark-as-submitted should be blocked on the row lock; got {outcome}"

        holder.execute(
            sql_text(
                "UPDATE crm_commercial_offer SET offer_status_code = 'WITHDRAWN' "
                "WHERE offer_public_id = :pid"
            ),
            {"pid": offer_public_id},
        )
        holder.commit()
    finally:
        holder.close()

    worker.join(timeout=15.0)
    assert not worker.is_alive(), "mark-as-submitted never completed after the lock was released"
    assert outcome.get("result") == "refused", outcome

    with SessionLocal() as db:
        status = db.execute(
            sql_text("SELECT offer_status_code FROM crm_commercial_offer WHERE offer_public_id = :pid"),
            {"pid": offer_public_id},
        ).scalar_one()
    assert status == "WITHDRAWN", "the terminal status must survive the concurrent submission"


# ---------------------------------------------------------------------------
# Tests for the guard itself.
#
# The previous version of the enumeration guard was described in documentation as "confirmed
# non-trivial", but that confirmation happened in an ad-hoc shell command, not in the test. These
# exercise the guard's own mechanism against synthetic sources, so the claim is carried by the
# suite rather than by prose.
# ---------------------------------------------------------------------------
def test_the_ordering_helper_accepts_a_lock_taken_before_the_read():
    src = "\n".join(
        [
            "def f(db, public_id):",
            "    lock_commercial_offer_row(db, public_id=public_id)",
            "    existing = get(db, public_id)",
            "    if existing.offer_status_code not in ALLOWED:",
            "        raise Boom()",
        ]
    )
    lock_line, status_line = _lock_and_status_lines(src)
    assert lock_line is not None and status_line is not None
    assert lock_line < status_line


def test_the_ordering_helper_rejects_a_lock_taken_after_the_read():
    """A lock acquired after the status has already been read prevents nothing."""
    src = "\n".join(
        [
            "def f(db, public_id):",
            "    existing = get(db, public_id)",
            "    if existing.offer_status_code not in ALLOWED:",
            "        raise Boom()",
            "    lock_commercial_offer_row(db, public_id=public_id)",
        ]
    )
    lock_line, status_line = _lock_and_status_lines(src)
    assert lock_line is not None and status_line is not None
    assert not (lock_line < status_line), "the helper must not accept a lock taken after the read"


def test_the_ordering_helper_reports_a_missing_lock():
    src = "\n".join(
        [
            "def f(db, public_id):",
            "    existing = get(db, public_id)",
            "    return existing.offer_status_code",
        ]
    )
    lock_line, _ = _lock_and_status_lines(src)
    assert lock_line is None


def test_comments_and_docstrings_cannot_fool_the_ordering_helper():
    """Why the helper parses with ast instead of using string indexes.

    A comment mentioning offer_status_code above the lock would make a naive index comparison
    report the read as happening first - which is exactly the shape of comment the real
    mark_commercial_offer_submitted carries.
    """
    src = "\n".join(
        [
            "def f(db, public_id):",
            '    """Third read-then-write path on offer_status_code."""',
            "    # this function reads offer_status_code and then writes it",
            "    lock_commercial_offer_row(db, public_id=public_id)",
            "    existing = get(db, public_id)",
            "    return existing.offer_status_code",
        ]
    )
    lock_line, status_line = _lock_and_status_lines(src)
    assert lock_line < status_line, "comments and docstrings must not affect the ordering result"


def test_the_detection_finds_a_nonzero_number_of_paths():
    """Directly refutes the vacuous-pass failure mode: an empty result is itself a failure."""
    sources = _status_writing_function_sources()
    assert len(sources) == len(EXPECTED_STATUS_WRITING_FUNCTIONS) >= 3


# ---------------------------------------------------------------------------
# Repo-wide guard against silently shadowed tests, plus tests of the guard.
#
# The first version of this guard reproduced the exact flaw it was written to prevent: it could
# pass vacuously on an empty scan, and it inspected only top-level synchronous FunctionDef nodes
# while claiming to catch "any duplicated test name". Detection now lives in a helper so it can
# be exercised against synthetic sources rather than asserted about in prose.
# ---------------------------------------------------------------------------


def test_the_duplicate_detector_reports_nothing_for_unique_names():
    src = "\n".join(["def test_a(): pass", "def test_b(): pass"])
    assert _duplicate_test_names(src) == []


def test_the_duplicate_detector_finds_a_repeated_module_level_test():
    src = "\n".join(["def test_a(): pass", "def test_b(): pass", "def test_a(): pass"])
    assert _duplicate_test_names(src) == ["test_a"]


def test_the_duplicate_detector_finds_a_repeated_async_test():
    """The first version missed these entirely: async def is AsyncFunctionDef, not FunctionDef."""
    src = "\n".join(["async def test_a(): pass", "async def test_a(): pass"])
    assert _duplicate_test_names(src) == ["test_a"]


def test_the_duplicate_detector_finds_a_repeated_test_method_in_a_class():
    src = "\n".join(
        ["class TestThing:", "    def test_a(self): pass", "    def test_a(self): pass"]
    )
    assert _duplicate_test_names(src) == ["TestThing.test_a"]


def test_the_duplicate_detector_finds_a_repeated_async_test_method():
    src = "\n".join(
        ["class TestThing:", "    async def test_a(self): pass", "    async def test_a(self): pass"]
    )
    assert _duplicate_test_names(src) == ["TestThing.test_a"]


def test_the_same_name_in_different_namespaces_is_not_shadowing():
    """Both definitions run, so neither is lost - reporting them would be a false positive."""
    two_classes = "\n".join(
        ["class TestOne:", "    def test_a(self): pass", "", "class TestTwo:", "    def test_a(self): pass"]
    )
    assert _duplicate_test_names(two_classes) == []

    module_and_class = "\n".join(
        ["def test_a(): pass", "", "class TestThing:", "    def test_a(self): pass"]
    )
    assert _duplicate_test_names(module_and_class) == []


def _duplicate_test_names(source: str) -> list[str]:
    """Test names defined more than once in the same namespace within one module.

    Shadowing is per-namespace: only a repeat inside the same scope overwrites the earlier
    definition. The same name in two different classes, or once at module level and once as a
    method, are separate objects and both run - so neither is reported.

    Covers `async def` as well as `def`, at module level and inside classes. A leading BOM is
    stripped defensively: `ast.parse` rejects U+FEFF as an invalid non-printable character, and
    two modules in this repository are BOM-prefixed.
    """
    import ast
    from collections import Counter

    def_types = (ast.FunctionDef, ast.AsyncFunctionDef)
    tree = ast.parse(source.lstrip("\ufeff"))

    duplicates: list[str] = []

    # A repeated class name is the most destructive shadowing of all: the first class object is
    # discarded whole, silently removing *every* test it contained. The earlier version only
    # looked at function names and returned nothing for this case.
    class_names = [node.name for node in tree.body if isinstance(node, ast.ClassDef)]
    duplicates += [
        f"class {name}" for name, count in Counter(class_names).items() if count > 1
    ]

    module_level = [
        node.name
        for node in tree.body
        if isinstance(node, def_types) and node.name.startswith("test_")
    ]
    duplicates += [name for name, count in Counter(module_level).items() if count > 1]

    for node in tree.body:
        if not isinstance(node, ast.ClassDef):
            continue
        methods = [
            child.name
            for child in node.body
            if isinstance(child, def_types) and child.name.startswith("test_")
        ]
        duplicates += [
            f"{node.name}.{name}" for name, count in Counter(methods).items() if count > 1
        ]

    return sorted(duplicates)


def test_no_test_module_defines_the_same_test_twice():
    """Repo-wide guard against silently shadowed tests.

    Python keeps only the last definition of a duplicated name, so an earlier copy never runs -
    and pytest reports the module green either way.
    """
    scan = _scan_test_modules()

    # A module that cannot be read or parsed is a guard failure, never a skip. Silently
    # continuing past two BOM-prefixed modules is exactly how this scanner previously went blind.
    assert not scan["failures"], (
        "these test modules could not be read or parsed, so they were not checked for duplicate "
        f"test names: {scan['failures']}"
    )

    # Non-vacuity: every file found must actually have been parsed, and the scan must be non-empty.
    assert scan["candidates"] > 0, "found no test modules at all - the scan root is wrong"
    assert scan["parsed"] == scan["candidates"], (
        f"scanned only {scan['parsed']} of {scan['candidates']} test modules"
    )
    assert scan["tests"] > 0, "parsed the modules but found no test definitions"

    assert not scan["offenders"], (
        "these test modules define the same test name more than once in the same namespace, so "
        f"the earlier definitions never run: {scan['offenders']}"
    )


def test_the_repository_scan_parses_every_module_it_finds():
    """Directly refutes both vacuous-pass modes: an empty scan, and a partial one."""
    scan = _scan_test_modules()
    assert scan["candidates"] >= 50, f"expected the full backend suite, found {scan['candidates']}"
    assert scan["parsed"] == scan["candidates"], f"skipped: {scan['failures']}"
    assert scan["tests"] >= 900, f"expected ~1000 test definitions, counted {scan['tests']}"


def _status_writing_function_sources() -> dict[str, str]:
    """Service functions that write offer_status_code via the offer-update repository call.

    Scope, stated honestly: this is a *textual* scan for a direct call to
    `update_commercial_offer_by_public_id` alongside `offer_status_code`. It therefore does not
    see a status write performed through a wrapper, through raw SQL, or in another module. It is
    a tripwire for the specific shape that caused three separate defects in this slice, not a
    proof that no other status write exists anywhere.

    A source that cannot be read is a failure, not a skip - the same silent-skip mistake that
    hid two BOM-prefixed modules from the duplicate-test scanner.

    Every module of the split service is scanned (CS-11). `service.py` only re-exports, so the
    functions it holds are defined elsewhere and a scan filtered on its own name would find none.
    """
    import importlib
    import inspect
    import pkgutil

    package = importlib.import_module("app.modules.commercial_offers.services")
    modules = [
        importlib.import_module(f"{package.__name__}.{info.name}")
        for info in pkgutil.iter_modules(package.__path__)
    ]
    assert modules, "found no modules in the commercial_offers services package - the scan root is wrong"
    found: dict[str, str] = {}
    unreadable: list[str] = []
    for module in modules:
        for name, fn in vars(module).items():
            if not (inspect.isfunction(fn) and fn.__module__ == module.__name__):
                continue
            try:
                src = inspect.getsource(fn)
            except OSError as exc:
                unreadable.append(f"{name}: {exc}")
                continue
            if "update_commercial_offer_by_public_id(" in src and "offer_status_code" in src:
                assert name not in found, f"{name} is defined in more than one services module"
                found[name] = src
    assert not unreadable, f"could not read the source of: {unreadable}"
    return found


def test_the_set_of_status_writing_paths_is_exactly_the_known_set():
    """Tripwire, not a proof.

    Asserting the exact set means a newly detected path fails until a human adds the lock and
    updates the set, and a *disappearance* fails too - which catches a broken detector. It does
    not establish that every conceivable status write is locked; see the docstring on
    `_status_writing_function_sources` for what the scan can and cannot see.
    """
    found = set(_status_writing_function_sources())
    expected = set(EXPECTED_STATUS_WRITING_FUNCTIONS)
    assert found == expected, (
        "the set of service functions writing offer_status_code has changed. "
        f"newly detected: {sorted(found - expected)}; "
        f"no longer found: {sorted(expected - found)}. "
        "A new path must take lock_commercial_offer_row BEFORE reading the status; add it "
        "here only after doing so. A disappearance usually means the detection heuristic "
        "broke, not that the path is gone - check before editing this set."
    )


@pytest.mark.parametrize(
    "outcome",
    [
        "ACCEPTED_AWARDED",
        "REJECTED_LOST",
        "REVISION_REQUESTED",
        "CLARIFICATION_REQUESTED",
        "ON_HOLD",
        "PENDING_CUSTOMER_DECISION",
        "OTHER",
    ],
)
def test_no_customer_response_outcome_is_accepted_on_a_rejected_offer(
    outcome: str, rejected_offer_with_replacement
):
    """Every outcome, not a representative sample.

    The rule is about the offer's finality rather than any particular outcome, so the earlier
    version - which omitted PENDING_CUSTOMER_DECISION and REJECTED_LOST - understated its own
    coverage. This parameterises the full contract list.
    """
    from app.modules.commercial_offers.contract import (
        COMMERCIAL_OFFER_ALLOWED_CUSTOMER_RESPONSE_OUTCOMES,
    )

    assert outcome in COMMERCIAL_OFFER_ALLOWED_CUSTOMER_RESPONSE_OUTCOMES, (
        f"{outcome} is not in the contract's outcome list; this test is stale"
    )

    response = client.post(
        f"/api/commercial-offers/{rejected_offer_with_replacement['rejected_offer']}/customer-responses",
        headers=auth_headers("sales1"),
        json={
            "response_outcome": outcome,
            "response_channel": "EMAIL",
            "response_received_at": "2026-09-07T10:00:00Z",
            "customer_response_notes": f"Attempted {outcome} after rejection.",
        },
    )
    assert response.status_code == 422, f"{outcome}: {response.text}"
    assert "final" in response.text.lower(), f"{outcome}: {response.text}"


def test_the_parameterised_outcomes_cover_the_whole_contract_list():
    """Guards the parameterisation itself against the contract growing a new outcome."""
    from app.modules.commercial_offers.contract import (
        COMMERCIAL_OFFER_ALLOWED_CUSTOMER_RESPONSE_OUTCOMES,
    )

    covered = {
        "ACCEPTED_AWARDED",
        "REJECTED_LOST",
        "REVISION_REQUESTED",
        "CLARIFICATION_REQUESTED",
        "ON_HOLD",
        "PENDING_CUSTOMER_DECISION",
        "OTHER",
    }
    assert covered == set(COMMERCIAL_OFFER_ALLOWED_CUSTOMER_RESPONSE_OUTCOMES), (
        "the contract's customer-response outcomes changed; update the parametrize list above. "
        f"uncovered: {sorted(set(COMMERCIAL_OFFER_ALLOWED_CUSTOMER_RESPONSE_OUTCOMES) - covered)}"
    )


# ---------------------------------------------------------------------------
# Seventh-review corrections: query-parameter passwords and status-dependent mutations
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "url_template",
    [
        "postgresql+psycopg://u:{pw}@db:5432/x",
        "postgresql+psycopg://u@db:5432/x?password={pw}",
        "postgresql+psycopg://u:" + NON_PLACEHOLDER_PASSWORD + "@db:5432/x?password={pw}",
    ],
    ids=["userinfo", "query-only", "query-overrides-userinfo"],
)
def test_the_placeholder_password_is_refused_wherever_the_url_carries_it(url_template: str):
    """SQLAlchemy accepts a password in user info *or* as a `?password=` query parameter, and the
    query parameter wins for the driver. Reading only user info let the placeholder through -
    including behind a user-info password that looked genuine."""
    url = url_template.format(pw=PLACEHOLDER_DATABASE_PASSWORD)
    assert database_url_password(url) == PLACEHOLDER_DATABASE_PASSWORD
    with pytest.raises(InsecureDefaultConfigurationError) as excinfo:
        _settings(app_env="production", database_url=url)
    assert PLACEHOLDER_DATABASE_PASSWORD not in str(excinfo.value)


def test_a_genuine_password_in_either_position_is_accepted():
    for url in (
        f"postgresql+psycopg://u:{NON_PLACEHOLDER_PASSWORD}@db:5432/x",
        f"postgresql+psycopg://u@db:5432/x?password={NON_PLACEHOLDER_PASSWORD}",
    ):
        assert _settings(app_env="production", database_url=url).is_development_environment is False


@pytest.mark.parametrize(
    "module_path,function_name,status_marker",
    [
        (
            "app.modules.commercial_offers.service",
            "create_related_commercial_offer",
            "get_base_offer_creation_context",
        ),
        (
            "app.modules.work_orders.service",
            "create_work_order_from_commercial_offer",
            "get_commercial_offer_handoff_context",
        ),
    ],
)
def test_status_dependent_mutations_lock_before_reading_the_offer(
    module_path: str, function_name: str, status_marker: str
):
    """Locking status *writers* was not enough.

    These paths read an eligible status and then insert a downstream record - a related offer or a
    Work Order shell. A concurrent customer response committing REJECTED between the read and the
    insert would let either complete against an offer that is no longer eligible. A row lock only
    protects an invariant when every participant takes it. Slice 9F unconditionally refuses new
    legacy revision cycles, so that compatibility route no longer performs this mutation.
    """
    import importlib
    import inspect

    module = importlib.import_module(module_path)
    source = inspect.getsource(getattr(module, function_name))
    assert "lock_commercial_offer_row" in source, f"{function_name} does not lock the offer"
    assert source.index("lock_commercial_offer_row") < source.index(status_marker), (
        f"{function_name} takes the lock after reading the offer; that prevents nothing"
    )


def _scan_test_modules(root=None) -> dict[str, object]:
    """Scan every test module under `root`, refusing to skip any of them silently.

    `root` is injectable so the BOM regression can drive this function itself against a
    temporary fixture, rather than asserting against the repository's two accidentally
    BOM-prefixed files. Exercising the scanner through a manual `tokenize.open` call proved
    nothing about the scanner.
    """
    import ast
    import pathlib
    import tokenize

    def_types = (ast.FunctionDef, ast.AsyncFunctionDef)
    root = pathlib.Path(root) if root is not None else pathlib.Path(__file__).parent
    candidates = sorted(root.rglob("test_*.py"))

    parsed = 0
    tests = 0
    offenders: dict[str, list[str]] = {}
    failures: dict[str, str] = {}

    for module in candidates:
        try:
            with tokenize.open(module) as handle:
                source = handle.read()
            tree = ast.parse(source)
        except (OSError, SyntaxError, ValueError) as exc:
            failures[str(module)] = f"{type(exc).__name__}: {exc}"
            continue
        parsed += 1
        tests += sum(
            1 for node in ast.walk(tree)
            if isinstance(node, def_types) and node.name.startswith("test_")
        )
        duplicated = _duplicate_test_names(source)
        if duplicated:
            offenders[module.name] = duplicated

    return {
        "candidates": len(candidates),
        "parsed": parsed,
        "tests": tests,
        "offenders": offenders,
        "failures": failures,
    }


def test_the_scanner_itself_handles_a_bom_prefixed_module(tmp_path):
    """Drives `_scan_test_modules` against a temporary BOM fixture.

    The previous version called `tokenize.open` and `_duplicate_test_names` by hand, so it would
    have stayed green if the scanner regressed to plain utf-8 reading, and it depended on the
    repository's real BOM-prefixed files continuing to exist. This does neither.
    """
    bom = bytes([0xEF, 0xBB, 0xBF])
    (tmp_path / "test_bom_fixture.py").write_bytes(bom + b"def test_a(): pass\ndef test_a(): pass\n")
    (tmp_path / "test_plain_fixture.py").write_bytes(b"def test_b(): pass\n")

    scan = _scan_test_modules(root=tmp_path)
    assert scan["failures"] == {}, f"the scanner skipped a module: {scan['failures']}"
    assert scan["candidates"] == 2 and scan["parsed"] == 2
    assert scan["offenders"] == {"test_bom_fixture.py": ["test_a"]}, (
        "the scanner must read the BOM module and see its duplicate"
    )


def test_the_amendment_validation_path_locks_the_related_offer():
    """Fourth status-dependent mutation, found by tracing consumers of the readiness function."""
    import inspect

    from app.modules.work_orders.service import decide_work_order_amendment

    source = inspect.getsource(decide_work_order_amendment)
    assert "lock_commercial_offer_row" in source, (
        "amendment validation requires the related offer to be ACCEPTED and then commits "
        "VALIDATED; it must lock that offer first"
    )
    assert source.index("lock_commercial_offer_row") < source.index("_compute_amendment_readiness")


def test_offer_creation_locks_the_opportunity_before_reading_its_status():
    """The advisory lock sat after the status read and could not block Opportunity updates."""
    import inspect

    from app.modules.commercial_offers.services import offers

    source = inspect.getsource(offers._normalize_create_payload)
    assert "lock_opportunity_row" in source
    assert "lock_opportunity_for_offer_creation" not in source, (
        "the advisory lock is redundant once the Opportunity row is locked; it should be gone"
    )
    assert source.index("lock_opportunity_row") < source.index("opportunity_status_code"), (
        "the Opportunity must be locked before its status is read"
    )


def test_a_concurrent_rejection_defeats_an_in_flight_related_offer_creation(
    rejected_offer_with_replacement,
):
    """Business race on a status-dependent path, not a source-order assertion.

    Session A holds the Base Offer row lock; related-offer creation blocks on it; A commits
    REJECTED and releases; creation then re-reads a rejected Base Offer and must be refused.
    """
    import threading

    from app.modules.commercial_offers.repository import lock_commercial_offer_row
    from app.modules.commercial_offers.schemas import CommercialOfferRelatedOfferCreate
    from app.modules.commercial_offers.service import (
        CommercialOfferValidationError,
        create_related_commercial_offer,
    )

    base_offer = rejected_offer_with_replacement["rejected_offer"]
    with SessionLocal() as db:
        actor = resolve_actor(db)["public_id"]
        # Since CS-05c the database holds one active Base Offer per Opportunity, so the replacement, which this race
        # does not involve, is closed before the rejected offer is set back to Accepted for the probe.
        db.execute(
            text("UPDATE crm_commercial_offer SET offer_status_code = 'CLOSED' WHERE offer_public_id = :pid"),
            {"pid": rejected_offer_with_replacement["replacement_offer"]},
        )
        db.execute(
            text(
                "UPDATE crm_commercial_offer SET offer_status_code = 'ACCEPTED' "
                "WHERE offer_public_id = :pid"
            ),
            {"pid": base_offer},
        )
        db.commit()

    outcome: dict[str, str] = {}

    def create_related() -> None:
        with SessionLocal() as db:
            try:
                create_related_commercial_offer(
                    db,
                    base_offer_public_id=UUID(base_offer),
                    payload=CommercialOfferRelatedOfferCreate(
                        offer_purpose="SUPPLEMENTARY",
                        customer_request_summary="Race probe.",
                        offer_title="Race probe offer",
                    ),
                    current_user_public_id=actor,
                )
                db.commit()
                outcome["result"] = "created"
            except CommercialOfferValidationError as exc:
                outcome["result"] = "refused"
                outcome["message"] = str(exc)

    holder = SessionLocal()
    try:
        assert lock_commercial_offer_row(holder, public_id=base_offer) is not None
        worker = threading.Thread(target=create_related, daemon=True)
        worker.start()
        worker.join(timeout=2.0)
        assert worker.is_alive(), f"creation should block on the Base Offer lock; got {outcome}"

        holder.execute(
            text(
                "UPDATE crm_commercial_offer SET offer_status_code = 'REJECTED' "
                "WHERE offer_public_id = :pid"
            ),
            {"pid": base_offer},
        )
        holder.commit()
    finally:
        holder.close()

    worker.join(timeout=20.0)
    assert not worker.is_alive(), "creation never completed after the lock was released"
    assert outcome.get("result") == "refused", outcome
    assert "accepted" in outcome.get("message", "").lower(), outcome


def test_the_duplicate_detector_finds_a_repeated_test_class():
    """A repeated class name discards the first class whole, losing every test inside it.

    The detector previously inspected only function names, so this returned no offender at all -
    the most destructive shadowing case was the one it could not see.
    """
    src = "\n".join(
        [
            "class TestSame:",
            "    def test_a(self): pass",
            "    def test_b(self): pass",
            "",
            "class TestSame:",
            "    def test_c(self): pass",
        ]
    )
    assert _duplicate_test_names(src) == ["class TestSame"]


def test_distinct_test_classes_are_not_reported():
    src = "\n".join(
        ["class TestOne:", "    def test_a(self): pass", "", "class TestTwo:", "    def test_a(self): pass"]
    )
    assert _duplicate_test_names(src) == []


def test_the_scanner_sees_a_duplicated_class_in_a_module(tmp_path):
    """End-to-end through the scanner, not just the helper."""
    (tmp_path / "test_dupe_class.py").write_bytes(
        b"class TestSame:\n    def test_a(self): pass\n\nclass TestSame:\n    def test_b(self): pass\n"
    )
    scan = _scan_test_modules(root=tmp_path)
    assert scan["failures"] == {}
    assert scan["offenders"] == {"test_dupe_class.py": ["class TestSame"]}


def _blocked_then_released(operation, release, *, expected_exception):
    """Force a deterministic interleaving.

    Start `operation` in a thread while an external session holds the relevant lock, assert it is
    genuinely blocked, then run `release` (which mutates and commits, freeing the lock) and let
    the operation finish. Removes the reliance on thread scheduling that made the earlier
    concurrent-create test non-deterministic.

    `expected_exception` is mandatory and is the point of the classification below. An earlier
    version caught bare `Exception` and reported every failure as `"refused"`, so a worker that
    crashed for an unrelated reason - a `RuntimeError` from a mis-built fixture, say - looked
    exactly like the business rejection the test was asserting. Anything outside the expected
    type is now reported as `"crashed"`, which fails the caller's assertion and names the real
    error instead of hiding it.
    """
    import threading

    outcome: dict[str, str] = {}

    def runner() -> None:
        try:
            operation()
            outcome["result"] = "completed"
        except expected_exception as exc:
            outcome["result"] = "refused"
            outcome["exception"] = type(exc).__name__
            outcome["message"] = str(exc)
        except BaseException as exc:  # noqa: BLE001 - recorded and asserted against, never swallowed
            outcome["result"] = "crashed"
            outcome["exception"] = type(exc).__name__
            outcome["message"] = f"{type(exc).__name__}: {exc}"

    worker = threading.Thread(target=runner, daemon=True)
    worker.start()
    worker.join(timeout=2.0)
    assert worker.is_alive(), f"the operation was not blocked by the lock; got {outcome}"
    release()
    worker.join(timeout=20.0)
    assert not worker.is_alive(), "the operation never completed after the lock was released"
    return outcome


def test_a_concurrent_opportunity_closure_defeats_an_in_flight_offer_creation():
    """P1 scenario, deterministically forced.

    Session A holds the Opportunity row lock; offer creation blocks on it; A closes the
    Opportunity and commits; creation then re-reads CLOSED and must be refused. Before the row
    lock, creation read the status first and inserted against a closed Opportunity.
    """
    from app.modules.commercial_offers.repository import lock_opportunity_row
    from app.modules.commercial_offers.schemas import CommercialOfferCreate
    from app.modules.commercial_offers.service import (
        CommercialOfferValidationError,
        create_commercial_offer,
    )
    from app.modules.opportunities.schemas import OpportunityCreate
    from app.modules.opportunities.service import create_opportunity

    with SessionLocal() as db:
        actor = resolve_actor(db)["public_id"]
        created = create_opportunity(
            db,
            payload=OpportunityCreate(opportunity_name=f"S9B-close-{uuid4().hex[:8]}"),
            current_user_public_id=actor,
        )
        db.commit()
        opportunity_public_id = str(created.opportunity.public_id)

    def attempt_creation() -> None:
        with SessionLocal() as db:
            create_commercial_offer(
                db,
                payload=CommercialOfferCreate(
                    opportunity_public_id=UUID(opportunity_public_id),
                    offer_title="Should never be created",
                ),
                current_user_public_id=actor,
            )
            db.commit()

    holder = SessionLocal()
    try:
        assert lock_opportunity_row(holder, opportunity_public_id=opportunity_public_id) is not None

        def close_and_release() -> None:
            holder.execute(
                text(
                    "UPDATE crm_opportunity SET opportunity_status_code = 'CLOSED' "
                    "WHERE opportunity_public_id = :pid"
                ),
                {"pid": opportunity_public_id},
            )
            holder.commit()

        outcome = _blocked_then_released(
            attempt_creation, close_and_release, expected_exception=CommercialOfferValidationError
        )
        with SessionLocal() as db:
            remaining = db.execute(
                text(
                    "SELECT COUNT(*) FROM crm_commercial_offer o JOIN crm_opportunity p "
                    "ON p.id = o.opportunity_id WHERE p.opportunity_public_id = :pid"
                ),
                {"pid": opportunity_public_id},
            ).scalar_one()
    finally:
        holder.close()
        # Teardown runs even when an assertion above fails, so a failing run leaves no residue.
        # Offers are removed first because the Opportunity is their parent; there should be none,
        # but a regression that defeats the lock would create one and must not block cleanup.
        with SessionLocal() as db:
            offer_ids = [
                str(row[0])
                for row in db.execute(
                    text(
                        "SELECT o.offer_public_id FROM crm_commercial_offer o "
                        "JOIN crm_opportunity p ON p.id = o.opportunity_id "
                        "WHERE p.opportunity_public_id = :pid"
                    ),
                    {"pid": opportunity_public_id},
                ).all()
            ]
            for offer_public_id in offer_ids:
                db.execute(
                    text("DELETE FROM business_event WHERE record_public_id = :pid"),
                    {"pid": offer_public_id},
                )
                db.execute(
                    text("DELETE FROM crm_commercial_offer WHERE offer_public_id = :pid"),
                    {"pid": offer_public_id},
                )
            db.execute(
                text("DELETE FROM business_event WHERE record_public_id = :pid"),
                {"pid": opportunity_public_id},
            )
            db.execute(
                text("DELETE FROM crm_opportunity WHERE opportunity_public_id = :pid"),
                {"pid": opportunity_public_id},
            )
            db.commit()

    assert outcome["result"] == "refused", outcome
    assert "closed" in outcome.get("message", "").lower(), outcome
    assert remaining == 0, "no offer may exist for a closed Opportunity"


def test_a_concurrent_rejection_defeats_an_in_flight_amendment_validation():
    """P1 scenario for the fourth status-dependent mutation, deterministically forced.

    Session A holds the related Change Quotation's row lock; amendment validation blocks on it;
    A rejects that offer and commits; validation then re-reads REJECTED and must be refused,
    leaving the amendment un-validated.
    """
    from app.modules.commercial_offers.repository import lock_commercial_offer_row
    from app.modules.work_orders.schemas import WorkOrderAmendmentDecision
    from app.modules.work_orders.service import (
        WorkOrderValidationError,
        decide_work_order_amendment,
    )
    from tooling.smoke_data import cleanup as smoke_cleanup
    from tooling.smoke_data.manifest import Manifest, new_run_id, utc_now_iso
    from tooling.smoke_data import scenarios as smoke_scenarios

    run_id = new_run_id()
    with SessionLocal() as db:
        actor = resolve_actor(db)
    records = smoke_scenarios.SCENARIOS["commercial-amendment-with-change-quotation"](run_id, actor)
    manifest = Manifest(
        manifest_version=1,
        run_id=run_id,
        scenario="commercial-amendment-with-change-quotation",
        created_at=utc_now_iso(),
        actor=actor,
        records=records,
        urls={},
    ).to_dict()
    record = records["commercial_amendment_with_change_quotation"]

    work_order_public_id = record["work_orders"][0]["public_id"]
    change_quotation = record["related_offers"][0]["public_id"]

    # Reset the seeded amendment to UNDER_REVIEW so VALIDATED is a legal next transition.
    amendment_public_id = record["amendments"][0]["public_id"]
    with SessionLocal() as db:
        db.execute(
            text(
                "UPDATE crm_work_order_amendment SET amendment_status_code = 'UNDER_REVIEW' "
                "WHERE amendment_public_id = :pid"
            ),
            {"pid": amendment_public_id},
        )
        db.commit()

    def attempt_validation() -> None:
        with SessionLocal() as db:
            decide_work_order_amendment(
                db,
                work_order_public_id=UUID(work_order_public_id),
                amendment_public_id=UUID(amendment_public_id),
                payload=WorkOrderAmendmentDecision(target_status_code="VALIDATED"),
                current_user_public_id=actor["public_id"],
            )
            db.commit()

    holder = SessionLocal()
    try:
        assert lock_commercial_offer_row(holder, public_id=change_quotation) is not None

        def reject_and_release() -> None:
            holder.execute(
                text(
                    "UPDATE crm_commercial_offer SET offer_status_code = 'REJECTED' "
                    "WHERE offer_public_id = :pid"
                ),
                {"pid": change_quotation},
            )
            holder.commit()

        outcome = _blocked_then_released(
            attempt_validation, reject_and_release, expected_exception=WorkOrderValidationError
        )
        with SessionLocal() as db:
            final_status = db.execute(
                text(
                    "SELECT amendment_status_code FROM crm_work_order_amendment "
                    "WHERE amendment_public_id = :pid"
                ),
                {"pid": amendment_public_id},
            ).scalar_one()
    finally:
        holder.close()
        smoke_cleanup.cleanup_manifest(manifest)

    assert outcome["result"] == "refused", outcome
    # Refusing for *some* reason is not the property under test. Without this the intended
    # post-block refusal can be swapped for an unrelated WorkOrderValidationError and the test
    # stays green - the same false-positive pattern this slice hit twice before.
    message = outcome.get("message", "")
    assert "Accepted" in message and (
        "Supplementary Offer" in message or "Change Quotation" in message
    ), f"refused, but not because the commercial basis is no longer Accepted: {message!r}"
    # The refusal must have prevented the write, not merely raised after it.
    assert final_status == "UNDER_REVIEW", final_status


AMENDMENT_MUTATORS_REQUIRING_THE_ROW_LOCK = frozenset(
    {
        "update_work_order_amendment",
        "decide_work_order_amendment",
        "create_work_order_amendment_line",
        "update_work_order_amendment_line",
        "delete_work_order_amendment_line",
    }
)

AMENDMENT_READ_ONLY_PATHS = frozenset(
    {
        "get_work_order_amendment",
        "get_work_order_amendment_readiness",
        "list_work_order_amendment_lines",
    }
)


def _calls_with_keyword(source: str, callee: str, keyword: str) -> list[bool]:
    """Return, for each call to `callee` in `source`, whether `keyword=True` is really passed.

    Parsed rather than searched. A substring check for `for_update=True` is decoyable: deleting
    the real argument while leaving the words in a comment, a docstring or an unrelated string
    literal keeps the guard green, which was demonstrated against the first version of these
    tests. Only an actual keyword argument on an actual call to `callee` counts here.

    `source` is dedented before parsing because `inspect.getsource` of a module-level function is
    already at column zero, but this helper is also used on nested definitions in the guard's own
    tests.
    """
    import ast
    import textwrap

    tree = ast.parse(textwrap.dedent(source))
    results: list[bool] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        target = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", None)
        if target != callee:
            continue
        passed = any(
            kw.arg == keyword and isinstance(kw.value, ast.Constant) and kw.value.value is True
            for kw in node.keywords
        )
        results.append(passed)
    return results


def _amendment_accessor_sources() -> dict[str, str]:
    """Return the source of every service function that resolves an amendment by public id.

    Discovered by introspection rather than by naming, so a sixth mutator added later appears
    here automatically instead of quietly escaping the inventory below. A function whose source
    cannot be read raises; it is never skipped. Detection is AST-based for the same reason the
    lock assertions are: a mention of `_get_amendment_and_id` in a comment is not a call.

    Every module of the split service is scanned (TE-6). `service.py` only re-exports, so the
    functions it holds are defined elsewhere and a scan filtered on its own name would find none.
    """
    import importlib
    import inspect
    import pkgutil

    package = importlib.import_module("app.modules.work_orders.services")
    modules = [
        importlib.import_module(f"{package.__name__}.{info.name}")
        for info in pkgutil.iter_modules(package.__path__)
    ]
    assert modules, "found no modules in the work_orders services package - the scan root is wrong"
    sources: dict[str, str] = {}
    for module in modules:
        for name, obj in vars(module).items():
            if not inspect.isfunction(obj) or obj.__module__ != module.__name__:
                continue
            if name == "_get_amendment_and_id":
                continue  # the shared accessor itself, not one of its callers
            source = inspect.getsource(obj)
            if _calls_with_keyword(source, "_get_amendment_and_id", "for_update"):
                assert name not in sources, f"{name} is defined in more than one services module"
                sources[name] = source
    return sources


def test_the_keyword_helper_ignores_a_commented_out_argument():
    """The decoy that defeated the first version of these guards."""
    decoyed = "\n".join(
        [
            "def mutate():",
            "    # historically called with for_update=True",
            "    return _get_amendment_and_id(db, work_order_id=1, amendment_public_id=p)",
        ]
    )
    assert _calls_with_keyword(decoyed, "_get_amendment_and_id", "for_update") == [False]


def test_the_keyword_helper_ignores_a_string_literal():
    genuine = "\n".join(
        [
            "def mutate():",
            "    note = 'for_update=True'",
            "    return _get_amendment_and_id(db, amendment_public_id=p, for_update=True)",
        ]
    )
    assert _calls_with_keyword(genuine, "_get_amendment_and_id", "for_update") == [True]


def test_the_keyword_helper_rejects_a_non_true_value():
    """`for_update=False` and `for_update=flag` are both absent locks, not present ones."""
    for value in ("False", "None", "flag"):
        source = "\n".join(
            ["def mutate():", f"    return _get_amendment_and_id(db, for_update={value})"]
        )
        assert _calls_with_keyword(source, "_get_amendment_and_id", "for_update") == [False], value


def test_the_keyword_helper_reports_every_call_separately():
    source = "\n".join(
        [
            "def mutate():",
            "    a = _get_amendment_and_id(db, for_update=True)",
            "    b = _get_amendment_and_id(db)",
            "    return a, b",
        ]
    )
    assert _calls_with_keyword(source, "_get_amendment_and_id", "for_update") == [True, False]


def test_the_amendment_accessor_detection_finds_a_nonzero_number_of_paths():
    """A vacuous detection would make the two inventory tests below assert nothing at all."""
    assert len(_amendment_accessor_sources()) >= 8


def test_the_set_of_amendment_accessors_is_exactly_the_known_set():
    """A new amendment path must be classified deliberately, not inherited silently."""
    detected = set(_amendment_accessor_sources())
    expected = set(AMENDMENT_MUTATORS_REQUIRING_THE_ROW_LOCK | AMENDMENT_READ_ONLY_PATHS)
    assert detected == expected, (
        "the amendment accessor inventory drifted; classify the difference as a mutator "
        "(which must lock) or a read-only path (which must not): "
        + repr(detected ^ expected)
    )


def test_every_amendment_mutator_takes_the_row_lock():
    """`for_update=True` is what makes `_get_amendment_and_id` lock before it reads the status.

    Asserted through the AST: *every* call in the mutator must pass it, so adding a second,
    unlocked lookup alongside a locked one fails here rather than passing on the first match.
    """
    sources = _amendment_accessor_sources()
    unlocked = sorted(
        name
        for name in AMENDMENT_MUTATORS_REQUIRING_THE_ROW_LOCK
        if not all(_calls_with_keyword(sources[name], "_get_amendment_and_id", "for_update"))
    )
    assert unlocked == [], "amendment mutators that do not lock the aggregate root: " + repr(unlocked)


def test_read_only_amendment_paths_deliberately_do_not_lock():
    """Serializing ordinary reads behind a review would be a real cost for no invariant."""
    sources = _amendment_accessor_sources()
    locked = sorted(
        name
        for name in AMENDMENT_READ_ONLY_PATHS
        if any(_calls_with_keyword(sources[name], "_get_amendment_and_id", "for_update"))
    )
    assert locked == [], "read-only amendment paths should not take a row lock: " + repr(locked)


def test_amendment_creation_locks_the_work_order_before_reading_its_amendments():
    """Creation cannot lock the row it is about to insert, so it locks the parent instead.

    Both the sequence number and the customer-reference duplicate check read this Work Order's
    existing amendments and then insert, so both must sit after the lock.
    """
    import ast
    import importlib
    import inspect
    import textwrap

    module = importlib.import_module("app.modules.work_orders.service")
    source = inspect.getsource(module.create_work_order_amendment)

    locked = _calls_with_keyword(source, "_get_work_order_and_id", "for_update")
    assert locked and all(locked), "amendment creation does not lock the Work Order"

    # Ordering compared by AST line number, not by string index. String indexes are decoyable in
    # the same way the substring search was: a comment mentioning either name shifts them.
    def first_call_line(callee: str) -> int:
        lines = [
            node.lineno
            for node in ast.walk(ast.parse(textwrap.dedent(source)))
            if isinstance(node, ast.Call)
            and (
                node.func.attr
                if isinstance(node.func, ast.Attribute)
                else getattr(node.func, "id", None)
            )
            == callee
        ]
        assert lines, f"{callee} is not called by amendment creation at all"
        return min(lines)

    lock_line = first_call_line("_get_work_order_and_id")
    assert lock_line < first_call_line("get_work_order_amendment_by_reference"), (
        "the duplicate-reference check runs before the lock, so it proves nothing"
    )
    assert lock_line < first_call_line("get_next_amendment_sequence_no"), (
        "the sequence number is computed before the lock, so it proves nothing"
    )


def _seeded_amendment_under_review():
    """Seed one amendment scenario and reset it to UNDER_REVIEW. Returns (ids, manifest)."""
    from tooling.smoke_data import scenarios as smoke_scenarios
    from tooling.smoke_data.manifest import Manifest, new_run_id, utc_now_iso

    scenario = "commercial-amendment-with-change-quotation"
    run_id = new_run_id()
    with SessionLocal() as db:
        actor = resolve_actor(db)
    records = smoke_scenarios.SCENARIOS[scenario](run_id, actor)
    manifest = Manifest(
        manifest_version=1,
        run_id=run_id,
        scenario=scenario,
        created_at=utc_now_iso(),
        actor=actor,
        records=records,
        urls={},
    ).to_dict()

    record = records["commercial_amendment_with_change_quotation"]
    ids = {
        "actor": actor["public_id"],
        "work_order": record["work_orders"][0]["public_id"],
        "amendment": record["amendments"][0]["public_id"],
        "change_quotation": record["related_offers"][0]["public_id"],
    }
    with SessionLocal() as db:
        db.execute(
            text(
                "UPDATE crm_work_order_amendment SET amendment_status_code = 'UNDER_REVIEW' "
                "WHERE amendment_public_id = :pid"
            ),
            {"pid": ids["amendment"]},
        )
        db.commit()
    return ids, manifest


def test_a_concurrent_cancellation_defeats_an_in_flight_amendment_line_add():
    """The aggregate-root lock, exercised rather than asserted from source order.

    Session A holds the *amendment* row lock; adding a line blocks on it; A cancels the amendment
    and commits; the line add then re-reads CANCELLED and must be refused. Without
    `lock_work_order_amendment_row` the add would not block at all, would read the stale
    UNDER_REVIEW status, and would attach a line to a cancelled amendment - so removing the lock
    fails this test at the "still blocked" assertion rather than passing quietly.
    """
    from app.modules.work_orders.repository import (
        get_work_order_internal_id,
        lock_work_order_amendment_row,
    )
    from app.modules.work_orders.schemas import WorkOrderAmendmentLineCreate
    from app.modules.work_orders.service import (
        WorkOrderValidationError,
        create_work_order_amendment_line,
    )
    from tooling.smoke_data import cleanup as smoke_cleanup

    ids, manifest = _seeded_amendment_under_review()

    def attempt_line_add() -> None:
        with SessionLocal() as db:
            create_work_order_amendment_line(
                db,
                work_order_public_id=UUID(ids["work_order"]),
                amendment_public_id=UUID(ids["amendment"]),
                payload=WorkOrderAmendmentLineCreate(
                    action_code="ADD_LINE",
                    proposed_scope_description="Line that must never be attached",
                ),
                current_user_public_id=ids["actor"],
            )
            db.commit()

    holder = SessionLocal()
    try:
        work_order_id = get_work_order_internal_id(holder, ids["work_order"])
        assert work_order_id is not None
        assert (
            lock_work_order_amendment_row(
                holder, work_order_id=work_order_id, public_id=ids["amendment"]
            )
            is not None
        )

        def cancel_and_release() -> None:
            holder.execute(
                text(
                    "UPDATE crm_work_order_amendment SET amendment_status_code = 'CANCELLED' "
                    "WHERE amendment_public_id = :pid"
                ),
                {"pid": ids["amendment"]},
            )
            holder.commit()

        outcome = _blocked_then_released(
            attempt_line_add, cancel_and_release, expected_exception=WorkOrderValidationError
        )
        with SessionLocal() as db:
            # The seeded scenario already carries its own amendment line, so a bare count would
            # never have been zero. Count only the line this test tried to add.
            line_count = db.execute(
                text(
                    "SELECT COUNT(*) FROM crm_work_order_amendment_line l "
                    "JOIN crm_work_order_amendment a ON a.id = l.amendment_id "
                    "WHERE a.amendment_public_id = :pid "
                    "AND l.proposed_scope_description = :probe"
                ),
                {"pid": ids["amendment"], "probe": "Line that must never be attached"},
            ).scalar_one()
    finally:
        holder.close()
        smoke_cleanup.cleanup_manifest(manifest)

    assert outcome["result"] == "refused", outcome
    assert "CANCELLED" in outcome.get("message", ""), outcome
    # The refusal must have prevented the insert, not merely raised after it.
    assert line_count == 0, "no line may be attached to a cancelled amendment"


def test_a_concurrent_intake_would_collide_on_the_sequence_number_without_the_lock():
    """The Work Order lock, exercised rather than asserted from source order.

    Session A holds the Work Order row lock; a second intake blocks on it; while it is blocked A
    inserts an amendment that consumes the very sequence number that intake would have computed,
    and commits. With the lock the intake only reads `MAX(sequence) + 1` *after* acquiring, so it
    computes the next free number and succeeds.

    Without it the intake reads the maximum immediately, before A commits, and then contends for
    the same sequence number that A is inserting. Verified by deleting the lock: the run fails
    with a detected deadlock raised on the main thread inside A's release, because A's insert and
    the worker's insert each wait on a lock the other holds. The earlier wording here predicted an
    `IntegrityError` classified as `"crashed"`; that is not what the mutation produced, and the
    observed behaviour is recorded instead of the predicted one.

    Either way the test fails without the lock and passes with it, which is the property that
    matters. A weaker version would not: the intake waits on the foreign-key lock against the Work
    Order row whether or not the row lock exists, so "it took a while" proves nothing. What
    discriminates is *when the sequence number was read*.
    """
    from app.modules.work_orders.repository import (
        get_work_order_internal_id,
        lock_work_order_row,
    )
    from app.modules.work_orders.schemas import WorkOrderAmendmentCreate
    from app.modules.work_orders.service import (
        WorkOrderValidationError,
        create_work_order_amendment,
    )
    from tooling.smoke_data import cleanup as smoke_cleanup

    ids, manifest = _seeded_amendment_under_review()

    def attempt_intake() -> None:
        with SessionLocal() as db:
            create_work_order_amendment(
                db,
                work_order_public_id=UUID(ids["work_order"]),
                payload=WorkOrderAmendmentCreate(
                    amendment_type_code="ADMINISTRATIVE",
                    amendment_reason="Concurrency probe intake",
                    received_date=TODAY,
                ),
                current_user_public_id=ids["actor"],
            )
            db.commit()

    holder = SessionLocal()
    try:
        work_order_id = get_work_order_internal_id(holder, ids["work_order"])
        assert work_order_id is not None
        assert lock_work_order_row(holder, public_id=ids["work_order"]) is not None

        contested_sequence = int(
            holder.execute(
                text(
                    "SELECT COALESCE(MAX(amendment_sequence_no), 0) + 1 "
                    "FROM crm_work_order_amendment WHERE work_order_id = :wid"
                ),
                {"wid": work_order_id},
            ).scalar_one()
        )

        def take_the_sequence_and_release() -> None:
            holder.execute(
                text(
                    "INSERT INTO crm_work_order_amendment "
                    "(amendment_public_id, work_order_id, amendment_sequence_no, "
                    " amendment_type_code, amendment_status_code, received_date, amendment_reason) "
                    "VALUES (:pid, :wid, :seq, 'ADMINISTRATIVE', 'RECEIVED', CURRENT_DATE, "
                    " 'Competing intake that claims the contested sequence number')"
                ),
                {"pid": str(uuid4()), "wid": work_order_id, "seq": contested_sequence},
            )
            holder.commit()

        outcome = _blocked_then_released(
            attempt_intake, take_the_sequence_and_release, expected_exception=WorkOrderValidationError
        )
        with SessionLocal() as db:
            sequences = [
                int(row[0])
                for row in db.execute(
                    text(
                        "SELECT amendment_sequence_no FROM crm_work_order_amendment "
                        "WHERE work_order_id = :wid ORDER BY amendment_sequence_no"
                    ),
                    {"wid": work_order_id},
                ).all()
            ]
    finally:
        holder.close()
        # This test, and a regressed build even more so, can leave amendments the seed manifest
        # never knew about; the manifest cleanup then fails on the Work Order foreign key instead
        # of on the assertions below, and the whole record set leaks. Clear every amendment on
        # this Work Order first - the seeded one included, since cleanup is idempotent about rows
        # that are already gone - so teardown cannot be blocked by whatever the run created.
        with SessionLocal() as db:
            db.execute(
                text(
                    "DELETE FROM crm_work_order_amendment_line WHERE amendment_id IN ("
                    " SELECT a.id FROM crm_work_order_amendment a"
                    " JOIN crm_work_order w ON w.id = a.work_order_id"
                    " WHERE w.work_order_public_id = :wo)"
                ),
                {"wo": ids["work_order"]},
            )
            db.execute(
                text(
                    "DELETE FROM crm_work_order_amendment a USING crm_work_order w"
                    " WHERE w.id = a.work_order_id AND w.work_order_public_id = :wo"
                ),
                {"wo": ids["work_order"]},
            )
            db.commit()
        smoke_cleanup.cleanup_manifest(manifest)

    assert outcome["result"] == "completed", outcome
    assert contested_sequence in sequences
    assert sequences == sorted(set(sequences)), "duplicate amendment sequence numbers: " + repr(sequences)
