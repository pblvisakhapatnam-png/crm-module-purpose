"""Tests for the TE-2C test-token helper (tooling/smoke_data/auth_tokens.py).

This exercises tooling, not a CRM business rule, so it lives alongside the other harness tests
rather than in a module suite (see test_smoke_data_audit_events.py for the sibling pattern this
file follows). It proves the boundary this helper is required to hold:

- APP_ENV must be EXPLICITLY present in the process environment and equal to a permitted value;
  an unset APP_ENV is never treated as "development" (app.core.config.Settings defaulted to
  "development" until TB-1 TB1-204 part d, 7 October 2026; it now refuses a missing APP_ENV
  itself, and this helper's own check remains);
- the helper is fixed to the readonly1 identity, with no caller-supplied username parameter;
- issued tokens use the short TE-2C expiry, not the application's normal 480-minute session
  duration;
- a missing or inactive readonly1 identity is refused;
- issuing a token creates no business_event.

Deliberately narrow: this does not re-test general JWT signing/verification (see test_auth.py)
or the real /api/auth/login route's own behaviour, which are unchanged by this module.
"""

from __future__ import annotations

import os

import pytest
from sqlalchemy import text

from app.core.database import SessionLocal
from app.core.security import decode_access_token
from tooling.smoke_data.auth_tokens import (
    TEST_TOKEN_EXPIRES_MINUTES,
    TEST_TOKEN_USERNAME,
    TestTokenError,
    issue_test_bearer_token,
)


class _FakeSettings:
    """Minimal stand-in for app.core.config.Settings, exposing only .app_env."""

    def __init__(self, app_env: str) -> None:
        self.app_env = app_env


def _business_event_max_id() -> int:
    with SessionLocal() as db:
        return int(db.execute(text("SELECT COALESCE(MAX(id), 0) FROM business_event")).scalar_one())


def test_missing_app_env_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    """An APP_ENV that is entirely absent from the process environment must be refused, not
    silently treated as 'development'. This is the exact gap an earlier version of this helper
    had: it read app.core.config.Settings.app_env, whose own field then defaulted to 'development'
    (until TB-1 TB1-204 part d), so a genuinely unset APP_ENV passed the guard undetected."""
    monkeypatch.delenv("APP_ENV", raising=False)

    with pytest.raises(TestTokenError, match="APP_ENV is not set"):
        issue_test_bearer_token()


def test_production_app_env_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")

    with pytest.raises(TestTokenError, match="not one of the permitted"):
        issue_test_bearer_token()


def test_unknown_app_env_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "staging")

    with pytest.raises(TestTokenError, match="not one of the permitted"):
        issue_test_bearer_token()


def test_development_app_env_is_permitted(monkeypatch: pytest.MonkeyPatch) -> None:
    """APP_ENV=development, with the application's own resolved settings agreeing, must issue a
    token for the fixed readonly1 identity. get_settings is monkeypatched (rather than relying on
    whatever the real process happens to be configured with) so this test is deterministic
    regardless of the actual local/CI environment's real APP_ENV value."""
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setattr(
        "tooling.smoke_data.auth_tokens.get_settings",
        lambda: _FakeSettings(app_env="development"),
    )

    token = issue_test_bearer_token()

    assert token
    payload = decode_access_token(token)
    assert payload["sub"] == TEST_TOKEN_USERNAME


def test_ci_app_env_is_permitted(monkeypatch: pytest.MonkeyPatch) -> None:
    """Same as the development case, for the other permitted value, 'ci' (what
    .github/workflows/te-2ci-validation.yml's compose-e2e job writes into its ephemeral .env)."""
    monkeypatch.setenv("APP_ENV", "ci")
    monkeypatch.setattr(
        "tooling.smoke_data.auth_tokens.get_settings",
        lambda: _FakeSettings(app_env="ci"),
    )

    token = issue_test_bearer_token()

    assert token
    payload = decode_access_token(token)
    assert payload["sub"] == TEST_TOKEN_USERNAME


def test_mismatched_explicit_env_and_settings_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    """The secondary consistency check: an explicit, permitted process-environment APP_ENV that
    disagrees with the application's own resolved settings.app_env must be refused rather than
    trusted, even though this should not normally be reachable in practice."""
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setattr(
        "tooling.smoke_data.auth_tokens.get_settings",
        lambda: _FakeSettings(app_env="ci"),
    )

    with pytest.raises(TestTokenError, match="does not match"):
        issue_test_bearer_token()


def test_helper_has_no_username_parameter() -> None:
    """Structural proof, not merely a convention: the function signature itself carries no
    parameter a caller could use to request a token for any identity other than the fixed one."""
    import inspect

    signature = inspect.signature(issue_test_bearer_token)
    assert signature.parameters == {}
    assert TEST_TOKEN_USERNAME == "readonly1"


def test_token_expiry_is_the_short_te2c_duration(monkeypatch: pytest.MonkeyPatch) -> None:
    """Must be materially shorter than the application's normal 480-minute session, and exactly
    the documented TEST_TOKEN_EXPIRES_MINUTES -- not merely "shorter than 480" by accident."""
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setattr(
        "tooling.smoke_data.auth_tokens.get_settings",
        lambda: _FakeSettings(app_env="development"),
    )

    token = issue_test_bearer_token()
    payload = decode_access_token(token)

    actual_lifetime_seconds = payload["exp"] - payload["iat"]
    assert actual_lifetime_seconds == TEST_TOKEN_EXPIRES_MINUTES * 60
    assert TEST_TOKEN_EXPIRES_MINUTES < 480


def test_missing_identity_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setattr(
        "tooling.smoke_data.auth_tokens.get_settings",
        lambda: _FakeSettings(app_env="development"),
    )
    monkeypatch.setattr(
        "tooling.smoke_data.auth_tokens.get_user_with_roles_by_username",
        lambda db, username: None,
    )

    with pytest.raises(TestTokenError, match="No active local user"):
        issue_test_bearer_token()


def test_inactive_identity_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setattr(
        "tooling.smoke_data.auth_tokens.get_settings",
        lambda: _FakeSettings(app_env="development"),
    )
    monkeypatch.setattr(
        "tooling.smoke_data.auth_tokens.get_user_with_roles_by_username",
        lambda db, username: {
            "username": TEST_TOKEN_USERNAME,
            "public_id": "00000000-0000-0000-0000-000000000000",
            "is_active": False,
            "role_codes": [],
        },
    )

    with pytest.raises(TestTokenError, match="No active local user"):
        issue_test_bearer_token()


def test_issuing_a_token_creates_no_business_event(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setattr(
        "tooling.smoke_data.auth_tokens.get_settings",
        lambda: _FakeSettings(app_env="development"),
    )

    before = _business_event_max_id()
    token = issue_test_bearer_token()
    after = _business_event_max_id()

    assert token
    assert after == before


def test_app_env_is_read_from_process_environment_not_cached_settings_default() -> None:
    """Direct proof that os.environ, not the application's already-loaded settings, is what this
    module reads first: with APP_ENV genuinely absent from the real process environment (not just
    monkeypatched away), the guard must refuse, although the cached settings were loaded while it
    was present and still hold a development value."""
    original = os.environ.pop("APP_ENV", None)
    try:
        with pytest.raises(TestTokenError, match="APP_ENV is not set"):
            issue_test_bearer_token()
    finally:
        if original is not None:
            os.environ["APP_ENV"] = original
