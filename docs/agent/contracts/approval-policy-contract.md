# Approval Policy Contract

## Contract ID and status

`APR-001` - `APPROVED` - 12 August 2026.

## Boundary

Approval Policy owns the rules that map a decision type/value/scope to required authority,
approval requests and decision evidence. The consuming business module owns what is being
approved and enforces the approved result against its aggregate.

Employee Master owns employees and organization positions. `ORA-001` owns application
permissions, data-scope/authority mappings and delegation validity against those references.
`APR-001` consumes that authoritative result and owns approval requests and decisions; it must
not create a second employee, organization or authority model.

## Approval request

```text
approval request public ID/version
policy code/version
source module, record type/public ID/version
decision type
amount/currency or other threshold inputs where applicable
requester identity
reason and evidence references
correlation/idempotency metadata
```

## Policy resolution and decision

```text
eligible role/authority and named assignment references
required approvals and maker/checker rule if configured
delegation reference/validity
decision: APPROVED / REJECTED / RETURNED / WITHDRAWN
authenticated decision-maker identity and authority snapshot
decision timestamp, reason, conditions and evidence
policy version used
```

Passwords, tokens and reusable credentials are never approval evidence. Clients cannot assert
their own authority; backend authentication and policy resolution are authoritative.

## Initial credit policy

For Account credit, the current eligible authority is the applicable Department Head or Managing
Director. Named approvers, thresholds and maker/checker independence remain configurable; no
additional rule is invented by this contract.

The credit approver acts while authenticated. A Sales proposal or uploaded document cannot assert
that the Department Head/Managing Director approved it. `ACP-001` activates effective values only
from a valid decision reference resolved through this contract.

## Settled baseline and module policy

- Authorized administrators maintain policy, named approver assignments and delegations; every
  change records who changed it, when, the old/new values and its effective period.
- The applicable Department Head or Managing Director is resolved from configured organization,
  role and authority assignments, not hard-coded names or credentials.
- Delegation is explicit, time-limited, revocable and cannot exceed the delegator's authority.
- Approval remains tied to the source record/version and policy version. A material change,
  withdrawal, supersession or configured expiry requires a new decision.
- Maker/checker independence applies only where the owning business policy requires it. It is
  already required for Billing Worksheets and specified vendor-payable controls; it is not
  imposed on credit approval until configured by PBL.
- Modules adopt the common facility as their approval slices are implemented; no separate PBL
  decision is needed merely to choose an implementation order.

Implementation of this contract starts only after the `ORA-001` authorization/organization-
authority foundation and its fixtures are ready.
