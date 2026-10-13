# Slice 1J - Account Documents Linkage

## Objective

Connect the existing document metadata foundation to Account / `business_party` without implementing file upload or document approval.

## Included

- Account Documents section on the Account detail page.
- `GET /api/accounts/{public_id}/documents`.
- `POST /api/accounts/{public_id}/documents`.
- Document metadata stored in `document_metadata` with `linked_record_type = business_party`.
- Role-aware document metadata capture.
- Business event `AccountDocumentRecorded`.
- Backend tests for create/list, permissions, missing Account, and invalid document metadata.

## Excluded

- Actual file upload.
- File storage.
- Versioning beyond the simple `version_no` metadata field.
- Document expiry and reminders.
- OCR / AI document reading.
- Document approval / verification workflow.
- Finance statutory-document verification.

## Role treatment

Read Account Documents:

```text
ADMIN
SALES_USER
SALES_MANAGER
FINANCE_USER
OPERATIONS_USER
MANAGEMENT_READ_ONLY
```

Record Account Document metadata:

```text
ADMIN
SALES_USER
SALES_MANAGER
FINANCE_USER
```

Finance is included because statutory document metadata such as PAN/GST proof may later be handled by Accounts/Finance. Operations and read-only users can view but cannot record Account document metadata.

## Document metadata treatment

Allowed document types in this foundation slice:

```text
PAN
GST
KYC
RFQ
COMMERCIAL
OTHER
```

Allowed storage modes:

```text
external_link
future_sharepoint
```

Allowed statuses:

```text
Draft
Linked
```

`Verified`, `Rejected`, expiry and approval states are intentionally left for a later document workflow slice.

## Event rule

Successful Account document metadata capture emits:

```text
event_name   = AccountDocumentRecorded
source_module = accounts
record_type  = document_metadata
record_public_id = document_public_id
```

The payload includes Account public id, document type, storage mode and status.
