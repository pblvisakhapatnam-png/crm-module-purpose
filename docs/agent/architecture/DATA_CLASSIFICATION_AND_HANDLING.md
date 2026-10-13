# Data Classification and Handling

## Purpose

Define the minimum handling categories for contract design, fixtures, logs, events and module
snapshots. An owning module may apply a stricter category.

| Class | Examples in this programme | Minimum handling |
| --- | --- | --- |
| Restricted personal/statutory | Employee/vendor/customer PAN, Aadhaar where applicable, bank details, licence numbers/files, medical/fitness evidence, personal address/contact data, SurePass raw/returned evidence | Need-to-know access, encryption in transit/at rest, no real values in fixtures/logs/events, access audit, retention/legal-hold policy, masked UI/export where appropriate |
| Restricted authentication/security | Passwords, tokens, API keys, provider secrets, session material, recovery codes | Approved secret/identity store only; never business evidence, logs, events, documents or source control |
| Confidential financial/commercial | Credit limits/days, exposure components, supplier rates/costs, pricing evidence, billing results, invoice/tax context, approval thresholds | Role/data-scope access, audit sensitive changes, non-public fixtures, controlled exports and retention |
| Internal operational | Resource availability, assignment schedules, site/location, non-sensitive equipment/employee display references, workflow status | Authenticated role/scope access, integrity/version controls, avoid unnecessary replication |
| Public/approved external | Deliberately published product/service or statutory public reference data | May be shared only through an approved publication path; classification is explicit, not assumed |

## Master-reference rule

Resource planning may copy only the operational minimum from Employee Master: stable reference,
display name where required, active status, organization/designation or crew classification,
eligibility status/reference and relevant validity dates. It must not copy payroll, bank, Aadhaar,
medical, family, salary or unrelated HR fields.

ORA may copy only stable employee/user, organization-unit, position/reporting and incumbent/
effective-period references plus the Employee Master version needed to authorize and audit an
action. It must not become a second employee or organization directory, and authority events must
not expose unrelated HR change reasons or personal data.

Identity Validation exposes normalized accepted fields/status and evidence references. Provider raw
payloads stay inside the adapter/evidence boundary and are retained only when an approved audit or
statutory need justifies them.

## Fixtures, logs and events

- Use fictional values in committed fixtures and examples.
- Logs/errors contain safe identifiers and correlation references, not restricted payloads.
- Business events include only context needed by authorized consumers.
- Documents are referenced by protected public IDs; notification content does not embed restricted
  evidence by default.
- Every external integration contract names field classification, transport/storage protection and
  retention owner before implementation.
