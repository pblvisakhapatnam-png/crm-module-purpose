# Slice 6M.1 Acceptance - Commercial Offer Controlled Terminal Status Transition Guard

This slice was implemented in two commits. Part 1 records the original `fa09489` acceptance results (cannot-leave guard for WITHDRAWN/REJECTED/CLOSED). Part 2 records the completion commit's acceptance results (controlled entry into ACCEPTED/REJECTED; ACCEPTED joins cannot-leave).

## Part 1 (commit `fa09489`) - original acceptance record

### Automated Checks

- [x] No migration added; Alembic current/heads both report `20260712_0027` (unchanged from Slice 6M).
- [x] New focused test: `pytest tests/test_commercial_offers_api.py -k terminal_status` - 1 passed.
- [x] Full backend suite: `pytest` - 142 passed (up from 141 at end of Slice 6M).
- [x] Frontend production build (`npm run build`, after clearing `.next`) - passed, no type errors.
- [x] Frontend test command (`npm test`) - passed; reports automated frontend tests are not configured, consistent with prior slices.
- [x] Frozen handoff contract confirmed unchanged: no edits made to `docs/agent/contracts/accepted-offer-to-work-order-handoff-contract.md`.

### Human UAT

Test user: `sales1` (Sales User). Test data: one Commercial Offer (`CO-002568`) created via API, then moved to `WITHDRAWN`.

- [x] Opening "Edit Commercial Offer / Status": the Offer status field is disabled and shows only "Withdrawn (final status, cannot be changed here)"; a note above the form explains the status is final and other fields remain editable.
- [x] Editing the Remarks field and saving succeeds; status remains Withdrawn.
- [x] Direct `PUT {"offer_status_code": "ACCEPTED"}` against the same offer returns `422` naming `WITHDRAWN` as final.

### Deferred / Known Gaps recorded at the time

The generic Commercial Offer PUT route could still set a Draft/Ready offer directly to Accepted/Rejected without a Slice 6L customer-response record, and an Accepted offer could still be moved away from Accepted through generic update. **This gap is the subject of Part 2 below.**

## Part 2 (this commit) - completion acceptance record

### Verification performed before implementing (per instruction)

Confirmed via focused API calls against the running `fa09489` backend, before any code change in this commit:

| # | Question | Result |
|---|---|---|
| 1 | Can a SUBMITTED offer be changed to ACCEPTED through generic PUT? | Yes (bug) |
| 2 | Can a SUBMITTED offer be changed to REJECTED through generic PUT? | Yes (bug) |
| 3 | Can an ACCEPTED offer be changed to another status through generic PUT? | Yes (bug) |
| 4 | Does the generic frontend status control offer ACCEPTED or REJECTED? | Yes (bug) |

All four were confirmed open, so the corrective completion was implemented as instructed.

### Automated Checks

- [x] No migration added; Alembic current/heads both report `20260712_0027` (unchanged).
- [x] Focused tests: `pytest tests/test_commercial_offers_api.py -k "terminal_status or cannot_enter or mark_submitted_status_credit"` - 3 passed.
- [x] Commercial Offer + Work Order regression: `pytest tests/test_commercial_offers_api.py tests/test_work_orders_api.py` - 50 passed.
- [x] Full backend suite: `pytest` - 143 passed (up from 142 after `fa09489`; net +1 test function - `test_generic_update_cannot_enter_accepted_or_rejected_but_customer_response_still_can` - since the extended terminal-status loop and the four updated pre-existing tests add coverage within existing test functions rather than new ones).
- [x] Frontend production build (`npm run build`, after clearing `.next`) - passed, no type errors.
- [x] Frontend test command (`npm test`) - passed; reports automated frontend tests are not configured.
- [x] Frozen handoff contract confirmed unchanged: `git diff --stat -- docs/agent/contracts/accepted-offer-to-work-order-handoff-contract.md` produced no output.

### Human UAT / API Smoke

Test user: `sales1`. Test data: a fresh Opportunity + Commercial Offer with one active line, submission evidence, marked Submitted.

- [x] `PUT {"offer_status_code": "ACCEPTED"}` on the Submitted offer -> `422`, `"Commercial Offer status cannot be set to ACCEPTED through general update. Use the dedicated Customer Response action (Submission tab) to record the award or rejection outcome."`
- [x] `PUT {"offer_status_code": "REJECTED"}` on the same offer -> `422`, matching message naming `REJECTED`.
- [x] No `business_event`, no `commercial_offer_customer_response` row, and no offer status change resulted from either rejected PUT (verified by count/GET before and after).
- [x] `POST /customer-responses {"response_outcome": "ACCEPTED_AWARDED", ...}` -> `201`; offer status becomes `ACCEPTED`; exactly one `CommercialOfferCustomerResponseRecorded` event recorded.
- [x] `GET /api/work-orders?commercial_offer_public_id=...` immediately after -> `[]` (recording ACCEPTED_AWARDED does not auto-create a Work Order).
- [x] `PUT {"offer_status_code": "DRAFT"}` on the now-ACCEPTED offer -> `422`, `"Commercial Offer status ACCEPTED is final..."` (cannot-leave guard now covers ACCEPTED).
- [x] `GET .../lifecycle-guidance` on the ACCEPTED offer -> `lifecycle_state == "ACCEPTED_READY_FOR_HANDOFF"`, `work_order_handoff_available == true`.
- [x] Second offer: `POST /customer-responses {"response_outcome": "REJECTED_LOST", ...}` -> `201`; offer status becomes `REJECTED`; `GET .../lifecycle-guidance` -> `lifecycle_state == "REJECTED_CLOSED"`.
- [x] Browser: opened the Commercial Offer edit form for the ACCEPTED offer - the Offer status control is disabled, showing only "Accepted (final status, cannot be changed here)"; the note directs to the Customer Response action in the Submission tab; a non-status field (remarks) edit still saves successfully while status remains Accepted.
- [x] Browser: opened the edit form for a Draft offer - the Offer status dropdown lists only Draft, Ready For Review, Withdrawn and Closed; Accepted and Rejected are absent.
- [x] Browser: Workflow Position badges on the Overview tab show "Accepted - via Customer Response" and "Rejected - via Customer Response" (distinct from the generic "- deferred" suffix used for Submitted/Revised) when they are not the current status.

### Permission Check

No new role rule introduced. The entry guard applies inside the existing Commercial Offer update route, still restricted to `ADMIN`/`SALES_USER`/`SALES_MANAGER` (unchanged; full suite still passes `test_finance_user_can_view_but_cannot_update_commercial_offer`).

### Validation / Regression Check

- [x] `test_update_commercial_offer_blocks_transition_away_from_terminal_status` extended to loop over `WITHDRAWN, REJECTED, CLOSED, ACCEPTED`; all four proven non-reopenable, all four allow non-status edits and same-status resubmission.
- [x] `test_generic_update_cannot_enter_accepted_or_rejected_but_customer_response_still_can` (new) covers both entry-guard directions, zero-side-effect on rejection, both Customer Response outcomes still working, no auto-Work-Order, and correct lifecycle guidance.
- [x] Four pre-existing tests that relied on the old generic-PUT-to-ACCEPTED/REJECTED path were updated to use the Customer Response action instead: `test_mark_submitted_status_credit_hold_and_warning_paths`, `test_sales_user_can_capture_commercial_offer_lifecycle_submission_and_outcome`, `test_commercial_offer_submit_and_accept_require_account_traceability`, `test_commercial_offer_lifecycle_succeeds_after_opportunity_account_repair`.
- [x] `test_work_orders_api.py`'s shared `create_test_offer_with_line(accepted=True)` helper (used by 2 tests) updated the same way; its `cleanup_records()` gained matching FK-safe deletion of `commercial_offer_customer_response` and `commercial_offer_submission_evidence` rows.
- [x] Full 152-test backend suite passed with no other regressions.

## Expected Result

`ACCEPTED` and `REJECTED` can now be established only through the dedicated Slice 6L Customer Response action. The general update route rejects any attempt to enter either status, and additionally can no longer leave `ACCEPTED` once reached (joining the existing `WITHDRAWN`/`REJECTED`/`CLOSED` cannot-leave protection from `fa09489`). Non-status field edits and same-status resubmission remain allowed throughout. No duplicate business events, no stray customer-response records, and no automatic Work Order creation result from either the blocked path or the sanctioned path. The frozen Slice 6D.1 handoff contract, the database schema, and every other route's behavior are unchanged.

## Deferred / Known Gaps

This remains a targeted transition guard over two named sets (cannot-leave, cannot-enter), not a full status state machine; `DRAFT`/`READY_FOR_REVIEW`/`WITHDRAWN`/`CLOSED` remain freely settable as generic-update targets from any non-cannot-leave status, matching the existing Slice 4C/4F design. Full calculated credit/exposure gating remains Slice 6I.3.

## Part 3 (4 October 2026) - a submitted offer stays submitted (TB-1 finding TB1-301)

### Automated checks

- [x] `test_a_submitted_offer_cannot_go_back_to_draft_or_ready_for_review_through_general_update`: fails without the
  service change (`200` where `422` is expected), passes with it.
- [x] `offerStatus.test.ts`: a submitted offer is offered only Withdrawn and Closed; Accepted, Rejected and Submitted
  are never offered.
- [x] Results of the full backend regression and the frontend checks: `docs/continuity/TB1_301_SUBMITTED_OFFER_STAYS_SUBMITTED.md`.

### Screen check

Test user `sales1` (Sales User). Test data: a Submitted offer - for example the offer seeded by the smoke-data
scenario `revision-requested` (`scripts/smoke-data.ps1`), or any offer marked Submitted on the Submission tab.
Starting URL: `/commercial-offers/<offer public id>`.

1. **Edit Commercial Offer / Status**: the Offer status list shows "Submitted (current status)", Withdrawn and Closed
   only - not Draft or Ready for Review - and the note above the form says a submitted offer cannot go back to Draft
   or Ready for Review.
2. Change the remarks only and save: it saves; the status stays Submitted.
3. Overview tab, Status path: Draft and Ready for Review show "- not set here".
4. Negative path (API): `PUT /api/commercial-offers/<id>` with `{"offer_status_code": "DRAFT"}` as `sales1` returns
   `422` with "A submitted Commercial Offer cannot go back to Draft or Ready for Review ..."; the offer is unchanged
   and no event is recorded.
5. Permission path: unchanged - the route's roles are as before (`test_finance_user_can_view_but_cannot_update_commercial_offer`).

### Known gaps

Content written after submission (lines, prices, T&C, credit reviews, evidence) is still editable in every status:
TB-1 finding TB1-301 (b), "Submitted document locking" (`DEFERRED_REQUIREMENTS.md`). A late "lost" response after a
handoff, TB1-301 (c), waits for HOF-2.

## Part 4 (5 October 2026) - a final offer's content stays as it was (TB-1 finding TB1-301 (b))

### Automated checks

- [x] `test_a_final_offers_lines_prices_terms_and_evidence_can_no_longer_change`: fails without the service change
  (`201` where `422` is expected, on the first write), passes with it.
- [x] `offerStatus.test.ts`: Accepted, Rejected, Withdrawn and Closed lock the content; Draft, Ready for Review and
  Submitted do not; the note names the status in words.
- [x] Results of the backend modules, the frontend checks and CI: `docs/continuity/TB1_301B_FINAL_OFFER_CONTENT_STAYS.md`.

### Screen check

Test user `sales1` (Sales User). Test data: an Accepted offer - for example the offer seeded by the smoke-data
scenario `accepted-offer-no-work-order` (`scripts/smoke-data.ps1`) - and a Draft or Submitted offer to compare.
Starting URL: `/commercial-offers/<offer public id>`.

1. **Lines** tab of the Accepted offer: no "Add Commercial Offer line" form and no "Edit line" buttons; the note says
   "This offer is Accepted, so its lines, prices, T&C, credit reviews and submission evidence can no longer change ...".
2. **Pricing evidence**, **T&C**, **Credit review** and **Submission** sections: the same note in place of each form;
   no "Select as basis rate", attach or remove buttons.
3. The Draft or Submitted offer: every form shows as before.
4. Negative path (API): `POST /api/commercial-offers/<accepted id>/lines` as `sales1` returns `422` with the note's
   text; the offer's lines and events are unchanged.
5. Permission path: unchanged - the routes' roles are as before.

### Known gaps

A submitted offer's content is still editable ("Submitted document locking" stays deferred). Header fields saved with
the status unchanged are unchanged by this rule. A late "lost" response after a handoff, TB1-301 (c), waits for HOF-2.
