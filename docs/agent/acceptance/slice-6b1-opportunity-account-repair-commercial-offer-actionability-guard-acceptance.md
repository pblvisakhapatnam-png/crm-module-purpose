# Slice 6B.1 Acceptance - Opportunity Account Repair and Commercial Offer Actionability Guard

## Automated checks

Required:

```powershell
git diff --check
docker compose up -d --build --force-recreate backend
docker compose exec backend pytest
docker compose stop frontend
Remove-Item -Recurse -Force .\frontend\.next -ErrorAction SilentlyContinue
docker compose run --rm frontend npm run build
docker compose run --rm frontend npm test
Remove-Item -Recurse -Force .\frontend\.next -ErrorAction SilentlyContinue
docker compose up -d frontend
```

## Manual happy path

```text
1. Login as sales1 / password.
2. Create or open a manual Opportunity with no linked Account.
3. Open /opportunities/<opportunity-public-id>.
4. Confirm Account context shows the repair panel.
5. Create a minimal Account / Qualified Prospect from the panel.
6. Confirm success message appears near the Create and link Account button.
7. Confirm the Opportunity profile now shows linked Account.
8. Open the linked Account and return to the Opportunity.
```

## Manual existing Account repair path

```text
1. Login as sales1 / password.
2. Open another manual Opportunity with no linked Account.
3. Use the repair panel to select an existing Account.
4. Click Link Account.
5. Confirm success message appears near the Link Account button.
6. Confirm the Opportunity profile now shows the selected linked Account.
```

## Manual Commercial Offer actionability checks

```text
1. Create a Commercial Offer for an Opportunity.
2. Open /commercial-offers/new?opportunityId=<same-opportunity-public-id>.
3. Confirm the page detects the existing active/actionable Commercial Offer and shows an Open link.
4. Click the normal create action.
5. Confirm the browser routes to the existing Commercial Offer instead of creating another one.
6. For a Commercial Offer that was blocked by missing Account traceability, repair the linked Opportunity Account.
7. Return to the Commercial Offer.
8. Confirm Submit/Accept is now possible and Account context is visible.
```

## Permission check

```text
1. Login as finance1 / password.
2. Open an Opportunity with no linked Account.
3. Confirm the missing Account state is visible.
4. Confirm Account repair controls are not available.
5. API check: POST /api/opportunities/{public_id}/account-repair returns 403 for finance1.
```

## Negative / validation checks

```text
1. Try Account repair with both account_public_id and create_account; expect 422.
2. Try Account repair with neither repair path; expect 422.
3. Try repairing an already-linked Opportunity; expect 422 and no Account change.
4. Try creating a second Commercial Offer for an Opportunity with an existing DRAFT/READY/SUBMITTED/ACCEPTED offer; expect 422 or UI route to the existing offer.
```

## Deferred items

```text
- Customer Master activation.
- Finance approval.
- Work Order release/posting.
- Equipment assignment.
- Crew assignment.
- Log sheets.
- Billing.
- Full approval workflow.
- Opportunity lines.
- Formal Commercial Offer revision/versioning.
- Production Commercial Offer numbering.
```

## Manual status

Pending human browser/UAT execution after automated checks complete.
