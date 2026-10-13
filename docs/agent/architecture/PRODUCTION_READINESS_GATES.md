# Production Definition of Ready and Done

## Module-slice Definition of Ready

An implementation package may be issued only when all applicable items are true:

```text
[ ] Objective and explicit out-of-scope list are approved.
[ ] Owning module and authoritative data are named.
[ ] Inbound/outbound contracts are APPROVED or FROZEN for the implemented behavior.
[ ] Open business questions are resolved or excluded with a safe stop condition.
[ ] Allowed files and shared-file owner are named.
[ ] Migration slot/strategy is assigned if schema changes are expected.
[ ] Backend permission rules and segregation-of-duties expectations are explicit.
[ ] Required business events, idempotency and correlation behavior are explicit.
[ ] API/request/response and error behavior are explicit enough to test.
[ ] Source guidance is classified/reconciled under ADR-013.
[ ] External dependencies have a current register status, owner, interface evidence and fallback.
[ ] Authority work has a current Employee Master organization/position/status snapshot and change/
    recovery interface; a CRM-owned organization copy is not accepted as a fallback. (Exception until the HR feed
    exists: approval rights set by an administrator, ADR-038.)
[ ] Restricted/personal/financial fields are classified and minimized across interfaces,
    fixtures, logs and events.
[ ] Applicable NFR controls and evidence are named.
[ ] Acceptance checklist includes happy, negative, permission and regression paths.
[ ] Test commands, fixture needs and manual check are identified.
[ ] Dependencies and integration-wave target are named.
```

If a required item is missing, PBL's reviewer prepares a decision/contract task rather than an
implementation prompt.

## Module-slice Definition of Done

```text
[ ] Implementation stays within the assigned module/files or records an approved deviation.
[ ] Schema changes include reviewed Alembic migration(s).
[ ] API and event behavior match the approved/frozen contracts.
[ ] MCF adoption or a recorded exception: for each MCF-001 guarantee the work touches, the package
    adopts it, or records a time-bounded exception (guarantee, owner, retirement package) in
    MCF_ADOPTION_RECORD.md, updating its module's row either way. (Added 8 October 2026, TB-1
    TB1-102, CS-06.)
[ ] A new read, write, row lock or database rule on another module's table, or an import of another
    module's repository, goes through the owning module's interface or adds its row to
    BOUNDARY_EXCEPTION_REGISTER.md; a package that retires one removes its row. (Added 8 October
    2026, TB-1 TB1-100 and TB1-101, CS-07.)
[ ] Backend authorization is enforced and tested.
[ ] Meaningful actions create required business events without secrets/sensitive excess.
[ ] Happy, negative, permission and regression-risk tests pass.
[ ] Backend full regression passes for substantial behavior changes.
[ ] Frontend build/tests and relevant Playwright scenarios pass when affected.
[ ] Empty-database migration and Docker clean start pass when infrastructure/schema changed.
[ ] Manual happy and permission paths are recorded.
[ ] Contract, slice, acceptance and continuity records are updated.
[ ] The handoff records the baseline commit the change was built on and a structured summary of it.
[ ] PBL's reviewer examines the actual diff and independently verifies risk-relevant checks.
[ ] Material review findings are resolved and affected checks rerun.
[ ] The change merges only after PBL's reviewer accepts it and the project owner confirms the merge.
[ ] Integration-wave regression passes after merge; no unmanaged Alembic heads remain.
    (CI does not re-run on main after a merge: the pull request's run on its branch, current with
    main as the ruleset requires, proved the merged tree and is this regression. Run the workflow on
    main by hand when a wave needs it.)
[ ] Applicable performance, security, failure-recovery, monitoring and data-handling evidence is
    recorded against NFR_BASELINE_AND_VERIFICATION.md.
[ ] Authority changes include leaver, transfer/scope, stale-HR-feed, recovery, pending-approval
    reassignment and no-backdated-reactivation tests where ORA is affected.
[ ] Exposure changes include explicit-expiry, no-expiry review, overdue hold, confirm-live and
    final-outcome tests where CEX/Commercial Offer is affected.
```

## Contract Definition of Ready for freeze

```text
[ ] Producer and every named consumer agree ownership and semantics.
[ ] Stable identifiers and versioning behavior are explicit.
[ ] Commands, queries, events and failure/retry behavior are explicit.
[ ] Authorization, audit, idempotency and evidence requirements are explicit.
[ ] Fixtures include happy, invalid, unauthorized, duplicate and dependency-failure cases.
[ ] ORA fixtures include Employee Master joiner/transfer/leaver/correction/stale-feed cases, and
    CEX fixtures include no-expiry review/overdue-resolution cases, when those contracts freeze.
[ ] Data, migration, security and compatibility impacts are reviewed.
[ ] Change owner and versioning process are named.
[ ] Fixture pack and manifest exist under the location defined by
    CONTRACT_FIXTURE_AND_FREEZE_PLAN.md and are validated by producer and consumers.
[ ] PBL confirms that the business information and behavior are correct and other modules may
    rely on them; PBL's reviewer records the technical status as FROZEN.
```

## TE-2C migrated-foundation Definition of Done

TE-2C verifies the technology migration and shared technical baseline. It is not the final
production-candidate product tag. It must prove:

- all supported migrations apply from an empty confirmed production database;
- backend regression, frontend build/tests and E2E regression pass;
- Docker clean start and health checks pass;
- TE-2CI GitHub Actions required checks reproduce the documented validation path and are required
  for protected integration. As of ADR-031 (17 August 2026) a GitHub repository ruleset technically
  enforces `Required validation` and the associated pull-request/branch-currency/no-force-push
  rules on `main`, closing the plan limitation ADR-029 recorded; TE-2C must independently verify the
  active ruleset against this requirement and record that evidence, rather than treating ADR-031's
  existence alone as satisfying this item;
- secrets/configuration, backup/restore evidence, logs/metrics and failure diagnostics meet the
  TE-2C NFR gate in `NFR_BASELINE_AND_VERIFICATION.md`;
- a repeatable standard-interaction timing baseline and dependency-failure checks are recorded;
- obsolete Next.js and SQL Server assumptions are removed or explicitly documented;
- contract registry and architecture records match the repository;
- known residual risks and still-unset production parameters are recorded without claiming final
  production compliance.

## Final production-candidate Definition of Done

After PF-1 and the selected business delivery waves, the release candidate must additionally
prove:

- every runtime cross-module boundary used by the release is `FROZEN` with validated producer and
  consumer fixtures;
- existing APIs/events in release scope have adopted MCF correlation, error, idempotency and
  schema/version conventions or carry a reviewed compatibility exception and retirement date;
- applicable security, access/data-scope, personal-data, retention/legal-hold, audit and
  vulnerability checks pass;
- production-like 95th-percentile performance, peak-load stability and volume assumptions are
  evidenced;
- availability SLA, RPO/RTO, backup retention, restore and recovery exercises are approved and
  evidenced;
- external dependency readiness, monitoring, retry/reconciliation and owned fallback procedures
  are accepted;
- support/runbooks, role-based UAT, training/admin documentation and rollback evidence are ready;
  and
- the final baseline commit/tag and residual risks are approved and recorded.
