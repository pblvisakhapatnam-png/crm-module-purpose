# Slice 4G - Market rates per offer line

Status: merged 11 October 2026 (pull request #121, merge commit `76506851`; reconciled 12 October 2026 - this line read
"in progress"). Branch `crm/market-rates-per-line`, started 11 October 2026. Migration `20260908_0055`.

## Why

Slice 4D recorded market rates (pricing evidence) against the whole Commercial Offer, with one basis rate per offer
(a partial unique index on `is_selected_basis` per offer, migration `20260705_0018`). An offer with a crawler crane and
a manlift could not record a basis for each. The owner asked on 11 October 2026 for each offer line to hold its own
market rates and its own basis rate; both test sites' testers wait on it and on the rewritten CRM test pack.

## Owner's answers (11 October 2026)

1. **The checklist warns; it does not block.** Recording the offer as sent never waits for a basis rate. The
   readiness checklist names each active line with no market rate, and each with rates but no basis rate.
2. **Rates are entered per line.** Vendors never give one combined price for two lines, but the same crane on two
   lines (two sites) may carry the same quoted rate from one quote: it is entered on each line. A broker's quote
   arrives as a WhatsApp screenshot, an email, or a PDF or Word document, and is attached to the rate. When one
   document covers several lines, it is attached to one line's rate, and the other lines' rates refer to that rate
   for the copy.
3. **A basis rate is never removed, only replaced.** Choosing another rate on the line needs a reason; the earlier
   choice becomes history. Each line shows its basis history - which rate, who chose it, when and why - on the line
   itself, and an earlier choice reads as past ("Was the basis until <date>, chosen by <name>: <reason>"). Nothing
   about an earlier choice is overwritten or deleted.
4. **A rate's currency may differ from its line's.** Each rate shows in its own currency; nothing is converted
   (Q-08).

Everything else as recommended: see "Engineering decisions" (ADR-023).

## Out of scope (unchanged)

- Who may enter a rate versus choose the basis (`DEFERRED_REQUIREMENTS.md`, "Entering a market rate and choosing the
  basis rate are one permission").
- Markup over the basis rate ("Markup over the basis rate is not modelled at all").
- The rate master and benchmarking.
- Quotation documents keep excluding pricing evidence; the quote snapshot fingerprint is unaffected.
- The Work Order handoff copies no pricing evidence and must not start (the frozen handoff contract's "Pricing
  evidence reference - include where available" stays unimplemented).

## Engineering decisions (ADR-023)

**Data (migration `20260908_0055`).**

- `crm_commercial_offer_pricing_evidence` gains `commercial_offer_line_id` (nullable) and `recorded_for_whole_offer`
  (boolean). The migration sets `recorded_for_whole_offer = TRUE` on every existing row and leaves its line empty;
  a check holds `(commercial_offer_line_id IS NULL) = recorded_for_whole_offer`, so a new rate without a line is
  refused by the database as well as the service. Rates recorded before this change are never deleted, never moved
  and never guessed onto a line.
- The line must belong to the rate's own offer: a composite foreign key `(commercial_offer_line_id,
  commercial_offer_id)` to `crm_commercial_offer_line (id, commercial_offer_id)`, backed by a new unique constraint on
  the line table.
- The per-offer index `ux_crm_commercial_offer_pricing_evidence_one_selected` is replaced. A line's basis is its open
  choice in the history table below, one per line; a check refuses the stored marker on a line's rate, so the marker
  and the history can never disagree (review 4G-R1-002). The whole-offer rates keep at most one selected per offer
  (`..._one_whole_offer_basis`), the guarantee they had.
- A new table `crm_commercial_offer_line_basis_choice` is the line's basis history: the rate chosen, who chose it,
  when, the reason (required), when the choice ended and who ended it, and - for a new version - the choice it was
  carried over from. A partial unique index allows one open choice per line. Ending a choice only fills its end
  columns; no row is deleted or rewritten.
- `quote_copy_evidence_id` (nullable, self-reference) names the rate whose attached document holds this rate's quote
  ("the other lines refer to this line for the attachment"). The database lets a rate refer only to a rate entered
  before it (a smaller id), so a chain of references always ends and cannot loop, however long (review 4G-R3-001).
- The API still answers `is_selected_basis` and `selection_reason` per rate: for a line's rate both are derived from
  the line's open choice; the stored columns are kept only for the whole-offer rates recorded before this change.
- A quote reference must lead to a rate whose quote is attached (its own or one it refers to), checked under the
  offer's lock (review 4G-R1-004).

**API.** `POST /api/commercial-offers/{id}/pricing-evidence` requires `line_public_id` (an active line of the same
offer) and accepts `quote_copy_rate_public_id` (another rate of the same offer). The list response gains, per rate:
`line_public_id`, `line_number`, `line_status_code`, `recorded_for_whole_offer`, `quote_copy_rate_public_id`,
`quote_copies` (the attached documents, its own and those it refers to, each with where it is attached) and
`basis_history` (every choice of this rate, with who, when, why and when it ended). `selection_reason` in the response
is the current choice's reason, and empty when the rate is not the basis. Selecting the rate that is already the basis
is refused (`422`).

**Attachments.** A new linked record type `commercial_offer_market_rate` in both maps of `documents/contract.py`:
reading needs `COMMERCIAL_OFFER_READ`, attaching `COMMERCIAL_OFFER_PRICING_EVIDENCE_WRITE`, as for the offer. A new
document type `VENDOR_QUOTE`. Commercial Offers registers an attach check (ELG-1's pattern): it refuses any type but
`VENDOR_QUOTE`, a link to a file kept elsewhere, a rate recorded for the whole offer, a rate on a cancelled line, and
a rate on a version that can no longer change (CS-05c/9F); it takes the offer's lock. An email is attached as a PDF or
a screenshot: `.eml` and `.msg` are not accepted uploads today and are not added here. The documents module refuses a
`VENDOR_QUOTE` filed against any other linked record type, on both routes (review 4G-R1-001).

**Versions (Slice 9F).** `copy_commercial_offer_version_children` copies each active line's rates onto the matching
copied line, its current basis choice as an open choice carried over from the earlier one, and whole-offer rates as
they are. Each copy is linked to the rate it was copied from by its own column (`copied_from_evidence_id`, with the
source offer), which the database holds to the offer the version was made from; a user's quote reference is held to
the same offer (review 4G-R4-005). The quote copy is found through either link, so the attachment stays where it was
filed (9F leaves documents on the earlier version) and still shows; a copy carries no user reference (4G-R2-001). The earlier choices' history stays on the
earlier version.

**Inactive line.** The screen calls an inactive line "Cancelled", so the wording follows it. Its rates and basis
history stay on it and are shown, read-only, under the note "This line is cancelled; its rates are kept as history." No rate, basis choice or attachment is added while it is inactive. As
before, a new version does not copy inactive lines, so their rates stay on the earlier version.

**Jump to (owner's screen check, 12 October 2026).** The tab's **Jump to** > **Market rates** goes to the market rates
of the line nearest what is on screen - the first panel whose start is on screen, else the one the screen is inside,
else the nearest - and unfolds it; the first line's panel carries the link's id. The shared `SectionIndex` takes an
optional `target` for this. The section at the bottom of the tab, now only the whole-offer rates and a note, is no
longer a Jump to target.

**Events.** Market rate added, historical rate added and basis rate selected carry `line_public_id` and
`line_number`; a basis change also carries the rate it replaced.

**Locks.** Every write takes `_lock_offer_for_content_change`, so rates stay unchangeable on a Submitted, Revised or
Abandoned version (CS-05c, 9F); CS-05a's stale-save `409` on offer and line saves is untouched.

## Authority and required reading

- `docs/agent/contracts/commercial-offer-contract.md` (4D, 4E, CS-05a, CS-05c, 9F sections)
- `docs/agent/slices/slice-4d-commercial-offer-rate-basis-pricing-evidence-foundation.md` and its acceptance record
- `docs/agent/slices/slice-4e-commercial-offer-line-items-scope-foundation.md`
- `docs/agent/slices/cs-05a-offer-stale-save-protection.md`, `cs-05c-submitted-offer-lock.md`,
  `slice-9f-commercial-offer-versions.md`
- `docs/agent/contracts/documents.md` ("Record-scoped write rights", "A machine certificate's copy (ELG-1)")
- `docs/agent/contracts/accepted-offer-to-work-order-handoff-contract.md` (frozen; hash checked before and after)
- `docs/agent/DEFERRED_REQUIREMENTS.md` (the two 4D entries named above)
- ADR-007, ADR-013, ADR-023, ADR-028

## Progress

- [x] Owner's questions answered; design recorded (this file).
- [x] Migration 0055, checked on an empty database.
- [x] Backend: repository, service, schemas, routes, attach check, readiness, version copy, events.
- [x] Backend tests (4D, readiness, CS-05a, CS-05c, 9F, smoke data, new per-line tests).
- [x] Smoke data: builders, scenarios (incl. `uat-pilot-seeded`), cleanup.
- [x] Frontend: Lines & Pricing per line.
- [x] Records: contract, 4D dated sections, acceptance checklist, MCF row if touched, NEXT_STEPS, continuity note.
- [x] CRM test pack (`docs/uat/`), Feedback Log, PDFs.
- [x] Walk the rewritten steps on the lane stack (27 of 27; see the continuity note).
- [x] PR #121 opened; reset steps and TE-8 note name it.
- [ ] review rounds (up to 3); merge on the owner's word.
