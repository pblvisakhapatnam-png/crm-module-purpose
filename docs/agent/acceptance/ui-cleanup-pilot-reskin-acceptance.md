# UI Cleanup - Pilot Reskin - Acceptance

Package record: `docs/agent/slices/ui-cleanup-pilot-reskin.md`.

## Automated checks

Recorded against the final candidate in "Verification record" at the end of this file.

```text
docker compose exec backend pytest                                   full backend regression
docker compose exec -T backend pytest tests/test_slice_9e_quotation_generation.py
docker compose exec -T backend pytest tests/test_ui_cleanup_display_names.py
frontend: npm run typecheck / npm test / npm run build (explicit source mount; see AGENTS.md)
.\scripts\run-e2e.ps1                                                Playwright
python scripts/validate_contract_fixtures.py
python scripts/check_tracked_secrets.py
python -m unittest discover -s scripts/tests
git diff --stat -- docs/agent/contracts/accepted-offer-to-work-order-handoff-contract.md   must be empty
```

## Manual checks

Setup: `docker compose exec -T backend python -m tooling.smoke_data seed --scenario uat-pilot-seeded`.
Prototype users are listed on the login page (`admin1`, `sales1`, `manager1`, `readonly1`). View at
a desktop width.

### Quotation approval

| # | Role | Steps | Expected |
| --- | --- | --- | --- |
| 1 | `manager1` | Open `UAT-Saint-Guilbert...` offer, Submission tab, Quotation and submission | No Approve button on V1. In its place: "Cannot be approved for issue: 1 active line has no rate..." |
| 2 | `manager1` | Lines & Pricing: give the unpriced line a rate. Back to Submission | V1 still has no Approve button; the reason now says the offer has changed since the version was generated |
| 3 | `sales1` then `manager1` | Generate the quotation again (V2), then look at it as `manager1` | V1 marked superseded. V2 shows the Approve button; approving it succeeds and records the approver |
| 4 | `manager1` | Open `UAT-MacDiarmid...` (Draft, V2 priced and current) | Approve button shown; no reason line |
| 5 | `manager1` | Open `UAT-Aurum...` (won, V1 approved) | Neither an Approve button nor a reason line |
| 6 | `sales1` | Any Draft version | Never an Approve button (role); the reason line, if any, is still shown so the preparer knows why |

### Reskin

For each of the six detail pages - Commercial Offer, Account, Lead, Opportunity, Work Order, Work
Order Amendment:

1. The header shows a Back link at the top left, the record type, the record's code or name, status
   badges and its actions.
2. Sections sit in labelled, coloured, boxed groups; related sections are together.
3. Long pages show a "Jump to" row; each link scrolls to its group and the row stays visible while
   scrolling.
4. No "Slice", "foundation", role code or raw event name appears in the page's own text. Text the
   backend supplies - business-event reasons and a few validation messages, such as the Work Order
   creation reason an Admin sees - may still say "Slice N"; that is a known gap, not a defect.
5. Owners and creators are shown by name, not by an `00000000-...` ID. On the Commercial Offer,
   Work Order and Work Order Amendment pages the linked Account and Opportunity show by name, with
   the reference number small beside them. On the Lead and Opportunity pages, linked records still
   read "Open Account", "Open Opportunity" or "Open Lead" with the reference beneath, and a Lead's
   qualification decision shows who decided by reference; both are known gaps.
6. Every action still works, and its success or error message appears beside its own button.

### Negative and permission paths

- `readonly1` sees the same grouped pages with no edit actions, and no Approve button anywhere.
- Approving a version with an unpriced line, or an outdated version, through the API returns `422`
  with the same reason the screen shows (automated: `test_slice_9e_quotation_generation.py`).
- The Accepted Offer -> Work Order handoff response carries no display-name field (automated:
  `test_ui_cleanup_display_names.py`).

## Known gaps, not defects

- Pages are grouped, not shortened; shortening is the post-pilot restructure.
- No component tests; the frontend still has no component-test capability.
- The owner's language pass is still to come, including about twenty backend-supplied strings
  (business-event reasons, a few validation messages) that still say "Slice N".
- Linked records on the Lead and Opportunity pages, and who decided a Lead's qualification, are
  shown by reference rather than by name.

## Verification record

Recorded 11 September 2026 against the candidate on branch `ui-cleanup` (base `40f6ff0`).

```text
Full backend regression        1327 passed, 0 failed, 638.81s
Stored document files          14 before, 14 after (absolute count)
Slice 9E module                56 passed (4 new approval tests, each seen failing first)
Mutation checks                each new approval check disabled in-process -> its test fails
Display names / Work Orders    34 passed; the frozen-handoff assertion seen failing first
Frontend                       typecheck clean; 54 tests passed; build succeeded
Playwright                     12 passed, 9 skipped (1.2m), retries 0; the 9 skipped are the
                               @demo-preflight suite, which runs only with its own manifest
Contract fixtures              all rules passed
Committed-credential check     no findings
Script unit tests              58 passed
Alembic                        20260908_0035 (head), unchanged
Frozen handoff contract        file unchanged
```

Manual: approval states checked on the Saint-Guilbert (unpriced draft), MacDiarmid (priced current
draft) and Aurum (won, approved) offers; all six detail pages walked at 1440x900 with no "Slice"
page text and no raw user IDs.

After independent review round 1 (two page corrections, one new backend test, one docstring):

```text
Display-name and Slice 9E modules   63 passed
Frontend                            typecheck clean; 54 tests passed; build succeeded
Playwright                          12 passed, 9 skipped (1.0m), retries 0
Stored document files               14
```

Backend code changed only by one docstring and one new test since the full regression, so the
affected modules were rerun rather than the whole suite. Browser: the Work Order handoff review on
the won Aurum offer shows the Account and Opportunity by name, each with its reference beneath.

After independent review round 2 (generation, the listing and approval now read the quotation
snapshot at one instant; one new backend test):

```text
Full backend regression        1329 passed, 0 failed, 570.80s
Stored document files          14 before, 14 after (absolute count)
Slice 9E module                57 passed on the final tree; the new interleaving test failed first
                               ("DID NOT RAISE") against the round-2 candidate
Playwright                     12 passed, 9 skipped (1.3m), retries 0
Contract fixtures              all rules passed
Committed-credential check     no findings
Script unit tests              58 passed
```

The frontend is unchanged since round 2, so its checks were not rerun.

After independent review round 3 (the listing reads at one instant; wording and acceptance criteria
corrected; no new test):

```text
Full backend regression        1329 passed, 0 failed, 681.91s
Stored document files          14 before, 14 after (absolute count)
Targeted modules               151 passed (Slice 9E, display names, Slice 9B hardening)
Frontend                       typecheck clean; 54 tests passed; build succeeded
Playwright                     12 passed, 9 skipped (1.6m), retries 0
Contract fixtures              all rules passed
Committed-credential check     no findings
Script unit tests              58 passed
```

Browser, on a throwaway Account: saving Sales Manager 1 as owner showed "Sales Manager 1" in the
Owner row, beside "Ownership and classification saved." Listing on the seeded pilot data: the same
approval states as before.
