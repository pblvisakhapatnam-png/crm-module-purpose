# External Dependency Source/Gap Validation Method

## Status

Adopted, 31 August 2026, as a standing analysis method (PF-1F-HR-E1 / ADR-032). Applies by default
to every current and future external dependency this programme relies on. This document is a
reusable method, not an inventory; the current inventory lives in
`EXTERNAL_DEPENDENCY_REGISTER.md` (near-term production dependencies) and
`docs/agent/pf-1f-hr/PF_1F_HR_DEPENDENCY_SOURCE_BASELINE.md` (HR-specific baseline plus the
captured-not-implemented later PF-1F lanes).

## Why this method exists

The PF-1F-HR discovery found a conflation between two genuinely different things: (1) `RMR-001`/
ADR-026's ownership decision, correctly stated, that Employee Master - as a **logical capability**
- is authoritative for employee/organization/position facts, and ORA and other consumers should
depend on that capability's output rather than inventing a competing structure; and (2) an
unwarranted further assumption that Plum, the specific physical system named as the initial
business source, must therefore *itself* already contain the structured Organisation Unit /
Position / Incumbency / change-feed model that capability implies. PBL has since confirmed (2) is
false: Plum supplies basic/raw employee facts, not that structure. **An existing source system does
not automatically mean a sufficient canonical master.** Confirming who owns a business concept
(the authoritative owner) is a separate question from confirming what a specific named system
actually contains (the existing source's real capability) - do not let a correct answer to the
first question stand in for an answer to the second, for the next dependency this method is applied
to.

## The method

Apply all sixteen steps to every external dependency before scheduling an implementation package
that depends on it:

```text
1.  REQUIRED CANONICAL DATA/CAPABILITY
    What does the new capability actually need, expressed independently of any particular source
    system (field names, identifiers, effective dating, freshness)?

2.  AUTHORITATIVE BUSINESS OWNER
    Which business function/system is supposed to own this concept? (This may be settled already,
    e.g. by ADR-026 for HR, or by RMR-001/VMR-001 for equipment/vendor.)

3.  EXISTING SOURCE/SYSTEM
    What system currently implements that ownership in practice? Name the actual product/module,
    not just "the ERP" - and do not assume it is Plum unless there is repository evidence for that
    specific dependency (see PF_1F_HR_DEPENDENCY_SOURCE_BASELINE.md's "do not label the central
    ERP Vendor Master as Plum" rule for a concrete example of this mistake to avoid).

4.  ACTUAL FIELDS/CAPABILITIES AVAILABLE
    Field-by-field or capability-by-capability: what does the named source actually contain today,
    in what form? Do not infer from the system's general reputation or its authoritative-owner
    status.

5.  STABLE IDENTIFIER QUALITY
    Does a stable, immutable identifier exist for the entity in question? Is it ever reused,
    reissued, or is the practical identifier just a name or free text?

6.  EFFECTIVE-DATING/HISTORY QUALITY
    Can the source answer "what was true as of a given past date," or does it only expose current
    state?

7.  INTERFACE/EXPORT/API AVAILABILITY
    Is there a machine-readable interface (API, export, feed), or only a UI screen a human reads?

8.  CHANGE-FEED/DELTA AVAILABILITY
    Can consumers detect what changed since a prior check, or must they always re-read full state?

9.  FRESHNESS/LATENCY
    How current is the data likely to be relative to the real-world fact it represents?

10. RECOVERY/RECONCILIATION
    If a feed/import is missed or fails, what is the recovery path? Full reconciliation? Manual
    catch-up?

11. SECURITY/DATA CLASSIFICATION
    Classify the fields per `DATA_CLASSIFICATION_AND_HANDLING.md` before deciding what a consumer,
    an interim source, or a fixture may copy.

12. FIELD/CAPABILITY GAP
    The explicit difference between step 1 (need) and steps 4-9 (actual availability).

13. INTERIM SOURCE/ADAPTER STRATEGY
    Where a gap exists, can a controlled, provider-neutral interim source close it (e.g. governed
    SharePoint Lists for HR reference data) without creating a competing master? State the
    strategy explicitly; do not leave the gap unaddressed by default.

14. EVENTUAL SYSTEM OF RECORD
    Name the target long-term owner, even if it differs from both the current source and the
    interim bridge (e.g. Plum today -> SharePoint interim -> NEW_SHARED_PLATFORM eventual, per
    ADR-032).

15. PROVIDER-NEUTRAL CONSUMER CONTRACT
    Define the contract consumers depend on so that swapping the current source, the interim
    bridge, or the eventual system of record never requires a consumer code change.

16. BLOCKING VS NON-BLOCKING GAP DECISION
    Classify the gap as a source/interface deficiency (bridge it, do not block unrelated work) or
    a missing business/governance definition (escalate for an explicit decision; only that
    specific dependent decision is blocked, not unrelated work). See
    `docs/agent/pf-1f-hr/PF_1F_HR_DECISION_GATE.md` for a worked example of this distinction.
```

## Worked example: this package's own application

| Step | HR reference application (this package) |
| --- | --- |
| 1. Required canonical data | Employee, Organisation Unit, Position, Position Incumbency, HR change events - see `PF_1F_HR_CANONICAL_REFERENCE_MODEL.md` |
| 2. Authoritative business owner | Employee Master, as a logical capability (ADR-026, `RMR-001`) - not Plum specifically; step 3 below is where the actual physical source is named and checked |
| 3. Existing source/system | Plum HR (flat/basic fields only; confirmed NOT to include a structured Organisation Unit Master, Position Master, or Position Incumbency record - see step 4) |
| 4. Actual fields available | Unconfirmed pending the Plum conversation in `PF_1F_HR_PLUM_GAP_ANALYSIS_PACKET.md`; structured org/position/incumbency confirmed absent |
| 5. Stable identifier quality | Unknown/likely absent (ADR-032) |
| 6. Effective-dating/history quality | Confirmed absent for org/position/incumbency |
| 7. Interface/export availability | Unconfirmed |
| 8. Change-feed/delta availability | Confirmed absent |
| 9. Freshness/latency | Unconfirmed |
| 10. Recovery/reconciliation | Not yet designed; deferred to the future adapter implementation |
| 11. Security/data classification | Restricted personal/statutory fields excluded from this reference model per `DATA_CLASSIFICATION_AND_HANDLING.md` |
| 12. Field/capability gap | Organisation Unit / Position / Incumbency / change-feed structure; Employee ID reliability |
| 13. Interim source/adapter strategy | Governed SharePoint Lists (Phase 1), `PF_1F_HR_SHAREPOINT_STARTER_SPEC.md` |
| 14. Eventual system of record | `NEW_SHARED_PLATFORM` HR / Organisation Reference Master (Phase 2), with Plum synchronization (Phase 3) |
| 15. Provider-neutral consumer contract | `PF_1F_HR_CANONICAL_REFERENCE_MODEL.md` adapter contract |
| 16. Blocking/non-blocking | Structural gaps: non-blocking (bridged by SharePoint). Employee ID reliability: non-blocking - a source-capability/reconciliation-quality question, not a missing business definition; it does not gate either PF-1A readiness state. `AUTHORITY_CONFIGURATION_ADMIN` bootstrap: blocking, but only for `READY_FOR_PRODUCTION_AUTHORITY_ACTIVATION` specifically, not for PF-1A design/implementation or unrelated work - see `PF_1F_HR_DECISION_GATE.md` |

## Reuse targets

This method must be applied, and its result recorded (in `EXTERNAL_DEPENDENCY_REGISTER.md` or a
dedicated sub-package baseline as this HR case did), before scheduling implementation work
depending on:

```text
Equipment / Maintenance Master
Vendor Master / central ERP vendor authority
Customer Master
Finance / receivables / unbilled Work Order inputs
SharePoint document repository (the Documents/Evidence use, distinct from this HR-reference use)
Notification channels/providers
GPS / IoT / telematics
Any other dependency discovered during future repository inspection
```

None of these is validated or implemented by this document. The inventory of what is currently
known about each is in `docs/agent/pf-1f-hr/PF_1F_HR_DEPENDENCY_SOURCE_BASELINE.md`'s "Later PF-1F
dependency inventory" table and in `EXTERNAL_DEPENDENCY_REGISTER.md`.

## Relationship to existing documents

This method does not replace `EXTERNAL_DEPENDENCY_REGISTER.md`'s status-tracking table
(`AVAILABLE` / `INTERFACE_NEEDED` / `DECISION_NEEDED` / `DESIGN_NEEDED`); it is the analysis
process that should be run before a register row's status can responsibly move toward `AVAILABLE`,
and before a register row is closed as "no gap" merely because a system is named as the
authoritative owner.
