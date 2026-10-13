# Slice 6M.1 - Commercial Offer Controlled Terminal Status Transition Guard

## Status

Implemented in two commits. This file documents the completed scope.

```text
fa09489 - Implement Slice 6M.1 commercial offer terminal status transition guard
          (cannot-leave guard for WITHDRAWN, REJECTED, CLOSED)
<this>  - Complete Slice 6M.1 controlled terminal status transition guard
          (controlled entry into ACCEPTED/REJECTED; ACCEPTED joins cannot-leave)
```

## Objective

Close a gap left open by every prior Commercial Offer lifecycle-status slice (4C/4F/6J/6K/6L/6M): the general update route (`PUT /api/commercial-offers/{public_id}`) placed no restriction on the offer's *current* status before applying a requested new status, and no restriction on which statuses could be *entered*. Every dedicated lifecycle route (`mark-submitted`, revisions, customer responses) already validated its own current-status precondition, but the generic update route did not.

## Part 1 (commit `fa09489`) - cannot-leave guard for WITHDRAWN/REJECTED/CLOSED

The first commit blocked the generic update route from changing `offer_status_code` away from `WITHDRAWN`, `REJECTED` or `CLOSED` once reached. Non-status field edits and same-status resubmission remained allowed. `ACCEPTED` was deliberately excluded from this set at the time, on the reasoning that the Slice 6L customer-response route still legitimately acts on `ACCEPTED` offers.

That reasoning was correct for the *customer-response route* (which is unaffected either way, since it writes `offer_status_code` through the repository layer directly, bypassing this service-level guard by design) but incomplete for the *generic update route*: it left two paths open that the follow-up verification in Part 2 found and closed.

## Part 2 (this commit) - completion: controlled entry into ACCEPTED/REJECTED

### Verification performed before implementing

Per the instruction to verify before changing anything, four questions were checked against the `fa09489` code and with live API calls against a running backend:

```text
1. Can a SUBMITTED Commercial Offer be changed to ACCEPTED through generic PUT?
   YES (bug). old_status=SUBMITTED was not in the fa09489 cannot-leave set, and there was
   no cannot-enter concept at all, so PUT {"offer_status_code": "ACCEPTED"} succeeded
   whenever Account traceability was present.
2. Can a SUBMITTED Commercial Offer be changed to REJECTED through generic PUT?
   YES (bug), for the same reason - REJECTED has no Account-traceability precondition at
   all, so this path had no guard whatsoever.
3. Can an ACCEPTED Commercial Offer be changed to another status through generic PUT?
   YES (bug). ACCEPTED was excluded from COMMERCIAL_OFFER_TERMINAL_STATUSES, so
   PUT {"offer_status_code": "DRAFT"} against an ACCEPTED offer succeeded.
4. Does the generic frontend status control offer ACCEPTED or REJECTED?
   YES (bug). COMMERCIAL_OFFER_STATUS_UPDATE_OPTIONS included both, and the edit form only
   disabled the whole selector for WITHDRAWN/REJECTED/CLOSED (not ACCEPTED), so a Sales user
   editing an ACCEPTED offer saw a fully enabled dropdown including every status.
```

All four paths were confirmed still open, so the corrective completion described below was implemented.

### Fix

Two contract constants replace the single `COMMERCIAL_OFFER_TERMINAL_STATUSES` from Part 1, because the two concepts do not share the same membership:

```text
COMMERCIAL_OFFER_GENERIC_UPDATE_CANNOT_LEAVE_STATUSES = (ACCEPTED, WITHDRAWN, REJECTED, CLOSED)
COMMERCIAL_OFFER_GENERIC_UPDATE_CANNOT_ENTER_STATUSES = (ACCEPTED, REJECTED)
```

`COMMERCIAL_OFFER_INACTIVE_FOR_NEW_OFFER_STATUSES` (Slice 6B.1's "blocks a new offer for the same Opportunity" concept) is un-aliased back to its own independent `(WITHDRAWN, REJECTED, CLOSED)` tuple: `ACCEPTED` must join the general-update cannot-leave set but must **not** join this Slice 6B.1 set, since an Accepted offer is still "active/actionable" for that unrelated rule.

`update_commercial_offer` now checks, in order: (1) cannot-leave (unchanged from Part 1, message unchanged, `ACCEPTED` added to the set), (2) cannot-enter (new - rejects any request whose target status is `ACCEPTED` or `REJECTED` and differs from the current status), (3) the pre-existing "use mark-submitted" check for `SUBMITTED` targets, (4) the pre-existing Account-traceability check. Same-status payloads are never a "transition" under rules 1 or 2, so they remain allowed (needed for full-update compatibility, e.g. resubmitting the form with an edited remarks field while the status field is unchanged).

No API-client-controlled bypass flag was added anywhere. The only sanctioned path into `ACCEPTED`/`REJECTED` remains the existing Slice 6L Customer Response action, which is architecturally separate (repository-layer write, not the guarded service function) rather than a flag on the same request.

## Scope

In scope (this commit, completing the already-approved 6M.1 scope):

```text
- Backend: reject any PUT that would set offer_status_code to ACCEPTED or REJECTED from a
  different current status ("cannot enter").
- Backend: add ACCEPTED to the statuses generic update cannot leave.
- Rename/restructure contract constants to keep the "cannot leave" and "cannot enter"
  concepts, and the unrelated Slice 6B.1 "inactive for new offer" concept, as distinct
  named tuples rather than aliases of one another.
- Frontend: remove ACCEPTED and REJECTED from the generic Offer status edit control; the
  control is disabled (not merely missing two options) once the current status is
  cannot-leave, same as Part 1's WITHDRAWN/REJECTED/CLOSED treatment, now including ACCEPTED.
- Frontend: point users at the Customer Response action (Submission tab) in the explanatory
  copy for both the disabled-control note and the read-only Workflow Position status badges.
- Update every existing backend test that relied on the old (buggy) behavior of reaching
  ACCEPTED/REJECTED through generic PUT, switching them to the dedicated Customer Response
  action instead.
- New focused tests for both entry-guard directions plus the widened cannot-leave set.
```

Out of scope:

```text
- No change to any specialized lifecycle route's own guard logic (mark-submitted, revisions,
  customer responses, lifecycle-guidance). They were already correct.
- No new state machine beyond the named cannot-leave/cannot-enter sets.
- No migration.
- No change to the frozen Slice 6D.1 Accepted Offer -> Work Order handoff contract.
```

## Backend Changes

```text
backend/app/modules/commercial_offers/contract.py
  - COMMERCIAL_OFFER_TERMINAL_STATUSES renamed/split into
    COMMERCIAL_OFFER_GENERIC_UPDATE_CANNOT_LEAVE_STATUSES (ACCEPTED, WITHDRAWN, REJECTED, CLOSED)
    and COMMERCIAL_OFFER_GENERIC_UPDATE_CANNOT_ENTER_STATUSES (ACCEPTED, REJECTED).
  - COMMERCIAL_OFFER_INACTIVE_FOR_NEW_OFFER_STATUSES reverted to its own independent
    (WITHDRAWN, REJECTED, CLOSED) tuple, no longer aliased to the cannot-leave set.
backend/app/modules/commercial_offers/service.py
  - update_commercial_offer gained the cannot-enter check, placed immediately after the
    existing cannot-leave check and before the existing "use mark-submitted" check.
```

## Frontend Changes

```text
frontend/app/commercial-offers/[commercialOfferId]/page.tsx
```

- `COMMERCIAL_OFFER_STATUS_UPDATE_OPTIONS` reduced to `DRAFT, READY_FOR_REVIEW, WITHDRAWN, CLOSED` (ACCEPTED and REJECTED removed).
- `COMMERCIAL_OFFER_TERMINAL_STATUSES` renamed to `COMMERCIAL_OFFER_GENERIC_UPDATE_CANNOT_LEAVE_STATUSES` and now includes `ACCEPTED`.
- New `COMMERCIAL_OFFER_GENERIC_UPDATE_CANNOT_ENTER_STATUSES` constant used only for explanatory badge wording.
- The "deferred" warning banner (for `SUBMITTED`/`REVISED`) and the "final status" banner (for cannot-leave statuses) no longer both render for the same offer; the final-status banner takes precedence and now explicitly names the Customer Response action.
- The read-only Workflow Position status badges show `- via Customer Response` for `ACCEPTED`/`REJECTED` instead of the generic `- deferred` suffix used for `SUBMITTED`/`REVISED`.

## Tests

`backend/tests/test_commercial_offers_api.py`:

```text
test_update_commercial_offer_blocks_transition_away_from_terminal_status  (extended)
  Now loops over WITHDRAWN, REJECTED, CLOSED and ACCEPTED. WITHDRAWN/CLOSED are reached via
  generic PUT (unchanged); REJECTED/ACCEPTED are reached via mark-submitted + the Customer
  Response action, since generic PUT can no longer reach them. Every status is then proven
  non-reopenable, non-status-field edits remain allowed, and same-status resubmission
  remains allowed.

test_generic_update_cannot_enter_accepted_or_rejected_but_customer_response_still_can  (new)
  SUBMITTED -> ACCEPTED and SUBMITTED -> REJECTED via generic PUT are both rejected (422)
  with no business event, no customer-response record and no status change as side effects.
  The dedicated Customer Response action still succeeds for both ACCEPTED_AWARDED and
  REJECTED_LOST, records exactly one CommercialOfferCustomerResponseRecorded event, and does
  not auto-create a Work Order. Once ACCEPTED, generic update cannot leave it either. Derived
  lifecycle guidance is checked and matches (ACCEPTED_READY_FOR_HANDOFF / REJECTED_CLOSED).

test_mark_submitted_status_credit_hold_and_warning_paths  (updated setup only)
  Its REJECTED/ACCEPTED setup steps switched from generic PUT to mark-submitted + Customer
  Response; the test's actual assertions (mark-submitted rejected once already in a non-
  Draft/Ready status) are unchanged.

test_sales_user_can_capture_commercial_offer_lifecycle_submission_and_outcome  (updated)
  Now asserts the generic-PUT-to-ACCEPTED path is blocked, then reaches ACCEPTED through the
  Customer Response action, then proves a non-status field edit (remarks) still succeeds on
  the now-ACCEPTED offer.

test_commercial_offer_submit_and_accept_require_account_traceability  (updated)
  The ACCEPTED-without-Account assertion now expects the entry-guard message rather than the
  Account-traceability message, since entry into ACCEPTED is blocked unconditionally before
  the traceability check ever runs; a code comment explains that there is consequently no
  longer any reachable API path for the original "Account traceability blocks ACCEPTED"
  scenario, since mark-submitted itself already requires Account traceability.

test_commercial_offer_lifecycle_succeeds_after_opportunity_account_repair  (updated)
  Reaches ACCEPTED via the Customer Response action instead of generic PUT.
```

`backend/tests/test_work_orders_api.py`:

```text
create_test_offer_with_line(accepted=True)  (updated helper, used by 2 tests)
  Now creates submission evidence, marks the offer Submitted, and records an
  ACCEPTED_AWARDED Customer Response instead of using generic PUT. cleanup_records() gained
  matching commercial_offer_customer_response and commercial_offer_submission_evidence
  deletion steps (FK-safe order, matching the existing pattern in test_commercial_offers_api.py)
  so the now-larger per-offer record set can be torn down without a foreign-key conflict.
```

Full backend suite: 143 passed (up from 142 after `fa09489`; the net gain is one new test function, `test_generic_update_cannot_enter_accepted_or_rejected_but_customer_response_still_can` - the extended loop in `test_update_commercial_offer_blocks_transition_away_from_terminal_status` and the updated assertions in four pre-existing tests do not add new test functions, only new coverage within existing ones).

## Migration / Alembic

None. Pure service/contract/UI logic change over the existing `offer_status_code` column. Alembic head remains `20260712_0027` (unchanged since Slice 6M).

## Manual / API Smoke

Performed against the running app as `sales1` after the fix, using both direct API calls and the browser UI:

```text
1. Created a fresh Opportunity + Commercial Offer, added a line, recorded submission evidence,
   and marked it Submitted.
2. PUT {"offer_status_code": "ACCEPTED"} -> 422, entry-guard message naming Customer Response.
3. PUT {"offer_status_code": "REJECTED"} -> 422, entry-guard message.
4. Confirmed no business_event or commercial_offer_customer_response row was created by either
   rejected PUT.
5. POST /customer-responses {"response_outcome": "ACCEPTED_AWARDED", ...} -> 201, offer now
   ACCEPTED; GET /api/work-orders?commercial_offer_public_id=... returned [] (no auto-created
   Work Order).
6. PUT {"offer_status_code": "DRAFT"} against the now-ACCEPTED offer -> 422, cannot-leave
   message.
7. Opened the Commercial Offer edit form in the browser for the ACCEPTED offer: the Offer
   status control was disabled, showing only "Accepted (final status, cannot be changed
   here)"; the explanatory note pointed to the Customer Response action in the Submission
   tab; a non-status field (remarks) edit still saved successfully.
8. Confirmed the Offer status dropdown on a non-terminal (Draft) offer's edit form no longer
   lists Accepted or Rejected as options.
```

## Frozen Handoff Contract

`docs/agent/contracts/accepted-offer-to-work-order-handoff-contract.md` is unchanged (confirmed via `git diff --stat`). This work does not touch Work Order handoff, Commercial Offer line identity, or any handoff-related field.

## Known Limitations / Deferred (unchanged)

```text
- This remains a transition guard over two named sets, not a full status state machine.
  DRAFT/READY_FOR_REVIEW/WITHDRAWN/CLOSED remain freely settable as generic-update targets
  from any non-cannot-leave current status, matching the existing Slice 4C/4F design.
- Full calculated Commercial Offer credit/exposure gating remains Slice 6I.3.
```

## Part 3 (4 October 2026) - a submitted offer stays submitted (TB-1 finding TB1-301)

TB-1's Pass 3 found that the general update could move a `SUBMITTED` offer back to `DRAFT` or `READY_FOR_REVIEW`:
the "use mark-submitted" check guards entering `SUBMITTED` only, and the edit form offered Draft and Ready for Review
whatever the current status. A submitted offer is commercially committed (AGENTS.md; the offer contract's Slice 6I
section), and the move took it out of the submitted pipeline. TB-1's independent review judged it a section 12
emergency; the owner chose a bounded fix as its own package (4 October 2026).

- **Backend:** `COMMERCIAL_OFFER_PRE_SUBMISSION_STATUSES` (`DRAFT`, `READY_FOR_REVIEW`) in `contract.py`; in
  `update_commercial_offer`, after the cannot-leave rule and under the same row lock, a `SUBMITTED` offer asked for
  one of them is refused with `422`. Withdrawn and Closed stay reachable. `SUBMITTED` is not added to the cannot-leave
  set, which the reports module uses to define open offers.
- **Frontend:** `frontend/src/pages/commercial-offers/offerStatus.ts` holds the statuses the edit form may set and
  `statusUpdateOptions(current)`, which offers only Withdrawn and Closed for a submitted offer; the edit form and the
  status overview use it, and the form says why.
- **Tests:** `test_a_submitted_offer_cannot_go_back_to_draft_or_ready_for_review_through_general_update` (both
  targets refused, nothing changed and no event; a same-status save and a withdrawal still work);
  `offerStatus.test.ts`.
- **Records:** the contract's 6M.1 section (rule 1a and the corrected parenthesis), the acceptance record (Part 3),
  `docs/continuity/TB1_301_SUBMITTED_OFFER_STAYS_SUBMITTED.md` and `NEXT_STEPS.md`. No migration, no new route, no
  new event. The frozen handoff contract is unchanged.

## Part 4 (5 October 2026) - a final offer's content stays as it was (TB-1 finding TB1-301 (b))

TB-1's Pass 3 found that an offer's lines, pricing evidence and basis rate, T&C clauses, credit reviews and submission
evidence could be written whatever the offer's status - after acceptance and handoff included, so the accepted offer and
its Work Order's copy could disagree, and a second handoff would copy the changed values. TB-1's final independent
review judged it a section 12 emergency; the owner chose a bounded fix as its own package (5 October 2026).

- **Backend:** `_lock_offer_for_content_change` in `commercial_offers/service.py` takes the offer's row lock, reads its
  status and refuses (`422`) when it is in `COMMERCIAL_OFFER_GENERIC_UPDATE_CANNOT_LEAVE_STATUSES` (Accepted,
  Rejected, Withdrawn, Closed). The eight content writers call it first: line add and edit, pricing evidence add, basis
  rate selection, T&C attach (and attach-recommended through it) and remove, credit review, submission evidence. The
  T&C remove route now maps the refusal to `422`. A submitted offer is unchanged by this rule.
- **Frontend:** `offerContentLocked` and `contentLockedNote` in `offerStatus.ts`; on a final offer the offer page hides
  the line, pricing, T&C, credit-review and submission-evidence forms and buttons and says why.
- **Tests:** `test_a_final_offers_lines_prices_terms_and_evidence_can_no_longer_change` (all eight writes refused on an
  accepted offer, nothing changed and no event; a line add still works while submitted; a withdrawn offer refused);
  `offerStatus.test.ts`. Changed because they changed an accepted offer: Slice 9E's
  `test_approval_cannot_validate_a_combination_of_offer_data_that_never_existed` made its concurrent write through the
  line and T&C writers from a second session in the same thread - they now wait for the offer lock the approval holds,
  so it makes the same writes by direct statements, its assertions unchanged;
  `test_lifecycle_guidance_rejected_closed_and_blocked_by_missing_active_lines` now expects the line cancel on an
  accepted offer to be refused and sets that older state directly to check the handoff guard; and the smoke-data
  harness's `_build_accepted_offer` adds a scenario's extra lines before submission (`extra_lines`).
- **Side effects of the lock, recorded:** the eight writes now queue behind one another on the offer's row, so two
  overlapping removals of one T&C clause record one removal, not two (the T&C half of TB-1's TB1-506); a line edit
  computes its amount from the line as it stands under the lock; and "mark submitted" reads lines and credit reviews
  that cannot change between its check and its commit (TB1-301 (d)).
- **Records:** the contract's 6M.1 section, the acceptance record (Part 4), `DEFERRED_REQUIREMENTS.md` ("Submitted
  document locking"), `docs/continuity/TB1_301B_FINAL_OFFER_CONTENT_STAYS.md` and `NEXT_STEPS.md`. No migration, no new
  route, no new event. The frozen handoff contract is unchanged.
