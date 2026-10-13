# Slice 1F Acceptance - Account List Pagination and Session-Viewed Links

## Automated checks

Run from repository root:

```powershell
cd <your checkout>

docker compose exec backend pytest

docker compose stop frontend
Remove-Item -Recurse -Force .\frontend\.next -ErrorAction SilentlyContinue
docker compose run --rm frontend npm run build
docker compose run --rm frontend npm test
Remove-Item -Recurse -Force .\frontend\.next -ErrorAction SilentlyContinue
docker compose up -d frontend
```

Expected:

```text
Backend tests pass, including Account list offset pagination.
Frontend build passes.
Frontend test command passes with the current Slice 0A stub message.
Frontend dev server restarts cleanly.
```

## Manual checks - pagination

1. Login as `sales1 / password` or `admin1 / password`.
2. Open `/accounts`.
3. Confirm the list auto-loads.
4. Confirm the page shows a page size note for 20 records.
5. Confirm `Refresh current page` reloads the current page.
6. If more than 20 Account records exist, confirm `Next` is enabled.
7. Click `Next` and confirm a different page of records is shown.
8. Confirm `Previous` returns to the earlier page.
9. Confirm `Previous` is disabled on the first page.
10. Confirm `Next` is disabled when there is no next page.

## Manual checks - session-viewed links

1. Login as `sales1 / password`.
2. Open `/accounts`.
3. Confirm Account links start in the unviewed colour for the current session.
4. Open one Account detail page.
5. Click `Back to Accounts`.
6. Confirm the opened Account is visually marked as viewed for this session.
7. Open another Account detail page and return.
8. Confirm both opened Accounts are marked as viewed.
9. Logout.
10. Login again.
11. Open `/accounts`.
12. Confirm the viewed markers have reset for the new login session.

## Manual checks - authorization regression

1. Login as `finance1`, `ops1`, or `readonly1`.
2. Confirm Account list can be viewed.
3. Confirm Create Account action remains hidden or unavailable.
4. Confirm Account detail can be opened.

## Exclusion checks

Confirm Slice 1F did not add:

```text
search
sorting
filters
export
total-count grid
Account edit
Contacts
Addresses
PAN/GST
Documents/events implementation
```

## Session expiry acceptance

- Leave or simulate an expired `pbl_auth_token`; the sidebar must no longer continue to show `Signed in / Logout` as if the session is active.
- When an Account list/detail API call receives HTTP 401, the frontend must clear the prototype token and switch the navigation session state to `Not signed in / Login`.
- Viewed-this-session Account markers must be cleared when the session is cleared because of expiry.

## Test data hygiene

Before and after a backend pytest run, the Account list should not keep increasing only because Account API tests created records.

Manual check if needed:

```powershell
# Count Account rows before pytest, run pytest, then count again.
# Ordinary Account API tests should clean up the rows they create.
```

Existing development/demo Accounts may remain, but repeated pytest runs should not keep adding new Slice 1B / Slice 1F test Accounts.
