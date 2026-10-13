from __future__ import annotations

import base64
import json
import re
import unicodedata
from datetime import date, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.modules.events.errors import EventCredentialRefusedError
from app.modules.events.schemas import BusinessEventCreate, BusinessEventSummary

# A credential has no place in the event log, which nobody can edit afterwards ("Do not store secrets in event
# payloads", workflow-and-events.md). It is recognised by its shape, never by an English word: "Secretariat", "Under
# Secretary" and "token advance" are ordinary business text (TB-1 TB1-500). The shapes are a closed list, chosen for
# what this application handles; a secret with none of them - a password typed as plain text, an opaque API key under a
# neutral name - is not recognised, so code must still never put one into an event.
#
# Keys are chosen by code, and read word by word (split at separators and at a lower-to-upper case change). One grammar
# covers every credential name: a key names a credential when one of its words is a credential root or a run-together
# credential term followed by nothing or by one suffix of _COMPACT_SUFFIXES ("secret", "secrets", "CREDENTIALVALUE",
# "ACCESSTOKEN", "BACKUPCODES", "PASSWORDHASH" - but "secretariat" is not "secret" and a suffix); or when two of its
# words in a row are a credential pair, the second with nothing or a suffix ("api key", "api_keys", "backup_codes").
# "token" is a credential word everywhere but in one business construction: the earnest money of commercial practice -
# "token" first in the key, or after "prepaid", "paid", "received", "booking" or "earnest", and followed by "advance",
# "amount", "money" or "payment". "pin" (a postal PIN code) and "PWD" (Public Works Department) are deliberately not
# credential words. A credential-named key is refused whatever it holds but nothing (None), unless it is metadata about
# a credential holding the value its kind of metadata holds (see _is_credential_metadata). Every key is also checked as
# text, like a value.
_CREDENTIAL_ROOTS = ("password", "passwd", "passphrase", "secret", "jwt", "token", "otp", "credential")
_CREDENTIAL_TERMS = (
    "accesstoken", "refreshtoken", "authtoken", "bearertoken", "idtoken", "sessiontoken", "apitoken", "csrftoken",
    "apikey", "accesskey", "privatekey", "secretkey", "signingkey", "clientsecret", "recoverycode", "backupcode",
)
_COMPACT_SUFFIXES = ("", "s", "hash", "value", "values", "data", "material")
_CREDENTIAL_WORDS = frozenset(
    stem + suffix for stem in _CREDENTIAL_ROOTS + _CREDENTIAL_TERMS for suffix in _COMPACT_SUFFIXES
)
_CREDENTIAL_PAIR_STEMS = (
    ("api", "key"),
    ("access", "key"),
    ("private", "key"),
    ("secret", "key"),
    ("signing", "key"),
    ("recovery", "code"),
    ("backup", "code"),
)
_CREDENTIAL_KEY_PAIRS = frozenset(
    (first, second + suffix) for first, second in _CREDENTIAL_PAIR_STEMS for suffix in _COMPACT_SUFFIXES
)
_TOKEN_PAYMENT_WORDS = frozenset({"advance", "amount", "money", "payment"})
_TOKEN_BUSINESS_LEADS = frozenset({None, "prepaid", "paid", "received", "booking", "earnest"})
# Metadata about a credential holds none, so each kind holds only its own kind of value: a flag after "has"/"is" or
# before a word of _METADATA_FLAG_WORDS ("has_password", "password_reset"); a whole number - an integer, or digits as
# text - before a word of _METADATA_NUMBER_WORDS ("password_attempts", "token_version"); a flag or a date (ISO 8601,
# with or without a time) before a word of _METADATA_DATE_WORDS ("password_changed": "2026-10-08"). Anything else under
# such a key - other text, a list, a mapping - is refused like any credential-named key.
_METADATA_FIRST_WORDS = frozenset({"has", "is"})
_METADATA_FLAG_WORDS = frozenset({"reset", "required", "removed", "valid", "known", "set"})
_METADATA_NUMBER_WORDS = frozenset({"attempt", "attempts", "count", "version", "length", "age"})
_METADATA_DATE_WORDS = frozenset({"changed", "expired", "expires", "expiry"})
_ISO_DATE = re.compile(r"\d{4}-\d{2}-\d{2}(?:[T ]\d{2}:\d{2}(?::\d{2}(?:\.\d{1,9})?)?(?:Z|[+-]\d{2}:?\d{2})?)?")
# The owner's decision, 8 October 2026 (TB1-500, after nine review rounds): text is refused only for a credential that
# proves itself - its own structure says what it is - never for one guessed from the words around a value. An opaque
# value after "Bearer", "Token", "Digest" or in a cookie looks like any reference number or long word, and every rule
# that guessed from the words around it refused some ordinary sentence, so none is kept: an opaque token pasted into
# free text is not recognised, a limit the contract states. The application issues JSON Web Tokens, which prove
# themselves, and no code writes request headers into events.
#
# A key that is, as a whole, an Authorization header name holding Basic credentials - "Basic " and base64 that decodes
# to "user:password", however short or long - is refused; holding anything else ("Basic training for operators",
# "Board approval recorded") it is not.
_AUTHORIZATION_HEADER_KEYS = frozenset({("authorization",), ("proxy", "authorization")})
_AUTHORIZATION_BASIC = re.compile(r"\s*+basic\s++([A-Za-z0-9+/]++={0,2})(?![A-Za-z0-9+/=])", re.IGNORECASE)
# Text - a value anywhere in the payload, a key, or any of the event's text columns - is refused when it holds one of
# these self-proving formats. Each but the private-key block must start the text or follow a character that is not a
# letter or a digit. A crypt-style hash needs 20 or more hash characters after its prefix. The patterns are possessive
# or bounded by their own delimiters, so a long text costs time in proportion to its length.
_START = r"(?<![A-Za-z0-9])"
_CREDENTIAL_VALUE_SHAPES = (
    re.compile(r"-----BEGIN [A-Z ]*?PRIVATE KEY(?: BLOCK)?-----"),  # a private key
    # Stored password hashes, each in its complete encoding - an incomplete or malformed one is ordinary text: this
    # application's pbkdf2_sha256$iterations$salt$hash (app/core/security.py: hex salt, a 64-hex SHA-256 digest;
    # Django's form too: an alphanumeric salt, the digest as 43 base64 characters and "="), the iteration count never
    # zero; bcrypt ($2b$, a cost from 04 to 31, 53 characters); and the crypt family's MD5, SHA-256, SHA-512 and
    # yescrypt forms. Argon2's PHC string is read field by field instead (_holds_an_argon2_hash).
    re.compile(
        _START + r"pbkdf2_sha256\$[1-9]\d*+\$(?:[0-9a-f]{2,}+\$[0-9a-f]{64}(?![0-9A-Za-z])"
        r"|[A-Za-z0-9]++\$[A-Za-z0-9+/]{43}=(?![A-Za-z0-9+/=]))"
    ),
    re.compile(_START + r"\$2[abxy]\$(?:0[4-9]|[12]\d|3[01])\$[./A-Za-z0-9]{53}(?![./A-Za-z0-9])"),
    re.compile(_START + r"\$1\$[./A-Za-z0-9]{1,8}\$[./A-Za-z0-9]{22}(?![./A-Za-z0-9])"),
    re.compile(_START + r"\$5\$(?:rounds=[1-9]\d{3,8}\$)?[./A-Za-z0-9]{1,16}\$[./A-Za-z0-9]{43}(?![./A-Za-z0-9])"),
    re.compile(_START + r"\$6\$(?:rounds=[1-9]\d{3,8}\$)?[./A-Za-z0-9]{1,16}\$[./A-Za-z0-9]{86}(?![./A-Za-z0-9])"),
    # yescrypt: its parameters begin "j" (as libxcrypt writes them), then the salt and a 43-character hash.
    re.compile(_START + r"\$y\$j[./A-Za-z0-9]{2,}+\$[./A-Za-z0-9]++\$[./A-Za-z0-9]{43}(?![./A-Za-z0-9])"),
)
# An Authorization header with Basic credentials: refused only when its value really is base64 of "user:password", so
# "Authorization: basic training for operators" is not.
_BASIC_CREDENTIALS = re.compile(
    _START + r"authorization[\"']?\s*+[:=]\s*+[\"']?basic\s++([A-Za-z0-9+/]{2,}+={0,2})", re.IGNORECASE
)
# An address's authority ends at the first "/", "?", "#" or space after "://".
_AUTHORITY_END = re.compile(r"[/?#\s]")
# Candidates for a JSON Web Token: runs of base64url characters and dots, in which a token may start at the beginning
# or after a "_", "-" or "." ("jwt_eyJ..."). A header longer than 16,384 characters is not read: real headers,
# certificate chains included, are far shorter, and the bound keeps the cost of a long text in proportion to its length.
_DOTTED_RUN = re.compile(r"[A-Za-z0-9_.-]+")
# Where a token may start inside one dot-free part of a run: its beginning, and after the first and the last few "_" or
# "-" in it ("jwt_eyJ...", "x-y-eyJ..."). Trying every separator would decode the same part once per separator - time in
# the square of its length - so a token glued after more separators than this, with as many inside its own header, is
# not looked for (a stated limit).
_TOKEN_STARTS_PER_PART = 16
_MAX_JOSE_HEADER = 16384


def _key_words(key: str) -> tuple[str, ...]:
    """Words split at separators, at a lower-to-upper case change ("apiKey") and where an acronym meets a word
    ("DBPassword", "JWTToken"); a key all in capitals stays one word ("ACCESSTOKEN")."""
    split = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", key)
    return tuple(re.findall(r"[a-z0-9]+", re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", split).lower()))


def _names_a_credential(words: tuple[str, ...]) -> bool:
    for position, word in enumerate(words):
        following = words[position + 1] if position + 1 < len(words) else None
        preceding = words[position - 1] if position > 0 else None
        if word == "token" and following in _TOKEN_PAYMENT_WORDS and preceding in _TOKEN_BUSINESS_LEADS:
            continue
        if word in _CREDENTIAL_WORDS or (word, following) in _CREDENTIAL_KEY_PAIRS:
            return True
    return False


def _is_credential_metadata(words: tuple[str, ...], item: Any) -> bool:
    """Metadata about a credential, holding the kind of value that kind of metadata holds."""
    if not words:
        return False
    if words[0] in _METADATA_FIRST_WORDS or words[-1] in _METADATA_FLAG_WORDS:
        return isinstance(item, bool)
    if words[-1] in _METADATA_NUMBER_WORDS:
        return (isinstance(item, int) and not isinstance(item, bool)) or (
            isinstance(item, str) and item.isascii() and item.isdigit()
        )
    if words[-1] in _METADATA_DATE_WORDS:
        return isinstance(item, bool) or (isinstance(item, str) and _is_a_real_date(item))
    return False


def _is_a_real_date(text: str) -> bool:
    """An ISO 8601 date or date-time in the shape _ISO_DATE allows that is also a real one: no 13th month, no 99th
    minute, no offset past a day."""
    if _ISO_DATE.fullmatch(text) is None:
        return False
    try:
        (date.fromisoformat if len(text) == 10 else datetime.fromisoformat)(text)
    except ValueError:
        return False
    return True


def _decodes_to_user_and_password(encoded: str) -> bool:
    """Base64 (padding optional) of "user:password": a user name in UTF-8 text with no control character ("ü" too), a
    colon, then any bytes - a password need not be text. A word that merely decodes to bytes ("Basic training") has no
    such user name. A user name in an older single-byte encoding is not recognised: allowing any bytes would take
    ordinary numbers and codes after "Basic" ("1986") for credentials."""
    encoded = encoded.rstrip("=")
    try:
        decoded = base64.b64decode(encoded + "=" * (-len(encoded) % 4), validate=True)
        user = decoded.partition(b":")[0].decode("utf-8")
    except ValueError:  # not base64 (binascii.Error), or a user name that is not UTF-8 (UnicodeDecodeError)
        return False
    return b":" in decoded and bool(user) and not any(unicodedata.category(c).startswith("C") for c in user)


def _authorization_credential(item: str) -> bool:
    basic = _AUTHORIZATION_BASIC.match(item)
    return basic is not None and _decodes_to_user_and_password(basic.group(1))


def _header_credential(words: tuple[str, ...], item: Any) -> bool:
    """An Authorization-named key holding Basic credentials - as text, or in a list of values."""
    if isinstance(item, list):
        return any(_header_credential(words, value) for value in item)
    return isinstance(item, str) and words in _AUTHORIZATION_HEADER_KEYS and _authorization_credential(item)


def _is_jose_header(segment: str) -> bool:
    """A JSON Web Token's first part: base64url of a JSON object naming its algorithm ("alg")."""
    try:
        header = json.loads(base64.urlsafe_b64decode(segment + "=" * (-len(segment) % 4)))
    # Not base64, text or JSON. RecursionError, which JSON nested past about 5,000 levels raises, is caught as a defence.
    except (ValueError, RecursionError):
        return False
    algorithm = header.get("alg") if isinstance(header, dict) else None
    return isinstance(algorithm, str) and algorithm != ""


def _holds_a_json_web_token(value: str) -> bool:
    """A header followed by at least two more dots (the payload and the signature may be empty), the header decoding to
    a JOSE header, whatever its encoding begins with."""
    for run in _DOTTED_RUN.findall(value):
        dots = [index for index, character in enumerate(run) if character == "."]
        # Each part of the run before a dot that has at least two more dots after it may hold a header.
        for number, header_end in enumerate(dots[:-1]):
            part_start = dots[number - 1] + 1 if number else 0
            separators = [i + 1 for i in range(part_start, header_end) if run[i] in "_-"]
            starts = dict.fromkeys(
                [part_start] + separators[:_TOKEN_STARTS_PER_PART] + separators[-_TOKEN_STARTS_PER_PART:]
            )
            for start in starts:
                if 0 < header_end - start <= _MAX_JOSE_HEADER and _is_jose_header(run[start:header_end]):
                    return True
    return False


def _holds_basic_credentials(value: str) -> bool:
    return any(_decodes_to_user_and_password(match.group(1)) for match in _BASIC_CREDENTIALS.finditer(value))


def _holds_an_address_with_a_password(value: str) -> bool:
    """scheme://user:password@host - found by scanning, with no length limit on the user or the password. The scheme
    follows the URI grammar: the whole run of scheme characters before "://" is a letter, then letters, digits, "+",
    "-" or "." ("a+://" counts; "+://" and "9a://" do not)."""
    position = value.find("://")
    while position != -1:
        start = position
        while start > 0 and value[start - 1].isascii() and (value[start - 1].isalnum() or value[start - 1] in "+.-"):
            start -= 1
        if start < position and value[start].isascii() and value[start].isalpha():
            authority_start = position + 3
            end = _AUTHORITY_END.search(value, authority_start)
            authority = value[authority_start : end.start() if end else len(value)]
            if "@" in authority:
                user, separator, password = authority.rsplit("@", 1)[0].partition(":")
                if user and separator and password:
                    return True
        position = value.find("://", position + 3)
    return False


# Argon2's PHC string, read field by field (see _holds_an_argon2_hash).
_ARGON2 = re.compile(
    _START + r"\$argon2(?:id|i|d)\$(?:v=(?:16|19)\$)?m=([1-9]\d*+),t=[1-9]\d*+,p=([1-9]\d*+)"
    r"\$([A-Za-z0-9+/]++)\$([A-Za-z0-9+/]++)"
)


def _unpadded_base64(text: str) -> bytes | None:
    """The bytes of canonical unpadded base64, as the PHC format writes it; None for any other text."""
    if len(text) % 4 == 1:
        return None
    try:
        decoded = base64.b64decode(text + "=" * (-len(text) % 4), validate=True)
    except ValueError:
        return None
    return decoded if base64.b64encode(decoded).decode("ascii").rstrip("=") == text else None


def _holds_an_argon2_hash(value: str) -> bool:
    """An Argon2 hash its algorithm could have written: version 16 or 19, memory at least eight times the parallelism
    (memory up to 2**32 - 1, parallelism up to 2**24 - 1), time at least 1, a salt of 8 bytes or more and a hash of 4 or
    more, each canonical unpadded base64."""
    for match in _ARGON2.finditer(value):
        memory, parallelism, salt_text, hash_text = match.groups()
        if len(memory) > 10 or len(parallelism) > 8:
            continue
        salt, digest = _unpadded_base64(salt_text), _unpadded_base64(hash_text)
        if (
            8 * int(parallelism) <= int(memory) <= 2**32 - 1
            and int(parallelism) <= 2**24 - 1
            and salt is not None
            and len(salt) >= 8
            and digest is not None
            and len(digest) >= 4
        ):
            return True
    return False


def _looks_like_a_credential(value: str) -> bool:
    return (
        any(shape.search(value) for shape in _CREDENTIAL_VALUE_SHAPES)
        or _holds_an_argon2_hash(value)
        or _holds_basic_credentials(value)
        or _holds_an_address_with_a_password(value)
        or _holds_a_json_web_token(value)
    )


def _check_payload(value: Any, credential_keys: list[str], shaped: list[bool]) -> None:
    """Walk the whole stored payload, collecting both kinds of finding: credential-named keys that hold anything, and
    credential-shaped text in a key or a value or a header-name key holding its credential form. The caller decides which
    refusal they make, so the order of the walk never does."""
    if isinstance(value, dict):
        for key, item in value.items():
            words = _key_words(key)
            if _looks_like_a_credential(key) or _header_credential(words, item):
                shaped.append(True)
            if item is not None and _names_a_credential(words) and not _is_credential_metadata(words, item):
                credential_keys.append(key)
            _check_payload(item, credential_keys, shaped)
    elif isinstance(value, list):
        for item in value:
            _check_payload(item, credential_keys, shaped)
    elif isinstance(value, str) and _looks_like_a_credential(value):
        shaped.append(True)


def _payload_findings(payload_text: str) -> tuple[list[str], list[bool]]:
    credential_keys: list[str] = []
    shaped: list[bool] = []
    _check_payload(json.loads(payload_text), credential_keys, shaped)
    return credential_keys, shaped


def payload_is_storable(payload: dict[str, Any]) -> bool:
    """Whether the guard below lets `payload` into the event log - no credential-named key holding a value, no text
    shaped like a credential - for a caller that must withhold a payload rather than fail (TB-1 TB1-204 part a)."""
    credential_keys, shaped = _payload_findings(json.dumps(payload, sort_keys=True, default=str))
    return not credential_keys and not shaped


def check_event_text(event: BusinessEventCreate) -> None:
    """Every text column of the event - name, record, status, reason, remarks, correlation - follows the value rule."""
    for value in event.model_dump(exclude={"event_payload"}).values():
        if isinstance(value, str) and _looks_like_a_credential(value):
            raise EventCredentialRefusedError()


def _safe_payload_json(payload: dict[str, Any] | None) -> str | None:
    if payload is None:
        return None

    # Serialized once, and the check reads exactly what will be stored: an object turned into text by `default=str`
    # is checked as that text.
    payload_text = json.dumps(payload, sort_keys=True, default=str)
    credential_keys, shaped = _payload_findings(payload_text)
    if credential_keys:
        # A key is chosen by code, so this is a defect to fix, not something a user typed: a plain server error - first,
        # whatever the key's value also looks like.
        # The message names no key: a key may itself be a credential ("jwt_eyJ...").
        raise ValueError(
            f"Business event payload must not carry credentials: {len(credential_keys)} credential-named key(s) hold a value."
        )
    if shaped:
        raise EventCredentialRefusedError()
    return payload_text


def _row_to_summary(row: object) -> BusinessEventSummary:
    data = row._mapping
    payload_json = data["event_payload_json"]
    payload = json.loads(payload_json) if payload_json else None
    return BusinessEventSummary(
        public_id=data["public_id"],
        event_name=data["event_name"],
        source_module=data["source_module"],
        record_type=data["record_type"],
        record_public_id=data["record_public_id"],
        user_public_id=data["user_public_id"],
        event_timestamp=data["event_timestamp"],
        status_before=data["status_before"],
        status_after=data["status_after"],
        reason=data["reason"],
        remarks=data["remarks"],
        correlation_id=data["correlation_id"],
        event_payload=payload,
    )


def create_business_event(db: Session, event: BusinessEventCreate) -> BusinessEventSummary:
    public_id = str(uuid4())
    payload_json = _safe_payload_json(event.event_payload)
    check_event_text(event)

    db.execute(
        text(
            """
            INSERT INTO business_event
                (public_id, event_name, source_module, record_type, record_public_id,
                 user_public_id, status_before, status_after, reason, remarks,
                 correlation_id, event_payload_json)
            VALUES
                (:public_id, :event_name, :source_module, :record_type, :record_public_id,
                 :user_public_id, :status_before, :status_after, :reason, :remarks,
                 :correlation_id, :event_payload_json)
            """
        ),
        {
            "public_id": public_id,
            "event_name": event.event_name,
            "source_module": event.source_module,
            "record_type": event.record_type,
            "record_public_id": event.record_public_id,
            "user_public_id": event.user_public_id,
            "status_before": event.status_before,
            "status_after": event.status_after,
            "reason": event.reason,
            "remarks": event.remarks,
            "correlation_id": event.correlation_id,
            "event_payload_json": payload_json,
        },
    )

    row = db.execute(
        text(
            """
            SELECT
                public_id, event_name, source_module, record_type, record_public_id,
                user_public_id, event_timestamp, status_before, status_after, reason,
                remarks, correlation_id, event_payload_json
            FROM business_event
            WHERE public_id = :public_id
            LIMIT 1
            """
        ),
        {"public_id": public_id},
    ).one()
    return _row_to_summary(row)


def list_recent_business_events(
    db: Session,
    limit: int = 25,
    *,
    record_type: str | None = None,
    record_public_id: str | None = None,
) -> list[BusinessEventSummary]:
    safe_limit = max(1, min(limit, 100))
    filters: list[str] = []
    params: dict[str, Any] = {}

    if record_type:
        filters.append("record_type = :record_type")
        params["record_type"] = record_type
    if record_public_id:
        filters.append("record_public_id = :record_public_id")
        params["record_public_id"] = record_public_id

    where_clause = ("WHERE " + " AND ".join(filters)) if filters else ""

    rows = db.execute(
        text(
            f"""
            SELECT
                public_id, event_name, source_module, record_type, record_public_id,
                user_public_id, event_timestamp, status_before, status_after, reason,
                remarks, correlation_id, event_payload_json
            FROM business_event
            {where_clause}
            ORDER BY event_timestamp DESC, id DESC
            LIMIT {safe_limit}
            """
        ),
        params,
    ).all()
    return [_row_to_summary(row) for row in rows]