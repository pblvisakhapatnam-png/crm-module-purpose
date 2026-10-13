# Slice 1J Acceptance - Account Documents Linkage

## Standard foundation-slice checks

- Backend tests pass.
- Frontend build passes.
- Existing Account Contacts, Addresses and PAN/GST sections still load.
- Account list pagination and viewed-this-session marker behavior are not intentionally changed.

## Backend acceptance

- `GET /api/accounts/{public_id}/documents` requires authentication.
- Read roles can list Account Documents.
- `POST /api/accounts/{public_id}/documents` is allowed for Admin, Sales User, Sales Manager and Finance User.
- Operations and read-only users cannot record document metadata.
- Missing Account returns 404.
- Invalid document type/status returns 422.
- Successful create stores metadata in `document_metadata` using `linked_record_type = business_party` and `linked_record_public_id = Account public id`.
- Successful create records `AccountDocumentRecorded`.
- Response and event payload must not leak passwords, tokens or secrets.

## Frontend acceptance

- Account detail page shows a Documents section.
- Existing documents are listed.
- Allowed roles see a Record Document Metadata form.
- Disallowed roles can view the section but cannot see the create form.
- User can record a simple document metadata row with document type, file/reference name, storage mode, version and status.
- Success/error feedback is visible near the document form.

## Out of scope acceptance notes for later agents

Later document agents must separately handle:

- file upload;
- storage provider integration;
- document version lifecycle;
- expiry and reminder rules;
- document approval / verification workflow;
- statutory document checks tied to Finance-controlled Customer Master activation.
