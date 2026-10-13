# Slice 6D.2 - Parallel Agent Work Packages

## Purpose

Create concrete, reusable implementation work packages for parallel production MVP workstreams.

This is a documentation/planning slice only. It does not change application code, backend logic, frontend logic, Docker files, database models, migrations, tests or runtime configuration.

## Workstreams Covered

```text
CRM workstream
Equipment Hiring workstream
Platform/NFR/security workstream
UAT/documentation workstream
```

## Files Created

```text
docs/planning/PARALLEL_AGENT_WORK_PACKAGES.md
docs/planning/CRM_AGENT_WORK_PACKAGE.md
docs/planning/HIRING_AGENT_WORK_PACKAGE.md
docs/planning/PLATFORM_NFR_AGENT_WORK_PACKAGE.md
docs/planning/UAT_DOCUMENTATION_AGENT_WORK_PACKAGE.md
docs/agent/slices/slice-6d2-parallel-agent-work-packages.md
docs/agent/acceptance/slice-6d2-parallel-agent-work-packages-acceptance.md
docs/continuity/SLICE_6D2_PARALLEL_AGENT_WORK_PACKAGES.md
```

## Files Updated

```text
docs/continuity/NEXT_STEPS.md
docs/agent/FUTURE_SLICES.md
docs/agent/AGENT_HANDOFF.md
```

## Common Rules Captured

All work packages state:

```text
- preserve the frozen Accepted Offer -> Work Order handoff contract;
- do not change frozen payload fields without contract-change record;
- keep Account as UI term;
- use business_party only internally;
- backend authorization remains authoritative;
- frontend role-awareness is UX only;
- meaningful business actions create business_event where applicable;
- frontend browser calls use relative /api URLs;
- no deferred production features unless explicitly assigned.
```

## Work Package Summary

CRM:

```text
Focuses on Lead / Account / Opportunity cleanup, Commercial Offer lifecycle clarity, Commercial Offer lines, pricing evidence, accepted-offer readiness, status/report visibility and preserving handoff identity.
```

Hiring:

```text
Focuses on Work Order header/line foundation from frozen payload, Customer Master activation checkpoint, release readiness gates, equipment assignment foundation, crew eligibility foundation, log sheet foundation and limited billing only after scenarios are selected.
```

Platform/NFR/security:

```text
Focuses on role matrix, backend authorization, audit/event visibility, negative paths, no secrets leakage, backup/restore, deployment notes and test reliability.
```

UAT/documentation:

```text
Focuses on end-to-end scripts, role checks, negative path checks, deferred-scope sign-off and vendor-readable acceptance evidence.
```

## Parallel Sequencing Captured

Recommended sequence:

```text
1. Confirm handoff fixtures/examples.
2. Let CRM and Hiring proceed in parallel after fixture confirmation.
3. Run Platform/NFR continuously.
4. Let UAT/docs prepare scripts in parallel.
5. Run integration checks at fixed intervals.
```

## Explicit Warning Captured

Parallel agents must not independently redefine:

```text
- customer/account identity;
- Commercial Offer line identity;
- Work Order line source identity;
- Customer Master activation boundary;
- credit/reference timing;
- document metadata policy;
- event/authorization expectations.
```

## Checks

Required check:

```powershell
git diff --check
```

No backend/frontend tests are required because this is docs-only.
