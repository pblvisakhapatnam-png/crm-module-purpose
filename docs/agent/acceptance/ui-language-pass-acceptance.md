# UI Language Pass and Tester Guide - Acceptance

Package record: `docs/agent/slices/ui-language-pass.md`. Branch `ui-language-pass`, base `8b7b5ff`.

## Commands

```text
docker compose exec backend pytest                                                 backend regression
docker compose run --rm --no-deps -v "${PWD}/frontend:/app" -v /app/node_modules frontend npm run typecheck
docker compose run --rm --no-deps -v "${PWD}/frontend:/app" -v /app/node_modules frontend npm test
docker compose run --rm --no-deps -v "${PWD}/frontend:/app" -v /app/node_modules frontend npm run build
.\scripts\run-e2e.ps1                                                              Playwright
python scripts/validate_contract_fixtures.py
python scripts/check_tracked_secrets.py
python -m unittest discover -s scripts/tests
```

## Acceptance checks

| # | Check | How it was checked |
| --- | --- | --- |
| 1 | The six terms the owner listed read as agreed | The rendered Commercial Offer Submission tab and Work Order page |
| 2 | A Work Order's status reads "Awaiting release to Ops" wherever it is shown, and the code `HANDOFF_CREATED` is unchanged | Dashboard, Work Order page and Commercial Offer page; the diff |
| 3 | No "Work Order shell", "Slice N", "prototype" or "foundation" wording in page text or in backend messages users see | A sweep of frontend strings and backend string literals. The wording still to consider is listed in `docs/agent/UI_UX_CARRY_FORWARD.md` |
| 4 | No behaviour change | The backend diff is string literals only; the frontend diff is strings plus the display formatters the package record names |
| 5 | The frozen handoff contract is unchanged | `git diff --stat` on the contract file is empty |
| 6 | The tester guide exists in the repository and as a shareable page | `docs/uat/PBL_CRM_TESTER_GUIDE.md`, and a private published page |
| 7 | A tester can follow the practice data sheet | Each step checked against the code it depends on; five steps corrected, see the package record |
| 8 | The regression suites pass | The commands above; results below |

## Results - first candidate

```text
Full backend regression        1329 passed, 0 failed, 601.19s
Stored document files          14 before, 14 after the full regression
Frontend                       typecheck clean; 54 tests passed; build succeeded
Playwright                     1 failed: accepted-offer-handoff (below)
Contract fixtures              all rules passed
Committed-credential check     no findings (879 files in the proposed tree)
Script unit tests              58 passed
Alembic                        current == heads == 20260908_0035 (no migration)
Frozen handoff contract file   unchanged
```

The Playwright failure was the language pass's own. The Commercial Offer page had reworded "No
Work Order has been created yet from this Commercial Offer.", which two specs check word for word
and which the Create Work Order page kept. The fix restored the sentence on the Commercial Offer
page rather than loosening the check, so both pages say the same thing again. The same correction
reworded the submission-readiness items for revised offers and for the Account and Opportunity
links, and updated the backend assertions that quoted them.

## Results - after the correction

```text
Full backend regression        1328 passed, 1 failed, 592.51s
                               the failure: test_commercial_offers_api.py:2784 still checked the old
                               revised-offer readiness message ("Open revision exists"); updated to
                               the new wording at the same strength
Commercial Offer API module    46 passed after that update, 112.54s (backend code unchanged since
                               the full run)
Stored document files          14 before, 14 after the full regression
Frontend                       typecheck clean; 54 tests passed; build succeeded
Playwright                     12 passed, 9 skipped (59.5s), retries 0; the 9 skipped are the
                               @demo-preflight suite, which runs only with its own manifest
Contract fixtures              all rules passed
Committed-credential check     no findings (882 files in the proposed tree)
Script unit tests              58 passed
Alembic                        current == heads == 20260908_0035 (no migration)
Frozen handoff contract file   unchanged
```

## Results - after independent review round 1

The four round-1 corrections changed a page subtitle, one test assertion and documentation only.
No backend code changed, so the full backend regression above stands.

```text
Commercial Offer API module    46 passed, 201.89s
Frontend                       typecheck clean; 54 tests passed; build succeeded
Playwright                     12 passed, 9 skipped (1.3m), retries 0
Contract fixtures              all rules passed
Committed-credential check     no findings (882 files in the proposed tree)
Script unit tests              58 passed
Frozen handoff contract file   unchanged
```

## Results - after independent review round 2

The round-2 correction changed the Commercial Offer page's status panel - the "Ready to create the
Work Order" row checks for an existing Work Order first, and "Commercially active" shows "No" rather
than "No - closed" - and documentation. No backend code changed.

```text
Frontend                       typecheck clean; 54 tests passed; build succeeded
Playwright                     12 passed, 9 skipped (1.2m), retries 0
Contract fixtures              all rules passed
Committed-credential check     no findings (882 files in the proposed tree)
Script unit tests              58 passed
Frozen handoff contract file   unchanged
```

## Results - after independent review round 3

The round-3 correction changed page text on the Commercial Offers list, the dashboard and the
Commercial Offer page, so that no page says approvals are not built while quotation approval for
issue is. No backend code changed.

```text
Frontend                       typecheck clean; 54 tests passed; build succeeded
Playwright                     12 passed, 9 skipped (58.2s), retries 0
Contract fixtures              all rules passed
Committed-credential check     no findings (882 files in the proposed tree)
Script unit tests              58 passed
Frozen handoff contract file   unchanged
```

## Independent review outcome

Round 4 (packet `902afba6`), which the owner directed beyond the three-round cap: ACCEPTED with no
findings, on candidate tree `7eb4b1e1`. Committed as `4dd3edf` with that exact tree and merged
through PR #35 as `22ba9fc`; Required validation passed on the pull request and on `main`.
Recorded here by the next package, because the commit had to reproduce the reviewed tree.

## Manual checks

In the browser at 1440x900, with the `uat-pilot-seeded` practice data (run `te1-db263f13`,
cleaned up afterwards) and signed in with the prefilled demo login:

- Dashboard: statuses read as words ("New", "Draft", "Submitted"), the Purpose column reads "Base"
  and "Change Quotation", and every Work Order reads "Awaiting release to Ops".
- Work Order page (UAT-Aurum Infra Projects): one status, "How this Work Order was created", a
  plain business-event reason, and the "Later steps" list in the guide's order.
- Commercial Offer Overview tab: "Submitted - not set here", and the not-built list without
  "deferred" or "shell".
- Commercial Offer Submission tab of an accepted offer without a Work Order, as rendered in the
  Playwright failure snapshot: "Before you create the Work Order", the four relabelled status rows,
  "Revised offers", "Start revised offer", and "Not built yet" badges.

Screenshots timed out in the hidden browser pane, so these checks were made on the page text.

## Known gaps

Listed in `docs/agent/UI_UX_CARRY_FORWARD.md`, "Language pass (September 2026)".

One of them is more than wording: no screen lets a tester upload a file against a chosen customer
or offer, because the Documents page's upload box always files to one fixed sample Account. The
data sheet's Step 12 now checks the stored quotation files instead, and uploading is listed as not
built yet. The owner decided on 11 September 2026 to build an upload control before the pilot, as
its own package after this one.
