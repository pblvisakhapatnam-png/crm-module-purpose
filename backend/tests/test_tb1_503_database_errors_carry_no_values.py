"""TB-1 TB1-503: a database error puts no customer value into the server log.

Two layers. The engine hides a failed statement's bound values (`hide_parameters`), which removes
SQLAlchemy's "[parameters: ...]" line. PostgreSQL's DETAIL line still travels in the same message - a
duplicated key, or a NOT NULL or CHECK violation's whole failing row - so a database error that escapes
a request is logged by app/core/errors.py without the error's text at all.

Each absence is checked against a control that shows the same value present where nothing hides it, so
a probe that could not see the value cannot pass.
"""

from __future__ import annotations

import logging
import re
import traceback
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError

from app.core import errors
from app.core.database import CONNECT_ARGS, build_sqlalchemy_url, engine
from app.modules.accounts import service as account_service
from tests.test_accounts_api import auth_headers, cleanup_test_records, client, create_test_account, unique_gstin

KEY = f"tb1-503-key-{uuid4().hex}"  # in the column a unique violation names
NOTE = f"tb1-503-note-{uuid4().hex}"  # in a column no failing constraint is about

_PROBE_TABLE = """
    CREATE TEMP TABLE tb1_503_probe (
        id serial PRIMARY KEY,
        key_value text UNIQUE,
        required_value text NOT NULL,
        checked_value text CHECK (checked_value <> 'refused'),
        note text
    )
"""
_FAILING_INSERT = {
    "unique": "INSERT INTO tb1_503_probe (key_value, required_value, note) VALUES (:key, 'x', :note)",
    "not_null": "INSERT INTO tb1_503_probe (key_value, required_value, note) VALUES (:key || '-2', NULL, :note)",
    "check": (
        "INSERT INTO tb1_503_probe (key_value, required_value, checked_value, note) "
        "VALUES (:key || '-3', 'x', 'refused', :note)"
    ),
}


def _refusal(on: Engine, kind: str) -> IntegrityError:
    """The error a failing insert raises, on a temporary table the rollback removes."""
    with on.connect() as connection:
        connection.execute(text(_PROBE_TABLE))
        connection.execute(text("INSERT INTO tb1_503_probe (key_value, required_value) VALUES (:key, 'x')"), {"key": KEY})
        with pytest.raises(IntegrityError) as raised:
            connection.execute(text(_FAILING_INSERT[kind]), {"key": KEY, "note": NOTE})
        connection.rollback()
    return raised.value


@pytest.fixture
def unhidden_engine():
    """An engine without hide_parameters: the control for every absence below."""
    unhidden = create_engine(build_sqlalchemy_url(), connect_args=CONNECT_ARGS)
    yield unhidden
    unhidden.dispose()


def test_the_engine_keeps_a_failed_statements_values_out_of_the_errors_text(unhidden_engine) -> None:
    assert NOTE in str(_refusal(unhidden_engine, "unique"))

    refused = str(_refusal(engine, "unique"))
    assert NOTE not in refused
    assert "[parameters:" not in refused
    assert "hide_parameters=True" in refused


def test_the_migrations_engine_hides_them_too() -> None:
    env = (Path(__file__).resolve().parents[1] / "alembic" / "env.py").read_text(encoding="utf-8-sig")
    assert "hide_parameters=True" in env


@pytest.mark.parametrize(("kind", "carried"), [("unique", KEY), ("not_null", NOTE), ("check", NOTE)])
def test_postgresqls_detail_line_still_carries_values_the_setting_cannot_hide(kind: str, carried: str) -> None:
    """Why app/core/errors.py logs no error text: the duplicated key, or the whole failing row."""
    assert carried in str(_refusal(engine, kind))


def test_the_logged_line_names_what_failed_and_carries_no_value() -> None:
    refusal = _refusal(engine, "not_null")
    assert NOTE in str(refusal)  # the error's own text carries the whole failing row

    line = errors.database_error_log_line(refusal, method="POST", route="/api/things/{public_id}", reference="ref-1")

    assert NOTE not in line
    assert KEY not in line
    for expected in (
        "reference=ref-1",
        "method=POST",
        "route=/api/things/{public_id}",
        "error=IntegrityError",
        "driver_error=NotNullViolation",
        "sqlstate=23502",
        "table=tb1_503_probe",
        "column=required_value",
    ):
        assert expected in line


def test_a_database_error_in_a_request_answers_500_and_logs_no_value(monkeypatch, caplog) -> None:
    gstin = unique_gstin()
    planted = {
        "legal_name": f"Planted Legal Name {uuid4().hex}",
        "trade_name": f"Planted Trade Name {uuid4().hex}",
        "remarks": f"Planted remark {uuid4().hex}",
    }
    account_public_ids: list[str] = []
    gstin_public_ids: list[str] = []

    def add_gstin(account_public_id: str, **extra: str):
        return client.post(
            f"/api/accounts/{account_public_id}/gstins",
            headers=auth_headers("sales1"),
            json={
                "gstin": gstin,
                "gstin_verification_state_code": "ENTERED_NOT_VERIFIED",
                "state_name": "Karnataka",
                "is_primary": False,
                **extra,
            },
        )

    try:
        account_public_id = str(create_test_account("sales1")["public_id"])
        account_public_ids.append(account_public_id)
        stored = add_gstin(account_public_id)
        assert stored.status_code == 201
        gstin_public_ids.append(stored.json()["gstin"]["public_id"])

        # The duplicate check misses, as when another request stores the same GSTIN between this one's
        # check and its insert (TB-1 TB1-304), so the insert meets the unique index.
        monkeypatch.setattr(account_service, "gstin_exists", lambda db, value: False)
        received: list[str] = []
        real_log_line = errors.database_error_log_line

        def spy(exc, **names):
            received.append("".join(traceback.format_exception(exc)))
            return real_log_line(exc, **names)

        monkeypatch.setattr(errors, "database_error_log_line", spy)

        with caplog.at_level(logging.DEBUG):
            refused = add_gstin(account_public_id, **planted)

        assert refused.status_code == 500
        assert refused.text == "Internal Server Error"
        # The control: the traceback the server used to log carried the GSTIN, in the DETAIL line.
        assert len(received) == 1
        assert gstin in received[0]

        logged = [record for record in caplog.records if record.name == "app.errors"]
        assert len(logged) == 1
        line = logged[0].getMessage()
        for expected in (
            "method=POST",
            "route=/api/accounts/{public_id}/gstins",
            "driver_error=UniqueViolation",
            "sqlstate=23505",
            "table=business_party_gstin",
            "constraint=ux_business_party_gstin",
            "modules/accounts/repository.py:",
            "insert_business_party_gstin",
        ):
            assert expected in line
        assert re.search(r"reference=[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", line)
        assert logged[0].exc_info is None

        everything_logged = "\n".join(record.getMessage() + (record.exc_text or "") for record in caplog.records)
        for value in (gstin, gstin[2:12], *planted.values()):
            assert value not in everything_logged
    finally:
        cleanup_test_records(account_public_ids=account_public_ids, gstin_public_ids=gstin_public_ids)
