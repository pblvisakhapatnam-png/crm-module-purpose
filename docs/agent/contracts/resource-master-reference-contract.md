# Equipment and Employee Master Reference Contract

## Contract ID and status

`RMR-001` - `APPROVED` - 12 August 2026.

## Boundary

Equipment Master is the authoritative source for owned equipment/vehicle identity and technical
master details. Employee Master is the authoritative source for employee identity, employment
status, organization units, positions/designations, reporting relationships and current position
incumbents. Resource Catalogue, Eligibility, Assignment and ORA keep stable references and the
small operational/decision snapshot needed for traceability; they do not create competing
masters.

Secured external equipment and external crew use the approved Market Hire/vendor-resource
reference until wider ERP master ownership is decided.

## Equipment reference

```text
equipment public ID and business reference
equipment category/type
make/model and key technical classification
ownership/control type
active/retired status
home/base location where authoritative
required document/evidence references
master version and updated-at
```

Availability, maintenance restrictions and assignment state remain outside Equipment Master.

## Employee/crew reference

```text
employee public ID and employee number
display name
employment/active status
organization/department and designation where needed
organization-unit and position public IDs, incumbent/effective period and reporting reference
crew/operator classification where authoritative
required identity/document references
master version and updated-at
```

Skills, licences and assignment eligibility remain owned by Compliance/Eligibility unless a later
approved master boundary assigns a specific field elsewhere.

## Change behavior

Master changes publish or expose a versioned result. Resource/authorization consumers retain the
master public ID and version used for historical assignments, decisions and log evidence.
Deactivation or retirement prevents new commitments/authority decisions under policy but does
not rewrite history. Employee inactive/leaver, transfer, promotion, organization-scope and
position-incumbent changes are supplied to ORA for the lifecycle in `ORA-001`.

Logical Employee Master facts include `EmployeeEmploymentStatusChanged`,
`EmployeePositionAssignmentChanged` and `EmployeeOrganizationScopeChanged` (names may be mapped
to the authoritative Plum interface). Consumers process version/effective time idempotently and
perform a recovery reconciliation after feed downtime.

## Settled baseline

- Plum Maintenance and Asset Management Equipment Master is authoritative for owned equipment.
- Plum HR Employee/Crew Master is authoritative for PBL employees and crew.
- Planners see only operationally necessary identity, category/type, model/classification,
  active status, ownership origin, current/base location, skills/licence status and relevant
  master version. Sensitive HR data is not copied into planning.
- A retired/inactive record cannot receive a new assignment. An active assignment becomes a
  visible exception requiring release or replacement; history is preserved. A statutory or
  safety invalidity hard-blocks continued assignment under `ELA-001`.

Outside-hired equipment uses the Hiring Vendor Equipment Register. Vendor crew representation is
the separate unresolved decision D-03 under `MHA-001`; it does not prevent approval of the owned
Equipment/Employee Master reference boundary.

## Note on the Plum HR source for employees/organization/position data (ADR-032, 31 August 2026)

The "Plum HR Employee/Crew Master is authoritative for PBL employees and crew" statement above is
unchanged by ADR-032 and remains the authoritative *ownership* statement: Employee Master, as a
logical capability, is authoritative for employee/crew facts, and this contract's boundary (planners
see only the operational minimum, no competing master) is unchanged. ADR-032 records a purely
factual refinement for the structured organization-unit/position/incumbency data this same
capability is elsewhere described as covering (see `RMR-001`'s "Employee/crew reference" section
above, and `ORA-001`): PBL has confirmed Plum does not currently implement a structured
Organisation Unit Master, Position Master, or Position Incumbency record. The current (Phase 1)
implementation of that structured data is a governed SharePoint-backed interim source composed
behind the HR-reference adapter/composition boundary in `docs/agent/pf-1f-hr/`, not a live
sophisticated Plum interface; the eventual canonical implementation is a future `NEW_SHARED_PLATFORM`
HR/Organisation Reference Master. See ADR-032 in `docs/agent/ARCHITECTURE_DECISIONS.md` for the full
decision.

## Note on the equipment structure (ADR-037, 24 September 2026)

The statement above that Plum's Equipment Master is authoritative for owned equipment is unchanged for
**machine identity, status and statutory documents**, which Plum holds in Phase 1. ADR-037 records one
refinement: the **structure** equipment is described in - classes, the types within each, and the
capabilities that describe them, each in one fixed unit - is the platform's own **Equipment
Reference**, not Plum's category list. Plum's categories enter it through an alias table, and Plum's
machines will enter it through an adapter-owned transformer, with authority stated per phase (Phase 1
Plum for machines, Phase 2 the platform, Phase 3 Plum ingests from the platform). This contract's
boundary - planners see only the operational minimum; no competing master for any fact - is unchanged.
See ADR-037 in `docs/agent/ARCHITECTURE_DECISIONS.md` and the WRR-001 design,
`docs/agent/slices/wrr-001-resource-requirement-foundation.md`.

ADR-037's refinement of 25 September 2026 (ERT-1) adds one sentence: in Phase 1 Plum's machine facts
are read **as corrected by the Fleet Admin** - by a recorded rule or correction, applied on every import
and listed for Plum to fix at source - and facts the job needs that Plum does not hold (a machine's
serial number and year of manufacture, so far) are entered on the platform, which is their source; each
fact still has one owner.
