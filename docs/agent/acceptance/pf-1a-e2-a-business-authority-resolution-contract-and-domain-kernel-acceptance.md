# PF-1A-E2-A Acceptance — Business Authority Resolution Contract & Domain Kernel

## Status

**IMPLEMENTED AND SELF-REVIEWED. NOT INDEPENDENTLY ACCEPTED.**

Acceptance is recorded by the independent reviewer, never by the implementation
agent (`INDEPENDENT_IMPLEMENTATION_REVIEW_WORKFLOW.md`). This file is the
implementation agent's *acceptance preparation* record: it states what was
built, what was run, what the results were, and what remains for the reviewer
to verify. Nothing in it may be read as acceptance.

```text
Package ID:        PF-1A-E2-A
Package name:      Business Authority Resolution Contract & Domain Kernel
Normative source:  docs/agent/pf-1a/PF_1A_E2_A_BUSINESS_AUTHORITY_RESOLUTION_CONTRACT_AND_DOMAIN_KERNEL.md
Branch:            pf-1a-e2-a-business-authority-domain-kernel
Baseline commit:   52192ff15f7b7da636588958d3e8d37b54d805cb
Alembic head:      20260831_0030   (UNCHANGED - E2-A adds no migration)
Repository status: uncommitted, nothing staged.
                   36 new files; 1 modified tracked file - this package's own
                   definition document (sections 26/27 and one line in 14.1),
                   additive only, 0 deletions. Counts derived from git after
                   correction C1.
Risk class:        HIGH (security/authorization boundary plus workflow/
                   lifecycle/state-machine characteristics)
```

## What was implemented

A provider-neutral semantic contract and a pure, deterministic domain kernel
that answers one question — at a specified authoritative instant, does this
authenticated actor hold this Business Authority for this business context,
and what immutable evidence proves why — with no persistence, no migration,
no route and no production composition.

### Production files (all NEW)

```text
backend/app/modules/hr_reference/__init__.py                  provider-neutral HR CONTRACT package
backend/app/modules/hr_reference/contract.py                  canonical DTOs and lookup outcomes
backend/app/modules/hr_reference/ports.py                     ActorPersonPort, CanonicalHrReferencePort

backend/app/modules/authorization/business_authority/__init__.py
backend/app/modules/authorization/business_authority/contract.py    closed vocabularies, stage ranks,
                                                                    the explicit reason-rank table
backend/app/modules/authorization/business_authority/domain.py      the four families, payloads,
                                                                    material DTOs, request/context
backend/app/modules/authorization/business_authority/ports.py       AuthorityConfigurationPort
backend/app/modules/authorization/business_authority/material.py    the DTO/port well-formedness boundary
backend/app/modules/authorization/business_authority/lineage.py     temporal semantics, derived closure,
                                                                    provenance validation
backend/app/modules/authorization/business_authority/scope.py       scope predicates, intersection
backend/app/modules/authorization/business_authority/evaluators.py  the evaluator registry
backend/app/modules/authorization/business_authority/defects.py     defect records, the total sort key
backend/app/modules/authorization/business_authority/evidence.py    the four evidence collections
backend/app/modules/authorization/business_authority/kernel.py      the pure resolution kernel
backend/app/modules/authorization/business_authority/resolver.py    the two entry points, production seam
```

### Test-only files (all NEW)

```text
backend/tests/fixtures/pf_1a_e2_a_reference_providers.py   reference/synthetic providers, builders
backend/tests/fixtures/pf_1a_e2_a_scenarios.py             the declarative baseline world
backend/tests/fixtures/pf_1a_e2_a_corpus.py                the verification manifest, as data

backend/tests/test_business_authority_contract.py
backend/tests/test_business_authority_direct_malformed_input.py
backend/tests/test_business_authority_lineage.py
backend/tests/test_business_authority_discovery.py
backend/tests/test_business_authority_scope_and_evaluators.py
backend/tests/test_business_authority_actor_and_hr_boundary.py
backend/tests/test_business_authority_aggregation.py
backend/tests/test_business_authority_evidence.py
backend/tests/test_business_authority_kernel_invariants.py
backend/tests/test_business_authority_security_boundary.py
backend/tests/test_business_authority_coverage_manifest.py
```

The reference/synthetic providers live under `backend/tests/` deliberately, so
section 9.6's production-unreachability property is **structural** rather than
merely asserted: no production module can import what is not on the production
import path.

## Automated checks

Run inside an isolated Compose project for this worktree
(`COMPOSE_PROJECT_NAME=pbl-crm-e2a`), against PostgreSQL 17 at Alembic head
`20260831_0030`.

```text
docker compose exec -T backend pytest tests/ -k "business_authority"
    356 passed, 382 deselected                                     PASS
    (218 before correction C1, plus 49 C1 regression tests)

docker compose exec -T backend pytest \
    tests/test_authorization_baseline_equivalence.py \
    tests/test_authorization_compatibility_matrix.py \
    tests/test_authorization_repository.py \
    tests/test_authorization_route_migration_guard.py
    117 passed                                                     PASS
    (identical to the pre-change baseline measured on this branch)

docker compose exec -T backend alembic heads      20260831_0030 (head)   UNCHANGED
docker compose exec -T backend alembic current    20260831_0030 (head)   UNCHANGED

git diff --check                                   clean
git status --short                                 36 new files; 1 modified (this package's
                                                   definition document, additive only)
git diff --stat docs/agent/pf-1a/                  324 insertions(+), 0 deletions(-)
git diff --cached --name-only                      0 staged
```

Per-file counts:

```text
test_business_authority_contract.py                    24
test_business_authority_direct_malformed_input.py      19
test_business_authority_lineage.py                     26
test_business_authority_discovery.py                   17
test_business_authority_scope_and_evaluators.py        31
test_business_authority_actor_and_hr_boundary.py       23
test_business_authority_aggregation.py                 17
test_business_authority_evidence.py                    23
test_business_authority_kernel_invariants.py            7
test_business_authority_security_boundary.py           18
test_business_authority_coverage_manifest.py           24
test_business_authority_historical_reference.py        19   (correction C1-1)
test_business_authority_hr_freshness_and_status.py     19   (corrections C1-2, C1-4)
test_business_authority_provider_identity_binding.py   17   (follow-up FU-1)
test_business_authority_progressive_evidence.py        30   (follow-up FU-2, FU-3, FU-4, FU-5)
                                                      ---
                                                      314
```

**The full backend regression was NOT run in this session**, by explicit
instruction: it is reserved for controller/human validation before independent
review. The 382 deselected tests above are the pre-existing suite, collected
but not executed by the `-k` filter.

## Verification-class corpus — how each obligation is discharged

`backend/tests/fixtures/pf_1a_e2_a_corpus.py` restates the binding manifests
(E2-B sections 5.7 and 5.7A) as **data**, and
`test_business_authority_coverage_manifest.py` checks the implementation
against them mechanically rather than by reading prose. That is the check
which would have caught F-10.1.

```text
GROUP                              COUNT   ASSERTED BY
malformed authority-store fixtures    29   counts, one-class-per-fixture, never "N/A"
    class A                           14   storable, parity owed, expected reason present
    class B1                          12   not storable, parity excluded, named boundary
    class B2                           3   absent from this corpus, written rationale
valid-shape parity scenarios          12   no class label, parity still owed
non-store scenarios                   46   no class, closed seam, BOTH store answers
```

The three groups are asserted **pairwise disjoint**, and every item outside
class B2 is asserted to have a **named, executing** test that is neither
skipped nor xfailed.

### Class B1 — the permanent direct coverage, at its named boundary

Twelve shapes, twelve IDs, twelve distinctly named executing tests. Boundary
fidelity is asserted, not assumed: a PURE KERNEL fixture proves the material
passes `check_material_well_formed` (so it genuinely reaches the kernel), and
a DTO/PORT fixture proves that same function rejects it.

```text
ID       FIXTURE NAME                      BOUNDARY      EXPECTED
B1-01    DUPLICATE-OBJECT-VERSION          PURE KERNEL   AUTHORITY_LINEAGE_CONTRADICTORY
B1-02    ASSIGNMENT-TARGET-BOTH            PURE KERNEL   ASSIGNMENT_TARGET_INVALID (S7)
B1-03    ASSIGNMENT-TARGET-NEITHER         PURE KERNEL   ASSIGNMENT_TARGET_INVALID (S7)
B1-04    INTERVAL-END-BEFORE-START         PURE KERNEL   AUTHORITY_LINEAGE_CONTRADICTORY
B1-05    INTERVAL-END-EQUALS-START         PURE KERNEL   AUTHORITY_LINEAGE_CONTRADICTORY
B1-06    VERSION-ABSENT-EFFECTIVE-FROM     DTO / PORT    AUTHORITY_CONFIGURATION_UNAVAILABLE
B1-07    VERSION-ABSENT-ACTIVE-FLAG        DTO / PORT    AUTHORITY_CONFIGURATION_UNAVAILABLE
B1-08a   PROVENANCE-ABSENT-PUBLISHED-AT    PURE KERNEL   PUBLICATION_PROVENANCE_INVALID
B1-08b   PROVENANCE-ABSENT-RETRACTED-AT    PURE KERNEL   PUBLICATION_PROVENANCE_INVALID
B1-09a   PROVENANCE-ABSENT-TYPE            PURE KERNEL   PUBLICATION_PROVENANCE_INVALID
B1-09b   PROVENANCE-ABSENT-REFERENCE-ID    PURE KERNEL   PUBLICATION_PROVENANCE_INVALID
B1-10    PROVENANCE-UNKNOWN-TYPE           PURE KERNEL   PUBLICATION_PROVENANCE_INVALID
```

**B1-09a is the F-10.1 closure and is present, distinct and executing**, with
its mandatory companion case applying the same absence to a retraction
assertion's `publication_reference_type`. A separate test asserts
PROVENANCE-ABSENT-TYPE and PROVENANCE-UNKNOWN-TYPE are two distinct executing
tests over two distinct inputs, and that their covering test sets are
disjoint.

The DTO is constructible into every one of these shapes: a dedicated test
asserts the reference provider and the material DTOs impose **no**
identity-uniqueness, XOR, interval-sanity, provenance-presence, closed-enum or
referential restriction over the DTO-optional fields of 9.3.4.

### NS-K-01 — all three executable parts

```text
(a) UNREACHABILITY   an enumerative property test over a declared bounded family
                     (up to 3 versions x 4 distinct starts x 4 declared ends,
                     evaluated at 13 boundary instants) asserting AT MOST ONE
                     effective version for every shape passing the
                     duplicate-start, nonsensical-interval and explicit-overlap
                     conditions. It computes effectiveness from the derived
                     intervals directly, so it tests the 11.4a THEOREM rather
                     than the implementation's assumption of it. A guard asserts
                     more than 100 shapes were actually exercised.
(b) DEFENSIVE BRANCH the residual 11.6 clause is reached by injecting a
                     fabricated internal state directly (it is unreachable
                     through any port, which is the point) and asserts
                     DENY + FAIL_CLOSED / AUTHORITY_VERSION_AMBIGUOUS with
                     ordinary 16.4 evidence. A companion test asserts the guard
                     has not been removed as dead code.
(c) RANK TOTALITY    AUTHORITY_VERSION_AMBIGUOUS carries an explicit declared
                     reason_code_rank, even though no provider can produce it.
```

## Acceptance criteria (section 19) — implementation agent's assessment

The reviewer verifies these independently; this column records only what the
implementation intends and what test demonstrates it.

```text
A  authority_code only, no name/code/title/role anywhere in the decision path   DEMONSTRATED
B  actor -> canonical person through the port; no client-supplied identity      DEMONSTRATED
C  person and position assignments; incumbency re-resolved at the same instant  DEMONSTRATED
D  active_flag immutable and distinct from effectiveness, all four families     DEMONSTRATED
E  complete lineage material plus RAW identity-only discovery; ill-formed and
   unavailable material both fail closed; empty versions[] is a truthful answer DEMONSTRATED
F  one business-effective as_of; no caller as_of and no recorded-time cutoff;
   recorded time is validation input only; corrected reconstruction, not replay DEMONSTRATED
G  half-open boundaries; immutability; append-only closure; durable dereference DEMONSTRATED
H  the 11.4 asserted-interval rule exactly, including explicit-overlap failure  DEMONSTRATED
I  the complete candidate path; scope composes by intersection, GLOBAL as top   DEMONSTRATED
J  15.3 total precedence; relevance is identity-only; unestablishable fails     DEMONSTRATED
J2 the total defect order; result reason is the first defect under it           DEMONSTRATED
K  registry-based evaluation, explicit boundaries/units, no expression language DEMONSTRATED
L  every 14.3 case fails closed with the correct code                           DEMONSTRATED
L2 exactly one class per authority-store fixture; B1 direct coverage at a named
   boundary; B2 absent with a rationale; the 9.3.4 split holds as declared      DEMONSTRATED
L3 the taxonomy is SCOPED; three disjoint groups; no "N/A"; no invented seam    DEMONSTRATED
L4 the residual clause is decided, retained, and verified by NS-K-01            DEMONSTRATED
L5 provenance covered shape by shape; ABSENT-TYPE distinct and executing        DEMONSTRATED
M  multiple grant paths retained in deterministic order                         DEMONSTRATED
N  first-class negative evidence; no fabricated pairs; populated established     DEMONSTRATED
O  reference providers test-only and production-unreachable                     DEMONSTRATED
P  no persistence, migration, model registration, route or frontend change      DEMONSTRATED
Q  no write path to published authority configuration anywhere                  DEMONSTRATED
R  no production/bootstrap authority data; synthetic fixtures labelled as such   DEMONSTRATED
S  every PF-1A-E1 protection intact and unmodified                              DEMONSTRATED
T  full backend regression                          RESERVED FOR CONTROLLER/HUMAN VALIDATION
   Alembic current == heads == 20260831_0030, unchanged                         VERIFIED
U  tracked-secret scan                              RESERVED FOR CONTROLLER/HUMAN VALIDATION
   git diff --check clean                                                       VERIFIED
V  a fresh independent bounded review returns ACCEPTED                          NOT PERFORMED
```

## Engineering decisions recorded, as section 20 requires

### HR port location — `hr_reference`, not `authorization`

Section 20 records this as an engineering layout decision with two defensible
answers, and requires the choice and its reasoning to be recorded here.

The canonical HR/actor-person port lives in a separate, contracts-only
`backend/app/modules/hr_reference/` package rather than inside
`authorization/`. Placing it under `authorization/` would misrepresent
ownership: the HR reference is not an Authorization-owned capability
(ADR-026, ADR-032, `RMR-001`). The package contains protocols and canonical
DTOs only — no provider, no persistence, no route.

### Production composition — option (a), refuse to compose

Section 9.6 permits two behaviours for a production composition lacking
authoritative providers. This package chooses **(a) refuse to compose at all,
so no resolver object exists**: `build_production_resolver()` raises
`ProductionCompositionUnavailableError`. It takes no input and consults none,
so no environment variable, settings flag, feature toggle or dependency
override can select a synthetic provider.

### `object_version` ordering

`object_version` is compared lexicographically over its canonical string form.
That is the only ordering the contract needs — for the 11.8.3
non-decreasing-`published_at` rule and for the 15.5 sort key — and it is
deterministic and provider-independent. A publisher must therefore use a
lexicographically ordered version identity; the fixtures use zero-padded
numerics. Recorded because it is an implementation choice the contract leaves
open.

### `result_level_reason` on an ALLOW

Empty, and only there. Section 14 defines result-level reasons for
DENY + RESOLVED and DENY + FAIL_CLOSED and defines none for a grant; the
reason a grant happened is the qualifying paths themselves. No reason code was
invented to fill the field, and a test asserts none was.

### Staleness threshold

The kernel accepts a **supplied** `hr_staleness_threshold_seconds` and invents
no default. A test asserts both directions: with a threshold supplied the same
snapshot fails closed as `HR_REFERENCE_STALE`, and with none supplied it
resolves — which is what proves no default value was quietly assumed.

## Manual checks

E2-A has no UI, no route and no runtime surface, so the usual manual
happy-path and permission checks do not apply and are not claimed. The
equivalent human-inspectable evidence is:

```text
- the resolution of the baseline valid world was inspected directly and returns
  ALLOW + RESOLVED with one qualifying path, all four object/version pairs, and
  a populated established_state;
- the candidate-key collision described under "Self-review findings" was
  reproduced by hand before being fixed, and re-checked by hand afterwards;
- git status was inspected directly and confirms 36 new files and exactly ONE
  modified file - this package's own definition document, whose diff is 119
  insertions and 0 deletions (the section 21 implementation-outcome record, the
  correction-C1 record and the owner-authorized clarification of section 27).
  No production or test file outside this package is touched, and no E1 file,
  no migration and no frontend file is touched at all.
```

## Self-review findings and corrections

```text
1. CANDIDATE-KEY COLLISION WHEN TWO RULES SHARE ONE ROLE.  FOUND AND FIXED.
   The 16.4 accounting invariant ("every candidate touched appears in exactly
   one collection") fired on an entirely ORDINARY configuration: two Business
   Authority Rules referencing ONE Business Authority Role - the same role
   carrying the authority under two different scopes or parameter bands. The
   candidate key for role-level and assignment-level PARTIAL evaluations was
   keyed on the object being evaluated rather than on the whole established
   path prefix, so the two candidates collided and a correct DENY + RESOLVED
   became INTERNAL_CONTRACT_VIOLATION - uncertainty manufactured out of valid
   configuration. Fixed by carrying the full established path prefix in the
   candidate key. Three regression tests added
   (test_business_authority_evidence.py, NS-EV-05). This is the kernel's own
   defensive invariant doing exactly what section 11.4a says such a guard is
   for, on a different invariant.

2. NAIVE SOURCE SCANS FIRED ON PROSE.  FOUND AND FIXED.
   The SECURITY / BOUNDARY assertions searched raw source for things that must
   not appear in CODE - an E1 role constant, a literal ADMIN comparison, an
   environment read - and therefore failed on the accurate DOCSTRINGS that
   discuss those very prohibitions. Fixed with a `_code_only` helper that
   strips docstrings and comments while KEEPING other string literals, because
   a literal "ADMIN" in code is exactly what those tests exist to catch.

3. MISSING IMPORT IN scope.compose.  FOUND AND FIXED.
   SCOPE_COMPOSITION_NOT_SATISFIED was referenced but not imported, so the
   two-EXACT-operands composition branch raised NameError. Caught by the V-11
   test; import added.

4. B2 RATIONALE ASSERTION TOO NARROW.  FOUND AND FIXED (test-side).
   The manifest test required every class B2 rationale to mention where
   `object_id` lives. That is the correct justification for B2-01 and B2-02,
   but B2-03's justification is different and equally valid: its counterpart
   COLLAPSES ONTO class A fixture A-11. The assertion now accepts both of the
   two justifications the contract actually gives, and no more.
```

## Known limitations

```text
- NS-DO-03 (defects across families at ONE stage) is proved DIRECTLY against
  the canonical defect sort key, with defect records constructed at one stage
  across all four families, plus an end-to-end complement showing stage_rank
  ordering across families. This kernel detects each family's lineage defects
  at that family's OWN stage (S3 authority, S4 rule, S5 role, S6 assignment),
  so a same-stage cross-family collision cannot be composed through the ports.
  The property the scenario is ABOUT is the total order itself, and that is
  what is tested. Recorded here explicitly so the reviewer can judge the
  placement rather than discover it.

- "Reversing traversal direction" is exercised by reversing the PROVIDER's
  return order, which reverses the order in which candidates and versions reach
  the kernel. That is the only traversal freedom this kernel has, since it
  traverses in one direction by construction.

- A truncated read presented as COMPLETE cannot be detected by the kernel from
  the material alone - which is precisely why 9.3.2 places that obligation on
  the PROVIDER. E2-A proves the conformance assertion catches such a provider,
  and that the correct behaviour (completeness = UNAVAILABLE) fails the
  resolution closed. The end-to-end half belongs to E2-B section 9.

- Ancestry traversal depth is bounded at 16 hops (MAX_ANCESTRY_DEPTH). The
  value is an engineering default for a bounded traversal, not a PBL policy
  parameter; depth exhaustion fails closed with ORG_HIERARCHY_UNRESOLVABLE.

- The full backend regression, the tracked-secret scan and hosted validation
  are reserved for controller/human validation before independent review.
```

## What this package does NOT deliver

Restated because section 9.6 forbids any record describing E2 as delivering a
production-callable resolver while its dependencies are unmet:

```text
- no persistence, no Alembic migration, no models_metadata registration;
- no HTTP route, request/response schema or API surface;
- no authoritative actor-person provider and no live HR/organisation provider;
- no production composition - the seam deliberately REFUSES to compose;
- no production authority data, no bootstrap holder, no resolution of Q-10;
- no consumer retrofit, no delegation, no HR lifecycle automation;
- no claim whatsoever on READY_FOR_PRODUCTION_AUTHORITY_ACTIVATION.
```

## Reviewer notes

The independent-review attack surface is section 22 (37 items), read together
with the core rubric of `BOUNDED_INDEPENDENT_REVIEW_METHOD.md` section G and
the workflow/lifecycle overlay in section H.2. Risk classification: **high**.

The highest-value probes, in the implementation agent's own judgement:

```text
17a  V1 [t0, t3) with V2 from t2 - the rejected min(...) formula probe. The
     test additionally resolves at an instant INSIDE the would-be truncation
     and asserts it still fails closed, because that is where a reintroduced
     min(...) would hide.
12a  can a MALFORMED retraction make the only requested-code-bearing or only
     reference-bearing version invisible? (A-17, both companions)
17f  construct LineageMaterial with publication_reference_type absent and
     everything else valid, call the kernel, require
     PUBLICATION_PROVENANCE_INVALID (B1-09a)
25a  shuffle provider rows, reverse order, re-run: the reason must not move
24   a fail-closed defect in RELEVANT state masked by another qualifying path
     (NS-AG-03)
```

## Correction C1 (4 September 2026)

A controller inspection of this candidate found five items. All five are
corrected. The package remains **UNCOMMITTED and NOT independently accepted**,
and no completion pointer is advanced.

### C1-1 — raw superset discovery must not grant through a historical parent reference

Two reproduced FAIL-OPEN defects. A Rule whose CURRENT effective version
referenced Business Authority B could still grant Business Authority A, because
A was carried only by a HISTORICAL version of that Rule; and the same one level
down, for an Assignment and its Business Authority Role.

The fix does **not** narrow discovery. Discovery remains raw and a superset
(9.3.1), complete lineage is still validated first, historical rows are not
discarded, and a malformed historical retraction or correction still surfaces
its own fail-closed defect. The parent-reference comparison happens only AFTER
authoritative lineage has been established, and the mismatch is ordinary
nonqualification - not corruption. No `RULE_*` or `ASSIGNMENT_*` mismatch code
was invented.

### C1-2 — HR staleness must apply to every HR state used

The supplied threshold was enforced for actor/person and employment state only.
Position, Incumbency and Organisation Unit ancestry were unchecked, and the
controller reproduced ALLOW + RESOLVED with stale Position/Incumbency and,
separately, with stale ancestry.

All five seams now share ONE implementation - `is_snapshot_stale` on the
canonical freshness indicator itself - applied against the SAME supplied
threshold and the SAME authoritative `as_of`. No default threshold is invented
and no second clock is consulted.

### C1-3 — complete evidence for retractions and HR snapshots

`recorded_retracted_at_of_participating_assertions` existed but was always
empty. Valid participating retraction assertions now carry their recorded times
into object evidence, ordered by the assertion's own canonical identity rather
than by timestamp value or provider order. An invalid assertion still fails the
resolution closed and can never reach successful evidence.

Path evidence retained only the employment snapshot. It now accounts for every
canonical HR state actually relied upon - actor/person, employment, Position,
Incumbency and every Organisation Unit ancestry hop - in establishment order,
with nothing omitted and no provider-specific identifier exposed.

### C1-4 — an unknown / ill-formed HR lookup status must never fail open

`HrLookup(status="BOGUS", value=<fresh ACTIVE employment>)` proceeded to
ALLOW + RESOLVED. Every HR seam now validates the status against the CLOSED
vocabulary BEFORE interpreting any attached value, and a non-contract status
takes the existing `HR_REFERENCE_UNAVAILABLE` classification. No new reason code
was invented, and an unknown status is never silently mapped onto `OK`,
`MISSING` or any other known state. `MISSING` and `AMBIGUOUS` remain
distinguishable per seam.

### C1-5 — the implementation-outcome documentation was false

Section 26 claimed "16 new files, 0 modified files" and "no existing file
modified". The 16 came from a `git status --short` line count in which two new
DIRECTORIES each collapsed to a single entry, and the "0 modified" ignored the
definition document itself. All counts in this record, in the continuity handoff
and in section 26 are now derived from git.

### The owner-authorized clarification C1 required

`OTHER_NONQUALIFICATION` is introduced as the ONE bounded path-level fallback,
recorded normatively in section 27 of the definition and named in 14.1. It means
authoritative state was completely and unambiguously resolved and the candidate
does not qualify for a well-understood reason no existing specific reason
precisely covers. It contributes only to DENY + RESOLVED, never sits on a
qualifying path, is never an ALLOW's result-level reason, and can never
represent uncertainty, malformed, unavailable, stale, ambiguous or contradictory
state, unsupported semantics, provider failure or a kernel invariant failure -
each of which keeps its own fail-closed code. There is deliberately **no**
`OTHER_FAIL_CLOSED`, and `INTERNAL_CONTRACT_VIOLATION` is unchanged.

Every use carries a deterministic, kernel-generated explanation built from a
fixed template over canonical identifiers, recorded on the partial evaluation as
`nonqualification_explanation`. It is stable for the same canonical input, never
derived from provider text, user text or an exception message, and deliberately
absent from the 16.5 sort key so it can take no part in result selection or
ordering.

### Tests added by C1

```text
test_business_authority_historical_reference.py       19   C1-1, all nine required proofs
test_business_authority_hr_freshness_and_status.py    19   C1-2 and C1-4, every seam
test_business_authority_evidence.py                   +9   C1-3 retraction and HR snapshot evidence
test_business_authority_contract.py                   +2   the bounded fallback's own semantics
                                                     ----
                                                       49
```

Four of these are deliberate NEGATIVE CONTROLS, so the positive assertions
cannot pass vacuously: the same current Rule still grants the authority it does
carry; the same current Assignment still grants through its current Role; a
position path with every HR state fresh still resolves; and the bogus-status
fixture is asserted to attach a genuinely plausible, fresh, ACTIVE value, so the
C1-4 tests prove the STATUS is what is rejected rather than the absence of a
value.

### Verification after C1

```text
docker compose exec -T backend pytest tests/ -k "business_authority"   356 passed
E1 authorization regression (four files)                               117 passed, unchanged
alembic current == heads == 20260831_0030                              UNCHANGED
git diff --check                                                       clean
```

Full backend regression remains RESERVED FOR CONTROLLER/HUMAN VALIDATION and is
not claimed here. No hosted CI was run. Nothing is staged, committed, pushed,
merged or opened as a pull request.

## Correction C1 follow-up — controller closure (4 September 2026)

A controller inspection of the post-C1 candidate found five further bounded
issues plus a documentation reconciliation. All are closed. The package remains
**UNCOMMITTED and NOT independently accepted**, no completion pointer is
advanced, and no full backend regression, hosted CI or independent review has
been run.

### FU-1 — a provider response must be bound to the identity requested

The most serious finding, reproduced as **fail-open ALLOW** at several seams. C1
validated a response's lookup status, value type and freshness, but not that the
object RETURNED was the object ASKED ABOUT. A fresh, otherwise-valid response
describing a different canonical object was accepted as the requested object's
authoritative state.

Every authoritative provider response used for authorization is now canonically
bound back to the identity requested, at all six seams:

```text
actor -> canonical person   the returned ActorPersonReference must be the mapping for the
                            AUTHENTICATED ACTOR requested - a reference for another actor,
                            even one whose person holds the authority, cannot authorize
employment                  the returned state must be for the canonical person requested
Position                    the returned reference must identify the position requested
Incumbency                  the incumbency's own canonical position must be the one requested
Organisation Unit           each ancestry hop's response must identify the unit requested,
                            or the traversal walks a chain nobody asked about
authority lineage           get_lineage material must carry the requested object_family AND
                            object_id
```

A mismatch means the requested authoritative fact was **not established**. It
takes an existing FAIL_CLOSED code — `HR_REFERENCE_UNAVAILABLE` at the actor/HR
seams, `AUTHORITY_CONFIGURATION_UNAVAILABLE` at the authority-configuration seam
— is never substituted, coerced or repaired, and is never ordinary
nonqualification. Identity is checked BEFORE freshness, deliberately: a response
that is not about the requested object has no meaningful freshness to assess.
The foreign identity is never echoed into evidence.

`get_published_version` was audited as the remaining canonical provider seam. The
kernel never calls it during resolution — dereference is an evidence/audit
operation, not an authorization input — so there is no unbound seam. A test pins
that property, and fails if a future change routes resolution through it.

### FU-2 — partial evidence must contain all state already established

A candidate that reached S9 and failed closed retained only the requested
Business Authority, although its Rule, Role and Assignment had all been
established. Evidence accounting is now progressive and candidate-scoped at
every stage S1–S9, carrying the object/version pairs **with** their
active/effective evaluations, the canonical HR state, the scope operands and the
evaluator state already established. A stale failure additionally retains the
very reference and snapshot responsible for it — while an identity-mismatched
response, which was never about the requested object, is not cited at all.

Nothing is fabricated, no placeholder pair is emitted, and one candidate never
inherits another's established state: the trail is reset at every rule and every
assignment boundary.

### FU-3 — the employment-state vocabulary is closed

`employment_status = "ALIEN_STATUS"` produced DENY + RESOLVED /
`EMPLOYMENT_NOT_ACTIVE`. That code is for KNOWN, resolved non-active states
(`INACTIVE`, `ON_LEAVE`, `LEFT`); an unknown one is not authoritative state at
all and now fails closed with `HR_REFERENCE_UNAVAILABLE`. Matching is exact —
never cased, fuzzy or prefixed. `employment_status` is the only closed-vocabulary
field carried inside an HR reference DTO; `HrLookup.status` was already validated
by C1, and the other four DTOs carry no enum.

### FU-4 — no provider prose or order artefact in canonical evidence

Provider exception text was being interpolated into evidence detail, and
malformed-material diagnostics carried list indices. Neither is stable domain
data. Canonical evidence now uses fixed kernel-owned templates over canonical
identifiers only; malformed records are named by their own canonical identity
rather than by position; and material records are checked in canonical order so
a provider that reorders its rows cannot change which rejection is reported.

### FU-5 — the bounded fallback applies to complete paths too

`OTHER_NONQUALIFICATION` was reachable only on partial evaluations, and an
invariant actively rejected it on a complete nonqualifying path — narrower than
the owner's C1 design. A complete path may now carry it, and its deterministic
explanation, under the same bounded conditions. It still never appears on a
qualifying path, never masks a fail-closed defect, never displaces a specific
reason, and is never an ALLOW's reason. There is still no `OTHER_FAIL_CLOSED`.

The current scope and evaluator predicates always supply a specific reason, so
the complete-path branch is a **defensive** one — retained in the same spirit as
the 11.4a single-effective-version invariant, and proved by bounded injection
rather than by inventing a new PBL policy scenario. Reporting a complete path
with no reason at all would be strictly worse: the denial would be
unexplainable.

### FU-6 — documentation reconciliation

Two stale statements corrected: the conformance corpus is 15 test files, not 11;
and "no existing file modified" was false — this package's own definition
document is modified. All counts are derived from git.

### Tests added by the follow-up

```text
test_business_authority_provider_identity_binding.py   17   FU-1, all six seams plus adversarial
                                                            combinations
test_business_authority_progressive_evidence.py        30   FU-2 (S1-S9), FU-3, FU-4, FU-5
                                                     ----
                                                       47
```

Negative controls are included throughout, so the positives cannot pass
vacuously: the same providers still authorize when they answer about the object
requested; every legitimate employment state still behaves as defined; every
existing specific nonqualification reason still wins where it applies; and a
fail-closed defect still wins over the complete-path fallback.

One pre-existing test was corrected rather than added:
`test_a_partial_evaluation_records_the_pairs_that_WERE_established` asserted the
FU-2 defect itself (only the Authority retained) and now asserts the corrected
progressive behaviour.

### Verification after the follow-up

```text
docker compose exec -T backend pytest tests/ -k "business_authority"   356 passed
E1 authorization regression (four files)                               117 passed, unchanged
alembic current == heads == 20260831_0030                              UNCHANGED
pyflakes over all new/changed files                                    clean
git diff --check                                                       clean
```

Full backend regression, hosted CI and independent review all remain
controller-owned and are NOT claimed here.

## Correction C2 — post-independent-review closure (4 September 2026)

The frozen pre-C2 candidate was submitted for independent review. **The independent review returned
CORRECTION_REQUIRED**, naming four material findings. All four are closed. The package remains
**UNCOMMITTED and NOT independently accepted**, no completion pointer is advanced, and hosted CI is
not run. This record does not state or imply that a further general independent review is required.

### C2-1 — an ancestry operand terminated on an unverified claim

The confirmed fail-open, and the most serious of the four. The bounded upward traversal validated
every organisation unit it PASSED THROUGH but not the ancestor it TERMINATED ON, so a subordinate
unit could satisfy an ANCESTRY operand by merely **declaring** the operand's scope as its parent,
while that ancestor had no canonical record at all. The claim belonged to the subordinate; believing
it granted authority over a superior unit the canonical reference could not even confirm existed.
The ANCESTRY self-match had the same shape, answering from two identifiers without consulting the
reference once.

Both terminations now resolve the target through one extracted `_resolve_org_unit` — contract
status, value type, identity binding, freshness — under the same `as_of` and the same supplied
threshold as every other hop, and the terminating ancestor is retained in the path's HR evidence.
The EXACT predicate is deliberately unchanged: it walks no chain and has no declared-parent claim to
verify, so changing it was neither requested nor within this correction.

### C2-2 — every authoritative instant must conform before it is used

A naive `effective_from` raised an uncaught `TypeError`; a naive `published_at` was accepted and
**allowed authorization**. One shape check now runs before any comparison at every seam:

```text
as_of at kernel entry (incl. the historical resolver)  INTERNAL_CONTRACT_VIOLATION
effective_from, declared_effective_to                  AUTHORITY_CONFIGURATION_UNAVAILABLE
published_at, retracted_at                             PUBLICATION_PROVENANCE_INVALID
canonical_snapshot_at (HR and organisation seams)      HR_REFERENCE_UNAVAILABLE
```

No new reason code. An aware instant in a non-UTC offset is accepted and **not** rewritten: it
denotes the same moment, Python compares aware datetimes by absolute instant, and section 11.8
forbids silently reinterpreting a supplied instant.

### C2-3 — the established version is evidence before it is judged

A Rule, Role or Assignment version reached the candidate trail only after the active-flag and
reference-mismatch checks had passed, so the two commonest ordinary denials named the object but not
the version the decision was taken on. It is now recorded first — as audit evidence, never
permission, with a test proving early recording grants nothing.

### C2-4 — one partial evaluation per logical candidate

A lineage breaking several rules emitted one partial per defect, inflating the apparent number of
candidates examined and forcing the candidate key to be padded with the reason code and detail
**text**. One partial now carries `defects`, with `defect` derived as the first; the key is
canonical identity alone; `ordered_defects` is unchanged. Closing this exposed a latent collision —
two Rules referencing one broken Role keyed on the role alone, previously masked by the padding —
which is fixed and pinned by a test.

### Tests added

```text
test_business_authority_c2_corrections.py   42   C2-1 (13), C2-2 (17), C2-3 (4), C2-4 (8),
                                                 counted as pytest collects them, parametrized
                                                 cases included; every group carries its own
                                                 negative control
```

Every group carries a negative control, so no assertion can pass vacuously: a verified ancestor
still allows, a non-UTC aware world still resolves identically, early evidence still does not grant,
and two genuinely different broken candidates remain two partials. One pre-existing test
(`test_path_evidence_accounts_for_every_hr_state_actually_relied_upon`) was reconciled rather than
added: the terminating ancestor is now genuinely relied upon, so it must appear in HR evidence, and
it was given its own distinct snapshot value so omitting it again could not hide behind another
unit's. The reference HR provider gained two per-unit knobs (`org_unit_results`,
`returned_org_unit_ids`), because the existing whole-provider knobs cannot express the shape this
correction is about: a subordinate that resolves perfectly while its declared ancestor is the
unresolvable one.

### Non-vacuity, proved by execution

With `is_conforming_instant` neutralized in every importing module, all seven C2-2 naive-value tests
fail — `effective_from` with exactly the `TypeError: can't compare offset-naive and offset-aware
datetimes` the review reported. With the terminating ancestor accepted unverified, all thirteen C2-1
assertions fail while the four verified-ancestor controls still pass. C2-3 and C2-4 assert a field
and an exact unpadded key that did not exist before the correction.

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
repository: 36 untracked, 1 modified tracked, 0 staged, 0 commits ahead of the baseline
prohibited scope: no migration, no route, no frontend, no CI, no compose change;
                  backend/app/modules/authorization/contract.py untouched
```

The full backend regression was run for C2 specifically, because C2 changes runtime kernel logic
rather than documentation or tests alone. Hosted CI and independent review remain controller-owned.

## C2 final contract reconciliation (4 September 2026)

Bounded closure of the single independent review. No review was rerun.

### Part A — temporal conformance is FIELD-SPECIFIC

The C2 handoff's phrase *"aware non-UTC instants are accepted and not rewritten"* was **too broad**.
Both the wording and the code are corrected. E2-A states two different requirements:

```text
as_of                   11.1  "timezone-aware and normalized to UTC"          AWARE + UTC
published_at            11.8.3 "timezone-aware, normalized to UTC, NOT NULL"  AWARE + UTC
retracted_at            11.8.3 same sentence                                  AWARE + UTC
effective_from          8.1   "inclusive, timezone-aware" — no UTC rule       AWARE ONLY
declared_effective_to   8.1 / 11.2 — awareness by necessary implication       AWARE ONLY
                        (I-6 and the 11.4 rule COMPARE it); no UTC rule
canonical_snapshot_at   7 / 9.1 / 9.2 — freshness indicator only; awareness   AWARE ONLY
                        required because staleness subtracts it from as_of
```

The single C2-2 predicate is split into `is_conforming_instant` (aware) and
`is_utc_normalized_instant` (aware, zero offset). **Nothing is ever rewritten**: a nonconforming
value is reported through that field's existing reason code, and no reason code was added.
Normalizing a supplied `+05:30` `published_at` would manufacture conformance for material the
provider published nonconforming — the silent reinterpretation §11.8 forbids — and §10.2 grants the
historical boundary no normalization step for a caller's `as_of`.

Proved in both directions: collapsing the stronger predicate onto the weaker makes the three
UTC-normalized tests fail while the three aware-only tests keep passing. A `+05:30` `effective_from`
at the *same absolute instant* as `as_of` is still effective at §11.2's inclusive boundary, proving
the instant is preserved rather than re-read as a wall-clock value. Sweeping all six fields with
naive and non-datetime junk returns a deterministic DENY + FAIL_CLOSED every time — no `TypeError`
or `ValueError` escapes.

### Part B — the EXACT scope predicate: **NOT A DEFECT**

§12.3 defines the two predicates differently, and the difference *is* the dereference: EXACT is
"satisfied only when the authoritative request context carries the same canonical scope_type and
scope_id"; ANCESTRY is satisfied by descent "**resolved ONLY through the provider-neutral canonical
organisation reference**". §9.2 confirms it — `get_org_unit` "is required only where scope evaluation
genuinely needs organisation relationships". §12.4 adds nothing contrary.

The C2-1 distinction is absent from EXACT: under ANCESTRY a **subordinate asserts a parent
relationship**, so the ancestor had to be canonically established before that assertion could grant
anything. EXACT asserts nothing about another unit and walks no chain. **No runtime change.**
Existing V-10 coverage already demonstrates exact-equal ALLOW, exact-different ordinary
nonqualification with the correct per-operand reason, and the separate `SCOPE_CONTEXT_MISSING`
fail-closed path.

### Verification

```text
E2-A focused          356 passed        E1 regression      117 passed, unchanged
full backend          738 passed / 0    scripts/tests       58 passed
fixtures / secrets    clean             alembic             20260831_0030 UNCHANGED
pyflakes              clean             git diff --check    clean
repo                  36 untracked, 1 modified tracked, 0 staged, 0 ahead
prohibited scope      none; authorization/contract.py untouched
```
