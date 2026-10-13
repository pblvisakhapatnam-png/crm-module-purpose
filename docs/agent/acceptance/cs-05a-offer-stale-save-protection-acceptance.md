# CS-05a acceptance - a stale form cannot overwrite a Commercial Offer or an offer line

Slice record: `docs/agent/slices/cs-05a-offer-stale-save-protection.md`. Contract: `commercial-offer-contract.md`,
"CS-05a (9 October 2026)". Migration `20260908_0051`.

## Automated checks

Run on branch `fix/cs-05a-offer-stale-save` in a port-free Compose stack (`pbl-crm-cs05a`) with
`PASSWORD_HASH_ITERATIONS=10000`. The full backend regression and Playwright run in CI (`Required validation`), not
locally, by the owner's rule for parallel lanes. Results of each run, with commands and counts, are in
`docs/continuity/CS_05A_OFFER_STALE_SAVE_PROTECTION.md`.

| Check | What it covers |
| --- | --- |
| `tests/test_cs05a_offer_stale_save.py` (19 tests, 21 cases) | The version on both tables, the `409`, nothing written on a refusal, the order of the checks (the request schema's `422` and a final offer's refusal come first), the raises by marking submitted and by a customer response, two saves at once, the line amount from the locked line, the static guard over every writer and a self-test of its scan |
| The touched files whole | `test_commercial_offers_api.py`, `test_operating_currency.py`, `test_reports_api.py`, `test_slice_9b_pilot_hardening.py`, `test_slice_9e_quotation_generation.py`, `test_cs11_commercial_offers_service_surface.py`, `test_smoke_data_harness.py` |
| Guard tests that read edited files | `test_authorization_route_migration_guard.py`, `test_authorization_post_baseline_catalogue.py`, `test_postgresql_dialect_regression.py`, `test_business_authority_coverage_manifest.py`, `test_business_authority_e3_security_boundary.py`, `test_business_authority_security_boundary.py`, `test_business_authority_store_wiring.py`, `test_tb1_503_database_errors_carry_no_values.py`, and `test_cs04_handoff_once_per_line.py` (the handoff's locks on offer lines) |
| Undo proofs | Seven: the offer's early check; the offer's version raise; the offer's check with its guarded write; the line read locked; the line's check with its guarded write; the line's version raise; the page's "changed fields only". Each switched off makes its tests fail, and the file is restored by hash |
| Migration | Empty database: upgrade to head, downgrade one, upgrade again. Populated: an offer seeded at head (version 3 after create, submit and the customer's response) is kept through downgrade and upgrade and starts again at 1; both checks and `NOT NULL DEFAULT 1` present |
| Frontend | `npm run typecheck`, `npm test` (Vitest, including `offerEditState.test.ts`), `npm run build` |
| Playwright (CI) | `e2e/tests/offer-stale-save.spec.ts` on the core bundle's new `stale_save_target`: the offer and a line, each saved from two tabs; the second refused beside its own Save button; the first's values stand |

## Manual check - two tabs (about 10 minutes)

**Who**: `sales1` (Sales User). A second person is not needed: two browser tabs are two people.
**Where**: a local stack or a test site carrying this package (migration `20260908_0051`), `/commercial-offers`.
**Data**: any Draft offer with at least one line - for example one you create from a qualified Opportunity, with one
line of quantity 10, rate 25000.

Positive path:

1. Sign in as `sales1`. Open the offer. Copy the address into a second tab and open it there too.
2. In tab 1, press **Edit Commercial Offer / Status**, change **Remarks / requirement notes**, press **Save Commercial
   Offer**. Expected: "Commercial Offer updated successfully." under the button; the remarks are saved.
3. In tab 1 press **Edit** again and press **Save Commercial Offer** without changing anything. Expected: "Nothing has
   been changed, so there is nothing to save." under the button; nothing is recorded (the Events list has no new
   entry).

Negative path - the stale tab:

4. In tab 2 (opened before step 2, not reloaded), press **Edit Commercial Offer / Status**, change the **Offer title**,
   press **Save Commercial Offer**. Expected, directly under that button: "Someone else changed this Commercial Offer
   after you opened it, so your change was not saved. Reload the page to see their version, then make your change
   again." The form stays open.
5. Reload tab 2. Expected: tab 1's remarks are shown; tab 2's title is not saved. Edit and save the title again:
   it saves.
6. Open **Lines & Pricing** in both tabs (reload tab 1 first). Press **Edit line** on the same line in both.
7. In tab 1 change **Rate amount** to 30000 and press **Save line**. Expected: "Commercial Offer line updated." and a
   line amount of quantity x 30000.
8. In tab 2 change **Quantity** to 4 and press **Save line**. Expected, directly under that **Save line** button:
   "Someone else changed this Commercial Offer line after you opened it, so your change was not saved. Reload the page
   to see their version, then make your change again." Reload: the line has tab 1's rate and the original quantity,
   and its amount is that quantity x 30000.
9. A third tab opened before someone **marks the offer submitted** (Submission tab) cannot then withdraw it from its old
   edit form: its save is refused the same way.

Permission path: sign in as `finance1` (view only): the edit buttons are not offered; a direct `PUT` is `403`, as
before (covered by the API tests).

Record: tester, date, site and build, Pass / Pass with minor issues / Fail, and any wording that confused.

## Results

| Check | Result |
| --- | --- |
| Manual two-tab check | **Not yet run.** This package was built overnight in a lane whose stack publishes no ports (the owner's rule for parallel lanes), so no browser could reach it; the Playwright spec above is the UI proof in CI. To be run by the owner or a tester on the first build that carries it |
| Automated checks | See the continuity note |

## Deferred and known gaps

- A write that bypasses the application (direct SQL) does not raise a version; the static guard covers the
  application's own writers only.
- An identical save that a caller other than the page sends is still recorded as an edit and raises the version (the
  page itself no longer sends one).
- The submitted-offer lock, the one-Base-Offer database rule and the double-click messages are the next package
  (owner's decisions of 9 October 2026, `NEXT_STEPS.md`). Accounts, Leads, Opportunities, Work Order amendments and
  interactions are CS-05b: testers keep the "never edit one record in two tabs" instruction for those.
