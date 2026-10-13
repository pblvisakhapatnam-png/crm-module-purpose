# Organization Authority and Authorization Contract

## Contract ID and status

`ORA-001` - `APPROVED` - 12 August 2026. Amended 13 August 2026 by explicit PBL decision to record
the `CREDIT_ASSESSOR` resolution rule below. Status remains `APPROVED`; no other semantics changed.

## Purpose

Define how authenticated users receive application permissions, business authority and data
scope. This is the prerequisite for configurable approvals; it does not itself approve any
business record.

## Current-to-target boundary

The prototype currently authenticates users with coarse role codes and checks hard-coded role
tuples in route files. Those roles remain a migration input, but they are not sufficient for
Department Head, Managing Director, Risk Approver, Finance Customer Master Owner, Billing
Maker/Checker, Procurement or delegated authority.

The production model separates:

```text
authenticated user          who is signed in
application role            broad job family / transitional access grouping
permission                  allowed module action
data scope                  branch, site, project, customer or organization limit
organization position       user's current position in PBL
business authority          named decision authority, optionally with amount/type threshold
delegation                  time-limited transfer within the delegator's authority
```

Department Head, Managing Director and Risk Approver are business authorities, not new global
login roles. Plum HR Employee Master is authoritative for employee status, organization units,
positions, reporting relationships and current position incumbents. ORA stores stable references
and the version/effective snapshot used for a decision; it does not create or maintain a second
organization structure.

Authorized administrators maintain the application mapping from those authoritative employee/
position references to permissions, data scope and business authority. Named people and authority
assignments are data rather than constants in code.

## Employee Master input

`RMR-001` supplies, directly or through the Integration Gateway:

```text
employee public ID and application-user link
employment/active status and effective time
organization-unit and position public IDs
position/designation and reporting reference where required for policy
position incumbent/effective-from/effective-to
master version, changed-at and as-of time
change type: joiner / position or scope change / inactive or leaver / correction
```

ORA may cache only the minimum versioned snapshot needed for authorization and audit. An HR
change updates the authorization source; an ORA administrator cannot edit the copied position to
make it disagree with Employee Master.

A human business-authority assignment requires a current Employee Master reference. Technical/
service identities may receive only explicitly defined machine permissions and cannot hold or
exercise Department Head, Managing Director or other human approval authority.

## Minimum authority assignment

```text
authority_assignment_public_id / version
user_public_id, employee_public_id and organization_position public reference/version
authority_code
applicable module / decision type
branch/site/department/project/customer scope where applicable
amount/currency or other threshold where applicable
valid_from / valid_to
status
status reason and Employee Master change/effective reference where applicable
delegation source reference where applicable
created/approved/suspended/reactivated/revoked actor (or system actor) and timestamp
reason/evidence reference
```

## Initial authority catalogue

| Authority | Initial business meaning |
| --- | --- |
| `CREDIT_ASSESSOR` | Performs the Account credit assessment. Initial/default mapping is `SALES_MANAGER`; assignable to any eligible employee/position without a code change |
| `CREDIT_APPROVER` | Applicable Department Head or Managing Director under configured scope/threshold |
| `IDENTITY_EXCEPTION_HANDLER` | Accounts by default; authorized Sales assignment permitted |
| `FINANCE_CUSTOMER_MASTER_OWNER` | Approves/rejects Customer Master activation and reconciliation |
| `RISK_APPROVER` | Decides only configured non-statutory eligibility exceptions |
| `BILLING_MAKER` | Prepares Billing Worksheets; cannot perform the required checker decision on the same version |
| `BILLING_CHECKER` | Reviews/approves Billing Worksheets independently of the maker |
| `VENDOR_HIRE_APPROVER` | Approves Vendor Hire Agreements within configured authority |
| `PROCUREMENT_AUTHORITY` | Performs required Procurement/PO actions when D-04 policy requires them |
| `FINANCE_AP_CHECKER` | Approves vendor-payable handoff where the payable policy requires it |

This catalogue defines capabilities, not named people. Additional authority codes require an
owned contract/policy change when they alter business meaning.

### `CREDIT_ASSESSOR` resolution rule

Recorded 13 August 2026 by explicit PBL decision, and consumed by `ACP-001`:

- The credit assessment may be performed only by an authenticated user holding a current, active
  `CREDIT_ASSESSOR` assignment for the relevant organizational/data scope.
- The initial/default mapping is the `SALES_MANAGER` application role, preserving the agreed
  current operating arrangement and migration compatibility.
- Assignments are made against eligible Employee Master employee/position references, with scope
  and validity (`valid_from` / `valid_to`) like any other authority in this contract.
- The target authorization decision uses the active authority assignment, not the application
  role. Authorized administrators may assign, suspend, revoke or reassign `CREDIT_ASSESSOR`
  without a code change.
- The transitional role-based check is compatibility only. It must not survive as a permanent
  hard-coded role check once the mapped permission and authority assignment are tested.
- Administering authority assignments and exercising `CREDIT_ASSESSOR` are separate capabilities.
  Business authority is never granted implicitly because a user is an administrator.

Preparing a credit proposal is not performing the assessment; proposal preparation remains with
the authorized Sales roles under the Account contract. Credit *approval* is separate again and
requires `CREDIT_APPROVER` under the configured Department Head / Managing Director policy.

## Authorization result

Backend policy resolution returns an allow/deny result with the authenticated user, applicable
permission, data scope, authority assignment/version and reason. Frontend hiding is only a
usability aid.

Clients cannot assert roles, authority, scope, thresholds or approver identity. Every sensitive
decision rechecks current backend authority against the source record and policy version.

## Delegation

- Delegation is explicit, time-limited, revocable and auditable.
- A delegate cannot receive authority beyond the delegator's scope or threshold.
- A delegation cannot remove a required maker/checker separation.
- Decisions retain both the acting user and the authority/delegation reference used at the time.

## Employment and position change lifecycle

Authority validity is continuously constrained by the current Employee Master status and
position assignment:

1. Employee Master publishes/exposes a versioned joiner, transfer/promotion, organization-scope
   change, position-incumbent change, inactive/leaver or correction fact.
2. ORA consumes the fact idempotently and re-evaluates every affected permission, data scope,
   authority assignment and outgoing delegation.
3. A temporary inactive/suspended employment fact immediately suspends the user's authority
   assignments and outgoing delegations for new decisions. A permanent leaver/termination fact
   revokes them at its authoritative effective time and records `AuthorityRevoked`; no separate
   administrator reminder is required to make the revocation happen.
4. A position, department, branch, reporting or scope change suspends any assignment whose basis
   no longer matches and marks it `REVIEW_REQUIRED`. It is re-assigned or explicitly confirmed
   against the new authoritative position before use.
5. Pending approval work is re-resolved to another currently eligible authority. Historical
   decisions retain the valid authority snapshot used at their decision time.
6. Corrected/reactivated HR data does not silently or retrospectively restore authority. An
   authorized ORA review creates/reactivates a current assignment from its effective time; it
   never backdates authority over the suspended gap.

Every sensitive authorization decision checks current Employee Master/ORA versions. After a
configured maximum source-data age, a stale or unavailable HR feed fails closed for new
authority-dependent decisions and raises an operational exception. The temporary fallback is a
controlled, versioned Employee Master import through the same adapter, never a manually edited
CRM organization master.

## Events

Logical facts include `AuthorityAssigned`, `AuthorityChanged`, `AuthoritySuspended`,
`AuthorityReviewRequired`, `AuthorityDelegated`, `AuthorityDelegationRevoked`,
`AuthorityReactivated` and `AuthorityRevoked`. Events contain no authentication secrets.

## Migration and implementation rule

The implementation slice must inventory every current hard-coded role tuple and map each action to
an explicit permission. Existing role behavior remains compatible until the mapped permission is
tested. No approval-dependent module may invent its own organization or authority table.
PF-1A cannot pass or freeze ORA until the Plum HR organization/position/status interface or its
controlled versioned-import fallback and change/recovery behavior are validated.

## Note on the Plum HR source (ADR-032, 31 August 2026)

This contract's text above is unchanged by ADR-032 and remains the authoritative statement of
*ownership*: Employee Master, as a logical capability, is authoritative for employee/organization/
position facts, and ORA consumes only that capability's output. ADR-032 records a purely factual
refinement of "the Plum HR organization/position/status interface" language above: PBL has
confirmed Plum does not currently implement a structured Organisation Unit Master, Position
Master, or Position Incumbency record, so the "controlled versioned-import fallback" this contract
already contemplates is, concretely, the governed SharePoint-backed interim source described in
`docs/agent/pf-1f-hr/`, not a live sophisticated Plum interface. "Validated" in the sentence above
means the accepted canonical HR-reference contract plus representative interim reference data, per
`docs/agent/pf-1f-hr/PF_1F_HR_DECISION_GATE.md` - not validation of Plum structures PBL has
confirmed do not exist. See ADR-032 in `docs/agent/ARCHITECTURE_DECISIONS.md` for the full
decision.
