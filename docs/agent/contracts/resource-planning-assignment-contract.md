# Resource Planning and Assignment Contract

## Contract ID and status

`RPA-001` - `APPROVED` - 12 August 2026.

## Boundary

Resource Requirement owns demand. Resource Availability owns candidate state/reservations.
Resource Assignment owns the final commitment and its history. Availability does not itself
assign, and Assignment does not recalculate availability by bypassing its interface.

## Availability query

```text
requirement public ID/version
resource category/type and quantity
site/location and scheduling window
operational constraints
eligibility requirements reference
as-of timestamp
```

## Candidate result

```text
candidate result public ID/version
requirement public ID/version
resource public ID
current/last-known location and as-of time
availability window and status
current/planned assignment or reservation references
maintenance/breakdown restriction reference
eligibility decision status/reference
owned/external source indicator
ranking inputs/explanation (non-binding)
```

Candidate ranking is advisory. A backend-authorized assignment command makes the commitment.

## Assignment command/result

The command names the requirement/version, selected candidate/resource, planned period,
site, crew references, eligibility decision and idempotency key. Success creates an assignment
public ID/version and reservation/commitment atomically under the first-valid-commit rule below.

## Failure behavior

Stale candidate versions, overlapping commitment, unavailable resource, invalid eligibility and
unfulfilled requirement quantity are distinct conflicts. Retrying must not create duplicate
assignments.

An active assignment also carries an eligibility/compliance decision reference and current
compliance state. `EligibilityLapsed` changes that state through an idempotent Assignment command;
it does not let Eligibility write Assignment tables directly. A statutory
`COMPLIANCE_BLOCKED` assignment cannot create new operational evidence or be extended and requires
an explicit release/replacement path.

## Settled baseline and configurable values

- The capability supports temporary reservations before final assignment. Reservation duration
  is a configurable operating parameter, not a reason to redesign the contract.
- Candidate ordering is advisory and may use suitability, availability, location, maintenance,
  eligibility and ownership/cost inputs. Statutory, maintenance and overlapping-commitment hard
  blocks cannot be bypassed by ranking.
- If two users attempt the same commitment, the first valid atomic commit succeeds; the other
  receives a conflict and must refresh. No duplicate/overlapping assignment is created.
- Partial fulfilment is supported and the remaining quantity stays visible.
- Plum Maintenance/Asset Management supplies owned-equipment maintenance restrictions. The
  authoritative master/location source is referenced with its as-of time; Assignment does not
  invent a competing master.
