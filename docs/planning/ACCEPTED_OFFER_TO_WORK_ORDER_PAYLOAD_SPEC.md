# Accepted Offer To Work Order Payload Spec

## Purpose

This document defines the frozen logical payload for the Accepted Commercial Offer to Work Order shell handoff.

It is a planning/specification document only. It does not implement new fields, routes, models or migrations.

## Payload Shape

Logical handoff shape:

```text
header
lines[]
documents[]
events/audit references
```

The production implementation may represent this as an API request, service command, event payload or internal DTO. The business fields and identity links must remain stable.

## Header Payload

| Field | Required for handoff | Source / note |
| --- | --- | --- |
| `commercial_offer_public_id` | Yes | Stable Commercial Offer public ID |
| `commercial_offer_number` | Yes | Current prototype uses `offer_code`; production may rename display label only |
| `commercial_offer_version` | Required when versioning exists | Use a frozen accepted version/reference for MVP if full revisioning is deferred |
| `opportunity_public_id` | Yes | Source Opportunity linked to the Commercial Offer |
| `account_public_id` | Yes | UI term is Account; derived from Account / business_party traceability |
| `account_display_name` | Yes | Name shown to business users |
| `pan` | Where available | PAN at Account level; may be placeholder if not captured yet |
| `offer_mode` | Yes | Plum-generated, customer-format, external quote, tender bid or equivalent |
| `acceptance_or_award_reference` | Yes for production MVP | Customer acceptance, tender award or internal acceptance reference |
| `accepted_date` | Yes | Date accepted/awarded |
| `submitted_document_references` | Where available | Metadata/link references, not app-server document storage |
| `accepted_document_references` | Where available | Customer PO/WO/award metadata or safe document link |
| `credit_decision_reference` | Where applicable | Latest available Commercial Offer credit/exposure decision or approval reference |
| `correlation_id` | Yes for production MVP | Trace ID across CRM, Hiring and audit logs |
| `source_status_code` | Yes | Commercial Offer status at handoff |
| `source_event_references` | Yes for production MVP | Event IDs/names for acceptance and handoff actions |

Current prototype coverage:

```text
- commercial_offer_public_id
- commercial_offer_number / offer_code
- opportunity_public_id
- account_public_id
- source_status_code
- customer_wo_reference
- received_date
- remarks
```

The missing target fields remain production implementation work. The freeze protects the intended shape so teams do not invent incompatible fields.

The credit/exposure reference carried in the handoff is the latest available Commercial Offer decision or approval reference where applicable. It does not replace the future Work Order release credit/readiness gate.

## Line Payload

| Field | Required for handoff | Source / note |
| --- | --- | --- |
| `commercial_offer_line_public_id` | Yes | Must be copied to Work Order line as source identity |
| `line_sequence` | Yes | Stable line number/sequence |
| `line_status` | Yes | Active/awarded/selected/cancelled treatment must be explicit |
| `equipment_category` | Where available | Current prototype has `equipment_service_category` |
| `equipment_model` | Where available | Production detail; optional in current foundation |
| `equipment_capacity` | Where available | Production detail; optional in current foundation |
| `scope_description` | Yes | Human-readable line scope |
| `quantity` | Where applicable | Current prototype captures quantity |
| `billing_uom` | Yes | Current prototype has `uom`; production should treat this as billing UOM when appropriate |
| `quoted_rate_amount` | Where available | Current prototype has `rate_amount` |
| `approved_rate_amount` | Where applicable | Production approval field; optional in current foundation |
| `currency_code` | Where available | Current prototype captures currency |
| `line_amount` | Where available | Simple foundation amount, not final billing engine |
| `expected_duration` | Where available | Production/MVP field; may be placeholder |
| `site_or_location_details` | Where available | Required before execution/billing if site-specific |
| `gstn` | Where available | May be header or line level depending business rule |
| `billing_party_details` | Where available | Customer/billing party identity for invoicing support |
| `mobilisation_demobilisation_notes` | Where available | Production/MVP field; may be placeholder |
| `document_references` | Where available | Metadata/link references only |
| `tc_references` | Where available | Future T&C header/line references |
| `pricing_evidence_reference` | Where available | Selected pricing evidence or basis-rate reference |
| `remarks` | Optional | Non-control notes |

Current prototype coverage:

```text
- commercial_offer_line_public_id
- line_sequence / line_number
- line_status
- scope_description
- equipment_service_category
- quantity
- uom
- rate_amount
- currency_code
- line_amount
- remarks
```

## Partial Award And Multiple Work Orders

One accepted Commercial Offer may create one or more Work Order shells.

This supports:

```text
- partial award;
- selected-line handoff;
- separate Work Order shells for different accepted lines where operations need them.
```

Rules:

```text
- Each Work Order line must retain the source Commercial Offer line public ID.
- A Work Order shell may contain all active/accepted lines or only selected/awarded lines.
- If production later allows splitting one Commercial Offer line across multiple Work Order lines, every split line must still store the same source Commercial Offer line public ID plus any additional split reference added by that later slice.
```

**Amendment, 8 October 2026 (CS-04 part 1, HOF-2; the project owner for PBL).** Recorded in full at the end of
`docs/agent/contracts/accepted-offer-to-work-order-handoff-contract.md`. In short: a Base Offer or a Supplementary
Offer is handed off, never a Change Quotation (cited on a Work Order amendment); the offer's latest customer response
must be the acceptance or award; an offer line's quantity goes onto Work Orders once, whole or in parts - the Work
Order lines of one offer line hold no more than its quantity, each keeping its source line public ID (splitting by
quantity is now in force, with no separate split reference: the Work Order line is its own reference); and an offer
with a Work Order is not recorded lost.

**Amendment, 12 October 2026 (CS-04 part 2, items c and d; the project owner for PBL).** Recorded in full at the end of
the same contract. In short: the Work Order output and both handoff events carry `commercial_offer_version_number`,
and a Work Order from a later version is titled with it ("Work Order from CO-000123 v2");
`CommercialOfferConvertedToWorkOrder` lists each Work Order line made - its source offer line, its own public ID,
quantity, unit, currency and amount. A request key that replays a repeat, and a correlation id, are agreed for later.

## Work Order Shell Output

The handoff must create or expose:

| Field | Required | Note |
| --- | --- | --- |
| `work_order_public_id` | Yes | Stable Work Order identity |
| `work_order_number` | Yes | Current prototype uses `work_order_code` |
| `linked_commercial_offer_public_id` | Yes | Source Commercial Offer |
| `linked_commercial_offer_version` | Required when versioning exists | Must refer to accepted/awarded version |
| `linked_opportunity_public_id` | Yes | Source Opportunity |
| `linked_account_public_id` | Yes | Account traceability |
| `work_order_status` | Yes | Must mean unreleased/non-posted |
| `work_order_lines[]` | Yes | Each line links to source Commercial Offer line |
| `business_event_reference` | Yes | `WorkOrderCreated`, `WorkOrderShellCreated` or equivalent |

Initial status rule:

```text
The current prototype uses HANDOFF_CREATED.
For production MVP, HANDOFF_RECEIVED is recommended as the initial Work Order shell status.
PENDING_CUSTOMER_MASTER may be a later readiness/checkpoint state or release-block reason, not necessarily the initial shell status.
No initial shell status should allow release, posting, execution, log sheets, billing or invoicing by itself.
```

## Document Metadata Rule

Business documents are not intended to be stored on the application server in production.

The handoff should carry document metadata and approved repository links only:

```text
- document public ID or external repository ID;
- document type;
- version;
- status;
- lock/access metadata;
- linked business record;
- safe URL or repository path where approved.
```

For demos, use safe sample metadata or non-confidential sample links only.

## Authorization And Audit

The handoff is a backend-authorized business action.

Rules:

```text
- Frontend role-awareness may hide or disable the action, but is not security.
- Unauthorized backend calls must be rejected.
- Handoff creation must produce a business event.
- Event/audit viewing follows existing Events module permissions unless a later contract changes it.
- No payload may contain passwords, tokens or secrets.
```

## Change Control

After this freeze, a payload change requires:

```text
- field changed;
- reason;
- owner;
- impacted CRM fields;
- impacted Hiring fields;
- migration/API impact;
- UAT impact;
- approval decision.
```
