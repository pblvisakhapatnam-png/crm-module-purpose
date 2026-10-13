# PF-1F-HR Dependency Source Baseline

## Status

Package: PF-1F-HR-E1. Documentation/architecture baseline only. No runtime change. See
`docs/agent/ARCHITECTURE_DECISIONS.md` ADR-032 and ADR-033 for the decisions this baseline
implements.

## Purpose

Record, for every data/capability the HR reference and authority model depends on, which system
is the actual current source, how confident that classification is, and what remains open. This
file exists because the PF-1F-HR discovery showed that assuming an external master's mere
existence proves it holds the required structure was itself the root problem; this baseline makes
the "who actually supplies this today" question explicit and auditable rather than implicit in
prose scattered across contracts.

## Classification values

Authoritative-source classification (use only these):

```text
NEW_CRM              Owned by this repository's CRM module
NEW_HIRING           Owned by this repository's Hiring module (not yet implemented)
NEW_SHARED_PLATFORM  Owned by a future PBL shared-platform capability (ADR-030)
PLUM                 Owned by the existing Plum ERP product
OTHER_EXTERNAL       Owned by an external product/service that is not Plum (e.g. SurePass,
                     SharePoint, a notification provider)
UNRESOLVED           Ownership is not yet confirmed
```

Confidence value (use only these):

```text
CONFIRMED                 PBL has explicitly confirmed this fact
ARCHITECTURE_INTENT       Recorded as the approved target direction, not yet independently verified
ASSUMED_NEEDS_VALIDATION  A working assumption that still needs confirmation before reliance
UNRESOLVED                Not yet known
```

Do not label the central ERP Vendor Master as "Plum" unless repository evidence shows that is its
actual physical source; `VMR-001`/`EXTERNAL_DEPENDENCY_REGISTER.md` currently record it only as
"Central ERP Vendor Master" with an unconfirmed product/module.

## HR reference and authority dependency inventory

| Dependency / canonical need | Authoritative owner (target) | Current physical source | Classification | Confidence | Notes |
| --- | --- | --- | --- | --- | --- |
| Employee identity, employment/active status | Employee Master (`RMR-001`) | Plum HR (flat/basic fields only, structure unconfirmed) + interim SharePoint reconciliation record | PLUM (raw facts) / interim OTHER_EXTERNAL (SharePoint) | ASSUMED_NEEDS_VALIDATION (stable Employee ID is UNKNOWN/LIKELY ABSENT per ADR-032 - a source-capability question, not confirmed absent) / ARCHITECTURE_INTENT (SharePoint interim) | Do not mark Employee ID reliability CONFIRMED-absent; only the four structural gaps below are human-confirmed (ADR-032). See `PF_1F_HR_PLUM_GAP_ANALYSIS_PACKET.md` |
| Organisation Unit hierarchy | Employee Master (`RMR-001`), eventually NEW_SHARED_PLATFORM | Confirmed absent as a structured master in Plum today; interim SharePoint List | OTHER_EXTERNAL (interim) -> NEW_SHARED_PLATFORM (target) | CONFIRMED (Plum gap) / ARCHITECTURE_INTENT (SharePoint interim, shared-platform target) | See ADR-032 |
| Position Master | Employee Master (`RMR-001`), eventually NEW_SHARED_PLATFORM | Confirmed absent in Plum today; interim SharePoint List | OTHER_EXTERNAL (interim) -> NEW_SHARED_PLATFORM (target) | CONFIRMED (Plum gap) / ARCHITECTURE_INTENT | See ADR-032 |
| Position Incumbency (effective-dated occupancy) | Employee Master (`RMR-001`), eventually NEW_SHARED_PLATFORM | Confirmed absent in Plum today; interim SharePoint List | OTHER_EXTERNAL (interim) -> NEW_SHARED_PLATFORM (target) | CONFIRMED (Plum gap) / ARCHITECTURE_INTENT | See ADR-032 |
| HR change-feed (joiner/transfer/promotion/scope/leaver/correction) | Employee Master (`RMR-001`), eventually NEW_SHARED_PLATFORM | Confirmed absent in Plum today; Phase 1 derives events by comparing controlled SharePoint/Plum state, not a manually maintained event list | NEW_SHARED_PLATFORM (target); Phase 1 derivation is owned by the **HR-reference adapter/composition capability** (never PF-1A/CRM/Hiring - corrected under PF-1F-HR-E1 Correction 1, C1-1) reading both interim sources | CONFIRMED (Plum gap) / ARCHITECTURE_INTENT (derivation approach) | PF-1A only ever reads the resulting canonical events; it never compares Plum/SharePoint itself. See `PF_1F_HR_CANONICAL_REFERENCE_MODEL.md` sections E, G and H |
| Crew classification / credential reference | Employee Master (`RMR-001`) / Compliance-Eligibility (`ELA-001`) | Plum, extent unconfirmed field-by-field | PLUM (target, pending gap analysis) | ASSUMED_NEEDS_VALIDATION | Do not move wholesale into SharePoint without a demonstrated gap; see `PF_1F_HR_PLUM_GAP_ANALYSIS_PACKET.md` section F |
| Role Catalogue, Authority Catalogue, Role->Authority rules, Person/Position->Role assignment | Organization Authority (`ORA-001`) | New: PBL/platform-owned configuration (parameter file / future admin UI) | NEW_SHARED_PLATFORM | ARCHITECTURE_INTENT | See ADR-033 and `PF_1A_AUTHORITY_CONFIGURATION_MODEL.md`; never sourced from Plum or SharePoint |
| Approval decision evidence/audit trail | Organization Authority (`ORA-001`) / Approval Policy (`APR-001`) | New: PBL/platform-owned | NEW_SHARED_PLATFORM | ARCHITECTURE_INTENT | Retains configuration version at decision time |

## Later PF-1F dependency inventory (captured, not implemented by this package)

These lanes are recorded so a future PF-1F sub-package can apply the same method
(`EXTERNAL_DEPENDENCY_SOURCE_GAP_VALIDATION_METHOD.md`) without rediscovering scope. None are
implemented, validated or scheduled by PF-1F-HR-E1.

| Dependency | Consumer | Authoritative owner (if known) | Current source (if known) | Classification | Confidence | Known evidence | Known uncertainty | Future validation lane | Stopgap feasible? | Open decision |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Equipment / Maintenance Master | Resource Catalogue, Availability, Eligibility, Assignment | Fleet Equipment Master Owner | Plum Maintenance and Asset Management (per `RMR-001`) | PLUM | ARCHITECTURE_INTENT | `RMR-001` names Plum Maintenance/Asset Management as authoritative | No API/export/readiness evidence in repo (`EXTERNAL_DEPENDENCY_REGISTER.md`: `INTERFACE_NEEDED`) | `PF-1F` equipment sub-lane | Controlled read-only versioned import through the same adapter, never a competing master | Confirm interface/sample data before RMR adapter prompt |
| Vendor Master / central ERP vendor authority | Market Hire, Vendor Payable | Purchase/Finance Vendor Master Owner | Central ERP Vendor Master, physical product/module not yet inventoried | UNRESOLVED | ASSUMED_NEEDS_VALIDATION | Accepted FRS requires one centralized vendor registry (`VMR-001`) | Current product/module interface not inventoried; do not assume "Plum" without evidence | `PF-1F` vendor sub-lane | Controlled versioned read-only import; free-text supplier creation prohibited | Identify current master product/module/owner before VMR adapter prompt |
| Customer Master | Customer Master Activation (`CMA-001`), Work Order release | Finance Customer Master Owner | Plum Customer Master | PLUM | ARCHITECTURE_INTENT | Ownership/timing settled per `EXTERNAL_DEPENDENCY_REGISTER.md` | Create/query/reconciliation interface not evidenced | `PF-1F` customer sub-lane / CMA slice discovery | Controlled Finance action with external reference entered/reconciled | Confirm duplicate-match/activation interface during CMA discovery |
| Finance / receivables / unbilled Work Order inputs | Credit Exposure (`CEX-001`) target formula | Finance Credit Control | Plum/Finance | PLUM | ARCHITECTURE_INTENT | Target formula settled; feed/cutover is the open item (D-02) | Reliable feed/cutover readiness unconfirmed | `PF-1F` finance sub-lane | Continue labelled temporary basis: allocated active Work Order value | D-02: Finance/Plum confirm data quality and cutover readiness |
| SurePass | Account identity validation (`AIV-001`) | Accounts identity-exception owner | SurePass (already used by PBL per ADR-015) | OTHER_EXTERNAL | CONFIRMED (in use) / ASSUMED_NEEDS_VALIDATION (API fields/access) | PBL confirms SurePass is already used | Account API fields, environment/access, support process not evidenced in repo | AIV runtime implementation | Pending state + audited manual route for prolonged outage | Confirm credentials/environment/API catalogue/rate limits/support path |
| SharePoint document repository | Documents/Evidence capability | IT Document Repository Owner | SharePoint (approved direction) | OTHER_EXTERNAL | ARCHITECTURE_INTENT | Repository direction exists | Library, permission and retention design open (D-05) | `PF-1F` documents sub-lane / D-05 | ERP metadata plus controlled manual repository reference | D-05 before SharePoint document automation |
| Notification channels/providers | Notifications (`NTF-001`) | HR/Sales/Operations per trigger | Not yet selected | UNRESOLVED | ASSUMED_NEEDS_VALIDATION | Required alerts accepted | Delivery providers/escalation channels not selected | `PF-1D`/`PF-1F` notification sub-lane | In-app queue plus owned manual escalation for critical failures | Select channels/provider and support ownership during NTF implementation |
| GPS / IoT / telematics | Future Resource Assignment / Log Sheet enrichment | Not yet named | Not yet identified | UNRESOLVED | UNRESOLVED | No repository evidence of a selected provider | Entirely open | Future PF-1F sub-lane, not yet scheduled | Not yet assessed | Not yet named as a business priority |

## Reconciliation note

This baseline does not change any contract's frozen/approved semantics. It records, as of
31 August 2026, which physical system actually supplies each dependency today, distinct from which
logical module is architecturally authoritative for it. Where the two currently differ (for
example: Employee Master is architecturally authoritative for Position data, but Plum does not
currently hold a Position Master), the interim source is named explicitly rather than left
implicit.
