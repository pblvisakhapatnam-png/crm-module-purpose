"""Tests for the user-test packs' tester sheets and Feedback Logs (the restart of 12 October 2026). Standard library only.

Each tester types their own data, so two testers must never be given the same GST number: the second is refused at
every GST field - correct behaviour, reported as a fault. A sheet that names another tester's record must name one that
tester's sheet makes. Every link between the documents must lead somewhere. And each Feedback Log must list exactly the
steps its sheets hold, in order, or testers record Pass and Fail against the wrong step.
"""

from __future__ import annotations

import re
import sys
import unittest
import zipfile
from pathlib import Path
from xml.etree import ElementTree

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import build_uat_feedback_logs as logs  # noqa: E402


def _application_pattern(name: str) -> re.Pattern[str]:
    """The exact PAN/GSTIN rule the Account service enforces, read from its source."""
    source = (REPO_ROOT / "backend" / "app" / "modules" / "accounts" / "service.py").read_text(encoding="utf-8-sig")
    match = re.search(rf'^{name} = re\.compile\(r"([^"]+)"\)', source, re.MULTILINE)
    if match is None:
        raise AssertionError(f"{name} not found in the Account service")
    return re.compile(match.group(1))


PAN = _application_pattern("PAN_PATTERN")
GSTIN = _application_pattern("GSTIN_PATTERN")
PAN_LIKE = re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b")
GSTIN_LIKE = re.compile(r"\b[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][0-9A-Z]{3}\b")
TESTER_NAME = re.compile(r"`(T([1-4])-[^`]+)`")
LINK = re.compile(r"\]\(([^)\s#]+\.md)\)")

# Typed on purpose into another tester's customer, to see it refused as a duplicate (CRM Tester 4, step 8).
DELIBERATE_DUPLICATES = {("docs/uat", 4): {"37ZZZZM1001Z1ZZ"}}

# The fields that name a record a tester makes. What a tester types in one must start with a tester's prefix - their
# own, or another's whose record it is (TE-8 round 1).
NAME_FIELDS = {
    "Company name", "Account name", "Legal name", "PAN legal name", "Opportunity name", "Offer title", "Source / vendor",
    "Customer WO reference", "Customer PO / WO reference", "Submission reference", "Customer amendment reference",
    "Model name", "Holiday", "Description", "Contact name",
}
TABLE_ROW = re.compile(r"^\| (?P<field>[^|`]+?) \|(?P<rest>.+)\|\s*$", re.MULTILINE)
INLINE_FIELD = re.compile(r"\*(?P<field>[^*\n]+)\* `(?P<value>[^`]+)`")
CODE = re.compile(r"`([^`]+)`")


def _tester_sheets(pack: logs.Pack) -> dict[int, Path]:
    return {number: pack.folder / sheet for number, (_, sheet) in enumerate(pack.tabs[:4], start=1)}


def _pack_key(pack: logs.Pack) -> str:
    return pack.folder.relative_to(REPO_ROOT).as_posix()


def _xlsx_tabs(path: Path) -> dict[str, list[tuple[int, str]]]:
    """Each tab's (step, what) rows, read from the workbook's XML."""
    ns = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    rel = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
    with zipfile.ZipFile(path) as book:
        shared = [
            "".join(t.text or "" for t in item.iter(f"{{{ns['m']}}}t"))
            for item in ElementTree.fromstring(book.read("xl/sharedStrings.xml")).findall("m:si", ns)
        ] if "xl/sharedStrings.xml" in book.namelist() else []
        targets = {
            item.get("Id"): item.get("Target")
            for item in ElementTree.fromstring(book.read("xl/_rels/workbook.xml.rels"))
        }
        tabs: dict[str, list[tuple[int, str]]] = {}
        for sheet in ElementTree.fromstring(book.read("xl/workbook.xml")).find("m:sheets", ns):
            target = targets[sheet.get(rel)].lstrip("/")
            target = target if target.startswith("xl/") else "xl/" + target
            rows: dict[int, dict[str, str]] = {}
            for cell in ElementTree.fromstring(book.read(target)).iter(f"{{{ns['m']}}}c"):
                column, row = re.match(r"([A-Z]+)(\d+)", cell.get("r")).groups()
                value = cell.find("m:v", ns)
                inline = cell.find("m:is", ns)
                if cell.get("t") == "s" and value is not None:
                    text = shared[int(value.text)]
                elif inline is not None:
                    text = "".join(t.text or "" for t in inline.iter(f"{{{ns['m']}}}t"))
                else:
                    text = value.text if value is not None else ""
                rows.setdefault(int(row), {})[column] = text
            tabs[sheet.get("name")] = [
                (int(cells["A"]), cells.get("B", "")) for number, cells in sorted(rows.items())
                if number > 1 and cells.get("A", "").isdigit() and "B" in cells
            ]
    return tabs


class TesterSheetTests(unittest.TestCase):
    def test_every_number_a_tester_types_is_valid_and_carries_their_digit(self):
        for pack in logs.PACKS:
            for tester, sheet in _tester_sheets(pack).items():
                text = sheet.read_text(encoding="utf-8")
                allowed = DELIBERATE_DUPLICATES.get((_pack_key(pack), tester), set())
                for gstin in set(GSTIN_LIKE.findall(text)):
                    with self.subTest(sheet=sheet.name, gstin=gstin):
                        self.assertRegex(gstin, GSTIN)
                        if gstin not in allowed:
                            self.assertEqual(gstin[7], str(tester), "a GST number of another tester")
                for pan in set(PAN_LIKE.findall(text)):
                    with self.subTest(sheet=sheet.name, pan=pan):
                        self.assertRegex(pan, PAN)
                        self.assertEqual(pan[5], str(tester), "a PAN of another tester")

    def test_no_two_sheets_are_given_the_same_pan_or_gst_number(self):
        """One map across both packs: the two sites are separate databases, but a number in two sheets is still one
        tester's data in another's hands (TE-8 round 1)."""
        owner: dict[str, tuple[str, int]] = {}
        for pack in logs.PACKS:
            for tester, sheet in _tester_sheets(pack).items():
                allowed = DELIBERATE_DUPLICATES.get((_pack_key(pack), tester), set())
                text = sheet.read_text(encoding="utf-8")
                for number in (set(GSTIN_LIKE.findall(text)) | set(PAN_LIKE.findall(text))) - allowed:
                    with self.subTest(sheet=sheet.name, number=number):
                        self.assertEqual(owner.setdefault(number, (_pack_key(pack), tester)), (_pack_key(pack), tester))

    def test_every_record_a_tester_names_carries_a_testers_prefix(self):
        found = 0
        for pack in logs.PACKS:
            for tester, sheet in _tester_sheets(pack).items():
                # A name may wrap onto the next line after its field.
                text = re.sub(r"\*\n`", "* `", sheet.read_text(encoding="utf-8"))
                values = [
                    (row["field"].strip().strip("*"), value)
                    for row in TABLE_ROW.finditer(text)
                    for value in CODE.findall(row["rest"])
                ] + [(match["field"].strip(), match["value"]) for match in INLINE_FIELD.finditer(text)]
                for field, value in values:
                    if field in NAME_FIELDS:
                        found += 1
                        with self.subTest(sheet=sheet.name, field=field, value=value):
                            self.assertRegex(value, r"^T[1-4]-")
        # Some sheets name no record (Hiring Operations and Accounts); together they name dozens.
        self.assertGreater(found, 30, "few record names found: the field list no longer matches the sheets")

    def test_another_testers_record_is_one_their_sheet_makes(self):
        for pack in logs.PACKS:
            sheets = _tester_sheets(pack)
            texts = {tester: sheet.read_text(encoding="utf-8") for tester, sheet in sheets.items()}
            for tester, text in texts.items():
                for name, digit in TESTER_NAME.findall(text):
                    if int(digit) != tester:
                        with self.subTest(sheet=sheets[tester].name, name=name):
                            self.assertIn(f"`{name}`", texts[int(digit)])

    def test_every_link_between_the_documents_leads_somewhere(self):
        for pack in logs.PACKS:
            for document in sorted(pack.folder.glob("*.md")):
                for target in LINK.findall(document.read_text(encoding="utf-8")):
                    with self.subTest(document=document.name, target=target):
                        self.assertTrue((document.parent / target).resolve().is_file())

    def test_each_sheets_steps_are_numbered_one_to_n(self):
        for pack in logs.PACKS:
            for _, sheet in pack.tabs:
                numbers = [number for number, _ in logs.steps(pack.folder / sheet)]
                with self.subTest(sheet=sheet):
                    self.assertEqual(numbers, list(range(1, len(numbers) + 1)))
                    self.assertGreater(len(numbers), 0)

    def test_each_feedback_log_lists_its_sheets_steps(self):
        for pack in logs.PACKS:
            tabs = _xlsx_tabs(pack.log_path)
            for tab, sheet in pack.tabs:
                with self.subTest(log=pack.log, tab=tab):
                    self.assertEqual(tabs.get(tab), logs.steps(pack.folder / sheet))


if __name__ == "__main__":
    unittest.main()
