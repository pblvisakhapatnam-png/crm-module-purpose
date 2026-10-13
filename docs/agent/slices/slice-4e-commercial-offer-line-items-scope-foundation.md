# Slice 4E - Commercial Offer Line Items / Scope Foundation

## Purpose

Create the minimum Commercial Offer line foundation needed for future agents to build quote terms, line-level T&C, accepted-offer conversion and Work Order handoff safely.

This slice is intentionally thin. It preserves domain shape and stable line identity; it does not build the full quote calculation engine.

## In scope

```text
- Add Commercial Offer line table.
- Link lines to one Commercial Offer.
- Give every line a stable public_id.
- Capture line number, scope/service description, equipment/service category, quantity, UOM, rate amount, simple line amount and remarks.
- List, add and update Commercial Offer lines through API.
- Display lines on the Commercial Offer profile.
- Record CommercialOfferLineAdded and CommercialOfferLineUpdated business events.
- Document future T&C and Work Order attachment points.
```

## Out of scope

```text
- No T&C master.
- No offer-level or line-level T&C customization.
- No T&C approval/deviation workflow.
- No GST/tax calculation.
- No rate master.
- No quote document generation.
- No submission/revision engine.
- No Commercial Offer credit/exposure gate against already-approved credit amount and credit days.
- No Work Order generation.
```

## Future-agent rule

Future agents must not collapse Commercial Offer lines into free-text header notes. Offer lines must remain addressable records because later features need line-level T&C, submission versioning, partial award and Work Order line handoff.


