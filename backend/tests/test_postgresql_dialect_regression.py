"""PostgreSQL dialect regression cover for the TE-2B Part 2 conversion (ADR-028).

Every test here pins behaviour that changed shape when the active repository SQL moved
from T-SQL to PostgreSQL. They are deliberately narrow: each one fails if a specific
converted construct is reverted or mistranslated, rather than re-testing business rules
that the module suites already own.

These tests run against the Docker development PostgreSQL database, like the rest of the
backend suite, and clean up every record they create.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.core.database import SessionLocal
from app.main import app

client = TestClient(app)

BACKEND_ROOT = Path(__file__).resolve().parents[1]


def auth_headers(username: str = "sales1") -> dict[str, str]:
    response = client.post(
        "/api/auth/login",
        json={"username": username, "password": "password"},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def create_account(name_suffix: str = "") -> dict[str, object]:
    response = client.post(
        "/api/accounts",
        headers=auth_headers("sales1"),
        json={
            "account_name": f"TE2B Dialect Account {name_suffix}{uuid4()}",
            "qualification_source": "manual",
        },
    )
    assert response.status_code == 201
    return response.json()["account"]


def cleanup_accounts(public_ids: list[str]) -> None:
    if not public_ids:
        return
    with SessionLocal() as db:
        for public_id in public_ids:
            db.execute(
                text(
                    """
                    DELETE FROM business_party_contact
                    USING business_party bp
                    WHERE bp.id = business_party_contact.business_party_id
                      AND bp.business_party_public_id = :public_id
                    """
                ),
                {"public_id": public_id},
            )
            db.execute(
                text("DELETE FROM business_event WHERE record_public_id = :public_id"),
                {"public_id": public_id},
            )
            db.execute(
                text("DELETE FROM business_party WHERE business_party_public_id = :public_id"),
                {"public_id": public_id},
            )
        db.commit()


# --------------------------------------------------------------------------------------
# Paging: OFFSET n ROWS / FETCH NEXT n ROWS ONLY  ->  LIMIT n OFFSET n
# --------------------------------------------------------------------------------------


def test_account_list_paging_returns_disjoint_ordered_pages() -> None:
    """The Account list paging was `OFFSET ... ROWS FETCH NEXT ... ROWS ONLY`.

    A LIMIT/OFFSET mistranslation that swapped the two arguments would still return rows,
    so this asserts the pages are the right sizes AND genuinely disjoint.
    """
    created: list[str] = []
    try:
        for _ in range(3):
            created.append(str(create_account()["public_id"]))

        first = client.get("/api/accounts?limit=2&offset=0", headers=auth_headers("sales1"))
        second = client.get("/api/accounts?limit=2&offset=2", headers=auth_headers("sales1"))
        assert first.status_code == 200
        assert second.status_code == 200

        first_ids = [row["public_id"] for row in first.json()]
        second_ids = [row["public_id"] for row in second.json()]

        assert len(first_ids) == 2
        assert not set(first_ids) & set(second_ids), "LIMIT/OFFSET pages must not overlap"

        # offset=1 must start exactly where offset=0's second row was.
        shifted = client.get("/api/accounts?limit=2&offset=1", headers=auth_headers("sales1"))
        assert shifted.status_code == 200
        assert [row["public_id"] for row in shifted.json()][0] == first_ids[1]
    finally:
        cleanup_accounts(created)


def test_events_recent_limit_is_applied() -> None:
    """`SELECT TOP {safe_limit}` became `LIMIT {safe_limit}` placed after ORDER BY."""
    response = client.get("/api/events/recent?limit=3", headers=auth_headers("admin1"))

    assert response.status_code == 200
    assert len(response.json()) <= 3


def test_single_row_lookup_by_public_id_returns_the_requested_record() -> None:
    """Many `SELECT TOP 1 ... WHERE public_id = :id` lookups became `... LIMIT 1`.

    The LIMIT had to land after the WHERE clause; if it were placed before it, or the
    WHERE were dropped, this would return the wrong record rather than error.
    """
    created: list[str] = []
    try:
        first = str(create_account("first ")["public_id"])
        second = str(create_account("second ")["public_id"])
        created.extend([first, second])

        response = client.get(f"/api/accounts/{first}", headers=auth_headers("sales1"))

        assert response.status_code == 200
        assert response.json()["public_id"] == first
    finally:
        cleanup_accounts(created)


# --------------------------------------------------------------------------------------
# Booleans: BIT/integer 1/0  ->  real PostgreSQL boolean
# --------------------------------------------------------------------------------------


def test_flag_columns_are_real_booleans_not_integers() -> None:
    with SessionLocal() as db:
        rows = db.execute(
            text(
                """
                SELECT table_name, column_name, data_type
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND column_name IN (
                      'is_active', 'is_primary', 'active', 'is_selected_basis',
                      'is_strategic_account', 'applies_to_header', 'applies_to_line',
                      'mandatory_default'
                  )
                """
            )
        ).all()

    assert rows, "expected flag columns to exist"
    non_boolean = [(r._mapping["table_name"], r._mapping["column_name"], r._mapping["data_type"]) for r in rows if r._mapping["data_type"] != "boolean"]
    assert non_boolean == [], f"flag columns must be PostgreSQL boolean, found: {non_boolean}"


def test_contact_insert_defaults_is_active_true_and_boolean_filter_excludes_deactivated() -> None:
    """Covers both converted forms at once.

    The insert wrote a literal `1` into a boolean column (now `TRUE`), and the list query
    filtered with `c.is_active = 1` (now `c.is_active IS TRUE`). Either left unconverted
    raises DatatypeMismatch; a filter dropped entirely would still return the row after
    deactivation, which this asserts against.
    """
    created: list[str] = []
    try:
        account_public_id = str(create_account()["public_id"])
        created.append(account_public_id)

        create_response = client.post(
            f"/api/accounts/{account_public_id}/contacts",
            headers=auth_headers("sales1"),
            json={"contact_name": "TE2B Dialect Contact", "is_primary": True},
        )
        assert create_response.status_code == 201
        contact = create_response.json()["contact"]
        assert contact["is_active"] is True
        assert contact["is_primary"] is True

        listed = client.get(
            f"/api/accounts/{account_public_id}/contacts",
            headers=auth_headers("sales1"),
        )
        assert listed.status_code == 200
        assert contact["public_id"] in [row["public_id"] for row in listed.json()]

        with SessionLocal() as db:
            db.execute(
                text("UPDATE business_party_contact SET is_active = FALSE WHERE contact_public_id = :public_id"),
                {"public_id": contact["public_id"]},
            )
            db.commit()

        after = client.get(
            f"/api/accounts/{account_public_id}/contacts",
            headers=auth_headers("sales1"),
        )
        assert after.status_code == 200
        assert contact["public_id"] not in [row["public_id"] for row in after.json()], (
            "IS TRUE filter must exclude a deactivated contact"
        )
    finally:
        cleanup_accounts(created)


# --------------------------------------------------------------------------------------
# Timestamps: SYSUTCDATETIME()  ->  CURRENT_TIMESTAMP on a UTC session
# --------------------------------------------------------------------------------------


def test_session_time_zone_is_utc() -> None:
    with SessionLocal() as db:
        assert db.execute(text("SHOW TimeZone")).scalar() == "UTC"


def test_created_at_is_written_as_utc_and_business_event_recorded() -> None:
    """`SYSUTCDATETIME()` returned UTC. `CURRENT_TIMESTAMP` returns timestamptz, which is
    converted to the naive column using the session time zone -- so this only stays UTC
    because the session is pinned to UTC. A session left on local time would silently
    store shifted business timestamps, which this catches.
    """
    created: list[str] = []
    try:
        # Naive UTC, to compare directly against the naive `timestamp without time zone`
        # column the application writes.
        utc_now = datetime.now(timezone.utc).replace(tzinfo=None)
        before = utc_now - timedelta(minutes=5)
        account = create_account()
        created.append(str(account["public_id"]))
        after = utc_now + timedelta(minutes=5)

        with SessionLocal() as db:
            stored = db.execute(
                text("SELECT created_at, updated_at FROM business_party WHERE business_party_public_id = :public_id"),
                {"public_id": account["public_id"]},
            ).one()

        created_at = stored._mapping["created_at"]
        assert created_at.tzinfo is None, "business timestamps are stored naive (UTC)"
        assert before <= created_at <= after, f"created_at {created_at} is not UTC-aligned"

        with SessionLocal() as db:
            event_count = db.execute(
                text(
                    """
                    SELECT count(*) FROM business_event
                    WHERE record_public_id = :public_id AND event_name = 'AccountCreated'
                    """
                ),
                {"public_id": account["public_id"]},
            ).scalar()
        assert event_count == 1, "business event recording must survive the timestamp conversion"
    finally:
        cleanup_accounts(created)


# --------------------------------------------------------------------------------------
# ISNULL -> COALESCE, and T-SQL '+' string concatenation -> '||'
# --------------------------------------------------------------------------------------


def test_coalesce_max_returns_zero_for_an_empty_set() -> None:
    """`ISNULL(MAX(col), 0)` became `COALESCE(MAX(col), 0)`.

    MAX over no rows is NULL; without the COALESCE the amendment sequence/line numbering
    would produce NULL rather than 0.
    """
    with SessionLocal() as db:
        value = db.execute(
            text(
                """
                SELECT COALESCE(MAX(amendment_sequence_no), 0)
                FROM crm_work_order_amendment
                WHERE work_order_id = -1
                """
            )
        ).scalar_one()

    assert value == 0


def test_business_reference_concatenation_pads_identically_to_the_tsql_form() -> None:
    """`'CO-' + RIGHT('000000' + CAST(id AS VARCHAR(20)), 6)` became `||` concatenation.

    ADR-007 makes these visible business references, so the padded width and truncation
    behaviour must match the T-SQL form exactly, not merely produce some string.
    """
    with SessionLocal() as db:
        for identity, expected in ((1, "CO-000001"), (123, "CO-000123"), (999999, "CO-999999")):
            rendered = db.execute(
                text("SELECT 'CO-' || RIGHT('000000' || CAST(:identity AS VARCHAR(20)), 6)"),
                {"identity": identity},
            ).scalar_one()
            assert rendered == expected


# --------------------------------------------------------------------------------------
# Case sensitivity: PostgreSQL compares case-sensitively where SQL Server's default
# collation did not. These pin the normalization the application already performs, and the
# explicit case-insensitive rule added for usernames.
# --------------------------------------------------------------------------------------


def test_pan_and_status_codes_are_normalized_before_they_reach_postgresql() -> None:
    """PAN/GSTIN are upper-normalized and status codes are upper-normalized at the service
    layer. That normalization is what makes case-sensitive PostgreSQL comparison safe, so
    removing it would reintroduce a silent lookup failure.
    """
    created: list[str] = []
    try:
        response = client.post(
            "/api/accounts",
            headers=auth_headers("sales1"),
            json={
                "account_name": f"TE2B Case Account {uuid4()}",
                "qualification_source": "MANUAL",
                "account_status_code": "draft",
                "pan": "abcde1234f",
            },
        )
        assert response.status_code == 201
        account = response.json()["account"]
        created.append(str(account["public_id"]))

        assert account["pan"] == "ABCDE1234F"
        assert account["account_status_code"] == "DRAFT"
        assert account["qualification_source"] == "manual"
    finally:
        cleanup_accounts(created)


def test_login_accepts_any_username_case_and_returns_the_stored_username() -> None:
    """Case-insensitive login is preserved across the migration.

    SQL Server's default collation matched usernames case-insensitively. PostgreSQL compares
    case-sensitively, so the rule is now explicit in the login query. The authenticated
    identity must remain the stored/canonical username, not whatever case the caller typed,
    because the username is the token subject and is echoed in responses.
    """
    for submitted in ("sales1", "SALES1", "Sales1", "sAlEs1"):
        response = client.post(
            "/api/auth/login",
            json={"username": submitted, "password": "password"},
        )
        assert response.status_code == 200, f"login failed for {submitted!r}"

        body = response.json()
        assert body["user"]["username"] == "sales1", (
            f"login as {submitted!r} must resolve to the stored username, "
            f"got {body['user']['username']!r}"
        )
        assert "SALES_USER" in body["user"]["role_codes"]
        assert body["access_token"]

    # A wrong password must still fail regardless of the case used.
    wrong = client.post("/api/auth/login", json={"username": "SALES1", "password": "nope"})
    assert wrong.status_code == 401


def test_authenticated_identity_carries_the_stored_username_not_the_submitted_case() -> None:
    """The token issued for an odd-case login must identify the canonical user."""
    token = client.post(
        "/api/auth/login",
        json={"username": "ADMIN1", "password": "password"},
    ).json()["access_token"]

    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert me.status_code == 200
    assert me.json()["username"] == "admin1"
    assert "ADMIN" in me.json()["role_codes"]


def test_case_only_duplicate_username_is_rejected_by_the_database() -> None:
    """`ux_app_user_username_lower` enforces uniqueness on the same basis login matches on.

    Without it, inserting `SALES1` alongside `sales1` would succeed and make the
    case-insensitive login lookup ambiguous - it could return either row, or raise on the
    `.one()` in the caller. The constraint is what makes case-insensitive login safe, so it
    is asserted at the database level rather than trusted.
    """
    inserted_public_id = str(uuid4())
    with SessionLocal() as db:
        try:
            with pytest.raises(IntegrityError):
                db.execute(
                    text(
                        """
                        INSERT INTO app_user (public_id, username, display_name, is_active)
                        VALUES (:public_id, 'SALES1', 'Case Duplicate Probe', TRUE)
                        """
                    ),
                    {"public_id": inserted_public_id},
                )
                db.flush()
        finally:
            db.rollback()

        # The probe must not have created a row, and the original must be untouched.
        remaining = db.execute(
            text("SELECT username FROM app_user WHERE lower(username) = 'sales1'")
        ).scalars().all()
        assert remaining == ["sales1"]


# --------------------------------------------------------------------------------------
# Static guard: keep T-SQL from being reintroduced into the active layer.
# --------------------------------------------------------------------------------------


def test_no_sql_server_only_constructs_remain_in_active_application_sql() -> None:
    """ADR-028 makes PostgreSQL the only supported runtime, so there is no dual-dialect
    layer to fall back on. A reintroduced T-SQL construct would fail only on the specific
    code path that runs it, which is easy to miss; this fails immediately instead.
    """
    forbidden = {
        "SELECT TOP": re.compile(r"SELECT\s+TOP\b", re.IGNORECASE),
        "FETCH NEXT": re.compile(r"FETCH\s+NEXT\b", re.IGNORECASE),
        "OFFSET ... ROWS": re.compile(r"OFFSET\s+\S+\s+ROWS\b", re.IGNORECASE),
        "SYSUTCDATETIME": re.compile(r"SYSUTCDATETIME\s*\(", re.IGNORECASE),
        "GETDATE/GETUTCDATE": re.compile(r"GET(UTC)?DATE\s*\(", re.IGNORECASE),
        "ISNULL(": re.compile(r"\bISNULL\s*\(", re.IGNORECASE),
        "JSON_VALUE(": re.compile(r"\bJSON_VALUE\s*\(", re.IGNORECASE),
        "SCOPE_IDENTITY": re.compile(r"SCOPE_IDENTITY\s*\(", re.IGNORECASE),
        "NEWID()": re.compile(r"\bNEWID\s*\(", re.IGNORECASE),
        "dbo. qualification": re.compile(r"\bdbo\.", re.IGNORECASE),
        "T-SQL DELETE alias FROM": re.compile(r"^\s*DELETE\s+[A-Za-z_][A-Za-z0-9_]*\s*$", re.MULTILINE),
    }

    offenders: list[str] = []
    for directory in ("app", "tooling"):
        for path in sorted((BACKEND_ROOT / directory).rglob("*.py")):
            if "__pycache__" in path.parts:
                continue
            source = path.read_text(encoding="utf-8")
            for label, pattern in forbidden.items():
                if pattern.search(source):
                    offenders.append(f"{path.relative_to(BACKEND_ROOT)}: {label}")

    assert offenders == [], "SQL Server-only constructs found in active PostgreSQL code: " + "; ".join(offenders)


def test_no_integer_literals_are_compared_against_boolean_columns() -> None:
    """`is_active = 1` / `SET active = 0` raise DatatypeMismatch on PostgreSQL. They are
    easy to reintroduce by copying an older query, so they are guarded statically.
    """
    boolean_columns = (
        "is_active", "is_primary", "is_deleted", "active", "is_selected_basis",
        "is_strategic_account", "applies_to_header", "applies_to_line", "mandatory_default",
    )
    pattern = re.compile(
        r"\b(?:[A-Za-z_][A-Za-z0-9_]*\.)?(" + "|".join(boolean_columns) + r")\s*=\s*[01]\b"
    )

    offenders: list[str] = []
    for directory in ("app", "tooling"):
        for path in sorted((BACKEND_ROOT / directory).rglob("*.py")):
            if "__pycache__" in path.parts:
                continue
            for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
                if pattern.search(line):
                    offenders.append(f"{path.relative_to(BACKEND_ROOT)}:{lineno}: {line.strip()}")

    assert offenders == [], "integer compared/assigned to a boolean column: " + "; ".join(offenders)
