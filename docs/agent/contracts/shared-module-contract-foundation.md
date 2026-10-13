# Shared Module Contract Foundation

## Contract ID and status

`MCF-001` - `APPROVED` - 12 August 2026.

## Purpose

Define the common semantics every new inter-module API, service interface, event and job must use.
It does not change existing routes or event storage.

## Required guarantees

- Stable public identity and explicit contract/schema version.
- Server-derived actor identity and backend-authoritative authorization.
- Correlation across command, event, job and integration activity.
- Idempotency for retryable commands and consumers.
- Structured non-sensitive errors with retryability.
- Append-only durable facts through business events/outbox where required.
- No direct cross-module repository/table writes.

## Common reference

```text
record_type
record_public_id
display_reference (optional, non-authoritative)
source_module
```

## Common evidence reference

```text
document_public_id or evidence_public_id
evidence_type
version/reference
status
```

The Documents/Evidence capability owns storage metadata. Business modules own why evidence is
required and whether it satisfies a business rule.

## Authorization

Contracts name required permission/policy checks, not only frontend roles. An authenticated role
is an input to backend policy evaluation; it is not proof that an action is allowed.

## Change control

See `docs/agent/architecture/CONTRACT_REGISTRY.md`. PBL accepts the business meaning and the
independent reviewer records whether the contract is ready for implementation or use by other
modules. Existing contracts are not retroactively changed by this proposal.

## Settled baseline

No PBL decision is pending. The guarantees above are production engineering requirements:

- every important committed action records who acted, when, the affected record and relevant
  decision/change context;
- a retry, repeated submission or double-click does not create a duplicate business effect; and
- failures return a clear, non-sensitive message and a support/tracking reference where useful.

This baseline is approved by ADR-023 and the existing integration, event, audit and security
governance. Implementation details remain an engineering responsibility.
