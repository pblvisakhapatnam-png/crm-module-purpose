# Slice 6O Acceptance - Work Order Shell Detail and Handoff Review UI

## Automated checks

```text
Backend: docker compose exec backend pytest tests/test_events.py tests/test_work_orders_api.py -q
  -> 15 passed.
Backend: docker compose exec backend pytest -q
  -> 149 passed.
Frontend: docker compose run --rm frontend npm run build
  -> Compiled successfully, no TypeScript errors, all 21 routes generated.
Frontend: docker compose run --rm frontend npm test
  -> "Frontend automated tests not configured in Slice 0A" (unchanged baseline).
```

## Manual happy path (performed via exploratory browser testing during this slice)

Test user: `sales1 / password` (SALES_USER).

1. Seeded a Lead -> qualify -> convert -> Commercial Offer -> 2 active lines -> submission
   evidence -> mark-submitted -> customer response Accepted/Awarded chain through the backend
   TestClient (equivalent to normal UI actions), producing an Accepted Commercial Offer.
2. Opened `/commercial-offers/{id}`, Submission tab. Confirmed the new "Work Order handoff
   review" snapshot showed the offer code, status (Accepted), mode/type, date, value, Account
   link, Opportunity link, active line count (2) and a short per-line summary, plus "No Work
   Order has been created yet from this Commercial Offer."
3. Clicked "Create Work Order shell" (header action) -> `/work-orders/new?commercialOfferId=...`.
   Confirmed the source-offer card showed offer mode/type/date and the same "no Work Order yet"
   statement. Entered a customer WO reference, left both lines selected, submitted.
4. Confirmed exactly one Work Order shell was created (`WO-001102`), 2 lines copied, and the
   success card linked to it with a `returnTo` back to the source Commercial Offer.
5. Opened the created Work Order. Confirmed: "Handoff shell" badge, status, created-at/updated-at/
   created-by fields, source Commercial Offer link with "Accepted / awarded at handoff" note,
   Opportunity/Account links, a "Handoff provenance" section, and a line-traceability table
   showing both lines with their `source_offer_line_public_id` values matching the original
   Commercial Offer line public IDs.
6. Clicked "Back to Commercial Offer" from the Work Order detail page - confirmed it returned to
   the originating Commercial Offer (not the generic Work Orders list), i.e. origin-aware
   navigation held end to end.
7. Reopened the Commercial Offer, Traceability tab: confirmed the linked Work Order shell was
   listed with "Open Work Order shell", and no "Create Work Order shell" action was offered
   anywhere on the page any more (header, Lifecycle Guidance panel, Traceability tab) now that a
   shell exists - and the panel does not claim the award is "fully handed off".

## Manual permission / role path

1. Logged in as `admin1` (ADMIN) and opened the same Work Order. Confirmed the "Handoff
   provenance" section additionally showed the underlying `WorkOrderCreated` business event
   (name, timestamp, reason) - exactly one event, sourced from the new
   `GET /api/events/recent?record_type=work_order&record_public_id=...` filter.
2. Logged in as `readonly1` (MANAGEMENT_READ_ONLY) and opened the same Work Order. Confirmed
   read access succeeded and the event history section loaded (same permission class as ADMIN).
3. (Backend-verified, not re-driven through the browser in this pass) `finance1` can view but not
   create Work Order shells; `sales1` cannot call `GET /api/events/recent` at all, filtered or
   not - both already covered by `test_finance_user_can_view_but_cannot_create_work_order_shell`
   and the new `test_events_recent_filter_still_rejects_sales_user`.

## Manual validation / blocked path

1. Seeded a second Commercial Offer left in `DRAFT` (never submitted/accepted) with one active
   line and full Account traceability.
2. Opened its Submission tab: the "Work Order handoff review" snapshot correctly did **not**
   render (status is not Accepted); the Lifecycle Guidance panel showed "Work Order handoff: Not
   available" with the blocked reason "Commercial Offer is not Accepted. Work Order handoff
   requires an accepted/awarded outcome." No create action was shown anywhere on the page.
3. Opened `/work-orders/new?commercialOfferId=...` directly for that same Draft offer: the
   "Create Work Order shell" submit button rendered but was verified `disabled` via
   `document.querySelector('button[type="submit"]').disabled === true`. Direct API enforcement
   for this same precondition is covered by
   `test_work_order_shell_requires_accepted_offer`.

## Deferred / not re-driven manually in this pass

```text
- A live mobile-width screenshot of the Work Order line table; verified instead via computed
  CSS (`.data-table-wrap` -> overflow-x: auto, `.data-table-wide` -> min-width: 980px), which is
  the same pre-existing, already-shipped pattern used on the Accounts/Leads/Opportunities list
  pages. The browser tool's resize/screenshot actions did not reliably reflect a changed
  window.innerWidth during this session; a future UI-focused pass should re-verify visually.
- A second Work Order shell created from the same accepted offer (partial-award duplicate) was
  exercised only through the backend TestClient/pytest
  (test_work_order_partial_award_allows_additional_shell_from_same_offer), not re-driven through
  the browser UI, since the UI intentionally does not offer that as a one-click action.
```

## Expected result

All automated checks pass; the handoff review and Work Order detail experience is materially
richer and more traceable while the frozen Slice 6D.1 handoff contract, its trigger conditions,
payload shape, authorization, and event semantics are provably unchanged (SHA-256 of the contract
file matched before and after this slice).
