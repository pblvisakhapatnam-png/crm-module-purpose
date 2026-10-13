# Slice 6H - Commercial Offer Submission Readiness Checklist Foundation

## Objective

Add one advisory Commercial Offer submission-readiness checklist that consolidates existing controls into a clear view before a Commercial Offer is shared with a customer.

This slice is guidance only. It does not create an approval workflow, quote document, credit calculation or hard submission block.

## Implemented Scope

Backend:

```text
GET /api/commercial-offers/{public_id}/submission-readiness
```

Optional query:

```text
recommendation_basis = HIRING | TRANSPORTATION
```

The recommendation basis is used only for T&C readiness. It is not persisted as a Commercial Offer classification.

Checklist items:

```text
- Commercial Offer active/actionable.
- Account traceability present.
- Opportunity traceability present.
- Commercial Offer active lines present.
- Pricing evidence present.
- Header T&C readiness.
- Commercial Offer credit/exposure gate as deferred future control.
- Approval workflow as deferred future control.
- Quote/PDF/document generation as deferred future control.
- Submission proof as deferred future control.
```

Frontend:

```text
/commercial-offers/[commercialOfferId]
```

The Commercial Offer detail page now shows a compact Submission Readiness panel near the lifecycle/action area. It includes:

```text
- overall readiness status;
- passed/warning/blocking/deferred counts;
- checklist rows with status and message;
- T&C recommendation basis selector;
- refresh readiness action.
```

## Readiness Meaning

Overall readiness values:

```text
READY
ATTENTION_REQUIRED
NOT_READY
```

Checklist item status values:

```text
PASS
ATTENTION_REQUIRED
BLOCKING
DEFERRED
```

`BLOCKING` means the existing prototype already has a safe control boundary or the item is structurally required for meaningful submission readiness. This slice does not add a new hard lifecycle block.

## Authorization

Submission readiness follows existing Commercial Offer read authorization.

No business event is created because readiness is a read-only advisory view.

## Out Of Scope

- No hard submission blocking added by this slice.
- No quote/PDF/document generation.
- No actual quote submission workflow.
- No submission proof upload/capture.
- No credit engine or exposure calculation.
- No approval workflow.
- No omitted mandatory T&C approval.
- No T&C deviation/new-clause approval.
- No line-level T&C selection.
- No legal versioning.
- No SharePoint/document automation.
- No Work Order release/posting.
- No billing logic.
- No Customer Master activation.
- No change to the frozen Slice 6D.1 Accepted Offer -> Work Order handoff contract.
- No dependency/security upgrade.

## Notes

The checklist uses UI wording `Account`. Internal/database wording remains `business_party` where the existing implementation uses it.

T&C clauses remain source-derived prototype/test records and are not final legal-approved wording.
