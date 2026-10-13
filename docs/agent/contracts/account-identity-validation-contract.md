# Account to Identity Validation Contract

## Contract ID and status

`AIV-001` - `APPROVED` - 12 August 2026.

## Owners

```text
Account Master                         owns Account identifiers, authoritative accepted values
Identity and Statutory Validation     owns provider interaction and normalized result
```

## Request semantics

Account submits a validation request containing:

```text
validation_request_public_id / idempotency key
Account public ID
identifier type and normalized value (PAN and/or GSTIN)
requested validation purposes
actor and correlation metadata
```

The request does not grant approval and does not expose provider credentials.

## Normalized result semantics

```text
validation_request_public_id
Account public ID
verification_state
provider code = SUREPASS (current provider)
provider reference ID where available
requested/validated identifiers
authoritative legal identity fields returned where supported
registration status/details where supported
mismatch fields
exception classification
verified/attempted timestamp
evidence references
retryable / next-retry information
manual-fallback reference where authorized
```

Account Master decides how to apply a completed result under ADR-015. SurePass-returned legal
identity values are authoritative, while original entered/document values and mismatch evidence
are preserved.

## Availability and exceptions

- Temporary provider unavailability leaves verification pending and does not hard-block ordinary
  operational work.
- Invalid identifiers, failed validation and returned mismatches remain exceptions.
- Accounts owns the exception queue by default; authorized Sales assignment is configurable.
- Prolonged unavailability may use an authorized, audited manual route.

## Events

Logical facts include `IdentityValidationRequested`, `IdentityValidationCompleted`,
`IdentityValidationExceptionRaised` and `IdentityValidationManuallyResolved`. Exact schemas must
be approved before freeze.

## Settled baseline and deferred parameters

ADR-015 and Q-01 to Q-04 already settle the business meaning:

- SurePass-returned legal name, registered address, PAN/GSTIN details and registration status are
  authoritative where returned; original entered/document values remain audit evidence.
- Invalid identifiers, failed validation, incomplete/ambiguous results and returned mismatches
  enter the exception queue. Accounts owns the queue by default; authorized Sales assignment is
  configurable.
- Temporary unavailability leaves verification pending and does not halt ordinary operations.
  Prolonged unavailability may use an authorized, audited manual route.

Retry timing, the point at which prolonged unavailability starts, evidence retention and repeat
verification remain configurable parameters. PBL deliberately deferred their values; they are
set when the implementation or operating support process needs them, not treated as reasons to
reopen this contract.
