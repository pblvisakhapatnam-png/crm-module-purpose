"""TB-1 TB1-204 part a: sign-in hardening (record: docs/continuity/TB1_204A_SIGN_IN_HARDENING.md).

The owner's decisions of 7 October 2026: five failed sign-ins for one username within fifteen minutes stop it for
fifteen minutes, counted per typed username, lifted early by the account tool's `unlock`; a password reset,
disabling and retiring end every earlier sign-in, and so does the tool's `end-sign-ins`; a role change needs nothing,
because roles are read on every request; passwords set by the tool are at least 12 characters, without the username
or an obvious word; the token stays where the browser keeps it. And three ordinary safeguards: 600,000 PBKDF2
iterations, upgraded at the next sign-in; an unknown username costs the same hashing as a known one; a malformed
token is a 401.

Every account here carries a per-run prefix and is removed afterwards, with the sign-in counts its names left. The six
demo users are never stopped: every lockout is on a throwaway name.
"""

from __future__ import annotations

import hashlib
import hmac
import inspect
import io
import json
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import text

import tooling.user_admin.credentials as credentials_module
from app.core import security
from app.core.config import STANDARD_PASSWORD_HASH_ITERATIONS, get_settings
from app.core.database import SessionLocal
from app.core.security import (
    password_iterations,
    TokenError,
    _base64url_encode,
    _json_dumps,
    decode_access_token,
    hash_password,
    password_hash_needs_upgrade,
    verify_password,
)
from app.main import app
from app.modules.identity import routes as identity_routes
from app.modules.identity import service as identity_service
from app.modules.identity import throttle
from app.modules.identity.password_rules import MIN_PASSWORD_LENGTH, OBVIOUS_FRAGMENTS, password_problem
from app.modules.identity.repository import replace_password_hash
from tooling.user_admin import cli, service
from tooling.user_admin.credentials import PASSWORD_SYMBOLS, PASSWORD_WORDS, generate_password
from tests.test_user_admin_tooling import _lose_the_commit_and_the_answer

client = TestClient(app)
# For the fault tests: a request that fails answers 500 instead of raising into the test.
failing_client = TestClient(app, raise_server_exceptions=False)

PREFIX = f"tb1a-{uuid4().hex[:8]}-"
STOPPED_FOR_15 = "Too many failed sign-ins for this username. Try again in 15 minutes."
# A wrong password, named so that no request body below assigns a literal to a password key (the committed-credential
# check's SEC-004 refuses that shape, rightly, whatever the value).
WRONG = "Wrong#Guess123"
# Text the event log refuses since TB-1 TB1-500 (CS-02, merged first): an address with a password in it, which proves
# itself a credential. Assembled, so the committed-credential check does not read this file as holding one.
CREDENTIAL_SHAPED = "https" + "://desk" + ":" + "pw-2026" + "@example.test"
# An older hash: fewer iterations than the current count (600,000; development and CI may set fewer).
OLD_ITERATIONS = password_iterations() // 2

_names_used: set[str] = set()


def _name(label: str) -> str:
    name = f"{PREFIX}{label}"
    _names_used.add(name)
    return name


@pytest.fixture(autouse=True)
def _clean_up():
    yield
    with SessionLocal() as db:
        for name in _names_used:
            digest = throttle.username_digest(db, name)
            db.execute(text("DELETE FROM sign_in_attempt WHERE username_digest = :digest"), {"digest": digest})
            db.execute(text("DELETE FROM sign_in_stop WHERE username_digest = :digest"), {"digest": digest})
        db.execute(
            text("DELETE FROM user_role WHERE user_id IN (SELECT id FROM app_user WHERE username LIKE :prefix)"),
            {"prefix": PREFIX + "%"},
        )
        db.execute(text("DELETE FROM app_user WHERE username LIKE :prefix"), {"prefix": PREFIX + "%"})
        db.commit()


@pytest.fixture
def credentials(tmp_path, monkeypatch) -> Path:
    # The tool writes only directly in its mounted credentials folder; the test's temporary folder stands in.
    monkeypatch.setattr(credentials_module, "CREDENTIALS_DIR", tmp_path)
    monkeypatch.setattr(credentials_module, "_is_mount", lambda folder: True)
    return tmp_path / "pilot-users.txt"


def _user(label: str, password: str = "Fictional#Tester-2026", *, password_hash: str | None = None) -> str:
    name = _name(label)
    with SessionLocal() as db:
        service.create_user(
            db, username=name, display_name=f"Sign-in {label}", role_codes=["SALES_USER"],
            password_hash=password_hash or hash_password(password),
        )
        db.commit()
    return name


def _insert_account(name: str, public_id: str | None = None) -> str:
    """An account the account tool would refuse to create - its username holds text the event log refuses - as a
    database may still hold one; its public id may be any 36 characters, not only a UUID. Returns the public id."""
    public_id = public_id or str(uuid4())
    with SessionLocal() as db:
        user_id = db.execute(
            text(
                "INSERT INTO app_user (public_id, username, display_name, password_hash, is_active) "
                "VALUES (:public_id, :username, 'Sign-in desk', :password_hash, TRUE) RETURNING id"
            ),
            {"public_id": public_id, "username": name, "password_hash": hash_password("Fictional#Tester-2026")},
        ).scalar_one()
        db.execute(
            text("INSERT INTO user_role (user_id, role_id) SELECT :user_id, id FROM role WHERE role_code = 'SALES_USER'"),
            {"user_id": user_id},
        )
        db.commit()
    return public_id


def _login(username: str, password: str):
    return client.post("/api/auth/login", json={"username": username, "password": password})


def _me(token: str):
    # As bytes, as a browser or curl sends them: the HTTP client refuses a non-ASCII header given as text.
    return client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}".encode("utf-8")})


def _event_boundary() -> int:
    with SessionLocal() as db:
        return int(db.execute(text("SELECT COALESCE(MAX(id), 0) FROM business_event")).scalar_one())


def _events_since(boundary: int) -> list[dict]:
    with SessionLocal() as db:
        rows = db.execute(
            text("SELECT * FROM business_event WHERE id > :boundary ORDER BY id"), {"boundary": boundary}
        ).all()
    return [dict(row._mapping) for row in rows]


def _payload(event: dict) -> dict:
    return json.loads(event["event_payload_json"]) if event["event_payload_json"] else {}


def _attempt_rows(name: str) -> list[dict]:
    with SessionLocal() as db:
        rows = db.execute(
            text("SELECT * FROM sign_in_attempt WHERE username_digest = :digest ORDER BY id"),
            {"digest": throttle.username_digest(db, name)},
        ).all()
    return [dict(row._mapping) for row in rows]


def _stop(name: str):
    """When the name's stop in force ends, or None."""
    with SessionLocal() as db:
        return db.execute(
            text("SELECT locked_until FROM sign_in_stop WHERE username_digest = :digest AND locked_until > now()"),
            {"digest": throttle.username_digest(db, name)},
        ).scalar()


def _register(name: str, moment: datetime) -> throttle.Attempt:
    with SessionLocal() as db:
        attempt = throttle.register_attempt(db, name, moment)
        db.commit()
    return attempt


def _shift_throttle(name: str, *, attempts: timedelta | None = None, stop: timedelta | None = None) -> None:
    """Move a name's recent attempts, or its stop, into the past, as if that much time had gone by."""
    with SessionLocal() as db:
        digest = throttle.username_digest(db, name)
        if attempts is not None:
            db.execute(
                text("UPDATE sign_in_attempt SET attempted_at = attempted_at - :delta WHERE username_digest = :digest"),
                {"delta": attempts, "digest": digest},
            )
        if stop is not None:
            db.execute(
                text("UPDATE sign_in_stop SET locked_until = locked_until - :delta WHERE username_digest = :digest"),
                {"delta": stop, "digest": digest},
            )
        db.commit()


def _legacy_token(name: str) -> str:
    """A token as issued before revision 20260908_0048: signed, valid, with no `ver`."""
    public_id = _me(_login(name, "Fictional#Tester-2026").json()["access_token"]).json()["public_id"]
    now = int(time.time())
    return _signed_token(
        {"sub": name, "user_public_id": public_id, "role_codes": ["SALES_USER"], "iat": now, "exp": now + 600}
    )


def _four_wrong(name: str) -> None:
    for _ in range(4):
        assert _login(name, "Wrong#Guess123").status_code == 401


def _stored_hash(name: str) -> str:
    with SessionLocal() as db:
        return str(db.execute(text("SELECT password_hash FROM app_user WHERE username = :u"), {"u": name}).scalar_one())


def _hash_with(password: str, iterations: int) -> str:
    salt = bytes(range(16))
    key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return f"pbkdf2_sha256${iterations}${salt.hex()}${key.hex()}"


def _signed_token(payload: object) -> str:
    """A token signed with the real secret, carrying whatever payload: what only someone with the secret could make."""
    header = _base64url_encode(_json_dumps({"alg": "HS256", "typ": "JWT"}))
    body = _base64url_encode(json.dumps(payload).encode("utf-8"))
    signature = hmac.new(get_settings().jwt_secret.encode("utf-8"), f"{header}.{body}".encode("ascii"), hashlib.sha256)
    return f"{header}.{body}.{_base64url_encode(signature.digest())}"


# Repeated wrong passwords ------------------------------------------------------------------------------------------


def test_the_fifth_wrong_password_stops_the_username_and_then_even_the_right_one_is_refused():
    name = _user("stopped")
    boundary = _event_boundary()

    for _ in range(4):
        assert _login(name, "Wrong#Guess123").status_code == 401
    fifth = _login(name, "Wrong#Guess123")
    assert fifth.status_code == 429
    assert fifth.json()["detail"] == STOPPED_FOR_15
    assert 890 <= int(fifth.headers["Retry-After"]) <= 900

    right = _login(name, "Fictional#Tester-2026")
    assert right.status_code == 429
    assert right.json()["detail"].startswith("Too many failed sign-ins for this username. Try again in ")

    events = _events_since(boundary)
    failed = [event for event in events if event["event_name"] == "UserLoginFailed"]
    locked = [event for event in events if event["event_name"] == "UserSignInLocked"]
    assert len(failed) == 6
    assert [event["reason"] for event in failed].count("Invalid credentials.") == 5
    assert failed[-1]["reason"] == "Refused: the username is stopped after repeated failed sign-ins."
    assert len(locked) == 1
    assert _payload(locked[0])["username"] == name
    assert datetime.fromisoformat(_payload(locked[0])["locked_until"]) > datetime.now(timezone.utc)
    assert not any(event["event_name"] == "UserLoginSucceeded" for event in events)


def test_a_stop_runs_out_and_the_right_password_then_signs_in():
    name = _user("runs-out")
    for _ in range(5):
        _login(name, "Wrong#Guess123")
    assert _login(name, "Fictional#Tester-2026").status_code == 429

    _shift_throttle(name, stop=timedelta(minutes=15), attempts=timedelta(minutes=15))

    assert _login(name, "Fictional#Tester-2026").status_code == 200
    assert _attempt_rows(name) == [] and _stop(name) is None


def test_a_stop_that_runs_out_starts_the_count_again():
    """A stop is never shorter than the window, so when it runs out the attempts that made it have left the window
    too, and counting starts again."""
    name = _user("counts-again")
    for _ in range(5):
        _login(name, "Wrong#Guess123")
    _shift_throttle(name, stop=timedelta(minutes=16), attempts=timedelta(minutes=16))

    assert [_login(name, "Wrong#Guess123").status_code for _ in range(5)] == [401, 401, 401, 401, 429]


def test_a_successful_sign_in_clears_the_count():
    """Here the right password comes on the fifth attempt, the one that reaches the limit: its stop is recorded with
    the stop, then lifted by the successful sign-in, and that is recorded too."""
    name = _user("cleared")
    for _ in range(4):
        assert _login(name, "Wrong#Guess123").status_code == 401
    boundary = _event_boundary()
    assert _login(name, "Fictional#Tester-2026").status_code == 200
    assert _attempt_rows(name) == [] and _stop(name) is None
    events = _events_since(boundary)
    assert [event["event_name"] for event in events] == ["UserSignInLocked", "UserSignInUnlocked", "UserLoginSucceeded"]
    assert events[1]["reason"] == "Lifted by a successful sign-in: too few attempts came after it to keep the stop."

    assert [_login(name, "Wrong#Guess123").status_code for _ in range(4)] == [401] * 4


def test_failures_older_than_the_window_no_longer_count():
    name = _user("window")
    for _ in range(4):
        _login(name, "Wrong#Guess123")
    _shift_throttle(name, attempts=timedelta(minutes=15, seconds=1))

    assert [_login(name, "Wrong#Guess123").status_code for _ in range(5)] == [401, 401, 401, 401, 429]


def test_the_window_rolls_so_no_boundary_lets_more_than_five_through():
    """One attempt, three just before its fifteen minutes are up, then more just after. A fixed window would start
    again at the boundary and check eight; the rolling one stops at the fifth within any fifteen minutes."""
    name = _name("rolling")
    t0 = datetime.now(timezone.utc) - timedelta(minutes=20)
    moments = (
        [t0]
        + [t0 + timedelta(minutes=14, seconds=59)] * 3
        + [t0 + timedelta(minutes=15, seconds=1 + offset) for offset in range(4)]
    )
    outcomes = []
    for moment in moments:
        with SessionLocal() as db:
            attempt = throttle.register_attempt(db, name, moment)
            db.commit()
        outcomes.append("stopped" if attempt.stopped_until else "stops" if attempt.stops_until else "checked")

    assert outcomes == ["checked"] * 5 + ["stops", "stopped", "stopped"]


def test_a_success_clears_only_its_own_attempt_and_those_before_it():
    """A right password registers first; four wrong ones register while it is being checked, the last of them
    reaching the limit. The success then clears only its own attempt: the four after it still count, the stop they
    could not make alone is lifted, and the next wrong password stops the name."""
    name = _name("success-first")
    now = datetime.now(timezone.utc)

    def register():
        with SessionLocal() as db:
            attempt = throttle.register_attempt(db, name, now)
            db.commit()
        return attempt

    success = register()
    later = [register() for _ in range(4)]
    assert [attempt.stops_until is not None for attempt in later] == [False, False, False, True]

    with SessionLocal() as db:
        lifted = throttle.clear_attempts(db, success, now)
        db.commit()
    assert lifted is True
    assert [row["id"] for row in _attempt_rows(name)] == [attempt.number for attempt in later]
    assert _stop(name) is None

    assert register().stops_until is not None, "the four failures after the success still count"


def test_pruning_removes_each_attempt_by_its_own_time_whatever_order_they_were_numbered_in():
    """Times are taken before the name's lock, so a later time can be numbered first. Each attempt is pruned by its own
    time, and only a minute past the window, so pruning never removes one a concurrent attempt could still count."""
    name, edge = _name("out-of-order"), _name("at-the-edge")
    now = datetime.now(timezone.utc)
    _register(name, now - timedelta(minutes=14))
    _register(name, now - timedelta(minutes=17))
    _register(edge, now - timedelta(minutes=15, seconds=30))

    with SessionLocal() as db:
        throttle.prune(db, now)
        db.commit()

    assert [row["attempted_at"] for row in _attempt_rows(name)] == [now - timedelta(minutes=14)]
    assert len(_attempt_rows(edge)) == 1, "within the minute's margin: kept, though no longer counted"
    assert _register(edge, now).stops_until is None
    assert _register(name, now).number is not None and len(_attempt_rows(name)) == 2


def test_a_success_paused_past_the_window_never_clears_a_later_attempt():
    """Attempt numbers come from a sequence and are never reused, even after pruning has removed every row a name had:
    a success whose check outlasted the window clears nothing that came after it."""
    name = _name("paused-success")
    now = datetime.now(timezone.utc)
    success = _register(name, now - timedelta(minutes=20))
    with SessionLocal() as db:
        throttle.prune(db, now)
        db.commit()
    assert _attempt_rows(name) == [], "pruned while its password was still being checked"

    later = _register(name, now)
    with SessionLocal() as db:
        throttle.clear_attempts(db, success, now)
        db.commit()

    assert [row["id"] for row in _attempt_rows(name)] == [later.number]


def test_the_stops_numbers_are_the_owners_and_no_configuration_changes_them(monkeypatch):
    """Five attempts within 15 minutes stop a username for 15 minutes, never shorter than the window (round 3). Round
    9: they are constants, not settings, so an environment variable cannot weaken the stop."""
    from app.core.config import Settings

    assert (throttle.ATTEMPT_LIMIT, throttle.ATTEMPT_WINDOW, throttle.STOP_LENGTH) == (
        5, timedelta(minutes=15), timedelta(minutes=15),
    )
    assert throttle.STOP_LENGTH >= throttle.ATTEMPT_WINDOW
    for variable in ("SIGN_IN_ATTEMPT_LIMIT", "SIGN_IN_ATTEMPT_WINDOW_MINUTES", "SIGN_IN_STOP_MINUTES"):
        monkeypatch.setenv(variable, "1000000000000")
    settings = Settings(app_env="development")
    assert not any(name.startswith("sign_in_") for name in type(settings).model_fields)
    name = _name("configured")
    for _ in range(4):
        assert _login(name, WRONG).status_code == 401
    assert _login(name, WRONG).status_code == 429


def test_an_unknown_username_is_stopped_the_same_way_and_what_was_typed_is_never_recorded():
    typed = _name("no-such-account")
    boundary = _event_boundary()

    assert [_login(typed, "Wrong#Guess123").status_code for _ in range(5)] == [401, 401, 401, 401, 429]
    assert _login(typed, "Wrong#Guess123").json()["detail"].startswith("Too many failed sign-ins")

    events = _events_since(boundary)
    assert {event["event_name"] for event in events} == {"UserLoginFailed", "UserSignInLocked"}
    assert all(_payload(event).get("username_known") is False for event in events)
    assert all("username" not in _payload(event) for event in events)
    assert not any(typed in str(event) for event in events)
    # Nor in the count's own tables: only the digest of the lower-cased name.
    rows = _attempt_rows(typed)
    digest = hashlib.sha256(typed.lower().encode("utf-8")).hexdigest()
    assert len(rows) == 5 and typed not in str(rows)
    assert {row["username_digest"] for row in rows} == {digest}
    assert _stop(typed) is not None


def test_a_password_typed_into_the_username_box_is_refused_cleanly_and_not_recorded():
    """Recording the typed name made a sign-in answer 500 when it held "password", "token" or "secret", which the event
    log refused until CS-02 (TB1-500), and 422 when it holds text shaped like a credential, which the log refuses since
    then. What was typed is no longer recorded at all."""
    boundary = _event_boundary()
    for typed in (_name("my-password-here"), _name("a-token-typed"), _name("secret-sauce"), _name("typed-") + CREDENTIAL_SHAPED):
        response = _login(typed, "Wrong#Guess123")
        assert response.status_code == 401, typed
    assert not any(PREFIX in str(event) for event in _events_since(boundary))


def test_an_account_whose_username_holds_text_the_event_log_refuses_signs_in_and_is_stopped_cleanly():
    """The event log refuses text shaped like a credential (TB-1 TB1-500; until CS-02 it refused the words "password",
    "token" and "secret"), so a sign-in event naming such an account by its username was refused - for the right
    password and the wrong one, and the stop could never be written. Such an account (the tool's username rule refuses
    the name, but a database may hold one) is named in its sign-in events by a fixed stand-in,
    `{"username_withheld": true}`, the event's record id naming the account (rounds 4 and 6)."""
    name = _name("the-desk-") + CREDENTIAL_SHAPED
    public_id = _insert_account(name)
    boundary = _event_boundary()

    assert _login(name, "Fictional#Tester-2026").status_code == 200
    assert [_login(name, WRONG).status_code for _ in range(5)] == [401, 401, 401, 401, 429]
    assert _login(name, "Fictional#Tester-2026").status_code == 429

    events = _events_since(boundary)
    assert [event["event_name"] for event in events] == (
        ["UserLoginSucceeded"] + ["UserLoginFailed"] * 4 + ["UserSignInLocked", "UserLoginFailed", "UserLoginFailed"]
    )
    assert all(event["record_public_id"] == public_id for event in events)
    assert all(_payload(event).get("username_withheld") is True and "username" not in _payload(event) for event in events)
    # Withheld whole - the success event's role codes and the stop's locked_until too - each composed with the real
    # username, then checked once (rounds 11 and 12).
    assert all(_payload(event) == {"username_withheld": True} for event in events)
    assert not any(name in str(event) for event in events)
    assert len(_attempt_rows(name)) == 5 and _stop(name) is not None


def test_the_account_tool_lifts_a_stop_and_ends_sign_ins_for_an_account_whose_username_holds_such_text(credentials):
    """The tool's own events named the account by username too, so on such an account unlock, end-sign-ins, a reset and
    disabling rolled back (exit 2) - the stop stood and earlier sign-ins survived. They now name it as the sign-in
    events do (round 5)."""
    name = _name("tool-desk-") + CREDENTIAL_SHAPED
    public_id = _insert_account(name)
    for _ in range(5):
        _login(name, WRONG)
    assert _stop(name) is not None
    boundary = _event_boundary()

    assert cli.main(["unlock", "--username", name]) == 0
    assert _stop(name) is None and _attempt_rows(name) == []
    earlier = _login(name, "Fictional#Tester-2026").json()["access_token"]
    assert cli.main(["end-sign-ins", "--username", name]) == 0
    assert _me(earlier).status_code == 401
    earlier = _login(name, "Fictional#Tester-2026").json()["access_token"]
    assert cli.main(["reset-password", "--username", name, "--credentials-file", str(credentials)]) == 0
    assert _me(earlier).status_code == 401
    password = [line.split("\t")[3] for line in credentials.read_text().splitlines() if name in line][-1]
    earlier = _login(name, password).json()["access_token"]
    assert cli.main(["disable", "--username", name]) == 0
    assert _me(earlier).status_code == 401

    tool_events = [event for event in _events_since(boundary) if event["reason"] == service.EVENT_REASON]
    assert [event["event_name"] for event in tool_events] == [
        "UserSignInUnlocked", "UserSignInsEnded", "UserPasswordReset", "UserAccountDisabled",
    ]
    assert all(event["record_public_id"] == public_id for event in tool_events)
    assert all(_payload(event) == {"username_withheld": True} for event in tool_events)
    assert not any(name in str(event) for event in tool_events)


@pytest.mark.parametrize(
    "command, also",
    [
        ("end-sign-ins", "the second also ends any sign-in made since"),
        ("unlock", "a second run lifts whatever stop is then in force, including one made by wrong passwords since"),
    ],
)
def test_a_lost_confirmation_says_what_running_end_sign_ins_or_unlock_again_does(command, also, monkeypatch, capsys):
    """`list` shows neither an account's sign-in number nor its stop, so it cannot settle these two commands' exit 3;
    and running either again acts on what happened since, so the message says so rather than calling it harmless."""
    name = _user(f"lost-{command}")
    _lose_the_commit_and_the_answer(monkeypatch)

    assert cli.main([command, "--username", name]) == cli.EXIT_NOT_CONFIRMED

    err = capsys.readouterr().err
    assert "`list` cannot show whether it was saved." in err and also in err
    assert "Check with `list`" not in err and "harmless" not in err


def test_the_tool_refuses_a_new_account_whose_display_name_holds_text_the_event_log_refuses():
    """Withholding an event's payload is for accounts a database already holds, not a way to create more: `create` asks
    the event log's own check first (round 7). Since CS-02 that refuses a credential's shape, not a word, so "Under
    Secretary" is created - the username rule already refuses every shape the log does."""
    refused, accepted = _name("new-desk"), _name("under-secretary")
    with SessionLocal() as db:
        with pytest.raises(service.UserAdminError, match="event log refuses"):
            service.create_user(
                db, username=refused, display_name="Desk " + CREDENTIAL_SHAPED, role_codes=["SALES_USER"],
                password_hash=hash_password("Fictional#Tester-2026"),
            )
        db.rollback()
        assert service.get_user(db, refused) is None
        created = service.create_user(
            db, username=accepted, display_name="Under Secretary", role_codes=["SALES_USER"],
            password_hash=hash_password("Fictional#Tester-2026"),
        )
        db.commit()
    assert created.display_name == "Under Secretary"


def test_a_role_code_holding_text_the_event_log_refuses_never_stops_a_sign_in_or_its_removal():
    """The whole payload is checked, not only the username: a success event lists the account's role codes and a role
    change lists both sets, so a role code holding refused text made a correct sign-in fail - after its attempt was
    counted - and the role impossible to remove. Such an event's payload is withheld whole (round 7)."""
    name = _user("role-holder")
    role_code = f"TB1A_{uuid4().hex[:8].upper()}_X" + "://U" + ":P@H"
    with SessionLocal() as db:
        role_id = db.execute(
            text(
                "INSERT INTO role (public_id, role_code, role_name, is_active) "
                "VALUES (:public_id, :role_code, :role_name, TRUE) RETURNING id"
            ),
            {"public_id": str(uuid4()), "role_code": role_code, "role_name": f"Sign-in test role {role_code}"},
        ).scalar_one()
        db.execute(
            text("INSERT INTO user_role (user_id, role_id) SELECT id, :role_id FROM app_user WHERE username = :username"),
            {"role_id": role_id, "username": name},
        )
        db.commit()
    try:
        boundary = _event_boundary()

        assert _login(name, "Fictional#Tester-2026").status_code == 200
        assert _attempt_rows(name) == [] and _stop(name) is None
        assert cli.main(["set-roles", "--username", name, "--role", "SALES_USER"]) == 0

        events = _events_since(boundary)
        assert [event["event_name"] for event in events] == ["UserLoginSucceeded", "UserRolesChanged"]
        assert all(_payload(event) == {"username_withheld": True} for event in events)
        assert not any(role_code in str(event) for event in events)
    finally:
        with SessionLocal() as db:
            db.execute(text("DELETE FROM user_role WHERE role_id = :role_id"), {"role_id": role_id})
            db.execute(text("DELETE FROM role WHERE id = :role_id"), {"role_id": role_id})
            db.commit()


def test_every_spelling_of_a_username_shares_its_count():
    name = _user("spelling")
    for spelling in (name.upper(), name, name.title(), name.upper()):
        assert _login(spelling, "Wrong#Guess123").status_code == 401
    assert _login(name.capitalize(), "Wrong#Guess123").status_code == 429
    assert _login(name, "Fictional#Tester-2026").status_code == 429


def test_a_burst_of_parallel_attempts_checks_no_more_passwords_than_the_limit():
    """Each attempt is counted, and committed, before its password is checked."""
    name = _name("burst")
    now = datetime.now(timezone.utc)
    attempts: list[throttle.Attempt] = []
    barrier = threading.Barrier(12)

    def one_attempt() -> None:
        with SessionLocal() as db:
            barrier.wait()
            attempt = throttle.register_attempt(db, name, now)
            db.commit()
            attempts.append(attempt)

    threads = [threading.Thread(target=one_attempt) for _ in range(12)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    checked = [attempt for attempt in attempts if attempt.stopped_until is None]
    assert len(attempts) == 12
    assert len(checked) == 5, "only the first five may go on to have their password checked"
    assert sum(attempt.stops_until is not None for attempt in checked) == 1


def test_pruning_never_waits_for_a_row_another_transaction_holds():
    """Pruning skips a row another transaction has locked rather than waiting for it."""
    held = _name("held")
    now = datetime.now(timezone.utc)
    _register(held, now - timedelta(minutes=30))

    with SessionLocal() as holder, SessionLocal() as db:
        holder.execute(
            text("SELECT 1 FROM sign_in_attempt WHERE username_digest = :digest FOR UPDATE"),
            {"digest": throttle.username_digest(holder, held)},
        )
        db.execute(text("SET LOCAL lock_timeout = '2s'"))
        throttle.prune(db, now)
        db.commit()
        holder.rollback()

    assert len(_attempt_rows(held)) == 1, "the held row was skipped, not removed"


def test_counting_stopping_and_clearing_one_name_never_wait_for_another_names_rows():
    """Every row of two other names - stale attempts, fresh ones, a stop - is held by another transaction. One name's
    five attempts, the stop they make and a success's clearing still complete at once: each touches its own name's
    rows only, under that name's lock, so sign-ins for two names can never wait for each other or deadlock."""
    mine, others = _name("own-rows"), [_name("other-a"), _name("other-b")]
    now = datetime.now(timezone.utc)
    # Written directly, not through the code under test, so the rows are there whatever that code does.
    with SessionLocal() as db:
        for other in others:
            for moment in (now - timedelta(minutes=30), now):
                db.execute(
                    text("INSERT INTO sign_in_attempt (username_digest, attempted_at) VALUES (:digest, :moment)"),
                    {"digest": throttle.username_digest(db, other), "moment": moment},
                )
        db.execute(
            text("INSERT INTO sign_in_stop (username_digest, locked_until) VALUES (:digest, :until)"),
            {"digest": throttle.username_digest(db, others[0]), "until": now + timedelta(minutes=10)},
        )
        db.commit()

    with SessionLocal() as holder, SessionLocal() as db:
        digests = [throttle.username_digest(holder, other) for other in others]
        holder.execute(text("SELECT 1 FROM sign_in_attempt WHERE username_digest = ANY(:digests) FOR UPDATE"), {"digests": digests})
        holder.execute(text("SELECT 1 FROM sign_in_stop WHERE username_digest = ANY(:digests) FOR UPDATE"), {"digests": digests})
        db.execute(text("SET LOCAL lock_timeout = '2s'"))
        attempts = [throttle.register_attempt(db, mine, now) for _ in range(5)]
        lifted = throttle.clear_attempts(db, attempts[0], now)
        db.commit()
        holder.rollback()

    assert attempts[-1].stops_until is not None and lifted is True


def test_concurrent_sign_ins_for_different_names_never_deadlock():
    """Twelve attempts for four names, each name with a stale attempt waiting to be pruned, all at once: every one is
    counted, none fails."""
    names = [_name(f"cross-{index}") for index in range(4)]
    now = datetime.now(timezone.utc)
    for name in names:
        _register(name, now - timedelta(minutes=30))
    errors: list[BaseException] = []
    barrier = threading.Barrier(12)

    def one_sign_in(name: str) -> None:
        try:
            with SessionLocal() as db:
                barrier.wait()
                throttle.prune(db, now)
                db.commit()
                throttle.register_attempt(db, name, now)
                db.commit()
        except BaseException as exc:  # noqa: BLE001 - any failure is the finding
            errors.append(exc)

    threads = [threading.Thread(target=one_sign_in, args=(names[index % 4],)) for index in range(12)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert errors == []
    assert sorted(len([r for r in _attempt_rows(name) if r["attempted_at"] == now]) for name in names) == [3, 3, 3, 3]


def test_a_stop_is_never_without_its_event_when_the_password_check_after_it_fails(monkeypatch):
    name = _user("fault-check")
    _four_wrong(name)
    boundary = _event_boundary()

    def broken(*args, **kwargs):
        raise RuntimeError("the password check failed")

    monkeypatch.setattr(identity_service, "verify_password", broken)
    response = failing_client.post("/api/auth/login", json={"username": name, "password": WRONG})

    assert response.status_code == 500
    assert _stop(name) is not None
    assert [event["event_name"] for event in _events_since(boundary)] == ["UserSignInLocked"]


def test_a_stop_is_never_without_its_event_when_the_attempts_own_event_fails(monkeypatch):
    name = _user("fault-failed-event")
    _four_wrong(name)
    boundary = _event_boundary()
    real = identity_routes.record_business_event

    def refuse_the_failure(db, **kwargs):
        if kwargs["event_name"] == "UserLoginFailed":
            raise RuntimeError("the event store refused it")
        return real(db, **kwargs)

    monkeypatch.setattr(identity_routes, "record_business_event", refuse_the_failure)
    response = failing_client.post("/api/auth/login", json={"username": name, "password": WRONG})

    assert response.status_code == 500
    assert _stop(name) is not None
    assert [event["event_name"] for event in _events_since(boundary)] == ["UserSignInLocked"]


def test_when_the_stops_event_cannot_be_written_nothing_of_that_attempt_is_kept(monkeypatch):
    name = _user("fault-stop-event")
    _four_wrong(name)
    boundary = _event_boundary()
    real = identity_service.record_business_event

    def refuse_the_stop(db, **kwargs):
        if kwargs["event_name"] == "UserSignInLocked":
            raise RuntimeError("the event store refused it")
        return real(db, **kwargs)

    monkeypatch.setattr(identity_service, "record_business_event", refuse_the_stop)
    response = failing_client.post("/api/auth/login", json={"username": name, "password": WRONG})

    assert response.status_code == 500
    assert _stop(name) is None and len(_attempt_rows(name)) == 4
    assert _events_since(boundary) == []
    monkeypatch.undo()
    assert _login(name, "Wrong#Guess123").status_code == 429


def test_the_stop_has_no_effect_on_another_username():
    stopped, other = _user("stopped-one"), _user("other-one")
    for _ in range(5):
        _login(stopped, "Wrong#Guess123")
    assert _login(other, "Fictional#Tester-2026").status_code == 200


def test_unlock_lifts_a_stop_early_and_says_when_there_was_none(credentials, capsys):
    name = _user("unlock")
    for _ in range(5):
        _login(name, "Wrong#Guess123")
    boundary = _event_boundary()

    assert cli.main(["unlock", "--username", name]) == 0
    assert f"{name} may sign in again." in capsys.readouterr().out
    assert _login(name, "Fictional#Tester-2026").status_code == 200

    assert cli.main(["unlock", "--username", name]) == 0
    assert "was not stopped from signing in; nothing changed" in capsys.readouterr().out
    unlocked = [event for event in _events_since(boundary) if event["event_name"] == "UserSignInUnlocked"]
    assert len(unlocked) == 1 and _payload(unlocked[0])["username"] == name


def test_unlock_before_the_limit_changes_nothing_and_keeps_the_count(capsys):
    name = _user("unlock-early")
    for _ in range(3):
        assert _login(name, "Wrong#Guess123").status_code == 401
    boundary = _event_boundary()

    assert cli.main(["unlock", "--username", name]) == 0

    assert "was not stopped from signing in; nothing changed" in capsys.readouterr().out
    assert [_login(name, "Wrong#Guess123").status_code for _ in range(2)] == [401, 429]
    assert not [event for event in _events_since(boundary) if event["event_name"] == "UserSignInUnlocked"]


# Ending earlier sign-ins -----------------------------------------------------------------------------------------


def test_a_password_reset_ends_every_earlier_sign_in(credentials, capsys):
    name = _name("reset")
    assert cli.main(["create", "--username", name, "--display-name", "Reset", "--role", "SALES_USER",
                     "--credentials-file", str(credentials)]) == 0
    first_password = [line.split("\t")[3] for line in credentials.read_text().splitlines() if name in line][-1]
    earlier = [_login(name, first_password).json()["access_token"] for _ in range(2)]
    assert all(_me(token).status_code == 200 for token in earlier)

    assert cli.main(["reset-password", "--username", name, "--credentials-file", str(credentials)]) == 0
    assert "Every sign-in made before this reset has ended." in capsys.readouterr().out

    for token in earlier:
        refused = _me(token)
        assert refused.status_code == 401
        assert refused.json()["detail"] == "This sign-in has ended. Sign in again."
    new_password = [line.split("\t")[3] for line in credentials.read_text().splitlines() if name in line][-1]
    assert _me(_login(name, new_password).json()["access_token"]).status_code == 200


def test_disabling_ends_sign_ins_so_enabling_again_does_not_bring_them_back():
    name = _user("disable")
    earlier = _login(name, "Fictional#Tester-2026").json()["access_token"]

    assert cli.main(["disable", "--username", name]) == 0
    assert _me(earlier).status_code == 401
    assert cli.main(["enable", "--username", name]) == 0

    assert _me(earlier).status_code == 401
    assert _me(_login(name, "Fictional#Tester-2026").json()["access_token"]).status_code == 200


def test_retiring_ends_sign_ins(monkeypatch):
    name = _user("retire")
    earlier = _login(name, "Fictional#Tester-2026").json()["access_token"]
    monkeypatch.setattr(service, "DEMO_USERNAMES", (name,))

    assert cli.main(["retire-demo-users"]) == 0
    with SessionLocal() as db:
        db.execute(text("UPDATE app_user SET is_active = TRUE WHERE username = :u"), {"u": name})
        db.commit()

    assert _me(earlier).status_code == 401


def test_end_sign_ins_ends_them_and_keeps_the_password(capsys):
    name = _user("end")
    earlier = _login(name, "Fictional#Tester-2026").json()["access_token"]
    boundary = _event_boundary()

    assert cli.main(["end-sign-ins", "--username", name]) == 0
    assert "its password is unchanged" in capsys.readouterr().out

    assert _me(earlier).status_code == 401
    assert _me(_login(name, "Fictional#Tester-2026").json()["access_token"]).status_code == 200
    ended = [event for event in _events_since(boundary) if event["event_name"] == "UserSignInsEnded"]
    assert len(ended) == 1 and _payload(ended[0])["username"] == name


def test_a_role_change_keeps_the_sign_in_and_applies_at_once():
    name = _user("roles")
    earlier = _login(name, "Fictional#Tester-2026").json()["access_token"]

    assert cli.main(["set-roles", "--username", name, "--role", "SALES_MANAGER"]) == 0

    me = _me(earlier)
    assert me.status_code == 200
    assert me.json()["role_codes"] == ["SALES_MANAGER"]


def test_accounts_already_disabled_when_the_change_is_deployed_do_not_bring_back_earlier_sign_ins():
    """Revision 20260908_0048 starts inactive accounts at 1: a token from before it counts as 0, so enabling such an
    account later does not bring that sign-in back. Active accounts start at 0 and keep theirs."""
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    migration = ScriptDirectory.from_config(Config("alembic.ini")).get_revision("20260908_0048").module
    assert "op.execute(INACTIVE_ACCOUNTS_START_ENDED)" in inspect.getsource(migration.upgrade)
    active, inactive = _user("deploy-active"), _user("deploy-inactive")
    legacy = {name: _legacy_token(name) for name in (active, inactive)}
    with SessionLocal() as db:
        # The migration's own statement, on these accounts as they stood before it: then rolled back, because it
        # touches every inactive account in this database.
        db.execute(text("UPDATE app_user SET is_active = FALSE WHERE username = :u"), {"u": inactive})
        db.execute(text(migration.INACTIVE_ACCOUNTS_START_ENDED))
        versions = dict(
            db.execute(
                text("SELECT username, token_version FROM app_user WHERE username IN (:a, :b)"),
                {"a": active, "b": inactive},
            ).all()
        )
        db.rollback()
    assert versions == {active: 0, inactive: 1}

    with SessionLocal() as db:
        db.execute(text("UPDATE app_user SET is_active = FALSE, token_version = 1 WHERE username = :u"), {"u": inactive})
        db.commit()
    assert cli.main(["enable", "--username", inactive]) == 0

    assert _me(legacy[inactive]).status_code == 401
    assert _me(legacy[active]).status_code == 200


def test_a_token_issued_before_this_change_works_until_the_account_ends_its_sign_ins():
    """Tokens from before revision 20260908_0048 carry no number; they are read as 0, the start of every account active
    when it ran, so the deploy signed no active account out - and the first reset or disable still ends them. (An
    account already inactive started at 1: the next test.)"""
    name = _user("pre-change")
    me = _me(_login(name, "Fictional#Tester-2026").json()["access_token"]).json()
    now = int(time.time())
    legacy = _signed_token(
        {"sub": name, "user_public_id": me["public_id"], "role_codes": ["SALES_USER"], "iat": now, "exp": now + 600}
    )
    assert _me(legacy).status_code == 200

    assert cli.main(["end-sign-ins", "--username", name]) == 0
    assert _me(legacy).status_code == 401


# The three safeguards ---------------------------------------------------------------------------------------------


def test_a_new_hash_uses_the_current_count_which_is_600000_outside_development_and_ci():
    from app.core.config import InsecureDefaultConfigurationError, Settings

    assert STANDARD_PASSWORD_HASH_ITERATIONS == 600_000
    # The field's own default, not a Settings built here: CI sets PASSWORD_HASH_ITERATIONS for the whole job.
    assert Settings.model_fields["password_hash_iterations"].default == 600_000, "the default"
    assert hash_password("Fictional#Tester-2026").split("$")[1] == str(password_iterations())
    with pytest.raises(InsecureDefaultConfigurationError, match="password_hash_iterations is below 600,000"):
        Settings(app_env="production", jwt_secret="s" * 48, password_hash_iterations=10_000)


def test_no_setting_may_hash_more_than_600000_times():
    """Round 8: a count above 600,000 would write hashes a later, lower setting could not use, and a huge one would
    hang every sign-in. Refused when the settings are built, in every environment, development included."""
    from app.core.config import Settings

    built = Settings(app_env="development", password_hash_iterations=STANDARD_PASSWORD_HASH_ITERATIONS)
    assert built.password_hash_iterations == 600_000
    for too_much in (STANDARD_PASSWORD_HASH_ITERATIONS + 1, 10**12):
        with pytest.raises(ValidationError):
            Settings(app_env="development", password_hash_iterations=too_much)


def test_every_hash_a_setting_can_write_stays_usable_when_the_setting_is_lowered(monkeypatch):
    """Round 8: a deploy with a lower count - a rollback, or an old backend still running beside a tool already on a
    new count - must not lock out anyone whose hash was written at a higher one. The most any setting writes is
    600,000, and that is accepted under any setting."""
    highest = _hash_with("Fictional#Tester-2026", STANDARD_PASSWORD_HASH_ITERATIONS)
    name = _user("lowered", password_hash=highest)
    monkeypatch.setattr(security, "password_iterations", lambda: 1_000)

    assert verify_password("Fictional#Tester-2026", highest) is True
    assert verify_password("Wrong#Guess-2026", highest) is False
    assert password_hash_needs_upgrade(highest) is False
    assert _login(name, "Fictional#Tester-2026").status_code == 200
    assert _stored_hash(name) == highest, "a hash with more rounds than the setting is kept, never downgraded"


def test_the_seed_keeps_a_demo_users_valid_older_hash_which_its_next_sign_in_upgrades(monkeypatch, capsys):
    """Round 8 corrected the records: the seed replaces a demo user's hash only when it no longer accepts the demo
    password. One hashed with fewer rounds still does, so it is kept, and upgraded at that user's next successful
    sign-in like anyone's - not when the backend starts."""
    demo = service.DemoUser(str(uuid4()), _name("seed-older"), "Demo stand-in", "SALES_USER")
    monkeypatch.setattr(service, "DEMO_USERS", (demo,))
    monkeypatch.setattr(service, "DEMO_USERNAMES", (demo.username,))
    assert cli.main(["seed-demo-users"]) == 0
    older = _hash_with(service.DEMO_PASSWORD, OLD_ITERATIONS)
    with SessionLocal() as db:
        db.execute(text("UPDATE app_user SET password_hash = :h WHERE username = :u"), {"h": older, "u": demo.username})
        db.commit()
    capsys.readouterr()

    assert cli.main(["seed-demo-users"]) == 0
    assert "already in place" in capsys.readouterr().out
    assert _stored_hash(demo.username) == older
    assert _login(demo.username, service.DEMO_PASSWORD).status_code == 200
    assert _stored_hash(demo.username).split("$")[1] == str(password_iterations())


def test_an_older_hash_is_upgraded_at_the_next_successful_sign_in_and_only_then():
    old = _hash_with("Fictional#Tester-2026", OLD_ITERATIONS)
    name = _user("upgrade", password_hash=old)
    with SessionLocal() as db:
        before = db.execute(
            text("SELECT updated_at, token_version FROM app_user WHERE username = :u"), {"u": name}
        ).one()

    assert _login(name, "Wrong#Guess123").status_code == 401
    assert _stored_hash(name) == old

    token = _login(name, "Fictional#Tester-2026").json()["access_token"]
    upgraded = _stored_hash(name)
    assert upgraded.split("$")[1] == str(password_iterations())
    assert not password_hash_needs_upgrade(upgraded)
    assert verify_password("Fictional#Tester-2026", upgraded)
    with SessionLocal() as db:
        after = db.execute(
            text("SELECT updated_at, token_version FROM app_user WHERE username = :u"), {"u": name}
        ).one()
    # Not a password change: the account's change time and its sign-ins are left alone.
    assert tuple(after) == tuple(before)
    assert _me(token).status_code == 200
    assert _login(name, "Fictional#Tester-2026").status_code == 200


def test_an_upgrade_never_overwrites_a_password_reset_made_in_the_meantime():
    old = _hash_with("Fictional#Tester-2026", OLD_ITERATIONS)
    name = _user("race", password_hash=old)
    reset = hash_password("Fresh@Password-2026")
    with SessionLocal() as db:
        db.execute(text("UPDATE app_user SET password_hash = :h WHERE username = :u"), {"h": reset, "u": name})
        user_id = db.execute(text("SELECT id FROM app_user WHERE username = :u"), {"u": name}).scalar_one()
        assert replace_password_hash(db, user_id, old, hash_password("Fictional#Tester-2026")) is False
        db.commit()
    assert _stored_hash(name) == reset


def test_every_wrong_credentials_refusal_costs_the_same_hashing_whether_or_not_the_account_exists(monkeypatch):
    """Every 401 "Invalid credentials." spends exactly password_iterations(). A stopped name's 429 checks no password at
    all, whoever it names, so it shows nothing either."""
    current = _user("current")
    old_hash = _user("old-hash", password_hash=_hash_with("Fictional#Tester-2026", OLD_ITERATIONS))
    disabled = _user("disabled")
    disabled_old_hash = _user("disabled-old", password_hash=_hash_with("Fictional#Tester-2026", OLD_ITERATIONS))
    no_password = _user("no-hash")
    with SessionLocal() as db:
        db.execute(text("UPDATE app_user SET is_active = FALSE WHERE username = :u"), {"u": disabled})
        db.execute(text("UPDATE app_user SET is_active = FALSE WHERE username = :u"), {"u": disabled_old_hash})
        db.execute(text("UPDATE app_user SET password_hash = NULL WHERE username = :u"), {"u": no_password})
        db.commit()

    spent: list[int] = []
    real = hashlib.pbkdf2_hmac

    def counted(name, password, salt, iterations, *args):
        spent.append(iterations)
        return real(name, password, salt, iterations, *args)

    monkeypatch.setattr(security.hashlib, "pbkdf2_hmac", counted)
    cases = {
        "an unknown username": (_name("unknown"), "Wrong#Guess123"),
        "a wrong password": (current, "Wrong#Guess123"),
        "a wrong password on an older hash": (old_hash, "Wrong#Guess123"),
        "a disabled account's right password": (disabled, "Fictional#Tester-2026"),
        "a disabled account's right password on an older hash": (disabled_old_hash, "Fictional#Tester-2026"),
        "an account with no password": (no_password, "Fictional#Tester-2026"),
    }
    for case, (username, password) in cases.items():
        spent.clear()
        assert _login(username, password).status_code == 401, case
        assert sum(spent) == password_iterations(), case


@pytest.mark.parametrize(
    "malformed",
    [
        "pbkdf2_sha256$600000$00$" + chr(0xE9) * 64,
        "pbkdf2_sha256$600000$00$abcd",
        "pbkdf2_sha256$600000$$" + "ab" * 32,
        "pbkdf2_sha256$600000$zz$" + "ab" * 32,
        "pbkdf2_sha256$0$00$" + "ab" * 32,
        "pbkdf2_sha256$60000000$00$" + "ab" * 32,
        f"pbkdf2_sha256${STANDARD_PASSWORD_HASH_ITERATIONS + 1}$00$" + "ab" * 32,
        f"pbkdf2_sha256${10 * STANDARD_PASSWORD_HASH_ITERATIONS}$00$" + "ab" * 32,
        "pbkdf2_sha256$abc$00$" + "ab" * 32,
        "bcrypt$600000$00$" + "ab" * 32,
        "not a hash at all",
    ],
)
def test_a_malformed_stored_hash_is_unusable_never_an_error(malformed, monkeypatch):
    """Only a hash this module could have written is checked: the algorithm, 1 to 600,000 iterations (round 7 refused
    ten times the count; round 8 bounded it at the most any setting can write), a non-empty hex salt and a 32-byte hex
    key. Anything else - a non-ASCII key made compare_digest raise, and the
    sign-in answer 500 - is refused after the stand-in's work, at sign-in and in the account tool's password checks."""
    name = _user("malformed-hash")
    with SessionLocal() as db:
        db.execute(text("UPDATE app_user SET password_hash = :h WHERE username = :u"), {"h": malformed, "u": name})
        db.commit()

    assert verify_password("Fictional#Tester-2026", malformed) is False
    assert password_hash_needs_upgrade(malformed) is False
    spent: list[int] = []
    real = hashlib.pbkdf2_hmac

    def counted(name_, password, salt, iterations, *args):
        spent.append(iterations)
        return real(name_, password, salt, iterations, *args)

    monkeypatch.setattr(security.hashlib, "pbkdf2_hmac", counted)
    assert _login(name, "Fictional#Tester-2026").status_code == 401
    assert sum(spent) == password_iterations()
    monkeypatch.undo()

    with SessionLocal() as db:
        assert name not in service.users_accepting_password(db, "Fictional#Tester-2026")


@pytest.mark.parametrize(
    "token, why",
    [
        ("é.a.b", "a non-ASCII character, which answered 500"),
        ("a.b.c", "an ordinary malformed token"),
        ("no-dots-at-all", "not three parts"),
    ],
)
def test_a_malformed_token_is_refused_as_not_signed_in(token, why):
    with pytest.raises(TokenError):
        decode_access_token(token)
    assert _me(token).status_code == 401, why


@pytest.mark.parametrize(
    "payload, why",
    [
        (["not", "an", "object"], "a list"),
        ({"sub": "x", "user_public_id": "y", "exp": "soon"}, "an expiry that is not a number"),
        ({"sub": "x", "user_public_id": "y", "exp": 4102444800, "ver": True}, "a version that is not a number"),
        ({"sub": "x", "user_public_id": "y", "exp": 4102444800, "ver": -1}, "a negative version"),
    ],
)
def test_a_signed_token_with_a_malformed_payload_is_refused_as_not_signed_in(payload, why):
    token = _signed_token(payload)
    with pytest.raises(TokenError):
        decode_access_token(token)
    assert _me(token).status_code == 401, why


@pytest.mark.parametrize(
    "body, why",
    [
        ({"username": "tb1a-nul" + chr(0) + "name", "password": WRONG}, "a NUL character in the username"),
        ({"username": "tb1a-surrogate", "password": WRONG + chr(0xD800)}, "a lone surrogate in the password"),
        ({"username": "tb1a-" + chr(0xD800) + "name", "password": WRONG}, "a lone surrogate in the username"),
    ],
)
def test_a_sign_in_holding_text_that_cannot_be_stored_is_refused_as_malformed_not_500(body, why):
    """PostgreSQL takes no NUL character and a lone surrogate is not UTF-8; each made the sign-in answer 500."""
    boundary = _event_boundary()
    with SessionLocal() as db:
        rows_before = db.execute(text("SELECT count(*) FROM sign_in_attempt")).scalar_one()

    # json.dumps escapes both as \u0000 and \ud800, as a browser's JSON would; JSON allows them, UTF-8 cannot carry the second.
    content = json.dumps(body).encode("ascii")
    response = client.post("/api/auth/login", content=content, headers={"Content-Type": "application/json"})

    assert response.status_code == 422, why
    assert _events_since(boundary) == [], "refused before anything is counted or recorded"
    with SessionLocal() as db:
        assert db.execute(text("SELECT count(*) FROM sign_in_attempt")).scalar_one() == rows_before


@pytest.mark.parametrize(
    "body, written",
    [
        (json.dumps({"username": 1.0, "password": WRONG}).replace("1.0", "1e400"), "inf"),
        (json.dumps({"username": float("-inf"), "password": WRONG}), "-inf"),
        (json.dumps({"username": float("nan"), "password": WRONG}), "nan"),
    ],
)
def test_the_422_answer_is_written_for_a_number_json_cannot_hold(body, written):
    """Python's JSON decoder reads 1e400 as infinity, and accepts Infinity and NaN; FastAPI's 422 repeats the input, and
    a non-finite number cannot be written as JSON, so the answer was a 500 (review round 12). It is repeated as its
    text."""
    refused = client.post("/api/auth/login", content=body.encode("ascii"), headers={"Content-Type": "application/json"})
    assert refused.status_code == 422
    [error] = refused.json()["detail"]
    assert error["loc"] == ["body", "username"] and error["input"] == written

    token = _login("admin1", "password").json()["access_token"]
    elsewhere = client.post(
        "/api/accounts",
        content=b'{"account_name": 1e400}',
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"},
    )
    assert elsewhere.status_code == 422
    assert any(item.get("input") == "inf" for item in elsewhere.json()["detail"])


@pytest.mark.parametrize(
    "body, content_type",
    [
        (b"\xff\xfe", "application/octet-stream"),
        (b"\xff", "text/plain"),
        (('{"username": ' + "[" * 3000 + "]" * 3000 + ', "password": ' + json.dumps(WRONG) + "}").encode(), "application/json"),
    ],
)
def test_the_422_answer_leaves_out_an_input_it_cannot_repeat(body, content_type):
    """Raw bytes that are not UTF-8, or a value nested too deeply to write, could not be repeated, so the answer was a
    500 (review round 13). Each error then keeps its type, location and message, and the inputs are left out."""
    refused = client.post("/api/auth/login", content=body, headers={"Content-Type": content_type})
    assert refused.status_code == 422
    detail = refused.json()["detail"]
    assert detail and all(set(error) == {"type", "loc", "msg"} for error in detail)
    assert detail[0]["loc"][0] == "body"

    token = _login("admin1", "password").json()["access_token"]
    elsewhere = client.post(
        "/api/accounts",
        content=b"\xff\xfe",
        headers={"Content-Type": "application/octet-stream", "Authorization": f"Bearer {token}"},
    )
    assert elsewhere.status_code == 422
    assert all("input" not in error for error in elsewhere.json()["detail"])


def test_the_422_answer_keeps_fastapis_shape_and_is_written_even_for_a_lone_surrogate_on_any_route():
    """FastAPI's 422 repeats the refused input; a lone surrogate could not be written as UTF-8, so the answer became a
    500. The application's handler writes the same body with non-ASCII escaped (app/core/errors.py)."""
    refused = client.post(
        "/api/auth/login",
        content=json.dumps({"username": "tb1a-shape", "password": WRONG + chr(0xD800)}).encode("ascii"),
        headers={"Content-Type": "application/json"},
    )
    assert refused.status_code == 422
    [error] = refused.json()["detail"]
    assert error["loc"] == ["body", "password"] and error["type"] == "string_unicode"
    assert error["input"] == WRONG + chr(0xD800)

    token = _login("admin1", "password").json()["access_token"]
    elsewhere = client.post(
        "/api/accounts",
        content=b'{"account_name": "Caf\\u00e9 \\ud800"}',
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"},
    )
    assert elsewhere.status_code == 422
    assert elsewhere.content.isascii()
    assert any(item.get("input") == "Caf" + chr(0xE9) + " " + chr(0xD800) for item in elsewhere.json()["detail"])


# Password rules ---------------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "password, problem",
    [
        ("Short#Pass1", "shorter than 12"),
        ("aaaaaaaaaaaaaaaa", "one character repeated"),
        ("Sales-Exec-01-Pass2026", "contains the username"),
        ("MyPassword2026x", "obvious"),
        ("QWERTY-is-long-enough", "obvious"),
        ("Pbl-Transport-2026", "obvious"),
        ("Admin@Company2026", "obvious"),
        ("x123456789012", "obvious"),
        ("x" * 201, "longer than 200"),
        ("Long-enough" + chr(0) + "-guess", "cannot be typed at sign-in"),
        ("Long-enough-guess" + chr(0xD800), "cannot be typed at sign-in"),
    ],
)
def test_a_password_that_breaks_a_rule_is_named_for_the_rule(password, problem):
    found = password_problem(password, "sales-exec-01")
    assert found is not None and problem in found
    assert password not in found


@pytest.mark.parametrize("password", ["Willow@Sienna904", "Fern@Mica123", "a long passphrase of plain words"])
def test_a_password_within_the_rules_is_accepted(password):
    assert password_problem(password, "uat-sales-01") is None


def test_every_password_the_tool_can_generate_meets_the_rules():
    """Two words of at least four letters, a symbol, three digits: at least 12 characters, and no word is obvious."""
    shortest = min(len(word) for word in PASSWORD_WORDS)
    assert 2 * shortest + 1 + 3 >= MIN_PASSWORD_LENGTH
    assert not [word for word in PASSWORD_WORDS if any(fragment in word.lower() for fragment in OBVIOUS_FRAGMENTS)]
    assert len(PASSWORD_SYMBOLS) and all(password_problem(generate_password(), "uat-sales-01") is None for _ in range(300))


def test_a_generated_password_that_happens_to_contain_the_username_is_drawn_again(monkeypatch):
    draws = iter(["Fern@Mica123", "Quartz@Topaz456"])
    monkeypatch.setattr(cli, "generate_password", lambda: next(draws))
    assert cli._new_password(from_stdin=False, username="fern") == "Quartz@Topaz456"

    monkeypatch.setattr(cli, "generate_password", lambda: "Fern@Mica123")
    with pytest.raises(credentials_module.CredentialsFileError, match="Choose one with --password-stdin"):
        cli._new_password(from_stdin=False, username="fern")


@pytest.mark.parametrize("weak", ["Short#Pass1", "Password@2026x", "PilotPbl#Sales1"])
def test_create_refuses_a_chosen_password_that_breaks_a_rule_before_the_database(monkeypatch, credentials, capsys, weak):
    name = _name("weak-create")
    monkeypatch.setattr("sys.stdin", io.StringIO(weak + chr(10)))

    assert cli.main(["create", "--username", name, "--display-name", "Weak", "--role", "SALES_USER",
                     "--credentials-file", str(credentials), "--password-stdin"]) == 2

    err = capsys.readouterr().err
    assert "That password cannot be used" in err and "12 to 200 characters" in err
    assert weak not in err
    assert not credentials.exists()
    with SessionLocal() as db:
        assert service.get_user(db, name) is None


def test_reset_refuses_a_chosen_password_that_breaks_a_rule_and_keeps_the_old_one(monkeypatch, credentials):
    name = _user("weak-reset")
    token = _login(name, "Fictional#Tester-2026").json()["access_token"]
    monkeypatch.setattr("sys.stdin", io.StringIO(f"{name}-2026" + chr(10)))

    assert cli.main(["reset-password", "--username", name, "--credentials-file", str(credentials),
                     "--password-stdin"]) == 2

    assert not credentials.exists()
    assert _login(name, "Fictional#Tester-2026").status_code == 200
    assert _me(token).status_code == 200, "a refused reset ends nothing"
