# Non-Functional Baseline and Verification

## Authority and scope

This baseline reconciles the accepted ERP NFR source with the production architecture. It does
not claim the prototype currently meets these targets. Every production work package identifies
the applicable controls and evidence; TE-2C verifies the migrated foundation, while the final
production-candidate gate verifies the complete applicable baseline.

Primary source:
`docs/source/current/requirements/PBL_ERP_Non_Functional_Requirements_2026-05-19.docx`.
The derived reading aid is
`docs/reference/erp-source-extracts/ERP_NFR_FULL_TEXT_EXTRACT.md`.

## Baseline controls

| Area | Required baseline | Evidence/gate |
| --- | --- | --- |
| Performance | 95% of standard interactions respond within 2 seconds under the agreed normal-load profile; heavy reports/jobs run in background | API/browser timing and load-test report with dataset/user profile |
| Scale | Multi-branch and multi-year data; stable month-end, payroll and billing operation | Representative volume model, peak-load test and query/job monitoring |
| Availability | Deployment SLA must be stated; 99.5% monthly is the current minimum recommended source baseline unless an approved deployment agreement sets another target | Environment SLA, monitoring calculation and incident exclusions |
| Backup/restore | Automated backups and a tested restore procedure | Backup job evidence and dated restore exercise against a non-production environment |
| Disaster recovery | RPO and RTO are explicitly approved before production deployment | Recorded RPO/RTO, recovery runbook and timed exercise |
| Graceful degradation | External failure does not lose accepted work; retry/queue/fallback state is visible | Dependency-failure contract fixtures and recovery tests |
| Authentication | SSO-capable design; MFA for privileged users; configurable session timeout and session/device controls | Identity-provider configuration and security tests |
| Authorization | Backend module/action permissions, field controls where required, branch/site/project/customer data scope, and timely suspension after Employee Master leaver/position/scope changes | `ORA-001`, Employee Master change/recovery fixtures, permission inventory and negative/data-scope tests |
| Transport/storage security | TLS 1.2+; encryption at rest for financial and personal data; secrets outside source control | TLS/config evidence, storage encryption, secret scan and access review |
| Audit | User/time/action, before/after for sensitive changes, workflow decision/remarks, searchable by relevant dimensions | Business-event/audit tests, access-control tests and search UAT |
| Data integrity | Referential integrity, duplicate prevention, consistent configurable precision/rounding | Constraints, idempotency/concurrency tests and billing fixtures |
| Records | Configurable retention, archival/disposal, legal hold, version/tamper evidence and retrieval | Data-category policy plus archival/legal-hold tests before use |
| Privacy | Data minimization, personal-data access controls and access logging; support applicable Indian IT/DPDP/CERT-In obligations | Data classification, permission tests and privacy/security review |
| Monitoring | Health, jobs, integrations, retries and safe error diagnostics are visible | Dashboards/alerts, synthetic checks and failure drills |
| Mobile/field | Responsive/native field flows; secure document/photo/signature capture; store-and-forward where approved | Device testing and offline/sync conflict tests for each mobile slice |
| Accessibility/usability | Keyboard navigation, scaling, role-focused screens, efficient data entry and traceable drill-down | Accessibility scan plus role-based manual UAT |
| Upgrade/migration | Upgrade-safe extensions and controlled migration of master/open/historical records | Clean upgrades, rollback/recovery evidence and migration reconciliation |

## Required parameters before production deployment

The following are genuine environment/operating decisions, not blockers for TE-2A documentation
or pure-domain work:

- production availability SLA and approved maintenance exclusions;
- RPO and RTO;
- normal/peak concurrent-user, branch/site and data-volume profile;
- backup frequency, retention and restore-test frequency;
- maximum accepted age of the canonical HR/Organisation Reference snapshot/feed used by ORA (the
  provider-neutral freshness indicator defined in
  `docs/agent/pf-1f-hr/PF_1F_HR_CANONICAL_REFERENCE_MODEL.md`, "Source-unavailable / staleness
  behaviour" - it applies to whichever provider, Plum, SharePoint or later `NEW_SHARED_PLATFORM`,
  currently backs the canonical record; see ADR-032), and the controlled-import fallback
  activation/reconciliation time; the value must balance timely leaver/transfer enforcement
  against unnecessary approval outages; the fail-closed rule (a stale/unavailable feed blocks new
  authority-dependent decisions rather than defaulting to allow) is unchanged;
- support response/resolution targets and escalation matrix;
- data-category retention/disposal periods where not already fixed by law/contract; and
- mobile offline duration and conflict policy for each field workflow.

Engineering must state the current source recommendation and risk when asking for one of these values.

## TE-2C NFR gate

TE-2C is a migrated-foundation verification, not the final product acceptance. It must prove:

- CI executes the documented backend/frontend/migration/E2E path;
- representative standard interactions have a repeatable timing baseline;
- authentication/authorization, secret handling, TLS deployment design and dependency failure
  behavior are reviewed;
- backup and restore commands/runbook exist and one non-production restore is demonstrated where
  the target database/environment is available;
- logs, health checks, jobs and integration failures are diagnosable; and
- unresolved production parameters and residual risks are recorded without claiming compliance.

The final production-candidate gate repeats the applicable tests against production-like scale,
security, backup/DR and operational configuration.
