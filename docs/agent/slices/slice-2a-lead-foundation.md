# Slice 2A - Lead Foundation

## Objective

Create the first Lead foundation after Account foundation stabilization. This slice establishes the Lead table, create/list/get API, minimal list UI, minimal create UI, role guardrails and LeadCreated event.

## Scope included

```text
crm_lead table
Lead workflow status seed rows
POST /api/leads
GET  /api/leads
GET  /api/leads/{public_id}
Minimal /leads list page
Minimal /leads/new create page
Sidebar and dashboard Lead shortcuts
LeadCreated business event
Backend tests
Lead contract document
```

## Scope excluded

```text
Lead qualification workflow
Conversion to Account / Qualified Prospect
Opportunity creation
Duplicate matching
Assignment queues
External intelligence integration
Tender ingestion
WhatsApp/email auto-import
Lead scoring
```

## Foundation-slice testing rule

Use the lighter Slice 1L testing gate: migration visible/applied, backend tests pass, frontend build/test pass, one happy-path manual check and one permission check.
