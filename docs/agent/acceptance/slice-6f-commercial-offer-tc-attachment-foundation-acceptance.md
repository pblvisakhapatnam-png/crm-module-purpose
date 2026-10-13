# Slice 6F Acceptance - Commercial Offer T&C Attachment Foundation

## Acceptance Scope

Validate that active source-derived T&C library clauses can be attached to a Commercial Offer header, shown on the Commercial Offer detail page, snapshotted for traceability and removed from the active attachment list.

## API Acceptance

| Scenario | Role/User | Route | Expected Result |
| --- | --- | --- | --- |
| List attachments | Sales User / `sales1` or Finance / `finance1` | `GET /api/commercial-offers/{public_id}/tc-clauses` | 200 with active header T&C attachments |
| Attach active header clause | Sales User / `sales1` | `POST /api/commercial-offers/{public_id}/tc-clauses` | 201 with attachment snapshot and `CommercialOfferTcClauseAttached` event |
| Duplicate active attach | Sales User / `sales1` | same POST with same clause | 422 and no second active attachment |
| Missing clause | Sales User / `sales1` | POST with missing clause public ID | 404 |
| Inactive clause | Sales User / `sales1` | POST with inactive library clause | 422 |
| Line-only clause | Sales User / `sales1` | POST with active clause where `applies_to_header = false` | 422 |
| Unauthorized attach | Finance / `finance1` | POST | 403 |
| Unauthorized remove | Finance / `finance1` | DELETE | 403 |
| Remove attachment | Sales User / `sales1` | `DELETE /api/commercial-offers/{public_id}/tc-clauses/{attachment_public_id}` | 200, active becomes false and `CommercialOfferTcClauseRemoved` event is recorded |
| List after remove | Sales User / `sales1` | GET | Removed attachment no longer appears |
| Snapshot preservation | Sales User / `sales1` | Attach, change master clause, list attachment | Snapshot title/text remain as originally attached |

## UI Acceptance

Role:

```text
Sales User or Sales Manager
```

Starting URL:

```text
/commercial-offers/{commercialOfferPublicId}
```

Steps:

```text
1. Login as a Sales user.
2. Open a Commercial Offer detail page.
3. Confirm the Header T&C clauses section is visible.
4. Confirm the section states clauses are source-derived prototype/test records.
5. Select an active header-applicable T&C library clause.
6. Attach the clause.
7. Confirm the clause appears in the active attachment list.
8. Expand the clause detail and confirm snapshot text/source/approval flags are visible.
9. Remove the clause.
10. Confirm the active list refreshes and the removed clause is no longer shown.
```

Expected result:

```text
- The UI uses relative /api calls.
- Action messages appear near the T&C controls.
- Finance/read-only roles can view attachments but do not see attachment controls as available actions.
- The UI does not imply line-level T&C, approval workflow or quote document generation is complete.
```

## Automated Checks

Run:

```powershell
git diff --check
docker compose exec backend alembic upgrade head
docker compose exec backend alembic current
docker compose exec backend alembic heads
docker compose exec backend pytest
docker compose run --rm frontend npm run build
docker compose run --rm frontend npm test
```

## Deferred Checks

Do not test these as Slice 6F deliverables:

```text
- line-level T&C selection;
- clause text editing inside Commercial Offer;
- deviation/new-clause approval;
- omitted mandatory-clause approval;
- quote/PDF generation;
- legal versioning;
- SharePoint/document automation;
- Work Order release/posting;
- billing.
```

## Handoff Contract Check

The frozen Slice 6D.1 Accepted Offer -> Work Order handoff contract is unchanged.
