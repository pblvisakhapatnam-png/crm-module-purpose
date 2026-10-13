# Slice 6F - Commercial Offer T&C Attachment Foundation

## Status

Implemented.

## Objective

Allow source-derived T&C library clauses from Slice 6E to be attached to a Commercial Offer at header level.

The attachment preserves a snapshot of the selected clause details so the Commercial Offer keeps the wording that was selected at the time of attachment, even if the master clause changes later.

## Implemented Scope

Backend:

```text
- SQL Server-compatible Alembic migration for commercial_offer_tc_clause.
- Header-level T&C attachment snapshots linked to Commercial Offer and T&C clause library.
- GET /api/commercial-offers/{public_id}/tc-clauses.
- POST /api/commercial-offers/{public_id}/tc-clauses.
- DELETE /api/commercial-offers/{public_id}/tc-clauses/{attachment_public_id}.
- Backend role checks for read versus attach/remove.
- Active-clause and header-applicability validation.
- Duplicate active attachment rejection.
- Soft removal through active = 0.
- Business events for attach and remove.
```

Frontend:

```text
- Commercial Offer detail page now shows a Header T&C clauses section.
- Attached clauses are listed with snapshot title, category, mandatory/default and approval flags.
- Clause text/source detail can be expanded.
- Sales/Admin users can attach active header-applicable library clauses.
- Sales/Admin users can remove active attachments.
- Finance, Operations and Management Read Only users can view attachments but cannot attach/remove.
```

Tests:

```text
- authorized user can list attached clauses;
- authorized user can attach an active header clause;
- duplicate attachment is rejected;
- missing clause cannot be attached;
- inactive clause cannot be attached;
- line-only clause cannot be attached to the header;
- unauthorized attach/remove is rejected;
- removed clause no longer appears as an active attachment;
- snapshot fields remain unchanged if the master clause changes later;
- attach/remove business events are recorded.
```

## Data Model

New table:

```text
commercial_offer_tc_clause
```

Important fields:

```text
public_id
commercial_offer_id
tc_clause_id
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
sort_order
active
attached_by
created_at
updated_at
```

The table has a filtered unique index preventing more than one active attachment of the same T&C clause to the same Commercial Offer.

## Business Events

Implemented events:

```text
CommercialOfferTcClauseAttached
CommercialOfferTcClauseRemoved
```

Events are recorded against the Commercial Offer record because the meaningful business action is changing the Commercial Offer's selected header T&C set.

## Boundaries

This slice is header-level only.

Deferred:

```text
- line-level T&C selection;
- clause text editing inside Commercial Offer;
- deviation/new-clause approval workflow;
- approval for omitted mandatory clauses;
- quote/PDF/document generation;
- legal versioning workflow;
- SharePoint/document automation;
- billing logic;
- Work Order release/posting;
- any change to the frozen Slice 6D.1 Accepted Offer -> Work Order handoff contract;
- any further dependency/security upgrade.
```

## Legal/Source Note

Selected clauses are still source-derived prototype/test records. They are not final legal-approved wording.

Production use requires legal/business review of the source clauses and approval workflow around omissions, changes and new clauses.

## Handoff Contract Impact

No change was made to the frozen Accepted Offer -> Work Order handoff contract.
