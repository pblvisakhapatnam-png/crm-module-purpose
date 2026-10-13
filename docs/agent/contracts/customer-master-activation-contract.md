# Customer Master Activation Contract

## Contract ID and status

`CMA-001` - `APPROVED` - 12 August 2026.

## Boundary

Account Master owns the Qualified Prospect/legal entity. Finance-controlled Customer Master
Activation owns the decision and external Finance/Plum customer reference. Work Order owns its
release state and consumes the activation result.

## Activation request

```text
activation request public ID/version
Account public ID and verified legal-identity version/reference
PAN/GSTIN and billing identity references
trigger Work Order public ID/version
approved credit profile reference where policy requires
required document/evidence references
requester/correlation metadata
```

The request does not create a duplicate customer/account record and does not itself release the
Work Order.

## Activation decision

```text
decision public ID/version
status: PENDING / ACTIVATED / REJECTED / EXCEPTION (names subject to review)
Finance approver identity/authority and timestamp
conditions/reason
Plum/customer-master external reference where activated
effective date
evidence and reconciliation references
```

Work Order release consumes an activated decision under its readiness policy. Account remains the
same business_party; activation adds a customer role/reference.

## Settled baseline and configurable checklist

- Sales starts Customer Master activation when the first Work Order is received/created for a
  Qualified Prospect. Activation must complete before Work Order release/posting and invoicing.
- The request uses the SurePass-verified PAN/legal identity, applicable GSTIN and billing address,
  approved credit profile/reference, first Work Order and required supporting documents.
- The Finance Customer Master Owner approves or rejects activation. The permission, named
  authority assignment and data scope come from `ORA-001`; backend authorization and decision
  audit remain mandatory.
- No universal maker/checker rule is added here. Approval remains separate from the Sales request;
  any stronger Finance independence rule is configured under `APR-001`.
- Plum is checked by PAN/legal entity and applicable GSTIN before create. An existing matching
  customer is linked/reconciled; the process must not create a duplicate customer merely because
  CRM uses a different internal public ID.

The exact customer/document checklist may vary by statutory and customer type and is maintained as
Finance configuration. That parameter does not reopen the activation timing or ownership.
