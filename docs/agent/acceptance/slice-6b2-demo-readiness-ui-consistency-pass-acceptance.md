# Slice 6B.2 Acceptance - Demo Readiness UI Consistency Pass

## Automated checks

Run from the repository root:

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
2. Open / and confirm the dashboard explains implemented demo flow versus deferred production work.
3. Open /leads, /accounts, /opportunities, /commercial-offers and /work-orders.
4. Confirm action buttons use consistent spacing and wrapping.
5. Confirm list tables/cards stay contained at desktop and narrower browser widths.
6. Confirm status badges, empty states and refresh/pagination controls remain visible and readable.
7. Open create pages for Lead, Account, Opportunity, Commercial Offer and Work Order shell where available.
8. Confirm forms are contained in consistent cards and submit feedback appears near the triggering action.
```

## Manual detail checks

```text
1. Open one Lead, Account, Opportunity, Commercial Offer and Work Order shell detail page where demo data exists.
2. Confirm the pages remain readable and linked navigation still works.
3. On an Opportunity missing Account traceability, confirm the Account repair panel remains visible and contained.
4. On a Commercial Offer missing Account traceability, confirm the guard text remains visible and no deferred Customer Master workflow is implied.
```

## Permission check

```text
1. Login as finance1 / password.
2. Open dashboard and the list/create/detail pages in the implemented flow.
3. Confirm read surfaces remain available where allowed.
4. Confirm create/update actions remain hidden or blocked for roles that cannot perform them.
5. Confirm this UI slice does not grant any new backend capability.
```

## Expected result

```text
- Demo screens look more consistent and professional.
- Page action rows and dashboard card actions wrap predictably.
- List and form containers avoid visual overflow at narrower widths.
- Account remains the user-facing term.
- Existing functionality and backend rules are preserved.
```

## Known manual gaps

```text
- Browser viewport checks should still be performed manually before demo sign-off.
- No Playwright/browser automation is added in this slice.
```

## Deferred production features not implemented

```text
Customer Master activation, Finance approval, WO release/posting, equipment assignment, crew assignment, log sheets, billing, approval workflow, Opportunity lines, Commercial Offer revision/versioning and production Commercial Offer numbering remain deferred.
```
