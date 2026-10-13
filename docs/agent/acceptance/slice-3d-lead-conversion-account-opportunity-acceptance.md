# Acceptance - Slice 3D Lead Conversion to Account + Opportunity

## Automated checks

```text
[ ] Alembic heads/current checked after migration.
[ ] docker compose exec backend pytest passed.
[ ] Frontend production build passed.
[ ] Frontend tests passed.
```

## Functional acceptance

```text
[ ] Sales/Admin can convert a QUALIFIED Lead.
[ ] Conversion creates one Account / business_party with status QUALIFIED_PROSPECT.
[ ] Conversion creates one Opportunity with source lead_conversion and status QUALIFIED.
[ ] Opportunity links to the created Account and source Lead.
[ ] Lead is marked CONVERTED only after Account and Opportunity are created.
[ ] Lead response/profile exposes links to the converted Account and Opportunity.
[ ] AccountCreated, OpportunityCreated and LeadConverted events are recorded.
```

## Permission and validation acceptance

```text
[ ] Finance/Operations/Management Read Only users cannot convert Leads.
[ ] Non-qualified Leads cannot be converted.
[ ] Already converted Leads cannot be converted again.
[ ] One source Lead cannot be linked to more than one conversion Opportunity.
```

## Deferred

```text
Existing Account matching / merge
PAN/GST duplicate matching
Credit checks and exposure consumption
Quote / Commercial Offer creation
Approval workflow
Work Order handoff
Customer activation
```

## Update, 4 October 2026: a converted Lead is final (TB-1 finding TB1-302)

Automated: `test_a_converted_lead_can_no_longer_be_edited_or_decided` fails without the change (the update returns
`200`) and passes with it; `leadStatus.test.ts`.

Screen check. Test user `sales1` (Sales User). Test data: any Lead converted on its page, or the smoke-data scenario
`vendor-demo-bundle` after converting its NEW Lead. Starting URL: `/leads/<lead public id>`.

1. Open a converted Lead: "Update Lead details" and "Qualification decision" show the note "This Lead has been
   converted, so its details and qualification decision can no longer be changed ..." instead of their forms; the
   Account and Opportunity links still show; follow-up activities can still be added.
2. Open a Lead not yet converted: both forms show and save as before.
3. Negative path (API): `PUT /api/leads/<converted id>` with `{"lead_status_code": "NEW"}` as `sales1` returns `422`
   with that message, and the Lead is unchanged.
4. Permission path: unchanged (`readonly1` still cannot update a Lead).
