# Contract Fixture and Freeze Plan

## Purpose

Turn approved logical contracts into tested compatibility boundaries that parallel agents can use.
An `APPROVED` contract authorizes its owning implementation; consumers may prepare mocks. Only a
`FROZEN` contract with reviewed fixtures authorizes independent consumer implementation against
that exact boundary.

## Fixture location and format

New packs use:

```text
docs/agent/fixtures/contracts/<contract-id>/README.md
docs/agent/fixtures/contracts/<contract-id>/manifest.yaml
docs/agent/fixtures/contracts/<contract-id>/happy/*.json
docs/agent/fixtures/contracts/<contract-id>/invalid/*.json
docs/agent/fixtures/contracts/<contract-id>/unauthorized/*.json
docs/agent/fixtures/contracts/<contract-id>/duplicate/*.json
docs/agent/fixtures/contracts/<contract-id>/dependency-failure/*.json
```

The manifest records contract/version, producer, consumers, fixture purpose, expected result and
data classification. Not every interface uses every folder, but the manifest must state why a
case is not applicable. All committed data is fictional.

Existing frozen fixture packs under `docs/agent/fixtures/accepted-offer-work-order/` remain in
place; do not relocate them merely for naming consistency.

## Ownership and workflow

1. The independent reviewer owns the contract wording and initial fixture specification.
2. The producer implementation package creates/validates producer examples and automated schema
   or contract tests.
3. Named consumers review the examples and add consumer tests without changing producer meaning.
4. Security/data owners review authorization, failure and classification cases.
5. The independent reviewer runs the freeze checklist, records evidence and changes registry status to `FROZEN` only
   when every required item passes.
6. Later changes use a new compatible version or an explicit migration/supersession plan.

## Scheduled freeze lanes

| Lane/milestone | Contracts | Contract/fixture owner | Required before |
| --- | --- | --- | --- |
| `CF-0` Shared platform | `MCF-001`, `ORA-001`, `NTF-001` | Platform, Authorization and Notifications owners | Approval/notification consumers and existing API/event retrofit; ORA freeze requires Employee Master joiner/transfer/leaver/correction/stale-feed fixtures |
| `CF-1A` Account lane, sequential | `AIV-001`, then `ACP-001`, then `CEX-001` | Identity Validation, Account Master and Credit Exposure owners | Credit Exposure and Commercial Offer gate consumer work; CEX fixtures include explicit expiry, no-expiry review due, overdue hold, confirm-live and final-outcome cases |
| `CF-1B` Approval | `APR-001` after `ORA-001` | Approval Policy owner | Credit, eligibility, Customer Master, Market Hire and Billing approval consumers |
| `CF-1C` Master references | `RMR-001`, `VMR-001` after interface discovery/sample data | Resource/Vendor reference-adapter owners | Resource/Market Hire runtime adapters |
| `CF-2A` Work demand | `WRR-001` | Work Order/Resource Requirement owner | Availability, Market Hire and Assignment consumers |
| `CF-2B` Planning/eligibility | `RPA-001`, `ELA-001` | Availability/Assignment and Eligibility owners | Resource Assignment and Log Sheet fixture consumers |
| `CF-2C` Customer activation | `CMA-001` | Customer Master Activation owner | Work Order release consumer |
| `CF-3A` Market Hire | `MHA-001` after D-03/D-04 | Market Hire owner | External-resource Assignment/runtime integration |
| `CF-3B` Assignment evidence | `RAL-001` | Resource Assignment and Log Sheet owners | Log Sheet runtime integration |
| `CF-4A` Billing inputs | `WBT-001`, `LBE-001` | Work Order Terms and Billing Engine owners | Billing Engine implementation |
| `CF-4B` Invoice handoff | `BIP-001` after D-06 | Billing/Invoice Preparation owners | Invoice Preparation/Plum integration |

## Freeze deliverables

Each lane has a named work package, allowed files, contract owner, producer/consumer reviewers,
fixture manifest, automated validation command and acceptance record. The lane is complete only
when `PRODUCTION_READINESS_GATES.md` contract-freeze checks pass. A target milestone in this table
is the scheduling commitment; the independent reviewer assigns a branch/agent and calendar date when that lane becomes
the next dependency.

## Safe parallelism

- Pure-domain functions may start against reviewed frozen fixtures.
- Approved but unfrozen mocks may support UI exploration, but not a claim of compatibility.
- A downstream package must stop if it discovers an absent field/status/outcome; it cannot repair
  the producer contract silently.
