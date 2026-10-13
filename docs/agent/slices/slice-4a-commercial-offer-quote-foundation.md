# Slice 4A - Commercial Offer / Quote Foundation

## Objective

Create Commercial Offer / Quote as its own foundation object linked to Opportunity, while preserving future paths for tender response, approval, credit checks, Work Order handoff, Equipment Hiring and Transportation.

## Scope

In scope:

```text
- Create crm_commercial_offer table.
- Seed commercial_offer workflow statuses.
- POST /api/commercial-offers.
- GET /api/commercial-offers.
- GET /api/commercial-offers/{public_id}.
- Link each Commercial Offer to one Opportunity.
- Carry Account context from the Opportunity where present.
- Generate a foundation offer_code using CO- style numbering.
- Record CommercialOfferCreated business event.
- Add frontend list/create/detail foundation pages.
- Add Opportunity profile shortcut to create a Commercial Offer for that Opportunity.
```

Out of scope:

```text
- Quote line items.
- Rate master.
- Revision workflow.
- Submission workflow.
- Approval workflow.
- Credit checks and exposure consumption.
- Award capture.
- Work Order handoff.
- Equipment Hiring fulfillment logic.
- Billing, OT, breakdown and invoice logic.
```

## Minimum gate

```text
1. Migration head/current visible and upgrade clean.
2. Backend pytest passes.
3. Frontend build/tests pass.
4. Manual happy path: create a Commercial Offer from an Opportunity and open the offer profile.
5. Manual permission path: Finance can view but cannot create Commercial Offers.
6. Manual validation path: missing Opportunity or invalid dates/status/mode are rejected.
7. Contracts, acceptance and continuity notes updated.
```
