# Billing Engine to Invoice Preparation Contract

## Contract ID and status

`BIP-001` - `PROPOSED` - 12 August 2026.

## Boundary

Billing Engine owns deterministic billable results. Invoice Preparation owns grouping, statutory
context, evidence packaging, approval and Finance/Plum handoff. Neither module owns receivables.

## Minimum billing result

```text
billing_result_public_id and version
Account/Customer Master, Work Order and Work Order line references
billing period
source Log Sheet/evidence versions
contract/rate/term versions
currency
billable quantity and UOM
normal/overtime/standby charges
breakdown/downtime deductions
mobilisation/demobilisation and approved adjustments
taxable-value basis before tax
calculation breakdown and policy version
approval/exception references
status and calculated_at
```

## Invoice preparation responsibilities

- Verify active Customer Master and statutory billing identity.
- Group/split results only under approved policy while preserving source result IDs.
- Select GSTN, billing address, tax treatment and invoice period.
- Assemble Work Order/PO/log/evidence references.
- Record approval and handoff/reconciliation status with Plum or Finance.

Invoice Preparation does not recalculate charge components. A disputed calculation returns to a
versioned Billing Engine recalculation/adjustment path.

## Events

Logical facts include `BillingResultApproved`, `InvoicePreparationCreated`,
`InvoiceHandoffRequested`, `InvoiceHandoffAccepted` and `InvoiceHandoffFailed`.

## Business questions PBL needs to answer

Most of this boundary is already settled:

- grouping follows the Work Order/customer invoice instructions and may combine only compatible
  results for the same legal customer, billing GSTN/address, tax treatment, billing period,
  currency and required PO/Work Order context; incompatible instructions split invoices;
- Plum Finance owns GST/tax treatment, the final statutory invoice, invoice number, e-invoice
  references, credit/debit notes and accounting corrections;
- Hiring sends one versioned, duplicate-safe package with source results and document links;
- IT Integration Support handles transport failures, while Finance handles business rejection and
  reconciliation; and
- corrections never rewrite an accepted package or statutory invoice silently.

One genuine decision remains: `D-06` must decide whether Plum creates the first draft invoice
directly from the approved Hiring package or whether Invoice Preparation holds an intermediate
draft in Hiring. This changes authoritative ownership and the handoff shape, so Finance, Billing
and the Plum team must decide it before this contract can be approved.
