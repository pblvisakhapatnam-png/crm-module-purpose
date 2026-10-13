# Slice 0G - Final Acceptance / Cleanup

## Goal

Confirm that Slice 0 is stable before beginning Slice 1 Account / Qualified Prospect Foundation.

This slice should not add new business functionality. It is a checkpoint.

## Scope

Slice 0G covers:

- clean rebuild of the local Docker stack;
- database migration/bootstrap verification;
- regression check for health, database, auth, events, workflow statuses and document metadata;
- backend automated tests;
- frontend manual smoke checks;
- Git working tree cleanup;
- documentation checkpoint before Slice 1.

## Out of scope

- Account / business_party implementation;
- Lead implementation;
- Opportunity implementation;
- Commercial Offer implementation;
- real file upload;
- SharePoint integration;
- production deployment hardening.

## Required manual checks

1. Docker stack starts from a clean state.
2. Backend health endpoint works.
3. Database health endpoint works and confirms foundation tables.
4. Login works for seeded users.
5. `/accounts` authentication smoke check works.
6. `/events` loads for Admin.
7. `/workflow-statuses` loads for Admin and Sales User.
8. `/documents` can create and load sample document metadata.
9. Backend pytest suite passes.
10. Git status is clean except intentionally excluded local helper scripts.

## Fresh rebuild note

Using `docker compose down -v` deletes the local SQL Server Docker volume.

That is acceptable for Slice 0G because the objective is to confirm that the system can bootstrap from scratch through migrations and seed data. It also deletes local sample events/documents, which is expected.

## Acceptance result

Record the final result in:

```text
docs/agent/acceptance/slice-0g-final-acceptance-cleanup-acceptance.md
```

## Completion rule

Slice 0 is complete only after Slice 0G passes and the result is committed and pushed.