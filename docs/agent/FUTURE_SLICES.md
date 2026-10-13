# Future Slices - Agent Backlog

This backlog starts after Slice 5B. It is intentionally sequenced so agents add business depth without breaking the foundation chain.

## Next recommended sequence

Slices 6A through 6P, including the documented decimal sub-slices, are implemented. Slice 6P (Demo Data and Vendor Walkthrough Scenario Pack, documentation/fixture-tooling only) did not choose or start a further functional slice, per its own scope.

The active planning baseline is `docs/continuity/PRODUCTION_DEVELOPMENT_TRANSITION_2026-08-11.md`. PAF-1 Production Architecture Foundation is complete as a documentation/contract-definition package: architecture ADRs and boundaries are approved, and sixteen of the eighteen new inter-module contracts are `APPROVED`. `MHA-001` remains `PROPOSED` pending genuine decisions D-03/D-04; `BIP-001` remains `PROPOSED` pending D-06. These do not delay unrelated modules. `TE-2A - Next.js -> React + Vite` is implemented, independently reviewed and accepted, committed as `5c87e07` and integrated on `main` (see `docs/agent/technical-enablement/TE_2A_REACT_VITE_MIGRATION.md`). PBL has confirmed PostgreSQL as the frozen production database (ADR-028), so that gate is closed. `TE-2B - migrate SQL Server -> PostgreSQL` is implemented, independently reviewed, accepted and integrated on `main` as commit `75fd4fc`. Part 1 established the PostgreSQL runtime/configuration and ported all 28 Alembic revisions; Part 2 converted the active repository, tooling, tests and generated skeleton and completed the full validation sequence. It is followed by `TE-2CI - GitHub Actions validation foundation`, which is split in two: **TE-2CI.1 (repository implementation) is implemented, locally verified, independently accepted and integrated on `main` as commit `1b4d08c`**, and **TE-2CI.2 (hosted validation and integration control) is complete and hosted-verified at commit `8bb6af1`, so TE-2CI as a whole is complete**: a first hosted run (`31865333180`) found that Compose teardown did not deterministically remove a cancelled run's containers and network, corrected by TE-2CI.2-C1 and integrated as `70f3c23`; the next hosted run (`31871165805`) then passed every substantive check including Playwright and failed only at teardown, because the profile-gated `e2e-node-modules` volume survived `down -v`, corrected by TE-2CI.2-C2 and integrated as `8bb6af1`. Run `31930125170` proved both — attempt 1 green end to end with a clean teardown, attempt 2 a controlled cancellation leaving nothing behind — and demonstrated `Required validation` succeeding and failing correctly. At the time (16 August 2026), required-check registration and enforced branch protection were not possible on the repository's then-current GitHub plan; ADR-029 recorded the approved interim manual merge gate, a process control rather than technical enforcement, and called for the plan to be reassessed before production. **As of 17 August 2026, that reassessment happened and the plan limitation is closed**: a GitHub repository ruleset technically enforces `Required validation` and the associated branch rules on `main`, recorded as **ADR-031**, which supersedes ADR-029 for the current enforcement mechanism. `TE-2C - migrated-foundation verification` was unblocked (ADR-025) but not started at the time this paragraph was first written; **status update, 18 August 2026: TE-2C is now complete** (evidence SATISFIED/PASS, closure documentation integrated on `main` as commit `7f5a05dca3ea93921e5a9f11a8c8dd0156c59c2f` - see `docs/agent/technical-enablement/TE_2C_MIGRATED_FOUNDATION_VERIFICATION.md`). The stable required-check name is `Required validation`. The current package is `DEV-ORCH-1A` (deterministic developer-orchestration core; see `docs/agent/technical-enablement/DEV_ORCH_1A_DETERMINISTIC_ORCHESTRATION_CORE.md`), followed by DEV-ORCH-1B, a controlled DEV-ORCH qualification run, the Vercel Readiness Spike, and then PF-1F-HR and PF-1A. `PF-1` implements shared authority, API/event retrofit, jobs, notifications, dependency discovery, NFR evidence and contract fixture/freeze lanes before dependent modules run in parallel. PF-1F-HR Employee/Organization interface and change-feed validation is the prerequisite for PF-1A authority activation; ORA must not create its own organization positions.

*Reconciled 7 October 2026 (TB-1 TB1-904):* the paragraph above is the position of 18 August 2026, kept as written; its "current package" is not current. Of the packages it names, DEV-ORCH-1A, DEV-ORCH-1B, the qualification run, the Vercel Readiness Spike, PF-1F-HR-E1 (the first PF-1F-HR package) and PF-1A through E3 are complete; after E3 (7 September 2026) PF-1A stopped and DEV-ORCH was suspended, and PF-1 as a whole is only partly met - the API/event retrofit (PF-1B) is not built (`docs/agent/architecture/MODULE_DEPENDENCY_AND_DELIVERY_WAVES.md`, "Foundation gates"). The work since (Slices 9A-9E, the CRM pilot, the Hiring lane's 7C to HOL-1) is summarised in `AGENTS.md`, "Current prototype state". What is next is in `docs/continuity/NEXT_STEPS.md`; this backlog says what each future slice holds, not which is current.

The previously recommended Consolidated Manual UAT and Vendor-Demo Review Cycle covering Slices 6L-6P remains available if PBL wants a final prototype/demo review; vendor review itself remains deferred until PBL explicitly authorizes it. After the production foundation is established, the previously-open threads 6G.1, 6H.1 or 6I.3 remain available, depending on whether T&C approvals, commercial approvals or calculated exposure controls should come first. Slice 6M.1 was a corrective foundation fix (Commercial Offer terminal status transition guard) inserted after 6M; it does not change this recommended sequence. Slice 6O (Work Order shell detail / handoff review UI) closed the Commercial-Offer/Work-Order-handoff UI thread that 6N/6M started.

TE-1 (`docs/agent/technical-enablement/TE_1_REUSABLE_SMOKE_FIXTURES_PLAYWRIGHT_REGRESSION_FOUNDATION.md`) is a technical-enablement work package inserted after Slice 6O, not a numbered business slice, and does not change this recommended sequence. It adds a reusable smoke-test data harness and an isolated Playwright regression suite covering the flow through Slice 6O.

Slice 6O.1 (Supplementary and Change Commercial Offer Foundation) is implemented; see `docs/agent/slices/slice-6o1-supplementary-change-commercial-offer-foundation.md` and the Slice 6O.1 section of `docs/agent/contracts/commercial-offer-contract.md`. It extended the TE-1 scenario catalogue (4 new scenarios) and Playwright suite (3 new specs) rather than building separate seed/cleanup tooling, as instructed.

Slice 6O.2 (Work Order Amendment Intake Foundation) is implemented; see `docs/agent/slices/slice-6o2-work-order-amendment-intake-foundation.md` and `docs/agent/contracts/work-order-amendment-contract.md`. It followed the same pattern as 6O.1: the TE-1 scenario catalogue and Playwright suite were extended (not replaced), with a third independently seeded/cleaned manifest alongside `core-regression-bundle` and `related-offer-regression-bundle`. Amendments are intake/review records only; no application of a validated amendment to the Work Order is implemented, and that remains a separate future slice.

Slice 6P (Demo Data and Vendor Walkthrough Scenario Pack) is implemented; see `docs/agent/slices/slice-6p-demo-data-vendor-walkthrough-scenario-pack.md`. It added a `vendor-demo-bundle` TE-1 scenario, `scripts/vendor-demo.ps1`, a non-destructive `@demo-preflight` Playwright suite and four `docs/demo/` walkthrough documents. It changes no CRM business behavior, API contract or migration.

TE-2A (`docs/agent/technical-enablement/TE_2A_REACT_VITE_MIGRATION.md`) is a technical-enablement work package, not a numbered business slice, implemented and accepted after independent review. It replaced Next.js with React 19 + Vite + React Router (ADR-016) while preserving every public URL, workflow, permission behavior and Playwright scenario. It removed the Playwright cold-compile warm-up (`e2e/tests/global-setup.ts`) because a pre-built bundle has no per-route compile cost; the scenario catalogue, manifests, assertions and `retries: 0` are unchanged.

### 6A - Linked Record Navigation and Traceability Stabilization

Status: implemented.

Thin UI/API polish slice.

In scope:

- Show linked Work Order(s) on the originating Commercial Offer profile.
- Add CO -> WO navigation after Work Order shell creation.
- Improve origin-aware return navigation between CO, Opportunity, Account and Work Order.
- Standardize linked-record cards and page-level Back actions.

Out of scope:

- No WO release/posting.
- No Equipment Hiring execution.
- No billing logic.

### 6A.1 - Commercial Offer Account Link Guard and Repair Path

Status: implemented.

Thin business-flow guard slice.

In scope:

- Show linked Account context on Commercial Offer and Work Order handoff surfaces.
- Block Commercial Offer submit/accept and Work Order shell handoff when Account traceability is missing.
- Keep repair guidance tied to the existing Opportunity / Lead / Account flow.

Out of scope:

- No Customer Master activation.
- No Account relinking workflow.
- No WO release/posting.

### 6B - Demo Navigation and UI Polish Foundation

Status: implemented.

Thin UI/demo-readiness slice.

In scope:

- Add a consistent app shell and demo-flow navigation cue.
- Improve the dashboard as a demo entry point.
- Standardize list status badges and empty-state treatment across implemented flow pages.

Out of scope:

- No backend route/schema changes.
- No T&C, approval, execution, billing or release/posting functionality.

### 6B.1 - Opportunity Account Repair and Commercial Offer Actionability Guard

Status: implemented.

Thin business-flow guard slice.

In scope:

- Controlled Opportunity Account repair for Opportunities missing Account / `business_party` traceability.
- Link existing Account or create a minimal Account / Qualified Prospect.
- Reject unauthorized repair and silent relinking.
- Preserve Commercial Offer submit/accept and Work Order shell Account traceability guard.
- Allow only one active/actionable Commercial Offer per Opportunity until formal revisions and Opportunity lines exist.

Out of scope:

- No Customer Master activation.
- No Opportunity lines.
- No formal Commercial Offer revision/versioning.
- No production Commercial Offer numbering.
- No Work Order release/posting.

### 6B.2 - Demo Readiness UI Consistency Pass

Status: implemented.

Thin UI/demo-readiness slice.

In scope:

- Dashboard implemented-versus-deferred guidance.
- Shared action row, button link, form card, list card and table containment styling.
- Consistent list/create surface treatment across Lead, Account, Opportunity, Commercial Offer and Work Order shell demo screens.

Out of scope:

- No backend route/schema/model/permission change.
- No Customer Master activation.
- No WO release/posting.
- No equipment, crew, log sheet, billing or approval workflow.

### 6C - Vendor Demo Guide and Prototype Traceability Pack

Status: implemented.

Documentation/demo-readiness slice.

In scope:

- Vendor demo guide for the implemented Lead -> Account -> Opportunity -> Commercial Offer -> Work Order shell flow.
- Prototype traceability walkthrough for linked records, Account repair / traceability guard and Commercial Offer active/actionable guard.
- Deferred functionality matrix for vendor/business review.
- Vendor implementation handoff notes for stack flexibility, API route base, authorization, Account terminology, Commercial Offer line identity and Work Order shell boundaries.

Out of scope:

- No application functionality.
- No backend route/schema/model/permission change.
- No frontend code change.
- No PHP/MS-SQL migration work.

### 6C.2 - Render Vendor Demo Deployment Plan

*Note, 13 October 2026:* 6C.2 and 6C.3 below are history. They studied a hosting provider for an early demonstration,
when the database was still SQL Server. Production will be in PBL's Azure account
(`docs/vendor/10_HOSTING_USERS_AND_TARGETS.md`); their records are not in this copy.

Status: implemented.

Documentation/deployment-planning slice.

In scope:

- Render Hobby vendor-demo deployment plan.
- Demo readiness checklist.
- Demo data backup/reset plan.
- Document-storage decision for demo and production direction.
- Open questions before actual deployment.

Out of scope:

- No deployment files.
- No Docker Compose change.
- No app code, schema, migration, contract or test change.
- No SharePoint integration.
- No production document storage.
- No PHP/MS-SQL migration.

### 6C.3 - Render Database and Runtime Feasibility Spike

Status: implemented.

Documentation/inspection spike.

In scope:

- Inspect current Docker, backend database, Alembic, dependency, environment and frontend `/api` runtime shape.
- Determine whether current app can use Render Postgres without a rewrite.
- Document alternatives for temporary vendor demo access.
- Recommend safest temporary vendor-demo path.

Finding, as recorded when the spike was performed:

- The current prototype is tightly tied to SQL Server.
- Render Postgres is not feasible without a separate database compatibility implementation slice.
- Safest near-term demo path is local Docker Compose screen share, or Render frontend/backend connected to an approved external SQL Server-compatible demo database after a small deployment configuration slice.

**Superseded as a current runtime recommendation by ADR-028 and TE-2B.** The finding above remains
an accurate record of what was true when the spike ran, and is preserved for that reason. The
premise it rested on no longer holds: PostgreSQL is now the frozen production database and the only
supported runtime, and TE-2B performed exactly the "separate database compatibility implementation"
the spike said would be required. A future hosted-demo decision should be re-taken against the
PostgreSQL stack; do not act on the SQL Server-compatible demo database recommendation.

Out of scope:

- No deployment implementation.
- No database conversion.
- No app code, Docker, Compose, migration, runtime config, contract or test change.

### 6D - Production MVP Scope and Parallel Delivery Plan

Status: implemented.

Documentation/planning slice.

In scope:

- Production-grade MVP definition.
- Minimum CRM production scope.
- Minimum Equipment Hiring production scope.
- Parallel workstream split for CRM, Hiring, Platform/NFR and UAT/documentation.
- CRM-to-Hiring handoff freeze checklist.
- Deferred-scope decisions to protect a 1-2 month MVP timeline.

Finding:

- A 1-2 month timeline is feasible only as a tightly scoped production MVP, not full CRM plus full Equipment Hiring.
- Parallel CRM/Hiring work is safe only after the Accepted Commercial Offer to Work Order handoff contract is frozen.

Out of scope:

- No application code.
- No backend/frontend logic.
- No Docker, database, migration, test or contract change.

### 6D.1 - Accepted Offer To Work Order Handoff Freeze

Status: implemented.

Documentation/contract-definition slice.

In scope:

- Freeze the Accepted Commercial Offer to Work Order shell handoff trigger.
- Freeze logical header and line payload fields for parallel CRM/Hiring work.
- Preserve Commercial Offer line identity into Work Order lines.
- Define Work Order shell output, unreleased status meaning and handoff events.
- Define CRM, Hiring, Platform/NFR and UAT agent responsibilities against the frozen contract.
- Update Commercial Offer and Work Order contracts to point to the handoff freeze.

Finding:

- Parallel CRM/Hiring work can proceed only if the frozen handoff fields, Account traceability, line identity, backend authorization and event/audit expectations remain stable.
- The current prototype status `HANDOFF_CREATED` maps to the production MVP unreleased shell meaning. `HANDOFF_RECEIVED` is recommended as the production MVP initial Work Order shell status, and `PENDING_CUSTOMER_MASTER` may be a later readiness/checkpoint state or release-block reason.

Out of scope:

- No application code.
- No backend/frontend logic.
- No Docker, database, migration, runtime config or test change.
- No Customer Master activation.
- No Work Order release/posting.
- No equipment, crew, log sheet, billing or invoicing functionality.

### 6D.2 - Parallel Agent Work Packages

Status: implemented.

Documentation/planning slice.

In scope:

- Create reusable implementation work packages for CRM, Equipment Hiring, Platform/NFR/security and UAT/documentation workstreams.
- Capture common rules for all agents.
- Give each workstream objective, docs to inspect, scope, out of scope, constraints, expected outputs, checks and commit message pattern.
- Document safe parallel sequencing.
- Warn parallel agents not to redefine identity, Customer Master boundary, credit/reference timing, document metadata policy or event/authorization expectations.

Finding:

- Parallel agents should first confirm handoff fixtures/examples, then CRM and Hiring can proceed in parallel.
- Platform/NFR should run continuously.
- UAT/documentation should prepare scripts in parallel and join fixed integration checks.

Out of scope:

- No application code.
- No backend/frontend logic.
- No Docker, database, migration, runtime config or test change.
- No implementation of CRM, Hiring, Platform or UAT features.

### 6D.3 - Handoff Fixture and Example Payload Pack

Status: implemented.

Documentation/fixture slice.

In scope:

- Create safe, non-confidential example fixtures for the frozen Accepted Commercial Offer -> Work Order shell handoff.
- Provide full accepted-offer handoff, Work Order shell output, partial-award/selected-line, missing Account and invalid line-selection examples.
- Provide a fixture validation checklist.
- Mark fixtures as contract examples only, not seed data or runtime fixtures.
- Update parallel-agent work-package references.

Finding:

- Future CRM, Hiring, Platform/NFR and UAT agents can use the same example payloads without redefining the 6D.1 handoff contract.
- Production MVP examples use `HANDOFF_RECEIVED`; current prototype mapping remains `HANDOFF_CREATED`.

Out of scope:

- No application code.
- No backend/frontend logic.
- No Docker, database, migration, runtime config or test change.
- No real customer, vendor, statutory, address, personal, document, secret, password or token data.

### 6D.4 - ERP Source Document Import and Agent Extract Pack

Status: implemented.

Documentation/source-reference slice.

In scope:

- Register ERP Functional Requirements Specification and NFR source `.docx` documents under `docs/source/`.
- Create agent-readable full-text Markdown extracts under `docs/reference/erp-source-extracts/`.
- Create curated CRM/Hiring, T&C, hiring billing, field annexure and tools/assets extracts.
- Create safe T&C reference fixtures for future T&C master and Commercial Offer attachment slices.
- Update continuity and future-agent references.

Finding:

- `pandoc` was not available locally, so full-text Markdown extracts were produced with a local PowerShell Open XML extraction method.
- Source `.docx` files remain the source of truth, especially for table-heavy annexures, exact legal wording and any embedded content.

Out of scope:

- No application code.
- No backend/frontend logic.
- No Docker, database, migration, runtime config, contract or test change.
- No production T&C implementation.
- No billing engine implementation.

### 6E - T&C Master / Clause Library Foundation

Status: implemented.

In scope:

- Create Terms and Conditions master/clause library.
- Clause categories, applicability and active/inactive treatment.
- Basic read-only list/detail with permission controls.
- Source-derived prototype clause seed data from Slice 6D.4 extracts/fixtures.

Out of scope:

- No Commercial Offer attachment.
- No line-level T&C selection.
- No clause create/update/deactivate UI.
- No deviation or new-clause approval workflow.
- No document generation.

### 6E.1 - T&C Clause Library Layout Polish

Status: implemented.

Frontend/UI polish slice.

In scope:

- Move selected clause detail near the top of the T&C Clause Library page.
- Show filter/search panel and selected clause detail side-by-side on wide screens.
- Stack filter/search, selected detail and clause list on smaller screens.
- Keep clause table below both top panels.
- Clear old page-level errors after successful clause load/filter.

Out of scope:

- No backend code.
- No database migrations.
- No API route changes.
- No seed data changes.
- No business behavior or contract changes.
- No Accepted Offer -> Work Order handoff change.

### 6E.2 - Frontend Next.js Security Patch Upgrade

Status: implemented.

Platform/security dependency patch slice.

In scope:

- Upgrade frontend Next.js from `15.1.3` to `15.1.12` within the compatible `15.1.x` patch line.
- Create/update the frontend lock file consistently.
- Run frontend build, frontend test script and Next.js version check.
- Record residual npm audit findings for future platform/security planning.

Finding:

- `15.1.9` was considered first, but npm still emitted a Next.js security warning for that version.
- `15.1.12` is the selected same-line patch target.
- `npm audit --omit=dev` still recommends `next@15.5.20`, which is outside this narrow patch scope and should be handled as a separate compatibility slice if required.

Out of scope:

- No backend code.
- No database migrations.
- No API route changes.
- No T&C behavior changes.
- No business behavior or contract changes.
- No Accepted Offer -> Work Order handoff change.

### 6F - Commercial Offer T&C Attachment Foundation

Status: implemented.

Header-level Commercial Offer T&C attachment foundation.

In scope:

- Attach selected active header-applicable T&C library clauses to Commercial Offer headers.
- Copy selected clause details into snapshot fields so future master changes do not silently change issued offers.
- Show attached header clauses on the Commercial Offer detail page.
- Allow Sales/Admin roles to attach and remove header T&C attachments.
- Record `CommercialOfferTcClauseAttached` and `CommercialOfferTcClauseRemoved` events.
- Preserve source-derived/prototype warnings and deferred-scope messaging.

Out of scope:

- No line-level T&C selection.
- No clause text editing inside Commercial Offer.
- No deviation approval workflow.
- No omitted mandatory-clause approval.
- No generated quote/PDF document.
- No legal versioning workflow.
- No Accepted Offer -> Work Order handoff change.

### 6G - Commercial Offer T&C Readiness And Recommended Clause Foundation

Status: implemented.

Commercial Offer header-level T&C readiness and recommended-clause attachment foundation.

In scope:

- Show recommended header-level clauses for an explicit recommendation basis.
- Support `HIRING` and `TRANSPORTATION` readiness.
- Compare active recommended header clauses with active Commercial Offer header attachments.
- Show attached/missing readiness counts and status.
- Attach missing recommended clauses through the Slice 6F snapshot mechanism.
- Keep attach-recommended idempotent when all recommended clauses are already attached.

Out of scope:

- No line-level T&C selection.
- No clause text editing inside Commercial Offer.
- No deviation approval workflow.
- No omitted mandatory-clause approval.
- No hard block on Commercial Offer submission.
- No generated quote/PDF document.
- No legal versioning workflow.
- No Accepted Offer -> Work Order handoff change.

### 6G.1 - T&C Deviation and New-Clause Approval Foundation

In scope:

- Request approval when a standard clause is materially modified.
- Request approval when a new clause is proposed for the master.
- Maker/checker rule where approval independence is required.
- Events for request, approve, reject and withdraw.

Out of scope:

- No complex approval hierarchy beyond foundation.

### 6H - Commercial Offer Submission Readiness Checklist Foundation

Status: implemented.

Advisory Commercial Offer submission-readiness checklist.

In scope:

- Single read-only submission readiness API.
- Commercial Offer detail page readiness panel.
- Consolidated checks for Account traceability, Opportunity traceability, active offer lines, pricing evidence and header T&C readiness.
- Deferred rows for credit/exposure gate, approval workflow, quote/PDF/document generation and submission proof.
- No business events for readiness reads.

Out of scope:

- No hard submission blocking added by this slice.
- No quote/PDF generation.
- No actual quote submission workflow.
- No submission proof upload/capture.
- No credit/exposure calculation.
- No approval workflow.
- No legal T&C approval.
- No line-level T&C selection.
- No Accepted Offer -> Work Order handoff change.

### 6H.1 - Commercial Offer Approval and Submission Control Foundation

In scope:

- Commercial approval before customer-facing submission where required.
- Submission proof and document locking metadata.
- Submitted version tamper-evidence.
- Potential Exposure event hook.

Out of scope:

- No full document generation unless separately scoped.

### 6I - Commercial Offer Submission Evidence Foundation

Status: implemented.

In scope:

- Metadata-only Commercial Offer submission evidence records.
- Multiple evidence records per Commercial Offer.
- Evidence fields for channel, submitted date/time, reference, recipient summary, external document metadata and notes.
- `CommercialOfferSubmissionEvidenceRecorded` business event on create.
- Submission readiness checklist item for evidence present/missing.
- Commercial Offer detail page evidence list and add form.

Out of scope:

- No quote/PDF/document generation.
- No file upload/storage.
- No SharePoint/document automation.
- No credit exposure calculation.
- No approval workflow.
- No legal T&C approval.
- No automatic lifecycle status change.
- No Accepted Offer -> Work Order handoff change.

### 6I.1 - Commercial Offer Detail Tabbed Navigation Polish

Status: implemented.

In scope:

- Frontend-only tab grouping for the existing Commercial Offer detail page.
- Overview, Lines & Pricing, Terms & Conditions, Submission and Traceability tabs.
- Preserve existing section actions, role visibility, linked navigation and local feedback.

Out of scope:

- No backend/API/database/business behavior change.
- No quote/PDF generation, approval workflow or legal T&C approval.
- No Work Order handoff or release/posting change.

### 6I.2 - Commercial Offer Credit / Exposure Readiness Foundation

Status: implemented.

In scope:

- Append-only manual credit/exposure review evidence.
- Current/superseded review history.
- Manual review integration with advisory Submission Readiness.
- Review creation event and role-controlled list/create routes.

Out of scope:

- No exposure calculation or Account/PAN credit-limit consumption.
- No Finance approval workflow or hard submission block.
- No lifecycle or Work Order handoff change.

### 6I.3 - Commercial Offer Calculated Credit/Exposure Gate Foundation

In scope:

- Exposure/availability gate against already-approved Account/PAN credit amount and payment days.
- Potential Exposure contribution from submitted offers and tender bids.
- Block or route for approval when over limit/exhausted.
- Preserve approval reference for Work Order release.

- The same availability gate must also run before a new Work Order is confirmed, against active
  commitments, outstanding receivables and the approved limit (FRS 2.3.10).

Important wording:

This is not the initial prospect credit assessment. That happens earlier at Account/PAN level.

### CRM - Account PAN hierarchy guard (number to be assigned)

From the 16 September 2026 gap check against FRS 2.3.4. The Account already holds one PAN and many
GSTINs, which is the shape the requirement asks for, but nothing enforces it:

- the same PAN may be recorded on two different Accounts, which splits the hierarchy that PAN-level
  credit (ADR-015) and line-level billing GSTIN selection (7C) both rely on;
- a GSTIN is not checked against the Account's own PAN, although a GSTIN contains the PAN it
  belongs to, so one Account can hold another company's registration.

A GSTIN may not be recorded twice anywhere, so that half is already safe. A fix needs a check of
existing data before any unique index is added, and it is CRM-lane work on the shared migration
chain. See `docs/agent/DEFERRED_REQUIREMENTS.md`, "FRS 2.3 to 2.8 gap check".

### 6J - Commercial Offer Submission Lifecycle / Commercial Commitment Foundation

Status: implemented.

In scope:

- Controlled Draft/Ready for Review -> Submitted action.
- Account, Opportunity, active-line, submission-evidence and rejected/on-hold credit-review guards.
- Commercial commitment event and readiness status.
- Submission-tab local action/feedback.

Out of scope:

- No document generation/sending, exposure calculation or approval workflow.
- No Work Order creation/release or handoff-contract change.

### 6K - Commercial Offer Revision / Resubmission Foundation

Status: implemented.

In scope:

- Metadata-only revision/resubmission records after Commercial Offer submission.
- OPEN, RESUBMITTED and CANCELLED revision status traceability.
- Optional source submission evidence and required existing resubmission evidence links.
- Opened/resubmitted/cancelled events and advisory Submission Readiness integration.
- Submission-tab history and role-controlled actions.

Out of scope:

- No Commercial Offer cloning or new offer lines.
- No full quote/legal versioning, version comparison or submitted-version locking.
- No quote/PDF generation, file storage or SharePoint automation.
- No credit exposure calculation or approval workflow.
- No Work Order handoff change.

Future follow-up work may add a full quote version model, immutable submitted-version snapshots, comparison, document generation and legal/version controls as a separate deeper slice.

### 6L - Commercial Offer Customer Response / Award Outcome Foundation

Status: implemented.

In scope:

- Append-only post-submission customer response / award metadata.
- Optional same-offer evidence and revision links.
- Accepted/rejected lifecycle alignment, response event, advisory readiness and Submission-tab UI.

Out of scope:

- No automatic Work Order or frozen handoff change.
- No Customer Master, Finance approval, release/posting, billing/execution or document automation.
- No full award-to-Work-Order readiness gate.

### 6M - Commercial Offer Post-Response Lifecycle Readiness Cleanup

Status: implemented.

In scope:

- Read-only derived lifecycle/readiness view (`GET /api/commercial-offers/{public_id}/lifecycle-guidance`) over existing Slice 4E/6H/6I/6I.2/6J/6K/6L records.
- One coherent Submission-tab narrative combining readiness, revision/response history, derived guidance and Work Order handoff state.
- Regression tests proving the existing revision-open and Work Order handoff guards already reject every invalid post-response action.
- Frontend default that stops offering "Create Work Order shell" once a shell already exists for the offer, while preserving the frozen contract's backend-level multi-shell/partial-award support.

Out of scope:

- No new backend guard/state machine; the existing guards already held and only gained regression tests.
- No automatic Work Order creation.
- No change to the frozen Slice 6D.1 Accepted Offer -> Work Order handoff contract.
- No calculated credit/exposure gate (remains Slice 6I.3).
- No award-amendment workflow or partial-award allocation redesign.

Finding: Slice 6M substantially absorbs the originally anticipated "6N - Accepted Offer to Work Order Handoff Guard and UX Polish" scope. A future agent should treat 6N as folded into 6M rather than opening a redundant slice; the next open functional slice in this thread is 6O.

### 6M.1 - Commercial Offer Controlled Terminal Status Transition Guard

Status: implemented, in two commits.

Corrective foundation fix, not a new business feature.

Commit `fa09489` (part 1): blocked `PUT /api/commercial-offers/{public_id}` from changing `offer_status_code` away from `WITHDRAWN`, `REJECTED` or `CLOSED` to any other value.

Completion commit (part 2): follow-up verification found the gap only partly closed - `SUBMITTED -> ACCEPTED`, `SUBMITTED -> REJECTED` and `ACCEPTED -> (anything else)` were all still possible through generic update. The completion commit:

- Blocks `PUT /api/commercial-offers/{public_id}` from ever setting `offer_status_code` to `ACCEPTED` or `REJECTED` ("cannot enter"), regardless of current status.
- Adds `ACCEPTED` to the set of statuses generic update cannot leave, joining `WITHDRAWN`/`REJECTED`/`CLOSED` from part 1.
- Splits `COMMERCIAL_OFFER_TERMINAL_STATUSES` into two explicitly separate contract constants - `COMMERCIAL_OFFER_GENERIC_UPDATE_CANNOT_LEAVE_STATUSES` and `COMMERCIAL_OFFER_GENERIC_UPDATE_CANNOT_ENTER_STATUSES` - and un-aliases `COMMERCIAL_OFFER_INACTIVE_FOR_NEW_OFFER_STATUSES` (Slice 6B.1) back to its own independent `(WITHDRAWN, REJECTED, CLOSED)` tuple, since `ACCEPTED` must join the cannot-leave set but must not join the unrelated 6B.1 "inactive for new offer" set.
- Frontend: removes `ACCEPTED`/`REJECTED` from the Offer status edit control entirely and disables the control (directing to the Customer Response action) once the current status is cannot-leave.
- Updates every pre-existing backend test that relied on the old (buggy) generic-PUT-to-ACCEPTED/REJECTED path, and adds a new focused test for both entry-guard directions.

Out of scope (unchanged by either commit):

- No change to any specialized lifecycle route's own guard logic (mark-submitted, revisions, customer responses, lifecycle-guidance); they were already correct.
- No new state machine beyond the two named cannot-leave/cannot-enter sets; `DRAFT`/`READY_FOR_REVIEW`/`WITHDRAWN`/`CLOSED` remain freely settable as generic-update targets from any non-cannot-leave status.
- No migration.
- No change to the frozen Slice 6D.1 Accepted Offer -> Work Order handoff contract.

Finding: every specialized Commercial Offer lifecycle route already validated its own current-status precondition; only the generic update route lacked one, and lacked it in two dimensions (leaving a terminal status, and entering `ACCEPTED`/`REJECTED` at all). Both dimensions are now closed without introducing a full status transition matrix.

### 6O - Work Order Shell Detail / Handoff Review UI

Status: implemented.

In scope:

- A "Work Order handoff review" snapshot inside the existing Commercial Offer Lifecycle Guidance panel (Submission tab), shown only while the offer is Accepted: offer reference, status, mode/type, date, value, Account/Opportunity links, active line count/summary and an explicit no-shell-yet / N-shells-exist statement.
- Minor context enrichment of the existing `/work-orders/new` review-before-create page (offer mode/type/date, existing-shell summary).
- A richer Work Order shell detail page: a "Handoff shell" status badge, created-by/last-updated fields, a "Handoff provenance" section (creation timestamp/creator for every viewing role, plus the underlying `WorkOrderCreated` business event for Admin/Management Read Only roles), and a contained, responsive line-traceability table showing each Work Order line's source Commercial Offer line identity.
- A narrow, backward-compatible `record_type`/`record_public_id` filter added to the existing `GET /api/events/recent` route to support the provenance panel, with no new route, permission change or migration.
- Backend regression/traceability tests, including proof that the frozen contract still allows more than one Work Order shell per accepted offer (partial award) even though the UI's default action remains "Create" only while zero shells exist.

Out of scope:

- No WO release/posting, equipment/crew assignment, log sheets or billing.
- No partial-award allocation/remaining-quantity logic; the UI default remains conservative (Create only while no shell exists, Open for any that do).
- No change to the frozen Slice 6D.1 handoff contract, which remains byte-for-byte unchanged (SHA-256 verified before and after this slice).

### 6O.1 - Supplementary and Change Commercial Offer Foundation

Status: implemented.

In scope:

- Explicit `offer_purpose` (`BASE`/`SUPPLEMENTARY`/`CHANGE_QUOTATION`) on Commercial Offer, backfilled to `BASE` for all pre-existing offers.
- Self-referencing `base_offer_id` linking a related offer directly to its Base Offer (no chains).
- Optional (Supplementary) / required (Change Quotation) `related_work_order_id` link, validated against the Base Offer's Opportunity/Account.
- Thin customer request context (`customer_request_reference`, `customer_request_received_date`, `customer_request_summary`).
- `POST /api/commercial-offers/{base_offer_public_id}/related-offers` creation action, `GET .../related-offers` and `GET /api/work-orders/{public_id}/related-offers` listings.
- Refinement of the Slice 6B.1 one-active-Base-Offer guard to scope its scan to `offer_purpose = BASE` only.
- Independent lifecycle for related offers via every existing Commercial Offer lifecycle route, unmodified.
- Frontend purpose badges, a dedicated related-offer creation page, and read-only related-offer sections on the Commercial Offer, Opportunity and Work Order detail pages.
- TE-1 smoke-data harness extension (4 new scenarios, 2 new builders, ownership-aware cleanup covering the new self-referencing FK and a new cross-table FK cycle with `crm_work_order`).
- Playwright extension (3 new specs, a second seeded manifest run alongside `core-regression-bundle`).

Out of scope:

- No Work Order Amendment record or application to a Work Order (Slice 6O.2).
- No automatic copying of offer lines, prices or terms from the Base Offer.
- No automatic Work Order or Work Order Amendment creation.
- No reopening or mutation of the Base Offer.
- No remaining-quantity / partial-award allocation logic.
- No second revision mechanism; Slice 6K revisions remain scoped inside one offer's own series.
- No change to the frozen Slice 6D.1 handoff contract, which remains byte-for-byte unchanged.

See `docs/agent/slices/slice-6o1-supplementary-change-commercial-offer-foundation.md`, the Slice 6O.1 section of `docs/agent/contracts/commercial-offer-contract.md`, and `docs/continuity/SLICE_6O1_SUPPLEMENTARY_CHANGE_COMMERCIAL_OFFER_FOUNDATION.md` for full detail.

### 6O.2 - Work Order Amendment Intake Foundation

Status: implemented.

In scope:

- Work Order Amendment record (`crm_work_order_amendment` / `crm_work_order_amendment_line`) capturing a customer-requested administrative or commercial change as an **intake/review record only**, with amendment types `ADMINISTRATIVE`/`COMMERCIAL`/`MIXED` and a guarded status transition matrix (`RECEIVED -> UNDER_REVIEW -> VALIDATED/REJECTED/CANCELLED`, the last three terminal).
- Amendment line actions `ADD_LINE`/`CHANGE_LINE`/`CANCEL_LINE`, with an original-value snapshot captured from the referenced Work Order line at proposal time.
- Traceability from the Amendment record back to an accepted Slice 6O.1 Supplementary Offer or Change Quotation as its commercial basis, where applicable; the `VALIDATED` transition requires that basis to be independently `ACCEPTED`, checked live.
- Full route set, authorization (reusing `WORK_ORDER_CREATE_ROLES`/`WORK_ORDER_READ_ROLES`), business events and frontend UI (Work Order Amendments section, intake page, detail page, and a restrained action on an Accepted related offer's Commercial Offer detail page).
- TE-1 scenario catalogue and Playwright suite extension, consistent with how Slice 6O.1 extended TE-1 (a third independently seeded/cleaned manifest, not a new framework).

Out of scope (deferred, not implemented by this slice):

- **Explicit, controlled application of an Amendment to a Work Order.** This was originally proposed as in-scope for 6O.2 but was deliberately deferred: nothing in this slice ever writes to `crm_work_order` or `crm_work_order_line`. "Validated" means validated for future downstream processing, not applied. A future slice must define Work Order versioning/line-replacement/effective-totals behavior separately.
- No remaining-quantity / partial-award allocation logic beyond what Slice 6O.1 already declined to add.
- No WO release/posting, equipment/crew assignment, log sheets or billing.
- No change to the frozen Slice 6D.1 handoff contract or the Slice 6O.1 related-offer contract.

See `docs/agent/contracts/work-order-amendment-contract.md`, `docs/agent/slices/slice-6o2-work-order-amendment-intake-foundation.md` and `docs/continuity/SLICE_6O2_WORK_ORDER_AMENDMENT_INTAKE_FOUNDATION.md` for full detail.

### 6P - Demo Data and Vendor Walkthrough Scenario Pack

Status: implemented.

In scope:

- A `vendor-demo-bundle` scenario added to the existing TE-1 smoke-data harness, covering demo Tracks A-F (Lead -> Account -> Opportunity, Commercial Offer preparation/submission, award/handoff, revision/outcome history, Supplementary Offer/Change Quotation, Work Order Amendment intake) with an interactive/fallback record pair for every live-mutation step.
- `scripts/vendor-demo.ps1` (`prepare`/`status`/`preflight`/`reset`/`cleanup`), delegating all seeding/cleanup to the existing harness.
- A new read-only `status` command in `backend/tooling/smoke_data`.
- A non-destructive `@demo-preflight` Playwright suite (`e2e/tests/demo-preflight.spec.ts`), reusing the existing `e2e/` workspace.
- Four `docs/demo/` documents: vendor demo runbook, scenario matrix, presenter checklist, vendor feedback template.
- Two real defects found and fixed during the required manual rehearsal: a Lead-conversion cleanup ownership gap, and a Playwright test-collection crash that would have broken the ordinary full regression run.

Out of scope:

- No application code changes beyond the test-tooling/fixture surface described above; no backend route/schema/migration change; no CRM business behavior change.
- No further functional slice was chosen or started as part of 6P. The Consolidated Manual UAT and Vendor-Demo Review Cycle recommended when 6P closed has since been superseded as the active next step; see the "Next recommended sequence" note above, which now points to the internal production-development transition baseline.

See `docs/agent/slices/slice-6p-demo-data-vendor-walkthrough-scenario-pack.md`, `docs/agent/acceptance/slice-6p-demo-data-vendor-walkthrough-scenario-pack-acceptance.md` and `docs/continuity/SLICE_6P_DEMO_DATA_VENDOR_WALKTHROUGH_SCENARIO_PACK.md` for full detail.

### 7A - Customer Master Activation Request Foundation

In scope:

- Customer Master activation request from first Work Order.
- Finance approval before WO release/posting.
- Preserve Account/business_party relationship.

Out of scope:

- No finance ERP posting unless explicitly scoped.

### 7B - Work Order Release / Posting Gate Foundation

In scope:

- WO release readiness checks.
- Required customer document/reference checks.
- Visibility of Commercial Offer approval and credit/exposure approval references.
- Release/hold events.
- Refuse release while any line's operational detail (7C) or billing terms (7D) are incomplete, or
  while the Work Order's holiday list is unanswered (7D Part 4: no answer, or "names these holidays"
  with none entered).
- Contract validity: no operational or billing transaction beyond the approved contract end date
  unless an extension has been recorded (FRS 2.3.7; the dates themselves come from 7D Part 3).
- On posting, create the Mobilisation Transportation Order under "PBL Own Loads" (FRS 2.7.1). That
  order belongs to Transportation/TMS; Hiring raises it rather than owning it.
- **Turn 8A's holds into firm allocations** (8A core, Q1, owner 28 September 2026): machines are held for an
  unreleased Work Order; release checks each held machine's eligibility again and makes the hold firm.
- **Release a line at a time, not only the whole Work Order** - the owner's leaning, 28 September 2026, "to
  be refined later": when every line but one can be released, because no machine can be allocated to that
  one, only that line should wait. So a line's required machines being held is a release check for the line.
  To be designed with 7B.

### 7C - Work Order Line Commercial Detail Foundation

Status: merged 14 September 2026 as "Work Order Line Operational Detail" (PR #58), with a 7C.1
follow-up for label spacing and collapsible line cards. See `docs/agent/slices/slice-7c-work-order-line-operational-detail.md`.

In scope:

- Site, GSTN, billing terms, UOM and customer line reference per WO line.
- Preserve source offer-line identity.

As built: site, billing GSTIN and billing address picked from the Account; billing basis
(Hour/Shift/Day/Month) and contracted hours; customer line reference. The remaining billing terms
moved to 7D by owner decision.

### 7D - Work Order Line Billing Terms

Status: slice document agreed 14 September 2026, split in two by owner decision. **Part 1** (periods,
basis and hours moved from 7C, Work Order rate, off days, overtime, breakdown, idle time, minimum
guarantee, part month) is merged through PR #61 (`eed77ea`), migration `20260908_0037`; five review
rounds, committed by owner decision with one finding carried to Part 2. **Part 2** (night/second shift,
mobilisation, demobilisation, fuel) is implemented on `hiring/slice-7d-part-2-billing-terms`, migration
`20260908_0038`, with owner decisions 8-12 of 15 September 2026; it also closes the Work Order detail
page load generation carried from Part 1's review round 5. Mobilisation and demobilisation are recorded
once for the line, on its first period. See
`docs/agent/slices/slice-7d-work-order-line-billing-terms.md` and
`docs/continuity/SLICE_7D_PART_2_BILLING_TERMS.md`.

In scope:

- The rest of the `WBT-001` term set per Work Order line: normal rate and period basis, overtime
  rule, standby, breakdown/downtime treatment, minimum guarantee and pro-rating, second shift and
  holiday, mobilisation/demobilisation, fuel treatment.
- Effective-dated term versions, so amendments never rewrite terms already billed.
- Entered with the customer's Work Order (owner decision 4 of Slice 7C).
- Designed against the Annexure-10 billing examples; no calculation engine.

### 7D Part 3 - the contract period, extensions, line dates and copying terms

Status: **implemented 17 September 2026** on `hiring/slice-7d-part-3-contract-period`, migration
`20260908_0039` (slot confirmed by the owner), against owner decisions 13 to 20d of the same day;
**accepted by independent review at round 3 on 18 September 2026**; merged as `944af54` on
23 September 2026, after the owner's screen check and three further review rounds. See
`docs/agent/slices/slice-7d-part-3-contract-period.md` and the Slice 7D Part 3 section of
`docs/agent/contracts/work-order-contract.md`.

In scope:

- The Work Order's contract start and end dates, with the end answerable as a fixed date or as "until
  the work is complete" - a recorded answer, distinct from leaving it blank, after which the screen
  says the Work Order cannot be closed until a firm date exists (owner decision 14).
- Extensions as their own records, keeping every earlier end date as history. No approval step; the
  screen says "Approval step not yet added" in those words.
- A line's own start and end inside that period, with blank meaning the line follows the Work Order.
- The date rules, each refusing with a message that names the dates and the line, built on a pure,
  separately tested "is this date inside the contract?" function for log sheets, release and billing
  to reuse.
- The contract's state on the Work Order page: not started, active, ends in N days, ended.
- "Apply these terms to other lines", copying every period of one line's terms - mobilisation and
  demobilisation with them - onto chosen other lines, with tick boxes, a count on the button, a
  confirmation naming any line whose terms would be replaced, and one business event per receiving
  line.

Out of scope, deliberately: expiry alerts, approval workflow, refusing closure, release or billing,
anything calculated, and the mobilisation lock (recorded, because mobilisation does not exist yet).

### 7D Part 4 - the remaining billing terms

Status: ~~**PROPOSED**, questions 21 to 26 open with the owner: billing frequency, extra kilometres,
extra crew, separate weekly-off and holiday rates, which days count as holidays, and the monthly
shortfall.~~ **Questions 21 to 26 answered 17-18 September 2026, recorded 23 September 2026;
follow-up decisions 27 to 31 of 24 September 2026. Implemented 24 September 2026** on
`hiring/slice-7d-part-4-billing-terms`, migration `20260908_0040` (confirmed by the owner); **accepted by
independent review at round 4 and passed the owner's screen check** the same day; merged as pull
request #68 (`87510ad`). See
`docs/agent/slices/slice-7d-part-4-remaining-billing-terms.md`, which supersedes the "Part 4" section of
the Part 3 document, and the Slice 7D Part 4 section of `docs/agent/contracts/work-order-contract.md`.

In scope, after the answers:

- Extra kilometres per period: not in the Work Order, or kilometres included per day or per month,
  with a rate per extra kilometre (answer 22).
- Crew per period: the number of operators and helpers per billing unit of the line, or none (equipment
  only), and how crew beyond that number is charged (answer 23).
- The holiday dates the Work Order states - national and festival - as a list of date, kind and
  description on the Work Order, one list for every line, with an explicit "names no holidays" answer,
  each date checked against the contract (answer 25, decisions 27 and 29).
- The monthly minimum-guarantee refusal reworded: a monthly shortfall is charged pro rata with no
  minimum (answer 26).

Out of Part 4, by the answers: billing frequency, which belongs to the equipment (8A, 8G; answer 21);
separate weekly-off and holiday rates, withdrawn because Part 1's single off-day choice records both
(answer 24); and any monthly-shortfall term (answer 26, a rule for 8D).

### 7D Part 5 - the shift pattern, and the crew's food, accommodation and travel

Status: **built 9-10 October 2026** on `hiring/slice-7d-part-5-crew-upkeep-shifts`, migration `20260908_0052`, from the
owner's answers of 9 October 2026; the points they left open are taken as listed assumptions (A1 to A15) for the
owner's screen check. See `docs/agent/slices/slice-7d-part-5-crew-upkeep-and-shifts.md` and the Slice 7D Part 5
section of `docs/agent/contracts/work-order-contract.md`.

In scope:

- The shift pattern per period, replacing Part 2's night shift (converted by the migration, or asked again where a
  "not in the Work Order" night shift says too little, that answer kept on the period): not in the Work Order (no shifts stated), or one, two or three
  shifts with each shift's hours in a day (no more than 24 together); one rate for every
  shift, or each later shift at its own rate - per shift, per hour or a % of the Work Order rate (the first shift's), with
  its own working days on a monthly line; overtime counted per shift or for the whole day where the Work Order charges
  it on several shifts.
- The crew's food, accommodation, travel to and from the job, and daily travel, for operators and helpers separately,
  once the Work Order states its crew: not in the Work Order, provided by the customer, or provided at a cost on a
  stated basis (food and accommodation per person per day or per month; travel per person or per trip, per person or
  per day), deducted from PBL's invoice or billed to PBL separately. Nothing is paid to the worker.

Out of scope: any calculation (8D); per-shift overtime or breakdown rules (Part 2 decision 10 stands); different
shifts on different weekdays.

### WRR-001 - Resource Requirement foundation and the Equipment Reference

Status: **design agreed 24 September 2026** (questions Q1 to Q17, ADR-037); **implemented 24 September
2026** on `hiring/wrr-001-resource-requirements`, migration `20260908_0041` (confirmed by the owner).
Independent review and the owner's screen check follow. See
`docs/agent/slices/wrr-001-resource-requirement-foundation.md` and
`docs/agent/contracts/resource-requirement-api-contract.md`.

Built:

- The platform's **Equipment Reference** (ADR-037): classes with the business lines that deploy them,
  types, capabilities each in one unit, an alias table taking in all 15 Annexure-21 types and every Plum
  category, versioned; read-only in version 1.
- **Resource Requirements**: several per Work Order line, each a number of machines of one class
  (optional type, least capabilities), a period inside the contract and the line's dates, crew numbers
  starting from the Work Order's Part 4 numbers, priority and notes; OPEN or CANCELLED; warnings for a
  missing site, dates the contract no longer covers, crew differing from the Work Order, and an unstated
  key capability. Operations and Admin write; every Work Order reader reads.
- Screens: "Resources needed" on the Work Order page, a new-requirement page, a requirement page
  (change, cancel), and the planning list in the sidebar.

### Equipment Reference transformer (next, after WRR-001): ERT-1 and ERT-2

ADR-037, route B. **ERT-1's design is agreed and built (25 September 2026)**:
`docs/agent/slices/ert-1-plum-machines-into-the-equipment-reference.md` (section 20 is the implementation
record), migration `20260908_0042`, API `docs/agent/contracts/equipment-reference-api-contract.md`.

- **ERT-1 - Plum machines into the Equipment Reference.** Admin, as Fleet Admin until that role exists,
  uploads Plum's vehicle report; a preview shows what would change and every doubtful value; nothing
  changes until confirmed. Adds the **Model** records (Plum's model names mapped to them once) and the
  **Machine** records, capabilities from the model with Plum's figure only a check, a crane's carrier as
  its fitted part, the facts Plum does not hold entered on the platform, and the Fleet Admin's recorded
  corrections of mixed or wrong Plum values, applied on every import and listed for Plum to fix.
- **ERT-2 - detachable kit.** Boom inserts, counterweights, hook blocks and tackles specific to a
  machine, recorded as its children, and the depth setting (default 3). Equipment-specific fixed assets
  are rows of Plum's equipment list (owner, 25 September 2026); the report of 24 September holds none
  apart from crane halves, so the Fleet Admin records the kit on the platform. There is no Plum tools
  list: general tools are the inventory system's (8A). See `DEFERRED_REQUIREMENTS.md`, "Asset component
  hierarchy". **Designed, agreed and built 26 September 2026; merged 27 September 2026 as `6d9154f` (PR #74)**
  (`docs/agent/slices/ert-2-detachable-kit.md`,
  section 18; migration `20260908_0043`): kit is shared by the crane models it fits, not held by one crane
  (owner and research, same day), so 8A's BOM picks from the kit held for the machine's model. Four kinds
  (boom and jib sections, counterweight - counted - hook blocks, the cranes' own lifting tackle); pieces
  retired with the day and the reason; the depth setting of 3 for fitted parts. Built so a future Fixed
  Assets module can link to machines and kit (owner, same day). Trailer beds are machines coupled to prime
  movers - Transportation's, in outline (`DEFERRED_REQUIREMENTS.md`).

Plum's report of 24 September 2026 is real fleet data: never committed as it is. Under the owner's rule
of 25 September 2026 a **dummified** copy - registration, engine and chassis numbers, PAN, insurance and
the like replaced; manufacturer-level facts kept - may be used for testing, and ERT-1 does
(`backend/tests/fixtures/plum_vehicle_report_dummified_2026-09-24.csv`).

### 8A - Equipment Hiring Execution Shell

In scope:

- Equipment assignment shell against WO line.
- Own/hired flag and vendor placeholder.
- Assignment status and traceability.
- Full assignment history per Work Order: registration number, HSN classification, asset value,
  assignment periods and every later change (FRS 2.6.1, from the Plum Equipment Master per
  `RMR-001`).
- Equipment replacement/transshipment: close tracking for the old unit, start it for the new one,
  leaving the history intact (FRS 2.5.5).
- Hired equipment: a posted vendor Purchase Order must exist before a vendor log sheet may be
  posted (FRS 2.6.2). **This is the answer `D-04` is waiting for, at least for log-sheet posting;
  whether assignment also requires one is still open.**
- Record Equipment and Personnel Gate Passes issued during execution; the closure check is 8E
  (FRS 2.7.6).
- **Fulfil the Resource Requirements WRR-001 records**: an assignment references a requirement's public
  id and the number it fulfils; "remaining" is `units_required` less that (`RPA-001`), and the reserved
  statuses PARTLY_FULFILLED, FULFILLED and COMPLETED come into use. Machines are chosen against the
  requirement's class, type and least capabilities in the Equipment Reference's terms (ADR-037).
- **Record each machine's billing cycle - weekly or monthly - with its assignment** (FRS 2.8.1; owner,
  17-18 September 2026, answer 21 of Slice 7D Part 4). The cycle belongs to the equipment, not the Work
  Order or the line: one line can carry several machines, and so several cycles. Invoicing (8G) reads
  it from here.
- **The mobilisation BOM:** what goes to site with each machine, recorded per trip - its detachable
  kit (boom inserts, counterweights, hook blocks, tackles), and general tools issued from the inventory
  system. Work Orders need not list these items (owner, 24 September 2026). Issuing a general tool
  moves stock, so that part waits for the inventory integration (owner, 25 September 2026). See
  `DEFERRED_REQUIREMENTS.md`, "Asset component hierarchy".

**Built in two parts, around the Hiring user test** (owner, 27 September 2026 - see "Hiring user test"
below):

- **8A core, before the test:** own machines allocated against the resource requirements; assignment
  status, traceability and full history; a replacement machine that keeps the earlier one's history; each
  machine's billing cycle; and the mobilisation list's kit, picked from the kit ERT-2 holds for the
  machine's model. Allocation checks the machine-side eligibility built just before it: it calls
  `record_decision` in its own transaction and keeps the decision's public id, cannot turn `BLOCKED` into an
  allocation, and checks again before the planned start (ELG-1 design, section 6, "What 8A does with it").
  8A records the site's state from the Work Order line's site and whether it is a central-government site.
- **After the test:** hired machines and vendors - the own/hired flag, the vendor placeholder and the
  Purchase Order gate - wait for decisions `D-03` and `D-04` and for `MHA-001`, still `PROPOSED`; gate
  passes; and issuing general tools, which waits for the inventory integration.

**8A core is built** (28 September 2026): `docs/agent/slices/8a-core-equipment-allocation.md` (section 17 is the
implementation record), migration `20260908_0045`, API `docs/agent/contracts/resource-assignment-api-contract.md`,
module `backend/app/modules/resource_assignments/`. Operations allocates PBL's own machines to a requirement's
units; before release an allocation **holds** the machine (owner, Q1), and a machine held for some days cannot be
held by another allocation on any of them. Eligibility's decision is stored with each allocation; a machine that
cannot be allocated, or that needs an approval, is never allocated; a warning needs the user's tick (Q2). Each
allocation shows today's answer beside the stored one, **Check again** stores a fresh one, and Allocations lists
those starting in the next 15 days. Replacing ends the old machine's days the day before, keeping both; freeing
keeps the allocation with its reason; cancelling a requirement frees its machines. The billing cycle is recorded
with each allocation, and the kit going to site is listed per trip, each piece checked as the crane is. A trip is
shown as a **Trip (Own Load)** (owner, 29 September 2026): a crane may go in several loads, each saying what part of
it it carries; moving or removing one, a model's standard loads, the crane's parts as records and the link to
Transportation's "PBL Own Loads" order are deferred (`DEFERRED_REQUIREMENTS.md`, 8A, "Trips (Own Load)").
`PARTLY_FULFILLED` and `FULFILLED` are in use; `COMPLETED` stays reserved for 8E. The site's state comes from the
Work Order line's site, and whether it is a central-government site is a new answer on the line's details.

### Eligibility foundation (before 8B)

Added to the roadmap by the owner, 25 September 2026 (ERT-1 design, Q12), after asking whether matching
crew to machines by licences and certifications had been missed. `ELA-001` (approved) holds the rules;
8B assigns crew; nothing yet builds the records the check reads:

- **each person's licences and certificates**, with issuing authority and validity - from Plum if it
  holds them (`PF_1F_HR_PLUM_GAP_ANALYSIS_PACKET.md`, question 8), otherwise entered by the responsible
  administrator (ADR-037 refinement, ERT-1 design section 19), through the HR reference of ADR-032,
  never a Hiring-owned copy;
- **what operating each kind of machine requires** - which licences, certificates or experience a class,
  type or capacity band needs - held in the Equipment Reference beside what the class can do;
- **the machine's own statutory certificates and validity dates** - insurance, fitness, pollution, road
  tax, load test, permits (FRS Annexure-20) - and those of the parts that carry them (hook blocks,
  slings, fire extinguishers; "Asset component hierarchy"). Plum's report holds none of these today;
  what Plum cannot give, the Fleet Admin enters;
- the `ELA-001` decision itself - eligible, blocked, override required - with its 60/30/15-day expiry
  alerts, which 8A (machines) and 8B (crew) then call.

The statutory position found on 26 September 2026 is recorded in `DEFERRED_REQUIREMENTS.md`,
"Statutory requirements found with ERT-2". The OSH Code 2020 has replaced the Factories Act and the BOCW
Act, and states are replacing their rules at different times. So this package holds the examination
rules as data for each jurisdiction.

**Built in two halves** (owner, 27 September 2026):

- **The machine half, before 8A's core:** each machine's statutory certificates and validity dates, and
  those of the parts that carry them, entered by the Fleet Admin where Plum cannot give them, with the
  examination rules per jurisdiction; the `ELA-001` decision for a machine, which allocation calls. An
  operations tester's first question will be whether a crane with lapsed insurance or fitness can be
  allocated.
- **The people half, with 8B:** licences and certificates of the crew, through the HR reference of
  ADR-032, and what operating each kind of machine requires. Crew assignment is 8B, after the user test.

**The machine half is built as ELG-1** (27 September 2026): `docs/agent/slices/elg-1-machine-eligibility.md`
(section 20 is the implementation record), migration `20260908_0044`, API
`docs/agent/contracts/eligibility-api-contract.md`, module `backend/app/modules/eligibility/`. Certificates of
machines, fitted parts and pieces of kit, each with its copy; "not applicable" marks only where a rule says the
law is unclear (the owner's conservative principle); rules as dated data per jurisdiction - `IN` for
central-government sites and the 36 states and union territories - with the first rules of section 5.4 in
effect from 21 November 2025; the `ELA-001` decision (`evaluate_asset`, and `record_decision` for 8A);
Certificates due worked out when read. The research of 27 September 2026 corrected the list above: fitness
and permits are for vehicles **registered as transport** only, registration itself expires and is a
certificate, and fire extinguishers are left to 8A's check before a machine goes to site (design section 2,
E, and `DEFERRED_REQUIREMENTS.md`, "Statutory requirements found with ERT-2").

### ELG-2 - Certificate reminders and escalation (after 8A's core, before the Hiring user test)

Designed in ELG-1's section 19; the owner agreed to build it as its own package on 27 September 2026 (Q14 to
Q18, "All as recommended"). **Sequence: ELG-1, then 8A's core, then ELG-2, then the Hiring user test.**

**Built as ELG-2** (1 October 2026): `docs/agent/slices/elg-2-certificate-reminders.md` (section 16 is the
implementation record), migration `20260908_0046`, API `eligibility-api-contract.md`, "Reminders and escalation".
The owner's answers of 1 October 2026 changed the list below in two ways: every short certificate takes a date and a
reason from why it is needed now (Q19), and papers never entered since they became needed are a **fourth** reminder,
"A certificate not yet recorded" - the Fleet Admin from that day, Operations 7 and Management 14 days after (Q19a). A
note with "seen" is a deferred design needing PBL's confirmation (Q20; `DEFERRED_REQUIREMENTS.md`, "Certificate
reminders: what ELG-2 leaves out").

- **Four reminders** (three as agreed on 27 September; the fourth added on 1 October, Q19a): a certificate
  running out on any active asset (from Certificates due); a certificate not yet recorded since it became needed - a
  machine added, a rule begun - which reaches the Fleet Admin first; one running out before an allocated machine's
  job starts; one running out during the job - the last two from 8A's allocations, through ELG-1's decision service,
  for the site each allocation is at.
- **Configurable schedules** (Q15): bands of "from N days before, every M days"; the standard is 60 and 30
  days before, weekly from 15, daily from 7 and after it has run out. An allocation inside the schedule is
  flagged at once.
- **Configurable escalation paths** (Q16): steps that add an audience - the Fleet Admin, then Operations
  (15 days before, or at once from the allocation), then Management (7 days before) - by role now, by
  `ORA-001` authority once positions are live. Each step names its channels: the screen only, until
  `NTF-001` is built with a provider.
- **Acknowledging never stops the escalation** (Q17); only dealing with the certificate does.
- **Admin changes the schedules and paths** (Q18) under `ELIGIBILITY_RULE_MANAGE`, on a settings screen;
  versioned, never edited. An Alerts page and a count in the menu.
- New records: `eligibility_alert_setting` and `eligibility_alert_acknowledgement`; worked out when read, so no
  job runner is needed for the screen.

### Hiring user test (after 8A's core, before log sheets)

Agreed with the owner, 27 September 2026: a business-user test of the Hiring module before going deeper,
so a mismatch with business expectations costs little rework. After 8A's core the planning half of the
chain is complete and testable end to end - accepted offer, Work Order, line details and billing terms,
resource requirements, machines allocated. Log sheets (8C) and billing come after, as they build on all of
it: a log sheet is recorded against an allocation, and billed on the line's billing terms and the
machine's billing cycle.

Sequence: the Eligibility foundation's machine half (ELG-1, built), then 8A's core, then the certificate reminders
and escalation (ELG-2), then this package, which holds:

- **Scope:** the flow above, including the earlier Hiring screens that have had only the owner's screen
  checks - line details (7C), billing terms and contract period (7D; Finance should look now, as billing
  will depend on them), resource requirements (WRR-001), and the Plum import and kit (ERT-1, ERT-2).
- **Test data:** a Hiring scenario for the synthetic data pack (TE-3), seeding Work Orders through
  allocation.
- **Testers by role:** Operations and the Fleet Admin, Sales, Finance - extending the CRM pilot's tester
  pack (`docs/uat/`).
- **Where:** the hosted UAT server, as for the CRM pilot (TE-5).
- **Open for the owner:** whether testers see PBL's real fleet from Plum's report or invented machines -
  real registration numbers on a hosted server would go against the test-data rule of 25 September 2026
  unless the owner decides otherwise.

### HOL-1 - PBL's holiday calendar (after TE-7)

Status: **design agreed 2 October 2026** (Q1 to Q5; Q4 answered with a change), **built 2 October 2026** on
`hiring/hol-1-holiday-calendar`, migration `20260908_0047` (confirmed by the owner). Independent review and the owner's
screen check follow. See `docs/agent/slices/hol-1-holiday-calendar.md`, `docs/agent/contracts/holiday-calendar-api-contract.md`
and the "HOL-1" section of `docs/agent/contracts/work-order-contract.md`.

In scope, as agreed:

- A Holiday Calendar page: a calendar per year, kept by Admin and read by everyone - each holiday's date, kind (national
  or festival), name, and all of India or the states named; versioned; a "complete" mark.
- Each Work Order follows the calendar unchanged or changes it: a holiday added, or a calendar holiday made a working day
  at the normal or the overtime rate (Q4). Slice 7D Part 4's list becomes those changes.
- The holidays that apply to each state's lines over the contract, from one pure rule log sheets and billing will call.
- A reminder on the Alerts for this year and next until each is marked complete (Q2).

Out, by the answers: the user test pack's update (Q1: after the test), a "national holidays only" choice (Q4), and
everything `DEFERRED_REQUIREMENTS.md` lists under "What HOL-1 leaves".

### 8B - Crew Eligibility / Assignment Foundation

In scope:

- Crew assignment shell.
- Skill, licence and certification checks, through the Eligibility foundation above.
- Hard block for expired/missing statutory licence when implemented.
- Assign crew from the Employee Master against each equipment shift, and generate daily attendance
  from those assignments for company-owned equipment (FRS 2.6.3; Employee Master through the
  provider-neutral HR reference of ADR-032, never a Hiring-owned copy).
- On transshipment or reassignment, stop attendance for the old crew and start it for the new one
  from the effective date, without manual intervention (FRS 2.6.4).
- **Standing rule: an operator's pay never derives from the customer's billed overtime** (owner,
  17-18 September 2026). PBL sets its operators' hours. An operator contracted for 10 hours works 10
  on a Work Order specifying 8: the customer is charged 2 hours of overtime, and the operator gets no
  overtime pay. Crew attendance and pay take their hours from PBL's own HR terms, through the HR
  reference of ADR-032 - never from the Work Order or its billing terms.
- The crew numbers Slice 7D Part 4 records per line (operators and helpers per billing unit) are what
  the **customer** is charged for. Assignment may compare the people assigned against them; it must
  not treat them as anyone's pay terms.
- The crew's food, accommodation and travel Slice 7D Part 5 records are what the **customer** provides or recovers
  from PBL, never an allowance paid to the crew ("nothing is ever paid to the worker", owner, 9 October 2026). The
  shift pattern it records (shifts a day and their hours) is the Work Order's; crew rostering per shift takes its
  hours from PBL's HR terms, as above.

### 8C - Log Sheet Foundation

In scope:

- Log sheet header/line shell against WO line and equipment assignment.
- Customer sign-off placeholder.
- Correction/audit hooks.
- Create a daily log sheet automatically for every active equipment unit, from the contract start
  date until completion, expiry or transshipment (FRS 2.5.1; needs the contract dates of 7D Part 3).
  Not on a day in a gap before an extension, which is outside the contract (owner, 22 September 2026;
  `contract_period_rules.py` answers `IN_GAP`).
- Daily capture of actual start and end times, breakdown duration, hour meter reading and odometer
  (FRS 2.5.2).
- Reconcile log sheet hours against cloud hour-meter readings before engine-hours overtime is
  processed (FRS 2.4.4.1.2). The telematics provider is an unresolved external dependency.
- ~~Which dates count as holidays, and different standard working hours on different weekdays, both
  used by billing (FRS 2.4.7; the rates for such days are recorded by 7D Part 4).~~ **Corrected
  23 September 2026:** which dates are holidays is recorded by 7D Part 4 - weekly off days already
  (Part 1), and the national and festival dates the Work Order states, as a list (answer 25) - and the
  rate for work on any of them is Part 1's single off-day choice (answer 24). Log sheets read both to
  mark a day as a holiday. Different standard working hours on different weekdays remain open
  (FRS 2.4.7).
- **PBL's default holiday calendar** (owner, 2 October 2026), built before or with this slice: PBL
  sets up a calendar every year - date, national or festival, and all of India or named states - and
  the system provides the facility. Every Work Order inherits the calendar for each line's site state,
  and its own terms vary it - a holiday added, or a calendar holiday removed - so 7D Part 4's holiday
  list becomes those variations. See `DEFERRED_REQUIREMENTS.md`, "PBL's default holiday calendar".
  **Built by HOL-1** (2 October 2026), with a calendar holiday made a working day at the normal or the overtime rate
  rather than removed (Q4). Log sheets mark each day through `work_orders/holiday_rules.py` - a holiday, or a working
  day at its rate - and correct an approved log sheet after the calendar changes a day it used by versioning
  (`LBE-001`).

### 8D - Billing Calculation Shell

In scope:

- Billing calculation placeholder from WO/log sheet.
- Billing period, UOM and line traceability.
- No full OT/breakdown/fuel logic unless separately scoped.

The calculations themselves, every one of them from terms 7D records and never guessed
(`WBT-001`):

- Hour, shift, day and month bases (FRS 2.4.2 to 2.4.4); the contracted-hours gate before overtime
  is billable (2.4.4.2); pro-rata billing below the contracted hours (2.4.4.2.1); and overtime
  first making up a shortfall (2.4.4.2.2).
- **A monthly line short of its contracted hours is deducted pro rata, with no minimum** (owner,
  17-18 September 2026, answer 26 of Slice 7D Part 4). There is no term for it: it is the rule for
  every monthly line, and 7D records no minimum guarantee on a monthly line.
- Different rates for normal, overtime, breakdown, second shift, holiday and weekly-off work
  (2.4.5), and monthly pro-rating by the calendar days of the billing period (2.4.6). **Weekly-off and
  holiday work take the same rate** (answer 24): Part 1's off-day choice - holiday rate, overtime
  rate, normal rate or not in the Work Order - applies to weekly off days and to every holiday the
  Work Order lists (answer 25), alike - and, once it exists, to every holiday of PBL's default
  calendar as the Work Order varies it (owner, 2 October 2026; see 8C). **Since HOL-1** a calendar holiday the Work
  Order makes a working day is charged as the Work Order says: at the normal rate, or every hour at the line's own
  overtime rate (Q4); where the line records no overtime rate for that day, billing refuses to guess it (`WBT-001`).
- Fuel: expected against actual consumption where the customer supplies it, with an excess parked
  as a pending deduction for the billing team (2.5.3, 2.5.4).
- Charges beyond the contract: extra kilometres, and crew beyond the agreed allocation (2.5.6). The
  allowance, the rate per extra kilometre, the crew numbers per billing unit and the extra-crew charge
  are recorded by 7D Part 4. What the customer is charged for crew never sets what the crew are paid
  (the 8B standing rule).
- **Before calculating with shifts, the owner confirms the 7D Part 5 assumptions that bear on money**
  (`slice-7d-part-5-crew-upkeep-and-shifts.md`): A9, how "the same rate for every shift" and "a rate set for each later
  shift" are counted; A10, which hours the Work Order rate buys when there are several shifts; A12's whole-month part,
  how a per-shift or per-day overtime answer applies to whole-month counting; and A15, that a later shift's percentage is
  of the Work Order rate the first (day) shift is charged at - Part 2's "% of normal" (owner decision 7) - and not of a
  rate per day, which no line records. None may be calculated with before then.
- **Shifts** (7D Part 5), once A9, A10, A12 and A15 are confirmed: bill each shift under the line's own unit - one rate
  covering every shift, or each later shift at its own rate (per shift, per hour, or a % of the Work Order rate, with its own working days on a monthly
  line) - and count overtime per shift or for the whole day as the period records. Reconcile the contracted hours
  with the shift hours against real Work Orders in Billing UAT; 7D records both as stated and checks neither against
  the other.
- **The crew's food, accommodation and travel** (7D Part 5): a cost the customer **deducts from PBL's invoice** is a
  deduction on that invoice, on the basis recorded (per person per day, month or trip, or per trip or per day whatever
  the number of people); one **billed separately**
  is a payable to the customer (Purchase/Finance), not an invoice line. "Provided by the customer" moves no money.
- Mobilisation credited back by credit note once the equipment stays beyond the minimum period
  (2.7.2), and demobilisation charged only where the contract's eligibility rule still applies
  (2.7.4).
- No billing transaction beyond the contract end date unless an extension is recorded (2.3.7).

### 8E - Work Order Closure and Demobilisation

In scope:

- Create the De-Mobilisation Transportation Order under "PBL Own Loads" on completion, where the
  contract calls for demobilisation (FRS 2.7.3).
- Validate demobilisation billing eligibility at closure (FRS 2.7.4).
- Refuse closure until every Equipment and Personnel Gate Pass issued is recorded as returned
  (FRS 2.7.6).
- Capture the closing fuel quantity at demobilisation, and refuse closure until fuel reconciliation
  differences are resolved (FRS 2.7.7).
- Check the mobilisation BOM's returnable items back, tools included (FRS 3.1; see 8A).
- Refuse closure while the contract end date is still "until the work is complete" rather than a
  firm date (owner, 17 September 2026, with Slice 7D Part 3). Part 3 tells the user so on screen;
  the refusal itself belongs here, where closure exists.

### 8F - Contract Expiry, Extension and Renewal

In scope:

- Notify the responsible people before a contract expires, so it can be extended, closed or planned
  around (FRS 2.3.8; delivery through `NTF-001`, the notice period a set parameter).
- Structured extension and renewal: continue on the same terms, or record revised ones, under an
  approval rule (FRS 2.3.9; approval needs `APR-001`). 7D Part 3 records the dates and the
  extension history; the approval workflow and the alerts are this slice.
- Enforce the validity rule across operations and billing (FRS 2.3.7), once log sheets and billing
  exist to enforce it against.

### 8G - Invoice Preparation and Submission

Waits on `D-06` - whether Plum creates the first draft from the Hiring package, or Hiring holds an
intermediate draft. `BIP-001` stays `PROPOSED` until that is decided.

In scope:

- Draft invoices generated from approved log sheets on each machine's billing cycle, weekly or
  monthly (FRS 2.8.1). **Corrected 23 September 2026:** this line said the frequency was recorded by
  7D Part 4. It is not - the owner decided (17-18 September 2026, answer 21) that the cycle belongs to
  the equipment, not the Work Order or the line, so it is recorded with equipment assignment (8A) and
  one line can be invoiced on more than one cycle.
- A configurable checklist of mandatory supporting documents (FRS 2.3.3.1), all linked and present
  before a draft is generated or submitted (2.8.5), with reminders to whoever must supply them
  (2.8.5.1), and automatic attachment of documents the ERP already holds (2.3.3.2).
- HR compliance documents - PF and ESI challans, wage register, bank transfer proof - verified
  before an invoice may be marked Ready for Submission (FRS 2.7.5).
- Submission method, and courier and proof-of-delivery tracking (FRS 2.8.2).
- Once the electronic tax invoice is generated, that line's billing address becomes read-only
  (FRS 2.3.5; recorded as a lock by 7C).
- Cancellation inside the statutory window and re-issue (FRS 2.3.6.1); a full-value credit note
  where cancellation is no longer allowed (2.3.6.2); **release of every billing and transaction
  lock afterwards, so the source data can be corrected** (2.3.6.3); and the matching reversal of
  accounting entries (2.3.6.4, Plum's own record).

### 8H - Collections and Customer Escalation

In scope:

- Configurable escalation levels by overdue age, naming the customer contact to approach at each
  level (FRS 2.8.3: 0-15 days, 16-30 days, above 30 days).

### 9A - Reporting and Dashboard Foundation

*Marked 7 October 2026 (TB-1 TB1-904):* the slice built as 9A on 7 September 2026 took part of this -
a live dashboard and four reports: pipeline, open offers, accepted offers and Work Order handoff
(`docs/agent/slices/slice-9a-reporting-dashboard-foundation.md`). Potential exposure, pending-action
views, export and profitability below are not built.

In scope:

- Pipeline, offers, potential exposure, Work Order handoff and pending action views.
- Export-ready simple tables.
- Profitability by equipment, site and customer, bringing revenue together with overtime, fuel
  variance, crew, subcontractor and other costs (FRS 2.8.4). It needs the billing and cost records
  above, so it follows them.

### 9B - Production Upgrade Readiness

*Marked 7 October 2026 (TB-1 TB1-904):* the slice built as 9B on 7 September 2026 is a different
package with the same number - CRM pilot hardening (`docs/agent/slices/slice-9b-crm-pilot-hardening.md`).
This planned package has no slice yet; parts of it were done since by TE-5 (backup and restore on the
hosted test sites), TE-3 and TE-7 (practice data) and TB-1's corrections, and TB-1's corrective
packages CS-03, CS-08, CS-09 and CS-15 (`docs/agent/tb-1/TB_1_CORRECTIVE_SLICE_REGISTER.md`) hold
much of the rest. Give it a new number when it is planned.

In scope:

- Environment/secrets review.
- Migration hygiene.
- Observability/logging.
- Backup/restore.
- Role/access matrix.
- UAT data and regression pack.

## Business areas deliberately deferred

```text
Advanced quote calculation
GST/tax calculation
Rate master
Automated Plum historical-rate import
External intelligence integrations
Generated quote/customer-format documents
Tender portal/source integrations
Full approval hierarchy
Customer Master finance integration
Equipment, vendor and crew scheduling optimization
GPS/fuel integration
Log sheet billing automation
Invoice/AR integration
Profitability analytics
```
