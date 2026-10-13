"""TB-1 TB1-500 (corrective package CS-02): the event store refuses credentials by their shape, not by English words.

Before, any event payload whose JSON text held "password", "token" or "secret" anywhere was refused with an unhandled
ValueError, so a Lead for "... Secretariat", a contact "Under Secretary" or a reason naming a "token advance" could not
be saved at all (500, nothing stored). Now a key is refused only when it names a credential and holds text, and a value -
in the payload, the reason or the remarks - only when it has a credential's machine shape. A value refused that way is a
422 with a plain message, and nothing is saved.

The credential samples are assembled from pieces at run time, so the repository's own secret scanner
(scripts/check_tracked_secrets.py) does not take this file for a leak.
"""

from __future__ import annotations

import base64
import json
import time
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.core.database import SessionLocal
from app.main import app
from app.modules.events import repository as events_repository
from app.modules.events.errors import REFUSAL_MESSAGE, EventCredentialRefusedError
from app.modules.events.repository import _looks_like_a_credential, _safe_payload_json, check_event_text
from app.modules.events.schemas import BusinessEventCreate
from app.modules.events.service import record_business_event

client = TestClient(app)

BUSINESS_TEXT = (
    "Gujarat State Secretariat (Sachivalaya)",
    "MAHARASHTRA MANTRALAYA SECRETARIAT",
    "Under Secretary (Works)",
    "Letter to the Secretary, PWD",
    "token advance of Rs 10,000 received",
    "Crawler crane for the new Secretariat building",
    "password reset requested by the customer",
    "Bearer of this letter is our site engineer",
    "Bearer AUTH-LETTER-2026-0001 may collect the documents",
    "Authorization: basic training for new operators",
    "Authorization: Bearer representative may collect the documents",
    "Authorization: Bearer representative, may collect the documents",
    "Authorization: Bearer representative; please release the equipment",
    "https://www.pbltransport.cloud/enquiry",
)


def _base64url(text: str) -> str:
    return base64.urlsafe_b64encode(text.encode()).decode().rstrip("=")


def _jwt_shaped() -> str:
    # A signed token as this application issues them: a JOSE header, a payload and a signature.
    return _base64url('{"alg":"HS256","typ":"JWT"}') + "." + _base64url('{"sub":"1","exp":1}') + "." + "c" * 43


def _jwt_with_spaced_header() -> str:
    # Legal whitespace before the header object: its encoding does not begin "eyJ".
    return _base64url(' {"alg":"HS256","typ":"JWT"}') + "." + _base64url('{"sub":"1"}') + "." + "s" * 43


def _bcrypt_hash() -> str:
    return "$2" + "b$12$" + "a" * 53


def _private_key_header() -> str:
    return "-----BEGIN " + "RSA PRIV" + "ATE KEY-----"


def _bearer() -> str:
    return "Authorization: " + "Bear" + "er " + "z" * 24


def _basic_header() -> str:
    return "Authorization: " + "Bas" + "ic " + base64.b64encode(("pbl_app" + ":" + "hunter" + "2").encode()).decode()


def _short_unsigned_jwt() -> str:
    # {"alg":"none"} . {} . (no signature): a valid compact token with a three-character payload.
    return "ey" + "JhbGciOiJub25lIn0" + "." + "e30" + "."


def _stored_password_hash() -> str:
    # Complete but short (a 4-byte salt), so it fits the 100-character text columns whole.
    return "pbkdf2" + "_sha256$600000$" + "ab" * 4 + "$" + "cd" * 32


def _address_with_password() -> str:
    return "postgresql" + "://pbl_app:" + "hunter" + "2@db:5432/pbl"


CREDENTIAL_SHAPED = (
    _jwt_shaped,
    _short_unsigned_jwt,
    _jwt_with_spaced_header,
    _private_key_header,
    _basic_header,
    _stored_password_hash,
    _bcrypt_hash,
    _address_with_password,
)
TEXT_COLUMNS = ("event_name", "source_module", "record_type", "status_before", "status_after", "reason", "remarks", "correlation_id")


def _event(**text_columns: str) -> BusinessEventCreate:
    return BusinessEventCreate(**{"event_name": "Tb1500Probe", "source_module": "tests", **text_columns})


@pytest.mark.parametrize("value", BUSINESS_TEXT)
def test_business_text_is_accepted_in_a_payload_and_every_text_column(value: str) -> None:
    payload = {"company_name": value, "nested": {"selection_reason": value}, "lines": [{"scope_description": value}]}
    assert json.loads(_safe_payload_json(payload)) == payload
    check_event_text(_event(reason=value, remarks=value[:1000], status_before=value[:100], correlation_id=value[:100]))


@pytest.mark.parametrize(
    "payload",
    [
        {"password": "x1"},
        {"new_password": "x1"},
        {"password_hash": "x1"},
        {"access_token": "x1"},
        {"refreshToken": "x1"},
        {"api_key": "x1"},
        {"clientSecret": "x1"},
        {"outer": {"jwt": "x1"}},
        {"items": [{"private_key": "x1"}]},
        {"secret": {"value": "x1"}},
        {"access_token_value": "x1"},
        {"outer": [{"api_key_value": "x1"}]},
        {"private_key_material": "x1"},
        {"ACCESSTOKEN": "x1"},
        {"ACCESSTOKENVALUE": "x1"},
        {"PASSWORDHASH": "x1"},
        {"token": "x1"},
        {"access_token_amount": "x1"},
        {"outer": {"refresh_token_amount": "x1"}},
        {"items": [{"apiTokenAmount": "x1"}]},
        {"session_token_payment": "x1"},
        {"oauth_token_amount": "x1"},
        {"outer": [{"authorizationTokenPayment": "x1"}]},
        {"otp": "123456"},
        {"otp": 123456},
        {"outer": [{"access_token": 123456}]},
        {"password": True},
        {"credentials": "opaque-api-key-material"},
        {"outer": {"credential": "opaque-value"}},
        {"items": [{"recovery_codes": ["a1", "b2"]}]},
        {"RECOVERYCODES": "a1"},
        # An acronym before a word (review round 10).
        {"DBPassword": "opaque-material"},
        {"outer": {"JWTToken": "opaque-material"}},
        {"items": [{"APISecret": "opaque-material"}]},
        # Plural and run-together names, by the same grammar as every credential root and term (review round 6).
        {"secrets": "opaque-material"},
        {"secretValue": "opaque-material"},
        {"CREDENTIALVALUE": "opaque-material"},
        {"BACKUPCODES": ["R7K4-P9Q2"]},
        {"outer": {"backup_codes": ["R7K4-P9Q2"]}},
        {"items": [{"api_keys": "opaque-material"}]},
        {"otps": ["123456"]},
        {"tokens": "opaque-material"},
        # Metadata keys holding something that is not their kind of value.
        {"has_recovery_codes": ["R7K4-P9Q2"]},
        {"password_reset": {"new": "opaque-material"}},
        {"outer": {"password_reset": "opaque-material"}},
        {"items": [{"token_version": "v2-opaque-material"}]},
        {"password_changed": "opaque-material"},
        {"is_password_set": "yes"},
        {"password_attempts": [3]},
        # Review round 16: a date or time that does not exist is not date metadata.
        {"password_changed": "2026-13-40"},
        {"outer": {"token_expiry": "2026-10-08" + "T99:99:00+99:99"}},
    ],
)
def test_a_key_named_like_a_credential_holding_content_is_refused(payload: dict) -> None:
    with pytest.raises(ValueError, match="must not carry credentials") as caught:
        _safe_payload_json(payload)
    # A key is chosen by code, so this is a defect to fix, not a user's mistake: not the 422 kind.
    assert not isinstance(caught.value, EventCredentialRefusedError)


@pytest.mark.parametrize(
    "payload",
    [
        {"password_reset": True},
        {"password_attempts": 3},
        {"api_key": None},
        {"token_version": 2},
        {"token_advance_amount": "10000"},
        {"token_amount": "5000"},
        {"prepaid_token_amount": "5000"},
        {"secretariat_name": "Sachivalaya"},
        {"client_secretariat_name": {"name": "Sachivalaya"}},
        {"clientSecretariatName": "Sachivalaya"},
        {"username_known": False},
        {"authorization_letter_reference": "AL-2026-14"},
        {"pin_code": "560001"},
        {"pwd_division_name": "Roads and Buildings"},
        {"token_version": "3"},
        {"has_password": True},
        {"password_changed": "2026-10-08"},
        {"clientsecretariat_name": "Sachivalaya"},
        {"authorization": "Board approval recorded"},
        {"outer": [{"Proxy-Authorization": "pending"}]},
        {"cookie": "chocolate"},
        # Metadata holding its own kind of value, and words that only begin like a credential.
        {"password_changed": "2026-10-08" + "T10:15:00+05:30"},
        {"token_expires": "2026-10-08" + "T10:15:00Z"},
        {"password_expired": False},
        {"has_recovery_codes": True},
        {"otp_attempts": 2},
        {"outer": [{"password_reset": False}]},
        {"secretary_name": "Under Secretary"},
        {"secretarial_staff": "2"},
        {"tokenization_mode": "none"},
        {"passwordless_sign_in": True},
        {"APIVersion": "2"},
        {"HTTPStatus": 200},
        # An Authorization-named key holding business wording, scheme word and all.
        {"Authorization": "Basic training for operators"},
        {"outer": {"Proxy-Authorization": "Basic training"}},
        {"items": [{"authorization": "Token amount acknowledged"}]},
        {"Authorization": "Token acknowledgement"},
        {"Authorization": "Digest of approvals for the board"},
        {"outer": [{"authorization": "Bearer of this letter may collect the documents"}]},
        # Bearer prose whose first word is eight characters or more (review round 7).
        {"Authorization": "Bearer representative may collect the documents"},
        {"outer": {"Proxy-Authorization": "Bearer representative may collect"}},
        {"items": [{"authorization": "Bearer representative of the contractor"}]},
        {"Authorization": "Bearer representative, may collect the documents"},
        {"outer": [{"authorization": "Bearer representative; please release the equipment"}]},
        # A cookie header whose every pair is short (review round 8).
        {"Cookie": "theme=light; lang=en"},
    ],
)
def test_a_flag_a_count_or_a_business_key_is_accepted(payload: dict) -> None:
    assert json.loads(_safe_payload_json(payload)) == payload


@pytest.mark.parametrize(
    "payload",
    [
        {"outer": [{"Proxy-Authorization": "Bas" + "ic " + base64.b64encode(b"u:p").decode() + "AAAAAAAA"}]},
        # Basic credentials however short, padded or not, at the top level, nested and in lists (review round 6).
        {"Authorization": "Bas" + "ic " + base64.b64encode(b'u:p').decode()},
        {"Authorization": "Bas" + "ic " + base64.b64encode(b'a:').decode().rstrip("=")},
        {"headers": {"Authorization": "Bas" + "ic " + base64.b64encode(b'u:p').decode()}},
        {"requests": [{"Proxy-Authorization": "Bas" + "ic " + base64.b64encode(b'a:').decode().rstrip("=")}]},
        {"Authorization": ["Bas" + "ic " + base64.b64encode(b'u:p').decode()]},
        # A password that is not text (review round 10): padded, unpadded, nested and in a list.
        {"Authorization": "Bas" + "ic " + base64.b64encode(b"u:" + bytes([0xFF])).decode()},
        {"headers": {"Authorization": "Bas" + "ic " + base64.b64encode(b"user:" + bytes([0xFF, 0xFE])).decode().rstrip("=")}},
        {"requests": [{"Proxy-Authorization": ["Bas" + "ic " + base64.b64encode(b"u:" + bytes([0x80])).decode()]}]},
        # A user name that is not ASCII (review round 11): padded, unpadded, nested and in a list.
        {"Authorization": "Bas" + "ic " + base64.b64encode("ü:p".encode()).decode()},
        {"headers": {"Proxy-Authorization": "Bas" + "ic " + base64.b64encode("Jürgen:p".encode()).decode().rstrip("=")}},
        {"requests": [{"Authorization": ["Bas" + "ic " + base64.b64encode("ü:p".encode()).decode()]}]},
    ],
)
def test_an_authorization_key_holding_basic_credentials_is_refused(payload: dict) -> None:
    with pytest.raises(EventCredentialRefusedError):
        _safe_payload_json(payload)


def _long_basic() -> str:
    # Base64 of "u:" and 4,000 characters: 5,336 encoded characters, past any 4,096-character limit.
    return "Bas" + "ic " + base64.b64encode(b"u:" + b"p" * 4000).decode()


def _basic_of_length_4096() -> str:
    # 3,072 bytes encode to exactly 4,096 characters.
    return "Bas" + "ic " + base64.b64encode(b"u:" + b"p" * 3070).decode()


@pytest.mark.parametrize(
    "make",
    [_long_basic, _basic_of_length_4096],
)
def test_a_basic_value_has_no_length_limit(make) -> None:
    # Review round 7: at the top level, nested and in a list.
    value = make()
    for payload in ({"Authorization": value}, {"headers": {"Proxy-Authorization": value}}, {"requests": [{"authorization": value}]}):
        with pytest.raises(EventCredentialRefusedError):
            _safe_payload_json(payload)


def test_a_long_basic_credential_is_refused_in_text() -> None:
    with pytest.raises(EventCredentialRefusedError):
        _safe_payload_json({"note": "Authorization: " + _long_basic()})


@pytest.mark.parametrize(
    "payload",
    [
        # The owner's decision, 8 October 2026 (review round 9): an opaque value is not guessed from the words around
        # it, so none of these is refused - the stated limit. Each would have needed a rule that refused some ordinary
        # sentence too ("Bearer representative, may collect", "Digest of approvals; username = reviewer").
        {"note": "Authorization: Bear" + "er " + "z" * 24},
        {"note": "headers = {'Authorization': 'Bear" + "er " + "z" * 24 + "'}"},
        {"Authorization": "Bear" + "er " + "z" * 24},
        {"Authorization": "Tok" + "en " + "ab12" * 4},
        {"headers": {"Proxy-Authorization": "Dig" + 'est username="u", realm="r", nonce="n", response="' + "c" * 32 + '"'}},
        {"requests": [{"Cookie": "theme=light; session=" + "a" * 20}]},
        {"Set-Cookie": "sid=" + "b" * 20 + "; HttpOnly"},
        # And the ordinary wording those rules refused.
        {"Authorization": "Digest of approvals; username = reviewer"},
        {"outer": [{"authorization": "Digest of approvals; response = pending"}]},
        {"note": "(Authorization: Bearer representative)"},
    ],
)
def test_an_opaque_value_is_not_guessed_from_the_words_around_it(payload: dict) -> None:
    assert json.loads(_safe_payload_json(payload)) == payload


@pytest.mark.parametrize(
    "payload",
    [
        {"password": _jwt_shaped()},
        {"outer": {"api_key": _bearer()}},
        {"items": [{"secret": _private_key_header()}]},
        {_jwt_shaped(): "x", "token": "opaque-material"},
        {"Authorization": "Bear" + "er " + "z" * 24, "nested": [{"password": "opaque-material"}]},
    ],
)
def test_a_credential_named_key_is_the_plain_error_whatever_its_value_looks_like(payload: dict) -> None:
    # Review round 7: a key is chosen by code, so the defect's plain ValueError comes first, never the 422 kind.
    with pytest.raises(ValueError, match="must not carry credentials") as caught:
        _safe_payload_json(payload)
    assert not isinstance(caught.value, EventCredentialRefusedError)


def test_a_long_private_key_label_and_a_long_iteration_count_are_still_found() -> None:
    # Review round 8: no shape is cut off at a length.
    with pytest.raises(EventCredentialRefusedError):
        _safe_payload_json({"note": "-----BEG" + "IN " + "A" * 50 + " PRIVATE KEY-----"})
    with pytest.raises(EventCredentialRefusedError):
        _safe_payload_json({"note": "pbkdf2" + "_sha256$" + "1" * 12 + "$" + "ab" * 16 + "$" + "cd" * 32})


def test_a_basic_credential_whose_password_is_not_text_is_refused_in_text() -> None:
    with pytest.raises(EventCredentialRefusedError):
        _safe_payload_json({"note": "Authorization: " + "Bas" + "ic " + base64.b64encode(b"u:" + bytes([0xFF])).decode()})


def test_a_basic_credential_with_a_non_ascii_user_is_refused_in_text() -> None:
    with pytest.raises(EventCredentialRefusedError):
        _safe_payload_json({"note": "Authorization: " + "Bas" + "ic " + base64.b64encode("ü:p".encode()).decode()})
    with pytest.raises(EventCredentialRefusedError):
        check_event_text(_event(remarks="Authorization: " + "Bas" + "ic " + base64.b64encode("ü:p".encode()).decode()))


def test_a_basic_user_name_that_is_not_utf8_is_not_recognised() -> None:
    # The stated limit (review round 11): allowing any bytes would take numbers and codes after "Basic" ("1986").
    payload = {"Authorization": "Bas" + "ic " + base64.b64encode(bytes([0xFF]) + b":p").decode()}
    assert json.loads(_safe_payload_json(payload)) == payload
    assert json.loads(_safe_payload_json({"Authorization": "Basic 1986"})) == {"Authorization": "Basic 1986"}


@pytest.mark.parametrize("scheme", ["a+", "a-", "a.", "postgresql+psycopg"])
def test_an_address_whose_scheme_ends_in_punctuation_is_refused(scheme: str) -> None:
    # Review round 11: the scheme follows the URI grammar.
    address = scheme + "://u:" + "p" * 8 + "@db/pbl"
    for payload in ({"note": address}, {"outer": [{"note": "see " + address}]}, {address: "x"}):
        with pytest.raises(EventCredentialRefusedError):
            _safe_payload_json(payload)
    with pytest.raises(EventCredentialRefusedError):
        check_event_text(_event(remarks=address))


@pytest.mark.parametrize("text_value", ["+://u:p@host", "9a://u:p@host", ".a://u:p@host", "-x://u:p@host"])
def test_an_address_without_a_valid_scheme_is_not_one(text_value: str) -> None:
    # Review round 12: the whole scheme must begin with a letter, not merely contain one.
    for payload in ({"note": text_value}, {"outer": [{"note": "see " + text_value}]}):
        assert json.loads(_safe_payload_json(payload)) == payload
    check_event_text(_event(remarks=text_value))


def test_the_plain_error_names_no_key() -> None:
    # Review round 10: a key may itself be a credential, so the message never repeats one.
    key = "jwt_" + _jwt_shaped()
    with pytest.raises(ValueError) as caught:
        _safe_payload_json({key: "x"})
    assert not isinstance(caught.value, EventCredentialRefusedError)
    assert _jwt_shaped() not in str(caught.value) and key not in str(caught.value)


def test_the_shortest_basic_credential_is_refused_in_text() -> None:
    # "a:" is base64 "YTo" without its padding.
    with pytest.raises(EventCredentialRefusedError):
        check_event_text(_event(remarks="Authorization: Bas" + "ic YTo"))


def test_an_address_with_a_long_password_is_refused() -> None:
    address = "postgresql" + "://u:" + "p" * 300 + "@db/pbl"
    for payload in ({"dsn": address}, {"outer": [{address: "x"}]}):
        with pytest.raises(EventCredentialRefusedError):
            _safe_payload_json(payload)
    with pytest.raises(EventCredentialRefusedError):
        check_event_text(_event(remarks=address))


def test_a_credential_used_as_a_key_is_refused_like_a_value() -> None:
    for payload in ({_jwt_shaped(): "active"}, {"outer": [{_jwt_with_spaced_header(): "active"}]}):
        with pytest.raises(EventCredentialRefusedError) as caught:
            _safe_payload_json(payload)
        assert _jwt_shaped() not in str(caught.value)


def test_a_deeply_nested_header_is_not_a_server_error() -> None:
    # 1,536 brackets (the parser refuses it as JSON), 12,000 (within the 16,384 characters of header that are read, and
    # deep enough for the parser's RecursionError) and 100,000 (beyond what is read): none is a credential, none raises.
    for depth in (1536, 12_000, 100_000):
        assert not _looks_like_a_credential(_base64url("[" * depth) + ".e30.sig")


def test_a_token_with_an_empty_payload_part_is_refused() -> None:
    assert _looks_like_a_credential(_base64url('{"alg":"HS256"}') + ".." + "s" * 43)


def test_the_token_scan_decodes_each_part_a_bounded_number_of_times(monkeypatch) -> None:
    # Review round 13: a deterministic count, not a clock. Doubling the separators doubles the characters decoded.
    decoded: list[int] = []
    real = events_repository._is_jose_header

    def counting(segment: str) -> bool:
        decoded.append(len(segment))
        return real(segment)

    monkeypatch.setattr(events_repository, "_is_jose_header", counting)
    totals = []
    for count in (2_000, 4_000):
        decoded.clear()
        assert not _looks_like_a_credential("a-" * count + "x.y.z")
        totals.append(sum(decoded))
    assert totals[1] <= 2.2 * totals[0]
    # And a token glued after a separator is still found.
    assert _looks_like_a_credential("jwt_" + _jwt_shaped())
    assert _looks_like_a_credential("a-b-c-" + _jwt_shaped())


@pytest.mark.parametrize(
    "text_value",
    [
        "pbkdf2" + "_sha256$600000$",
        "pbkdf2" + "_sha256$600000$abcd$",
        # Review round 14: a short digest, an impossible digest, zero iterations, an invalid bcrypt cost.
        "pbkdf2" + "_sha256$" + "1" * 12 + "$salt$hash",
        "pbkdf2" + "_sha256$600000$salt$abcdefghijklmnop",
        "pbkdf2" + "_sha256$0$" + "ab" * 16 + "$" + "cd" * 32,
        "$2" + "b$99$" + "a" * 53,
        # Review round 15: impossible Argon2 and crypt parameters.
        "$argon2" + "id$v=999$m=0,t=0,p=0$a$" + "A" * 16,
        "$argon2" + "id$v=19$m=0,t=3,p=4$c2FsdHNhbHQ$" + "A" * 43,
        "$argon2" + "id$v=19$m=65536,t=3,p=4$abc$" + "A" * 43,
        # Review round 16: memory below eight times the parallelism, a salt whose length base64 cannot have.
        "$argon2" + "id$v=19$m=1,t=1,p=1$c2FsdHNhbHQ$" + "A" * 43,
        "$argon2" + "id$v=19$m=65536,t=3,p=4$" + "c" * 13 + "$" + "A" * 43,
        "$6" + "$rounds=0$saltsalt$" + "b" * 86,
        "$5" + "$rounds=12$saltsalt$" + "c" * 43,
        "$y" + "$abc$saltsalt$" + "e" * 43,
        "$2" + "b$abcdefghijklmnopqrst",
        "$2" + "b$12$" + "a" * 20,
        "$6" + "$rounds",
        "$argon2" + "id$v=19$",
        "$1" + "$abc",
    ],
)
def test_an_incomplete_or_malformed_hash_is_ordinary_text(text_value: str) -> None:
    # Review rounds 13 to 15: only a hash in its complete, possible encoding proves itself.
    assert json.loads(_safe_payload_json({"note": text_value})) == {"note": text_value}
    assert json.loads(_safe_payload_json({"outer": [{"note": text_value}]})) == {"outer": [{"note": text_value}]}
    check_event_text(_event(remarks=text_value))


@pytest.mark.parametrize(
    "text_value",
    [
        "$argon2" + "id$v=19$m=65536,t=3,p=4$" + "c2FsdHNhbHQ" + "$" + "A" * 43,
        "$6" + "$rounds=5000$" + "saltsalt" + "$" + "b" * 86,
        "$5" + "$saltsalt$" + "c" * 43,
        "$1" + "$saltsalt$" + "d" * 22,
        "$y" + "$j9T$saltsalt$" + "e" * 43,
        "pbkdf2" + "_sha256$870000$" + "SaltSaltSalt" + "$" + "Q" * 43 + "=",
    ],
)
def test_a_complete_hash_of_each_family_is_refused(text_value: str) -> None:
    # Django's pbkdf2 form is among them (below).
    with pytest.raises(EventCredentialRefusedError):
        _safe_payload_json({"note": "see " + text_value})
    with pytest.raises(EventCredentialRefusedError):
        check_event_text(_event(remarks=text_value))


@pytest.mark.parametrize("algorithm", [None, "", ["HS256"], {"name": "HS256"}, 256])
def test_a_header_without_a_named_algorithm_is_not_a_token(algorithm) -> None:
    # Review round 14: the header must name its algorithm as text.
    header = _base64url(json.dumps({"alg": algorithm}))
    value = header + "." + _base64url('{"sub":"1"}') + "." + "s" * 43
    assert json.loads(_safe_payload_json({"note": value})) == {"note": value}
    check_event_text(_event(remarks=value[:1000]))


def test_a_long_text_is_checked_in_time_proportional_to_its_length() -> None:
    # Inputs that cost time in the square of their length to an unbounded pattern or a split from every start.
    texts = ("a." * 25_000, "a-" * 25_000 + "x.y.z", "x://" + "a:" * 20_000)
    started = time.monotonic()
    for value in texts:
        assert not _looks_like_a_credential(value)
    assert time.monotonic() - started < 5


@pytest.mark.parametrize("make", CREDENTIAL_SHAPED)
def test_a_credential_shaped_value_is_refused_wherever_it_is(make) -> None:
    value = make()
    # In a note, the sample ends its line: a Bearer value followed on its line by more words is prose (review round 7).
    for payload in ({"company_name": value}, {"outer": {"note": f"see {value}\nhere"}}, {"lines": [value]}):
        with pytest.raises(EventCredentialRefusedError):
            _safe_payload_json(payload)
    for column in TEXT_COLUMNS:
        with pytest.raises(EventCredentialRefusedError):
            check_event_text(_event(**{column: f"x {value}"[:100]}))


def test_bearer_text_is_ordinary_text() -> None:
    # Not guessed from the words around it (the owner's decision, review round 9); a JSON Web Token after it is still
    # refused, because the token proves itself.
    assert not _looks_like_a_credential("Authorization: " + "Bear" + "er " + "z" * 24)
    assert _looks_like_a_credential("Authorization: " + "Bear" + "er " + _jwt_shaped())
    assert not _looks_like_a_credential("Bear" + "er " + "z" * 40)
    assert not _looks_like_a_credential("Bearer AUTH-LETTER-2026-0001 may collect the documents")
    assert not _looks_like_a_credential("Bearer of this letter is our site engineer")


def test_a_shape_glued_to_a_separator_is_still_found() -> None:
    for value in ("jwt_" + _jwt_shaped(), "token_" + _short_unsigned_jwt(), "hash_" + _stored_password_hash()):
        assert _looks_like_a_credential(value)
        with pytest.raises(EventCredentialRefusedError):
            _safe_payload_json({"reference": value})
        with pytest.raises(EventCredentialRefusedError):
            check_event_text(_event(correlation_id=value[:100]))


class _ChangesItsText:
    """Text that differs from one str() call to the next - the check must read what is stored."""

    def __init__(self, first: str, then: str) -> None:
        self._texts = [first, then]

    def __str__(self) -> str:
        return self._texts.pop(0) if len(self._texts) > 1 else self._texts[0]


def test_the_check_reads_exactly_the_text_that_is_stored() -> None:
    harmless_first = _safe_payload_json({"reference": _ChangesItsText("harmless", _jwt_shaped())})
    assert json.loads(harmless_first) == {"reference": "harmless"}
    with pytest.raises(EventCredentialRefusedError):
        _safe_payload_json({"reference": _ChangesItsText(_jwt_shaped(), "harmless")})


def test_the_refusal_names_no_value() -> None:
    value = _jwt_shaped()
    with pytest.raises(EventCredentialRefusedError) as caught:
        _safe_payload_json({"company_name": value})
    assert value not in str(caught.value)


@pytest.mark.parametrize("column", ["remarks", "correlation_id", "status_after"])
def test_a_refused_text_column_stores_no_event(column: str) -> None:
    marker = str(uuid4())
    with SessionLocal() as db:
        with pytest.raises(EventCredentialRefusedError):
            record_business_event(
                db,
                event_name="Tb1500Probe",
                source_module="tests",
                record_type="probe",
                record_public_id=marker,
                **{column: _basic_header()},
            )
        db.rollback()
        stored = db.execute(text("SELECT count(*) FROM business_event WHERE record_public_id = :m"), {"m": marker})
        assert stored.scalar() == 0


# --- Through a real route -----------------------------------------------------------------------------------------


def _auth_headers() -> dict[str, str]:
    response = client.post("/api/auth/login", json={"username": "sales1", "password": "password"})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _lead_body(company_name: str) -> dict[str, str]:
    return {
        "lead_source": "manual",
        "source_reference": "TB1-500 test enquiry",
        "company_name": company_name,
        "contact_name": "Under Secretary (Works)",
        "requirement_summary": "Crawler crane for the new Secretariat building; token advance agreed.",
        "lead_status_code": "NEW",
    }


def _remove_leads(company_name: str) -> None:
    with SessionLocal() as db:
        ids = [row[0] for row in db.execute(text("SELECT lead_public_id FROM crm_lead WHERE company_name = :n"), {"n": company_name})]
        for public_id in ids:
            db.execute(text("DELETE FROM business_event WHERE record_type = 'lead' AND record_public_id = :p"), {"p": str(public_id)})
            db.execute(text("DELETE FROM crm_lead WHERE lead_public_id = :p"), {"p": public_id})
        db.commit()


def test_a_lead_for_a_secretariat_is_saved_with_its_event() -> None:
    company_name = f"Gujarat State Secretariat (Sachivalaya) {uuid4()}"
    try:
        response = client.post("/api/leads", headers=_auth_headers(), json=_lead_body(company_name))
        assert response.status_code == 201, response.text
        lead_public_id = response.json()["lead"]["public_id"]
        with SessionLocal() as db:
            payload = db.execute(
                text(
                    "SELECT event_payload_json FROM business_event WHERE record_type = 'lead' AND record_public_id = :p "
                    "AND event_name = 'LeadCreated'"
                ),
                {"p": str(lead_public_id)},
            ).scalar_one()
        assert json.loads(payload)["company_name"] == company_name
    finally:
        _remove_leads(company_name)


@pytest.mark.parametrize(
    "hash_like",
    ["$argon2" + "id$v=999$m=0,t=0,p=0$a$" + "A" * 16, "$argon2" + "id$v=19$m=1,t=1,p=1$c2FsdHNhbHQ$" + "A" * 43],
)
def test_a_lead_whose_name_holds_hash_like_text_is_saved(hash_like: str) -> None:
    # Review rounds 15 and 16: impossible hash-like text through the real route.
    company_name = f"Ref {hash_like} {uuid4()}"
    try:
        response = client.post("/api/leads", headers=_auth_headers(), json=_lead_body(company_name))
        assert response.status_code == 201, response.text
    finally:
        _remove_leads(company_name)


@pytest.mark.parametrize("wording", ["may collect", ", may collect", "; please release"])
def test_a_lead_naming_a_bearer_representative_is_saved(wording: str) -> None:
    # Review rounds 7 and 8: Bearer prose through the real route, with an eight-letter first word and punctuation.
    company_name = f"Authorization: Bearer representative{'' if wording[0] in ',;' else ' '}{wording} {uuid4()}"
    try:
        response = client.post("/api/leads", headers=_auth_headers(), json=_lead_body(company_name))
        assert response.status_code == 201, response.text
    finally:
        _remove_leads(company_name)


def test_a_lead_whose_name_holds_a_token_is_refused_plainly_and_nothing_is_saved() -> None:
    company_name = f"Probe {_jwt_shaped()} {uuid4()}"
    try:
        response = client.post("/api/leads", headers=_auth_headers(), json=_lead_body(company_name))
        assert response.status_code == 422
        assert response.json() == {"detail": REFUSAL_MESSAGE}
        assert _jwt_shaped() not in response.text
        with SessionLocal() as db:
            saved = db.execute(text("SELECT count(*) FROM crm_lead WHERE company_name = :n"), {"n": company_name})
            assert saved.scalar() == 0
    finally:
        _remove_leads(company_name)
