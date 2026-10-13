# Account / business_party Contract

## Naming rule

The user-facing name is:

```text
Account
```

The internal domain/database name is:

```text
business_party
```

This distinction is intentional.

Use `Account` in UI labels, user help, routes, and business-facing documentation where appropriate.

Use `business_party` for database table names, internal record type references, and internal module design where precision is needed.

## Business meaning

An Account represents a long-lived business party known to PBL.

At the early stage, the Account may be only a Qualified Prospect. It becomes a Customer only after the first Work Order is received and the finance/statutory activation process is completed.

## Lifecycle statuses

The Account lifecycle uses the workflow status foundation from Slice 0E.

Minimum expected statuses:

```text
DRAFT
QUALIFIED_PROSPECT
CUSTOMER_ACTIVATION_PENDING
CUSTOMER_ACTIVE
BLACKLISTED
```

The seeded `workflow_status.module` for these statuses is:

```text
business_party
```

## Creation rules

An Account / Qualified Prospect may be created when:

1. PBL has received an enquiry, RFQ, tender, or other business approach; or
2. PBL has a formal vendor/customer registration with the party and an enquiry is received or expected; or
3. a reviewed external intelligence source is manually accepted for follow-up.

Direct Customer creation is not the normal starting point.

A Customer Master / active customer state should come later, after first Work Order and finance approval.

## Credit governance note

PAN-level credit governance is important, but Slice 1B does not implement credit checks.

Future slices must preserve these principles:

- credit pre-qualification is recorded before commercial commitment;
- submitted quotes/tender bids create potential exposure;
- Work Orders create firm exposure;
- sales users cannot silently bypass credit controls.

## Data model

Slice 1A created the `business_party` table.

Minimum persisted columns:

```text
id
business_party_public_id
party_type
account_name
legal_name
pan
gstin
account_status_code
qualification_source
account_owner_user_public_id
segment
industry
source_remarks
created_by
created_at
updated_at
```

## Slice 1B API contract

Slice 1B adds backend Account API routes using the existing `business_party` table.

No database schema change is required for Slice 1B.

### Route summary

```text
POST /api/accounts
GET  /api/accounts
GET  /api/accounts/{public_id}
```

`GET /api/accounts/{public_id}` is included because it is small and useful for confirming created records without requiring a frontend screen.

### POST /api/accounts

Creates one Account record in `business_party`.

Allowed Slice 1B creation statuses:

```text
DRAFT
QUALIFIED_PROSPECT
```

Customer activation statuses must not be directly created through this API in Slice 1B.

Request fields:

```text
party_type                       optional; defaults to organization; Slice 1B supports organization only
account_name                     required
legal_name                       optional
pan                              optional; if provided, must be valid PAN format
gstin                            optional; if provided, must be valid GSTIN format
account_status_code              optional; defaults to DRAFT; only DRAFT or QUALIFIED_PROSPECT allowed
qualification_source             optional; defaults to manual
account_owner_user_public_id      optional; defaults to current authenticated user where available
segment                          optional
industry                         optional
source_remarks                   optional
```

Allowed `qualification_source` values in Slice 1B:

```text
manual
enquiry
rfq
tender
registration
external_intelligence
```

Response body:

```text
{
  "account": {
    "public_id": "...",
    "party_type": "organization",
    "account_name": "...",
    "legal_name": "...",
    "pan": "...",
    "gstin": "...",
    "account_status_code": "DRAFT",
    "qualification_source": "manual",
    "account_owner_user_public_id": "...",
    "segment": "...",
    "industry": "...",
    "source_remarks": "...",
    "created_by": "...",
    "created_at": "...",
    "updated_at": "..."
  },
  "event": {
    "public_id": "...",
    "event_name": "AccountCreated",
    "record_type": "business_party",
    "record_public_id": "..."
  }
}
```

Business event rule:

- Account creation records `AccountCreated` in `business_event`.
- `source_module` is `accounts`.
- `record_type` is `business_party`.
- `record_public_id` is the created `business_party_public_id`.
- Event payload must not include passwords, tokens, secrets, or unnecessary statutory identifiers.

### GET /api/accounts

Lists recent Accounts from `business_party`.

Supported query parameters:

```text
limit        optional; default 20; min 1; max 100
offset       optional; default 0; min 0; used for simple list pagination
status_code  optional; filters by account_status_code when provided
```

Sort order:

```text
created_at DESC, id DESC
```

Response body:

```text
[
  {
    "public_id": "...",
    "party_type": "organization",
    "account_name": "...",
    "legal_name": "...",
    "pan": "...",
    "gstin": "...",
    "account_status_code": "DRAFT",
    "qualification_source": "manual",
    "account_owner_user_public_id": "...",
    "segment": "...",
    "industry": "...",
    "source_remarks": "...",
    "created_by": "...",
    "created_at": "...",
    "updated_at": "..."
  }
]
```

### GET /api/accounts/{public_id}

Returns one Account by `business_party_public_id`.

Expected responses:

```text
200  Account found
404  Account not found
422  Invalid UUID path value
```

## Authorization rule for Slice 1B

Create Account:

```text
ADMIN
SALES_USER
SALES_MANAGER
```

Read/list Account:

```text
ADMIN
SALES_USER
SALES_MANAGER
FINANCE_USER
OPERATIONS_USER
MANAGEMENT_READ_ONLY
```

Events/audit access remains separate and Admin/management-read-only controlled by the existing Events API.

## What Slice 1B does not implement

- Account frontend create/list UI;
- lead conversion;
- opportunity creation;
- customer activation;
- credit limit checks;
- PAN/GSTN duplicate workflow beyond format validation;
- document linkage UI;
- file upload.

Those belong in later Slice 1 parts.
## Slice 1C frontend consumption contract

Slice 1C adds a minimal frontend Account list UI. It does not change the backend Account API.

Frontend route:

```text
/accounts
```

API consumed:

```text
GET /api/accounts?limit=20
```

Frontend rules:

```text
Use relative API paths for Account API calls.
Read the browser token from pbl_auth_token.
Send Authorization: Bearer <token>.
Show loading, empty, success and error states.
Do not display PAN/GSTIN in the minimal list view unless a later PAN/GST role-aware UI slice explicitly allows it.
Do not add create/edit/detail behavior in Slice 1C.
```

Displayed list fields:

```text
account_name
legal_name
public_id
account_status_code
qualification_source
segment
industry
account_owner_user_public_id
created_at
```

## Slice 1D frontend create behavior

Slice 1D adds a minimal frontend create page at:

```text
/accounts/new
```

The page consumes the existing Slice 1B route:

```text
POST /api/accounts
```

The frontend must use:

```text
Authorization: Bearer <pbl_auth_token>
relative API path: /api/accounts
```

Slice 1D frontend-supported create fields are:

```text
account_name             required
legal_name               optional
account_status_code      DRAFT or QUALIFIED_PROSPECT only
qualification_source     manual, enquiry, rfq, tender, registration, external_intelligence
segment                  optional
industry                 optional
source_remarks           optional
```

The frontend sends:

```text
party_type = organization
```

PAN and GSTIN are deliberately excluded from the Slice 1D create UI. They belong to a later PAN/GST workflow/tab with clearer role and validation treatment.

After successful creation, the UI shows the created Account public ID, status, qualification source, owner, created timestamp and `AccountCreated` business event reference.

The frontend must show user-friendly validation and permission errors and must not display raw JSON response bodies in the normal UI.

## Slice 1E frontend detail/profile shell

Slice 1E adds a read-only frontend Account detail/profile shell.

Browser route:

```text
/accounts/<public_id>
```

Frontend implementation path:

```text
frontend/app/accounts/[accountId]/page.tsx
```

In this route, `accountId` is treated as the Account `public_id`.

API used:

```text
GET /api/accounts/{public_id}
```

Frontend behaviour:

- Account list rows link to the detail shell by public ID.
- The detail shell reads the browser token from `pbl_auth_token`.
- The detail shell uses a relative API path.
- The detail shell displays existing Slice 1B Account response fields only.
- The detail shell does not implement edit, contacts, addresses, PAN/GST, documents or events.
- Backend read permissions remain authoritative.
- Frontend error states must be user-friendly and must not expose raw stack traces, tokens or unnecessary technical response bodies.

## Slice 1F frontend list behaviour

Slice 1F establishes the first reusable list-screen pattern for Account records.

Pagination:

```text
The frontend page size is 20 records.
The frontend may request limit=21 so it can display 20 records and determine whether a next page exists.
The backend response remains a plain list of Account records; total count is intentionally not added in Slice 1F.
Previous and Next controls are based on offset and page size.
```

Session-viewed link state:

```text
The Account list should visually indicate Account records opened during the current login session.
This state must reset on logout and on a new login.
This state must not depend on the browser native :visited history, because browser visited-link history is outside the application session model.
```

The frontend uses browser `sessionStorage` for this prototype-only per-login-session viewed state. This is a UI aid only and is not business audit evidence.

## Slice 1G Account Contact API contract

User-facing term: Account Contact.
Internal/database term: `business_party_contact`.

### Data ownership

Contacts are subordinate records of an Account / `business_party`. A Contact must not exist without an owning Account.

### Table

`business_party_contact`

Minimum fields:

- `id` internal integer primary key.
- `contact_public_id` public UUID string.
- `business_party_id` foreign key to `business_party.id`.
- `contact_name` required.
- `designation`, `department`, `phone`, `email`, `is_primary`, `is_active`, `remarks`.
- `created_by`, `created_at`, `updated_at`.

### API routes

```text
GET  /api/accounts/{public_id}/contacts
POST /api/accounts/{public_id}/contacts
```

### Create request

```json
{
  "contact_name": "Contact Person",
  "designation": "Procurement Manager",
  "department": "Commercial",
  "phone": "+91-9876543210",
  "email": "person@example.com",
  "is_primary": true,
  "remarks": "Optional remarks"
}
```

### Response

`POST` returns:

```json
{
  "contact": {
    "public_id": "...",
    "account_public_id": "...",
    "contact_name": "Contact Person",
    "designation": "Procurement Manager",
    "department": "Commercial",
    "phone": "+91-9876543210",
    "email": "person@example.com",
    "is_primary": true,
    "is_active": true,
    "remarks": "Optional remarks",
    "created_by": "...",
    "created_at": "...",
    "updated_at": "..."
  },
  "event": {
    "public_id": "...",
    "event_name": "AccountContactCreated",
    "record_type": "business_party_contact",
    "record_public_id": "..."
  }
}
```

### Roles

Read Contacts:

- `ADMIN`
- `SALES_USER`
- `SALES_MANAGER`
- `FINANCE_USER`
- `OPERATIONS_USER`
- `MANAGEMENT_READ_ONLY`

Create Contacts:

- `ADMIN`
- `SALES_USER`
- `SALES_MANAGER`

Backend role enforcement is authoritative. Frontend action visibility must also respect these roles.

### Events

Creating a Contact emits `AccountContactCreated` with:

- `source_module = accounts`
- `record_type = business_party_contact`
- `record_public_id = contact_public_id`
- payload `account_public_id`, `contact_public_id` and `is_primary` - never the contact's name.

**Changed 7 October 2026 (TB-1 TB1-202, owner's decision).** Until then the payload carried
`contact_name`. A business contact's name is personal contact data, which
`docs/agent/architecture/DATA_CLASSIFICATION_AND_HANDLING.md` keeps out of events, and the event log
cannot be corrected afterwards; the name stays on the contact record, which the event's
`record_public_id` and `contact_public_id` point to. Events already stored are left as they are
(the pilots hold invented data). From the same date no Account event - created, classification,
contact, address, PAN profile, GSTIN or document - copies the user's own text (remarks, source
remarks, classification notes) into the event's `remarks`: what a user types there can hold a PAN,
a GSTIN or a name. The text stays on the record it was sent with.
`backend/tests/test_tb1_202_account_event_payloads.py` holds every Account event to an allowlist of
payload keys and to fixed text in its other arguments.

### Slice 1G exclusions

- Contact edit/delete.
- Contact duplicate detection.
- Contact approval workflow.
- Contact import.
- Contact activity history.
- Opportunity or Lead linkage.

---

## Slice 1H Account Address API

Slice 1H adds CRM Account address create/list endpoints under the Account API.

### Routes

```text
GET  /api/accounts/{public_id}/addresses
POST /api/accounts/{public_id}/addresses
```

### Address request fields

```text
address_type_code: REGISTERED_OFFICE | COMMUNICATION | SITE | BILLING_DRAFT | OTHER
address_line1: required
address_line2: optional
city: required
 district: optional
state: required
postal_code: optional
country_code: two-letter code, default IN
is_primary: boolean, default false
remarks: optional
```

### Business rules

- Addresses are linked to `business_party` through `business_party_address`.
- Address create is allowed only for Admin, Sales User and Sales Manager.
- Finance, Operations and Read Only users may view but not create.
- `BILLING_DRAFT` is draft CRM information only and is not Finance-approved billing master data.
- A successful address create records `AccountAddressCreated` against record type `business_party_address`.

### Out of scope

- Address edit/delete.
- Duplicate address checks.
- Finance approval.
- GSTN-wise billing address control.
- Customer Master activation.
- Work Order site address rules.


## Slice 1I - PAN / GST API Contract

Slice 1I adds early-stage statutory capture under Account.

### Tables

- `business_party_tax_profile` stores one Account-level PAN profile.
- `business_party_gstin` stores one or more GSTIN rows for an Account.

### Routes

```text
GET  /api/accounts/{public_id}/tax-profile
POST /api/accounts/{public_id}/tax-profile
POST /api/accounts/{public_id}/gstins
```

### Events

Saving the PAN profile emits `AccountTaxProfileCaptured`, whose payload records only that a PAN is
present (`pan_present`) and its verification state. Adding a GSTIN emits `AccountGstinCaptured`
(`record_type = business_party_gstin`, `record_public_id` = the GSTIN's public id) with the payload
`account_public_id`, `gstin_public_id`, `state_code`, `gstin_verification_state_code` and
`is_primary` - never the GSTIN itself, not even masked: characters 3 to 12 of a GSTIN are its
holder's PAN. Changed 7 October 2026 (TB-1 TB1-202, owner's decision); until then the payload
carried `gstin`. Events already stored are left as they are.

### Verification states

```text
NOT_AVAILABLE
ENTERED_NOT_VERIFIED
VERIFICATION_PENDING
VERIFIED
REJECTED_INCORRECT
NOT_REQUIRED_YET
```

### Important boundary

PAN/GST data captured here is CRM-stage Account information only. It must not be treated as Finance-approved Customer Master data until a later Finance approval / Customer Master activation workflow is implemented.

### Role treatment

Admin, Sales User and Sales Manager can capture draft PAN/GST details in Slice 1I using non-final verification states. Finance / Accounts can capture/update PAN/GST details and can set final verification states such as VERIFIED or REJECTED_INCORRECT. Operations and Read-only users can view but cannot add/update.

> **Superseded as architectural direction.** The paragraph above and the Slice 1I hardening note
> below remain an accurate record of what the prototype implements today, and are preserved for
> that reason. They are **not** the intended production design. Manual Finance / Accounts setting
> of final verification states is superseded by integration-driven validation; see
> "Production direction: integration-driven legal identity validation" later in this file, and
> `docs/agent/ARCHITECTURE_DECISIONS.md` ADR-014 / ADR-015.


## Slice 1I hardening note

PAN/GST capture and verification are separated. Sales/Admin/Sales Manager roles may capture draft tax details using non-final states such as ENTERED_NOT_VERIFIED or VERIFICATION_PENDING. Finance / Accounts role is responsible for setting VERIFIED or REJECTED_INCORRECT states. Multiple GSTIN rows with the same GST state code are allowed in the CRM-stage register because Indian GST rules allow separate registrations for multiple places of business within a State/Union territory in permitted cases. Exact duplicate GSTIN values remain blocked. PAN/GST form success and error messages should appear below the relevant Save/Add button, not only at the top of the PAN/GST section.

## PAN/GST feedback and duplicate handling

- Exact duplicate GSTIN values should be rejected or shown as already recorded for the Account.
- Multiple different GSTIN values with the same state code are not blocked in Slice 1I.
- User-facing validation should show specific backend details where available and useful.
- PAN/GST messages should be local to the relevant action and should clear when the user edits the relevant field.

## Production direction: integration-driven legal identity validation

Status: approved architecture direction, recorded 11 August 2026 as `ADR-015` in
`docs/agent/ARCHITECTURE_DECISIONS.md`. **Not yet implemented.** Nothing in this section changes
current prototype behaviour, current routes, current schema or current permissions. It records
the target design so that a future slice does not extend the superseded manual-approval model.

### Superseded assumption

```text
A newly created Account / Qualified Prospect is routed to Accounts/Finance for PAN/GST
verification and approval before the Account is confirmed.
```

### Target behaviour

PAN and GSTIN captured against an Account are passed to PBL's existing **SurePass** integration
for validation. Where the service supports it, the validated response is used to obtain or
confirm authoritative legal-entity information such as legal/entity name, PAN details, GST
registration details and status, registered/legal address, and other relevant identity fields
returned by the service.

A routine manual Accounts/Finance approval step is **not** required to reconfirm information
SurePass has already successfully validated. Human review is exception-driven only:

```text
PAN/GST mismatch
validation failure
incomplete or ambiguous response
prolonged provider unavailability requiring the authorized manual route
policy-defined exception
```

Do not describe SurePass, or any third-party validation service, as granting business approval.
It validates facts. Business approvals remain separate where required.

### Verification state

The Account is not modelled as simply approved or not approved. Target conceptual states:

```text
UNVERIFIED
VERIFICATION_PENDING
VERIFIED
VERIFICATION_EXCEPTION
```

The implementing slice should reconcile these with the existing Slice 1I states above
(`NOT_AVAILABLE`, `ENTERED_NOT_VERIFIED`, `VERIFICATION_PENDING`, `VERIFIED`,
`REJECTED_INCORRECT`, `NOT_REQUIRED_YET`) rather than introducing a parallel vocabulary. Exact
enum names may be adjusted to fit existing repository conventions.

A temporary SurePass outage must not prevent an Account / Qualified Prospect record from
existing or hard-block downstream operational work. Keep the Account pending/unverified and
record the outage, retries and eventual result. This non-blocking availability rule does not
apply to a failed validation, invalid identifier or SurePass-returned mismatch; those remain
identity exceptions. Prolonged or permanent unavailability uses an authorized, audited manual
validation route defined by PBL until service is restored.

### Verification evidence

Retain, subject to data minimisation:

```text
verification status
verification timestamp
source/provider = SurePass
external/reference/request ID where available
validated PAN/GST identifiers
returned legal name/address/details as appropriate
mismatch/exception reason
```

Do not persist unnecessary third-party payload data merely because the provider returns it.

SurePass-returned legal identity values are authoritative for the Account Master. Preserve
user-entered and customer-document values plus any mismatch as evidence. If Work Order identity
data conflicts with SurePass, correct/revalidate an incorrectly entered PAN first; if the PAN is
correct, obtain a corrected Work Order before treating that document as identity-consistent.

Evidence-retention duration and any periodic re-verification interval/trigger are authorized
policy parameters. Their values remain deferred and must not be invented by the implementing
slice.

### Ownership at onboarding

```text
Sales (SALES_USER / SALES_MANAGER)   initiates the Account / Qualified Prospect and may
                                     prepare a credit proposal
SurePass                             validates legal identity
CREDIT_ASSESSOR authority            performs the credit assessment
                                     (initial/default mapping: SALES_MANAGER)
CREDIT_APPROVER authority            approves credit limit / credit days under configurable
                                     authority; currently the applicable Department Head or
                                     Managing Director
Accounts / Finance                   consumes the validated legal master and the financial/exposure
                                     information, without a redundant PAN/GST approval step
```

Account / Qualified Prospect initiation is unchanged by this direction and remains available to
the existing authorized Sales roles under this contract's create-role set (`ADMIN`, `SALES_USER`,
`SALES_MANAGER`).

Accounts is the default owner of the identity-verification exception queue. Authorized Sales
personnel may also be assigned. Queue ownership must be configurable by authorized personnel.

Credit assessment is authorized through the configurable `CREDIT_ASSESSOR` business authority
defined in `ORA-001`: an authenticated user holding a current, active assignment for the relevant
organizational/data scope. `SALES_MANAGER` is the initial/default mapping, preserving the agreed
current operating arrangement and migration compatibility; once ORA assignments are active,
authorized administrators may assign, suspend, revoke or reassign the authority without a code
change, so the application role alone is not the permanent authorization rule. Preparing a
proposal is not performing the assessment. Do not assume Accounts/Finance owns that assessment or
its approval merely because the subject matter is credit. Actual financial exposure against
approved credit remains a separate concern that Finance/Accounts may consume and monitor.

Business authority is not implied by administrative access: maintaining authority assignments and
exercising `CREDIT_ASSESSOR` are separate capabilities, and `ADMIN` is not a permanent implicit
assessor.

The `CREDIT_ASSESSOR` authority is also where the business function PBL describes as "Pre-Sales"
lands for the current scope; no Pre-Sales application role is added. A later multi-source Lead
ingestion and pre-sales vetting slice may propose a dedicated pre-sales module, workflow or role,
but must do so through an explicit role/permission and contract change rather than extending this
direction by implication.

The CRM Account Master's legal-entity/PAN-level credit profile is authoritative for approved
Credit Amount and Credit Days. Sales may prepare a proposal; the `CREDIT_ASSESSOR` authority
performs the assessment. The eligible approver is policy-configured under `CREDIT_APPROVER`; the
applicable Department Head or Managing Director makes the decision while authenticated. The
Account Credit Profile service activates approved values from that decision; Sales cannot assert
another person's approval. Named assessors and approvers, delegated thresholds and any future
maker/checker requirement are configuration, not hard-coded workflow rules.

Store the authenticated assessor identity and the `CREDIT_ASSESSOR` authority assignment/version
relied on as assessment evidence, and the authenticated approver identity, role/authority at the
time, decision, timestamp, reference and conditions as approval evidence. Never store passwords,
authentication secrets or reusable credentials as evidence.

### Unchanged by this direction

The `Important boundary` above still holds: CRM-stage PAN/GST data is not Finance-approved
Customer Master data. Customer Master activation remains a separate, Finance-approved step at
first Work Order, before Work Order release/posting. PAN-level credit governance, the distinction
between Potential Exposure and Firm Exposure, the `Account` / `business_party` naming rule,
backend-authoritative authorization and audit/traceability requirements are all unchanged.


---

## Slice 1J Account Documents Linkage Contract

User-facing term: Account Document.
Stored record: `document_metadata`.
Account link: `linked_record_type = business_party` and `linked_record_public_id = business_party_public_id`.

### Routes

```text
GET  /api/accounts/{public_id}/documents
POST /api/accounts/{public_id}/documents
```

### Create request

```json
{
  "document_type": "KYC",
  "file_name": "customer-kyc.pdf",
  "original_file_name": "customer-kyc.pdf",
  "storage_mode": "external_link",
  "storage_path_or_url": "https://example.invalid/customer-kyc.pdf",
  "version_no": 1,
  "status": "Linked",
  "remarks": "Optional remarks"
}
```

### Allowed values

Document types:

```text
PAN
GST
KYC
RFQ
COMMERCIAL
OTHER
```

Storage modes in Slice 1J:

```text
external_link
future_sharepoint
```

Statuses in Slice 1J:

```text
Draft
Linked
```

`Verified`, `Rejected`, expiry and approval states are intentionally excluded from Slice 1J.

### Response

`POST` returns:

```json
{
  "document": {
    "public_id": "...",
    "account_public_id": "...",
    "document_type": "KYC",
    "file_name": "customer-kyc.pdf",
    "original_file_name": "customer-kyc.pdf",
    "storage_mode": "external_link",
    "storage_path_or_url": "https://example.invalid/customer-kyc.pdf",
    "version_no": 1,
    "status": "Linked",
    "uploaded_by": "...",
    "uploaded_at": "...",
    "remarks": "Optional remarks"
  },
  "event": {
    "public_id": "...",
    "event_name": "AccountDocumentRecorded",
    "record_type": "document_metadata",
    "record_public_id": "..."
  }
}
```

### Roles

Read Account Documents:

- `ADMIN`
- `SALES_USER`
- `SALES_MANAGER`
- `FINANCE_USER`
- `OPERATIONS_USER`
- `MANAGEMENT_READ_ONLY`

Record Account Document metadata:

- `ADMIN`
- `SALES_USER`
- `SALES_MANAGER`
- `FINANCE_USER`

Backend enforcement is authoritative. Frontend action visibility must also respect these roles.

### Event

Creating an Account Document metadata row emits `AccountDocumentRecorded` with:

- `source_module = accounts`;
- `record_type = document_metadata`;
- `record_public_id = document_public_id`;
- payload containing at least `account_public_id`, `document_type`, `storage_mode`, and `status`.

### Slice 1J exclusions

- Actual file upload.
- File storage provider integration.
- Document version lifecycle beyond the simple metadata `version_no`.
- Document expiry/reminder.
- OCR/AI document reading.
- Document approval/verification workflow.
- Finance-approved statutory document validation tied to Customer Master activation.


---

## Slice 1K Account Ownership / Classification Contract

User-facing term: Account Ownership / Classification.
Stored record: `business_party`.

### Routes

```text
GET /api/accounts/{public_id}/classification
PUT /api/accounts/{public_id}/classification
```

### Update request

```json
{
  "account_owner_user_public_id": "optional-user-public-id",
  "segment": "Key Account",
  "industry": "Infrastructure",
  "is_strategic_account": true,
  "classification_notes": "Optional notes"
}
```

### Response

`GET` returns the classification object.

`PUT` returns:

```json
{
  "classification": {
    "account_public_id": "...",
    "account_owner_user_public_id": "...",
    "segment": "Key Account",
    "industry": "Infrastructure",
    "is_strategic_account": true,
    "classification_notes": "Optional notes",
    "updated_at": "..."
  },
  "event": {
    "public_id": "...",
    "event_name": "AccountClassificationUpdated",
    "record_type": "business_party",
    "record_public_id": "..."
  }
}
```

### Roles

Read Account classification:

- `ADMIN`
- `SALES_USER`
- `SALES_MANAGER`
- `FINANCE_USER`
- `OPERATIONS_USER`
- `MANAGEMENT_READ_ONLY`

Update Account classification:

- `ADMIN`
- `SALES_USER`
- `SALES_MANAGER`

Backend enforcement is authoritative. Frontend action visibility must also respect these roles.

### Event

Updating Account classification emits `AccountClassificationUpdated` with:

- `source_module = accounts`;
- `record_type = business_party`;
- `record_public_id = business_party_public_id`;
- payload containing owner before/after, segment, industry and strategic flag.

### Slice 1K exclusions

- Owner user picker.
- Sales hierarchy validation.
- Territory assignment.
- Account reassignment approval.
- Account scoring.
- Duplicate Account merge.
- Customer Master ownership.


---

## Slice 1L Account Foundation Stabilization

Slice 1L closes the Account foundation group and defines the working rules for future agents.

### Foundation Slice Mode

Foundation slices are guardrail slices. They should establish database shape, route/API shape, permissions, events, minimal UI and acceptance documentation without attempting full business completeness.

Detailed validation and UX hardening should be deferred unless the issue affects:

- security or backend permission enforcement;
- data model correctness;
- Alembic migration correctness;
- route/API contract stability;
- business event/audit integrity;
- a reusable pattern that future agents are likely to copy.

### Account foundation route families established

```text
POST /api/accounts
GET  /api/accounts
GET  /api/accounts/{public_id}

GET  /api/accounts/{public_id}/contacts
POST /api/accounts/{public_id}/contacts

GET  /api/accounts/{public_id}/addresses
POST /api/accounts/{public_id}/addresses

GET  /api/accounts/{public_id}/tax-profile
POST /api/accounts/{public_id}/tax-profile
POST /api/accounts/{public_id}/gstins

GET  /api/accounts/{public_id}/documents
POST /api/accounts/{public_id}/documents

GET /api/accounts/{public_id}/classification
PUT /api/accounts/{public_id}/classification
```

### UI action-feedback rule

For future Account, Lead, Opportunity, Quote and Work Order screens, success/error feedback for create/update actions must appear below or next to the relevant action button. Do not rely only on top-of-section messages in long forms.

### Backend refresh rule

When backend route/schema/service/repository files change, rebuild/recreate the backend container before manual testing, even when no Alembic migration is added.

### Next module boundary

Lead Foundation should use Account / Qualified Prospect as the long-lived business-party context. It must not implement Customer Master activation, quote creation or external intelligence automation in its first foundation slice.


## Slice 3D Lead conversion Account creation

Slice 3D may create an Account / business_party from a qualified Lead. The created Account represents a Qualified Prospect, not an activated Customer.

Conversion-created Accounts use:

```text
party_type = organization
account_status_code = QUALIFIED_PROSPECT
qualification_source = mapped from Lead source
account_name = Lead company_name unless conversion payload overrides it
source_remarks = conversion note and source Lead reference
```

Slice 3D does not implement existing Account matching, PAN/GST duplicate checks, credit checks, customer activation, or Customer Master finalization. Those remain later governance slices.


## UI cleanup package (September 2026): display names

Recorded 11 September 2026. Account responses exposed people only as user public IDs, so the
screen showed a UUID for "Owner" and "Created by". This package adds read-only display-name fields
beside those IDs:

```text
AccountResponse   (GET /api/accounts, GET /api/accounts/{public_id}, POST /api/accounts, and the
                   Account embedded in the Lead conversion and Opportunity Account repair responses)
    account_owner_display_name   beside account_owner_user_public_id
    created_by_display_name      beside created_by

AccountClassificationResponse   (GET and PUT /api/accounts/{public_id}/classification)
    account_owner_display_name   beside account_owner_user_public_id
```

Rules:

- Additive and read-only. Each field is `string | null` and is never accepted on a request.
- Resolved from `app_user.display_name`, matched on `app_user.public_id`, in the same query as the
  record (a LEFT JOIN, following the Slice 9E quotation `generated_by_display_name` precedent).
- `null` when the underlying ID is null or does not match any user. The Account itself is still
  returned; an unresolvable ID never drops it from a list.
- `account_owner_user_public_id` and `created_by` are unchanged and remain the identifiers.
- No route, permission, request field, business event or migration change.
