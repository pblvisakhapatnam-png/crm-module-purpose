# Slice 6E - T&C Master / Clause Library Foundation

## Status

Implemented.

## Objective

Create a narrow Terms and Conditions clause library foundation using the source-derived T&C extract and fixture pack created in Slice 6D.4.

This slice allows authenticated users to view, search and filter prototype T&C clauses for CRM/Commercial Offer preparation.

## Implemented Scope

Backend:

```text
- SQL Server-compatible Alembic migration for tc_clause_library.
- Seeded 15 source-derived prototype clauses.
- Read-only T&C API module.
- GET /api/tc-clauses.
- GET /api/tc-clauses/{public_id}.
- Filters for business_line, clause_category, active, applies_to_header, applies_to_line and search.
- Backend role checks for authenticated CRM/commercial users and read-only management.
```

Frontend:

```text
- /terms-and-conditions page.
- Main navigation link.
- Dashboard card.
- Read-only clause table with search/filter controls.
- Inline clause detail view.
- Prototype/source-derived warning and deferred-scope note.
```

Tests:

```text
- authorized clause list access;
- authentication required;
- management read-only access;
- filter/search;
- detail lookup;
- missing clause 404;
- invalid business-line validation.
```

Docs:

```text
- terms-and-conditions contract;
- Commercial Offer contract cross-reference;
- slice note;
- acceptance checklist;
- continuity note;
- NEXT_STEPS, FUTURE_SLICES, AGENT_HANDOFF and CRM work-package updates.
```

## Seed Data

Seeded records:

```text
8 Transportation clauses
7 Equipment Hiring clauses
15 total clauses
```

Seed content is based on:

```text
docs/reference/erp-source-extracts/TERMS_AND_CONDITIONS_EXTRACT.md
docs/agent/fixtures/terms-and-conditions/tc-clause-library-demo.json
```

These are prototype/test records only. They are not legal-approved final clauses.

## Out Of Scope

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
- any change to the frozen Accepted Offer -> Work Order handoff contract.
```

## Business Events

This slice is read-only after migration seed data is loaded. Clause browsing does not create business events.

Future write actions must create business events.

## Handoff Contract Impact

No change was made to the frozen Accepted Offer -> Work Order handoff contract.

