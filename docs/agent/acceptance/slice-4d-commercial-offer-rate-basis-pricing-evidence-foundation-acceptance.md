# Slice 4D Acceptance - Commercial Offer Rate Basis / Pricing Evidence Foundation

## Automated checks

```text
- Alembic upgrade head passes.
- Backend pytest passes.
- Frontend build passes.
- Frontend test script passes.
```

## Manual happy path

```text
1. Login as sales1 / password.
2. Open /commercial-offers.
3. Open a Commercial Offer profile.
4. Add a market-rate pricing evidence entry.
5. Add a historical Plum-rate comparison entry.
6. Select one entry as the basis rate and enter a rationale.
7. Confirm the profile shows exactly one selected basis rate.
8. Confirm CommercialOfferMarketRateAdded, CommercialOfferHistoricalRateAdded and CommercialOfferBasisRateSelected are recorded by the API response/UI event message.
```

## Manual permission check

```text
1. Login as finance1 / password.
2. Open the same Commercial Offer profile.
3. Confirm pricing evidence is visible.
4. Confirm add/select actions are not available.
```

## Manual validation check

```text
1. Login as sales1 / password.
2. Try adding pricing evidence without equipment/service description.
3. Try adding pricing evidence with a negative rate amount.
4. Try selecting a basis rate without a selection reason.
5. Confirm each validation is blocked.
```

## Explicit exclusions

```text
No automated Plum integration.
No line-item engine.
No rate master.
No approval workflow.
No credit checks.
No tender submission workflow.
No Work Order handoff.
```

## Changed 11 October 2026: market rates per offer line (Slice 4G)

The steps above add rates and choose a basis for the whole offer. Since Slice 4G every rate is entered on a line and the
basis is chosen per line, with each line's history, so these steps no longer run as written. Use
`docs/agent/acceptance/slice-4g-market-rates-per-offer-line-acceptance.md` instead.
