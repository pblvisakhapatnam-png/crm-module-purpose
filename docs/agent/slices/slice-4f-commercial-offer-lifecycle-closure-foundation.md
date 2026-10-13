# Slice 4F - Commercial Offer Lifecycle Closure Foundation

Status: implemented by apply script.

## Purpose

Slice 4F keeps the remaining CRM foundation thin. It lets users record the basic lifecycle outcome of a Commercial Offer without building the full approval, exposure, revision, document-generation or Work Order conversion engines.

## In scope

- Controlled update of Commercial Offer lifecycle status to Draft, Ready for Review, Submitted, Withdrawn, Accepted, Rejected or Closed.
- Basic submission capture: submitted date/time, submission reference and proof note.
- Basic outcome capture: outcome date and outcome remarks.
- Business events for lifecycle movement.
- Read-only display of submission and outcome context on the Commercial Offer profile.

## Out of scope

- Formal approval workflow.
- Automated Commercial Offer exposure/availability gate.
- Initial prospect credit assessment.
- Formal revision engine and version comparison.
- Quote document generation.
- Document locking/versioning for submitted offers.
- Work Order handoff.

## Credit / exposure clarification

Future agents must not treat the Commercial Offer stage as the first credit assessment. Prospect/account credit assessment happens earlier at Account/PAN level, before the prospect is pursued seriously. That assessment assigns both credit amount and credit days.

At Commercial Offer submission, the required future control is an exposure/availability gate against the already-approved credit amount and credit days. The gate should decide whether the Commercial Offer may be submitted, must be blocked, or must be routed for approval.
