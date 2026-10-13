# Production Architecture Direction

## Status

Approved architecture foundation, 12 August 2026. Documentation-only; it does not change runtime
behavior.

**Platform scope, 16 August 2026 (ADR-030).** This system shape and these dependency rules are the
PBL platform architecture baseline, not CRM/Hiring-specific conventions. They apply by default to
future PBL-developed modules and to modules progressively replacing Plum functionality, unless an
approved ADR records an exception. See
`docs/agent/architecture/PBL_PLATFORM_ARCHITECTURE_AND_FUTURE_AI_READINESS.md` for the full
platform-versus-reference-stack distinction and future AI-readiness governance.

## System shape

The initial production system is a modular API-first application with:

```text
React + Vite + React Router web client
Future React Native mobile clients
FastAPI authoritative backend
SQLAlchemy + Alembic persistence boundary
PostgreSQL 17 via Psycopg 3, confirmed as the frozen production database (ADR-028)
Database-backed background jobs behind an abstraction
GitHub Actions CI/CD
Docker-based development and deployment artifacts
```

The modules are initially deployed together. That deployment choice is not permission for them to
share ownership: each bounded module owns its data and rules and exposes controlled synchronous
contracts and durable facts. Modules may later be separated or replaced without redesigning the
business model or consumer contracts.

## Dependency rules

1. UI clients call FastAPI; they do not own business decisions.
2. Business modules depend on shared capabilities through interfaces, not provider details.
3. A module may hold another module's stable public ID, but that reference does not transfer
   ownership.
4. A module does not write another module's tables or import its repository.
5. Cross-module commands use an approved service/API contract.
6. Cross-module facts use approved versioned business-event contracts.
7. Background jobs execute deferred work; they do not replace domain events.
8. Read models may denormalize data only with documented source ownership and refresh behavior.

## Application layers

```text
Clients
  Web / mobile / approved integrations

Application API
  FastAPI routes, authentication, request validation

Bounded modules
  Domain services, policies, owned repositories and events

Shared platform capabilities
  Authorization, approvals, documents, events/outbox, jobs, integrations, audit

Infrastructure
  Database, object/document storage, external providers, observability, CI/CD
```

## Consistency model

- Use one database transaction inside one module's command boundary.
- Use a narrowly scoped use-case coordinator (an application service) for a short synchronous
  workflow spanning modules only when an immediate result or all-or-nothing behavior is required
  and the contracts permit it. The coordinator invokes module-owned interfaces; it does not own
  their rules, repositories or tables.
- Use a transactional outbox and idempotent consumers for durable cross-module propagation.
- Do not simulate distributed transactions with direct cross-module table writes.

## Contract maturity

`CONTRACT_REGISTRY.md` is the single authority for maturity definitions and current contract
status. In summary, only a `FROZEN` boundary with reviewed fixtures permits independent consumer
implementation against that exact version.

## Production foundation sequence

```text
PAF-1 architecture records and contract registry
  -> use approved contracts; resolve only the remaining decision needed by a selected package
  -> TE-2A web migration                          DONE, integrated on main
  -> confirm production database                  DONE, PostgreSQL, ADR-028
  -> TE-2B database migration                     DONE, integrated on main
  -> TE-2CI GitHub Actions validation foundation  DONE, hosted-verified; enforced by ADR-031
  -> TE-2C migrated-foundation verification       DONE, 18 August 2026
  -> PF-1 shared controls, API/event retrofit and contract fixtures
                                                  PF-1A DONE through E3; PF-1B retrofit not built
  -> bounded-module delivery waves                CRM pilot and Hiring lane since September 2026
```

*Statuses reconciled 7 October 2026 (TB-1 TB1-110). Where the project stands now is in
`docs/continuity/NEXT_STEPS.md`.*

No module implementation should be started merely to keep an agent busy. Parallel work begins
when its contract and dependencies satisfy the Definition of Ready.
