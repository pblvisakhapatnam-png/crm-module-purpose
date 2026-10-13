from __future__ import annotations

import re
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

_UUID_RE = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)


def is_uuid_like(value: object) -> bool:
    """Shared by the manifest and the cleanup ids, so both agree on what an id may look like."""
    return isinstance(value, str) and bool(_UUID_RE.match(value))


MANIFEST_VERSION = 1
RUN_ID_PREFIX = "te1"
DATA_TAG_PREFIX = "TE1-SMOKE"


def new_run_id() -> str:
    return f"{RUN_ID_PREFIX}-{uuid.uuid4().hex[:8]}"


def data_tag(run_id: str) -> str:
    """A distinctive, human-readable prefix stamped onto every created record's name/title."""
    return f"{DATA_TAG_PREFIX}-{run_id}"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def is_valid_run_id(run_id: object) -> bool:
    if not isinstance(run_id, str) or not run_id:
        return False
    if not run_id.startswith(f"{RUN_ID_PREFIX}-"):
        return False
    suffix = run_id[len(RUN_ID_PREFIX) + 1 :]
    return len(suffix) >= 4 and all(ch in "0123456789abcdef" for ch in suffix.lower())


@dataclass
class Manifest:
    manifest_version: int
    run_id: str
    scenario: str
    created_at: str
    actor: dict[str, str]
    records: dict[str, Any]
    urls: dict[str, str]
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ManifestValidationError(ValueError):
    """Raised when a manifest dict does not look like a genuine TE-1 smoke-data manifest."""


def validate_manifest_dict(data: Any) -> None:
    """Defensive shape/version check run before any cleanup touches the database.

    This intentionally checks more than a loose run-id prefix match: it requires the
    full expected top-level shape so a malformed or unrelated JSON file is rejected
    before any DELETE is attempted.
    """
    if not isinstance(data, dict):
        raise ManifestValidationError("Manifest must be a JSON object.")

    required_keys = {"manifest_version", "run_id", "scenario", "created_at", "records"}
    missing = required_keys - data.keys()
    if missing:
        raise ManifestValidationError(f"Manifest is missing required keys: {sorted(missing)}")

    if data.get("manifest_version") != MANIFEST_VERSION:
        raise ManifestValidationError(
            f"Unsupported manifest_version {data.get('manifest_version')!r}; "
            f"this harness only understands version {MANIFEST_VERSION}."
        )

    run_id = data.get("run_id")
    if not is_valid_run_id(run_id):
        raise ManifestValidationError(f"Manifest run_id is missing or malformed: {run_id!r}")

    if not isinstance(data.get("scenario"), str) or not data["scenario"]:
        raise ManifestValidationError("Manifest 'scenario' must be a non-empty string.")

    if not isinstance(data.get("records"), dict) or not data["records"]:
        raise ManifestValidationError("Manifest 'records' must be a non-empty object.")
