# Slice 3C Acceptance - Opportunity Update / Stage Foundation

## Automated checks

```powershell
docker compose up -d --build --force-recreate backend
docker compose exec backend pytest

docker compose stop frontend
Remove-Item -Recurse -Force .\frontend\.next -ErrorAction SilentlyContinue
docker compose run --rm frontend npm run build
docker compose run --rm frontend npm test
Remove-Item -Recurse -Force .\frontend\.next -ErrorAction SilentlyContinue
docker compose up -d frontend
```

## Backend acceptance

```text
- PUT /api/opportunities/{public_id} exists.
- Sales/Admin roles can update foundation Opportunity fields.
- Finance/Operations/Management read-only roles cannot update.
- Invalid status values are rejected.
- WON and CLOSED remain unavailable in Slice 3C update.
- OpportunityUpdated is recorded on successful update.
- OpportunityStageChanged is recorded when opportunity_status_code changes.
- Event payloads do not contain passwords, tokens or secrets.
```

## Frontend acceptance

```text
- Sales/Admin users see Edit Opportunity / Stage on Opportunity profile.
- Read-only roles can view the Opportunity profile but do not see the edit action.
- Update form allows foundation fields and early status movement only.
- Saved changes are reflected on the profile after successful update.
- Business timestamps continue to display in local business time.
```

## Manual happy path

```text
1. Login as sales1 / password.
2. Open /opportunities.
3. Open an Opportunity profile.
4. Click Edit Opportunity / Stage.
5. Change requirement summary and status to QUALIFIED or QUOTE_PENDING.
6. Save.
7. Confirm the profile updates and shows OpportunityUpdated / OpportunityStageChanged.
```

## Manual permission check

```text
1. Login as finance1 / password.
2. Open /opportunities.
3. Open an Opportunity profile.
4. Confirm the profile loads read-only.
5. Confirm Edit Opportunity / Stage is not available.
```

## Manual validation check

```text
1. Login as sales1 / password.
2. Open an Opportunity profile.
3. Try to save a blank Opportunity name.
4. Confirm the update is rejected.
5. Confirm WON/CLOSED cannot be selected from the Slice 3C UI.
```

## Explicit non-acceptance items

```text
Lead conversion
Quote / Commercial Offer
Approval workflow
Credit check / exposure
Work Order handoff
```
