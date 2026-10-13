# PF-1F-HR Decision Gate

## Status

Package: PF-1F-HR-E1, corrected under Correction 1 (C1-6, C1-7), Correction 2 (C2-4), Correction 3
(C3-5), Correction 4 (C4-4), the Final Fixture Closure pass, and the Bootstrap / Actor Fixture
Closure pass. Documentation only. This is the single reference point for "is PF-1F-HR ready for
the next step" and "does this particular Plum gap block PF-1A." See ADR-032 and ADR-033.

**Bootstrap / Actor Fixture Closure note.** After the Final Fixture Closure pass, independent
review found the authority fixture still showed two normal-workflow examples
(`cc-004`/`cc-006`) with `recomputed_authorization_required = true` alongside same-person
authorization and `authorization_satisfied = true` - a direct violation of the different-person
preventive invariant - and a pending self-affecting example initiated by an actor the fixture's
own prose said held no authority to initiate anything. Corrected by separating a distinctly-typed,
explicitly exceptional `bootstrap_provenance` record (no authorization/activation evaluation
fields at all) from genuine post-bootstrap `configuration_changes`, and by introducing a second
synthetic actor so a genuine different-person authorization scenario can be shown without
inventing one that contradicts the model. A4 below is re-confirmed accordingly. This pass touched
only the authority fixture and this gate's A4 justification - no other design document, provider
decision, temporal model, SharePoint model, or classification changed, and production Q-10 is
unaffected (the synthetic actors do not resolve it).

**Final Fixture Closure note.** After Correction 4, independent review found the authority
reference fixture (`PF_1A_AUTHORITY_CONFIGURATION_MODEL.md`, "Parameter-file representation") still
had three P2 defects surviving C4-2's field-naming fix: dangling Configuration Change references,
an authorization-time record that was a version snapshot rather than a genuine recomputed verdict,
and a pending self-affecting example naming an undefined role so its risk could not actually be
derived from the fixture's own data. All three are corrected; A4 below is re-confirmed accordingly.
This pass touched only the authority fixture and this gate's A4 justification - no other design
document, provider decision, temporal model, SharePoint model, or classification changed.

**Correction 4 note (C4-4).** Correction 4 fixed remaining current-normative wording that still
read as Plum itself owning structured organization/position data (C4-1, across `AGENTS.md`,
ADR-032, the external-dependency validation method, and `CONTRACT_REGISTRY.md`), aligned the
authority model's illustrative fixture with the activation-time recomputation design it was meant
to demonstrate (C4-2), and separated Q-09 from Q-10 in ADR-032 itself, not only in
`OPEN_QUESTIONS.md` (C4-3). None of these are soundness defects in the design documents themselves
- A1/A4's underlying content was already independently re-verified sound under Correction 3. C4-1
and C4-3 are current-documentation-accuracy corrections (what the architecture says about who
currently supplies HR data, and how Q-09/Q-10 are classified), and C4-2 is a fixture-consistency
correction (the reference example now actually demonstrates the design the surrounding prose
already described correctly). Section A below is re-confirmed, not re-derived from scratch.

**Correction 2 note (C2-4).** Correction 1 introduced the two-tier distinction (design/
implementation readiness versus production authority activation readiness) but still described
"the PF-1A unblocking rule" as one ten-item list that "design/implementation readiness" required in
full, while simultaneously marking two of those ten items (criteria 3 and 5, data population) as
not met - an internal contradiction. This is corrected by defining two genuinely separate,
non-overlapping criteria lists below: **section "A"** gates READY_FOR_PF_1A_DESIGN_IMPLEMENTATION,
and **section "B"** (the two data-population items from the old list, plus governance/production
items not previously listed at all) gates READY_FOR_PRODUCTION_AUTHORITY_ACTIVATION. Section A
never again lists a not-met item as required, and section B is never described as required to
*start* design/implementation.

**Correction 3 note (C3-5).** Independent review found that Correction 2 marked all eight section-A
criteria MET while two of the underlying documents still had unsound design content: the canonical
model's as-of/current derivation omitted `effective_from` (a future row could resolve as "current"
early) and its backdated-correction procedure only handled a single wrong row, not a shared
boundary affecting multiple rows (C3-1); and the authority model trusted a proposal-time risk
classification through to activation instead of recomputing it against current state (C3-2), while
its resolution evidence retained only two of the four authority object/version pairs (C3-3). Marking
A1/A4/A6 "MET" at that time understated real gaps. C3-1 through C3-3 have now corrected the
underlying documents (half-open interval convention and explicit as-of formula; multi-row boundary
correction; fail-closed ambiguity validation; activation-time risk recomputation; four-way
resolution evidence; publication immutability). Section A below is independently re-evaluated
against that corrected content, not mechanically carried forward from Correction 2's wording.

## Purpose

The PF-1F-HR discovery showed a real risk: treating "Plum does not hold a structured organisation model" as
automatically blocking, when in most cases a controlled, provider-neutral interim source
(SharePoint) can safely bridge the gap without stalling unrelated work. This gate makes that
distinction explicit so a future agent does not default to blocking merely because a source
deficiency exists.

## Gate states

```text
READY_FOR_CANONICAL_CONTRACT
    The canonical HR reference model (PF_1F_HR_CANONICAL_REFERENCE_MODEL.md) and the SharePoint
    starter spec (PF_1F_HR_SHAREPOINT_STARTER_SPEC.md) are documented and internally consistent,
    including the canonical-vs-source-binding boundary (C1-1), the explicit stable-identity/
    version-record split with business-time vs. recorded-time semantics (C2-1), and corrected
    SharePoint FK portability (C1-4).
    STATUS: MET as of this package (31 August 2026, corrected under Correction 1 and Correction 2).

READY_FOR_SHAREPOINT_POPULATION
    The seven starter Lists (Employee Reference, Employment Status History, Organisation Units,
    Organisation Unit Versions, Positions, Position Versions, Position Incumbency) have a
    concrete, field-level specification PBL staff can act on without further engineering input.
    STATUS: MET as of this package. PBL staff may begin populating the Lists now.

READY_FOR_PF_1A_DESIGN_IMPLEMENTATION
    See "A. Criteria for design/implementation readiness" below.
    STATUS: MET. All eight criteria are satisfied; none of them requires production data
    population, a confirmed stable Plum Employee ID, a resolved meta-authority bootstrap holder,
    or production integration readiness.

READY_FOR_PRODUCTION_AUTHORITY_ACTIVATION
    See "B. Criteria for production authority activation readiness" below.
    STATUS: NOT MET. This is a materially higher, separate bar and must never be conflated with
    design/implementation readiness.

PARTIAL_PLUM_SOURCE_SHAREPOINT_REQUIRED
    Applies to: Organisation Unit hierarchy, Position Master, Position Incumbency, HR change-feed
    derivation. Plum does not currently supply these; SharePoint is the accepted interim source
    for all of them (ADR-032). This is a source/interface deficiency, not a missing business
    definition, and does not block PF-1A design/implementation readiness.

PLUM_ENHANCEMENT_DESIRABLE_NOT_BLOCKING
    Applies to: stable Employee ID/code reliability, reliable employment-status code, effective
    leaver date, stable Department/Designation codes, manager-by-ID reference, last-modified/
    version value, controlled export/API. All of these are currently `UNKNOWN` /
    `ASSUMED_NEEDS_VALIDATION` per `PF_1F_HR_PLUM_GAP_ANALYSIS_PACKET.md` - not confirmed absent,
    and not confirmed present either. None of them blocks PF-1A design/implementation readiness or
    unrelated CRM/Hiring development. Stable Employee ID reliability specifically is a
    source-capability/reconciliation-quality question, not a business-governance blocker.

BLOCKED_BY_MISSING_BUSINESS_DEFINITION
    Applies only to: the `AUTHORITY_CONFIGURATION_ADMIN` bootstrap/first-holder governance question
    (`PF_1A_AUTHORITY_CONFIGURATION_MODEL.md`, Q-10). This requires a genuine PBL business/
    governance decision that no interim technical source can bridge. It blocks
    READY_FOR_PRODUCTION_AUTHORITY_ACTIVATION specifically - it does not block
    READY_FOR_PF_1A_DESIGN_IMPLEMENTATION, and it does not block unrelated CRM/Hiring work. See
    `docs/continuity/OPEN_QUESTIONS.md` Q-10.
```

## Source/interface deficiency vs. missing business definition

This distinction is the core judgment call this gate exists to make explicit:

```text
Source/interface deficiency
    The business rule/definition is already clear (e.g. "an authority attaches to a position");
    what is missing is a system that currently implements the supporting data structure, or it is
    simply unknown/unverified whether a system has a given capability. A controlled,
    provider-neutral interim source (SharePoint) can bridge a confirmed gap without waiting for the
    ideal source system, and an unverified capability is investigated without being pre-judged as
    absent. -> PARTIAL_PLUM_SOURCE_SHAREPOINT_REQUIRED or PLUM_ENHANCEMENT_DESIRABLE_NOT_BLOCKING.
    Does not block PF-1A design/implementation readiness.

Missing business definition
    PBL has not yet decided the actual policy/governance answer (e.g. "who is authorized to
    become the first AUTHORITY_CONFIGURATION_ADMIN"). No interim technical source can bridge a
    decision that has not been made. -> BLOCKED_BY_MISSING_BUSINESS_DEFINITION. Blocks the
    specific dependent decision (production authority activation), not design/implementation
    readiness and not unrelated work.
```

Do not automatically block PF-1A, or any other package, merely because Plum does not hold a
particular field or model, and do not treat an unverified Plum capability as if it had been confirmed absent
- check first whether the gap is a confirmed absence at the source (bridge it), an unverified
capability (investigate, do not assume), or a genuinely missing business definition (escalate it).

## A. Criteria for design/implementation readiness (corrected, C2-4)

These are the **only** criteria READY_FOR_PF_1A_DESIGN_IMPLEMENTATION requires. None of them
requires production data population, a confirmed stable Plum Employee ID, a resolved
meta-authority bootstrap holder, or production integration readiness - those belong exclusively to
section B below.

```text
A1. Canonical HR-reference contract is sufficiently defined, INCLUDING sound temporal/as-of
    semantics and fail-closed ambiguity behavior.
    MET (re-verified, C3-1) - PF_1F_HR_CANONICAL_REFERENCE_MODEL.md now defines: a single
    half-open interval convention (effective_from inclusive, effective_to exclusive); an explicit
    as-of resolution formula (effective_from <= as_of AND (effective_to IS NULL OR as_of <
    effective_to) AND superseded_at IS NULL) that a future row cannot satisfy before its own
    effective_from, closing the "prospective row looks current early" defect; an ordinary-change
    procedure using matching boundary dates (no gap); a backdated-correction procedure that
    identifies and supersedes every non-superseded row a corrected boundary affects, not only one;
    and a "Fail-closed ambiguity validation" subsection requiring the adapter to detect overlapping,
    contradictory, or missing canonical state and refuse to resolve it rather than guessing. This
    is a documented design ready to implement against, not yet implemented/tested code - see B3.
A2. Stable PBL canonical IDs are defined.
    MET - person_id / org_unit_id / position_id, plus per-version-record identifiers
    (employment_status_history_id, org_unit_version_id, position_version_id, incumbency_id).
    Population of real records against these IDs is a section B concern, not a design gap.
A3. Provider-neutral adapter/composition boundary is defined.
    MET - PF_1F_HR_CANONICAL_REFERENCE_MODEL.md section H; no consumer dependence on SharePoint
    or Plum schemas (sections A-F never reference a provider-specific field).
A4. Authority configuration model is defined sufficiently for implementation, INCLUDING a sound
    preventive self-escalation design that recomputes risk at activation, not only at proposal.
    MET (re-verified, C3-2/C3-3) - PF_1A_AUTHORITY_CONFIGURATION_MODEL.md now defines: the unified
    Configuration Change/Publication record (Role Catalogue, Authority Catalogue, Role -> Authority
    Rules, Person/Position -> Role Assignments, C2-2); an explicit "Activation-time risk
    recomputation" mandatory sequence that recomputes is_self_affecting and
    affects_protected_meta_authority against CURRENT context immediately before activation, never
    trusting the proposal-time booleans (closing the "context changes between proposal and
    activation" defect); and resolution evidence retaining all four (object_id, object_version)
    pairs (role, authority, rule, assignment) plus each one's publishing Configuration Change, with
    publication immutability stated explicitly. RE-VERIFIED, Final Fixture Closure pass (following
    C4-2, which had corrected field naming but left the fixture internally dangling and
    unauthoritative in three places): the illustrative parameter-file fixture is now fully
    self-contained - every `published_by_configuration_change_id` resolves to a Configuration
    Change actually defined in the fixture (`cc-001` through `cc-008`, closing the prior dangling
    `cc-002`..`cc-005` references); `authorization_evaluation` is a genuine recomputed verdict
    (never a version-only snapshot), and the fixture's own explanatory note attributes single-person
    authorization to that recomputed verdict, not to the proposal-time classification (closing the
    unsafe "same person because proposal_time_authorization_required was false" reasoning); and the
    pending self-affecting example (`cc-008`) proposes a role that is actually defined and actually
    linked, via an actually-published Rule, to the protected Authority, so its risk is derivable
    from the fixture's own structured data rather than asserted only in prose. RE-VERIFIED,
    Bootstrap / Actor Fixture Closure pass (following the Final Fixture Closure pass, which
    resolved dangling references but still ran the initial seed through the same schema as normal
    Configuration Changes - producing `cc-004`/`cc-006` examples that showed
    `recomputed_authorization_required = true` together with same-person authorization and
    `authorization_satisfied = true`, exactly the violation the preventive model exists to prevent,
    and a pending example initiated by an actor the fixture said held no authority to initiate
    anything): the fixture now separates a distinctly-typed `bootstrap_provenance` record (no
    `authorization_evaluation`/`activation_evaluation` fields at all, explicitly labelled a
    one-time, exceptional, out-of-band act that does not go through - and does not pretend to have
    gone through - the normal workflow) from `configuration_changes` (now only genuine post-
    bootstrap examples). Two synthetic actors are bootstrap-established: `ILLUSTRATIVE-ADMIN-A`
    (eligible to initiate, shown authorizing only an ordinary change where recomputed
    `authorization_required = false`) and `ILLUSTRATIVE-ADMIN-B` (a different, independently
    eligible holder who has not yet acted on the fixture's one self-affecting, protected-meta-
    authority-affecting, `PENDING` example). No Configuration Change anywhere in the fixture now
    shows `authorization_required = true` together with same-person authorization. This is a
    documented design ready to implement against, not yet implemented/tested code - see B3.
A5. Representative fixtures can be constructed for design/testing purposes.
    MET - synthetic/illustrative fixtures (the parameter-file fragment in
    PF_1A_AUTHORITY_CONFIGURATION_MODEL.md, and representative HR reference records following the
    canonical model's shape) are sufficient to design and test against; real SharePoint population
    is not required to construct them.
A6. Provider failure/staleness behavior is defined sufficiently for design and testing.
    MET - PF_1F_HR_CANONICAL_REFERENCE_MODEL.md "Source-unavailable / staleness behaviour" (a
    canonical, provider-neutral freshness indicator) together with the "Fail-closed ambiguity
    validation" subsection (an internally ambiguous timeline, not only a stale/unavailable feed,
    also fails closed); the exact staleness threshold VALUE remains a deferred policy parameter,
    which does not block design (the mechanism accepts a configurable threshold either way).
A7. No consumer dependence on SharePoint/Plum schemas.
    MET - verified: sections A-F of the canonical model contain no SharePoint or Plum-specific
    field, and PF-1A's own model (PF_1A_AUTHORITY_CONFIGURATION_MODEL.md) references only
    canonical IDs.
A8. No CRM/Hiring-owned duplicate HR master is created.
    MET - confirmed by this package's own quality checks; `RMR-001`'s existing prohibition is
    unchanged and reaffirmed.
```

**READY_FOR_PF_1A_DESIGN_IMPLEMENTATION: all eight criteria MET, independently re-evaluated under
Correction 3 against the corrected temporal, fail-closed and activation-time-recomputation content,
re-confirmed under Correction 4 after aligning the illustrative authority fixture and correcting
residual current-normative Plum-ownership wording and Q-09/Q-10 classification, and finally
re-confirmed once more under the Final Fixture Closure pass once the authority fixture's remaining
dangling references, authorization-time snapshot, and undefined-role pending example were fixed
(none of these changed any design invariant - see the notes above).** PF-1A's own implementation
package (schema design, adapter interface, authority-resolution logic, self-escalation-prevention
workflow) may be scoped and started now. "MET" here means the current
documentation defines each item sufficiently to implement safely against - it does not mean any of
it is implemented or tested yet; B3 below
tracks that separately and explicitly.

## B. Criteria for production authority activation readiness (a stronger, separate gate)

READY_FOR_PRODUCTION_AUTHORITY_ACTIVATION requires all of A1-A8 above **plus** all of the
following, none of which is required to start design/implementation:

```text
B1. Representative reference data is actually populated (SharePoint Lists per
    PF_1F_HR_SHAREPOINT_STARTER_SPEC.md, or an equivalent operational source).
    NOT MET. A bounded data-population task, not a design gap.
B2. Employee/org/position/incumbency data required for real authority scenarios can be supplied
    from that populated data.
    NOT MET, for the same reason as B1 - this is the data half of the same population task.
B3. The preventive self-escalation workflow is implemented and demonstrated (not merely
    documented) - the Configuration Change/Publication model actually enforces independent
    authorization for self-affecting and protected-meta-authority-affecting changes.
    NOT MET. Documented (PF_1A_AUTHORITY_CONFIGURATION_MODEL.md section 5); implementation and
    demonstration are PF-1A build/test work.
B4. The `AUTHORITY_CONFIGURATION_ADMIN` bootstrap/first-holder governance question is resolved.
    NOT MET. Open PBL governance decision (Q-10); see BLOCKED_BY_MISSING_BUSINESS_DEFINITION
    above.
B5. Applicable NFR/security evidence is recorded per
    `docs/agent/architecture/PRODUCTION_READINESS_GATES.md` and
    `docs/agent/architecture/NFR_BASELINE_AND_VERIFICATION.md`, including an accepted staleness
    threshold for the canonical HR/Organisation Reference snapshot/feed.
    NOT MET. Production-gate work, not started.
B6. Recovery/reconciliation evidence exists for the adapter/composition capability's handling of
    source unavailability (Plum, SharePoint, or both).
    NOT MET. Not started.
```

**READY_FOR_PRODUCTION_AUTHORITY_ACTIVATION: NOT MET.** This is expected at this stage of the
programme and does not indicate any defect in the design/implementation-readiness criteria above;
it indicates only that population, implementation, governance and production-evidence work has not
yet happened.

## Affected-files list for this package's traceability reconciliation

The following files carry a minimal current-state correction so they stop implying PF-1A must wait
for a live, sophisticated Plum HR interface, so ADR-032's relationship to ADR-026/`RMR-001` is
explicit, and so NFR/PBL-facing staleness wording is provider-neutral (C2-3):

```text
AGENTS.md
docs/agent/architecture/EXTERNAL_DEPENDENCY_REGISTER.md
docs/agent/architecture/EXTERNAL_DEPENDENCY_SOURCE_GAP_VALIDATION_METHOD.md
docs/agent/architecture/MODULE_DEPENDENCY_AND_DELIVERY_WAVES.md
docs/agent/architecture/MODULE_BOUNDARY_OWNERSHIP_MATRIX.md
docs/agent/architecture/PBL_BUSINESS_REVIEW_GUIDE.md
docs/agent/architecture/NFR_BASELINE_AND_VERIFICATION.md
docs/agent/architecture/CONTRACT_REGISTRY.md
docs/agent/contracts/organization-authority-authorization-contract.md
docs/agent/contracts/resource-master-reference-contract.md
docs/agent/PLAN.md
docs/continuity/NEXT_STEPS.md
docs/continuity/OPEN_QUESTIONS.md
```

None of these files' frozen/approved contract semantics change; only current-state narrative is
reconciled to point to ADR-032/ADR-033 and this gate. `MODULE_BOUNDARY_OWNERSHIP_MATRIX.md` and
`PBL_BUSINESS_REVIEW_GUIDE.md` (corrected, C3-4) now state the current model directly in their own
sentences rather than relying only on an appended cross-reference. The two contract files
(`ORA-001`, `RMR-001`) instead carry a short, explicitly non-substantive cross-reference note
appended after their existing text, which does not alter any existing sentence in either contract -
a deliberate distinction between architecture-guide narrative (corrected directly) and approved
contract text (preserved, with a reconciliation note appended).
