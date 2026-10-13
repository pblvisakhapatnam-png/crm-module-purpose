# 04 - How we build

These are the rules the code already follows, and that we ask you to keep. Each is stated briefly, with the record
that holds it in full and, where it matters, how far today's code meets it. This page points to the records; where a
record and this page differ, the record applies and we would like to hear about the difference.

Most of these rules were decided for good reasons that are written down. If one stands in the way of the agreed work,
tell us; do not work around it.

## The shape of the system

- **One application, in modules.** It is deployed as one application, divided into modules (Leads, Accounts,
  Commercial Offers and so on). Each module owns its own tables, rules and status changes. No module writes another
  module's tables: it asks the owning module, or reacts to its events. *Records: ADR-004, ADR-005, ADR-017;
  `docs/agent/architecture/MODULE_BOUNDARY_OWNERSHIP_MATRIX.md`; `docs/agent/architecture/PRODUCTION_ARCHITECTURE_DIRECTION.md`.*
- **One owner for every fact.** Each piece of information has one system and one module that owns it. A copy kept
  for a decision (an approved price, a handed-off line) records the value used at the time; a report never becomes the
  owner of anything. *Records: `docs/source/current/governance/PBL_CRM_Equipment_Hiring_System_of_Record_Matrix_Clarified.md`;
  ADR-030.*
- **Exceptions are written down.** Where today's code crosses a module boundary, the crossing is listed with how it
  will be removed (annex A). A change that adds one adds its row; a change that removes one deletes it. *Record:
  `docs/agent/architecture/BOUNDARY_EXCEPTION_REGISTER.md`.*
- **Our own structure, with outside data brought in.** PBL designs the best structure for its own information - for
  example the equipment structure - and data from outside systems is translated into it on the way in, with doubtful
  values flagged rather than silently changed. *Records: ADR-037, ADR-022.*

## Security

- **The server decides.** Every business route checks the user's permission on the server (the health and
  platform-status addresses are recorded exceptions; annex A, CS-08); the acting user comes from the session, never
  from what the screen sends. Hiding a button is a convenience, not a control. *Records: MCF-001
  (`docs/agent/contracts/shared-module-contract-foundation.md`), "Authorization"; `docs/agent/CODING_STANDARDS.md`.*
- **Roles today, authorities tomorrow.** Six roles (Admin, Sales User, Sales Manager, Finance User, Operations User,
  Management Read-Only) map to 55 permissions in `backend/app/modules/authorization/contract.py`. Nothing yet limits a
  person to their own records, and only a few reads are narrower by role; who sees what is a PBL decision still to come
  (Q-14). For business authority - who may assess credit, who may approve - the code is to ask for a named authority,
  never a hard-coded person or role; an engine for that exists and is switched off until the HR feed is bought (doc 03,
  group C). Until then, an administrator names each kind of approver - a role or a person - in the application's
  settings: a recorded exception, ADR-038. Today the one approval built, a quotation's approval for issue, is a role
  permission (Admin, Sales Manager). *Records: ORA-001; ADR-026,
  ADR-033; `docs/agent/pf-1a/`.*
- **Personal and statutory data is protected.** PAN, contact details, conversation notes and identity evidence are
  restricted: need-to-know access, never real values in test data, logs or events. Passwords and keys live only in a
  secret store, never in the code. Indian law applies (IT Act, DPDP Act, CERT-In). *Records:
  `docs/agent/architecture/DATA_CLASSIFICATION_AND_HANDLING.md`; `docs/agent/architecture/NFR_BASELINE_AND_VERIFICATION.md`.*

## Business rules and records

- **Every meaningful action is recorded** as a business event: who, when, which record, the status before and after,
  and why. Events are never edited and never carry passwords or keys (the system refuses them). *Records:
  `docs/agent/contracts/workflow-and-events.md`; `docs/agent/architecture/API_EVENT_AND_INTEGRATION_CONVENTIONS.md`.*
- **Approvals** will be one shared facility: it records each request and decision against the version of the record;
  the module that asked enforces the answer; approving your own work is refused where the policy says so; delegation
  is explicit and time-limited. Not built yet (doc 03, group A). *Record: APR-001,
  `docs/agent/contracts/approval-policy-contract.md`.*
- **Notifications** will be one shared facility too: the module decides why, to whom and when; Notifications delivers,
  retries and records delivery. A failed message never relaxes a deadline or an approval. Not built yet. *Record:
  NTF-001, `docs/agent/contracts/notification-delivery-contract.md`.*
- **Documents** are stored through one storage layer, so that SharePoint can replace today's local disk without the
  modules noticing. People download through the application, which checks their right to the linked record. *Records:
  ADR-036; `docs/agent/contracts/documents.md`.*
- **Conversations** with customers are one log, owned by one module, which any future connector for email or
  WhatsApp must write through. *Record: INT-001, `docs/agent/contracts/interaction-contract.md`.*
- **Money**: INR by default, USD, GBP or EUR when chosen, never converted and never added across currencies
  (`AGENTS.md`, "Currency").
- **Time**: kept in UTC, shown and entered in India's time, through one shared way of doing each (`AGENTS.md`,
  "Date/time display rule").

## The interface between screens and server

- **Under `/api`, by public identifiers.** Records are identified by their public IDs, never by internal numbers.
  Reading never changes anything. A date and time sent to the server carries its time zone. Additions are preferred
  to changes; removing or renaming something needs a new version. *Records: `docs/agent/CODING_STANDARDS.md`, section
  3; `docs/agent/architecture/API_EVENT_AND_INTEGRATION_CONVENTIONS.md`.*
- **A repeated request must not do the work twice.** The shared rule is a request key: the very same request repeated
  gets back what it first made; a different request with the same key is refused. The conversation log and three
  Hiring modules use it; Leads, Accounts, Opportunities, offers, documents and the handoff do not yet. For offers and
  offer lines an out-of-date save is refused rather than overwriting someone else's; elsewhere the last save still
  wins (annex A, CS-05b). *Records:
  `docs/agent/CODING_STANDARDS.md`, section 2; `backend/app/shared/request_keys.py`.*
- **Errors** - the intended form is one structured error with a code, a safe message and a support reference, never a
  stack trace. **Today every route still answers in the framework's plain form**, a recorded exception. Moving to the
  intended form, with a tracking id carried from each request to its events and a request key on every command, is
  the shared request rules option (PF-1B, doc 03, group C). *Records: `docs/agent/architecture/MCF_ADOPTION_RECORD.md`;
  `docs/agent/CODING_STANDARDS.md`, section 8.*

## Outside systems

Each outside system is reached through its own adapter, which keeps that system's way of doing things to itself; the
modules see PBL's own terms. Every call has a time limit, retries and protection against doing the work twice; the
system keeps the outside reference and whether the two sides agree, never the outside system's passwords. Replacing a
provider is then contained to its adapter - not free, but contained. Doc 06 covers each system. *Records:
`docs/agent/architecture/API_EVENT_AND_INTEGRATION_CONVENTIONS.md`, "External integrations"; ADR-022, ADR-037;
`docs/agent/architecture/EXTERNAL_DEPENDENCY_REGISTER.md`.*

## The database

- **PostgreSQL only**, written in PostgreSQL's own language; no second database, no code for two. Version 17 today;
  a later version may be proposed (doc 10). *Record: ADR-028.*
- **Every change to its structure is a migration written by hand**, added at the end of one single chain. Generated
  migrations are refused by the code itself. An existing migration is never edited. PBL decides the order when two
  pieces of work need one. Each is proved from an empty database. *Record: `db/notes/migration-rules.md`.*
- **Back up before every upgrade; undo a release by restoring.** The server applies migrations when it starts and
  stops at once if one fails. A release is undone by putting back the previous release and restoring the backup taken
  just before the upgrade - never by stepping a database that holds data backwards. *Record:
  `db/notes/migration-rules.md`, "Undoing a release".*

## Testing and acceptance

- **A test is worth having only if it fails when the rule it protects is broken.** Each route is tested for success,
  bad input, not found, not allowed and the shape of its answer. Existing tests are never weakened to let a change
  pass. A test that depends on today's date uses the shared test day. *Record: `docs/agent/TESTING_STRATEGY.md`.*
- **One combined result decides.** Every proposed change runs the full checks; `Required validation` succeeds only if
  every one of them succeeds (doc 07). *Record: ADR-031.*
- **Done means done.** A change stays within its agreed scope; has its migration if the structure changed; matches
  its contracts, or updates them; records any new boundary crossing; tests its permissions and its events; passes the
  full checks; and updates its contract, slice and acceptance records. *Record:
  `docs/agent/architecture/PRODUCTION_READINESS_GATES.md`, "Module-slice Definition of Done".*
- **Each piece of work can be tried by a person in 10 to 20 minutes**, with the steps written in its acceptance
  record. *Record: `docs/agent/UI_UAT_GUIDELINES.md`.*

## Running in production

- **Logs help support without leaking.** Failures are logged in enough detail to diagnose; passwords, keys and
  sensitive business data never are, and a database error is logged by its kind, never by the values in it. Business
  history comes from events, not logs. *Records: `docs/agent/CODING_STANDARDS.md`, section 9;
  `backend/app/core/errors.py`.*
- **Background work** - reminders, rechecks, heavy reports - goes through one job queue behind a shared interface.
  Not built yet; everything runs at once today (doc 03, group C). *Record: ADR-019.*
- **Speed, availability, backups, recovery and support** are set out in doc 10.

## Ready for AI, without building it now

PBL expects to use AI in the platform later, and the architecture is ready for it in one specific way:

```text
AI  ->  the application's own governed services  ->  permissions and business rules  ->  the records
```

and never `AI -> the database directly`. AI acts for a signed-in person, with no more authority than that person has;
calculations and business rules stay in ordinary code; the AI provider stays replaceable; and the platform works with
AI switched off. *Records: ADR-030; `docs/agent/architecture/PBL_PLATFORM_ARCHITECTURE_AND_FUTURE_AI_READINESS.md`.*

Recorded as future capability, **not part of this package**:

- help in plain language on the screen a person is using;
- questions about the business in plain language, and analysis of operations;
- reports and dashboards produced on request;
- freedom to change AI model or provider;
- reporting through defined, governed queries rather than database queries written freely by an AI;
- AI actions only within the signed-in person's permissions.

Please do not introduce an AI platform or AI features in this package. Keeping the shape above - business rules in
services, permissions on the server, every action recorded - is what keeps the door open.

## Where the rest is

| Topic | Record |
| --- | --- |
| Every architecture decision, with its reasons | `docs/agent/ARCHITECTURE_DECISIONS.md` |
| The architecture records and their reading order | `docs/agent/architecture/README.md` |
| Coding conventions in detail | `docs/agent/CODING_STANDARDS.md` |
| The contracts between modules, and their status | `docs/agent/architecture/CONTRACT_REGISTRY.md`, `docs/agent/contracts/` |
| How far each module follows the shared module rules | `docs/agent/architecture/MCF_ADOPTION_RECORD.md` |
| Screens: what is known to need work | `docs/agent/UI_UX_CARRY_FORWARD.md` |
