# Slice 4C - Commercial Offer Update / Status Foundation

## Purpose

Slice 4C adds controlled Commercial Offer header updates and early status movement.

The slice keeps Commercial Offer as the single foundation object for Plum-generated quotes and external/customer/tender-format commercial responses.

## In scope

```text
PUT /api/commercial-offers/{public_id}
CommercialOfferUpdated business event
CommercialOfferStatusChanged business event when status changes
Frontend edit/status action from Commercial Offer profile
Sales/Admin backend permission enforcement
Read-only access for Finance, Operations and Management Read Only roles
```

Editable foundation fields:

```text
offer_title
offer_mode
offer_type
offer_status_code
offer_value
currency_code
offer_date
valid_until
remarks
```

Slice 4C status movement is intentionally limited to early foundation statuses:

```text
DRAFT
READY_FOR_REVIEW
WITHDRAWN
```

## Out of scope

```text
Quote line-item engine
Rate master
Market-rate capture engine
Historical Plum-rate import/comparison
Revision workflow
Submission workflow
Approval workflow
Credit checks
Tender/customer submission proof
Award/acceptance capture
Work Order handoff
Billing, OT, breakdown or invoice logic
```

## Notes for later agents

- `SUBMITTED`, `REVISED`, `ACCEPTED`, `REJECTED` and `CLOSED` are seeded for lifecycle orientation but are not available as Slice 4C update targets.
- The profile continues to show pricing-evidence placeholders from Slice 4B.
- Future slices should replace placeholders with API-backed Operations market-rate records, selected basis rate, selection rationale and historical Plum-rate comparison.
- Cross-profile return navigation remains a carry-forward item.
