# Terms And Conditions Clause Library Contract - Slice 6E Foundation

## Purpose

Slice 6E creates a read-only foundation for a Terms and Conditions clause library.

The library lets authenticated users view, search and filter source-derived prototype T&C clauses for CRM and Commercial Offer preparation.

These records are prototype/test clause records derived from the ERP source extracts. They are not final legal-approved clauses.

## Backend Routes

```text
GET /api/tc-clauses
GET /api/tc-clauses/{public_id}
```

Frontend callers must use relative `/api/...` URLs.

## Frontend Route

```text
/terms-and-conditions
```

The page is reachable from the main navigation and the dashboard.

## Database Record

```text
tc_clause_library
```

Public identifier:

```text
public_id
```

Visible source-derived clause identifier:

```text
clause_id
```

Seeded prototype clause IDs use the source-derived pattern:

```text
TRANS-TC-001
HIRE-TC-001
```

## Fields

```text
public_id
clause_id
business_line
clause_category
source_clause_number
title
clause_text
mandatory_default
risk_category
applies_to_header
applies_to_line
requires_approval_if_omitted
requires_approval_if_modified
active
source_reference
created_at
updated_at
```

## Seed Data

Slice 6E seeds 15 source-derived prototype clauses:

```text
8 Transportation clauses
7 Equipment Hiring clauses
```

The seed records are based on:

```text
docs/reference/erp-source-extracts/TERMS_AND_CONDITIONS_EXTRACT.md
docs/agent/fixtures/terms-and-conditions/tc-clause-library-demo.json
```

The source `.docx` remains authoritative for exact wording.

## List Filters

`GET /api/tc-clauses` supports:

```text
limit
offset
business_line
clause_category
active
applies_to_header
applies_to_line
search
```

`search` checks:

```text
clause_id
title
clause_text
```

Supported business-line values:

```text
TRANSPORTATION
HIRING
```

The API also accepts common Hiring aliases such as `Equipment Hiring` and normalizes them to `HIRING`.

## Roles

Read access:

```text
ADMIN
SALES_USER
SALES_MANAGER
FINANCE_USER
OPERATIONS_USER
MANAGEMENT_READ_ONLY
```

Backend authorization is authoritative. Frontend visibility is only UX.

## Business Events

Slice 6E is read-only after seeded migration data is loaded. Clause list and detail reads do not create `business_event` records.

Future create/update/deactivate, clause selection, clause modification, omission, approval request, approval and rejection actions must create business events.

## Deferred Scope

Slice 6E does not implement:

```text
- attaching clauses to Commercial Offers;
- line-level T&C selection;
- clause modification/deviation approval;
- customer-specific T&C negotiation workflow;
- quote PDF/document generation;
- full legal approval/versioning workflow;
- SharePoint/document automation;
- billing logic;
- Work Order release/posting;
- changes to the frozen Accepted Offer -> Work Order handoff contract.
```

## Commercial Offer Boundary

The Commercial Offer module may use this library in later slices. Slice 6E does not attach clauses to Commercial Offer headers or Commercial Offer lines.

Future slices must preserve:

```text
Commercial Offer public ID
Commercial Offer line public ID
Accepted Offer -> Work Order handoff contract
```

## Slice 6F Commercial Offer Header Attachments

Slice 6F allows active header-applicable library clauses to be attached to a Commercial Offer header.

Commercial Offer attachment routes:

```text
GET    /api/commercial-offers/{public_id}/tc-clauses
POST   /api/commercial-offers/{public_id}/tc-clauses
DELETE /api/commercial-offers/{public_id}/tc-clauses/{attachment_public_id}
```

Attachment table:

```text
commercial_offer_tc_clause
```

The attachment stores snapshot fields copied from `tc_clause_library` at the time of attachment:

```text
clause_id_snapshot
title_snapshot
clause_text_snapshot
business_line_snapshot
clause_category_snapshot
source_clause_number_snapshot
source_reference_snapshot
mandatory_default_snapshot
risk_category_snapshot
applies_to_header_snapshot
applies_to_line_snapshot
requires_approval_if_omitted_snapshot
requires_approval_if_modified_snapshot
```

Snapshotting is intentional. Future changes to the master library clause must not silently change wording already selected for a Commercial Offer.

Slice 6F remains a foundation slice. It does not implement:

```text
- line-level T&C selection;
- clause text editing inside Commercial Offer;
- deviation/new-clause approval;
- omitted mandatory-clause approval;
- quote/PDF/document generation;
- legal versioning workflow;
- SharePoint/document automation;
- Work Order release/posting;
- billing.
```

Attached clauses are still source-derived prototype/test records, not final legal-approved wording.

## Slice 6G Commercial Offer T&C Readiness And Recommended Clauses

Slice 6G adds a Commercial Offer readiness view that compares attached header-level clauses with active recommended header clauses from `tc_clause_library`.

Readiness routes:

```text
GET  /api/commercial-offers/{public_id}/tc-clause-readiness
POST /api/commercial-offers/{public_id}/tc-clauses/attach-recommended
```

Recommendation basis is explicit because the Commercial Offer record does not yet store a reliable business line:

```text
recommendation_basis = TRANSPORTATION | HIRING
```

`business_line` is accepted as a compatibility alias. It is not persisted by this slice.

Recommended clauses must be:

```text
- active;
- header-applicable;
- from the selected recommendation basis.
```

The readiness response marks each recommended clause as:

```text
ATTACHED
NOT_ATTACHED
```

`attach-recommended` attaches only missing recommended clauses. It is idempotent when all recommended clauses are already attached and reuses the Slice 6F attachment snapshot and `CommercialOfferTcClauseAttached` event behavior.

Slice 6G remains a prototype readiness slice. It does not implement line-level T&C selection, clause editing, omitted mandatory-clause approval, deviation/new-clause approval, quote/PDF generation, legal versioning, SharePoint automation, billing, Work Order release/posting or any change to the frozen Accepted Offer -> Work Order handoff contract.

## Slice 6H Use In Submission Readiness

Slice 6H reuses the Slice 6G T&C readiness logic inside:

```text
GET /api/commercial-offers/{public_id}/submission-readiness
```

If `recommendation_basis` is supplied, the submission-readiness checklist reports whether recommended header clauses are attached or missing.

If no basis is supplied, the T&C checklist item is attention/not assessed and asks the user to select a recommendation basis. This is not a system failure and does not create or attach clauses.

The submission-readiness checklist remains advisory. It does not approve T&C wording, does not implement omitted mandatory-clause approval, does not implement deviation/new-clause approval and does not add line-level T&C.
