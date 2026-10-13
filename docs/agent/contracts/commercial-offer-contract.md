# Commercial Offer / Quote Contract - Slice 4A Foundation

## Purpose

The Commercial Offer / Quote contract defines the first commercial response boundary after Opportunity.

A Commercial Offer represents either:

```text
- a Plum/system-generated quote; or
- an external/customer/tender-format commercial response recorded in the system.
```

Slice 4A creates only the foundation object. It deliberately does not implement quote line items, rate master, approval workflow, Commercial Offer credit/exposure gates against already-approved credit amount and credit days, submission, award capture, Work Order handoff or billing logic.

## Backend routes

```text
POST /api/commercial-offers
GET  /api/commercial-offers
GET  /api/commercial-offers/{public_id}
PUT  /api/commercial-offers/{public_id}
```

## Frontend routes

```text
/commercial-offers
/commercial-offers/new
/commercial-offers/[commercialOfferId]
```

`commercialOfferId` is the API `public_id`, backed by `crm_commercial_offer.offer_public_id`.

## Database record

```text
crm_commercial_offer
```

The Commercial Offer public identifier is `offer_public_id`. API responses expose it as `public_id`.

The visible offer number/code is:

```text
offer_code
```

Slice 4A generates codes in this prototype using the `CO-000001` style. Slice 9F retains that code for the whole
series and displays immutable versions as `CO-000001 v1`, `CO-000001 v2`, and so on. Production numbering policy
beyond this implemented series rule remains deferred.

## Fields

```text
offer_code                         response only
action public id                    public_id / offer_public_id
opportunity_public_id               required on create
account_public_id                   response only; derived from linked Opportunity where present
offer_title
offer_mode
offer_type
offer_status_code
offer_value
currency_code
offer_date
valid_until
remarks
created_by
created_at
updated_at
```

The database stores internal link columns:

```text
opportunity_id
business_party_id
```

`business_party_id` is copied from the linked Opportunity at offer creation where the Opportunity already has an Account link. Slice 4A does not implement separate Account relinking.

## Offer modes

```text
plum_generated
external_tender
customer_format
budgetary_response
other
```

This keeps one object for both Plum-generated quotes and externally submitted tender/customer formats.

## Offer types

```text
budgetary
firm
tender_response
revision
other
```

Slice 4A allows these values for foundation capture only. Revision lifecycle handling is deferred.

## Offer statuses

Seeded Commercial Offer workflow statuses are:

```text
DRAFT
READY_FOR_REVIEW
SUBMITTED
REVISED
ABANDONED
WITHDRAWN
ACCEPTED
REJECTED
CLOSED
```

Create API allows only:

```text
DRAFT
```

Slice 4C update API allows early foundation movement only:

```text
DRAFT
READY_FOR_REVIEW
WITHDRAWN
```

Submission, revision, approval, acceptance/rejection and closure transitions are deferred.

## Roles

```text
ADMIN / SALES_USER / SALES_MANAGER:
- create Commercial Offers
- list/view Commercial Offers

FINANCE_USER / OPERATIONS_USER / MANAGEMENT_READ_ONLY:
- list/view Commercial Offers only
```

*Reconciled 7 October 2026 (TB-1 TB1-904):* the block above is the Slice 4A position. Since Slice 4D
`OPERATIONS_USER` also records pricing evidence and may select the basis rate
(`COMMERCIAL_OFFER_PRICING_EVIDENCE_WRITE`, which also governs attaching a file to an offer - see
`DEFERRED_REQUIREMENTS.md`); later slices added their own codes. The current grants are those in
`backend/app/modules/authorization/contract.py`.

Backend permission checks are authoritative. Frontend role visibility is only a convenience.

Business event viewing remains controlled by the Events module route:

```text
GET /api/events/recent
```

## Business events

Commercial Offer creation records:

```text
CommercialOfferCreated
source_module = commercial_offers
record_type = commercial_offer
record_public_id = offer_public_id
status_after = DRAFT
```

Commercial Offer update records:

```text
CommercialOfferUpdated
CommercialOfferStatusChanged, only when offer_status_code changes
```

Event payload may include public Opportunity/Account IDs and non-sensitive offer metadata. It must not contain passwords, tokens or secrets.

## Slice 4A profile shell sections

The Commercial Offer detail page should present these sections:

```text
Profile snapshot
Opportunity context
Account context
Commercial values
Next workflow boundaries
Audit and traceability
```

## Explicit exclusions from Slice 4A

```text
Quote line items
Rate master
Revision management
Submission workflow
Approval workflow
Credit checks or exposure consumption
Tender award/acceptance capture
Work Order creation or handoff
Billing, OT, breakdown or invoice logic
```

## Date/time display rule

Backend/database timestamps may be stored or transmitted in UTC. User-facing CRM pages in this prototype should display date/time values in the local business time used by PBL users, currently Asia/Kolkata, without repeatedly appending a timezone label beside every timestamp.

A date and time a person types is India's time and is sent with its zone; the API refuses one without (11 October 2026: "Entered times", at the end of this contract).

## UI navigation consistency carry-forward

Back / return navigation should be positioned consistently across operational pages. Slice 4A follows the current page-action placement pattern but a later UI cleanup should introduce a common page-header/action component.

## Commercial Offer Account Context Fix

Commercial Offer profile/read responses must show Account context when it is available through the linked Opportunity. The Commercial Offer row may carry its own copied `business_party_id`; if that value is missing, API reads should fall back to the linked Opportunity `business_party_id`.

This is a read/display consistency fix only. Slice 4A still does not implement separate Account relinking from the Commercial Offer screen.

<!-- SLICE_4B_PROFILE_SHELL_START -->
## Slice 4B profile shell refinement

Slice 4B refines the Commercial Offer detail page as a read-only profile shell.

The profile should show:

```text
Offer snapshot
Opportunity context
Account context
Commercial summary
Remarks / requirement notes
Workflow position
Deferred boundaries
Audit and traceability
```

Slice 4B does not change the backend routes, database schema or Commercial Offer event model.

The detail page must continue to show Account context only when the linked Opportunity has Account context available through the API. If the linked Opportunity has no Account, the profile should clearly show that no Account is linked yet.
<!-- SLICE_4B_PROFILE_SHELL_END -->

## Future pricing evidence display

Commercial Offer profile and detail contracts must leave room for pricing evidence used to prepare the offer. Later slices should model and display:

- Multiple market rates collected by Operations for the same Commercial Offer requirement.
- The selected basis rate used in the Commercial Offer, which need not be the lowest market rate.
- The reason for selecting that basis rate.
- Relevant historical Plum rates for similar requirement, route, customer, equipment category, work type or commercial context.
- Comparison between collected market rates, selected basis rate and historical Plum rates.

Slice 4B only adds read-only placeholders. It does not create the market-rate or historical-rate data model.

<!-- SLICE_4C_UPDATE_STATUS_START -->
## Slice 4C update and status foundation

Slice 4C adds controlled Commercial Offer update through:

```text
PUT /api/commercial-offers/{public_id}
```

Editable foundation fields are:

```text
offer_title
offer_mode
offer_type
offer_status_code
offer_value
currency_code
offer_date
valid_until
remarks
```

Only Sales/Admin roles can update. Finance, Operations and Management Read Only roles remain read-only.

Slice 4C allows only DRAFT, READY_FOR_REVIEW and WITHDRAWN as update targets. Submitted, Revised, Accepted, Rejected and Closed remain deferred until the relevant submission, revision, approval, award and closure rules are implemented.
<!-- SLICE_4C_UPDATE_STATUS_END -->


<!-- SLICE_4D_PRICING_EVIDENCE_START -->
## Slice 4D pricing evidence foundation

Slice 4D adds pricing evidence linked to Commercial Offers.

Backend routes:

```text
GET  /api/commercial-offers/{public_id}/pricing-evidence
POST /api/commercial-offers/{public_id}/pricing-evidence
POST /api/commercial-offers/{public_id}/pricing-evidence/{evidence_public_id}/select-basis
```

Database record:

```text
crm_commercial_offer_pricing_evidence
```

Evidence types:

```text
market_rate
historical_plum_rate
```

Foundation fields:

```text
public_id / evidence_public_id
commercial_offer_public_id
evidence_type
source_name
vendor_contact
equipment_service_description
rate_amount
currency_code
rate_basis
collected_by_name
collected_at
source_reference
is_selected_basis
selection_reason
comparison_notes
created_by
created_at
updated_at
```

The contract allows multiple pricing evidence entries per Commercial Offer. Only one entry can be selected as the basis rate for the Commercial Offer.

The selected basis rate need not be the lowest collected market rate. Selection rationale should explain the commercial reason, such as availability, reliability, matching scope, risk, customer requirement, mobilisation or strategic account treatment.

Historical Plum-rate comparison is manual in Slice 4D. Automated Plum extraction is deferred.

*Changed 11 October 2026 by Slice 4G:* pricing evidence now belongs to one offer line, and the basis rate is chosen per
line, with each line's basis history. "Only one entry can be selected as the basis rate for the Commercial Offer" now
holds only for rates recorded for the whole offer before that change. See "Slice 4G (11 October 2026): market rates per
offer line" at the end of this contract.
<!-- SLICE_4D_PRICING_EVIDENCE_END -->

<!-- SLICE_4E_LINE_SCOPE_START -->
## Slice 4E Commercial Offer line/scope foundation

Slice 4E adds stable Commercial Offer line identity and basic line-level scope capture.

Backend routes:

```text
GET  /api/commercial-offers/{public_id}/lines
POST /api/commercial-offers/{public_id}/lines
PUT  /api/commercial-offers/{public_id}/lines/{line_public_id}
```

Database record:

```text
crm_commercial_offer_line
```

Foundation fields:

```text
public_id / line_public_id
commercial_offer_public_id
line_number
line_status_code
scope_description
equipment_service_category
quantity
uom
rate_amount
currency_code
line_amount
remarks
created_by
created_at
updated_at
```

Line status values in this foundation are:

```text
ACTIVE
CANCELLED
```

The line amount is a simple transparent product of quantity and rate amount when rate amount is captured. It is not a final quote calculation engine. GST, taxes, minimum hours, extra hours, extra KM, fuel terms, crew terms, mobilization/demobilization, billing terms and other detailed commercial rules remain deferred.

Future agents must preserve this line identity because later modules need to attach or derive from it:

```text
- offer-level T&C selection/customization;
- offer-line-level T&C selection/customization;
- approval/deviation workflow;
- submitted quote/tender version lines;
- accepted/awarded lines;
- Work Order lines;
- billing/log-sheet line traceability.
```

T&C master, clause customization, new-clause approval and deviation workflow are explicitly deferred. They must attach to Commercial Offer header and Commercial Offer line records rather than replacing the line foundation.
<!-- SLICE_4E_LINE_SCOPE_END -->



## Slice 4F lifecycle closure fields

Commercial Offer now carries thin lifecycle fields:

- `submitted_at`
- `submission_reference`
- `submission_proof_note`
- `outcome_date`
- `outcome_remarks`

Allowed lifecycle statuses in the Slice 4F update foundation are:

- `DRAFT`
- `READY_FOR_REVIEW`
- `SUBMITTED`
- `WITHDRAWN`
- `ACCEPTED`
- `REJECTED`
- `CLOSED`

This was the Slice 4F position. Slice 9F now uses `REVISED` for a submitted predecessor replaced by a later submitted
version and `ABANDONED` for a preparation version intentionally stopped before submission.

Credit/exposure note: Commercial Offer submission must later run an exposure/availability gate against already-approved Account/PAN credit amount and credit days. This is not the initial prospect credit assessment.

## Slice 6A linked Work Order traceability

The Commercial Offer profile now displays Work Order shell(s) generated from the offer through the Slice 5A handoff route.

Frontend behaviour:

```text
- Load linked Work Orders through GET /api/work-orders?commercial_offer_public_id={commercial_offer_public_id}.
- Show linked WO code, status, customer WO reference, received date, source offer status and created timestamp.
- Provide CO -> WO navigation with a safe return path back to the originating Commercial Offer.
- Pass safe return paths when navigating from Commercial Offer to linked Opportunity or Account.
```

This is navigation and traceability stabilization only. It does not implement WO release/posting, Customer Master activation, equipment assignment, crew assignment, log sheets, billing or approval workflow.

## Slice 6A.1 Account traceability guard

Commercial Offer read/list responses continue to expose:

```text
account_public_id
```

The value is derived from the Commercial Offer copied `business_party_id` or, when that copy is missing, from the linked Opportunity `business_party_id`.

Backend lifecycle validation now blocks these status movements when `account_public_id` is missing:

```text
SUBMITTED
ACCEPTED
```

Expected response:

```text
422 Unprocessable Entity
```

The user-facing message must refer to `Account` and should explain that Account traceability must be repaired through the existing Opportunity / Lead / Account flow. Internal/domain wording may refer to `business_party`.

This guard does not create Customer Master activation, Finance approval, Work Order release/posting, equipment assignment, crew assignment, log sheets, billing or a new Account relinking workflow.

## Slice 6B.1 Opportunity Account repair and actionability guard

Slice 6B.1 preserves the Slice 6A.1 Account traceability guard and adds a controlled repair path on the linked Opportunity.

Commercial Offer creation now enforces one active/actionable Commercial Offer per Opportunity until formal Commercial Offer revision/versioning and Opportunity lines exist.

For this foundation slice, active/actionable means any existing Commercial Offer for the same Opportunity whose status is not one of:

```text
WITHDRAWN
REJECTED
CLOSED
```

Therefore these existing statuses block creating another foundation Commercial Offer for the same Opportunity:

```text
DRAFT
READY_FOR_REVIEW
SUBMITTED
REVISED
ACCEPTED
```

*Reconciled 12 October 2026:* `REVISED` no longer blocks. Since Slice 9F it marks a sent version replaced by a later
one, and the statuses that do not block are `COMMERCIAL_OFFER_INACTIVE_FOR_NEW_OFFER_STATUSES` = `WITHDRAWN`,
`REJECTED`, `CLOSED`, `REVISED`, `ABANDONED`. A later version still in preparation does not count either. The rule is
held by the database (the CS-05c and Slice 9F sections below).

Expected create failure:

```text
422 Unprocessable Entity
```

The message should identify that an active/actionable Commercial Offer already exists and include the existing offer code/public id where possible so the UI can route the user to the existing Commercial Offer.

Frontend create behavior:

```text
- When an Opportunity is selected or prefilled, check existing Commercial Offers for that Opportunity.
- If an active/actionable offer exists, show a link and route normal create action to that offer.
- Do not create a second unrelated Commercial Offer for the same Opportunity through normal UI action.
```

This slice does not implement formal Commercial Offer revision/versioning, Opportunity lines or production Commercial Offer numbering.

## Slice 6D.1 Accepted Offer to Work Order handoff freeze

Slice 6D.1 freezes the logical handoff contract from Accepted Commercial Offer to Work Order shell:

```text
docs/agent/contracts/accepted-offer-to-work-order-handoff-contract.md
```

Commercial Offer changes after this point must preserve these handoff fields and meanings:

```text
- Commercial Offer public ID and offer code/number.
- Commercial Offer accepted/awarded status and accepted date/reference.
- Opportunity public ID.
- Account public ID and display name.
- offer mode.
- Commercial Offer version/reference where implemented.
- Commercial Offer line public IDs and stable line sequence.
- selected/awarded line status.
- pricing evidence references where implemented.
- submitted/accepted document metadata where implemented.
- Commercial Offer credit/exposure approval reference where applicable.
- source status and event references.
```

The current prototype remains thinner than the production MVP target, but future agents must not break the stable identifiers or line identity that Work Order handoff depends on.

## Slice 6E T&C clause library foundation

Slice 6E adds a read-only Terms and Conditions clause library under:

```text
GET /api/tc-clauses
GET /api/tc-clauses/{public_id}
/terms-and-conditions
```

The T&C library contains source-derived prototype/test clause records only. They are not final legal-approved clauses.

Slice 6E does not attach clauses to Commercial Offer headers or Commercial Offer lines. It does not add clause modification, deviation approval, legal versioning, quote document generation or any change to the Accepted Offer -> Work Order handoff contract.

## Slice 6F Commercial Offer header T&C attachment foundation

Slice 6F adds header-level T&C attachment to Commercial Offers.

Backend routes:

```text
GET    /api/commercial-offers/{public_id}/tc-clauses
POST   /api/commercial-offers/{public_id}/tc-clauses
DELETE /api/commercial-offers/{public_id}/tc-clauses/{attachment_public_id}
```

Database record:

```text
commercial_offer_tc_clause
```

Foundation fields:

```text
public_id
commercial_offer_public_id
tc_clause_public_id
clause_id_snapshot
title_snapshot
clause_text_snapshot
business_line_snapshot
clause_category_snapshot
source_clause_number_snapshot
source_reference_snapshot
mandatory_default_snapshot
risk_category_snapshot
applies_to_header_snapshot
applies_to_line_snapshot
requires_approval_if_omitted_snapshot
requires_approval_if_modified_snapshot
sort_order
active
attached_by
created_at
updated_at
```

Rules:

```text
- Only active T&C library clauses may be attached.
- Slice 6F attaches to Commercial Offer header only, so clauses must be header-applicable.
- Duplicate active attachment of the same library clause to the same Commercial Offer is rejected.
- Removing an attachment soft-removes it from the active list; it does not delete the T&C library clause.
- Snapshot fields preserve the selected library clause wording and flags at attachment time.
```

Roles:

```text
ADMIN / SALES_USER / SALES_MANAGER:
- view, attach and remove Commercial Offer header T&C clauses

FINANCE_USER / OPERATIONS_USER / MANAGEMENT_READ_ONLY:
- view Commercial Offer header T&C clauses only
```

Business events:

```text
CommercialOfferTcClauseAttached
CommercialOfferTcClauseRemoved
```

Slice 6F does not implement line-level T&C selection, clause text editing inside Commercial Offer, deviation/new-clause approval, approval for omitted mandatory clauses, quote/PDF generation, legal versioning, SharePoint/document automation, Work Order release/posting or any change to the frozen Accepted Offer -> Work Order handoff contract.

## Slice 6G Commercial Offer T&C readiness and recommended clauses

Slice 6G adds recommended header-level T&C readiness on the Commercial Offer profile.

Backend routes:

```text
GET  /api/commercial-offers/{public_id}/tc-clause-readiness
POST /api/commercial-offers/{public_id}/tc-clauses/attach-recommended
```

Read access follows Commercial Offer read roles.

Attach recommended access follows the existing Commercial Offer header T&C write roles:

```text
ADMIN / SALES_USER / SALES_MANAGER
```

Readiness response fields include:

```text
commercial_offer_public_id
recommendation_basis
total_recommended_count
attached_recommended_count
missing_recommended_count
attached_optional_count
status_text
deferral_notes
recommended_clauses[]
```

Recommended clause status values:

```text
ATTACHED
NOT_ATTACHED
```

Rules:

```text
- The recommendation basis is explicit: TRANSPORTATION or HIRING.
- `business_line` is accepted as an alias for `recommendation_basis`.
- Only active, header-applicable library clauses are recommended.
- `attach-recommended` attaches only missing recommended clauses.
- `attach-recommended` is idempotent when all recommended clauses are already attached.
- Attachment snapshots and attach events reuse the Slice 6F mechanism.
- The readiness view is guidance only and is not legal approval.
```

Slice 6G does not block Commercial Offer submission. It does not implement line-level T&C, clause editing, omitted mandatory approval, deviation/new-clause approval, quote/PDF generation, legal versioning, SharePoint/document automation, billing, Work Order release/posting or any change to the frozen Accepted Offer -> Work Order handoff contract.

## Slice 6H Commercial Offer submission readiness checklist

Slice 6H adds one advisory readiness endpoint for customer-facing Commercial Offer submission preparation.

Backend route:

```text
GET /api/commercial-offers/{public_id}/submission-readiness
```

Optional query:

```text
recommendation_basis = HIRING | TRANSPORTATION
```

`recommendation_basis` is used only to assess header T&C readiness through the Slice 6G logic. It is not persisted as a Commercial Offer classification.

Read access follows Commercial Offer read roles.

Response fields include:

```text
commercial_offer_public_id
readiness_status
summary
checklist_items[]
```

Overall readiness status values:

```text
READY
ATTENTION_REQUIRED
NOT_READY
```

Checklist item status values:

```text
PASS
ATTENTION_REQUIRED
BLOCKING
DEFERRED
```

Checklist items cover:

```text
- Commercial Offer active/actionable status.
- Account traceability.
- Opportunity traceability.
- active Commercial Offer lines.
- pricing evidence presence.
- header T&C readiness.
- deferred Commercial Offer credit/exposure gate.
- deferred approval workflow.
- deferred quote/PDF/document generation.
- deferred submission proof.
```

The route is read-only and must not create `business_event` rows.

Slice 6H is advisory readiness guidance only. It does not add a new hard submission block, does not implement actual quote submission, does not generate quote/PDF documents, does not capture submission proof, does not calculate credit/exposure, does not approve the offer or T&C wording, does not add line-level T&C and does not change the frozen Accepted Offer -> Work Order handoff contract.

## Slice 6I Commercial Offer submission evidence foundation

Slice 6I adds metadata-only evidence records for Commercial Offers that have been submitted or shared with the customer.

Backend routes:

```text
GET  /api/commercial-offers/{public_id}/submission-evidence
POST /api/commercial-offers/{public_id}/submission-evidence
```

Database record:

```text
commercial_offer_submission_evidence
```

Foundation fields:

```text
public_id
commercial_offer_public_id
submission_reference
submission_channel
submitted_at
submitted_by
recipient_summary
submitted_amount_snapshot
submitted_currency_snapshot
submitted_version_snapshot
document_reference_label
document_reference_url_or_path
evidence_notes
active
created_by
created_at
updated_at
```

Allowed submission channels:

```text
EMAIL
PORTAL
HAND_DELIVERY
CUSTOMER_FORMAT_UPLOAD
TENDER_PORTAL
OTHER
```

Rules:

```text
- One Commercial Offer may have multiple submission evidence records over time.
- Evidence records capture metadata and traceability only.
- Document reference fields are metadata for externally managed documents, not application file upload/storage.
- Creating evidence records a CommercialOfferSubmissionEvidenceRecorded business_event.
- Reading evidence does not create business_event rows.
- Recording evidence does not automatically change Commercial Offer lifecycle status in Slice 6I.
- Submitted/shared offers are treated as commercially committed for future exposure/control work, but exposure calculation remains deferred.
```

Roles:

```text
ADMIN / SALES_USER / SALES_MANAGER:
- view and add submission evidence

FINANCE_USER / OPERATIONS_USER / MANAGEMENT_READ_ONLY:
- view submission evidence only
```

Slice 6I updates `GET /api/commercial-offers/{public_id}/submission-readiness` with a `SUBMISSION_EVIDENCE` checklist row. Evidence present is `PASS`; missing evidence is `ATTENTION_REQUIRED`. The checklist still treats quote/PDF generation and submission proof upload/storage as deferred future controls and remains advisory, not hard-blocking.

Slice 6I does not implement quote/PDF generation, file upload/storage, SharePoint automation, credit exposure calculation, approval workflow, omitted mandatory T&C approval, deviation/new-clause approval, line-level T&C selection, legal versioning, Work Order release/posting, billing, Customer Master activation or any change to the frozen Slice 6D.1 Accepted Offer -> Work Order handoff contract.

## Slice 6I.2 Commercial Offer manual credit/exposure readiness

Slice 6I.2 adds append-only manual credit/exposure review evidence.

Backend routes:

```text
GET  /api/commercial-offers/{public_id}/credit-review
POST /api/commercial-offers/{public_id}/credit-review
```

Database record:

```text
commercial_offer_credit_review
```

Review statuses:

```text
NOT_ASSESSED
WITHIN_LIMIT_AS_PER_MANUAL_REVIEW
APPROVAL_REQUIRED
APPROVED_WITH_REFERENCE
REJECTED_OR_ON_HOLD
```

One Commercial Offer may have multiple review records. A new record supersedes the previous active record without deleting history. The latest active review drives `CREDIT_EXPOSURE_REVIEW` in `GET /submission-readiness`.

Creating a review records `CommercialOfferCreditReviewRecorded`. Reads do not create events. Create access follows Commercial Offer manage roles; view access follows Commercial Offer read roles.

This is manual readiness evidence only. It does not calculate exposure, consume Account/PAN credit, aggregate ledger/WIP/open-offer/open-Work-Order balances, run Finance approval workflow, block submission, change lifecycle status or alter the frozen Accepted Offer -> Work Order handoff contract.

## Slice 6J controlled submission / commercial commitment

Slice 6J adds:

```text
POST /api/commercial-offers/{public_id}/mark-submitted
```

The action is the authoritative path from `DRAFT` or `READY_FOR_REVIEW` into `SUBMITTED`. Generic PUT updates cannot newly select `SUBMITTED`.

Required guards are manage-role authorization, Account and Opportunity traceability, at least one active line, at least one submission evidence record and no current `REJECTED_OR_ON_HOLD` manual credit review. Missing/not-assessed/approval-required review remains a warning only. T&C readiness remains advisory.

Successful action records `CommercialOfferCommerciallyCommitted`, updates existing submitted date/reference fields from the latest evidence and returns the updated offer, event and warnings. It does not create evidence, generate/send documents, calculate exposure, complete approval, create/release a Work Order or change the frozen Slice 6D.1 handoff contract.

## Slice 6K revision / resubmission traceability

Slice 6K adds metadata-only revision/resubmission records after controlled commercial submission.

Backend routes:

```text
GET  /api/commercial-offers/{public_id}/revisions
POST /api/commercial-offers/{public_id}/revisions
POST /api/commercial-offers/{public_id}/revisions/{revision_public_id}/mark-resubmitted
POST /api/commercial-offers/{public_id}/revisions/{revision_public_id}/cancel
```

Database record: `commercial_offer_revision`. Statuses are `OPEN`, `RESUBMITTED` and `CANCELLED`.

Historically, only `SUBMITTED` Commercial Offers could open a revision in this foundation. Slice 9F retires creation
of new in-place revision cycles: `POST /revisions` now returns a business refusal directing Sales to **Make a new
version**. Existing OPEN legacy records remain listable and may be marked resubmitted or cancelled so deployed data is
not stranded. Source and resubmission evidence references on those legacy actions must still identify active evidence
belonging to the same Commercial Offer.

Only `OPEN` revisions can transition, once, to `RESUBMITTED` or `CANCELLED`. Revision reads create no events. Actions create:

```text
CommercialOfferRevisionOpened
CommercialOfferRevisionResubmitted
CommercialOfferRevisionCancelled
```

Submission Readiness retains advisory `REVISION_RESUBMISSION_TRACEABILITY` for legacy records. An open legacy revision
warns that resubmission evidence is not yet recorded; a latest Resubmitted revision reports positive evidence.

Slice 6K did not clone Commercial Offers. Slice 9F now supplies the immutable copy/version mechanism while preserving
the frozen Slice 6D.1 handoff contract. Comparison, legal approval and calculated exposure remain separate work.

## Slice 6L customer response / award outcome traceability

Slice 6L adds append-only post-submission customer response records through:

```text
GET  /api/commercial-offers/{public_id}/customer-responses
POST /api/commercial-offers/{public_id}/customer-responses
```

The database record is `commercial_offer_customer_response`. Outcomes are `ACCEPTED_AWARDED`, `REJECTED_LOST`, `REVISION_REQUESTED`, `CLARIFICATION_REQUESTED`, `ON_HOLD`, `PENDING_CUSTOMER_DECISION` and `OTHER`. Channels are `EMAIL`, `TENDER_PORTAL`, `CUSTOMER_PO`, `LETTER_OF_AWARD`, `PHONE_OR_VERBAL`, `MEETING` and `OTHER`.

Creation is allowed only for `SUBMITTED` or `ACCEPTED` offers. Linked submission evidence and revisions must belong to the same offer. Accepted/awarded aligns status to `ACCEPTED`; rejected/lost aligns status to `REJECTED`; other outcomes preserve status.

**Historical note, dated 7 September 2026.** From Slice 6L until Slice 9B this sentence read "`SUBMITTED`, `ACCEPTED` or `REJECTED`". `REJECTED` was removed by explicit PBL decision because it allowed a rejected offer to be reactivated to `ACCEPTED` by a late award while a replacement offer already existed for the same Opportunity. See the Slice 9B section at the end of this contract.

Creation emits `CommercialOfferCustomerResponseRecorded`; reads emit no events. Submission Readiness includes advisory `CUSTOMER_RESPONSE_AWARD_OUTCOME`. No automatic Work Order, Customer Master activation, approval, release/posting, billing/execution, document automation or frozen Slice 6D.1 handoff change is introduced.

**CS-04 part 1, 8 October 2026 (owner's decision; the dated amendment of the frozen handoff contract).** While the
offer has a Work Order, `REJECTED_LOST` is refused with `422` - *"This offer already has Work Order WO-..., so it
cannot be recorded as lost or rejected. A Work Order cannot be cancelled yet."* - and nothing is written. The check
runs under the offer's row lock, which the Work Order handoff also takes, so neither can pass the other's check. The
other outcomes are still recorded after a handoff; a non-final one holds back a further Work Order until an acceptance
is recorded again. Before this, a lost response after a handoff moved the offer to `REJECTED` with nothing on the Work
Order showing it (TB-1 TB1-301 part c).

## Slice 6M post-response lifecycle/readiness cleanup

Slice 6M adds one read-only derived view over the existing Slice 4E/6H/6I/6I.2/6J/6K/6L records:

```text
GET /api/commercial-offers/{public_id}/lifecycle-guidance
```

This route creates no `business_event`. It follows the existing Commercial Offer read-role set.

Response fields include `latest_customer_response_outcome/public_id/received_at`, a machine-readable `lifecycle_state` and human `lifecycle_state_label`, `is_commercially_active`, `advisory_message`, `recommended_next_action`, legacy `can_open_revision` (always false for new work), `can_make_new_version`, `has_open_revision_awaiting_resubmission`, `can_record_customer_response`, `work_order_handoff_available`, `work_order_handoff_blocked_reasons` and `linked_work_orders` (public id/code/status of any Work Order shells already handed off from this offer).

Lifecycle states are: `NOT_YET_SUBMITTED`, `AWAITING_CUSTOMER_RESPONSE`, `ACCEPTED_READY_FOR_HANDOFF`, `ACCEPTED_HANDOFF_BLOCKED`, `ACCEPTED_WORK_ORDER_EXISTS`, `REJECTED_CLOSED`, `REVISION_REQUESTED_ACTIVE`, `CLARIFICATION_REQUESTED_ACTIVE`, `ON_HOLD_ACTIVE`, `PENDING_CUSTOMER_DECISION_ACTIVE`, `OTHER_ACTIVE`, `REPLACED_HISTORY` and `ABANDONED_HISTORY`. The last two are inactive history states introduced by Slice 9F; their labels are **Replaced version - history** and **Abandoned version - history**.

Rules:

```text
- The latest customer response (existing Slice 6L ordering) takes precedence over offer_status_code alone for
  REVISION_REQUESTED, CLARIFICATION_REQUESTED, ON_HOLD, PENDING_CUSTOMER_DECISION and OTHER, so a later non-final
  response correctly reports Work Order handoff as unavailable even if the offer was previously Accepted.
- work_order_handoff_available mirrors the real Work Order handoff guard: offer_status_code == ACCEPTED, Account
  traceability present, and at least one active Commercial Offer line. It does not duplicate that guard; the Work
  Order handoff endpoint still validates its own preconditions independently.
- An existing linked Work Order does not make work_order_handoff_available false, because the frozen Slice 6D.1
  contract explicitly allows one accepted Commercial Offer to support one or more Work Order shells for partial
  award. The frontend, however, only offers the default "Create Work Order shell" action while no shell yet exists
  for that offer; once one exists it offers only "Open Work Order shell" for the existing shell(s), so the default
  UI never invites a duplicate-looking creation. This is a UI-only default, not a new backend block.
- This route does not calculate credit/exposure, approve the offer, generate documents, activate Customer Master,
  or change any lifecycle status, revision, or Work Order state itself.
```

**Reconciliation, 8 October 2026 (CS-04 part 1).** The third rule above no longer holds as written: the handoff now
refuses what is already on Work Orders, so the view follows it. `work_order_handoff_available` is also false, with its
reason in `work_order_handoff_blocked_reasons`, when the offer is a Change Quotation ("A Change Quotation does not make
a Work Order of its own: cite it on an amendment of the Work Order it changes."), when an `ACCEPTED` offer has no
customer response at all, and when Work Orders exist and every active line is on them in full ("Every line of this
offer is already on a Work Order in full."). When an `ACCEPTED` offer's latest customer response is not
`ACCEPTED_AWARDED`, the reason is the handoff's own refusal, in the same words ("The customer's latest response is On
hold. Record the customer's acceptance or award first, then create the Work Order.", from
`latest_response_not_accepted_reason` in `commercial_offers/contract.py`), listed whatever else blocks the offer -
before review round 7 it was a generic sentence added only when no other reason was found, so an offer with every line
in full and a later On hold named only the lines. While anything is left, an existing Work Order leaves it true, and the
offer page offers "Create another Work Order" beside "Open" - safe now that the server holds the rule, not only the
screen. The `ACCEPTED_WORK_ORDER_EXISTS` advisory adds that a second Work Order "may take only what is not on a Work
Order yet". The second rule's guard now also includes the offer's purpose and its latest response.

The response also gains `line_handoff` (CS-04 part 1, review round 2): one entry per active offer line, in line
order - `offer_line_public_id`, `line_number`, `quantity`, `quantity_on_work_orders`, `quantity_left` (decimal
strings) and `work_orders` (`work_order_public_id`, `work_order_code`, `quantity` of each Work Order line holding
it). It is counted in one statement over every Work Order of the offer; the Create Work Order page offers from it,
and the "in full" reason above is read from it. `linked_work_orders` already lists every Work Order of the offer
(no page limit), and the page shows that list.

This slice added no new backend guard logic to any existing endpoint: inspection confirmed the existing revision-open guard (`SUBMITTED` only) and the existing Work Order handoff guard already correctly reject every action the derived view marks unavailable. Slice 6M only added the derived read model, the missing active-line precondition to that model, and regression tests proving the existing guards hold.

## Slice 6M.1 Commercial Offer controlled terminal status transition guard

Slice 6M.1 is a corrective foundation fix, delivered in two commits that together close the full gap. Both commits address the same root cause: the general update route,

```text
PUT /api/commercial-offers/{public_id}
```

placed no restriction on the *current* `offer_status_code` before applying a new one, and no restriction on which statuses could be *entered*. Every dedicated lifecycle route (`mark-submitted`, revisions, customer responses) already validated the offer's current status before acting, but the generic update route did not.

### Commit `fa09489` - cannot-leave guard for WITHDRAWN/REJECTED/CLOSED

The first commit stopped the generic update route from moving a `WITHDRAWN`, `REJECTED` or `CLOSED` offer to any other status (including back to `DRAFT`). It did not yet stop the route from *entering* `ACCEPTED` or `REJECTED` from a non-terminal status, and it did not yet stop the route from *leaving* `ACCEPTED`.

### This commit - completion: controlled entry into ACCEPTED/REJECTED, and ACCEPTED becomes cannot-leave too

Verification after `fa09489` showed the original gap was only partially closed: a `SUBMITTED` offer could still be moved straight to `ACCEPTED` or `REJECTED` through generic update (bypassing the Slice 6L Customer Response action entirely), and an already-`ACCEPTED` offer could still be moved to any other status through generic update. This commit closes both remaining paths.

Two separate contract constants are used because the two concepts do not share the same membership - do not collapse them into one:

```text
COMMERCIAL_OFFER_GENERIC_UPDATE_CANNOT_LEAVE_STATUSES = (ACCEPTED, WITHDRAWN, REJECTED, CLOSED)
COMMERCIAL_OFFER_GENERIC_UPDATE_CANNOT_ENTER_STATUSES = (ACCEPTED, REJECTED)
```

`COMMERCIAL_OFFER_INACTIVE_FOR_NEW_OFFER_STATUSES` (Slice 6B.1's "blocks creating a new offer for the same Opportunity" concept) remains its own independent `(WITHDRAWN, REJECTED, CLOSED)` tuple and is **not** aliased to either constant above: `ACCEPTED` is cannot-leave for general update but is still active/actionable for the Slice 6B.1 one-offer-per-Opportunity rule, so it must not appear in that list.

Rules, checked in this order inside `update_commercial_offer`:

```text
1. If the offer's current status is in COMMERCIAL_OFFER_GENERIC_UPDATE_CANNOT_LEAVE_STATUSES and the
   requested offer_status_code differs from the current value, reject with 422: "Commercial Offer
   status {current} is final and cannot be changed through general update. Use the dedicated
   Commercial Offer workflow actions (such as customer response recording) where applicable."
2. Else if the requested offer_status_code is in COMMERCIAL_OFFER_GENERIC_UPDATE_CANNOT_ENTER_STATUSES
   and differs from the current value, reject with 422: "Commercial Offer status cannot be set to
   {target} through general update. Use the dedicated Customer Response action (Submission tab) to
   record the award or rejection outcome."
3. Resubmitting the same (unchanged) status is never a transition under either rule and is not
   blocked, including for a terminal/cannot-leave status - required for full-update compatibility.
4. Non-status fields (offer_title, offer_mode, offer_type, offer_value, currency_code, offer_date,
   valid_until, submission fields, outcome fields, remarks) remain editable on a cannot-leave offer
   through this route. This is a transition guard, not a record-immutability lock.
```

Net effect: `ACCEPTED` and `REJECTED` can now be reached only through the dedicated Slice 6L Customer Response action (`ACCEPTED_AWARDED` -> `ACCEPTED`, `REJECTED_LOST` -> `REJECTED`), which writes `offer_status_code` through the repository layer directly and is therefore unaffected by this guard - it is the sanctioned bypass, not an API-controlled flag. `WITHDRAWN` and `CLOSED` remain reachable through generic update from any non-cannot-leave status, unchanged from Slice 4C/4F. No new business event type was introduced; a rejected generic update creates no `business_event`, no customer-response record and no Work Order.

The frontend Commercial Offer detail edit form removes `ACCEPTED` and `REJECTED` from the Offer status selector entirely (they are never valid entry targets) and disables the selector altogether once the current status is cannot-leave, directing users to the Customer Response action in the Submission tab. `WITHDRAWN` and `CLOSED` remain selectable entry targets from non-terminal statuses.

Known, deliberately out-of-scope gap, unchanged by either commit: this remains a transition guard, not a full state machine. It does not, for example, prevent every other conceivable status combination beyond the ones explicitly named above (none exist today, since `COMMERCIAL_OFFER_STATUS_UPDATE_ALLOWED_STATUSES` only contains `DRAFT`, `READY_FOR_REVIEW`, `SUBMITTED`, `WITHDRAWN`, `ACCEPTED`, `REJECTED`, `CLOSED`, and `SUBMITTED` is already separately guarded by the existing "use mark-submitted" check). This does not change the frozen Slice 6D.1 Accepted Offer -> Work Order handoff contract, add a migration, or change any other route's request/response shape.

**Correction, 4 October 2026 (TB-1 finding TB1-301).** The parenthesis above was wrong about `SUBMITTED`: the "use
mark-submitted" check guards *entering* it only, so the general update could move a submitted offer back to `DRAFT` or
`READY_FOR_REVIEW`, and the edit form offered both - against "submitted/shared offers are treated as commercially
committed" (Slice 6I, above). A third rule now sits between rules 1 and 2:

```text
1a. If the offer's current status is SUBMITTED and the requested offer_status_code is in
    COMMERCIAL_OFFER_PRE_SUBMISSION_STATUSES (DRAFT, READY_FOR_REVIEW), reject with 422: "A submitted
    Commercial Offer cannot go back to Draft or Ready for Review through general update. It can be
    withdrawn or closed here, or the customer's response recorded in the Submission tab."
```

`WITHDRAWN` and `CLOSED` stay reachable from `SUBMITTED`, as before; same-status saves and non-status fields are
unchanged (rules 3 and 4). `SUBMITTED` is deliberately not added to the cannot-leave set: the reports module derives
"open" offers from that set, and a submitted offer is open. On a submitted offer the edit form offers only Withdrawn
and Closed beside the current status, and says why. No migration, no new route, no new event; a refused update writes
nothing.

**A final offer's content stays as it was (5 October 2026, TB-1 finding TB1-301 (b)).** Until then nothing stopped
changes to an offer's lines, prices, T&C, credit reviews or submission evidence once the customer's answer was recorded
or the offer was withdrawn or closed - so an accepted offer and the Work Order that copied its lines could disagree,
and a further handoff would copy the changed values. TB-1's final review judged it a section 12 emergency; the owner
chose a fix package. Now, on an offer whose status is in `COMMERCIAL_OFFER_GENERIC_UPDATE_CANNOT_LEAVE_STATUSES`
(`ACCEPTED`, `REJECTED`, `WITHDRAWN`, `CLOSED`):

```text
POST   /api/commercial-offers/{public_id}/lines                                         -> 422
PUT    /api/commercial-offers/{public_id}/lines/{line_public_id}                        -> 422
POST   /api/commercial-offers/{public_id}/pricing-evidence                              -> 422
POST   /api/commercial-offers/{public_id}/pricing-evidence/{evidence_public_id}/select-basis -> 422
POST   /api/commercial-offers/{public_id}/tc-clauses                                    -> 422
POST   /api/commercial-offers/{public_id}/tc-clauses/attach-recommended                 -> 422 when it would attach any
DELETE /api/commercial-offers/{public_id}/tc-clauses/{attachment_public_id}             -> 422 (was: no 422 mapping)
POST   /api/commercial-offers/{public_id}/credit-review                                 -> 422
POST   /api/commercial-offers/{public_id}/submission-evidence                           -> 422
       "This Commercial Offer is <Status>, so its lines, prices, T&C, credit reviews and submission evidence can no
        longer change. A change after the award goes on a Work Order amendment; otherwise raise a new offer."
```

Each of these writes now takes the offer's row lock before reading its status, as the general update and the customer
response already do, so a change waiting behind an acceptance reads `ACCEPTED` and is refused; nothing is written and
no event is recorded. A `SUBMITTED` offer's content is unchanged by this rule ("Submitted document locking" stays
deferred in `DEFERRED_REQUIREMENTS.md`); the header fields the general update saves with the status unchanged are
unchanged too. On a final offer the page shows a note in place of the line, pricing, T&C, credit-review and
submission-evidence forms. No migration, no new route, no new event.

*Reconciliation, 10 October 2026 (CS-05c):* a `SUBMITTED` offer's content now changes only through an open revision;
see the CS-05c section at the end of this contract.

*Reconciliation, 12 October 2026 (Slice 9F, as built):* this section's lists and rule 4 are superseded. The current
rules are in the Slice 9F section, "Submission, immutability and outcomes":

- `COMMERCIAL_OFFER_GENERIC_UPDATE_CANNOT_LEAVE_STATUSES` is now `ACCEPTED`, `WITHDRAWN`, `REJECTED`, `CLOSED`,
  `REVISED`, `ABANDONED`, and `COMMERCIAL_OFFER_INACTIVE_FOR_NEW_OFFER_STATUSES` is `WITHDRAWN`, `REJECTED`, `CLOSED`,
  `REVISED`, `ABANDONED`.
- Rule 4 no longer holds. Only a `DRAFT` or `READY_FOR_REVIEW` row takes changes to its header content or its lines,
  prices, T&C, credit reviews or submission evidence. On the latest live row in `SUBMITTED`, `ACCEPTED`, `REJECTED`,
  `WITHDRAWN` or `CLOSED`, only `outcome_date` and `outcome_remarks` stay editable (and a `SUBMITTED` row may still be
  withdrawn or closed); a `REVISED` or `ABANDONED` row takes no update at all. A change to a sent offer is made in a new
  version.

## Slice 6O.1 Supplementary and Change Commercial Offer Foundation

Slice 6O.1 adds an explicit `offer_purpose` and a controlled path for creating **separate**
Commercial Offer series linked to a Base Offer, for two post-award scenarios: a Supplementary
Offer (additional line/quantity against the same enquiry) and a Change Quotation (revised price
proposed before a Work Order amendment). Neither is a revision of the Base Offer; Slice 6K
revisions remain scoped inside one offer's own series.

### Offer purpose

```text
COMMERCIAL_OFFER_PURPOSE_BASE = "BASE"
COMMERCIAL_OFFER_PURPOSE_SUPPLEMENTARY = "SUPPLEMENTARY"
COMMERCIAL_OFFER_PURPOSE_CHANGE_QUOTATION = "CHANGE_QUOTATION"
```

Every Commercial Offer response now exposes `offer_purpose` (default/backfilled `BASE` for all
pre-existing offers), plus, for related offers: `base_offer_public_id`, `base_offer_code`,
`related_work_order_public_id`, `related_work_order_code`, `customer_request_reference`,
`customer_request_received_date`, `customer_request_summary`.

### Relationship model

A related offer links directly to its Base Offer via `base_offer_id` (self-referencing FK on
`crm_commercial_offer`). Chains are rejected: a related offer can never itself father another
related offer. A related offer may (Supplementary, optional) or must (Change Quotation, required)
link to an existing Work Order via `related_work_order_id` (FK to `crm_work_order`); the linked
Work Order must belong to the same Opportunity and, where both sides carry a value, the same
Account as the Base Offer.

### Base Offer eligibility

A Base Offer may father a related offer only while `offer_status_code == ACCEPTED`. The Slice
6M.1 guard prevents *generic update* from leaving `ACCEPTED`, but **`ACCEPTED` is not immutable**:
the dedicated Slice 6L Customer Response route writes the status directly and can move an accepted
offer to `REJECTED`. An earlier version of this section described `ACCEPTED` as a stable
cannot-leave status, which was wrong and is corrected here (Slice 9B, 7 September 2026).

Because the status can therefore change under a reader, related-offer creation takes a row lock on
the Base Offer before checking eligibility, so a concurrent rejection cannot land between the check
and the insert. Creation never reopens, mutates or reinterprets the Base Offer, and never
fabricates response evidence for older records.

### Related-offer creation route

*Path parameter aligned 7 October 2026 (TB-1 documentation register, PF-2 entry 28): the POST was
written `{base_offer_public_id}`; the route declares `{public_id}`, which is the Base Offer's.*

```text
POST /api/commercial-offers/{public_id}/related-offers
GET  /api/commercial-offers/{public_id}/related-offers
```

Create roles: `ADMIN`, `SALES_USER`, `SALES_MANAGER` (same as ordinary Commercial Offer
creation). Read roles: the existing Commercial Offer read-role set. Request fields:
`offer_purpose` (`SUPPLEMENTARY` or `CHANGE_QUOTATION` only - `BASE` is rejected here), optional
`related_work_order_public_id`, optional `customer_request_reference` and
`customer_request_received_date`, required non-blank `customer_request_summary`, and the usual
initial offer fields (`offer_title`, `offer_mode`, `offer_type`, `offer_value`, `currency_code`,
`offer_date`, `valid_until`, `remarks`). `opportunity_public_id` and `business_party_id` are
always derived server-side from the Base Offer; the request body cannot override them.

The action starts the related offer in `DRAFT`, copies no lines, prices, terms or evidence, and
creates no Work Order or Work Order Amendment. It records exactly one
`CommercialOfferRelatedOfferCreated` business event.

### Refined one-active-Base-Offer guard

The Slice 6B.1 rule (one active/actionable Commercial Offer per Opportunity until formal
revisions/Opportunity lines exist) now scopes its scan to `offer_purpose = BASE` only. An active
Base Offer never blocks creating a Supplementary Offer or Change Quotation, and multiple
Supplementary Offers / Change Quotations may coexist under the same Base Offer, each
representing a distinct customer request. `COMMERCIAL_OFFER_INACTIVE_FOR_NEW_OFFER_STATUSES`
(`WITHDRAWN`, `REJECTED`, `CLOSED`) is unchanged.

### Independent lifecycle

A related offer reuses every existing Commercial Offer lifecycle route unmodified: its own lines
(Slice 4E), pricing evidence (Slice 4D), header T&C (Slice 6F/6G), submission readiness (Slice
6H), submission evidence (Slice 6I), manual credit review (Slice 6I.2), mark-submitted (Slice
6J), revisions (Slice 6K), customer responses (Slice 6L) and lifecycle guidance (Slice 6M). None
of these routes were changed by this slice; a related offer's status changes never mutate the
Base Offer, and accepting a related offer never creates a Work Order or Work Order Amendment
automatically.

### Work Order handoff

The frozen Slice 6D.1 handoff contract, `POST /api/work-orders/from-commercial-offer`, is
unchanged. An accepted Supplementary Offer or Change Quotation does not automatically create a
Work Order or a Work Order Amendment; that remains explicit, separate action design left for
Slice 6O.2 (Work Order Amendment Intake Foundation) to define.

### Explicit exclusions from Slice 6O.1

```text
Work Order Amendment records or application to a Work Order (Slice 6O.2)
Automatic copying of offer lines, prices or terms from the Base Offer
Automatic Work Order or Work Order Amendment creation
Reopening or mutating the Base Offer
Remaining-quantity / partial-award allocation logic
A second revision mechanism (Slice 6K revisions remain scoped inside one offer's own series)
```

## Production carry-forward: commercial commitment review

The current nullable `valid_until` prototype field remains unchanged until the production
exposure slice. That slice must implement the `CEX-001` liveness rule: controlled submission has
either `valid_until` or a mandatory system-calculated `next_exposure_review_due_at`; an overdue
item remains Potential and holds new exposure-dependent decisions until Sales confirms it remains
live or records the final/not-awarded outcome. This requires a scoped schema migration, jobs,
notifications, events and tests; it is not current prototype behavior.


## Slice 9B a Rejected Commercial Offer is final

Slice 9B narrows the Slice 6L Customer Response action by one status. `REJECTED` is removed from
the allowed set:

```text
COMMERCIAL_OFFER_CUSTOMER_RESPONSE_ALLOWED_STATUSES = (SUBMITTED, ACCEPTED)
```

A customer response of any outcome against a `REJECTED` Commercial Offer is rejected with `422`
and a message directing the user to the replacement offer. No response record is written, no
event is emitted, and the offer's status is unchanged.

Reason: a rejected offer is treated as inactive for the Slice 6B.1 one-active-Base-Offer guard,
so a replacement offer may legitimately exist for the same Opportunity. While `REJECTED` remained
an allowed customer-response status, a late `ACCEPTED_AWARDED` response drove the rejected offer
back to `ACCEPTED`, leaving two live offers for one enquiry. Recorded as a known gap in
`docs/agent/DEFERRED_REQUIREMENTS.md` and closed by explicit PBL decision on 7 September 2026.

Deliberately unchanged:

- `COMMERCIAL_OFFER_INACTIVE_FOR_NEW_OFFER_STATUSES` still contains `REJECTED`, so preparing a
  replacement offer for the same Opportunity remains permitted. That was never the defect.
- `ACCEPTED` remains an allowed customer-response status; this slice narrows one status, not the
  action.
- The Slice 6M `lifecycle-guidance` read model needs no change: `can_record_customer_response`
  already derives from the same contract tuple and now correctly reports `false` for a rejected
  offer. The frontend gates its form on that value rather than on a duplicated status list.
- No migration, no permission change, and no change to the frozen Slice 6D.1 handoff contract.

### Concurrency requirement for `offer_status_code`

Removing a status from an allowed tuple is not by itself a guard: two concurrent requests can both
read an eligible status and both proceed. Slice 9B therefore makes the lock part of the contract.

**Every operation that reads `offer_status_code` and then writes it, or reads it and then inserts
or decides a dependent record, must call `lock_commercial_offer_row` before the read.** The
current participants are:

```text
writers      update_commercial_offer
             mark_commercial_offer_submitted
             create_commercial_offer_customer_response
dependants   create_related_commercial_offer
             create_commercial_offer_revision
             create_work_order_from_commercial_offer   (work_orders module)
             decide_work_order_amendment               (work_orders module)
```

Base Offer creation additionally locks the parent `crm_opportunity` row before reading
`opportunity_status_code`, which serializes concurrent creations against each other and blocks a
concurrent Opportunity closure. Read-only routes take no lock.

`backend/tests/test_slice_9b_pilot_hardening.py` discovers the status-writing paths by source
introspection and asserts the detected set equals the list above, so a new writer added later
fails the suite rather than shipping unlocked. **Slice 9E's `generate_commercial_offer_quote_document`
only reads `offer_status_code` (it never writes it), so that discovery guard does not detect
it; Slice 9E adds its own AST ordering test instead - see the section below.**

## Slice 9E Quotation Generation foundation

Slice 9E adds the customer-facing document that everything from Slice 4E onward has been
preparing: a frozen, versioned quotation rendered from the offer's active lines and its Slice
6F/6G header T&C snapshots, stored through the Slice 9C storage abstraction, with a one-step
Draft -> Approved for Issue gate.

### Records

```text
crm_commercial_offer_quote_document

id                          integer identity PK
quote_document_public_id    UUID, unique
commercial_offer_id         FK -> crm_commercial_offer.id (application-enforced, no declared FK,
                             matching this module's existing subordinate-table convention)
version_no                  1, 2, 3... per offer; UNIQUE (commercial_offer_id, version_no)
quote_reference              derived, e.g. "CO-000042/V1" - no new numbering series
document_public_id           -> document_metadata.document_public_id (the stored HTML bytes)
source_fingerprint            sha256 over the canonical source-data snapshot
quote_status_code             DRAFT | APPROVED_FOR_ISSUE
generated_by / generated_at
approved_by / approved_at / approval_note
superseded_at                 independent column, NOT a third status value - see below
```

Two CHECK constraints (Alembic `20260908_0035`):

```sql
ck_quote_document_status               quote_status_code IN ('DRAFT', 'APPROVED_FOR_ISSUE')
ck_quote_document_approval_is_complete (DRAFT with approved_by/approved_at both NULL)
                                        OR (APPROVED_FOR_ISSUE with both NOT NULL)
```

A row cannot claim approval without recording who approved it and when, even against a direct
`INSERT` that bypasses the API - the same shape as Slice 9C's
`ck_document_metadata_local_upload_has_bytes`.

`superseded_at` is deliberately a separate column, not a third status value: generating version
N+1 marks every earlier version superseded in the same transaction, but must not erase an
earlier version's own approval status, approver or timestamp - that is the record of what was
actually approved and, potentially, already sent to the customer.

### Storage and rendering

The generated HTML is stored through `documents.service.store_generated_document()` (see
`docs/agent/contracts/documents.md`, "Slice 9E extension"), linked as
`linked_record_type = 'commercial_offer'`, `document_type = 'QUOTATION'`. The file name
deliberately excludes the customer name (`Quotation-{offer_code}-V{version}.html`), because a
file name alone leaks the customer's identity (the same lesson Slice 9C recorded for
`Acme-PAN-card.pdf`) and the generic documents list is visible more widely than one offer.

Rendering is a pure function, `commercial_offers.quote_render.render_quote_html()`: no database
access, no I/O, no clock, no randomness, so the same input renders byte-identical output. Every
interpolated value passes through `html.escape(..., quote=True)` - Account names, offer titles,
line descriptions, the prepared-by name and T&C snapshot text are all customer- or user-supplied
free text, and this is the single largest risk in the slice. The output contains no `<script>`
element and no `on...=` event-handler attribute, proven by tests driven with hostile input.

**Nothing mutable may be rendered into the frozen document.** Because the bytes are never
rewritten, any fact the document embeds must remain true for the life of the file. The document
therefore carries only immutable facts about its own version - quote reference, version number,
generation timestamp and **prepared-by** - plus a pointer stating that issue approval is recorded
in the CRM against that quote reference. It deliberately does **not** display its own approval
status: generation always precedes approval, so a status rendered at generation would always read
"Draft" and an approved, issued document would contradict its own approval record (independent
review, correction pass 1, finding 1).

Two consequences are recorded rather than hidden. First, a Draft download and an approved
download are byte-identical, so the document itself cannot signal that it was not approved; the
UI labels the action on an unapproved version accordingly, and the approval record in the system
remains authoritative. Second, if PBL later requires the issued document itself to assert
"Approved for Issue", that is a separate approved-artifact design (generate-at-approval, or a
second rendered artifact) and needs explicit owner confirmation - it is not a defect fix.

**The document never presents a numeric grand total unless every active line carries an amount.**
Two wrong numbers were possible and both were shipped before being caught: with no line priced
the snapshot total is `0.00`, so the document asserted a zero price; with *some* lines priced the
total summed only the amounts that existed, so one priced line at INR 100 beside one unpriced
line printed `Total (INR) 100.00` - a partial sum presented as the complete quotation total,
reachable because `rate_amount` is optional on an active line. The total now reads **"Not
priced"** when no line is priced and **"Not fully priced"** when only some are; each is exactly
true of its own case.

Generation is deliberately **not** blocked when pricing is incomplete, so Sales can still produce
rough drafts. Incomplete pricing is gated at **approval for issue** instead - see the approval
preconditions below. (Until 11 September 2026 this sentence pointed to a "Deferred pricing
precondition" section that was never written. The plan it referred to - blocking generation
after the pilot - was superseded by owner decision on 9 September 2026; see
`docs/agent/DEFERRED_REQUIREMENTS.md`.)

**Changing the canonical snapshot shape is a breaking change for staleness comparison.** Every
stored `source_fingerprint` was computed over the shape in force when that version was generated,
so altering the shape (adding, removing or reformatting a field) makes every pre-existing version
report `is_stale = true` even though its offer has not changed. Correction pass 1 changed the
shape - addresses are now filtered and labelled, GSTINs filtered - which was harmless only
because the slice was never released and no stored quotation existed outside test data. A future
shape change against released data must be treated as a migration concern and bump the snapshot's
own `schema_version`.

The document is HTML, not PDF (owner decision 1, 8 September 2026): there is no PDF renderer in
`backend/requirements.txt`, and adding one (WeasyPrint needs system libraries; ReportLab needs
hand-built layout code) was declined in favour of shipping the pilot sooner. **The artifact the
system freezes and checksums is the HTML; the PDF a customer receives is produced by the user's
browser Print dialog, outside the system, and is not itself stored or checksummed.** A future
server-side renderer replaces `render_quote_html` behind the same seam without touching the
storage, versioning, fingerprint or approval-gate plumbing.

### Snapshot and staleness

`build_quote_snapshot()` gathers the offer header, Account identity (name, legal name,
addresses, GSTINs - read through the existing `accounts` module repository/service functions,
never a new ad hoc join), active offer lines and active header T&C clause snapshots into one
canonical, JSON-serializable dict.

**Account identity is filtered, not merely gathered** (independent review, correction pass 1,
finding 3). Only `REGISTERED_OFFICE` and `COMMUNICATION` addresses reach the document, each
carrying its type label so the two are distinguishable; `SITE`, `BILLING_DRAFT` and `OTHER` are
excluded, `BILLING_DRAFT` most pointedly because the Account contract defines it as draft CRM
information that is explicitly not Finance-approved billing master data. A GSTIN whose
verification state is `REJECTED_INCORRECT` is excluded, because a number the business has already
determined to be wrong must never be printed on a customer document; every other verification
state remains quotable, since an unverified or pending GSTIN is the customer's stated number and
is what a prototype-stage quotation legitimately carries. This filtering matters more than it
would elsewhere precisely because the artifact is frozen: an unrelated address or a known-bad
GSTIN captured into a version cannot be repaired by later correcting the Account, only superseded
by generating a new version. **The same dict is what `compute_source_fingerprint()` hashes
and what `render_quote_html()` renders** - deliberately one shape, not two independently
maintained ones, so a hash-shape/render-shape drift bug cannot arise.

The fingerprint is taken over source data only - never over `quote_reference`, `version_no` or
`generated_at`, which are per-document facts, not offer facts, and would otherwise make the
fingerprint depend on how many prior versions existed rather than on whether the offer's
underlying data changed.

On read, the fingerprint is recomputed from current data and compared; a mismatch sets
`is_stale = true` on the response. This is **advisory only** - the control is that the stored
bytes are immutable; staleness is a convenience prompting a new version, never a block.

**Excluded from the document by construction:** pricing evidence, the selected basis rate, its
selection rationale and credit review outcomes - internal commercial records that must never
reach a customer-facing document. GST is shown as an explicit "amounts exclusive of GST" line
rather than calculated, because GST determination remains deferred.

### Routes

```text
GET  /api/commercial-offers/{public_id}/quote-documents
                                        require_permission(COMMERCIAL_OFFER_READ)
POST /api/commercial-offers/{public_id}/quote-documents
                                        require_permission(COMMERCIAL_OFFER_QUOTE_GENERATE)
POST /api/commercial-offers/{public_id}/quote-documents/{quote_document_public_id}/approve
                                        require_permission(COMMERCIAL_OFFER_QUOTE_APPROVE)
```

Download reuses the existing `GET /api/documents/{public_id}/content` - no new download route,
no second authorization path. Slice 9C's record-scoped, fail-closed check already maps
`commercial_offer` to `COMMERCIAL_OFFER_READ`.

All three are new routes (they did not exist at the PF-1A-E1 baseline), recorded in
`POST_BASELINE_NEW_ROUTES` (`backend/tests/fixtures/post_baseline_tightened_routes.py`), never
in the frozen baseline inventory. The frozen 31 permission / 110 grant / 76 route counts are
unchanged.

### Permissions

Two new codes in `POST_BASELINE_ROLE_PERMISSION_MATRIX`:

```text
COMMERCIAL_OFFER_QUOTE_GENERATE   ADMIN, SALES_USER, SALES_MANAGER
COMMERCIAL_OFFER_QUOTE_APPROVE    ADMIN, SALES_MANAGER
```

`COMMERCIAL_OFFER_QUOTE_APPROVE` deliberately excludes `SALES_USER` (owner decision 4, 8
September 2026): a Sales User may generate a quote but not approve it for issue.

### The approval gate is procedural, not an access control

The gate records that a named person authorised a specific version for issue, with a timestamp
and an event (`CommercialOfferQuoteDocumentApprovedForIssue`). It is **not** an access control:

- A Draft quote is downloadable by anyone who can already open the Commercial Offer - it has to
  be, since approval requires being able to read the document first, and it leaks nothing new
  (every figure is already on the offer screen for the same audience).
- No system can stop a human emailing a file; "only approved quotations may be shared with
  customers" is enforced by the record of which version was approved, not by preventing bytes
  from moving.
- A Sales Manager may both prepare and approve their own quote - this does not achieve full
  maker-checker. That is `APR-001`'s to close.

An earlier design considered a cross-module hook so the generic documents download route would
refuse an unapproved quote. It was removed before freezing: it would have implied enforcement
over data the same users can already read on screen, added a `documents -> commercial_offers`
dependency, and introduced a fail-open risk if the hook were ever not registered.

### Preconditions and the row lock

Generation requires, checked in order: offer status is `DRAFT`, `READY_FOR_REVIEW` or
`SUBMITTED` (a customer-facing quotation for a concluded offer is not meaningful); Account
traceability resolves; at least one `ACTIVE` offer line exists.

`generate_commercial_offer_quote_document` reads `offer_status_code` and then inserts a
dependent record, so per the Slice 9B contract it locks the offer row first
(`lock_commercial_offer_row`) - **before** the discovery guard in
`test_slice_9b_pilot_hardening.py`'s `EXPECTED_STATUS_WRITING_FUNCTIONS`, which detects only
functions that *write* `offer_status_code`. This function only reads it, so that guard does not
cover this path; Slice 9E adds its own AST ordering test
(`test_the_generation_path_locks_the_offer_row_before_reading_status` in
`test_slice_9e_quotation_generation.py`) rather than assuming the existing guard applies.

Approval requires, in order: the Commercial Offer is **not** `ACCEPTED`, `REJECTED`,
`WITHDRAWN`, `CLOSED`, `REVISED` or `ABANDONED`; the quotation version is not superseded; it is `DRAFT`; **every active
line on the offer carries an amount**; and **the version still matches the offer** (its stored
`source_fingerprint` equals a freshly computed one - `is_stale` is false).

**The staleness match is taken at one instant.** Approval reads every part of the snapshot -
header, lines, T&C clauses and Account identity - in one read-only `REPEATABLE READ` transaction
(`build_quote_snapshot_at_one_instant`), opened after it holds its two locks, so the version is
compared with the offer as it stood at a single moment inside the approval. Line, T&C clause and
Account identity writers do not take the offer lock, so a change that commits after that moment
leaves the approved version stale a moment later - exactly as a change committed a minute after
approval does. Both are flagged by `is_stale`, and the approved document is fully priced either
way, because a version passes only if the offer matched it at that moment with every active line
priced.

The first version of this precondition read the parts statement by statement under
`READ COMMITTED`, so a part read before a concurrent write and a part read after it could combine
into a snapshot the offer never had, and approve a version the offer matched at no instant during
the approval (independent review, round 2; pinned by
`test_approval_cannot_validate_a_combination_of_offer_data_that_never_existed`). Generation and the
listing read their snapshots the same single-instant way, so a frozen document and a staleness flag
each describe one real state of the offer. The single-instant read sees committed data only - every
caller reads before it writes - takes no locks and writes nothing, so it can neither block on the
caller's own row locks nor fail with a serialization error. It runs on its own connection, so each
generation, listing or approval briefly uses two pooled connections. Serializing every snapshot writer
against approval, the Accounts module included, was considered and not taken (independent review,
round 1): it would close the moment between the snapshot and the approval's commit without changing
what the approved document says.

The last two were added by the UI cleanup package (owner decisions of 9 and 11 September 2026,
superseding Slice 9E decision 7, which planned to block *generation* after the pilot). They only
work as a pair: if the version still matches the offer and every active line is priced, then
every line in the frozen document is priced. A check of the offer's current lines alone would
leave a version frozen as "Not fully priced" approvable the moment the missing rate was filled
in on the offer. What counts as priced is defined once, in `quote_render.count_unpriced_lines`,
which the document's "Not priced" / "Not fully priced" wording also uses.

Every refusal reason comes from one function, `quote_document_approval_blocked_reason`, which
also fills the `approval_blocked_reason` field on every returned quotation version (list,
generate and approve responses). It is evaluated against the state that response was read from:
`null` when an approval would then succeed for a caller holding `COMMERCIAL_OFFER_QUOTE_APPROVE`,
otherwise the exact message the approve route would refuse with. The listing reads the offer, its
quotation versions and the snapshot in one single-instant transaction, so each listing describes
one real state. The field deliberately ignores the caller's role, which remains the route
permission's job.

The field is **advisory**. The UI offers the Approve button only when it is `null` and shows the
reason in its place otherwise, but the offer can change between loading the page and clicking
Approve, so approval re-checks under its locks and may still refuse. What the field fixes is the
button appearing on a version that could not be approved when the page was loaded - it used to
appear on a Draft version of a won or lost offer and then fail. This is an additive response
field; no route, permission, table column or migration changed.

One ordering consequence, recorded rather than hidden: the concluded-offer check now runs after
the quotation row is looked up, so approving a quotation id that does not exist on a concluded
offer returns `404` rather than `422`. The lock order (offer, then quotation) is unchanged.

The offer-status precondition is an owner decision of 9 September 2026 (on independent review's
recommendation). "Approved for Issue" is a present authorisation to send the document to a
customer, so applying it after the offer has concluded asserts an authorisation that no longer
means anything. If retrospective confirmation of which version was actually sent is wanted later,
that needs its own archival action rather than reusing this one. The blocked set is
`COMMERCIAL_OFFER_QUOTE_DOCUMENT_APPROVE_BLOCKED_OFFER_STATUSES`, deliberately its own tuple even
though it currently shares membership with the Slice 6M.1 generic-update set - this module has
been bitten before by collapsing two same-looking sets into one alias.

Approval therefore takes **two** row locks, in this order: the parent Commercial Offer first,
then the quotation row. The order is not incidental - generation also locks the offer first and
then touches quotation rows through `supersede_earlier_quote_documents`, so taking them in the
same order is what stops the two paths deadlocking. The offer lock is required because the new
precondition makes approval a read-then-write against `offer_status_code`, the exact Slice 9B
shape; the quotation lock closes the separate race where two concurrent approvals of the same
version both succeed, silently overwriting one approver's identity with another's. Both are
proven by concurrency tests, not asserted.

### Events

```text
CommercialOfferQuoteDocumentGenerated
CommercialOfferQuoteDocumentApprovedForIssue
DocumentGenerated                      (documents module, for the stored artifact)
```

Payloads carry metadata only (version, reference, fingerprint, byte size) - never the rendered
document, never its content.

### Submission readiness

Two advisory rows added to `GET /api/commercial-offers/{public_id}/submission-readiness`:

```text
QUOTATION_DOCUMENT   PASS if a non-superseded APPROVED_FOR_ISSUE version exists;
                     ATTENTION_REQUIRED otherwise
INTERACTION_LOG      PASS if at least one interaction is recorded against the offer or its
                     Opportunity/Account chain; ATTENTION_REQUIRED if none
```

`QUOTE_DOCUMENT_GENERATION` is **removed** from `COMMERCIAL_OFFER_SUBMISSION_READINESS_DEFERRED_ITEMS`:
Slice 9E implements what it used to defer, so leaving it in the deferred tuple would misstate
current behaviour.

`INTERACTION_LOG` is the FRD row (source line 855: "capture all communications ... in a
time-stamped log before a quote can be raised") that Slice 9D deliberately deferred out of its
own package - see `docs/agent/contracts/interaction-contract.md`, "Explicitly out of scope for
v1.0". It is **advisory only**, exactly as that contract records: hard enforcement waits until
the pilot habit forms.

### Explicitly out of scope for Slice 9E

Server-side PDF rendering. Margin-threshold evaluation and approval (needs `APR-001`). Full
maker-checker. Emailing or otherwise transmitting the quote. Line-level T&C. GST/tax
calculation. Offer cloning or immutable offer-version snapshots (Slice 6K's deferred deeper
work). Hard enforcement of the FRD interaction-logging rule. Retention purge and read-access
auditing (extends the existing Slice 9D/9C deferred entry to a third thing it covers, rather
than a fourth entry). The two synthetic UAT datasets, sequenced as their own package after this
one.

See `docs/agent/slices/slice-9e-quotation-generation.md` for the full design record, the six
owner decisions and the complete test plan.


## UI cleanup package (September 2026): display names

Recorded 11 September 2026. One additive, read-only field so the screen can show a name instead of
a user public ID:

```text
CommercialOfferResponse   (GET /api/commercial-offers, GET /api/commercial-offers/{public_id},
                           and every response that returns or embeds a Commercial Offer record)
    created_by_display_name   beside created_by
```

The field is `string | null`, resolved from `app_user.display_name` matched on
`app_user.public_id` in the same query, as a LEFT JOIN - the same approach the Slice 9E quotation
versions already use for `generated_by_display_name` and `approved_by_display_name`. It is `null`
when `created_by` is null or does not match any user, and the offer is still returned in that case.
`created_by` is unchanged. Subordinate records (lines, pricing evidence, submission evidence,
credit reviews, revisions, customer responses) are unchanged by this package. No route,
permission, request field, business event or migration change.

## Language pass (September 2026): wording of text fields

Recorded 11 September 2026. Human-readable text returned by this module was reworded to plain
language: `lifecycle_state_label` for the three accepted states, `advisory_message`,
`recommended_next_action`, `work_order_handoff_blocked_reasons`, submission-readiness item messages
and deferral notes, business-event reasons, and some validation messages. Every code - the
`lifecycle_state` values, readiness item codes and statuses, status codes and event names - is
unchanged. Clients branch on codes, never on these texts. No route, permission, field or migration
change. See `docs/agent/slices/ui-language-pass.md`.

## TB-1 fix TB1-600 (4 October 2026): the currency list

Recorded 4 October 2026. Until now every currency field below took any three letters, upper-cased and kept them
(`XYZ` included), and the dashboard added every offer's value into one rupee total. TB-1's Pass 6 found it (TB1-600).
The owner decided on 4 October 2026: INR stays the default and the operating currency; USD, GBP and EUR may be chosen,
so that work in neighbouring countries stays possible; nothing else, and other currencies are a later decision.

The list is held once, in `backend/app/shared/currency.py` (`OPERATING_CURRENCIES`), and offered on screen from
`frontend/src/components/currency.ts`. Every currency an offer request carries is checked against it:

```text
CommercialOfferCreate, CommercialOfferUpdate              currency_code
CommercialOfferRelatedOfferCreate                         currency_code
CommercialOfferLineCreate, CommercialOfferLineUpdate      currency_code
CommercialOfferPricingEvidenceCreate                      currency_code
CommercialOfferCustomerResponseCreate                     awarded_currency_snapshot
```

A missing or empty code is INR, and lower case is stored upper case, both as before. Any other code is refused with
`422` and `Currency must be one of INR, USD, GBP, EUR.`, which replaces `Currency code must be a 3-letter code such as
INR.` The request and response fields keep their names and shape. Nothing is converted. Every currency box on the offer
pages is now a choice from the list (`components/CurrencySelect.tsx`). A record saved before the fix keeps its code; the
screen shows it, marked "no longer offered", and the edit form asks for a listed currency before it saves.

No route, permission, response field, business event or migration change. Not changed: an offer line may still be in
a different currency from its offer. Credit exposure and Work Order billing terms remain INR; see
`DEFERRED_REQUIREMENTS.md`, "Currencies other than INR".

## CS-05a (9 October 2026): a stale form cannot overwrite an offer or an offer line

Recorded 9 October 2026, TB-1 corrective package CS-05a (finding TB1-303, the offer part; row 10 of the corrective
register's sequence). Until now two people with the same offer, or the same line, open saved over each other without
a word: the second save wrote every field the first had changed - an offer's status and value, a line's quantity and
rate - and the screens sent the whole form, so a field nobody touched was written back too. A line's amount could be
neither user's quantity times rate.

Migration `20260908_0051` adds `row_version` to `crm_commercial_offer` and to `crm_commercial_offer_line`: `1` when
the row is made, never below `1` (a check), raised by one on every write of the row the application makes - the
offer's edit, marking it submitted, and a customer response that sets its status; a line's edit. A customer response
that leaves the status as it is writes nothing on the offer's row and leaves its version. The version is a concurrency
token only - it is not the offer's commercial version or revision ("Commercial Offer version/reference" in the frozen
handoff contract, Slice 6K's revisions), and a quotation's fingerprint does not read it.

```text
PUT /api/commercial-offers/{public_id}
PUT /api/commercial-offers/{public_id}/lines/{line_public_id}

request    expected_row_version   required, integer >= 1: the row_version the screen loaded. Missing, null or 0 is
                                  422. Send only the fields being changed; a field left out keeps what is recorded.
                                  The version alone is not a change: 422, as an empty update always was.
response   row_version            on every Commercial Offer response (GET, list, create, update, mark-submitted,
                                  customer response, and every response embedding an offer) and every line
                                  response (GET lines, add, update) - the version after the write
409        a version other than the row's, however it came about:
           "Someone else changed this Commercial Offer after you opened it, so your change was not saved. Reload the
            page to see their version, then make your change again."
           "Someone else changed this Commercial Offer line after you opened it, so your change was not saved. Reload
            the page to see their version, then make your change again."
```

The version is compared under the offer's row lock (`lock_commercial_offer_row`), which every writer of the offer's
status and every content writer already takes; for a line, with the line itself read `FOR NO KEY UPDATE` - the lock
its own `UPDATE` takes - so its amount is computed from the line as it stands for this write, even against a writer
that does not take the offer lock. Each `UPDATE` also carries `AND row_version = :expected_row_version`, the client's
version, and a row it did not write is the same `409`. The checks run in this order, and whichever refuses, nothing is
written and no event is recorded:

```text
1. sign-in and permission                                                   401 / 403
2. the request schema, before the record is read and whatever the version:   422 (FastAPI's list)
   expected_row_version missing, null, not an integer or below 1; a value of the wrong type; a bound the
   schema declares - a negative offer value or rate, a quantity of zero or less, more than two decimal
   places, a text over its length, a currency code not three letters
3. under the offer's row lock: the offer does not exist                       404
   for a line: the offer is Accepted, Rejected, Withdrawn or Closed            422 (TB1-301 (b), as before)
   for a line: the line is not on this offer                                   404
4. the version                                                                409
5. the rules about the values: the status moves, the dates, the currency       422
   list, a line's status; and the version alone is not a change
```

So a stale form whose values pass the schema is told to reload, never that its values break a rule of an offer it no
longer sees; a stale form whose values the schema refuses is told that first, and its next save, corrected, is `409`. The error keeps this module's `{"detail": "..."}` shape until CS-06
brings the common error envelope (`MCF_ADOPTION_RECORD.md`).

`CommercialOfferUpdated` and `CommercialOfferLineUpdated` payloads gain `row_version`, the version the save wrote. No
new route, permission or event name. Not versioned: a write that bypasses the application (a direct SQL statement)
changes a row without raising its version; `backend/tests/test_cs05a_offer_stale_save.py` fails if a function in the
application writes either table without raising it, the new offer's code set straight after its insert excepted.

The offer page sends the version of the record its form was opened from and only the fields the user changed
(`frontend/src/pages/commercial-offers/offerEditState.ts`); a form saved unchanged says so beside its Save button
and sends nothing. A refusal, the `409` included, is shown beside the Save button that was pressed - the offer's
"Save Commercial Offer", or the line's "Save line". The form stays open; reloading the page loads the current version.

Out of scope here and next, by the owner's decisions of 9 October 2026: a submitted offer's content may be changed
only through a revision; the database holds the one-active-Base-Offer rule; a duplicate caused by a double click gets
a clear refusal, not a server error. Accounts, Leads, Opportunities, Work Order amendments and interactions are
CS-05b's.

## CS-05c (10 October 2026): a submitted offer changes only through a revision; the database holds one active Base Offer; a duplicate made at the same time is answered

Recorded 10 October 2026, TB-1 corrective package CS-05c, which closes TB1-301 parts (b2) and (d), TB1-304 for the offer
constraints and the deferred "Database-level uniqueness for the one-active-Base-Offer rule". The owner's decisions of
9 October 2026: (1) "Do not allow submitted offer to be changed except by means of a revision." (2) The database
enforces the one-active-Base-Offer rule, "for consistency". (3) A double click is quite possible, so a duplicate gets a
clear message, not a server error.

### 1. A submitted offer's content changes only through a revision

Until now a Submitted offer's lines, prices, T&C, credit reviews and submission evidence could be changed at will,
though the customer held it (the 6M.1 section above, "A final offer's content stays as it was", left them open). Now,
on an offer whose status is past `DRAFT` and `READY_FOR_REVIEW` and not final - in practice `SUBMITTED`; `REVISED`,
which nothing sets, would be treated the same - the content writers are refused unless the offer has a revision that
is `OPEN`:

```text
POST   /api/commercial-offers/{public_id}/lines                                         -> 422
PUT    /api/commercial-offers/{public_id}/lines/{line_public_id}                        -> 422 (an edit or a cancellation)
POST   /api/commercial-offers/{public_id}/pricing-evidence                              -> 422
POST   /api/commercial-offers/{public_id}/pricing-evidence/{evidence_public_id}/select-basis -> 422
POST   /api/commercial-offers/{public_id}/tc-clauses                                    -> 422
POST   /api/commercial-offers/{public_id}/tc-clauses/attach-recommended                 -> 422 when it would attach any
DELETE /api/commercial-offers/{public_id}/tc-clauses/{attachment_public_id}             -> 422
POST   /api/commercial-offers/{public_id}/credit-review                                 -> 422
POST   /api/commercial-offers/{public_id}/submission-evidence                           -> 422
       "This Commercial Offer is Submitted, so its lines, prices, T&C, credit reviews and submission evidence change
        only through a revised offer. Start a revised offer on the Submission tab, make the change, record how the
        revised offer was sent, then mark it as re-sent."
```

Nothing is written and no event is recorded. A final offer is refused first, with the 6M.1 message, whether or not a
revision was left open on it; an offer before submission is unchanged. All of this is one helper,
`_lock_offer_for_content_change` in `services/common.py`, which every writer above already called: it takes the offer's
row lock, reads the status and, for a submitted offer, looks for the open revision under the same lock. For a line's
edit the refusal comes in step 3 of the CS-05a list below, after the final offer's refusal and before the line and the
version are read.

**How a revision works (Slice 6K), checked for this package.** A revision opens only on a `SUBMITTED` offer, one at a
time; it closes when it is marked resubmitted - citing submission evidence of the same offer, which is recorded while
the revision is open - or cancelled. So an open revision is the window in which a submitted offer is being revised,
and the rule needs no new state. One change was needed to make "only through a revision" hold under concurrency:
marking a revision resubmitted and cancelling it took no lock on the offer (their own `UPDATE ... WHERE revision_status
= 'OPEN'` already stopped a double close). They now take the offer's row lock before reading the revision, as opening
one already did, so a change queued behind a close reads the revision closed and is refused, and a change ahead of it
is made while it is open.

**The same lock serialises mark-submitted** (TB1-301 (d)), which already held it while it read the lines and the current
credit review: a line cancellation or a Rejected / On Hold credit review waiting behind it is refused once the offer is
submitted, and one ahead of it is what mark-submitted then reads ("At least one active Commercial Offer line ...", "...
Rejected or On Hold ..."). A submitted offer can no longer be left with no active line, or with a held credit review,
by a race or without one.

**Not changed.** The offer's own fields that the general update saves with the status unchanged (title, value,
currency, dates, remarks, submission and outcome fields - rule 4 of the 6M.1 section) stay editable on a submitted
offer, as on a final one; the owner's brief scoped this package to the five kinds of content above. Cancelling a
revision does not undo what was changed while it was open: each change and the cancellation are in the offer's events,
and a snapshot of the submitted version stays deferred ("Prior submitted version lock/tamper evidence",
`DEFERRED_REQUIREMENTS.md`). Marking a revision resubmitted does not repeat mark-submitted's checks of active lines and
the credit review. Generating a quotation version is not a change to the offer's content and is unchanged.

The offer page follows: on a submitted offer with no revised offer in progress, the line, pricing, T&C, credit-review
and submission-evidence forms and buttons give way to the same sentence; once a revised offer is started they come
back. The revision panel says that its changes stay if it is cancelled (`offerStatus.ts`, `offerContentLocked(status,
hasOpenRevision)`).

*Superseded the same day by Slice 9F (reconciled 12 October 2026):* the open-revision window described above no longer
exists. `_lock_offer_for_content_change` refuses every content change on a row past `DRAFT` and `READY_FOR_REVIEW`,
whether or not a legacy revision is open, and new Slice 6K revision cycles are refused; a change to a sent offer is
made in a new version. The "Not changed" paragraph is superseded too: a sent offer's header content is locked, and only
its outcome date and remarks stay editable (the 6M.1 reconciliation above). The page's `offerContentLocked` now takes
the status alone.

### 2. One active Base Offer per Opportunity, held by the database

Migration `20260908_0053` adds the partial unique index the deferred entry described, over exactly the rule creation
checks (Slice 6B.1, scoped to Base Offers by 6O.1):

```sql
CREATE UNIQUE INDEX ux_crm_commercial_offer_one_active_base_per_opportunity ON crm_commercial_offer (opportunity_id)
WHERE offer_purpose = 'BASE' AND offer_status_code NOT IN ('WITHDRAWN', 'REJECTED', 'CLOSED')
```

The statuses are `COMMERCIAL_OFFER_INACTIVE_FOR_NEW_OFFER_STATUSES`; a test holds the migration's list equal to it and
reads the index's definition. Supplementary Offers and Change Quotations never count. The upgrade first looks for an
Opportunity with two active Base Offers - before Slice 9B a late award could bring a rejected offer back beside its
replacement - and, finding one, stops and names each offer and its status, changing nothing; which one stays active is
the business's choice, made by hand. Creation still locks the Opportunity and checks first, so a second creation gets
the check's `422`; the index holds the rule against any writer that does not take that lock.

*Reconciled 12 October 2026:* migration `20260908_0054` (Slice 9F) rebuilt this index for versions. Its condition is
now:

```sql
offer_purpose = 'BASE'
AND offer_status_code NOT IN ('WITHDRAWN', 'REJECTED', 'CLOSED', 'REVISED', 'ABANDONED')
AND (previous_version_offer_id IS NULL OR offer_status_code NOT IN ('DRAFT', 'READY_FOR_REVIEW'))
```

A replaced or abandoned version does not count, and neither does a later version still in preparation.

### 3. A duplicate the database refuses is answered, not a 500

Four database rules refuse a duplicate two requests make at once. Each command checks first, under the offer's row lock
(or the Opportunity's, for a new Base Offer), so through the application a double click gets the check's answer - the
second attach of a clause is told it is attached; a second basis-rate choice or credit review replaces the first, as
one after another always did. A rule is reached only when a writer that takes no such lock commits the duplicate after
the check; the module now answers it instead of a `500`:

```text
rule                                                     routes                                      answer
ux_crm_commercial_offer_one_active_base_per_opportunity  POST /api/commercial-offers                 422, the check's own message, naming the
                                                                                                     active offer
ux_crm_commercial_offer_line_basis_choice_one_open       POST .../pricing-evidence (a selected one); 409, "Someone else chose a basis rate for this
(Slice 4G; before it, ..._pricing_evidence_one_selected, POST .../select-basis                       line at the same time, so yours was not
one per offer)                                                                                       saved. Reload the page to see which rate is
                                                                                                     selected, then choose again if you still
                                                                                                     need to."
uq_commercial_offer_tc_clause_active_clause              POST .../tc-clauses, .../attach-recommended 422, "T&C clause <id> is already attached to
                                                                                                     this Commercial Offer." (the check's message)
ux_commercial_offer_credit_review_current                POST .../credit-review                      409, "Someone else recorded a credit review for
                                                                                                     this Commercial Offer at the same time, so
                                                                                                     yours was not saved. Reload the page to see
                                                                                                     it, then record yours again if it is still
                                                                                                     needed."
```

Only these four rules are answered (`_refuse_duplicate` in `services/common.py`); any other database error is raised as
it came, to the server's own handler (TB1-503). The answer is logged at warning level by what identifies the rule - the
error's class, SQLSTATE, table, constraint and the code path, `app.core.errors.database_error_fields` - never the
database's message, whose DETAIL line repeats the duplicated key (`CODING_STANDARDS.md` section 9). The two `409`s are
new on those three routes; the errors keep this module's `{"detail": "..."}` shape until CS-06.

No new route, permission, event name, request or response field. TB1-304's other parts - GSTIN, Lead conversion, a
first PAN profile, an amendment's customer reference - are CS-05b's and PF-1B's.

## Slice 9F (10 October 2026): immutable Commercial Offer versions

Slice 9F supersedes CS-05c's in-place content-change window for all new work. A submitted Commercial Offer row is
commercial history and never changes its commercial content. A customer-facing change starts a new copied row in the
same offer series.

### Identity and data

Every offer response adds:

```text
version_number
previous_version_offer_public_id
version_reason
version_note
replaced_by_offer_public_id
replaced_by_version_number
```

Versions share `offer_code`; `(offer_code, version_number)` is unique when a code exists. `version_number` starts at
1 and never reuses an abandoned number. `previous_version_offer_id` is an internal self-reference to the exact row
copied. API and UI links use only public IDs.

Creating a version copies the offer header and relationship fields, active lines, all pricing evidence including the
selected basis, active offer-level T&C attachments and the current active credit review. Each copied child receives a
new public ID. Submission evidence, quote documents, customer responses and legacy revision rows are not copied.

### Routes and authority

```text
GET  /api/commercial-offers/{public_id}/versions          COMMERCIAL_OFFER_READ
POST /api/commercial-offers/{public_id}/versions          COMMERCIAL_OFFER_UPDATE
POST /api/commercial-offers/{public_id}/abandon-version   COMMERCIAL_OFFER_UPDATE
```

The list is oldest first. A new version may be made only from the latest `SUBMITTED` version, with no Draft/Ready
later version already in preparation. Abandonment is allowed only on a later Draft/Ready version and sets
`ABANDONED`; its submitted predecessor remains unchanged. The backend permission check is authoritative.

### Submission, immutability and outcomes

Only `DRAFT` and `READY_FOR_REVIEW` rows accept commercial-content changes. A sent, replaced, abandoned or concluded
row rejects changes to its header content, lines, pricing, selected basis, T&C, credit review and submission evidence.
A `SUBMITTED` row may still move to `WITHDRAWN` or `CLOSED` and may record outcome date/remarks. Outcome notes may
remain on the current sent version while a successor is prepared; withdrawal, closure and customer responses are
refused until that preparation version is sent or abandoned. The latest live version also keeps outcome date/remarks
editable after it reaches `ACCEPTED`, `REJECTED`, `WITHDRAWN` or `CLOSED`; its status and every commercial-content
field remain locked. `REVISED` and `ABANDONED` history accepts no update, including outcome notes.

A later Draft/Ready version cannot be moved to `WITHDRAWN` or `CLOSED` through general update. It remains Draft/Ready
until the controlled submit action sends it, or the dedicated abandon action records `ABANDONED`. Lifecycle guidance
also reports that the predecessor cannot take a customer response until the preparation version is sent or abandoned.

Marking a later version submitted locks the predecessor and current row in a deterministic order and, in one
transaction, requires the predecessor still to be `SUBMITTED`, moves it to `REVISED`, and moves the current row to
`SUBMITTED`. The event payload identifies the predecessor and its new status. A customer response, acceptance and Work
Order handoff belong only to the latest live version. The frozen handoff payload and line identity contract are
unchanged because handoff continues to use that accepted row and its own copied lines.

### Statuses, reports and quotations

`REVISED` means a submitted version was replaced by a later submitted version. `ABANDONED` means a later preparation
was stopped before submission. Both are read-only history and are excluded from open-offer reporting. A Draft/Ready
later version is also excluded while its submitted predecessor is counted, preventing double counting.

A Draft quotation document already generated for a version cannot be approved for issue after that offer version
becomes `REVISED` or `ABANDONED`; only a current live version may receive that customer-facing authorization.

Quotation numbering remains per offer row. Version 1 retains `CO-000123/V1`; the first quotation generated for offer
version 2 is `CO-000123 v2/V1`. The quotation snapshot and fingerprint shape do not change.

### Events

```text
CommercialOfferVersionCreated
CommercialOfferVersionAbandoned
CommercialOfferVersionReplaced    recorded on the predecessor when the later version is sent
CommercialOfferCommerciallyCommitted  existing event; version submission payload names the predecessor
```

Reads record no event. Event payloads use public IDs and contain no credentials or secrets.

### Legacy Slice 6K compatibility

`POST /revisions` refuses every new in-place cycle and points the caller to **Make a new version**. Existing legacy
revision rows remain readable; an existing OPEN row may still be marked resubmitted or cancelled through the original
routes. `can_open_revision` remains in the lifecycle response for compatibility and is false; additive
`can_make_new_version` governs the new action.

### Explicitly deferred

Side-by-side version comparison, legal/deviation approval, calculated credit/exposure gating, server-side PDF,
tender/BOQ automation and downstream Work Order amendment application are not part of 9F.

## Slice 4G (11 October 2026): market rates per offer line

Slice record: `docs/agent/slices/slice-4g-market-rates-per-offer-line.md`; acceptance:
`docs/agent/acceptance/slice-4g-market-rates-per-offer-line-acceptance.md`. Migration `20260908_0055`.

### Business rules (owner, 11 October 2026)

- A market or historical rate belongs to one line of its offer. A rate is entered on each line it applies to, even
  when one vendor quote covers two lines (the same crane at two sites).
- Each line has at most one basis rate. Choosing one needs a reason. A basis rate is never removed, only replaced by
  choosing another rate on the same line, with a reason; the earlier choice becomes history and is never overwritten or
  deleted. Each line shows its history: which rate, who chose it, when and why, and when it stopped being the basis
  ("Was the basis until <date>, chosen by <name>: <reason>").
- A rate's currency may differ from its line's; nothing is converted (Q-08).
- The submission readiness checklist warns, per line, about a line with no rate and a line with rates but no basis rate.
  It never blocks recording the offer as sent.
- A broker's quote (a WhatsApp screenshot, an email kept as a PDF or picture, a PDF or Word document) is attached to the
  rate as a `VENDOR_QUOTE` document. When one document covers several lines, it is attached to one line's rate and the
  other lines' rates refer to that rate for their quote copy.
- A cancelled line keeps its rates and basis history, read-only: no rate, basis choice or quote copy is added to it.
- Rates recorded before Slice 4G belong to the whole offer. They stay as they were, are never moved to a line, can no
  longer be chosen and take no new file, and count for no line in the checklist. The screen lists them under "Rates
  recorded for the whole offer, before rates were kept per line".
- Rates stay unchangeable on a Submitted, Revised or Abandoned version (CS-05c, 9F): every write, and attaching a quote
  copy, takes the offer's row lock and is refused once the version is sent.

### Data

```text
crm_commercial_offer_pricing_evidence
  commercial_offer_line_id   nullable; (commercial_offer_line_id, commercial_offer_id) references the line on the same
                             offer (composite foreign key; the line table gains unique (id, commercial_offer_id))
  recorded_for_whole_offer   true only for rates recorded before Slice 4G; check:
                             (commercial_offer_line_id IS NULL) = recorded_for_whole_offer
  quote_copy_evidence_id     nullable; a user's reference to another rate of the SAME offer whose attached document
                             holds this rate's quote ((quote_copy_evidence_id, commercial_offer_id) references
                             (id, commercial_offer_id); review 4G-R4-005)
  copied_from_evidence_id,   a new version's rate's link to the rate it was copied from, on the offer its own offer
  copied_from_offer_id       was made from: (copied_from_evidence_id, copied_from_offer_id) references the rate on that
                             offer, and (commercial_offer_id, copied_from_offer_id) references (id,
                             previous_version_offer_id) of crm_commercial_offer; both or neither; earlier id only.
                             A rate has at most one of the two links, and its quote copy is found through either
                             check: NULL or smaller than the rate's own id - only an earlier rate, never itself
                             or a later one, so a chain of references ends and cannot loop (review 4G-R3-001)
  ck_..._line_basis_in_history     recorded_for_whole_offer OR NOT is_selected_basis: a line's rate never carries the
                                   stored marker; its basis is its line's open choice below (review 4G-R1-002)
  ux_..._one_whole_offer_basis     unique (commercial_offer_id) where selected and for the whole offer
  (these replace ux_crm_commercial_offer_pricing_evidence_one_selected)

crm_commercial_offer_line_basis_choice     each line's basis history
  choice_public_id, commercial_offer_line_id, pricing_evidence_id (the rate, which must be on that line: composite
  foreign key), selection_reason (required), chosen_by, chosen_at, ended_by, ended_at, carried_from_choice_id
  ux_crm_commercial_offer_line_basis_choice_one_open   unique (commercial_offer_line_id) where ended_at is null
```

A line's basis is one record only: the line's open choice. The API's `is_selected_basis` for a line's rate is derived
from it (the rate holds the line's open choice), and its `selection_reason` is that choice's reason, so the two cannot
disagree. The stored `is_selected_basis` and `selection_reason` columns are kept for whole-offer rates only.

### API

```text
GET  /api/commercial-offers/{public_id}/pricing-evidence                                      unchanged route
POST /api/commercial-offers/{public_id}/pricing-evidence                                      line_public_id required
POST /api/commercial-offers/{public_id}/pricing-evidence/{evidence_public_id}/select-basis   per line
```

- Create: `line_public_id`, required by the request schema (an active line of the same offer; otherwise `422` -
  the request's own validation error when it is missing, "That line is not a line of this Commercial Offer.", or
  "Line N is cancelled, ..."), optional
  `quote_copy_rate_public_id` (another rate of the same offer whose quote copy - its own, or one it refers to - is
  attached already; otherwise `422`, "... has no quote attached yet. Attach the quote to that rate first."). `is_selected_basis` with a
  `selection_reason` chooses it as its line's basis in the same request.
- Select: refused (`422`) for a whole-offer rate, a rate on a cancelled line, and the rate that is already its line's
  basis; a reason is required. The response adds `previous_basis_rate_public_id`.
- Each rate in a response adds `line_public_id`, `line_number`, `line_status_code`, `recorded_for_whole_offer`,
  `quote_copy_rate_public_id`, `quote_copies` (each: `document_public_id`, `file_name`, `uploaded_at`,
  `attached_to_rate_public_id`, `attached_to_line_number`, `attached_to_offer_version_number`, `attached_here`) and
  `basis_history` (each choice: `public_id`, `pricing_evidence_public_id`, `selection_reason`, `chosen_by`,
  `chosen_by_display_name`, `chosen_at`, `ended_by`, `ended_by_display_name`, `ended_at`, `is_current`,
  `carried_over_from_version_number`). `selection_reason` is the current choice's reason, empty when the rate is not
  the basis.
- Quote copies use the documents module's routes. Linked record type `commercial_offer_market_rate`: reading needs
  `COMMERCIAL_OFFER_READ`, attaching `COMMERCIAL_OFFER_PRICING_EVIDENCE_WRITE`. The module's attach check refuses
  (`422`) any type but `VENDOR_QUOTE`, a link to a file kept elsewhere, a whole-offer rate, a rate on a cancelled line
  (read again under the offer's lock), and a rate on a version that can no longer change. The documents module refuses
  (`422`) a `VENDOR_QUOTE` filed against any other linked record type, on both routes, so a quote cannot skip that
  check (review 4G-R1-001).

### Events

`CommercialOfferMarketRateAdded`, `CommercialOfferHistoricalRateAdded` and `CommercialOfferBasisRateSelected` carry
`line_public_id` and `line_number`; a rate added with a quote reference carries
`quote_copy_pricing_evidence_public_id`; a basis choice carries `previous_basis_pricing_evidence_public_id` (empty for
a line's first choice). The record type is still the Commercial Offer.

### Versions (Slice 9F)

`copy_commercial_offer_version_children` copies each active line's rates onto the matching copied line, each line's
current basis choice as an open choice naming the choice it was carried from (same rate, reason, chooser and time), and
whole-offer rates as they are. Each copy is linked to the rate it was copied from (`copied_from_evidence_id`), held
by the database to the offer its version was made from, and its quote copy is found through that link, so a quote
attached on an earlier version still shows. A copy carries no user reference: its `quote_copy_rate_public_id` is
empty. A cancelled line is not copied, so its rates stay on the earlier version.

### Unchanged

Quotation documents exclude pricing evidence and the quote snapshot fingerprint does not read it. The Work Order handoff
copies no pricing evidence; the frozen handoff contract's "Pricing evidence reference - include where available" stays
unimplemented. Who may enter a rate and who may choose the basis are still one permission
(`DEFERRED_REQUIREMENTS.md`), and markup over the basis rate is not modelled.

## Entered times (11 October 2026): a date and time carries its zone

Found in the Slice 4G screen check: a market rate's "Collected at" typed as 10:30 showed as 4:00 pm. The page sent the
India time typed with no zone, the backend stored it in a UTC column as it came, and the page read it back as UTC. The
rule now (ADR-028, "Timestamps"; `docs/agent/slices/entered-times-in-india.md`):

- `submitted_at` on `PUT /api/commercial-offers/{public_id}`, `collected_at` on `POST .../pricing-evidence`,
  `submitted_at` on `POST .../submission-evidence`, `reviewed_at` on `POST .../credit-review`, `response_received_at`
  on `POST .../customer-responses` and `opened_at` on `POST .../revisions` take a date and time only with its zone
  (`Z` or an offset such as `+05:30`) - text in the ISO form; a number or digits, which would otherwise be read as
  seconds since 1970, are refused too. One with no zone is refused with `422`: "Give the date and time with its time
  zone, for example 2026-10-12T05:00:00Z or 2026-10-12T10:30:00+05:30." Any offset is converted to UTC and stored as
  UTC. This is an intentional tightening of these routes' request contract: a time with no zone was accepted before
  and stored as if it were UTC, and a caller that sent one must now send its zone. Field names and types are unchanged.
- The page sends a time typed in India as the same moment in UTC with `Z`. The records' times in responses are
  unchanged in form - these columns' times come back in UTC with no zone, and the page shows them in India's time.
- A customer response that accepts or rejects the offer sets `outcome_date` to the day the response was received **in
  India** (`business_time.india_date`): 00:30 on 12 October in India is 12 October, though it is still 11 October in
  UTC. The `CommercialOfferCustomerResponseRecorded` event's `response_received_at` - in the stored event and in the
  `event` of the `POST` response - is the time as received, now always in UTC with `+00:00`; before, it was the time
  as sent (with no zone when the page sent none).
- Dates (`offer_date`, `valid_until`, `outcome_date` as sent) are unchanged.
- Rows typed on screen before this change keep India's time in a UTC column and show 5 hours 30 minutes late; there is
  no data migration (the slice record says why). The test sites are cleared by the October reset.

## Quotation totals per currency (12 October 2026)

An offer line may be in a currency other than its offer's (TB1-600, above), and amounts in different currencies are
never added together (`AGENTS.md`, "Currency"). The Slice 9E quotation broke that rule: it added every line into one
total and labelled it with the offer's currency, so an INR offer with a USD line printed a wrong customer-facing total.
Found by the vendor-baseline audit of 12 October 2026; fixed in `services/quote_documents.py` and `quote_render.py`.

- **Snapshot.** A snapshot line carries `currency_code` only when its currency differs from the offer's. `total_amount`
  is the total of the lines in the offer's own currency. Codes are compared trimmed and upper-cased
  (`currency_code_key`, `app/shared/currency.py`), as they are stored since TB1-600: a row saved before it may hold
  its code in another case and is still the same currency.
- **Document.** When every line is in the offer's currency the document is exactly as before, byte for byte. Otherwise
  each rate and amount shows its currency code, there is one "Total (CUR)" row per currency (the offer's currency first,
  then the others alphabetically), the header reads "Currencies: INR, USD" (or "Currency: USD" when every line is in one
  other currency), and a note under the GST note says each currency is totalled separately and nothing is converted.
  "Not priced" and "Not fully priced" apply to each currency's total on its own.
- **Stored versions and `schema_version`.** The snapshot of an offer whose lines are all in its own currency is
  unchanged, so its stored fingerprint still matches and nothing reports changed; checked by building every seeded
  offer's snapshot and document with the code before and after the fix (14 offers, identical fingerprints and HTML).
  Only an offer with a line in another currency gets a new fingerprint, so a version generated for it before the fix
  reports that the offer has changed and cannot be approved for issue - correct, since its frozen document carries the
  wrong total; generate a new version. The snapshot's `schema_version` stays `1.0` for that reason: bumping it would
  make every stored version report a change its offer never had (Slice 9E, "Snapshot and staleness").
- No route, permission, event, migration or approval rule changes. Tests: `test_slice_9e_quotation_generation.py`, the
  "Lines in more than one currency" group.
