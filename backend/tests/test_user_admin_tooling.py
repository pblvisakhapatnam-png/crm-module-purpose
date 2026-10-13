"""TE-5 server account tool (backend/tooling/user_admin).

Every account these tests create carries a per-run prefix and is removed after each test. The six
real demo users are never changed: the retire and seed commands, and the harness's demo authors
(TB-1 TB1-203), are exercised against synthetic stand-ins.
"""

from __future__ import annotations

import errno
import io
import json
import os
import re
import stat
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session, sessionmaker

import tooling.user_admin.credentials as credentials_module
import tooling.user_admin.database as user_admin_database
from app import startup
from app.core.config import STANDARD_PASSWORD_HASH_ITERATIONS, Settings
from app.core.database import CONNECT_ARGS, SessionLocal, build_sqlalchemy_url
from app.core.security import hash_password
from app.main import app
from tooling.smoke_data.actors import resolve_actor
from tooling.user_admin import cli, service
from tooling.user_admin.credentials import (
    CREDENTIALS_FILE_HEADER,
    CREDENTIALS_FILE_SIGNATURE,
    READABLE_CHARACTERS,
    CredentialsFileError,
    append_credentials,
    PASSWORD_SYMBOLS,
    PASSWORD_WORDS,
    generate_high_entropy_password,
    generate_password,
)

client = TestClient(app)

# Captured before any test can stand in for it: the cleanup below must work even in a test that
# leaves Session.commit failing.
_REAL_COMMIT = Session.commit

PREFIX = f"te5t-{uuid4().hex[:8]}-"
BACKEND_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def _remove_accounts_created_by_the_test():
    yield
    with SessionLocal() as db:
        db.execute(
            text("DELETE FROM user_role WHERE user_id IN (SELECT id FROM app_user WHERE username LIKE :prefix)"),
            {"prefix": PREFIX + "%"},
        )
        db.execute(text("DELETE FROM app_user WHERE username LIKE :prefix"), {"prefix": PREFIX + "%"})
        _REAL_COMMIT(db)


@contextmanager
def _sessions_without_hidden_parameters():
    """Sessions on an engine without hide_parameters, the control for a hash in a database error's text.

    The tool's engine and, since TB-1 TB1-503, the application's both set it, so neither can show that a failed
    statement's text would otherwise carry the hash.
    """
    unhidden_engine = create_engine(build_sqlalchemy_url(), connect_args=CONNECT_ARGS)
    try:
        yield sessionmaker(bind=unhidden_engine, class_=Session)
    finally:
        unhidden_engine.dispose()


@pytest.fixture(autouse=True)
def _credentials_folder(tmp_path, monkeypatch):
    # The tool accepts a file only directly in its credentials folder, which must be a mounted
    # folder. Here that folder is the test's own temporary folder, standing in for the mount.
    monkeypatch.setattr(credentials_module, "CREDENTIALS_DIR", tmp_path)
    monkeypatch.setattr(credentials_module, "_is_mount", lambda folder: True)


def _unconfirmed_marks(credentials: Path) -> list[str]:
    """The marks in the file, not the header's mention of them: only a line that starts with one."""
    mark = credentials_module.UNCONFIRMED_MARK
    return [line for line in credentials.read_text().splitlines() if line.startswith(mark)]


def _username(label: str) -> str:
    return f"{PREFIX}{label}"


def _create(credentials: Path, label: str, *roles: str) -> str:
    username = _username(label)
    role_args = [part for role in (roles or ("SALES_USER",)) for part in ("--role", role)]
    assert cli.main(
        ["create", "--username", username, "--display-name", f"Pilot {label}", *role_args,
         "--credentials-file", str(credentials)]
    ) == 0
    return username


def _credential_lines(credentials: Path) -> list[list[str]]:
    return [line.split("\t") for line in credentials.read_text().splitlines() if line and not line.startswith("#")]


def _password_for(credentials: Path, username: str) -> str:
    return [fields[3] for fields in _credential_lines(credentials) if fields[2] == username][-1]


def _insert_with_password(username: str, password: str) -> None:
    with SessionLocal() as db:
        service.create_user(
            db, username=username, display_name="Demo stand-in", role_codes=["SALES_USER"],
            password_hash=hash_password(password),
        )
        db.commit()


def _login(username: str, password: str):
    return client.post("/api/auth/login", json={"username": username, "password": password})


def _me(token: str):
    return client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})


def test_create_writes_the_password_only_to_the_credentials_file(tmp_path, capsys):
    credentials = tmp_path / "pilot-users.txt"

    username = _create(credentials, "sales-01")

    printed = capsys.readouterr()
    password = _password_for(credentials, username)
    assert password not in printed.out + printed.err
    assert "It is not shown here." in printed.out
    assert stat.S_IMODE(credentials.stat().st_mode) == 0o600
    assert credentials.read_text().startswith(CREDENTIALS_FILE_HEADER)

    response = _login(username, password)
    assert response.status_code == 200
    assert response.json()["user"]["role_codes"] == ["SALES_USER"]


def test_generated_passwords_are_random_and_easy_to_read_out():
    """The pilot form: two different words, a symbol, three digits - `Zinnia#Delta122`.

    Shorter and far easier to dictate than the four-group form, and deliberately much weaker; see
    PASSWORD_WORDS for the decision and for when it must be reverted.
    """
    generated = [generate_password() for _ in range(200)]

    assert len(set(generated)) > 190, "passwords should rarely repeat"
    for password in generated:
        assert len(password) <= 16, password
        symbols = [c for c in password if c in PASSWORD_SYMBOLS]
        assert len(symbols) == 1, password
        head, tail = password.split(symbols[0])
        assert head in PASSWORD_WORDS, password
        assert tail[:-3] in PASSWORD_WORDS, password
        assert head != tail[:-3], "a doubled word reads as a mistake"
        assert tail[-3:].isdigit(), password


def test_a_chosen_password_can_be_given_on_standard_input(monkeypatch, tmp_path):
    """`--password-stdin` sets the operator's own password instead of a generated one.

    For the UAT pilot the project owner chose the tester passwords themselves. The value is read
    from stdin, never from argv, so it is not visible to `ps` and does not land in shell history.
    """
    credentials = tmp_path / "pilot-users.txt"
    username = _username("chosen")
    monkeypatch.setattr("sys.stdin", io.StringIO("Ex@mpl3pass123_1" + chr(10)))

    assert cli.main(
        ["create", "--username", username, "--display-name", "Chosen", "--role", "SALES_USER",
         "--credentials-file", str(credentials), "--password-stdin"]
    ) == 0

    assert _password_for(credentials, username) == "Ex@mpl3pass123_1"
    assert _login(username, "Ex@mpl3pass123_1").status_code == 200


def test_a_chosen_password_replaces_the_previous_one(monkeypatch, tmp_path):
    credentials = tmp_path / "pilot-users.txt"
    username = _create(credentials, "reset-chosen")
    generated = _password_for(credentials, username)
    # At least 12 characters since TB-1 TB1-204 part a's password rules; the symbols are the point of the case.
    monkeypatch.setattr("sys.stdin", io.StringIO("Sampl3!@#$-chosen" + chr(10)))

    assert cli.main(
        ["reset-password", "--username", username, "--credentials-file", str(credentials),
         "--password-stdin"]
    ) == 0

    assert _login(username, "Sampl3!@#$-chosen").status_code == 200
    assert _login(username, generated).status_code == 401


@pytest.mark.parametrize(
    "given, why",
    [
        ("", "nothing on standard input"),
        (chr(10), "only a newline"),
        ("first" + chr(10) + "second" + chr(10), "a line break inside the password"),
        ("x" * 201 + chr(10), "longer than the application accepts"),
    ],
)
def test_an_unusable_chosen_password_is_refused_before_the_database(monkeypatch, tmp_path, given, why):
    """Refused at exit 2, the tool's "nothing was saved" status, with no account created.

    The 200-character limit is the application's own (`identity/schemas.py`); without this check a
    longer password would be written to the credentials file and then refused at sign-in, which is
    the worst of both.
    """
    credentials = tmp_path / "pilot-users.txt"
    username = _username("refused")
    monkeypatch.setattr("sys.stdin", io.StringIO(given))

    assert cli.main(
        ["create", "--username", username, "--display-name", "Refused", "--role", "SALES_USER",
         "--credentials-file", str(credentials), "--password-stdin"]
    ) == 2, why
    assert not credentials.exists()


def test_the_high_entropy_form_is_still_available_to_return_to():
    """The pilot's weaker passwords are a decision, not a loss of the stronger generator."""
    groups = generate_high_entropy_password().split("-")

    assert len(groups) == 4 and all(len(group) == 4 for group in groups)
    assert set("".join(groups)) <= set(READABLE_CHARACTERS)
    assert not set("0O1lI") & set(READABLE_CHARACTERS)


def test_create_refuses_a_duplicate_a_bad_username_and_an_unknown_role(tmp_path, capsys):
    credentials = tmp_path / "pilot-users.txt"
    username = _create(credentials, "sales-01")

    duplicate = ["create", "--username", username.upper().lower(), "--display-name", "Again",
                 "--role", "SALES_USER", "--credentials-file", str(credentials)]
    assert cli.main(duplicate) == 2
    assert cli.main(["create", "--username", f"{PREFIX}Has Capitals", "--display-name", "X",
                     "--role", "SALES_USER", "--credentials-file", str(credentials)]) == 2
    assert cli.main(["create", "--username", _username("norole"), "--display-name", "X",
                     "--role", "NOT_A_ROLE", "--credentials-file", str(credentials)]) == 2

    assert "already exists" in capsys.readouterr().err
    # Refused requests write no password and create no account.
    assert [fields[2] for fields in _credential_lines(credentials)] == [username]
    with SessionLocal() as db:
        assert service.get_user(db, _username("norole")) is None


def test_usernames_are_unique_regardless_of_case(tmp_path):
    credentials = tmp_path / "pilot-users.txt"
    username = _create(credentials, "sales-01")

    with SessionLocal() as db:
        with pytest.raises(service.UserAdminError, match="already exists"):
            service.create_user(
                db, username=username, display_name="X", role_codes=["SALES_USER"], password_hash="x"
            )
        # The pattern itself refuses upper case, so a mixed-case twin cannot even be asked for.
        assert not service.USERNAME_PATTERN.fullmatch(username.upper())


def test_reset_password_replaces_the_old_one(tmp_path, capsys):
    credentials = tmp_path / "pilot-users.txt"
    username = _create(credentials, "sales-01")
    old_password = _password_for(credentials, username)

    assert cli.main(["reset-password", "--username", username, "--credentials-file", str(credentials)]) == 0

    new_password = _password_for(credentials, username)
    assert new_password != old_password
    assert new_password not in capsys.readouterr().out
    assert _login(username, old_password).status_code == 401
    assert _login(username, new_password).status_code == 200
    assert stat.S_IMODE(credentials.stat().st_mode) == 0o600


def test_disable_takes_effect_at_once_even_for_someone_already_signed_in(tmp_path):
    credentials = tmp_path / "pilot-users.txt"
    username = _create(credentials, "sales-01")
    password = _password_for(credentials, username)
    token = _login(username, password).json()["access_token"]
    assert _me(token).status_code == 200

    assert cli.main(["disable", "--username", username]) == 0

    assert _me(token).status_code == 401
    assert _login(username, password).status_code == 401

    assert cli.main(["enable", "--username", username]) == 0
    # Since TB-1 TB1-204 part a disabling also ends the sign-ins, so enabling again does not bring back one made
    # before; the account signs in afresh.
    assert _me(token).status_code == 401
    assert _login(username, password).status_code == 200


def test_set_roles_replaces_the_role_set(tmp_path):
    credentials = tmp_path / "pilot-users.txt"
    username = _create(credentials, "manager-01", "SALES_USER")
    token = _login(username, _password_for(credentials, username)).json()["access_token"]

    assert cli.main(["set-roles", "--username", username, "--role", "SALES_MANAGER", "--role", "FINANCE_USER"]) == 0
    assert sorted(_me(token).json()["role_codes"]) == ["FINANCE_USER", "SALES_MANAGER"]

    # A refused change leaves the roles as they were.
    assert cli.main(["set-roles", "--username", username, "--role", "NOT_A_ROLE"]) == 2
    assert sorted(_me(token).json()["role_codes"]) == ["FINANCE_USER", "SALES_MANAGER"]


def test_retiring_removes_the_password_so_re_enabling_does_not_bring_it_back(monkeypatch, capsys):
    stand_ins = (_username("demo-a"), _username("demo-b"))
    for username in stand_ins:
        _insert_with_password(username, service.DEMO_PASSWORD)
    monkeypatch.setattr(service, "DEMO_USERNAMES", (*stand_ins, _username("never-created")))

    assert cli.main(["retire-demo-users"]) == 0
    assert "2 demo user(s) retired" in capsys.readouterr().out

    with SessionLocal() as db:
        for username in stand_ins:
            user = service.get_user(db, username)
            assert user is not None and not user.is_active and not user.has_password

    assert cli.main(["enable", "--username", stand_ins[0]]) == 0
    assert "no password" in capsys.readouterr().out
    assert _login(stand_ins[0], service.DEMO_PASSWORD).status_code == 401

    # Running it again changes nothing that is already retired.
    assert cli.main(["disable", "--username", stand_ins[0]]) == 0
    assert cli.main(["retire-demo-users"]) == 0
    assert "0 demo user(s) retired" in capsys.readouterr().out


def test_the_demo_users_are_the_six_the_seed_migration_created():
    """`retire-demo-users` and `check-default-passwords` must still reach every demo user a database
    built before TB-1 TB1-203 (7 October 2026) may hold: the names, public ids, display names and
    roles Alembic revision 20260629_0002 gave them until then."""
    assert [(user.public_id, user.username, user.display_name, user.role_code) for user in service.DEMO_USERS] == [
        ("00000000-0000-0000-0000-000000000201", "admin1", "Admin User 1", "ADMIN"),
        ("00000000-0000-0000-0000-000000000202", "sales1", "Sales User 1", "SALES_USER"),
        ("00000000-0000-0000-0000-000000000203", "manager1", "Sales Manager 1", "SALES_MANAGER"),
        ("00000000-0000-0000-0000-000000000204", "finance1", "Finance User 1", "FINANCE_USER"),
        ("00000000-0000-0000-0000-000000000205", "ops1", "Operations User 1", "OPERATIONS_USER"),
        ("00000000-0000-0000-0000-000000000206", "readonly1", "Management Read Only User 1", "MANAGEMENT_READ_ONLY"),
    ]
    assert service.DEMO_USERNAMES == tuple(user.username for user in service.DEMO_USERS)


# ---------------------------------------------------------------------------
# TB-1 TB1-203: the demo users come from development and CI seeding, not the migrations
# ---------------------------------------------------------------------------


def test_no_migration_creates_a_user():
    """Every revision is read: none inserts into app_user or hashes a password, so no database the
    migrations build - production, a vendor's, a preview - gets a user that signs in with a password
    published in this repository. CI's empty-database job checks the same at run time (no user after
    upgrading from empty)."""
    offenders = [
        path.name
        for path in sorted((BACKEND_ROOT / "alembic" / "versions").glob("*.py"))
        if re.search(r"insert\s+into\s+app_user\b|pbkdf2_hmac", path.read_text(encoding="utf-8-sig"), re.IGNORECASE)
    ]
    assert offenders == []


def _stand_in_demo_users(monkeypatch, *labels: str) -> tuple[service.DemoUser, ...]:
    """Stand-ins for the six, so the real demo users are never changed (see the module docstring)."""
    stand_ins = tuple(
        service.DemoUser(str(uuid4()), _username(label), f"Demo stand-in {label}", "SALES_USER") for label in labels
    )
    monkeypatch.setattr(service, "DEMO_USERS", stand_ins)
    monkeypatch.setattr(service, "DEMO_USERNAMES", tuple(user.username for user in stand_ins))
    return stand_ins


def _account_event_count(public_id: str) -> int:
    with SessionLocal() as db:
        return db.execute(
            text("SELECT count(*) FROM business_event WHERE record_type = 'app_user' AND record_public_id = :public_id"),
            {"public_id": public_id},
        ).scalar_one()


def test_seed_demo_users_creates_them_able_to_sign_in_and_a_second_run_changes_nothing(monkeypatch, capsys):
    stand_ins = _stand_in_demo_users(monkeypatch, "seed-a", "seed-b")

    assert cli.main(["seed-demo-users"]) == 0
    assert "2 demo user(s) created or restored" in capsys.readouterr().out
    for demo in stand_ins:
        with SessionLocal() as db:
            user = service.get_user(db, demo.username)
        assert (user.public_id, user.display_name, user.role_codes, user.is_active) == (
            demo.public_id, demo.display_name, ("SALES_USER",), True,
        )
        assert _login(demo.username, service.DEMO_PASSWORD).status_code == 200

    events_before = [_account_event_count(demo.public_id) for demo in stand_ins]
    assert cli.main(["seed-demo-users"]) == 0
    assert "already in place" in capsys.readouterr().out
    assert [_account_event_count(demo.public_id) for demo in stand_ins] == events_before


def test_seed_demo_users_restores_a_retired_one_and_adds_its_role(monkeypatch, capsys):
    (demo,) = _stand_in_demo_users(monkeypatch, "seed-c")
    with SessionLocal() as db:
        service.create_user(
            db, username=demo.username, display_name="Changed by hand", role_codes=["OPERATIONS_USER"],
            password_hash=hash_password("a-password-of-its-own"),
        )
        service.retire_users(db, [demo.username])
        db.commit()

    assert cli.main(["seed-demo-users"]) == 0
    assert f"1 demo user(s) created or restored: {demo.username}" in capsys.readouterr().out
    with SessionLocal() as db:
        user = service.get_user(db, demo.username)
    # Active again, its own role added and the other kept; the display name is left as it was.
    assert (user.is_active, user.role_codes, user.display_name) == (True, ("OPERATIONS_USER", "SALES_USER"), "Changed by hand")
    assert _login(demo.username, service.DEMO_PASSWORD).status_code == 200


@pytest.mark.parametrize("app_env", ["uat", "production", "staging"])
def test_seed_demo_users_is_refused_outside_development(monkeypatch, capsys, app_env):
    (demo,) = _stand_in_demo_users(monkeypatch, "seed-d")
    settings = Settings(  # type: ignore[call-arg]
        _env_file=None,
        app_env=app_env,
        database_url="postgresql+psycopg://u@db:5432/x",
        jwt_secret="-".join(("not", "the", "shipped", "placeholder")),
        password_hash_iterations=STANDARD_PASSWORD_HASH_ITERATIONS,  # CI sets fewer for its whole job
    )
    monkeypatch.setattr(cli, "get_settings", lambda: settings)

    assert cli.main(["seed-demo-users"]) == 2
    assert "not a development environment" in capsys.readouterr().err
    with SessionLocal() as db:
        assert service.get_user(db, demo.username) is None


def test_a_demo_author_cannot_sign_in_and_needs_no_retiring(monkeypatch, capsys):
    (demo,) = _stand_in_demo_users(monkeypatch, "author-a")
    with SessionLocal() as db:
        author = service.add_demo_author(db, demo.username)
        db.commit()

    assert (author.public_id, author.is_active, author.has_password, author.role_codes) == (
        demo.public_id, False, False, ("SALES_USER",),
    )
    assert _login(demo.username, service.DEMO_PASSWORD).status_code == 401
    assert cli.main(["retire-demo-users"]) == 0
    assert "0 demo user(s) retired" in capsys.readouterr().out
    assert cli.main(["check-default-passwords"]) in (0, 1)  # the real six may be active on this database
    assert demo.username not in capsys.readouterr().err


def test_only_a_demo_user_can_be_added_as_an_author():
    with SessionLocal() as db:
        with pytest.raises(service.UserAdminError, match="not a demo user"):
            service.add_demo_author(db, _username("someone-else"))


def test_the_harness_writes_as_a_missing_demo_user_by_creating_it_switched_off(monkeypatch):
    """A hosted site's practice data is written as the demo users, which its database no longer gets
    from the migrations: the harness creates the author it needs, unable to sign in, and commits it."""
    (demo,) = _stand_in_demo_users(monkeypatch, "author-b")

    with SessionLocal() as db:
        actor = resolve_actor(db, demo.username)
    assert actor == {"public_id": demo.public_id, "username": demo.username}

    with SessionLocal() as db:
        user = service.get_user(db, demo.username)
        assert user is not None and not user.is_active and not user.has_password
        assert resolve_actor(db, demo.username) == actor  # found, not created again
        with pytest.raises(RuntimeError, match="was not found"):
            resolve_actor(db, _username("not-a-demo-user"))


@pytest.mark.parametrize(("app_env", "seeds"), [("development", True), ("ci", True), ("uat", False), ("production", False)])
def test_the_backend_seeds_the_demo_users_when_it_starts_in_development_only(monkeypatch, app_env, seeds):
    calls: list[tuple[list[str], bool]] = []
    monkeypatch.setattr(startup, "subprocess", SimpleNamespace(run=lambda command, check: calls.append((command, check))))
    settings = Settings(  # type: ignore[call-arg]
        _env_file=None,
        app_env=app_env,
        database_url="postgresql+psycopg://u@db:5432/x",
        jwt_secret="-".join(("not", "the", "shipped", "placeholder")),
        password_hash_iterations=STANDARD_PASSWORD_HASH_ITERATIONS,  # CI sets fewer for its whole job
    )

    startup.seed_development_sign_ins(settings)

    assert calls == ([(list(startup.SEED_DEMO_USERS_COMMAND), True)] if seeds else [])
    assert list(startup.SEED_DEMO_USERS_COMMAND)[1:] == ["-m", "tooling.user_admin", "seed-demo-users"]
    assert cli.build_parser().parse_args(["seed-demo-users"]).handler is cli._cmd_seed_demo_users


def test_check_default_passwords_names_active_accounts_that_still_accept_it(tmp_path, capsys):
    exposed = _username("exposed")
    _insert_with_password(exposed, service.DEMO_PASSWORD)
    safe = _create(tmp_path / "pilot-users.txt", "safe")
    capsys.readouterr()

    assert cli.main(["check-default-passwords"]) == 1
    reported = capsys.readouterr().err
    assert exposed in reported
    assert safe not in reported

    assert cli.main(["disable", "--username", exposed]) == 0
    with SessionLocal() as db:
        assert exposed not in service.users_accepting_password(db, service.DEMO_PASSWORD)


def test_account_changes_are_recorded_without_the_password(tmp_path):
    credentials = tmp_path / "pilot-users.txt"
    username = _create(credentials, "sales-01")
    assert cli.main(["reset-password", "--username", username, "--credentials-file", str(credentials)]) == 0
    assert cli.main(["disable", "--username", username]) == 0
    passwords = [fields[3] for fields in _credential_lines(credentials)]

    with SessionLocal() as db:
        user = service.get_user(db, username)
        rows = db.execute(
            text(
                "SELECT event_name, source_module, user_public_id, status_after, event_payload_json "
                "FROM business_event WHERE record_type = 'app_user' AND record_public_id = :public_id ORDER BY id"
            ),
            {"public_id": user.public_id},
        ).all()

    assert [row.event_name for row in rows] == ["UserAccountCreated", "UserPasswordReset", "UserAccountDisabled"]
    assert {row.source_module for row in rows} == {"identity"}
    assert rows[-1].status_after == "INACTIVE"
    for row in rows:
        payload = row.event_payload_json or ""
        assert json.loads(payload)["username"] == username
        assert "pbkdf2" not in payload
        assert not any(password in payload for password in passwords)


def test_a_name_with_secretary_in_it_is_accepted(tmp_path):
    # Until TB-1 TB1-500 the event log refused "Secretary"; now only a credential's shape is refused.
    credentials = tmp_path / "pilot-users.txt"
    username = _username("secretary")

    assert cli.main(["create", "--username", username, "--display-name", "Sales Secretary",
                     "--role", "SALES_USER", "--credentials-file", str(credentials)]) == 0

    with SessionLocal() as db:
        assert service.get_user(db, username).display_name == "Sales Secretary"


def test_a_name_the_event_log_refuses_is_refused_cleanly_and_changes_nothing(tmp_path, capsys):
    credentials = tmp_path / "pilot-users.txt"
    username = _username("tokenname")
    # A JSON Web Token - header {"alg":"HS256"}, payload {} - which the event log refuses (TB1-500); assembled so the
    # secret scanner passes it.
    display_name = "Probe " + "eyJhbGciOiJ" + "IUzI1NiJ9" + "." + "e30" + "." + "c" * 20

    assert cli.main(["create", "--username", username, "--display-name", display_name,
                     "--role", "SALES_USER", "--credentials-file", str(credentials)]) == 2

    assert "event log refuses" in capsys.readouterr().err
    assert not credentials.exists()
    with SessionLocal() as db:
        assert service.get_user(db, username) is None


def test_retiring_records_an_event_the_event_log_accepts(monkeypatch):
    stand_in = _username("demo-c")
    _insert_with_password(stand_in, service.DEMO_PASSWORD)
    monkeypatch.setattr(service, "DEMO_USERNAMES", (stand_in,))

    assert cli.main(["retire-demo-users"]) == 0

    with SessionLocal() as db:
        user = service.get_user(db, stand_in)
        event = db.execute(
            text(
                "SELECT status_before, status_after FROM business_event "
                "WHERE record_type = 'app_user' AND record_public_id = :public_id "
                "AND event_name = 'UserAccountRetired'"
            ),
            {"public_id": user.public_id},
        ).one()
    assert (event.status_before, event.status_after) == ("ACTIVE", "INACTIVE")


def test_a_credentials_file_that_cannot_be_written_leaves_no_account(tmp_path, capsys, monkeypatch):
    missing = tmp_path / "missing-directory"
    monkeypatch.setattr(credentials_module, "CREDENTIALS_DIR", missing)
    username = _username("unwritten")

    assert cli.main(["create", "--username", username, "--display-name", "X", "--role", "SALES_USER",
                     "--credentials-file", str(missing / "users.txt")]) == 2

    assert "does not exist" in capsys.readouterr().err
    with SessionLocal() as db:
        assert service.get_user(db, username) is None


@pytest.mark.parametrize("where", ["beside the folder", "below the folder", "escaping with .."])
def test_a_file_outside_the_credentials_folder_is_refused_before_any_change(tmp_path, capsys, monkeypatch, where):
    folder = tmp_path / "credentials"
    (folder / "sub").mkdir(parents=True)
    monkeypatch.setattr(credentials_module, "CREDENTIALS_DIR", folder)
    target = {
        "beside the folder": tmp_path / "pilot-users.txt",
        "below the folder": folder / "sub" / "pilot-users.txt",
        "escaping with ..": folder / ".." / "pilot-users.txt",
    }[where]
    applied = []
    real_create_user = service.create_user
    monkeypatch.setattr(
        service, "create_user", lambda db, **fields: applied.append(fields) or real_create_user(db, **fields)
    )
    username = _username("outside")

    assert cli.main(["create", "--username", username, "--display-name", "X", "--role", "SALES_USER",
                     "--credentials-file", str(target)]) == 2

    assert "must be directly in" in capsys.readouterr().err
    assert applied == []  # refused before the database was touched
    assert not target.exists()
    with SessionLocal() as db:
        assert service.get_user(db, username) is None


def test_a_path_that_escapes_the_folder_through_a_symbolic_link_is_refused(tmp_path, capsys, monkeypatch):
    # /credentials/jump/../pilot-users.txt reads as /credentials once normalised as text, but the
    # kernel follows jump first and lands outside it. Only a plain file name in the folder is taken.
    folder = tmp_path / "credentials"
    folder.mkdir()
    outside = tmp_path / "outside" / "child"
    outside.mkdir(parents=True)
    os.symlink(outside, folder / "jump", target_is_directory=True)
    monkeypatch.setattr(credentials_module, "CREDENTIALS_DIR", folder)
    username = _username("escape")

    assert cli.main(["create", "--username", username, "--display-name", "X", "--role", "SALES_USER",
                     "--credentials-file", str(folder / "jump" / ".." / "pilot-users.txt")]) == 2

    assert "must be directly in" in capsys.readouterr().err
    assert [path.name for path in (tmp_path / "outside").iterdir()] == ["child"]
    assert list(outside.iterdir()) == []
    with SessionLocal() as db:
        assert service.get_user(db, username) is None


def test_a_credentials_folder_that_is_not_mounted_is_refused(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(credentials_module, "_is_mount", lambda folder: False)
    username = _username("not-mounted")

    assert cli.main(["create", "--username", username, "--display-name", "X", "--role", "SALES_USER",
                     "--credentials-file", str(tmp_path / "pilot-users.txt")]) == 2

    assert "not a mounted folder" in capsys.readouterr().err
    assert not (tmp_path / "pilot-users.txt").exists()
    with SessionLocal() as db:
        assert service.get_user(db, username) is None


def test_the_credentials_file_refuses_a_symbolic_link(tmp_path):
    target = tmp_path / "elsewhere.txt"
    link = tmp_path / "users.txt"
    os.symlink(target, link)

    with pytest.raises(CredentialsFileError, match="symbolic link"):
        append_credentials(link, action="created", username="x", password="y")
    assert not target.exists()


def test_an_existing_credentials_file_is_tightened_and_kept(tmp_path):
    credentials = tmp_path / "users.txt"
    append_credentials(credentials, action="created", username="first", password="example-generated-value")
    credentials.chmod(0o644)

    append_credentials(credentials, action="created", username="second", password="example-generated-value")

    assert stat.S_IMODE(credentials.stat().st_mode) == 0o600
    content = credentials.read_text()
    assert content.startswith(CREDENTIALS_FILE_HEADER)
    assert content.count(CREDENTIALS_FILE_SIGNATURE) == 1
    assert [fields[2] for fields in _credential_lines(credentials)] == ["first", "second"]


def test_a_file_the_tool_did_not_create_is_refused_and_left_alone(tmp_path, capsys):
    other = tmp_path / "PERIMETER-ACCESS.txt"
    other.write_text("site login: not for this tool\n")
    username = _username("wrong-file")

    assert cli.main(["create", "--username", username, "--display-name", "X", "--role", "SALES_USER",
                     "--credentials-file", str(other)]) == 2

    assert "not created by this tool" in capsys.readouterr().err
    assert other.read_text() == "site login: not for this tool\n"
    with SessionLocal() as db:
        assert service.get_user(db, username) is None


def test_an_existing_empty_file_is_refused_too(tmp_path, capsys):
    other = tmp_path / "users.txt"
    other.touch()
    username = _username("empty-file")

    assert cli.main(["create", "--username", username, "--display-name", "X", "--role", "SALES_USER",
                     "--credentials-file", str(other)]) == 2

    assert "not created by this tool" in capsys.readouterr().err
    assert other.read_bytes() == b""
    with SessionLocal() as db:
        assert service.get_user(db, username) is None


def test_a_fifo_is_refused_without_waiting_for_a_reader(tmp_path):
    fifo = tmp_path / "users.txt"
    os.mkfifo(fifo)

    with pytest.raises(CredentialsFileError, match="not a regular file"):
        append_credentials(fifo, action="created", username="x", password="example-generated-value")


def test_a_hard_linked_file_is_refused(tmp_path):
    credentials = tmp_path / "users.txt"
    append_credentials(credentials, action="created", username="first", password="example-generated-value")
    os.link(credentials, tmp_path / "second-name.txt")
    before = credentials.read_text()

    with pytest.raises(CredentialsFileError, match="hard link"):
        append_credentials(credentials, action="created", username="second", password="example-generated-value")
    assert credentials.read_text() == before


def test_a_directory_reached_through_a_symbolic_link_is_refused(tmp_path, monkeypatch):
    real = tmp_path / "real"
    real.mkdir()
    link = tmp_path / "link"
    os.symlink(real, link, target_is_directory=True)
    monkeypatch.setattr(credentials_module, "CREDENTIALS_DIR", link)

    with pytest.raises(CredentialsFileError, match="symbolic link"):
        append_credentials(link / "users.txt", action="created", username="x", password="example-generated-value")
    assert not (real / "users.txt").exists()


def test_a_database_refusal_prints_neither_the_password_nor_its_hash(tmp_path, capsys, monkeypatch):
    credentials = tmp_path / "pilot-users.txt"
    username = _create(credentials, "sales-01")
    lines_before = _credential_lines(credentials)

    # Without the tool's handling, the database's own error text carries the hash: the danger is real.
    with _sessions_without_hidden_parameters() as unhidden, unhidden() as db:
        with pytest.raises(IntegrityError) as raised:
            db.execute(
                text(
                    "INSERT INTO app_user (public_id, username, display_name, password_hash, is_active) "
                    "VALUES (:public_id, :username, 'X', :hash_value, TRUE)"
                ),
                {"public_id": str(uuid4()), "username": username, "hash_value": "pbkdf2_sha256$1$00$visible"},
            )
        db.rollback()
    assert "pbkdf2_sha256$1$00$visible" in str(raised.value)

    # Make the duplicate check miss, so the INSERT itself hits the unique index, as in a race.
    monkeypatch.setattr(service, "get_user", lambda db, name: None)
    capsys.readouterr()

    assert cli.main(["create", "--username", username, "--display-name", "Again", "--role", "SALES_USER",
                     "--credentials-file", str(credentials)]) == 2

    printed = capsys.readouterr()
    assert "a user with that name may already exist" in printed.err
    assert "pbkdf2" not in printed.out + printed.err
    assert _credential_lines(credentials) == lines_before


def test_the_tools_own_database_errors_carry_no_parameters_at_all(tmp_path):
    """The hash is not hidden from the output; it is not in the exception to begin with.

    An engine without hide_parameters formats a failed statement's parameters into the error's text,
    which is the only reason a hash could reach a message or a traceback at all. The tool's engine sets
    hide_parameters, so the same failure carries none - which closes every route out, including the
    ones no guard covers. The application's engine has set it too since TB-1 TB1-503.
    """
    credentials = tmp_path / "pilot-users.txt"
    username = _create(credentials, "sales-01")
    statement = text(
        "INSERT INTO app_user (public_id, username, display_name, password_hash, is_active) "
        "VALUES (:public_id, :username, 'X', :hash_value, TRUE)"
    )
    parameters = {"public_id": str(uuid4()), "username": username, "hash_value": "pbkdf2_sha256$1$00$visible"}

    def failure(factory) -> str:
        with factory() as db:
            with pytest.raises(IntegrityError) as raised:
                db.execute(statement, parameters)
            db.rollback()
        return str(raised.value)

    with _sessions_without_hidden_parameters() as unhidden:
        # The control: without the setting the hash is in the text, so its absence below means something.
        assert "pbkdf2_sha256$1$00$visible" in failure(unhidden)
    assert "pbkdf2_sha256$1$00$visible" not in failure(user_admin_database.SessionLocal)  # the tool's
    assert "pbkdf2_sha256$1$00$visible" not in failure(SessionLocal)  # the application's


def test_an_interruption_during_a_refusals_rollback_does_not_re_expose_the_error(
    tmp_path, capsys, monkeypatch
):
    """Ctrl+C is a BaseException, so it escaped cleanup that caught only Exception.

    Raised inside the handler for a database error, it would come out carrying that error as its
    context, and Python prints the chain. The command must still return its own status instead.
    """
    credentials = tmp_path / "pilot-users.txt"
    username = _create(credentials, "sales-01")
    lines_before = _credential_lines(credentials)

    def interrupt_the_rollback(self):
        raise KeyboardInterrupt

    monkeypatch.setattr(service, "get_user", lambda db, name: None)  # so the INSERT itself collides
    monkeypatch.setattr(Session, "rollback", interrupt_the_rollback)
    capsys.readouterr()

    assert cli.main(["create", "--username", username, "--display-name", "Again", "--role", "SALES_USER",
                     "--credentials-file", str(credentials)]) == 2

    printed = capsys.readouterr()
    assert "a user with that name may already exist" in printed.err
    assert "pbkdf2" not in printed.out + printed.err
    assert "password_hash" not in printed.out + printed.err
    assert _credential_lines(credentials) == lines_before


def test_an_interruption_while_the_session_closes_does_not_re_expose_the_error(
    tmp_path, capsys, monkeypatch
):
    """The same, for the other cleanup step: closing the session on the way out."""
    credentials = tmp_path / "pilot-users.txt"
    username = _username("interrupted-close")
    real_close = Session.close
    closed = []

    def interrupt_the_first_close(self, *args, **kwargs):
        if not closed:
            closed.append(True)
            raise KeyboardInterrupt
        return real_close(self, *args, **kwargs)

    monkeypatch.setattr(Session, "close", interrupt_the_first_close)
    capsys.readouterr()

    assert cli.main(["create", "--username", username, "--display-name", "Closing", "--role", "SALES_USER",
                     "--credentials-file", str(credentials)]) == 0

    printed = capsys.readouterr()
    assert closed
    assert "pbkdf2" not in printed.out + printed.err
    monkeypatch.setattr(Session, "close", real_close)

    with SessionLocal() as db:
        assert service.get_user(db, username) is not None


def test_a_database_refusal_whose_rollback_also_fails_still_says_nothing_about_the_hash(
    tmp_path, capsys, monkeypatch
):
    """The refusal's own cleanup must not turn a handled error into a traceback.

    The rollback runs inside the handler for a database error whose text carries the statement's
    parameters, the password hash among them. A rollback that raised there would come out with that
    error still in its exception chain, and Python would print the chain.
    """
    credentials = tmp_path / "pilot-users.txt"
    username = _create(credentials, "sales-01")
    lines_before = _credential_lines(credentials)

    def failing_rollback(self):
        raise OperationalError("ROLLBACK", {}, RuntimeError("connection lost"))

    # Make the duplicate check miss, so the INSERT itself hits the unique index, as in a race: the
    # test above proves that error's own text carries the hash.
    monkeypatch.setattr(service, "get_user", lambda db, name: None)
    monkeypatch.setattr(Session, "rollback", failing_rollback)
    capsys.readouterr()

    assert cli.main(["create", "--username", username, "--display-name", "Again", "--role", "SALES_USER",
                     "--credentials-file", str(credentials)]) == 2

    printed = capsys.readouterr()
    assert "a user with that name may already exist" in printed.err  # the ordinary refusal, unchanged
    assert "pbkdf2" not in printed.out + printed.err
    assert "ROLLBACK" not in printed.out + printed.err  # the cleanup failure does not speak either
    assert _credential_lines(credentials) == lines_before


def test_a_session_that_cannot_be_closed_does_not_change_what_the_command_reports(
    tmp_path, capsys, monkeypatch
):
    """Closing happens on the way out of a block that may be handling a hash-bearing error.

    An exception from the close would come out with that error still in its chain, and Python
    prints the chain. It is swallowed, so the command keeps the status it had already decided on -
    here a successful create, which really was saved.
    """
    credentials = tmp_path / "pilot-users.txt"
    username = _username("closing")
    real_close = Session.close
    closed = []

    def fail_the_first_close(self, *args, **kwargs):
        if not closed:
            closed.append(True)
            raise OperationalError(
                "UPDATE app_user SET password_hash = %(hash_value)s",
                {"hash_value": "pbkdf2_sha256$1$00$visible"},
                RuntimeError("connection lost"),
            )
        return real_close(self, *args, **kwargs)

    monkeypatch.setattr(Session, "close", fail_the_first_close)
    capsys.readouterr()

    assert cli.main(["create", "--username", username, "--display-name", "Closing", "--role", "SALES_USER",
                     "--credentials-file", str(credentials)]) == 0

    printed = capsys.readouterr()
    assert closed  # the close really did fail
    assert "pbkdf2" not in printed.out + printed.err
    assert "password_hash" not in printed.out + printed.err
    assert "did not complete" not in printed.err  # it did complete; the backstop is not involved
    monkeypatch.setattr(Session, "close", real_close)

    with SessionLocal() as db:
        assert service.get_user(db, username) is not None
    assert [fields[2] for fields in _credential_lines(credentials)] == [username]


def test_an_unforeseen_database_error_is_reported_by_kind_not_as_a_traceback(capsys, monkeypatch):
    """The backstop in main(), a last resort rather than a working path.

    Nothing is expected to reach it, so it is driven directly. Its job is that no database error's
    text - which for these commands can hold a password hash - ever reaches a traceback.
    """

    def exploding_handler(args):
        raise OperationalError(
            "UPDATE app_user SET password_hash = %(hash_value)s",
            {"hash_value": "pbkdf2_sha256$1$00$visible"},
            RuntimeError("connection lost"),
        )

    monkeypatch.setattr(cli, "_cmd_list", exploding_handler)  # bound into the parser as it is built
    capsys.readouterr()

    assert cli.main(["list"]) == cli.EXIT_NOT_CONFIRMED

    printed = capsys.readouterr()
    assert "the database call did not complete (OperationalError)" in printed.err
    assert "If the command changes something" in printed.err  # true of a read as well as a write
    assert "pbkdf2" not in printed.out + printed.err
    assert "password_hash" not in printed.out + printed.err


def test_a_failed_commit_keeps_no_password_line_and_no_account(tmp_path, capsys, monkeypatch):
    credentials = tmp_path / "pilot-users.txt"
    _create(credentials, "sales-01")
    before = credentials.read_bytes()
    username = _username("sales-02")

    def failing_commit(self):
        raise OperationalError("COMMIT", {}, RuntimeError("connection lost"))

    monkeypatch.setattr(Session, "commit", failing_commit)
    capsys.readouterr()

    assert cli.main(["create", "--username", username, "--display-name", "Pilot 2", "--role", "SALES_USER",
                     "--credentials-file", str(credentials)]) == 2

    printed = capsys.readouterr()
    assert "Nothing was saved" in printed.err
    assert "pbkdf2" not in printed.out + printed.err
    assert credentials.read_bytes() == before
    monkeypatch.undo()
    with SessionLocal() as db:
        assert service.get_user(db, username) is None


def test_a_write_that_fails_part_way_is_cut_back(tmp_path, capsys, monkeypatch):
    credentials = tmp_path / "pilot-users.txt"
    _create(credentials, "sales-01")
    before = credentials.read_bytes()
    username = _username("sales-02")
    real_write = os.write
    calls = []

    def short_write_then_full_disk(descriptor, data):
        calls.append(len(data))
        if len(calls) == 1:
            return real_write(descriptor, data[:5])
        raise OSError(errno.ENOSPC, "No space left on device")

    monkeypatch.setattr(credentials_module, "_write", short_write_then_full_disk)
    capsys.readouterr()

    assert cli.main(["create", "--username", username, "--display-name", "Pilot 2", "--role", "SALES_USER",
                     "--credentials-file", str(credentials)]) == 2

    assert "No space left on device" in capsys.readouterr().err
    assert len(calls) == 2
    assert credentials.read_bytes() == before
    with SessionLocal() as db:
        assert service.get_user(db, username) is None


def test_a_new_file_and_its_name_are_on_disk_before_the_commit(tmp_path, monkeypatch):
    credentials = tmp_path / "pilot-users.txt"
    order = []
    real_fsync_directory = credentials_module._fsync_directory
    real_commit = Session.commit

    def fsync_directory(folder):
        order.append(("directory", "flushed"))
        real_fsync_directory(folder)

    def commit(self):
        order.append(("commit", [fields[2] for fields in _credential_lines(credentials)]))
        real_commit(self)

    monkeypatch.setattr(credentials_module, "_fsync_directory", fsync_directory)
    monkeypatch.setattr(Session, "commit", commit)

    first = _create(credentials, "sales-01")
    second = _create(credentials, "sales-02")

    # The directory is flushed once, when the file is created; each commit finds its line already there.
    assert order == [("directory", "flushed"), ("commit", [first]), ("commit", [first, second])]


def test_if_a_new_file_cannot_be_made_durable_nothing_is_saved_and_no_file_is_left(tmp_path, capsys, monkeypatch):
    credentials = tmp_path / "pilot-users.txt"
    username = _username("not-durable")

    def failing_fsync_directory(folder):
        raise OSError(errno.EIO, "Input/output error")

    monkeypatch.setattr(credentials_module, "_fsync_directory", failing_fsync_directory)

    assert cli.main(["create", "--username", username, "--display-name", "X", "--role", "SALES_USER",
                     "--credentials-file", str(credentials)]) == 2

    assert "Input/output error" in capsys.readouterr().err
    assert not credentials.exists()
    with SessionLocal() as db:
        assert service.get_user(db, username) is None


def test_a_commit_whose_confirmation_is_lost_keeps_the_new_password(tmp_path, capsys, monkeypatch):
    credentials = tmp_path / "pilot-users.txt"
    username = _create(credentials, "sales-01")
    old_password = _password_for(credentials, username)
    real_commit = Session.commit

    def commit_then_lose_the_connection(self):
        real_commit(self)
        raise OperationalError("COMMIT", {}, RuntimeError("connection lost after the commit"))

    monkeypatch.setattr(Session, "commit", commit_then_lose_the_connection)
    capsys.readouterr()

    assert cli.main(["reset-password", "--username", username, "--credentials-file", str(credentials)]) == 0

    printed = capsys.readouterr()
    assert "confirmed afterwards that it was" in printed.out
    new_password = _password_for(credentials, username)
    assert new_password != old_password
    assert new_password not in printed.out + printed.err
    monkeypatch.undo()  # sign-in records an event and commits
    assert _login(username, new_password).status_code == 200
    assert _login(username, old_password).status_code == 401


def test_a_commit_whose_outcome_cannot_be_found_keeps_the_line_and_says_so(tmp_path, capsys, monkeypatch):
    credentials = tmp_path / "pilot-users.txt"
    username = _username("unconfirmed")
    asked = []

    def failing_commit(self):
        raise OperationalError("COMMIT", {}, RuntimeError("connection lost"))

    def unreachable(db, transaction_id):
        asked.append(transaction_id)
        raise OperationalError("SELECT pg_xact_status", {}, RuntimeError("database unreachable"))

    monkeypatch.setattr(Session, "commit", failing_commit)
    monkeypatch.setattr(service, "transaction_status", unreachable)
    monkeypatch.setattr(cli, "COMMIT_CHECK_INTERVAL_SECONDS", 0)

    assert cli.main(["create", "--username", username, "--display-name", "X", "--role", "SALES_USER",
                     "--credentials-file", str(credentials)]) == cli.EXIT_NOT_CONFIRMED

    printed = capsys.readouterr()
    assert "Not confirmed" in printed.err and "run the command again" in printed.err
    assert "marked unconfirmed" in printed.err
    assert [mark for mark in _unconfirmed_marks(credentials) if username in mark]
    assert len(asked) == cli.COMMIT_CHECK_ATTEMPTS
    assert [fields[2] for fields in _credential_lines(credentials)] == [username]
    assert _password_for(credentials, username) not in printed.out + printed.err
    assert "pbkdf2" not in printed.out + printed.err


def test_a_mark_that_cannot_be_written_is_reported_instead_of_claimed(tmp_path, capsys, monkeypatch):
    credentials = tmp_path / "pilot-users.txt"
    username = _username("unmarkable")
    real_write = os.write

    def write_everything_except_the_mark(descriptor, data):
        if data.startswith(credentials_module.UNCONFIRMED_MARK.encode("utf-8")):
            raise OSError(errno.EIO, "Input/output error")
        return real_write(descriptor, data)

    def failing_commit(self):
        raise OperationalError("COMMIT", {}, RuntimeError("connection lost"))

    def unreachable(db, transaction_id):
        raise OperationalError("SELECT pg_xact_status", {}, RuntimeError("database unreachable"))

    monkeypatch.setattr(credentials_module, "_write", write_everything_except_the_mark)
    monkeypatch.setattr(Session, "commit", failing_commit)
    monkeypatch.setattr(service, "transaction_status", unreachable)
    monkeypatch.setattr(cli, "COMMIT_CHECK_INTERVAL_SECONDS", 0)

    assert cli.main(["create", "--username", username, "--display-name", "X", "--role", "SALES_USER",
                     "--credentials-file", str(credentials)]) == cli.EXIT_NOT_CONFIRMED

    printed = capsys.readouterr()
    assert "not reliably written there" in printed.err
    assert "marked unconfirmed, in case it was" not in printed.err
    assert not _unconfirmed_marks(credentials)
    assert [fields[2] for fields in _credential_lines(credentials)] == [username]  # the line itself is kept
    assert _password_for(credentials, username) not in printed.out + printed.err


def test_a_mark_that_cannot_be_flushed_is_reported_instead_of_claimed(tmp_path, capsys, monkeypatch):
    credentials = tmp_path / "pilot-users.txt"
    username = _username("unflushable")
    real_write = os.write
    real_fsync = os.fsync
    mark_written = []

    def note_the_mark(descriptor, data):
        if data.startswith(credentials_module.UNCONFIRMED_MARK.encode("utf-8")):
            mark_written.append(descriptor)
        return real_write(descriptor, data)

    def fsync_until_the_mark(descriptor):
        if mark_written:
            raise OSError(errno.EIO, "Input/output error")
        return real_fsync(descriptor)

    def failing_commit(self):
        raise OperationalError("COMMIT", {}, RuntimeError("connection lost"))

    def unreachable(db, transaction_id):
        raise OperationalError("SELECT pg_xact_status", {}, RuntimeError("database unreachable"))

    monkeypatch.setattr(credentials_module, "_write", note_the_mark)
    monkeypatch.setattr(credentials_module, "_fsync", fsync_until_the_mark)
    monkeypatch.setattr(Session, "commit", failing_commit)
    monkeypatch.setattr(service, "transaction_status", unreachable)
    monkeypatch.setattr(cli, "COMMIT_CHECK_INTERVAL_SECONDS", 0)

    assert cli.main(["create", "--username", username, "--display-name", "X", "--role", "SALES_USER",
                     "--credentials-file", str(credentials)]) == cli.EXIT_NOT_CONFIRMED

    printed = capsys.readouterr()
    # The note was written, but an unflushed write is not a record: it may not survive a crash.
    # So it is taken back out, and reported as unwritten rather than claimed.
    assert mark_written and not _unconfirmed_marks(credentials)
    assert "not reliably written there" in printed.err
    assert "marked unconfirmed, in case it was" not in printed.err
    assert credentials.read_bytes().endswith(b"\n")
    assert [fields[2] for fields in _credential_lines(credentials)] == [username]


def _restore_real_writes(monkeypatch):
    """Put back only what a test replaced.

    monkeypatch.undo() would also undo the autouse credentials-folder fixture, which stands in
    for the mounted folder, so the tool would then refuse the test's own file.
    """
    monkeypatch.setattr(credentials_module, "_write", os.write)
    monkeypatch.setattr(credentials_module, "_fsync", os.fsync)
    monkeypatch.setattr(credentials_module, "_ftruncate", os.ftruncate)
    monkeypatch.setattr(Session, "commit", _REAL_COMMIT)


def _lose_the_commit_and_the_answer(monkeypatch):
    """An unknown commit outcome: the commit fails and the database cannot be asked about it."""

    def failing_commit(self):
        raise OperationalError("COMMIT", {}, RuntimeError("connection lost"))

    def unreachable(db, transaction_id):
        raise OperationalError("SELECT pg_xact_status", {}, RuntimeError("database unreachable"))

    monkeypatch.setattr(Session, "commit", failing_commit)
    monkeypatch.setattr(service, "transaction_status", unreachable)
    monkeypatch.setattr(cli, "COMMIT_CHECK_INTERVAL_SECONDS", 0)


def _fail_the_mark_part_way(monkeypatch):
    """Write the first 30 bytes of the mark, then fail, leaving the file ending mid-line."""
    real_write = os.write

    def half_write_the_mark(descriptor, data):
        if data.startswith(credentials_module.UNCONFIRMED_MARK.encode("utf-8")):
            real_write(descriptor, data[:30])
            raise OSError(errno.ENOSPC, "No space left on device")
        return real_write(descriptor, data)

    monkeypatch.setattr(credentials_module, "_write", half_write_the_mark)


def _refuse_to_cut_back(monkeypatch):
    def refuse(descriptor, length):
        raise OSError(errno.EIO, "Input/output error")

    monkeypatch.setattr(credentials_module, "_ftruncate", refuse)


def _interrupt_the_mark_part_way(monkeypatch):
    """Write the first 30 bytes of the mark, then Ctrl+C, as an operator can at any moment."""
    real_write = os.write

    def interrupt_half_way(descriptor, data):
        if data.startswith(credentials_module.UNCONFIRMED_MARK.encode("utf-8")):
            real_write(descriptor, data[:30])
            raise KeyboardInterrupt
        return real_write(descriptor, data)

    monkeypatch.setattr(credentials_module, "_write", interrupt_half_way)


def test_a_mark_that_fails_part_way_is_cut_back_so_the_next_line_stays_a_line(tmp_path, capsys, monkeypatch):
    """A half-written mark must not swallow the next password into its own comment."""
    credentials = tmp_path / "pilot-users.txt"
    first = _create(credentials, "sales-01")
    username = _username("sales-02")
    _fail_the_mark_part_way(monkeypatch)
    _lose_the_commit_and_the_answer(monkeypatch)
    capsys.readouterr()

    assert cli.main(["create", "--username", username, "--display-name", "Pilot 2", "--role", "SALES_USER",
                     "--credentials-file", str(credentials)]) == cli.EXIT_NOT_CONFIRMED

    printed = capsys.readouterr()
    assert "not reliably written there" in printed.err
    assert "incomplete line" not in printed.err
    assert not _unconfirmed_marks(credentials)  # the half-written note was taken back out
    assert credentials.read_bytes().endswith(b"\n")
    assert [fields[2] for fields in _credential_lines(credentials)] == [first, username]

    _restore_real_writes(monkeypatch)
    third = _create(credentials, "sales-03")  # the file is still usable, and the new line is its own
    assert [fields[2] for fields in _credential_lines(credentials)] == [first, username, third]
    assert _password_for(credentials, third) != _password_for(credentials, username)


def test_a_half_written_mark_that_cannot_be_cut_back_is_reported_and_stops_later_appends(tmp_path, capsys, monkeypatch):
    credentials = tmp_path / "pilot-users.txt"
    first = _create(credentials, "sales-01")
    username = _username("sales-02")

    _fail_the_mark_part_way(monkeypatch)
    _refuse_to_cut_back(monkeypatch)
    _lose_the_commit_and_the_answer(monkeypatch)
    capsys.readouterr()

    assert cli.main(["create", "--username", username, "--display-name", "Pilot 2", "--role", "SALES_USER",
                     "--credentials-file", str(credentials)]) == cli.EXIT_NOT_CONFIRMED

    printed = capsys.readouterr()
    assert "ends in an incomplete `# unconfirmed:` line" in printed.err
    assert "not the password line above it" in printed.err  # the password line is the one to keep
    assert not credentials.read_bytes().endswith(b"\n")  # the file is damaged, and the output says so

    _restore_real_writes(monkeypatch)
    third = _username("sales-03")
    assert cli.main(["create", "--username", third, "--display-name", "Pilot 3", "--role", "SALES_USER",
                     "--credentials-file", str(credentials)]) == 2

    refusal = capsys.readouterr()
    assert "ends in an incomplete line" in refusal.err  # refused, rather than appended to
    assert first in credentials.read_text() and third not in credentials.read_text()
    with SessionLocal() as db:
        assert service.get_user(db, third) is None


def test_a_note_that_wrote_nothing_is_not_called_damage_when_the_cut_back_fails(tmp_path, capsys, monkeypatch):
    """The file still ends at the password line, so the owner must not be told to remove it.

    The cut-back has nothing to cut back here, and its failing says nothing about the file. If that
    alone were read as damage, the recovery instruction would delete a complete password line - and
    if the commit did take effect, that line is the only copy of the password the account now has.
    """
    credentials = tmp_path / "pilot-users.txt"
    first = _create(credentials, "sales-01")
    username = _username("sales-02")
    real_write = os.write

    def refuse_the_mark(descriptor, data):
        if data.startswith(credentials_module.UNCONFIRMED_MARK.encode("utf-8")):
            raise OSError(errno.ENOSPC, "No space left on device")  # before any byte is written
        return real_write(descriptor, data)

    monkeypatch.setattr(credentials_module, "_write", refuse_the_mark)
    _refuse_to_cut_back(monkeypatch)
    _lose_the_commit_and_the_answer(monkeypatch)
    capsys.readouterr()

    assert cli.main(["create", "--username", username, "--display-name", "Pilot 2", "--role", "SALES_USER",
                     "--credentials-file", str(credentials)]) == cli.EXIT_NOT_CONFIRMED

    printed = capsys.readouterr()
    assert "not reliably written there" in printed.err
    assert "incomplete" not in printed.err and "Remove" not in printed.err  # nothing to remove
    assert credentials.read_bytes().endswith(b"\n")  # the file was never damaged
    assert [fields[2] for fields in _credential_lines(credentials)] == [first, username]

    _restore_real_writes(monkeypatch)
    third = _create(credentials, "sales-03")  # so it is still usable, unrepaired
    assert [fields[2] for fields in _credential_lines(credentials)] == [first, username, third]


def test_an_interruption_that_leaves_a_half_written_note_reports_the_damage(tmp_path, capsys, monkeypatch):
    """Ctrl+C during the note must not be reported as a note that simply could not be written.

    The note only catches I/O errors elsewhere; an interruption escaping it would leave the file
    ending mid-line while the command said the file held nothing about the doubt.
    """
    credentials = tmp_path / "pilot-users.txt"
    first = _create(credentials, "sales-01")
    username = _username("sales-02")
    _interrupt_the_mark_part_way(monkeypatch)
    _refuse_to_cut_back(monkeypatch)
    _lose_the_commit_and_the_answer(monkeypatch)
    capsys.readouterr()

    assert cli.main(["create", "--username", username, "--display-name", "Pilot 2", "--role", "SALES_USER",
                     "--credentials-file", str(credentials)]) == cli.EXIT_NOT_CONFIRMED

    printed = capsys.readouterr()
    assert "ends in an incomplete `# unconfirmed:` line" in printed.err
    assert "not the password line above it" in printed.err
    assert not credentials.read_bytes().endswith(b"\n")
    assert [fields[2] for fields in _credential_lines(credentials)] == [first, username]

    _restore_real_writes(monkeypatch)
    third = _username("sales-03")
    assert cli.main(["create", "--username", third, "--display-name", "Pilot 3", "--role", "SALES_USER",
                     "--credentials-file", str(credentials)]) == 2  # refused until the line is removed


def test_an_interruption_during_the_note_leaves_the_file_whole_when_it_can_be_cut_back(tmp_path, capsys, monkeypatch):
    credentials = tmp_path / "pilot-users.txt"
    first = _create(credentials, "sales-01")
    username = _username("sales-02")
    _interrupt_the_mark_part_way(monkeypatch)
    _lose_the_commit_and_the_answer(monkeypatch)
    capsys.readouterr()

    assert cli.main(["create", "--username", username, "--display-name", "Pilot 2", "--role", "SALES_USER",
                     "--credentials-file", str(credentials)]) == cli.EXIT_NOT_CONFIRMED

    printed = capsys.readouterr()
    assert "not reliably written there" in printed.err
    assert "incomplete" not in printed.err
    assert not _unconfirmed_marks(credentials)  # the half-written note was taken back out
    assert credentials.read_bytes().endswith(b"\n")

    _restore_real_writes(monkeypatch)
    third = _create(credentials, "sales-03")
    assert [fields[2] for fields in _credential_lines(credentials)] == [first, username, third]


def test_a_whole_note_left_in_the_file_is_not_called_damage_either(tmp_path, capsys, monkeypatch):
    """The note is there, complete, and the file ends in a newline: nothing to repair by hand.

    Its flush failed and it could not be taken back out, so it may not survive a crash. It is
    therefore not claimed as written either - the message covers both.
    """
    credentials = tmp_path / "pilot-users.txt"
    first = _create(credentials, "sales-01")
    username = _username("sales-02")
    real_write = os.write
    real_fsync = os.fsync
    mark_written = []

    def note_the_mark(descriptor, data):
        if data.startswith(credentials_module.UNCONFIRMED_MARK.encode("utf-8")):
            mark_written.append(descriptor)
        return real_write(descriptor, data)

    def fsync_until_the_mark(descriptor):
        if mark_written:
            raise OSError(errno.EIO, "Input/output error")
        return real_fsync(descriptor)

    monkeypatch.setattr(credentials_module, "_write", note_the_mark)
    monkeypatch.setattr(credentials_module, "_fsync", fsync_until_the_mark)
    _refuse_to_cut_back(monkeypatch)
    _lose_the_commit_and_the_answer(monkeypatch)
    capsys.readouterr()

    assert cli.main(["create", "--username", username, "--display-name", "Pilot 2", "--role", "SALES_USER",
                     "--credentials-file", str(credentials)]) == cli.EXIT_NOT_CONFIRMED

    printed = capsys.readouterr()
    assert "not reliably written there" in printed.err
    assert "incomplete" not in printed.err and "Remove" not in printed.err
    assert [mark for mark in _unconfirmed_marks(credentials) if username in mark]  # it is in the file
    assert credentials.read_bytes().endswith(b"\n")

    _restore_real_writes(monkeypatch)
    third = _create(credentials, "sales-03")  # undamaged, so the next line is still its own
    assert [fields[2] for fields in _credential_lines(credentials)] == [first, username, third]


def test_a_credentials_file_ending_in_an_incomplete_line_is_refused(tmp_path, capsys):
    """A file a killed run left mid-line: a password appended to it would read as part of a comment."""
    credentials = tmp_path / "pilot-users.txt"
    credentials.write_text(CREDENTIALS_FILE_HEADER + "# unconfirmed: the line above, for some", encoding="utf-8")
    before = credentials.read_bytes()
    username = _username("sales-01")

    assert cli.main(["create", "--username", username, "--display-name", "Pilot 1", "--role", "SALES_USER",
                     "--credentials-file", str(credentials)]) == 2

    printed = capsys.readouterr()
    assert "ends in an incomplete line" in printed.err and "not written in full" in printed.err
    assert credentials.read_bytes() == before
    with SessionLocal() as db:
        assert service.get_user(db, username) is None


def test_an_unconfirmed_reset_that_was_never_saved_is_not_settled_by_list(tmp_path, capsys, monkeypatch):
    """The recovery instruction must not be `list`: both outcomes look identical to it.

    Here the reset genuinely did not take effect, and the kept line names a password the account
    does not have - while `list` still shows the account, active and with some password. An operator
    who read that as confirmation would hand out a password that does not work.
    """
    credentials = tmp_path / "pilot-users.txt"
    username = _create(credentials, "sales-01")
    old_password = _password_for(credentials, username)

    def commit_that_loses_the_change(self):
        self.rollback()
        raise OperationalError("COMMIT", {}, RuntimeError("connection lost"))

    def unreachable(db, transaction_id):
        raise OperationalError("SELECT pg_xact_status", {}, RuntimeError("database unreachable"))

    monkeypatch.setattr(Session, "commit", commit_that_loses_the_change)
    monkeypatch.setattr(service, "transaction_status", unreachable)
    monkeypatch.setattr(cli, "COMMIT_CHECK_INTERVAL_SECONDS", 0)
    capsys.readouterr()

    assert cli.main(["reset-password", "--username", username,
                     "--credentials-file", str(credentials)]) == cli.EXIT_NOT_CONFIRMED

    printed = capsys.readouterr()
    assert "`list` cannot settle a reset" in printed.err
    assert "Sign in with the kept password" in printed.err
    assert "run reset-password and hand out only a password from a run that reported success" in printed.err
    kept = _password_for(credentials, username)
    assert kept != old_password
    assert kept not in printed.out + printed.err

    monkeypatch.undo()  # a sign-in records an event and commits
    with SessionLocal() as db:
        summary = service.get_user(db, username)
    assert summary is not None and summary.is_active and summary.has_password  # all `list` can show
    assert _login(username, kept).status_code == 401  # the kept line is not the account's password
    assert _login(username, old_password).status_code == 200  # the old password still works


def test_an_interruption_as_the_commit_took_effect_keeps_the_new_password(tmp_path, capsys, monkeypatch):
    credentials = tmp_path / "pilot-users.txt"
    username = _create(credentials, "sales-01")
    old_password = _password_for(credentials, username)
    real_commit = Session.commit

    def commit_then_interrupt(self):
        real_commit(self)
        raise KeyboardInterrupt

    monkeypatch.setattr(Session, "commit", commit_then_interrupt)
    capsys.readouterr()

    assert cli.main(["reset-password", "--username", username, "--credentials-file", str(credentials)]) == 0

    assert "Interrupted as the change was saved" in capsys.readouterr().out
    new_password = _password_for(credentials, username)
    assert new_password != old_password
    monkeypatch.undo()  # sign-in records an event and commits
    assert _login(username, new_password).status_code == 200
    assert _login(username, old_password).status_code == 401


def test_an_interruption_before_the_commit_took_effect_removes_the_line(tmp_path, capsys, monkeypatch):
    credentials = tmp_path / "pilot-users.txt"
    _create(credentials, "sales-01")
    before = credentials.read_bytes()
    username = _username("sales-02")

    def interrupted_commit(self):
        raise KeyboardInterrupt

    monkeypatch.setattr(Session, "commit", interrupted_commit)
    capsys.readouterr()

    assert cli.main(["create", "--username", username, "--display-name", "Pilot 2", "--role", "SALES_USER",
                     "--credentials-file", str(credentials)]) == cli.EXIT_INTERRUPTED

    assert "nothing was saved and no password was kept" in capsys.readouterr().err
    assert credentials.read_bytes() == before
    monkeypatch.undo()
    with SessionLocal() as db:
        assert service.get_user(db, username) is None


def test_a_role_change_whose_commit_confirmation_is_lost_is_reported_as_saved(tmp_path, capsys, monkeypatch):
    credentials = tmp_path / "pilot-users.txt"
    username = _create(credentials, "manager-01", "SALES_USER")
    real_commit = Session.commit

    def commit_then_lose_the_connection(self):
        real_commit(self)
        raise OperationalError("COMMIT", {}, RuntimeError("connection lost after the commit"))

    monkeypatch.setattr(Session, "commit", commit_then_lose_the_connection)
    capsys.readouterr()

    assert cli.main(["set-roles", "--username", username, "--role", "FINANCE_USER"]) == 0

    assert "confirmed afterwards that it was" in capsys.readouterr().out
    monkeypatch.undo()
    with SessionLocal() as db:
        assert service.get_user(db, username).role_codes == ("FINANCE_USER",)


def test_a_role_change_whose_commit_did_not_take_effect_is_reported_as_refused(tmp_path, capsys, monkeypatch):
    credentials = tmp_path / "pilot-users.txt"
    username = _create(credentials, "manager-01", "SALES_USER")

    def failing_commit(self):
        raise OperationalError("COMMIT", {}, RuntimeError("connection lost"))

    monkeypatch.setattr(Session, "commit", failing_commit)
    capsys.readouterr()

    assert cli.main(["set-roles", "--username", username, "--role", "FINANCE_USER"]) == 2

    assert "Nothing was saved" in capsys.readouterr().err
    monkeypatch.undo()
    with SessionLocal() as db:
        assert service.get_user(db, username).role_codes == ("SALES_USER",)


def test_an_interrupted_disable_changes_nothing_and_says_so(tmp_path, capsys, monkeypatch):
    credentials = tmp_path / "pilot-users.txt"
    username = _create(credentials, "sales-01")

    def interrupted_commit(self):
        raise KeyboardInterrupt

    monkeypatch.setattr(Session, "commit", interrupted_commit)
    capsys.readouterr()

    assert cli.main(["disable", "--username", username]) == cli.EXIT_INTERRUPTED

    assert "nothing was saved" in capsys.readouterr().err
    monkeypatch.undo()
    with SessionLocal() as db:
        assert service.get_user(db, username).is_active


def test_list_shows_state_and_roles_but_no_password_material(tmp_path, capsys):
    credentials = tmp_path / "pilot-users.txt"
    username = _create(credentials, "ops-01", "OPERATIONS_USER")
    capsys.readouterr()

    assert cli.main(["list"]) == 0

    out = capsys.readouterr().out
    assert f"{username} (Pilot ops-01) - active - OPERATIONS_USER" in out
    assert "pbkdf2" not in out
    assert _password_for(credentials, username) not in out


def test_the_tool_is_not_reachable_through_the_api():
    paths = [getattr(route, "path", "") for route in app.routes]
    assert not [path for path in paths if "user-admin" in path or "user_admin" in path or "tooling" in path]
    assert "tooling" not in (BACKEND_ROOT / "app" / "main.py").read_text()
