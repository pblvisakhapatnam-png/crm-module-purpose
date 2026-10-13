"""Pure HTML quotation renderer (Slice 9E).

`render_quote_html` is a PURE FUNCTION: no database access, no I/O, no clock, no randomness. The
same inputs render byte-identical output every time. This is what makes the output directly
testable and what makes `source_fingerprint` (computed separately, in service.py, over the
source-data snapshot BEFORE it reaches this module) meaningful - see
docs/agent/slices/slice-9e-quotation-generation.md, "Rendering" and "Snapshot and staleness".

Build-time deviation from the frozen design, recorded here per this project's own transparency
convention (see Slice 9C's "What changed from the frozen design, and why"): the frozen spec names
the input `payload: QuoteSnapshotPayload`. This module instead takes the same canonical dict that
service.py separately hashes for `source_fingerprint`, plus a few document-specific keyword
arguments (quote_reference, version_no, ...) that are facts about THIS GENERATED VERSION, not
about the offer's source data, and must therefore never be part of the hashed snapshot - if they
were, the fingerprint would depend on how many prior versions existed rather than on whether the
offer's underlying data has changed. Passing the identical dict into both the hasher and the
renderer (rather than two independently-maintained shapes, one a plain dict and one a dataclass)
removes an entire class of "the hash checks shape A but the render was actually built from shape
B" drift bug. This changes no business meaning, output content or field name; it is an internal
representation choice within this slice's own new code.

THE SINGLE LARGEST RISK IN THIS MODULE: every interpolated value is customer- or user-supplied
free text (Account name, offer title, remarks, line descriptions, T&C snapshot text). Every one
of them passes through `_esc()` (`html.escape(..., quote=True)`). No exceptions - not "this one
looks safe", not "this one is normally short". The output must never contain a `<script>` element
or an `on...=` event-handler attribute; that is proven by tests driven with hostile input against
this file's actual output, not by inspecting this file's own shape (a test never shown to catch
its defect is an assertion of intent, not a control).
"""

from __future__ import annotations

from decimal import Decimal
from html import escape as _html_escape
from typing import Any

from app.shared.currency import currency_code_key

QUOTE_RENDER_SCHEMA_VERSION = "1.0"


def _esc(value: Any) -> str:
    """Escape a single value for safe interpolation into HTML text OR a double-quoted HTML
    attribute.

    `quote=True` additionally escapes `"` and `'`, so the same helper is safe in both contexts -
    there is deliberately only one escaping path in this module, not one for text and a
    different (easier to get wrong) one for attributes.

    None/empty becomes an empty string rather than the literal "None", so a missing optional
    field renders as blank rather than as a visible implementation artefact.
    """
    if value is None:
        return ""
    return _html_escape(str(value), quote=True)


def _format_amount(value: Decimal | str | None) -> str:
    """Render a Decimal/decimal-string amount with thousands separators and 2 decimal places.

    Never trusts the value to already be a Decimal - the snapshot dict stores amounts as
    strings (so it round-trips through json.dumps for fingerprinting), so this accepts either.
    A None or unparseable value renders as "-" rather than raising, because a quote with a
    missing rate on one line must still render every other line.
    """
    if value is None or value == "":
        return "-"
    try:
        decimal_value = value if isinstance(value, Decimal) else Decimal(str(value))
    except Exception:
        return _esc(value)
    return f"{decimal_value:,.2f}"


_STYLE = """
  * { box-sizing: border-box; }
  body { font-family: Arial, Helvetica, sans-serif; color: #1f2937; margin: 0; padding: 24px; background: #ffffff; }
  .quote-header { display: flex; justify-content: space-between; align-items: flex-start; border-bottom: 3px solid #1f2937; padding-bottom: 12px; margin-bottom: 20px; }
  .quote-header h1 { margin: 0; font-size: 22px; letter-spacing: 1px; }
  .quote-meta { text-align: right; font-size: 13px; color: #374151; }
  .quote-meta div { margin-bottom: 2px; }
  .prepared-by { margin-top: 8px; font-size: 12px; color: #6b7280; }
  .approval-pointer { margin-top: 24px; font-size: 11px; color: #6b7280; border-top: 1px solid #e5e7eb; padding-top: 8px; }
  .parties { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 20px; }
  .party-block h3 { font-size: 12px; text-transform: uppercase; color: #6b7280; margin: 0 0 6px; }
  .party-block p { margin: 0 0 4px; font-size: 14px; }
  .reference-block { font-size: 13px; color: #374151; margin-bottom: 20px; }
  table.lines { width: 100%; border-collapse: collapse; margin-bottom: 6px; }
  table.lines th, table.lines td { border: 1px solid #d1d5db; padding: 8px; font-size: 13px; text-align: left; }
  table.lines th { background: #f3f4f6; }
  table.lines td.numeric, table.lines th.numeric { text-align: right; }
  .total-row td { font-weight: bold; background: #f9fafb; }
  .gst-note { font-size: 12px; color: #6b7280; margin: 4px 0 20px; }
  .terms h3 { font-size: 14px; margin-bottom: 8px; }
  .clause { margin-bottom: 10px; font-size: 13px; }
  .clause-title { font-weight: bold; }
  .clause-text { white-space: pre-wrap; color: #374151; }
  .footer { margin-top: 32px; display: grid; grid-template-columns: 1fr 1fr; gap: 20px; font-size: 13px; }
  .signature-block { border-top: 1px solid #9ca3af; padding-top: 40px; margin-top: 20px; }
  @media print {
    body { padding: 0; }
    .quote-header { break-inside: avoid; }
    table.lines tr { break-inside: avoid; }
  }
"""


def _format_total(lines: list[dict[str, Any]], total_amount: Any) -> str:
    """Render the grand total only when every line actually carries an amount.

    Two distinct wrong numbers were possible here, and only the first was caught initially:

    - No line priced at all: the snapshot total is "0.00", so the document printed
      "Total (INR) 0.00" - asserting a zero price for work that has simply not been priced.
    - SOME lines priced: the snapshot total sums only the amounts that exist, so one priced line
      at 100 alongside one unpriced line printed "Total (INR) 100.00" - a partial sum presented
      as the complete quotation total. Reachable because rate_amount is optional on an active
      line (independent review of correction pass 1, finding 2).

    Any missing active-line amount therefore prevents a numeric grand total. The two non-numeric
    outcomes are kept distinct because each is exactly true of its own case, and "Not fully
    priced" would be needlessly vague for a quotation with no prices at all.

    Derived from the lines rather than from a new snapshot key deliberately, so the canonical
    snapshot shape - and therefore every stored source_fingerprint - is unaffected.
    """
    if not lines:
        return _format_amount(total_amount)
    unpriced = count_unpriced_lines(lines)
    if unpriced == len(lines):
        return "Not priced"
    if unpriced:
        return "Not fully priced"
    return _format_amount(total_amount)


def count_unpriced_lines(lines: list[dict[str, Any]]) -> int:
    """How many snapshot lines carry no amount.

    Shared with the approval-for-issue gate in service.py, so the gate and this document's "Not
    priced" / "Not fully priced" wording can never disagree about what counts as priced.
    """
    return sum(1 for line in lines if line.get("line_amount") in (None, ""))


def _render_address_lines(address_lines: tuple[str, ...] | list[str]) -> str:
    if not address_lines:
        return "<p>-</p>"
    return "".join(f"<p>{_esc(line)}</p>" for line in address_lines)


def _render_gstins(gstins: tuple[str, ...] | list[str]) -> str:
    if not gstins:
        return "<p>GSTIN: -</p>"
    return "".join(f"<p>GSTIN: {_esc(value)}</p>" for value in gstins)


def _has_lines_in_another_currency(lines: list[dict[str, Any]]) -> bool:
    """A snapshot line names its currency only when it differs from the offer's (see
    build_quote_snapshot), so one such line means the document cannot carry a single total."""
    return any(line.get("currency_code") for line in lines)


def _currency_groups(lines: list[dict[str, Any]], offer_currency_code: str) -> list[tuple[str, list[dict[str, Any]]]]:
    """The lines by currency: the offer's own currency first, then the others alphabetically.

    Amounts in different currencies are never added together and never converted (AGENTS.md,
    "Currency"), so each group is totalled on its own.
    """
    offer_key = currency_code_key(offer_currency_code)
    groups: dict[str, list[dict[str, Any]]] = {}
    for line in lines:
        groups.setdefault(_line_currency(line, offer_currency_code), []).append(line)
    ordered = sorted(groups, key=lambda code: (code != offer_key, code))
    return [(code, groups[code]) for code in ordered]


def _line_currency(line: dict[str, Any], offer_currency_code: str) -> str:
    """A line's currency as codes are compared and shown when lines differ: trimmed and upper-cased."""
    return currency_code_key(line.get("currency_code") or offer_currency_code)


def _sum_line_amounts(lines: list[dict[str, Any]]) -> Decimal:
    return sum(
        (Decimal(str(line["line_amount"])) for line in lines if line.get("line_amount") not in (None, "")),
        start=Decimal("0.00"),
    )


def _format_line_amount(value: Any, currency_code: str | None) -> str:
    formatted = _format_amount(value)
    if currency_code is None or formatted == "-":
        return formatted
    return f"{_esc(currency_code)} {formatted}"


def _render_lines(lines: list[dict[str, Any]], offer_currency_code: str) -> str:
    # Each amount carries its currency only when the lines are in more than one; a
    # single-currency quotation is laid out exactly as it always was.
    show_currency = _has_lines_in_another_currency(lines)
    rows: list[str] = []
    for line in lines:
        line_currency = _line_currency(line, offer_currency_code) if show_currency else None
        rows.append(
            "<tr>"
            f"<td>{_esc(line.get('line_number'))}</td>"
            f"<td>{_esc(line.get('scope_description'))}</td>"
            f"<td>{_esc(line.get('equipment_service_category'))}</td>"
            f"<td class=\"numeric\">{_esc(line.get('quantity'))} {_esc(line.get('uom'))}</td>"
            f"<td class=\"numeric\">{_format_line_amount(line.get('rate_amount'), line_currency)}</td>"
            f"<td class=\"numeric\">{_format_line_amount(line.get('line_amount'), line_currency)}</td>"
            "</tr>"
        )
    return "".join(rows)


_MORE_THAN_ONE_CURRENCY_NOTE = (
    '\n  <p class="gst-note">These lines are in more than one currency. Each currency is totalled '
    "separately; no amount is converted.</p>"
)


def _render_total_rows(snapshot: dict[str, Any], lines: list[dict[str, Any]], offer_currency_code: str) -> str:
    """One total row for a single-currency quotation, as before; one per currency otherwise.

    A quotation whose lines were in more than one currency used to add them into one "Total" in
    the offer's currency - a customer-facing number that was simply wrong.
    """
    if not _has_lines_in_another_currency(lines):
        return _total_row(offer_currency_code, _format_total(lines, snapshot.get("total_amount")))
    return "\n      ".join(
        _total_row(code, _format_total(group, _sum_line_amounts(group)))
        for code, group in _currency_groups(lines, offer_currency_code)
    )


def _total_row(currency_code: str, value: str) -> str:
    return (
        "<tr class=\"total-row\">\n"
        f"        <td colspan=\"5\" style=\"text-align:right;\">Total ({_esc(currency_code)})</td>\n"
        f"        <td class=\"numeric\">{value}</td>\n"
        "      </tr>"
    )


def _render_tc_clauses(clauses: list[dict[str, Any]]) -> str:
    if not clauses:
        return "<p>No Terms and Conditions clauses are attached to this offer.</p>"
    blocks: list[str] = []
    for clause in clauses:
        blocks.append(
            "<div class=\"clause\">"
            f"<div class=\"clause-title\">{_esc(clause.get('clause_id_snapshot'))} - {_esc(clause.get('title_snapshot'))}</div>"
            f"<div class=\"clause-text\">{_esc(clause.get('clause_text_snapshot'))}</div>"
            "</div>"
        )
    return "".join(blocks)


def render_quote_html(
    snapshot: dict[str, Any],
    *,
    quote_reference: str,
    version_no: int,
    generated_at_display: str,
    prepared_by_display: str,
) -> str:
    """Render a self-contained HTML quotation document from a source-data snapshot.

    `snapshot` is the exact same canonical dict service.py hashes for `source_fingerprint` (see
    the module docstring for why). The remaining keyword arguments are facts about THIS
    generated version - never hashed, never part of the source snapshot.

    Self-contained: one inline <style>, no external stylesheet/font/image/script, so the file
    renders identically from disk with no network. `@media print` rules are included so the
    browser's own Print dialog produces a sensible page (owner decision 1: there is no
    server-side PDF renderer in this slice; the user prints this HTML to PDF).

    NOTHING MUTABLE MAY BE RENDERED HERE. The bytes are frozen at generation and never rewritten,
    so any fact this function embeds must still be true for the life of the file - which means
    true at BOTH ends of that life, not merely at the end you happen to be thinking about.

    This footnote took two corrections to get right, and both failures are worth keeping visible:

    - It first rendered the quote's workflow status, always "Draft" because generation always
      precedes approval, so an approved and issued document still told the customer it was a
      draft (independent review, correction pass 1, finding 1).
    - The replacement then asserted that issue approval "is recorded" - false for every Draft,
      which is what every document is when its bytes are frozen. Read away from the application,
      that sentence works as confirmation the quotation was approved, undermining the gate inside
      the very artifact the gate governs (independent review of correction pass 1, finding 1).

    The wording is now an instruction to verify, which is true before and after approval.
    Approval status itself lives only in the system record and the UI.

    `prepared_by_display` is safe to freeze for the opposite reason: the preparer is known at
    generation time and can never change for that version.
    """
    lines = snapshot.get("lines", [])
    tc_clauses = snapshot.get("tc_clauses", [])
    offer_currency_code = snapshot.get("currency_code") or "INR"
    if _has_lines_in_another_currency(lines):
        currency_codes = [code for code, _ in _currency_groups(lines, offer_currency_code)]
    else:
        currency_codes = [offer_currency_code]
    more_than_one_currency = len(currency_codes) > 1
    currency_label = "Currencies" if more_than_one_currency else "Currency"
    currency_value = _esc(", ".join(currency_codes))

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<title>{_esc(quote_reference)}</title>
<style>{_STYLE}</style>
</head>
<body>
  <div class="quote-header">
    <div>
      <h1>QUOTATION</h1>
      <div>PBL - Equipment Hiring</div>
    </div>
    <div class="quote-meta">
      <div><strong>Quote Reference:</strong> {_esc(quote_reference)}</div>
      <div><strong>Version:</strong> {_esc(version_no)}</div>
      <div><strong>Generated:</strong> {_esc(generated_at_display)}</div>
      <div><strong>Prepared by:</strong> {_esc(prepared_by_display)}</div>
      <div><strong>{currency_label}:</strong> {currency_value}</div>
    </div>
  </div>

  <div class="parties">
    <div class="party-block">
      <h3>Customer</h3>
      <p><strong>{_esc(snapshot.get('account_name'))}</strong></p>
      {"<p>" + _esc(snapshot.get('account_legal_name')) + "</p>" if snapshot.get('account_legal_name') else ""}
      {_render_address_lines(snapshot.get('account_addresses') or [])}
      {_render_gstins(snapshot.get('account_gstins') or [])}
    </div>
    <div class="party-block">
      <h3>Reference</h3>
      <p><strong>Offer:</strong> {_esc(snapshot.get('offer_code'))}</p>
      <p><strong>Offer Date:</strong> {_esc(snapshot.get('offer_date') or '-')}</p>
      <p><strong>Valid Until:</strong> {_esc(snapshot.get('valid_until') or '-')}</p>
      <p><strong>Customer Request Reference:</strong> {_esc(snapshot.get('customer_request_reference') or '-')}</p>
    </div>
  </div>

  <table class="lines">
    <thead>
      <tr>
        <th>#</th>
        <th>Scope / Description</th>
        <th>Equipment / Service Category</th>
        <th class="numeric">Quantity</th>
        <th class="numeric">Rate</th>
        <th class="numeric">Amount</th>
      </tr>
    </thead>
    <tbody>
      {_render_lines(lines, offer_currency_code)}
      {_render_total_rows(snapshot, lines, offer_currency_code)}
    </tbody>
  </table>
  <p class="gst-note">Amounts shown are EXCLUSIVE OF GST. GST will be determined separately at the applicable rate.</p>{_MORE_THAN_ONE_CURRENCY_NOTE if more_than_one_currency else ""}

  <div class="terms">
    <h3>Terms and Conditions</h3>
    {_render_tc_clauses(tc_clauses)}
  </div>

  <div class="footer">
    <div class="signature-block">
      <p>For PBL</p>
      <p>Authorised Signatory</p>
      <p class="prepared-by">Prepared by {_esc(prepared_by_display)}</p>
    </div>
    <div class="signature-block">
      <p>Customer Acceptance</p>
      <p>Signature &amp; Stamp</p>
    </div>
  </div>
  <p class="approval-pointer">
    Verify the current issue-approval status for this quotation in the PBL CRM system against
    quote reference {_esc(quote_reference)}. This document is a fixed record of that version and
    is never rewritten, so it does not itself display an approval status.
  </p>
</body>
</html>
"""
