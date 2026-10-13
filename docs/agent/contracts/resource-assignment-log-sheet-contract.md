# Resource Assignment to Log Sheet Contract

## Contract ID and status

`RAL-001` - `APPROVED` - 12 August 2026.

## Owners

Resource Assignment owns who/what was committed and when. Log Sheet owns the operational evidence
of what occurred. A Log Sheet cannot rewrite assignment history.

## Assignment context supplied

```text
assignment_public_id and version
requirement public ID
Work Order and Work Order line public IDs/versions
resource public ID and category/type
owned/external source indicator
site/location reference
planned assigned-from/to
actual release/replacement references where available
crew/operator public references
eligibility decision/evidence reference
assignment status
```

## Log Sheet initiation rule

Only an assignment state explicitly eligible for operational recording, with a current eligible
compliance decision, may initiate a Log Sheet. A statutory `COMPLIANCE_BLOCKED` assignment cannot
produce new Log Sheets. The Log Sheet snapshots necessary assignment context while retaining
source IDs and versions.

The evidence key is the billable Work Order line plus effective assignment/period, not equipment
alone. Equipment-hire lines normally produce one daily Log Sheet per active equipment assignment.
A crew/operator/service-only Work Order line can produce a daily crew/service Log Sheet when its
Work Order terms make that assignment independently executable or billable. It must not invent an
equipment reference. Combined equipment-and-crew evidence retains both assignment references.

## Changes after evidence exists

Replacement/reassignment creates traceable assignment history. Existing Log Sheets retain their
original assignment reference; corrections do not silently relink evidence.

## Events

Logical facts include `ResourceAssigned`, `ResourceReplaced`, `ResourceReleased` and
`LogSheetInitiated`.

## Settled baseline

- Daily Log Sheets are generated for each effective, execution-eligible billable assignment/Work
  Order line. Equipment-hire lines use the active equipment assignment; crew/service-only lines
  use their own assignment. A reservation or unreleased Work Order cannot produce billable
  evidence.
- Business time is Asia/Kolkata. Site/shift boundaries come from the applicable Work Order/site
  terms rather than a global hard-coded shift length.
- The same resource cannot have overlapping active assignments. A specifically modelled crew
  team may contain several non-overlapping crew member commitments for one equipment assignment.
- Equipment or crew replacement ends the old effective assignment/evidence period and starts a
  new one. Existing Log Sheets retain the old references and complete audit history.
