# PF-1A-E2-A — Business Authority Resolution Contract & Domain Kernel

## 1. Status

**PROPOSED PACKAGE DEFINITION. NOT IMPLEMENTED. NOT INDEPENDENTLY ACCEPTED.**

This document is an architecture/contract-definition artefact produced under the PF-1A delivery
line. It defines *what* PF-1A-E2-A must specify and implement; it does not implement any of it. No
runtime code, database schema, Alembic migration, API route, business event, permission rule or
frontend screen is created, changed or authorized by this document.

```text
Package ID:        PF-1A-E2-A
Package name:      Business Authority Resolution Contract & Domain Kernel
Predecessor:       PF-1A-E1 (Explicit Permission Compatibility Foundation) - COMPLETE, INTEGRATED
Successor:         PF-1A-E2-B (Persisted Published Authority Store & Runtime Wiring)
Later:             PF-1A-E3 (Governed Authority Configuration, Publication and
                   Self-Escalation Prevention)
Definition-time
repository state:  main @ b6e58994ca4486819312457e89adec22ad720495
Document status:   proposed definition. Correction cycles 1, 2 and 3 were applied to the
                   predecessor package after three independent reviews. That package's final
                   independent re-review found F-10 PARTIALLY_RESOLVED and the package's
                   correction/model ceilings were exhausted. A NEW human-authorized work package,
                   PF-1A-E2 F-10 DEFINITION CLOSURE, then completed F-10 through the THREE-CLASS
                   fixture taxonomy of section 9.7 and the total manifest in
                   PF_1A_E2_B_...md section 5.7. A re-review of THAT package found F-10 still
                   PARTIALLY_RESOLVED with three residual blocking findings (F-10.1, F-10.2,
                   F-10.3) and exhausted its ceilings; a further NEW human-authorized package,
                   PF-1A-E2 F-10 FINAL DEFINITION CLOSURE, closed all three - the mandatory
                   pure-kernel fixture for an ABSENT publication_reference_type (section 18,
                   PROVENANCE-ABSENT-TYPE), the deferred A-03 classification (decided in section
                   11.4a: unreachable on every provider, withdrawn, replaced by NS-K-01), and the
                   SCOPE of the A/B1/B2 taxonomy (section 9.7.0: authority-store fixtures only,
                   with non-store scenarios in PF_1A_E2_B_...md section 5.7A). The review of THAT
                   package accepted F-10.1 and F-10.2 and left two material findings against F-10.3
                   itself; a one-time OWNER-AUTHORIZED DIRECT CORRECTION closed both - F-10.3a (the
                   taxonomy's own universe, violated by fixture A-12 and by closure-parity text
                   calling VALID shapes "class A") and F-10.3b (the non-store table was not TOTAL
                   over the orchestration, ordering and evidence obligations the normative text
                   already mandates). See section 1.1.
                   Pending re-review under
                   docs/agent/architecture/INDEPENDENT_IMPLEMENTATION_REVIEW_WORKFLOW.md
```

This definition being written is not acceptance of it. Implementation of PF-1A-E2-A may begin only
after this definition has itself been independently reviewed and integrated under the project
workflow, and after a bounded implementation package has been issued against it.

**Implementation status, added 4 September 2026.** The status block above describes this DEFINITION
at the time it was written, and is preserved as that record. The definition has since been
independently accepted and integrated (PR #14), and a bounded implementation package has been
issued and executed against it. **The implementation exists, is self-reviewed, and is NOT
independently accepted**; it is left uncommitted for independent review. Section 26 records the
implementation outcome, as section 21 requires. **No normative text in sections 2 to 25 was changed
by the implementation package** — no semantic rule, no fail-closed behaviour, no reason code, no
expected outcome and no verification obligation. See
`docs/agent/acceptance/pf-1a-e2-a-business-authority-resolution-contract-and-domain-kernel-acceptance.md`
and `docs/continuity/PF_1A_E2_A_IMPLEMENTATION_HANDOFF_2026-09-04.md`.

### 1.1 Correction record

Five independent reviews have now been applied across three packages. Three returned
`CORRECTION_REQUIRED` against the original definition (cycles 1-3 below); a fourth returned
`CORRECTION_REQUIRED` with F-10 `PARTIALLY_RESOLVED`, closed by the F-10 definition-closure package;
and a fifth returned `CORRECTION_REQUIRED` with F-10 still `PARTIALLY_RESOLVED` and three named
residual findings, closed by the F-10 FINAL definition-closure package. Every finding was accepted
as a **definition defect**; none required a new PBL
business decision. This document is the reconciled result of all of them, not an addendum:
contradictory earlier text has been rewritten rather than annotated, so no reader needs any
correction brief to understand the final contract.

**Cycle 1 — six findings, all now resolved.**

```text
F-01  active_flag semantics were internally contradictory and incomplete.            RESOLVED
      Corrected in sections 8.2, 11.2, 11.5, 14, 16, 18, 19, 22.
F-02  the provider port prefiltered to "effective" rows and could therefore hide     see F-07
      lineage defects. Corrected in sections 9.3, 9.5, 11.3, 11.4, 18, 19, 22 - but
      candidate discovery still interpreted retraction, which cycle 2 reopened.
F-03  candidate path construction, scope composition and cross-path aggregation      see F-08
      were undefined. Corrected in sections 12, 12.4, 15, 15.3, 18, 19, 22 - but the
      aggregation precedence was not TOTAL within one stage, which cycle 2 reopened.
F-04  E2-B authorized runtime composition with synthetic actor/HR providers.         RESOLVED
      Corrected in section 9.6 here and in E2-B sections 5.3, 6, 9, 10, 13, 16.
F-05  a legitimate effective-time gap was wrongly classified as contradictory        see F-09
      lineage. Corrected in sections 11.4, 11.6, 14, 18, 19 - but the closure formula
      made explicit-overlap detection unreachable, which cycle 2 reopened.
F-06  denial and failure evidence were not normatively representable.                RESOLVED
      Corrected in sections 16, 16.2, 16.3, 16.4, 18, 19, 22, 24.
```

**Cycle 2 — three findings, all now resolved.**

```text
F-07  candidate discovery still excluded versions "targeted by a retraction assertion", so a
      malformed or contradictory retraction could suppress the only version carrying the requested
      authority_code or a relevant stable reference, hiding its own defect behind an empty
      candidate set. Separately, published_at / retracted_at were carried as evidence but their
      effect on as-of resolution was undefined.
      Corrected in sections 9.3.1, 9.3.2, 9.5, 11.8 (new), 15.2, 18, 19.E, 22, 24
      (and E2-B sections 5.2, 9, 10.D, 13, 15).

F-08  fail-closed RESULT-level reason selection was not total: two relevant defects with different
      reason codes at the same S0-S9 stage had no deterministic tie-break, so provider order, SQL
      row order, dictionary iteration or traversal order could decide which reason was reported.
      Corrected in sections 12.2, 15.3, 15.5 (new), 16.5, 18, 19.J, 22, 24
      (and E2-B sections 9, 10.N, 13, 15).

F-09  derived closure took min(declared_effective_to, next_start) unconditionally, which silently
      normalized a genuine explicit overlap into two adjacent intervals and made the stated
      overlap failure condition unreachable except for duplicate starts.
      Corrected in sections 11.4, 11.5, 11.6, 18, 19.H, 22, 24
      (and E2-B sections 5.6, 9, 10.F, 13, 15).
```

**Cycle 3 — one finding, partially resolved at the time; closed by the F-10 closure package below.**

```text
F-10  the VERIFICATION contract across the E2-A/E2-B pair was internally impossible. E2-B's
      mandatory structural database constraints reject several malformed shapes at write time,
      while E2-B's parity corpus and acceptance criteria simultaneously required those SAME shapes
      - end <= start, a duplicate (object_id, object_version) "surfaced through the provider", and
      every fail-closed reason code including ASSIGNMENT_TARGET_INVALID - to be seeded in
      PostgreSQL and agreed between the reference and PostgreSQL providers. No conforming
      implementation could satisfy both sides.
      The SEMANTICS in this document did not change. What was missing was an explicit statement of
      WHERE each malformed input is proved when a given provider is structurally incapable of
      holding it.
      Cycle 3 introduced TWO verification lanes in section 9.7 and applied them in sections 11.6,
      18, 19.L2, 22.17a/17b, 24 and 25 (and E2-B sections 5.6, the new 5.7, 9, 10.E/F/N/N3, 13
      and 15). That removed the original impossible parity obligations but left a residual gap,
      recorded immediately below.
```

**F-10 definition closure — a NEW human-authorized work package, not a fourth correction cycle.**

The predecessor package's final independent re-review recorded F-10 as `PARTIALLY_RESOLVED` and
found its correction/model ceilings exhausted. The residual gap it named was precise:

```text
The two-lane contract required EVERY structurally rejected "Lane B" fixture to have an equivalent
malformed input tested directly against the kernel. E2-B section 5.7 assigned several additional
structural shapes to Lane B and pointed at this document's section 18 DOMAIN INVARIANTS block,
which did not define those tests or their expected fail-closed results:

    - a NULL effective_from;
    - a NULL active_flag;
    - a version row whose stable-identity parent row does not exist;
    - a retraction whose object stable-identity parent row does not exist.

For the last two the gap was structural rather than clerical: section 9.3.2 carries object_id on
the LineageMaterial CONTAINER, not on each version or each retraction assertion, so a version or
retraction cannot be provider-neutrally "orphaned" from its object at all. No direct-kernel fixture
could be written without inventing a persistence-specific field or weakening the DTO - both of
which this contract forbids.
```

The closure is a **three-class taxonomy**, defined normatively in the rewritten section 9.7 and
applied throughout:

```text
A    persistable semantic contradiction        -> full provider parity owed
B1   database-rejected structure WITH a meaningful provider-neutral E2-A counterpart
                                               -> DB rejection test + a named, executed E2-A
                                                  direct test at the STATED boundary
                                                  (DTO validation / provider port / kernel)
B2   persistence-only structural invariant with NO meaningful provider-neutral counterpart
                                               -> DB rejection test + explicit exclusion from BOTH
                                                  the parity corpus and the E2-A semantic fixture
                                                  manifests, with a written rationale
```

Two supporting clarifications were required to make the taxonomy total and executable, and both are
now normative rather than implied: section 9.3.2 states what `get_lineage` returns for an object
identity that carries no material (so a "missing stable-identity row" collapses to the already
classified dangling-reference state rather than to an unrepresentable one), and section 9.3.4 states
which `LineageMaterial` fields are DTO-required and which are DTO-optional-and-kernel-validated (so
every B1 fixture is genuinely constructible at the boundary named for it).

This closure changed **no semantic rule** of this document. No fail-closed behaviour was weakened,
no reason code was invented, no reason code was removed, and every rule in sections 8-16 still binds
every provider exactly as before. Sections 9.7, 9.3.2, 9.3.4, 9.3.3, 11.6, 18, 19.L2, 22.17b, 23, 24
and 25 were reconciled here, and E2-B sections 5.6, 5.7, 9, 10, 13, 15 and 16 were reconciled there,
so no contradictory two-lane language survives anywhere in the pair.

**F-10 FINAL definition closure — a further NEW human-authorized work package.**

The re-review of the three-class closure above returned `CORRECTION_REQUIRED` with F-10 recorded as
`PARTIALLY_RESOLVED` and named exactly three residual blocking defects. None of them was a
semantic defect; all three were defects in the **verification contract's totality and
executability**. They are closed here, in the normative body of both documents:

```text
F-10.1  E2-B classified an ABSENT publication_reference_type as B1 and promised a named, executed
        pure-kernel E2-A fixture. Section 18 named an absent publication_reference_id, an absent
        published_at, an absent retracted_at and an UNKNOWN publication_reference_type - but not an
        ABSENT publication_reference_type. One B1 shape therefore had no direct E2-A coverage.
        CLOSED: the fixture now exists, is named, and its expected result is normative. See 9.3.4,
        9.7 class B1 shapes, 11.6, 18 (PROVENANCE-ABSENT-TYPE), 19.L2, 24, 25, and E2-B 5.7's
        B1-09a. The provenance B1 fixtures were also split one-shape-per-ID (B1-08a/B1-08b,
        B1-09a/B1-09b) so no single manifest ID can again cover two shapes of which only one is
        actually tested.

F-10.2  Fixture A-03 (residual ">1 effective version at one as_of") deferred its class, its
        PostgreSQL participation and its expected reason code to implementation time through a
        "RESOLUTION PROCEDURE". A definition that defers a required classification is not total.
        CLOSED, and DECIDED NOW, as branch (b): the residual condition is UNREACHABLE from any
        lineage material, on any provider, by a short proof over the rules this document already
        states (11.4a). A-03 is therefore removed from the authority-store negative-fixture
        manifest, its PostgreSQL parity obligation is withdrawn, and the invariant it was trying to
        exercise is retained as the PURE-KERNEL self-check NS-K-01 with an executable expected
        result. The residual clause of 11.6 is NOT deleted - it remains as a defensive kernel
        invariant, and 11.4a now states normatively that it emits AUTHORITY_VERSION_AMBIGUOUS if it
        is ever reached.

F-10.3  Class A was defined as a PERSISTABLE semantic contradiction whose raw rows PostgreSQL
        stores and returns, yet A-16 (an induced read failure), A-18 (actor/HR provider states),
        A-19 and A-20 (request-side inputs) were all labelled A while their own records recorded
        PostgreSQL storage as "N/A". Their subject is not malformed authority-store state at all,
        so class A's mandatory storage test was not executable for them.
        CLOSED: 9.7 now states normatively that A/B1/B2 classifies ONLY negative fixtures whose
        subject is the published authority-store / read-repository data contract. Everything else
        is a NON-STORE RESOLVER / PROVIDER CONFORMANCE SCENARIO, carried in its own normative table
        (E2-B section 5.7A) with its own seam, executable obligation and parity statement. A-16,
        A-18, A-19 and A-20 were moved there and their IDs retired; every remaining A/B1/B2 entry
        was re-checked against the same test.
```

Retired manifest IDs are **never reused**: `A-03`, `A-16`, `A-18`, `A-19` and `A-20` are retired -
joined by `A-12` in the direct correction below - and each is recorded in E2-B section 5.7 with the
scenario that now carries its obligation, so a later reader tracing an old citation lands on the
replacement rather than on silence.

This closure again changed **no semantic rule**, weakened no fail-closed behaviour, invented no
reason code and removed no reason code. It made the verification contract total and executable, and
it recorded one previously-undecided classification as a decided one.

**Owner-authorized direct correction — F-10.3a and F-10.3b.**

The independent review of the F-10 FINAL definition closure recorded F-10.1 and F-10.2 as
`RESOLVED` and left two material findings against F-10.3 itself. Both were closed under a one-time,
human-authorized direct correction scoped to this document and `PF_1A_E2_B_...md`. As with every
closure above, it changed **no semantic rule**: no fail-closed behaviour was weakened, no reason
code invented or removed, no expected outcome altered, and no obligation dropped. What changed is
where two classes of obligation are recorded and how they are labelled.

```text
F-10.3a  A-12, AND THE CLOSURE-PARITY TEXT, VIOLATED THE TAXONOMY'S OWN DECLARED UNIVERSE.
         9.7.0 admits into A/B1/B2 only fixtures whose subject is a MALFORMED or CONTRADICTORY
         published authority-store state. E2-B fixture A-12 - "the requested authority_code has no
         grant-eligible-by-lineage version at as_of, including an as_of inside a VALID GAP" - was
         labelled class A, a PERSISTABLE SEMANTIC CONTRADICTION. There is no contradiction in it.
         Section 11.5 of this document says in terms that a temporal gap is VALID lineage, every row
         involved is well formed, and what the case actually exercises is the RESOLVER's deliberate
         asymmetry at an as_of. Class A's defining obligation - store the raw CONTRADICTORY state
         and read it back - had nothing to bite on. Separately, E2-B section 9 and criterion 10.N
         described VALID closure shapes (null-end successor closure, explicit adjacency, the valid
         gap, reactivation after it) as "CLASS A", attaching a negative-fixture label to states that
         are not defects at all.
         CLOSED. A-12 is removed from A/B1/B2 and its ID retired; its obligation moves INTACT -
         same seeded VALID rows, same DENY + FAIL_CLOSED / AUTHORITY_CODE_NOT_CONFIGURED, same 16.4
         evidence, same FULL PostgreSQL parity - to non-store scenario NS-RS-01 (E2-B 5.7A). Valid
         stored shapes are recognised as a THIRD named group, the VALID-SHAPE PARITY SCENARIOS
         V-01 to V-12 of E2-B 5.7, carrying no class label and remaining fully parity-owed. Section
         11.5's asymmetry, and the AUTHORITY_CODE_NOT_CONFIGURED code it produces, are UNCHANGED;
         only the place where that behaviour is proved is corrected.

F-10.3b  THE NON-STORE TAXONOMY WAS NOT TOTAL over the resolver-orchestration, ordering and
         evidence scenarios the CURRENT normative text already makes mandatory. Twenty scenarios
         covered the actor, HR, request, port and kernel-invariant seams. But section 18 and E2-B
         section 9 state other obligations in the imperative - the server-captured live as_of and
         the single-clock rule, the prohibition on a caller-selected as_of, a recorded-time cutoff
         or the historical resolver as a live authorization path, the client-supplied person_id
         trust boundary, synthetic-provider production unreachability, the
         provider-supplies-facts-not-judgements rule, multiple legitimate qualifying paths,
         relevant-corrupt state not being masked by a valid path, result-level reason selection, the
         TOTAL defect ORDER cases, and the complete / nonqualifying / partial evidence and
         evidence-ordering cases - and none of those carried a scenario ID or appeared in either
         table.
         CLOSED. E2-B 5.7A now carries FORTY-SIX scenarios across ten seam groups, each with a
         stable ID, a named seam drawn from this document's closed list, its input/condition, BOTH
         store answers, an executable obligation, an expected outcome/status/reason/evidence and an
         explicit parity statement. Section 18 cites every ID at the block that executes it. This
         was an ID-assignment and reconciliation exercise over obligations that already existed;
         no new requirement was created and no speculative scenario was added.
```

The two store answers are now separate, because conflating them is what allowed a scenario that
merely READS valid PostgreSQL rows to be mistaken for one whose malformed SUBJECT is stored state.
"Does the PostgreSQL authority store participate in composing this test?" and "is the malformed
subject under test itself stored authority state?" are different questions with different answers,
and both are recorded per scenario.

**Owner-authorized direct correction — F-10.3-DC-01 and F-10.3-DC-02.**

The independent review of the correction immediately above returned two further blocking findings
against the same F-10.3 work. Both are closed here under a second one-time, human-authorized direct
correction scoped to this document and `PF_1A_E2_B_...md`. Neither creates a business decision,
invents or removes a reason code, changes a class, changes a count, or alters any settled F-10.1,
F-10.2, F-10.3, F-10.3a or F-10.3b outcome.

```text
F-10.3-DC-01  EVALUATOR MISMATCH SEMANTICS CONTRADICTED THEMSELVES ACROSS THE PAIR.
              Section 13 requires a unit/currency/basis mismatch between the stored payload and the
              supplied fact to FAIL CLOSED with EVALUATOR_FACTS_INVALID, and 14.3 lists that code as
              DENY + FAIL_CLOSED. Yet E2-B's VALID-SHAPE scenario V-12 listed "unit/currency
              mismatch" among the shapes producing an ordinary path-level
              EVALUATOR_CONDITION_NOT_SATISFIED, and section 18's EVALUATORS block repeated it in
              the V-12 group. One malformed input therefore carried two contradictory normative
              outcomes, and NS-RQ-02 covered only the ABSENT and WRONG-TYPED request facts.
              CLOSED. The mismatch is REMOVED from V-12 and from the V-12 group of section 18. V-12
              now covers only genuine valid-shape non-satisfaction and states its input
              precondition explicitly - facts present, correctly typed AND
              unit/currency/basis-COMPATIBLE. The mismatch is carried by the EXISTING non-store
              scenario NS-RQ-02, EXTENDED rather than given a new ID, so no count changes:
              PG-DATA = YES, SUBJ = NO, PARITY = YES, outcome DENY, resolution status FAIL_CLOSED,
              reason EVALUATOR_FACTS_INVALID at stage S9, with ordinary 16.4 deterministic failure
              evidence. Section 13 now says in terms that the incompatibility is malformed evaluator
              INPUT and is NEVER reported as EVALUATOR_CONDITION_NOT_SATISFIED.

F-10.3-DC-02  "SUBJ = NO" WAS BEING READ AS "NO MALFORMED ROW MAY EXIST IN THE FIXTURE".
              E2-B's NS-PR-03, NS-AG-03, NS-AG-04 and NS-DO-01..05 are DEFINED to compose
              already-classified class A malformed authority-store rows as ingredients, and
              NS-DO-01..05 must be built from class A defect shapes because B1/B2 shapes cannot be
              seeded at all.
              Other text, here in 9.7.0 and in E2-B 5.7, 5.7A and 9, stated absolutely that no
              malformed row is stored or read in any non-store scenario. Both statements could not
              be true, and as written the prescribed tests were impossible to author.
              CLOSED. Store PARTICIPATION (PG-DATA) and store SUBJECTHOOD (SUBJ) are stated as two
              INDEPENDENT DIMENSIONS, neither inferable from the other. SUBJ = NO means the
              malformed or negative condition UNDER TEST is not authority-store state; it does not
              mean every participating row is valid. Already-classified class A malformed rows may
              participate as CONTROLLED INGREDIENTS where a scenario's defined semantics require
              them, keeping their own class and their own 5.7 obligations and reclassifying nothing.
              Four prohibitions are stated explicitly: the ingredient is never the scenario's
              SUBJECT; no new malformed persisted shape may be introduced without an A/B1/B2
              classification; the non-store taxonomy is never an escape from the 5.7 fixture
              manifest; and the ingredient is never suppressed or normalized against the
              raw-discovery and fail-closed rules. The A/B1/B2 fixture obligations are unchanged.
```

Neither finding changed a class, a count, a reason code, a parity obligation or an expected outcome
beyond the single contradiction each names: A/B1/B2 remain 14/12/3, the valid-shape list remains
V-01 to V-12, and the non-store table remains forty-six scenarios.

## 2. Objective

PF-1A-E2-A establishes the **provider-neutral semantic contract and pure, deterministic domain
kernel** that answers exactly one question:

> At a specified authoritative instant, does this authenticated application actor hold this
> **Business Authority** (identified by `authority_code`) for this business context, under the
> published authority configuration and the canonical HR/organisation state — and what immutable
> evidence proves why?

The answer must be deterministic, must **fail closed** whenever relevant authoritative state cannot
be established, and must carry evidence sufficient to reconstruct the decision later, unchanged,
even after the configuration has since moved on. A denial must be as explainable as an approval.

This is materially different from what PF-1A-E1 answers. E1 answers *"does this transitional
application login role grant this application permission?"*. E2-A answers *"does this canonical
person — possibly through an organisational position — currently hold this business authority
within the applicable scope and parameter limits?"*. The two remain separate layers and neither may
be inferred from the other (section 6).

## 3. Authoritative inputs

Read these before implementing or reviewing this package. Where they conflict with this document,
they win, and the conflict must be raised rather than silently resolved.

```text
docs/agent/ARCHITECTURE_DECISIONS.md            ADR-004, ADR-005, ADR-017 (modular ownership),
                                                 ADR-023 (settled defaults, INR),
                                                 ADR-026 (Employee Master owns positions),
                                                 ADR-028 (PostgreSQL), ADR-030 (platform
                                                 principles), ADR-032 (HR reference source),
                                                 ADR-033 (parameter-driven authority)
docs/agent/contracts/organization-authority-authorization-contract.md      ORA-001 (APPROVED)
docs/agent/contracts/resource-master-reference-contract.md                 RMR-001 (APPROVED)
docs/agent/pf-1f-hr/PF_1F_HR_CANONICAL_REFERENCE_MODEL.md    canonical HR contract, sections A-H
docs/agent/pf-1f-hr/PF_1A_AUTHORITY_CONFIGURATION_MODEL.md   the four configurable concepts, the
                                                              fifth governing record, publication
                                                              immutability, and the rule that only
                                                              ACTIVE Roles/Authorities/Rules/
                                                              Assignments participate in resolution
docs/agent/pf-1f-hr/PF_1F_HR_DECISION_GATE.md                sections A and B (two separate gates)
docs/agent/pf-1a/PF_1A_E1_EXPLICIT_PERMISSION_COMPATIBILITY_FOUNDATION.md
docs/continuity/PF_1A_E1_INTEGRATION_CLOSURE_2026-09-02.md
docs/continuity/OPEN_QUESTIONS.md               Q-05 to Q-10
docs/agent/architecture/CONTRACT_REGISTRY.md    ORA-001/RMR-001 maturity
docs/agent/architecture/INDEPENDENT_IMPLEMENTATION_REVIEW_WORKFLOW.md
docs/agent/architecture/BOUNDED_INDEPENDENT_REVIEW_METHOD.md
docs/agent/architecture/PRODUCTION_READINESS_GATES.md
```

Runtime code that must be read before implementing (the accepted E1 boundary):

```text
backend/app/modules/authorization/contract.py       31 permission codes, 6 role codes, the matrix
backend/app/modules/authorization/dependencies.py   require_permission(...) seam
backend/app/modules/authorization/service.py        has_permission(...)
backend/app/modules/authorization/repository.py
backend/app/modules/authorization/models.py         AuthzPermission, AuthzRolePermission
backend/app/modules/identity/models.py              AppUser, Role, UserRole
backend/app/modules/identity/schemas.py             AuthUser (public_id, username, display_name,
                                                     roles, role_codes) - note: no person_id
backend/app/modules/identity/dependencies.py        get_current_user(), require_roles()
backend/app/models_metadata.py
backend/alembic/versions/20260831_0030_explicit_permission_compatibility_foundation.py
backend/tests/test_authorization_baseline_equivalence.py
backend/tests/test_authorization_compatibility_matrix.py
backend/tests/test_authorization_repository.py
backend/tests/test_authorization_route_migration_guard.py
backend/tests/fixtures/pf_1a_e1_baseline_authorization.py
```

## 4. Terminology — four concepts that must never be collapsed

This is the single most important section of this document. A future agent or reviewer that
conflates any two of these four has already introduced a security defect.

```text
1. APPLICATION / LOGIN ROLE
   The six existing transitional codes in the `role` table: ADMIN, SALES_USER, SALES_MANAGER,
   FINANCE_USER, OPERATIONS_USER, MANAGEMENT_READ_ONLY. Carried on AuthUser.role_codes.
   These are NOT Business Authority Roles. They confer NO business authority, ever, by any path.

2. APPLICATION PERMISSION
   The 31 PF-1A-E1 codes (ACCOUNT_READ, ACCOUNT_TAX_VERIFY, WORK_ORDER_CREATE, ...), held in
   authz_permission and granted to Application/Login Roles through authz_role_permission.
   These are NOT Business Authorities. A permission gates a route; it does not decide a business
   matter such as who may assess credit.

3. BUSINESS AUTHORITY ROLE
   A configurable, business-facing grouping that carries Business Authorities and is assigned to a
   person or a position. It has a stable object identity and immutable, versioned published
   meaning. It is NOT the `role` table, NOT an Application/Login Role, and its code space is
   entirely separate. It is the concept ADR-033 and
   PF_1A_AUTHORITY_CONFIGURATION_MODEL.md call the "Role Catalogue"; this document deliberately
   uses the longer name "Business Authority Role" because the bare word "Role" already means
   `app.modules.identity.models.Role` in this repository's runtime.

4. BUSINESS AUTHORITY
   A named capability identified by `authority_code` (CREDIT_ASSESSOR, CREDIT_APPROVER,
   FINANCE_CUSTOMER_MASTER_OWNER, AUTHORITY_CONFIGURATION_ADMIN, ...). It has a stable object
   identity and immutable, versioned published meaning. Workflow and business consumers ask for a
   Business Authority BY `authority_code` and by nothing else - never by a person's name, an
   employee code, a designation, a job title, an Application/Login Role code, or a Business
   Authority Role name.
```

Two further terms used throughout:

```text
ACTOR          The authenticated application user (AppUser / AuthUser). Identified to this kernel
               only by its application-user public identifier. The actor is never trusted to state
               who it is canonically.
CANONICAL PERSON   The platform-owned `person_id` defined by
               PF_1F_HR_CANONICAL_REFERENCE_MODEL.md. Resolved from the actor through a
               provider-neutral boundary; never supplied by a client.
```

Naming rule for implementation: every new type, table, constant, module and test introduced by
PF-1A-E2-A/E2-B must be named so that concept 3 can never be mistaken for concept 1. Prefer
`BusinessAuthorityRole` / `business_authority_role` over `AuthorityRole` or `Role`.

## 5. Why the E2-A / E2-B / E3 split exists

The split is a **security boundary**, not a convenience.

```text
RESOLVING existing published authority   (who currently holds what)   -> E2-A semantics, E2-B store
CHANGING who has authority               (governed configuration)     -> E3
```

These are distinct security problems with distinct failure modes. Resolution failures leak or
withhold authority for a decision. Configuration failures create authority that should never have
existed — including self-escalation. Coupling them in one package would put a write surface for
published authority configuration into the same package that first learns how to read it, before
the preventive Configuration Change/Publication controls of ADR-033 exist. **Neither E2-A nor E2-B
may therefore expose any production path that creates, edits, deactivates or otherwise mutates
published authority configuration.** The E2 authority store is read-only in production terms; the
only writers are E2-B's own deterministic test fixtures and, later, E3's governed Configuration
Change activation.

The further split between E2-A and E2-B exists for a different reason: the hard problems in E2 are
semantic (temporal resolution, identity boundaries, ambiguity, lineage integrity, immutable
evidence), not SQL mechanics. Independently reviewing the semantics **before** a schema is frozen is
materially cheaper than discovering a semantic defect after a migration exists. E2-A therefore has
no persistence and no migration at all.

Do not collapse E2-A, E2-B and E3 merely because one implementation session could plausibly do more
than one of them.

### 5.1 Ownership of semantics versus ownership of facts

This division is normative and is the basis of finding F-02's correction:

```text
E2-A OWNS SEMANTICS
    what "effective" means; what "grant-eligible" means; how lineage closure is derived; what a
    lineage contradiction is; how scopes compose; how paths aggregate; every reason code; every
    fail-closed rule; the evidence contract.

E2-B (and any other provider) OWNS FACTS ONLY
    it supplies complete, faithful, deterministically ordered lineage material and candidate
    identity sets. It may store lineage facts and return them. It must NOT re-derive, duplicate,
    approximate or weaken any semantic rule above, and must NOT prefilter in a way that could hide
    a defect the kernel is required to detect.
```

A provider that implements a second copy of the effectiveness/closure/contradiction rules is a
blocking defect even if its answers happen to agree, because the two copies will drift.

One consequence of that division needed an explicit statement and now has one: because semantics are
provider-neutral while a concrete store's *structural capability* is not, section 9.7 defines the
**three verification classes** (A, B1, B2) that determine **where** each malformed input is proved.
A store may be unable to hold a shape; it may never answer differently about one it can hold. And a
store's structural constraint may protect a purely representational invariant that has no
provider-neutral malformed counterpart at all — which is a real category (B2), not a licence to
ignore a semantic defect.

## 6. Compatibility boundary with PF-1A-E1 (immutable)

PF-1A-E1 is complete and integrated (implementation commit
`d0b54d34347d33cdbcff1b3622befb317e8a5b32`, integration commit
`10cc2e49c2bc57cd85374abc31cb23a602fcb641`). Its accepted, independently reconfirmed facts are:

```text
31 application permissions
6 transitional Application/Login Roles
exactly 110 role-permission grants
exactly 76 permission-protected route method/path entries
exactly 11 authenticated-only exceptions
no privilege widening or narrowing versus the protected baseline
no implicit universal ADMIN bypass
ACCOUNT_TAX_VERIFY remains FINANCE_USER-only
unknown / unmapped / inactive authorization inputs fail closed
```

PF-1A-E2-A (and E2-B) **must not**:

```text
- add any Business Authority code to backend/app/modules/authorization/contract.py;
- add, remove, rename, widen or narrow any E1 application permission or any of the 110 grants;
- add, remove or reinterpret any of the six transitional Application/Login Roles;
- introduce an implicit ADMIN bypass anywhere, for permissions or for business authority;
- derive, infer or default a Business Authority from an Application/Login Role code;
- treat an Application/Login Role as a Business Authority Role, or map one onto the other in code;
- reintroduce require_roles(...) into any route module;
- weaken, relax, delete or skip any assertion in
  backend/tests/test_authorization_route_migration_guard.py or any other E1 test;
- replace, wrap, bypass or weaken require_permission(...).
```

`ORA-001`'s statement that `SALES_MANAGER` is the *initial/default mapping* for `CREDIT_ASSESSOR`
is a statement about **configuration data**, not about code. It is satisfied by a
Person/Position → Business Authority Role assignment that an administrator can change, never by a
code path that reads `AuthUser.role_codes` and concludes a business authority. If an
implementation finds itself importing an E1 role constant into the authority kernel, that is a
defect.

The intended future consumer pattern, to be implemented by a later package and **not** by E2:

```text
route / service action
   -> require_permission(APPLICATION_PERMISSION_CODE)      # PF-1A-E1, unchanged
   AND
   -> resolve_current_authority(actor, AUTHORITY_CODE, business_context)   # PF-1A-E2
```

The two gates retain distinct meanings and neither substitutes for the other.

**Do not copy historical test-count totals into acceptance criteria.** The recorded E1 closure
figures (guard file 99/99, focused authorization suite 117/117, full backend regression 382/382,
Alembic head `20260831_0030`) are the state at E1 integration. Adding E2-A tests will raise the
full-suite total legitimately. The invariant to preserve is *every existing E1 test still passes,
unmodified, and the compatibility facts above are unchanged* — not a frozen number.

## 7. HR / organisation ownership boundary

```text
CRM / Hiring / PF-1A / Authorization
        |
        v
PROVIDER-NEUTRAL CANONICAL HR CONTRACT      (PF_1F_HR_CANONICAL_REFERENCE_MODEL.md sections A-F, H)
        |
        v
HR-reference adapter / composition layer    (owns section G source bindings and all reconciliation)
        |
   Plum (basic facts)    SharePoint (Phase-1 interim structured reference)
        |
   later: NEW_SHARED_PLATFORM HR / Organisation Reference Master
```

Rules binding on E2-A:

- PF-1A **does not** own, create, cache authoritatively, or maintain an Employee, Organisation Unit,
  Position or Incumbency master. `RMR-001`'s prohibition on a competing master is unchanged.
- PF-1A **never** sees a SharePoint List Item ID, a SharePoint column name, a Plum field/table name,
  a raw provider timestamp, a Source Binding record, a `provider_code`, or an employee name used as
  identity. Only canonical identifiers and canonical DTOs cross the boundary.
- PF-1A **never** performs Plum/SharePoint comparison or canonical-event derivation. That is
  adapter/composition work (canonical model section E, "Ownership of derivation").
- Freshness reaches PF-1A only as the canonical, provider-neutral indicator (`canonical_snapshot_at`)
  plus an explicit unavailable/stale result. The exact staleness threshold **value** remains a
  deferred policy parameter; the kernel accepts it as configuration and fails closed when the
  supplied canonical state is missing, stale or ambiguous.
- `READY_FOR_PF_1A_DESIGN_IMPLEMENTATION` is **MET** (`PF_1F_HR_DECISION_GATE.md` section A).
  `READY_FOR_PRODUCTION_AUTHORITY_ACTIVATION` is **NOT MET** (section B) and is a different, higher
  gate. Nothing in E2-A design or implementation implies, advances or claims section B.
- Synthetic/reference HR providers are explicitly sufficient for E2-A design and deterministic
  testing (criterion A5). Real SharePoint population (B1/B2) is not required and must not be
  attempted here. Section 9.6 governs where those synthetic providers may exist.
- The absence or unverified status of Plum Position/Incumbency structures, and the unverified stable
  Plum Employee ID (Q-09), do **not** block this package. Q-09 is a source-capability/reconciliation
  question, not a missing business definition.

### 7.1 Recorded reconciliation: the actor → canonical person link

`ORA-001`'s "Employee Master input" section already lists **"employee public ID and application-user
link"** as an Employee Master input to ORA. The current runtime has no such link: `AppUser` carries
`id`, `public_id`, `username`, `display_name`, `password_hash`, `is_active` and timestamps, and
`AuthUser` carries `public_id`, `username`, `display_name`, `roles`, `role_codes`. Neither carries a
`person_id`. Separately, `PF_1F_HR_CANONICAL_REFERENCE_MODEL.md` sections A1/A2 and the section H
adapter contract do not currently expose an operation returning the canonical person for a given
application user.

**This is an engineering contract seam, not a new PBL business decision.** ORA-001 already assigns
ownership of the link to the Employee Master capability; what is missing is only its expression in
the canonical adapter surface and in runtime. E2-A therefore defines a provider-neutral
actor→person resolution port (section 9.1) that PF-1A depends on, whose Phase-1 implementation is
synthetic/reference and test-only (section 9.6), and whose eventual authoritative implementation
belongs to the HR-reference capability under a later authorized package.

Recorded follow-up, **not** performed by this package and **not** a blocker: a future PF-1F-HR
documentation pass should adopt an equivalent operation into
`PF_1F_HR_CANONICAL_REFERENCE_MODEL.md` section H so the canonical contract states it directly.
E2-A must not edit that document, `ORA-001` or `RMR-001`.

**Recommended design (engineering discretion, documented):** do **not** add `person_id` to
`AppUser`, `AuthUser` or the JWT. Keep the link behind the HR-reference boundary. Reasons: the
link's authoritative owner is Employee Master, not Identity; a column on `AppUser` would become a
second, drifting copy of an HR fact; and a claim in a token would be a client-influenced identity
input. If a future package proves a persisted local link is unavoidable for performance, it must be
justified, reviewed and recorded as a cache with explicit freshness and fail-closed semantics —
never as the authoritative link.

## 8. Domain objects and identity

E2-A defines four configurable business-authority object families, each with a **stable object
identity** distinct from its **immutable published version identity**. These correspond one-to-one
to the four concepts in `PF_1A_AUTHORITY_CONFIGURATION_MODEL.md` sections 1-4.

### 8.1 The four families

```text
BusinessAuthorityRole
    business_authority_role_id          stable, immutable, never reused
    business_authority_role_version     immutable published version identity
    role_code, role_name, description   published business meaning

BusinessAuthority
    business_authority_id               stable, immutable, never reused
    business_authority_version          immutable published version identity
    authority_code                      the code consumers request
    authority_name, description
    is_protected_meta_authority         explicit data-driven classification field (ADR-033);
                                        NEVER a hard-coded comparison against a literal code string

BusinessAuthorityRule                   (Business Authority Role -> Business Authority)
    business_authority_rule_id          stable
    business_authority_rule_version     immutable published version identity
    business_authority_role_id          STABLE reference (never a version reference)
    business_authority_id               STABLE reference (never a version reference)
    scope_type, scope_id                see section 12
    parameter_evaluator_type, parameter_payload    see section 13

BusinessAuthorityAssignment             (Person/Position -> Business Authority Role)
    business_authority_assignment_id    stable
    business_authority_assignment_version  immutable published version identity
    business_authority_role_id          STABLE reference
    person_id      XOR   position_id    exactly one is present; both or neither is invalid
    scope_type, scope_id
```

Every published version additionally carries:

```text
effective_from                 inclusive, timezone-aware
declared_effective_to          nullable, exclusive, immutable once published (see section 11)
active_flag                    IMMUTABLE published business meaning (see 8.2)
publication_reference_type     BOOTSTRAP_PROVENANCE | CONFIGURATION_CHANGE
publication_reference_id
published_at
corrects_object_version        nullable; set only on a correcting version (section 11.6)
```

### 8.2 `active_flag` — immutable published value, not temporal effectiveness (F-01)

This was the first candidate's most serious internal contradiction and is now settled normatively.

```text
active_flag is an IMMUTABLE VALUE ON A PUBLISHED OBJECT VERSION.

It is part of that version's published business meaning. It is decided when the version is
published and never changes thereafter, for any reason, by any path (invariant I-2).

active_flag is NOT temporal effectiveness. It is NOT derived from effective_from /
declared_effective_to / lineage closure. There is no "current projection" that computes it.
Deactivating an object means PUBLISHING A NEW VERSION whose active_flag is false; it never means
editing an existing version's flag, and it never means letting a version's interval lapse.
```

Three independent conditions must all hold before any version of any of the four families may
contribute to a grant. They are evaluated in this order and each is separately reportable:

```text
GRANT-ELIGIBLE(V, as_of) :=
    (1) LINEAGE VALID      the object's complete lineage is well formed and non-contradictory,
                           and exactly one version is effective at as_of        (section 11.3-11.5)
  AND (2) EFFECTIVE        V is that one effective version                      (section 11.2)
  AND (3) ACTIVE           V.active_flag == true                                (this section)
```

Consequences, applied **identically** to Business Authority Role, Business Authority, Rule and
Assignment:

```text
- An inactive version still participates in LINEAGE and in CLOSURE derivation. Publishing an
  inactive version is exactly how an object is deactivated without a successor, and that version
  legitimately closes its predecessor. Excluding inactive versions from lineage would silently
  re-open a deactivated predecessor and is a blocking defect.
- An unambiguously inactive EFFECTIVE version is NOT corruption and NEVER fails closed. It is a
  deliberate, known configuration state, and it produces deterministic NONQUALIFICATION evidence
  (section 16.3) with a family-specific reason code (section 14.1 / 14.2).
- For the specifically requested Business Authority, an inactive effective version short-circuits
  the whole resolution to DENY + RESOLVED / AUTHORITY_NOT_ACTIVE (section 15.3).
- Missing, ambiguous or contradictory state for the REQUESTED Business Authority remains fail
  closed (AUTHORITY_CODE_NOT_CONFIGURED / AUTHORITY_VERSION_AMBIGUOUS /
  AUTHORITY_LINEAGE_CONTRADICTORY). Inactivity and unresolvability are different answers and must
  never be merged.
```

This is consistent with `PF_1A_AUTHORITY_CONFIGURATION_MODEL.md`: only ACTIVE Roles, Authorities,
Rules and Assignments participate in resolution.

### 8.3 Invariants

```text
I-1  A stable object identity is never reused and never itself versioned.
I-2  A published version is immutable. Its content - including active_flag, effective_from,
     declared_effective_to, provenance and published_at - never changes after publication, for any
     reason, including correction.
I-3  (object_id, object_version) is unique within an object family and dereferences forever to
     exactly the same content - including for a version later retracted or corrected.
I-4  An assignment version has exactly one of person_id / position_id. Neither and both are invalid
     and fail closed; they are never silently coerced.
I-5  A rule/assignment references a Business Authority Role or Business Authority by STABLE
     identity, never by version. That referenced object must itself be grant-eligible at the
     evaluation instant for the path to qualify; a reference to a stable identity with no lineage
     material at all is DANGLING and fails closed (section 11.6).
I-6  A version's declared_effective_to, when present, must be strictly greater than its
     effective_from. A malformed interval fails closed; it is never repaired.
I-7  Publication provenance must be present and well formed on every published version and every
     retraction. A missing, unknown or internally inconsistent provenance fails closed.
I-8  active_flag is a published value, never a derived projection (section 8.2).
```

## 9. Provider ports (provider-neutral, no implementation of any real provider)

E2-A defines ports (protocols/interfaces) plus **reference/synthetic implementations for
deterministic testing only** (section 9.6). It implements no real provider, no SharePoint client, no
Plum client and no database.

### 9.1 Actor → canonical person port

```text
resolve_actor_person(actor_user_public_id, as_of) -> ActorPersonReference | fail-closed outcome

ActorPersonReference:
    actor_user_public_id            the authenticated application user's public identifier
    person_id                        canonical, platform-owned
    canonical_snapshot_at            canonical freshness indicator
    reference_evidence               a canonical, provider-neutral reference to the link record
```

Rules:

```text
- The input is ALWAYS the authenticated actor's own application-user public identifier, taken from
  the server-side authenticated context. A client-supplied person_id, employee code, username or
  display name is NEVER accepted as the identity being authorized.
- No mapping           -> fail closed, ACTOR_PERSON_MAPPING_MISSING.
- More than one mapping-> fail closed, ACTOR_PERSON_MAPPING_AMBIGUOUS. Never pick one.
- Port unavailable / snapshot older than the configured staleness threshold
                       -> fail closed, HR_REFERENCE_UNAVAILABLE / HR_REFERENCE_STALE.
- Port not bound in this composition
                       -> fail closed, ACTOR_PERSON_PROVIDER_NOT_CONFIGURED (section 9.6).
- The port never returns a provider identifier, a provider name, or a raw provider timestamp.
```

### 9.2 Canonical HR reference port

Only the operations authority resolution actually needs, expressed against
`PF_1F_HR_CANONICAL_REFERENCE_MODEL.md` sections A-D:

```text
get_employment_state(person_id, as_of)   -> employment status effective at as_of (A2)
get_position(position_id, as_of)          -> Position Version effective at as_of (C2)
get_incumbency(position_id, as_of)        -> Position Incumbency effective at as_of (D)
get_org_unit(org_unit_id, as_of)           -> Organisation Unit Version effective at as_of (B2)
```

Every response carries `canonical_snapshot_at`. Every operation may return an explicit
`UNAVAILABLE`, `STALE`, `MISSING` or `AMBIGUOUS` outcome, each of which fails closed. An unbound
port fails closed with `HR_REFERENCE_PROVIDER_NOT_CONFIGURED`. `get_org_unit` is required only where
scope evaluation genuinely needs organisation relationships (section 12).

### 9.3 Authority configuration port — complete lineage material, not prefiltered rows (F-02)

The first candidate exposed `list_effective_*` operations. That was a blocking defect: a provider
answering "the effective rows" must itself decide what *effective* means, and can therefore hide
duplicate effective versions, interval overlap, broken supersession, contradictory
correction/retraction assertions and invalid provenance — exactly the defects the kernel is
*required* to detect. The port is redefined as **candidate discovery plus complete lineage
material**.

#### 9.3.1 Candidate discovery from RAW published lineage facts (identity only, superset) (F-07)

Discovery operates on **raw immutable published lineage facts**. It does not interpret them.

```text
find_business_authority_ids_by_code(authority_code)
        -> the stable business_authority_id of EVERY Business Authority for which ANY RAW published
           version/assertion carries this authority_code - INCLUDING a version that is targeted by
           a retraction assertion, inactive, future-dated, superseded or otherwise apparently
           disqualified.

find_rule_ids_for_authority(business_authority_id)
        -> the stable business_authority_rule_id of EVERY Rule for which ANY RAW published
           version/assertion carries this stable business_authority_id as its reference, under the
           same "including retracted and otherwise apparently disqualified" rule.

find_assignment_ids_for_role(business_authority_role_id)
        -> the stable business_authority_assignment_id of EVERY Assignment for which ANY RAW
           published version/assertion carries this stable business_authority_role_id as its
           reference, under the same rule.
```

**The discovery boundary, normatively (F-07).** E2-A owns whether a lineage fact is valid,
retracted, superseded, effective, active or otherwise relevant *after validation*. A provider — in
SQL, in a repository, or anywhere else — must not decide any of those questions in order to answer a
discovery call.

```text
- Discovery returns STABLE IDENTITIES ONLY. It never returns a version.
- Discovery may use structurally trustworthy storage keys and index columns needed to LOCATE the raw
  facts: the object family, the stable identity columns, the authority_code column and the stable
  reference columns named above.
- Discovery MUST NOT exclude a candidate because a RETRACTION assertion, a CORRECTION assertion, an
  active_flag value, a business-effective interval, an evaluator outcome, a scope value, a "latest
  version" notion, a provenance value, or any other apparent semantic disqualification seems to rule
  it out. Every one of those is a semantic judgement reserved to the kernel, and every one of them
  can ITSELF be the defect the kernel is required to detect.
- Consequence, stated so it cannot be missed: for requested Business Authority discovery, ANY raw
  published Business Authority version/assertion carrying the requested authority_code is sufficient
  to discover that stable object, EVEN IF that fact is targeted by a retraction assertion. For graph
  expansion / reference discovery, ANY raw immutable published version/assertion carrying the
  relevant stable reference is sufficient to discover the referenced stable object, under the same
  rule.
- Discovery is therefore deliberately a SUPERSET, and being a superset is a correctness requirement
  rather than a performance concession: an object whose code or reference appears on any published
  fact must reach the kernel with its complete lineage (9.3.2) before anything about it is excluded.
- If raw discovery yields a stable object whose lineage turns out to be malformed or contradictory,
  the normal relevance rules (15.2) and fail-closed rules (11.6, 15.3) apply to it. A provider may
  NOT convert that defect into "no candidate" by prefiltering it away, and a kernel may NOT convert
  it into an ordinary denial.
- Retraction and correction assertions are NOT discovery filters. They are lineage facts, returned
  by get_lineage (9.3.2), because they are required INPUTS to validating the discovered object's
  complete relevant lineage - including the validity of the retraction assertion itself.
- An empty result means "no raw published fact carries this code/reference at all" and is a
  legitimate, resolvable answer. A read failure is NOT an empty result; see 9.3.3.
```

**Conformance obligation.** E2-A's own conformance suite, and E2-B's PostgreSQL parity suite, must
each prove that malformed or contradictory retraction assertions **cannot hide** a requested-code
version or a reference-bearing version. Concretely: seed a state whose only version carrying the
requested `authority_code` (and, separately, whose only version carrying a relevant stable
reference) is targeted by an invalid retraction — dangling, duplicated, or otherwise contradictory
under 11.6 — and assert the object is still discovered, its lineage still reaches the kernel, and
the resolution fails closed with the lineage defect's own reason code rather than reporting an
absent candidate. See section 18 and E2-B section 9.

These retraction shapes are deliberately **class A** (section 9.7): every individual row involved is
structurally valid, so a relational store must be able to hold them and the obligation above is
genuinely dischargeable on both providers. No structural constraint may be introduced that would
make them unseedable — E2-B section 5.6 accordingly forbids a retraction-uniqueness constraint and a
retraction foreign key to a specific version row.

#### 9.3.2 Lineage material (complete, per stable object)

```text
get_lineage(object_family, object_id) -> LineageMaterial

LineageMaterial:
    object_family                  BUSINESS_AUTHORITY_ROLE | BUSINESS_AUTHORITY |
                                   BUSINESS_AUTHORITY_RULE | BUSINESS_AUTHORITY_ASSIGNMENT
    object_id                      the stable identity
    versions[]                     EVERY published version of this object, retracted or not:
        object_version
        effective_from
        declared_effective_to      nullable
        active_flag
        corrects_object_version    nullable
        publication_reference_type
        publication_reference_id
        published_at
        payload                    the family-specific published business meaning (8.1)
    retraction_assertions[]        EVERY append-only retraction assertion for this object:
        retraction_id
        object_version             the version asserted to have been recorded in error
        retracted_at
        publication_reference_type
        publication_reference_id
    completeness                   COMPLETE | UNAVAILABLE     (never "partial")

get_published_version(object_family, object_id, object_version)
        -> the immutable content of exactly that version, forever, regardless of retraction or
           correction. Dereference is ALWAYS available; retraction affects RESOLUTION only.
```

```text
- "Every version" means every version, including future-dated versions, versions the provider
  believes are superseded, inactive versions, and retracted versions. The kernel needs all of them
  to derive closure (11.4), to detect duplicate effective starts, explicit overlap, dangling
  retractions and unretracted correction targets (11.6), and to establish that a valid gap is a gap
  rather than corruption (11.5).
- Because discovery is raw (9.3.1), get_lineage is the point at which the kernel first learns that a
  discovered object's only code-bearing or reference-bearing version is retracted, and whether that
  retraction is itself valid. Returning the retraction assertions is therefore mandatory, not
  optional detail: without them the kernel cannot distinguish a correctly retracted version from a
  malformed retraction attempting to suppress one.
- published_at and retracted_at are returned as immutable recorded-time provenance evidence and as
  validation inputs (11.8). They are NOT a second business-effective clock, and the provider must not
  use them to filter anything.
- A provider that cannot return the complete set MUST return completeness = UNAVAILABLE rather than
  a truncated list. A truncated list presented as complete is a blocking defect.
- The provider applies NO interpretation: it does not compute closure, does not decide which
  version is effective, does not exclude retracted or inactive versions, and does not rank them.
- OBJECT IDENTITIES THAT CARRY NO MATERIAL. get_lineage(object_family, object_id) for an identity
  the provider holds nothing for returns LineageMaterial with completeness = COMPLETE, an EMPTY
  versions[] and an EMPTY retraction_assertions[]. It does NOT raise, does NOT return UNAVAILABLE
  and does NOT invent a "no such object" signal. "The provider holds nothing for this identity" is
  a complete, truthful answer, and the kernel classifies it (AUTHORITY_REFERENCE_DANGLING, 11.5).
- Consequently there is NO provider-neutral notion of a "stable identity row" that exists
  independently of the material carried under it. A store MAY represent stable identity as a
  separate physical row; that is a persistence representation choice (E2-B 5.1), and whether such a
  row exists is invisible at this boundary by design. See 9.7 class B2.
```

#### 9.3.3 Ordering, interpretation and error propagation

```text
ORDERING
    The provider returns versions ordered by (effective_from ASC, object_version ASC) and
    retraction assertions ordered by (object_version ASC, retraction_id ASC), so results are
    reproducible. The KERNEL nevertheless re-sorts canonically and must not depend on the
    provider's order; a deterministic-ordering test shuffles provider output and asserts the result
    is unchanged (section 18).

INTERPRETATION
    All interpretation belongs to the kernel (section 5.1). The provider contributes facts only.

ERROR PROPAGATION
    - completeness = UNAVAILABLE, a raised provider error, a timeout, or any partial/degraded
      result  -> DENY + FAIL_CLOSED, AUTHORITY_CONFIGURATION_UNAVAILABLE.
    - ILL-FORMED MATERIAL: material that cannot be constructed at all because a DTO-REQUIRED field
      (9.3.4) is absent or of the wrong type is likewise DENY + FAIL_CLOSED,
      AUTHORITY_CONFIGURATION_UNAVAILABLE. A provider incapable of producing a well-formed version
      record has not supplied facts; it has failed. No new reason code is introduced for this, and
      no placeholder value is substituted for the missing field.
    - This is NEVER degraded to "no candidates found" and NEVER degraded to DENY + RESOLVED.
    - A discovery call that succeeds and returns an empty set IS a resolvable answer and is not an
      error. So is COMPLETE material with an empty versions[] (9.3.2).
    - An internally contradictory provider result whose fields are individually well formed - for
      example a versions[] list containing two entries with the same object_version, or a version
      carrying declared_effective_to <= effective_from - is NOT an ill-formed-material case. It
      reaches the kernel and fails closed under section 11.6, not silently.

READ-ONLY
    The port defines no create/update/deactivate/publish/delete operation, and E2-B implements
    none.
```

#### 9.3.4 DTO well-formedness versus kernel-validated content (F-10)

The three-class taxonomy of section 9.7 depends on being able to say precisely **at which boundary**
a malformed input is rejected. That is only answerable if the material DTO's own required/optional
shape is part of the contract rather than an implementation accident. It is therefore fixed here.

```text
DTO-REQUIRED  (absence or wrong type is ILL-FORMED MATERIAL, rejected at the DTO/port boundary and
               surfaced as AUTHORITY_CONFIGURATION_UNAVAILABLE per 9.3.3)
    LineageMaterial:      object_family, object_id, versions[], retraction_assertions[],
                          completeness
    version:              object_version, effective_from, active_flag, payload
    retraction assertion: retraction_id, object_version

    Rationale: these are the constituents WITHOUT WHICH THE RECORD IS NOT A PUBLISHED VERSION (or
    not a retraction assertion) at all, and this document defines no semantic classification for
    their absence. Inventing a reason code for "a version with no effective_from" would be
    inventing a semantic answer to a well-formedness question - precisely what 9.7 forbids.

DTO-OPTIONAL, VALIDATED BY THE KERNEL  (present-but-absent/unknown values are legitimate inputs the
               kernel must CLASSIFY, not values the DTO may reject)
    version:              declared_effective_to, corrects_object_version,
                          publication_reference_type, publication_reference_id, published_at
    retraction assertion: retracted_at, publication_reference_type, publication_reference_id
    assignment payload:   person_id, position_id      (BOTH optional at the DTO; the XOR is a
                          SEMANTIC rule the kernel enforces at S7 - see I-4 and
                          ASSIGNMENT_TARGET_INVALID)

    Rationale: this document ALREADY assigns each of these a semantic classification - absent or
    unknown provenance is PUBLICATION_PROVENANCE_INVALID (11.6, 11.7, 11.8.3); neither-or-both
    assignment targets is ASSIGNMENT_TARGET_INVALID (I-4, 14.3); a malformed declared interval is
    AUTHORITY_LINEAGE_CONTRADICTORY (I-6, 11.4). A DTO that rejected any of them would make the
    kernel rule it already owns permanently unreachable and untestable.
```

Two binding consequences:

```text
- publication_reference_type is carried as an OPEN, OPTIONAL value that the kernel validates against
  the two defined values (11.7). It must NOT be modelled as a closed language-level enum, and it
  must NOT be modelled as a required field, because BOTH an UNKNOWN type and an ABSENT type are
  states the kernel is required to classify as PUBLICATION_PROVENANCE_INVALID. These are two
  DISTINCT constructible shapes and each carries its own mandatory direct E2-A fixture (section 18;
  E2-B fixtures B1-09a and B1-10). A DTO or reference provider that defaults a missing
  publication_reference_type to BOOTSTRAP_PROVENANCE, or that refuses to construct material without
  it, destroys the B1-09a coverage and is a blocking defect.
- The reference/synthetic provider and every DTO used by it must be constructible into every
  DTO-OPTIONAL malformed shape above. A convenience validator that "helpfully" enforces the XOR,
  provenance presence, enum membership or interval sanity at construction time silently destroys
  the direct E2-A malformed-input coverage class B1 depends on, and is a blocking defect (section
  18, section 22.17b).
```

### 9.4 Port usage rule for the kernel

The kernel obtains lineage material **once per stable object per resolution** and evaluates every
condition from that material. It must not re-query for a narrower answer, and must not accept any
provider-supplied claim about effectiveness, activity, closure or validity.

### 9.5 What a provider may and may not store

Recorded here because it binds E2-B (F-02):

```text
MAY   store lineage facts exactly as published, including effective_from, declared_effective_to,
      active_flag, corrects_object_version, provenance and retraction assertions; index them;
      order them; return them.

MAY   narrow candidate discovery by the structurally trustworthy storage keys / index columns named
      in 9.3.1 - object family, stable identity, authority_code, stable reference - and by nothing
      else.

MAY NOT  filter to "the effective row"; exclude retracted, inactive, superseded or future versions
      FROM DISCOVERY OR FROM LINEAGE; treat a retraction, correction, active_flag, effective
      interval, evaluator outcome, scope value or provenance value as a discovery predicate;
      compute or store a derived asserted_effective_to and return it as fact; deduplicate;
      tie-break; select a "latest"; use published_at / retracted_at as a filter; or otherwise apply
      any rule from section 11.
```

The single sentence a provider implementer should remember: **locating a fact is permitted;
judging a fact is not.**

### 9.6 Reference/synthetic implementations are TEST-ONLY (F-04)

E2-A ships in-memory reference implementations of 9.1-9.3 driven by declarative synthetic fixtures.

```text
- They are test/reference artefacts ONLY. They exist to make the kernel's semantics deterministically
  provable without a database, a real HR system or a real identity link.
- They must not be importable from, or reachable through, any production runtime path. E2-A must
  include a test proving this (mirroring the TE-1 precedent that the smoke-data harness is
  unreachable from any public API route).
- No production composition may bind them. Until a later authorized package supplies AUTHORITATIVE
  actor-person and HR/organisation providers, a production composition must either (a) refuse to
  compose at all, so no resolver object exists, or (b) if a resolver object exists, deterministically
  return DENY + FAIL_CLOSED with ACTOR_PERSON_PROVIDER_NOT_CONFIGURED /
  HR_REFERENCE_PROVIDER_NOT_CONFIGURED on every call. Silent substitution of a synthetic provider is
  a blocking defect.
- No E2 document, handoff or acceptance record may describe E2 as delivering a production-callable
  business-authority resolver while those dependencies are unmet.
```

### 9.7 Provider structural capability and the THREE verification classes (F-10)

Sections 9.3-9.6 define what a provider must **supply**. This section settles a different question,
which the third independent review found unanswered and the fourth found only partly answered:
**where a given malformed input is PROVED to fail closed**, when a particular provider is
structurally incapable of expressing it at all.

The core rule, stated once:

```text
E2-A defines PROVIDER-NEUTRAL SEMANTIC VALIDITY and fail-closed classification. That definition is
absolute and binds EVERY provider, present and future.

A concrete provider MAY be structurally incapable of representing some malformed inputs. A
relational store's unique key, XOR CHECK, NOT NULL, enum domain or foreign key rejects such a row
before any resolution can occur. That is a property of THAT STORE, not a change to these semantics
and not permission for any provider to answer differently.

Therefore: a provider's conformance/parity corpus may contain only the defect shapes that provider
is INTENTIONALLY CAPABLE of storing and returning. Every other defect shape is proved DIRECTLY
against E2-A, at the exact boundary that owns it, WHENEVER a provider-neutral counterpart exists at
all. Exclusion from one provider's parity corpus is a VERIFICATION-PLACEMENT decision, never a
semantic exemption.

And - the point the fourth review made, which the earlier two-lane wording could not express - a
structural constraint may protect a PURELY REPRESENTATIONAL invariant for which NO provider-neutral
counterpart exists, because the provider-neutral contract does not model the thing the constraint
protects. That is a real, bounded third category. It is not a place to put a semantic defect that
has simply not been written a test yet.
```

#### 9.7.0 Scope of the A / B1 / B2 taxonomy — normative (F-10.3, corrected by F-10.3a)

The three classes below are a statement about **what a store can and cannot hold when the state is
malformed**. That question is only meaningful for a fixture whose subject is a malformed stored
authority state. Applying the classes anywhere else produced two blocking findings, one in each
direction, and both are closed here:

- applying them to a fixture with **no stored subject at all** produced the fourth review's third
  finding: several fixtures were labelled class A while recording their own PostgreSQL storability
  as "N/A", which made class A's mandatory storage test unexecutable for them;
- applying them to a fixture whose stored subject is **entirely valid** produced F-10.3a: fixture
  A-12 recorded an honest storability of YES, and still could not discharge class A's obligation,
  because that obligation is to store a CONTRADICTION and there was none to store. Its rows are
  valid, 11.5 says so, and what it exercises is the resolver.

```text
THE A / B1 / B2 TAXONOMY CLASSIFIES ONLY NEGATIVE FIXTURES WHOSE SUBJECT IS A MALFORMED OR
CONTRADICTORY STATE OF THE PUBLISHED AUTHORITY-STORE / READ-REPOSITORY DATA CONTRACT.

Concretely, a fixture belongs in A / B1 / B2 if and only if its subject is a raw published
authority-configuration shape - a version record, a retraction assertion, a stable-identity
reference, or a stored field on one of those - that this document requires the kernel to REJECT AS
INVALID, and that a store either does or does not hold.

ENTRY TEST, applied before any class is assigned. BOTH questions must be YES:
    (i)  Is the item's SUBJECT a MALFORMED or CONTRADICTORY published authority-store state - one a
         store could, in principle, be asked to hold and return through get_lineage / discovery
         (9.3.1, 9.3.2), and which this document requires the kernel to reject as invalid?
    (ii) Does provider-neutral E2-A meaningfully represent that malformed AUTHORITY STATE (as
         opposed to representing a provider failure, an HR/actor fact, a request input, an
         orchestration or ordering rule, or an evidence rule)?

    BOTH YES    -> classify A, B1 or B2 by the rules below, and answer questions (2)-(7).
    (i) = NO because the stored state under test is VALID
                -> it is a VALID-SHAPE PARITY SCENARIO (E2-B 5.7, V-01 to V-12) when its subject is
                   that stored state, or a NON-STORE scenario (below) when its subject is a seam.
                   Either way it carries NO class label, is NOT a negative fixture, and is STILL
                   fully parity-owed.
    (ii) = NO   -> the fixture is OUT OF SCOPE of this taxonomy. It is a NON-STORE RESOLVER /
                   PROVIDER CONFORMANCE SCENARIO and belongs in the separate normative table
                   (E2-B section 5.7A), with its own seam, its own executable obligation and its own
                   parity statement. It carries NO class label, and "N/A" is never written into a
                   class-A/B1/B2 storability column.

A FAIL-CLOSED OUTCOME DOES NOT BY ITSELF MAKE AN ITEM A NEGATIVE FIXTURE. The withdrawn A-12 is the
worked example: valid rows, valid lineage, and a correct DENY + FAIL_CLOSED /
AUTHORITY_CODE_NOT_CONFIGURED, because 11.5 treats an unestablished REQUESTED authority as an
unknown question rather than an absent grant. The outcome is the kernel's answer, not the data's
defect.

STORE PARTICIPATION IS NOT STORE SUBJECTHOOD. These are two INDEPENDENT DIMENSIONS: no value of one
constrains the value of the other, and neither may be inferred from the other. STORE PARTICIPATION
(the 5.7A PG-DATA column) asks whether authority-store rows must be stored and read for the scenario
to reach its condition at all. STORE SUBJECTHOOD (the SUBJ column) asks whether the MALFORMED OR
NEGATIVE CONDITION THE SCENARIO IS TESTING is itself authority-store state. A test may legitimately
read stored authority rows while exercising a malformed actor provider, HR provider, request, clock,
orchestration, ordering or evidence condition. That does NOT make the scenario A/B1/B2. The two
facts are recorded in two separate columns of the 5.7A table, and question (4) below exists so
neither can be inferred from the other.

SUBJ = NO THEREFORE MEANS "THE MALFORMED THING UNDER TEST IS NOT A STORED ROW". It does NOT mean
"every authority-store row in the fixture is valid". An ALREADY-CLASSIFIED malformed authority-store
row MAY participate as a CONTROLLED TEST INGREDIENT wherever a scenario's own defined semantics
require one - E2-B's NS-PR-03, NS-AG-03, NS-AG-04 and NS-DO-01..05 are the defined cases. Such an
ingredient retains its OWN A/B1/B2 classification and discharges its own storability, reason-code
and parity obligations in E2-B 5.7; composing it does NOT convert the enclosing resolver, provider
or orchestration scenario into an A/B1/B2 one, and does not double-count the stored shape.

WHAT REMAINS PROHIBITED IN A NON-STORE SCENARIO, exactly four things: (1) treating the malformed
store ingredient as the scenario's actual non-store SUBJECT; (2) introducing a NEW malformed
persisted shape that carries no A/B1/B2 classification; (3) using the non-store taxonomy as an
escape hatch from the authority-store fixture manifest of E2-B 5.7; and (4) suppressing or
normalizing the malformed ingredient contrary to the raw-discovery rules of 9.3.1 and the
fail-closed rules of 11.6 and 15.5.

A NON-STORE SCENARIO IS NOT LESS OBLIGATORY, AND NEITHER IS A VALID-SHAPE ONE. Moving a scenario out
of A / B1 / B2 removes a MALFORMED-STATE STORAGE obligation that was never executable for it; it
removes no fail-closed rule, no expected reason code, no evidence obligation and no provider-parity
obligation that genuinely applies. Where two compositions must agree about a non-store failure, that
parity requirement is stated in the 5.7A table itself, naming the providers involved; the V-list
scenarios stay in the parity corpus in full.
```

The seams a non-store scenario may sit on are exactly the interfaces this document already defines —
actor→person mapping/provider validity (9.1), HR provider availability/freshness/ambiguity (9.2),
the authority configuration port's own read/transport failure, material well-formedness and
fact-fidelity (9.3.1, 9.3.3, 9.5), provider reachability and composition (9.6),
request/scope/evaluator input (12, 13), resolver orchestration, the resolution clock and the two
entry points (10, 11.1, 11.5, 11.8), aggregation, relevance and the total defect order (15), the
evidence contract (16), and pure-kernel invariants (11, 15.5). **No new provider surface may be
invented in order to classify a scenario**; if a scenario does not sit on a seam this document
already defines, that is a contract gap to raise, not a licence to add a seam.

**The non-store table must be TOTAL over CURRENT mandatory obligations (F-10.3b).** Every scenario
this document or `PF_1A_E2_B_...md` already states as a mandatory conformance or acceptance
obligation, and whose malformed or negative subject is not stored authority state, carries a stable
scenario ID in that table. That is a completeness requirement over what is ALREADY required — not a
licence to invent defensive scenarios nobody asked for, and not a route to convert an optional
completeness improvement into a new normative requirement. Section 18 cites each ID at the block
that executes it, so the two documents can be checked against each other mechanically.

#### 9.7.1 The three classes

Every **malformed authority-store** negative fixture — one that has passed BOTH questions of the
9.7.0 entry test — is assigned to **exactly one of three classes**. A valid-shape scenario and a
non-store scenario are assigned to none of them:

```text
A    PERSISTABLE SEMANTIC CONTRADICTION
     the store can hold every row; the composed authoritative state is semantically invalid.
     -> FULL provider parity owed.

B1   DATABASE-REJECTED STRUCTURE, WITH a meaningful provider-neutral E2-A counterpart
     the store rejects the write; the equivalent malformed authority state IS expressible at a
     provider-neutral E2-A boundary using only fields this contract already defines.
     -> store proves the REJECTION; E2-A proves the FAIL-CLOSED RESPONSE at the NAMED boundary;
        excluded from that store's parity corpus only.

B2   PERSISTENCE-ONLY STRUCTURAL INVARIANT, with NO meaningful provider-neutral counterpart
     the store rejects the write; the invariant protects the store's own representation, and after
     persistence decoding there is no DISTINCT malformed state the provider-neutral contract can
     express.
     -> store proves the REJECTION; excluded from the parity corpus AND from E2-A's semantic
        fixture/parity manifests; a written rationale is mandatory.
```

#### Class A — persistable semantic-contradiction parity

A defect belongs in class A when **every involved row satisfies the provider's structural shape
constraints, but the complete authoritative lineage is semantically invalid under this document.**

```text
REQUIRED VERIFICATION - all three
    1. the provider stores the raw contradictory state with NO normalization and NO semantic
       suppression (9.5, and E2-B 5.6);
    2. the read repository returns the raw relevant facts (9.3.2);
    3. the provider-backed resolution and the reference/synthetic-provider resolution receive FULL
       E2-A parity: the same outcome, the same resolution_status, the same result_level_reason, the
       same evidence and the same deterministic ordering (15.5, 16.5).
    The shape belongs in that provider's FULL parity corpus.

CLASS A SHAPES  (subject to the concrete store's actual schema; E2-B 5.7 is binding for the
PostgreSQL store)
    - explicit cross-version overlap, where each individual row is structurally valid (11.4);
    - duplicate temporal starts for one stable object, where (stable_object_id, effective_from) is
      deliberately NOT a structural identity uniqueness constraint;
    - structurally valid but malformed or duplicated RETRACTION semantics (11.6);
    - structurally valid but malformed CORRECTION / supersession semantics - a corrects_object_version
      target that does not exist, or one that exists but is not retracted (11.6);
    - contradictory cross-record lineage/provenance relationships requiring multi-row semantic
      analysis, including every impossible recorded-timestamp relationship of 11.8.3;
    - a reference to a stable identity that carries no lineage material
      (AUTHORITY_REFERENCE_DANGLING, 11.5, and see the B2 note on what this absorbs);
    - every other cross-row semantic contradiction this document requires the kernel to detect.

DO NOT move a defect into structural rejection merely to avoid E2-A classification. A structural
constraint MUST NOT be introduced in order to pre-empt a class A shape. In particular, do NOT add a
database uniqueness constraint on (stable_object_id, effective_from) merely to reject duplicate
temporal starts: this contract requires duplicate-start classification and parity. Structural
uniqueness for an IMMUTABLE IDENTITY/VERSION KEY is a different thing and may remain mandatory
(class B1 below).
```

#### Class B1 — structural rejection WITH a provider-neutral counterpart

A defect belongs in class B1 when **both** of the following hold:

```text
- the store intentionally REJECTS the persisted shape through a structural key / CHECK / XOR /
  NOT NULL / closed-domain / single-row constraint; AND
- the equivalent malformed authority state IS meaningfully representable at a provider-neutral E2-A
  input/boundary, USING ONLY the fields section 9.3.2 and 9.3.4 already define - without inventing a
  persistence-specific column and without weakening the DTO.
```

```text
REQUIRED VERIFICATION - all four, none optional
    1. an E2-B database/migration/model test proves the PostgreSQL REJECTION (the write fails,
       naming the constraint that rejected it);
    2. an EXPLICIT, EXECUTABLE E2-A test - a synthetic/reference-provider fixture, or an E2-A
       boundary/DTO fixture - represents the equivalent malformed provider-neutral state;
    3. the expected E2-A fail-closed outcome, reason code and evidence for that state are NORMATIVE
       (stated in section 18 and in the manifest, not left to the implementer to choose);
    4. the fixture is EXCLUDED from that store's provider-parity corpus, because PostgreSQL cannot
       return a row its schema forbids storing.

NAME THE BOUNDARY PRECISELY. Requirement 2 must state WHICH E2-A boundary rejects the state, and the
test must exercise THAT boundary:
    DTO / PORT WELL-FORMEDNESS   the material cannot be constructed because a DTO-REQUIRED field
                                 (9.3.4) is absent or ill-typed. Expected result:
                                 DENY + FAIL_CLOSED, AUTHORITY_CONFIGURATION_UNAVAILABLE (9.3.3).
                                 Say so explicitly; do NOT call this a kernel fixture.
    PURE KERNEL                  the material is well formed and reaches the kernel, which
                                 classifies it under sections 11.4 / 11.6 / 12.2. Expected result:
                                 the specific fail-closed reason code named in the manifest.

Requirement 4 is NOT a semantic exemption, and requirements 2-3 are what keep it honest: E2-A must
still fail closed if ANY other provider supplies such malformed data. A future provider with a
weaker schema inherits the same semantic obligation, and its own corpus reclassifies the shape into
class A automatically.

CLASS B1 SHAPES  (subject to the concrete store's actual schema; E2-B 5.7 is binding for PostgreSQL)
    - immutable identity/version uniqueness violations - two version records sharing one
      object_version within one object's material. PROVIDER-NEUTRAL COUNTERPART: versions[] is a
      LIST, so two entries with the same object_version are trivially constructible (9.3.3, 11.6).
      Boundary: PURE KERNEL. Expected: AUTHORITY_LINEAGE_CONTRADICTORY;
    - assignment person/position XOR violations - NEITHER or BOTH targets. PROVIDER-NEUTRAL
      COUNTERPART: person_id and position_id are both DTO-OPTIONAL on the assignment payload (9.3.4),
      exactly so this state is constructible. Boundary: PURE KERNEL, stage S7. Expected:
      ASSIGNMENT_TARGET_INVALID;
    - single-row interval-shape violations - declared_effective_to <= effective_from (I-6), covering
      both end < start and the empty end == start. PROVIDER-NEUTRAL COUNTERPART: both fields exist on
      the version DTO and declared_effective_to is DTO-OPTIONAL and kernel-validated. Boundary: PURE
      KERNEL, the 11.4 NONSENSICAL DECLARED INTERVAL pre-check. Expected:
      AUTHORITY_LINEAGE_CONTRADICTORY;
    - missing or unknown PROVENANCE, which is FOUR distinct constructible shapes, each owed its own
      named fixture rather than being grouped under one manifest entry: an absent published_at on a
      version, or an absent retracted_at on a retraction assertion; an absent
      publication_reference_type; an absent publication_reference_id; and a
      publication_reference_type outside the two defined values. PROVIDER-NEUTRAL COUNTERPART: every
      provenance field is DTO-OPTIONAL and kernel-validated, and publication_reference_type is an
      OPEN and OPTIONAL value (9.3.4), exactly so all four states are constructible. Boundary: PURE
      KERNEL. Expected, for each: PUBLICATION_PROVENANCE_INVALID. (E2-B fixtures B1-08a, B1-08b,
      B1-09a, B1-09b and B1-10 - one shape per ID, because the fourth review found that a single ID
      covering two shapes let one of them go untested);
    - absent DTO-REQUIRED constituents of a version record - a missing effective_from or a missing
      active_flag. PROVIDER-NEUTRAL COUNTERPART: the absence itself, at the port boundary. Boundary:
      DTO / PORT WELL-FORMEDNESS. Expected: AUTHORITY_CONFIGURATION_UNAVAILABLE (9.3.3). This
      document deliberately defines NO semantic reason code for "a version with no effective_from"
      or "a version with no active_flag", because such a record is not a published version at all;
      inventing one to mirror a NOT NULL constraint is prohibited (see class B2's prohibition, which
      applies here for the same reason).
```

#### Class B2 — persistence-only structural invariant with NO provider-neutral counterpart

A defect belongs in class B2 **only** when the database rejection protects a persistence
*representation* invariant that does not correspond to a distinct malformed state expressible
through the provider-neutral E2-A contract after persistence decoding.

```text
REQUIRED VERIFICATION - all five, none optional
    1. an E2-B database/migration/model test proves the PostgreSQL REJECTION (the write fails,
       naming the constraint);
    2. the fixture is EXPLICITLY EXCLUDED from the PostgreSQL provider-parity corpus;
    3. the fixture is EXPLICITLY EXCLUDED from E2-A's semantic fixture and parity manifests - it
       appears NOWHERE in section 18's DIRECT E2-A MALFORMED-INPUT COVERAGE;
    4. the manifest carries a SHORT NORMATIVE RATIONALE explaining why there is no meaningful
       provider-neutral malformed-input counterpart;
    5. NO E2-A reason code and NO DTO field/shape is invented solely to mirror the database
       implementation detail.

CLASS B2 SHAPES for a store that represents stable object identity as a SEPARATE PHYSICAL ROW from
its versions (which E2-B does - see E2-B 5.1)
    - a version row whose stable-identity parent row does not exist;
    - a retraction row whose object stable-identity parent row does not exist;
    - a rule/assignment version referencing a role/authority STABLE IDENTITY ROW that does not exist.

    RATIONALE, which is the whole justification and must not be paraphrased away: section 9.3.2
    carries object_id on the LineageMaterial CONTAINER, and groups versions[] and
    retraction_assertions[] UNDER it. A version or a retraction assertion therefore cannot be
    provider-neutrally orphaned from its object - the contract has no field in which that state could
    be expressed. And per 9.3.2, an object identity the provider holds nothing for returns COMPLETE
    material with an EMPTY versions[], which is exactly the ALREADY-CLASS-A dangling-reference state
    (AUTHORITY_REFERENCE_DANGLING, 11.5). So the third shape does not lack a counterpart in the sense
    of being ignored: its counterpart COLLAPSES ONTO an existing class A fixture that is already owed
    full parity. What the foreign key protects is the store's own two-table parent/child
    representation, which this contract deliberately does not model.
```

#### The B2 discipline — this is not a semantic exemption

```text
B2 is NOT a place to put a semantic defect that is merely inconvenient to test.

THE DECIDING TEST, applied before any fixture may be classified B2:
    Could ANY conforming provider, using only the DTO fields defined in 9.3.2/9.3.4 and without
    inventing a persistence-specific field, present a state that the kernel would classify
    DIFFERENTLY from an already-classified class A or class B1 state?
        YES, and the store rejects it   -> it is B1, and its E2-A boundary and expected reason must
                                           be named.
        YES, and the store can hold it  -> it is A, and full parity is owed.
        NO                              -> it is B2, and rationale requirement 4 must say WHY not.

A fixture classified B2 without that rationale, or with a rationale that amounts to "the kernel has
no test for it", is the F-10 defect reappearing and is a blocking finding.
```

#### Classification rule

```text
- Every negative or conformance item named by this document or by a provider package is FIRST put
  through the 9.7.0 ENTRY TEST. An item that passes it (a MALFORMED authority-store subject) is
  assigned to EXACTLY ONE of A, B1, B2 FOR THAT PROVIDER. An item that fails it because its stored
  state is VALID is recorded as a VALID-SHAPE PARITY SCENARIO (E2-B 5.7, V-01 to V-12) when its
  subject is that stored state. An item that fails it because its subject is a seam is recorded in
  the NON-STORE RESOLVER / PROVIDER CONFORMANCE SCENARIOS table instead (E2-B 5.7A). In both cases
  it carries no class label, and in both cases it must still carry an explicit executable test
  obligation - at the seam it actually exercises, or as a parity scenario over the valid state it
  actually seeds.
- No fixture may carry more than one class, and no MALFORMED authority-store fixture may be left
  unclassified or with its class implicit. No item may appear in more than one of the three groups
  (A/B1/B2 manifest, V-list, non-store table), and none may appear in no group at all.
- NO CLASSIFICATION MAY BE DEFERRED TO IMPLEMENTATION TIME. A manifest entry whose class,
  storability, expected reason code or parity obligation is written as "to be determined once the
  kernel is implemented" is not a classification; it is the F-10 defect restated. If a proposed
  fixture's status genuinely depends on whether the semantics make it reachable, that reachability
  question is answered HERE, from the rules this document already states (11.4a is the worked
  example), and the fixture is then either defined concretely or removed and replaced by a named
  invariant self-check.
- If a proposed structural constraint would make a defect impossible to persist while a parity
  obligation also demands that defect, the contradiction is resolved DELIBERATELY:
      * the constraint is genuinely structural AND a provider-neutral counterpart exists -> B1,
        with its four requirements and its named boundary; or
      * the constraint is genuinely structural AND no provider-neutral counterpart exists -> B2,
        with its five requirements including the written rationale; or
      * the defect is intentionally a STORABLE semantic contradiction -> the constraint must not
        exist, and the kernel - not the schema - classifies it (class A).
  "Both" is not an available answer, and neither is leaving it undecided.
- A fresh implementation or review chat must be able to answer, for EVERY named AUTHORITY-STORE
  negative fixture, from the repository alone:
      (1) is it A, B1 or B2?
      (2) can PostgreSQL intentionally store it?          (never "N/A" - see 9.7.0)
      (3) can the provider-neutral E2-A contract meaningfully represent it - and at which boundary
          (DTO validation / provider port / kernel)?
      (4) exactly what DB test is required?
      (5) exactly what E2-A test is required?
      (6) is PostgreSQL-provider parity required?
      (7) if there is no E2-A counterpart, WHY is that a persistence-only invariant rather than an
          ignored semantic defect?
  and, for EVERY named NON-STORE scenario, EIGHT - the extra one added by F-10.3b, because
  conflating (3) with (4) is what let a scenario that merely READS valid rows look like one whose
  malformed subject is stored state:
      (1) which already-defined seam is under test?
      (2) what input/condition drives it?
      (3) does PostgreSQL authority-store DATA participate in composing the test - i.e. must rows be
          stored and read to reach the condition?           (YES / NO, never blank)
      (4) is the malformed/negative SUBJECT itself authority-store state?
          (NO on every row, by construction - a YES means it belongs in 5.7 instead - and written
           out per scenario rather than inferred from (3))
      (5) exactly what executable test obligation applies?
      (6) what outcome / resolution_status / reason / evidence is expected?
      (7) is provider parity required, and BETWEEN WHICH PROVIDERS? If not, WHY does an agreement
          test have no second side - a surface/structural assertion, or a state no provider can
          present?
      (8) why is it outside A / B1 / B2?
  and, for EVERY named VALID-SHAPE scenario, that it seeds a VALID stored state, carries no class
  label, and is in the parity corpus.
  The binding per-fixture answers for the PostgreSQL store are the total manifest in
  `PF_1A_E2_B_...md` section 5.7, the binding per-scenario answers are its section 5.7A, and the
  valid-shape list is in 5.7 alongside the class A records.
```

#### What E2-A owns permanently

E2-A's direct malformed-input coverage (section 18, `DIRECT E2-A MALFORMED-INPUT COVERAGE`) is
**mandatory and permanent, regardless of what any store's schema rejects.** It is precisely the
coverage that makes a class B1 exclusion honest, so it may never be deleted, skipped, xfailed or
weakened on the grounds that "the database already prevents that". Deleting it would convert a
verification-placement decision into the semantic exemption this section forbids.

Class B2 is the deliberate, bounded exception, and its honesty rests on a different guarantee: not
on an E2-A test, but on the written rationale that no provider-neutral counterpart exists, checked
against the deciding test above. Because B2 fixtures appear in no E2-A manifest at all, every B2
classification must be re-examined whenever the provider-neutral DTO changes. If a future change to
section 9.3.2 or 9.3.4 makes one of these states expressible, it stops being B2 and becomes B1 that
same day.

#### What this section does not do

It does **not** permit a provider to reject, filter, normalize or suppress a semantic cross-row
contradiction in order to move it out of class A. Sections 9.3.1, 9.5, 11.4-11.6 and 11.8.3 are
unchanged: the storable contradictions the kernel is required to detect — explicit overlap,
duplicate temporal start, malformed or duplicated retraction, broken correction lineage, impossible
recorded provenance, dangling reference to a stable identity carrying no material — must remain
reachable through every provider that can physically hold them.

It also does **not** create a general "the contract does not model it, so it does not matter"
principle. B2 applies only to invariants over a store's *own* representation of identity and
parentage. A malformed *business* state is never B2.

And it does **not** let the 9.7.0 scope statement become an escape hatch. Moving a fixture out of
A/B1/B2 removes exactly one thing — a PostgreSQL **malformed-state storage** obligation that was
never executable, either because the store never holds that subject or because there was no
contradiction to store. It removes no fail-closed rule, no normative expected reason code, no
evidence obligation and no genuinely applicable parity obligation; every moved scenario carries all
of those in the 5.7A table, or in the V-list, instead. A scenario moved out of A/B1/B2 and left
without an explicit executable test obligation — at a named seam, or as a named parity scenario — is
the F-10 defect in a new costume, and is a blocking finding. The reverse abuse is equally a finding:
labelling a valid stored shape "class A" to keep it visible, which is what F-10.3a corrected.

`PF_1A_E2_B_...md` section 5.6 is the binding list of what may and may not be enforced structurally
in the PostgreSQL store, its section 5.7 is the binding, TOTAL per-fixture class assignment for
malformed authority-store fixtures AND the binding list of VALID-SHAPE parity scenarios (V-01 to
V-12), and its section 5.7A is the binding, TOTAL non-store scenario table.

## 10. Resolution operations

Two operations, deliberately separated.

### 10.1 Current / live authorization

```text
resolve_current_authority(
    authenticated_actor,          # server-side authenticated context, not client input
    authority_code,
    business_context
) -> AuthorityResolutionResult
```

```text
- The operation itself captures ONE server-controlled, timezone-aware current instant as `as_of`.
- It does NOT accept a caller-supplied as_of, and no parameter, header, query value or payload
  field may influence it. A client must not be able to re-acquire authority it used to hold.
- That single instant governs the ENTIRE evaluation: actor->person mapping, employment state,
  position version, incumbency, organisation unit versions, authority versions, role versions,
  rules, assignments, scope resolution and parameter evaluation. No component may call its own
  clock or resolve against a different instant (section 11.1).
```

### 10.2 Historical / internal as-of resolution

```text
resolve_authority_as_of(
    actor_person_reference,
    authority_code,
    business_context,
    as_of
) -> AuthorityResolutionResult
```

```text
- Explicitly accepts an instant, which is a BUSINESS-EFFECTIVE instant. For audit, reconstruction,
  reconciliation and deterministic tests.
- Its exact semantic is CORRECTED BUSINESS-EFFECTIVE RECONSTRUCTION under the complete authoritative
  publication/correction lineage known at invocation time. It is NOT point-in-time
  recorded-knowledge replay. Section 11.8 defines this normatively and must be read with this
  section; do not implement either operation without it.
- MUST NEVER be used to authorize a new current business action. E2-A must make this structurally
  hard, not merely documented: separate entry points, separate naming, and a test proving the
  current-authorization path does not expose an as_of parameter - or any recorded-time cutoff such
  as a published_at bound - through any signature, DTO field or keyword pass-through.
```

Both operations share one pure kernel. The kernel takes an explicit instant and explicit resolved
inputs and returns a result; only 10.1 is permitted to obtain the instant from the clock.

### 10.3 Kernel purity

The kernel must be a pure function of (instant, request, port results). It performs no I/O, reads
no clock, reads no environment, raises no HTTP concern, and holds no database session. E2-B must be
able to reuse it **unchanged**; any E2-B change to the kernel is a signal that E2-A's boundary was
drawn wrongly and requires reconciliation, not a quiet edit.

## 11. Temporal semantics and publication lineage

### 11.1 One authoritative instant

Exactly one `as_of` governs a resolution. It is timezone-aware and normalized to UTC (ADR-028:
database timestamps are UTC; the UI's Asia/Kolkata display convention is unaffected and irrelevant
here). The instant is carried explicitly through every port call and every evaluation step, and is
recorded in the result evidence. A component that needs "now" must receive the instant; it must
never call a clock of its own.

### 11.2 Half-open intervals and what "effective" means

The canonical convention from `PF_1F_HR_CANONICAL_REFERENCE_MODEL.md` applies identically to every
business-authority object version, every rule, every assignment, and every HR record consumed:

```text
effective_from   INCLUSIVE
effective_to     EXCLUSIVE, nullable ("no known end")

EFFECTIVE(V, as_of) :=
        V is in the current asserted lineage (i.e. V carries no VALID retraction assertion, as
        established AFTER the whole lineage has been validated - section 11.3)
    AND effective_from(V) <= as_of
    AND (asserted_effective_to(V) IS NULL OR as_of < asserted_effective_to(V))

where asserted_effective_to is DERIVED per the section 11.4 asserted-interval rule and is never
stored on the row, and `as_of` is the single BUSINESS-EFFECTIVE instant of 11.1 - never a recorded
time (11.8).
```

`EFFECTIVE` is a purely temporal/lineage predicate. It says nothing about `active_flag`.
**Grant-eligibility is `LINEAGE VALID AND EFFECTIVE AND active_flag == true` (section 8.2).** The
two must never be merged into one predicate, because a caller of the evidence contract must be able
to see which of the two failed.

Consequences that must be tested explicitly:

```text
- exactly at effective_from                       -> effective
- one tick before effective_from                  -> NOT effective (a future-dated grant confers
                                                     nothing before its own start)
- one tick before asserted_effective_to           -> effective
- exactly at asserted_effective_to                -> NOT effective
- adjacent versions meeting at the same instant   -> no gap and no overlap
- an instant inside a legitimate gap              -> NO version effective (section 11.5)
```

### 11.3 The lineage problem, and the adopted model

There is a real tension the naive model does not resolve: **published versions are immutable
(I-2), yet a later version must be able to bound an earlier open-ended one.** If version 1 is
published with `declared_effective_to = null` and version 2 is later published effective from X,
setting version 1's `effective_to` to X would mutate an already-published row that historical
decisions may already cite. That is not acceptable.

**Rejected approach.** A `supersedes_version` pointer chain is *not* adopted as the resolution
mechanism. It requires walking a chain that can fork, break or disagree with the versions' own
effective dates, and it still leaves the closing instant implicit. Such an annotation may be
retained as optional audit information, but resolution must not depend on it.

**Adopted model: derived closure over an append-only lineage.**

```text
LINEAGE
    All published versions of one stable object. Append-only: publishing is the only write, and it
    only ever appends. Nothing is ever edited or deleted.

RETRACTION ASSERTION (append-only)
    A separate, append-only record stating that a specific (object_id, object_version) was recorded
    in error and must no longer participate in resolution:
        retraction_id
        object_family, object_id, object_version
        retracted_at                 (recorded/system time)
        publication_reference_type / publication_reference_id
    A retraction never edits the retracted version. The retracted version remains fully
    dereferenceable through get_published_version (section 9.3.2).

CURRENT ASSERTED LINEAGE
    The versions of a stable object that carry no VALID retraction assertion.

    Order of operations, which matters and is not optional: the kernel first receives the COMPLETE
    lineage material for the object (9.3.2, reached through RAW discovery per 9.3.1); then validates
    every retraction and correction assertion and its provenance (11.6, 11.8.3); and only then
    derives the current asserted lineage. An INVALID retraction never removes its target - it fails
    the whole resolution closed. A retraction is therefore never a shortcut for making an
    inconvenient version disappear, at any layer.
```

### 11.4 Derived asserted closure — valid successor closure, gaps, and explicit overlap (F-09)

**The naive formula `min(declared_effective_to, next_start)` is REJECTED and must not be
implemented.** It silently rewrites a genuine, explicitly declared overlap into two adjacent
non-overlapping intervals, which makes the overlap contradiction in 11.6 unreachable for any case
other than a duplicate start. Truncating a publisher's explicit declaration is also a normalization
of published business meaning, which contradicts immutability (I-2) in spirit even though no row is
edited.

Closure is derived **only after** the deterministic canonical ordering of the current asserted
lineage and the duplicate-start check below.

```text
PRE-CHECK (before any closure is derived)

    DUPLICATE START
        two or more versions in the current asserted lineage sharing the same effective_from
        -> CONTRADICTORY. Fail closed (AUTHORITY_LINEAGE_CONTRADICTORY). Closure is not derived,
           and no tie-break is attempted.

    NONSENSICAL DECLARED INTERVAL
        declared_effective_to(V) IS NOT NULL AND declared_effective_to(V) <= effective_from(V)
        -> CONTRADICTORY. Fail closed (AUTHORITY_LINEAGE_CONTRADICTORY; invariant I-6). This covers
           both an end before the start and an empty (end == start) interval.

ORDERING
    After the duplicate-start check, effective_from is unique across the current asserted lineage,
    so ordering by effective_from ASC is a total order over that lineage.

    next_start(V) = the effective_from of the next valid successor version - that is,
                    min{ effective_from(W) : W in the current asserted lineage,
                                             effective_from(W) > effective_from(V) }
                    - if such a W exists; otherwise next_start(V) is undefined.

ASSERTED INTERVAL RULE

    NO SUCCESSOR (next_start(V) undefined)
        declared_effective_to(V) IS NULL      -> asserted_effective_to(V) = NULL (open-ended).
        declared_effective_to(V) non-null     -> asserted_effective_to(V) = declared_effective_to(V),
                                                 subject to the nonsensical-interval pre-check above.

    SUCCESSOR EXISTS
        declared_effective_to(V) IS NULL
            -> the successor CLOSES the open-ended version:
               asserted_effective_to(V) = next_start(V).                     VALID.

        declared_effective_to(V) <  next_start(V)
            -> asserted_effective_to(V) = declared_effective_to(V).
               The interval (declared_effective_to(V), next_start(V)) is a VALID TEMPORAL GAP
               during which no version of this object is effective (11.5).   VALID.

        declared_effective_to(V) == next_start(V)
            -> asserted_effective_to(V) = declared_effective_to(V) = next_start(V).
               Explicit ADJACENCY: the two intervals meet exactly at a half-open boundary, with no
               gap and no overlap.                                            VALID.

        declared_effective_to(V) >  next_start(V)
            -> CONTRADICTORY EXPLICIT OVERLAP. The published lineage asserts two different things
               about the same instant. FAIL CLOSED (AUTHORITY_LINEAGE_CONTRADICTORY).
               DO NOT truncate it, DO NOT normalize it to next_start(V), DO NOT prefer either
               version, and DO NOT "repair" it. Correction is a governed append-only act (11.6),
               never a resolution-time adjustment.                            INVALID.
```

The model remains fully append-only and deterministic: a successor closes an *open-ended*
predecessor by existing, without any mutation, while an *explicitly declared* end is honoured
exactly as published and never silently shortened. It expresses deactivation without a successor
(publish a version with `active_flag = false` and its own `effective_from`), an explicit planned end
(`declared_effective_to` set at publication and never changed), a deliberate period of absence
followed by reactivation (a gap, 11.5), and a genuinely broken publication (explicit overlap, failing
closed).

A worked check a reviewer can apply directly:

```text
V1 [t0, null),  V2 from t2                     -> V1 closes at t2. Adjacent. VALID.
V1 [t0, t2),    V2 from t2                     -> explicit adjacency at t2.  VALID.
V1 [t0, t1),    V2 from t2, t1 < t2            -> gap [t1, t2). Reactivation at t2. VALID.
V1 [t0, t3),    V2 from t2, t0 < t2 < t3       -> EXPLICIT OVERLAP. FAIL CLOSED.
V1 [t0, ...),   V2 also from t0                -> duplicate start. FAIL CLOSED.
V1 [t0, t0)     or V1 [t0, t_before_t0)        -> nonsensical interval. FAIL CLOSED.
```

The fourth line is the case the rejected `min(...)` formula turned into `V1 [t0, t2), V2 [t2, ...)`
and thereby hid.

### 11.4a Single-effective-version theorem, and the status of the residual multiplicity clause (F-10.2)

Section 11.6 lists, as a residual catch-all sitting **after** the duplicate-start and
explicit-overlap conditions, "more than one version of the current asserted lineage satisfying
EFFECTIVE at the evaluation instant". A previous draft left it undecided whether any real state can
still reach that clause, and deferred the question — together with the expected reason code and the
PostgreSQL parity obligation of the fixture that was supposed to exercise it — to implementation
time. That deferral is withdrawn. The question is answered here, from the rules already stated
above, because it is a property of 11.2 and 11.4 and not of any store.

```text
THEOREM (single effective version).
    Let L be the CURRENT ASSERTED LINEAGE of one stable object at the point closure is derived -
    that is, after (a) every retraction and correction assertion and all provenance has been
    validated (11.3, 11.6, 11.8.3), (b) the DUPLICATE START pre-check has passed, (c) the
    NONSENSICAL DECLARED INTERVAL pre-check has passed, and (d) no EXPLICIT OVERLAP branch has
    fired.
    Then for ANY instant t, AT MOST ONE version in L satisfies EFFECTIVE(V, t).

PROOF.
    By (b), effective_from is injective over L, so "<" on effective_from is a strict total order
    on L (this is exactly what 11.4's ORDERING paragraph already relies on).

    LEMMA. For every V in L that has a successor, asserted_effective_to(V) is NON-NULL and
    asserted_effective_to(V) <= next_start(V).
        The SUCCESSOR EXISTS branch of 11.4 has exactly four cases. declared NULL gives
        asserted = next_start. declared < next_start gives asserted = declared < next_start.
        declared == next_start gives asserted = next_start. declared > next_start is the EXPLICIT
        OVERLAP failure, excluded by (d). In all three surviving cases the value is non-null and is
        <= next_start(V). (The only branch that yields NULL is NO SUCCESSOR, which does not apply.)

    Suppose V, W in L, V != W, and both satisfy EFFECTIVE at t. By injectivity, WLOG
    effective_from(V) < effective_from(W). Then W is a successor of V, so next_start(V) is defined
    and next_start(V) <= effective_from(W).
        EFFECTIVE(V, t) requires asserted_effective_to(V) IS NULL or t < asserted_effective_to(V).
        By the lemma it is not NULL, so t < asserted_effective_to(V) <= next_start(V)
        <= effective_from(W).
        EFFECTIVE(W, t) requires effective_from(W) <= t.
    Together: t < effective_from(W) <= t. Contradiction. Hence at most one such V exists.   QED
```

Three consequences, all normative:

```text
1. THE RESIDUAL CLAUSE IS UNREACHABLE FROM ANY PROVIDER INPUT. The theorem is a statement about
   11.2 and 11.4, not about any store's schema. No lineage material - PostgreSQL-storable,
   reference-provider-constructed, or supplied by a future provider with a weaker schema - can
   present a state that passes the duplicate-start, nonsensical-interval and explicit-overlap
   conditions and still yields two effective versions. There is therefore NO authority-store
   negative fixture to seed, on any provider, and no parity obligation to owe. E2-B's former
   fixture A-03 is withdrawn accordingly (E2-B 5.7).

2. THE CLAUSE ITSELF IS NOT DELETED, AND MUST NOT BE. It is retained in 11.6 as a DEFENSIVE KERNEL
   INVARIANT: a cheap, explicit assertion that the theorem actually holds in the implementation, so
   that a future refactor of ordering, closure or retraction validation that breaks it fails closed
   loudly instead of silently granting authority from an ambiguous lineage. An implementation that
   removes the check as "dead code" has removed the one guard that would catch its own regression,
   and that is a blocking finding.

3. ITS REASON CODE IS NORMATIVE, NOT IMPLEMENTER'S CHOICE. If the defensive invariant is ever
   violated, the resolution is DENY + FAIL_CLOSED with result_level_reason
   AUTHORITY_VERSION_AMBIGUOUS - not AUTHORITY_LINEAGE_CONTRADICTORY, which is reserved for the
   detectable lineage contradictions the pre-checks and the overlap branch DO reach, and not
   INTERNAL_CONTRACT_VIOLATION, which is reserved for a violated kernel invariant that is not about
   authority-version multiplicity. AUTHORITY_VERSION_AMBIGUOUS keeps its declared reason_code_rank
   (15.5) exactly as any other fail-closed code does.
```

Because the state is unreachable from provider input, the invariant is verified as a **pure-kernel
self-check** rather than as an authority-store fixture: scenario `NS-K-01` in the non-store table
(E2-B 5.7A), whose executable obligation is stated there and cross-referenced from section 18. The
code `AUTHORITY_VERSION_AMBIGUOUS` is consequently on the justified PostgreSQL parity-exclusion list
as KERNEL-INTERNAL — excluded because no provider can present the state, never because the state is
tolerated.

### 11.5 A temporal gap is VALID lineage, not a contradiction (F-05)

The first candidate classified "a declared end before a later version's start" as irreconcilable
corruption. That was wrong, and it is corrected here.

```text
GAP (VALID)
    declared_effective_to(V1) = t1 and the next valid successor V2 starts at t2 with t1 < t2.
    Derived closure gives asserted_effective_to(V1) = t1 (11.4). During [t1, t2) NO version of the
    object is effective. This is a normal, supported history: an object may end, be absent for a
    period, and later be reactivated or re-established by a new effective version. A LATER VALID
    VERSION AFTER A GAP IS REACTIVATION, NOT CORRUPTION, and never invalidates the lineage.

OVERLAP / DUPLICATION / CONTRADICTION (INVALID -> FAIL CLOSED)
    two versions in the current asserted lineage sharing the same effective_from; or an EXPLICIT
    OVERLAP in which declared_effective_to(V1) > next_start(V1) (11.4 - never truncated or
    normalized away); or any residual state in which more than one version of the current asserted
    lineage satisfies EFFECTIVE at one instant; or a version whose own declared_effective_to <= its
    own effective_from; or broken/contradictory retraction and correction assertions (11.6).
```

Behaviour of a valid gap, per family, at an `as_of` inside the gap. None of these is corruption and
none fails closed:

```text
BusinessAuthorityAssignment   no effective assignment -> this candidate contributes no path.
                              Reason ASSIGNMENT_NOT_EFFECTIVE. If no other path qualifies, the
                              result is an ordinary DENY + RESOLVED.

BusinessAuthorityRule         no effective rule -> that path has no grant relation between the role
                              and the authority. Reason RULE_NOT_EFFECTIVE. Normal
                              nonqualification.

BusinessAuthorityRole         no effective version for a REFERENCED role whose lineage exists -> the
                              path cannot qualify. Reason ROLE_NOT_EFFECTIVE. Represented
                              deterministically as a partial evaluation (16.4); explicitly NOT
                              corruption and explicitly NOT a dangling reference.

BusinessAuthority (requested) no effective version establishing the requested authority_code ->
                              the requested authority's MEANING AND CONFIGURATION cannot be
                              established at as_of. Under the already-settled unconfigured-authority
                              rule this is DENY + FAIL_CLOSED, AUTHORITY_CODE_NOT_CONFIGURED.
                              This is deliberately asymmetric with the three families above,
                              because the other three describe an absent grant while this one
                              describes an unknown question.
```

The distinction between a gap and a dangling reference is exact:

```text
GAP                lineage material EXISTS for the stable id, but no version is effective at as_of.
                   -> normal nonqualification (or, for the requested authority, the fail-closed rule
                      above).
DANGLING           NO lineage material exists for the referenced stable id at all (no versions ever,
                   or every version retracted with no replacement lineage record).
                   -> FAIL_CLOSED, AUTHORITY_REFERENCE_DANGLING. The configuration is broken, not
                      merely quiet.
```

Two clarifications that follow from 11.4 and must not be lost:

```text
- A gap NEVER makes the surrounding lineage "overlap corruption". Overlap is a distinct, explicitly
  defined condition (declared_effective_to > next_start, or a duplicate start). A reviewer or
  implementer who reports AUTHORITY_LINEAGE_CONTRADICTORY merely because a valid gap exists has
  reintroduced the cycle-1 F-05 defect.
- The "every version retracted with no replacement" DANGLING case is established from COMPLETE
  lineage material after the retraction assertions themselves have been validated (11.6), never from
  a discovery-time exclusion. Discovery is raw (9.3.1): an object whose only reference-bearing
  version carries an INVALID retraction is still discovered, still has its lineage validated, and
  still fails closed on that invalid retraction - it does not disappear and it is not reported as
  dangling.
```

### 11.6 Lineage contradictions that must fail closed

```text
- two versions of the current asserted lineage with the same effective_from (duplicate start, 11.4);
- an EXPLICIT OVERLAP: a version whose declared_effective_to is strictly greater than the
  effective_from of its next valid successor (11.4) - never truncated, normalized or repaired;
- more than one version of the current asserted lineage satisfying EFFECTIVE at the evaluation
  instant (the residual catch-all, after the two conditions above). PROVED UNREACHABLE from any
  provider input by the theorem in 11.4a; retained as a DEFENSIVE KERNEL INVARIANT that must not be
  deleted, and emitting AUTHORITY_VERSION_AMBIGUOUS if ever violated. It is verified as pure-kernel
  self-check NS-K-01 (E2-B 5.7A), not as an authority-store fixture, and it is therefore the one
  entry in this list with no A/B1/B2 class;
- a version whose declared_effective_to <= its own effective_from (I-6);
- a retraction assertion referencing a version that does not exist;
- more than one retraction assertion for the same (object_id, object_version);
- a correcting version whose corrects_object_version is not itself retracted;
- a correcting version whose corrects_object_version does not exist;
- a duplicate (object_id, object_version) pair within one lineage;
- missing, unknown or internally inconsistent publication provenance on any participating version
  or retraction assertion, including a recorded timestamp that violates the validity constraints of
  section 11.8;
- a reference to a stable identity with no lineage material at all (dangling, section 11.5).
```

Reason codes: `AUTHORITY_LINEAGE_CONTRADICTORY`, `AUTHORITY_VERSION_AMBIGUOUS`,
`PUBLICATION_PROVENANCE_INVALID`, `AUTHORITY_REFERENCE_DANGLING`.

Never tie-break, never take the latest, never take the first. Fail closed and require correction.

**Where each of these is PROVED (F-10).** Every contradiction listed above is a semantic rule of
this document and binds every provider without exception. Which test demonstrates it depends on
whether the provider can physically hold the shape, and — where it cannot — on whether a
provider-neutral counterpart exists at all, per the three classes of section 9.7:

```text
CLASS A - must remain STORABLE and must be PARITY-tested on any store that can hold it
    duplicate effective_from (duplicate temporal start);
    explicit overlap (declared_effective_to > next_start);
    a retraction assertion referencing a version that does not exist (dangling retraction);
    more than one retraction assertion for the same (object_id, object_version);
    a correcting version whose corrects_object_version is not retracted, or does not exist;
    INTERNALLY INCONSISTENT provenance - the cross-row recorded-timestamp violations of 11.8.3;
    a reference to a stable identity that carries no lineage material (dangling reference).

CLASS B1 - a store may reject these structurally; the store then proves the REJECTION, and this
document proves the fail-closed classification DIRECTLY at the named boundary (section 18)
    a duplicate object_version within one object's material          KERNEL ->
        AUTHORITY_LINEAGE_CONTRADICTORY;
    declared_effective_to <= its own effective_from (I-6), including the empty end == start case
                                                                     KERNEL ->
        AUTHORITY_LINEAGE_CONTRADICTORY;
    an assignment version carrying neither or both of person_id / position_id
                                                                     KERNEL (S7) ->
        ASSIGNMENT_TARGET_INVALID;
    MISSING or UNKNOWN provenance, as FOUR separately named shapes -
        an absent published_at, or an absent retracted_at on a retraction assertion;
        an ABSENT publication_reference_type;
        an absent publication_reference_id;
        a publication_reference_type OUTSIDE the two defined values
                                                                     KERNEL, each ->
        PUBLICATION_PROVENANCE_INVALID;
    an absent DTO-REQUIRED constituent - no effective_from, or no active_flag
                                                                     DTO / PORT WELL-FORMEDNESS ->
        AUTHORITY_CONFIGURATION_UNAVAILABLE (9.3.3, 9.3.4).

NOT CLASSIFIED HERE - the residual multiplicity clause above is unreachable from any provider input
(11.4a) and is verified as pure-kernel self-check NS-K-01 in the non-store table (E2-B 5.7A). It has
no A/B1/B2 class because it has no storable subject, not because it is exempt.

CLASS B2 - a store may reject these structurally, and there is NO distinct provider-neutral
malformed counterpart, so they appear in NO E2-A fixture manifest (9.7 class B2)
    a version record whose stable-identity PARENT ROW does not exist;
    a retraction record whose object stable-identity PARENT ROW does not exist;
    a rule/assignment referencing a role/authority STABLE IDENTITY ROW that does not exist.
    Rationale: object_id lives on the LineageMaterial CONTAINER (9.3.2), so a version or retraction
    cannot be provider-neutrally orphaned; and an identity carrying no material decodes to the
    class A dangling-reference state, which is already parity-tested. See 9.7 class B2.
```

Nothing here weakens, qualifies or exempts any rule above; it settles only where each is
demonstrated. Classes A and B1 are both mandatory verification obligations; class B2 is a bounded
statement that a particular database constraint has no semantic counterpart to verify, and it
carries its own written rationale rather than a test. `PF_1A_E2_B_...md` section 5.7 carries the
binding, TOTAL per-fixture assignment for the PostgreSQL store.

**Corrections** (the recorded business-effective claim was itself wrong) follow the canonical HR
pattern: retract every affected version, then publish corrected replacement versions carrying
`corrects_object_version`. A corrected boundary may affect two or more adjacent versions at once;
all of them are retracted and replaced, never only "the wrong one".

E2-A owns this **semantic model and its invariants**. It deliberately does not freeze E2-B's exact
table layout; E2-B may choose any representation that provably satisfies the invariants above,
supplies complete lineage material per section 9.3, and passes the same deterministic conformance
and parity tests.

### 11.7 Publication provenance without governance

Every published version and every retraction assertion carries immutable provenance:

```text
publication_reference_type    BOOTSTRAP_PROVENANCE | CONFIGURATION_CHANGE
publication_reference_id
published_at / retracted_at
```

`BOOTSTRAP_PROVENANCE` is the only type E2 fixtures use, and it is explicitly synthetic/test
provenance. `CONFIGURATION_CHANGE` is a forward-compatible reference that E3 will populate; E2
defines the value's shape and never creates such a record. Unknown, missing or internally
inconsistent provenance fails closed (`PUBLICATION_PROVENANCE_INVALID`).

Stated field by field, so no shape can be assumed covered by another (F-10.1): an **absent**
`publication_reference_type`, an **unknown** `publication_reference_type` (any value other than the
two above), an **absent** `publication_reference_id`, an **absent** `published_at` on a version, and
an **absent** `retracted_at` on a retraction assertion are five distinct malformed states. Each
fails closed with `PUBLICATION_PROVENANCE_INVALID`, and each carries its own mandatory direct E2-A
fixture at the pure-kernel boundary (section 18). **Absence and unknown-value are not the same
state**, and a kernel that validates only membership in the two defined values — implicitly treating
an absent type as "nothing to check" — passes the unknown-value fixture while failing the
absent-type one. That is precisely the gap the fourth review found.

**Synthetic bootstrap provenance in an E2 fixture is not a resolution of Q-10 and is not a
production bootstrap.** It must be labelled as such in the fixture itself, exactly as
`PF_1A_AUTHORITY_CONFIGURATION_MODEL.md`'s own fixture does.

### 11.8 Recorded time versus business-effective time (F-07)

Two clocks appear in the lineage, and conflating them is a security defect in either direction. This
section settles their relationship normatively. **The one authoritative business `as_of` invariant of
section 11.1 is unchanged and is not weakened by anything here.**

```text
BUSINESS-EFFECTIVE TIME     as_of, effective_from, declared_effective_to, asserted_effective_to.
                            The single as_of is THE authorization clock. It governs authority
                            versions, roles, rules, assignments, scope, parameters AND every HR/org
                            evaluation, consistently, in one resolution (11.1).

RECORDED TIME               published_at, retracted_at.
                            Immutable recorded-time / provenance EVIDENCE and VALIDATION INPUT.
                            NOT a second business-effective clock, and NOT an authorization clock.
```

#### 11.8.1 The E2 historical resolver contract

`resolve_authority_as_of` (10.2) is defined as **corrected business-effective reconstruction under
the complete authoritative publication/correction lineage known at resolver invocation time.**

```text
- as_of remains the BUSINESS-EFFECTIVE instant, and is used consistently across authority evaluation
  and HR/organisation evaluation alike.
- published_at and retracted_at are NEVER used to filter lineage merely because they are later than
  the historical business as_of. A version published today that asserts a business-effective
  interval containing an older as_of DOES participate in reconstructing that older instant, and a
  retraction recorded today DOES remove its target from that reconstruction.
- A valid later append-only correction or retraction may therefore change what
  resolve_authority_as_of(old_business_time) reconstructs TODAY compared with what it reconstructed
  before the correction. That is the intended behaviour: the corrected lineage is the best current
  understanding of what was business-effective then.
- This NEVER mutates or rewrites the evidence of an authorization decision that actually happened
  earlier. The immutable decision evidence captured at that time (section 16), together with
  get_published_version dereference (9.3.2, which is unaffected by retraction), remains the source
  of truth for "what the system decided, and what it knew, then". The two answers are allowed to
  differ; that difference is exactly the audit signal a correction is supposed to produce, and both
  sides of it remain provable.
- POINT-IN-TIME RECORDED-KNOWLEDGE REPLAY - "reconstruct using ONLY the publications known by
  recorded time T", i.e. a bitemporal as-known-at query - is explicitly NOT the E2 historical
  resolver contract. Do not implement it here, do not approximate it by filtering on published_at,
  and do not describe resolve_authority_as_of as providing it. If it is later required, it belongs
  to evidence/audit replay under separately authorized work, using published_at/retracted_at as the
  recorded-time axis alongside the business-effective axis.
```

#### 11.8.2 Live resolution

```text
- resolve_current_authority uses the COMPLETE authoritative lineage available at invocation and the
  ONE server-captured current business as_of (10.1). It never accepts a caller backdate, and no
  recorded-time parameter is exposed on it either - offering a caller-selected published_at cutoff
  would be an equivalent backdating attack under a different name.
```

#### 11.8.3 Validity constraints on recorded timestamps

Recorded timestamps must be constrained enough to fail closed on impossible or contradictory
provenance, **without** becoming caller-controlled authorization time.

```text
- published_at and retracted_at are timezone-aware, normalized to UTC, and NOT NULL on every
  published version and every retraction assertion respectively.
- A retraction's retracted_at must be >= the published_at of the version it retracts. A retraction
  recorded before the thing it retracts was published is impossible provenance.
- A correcting version's published_at must be >= the retracted_at of every version it corrects
  (correction is retract-then-republish, 11.6). A correction recorded before its target was
  retracted is impossible provenance.
- Within one stable object's lineage, published_at must be NON-DECREASING IN object_version order.
  Version numbers are assigned in publication order, so a higher object_version whose published_at
  precedes that of a lower object_version is contradictory provenance. (This constrains RECORDED
  order only. Business intervals may legitimately be published out of business order - a backdated
  correction is normal and expected - so NOTHING here ties published_at to effective_from, and a
  version published today may assert any business-effective interval, past or future.)
- Equal timestamps are permitted wherever ">=" is stated above; simultaneity is not by itself a
  defect.
- Any violation of the above is PUBLICATION_PROVENANCE_INVALID and fails closed (11.6, 14.3). It is
  never repaired, reordered or ignored.
- These constraints are VALIDATION only. They never select which version is business-effective, and
  they never act as a filter on lineage material.
```

#### 11.8.4 Evidence

Every result's evidence records the single business `as_of` (16.1) and, for each cited version, its
`published_at` (and, where a retraction participated in the decision, that assertion's
`retracted_at`) as provenance evidence — labelled as recorded time, never as effective time, so a
later reader cannot mistake one for the other.

## 12. Candidate paths, scope and composition (F-03)

### 12.1 The complete candidate grant path — normative

A grant exists if and only if a **complete candidate path** qualifies. The path is:

```text
authenticated actor (server-side context)
  -> canonical person                       port 9.1; never client-supplied
  -> employment state at as_of              port 9.2; must be unambiguously active
  -> [only for a position assignment]
     effective position incumbency at as_of port 9.2; incumbent must be this canonical person
  -> BusinessAuthorityAssignment            grant-eligible version, target matches this person
  -> BusinessAuthorityRole                  the assignment's role_id, grant-eligible version
  -> BusinessAuthorityRule                  role_id -> business_authority_id, grant-eligible version
  -> BusinessAuthority (requested)          authority_code matches, grant-eligible version
```

Every one of the four business-authority stages must be **grant-eligible** as defined in section
8.2 (lineage valid, effective at the single `as_of`, `active_flag == true`). In addition the
composed scope predicate (12.4) and the rule's parameter evaluation (section 13) must be satisfied.

Required HR/org evidence per path:

```text
ALWAYS      canonical person_id; employment-state version/reference; canonical_snapshot_at.
POSITION    Position Version identity and incumbency_id, both resolved at the SAME as_of.
            A position assignment NEVER confers authority on a former incumbent: incumbency is
            re-resolved every time, never inferred from history.
SCOPE       Organisation Unit Version identities for every hop actually traversed (12.3).
```

Required evaluator data: the declared business facts named by the rule's evaluator payload, taken
from the authoritative business context supplied by the caller (section 13).

### 12.2 Deterministic evaluation stages (traversal does not affect the result)

The kernel may traverse the graph in whichever direction is efficient, but the result must be
identical either way. The stages, which supply `stage_rank` for the total defect order in 15.5 and
allow the two legitimate short-circuits in 15.3, are:

```text
S0  identify the authenticated actor
S1  resolve canonical person
S2  establish employment state
S3  establish the requested Business Authority (discovery 9.3.1 + lineage 9.3.2 + grant-eligibility)
S4  discover candidate Rules for that authority and establish their versions
S5  establish the referenced Business Authority Role versions
S6  discover candidate Assignments for those roles and establish their versions
S7  resolve each assignment's target against this person (direct, or via incumbency at as_of)
S8  evaluate composed scope
S9  evaluate parameters
```

`stage_rank(S0) = 0 ... stage_rank(S9) = 9`. This numbering is a fixed, closed part of the contract:
inserting a stage later requires renumbering deliberately and re-reviewing 15.5, never quietly
appending an out-of-order value.

**The stage order alone is NOT a total order over defects (F-08).** Two different defects with
different reason codes can occur at the *same* stage — for example
`PUBLICATION_PROVENANCE_INVALID` on one relevant Rule and `AUTHORITY_LINEAGE_CONTRADICTORY` on
another, both at S4. Section 15.5 extends `stage_rank` into the total order that selects the
result-level reason and orders the evidence.

A path is **COMPLETE** once S3–S7 have established all four `(object_id, object_version)` pairs and
the assignment target matches this person. S8 and S9 then decide whether a complete path
**qualifies** or is a **complete nonqualifying path** (section 16.3). Anything failing before
completeness produces a **partial evaluation** record (section 16.4).

A determinism test must assert that reversing the traversal direction and shuffling every provider
result leaves outcome, status, reason, path sets and evidence ordering unchanged.

### 12.3 Scope predicates

E2-A defines a bounded, deterministic scope mechanism. It does **not** invent a PBL organisation
hierarchy.

```text
SATISFIES(scope, context) for a single scope operand:

GLOBAL                      satisfied for every applicable business context. GLOBAL is the
                            unconstrained TOP element for that operand.
EXACT (scope_type,scope_id) satisfied only when the authoritative request context carries the same
                            canonical scope_type and scope_id.
ANCESTRY (optional)         satisfied when the context's canonical scope is the operand's scope or
                            a descendant of it, resolved ONLY through the provider-neutral canonical
                            organisation reference (get_org_unit, parent_org_unit_id, at the same
                            as_of).
```

Rules:

```text
- Scope identifiers are canonical (org_unit_id and other canonical scope identities). A raw
  provider identifier is never a scope_id.
- Ancestry traversal, if implemented, must be bounded (an explicit maximum depth), must resolve each
  hop's Organisation Unit Version at the SAME as_of, and must fail closed on a missing version, an
  ambiguous version, a cycle, or depth exhaustion (ORG_HIERARCHY_UNRESOLVABLE).
- A scope_type the evaluator does not support fails closed (SCOPE_SEMANTICS_UNSUPPORTED). It is
  never treated as GLOBAL and never silently ignored.
- A business context that does not supply a scope required by a non-GLOBAL operand fails closed
  (SCOPE_CONTEXT_MISSING) rather than matching permissively.
- A well-formed, supported operand that simply does not match is ordinary nonqualification
  (RULE_SCOPE_NOT_MATCHED / ASSIGNMENT_SCOPE_NOT_MATCHED), not a defect.
```

### 12.4 Scope composition — intersection of Rule scope and Assignment scope

Both the Rule and the Assignment carry scope. They **compose by intersection**:

```text
SCOPE_SATISFIED(path, context) := SATISFIES(rule.scope, context)
                              AND SATISFIES(assignment.scope, context)

- BOTH operands must be satisfied. There is no union, no widening, and no "either will do".
- GLOBAL is unconstrained/top for its operand, so GLOBAL ∩ X = X: a GLOBAL rule scope with an EXACT
  assignment scope is constrained by the assignment, and vice versa.
- Two EXACT operands naming different canonical scopes can never both be satisfied by one context;
  this is ordinary nonqualification (SCOPE_COMPOSITION_NOT_SATISFIED), not a defect and not a
  configuration error.
- Incompatible or non-matching scope combinations are normal nonqualification. Only UNSUPPORTED
  semantics, MISSING required context, or an UNRESOLVABLE organisation relationship fail closed.
```

The path evidence records each operand's own evaluation and the composed outcome, so a reviewer can
see which operand was decisive (section 16.3).

## 13. Authority-specific parameter evaluation

There is **no** universal monetary schema. Different authorities genuinely need different parameter
shapes (`PF_1A_AUTHORITY_CONFIGURATION_MODEL.md` section 3).

E2-A defines an **evaluator registry**: each `parameter_evaluator_type` has a typed,
schema-validated `parameter_payload` and a deterministic evaluation function over the business
context's declared facts.

Illustrative evaluator types — examples of the mechanism, **not** a promise of the production
catalogue:

```text
NONE               no parameters; the rule is scope-only.
NUMERIC_BAND       lower/upper bounds with EXPLICIT inclusivity flags and an EXPLICIT unit
                   (for example currency INR, per ADR-023 / Q-08 - the unit is declared in the
                   payload and matched against the fact, never assumed).
PERCENTAGE_BAND    bounds with explicit inclusivity and an explicit percentage basis.
EXACT_VALUE_SET    membership in an enumerated set of canonical values.
```

Requirements:

```text
- Evaluator selection is deterministic and total: exactly one registered evaluator per
  parameter_evaluator_type, resolved by exact match, never by prefix, fuzzy match or fallback.
- Boundary semantics are EXPLICIT. "lower_limit"/"upper_limit" without stated inclusivity is
  forbidden; the payload must state it.
- Units/currency/basis are explicit and must match the supplied fact. A unit, currency or basis
  INCOMPATIBILITY between the payload and the supplied fact is MALFORMED EVALUATOR INPUT, not a
  comparison that came out false: it fails closed (EVALUATOR_FACTS_INVALID), it is never coerced or
  converted implicitly, and it is NEVER reported as EVALUATOR_CONDITION_NOT_SATISFIED.
- Payload validation is authoritative in E2-A and runs at evaluation time against the published
  payload, regardless of what any store validated at write time.
- An unknown parameter_evaluator_type fails closed (EVALUATOR_UNKNOWN).
- A malformed, incomplete or type-invalid payload fails closed (EVALUATOR_PAYLOAD_INVALID).
- A required business fact that is missing, type-invalid, or supplied in a unit/currency/basis
  incompatible with the one the payload declares fails closed (EVALUATOR_FACTS_INVALID).
- A WELL-FORMED evaluation that simply is not satisfied is ordinary nonqualification
  (EVALUATOR_CONDITION_NOT_SATISFIED). WELL-FORMED is a precondition on the INPUT, not a description
  of the outcome: every required fact is present, correctly typed AND
  unit/currency/basis-compatible, so the declared comparison was actually performed and legitimately
  returned false.
- NO arbitrary executable expression language. No eval/exec, no user-authored code, scripts, SQL,
  lambda strings, regex-as-policy, template expansion or any other Turing-complete or
  injection-capable condition mechanism. Conditions are declarative data interpreted by registered,
  reviewed evaluator code only.
```

## 14. Outcome, status and reason taxonomy

Two orthogonal dimensions on the result. Never collapse them into a single boolean.

```text
outcome:            ALLOW | DENY
resolution_status:  RESOLVED | FAIL_CLOSED
```

`ALLOW` is only ever valid with `RESOLVED`. `FAIL_CLOSED` always implies `DENY`. Uncertainty is
never converted into permission.

Reasons exist at two levels, and both are recorded (section 16):

```text
PATH-LEVEL REASON      why one particular candidate path did not qualify, or at which stage it
                       could not be completed. A path-level reason NEVER by itself decides the
                       result.
RESULT-LEVEL REASON    the single decisive reason for the whole resolution, chosen by section 15.3.
```

### 14.1 Path-level nonqualification reasons (normal; contribute to DENY + RESOLVED)

```text
ASSIGNMENT_NOT_EFFECTIVE            valid lineage, no effective assignment version at as_of (gap)
ASSIGNMENT_NOT_ACTIVE               effective assignment version has active_flag = false
ASSIGNMENT_TARGET_NOT_THIS_PERSON   person_id differs, or the position's incumbent at as_of is
                                    someone else
ROLE_NOT_EFFECTIVE                  referenced role has lineage but no effective version at as_of
ROLE_NOT_ACTIVE                     effective role version has active_flag = false
RULE_NOT_EFFECTIVE                  valid lineage, no effective rule version at as_of (gap)
RULE_NOT_ACTIVE                     effective rule version has active_flag = false
RULE_SCOPE_NOT_MATCHED              rule scope operand supported, well formed, does not match
ASSIGNMENT_SCOPE_NOT_MATCHED        assignment scope operand supported, well formed, does not match
SCOPE_COMPOSITION_NOT_SATISFIED     both operands well formed; their intersection cannot be
                                    satisfied by this context
EVALUATOR_CONDITION_NOT_SATISFIED   threshold/band/set condition legitimately not met
OTHER_NONQUALIFICATION              THE ONE BOUNDED FALLBACK. Authoritative state was completely
                                    and unambiguously resolved, and this candidate does not
                                    qualify for a well-understood reason for which no reason above
                                    precisely applies. The reasons above remain authoritative and
                                    MUST be used wherever they apply. Every use carries a
                                    deterministic kernel-generated explanation. See section 27.
```

### 14.2 Result-level DENY + RESOLVED reasons

```text
AUTHORITY_NOT_ACTIVE          the requested authority resolved to exactly one effective version and
                              that version is explicitly inactive (short-circuit, section 15.3)
EMPLOYMENT_NOT_ACTIVE         employment state resolved unambiguously to a non-active state
                              (INACTIVE / ON_LEAVE / LEFT) (short-circuit, section 15.3)
NO_CANDIDATE_ASSIGNMENT       the authority and its rules/roles were established, and no assignment
                              candidate targeted this person at all
NO_QUALIFYING_PATH            candidate paths existed and none qualified; used when the
                              nonqualifying paths do not share one single path-level reason
<a path-level reason>         when EVERY nonqualifying path and partial evaluation shares exactly
                              one path-level reason, that reason is promoted to the result level
                              (section 15.3), which is what makes a denial legible
```

### 14.3 DENY + FAIL_CLOSED reasons

```text
ACTOR_PERSON_PROVIDER_NOT_CONFIGURED     no authoritative actor-person provider is bound (9.6)
HR_REFERENCE_PROVIDER_NOT_CONFIGURED     no authoritative HR provider is bound (9.6)
ACTOR_PERSON_MAPPING_MISSING
ACTOR_PERSON_MAPPING_AMBIGUOUS
HR_REFERENCE_UNAVAILABLE
HR_REFERENCE_STALE
EMPLOYMENT_STATE_MISSING
EMPLOYMENT_STATE_AMBIGUOUS
POSITION_STATE_MISSING
POSITION_STATE_AMBIGUOUS
INCUMBENCY_MISSING
INCUMBENCY_AMBIGUOUS
ORG_UNIT_STATE_MISSING
ORG_UNIT_STATE_AMBIGUOUS
ORG_HIERARCHY_UNRESOLVABLE
AUTHORITY_CODE_NOT_CONFIGURED      no grant-eligible-by-lineage version establishes the requested
                                   authority_code at as_of, including inside a valid gap (11.5)
AUTHORITY_CONFIGURATION_UNAVAILABLE   provider error, timeout, or completeness = UNAVAILABLE (9.3.3)
AUTHORITY_VERSION_AMBIGUOUS
AUTHORITY_LINEAGE_CONTRADICTORY
AUTHORITY_REFERENCE_DANGLING
PUBLICATION_PROVENANCE_INVALID
ASSIGNMENT_TARGET_INVALID          neither or both of person_id / position_id
SCOPE_SEMANTICS_UNSUPPORTED
SCOPE_CONTEXT_MISSING
EVALUATOR_UNKNOWN
EVALUATOR_PAYLOAD_INVALID
EVALUATOR_FACTS_INVALID
INTERNAL_CONTRACT_VIOLATION        a kernel invariant was violated; never degrade to a plain DENY
```

### 14.4 Three deliberate distinctions, recorded so a later agent does not "simplify" them away

```text
1. KNOWN-AND-NO versus NOT-KNOWN.
   An UNAMBIGUOUSLY RESOLVED non-active employment state, and an unambiguously INACTIVE effective
   version of any of the four families, are normal RESOLVED outcomes. A MISSING, AMBIGUOUS or
   CONTRADICTORY state is FAIL_CLOSED. The difference is whether the system knows the answer, not
   whether the answer is unfavourable.

2. ABSENT GRANT versus UNKNOWN QUESTION.
   A valid gap in an Assignment, Rule or Role lineage means there is no grant right now: normal
   nonqualification. A valid gap in the REQUESTED authority's lineage means the question itself
   cannot be established: FAIL_CLOSED, AUTHORITY_CODE_NOT_CONFIGURED (11.5).

3. INACTIVE versus INEFFECTIVE.
   These are separate conditions with separate reason codes for every family. Never report one as
   the other, and never merge them into a single "not applicable" code; the evidence must show
   which of the three grant-eligibility conditions failed.
```

## 15. Multiple paths, relevance and aggregation (F-03)

### 15.1 Multiplicity is not ambiguity

A person may legitimately hold the same authority through more than one complete, valid path — for
example a person-based assignment to one Business Authority Role and a position-based assignment to
another, where both roles carry the same authority under rules whose composed scope and parameters
are both satisfied. **This is a normal, supported outcome, not corruption.**

```text
AMBIGUITY / CORRUPTION means contradictory or irreconcilable authoritative state for ONE fact:
    two effective versions of the same object's current asserted lineage at the same instant, a
        duplicate start, or an explicit overlap (11.4);
    two current incumbents of one position where joint occupancy is not supported;
    a broken, forked or contradictory publication lineage;
    two conflicting mappings from one actor to a canonical person.

MULTIPLE QUALIFYING PATHS means several independently valid grants of the same authority. It is
ALLOW + RESOLVED, and EVERY qualifying path is retained as evidence.
```

### 15.2 Relevant authoritative state

```text
RELEVANT authoritative state for a resolution is every fact the kernel must read - or must have
PROVED it need not read - in order to decide this (actor, authority_code, business_context, as_of).
```

```text
- A record is PROVABLY IRRELEVANT only when the exclusion can be established WITHOUT relying on any
  defective, ambiguous, contradictory or semantically interpreted field. Safe exclusions are
  structural and identity-only, and are evaluated over RAW published facts exactly as discovery is
  (9.3.1):
      * a Business Authority object NONE of whose raw published versions/assertions - retracted or
        not, active or not, effective or not - carries the requested authority_code;
      * a Rule object NONE of whose raw published versions/assertions carries the requested
        authority's stable id as its reference;
      * an Assignment object NONE of whose raw published versions/assertions carries any candidate
        role's stable id as its reference.
- Retraction is NOT an irrelevance test. An object whose only code-bearing or reference-bearing
  version is retracted remains RELEVANT and must be validated, because the retraction assertion
  itself may be the defect (9.3.1, 11.6). Excluding it here would reintroduce, at the kernel, the
  very prefiltering the provider is forbidden to do.
- If the exclusion WOULD depend on the defective field itself - for example, an object with two
  duplicate effective versions where which one is effective determines whether it references a
  candidate role, or an object excluded only because a malformed retraction appears to remove its
  reference - the record is NOT provably irrelevant.
- If relevance itself cannot be established safely, FAIL CLOSED. Do not guess relevance in order to
  reach an ALLOW.
- A defect in a lineage or dependency that IS relevant to this actor + requested authority +
  candidate graph can NEVER be masked by another, valid path.
```

### 15.3 Total aggregation precedence

Evaluated in this exact order. This is total: every resolution lands in exactly one branch.

```text
1. Any FAIL_CLOSED defect in relevant authoritative state or in a relevant dependency
       -> DENY + FAIL_CLOSED, with that defect's reason code.
          A qualifying path elsewhere does NOT rescue it. If more than one defect exists, the
          reported result_level_reason is the reason code of the FIRST defect under the TOTAL
          fail-closed defect order of section 15.5 - not merely the first stage, and never the first
          one the traversal happened to encounter. Every other detected defect is retained in the
          partial-evaluation evidence (16.4), ordered by that same total order.

2. Otherwise, one or more COMPLETE QUALIFYING paths exist
       -> ALLOW + RESOLVED. All qualifying paths are retained, in the deterministic order of 15.4.

3. Otherwise
       -> DENY + RESOLVED, with the result-level reason chosen as follows:
          a. the two permitted short-circuits, if they occurred: an unambiguously non-active
             employment state (EMPLOYMENT_NOT_ACTIVE) or an unambiguously inactive effective version
             of the REQUESTED authority (AUTHORITY_NOT_ACTIVE). Both are safe short-circuits because
             no path can qualify regardless, so the remainder of the candidate graph becomes
             provably irrelevant under 15.2 without relying on any defective field;
          b. else, if no assignment candidate targeted this person at all, NO_CANDIDATE_ASSIGNMENT;
          c. else, if every nonqualifying path and partial evaluation shares exactly one path-level
             reason, that reason, promoted to result level;
          d. else NO_QUALIFYING_PATH.
```

Normal nonqualification — inactive, ineffective within a valid gap, scope miss, parameter miss,
absent assignment or rule — is **never** a defect and never triggers branch 1.

### 15.4 Determinism

Ordering is a total order computed by the kernel from canonical identifiers and version numbers —
for example lexicographic over

```text
(business_authority_role_id, business_authority_role_version,
 business_authority_id,      business_authority_version,
 business_authority_rule_id, business_authority_rule_version,
 business_authority_assignment_id, business_authority_assignment_version)
```

The kernel must **never** depend on provider or SQL row order, and must never select an arbitrary
"first" path when more than one qualifies. A deterministic-ordering test must prove that shuffling
every provider's return order does not change the result or any evidence ordering.

### 15.5 Total fail-closed defect order (F-08)

Section 12.2 orders *stages*. That is not enough: two relevant defects with different reason codes
can arise at the same stage, and without a further tie-break the reported reason would depend on
provider order, SQL row order, dictionary iteration order, path traversal order or concurrency. This
section defines the **total order** that removes that dependence.

Every fail-closed defect the domain can emit carries a **canonical defect sort key**, compared
lexicographically in this exact field order:

```text
1. stage_rank
       the S0..S9 numeric rank from section 12.2 at which the defect was detected. Lower first.

2. canonical_subject_key
       a deterministic ordinal tuple identifying WHAT the defect is about. Exactly one of the three
       forms below applies to any given defect, and the form itself carries the first ordinal
       component so the three forms are mutually orderable:

       (a) OBJECT-BACKED SUBJECT           subject_form_rank = 0
           (object_family_rank, stable_object_id, object_version)
           where object_family_rank is the fixed closed ranking
               0 BUSINESS_AUTHORITY
               1 BUSINESS_AUTHORITY_ROLE
               2 BUSINESS_AUTHORITY_RULE
               3 BUSINESS_AUTHORITY_ASSIGNMENT
           object_version is included ONLY when it has been established; when the defect concerns
           the object's lineage as a whole rather than one version, object_version sorts as the
           empty/lowest value so lineage-level defects precede version-level defects for the same
           object.

       (b) PATH-BACKED SUBJECT             subject_form_rank = 1
           a canonical path key assembled ONLY from the stable IDs and versions ALREADY established
           for that candidate path, in the fixed field order of section 15.4, with unestablished
           trailing fields sorting as the empty/lowest value.

       (c) PROVIDER / ABSENCE / DEPENDENCY SUBJECT     subject_form_rank = 2
           (subject_token, canonical_request_key)
           where subject_token comes from a CLOSED, fixed-rank vocabulary - for example
               ACTOR_PERSON_PORT, HR_EMPLOYMENT_PORT, HR_POSITION_PORT, HR_INCUMBENCY_PORT,
               HR_ORG_UNIT_PORT, AUTHORITY_CONFIGURATION_PORT, KERNEL_INVARIANT
           and canonical_request_key is built only from the canonical request identifiers already
           established: (authority_code, actor_user_public_id, person_id-if-established,
           and the canonical scope identity of the business context).

       PROHIBITED as any component of canonical_subject_key: a process/memory address, an object
       identity hash, a provider row number, a query or iteration position, a wall-clock reading, a
       randomly generated UUID, a thread/task id, or any other value not derived from stable,
       reproducible domain data.

3. reason_code_rank
       the ordinal of the fail-closed reason code, taken from a CLOSED, EXPLICIT, IMMUTABLE
       reason-rank table declared once in the reason registry. The rank is an explicit integer
       assigned per code; it is NOT the code's alphabetical spelling and NOT its Python enum
       definition order by accident. Adding a reason code requires assigning it a rank deliberately.

4. evidence_discriminator                (used only if 1-3 are still equal)
       a final canonical discriminator built ONLY from stable, deterministic evidence fields already
       present on the defect record - for example the canonical (object_id, object_version) pairs of
       the participating dependency, the canonical scope identity, or the evaluator type - in a
       fixed declared field order. It must contain no nondeterministic value of any kind.
```

Normative consequences:

```text
- The tuple MUST be total for every fail-closed defect the domain can emit. If an implementation
  finds two distinct defects with an equal key, that is a contract gap in this section, to be raised
  and corrected here - never resolved at runtime by "whichever came first".
- result_level_reason on a DENY + FAIL_CLOSED result is EXACTLY the reason_code of the first defect
  under this total order (15.3 branch 1).
- Provider order, SQL row order, dictionary/set iteration order, path traversal order and
  concurrency MUST NOT affect it. The kernel computes the key from domain data and sorts; it never
  reports "the first defect observed".
- The SAME total order is used to order the partial/failed evaluation evidence (16.5), so the
  result-level reason is always the reason of the FIRST item in that ordered collection. There is
  deliberately only one order, so the two can never disagree about which defect is first. Any
  alternative evidence ordering an implementation wishes to expose must be an ADDITIONAL view, never
  a replacement, and must not be the basis of result_level_reason.
- Nonqualification reasons (14.1) are not defects and never enter this order; they are ordered with
  their paths under 15.4/16.5.
```

## 16. Evidence contract (F-06)

Negative outcomes are **first-class**. A resolution result must retain deterministic evidence
sufficient to prove exactly why it allowed, denied or failed closed, and what authoritative state
was used. "It returned DENY with a reason code" is not sufficient evidence and is a blocking defect.

The result carries four evidence collections plus a result-level header.

### 16.1 Result header — always present

```text
outcome, resolution_status, result_level_reason        section 14 / 15.3
authority_code requested
as_of                                 the single authoritative instant
authenticated actor reference          application-user public identifier; never a credential
established_state                      what WAS successfully established before the result was
                                       reached, and the exact stage at which evaluation stopped:
     canonical person_id                        (if S1 succeeded)
     employment-state version/reference          (if S2 succeeded)
     requested authority (object_id, version)    (if S3 succeeded), plus its active/effective
                                                 evaluation
     candidate counts                            rules discovered, roles referenced, assignments
                                                 discovered, complete paths evaluated
     canonical_snapshot_at value(s) relied on
     last_stage_reached                          S0..S9 per section 12.2
business_context as evaluated          scope and the declared facts actually used
```

`established_state` is what makes a `DENY + RESOLVED` with **zero** complete paths explainable: it
records what was established and therefore why no grant path could exist.

### 16.2 Qualifying paths — for every path that granted

All four object/version pairs. This is `ORA-001`'s requirement as corrected by
`PF_1A_AUTHORITY_CONFIGURATION_MODEL.md` (C3-3); omitting any one of the four is a blocking defect.

```text
business_authority_role_id,       business_authority_role_version
business_authority_id,            business_authority_version
business_authority_rule_id,       business_authority_rule_version
business_authority_assignment_id, business_authority_assignment_version
plus, for each of the four, its publication_reference_type / publication_reference_id and its
published_at, and the retracted_at of any retraction assertion that participated in establishing
the current asserted lineage - all explicitly labelled RECORDED TIME, never effective time (11.8.4)

active/effective evaluation      per object: lineage-valid, effective-at-as_of, active_flag
                                 (the three conditions of section 8.2, reported separately)
HR evidence                      employment-state version identity; Position Version identity and
                                 incumbency_id where a position path was used; Organisation Unit
                                 Version identities for every ancestry hop traversed;
                                 canonical_snapshot_at
scope evaluation                 rule operand result, assignment operand result, composed result
parameter evaluation             evaluator type and the decisive comparison
```

### 16.3 Complete nonqualifying paths — for every evaluated complete path that did not grant

A path that reached completeness (12.2) but failed at scope, parameters or an active/effective
check on an already-established object retains **exactly the same structure as 16.2** — all four
object/version pairs, HR evidence, active/effective evaluation, scope evaluation, parameter
evaluation — plus:

```text
decisive_nonqualification_reason    one path-level reason from section 14.1
```

This is what allows a scope denial or a parameter denial to be proved rather than merely asserted.

### 16.4 Partial / failed evaluations — where four pairs cannot exist

For an early `FAIL_CLOSED`, or for a candidate that could not be completed (for example a role in a
valid gap, a dangling reference, an incumbency that resolved to a different person, or an
unavailable provider), the result retains a partial-evaluation record:

```text
every successfully established evidence/version item, in the order established
   (for example: person_id and employment state established; requested authority object/version
    established; rule object/version established; role NOT established)
the exact stage that failed or was absent           last_stage_reached, per 12.2
the deterministic reason                            a path-level reason (14.1) or a fail-closed
                                                    reason (14.3)
```

```text
- NEVER fabricate the missing object/version pairs. A partial evaluation records what exists and
  names what does not; it must not emit placeholder, null-filled or guessed pairs that a later
  reader could mistake for established state.
- A partial evaluation is never silently dropped. Every candidate the kernel touched is accounted
  for in exactly one of 16.2, 16.3 or 16.4.
```

### 16.5 Ordering, exclusions and durability

```text
ORDERING
    Qualifying paths            the total order of section 15.4.
    Complete nonqualifying paths the same total order.
    Partial/failed evaluations   the TOTAL FAIL-CLOSED DEFECT ORDER of section 15.5 - the identical
                                 canonical defect sort key used to select result_level_reason. This
                                 is deliberately ONE order, not a compatible-but-separate one, so
                                 the first item in this collection and the result-level reason can
                                 never disagree about which defect is first (F-08). A partial
                                 evaluation that ended in a NONQUALIFICATION rather than a defect
                                 sorts after every defect item, ordered by (last_stage_reached ASC,
                                 then the established canonical identifiers in the 15.4 field order
                                 with unestablished fields sorting last, then reason_code_rank).
    Evidence items within a path ordered by the fixed field order of 16.2.
    All ordering is computed by the kernel from stable domain data and is independent of provider
    order, SQL row order, iteration order, traversal direction and concurrency.

NEVER INCLUDED
    passwords, password hashes, tokens, session identifiers, any authentication secret, or any
    provider-specific identifier/field (section 7).

DURABILITY
    Evidence cited by a historical decision must remain dereferenceable and byte-identical after
    later versions, retractions and corrections exist. E2-A must include a test that publishes
    further synthetic versions (and a retraction, and a correction) after capturing a result, then
    proves every cited (object_id, object_version) still dereferences to exactly the content it had
    at decision time.
```

E2 does not itself persist business decisions or their evidence; it produces the evidence structure
that a future consumer package will store alongside its own decision record.

## 17. Explicit exclusions (PF-1A-E2-A)

```text
- SQLAlchemy persistence for any new authority object                (PF-1A-E2-B)
- any Alembic migration                                              (PF-1A-E2-B)
- a database-backed authority repository or provider                 (PF-1A-E2-B)
- registration in backend/app/models_metadata.py                     (PF-1A-E2-B)
- ANY HTTP route, request/response schema or API surface             (later consumer package)
- a production read/write authority administration API               (PF-1A-E3)
- Configuration Change proposal / authorization / activation         (PF-1A-E3)
- activation-time risk recomputation implementation                  (PF-1A-E3)
- preventive self-escalation workflow implementation                 (PF-1A-E3)
- protected meta-authority administration workflow                   (PF-1A-E3)
- authority administration UI                                        (later)
- an AUTHORITATIVE actor-person provider or live HR provider          (later authorized package)
- production authority bootstrap, or choosing any real holder        (blocked by Q-10)
- resolution of Q-10                                                 (PBL governance decision)
- delegation                                                          (later)
- HR-change lifecycle automation (leaver/transfer suspension,
  pending-approval reassignment)                                      (later)
- SharePoint adapter implementation                                   (HR-reference capability)
- Plum adapter implementation                                         (HR-reference capability)
- Source Binding / reconciliation implementation                      (HR-reference capability)
- consumer business-workflow retrofit (credit assessment/approval,
  Commercial Offer approval, T&C deviation, Work Order release,
  Customer Master activation)                                         (later packages)
- any frontend change                                                 (out of scope)
- production authority assignments or any real authority seed data    (out of scope)
- any change to PF-1A-E1 runtime, contract, permissions or tests      (section 6)
```

## 18. Deterministic test strategy

E2-A is a pure kernel with reference providers, so its tests are fully deterministic and require no
database. All of the following must exist.

```text
DIRECT E2-A MALFORMED-INPUT COVERAGE  (the PERMANENT class B1 coverage of section 9.7)
    These cases supply malformed material DIRECTLY to E2-A through the reference/synthetic provider,
    which can express any shape section 9.3.4 leaves DTO-optional. Several of them are shapes a
    relational store deliberately rejects at write time, so this is the ONLY place E2-A's
    provider-neutral fail-closed classification of them can be proved. They are mandatory
    permanently and must never be deleted, skipped, xfailed or weakened on the grounds that "the
    database prevents that" (9.7). Each case states the BOUNDARY it exercises, and a test that
    exercises a different boundary than the one named does not discharge the obligation:

    Each fixture below carries a STABLE FIXTURE NAME and the E2-B manifest ID it discharges, so a
    reviewer can check the two documents against each other mechanically. One fixture name covers
    exactly one malformed shape; a name covering two shapes is how F-10.1 happened.

    B1, PURE KERNEL BOUNDARY - well-formed material reaches the kernel, which classifies it:
        DUPLICATE-OBJECT-VERSION            [B1-01] two entries in one object's versions[] carrying
            the same object_version -> AUTHORITY_LINEAGE_CONTRADICTORY (9.3.3, 11.6);
        ASSIGNMENT-TARGET-BOTH              [B1-02] an assignment payload carrying BOTH person_id
            and position_id -> ASSIGNMENT_TARGET_INVALID at stage S7 (I-4);
        ASSIGNMENT-TARGET-NEITHER           [B1-03] an assignment payload carrying NEITHER ->
            ASSIGNMENT_TARGET_INVALID at stage S7 (I-4);
        INTERVAL-END-BEFORE-START           [B1-04] declared_effective_to < effective_from ->
            AUTHORITY_LINEAGE_CONTRADICTORY, from the 11.4 NONSENSICAL DECLARED INTERVAL pre-check
            (I-6);
        INTERVAL-END-EQUALS-START           [B1-05] the empty interval, declared_effective_to ==
            effective_from -> AUTHORITY_LINEAGE_CONTRADICTORY, same pre-check (I-6);
        PROVENANCE-ABSENT-PUBLISHED-AT      [B1-08a] a version carrying no published_at ->
            PUBLICATION_PROVENANCE_INVALID (11.6, 11.7);
        PROVENANCE-ABSENT-RETRACTED-AT      [B1-08b] a retraction assertion carrying no
            retracted_at -> PUBLICATION_PROVENANCE_INVALID (11.6, 11.7);
        PROVENANCE-ABSENT-TYPE              [B1-09a] a published version whose
            publication_reference_type is ABSENT ALTOGETHER, with publication_reference_id and
            published_at present and well formed, so the ONLY defect under test is the missing type
            -> DENY + FAIL_CLOSED, PUBLICATION_PROVENANCE_INVALID, with the ordinary deterministic
            failure evidence of 16.4 (established items, the exact failed stage, the deterministic
            reason, no fabricated object/version pairs) and the ordinary 15.5 defect ordering. A
            COMPANION CASE applies the same absence to a RETRACTION ASSERTION's
            publication_reference_type and expects the identical classification. This fixture is
            MANDATORY and is the F-10.1 closure: it is NOT discharged by
            PROVENANCE-UNKNOWN-TYPE below, because a kernel that validates only membership in the
            two defined values passes that one and fails this one. It is a PURE KERNEL fixture, not
            a DTO one - publication_reference_type is DTO-OPTIONAL and OPEN (9.3.4) precisely so
            this material CAN be constructed and CAN reach the kernel;
        PROVENANCE-ABSENT-REFERENCE-ID      [B1-09b] a published version whose
            publication_reference_id is absent, with a valid publication_reference_type present ->
            PUBLICATION_PROVENANCE_INVALID (11.6, 11.7);
        PROVENANCE-UNKNOWN-TYPE             [B1-10] a publication_reference_type PRESENT but outside
            the two defined values -> PUBLICATION_PROVENANCE_INVALID (11.6, 11.7).

    HOW THE MALFORMED PROVIDER-NEUTRAL INPUT REACHES THE KERNEL'S VALIDATION SEAM. The kernel
    consumes a normalized domain object, not a wire DTO, so the route matters and is fixed here
    rather than left to the implementer. LineageMaterial (9.3.2) IS that provider-neutral normalized
    object: it is what get_lineage returns and what the kernel receives. Its version and retraction
    records carry publication_reference_type as a DTO-OPTIONAL, OPEN value (9.3.4). The
    reference/synthetic provider therefore constructs LineageMaterial with that field absent and
    returns it from get_lineage unchanged; no decoding step, normalization step, defaulting step or
    convenience validator sits between that construction and the kernel's provenance validation
    (11.7, 11.8.3), which is where the state is classified. If an implementation introduces an
    intermediate normalization layer between the port and the kernel, that layer MUST pass the
    absent value through untouched, and the fixture MUST still be asserted through the kernel entry
    point - not against the layer. Relocating this fixture to DTO-only rejection is explicitly
    PROHIBITED: this contract requires pure-kernel coverage for it, because 11.6/11.7 already assign
    the state a semantic reason code, and a DTO that rejected it would make that rule permanently
    unreachable and untestable (9.3.4, and the class B2 fabrication prohibition in 9.7).

    B1, DTO / PORT WELL-FORMEDNESS BOUNDARY - material that cannot be constructed at all:
        VERSION-ABSENT-EFFECTIVE-FROM       [B1-06] a version record with NO effective_from -> the
            port rejects the material as ill formed and the resolution is DENY + FAIL_CLOSED /
            AUTHORITY_CONFIGURATION_UNAVAILABLE (9.3.3);
        VERSION-ABSENT-ACTIVE-FLAG          [B1-07] a version record with NO active_flag -> the
            same.
        These two are explicitly NOT kernel fixtures and must not be described as such: this
        document defines no semantic reason code for a version lacking either field, and inventing
        one to mirror a NOT NULL constraint is prohibited (9.7). The test asserts the DTO/port
        boundary rejects the material and that the resulting resolution fails closed with the
        AUTHORITY_CONFIGURATION_UNAVAILABLE code and normal partial-evaluation evidence (16.4) -
        never a placeholder value, never a substituted default, never an empty candidate set.

    ALSO PROVED DIRECTLY HERE, though these are class A shapes owed parity as well (a class A shape
    may legitimately carry a direct test too - E2-A must classify it with no store present):
        a reference to a stable identity with NO lineage material at all ->
            AUTHORITY_REFERENCE_DANGLING (11.5). Note this is the SAME provider-neutral state that a
            store's missing-stable-identity-row FK protects against, which is exactly why that FK is
            class B2 rather than B1 (9.7).

    STRUCTURAL INVARIANT ASSERTIONS, not negative fixtures, and therefore NOT class-assigned:
        stable identity never versioned;
        published version immutability, INCLUDING active_flag (no API path mutates one).

    DELIBERATELY ABSENT FROM THIS BLOCK - the class B2 shapes of section 9.7:
        a version record whose stable-identity parent row does not exist;
        a retraction record whose object stable-identity parent row does not exist;
        a rule/assignment referencing a role/authority stable identity ROW that does not exist.
        These have no distinct provider-neutral counterpart (object_id lives on the LineageMaterial
        container, 9.3.2), so there is nothing here to test. A test asserts they are absent from the
        E2-A fixture corpus, so a later agent cannot "helpfully" add a fabricated one.

NON-STORE RESOLVER / PROVIDER CONFORMANCE SCENARIOS (F-10.3, made TOTAL by F-10.3b)
    These are negative/conformance scenarios whose malformed or negative SUBJECT IS NOT stored
    authority data, so they carry NO A/B1/B2 class (9.7.0). They are nonetheless MANDATORY E2-A
    coverage, and the blocks below in this same section are where they are actually executed - the
    scenario IDs are assigned so the two documents can be checked against each other mechanically,
    not because a separate test suite is intended. Their binding per-scenario obligations, seams,
    both store answers, parity requirements and expected results are the table in
    `PF_1A_E2_B_...md` section 5.7A.

    NOTHING BELOW IS A NEW REQUIREMENT. Every scenario listed here was ALREADY stated in the
    imperative somewhere in this section or in E2-B section 9; F-10.3b assigned each an ID because
    an obligation with no ID cannot be asserted total, and twelve of them were consequently sitting
    in neither document's table. Do not add a scenario here that no current normative sentence
    requires - padding the table is the opposite error, not a safer one.

    SEVERAL OF THESE SCENARIOS LEGITIMATELY READ STORED ROWS. NS-RS-01, NS-RQ-01/02, NS-PR-03 and
    every NS-AG/NS-DO/NS-EV scenario need authority rows stored and read to reach their condition;
    in NS-RS-01, NS-RQ-01/02 and the NS-EV rows those rows are entirely VALID, and in NS-PR-03,
    NS-AG-03/04 and NS-DO-01..05 they are class A shapes already independently classified in E2-B
    5.7 and used as CONTROLLED INGREDIENTS that keep their own class. Reading a row is not being
    about a row, and SUBJ = NO does not mean every row in the fixture is valid (9.7.0). The 5.7A
    PG-DATA and SUBJ columns record the two facts separately.

        NS-AP-01..03   actor->person seam (9.1): no mapping; more than one mapping; port unbound.
                       Covered by ACTOR BOUNDARY below.
        NS-AP-04       actor->person TRUST BOUNDARY (9.1, 7.1): no client-supplied person_id, and no
                       other client-controlled identity hint, can influence the identity authorized.
                       Covered by ACTOR BOUNDARY below, and asserted again against the wired path in
                       E2-B 9. Parity is NO: a surface/trust assertion has no second outcome to
                       compare, and it is asserted independently on both sides.
        NS-HR-01..12   HR reference seam (9.2): port unbound; unavailable; stale; employment state
                       missing/ambiguous; position state missing/ambiguous; incumbency
                       missing/ambiguous; org unit state missing/ambiguous; org hierarchy
                       unresolvable. Covered by ACTOR BOUNDARY, POSITION ASSIGNMENT and the
                       ancestry cases in SCOPE AND COMPOSITION below.
        NS-RQ-01       request/scope input seam (12): a non-GLOBAL scope operand whose required
                       canonical scope the business context does not supply -> SCOPE_CONTEXT_MISSING.
                       The stored rule/assignment is VALID and is read normally. Covered by SCOPE
                       AND COMPOSITION below.
        NS-RQ-02       request/evaluator input seam (13): a required business fact absent, of the
                       wrong type, or supplied in a unit/currency/basis INCOMPATIBLE with the one
                       the stored payload declares -> EVALUATOR_FACTS_INVALID. The stored evaluator
                       and payload are VALID. Covered by EVALUATORS below.
        NS-PT-01       authority configuration PORT seam (9.3.3), transport rather than data: a
                       raised provider error, a timeout, completeness = UNAVAILABLE, and a truncated
                       read presented as complete -> AUTHORITY_CONFIGURATION_UNAVAILABLE, never an
                       empty candidate set and never DENY + RESOLVED. Covered by the final case in
                       LINEAGE AND CLOSURE below.
        NS-PR-01       provider reachability seam (9.6): the reference/synthetic actor, person and
                       HR providers are TEST-ONLY and production-unreachable - not importable from
                       or reachable through any production module or the production wiring, and not
                       selectable by any environment variable, settings flag, feature toggle or
                       dependency override. Covered by SECURITY / BOUNDARY below. Parity NO:
                       structural assertion, no second side; asserted on both sides independently.
        NS-PR-02       production composition seam (9.6, E2-B 5.3): a production composition lacking
                       an authoritative actor-person / HR provider either REFUSES TO COMPOSE or
                       returns DENY + FAIL_CLOSED with ACTOR_PERSON_PROVIDER_NOT_CONFIGURED /
                       HR_REFERENCE_PROVIDER_NOT_CONFIGURED on every call - whichever option the
                       implementation chose, asserted explicitly. Distinct from NS-AP-03/NS-HR-01,
                       which assert the REASON CODE for an unbound provider in a test composition.
                       Primarily an E2-B obligation; covered here by SECURITY / BOUNDARY. Parity NO.
        NS-PR-03       provider FACT-FIDELITY seam (9.3.1, 9.5): a provider that supplies JUDGEMENTS
                       instead of FACTS - prefiltering to "the effective row", computing closure,
                       effectiveness, ranking or deduplication, or applying any excluded discovery
                       predicate - is REJECTED by a conformance test. Covered by PROVIDER CANNOT
                       HIDE A DEFECT in LINEAGE AND CLOSURE, and by the excluded-predicate cases in
                       RAW DISCOVERY AND RETRACTION, below. Parity NO in the agreement sense: the
                       SAME conformance assertion runs independently against EACH provider and both
                       must pass.
        NS-RS-01       resolver / as_of seam (11.5, 12.2): the REQUESTED authority_code has no
                       grant-eligible-by-lineage version at as_of - lineage not started, ended, or
                       an as_of inside a VALID GAP -> DENY + FAIL_CLOSED,
                       AUTHORITY_CODE_NOT_CONFIGURED, the deliberate asymmetry of 11.5. EVERY STORED
                       ROW IS VALID, which is why this replaces the withdrawn authority-store
                       fixture A-12 rather than remaining one. PostgreSQL data participates and FULL
                       parity IS owed. Covered by GAP BEHAVIOUR PER FAMILY in LINEAGE AND CLOSURE
                       below - specifically its REQUESTED-authority branch, which must not be
                       confused with the three normal-nonqualification branches (V-03).
        NS-RS-02       resolution-clock seam (11.1): ONE server-captured instant governs every stage
                       of one live resolution; no component consults a second clock. Covered by
                       TEMPORAL below, and re-asserted through the wired composition in E2-B 9 where
                       real read latency between port calls makes a second clock observable.
        NS-RS-03       entry-point surface seam (10.1, 10.2, 11.8.2): resolve_current_authority
                       exposes NO as_of and no recorded-time bound; NEITHER operation exposes a
                       published_at cutoff or as-known-at parameter; the historical resolver is not
                       a live authorization path. Covered by ACTOR BOUNDARY and by RECORDED TIME's
                       "NO recorded-knowledge replay" case below. Parity NO: a parameter-surface
                       assertion, asserted independently on both sides.
        NS-RS-04       recorded-time-is-not-a-filter seam (11.8): shifting ONLY the recorded
                       timestamps of an otherwise unchanged valid lineage, keeping them valid under
                       11.8.3, changes no outcome, status, reason or path set. Covered by RECORDED
                       TIME below. Distinct from the RECONSTRUCTION cases, which are valid-shape
                       parity scenario V-09 and assert what business-effective time correctly does
                       change.
        NS-AG-01..05   aggregation and relevance seam (15.1, 15.2, 15.3): two valid qualifying paths
                       both retained in deterministic order (multiplicity is not ambiguity);
                       valid + normal-nonqualifying, with the nonqualifying path retained in full;
                       valid + RELEVANT-corrupt failing closed, the valid path NOT rescuing it;
                       IRRELEVANT-corrupt leaving the result unaffected, with its companion case
                       where irrelevance would depend on the defective field failing closed; and the
                       correct RESULT-LEVEL reason when no path qualifies. Covered by MIXED PATHS
                       AND AGGREGATION below. NS-AG-03/04 COMPOSE a class A shape but are not class
                       A: the stored shape's own storage and parity obligations are discharged in
                       E2-B 5.7, and what these assert is the aggregation/relevance rule over it.
        NS-DO-01..06   deterministic defect ORDER seam (15.4, 15.5): same-stage two-defect
                       selection; one subject carrying two reason codes; cross-family ordering;
                       shuffled provider order, reversed traversal and repeated runs producing
                       byte-identical output; the first ordered partial/failed item always carrying
                       exactly the result_level_reason; and rank TOTALITY over 14.3. Covered by
                       TOTAL FAIL-CLOSED DEFECT ORDER below. NS-DO-06 owes no parity (it asserts a
                       property of the declared rank tables) and needs no stored row.
        NS-EV-01..07   evidence-contract seam (16): ALLOW evidence carrying all four pairs and the
                       per-object, HR, scope and parameter evaluations; COMPLETE NONQUALIFYING
                       evidence with its decisive reason, proved for a scope denial and a parameter
                       denial; PARTIAL evidence with the established items, the exact failed stage
                       and NO fabricated pairs; a zero-path DENY + RESOLVED still explaining itself;
                       one-collection membership and deterministic ordering under shuffled provider
                       output; no secret, credential or provider-specific identifier anywhere; and
                       durability across later versions, a retraction and a correction. Covered by
                       EVIDENCE below. NS-EV-07 shares its seeded state with valid-shape scenario
                       V-09 but asserts a different thing - V-09 asserts what the historical
                       resolver RECONSTRUCTS, NS-EV-07 asserts that captured evidence stays
                       byte-identical while that reconstruction changes (11.8.1); neither discharges
                       the other.
        NS-K-01        pure-kernel invariant seam (11.4a): the SINGLE-EFFECTIVE-VERSION theorem.
                       EXECUTABLE OBLIGATION, three parts, all mandatory:
                         (a) an enumerative/property test over a declared, bounded family of lineage
                             shapes - every combination of up to N versions with NULL and non-NULL
                             declared ends, distinct starts, and each of the boundary instants of
                             the TEMPORAL block below - asserting that for every shape passing the
                             duplicate-start, nonsensical-interval and explicit-overlap conditions,
                             AT MOST ONE version of the current asserted lineage is EFFECTIVE;
                         (b) a defensive-branch test that reaches the residual clause of 11.6 by
                             injecting a fabricated internal state directly (it is unreachable
                             through any port, which is the point) and asserts the result is
                             DENY + FAIL_CLOSED with result_level_reason AUTHORITY_VERSION_AMBIGUOUS
                             and ordinary 16.4 failure evidence - proving the guard exists, is
                             wired, and has not been removed as dead code;
                         (c) an assertion that AUTHORITY_VERSION_AMBIGUOUS carries an explicit
                             declared reason_code_rank (15.5 totality), even though no provider can
                             produce it.
                       This scenario replaces the withdrawn authority-store fixture A-03. No store
                       participates; no parity is owed.
        NS-K-02        pure-kernel invariant seam: INTERNAL_CONTRACT_VIOLATION. A violated kernel
                       invariant that is NOT authority-version multiplicity fails closed with that
                       code and is never degraded to a plain DENY (14.3). No store participates; no
                       parity is owed.

    Forty-six scenarios in ten seam groups. A coverage test asserts every scenario ID above has an
    executing E2-A test, that no scenario ID appears in the A/B1/B2 manifest or in the V-list, and
    that the three groups together are disjoint and exhaustive over the whole negative, valid-shape
    and conformance corpus.

ACTIVE STATE (F-01)   (VALID-SHAPE parity scenarios V-05 and V-06; the requested-authority
                       fail-closed cases below are class A fixtures or NS-RS-01, as named there)
    for EACH of the four families independently:
        effective + active                  -> contributes to a grant;
        effective + INACTIVE                -> deterministic nonqualification with the family's own
                                               *_NOT_ACTIVE reason, NEVER fail closed;
        an inactive version still closes its predecessor in derived closure;
    requested authority effective + inactive -> DENY + RESOLVED / AUTHORITY_NOT_ACTIVE;
    requested authority missing/ambiguous/contradictory -> FAIL_CLOSED with the correct code;
    active_flag is never inferred from effective time, and effective time is never inferred from
        active_flag (a version that is inactive but effective, and one that is active but not yet
        effective, produce DIFFERENT reason codes).

TEMPORAL   (the boundary shapes are VALID-SHAPE parity scenarios V-02 and V-07; the clock case is
            NON-STORE scenario NS-RS-02 - E2-B 5.7A)
    exactly at effective_from; one tick before; one tick before asserted_effective_to; exactly at
    asserted_effective_to; adjacent versions meeting at one instant (no gap, no overlap);
    a future-dated authority/rule/assignment/incumbency confers nothing before its effective_from;
    one as_of governs everything (NS-RS-02: a test proving no component consults a second clock -
        the server captures ONE current instant for a live resolution and every stage uses it).

LINEAGE AND CLOSURE (F-02, F-05, F-09)
    CLASSIFICATION NOTE (F-10.3a). The branches of the 11.4 rule do NOT all carry the same label, and
    describing them uniformly as "class A" was a defect corrected by F-10.3a. The four VALID branches
    are VALID-SHAPE parity scenarios V-01 to V-04 (E2-B 5.7), carrying no class label. Only the two
    CONTRADICTORY branches are class A negative fixtures: explicit overlap (A-01) and duplicate start
    (A-02). The end <= start branch is class B1 (B1-04/B1-05). All of them are mandatory here.
    CLOSURE, every branch of the section 11.4 asserted-interval rule, each as its own case:
        NULL-END SUCCESSOR CLOSURE   [V-01] V1 [t0, null) with V2 from t2 -> V1 asserted end = t2; an
            as_of in [t0, t2) resolves V1, an as_of at/after t2 resolves V2; V1's row is NOT mutated;
        EXPLICIT ADJACENCY           [V-02] V1 [t0, t2), V2 from t2 -> valid; no gap and no overlap;
            exactly at t2 only V2 is effective;
        EXPLICIT END BEFORE SUCCESSOR -> GAP  [V-03] V1 [t0, t1), V2 from t2, t1 < t2 -> V1 asserted
            end = t1 (NOT truncated to anything else, NOT extended to t2); [t1, t2) has no effective
            version;
        LATER REACTIVATION AFTER A GAP  [V-04] V2 becoming effective at t2 after that gap is
            REACTIVATION: the lineage stays VALID and V2 DOES grant when otherwise eligible;
        EXPLICIT END AFTER SUCCESSOR -> FAIL CLOSED  [A-01] V1 [t0, t3), V2 from t2, t0 < t2 < t3 ->
            AUTHORITY_LINEAGE_CONTRADICTORY. A test must assert this is NOT normalized into
            V1 [t0, t2) - i.e. it must fail if the rejected min(...) formula is reintroduced;
        DUPLICATE START              [A-02] two versions sharing one effective_from -> FAIL CLOSED, no
            tie-break attempted, closure not derived. CLASS A (9.7): this shape must remain STORABLE
            in any persisted store and is owed full provider parity there; no uniqueness constraint
            on (stable_object_id, effective_from) may be introduced to pre-empt it;
        END <= START                 declared_effective_to == effective_from, and
            declared_effective_to < effective_from -> FAIL CLOSED (I-6). CLASS B1 (9.7): a store may
            reject this single-row shape at write time, in which case the store proves the
            REJECTION and this direct KERNEL-boundary case remains the permanent proof of the
            semantic response. It is then excluded from that store's parity corpus. The DTO must NOT
            validate the declared_effective_to / effective_from relationship (9.3.4), or this case
            becomes unconstructible;
        EXACT HALF-OPEN BOUNDARIES   for every shape above: exactly at each start; one tick before
            each start; one tick before each asserted end; exactly at each asserted end; exactly at
            a gap start; one tick inside a gap; one tick before a gap end.
    GAP BEHAVIOUR PER FAMILY: an as_of inside a valid gap produces ASSIGNMENT_NOT_EFFECTIVE /
        RULE_NOT_EFFECTIVE / ROLE_NOT_EFFECTIVE (all normal nonqualification) [V-03], and
        AUTHORITY_CODE_NOT_CONFIGURED (fail closed) for the REQUESTED authority [NON-STORE scenario
        NS-RS-01, E2-B 5.7A] - and a gap is never reported as overlap or as a dangling reference.
        The requested-authority branch is called out separately because it is the ONLY one of the
        four that fails closed, and because it was previously carried as authority-store fixture
        A-12. It is not one: every row it reads is VALID (11.5), so there is no malformed stored
        state to classify. It keeps its full obligation - the same expected code, the same 16.4
        evidence, and FULL PostgreSQL parity in E2-B 9 - as NS-RS-01. Do NOT soften 11.5's asymmetry
        on the strength of that reclassification;
    retraction removes a version from resolution but NOT from dereference;
    correction of a shared boundary retracts and replaces every affected version;
    every contradiction listed in section 11.6 -> FAIL_CLOSED with the correct reason code;
    PROVIDER CANNOT HIDE A DEFECT [NON-STORE scenario NS-PR-03, E2-B 5.7A]: a reference provider
        that prefilters to "the effective row" is
        rejected by a conformance test - the kernel is given lineage material containing duplicate
        effective versions, an explicit overlap, a dangling retraction, an unretracted correction
        target and invalid provenance, and fails closed on each. The subject is the PROVIDER's
        fact-fidelity, not a stored shape, so it carries no class; the same assertion runs
        independently against the PostgreSQL provider in E2-B 9 PROVIDER FIDELITY;
    completeness = UNAVAILABLE, a raised provider error, a timeout, and a truncated read presented as
        COMPLETE each -> AUTHORITY_CONFIGURATION_UNAVAILABLE, never "no candidates" and never
        DENY + RESOLVED. This is NON-STORE scenario NS-PT-01 (E2-B 5.7A): the subject is the port's
        transport behaviour, not a stored shape, so it carries no A/B1/B2 class - but parity with the
        PostgreSQL-backed composition IS required and is discharged there.

RAW DISCOVERY AND RETRACTION (F-07)
    (the two "still discovered" cases over VALID retraction facts are VALID-SHAPE parity scenario
     V-08; the excluded-predicate conformance cases are NON-STORE scenario NS-PR-03; the malformed
     retraction cases are class A fixtures A-04/A-05/A-08 and A-17 - E2-B 5.7 and 5.7A)
    a version targeted by a retraction assertion is STILL DISCOVERED: an object whose ONLY version
        carrying the requested authority_code is retracted is discovered, its complete lineage
        reaches the kernel, and the kernel - not the provider - decides the outcome;
    the same, for graph expansion: an object whose ONLY reference-bearing version is retracted is
        still discovered as a candidate Rule / Assignment;
    MALFORMED RETRACTION CANNOT HIDE A VERSION: for each of a dangling retraction, a duplicated
        retraction and a retraction with impossible provenance (11.8.3), where the retraction targets
        the only requested-code-bearing version and, in a companion case, the only
        reference-bearing version - assert the object is discovered, the lineage is validated, and
        the result is FAIL_CLOSED with the lineage/provenance defect's own reason code, NOT
        AUTHORITY_CODE_NOT_CONFIGURED, NOT NO_CANDIDATE_ASSIGNMENT and NOT an empty candidate set;
    discovery applies no active_flag, effective-interval, scope, parameter, evaluator-outcome,
        provenance or "latest version" predicate - one case per excluded predicate;
    RELEVANCE: a record is excluded as irrelevant ONLY by the identity-only raw tests of 15.2; a
        companion case where the same object's irrelevance would depend on a retraction or on a
        defective field fails closed.

RECORDED TIME VERSUS BUSINESS-EFFECTIVE TIME (F-07)
    (the RECONSTRUCTION cases are VALID-SHAPE parity scenario V-09 and the durability case is
     NON-STORE scenario NS-EV-07; "never a lineage filter" is NS-RS-04; "no recorded-knowledge
     replay" is NS-RS-03; the impossible-timestamp cases are class A fixtures A-08 to A-10 -
     E2-B 5.7 and 5.7A)
    a version published AFTER a historical as_of, but asserting a business-effective interval that
        contains that as_of, DOES participate in resolve_authority_as_of(that as_of);
    a retraction recorded today DOES remove its target from resolve_authority_as_of(older as_of);
    therefore a valid later correction CHANGES what resolve_authority_as_of(old_business_time)
        reconstructs today - asserted explicitly, so the behaviour is deliberate rather than
        accidental;
    and yet a result captured BEFORE that correction still dereferences every cited
        (object_id, object_version) to byte-identical content afterwards (see EVIDENCE below) - the
        two answers are both provable and are allowed to differ;
    published_at / retracted_at are NEVER used as a lineage filter [NS-RS-04]: a test asserts that
        shifting only the recorded timestamps (while keeping them valid under 11.8.3) changes no
        outcome, status, reason or path set;
    NO recorded-knowledge replay [NS-RS-03]: a test asserts the kernel exposes no published_at
        cutoff / as-known-at parameter on either operation, that the current-authorization entry
        point exposes neither an as_of nor any recorded-time bound, and that the historical resolver
        is therefore not reachable as a live authorization path (10.2, 11.8.2);
    PROVENANCE VALIDITY: retracted_at before its target's published_at; a correcting version
        published before its target's retracted_at; and published_at decreasing across increasing
        object_version within one lineage - each -> PUBLICATION_PROVENANCE_INVALID; equal timestamps
        where ">=" is specified are accepted; and a version published TODAY asserting a business
        interval that started long ago is VALID (a backdated correction), never a provenance defect.

PERSON ASSIGNMENT
    actor -> person P; assignment to P; rule to authority A; context matches -> ALLOW + RESOLVED;
    and the corresponding negatives.

POSITION ASSIGNMENT   (the HR-supplied halves are NON-STORE scenarios NS-HR-06..09; E2-B 5.7A)
    incumbency(position, as_of) == P -> eligible;
    different incumbent (-> ASSIGNMENT_TARGET_NOT_THIS_PERSON, a normal nonqualification);
    position state missing (NS-HR-06) and ambiguous (NS-HR-07);
    no incumbent (NS-HR-08); two incumbents (NS-HR-09);
    future incumbent; expired incumbent; stale canonical snapshot - each with the correct
    outcome/status/reason.
    Note the boundary: the assignment VERSION is authority-store data (its malformed target shapes
    are class B1, B1-02/B1-03), while the INCUMBENCY answer about that position is HR-supplied and
    non-store. Do not conflate them.

ACTOR BOUNDARY   (NON-STORE scenarios NS-AP-01..04, NS-HR-01..05 and NS-RS-03; E2-B 5.7A)
    missing mapping (NS-AP-01); ambiguous mapping (NS-AP-02);
    UNBOUND actor-person provider -> ACTOR_PERSON_PROVIDER_NOT_CONFIGURED (NS-AP-03);
    UNBOUND HR provider -> HR_REFERENCE_PROVIDER_NOT_CONFIGURED (NS-HR-01);
    unavailable HR reference (NS-HR-02); stale HR reference against a SUPPLIED staleness threshold,
        inventing no default value (NS-HR-03);
    employment state missing (NS-HR-04) and ambiguous (NS-HR-05);
    a test proving the CURRENT authorization entry point exposes no as_of parameter (NS-RS-03);
    a test proving no client-supplied person_id, and no other client-controlled identity hint, can
        influence the identity authorized (NS-AP-04) - the actor -> canonical person mapping is a
        trusted server/provider boundary (7.1, 9.1) and no caller may reach across it.

SCOPE AND COMPOSITION (F-03)
    (the valid operand and composition cases are VALID-SHAPE parity scenarios V-10 and V-11;
     A-15 is the class A stored-value fixture; NS-RQ-01 and NS-HR-10..12 are non-store)
    each operand alone: GLOBAL; exact match; exact mismatch; missing required context
        (NON-STORE NS-RQ-01 -> SCOPE_CONTEXT_MISSING: the stored operand is well formed and the
        defect is in the REQUEST); unsupported scope_type VALUE on a stored rule (class A fixture
        A-15 -> SCOPE_SEMANTICS_UNSUPPORTED: this one IS stored data); ancestry match and non-match;
        org unit state missing (NON-STORE NS-HR-10) and ambiguous (NS-HR-11); ancestry cycle and
        ancestry depth exhaustion (both NON-STORE NS-HR-12 -> ORG_HIERARCHY_UNRESOLVABLE);
    COMPOSITION: GLOBAL rule ∩ EXACT assignment (constrained by the assignment);
        EXACT rule ∩ GLOBAL assignment; both EXACT and equal; both EXACT and different
        (-> SCOPE_COMPOSITION_NOT_SATISFIED, normal); ancestry ∩ exact;
        a case proving there is NO union/widening behaviour.

EVALUATORS
    (the satisfaction and legitimate non-satisfaction cases are VALID-SHAPE parity scenario V-12;
     A-13/A-14 are the class A stored-value fixtures; NS-RQ-02 is non-store)
    NONE; numeric band at each boundary under each inclusivity flag;
    percentage band; exact-value set membership and non-membership - in every one of these the
    supplied facts are present, correctly typed AND unit/currency/basis-COMPATIBLE, which is what
    makes the non-match legitimate;
    malformed stored payload (class A fixture A-14 -> EVALUATOR_PAYLOAD_INVALID);
    unknown stored evaluator type (class A fixture A-13 -> EVALUATOR_UNKNOWN);
    a required business fact missing from the REQUEST, one of the wrong type, and one supplied in a
    unit/currency/basis INCOMPATIBLE with the one the stored payload declares
        (all three NON-STORE NS-RQ-02 -> DENY + FAIL_CLOSED / EVALUATOR_FACTS_INVALID with ordinary
        16.4 failure evidence; the stored evaluator and payload are valid in these cases, and only
        the supplied business_context is defective). The unit/currency/basis case is deliberately
        NOT in the V-12 list above: section 13 makes it malformed evaluator INPUT, never an ordinary
        EVALUATOR_CONDITION_NOT_SATISFIED.

MIXED PATHS AND AGGREGATION (F-03)   (NON-STORE scenarios NS-AG-01..05; E2-B 5.7A)
    valid + valid                  [NS-AG-01] -> ALLOW, BOTH paths retained, deterministic order;
    valid + normal-nonqualifying   [NS-AG-02] -> ALLOW, the qualifying path retained and the
                                      nonqualifying path retained in full under 16.3;
    valid + RELEVANT-corrupt       [NS-AG-03] -> DENY + FAIL_CLOSED (the valid path does NOT rescue
                                      it), with the qualifying path's established evidence still
                                      retained;
    IRRELEVANT-corrupt             [NS-AG-04] -> the corrupt object is provably irrelevant under
                                      15.2 by an identity-only test, so the result is unaffected
                                      (ALLOW or the ordinary denial), AND a companion test where the
                                      same object's irrelevance would depend on the defective field
                                      fails closed;
    no path                        [NS-AG-05] -> DENY + RESOLVED with the correct result-level reason
                                      (NO_CANDIDATE_ASSIGNMENT / promoted single reason /
                                      NO_QUALIFYING_PATH);
    shuffling every provider's return order, and reversing traversal direction, changes nothing.
    WHY THESE ARE NOT CLASS A (F-10.3b): NS-AG-03 and NS-AG-04 each COMPOSE a malformed stored
    object, and that object is separately a class A fixture in E2-B 5.7 with its own storability and
    parity obligations. What these five scenarios are ABOUT is the aggregation-precedence and
    relevance rules of 15.2/15.3 - that a valid path never rescues relevant corruption, and that
    irrelevance must be decidable from identity alone. Seeding a row does not discharge them.

TOTAL FAIL-CLOSED DEFECT ORDER (F-08)   (NON-STORE scenarios NS-DO-01..06; E2-B 5.7A. Each is BUILT
    FROM class A defect shapes, because those are the only shapes a store can hold - but the SUBJECT
    under test is the 15.5 total order, not the acceptance or rejection of any one row, which is why
    none of them carries a class label)
    SAME STAGE, TWO DIFFERENT DEFECTS [NS-DO-01]: two relevant Rules, one with
        PUBLICATION_PROVENANCE_INVALID
        and one with AUTHORITY_LINEAGE_CONTRADICTORY, both detected at S4 - the reported
        result_level_reason is the one selected by the section 15.5 total order, and it is the same
        in every run;
    SAME SUBJECT, TWO REASON CODES [NS-DO-02]: one object carrying two distinct fail-closed defects -
        the reason_code_rank tie-break decides, deterministically;
    ACROSS FAMILIES AT ONE STAGE [NS-DO-03]: defects on objects of different families at the same
        stage order by object_family_rank, not by discovery order;
    SHUFFLED PROVIDER ROW ORDER [NS-DO-04]: the same logical state presented in shuffled provider
        order yields an identical result_level_reason and an identical partial-evaluation ordering;
    REVERSED CANDIDATE-PATH TRAVERSAL [NS-DO-04]: traversing the candidate graph in the reverse
        direction yields an identical result_level_reason and identical evidence ordering;
    REPEATED RUNS [NS-DO-04]: running the identical scenario N times produces BYTE-IDENTICAL
        serialized ordering and result reason (no set/dict iteration, address, hash-seed or clock
        dependence);
    ONE ORDER ONLY [NS-DO-05]: the first item of the ordered partial/failed evaluation collection
        always carries exactly the result_level_reason - asserted across every multi-defect scenario,
        so the two can never disagree;
    TOTALITY [NS-DO-06]: a coverage test asserts every fail-closed reason code in 14.3 has an
        explicit reason_code_rank, and that no two distinct defects in the corpus produce an equal
        canonical defect sort key. This one needs no stored row and owes no parity: it is a property
        of the kernel's declared rank tables.

EVIDENCE (F-06)   (NON-STORE scenarios NS-EV-01..07; E2-B 5.7A. Their subject is the section 16
                   evidence contract - what a result must carry, how it must be ordered, and what it
                   must never fabricate - not a stored shape; several are driven by entirely valid
                   state and a successful ALLOW)
    every ALLOW carries all four object/version pairs, per-object active/effective evaluation, HR
        evidence, scope operand + composed results, and parameter evaluation [NS-EV-01];
    every COMPLETE NONQUALIFYING path carries the same four pairs plus its decisive reason -
        specifically proved for a scope denial and for a parameter denial [NS-EV-02];
    every PARTIAL evaluation carries the established items, the exact failed/absent stage and the
        deterministic reason, and NO fabricated pairs (a test asserts absent pairs are absent, not
        null placeholders) [NS-EV-03];
    a DENY + RESOLVED with ZERO complete paths still explains what was established and why no path
        existed (established_state populated, last_stage_reached correct) [NS-EV-04];
    every candidate touched appears in exactly one of the three collections [NS-EV-05];
    ordering of all four collections is deterministic under shuffled provider output [NS-EV-05];
    evidence remains dereferenceable after later versions, a retraction and a correction, and the
        11.8.1 asymmetry holds alongside it - the historical resolver may reconstruct a different
        answer for the same business as_of while the captured evidence is unchanged [NS-EV-07];
    no secret, credential or provider-specific identifier appears anywhere in evidence [NS-EV-06] -
        asserted on the PostgreSQL-backed composition independently as well as by parity, because a
        provider-specific identifier could only ever leak on that side.

VERIFICATION CLASS ASSIGNMENT (F-10)
    TAXONOMY SCOPE FIRST (9.7.0, F-10.3, corrected by F-10.3a/b): a coverage test partitions the
        whole negative, valid-shape and conformance corpus into exactly THREE pairwise-disjoint,
        exhaustive groups - MALFORMED AUTHORITY-STORE fixtures (subject: a malformed or
        contradictory published authority-store state), VALID-SHAPE PARITY scenarios (subject: a
        VALID stored authority state) and NON-STORE scenarios (subject: a provider, a request input,
        orchestration, the resolution clock, defect ordering, evidence, or a pure-kernel invariant).
        It asserts that every malformed authority-store fixture carries exactly one of A / B1 / B2
        and a non-"N/A" storability answer; that every valid-shape scenario carries NO class label
        and IS in the parity corpus; that every non-store scenario carries NO class label and DOES
        carry a named seam, an executable obligation and BOTH store answers; and that no item
        appears in more than one group or in none. A
        fixture whose storability answer is "N/A" while it carries a class label is the F-10.3
        defect and fails this test;
    A FAIL-CLOSED OUTCOME IS NOT A CLASS LABEL (F-10.3a): a specific assertion proves that every
        A/B1/B2 fixture seeds a state this document requires the kernel to REJECT AS INVALID, and
        that no item whose seeded rows are VALID carries a class label. NS-RS-01 is the worked
        example - valid rows, a correct DENY + FAIL_CLOSED / AUTHORITY_CODE_NOT_CONFIGURED, and no
        class;
    NON-STORE TOTALITY (F-10.3b): a coverage test asserts that every obligation this section or
        E2-B section 9 states in the imperative, and whose malformed/negative subject is not stored
        authority state, carries one of the forty-six scenario IDs - specifically including the
        actor-to-person trust boundary, synthetic/production provider reachability and fidelity, the
        server-captured live as_of and single-clock rule, the entry-point parameter surfaces,
        recorded time never acting as a filter, aggregation over multiple qualifying paths,
        relevant-corrupt state not being masked, result-level reason selection, deterministic defect
        ordering, and the complete/nonqualifying/partial evidence and evidence-ordering cases;
    every AUTHORITY-STORE negative fixture in this corpus carries EXACTLY ONE class label per
        provider (9.7):
        CLASS A   a persistable semantic contradiction - therefore also owed FULL provider parity by
                  any store that can physically hold it;
        CLASS B1  a shape a store rejects structurally, WITH a provider-neutral counterpart -
                  therefore proved HERE directly against E2-A at its NAMED boundary, proved as a
                  REJECTION by that store, and excluded from that store's parity corpus only;
        CLASS B2  a shape a store rejects structurally, with NO provider-neutral counterpart -
                  therefore proved ONLY as a store rejection, absent from this corpus entirely, and
                  carrying a written rationale in the manifest;
    no fixture carries more than one label and none carries none: a coverage test asserts the
        labelling is TOTAL and EXCLUSIVE over the MALFORMED AUTHORITY-STORE negative corpus (the
        valid-shape and non-store scenarios are covered by the TAXONOMY SCOPE assertion above and
        carry no label);
    BOUNDARY FIDELITY: every class B1 fixture names its boundary (DTO/port well-formedness, or pure
        kernel), and a test asserts the E2-A test that covers it actually exercises THAT boundary -
        a DTO-boundary fixture asserted through a kernel call, or vice versa, does not discharge the
        obligation;
    a companion assertion proves the class B1 labels are not silently self-serving - for every B1
        fixture, INCLUDING EACH OF THE FIVE SEPARATELY NAMED PROVENANCE SHAPES (B1-08a, B1-08b,
        B1-09a, B1-09b, B1-10), there is a named test in DIRECT E2-A MALFORMED-INPUT COVERAGE above,
        with a NORMATIVE expected reason code, and that test is exercised in the ordinary run rather
        than skipped or xfailed. The mapping is asserted ONE FIXTURE NAME TO ONE MANIFEST ID: a test
        that discharges two manifest IDs, or a manifest ID with no distinctly named covering test,
        fails this assertion, because that is exactly how PROVENANCE-ABSENT-TYPE went missing;
    ABSENCE IS NOT UNKNOWN-VALUE: a specific assertion proves PROVENANCE-ABSENT-TYPE and
        PROVENANCE-UNKNOWN-TYPE are two distinct executing tests over two distinct inputs, and that
        neither is skipped in favour of the other;
    B2 HONESTY: a test asserts every class B2 fixture is ABSENT from this corpus (there is nothing
        provider-neutral to assert about it) AND that its manifest entry carries a non-empty written
        rationale. A B2 entry whose rationale is missing, or amounts to "no kernel test exists", is
        a blocking finding;
    B2 RE-EXAMINATION: a test asserts the DTO-required / DTO-optional split of section 9.3.4 is
        exactly as declared there, because a change to it can turn a B2 shape into a representable
        B1 shape and would silently strip that shape of all E2-A coverage;
    the resulting labels are the manifest E2-B cites in its acceptance record (E2-B 5.7), so a
        defect class can never lose coverage by moving between packages;
    a negative test asserts that no structural convenience has been imported into this kernel's own
        fixtures: neither the reference/synthetic provider NOR the material DTOs impose any
        identity-uniqueness, XOR, interval-sanity, provenance-presence, closed-enum or referential
        restriction over the DTO-OPTIONAL fields of 9.3.4, because that would silently destroy the
        very coverage class B1 depends on. The DTO-REQUIRED fields of 9.3.4 are the deliberate,
        enumerated exception, and their rejection IS the tested boundary for the two fixtures that
        name it.

SECURITY / BOUNDARY   (the two provider-reachability cases are NON-STORE scenarios NS-PR-01 and
                       NS-PR-02; E2-B 5.7A)
    an Application/Login Role alone (including ADMIN) grants NO business authority;
    the kernel imports no E1 role constant and no E1 permission constant;
    reference/synthetic providers are unreachable from production runtime paths (section 9.6), are
        not importable from any production module or the production dependency wiring, and cannot be
        selected by any environment variable, settings flag, feature toggle or dependency override
        [NS-PR-01];
    a production composition lacking an authoritative actor-person / HR provider either REFUSES TO
        COMPOSE or fails closed deterministically with ACTOR_PERSON_PROVIDER_NOT_CONFIGURED /
        HR_REFERENCE_PROVIDER_NOT_CONFIGURED on every call, whichever option was chosen, asserted
        explicitly [NS-PR-02]; this is distinct from NS-AP-03 / NS-HR-01, which assert the reason
        code for an unbound provider inside a TEST composition;
    no code path in the package writes authority configuration.

E1 REGRESSION
    every existing E1 test passes unmodified; the E1 compatibility facts in section 6 are unchanged.
```

## 19. Acceptance criteria (PF-1A-E2-A implementation)

```text
A.  Business authority resolves by authority_code only. No person name, employee code, designation,
    position name, Business Authority Role name or Application/Login Role code appears in any
    resolution decision path.
B.  The authenticated actor is resolved to a canonical person through the provider-neutral port; no
    client-supplied person identity is ever accepted.
C.  Person-based and position-based assignments both resolve correctly, and a position assignment
    re-resolves incumbency at the same instant every time.
D.  active_flag is an immutable published value, distinct from temporal effectiveness, applied
    uniformly to all four families; grant-eligibility is exactly lineage-valid AND effective AND
    active, and each condition is separately reported. An unambiguously inactive effective version
    never fails closed; an inactive effective version of the REQUESTED authority yields
    DENY + RESOLVED / AUTHORITY_NOT_ACTIVE.                                                  (F-01)
E.  The authority configuration port supplies COMPLETE lineage material plus RAW, identity-only
    candidate discovery. Discovery matches on raw published facts and never excludes a candidate
    because of a retraction, correction, active_flag, effective interval, evaluator outcome, scope,
    provenance or "latest version" judgement; retraction assertions are returned as lineage facts,
    not applied as discovery filters. No provider prefilters to "the effective row", and conformance
    tests prove (i) the kernel detects duplicate effective versions, explicit overlap, broken
    supersession, contradictory correction/retraction assertions and invalid provenance from
    provider-supplied material, and (ii) a malformed or contradictory retraction CANNOT hide a
    requested-code-bearing or reference-bearing version. Provider errors, incomplete material and
    ILL-FORMED material (a DTO-REQUIRED field of 9.3.4 absent or ill-typed) all fail closed with
    AUTHORITY_CONFIGURATION_UNAVAILABLE and are never read as "not found"; conversely, COMPLETE
    material with an empty versions[] is a truthful answer the kernel classifies, not an error
    (9.3.2).                                                                     (F-02, F-07, F-10)
F.  Exactly one authoritative BUSINESS-EFFECTIVE as_of governs the whole evaluation, across authority
    and HR/organisation evaluation alike; the current-authorization entry point accepts no
    caller-selected instant and no recorded-time cutoff. published_at / retracted_at are recorded-time
    evidence and validation input only, never a second business clock and never a lineage filter; the
    historical resolver is corrected business-effective reconstruction under the lineage known at
    invocation, NOT recorded-knowledge replay; and impossible or contradictory recorded provenance
    fails closed per 11.8.3.                                                                  (F-07)
G.  Half-open interval semantics hold at every boundary; future-dated state confers nothing early;
    published versions are immutable; closure is derived from an append-only lineage; retracted and
    corrected versions remain dereferenceable, byte-identical, even after a later valid correction
    changes what the historical resolver reconstructs.
H.  Derived closure implements the section 11.4 asserted-interval rule exactly: a successor closes a
    NULL-ended predecessor; an explicit end earlier than the successor's start is honoured and
    creates a VALID GAP; an explicit end equal to it is valid adjacency; an explicit end LATER than
    it is a CONTRADICTORY EXPLICIT OVERLAP that fails closed and is never truncated or normalized;
    duplicate starts and end <= start fail closed. Reactivation after a gap is valid history with the
    per-family behaviour of section 11.5.                                              (F-05, F-09)
I.  The complete candidate grant path of section 12.1 is implemented; Rule scope and Assignment
    scope compose by intersection with GLOBAL as top; incompatible scopes are normal
    nonqualification; unsupported semantics and missing required context fail closed.        (F-03)
J.  Aggregation follows the total precedence of section 15.3: a fail-closed defect in RELEVANT state
    is never masked by a valid path; otherwise qualifying paths yield ALLOW; otherwise DENY +
    RESOLVED with a legible result-level reason. Relevance is established by RAW, identity-only
    tests, and unestablishable relevance fails closed.                                       (F-03)
J2. Fail-closed reason selection is TOTAL. Every defect carries the canonical defect sort key of
    section 15.5 (stage_rank, canonical_subject_key, reason_code_rank, evidence_discriminator);
    result_level_reason is exactly the reason code of the first defect under that order; the SAME
    order sequences the partial/failed evidence, so the first ordered item always carries the
    result-level reason. Provider order, SQL row order, dictionary iteration, path traversal
    direction and concurrency demonstrably do not affect it, repeated runs are byte-identical, and
    every reason code has an explicit declared rank.                                         (F-08)
K.  Parameter evaluation is registry-based and schema-validated, with explicit boundaries and units,
    and no executable expression language.
L.  Every fail-closed case in section 14.3 fails closed with the correct reason code; no uncertainty
    is converted into permission.
L2. Semantic validity is provider-neutral; verification placement is explicit. Every AUTHORITY-STORE
    negative fixture is assigned EXACTLY ONE of the three verification classes of section 9.7
    (A / B1 / B2); the assignment is TOTAL and EXCLUSIVE over the authority-store negative corpus,
    no fixture is left ambiguous, and no fixture's class, storability, expected reason or parity
    obligation is deferred to implementation time. Class B1 shapes — structurally rejected by a
    store, but representable provider-neutrally — retain mandatory, exercised direct E2-A coverage
    here (section 18, DIRECT E2-A MALFORMED-INPUT COVERAGE) with a NORMATIVE expected reason code
    and an explicitly NAMED boundary (DTO/port well-formedness, or pure kernel), the covering test
    exercises that boundary, and the fixture-name-to-manifest-ID mapping is one-to-one. Class B2
    shapes — structurally rejected, with no distinct provider-neutral counterpart because object_id
    lives on the LineageMaterial container (9.3.2) — are absent from this document's fixture corpus
    by design, carry a written rationale in the manifest, and introduce no invented reason code or
    DTO shape. No structural rejection by any store is ever treated as satisfying a semantic rule of
    this document. The section 9.3.4 DTO-required/DTO-optional split holds exactly as declared, so
    neither the reference/synthetic provider nor a DTO validator makes any class B1 shape
    unconstructible here.                                                                     (F-10)
L3. The A/B1/B2 taxonomy is SCOPED: it classifies only negative fixtures whose subject is a
    MALFORMED OR CONTRADICTORY state of the published authority-store / read-repository data
    contract (9.7.0), and a fail-closed outcome alone never makes an item one. A VALID stored shape
    is a VALID-SHAPE PARITY SCENARIO (`PF_1A_E2_B_...md` 5.7, V-01 to V-12): no class label, not a
    negative fixture, still fully parity-owed. Every other negative or
    conformance scenario — actor→person and HR provider states, authority-configuration port
    read/transport failure and provider fact-fidelity, provider reachability, request-side scope and
    evaluator input, resolver/as_of and clock behaviour, aggregation and relevance, deterministic
    defect ordering, the evidence contract, and pure-kernel invariants —
    is recorded in the NON-STORE RESOLVER / PROVIDER CONFORMANCE SCENARIOS table
    (`PF_1A_E2_B_...md` section 5.7A), carries no class label, and carries an explicit executable
    test obligation at an ALREADY-DEFINED seam together with its expected outcome, status, reason
    and evidence, BOTH store answers (does store data participate; is the malformed subject stored
    state — the latter NO on every row), and its parity requirement where one applies. That table is
    TOTAL over the non-store obligations the CURRENT normative text already mandates. No item sits
    in more than one of the three groups or in none; no classified fixture records its storability
    as "N/A"; and no new provider surface was invented in order to classify anything.
                                                                        (F-10.3, F-10.3a, F-10.3b)
L4. The residual multiplicity clause of 11.6 is DECIDED, not deferred: it is proved unreachable from
    any provider input by the section 11.4a theorem, is retained as a defensive kernel invariant
    that must not be deleted, emits AUTHORITY_VERSION_AMBIGUOUS if ever violated, and is verified by
    pure-kernel self-check NS-K-01 with all three of its executable parts. It is therefore absent
    from the authority-store negative-fixture manifest and from every parity corpus, and
    AUTHORITY_VERSION_AMBIGUOUS sits on the justified parity-exclusion list as KERNEL-INTERNAL.
                                                                                           (F-10.2)
L5. Provenance malformation is covered SHAPE BY SHAPE. An ABSENT publication_reference_type is a
    distinct, mandatory, executing pure-kernel fixture (PROVENANCE-ABSENT-TYPE / B1-09a) expecting
    DENY + FAIL_CLOSED, PUBLICATION_PROVENANCE_INVALID with ordinary deterministic failure evidence,
    separate from the absent-reference-id, absent-published_at, absent-retracted_at and
    unknown-type fixtures. The malformed provider-neutral input reaches the kernel through
    LineageMaterial with no intervening normalization, defaulting or convenience validation, and the
    fixture is asserted through the kernel entry point — never relocated to DTO-only rejection.
                                                                                           (F-10.1)
M.  Multiple legitimate grant paths are all returned in a deterministic order; ambiguity is
    distinguished from multiplicity.
N.  Evidence is first-class for negative outcomes: qualifying paths, complete nonqualifying paths
    and partial/failed evaluations are all retained per section 16, with deterministic ordering, no
    fabricated object/version pairs, and a populated established_state on a zero-path denial.
    Evidence contains no secret and no provider-specific identifier.                         (F-06)
O.  Reference/synthetic providers exist only in tests/reference harnesses and are proved unreachable
    from production runtime paths; no production composition binds them.                     (F-04)
P.  No persistence, no migration, no model registration, no HTTP route, no frontend change.
Q.  No write path to published authority configuration exists anywhere in the package.
R.  No production/bootstrap authority data is seeded; synthetic fixtures are labelled as such.
S.  Every PF-1A-E1 protection is intact and unmodified: the compatibility matrix, the route
    inventory, the route-migration guard, require_permission(...), and the facts in section 6.
T.  Full backend regression passes. Alembic `current` equals `heads` and is UNCHANGED from the
    baseline this package started on (E2-A adds no migration).
U.  Tracked-secret scan passes; `git diff --check` is clean.
V.  A fresh, independent bounded review returns ACCEPTED with no blocking findings.
```

Acceptance is recorded by the independent reviewer, never by the implementation agent.

## 20. Allowed and disallowed file areas (for the future E2-A implementation package)

Indicative, to be confirmed in the bounded implementation package. **This document does not
authorize any of these edits; it scopes them.**

Allowed:

```text
backend/app/modules/authorization/business_authority/     new subpackage: DTOs, domain objects,
                                                          ports, kernel, evaluators, scope matcher,
                                                          lineage/closure logic, reason codes
backend/app/modules/hr_reference/                          RECOMMENDED location for the
                                                          provider-neutral HR/actor-person PORT
                                                          (protocols + canonical DTOs only; no
                                                          provider, no persistence, no route)
backend/tests/test_business_authority_*.py
backend/tests/fixtures/pf_1a_e2_*.py                       reference/synthetic providers and the
                                                           declarative scenario corpus - TEST-ONLY
                                                           (section 9.6)
docs/agent/pf-1a/                                          this package's documents
docs/agent/acceptance/pf-1a-e2-a-*.md
docs/continuity/                                            handoff / review / closure records
```

Reference/synthetic provider implementations belong under `backend/tests/` (or an equivalent
explicitly test-only location), never under a production package path, so section 9.6's
unreachability property is structural rather than merely asserted.

The HR-port location is an engineering layout decision with two defensible answers. Placing the
canonical HR port inside `authorization/` would misrepresent ownership (the HR reference is not an
Authorization-owned capability — ADR-026, ADR-032, `RMR-001`), which is why a separate
contracts-only `hr_reference` module is recommended. Either choice is acceptable provided the
decision and its reasoning are recorded in the implementation handoff; it is not a blocking
question.

Disallowed (high risk — changing any of these without separate authorization is a blocking finding):

```text
backend/app/modules/authorization/contract.py       E1 permission catalogue/matrix
backend/app/modules/authorization/dependencies.py   require_permission(...)
backend/app/modules/authorization/service.py        has_permission(...)
backend/app/modules/authorization/repository.py
backend/app/modules/authorization/models.py
backend/app/modules/identity/**                      AppUser/AuthUser/Role/UserRole/dependencies
backend/app/models_metadata.py                       (E2-B only)
backend/alembic/**                                   (E2-B only)
backend/app/modules/{accounts,commercial_offers,leads,opportunities,work_orders,
                     terms_and_conditions,events,documents,workflow}/**
backend/tests/test_authorization_*.py                existing E1 tests
backend/tests/fixtures/pf_1a_e1_baseline_authorization.py
frontend/**
docs/agent/contracts/**                              approved contracts (ORA-001, RMR-001, ...)
docs/agent/pf-1f-hr/**                               PF-1F-HR accepted documents
```

## 21. Documentation obligations at implementation time

```text
- this package document, updated with the actual implementation outcome;
- docs/agent/acceptance/pf-1a-e2-a-*.md acceptance record;
- a docs/continuity/ implementation handoff recording baseline commit, proposed scope, exact test
  commands and real counts, self-review findings, limitations and deferred items;
- a docs/continuity/ closure record at integration;
- PLAN.md / NEXT_STEPS.md / AGENT_HANDOFF.md current-state reconciliation AT PACKAGE CLOSURE - not
  by this definition document, which must not touch them.
```

## 22. Independent-review attack surface

A reviewer of the E2-A implementation must attack at least the following. Each is a blocking
finding if reachable.

```text
1.  Collision between Application/Login Role and Business Authority Role (naming, types, tables, or
    a mapping between them).
2.  Any hidden ADMIN bypass, in permissions or in business authority.
3.  Business Authority inferred, defaulted or derived from an E1 role code.
4.  Hard-coded person / designation / position / role-specific authority logic instead of
    authority_code lookup; a literal comparison against AUTHORITY_CONFIGURATION_ADMIN instead of the
    is_protected_meta_authority data field.
5.  Client-supplied person_id (body, query, header, token claim) influencing the identity
    authorized.
6.  A caller-controlled or backdated as_of reaching a current authorization decision.
7.  More than one clock / instant used within a single resolution.
8.  Interval-boundary errors (inclusive/exclusive confusion; gap or overlap at a shared boundary).
9.  Future-dated authority, rule, assignment or incumbency taking effect before effective_from.
10. active_flag treated as a derived/temporal projection, mutated on a published version, omitted
    from the grant-eligibility test for any of the four families, or merged with effectiveness so
    the evidence cannot show which condition failed.                                         (F-01)
11. An inactive effective version reported as corruption / fail-closed, or an unresolvable authority
    reported as merely inactive.                                                             (F-01)
12. A provider that prefilters to "the effective row", excludes retracted/inactive/future versions,
    returns a derived closure as fact, deduplicates, tie-breaks, or returns truncated lineage
    material presented as complete.                                                          (F-02)
12a. Candidate DISCOVERY narrowed by anything beyond object family, stable identity, authority_code
    and stable reference - in particular discovery that excludes a version because it is retracted,
    corrected, inactive, not effective, out of scope, of a non-matching evaluator outcome, or not
    "the latest". Probe specifically: can a MALFORMED retraction (dangling, duplicated, or with
    impossible provenance) make the only requested-code-bearing or only reference-bearing version
    invisible, so its own defect is reported as an absent candidate?                          (F-07)
12b. Kernel-side relevance (15.2) applying the same forbidden exclusion - treating retraction as an
    irrelevance test, or asserting irrelevance using a field that is itself defective.        (F-07)
12c. published_at / retracted_at used as a lineage or discovery FILTER; the historical resolver
    implemented as recorded-knowledge replay instead of corrected business-effective reconstruction;
    a recorded-time cutoff parameter exposed on either operation (a backdating attack under another
    name); recorded timestamps carried but never validated, so impossible provenance passes.  (F-07)
13. Lineage semantics duplicated or re-derived inside a provider instead of owned by the kernel.
14. A provider error, timeout or UNAVAILABLE completeness degraded to "no candidates found" or to
    DENY + RESOLVED.                                                                          (F-02)
15. Mutable published versions, or destructive closure of a historical version.
16. Contradictory or broken append-only lineage accepted instead of failing closed.
17. A legitimate temporal GAP misclassified as contradictory lineage; or reactivation after a gap
    rejected; or a gap in the REQUESTED authority silently treated as an ordinary denial instead of
    AUTHORITY_CODE_NOT_CONFIGURED; or a genuinely dangling reference treated as a gap.        (F-05)
17a. Closure computed as min(declared_effective_to, next_start) - or any equivalent that silently
    truncates an explicit declared end to a successor's start. Probe with V1 [t0, t3) and V2 from
    t2, t0 < t2 < t3: the required answer is AUTHORITY_LINEAGE_CONTRADICTORY, and any implementation
    that instead resolves V1 [t0, t2) has made explicit-overlap detection unreachable. Also probe
    end == start and end < start (must fail closed — direct E2-A kernel-boundary test, class B1 per
    9.7), explicit adjacency (must be valid), and an explicit end earlier than the successor's start
    (must be a valid gap, not a truncation and not an extension to the successor's start).    (F-09)
17b. VERIFICATION CLASS ERRORS (section 9.7). A semantic rule of this document treated as satisfied
    merely because some store's schema rejects the shape; a class B1 shape whose direct E2-A test
    has been deleted, skipped, xfailed or weakened because "the database prevents it"; a class B1
    shape whose expected reason code is left to the implementer instead of being normative; a class
    B1 shape whose test exercises a DIFFERENT boundary than the one named for it — in particular a
    DTO/port well-formedness case (missing effective_from, missing active_flag) dressed up as a
    kernel fixture, or a kernel case (XOR, provenance, interval sanity, duplicate object_version)
    quietly moved into a DTO validator so it can never reach the kernel; a CLASS A cross-row
    semantic contradiction (explicit overlap, duplicate temporal start, malformed or duplicated
    retraction, broken correction lineage, impossible recorded provenance, dangling reference to a
    stable identity carrying no material) reclassified into B1 or B2 by introducing a structural
    constraint that suppresses it — a uniqueness constraint on (stable_object_id, effective_from) is
    the archetype; a reference/synthetic provider or a material DTO that imposes identity-uniqueness,
    XOR, interval-sanity, provenance-presence, closed-enum or referential restrictions over the
    DTO-OPTIONAL fields of 9.3.4, so a class B1 shape cannot even be constructed; a fixture carrying
    more than one class, or none; a parity obligation left implicit about which class it belongs to.
17c. CLASS B2 ABUSE (section 9.7). B2 used as a semantic escape hatch: a fixture classified B2 whose
    equivalent malformed state a conforming provider COULD in fact supply through the 9.3.2/9.3.4
    fields — apply the deciding test in 9.7 rather than accepting the label; a B2 entry with a
    missing, circular or "no kernel test exists" rationale; a B2 classification applied to a
    malformed BUSINESS state rather than to a store's own identity/parentage representation; an
    invented reason code, DTO field or fake DTO shape added solely to mirror a database
    implementation detail; a change to the 9.3.4 DTO-required/DTO-optional split that makes a B2
    state representable without reclassifying it to B1 the same day.                          (F-10)
17d. TAXONOMY SCOPE ERRORS (section 9.7.0). A negative fixture whose subject is NOT authority-store
    data carrying an A / B1 / B2 label - the archetype being a class-A label sitting next to an
    "N/A" storability answer, which is unexecutable by construction. Conversely, a scenario moved
    into the non-store table and left WITHOUT an explicit executable obligation, a named seam, an
    expected result, BOTH store answers, or a parity statement - that converts a category fix into a
    silent coverage
    loss. Also: a non-store scenario attached to a seam this document does not define (an invented
    provider surface); a sentence anywhere outside the three groups still claiming that EVERY
    negative/conformance scenario carries an A/B1/B2 class, or that PostgreSQL must store a
    provider-failure, HR-state or request-input scenario; an item appearing in more than one group
    or in none.                                                                            (F-10.3)

17g. VALID STATE WEARING A NEGATIVE-FIXTURE LABEL (section 9.7.0 entry test). Class A means a
    PERSISTABLE SEMANTIC CONTRADICTION, and its defining obligation is to store that contradiction
    and read it back. Probe each A/B1/B2 entry with one question: does THIS document require the
    kernel to REJECT that state as invalid? If the honest answer is "no - the configuration is valid,
    and this is simply what it means at that as_of", the entry is a valid-shape or non-store scenario
    and the label is wrong. That is exactly how E2-B fixture A-12 (the requested authority with no
    grant-eligible version at as_of, including inside a VALID GAP - section 11.5) came to be class A.
    Also probe the mirror errors: a VALID closure, adjacency, gap or reactivation shape described
    anywhere as "class A"; such a shape quietly dropped from the parity corpus on the grounds that it
    "is not a negative fixture" - it remains fully parity-owed as V-01 to V-04; and section 11.5's
    asymmetry softened, so that the REQUESTED authority stops failing closed with
    AUTHORITY_CODE_NOT_CONFIGURED inside a valid gap, on the pretext that NS-RS-01 is "only" a
    conformance scenario. Reclassification moved where that behaviour is proved; it changed no
    behaviour.                                                                            (F-10.3a)

17h. NON-STORE TABLE NOT TOTAL (section 9.7.0, F-10.3b). An obligation stated in the imperative in
    section 18 or in E2-B section 9, whose malformed/negative subject is not stored authority state,
    and which carries no scenario ID in E2-B 5.7A. Check each of the categories this correction was
    written against, and confirm each has a live ID and an executing test: actor-to-canonical-person
    trust boundary (NS-AP-04); synthetic-versus-production provider reachability and the production
    composition's own behaviour (NS-PR-01, NS-PR-02); provider fact-fidelity (NS-PR-03); the
    server-captured live as_of and the single-clock rule (NS-RS-02); no caller-selected as_of, no
    recorded-time cutoff, and the historical resolver not usable as a live authorization path
    (NS-RS-03); recorded time never acting as a lineage filter (NS-RS-04); aggregation across
    multiple legitimate qualifying paths (NS-AG-01); relevant corrupt state not masked by a valid
    path (NS-AG-03); result-level reason selection (NS-AG-05); deterministic defect ordering
    (NS-DO-01..06); and complete, nonqualifying and partial denial evidence with deterministic
    ordering (NS-EV-01..05). Probe the inverse too: a scenario ID invented for an obligation no
    current normative sentence states, which is padding rather than totality, and a
    correction-cycle finding in its own right.                                             (F-10.3b)
17e. DEFERRED CLASSIFICATION. Any manifest entry whose class, storability, expected reason code or
    parity obligation is written as conditional on what the implemented kernel turns out to do -
    "see record", "whichever code the kernel emits", "resolve this once implemented". A definition
    that defers a classification has not made one. Probe specifically that the residual multiplicity
    clause is decided (11.4a): the theorem is stated, the clause is retained as a defensive
    invariant rather than deleted, its reason code is AUTHORITY_VERSION_AMBIGUOUS, no
    authority-store fixture claims to seed it, and NS-K-01 exists with all three executable parts.
                                                                                           (F-10.2)
17f. PROVENANCE SHAPE COLLAPSE. An ABSENT publication_reference_type treated as covered by the
    UNKNOWN-value fixture, or by the absent-reference-id fixture, or by any DTO-level rejection.
    Probe directly: construct LineageMaterial with publication_reference_type absent and everything
    else valid, call the kernel, and require DENY + FAIL_CLOSED /
    PUBLICATION_PROVENANCE_INVALID with ordinary 16.4 evidence. Also probe the inverse defect - a
    DTO, dataclass default, decoder or reference-provider helper that silently substitutes
    BOOTSTRAP_PROVENANCE for a missing type, or refuses to construct material without it, either of
    which makes the fixture unconstructible; and any manifest ID covering two malformed shapes of
    which only one has an executing test.                                                  (F-10.1)
18. Arbitrary first-row / latest-row selection masking ambiguity.
19. Stale, missing or unavailable HR state producing an ALLOW.
20. Position-based authority resolved without re-resolving incumbency at as_of.
21. SharePoint / Plum / Source Binding detail leaking across the canonical boundary.
22. An organisation hierarchy invented inside authorization.
23. Rule and Assignment scope composed by union, by "either", or with GLOBAL treated as a match
    that overrides a narrower operand; or an incompatible scope pair reported as a defect.    (F-03)
24. A fail-closed defect in RELEVANT authoritative state masked by another qualifying path; or
    relevance asserted without an identity-only proof; or an unestablishable relevance resolved
    optimistically instead of failing closed.                                                 (F-03)
25. Aggregation that is not total, or that returns ALLOW ahead of a relevant fail-closed defect.
25a. RESULT-LEVEL REASON selection that is not total: two defects at the same stage with no
    tie-break; a canonical_subject_key containing a memory address, object hash, provider row
    number, iteration position, clock reading or random UUID; a reason_code_rank derived from
    alphabetical spelling or accidental enum order rather than an explicit closed rank table; a
    missing rank for any reason code; result_level_reason taken from "the first defect observed"
    rather than the first under the total order; or a partial-evidence ordering that can disagree
    with result_level_reason about which defect is first. Probe by shuffling provider rows,
    reversing traversal and re-running: the reason must not move.                             (F-08)
26. Any executable expression / eval / template / SQL-string condition language.
27. An unknown or malformed evaluator or payload treated as satisfied, or silently skipped.
28. Missing or malformed publication provenance accepted.
29. Legitimate multiple grant paths misreported as corruption, or silently reduced to one.
30. Evidence omitting any of the four object/version pairs on a QUALIFYING or a COMPLETE
    NONQUALIFYING path; a denial carrying only a reason code; a partial evaluation fabricating
    placeholder pairs; a candidate touched but absent from all three evidence collections; a zero-
    path DENY + RESOLVED with an empty established_state; non-deterministic evidence ordering. (F-06)
31. Historical evidence that stops dereferencing after later versions/retractions/corrections.
32. A synthetic/reference provider importable from, or bound by, a production composition; or any
    claim that E2 delivers a production-callable resolver while authoritative actor-person and HR
    providers do not exist.                                                                   (F-04)
33. Any weakening of E1 permissions, the compatibility matrix, the route inventory or the
    route-migration guard.
34. Any write surface (function, repository method, fixture helper reachable from production, test
    hook) that mutates published authority configuration outside a future governed Configuration
    Change.
35. Synthetic bootstrap/test data presented, labelled or relied upon as production bootstrap or as a
    resolution of Q-10.
36. Persistence, migration, model registration or an HTTP route smuggled into E2-A scope.
37. Secrets, credentials or personal data beyond the operational minimum appearing in evidence, logs
    or fixtures.
```

Risk classification for the bounded review method: **high** — security/authorization boundary plus
workflow/lifecycle/state-machine characteristics. Apply the core rubric of
`BOUNDED_INDEPENDENT_REVIEW_METHOD.md` section G together with the workflow/lifecycle overlay
(section H.2), and treat the list above as package-specific overlay items.

## 23. Business-decision assessment

```text
Q-10 (first production AUTHORITY_CONFIGURATION_ADMIN holder)
    OPEN. A genuine PBL governance decision.
    Blocks:        READY_FOR_PRODUCTION_AUTHORITY_ACTIVATION / production authority bootstrap.
    Does NOT block: PF-1A-E2-A definition, implementation, or synthetic/reference testing.
    E2-A must not seed, choose, imply or pre-empt a real bootstrap holder.

Q-09 (stable Plum Employee ID reliability)
    OPEN, and NOT a business decision. A source-capability/reconciliation-quality question.
    Blocks nothing here: canonical person_id is platform-owned and never depends on Plum having a
    stable identifier.

Deferred parameter values (HR staleness threshold; evidence retention)
    Remain deferred policy parameters. The kernel accepts a configured threshold and fails closed
    when required state is missing or stale. Do NOT invent a default value.

Actor -> canonical person runtime link
    An engineering contract seam, resolved in section 7.1. Not a PBL decision.

Append-only publication lineage, derived closure, gap semantics
    Engineering design problems, resolved in section 11. Not PBL decisions.

active_flag semantics, scope composition, path aggregation, denial evidence
    Engineering semantic problems raised by independent review and resolved in sections 8.2, 12.4,
    15.3 and 16. Not PBL decisions.

Raw discovery boundary; recorded-time versus business-effective-time semantics; total fail-closed
defect ordering; valid successor closure with gaps and explicit overlap
    Engineering semantic problems raised by the second independent review (F-07, F-08, F-09) and
    resolved in sections 9.3.1, 11.4, 11.8, 15.5 and 16.5. Not PBL decisions. In particular, the
    choice NOT to implement point-in-time recorded-knowledge replay in E2 is a scope/engineering
    decision recorded in 11.8.1, not a business policy PBL must settle; if PBL later requires
    as-known-at audit replay, that is separately authorized work and does not change the E2
    contract retroactively.

Verification placement of malformed inputs a store cannot hold (the three classes A / B1 / B2)
    An engineering VERIFICATION-CONTRACT problem raised by the third independent review, found only
    partly closed by the fourth, and resolved by the F-10 definition-closure package in section 9.7,
    with the per-fixture consequences in 9.3.2, 9.3.3, 9.3.4, 11.6, 18, 19.L2 and 22.17b/17c. Not a
    PBL decision, and not a change to any semantic rule: which structural constraints a relational
    store enforces - and whether the invariant a given constraint protects even EXISTS in the
    provider-neutral contract - are engineering properties of that store and of this document's own
    DTO shape. The semantics remain provider-neutral and unchanged, and no fail-closed behaviour,
    reason code or evidence obligation was added, removed or weakened.

DTO-required versus DTO-optional material fields (section 9.3.4)
    An engineering CONTRACT-SHAPE decision made by the F-10 closure package so that every class B1
    fixture has a constructible, boundary-accurate test. It is derived mechanically from rules this
    document already states: a field this document already assigns a semantic classification to
    (provenance, assignment target, declared interval) MUST be DTO-optional so the kernel can
    classify it; a field this document assigns no classification to, and without which the record is
    not a published version at all (effective_from, active_flag), is DTO-required and its absence is
    a well-formedness failure. Not a PBL decision.

Scope of the verification taxonomy; reachability of the residual multiplicity clause; per-shape
provenance coverage (the three F-10 FINAL closure items)
    Engineering VERIFICATION-CONTRACT problems raised by the fourth independent review and resolved
    by the F-10 FINAL definition-closure package in sections 9.7.0, 11.4a, 11.7, 18, 19.L3/L4/L5 and
    22.17d/17e/17f, with the per-fixture and per-scenario consequences in E2-B 5.7 and the new
    5.7A. None is a PBL decision:
      - WHICH universe a verification class applies to is a property of what a store holds, decided
        by inspecting this document's own port contract;
      - WHETHER the residual multiplicity clause is reachable is a THEOREM over rules this document
        already states (11.4a), so leaving it "to be determined by the implementation" was a defect
        rather than a genuine open choice - the answer was already implied and merely unstated;
      - WHETHER an absent field and an unknown value are the same malformed state is a question of
        fact about the contract's own shape, not of business policy.
    No semantic rule, fail-closed behaviour, reason code or evidence obligation was added, removed
    or weakened by resolving any of them.
```

**No unresolved PBL business decision blocks PF-1A-E2-A.** If an implementation or review pass
discovers one, it must stop and escalate rather than choosing a business answer.

## 24. Standalone continuation contract

*A fresh implementation or review chat should be able to act safely from the repository plus this
section, with no dependence on any prior conversation.*

**Package status.** PF-1A-E2-A is a **proposed definition**, corrected across five independent
reviews and three authorized correction/closure packages (section 1.1). It has not been implemented
and has not been independently
accepted. This
document is the definition; acceptance of the definition, and later acceptance of an implementation,
are separate events recorded by an independent reviewer.

**Source-of-truth precedence.**

```text
1. Current explicit human instruction or approved decision
2. Frozen contracts and approved architecture decisions (ORA-001, RMR-001, ADR-026/030/032/033)
3. Accepted requirements and active acceptance criteria
4. Current module contracts and active implementation documentation (this document)
5. Current source/reference documents
6. Historical continuity records and superseded drafts
```

**Predecessors and dependencies.** PF-1A-E1 is COMPLETE and INTEGRATED (section 6). PF-1F-HR-E1 is
COMPLETE; `READY_FOR_PF_1A_DESIGN_IMPLEMENTATION` is MET and
`READY_FOR_PRODUCTION_AUTHORITY_ACTIVATION` is NOT MET. E2-A depends on the canonical HR contract
and the ADR-033 authority configuration model as **documented designs**, not as implemented systems.
No authoritative actor-person or HR/organisation provider exists yet; supplying one is a later
authorized package (section 9.6).

**Terminology.** Four concepts must never be collapsed: Application/Login Role; Application
Permission; Business Authority Role; Business Authority. See section 4 in full — it is not optional
background.

**Settled invariants that must not be reopened.**

```text
- Business consumers request authority by authority_code only.
- No Business Authority is ever derived from an Application/Login Role, including ADMIN.
- Backend authorization is authoritative; frontend hiding is a usability aid only.
- CRM/Hiring/Authorization never owns an Employee/Organisation/Position master.
- Provider-specific HR detail never crosses the canonical boundary.
- Published authority versions are immutable; history is append-only; closure is derived.
- active_flag is an IMMUTABLE PUBLISHED VALUE, not temporal effectiveness; grant-eligibility is
  lineage-valid AND effective AND active, for all four families (section 8.2).
- A valid temporal GAP is valid history, not corruption, and a later valid version after a gap is
  REACTIVATION (section 11.5). An EXPLICIT declared end later than the next valid successor's start
  is a CONTRADICTORY OVERLAP that fails closed and is never truncated or normalized; the formula
  min(declared_effective_to, next_start) is rejected (section 11.4).
- E2-A owns lineage semantics; providers supply complete facts only and never prefilter (5.1, 9.3).
- AT MOST ONE version of a stable object's current asserted lineage is EFFECTIVE at any instant once
  the duplicate-start, nonsensical-interval and explicit-overlap conditions have passed (the section
  11.4a theorem). The residual multiplicity clause of 11.6 is therefore unreachable from any
  provider input; it is RETAINED as a defensive kernel invariant, must not be deleted as dead code,
  emits AUTHORITY_VERSION_AMBIGUOUS if ever violated, and is verified as pure-kernel self-check
  NS-K-01 rather than as an authority-store fixture.
- SEMANTIC VALIDITY IS PROVIDER-NEUTRAL; VERIFICATION PLACEMENT IS NOT (section 9.7). The A/B1/B2
  taxonomy is SCOPED (9.7.0): it classifies ONLY negative fixtures whose subject is a MALFORMED OR
  CONTRADICTORY published authority-store / read-repository state - one this document requires the
  kernel to reject as invalid - and every such fixture carries EXACTLY ONE of three classes. A VALID
  stored shape is a VALID-SHAPE PARITY SCENARIO (E2-B 5.7, V-01 to V-12): no class label, not a
  negative fixture, full parity still owed. Everything whose subject is a SEAM - provider states,
  provider reachability and fact-fidelity, request inputs, resolver orchestration and the resolution
  clock, aggregation and relevance, deterministic defect ordering, the evidence contract, and
  pure-kernel invariants - is a NON-STORE scenario in the separate normative table (E2-B 5.7A),
  carrying no class but a named seam, an executable obligation, an expected result, BOTH store
  answers and an explicit parity statement, and that table is TOTAL over the non-store obligations
  the current normative text already mandates. "N/A" is never a storability answer for a classified
  fixture; a fail-closed OUTCOME never by itself makes an item a negative fixture; READING valid
  stored rows never makes a scenario one either; and no classification is ever deferred to
  implementation time.
      A   a cross-row semantic contradiction the kernel is required to detect must remain STORABLE
          and parity-tested; a structural constraint must never be added in order to suppress it,
          and in particular no uniqueness constraint on (stable_object_id, effective_from) may be
          introduced to pre-empt duplicate temporal starts.
      B1  a store may be structurally incapable of holding a malformed shape that IS representable
          provider-neutrally; it is then proved DIRECTLY against E2-A at a NAMED boundary (DTO/port
          well-formedness, or pure kernel) with a NORMATIVE expected reason code, proved as a
          rejection by that store, and excluded from that store's parity corpus only - never
          exempted from the semantics and never left implicit.
      B2  a store's constraint may protect its OWN representation of identity/parentage, for which
          the provider-neutral contract has no field at all (object_id lives on the LineageMaterial
          container, 9.3.2). It is then proved only as a store rejection, is absent from every E2-A
          fixture manifest, and carries a written rationale. B2 is never a home for a semantic
          defect: apply the deciding test in 9.7 before using it, and never invent a reason code or
          DTO shape to mirror a database implementation detail.
- The section 9.3.4 DTO-required / DTO-optional split is part of the contract, not an implementation
  choice: it is what makes every class B1 fixture constructible at the boundary named for it.
  Changing it can silently strip a shape of all E2-A coverage and requires reclassification.
  publication_reference_type in particular is DTO-OPTIONAL and OPEN, so that an ABSENT type and an
  UNKNOWN type are two separately constructible, separately fixtured malformed states, each failing
  closed with PUBLICATION_PROVENANCE_INVALID at the PURE KERNEL boundary (11.7, 18). Never default
  a missing provenance type, and never let a manifest ID cover two malformed shapes.
- Candidate discovery operates on RAW published facts. A retraction, correction, active_flag,
  effective interval, evaluator outcome, scope value or provenance value is NEVER a discovery or
  irrelevance filter; retraction assertions are lineage facts to be validated, not filters
  (sections 9.3.1, 15.2).
- as_of is the one BUSINESS-EFFECTIVE authorization clock. published_at / retracted_at are
  recorded-time evidence and validation input only. The historical resolver performs CORRECTED
  BUSINESS-EFFECTIVE RECONSTRUCTION under the lineage known at invocation - not recorded-knowledge
  replay - so a valid later correction may change what it reconstructs, while previously captured
  decision evidence remains immutable and dereferenceable (section 11.8).
- Rule scope and Assignment scope compose by INTERSECTION; GLOBAL is top (section 12.4).
- A fail-closed defect in RELEVANT authoritative state can never be masked by a valid path
  (section 15.3).
- Fail-closed reason selection is TOTAL: result_level_reason is the reason of the first defect under
  the canonical defect sort key (stage_rank, canonical_subject_key, reason_code_rank,
  evidence_discriminator), and that same single order sequences the partial/failed evidence
  (sections 15.5, 16.5).
- Denial and failure evidence are first-class; never fabricate missing object/version pairs
  (section 16).
- A historical decision retains its decision-time authority snapshot, dereferenceable forever.
- Missing, stale, ambiguous or contradictory authoritative state fails closed.
- is_protected_meta_authority is a data field, never a hard-coded code-string comparison.
- Administering authority and holding a business authority are separate capabilities.
- Synthetic/reference providers are test-only and are never bound by a production composition.
- INR is the current operating currency (ADR-023 / Q-08); units are still declared explicitly.
```

**Unresolved business decisions.** Q-10 is open and blocks production authority activation only.
Q-09 is open and is not a business decision. Neither blocks this package. See section 23.

**E1 compatibility boundary.** Section 6, in full. Do not copy historical test totals as targets;
preserve the protections instead.

**HR/organisation ownership boundary.** Section 7, including the recorded actor→person
reconciliation in 7.1.

**E2-A / E2-B / E3 split and why.** Section 5. Resolving authority and changing authority are
distinct security problems. E2-A has no persistence and no migration; E2-B adds persistence with an
unchanged kernel and a read-side provider that supplies facts only; E3 adds governed configuration
change, publication and preventive self-escalation control. Do not collapse them.

**Current-versus-historical temporal rule.** `resolve_current_authority` captures its own single
server-side instant, accepts no caller-selected `as_of` and exposes no recorded-time cutoff.
`resolve_authority_as_of` accepts a business-effective instant, performs corrected business-effective
reconstruction under the lineage known at invocation (11.8.1), and must never authorize a new current
action. Sections 10 and 11.8.

**Canonical time semantics.** Half-open: `effective_from <= as_of AND (asserted_effective_to IS NULL
OR as_of < asserted_effective_to)`, plus not retracted. `asserted_effective_to` is derived per the
11.4 asserted-interval rule — successor closure for a NULL end, honoured declared end otherwise,
valid gap when the declared end is earlier than the successor's start, valid adjacency when equal,
fail closed when later — and never stored. Effectiveness is temporal only; activity is separate
(8.2). Recorded time (`published_at`, `retracted_at`) is a separate axis with its own validity
constraints (11.8.3) and is never an authorization clock.

**Fail-closed taxonomy.** Two dimensions (`ALLOW`/`DENY` × `RESOLVED`/`FAIL_CLOSED`), reasons at
both path level and result level, with the explicit lists in section 14, the aggregation precedence
in 15.3 and the TOTAL defect order in 15.5 that selects the result-level reason and sequences the
evidence. Uncertainty never becomes permission; a known-and-unfavourable answer never fails closed.

**Verification classes (where each malformed input is proved).** Section 9.7, with the taxonomy
SCOPE statement in 9.7.0 and the DTO-shape prerequisites in 9.3.2 and 9.3.4.

THREE pairwise-disjoint groups, and the first question about any item is which group it is in:

```text
MALFORMED AUTHORITY-STORE  subject: a MALFORMED or CONTRADICTORY published authority-store /
FIXTURES                   read-repository state - one this document requires the kernel to reject.
                           Classified A / B1 / B2. Manifest: E2-B section 5.7.
VALID-SHAPE PARITY         subject: a VALID published authority-store state. NO class label, not a
SCENARIOS                  negative fixture, FULL parity owed. List: E2-B section 5.7, V-01..V-12.
NON-STORE SCENARIOS        subject: a provider, a request input, resolver orchestration or the
                           resolution clock, deterministic defect ordering, evidence, or a
                           pure-kernel invariant. NO class. Table: E2-B section 5.7A, forty-six
                           scenarios, TOTAL over the current mandatory non-store obligations.
```

A FAIL-CLOSED OUTCOME NEVER BY ITSELF PUTS AN ITEM IN THE FIRST GROUP. The withdrawn fixture A-12
produced DENY + FAIL_CLOSED / AUTHORITY_CODE_NOT_CONFIGURED from entirely VALID rows, because 11.5
treats an unestablished REQUESTED authority as an unknown question rather than an absent grant; it
is non-store scenario NS-RS-01. Equally, READING valid stored rows never puts an item in the first
group: store participation and store subjecthood are separate questions with separate answers.

For every named AUTHORITY-STORE fixture a fresh chat must be able to answer seven questions from
the repository alone:

```text
(1) is it A, B1 or B2?
(2) can PostgreSQL intentionally store it?          (YES or NO - never "N/A"; an "N/A" answer means
                                                     it is not an authority-store fixture at all)
(3) can the provider-neutral E2-A contract meaningfully represent it - and at which boundary
    (DTO validation / provider port / kernel)?
(4) exactly what DB test is required?
(5) exactly what E2-A test is required?
(6) is PostgreSQL-provider parity required?
(7) if there is no E2-A counterpart, why is that a persistence-only invariant rather than an
    ignored semantic defect?
```

and for every named NON-STORE scenario, eight different ones:

```text
(1) which already-defined seam is under test?
(2) what input/condition drives it?
(3) does PostgreSQL authority-store DATA participate in composing the test?   (YES / NO)
(4) is the malformed/negative SUBJECT itself authority-store state?
    (NO on every 5.7A row by construction; written out per scenario, never inferred from (3))
(5) exactly what executable test obligation applies?
(6) what outcome / resolution_status / reason / evidence is expected?
(7) is provider parity required, and between which providers? If not, why does an agreement test
    have no second side?
(8) why is it outside A / B1 / B2?
```

and for every named VALID-SHAPE scenario: that it seeds VALID stored state, carries no class label,
and sits in the parity corpus.

Class A shapes are persistable semantic contradictions and are owed full parity. Class B1 shapes are
structurally rejected but provider-neutrally representable, and are proved by a store rejection test
plus this document's permanent direct E2-A test at the named boundary, then excluded from that
store's parity corpus. Class B2 shapes are structurally rejected and have no provider-neutral
counterpart at all, so they are proved only as a store rejection, are excluded from BOTH the parity
corpus and every E2-A fixture manifest, and carry a written rationale. Exclusion is placement, never
exemption — and moving a scenario into the non-store table, or recognising it as a valid-shape one,
is likewise placement, never exemption:
it drops only a MALFORMED-STATE storage obligation that was never executable for it.
`PF_1A_E2_B_...md` section 5.7
holds the binding, TOTAL per-fixture assignment for the PostgreSQL store together with the
valid-shape list V-01 to V-12, and its section 5.7A holds
the binding, TOTAL non-store scenario table; that is where all three question sets are actually
answered.
Retired manifest IDs (`A-03`, `A-12`, `A-16`, `A-18`, `A-19`, `A-20`) are never reused and are
recorded there with their replacements.

**Publication immutability and lineage.** Append-only lineage with derived closure and append-only
retraction assertions; no mutation of a published version, ever, including its `active_flag`.
Contradictions in 11.6 — including duplicate starts, explicit overlap and impossible recorded
provenance — fail closed; gaps in 11.5 do not. Section 11.

**Evidence requirements.** Four collections — result header with `established_state`, qualifying
paths, complete nonqualifying paths, and partial/failed evaluations — with all four object/version
pairs on every complete path, per-object active/effective evaluation, HR/scope/parameter evidence,
recorded-time provenance labelled as such, the single business `as_of`, deterministic ordering (15.4
for paths, the 15.5 total defect order for partial/failed evaluations), no fabricated pairs, and
permanent dereferenceability. Section 16.

**Allowed implementation discretion.** Module layout within the allowed areas; the HR-port location
(section 20); DTO/type shapes and naming (subject to section 4, and subject to the DTO-required /
DTO-optional split of section 9.3.4, which is contract rather than discretion); the evaluator
registry mechanics;
the internal representation of lineage provided the invariants and the section 9.3 material contract
hold; the concrete encoding of the 15.5 sort key and the specific integer values in the reason-rank
table, provided the table is closed, explicit, immutable and total; traversal direction (subject to
12.2 determinism); test file organisation.

**Prohibited reinterpretation.** Anything in "settled invariants" above; the E2-A/E2-B/E3 boundary;
the exclusions in section 17; the E1 boundary in section 6; the HR ownership boundary in section 7;
inventing a business answer to Q-10.

**Out of scope.** Section 17, in full.

**What must be freshly established when implementation begins.**

```text
- the actual protected-main baseline commit at that time (do not reuse the definition-time commit
  b6e58994ca4486819312457e89adec22ad720495 as the implementation baseline without re-checking);
- the actual current Alembic head, verified from backend/alembic/versions/ (E2-A must not change it,
  so this is a "confirm unchanged" check, not a parent selection);
- the actual current E1 test counts and route/permission inventory, read from the repository, not
  from any document;
- the branch/worktree assigned by the controller for the implementation package.
```

**Required independent-review posture.** Bounded, packet-based review per
`BOUNDED_INDEPENDENT_REVIEW_METHOD.md`; risk classification high; core rubric plus the
workflow/lifecycle overlay plus this document's section 22 attack surface. The implementation agent
never records acceptance of its own package. Integration follows the ADR-031 protected gate (pull
request, branch current with `main`, `Required validation` reporting success on the exact commit,
project-owner confirmation).

**Completion / handoff condition.** PF-1A-E2-A is complete when: the kernel, ports (including raw
candidate discovery), evaluators, reason taxonomy with its closed reason-rank table, lineage
semantics (derived closure with gaps, adjacency and explicit-overlap detection; the 11.4a
single-effective-version invariant; recorded-time validation), scope composition, aggregation
precedence with the total defect order, evidence contract
and test-only reference providers are implemented within the allowed file areas; the section 18 tests
exist and pass, including the permanent direct E2-A class B1 coverage at its named boundaries — with
PROVENANCE-ABSENT-TYPE present and distinct from PROVENANCE-UNKNOWN-TYPE, and a one-to-one
fixture-name-to-manifest-ID mapping — the class B2 absence/rationale assertions, the VALID-SHAPE
parity coverage (V-01 to V-12), the NON-STORE
scenario coverage for all forty-six scenarios including NS-K-01's three executable parts, a TOTAL,
EXCLUSIVE three-class
(A / B1 / B2) assignment over the MALFORMED AUTHORITY-STORE negative corpus, and a total, pairwise
disjoint partition
of the whole negative, valid-shape and conformance corpus into malformed authority-store fixtures,
valid-shape parity scenarios and non-store scenarios
(sections 9.7, 9.7.0); every acceptance criterion in
section 19 is demonstrated with real, recorded
evidence; a fresh independent review returns ACCEPTED with no blocking findings; and the package is
integrated on `main` through the protected gate. Only then may PF-1A-E2-B begin, and only then is
the E2-B baseline and Alembic parent determined.

## 25. Completion and handoff boundary

E2-A hands to E2-B: an accepted, integrated, provider-neutral kernel plus its ports, its reason
taxonomy and reason-rank table, its total defect order, its evidence contract, its lineage semantics
and its **test-only** reference providers — with the explicit expectation that **E2-B reuses the
kernel unchanged** and supplies only a PostgreSQL-backed read-side implementation of the authority
configuration port that returns complete lineage material and RAW identity-only candidate sets
(section 9.3), together with persistence for the already-accepted model. E2-B stores the
**persistable** lineage shapes of section 11.4 — null-end successor closure, adjacency, gaps and
reactivation, explicit overlaps and duplicate starts alike — without normalizing any of them, and
proves the kernel classifies them identically to the reference provider. E2-B does not implement,
duplicate or weaken any semantic rule in this document.

E2-A also hands E2-B its **three-class verification manifest** (section 9.7), whose binding
per-fixture form is E2-B section 5.7:

```text
CLASS B1 - E2-B's schema rejects the write, and the malformed state IS representable here.
    a duplicate object_version within one object's material; an assignment carrying neither or both
    targets; declared_effective_to < effective_from and the empty declared_effective_to ==
    effective_from; and FIVE separately named provenance shapes - an absent published_at, an absent
    retracted_at, an ABSENT publication_reference_type, an absent publication_reference_id, and a
    publication_reference_type outside the two defined values - all proved HERE at the PURE KERNEL
    boundary; plus an absent effective_from or active_flag - proved HERE at the DTO / PORT
    WELL-FORMEDNESS boundary as AUTHORITY_CONFIGURATION_UNAVAILABLE. Each shape has its own named
    fixture and its own manifest ID (B1-01 to B1-07, B1-08a, B1-08b, B1-09a, B1-09b, B1-10): twelve
    shapes, twelve IDs, twelve executing tests. E2-B proves each database rejection; these shapes
    are excluded from the PostgreSQL parity corpus and recorded as such in E2-B's acceptance record.

CLASS B2 - E2-B's schema rejects the write, and there is NO provider-neutral counterpart.
    a version row whose stable-identity parent row does not exist; a retraction row whose object
    stable-identity parent row does not exist; a rule/assignment referencing a role/authority stable
    identity ROW that does not exist. These exist only because E2-B represents stable identity as a
    separate physical row (E2-B 5.1); section 9.3.2 puts object_id on the LineageMaterial container,
    so nothing here is expressible at this boundary. E2-B proves the rejections; this document
    contains NO fixture for them, deliberately; the rationale is recorded in the manifest.

CLASS A - every remaining MALFORMED AUTHORITY-STORE negative fixture. Owed FULL PostgreSQL parity.
    Fourteen of them, after A-12's withdrawal (E2-B 5.7).

NOT CLASSIFIED, GROUP 1 - the VALID-SHAPE PARITY SCENARIOS (9.7.0; E2-B 5.7, V-01 to V-12), whose
    subject IS stored authority state but whose stored rows are VALID: null-end successor closure,
    explicit adjacency, the valid gap and reactivation after it; active-state and inactive-closure
    behaviour; the exact half-open boundary instants; raw discovery over valid retraction facts;
    recorded-time-versus-business-effective-time reconstruction; valid scope operands and
    composition; and evaluator satisfaction and legitimate non-satisfaction. They carry NO class
    label because there is no malformed state to classify, and they remain FULLY parity-owed.
    Calling any of them "class A" is the F-10.3a defect.

NOT CLASSIFIED, GROUP 2 - the NON-STORE scenarios (9.7.0; E2-B 5.7A), whose subject is a provider,
    a request input, resolver orchestration or the resolution clock, defect ordering, evidence, or a
    pure-kernel invariant rather than stored authority data:
    actor->person states and the identity trust boundary, HR/organisation states,
    authority-configuration PORT read/transport failure and provider fact-fidelity, provider
    reachability and production composition behaviour, request-side scope and evaluator input, the
    requested-authority as_of asymmetry (NS-RS-01, formerly A-12), the single-clock and
    entry-point-surface rules, recorded time never acting as a filter, aggregation and relevance,
    the total defect ORDER cases, the evidence-contract cases, the NS-K-01 single-effective-version
    invariant and the NS-K-02 kernel self-check. Forty-six in all. E2-A executes all of them; E2-B
    carries their binding table (5.7A) with each scenario's seam, obligation, BOTH store answers,
    expected result and parity requirement. They are
    outside A/B1/B2 because there is no malformed stored shape for a store to accept or reject - not
    because any obligation was dropped, and not because some of them read stored rows.
```

Neither package may leave a malformed authority-store fixture in more than one class, in none, or
with its
class unstated; nor may either leave a non-store scenario without a named seam, an executable
obligation and both store answers; nor may either drop a valid-shape scenario from the parity corpus
on the grounds that it is not a negative fixture. In particular, a class B2 entry must never be used
to retire a semantic obligation: if a
future change to section 9.3.2 or 9.3.4 makes one of those three states representable, it becomes
class B1 and acquires a mandatory direct E2-A test. Equally, the 9.7.0 scope statement must never be
used to retire one: a scenario that leaves A/B1/B2 keeps every fail-closed rule, expected reason,
evidence obligation and applicable parity requirement it had, restated in 5.7A or in the V-list.
NS-RS-01 is the test case for that promise - it kept the 11.5 asymmetry, the
AUTHORITY_CODE_NOT_CONFIGURED code, the 16.4 evidence and full parity when it stopped being A-12.

E2-A hands to E3: a read-only published-authority world with immutable versions, append-only
lineage and retraction, and a forward-compatible `CONFIGURATION_CHANGE` provenance reference that E3
will populate when it implements governed proposal, independent authorization, activation-time risk
recomputation and preventive self-escalation control.

E2-A hands nothing to production: no route, no real data, no bootstrap holder, no authoritative
actor-person or HR provider, and no claim on `READY_FOR_PRODUCTION_AUTHORITY_ACTIVATION`.

## 26. Implementation outcome (added 4 September 2026)

Recorded under the section 21 obligation to update this package document with the actual
implementation outcome. This section is **additive**: it changes no normative rule, no fail-closed
behaviour, no reason code, no expected outcome and no verification obligation in sections 2 to 25.
It records what was built and what was proved, not what is required.

**Status: IMPLEMENTED AND SELF-REVIEWED. UNCOMMITTED. NOT INDEPENDENTLY ACCEPTED.** Acceptance is
recorded by the independent reviewer, never by the implementation agent.

```text
Branch:            pf-1a-e2-a-business-authority-domain-kernel
Baseline commit:   52192ff15f7b7da636588958d3e8d37b54d805cb
Alembic head:      20260831_0030   UNCHANGED - E2-A adds no migration, and
                                   backend/alembic/** is untouched
Repository status: 36 new files; 1 modified tracked file - this package's own
                   definition document (sections 14.1, 26 and 27; additive only,
                   539 insertions, 0 deletions). 0 staged.
                   CORRECTED under C1-5: this block previously read
                   "16 new files, 0 modified files", which was false. The 16 came
                   from a `git status --short` line count in which two new
                   DIRECTORIES each collapsed to one entry, and the "0 modified"
                   ignored this document itself. Counts are now derived from git.
```

### What was built

```text
backend/app/modules/hr_reference/                 provider-neutral HR / actor-person CONTRACT
                                                  (protocols and canonical DTOs only)
backend/app/modules/authorization/business_authority/
    contract.py    closed vocabularies, stage ranks, the explicit reason-rank table
    domain.py      the four families, payloads, material DTOs, request/context shapes
    ports.py       the authority configuration port - raw discovery plus complete lineage
    material.py    the DTO / PORT WELL-FORMEDNESS boundary
    lineage.py     temporal semantics, derived closure, provenance validation
    scope.py       scope predicates and INTERSECTION composition
    evaluators.py  the evaluator registry (no expression language of any kind)
    defects.py     defect records and the TOTAL canonical sort key
    evidence.py    the four evidence collections and their ordering
    kernel.py      the pure resolution kernel
    resolver.py    the two entry points, and the production seam that REFUSES to compose
backend/tests/fixtures/pf_1a_e2_a_*.py            reference/synthetic providers, the declarative
                                                  baseline world, and the manifest AS DATA
backend/tests/test_business_authority_*.py        the conformance corpus, 16 files
```

The reference/synthetic providers live under `backend/tests/`, so section 9.6's
production-unreachability property is **structural** rather than merely asserted.

### What was proved

```text
356 E2-A conformance tests pass  (218 originally, plus 49 from correction C1, 47 from the
                                 C1 follow-up closure, and 42 from correction C2 including its
                                 final contract reconciliation)
117 PF-1A-E1 authorization tests pass, unchanged from the pre-change baseline on this branch
Alembic current == heads == 20260831_0030, unchanged
git diff --check clean; nothing staged; the ONLY modified tracked file is this
definition document itself (sections 14.1, 26 and 27; additive, 0 deletions)
```

The section 18 corpus is discharged in full and checked MECHANICALLY rather than by reading prose:
`backend/tests/fixtures/pf_1a_e2_a_corpus.py` restates the binding manifests (E2-B 5.7 and 5.7A) as
data, and `test_business_authority_coverage_manifest.py` asserts the three groups are pairwise
disjoint with counts 14 / 12 / 3, V-01..V-12 and forty-six non-store scenarios; that every
authority-store fixture carries exactly one class and a non-"N/A" storability answer; that every
item outside class B2 has a named, executing, unskipped test; and that each class B1 test exercises
the boundary its manifest entry names.

**PROVENANCE-ABSENT-TYPE (B1-09a, the F-10.1 closure) is present, distinct from
PROVENANCE-UNKNOWN-TYPE, executing at the PURE KERNEL boundary, and carries its mandatory companion
case on a retraction assertion.** NS-K-01 is discharged in all three of its executable parts,
including the defensive-branch injection that reaches the 11.6 residual clause and asserts
`AUTHORITY_VERSION_AMBIGUOUS`.

Hosted validation (`Required validation` on GitHub-hosted runners) is controller/human-owned
and is NOT claimed here. The full backend regression and the tracked-secret scan WERE run for
correction C2, because C2 changes runtime kernel logic; their results are recorded in section 26.3.

### 26.1 Correction C1 (4 September 2026)

A controller inspection of this candidate found five items. All five are corrected; the package
remains UNCOMMITTED and NOT independently accepted, and no completion pointer is advanced.

```text
C1-1  RAW SUPERSET DISCOVERY GRANTED THROUGH A HISTORICAL PARENT REFERENCE. Two fail-open defects:
      a Rule whose CURRENT effective version referenced a different Business Authority could still
      grant the authority only its HISTORICAL version carried, and the same one level down for an
      Assignment and its Business Authority Role. Discovery is UNCHANGED and still a raw superset;
      the mismatch is evaluated only after lineage has been established, and is reported as the new
      bounded fallback OTHER_NONQUALIFICATION with a deterministic explanation (section 27).
C1-2  HR STALENESS WAS ENFORCED AT ONLY TWO SEAMS. The supplied threshold now applies to EVERY
      canonical state actually relied upon - actor/person, employment, Position, Incumbency and
      every Organisation Unit ancestry hop - against the SAME authoritative as_of. No default
      threshold is invented, and no second clock is consulted.
C1-3  INCOMPLETE EVIDENCE. Participating retraction assertions now carry their recorded times into
      object evidence in a deterministic canonical order, and path evidence now accounts for every
      canonical HR snapshot relied upon rather than only the employment one.
C1-4  AN UNKNOWN LOOKUP STATUS FAILED OPEN. A status outside the closed HR vocabulary was trusted
      when a plausible value was attached. Every HR seam now validates the status against the
      closed vocabulary FIRST and fails closed with the existing HR_REFERENCE_UNAVAILABLE
      classification. No new reason code was invented, and no unknown status is silently mapped
      onto a known one.
C1-5  THIS DOCUMENT'S OWN FILE COUNTS WERE FALSE, and are corrected above from git.
```

The single new reason code introduced by C1 is `OTHER_NONQUALIFICATION`, under the owner-authorized
clarification recorded in section 27. There is no `OTHER_FAIL_CLOSED`, no other reason code was
added, and `INTERNAL_CONTRACT_VIOLATION` is unchanged.

### 26.2 Correction C1 follow-up - controller closure (4 September 2026)

A controller inspection of the post-C1 candidate found five further bounded issues, all closed
here before candidate freeze. The package remains UNCOMMITTED and NOT independently accepted.

```text
FU-1  A PROVIDER RESPONSE WAS NOT BOUND TO THE IDENTITY REQUESTED. The most serious finding, and
      reproduced as fail-open ALLOW at several seams: a fresh, otherwise-valid response describing
      a DIFFERENT canonical object was accepted as the requested object's authoritative state - a
      mapping for another authenticated actor, employment state for another person, a Position or
      Incumbency for another position, an Organisation Unit for another unit, and lineage material
      for another object or object family. Every authoritative provider response used for
      authorization is now canonically bound back to the identity requested. A mismatch means the
      requested fact was NOT established: it takes an existing FAIL_CLOSED code
      (HR_REFERENCE_UNAVAILABLE at the actor/HR seams, AUTHORITY_CONFIGURATION_UNAVAILABLE at the
      authority-configuration seam), is never coerced or repaired, and is never ordinary
      nonqualification.
FU-2  PARTIAL EVIDENCE DISCARDED ESTABLISHED STATE. A candidate that reached S9 and then failed
      closed retained only the requested Business Authority, although its Rule, Role and Assignment
      had all been established. Evidence accounting is now PROGRESSIVE and CANDIDATE-SCOPED at
      every stage from S1 to S9, retaining the object/version pairs with their active/effective
      evaluations, the canonical HR state, the scope operands and the evaluator state already
      established - and, for a stale failure, the very reference and snapshot responsible for it.
      Nothing is fabricated, and one candidate never inherits another's state.
FU-3  THE EMPLOYMENT-STATE VOCABULARY WAS NOT CLOSED. An `employment_status` outside the contract's
      own vocabulary produced DENY + RESOLVED / EMPLOYMENT_NOT_ACTIVE. EMPLOYMENT_NOT_ACTIVE is for
      KNOWN, resolved non-active states; an unknown one is not authoritative state at all and now
      fails closed. Matching is exact - never cased, fuzzy or prefixed.
FU-4  PROVIDER PROSE AND ORDER ARTEFACTS REACHED CANONICAL EVIDENCE. Exception text and list
      indices are not stable domain data: they vary across provider, library and runtime versions,
      may carry sensitive detail, and would destroy byte-identical evidence and canonical defect
      ordering. Canonical evidence now uses fixed kernel-owned templates over canonical identifiers
      only, and malformed-material records are named by their own canonical identity rather than by
      position.
FU-5  THE BOUNDED FALLBACK DID NOT REACH COMPLETE PATHS. Reconciled in section 27 above.
FU-6  Remaining stale documentation counts corrected, and derived from git.
```

No new reason code was added by this follow-up, `OTHER_FAIL_CLOSED` still does not exist, raw
superset discovery is unchanged, and `backend/app/modules/authorization/contract.py` is untouched.

### 26.3 Correction C2 - post-independent-review closure (4 September 2026)

The frozen pre-C2 candidate was submitted for independent review. **The independent review returned
CORRECTION_REQUIRED**, naming four material findings. All four are closed here. The package remains
UNCOMMITTED and NOT independently accepted; acceptance is recorded by the reviewer, never by the
implementation agent.

```text
C2-1  ANCESTRY TERMINATED ON AN UNVERIFIED CLAIM - a confirmed FAIL-OPEN, and the most serious
      finding of the review. The bounded upward traversal validated every organisation unit it
      PASSED THROUGH - contract status, value type, identity binding, freshness - but not the
      ancestor it TERMINATED ON. A subordinate unit could therefore satisfy an ANCESTRY operand by
      merely DECLARING the operand's scope as its `parent_org_unit_id`, while that ancestor had no
      canonical record at all: missing, unavailable, ambiguous, stale, or answered by a response
      about a different unit. An unverifiable claim BY THE SUBORDINATE granted authority OVER THE
      SUPERIOR. The ANCESTRY self-match had the same shape one step earlier, answering "the context
      IS the operand's scope" from two identifiers without consulting the canonical reference once.
      Both terminations now resolve the target through the single extracted `_resolve_org_unit`,
      under the SAME `as_of` and the SAME supplied staleness threshold as every other hop, and the
      terminating ancestor is retained in the path's HR evidence like every unit traversed.
C2-2  NON-CONFORMING TEMPORAL VALUES. A naive `effective_from` raised an uncaught TypeError when
      compared against the timezone-aware authorization instant, and a naive `published_at` was
      ACCEPTED and allowed authorization. One shape check, `is_conforming_instant`, is now applied
      before any comparison at every seam - refined in section 26.4 into the two FIELD-SPECIFIC
      predicates E2-A actually states: the authorization `as_of` at kernel entry
      (INTERNAL_CONTRACT_VIOLATION), `effective_from` and `declared_effective_to` at the DTO/port
      well-formedness boundary (AUTHORITY_CONFIGURATION_UNAVAILABLE), `published_at` and
      `retracted_at` in lineage provenance (PUBLICATION_PROVENANCE_INVALID), and
      `canonical_snapshot_at` at the HR and organisation-reference seams (HR_REFERENCE_UNAVAILABLE).
      No new reason code was added.
C2-3  EVIDENCE RECORDED AFTER THE CHECKS THAT REJECT IT. The established version of a Rule, Role or
      Assignment reached the candidate trail only AFTER the active-flag and reference-mismatch
      checks had passed, so the two most common ordinary denials reported a partial that named the
      object but not the version the decision was actually taken on. The established version is now
      recorded before those checks. It is audit evidence, never permission: nothing downstream reads
      the trail as a grant, and a proof of that is included.
C2-4  ONE LOGICAL CANDIDATE SPLIT ACROSS SEVERAL PARTIALS. A lineage breaking several structural
      rules at once emitted one partial evaluation per defect, so `partial_evaluations` read as
      though more candidates had been examined than actually were - and the candidate key had to be
      padded with the reason code and the detail TEXT to keep those duplicates distinct under the
      16.4 accounting, making canonical identity depend on wording written for humans. A candidate
      now produces exactly ONE partial carrying `defects: tuple[DefectRecord, ...]`, with `defect`
      derived as the first, and the candidate key is canonical identity alone. Every defect is still
      reported individually in `ordered_defects` under the ONE total order of 15.5.
```

Three bounded engineering decisions were taken while closing these, and are recorded rather than
left implicit:

```text
TEMPORAL CONFORMANCE IS FIELD-SPECIFIC, NOT ONE RULE. This bullet originally read
"aware-but-not-UTC instants are accepted and not rewritten", which was too broad and is CORRECTED
in section 26.4. E2-A states TWO different requirements, and neither may be applied to the other's
fields: `effective_from` is "inclusive, timezone-aware" (8.1) with no UTC rule, while the single
`as_of` (11.1) and `published_at` / `retracted_at` (11.8.3) are required to be "normalized to UTC"
in terms. NEITHER rule ever rewrites its input: a nonconforming value is reported through that
field's existing reason code, because 11.8 forbids silently reinterpreting a supplied instant.
A LATENT CANDIDATE-KEY COLLISION WAS CLOSED WITH C2-4. Two Rules referencing ONE broken Role keyed
their role-lineage failures on the role alone. The removed reason/detail padding had been masking
it - both partials would have carried identical text - so removing the padding without also moving
`role_candidate` above the role lineage load would have produced a spurious
INTERNAL_CONTRACT_VIOLATION on an ordinary configuration. A regression test pins it.
THE EXACT SCOPE PREDICATE IS DELIBERATELY UNCHANGED. C2-1 names the ANCESTRY terminations. EXACT
answers from identifier equality and walks no chain, so it has neither the traversal asymmetry the
review found nor a declared-parent claim to verify. Changing it was not requested and would alter
behaviour well beyond this correction; it is recorded here as an observation for the controller
rather than acted on unilaterally.
```

### Verification after C2

```text
docker compose exec -T backend pytest tests/ -k "business_authority"    356 passed
PF-1A-E1 authorization regression (four files)                          117 passed, unchanged
FULL backend regression: docker compose exec -T backend pytest          738 passed, 0 failed
python -m unittest discover -s scripts/tests                             58 passed
python scripts/validate_contract_fixtures.py                            all rules passed
python scripts/check_tracked_secrets.py                                 no findings (785 files)
alembic current == heads == 20260831_0030                               UNCHANGED
pyflakes over every new/changed file                                    clean
git diff --check                                                        clean
```

The full backend regression was run for C2 specifically, because C2 changes runtime kernel logic
rather than documentation or tests alone.

**The corrections are proved non-vacuous by execution, not by assertion.** With
`is_conforming_instant` neutralized in every importing module, all seven C2-2 naive-value tests
fail - `test_a_naive_effective_from_fails_closed_instead_of_raising` with exactly the
`TypeError: can't compare offset-naive and offset-aware datetimes` the review reported. With the
terminating ancestor accepted unverified, all thirteen C2-1 assertions fail while the four
verified-ancestor controls still pass. C2-3 and C2-4 are inherently non-vacuous: they assert a
field (`defects`) and an exact unpadded candidate key that did not exist before the correction.

Hosted CI and independent review remain controller/human-owned and are NOT claimed here. This
record does not state or imply that a further general independent review is required; it records
what this correction changed and what was proved.

### 26.4 C2 final contract reconciliation (4 September 2026)

The bounded closure of the single independent review. Two questions were put, and both are answered
here from the authoritative text rather than by inference. **No independent review was rerun; this
is closure of findings from the review that already occurred.**

#### Part A - temporal conformance is FIELD-SPECIFIC

The C2 handoff stated that "aware non-UTC instants are accepted and not rewritten". **That was too
broad, and both the wording and the code are corrected.** E2-A states TWO different temporal
requirements, and conflating them fails in opposite directions: applying the weaker rule everywhere
lets nonconforming provenance authorize, and applying the stronger rule everywhere rejects valid
configuration data.

```text
FIELD                   EXACT NORMATIVE TEXT                              REQUIRED SHAPE
as_of                   11.1 "Exactly one as_of governs a resolution.     AWARE AND UTC-NORMALIZED
                        It is timezone-aware and normalized to UTC"
                        10.2 defines NO input-normalization step at the
                        historical boundary
published_at            11.8.3 "published_at and retracted_at are         AWARE AND UTC-NORMALIZED
retracted_at            timezone-aware, normalized to UTC, and NOT NULL"
effective_from          8.1 "effective_from   inclusive, timezone-aware"  AWARE ONLY
                        - no UTC requirement anywhere in E2-A
declared_effective_to   8.1 "nullable, exclusive, immutable once          AWARE ONLY
                        published"; 11.2 "effective_to EXCLUSIVE,
                        nullable". Awareness is required by NECESSARY
                        IMPLICATION, because I-6 and the 11.4
                        asserted-interval rule COMPARE this value; no
                        section states a UTC rule for it
canonical_snapshot_at   7 / 9.1 / 9.2 describe it only as the canonical   AWARE ONLY
                        freshness indicator. Awareness is required
                        because the staleness rule subtracts it from
                        as_of; no section states a UTC rule for it
```

The single predicate introduced by C2-2 is therefore split into two, and each caller applies the one
its own field's text requires:

```text
is_conforming_instant(value)        AWARE (any offset)   effective_from, declared_effective_to,
                                                          canonical_snapshot_at
is_utc_normalized_instant(value)    AWARE AND offset 0    as_of, published_at, retracted_at
```

`is_utc_normalized_instant` constrains the OFFSET the value asserts, not the concrete `tzinfo`
object, so `timezone.utc`, a fixed zero-offset `timezone` and a zone at zero offset are accepted
alike; a non-zero offset is not.

**No value is ever rewritten.** A nonconforming instant is reported through that field's EXISTING
reason code - `INTERNAL_CONTRACT_VIOLATION` for `as_of`, `PUBLICATION_PROVENANCE_INVALID` for
recorded provenance, `AUTHORITY_CONFIGURATION_UNAVAILABLE` at the material boundary,
`HR_REFERENCE_UNAVAILABLE` at the canonical-reference seams. **No reason code was added.**
Normalizing a supplied `+05:30` `published_at` into UTC here would manufacture conformance for
material the provider published nonconforming, which is exactly the silent reinterpretation 11.8
forbids; and 10.2 grants the historical boundary no normalization step through which a caller's
non-UTC `as_of` could be repaired.

The corrected behaviour is proved in both directions, by execution rather than assertion. Collapsing
`is_utc_normalized_instant` onto `is_conforming_instant` - the over-broad rule the handoff described
- makes the `as_of`, `published_at` and `retracted_at` non-UTC tests fail while the `effective_from`,
`declared_effective_to` and `canonical_snapshot_at` non-UTC tests keep passing. A `+05:30`
`effective_from` set to the SAME ABSOLUTE INSTANT as `as_of` is still effective at the 11.2
inclusive boundary, which proves the business instant is preserved rather than re-read as a
wall-clock reading. A sweep of all six fields with naive and non-datetime values returns a
deterministic DENY + FAIL_CLOSED result every time: no `TypeError` or `ValueError` escapes.

#### Part B - the EXACT scope predicate: NOT A DEFECT

The C2 handoff flagged that EXACT answers from identifier equality without canonical resolution, and
asked whether that is the same defect C2-1 closed for ANCESTRY. **It is not.** E2-A 12.3 defines the
two predicates differently, in terms, and the difference is exactly the dereference:

```text
EXACT (scope_type,scope_id)  "satisfied only when the authoritative request context carries the
                             same canonical scope_type and scope_id."
ANCESTRY (optional)          "satisfied when the context's canonical scope is the operand's scope
                             or a descendant of it, RESOLVED ONLY THROUGH THE PROVIDER-NEUTRAL
                             CANONICAL ORGANISATION REFERENCE (get_org_unit, parent_org_unit_id,
                             at the same as_of)."
```

EXACT is canonical identifier equality between two ALREADY-CANONICAL scope identities; 12.3's rule
that "a raw provider identifier is never a scope_id" is what makes that equality meaningful without
a dereference. ANCESTRY alone asserts a RELATIONSHIP between two units, and 12.3 requires that
relationship to be resolved through the canonical organisation reference - which is why 9.2 says
`get_org_unit` "is required only where scope evaluation genuinely needs organisation relationships
(section 12)". 12.4 adds nothing to the contrary: it composes the two operands by intersection and
treats two EXACT operands naming different scopes as ordinary nonqualification, never as an
unresolvable organisation relationship.

The distinction C2-1 turned on is therefore absent from EXACT. Under ANCESTRY a SUBORDINATE unit
asserts a parent relationship, so the ancestor itself had to be canonically established before that
assertion could grant anything. EXACT makes no assertion about any other unit and walks no chain.

**No runtime change is made.** Existing coverage under manifest scenario V-10
(`test_an_exact_operand_matches_and_mismatches_deterministically` and
`test_an_assignment_operand_mismatch_reports_its_own_reason_code`) already demonstrates exact-equal
ALLOW, exact-different ordinary nonqualification with the correct per-operand reason code, and the
separate `SCOPE_CONTEXT_MISSING` fail-closed path when the context supplies no scope at all.

#### Verification after the final reconciliation

```text
docker compose exec -T backend pytest tests/ -k "business_authority"    356 passed
PF-1A-E1 authorization regression (four files)                          117 passed, unchanged
FULL backend regression: docker compose exec -T backend pytest          738 passed, 0 failed
python -m unittest discover -s scripts/tests                             58 passed
python scripts/validate_contract_fixtures.py                            all rules passed
python scripts/check_tracked_secrets.py                                 no findings
alembic current == heads == 20260831_0030                               UNCHANGED
pyflakes over every new/changed file                                    clean
git diff --check                                                        clean
```

### Engineering choices this document left open

```text
HR PORT LOCATION      a separate contracts-only backend/app/modules/hr_reference/ package rather
                      than authorization/, because the HR reference is not an Authorization-owned
                      capability (ADR-026, ADR-032, RMR-001). Section 20 requires this choice and
                      its reasoning to be recorded in the implementation handoff; it is.
PRODUCTION SEAM       section 9.6 option (a): the composition REFUSES to compose, so no resolver
                      object exists. It takes no input and consults none.
object_version ORDER  lexicographic over the canonical string form.
ALLOW RESULT REASON   empty, and only there; section 14 defines none for a grant and none was
                      invented.
STALENESS THRESHOLD   supplied, never defaulted, asserted in both directions.
ANCESTRY DEPTH        bounded at 16 hops - an engineering default for a bounded traversal, not a
                      PBL policy parameter.
```

### One defect found by self-review, and fixed

The kernel's own 16.4 accounting invariant fired on an entirely ORDINARY, VALID configuration: two
Business Authority Rules referencing ONE Business Authority Role — which is exactly how one role
carries an authority under two different scopes or parameter bands. Partial evaluations were keyed
on the object being evaluated rather than on the whole established path prefix, so two genuinely
distinct candidates collided and a correct `DENY + RESOLVED` became `INTERNAL_CONTRACT_VIOLATION` —
uncertainty manufactured out of valid configuration. Fixed by carrying the full established path
prefix in the candidate key; three regression tests added. Recorded here because it is the defensive
invariant doing precisely what 11.4a says such a guard is for, on a different invariant.

### Unchanged, and explicitly not claimed

No persistence, no migration, no `models_metadata` registration, no HTTP route, no API schema, no
frontend change, no business event, no permission change, no write path to published authority
configuration, no authoritative actor-person or HR provider, no production composition, no
production authority data, no bootstrap holder, no resolution of Q-10, and no claim whatsoever on
`READY_FOR_PRODUCTION_AUTHORITY_ACTIVATION`.

Per section 21, `PLAN.md`, `NEXT_STEPS.md` and `AGENT_HANDOFF.md` are reconciled **at package
closure**, not by the implementation package, and are therefore untouched.

## 27. Owner-authorized contract clarification — the bounded nonqualification fallback (correction C1)

Recorded 4 September 2026 as an **owner-authorized contract clarification made as part of
correction C1**, not as an implementation agent inventing a business rule. It is deliberately
additive: sections 2 to 26 are unchanged apart from the single new line in 14.1 that names the code
and points here. No existing reason code changed meaning, none was removed, and no fail-closed
behaviour was weakened.

### 27.1 Why the fallback exists

The path-level reason taxonomy of 14.1 must **not grow a new permanent reason code for every minor,
rare, fully understood nonqualification variant**. Left unchecked that produces a taxonomy nobody
can hold in mind, in which the specific codes stop carrying signal. One bounded fallback is
introduced instead:

```text
OTHER_NONQUALIFICATION
```

### 27.2 Strict semantics

```text
- It means authoritative state was COMPLETELY AND UNAMBIGUOUSLY RESOLVED, and this candidate/path
  does not qualify for a well-understood reason for which no existing specific path-level
  nonqualification reason precisely applies.
- It is ORDINARY NONQUALIFICATION only, and may contribute only to DENY + RESOLVED.
- It applies to a COMPLETE NONQUALIFYING PATH exactly as it applies to a partial evaluation
  (correction FU-5). The original implementation was narrower than this design: the fallback was
  reachable only on partial evidence, and a complete path could neither carry it nor its
  explanation. A complete path may carry it when authoritative state is completely and
  unambiguously resolved, no fail-closed condition exists, no existing specific nonqualification
  reason applies more precisely, and the candidate simply does not qualify.
- It can never cause an ALLOW, never appears on a QUALIFYING path, and is never the result-level
  reason of an ALLOW.
- It can NEVER represent uncertainty, malformed state, unavailable state, stale state, ambiguous
  state, contradictory state, unsupported semantics, provider failure, or a kernel invariant
  failure. Every one of those already has a FAIL-CLOSED code in 14.3 and keeps using it.
- The existing specific reasons of 14.1 remain AUTHORITATIVE and MUST be used wherever they apply.
  This is not a shortcut for avoiding a specific reason.
- There is deliberately NO `OTHER_FAIL_CLOSED`. INTERNAL_CONTRACT_VIOLATION remains the defensive
  kernel-invariant fail-closed category defined by 14.3, and nothing here touches it.
```

**Scope note on "never accompanies ALLOW".** The prohibition is on GRANTING and on DECIDING: the
fallback may never sit on a qualifying path and may never be an ALLOW's result-level reason. It may
appear in the evidence of a resolution whose ALLOW came from a **different, independently qualifying
path**, exactly as every other path-level nonqualification reason may — that is the already-accepted
multiplicity behaviour of 15.1 and of scenario NS-AG-02, and this clarification does not disturb it.

### 27.3 Mandatory deterministic explanation

Every use carries a short, deterministic, **kernel-generated** explanation, recorded on the
evidence record that carries the fallback - `PartialEvaluation.nonqualification_explanation` for a
partial evaluation, and `PathEvidence.nonqualification_explanation` for a complete nonqualifying
path (correction FU-5). The two are the same kind of string under the same rules.

```text
- it is built from a FIXED implementation-owned template over canonical identifiers;
- it never comes from provider text, user text, an exception message or any arbitrary external
  prose;
- it is STABLE for the same canonical input, so the evidence remains byte-identical under the
  determinism rules of 15.4 / 16.5;
- it does NOT participate in result selection or in ordering, and is deliberately absent from
  BOTH the 16.5 partial-evidence sort key and the 15.4 path sort key;
- it does NOT affect whether a path qualifies; it is audit evidence only;
- it contains, or is accompanied by, the canonical facts needed to understand the condition.
```

### 27.4 Aggregation behaviour

Unchanged mechanisms, applied to one more code. The fallback is an ordinary path-level reason, so:

```text
- it never enters the TOTAL FAIL-CLOSED DEFECT ORDER of 15.5, because it is not a defect;
- it is ordered with its partial evaluation under 16.5 like any other nonqualification;
- where EVERY nonqualifying path and partial evaluation shares it, the existing 15.3 branch 3c
  promotion may raise it to the result-level DENY + RESOLVED reason. The per-path explanations are
  retained in the evidence, so the result stays LEGIBLE rather than collapsing into an opaque code;
- it carries an explicit `reason_code_rank` like every other code (15.5 totality), ranked LAST among
  path-level reasons because a specific reason is always preferred where one applies.
```

### 27.5 First application: raw superset discovery and a historical parent reference (C1-1)

The condition that motivated the clarification, recorded normatively because it is a semantic rule
and not merely an implementation detail.

Candidate discovery is deliberately a **RAW SUPERSET** over published facts (9.3.1), so an object is
legitimately discovered through a reference carried only by a **historical** version of it. Two
shapes follow:

```text
CASE A   Rule V1 references Business Authority A; the CURRENT EFFECTIVE Rule version V2 references
         Business Authority B.
CASE B   Assignment V1 references Business Authority Role R; the CURRENT EFFECTIVE Assignment
         version V2 references Role R2.
```

In both, the object **is still discovered** for the historical reference — discovery is NOT narrowed,
and narrowing it would reintroduce exactly the prefiltering 9.3.1 forbids. Complete lineage is still
returned and still validated first. But once the current effective version has been established, it
belongs to a different parent and **must not participate in a grant path for the parent it no longer
carries**.

```text
- This is ORDINARY NONQUALIFICATION, reported as OTHER_NONQUALIFICATION with the deterministic
  explanation of 27.3, whose text makes the EXPECTED and the CURRENT reference unambiguous using
  canonical stable identifiers.
- It is NOT corruption: every row is well formed and the state is fully resolved.
- No RULE_* or ASSIGNMENT_* mismatch reason code is invented.
- The mismatch is evaluated ONLY AFTER authoritative lineage has been successfully established, so a
  malformed historical retraction or correction still surfaces its own fail-closed defect first and
  is never masked by the mismatch handling (11.3, 11.6).
- Where a SPECIFIC reason also applies - the effective version is inactive, or sits in a valid gap -
  that specific reason is used instead, because the effectiveness and activity checks precede the
  reference comparison.
```
