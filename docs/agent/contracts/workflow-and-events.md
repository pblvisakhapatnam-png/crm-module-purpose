# Workflow and Events Contract

## Purpose

This contract defines the initial lightweight workflow and business event foundation.

The goal is traceability, not a full workflow engine.

## Design principle

Important business changes should be visible and queryable.

The system should record:

- who performed an important action;
- when it happened;
- what record was affected;
- previous and new status where applicable;
- reason or remarks where applicable.

## Workflow status

Workflow status is used to control lifecycle movement for future modules.

Initial usage:

- Account lifecycle status in Slice 1.
- Later Lead, Opportunity, Offer, Work Order, Log Sheet and Invoice statuses.

## Business event

A business event is created when something important happens.

Examples for early slices:

```text
UserLoggedIn
AccountCreated
AccountUpdated
AccountStatusChanged
DocumentLinked
WorkflowStatusChanged
DuplicateWarningRaised
```

## Event fields

Recommended minimum:

```text
id
public_id
event_name
source_module
record_type
record_public_id
user_public_id
event_timestamp
status_before
status_after
reason
remarks
correlation_id
event_payload_json
created_at
```

## Event rules

- Events should be append-only.
- Do not use events as the only source of current state.
- Events should support audit/traceability, not replace core tables.
- Do not store secrets in event payloads.
- Avoid storing unnecessary sensitive data in event payloads.

How the event store enforces "no secrets" (`backend/app/modules/events/repository.py`; since 8 October 2026, TB-1
TB1-500). Before, it refused any payload whose text held the words "password", "token" or "secret" anywhere - so a Lead
for a "Secretariat", a contact "Under Secretary" or a reason naming a "token advance" could not be saved at all, with a
server error. It now refuses a credential by its shape, never an English word. The payload is serialized once, and the
check reads exactly the text that is stored. The shapes below are a closed list of credentials that **prove
themselves** - their own structure says what they are - chosen for what this application handles (the owner's
decision, 8 October 2026, after nine review rounds). A value is never guessed to be a credential from the words around
it: an opaque value after "Bearer", "Token" or "Digest", or a cookie's value, looks like any reference number or long
word, and every rule that guessed refused some ordinary sentence ("Bearer representative, may collect the documents",
"Digest of approvals; username = reviewer"). So a secret with none of these shapes - a password typed as plain text,
an opaque API key under a neutral name, an opaque token pasted after "Bearer" - is not recognised, and code must still
never put one into an event. The tokens this application issues are JSON Web Tokens, which prove themselves, and no
code writes request headers into events.

- **A payload key that names a credential**, anywhere in the payload, holding anything but nothing (`None`) - text, a
  structure, a number or a flag - unless the key is metadata about a credential holding its own kind of value, which
  is never a credential: a flag (`true`/`false`) when its first word is `has` or `is` or its last is `reset`,
  `required`, `removed`, `valid`, `known` or `set`; a whole number (an integer, or digits as text) when its last word is
  `attempt(s)`, `count`, `version`, `length` or `age`; a flag or an ISO 8601 date, with or without a time, when its
  last word is `changed`, `expired`, `expires` or `expiry` - a real one: "2026-13-40" is not a date (`password_reset: true`, `token_version: 2`,
  `has_password: true`, `password_changed: "2026-10-08"` are accepted; `otp: 123456`, `has_recovery_codes: [...]` and
  `password_reset: {"new": ...}` are not). The key is read word by word - split at separators and at a lower-to-upper
  case change, and where an acronym meets a word (`DBPassword` is `db password`) - and one grammar decides whether it
  names a credential: one of its words is a credential root
  (`password`, `passwd`, `passphrase`, `secret`, `jwt`, `token`, `otp`, `credential`) or a run-together credential term
  (`accesstoken`, `refreshtoken`, `apikey`, `accesskey`, `privatekey`, `secretkey`, `signingkey`, `clientsecret`,
  `recoverycode`, `backupcode` and the like), alone or followed by one of `s`, `hash`, `value(s)`, `data` or `material`
  (`secrets`, `CREDENTIALVALUE`, `ACCESSTOKEN`, `BACKUPCODES`, `PASSWORDHASH`; `secretariat`, `secretary` and
  `clientsecretariat` are not); or two of its words in a row are `api key`, `access key`, `private key`, `secret key`,
  `signing key`, `recovery code` or `backup code`, the second alone or with one of those suffixes (`api_keys`,
  `backup_codes`). "token" is a credential word everywhere but in one
  business construction, the earnest money of commercial practice: "token" first in the key, or after "prepaid",
  "paid", "received", "booking" or "earnest", and followed by "advance", "amount", "money" or "payment"
  (`token_advance_amount`, `prepaid_token_amount`); `oauth_token_amount` and `access_token_amount` are credentials. No
  term is looked for across two words (`client_secretariat_name` passes), and "pin" (a postal PIN code) and "PWD"
  (Public Works Department) are deliberately not credential words. Keys are chosen by code, so this refusal is a
  defect to fix: a plain `ValueError`, a server error, whose message names no key (a key may itself be a credential).
- **An Authorization-named key holding Basic credentials** - `Authorization` or `Proxy-Authorization`, as text or in
  a list of values, holding "Basic " and base64 that decodes to a user name in UTF-8 text with no control character,
  a colon and any password - which need not be text - however short or long, padded or not. A user name in an older
  single-byte encoding is not recognised: allowing any bytes would take numbers and codes after "Basic" for
  credentials.
  The same keys holding anything else are accepted - "Board approval recorded", "Basic training for operators", and
  any Bearer, Token or Digest value (the limit above).
- **Text holding a credential's machine shape** - a value anywhere in the payload, a key, or any of the event's text
  columns (name, source, record, statuses, reason, remarks, correlation id): a JSON Web Token (a header followed by
  at least two more dots - the payload and signature parts may be empty - whose header, up to 16,384 characters,
  decodes to a JSON object naming its algorithm, `"alg"`, as non-empty text; found whatever its encoding begins with, at the start of the
  text or after any character that is not a letter or a digit, so `jwt_eyJ...` counts) - after "Bearer" too; a
  private-key block; an Authorization header with Basic credentials (refused only when the value is base64 of
  `user:password`, however short or long - "Authorization: basic training" is not); a stored password hash - this
  application's `pbkdf2_sha256$iterations$salt$hash` (a hex salt and the 64-hex SHA-256 digest; Django's form too,
  an alphanumeric salt and the digest as 43 base64 characters and "="; never zero iterations), bcrypt (`$2b$`, a cost
  from 04 to 31 and 53 characters), Argon2's PHC string (`$argon2id$v=16|19$m=..,t=..,p=..$salt$hash`, each parameter
  read field by field: memory at least eight times the parallelism, time at least 1, a salt of 8 bytes or more and a hash
  of 4 or more, both canonical unpadded base64) and the crypt family's MD5, SHA-256 and SHA-512 (rounds 1,000 to 999,999,999) and
  yescrypt (`$y$j...`) forms - each only in its complete encoding, so an incomplete or malformed one
  (`pbkdf2_sha256$600000$`, `$2b$abc...`) is ordinary text; or an address with a password in it
  (`scheme://user:password@...`, found by scanning, whatever the length of the user or the password; the scheme as
  the URI grammar allows - a letter, then letters, digits, `+`, `-` or `.`, so `postgresql+psycopg://` counts). No value is cut
  off at a length (only a JSON
  Web Token's header is read up to 16,384 characters), and the scans are linear - possessive patterns, no
  backtracking - so checking a long text costs time in proportion to its length. A JSON Web Token is looked for at the
  start of each dot-free part of a text and after the first and the last 16 "_" or "-" in it (`jwt_eyJ...`,
  `x-y-eyJ...`), not after every one, which would decode the same part once per separator: a token glued after more
  separators than that, with as many inside its own header, is not looked for - a stated limit.

When one payload has both - a credential-named key holding something, and credential-shaped text anywhere - the
credential-named key decides: the plain `ValueError` (a defect in code) comes first, whatever its value looks like and
wherever the walk meets it.

The two text refusals are `EventCredentialRefusedError` (`events/errors.py`), which the application answers `422` with
`{"detail": "This was not saved: some of the text looks like a password, an access token or a private key, which must
never be recorded. Remove it and try again."}`. The answer names no value, and the record is not saved: the services
that put typed text into events write the event in the same transaction as the record and roll it back on an error
(TB1-500's evidence lists them).

## Future compatibility

The design should allow later expansion to:

- approval events;
- rejection events;
- correction events;
- integration events;
- retry/reconciliation events;
- credit override events;
- document locking events.

## Slice 0D implemented recent-events access

```text
GET /api/events/recent?limit=25
```

Access:

```text
Admin
Management / Read Only
```

Implemented event names:

```text
UserLoginSucceeded
UserLoginFailed
```

Rules:

- business event payloads must not store passwords, tokens or secrets;
- failed-login events may store attempted username but not attempted password (since TB-1 TB1-204 part a, below, they
  store neither);
- event records are append-only and are not the source of current business state.

*Changed 7 October 2026 (TB-1 TB1-204 part a; record `docs/continuity/TB1_204A_SIGN_IN_HARDENING.md`).*
A failed sign-in no longer stores what was typed as the username - it is sometimes the password, typed
in the wrong box, and a typed name holding "password", "token" or "secret" made the sign-in answer 500.
`UserLoginFailed` now carries `{"username": <the account's own username>}` when the typed name reaches
an account and `{"username_known": false}` when it does not; when the log would refuse the account's own
username (until TB1-500 the three words; since, text shaped like a credential - "Event rules" above), it
carries the fixed `{"username_withheld": true}` in its place, so the sign-in still answers 200, 401 or
429. Whenever the typed name reaches an account, the event's `record_public_id` is that account's public
id, a UUID the application chose. That rule -
`username` when the log can store it, else `username_withheld`, the account named by `record_public_id`
- holds for every sign-in event below, for `UserLoginSucceeded` (beside its `role_codes`) and for the
account tool's own events on an account (rounds 4 to 6 of the package's review). Since round 7 the
whole payload is checked: when the log would refuse any part of an `identity` or account-tool event's
payload - a role code, a display name - the whole payload is `{"username_withheld": true}`, so such a
role code neither stops a sign-in nor stops the tool removing that role. The tool refuses to create an
account whose username or display name the log would refuse. Its `reason` is
`Invalid credentials.` or,
for an attempt refused because the username is stopped, `Refused: the username is stopped after
repeated failed sign-ins.` Further `identity` events, with the same payload rule:

```text
UserSignInLocked      the username is stopped after repeated failed sign-ins; payload adds locked_until.
                      Written in the same transaction as the stop, so a stop is never without it
UserSignInUnlocked    a stop in force was lifted: by the account tool (only for an account), or by a
                      successful sign-in after which fewer than the limit of attempts remain in the window -
                      whichever attempt reached the limit (the success's own, or a wrong one that came after it)
UserSignInsEnded      the account tool ended every sign-in of an account without changing its password
```

A password reset, disabling and retiring also end every earlier sign-in; their existing events
(`UserPasswordReset`, `UserAccountDisabled`, `UserAccountRetired`) record it.

## Slice 0E implemented workflow status lookup

```text
GET /api/workflow/statuses?module=business_party&active_only=true
GET /api/workflow/modules?active_only=true
```

Access:

```text
Any authenticated user
```

Seeded internal module:

```text
business_party
```

Seeded Account status codes:

```text
DRAFT
LEAD_LINKED
QUALIFIED_PROSPECT
ACTIVE_PROSPECT
DORMANT
ON_HOLD
BLOCKED
CUSTOMER_ACTIVATION_PENDING
CUSTOMER_ACTIVE
BLACKLISTED
```

Notes:

- The internal module name is `business_party`.
- The UI label for users will be Account.
- Slice 0E provides reference data lookup only; status transition enforcement comes later.

## Slice 3A implemented Opportunity workflow and event foundation

```text
POST /api/opportunities
GET  /api/opportunities
GET  /api/opportunities/{public_id}
```

Seeded internal module:

```text
opportunity
```

Seeded Opportunity status codes:

```text
NEW
NEEDS_REVIEW
QUALIFIED
QUOTE_PENDING
ON_HOLD
WON
LOST
CLOSED
```

Implemented event name:

```text
OpportunityCreated
```

Rules:

- Slice 3A creates Opportunity foundation records only.
- Lead conversion, quote/commercial offer, approval, Commercial Offer credit/exposure gates against already-approved credit amount and credit days and Work Order handoff remain deferred.
- OpportunityCreated payloads must not store passwords, tokens or secrets.
- `business_party_id` and `source_lead_id` are nullable future link columns and are not populated by manual Slice 3A creation.

## Slice 3B Opportunity profile shell note

Slice 3B introduced no new business event. It displays existing Opportunity fields and may link authorized users to the existing Events page. Events route permissions remain authoritative.

## Slice 3C Opportunity update/stage events

```text
PUT /api/opportunities/{public_id}
```

Implemented event names:

```text
OpportunityUpdated
OpportunityStageChanged
```

Rules:

- Any successful Opportunity update records `OpportunityUpdated`.
- If `opportunity_status_code` changes, the update also records `OpportunityStageChanged` with status_before and status_after.
- Slice 3C status movement is limited to early-stage statuses: NEW, NEEDS_REVIEW, QUALIFIED, QUOTE_PENDING, ON_HOLD and LOST.
- WON and CLOSED remain deferred until quote/commercial offer, award, closure and Work Order handoff rules are designed.
- Event payloads must not store passwords, tokens or secrets.


## Slice 3D Lead conversion events

```text
POST /api/leads/{public_id}/convert
```

Implemented event names:

```text
AccountCreated
OpportunityCreated
LeadConverted
```

Rules:

- Conversion is atomic at the backend service boundary: Account, Opportunity and Lead status update either commit together or roll back together.
- `LeadConverted` records status_before as the prior Lead status and status_after as `CONVERTED`.
- Conversion event payloads may include public IDs of the created Account and Opportunity, but must not store passwords, tokens or secrets.
- Event access remains governed by the Events module.

## Slice 4A Commercial Offer workflow and event foundation

```text
POST /api/commercial-offers
GET  /api/commercial-offers
GET  /api/commercial-offers/{public_id}
```

Seeded internal module:

```text
commercial_offer
```

Seeded Commercial Offer status codes:

```text
DRAFT
READY_FOR_REVIEW
SUBMITTED
REVISED
WITHDRAWN
ACCEPTED
REJECTED
CLOSED
```

Implemented event name:

```text
CommercialOfferCreated
```

Rules:

- Slice 4A creates Commercial Offer / Quote foundation records linked to Opportunities.
- Create is limited to DRAFT status.
- Submission, approval, Commercial Offer credit/exposure gates against already-approved credit amount and credit days, award, Work Order handoff and billing logic remain deferred.
- CommercialOfferCreated payloads must not store passwords, tokens or secrets.

<!-- SLICE_4B_WORKFLOW_EVENTS_NOTE_START -->
## Slice 4B Commercial Offer workflow/events note

Slice 4B is a read-only profile shell refinement.

No new backend business event is added in this slice. Commercial Offer creation continues to record `CommercialOfferCreated` from Slice 4A. Future Commercial Offer update or stage/status slices should add events such as `CommercialOfferUpdated` and `CommercialOfferStatusChanged` only when those actions are implemented.
<!-- SLICE_4B_WORKFLOW_EVENTS_NOTE_END -->

## Slice 4C Commercial Offer update/status events

```text
PUT /api/commercial-offers/{public_id}
```

Implemented event names:

```text
CommercialOfferUpdated
CommercialOfferStatusChanged
```

Rules:

- Any successful Commercial Offer update records `CommercialOfferUpdated`.
- If `offer_status_code` changes, the update also records `CommercialOfferStatusChanged` with status_before and status_after.
- Slice 4C status movement is limited to DRAFT, READY_FOR_REVIEW and WITHDRAWN.
- SUBMITTED, REVISED, ACCEPTED, REJECTED and CLOSED remain deferred until submission, revision, approval, award and closure rules are designed.
- Event payloads must not store passwords, tokens or secrets.


<!-- SLICE_4D_EVENTS_START -->
## Slice 4D Commercial Offer pricing evidence events

Slice 4D records these Commercial Offer pricing evidence events:

```text
CommercialOfferMarketRateAdded
CommercialOfferHistoricalRateAdded
CommercialOfferBasisRateSelected
```

These events use:

```text
source_module = commercial_offers
record_type = commercial_offer
record_public_id = Commercial Offer public_id
```

Event payloads may include non-sensitive offer code, pricing evidence public id, evidence type, rate amount, currency, rate basis, selected-basis flag and selection reason. Event payloads must not contain passwords, tokens or secrets.
<!-- SLICE_4D_EVENTS_END -->

<!-- SLICE_4E_EVENTS_START -->
## Slice 4E Commercial Offer line/scope events

Slice 4E records these Commercial Offer line events:

```text
CommercialOfferLineAdded
CommercialOfferLineUpdated
```

These events use:

```text
source_module = commercial_offers
record_type = commercial_offer
record_public_id = Commercial Offer public_id
```

Event payloads may include non-sensitive offer code, offer line public id, line number, line status, scope description, equipment/service category, quantity, UOM, rate, currency and line amount. Event payloads must not contain passwords, tokens or secrets.

Slice 4E does not implement T&C master, line-level T&C customization, approvals, Commercial Offer credit/exposure gates against already-approved credit amount and credit days, submission, award or Work Order handoff. Later events for those features must preserve the Commercial Offer header and Commercial Offer line identifiers created by this slice.
<!-- SLICE_4E_EVENTS_END -->



## Slice 4F Commercial Offer lifecycle events

Slice 4F adds these lifecycle events:

- `CommercialOfferSubmitted`
- `CommercialOfferAccepted`
- `CommercialOfferRejected`
- `CommercialOfferWithdrawn`
- `CommercialOfferClosed`

`CommercialOfferStatusChanged` continues to record the before/after status when the lifecycle status changes.

*Reconciled 12 October 2026 with the code as it now stands:* three of these five names are never recorded.
`CommercialOfferSubmitted`, `CommercialOfferAccepted` and `CommercialOfferRejected` are emitted only by the general
update route (`services/offers.py`), which since Slice 6M.1 refuses to move an offer into `SUBMITTED`, `ACCEPTED` or
`REJECTED`. The actions that do make those changes record their own events and no `CommercialOfferStatusChanged`.
Every event each status change records, in the order recorded:

| Change | Made by | Events recorded |
| --- | --- | --- |
| between `DRAFT` and `READY_FOR_REVIEW` | general update | `CommercialOfferUpdated`, `CommercialOfferStatusChanged` |
| to `WITHDRAWN` or `CLOSED` | general update | `CommercialOfferUpdated`, `CommercialOfferStatusChanged`, then `CommercialOfferWithdrawn` or `CommercialOfferClosed` |
| to `SUBMITTED` | mark-submitted (Slice 6J) | `CommercialOfferCommerciallyCommitted`; when a later version is sent, first `CommercialOfferVersionReplaced` on the predecessor, whose status goes from `SUBMITTED` to `REVISED` (Slice 9F) |
| to `ACCEPTED` or `REJECTED` | customer response (Slice 6L) | `CommercialOfferCustomerResponseRecorded` |
| to `ABANDONED` | abandon-version (Slice 9F) | `CommercialOfferVersionAbandoned` |

No other path changes an offer's status. The general update cannot set `REVISED` or `ABANDONED` - they are not in
`COMMERCIAL_OFFER_STATUS_UPDATE_ALLOWED_STATUSES`, which it checks first ("Commercial Offer status cannot be set to
..."), nor `SUBMITTED`, `ACCEPTED` or `REJECTED`, as above. The general update records `CommercialOfferUpdated` on every save, status changed or not. A consumer that needs every
status change of an offer reads these together. Naming and versioning events consistently across modules is part of
the PF-1B retrofit (`MCF_ADOPTION_RECORD.md`).

Future agents must add approval, exposure/availability gate, document locking, formal revision control and Work Order handoff events later.

## Slice 5A Work Order handoff events

- `WorkOrderCreated`: recorded against the Work Order when a shell is created from an Accepted Commercial Offer.
- `CommercialOfferConvertedToWorkOrder`: recorded against the Commercial Offer when it is handed off to a Work Order shell.

Slice 5A events are traceability events only. Future agents must add release, Customer Master, execution, log sheet and billing events.
