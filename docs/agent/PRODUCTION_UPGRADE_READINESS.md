# Production Upgrade Readiness Notes

This prototype is production-style but not production-ready. Before production upgrade, assign a dedicated Production Upgrade Agent.

## Areas to review

```text
security and role matrix
session and password policy
secret management and .env handling
migration rollback/restore discipline
backup and restore tests
observability and audit logging
error handling and support diagnostics
performance on realistic data volumes
data retention and archival policy
document storage and access control
UAT data, demo data and test-data reset strategy
```

## Database and migration cautions

```text
- Review all Alembic migrations for idempotency and clean upgrade order.
- Confirm indexes and constraints under realistic data volumes.
- Confirm public_id and business-reference uniqueness.
- Confirm no helper/test artifacts are in production migration path.
```

## API and integration cautions

```text
- Export and review OpenAPI schema after API stabilization.
- Version integration contracts before connecting external systems.
- Add integration monitoring, retry/reprocess and failure visibility.
- Keep graceful manual fallback for external intelligence and automation.
```

## Security and audit cautions

```text
- Backend permissions must remain authoritative.
- Approval independence must be enforced where required.
- Business events must capture key lifecycle actions and status changes.
- Submitted/approved documents should not be silently overwritten.
```

## UAT caution

Do not treat passing automated tests as production acceptance. UAT must prove business controls, negative paths, role behaviour, document traceability and handoff integrity.
