"""A database error that escapes a request, logged without the error's text (TB-1 TB1-503).

The text of a database error is not safe to log. The engine hides a failed statement's bound values
(`hide_parameters`, app/core/database.py), but PostgreSQL's DETAIL line travels in the same message:
a unique violation repeats the duplicated key - a GSTIN, whose characters 3 to 12 are the holder's
PAN - and a NOT NULL or CHECK violation prints the whole failing row. Logs may carry safe identifiers
and references, not restricted payloads (docs/agent/architecture/DATA_CLASSIFICATION_AND_HANDLING.md).

So such an error is answered here with the same plain 500 the server gave before, and logged by what
identifies it without carrying a value: its class and SQLSTATE, the table, constraint and column
PostgreSQL names, the route's template rather than its URL, a reference for this occurrence and the
application code it passed through. Never str(exc), and never the exception chain, which repeats it.

Registered for SQLAlchemyError rather than Exception: Starlette re-raises an error a handler for
Exception has answered, so the server would log its traceback anyway. Other unexpected errors, and
returning the reference to the user, are CS-09's and CS-06's (docs/agent/tb-1/).

Also here, since TB-1 TB1-204 part a: FastAPI's 422 answer to a refused request, unchanged but for its
encoding, so a request holding text UTF-8 cannot carry is answered 422 rather than 500.
"""

from __future__ import annotations

import json
import logging
import math
import traceback
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, PlainTextResponse
from sqlalchemy.exc import DBAPIError, SQLAlchemyError

logger = logging.getLogger("app.errors")

_APP_ROOT = Path(__file__).resolve().parents[1]

# The diagnostic fields that name a schema object, never a value.
_NAMED_FIELDS = (("table", "table_name"), ("constraint", "constraint_name"), ("column", "column_name"))


def _application_code_path(exc: BaseException) -> str:
    frames = [
        f"{Path(frame.filename).relative_to(_APP_ROOT).as_posix()}:{frame.lineno} {frame.name}"
        for frame in traceback.extract_tb(exc.__traceback__)
        if Path(frame.filename).is_relative_to(_APP_ROOT)
    ]
    return " > ".join(frames) or "-"


def database_error_fields(exc: SQLAlchemyError) -> str:
    """What identifies a database error without carrying a value: its class and SQLSTATE, the table, constraint and
    column PostgreSQL names, and the application code it passed through. A module that answers such an error itself,
    as Commercial Offers answers a duplicate two requests made at once (CS-05c), logs it with these too."""
    driver_error = exc.orig if isinstance(exc, DBAPIError) else None
    diag = getattr(driver_error, "diag", None)
    parts = [
        f"error={type(exc).__name__}",
        f"driver_error={type(driver_error).__name__ if driver_error is not None else '-'}",
        f"sqlstate={getattr(diag, 'sqlstate', None) or '-'}",
        *(f"{label}={getattr(diag, field, None) or '-'}" for label, field in _NAMED_FIELDS),
        f"at={_application_code_path(exc)}",
    ]
    return " ".join(parts)


def database_error_log_line(exc: SQLAlchemyError, *, method: str, route: str, reference: str) -> str:
    parts = [f"reference={reference}", f"method={method}", f"route={route}", database_error_fields(exc)]
    return "Database error in a request: " + " ".join(parts)


def handle_database_error(request: Request, exc: SQLAlchemyError) -> PlainTextResponse:
    route = request.scope.get("route")
    logger.error(
        database_error_log_line(
            exc,
            method=request.method,
            route=getattr(route, "path", None) or "-",
            reference=str(uuid4()),
        )
    )
    return PlainTextResponse("Internal Server Error", status_code=500)


class _AsciiJSONResponse(JSONResponse):
    """JSON with every non-ASCII character escaped, so any text a request held can be written back."""

    def render(self, content: Any) -> bytes:
        return json.dumps(content, ensure_ascii=True, allow_nan=False, indent=None, separators=(",", ":")).encode("ascii")


def _finite(value: Any) -> Any:
    """`value` with every number JSON cannot hold - Python's decoder reads 1e400 as infinity, and accepts NaN - as its
    text ("inf", "-inf", "nan")."""
    if isinstance(value, float) and not math.isfinite(value):
        return str(value)
    if isinstance(value, dict):
        return {key: _finite(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_finite(item) for item in value]
    return value


# What every validation error carries and can always be written: its kind, where it is and what it says.
_ALWAYS_WRITABLE_ERROR_KEYS = ("type", "loc", "msg")


def handle_request_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    """FastAPI's own 422 answer - the same body - written so that it can always be sent.

    The standard answer repeats the refused input, and a lone surrogate, which JSON allows and UTF-8 cannot carry, made
    writing it fail: the request answered 500 instead of 422, on any route (found with TB-1 TB1-204 part a, on the
    sign-in). Escaping every non-ASCII character keeps the same JSON; a number JSON cannot hold is repeated as its text
    (review round 12). Any other input that cannot be repeated - raw bytes that are not UTF-8, a value nested too deeply
    to write (review round 13), or whatever else - leaves the inputs out: each error keeps its type, location and
    message, so the answer is still FastAPI's 422.
    """
    errors = exc.errors()
    try:
        return _AsciiJSONResponse(status_code=422, content={"detail": _finite(jsonable_encoder(errors))})
    except (ValueError, TypeError, RecursionError):
        written = [{key: error[key] for key in _ALWAYS_WRITABLE_ERROR_KEYS if key in error} for error in errors]
        return _AsciiJSONResponse(status_code=422, content={"detail": jsonable_encoder(written)})
