"""The one replay rule for a create that carries a request key (TB-1 finding TB1-102 part b, corrective package
CS-06's early step, October 2026). Resource Assignments built it first (8A core, independent review round 1,
8A-R1-002); Equipment Reference's models and kit, and Resource Requirements, now follow it.

A form makes one key when it opens and sends it with each save. What the key's first save made is stored with that
request's fingerprint. Another save carrying the key is then either the same request - the same fields sent with the
same values - and is answered with what the first made, flagged `replayed`, recording nothing; or any other request,
which is refused (409) rather than answered with a record it did not ask for. MCF-001: a retry or repeated submission
has no duplicate business effect; the API conventions: a duplicate key returns "the original compatible result".
"""

from __future__ import annotations

import hashlib
import json
from uuid import UUID

from pydantic import BaseModel

REQUEST_KEY_FIELD = "create_request_key"


def request_fingerprint(payload: BaseModel, *, acts_on: UUID | str | None = None) -> str:
    """The request as sent, with the record it acts on, hashed: 64 hexadecimal digits of SHA-256. Only the fields sent
    count, so leaving one out and sending it empty differ; the key itself is left out. Stored fingerprints were made
    this exact way, so a change here would refuse the retry of every request made before it."""
    sent = payload.model_dump(mode="json", exclude_unset=True, exclude={REQUEST_KEY_FIELD})
    body = json.dumps({"acts_on": str(acts_on) if acts_on else None, "request": sent}, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def is_same_request(stored_fingerprint: str | None, fingerprint: str) -> bool:
    """Whether the key's first request is this one. A key stored without a fingerprint - its record made before its
    module kept one - cannot be compared, so it is never taken for this request: its reuse is refused, never replayed."""
    return stored_fingerprint is not None and stored_fingerprint == fingerprint
