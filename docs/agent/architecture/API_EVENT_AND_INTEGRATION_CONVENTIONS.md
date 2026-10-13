# API, Event and Integration Conventions

## Status

Approved shared conventions under contract `MCF-001`. Existing implemented APIs are compatibility
inputs, not permanent exceptions. `PF-1B` inventories every route/event and provides shared
correlation, idempotency, error and event-version foundations; explicit per-module retrofit
packages adopt them without unplanned response-breaking changes.

Any existing module touched for new production behavior must adopt the applicable MCF conventions
in the same package or record a time-bounded compatibility exception with owner and retirement
package. The final production-candidate gate does not permit two indefinite API/event classes.

## Synchronous interfaces

- Commands use backend-authoritative authorization and validation.
- Queries do not mutate business state.
- Public APIs use UUID public IDs and never expose integer identity keys as cross-module identity.
- Browser clients use relative `/api` URLs.
- A command that may be retried accepts an idempotency key and returns the original compatible
  result for a duplicate key in the same scope.
- Correlation IDs flow through commands, events, jobs and integration calls.
- A date and time a request carries, in its body or its query, is ISO text with its zone (`Z` or an offset);
  anything else - no zone, a number, digits - is refused with `422`, and any offset is held as UTC. Use
  `app.shared.zoned_datetime.ZonedDateTime` (added 11 October 2026; ADR-028, "Timestamps").

## Logical command metadata

```text
request_id
correlation_id
idempotency_key (when retryable)
actor_user_public_id
actor_roles / authority context
requested_at
contract_version
```

Authentication derives actor identity server-side. Clients must not be trusted to assert an
approver identity or role merely by sending these fields.

## Errors

Logical error responses contain:

```text
error_code                 stable machine-readable code
message                    safe user-facing summary
field_errors[]             optional field/code/message entries
correlation_id
retryable                  true/false
details                    optional non-sensitive structured context
```

Validation, authorization, conflict, not-found, dependency-unavailable and unexpected failures
must remain distinguishable. Provider payloads, stack traces and secrets are never returned.

## Business events

Existing event names use PascalCase and remain compatible. New internal event names should follow
`AggregateFact`, for example `ResourceAssigned` or `LogSheetApproved`, with an explicit numeric
`schema_version` in the event record/payload.

Minimum event envelope:

```text
event_public_id
event_name
schema_version
occurred_at
source_module
aggregate_type
aggregate_public_id
actor_user_public_id (nullable for system action)
correlation_id
causation_event_public_id (nullable)
payload
```

Events are completed facts, append-only and never the only store of current state. Reliable
cross-module publication uses a transactional outbox or equivalent atomic pattern.

## Event consumers

- Consumers are idempotent by event public ID plus consumer name/version.
- Failed delivery is visible and retryable.
- Event order is guaranteed only where a contract explicitly defines an aggregate sequence.
- Consumers do not infer missing business decisions from event arrival.

## Background jobs

Jobs contain an operation type, versioned input reference, idempotency key, attempt count,
schedule, lock state and safe failure detail. Prefer references to authoritative records over
copying sensitive payloads. A job completion may produce a business event only when a business
fact actually occurred.

## External integrations

- Provider-specific DTOs stay inside the Integration Gateway/provider adapter.
- Business modules consume normalized contracts.
- Every outbound call has timeout, retry and idempotency behavior appropriate to the provider.
- Reconciliation status and external reference IDs are retained without storing secrets.
- Webhooks are authenticated, replay-protected, idempotent and mapped to internal commands/events.

## Change compatibility

- Additive optional fields are preferred within a contract version.
- Removing, renaming or changing meaning requires a new version and migration plan.
- Contract fixtures are validated by TE-2CI/PF-1 CI once a contract is frozen; a freeze cannot be
  recorded while that validation path is absent.
- Database tables are not integration contracts.
