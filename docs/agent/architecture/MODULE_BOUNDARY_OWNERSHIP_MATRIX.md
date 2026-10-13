# Module Boundary and Ownership Matrix

## Status

Approved boundary baseline, 12 August 2026. Exact schemas and routes remain contract/slice work.

## Commercial and contract modules

| Module | Owns | Does not own | Primary dependencies |
| --- | --- | --- | --- |
| Lead | enquiry/lead intake record, source, triage, qualification and conversion decision | Account identity, Opportunity pursuit, credit | Account, Opportunity, Events |
| Account Master | legal party/Qualified Prospect identity, contacts, addresses, classifications, Account lifecycle and authoritative legal-entity/PAN credit profile | external validation execution, exposure calculation | Identity Validation, Authorization/Org Authority, Approval Policy, Documents |
| Opportunity | one pursuit/RFQ/tender context and stage | Account master data, offer pricing, Work Order | Account Master, Commercial Offer |
| Commercial Offer | offer series, lines, pricing evidence, terms attachment, submission, commitment-review schedule and customer outcome | Account credit master, calculated exposure, Work Order execution | Opportunity, Credit Exposure, Background Jobs, Notifications, Work Order handoff |
| Account Credit Profile (Account Master component) | independently implementable component inside the Account Master boundary for approved Credit Amount/Days, approval evidence and effective history | separate customer master, utilization/exposure calculation, receivables | Account identity, Authorization/Org Authority, Approval Policy |
| Credit Exposure | Potential/Firm exposure calculation and availability decision | approved credit master, offer/work-order ownership, receivables ledger | Credit Profile, Commercial Offer, Finance integration |
| Work Order / Contract | customer commitment shell, lines, amendments, contractual execution terms and release state | resource availability, operational evidence, billing calculation | Commercial Offer handoff, Customer Master, Resource Requirement |
| Customer Master Activation | Finance-controlled activation decision and Plum/customer reference | Account identity creation, Work Order execution | Account Master, Work Order, Authorization/Org Authority, Approval Policy, Finance integration |

## Operational modules

### Upstream master-data modules

| Module | Owns | Does not own | Primary dependencies |
| --- | --- | --- | --- |
| Equipment Master | authoritative owned-equipment/vehicle identity, technical specifications, ownership and active status; in Phase 1 held in Plum and read through a transformer (ADR-037), as corrected by the Fleet Admin, with facts Plum does not hold (serial number, year of manufacture) entered on the platform (ADR-037 refinement, 25 September 2026; built by ERT-1) | the equipment structure - classes, types, capabilities and their units - which is the platform's Equipment Reference since ADR-037; availability, operational assignment, log evidence | Equipment Reference, Documents, Integration Gateway, Maintenance inputs |
| Equipment Reference (platform, ADR-037) | the canonical equipment structure: classes and the business lines that deploy them, types, capabilities each in one unit, the alias table mapping other systems' words to it, and its versions; models and machines with their fitted parts, and the Fleet Admin's value rules and corrections (ERT-1); and the detachable kit held for each crane model, recorded on the platform (ERT-2). Owned on the business side by Fleet's Equipment Master owner | machine identity and status in Phase 1 (Plum, as corrected), availability, assignment | Transformer from Plum's report (ERT-1); consumed by Resource Requirement, Availability, Assignment, Eligibility |
| Holiday Calendar (platform reference, HOL-1) | PBL's default holiday calendar, year by year (`backend/app/modules/holiday_calendar/`): each holiday's date, kind (national or festival), name and where it applies - all of India or the states named, from ELG-1's list - each year's versions and Admin's "complete" mark; kept by Admin until a position is mapped under `ORA-001` | a Work Order's changes to it (the Work Order's terms), what a holiday is charged (each line's off-day term; a working day's rate is the Work Order's), employees' holidays for attendance or pay (8B, from PBL's HR terms), the list of states (Eligibility's, read through its service) | Eligibility (the states, through its service; it asks which years are not complete through a port the calendar registers); consumed by Work Order, and later Log Sheet and Billing Engine |
| Employee Master | authoritative employee identity, employment/active status, organization units, positions/designations, reporting relationships and current position incumbents | application permissions/authority mappings, assignment, attendance/log evidence, eligibility decision | Identity Validation, Documents, HR/Payroll integration |
| Vendor Master | authoritative supplier/service-provider/broker legal identity, active/blocked status and statutory/payment-profile references | Vendor Hire Agreement, equipment/crew resource identity, assignment or supplier bill | Identity Validation, Documents, Purchase/Finance integration |

Equipment, Employee and Vendor Masters may be implemented elsewhere in the wider ERP, but they
are explicit dependencies of the operational modules. PBL CRM/Hiring must consume their approved
records through `RMR-001`/`VMR-001` and the Integration Gateway and must not create competing
master copies.

### Operational planning and execution modules

| Module | Owns | Does not own | Primary dependencies |
| --- | --- | --- | --- |
| Resource Catalogue | operational resource reference that makes owned equipment, eligible employees/crew and secured external resources available to planning, classified in the Equipment Reference's terms (ADR-037) rather than a catalogue of its own | Equipment or Employee master data, the equipment structure itself, availability, assignment, maintenance history | Equipment Master, Equipment Reference, Employee Master, Market Hire, Documents, Integration Gateway |
| Resource Requirement | demand recorded against a Work Order line (WRR-001): units, period, crew, and what each unit is in Equipment Reference terms; since 8A core, its fulfilment status, worked out from the allocations it reads through a port Resource Assignment registers (`resource_requirements/ports.py`) | resource commitment or procurement, any Work Order table, the equipment structure, the allocations themselves | Work Order (read through its service), Equipment Reference, Eligibility, Resource Assignment (through the port) |
| Resource Availability | candidate availability, reservations and expected release. For owned machines, 8A core works availability out inside Resource Assignment from the allocations themselves, with no reservation or expected release yet | final assignment, maintenance authority | Resource Catalogue, Requirement, maintenance inputs |
| Resource Assignment | commitment/release/replacement history for equipment/resources and crew. Owned-machine half built by 8A core (`backend/app/modules/resource_assignments/`): a machine held for a requirement's unit over a period, never two over a common day, replacements and frees kept as history, the billing cycle, trips and the kit listed on them, and the eligibility decision each was made on | procurement, Equipment/Employee master data, eligibility rules, log evidence; the requirement, the Work Order line and its site, read only through their services | Availability, Eligibility, Resource Catalogue, Market Hire, Resource Requirement, Equipment Reference |
| Compliance / Eligibility | licence/certification/skill evidence and assignment eligibility decision. Machine half built by ELG-1 (`backend/app/modules/eligibility/`): machines', fitted parts' and kit's certificates and "not applicable" marks, keyed on the asset's public id; the certificate rules as dated data per jurisdiction; the `ELA-001` decision, stored when 8A allocates on it; and (ELG-2) the certificate reminders - worked out when read, from its own records and 8A's held allocations, read through a port Resource Assignments registers - with their versioned schedules and escalation paths and people's "seen" marks, shown on its own Alerts page until Notifications can take the screen channel | assignment state or Equipment/Employee master ownership; the equipment structure and asset records, read only through the Equipment Reference's service | Documents, Identity Validation, Equipment Master, Equipment Reference, Employee Master, Resource Catalogue |
| Market Hire | external resource sourcing, supplier quote/approval and secured-resource reference | supplier master identity, final operational assignment, supplier invoice accounting | Vendor Master, Requirement, Authorization/Org Authority, Approval Policy, Resource Assignment |
| Log Sheet | approved record of what happened operationally and supporting evidence | commercial interpretation or invoice grouping | Assignment, Work Order, Documents |
| Billing Engine | deterministic interpretation of contract terms and approved evidence into billable results | operational evidence approval, tax invoice issue | Work Order, Log Sheet, Approval Policy |
| Invoice Preparation | grouping, statutory context, evidence pack and Finance/Plum handoff | billable calculation or receivables accounting | Billing Engine, Account/Customer Master, Finance integration |

## Shared platform capability modules

Each row below is a **logical module/capability**: it has one clear owner, its own responsibilities
and a defined interface used by other modules. This does **not** mean each one needs a separate
server, database, repository or deployment. Several may initially live in one shared-platform
code area and deploy with the application. They should be separated physically only when scale,
security, ownership or operational needs justify it.

These are PBL platform-level shared capabilities (ADR-030): a future module should consume the
same identity, authorization, documents, events, jobs, integration-gateway and notification
capabilities listed here rather than reinventing them, unless a documented exception applies. See
`PBL_PLATFORM_ARCHITECTURE_AND_FUTURE_AI_READINESS.md` section 8.4.

| Capability | Owns | Boundary rule |
| --- | --- | --- |
| Authentication | user authentication/session/token lifecycle | Business modules consume authenticated identity; they do not issue tokens |
| Authorization / Organization Authority (`ORA-001`) | application permissions, data-scope and business-authority mappings against Employee Master employee/position references, authority lifecycle and delegation validity | Employee Master is a logical capability that owns organization units, positions, reporting relationships, incumbents and employment status. As of ADR-032 (31 August 2026), Plum does not currently implement the structured organisation-unit/position/incumbency data that capability requires; Phase 1 builds the canonical Employee Master output from Plum's basic/raw HR facts plus a governed SharePoint-backed interim structured source (see `docs/agent/pf-1f-hr/`), with a future `NEW_SHARED_PLATFORM` HR/Organisation Reference Master as the eventual canonical implementation and later Plum synchronization. ORA and every other consumer read only the resulting canonical Employee Master output through the provider-neutral contract in `docs/agent/pf-1f-hr/PF_1F_HR_CANONICAL_REFERENCE_MODEL.md`, never Plum or SharePoint directly; backend ORA checks are authoritative for application actions |
| Workflow / Approval Policy (`APR-001`) | approval request/decision, configured approval policy and decision evidence | Consumes `ORA-001`; does not own authority identity or the business record being approved |
| Identity and Statutory Validation | provider adapters, normalized validation result, retry/fallback and evidence reference | Consumer owns business consequences; provider payload does not leak across modules |
| Documents / Evidence | document metadata, versions, access metadata and storage reference | Consumer owns why a document is required and its business status |
| Business Events / Outbox | durable event record, publication state and consumer delivery metadata | Originating module owns event meaning and schema |
| Background Jobs | scheduling, retries, locking, idempotency and failed-job state | Job execution is not a substitute for business state |
| Integration Gateway | external-system/provider connectivity, mapping and reconciliation transport | Business modules own source business rules and accepted outcomes |
| Notifications (`NTF-001`) | template/channel delivery, retry and status | Originating module owns audience trigger and business meaning |
| Interactions (`INT-001`) | the shared conversation log: `interaction` and `interaction_participant`, their channel/direction/participant semantics, message-content classification and content-read redaction | Sole writer of its own two tables and writer of no others. Attaches polymorphically to Lead, Account, Opportunity, Commercial Offer and Work Order without those modules owning, storing or being aware of the log; reads them only to prove a link target exists and to resolve Lead conversion lineage for inherited history. Attachments use the Documents capability's `document_metadata`, which Interactions does not own. A future ingestion adapter is a consumer of this capability, never a parallel writer (ADR-030) |
| Audit / Observability | technical telemetry and cross-module trace access | Does not replace module business events or current state |

## Boundary enforcement

- One module is the sole writer of each authoritative aggregate/table group. Where the code departs from this today -
  three writers into another module's table, five repository imports and 183 cross-module reads, and five database
  rules that read across the Commercial Offer and Work Order tables - each departure is recorded in
  `BOUNDARY_EXCEPTION_REGISTER.md` (8 October 2026, TB-1 TB1-100 and TB1-101; measured again on 9 October, after
  CS-04 part 1). PF-1B owns and retires all but the five rules, which are a permanent exception to ADR-017 the owner
  approved on 9 October 2026, owned by the Commercial Offer to Work Order handoff (the CRM lane). Interactions' link
  checks, in its row above, are one of the departures.
- The Employee Master logical capability is the sole writer of employee and organization
  structure; ORA may keep a versioned decision snapshot/reference but cannot edit a competing
  position or reporting tree, and no CRM/Hiring-owned competing master may be created. As of
  ADR-032 (31 August 2026), Plum does not currently implement the structured Organisation Unit,
  Position or Position Incumbency data this capability requires - PBL has confirmed this
  directly. The current (Phase 1) implementation of this capability is: Plum's
  basic/raw HR facts, composed with a governed SharePoint-backed interim structured source, behind
  the HR-reference adapter/composition boundary defined in
  `docs/agent/pf-1f-hr/PF_1F_HR_CANONICAL_REFERENCE_MODEL.md`. The eventual canonical
  implementation/owner is a future `NEW_SHARED_PLATFORM` HR/Organisation Reference Master (Phase
  2), with Plum synchronizing applicable raw facts into it thereafter (Phase 3). ORA and every
  other consumer depend only on the provider-neutral canonical contract that boundary exposes -
  never directly on a Plum table, a SharePoint List, or any other provider-specific structure.
- Foreign public IDs are references; consumers validate them through contracts.
- A shared capability may be implemented in common infrastructure but must still expose an owned
  interface.
- `Account` remains the UI term and `business_party` the internal/domain/database term where the
  existing model uses it.
- Future multi-source Lead ingestion and pre-sales vetting may introduce a dedicated module/role
  only through an approved boundary and role decision; the credit assessment is owned by the
  configurable `CREDIT_ASSESSOR` authority (`ORA-001`), whose initial/default mapping is
  `SALES_MANAGER`.

## Initial code mapping

Existing `backend/app/modules/` folders are implementation history, not automatic production
boundaries. TE-2 and later module slices may reorganize internals only through scoped migrations
and regression-safe changes. In particular, `accounts` and `business_party` together currently
serve the Account surface; do not duplicate Account data while refining that boundary.
