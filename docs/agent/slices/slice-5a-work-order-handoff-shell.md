# Slice 5A - Work Order Handoff Shell

## Objective

Create a thin Work Order shell from an Accepted Commercial Offer so the prototype demonstrates the CRM-to-operations handoff without building Equipment Hiring execution.

## In scope

- Work Order and Work Order line tables.
- Work Order workflow seed statuses.
- Create Work Order shell from Accepted Commercial Offer.
- Copy selected accepted Commercial Offer lines into Work Order shell lines.
- Preserve links to Account / business_party, Opportunity, Commercial Offer and Commercial Offer lines.
- Work Order list and detail shell.
- Commercial Offer profile shortcut to create the Work Order shell when offer status is Accepted.
- Business events for Work Order creation and Commercial Offer handoff.

## Out of scope

- Customer Master activation and Finance approval.
- WO release/posting control.
- Site-wise GSTN, billing terms and document checklist enforcement.
- Equipment allocation, hired equipment, vendors and crew assignment.
- Log sheets, fuel, billing, invoice and profitability.
- Approval workflow and credit/exposure automation.

## Notes for future agents

The Work Order shell must not be treated as a released operational Work Order. It is a handoff record only. Future agents must add release controls and Customer Master/Finance gates before allowing execution or billing.
