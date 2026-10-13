# Accepted Offer To Work Order Handoff Contract

## Purpose

This contract freezes the Accepted Commercial Offer to Work Order shell handoff so CRM and Equipment Hiring production MVP work can proceed in parallel.

It is a contract-definition document only. Slice 6D.1 does not implement new routes, schemas, models, migrations, tests, permissions or runtime behavior.

## Scope

The handoff scope is:

```text
Accepted Commercial Offer -> Work Order shell
```

The Work Order shell preserves traceability. It does not release, post, execute, assign, bill or invoice.

One accepted Commercial Offer may create one or more Work Order shells. This supports partial award and selected-line handoff while preserving source line identity.

## Terminology

Use in UI and vendor-facing documents:

```text
Account
```

Use only in internal/domain/database implementation notes where the existing code does:

```text
business_party
```

Customer Master is a later Finance-controlled activation. Account / Qualified Prospect creation is not Customer Master activation.

## Trigger Contract

The handoff can occur only when:

```text
- the Commercial Offer is accepted or awarded;
- the Commercial Offer has an Opportunity link;
- the Commercial Offer resolves to an Account through the linked Opportunity / Account chain;
- selected Commercial Offer lines are valid and stable, or all active lines are selected by default;
- required header and line details exist or are explicitly treated as placeholders;
- backend authorization allows the action.
```

The current prototype trigger is `ACCEPTED` Commercial Offer status and the route:

```text
POST /api/work-orders/from-commercial-offer
```

Frontend callers must use relative `/api/...` URLs.

## Header Payload Contract

The frozen logical header payload is:

| Field | Contract rule |
| --- | --- |
| Commercial Offer public ID | Required and stable |
| Commercial Offer number/code | Required display/reference value |
| Commercial Offer version/reference | Required when versioning exists; MVP may use accepted-offer reference until full versioning |
| Opportunity public ID | Required and stable |
| Account public ID | Required and stable |
| Account display name | Required for business readability |
| PAN | Include where available |
| Offer mode | Required |
| Acceptance/award reference | Required for production MVP |
| Accepted date | Required for production MVP |
| Submitted document metadata/references | Include where available |
| Accepted document metadata/references | Include where available |
| Credit decision/approval reference | Include latest available Commercial Offer credit/exposure decision or approval reference where applicable |
| Correlation ID | Required for production MVP traceability |
| Source status/event references | Required for production MVP audit |

Current prototype has a thinner implemented payload. Future production work may add the missing fields, but must not remove the required identity and traceability fields.

The credit/exposure reference carried at handoff does not replace the future Work Order release credit/readiness gate.

## Line Payload Contract

Each handoff line must preserve:

| Field | Contract rule |
| --- | --- |
| Commercial Offer line public ID | Required; copied to Work Order line source identity |
| Stable line sequence | Required |
| Line status | Required |
| Scope description | Required |
| Equipment category/model/capacity | Include where available |
| Billing UOM | Required before release/billing; current prototype uses `uom` |
| Quoted/approved rate fields | Include where available |
| Expected duration | Include where available |
| Site/location details | Include where available; required before execution where applicable |
| GSTN/billing party details | Include where available; required before invoice support where applicable |
| Mobilisation/demobilisation notes | Include where available |
| Document/T&C references | Include where available |
| Pricing evidence reference | Include where available |
| Remarks | Optional |

The Commercial Offer line public ID must remain the source of truth for downstream Work Order lines, equipment assignment, log sheets and billing traceability.

Partial-award rule:

```text
- One accepted Commercial Offer may create one or more Work Order shells.
- A Work Order shell may use all active/accepted lines or only selected/awarded lines.
- Every Work Order line must retain the source Commercial Offer line public ID.
- If a later production slice supports splitting one source line across multiple Work Order lines, each split line must still retain the source Commercial Offer line public ID.
```

## Work Order Shell Output Contract

The handoff output must include:

```text
- Work Order public ID.
- Work Order number/code.
- linked Commercial Offer ID and version/reference.
- linked Opportunity public ID.
- linked Account public ID.
- Work Order lines linked to source Commercial Offer lines.
- initial unreleased status.
- handoff business event reference.
```

Recommended initial status for production MVP:

```text
HANDOFF_RECEIVED
```

Current prototype mapping:

```text
HANDOFF_CREATED
```

For production MVP, `HANDOFF_RECEIVED` is the recommended initial Work Order shell status.

`PENDING_CUSTOMER_MASTER` may be a later readiness/checkpoint state or release-block reason, not necessarily the initial shell status.

The status name may differ between prototype and production, but the meaning must remain a shell that is not released, posted, executable or billable.

Expected event behavior:

```text
WorkOrderShellCreated or equivalent Work Order creation event
CommercialOfferConvertedToWorkOrder or equivalent source Commercial Offer event
```

The current prototype records:

```text
WorkOrderCreated
CommercialOfferConvertedToWorkOrder
```

## Controls

Required controls:

```text
- no silent relinking of Account, Opportunity, Commercial Offer or Work Order;
- no breaking or regenerating Commercial Offer line identity;
- no Work Order shell handoff without Account traceability;
- backend authorization remains authoritative;
- frontend role-awareness is only UX;
- meaningful handoff action creates a business_event;
- event/audit access follows existing Events module permissions unless a later contract changes it;
- no passwords, tokens or secrets in payloads or event metadata;
- business documents are represented by metadata/links, not app-server local storage.
```

## Deferred Production Controls

This contract does not implement:

```text
- Customer Master activation;
- Finance approval for Customer Master;
- Work Order release/posting;
- equipment assignment;
- crew assignment;
- log sheets;
- billing;
- invoicing;
- full approval workflow;
- full credit exposure calculation engine;
- full Commercial Offer revision/versioning;
- full T&C automation;
- SharePoint integration automation.
```

## Change Control

After Slice 6D.1, future agents must treat this contract as frozen for parallel work.

Any change must update:

```text
docs/agent/contracts/accepted-offer-to-work-order-handoff-contract.md
docs/planning/ACCEPTED_OFFER_TO_WORK_ORDER_PAYLOAD_SPEC.md
docs/planning/CRM_HIRING_PARALLEL_AGENT_CONTRACT.md
docs/continuity/NEXT_STEPS.md
```

The change record must include:

```text
- changed field or control;
- reason;
- affected CRM and Hiring workstreams;
- API/schema/migration impact;
- event/audit impact;
- UAT impact;
- approval owner.
```

## Amendment, 8 October 2026 - CS-04 part 1 (HOF-2)

Approved by the project owner on 8 October 2026, after asking PBL. This closes the business half of TB-1 finding
TB1-103 with TB1-300 (group G-103) and TB1-301 part (c), as corrective package CS-04 part 1. Everything above this
section is the contract as Slice 6D.1 froze it, kept as written; where the two differ, this amendment applies. The
record of the decisions and checks is `docs/continuity/TB1_103_WORK_ORDER_HANDOFF_ONCE_PER_LINE.md`.

SHA-256 of this file before the amendment: `70debad711eea67f5e8f0ff3a945c7431235ddfd97b34330beb390215cb0b86a`. Its
hash after the amendment is recorded in `docs/continuity/NEXT_STEPS.md` (a file cannot hold its own hash).

### Changed controls

1. **Which offers are handed off.** The handoff takes an accepted **Base Offer** or an accepted **Supplementary
   Offer**. A **Change Quotation** never creates a Work Order: it changes work already on a Work Order and is cited on
   a Work Order amendment (Slice 6O.2). A Supplementary Offer may either create its own Work Order or be cited on an
   amendment of the existing one; the business chooses case by case.
2. **"Accepted or awarded" means the latest answer.** The offer's latest customer response must be the acceptance or
   award (`ACCEPTED_AWARDED`), latest by the date the customer responded, then by entry - the offer's own lifecycle
   view counts it the same way. An Accepted offer whose latest response is on hold, pending, a clarification or
   revision request, or other is not handed off until an acceptance is recorded again.
3. **The partial-award rule, refined.** One accepted offer may still create one or more Work Orders, and one offer line
   may now be split across Work Orders by its quantity, in whatever unit the line records it (quantity 4 as 3 on one
   Work Order and 1 on another). The Work Order lines made from one offer line together hold no more than that line's
   quantity: each takes all or part of what is left, and every one keeps the source offer line public ID (the rule
   above for "a later production slice", now in force). A part's amount is the line's amount up to the end of the part
   less its amount up to the part's start - each the rate times the quantity so far, rounded to the paisa - so the
   parts of a line add up to its amount exactly and none is below zero; a line taken whole keeps the offer's own line
   amount. A request for a line with nothing left, or for more than is
   left, is refused, naming the Work Orders that hold it. With no line chosen, a Work Order takes what is left of every
   active line.
4. **No "lost" after a handoff.** While an offer has a Work Order, its customer response cannot be recorded as
   rejected or lost (`REJECTED_LOST`): there is no way to cancel a Work Order yet. Other responses are still recorded.
5. **One customer order, one Work Order.** Every Work Order carries the customer's Work Order reference - their
   order number, or the Letter of Intent's - and one offer never has two Work Orders with the same reference,
   compared without case or surrounding whitespace. A request repeated - a Create pressed again, a second tab, two people
   at once - carries the same reference and is refused, naming the Work Order that has it; a second order of the
   same size carries its own number. The same reference may be on Work Orders of different offers: one customer
   order may cover a Base Offer and its Supplementary Offer. (The owner, 8 October 2026, after review round 3.)

Unchanged: the header and line payload fields, the output, the initial status, the two events, the controls and the
deferred production controls above. A request key - which would answer a repeated request with the Work Order it
made rather than item 5's refusal - the correlation id, the line ids and amounts in
`CommercialOfferConvertedToWorkOrder`, and the other differences TB1-103 lists (its part a) are CS-04 part 2, with
CS-06.

### Change record

The change record the "Change Control" section above asks for:

- **Changed field or control:** the trigger (offer purpose; the latest customer response), the partial-award rule (an
  offer line's quantity onto Work Orders once, whole or in parts), the customer response after a handoff, and the
  customer's Work Order reference - items 1 to 5 above.
- **Reason:** the handoff checked only that the offer was Accepted. The same accepted lines could be handed off twice
  - a Create pressed again after a timeout, a second tab, two people at once (TB-1 demonstrated two requests at once
  giving WO-001852 and WO-001853) - and an accepted Change Quotation, or an Accepted offer whose latest response was on
  hold, was handed off too. Credit exposure (CEX-001's selected-line allocation, transferred once), log sheets and
  billing will read Work Order lines, so a line handed off twice would be counted and billed twice.
- **Affected CRM and Hiring workstreams:** CRM - Commercial Offer customer responses, the offer's lifecycle view and
  offer page; Hiring - the Work Order handoff and the Create Work Order page. Nothing written after the handoff (7C, 7D,
  WRR-001, 8A, HOL-1) changes.
- **API, schema and migration impact:** `POST /api/work-orders/from-commercial-offer` takes an optional
  `selected_offer_line_quantities` (`[{"offer_line_public_id", "quantity"}]`), requires `customer_wo_reference`, and
  refuses with `409` what is already on Work Orders or a reference already on one of the offer's Work Orders, with
  `422` a missing reference, a Change Quotation or a latest response that is not the acceptance; its response is
  unchanged. `POST /api/commercial-offers/{public_id}/customer-responses` refuses `REJECTED_LOST` with `422` while the
  offer has a Work Order. `GET /api/commercial-offers/{public_id}/lifecycle-guidance` adds `line_handoff`: each active
  line's quantity, what Work Orders hold of it and what is left, counted in one statement, which the Create Work Order
  page offers from. Migration `20260908_0049` adds database rules - the Work Order lines of one offer line hold at
  most its quantity (each locks the offer line, so two at once cannot together pass it); an offer line's own quantity
  cannot go below what they hold; a Work Order line comes from its own Work Order's offer; no Work Order from a
  Change Quotation, and an offer with a Work Order cannot become one; a Work Order written carries a customer
  reference, unique on its offer - and stops, changing nothing, on a database where a line is already past its
  quantity or on a Work Order of another offer, or a reference is on two Work Orders of one offer, having first locked the Work Order
  and line tables against writes so nothing slips in between its look and its rules.
- **Event and audit impact:** none. The same two events are written; a refused request writes nothing.
- **UAT impact:** testers enter the customer's Work Order or Letter of Intent reference on every Work Order, and see
  the refusals above beside the Create button and the customer-response form. The owner's containment instruction
  (one Work Order per accepted offer, never a repeated request) is lifted: a repeated request is refused.
- **Approval owner:** the project owner, for PBL, 8 October 2026.

## Amendment, 12 October 2026 - CS-04 part 2, items c and d

Approved by the project owner on 12 October 2026, preparing the vendor-evaluation baseline. Everything above this
section, the 8 October amendment included, still applies; where they differ, this amendment applies. Like the first,
it adds and changes nothing else.

SHA-256 of this file before this amendment: `0f16ff221e897f6199c352204a0ecced6f9a67f0c6695ad97c08c9dc2cd39080`. Its
hash after is recorded in `docs/continuity/NEXT_STEPS.md`.

### In force

1. **The offer's version in the output (item d).** Since Slice 9F a Commercial Offer's versions share one offer code,
   so the code no longer says which version a Work Order came from - the "Offer version/reference" this contract
   requires "when versioning exists". The Work Order the handoff returns, and the Work Order read routes, carry
   `commercial_offer_version_number`: the `version_number` of the offer row handed off, `1` for an offer never
   versioned. For a later version the Work Order's title names it: "Work Order from CO-000123 v2" (version 1 keeps "Work
   Order from CO-000123", as a quotation's reference does). The handoff takes the version that was accepted, which is
   the latest live one (Slice 9F): a version replaced by a later version that was sent is `REVISED` and is refused as
   any non-accepted offer is, while a later version abandoned before it was sent replaces nothing - the version before
   it stays live, may be accepted and is handed off under its own number.
2. **Both events name the version.** `WorkOrderCreated` and `CommercialOfferConvertedToWorkOrder` carry
   `commercial_offer_version_number`.
3. **What was handed off, line by line (item c).** `CommercialOfferConvertedToWorkOrder` carries `lines`: one entry per
   Work Order line made, in the order of the response's `lines`:

   ```text
   offer_line_public_id       the source offer line (line_public_id)
   work_order_line_public_id  the Work Order line made from it
   line_number                the Work Order line's number
   quantity                   decimal as text, e.g. "6.00" - this part's quantity, not the offer line's
   uom
   currency_code              the offer line's currency
   line_amount                decimal as text - this part's amount (rule 3 of the 8 October amendment). A line taken
                              whole keeps the offer line's own amount, null when that line has none; a part of a
                              line with no rate is null
   ```

   It is the record of what moved from the offer onto Work Orders: credit exposure's Potential-to-Firm transfer
   (`CEX-001`, "transferred once") and later readers count from it rather than from the Work Order's current lines.

The request, the controls, the statuses, the response's other fields and the line payload are unchanged. Nothing is
removed or renamed.

### Agreed, not yet in force

The owner approved on 12 October 2026 how the handoff will behave once these are built, as part of the shared request
rules of `MCF-001` (the PF-1B retrofit). Until then the handoff behaves as above. When either is built, a further dated
amendment records it as in force.

- **(a) A request key.** The handoff request may carry a request key. The very same request repeated with the same key
  is answered with the Work Order it made, `replayed: true`, and records no event; the same key with any other request
  is refused with `409`; a request without a key behaves as now - a repeat is refused by its customer reference (item
  5 of the 8 October amendment). Requests are compared as `CODING_STANDARDS.md` section 2 sets out
  (`request_fingerprint`, `is_same_request`).
- **(b) A correlation id.** One id for each handoff request, carried as `correlation_id` on both events.

### Change record

- **Changed field or control:** the Work Order output gains `commercial_offer_version_number` and, for a later version,
  names it in its title; both handoff events carry the version; `CommercialOfferConvertedToWorkOrder` carries `lines`.
  Items (a) and (b) are agreed behaviour, not yet changed.
- **Reason:** CS-04 part 2 (TB-1 TB1-103 part a). Since Slice 9F a Work Order from v2 read exactly like one from v1, and
  the handoff event said only how many lines moved, not which, how much or of what value - what credit exposure,
  log sheets and billing will need. Settled before the vendor-evaluation baseline is cut, so that every vendor prices
  the same boundary.
- **Affected CRM and Hiring workstreams:** CRM - credit exposure (a future reader of the event). Hiring - the Work
  Order pages show the offer as "CO-000123 v2"; nothing written after the handoff changes.
- **API, schema and migration impact:** additive. `POST /api/work-orders/from-commercial-offer`, `GET
  /api/work-orders` and `GET /api/work-orders/{public_id}` return `commercial_offer_version_number`; the two event
  payloads gain the fields above. No migration, no new route, no permission change.
- **Event and audit impact:** the two events carry more; no event is added or removed.
- **UAT impact:** the Work Order pages and the Create Work Order page show the offer's version beside its code; a Work
  Order from a later version is titled with it.
- **Approval owner:** the project owner, for PBL, 12 October 2026.
