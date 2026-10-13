# Slice 6O.2 Acceptance - Work Order Amendment Intake Foundation

## Automated checks

- `docker compose exec backend alembic heads` / `alembic current` both report
  `20260713_0029 (head)`.
- `docker compose exec backend pytest tests/test_work_order_amendments_api.py -q` -
  20 focused tests, all passing.
- `docker compose exec backend pytest` (full suite) - all passing, no regressions.
- Frontend `npm run build` passes; both new amendment routes
  (`/work-orders/[workOrderId]/amendments/new`,
  `/work-orders/[workOrderId]/amendments/[amendmentId]`) compile as dynamic routes.
- Frontend `npm test` remains the pre-existing "not configured" placeholder.
- `docs/agent/contracts/accepted-offer-to-work-order-handoff-contract.md` byte-for-byte
  unchanged (`git diff --stat` empty for that file, SHA-256 verified before/after).
- `.\scripts\run-e2e.ps1` run twice from clean state: all Playwright specs pass both
  times with distinct run ids, cleanup succeeds both times, no residue left behind.

## Manual UI acceptance

Test users: `sales1` (SALES_USER, authorized), `readonly1` (MANAGEMENT_READ_ONLY,
read-only). Starting point: `http://localhost:3000`, logged in as the relevant user.

### Positive path - Administrative amendment

1. Login as `sales1`.
2. Seed or open an accepted Commercial Offer with an existing Work Order shell.
3. Open the Work Order. Confirm the "Work Order Amendments (Slice 6O.2)" section shows
   "No Work Order Amendment has been recorded yet." and a "Record Work Order Amendment"
   action.
4. Click it. Confirm the Work Order/Account/Opportunity/Base Offer context is shown
   locked (read-only) at the top of the form.
5. Leave Amendment type as Administrative. Fill Received date and Amendment reason.
   Submit.
6. Confirm "Amendment recorded" and an "Open Amendment #1" link.
7. Open it. Confirm status "Received", the non-application wording ("does not change
   this Work Order or any of its lines"), and that no lifecycle action is shown other
   than "Start Review" / "Reject" / "Cancel".
8. Return to the Work Order. Confirm the Amendments section now lists "Amendment #1 -
   Administrative" with status "Received", and that the Work Order's own status badge
   and line-traceability table are unchanged.

### Positive path - Commercial amendment with accepted Change Quotation

1. From an accepted Commercial Offer with a linked Work Order, create and accept a
   Change Quotation (Slice 6O.1 flow) linked to that Work Order.
2. On the Change Quotation's Traceability tab, confirm "Record Work Order Amendment" is
   visible (offer is Accepted and linked to a Work Order) and no amendment is linked
   yet.
3. Click it. Confirm the amendment type defaults to Commercial and the commercial basis
   selector is pre-filled with the Change Quotation.
4. Fill Received date, Amendment reason, Commercial change summary. Submit.
5. On the amendment detail page, add one "Add Line" proposal (proposed description
   required). Confirm the "Original" column reads "Not applicable (new line)" and the
   "Proposed" column shows the entered values - visually distinct from any live Work
   Order line.
6. Click "Start Review", then "Validate" (now enabled because the basis is Accepted and
   a line exists). Confirm status "Validated" and the terminal read-only wording.
7. Reopen the Work Order and the Change Quotation. Confirm neither changed: the Work
   Order's lines are the same, and the Change Quotation is still Accepted.

### Negative / permission path

1. As `sales1`, create a Commercial amendment citing a **DRAFT** (not yet accepted)
   Change Quotation, add one line, move to Under Review.
2. Confirm the readiness "blocking reasons" list explains the basis must be Accepted,
   and the Validate button is disabled.
3. Login as `readonly1`. Open the same Work Order. Confirm the Amendments section is
   visible but "Record Work Order Amendment" is not.
4. Open an amendment. Confirm no "Start Review"/"Reject"/"Cancel" buttons and no line
   add/remove controls are shown; the summary/lines remain visible read-only.
5. Confirm a direct API mutation attempt (e.g. `POST .../decision`) as `readonly1`
   returns `403` (covered by backend permission tests; optionally spot-checked
   manually).

## Deferred / known limitations

- No application of a validated amendment to the Work Order; that is explicitly future
  work.
- No remaining-quantity/partial-award allocation logic.
- No amendment document generation or customer communication.
- Cross-browser Playwright coverage remains a single Chromium project, consistent with
  TE-1's existing scope.

## Code review findings (high effort, 8 finder angles)

Two low-cost, high-value UI findings were fixed:

- The amendment detail page's terminal read-only advisory message was gated entirely on
  the `readiness` fetch succeeding, with no fallback; if that fetch failed while the
  amendment fetch itself succeeded, a terminal (Validated/Rejected/Cancelled) amendment
  would show no explanation at all. Fixed by adding a static fallback message and by
  deriving `isTerminal` from the same `isEditable` value (`readiness.is_editable` with a
  local fallback) instead of a second, independently hardcoded status list that could
  drift out of sync with it.
- The "Start Review" button was gated only by `amendment.amendment_status_code ===
  "RECEIVED"`, unlike the adjacent "Validate" button which correctly also checks
  `readiness.can_move_to_validated`. Fixed so "Start Review" also respects
  `readiness.can_move_to_under_review` (defaulting to enabled if the readiness fetch is
  unavailable, since today's precondition is exactly the status check already applied).

The following were reviewed and intentionally left as documented, deferred findings
rather than fixed in this slice, because fixing them would mean rewriting or
significantly hardening Part 1's already-tested backend logic (out of proportion for a
Foundation Slice Mode UI/E2E/docs pass) or extending an established repo-wide
convention this slice did not introduce:

- **Sequence-number and duplicate-reference races** (`amendment_sequence_no`,
  `line_number`, `customer_amendment_reference` uniqueness) are each implemented as a
  read-then-write with no row lock or `IntegrityError` translation. A genuine concurrent
  double-submission (e.g. a double-click race, not normal single-user sequential use)
  would surface as an unhandled 500 instead of a clean 422/retry, though the database's
  own unique constraints prevent any duplicate or corrupted row from ever being
  committed - this is a UX/error-shape gap, not a data-integrity gap. This exact
  MAX()+1 pattern is used elsewhere in the codebase (e.g. Commercial Offer revisions)
  as an accepted foundation-prototype trade-off.
- **Amendment business events share `record_type = work_order` /
  `record_public_id = <Work Order public_id>` with the original `WorkOrderCreated`
  handoff event** (a deliberate Part 1 design choice documented in the amendment
  contract, mirroring the existing `commercial_offer_revision` /
  `commercial_offer_customer_response` subordinate-event pattern). Because
  `GET /api/events/recent` returns only the most recent 10 events for a given
  `record_type`/`record_public_id` pair, a Work Order that accumulates 10+ amendment
  events could see the original `WorkOrderCreated` event silently drop out of the
  Slice 6O "Handoff provenance" panel. Fixing this cleanly would mean adding an
  `event_name` filter or raising the panel's limit in the events module - reasonable
  future hardening, out of scope for this slice.
- **Code duplication** across the new frontend pages (per-file copies of
  `AMENDMENT_TYPE_LABELS`, `COMMERCIAL_OFFER_PURPOSE_LABELS`, token/access helpers) and
  backend (`service.py` validation helpers duplicating `commercial_offers/service.py`
  equivalents; four call sites repeating the same "amendment must be
  RECEIVED/UNDER_REVIEW to edit" guard). This matches the repo's existing convention of
  every page/module defining its own local helpers (no shared frontend utility module
  exists anywhere in the codebase today), so it is consistent rather than novel, but a
  future slice introducing a shared module would have a natural place to consolidate
  these.
- **Efficiency**: several read routes issue 2 sequential queries to resolve a Work
  Order/amendment by public id before doing any real work, and several
  create/update/decision repository functions re-`SELECT` the row they just wrote
  instead of using SQL Server's `OUTPUT inserted.*`. The Commercial Offer detail page's
  new `loadLinkedAmendments` call joins ~13 other sequential `await` calls already on
  that page rather than running in parallel. None of these affect correctness; they are
  reasonable future performance hardening once real data volumes make them worth
  measuring.
- `backend/tooling/smoke_data/scenarios.py`'s new `_build_blocked_validation_target`
  does not itself attempt the blocked `VALIDATED` transition at seed time to prove it
  is rejected (unlike the sibling `_build_blocked_handoff`, which does exactly this).
  The blocking rule is directly covered by a backend API test
  (`test_commercial_and_mixed_amendments_cannot_validate_without_accepted_basis_or_change_detail`)
  and by `amendment-blocked-commercial-validation.spec.ts`, so the missing seed-time
  self-check is a minor regression-safety gap in the harness itself, not an unverified
  business rule.

## TB-1 fix TB1-801 (5 October 2026): a refused amendment line keeps the page

Before this fix, a proposed quantity of 0, or a quantity or rate with more than two decimals, replaced the whole
amendment page with "Unexpected Application Error!" when **Record Add Line** was pressed: the page put FastAPI's list
of field errors on screen as it came. The line form now checks both numbers first (quantity above 0, rate 0 or more,
at most two decimals), and the line, removal and status actions - and the Work Order and amendment create pages - read
any refusal through the shared reader (`frontend/src/components/errorDetail.ts`).

Test user: `sales1` / `password` (SALES_USER). Starting URL: an amendment in Received or Under Review,
`http://localhost:3000/work-orders/<id>/amendments/<id>`.

1. In **Propose a line change**, fill **Proposed description / scope**, type `0` in **Proposed quantity**, press
   **Record Add Line**: "Proposed quantity must be greater than 0." appears; the page and what was typed stay.
2. Type `1.234`: "Proposed quantity can have at most 2 decimal places."; type `-1` in **Proposed rate amount** with a
   valid quantity: "Proposed rate amount must be 0 or more."
3. Type `1` as the quantity and clear the rate: "Amendment line proposal recorded."

`e2e/tests/amendment-commercial-with-change-quotation.spec.ts` runs steps 1 and 3, and also answers the line once with
the server's list of field errors to show the page stays and says "Check the values entered: one of them is not
accepted."
