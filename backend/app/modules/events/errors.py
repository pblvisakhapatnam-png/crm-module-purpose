"""The event store's refusal of a credential a user typed (TB-1 TB1-500).

A save whose event would record text shaped like a password hash, an access token, a private key or an address with a
password in it is refused as a whole - nothing is saved - and the user is told why in plain words: a 422, not a server
error. The answer names no value. A key that names a credential is chosen by code, not typed by a user, so it stays a
plain ValueError and a server error: it is a defect to fix.
"""

from __future__ import annotations

from fastapi import Request, status
from fastapi.responses import JSONResponse

REFUSAL_MESSAGE = (
    "This was not saved: some of the text looks like a password, an access token or a private key, which must never "
    "be recorded. Remove it and try again."
)


class EventCredentialRefusedError(ValueError):
    """The event a save would record holds text shaped like a credential."""

    def __init__(self) -> None:
        super().__init__(REFUSAL_MESSAGE)


def handle_event_credential_refused(request: Request, exc: EventCredentialRefusedError) -> JSONResponse:
    return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content={"detail": REFUSAL_MESSAGE})
