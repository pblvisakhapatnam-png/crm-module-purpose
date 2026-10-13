# Slice 1G Acceptance - Account Contacts Foundation

## Automated checks

Run:

```powershell
docker compose exec backend alembic heads
docker compose exec backend alembic upgrade head
docker compose exec backend pytest

docker compose stop frontend
Remove-Item -Recurse -Force .\frontend\.next -ErrorAction SilentlyContinue
docker compose run --rm frontend npm run build
docker compose run --rm frontend npm test
Remove-Item -Recurse -Force .\frontend\.next -ErrorAction SilentlyContinue
docker compose up -d frontend
```

Expected:

- Alembic has one head: `20260702_0007`.
- Backend tests pass.
- Frontend build succeeds.
- Frontend test command succeeds or returns the accepted Slice 0A stub.

## API acceptance

- Unauthenticated `GET /api/accounts/{public_id}/contacts` returns 401.
- Sales/Admin/Manager can create a Contact for an existing Account.
- Finance/Ops/Read-only can list Contacts.
- Finance/Ops/Read-only cannot create Contacts.
- Creating a Contact for a missing Account returns 404.
- Invalid email returns 422.
- Contact creation emits `AccountContactCreated` with `record_type = business_party_contact`.
- Test-created Contacts and Accounts are cleaned up by tests.

## Manual UI acceptance

1. Login as `sales1` or `admin1`.
2. Open `/accounts`.
3. Open an Account detail page.
4. Confirm Contacts section is visible.
5. Add a Contact with name, designation, phone and email.
6. Confirm Contact appears in the Contacts list.
7. Add a Contact with invalid email and confirm user-friendly validation/error handling.
8. Logout and login as `finance1`, `ops1` or `readonly1`.
9. Open the same Account detail page.
10. Confirm Contacts are visible but the add Contact form is not available.

## Regression checks

- Account list pagination still works.
- Viewed-this-session markers still work and reset on logout/new login.
- Account create page still works for allowed roles.
- Dashboard Create Account visibility remains role-aware.
- Events page remains Admin-only.