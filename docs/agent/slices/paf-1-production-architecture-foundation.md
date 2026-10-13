# PAF-1 - Production Architecture Foundation

## Purpose

Create the production architecture, bounded-module, contract and parallel-delivery records needed
before TE-2 and independent module implementation.

## Scope

- Record ADR-016 through ADR-027.
- Define the production modular API-first application direction and ownership rules.
- Define commercial, operational and shared-platform module boundaries.
- Create a contract registry and eighteen minimum contracts.
- Define API/event/integration conventions and contract maturity.
- Define external-dependency readiness, data handling, NFR verification and contract-fixture
  freeze work.
- Define dependency-based delivery waves and production readiness gates.
- Record the internal planner/reviewer and implementer/tester workflow.
- Update agent entry points, handoff and continuity records.

## Contract status decision

ADR-023 applies existing decisions and ordinary production safeguards without unnecessary PBL
reconfirmation. ADR-024 fixes value-allocation exposure semantics; ADR-025 records authority,
CI, NFR and contract-freeze prerequisites; ADR-026 fixes Employee Master/ORA ownership and
authority lifecycle; ADR-027 prevents submitted offers without expiry from becoming silent,
permanent exposure. Sixteen new contracts are `APPROVED`; `MHA-001` and
`BIP-001` remain `PROPOSED` for D-03/D-04 and D-06 respectively. The Slice 6D.1 Accepted Offer -> Work Order contract remains
frozen and unchanged.

## Out of scope

- No backend, frontend, database, Docker or GitHub Actions implementation.
- No schema or Alembic migration.
- No production database choice.
- No business workflow or permission change.
- No new contract freeze beyond the existing Slice 6D.1 boundary. Sixteen contracts are marked
  `APPROVED`; none is marked `FROZEN` merely because it is documented.
- No vendor-review repository content.

## Checks

Documentation-only validation:

```powershell
git diff --check
```

Also verify internal links, balanced code fences, contract registry coverage, no non-document
changes and no PAF-1/internal markers in the vendor-review clone.
