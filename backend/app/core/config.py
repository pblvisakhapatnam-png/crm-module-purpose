from functools import lru_cache

from pydantic import Field, model_validator
from sqlalchemy.engine import make_url
from pydantic_settings import BaseSettings, SettingsConfigDict

# Environments treated as non-production for the secret guard below. Anything else -
# including an unrecognised value - is treated as production and fails closed.
DEVELOPMENT_APP_ENVS = frozenset({"development", "dev", "local", "test", "ci"})

# Values shipped in `.env.example` purely so a developer can start the stack. They are public
# by definition: anyone with the repository knows them.
PLACEHOLDER_JWT_SECRET = "change-this-in-real-use"
PLACEHOLDER_DATABASE_PASSWORD = "ChangeThisStrongPassword123!"

# OWASP's current figure for PBKDF2-HMAC-SHA256 (TB-1 TB1-204 part a): what every environment but development and CI
# uses, and the most any may set. Those two may set fewer (`PASSWORD_HASH_ITERATIONS`), because the test suite signs
# in so many times that 600,000 a sign-in took it past CI's time limit (the owner's decision, 8 October 2026). As no
# setting can write more, every stored hash is usable under any setting (`security._parse_password_hash`), so changing
# it - a rollback, two deploys overlapping - never locks anyone out. Raising the work factor is a change to this
# number in code: older hashes are then upgraded at each person's next sign-in. Never lower it here: hashes above it
# would become unusable.
STANDARD_PASSWORD_HASH_ITERATIONS = 600_000


class InsecureDefaultConfigurationError(RuntimeError):
    """Raised at startup when the configured secrets are unsafe outside development."""


class MissingAppEnvironmentError(InsecureDefaultConfigurationError):
    """Raised at startup when APP_ENV is not set (TB-1 TB1-204 part d).

    An absent APP_ENV used to mean development, which accepts the published placeholder secrets.
    Every environment now names itself.
    """


def database_url_password(database_url: str) -> str | None:
    """Return the password the driver will actually use from a SQLAlchemy URL, if any.

    Parsed with SQLAlchemy's own `make_url`, the same parser the connection builder in
    `app.core.database` uses, so the guard sees exactly what the driver will see.

    Two places can carry a password, and a naive `urlsplit(...).password` reads only the first:

    - user info, `postgresql+psycopg://user:secret@host/db`;
    - a query parameter, `...?password=secret`, which SQLAlchemy passes through to the DBAPI
      and which therefore **takes precedence** over any user-info password.

    Checking only user info let the shipped placeholder through in a URL that carried it as a
    query parameter - including one whose user-info password looked like a real secret.
    """
    raw = database_url.strip()
    if not raw:
        return None
    try:
        url = make_url(raw)
    except Exception:
        # An unparseable URL is not this guard's problem; the database layer rejects it loudly.
        return None

    query_password = url.query.get("password")
    if isinstance(query_password, (tuple, list)):  # SQLAlchemy allows repeated query keys
        query_password = query_password[-1] if query_password else None
    if query_password:
        return str(query_password)
    return url.password


class Settings(BaseSettings):
    # No default: a missing or blank APP_ENV is refused below rather than read as development.
    app_env: str = ""
    backend_port: int = 8000

    # PostgreSQL is the frozen production database (ADR-028). `database_url` is the single
    # source of truth for the connection; the discrete postgres_* fields below only supply the
    # default when DATABASE_URL is not set, and are not consulted once it is.
    database_url: str = ""

    postgres_host: str = "db"
    postgres_port: int = 5432
    postgres_db: str = "pbl_crm_hiring"
    postgres_user: str = "pbl_app"
    postgres_password: str = PLACEHOLDER_DATABASE_PASSWORD

    jwt_secret: str = PLACEHOLDER_JWT_SECRET
    jwt_expires_minutes: int = 480

    # The repeated-wrong-password stop's numbers are the owner's decision, fixed in app.modules.identity.throttle, not
    # settings: no configuration can weaken it (TB-1 TB1-204 part a, review round 9).
    password_hash_iterations: int = Field(
        default=STANDARD_PASSWORD_HASH_ITERATIONS, ge=1, le=STANDARD_PASSWORD_HASH_ITERATIONS
    )

    # Document Storage Foundation (Slice 9C). "local" is the only provider today; the value is
    # configuration rather than a hard-coded import so a future provider (SharePoint) is added
    # by registering it in app.modules.documents.storage.get_storage_provider, not by changing
    # every caller. document_storage_root backs a named Docker volume in Compose so files
    # survive restarts and image rebuilds - see docker-compose.yml.
    document_storage_provider: str = "local"
    document_storage_root: str = "/app/document-store"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def is_development_environment(self) -> bool:
        return self.app_env.strip().lower() in DEVELOPMENT_APP_ENVS

    @property
    def effective_database_password(self) -> str | None:
        """The password actually used to connect, or None when none is configured.

        DATABASE_URL is authoritative when set: the discrete postgres_* fields are then ignored
        entirely, so the branch is on whether a URL is *configured*, not on whether parsing
        happened to find a password in it. A configured URL carrying no password is a legitimate
        production setup - libpq can supply credentials from a service file, .pgpass, or an
        external/IAM mechanism - and must not fall back to the ignored discrete field.
        """
        if self.database_url.strip():
            return database_url_password(self.database_url)
        return self.postgres_password

    @model_validator(mode="after")
    def _refuse_unsafe_secrets(self) -> "Settings":
        """Fail closed on absent or publicly-known secrets outside development.

        Two distinct problems are checked, because they are different failures:

        - **Absent.** A blank or whitespace-only `jwt_secret` is not a weak secret, it is no
          secret: the HMAC key becomes trivial and anyone can forge a token for any user and
          role. This is not an entropy policy, which remains out of scope.
        - **Publicly known.** A secret still equal to the value shipped in `.env.example`.
          For the database password this is checked against the *effective* password, so the
          placeholder cannot slip through embedded in DATABASE_URL.

        Development is exempt so the documented local setup keeps working unchanged. An
        unrecognised app_env is treated as production, so a typo fails closed rather than open,
        and a missing one is refused outright (TB-1 TB1-204 part d): it used to mean development,
        so a deployment that left out both APP_ENV and JWT_SECRET signed tokens with the
        published placeholder.
        """
        if not self.app_env.strip():
            raise MissingAppEnvironmentError(
                "Refusing to start: APP_ENV is not set. Set it explicitly - development (or ci) for a "
                "local or CI stack, uat for a hosted pilot, production for production. A missing APP_ENV "
                "is never assumed to be development."
            )
        if self.is_development_environment:
            return self

        problems: list[str] = []

        if self.password_hash_iterations < STANDARD_PASSWORD_HASH_ITERATIONS:
            problems.append(
                f"password_hash_iterations is below {STANDARD_PASSWORD_HASH_ITERATIONS:,}, which only development and CI "
                "may use"
            )
        if not self.jwt_secret.strip():
            problems.append("jwt_secret is blank, so authentication tokens would be trivially forgeable")
        elif self.jwt_secret == PLACEHOLDER_JWT_SECRET:
            problems.append("jwt_secret still holds the public placeholder value from .env.example")

        effective_password = self.effective_database_password
        if effective_password is not None and effective_password == PLACEHOLDER_DATABASE_PASSWORD:
            source = "DATABASE_URL" if self.database_url.strip() else "postgres_password"
            problems.append(
                f"the database password supplied through {source} still holds the public "
                "placeholder value from .env.example"
            )

        if problems:
            raise InsecureDefaultConfigurationError(
                f"Refusing to start with APP_ENV={self.app_env!r}: "
                + "; ".join(problems)
                + ". Set real values through the environment. (Configured values are never logged.)"
            )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
