# Slice 2E - Lead Qualification / Closure Decision Foundation

## Purpose

Add a controlled Lead qualification / closure decision step after Lead details and activities have been captured. This slice records the decision that a Lead is ready for qualification, qualified, unqualified or closed. It does not convert the Lead into Account or Opportunity.

## Scope

```text
- Add qualification decision fields to crm_lead
- Seed qualification decision workflow statuses
- Add POST /api/leads/{public_id}/qualification-decision
- Capture decision status, decision notes and reason
- Require reason for Unqualified and Closed decisions
- Record business events for each decision type
- Add Lead Qualification / Closure Decision section to Lead detail page
- Preserve Lead Activities / Follow-ups history
- Keep view-only roles able to see Lead details, activities and current decision information
```

## Backend events

```text
LeadQualificationReady
LeadQualified
LeadUnqualified
LeadClosed
```

## Explicit exclusions

```text
- Account creation
- Qualified Prospect creation
- Opportunity creation
- Lead conversion workflow
- Duplicate Lead / Account matching
- Approval workflow
- Task/reminder workflow
```

## Notes

The generic Lead Details update route remains separate from the qualification decision route. This avoids using ordinary Lead edits to perform business decisions that should have a clear event trail.
