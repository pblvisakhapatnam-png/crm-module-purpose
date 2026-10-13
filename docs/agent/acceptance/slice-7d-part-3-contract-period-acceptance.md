# Slice 7D Part 3 Acceptance - the contract period, extensions, line dates, and copying terms

Written so a later tester can perform regression/UAT without this session's chat history. Design and
owner decisions: `docs/agent/slices/slice-7d-part-3-contract-period.md`.

## Preconditions

Stack running. This slice adds migration `20260908_0039`; `alembic/` is baked into the backend image,
so after merging rebuild before testing:

```powershell
docker compose up -d --build --force-recreate backend
docker compose exec backend alembic current
```

Expected: `20260908_0039 (head)`. Rebuild the frontend image too (`docker compose up -d --build
frontend`): its source is not bind-mounted.

Frozen contract check, before and after:

```bash
sha256sum docs/agent/contracts/accepted-offer-to-work-order-handoff-contract.md
```

Expected: `70debad711eea67f5e8f0ff3a945c7431235ddfd97b34330beb390215cb0b86a`.

## Automated checks

| Check | Command | Expected |
| --- | --- | --- |
| Part 3 rules, no database | `docker compose exec backend pytest tests/test_slice_7d_part_3_contract_rules.py -q` | 47 passed (35 before the owner's clarification of 22 September 2026) |
| Part 3 through the routes | `docker compose exec backend pytest tests/test_slice_7d_part_3_contract_period.py -q` | 128 passed (68 at round 1, 82 after rounds 1 and 2, 107 after the owner's screen check, 128 after the owner's clarification, both 22 September 2026) |
| Slice 7C tests (two new response fields) | `docker compose exec backend pytest tests/test_slice_7c_work_order_line_detail.py -q` | all pass |
| Slice 7D Parts 1 and 2 | `docker compose exec backend pytest tests/test_slice_7d_work_order_line_billing_terms.py tests/test_slice_7d_part_2_billing_terms.py -q` | all pass |
| Harness cleanup of the two new tables | `docker compose exec backend pytest tests/test_smoke_data_harness.py -q -k contract_period` | 1 passed |
| Route guard (pins all five new routes) | `docker compose exec backend pytest tests/test_authorization_route_migration_guard.py -q` | all pass |
| Full backend regression, run alone | `docker compose exec backend pytest -q` | 1957 passed, 0 failed on the accepted tree; 1982 after the owner's screen check; 2015 after the owner's clarification |
| Migration: empty database to head | scratch database, as recorded in the continuity note | reaches `20260908_0039` |
| Migration: `0038` with Part 1 and Part 2 data present, then `downgrade -1`, then head | as recorded in the continuity note | terms and line details survive untouched both ways; the two tables, two columns, two permissions and eight grants appear and disappear with the revision |
| Frontend typecheck, tests, build | the `AGENTS.md` sequence (prefix `MSYS_NO_PATHCONV=1` in Git Bash) | clean; 188 tests (164 on the accepted tree, 173 after the screen check, 183 after the clarification, 188 after review round 5); `workOrderContractPeriodState.test.ts` added; route table unchanged |
| Full E2E suite | `pwsh -NoProfile -File scripts/run-e2e.ps1` | no failures. **Run it with `pwsh`, not `powershell`.** Under Windows PowerShell 5.1 the script's `Set-Content -Encoding utf8` writes a BOM, every seed manifest then breaks `JSON.parse`, and each spec dies in its fixture before running - leaving `e2e/test-results/` empty and nothing useful in the report |
| Committed-credential and fixture checks | `python scripts/check_tracked_secrets.py`, `python scripts/validate_contract_fixtures.py` | clean |

## Test data

Seed the scenario written for this screen check. It builds a Work Order with three lines: line 1 has
**two** billing-terms periods (the second starting 1 July 2027), line 2 has terms on a different
basis and rate, and line 3 has none. The contract dates are deliberately left unrecorded, so the
empty state and the first save are both seen.

```powershell
.\scripts\smoke-data.ps1 seed -Scenario work-order-contract-period
```

The output prints the Work Order's URL. Clean up afterwards with
`.\scripts\smoke-data.ps1 cleanup -RunId <run id>`.

## Manual happy path - the contract dates

User `sales1` (Sales User). Open the seeded Work Order.

1. In **The Work Order**, below the snapshot, there is a **Contract period** section. It reads
   "Contract dates not recorded" and "Missing: contract start date, contract end date".
2. In **Billing terms**, open line 1. Its first period reads **"From contract start to 30 June 2027"** -
   no date, because none is recorded yet.
3. Back in **Contract period**, set **Contract starts on** to 1 January 2027, **Contract ends** to
   "On a fixed date", and **Contract ends on** to 31 December 2027. Click **Save contract dates**.
   Expected: "Contract dates saved." beneath the button; the badges change to a state ("Starts in N
   days, on 1 January 2027" or "Active...", depending on today's date) and "Contract dates recorded".
4. Open line 1's terms again. Its first period now reads **"From 1 January 2027 to 30 June 2027"** -
   the contract's own start date in place of the words.
5. Click **Save contract dates** again without changing anything. Expected: "Nothing changed, so
   nothing was saved."

## Manual happy path - "until the work is complete"

6. Change **Contract ends** to "Until the work is complete" and save. Expected: the end date field
   disappears; the badge reads "Active, until the work is complete" (or "Starts ..." if the start is
   still ahead); "Contract dates recorded" - it is an answer, not a gap; and a sentence appears
   saying the Work Order **cannot be closed until a firm end date is recorded**.
7. Change **Contract ends** back to "Not recorded yet" and save. Expected: the badge reads "Missing:
   contract end date" - blank is not an answer, and the closure sentence is gone. This is the
   difference decision 14 turns on.
8. Set it back to a fixed date of 31 December 2027 and save before continuing.

## Manual negative path - the dates that cannot move

These come before any extension, because once an extension exists the end date is no longer on the
form (owner, 22 September 2026). Until that date this checklist put them after the extensions, and
its step 16 then told the tester to type the end date back on the form - the very edit that silently
undid the extensions. The owner's screen check found it.

9. In **Contract period**, change **Contract ends on** to 1 February 2027 and save. Expected: refused
   with **"The contract cannot end on 1 February 2027, because line 1 has terms starting 1 July
   2027."** The dates are named, and so is the line.
10. Change **Contract starts on** to 1 August 2027 and save. Expected: refused, naming line 1's period
    again - a period cannot begin before the contract does either.
11. Put the dates back to 1 January 2027 and 31 December 2027 (the refused saves changed nothing;
    reload if the form still shows what was typed), and save. Expected: "Nothing changed, so nothing
    was saved."
12. In **Billing terms**, on line 1, enter **A later period starts on** 1 January 2028 and click
    **Add a later period**. Expected: refused with "This period starts on 1 January 2028, after the
    contract ends on 31 December 2027."
12a. Click into any date field on the page and try to type a year of five digits. Expected: the year
    stops at four digits. Every date field on the Work Order page has a maximum of 31 December 9999.

## Manual happy path - an extension

13. Under **Extensions**, the list is empty and the text says **"Approval step not yet added."**
14. Under **The extension starts on**, expect **1 January 2028** filled in, with "Normally the day
    after the contract ends." Leave it. Enter **The contract now ends on** 30 June 2028, **Extension
    order received on** 1 November 2027, and a customer's reference such as `EXT/2027/01`. Click
    **Record extension**. No question is asked, because the extension runs straight on. Expected:
    "Extension recorded, and the contract end date moved to it."; a row reading "31 December 2027 to
    30 June 2028", with its date under **Order received on**; the contract end date above now 30 June
    2028.
15. Look at **Contract ends on** above. Expected: it is no longer a field. It reads **30 June 2028**,
    with "Set by the extensions below. To change it, record another extension, or remove the latest
    one." **Contract starts on** and the notes are still fields: type a note and save. Expected:
    "Contract dates saved.", and the end date is still 30 June 2028.
16. Record a second extension to 31 December 2028, order received on 1 May 2028 (its start fills in as
    1 July 2028). Expected: both rows
    are listed, oldest first; the first still reads "31 December 2027 to 30 June 2028" - **earlier end
    dates are not overwritten**; and **Remove** appears on the second row only.
17. Try an extension to 30 September 2028. Expected: refused with "An extension must move the end
    date later. The contract currently ends on 31 December 2028, so 30 September 2028 would not extend
    it. To correct an extension recorded in error, remove it instead."
17a. Try an extension to 31 March 2029 with the order received on 15 December 2026. Expected: refused
    with "This extension order is dated 15 December 2026, before the contract starts on 1 January
    2027."
17b. In **Extension order received on**, enter a date 20 days before today. Expected: a warning under
    the field - "This order is dated ..., more than 15 days ago. Check the date before recording it.
    It can still be recorded." - and the **Record extension** button still available. Change the date
    to today: the warning goes. Do not record it: with this test data a date 20 days ago is also
    before the contract start, so it would be refused as in 17a. The warning is a prompt to check,
    never a refusal.

## Manual happy path - removing an extension recorded in error

17c. Click **Remove** on the second row. Expected: a confirmation reading "Remove extension 2 (30 June
    2028 to 31 December 2028)? The contract end date goes back to 30 June 2028. The removal is kept
    in the Work Order's audit log." Cancel it: nothing changes.
17d. Click **Remove** again and confirm. Expected: "Extension removed, and the contract end date put
    back."; one row left; the contract end date 30 June 2028; **Remove** now on the first row.
17e. Remove the first extension too. Expected: no extension listed, the same confirmation message
    still shown, and **Contract ends** is a field again, set to 31 December 2027 - with no extension
    left, the end is edited on the form as before.
17f. Sign in as `admin1` and open **Business Events**. Expected: two
    `WorkOrderContractExtensionRemoved` events for this Work Order. The rows have gone from the
    history; the audit log is what keeps the fact that they existed.

## Manual happy path - an extension that starts later, and an order that arrives late

The owner's clarification of 22 September 2026. Continue on the same Work Order, which after 17e
runs 1 January to 31 December 2027 with no extensions.

17g. Record an extension to 30 June 2028 with **The extension starts on** changed to 15 January 2028
    and the order received on 20 December 2027. Before you click, a line under the start field says the
    days from 1 January 2028 to 14 January 2028 will be outside the contract. Click **Record extension**.
    Expected: a confirmation naming those days. Cancel it - nothing is recorded.
17h. Click again and confirm. Expected: the row reads "31 December 2027 to 30 June 2028, starting 15
    January 2028", and below the history, "No contract runs on 1 January 2028 to 14 January 2028, before
    extension 1."
17i. **Leave the extension form** - nothing you typed there is saved - and scroll down the page to
    **Billing terms**. Open **line 1**, and in its **A later period starts on** field enter 5 January
    2028, then click **Add a later period**. Expected: refused with "This period starts on 5 January
    2028, when no contract runs: the contract ended on 31 December 2027, and extension 1 starts on
    15 January 2028." This is the point of the gap: the days 1 to 14 January 2028 belong to no
    contract, so nothing may be recorded on them.
17j. Remove that extension, then record one to 30 June 2028 with the start left at 1 January 2028 and
    the order received on **10 January 2028** - after the contract ended. Expected: recorded without a
    question. A verbal commitment can come first and the order arrive later; the extension still starts
    the day after.
17k. Remove that extension before continuing, so the dates are 1 January to 31 December 2027 again.
    (Moving the contract start past the end an extension continued from is also refused, but this
    Work Order's billing terms refuse such a move first, naming line 1; the extension's own refusal is
    covered by a backend test.)

## Manual happy path - a line's own dates

These controls sit in the **Site and billing details** section, with the line's other facts, because
that is where a line's own dates belong. They were missing from the first version of this package and
added after independent review (round 1, finding F-03).

18. In **Site and billing details**, open line 2. Below the customer's line reference there are
    **This line starts on** and **This line ends on**, with a note saying a line left empty follows
    the Work Order's contract dates. Set 1 March 2027 and 31 August 2027, and save. Expected:
    "Details saved."
19. Try line 3 with a start of 1 December 2026. Expected: refused with "This line starts on
    1 December 2026, before the contract starts on 1 January 2027."
20. Leave line 3's dates empty and save. Expected: accepted, and nothing is reported missing - blank
    means the line follows the Work Order.
20a. Open line 2 again, change only the **customer's line reference**, and save. Expected: the dates
    set in step 18 are still there afterwards. Editing one field must never clear the others.
20b. Sign in as `finance1` and open the same section. Expected: line 2 shows a **This line runs** row
    reading "1 March 2027 to 31 August 2027", and line 3 shows "The same dates as the Work Order" -
    a role that cannot edit still sees what is recorded.

## Manual happy path - applying one line's terms to others

21. In **Billing terms**, open line 1 and click **Apply these terms to other lines**. Expected: line
    2 and line 3 are listed and line 1 is not - the source is the line you are standing on. **Line 3
    is ticked** (it has no terms); **line 2 is not** (it has terms), and each shows its own basis and
    rate, so a line that differs is easy to leave alone.
22. The button reads **"Apply these terms to 1 line"**.
23. Tick line 2 as well. Expected: the button reads "Apply these terms to 2 lines", and a note
    appears saying line 2 already has billing terms and that you will be asked to confirm.
24. Click the button. Expected: a confirmation naming line 2. Cancel it - nothing is written; line 2
    still shows its own shift rate.
25. Click again and confirm. Expected: "Terms copied to line 3. Terms replaced on line 2."; both
    lines now read "Terms complete"; both show line 1's monthly basis and rate; and **both have two
    periods**, because every period is copied, not only the current one.
25a. This step is about **the copy panel**, not about saving a period. Keep this tab open. In a
    second browser tab, open the same Work Order and save any change to line 2's billing terms -
    **including a change to its earlier period**, now that it has two. Back in the first tab, without
    reloading, open **Apply these terms to other lines** on line 1, tick line 2, click the button and
    confirm. Expected: refused with "Line 2's billing terms changed after you opened this page. Reload
    to see their version." - **the line is named**. The confirmation is only meaningful about the
    terms the screen actually saw, and with several lines chosen the user has to be told which one
    refused (rounds 1 and 2, findings F-01, F-02, F-07 and F-08).

    Saving one period from two tabs is a different check, and behaves differently: the second save is
    refused only if the first changed the same period, and that message is about the period, not a
    named line. The owner tried that on 22 September 2026 and it worked correctly; this step was
    reworded because its first version read as if it were about that.
26. Open line 3 and change its rate, then save. Expected: it saves - each receiving line stays
    editable.
27. Open the panel on line 3 now. Expected: lines 1 and 2 are listed, neither ticked (both have
    terms) - the source is whichever line you are standing on.

## Permission check

27a. At any point, look at the sidebar below the navigation. Expected: "Signed in as Sales User 1"
    with "Sales User" beneath it. Sign in as someone else and it changes to them - and never shows the
    previous person's name for the new session: if the new name is slow to arrive, the sidebar reads
    just "Signed in" until it does (review round 5, finding F-01).
28. Sign in as `finance1` (Finance User). Open the same Work Order. Expected: the sidebar reads "Signed
    in as" the Finance user, and the **Contract period**
    section shows the dates and the extension history as plain text, with no form, no Save button,
    no **Record extension** button and no **Remove** button; **Billing terms** shows no **Apply these terms to other lines**
    button; **Site and billing details** shows the line's dates read-only.

    Note which permission governs which: the Work Order's contract dates are
    `WORK_ORDER_CONTRACT_PERIOD_WRITE`, recording or removing an extension is
    `WORK_ORDER_CONTRACT_EXTENSION_WRITE`, and a
    **line's own dates are `WORK_ORDER_LINE_DETAIL_WRITE`** - they are part of that line's detail and
    are saved through its route. All three hold the same four roles today.
29. Sign in as `ops1` (Operations User). Expected: every form above is available - the same four
    roles that record a line's details and terms.

## Known limitations recorded rather than fixed

- A copied period is checked against the contract but **not** against the receiving line's own dates,
  so a line running to earlier dates can receive a period starting after its own end. Deliberate;
  recorded in the slice document.
- The contract start does not yet lock at mobilisation (owner decision 19); mobilisation does not
  exist. Recorded in `docs/agent/DEFERRED_REQUIREMENTS.md`.
- Nothing refuses closure, release, a log sheet or billing on these dates yet; those slices will.
- No expiry alerts and no approval of an extension; the screen says "Approval step not yet added".
- Only the Work Order page's date fields stop at a four-digit year. The same gap on other pages -
  Work Order Amendment, new Work Order and others - is recorded in
  `docs/agent/DEFERRED_REQUIREMENTS.md`.
- Showing who is signed in was rolled into this package at the owner's word (22 September 2026); it
  is app-wide, so it is visible on every page, not only the Work Order.
- Nothing yet refuses a log sheet or a bill on a day in a gap, because neither exists; the rule that
  will (`IN_GAP`) is built and tested.
- The frontend still has no component-test capability, so the pure rules are tested
  (`workOrderContractPeriodState.test.ts`) and the wiring is covered by the diff and this screen
  check.

## Acceptance outcome

Record one of: Pass / Pass with minor issues / Fail - functional issue / Fail - usability issue /
Blocked. Note any defect against the numbered step above.

**23 September 2026: PASS**, recorded by the project owner after walking the whole checklist on the
seeded `work-order-contract-period` scenario. Every step behaved as written. Three observations, all
recorded rather than corrected:

- **"Remove this period" is placed confusingly** - at the foot of a period's long form, directly under
  Save terms and beside two line-level buttons. Recorded in `docs/agent/UI_UX_CARRY_FORWARD.md` with
  the fix named, under the owner's standing 7D.1 ruling that this form is not re-opened for polish.
- **Backspace should walk back through a date field**, clearing year to month to day. The browser's own
  control stops at one segment. Recorded in `docs/agent/DEFERRED_REQUIREMENTS.md` beside the
  four-digit-year cap, which wants the same shared date-input component.
- **Date fields on other pages** still accept a five- or six-digit year; only the Work Order page's are
  capped. Same entry.

Two steps needed clarifying during the check and have been reworded here rather than left to trip the
next tester: **17i** now says plainly to leave the extension form and scroll to Billing terms, because
coming after two extension steps it read as if it were still about them. The same check also showed
that a billing-terms period recorded beyond the contract end blocks removing the extension that
allowed it - correctly, and with a message that says so.
