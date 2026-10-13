# Market Hire to Resource Assignment Contract

## Contract ID and status

`MHA-001` - `PROPOSED` - 12 August 2026.

## Boundary

Market Hire owns external sourcing, quotation/approval and hire confirmation. Resource Assignment
owns operational commitment. Supplier accounting and invoice reconciliation remain outside both.

## Secured external resource

```text
market_hire_public_id/version
requirement public ID/version
supplier/business-party public ID
external resource public ID/reference and category/type
availability window and site/location
agreed supplier cost/rate reference and currency
hire approval decision/reference
confirmation reference/date
compliance/evidence references
status = SECURED (or approved equivalent)
```

Only a secured, non-cancelled version may be offered to Assignment. Assignment references this
record and does not copy supplier commercial terms into operational evidence unnecessarily.

## Lifecycle effects

Cancellation, replacement or supplier failure publishes a fact that Assignment consumes through
an explicit replacement/release workflow. It never silently relinks an active assignment.

## Business questions PBL needs to answer

Most of this boundary is already settled:

- the centralized ERP Vendor Master supplies the supplier identity; the implementation inventory
  must map that logical master to PBL's current Purchase/Finance system without creating a second
  supplier master in Hiring;
- Hiring's Vendor Equipment Register supplies the verified outside-equipment identity;
- a resource is `SECURED` only after vendor confirmation, required evidence checks and the
  approved Vendor Hire Agreement/approval reference exist;
- cancellation or replacement is explicit and auditable;
- supplier rates/costs are restricted by `ORA-001` permissions/data scope to authorized Hiring
  Operations, Procurement, Finance and Management users, not invented global role strings and not
  general Sales/site access; and
- Finance Accounts Payable owns supplier-bill accounting/reconciliation, using the approved
  vendor-payable worksheet and operational evidence.

Two genuine decisions remain:

1. `D-03`: Should vendor crew be held in Plum HR/Crew Master with a vendor flag, or in a thinner
   Hiring Vendor Resource Register? This changes the authoritative owner and must be agreed by HR,
   Hiring Operations and the Plum team.
2. `D-04`: Must every Vendor Hire Agreement also have an approved/posted Purchase Order before
   the outside resource or its Log Sheet can proceed? This changes whether Operations is blocked
   and must be agreed by Operations, Procurement and Finance.
