# Slice 6A - Linked Record Navigation and Traceability Stabilization

## Purpose

Stabilize navigation and traceability between Commercial Offers and generated Work Order shells before deeper commercial, approval or execution features are added.

## In scope

```text
- Add a Work Order list filter by commercial_offer_public_id.
- Show linked Work Order shell(s) on the originating Commercial Offer profile.
- Allow users to open generated Work Order shells from the Commercial Offer profile.
- Carry safe origin-aware return links between Commercial Offer, Work Order, Opportunity and Account detail pages where practical.
- Preserve existing backend permission enforcement.
- Add backend API test coverage for filtered Work Order listing.
```

## Out of scope

```text
- No WO release/posting.
- No Customer Master activation.
- No equipment assignment.
- No crew assignment.
- No log sheets.
- No billing.
- No full approval workflow.
- No database schema change.
```

## Backend contract

Slice 6A extends the existing Work Order list route:

```text
GET /api/work-orders?commercial_offer_public_id={commercial_offer_public_id}
```

The route returns the existing `WorkOrderResponse` shape and uses the existing Work Order read roles. Invalid UUID query values are rejected by FastAPI validation.

## Frontend behaviour

The Commercial Offer profile loads linked Work Order shells through the filtered Work Order list route and displays them in a dedicated linked-record section.

Linked-record navigation uses safe relative `returnTo` and `returnLabel` query parameters. External URLs, protocol-style values and protocol-relative URLs are ignored by destination pages.

**Reconciliation, 7 October 2026 (TB-1 TB1-805).** The sentence above was not fully true until this date. Each page
carried its own copy of the check - eight in all - and the copies tested the text's prefix: it starts with "/", not
"//", and has no "://". A browser reads a backslash in a web address as "/" and drops a tab or a line break, so
`/\evil.example/x` and `/<tab>/evil.example/x` passed and the page's Back link, labelled as the link chose, led to another
site. The eight copies are replaced by one guard, `frontend/src/components/returnTarget.ts`, which refuses a backslash
or control character and any value starting "//" (even one naming this site), and keeps a value only when it starts
with "/" and, resolved as a link on the current page, stays on the same site;
when it refuses `returnTo`, the link's `returnLabel` is ignored too. The rule itself is unchanged. See
`docs/continuity/TB1_503_805_LOGS_AND_RETURN_LINKS.md`.

## Notes

This slice creates no new `business_event` because it adds read/navigation support only. Work Order creation continues to record the Slice 5A `WorkOrderCreated` and `CommercialOfferConvertedToWorkOrder` events.
