# Slice 6M Acceptance - Commercial Offer Post-Response Lifecycle Readiness Cleanup

## Automated Checks

- [x] No migration added; Alembic current/heads both report `20260712_0027` (unchanged from Slice 6L).
- [x] `git diff --check` passed.
- [x] Commercial Offer focused regression: `pytest tests/test_commercial_offers_api.py -k lifecycle_guidance` - 2 passed.
- [x] Commercial Offer + Work Order focused regression: `pytest tests/test_commercial_offers_api.py tests/test_work_orders_api.py` - 48 passed.
- [x] Full backend suite: `pytest` - 141 passed.
- [x] Frontend production build (`npm run build`, after clearing `.next`) - passed.
- [x] Frontend test command (`npm test`) - passed; reports automated frontend tests are not configured, consistent with prior slices.
- [x] Frozen handoff contract confirmed byte-for-byte unchanged: `git diff --stat -- docs/agent/contracts/accepted-offer-to-work-order-handoff-contract.md` produced no output.

## Human UAT

Test user: `sales1`; permission user: `readonly1`.

Starting route: `/commercial-offers/{offer-public-id}`, Submission tab.

Test data: eight Commercial Offers were created via API for this pass (one per scenario below), each with an Account-linked Opportunity, one active line, submission evidence and marked Submitted.

- [x] Submitted, no customer response: Lifecycle Guidance shows "Submitted - awaiting customer response"; Work Order handoff not available; blocked reason names the missing Accepted status; new revision cycle allowed.
- [x] `REVISION_REQUESTED`: guidance shows "Customer requested revision" and directs to the existing revision workflow; `Start revision cycle` button is enabled (offer still Submitted, no open revision); Work Order handoff not available.
- [x] `CLARIFICATION_REQUESTED`: guidance shows "Customer requested clarification"; Work Order handoff not available; no new workflow invented.
- [x] `ON_HOLD`: guidance shows "On hold"; Work Order handoff not available; offer not closed.
- [x] `PENDING_CUSTOMER_DECISION`: guidance shows waiting/pending guidance; Work Order handoff not available.
- [x] `REJECTED_LOST`: guidance shows "Rejected / lost - closed"; `Commercially active` = No; `Start revision cycle` button disabled; `POST .../revisions` returns 422; `POST /api/work-orders/from-commercial-offer` returns 422.
- [x] `ACCEPTED_AWARDED`, no Work Order yet: guidance shows "Accepted / awarded - ready for Work Order handoff"; `Create Work Order shell` action appears (role-gated); recording the response did not create a Work Order (`GET /api/work-orders?commercial_offer_public_id=...` returned `[]` immediately after).
- [x] `ACCEPTED_AWARDED`, Work Order already created: guidance shows "Accepted / awarded - Work Order shell already created"; the default `Create Work Order shell` action is **not** offered anywhere on the page (header, Traceability tab, Lifecycle Guidance panel); `Open Work Order shell` is offered and links correctly with return navigation; a note explains that an additional shell remains possible only for a genuine partial-award scenario, not as a default action.
  - *Reconciled 8 October 2026 (TB-1 CS-04 part 1):* this no longer holds. An offer line's quantity goes onto Work
    Orders once, whole or in parts, and the server refuses anything already on one, so while anything is left
    the page offers "Create another Work Order" beside "Open"; the note under the existing Work Orders says another
    takes only what is not on a Work Order yet. See `docs/continuity/TB1_103_WORK_ORDER_HANDOFF_ONCE_PER_LINE.md`.
- [x] `readonly1` (no Work Order create permission): Lifecycle Guidance section is visible (read-only); `Create Work Order shell` action is not shown anywhere; backend `POST /api/work-orders/from-commercial-offer` returns 403; backend `GET .../lifecycle-guidance` returns 200 for `readonly1`.
- [x] Historical response records: all six non-final outcomes recorded in sequence on one offer remained visible in the Customer Response history list (append-only, latest first); the Lifecycle Guidance state followed only the most recent one at each step (verified via API after each POST).
- [x] Revisions, Submission Evidence, Credit / Exposure Review, T&C tab and linked Work Orders (Traceability tab) all still render correctly across the scenarios above.

## Expected Result

Every scenario above produced a single, non-contradictory narrative: readiness, revision/response history, derived guidance and Work Order handoff state agree with each other and with what the backend guards actually allow. No automatic Work Order was created by any customer-response outcome. The frozen Slice 6D.1 handoff contract file, route, payload, permissions and event names are all unchanged.

## Deferred / Known Gaps

The generic Commercial Offer PUT endpoint can still set Accepted/Rejected directly without a Slice 6L response record (pre-existing, out of scope here). Full calculated credit/exposure gating before handoff remains future work (Slice 6I.3). See the matching continuity note for the Slice 6N renumbering recommendation.
