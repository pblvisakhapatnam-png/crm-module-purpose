# CRM Hiring Parallel Agent Contract

## Purpose

This document tells future CRM, Hiring, Platform/NFR and UAT agents how to work in parallel after the Accepted Commercial Offer to Work Order handoff is frozen.

It is a planning document only. It does not assign runtime services or implement new functionality.

## Contract Anchor

All parallel work must preserve:

```text
docs/agent/contracts/accepted-offer-to-work-order-handoff-contract.md
docs/planning/ACCEPTED_OFFER_TO_WORK_ORDER_PAYLOAD_SPEC.md
```

The handoff is not an informal screen-to-screen dependency. It is the contract between CRM and Equipment Hiring.

## CRM Agent Responsibilities

CRM agents own:

```text
- Lead.
- Account / Qualified Prospect.
- Opportunity.
- Commercial Offer.
- Commercial Offer lines.
- pricing evidence.
- Commercial Offer lifecycle.
- Accepted offer/award trigger.
- CRM events and reports.
```

CRM agents may continue cleanup only if they preserve:

```text
- Commercial Offer public ID;
- Commercial Offer number/code;
- Opportunity public ID;
- Account public ID;
- Account display name;
- offer mode;
- accepted/award reference and date;
- Commercial Offer line public ID;
- line sequence;
- selected/awarded line status;
- source event references.
```

CRM agents must allow the frozen handoff to support one accepted Commercial Offer creating one or more Work Order shells for partial award or selected-line handoff. They must keep selected or awarded line identity stable for each shell created later by Hiring.

CRM agents must not:

```text
- regenerate line public IDs;
- silently relink the Commercial Offer to a different Opportunity or Account;
- remove Account traceability from submit, accept or handoff checks;
- replace Commercial Offer lines with header free text;
- change the handoff payload without contract review.
```

## Hiring Agent Responsibilities

Hiring agents own:

```text
- Work Order header and lines.
- Accepted-offer handoff consumption.
- Customer Master request/activation checkpoint.
- Work Order release/posting gate.
- equipment assignment foundation.
- crew eligibility foundation.
- log sheet foundation.
- billing calculation foundation for agreed MVP scenarios.
- invoice-support handoff.
- Hiring events and reports.
```

Hiring agents may build against:

```text
- the frozen payload spec;
- a fixture matching the payload spec;
- current prototype fields where production fields are still placeholders.
```

Hiring agents must support partial award and selected-line handoff. One accepted Commercial Offer may create one or more Work Order shells, and every Work Order line must retain the source Commercial Offer line public ID.

**Amendment, 8 October 2026 (CS-04 part 1, HOF-2; the project owner for PBL).** Recorded in full at the end of
`docs/agent/contracts/accepted-offer-to-work-order-handoff-contract.md`. In short: a Base Offer or a Supplementary
Offer is handed off, never a Change Quotation (cited on a Work Order amendment); the offer's latest customer response
must be the acceptance or award; an offer line's quantity goes onto Work Orders once, whole or in parts - the Work
Order lines of one offer line hold no more than its quantity, each keeping its source line public ID (splitting by
quantity is now in force, with no separate split reference: the Work Order line is its own reference); and an offer
with a Work Order is not recorded lost.

**Amendment, 12 October 2026 (CS-04 part 2, items c and d; the project owner for PBL).** Recorded in full at the end of
the same contract. In short: the Work Order output and both handoff events carry `commercial_offer_version_number`,
and a Work Order from a later version is titled with it ("Work Order from CO-000123 v2");
`CommercialOfferConvertedToWorkOrder` lists each Work Order line made - its source offer line, its own public ID,
quantity, unit, currency and amount. A request key that replays a repeat, and a correlation id, are agreed for later.

If the handoff carries a Commercial Offer credit/exposure decision or approval reference, Hiring should keep that reference visible for release readiness. It does not replace the future Work Order release credit/readiness gate.

Hiring agents must not:

```text
- invent a separate customer identity when Account traceability is present;
- treat Account creation as Customer Master activation;
- release or post a Work Order from shell creation alone;
- drop source Commercial Offer line identity from Work Order lines;
- bypass backend authorization or event creation.
```

## Platform / NFR Agent Responsibilities

Platform/NFR agents own:

```text
- authentication/session policy;
- backend authorization checks;
- role matrix hardening;
- audit/event visibility;
- environment and secret handling;
- migrations and backup/restore;
- observability and support diagnostics;
- deployment runbooks.
```

Platform/NFR agents should test:

```text
- unauthorized handoff attempts;
- missing Account traceability;
- missing or invalid Commercial Offer line IDs;
- audit/event creation;
- relative /api routing in browser calls;
- absence of secrets in payloads and docs.
```

## UAT / Documentation Agent Responsibilities

UAT/documentation agents own:

```text
- end-to-end scripts from Lead to Work Order shell;
- vendor demo scripts;
- role and negative-path checks;
- payload examples;
- deferred-scope sign-off;
- training notes.
```

UAT scripts should explicitly prove:

```text
- Accepted Commercial Offer creates only a Work Order shell;
- one accepted Commercial Offer can create one or more Work Order shells for partial award or selected-line handoff;
- (since 8 October 2026, CS-04 part 1) an offer line's quantity is never handed off past its total, a Change
  Quotation is refused, and an offer with a Work Order cannot be recorded lost;
- Work Order lines preserve source Commercial Offer line public IDs;
- Account traceability cannot be bypassed;
- Customer Master activation and Work Order release are still deferred;
- event/audit expectations are visible through approved roles.
```

## Safe Parallel Work

Parallel work is safe when:

```text
- CRM keeps the frozen fields stable;
- Hiring builds from fixtures or APIs that match the frozen payload;
- Platform tests the same permission and event expectations;
- UAT scripts use the same status, field and terminology names.
```

## Unsafe Parallel Work

Parallel work is unsafe when:

```text
- CRM changes Commercial Offer line identity after Hiring starts;
- Hiring changes the customer identity model without CRM and Finance agreement;
- either team assumes Customer Master activation has already happened;
- Work Order release, billing or invoicing is implemented from shell creation alone;
- the Commercial Offer credit/exposure reference is treated as a substitute for the Work Order release credit/readiness gate;
- event names or authorization expectations are changed without contract review.
```

## Contract Change Process

Any post-freeze change must record:

```text
- requested change;
- reason;
- affected fields;
- affected agents/workstreams;
- migration/API/test impact;
- UAT impact;
- approval owner;
- implementation slice.
```

Until that record exists, agents should treat the freeze as binding.

## Explicit Out Of Scope

This agent contract does not implement:

```text
- Customer Master activation;
- Finance approval for Customer Master;
- Work Order release/posting;
- equipment assignment;
- crew assignment;
- log sheets;
- billing;
- invoicing;
- full approval workflow;
- full Commercial Offer credit/exposure calculation engine;
- full Commercial Offer revision/versioning;
- full T&C automation;
- SharePoint integration automation.
```
