# Slice 6I.1 - Commercial Offer Detail Tabbed Navigation Polish

## Status

Implemented; final manual browser acceptance is recorded in the matching acceptance checklist.

## Objective

Reduce scroll burden on the Commercial Offer detail page by grouping existing sections into lightweight client-side tabs without changing application behavior.

## Implemented Scope

Frontend route:

```text
/commercial-offers/[commercialOfferId]
```

The page groups its existing content into:

```text
Overview
- offer snapshot;
- Opportunity and Account context;
- commercial summary;
- submission/outcome notes;
- workflow position and deferred boundaries.

Lines & Pricing
- Commercial Offer lines;
- rate basis and pricing evidence.

Terms & Conditions
- recommended header T&C readiness;
- Attach Recommended Clauses;
- manual header T&C attachment/list/remove;
- local T&C action feedback.

Submission
- advisory Submission Readiness;
- Submission Evidence list and add form;
- local submission evidence feedback.

Traceability
- linked Work Order shell records and navigation;
- audit/event references already available to the current role.
```

Overview is selected by default. The tablist uses button, `tablist`, `tab`, `aria-selected`, `aria-controls` and `tabpanel` semantics. Tabs can scroll horizontally on narrow screens.

The existing page header retains lifecycle/status actions and origin-aware return navigation so critical actions remain clear.

## Behavior Preserved

- Existing Commercial Offer detail loading and update actions.
- Account and Opportunity traceability links.
- Commercial Offer line and pricing evidence actions.
- Slice 6F manual T&C attach/remove behavior and local messages.
- Slice 6G recommended T&C readiness, Attach Recommended Clauses behavior and local messages.
- Slice 6H advisory Submission Readiness logic.
- Slice 6I Submission Evidence list/add behavior and local messages.
- Linked Work Order shell navigation and role-aware audit/event links.

## Boundaries

This is frontend navigation polish only. It adds no backend route, API/schema change, database migration, persistence change, business event, permission rule or lifecycle rule.

It does not implement quote/PDF generation, document upload/storage, approval workflow, legal T&C approval, credit/exposure calculation, Work Order release/posting or Customer Master activation.

## Handoff Contract Impact

No change was made to the frozen Slice 6D.1 Accepted Commercial Offer -> Work Order handoff contract.

