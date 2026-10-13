# Slice 7D Part 1 Acceptance - Work Order Line Billing Terms

Written so a later tester can perform regression/UAT without this session's chat history. Design
and owner decisions: `docs/agent/slices/slice-7d-work-order-line-billing-terms.md`.

## Preconditions

Stack running. This slice adds migration `20260908_0037`; `alembic/` is baked into the backend
image, so after merging rebuild before testing:

```powershell
docker compose up -d --build --force-recreate backend
docker compose exec backend alembic current
```

Expected: `20260908_0037 (head)`. Rebuild the frontend image too (`docker compose up -d --build
frontend`): its source is not bind-mounted.

Frozen contract check, before and after:

```bash
sha256sum docs/agent/contracts/accepted-offer-to-work-order-handoff-contract.md
```

Expected: `70debad711eea67f5e8f0ff3a945c7431235ddfd97b34330beb390215cb0b86a`.

## Automated checks

| Check | Command | Expected |
| --- | --- | --- |
| Slice 7D Part 1 tests | `docker compose exec backend pytest tests/test_slice_7d_work_order_line_billing_terms.py -q` | 122 passed (Part 2 changed four expected missing-item lists, not the count) |
| Slice 7C tests (basis and hours moved out) | `docker compose exec backend pytest tests/test_slice_7c_work_order_line_detail.py -q` | all pass |
| Harness cleanup of line detail and billing terms | `docker compose exec backend pytest tests/test_smoke_data_harness.py -q -k billing_terms` | 1 passed |
| Route guard (pins all four new routes) | `docker compose exec backend pytest tests/test_authorization_route_migration_guard.py -q` | all pass |
| Full backend regression, run alone | `docker compose exec backend pytest -q` | recorded in the continuity note |
| Migration: 0036 with 7C rows -> 0037 -> `downgrade -1` -> head | scratch database, as recorded in the continuity note | basis and hours carried into period 1 and back; upgrade refused while a row holds hours with no basis |
| Frontend typecheck, tests, build | the `AGENTS.md` sequence (prefix `MSYS_NO_PATHCONV=1` in Git Bash) | clean; `workOrderBillingTermsState.test.ts` added; route table unchanged |
| Full E2E suite | `.\scripts\run-e2e.ps1` | no failures |
| Committed-credential and fixture checks | `python scripts/check_tracked_secrets.py`, `python scripts/validate_contract_fixtures.py` | clean |

## Test data

Any accepted Commercial Offer with a Work Order that has at least one line. Nothing is needed on the
Account for this slice.

## Manual happy path - a monthly line (the Annexure-10 month example)

User `sales1` (Sales User). Start at `/work-orders/{id}`.

1. In **Lines**, the **Site and billing** column shows a second badge, "Terms missing: no terms yet".
2. Scroll to **Billing terms**. The line's card is open and reads "No billing terms have been
   recorded for this line yet." Click **Start billing terms**. Expected: "Billing terms started for
   this line." beneath the button, and an empty period "From contract start" with a Billing basis
   selector.
3. Choose **Month**. The form shows contracted hours per month, working days per month, the Work
   Order rate, working days and off days, overtime, breakdown, idle time and part month - and no
   minimum guarantee. Enter: 260 hours, 26 days, rate 100000; tick "The Work Order states the weekly
   off days" and tick Sun; off-day work charged at **Overtime rate**; overtime **% of the normal
   rate**, 125; overtime hours counted **Hours the machine was available**; counted **Over the whole
   month, after contracted hours**; breakdown **Reduce the billed hours pro rata**; idle time **Paid
   as working hours**; part month **Calendar days in that month**. Click **Save terms**.
4. Expected: "Terms saved." beneath the button; the period badge reads "Complete"; the card and the
   Lines column read "Terms complete"; the Lines column reads "Billed by month"; the helper text under
   working days reads "That is 10.00 hours a working day, as last saved."
5. Quoted rate: the line reads "Quoted on the offer: INR ... per ..." with the offer's rate, which is
   unchanged by the rate you entered.

## Manual happy path - periods

6. Under the card, enter a start date two months ahead in **A later period starts on** and click
   **Add a later period**. Expected: "Later period added."; a second period "From <date>" with the
   same terms; the first period now reads "From contract start to <day before>".
7. Change the second period's rate and save. Expected: "Terms saved."; the first period is unchanged.
8. On the second period click **Remove this period**. Expected: "Period removed." below the remaining
   period, where the removed period's button was; one period left, with no end date. The first period
   has no Remove button.

## Manual happy path - an hourly line

9. On a line with no terms, start terms and choose **Hour**. Expected: only the rate, idle time and
   minimum guarantee appear. Enter a rate, idle time **Paid as working hours**, minimum guarantee
   **Not in the Work Order**. Save. Expected: complete.

## Negative and permission checks

10. On a Shift period, choose overtime **Rate per hour** and leave the rate empty. Save. Expected:
    "Enter the overtime rate per hour." beneath Save terms, nothing saved.
10a. On a Shift period with off-day work charged at the **Overtime rate**, set overtime to **Not in the
    Work Order** and save. Expected: refused, with a message that off-day work cannot be charged at the
    overtime rate when overtime is not in the Work Order.
11. Add a later period with no date. Expected: "A later period needs the date it starts from."
11a. Start billing terms on a line whose offer has a quoted rate and choose a basis. Expected: the Work
    Order rate field fills in with the quoted rate and reads "Filled in from the quoted rate"; nothing is
    saved until Save terms.
11b. While a save on a line is in progress, every button on that line is disabled.
11c. Click **Add a later period** with no date so its error shows, then save a period on the same line.
    Expected: the error under Add a later period disappears when the save starts; only "Terms saved."
    remains.
11d. After the first save, **Start billing terms** does not return, even if every term is cleared and
    saved: period 1 is corrected in place, never removed (owner decision, screen check).
12. Two browser tabs on the same Work Order: save a change in one, then save a different change in the
    other. Expected in the second: "These terms have changed since the page loaded. Reload to see the
    latest version." (Part 2 reworded this: your own refresh can cause it, so it no longer blames
    someone else.)
13. Sign in as `finance1`. Expected: the Billing terms section shows each period read-only, with no
    Start, Save, Add or Remove buttons. The API refuses writes with `403` (covered by tests).
14. Site and billing details (7C section): there is no billing basis or hours field any more.

## Deferred and known manual gaps

- Night/second shift, mobilisation, demobilisation and fuel terms: Part 2.
- Locking terms at mobilisation or once billed; release (7B) refusing incomplete terms.
- Nothing is calculated; the Annexure-10 examples are tested as recordable term sets only. Billing/
  Finance UAT must still compare every implemented formula with Annexure-10 before billing goes live
  (`WBT-001`).
- The manual checks above cannot be performed from the implementation session (browser sign-in is not
  possible there); they are owed by the project owner's screen check.
- Carried to Part 2 and **closed there**: navigating between Work Orders while one is loading, or
  pressing Refresh while a save is in flight, could leave a stale screen or read-only billing terms until
  reload (review round 5). Part 2 item 1 fixes it; check it with steps P2-9 and P2-10 below.


---

# Slice 7D Part 2 Acceptance - Night Shift, Mobilisation, Demobilisation and Fuel

Part 2 also closes the page-load defect Part 1 carried forward. Design and owner decisions 8-12:
the "Part 2" section of `docs/agent/slices/slice-7d-work-order-line-billing-terms.md`.

## Preconditions

Part 2 adds migration `20260908_0038`. After merging, rebuild the backend (`alembic/` is baked into the
image) and the frontend (its source is not bind-mounted):

```powershell
docker compose up -d --build --force-recreate backend
docker compose exec backend alembic current
docker compose up -d --build frontend
```

Expected: `20260908_0038 (head)`. The frozen contract hash is unchanged:
`70debad711eea67f5e8f0ff3a945c7431235ddfd97b34330beb390215cb0b86a`.

## Automated checks

| Check | Command | Expected |
| --- | --- | --- |
| Slice 7D Part 2 tests | `docker compose exec backend pytest tests/test_slice_7d_part_2_billing_terms.py -q` | 100 passed |
| Slice 7D Part 1 and 7C tests | `docker compose exec backend pytest tests/test_slice_7d_work_order_line_billing_terms.py tests/test_slice_7c_work_order_line_detail.py -q` | all pass; with Part 2, 259 passed |
| Full backend regression, run alone | `docker compose exec backend pytest -q` | recorded in the continuity note |
| Migration: 0037 with Part 1 rows -> 0038 -> `downgrade -1` -> head | scratch database, as recorded in the continuity note | new columns null on existing rows; downgrade drops them |
| Frontend typecheck, tests, build | the `AGENTS.md` sequence (prefix `MSYS_NO_PATHCONV=1` in Git Bash) | clean; `workOrderPageState.test.ts` added |
| Full E2E suite | `.\scripts\run-e2e.ps1` | no failures |
| Committed-credential and fixture checks | `python scripts/check_tracked_secrets.py`, `python scripts/validate_contract_fixtures.py` | clean |

## Manual checks - the new terms

User `sales1`. Start at `/work-orders/{id}` on a line whose terms were recorded under Part 1, or a new one.

P2-1. Open **Billing terms** on a Shift or Month line. Expected: the line's badge now also reports the
   new terms as missing - "Terms missing: night shift, mobilisation, demobilisation, fuel" - because they
   were never recorded. Three new groups appear in the first period's form: **Night shift**, **Fuel**, and
   **Mobilisation and demobilisation (for the whole line)**.

P2-2. Night shift: choose **Rate per night shift**, enter 9000, and enter 8 contracted hours per night
   shift. On a **Month** line the form also asks for night-shift working days per month. Save. Expected:
   "Terms saved."; the night-shift rows appear in the saved view; the helper text says overtime,
   breakdown, idle time and off-day work follow the terms above.

P2-3. Night shift on an **Hour** line: the Night shift group does not appear at all.

P2-4. Choose night shift **Not in the Work Order**. Expected: the hours field disappears, and after
   saving the badge no longer lists "night shift" - a recorded answer, not a gap.

P2-5. Fuel: choose **Supplied by PBL and charged**, then **At an agreed rate per litre**, and enter
   95.50. Save. Change it to **Supplied by the customer**, enter 12 litres per working hour, choose **A
   number of litres per travel hour** and enter 8. Save. Expected: both save; the rate per litre no longer
   appears once the customer supplies the fuel.

P2-6. Mobilisation: choose **Charged, credited back if the machine stays beyond a number of months**,
   enter 150000 and 12 months. Demobilisation: **Not charged if the machine stays beyond a number of
   months**, 120000 and 12. Save. Expected: "Terms saved.", and with every other term answered the badge
   reads "Terms complete".

P2-7. Add a later period. Expected: the new period copies the night shift and fuel, and has **no**
   mobilisation or demobilisation group at all - they belong to the line's first period. The first period
   still shows them.

P2-8. Leave a month count empty: choose "credited back after..." and save with no months. Expected: it
   saves, and the badge lists "mobilisation" as missing (a value still needed is missing, not refused).
   Enter 12 and save; the badge clears.

## Manual checks - the page shows only its latest load (item 1)

P2-9. Open a Work Order, then immediately click a link to another Work Order (or use the browser's Back
   and Forward quickly). Expected: the page never shows the first Work Order's code, lines or terms under
   the second one, and the second Work Order's own billing terms become editable normally.

P2-10. Save a period, and while "Saving..." is showing click **Refresh** in the page header. Expected:
   the page reloads and the billing terms become editable again without a further reload - they do not
   stay read-only. The save itself still reached the server: the reloaded terms show it, or the next save
   on that line says "These terms have changed since the page loaded. Reload to see the latest version."

## Carried from Part 1 - the owner's re-check

P2-11. Part 1's stale-message fix, deferred to this screen check: perform **steps 11c and 11d** of the
   Part 1 checklist above.

## Deferred and known manual gaps

- Nothing is calculated. Mobilisation invoices and credit notes, demobilisation billing, fuel variance
  and night-shift pay belong to the billing slices; `WBT-001` still requires Billing/Finance UAT against
  Annexure-10 before billing goes live.
- How the credit-back and waiver months are counted (owner decision 9) and how customer-supplied fuel
  excess is measured (decision 12) are the billing slices' to define.
- Separate overtime or breakdown rules for a night shift are not offered; add a choice when a real Work
  Order needs one (decision 10).
- Locking any term at mobilisation or once billed; release (7B) refusing incomplete terms.
- The frontend still has no component-test capability, so the page-load rules are covered by pure-rule
  tests of the reducer (`workOrderPageState.test.ts`) and by P2-9 and P2-10 above, not by a component
  test of the page itself.
- The manual checks above could not be performed from the implementation session (browser sign-in is not
  possible there), so they were the project owner's screen check.

## Outcome

**PASSED - the project owner's screen check, 15 September 2026**, on the worktree stack at Alembic
`20260908_0038`, against Work Order `WO-002674`: a monthly line whose first period held Part 1's terms only
(so its badge started at "Terms missing: night shift, mobilisation, demobilisation, fuel"), and an hourly
line with no terms at all. That covered P2-1 to P2-10, and P2-11 - Part 1's deferred stale-message
re-check, steps 11c and 11d - which also closes that item for Part 1.

Independent review: **ACCEPTED at round 2** (the independent reviewer, read-only, one hashed bounded packet per round),
after round 1's three material findings were corrected. The accepted tree is
`bc017b3a37c76538029b729594a7e04e1ad3b65e`, committed unchanged as the first Part 2 commit; this record
was added in a second commit.

## Follow-up checks (7D.1): the billing terms layout

Seeded Work Order with three lines: a complete monthly line with a later period, a shift line recorded only
in part, and a line with no terms. User `sales1`, then `finance1` for L-7. L-10 adds a period to line 1.

L-1. **Chapters.** Open line 1's first period. The terms appear under three coloured headings - The rate,
   Working time, Extra charges - each with a short line saying what it covers.
L-2. **Cards.** Each group is its own card with a coloured top edge, a title, a one-line description and a
   tag. On line 1 every card reads **Answered**, and the period band reads **Complete**.
L-3. **Side by side.** In Basis and rate, the billing basis and the rate share a row, then the contracted
   hours and the working days. In Overtime, the choice and the percentage share a row.
L-4. **Still needed.** Open line 2 (Shift, recorded in part). Working days and off days, Breakdown, Night
   shift, Fuel and Mobilisation and demobilisation read **Still needed**; Basis and rate, Overtime and Idle
   time read **Answered**.
L-5. **A later period.** Line 1's second period shows its **Starts on** date and has no Mobilisation and
   demobilisation card.
L-6. **No tag after a basis change.** On line 2, change the billing basis to Day without saving. The tags
   disappear, because they describe the saved Shift terms; choose Shift again and they return. Nothing needs
   saving. Line 3: start billing terms and choose Hour - The
   rate, Working time (Idle time and minimums only) and Extra charges (Fuel, Mobilisation and
   demobilisation) appear, and there is no Night shift card.
L-7. **Read-only.** Sign in as `finance1`: the same chapters and cards show the saved values, with no
   fields, Save, Add or Remove.
L-8. **Actions.** Save terms, and its message, sit in their own bar at the end of the period; Add a later
   period sits apart in a dashed box below the line's periods.
L-9. **Periods open and close.** On line 1, the first period (from contract start, complete) starts
   closed and the later one (from 1 March 2027) starts open. Each closed period shows its date, basis and
   rate and its tag. The first period reads **In force now**, because the later one starts in the future.
   Click a period's heading to open or close
   it; the other stays as it was.
L-10. **An edited period stays open.** Open line 1's first period, change a value and save. It stays open
   after "Terms saved.". Add a later period: the new one opens, and a period you opened or edited keeps
   its state.
