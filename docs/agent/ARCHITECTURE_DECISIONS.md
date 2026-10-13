# Architecture Decisions

This file records technical and delivery decisions that coding agents must follow.

## ADR-001: Production-style prototype

Decision: Build as a production-style prototype, not as a throwaway demo.

Reason:
- The prototype may be shown to the Plum vendor.
- The prototype may become a reusable reference implementation.
- The data model, contracts, workflow controls and tests should therefore be disciplined from the beginning.

## ADR-002: CRM first, preserve downstream paths

Decision: Build CRM first, but preserve future Equipment Hiring and Transportation integration paths.

Reason:
- CRM will later hand off to Commercial Offer, Work Order, Equipment Hiring and Transportation.
- Early CRM decisions must not create duplicate party/customer data or break lifecycle traceability.

## ADR-003: Account in UI, business_party internally

Decision:
- UI label: Account.
- Internal module/model: business_party.

Reason:
- The business user should see the familiar term Account.
- The backend should remain flexible because one party may later hold multiple roles.

## ADR-004: Single-deployment modular architecture first

Decision: Use one modular API-first application, initially deployed together rather than as
separate microservices.

Reason:
- Keeps the first prototype practical.
- Preserves clear module boundaries and API contracts.
- Avoids deployment and integration complexity too early.

Implication:
- Backend modules must remain separated under `backend/app/modules/`.
- Each module should have routes, schemas, service layer, repository layer and tests.
- Shared concerns should stay in `backend/app/core/` or `backend/app/shared/`.

## ADR-005: API-first but not microservice-first

Decision: Use explicit module-level API routes and OpenAPI documentation.

Reason:
- Agentic coding works better with clear contracts.
- The vendor may later reuse the contracts even if implementation is in PHP/MS-SQL.

Implication:
- Contract files under `docs/agent/contracts/` are mandatory before module implementation.
- FastAPI OpenAPI output should reflect implemented route contracts.

## ADR-006: SQL Server from day one

Decision: Use SQL Server Developer Edition in Docker for local development.

Status, updated 13 August 2026: **superseded for the production baseline by ADR-028**, which
records PBL's confirmation of PostgreSQL. This decision governed the prototype foundation and
remains an accurate historical record of how that foundation was implemented; it is preserved for
that reason and is not withdrawn. It no longer selects the production database.

Reason:
- The vendor environment is expected to use MS-SQL.
- SQLite could hide differences in constraints, data types, migrations and query behavior.

Implication:
- Use SQLAlchemy 2.x and Alembic migrations.
- Do not make schema changes without a migration.
- Use database naming that remains portable to PHP/MS-SQL usage.

## ADR-007: ID strategy

Decision: Use integer identity primary keys, UUID public IDs and visible business reference numbers.

Pattern:
- Internal DB ID: integer identity.
- Public ID: UUID.
- Business reference: e.g. `ACC-000001`.

Reason:
- Internal IDs are efficient.
- UUIDs are safer for APIs and future integrations.
- Business references are readable for users and documents.

### Exception, 8 October 2026: no business reference for Accounts, Leads and Opportunities, for now

Approved by the project owner on 8 October 2026 (TB-1 finding TB1-402, corrective package CS-16). It answers the
question CS-18 left open (`docs/continuity/CS_18_GOVERNANCE_RECORDS.md`, question 1). Recorded with the headings
ADR-030's exception process asks for.

- **What it covers.** (1) Accounts (`business_party`), Leads (`crm_lead`) and Opportunities (`crm_opportunity`) keep
  their integer key and UUID public ID but get no visible business reference: people know and find them by name, and
  a link carries the public ID. (2) Commercial Offer and Work Order codes (`CO-000001`, `WO-000001`) stay made as they
  are - set straight after the insert, keeping the ID's last six digits - rather than moved to the generated column
  that requirements, machines and allocations use (`RR-`, `EQ-`, `AL-`). Integer keys and public IDs, and every other
  record's reference, are unchanged.
- **Principle varied.** This decision's "visible business reference numbers", for those three record types; and its
  implied one way of making a reference, for offer and Work Order codes.
- **Reason.** Nothing in the work now planned needs to cite these records by number, and adding references changes
  what users see and quote - a migration in each of three CRM modules and changes to their screens - for no present
  use. The code form is safe at PBL's volume: it repeats an earlier code only from the 1,000,001st offer or Work Order
  (thousands a year are expected), and its unique index then refuses the record rather than storing a duplicate.
- **Alternatives considered.** TB-1's recommendation: `ACC-`, `LD-` and `OPP-` references as generated columns,
  backfilled from the ID, and the `CO-`/`WO-` codes moved to the same form - deferred, not rejected. References for
  Accounts only - deferred with the rest.
- **Consequences.** Account names are not unique (the duplicate rule is itself deferred), so two similar Accounts
  are told apart by their details, not by a number; quotations and documents name the Account. A vendor reading this
  ADR should not expect `ACC-` numbers; the database conventions record says the same
  (`db/notes/naming-conventions.md`, "Business references").
- **Integration and security.** An integration refers to these records by public ID, which this ADR already makes the
  external identifier; nothing exposes more or less than before. No permission, event or API changes.
- **Temporary, and when it ends.** Temporary. Part (1) ends when PBL asks for visible numbers or a package needs to
  cite these records by number - for example a document template or Customer Master activation (`CMA-001`) - and is
  built by CS-16's reference migration; it is to be looked at again before production at the latest. Part (2) ends
  when CS-16 moves the codes to the generated form, which is needed only before the millionth offer or Work Order.

## ADR-008: Simple auth and roles early

Decision: Implement simple authentication and role checks early.

Initial roles:
- Admin
- Sales User
- Sales Manager
- Finance User
- Operations User
- Management / Read Only

Reason:
- Role-based access, workflow gates and segregation of duties are cross-cutting NFRs.
- Adding role logic too late causes rework.

## ADR-009: Lightweight workflow and business events

Decision: Build simple reusable `workflow_status` and `business_event` foundations, not a heavy workflow engine.

Reason:
- The project needs traceability and status control from the beginning.
- Full approval/workflow complexity can come later.

## ADR-010: Document metadata first

Decision: Start with document metadata and local upload/link support. SharePoint integration can come later.

Reason:
- The ERP record must preserve document type, linked object, version/status and access metadata.
- Storage mechanism can evolve later.

## ADR-011: Two documentation sets

PBL's internal documentation practice (an agent-facing set and a continuity set). Not part of this copy; the vendor documents under `docs/vendor/` replace it for a vendor.

## ADR-012: Tool-portable agent instructions

PBL's internal rule for the instruction files its own coding tools read. Not part of this copy.

## ADR-013: Source document authority hierarchy and directional-versus-binding guidance

Decision: Establish an explicit authority hierarchy for resolving conflicts between source documents, extracts, matrices, contracts, decisions and instructions, and classify most source-document content as directional guidance rather than binding technical prescription.

Reason:
- The repository now holds ERP-wide formal requirements (`docs/source/current/requirements/`), a directional System-of-Record Matrix (`docs/source/current/governance/`), derived extracts (`docs/reference/erp-source-extracts/`) and a growing set of frozen contracts and approved architecture decisions.
- Without an explicit hierarchy, a later agent could treat an older source document's suggested workflow, ownership arrangement or field treatment as equally or more authoritative than a later approved decision, silently reversing a deliberate choice.
- Source documents describe business intent and preferred direction as understood when they were prepared. They are not automatically wrong when a later decision differs, and they are not automatically binding either.

Authority hierarchy, highest first:

```text
1. Current explicit human instruction or approved decision
2. Frozen contracts and approved architecture decisions
3. Accepted requirements and active slice acceptance criteria
4. Current module contracts and active implementation documentation
5. Current source and reference documents (docs/source/, docs/reference/erp-source-extracts/)
6. Historical continuity records and superseded drafts
```

Directional-versus-binding rule:
- Unless a provision is explicitly classified as a frozen contract, approved architecture decision, mandatory control, accepted requirement or current approved business rule, its proposed workflow, ownership arrangement, module boundary, field treatment or implementation approach is directional guidance, not a binding technical prescription.
- An agent or developer may adopt a different, better solution during detailed design or implementation where it is demonstrably clearer, safer, simpler, more maintainable, more extensible or more appropriate to the actual business requirement.
- A different solution is acceptable only where it preserves or improves: the intended business outcome; authorization and segregation of duties; auditability and traceability; statutory and mandatory controls; NFR compliance; cross-module compatibility; frozen API and event contracts; and the agreed API-first modular direction.
- Material deviations must not be made silently. The implementation record (slice note, contract update or continuity note) must identify: the original suggestion; whether it was directional or binding; the proposed alternative; why the alternative is better; affected contracts, modules, data, migrations, events, security and tests; and any limitation, risk or deferred work.
- A frozen contract, explicit current human instruction, approved business rule or accepted architecture decision may not be changed without human approval, regardless of what an older source document says.

Implication:
- An original source document remains authoritative for what it said when it was prepared; that is a historical fact, not a live prescription.
- A source document does not automatically override a later explicit PBL decision, frozen contract, approved architecture decision or current implementation instruction.
- The latest approved decision controls where it intentionally refines an earlier source; the older wording must remain preserved as historical input, not silently erased.
- See `docs/source/README.md` for the full folder structure and reconciliation workflow, and `docs/reference/erp-source-extracts/README.md` for how derived extracts are classified.

## ADR-014: Automate deterministic validation; reserve human review for exceptions and judgement

Date recorded: 11 August 2026.

Decision: Where a trusted integration can deterministically validate a required fact, the system should perform that validation automatically. Human review should be introduced only for failures, mismatches, ambiguity, policy exceptions, or genuine business decisions requiring judgement or approval.

Reason:
- Routing an already-validated fact to a human merely to reconfirm it adds delay, creates an illusion of control, and produces an approval record that carries no real decision content.
- A validation and an approval are different things. A validation answers a question of fact. An approval is a business decision that a person or role is accountable for.
- Segregation of duties and auditability are preserved better by recording what was validated, by which source, when, and with what reference, than by collecting a human signature on a fact nobody actually re-checked.

Implication:
- A workflow step that exists only to reconfirm a successfully validated fact should be removed or downgraded to an exception path.
- Automatic validation must still be evidenced. Record the outcome, the provider, the timestamp and the reference, so the automated decision is auditable in the same way a human decision would be.
- A third-party validation service must not be described as granting business approval unless it genuinely does so. Such services validate facts; business approvals remain separate where required.
- An exception path must always exist. Failure, mismatch, ambiguity, provider unavailability and policy-defined exceptions route to a named human role.
- This principle does not weaken any mandatory control, statutory requirement, maker/checker rule or genuine approval gate recorded elsewhere in this repository.

## ADR-015: Integration-driven Account legal identity validation, and separation of identity, credit and exposure

Date recorded: 11 August 2026.

Amended: 13 August 2026, by explicit PBL decision. Credit assessment authorization is expressed
through the configurable `CREDIT_ASSESSOR` business authority (`ORA-001`) rather than being
permanently fixed to the `SALES_MANAGER` application role. `SALES_MANAGER` remains the
initial/default mapping. The amendment changes only how the assessor is authorized; it does not
change who may initiate an Account, the separation of identity/credit/exposure, or the credit
approval policy in Q-06. See "Master-data ownership" below and `OPEN_QUESTIONS.md` Q-07.

Status: supersedes the earlier working assumption that a newly created Account / Qualified Prospect must be routed to Accounts/Finance for manual PAN/GST verification and approval before the Account is confirmed.

Decision: For Account / Qualified Prospect onboarding, legal identity is validated through PBL's existing SurePass integration rather than through a routine manual Accounts/Finance approval step. Legal identity validation, credit assessment/approval, and financial exposure are treated as three separate concerns with three separate owners.

### Legal identity validation

- PAN and GSTIN captured against an Account are passed to SurePass for validation.
- Where the service supports it, the validated response is used to obtain or confirm authoritative legal-entity information such as legal/entity name, PAN details, GST registration details and status, registered/legal address, and other relevant identity fields returned by the service.
- A routine manual Accounts/Finance approval step is **not** required merely to reconfirm information already successfully validated through SurePass.
- Human review is exception-driven only: PAN/GST mismatch, validation failure, incomplete or ambiguous response, a policy-defined exception, or prolonged provider unavailability requiring the authorized manual route. A temporary outage alone leaves verification pending and does not halt operations.

### Separation of concerns

```text
A. Legal identity validation
   Question: Is this legally the entity claimed?
   Mechanism: SurePass / authoritative external validation.
   Nature: normally deterministic validation, not a human approval.

B. Credit assessment and approval
   Question: What credit limit and payment/credit days should PBL allow?
   Business ownership: the assessment requires a current, active CREDIT_ASSESSOR
   authority assignment for the relevant scope; the configured Department Head or
   Managing Director provides the applicable approval under CREDIT_APPROVER.
   SALES_MANAGER is the initial/default mapping for CREDIT_ASSESSOR, not the
   permanent authorization rule.
   Note: do not assume Accounts/Finance owns this assessment or approval merely
   because the subject matter is credit.

C. Financial exposure
   Question: How much approved credit is currently consumed/outstanding?
   Nature: a separate financial/ERP concern; may be consumed and monitored by
   Finance/Accounts.
```

These three must remain separately modelled. A single "customer approved" flag that conflates them is not acceptable.

### Verification state

An Account must not be modelled as simply approved or not approved. The architecture supports explicit verification states, conceptually:

```text
UNVERIFIED
VERIFICATION_PENDING
VERIFIED
VERIFICATION_EXCEPTION
```

Exact enum names may be adjusted to fit existing repository conventions when a slice implements this.

A temporary SurePass outage must not prevent an Account / Qualified Prospect record from
existing or hard-block downstream operational work. The Account remains pending/unverified, and
the outage, retries and eventual result are auditable. A validation failure, invalid identifier
or SurePass-returned mismatch is a separate identity exception and is not converted into an
allow decision by this availability rule. For prolonged or permanent provider unavailability,
the architecture supports an authorized, audited manual validation route until service is
restored.

### Verification evidence and audit

Retain appropriate evidence/metadata from the validation, such as:

```text
verification status
verification timestamp
source/provider = SurePass
external/reference/request ID where available
validated PAN/GST identifiers
returned legal name/address/details as appropriate
mismatch/exception reason
```

Do not persist unnecessary third-party payload data merely because the provider returns it. Apply data minimisation, retaining what audit and business traceability genuinely require.

SurePass-returned legal identity values are authoritative over user-entered or customer-document
values for the same fields. The validated legal name, registered address, PAN/GSTIN details and
registration status populate the Account Master where the service supports them. Preserve the
original value and mismatch as evidence. If a customer's Work Order conflicts with SurePass,
first correct and revalidate an incorrectly entered PAN; if the PAN is correct, obtain a corrected
Work Order before treating that document as identity-consistent.

Evidence-retention duration and any periodic re-verification interval/trigger are authorized
policy parameters whose values remain deferred. Implementations must not invent defaults or
silently purge evidence.

### Master-data ownership

The credit assessment is controlled by the configurable `CREDIT_ASSESSOR` business authority
defined in `ORA-001`, not by a permanently hard-coded application role. `SALES_MANAGER` is the
initial/default mapping for `CREDIT_ASSESSOR`, which preserves the agreed current operating
arrangement and migration compatibility. Once ORA authority assignments are active, authorized
administrators may assign, suspend, revoke or reassign `CREDIT_ASSESSOR` to an eligible employee
or position without a code change, so the application role `SALES_MANAGER` alone is not the
permanent authorization rule.

The business function PBL describes as "Pre-Sales" therefore maps to the `CREDIT_ASSESSOR`
authority rather than to a new application role. Do not add a Pre-Sales role on the strength of
this ADR. A future slice may propose a dedicated pre-sales module, workflow and role when
multi-source Lead ingestion and pre-sales vetting enter scope; that would require its own approved
role, permission, contract and migration impact decision.

The onboarding ownership model is:

```text
Sales (SALES_USER / SALES_MANAGER)   initiates the Account / Qualified Prospect and may
                                     prepare a credit proposal
SurePass                             validates legal identity
CREDIT_ASSESSOR authority            performs the credit assessment
                                     (initial/default mapping: SALES_MANAGER)
CREDIT_APPROVER authority            approves credit limit / credit days under configurable
                                     authority; currently the applicable Department Head or
                                     Managing Director
Accounts / Finance                   consumes the validated legal master and the
                                     financial/exposure information, without a redundant
                                     PAN/GST approval step
```

Preparing a proposal is not the same as performing the formal credit assessment. Account /
Qualified Prospect initiation and proposal preparation remain available to the existing authorized
Sales roles (`SALES_USER`, `SALES_MANAGER`, and `ADMIN` where the Account contract permits it).

Business authority is never granted merely because a user is an administrator. Administrative
maintenance of authority assignments and exercising `CREDIT_ASSESSOR` are separate capabilities;
the documented migration approach preserves existing prototype compatibility without making
`ADMIN` a permanent implicit assessor.

Accounts is the default owner of the identity-verification exception queue; authorized Sales
personnel may also be assigned. Queue ownership is configurable by authorized personnel.

The CRM Account Master's legal-entity/PAN-level credit profile is authoritative for approved
Credit Amount and Credit Days, resolving System-of-Record Matrix decision D-01. Sales may prepare
a proposal; an authenticated holder of a current, active `CREDIT_ASSESSOR` assignment for the
relevant organizational/data scope performs the assessment. The configured Department Head or
Managing Director decides while authenticated under `CREDIT_APPROVER`; the Account Credit Profile
service activates the approved values from that valid decision. Sales cannot assert another
person's approval. Eligible assessors and approvers, named assignments, delegated-authority
thresholds and any future maker/checker rule are policy configuration rather than workflow
constants.

Approval evidence records authenticated approver identity, role/authority at the time, decision,
timestamp, reference and conditions. Passwords, authentication secrets and reusable credentials
must never be stored as approval evidence.

Reason:
- PBL already uses SurePass, so the validation capability exists and does not need to be procured or prototyped.
- The ERP Functional Requirements Specification already mandates SurePass validation of PAN, GSTN and bank-account ownership for vendor onboarding, and Aadhaar/PAN/bank validation for employee onboarding. Applying the same pattern to customer Account onboarding is consistent with an already-accepted requirement rather than a new departure.
- The superseded assumption assigned Finance an approval step over a fact Finance would not independently re-derive, which is exactly the pattern ADR-014 identifies as unnecessary human workflow.
- Attributing the credit assessment to Finance because it concerns credit misstates the current PBL process, in which the `CREDIT_ASSESSOR` authority performs the assessment and the configured Department Head or Managing Director provides the applicable business approval under `CREDIT_APPROVER`.

Implication:
- Update or reconcile any current record that implies "Accounts/Finance confirms PAN/GST and approves Account creation".
- The following existing decisions are explicitly preserved and unchanged by this ADR: the UI term `Account` and internal/domain term `business_party` (ADR-003); Qualified Prospect becomes Customer at first Work Order; Customer Master activation remains a Finance-approved step before Work Order release/posting; PAN-level credit governance; Potential Exposure and Firm Exposure remain distinct; API-first modular architecture (ADR-004, ADR-005); backend authorization is authoritative; audit and traceability requirements.
- Nothing in this ADR removes Finance's ownership of Customer Master activation, invoicing, receivables or accounting controls. It removes only the redundant PAN/GST reconfirmation approval at Account onboarding.
- No application behaviour changes as a result of recording this ADR. The prototype's Slice 1I PAN/GST capture remains as built until a future slice implements the SurePass-backed flow. See `docs/agent/contracts/account-business-party-contract.md` and `docs/continuity/ACCOUNT_IDENTITY_VALIDATION_CORRECTION_2026-08-11.md`.

## ADR-016: React, Vite and React Router for the production web client

Date recorded: 12 August 2026.

Decision: Migrate the production web client from Next.js to React, Vite and React Router while
preserving FastAPI as the sole authoritative application backend.

Reason:
- The application does not currently require Next.js server-side application capabilities.
- A client-rendered React application matches the API-first boundary already established around
  FastAPI.
- The migration removes duplicate server/runtime concerns without moving business rules,
  authorization or persistence into the frontend.

Implication:
- TE-2A owns this migration and must preserve existing routes, workflows and regression coverage.
- Browser API requests continue to use relative `/api` paths through the deployment proxy.
- Detailed data-fetching and state-management libraries remain implementation decisions unless a
  later ADR makes them architectural constraints.

## ADR-017: Production modular API-first application and module-owned data

Date recorded: 12 August 2026.

Decision: Continue as a modular API-first application, decomposed into bounded business modules
and shared platform capabilities with explicit ownership, contracts and dependency direction.
Modules are initially deployed together but remain independently owned and contract-defined.

Rules:
- A module owns its authoritative tables, invariants and state transitions.
- Another module must not write those tables directly. It uses an approved service/API contract
  or reacts to an approved business event.
- Cross-module reads use an owning-module query interface, a documented read model, or an
  explicitly approved immutable identifier/reference. Ad hoc joins do not create ownership.
- Synchronous APIs/services are used when the caller needs an immediate decision. Durable events
  communicate completed facts. Background jobs execute deferred work and are not business facts.
- Module boundaries are code, data and ownership boundaries inside the application. They do not
  require each module to be deployed as a microservice.

Reason:
- This provides independent coding and review surfaces without premature distributed-system
  complexity.
- Explicit ownership prevents parallel agents from silently coupling schemas or duplicating
  business rules.

Implication:
- `docs/agent/architecture/MODULE_BOUNDARY_OWNERSHIP_MATRIX.md` is the current boundary map.
- Parallel implementation requires an approved or frozen contract and the production Definition
  of Ready.
- Only one active work package may own a shared contract, shared platform file or migration head
  at a time.

### Exception, 9 October 2026: five database rules across the Commercial Offer and Work Order tables, permanent

Approved by the project owner on 9 October 2026, in review round 3 of pull request #108 (TB-1 rows 8 and 11), as the
disposition of the five trigger rules CS-04 part 1 (HOF-2) added in migration `20260908_0049`. Recorded with the
headings ADR-030's exception process asks for. The rules are listed, with what each reads and locks, in
`docs/agent/architecture/BOUNDARY_EXCEPTION_REGISTER.md`, section 4 (D1 to D5).

- **What it covers.** Five trigger functions, each run before a write to one module's table, that read rows of the
  other module's table, locking them in three cases: `crm_work_order_line_within_offer_quantity` and
  `crm_work_order_line_from_its_offer` on `crm_work_order_line`, and `crm_work_order_not_from_change_quotation` on
  `crm_work_order` (Work Orders), reading `crm_commercial_offer_line` or `crm_commercial_offer` (Commercial Offers);
  `crm_commercial_offer_line_keeps_its_work_orders` on `crm_commercial_offer_line` and
  `crm_commercial_offer_keeps_its_work_orders_purpose` on `crm_commercial_offer` (Commercial Offers), reading
  `crm_work_order_line` or `crm_work_order` (Work Orders). Nothing else: every other cross-module access in the
  register stays a temporary exception owned by PF-1B.
- **Principle varied.** This decision's rule that cross-module reads use an owning-module query interface, a
  documented read model or an approved immutable identifier: these rules read the other module's rows in the database
  itself.
- **Reason.** The handoff contract's dated amendment of 8 October 2026, approved by the owner, requires its rules - an
  offer line's quantity goes onto Work Orders at most once in all; a Work Order line comes from its own Work Order's
  offer; no Work Order from a Change Quotation - to hold for any writer, the application or not. Only the database can
  hold a writer that does not go through the application, and the rules' row locks keep two requests at once apart.
- **Alternatives considered.** Moving the checks into the application behind a Commercial Offer interface, built by
  PF-1B, and dropping the triggers: it keeps the modules' data apart, but a writer that bypasses the application - an
  import, a repair script, a second service - would no longer be held, which the amendment rules out. Leaving the
  disposition open: rejected, because an exception needs a defined end or an approved permanence.
- **Consequences.** The two modules' schemas are coupled at the columns the rules read: a change to the offer line's
  `quantity` or `commercial_offer_id`, the offer's `offer_purpose`, or the Work Order line's `commercial_offer_line_id`,
  `work_order_id` or `quantity` must keep the rules working, and is made in a migration both modules' owners see. The
  two modules cannot be put in separate databases while the rules stand. Moving the handoff's reads behind a
  Commercial Offer interface (the register's R4) leaves the rules in place.
- **Integration and security.** No route, permission, event or data exposure is added. A write the rules refuse fails
  with PostgreSQL's `check_violation`, naming the rule; the application checks the same rules first and refuses
  plainly, so a user normally meets those refusals instead. Any other writer - an integration, a script - is refused
  the same way, which is the purpose. No business data leaves either module.
- **Owner, and permanent.** Permanent. The owner is the Commercial Offer to Work Order handoff, which the CRM lane owns
  (`AGENTS.md`, "Where two lanes meet inside one module"). The rules change only when the handoff contract's rules do,
  by a dated amendment the project owner approves; each change is made in a migration and recorded in the register's
  section 4. They are looked at again only if the amendment's rules change or the two modules are to be split into
  separate databases.

## ADR-018: Resource Availability and Assignment as a shared operational capability

Date recorded: 12 August 2026.

Decision: Resource Requirement, Resource Availability and Resource Assignment form a shared
operational capability usable by Hiring first and later by Transportation, Maintenance and other
domains. Availability and assignment remain distinct concepts even if implemented in one module
initially.

Reason:
- Owned and externally controlled equipment must enter one assignment process.
- Hiring-specific ownership would duplicate the same availability and commitment rules later.

Implication:
- Work Order supplies requirements through a contract; it does not allocate equipment directly.
- Market Hire supplies an external resource reference after procurement; assignment remains owned
  by the shared capability.
- Compliance/Eligibility supplies a decision and does not reproduce assignment state.

## ADR-019: Database-backed background job queue behind an abstraction

Date recorded: 12 August 2026.

Decision: Begin with a database-backed job queue exposed through a shared job-submission and
status interface.

Reason:
- The expected initial scale does not justify a dedicated broker.
- An abstraction preserves a later move to RabbitMQ or another broker without changing business
  modules.

Implication:
- The job capability owns scheduling, retries/back-off, idempotency, locking, failed-job handling
  and operational status.
- Business modules submit work without reading or writing queue tables.
- Business events and jobs remain separate records with separate meanings.

## ADR-020: React Native for future native mobile clients

Date recorded: 12 August 2026.

Decision: Use React Native for future iOS and Android applications. This records the vendor's
proposal accepted by PBL.

Reason:
- It reuses the React skill set while providing native mobile delivery.
- Mobile and web can consume the same authoritative FastAPI contracts.

Implication:
- Mobile clients must not implement independent authoritative business rules.
- Authentication, secure local storage, offline behavior, synchronization, push notifications and
  API-version compatibility require a mobile foundation slice before feature implementation.
- No native mobile implementation is started by this ADR.

## ADR-021: GitHub Actions as the CI/CD platform

Date recorded: 12 August 2026.

Decision: Use GitHub Actions for continuous integration and deployment automation. This records
the vendor's proposal accepted by PBL.

Reason:
- The source repository is already hosted on GitHub.
- Repository-native required checks and environment approvals provide a clear path from review to
  controlled deployment.

Implication:
- `TE-2CI` must implement backend, frontend, migration, E2E, contract-fixture and container checks
  before TE-2C can pass; it also defines protected integration, secret handling, artifact
  retention, deployment approval and rollback evidence.
- Production secrets must use GitHub environment/repository secret mechanisms or an approved
  external secret store and must never be committed.
- This ADR does not create a workflow or authorize production deployment by itself.

Reconciliation, 16 August 2026: the "repository-native required checks" named in the reason above
were not available on the repository's GitHub plan as it then stood. TE-2CI delivered and
hosted-proved the checks themselves, but required-check registration and enforced branch protection
could not be enabled. ADR-029 records the approved interim manual merge gate and the reassessment
owed before production. This ADR's choice of GitHub Actions is unchanged, and its expectation of
enforced protection is deferred rather than withdrawn.

Further reconciliation, 17 August 2026: the reassessment above has happened. The repository owner
upgraded to GitHub Pro and activated a repository ruleset that provides the "repository-native
required checks" originally anticipated by this ADR's reason. This is recorded as ADR-031, which
supersedes ADR-029 for the current enforcement mechanism. This ADR's choice of GitHub Actions
remains unchanged; its expectation of enforced protection is now met rather than deferred.

## ADR-022: Identity and Statutory Validation as a shared platform capability

Date recorded: 12 August 2026.

Decision: External identity and statutory validation is a shared provider-independent capability,
with SurePass as the current provider, rather than Account-specific integration code.

Reason:
- Account, vendor and employee onboarding require overlapping validation behavior.
- A normalized interface prevents provider payloads and retry mechanics from spreading through
  business modules.

Implication:
- The capability owns provider adapters, normalized results, retry/fallback mechanics and
  validation evidence references.
- Consuming modules own the business consequence of a result under their approved contract.
- ADR-014 and ADR-015 continue to govern authoritative values, exception ownership and outage
  behavior for Account onboarding.

## ADR-023: Settled production defaults and business-review threshold

Date recorded: 12 August 2026.

Decision: Do not ask PBL to approve ordinary production safeguards or repeat business decisions
already recorded at a higher or equal authority. Engineering may resolve those items when
the outcome is unambiguous, preserves PBL's business controls and does not create a new material
business policy. Ask PBL only where two or more reasonable choices would materially change
operations, authority, money, statutory treatment or cross-module ownership.

The following current defaults are confirmed:

- Important committed actions record the actor, time, affected record and relevant decision or
  change context.
- Retries, repeated submissions and double-clicks must not create duplicate business effects.
- Failures return a clear, non-sensitive message and a support/tracking reference where useful.
- All current sales, hiring, customer billing, vendor hire and other operating amounts use INR.
  Multi-currency is deferred until PBL serves overseas customers. Purchases of assets and spares
  are the only present exception and remain owned by their future Purchase/Finance design.
  Refined by the owner on 4 October 2026 (Q-08, TB1-600): INR remains the default and the
  operating currency; an offer or amendment may be recorded in USD, GBP or EUR when chosen, from
  one list (`backend/app/shared/currency.py`), and reports total each currency separately.
  Nothing converts; exposure and billing terms remain INR.
- Potential/Firm Exposure follows the allocation state machine in `CEX-001`. A latest submitted or
  accepted live amount remains Potential only until the corresponding selected-line amount is
  transferred by successful Work Order shell creation. Partial handoffs transfer only their
  allocated amount; unawarded amounts leave Potential and live unhanded amounts remain Potential.
  Work Order release does not transfer the same value again.
- Firm Exposure temporarily uses allocated active Work Order shell/Work Order value. The target
  basis remains unbilled effective Work Order value plus outstanding receivables from Plum.
  Decision D-02 concerns only when reliable Plum/Work Order inputs permit that target basis to be
  activated.
- Within-limit actions proceed. An over-limit or exhausted-credit Commercial Offer is held until
  an authorized exception is approved. Missing, stale or unavailable inputs are shown explicitly
  and are never silently treated as zero.

Reason:
- These safeguards are already established by current contracts, NFRs and the System-of-Record
  Matrix, or are necessary to avoid obviously incorrect duplicate or unauditable behavior.
- Repeatedly asking PBL to confirm them obscures the smaller set of decisions that genuinely need
  business judgement.
- PBL explicitly confirmed the INR rule and directed that existing decisions and common-sense
  controls be applied without unnecessary concurrence requests.

Implication:
- The PBL review guide separates settled baselines, deferred parameters and genuinely unresolved
  choices.
- `APPROVED` contracts may still contain configurable values to be set in the implementation
  slice. A missing future parameter does not reopen settled business meaning.
- High-risk calculation examples, especially billing, must still be demonstrated against real
  PBL contracts during UAT. This verifies implementation accuracy; it does not reopen the agreed
  billing methods without a specific conflict.

## ADR-024: Allocation-based Potential to Firm Exposure transfer

Date recorded: 12 August 2026.

Decision: Potential and Firm Exposure are reconciled through line/value allocations. Successful
Work Order shell creation from selected Commercial Offer lines transfers exactly that selected
amount from Potential to Firm. Offer acceptance alone does not transfer it, and later Work Order
release does not transfer it a second time.

Rules:

- Accepted/awarded value awaiting handoff remains Potential.
- Partial handoff transfers only the selected-line value. A still-live remainder remains
  Potential; an explicitly unawarded/rejected remainder leaves exposure.
- If the exact partial award is not yet recorded, retain the unallocated submitted balance in
  Potential conservatively until Sales records its outcome.
- Change/Supplementary Offer or proposed amendment increases remain Potential until applied to an
  effective Work Order version; application transfers the change amount to Firm.
- Cancellation/reversal removes the Work Order allocation from Firm and returns it to Potential
  only if the commercial commitment remains live and awaits replacement handoff.
- Every transfer/reversal records source offer/revision/line, Work Order/line, amount and event;
  the same allocation can never exist in both buckets.

Reason:
- The earlier wording excluded terminal offers but did not define `ACCEPTED`, partial awards or a
  transfer event, allowing a full offer and derived Work Order to be counted together.
- The frozen Slice 6D.1 boundary permits one accepted offer to produce multiple Work Orders, so a
  header-status-only formula is insufficient.
- Work Order shell creation already records the conversion/handoff fact and selected source-line
  identity, making it the earliest unambiguous transfer event.

Implication:
- `CEX-001` is the detailed state machine and includes partial-award/amendment examples.
- D-02 remains only the later switch from temporary allocated active Work Order value to unbilled
  effective Work Order value plus Plum receivables.
- No change is made to the frozen handoff payload or current prototype behavior by this ADR.

## ADR-025: Authority, CI, NFR and contract-freeze prerequisites

Date recorded: 12 August 2026.

Decision: Configurable approvals depend on one shared Organization Authority/Authorization model
(`ORA-001`). GitHub Actions (`TE-2CI`) precedes TE-2C completion. PF-1 then establishes shared
authorization, API/event retrofit, jobs/events, notifications, NFR evidence, dependency discovery
and initial contract fixture/freeze lanes before dependent business modules run in parallel.

Reason:
- Prototype hard-coded role tuples cannot resolve Department Head, Managing Director, Risk
  Approver, Finance Customer Master Owner, Billing Maker/Checker, Procurement or delegation.
- A verification gate cannot require CI while scheduling CI after itself.
- Approved logical contracts do not provide a compatibility boundary until producer/consumer
  fixtures and freeze evidence exist.
- The accepted ERP NFR source requires measurable performance, security, availability,
  backup/restore, retention and operational visibility evidence.

Implication:
- TE-2C is a migrated-foundation verification, not the final production-candidate product tag.
- The final production-candidate gate occurs only after applicable PF-1/business waves, frozen
  runtime contracts, NFR evidence and production operating parameters are ready.
- Existing APIs/events are explicitly inventoried and retrofitted under PF-1B/per-module packages;
  they are not permanent exceptions to MCF-001.
- External master/provider readiness is tracked in `EXTERNAL_DEPENDENCY_REGISTER.md`.

## ADR-026: Employee Master owns organization positions used by authorization

Date recorded: 12 August 2026.

Decision: Plum HR Employee Master is authoritative for employee status, organization units,
positions/designations, reporting relationships and current incumbents. ORA owns application
permissions, data-scope and business-authority mappings against stable Employee Master references;
it does not own or maintain a second organization structure.

Employment and position changes constrain authority continuously:

- inactive/leaver changes immediately suspend authority and outgoing delegations for new actions;
- transfers, promotions, organization/scope changes and incumbent changes suspend affected
  assignments for re-evaluation against the new Employee Master position;
- pending approvals are re-resolved to a currently eligible authority;
- historical decisions retain their decision-time authority snapshot; and
- correction/reactivation requires a current authorized review and never backdates authority
  across a suspended period.

Reason:
- Giving both Employee Master and ORA ownership of positions would create competing organization
  structures and permit transferred/departed employees to retain stale approval authority.
- Authorization lifecycle is at least as important as statutory eligibility lifecycle and must
  react to authoritative master changes rather than rely on an administrator remembering.

Implication:
- The Plum HR employee/organization/position snapshot, change feed and recovery/import fallback
  are a critical-path external dependency for PF-1A activation and ORA freeze.
- ORA stores only the minimum versioned reference/snapshot required for authorization and audit.
- New authority-dependent decisions fail closed when HR source data exceeds the configured
  staleness limit; a controlled versioned import is the fallback, not manual CRM org maintenance.
- `RMR-001`, `ORA-001` and their fixtures cover joiner, transfer/promotion, leaver, correction,
  stale-feed and recovery cases.

## ADR-027: Mandatory review schedule for submitted offers without expiry

Date recorded: 12 August 2026.

Decision: A controlled Commercial Offer/tender submission must have either an explicit
`valid_until` date or a mandatory system-calculated `next_exposure_review_due_at`. The latter uses
a configured maximum review interval and cannot be bypassed by leaving `valid_until` blank.

At the review date, Sales confirms the commitment remains live and sets the next review date, or
records expiry, withdrawal, rejection/loss, closure or a not-awarded outcome. An overdue unresolved
amount remains Potential conservatively, but the exposure result holds new exposure-dependent
decisions for that Account and reminders escalate until the review is resolved.

Reason:
- Submitted tender bids may receive no customer response and the current prototype permits
  `valid_until = null`; without a review schedule they consume credit headroom silently forever.
- Automatically dropping an unanswered offer would understate exposure. A mandatory owned review
  resolves the stale commitment without assuming that silence means loss.

Implication:
- Commercial Offer owns the review state/outcome; Credit Exposure consumes it.
- Background Jobs and Notifications own scheduling/delivery mechanics, not the business outcome.
- Existing submitted offers are backfilled into the review queue without silently removing their
  Potential Exposure.
- The maximum review interval, reminder offsets and escalation timing are configuration set before
  the production exposure gate is enabled; their absence does not reopen the settled behavior.

## ADR-028: PostgreSQL production database baseline

Date recorded: 13 August 2026.

Decision: PostgreSQL is the frozen production database for the PBL CRM + Equipment Hiring
application. This supersedes ADR-006 for the production baseline.

PBL confirmed this choice. ADR-006 is not withdrawn: it remains accurate historical evidence of
how the prototype foundation was actually implemented on SQL Server Developer Edition, and that
record is preserved rather than rewritten.

### Selected baseline

- PostgreSQL 17, kept on its latest supported minor release.
- SQLAlchemy's `postgresql+psycopg` dialect using Psycopg 3.
- PostgreSQL is the only supported runtime once TE-2B completes. Do not maintain permanent
  SQL Server/PostgreSQL dual-dialect code, a compatibility layer, or per-dialect branches in
  migrations, repositories or services.

### Migration-chain treatment

Existing Alembic revision IDs, their `down_revision` edges and the single linear head are
preserved. Their pre-production implementation may be ported from T-SQL to PostgreSQL.

This is permitted because no production database has ever been released from the SQL Server
chain. The revisions are therefore an internal development artefact whose implementation may be
rewritten, not a compatibility boundary any deployed database depends on. Preserving the IDs and
order keeps the project's migration history, review trail and cross-references intact.

### Data treatment

- TE-2B establishes a fresh PostgreSQL schema from migrations.
- Local prototype, test and demo rows are not production data. They are recreated using the
  existing seed migrations and the TE-1 smoke-data tooling
  (`backend/tooling/smoke_data`, `scripts/smoke-data.ps1`, `scripts/vendor-demo.ps1`).
- Do not copy local SQL Server rows into PostgreSQL in TE-2B. There is no row-level migration,
  export/import or dual-write step in scope.
- Preserve the old local SQL Server Docker volume untouched as rollback/reference evidence. It is
  deliberately no longer declared in `docker-compose.yml`, which removes it from Compose's
  management so `docker compose down -v` cannot delete it.
- Any future import of real legacy or business data requires a separate mapped, reconciled and
  approved production data-migration package with its own field mapping, reconciliation evidence
  and business sign-off. TE-2B does not authorize it.

### Timestamps

Database timestamps are stored in UTC. Application and Alembic connections set the session time
zone to UTC explicitly. The existing display convention is unchanged: the UI converts business
timestamps to Asia/Kolkata for PBL users.

*Refined 11 October 2026 (entered times; an engineering decision under ADR-023, no business
meaning changed):* a date and time a person types is India's time. The page sends it as the same
moment in UTC with its zone (`frontend/src/components/enteredDateTime.ts`); the API takes a date
and time - in a request body or query - only as ISO text with its zone (or a datetime made in
code) and refuses anything else with `422`, numbers included (`backend/app/shared/zoned_datetime.py`,
`ZonedDateTime`), converting any offset to UTC; storage stays UTC. A time with no zone was the
defect: the offer page sent the India time typed with no zone, the API stored it as UTC, and the
screen showed it 5 hours 30 minutes late. The times the API sends back keep their form (the CRM
tables' times with no zone, read as UTC: TB-1 TB1-401, until CS-16). Unlike the decision itself
("Unchanged by this decision", below), **this refinement does change API contracts**: thirteen
request inputs that accepted a time with no zone, and read it as UTC, now refuse it - an
intentional tightening, recorded in `commercial-offer-contract.md`, `lead-contract.md` and
`interaction-contract.md`, whose responses now carry `contract_version` `2.0`; and a customer
response's event now gives its received time in UTC with `+00:00`. See
`docs/agent/slices/entered-times-in-india.md`.

### Unchanged by this decision

No API contract, business rule, permission rule, business event, ownership boundary or workflow
status changes as a result of this ADR. The frozen Slice 6D.1 Accepted Offer to Work Order handoff
contract and the Slice 6O.1 related-offer contract are unaffected. ADR-007 (integer identity
primary keys, UUID public IDs, visible business references) continues to hold; PostgreSQL
implements the integer identity through its own sequence-backed mechanism.

*This section is the original decision's, of 13 August 2026. The dated refinement of "Timestamps"
above (11 October 2026) is the one exception: it changes the API contracts it names, and the form
of one business event field (a customer response's received time, now always in UTC with
`+00:00`). It changes no business rule, permission rule, ownership boundary or workflow status.*

Implication:
- The database ADR that TE-2B implements is this one, not ADR-006.
- `docs/agent/technical-enablement/TE_2B_POSTGRESQL_MIGRATION.md` records the implementation.
- Documentation that describes the prototype's SQL Server history stays as written; it is
  historical record, not a live prescription.

## ADR-029: Interim manual merge gate while enforced branch protection is unavailable

Superseded by ADR-031. History only; not part of this copy.

## ADR-030: PBL platform architecture baseline and future AI-readiness scope

Date recorded: 16 August 2026.

Decision: The architectural principles governing this repository's CRM + Equipment Hiring
implementation are **PBL platform-level architectural principles**, not conventions scoped only to
CRM/Hiring. CRM + Equipment Hiring are the first substantial implementations of a broader PBL
application-platform direction. This ADR records that scope explicitly and distinguishes enduring
platform principles from the current PBL reference implementation stack, so that no future module
is designed as if this repository's architecture applied only to itself.

Full explanation, the six extensibility characteristics, the additional platform principles and the
future-AI governance rules are in
`docs/agent/architecture/PBL_PLATFORM_ARCHITECTURE_AND_FUTURE_AI_READINESS.md`. This ADR is the
decision of record; that document is the fuller reference it points back to.

### Applicability

The principles apply by default to:

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

Whether a future module lives inside this repository or a separate one is a delivery decision, not
a change to which principles govern it.

### Platform principles versus reference stack

Two things must not be conflated:

- **Platform architectural principles** (enduring, framework-independent): governed
  application/domain services as the home of business logic; structured, machine-consumable
  contracts; identity, authorization, segregation of duties, correlation and audit; document
  abstraction independent of storage technology; retry-safe/idempotent write operations; durable
  processing independent of interactive sessions; API-first, contract-governed interoperability;
  and future AI/agent extensibility as a consumer of governed services, never a parallel
  implementation of business logic.
- **PBL reference implementation stack** (current preference, not a mandate): React + Vite
  (ADR-016), FastAPI (ADR-004, ADR-005), PostgreSQL (ADR-028), Redis where appropriate for
  transient/cache/coordination/streaming use, an appropriate durable/background-processing
  mechanism (ADR-019), and document storage through a repository abstraction. This is the
  preferred stack for modules PBL itself builds. A purchased specialist application, a
  Microsoft/Power Platform component, an externally supplied module, an integration service, or a
  future technology selected for a justified reason may use a different internal implementation,
  provided it conforms to the platform principles at its integration boundary — API quality,
  identity integration, authorization, auditability, System-of-Record ownership, document handling,
  integration reliability, data portability and interoperability — or carries an ADR explaining why
  it cannot. PBL does not require internal technology conformity from a third-party product it does
  not control.

### Plum coexistence during migration

Migration away from Plum is expected to be progressive, not a single replacement event. During the
transition, new PBL modules, retained Plum modules, external systems and shared services must be
able to coexist, with the boundary between Plum and new modules increasingly based on explicit
contracts/APIs rather than uncontrolled direct coupling. Where a business capability moves out of
Plum: ownership must be explicit; its authoritative System of Record must be explicit; integration
contracts with retained modules must be explicit; duplicate ownership of business rules must be
avoided; and migration must not create competing authoritative implementations. The long-term
direction favours independently replaceable modules under common platform governance over rebuilding
a new monolithic system outside Plum.

### Future AI is anticipated, not implemented

Good platform architecture makes a future AI/copilot/agent layer easier to add later, because that
layer would consume the same governed services conventional applications and integrations already
use. **AI readiness is a consequence and benefit of good platform architecture; it is not the
primary reason for the architecture and it is not part of the current implementation scope.** Two
rules govern any future AI work:

- `AI -> governed tool/application service -> authorization + business rules -> System of Record`,
  never `AI -> unrestricted database access`;
- use AI where interpretation, ambiguity, language understanding or judgement adds value; use
  deterministic software for calculations, business rules, reconciliation and repeatable
  processing.

A future AI agent is a governed execution channel acting on behalf of an authenticated user or an
explicitly authorised system process; it may acquire no more business authority than any other
caller because of the technology it is implemented with, and the transactional platform must remain
fully usable if the AI subsystem is unavailable or removed.

### Explicit non-goals of this decision

This ADR does not implement Claude, Anthropic, OpenAI, any other LLM, assistant-ui, the Vercel AI
SDK, Anthropic Code Execution, the Anthropic Files API, AI Agent Skills, Langfuse, UploadThing,
vector databases, embeddings, RAG infrastructure, autonomous agents, AI-specific queues, AI-specific
document pipelines, or any particular AI vendor or model. It does not add an AI dependency merely to
demonstrate future readiness, does not perform a broad CRM/Hiring refactor, does not begin migration
of any additional Plum module, and does not convert the current architecture into microservices
merely because future modules are anticipated. **Architecturally anticipate AI now; implement AI
only when there is a justified and separately approved business requirement.**

### Exception process

A future module may depart from the reference implementation stack, a particular infrastructure
pattern, or a particular shared service where there is a justified requirement. Material exceptions
must be recorded through an ADR identifying: the principle being varied; the reason; alternatives
considered; consequences; integration implications; security/governance implications; and whether
the exception is temporary or permanent. Platform principles are default and enforceable, but
explicitly overridable through architectural decision — never casually ignored.

Reason:
- Without an explicit platform-scope statement, a future agent could reasonably read this
  repository's architecture records as CRM/Hiring-specific and re-derive incompatible conventions
  for the next module, reproducing exactly the tightly coupled, per-module-bespoke architecture the
  modular direction (ADR-004, ADR-017) already exists to avoid.
- Recording the reference-stack/platform-principle distinction now prevents a future purchased or
  externally supplied component from being wrongly rejected — or wrongly accepted without
  boundary-level governance — for the wrong reason.
- Recording AI governance now, without building anything now, keeps the option open at negligible
  present cost while avoiding premature vendor dependency, consistent with ADR-023's principle of
  not incurring engineering cost before it is justified.

Implication:
- `docs/agent/architecture/README.md`, `docs/agent/architecture/PRODUCTION_ARCHITECTURE_DIRECTION.md`,
  `docs/agent/architecture/MODULE_BOUNDARY_OWNERSHIP_MATRIX.md` and `docs/agent/PROJECT_OVERVIEW.md`
  are updated to state or cross-reference this platform scope.
- A structured review of the current CRM/Hiring implementation against these principles is recorded
  in `docs/agent/architecture/PLATFORM_PRINCIPLES_IMPLEMENTATION_REVIEW.md`. One pre-existing gap
  between documentation and code was found — `leads/service.py` and `opportunities/service.py`
  import another module's repository layer directly, contradicting
  `PRODUCTION_ARCHITECTURE_DIRECTION.md`'s dependency rule 4 — and is recorded as follow-up work for
  the already-planned PF-1B API/event retrofit rather than refactored by this documentation change.
- No application code, API contract, database schema, migration, permission rule, business event or
  AI dependency is introduced by this ADR.

## ADR-031: Repository-enforced protected integration gate

Date recorded: 17 August 2026.

Decision: The repository now uses a technically enforced GitHub ruleset on the default branch. A
pull request is required for changes to `main`, and `Required validation` is a required GitHub
Actions status check that GitHub requires to have reported on the exact commit before merge is
allowed — accepting, per GitHub's own required-status-check semantics, `success`, `skipped` or
`neutral` alike as a GitHub-successful conclusion. PBL's own, stronger invariant is that
`Required validation` must conclude `success` specifically; that stronger invariant is met by the
workflow's own design, not by GitHub ruleset semantics alone (see "Required check semantics"
below). Branch currency (the PR must be up to date with `main`) is technically enforced. Force-push
and branch-deletion protection are technically enforced. Once a pull request is merged, only the
merge-commit method is allowed (squash and rebase are disabled). No bypass actor currently exists.
Required review conversations must be resolved before merge. This record does not claim that the
ruleset makes every possible direct or PR-associated update to `main` technically impossible, and
does not claim that GitHub's own required-status-check semantics by themselves treat a *skipped*
check as blocking — see "Required check semantics" and "Direct push semantics" below for the exact
boundary of what is GitHub-enforced versus what remains workflow design or PBL process policy.

### Verified configuration

Recorded here as the decision's factual basis, evidenced through the GitHub API on 17 August 2026
for repository `<PBL's internal repository>`:

```text
Ruleset name:            main
Ruleset id:               20939060
Target:                   branch, ~DEFAULT_BRANCH
Source:                   repository
Enforcement:              active
Bypass actors:            none (the current repository owner cannot bypass the ruleset)

Effective rules:
1. Deletion blocked.
2. Non-fast-forward updates / force pushes blocked.
3. Pull request required:
   - required GitHub approvals: 0
   - stale-review dismissal: false
   - Code Owner review: false
   - most-recent-push approval: false
   - unresolved review conversations must be resolved
   - allowed merge method: merge commit only (squash and rebase not allowed)
4. Required status checks:
   - strict/up-to-date policy: true
   - status checks enforced on creation
   - required context exactly: Required validation
   - integration: GitHub Actions (integration id 15368)
```

The workflow already defines the aggregate job as `Required validation`; this ADR records that the
ruleset now enforces that existing check. It does not edit
`.github/workflows/te-2ci-validation.yml`.

### Required check semantics

Two layers apply here and must not be conflated:

- **What GitHub itself requires and accepts.** GitHub's required-status-check enforcement requires
  the named `Required validation` check to have reported on the relevant/latest commit before merge
  is allowed, and — per GitHub's own required-status-check semantics — treats `success`, `skipped`
  and `neutral` alike as a GitHub-successful conclusion. A **missing** report (the check never ran
  or never reported at all) still blocks merge, because no report exists to satisfy the requirement.
  GitHub's own semantics do **not** by themselves guarantee that a reported `skipped` or `neutral`
  conclusion is treated as blocking.
- **What PBL requires, and how it is met.** PBL's own, stronger invariant is that `Required
  validation` must conclude `success` specifically — `skipped` or `neutral` must not pass. This
  invariant is met today by a workflow-level mitigation, not by GitHub ruleset semantics alone: the
  aggregate `required-validation` job in `.github/workflows/te-2ci-validation.yml` carries
  `if: always()`, inspects every dependency job's result, and fails unless every dependency reports
  exactly `success`. Under the current workflow, a failed, cancelled or skipped dependency therefore
  makes the *aggregate job itself* conclude `failure` (never `skipped`), which GitHub's
  required-status-check rule then blocks on because the required check did not report `success`. A
  **missing** required check (for example, if the job were renamed without updating the ruleset)
  remains blocking under GitHub's own rule regardless of workflow design.

This ADR does not claim the ruleset itself treats a skipped or neutral required check as failure;
it records that the existing workflow design converts every non-success dependency outcome into an
aggregate `failure`, which the ruleset then enforces because `failure` is not a GitHub-successful
conclusion. **Any future workflow change capable of making the aggregate `required-validation` job
itself conclude `skipped` or `neutral` (rather than `failure`) would be accepted by GitHub's own
semantics and would silently weaken PBL's stronger invariant; it requires explicit review and
reconciliation of this ADR before it is made.**

### Reconciliation, 9 September 2026: what `Required validation` covers was narrowed

This is the explicit review the paragraph above requires, performed before the change was made
rather than discovered afterwards. **The mechanism is unchanged and PBL's stronger invariant is
intact**: the aggregate `required-validation` job still carries `if: always()`, still fails unless
every dependency reports exactly `success`, still concludes `failure` rather than `skipped`, and
still bears the name `Required validation` that the ruleset matches on. Nothing here touches the
semantics that section describes.

What changed is *coverage*. The six DEV-ORCH core-test partitions were removed from
`required-validation.needs` and moved into `.github/workflows/devorch-validation.yml`, which runs
them only when DEV-ORCH's own files change (`tools/devorch/**`, `scripts/devorch-*.ps1`,
`scripts/tests/devorch-*.ps1`, that workflow file, plus `workflow_dispatch`). `Required validation`
now aggregates six jobs rather than twelve: backend regression, empty-database migrations, the
frontend gate, contract fixtures, secret/dependency checks, and Compose build/health/E2E.

**Reason, measured.** On run `34332499983` the six DEV-ORCH jobs accounted for 66 of the 79
billable minutes that validation run cost - 84% - because they are `windows-latest`, which GitHub
bills at a 2x multiplier with per-job rounding up to the whole minute. At roughly 40 runs per week
that one item consumed most of a month's included minutes on a private repository, and it did so on
every change regardless of what the change touched. DEV-ORCH is separately suspended rather than
under active development (`docs/continuity/PF_1A_E3_INTEGRATION_CLOSURE_AND_WAY_FORWARD_2026-09-07.md`),
so the routine re-run was defending against a change that, by decision, is not being made.

**The residual risk, stated rather than minimised.** A change to DEV-ORCH can now reach `main`
without its test suite having been a *required* status check. This is a genuine reduction in
technical enforcement for that one area, and must not be described as equivalent to the previous
arrangement. It was unavoidable in this form: a required check that carries a `paths:` filter
simply never reports on a pull request that does not match, and a missing required check blocks
merge outright - so the suite could not be both path-triggered and required without blocking every
CRM change. Three things carry the residual:

- the path trigger fires on any change to the files the suite covers, so the suite still runs and
  still reports on exactly the changes that could break it;
- `tools/devorch/tests/15-TestPartitions.Tests.ps1` now asserts that the trigger actually covers
  `tools/devorch/**`, because a mistyped filter would leave the suite silently never running and an
  absent suite is indistinguishable from a passing one. That guard was proven by breaking the
  filter and watching it fail before restoring it;
- the project owner's explicit pre-merge confirmation, which this ADR already records as the human
  integration authority given GitHub's required-approvals count of `0`.

No ruleset change accompanies this. The required context remains exactly `Required validation`, and
`devorch-validation.yml` is deliberately not registered as a second required check, for the
path-filter reason above.

### Direct push semantics

PBL process policy prohibits direct/local pushes to `main`; changes must go through the controlled
branch-and-pull-request path, except for a documented emergency exception approved by the project
owner. GitHub technically enforces that a ref update on `main` be associated with a pull request
(the ruleset's "pull request required" rule, verified above) together with the other configured
rules. The verified ruleset does **not** include a separate "restrict updates" rule. This ADR
therefore does not claim the ruleset makes every possible pull-request-associated or direct update
to `main` technically impossible — only that the specific rules verified above (pull request
required, `Required validation` required, branch currency, no force push, no deletion, resolved
conversations) are enforced. Force pushes specifically remain a distinct, verified, technically
enforced rule (non-fast-forward updates are blocked), independent of the pull-request-association
point above.

### Relationship to ADR-029

ADR-029 is **not** deleted or withdrawn. It remains the accurate historical record of the interim
manual control that applied while required-status-check registration and enforced branch
protection were unavailable on the repository's prior GitHub plan, and the TE-2CI hosted evidence
recorded under it stays historically accurate exactly as written. **ADR-031 supersedes ADR-029
only for the current enforcement mechanism.** Any statement written as *current* guidance about how
integration into `main` is controlled must now follow ADR-031, not the ADR-029 manual gate
description. A document that narrates what happened on or before 16 August 2026 — hosted run
evidence, acceptance records, continuity notes — is not rewritten merely because the mechanism has
since changed; it may carry a short, clearly dated cross-reference to this ADR instead.

### Relationship to ADR-021

GitHub Actions remains the CI/CD platform selected by ADR-021. The validation workflow
(`.github/workflows/te-2ci-validation.yml`) and its stable required-check name
(`Required validation`) are unchanged. ADR-031 closes the enforcement gap ADR-021 anticipated and
ADR-029 recorded as temporarily unavailable; it does not redesign CI, add a job, or change what the
check validates.

### Project-owner authority

Explicit project-owner approval before merge remains a PBL process requirement, unchanged by this
ADR. Be precise about what is and is not technically enforced: GitHub technically enforces the
rules listed above — pull request required, up-to-date branch, `Required validation`, no force
push/deletion, merge-commit-only merge method, resolved conversations. Required GitHub approvals
are configured at `0`, so GitHub does not itself require a second person's approving review. The
project owner's explicit integration confirmation described in
`docs/agent/architecture/INDEPENDENT_IMPLEMENTATION_REVIEW_WORKFLOW.md` is therefore a
process/governance control layered on top of the technically enforced rules above, not a further
GitHub-enforced approving-review requirement. Do not describe GitHub as technically enforcing the
project owner's approval; describe it as technically enforcing the rules actually configured, with
the project owner's approval remaining the recorded human integration authority.

### Relationship to ADR-030

The specific GitHub Pro plan, this ruleset (id `20939060`) and this exact CI implementation are a
repository-level implementation choice, not a new PBL platform technology mandate. Do not read this
ADR as requiring every future PBL module or repository to use GitHub Pro, this ruleset
configuration, or GitHub Actions specifically. The enduring platform principle, consistent with
ADR-030 and `docs/agent/architecture/PBL_PLATFORM_ARCHITECTURE_AND_FUTURE_AI_READINESS.md`, is
**governed, validated, non-bypassable integration with auditable controls** — a mandatory,
independently-run validation gate designed so it cannot be silently skipped (in this repository,
through the combination of the ruleset's required-status-check rule and the workflow's own
`if: always()` aggregate design, not the ruleset alone — see the "Required check semantics" note in
`docs/agent/architecture/INDEPENDENT_IMPLEMENTATION_REVIEW_WORKFLOW.md`), on a branch that is
technically protected against force pushes and deletion. A future PBL module or repository may
implement that
platform principle with a different platform, plan or ruleset mechanism, consistent with ADR-030's
exception process, without requiring a new ADR merely to select different but equivalent tooling.

### Scope

This is a documentation/governance reconciliation only. It changes no business behavior, API,
database schema, migration, permission rule, business event, frontend screen, CI workflow file or
runtime configuration. The "Verified configuration" section above is a configuration inspection
through the GitHub API, not end-to-end behavioral proof that the protected integration path
rejects a non-compliant pull request or push in practice; that behavioral verification remains
TE-2C's to perform. No TE package's completion pointer changes: TE-2CI remains complete under its
historical acceptance basis; TE-2C remains the next technical-enablement package, unblocked but not
started, and this ADR does not by itself satisfy TE-2C's own Definition of Done — TE-2C must still
perform and record its own end-to-end behavioral verification against the now-active ruleset.

Reason:
- The repository owner upgraded to GitHub Pro and activated a repository ruleset, removing the
  plan limitation ADR-029 recorded and closing the gap between the intended control (ADR-021's
  "repository-native required checks") and what the platform could previously enforce.
- Leaving ADR-029 as the only current description of the integration gate after this change would
  misstate the repository's actual control state in the opposite direction from the error ADR-029
  itself was written to avoid: understating a real control instead of overstating one.
- Recording the verified ruleset configuration as decision-of-record evidence, rather than only as
  a chat claim, keeps this ADR auditable the same way TE-2CI.2's hosted evidence was recorded.

Implication:
- Every active/current-guidance reference to the ADR-029 manual gate as the mechanism presently in
  force is reconciled to point to ADR-031 in this documentation package; see the affected files
  listed in the corresponding continuity/handoff record for this package.
- `docs/agent/architecture/PRODUCTION_READINESS_GATES.md`'s TE-2C Definition of Done item about
  required checks being "required for protected integration" is now genuinely satisfiable and is
  reconciled to say so, without marking TE-2C complete.
- No application code, API contract, database schema, migration, permission rule, business event,
  frontend screen, CI workflow or Docker/Compose file is changed by this ADR.

## ADR-032: HR reference source decision - the structures Plum does not hold, and a SharePoint-backed interim canonical reference

Date recorded: 31 August 2026, amended 31 August 2026 under PF-1F-HR-E1 Correction 1 (C1-1:
canonical/source-binding boundary architecture and explicit ADR-026/`RMR-001` refinement wording
added; C1-3: effective-dating claims narrowed; C1-7: unverified Plum raw-field capabilities
reclassified), Correction 2 (C2-1: effective-dated version records given explicit per-version
identifiers and business-effective/recorded/superseded-time semantics, with a corresponding
seven-List SharePoint shape; C2-3: further current normative documents reconciled, including
provider-neutral NFR staleness wording and a short cross-reference appended to `ORA-001`) and
Correction 4 (C4-1: removed residual current-normative wording that read as Plum itself being
authoritative for structured organization/position facts, replacing it with the explicit
business-source-fact-versus-canonical-structured-reference-capability distinction; C4-3: Q-09
(Employee ID reliability) and Q-10 (authority-administration bootstrap) explicitly separated so
Q-09 is never described as a business decision). Package: PF-1F-HR-E1 (documentation/architecture
only; no runtime change).

Decision: PBL confirms that Plum does not currently provide the structured Organisation Unit
Master, Position Master, Position Incumbency or effective-dated HR change-feed model that parts of
the PF-1A Organization Authority design assumed. PBL further flags that a stable, immutable
Employee ID in Plum is unverified and should be treated as likely absent rather than assumed to
exist. Rather than waiting for Plum to build that structure, PBL approves governed SharePoint Lists
as the fast **interim** authoritative source for the structured Employee / Organisation Unit /
Position / Position Incumbency reference data Plum does not provide, alongside continued
consumption of whatever flat/basic HR facts Plum can reliably supply. The platform introduces its
own stable canonical identifiers (`person_id`, `org_unit_id`, `position_id`, `incumbency_id`)
immediately; these are never SharePoint List Item IDs, Plum field values or employee names.

This decision does not change `RMR-001` or `ORA-001`'s substantive authorization/eligibility
semantics. It changes **which system currently supplies** the structured reference data those
contracts describe, and records that Plum's absence of that structure is a confirmed current fact,
not an unconfirmed gap requiring further discovery before PF-1A can be scoped. See
`docs/agent/pf-1f-hr/` for the full canonical model, SharePoint starter specification, Plum
field-level gap analysis and decision gate produced under this ADR.

### Confirmed current Plum limitations

```text
1. No structured Organisation Unit hierarchy/master of the sophistication the target authority
   model assumed.
2. No true Position Master with stable position identities (as distinct from designation labels).
3. No Position Incumbency / effective-dated position occupancy record.
4. No effective-dated HR change-feed model covering joiner / transfer / promotion / scope-change /
   leaver / correction.
5. Stable immutable Employee ID: UNKNOWN / LIKELY ABSENT until verified. Plum may practically
   identify employees by name today.
```

These are recorded as confirmed facts for this programme, not items to re-ask Plum to confirm.
The remaining Plum-facing question is narrower: what flat/basic HR fields does Plum actually
contain, in what form, with what identifier and freshness quality (see
`docs/agent/pf-1f-hr/PF_1F_HR_PLUM_GAP_ANALYSIS_PACKET.md`).

### Canonical identity rule

The platform, not Plum and not SharePoint, owns canonical identity. `person_id` is an immutable
platform-assigned identifier (UUID/GUID), never an employee name and never a SharePoint Item ID.
Where Plum has no stable Employee ID, name-assisted matching may support initial reconciliation,
but must never silently become canonical identity on an ambiguous or duplicate match; such cases
are recorded as `AMBIGUOUS` or `UNMATCHED` and routed to a human reconciliation step. See
`docs/agent/pf-1f-hr/PF_1F_HR_CANONICAL_REFERENCE_MODEL.md`.

### Boundary architecture: canonical contract versus adapter-owned source binding (Correction 1)

**Correction, recorded during independent review (PF-1F-HR-E1 Correction 1).** The initial
version of this ADR's supporting documentation put provider-specific reconciliation fields
(`source_system`, `source_record_key`, `source_employee_name`, and equivalents for department/
designation/reporting-manager free text) directly on the canonical, consumer-facing Employee/
Organisation Unit/Position records, and attributed Phase-1 Plum/SharePoint comparison to PF-1A.
Both are corrected. The architecture is, and must remain:

```text
CRM / Hiring / ORA / PF-1A
        |
        v
PROVIDER-NEUTRAL CANONICAL HR CONTRACT        (consumer-facing DTOs/events only)
        |
        v
HR-reference adapter / composition / reconciliation layer   (owns source bindings, comparison,
        |                                                     canonical-event derivation)
   +----+----------------+
   |                     |
Plum/basic source    SharePoint/interim
   |                     |
   +----------+----------+
              |
        canonical output
```

Provider-specific information (source system, provider record keys, raw employee/department/
designation/manager text, SharePoint list/item metadata, Plum field/table/screen names) is owned
exclusively by the adapter/composition layer's source-binding model and is never part of the
normal consumer-facing canonical Employee/Organisation Unit/Position objects. **PF-1A never
compares Plum and SharePoint itself, never reads a source-binding record, and never receives a raw
provider field.** It consumes only canonical reference records and canonical HR change events; the
comparison/derivation that produces those events in Phase 1 is HR-reference adapter/composition
work. See `docs/agent/pf-1f-hr/PF_1F_HR_CANONICAL_REFERENCE_MODEL.md` sections A-F (canonical),
section G (source binding, adapter-owned) and section H (the consumer-facing adapter contract) for
the full, corrected model. The same document also narrows an over-claim in the original text: only
the specific effective-dated records it names (Employment Status History, Organisation Unit
Version, Position Version, Position Incumbency) support point-in-time historical reconstruction;
current descriptive fields such as name or code do not.

### Provider progression and ownership

```text
PHASE 1 (current)  SharePoint-backed interim structured reference + Plum raw/basic fields
PHASE 2            NEW_SHARED_PLATFORM HR / Organisation Reference Master becomes the canonical
                    structured reference capability
PHASE 3            Plum synchronizes/feeds applicable raw HR data into that shared master
```

Eventual production ownership of the canonical structured HR reference capability is
**NEW_SHARED_PLATFORM** (a future HR / Organisation Reference Master), consistent with ADR-030's
platform-capability direction. SharePoint is an interim provider/source, not the permanent
architectural owner. This decision does **not** authorize a CRM-owned or Hiring-owned Employee,
Organisation or Position master; `RMR-001`'s existing prohibition on competing masters is
unchanged. CRM/Hiring and PF-1A consume the structured reference data only through a
provider-neutral adapter/contract that never leaks SharePoint List Item IDs, SharePoint column
names, Plum field names, employee names as identity, or other implementation-specific provider
detail across the boundary.

### PF-1A unblocking rule

`ORA-001`'s existing statement that "PF-1A cannot pass or freeze ORA until the Plum HR
organization/position/status interface or its controlled versioned-import fallback and
change/recovery behavior are validated" already contemplated a controlled versioned-import
fallback; this ADR names that fallback concretely as the Phase 1 SharePoint-backed interim source
and removes any reading that PF-1A must wait for Plum itself to build the missing structures.
PF-1A may proceed once: the canonical HR reference contract is accepted; stable canonical IDs
exist; representative SharePoint-backed reference fixtures exist; the provider-neutral adapter
boundary is defined; source-unavailable/staleness behavior is defined; and no CRM/Hiring-owned
duplicate HR master is created. See
`docs/agent/pf-1f-hr/PF_1F_HR_DECISION_GATE.md` for the full gate.

### Relationship to ADR-026 and `RMR-001` (explicit refinement)

**This ADR explicitly refines/supersedes the product-specific source wording in ADR-026,
`RMR-001` and current architecture documents wherever that wording currently implies Plum itself
holds a structured Organisation Unit Master, Position Master, Position Incumbency record, or a
sophisticated HR change feed.** It does not reverse or supersede the underlying *ownership*
principle those records establish: Employee Master (as a logical capability) remains the
authoritative concept for employee/organization/position facts, ORA still consumes only that
capability's output, and CRM/Hiring still may not create a competing, uncontrolled Employee/
Organisation/Position master. What this ADR corrects is narrower and purely factual: which
physical system currently implements that logical capability's structured data (Plum does not,
today; SharePoint is the accepted interim implementation; `NEW_SHARED_PLATFORM` is the eventual
one) is now explicit, so a future PF-1A implementer cannot reasonably read ADR-026/`RMR-001` as
requiring consumption of a live, sophisticated Plum Organisation Unit/Position Master that PBL has
confirmed does not exist. `docs/agent/architecture/MODULE_BOUNDARY_OWNERSHIP_MATRIX.md`,
`docs/agent/architecture/PBL_BUSINESS_REVIEW_GUIDE.md` and other current normative documents
naming Plum as the org/position source carry a short cross-reference to this ADR for exactly this
reason; genuinely historical, dated evidence elsewhere in the repository is not rewritten.

### Standing external-dependency validation method

The same failure mode this ADR corrects - assuming an external system's mere existence proves it
contains the structure, identifiers, effective-dating and interface semantics a new capability
needs - is not unique to Plum HR. PF-1F-HR-E1 therefore also adopts a standing, reusable
external-dependency validation method (required canonical need -> authoritative owner -> actual
source capability -> field/interface gap -> controlled interim provider where appropriate ->
eventual authority -> provider-neutral contract -> reconciliation/freshness/security ->
blocking/non-blocking decision), recorded in
`docs/agent/architecture/EXTERNAL_DEPENDENCY_SOURCE_GAP_VALIDATION_METHOD.md` for reuse against
Equipment, Vendor, Customer, Finance, document, notification and telematics dependencies. Adopting
the method here does not itself validate or implement any of those other dependencies.

Reason:
- PBL has confirmed directly which structures Plum does not hold; asking again would repeat work
  already done.
- ADR-014's principle (automate deterministic validation, reserve human/manual routes for
  exceptions) extends naturally to sourcing: where the intended authoritative system cannot
  currently supply structured data, a governed, provider-neutral interim source is preferable to
  either inventing a duplicate CRM/Hiring master or stalling PF-1A indefinitely.
- ADR-026 already established Employee Master, as a logical capability, as authoritative for
  employee/organization/position facts; this ADR does not reverse that ownership decision. It
  corrects a narrower, purely factual point ADR-026's product-specific wording did not yet
  distinguish: Plum is a genuine **business source** of the *basic* employee facts it actually
  maintains (subject to validation), but it is not itself the **canonical structured reference
  capability** for Organisation Unit, Position or Position Incumbency data, because PBL has
  confirmed Plum does not contain that structure. This ADR records which system currently
  implements the canonical structured reference capability behind that ownership claim (governed
  SharePoint Lists, Phase 1) and how the gap is bridged until `NEW_SHARED_PLATFORM` (or a
  synchronized Plum feed into it) can supply it directly.
- SharePoint is already a PBL-approved tool (see the existing SharePoint document-repository
  direction in `EXTERNAL_DEPENDENCY_REGISTER.md`), so using governed Lists as a fast interim
  structured-data source avoids introducing a new unapproved product merely to unblock PF-1A.

Implication:
- `docs/agent/architecture/EXTERNAL_DEPENDENCY_REGISTER.md` and
  `docs/agent/architecture/MODULE_DEPENDENCY_AND_DELIVERY_WAVES.md` are reconciled to describe the
  PF-1F-HR gate in terms of the accepted canonical contract and interim SharePoint source rather
  than a live sophisticated Plum interface; see the affected-files list in
  `docs/agent/pf-1f-hr/PF_1F_HR_DECISION_GATE.md`.
- `RMR-001` and `ORA-001` are not rewritten by this ADR. Their contract registry entries carry a
  short cross-reference to this ADR and to `docs/agent/pf-1f-hr/`; their substantive authorization
  and eligibility semantics are unchanged.
- No CRM-owned or Hiring-owned Employee/Organisation/Position master is created. No database
  migration, API route, business event or runtime authorization behavior changes as a result of
  this ADR.
- Two items are recorded in `docs/continuity/OPEN_QUESTIONS.md`, and they are **not the same kind
  of item** (corrected, PF-1F-HR-E1 Correction 4, C4-3): stable Employee ID reliability in Plum
  (Q-09) is a non-blocking **source-capability/reconciliation** question - useful for future Plum
  synchronization quality, `UNKNOWN`/`LIKELY ABSENT` until verified, and not itself a missing PBL
  business definition; it does not gate either PF-1A readiness state. The bootstrap question of who
  is first assigned the protected `AUTHORITY_CONFIGURATION_ADMIN` meta-authority (Q-10, ADR-033) is
  the genuine remaining PBL **governance/business decision**, required only before production
  authority administration/activation and not a blocker to PF-1A design/implementation or
  unrelated CRM/Hiring work. Do not describe Q-09 as a business decision or as equivalent to Q-10.

## ADR-033: Parameter-driven Organization Authority configuration model

Date recorded: 31 August 2026, amended 31 August 2026 under PF-1F-HR-E1 Correction 1 (C1-2:
self-escalation prevention corrected from an audit-only control to a preventive invariant),
Correction 2 (C2-2: the preventive invariant and version/publication history made structurally
uniform across all four configurable concepts through one Configuration Change/Publication record,
and protected-meta-authority classification made an explicit data field rather than an
implicit string check) and Correction 3 (C3-2: risk classification made system-derived and
recomputed atomically at activation rather than trusted from proposal time; C3-3: decision evidence
extended to all four object/version pairs, with publication immutability stated explicitly).
Package: PF-1F-HR-E1 (documentation/architecture only; no runtime change).

Decision: The Organization Authority / Authorization capability (`ORA-001`) must be
**configuration/parameter-driven**. Approval and business workflow code must request a named
**business authority/capability** (an `authority_code`, for example `COMMERCIAL_DISCOUNT_APPROVAL`
or `CREDIT_ASSESSMENT`) plus the relevant transaction facts (amount, scope, company/branch,
customer/project/site, other policy dimensions). It must never hard-code an organisational role
name, job title, database role value, employee name, or a specific approver position (for example
"Finance Head" or "Regional Manager") as the thing being checked. The authority-resolution layer,
not the calling workflow, resolves who currently holds that authority under the active, versioned
configuration.

This ADR formalizes and generalizes a pattern `ORA-001` already partially uses (the
`CREDIT_ASSESSOR` / `CREDIT_APPROVER` resolution rule, amended 13 August 2026): named roles and
authorities are configuration data with an initial/default mapping, not permanent hard-coded role
checks. ADR-033 makes that pattern the general rule for every business authority the platform
resolves, not only credit assessment/approval, and adds the configuration-model, versioning,
parameter-file representation and protected-administration detail `ORA-001` did not fully spell
out.

### Four configurable concepts, governed by one Configuration Change/Publication record (corrected, C2-2)

```text
1. Role Catalogue            admin-configurable named roles (role_id, role_version, role_code,
                              role_name, description, active_flag, effective_from, effective_to)
2. Authority Catalogue       admin-configurable business authorities/capabilities identified by
                              authority_code (authority_id, authority_version, authority_code,
                              authority_name, description, active_flag, is_protected_meta_authority,
                              effective_from, effective_to)
3. Role -> Authority rules   which role carries which authority, for what scope_type/scope_id,
                              with what limit/threshold/condition parameters, effective-dated and
                              versioned (rule_version)
4. Person/Position -> Role   assignment of a role to a person or a position (exactly one of
   assignment                person_id / position_id, per the assignment schema), with scope,
                              effective dates and assignment_version
```

**Correction (C2-2).** The initial version of this ADR versioned only concepts 3 and 4
(`rule_version` / `assignment_version`) and gave the preventive self-escalation fields
(`activation_status`/`initiated_by`/`authorized_by`) only to those same two concepts, leaving the
Role Catalogue and Authority Catalogue themselves without durable version/publication history or
preventive control - an administrator could create or edit a Role or an Authority, including one
later flagged as protecting configuration itself, with no independent-authorization gate at all.
This is corrected: all four concepts are now versioned (`role_version`, `authority_version`,
`rule_version`, `assignment_version`), and proposal/authorization/activation for all four is
governed by one common, provider-neutral Configuration Change/Publication record rather than by
inconsistent per-table fields. See
`docs/agent/pf-1f-hr/PF_1A_AUTHORITY_CONFIGURATION_MODEL.md` section 5 for the full record shape.

Illustrative role/authority names appearing anywhere in this ADR or in
`docs/agent/pf-1f-hr/PF_1A_AUTHORITY_CONFIGURATION_MODEL.md` (for example `Credit Assessor`,
`COMMERCIAL_DISCOUNT_APPROVAL`) are examples of the kind of configuration data the model holds.
They are illustrative, not a frozen catalogue, and must never be compiled into workflow/application
code as literal constants standing in for the authority-resolution call.

### Protected administration (meta-authority)

Roles, authorities, role-authority rules and person/position-role assignments are maintained only
by an administrator holding an authority flagged `is_protected_meta_authority = true` (the working
example is `AUTHORITY_CONFIGURATION_ADMIN`), not by an implicit "is admin" UI flag that bypasses
the authority model. **`is_protected_meta_authority` is an explicit, data-driven classification
field on the Authority Catalogue row (corrected, C2-2), never a hard-coded comparison against the
literal string `AUTHORITY_CONFIGURATION_ADMIN` in application/workflow code** - other authorities
may later be flagged the same way, purely through configuration data, without a code change.
Administering authority configuration and exercising a business authority remain separate
capabilities, consistent with the existing `ORA-001` principle that `ADMIN` is never an implicit
`CREDIT_ASSESSOR`.

**Self-escalation prevention is a preventive design invariant, not merely an audit outcome
(corrected, PF-1F-HR-E1 Correction 1, C1-2).** A configuration change that is self-affecting (it
would increase the initiating administrator's own authority, scope or threshold) or that creates
or changes a protected meta-authority (including `AUTHORITY_CONFIGURATION_ADMIN` itself) must
activate only after authorization by a person other than the initiator; the requester must never
be able to approve their own pending privilege increase. An ordinary, non-self-affecting,
non-meta-authority configuration change does not require a second person. Recording who authorized
a change is necessary but is not, by itself, the control - the change must not take effect at all
until independently authorized. See
`docs/agent/pf-1f-hr/PF_1A_AUTHORITY_CONFIGURATION_MODEL.md`, "Self-escalation prevention", for the
full preventive-invariant design (the `activation_status` / `initiated_by` / `authorized_by`
mechanism).

This preventive invariant is separate from, and does not resolve, the **bootstrap question** of
who is first authorized to grant/change `AUTHORITY_CONFIGURATION_ADMIN` itself before any
configuration exists at all. That remains an explicit, named open governance question (see
`docs/continuity/OPEN_QUESTIONS.md` Q-10); this ADR does not invent an unsafe self-service answer
to it.

### Parameter-file representation

For the reference implementation/prototype, the Role Catalogue, Authority Catalogue, Role ->
Authority rules and Person/Position -> Role assignments are representable as a human-readable,
schema-validated, versioned parameter file (JSON or YAML), suitable as fixtures, as a review/audit
artefact, and as an import/export representation for a future admin UI. The parameter file is
configuration **data**; it is not required to be the live production runtime store. A future
production implementation may store the same provider-neutral model in shared-platform
tables/admin UI while approval logic remains independent of the storage mechanism. See
`docs/agent/pf-1f-hr/PF_1A_AUTHORITY_CONFIGURATION_MODEL.md` for an illustrative (non-final)
fragment.

### Versioning, audit and the HR/authority boundary

Configuration is effective-dated and versioned - for all four concepts, not only Role -> Authority
rules and Person/Position -> Role assignments (corrected, C2-2). A historical approval decision
retains the authority requested, the exact Role/Authority/Rule/Assignment versions used (each
traceable to the Configuration Change that published it), the acting person/position identity and
role/authority context, the scope, and the limit/condition basis relied on, so that changing a
role, an authority, or a threshold today never alters the explanation of a decision made earlier -
consistent with `ORA-001`'s existing rule that historical decisions retain their decision-time
authority snapshot.
The HR/Organisation Reference Master (ADR-032, Phase 1 SharePoint-backed) answers *who the person
is, whether they are active, and what organisation unit/position they occupy over what effective
period*; the Authority capability answers *what configurable role is assigned, what authority
follows, for what scope, subject to what limits, over what effective period*. Approval authorities
must not be modelled as fields inside the HR reference Lists merely because those Lists are easy to
edit.

Reason:
- Baking organisational role names, job titles or employee names into approval code makes every
  reorganisation, delegation or title change a code change, which is exactly the fragility ORA-001
  already avoided for `CREDIT_ASSESSOR`/`CREDIT_APPROVER`; this ADR generalizes that avoidance to
  every business authority rather than leaving it as a one-off pattern.
- PBL explicitly directed that approval/process code must request a business authority/capability,
  not a named role, title or person, and that roles/authorities/rules/assignments must be
  admin-configurable data.
- Separating configuration representation (parameter file, schema-validated, versioned) from
  production storage mechanism keeps the model provider-neutral and avoids prematurely freezing a
  filesystem JSON/YAML file as the permanent production runtime store.

Implication:
- `ORA-001` is not rewritten by this ADR. Its contract registry entry carries a short
  cross-reference to this ADR and to `docs/agent/pf-1f-hr/PF_1A_AUTHORITY_CONFIGURATION_MODEL.md`;
  its existing `CREDIT_ASSESSOR`/`CREDIT_APPROVER` resolution rule and initial authority catalogue
  are unchanged and remain a worked example of this ADR's general rule.
- No workflow/application code, API route, database migration, permission check or business event
  changes as a result of this ADR. `docs/agent/pf-1f-hr/PF_1A_AUTHORITY_CONFIGURATION_MODEL.md`
  carries the detailed conceptual schema and an illustrative, explicitly non-final parameter-file
  fragment.
- PF-1A's own implementation package must resolve the `AUTHORITY_CONFIGURATION_ADMIN` bootstrap
  question and the exact role/authority/rule/assignment schema before production activation; this
  ADR records the governing principle, not the final schema or the first administrator.

## ADR-034: Model-role allocation and foundation-to-functional delivery strategy for the remaining PF phase

PBL's internal allocation of development work between tools for an earlier phase. Not part of this copy; it sets no rule for the application.

## ADR-035: Withdrawn — review correction-cycle sequencing belongs in delivery methodology

Withdrawn; the number is retired and not reused.

## ADR-036: SharePoint as the platform document and media repository

Date recorded: 13 September 2026. Resolves `D-05`, open since PAF-1.

Decision: a **single ERP SharePoint site** serves the PBL application platform - CRM and Equipment
Hiring now, Transportation, Maintenance and other modules later - rather than a site per module.
The application owns its content; people may look, not touch.

### The site and its shape

- **One ERP site**, exclusive to these modules. Not one site per module: a module boundary is a
  library, not a site, and one site keeps one permission model, one retention surface and one
  place to look.
- **One document library per module**, with folders organising categories *within* a module's
  library. Libraries are the boundary because permissions, metadata columns and retention all
  apply cleanly at library level, and because deep folder trees meet SharePoint's view thresholds
  as they grow. The owner's stated design allowed either folders or libraries for CRM; library-per-
  module is the engineering recommendation within it.

### Who may do what

- **The application owns the content.** It reads and writes through a service identity. Users
  reach documents through the application's own screens, where the record-scoped, fail-closed
  authorization added by Slice 9C is the access control.
- **No human access to the site at all, except a named administrator role.** Not even view. People
  reach documents through the application, which is also where they download anything they want to
  work with outside it - `GET /api/documents/{public_id}/content`, already record-scoped and
  fail-closed since Slice 9C.
- The access rules therefore live in **one** place - the application - rather than being mirrored
  into SharePoint and kept in sync forever.

Site-wide view permission for staff was considered first and rejected, as was mirroring the
application's permission structure into SharePoint. **The mirror cannot be built faithfully**: the
application's rules are *record-scoped* ("documents belonging to Accounts you own"), while
SharePoint's are *container-scoped* (a library, a folder). Expressing one as the other would mean
arranging folders by ownership - and ownership changes, so the structure would have to be rewritten
on every reassignment. That is not a maintenance cost; it is a design that does not hold.

A site administrator can necessarily read everything. Keep that a small, named group.

**This closes a coupling with `Q-14` rather than leaving one open.** View-only stops editing, not
reading: had staff kept site view permission, anyone could have read and exported every document in
a library - including documents attached to records the application would not show them. That is
harmless while every role already reads every record, but `Q-14` exists precisely to narrow that,
and site-wide view would then have silently undone it for documents. Admin-only removes the
question: when Q-14 narrows what a person may see, it narrows document access with it, because the
application is the only way in.

### What goes in SharePoint, and what does not

- SharePoint holds **files** - documents, images, video and similar - and **lists that are not part
  of the application's own data structure**.
- **Anything that is part of the database structure stays in PostgreSQL.** SharePoint is not a
  second home for application data.
- The purpose is cost: file bytes are far cheaper in SharePoint than in the database, and media is
  what drives storage up.

This rule also covers the governed HR reference Lists of ADR-032: they are structured reference
data read through a provider-neutral adapter, not application database structure, so SharePoint is
their correct Phase-1 home.

**Timing trap for those Lists.** `docs/agent/pf-1f-hr/PF_1F_HR_SHAREPOINT_STARTER_SPEC.md` records
that copying a List to another site **silently breaks its Lookup column relationships**. The seven
starter Lists are pending population by PBL staff. Create the ERP site *before* anyone populates
them; a later move breaks the relationships without saying so.

### Retention

Deliberately deferred, by owner decision: retention policies are to be defined **once the system is
running**, judged against real storage consumption, business need and data-protection rules.

This **extends the existing deferred retention item** rather than creating a second one - see
`docs/agent/DEFERRED_REQUIREMENTS.md`, "Interactions (Slice 9D) - recorded parkable items", the
policy entry covering interactions, documents and quotations together. SharePoint's own retention
labels may become the implementation mechanism; if they do, they must not become a *second*
retention rule competing with `document_metadata.retention_due_at`. Decide one owner for the
policy at that point.

### Consequence for uploads: images work, video does not

Checked against `backend/app/modules/documents/contract.py` on 13 September 2026:

```text
MAX_UPLOAD_BYTES         = 25 MiB
ALLOWED_UPLOAD_EXTENSIONS = .pdf .doc .docx .xls .xlsx .png .jpg .jpeg .txt .csv
```

Images are already accepted. **Video is not - neither the type nor the size** - so the intent to
store video needs its own design rather than a larger cap. A file of that size should almost
certainly go **direct to SharePoint with the application storing a reference**, rather than being
streamed through the application's upload path, which buffers against a request ceiling. That is
future work, not a gap in this decision.

### Scope

No code, contract, schema, migration, permission, business event or workflow changes as a result
of this ADR. Slice 9C's storage abstraction is already the seam a SharePoint provider plugs into,
and the `documents` module already keys on `linked_record_type` with a fail-closed map, so adding
Hiring, Transportation or Maintenance record types is a map entry rather than a restructuring.

Reason:
- `D-05` had been open since PAF-1 with the register recording only "library, permission and
  retention design open", and the SharePoint work could not start without it.
- App-owned storage keeps one set of access rules instead of two, and the application's own
  record-scoped check already exists and is tested. Mirroring business rules into SharePoint
  permissions would create a second authority to keep in step - and could not express them anyway,
  record-scoped rules having no faithful container-scoped equivalent.
- A single site with per-module libraries matches the platform direction of ADR-030: future
  modules consume the same documents capability rather than reinventing one, and a library gives
  each module a clean boundary without a separate site to administer.
- Keeping database-structural data out of SharePoint, and file bytes out of the database, is a
  cost decision the project owner made explicitly.

Implication:
- `docs/agent/architecture/EXTERNAL_DEPENDENCY_REGISTER.md` and `docs/continuity/OPEN_QUESTIONS.md`
  are reconciled: `D-05` is resolved for the design questions above, with **retention the only part
  deliberately left open**.
- A SharePoint provider implementation may now be scoped. It belongs behind the Documents
  capability as a provider, not inside any business module.

## ADR-037: Canonical platform data structures; external masters enter through transformers

Date recorded: 24 September 2026. The owner's standing rule of that date, and its first
application, agreed with the WRR-001 design (`docs/agent/slices/wrr-001-resource-requirement-foundation.md`,
questions Q10 to Q17).

Decision: the platform designs its own canonical structure for each kind of master data it depends
on, to the standard the domain needs, and does not inherit the structure of Plum or any other
existing system. Where the existing system holds the data today, an adapter-owned transformer maps it
into the canonical structure - converting units, combining or splitting fields, and flagging doubtful
values rather than silently correcting them. Authority is stated per phase, so no two systems claim
the same fact. When the platform becomes primary, a reverse transformer feeds the existing system in
whatever shape it still needs.

The owner's position, in summary:

> We design the structure our business needs rather than inheriting another system's. Where the existing ERP
> system's master cannot change, we build a transformer from what it holds into the new structure. In time the new
> structure becomes the primary source, and the existing ERP system takes its data from it - combining some fields,
> or transforming them in other ways. Our build must be sound and future-proof.

### First application: equipment

The **Equipment Reference** - class, type, capability with exactly one unit each, and later model,
machine, and the part classes of the machine's component hierarchy - is platform-owned, serves both Hiring and Transportation, and is owned on the business
side by Fleet's Equipment Master owner (Q14). Each class records which business lines deploy it
(Hiring, Transportation, or neither), so one structure serves both modules without light vehicles
or workshop assets appearing where Operations plans hiring. Codes never change and nothing is
deleted: a row is retired in a later version and anything saved with it keeps it. An alias table
records what other systems and people call things - Plum's categories, the FRS Annexure-21 types,
trade words - and is what the transformer reads Plum through.

Authority by phase:

| Phase | Machine identity, status, statutory documents | Class, type, model, capabilities |
| --- | --- | --- |
| 1 - now to Hiring assignment | Plum, through the transformer | **The platform's Equipment Reference**; Fleet curates the mappings |
| 2 - Hiring assignment on the platform | **The platform**; Fleet maintains machines in it | The platform |
| 3 - Plum follows | The platform; Plum ingests through the reverse transformer | The platform |

Plum's data comes in by three routes that combine (Q16): **B**, the platform's own transformer, now
(the package after WRR-001); **A**, asking Plum's vendor for a type field, a model key, capabilities
in the platform's units, the Annexure-20 validity dates and a superstructure-carrier link, in
parallel; **C**, the platform primary, once Hiring assignment runs on it.

### Relationship to earlier decisions

- Follows ADR-032's pattern for HR - canonical, provider-neutral structure behind an adapter, with
  authority stated per phase - and ADR-030's direction of capability moving out of Plum.
- Refines `RMR-001`'s statement that Plum's Equipment Master is authoritative for owned equipment:
  that remains true for machine identity, status and statutory documents in Phase 1, while the
  structure, meaning how machines are classified and described, is the platform's. `RMR-001` gains a
  short note; its text is not rewritten.
- "Never a competing master" (`RMR-001`, the module boundary matrix) is met by making ownership of
  each fact explicit per phase, not by copying the legacy shape.

Reason:
- Plum's equipment master was built for a different purpose and does not separate what planning needs. One "CRANES" category covers
  crawler, all-terrain, truck-mounted and pick-and-carry cranes alike; its one capacity field is
  tonnes for cranes and kilograms for manlifts and axles; "TRAILERS" means the prime movers (section
  21 of the WRR-001 design, from Plum's report of 24 September 2026). A requirement shaped around
  that would carry the same ambiguity into availability, assignment and eligibility.
- A structure of the platform's own is data, not code: a type or capability is added by a new
  version, and the transformer absorbs whatever Plum can or cannot supply.

Implication:
- New module `backend/app/modules/equipment_reference/` holds the structure (version 1 loaded by
  migration `20260908_0041`) and a `ports.py` naming the source-adapter interface the transformer
  will implement. Resource Requirements (`WRR-001`) is its first consumer.
- `RMR-001` carries a note pointing here; `CONTRACT_REGISTRY.md`,
  `architecture/EXTERNAL_DEPENDENCY_REGISTER.md` (Plum Equipment Master row) and
  `architecture/MODULE_BOUNDARY_OWNERSHIP_MATRIX.md` (Equipment Master and Resource Catalogue rows)
  are reconciled with it.
- Every later master the platform depends on - vehicle types for Transportation, maintenance codes,
  spares - starts from the same question: what structure does the domain need, and how does the
  existing system's data get transformed into it?

### Refinement, 25 September 2026 (owner; recorded with ERT-1)

Drafted in section 19 of the ERT-1 design
(`docs/agent/slices/ert-1-plum-machines-into-the-equipment-reference.md`) from the owner's comments 1 to 3
of 25 September 2026, and recorded here when ERT-1 was built.

> **Refinement, 25 September 2026 (owner).** The platform's records are built for the job at hand, not
> limited by what Plum holds or can give.
>
> 1. Where Plum does not hold a fact the job needs, the Fleet Admin obtains it and enters it on the
>    platform, which is then that fact's source; the transformer never overwrites it. Machines are
>    still added through Plum in Phase 1: Plum's facts first, the rest by the Fleet Admin.
> 2. Where a Plum value is mixed or wrong, the Fleet Admin decides how it is read - split into its
>    facts, or reassigned to the field it belongs in - by a recorded rule or correction that the
>    transformer applies on every import, and that is listed for Plum to fix at source. A correction is a
>    decision by an accountable person, so "flag doubtful values rather than silently correct them"
>    stands.
> 3. Until a Fleet Admin role exists - one or two responsible people outside day-to-day operations -
>    Admin holds these duties.
>
> The Phase 1 row of the authority table reads: machine identity, status and statutory documents -
> **Plum, through the transformer, as corrected by the Fleet Admin; facts Plum does not hold, the
> platform.**

The Phase 1 row above therefore now reads, for machine identity, status and statutory documents: Plum,
through the transformer, as corrected by the Fleet Admin; facts Plum does not hold, the platform. Class,
type, model and capabilities are unchanged: the platform's.

As built by ERT-1: a value rule (`equipment_source_value_rule`) reads one Plum value wherever it appears;
a machine correction (`equipment_asset_correction`) replaces one Plum value of one machine, applies at
once and on every import, closes itself when a confirmed report carries the corrected value, and is
flagged `PLUM_CHANGED_CORRECTED_VALUE` when Plum changes to a third; "Corrections to send to Plum" lists
every open one - route A, always current. A machine's serial number and year of manufacture are the
platform's facts (point 1). `EQUIPMENT_REFERENCE_MANAGE` is granted to Admin (point 3). Updated with it:
`RMR-001`'s ADR-037 note, `architecture/EXTERNAL_DEPENDENCY_REGISTER.md` (Plum Equipment Master) and
`architecture/MODULE_BOUNDARY_OWNERSHIP_MATRIX.md` (Equipment Master).

## ADR-038: Approval rights set by an administrator until the HR feed exists

Date recorded: 13 October 2026. The owner's decision while preparing the CRM vendor package
(`docs/continuity/OPEN_QUESTIONS.md`, "The CRM package"). A recorded exception under ADR-030's exception process.

Decision: until PBL buys and activates the HR feed - organisation authority read from PBL's HR records (`ORA-001`), a
separately priced option in the vendor package - the right to approve is set by an administrator in the application's
settings. For each kind of approval - markup below the threshold, a quotation's issue, the credit assessment, the credit
approval, a material change to a terms-and-conditions clause - an administrator names a role or a named person, and may
change it to another role or person at any time without a code change.

Principle varied: authority to approve comes from PBL's HR records - positions, and who holds them - and never from a
list kept separately in the application, so that a leaver or a mover loses it automatically (ADR-026, ADR-033,
`ORA-001`; `architecture/PRODUCTION_READINESS_GATES.md`, Definition of Ready, the authority item).

Reason: the owner chose to quote the approvals facility now and the HR feed as a separate option, and PBL's position
data is not yet held in a structured form (ADR-032). Without this exception, approvals - and with them markup, quotation
and credit control - could not go live until the HR feed does.

Alternatives considered:
- the HR feed as a condition of approvals: safer, but approvals wait for the HR feed and for PBL's position data;
- no approvals until then: markup, quotation and credit decisions would go unchecked.

Consequences, and the rules while it applies:
- every change of an approver setting is recorded as a business event: who changed it, when, from what to what;
- an approval already given keeps the approver and the authority they held at the time; a request still waiting when
  the setting changes moves to the new approver;
- disabling a user ends every approval right they hold, at once;
- a screen lists who may approve what, for PBL to review regularly;
- the person who prepared a quotation never approves it; other maker-checker rules are as the approval policy sets
  (`APR-001`);
- the cost: when someone leaves or changes job, an administrator must update the settings by hand.

Integration: modules ask one question through the approvals facility (`APR-001`) - may this person approve this, now?
The answer comes from the administrator's settings while this exception applies, and from the organisation-authority
engine once the HR feed is active, so the switch needs no change in the modules that ask.

Security and governance: only administrators change approver settings. Being an administrator does not by itself make
someone an approver (`docs/continuity/OPEN_QUESTIONS.md`, Q-07).

Temporary: it ends when the HR feed option is bought and activated. The administrator's settings then become authority
assignments read from HR records, and this decision is superseded.
