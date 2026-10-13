# Slice 1I Acceptance - Account PAN / GST Foundation

## Automated checks

Run:

```powershell
docker compose exec backend alembic heads
docker compose exec backend alembic upgrade head
docker compose exec backend alembic current
docker compose exec backend pytest

docker compose stop frontend
Remove-Item -Recurse -Force .\frontend\.next -ErrorAction SilentlyContinue
docker compose run --rm frontend npm run build
docker compose run --rm frontend npm test
Remove-Item -Recurse -Force .\frontend\.next -ErrorAction SilentlyContinue
docker compose up -d frontend
```

Expected:

- Alembic head/current show `20260703_0009`;
- backend tests pass;
- frontend build passes;
- frontend test command runs with the configured Slice 0A stub if no real frontend tests exist.

## Manual acceptance

1. Login as `sales1` or `admin1`.
2. Open `/accounts`.
3. Open an Account detail page.
4. Confirm Contacts and Addresses still load.
5. Confirm PAN / GST section is visible.
6. Save a PAN profile using a valid PAN such as `ABCDE1234F`.
7. Confirm the PAN profile appears in the section.
8. Add a GSTIN such as `29ABCDE1234F1Z5`.
9. Confirm the GSTIN appears in the GSTIN list.
10. Try invalid PAN and confirm a friendly validation error.
11. Try invalid GSTIN and confirm a friendly validation error.
12. Login as `finance1`, `ops1`, or `readonly1`.
13. Confirm PAN / GST details are visible but the add/update form is not available.
14. Confirm Account pagination and viewed-this-session markers still work.

## Negative-path checks

- unauthenticated PAN/GST API access returns 401;
- Finance user cannot create/update PAN/GST details in Slice 1I;
- missing Account returns 404;
- invalid PAN/GSTIN returns 422;
- repeated backend pytest runs must not keep adding test Account tax records to the shared development database.


## Slice 1I hardening note

PAN/GST capture and verification are separated. Sales/Admin/Sales Manager roles may capture draft tax details using non-final states such as ENTERED_NOT_VERIFIED or VERIFICATION_PENDING. Finance / Accounts role is responsible for setting VERIFIED or REJECTED_INCORRECT states. Multiple GSTIN rows with the same GST state code are allowed in the CRM-stage register because Indian GST rules allow separate registrations for multiple places of business within a State/Union territory in permitted cases. Exact duplicate GSTIN values remain blocked. PAN/GST form success and error messages should appear below the relevant Save/Add button, not only at the top of the PAN/GST section.

## PAN/GST feedback hardening

- [ ] Invalid PAN/GSTIN input shows a message below the relevant action area.
- [ ] Correcting an invalid PAN/GSTIN clears the stale message before resubmission.
- [ ] Exact duplicate GSTIN entry shows a duplicate-specific message.
- [ ] Different GSTINs with the same state code remain allowed.
- [ ] Successful PAN save and GSTIN add show local success messages.

## GSTIN input feedback fix

- [ ] Entering an invalid GSTIN shows a GSTIN-specific format message below the GSTIN action area.
- [ ] Correcting that same GSTIN field to a valid value clears the stale message and allows successful submission.
- [ ] Exact duplicate GSTIN values show a duplicate-specific message.
- [ ] Different GSTIN values with the same state code remain allowed.

## TB-1 fix TB1-800 (5 October 2026): Finance adds a GSTIN

Reconciliation, not a rewrite (ADR-013): "Finance user cannot create/update PAN/GST details in Slice 1I", above, was
Slice 1I's first scope. The hardening note replaced it - Finance sets the final states - and since PF-1A-E1 the routes
grant `ACCOUNT_TAX_CAPTURE` to Finance and `ACCOUNT_TAX_VERIFY` to Finance alone. The Add GSTIN form followed that; its
button did not, until this fix.

Test user: `finance1` / `password` (FINANCE_USER). Starting URL: any Account, `http://localhost:3000/accounts/<id>`.

1. In **GSTINs**, enter a GSTIN the Account does not hold (for example `27ABCDE1234F1Z5`), choose **Verified** in
   **GSTIN verification state**, and press **Add GSTIN**.
2. "GSTIN added." appears below the button; the GSTIN is listed with **Verified**.
3. Sign in as `sales1`: the same form offers no **Verified** or **Rejected / Incorrect**.

Negative path: before this fix step 1 showed "You do not have permission to add GSTIN details." and sent nothing.
`e2e/tests/finance-verifies-gstin.spec.ts` runs both steps on every E2E run. Still not possible, and recorded
(`docs/agent/DEFERRED_REQUIREMENTS.md`, Slice 7C's dependency on the Account module): changing the state of a GSTIN
already on the Account. Finance verifies a GSTIN by adding it, not by marking one Sales entered.
