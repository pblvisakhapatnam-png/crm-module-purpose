# Slice 4D - Commercial Offer Rate Basis / Pricing Evidence Foundation

## Purpose

Slice 4D adds a narrow pricing-evidence foundation for Commercial Offers.

Commercial Offers are not based only on a typed offer value. Operations may collect multiple market rates. Sales/Admin may choose one of those rates as the offer basis, and the selected rate need not be the lowest rate. Historical Plum rates for similar work may also be captured manually for comparison.

## Scope

In scope:

```text
- Pricing evidence table linked to Commercial Offer.
- Multiple market-rate and historical Plum-rate entries per Commercial Offer.
- One selected basis rate per Commercial Offer.
- Basic source/vendor, equipment/service description, rate amount, currency, rate basis, collected-by, collected-at, source reference, comparison notes and selection rationale.
- API list/add/select-basis endpoints.
- Frontend display and capture on the Commercial Offer profile.
- Business events for added evidence and basis-rate selection.
```

Out of scope:

```text
- Automated Plum integration.
- Rate master.
- Quote line-item engine.
- Final pricing calculation engine.
- Approval workflow.
- Credit checks.
- Tender submission workflow.
- Work Order handoff.
```

## Backend routes

```text
GET  /api/commercial-offers/{public_id}/pricing-evidence
POST /api/commercial-offers/{public_id}/pricing-evidence
POST /api/commercial-offers/{public_id}/pricing-evidence/{evidence_public_id}/select-basis
```

## Data model

```text
crm_commercial_offer_pricing_evidence
```

Each record belongs to one Commercial Offer.

Evidence types:

```text
market_rate
historical_plum_rate
```

Only one evidence record can be selected as the basis rate for one Commercial Offer.

## Business events

```text
CommercialOfferMarketRateAdded
CommercialOfferHistoricalRateAdded
CommercialOfferBasisRateSelected
```

Events must not contain passwords, tokens or secrets.

## Frontend

The Commercial Offer profile now includes a Rate basis and pricing evidence section.

Users with Sales, Operations or Admin roles can add pricing evidence. Users with read access can view the pricing evidence.

## Deferred carry-forward

Future slices should decide how pricing evidence feeds into Commercial Offer line items, approval workflow, rate master governance, Plum historical extraction and final offer calculation.

## Changed 11 October 2026: market rates per offer line (Slice 4G)

Pricing evidence now belongs to one offer line, and each line has its own basis rate and basis history; quotes can be
attached to a rate. The rates recorded under this slice, for the whole offer, stay as they were and are shown apart.
See `docs/agent/slices/slice-4g-market-rates-per-offer-line.md` and the contract's "Slice 4G" section. This record is
kept as the history of the foundation.
