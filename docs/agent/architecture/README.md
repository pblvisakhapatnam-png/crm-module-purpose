# Production Architecture Records

## Purpose

This folder is the **PBL application-platform architecture foundation**. CRM + Equipment Hiring are
the first substantial implementations of that broader platform direction, not a CRM/Hiring-only
architecture — see ADR-030 in `../ARCHITECTURE_DECISIONS.md` and
`PBL_PLATFORM_ARCHITECTURE_AND_FUTURE_AI_READINESS.md`. These records apply by default to the
current CRM and Equipment Hiring modules, to future PBL-developed modules, and to modules that
progressively replace existing Plum ERP functionality, unless an approved ADR documents a justified
exception. Read this folder after `ARCHITECTURE_DECISIONS.md` and before planning a production
module, whether that module belongs to CRM/Hiring or a future PBL module.

## Reading order

1. `PBL_PLATFORM_ARCHITECTURE_AND_FUTURE_AI_READINESS.md` — platform-wide scope, the reference-stack
   versus platform-principle distinction, and future AI-readiness governance; read this first if you
   are scoping a module outside CRM/Hiring
2. `PRODUCTION_ARCHITECTURE_DIRECTION.md`
3. `MODULE_BOUNDARY_OWNERSHIP_MATRIX.md`
4. `PBL_BUSINESS_REVIEW_GUIDE.md` for PBL decisions in simple language
5. `CONTRACT_REGISTRY.md`
6. `API_EVENT_AND_INTEGRATION_CONVENTIONS.md`
7. `EXTERNAL_DEPENDENCY_REGISTER.md`
8. `DATA_CLASSIFICATION_AND_HANDLING.md`
9. `NFR_BASELINE_AND_VERIFICATION.md`
10. `CONTRACT_FIXTURE_AND_FREEZE_PLAN.md`
11. `MODULE_DEPENDENCY_AND_DELIVERY_WAVES.md`
12. `PRODUCTION_READINESS_GATES.md`
13. `INDEPENDENT_IMPLEMENTATION_REVIEW_WORKFLOW.md` when using the internal implementation and
    independent-review delivery split
14. `BOUNDED_INDEPENDENT_REVIEW_METHOD.md`, read together with 13, for how a material/
    production-candidate independent review is actually packaged and invoked (delivery
    methodology, added 17 August 2026 — not a product/platform architecture change)
15. `EXTERNAL_DEPENDENCY_SOURCE_GAP_VALIDATION_METHOD.md` before relying on any external
    dependency's mere existence/ownership as proof it holds the structure a new capability needs
    (method adopted 31 August 2026, PF-1F-HR-E1, ADR-032); see `docs/agent/pf-1f-hr/` for its first
    full application (HR reference source and parameter-driven authority)

Two registers record where the code departs from these records today, each departure with its owner and the package
that retires it - or, for five database rules, the permanent exception that keeps them (added 8 October 2026, TB-1
CS-07 and CS-06). Read them with the record they qualify:

- `BOUNDARY_EXCEPTION_REGISTER.md`, with 3 - every write into another module's table, import of another module's
  repository, cross-module table read and database rule that reads another module's table (TB1-100, TB1-101), owned
  by PF-1B, apart from five database rules: a permanent exception to ADR-017 the owner approved on 9 October 2026,
  owned by the Commercial Offer to Work Order handoff (the CRM lane).
- `MCF_ADOPTION_RECORD.md`, with 5 and `docs/agent/contracts/shared-module-contract-foundation.md` - each module's
  standing against `MCF-001`'s guarantees: met, not met, and the package that meets them (TB1-102).

## Authority

Approved ADRs and frozen contracts take precedence over these explanatory records. Contract
maturity is explicit in `CONTRACT_REGISTRY.md`; a proposed contract is not frozen merely because
it exists.

These records are internal PBL development material and must not be copied to the vendor-review
repository without explicit approval.
