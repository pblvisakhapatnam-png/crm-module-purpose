# Work Order to Resource Requirement Contract

## Contract ID and status

`WRR-001` - `APPROVED` - 12 August 2026.

## Owners

Work Order owns contractual demand. Resource Requirement owns the operational demand record used
for planning and fulfillment. Requirement does not alter the Work Order.

## Trigger

A valid Work Order shell line may create a Resource Requirement and begin non-committing planning.
Final reservation/assignment, mobilisation, Log Sheet and execution actions require the Work
Order state and readiness checks defined for those actions; an unreleased shell does not authorize
execution.

## Minimum requirement

```text
requirement_public_id
Work Order public ID/number/version
Work Order line public ID/version
source Commercial Offer line public ID
Account and site/location public references
required resource category/type and quantity
required start/end or scheduling window
skill/licence/certification requirements
crew/operator requirements where applicable
operational constraints and priority
requirement status/version
correlation/source event reference
```

Commercial rate fields are referenced through Work Order terms and are not copied into planning
unless an approved operational rule requires them.

## Result semantics

Resource Requirement publishes created/changed/cancelled facts. Availability and Market Hire may
consume the same requirement. Assignment references the requirement public ID and fulfilled
quantity; it does not rewrite the Work Order.

## Settled baseline

- Planning may begin from a valid Work Order shell so Operations can search and prepare without
  treating the shell as released work.
- Resource categories come from the authoritative Equipment and Employee/Crew Masters. A
  requirement records count/quantity, planning period and the Work Order billing basis where
  operationally relevant; it does not invent a duplicate category catalogue.
- One requirement may be partly fulfilled, split across several resources or periods, and later
  completed. Every fulfilment remains linked to the same Work Order line and source Offer line.
- Cancellation prevents new reservations/assignments and releases uncommitted reservations.
  Existing commitments use an explicit release/replacement/cancellation action and retain
  history; they are never silently deleted.
