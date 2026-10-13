# Slice 1H Acceptance - Account Addresses Foundation

## Automated checks

- [ ] `docker compose exec backend alembic heads` shows `20260702_0008`.
- [ ] `docker compose exec backend alembic upgrade head` succeeds.
- [ ] `docker compose exec backend alembic current` shows `20260702_0008 (head)`.
- [ ] `docker compose exec backend pytest` passes.
- [ ] Frontend safe build/test sequence passes.

## Backend API checks

- [ ] Unauthenticated `GET /api/accounts/{public_id}/addresses` returns 401.
- [ ] Sales user can create an Account address.
- [ ] Read-only user can list Account addresses.
- [ ] Finance user can view but cannot create Account addresses.
- [ ] Missing Account returns 404 for address create.
- [ ] Invalid address type returns 422.
- [ ] Address create records `AccountAddressCreated` with record type `business_party_address`.
- [ ] Repeated pytest runs do not keep adding test Account/Address records.

## Manual UI checks

- [ ] Login as `sales1` or `admin1`.
- [ ] Open `/accounts`.
- [ ] Open an Account detail page.
- [ ] Confirm Addresses section is visible.
- [ ] Add an address with type, line 1, city and state.
- [ ] Confirm the address appears in the list.
- [ ] Try invalid/missing required fields and confirm friendly error handling.
- [ ] Login as `finance1`, `ops1` or `readonly1`.
- [ ] Confirm Addresses are visible but the add Address form is not available.
- [ ] Confirm Contacts still work.
- [ ] Confirm Account list pagination and viewed-this-session markers still work.

## Out of scope confirmation

- [ ] No address edit/delete added.
- [ ] No Finance-approved billing address workflow added.
- [ ] No Customer Master activation added.
- [ ] No PAN/GST statutory validation added.
- [ ] No Work Order site address logic added.
