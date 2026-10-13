# PBL Platform Architecture and Future AI Readiness

## Status

Approved platform architecture baseline, recorded as **ADR-030** in
`docs/agent/ARCHITECTURE_DECISIONS.md`. Documentation-only; it does not change runtime behavior,
approve any AI implementation, or introduce any AI dependency. Read `docs/agent/ARCHITECTURE_DECISIONS.md`
(ADR-030) first — it is the decision of record; this document is the fuller explanation ADR-030
points to.

## Scope: this is a PBL platform document, not a CRM/Hiring-only document

The CRM + Equipment Hiring application in this repository is the **first substantial
implementation** of a broader PBL application-platform direction, not a one-off system built for
its own sake. The principles in this document apply, by default, to:

- the current CRM module;
- the current Equipment Hiring module;
- all future PBL-developed modules;
- modules progressively rebuilt or migrated away from the existing Plum ERP;
- replacement implementations of existing Plum functionality;
- new business modules that do not presently exist in Plum (for example Transportation/TMS,
  Maintenance, Fixed Assets, Finance-related operational integrations, Document Management, and
  other operational, commercial or administrative modules subsequently brought onto the PBL
  application platform);
- common/shared platform services introduced to support multiple PBL modules.

> **These are PBL platform-level architectural principles. They apply to current and future
> PBL-developed or replacement modules unless an explicit Architecture Decision Record (ADR)
> documents a justified exception.**

Whether a future module is delivered inside this repository or in a separate repository is an
implementation/delivery decision for that module, not a change to which principles govern it. Where
this document says "module," it means any PBL-developed or PBL-owned-replacement business
capability, regardless of which repository eventually hosts it.

## Why this is being documented now

Three reasons, all already true today rather than speculative:

1. **Avoid rework as Plum modules are replaced.** Without a common architectural baseline, every
   migrated module could invent its own APIs, audit conventions, document handling, authorization
   model, retry semantics and database dependencies — eventually reproducing a tightly coupled ERP
   architecture under a different technology stack. Establishing the platform principles now, while
   only two modules exist, is materially cheaper than reconciling divergent conventions across many
   modules later.
2. **Preserve the option to add AI later without paying for it now.** The characteristics in this
   document make a future AI/copilot/agent layer substantially easier to add, because that layer
   would consume the same governed services conventional applications and integrations already use.
   Building an AI stack now would add development cost, runtime cost, vendor dependency, security
   surface, observability requirements, AI-specific testing and additional failure modes with no
   present business justification. Those costs should be incurred only once a concrete, approved AI
   use case exists.
3. **Avoid future vendor lock-in.** The enduring PBL asset is well-defined business capabilities,
   authoritative data, governed service boundaries, reusable contracts, auditability and modularity
   — not today's preferred AI provider, cloud provider or frontend framework. The architecture must
   not assume any of those stay preferred indefinitely.

## 1. Platform architectural principles versus the PBL reference implementation stack

This distinction must be kept explicit everywhere this repository's architecture is discussed.

### 1.1 Platform architectural principles (enduring)

These are the architectural requirements future modules should follow unless a documented exception
is approved. They concern:

- governed application/domain services as the home of business logic (section 2 below);
- structured, machine-consumable contracts (section 3);
- identity, authorization, segregation of duties, correlation and audit (section 4);
- document abstraction and governance, independent of storage technology (section 5);
- retry-safe/idempotent write operations (section 6);
- durable processing independent of interactive sessions (section 7);
- API-first, contract-governed interoperability rather than direct coupling (section 8);
- future AI/agent extensibility as a consumer of the same governed services, never a parallel
  implementation of business logic (section 9).

These principles are intended to survive changes in frameworks, vendors, or deployment technology.
A future module built entirely differently at the implementation level can still be a fully
conformant PBL module if it honours these principles at its boundaries.

### 1.2 PBL reference implementation stack (current preference, not a mandate)

For modules developed directly by PBL under the present architecture, the preferred/reference stack
is currently:

```text
React + Vite for the frontend                    (ADR-016)
FastAPI for backend APIs and application services (ADR-004, ADR-005)
PostgreSQL as the primary System of Record         (ADR-028)
Redis where appropriate for transient/cache/coordination/streaming use cases
appropriate durable/background-processing mechanisms for long-running work (ADR-019)
controlled document storage through a repository abstraction, not direct filesystem/vendor coupling
```

This is the **preferred/reference stack for PBL-developed modules**, recorded so that a new
PBL-built module does not need to re-litigate its technology choice from scratch. It is not an
absolute technology mandate for every future component. A purchased specialist application, a
Microsoft/Power Platform component, an externally supplied module, an integration service, or a
future technology selected for a justified reason may use a different internal implementation.

Such a component must still conform to the relevant platform principles **at its integration
boundary** — API quality, identity integration, authorization, auditability, System-of-Record
ownership, document handling, integration reliability, data portability and interoperability — or
have an explicit ADR documenting why it cannot. PBL does not require internal technology conformity
from a third-party product it does not control the implementation of; it requires that the product's
boundary behaves like a governed platform citizen. Do not create unnecessary technology lock-in by
treating the reference stack as mandatory where a principled exception is available.

## 2. Keep core business/domain operations behind governed application services

### Requirement

Core business behaviour must be implemented behind well-defined application/domain-service
boundaries. Business logic must not exist solely in frontend code, UI workflows, one-off scripts,
reporting code, direct database manipulation, integration glue, or — looking ahead — AI prompts or
AI tool implementations.

Important operations should remain accessible through governed backend services and, where
appropriate, explicit APIs: retrieving Accounts, Opportunities, Commercial Offers, Work Orders,
customer credit/exposure, equipment availability/assignments, log sheets; calculating or retrieving
profitability; checking billing readiness; performing lifecycle transitions; applying business-rule
validation; creating or modifying controlled business objects. Not every internal method needs to be
publicly exposed over HTTP — the requirement is a clean application-service boundary, not universal
HTTP exposure (see section 8's "API-first does not mean API-only").

This repository already follows this pattern module by module: `backend/app/modules/<module>/`
separates `routes.py`, `service.py`, `repository.py` and `schemas.py`, per
`docs/agent/CODING_STANDARDS.md` section 2. That per-module discipline is the platform requirement,
not a CRM/Hiring-specific convention; a future Transportation or Maintenance module should follow
the same shape.

### Platform reason

This allows multiple PBL modules to reuse the same capability, integrations to use authoritative
logic rather than reimplementing it, Plum-replacement modules to interoperate cleanly, external
systems to consume controlled services, and future AI agents to invoke the same governed business
operations. The system must avoid multiple implementations of the same business rule.

### Architectural principle

> **Business rules belong to the authoritative domain/application service, not to the caller.**

A future AI agent may orchestrate these services but must not become an alternative implementation
of them.

## 3. Maintain explicit and strongly structured schemas/contracts

Continue using explicit request, response and domain schemas. For the current reference stack this
means Pydantic/FastAPI models and generated OpenAPI/JSON Schema, already the repository's practice
(`docs/agent/CODING_STANDARDS.md` section 2-3). Contracts should use explicit types, distinguish
required/optional fields, use controlled enums for defined states, have clear semantics, validate
boundaries, use documented identifiers, evolve deliberately, and remain machine-consumable.

The full inter-module contract conventions — command metadata, error shape, event envelope, change
compatibility — are already the platform baseline recorded in `MCF-001`
(`docs/agent/contracts/shared-module-contract-foundation.md`) and
`docs/agent/architecture/API_EVENT_AND_INTEGRATION_CONVENTIONS.md`. This section does not restate
those; it records that they are platform-wide, not CRM/Hiring-specific, and that they are the
authority for command/event/error shape.

### Platform reason

These contracts may serve React applications, other PBL modules, Plum integrations, external
applications, Power Platform, automation, test systems and future AI tool definitions. Avoid
creating unnecessary parallel schemas for each consumer. Where future TypeScript/Zod or AI-tool
schemas are required, they should preferably be generated or derived from the authoritative
application contracts rather than independently redefining PBL domain semantics.

### Architectural principle

> **One authoritative business contract should support many consumers.**

## 4. Preserve identity, authorization, segregation of duties, correlation and auditability

Every material operation should remain traceable, where relevant, to: authenticated user/system
actor, authorization context, role, source/channel, correlation/request/run identifier, timestamp,
affected business object, important state changes, approval, override, and reason/comment. These
controls are platform concerns and must be applied consistently across future modules, not
reinvented per module.

`MCF-001` already requires server-derived actor identity, backend-authoritative authorization, and
correlation across command, event, job and integration activity as a platform-wide guarantee, and
`docs/agent/architecture/DATA_CLASSIFICATION_AND_HANDLING.md` already sets the handling rules for
restricted, confidential and internal data that audit and correlation records must respect. This
section states the applicability, not a new mechanism.

### Platform reason

A user should not gain different authority merely because an operation passes through another
module, integration, automation or AI system. Future AI agents should therefore be treated as
governed execution channels acting on behalf of an authenticated user, or an explicitly authorised
system process — never as a source of authority in their own right.

### Architectural principle

> **No integration, automation or AI agent may acquire greater business authority merely because
> of the technology through which the operation is performed.**

The same RBAC, segregation of duties, approvals, lifecycle guards, statutory blocks and audit
requirements must apply regardless of caller.

## 5. Maintain a proper document abstraction and document metadata model

Do not tightly couple business logic to a local filesystem path, a particular cloud storage
provider, an AI provider's temporary storage, or an arbitrary uploaded-file location. Documents and
generated artifacts should have controlled identities and metadata: document identifier, document
type, owning/related business object, source, filename, MIME type, repository/storage reference,
version, created/uploaded/generated-by, timestamp, approval status, lifecycle status,
finalisation/lock status, checksum/hash, predecessor/superseded-version relationship, and retention
classification, where applicable to the document's purpose.

`docs/agent/contracts/documents.md` already establishes the core abstraction for this repository —
a `storage_mode` (`local_upload` / `external_link` / `future_sharepoint`) that keeps domain logic
independent of where a file physically lives — and the current implementation
(`backend/app/modules/documents/`) follows it. That abstraction is the platform principle; the
richer metadata fields listed above (checksum, lock/finalisation status, version lineage, retention
classification) are not all present in the current prototype-stage `document_metadata` model and
are correctly deferred future work, not a present requirement to retrofit immediately (see section
13 of ADR-030 / the implementation review below).

### Platform reason

Document handling will span multiple future modules — CRM, Hiring, Transportation, Maintenance,
Fixed Assets, Finance-related workflows, tender processing, billing, reporting. The authoritative
document model should not be recreated independently inside each module. Physical storage may
evolve over time — for example to SharePoint or another controlled repository — without forcing
domain logic to change.

### Future AI implication

If an AI system temporarily processes a copy of a PBL document, that external processing
environment must not become the authoritative PBL repository.

### Architectural principle

> **Processing locations are not Systems of Record.**

## 6. Make material write operations retry-safe/idempotent where appropriate

Design operations that can legitimately be retried with duplicate prevention and safe retry
semantics: idempotency keys, unique business constraints, request/command IDs, lifecycle guards,
optimistic concurrency, or duplicate detection. Apply the mechanism appropriate to the operation
rather than forcing one pattern everywhere.

`MCF-001` already states this as a required guarantee for retryable commands and consumers, and
`docs/agent/architecture/API_EVENT_AND_INTEGRATION_CONVENTIONS.md` already specifies the idempotency
key and consumer-idempotency conventions. What the current implementation actually has today is
narrower: targeted unique-constraint-based duplicate prevention in specific places (for example the
case-insensitive unique username index, the one-active-Base-Offer-per-Opportunity guard, and the
filtered unique index on Lead-to-Opportunity conversion), not yet a general idempotency-key envelope
applied across commands. This gap is recorded honestly in the implementation review below rather
than silently assumed closed.

### Platform reason

Retries already arise from network failures, integration failures, service restarts, worker
crashes, timeouts and uncertain acknowledgements. This becomes more important, not less, as more
modules and automated consumers are introduced. Future AI agents will also frequently operate in
environments where tool calls may be retried.

### Architectural principle

> **Retry safety must be enforced by the receiving business service rather than depending on the
> caller never retrying.**

## 7. Keep long-running work durable and separate from interactive HTTP/UI sessions

Tasks that may be long-running, restartable or asynchronous must not depend on a browser remaining
open, one HTTP connection, one frontend session, or one application-process lifetime. Where
appropriate, the architecture should support persistent job/run identity, explicit processing
states, queued/claimable work, checkpoints, retries, resume/restart, failure state, progress events
and final output references.

For the present architecture, PostgreSQL remains authoritative for durable business/job state unless
a later ADR establishes another durable mechanism (ADR-019 already anticipates a database-backed job
queue behind an abstraction, precisely so this can be adopted without redesigning business modules
when it is needed). Redis may support transient caching, coordination, event delivery or stream
state, but must not become the authoritative System of Record for completed business processes.

The current implementation has no durable background-job runtime yet — every current CRM/Hiring
operation is synchronous request/response, and ADR-019 remains a decision record, not yet an
implemented mechanism. This is not a contradiction of the principle; nothing in the current scope
has needed durable asynchronous processing, and the architecture already anticipates adding it
without redesign. It is recorded as a gap to close through normal future development, not a defect
to fix now (see the implementation review below).

### Platform reason

This supports conventional workloads such as imports, exports, billing preparation, document
generation, integration processing, batch jobs and reconciliations, as well as future AI workloads.
The UI may use polling, Server-Sent Events, WebSockets, or another event mechanism to display
progress.

> **The UI observes the durable process; it does not keep the process alive.**

## 8. Additional platform principles

### 8.1 API-first does not mean API-only

Business capabilities should have clean service boundaries. Externally or cross-module-consumed
capabilities should be exposed through appropriate APIs/contracts. Internal implementation may use
application-service calls directly where appropriate. Do not introduce needless HTTP hops inside a
single service merely to claim API-first compliance. The important property is explicit, governed
boundaries and replaceability, not maximal HTTP surface area.

### 8.2 Avoid direct cross-module database coupling

As the number of modules grows, one module should not casually query or modify another module's
internal tables. Preferred patterns are authoritative application services, explicit APIs,
controlled integration events, or documented read models where justified. Direct cross-module
database access should require explicit architectural justification. This is already recorded as
`PRODUCTION_ARCHITECTURE_DIRECTION.md`'s dependency rule 4 ("A module does not write another
module's tables or import its repository"); this section confirms it is a platform-wide rule, not a
CRM/Hiring-specific one, and is particularly important during the progressive migration from Plum.

**Current implementation note.** This rule is not yet fully honoured in this repository's
prototype-era code: `leads/service.py` and `opportunities/service.py` currently import the
`accounts` (and, for Lead conversion, `opportunities`) module's `repository` layer directly, rather
than going through an application-service interface. This predates the PAF-1 architecture records
that state the rule, reflects the deliberate "modules initially deployed together" prototype
starting point recorded in ADR-004, and is exactly the kind of retrofit PF-1B ("API/event retrofit")
is intended to address for existing routes/services. It is recorded here as a known, pre-existing
gap between documentation and code — not newly created by this document — and is left as follow-up
work rather than refactored as part of this documentation change (see the implementation review
below).

### 8.3 Make System-of-Record ownership explicit

For each major business entity/capability, documentation should identify which system/module is
authoritative. `docs/agent/architecture/MODULE_BOUNDARY_OWNERSHIP_MATRIX.md` already does this for
the current CRM/Hiring boundary (Account/Customer, Opportunity, Commercial Offer, Work Order,
equipment/employee/vendor masters, and the shared platform capabilities); a future module must add
its own row(s) there or in an equivalent record rather than leaving ownership implicit. During Plum
coexistence, unclear ownership can create conflicting records; avoid dual-master situations unless
explicitly designed as temporary migration arrangements with a recorded end state.

### 8.4 Reuse common platform capabilities where appropriate

Future modules should not independently reinvent identity/authentication, authorization/RBAC,
audit, correlation IDs, document metadata, notifications, integration conventions, background-job
conventions, or common master-data identifiers.
`docs/agent/architecture/MODULE_BOUNDARY_OWNERSHIP_MATRIX.md`'s "Shared platform capability modules"
table already lists these as logical modules with one clear owner each, explicitly not requiring a
separate server, database or deployment merely to exist as a shared capability. Do not prematurely
build a large "shared services" platform merely for architectural purity — create shared
capabilities when actual reuse emerges, but maintain consistent conventions from the start so that
emergence does not require a rewrite.

## 9. Relationship with Plum during migration

Migration away from Plum is expected to be progressive, not a single replacement event. During the
transition period the architecture must support coexistence between new PBL modules, retained Plum
modules, external systems and shared services. The boundary between Plum and newly developed modules
should increasingly be based on explicit contracts/APIs rather than uncontrolled direct coupling —
`docs/agent/architecture/EXTERNAL_DEPENDENCY_REGISTER.md` and the Integration Gateway capability row
in the module boundary matrix are the existing mechanisms for this.

Where a business capability is moved out of Plum:

1. ownership of that capability should be explicit;
2. its authoritative System of Record should be explicit;
3. integration contracts with retained modules should be explicit;
4. duplicate ownership of business rules should be avoided;
5. migration should not create competing authoritative implementations.

The long-term direction favours independently replaceable modules sharing common platform
governance over rebuilding a new monolithic system outside Plum under a different name.

## 10. Governing principles for future AI

**Restated plainly: nothing in this section approves, requires, or schedules any AI implementation.
It exists so that if and when a business-justified AI capability is approved, it can be added
without restructuring the transactional application platform.** See "Explicit non-goals" below and
ADR-030 for the current-scope boundary.

### 10.1 AI uses governed tools/services, not direct database access

Preferred future pattern:

```text
AI -> governed tool/application service -> authorization + business rules -> System of Record
```

Not:

```text
AI -> unrestricted PostgreSQL
```

The same applies to any other authoritative system a future AI layer might need to read from or act
on.

### 10.2 Use AI for uncertainty; deterministic software for certainty

> **Use AI where interpretation, ambiguity, language understanding or judgement adds value. Use
> deterministic software for calculations, business rules, reconciliation and repeatable
> processing.**

| Requirement | Preferred mechanism |
| --- | --- |
| Calculate financial totals | SQL/Python/application code |
| Calculate equipment utilisation | deterministic code |
| Apply credit-limit rules | domain service |
| Enforce statutory block | domain service |
| Validate lifecycle transition | domain service |
| Reconcile report totals | deterministic code |
| Interpret a natural-language question | AI |
| Explain unexpected trends | AI |
| Summarise complex findings | AI |
| Decide which governed tools may answer an ad-hoc question | AI orchestration |
| Repeat an approved monthly computation | deterministic software |

### 10.3 Keep the AI/model vendor replaceable

Do not embed vendor-specific concepts (any particular LLM provider, hosting platform, or SDK) into
core PBL domain models unless technically unavoidable. A future AI layer should sit behind an
integration/orchestration boundary. The platform should permit model replacement, model routing by
task, multiple providers, local/on-premise models where appropriate, and replacement of AI
processing with deterministic code. The transactional platform must remain fully usable if the AI
subsystem is unavailable or removed entirely.

### 10.4 Introduce future AI capability progressively

Any future agent capability should normally progress through maturity stages: (1) read-only
conversational/query functionality; (2) analysis and report generation; (3) preparation of draft
business objects/actions; (4) human-approved execution; (5) limited autonomous action only where
business value and governance justify it. Do not treat future AI enablement as automatic authority
to modify transactional data.

Future requirements that would eventually motivate this maturity path may include conversational
access to business information, natural-language operational analysis, exception identification and
explanation, management reporting, analytical workbook/PDF generation, workflow assistance,
preparation of draft transactions or amendments, analysis of customer/job/equipment profitability,
and controlled agentic execution of approved processes — none of which are in scope now. These
capabilities should eventually consume the same governed application services used by conventional
applications and integrations. Do not create a separate parallel application architecture
specifically for AI.

## Explicit non-goals of this document

This document does not implement AI, an agent, a chatbot, or any AI SDK; does not create AI prompts;
does not add vector search, embeddings or RAG infrastructure; does not select an AI vendor, model or
provider; does not create speculative AI-specific abstractions; does not upload PBL data anywhere;
does not build a new backend or runtime; does not perform a broad CRM/Hiring refactor; does not begin
migration of any additional Plum module; and does not convert the current architecture into
microservices merely because future modules are anticipated. The goal is clear architectural
direction and preservation of future options, not premature infrastructure. See ADR-030 for the full
non-goals list and current-scope statement.

## Applicability and exceptions

> **Any future module developed by PBL, or developed specifically for PBL as a replacement for
> existing Plum functionality, should be designed against these platform principles from its
> inception unless an approved ADR records a justified exception.**

For externally acquired products, require conformance at the integration boundary where technically
possible; do not demand internal technology conformity PBL does not control. A material departure
from the reference implementation stack, a particular infrastructure pattern, or a particular shared
service is acceptable where there is a justified requirement, but must be recorded through an ADR
identifying: the principle being varied, the reason, alternatives considered, consequences,
integration implications, security/governance implications, and whether the exception is temporary
or permanent. Platform principles are therefore **default and enforceable, but explicitly
overridable through architectural decision — not casually ignored.**

## Cross-references

- `docs/agent/ARCHITECTURE_DECISIONS.md`, ADR-030 — the decision record this document explains.
- `docs/agent/architecture/README.md` — reading order for the full production architecture set.
- `docs/agent/architecture/PRODUCTION_ARCHITECTURE_DIRECTION.md` — the current system shape and
  dependency rules this document generalizes to platform scope.
- `docs/agent/architecture/MODULE_BOUNDARY_OWNERSHIP_MATRIX.md` — System-of-Record ownership and
  shared platform capability modules.
- `docs/agent/architecture/API_EVENT_AND_INTEGRATION_CONVENTIONS.md` and
  `docs/agent/contracts/shared-module-contract-foundation.md` (`MCF-001`) — command/event/error/job
  conventions this document treats as platform-wide.
- `docs/agent/architecture/DATA_CLASSIFICATION_AND_HANDLING.md` — data-handling categories that
  audit, correlation and document metadata must respect.
- `docs/agent/contracts/documents.md` — the current document-metadata contract this document builds
  on.
- `docs/agent/PROJECT_OVERVIEW.md` — states that CRM/Hiring is the first implementation of this
  platform direction.
- `docs/agent/architecture/PLATFORM_PRINCIPLES_IMPLEMENTATION_REVIEW.md` — the one-time review of
  the current CRM/Hiring implementation against every principle in this document, including the one
  material contradiction found.
