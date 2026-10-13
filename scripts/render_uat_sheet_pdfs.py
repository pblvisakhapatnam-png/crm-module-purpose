"""Render the tester guides and sheets to PDF, beside their Markdown (TE-5 CRM pilot pack, TE-7 Hiring pack,
both rebuilt for the restart of 12 October 2026).

The owner shares `docs/uat/` and `docs/uat-hiring/` with the testers, so every document a tester is
given needs to be readable without a Markdown viewer: the guides, each tester's sheet, the one-person
route and the own-data part. The Hiring user guide's pictures sit in `docs/uat-hiring/images/`.

    python scripts/render_uat_sheet_pdfs.py                      # write the PDFs
    python scripts/render_uat_sheet_pdfs.py --check              # exit 1 if any is missing or out of date
    python scripts/render_uat_sheet_pdfs.py docs/uat-hiring      # only the sheets under that folder

Printing stamps the time into a PDF, so render only the pack you changed: re-rendering the other
rewrites its PDFs for nothing.

Deliberately NOT converted: the runbooks and READMEs, which are not for testers, and the written
feedback forms, which the spreadsheets supersede.

Needs `markdown` (pip) and a Chromium browser for printing. Chrome or Edge is found automatically;
set UAT_PDF_BROWSER to force one.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
UAT = REPO_ROOT / "docs" / "uat"
UAT_HIRING = REPO_ROOT / "docs" / "uat-hiring"

SHEETS = [
    UAT / "PBL_CRM_TESTER_GUIDE.md",
    UAT / "PBL_CRM_UAT_TESTER_1_SALES.md",
    UAT / "PBL_CRM_UAT_TESTER_2_SALES_MANAGER.md",
    UAT / "PBL_CRM_UAT_TESTER_3_OPERATIONS.md",
    UAT / "PBL_CRM_UAT_TESTER_4_ACCOUNTS.md",
    UAT / "PBL_CRM_UAT_ONE_PERSON_ROUTE.md",
    UAT / "PBL_CRM_UAT_YOUR_OWN_DATA.md",
    UAT_HIRING / "PBL_HIRING_USER_GUIDE.md",
    UAT_HIRING / "PBL_HIRING_TESTER_GUIDE.md",
    UAT_HIRING / "PBL_HIRING_UAT_TESTER_1_SALES.md",
    UAT_HIRING / "PBL_HIRING_UAT_TESTER_2_FLEET_ADMIN.md",
    UAT_HIRING / "PBL_HIRING_UAT_TESTER_3_OPERATIONS.md",
    UAT_HIRING / "PBL_HIRING_UAT_TESTER_4_ACCOUNTS.md",
    UAT_HIRING / "PBL_HIRING_UAT_ONE_PERSON_ROUTE.md",
    UAT_HIRING / "PBL_HIRING_UAT_YOUR_OWN_DATA.md",
]

# Each pack's footer names its own test.
FOOT_LABEL = {UAT: "PBL CRM test", UAT_HIRING: "PBL Hiring user test"}

BROWSERS = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    "/usr/bin/google-chrome",
    "/usr/bin/chromium",
]

# Print-first, not a web page: a working document people put on the desk beside the keyboard.
# Colours match the CRM's own palette so the pack looks of a piece with the guide.
CSS = """
@page { size: A4; margin: 18mm 16mm 16mm; }
* { box-sizing: border-box; }
body {
  margin: 0; color: #1f2933; background: #fff;
  font: 400 10.5pt/1.5 "Segoe UI", Arial, sans-serif;
}
h1 {
  margin: 0 0 4pt; padding-bottom: 6pt; border-bottom: 2.5pt solid #0f766e;
  color: #0f766e; font-size: 19pt; line-height: 1.15; font-weight: 600;
}
h1 + p { margin-top: 8pt; }
h2 {
  margin: 18pt 0 6pt; padding-top: 2pt; color: #1f2a27; font-size: 13.5pt; font-weight: 600;
  border-top: 0.75pt solid #d8e0e8; padding-top: 8pt;
  break-after: avoid; page-break-after: avoid;
}
h3 { margin: 12pt 0 4pt; font-size: 11.5pt; font-weight: 600; break-after: avoid; page-break-after: avoid; }
p, ul, ol { margin: 0 0 7pt; }
li { margin-bottom: 2.5pt; }
li > p { margin-bottom: 3pt; }
strong { color: #14532d; }
code {
  font: 9.5pt "Consolas", "Courier New", monospace;
  background: #eef2f5; padding: 0.5pt 3pt; border-radius: 2pt;
}
pre {
  background: #f5f7fa; border: 0.75pt solid #d8e0e8; border-left: 2.5pt solid #b8c4d1;
  padding: 7pt 9pt; border-radius: 3pt; overflow-wrap: break-word; white-space: pre-wrap;
  font: 9pt/1.45 "Consolas", "Courier New", monospace;
}
pre code { background: none; padding: 0; }
blockquote {
  margin: 8pt 0; padding: 7pt 10pt; background: #fffbeb;
  border: 0.75pt solid #f3d59a; border-left: 2.5pt solid #b45309; border-radius: 3pt;
}
blockquote p:last-child { margin-bottom: 0; }
table {
  width: 100%; border-collapse: collapse; margin: 7pt 0 10pt; font-size: 9.5pt;
  break-inside: auto; page-break-inside: auto;
}
th, td { border: 0.75pt solid #d8e0e8; padding: 4.5pt 6pt; text-align: left; vertical-align: top; }
th { background: #eef2f5; color: #1f2a27; font-weight: 600; }
tr { break-inside: avoid; page-break-inside: avoid; }
thead { display: table-header-group; }
hr { border: 0; border-top: 0.75pt solid #d8e0e8; margin: 14pt 0; }
img {
  display: block; max-width: 100%; height: auto; margin: 4pt 0 10pt;
  border: 0.75pt solid #d8e0e8; break-inside: avoid; page-break-inside: avoid;
}
img[alt="The menu"] { max-height: 150mm; }
a { color: #0f766e; }
.foot {
  margin-top: 18pt; padding-top: 6pt; border-top: 0.75pt solid #d8e0e8;
  color: #5b6776; font-size: 8.5pt;
}
"""


def find_browser() -> str:
    forced = os.environ.get("UAT_PDF_BROWSER")
    if forced:
        return forced
    for candidate in BROWSERS:
        if Path(candidate).exists():
            return candidate
        found = shutil.which(Path(candidate).name)
        if found:
            return found
    raise SystemExit(
        "No Chromium browser found for printing. Install Chrome or Edge, or set UAT_PDF_BROWSER."
    )


def html_for(source: Path) -> str:
    import markdown  # imported here so --check can report a clear error first

    body = markdown.markdown(
        source.read_text(encoding="utf-8"),
        extensions=["tables", "fenced_code", "sane_lists"],
    )
    title = source.stem.replace("_", " ")
    pack = next(folder for folder in FOOT_LABEL if folder in source.parents)
    foot = (
        '<p class="foot">' + FOOT_LABEL[pack] + " &middot; practice data only, nothing here is real &middot; "
        + source.name
        + "</p>"
    )
    # The page is printed from a temporary folder: the base makes a picture's relative path
    # (images/...) resolve beside the Markdown it belongs to.
    base = source.parent.resolve().as_uri() + "/"
    return (
        "<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">"
        + '<base href="' + base + '">'
        + "<title>" + title + "</title><style>" + CSS + "</style></head><body>"
        + body + foot + "</body></html>"
    )


def render(source: Path, browser: str, out: Path) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        page = Path(tmp) / (source.stem + ".html")
        page.write_text(html_for(source), encoding="utf-8")
        subprocess.run(
            [
                browser,
                "--headless",
                "--disable-gpu",
                "--no-pdf-header-footer",
                # Force light: a machine set to dark mode would otherwise print an ink-heavy page.
                "--blink-settings=preferredColorScheme=1",
                "--print-to-pdf=" + str(out),
                page.resolve().as_uri(),
            ],
            check=True,
            capture_output=True,
            timeout=120,
        )
    if not out.exists() or out.stat().st_size == 0:
        raise SystemExit("Printing produced nothing for " + source.name)


def _within(sheet: Path, path: Path) -> bool:
    target = (path if path.is_absolute() else Path.cwd() / path).resolve()
    return sheet == target or target in sheet.parents


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("only", nargs="*", type=Path,
                        help="Only the sheets in these folders or files (default: every sheet).")
    parser.add_argument("--check", action="store_true",
                        help="Report missing or out-of-date PDFs instead of writing them.")
    args = parser.parse_args(argv)
    chosen = [s for s in SHEETS if not args.only or any(_within(s, path) for path in args.only)]
    if not chosen:
        print("No sheet is under " + ", ".join(str(path) for path in args.only), file=sys.stderr)
        return 1

    missing = [s for s in chosen if not s.exists()]
    if missing:
        print("Source sheet missing: " + ", ".join(s.name for s in missing), file=sys.stderr)
        return 1

    if args.check:
        stale = []
        for source in chosen:
            pdf = source.with_suffix(".pdf")
            if not pdf.exists() or pdf.stat().st_mtime < source.stat().st_mtime:
                stale.append(pdf)
        for pdf in stale:
            print("Out of date or missing: " + str(pdf.relative_to(REPO_ROOT)))
        if stale:
            print("Run: python scripts/render_uat_sheet_pdfs.py", file=sys.stderr)
            return 1
        print("All " + str(len(chosen)) + " sheet PDFs are present and newer than their Markdown.")
        return 0

    browser = find_browser()
    for source in chosen:
        out = source.with_suffix(".pdf")
        render(source, browser, out)
        print("Wrote " + str(out.relative_to(REPO_ROOT)) + "  (" + str(out.stat().st_size) + " bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
