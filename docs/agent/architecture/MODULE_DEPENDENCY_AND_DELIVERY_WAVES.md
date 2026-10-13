# Module Dependency and Parallel Delivery Waves

## Principle

Parallelism depends on contract readiness and file/data ownership, not the number of available
agents. A work package may start when its inbound contracts are approved/frozen and its
Definition of Ready is satisfied.

## Dependency spine

```text
Account Master [Credit Profile component] -> Credit Exposure -> Commercial Offer/WO gates

Commercial Offer -> Work Order -> Resource Requirement
                                  -> Availability -> Assignment -> Log Sheet -> Billing
                                                       ^                         -> Invoice Prep
                                  -> Market Hire -------|
                                  -> Eligibility -------|

Equipment Master -> Resource Catalogue/Availability/Eligibility/Assignment
Employee Master  -> Resource Catalogue/Eligibility/Assignment
Employee Master  -> Organization Authority -> Approval Policy/approval consumers

Shared: Authorization, Approval Policy, Identity Validation, Documents, Events/Outbox,
        Jobs, Integration Gateway, Notifications, Audit/Observability

External masters: Equipment, Employee/Crew and Vendor Master readiness is tracked in
                  EXTERNAL_DEPENDENCY_REGISTER.md
```

## Foundation gates

| Gate | Required outcome |
| --- | --- |
| `PAF-1` | Architecture records, owners and contract status are visible |
| Contract readiness | PBL has accepted the business meaning; required inbound contracts are marked `APPROVED` or `FROZEN` |
| `TE-2A` | React/Vite web migration preserves behavior and regression coverage. **Met** (`5c87e07`) |
| Database decision | **Met.** PostgreSQL explicitly confirmed by PBL and recorded as ADR-028 |
| `TE-2B` | Controlled database migration completes. **Met** (both parts integrated as `75fd4fc`) |
| `TE-2CI` | GitHub Actions required checks implement the documented validation path. **Met** (complete and hosted-verified at `8bb6af1`; enforced by ADR-031) |
| `TE-2C` | Migrated technical foundation verified; no final production-candidate claim. **Met** (`7f5a05d`, 18 August 2026) |
| `PF-1` | Shared authorization/NFR/API-event retrofit and first contract fixtures complete. **Partly met:** PF-1A is complete through E3 (7 September 2026); the API/event retrofit (PF-1B) is not built - TB-1's corrective package CS-06 holds it. The position agreed after E3 (6-7 September 2026) was to run the CRM pilot and the Hiring lane rather than a further PF package (`docs/continuity/PF_1A_E3_INTEGRATION_CLOSURE_AND_WAY_FORWARD_2026-09-07.md`, "Way forward") |

*Gate statuses reconciled 7 October 2026 (TB-1 TB1-110); commits from `docs/agent/PLAN.md`.*

`TE-2CI` may be developed alongside late TE-2A/TE-2B work, but it must be complete before TE-2C
can pass. Significant business-module schema work begins after TE-2C and the applicable PF-1/
contract gate. Approved-contract fixture design and isolated pure-domain test design may proceed
earlier. Proposed contracts may be refined, but dependent implementation waits for their named
open decision.

## Platform and contract wave after TE-2C

### PF-1 - Shared production controls

Parallel lanes where ownership is disjoint:

- `PF-1F-HR` begins first. **Status update, 31 August 2026 (PF-1F-HR-E1, ADR-032, ADR-033):** PBL
  has confirmed Plum does not currently hold a structured Organisation Unit Master, Position
  Master, Position Incumbency or HR change-feed model, and a stable Employee ID is unverified. The
  gate for this lane is no longer "validate a live, sophisticated Plum HR interface"; it is the
  accepted canonical HR reference contract, the provider-neutral adapter boundary and
  representative SharePoint-backed reference data populated against the starter specification -
  see `docs/agent/pf-1f-hr/PF_1F_HR_DECISION_GATE.md`. This remains the external/data-population
  critical-path prerequisite for ORA activation; schema/fixture design may proceed earlier, but
  live authority must not use a CRM-owned organization copy, and SharePoint is an interim source,
  not a permanent substitute for the eventual `NEW_SHARED_PLATFORM` HR/Organisation Reference
  Master.
- `PF-1A`: Organization Authority/Authorization foundation and current-role/route permission
  inventory (`ORA-001`), consuming the validated Employee Master position/employment interface.
  Include leaver/transfer change handling, stale-feed fail-closed behavior and pending-approval
  reassignment. This precedes `APR-001` and every configurable authority consumer.
- `PF-1B`: MCF retrofit foundation for current APIs/events: correlation middleware, idempotency
  infrastructure, error compatibility, event schema/version strategy and a route/event adoption
  inventory. Existing modules adopt it through explicit per-module packages; no permanent legacy
  class is accepted.
- `PF-1C`: Business Events/Transactional Outbox and Background Jobs production hardening
  (`MCF-001`, ADR-019).
- `PF-1D`: Notifications foundation (`NTF-001`), including 60/30/15-day statutory expiry and
  30-day Work Order/contract expiry scheduling patterns.
- `PF-1E`: Documents/Evidence, data classification, audit/observability and NFR evidence
  foundation, including backup/restore runbook verification.
- `PF-1F`: remaining external dependency discovery and sample-interface validation for Equipment,
  Vendor and Customer Masters, Plum receivables, SharePoint and notification providers; its HR
  critical-path sub-lane is `PF-1F-HR` above.
- `CF-0`: first shared fixture/freeze lane under `CONTRACT_FIXTURE_AND_FREEZE_PLAN.md`.

PF-1 integration gate: CI, permissions, events, jobs, classified fixtures, empty-database upgrade,
dependency failure tests and NFR baseline evidence pass together.

## Business delivery waves

### Wave 1 - Shared and master foundations

Parallel lanes where modules/files are disjoint:

- Identity/Statutory Validation provider abstraction, without writing Account Master.
- One sequential Account Master lane: Account identity adapter/state (`AIV-001`), then Account
  Credit Profile (`ACP-001`). These may not run as parallel writers even if files appear disjoint.
- Approval Policy implementation (`APR-001`) only after `ORA-001` is implemented/frozen.
- Resource Catalogue foundation.
- Equipment/Employee Master reference adapters (`RMR-001`) after external interface/sample-data
  readiness is recorded.
- Vendor Master reference adapter (`VMR-001`) after current ERP master/interface discovery.
- Per-module MCF retrofit for Account, Commercial Offer and Work Order APIs/events before new
  production behavior is added to those modules.
- `CF-1A` to `CF-1C` fixture/freeze lanes for Account, approval and master references.

Wave 1 integration gate: authorization, events, migrations, empty-database upgrade and shared
contract fixtures pass together. No module with an unfrozen outbound boundary is advertised as
ready for independent consumer coding.

### Wave 2 - Commercial and operational planning

- Credit Exposure engine and Commercial Offer commitment-review integration after `ACP-001` and
  `CEX-001` approval, including no-expiry review dates, jobs/notifications, overdue Account hold
  and migration of existing submitted offers.
- Customer Master activation/readiness after `CMA-001` approval.
- Work Order release/readiness and Resource Requirement after `WRR-001` approval.
- Compliance/Eligibility foundation after `ELA-001` approval.
- Resource Availability foundation after `RPA-001` approval.
- Market Hire foundation after `MHA-001` approval and against an approved Requirement fixture.
- Log Sheet domain model/test harness may begin against a frozen Assignment fixture, without
  inventing assignment behavior.
- `CF-2A` to `CF-2C` produce/freeze Work demand, Planning/Eligibility and Customer activation
  boundaries before their named consumers start.

### Wave 3 - Assignment and evidence

- Resource Assignment after `RPA-001`, `ELA-001` and applicable `MHA-001` contracts are ready.
- Market Hire -> Assignment integration.
- Log Sheet runtime integration after `RAL-001` freeze.
- Document/evidence and notification consumers for operational workflows.
- Eligibility expiry/recheck jobs, 60/30/15-day alerts and `EligibilityLapsed` -> Assignment
  compliance-block integration.
- `CF-3A`/`CF-3B` complete Market Hire and Assignment-to-Log-Sheet freeze work.

### Wave 4 - Billing and Finance handoff

- Billing Engine after `WBT-001` and `LBE-001` are frozen.
- Invoice Preparation after `BIP-001`, Customer Master and tax/Plum policy decisions are ready.
- Finance reconciliation and reporting read models.
- `CF-4A`/`CF-4B` freeze Billing input and invoice-handoff boundaries before dependent runtime
  work.

## Safe speculative work

Before an upstream implementation is complete, a downstream team may create:

- pure-domain functions against frozen fixtures;
- consumer contract tests;
- UI shells against approved mock responses, clearly marked unfrozen;
- acceptance scripts and negative-path matrices.

It may not claim compatibility or guess fields, statuses, permissions or business outcomes absent
from the contract. Independent consumer implementation requires a frozen fixture pack.

## Parallel ownership controls

- One work package owns a module's authoritative tables and contract at a time.
- The independent reviewer assigns owners for shared files such as router registration, dependency manifests,
  Compose, CI workflows and global configuration.
- The independent reviewer assigns Alembic revision IDs/parents. Explicit parallel heads are allowed only for
  disjoint module schemas and require an integration merge revision plus empty-database test.
- A worker does not rewrite another package's migration or contract to resolve a merge conflict.
- Every wave ends with integrated regression; passing branch tests alone is not completion.

## First coding action

The first implementation package was `TE-2A - Next.js -> React + Vite`. It is repository-wide
and should run as one controlled implementation lane. `TE-2CI` is prepared as soon as the migrated
frontend/backend/database validation commands are stable and must finish before TE-2C.

*Reconciled 7 October 2026 (TB-1 TB1-904):* TE-2A, TE-2B, TE-2CI and TE-2C are complete (the
gates above). This section records the order the foundation was built in; what is next is in
`docs/continuity/NEXT_STEPS.md`.
