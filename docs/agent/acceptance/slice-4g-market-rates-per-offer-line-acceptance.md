# Slice 4G acceptance - market rates per offer line

Slice record: `docs/agent/slices/slice-4g-market-rates-per-offer-line.md`. Contract: `commercial-offer-contract.md`,
"Slice 4G (11 October 2026)". Migration `20260908_0055`.

## Automated checks

Run on branch `crm/market-rates-per-line` in a port-free Compose stack (`pbl-mrpl`) with
`PASSWORD_HASH_ITERATIONS=10000`. The full backend regression and Playwright run in CI (`Required validation`).

| Check | What it covers |
| --- | --- |
| `tests/test_slice_4g_market_rates_per_line.py` | A rate needs an active line of its own offer (service and database); a rate's currency may differ from its line's; one basis rate per line, chosen with a reason; replacing it ends the earlier choice and keeps it, its reason no longer reading as current; the same rate cannot be chosen twice; the database holds one basis rate and one current choice per line; a cancelled line keeps its rates and takes no rate, choice or file; a whole-offer rate stays visible, cannot be chosen, takes no file and counts for no line; the checklist warns per line and never blocks sending; a quote attached to one rate and referred to by another line's rate, readable by Finance, attachable only by those who record rates, only as `VENDOR_QUOTE`, and not once the offer is sent; a quote reference must be a rate of the same offer and lead to an attached quote; a `VENDOR_QUOTE` refused on any other record, on both document routes; a new version's rates show the quote attached on version 1, downloadable; the stored marker refused on a line's rate; events carry the line |
| `tests/test_slice_9f_commercial_offer_versions.py` | A new version's rate is on the matching copied line, its basis choice carried over from version 1 with the same reason and time, and it refers to the rate it was copied from for its quote copy |
| `tests/test_cs05c_submitted_offer_lock.py` | Rates and basis choices refused on a sent version and allowed on a new one; a basis chosen at the same time as another writer's complete choice answered `409` by the one-open-choice rule, the other choice kept as the basis with its reason; two writers that take the offer's lock taken in turn, both choices kept |
| `tests/test_commercial_offers_api.py`, `test_work_orders_api.py`, `test_cs05a_offer_stale_save.py`, `test_operating_currency.py`, `test_cs11_commercial_offers_service_surface.py`, `test_document_upload_rights.py` | The 4D, readiness, stale-save, currency, service-surface and upload-rights rules with rates on lines |
| `tests/test_smoke_data_harness.py` | The UAT pilot data: three quotes on every line, each line with a basis rate and a recorded reason, both the lowest and a dearer choice |
| Migration | Empty database: upgrade to head, downgrade one, upgrade again |
| Frontend | `npm run typecheck`, `npm test` (Vitest, including `lineMarketRatesState.test.ts`), `npm run build` |
| Frozen handoff contract | SHA-256 `0f16ff22...cd39080` before and after |

## Manual check (about 15 minutes)

**Who**: `ops1` (Operations) to enter rates and attach quotes; `sales1` (Sales User) to choose the basis; `finance1` to
read.
**Where**: a local stack or a test site carrying this package, `/commercial-offers`.
**Data**: a Draft offer with two active lines - for example line 1 "80T crawler crane", line 2 "Manlift 18 m". A small
PNG or PDF to stand for a broker's quote.

Positive path:

1. Sign in as `ops1`. Open the offer, **Lines & Pricing**. Under line 1, open **Market rates for line 1**. Expected: "No
   market rate is recorded for this line yet." and a form **Add a rate for line 1**, its description filled from the
   line.
2. Add two rates on line 1 - vendor A 90,000 per day, vendor B 94,000 per day. Expected after each: "Rate saved on line
   1." under **Save rate**, and the rate listed under line 1 only.
3. On vendor A's rate press **Attach the quote** and upload the file as a Vendor quote. Expected: it is listed as
   "Quote copy: <file>" with **Download**.
4. Under line 2 add a rate, and in **Quote copy attached to another rate** choose "Line 1: vendor A ...". Expected: the
   line 2 rate shows the same file with "(Attached to line 1's rate)".
5. Sign in as `sales1`. On line 1's vendor A rate type a reason and press **Select as basis**. Expected: "Now the basis
   rate for line 1." beside the button; the rate shows **Basis rate** and "The basis since <time>, chosen by <name>:
   <reason>".
6. On vendor B press **Select as basis** with another reason. Expected: vendor B is the basis; vendor A no longer shows
   a current reason; **Basis history for line 1** lists vendor B as current and vendor A as "Was the basis until
   <time>, chosen by <name> on <time>: <reason>".
7. Open **Submission** and look at the readiness checklist. Expected: "Market rates and basis rate on each line" warns
   "No basis rate chosen on line(s) 2." and says it does not block anything.
8. Choose line 2's basis, record submission evidence and **Record as Submitted**. Expected: the offer is Submitted; on
   **Lines & Pricing** the rates are shown without the add form, **Select as basis** or **Attach the quote**, with the
   offer's locked note.
9. Make a new version (Submission tab). Expected: each line of version 2 shows the same rates, the basis marked
   "(carried over from version 1)", and the quote copy "(Attached to line 1's rate on version 1)".

9a. Scroll to line 2 and press **Jump to** > **Market rates**. Expected: the page goes to line 2's market rates, unfolded,
    just below the Jump to row; from line 1 it goes to line 1's (owner's screen check, 12 October 2026: the link had
    gone to the whole-offer section at the bottom of the tab).

Negative and permission path:

10. On the Draft version, press **Select as basis** with no reason. Expected: "Give the reason for choosing this rate."
    beside the button; nothing changes.
11. Cancel line 2 (Edit line, status Cancelled). Expected: line 2's rates stay listed with "This line is cancelled; its
    rates are kept as history." and no form.
12. Sign in as `finance1`. Expected: the rates, basis history and quote copies are visible and the quote downloads;
    there is no add form, **Select as basis** or **Attach the quote**.

## Deferred and known gaps

- Entering a rate and choosing the basis are still one permission; markup over the basis rate is not modelled; no rate
  master or benchmarking (`DEFERRED_REQUIREMENTS.md`).
- `.eml` and `.msg` files are not accepted uploads: an email is attached as a PDF or a picture.
- A rate cannot be edited or deleted once entered; a wrong rate is left in place and another chosen as the basis.
- The offer page's older inline styles are unchanged; only the new per-line rates panel uses the shared stylesheet.
- The per-line panel is not rendered in a frontend test: the frontend has no component-test capability yet
  (`DEFERRED_REQUIREMENTS.md`, "Frontend component-test capability"; review 4G-R1-008). Its wording is tested through
  `lineMarketRatesState.test.ts`; its behaviour by the manual check above.
