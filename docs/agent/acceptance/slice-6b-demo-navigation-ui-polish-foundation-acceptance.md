# Slice 6B Acceptance - Demo Navigation and UI Polish Foundation

## Automated checks

Frontend:

```powershell
git diff --check
docker compose run --rm frontend npm run build
docker compose run --rm frontend npm test
```

Backend:

```text
Run docker compose exec backend pytest only if backend files are touched.
```

## Manual happy path

```text
1. Login as sales1 / password.
2. Open /.
3. Confirm the dashboard shows the implemented flow modules and role-appropriate create shortcuts.
4. Confirm the sidebar navigation includes the implemented demo flow cue.
5. Open /leads, /accounts, /opportunities, /commercial-offers and /work-orders.
6. Confirm each page loads, keeps existing actions, and shows consistent page framing, status badges, messages and empty states.
7. Open one Lead, Account, Opportunity, Commercial Offer and Work Order shell detail page where test data exists.
8. Confirm existing linked-record and return navigation still works.
```

## Manual regression checks

```text
1. Open a Commercial Offer with Account traceability.
2. Confirm linked Account, linked Opportunity and linked Work Order shell navigation still works.
3. Open a Commercial Offer missing Account traceability if demo data exists.
4. Confirm the Slice 6A.1 missing Account block is still prominent.
5. Confirm missing Account traceability still blocks submit, accept and Work Order shell handoff from the UI.
```

## Permission check

```text
1. Login as finance1 / password.
2. Open the dashboard and the Lead, Account, Opportunity, Commercial Offer and Work Order list pages.
3. Confirm read access still works where allowed.
4. Confirm create/edit actions remain hidden or unavailable for the read-only role surfaces.
5. Confirm backend permissions remain authoritative; this UI slice does not grant new actions.
```

## Expected result

```text
- The implemented CRM-to-Work Order shell flow is easier to demo.
- Navigation and page framing are consistent across implemented modules.
- Status and empty/read-only states are clearer.
- No deferred production functionality is introduced.
- Existing Slice 6A and Slice 6A.1 traceability behavior is preserved.
```

## Deferred items

```text
- T&C master / clause library.
- Offer-level and offer-line-level T&C attachment.
- Customer Master activation.
- Finance approval.
- Work Order release/posting.
- Equipment assignment.
- Crew assignment.
- Log sheets.
- Billing.
- Full approval workflow.
- Playwright/browser regression automation.
```
