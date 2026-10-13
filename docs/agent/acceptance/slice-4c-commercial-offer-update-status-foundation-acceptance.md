# Slice 4C Acceptance - Commercial Offer Update / Status Foundation

## Automated checks

Backend:

```powershell
docker compose up -d --build --force-recreate backend
docker compose exec backend pytest
```

Frontend:

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
2. Open /commercial-offers.
3. Open a Commercial Offer profile.
4. Click Edit Commercial Offer / Status.
5. Change offer title, offer value, remarks and status to Ready for Review.
6. Save.
7. Confirm the profile updates.
8. Confirm the page shows CommercialOfferUpdated and CommercialOfferStatusChanged.
```

## Manual permission check

```text
1. Login as finance1 / password.
2. Open /commercial-offers.
3. Open a Commercial Offer profile.
4. Confirm the profile is visible.
5. Confirm Edit Commercial Offer / Status is not available.
```

## Manual validation check

```text
1. Login as sales1 / password.
2. Open a Commercial Offer profile.
3. Try saving a negative offer value.
4. Confirm it is rejected.
5. Try valid-until date earlier than offer date.
6. Confirm it is rejected.
7. Confirm Submitted, Revised, Accepted, Rejected and Closed are shown as deferred and are not selectable in the Slice 4C edit form.
```

## Acceptance result

Pass when backend tests pass, frontend build/test pass, and the manual checks above behave as expected.
