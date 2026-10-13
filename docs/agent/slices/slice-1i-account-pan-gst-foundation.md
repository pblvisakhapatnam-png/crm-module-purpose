# Slice 1I - Account PAN / GST Foundation

## Scope

Slice 1I adds early-stage PAN / GST capture for Account (`business_party`).

This slice implements Option B:

- one Account-level PAN tax profile
- multiple GSTIN rows linked to the Account

The feature remains CRM-stage statutory information only. It does not create or approve formal Customer Master tax/billing data.

## Included

- `business_party_tax_profile` table
- `business_party_gstin` table
- `GET /api/accounts/{public_id}/tax-profile`
- `POST /api/accounts/{public_id}/tax-profile`
- `POST /api/accounts/{public_id}/gstins`
- PAN and GSTIN basic format validation
- PAN/GST verification state capture
- minimal PAN / GST section on Account detail page
- role-aware create/update UI for Admin/Sales roles
- Finance/Ops/Read-only view-only treatment *(Slice 1I's first scope for Finance; superseded by the
  hardening note below - Finance captures PAN/GST details and alone sets the final verification states.
  Marked 7 October 2026, TB-1 TB1-904)*
- business events for PAN profile capture and GSTIN capture
- backend tests and test-data cleanup

## Excluded

- Customer Master activation
- Finance approval workflow
- external PAN/GST validation
- credit checks
- Work Order release checks
- GSTN-wise billing address approval
- PAN/GST duplicate workflow beyond basic GSTIN uniqueness
- edit/delete/deactivate GSTIN rows

## Implementation plan

1. Add Alembic revision `20260703_0009`.
2. Add Account tax/GST constants and schema classes.
3. Add repository/service functions for tax-profile upsert and GSTIN create/list.
4. Add API routes under Account.
5. Add backend tests for create/list/validation/permission paths.
6. Extend Account detail page with PAN / GST section.
7. Update Account contract and continuity documents.

## Completion rule

Slice 1I is complete only when:

- Alembic head/current are `20260703_0009`;
- backend pytest passes;
- frontend build passes;
- manual PAN / GST capture works for allowed users;
- Finance/Ops/Read-only users can view but not add/update (for Finance, superseded by the hardening
  note below);
- docs are committed with the code.


## Slice 1I hardening note

PAN/GST capture and verification are separated. Sales/Admin/Sales Manager roles may capture draft tax details using non-final states such as ENTERED_NOT_VERIFIED or VERIFICATION_PENDING. Finance / Accounts role is responsible for setting VERIFIED or REJECTED_INCORRECT states. Multiple GSTIN rows with the same GST state code are allowed in the CRM-stage register because Indian GST rules allow separate registrations for multiple places of business within a State/Union territory in permitted cases. Exact duplicate GSTIN values remain blocked. PAN/GST form success and error messages should appear below the relevant Save/Add button, not only at the top of the PAN/GST section.
