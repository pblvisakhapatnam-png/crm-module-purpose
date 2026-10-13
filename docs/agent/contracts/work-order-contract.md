# Work Order Contract

## Purpose

Slice 5A introduces Work Order as the downstream handoff shell created from an Accepted Commercial Offer.

The shell is intentionally thin. It preserves traceability from Account / business_party, Opportunity, Commercial Offer and Commercial Offer lines into Work Order and Work Order lines. It does not implement Equipment Hiring execution, Customer Master activation, WO release/posting, log sheets, billing or invoice support.

## API routes

- `POST /api/work-orders/from-commercial-offer`
- `GET /api/work-orders`
- `GET /api/work-orders/{public_id}`
- `GET /api/work-orders/{public_id}/lines`

All routes are under `/api` and frontend callers must use relative `/api/...` URLs.

## Slice 6A linked-record listing

Slice 6A keeps the Work Order shell thin but adds a traceability filter to the existing list route:

```text
GET /api/work-orders?commercial_offer_public_id={commercial_offer_public_id}
```

The filter returns Work Order shells generated from the specified Commercial Offer. It uses the existing `WorkOrderResponse` shape and existing Work Order read permissions. It does not add release/posting, Customer Master activation, equipment assignment, crew assignment, log sheets or billing.

## Create from Commercial Offer

Creation is allowed only from an Accepted Commercial Offer.

Slice 6A.1 adds an Account traceability guard: creation is also blocked when the source Commercial Offer cannot resolve an Account through its own copied `business_party_id` or the linked Opportunity `business_party_id`.

Expected response when Account traceability is missing:

```text
422 Unprocessable Entity
```

The user-facing message should use `Account` and make clear that a minimal/provisional Account / Qualified Prospect is sufficient for traceability. It must not imply Customer Master activation.

Payload:

```json
{
  "commercial_offer_public_id": "uuid",
  "selected_offer_line_public_ids": ["uuid"],
  "customer_wo_reference": "optional customer WO reference",
  "received_date": "YYYY-MM-DD",
  "remarks": "optional remarks"
}
```

If no selected line ids are supplied, all active Commercial Offer lines are copied. If selected ids are supplied, each must belong to the accepted offer and be active.

### CS-04 part 1: what may be handed off, and how often (8 October 2026)

The owner's decisions of 8 October 2026, recorded as the dated amendment at the end of the frozen
`accepted-offer-to-work-order-handoff-contract.md` and in `docs/continuity/TB1_103_WORK_ORDER_HANDOFF_ONCE_PER_LINE.md`.
They change the paragraph above as follows.

- **An offer line's quantity goes onto Work Orders once, whole or in parts.** The Work Order lines made from one offer
  line together hold no more than that line's quantity. An optional `selected_offer_line_quantities` names how much of
  a selected line this Work Order takes:

  ```json
  "selected_offer_line_quantities": [{"offer_line_public_id": "uuid", "quantity": "3.00"}]
  ```

  A selected line not named takes all that is left of it. A quantity must be above zero, for a selected line, named
  once (`422` otherwise). With no line selected, every active line with something left is taken, for all that is left;
  a line already on Work Orders in full is passed over. A part's `line_amount` is the line's amount up to the end of the
  part less its amount up to the part's start, each the rate times the quantity so far rounded to the paisa, so the
  parts add up to the line's amount exactly and none is below zero; a line taken whole keeps the offer's own amount. The other copied fields keep their meaning, and the
  response shape is unchanged.
- **`409 Conflict`** when a selected line has nothing left or less than asked, or - with no line selected - every line
  is on Work Orders in full. The message names each Work Order holding the line and its quantity, for example
  `Line 1 has 4 of 10 left to hand off (on a Work Order: WO-001852 (6)); 6 was asked.` The check runs under the offer's
  row lock, so two requests at once never together pass the line's quantity: when both cannot fit, one gets the Work
  Order and the other the `409`. A database rule (migration `20260908_0049`)
  holds the total for any writer, and its refusal is answered with the same `409`, never a `500`; further rules
  keep an offer line's own quantity from going below what its Work Orders hold, a Work Order line to lines of its own
  Work Order's offer, and an offer with a Work Order from becoming a Change Quotation. What each line has left is read
  from the offer's lifecycle view (`line_handoff`, `commercial-offer-contract.md`).
- **`422`** when the offer is a Change Quotation (it is cited on a Work Order amendment instead) or when the offer's
  latest customer response - by the date the customer responded, as the offer's lifecycle view counts it - is not
  `ACCEPTED_AWARDED`. A Base Offer and a Supplementary Offer may both be handed off. The status and Account checks come
  first, as before.
- **`customer_wo_reference` is required** - the customer's order number, or the Letter of Intent's (`422`
  otherwise) - and one offer never has two Work Orders with the same reference (`409`, naming the Work Order that has
  it). Two references are the same when they match without case and without the whitespace around them: every
  character Python's `str.isspace()` accepts, which is what the handoff strips - spaces, tabs, line breaks, no-break
  and the other Unicode spaces - held as `WORK_ORDER_REFERENCE_SPACE` in `work_orders/contract.py` and as the same
  class in migration `20260908_0049`. A reference of that whitespace alone is no reference. One customer order makes
  one Work Order, so a repeated request - whole line or part, a second tab, two people at once - is refused; a second
  order of the same size carries its own number. The same reference may be on Work Orders of different offers. A
  unique index holds it for any writer; Work Orders made before migration `20260908_0049` without a reference keep it
  empty (the owner, 8 October 2026, after review round 3). A request key that would replay a repeated request is CS-04
  part 2.

### CS-04 part 2, items c and d: the offer's version and the lines handed off (12 October 2026)

The owner's approval of 12 October 2026, recorded as the second dated amendment at the end of the frozen handoff
contract. The Work Order output (the handoff's response and both read routes) carries
`commercial_offer_version_number`, the handed-off offer row's version (`1` for an offer never versioned), and a Work
Order from a later version is titled "Work Order from CO-000123 v2". `WorkOrderCreated` and
`CommercialOfferConvertedToWorkOrder` carry the version too, and `CommercialOfferConvertedToWorkOrder` lists each Work
Order line made: `offer_line_public_id`, `work_order_line_public_id`, `line_number`, `quantity` and `line_amount`
(decimal text; a line taken whole keeps the offer line's own amount, `null` when that line has none; a part of a line
with no rate is `null`), `uom` and `currency_code`. The Work Order pages and the Create Work Order page show the offer as "CO-000123 v2". The request
key (a repeat answered with the Work Order it made) and a correlation id are agreed for the PF-1B retrofit and not
built; until then a repeat is refused by its customer reference.

**Where the runtime differs from the frozen contract's text** (12 October 2026; none changed by this or the first
amendment, recorded so that nobody takes the frozen text for what the code does):

- Of the production-MVP header fields the frozen contract lists, these are not in the request, response or events:
  Account display name and PAN, offer mode, the acceptance or award reference and date, document references, the
  credit-decision reference and source event references; its own "thinner implemented payload" clause allows this.
  The source status is there, as the Work Order's `source_offer_status_code`. `received_date` is optional.
- The initial status is `HANDOFF_CREATED`, the prototype mapping of `HANDOFF_RECEIVED`, as the frozen contract allows.
- Each Work Order line's status is set to `HANDOFF_CREATED`, not copied from the offer line.
- The Account is the offer's own, or else its Opportunity's (`COALESCE`); the two are not checked to agree.
- The response's lines carry `source_offer_line_number` as well, as the read routes do.
- An offer line in USD, GBP or EUR is copied in that currency, while billing terms are in INR only
  (`DEFERRED_REQUIREMENTS.md`, "Currencies other than INR").
- The fixture pack under `docs/agent/fixtures/accepted-offer-work-order/` predates both amendments: it has no customer
  reference or quantity split, and uses logical names (`work_order_number`, `HANDOFF_RECEIVED`, line statuses
  `AWARDED`) the runtime does not. It is illustrative, checked only for its own consistency
  (`scripts/validate_contract_fixtures.py`).

## Work Order fields

Foundation response fields include:

- `public_id`
- `work_order_code`
- `work_order_title`
- `work_order_status_code`
- `commercial_offer_public_id`
- `commercial_offer_code`
- `commercial_offer_version_number` (since 12 October 2026)
- `opportunity_public_id`
- `account_public_id`
- `customer_wo_reference`
- `received_date`
- `source_offer_status_code`
- `remarks`
- timestamps

## Work Order line fields

Foundation line fields include:

- `public_id`
- `work_order_public_id`
- `source_offer_line_public_id`
- `line_number`
- `line_status_code`
- `scope_description`
- `equipment_service_category`
- `quantity`
- `uom`
- `rate_amount`
- `currency_code`
- `line_amount`
- `remarks`

Future agents must preserve `source_offer_line_public_id` when adding site, GSTN, billing terms, allocation, log sheet and billing functions.

## Statuses

Slice 5A seeds a small Work Order workflow module:

- `DRAFT`
- `HANDOFF_CREATED`
- `EXECUTION_DEFERRED`
- `CLOSED`

Slice 5A creates Work Orders as `HANDOFF_CREATED`.

## Events

Slice 5A records:

- `WorkOrderCreated`
- `CommercialOfferConvertedToWorkOrder`

## Deferred controls

Future agents must add:

- Customer Master creation/activation and Finance approval before WO release/posting.
- Work Order release/posting gate.
- Site-wise GSTN and billing terms.
- Equipment/vendor/crew allocation.
- Log sheet and billing integration.
- Execution, demobilization, invoice support and profitability links.

## Slice 6D.1 Accepted Offer to Work Order handoff freeze

Slice 6D.1 freezes the logical Accepted Commercial Offer to Work Order shell handoff:

```text
docs/agent/contracts/accepted-offer-to-work-order-handoff-contract.md
```

Work Order implementation after this point must preserve:

```text
- Work Order public ID and work order code/number.
- linked Commercial Offer ID and version/reference.
- linked Opportunity public ID.
- linked Account public ID.
- Work Order lines linked to source Commercial Offer line public IDs.
- unreleased initial shell status.
- handoff business event/audit references.
```

Current prototype mapping:

```text
HANDOFF_CREATED
WorkOrderCreated
CommercialOfferConvertedToWorkOrder
```

Production MVP may choose `DRAFT`, `HANDOFF_RECEIVED` or `PENDING_CUSTOMER_MASTER` for the initial shell status, but the status must remain unreleased and must not allow posting, execution, assignment, log sheets, billing or invoicing by itself.

## Slice 6O Work Order shell detail and handoff review UI

Slice 6O is a UI/traceability polish slice over the existing `GET /api/work-orders/{public_id}` and `GET /api/work-orders/{public_id}/lines` responses. It adds no new Work Order fields, routes, schema or migration; every field it displays (`created_by`, `updated_at`, `source_offer_line_public_id`, etc.) already existed in `WorkOrderResponse` / `WorkOrderLineResponse`.

The only backend change introduced by Slice 6O is outside this module: `GET /api/events/recent` (events module) gained optional `record_type` and `record_public_id` query filters so the Work Order detail page can show the specific `WorkOrderCreated` business event for that shell to `ADMIN` / `MANAGEMENT_READ_ONLY` roles, without scanning the full recent-events feed. This is backward compatible - omitting the new parameters reproduces the exact prior unfiltered behavior - and does not change Work Order permissions, which remain exactly `WORK_ORDER_CREATE_ROLES` / `WORK_ORDER_READ_ROLES` as defined in `backend/app/modules/work_orders/routes.py`. *(Reconciled 7 October 2026, TB-1 TB1-904: PF-1A-E1 replaced those role constants with the permission codes `WORK_ORDER_CREATE` and `WORK_ORDER_READ`, whose grants are in `backend/app/modules/authorization/contract.py`; the roles are unchanged.)*

Frontend behaviour added by Slice 6O:

```text
- Commercial Offer Submission tab: a "Work Order handoff review" snapshot inside the existing
  Lifecycle Guidance panel, shown only while the offer is Accepted, reusing that panel's existing
  backend-derived readiness data rather than re-deriving lifecycle rules in the frontend.
- /work-orders/new: offer mode/type/date context and an explicit existing-shell summary before
  the explicit create action.
- Work Order detail page: a "Handoff shell" status badge, created-by/last-updated fields, a
  "Handoff provenance" section, and a contained/responsive line-traceability table.
```

Slice 6O does not change the frozen Slice 6D.1 handoff trigger, payload, output contract, or the partial-award rule (one accepted Commercial Offer may still create more than one Work Order shell). The frontend continues the Slice 6M/6M.1 conservative default of offering "Create Work Order shell" only while zero shells exist for an offer, and "Open" for any that already exist; it does not add allocation/remaining-quantity logic to safely offer a second one-click create action, and that limitation is recorded as deferred work rather than guessed at.

## Slice 6O.1 Related Commercial Offer visibility (non-normative)

Slice 6O.1 adds a read-only cross-reference from a Work Order shell to any Supplementary Offer
or Change Quotation (Slice 6O.1 Commercial Offer `offer_purpose`) linked to it via
`crm_commercial_offer.related_work_order_id`:

```text
GET /api/work-orders/{public_id}/related-offers
```

Read roles: the existing `WORK_ORDER_READ_ROLES` set. This route is purely additive traceability
and does not change the frozen Slice 6D.1 handoff contract, any existing Work Order route,
schema, permission or migration described above. A linked related offer never implies the Work
Order itself has been amended, released, posted or otherwise changed; the frontend Work Order
detail page explicitly avoids that claim. Work Order Amendment application is deferred to Slice
6O.2. See `docs/agent/contracts/commercial-offer-contract.md` (Slice 6O.1 section) for the full
related-offer contract.

## Slice 6O.2 Work Order Amendment intake foundation

Slice 6O.2 adds `crm_work_order_amendment` / `crm_work_order_amendment_line` as
subordinate intake/review records under an existing Work Order shell:

```text
GET    /api/work-orders/{public_id}/amendments
POST   /api/work-orders/{public_id}/amendments
GET    /api/work-orders/{public_id}/amendments/{amendment_public_id}
PUT    /api/work-orders/{public_id}/amendments/{amendment_public_id}
POST   /api/work-orders/{public_id}/amendments/{amendment_public_id}/decision
GET    /api/work-orders/{public_id}/amendments/{amendment_public_id}/readiness
GET    /api/work-orders/{public_id}/amendments/{amendment_public_id}/lines
POST   /api/work-orders/{public_id}/amendments/{amendment_public_id}/lines
PUT    /api/work-orders/{public_id}/amendments/{amendment_public_id}/lines/{line_public_id}
DELETE /api/work-orders/{public_id}/amendments/{amendment_public_id}/lines/{line_public_id}
```

Mutation roles reuse the existing `WORK_ORDER_CREATE_ROLES` set; read roles reuse
`WORK_ORDER_READ_ROLES`. An amendment moves `RECEIVED -> UNDER_REVIEW ->
VALIDATED/REJECTED/CANCELLED`; the latter three are terminal. A `COMMERCIAL`/`MIXED`
amendment may cite an accepted Slice 6O.1 Supplementary Offer or Change Quotation
already linked to this Work Order as its commercial basis, but validation is blocked
until that offer is independently `ACCEPTED`.

**Nothing under this route family is ever applied to `crm_work_order` or
`crm_work_order_line`.** "Validated" means validated for future downstream processing,
not applied. This is the same non-application boundary the Slice 6D.1 handoff and Slice
6O.1 related-offer contracts already establish for their own record types; Work Order
Amendments extend that boundary rather than crossing it. See
`docs/agent/contracts/work-order-amendment-contract.md` for the full contract
(amendment types, transition matrix, line actions, snapshot behaviour, events).

Application of a validated amendment to the Work Order (versioning, line replacement,
effective totals) remains explicit future work and is not implemented by this slice.

## UI cleanup package (September 2026): display names

Recorded 11 September 2026. One additive, read-only field so the screen can show a name instead of
a user public ID:

```text
WorkOrderReadResponse   (GET /api/work-orders, GET /api/work-orders/{public_id} only)
    created_by_display_name   beside created_by
```

The field is `string | null`, resolved from `app_user.display_name` matched on
`app_user.public_id` in the same query (a LEFT JOIN), and `null` when `created_by` is null or does
not match any user; the Work Order is still returned in that case. `created_by` is unchanged. Work
Order lines are unchanged. The Work Order Amendment response gains the same field; see
`work-order-amendment-contract.md`.

**The frozen Slice 6D.1 handoff output is deliberately unchanged.** `POST
/api/work-orders/from-commercial-offer` still returns `WorkOrderResponse` with exactly its previous
fields. The display name lives on `WorkOrderReadResponse`, a subclass used only by the two read
routes, rather than on the model the handoff returns - so the frozen output neither gains nor loses
a field, and the frozen contract file needs no change record. A test asserts both halves: the
handoff response carries no `created_by_display_name`, and the read routes do. No route,
permission, request field, business event or migration change.

## Pilot screen review (September 2026): source offer line number

Recorded 12 September 2026. One additive, read-only field, so a screen can name the source
Commercial Offer line instead of showing only its UUID:

```text
WorkOrderLineResponse   (GET /api/work-orders/{public_id}/lines)
    source_offer_line_number   beside source_offer_line_public_id
```

`int | null`, read from `crm_commercial_offer_line.line_number` through the LEFT JOIN the lines
query already performs, and null when the source line no longer resolves - the Work Order line is
still returned in that case. `source_offer_line_public_id` is unchanged and remains the identifier
the frozen Slice 6D.1 handoff traceability depends on. The Work Order detail page now renders
"CO-000013 line 2" with the UUID kept as secondary reference text. No route, permission, request
field, business event or migration change.

## Language pass (September 2026): display label

Recorded 11 September 2026. The UI shows the status code `HANDOFF_CREATED` as **Awaiting release
to Ops**, and calls the record a Work Order rather than a Work Order shell. The code, every field,
every route and the frozen Slice 6D.1 handoff contract are unchanged; only the words shown change.
The helper is `formatWorkOrderStatusLabel` in `frontend/src/components/PageLayout.tsx`. Backend
messages that said "Work Order shell" or "handoff" were reworded to match. See
`docs/agent/slices/ui-language-pass.md`.

## Slice 7C Work Order line operational detail

Recorded 14 September 2026. Detail consumed **after** handoff: the site the work happens at, the
GSTIN and address the customer is billed on, and the customer's own line reference. Full design and
owner decisions: `docs/agent/slices/slice-7c-work-order-line-operational-detail.md`.

**Changed by Slice 7D, 14 September 2026.** The billing basis and contracted hours moved from this
detail into the line's billing terms (section below), because they are part of the versioned term set
`WBT-001` describes. Migration `20260908_0037` copied every recorded basis and hours into period 1 of
that line's terms. The request, response, missing items and event payload below are the current
shape; as merged in 7C they also carried `billing_uom_code` and `contracted_hours_per_billing_unit`.

### Routes

```text
GET  /api/work-orders/{public_id}/line-details
     require_permission(WORK_ORDER_READ)
     one entry per Work Order line, in line order; detail fields null where none recorded

PUT  /api/work-orders/{public_id}/lines/{line_public_id}/detail
     require_permission(WORK_ORDER_LINE_DETAIL_WRITE)
     whole replacement; 200, 404 (Work Order or line), 409 (version conflict), 422 (validation)
```

`WORK_ORDER_LINE_DETAIL_WRITE` holds `ADMIN`, `SALES_USER`, `SALES_MANAGER`, `OPERATIONS_USER`.
It is its own code rather than a reuse of `WORK_ORDER_CREATE`, so a change to who creates Work
Orders cannot silently change who records billing identity.

### Request

```text
expected_detail_version             null before the first save; otherwise the version last read
site_address_public_id              active SITE address on the Work Order's own Account
billing_gstin_public_id             active GSTIN on that Account, not REJECTED_INCORRECT
billing_address_public_id           active REGISTERED_OFFICE or BILLING_DRAFT address on that Account
customer_line_reference             text, up to 255
operational_notes                   text, up to 4000; never read by any calculation
line_start_date, line_end_date      Slice 7D Part 3: the line's own dates inside the Work Order's
                                    contract period; both blank means the line follows the Work Order
site_central_government             8A core: is the site a central-government site - a railway or metro,
                                    a major port, an oil field or a mine (ELG-1 Q8)? true, false, or null
                                    (not answered). Left out of the request, it keeps what is recorded;
                                    sent as null, it clears
```

Every field may be null; an incomplete detail is allowed and reported, not refused. A reference to
another Account's record is refused with the same message as an unknown one. Any other field is
refused with `422` (since Slice 7D), so a caller still sending the billing basis learns it was not
saved here.

### Response entry

```text
work_order_line_public_id, line_number, source_offer_line_public_id
detail_public_id, detail_version                         null until the first save
site_address_public_id,    site_address    {public_id, address_type_code, address_line1, city, state, postal_code}
billing_gstin_public_id,   billing_gstin   {public_id, gstin, state_code, verification_state_code}
billing_address_public_id, billing_address {public_id, address_type_code, address_line1, city, state, postal_code}
customer_line_reference, operational_notes
line_start_date, line_end_date   Slice 7D Part 3; never reported missing, because blank means the
                                 line follows the Work Order
site_central_government          8A core; null until answered. Not a missing item: allocating a machine
                                 to the line's requirements needs it (resource-assignment-api-contract.md),
                                 and release (7B) will decide what it needs
is_complete, missing_items[]   SITE_ADDRESS | BILLING_GSTIN | BILLING_ADDRESS
updated_by, updated_by_display_name, updated_at
```

A picked reference that is no longer usable (address inactive, GSTIN since rejected) keeps its
`*_public_id`, returns its resolved object as null and appears in `missing_items`. Completeness is
computed on every read against the Account's records as they are now. The `PUT` response wraps one
entry as `line_detail` alongside `event`, which is null when the save changed nothing.

### Rules

- Refused on a `CLOSED` Work Order. The mobilisation lock (site, basis, hours, customer reference)
  and the e-invoice lock (billing GSTIN and address) are later slices' to add.
- An identical save records no event and keeps the version.
- Nothing blocks on incompleteness in this slice; Work Order release (7B) will.
- 8A core: a save that changes the line's own end, like saving the contract period or adding or removing an
  extension, calls the listeners registered through `register_end_dates_listener` (Resource Requirements, whose
  requirements without an end of their own run to it) in the same transaction, under the Work Order's row lock.
- 8A core: `hold_work_order_status` reads a Work Order's status under a shared lock on its row, held to the end of
  the caller's transaction. Resource Assignments and Resource Requirements take it first on every write, so a change
  to the Work Order - its closure, when that is built - waits for the write or is seen by it. No route; no event.

### Events

```text
WorkOrderLineDetailRecorded   first save
WorkOrderLineDetailUpdated    later changing save
record_type = work_order, record_public_id = Work Order public id
payload: work_order_line_public_id, detail_version, changed_fields[],
         site_address_public_id, billing_gstin_public_id, billing_address_public_id,
         line_start_date, line_end_date (7D Part 3), site_central_government (8A core)
```

Public ids and codes only; never the GSTIN value or address text.

### What is unchanged

`POST /api/work-orders/from-commercial-offer`, `GET /api/work-orders/{public_id}/lines`,
`WorkOrderResponse`, `WorkOrderLineResponse` and `crm_work_order_line` are untouched; the detail
lives in its own table, `crm_work_order_line_detail` (Alembic `20260908_0036`; 8A core's `20260908_0045` adds
the nullable boolean `site_central_government`). The frozen handoff
contract file is byte-identical, and a test pins the exact handoff response key sets.

## Slice 7D Part 1 Work Order line billing terms

Recorded 14 September 2026. The terms the customer's Work Order sets for each line, consumed after
handoff and implementing `WBT-001`'s term set in part. Full design and owner decisions:
`docs/agent/slices/slice-7d-work-order-line-billing-terms.md`. Part 2 (night/second shift,
mobilisation, demobilisation, fuel) adds fields to the same records.

### Periods

A line's terms are one or more **periods**. Period 1 starts with the contract and has no date of its
own; each later period has `effective_from` and applies from that date until the next period starts.
Dates strictly increase across a line's periods. Only the latest period can be removed, and never
period 1, which is corrected in place instead.

### Routes

```text
GET    /api/work-orders/{public_id}/billing-terms
       require_permission(WORK_ORDER_READ)
       one entry per Work Order line, in line order

POST   /api/work-orders/{public_id}/lines/{line_public_id}/billing-terms
       require_permission(WORK_ORDER_LINE_BILLING_TERMS_WRITE)
       add the next period; 201, 404, 409 (period count), 422

PUT    /api/work-orders/{public_id}/lines/{line_public_id}/billing-terms/{term_public_id}
       require_permission(WORK_ORDER_LINE_BILLING_TERMS_WRITE)
       whole replacement of one period; 200, 404, 409 (revision), 422

DELETE /api/work-orders/{public_id}/lines/{line_public_id}/billing-terms/{term_public_id}?expected_term_revision=N
       require_permission(WORK_ORDER_LINE_BILLING_TERMS_WRITE)
       remove the latest period; 200, 404, 409, 422
```

`WORK_ORDER_LINE_BILLING_TERMS_WRITE` holds `ADMIN`, `SALES_USER`, `SALES_MANAGER`, `OPERATIONS_USER`
(owner decision 5). All four routes are pinned in `POST_BASELINE_NEW_ROUTES`.

### Request

`POST` adds `expected_period_count` (the periods the caller saw) and `expected_latest_term_revision`
(the latest period's revision the caller saw, null when there is none); either differing is `409`.
`PUT` adds `expected_term_revision`. Both then carry every term; unknown fields are refused.

```text
effective_from                     null for period 1; required, later than the previous period and not
                                   0001-01-01 otherwise
billing_uom_code                   HOUR | SHIFT | DAY | MONTH
contracted_hours_per_billing_unit  > 0; SHIFT, DAY, MONTH (per shift, per day, per month)
contracted_working_days_per_month  > 0; MONTH
normal_rate_amount                 > 0; the Work Order rate per billing unit, INR
weekly_off_day_codes               subset of MON..SUN, never all seven; [] is a 7-day week; SHIFT, DAY, MONTH
off_day_work_treatment_code        NONE | OVERTIME_RATE | HOLIDAY_RATE | NORMAL_RATE; SHIFT, DAY, MONTH;
                                   OVERTIME_RATE is refused while overtime is NONE
holiday_rate_*                     only with HOLIDAY_RATE
overtime_rate_method_code          NONE | RATE_PER_HOUR | PERCENT_OF_NORMAL; SHIFT, DAY, MONTH
month_overtime_hours_basis_code    AVAILABLE_HOURS | ENGINE_HOURS; MONTH with overtime charged
month_overtime_counting_code       WHOLE_MONTH | DAY_BY_DAY; MONTH with overtime charged
breakdown_treatment_code           NONE | REDUCE_BILLED_HOURS | DEDUCT_AT_BREAKDOWN_RATE; SHIFT, DAY, MONTH
breakdown_rate_*                   only with DEDUCT_AT_BREAKDOWN_RATE
breakdown_offset_by_same_day_overtime  boolean; true only when breakdown is deducted and overtime charged
customer_idle_treatment_code       NONE | AS_WORKING_HOURS | STANDBY_RATE
standby_rate_*                     only with STANDBY_RATE
minimum_guarantee_code             NONE | UNITS_PER_MONTH; HOUR, SHIFT, DAY
minimum_billing_units_per_month    > 0; only with UNITS_PER_MONTH
part_month_basis_code              CALENDAR_DAYS | CONTRACTED_WORKING_DAYS | THIRTY_DAYS; MONTH
term_notes                         text, up to 4000; never read by any calculation
```

Each `*_rate_*` group is `_method_code` (`RATE_PER_HOUR` or `PERCENT_OF_NORMAL`), `_amount` and
`_percent`: exactly the value the method asks for, nothing else. Every number is finite and greater than
zero, and `weekly_off_day_codes` is a flat list; the database refuses `NaN` and a nested array even from a
direct write. Every term except the start date and
the offset flag may be null: **null means not recorded yet; `NONE` means not in the Work Order**, which
is a recorded answer and is never charged or deducted. No term, idle time included, may be given before
the billing basis.

### Response entry

```text
work_order_line_public_id, line_number, source_offer_line_public_id
quoted_uom, quoted_rate_amount          the handoff copy, read-only
current_period_number                   latest period started on or before today (India time), else 1; null with none
periods[]                               term_public_id, period_number, effective_from, effective_to (derived),
                                        term_revision, currency_code, every term above,
                                        derived_hours_per_working_day (MONTH), is_complete, missing_items[],
                                        updated_by, updated_by_display_name, updated_at
terms_complete, line_missing_items[]    NO_TERMS, or the union of the periods' items
```

Missing items, in this order: `BILLING_BASIS`, `CONTRACTED_HOURS`, `CONTRACTED_WORKING_DAYS`,
`NORMAL_RATE`, `WEEKLY_OFF_DAYS`, `OFF_DAY_WORK`, `OVERTIME`, `MONTH_OVERTIME_METHOD`, `BREAKDOWN`,
`IDLE_TIME`, `MINIMUM_GUARANTEE`, `PART_MONTH` - each only for the bases it applies to. A choice
that asks for a rate (holiday, breakdown deduction, standby) is missing until the rate's method is
chosen, and off-day work at the overtime rate is missing while overtime is unrecorded. Write responses
wrap one entry as `line_billing_terms` beside `event`, which is null when a
`PUT` changed nothing.

### Rules

- Refused on a `CLOSED` Work Order. Locking at mobilisation and once billed are later slices' (owner
  decision 6).
- An identical `PUT` records no event and keeps the revision.
- Nothing blocks on incompleteness; Work Order release (7B) will.
- Nothing is calculated. `crm_work_order_line.rate_amount` stays the quoted rate from the offer.

### Events

```text
WorkOrderLineBillingTermsPeriodAdded | WorkOrderLineBillingTermsPeriodUpdated | WorkOrderLineBillingTermsPeriodRemoved
record_type = work_order, record_public_id = Work Order public id
payload: work_order_line_public_id, term_public_id, period_number, effective_from, term_revision,
         billing_uom_code, changed_fields[]
```

No amount, rate or percentage appears in any payload.

### What is unchanged

The handoff route and output, `GET /api/work-orders/{public_id}/lines`, `WorkOrderResponse`,
`WorkOrderLineResponse` and `crm_work_order_line` are untouched; the terms live in
`crm_work_order_line_billing_term` (Alembic `20260908_0037`). The frozen handoff contract file is
byte-identical.

## Slice 7D Part 2 night shift, mobilisation, demobilisation and fuel

Recorded 15 September 2026, owner decisions 8-12. **Changed by Slice 7D Part 5 (10 October 2026):** the night shift became the
shift pattern - its fields and `NIGHT_SHIFT` below are Part 2's, kept as the record; see "Slice 7D Part 5" at the end of
this file. The rest of `WBT-001`'s term set, added as columns on
`crm_work_order_line_billing_term` (Alembic `20260908_0038`). No new route, permission, event or table,
and nothing in Part 1 changes: `POST` and `PUT` accept the new fields and `GET` returns them.

### Where each term lives

Night shift and fuel belong to **each period**, because a Work Order amendment can change a night rate
or a fuel average from a date. Mobilisation and demobilisation are recorded **once for the line, on
period 1** - the machine arrives once and leaves once - and a later period neither carries nor changes
them: sending one on period 2 or later is `422`, and the database refuses it too. A later period made
by copying the latest one therefore starts without them.

### Request fields

```text
night_shift_rate_method_code       NONE | RATE_PER_SHIFT | RATE_PER_HOUR | PERCENT_OF_NORMAL;
                                   SHIFT, DAY, MONTH (an hourly line has no night shift)
night_shift_rate_amount            > 0; required with RATE_PER_SHIFT or RATE_PER_HOUR
night_shift_rate_percent           > 0; required with PERCENT_OF_NORMAL
night_shift_contracted_hours       > 0; only while the night shift is charged; counted per the line's
                                   billing unit, exactly like contracted_hours_per_billing_unit
night_shift_working_days_per_month > 0; MONTH, only while the night shift is charged

mobilisation_charge_code           NONE | CHARGED | CHARGED_CREDITED_AFTER_MONTHS; period 1 only
mobilisation_charge_amount         > 0; only when charged
mobilisation_credit_after_months   whole months >= 1; only with CHARGED_CREDITED_AFTER_MONTHS
demobilisation_charge_code         NONE | CHARGED | CHARGED_WAIVED_AFTER_MONTHS; period 1 only
demobilisation_charge_amount       > 0; only when charged
demobilisation_waived_after_months whole months >= 1; only with CHARGED_WAIVED_AFTER_MONTHS

fuel_treatment_code                NONE | PBL_SUPPLIED_INCLUDED | PBL_SUPPLIED_CHARGED | CUSTOMER_SUPPLIED
fuel_charge_method_code            AGREED_RATE_PER_LITRE | ACTUAL_COST; only with PBL_SUPPLIED_CHARGED
fuel_rate_per_litre_amount         > 0; only with AGREED_RATE_PER_LITRE
fuel_litres_per_working_hour       > 0; only with CUSTOMER_SUPPLIED
fuel_travel_allowance_code         NONE | LITRES_PER_TRAVEL_HOUR; only with CUSTOMER_SUPPLIED
fuel_litres_per_travel_hour        > 0; only with LITRES_PER_TRAVEL_HOUR
```

Part 1's rules carry over unchanged: every number finite and greater than zero, no term before the
billing basis, **null means not recorded yet and `NONE` means not in the Work Order**, and the database
refuses directly-written rows that break any of it. "Credited after N months" and "waived after N
months" are codes rather than a number beside `CHARGED`, so "charged, with no credit back" is a recorded
answer and a forgotten month count is missing. Whether the months are counted from mobilisation, from
first working day, and how a part month counts, is decided by the billing slice (owner decision 9).

A chosen rate method carries its own value in the same save, exactly as Part 1's overtime, holiday,
breakdown and standby rates do: "charged per night shift" with no amount is refused rather than stored
and reported missing. What may be left for a later save is the night-shift hours, and on a monthly line
its working days. The month counts are whole months of at least one with no business maximum; the only
upper bound is the integer column's own range, so a nonsense number is refused as a `422` rather than
failing at the database.

Night-shift overtime, breakdown, idle time and off-day rules are the line's day-shift terms; only the
rate, the contracted hours and (monthly) the working days are separate (decision 10).

### Response and completeness

The period entry carries every field above. Four items join `missing_items`, after `PART_MONTH`:

```text
NIGHT_SHIFT       SHIFT, DAY or MONTH with no night-shift choice; or charged without its hours, or
                  (MONTH) without its working days
MOBILISATION      period 1 with no mobilisation choice, or charged without the amount or the months
DEMOBILISATION    period 1 with no demobilisation choice, or charged without the amount or the months
FUEL              no fuel choice; or a sub-choice or its value missing
```

`MOBILISATION` and `DEMOBILISATION` are reported against period 1 only, the period that holds them. A
period written before Part 2 holds none of the new terms, so its line reports all four as missing -
correct, because they were never recorded.

### Events

The three Part 1 events keep their names and payload shape. `changed_fields` names the new columns; **no
amount, percentage, litre figure or month count appears in any payload** - they are commercial values.

### What is unchanged

The frozen handoff (route, output, `WorkOrderResponse`, `WorkOrderLineResponse`,
`WORK_ORDER_LINE_SELECT_COLUMNS`, `crm_work_order_line`) and the frozen contract file, which is
byte-identical. Nothing is calculated: mobilisation invoices, credit notes, demobilisation billing, fuel
variance and night-shift pay are the billing slices'.

## Slice 7D Part 3 the contract period, extensions, line dates and copying terms

Recorded 17 September 2026. The dates the customer's Work Order runs between, the extensions that
move its end, each line's own dates inside that period, and copying one line's billing terms onto
others. Owner decisions 13 to 20d of 17 September 2026; full design and reasoning:
`docs/agent/slices/slice-7d-part-3-contract-period.md`. Migration `20260908_0039`.

When equipment actually arrives on site and leaves is a different thing, and comes later from
mobilisation and log sheets. Nothing here is that, and nothing here is calculated.

### The contract period

One row per Work Order, in `crm_work_order_contract_period`. The Work Order leads; a line may carry
its own dates inside that period, and a line left blank follows the Work Order (owner decision 13).

```text
GET  /api/work-orders/{public_id}/contract-period
     require_permission(WORK_ORDER_READ)
     the period with every extension inline, as a line's billing terms return their periods inline

PUT  /api/work-orders/{public_id}/contract-period
     require_permission(WORK_ORDER_CONTRACT_PERIOD_WRITE)
     whole replacement; 200, 404, 409 (version conflict), 422 (validation)

POST /api/work-orders/{public_id}/contract-extensions
     require_permission(WORK_ORDER_CONTRACT_EXTENSION_WRITE)
     one extension, moving the end date to it; 201, 404, 409, 422

DELETE /api/work-orders/{public_id}/contract-extensions/{extension_public_id}
     require_permission(WORK_ORDER_CONTRACT_EXTENSION_WRITE)
     remove the most recent extension, putting the end back; 200, 404, 409, 422
     (owner's screen check, 22 September 2026)
```

#### Request

```text
expected_period_version    null before the first save; otherwise the version last read
contract_start_date        the date the contract starts
contract_end_basis_code    FIXED_DATE | UNTIL_WORK_COMPLETE; null is not recorded yet
contract_end_date          required with FIXED_DATE, refused with UNTIL_WORK_COMPLETE
contract_notes             text, up to 4000; never read by any rule
```

`contract_end_basis_code` is how the end was answered, not a formatting choice (owner decision 14).
**Null with no date means not answered yet, and is reported missing. `UNTIL_WORK_COMPLETE` is a
recorded answer** - exactly as `NONE` is for a billing term - **and is not missing**, but it still
leaves the Work Order un-closable, which the response reports separately and the screen states in
those words. Refusing the closure itself belongs to the closure slice (8E). An end date with no
basis beside it is refused rather than given one, because which of the two answers the user meant is
what is missing. Any other field is refused with `422`.

**Once an extension exists, the end moves only through extensions** (owner, 22 September 2026). A
save that changes `contract_end_basis_code` or `contract_end_date` is then refused with `422`:
"Once an extension has been recorded, the contract end date changes only through extensions. Record
another extension, or remove the latest one." Resending the end unchanged is not a change, so a save
of the start or the notes still succeeds. With every extension removed, the end is editable again.
Before this, a save could silently replace the end the extensions had set.

#### Response

```text
work_order_public_id, period_public_id, period_version        null until the first save
contract_start_date, contract_end_basis_code, contract_end_date, contract_notes
contract_state_code    NOT_RECORDED | NOT_STARTED | ACTIVE | ENDED | BETWEEN_EXTENSIONS
contract_state_label   "Active, ends in 12 days, on 31 March 2027", "Ended on ...", "Starts ..."
days_until_start, days_until_end
needs_firm_end_date    true only while the end is "until the work is complete"
is_complete, missing_items[]    CONTRACT_START | CONTRACT_END
extensions[]           oldest first: extension_public_id, extension_sequence_no,
                       previous_end_basis_code, previous_end_date, new_end_date, extension_start_date,
                       customer_reference, received_date, extension_notes, created_by,
                       created_by_display_name, created_at
gaps[]                 oldest first: first_day, last_day, extension_sequence_no - days no contract runs
                       on, before an extension that starts later than the day after the end it follows
updated_by, updated_by_display_name, updated_at
```

The state is computed on every read against India's date and never stored. **Where the start date is
not recorded the state is `NOT_RECORDED` even if an end date is** - whether the contract has begun is
not knowable, and "Active" would be a guess. The one exception is an end date already past: that
contract is over whatever its start was.

#### Extensions

```text
new_end_date        required; the firm date the contract now ends
received_date       required; the date the customer's extension was received
customer_reference  optional, up to 255 - following the Slice 6O.2 amendment intake, which makes its
                    customer reference optional for the same reason: a customer may extend by email
                    or on a call, and requiring a number would invite an invented one
extension_notes     optional, up to 4000
extension_start_date  optional; the day the extension starts. Omitted, it is the day after the current
                    fixed end. Refused where there is no fixed end to follow
gap_confirmed_from  the first day of the gap the user agreed to leave, as the screen showed it; only
                    where the start is later than the day after
```

**An extension has its own start date** (owner's clarification, 22 September 2026). Normally it is the
day after the fixed end it follows. It must be after that end and not after the extension's own new end.
A later start leaves days no contract runs on, and is refused without `gap_confirmed_from`, naming
them; the screen asks first. The confirmation is the first day of the gap as the screen showed it, not a
yes: if the end moved since - another user recorded or removed an extension - it no longer matches and the
request is refused with `409`, so a user's agreement to one gap can never record another. `extension_start_date` is null exactly when there was no fixed end to follow, and a
CHECK constraint makes that a database guarantee.

**Days in a gap are outside the contract.** The rule module answers `IN_GAP` for them, which is one of
`CONTRACT_DATE_OUTSIDE_OUTCOMES`, and it does so whether or not the start is recorded, because a gap is
made only of recorded dates. A billing period may not start, and a line's own dates may not fall, on
one. The state reads `BETWEEN_EXTENSIONS` on such a day, never `ACTIVE`.

Each extension keeps what the contract said before it, so **previous end dates stay as history**
and what the contract said at any time is recoverable while the extension stands.

**An extension must move a fixed end date later** (owner, 22 September 2026). Where the end is
"until the work is complete" or not recorded, there is no current end to compare with, and the new
end is checked against the contract start instead. An extension against a contract with no dates
recorded at all is accepted and records no previous end.

**`received_date` may be any date except one before the contract start**, which is refused naming
both dates - including a date after the contract has ended, when a verbal commitment came first and the
order arrived later (owner, 22 September 2026). The extension still starts the day after the end. The screen warns - never refuses - when the order is dated more than 15 days before
today in India, because extensions usually arrive before the contract ends. The contract start may
not later move past an order already recorded, which is refused naming the extension - nor past
the end an extension continued from, which a late order's date would not otherwise prevent.

*Superseded:* from 17 to 22 September 2026 any end date other than the current one was accepted,
earlier or later, so that a mistyped end date could be put right by recording another extension.
Removal now does that instead.

#### Removing an extension

Only the **most recent** extension can be removed, as only the latest billing-terms period can be:
a gap in the middle of the chain would no longer explain how the current end was reached. Removing
any other is refused, naming the one that is most recent; one already removed, or not on this Work
Order, is `404`.

The end basis and date go back to the ones the extension recorded as previous - a date, "until the
work is complete", or not recorded. That restored end is checked like any other move of the end, so
a removal that would now exclude a billing period, a line's own date or the contract's own start is
refused, and the refusal begins "This extension cannot be removed." The response is the whole
contract period, as for every other write here.

The extension row is deleted; `WorkOrderContractExtensionRemoved` keeps the fact that it existed. The
history in the response therefore lists the extensions in force, and the audit log every one ever
recorded.

**No approval is asked for.** The screen says "Approval step not yet added" in those words, so a
reader learns the system does not ask for one yet rather than that none is needed. Approval rules
need `APR-001` and are recorded for Slice 8F.

### A line's own dates

Two nullable columns on `crm_work_order_line_detail` (7C's table, where a line's own facts already
live), carried on the existing `PUT .../lines/{line}/detail` and its response:

```text
line_start_date, line_end_date    both blank means the line follows the Work Order
```

Blank is never reported missing: following the Work Order is the normal case. Both are checked
against the contract, and a line's end may not precede its own start. The event payload gains both
dates; they are dates, not commercial amounts.

**These two fields alone are not whole-replacement.** Omitting a date field keeps what is recorded;
sending it as null clears it. Every other field on that route is replaced by what the request
carries. The exception is deliberate: the fields were added to a route that already had callers, and
whole replacement would have let an ordinary edit of a site or a reference erase dates nobody
touched (independent review round 1, finding F-03).

They are governed by `WORK_ORDER_LINE_DETAIL_WRITE`, the permission of the route they are saved
through, **not** by `WORK_ORDER_CONTRACT_PERIOD_WRITE`, which governs the Work Order's own contract
dates. An earlier draft of this contract claimed otherwise; a permission description has to state
what is actually enforced, or narrowing the grant will not narrow what the description promised
(round 1, finding F-04).

### What is refused

Every refusal names the dates (owner decision 17), and the line where one is involved:

```text
This period starts on 1 May 2027, after the contract ends on 31 March 2027.
The contract cannot end on 1 February 2027, because line 2 has terms starting 1 March 2027.
```

- a billing-terms period start must sit inside the contract, on adding and on changing a period;
- a line's own dates must sit inside it;
- the contract's dates may not move to exclude a period start or a line date already recorded;
- an extension's new end date is checked the same way;
- once an extension exists, a save may not change the end;
- an extension must move a fixed end later, and its order may not be dated before the contract start;
- the contract start may not move past an extension order already recorded, or past the end an
  extension continued from;
- an extension must start after the end it follows, and a later start than the day after needs
  confirmation;
- a billing period may not start, and a line's own dates may not fall, in a gap before an extension;
- removing an extension may not restore an end that would exclude any of the above.

Both bounds are inclusive. **A bound that is not recorded is never treated as broken**: the rule in
`backend/app/modules/work_orders/contract_period_rules.py` answers `NOT_DETERMINED` where a bound is
unknown, and nothing turns that into a refusal. That module is pure - no database, no clock, no I/O -
and is the rule log sheets, Work Order release and billing will reuse.

The start side of each rule is a deliberate completion of the stated one: decision 17 names only the
end case, and the start case is the same rule read the other way, reachable whenever dates are
entered before the contract is. Recorded rather than added quietly.

### Copying one line's terms onto other lines

```text
POST /api/work-orders/{public_id}/lines/{line_public_id}/billing-terms/apply-to-lines
     require_permission(WORK_ORDER_LINE_BILLING_TERMS_WRITE)
```

It writes billing terms, so it asks for the permission that already governs writing them rather than
one of its own: who may change a line's rates should be one answer, not two.

```text
targets[]         one per line being given the terms; the source is in the path, never here
  work_order_line_public_id
  observed_periods[]                  every period the screen saw of THIS line, in order
    term_public_id, term_revision     empty when the screen saw a line with no terms
  replace_confirmed                   true only where the screen named this line and the user agreed
source_periods[]  every period of the source line as the caller saw it
  term_public_id, term_revision
```

Both sides are compared **period by period**, in order, under the Work Order lock. A count plus the
latest revision is not sufficient for either, and was tried on both: neither changes when an earlier
period is edited, so on the source a version the user never reviewed could be copied, and on a target
a concurrent edit would be silently deleted by the replacement. A target whose live periods differ
from those observed is refused **by name**, which is also what prevents one line's confirmation
authorizing the replacement of another. Found by independent review across two rounds (findings F-01,
F-02 and F-07).

**Every period the source line has is copied**, mobilisation and demobilisation with them (owner
decisions 20c and 20d), column by column from rows that already passed every term rule. Receiving
lines start at revision 1 and remain editable.

A chosen line that already has terms and carries no `replace_confirmed` of its own refuses the
**whole** request, naming those lines, so nothing recorded is replaced unasked. A line simply left
out of `targets` is not touched, and leaving it out never removes its terms. The source line may not
also be a target, a line chosen twice is refused, and a line that is not on this Work Order is `404`.

```text
source_line_public_id, source_line_number
results[]        work_order_line_public_id, line_number,
                 outcome  COPIED | REPLACED | FAILED,
                 periods_copied, replaced_period_count, message
billing_terms[]  every line's terms as they now stand, so the page refreshes in one go
events[]         one per receiving line that was written
```

Each receiving line is written inside its own savepoint and records its own event, so the trail reads
as one change per line and a line that could not be written is named in the result without stopping
the others. With the Work Order locked for the whole operation nothing can change a line underneath
the call, so that path is a guard rather than a common outcome.

**A copied period is not checked against the receiving line's own dates**, only against the contract.
That is deliberate and recorded as a known gap in the slice document: enforcing it would block the
case decision 20d describes, where a line takes the terms and is then edited.

### Events

```text
WorkOrderContractPeriodRecorded | WorkOrderContractPeriodUpdated
  period_version, contract_start_date, contract_end_basis_code, contract_end_date, changed_fields[]

WorkOrderContractExtensionRecorded
  extension_public_id, extension_sequence_no, previous_end_basis_code, previous_end_date,
  new_end_date, extension_start_date, starts_after_a_gap, received_date, has_customer_reference

WorkOrderContractExtensionRemoved
  extension_public_id, extension_sequence_no, removed_new_end_date,
  restored_end_basis_code, restored_end_date

WorkOrderLineBillingTermsCopied            one per receiving line
  work_order_line_public_id, source_work_order_line_public_id, periods_copied,
  replaced_period_count, billing_uom_code
```

Dates, codes and public ids only. The customer's reference text never appears in a payload - only
whether one was given.

### Locking

A Closed Work Order refuses every write above, as it does for 7C's detail and 7D's terms. The
contract start additionally locks at mobilisation (owner decision 19): **recorded, not enforced**,
because mobilisation does not exist yet. See `docs/agent/DEFERRED_REQUIREMENTS.md`. The other half of
decision 19 - the end moving only through extensions - applies earlier, from the first extension
(owner, 22 September 2026), and is enforced now.

### What is unchanged

`POST /api/work-orders/from-commercial-offer`, `GET /api/work-orders/{public_id}/lines`,
`WorkOrderResponse`, `WorkOrderLineResponse`, `crm_work_order` and `crm_work_order_line` are all
untouched: the contract period and its extensions live in their own tables, and the line's dates on
the 7C detail row. The frozen handoff contract file is byte-identical, and a test asserts that no
Part 3 field appears in what the handoff returns.

## Slice 7D Part 4 extra kilometres, crew, and the holidays a Work Order names

Recorded 24 September 2026. The owner's answers 21 to 26 of 17-18 September 2026 and decisions 27 to 31
of 24 September; full design and reasoning: `docs/agent/slices/slice-7d-part-4-remaining-billing-terms.md`.
Migration `20260908_0040`. Nothing is calculated.

Two of the six answers add nothing here: billing frequency belongs to each machine and goes to
equipment assignment (8A) and invoicing (8G); weekly-off and holiday work are not given separate rates,
because Part 1's single off-day choice already records both.

### Extra kilometres and crew, per period

New columns on `crm_work_order_line_billing_term`, carried on the existing billing-terms routes exactly
as Part 2's were. No new route, permission or event for them.

```text
extra_km_allowance_code            NONE | KM_PER_DAY | KM_PER_MONTH; every basis
extra_km_included_km               > 0; only with KM_PER_DAY or KM_PER_MONTH
extra_km_rate_amount               > 0, INR per extra kilometre; only with KM_PER_DAY or KM_PER_MONTH
crew_code                          NONE (equipment only) | STATED; every basis
crew_operators_per_unit            whole number >= 0; only with STATED
crew_helpers_per_unit              whole number >= 0; only with STATED
extra_crew_charge_code             NONE | RATE_PER_PERSON; only with STATED
extra_crew_operator_rate_amount    > 0, INR per extra operator per billing unit; only with RATE_PER_PERSON
extra_crew_helper_rate_amount      > 0, INR per extra helper per billing unit; only with RATE_PER_PERSON
```

The crew numbers are counted **per billing unit of the line** - the line's own basis is the unit - so a
day line carrying two operators and two helpers records 2 and 2. They are the one exception to "every
number greater than zero": one of the two may be zero ("2 operators, no helpers"), not both, because a
Work Order with no crew at all is recorded as equipment only (decision 28). Neither term may be given
before the billing basis. A period records one kilometre allowance, per day or per month.

What the customer is charged for crew never sets what the crew are paid: crew hours and pay come from
PBL's HR terms (the standing rule recorded against 8B in `docs/agent/FUTURE_SLICES.md`).

Two items join `missing_items`, after `FUEL`: `EXTRA_KILOMETRES` (no choice, or an allowance without its
kilometres or rate) and `CREW` (no choice; or crew stated without both numbers, without how extra crew is
charged, or charged per person without both rates). "Not in the Work Order" and "equipment only" are
answers, so a period answering both is not missing them. A period saved before Part 4 reports both -
correct, because they were never recorded.

Copying one line's terms onto others copies these columns with the rest, column by column.

### The monthly minimum guarantee

Unchanged in rule: a monthly line still records no minimum guarantee, and sending one is `422`. The
reason given is corrected (answer 26): "A minimum guarantee does not apply to Month billing: a month short
of the contracted hours is charged pro rata, with no minimum." It used to say the monthly rate already
covered the contracted month, which contradicted how a monthly shortfall is billed. The pro-rata rule
itself is billing's (8D).

### The holidays a Work Order names

**Changed by HOL-1 (2 October 2026)**: the answer codes, the request's `holidays[]` and the response's `holidays[]`
below are Part 4's, kept as the record of what Part 4 built. Since HOL-1 the list holds the Work Order's changes to PBL's
holiday calendar - see "HOL-1" at the end of this file, which states the routes as they now are.

```text
GET  /api/work-orders/{public_id}/holidays
     require_permission(WORK_ORDER_READ)

PUT  /api/work-orders/{public_id}/holidays
     require_permission(WORK_ORDER_LINE_BILLING_TERMS_WRITE)
     whole replacement; 200, 404, 409 (version conflict), 422
```

One list on the Work Order, for every line (decision 27), in two tables of its own:
`crm_work_order_holiday_list` holds the answer, one row per Work Order; `crm_work_order_holiday` holds
the dates, each belonging to that row. Weekly off days are not in the list: they are recorded per
billing-terms period (Part 1). Work on any listed day is charged as each line's off-day choice says.

The PUT is written under the billing-terms permission rather than one of its own: which days are holidays
decides which days take a line's off-day rate, so who may change a rate decides them too. The
permission's description is reworded by the migration to say so, and to name the Part 2 terms and the
Part 3 copying it has governed since those parts.

#### Request

```text
expected_list_version   null before the first save; otherwise the version last read
holidays_answer_code    required: NONE (the Work Order names no holidays) | LISTED (names these)
holidays[]              only with LISTED
  holiday_date          a date
  holiday_kind_code     NATIONAL | FESTIVAL
  description           optional, up to 255
```

Unknown fields are refused. Codes are accepted in any case and stored in capitals.

#### Response

```text
work_order_public_id
holiday_list_public_id, list_version, holidays_answer_code    null until the first save
holidays[]              holiday_public_id, holiday_date, holiday_kind_code, description; earliest first
is_complete, missing_items[]   HOLIDAYS
updated_by, updated_by_display_name, updated_at
```

The PUT response wraps it as `holiday_list` beside `event`, which is null when the save changed nothing.

**No answer recorded is missing. LISTED with no dates entered is missing. NONE is an answer and is not
missing** (decision 29): an empty list alone could never tell "none" from "not entered".

#### What is refused

- NONE with any dates;
- an answer other than NONE or LISTED, and no answer at all;
- a kind other than NATIONAL or FESTIVAL - weekly off is not a kind here;
- a date listed twice, naming it;
- a date outside the contract, or in a gap before an extension, naming both dates, by the same rule
  (`contract_period_rules.py`) Part 3 applies to a billing period's start: "A holiday is listed on
  25 December 2026, before the contract starts on 1 January 2027." An unrecorded bound is never treated
  as broken;
- any write on a Closed Work Order: "This Work Order is closed. Its holidays can no longer be changed."

And the reverse, in the contract-period routes: **the contract dates cannot move to exclude a listed
holiday** - by an edit of the dates, or by removing an extension - naming both dates, as they already
cannot for a billing period's start or a line's own dates: "The contract cannot start on 1 February 2027,
because a holiday is listed on 26 January 2027."

The Work Order is locked for every write, so a holiday save and a contract-date change cannot pass each
other. The list is replaced as a whole; each date row is recreated on every changing save.

#### Events

```text
WorkOrderHolidaysRecorded | WorkOrderHolidaysUpdated
  list_version, holidays_answer_code, holiday_count, added_dates[], removed_dates[], changed_dates[]
```

Dates, codes and counts only. A description is the customer's own wording and never appears in a
payload. An identical save records no event and keeps the version.

### What is unchanged

The frozen handoff (route, output, `WorkOrderResponse`, `WorkOrderLineResponse`, `crm_work_order`,
`crm_work_order_line`) and the frozen contract file, which is byte-identical. The billing-terms routes'
shape is unchanged apart from the new fields; their events keep their names and payload shape.

## HOL-1 the Work Order's changes to PBL's holiday calendar, and the holidays that apply

Recorded 2 October 2026. The owner's decision of 2 October 2026 (`DEFERRED_REQUIREMENTS.md`, "PBL's default holiday
calendar") and answers to HOL-1's questions; full design: `docs/agent/slices/hol-1-holiday-calendar.md`. The calendar
itself is `holiday-calendar-api-contract.md`. Migration `20260908_0047`. Nothing is calculated.

Every Work Order inherits PBL's holiday calendar for each line's site state, and its own terms change it. Part 4's list,
on the Work Order and one for every line (decision 27), now holds those changes; each line applies them to the calendar
for its own state.

### The routes

```text
GET  /api/work-orders/{public_id}/holidays             WORK_ORDER_READ                       (shape changed)
PUT  /api/work-orders/{public_id}/holidays             WORK_ORDER_LINE_BILLING_TERMS_WRITE   (shape changed)
GET  /api/work-orders/{public_id}/holidays/resulting   WORK_ORDER_READ                       200, 404   (new)
```

The new route is pinned in `POST_BASELINE_NEW_ROUTES`. Nothing in the frozen handoff writes or returns any of it.

### The answer and the changes

```text
expected_list_version   null before the first save; otherwise the version last read
holidays_answer_code    required: CALENDAR_UNCHANGED (the Work Order follows PBL's calendar unchanged)
                                | CALENDAR_CHANGED   (the Work Order changes PBL's calendar as listed)
changes[]               only with CALENDAR_CHANGED
  change_code           required: HOLIDAY_ADDED | WORKING_DAY
  holiday_date          a date
  holiday_kind_code     NATIONAL | FESTIVAL; required with HOLIDAY_ADDED, refused with WORKING_DAY
  working_day_rate_code NORMAL_RATE | OVERTIME_RATE; required with WORKING_DAY, refused with HOLIDAY_ADDED
  description           optional, up to 255: an added holiday's description, or a working day's note
```

- **A holiday added** is a holiday on every line, charged as each line's off-day term says (answer 24).
- **A working day** is a calendar holiday the Work Order works (Q4): charged at the normal rate, or - every hour of the
  day - at the line's own overtime rate (the owner's point 2, 2 October 2026). A day that stays a holiday is charged by
  the off-day term (point 3).

The response is Part 4's with `changes[]` - `change_public_id`, `change_code`, `holiday_date`, `holiday_kind_code`,
`working_day_rate_code`, `description`, earliest first - in place of `holidays[]`. **No answer recorded is missing;
CALENDAR_CHANGED with no change entered is missing; CALENDAR_UNCHANGED is an answer and is not missing** (decision 29,
reworded).

Refused (`422`, each naming the date): an answer other than the two (Part 4's `NONE` and `LISTED` included), or none;
CALENDAR_UNCHANGED with any change; a change other than the two, or none; a kind or a rate where it does not belong, or
missing where it does; a description or note longer than 255 characters; a field left out or null - each checked by
the service, not the request schema, so the refusal names the date (HOL1-R3-001, HOL1-R4-002); a date listed twice - a date is either a holiday added or a working day; a date outside the
contract or in a gap before an extension ("A working day is listed on ..." for a working day); any write on a Closed
Work Order. A stale version is `409`. Part 4's request field `holidays` is an unknown field now, refused.

**The contract cannot move to leave a change outside it** - a holiday added or a working day - by an edit of the dates
or by removing an extension, naming what the date is: "The contract cannot end on 1 March 2027, because a working day
is listed on 22 March 2027."

A working day on a date that is not (yet) in PBL's calendar is accepted: it does nothing until the calendar has the
day, and the read below notes it.

### Events

```text
WorkOrderHolidaysRecorded | WorkOrderHolidaysUpdated          (names kept)
  list_version, holidays_answer_code, holidays_added_count, working_days_count,
  entered_dates[], taken_off_dates[], changed_dates[]         (a change of what it is, its kind, rate or description)
```

"Added" names a kind of change since HOL-1, so Part 4's `added_dates` and `removed_dates` are now `entered_dates` and
`taken_off_dates`, and `holiday_count` is the two counts. Dates, codes and counts only: no description or note.

### The holidays that apply (`GET .../holidays/resulting`)

PBL's calendar as the Work Order changes it, for each group of lines in one state, over the contract. A read: it never
writes, and the Work Order is not locked.

```text
work_order_public_id, holidays_answer_code, list_version
period_from, period_to          the contract period; both null with no contract start
period_note_code                NO_CONTRACT_START | OPEN_END (no fixed end: shown to 31 December of the latest of the
                                start's year, the last year started in the calendar and the last change's year) | null
period_message                  the same in words
calendar_days[]                 the calendar holidays inside the period for at least one line's state, by date:
  holiday_date, line_numbers[], entries[] {holiday_name, holiday_kind_code, applies_to_code, state_codes[], state_labels[]}
groups[]                        lines in one state, or whose state is not known, in line order:
  state_code, state_label       null when not known
  problem_code                  SITE_NOT_RECORDED | SITE_STATE_NOT_RECOGNISED | null
  problem_message               what to put right, naming the lines
  line_numbers[]
  days[]                        earliest first:
    holiday_date, day_code (HOLIDAY | WORKING_DAY), source_code (CALENDAR | WORK_ORDER),
    holiday_kind_code, name (the calendar's name, or an added holiday's description),
    working_day_rate_code, note,
    lines_without_overtime_rate[]   for a working day at the overtime rate: the group's lines whose billing terms record
                                    no overtime rate for the period that day falls in (none recorded, "not in the Work
                                    Order", no terms, or an hourly line)
years_not_complete[]            the years in the period whose calendar Admin has not marked complete (from 2000 to 2100)
change_notes[]                  holiday_date, change_code, note_code, message:
                                DOES_NOTHING        a working day on a date PBL's calendar has as a holiday for none of
                                                    the Work Order's sites
                                ALREADY_IN_CALENDAR a holiday added on a date the calendar has for every site
```

The rule, for a line whose site is in state S, written once in `work_orders/holiday_rules.py` (pure, for log sheets and
billing to call): every calendar holiday for all of India or for S is a holiday - unless the Work Order makes that date a
working day, then a working day at its rate - plus each date the Work Order adds, on days inside the contract (not
before its start, not after its end, not in a gap before an extension). A line with no site, or whose state the platform
does not recognise (read as 8A reads it), gets the all-India holidays only. A line's own dates do not narrow it.

### What is unchanged

The frozen handoff (route, output, `WorkOrderResponse`, `WorkOrderLineResponse`, `crm_work_order`,
`crm_work_order_line`) and the frozen contract file, which is byte-identical. The billing-terms, contract-period and
line-detail routes are unchanged; the contract-period routes' refusal names a working day as such.


## Slice 7D Part 5 the shift pattern, and the crew's food, accommodation and travel

Recorded 10 October 2026. The owner's answers of 9 October 2026; full design, and the assumptions (A1 to A15) taken
where the answers left a point open: `docs/agent/slices/slice-7d-part-5-crew-upkeep-and-shifts.md`. Migration
`20260908_0052`. New columns on `crm_work_order_line_billing_term`, carried on the existing billing-terms routes as
Parts 2 and 4 were: no new route, permission or event. Nothing is calculated.

### What changes for a caller

- **Part 2's five night-shift fields are gone** from the request and the response: `night_shift_rate_method_code`,
  `night_shift_rate_amount`, `night_shift_rate_percent`, `night_shift_contracted_hours`,
  `night_shift_working_days_per_month`. A request still sending one is refused as an unknown field (`422`). The
  migration converted every stored night shift into the shift pattern, or - for a night shift "not in the Work
  Order" - asked for the shift pattern again and kept that answer on the period (below).
- Each period's response gains `legacy_night_shift_not_in_work_order` (boolean, read only): true where Part 2 recorded
  the night shift as not in the Work Order. No request can set or change it; copying terms does not carry it.
- `missing_items` reports `SHIFTS` in `NIGHT_SHIFT`'s place, and `CREW_UPKEEP` after `CREW`.
- The resource requirement's `line.night_shift_charged` became `line.shifts_per_day` - 1, 2 or 3 as stated, null for
  `NONE` or not recorded (`resource-requirement-api-contract.md`).

### The shift pattern, per period (shift, day and month lines)

```text
shift_pattern_code              NONE (not in the Work Order: no shifts stated) | ONE_SHIFT | TWO_SHIFTS | THREE_SHIFTS
shift_1_hours                   > 0, the first shift's hours in a day; only with ONE_SHIFT, TWO_SHIFTS or THREE_SHIFTS
shift_2_hours                   > 0; only with TWO_SHIFTS or THREE_SHIFTS
shift_3_hours                   > 0; only with THREE_SHIFTS
                                the shifts of one day add up to no more than 24
shift_rate_code                 SAME_FOR_ALL_SHIFTS (the Work Order states the same rate for every shift) | PER_SHIFT
                                (a rate set for each later shift; shift 1 at the Work Order rate). How billing counts
                                either is the slice document's A9, which bears on money and waits for the owner.
                                Only with TWO_SHIFTS or THREE_SHIFTS
shift_2_rate_method_code        RATE_PER_SHIFT | RATE_PER_HOUR | PERCENT_OF_NORMAL; only with PER_SHIFT
shift_2_rate_amount / _percent  exactly the value the method asks for, in the same save; a percentage is of
                                normal_rate_amount, the Work Order rate the first (day) shift is charged at - Part 2's
                                night-shift percentage, unchanged
shift_2_working_days_per_month  > 0; MONTH, only with PER_SHIFT
shift_3_rate_*, shift_3_working_days_per_month   as shift 2's, and only with THREE_SHIFTS
overtime_counted_per_code       PER_SHIFT | PER_DAY; only while overtime is charged on TWO_SHIFTS or THREE_SHIFTS
                                (on a monthly line whichever way overtime is counted over the month)
```

Null on an hourly line and before the billing basis. The contracted hours keep their meaning - the hours the Work
Order rate buys per billing unit - and are not checked against the shift hours. Overtime, breakdown, idle time and off
days are the line's terms for every shift (Part 2, decision 10).

### The crew's food, accommodation and travel, per period (every basis)

```text
upkeep_<item>_<role>_code           NONE | PROVIDED (by the customer) | PROVIDED_AT_COST
upkeep_<item>_<role>_amount         > 0, INR; only with PROVIDED_AT_COST
upkeep_<item>_<role>_unit_code      the cost's basis; only with PROVIDED_AT_COST:
                                      food, accommodation   PER_PERSON_PER_DAY | PER_PERSON_PER_MONTH
                                      job_travel            PER_PERSON_PER_TRIP | PER_TRIP (whatever the number of people)
                                      daily_travel          PER_PERSON_PER_DAY | PER_DAY (whatever the number of people)
upkeep_<item>_<role>_recovery_code  DEDUCTED_FROM_INVOICE | BILLED_SEPARATELY; only with PROVIDED_AT_COST

<item>   food | accommodation | job_travel (to and from the job, at its start and end) | daily_travel (to site)
<role>   operator | helper
```

Only while `crew_code` is `STATED`, and nothing for a role whose crew number is 0. Nothing is ever paid to the worker:
these are what the customer provides, or recovers from PBL - deducted from PBL's invoice or billed separately. A cost
left without its amount, basis or recovery is reported missing, not refused.

### Completeness

```text
SHIFTS        SHIFT, DAY or MONTH with no shift choice; or stated shifts without each shift's hours; or two or three
              without the rate choice; or PER_SHIFT without each later shift's rate method or (MONTH) its working days
OVERTIME      also: overtime charged on two or three shifts with no per-shift-or-per-day answer
CREW_UPKEEP   the crew is stated and an item for operators (unless 0) or helpers (unless 0) is unanswered, or a
              cost lacks its amount, its basis or its recovery
```

A period saved before Part 5 whose crew is stated reports `CREW_UPKEEP` - correct, it was never recorded.

### What is refused

Each rule above, by the service with a message and by a CHECK on the table (`ck_wol_term_shift_codes`,
`_shift_positive_values`, `_shift_hours_in_a_day`, `_shift_values`, `_shift_rates`, `_shift_not_hourly`,
`_overtime_counted_per`, `_upkeep_codes`, `_upkeep_positive_values`, `_upkeep_cost_values`, `_upkeep_needs_crew`,
`_upkeep_role_present`), each written to be TRUE or FALSE when a column it compares is empty, every number finite.

### Events

The three Part 1 events keep their names and payload. `changed_fields` names the new columns; no hours, amount,
percentage or day count appears in any payload.

### The migration

`20260908_0052` (after `20260908_0051`) converts Part 2's night shift: not recorded stays not recorded; `NONE` (night
shift not in the Work Order) is left **not recorded**, so the period asks for its shift pattern again - that answer cannot
be read from a night shift's - while `legacy_night_shift_not_in_work_order` keeps the old answer, and the upgrade logs how
many periods it re-asks; a charged night
shift becomes two shifts each at its own rate - shift 2's rate and working days carried, its hours from the night hours
per billing unit (on a monthly line divided by the night working days), and shift 1's hours from the contracted hours
the same way, filled in only where the division is exact. It refuses to run, naming each period, where a monthly night
shift's hours have no working days, do not divide into an exact hour figure, or would make two shifts longer than 24
hours. Downgrade converts back what Part 2 can hold and loses the rest, as its docstring says.

### What is unchanged

The frozen handoff (route, output, `WorkOrderResponse`, `WorkOrderLineResponse`, `WORK_ORDER_LINE_SELECT_COLUMNS`,
`crm_work_order`, `crm_work_order_line`) and the frozen contract file, which is byte-identical. Copying one line's terms
onto others copies the new columns with the rest, column by column.
