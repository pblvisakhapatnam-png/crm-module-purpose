# Slice 6C - Vendor Demo Guide and Prototype Traceability Pack

## Purpose

Create vendor-facing and demo-facing documentation for the prototype after Slice 6B.2.

This is a documentation slice. It does not add application functionality, backend routes, database schema, API contracts, permissions, tests or UI behavior.

## In scope

```text
- Vendor demo guide for Lead -> Account -> Opportunity -> Commercial Offer -> Commercial Offer lines -> closure -> Work Order shell.
- Traceability walkthrough for Lead, Account, Opportunity, Commercial Offer and Work Order shell links.
- Deferred functionality matrix separating prototype-demonstrated features from production-required features.
- Vendor implementation handoff notes for stack flexibility, authorization, API route base, Account terminology and Commercial Offer / Work Order boundaries.
- Continuity and acceptance documentation for the slice.
- Backlog update so the next functional T&C slice is not confused with this documentation slice.
```

## Out of scope

```text
- No backend logic changes.
- No frontend code changes.
- No database model or migration changes.
- No API contract changes.
- No permission changes.
- No new tests.
- No PHP or MS-SQL migration work.
- No new product functionality.
```

## Files added

```text
docs/demo/01_VENDOR_DEMO_GUIDE.md
docs/demo/02_VENDOR_IMPLEMENTATION_HANDOFF_NOTES.md
docs/demo/03_PROTOTYPE_TRACEABILITY_WALKTHROUGH.md
docs/demo/04_PROTOTYPE_SCOPE_AND_DEFERRED_FUNCTIONALITY.md
docs/agent/slices/slice-6c-vendor-demo-guide-traceability-pack.md
docs/agent/acceptance/slice-6c-vendor-demo-guide-traceability-pack-acceptance.md
docs/continuity/SLICE_6C_VENDOR_DEMO_GUIDE_TRACEABILITY_PACK.md
```

## Files updated

```text
docs/continuity/NEXT_STEPS.md
docs/agent/FUTURE_SLICES.md
```

## Documentation behavior

The demo guide explains each step of the implemented flow:

```text
Lead
Account / Qualified Prospect
Opportunity
Commercial Offer
Commercial Offer line / pricing evidence
Commercial Offer closure
Work Order shell
```

Each step records:

```text
- purpose of the screen;
- what to demonstrate;
- key control shown;
- business event/audit expectation where applicable;
- what is not yet implemented.
```

The traceability walkthrough explains:

```text
- Lead to Account;
- Account to Opportunity;
- Opportunity to Commercial Offer;
- Commercial Offer to Work Order shell;
- Account repair / traceability guard;
- Commercial Offer active/actionable guard.
```

The deferred functionality document explicitly marks these items as deferred:

```text
Customer Master activation
Finance approval for Customer Master
Work Order release/posting
equipment assignment
crew assignment
log sheets
billing
invoicing
full approval workflow
credit exposure calculation engine
Commercial Offer revisions/versioning
T&C / clause library
production integrations
```

The vendor handoff note states:

```text
- Prototype stack is a reference only.
- Production stack may be PHP + MS-SQL.
- Backend authorization remains authoritative.
- Frontend role-awareness is only UX.
- /api is the route base.
- Frontend browser calls use relative /api URLs.
- Account is the UI term; business_party is internal/domain/database terminology.
- Commercial Offer is the common control record for quotes, external quotes, customer-format quotes and tender bids.
- Commercial Offer lines must preserve stable identity.
- Accepted Commercial Offer creates only a Work Order shell in the prototype.
```

## Events

This slice creates no new `business_event` because it is documentation-only.

Existing event expectations are documented for vendor/demo review.

## Testing notes

Required check:

```powershell
git diff --check
```

No frontend or backend tests are required because only documentation files changed.

If any code files are changed later in this slice, run the relevant build/tests and record why code changed.
