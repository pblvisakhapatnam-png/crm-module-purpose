# Lead Contract - Slice 2E Foundation

## Purpose

The Lead contract defines the first CRM Lead boundary. Leads are early sales enquiries and are not yet Qualified Prospects, Accounts, Opportunities or Work Orders.

Slice 2C adds controlled early Lead details update. Slice 2D adds repeatable Lead Activities / Follow-ups. Slice 2E adds Lead Qualification / Closure Decision without creating Account or Opportunity.

## Backend routes

```text
POST /api/leads
GET  /api/leads
GET  /api/leads/{public_id}
PUT  /api/leads/{public_id}
GET  /api/leads/{public_id}/activities
POST /api/leads/{public_id}/activities
POST /api/leads/{public_id}/qualification-decision
```

## Frontend routes

```text
/leads
/leads/new
/leads/[leadId]
```

`leadId` is the API `public_id`, backed by `crm_lead.lead_public_id`.

## Database record

```text
crm_lead
```

The Lead public identifier is `lead_public_id`. API responses expose it as `public_id`.

## Fields

```text
lead_source
source_reference
company_name
contact_name
contact_phone
contact_email
requirement_summary
lead_status_code
assigned_to_user_public_id
qualification_decision_notes
qualification_reason
qualification_decided_by
qualification_decided_at
created_by
created_at
updated_at
```

Slice 2E adds qualification decision fields to `crm_lead`. It does not create a separate qualification history table. The business event stream records each qualification/closure decision for audit purposes.

## Lead sources

```text
manual
email
phone
whatsapp
rfq
tender
external_intelligence
referral
website
other
```

## Lead statuses

Existing and seeded Lead statuses include:

```text
NEW
CONTACTED
REVIEW_PENDING
UNDER_REVIEW
QUALIFICATION_PENDING
QUALIFICATION_READY
QUALIFIED
UNQUALIFIED
DISQUALIFIED
CLOSED
CONVERTED
```

Lead create API allows only:

```text
NEW
REVIEW_PENDING
```

Lead early Lead details update allows only:

```text
NEW
CONTACTED
REVIEW_PENDING
UNDER_REVIEW
UNQUALIFIED
```

Qualification and conversion statuses are deliberately not exposed through the generic Lead Details update route. Slice 2E uses a separate qualification decision endpoint for qualification and closure statuses.

## Roles

```text
ADMIN / SALES_USER / SALES_MANAGER:
- create Leads
- list/view Leads
- update early Lead details fields
- create Lead Activities / Follow-ups
- record qualification and closure decisions
- convert a qualified Lead into an Account and Opportunity (Slice 3D; added here 7 October 2026,
  TB-1 TB1-904 - the grant, `LEAD_CONVERT`, has held these three roles since 3D)

FINANCE_USER / OPERATIONS_USER / MANAGEMENT_READ_ONLY:
- list/view Leads only
```

Backend permission checks are authoritative. Frontend role visibility is only a convenience.

## Business events

Lead creation records:

```text
LeadCreated
source_module = leads
record_type = lead
record_public_id = lead_public_id
```

Lead update records:

```text
LeadUpdated
```

If status changes, it also records:

```text
LeadStatusChanged
```

If assigned user changes, it also records:

```text
LeadAssigned
```

Lead Activities record:

```text
LeadActivityRecorded
```

Lead Qualification / Closure Decision records one of:

```text
LeadQualificationReady
LeadQualified
LeadUnqualified
LeadClosed
```

Event payload must not contain passwords, tokens or secrets.

## Explicit exclusions from Slice 2E

```text
Lead conversion to Account / Qualified Prospect
Opportunity creation
Duplicate Lead / Account matching
External intelligence direct integration
Tender ingestion
WhatsApp/email auto-import
Automated assignment rules or queues
Lead scoring
Activity edit/delete
Task/reminder workflow
```


## Slice 2D - Lead Activities / Follow-ups

Lead Activities are repeatable records linked to a Lead. They are distinct from Lead Details Update.

Routes:

```text
GET  /api/leads/{public_id}/activities
POST /api/leads/{public_id}/activities
```

Fields:

```text
activity_public_id
lead_public_id
activity_type
activity_at
notes
outcome
next_follow_up_at
created_by
created_at
```

Allowed activity types:

```text
CALL
EMAIL
WHATSAPP
MEETING
NOTE
OTHER
```

Business event:

```text
LeadActivityRecorded
```

Permissions:

```text
ADMIN / SALES_USER / SALES_MANAGER: create and view
FINANCE_USER / OPERATIONS_USER / MANAGEMENT_READ_ONLY: view only
```

Deferred:

```text
activity edit/delete
reminders
calendar integration
WhatsApp/email ingestion
task assignment workflow
```
## Date/time display rule

Backend/database timestamps may be stored or transmitted in UTC. User-facing CRM pages in this prototype should display date/time values in `Asia/Kolkata` / IST unless a later localisation requirement changes this.

A date and time a person types is India's time and is sent with its zone; the API refuses one without (11 October 2026: "Entered times", at the end of this contract).


## Slice 2E - Lead Qualification / Closure Decision

Slice 2E adds a controlled decision endpoint and frontend section for deciding whether a Lead should move forward, be marked ready for qualification, be unqualified, or be closed.

Route:

```text
POST /api/leads/{public_id}/qualification-decision
```

Request fields:

```text
decision_status_code
decision_notes
reason
```

Allowed decision statuses:

```text
QUALIFICATION_READY
QUALIFIED
UNQUALIFIED
CLOSED
```

Reason is required when the decision is:

```text
UNQUALIFIED
CLOSED
```

Explicit boundary:

```text
Slice 2E does not create Account, Qualified Prospect, Opportunity or Work Order records.
```


## Slice 3D - Lead Conversion to Account + Opportunity

Slice 3D adds controlled Lead conversion after the Opportunity foundation has been stabilized.

Backend route:

```text
POST /api/leads/{public_id}/convert
```

Conversion is allowed only when the Lead status is:

```text
QUALIFIED
```

Successful conversion performs one atomic backend workflow:

```text
1. Create an Account / business_party as QUALIFIED_PROSPECT.
2. Create an Opportunity with opportunity_source = lead_conversion.
3. Link Opportunity to the new Account through business_party_id.
4. Link Opportunity to the source Lead through source_lead_id.
5. Mark the Lead as CONVERTED.
```

The Lead response now also exposes derived conversion links when available:

```text
converted_account_public_id
converted_opportunity_public_id
```

These are derived from the linked Opportunity and are provided for operational navigation.

Request body is optional:

```text
account_name       optional; defaults to Lead company_name
opportunity_name   optional; defaults to Lead company_name + " Opportunity"
conversion_notes   optional; stored in events/source remarks, not as a separate history table
```

Response body:

```text
{
  "lead": {...},
  "account": {...},
  "opportunity": {...},
  "events": [...]
}
```

Events recorded:

```text
AccountCreated
OpportunityCreated
LeadConverted
```

Duplicate conversion control:

```text
- A Lead already in CONVERTED status cannot be converted again.
- A Lead that already has an Opportunity with source_lead_id cannot be converted again.
- Slice 3D adds a filtered unique SQL Server index on crm_opportunity.source_lead_id where source_lead_id is not null.
```

**A converted Lead is final (4 October 2026, TB-1 finding TB1-302).** Until then only the target status was checked,
so the details update could set a converted Lead back to New, Contacted, Review Pending, Under Review or Unqualified,
and a qualification decision to Qualification Ready, Qualified, Unqualified or Closed - against "a Lead already in
CONVERTED status" being final above. Now:

```text
PUT  /api/leads/{public_id}                        on a CONVERTED Lead -> 422, nothing changed, no event
POST /api/leads/{public_id}/qualification-decision on a CONVERTED Lead -> 422, nothing changed, no event
     "This Lead has been converted, so its details and qualification decision can no longer be changed.
      Work continues on its Account and Opportunity."
```

Both take the Lead's row lock (`SELECT ... FOR UPDATE`) before reading its status. A conversion writes CONVERTED with
an `UPDATE`, which takes the same lock, so an edit or decision that waits on it reads CONVERTED and is refused; one
that commits first is followed by the conversion's CONVERTED. Follow-up activities stay open on a converted Lead. The
Lead page shows the note in place of both forms. The Opportunity half of TB1-302 (Lost while an offer or Work Order is
live) waits for the Opportunity closure rules. No migration, no new route.

Explicit exclusions from Slice 3D:

```text
Existing Account matching / merge
PAN/GST duplicate matching
Credit checks or pre-qualification
Quote / Commercial Offer creation
Approval workflow
Work Order handoff
Customer activation / Customer Master finalization
```


## UI cleanup package (September 2026): display names

Recorded 11 September 2026. Additive, read-only fields so the screen can show a name instead of a
user public ID:

```text
LeadResponse   (GET /api/leads, GET /api/leads/{public_id}, and every response embedding a Lead:
                create, update, qualification decision and conversion)
    assigned_to_display_name   beside assigned_to_user_public_id
    created_by_display_name    beside created_by
```

Each field is `string | null`, resolved from `app_user.display_name` matched on
`app_user.public_id` (a LEFT JOIN in the same query), and `null` when the underlying ID is null or
does not match any user; the Lead is still returned in that case. `assigned_to_user_public_id` and
`created_by` are unchanged. `qualification_decided_by` is not resolved by this package. The Account
and Opportunity embedded in the conversion response carry their own display names; see the Account
and Opportunity contracts. No route, permission, request field, business event or migration change.

## Entered times (11 October 2026): a date and time carries its zone

`activity_at` and `next_follow_up_at` on `POST /api/leads/{public_id}/activities` take a date and time only with its
zone (`Z` or an offset such as `+05:30`), as ISO text - a number or digits are refused too; one with no zone is refused
with `422` ("Give the date and time with its time zone, ..."). Any offset is converted to UTC and stored as UTC; the
times in responses keep their form (UTC with no zone, shown in India's time). The Lead page sends the time typed as
India's time, whatever the browser's own zone - before, it used the browser's zone, which was right only in India. An
omitted `activity_at` is still the time of recording. This is an intentional tightening of the request contract: a
time with no zone was accepted before (read as UTC), and a caller that sent one must now send its zone; field names,
types and responses are otherwise unchanged. See
`commercial-offer-contract.md`, "Entered times", and `docs/agent/slices/entered-times-in-india.md`.
