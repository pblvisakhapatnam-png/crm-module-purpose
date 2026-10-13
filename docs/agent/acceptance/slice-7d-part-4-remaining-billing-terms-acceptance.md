# Slice 7D Part 4 Acceptance - extra kilometres, crew, and the holidays a Work Order names

Written so a later tester can perform regression/UAT without this session's chat history. Design,
owner answers and decisions: `docs/agent/slices/slice-7d-part-4-remaining-billing-terms.md`.

## Preconditions

Stack running. This slice adds migration `20260908_0040`; `alembic/` is baked into the backend image,
so after merging rebuild before testing:

```powershell
docker compose up -d --build --force-recreate backend
docker compose exec backend alembic current
```

Expected: `20260908_0040 (head)`. Rebuild the frontend image too (`docker compose up -d --build
frontend`): its source is not bind-mounted.

Frozen contract check, before and after:

```bash
sha256sum docs/agent/contracts/accepted-offer-to-work-order-handoff-contract.md
```

Expected: `70debad711eea67f5e8f0ff3a945c7431235ddfd97b34330beb390215cb0b86a`.

## Automated checks

| Check | Command | Expected |
| --- | --- | --- |
| Part 4 terms through the routes and the database | `docker compose exec backend pytest tests/test_slice_7d_part_4_billing_terms.py -q` | 63 passed (58 at review round 1) |
| The holiday list | `docker compose exec backend pytest tests/test_slice_7d_part_4_holidays.py -q` | 54 passed (50 at review round 1, 52 at round 2) |
| Slice 7D Parts 1 to 3 and 7C | `docker compose exec backend pytest tests/test_slice_7d_work_order_line_billing_terms.py tests/test_slice_7d_part_2_billing_terms.py tests/test_slice_7d_part_3_contract_period.py tests/test_slice_7d_part_3_contract_rules.py tests/test_slice_7c_work_order_line_detail.py -q` | all pass |
| TE-6 service surface (names added after the split pinned apart) | `docker compose exec backend pytest tests/test_te6_work_orders_service_surface.py -q` | all pass |
| Route guard (pins both new routes) | `docker compose exec backend pytest tests/test_authorization_route_migration_guard.py -q` | all pass |
| Harness cleanup and scenario | `docker compose exec backend pytest tests/test_smoke_data_harness.py -q` | all pass |
| Full backend regression, run alone | `docker compose exec backend pytest -q` | 2139 passed, 0 failed (2130 at review round 1, 2137 at round 2) |
| Migration: empty database to head, then `downgrade -1`, then head | as recorded in the continuity note | reaches `20260908_0040`; the two tables, nine columns, nine CHECKs and the reworded permission description appear and disappear with the revision; with Parts 1 to 3 billing-term rows present, those rows survive both ways (Part 4 values are dropped by the downgrade, as its docstring says) |
| Frontend typecheck, tests, build | the `AGENTS.md` sequence (prefix `MSYS_NO_PATHCONV=1` in Git Bash) | clean; 222 tests (188 before Part 4, 214 at review round 1, 216 at round 2, 219 at round 3); `workOrderHolidaysState.test.ts` added; route table unchanged |
| Full E2E suite | `pwsh -NoProfile -File scripts/run-e2e.ps1` | 17 passed, 9 skipped, 0 failed; cleanup succeeded. **Run it with `pwsh`, not `powershell`** (a BOM breaks every seed manifest under 5.1) |
| Committed-credential and fixture checks | `python scripts/check_tracked_secrets.py`, `python scripts/validate_contract_fixtures.py` | clean |

## Test data

Seed the scenario written for this screen check:

```powershell
.\scripts\smoke-data.ps1 seed -Scenario work-order-billing-terms-part-4
```

It builds a Work Order with three lines and a contract from **1 October 2026 to 30 September 2027**:

- **line 1** - a day line with every Part 1 to 3 term answered but neither extra kilometres nor crew, as
  a period saved before Part 4 would be;
- **line 2** - a shift line with every Part 4 term answered: 100 kilometres a day included at INR 45 per
  extra kilometre; 2 operators and 2 helpers per shift; INR 1,800 per extra operator and INR 900 per extra
  helper;
- **line 3** - no terms at all.

The holiday list is left unanswered, so the empty state and the first save are both seen. The output
prints the Work Order's URL. Clean up afterwards with `.\scripts\smoke-data.ps1 cleanup -RunId <run id>`.

## Manual happy path - the holidays

User `sales1` (Sales User). Open the seeded Work Order.

1. In **The Work Order**, below **Contract period**, there is a section **Holidays named in the Work
   Order**. Its badge reads **"Holidays: not answered yet"** in amber, and **Holidays in the Work Order**
   shows "Not answered yet".
2. Choose **"The Work Order names these holidays"**. Expected: "No holidays entered yet." and an **Add a
   holiday** button.
3. Click **Add a holiday** twice. In the first row enter **26 January 2027**, **National holiday**,
   "Republic Day". In the second enter **22 March 2027**, **Festival holiday**, and leave the description
   empty. Click **Save holidays**. Expected: "Holidays saved." beneath the button, and the badge reads
   **"2 holidays listed"** in green.
4. Open **Holidays in the Work Order** again. Expected: "The Work Order names no holidays" is greyed out,
   with "To record that it names no holidays, remove the dates listed first." beneath.
5. Add a holiday on **15 August 2026**, National, and save. Expected, beneath the button: **"A holiday is
   listed on 15 August 2026, before the contract starts on 1 October 2026."** Nothing is saved. Remove
   that row.
6. Add a holiday on **26 January 2027** again and save. Expected: **"26 January 2027 is listed more than
   once. List each holiday once."** Remove that row.
7. Click **Save holidays** without changing anything. Expected: "Nothing changed, so nothing was saved."
8. In **Contract period**, change **Contract starts on** to **1 February 2027** and save. Expected:
   **"The contract cannot start on 1 February 2027, because a holiday is listed on 26 January 2027."**
   Put the start back to 1 October 2026 (or reload).
9. Remove both holidays, choose **"The Work Order names no holidays"** and save. Expected: the badge
   reads **"The Work Order names no holidays"** in green - a recorded answer, not a gap.

## Manual happy path - extra kilometres and crew

10. In **Billing terms**, line 1's card reads **"Terms missing: extra kilometres, crew"**. Open it. In the
    amber **Extra charges** chapter, after **Night shift** and **Fuel**, there are two new cards,
    **Extra kilometres** and **Crew**, each tagged **Still needed**.
11. In **Extra kilometres**, choose **"A number of kilometres included per day"**. Expected: two fields,
    **Kilometres included per day** and **Rate per extra kilometre (INR)**. Enter 120 and 50.
12. In **Crew**, choose **"The Work Order states the operators and helpers"**. Expected: **Operators per
    day** and **Helpers per day**, a note that 0 means none and that these are what the customer is
    charged for, and **Crew beyond these numbers**. Enter **2** and **0**. Choose **"A rate for each
    extra operator and each extra helper"**; enter 2000 and 1000 in **Each extra operator, per day
    (INR)** and **Each extra helper, per day (INR)**.
13. Click **Save terms**. Expected: "Terms saved."; both cards tagged **Answered**; the line reads
    **"Terms complete"**.
14. Change **Operators per day** to **0** (helpers still 0) and save. Expected, beneath the button:
    **"A Work Order with no operators and no helpers has no crew. Record it as equipment only instead."**
    Put it back to 2.
15. Open **line 2**. Expected: 100 kilometres per day, INR 45 per extra kilometre; 2 operators and 2
    helpers per **shift**; INR 1800 and INR 900 per extra operator and helper per shift - the unit
    follows the line's own basis.
16. On line 2 use **Apply these terms to other lines**, tick line 3, and apply. Expected: line 3 now shows
    the same extra kilometres and crew as line 2, and reads "Terms complete".

## Manual permission check

17. Sign in as `finance1` or `readonly1` and open the same Work Order. Expected: the holidays show as a
    list (or "The Work Order names no holidays"), with no answer control, no rows to edit and no Save
    button; the billing-terms cards show the extra kilometres and crew as read-only rows.

## Not visible on screen, checked by the automated tests

- The **monthly minimum-guarantee message** (answer 26). A monthly line shows no minimum-guarantee field,
  so the corrected refusal - "a month short of the contracted hours is charged pro rata, with no
  minimum" - is only reachable through the API; `test_a_monthly_line_still_refuses_a_minimum_guarantee_with_the_corrected_reason`
  checks it.
- Removing a contract extension that would leave a listed holiday outside the contract, and a holiday on
  a day in a gap before an extension - both refused naming the dates.
- Every database CHECK, by inserting rows directly.

## Deferred, deliberately

- **Billing frequency** - recorded with equipment assignment (8A), used by invoicing (8G); answer 21.
- **Separate weekly-off and holiday rates** - withdrawn; answer 24.
- **Anything calculated** - extra-kilometre and extra-crew charges, the pro-rata monthly shortfall and
  billing a holiday are billing's (8D).
- **Marking a holiday "only these lines"** - to be added if a Work Order needs different festivals for
  different sites; nothing entered now changes when it is (decision 27).
- **Crew assignment, attendance and pay** - 8B, from PBL's HR terms, never from these numbers.

## Results

- **Independent review:** the independent reviewer, four rounds - 4, 2, 1 and 0 material findings; round 4 (authorised by
  the owner beyond the three-round cap) **ACCEPTED** with no findings, on tree
  `15d5ac5df35a65f23c25f9063ddfbbc0528163dd`, committed unchanged as `357bced`.
- **Owner's screen check, 24 September 2026: PASS**, on the seeded scenario (`WO-002658`), steps 1 to 17.
