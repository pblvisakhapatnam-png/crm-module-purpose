# Slice 6I.1 - Commercial Offer Detail Tabbed Navigation Polish Acceptance

## Scope

Verify that existing Commercial Offer detail content is grouped into usable client-side tabs without changing underlying behavior.

## Test Users

```text
sales1 / password      Sales User; exercises write actions.
finance1 / password    Finance User; confirms read-only visibility.
```

## Starting Route And Data

1. Start the Docker Compose application.
2. Login as `sales1 / password`.
3. Open `/commercial-offers`.
4. Choose an existing Commercial Offer with Account/Opportunity context, at least one line, pricing evidence and linked Work Order data where available.

## Positive Path

1. Confirm tabs appear near the page header.
2. Confirm `Overview` is selected on initial page load.
3. Confirm Overview shows the offer snapshot, Account/Opportunity context, commercial summary and workflow/deferred guidance.
4. Open `Lines & Pricing`; confirm lines and pricing evidence remain available and their existing actions render for the Sales role.
5. Open `Terms & Conditions`; confirm recommended readiness, Attach Recommended Clauses, attached clause list, manual attach and remove controls are present.
6. Attach one available manual clause and confirm feedback appears in the T&C tab near the clause list/form. Remove the same attachment if it was created only for this test and confirm local removal feedback.
7. Run Attach Recommended Clauses where missing recommendations exist, or run the idempotent action where all are attached. Confirm its feedback appears beside the recommended panel action.
8. Open `Submission`; confirm Submission Readiness and Submission Evidence are both present.
9. Add a clearly marked test evidence metadata record if safe test data is available. Confirm the evidence list refreshes and success/error feedback stays inside the Submission tab.
10. Open `Traceability`; confirm linked Work Order shell links and role-appropriate audit/event links remain usable.
11. Reload the detail URL and confirm `Overview` is selected again.

## Read-Only / Permission Path

1. Login as `finance1 / password`.
2. Open the same Commercial Offer detail URL.
3. Confirm all five tabs remain viewable.
4. Confirm existing T&C and submission evidence records can be viewed.
5. Confirm write actions remain hidden or disabled according to existing frontend role guidance. Backend authorization remains authoritative and is unchanged by this slice.

## Responsive And Accessibility Checks

- Tab buttons have accessible tab semantics and a clear selected state.
- Tabs remain reachable on a narrow viewport through clean horizontal scrolling.
- Long readiness and evidence text remains readable.
- No tab invents or implies completed quote/PDF generation, approval, legal approval, credit approval or Work Order release/posting.

## Expected Result

All existing detail capabilities remain available in the appropriate tab, local action feedback stays with its action section, existing links work and no backend/business behavior changes.

## Automated Checks

```text
git diff --check
docker compose run --rm frontend npm run build
docker compose run --rm frontend npm test
```

## Acceptance Result

Automated frontend gate: Pass.

```text
git diff --check - pass
docker compose run --rm frontend npm run build - pass
docker compose run --rm frontend npm test - pass; script reports frontend automated tests are not configured
```

Manual browser smoke: Not performed. The in-app browser surface had no available browser instance in this session. Final tab clicking, action-message and responsive UAT remains a human/manual acceptance item; it must not be inferred from the successful production build.
