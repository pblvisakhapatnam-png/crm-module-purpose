"""Upload limits added after independent review of the upload package, rounds 1 to 6.

An extension and a declared content type could not guarantee two things:

- Size before parsing. FastAPI reads a request's whole form body before it runs any dependency,
  authentication included, so an upload of any size, from any caller, signed in or not, was
  received and spooled to a temporary file before it could be refused. routes.py now caps every
  documents request as its bytes arrive. The test below drives the real application through ASGI
  with a body that does not end and no token, and checks that the server stopped reading near the
  cap and answered 413 - where, without the cap, it would have read the whole body and then
  answered 401.
- Content. Both the extension and the declared type are the caller's claim, and the frontend
  declares whatever type the extension requires. The service now checks a file against its
  extension's format before it stores the file. A Word or Excel 97-2003 file is a compound file,
  like a PowerPoint deck, an Outlook message or a Windows installer, so .doc and .xls are checked
  by the streams at the top of the file's directory tree: round 2 found the signature alone too
  little, and round 3 found that reading every directory slot counted names no link reaches.
  Round 4 found the reader trusting too much of a crafted file: it now cross-checks the allocation
  table's counts, refuses a table sector listed twice, requires every name it reaches to be well
  formed, and refuses a file whose structure cannot be read rather than failing with a server error.
  Round 5 bounds the ZIP directory before it is read, round 6 closes two remaining resource gaps
  (a self-referential DIFAT chain under an attacker-controlled count, and a ZIP whose end-record
  entry count is forged below the directory's real size), and round 7 refuses a ZIP with data
  prepended before it, whose stored directory offset would otherwise point somewhere other than the
  directory zipfile actually opens.

The Office-format tests use two kinds of file. Short test files saved by Word and Excel - in the
97-2003 formats and the current ones - committed under tests/fixtures/documents, are the
independent evidence that the checks handle what Office writes. Files built here - compound files
to the [MS-CFB] layout, and ZIP archives - cover what those cannot: 4096-byte sectors, a directory
spanning several sectors, sub-storages, and the malformed shapes that must be refused.

Linked record ids are fresh uuid4 values, as in test_document_upload_rights.py: the checks read
nothing about the record itself.
"""

from __future__ import annotations

import asyncio
import contextlib
import io
import zipfile
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.main import app
from app.modules.documents.contract import ALLOWED_UPLOAD_EXTENSIONS, MAX_DOCUMENTS_REQUEST_BYTES
from app.modules.documents.routes import _BoundedBodyRoute
from app.modules.documents.service import (
    DocumentUploadTypeError,
    _compound_file_root_stream_names,
    _zip_directory_is_bounded,
    upload_document,
)
from app.modules.documents.storage import get_storage_provider_by_code

client = TestClient(app)

_tokens: dict[str, str] = {}


def _headers(username: str) -> dict[str, str]:
    if username not in _tokens:
        response = client.post("/api/auth/login", json={"username": username, "password": "password"})
        assert response.status_code == 200, response.text
        _tokens[username] = response.json()["access_token"]
    return {"Authorization": f"Bearer {_tokens[username]}"}


def _upload(username: str, linked_record_public_id: str, file_name: str, body: bytes):
    """Upload to an Account, declaring the exact content type the file's extension requires - as
    the frontend does - so the only thing left for the server to judge is the content."""
    return client.post(
        "/api/documents/upload",
        headers=_headers(username),
        data={
            "linked_record_type": "business_party",
            "linked_record_public_id": linked_record_public_id,
            "document_type": "OTHER",
        },
        files={"file": (file_name, body, ALLOWED_UPLOAD_EXTENSIONS[Path(file_name).suffix.lower()])},
    )


def _stored_file_count() -> int:
    root = Path(get_settings().document_storage_root)
    if not root.exists():
        return 0
    return sum(1 for path in root.rglob("*") if path.is_file())


def _documents_linked_to(linked_record_public_id: str) -> int:
    with SessionLocal() as db:
        return db.execute(
            text("SELECT count(*) FROM document_metadata WHERE linked_record_public_id = :id"),
            {"id": linked_record_public_id},
        ).scalar_one()


def _document_events_naming(linked_record_public_id: str) -> int:
    with SessionLocal() as db:
        return db.execute(
            text(
                "SELECT count(*) FROM business_event WHERE source_module = 'documents' "
                "AND event_payload_json LIKE :pattern"
            ),
            {"pattern": f"%{linked_record_public_id}%"},
        ).scalar_one()


def _delete_documents_linked_to(linked_record_public_id: str) -> None:
    """Stored bytes first, then rows: once a row is gone, so is the storage_key that finds them."""
    with SessionLocal() as db:
        rows = db.execute(
            text(
                "SELECT storage_provider_code, storage_key FROM document_metadata "
                "WHERE linked_record_public_id = :id AND storage_key IS NOT NULL"
            ),
            {"id": linked_record_public_id},
        ).fetchall()
    for provider_code, storage_key in rows:
        with contextlib.suppress(Exception):
            get_storage_provider_by_code(provider_code).delete(storage_key=storage_key)
    with SessionLocal() as db:
        db.execute(
            text("DELETE FROM document_metadata WHERE linked_record_public_id = :id"),
            {"id": linked_record_public_id},
        )
        db.commit()


def _assert_accepted(file_name: str, body: bytes) -> None:
    linked_id = str(uuid4())
    try:
        response = _upload("admin1", linked_id, file_name, body)
        assert response.status_code == 201, response.text
        assert _documents_linked_to(linked_id) == 1
    finally:
        _delete_documents_linked_to(linked_id)


def _assert_refused_and_nothing_written(file_name: str, body: bytes) -> None:
    linked_id = str(uuid4())
    files_before = _stored_file_count()
    try:
        response = _upload("admin1", linked_id, file_name, body)
        assert response.status_code == 422, response.text
        assert "content is not" in response.json()["detail"]
        assert _documents_linked_to(linked_id) == 0, "a refused file inserted a document row"
        assert _document_events_naming(linked_id) == 0, "a refused file recorded a business event"
        assert _stored_file_count() == files_before, "a refused file stored bytes"
    finally:
        _delete_documents_linked_to(linked_id)


@pytest.fixture(scope="module", autouse=True)
def _no_stored_object_is_leaked_by_this_module():
    before = _stored_file_count()
    yield
    after = _stored_file_count()
    assert after == before, f"this module leaked {after - before} stored object(s)"


# =============================================================================================
# The request cap: counted as the body arrives, before it is parsed or the caller authenticated.
# =============================================================================================

_CHUNK = 1024 * 1024
_BOUNDARY = "upload-limit-boundary"


def _send_endless_upload(chunk_count: int) -> tuple[int, int]:
    """POST, with no token, a multipart upload whose file part is `chunk_count` MB long and never
    closed. Returns the response status and how many bytes the application took from the request.
    """
    preamble = (
        f"--{_BOUNDARY}\r\n"
        'Content-Disposition: form-data; name="file"; filename="endless.txt"\r\n'
        "Content-Type: text/plain\r\n\r\n"
    ).encode("ascii")
    pending = [preamble, *([b"x" * _CHUNK] * chunk_count)]
    taken = 0
    statuses: list[int] = []

    async def receive() -> dict:
        nonlocal taken
        if pending:
            body = pending.pop(0)
            taken += len(body)
            return {"type": "http.request", "body": body, "more_body": True}
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message: dict) -> None:
        if message["type"] == "http.response.start":
            statuses.append(message["status"])

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": "/api/documents/upload",
        "raw_path": b"/api/documents/upload",
        "root_path": "",
        "query_string": b"",
        "headers": [
            (b"host", b"testserver"),
            (b"content-type", f"multipart/form-data; boundary={_BOUNDARY}".encode("ascii")),
        ],
        "client": ("127.0.0.1", 50000),
        "server": ("testserver", 80),
    }
    asyncio.run(app(scope, receive, send))
    return statuses[0], taken


def test_an_upload_is_refused_once_its_body_passes_the_cap_before_it_is_even_authenticated() -> None:
    chunk_count = MAX_DOCUMENTS_REQUEST_BYTES // _CHUNK + 15
    status, taken = _send_endless_upload(chunk_count)
    # Without the cap the whole body is read, and the missing token then earns a 401.
    assert status == 413
    assert taken <= MAX_DOCUMENTS_REQUEST_BYTES + _CHUNK, f"the application read {taken} bytes"
    assert taken < chunk_count * _CHUNK


def test_every_documents_route_counts_its_body_as_it_arrives() -> None:
    """The cap lives in the route class, so it must survive include_router on every route."""
    documents_routes = [
        route for route in app.routes if isinstance(route, APIRoute) and route.path.startswith("/api/documents")
    ]
    assert "/api/documents/upload" in {route.path for route in documents_routes}
    unbounded = [route.path for route in documents_routes if not isinstance(route, _BoundedBodyRoute)]
    assert unbounded == []


# =============================================================================================
# Word and Excel 97-2003: compound files built here to the [MS-CFB] layout.
# =============================================================================================

_CFB_SIGNATURE = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"
_FREE = 0xFFFFFFFF
_END_OF_CHAIN = 0xFFFFFFFE
_FAT_SECTOR = 0xFFFFFFFD
_NO_ENTRY = 0xFFFFFFFF
_ROOT, _STORAGE, _STREAM = 5, 1, 2


def _cfb_order(name: str) -> tuple[int, str]:
    """[MS-CFB] orders a directory's children by name length first, then by upper-cased name."""
    return (len(name), name.upper())


def _link_as_red_black_tree(entries: list[dict], ids: list[int]) -> int:
    """Link the given entries, one directory's children, into a red-black tree in [MS-CFB] order,
    and return the ID at its top.

    Balanced by construction: each subtree's middle entry is its top. Entries on the deepest level
    of a tree that is not full are red and every other entry is black, so every path from the top
    passes the same number of black entries and no red entry has a red child.
    """
    ordered = sorted(ids, key=lambda entry_id: _cfb_order(entries[entry_id]["name"]))
    if not ordered:
        return _NO_ENTRY
    deepest = len(ordered).bit_length() - 1
    full = len(ordered) == (1 << (deepest + 1)) - 1

    def build(low: int, high: int, depth: int) -> int:
        if low > high:
            return _NO_ENTRY
        middle = (low + high) // 2
        entry = entries[ordered[middle]]
        entry["left"] = build(low, middle - 1, depth + 1)
        entry["right"] = build(middle + 1, high, depth + 1)
        entry["red"] = not full and depth == deepest
        return ordered[middle]

    return build(0, len(ordered) - 1, 0)


def _compound_file_entries(
    root_streams: tuple[str, ...],
    storages: dict[str, tuple[str, ...]],
    orphan_streams: tuple[str, ...],
) -> list[dict]:
    """The directory entries of a compound file: the root, its streams and storages (each storage
    with its own streams) linked as trees, then any orphans - listed, but reached by no link."""
    entries: list[dict] = []

    def add(name: str, object_type: int) -> int:
        entries.append(
            {"name": name, "type": object_type, "left": _NO_ENTRY, "right": _NO_ENTRY, "child": _NO_ENTRY, "red": False}
        )
        return len(entries) - 1

    add("Root Entry", _ROOT)
    top_level = [add(name, _STREAM) for name in root_streams]
    for storage_name, children in storages.items():
        storage_id = add(storage_name, _STORAGE)
        top_level.append(storage_id)
        entries[storage_id]["child"] = _link_as_red_black_tree(entries, [add(child, _STREAM) for child in children])
    entries[0]["child"] = _link_as_red_black_tree(entries, top_level)
    for name in orphan_streams:
        add(name, _STREAM)
    return entries


def _compound_file(
    *root_streams: str,
    sector_size: int = 512,
    storages: dict[str, tuple[str, ...]] | None = None,
    orphan_streams: tuple[str, ...] = (),
) -> bytes:
    """A minimal compound file laid out as [MS-CFB] describes: a header; sector 0, the allocation
    table; then as many directory sectors as the entries need, chained through the table. The
    streams hold nothing - a reader of the directory depends on nothing more."""
    entries = _compound_file_entries(root_streams, storages or {}, orphan_streams)
    entries_per_sector = sector_size // 128
    directory_sectors = -(-len(entries) // entries_per_sector)
    # Directory sectors are 1..directory_sectors, each pointing at the next; the last ends the chain.
    fat = [_FAT_SECTOR, *range(2, directory_sectors + 1), _END_OF_CHAIN]
    fat += [_FREE] * (sector_size // 4 - len(fat))

    header = bytearray(512)
    header[0:8] = _CFB_SIGNATURE
    header[0x18:0x1A] = (0x3E).to_bytes(2, "little")  # minor version
    header[0x1A:0x1C] = (3 if sector_size == 512 else 4).to_bytes(2, "little")  # major version
    header[0x1C:0x1E] = b"\xfe\xff"  # byte order
    header[0x1E:0x20] = (sector_size.bit_length() - 1).to_bytes(2, "little")  # sector shift
    header[0x20:0x22] = (6).to_bytes(2, "little")  # mini sector shift
    header[0x2C:0x30] = (1).to_bytes(4, "little")  # one allocation-table sector
    header[0x30:0x34] = (1).to_bytes(4, "little")  # the directory starts at sector 1
    header[0x38:0x3C] = (4096).to_bytes(4, "little")  # mini stream cutoff
    header[0x3C:0x40] = _END_OF_CHAIN.to_bytes(4, "little")  # no mini allocation table
    header[0x44:0x48] = _END_OF_CHAIN.to_bytes(4, "little")  # no further table-sector list
    header[0x4C:0x50] = (0).to_bytes(4, "little")  # the allocation table is sector 0
    header[0x50:0x200] = b"\xff" * (0x200 - 0x50)  # the other 108 slots are free

    directory = bytearray()
    for entry in entries:
        raw = bytearray(128)
        encoded = (entry["name"] + "\0").encode("utf-16-le")
        raw[0 : len(encoded)] = encoded
        raw[0x40:0x42] = len(encoded).to_bytes(2, "little")
        raw[0x42] = entry["type"]
        raw[0x43] = 0 if entry["red"] else 1  # colour: 0 red, 1 black
        raw[0x44:0x48] = entry["left"].to_bytes(4, "little")
        raw[0x48:0x4C] = entry["right"].to_bytes(4, "little")
        raw[0x4C:0x50] = entry["child"].to_bytes(4, "little")
        raw[0x74:0x78] = _END_OF_CHAIN.to_bytes(4, "little")  # no content
        directory += raw
    unused = bytearray(128)
    unused[0x44:0x50] = b"\xff" * 12  # an unused entry links to nothing
    while len(directory) < directory_sectors * sector_size:
        directory += unused

    table = b"".join(value.to_bytes(4, "little") for value in fat)
    return bytes(header) + bytes(sector_size - 512) + table + bytes(directory)


# In a built file with 512-byte sectors the directory starts after the header and the table.
_DIRECTORY_OFFSET = 1024


def _set_entry_field(compound_file: bytes, entry_id: int, field_offset: int, value: int, width: int = 4) -> bytes:
    patched = bytearray(compound_file)
    position = _DIRECTORY_OFFSET + entry_id * 128 + field_offset
    patched[position : position + width] = value.to_bytes(width, "little")
    return bytes(patched)


def _with_sibling_loop(compound_file: bytes) -> bytes:
    """The root's top child points back at itself as its own left sibling."""
    top = int.from_bytes(compound_file[_DIRECTORY_OFFSET + 0x4C : _DIRECTORY_OFFSET + 0x50], "little")
    return _set_entry_field(compound_file, top, 0x44, top)


def _with_looping_directory_chain(compound_file: bytes) -> bytes:
    """The directory's only sector points back at itself in the allocation table."""
    looped = bytearray(compound_file)
    looped[512 + 4 : 512 + 8] = (1).to_bytes(4, "little")  # table entry for sector 1 -> sector 1
    return bytes(looped)


def _set_entry_bytes(compound_file: bytes, entry_id: int, field_offset: int, raw: bytes) -> bytes:
    patched = bytearray(compound_file)
    position = _DIRECTORY_OFFSET + entry_id * 128 + field_offset
    patched[position : position + len(raw)] = raw
    return bytes(patched)


def _with_table_sectors_listed(compound_file: bytes, listed: list[int], count: int) -> bytes:
    """The file with 300 empty sectors added - so its size would allow a larger allocation table -
    and a header that lists `listed` as the table's sectors and states `count` of them."""
    patched = bytearray(compound_file) + bytes(512 * 300)
    slots = [*listed, *([_FREE] * (109 - len(listed)))]
    patched[0x4C:0x200] = b"".join(slot.to_bytes(4, "little") for slot in slots)
    patched[0x2C:0x30] = count.to_bytes(4, "little")
    return bytes(patched)


def _in_order_names(entries: list[dict], top: int) -> list[str]:
    if top == _NO_ENTRY:
        return []
    entry = entries[top]
    return [*_in_order_names(entries, entry["left"]), entry["name"], *_in_order_names(entries, entry["right"])]


def _black_height(entries: list[dict], top: int) -> int:
    """The number of black entries on every path down from `top`; fails if the paths disagree or
    a red entry has a red child."""
    if top == _NO_ENTRY:
        return 1
    entry = entries[top]
    for side in ("left", "right"):
        child = entry[side]
        assert not (entry["red"] and child != _NO_ENTRY and entries[child]["red"]), "a red entry has a red child"
    left, right = _black_height(entries, entry["left"]), _black_height(entries, entry["right"])
    assert left == right, "paths down the tree pass different numbers of black entries"
    return left + (0 if entry["red"] else 1)


@pytest.mark.parametrize("child_count", range(1, 21))
def test_built_files_link_each_directory_as_a_red_black_tree_in_cfb_order(child_count: int) -> None:
    """The built files are only evidence if their directory trees are valid: ordered as [MS-CFB]
    requires, black at the top, no red entry with a red child, equal black height everywhere."""
    names = tuple(f"Stream{number}" for number in range(child_count))
    entries = _compound_file_entries(names, {}, ())
    top = entries[0]["child"]
    assert _in_order_names(entries, top) == sorted(names, key=_cfb_order)
    assert not entries[top]["red"]
    _black_height(entries, top)


def test_a_self_referential_difat_sector_is_refused_without_a_long_loop() -> None:
    """Round 6: the header's list-sector count is only a claim and a DIFAT sector could point back
    at itself. The reader must reject the file by structure, not spin up to the claimed count. This
    returns by the count cross-check, so no wall-clock timeout is needed to prove it is bounded."""
    built = _with_self_referential_difat(_compound_file("WordDocument"))
    assert _compound_file_root_stream_names(io.BytesIO(built)) == set()


def test_a_forged_low_entry_count_over_a_large_directory_is_refused() -> None:
    """Round 6: the end record's entry count is only a claim; the reader must count the directory's
    real entries and refuse when there are more than the limit, whatever the claim says."""
    forged = _zip_with_forged_entry_count(_zip_with_extra_parts(12_000, 8), 5)
    assert _zip_directory_is_bounded(io.BytesIO(forged)) is False


def test_a_prepended_archive_is_refused_because_the_directory_does_not_meet_the_end_record() -> None:
    """Round 7: data prepended before the archive leaves the stored directory offset short of the
    end record by the prefix length. The reader must refuse it, so it can never validate one
    directory while zipfile (which follows a concatenation offset) opens another. A clean archive
    passes; the same archive with a prefix does not."""
    clean = _zip_of("[Content_Types].xml", "word/document.xml")
    assert _zip_directory_is_bounded(io.BytesIO(clean)) is True
    assert _zip_directory_is_bounded(io.BytesIO(_with_prepended_data(clean, b"decoy " * 200))) is False


@pytest.mark.parametrize("sector_size", [512, 4096])
def test_the_reader_lists_exactly_the_streams_at_the_top_of_the_tree(sector_size: int) -> None:
    """Not a storage's name, not the streams inside it, and not an orphan no link reaches."""
    top_level = ("WordDocument", "1Table", "\x05SummaryInformation", *[f"Part{number}" for number in range(6)])
    built = _compound_file(
        *top_level,
        sector_size=sector_size,
        storages={"ObjectPool": ("Hidden",)},
        orphan_streams=("Orphan",),
    )
    assert _compound_file_root_stream_names(io.BytesIO(built)) == set(top_level)


# =============================================================================================
# Word and Excel 97-2003: blank files saved by Word and Excel themselves.
# =============================================================================================

# Short test files saved by Word and Excel on 11 September 2026. In these copies the author's name
# is replaced by a placeholder and nothing else is changed; the folder's README says how.
_SAVED_BY_OFFICE = Path(__file__).parent / "fixtures" / "documents"
_SAVED_BY_WORD_97 = _SAVED_BY_OFFICE / "saved-by-word-97-2003.doc"
_SAVED_BY_EXCEL_97 = _SAVED_BY_OFFICE / "saved-by-excel-97-2003.xls"
_SAVED_BY_WORD = _SAVED_BY_OFFICE / "saved-by-word.docx"
_SAVED_BY_EXCEL = _SAVED_BY_OFFICE / "saved-by-excel.xlsx"


def test_the_reader_finds_word_and_excel_streams_in_files_saved_by_word_and_excel() -> None:
    assert "WordDocument" in _compound_file_root_stream_names(io.BytesIO(_SAVED_BY_WORD_97.read_bytes()))
    assert "Workbook" in _compound_file_root_stream_names(io.BytesIO(_SAVED_BY_EXCEL_97.read_bytes()))


@pytest.mark.parametrize(
    "path", [_SAVED_BY_WORD_97, _SAVED_BY_EXCEL_97, _SAVED_BY_WORD, _SAVED_BY_EXCEL], ids=lambda path: path.name
)
def test_files_saved_by_word_and_excel_are_accepted(path: Path) -> None:
    _assert_accepted(path.name, path.read_bytes())


@pytest.mark.parametrize(
    ("path", "wrong_name"),
    [
        (_SAVED_BY_WORD_97, "word-document.xls"),
        (_SAVED_BY_EXCEL_97, "excel-workbook.doc"),
        (_SAVED_BY_WORD, "word-document.xlsx"),
        (_SAVED_BY_EXCEL, "excel-workbook.docx"),
    ],
    ids=["word-97-named-xls", "excel-97-named-doc", "word-named-xlsx", "excel-named-docx"],
)
def test_a_file_saved_by_word_or_excel_is_refused_under_the_other_extension(path: Path, wrong_name: str) -> None:
    _assert_refused_and_nothing_written(wrong_name, path.read_bytes())


# =============================================================================================
# Content: a file must match its extension's format.
# =============================================================================================


def _zip_of(*names: str) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name in names:
            archive.writestr(name, "<root/>")
    return buffer.getvalue()


def _zip_with_undecodable_part_name() -> bytes:
    """A Word archive whose last part's name, in the central directory, is flagged as UTF-8 but is
    not valid UTF-8: reading the directory fails, and the file must be refused, not crash."""
    archive = bytearray(_zip_of("[Content_Types].xml", "word/document.xml", "zz"))
    entry = archive.rfind(b"PK\x01\x02")  # the central-directory entry for "zz"
    archive[entry + 8 : entry + 10] = (0x0800).to_bytes(2, "little")  # flags: the name is UTF-8
    archive[entry + 46 : entry + 48] = b"\xff\xfe"  # the name's two bytes, not valid UTF-8
    return bytes(archive)


def _zip_with_extra_parts(count: int, name_length: int) -> bytes:
    """A Word archive with its two required parts and `count` empty extra parts, each named with
    `name_length` digits - to push the directory past its entry or size limit (round 5)."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
        archive.writestr("word/document.xml", "<root/>")
        for number in range(count):
            archive.writestr(f"extra/{number:0{name_length}d}", b"")
    return buffer.getvalue()


def _zip_with_zip64_locator() -> bytes:
    """A Word archive with a ZIP64 locator placed just before its end record."""
    archive = _zip_of("[Content_Types].xml", "word/document.xml")
    end = archive.rfind(b"PK\x05\x06")
    return archive[:end] + b"PK\x06\x07" + bytes(16) + archive[end:]


def _zip_with_forged_entry_count(archive: bytes, count: int) -> bytes:
    """The archive with its end record's entry-count fields forced to `count` - a smaller number
    than the directory really holds, which zipfile ignores and reads every entry regardless."""
    patched = bytearray(archive)
    end = patched.rfind(b"PK\x05\x06")
    patched[end + 8 : end + 10] = count.to_bytes(2, "little")  # entries on this disk
    patched[end + 10 : end + 12] = count.to_bytes(2, "little")  # entries in total
    return bytes(patched)


def _with_prepended_data(archive: bytes, prefix: bytes) -> bytes:
    """Bytes prepended before a ZIP archive, its end record left unadjusted. zipfile handles this
    by computing a concatenation offset and reading the real directory; a reader that trusted the
    stored offset would validate a directory at the wrong place (round 7 trigger)."""
    return prefix + archive


def _with_self_referential_difat(compound_file: bytes) -> bytes:
    """The file with a DIFAT (allocation-table list) sector that points back at itself and a
    header claiming a huge number of them - the round 6 CPU-exhaustion trigger."""
    patched = bytearray(compound_file)
    sector_index = (len(patched) - 512) // 512  # the next sector after the existing ones
    difat = bytearray(b"\xff" * 512)  # every table-sector slot free
    difat[512 - 4 : 512] = sector_index.to_bytes(4, "little")  # next DIFAT sector: itself
    patched += difat
    patched[0x44:0x48] = sector_index.to_bytes(4, "little")  # first DIFAT sector
    patched[0x48:0x4C] = (0x7FFFFFFF).to_bytes(4, "little")  # number of DIFAT sectors
    return bytes(patched)


# Files built the way each accepted format is built - written out here, not taken from the code
# under test. The check confirms how a file is built, not that the document inside is valid (owner
# decision after review round 5), so a built Word or Excel file with empty streams is accepted.
ACCEPTED_FILES: dict[str, bytes] = {
    "offer.pdf": b"%PDF-1.7\n%\xe2\xe3\xcf\xd3\n1 0 obj\n<< /Type /Catalog >>\nendobj\n",
    "letter.doc": _compound_file("WordDocument", "1Table", "\x05SummaryInformation"),
    "large-sector-letter.doc": _compound_file("WordDocument", "1Table", sector_size=4096),
    # Nine entries need three 512-byte directory sectors, so the reader must follow the chain.
    "long-directory-letter.doc": _compound_file(*[f"Part{number}" for number in range(7)], "WordDocument"),
    # A document with embedded objects keeps them in a sub-storage beside the Word stream.
    "letter-with-objects.doc": _compound_file("WordDocument", "1Table", storages={"ObjectPool": ("\x01Ole",)}),
    "letter.docx": _zip_of("[Content_Types].xml", "word/document.xml"),
    "rates.xls": _compound_file("Workbook", "\x05SummaryInformation"),
    "old-rates.xls": _compound_file("Book"),
    "rates.xlsx": _zip_of("[Content_Types].xml", "xl/workbook.xml"),
    "site.png": b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01",
    "site.jpg": b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01",
    "site.jpeg": b"\xff\xd8\xff\xe1\x00\x16Exif\x00\x00",
    "note.txt": "Copy of customer work order received by email.\n".encode("utf-8"),
    "rupee-note.txt": "Rate agreed: ₹45,000 per day.\n".encode("utf-8"),
    "unicode-note.txt": "Rate agreed: ₹45,000 per day.\n".encode("utf-16"),
    "lines.csv": b"line,description,amount\r\n1,Crane hire,45000\r\n",
}

REFUSED_FILES: dict[str, bytes] = {
    # A web page named .pdf, and one that mentions the PDF header only in a comment.
    "invoice.pdf": b"<!DOCTYPE html><html><body><script>alert(1)</script></body></html>",
    "comment.pdf": b"<!-- %PDF-1.4 --><html><body>not a PDF</body></html>",
    "empty.pdf": b"",
    # A Windows program named .png.
    "photo.png": b"MZ\x90\x00\x03\x00\x00\x00\x04\x00\x00\x00\xff\xff",
    # A PDF named .jpg.
    "scan.jpg": b"%PDF-1.4\n",
    # The compound-file signature and nothing a directory could be read from: what round 1 accepted.
    "header-only.doc": _CFB_SIGNATURE + b"\x00" * 504,
    # A ZIP archive named .doc.
    "zip-letter.doc": _zip_of("word/document.xml"),
    # PowerPoint decks are compound files too.
    "slides.doc": _compound_file("PowerPoint Document", "Current User"),
    "slides.xls": _compound_file("PowerPoint Document", "Current User"),
    # A workbook named .doc, and a Word document named .xls.
    "workbook-as-letter.doc": _compound_file("Workbook"),
    "letter-as-workbook.xls": _compound_file("WordDocument", "1Table"),
    # A Word or Excel stream listed in the directory but reached by no link: what round 2 accepted.
    "orphan-word.doc": _compound_file("PowerPoint Document", orphan_streams=("WordDocument",)),
    "orphan-workbook.xls": _compound_file("PowerPoint Document", orphan_streams=("Workbook",)),
    # A Word stream inside a sub-storage, not at the top of the tree.
    "nested-word.doc": _compound_file("Current User", storages={"ObjectPool": ("WordDocument",)}),
    # Malformed directories: a chain that loops, a tree that loops, a root entry that is not one,
    # and a link to an entry that does not exist.
    "looping-directory-chain.doc": _with_looping_directory_chain(_compound_file("WordDocument")),
    "looping-tree.doc": _with_sibling_loop(_compound_file("WordDocument", "1Table")),
    "no-root.doc": _set_entry_field(_compound_file("WordDocument"), 0, 0x42, _STORAGE, width=1),
    "broken-link.doc": _set_entry_field(_compound_file("WordDocument"), 0, 0x4C, 999),
    # Crafted allocation-table lists, each accepted by round 3's reader: the same table sector
    # listed 109 times, listed twice, and a list the header's count does not match (round 4).
    "repeated-table-sector.doc": _with_table_sectors_listed(_compound_file("WordDocument"), [0] * 109, 109),
    "duplicate-table-sector.doc": _with_table_sectors_listed(_compound_file("WordDocument"), [0, 0], 2),
    "table-count-mismatch.doc": _with_table_sectors_listed(_compound_file("WordDocument"), [0], 2),
    # Malformed names, each accepted by round 3's reader beside a valid Word stream: a Word name
    # without its closing NUL, an odd name length, a name that is not valid UTF-16, and one with a
    # NUL inside (round 4). Entry 1 is "WordDocument", entry 2 "1Table".
    "unterminated-name.doc": _set_entry_bytes(_compound_file("WordDocument", "1Table"), 1, 24, "X".encode("utf-16-le")),
    "odd-name-length.doc": _set_entry_field(_compound_file("WordDocument", "1Table"), 2, 0x40, 13, width=2),
    "undecodable-name.doc": _set_entry_bytes(_compound_file("WordDocument", "1Table"), 2, 0, b"\x00\xd8"),
    "nul-inside-name.doc": _set_entry_bytes(_compound_file("WordDocument", "1Table"), 2, 2, b"\x00\x00"),
    # A Word archive whose part name cannot be decoded: refused, not a server error (round 4).
    "undecodable-part-name.docx": _zip_with_undecodable_part_name(),
    # Directories too big to read before judging, each accepted by round 4's reader: more than
    # 10,000 entries; fewer, but a directory over 1 MB; and a ZIP64 locator (round 5).
    "many-parts.docx": _zip_with_extra_parts(12_000, 8),
    "large-directory.docx": _zip_with_extra_parts(9_000, 120),
    "zip64-locator.docx": _zip_with_zip64_locator(),
    # A directory of more than 10,000 entries with its end-record count forged down to 5, and a
    # compound file whose DIFAT sector points back at itself under a huge count (round 6).
    "forged-entry-count.docx": _zip_with_forged_entry_count(_zip_with_extra_parts(12_000, 8), 5),
    "self-referential-difat.doc": _with_self_referential_difat(_compound_file("WordDocument")),
    # Data prepended before a valid Word archive, and before one with more than 10,000 parts: the
    # stored directory offset no longer meets the end record, so the archive is refused before
    # zipfile - which would follow its concatenation offset to the real directory - opens it
    # (round 7).
    "prepended-data.docx": _with_prepended_data(_zip_of("[Content_Types].xml", "word/document.xml"), b"decoy " * 200),
    "prepended-many-parts.docx": _with_prepended_data(_zip_with_extra_parts(12_000, 8), b"decoy " * 200),
    # An HTML table named .xls, as some exporters produce.
    "export.xls": b"<table><tr><td>1</td></tr></table>",
    # A ZIP archive that is not a Word document, and a web page, named .docx.
    "report.docx": _zip_of("readme.txt"),
    "report-page.docx": b"<html>not an archive</html>",
    # A macro-enabled document or workbook renamed.
    "macros.docx": _zip_of("[Content_Types].xml", "word/document.xml", "word/vbaProject.bin"),
    "macros.xlsx": _zip_of("[Content_Types].xml", "xl/workbook.xml", "xl/vbaProject.bin"),
    # A Word document named .xlsx.
    "sheet.xlsx": _zip_of("[Content_Types].xml", "word/document.xml"),
    # A Windows program named .txt.
    "notes.txt": b"MZ\x90\x00\x03\x00\x00\x00\x04\x00",
    # An image named .csv.
    "data.csv": b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR",
}


@pytest.mark.parametrize("file_name", sorted(ACCEPTED_FILES))
def test_each_accepted_format_is_accepted(file_name: str) -> None:
    _assert_accepted(file_name, ACCEPTED_FILES[file_name])


@pytest.mark.parametrize("file_name", sorted(REFUSED_FILES))
def test_a_file_whose_content_does_not_match_its_extension_is_refused_and_nothing_is_written(
    file_name: str,
) -> None:
    _assert_refused_and_nothing_written(file_name, REFUSED_FILES[file_name])


def test_content_is_checked_only_after_the_rights_check() -> None:
    """readonly1 may attach to nothing. A 403 rather than a 422 for mismatched content shows the
    check that reads the file never ran for a caller who was refused."""
    linked_id = str(uuid4())
    files_before = _stored_file_count()
    try:
        response = _upload("readonly1", linked_id, "invoice.pdf", REFUSED_FILES["invoice.pdf"])
        assert response.status_code == 403, response.text
        assert _documents_linked_to(linked_id) == 0
        assert _stored_file_count() == files_before
    finally:
        _delete_documents_linked_to(linked_id)


def test_a_stream_that_cannot_be_rewound_is_refused_rather_than_stored_unchecked() -> None:
    """The content check reads the file and rewinds, so the storage write still counts every byte.
    A stream that cannot rewind is refused, not stored unchecked."""

    class _OneWayStream:
        def read(self, size: int = -1) -> bytes:
            return b"%PDF-1.4\n"

        def seekable(self) -> bool:
            return False

    linked_id = uuid4()
    with SessionLocal() as db:
        with pytest.raises(DocumentUploadTypeError):
            upload_document(
                db,
                linked_record_type="business_party",
                linked_record_public_id=linked_id,
                document_type="OTHER",
                file_name="one-way.pdf",
                declared_content_type="application/pdf",
                stream=_OneWayStream(),  # type: ignore[arg-type]
                remarks=None,
                current_user_public_id=None,
            )
    assert _documents_linked_to(str(linked_id)) == 0
