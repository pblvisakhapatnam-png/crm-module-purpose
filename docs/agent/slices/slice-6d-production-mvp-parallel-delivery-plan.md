# Slice 6D - Production MVP Scope and Parallel Delivery Plan

## Purpose

Create a documentation/planning pack for a production-grade MVP that can be delivered faster by running CRM and Equipment Hiring in parallel workstreams.

This slice replaces the earlier planned 6D T&C implementation slot. T&C implementation is moved later in the backlog.

## In scope

```text
- Define production-grade MVP meaning.
- Define minimum CRM production scope.
- Define minimum Equipment Hiring production scope.
- Define Platform/NFR and UAT/documentation parallel workstreams.
- Define CRM-to-Hiring handoff freeze checklist.
- Define deferred scope decisions needed to protect a 1-2 month timeline.
- Update continuity and future-slice pointers.
```

## Out of scope

```text
- No application code changes.
- No backend logic changes.
- No frontend logic changes.
- No Docker changes.
- No database model changes.
- No migrations.
- No tests.
- No API contract changes.
- No production deployment implementation.
```

## Files added

```text
docs/planning/PRODUCTION_MVP_SCOPE_AND_PARALLEL_DELIVERY_PLAN.md
docs/planning/CRM_HIRING_PARALLEL_WORKSTREAM_SPLIT.md
docs/planning/MVP_DEFERRED_SCOPE_DECISIONS.md
docs/planning/CRM_TO_HIRING_HANDOFF_FREEZE_CHECKLIST.md
docs/agent/slices/slice-6d-production-mvp-parallel-delivery-plan.md
docs/agent/acceptance/slice-6d-production-mvp-parallel-delivery-plan-acceptance.md
docs/continuity/SLICE_6D_PRODUCTION_MVP_PARALLEL_DELIVERY_PLAN.md
```

## Files updated

```text
docs/continuity/NEXT_STEPS.md
docs/agent/FUTURE_SLICES.md
docs/agent/AGENT_HANDOFF.md
```

## Planning finding

A 1-2 month timeline is feasible only as a tightly scoped production MVP.

It is not feasible for full CRM plus full Equipment Hiring plus full integrations, advanced approvals, advanced analytics, full document automation and deep billing/execution automation.

## Parallel delivery rule

Parallel CRM and Hiring work is acceptable only if this is frozen early:

```text
Accepted Commercial Offer -> Work Order header and lines handoff contract
```

The freeze must cover:

```text
- Work Order header payload.
- Work Order line payload.
- Account/Customer identity.
- PAN/GSTN/site/billing terms.
- Commercial Offer version/reference.
- Commercial Offer line identity.
- Credit decision reference.
- Document metadata/link references.
- Status/event names.
- Authorization expectations.
```

## Testing notes

Required check:

```powershell
git diff --check
```

No backend or frontend tests are required because this is documentation-only.
