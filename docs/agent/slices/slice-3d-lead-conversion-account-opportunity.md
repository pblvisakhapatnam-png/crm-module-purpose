# Slice 3D - Lead Conversion to Account + Opportunity

## Objective

Create the first controlled handoff from Lead to Account and Opportunity after the Opportunity foundation has been stabilized.

## Scope

In scope:

```text
- POST /api/leads/{public_id}/convert
- Convert only QUALIFIED Leads.
- Create an Account / business_party as QUALIFIED_PROSPECT.
- Create an Opportunity with source = lead_conversion and status = QUALIFIED.
- Link the Opportunity to both the created Account and source Lead.
- Mark the Lead as CONVERTED only after Account and Opportunity creation/linkage succeeds.
- Record AccountCreated, OpportunityCreated and LeadConverted events.
- Prevent duplicate conversion of the same Lead.
- Add a Lead profile conversion action for Sales/Admin roles.
```

Out of scope:

```text
- Existing Account matching or merge.
- PAN/GST duplicate matching.
- Credit checks and exposure controls.
- Quote / Commercial Offer.
- Approval workflow.
- Work Order handoff.
- Customer activation / Customer Master finalization.
```

## Minimum gate

```text
1. Migration head/current visible and upgrade clean.
2. Backend pytest passes.
3. Frontend build/tests pass.
4. Manual happy path: qualify Lead, convert, open created Account and Opportunity.
5. Manual permission path: Finance can view Lead but cannot convert.
6. Manual validation path: non-qualified Lead and already-converted Lead cannot be converted.
7. Contracts, acceptance and continuity notes updated.
```

## Update, 4 October 2026: a converted Lead is final (TB-1 finding TB1-302)

TB-1's Pass 3 found that the Lead details update and the qualification decision checked only the target status, so a
converted Lead could be set back to an open or closed status while it kept its Account and Opportunity. The owner
decided it was an emergency under the TB-1 plan's section 12 and chose a fix as its own package for the Lead half
(the Opportunity half waits for its closure rules).

- **Backend:** `leads/repository.py` `lock_lead_row`; `leads/service.py` `_locked_changeable_lead` - the row lock,
  then `422` for a CONVERTED Lead - used by `update_lead` and `decide_lead_qualification`.
- **Frontend:** `frontend/src/pages/leads/leadStatus.ts` (`leadCanBeChanged`, the note) with its test; the Lead page
  shows the note in place of the details and decision forms once converted.
- **Test:** `test_a_converted_lead_can_no_longer_be_edited_or_decided` (both routes, status and details, nothing
  changed, no event).
- **Records:** the Lead contract ("A converted Lead is final"), the 3D acceptance record,
  `docs/continuity/TB1_302_CONVERTED_LEAD_STAYS_CONVERTED.md` and `NEXT_STEPS.md`. No migration, no new route.
