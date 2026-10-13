# Slice 6A.1 - Commercial Offer Account Link Guard and Repair Path

## Purpose

Close the demo/business-flow gap where a Commercial Offer can exist without Account traceability through its linked Opportunity / `business_party` chain.

The UI term is Account. The internal/domain/database term is `business_party`.

## In scope

```text
- Display linked Account clearly on the Commercial Offer profile when available.
- Display a prominent missing-Account traceability block when Account context is absent.
- Block Commercial Offer submission and acceptance when Account traceability is absent.
- Block Work Order shell creation from an Accepted Commercial Offer when Account traceability is absent.
- Provide the safest existing repair route by linking back to the Opportunity context, where users can inspect the Lead / Account trace.
- Keep backend validation authoritative and frontend blocking as usability support.
- Add backend tests for the missing Account blocking path.
```

## Out of scope

```text
- No Customer Master activation.
- No Finance approval.
- No Work Order release/posting.
- No equipment assignment.
- No crew assignment.
- No log sheets.
- No billing.
- No new Account relinking workflow.
- No full approval workflow.
```

## Backend behavior

Commercial Offer lifecycle update now rejects these target statuses when `account_public_id` cannot be resolved:

```text
SUBMITTED
ACCEPTED
```

Work Order shell creation from Commercial Offer now rejects handoff when the source Commercial Offer cannot resolve Account traceability through its copied `business_party_id` or the linked Opportunity `business_party_id`.

Both guards return:

```text
422 Unprocessable Entity
```

No database schema change is required.

## Frontend behavior

Commercial Offer profile:

```text
- Shows linked Account as a first-class linked record when available.
- Shows a prominent Account traceability missing block when absent.
- Disables Submit/Accept save action in the edit form when the selected status requires Account traceability.
- Hides Create Work Order shell when the offer is Accepted but Account traceability is missing.
- Shows a blocked Work Order handoff message with a link to the Opportunity context.
```

Work Order handoff page:

```text
- Shows source Commercial Offer Account context.
- Shows a blocked message when Account traceability is missing.
- Disables Create Work Order shell when Account traceability is missing.
```

## Repair route

Slice 6A.1 does not invent a new Account-management workflow. The safe repair path is to open the linked Opportunity context and repair through the existing Lead / Account / Opportunity flow where supported.

If the Opportunity was created manually and has no Account link, later agents should add a controlled Opportunity-to-Account linking slice rather than bypassing Account traceability from Commercial Offer or Work Order.

## Events

No new business event is created for the blocked validation path. Existing successful actions continue to record their established events:

```text
CommercialOfferSubmitted
CommercialOfferAccepted
WorkOrderCreated
CommercialOfferConvertedToWorkOrder
```

Because Slice 6A.1 prevents the invalid business action before state change or Work Order insertion, no success event is emitted for blocked attempts.
