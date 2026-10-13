# Slice 6G - Commercial Offer T&C Readiness And Recommended Clause Foundation

## Objective

Add a narrow Commercial Offer T&C readiness foundation using the existing Slice 6E T&C library and Slice 6F header attachment mechanism.

The slice helps Sales/Admin users see which recommended header-level clauses are attached for a selected recommendation basis and attach the missing recommended clauses in one action.

## Implemented Scope

- Added `GET /api/commercial-offers/{public_id}/tc-clause-readiness`.
- Added `POST /api/commercial-offers/{public_id}/tc-clauses/attach-recommended`.
- Supported explicit recommendation basis values:
  - `HIRING`
  - `TRANSPORTATION`
- Accepted `business_line` as a compatibility alias for `recommendation_basis`.
- Listed only active, header-applicable clauses from `tc_clause_library`.
- Marked recommended clauses as `ATTACHED` or `NOT_ATTACHED`.
- Added readiness counts:
  - total recommended
  - attached recommended
  - missing recommended
  - attached optional
- Reused Slice 6F attachment snapshots and `CommercialOfferTcClauseAttached` events.
- Made `attach-recommended` idempotent when all recommended clauses are already attached.
- Added a readiness panel to the Commercial Offer detail page above the existing 6F manual attachment list.

## Authorization

Readiness follows Commercial Offer read roles.

Attach recommended follows the existing Commercial Offer header T&C write roles:

```text
ADMIN
SALES_USER
SALES_MANAGER
```

## Out Of Scope

- No line-level T&C selection.
- No clause editing inside Commercial Offer.
- No approval workflow.
- No omitted mandatory-clause approval.
- No hard block on Commercial Offer submission.
- No quote/PDF generation.
- No legal versioning.
- No SharePoint or document automation.
- No billing.
- No Work Order release/posting.
- No change to the frozen Slice 6D.1 Accepted Offer -> Work Order handoff contract.
- No dependency/security upgrade.

## Notes

The Commercial Offer record does not yet store a reliable business line, so the UI requires the user to select a recommendation basis. This value is used only for the readiness comparison and is not persisted by this slice.

The readiness status is prototype guidance only. It does not mean clauses are legally approved.
