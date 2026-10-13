# Slice 6A.1 Acceptance - Commercial Offer Account Link Guard and Repair Path

## Automated checks

Backend:

```powershell
docker compose up -d --build --force-recreate backend
docker compose exec backend pytest
```

Frontend, because frontend code changed:

```powershell
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
2. Open a Commercial Offer created from a Lead-converted Opportunity with linked Account context.
3. Confirm the Commercial Offer profile shows the linked Account.
4. Move the offer to Submitted, then Accepted.
5. Confirm the save succeeds and lifecycle events are recorded.
6. Create a Work Order shell from the Accepted offer.
7. Confirm the Work Order shell shows Account, Opportunity and Commercial Offer traceability.
```

## Manual missing Account block

```text
1. Login as sales1 / password.
2. Open a Commercial Offer whose linked Opportunity has no Account / business_party link.
3. Confirm the Commercial Offer profile shows a prominent Account traceability missing message.
4. Confirm the message links back to the Opportunity context.
5. Try selecting Submitted or Accepted in the Commercial Offer edit form.
6. Confirm the save action is blocked and explains that Account traceability is required.
7. If the bad offer is already Accepted from legacy/demo data, confirm Create Work Order shell is not available on the Commercial Offer profile.
8. Open /work-orders/new?commercialOfferId=<offer-public-id> for that offer.
9. Confirm the Work Order handoff page shows the missing Account block and cannot create the shell.
```

## Permission check

```text
1. Login as finance1 / password.
2. Open the same Commercial Offer profile.
3. Confirm Account traceability state is visible.
4. Confirm Finance still cannot edit Commercial Offer status or create a Work Order shell.
```

## API validation check

```text
1. Call PUT /api/commercial-offers/{public_id} with offer_status_code = SUBMITTED on an offer with no account_public_id.
2. Confirm 422 and an Account traceability message.
3. Call PUT /api/commercial-offers/{public_id} with offer_status_code = ACCEPTED on the same offer.
4. Confirm 422 and no status change.
5. Call POST /api/work-orders/from-commercial-offer for an Accepted legacy/bad offer with no Account traceability.
6. Confirm 422 and no Work Order shell is created.
```

## Deferred items

```text
- Controlled Opportunity-to-Account relinking for manually created Opportunities.
- Customer Master activation.
- Finance approval.
- Work Order release/posting.
- Equipment assignment.
- Crew assignment.
- Log sheets.
- Billing.
- Full approval workflow.
```
