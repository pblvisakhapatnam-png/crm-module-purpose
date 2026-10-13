# CS-05c acceptance - a submitted offer changes only through a revision; one active Base Offer; duplicates answered

Slice record: `docs/agent/slices/cs-05c-submitted-offer-lock.md`. Contract: `commercial-offer-contract.md`, "CS-05c
(10 October 2026)". Migration `20260908_0053`.

## Automated checks

Run on branch `fix/cs-05c-submitted-offer-lock` in a port-free Compose stack (`pbl-crm-cs05c`) with
`PASSWORD_HASH_ITERATIONS=10000`. The full backend regression and Playwright run in CI (`Required validation`), not
locally, by the owner's rule for parallel lanes. Results of each run, with commands and counts, are in
`docs/continuity/CS_05C_SUBMITTED_OFFER_LOCK.md`.

| Check | What it covers |
| --- | --- |
| `tests/test_cs05c_submitted_offer_lock.py` | Every content writer refused on a submitted offer without an open revision and allowed with one; refused again after the revision is resubmitted or cancelled; a final offer refused with a revision left open; mark-submitted against a line cancellation and a credit hold, both orders; a change against a revision's cancel, both orders; a double attach; each of the four database rules reached by a writer that skips the lock and answered `409`/`422`, logged without the key; only the named rules answered; the index's definition and statuses; what the database refuses; the migration's stop |
| The touched files whole | `test_commercial_offers_api.py`, `test_slice_9b_pilot_hardening.py`, `test_smoke_data_harness.py`, `test_cs11_commercial_offers_service_surface.py`, and the offer files the change reaches: related offers, 9E quotations, CS-05a, CS-04, Work Orders, amendments, reports, currency, display names, upload rights |
| Guard tests that read edited files | route migration guard, PostgreSQL dialect, the authority guards that scan every module, TB1-405 (a failing migration stops the start), TB1-500 event payloads, TB1-503 database errors (reads `app/core/errors.py`), 9C storage, upload limits, and the harness files that build submitted offers |
| Undo proofs | Nine: the submitted-offer rule; closing a revision under the offer's lock; each of the four answers; the `409` on select-basis; logging without the database's text; only named rules answered. Each switched off makes its tests fail; the file is restored and checked by SHA-256 |
| Migration | Empty database: upgrade to head, downgrade one, upgrade again (the index present at head, absent at `0052`). Bad data: at `0052`, two active Base Offers on one Opportunity; the upgrade stops naming both, changing nothing; withdraw one, and it upgrades |
| Frontend | `npm run typecheck`, `npm test` (Vitest, including `offerStatus.test.ts`), `npm run build` |
| Playwright (CI) | `e2e/tests/submitted-offer-lock.spec.ts` on the core bundle's new `submitted_lock_target`: the lines locked with the note, a revised offer started, the lines open |

## Manual check (about 15 minutes)

**Who**: `sales1` (Sales User); `ops1` (Operations) for the pricing step.
**Where**: a local stack or a test site carrying this package (migration `20260908_0053`), `/commercial-offers`.
**Data**: a Draft offer on a qualified Opportunity with an Account, with one line and one market rate - or the
`submitted_lock_target` record of a `core-regression-bundle` run, already submitted (start at step 3).

Positive path:

1. Sign in as `sales1`. Open the offer. On **Lines & Pricing** add a line: it saves (a Draft offer is open).
2. On **Submission**, record submission evidence, then **Record as Submitted / Commercially Committed**. The status reads Submitted.
3. Open **Lines & Pricing**. Expected: no **Add Commercial Offer line** form, no **Edit line** button, and in their place
   "This offer is Submitted, so its lines, prices, T&C, credit reviews and submission evidence change only through a
   revised offer. Start a revised offer on the Submission tab, make the change, record how the revised offer was sent,
   then mark it as re-sent." The same note stands in for the pricing, T&C, credit-review and submission-evidence forms.
4. On **Submission**, under **Revised offers**, press **Start revised offer**. Expected: "Revised offer started. ...";
   the panel says the offer's lines, prices, T&C, credit reviews and submission evidence can be changed until it is
   marked as re-sent or cancelled, and that cancelling does not undo a change.
5. On **Lines & Pricing**, change the line's rate and add a line: both save. Sign in as `ops1` and add a market rate:
   it saves.
6. On **Submission**, record submission evidence for the revised offer, then press **Mark as re-sent** on the revised
   offer, choosing that evidence. Expected: the forms of step 3 give way to the note again.

Negative path:

7. Start another revised offer, change nothing, and press **Cancel revision**: the note returns. Start one, add a line, cancel it:
   the note returns and the added line stays (cancelling records history; it does not undo).
8. On another Opportunity that already has an active offer, try to create a second offer: refused, naming the existing
   offer, as before.
9. A double click on **Attach T&C clause** on a Draft offer: one attachment; any second answer says the clause is
   already attached - never "Internal Server Error".

Permission path: `finance1` (view only) sees no edit forms on any offer, as before; a direct write is `403` (covered by
the API tests).

Deploying: the migration stops, changing nothing, if any Opportunity already has two active Base Offers - its message
names them. Withdraw or close the one that should not be active, then deploy again.

Record: tester, date, site and build, Pass / Pass with minor issues / Fail, and any wording that confused.
