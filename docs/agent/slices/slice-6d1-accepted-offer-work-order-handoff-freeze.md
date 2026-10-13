# Slice 6D.1 - Accepted Offer To Work Order Handoff Freeze

## Purpose

Freeze the Accepted Commercial Offer to Work Order shell handoff contract so CRM and Equipment Hiring production MVP workstreams can proceed in parallel.

This is a documentation and contract-definition slice only.

## Scope

In scope:

```text
- Document the handoff trigger from accepted/awarded Commercial Offer to Work Order shell.
- Freeze header payload fields needed by Hiring.
- Freeze line payload fields and Commercial Offer line identity rules.
- Define Work Order shell output expectations.
- Define authorization, traceability, event/audit and terminology controls.
- Define parallel agent responsibilities for CRM, Hiring, Platform/NFR and UAT.
- Update current handoff/backlog/continuity docs.
```

Out of scope:

```text
- No application code.
- No backend or frontend logic.
- No Docker, Compose or deployment change.
- No database model, migration, schema or runtime configuration change.
- No test change.
- No Customer Master activation.
- No Finance approval for Customer Master.
- No Work Order release/posting.
- No equipment or crew assignment.
- No log sheets, billing or invoicing.
- No full approval workflow.
- No full credit exposure calculation engine.
- No full Commercial Offer revision/versioning.
- No full T&C automation.
- No SharePoint integration automation.
```

## Files Created

```text
docs/planning/ACCEPTED_OFFER_TO_WORK_ORDER_HANDOFF_FREEZE.md
docs/planning/ACCEPTED_OFFER_TO_WORK_ORDER_PAYLOAD_SPEC.md
docs/planning/CRM_HIRING_PARALLEL_AGENT_CONTRACT.md
docs/agent/contracts/accepted-offer-to-work-order-handoff-contract.md
docs/agent/slices/slice-6d1-accepted-offer-work-order-handoff-freeze.md
docs/agent/acceptance/slice-6d1-accepted-offer-work-order-handoff-freeze-acceptance.md
docs/continuity/SLICE_6D1_ACCEPTED_OFFER_WORK_ORDER_HANDOFF_FREEZE.md
```

## Files Updated

```text
docs/agent/contracts/commercial-offer-contract.md
docs/agent/contracts/work-order-contract.md
docs/continuity/NEXT_STEPS.md
docs/agent/FUTURE_SLICES.md
docs/agent/AGENT_HANDOFF.md
```

## Freeze Summary

Handoff trigger:

```text
Accepted/awarded Commercial Offer with Account traceability and stable selected/active Commercial Offer lines creates a Work Order shell only.
```

Frozen header identity:

```text
Commercial Offer public ID/number/version reference
Opportunity public ID
Account public ID and display name
PAN where available
offer mode
acceptance/award reference and accepted date
document metadata/references
Commercial Offer credit/exposure approval reference where applicable
correlation ID
source status/event references
```

Frozen line identity:

```text
Commercial Offer line public ID
stable line sequence
equipment/service details where available
billing UOM
rate fields where available
duration, site, GSTN and billing-party details where available
mobilisation/demobilisation notes where available
document, T&C and pricing evidence references where available
line status
```

## Important Mapping

The current prototype creates Work Orders with:

```text
HANDOFF_CREATED
```

Production MVP may use:

```text
DRAFT
HANDOFF_RECEIVED
PENDING_CUSTOMER_MASTER
```

The frozen meaning is the same: unreleased, non-posted and not executable.

## Checks

Required check for this docs/contract-only slice:

```powershell
git diff --check
```

No backend or frontend tests are required because no application code changed.

## Known Follow-Ups

Future production implementation must decide:

```text
- final Work Order initial status name;
- exact Commercial Offer version/reference treatment before full revisioning;
- minimum PAN/GSTN/site/billing-party fields for MVP handoff;
- whether credit/exposure approval reference is mandatory before handoff or before Work Order release;
- partial award and multiple Work Order treatment;
- production document metadata and repository process.
```
