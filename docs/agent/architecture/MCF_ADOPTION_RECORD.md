# MCF-001 Adoption Record

## Status and owner

Recorded 8 October 2026 (TB-1 finding TB1-102 part a; corrective package CS-06, its "now" part). Measured at `main`
`5e19123`; brought up to date on 9 October with what merged since: the Work Orders row with CS-04 part 1 (`b4dd8fe`),
and the Equipment Reference, Resource Requirements and Resource Assignments rows with TB1-102 part b (PR #107,
`d33a9ae`). The other packages merged up to `fb381c6` change no row. The Commercial Offers row covers CS-05a
(9 October), CS-05c and Slice 9F (10 October); Slice 7D Part 5 changes no row (noted in the Work Orders row).
**Owner: PF-1B**, the API and event retrofit
(CS-06), due before production; the "Retired by" column names an earlier package where one exists.

`MCF-001` (`docs/agent/contracts/shared-module-contract-foundation.md`, approved 12 August 2026) and
`API_EVENT_AND_INTEGRATION_CONVENTIONS.md` require a module touched for new production behaviour to adopt the
conventions in the same package or to record a time-bounded compatibility exception with an owner and a retirement
package; ADR-025 says existing APIs are not permanent exceptions. Only Interactions (`INT-001`) did either. **Every
"Not met" and "Partly" below is now that recorded exception**: owner PF-1B, retirement as named. Interactions' own
exception, in `interaction-contract.md`, stands as written.

**Keeping it current.** A package that changes a module either meets a guarantee it touches or leaves its exception
here, and updates the module's row either way (`PRODUCTION_READINESS_GATES.md`, module-slice Definition of Done).

## The seven guarantees, and how each is judged here

| | Guarantee (`MCF-001`) | Met when |
| --- | --- | --- |
| G1 | Stable public identity and an explicit contract or schema version | Routes and responses use public IDs, never integer keys, and the API states its contract version and each event payload its schema version |
| G2 | Server-derived actor; backend-authoritative authorization | Every route but sign-in names its permission (`require_permission`), and the acting user comes from the session, never the request |
| G3 | Correlation across command, event, job and integration | A correlation id is taken or made per request and carried onto its events |
| G4 | Idempotency for retryable commands | A command retried after a lost reply replays the first result; the same key with a different request is refused |
| G5 | Structured, non-sensitive errors with retryability | Errors carry a code, a message, whether to retry and a support reference (the conventions' "Errors") |
| G6 | Append-only durable facts through business events | Each meaningful write records a business event - named `AggregateFact` with a numeric schema version (the conventions' "Business events") |
| G7 | No direct cross-module repository or table writes | The module writes only its own tables, through its own repository |

## What is the same in every module

- **G2 is met.** Every route in the module routers names its permission except `POST /api/auth/login`; `GET
  /api/auth/me` and the two `/api/workflow` reads need a sign-in only. The three platform diagnostics in `main.py`
  (`/api/health`, `/api/platform/config-summary`, `/api/platform/db-health`) need none - TB-1 TB1-204 part b, CS-08.
  No request carries the actor: writes take it from the signed-in user.
- **G3 is not met, except in Interactions.** There is no correlation middleware (`main.py` registers CORS only), and
  `record_business_event` stores `correlation_id` as null unless a caller passes one; only Interactions does.
- **G5 is not met anywhere.** Every route answers FastAPI's `{"detail": ...}` - a string, or for invalid input a list
  of objects - with no code, retry flag or reference. `main.py`'s handlers: an unexpected database error is a plain
  `500` whose reference is logged but not returned (`core/errors.py`, TB1-503); invalid input is FastAPI's `422`;
  a credential-shaped value the event log refuses is a `422` (CS-02). `CODING_STANDARDS.md`, section 8, says the same.
  Retired by CS-06's one error envelope and handler, shipped with CS-10's shared error reader on the pages.
- **G6's naming and version are not met outside Documents and Interactions.** Events are recorded for meaningful
  writes, but `business_event` has no schema-version column and no outbox; only Documents and Interactions put a
  `schema_version` in the payload. Names are `AggregateFact` in the CRM modules, Identity, Interactions and Resource
  Requirements, and `UPPER_SNAKE_CASE` in Equipment Reference, Eligibility, Resource Assignments and Holiday Calendar
  (TB1-501). Retired by CS-06's event naming and version decision.

## By module

"Cmds" counts a module's `POST`, `PUT`, `PATCH` and `DELETE` routes.

| Module (contract) | G1 identity, version | G4 idempotency | G6 events | G7 own tables only | Retired by |
| --- | --- | --- | --- | --- | --- |
| Accounts (`account-business-party-contract.md`) | Partly: public IDs; no version | Not met: 7 cmds, none takes a key - a retried create stores twice | Partly: `AccountCreated`, `AccountTaxProfileCaptured`; no payload version | **Not met**: writes the Documents table (W3) | PF-1B; W3 in `BOUNDARY_EXCEPTION_REGISTER.md` |
| Leads (`lead-contract.md`) | Partly: public IDs; no version | Not met: 5 cmds, no key | Partly: `LeadCreated`, `LeadStatusChanged`; conversion also records `AccountCreated` and `OpportunityCreated` in those modules' names | **Not met**: conversion inserts the Account and Opportunity (W1) | PF-1B; W1 |
| Opportunities (`opportunity-contract.md`) | Partly: public IDs; no version | Not met: 3 cmds, no key | Partly: `OpportunityCreated`, `OpportunityStageChanged`, `OpportunityAccountRepaired` | **Not met**: Account repair inserts an Account (W2) | PF-1B; W2 |
| Commercial Offers (`commercial-offer-contract.md`) | Partly: public IDs; the quotation's snapshot and render carry a schema version, not the API or events | Not met: 21 cmds, none takes a key; each quotation generation or Commercial Offer version command makes a new record/action on repeat. Since CS-05a the offer's and a line's edits check an expected `row_version`, so a retry after the save is a `409`, not a replay - its `{"detail": ...}` body is G5's exception. Since CS-05c a double click whose duplicate the database refuses (the active Base Offer, the selected basis rate - per line since Slice 4G, with its open choice - a T&C clause, the current credit review) is answered with the check's `422` or a `409`, not a `500` - refused, not replayed, with the same G5 exception. Slice 9F serializes version creation under the source row lock and refuses a second preparation, but that is not replay idempotency | Partly: `CommercialOfferCreated`, `CommercialOfferCommerciallyCommitted`, `CommercialOfferVersionCreated`, `CommercialOfferVersionAbandoned`, `CommercialOfferVersionReplaced`; no payload version | Met for writes; reads other modules' tables (R3) | PF-1B; CS-11 split the service (merged 9 October) |
| Work Orders (`work-order-contract.md` and its amendment and billing-terms contracts; the frozen handoff contract) | Partly: public IDs; no version. A line's integer key passes in process to Resource Requirements, never over HTTP | Not met: 16 cmds, none takes a key; edits check an expected version, so a retry after the save is a `409`, not a replay; a repeated handoff, which made a second Work Order at `5e19123`, is refused since CS-04 part 1 merged (each offer line's quantity goes onto Work Orders once, and one customer reference per offer) - refused, not replayed | Partly: `WorkOrderCreated`, `CommercialOfferConvertedToWorkOrder`, `WorkOrderAmendmentRecorded` | Met for writes; reads and row-locks the source offer (R4) | The handoff's key and correlation id: behaviour agreed by the owner on 12 October 2026 (the frozen handoff contract's second amendment), built with PF-1B; the rest PF-1B. Slice 7D Part 5 (10 October 2026) adds billing-term fields to existing commands - no new command, event, key or table - so the row is unchanged. CS-04 part 2 items c and d (12 October 2026) add the offer's version to the Work Order and both handoff events, and the lines handed off to `CommercialOfferConvertedToWorkOrder`: more in the same events, no new command, key or table |
| Documents (`documents.md`) | Partly: public IDs; event payloads carry `schema_version` `1.0`; no API version | Not met: 2 cmds, no key - an upload retried stores twice (recorded in `documents.md`) | **Met**: `DocumentUploaded`, `DocumentGenerated`, with `schema_version` | Met; but Accounts also writes its table (W3) | PF-1B |
| Interactions (`interaction-contract.md`, `INT-001`) | **Met**: `contract_version` on responses, `schema_version` on events | **Met**, as the approved `INT-001` classifies it: a create's optional `idempotency_key` with a fingerprint - the same request replays, a different one is `409` (its "Idempotency key scope"); updating and deleting take no key, and the contract's idempotency rule covers creation only | **Met**: `InteractionRecorded`, `InteractionUpdated`, `InteractionDeleted`, versioned | Met | PF-1B (and G3 is met here, G5 is its recorded exception) |
| Equipment Reference (`equipment-reference-api-contract.md`) | Partly: public IDs; the structure's `taxonomy_version`, not an API version | Partly: 2 of 17 cmds take a key - a model's create and a kit lot's - and since TB1-102 part b both follow the shared rule (`app/shared/request_keys.py`): the very same request replays, `replayed: true`; any other request, or a key whose record predates migration `20260908_0050`, is `409`; an import is matched by the file's fingerprint | Partly: `EQUIPMENT_IMPORT_PUBLISHED`, `EQUIPMENT_ASSET_REGISTERED` - not `AggregateFact`, no version | Met | PF-1B (the two creates' rule was CS-06's early step, merged as PR #107) |
| Eligibility (`eligibility-api-contract.md`) | Partly: public IDs; no version | Partly: 3 of 8 cmds take a key - an exact repeat replays, any difference is `409`; withdrawals, "seen" marks and settings take none | Partly: `ELIGIBILITY_CERTIFICATE_RECORDED`, `ELIGIBILITY_EVALUATED`; a person's "seen" mark records none, by the contract's design | Met | PF-1B |
| Resource Requirements (`resource-requirement-api-contract.md`) | Partly: public IDs; no version | Partly: a create's key follows the shared rule since TB1-102 part b - the very same request replays, any other request (or a key whose record predates migration `20260908_0050`) is `409`; an edit checks an expected version; cancelling takes no key | Partly: `ResourceRequirementCreated`, `ResourceRequirementUpdated`, `ResourceRequirementCancelled`; no version | Met | PF-1B (the create's rule was CS-06's early step, merged as PR #107) |
| Resource Assignments (`resource-assignment-api-contract.md`) | Partly: public IDs; no version | Partly, the nearest to the rule: allocating, replacing and listing kit store the request's fingerprint - the same request replays, a different one is `409` (the function is the shared one since TB1-102 part b, giving the same digests); 7 other cmds take no key | Partly: `RESOURCE_ASSIGNMENT_HELD`, `RESOURCE_ASSIGNMENT_REPLACED`; no version | Met | PF-1B |
| Holiday Calendar (`holiday-calendar-api-contract.md`) | Partly: a year is its own key; no version | Partly: one cmd, a `PUT` with an expected version - a retry after the save is a `409`, an identical save changes nothing | Partly: `HOLIDAY_CALENDAR_YEAR_RECORDED`, `HOLIDAY_CALENDAR_YEAR_CHANGED`; no version | Met | PF-1B |
| Identity (`platform-foundation.md`) | Partly | Not applicable (sign-in) | Partly: `UserLoginSucceeded`, `UserSignInLocked`; no version | Met | PF-1B |
| Events (`workflow-and-events.md`): 1 read route | Partly: public IDs (its filter `record_public_id` is a text query parameter); no version | Not applicable: no commands | Not applicable: it records none | Met: it writes nothing | PF-1B (the version) |
| Workflow (`workflow-and-events.md`): 2 read routes | Partly: a status's `public_id`; no version | Not applicable: no commands | Not applicable: it records none | Met: it writes nothing | PF-1B (the version) |
| Terms and Conditions (`terms-and-conditions-contract.md`): 2 read routes | Partly: public IDs; no version | Not applicable: no commands | Not applicable: it records none | Met: it writes nothing | PF-1B (the version) |
| Reports (`reports-contract.md`): 4 read routes | Partly: public IDs where a record is named; no version | Not applicable: no commands | Not applicable: it records none | Met: it writes nothing; its reads of other modules' tables are a documented read model (R7 of the boundary register) | PF-1B (the version) |
| Authorization (`ORA-001`): no routes | Not applicable: no routes. The business-authority engine is dormant by decision (TB1-106) and reports in-process reason codes | Not applicable: no route takes a command | None recorded: no route reaches the engine, and its one writer, the governed configuration writer (PF-1A-E3, called in process only), records no `business_event` | Met: it writes only its own tables | When the engine is activated (APR-001, TB1-106) |
| HR Reference (`ADR-026`, `ADR-032`, `RMR-001`): no routes | Not applicable: ports and canonical data classes only - no provider, no persistence, no route (its package docstring) | Not applicable: no commands | Not applicable: it writes nothing, so records nothing | Met: it writes nothing | When a provider is wired behind its ports (the HR-reference adapter, `ADR-032`); until then nothing to meet |

G2, G3 and G5 are as "What is the same in every module" says, for every row; Interactions alone meets G3.

## Where the count of the debt stands

No module meets G5, and one meets G3. Interactions meets G4 as its approved contract classifies it (creation is its
one keyed command); no other module has G4 for all its commands: Resource Assignments comes nearest, and Accounts,
Leads, Opportunities, Commercial Offers, Work Orders and Documents have none. Three modules break G7 (the
boundary register's W1 to W3). Every module with routes but Interactions states no contract version (G1). PF-1B's
size is therefore: a contract version on every API but Interactions'; one error envelope and handler over the
seventeen routers and every page that reads an error; one correlation middleware; one idempotency rule - the shared
one Resource Assignments, Equipment Reference and Resource Requirements follow since TB1-102 part b - carried to
Eligibility's and Interactions' own and to every command that takes no key, the CRM creates and the handoff among
them; one decision on event names and versions, over the 59 names added since `MCF-001` (TB1-501); and W1 to W3.
