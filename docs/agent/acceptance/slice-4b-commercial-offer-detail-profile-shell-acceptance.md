# Acceptance - Slice 4B Commercial Offer Detail / Profile Shell

## Slice summary

Slice 4B refines the Commercial Offer / Quote profile into a structured read-only profile shell.

## Automated checks

Run frontend checks:

```powershell
docker compose stop frontend
Remove-Item -Recurse -Force .\frontend\.next -ErrorAction SilentlyContinue

docker compose run --rm frontend npm run build
docker compose run --rm frontend npm test

Remove-Item -Recurse -Force .\frontend\.next -ErrorAction SilentlyContinue
docker compose up -d frontend
```

Recommended backend regression check:

```powershell
docker compose exec backend pytest
```

## Manual happy path

```text
1. Login as sales1 / password.
2. Open /commercial-offers.
3. Open an existing Commercial Offer profile.
4. Confirm the page shows these sections:
   - Offer snapshot
   - Opportunity context
   - Account context
   - Commercial summary
   - Remarks / requirement notes
   - Workflow position
   - Deferred boundaries
   - Audit and traceability
5. Click Back to Commercial Offers and confirm navigation works.
6. Open the profile again.
7. Click Open Opportunity and confirm navigation works.
8. If the profile shows a linked Account, click Open Account and confirm navigation works.
```

## Manual permission path

```text
1. Login as finance1 / password.
2. Open /commercial-offers.
3. Open an existing Commercial Offer profile.
4. Confirm the profile is visible and read-only.
5. Confirm there is no edit, submission, approval, credit or Work Order action.
```

## Manual event access path

```text
1. Login as admin1 / password.
2. Open a Commercial Offer profile.
3. Confirm View recent business events is visible.
4. Click it and confirm the Events page has a Back to Commercial Offer action.
5. Login as sales1 or finance1, depending on current role setup.
6. Confirm event access is not shown unless that role is intentionally authorized by the Events module.
```

## Explicitly deferred

```text
Commercial Offer update
Commercial Offer submission
Quote line-item engine
Rate master
Revision workflow
Approval workflow
Credit checks and exposure consumption
Tender/customer submission evidence
Award capture
Work Order handoff
Equipment Hiring fulfillment logic
Transportation handoff logic
```

## Additional accepted carry-forward observations

- The profile can navigate from Commercial Offer to linked Opportunity and Account, but those destination pages do not yet provide a return button back to the originating Commercial Offer. This is accepted for Slice 4B and should be handled in a later navigation-consistency slice.
- The profile now visibly reserves space for market-rate collection, selected basis rate, historical Plum-rate comparison and selection rationale. These are placeholders only; backend records and workflows are deferred.

