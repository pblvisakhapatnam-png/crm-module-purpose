# Opportunity Contract - Slice 3A/3B/3C Foundation

## Purpose

The Opportunity contract defines the first CRM Opportunity boundary. An Opportunity is a potential business pursuit that can later lead to a quote/commercial offer and eventually one or more Work Orders.

Slice 3A establishes Opportunity as its own foundation object. Slice 3B stabilizes the read-only Opportunity detail/profile shell. Slice 3C adds controlled update and early stage movement for foundation fields. Slice 3D creates linked Opportunities through controlled Lead conversion. These slices deliberately do not implement quote/commercial offer, approval, credit checks, or Work Order handoff.

## Backend routes

```text
POST /api/opportunities
GET  /api/opportunities
GET  /api/opportunities/{public_id}
PUT  /api/opportunities/{public_id}
POST /api/opportunities/{public_id}/account-repair
```

## Frontend routes

```text
/opportunities
/opportunities/new
/opportunities/[opportunityId]
```

`opportunityId` is the API `public_id`, backed by `crm_opportunity.opportunity_public_id`.

## Database record

```text
crm_opportunity
```

The Opportunity public identifier is `opportunity_public_id`. API responses expose it as `public_id`.

Slice 3C requires no database migration. It updates fields already created by Slice 3A.

## Fields

```text
opportunity_name
opportunity_source
source_reference
account_public_id              response only in current foundation slices; nullable
source_lead_public_id          response only in current foundation slices; nullable
customer_requirement_summary
estimated_value
expected_close_date
opportunity_status_code
owner_user_public_id
created_by
created_at
updated_at
```

The database also includes nullable internal link columns:

```text
business_party_id
source_lead_id
```

These columns are present to preserve the future path from Lead conversion and Account linkage. Slice 3A manual Opportunity creation does not populate them. Slice 3C does not edit them. Slice 3D populates them only through the controlled Lead conversion workflow.

## Opportunity sources

```text
manual
lead_conversion
rfq
tender
repeat_enquiry
account_review
external_intelligence
other
```

`lead_conversion` is reserved for a later slice. The current foundation does not implement Lead conversion even though the source code is reserved for contract stability.

Manual create/edit UI does not offer `lead_conversion`; that source should be set only by a future conversion workflow.

*Reconciled 12 October 2026:* Lead conversion has existed since Slice 3D (below). It sets `lead_conversion`
(`leads/service.py`), and the manual form still does not offer it. "Lead conversion" in the deferred and excluded lists
further down is likewise Slice 3D's; those lists describe Slices 3A to 3C. `WON` and `CLOSED` are still never set by
any code: neither an offer's outcome nor a Work Order moves the Opportunity.

## Opportunity statuses

Seeded Opportunity workflow statuses are:

```text
NEW
NEEDS_REVIEW
QUALIFIED
QUOTE_PENDING
ON_HOLD
WON
LOST
CLOSED
```

Create API allows only:

```text
NEW
NEEDS_REVIEW
```

Slice 3C update/stage API allows early-stage movement only:

```text
NEW
NEEDS_REVIEW
QUALIFIED
QUOTE_PENDING
ON_HOLD
LOST
```

`WON` and `CLOSED` remain deferred until quote/commercial offer, award, closure and Work Order handoff rules are designed.

## Roles

```text
ADMIN / SALES_USER / SALES_MANAGER:
- create Opportunities
- list/view Opportunities
- update foundation fields and early stage/status
- repair missing Account linkage when an Opportunity has no Account

FINANCE_USER / OPERATIONS_USER / MANAGEMENT_READ_ONLY:
- list/view Opportunities only
```

Backend permission checks are authoritative. Frontend role visibility is only a convenience.

Business event viewing remains controlled by the Events module route:

```text
GET /api/events/recent
```

The Opportunity profile may show a link to the Events page only for roles that can access that page. It must not bypass Events module permissions.

## Slice 6B.1 Account repair route

Slice 6B.1 adds a controlled Account repair endpoint for Opportunities where `business_party_id` is null:

```text
POST /api/opportunities/{public_id}/account-repair
```

The request must provide exactly one of:

```json
{ "account_public_id": "existing-account-public-id" }
```

or:

```json
{
  "create_account": {
    "account_name": "Minimal Qualified Prospect",
    "legal_name": "optional",
    "segment": "optional",
    "industry": "optional",
    "source_remarks": "optional"
  }
}
```

Rules:

- Existing Account repair links the Opportunity to the selected Account / `business_party`.
- Minimal Account repair creates a `QUALIFIED_PROSPECT` Account / `business_party` and links it to the Opportunity.
- Account in this flow does not mean Customer Master.
- Already-linked Opportunities are rejected; this slice does not implement relinking or Account merge.
- Read-only, Finance and Operations roles are rejected by backend authorization.

Expected failures:

```text
403 unauthorized role
404 Opportunity not found
422 missing repair path, both repair paths supplied, missing selected Account, or already-linked Opportunity
```

## Business events

Opportunity creation records:

```text
OpportunityCreated
source_module = opportunities
record_type = opportunity
record_public_id = opportunity_public_id
```

Opportunity update records:

```text
OpportunityUpdated
source_module = opportunities
record_type = opportunity
record_public_id = opportunity_public_id
```

If status changes during the update, the update also records:

```text
OpportunityStageChanged
source_module = opportunities
record_type = opportunity
record_public_id = opportunity_public_id
status_before = previous opportunity_status_code
status_after = new opportunity_status_code
```

Event payload must not contain passwords, tokens or secrets.

Opportunity Account repair records:

```text
OpportunityAccountRepaired
source_module = opportunities
record_type = opportunity
record_public_id = opportunity_public_id
```

If the repair creates a minimal/provisional Account / Qualified Prospect, that Account creation also records `AccountCreated` against `record_type = business_party`.

## Slice 3B/3C profile shell sections

The Opportunity detail page should present these sections:

```text
Profile snapshot
Workflow position
Account context
Source / enquiry context
Customer requirement
Commercial readiness
Next workflow boundaries
Audit and traceability
```

Slice 3C adds an edit form for Sales/Admin roles. Read-only roles continue to see the profile without update actions.

The shell should clearly state that the following are deferred:

```text
Lead conversion
Quote / Commercial Offer creation
Approval workflow
Credit checks
Work Order handoff
WON/CLOSED outcome handling
```

## Explicit exclusions from current Opportunity foundation slices

```text
Lead conversion to Account / Qualified Prospect
Lead conversion to Opportunity
Account linkage workflow
Quote / Commercial Offer creation
Approval workflow
Credit checks or exposure consumption
Work Order creation or handoff
Duplicate matching
Assignment queues
Task/reminder workflow
Tender ingestion
WhatsApp/email auto-import
```

## Date/time display rule

Backend/database timestamps may be stored or transmitted in UTC. User-facing CRM pages in this prototype should display date/time values in the local business time used by PBL users, currently Asia/Kolkata, without repeatedly appending a timezone label beside every timestamp.

## UI navigation consistency carry-forward

Back / return navigation should be positioned consistently across operational pages. In Slice 3B, Opportunity Detail shows â€œBack to Opportunitiesâ€ inline near the page actions, while Business Events shows â€œBack to Opportunityâ€ at the top-right. This is acceptable for the foundation, but future slices should standardize page-level navigation placement, preferably using a common page action/header pattern.


## Slice 3D Lead conversion linkage

Lead conversion is exposed from the Lead module, not as a generic Opportunity create/update action.

Conversion-created Opportunities use:

```text
opportunity_source = lead_conversion
opportunity_status_code = QUALIFIED
business_party_id = created Account / business_party id
source_lead_id = converted Lead id
```

Manual Opportunity create/update UI must continue not to offer `lead_conversion` as a normal user-selectable source.

Slice 3D also adds a filtered unique database index so one Lead can have at most one conversion-created Opportunity link through `source_lead_id`.

## Slice 4A Commercial Offer linkage

Commercial Offer / Quote foundation is implemented as a separate object under:

```text
/api/commercial-offers
crm_commercial_offer
```

Each Commercial Offer links to one Opportunity through `opportunity_id` internally and `opportunity_public_id` in API responses. Account context is carried from the Opportunity where an Account link exists.

Opportunity status is not automatically changed by Slice 4A offer creation. Later slices may introduce controlled offer submission and Opportunity stage movement.


## UI cleanup package (September 2026): display names

Recorded 11 September 2026. Additive, read-only fields so the screen can show a name instead of a
user public ID:

```text
OpportunityResponse   (GET /api/opportunities, GET /api/opportunities/{public_id}, and every
                       response embedding an Opportunity: create, update, Account repair and
                       Lead conversion)
    owner_display_name        beside owner_user_public_id
    created_by_display_name   beside created_by
```

Each field is `string | null`, resolved from `app_user.display_name` matched on
`app_user.public_id` (a LEFT JOIN in the same query), and `null` when the underlying ID is null or
does not match any user; the Opportunity is still returned in that case. `owner_user_public_id`
and `created_by` are unchanged. No route, permission, request field, business event or migration
change.
