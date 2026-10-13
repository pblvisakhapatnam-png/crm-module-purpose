# Acceptance - Slice 4A Commercial Offer / Quote Foundation

## Automated checks

```text
[ ] Alembic heads/current checked after migration.
[ ] docker compose exec backend pytest passed.
[ ] Frontend production build passed.
[ ] Frontend tests passed.
```

## Functional acceptance

```text
[ ] Sales/Admin can create a Commercial Offer for an existing Opportunity.
[ ] Commercial Offer receives a visible CO-style offer_code.
[ ] Commercial Offer links to the selected Opportunity.
[ ] Commercial Offer carries Account context where the Opportunity has an Account link.
[ ] Commercial Offer list page shows the created record.
[ ] Commercial Offer detail page opens and shows profile, Opportunity context, commercial values and audit sections.
[ ] Opportunity profile provides a shortcut to create a Commercial Offer for that Opportunity.
[ ] CommercialOfferCreated event is recorded.
```

## Permission and validation acceptance

```text
[ ] Finance/Operations/Management Read Only users can list/view Commercial Offers.
[ ] Finance/Operations/Management Read Only users cannot create Commercial Offers.
[ ] Missing Opportunity is rejected.
[ ] Invalid offer mode is rejected.
[ ] Non-DRAFT create status is rejected in Slice 4A.
[ ] Valid until date earlier than offer date is rejected.
```

## Deferred

```text
Quote line items
Rate master
Revision management
Submission workflow
Approval workflow
Credit checks and exposure consumption
Tender award/acceptance capture
Work Order handoff
Equipment Hiring fulfillment
Billing, OT, breakdown and invoice logic
```
