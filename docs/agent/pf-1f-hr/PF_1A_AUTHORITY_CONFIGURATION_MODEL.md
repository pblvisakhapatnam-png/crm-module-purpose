# PF-1A Authority Configuration Model

## Status

Package: PF-1F-HR-E1, corrected under Correction 1 (C1-2), Correction 2 (C2-2), Correction 3
(C3-2, C3-3), Correction 4 (C4-2), the Final Fixture Closure pass, and the Bootstrap / Actor
Fixture Closure pass. Documentation only; no runtime code, migration, API or admin UI implements
this model yet. See `docs/agent/ARCHITECTURE_DECISIONS.md` ADR-033. This document supports the
future PF-1A implementation package and is created alongside the HR-reference boundary documents
because the two boundaries (who a person is vs. what authority they hold) must be established
together before PF-1A begins.

**Bootstrap / Actor Fixture Closure note.** The Final Fixture Closure pass made the fixture
self-contained but still ran its initial seed objects through the same schema as normal
Configuration Changes, which forced two of them (`cc-004`, `cc-006`) to show
`recomputed_authorization_required = true` while still being authorized by their own initiator with
`authorization_satisfied = true` - the exact different-person violation the preventive model exists
to prevent - and its one pending self-affecting example (`cc-008`) was initiated by an actor the
fixture's own prose said held no authority to initiate anything. Both are corrected by introducing
a `bootstrap_provenance` record type, structurally distinct from `configuration_changes`, and two
synthetic actors (`ILLUSTRATIVE-ADMIN-A`, `ILLUSTRATIVE-ADMIN-B`) established by it. See
"Parameter-file representation" below, and its own closure note, for the corrected fixture.

**Final Fixture Closure note.** Correction 4 (C4-2) fixed the fixture's field *naming*
(`proposal_time_*` instead of unqualified booleans) but left three structural defects: dangling
`published_by_configuration_change_id` references (`cc-002` through `cc-005` were cited but never
defined), an authorization-time record (`authorization_context_snapshot`) that only captured a
version snapshot rather than a genuine recomputed verdict, and a pending self-affecting example
that named a role (`role-authority-config-admin-role`) never actually defined anywhere in the
fixture - so its self-affecting nature could not be derived from structured data, only asserted in
prose. All three are corrected in the fixture below: it is now fully self-contained (every
`published_by_configuration_change_id` resolves to a defined Configuration Change, `cc-001`
through `cc-008`); `authorization_context_snapshot` is replaced by `authorization_evaluation`, a
genuine recomputed verdict (`recomputed_is_self_affecting`, `recomputed_affects_protected_meta_
authority`, `recomputed_privilege_increasing`, `recomputed_authorization_required`,
`authorizer_eligible`, `authorizer_is_different_person`, `dependencies_current`,
`authorization_satisfied`) - this evaluation, never a proposal-time field, is cited as the reason
an ordinary change may be authorized single-person; and the pending example (`cc-008`) proposes a
real, fully-defined role linked via a real Rule to the protected Authority, so its risk is
derivable directly from the fixture's own published data (see its `risk_derivation_illustrative_
only` field), not asserted by prose alone. See "Parameter-file representation" below for the
corrected fixture and its own closure note.

**Correction 4 note (C4-2, superseded in naming by the Final Fixture Closure pass above; kept as
historical record of what C4-2 itself fixed).** The illustrative parameter-file fixture still used
unqualified `is_self_affecting`/`affects_protected_meta_authority`/`authorization_required` fields
directly on the Configuration Change record, even though the C3-2 prose above it had already
corrected the design to recompute risk at activation. This let the reference example teach the
unsafe pre-C3-2 pattern despite the surrounding text being correct. Corrected (at the time): every
proposal-time field was renamed `proposal_time_*` and labelled preliminary/audit-only, and a new
`activation_evaluation` object was added. The Final Fixture Closure pass above completes this by
also resolving the dangling references and replacing the authorization-time snapshot with a
genuine recomputed evaluation.

**Correction 3 note.** Two further defects are corrected. (C3-2) `is_self_affecting` and
`affects_protected_meta_authority` were evaluated once at proposal time and then trusted through to
activation; because the authoritative context (who holds what role, current incumbency, published
Role/Authority/Rule/Assignment versions) can change between proposal and activation, this allowed
an originally-ordinary change to activate as if it were still ordinary after it had actually become
self-affecting or protected-meta-authority-affecting. Corrected: risk is now explicitly
system-derived and recomputed atomically immediately before activation ("Activation-time risk
recomputation"), with the proposal-time booleans retained only as preliminary audit information.
(C3-3) The conceptual authority-resolution result retained only `rule_version` and
`assignment_version`, not `role_version`/`authority_version`, so a decision could not prove which
Role or Authority definition was in force independently of the Rule/Assignment referencing it.
Corrected: resolution evidence now retains all four `(object_id, object_version)` pairs plus each
one's publishing Configuration Change, and publication immutability is stated explicitly.

**Correction 1 note.** The original "Self-escalation prevention" text treated the configuration-
change audit trail as the control against self-escalation. Corrected to a preventive invariant:
changes that would increase the initiator's own authority activate only after independent
authorization.

**Correction 2 note (C2-2).** Correction 1's preventive fields (`activation_status`,
`initiated_by_person_id`, `authorized_by_person_id`) were added only to sections 3 and 4 (Role ->
Authority rules, Person/Position -> Role assignments). Sections 1 and 2 (the Role Catalogue and
the Authority Catalogue themselves) had no equivalent mechanism at all - an administrator could
create or edit a Role or an Authority, including one later used as a protected meta-authority,
with no preventive control and no durable version/publication history, because the pattern had
been added ad hoc to two of the four concepts rather than structurally to all four. This is
corrected by introducing one coherent, provider-neutral **Configuration Change / Publication**
record (section 5) that governs proposal, authorization and activation uniformly across all four
configurable concepts, and by replacing the implicit "the string `AUTHORITY_CONFIGURATION_ADMIN` is
special" assumption with an explicit, data-driven `is_protected_meta_authority` classification on
the Authority Catalogue (section 2).

This document does not change `ORA-001` (Organization Authority and Authorization Contract),
which remains `APPROVED` and unedited. It generalizes and spells out in full the configuration
model `ORA-001` already partially demonstrates through its `CREDIT_ASSESSOR`/`CREDIT_APPROVER`
resolution rule.

## Why this exists

Workflow code that checks `if user.role == "SALES_MANAGER"` before allowing a credit decision
bakes an organisational fact into source code. Every reorganisation, delegation, or title change
then requires a code change and a redeploy. The parameter-driven model replaces that with: workflow
code asks "does the current user hold `CREDIT_ASSESSOR` authority for this scope?" and a
configuration-driven resolution layer answers, using data an authorized administrator can change
without touching application code.

## The four configurable concepts, and the fifth record that governs all of them

```text
1. Role Catalogue
2. Authority Catalogue
3. Role -> Authority Rules
4. Person/Position -> Role Assignments

5. Configuration Change / Publication  (governs how 1-4 are proposed, authorized and activated -
                                         see section 5 below; this is what corrects C2-2)
```

### 1. Role Catalogue

Admin-configurable named roles (business-facing labels used to group authorities for assignment
convenience - not the same as the application's coarse login roles like `SALES_MANAGER`).

```text
role_id                stable identity, never reused
role_version            the published version number currently in force for this role_id
role_code
role_name
description
active_flag
effective_from
effective_to
published_by_configuration_change_id   the Configuration Change (section 5) that activated this
                                        version - audit link, not itself a workflow field
```

Illustrative only (not a frozen catalogue): `Credit Assessor`, `Credit Approver`, `Regional
Commercial Approver`. These names must never become hard-coded constants in workflow/application
code; they are configuration rows an administrator can add, rename or retire, and every such
add/rename/retirement is itself a Configuration Change (section 5) - creating or editing a Role is
not a direct, ungoverned write to this table.

### 2. Authority Catalogue

Admin-configurable business authorities/capabilities. Workflow code references only
`authority_code`.

```text
authority_id                stable identity, never reused
authority_version             the published version number currently in force for this
                              authority_id
authority_code
authority_name
description
active_flag
effective_from
effective_to
is_protected_meta_authority   boolean; see "Protected meta-authority classification" below
published_by_configuration_change_id   the Configuration Change (section 5) that activated this
                                        version
```

Illustrative only: `CREDIT_ASSESSMENT`, `CREDIT_LIMIT_APPROVAL`, `COMMERCIAL_DISCOUNT_APPROVAL`,
`MARKET_HIRE_APPROVAL`, `ELIGIBILITY_OVERRIDE`, `AUTHORITY_CONFIGURATION_ADMIN`. This is not
assumed to be the final catalogue. Business workflow code references `authority_code` - never
`role_code`, a designation, a position name, or an employee name.

#### Protected meta-authority classification (corrected, C2-2)

`is_protected_meta_authority` is a **data-driven classification field on the Authority Catalogue
row itself**, not a hard-coded string comparison against the literal text
`AUTHORITY_CONFIGURATION_ADMIN` anywhere in application/workflow code. `AUTHORITY_CONFIGURATION_ADMIN`
is the first, primary example of an authority carrying this flag, but the model does not assume it
is the only one: any authority PBL later designates as governing configuration, security, or other
structurally sensitive capability may also be flagged `is_protected_meta_authority = true`, purely
through configuration data, without a code change. Application/workflow code checks the flag on the
resolved authority, never the authority's code/name string. Setting or clearing this flag on an
authority is itself always a self-affecting-or-worse Configuration Change (section 5) and is
therefore always subject to the mandatory preventive rule below - an administrator cannot quietly
strip protection from `AUTHORITY_CONFIGURATION_ADMIN`, or grant it to a new authority they control,
without independent authorization.

### 3. Role -> Authority Rules

Which role carries which authority, for what scope, subject to what parameters.

```text
rule_id                stable identity, never reused
rule_version            the published version number currently in force for this rule_id
role_id
authority_id
scope_type
scope_id             nullable where global
lower_limit          nullable
upper_limit          nullable
                     (additional threshold/parameter fields as a given authority genuinely requires
                     - do not force every authority into one universal monetary-limit schema)
conditions           nullable, where genuinely required
effective_from
effective_to
active_flag
published_by_configuration_change_id   the Configuration Change (section 5) that activated this
                                        version
```

Different authorities may require different parameter shapes (a monetary threshold for
`CREDIT_LIMIT_APPROVAL`, a scope-only rule with no threshold for `MARKET_HIRE_APPROVAL`, a
percentage-discount threshold for `COMMERCIAL_DISCOUNT_APPROVAL`). The rule schema must accommodate
this without forcing a single universal parameter set; the reference representation below uses an
open `parameters` object for this reason.

### 4. Person/Position -> Role Assignments

```text
assignment_id           stable identity, never reused
assignment_version       the published version number currently in force for this assignment_id
role_id
person_id            nullable
position_id          nullable   (exactly one of person_id / position_id must be supplied)
scope_type           nullable
scope_id             nullable
effective_from
effective_to
active_flag
published_by_configuration_change_id   the Configuration Change (section 5) that activated this
                                        version
```

Assigning to a **position** (rather than a person) means the authority follows whoever currently
occupies that position (per the Position Incumbency dataset in
`PF_1F_HR_CANONICAL_REFERENCE_MODEL.md`), which is appropriate for a seat-based authority (e.g.
"whoever is Regional Manager - South"). Assigning to a **person** is appropriate for a
person-specific delegation or a role not yet tied to a formal position. The implementation must
reject an assignment that supplies both `person_id` and `position_id`, or neither.

Duplicate/conflicting active assignments (the same role, scope and overlapping effective period
assigned twice, or contradictory rules) must be rejected at write time, not silently tolerated.

## 5. Configuration Change / Publication (structural fix for C2-2)

**This single, provider-neutral record type governs proposal, independent authorization and
activation uniformly for all four concepts above.** It replaces the earlier, ad-hoc approach of
adding activation fields directly and inconsistently to individual tables. Creating, editing or
deactivating a Role, an Authority, a Role -> Authority Rule, or a Person/Position -> Role
Assignment is never a direct write to that object's table; it is always proposed as a
Configuration Change, and the object's own row (with its `*_version` and
`published_by_configuration_change_id` fields) is only written/updated once that Configuration
Change reaches `ACTIVE`.

```text
configuration_change_id
configuration_object_type       ROLE | AUTHORITY | ROLE_AUTHORITY_RULE | PERSON_POSITION_ROLE_ASSIGNMENT
configuration_object_id         the stable role_id / authority_id / rule_id / assignment_id being
                                 changed; for a brand-new object this is the identity the object
                                 will receive once activated (generated up front so the change can
                                 be referenced before activation)
change_type                     CREATE | UPDATE | DEACTIVATE
proposed_version                the version number this change publishes if activated
change_payload                  the proposed field values for the object at this version (the
                                 pending content of the row described in sections 1-4)
previous_version_reference      nullable; for UPDATE/DEACTIVATE, the version being superseded

proposal_time_is_self_affecting                boolean, evaluated ONCE at proposal time as
                                                preliminary/audit information only - see
                                                "Activation-time risk recomputation" below; NEVER
                                                trusted as the final answer
proposal_time_affects_protected_meta_authority boolean, evaluated ONCE at proposal time,
                                                preliminary/audit information only, same caveat
proposal_time_authorization_required           boolean derived from the two proposal-time booleans
                                                above at proposal time ONLY - preliminary/audit
                                                information, never itself sufficient to authorize
                                                or activate; see `authorization_required` below for
                                                the value that actually gates authorization/
                                                activation
proposal_context_snapshot        the published Role/Authority/Rule/Assignment versions and the
                                 canonical HR-reference snapshot (person/position/incumbency
                                 versions, per `PF_1F_HR_CANONICAL_REFERENCE_MODEL.md`) that were
                                 current when the proposal-time fields above were computed -
                                 recorded so staleness can be detected before activation, not used
                                 to justify skipping recomputation

authorization_required           boolean, RECOMPUTED (see below) at the moment authorization is
                                 sought/granted, not merely copied from proposal_time_
                                 authorization_required = current is_self_affecting OR current
                                 affects_protected_meta_authority OR otherwise flagged as
                                 privilege-escalating by policy (see "Preventive rule" below)
initiated_by_person_id
initiated_at
authorized_by_person_id          nullable until authorized; must differ from
                                 initiated_by_person_id whenever authorization_required is true
                                 AS RECOMPUTED at the time authorization is granted
authorized_at                     nullable until authorized
authorization_evaluation          the recomputation record produced at the moment authorization is
                                 sought/granted (corrected, FINAL FIXTURE CLOSURE) - null while
                                 authorized_at is null; conceptually:
                                     evaluated_at
                                     context_reference (current published Role/Authority/Rule/
                                         Assignment versions and canonical HR-reference snapshot)
                                     recomputed_is_self_affecting
                                     recomputed_affects_protected_meta_authority
                                     recomputed_privilege_increasing
                                     recomputed_authorization_required
                                     authorizer_eligible
                                     authorizer_is_different_person
                                     dependencies_current
                                     authorization_satisfied
                                 This is what actually determines whether authorization_required
                                 is true and whether an ordinary change may proceed single-person -
                                 never the proposal-time fields. Used at activation to detect drift
                                 between authorization time and activation time (see below).
activation_evaluation              the atomic activation-time recomputation record produced
                                 immediately before activation (see "Activation-time risk
                                 recomputation" below) - null until that check has actually run;
                                 it is never pre-filled from proposal_time_* or authorization-time
                                 values
activation_status                 PENDING | ACTIVE | REJECTED
effective_from                    the business-effective date the published version takes effect
effective_to                       nullable
```

Do not freeze this exact schema unless appropriate; the important structural property is that one
governed record type - not four inconsistent ad-hoc variants - is capable of representing every
case below:

```text
- pending creation of a Role;
- pending edit/deactivation of a Role;
- pending creation/edit/deactivation of an Authority (including setting/clearing
  is_protected_meta_authority);
- pending changes to a Role -> Authority Rule;
- pending changes to a Person/Position -> Role Assignment;
- independent authorization where authorization_required is true;
- activation/publication only after that authorization, or immediately for an ordinary,
  non-escalating change (see "Preventive rule" below).
```

### Preventive rule (unchanged principle, now structurally uniform across all four concepts)

At minimum, independent authorization (`authorized_by_person_id` distinct from
`initiated_by_person_id`) is mandatory before `activation_status` may become `ACTIVE`, for:

```text
- a self-affecting privilege grant, scope increase, or threshold/limit increase, however produced
  (a new Role, a new Authority, a new Rule, or a new Assignment can all be self-affecting);
- any Configuration Change that creates, edits, or deactivates a Role, Authority, Rule or
  Assignment where is_protected_meta_authority applies (directly on the Authority Catalogue row,
  or by resolution through the Rule/Assignment being changed);
- any other change the implementation's own policy classifies as privilege-escalating (the two
  cases above are the mandatory minimum, not an exhaustive list).
```

The initiator can never authorize their own pending change: the system must reject
`authorized_by_person_id == initiated_by_person_id` whenever `authorization_required` is true. If
no independently-authorizing holder of the relevant meta-authority currently exists, the change
remains `PENDING` indefinitely - the system never falls back to self-authorization and never
silently expires a pending change into `ACTIVE`.

**Ordinary administration remains single-person.** For a Configuration Change where
`authorization_required` is false (an ordinary, non-self-affecting, non-protected-meta-authority
edit - for example, an `AUTHORITY_CONFIGURATION_ADMIN` holder assigning an unrelated business role
to a different employee, with no effect on the admin's own authority and no protected authority
involved), `activation_status` may move directly from `PENDING` to `ACTIVE` at the same
administrator's action, recording `initiated_by_person_id == authorized_by_person_id` and
`initiated_at == authorized_at` as evidence that no second party was required for that specific,
non-escalating change. **Do not turn every ordinary configuration edit into a mandatory two-person
process; the preventive rule applies only to the cases listed above.** A rejected change is
recorded as `REJECTED`, not deleted, preserving audit value; audit remains necessary, it is simply
not sufficient on its own, which is why the preventive rule above (not the audit trail) is the
control.

### Activation-time risk recomputation (new, C3-2)

**Risk classification is system-derived, evaluated fresh against current authoritative context; it
is never a trusted, persisted proposal-time flag.** The context a proposal was assessed against -
who currently holds what role, what the current published Role/Authority/Rule/Assignment versions
say, who currently occupies a relevant position - can change between proposal, authorization and
activation. A proposal correctly classified as ordinary at the moment it was raised can become
self-affecting or protected-meta-authority-affecting before it activates (for example: the
initiator is later assigned a role that makes the pending change self-affecting; a position's
incumbent changes; a Role or Authority the pending change references is itself edited). Trusting
the original `proposal_time_is_self_affecting` / `proposal_time_affects_protected_meta_authority`
booleans at activation would let exactly this drift bypass the preventive rule. This closes that
gap.

**Mandatory sequence immediately before `activation_status` may become `ACTIVE`** (this check is
atomic with activation - no window exists between the check and the effect):

```text
1. Load the CURRENT authoritative context relevant to this Configuration Change: the canonical
   person identity, current position/incumbency (PF_1F_HR_CANONICAL_REFERENCE_MODEL.md), the
   currently published Role Catalogue, Authority Catalogue, Role -> Authority Rules and
   Person/Position -> Role Assignments, and the current is_protected_meta_authority
   classification.
2. Recompute is_self_affecting and affects_protected_meta_authority against that current context -
   not against proposal_context_snapshot or authorization_evaluation. These freshly recomputed
   values are the authoritative ones; the proposal-time fields and the earlier authorization_
   evaluation remain on the record only as audit history of what was believed at those earlier
   moments.
3. Recompute authorization_required from the freshly recomputed values (plus any other
   policy-flagged case).
4. If authorization_required is now true:
   a. verify authorized_by_person_id is populated and still differs from initiated_by_person_id;
   b. verify the recorded authorizer still currently holds the meta-authority required to grant
      this specific authorization (an authorizer who has since left, been suspended, or lost the
      relevant authority no longer counts);
   c. if either check fails - including the case where authorization_required flipped from false
      to true after authorization was already granted under the old, lower-risk classification -
      the change is NOT activated. It reverts to (or remains) PENDING and requires fresh,
      independent authorization under the newly-recomputed risk classification.
5. Only if step 4 is satisfied (or authorization_required is false) does the change activate:
   the object's published row (section 1-4 fields, including its new *_version) is written and
   activation_status is set to ACTIVE, atomically with this check - no other write may activate
   the object's new version without having just performed steps 1-4 against current state.
6. Steps 1-5 above are themselves recorded as the Configuration Change's `activation_evaluation`
   (evaluated_at, the current context reference used, the recomputed booleans, whether
   authorization/eligibility/dependency checks were satisfied, and the resulting
   activation_permitted outcome) - see the illustrative fixture below. A Configuration Change with
   `activation_status = ACTIVE` always has a non-null `activation_evaluation` showing
   `activation_permitted = true`; one that is still `PENDING` has `activation_evaluation = null`
   because this sequence has not yet succeeded for it.
```

**Never permitted:** a proposal classified ordinary at proposal time, followed by a context change
that would make it self-affecting or protected-meta-authority-affecting, followed by the same
initiator activating it on the strength of the original, now-stale classification. Step 4c
explicitly exists to prevent this.

**Dependency staleness, without over-specifying runtime mechanics.** `proposal_context_snapshot`
and `authorization_context_snapshot` exist so an implementation can detect *that* material
dependencies changed between stages (by comparing recorded versions to current versions), which is
useful operator/audit information and can drive a user-facing "this proposal's context has changed,
please re-review" signal. The mandatory safety property, however, does not depend on diffing those
snapshots - it depends on step 2 always recomputing against current state rather than ever reading
a stored boolean as final. Do not over-specify the exact staleness-detection mechanism; the
recompute-at-activation invariant above is what a future implementation must guarantee.

### Version/publication history now covers all four concepts (corrected, C2-2)

The earlier version of this document versioned only Role -> Authority Rules and Assignments
(`rule_version` / `assignment_version`) and left the Role Catalogue and Authority Catalogue
themselves unversioned - meaning a change to what a Role or an Authority *means* had no durable
publication history at all. Every one of the four concepts now carries its own `*_version` field
(`role_version`, `authority_version`, `rule_version`, `assignment_version`) plus a
`published_by_configuration_change_id` audit link, all produced only through an activated
Configuration Change. A historical approval decision can therefore identify the exact published
Role, Authority, Rule and Assignment versions - and the Configuration Change that published each -
relevant to that decision, so that changing any of the four today never changes the explanation of
a decision made under a previous configuration.

## Authority resolution (conceptual)

```text
request: authority_code + transaction facts (amount, scope, company/branch, customer/project/
         site, other policy dimensions) + as_of time (normally "now")
  -> resolve active Role -> Authority Rules for authority_code valid as_of, matching scope and
     satisfying threshold/condition parameters against the transaction facts
  -> resolve active Person/Position -> Role Assignments for the matched role(s), valid as_of,
     matching scope (following current Position Incumbency where the assignment is
     position-based)
  -> result: allow/deny, reason, scope, and IMMUTABLE EVIDENCE OF EXACTLY WHAT WAS RESOLVED
     (corrected, C3-3 - all four object/version pairs, not only two):
        role_id, role_version
        authority_id, authority_version
        rule_id, rule_version
        assignment_id, assignment_version
     plus the published_by_configuration_change_id recorded on each of the four rows above, so the
     exact Configuration Change that published each participating version can be identified.
```

**Correction (C3-3).** The result previously retained only `rule_version` and `assignment_version`
(and only the `role_id`/`authority_id` object identities, not their versions), which is
insufficient: `ORA-001` requires that "a historical approval decision retains ... the exact
Role/Authority/Rule/Assignment versions used," and a decision cannot prove which *Role* or
*Authority* definition was in force at decision time from `rule_version`/`assignment_version`
alone - a Role or an Authority can itself be edited (a new `role_version`/`authority_version`)
independently of any Rule or Assignment referencing it. All four `(object_id, object_version)`
pairs above must be retained together as one immutable decision-time snapshot.

Only `ACTIVE` Roles, Authorities, Rules and Assignments (i.e. those whose governing Configuration
Change has `activation_status = ACTIVE`, confirmed via the activation-time recomputation in
"Activation-time risk recomputation" above - never a stale proposal-time flag) participate in
resolution; a `PENDING` Configuration Change of any kind confers no authority. This mirrors
`ORA-001`'s existing "Authorization result" section (allow/deny with authenticated user, applicable
permission, authority assignment/version and reason); this document names the configuration
objects that resolution reads.

### Publication immutability

A published version row (any row written by an activated Configuration Change, per section 5) is
never edited after activation. A later change to the same Role, Authority, Rule or Assignment
always produces a **new** version row, with its own `*_version` number and its own
`published_by_configuration_change_id`; it never overwrites the row an earlier decision already
cited as evidence. Only a still-`PENDING` proposal (not yet activated) is mutable, per the
governance path in section 5. This is what makes the immutable evidence in the "Authority
resolution" result above actually immutable: the specific `(object_id, object_version)` pairs a
decision recorded can be dereferenced at any later time and will return exactly the same published
content they returned at decision time, regardless of how many further Configuration Changes have
since activated for the same objects.

## Protected administration (meta-authority)

Only a user holding an authority flagged `is_protected_meta_authority = true` (the primary
illustrative example is `AUTHORITY_CONFIGURATION_ADMIN`) may initiate or authorize a Configuration
Change against sections 1-4. Administering authority configuration and exercising an ordinary
business authority (e.g. `CREDIT_ASSESSOR`) are separate capabilities; holding one never implicitly
grants the other, consistent with `ORA-001`'s existing rule that `ADMIN` is never an implicit
`CREDIT_ASSESSOR`.

**Two separate concerns - do not conflate them:**

```text
IMPLEMENTATION/DESIGN INVARIANT (section 5, resolved here):
    No unilateral self-escalation. A self-affecting or protected-meta-authority-affecting
    Configuration Change requires a different, independent authorizer before it activates - and
    this now applies structurally to all four configurable concepts, not only to two of them.

BUSINESS GOVERNANCE QUESTION (Q-10, unresolved, not answered here):
    Who initially holds/approves the protected AUTHORITY_CONFIGURATION_ADMIN meta-authority before
    any configuration exists, and how is a later change of that holder itself authorized?
```

The preventive invariant above holds regardless of how Q-10 is eventually answered: whoever PBL
designates as the first `AUTHORITY_CONFIGURATION_ADMIN` still cannot unilaterally grant themselves
a further authority increase, or grant `is_protected_meta_authority` to a new authority they
control, once at least one other independent holder of a protected meta-authority exists; the
residual gap is only the single-holder bootstrap moment itself, which is exactly what Q-10 asks
PBL to resolve (for example, by designating more than one initial holder, or by using an
out-of-band administrative act for the very first assignment, analogous to the DEV-ORCH controlled
qualification pattern already used elsewhere in this repository). This document does not invent
that answer. If the repository later adopts a different protected-administration pattern
elsewhere, PF-1A should reuse it rather than inventing a second one.

## Parameter-file representation (illustrative, non-final)

The following fragment illustrates how the model above could be represented as a versioned,
schema-validated JSON parameter file for the reference implementation, fixtures, or as an
import/export format for a future admin UI. **This is an illustrative example only - it is not the
frozen final authority catalogue, and production storage is not required to be a filesystem file
(see ADR-033).** It is self-contained: every object's provenance reference resolves to an entry
actually defined below, and every Configuration Change's `change_payload` carries enough
structured data to derive, without guessing, who would receive or change authority, which
role/authority/rule/assignment is affected, the scope, and whether protected meta-authority is
impacted.

**Bootstrap / Actor Fixture Closure note.** The prior version of this fixture ran its initial seed
objects through the *same* Configuration Change schema used for normal runtime changes, including
setting `recomputed_authorization_required = true` on some of them while still showing the same
person as both initiator and authorizer with `authorization_satisfied = true` - exactly the
different-person violation the preventive model exists to prevent, and something a genuine
Configuration Change must never show. It also had its one pending self-affecting example initiated
by an actor the fixture's own prose said held no authority to initiate anything. Both are corrected
by cleanly separating two kinds of record:

```text
BOOTSTRAP PROVENANCE (`bootstrap_provenance`, ids boot-001..boot-008)
    Establishes the fixture's initial synthetic state: two illustrative actors already holding the
    protected AUTHORITY_CONFIGURATION_ADMIN role, plus the ordinary Role/Authority/Rule needed to
    demonstrate a non-protected business authority. This is explicitly labelled a one-time,
    exceptional, GOVERNED_OUT_OF_BAND_BOOTSTRAP_ACT - it carries no proposal_time_*, no
    authorization_evaluation, and no activation_evaluation, because it does not go through the
    normal Configuration Change workflow at all (that workflow cannot yet operate before any
    authority exists to operate it). It is illustrative/test-fixture bootstrap only: it does not
    resolve production Q-10, and it is not evidence that any real PBL bootstrap holder has been
    chosen - see "Protected administration" above and `docs/continuity/OPEN_QUESTIONS.md` Q-10.

NORMAL CONFIGURATION CHANGES (`configuration_changes`, ids cc-101, cc-102)
    Everything AFTER bootstrap. Both are initiated by ILLUSTRATIVE-ADMIN-A, who is legitimately
    eligible to initiate because bootstrap already established ADMIN-A as an
    AUTHORITY_CONFIGURATION_ADMIN holder (boot-007) - initiating is never, by itself, what grants
    permission. cc-101 is ordinary (authorization not required, so ADMIN-A may authorize their own
    proposal - this is the only case where same-person authorization is shown, and only because
    the recomputed verdict says independent authorization is not required). cc-102 is self-affecting
    (ADMIN-A proposes broadening their OWN admin assignment's scope) and therefore requires
    independent authorization from a different eligible holder; ILLUSTRATIVE-ADMIN-B (boot-008) is
    shown as currently eligible to grant it, but has not acted, so cc-102 correctly stays PENDING
    with no authorization, no activation evaluation, and nothing published.
```

No normal Configuration Change below shows `recomputed_authorization_required = true` together with
the same person as initiator and authorizer, or `authorization_satisfied = true` without a distinct,
eligible authorizer having actually acted.

```json
{
  "config_snapshot_at": "2026-08-31T00:00:00Z",
  "bootstrap_provenance_disclaimer": "Every entry in bootstrap_provenance below is a one-time, exceptional, GOVERNED_OUT_OF_BAND_BOOTSTRAP_ACT for this ILLUSTRATIVE/TEST FIXTURE ONLY. It establishes synthetic initial actors and configuration so the NORMAL Configuration Change workflow below has something to operate against. It is NOT the normal Configuration Change authorization workflow, it does NOT resolve production Q-10 (who the real PBL bootstrap/protected holders will be), and it is NOT evidence that any real PBL bootstrap holder has been chosen. See 'Protected administration' above and OPEN_QUESTIONS.md Q-10.",
  "bootstrap_provenance": [
    {
      "bootstrap_provenance_id": "boot-001",
      "provenance_type": "SYNTHETIC_BOOTSTRAP_SEED",
      "configuration_object_type": "ROLE",
      "configuration_object_id": "role-credit-assessor",
      "established_payload": {
        "role_code": "CREDIT_ASSESSOR_ROLE",
        "role_name": "Credit Assessor",
        "active_flag": true,
        "effective_from": "2026-01-01"
      },
      "established_at": "2026-01-01T00:00:00Z"
    },
    {
      "bootstrap_provenance_id": "boot-002",
      "provenance_type": "SYNTHETIC_BOOTSTRAP_SEED",
      "configuration_object_type": "ROLE",
      "configuration_object_id": "role-authority-config-admin",
      "established_payload": {
        "role_code": "AUTHORITY_CONFIGURATION_ADMIN_ROLE",
        "role_name": "Authority Configuration Administrator",
        "active_flag": true,
        "effective_from": "2026-01-01"
      },
      "established_at": "2026-01-01T00:00:00Z"
    },
    {
      "bootstrap_provenance_id": "boot-003",
      "provenance_type": "SYNTHETIC_BOOTSTRAP_SEED",
      "configuration_object_type": "AUTHORITY",
      "configuration_object_id": "auth-credit-assessment",
      "established_payload": {
        "authority_code": "CREDIT_ASSESSMENT",
        "authority_name": "Perform Account credit assessment",
        "active_flag": true,
        "is_protected_meta_authority": false,
        "effective_from": "2026-01-01"
      },
      "established_at": "2026-01-01T00:00:00Z"
    },
    {
      "bootstrap_provenance_id": "boot-004",
      "provenance_type": "SYNTHETIC_BOOTSTRAP_SEED",
      "configuration_object_type": "AUTHORITY",
      "configuration_object_id": "auth-authority-config-admin",
      "established_payload": {
        "authority_code": "AUTHORITY_CONFIGURATION_ADMIN",
        "authority_name": "Maintain authority configuration",
        "active_flag": true,
        "is_protected_meta_authority": true,
        "effective_from": "2026-01-01"
      },
      "established_at": "2026-01-01T00:00:00Z",
      "note_illustrative_only": "Defining the protected meta-authority itself has no prior authority to be authorized against - this is precisely why it can only be established through this exceptional bootstrap path, never through the normal Configuration Change workflow."
    },
    {
      "bootstrap_provenance_id": "boot-005",
      "provenance_type": "SYNTHETIC_BOOTSTRAP_SEED",
      "configuration_object_type": "ROLE_AUTHORITY_RULE",
      "configuration_object_id": "rule-001",
      "established_payload": {
        "role_id": "role-credit-assessor",
        "authority_id": "auth-credit-assessment",
        "scope_type": "ORG_UNIT",
        "scope_id": null,
        "parameters": {},
        "effective_from": "2026-01-01"
      },
      "established_at": "2026-01-01T00:00:00Z"
    },
    {
      "bootstrap_provenance_id": "boot-006",
      "provenance_type": "SYNTHETIC_BOOTSTRAP_SEED",
      "configuration_object_type": "ROLE_AUTHORITY_RULE",
      "configuration_object_id": "rule-002",
      "established_payload": {
        "role_id": "role-authority-config-admin",
        "authority_id": "auth-authority-config-admin",
        "scope_type": "GLOBAL",
        "scope_id": null,
        "parameters": {},
        "effective_from": "2026-01-01"
      },
      "established_at": "2026-01-01T00:00:00Z",
      "note_illustrative_only": "This rule is what makes holding role-authority-config-admin equivalent to holding the protected auth-authority-config-admin authority - the link an evaluator follows to derive self-affecting/protected impact for cc-102 below."
    },
    {
      "bootstrap_provenance_id": "boot-007",
      "provenance_type": "SYNTHETIC_BOOTSTRAP_SEED",
      "configuration_object_type": "PERSON_POSITION_ROLE_ASSIGNMENT",
      "configuration_object_id": "assign-A",
      "established_payload": {
        "role_id": "role-authority-config-admin",
        "person_id": "ILLUSTRATIVE-ADMIN-A",
        "position_id": null,
        "scope_type": "ORG_UNIT",
        "scope_id": "BRANCH-WEST",
        "effective_from": "2026-01-01"
      },
      "established_at": "2026-01-01T00:00:00Z",
      "note_illustrative_only": "Bootstrap-seeds ILLUSTRATIVE-ADMIN-A as a currently eligible initiator/authorizer of Configuration Changes, scoped to BRANCH-WEST only. This is what makes ADMIN-A's later initiations (cc-101, cc-102) legitimate - initiating was never itself the source of permission, holding this bootstrap-seeded assignment is."
    },
    {
      "bootstrap_provenance_id": "boot-008",
      "provenance_type": "SYNTHETIC_BOOTSTRAP_SEED",
      "configuration_object_type": "PERSON_POSITION_ROLE_ASSIGNMENT",
      "configuration_object_id": "assign-B",
      "established_payload": {
        "role_id": "role-authority-config-admin",
        "person_id": "ILLUSTRATIVE-ADMIN-B",
        "position_id": null,
        "scope_type": "GLOBAL",
        "scope_id": null,
        "effective_from": "2026-01-01"
      },
      "established_at": "2026-01-01T00:00:00Z",
      "note_illustrative_only": "Bootstrap-seeds a SECOND, different synthetic actor (ILLUSTRATIVE-ADMIN-B) as a currently eligible independent authorizer with GLOBAL scope, specifically so the normal workflow below can demonstrate a genuine different-person authorization without inventing one mid-example. Seeding two independent holders at bootstrap is itself only a test-fixture convenience - it does not answer production Q-10, which is about who the real initial PBL holder(s) will be and how that is governed."
    }
  ],
  "roles": [
    {
      "role_id": "role-credit-assessor",
      "role_version": 1,
      "role_code": "CREDIT_ASSESSOR_ROLE",
      "role_name": "Credit Assessor",
      "active_flag": true,
      "effective_from": "2026-01-01",
      "established_by_bootstrap_provenance_id": "boot-001"
    },
    {
      "role_id": "role-authority-config-admin",
      "role_version": 1,
      "role_code": "AUTHORITY_CONFIGURATION_ADMIN_ROLE",
      "role_name": "Authority Configuration Administrator",
      "active_flag": true,
      "effective_from": "2026-01-01",
      "established_by_bootstrap_provenance_id": "boot-002"
    }
  ],
  "authorities": [
    {
      "authority_id": "auth-credit-assessment",
      "authority_version": 1,
      "authority_code": "CREDIT_ASSESSMENT",
      "authority_name": "Perform Account credit assessment",
      "active_flag": true,
      "is_protected_meta_authority": false,
      "effective_from": "2026-01-01",
      "established_by_bootstrap_provenance_id": "boot-003"
    },
    {
      "authority_id": "auth-authority-config-admin",
      "authority_version": 1,
      "authority_code": "AUTHORITY_CONFIGURATION_ADMIN",
      "authority_name": "Maintain authority configuration",
      "active_flag": true,
      "is_protected_meta_authority": true,
      "effective_from": "2026-01-01",
      "established_by_bootstrap_provenance_id": "boot-004"
    }
  ],
  "role_authority_rules": [
    {
      "rule_id": "rule-001",
      "rule_version": 1,
      "role_id": "role-credit-assessor",
      "authority_id": "auth-credit-assessment",
      "scope_type": "ORG_UNIT",
      "scope_id": null,
      "parameters": {},
      "effective_from": "2026-01-01",
      "active_flag": true,
      "established_by_bootstrap_provenance_id": "boot-005"
    },
    {
      "rule_id": "rule-002",
      "rule_version": 1,
      "role_id": "role-authority-config-admin",
      "authority_id": "auth-authority-config-admin",
      "scope_type": "GLOBAL",
      "scope_id": null,
      "parameters": {},
      "effective_from": "2026-01-01",
      "active_flag": true,
      "established_by_bootstrap_provenance_id": "boot-006"
    }
  ],
  "assignments": [
    {
      "assignment_id": "assign-A",
      "assignment_version": 1,
      "role_id": "role-authority-config-admin",
      "person_id": "ILLUSTRATIVE-ADMIN-A",
      "position_id": null,
      "scope_type": "ORG_UNIT",
      "scope_id": "BRANCH-WEST",
      "effective_from": "2026-01-01",
      "active_flag": true,
      "established_by_bootstrap_provenance_id": "boot-007"
    },
    {
      "assignment_id": "assign-B",
      "assignment_version": 1,
      "role_id": "role-authority-config-admin",
      "person_id": "ILLUSTRATIVE-ADMIN-B",
      "position_id": null,
      "scope_type": "GLOBAL",
      "scope_id": null,
      "effective_from": "2026-01-01",
      "active_flag": true,
      "established_by_bootstrap_provenance_id": "boot-008"
    },
    {
      "assignment_id": "assign-101",
      "assignment_version": 1,
      "role_id": "role-credit-assessor",
      "person_id": null,
      "position_id": "ILLUSTRATIVE-SALES-MANAGER-POSITION",
      "scope_type": "ORG_UNIT",
      "scope_id": null,
      "effective_from": "2026-03-01",
      "active_flag": true,
      "published_by_configuration_change_id": "cc-101",
      "note_illustrative_only": "The only assignment published through the NORMAL Configuration Change workflow in this fixture - see cc-101. assign-A and assign-B above are bootstrap-sourced (established_by_bootstrap_provenance_id), never published_by_configuration_change_id, because no Configuration Change produced them."
    }
  ],
  "configuration_changes": [
    {
      "configuration_change_id": "cc-101",
      "configuration_object_type": "PERSON_POSITION_ROLE_ASSIGNMENT",
      "configuration_object_id": "assign-101",
      "change_type": "CREATE",
      "proposed_version": 1,
      "change_payload": {
        "role_id": "role-credit-assessor",
        "person_id": null,
        "position_id": "ILLUSTRATIVE-SALES-MANAGER-POSITION",
        "scope_type": "ORG_UNIT",
        "scope_id": null,
        "effective_from": "2026-03-01"
      },
      "risk_derivation_illustrative_only": "change_payload.role_id (role-credit-assessor) resolves via rule-001 to auth-credit-assessment, which is not protected (is_protected_meta_authority=false). change_payload.person_id is null (a position assignment); initiated_by_person_id (ILLUSTRATIVE-ADMIN-A) gains nothing from this assignment either way. Ordinary, non-self-affecting, non-protected - derivable directly from published data.",
      "proposal_time_is_self_affecting": false,
      "proposal_time_affects_protected_meta_authority": false,
      "proposal_time_authorization_required": false,
      "proposal_context_snapshot": {
        "note_illustrative_only": "PRELIMINARY/AUDIT ONLY - versions current when the proposal was raised, never trusted at authorization or activation",
        "hr_reference_snapshot_at": "2026-03-01T00:00:00Z",
        "role_catalogue_version_observed": 1,
        "authority_catalogue_version_observed": 1,
        "relevant_rule_versions_observed": ["rule-001@1"],
        "relevant_assignment_versions_observed": []
      },
      "initiated_by_person_id": "ILLUSTRATIVE-ADMIN-A",
      "initiated_at": "2026-03-01T00:00:00Z",
      "authorized_by_person_id": "ILLUSTRATIVE-ADMIN-A",
      "authorized_at": "2026-03-01T00:00:00Z",
      "authorization_evaluation": {
        "note_illustrative_only": "GOVERNING evaluation - this recomputed verdict, not the proposal-time fields above, is why a single person could authorize this change. ADMIN-A is eligible to initiate AND authorize here only because recomputed_authorization_required came back false under current published policy for this specific, non-escalating change - NOT because ADMIN-A is the initiator.",
        "evaluated_at": "2026-03-01T00:00:00Z",
        "context_reference": {
          "hr_reference_snapshot_at": "2026-03-01T00:00:00Z",
          "role_catalogue_version": 1,
          "authority_catalogue_version": 1
        },
        "recomputed_is_self_affecting": false,
        "recomputed_affects_protected_meta_authority": false,
        "recomputed_privilege_increasing": false,
        "recomputed_authorization_required": false,
        "authorizer_eligible": true,
        "authorizer_is_different_person": false,
        "dependencies_current": true,
        "authorization_satisfied": true
      },
      "activation_evaluation": {
        "note_illustrative_only": "Mandatory recomputation immediately before activation, per 'Activation-time risk recomputation' - never skipped, and never reads the proposal-time fields or authorization_evaluation as final",
        "evaluated_at": "2026-03-01T00:00:00Z",
        "current_context_reference": {
          "hr_reference_snapshot_at": "2026-03-01T00:00:00Z",
          "role_catalogue_version": 1,
          "authority_catalogue_version": 1
        },
        "recomputed_is_self_affecting": false,
        "recomputed_affects_protected_meta_authority": false,
        "recomputed_authorization_required": false,
        "authorization_satisfied": true,
        "authorizer_still_eligible": true,
        "dependencies_current": true,
        "activation_permitted": true
      },
      "activation_status": "ACTIVE",
      "effective_from": "2026-03-01",
      "note_illustrative_only": "First NORMAL (post-bootstrap) Configuration Change. ADMIN-A may initiate this only because bootstrap (boot-007) already made them an eligible AUTHORITY_CONFIGURATION_ADMIN holder."
    },
    {
      "configuration_change_id": "cc-102",
      "configuration_object_type": "PERSON_POSITION_ROLE_ASSIGNMENT",
      "configuration_object_id": "assign-A",
      "change_type": "UPDATE",
      "proposed_version": 2,
      "previous_version_reference": 1,
      "change_payload": {
        "scope_type": "GLOBAL",
        "scope_id": null
      },
      "risk_derivation_illustrative_only": "configuration_object_id (assign-A) is ILLUSTRATIVE-ADMIN-A's OWN assignment of role-authority-config-admin (boot-007), currently scoped to ORG_UNIT/BRANCH-WEST. change_payload proposes broadening that same assignment's scope to GLOBAL. role-authority-config-admin resolves via rule-002 to the protected auth-authority-config-admin authority. Therefore: this is initiated_by_person_id (ILLUSTRATIVE-ADMIN-A) proposing to broaden their OWN scope over a protected authority - self-affecting, protected-meta-authority-affecting, and privilege-increasing, all derivable directly from published data plus this change_payload, without asserting it in prose.",
      "proposal_time_is_self_affecting": true,
      "proposal_time_affects_protected_meta_authority": true,
      "proposal_time_authorization_required": true,
      "proposal_context_snapshot": {
        "note_illustrative_only": "PRELIMINARY/AUDIT ONLY - what ILLUSTRATIVE-ADMIN-A's proposal was assessed against at the moment it was raised; never sufficient to authorize or activate by itself",
        "hr_reference_snapshot_at": "2026-04-01T00:00:00Z",
        "role_catalogue_version_observed": 1,
        "authority_catalogue_version_observed": 1,
        "relevant_rule_versions_observed": ["rule-002@1"],
        "relevant_assignment_versions_observed": ["assign-A@1"]
      },
      "initiated_by_person_id": "ILLUSTRATIVE-ADMIN-A",
      "initiated_at": "2026-04-01T00:00:00Z",
      "authorized_by_person_id": null,
      "authorized_at": null,
      "authorization_evaluation": null,
      "activation_evaluation": null,
      "activation_status": "PENDING",
      "effective_from": null,
      "note_illustrative_only": "ADMIN-A is a legitimately eligible INITIATOR (holds role-authority-config-admin per boot-007) - eligibility to initiate is never in question here. What is blocked is self-authorization: the system must reject authorized_by_person_id == initiated_by_person_id for this self-affecting, protected-meta-authority-affecting change. ILLUSTRATIVE-ADMIN-B (boot-008) IS currently eligible to authorize this independently (different person, holds the same protected role at GLOBAL scope), but has not done so. Until ADMIN-B (or another currently-eligible, different, independent holder) actually authorizes it, authorized_by_person_id/authorization_evaluation/activation_evaluation all stay null, activation_status stays PENDING, and assign-A above remains at version 1 - nothing is published. This demonstrates the ordinary case (cc-101) and the blocked case (cc-102) both correctly, with no example anywhere showing a self-affecting or protected-meta-authority-affecting change authorized by its own initiator."
    }
  ]
}
```

## Relationship to existing `ORA-001` catalogue

`ORA-001`'s existing "Initial authority catalogue" table (`CREDIT_ASSESSOR`, `CREDIT_APPROVER`,
`IDENTITY_EXCEPTION_HANDLER`, `FINANCE_CUSTOMER_MASTER_OWNER`, `RISK_APPROVER`, `BILLING_MAKER`,
`BILLING_CHECKER`, `VENDOR_HIRE_APPROVER`, `PROCUREMENT_AUTHORITY`, `FINANCE_AP_CHECKER`) is a
worked example of the Authority Catalogue concept above, already documented in a frozen-adjacent
contract. This document does not replace or duplicate that table; it generalizes the mechanism the
table is an instance of, and adds the `AUTHORITY_CONFIGURATION_ADMIN` meta-authority (and its
`is_protected_meta_authority` classification) that `ORA-001` did not name explicitly.

## Explicit exclusions

- No runtime authority-resolution code is implemented by this document.
- No database schema or migration is created.
- No admin UI is built.
- No final Role/Authority catalogue is frozen; every example above is illustrative.
- The `AUTHORITY_CONFIGURATION_ADMIN` bootstrap/first-holder question is not answered here.
