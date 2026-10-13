# Acceptance - Slice 4E Commercial Offer Line Items / Scope Foundation

## Automated checks

```text
- Alembic migration upgrades to head.
- Backend pytest passes.
- Frontend build passes.
- Frontend test script passes.
```

## Manual happy path

```text
1. Login as sales1 / password.
2. Open /commercial-offers.
3. Open a Commercial Offer profile.
4. Add a Commercial Offer line with scope, quantity, UOM and rate.
5. Confirm the line appears in the Commercial Offer lines section.
6. Edit the line and confirm the profile refreshes with the updated line values.
7. Confirm the line has a visible public id / stable line identity.
```

## Manual permission check

```text
1. Login as finance1 / password.
2. Open the same Commercial Offer profile.
3. Confirm lines are visible.
4. Confirm add/update line actions are not available.
```

## Manual validation check

```text
1. Login as sales1 / password.
2. Try saving a line without scope/description.
3. Try saving a line with zero or negative quantity.
4. Try saving a line with negative rate.
5. Confirm validation blocks each case.
```

## Deferred acceptance

```text
- T&C master and line-level clause customization are not part of 4E.
- Approval/deviation workflow is not part of 4E.
- Quote calculation, GST/taxes and document generation are not part of 4E.
- Work Order creation and line handoff are not part of 4E.
```

