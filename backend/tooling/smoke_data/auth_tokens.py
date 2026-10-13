"""Issue a short-lived bearer token for the fixed local readonly1 seed identity, without
creating a login audit event.

TE-2C's local timing-baseline tooling needs to measure a real authenticated HTTP request, but
must not accumulate a genuine login audit trail every time it runs (see
docs/agent/technical-enablement/TE_2C_MIGRATED_FOUNDATION_VERIFICATION.md). The real
`POST /api/auth/login` route always writes a `UserLoginSucceeded` business_event, by design --
that is correct behaviour for a real login and must not change.

This module reuses the exact identity lookup and token-signing functions the real login route
uses (app.modules.identity.repository.get_user_with_roles_by_username,
app.core.security.create_access_token) so a token issued this way is valid and indistinguishable
in shape from one issued by a real login -- it simply skips the HTTP round trip and the
business_event that route writes. It does not add a new authentication mechanism, does not
weaken password checking for the real login path, and is not reachable through any API route.

This is deliberately NARROW, not a general-purpose "impersonate any user" tool:

- There is no username parameter. The only identity this module will ever issue a token for is
  the fixed TEST_TOKEN_USERNAME constant (readonly1), never a caller-supplied value. An earlier
  version of this module accepted an arbitrary --username; that was independently reviewed as
  too broad (passwordless bearer-token creation for any active username) and removed.
- Issuance requires APP_ENV to be EXPLICITLY PRESENT in the process environment (read from
  os.environ by this module itself -- see the explicit-presence note below) and equal to one of
  _ALLOWED_APP_ENVIRONMENTS, a narrower list than the application's own development values, so
  this cannot issue a token in a misconfigured, unset, or production-pointed environment.
- Tokens are short-lived (TEST_TOKEN_EXPIRES_MINUTES), not the normal long-lived login session
  duration, since this exists only to cover the span of one timing-baseline run.

EXPLICIT-PRESENCE NOTE. Until 7 October 2026 app.core.config.Settings defaulted app_env to
"development" when the variable was unset, so get_settings().app_env alone could not tell "unset"
from "development"; this module was corrected once for exactly that, and reads
os.environ.get("APP_ENV") directly. Since TB-1 TB1-204 part d (7 October 2026) Settings has no
default and itself refuses a missing or blank APP_ENV, so the application - and the import of this
module, whose database session loads the settings - stops before anything is issued. This module's
own check is kept as an independent, narrower boundary: it requires the variable in the process
environment itself (not merely in a .env file the settings may also read) and allows only
"development" and "ci". As a secondary consistency check, the explicit value is compared against
the resolved get_settings().app_env; a mismatch is refused rather than trusted.

This check exists only in this narrow tooling module, layered on top of, not in place of, the
application's own configuration check.

This is NOT the same kind of trust boundary as backend/tooling/smoke_data/actors.py. That module
resolves a seeded username to a `public_id` for direct, in-process service-layer calls -- it never
produces anything that could be replayed as an HTTP bearer credential. This module does produce a
real, valid HTTP bearer token, which is a materially different and more sensitive capability, and
is scoped much more narrowly (one fixed username, a short expiry, an explicit environment gate) in
recognition of that difference.

PRINTING CONTRACT, stated precisely (do not read more into this than what is written): the CLI
wrapper around this function (backend/tooling/smoke_data/cli.py, "issue-test-token") intentionally
writes exactly the returned token to stdout -- that is its entire purpose as a command a caller
can capture. This module itself never writes the token to stderr, to a log, or into any
surrounding human-readable diagnostic text; every error path raises TestTokenError with a message
that never contains the token (because no token has been generated yet on any error path in this
function). What a *caller* of the CLI does with that captured stdout is that caller's own
responsibility -- see scripts/te-2c-timing-baseline.ps1 for how the TE-2C timing script captures
it and never displays or echoes it.

Testing/tooling code only. Never imported by app.main and not reachable through any public API
route. Adds no HTTP route.
"""

from __future__ import annotations

import os

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.core.security import create_access_token
from app.modules.identity.repository import get_user_with_roles_by_username

# The only identity this module will ever issue a token for. Not a parameter, not configurable
# from the CLI -- narrowing this to a single fixed value is the point.
TEST_TOKEN_USERNAME = "readonly1"

# Short enough that a token cannot outlive one timing-baseline invocation by any meaningful
# margin, unlike the application's normal JWT_EXPIRES_MINUTES (480 by default).
TEST_TOKEN_EXPIRES_MINUTES = 5

# The exact, explicit APP_ENV values this repository's own configuration already uses for
# non-production contexts: "development" is the Compose/.env.example default, "ci" is what
# .github/workflows/te-2ci-validation.yml's compose-e2e job writes into its ephemeral .env.
# Anything else -- including an ENTIRELY UNSET APP_ENV, "production", a typo, or a value this
# module does not recognise -- is refused rather than guessed at. See the explicit-presence note
# in this module's own docstring for why this is checked via os.environ directly as well as
# through the application's settings.
_ALLOWED_APP_ENVIRONMENTS = frozenset({"development", "ci"})


class TestTokenError(RuntimeError):
    """Raised when a bearer token cannot be issued."""


def issue_test_bearer_token() -> str:
    """Return a short-lived bearer token for the fixed local readonly1 seed identity.

    Read-only: no row is created, updated or deleted, and no business_event is written.

    Refuses to run unless APP_ENV is EXPLICITLY PRESENT in the process environment (an unset
    APP_ENV is refused, never silently treated as "development") and equal to one of
    _ALLOWED_APP_ENVIRONMENTS, and refuses if the fixed readonly1 identity does not exist or is
    not active.
    """
    explicit_app_env = os.environ.get("APP_ENV")
    if explicit_app_env is None:
        raise TestTokenError(
            "Refusing to issue a test token: APP_ENV is not set in the process environment. "
            f"This tool requires APP_ENV to be explicitly present and equal to one of "
            f"{sorted(_ALLOWED_APP_ENVIRONMENTS)!r}; an unset value is never treated as "
            "'development'."
        )
    if explicit_app_env not in _ALLOWED_APP_ENVIRONMENTS:
        raise TestTokenError(
            f"Refusing to issue a test token: APP_ENV={explicit_app_env!r} is not one of the "
            f"permitted local development/test values {sorted(_ALLOWED_APP_ENVIRONMENTS)!r}."
        )

    settings = get_settings()
    if settings.app_env != explicit_app_env:
        raise TestTokenError(
            f"Refusing to issue a test token: the process environment's APP_ENV "
            f"({explicit_app_env!r}) does not match the application's resolved "
            f"settings.app_env ({settings.app_env!r}). Refusing to proceed on an inconsistent "
            "environment signal."
        )

    with SessionLocal() as db:
        user = get_user_with_roles_by_username(db, TEST_TOKEN_USERNAME)

    if not user or not user.get("is_active"):
        raise TestTokenError(f"No active local user named {TEST_TOKEN_USERNAME!r} was found.")

    return create_access_token(
        subject=str(user["username"]),
        user_public_id=str(user["public_id"]),
        role_codes=[str(code) for code in user.get("role_codes", [])],
        token_version=int(user["token_version"]),
        expires_minutes=TEST_TOKEN_EXPIRES_MINUTES,
    )
