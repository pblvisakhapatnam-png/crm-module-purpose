# PF-1A-E2-B Acceptance Record — Persisted Published Authority Store & Runtime Wiring

**POST-INTEGRATION CURRENT STATUS — 6 September 2026. This note supersedes every earlier
"current status", "CURRENT CONTROL STATE", "NOT ACCEPTED" and "next review gate" statement below
for present-state purposes; those earlier statements are retained only as historical evidence of
the C1-C10 review/correction sequence. PF-1A-E2-B is COMPLETE and integrated on `main` through
PR #20 at merge commit `97e82b62a2cc916d90d50e1e0a5854dc133ed8b6`. Its C1-C10 chronology is
not retroactively rewritten. ADR-035, which was briefly integrated while E2-B was already in that
review sequence, is withdrawn as an active architecture decision by the subsequent review-method
simplification; future correction-cycle sequencing is governed by
`docs/agent/architecture/BOUNDED_INDEPENDENT_REVIEW_METHOD.md` and
`docs/agent/architecture/INDEPENDENT_IMPLEMENTATION_REVIEW_WORKFLOW.md`.

**Status: IMPLEMENTED, under independent-review correction, NOT ACCEPTED.** Acceptance is recorded
by the independent reviewer, never by the implementation agent. This document is the evidence
record the bounded independent review consumes, not a claim of acceptance. For the authoritative,
present repository and review status, see the **CURRENT CONTROL STATE** in section 0 immediately
below.

**The one material blocker raised on 4 September 2026 is CLOSED by controller-authorized
reconciliation C1 (5 September 2026), recorded in full in section 12.** It was an
implementation-time TEST-CONTRACT contradiction at the E2-A -> E2-B phase boundary - two stale
PHASE-LOCAL structural assertions in the integrated PF-1A-E2-A test corpus - not an E2-B semantic
implementation defect. Exactly those two assertions were revised, in one file, under narrow
controller authorization. No E2-A semantic rule, fail-closed behaviour, ADMIN protection, E1
protection or synthetic-provider reachability protection changed, and no E2-A or E2-B runtime
source changed.

```text
Package                        PF-1A-E2-B
Historical inception baseline  22a4b28a2679503187a9db4cd5be580a8eac39ec
                               The commit this package was branched from and originally
                               reviewed against. It is NO LONGER the review base; for the
                               current main/review base and the other endpoints, see the
                               CURRENT CONTROL STATE (section 0).
Branch                         pf-1a-e2-b-persisted-published-authority-store-runtime-wiring
Alembic head at start          20260831_0030   (verified from backend/alembic/versions/,
                                                `alembic heads` and `alembic current`)
New revision                   20260904_0031   down_revision = 20260831_0030
Production composition         OPTION (a) - REFUSE TO COMPOSE (section 5.3)
```

---

## 0. CURRENT CONTROL STATE — authoritative present-state summary (established by correction C7;
updated by C8 and C9)

**This is the single authoritative summary of present repository and review status for this
document.** Every other section of this record that touches repository, correction-layer or
review status is either evidence detail, or a labelled HISTORICAL SNAPSHOT of an earlier point in
this same correction sequence (sections 16, 17, 18, 19, 20, 21), and each points back here rather
than restating or duplicating this summary. The package definition document and the implementation
handoff each carry their own CURRENT CONTROL STATE block, kept in agreement with this one.

```text
FOUR DISTINCT ENDPOINTS, all verified from the repository (C9, 5 September 2026). Before C9 this
block named only the first and the fourth, and called them "protected baseline" and "committed+
pushed candidate", which no longer described the current review base.

Historical inception baseline:
  22a4b28a2679503187a9db4cd5be580a8eac39ec
  The commit this package was branched from and ORIGINALLY reviewed against.
  It is NO LONGER the review base.

Current main / current review base:
  5d737c05478986d4bd88ee13da209d9a99b1bc43
  Merge of PR #19, which integrated ADR-035. ADR-035 is therefore present in this
  package's synchronized current-main baseline. It does NOT govern this package's
  closure - see the transitional rule immediately below.

Review lifecycle governing PF-1A-E2-B closure (corrected by C10):
  PF-1A-E2-B entered its independent-review/correction sequence BEFORE ADR-035 was
  integrated. This already-running package is therefore closed under the strict
  PRE-ADR-035 Criterion-Z process that has governed its C1-C10 sequence throughout.

  Historical sequencing note: PF-1A-E2-B entered and completed its C1-C10 review/correction
  sequence independently of the later ADR-035 experiment. ADR-035 was subsequently withdrawn
  as an active architecture decision; E2-B's recorded history is not retroactively rewritten.
  Future packages use the correction-cycle sequencing in the bounded-review methodology: fix
  material/core defects immediately, batch only safely non-normative documentation cleanup,
  then run the normal final independent review of the complete candidate.

  The valid top-level bounded-review verdict for PF-1A-E2-B remains exactly:
    ACCEPTED / CORRECTION_REQUIRED / MODEL_ESCALATION_REQUIRED
  Criterion Z is satisfied only when a fresh bounded independent review returns ACCEPTED.

  This is a PACKAGE-SPECIFIC TRANSITIONAL EXCEPTION for an in-flight package. It neither
  weakens nor alters ADR-035, and it does not affect any later applicable work.

Current LOCAL feature-branch HEAD:
  6de6fb0089069a64be2b4b9a132f9b8644a1a945
  Merge commit "Sync PF-1A-E2-B branch with current main" (merges 481a860 with 5d737c0).
  COMMITTED LOCALLY, NOT PUSHED.

Current ORIGIN feature ref:
  481a860297ca2a5e6c6b3fd2e87ed3a19581ba28
  origin/pf-1a-e2-b-persisted-published-authority-store-runtime-wiring.
  Still parented on 22a4b28, and therefore STALE relative to the local HEAD: it does not
  contain the main sync. NOT merged to main.

The sync merge changed NO E2-B candidate file. `git diff --name-only 481a860 6de6fb0` reports
only eight main-side files (AGENTS.md, PBL's internal working instructions, docs/agent/ARCHITECTURE_DECISIONS.md, the two
review-method/workflow documents, two DEV-ORCH records and NEXT_STEPS.md). The committed E2-B
candidate content is therefore identical at 481a860 and at 6de6fb0.

Candidate:
  - committed locally at 6de6fb0
  - the E2-B candidate content is pushed as origin ref 481a860, which does NOT contain the
    main sync
  - NOT merged to main

Current working-tree correction layer:
  C2/C3/C4/C5/C6/C7/C8/C9/C10
  - collectively one layer
  - UNCOMMITTED
  - UNPUSHED
  - exactly 12 MODIFIED files
  - no correction creates a thirteenth working-tree file
  - C10 itself edits only the same three documentation files already inside those 12

Inventory (each line now names BOTH of its endpoints explicitly - C9):
  current main 5d737c0 -> local HEAD 6de6fb0     19 files   committed candidate content
  local HEAD 6de6fb0 -> working tree             12 files   uncommitted correction layer
  current main 5d737c0 -> working tree           21 files   full effective candidate
                                                            = the union of the 19 and the 12,
                                                              which overlap in 10

  The counts are UNCHANGED by C9; only the endpoints they are bound to are corrected. The same
  19 paths are what `22a4b28 -> 481a860` also reports, which is exactly why 19/12/21 stayed
  arithmetically correct while their endpoint labels went stale.
  (full detail: section 17.3, and the implementation handoff section 3)

Current supplied deterministic evidence:
  E2-B focused suite          149 passed
  E2-A focused suite          356 passed
  PF-1A-E1 compatibility      117 passed
  full backend regression     887 passed, 0 failed
  Alembic current = head      20260904_0031
  tracked-secret scan         801 files scanned, no findings
  contract fixture validator  all rules passed
  repository script tests     58 tests, OK
  git diff --check            clean
  python -m compileall        OK
  (full detail: section 9.2)

  No causal explanation for the 799 -> 801 tracked-secret-scan file-count change is asserted.
  These figures are unchanged by C10, which is documentation-only and reran no deterministic
  test. No deterministic suite was rerun for C10.

Review state (chronological):
  - initial independent review of 481a860   -> CORRECTION_REQUIRED, findings F1-F4 (section 15)
  - C2                                          substantively corrected F1-F4, plus a separately
                                                 discovered test-only autocommit-pool-contamination
                                                 leak (section 15.6)
  - post-C2 independent review               -> documentation-only P2 finding -> C3 (section 16)
  - post-C3 independent review               -> residual documentation-only P2 finding -> C4
                                                 (section 17)
  - post-C4 independent review               -> stale current-summary P2 finding -> C5 (section 18)
  - post-C5 independent review               -> secret-scan provenance P2 finding -> C6 (section 19)
  - post-C6 independent review               -> stale duplicated-current-summary P2 finding -> C7
                                                 (section 20)
  - post-C7 independent review               -> residual noncanonical mutable-summary P2 finding
                                                 -> C8 (section 21)
  - post-C8 independent review               -> NO new material functional, security, persistence,
                                                 migration, parity, E2-A or E1 defect identified.
                                                 F1, F2, F3, F4 and the test-only
                                                 autocommit-pool contamination all remain CLOSED
  - D1 (project-owner decision)              -> the feature branch was synced with current main
                                                 (merge 6de6fb0, bringing PR #18 and PR #19 /
                                                 ADR-035 into the review base), and a
                                                 documentation-only correction C9 was directed,
                                                 scoped to the three package documents and
                                                 additionally authorizing the narrow C7/C8
                                                 historical labelling
  - C9                                          endpoint reconciliation; documentation only
                                                 (section 22)
  - post-C9 fresh bounded review             -> CORRECTION_REQUIRED. It independently confirmed
                                                 F1, F2, F3, F4, the test-only autocommit-pool
                                                 contamination and D1 all CLOSED, and identified
                                                 NO new material runtime, persistence,
                                                 concurrency, migration, production-composition,
                                                 security, parity, E2-A-semantic, E1-compatibility
                                                 or main-synchronization defect. Its ONLY material
                                                 finding was D2
  - D2                                       -> the canonical current-state blocks incorrectly
                                                 applied ADR-035 retroactively to this
                                                 already-running package, stating that its
                                                 two-phase lifecycle now governed E2-B closure
  - C10                                         pre-ADR-035 in-flight lifecycle reconciliation;
                                                 documentation only (section 23, this correction)
  - fresh post-C10 independent bounded review   NOT YET PERFORMED

Current status:
  PF-1A-E2-B: NOT ACCEPTED.
  Criterion Z: NOT MET (section 14).

Next gate:
  A fresh bounded independent POST-C10 review of the full effective candidate - current main
  5d737c0, plus the committed candidate content at local HEAD 6de6fb0, plus the current C2-C10
  working-tree correction layer - covering runtime, documentation and this canonical
  current-state block together.

  Its valid top-level verdict is ACCEPTED / CORRECTION_REQUIRED / MODEL_ESCALATION_REQUIRED.
  There is no intermediate FUNCTIONAL_REVIEW_COMPLETE gate for this package.
```

None of the independent reviews recorded above re-ran the deterministic test suites; the figures
above are this package's own tool output, supplied as evidence, not something a reviewer executed.

For any other section of this record, the package definition document, or the implementation
handoff that discusses present repository or review status: this block is authoritative. A
historical snapshot section may still describe what was true at an earlier correction point, but
its own supersession pointer references this block by name (CURRENT CONTROL STATE, section 0)
rather than a specific later-numbered correction, so that a future correction does not require
revisiting every historical pointer again.

---

## 1. What this package does and does not deliver

**PF-1A-E2-B DOES NOT DELIVER A PRODUCTION-CALLABLE BUSINESS-AUTHORITY RESOLVER**, and no statement
in this record, in the code or in the handoff says otherwise.

```text
DELIVERED       the unchanged PF-1A-E2-A kernel, wired to a durable, READ-ONLY PostgreSQL
                provider of published authority configuration facts; the twelve-table published
                authority store; and a defined production dependency seam.

NOT DELIVERED   an authoritative actor -> canonical person provider;
                an authoritative canonical HR / organisation provider.
                Until a later authorized package supplies BOTH, the production composition
                refuses to compose, and no consumer route or service may call business-authority
                resolution as a real authorization gate.
```

The E2-A **kernel, ports, reason codes, evidence DTOs, domain, lineage, material, scope,
evaluators, contract and defects modules are byte-for-byte unchanged**, and no E2-A semantic rule,
reason code, rank table, fail-closed behaviour or evidence shape is altered anywhere in this
package.

**One baseline file is touched, and only by correction C2: `resolver.py`.** C2 withdrew the
phase-local `build_production_resolver()` factory from it, because independent review finding F4
established that maintaining two independent production composition seams — one binding PostgreSQL
and one binding nothing — is a drift hazard for the successor package that will add the
actor-person and HR providers. The two RESOLUTION entry points in that file
(`resolve_current_authority`, `resolve_authority_as_of`), the `ProductionCompositionUnavailableError`
type and every semantic behaviour in it are unchanged. See section 15.4.

---

## 2. Physical persistence design

Twelve tables — for each of the four E2-A object families, a **stable identity** table, an
**immutable published version** table and an **append-only retraction assertion** table.

```text
authz_business_authority              / _version / _retraction
authz_business_authority_role         / _version / _retraction
authz_business_authority_rule         / _version / _retraction
authz_business_authority_assignment   / _version / _retraction
```

- **Stable identity is a separate physical row from its versions.** The stable row carries `id`
  (integer identity, ADR-007) and `object_id`, the opaque canonical externally-referenceable
  identity the E2-A port exchanges. A second `public_id` column is deliberately **not** added:
  two external identities for one object is the ambiguity ADR-007 exists to prevent.
- **Rule and Assignment reference the STABLE identity** of the Role/Authority they name, never a
  specific version — a version-level reference would break correction (E2-A invariant I-5).
- `person_id`, `position_id` and every scope identifier are **opaque canonical values** with no
  local foreign key and no join target. No employee, person, organisation-unit, position or
  incumbency table, view or cache exists (ADR-026, ADR-032, `RMR-001`).
- `parameter_payload` is `JSONB`, nullable, stored faithfully and never validated per evaluator
  type by the database.
- `active_flag` is a plain, `NOT NULL`, stored boolean **on the version row**: never computed,
  never on the stable-identity row, never derived from the interval, and never filtered by the
  store.
- There is **no** `asserted_effective_to`, `is_current`, `is_effective`, `is_retracted` or
  `is_superseded` column, no materialized view and no trigger-maintained artefact. Closure is
  DERIVED per resolution by the kernel.
- There is **no UPDATE or DELETE path** in the package at all.

**Why four retraction tables rather than one.** Section 5.6 requires a foreign key from a
retraction row to the **stable identity** of the object it retracts (fixture B2-02). One shared
polymorphic table would need either four nullable foreign keys plus a discriminator CHECK — an
extra structural constraint section 5.6 does not list, which section 5.7 warns changes a fixture's
class — or no usable foreign key at all. Four single-target foreign keys keep the constraint set
exactly the one 5.6 enumerates.

**Column type note.** Opaque canonical identifiers use `TEXT` rather than a bounded `VARCHAR(n)`.
Their production length is owned by the canonical HR/organisation reference capability, not by this
store, and an invented length limit would be an unclassified rejection shape.

---

## 3. Structural constraints — exactly section 5.6's list, no more and no less

Enumerated from `pg_constraint` and compared against the manifest by
`test_the_structural_constraint_set_is_exactly_the_one_section_5_6_lists`.

| Constraint (per family, `{f}` ∈ authority / role / rule / assignment) | Kind | 5.6 justification |
| --- | --- | --- |
| `uq_ba_{f}_object_id` | UNIQUE | stable identity uniqueness; the foreign-key target |
| `uq_ba_{f}_version_object_version` | UNIQUE | the immutable IDENTITY/VERSION key → **B1-01** |
| `ck_ba_{f}_version_interval` | CHECK | single-row interval shape, E2-A I-6 → **B1-04, B1-05** |
| `ck_ba_{f}_publication_reference_type` | CHECK | closed provenance domain → **B1-10** |
| `ck_ba_{f}_retraction_publication_reference_type` | CHECK | same, on retraction rows |
| `fk_ba_{f}_version_object_id` | FK | version → stable identity ROW → **B2-01** |
| `fk_ba_{f}_retraction_object_id` | FK | retraction → object stable identity ROW → **B2-02** |
| `fk_ba_rule_version_role_reference` | FK | rule → role STABLE identity → **B2-03** |
| `fk_ba_rule_version_authority_reference` | FK | rule → authority STABLE identity → **B2-03** |
| `fk_ba_assignment_version_role_reference` | FK | assignment → role STABLE identity → **B2-03** |
| `ck_ba_assignment_version_target_xor` | CHECK | person XOR position → **B1-02, B1-03** |
| `NOT NULL` `effective_from` / `active_flag` | column | → **B1-06, B1-07** |
| `NOT NULL` `published_at` / `retracted_at` | column | → **B1-08a, B1-08b** |
| `NOT NULL` `publication_reference_type` / `_id` | column | → **B1-09a, B1-09b** |

Indexes (enumerated and compared by `test_the_index_set_supports_discovery_lineage_and_dereference`):
`ix_ba_authority_version_authority_code`, `ix_ba_rule_version_authority_reference`,
`ix_ba_assignment_version_role_reference`, `ix_ba_{f}_retraction_object_id`, plus the indexes
backing every primary key and unique constraint. Per-object **lineage retrieval** and version
**dereference** are served by `uq_ba_{f}_version_object_version`, whose leading column is
`object_id`.

---

## 4. Semantic conditions DELIBERATELY NOT enforced structurally

Every one of these is a state the kernel must be given the chance to classify. Enforcing any of
them would suppress a defect class the kernel owns while wearing the costume of the same safeguard.

```text
NOT enforced, and asserted absent by test                       the fixture it protects
------------------------------------------------------------   ----------------------
uniqueness / exclusion constraint on (object_id, effective_from) A-02 duplicate temporal start
any overlap-rejecting constraint or trigger                      A-01 contradictory explicit overlap
any contiguity / no-gap constraint                               V-03 the VALID temporal gap
uniqueness of retraction per (object_id, object_version)         A-05 duplicated retraction
a foreign key from a retraction to a specific VERSION row        A-04 dangling retraction
any FK or CHECK on corrects_object_version                       A-06, A-07 correction targets
a closed enum / lookup FK on parameter_evaluator_type            A-13 unknown evaluator
a per-evaluator payload schema check                             A-14 malformed payload
a closed enum / lookup FK on scope_type                          A-15 unsupported scope semantics
any CROSS-ROW recorded-timestamp ordering constraint             A-08, A-09, A-10 provenance
extending the stable-identity FK to reject an identity row that  A-11 dangling reference
  EXISTS but carries no versions
```

A test asserts there is **no** exclusion constraint, **no** trigger and **no** index definition
mentioning `effective_from` anywhere on the twelve tables.

---

## 5. Provider strategy — facts, never judgements

```text
DISCOVERY (raw, identity-only, deliberately a superset)
    SELECT d.object_id, COUNT(*) OVER () AS total_rows
    FROM (SELECT DISTINCT v.object_id FROM <version table> v WHERE v.<locating column> = :value) d
    ORDER BY d.object_id

    The locating column is one of exactly three, all owned by this package:
    authority_code, business_authority_object_id, business_authority_role_object_id.

    ABSENT, and asserted absent by reading the query source as CODE (docstrings stripped):
    NOT EXISTS over any retraction table, ACTIVE_FLAG, EFFECTIVE_FROM, DECLARED_EFFECTIVE_TO,
    PUBLISHED_AT, SCOPE_*, PARAMETER_*, LIMIT, DISTINCT ON.

LINEAGE (complete)
    every version row and every retraction assertion for the object, under an explicit total
    ORDER BY. No closure, effectiveness, ranking, deduplication, tie-break or "latest".

DEREFERENCE
    the exact immutable stored version, regardless of retraction, correction, supersession,
    inactivity or expiry. Never a substitution.
```

**Completeness or nothing.** Every list query carries `COUNT(*) OVER ()`, and the row count is
compared against it, so a short read raises `TruncatedReadError` (a subclass of
`AuthorityConfigurationPortError`) rather than being presented as COMPLETE. A read error, a
timeout and a truncated read all surface as a port error, which the kernel maps to
`AUTHORITY_CONFIGURATION_UNAVAILABLE` — never an empty result and never DENY + RESOLVED.

**No one-row shortcuts.** `.first()`, `LIMIT 1`, `.scalar()`, `.scalar_one()` and `DISTINCT ON`
appear nowhere in the repository's executable source. `load_version` returns a single row only
because the unique `(object_id, object_version)` key makes at most one possible, and RAISES rather
than collapsing if that ever ceased to hold.

**Injection.** Table and column names reach the SQL text only from a closed registry keyed by the
provider-neutral object family; an unknown family raises. Every caller-supplied value is bound.

### Proof of complete-lineage and raw-discovery fidelity

| Property | Test |
| --- | --- |
| every version returned (retracted, inactive, future-dated, superseded) plus every retraction | `test_get_lineage_returns_every_version_and_every_retraction_assertion` |
| no closure/effectiveness/ranking/deduplication; explicit end NOT truncated to the successor's start | `test_the_provider_computes_no_closure_effectiveness_ranking_or_deduplication` |
| one seeded case per EXCLUDED discovery predicate (retracted, inactive, not-yet-effective, already-ended, superseded, invalid provenance) | `test_discovery_applies_no_semantic_predicate_of_any_kind` |
| retraction is never a discovery filter, for authority_code AND for both stable references | `test_retraction_is_never_a_discovery_filter` |
| no `NOT EXISTS` over a retraction table in any discovery query — read as CODE | `test_no_discovery_query_contains_a_retraction_anti_join_or_a_semantic_predicate` |
| `published_at` / `retracted_at` are never a filter; no recorded-time cutoff on any operation | `test_recorded_timestamps_are_never_used_as_a_discovery_or_lineage_filter`, `test_no_port_operation_exposes_a_recorded_time_cutoff` |
| an identity carrying no material returns COMPLETE with an EMPTY `versions[]` | `test_an_identity_with_no_material_returns_complete_with_an_empty_version_list` |
| deterministic total order; unchanged when rows are inserted in the opposite physical order | `test_lineage_is_returned_under_an_explicit_total_order` |
| immutable dereference of a retracted and of a superseded version | `test_dereference_returns_the_exact_version_even_when_retracted_or_superseded` |
| a REAL read error, a REAL lock timeout and a truncated read all fail closed | `test_a_read_error_...`, `test_a_real_lock_timeout_raises_a_port_error`, `test_a_truncated_read_is_never_reported_as_complete` |

---

## 6. Production composition behaviour

**Option (a) of section 5.3 was chosen: REFUSE TO COMPOSE**, because an unusable object cannot be
misused, and because PF-1A-E2-A had already made the same choice — binding the new provider into
that existing seam keeps one behaviour rather than two.

`build_production_business_authority_resolver(db)` binds the PostgreSQL authority configuration
provider — proving the binding point exists and is wired — and then raises
`ProductionCompositionUnavailableError` naming both absent authoritative providers. It never
returns a resolver.

`build_authority_configuration_provider(db)` returns the READ-ONLY provider on its own. Holding it
confers no authority and authorizes nothing.

```text
proved by test
--------------
NS-PR-02  the seam refuses to compose, names what is missing, and takes only `db`
NS-PR-02  no os.environ / getenv / get_settings / feature flag anywhere in the seam
NS-PR-01  no production module imports tests.fixtures or any synthetic provider class
NS-PR-01  the synthetic providers live only under backend/tests/
NS-AP-04  no client-supplied identity hint influences the WIRED resolution;
          AuthenticatedActor carries only actor_user_public_id and BusinessContext has no person_id
NS-RS-03  resolve_current_authority exposes no as_of, no recorded-time bound and no **kwargs
```

*Reconciled 9 October 2026:* from `481a860`, which added the test, until that date, the first
NS-PR-01 line above was proved for at most four modules - `app.api.router`, `app.main`,
`app.models_metadata` and `app.startup`, the only ones its `pkgutil.walk_packages` listed at any
commit up to then (measured; whether each imported and was read at every commit was not checked).
The walk did not enter `app/modules`, which has never had an `__init__.py`, so no business module
was read. The test now reads every file under `backend/app` and asserts that it did; see
`docs/continuity/NS_PR_01_GUARD_READS_EVERY_PRODUCTION_MODULE.md`.

---

## 7. Verification-class manifest, as implemented

### 7.1 Class A — 14 fixtures, storable, parity-owed. **PASS**

`A-01, A-02, A-04, A-05, A-06, A-07, A-08, A-09, A-10, A-11, A-13, A-14, A-15, A-17`

Each is stored in PostgreSQL, read back byte-identical, resolved through the wired kernel with the
reason code section 5.7 states for it, and byte-identical to the reference-backed resolution.
**A-17 is the highest-value regression test in the package**: a dangling, duplicated or
impossibly-provenanced retraction targeting the ONLY code-bearing version — and the companion case
over the only reference-bearing version of an Assignment — fails closed on that defect's own reason
code, never `AUTHORITY_CODE_NOT_CONFIGURED`, never `NO_CANDIDATE_ASSIGNMENT` and never an empty
candidate set.

### 7.2 Class B1 — 12 fixtures, structurally rejected. **PASS**

Each asserts the INSERT FAILS against the **migrated schema exactly as shipped**. No constraint was
disabled, deferred, dropped or ALTERed in any fixture. Each is EXCLUDED from the parity corpus,
because no conforming implementation of this schema can return a row the schema forbids storing —
a verification-PLACEMENT decision, never a semantic exemption.

| ID | Shape | Rejecting constraint | Covering E2-A test (fixture name) | E2-A boundary |
| --- | --- | --- | --- | --- |
| B1-01 | duplicate `(object_id, object_version)` | `uq_ba_authority_version_object_version` | DUPLICATE-OBJECT-VERSION | PURE KERNEL |
| B1-02 | assignment with BOTH targets | `ck_ba_assignment_version_target_xor` | ASSIGNMENT-TARGET-BOTH | PURE KERNEL (S7) |
| B1-03 | assignment with NEITHER target | `ck_ba_assignment_version_target_xor` | ASSIGNMENT-TARGET-NEITHER | PURE KERNEL (S7) |
| B1-04 | `declared_effective_to < effective_from` | `ck_ba_authority_version_interval` | INTERVAL-END-BEFORE-START | PURE KERNEL |
| B1-05 | `declared_effective_to == effective_from` | `ck_ba_authority_version_interval` | INTERVAL-END-EQUALS-START | PURE KERNEL |
| B1-06 | NULL `effective_from` | `NOT NULL effective_from` | VERSION-ABSENT-EFFECTIVE-FROM | DTO / PORT WELL-FORMEDNESS |
| B1-07 | NULL `active_flag` | `NOT NULL active_flag` | VERSION-ABSENT-ACTIVE-FLAG | DTO / PORT WELL-FORMEDNESS |
| B1-08a | NULL `published_at` on a version | `NOT NULL published_at` | PROVENANCE-ABSENT-PUBLISHED-AT | PURE KERNEL |
| B1-08b | NULL `retracted_at` on a retraction | `NOT NULL retracted_at` | PROVENANCE-ABSENT-RETRACTED-AT | PURE KERNEL |
| B1-09a | **ABSENT** `publication_reference_type` | `NOT NULL publication_reference_type` | **PROVENANCE-ABSENT-TYPE** | PURE KERNEL |
| B1-09b | absent `publication_reference_id` | `NOT NULL publication_reference_id` | PROVENANCE-ABSENT-REFERENCE-ID | PURE KERNEL |
| B1-10 | `publication_reference_type` outside the two values | `ck_ba_authority_publication_reference_type` | PROVENANCE-UNKNOWN-TYPE | PURE KERNEL |

B1-09a and B1-10 are two distinct shapes with two distinct E2-A fixtures: **absence is not
unknown-value**, and a schema or kernel that only checks membership in the two defined values
passes B1-10 and fails B1-09a. The one-to-one ID↔fixture mapping and the boundary fidelity are
asserted mechanically by the E2-A coverage module, which continues to pass unmodified.

### 7.3 Class B2 — 3 fixtures, structurally rejected, NO E2-A counterpart. **PASS**

| ID | Shape | Rejecting foreign key |
| --- | --- | --- |
| B2-01 | version row whose stable-identity PARENT ROW does not exist | `fk_ba_authority_version_object_id` |
| B2-02 | retraction row whose object stable-identity PARENT ROW does not exist | `fk_ba_authority_retraction_object_id` |
| B2-03 | rule/assignment referencing a role/authority stable identity ROW that does not exist | `fk_ba_rule_version_role_reference` |

**Written rationale (mandatory, and not paraphrased away).** All three constraints exist ONLY
because this store represents stable object identity as a SEPARATE PHYSICAL ROW from its versions.
That split is a persistence representation choice the provider-neutral contract does not share:

- E2-A 9.3.2 carries `object_id` on the **LineageMaterial CONTAINER**, with `versions[]` and
  `retraction_assertions[]` grouped UNDER it. A version or a retraction therefore **cannot** be
  provider-neutrally orphaned from its object — the contract has no field in which that state could
  be expressed at all. B2-01 and B2-02 have no counterpart, full stop.
- `get_lineage` for an identity the provider holds nothing for returns COMPLETE material with an
  EMPTY `versions[]`. A reference to a stable identity ROW that does not exist therefore **decodes,
  at the provider-neutral boundary, to exactly the class A state of fixture A-11**
  (`AUTHORITY_REFERENCE_DANGLING`), which is already owed full parity and already carries a direct
  E2-A test. B2-03's counterpart does not go untested; it COLLAPSES ONTO an existing class A
  fixture, so there is no DISTINCT malformed state left to place.

Applying E2-A 9.7's deciding test to each — *could any conforming provider, using only the
9.3.2/9.3.4 fields and without inventing a persistence-specific field, present a state the kernel
would classify DIFFERENTLY from an already-classified state?* — the answer for all three is **NO**.
Hence B2, not B1. What these foreign keys protect is this store's own parent/child referential
integrity: a real and worthwhile invariant, worth a rejection test, but not a semantic rule of E2-A.

**No E2-A fixture was fabricated for any of them**, and the E2-A coverage module continues to assert
that absence deliberately. `test_the_class_assignment_this_store_relies_on_is_unchanged` re-checks
the two E2-A DTO properties the rationale rests on, so a future change to 9.3.2 / 9.3.4 that made a
B2 state expressible would fail here and force reclassification to B1.

**The distinction the whole classification depends on is pinned by its own test**
(`test_the_stable_identity_foreign_key_is_not_extended_into_class_a_territory`): a rule referencing
a stable identity row that **EXISTS but carries no versions** is ACCEPTED by the schema. Extending
the foreign key to reject that would silently swallow class A fixture A-11.

### 7.4 Valid-shape parity scenarios — V-01 to V-12. **PASS**

No class label; not negative fixtures; fully parity-owed. Any test describing one as "class A"
would be the F-10.3a defect and none does.

### 7.5 Non-store scenarios — 46. **PASS**

38 parity-YES drive the identical condition through both compositions. The 8 parity-NO carry the
E2-B half section 5.7A states: `NS-AP-04` and `NS-RS-03` as trust/surface assertions on the WIRED
path, `NS-PR-01`/`NS-PR-02` as reachability and composition assertions, `NS-PR-03` as the
provider-fidelity conformance suite, and `NS-DO-06`/`NS-K-01`/`NS-K-02` as cross-reference checks
that the named E2-A tests exist and are neither skipped nor xfailed.

**Where the corpus departs from the E2-A test bodies, and why.** Several E2-A multi-defect
scenarios are driven by class B1 shapes — an absent `published_at`, an `end <= start` interval —
which this schema rejects at write time. `NS-DO-01`, `NS-DO-02` and `NS-DO-05` are therefore rebuilt
from **class A** shapes carrying the same reason codes (a DECREASING `published_at` for
`PUBLICATION_PROVENANCE_INVALID`, a duplicate temporal start or a non-existent correction target for
`AUTHORITY_LINEAGE_CONTRADICTORY`), exactly as section 5.7A requires. No constraint was circumvented
to seed anything.

### 7.6 Justified fail-closed reason-code exclusion list — CLOSED

`test_the_implemented_exclusion_list_is_exactly_the_closed_manifest_list` derives the excluded set
from the binding manifest and asserts it equals exactly these three:

| Reason code | Justification |
| --- | --- |
| `ASSIGNMENT_TARGET_INVALID` | **class B1**: the person/position XOR CHECK (`ck_ba_assignment_version_target_xor`) makes B1-02 and B1-03 unstorable here; E2-A fixtures ASSIGNMENT-TARGET-BOTH / ASSIGNMENT-TARGET-NEITHER prove the semantics at the PURE KERNEL boundary, stage S7. |
| `AUTHORITY_VERSION_AMBIGUOUS` | **kernel-internal**: proved unreachable from any provider input by the E2-A 11.4a single-effective-version theorem, so no store can present the state; covered by NS-K-01. |
| `INTERNAL_CONTRACT_VIOLATION` | **kernel-internal** self-check: by definition not a provider-supplied state; covered by NS-K-02. |

Every other fail-closed code of E2-A 14.3 is parity-covered.
`test_the_codes_a_reviewer_should_probe_specifically_are_still_parity_covered` pins the four that
moved during the F-10 closures — `AUTHORITY_CODE_NOT_CONFIGURED` (via NS-RS-01),
`AUTHORITY_CONFIGURATION_UNAVAILABLE` (via NS-PT-01), `SCOPE_CONTEXT_MISSING` (via NS-RQ-01) and
`EVALUATOR_FACTS_INVALID` (via NS-RQ-02).

---

## 8. Central parity corpus — 64 scenarios. **PASS**

```text
14  class A fixtures            varies the MALFORMED stored state
12  valid-shape scenarios       varies the VALID stored state (no class label)
38  parity-YES non-store        varies a provider, request, clock, orchestration or evidence
--  ---------------------------------------------------------------------------------------
64  and no class B1, no class B2, and none of the 8 parity-NO scenarios
```

For every scenario the comparison is `serialize_result(...)` — the canonical byte-stable form of
the entire result, covering outcome, `resolution_status`, `result_level_reason`, the
`established_state` header, the evaluated business context, and all three evidence collections with
their ordering and every field. The comparison was not weakened anywhere to obtain parity.

`test_the_parity_marked_tests_cover_exactly_the_sixty_four_scenarios` asserts the parity-marked set
equals the corpus exactly — neither a subset nor a superset.

**Determinism under persistence (criterion N2).** Proved byte-identical under: rows inserted in the
opposite physical order; the reference provider's return order reversed and shuffled across four
seeds; `VACUUM (FULL, ANALYZE)` rewriting the heap so physical order genuinely differs; repeated
runs over the same stored rows; two concurrent resolutions on separate sessions; and a
mutation-style run with the provider's `ORDER BY` deliberately removed, proving the kernel's
canonical re-sort — not the database — is what decides.

---

## 9. Test results

All commands run inside the isolated PF-1A-E2-B Compose project `pbl-crm-e2b` (host ports
65432/18000, its own named volume), which left the PF-1A-E1 (5432/8000/3000) and PF-1A-E2-A
(55432/58000) environments running and unmodified.

**These are the ORIGINAL implementation-time results (4-5 September 2026, after reconciliation
C1, BEFORE the independent review and BEFORE correction C2).** They remain an accurate record of
that earlier state and are retained for that reason, but they are superseded, for the C2-corrected
candidate, by the current post-C2 figures in section 9.2 below. Do not read the counts in this
block as the current result.

```text
FOCUSED E2-B SUITE
docker compose ... exec -T backend pytest \
  tests/test_business_authority_store_schema.py \
  tests/test_business_authority_store_provider.py \
  tests/test_business_authority_store_parity.py \
  tests/test_business_authority_store_non_store_parity.py \
  tests/test_business_authority_store_wiring.py \
  tests/test_business_authority_store_coverage.py -q
                                                     144 passed

  schema / storage integrity ......................... 34 passed
  provider fidelity .................................. 19 passed
  class A + valid-shape parity ....................... 26 passed
  non-store parity, determinism, evidence durability .. 40 passed
  runtime wiring, security, E1 boundary ............... 15 passed
  verification-class coverage ......................... 10 passed

MANIFEST COVERAGE (asserted mechanically)
  manifest IDs with an executing E2-B test ............ 87 of 87
  parity-marked IDs ................................... 64 of 64
  E2-B tests carrying a coverage marker ............... 120

EXISTING PF-1A-E2-A SUITE (16 modules)
  before reconciliation C1                           354 passed, 2 failed
  after  reconciliation C1                           356 passed
  Fifteen of the sixteen modules are UNMODIFIED. The sixteenth,
  test_business_authority_security_boundary.py, carries the two assertions
  reconciled under C1 (section 12) and nothing else.

EXISTING PF-1A-E1 SUITE (4 modules, unmodified)
                                                     117 passed

FULL BACKEND REGRESSION
docker compose ... exec -T backend pytest -q
  before reconciliation C1                           880 passed, 2 failed  (5m 05s)
  after  reconciliation C1                           882 passed, 0 failed  (5m 44s)
  The pre-E2-B total was 738 at PF-1A-E1 closure and rose with E2-A; E2-B adds
  144, and the total legitimately rises rather than being held to a frozen figure.
  The +2 is exactly the two reconciled assertions turning green; no test was
  added, removed, skipped or xfailed by C1.

ALEMBIC
  alembic heads    -> 20260904_0031 (head)          exactly one head
  alembic current  -> 20260904_0031 (head)          current == heads
  empty database -> upgrade head                    clean, all 31 revisions
  all 12 store tables after upgrade                 0 rows (no seed)
  authz_permission / authz_role_permission / role   31 / 110 / 6 (E1 intact)
  downgrade -1 then upgrade head                    12 tables dropped, then recreated

REPOSITORY VALIDATORS
  python scripts/check_tracked_secrets.py           no findings (799 files)
  python scripts/validate_contract_fixtures.py      all rules passed
  python -m unittest discover -s scripts/tests      58 tests, OK
  git diff --check                                  clean
  python -m compileall (new + changed sources)      OK

STATIC / LINT / TYPE
  The repository configures no backend linter or type checker (no ruff, mypy,
  flake8 or black in backend/requirements.txt or in the TE-2CI workflow), so
  there is no such gate to run. Byte-compilation and the two repository
  validators above are the static checks the workflow actually defines.
```

### 9.1 One defect found and fixed during self-verification

`test_a_real_lock_timeout_raises_a_port_error` passed in isolation but failed once
(`DID NOT RAISE`) inside the full 880-test run. The assertion could pass vacuously if the blocking
`ACCESS EXCLUSIVE` lock was not actually held at the moment of the read, which is exactly what
appears to have happened under full-suite timing. Fixed by making the test self-checking rather
than timing-dependent: this session's transaction is ended before the blocker starts, the blocker's
own failure is reported to the main thread, `SET` replaces `SET LOCAL` so the timeout cannot be
discarded at a transaction boundary, and **the lock is verified from `pg_locks` before the read**,
so an unheld lock now fails loudly instead of producing a vacuous pass. Re-run three times in
isolation and once in the full suite: stable.

**SUPERSEDED BY CORRECTION C2/F2 — this fix is the earlier, now-superseded approach.** The
`SET` (session-level `lock_timeout` on the shared `store_db` session, replacing `SET LOCAL`)
described immediately above is the ORIGINAL self-verification fix made at implementation time,
BEFORE the independent review. It is exactly the pattern the review's finding F2 later identified
as a connection-pool contamination hazard: a Session releases its physical connection at
transaction end, so a later cleanup statement acting on that session can land on a different
pooled checkout, leaving a contaminated connection behind for an unrelated later test. Correction
C2 REPLACED it: the test now checks out its OWN dedicated connection and uses `SET LOCAL` inside
the reading transaction, which PostgreSQL itself reverts at ROLLBACK on that SAME physical
connection — with no `RESET` statement and no session-level `SET` anywhere in the module — and the
correction proves a sweep of subsequently drawn pooled connections comes back clean. **Do not read
the `SET`/session-level description above as the current fix; see section 15.3 for the current,
accepted C2/F2 correction.** This subsection is retained only as the historical record of the
earlier approach.

### 9.2 Deterministic evidence detail (established at C2; consolidated into CURRENT CONTROL STATE, section 0)

```text
FOCUSED E2-B SUITE (6 modules, post-C2)               149 passed   (144 -> +5 regression tests
                                                       added by C2: F1's interleaving proof, F2's
                                                       structural SET-LOCAL-only guard, F3's
                                                       genuine-concurrency proof, F4's
                                                       exactly-one-seam proof, and the guard
                                                       against a pooled connection returning in
                                                       autocommit)
EXISTING PF-1A-E2-A SUITE (16 modules)                356 passed   (unchanged since C1)
EXISTING PF-1A-E1 SUITE (4 modules, unmodified)        117 passed
FULL BACKEND REGRESSION                                887 passed, 0 failed   (882 -> +5, the
                                                       same five C2 regression tests; no test
                                                       removed, skipped or xfailed)
ALEMBIC
  alembic heads    -> 20260904_0031 (head)             exactly one head, unchanged
  alembic current  -> 20260904_0031 (head)             current == heads, unchanged
REPOSITORY VALIDATORS
  python scripts/check_tracked_secrets.py              801 files scanned, no findings
  python scripts/validate_contract_fixtures.py         all rules passed
  python -m unittest discover -s scripts/tests         58 tests, OK
  git diff --check                                     clean
  python -m compileall (new + changed sources)         OK
```

These figures were established at C2 and remain unchanged through C3/C4/C5/C6/C7, since none of
those corrections touched production code, tests, or the migration; they are consolidated in the
CURRENT CONTROL STATE (section 0), which is authoritative if this detail and that block ever
appear to diverge. The figures in section 9 above (144 focused / 882 full backend / 799 secret-scan
files) are the accurate historical record of the ORIGINAL implementation, before the independent
review and before C2; they remain correct as a description of that earlier state and are not
erased, but they must not be read as the current result.

---

## 10. PF-1A-E1 compatibility boundary — intact

```text
31 application permissions          asserted from the contract AND from the live database
6 transitional Application/Login Roles
110 role-permission grants          asserted from the contract AND from the live database
ACCOUNT_TAX_VERIFY                  FINANCE_USER-only, unchanged
no implicit ADMIN bypass            no E1 role constant appears in the business-authority CODE
no schema link                      no foreign key in either direction between the store and
                                    role / app_user / user_role / authz_permission /
                                    authz_role_permission
no Business Authority code in the E1 contract; no `require_roles(...)` reintroduced anywhere
all 117 existing E1 tests pass UNMODIFIED
```

`backend/app/models_metadata.py` was the only pre-existing PRODUCTION file candidate `481a860`
itself modified (a single import group of twelve model classes — no other line changed). Under
controller-authorized reconciliation C1 (section 12), that same candidate also modified the
pre-existing TEST file `backend/tests/test_business_authority_security_boundary.py`. Correction
pass C2 (section 15) subsequently modified two further pre-existing files that predate this
package entirely: `backend/app/modules/authorization/business_authority/resolver.py`, solely to
withdraw finding F4's duplicate production-composition seam, and the E2-A test fixture
`backend/tests/fixtures/pf_1a_e2_a_reference_providers.py` (a stale-docstring reconciliation
related to the same finding); C2 also further re-pointed the same two
`test_business_authority_security_boundary.py` assertions C1 had already revised. **No other
pre-existing production file is modified anywhere in this package, across the original candidate
or any correction layer.** No E1 file, and no E2-A kernel/domain/port/contract/evidence/
lineage/material/scope/evaluator module, is modified.

---

## 11. HR / organisation ownership boundary — intact

No employee, person, organisation-unit, position or incumbency table, view or cache exists. No
column named for a provider identifier, provider field, SharePoint item id, Plum field, employee
name, raw provider timestamp or Source Binding reference exists on any store table. `person_id`,
`position_id` and scope identifiers are opaque canonical values with no foreign key and no join
target. No decision or evidence is persisted by this package.

---

## 12. Controller-authorized reconciliation C1 — the E2-A → E2-B phase boundary

**Status: CLOSED, 5 September 2026, by controller-authorized reconciliation C1.** Raised as a
material blocker on 4 September 2026; determined by the controller to be a stale PHASE-LOCAL
structural assertion problem at the E2-A → E2-B boundary, **not** an E2-B semantic implementation
defect. C1 is a narrowly scoped authorization and is **not** authorization for general test
modification.

### 12.1 What the contradiction was

Two tests in `backend/tests/test_business_authority_security_boundary.py` failed, and no conforming
implementation of PF-1A-E2-B could make them pass:

```text
test_the_package_adds_no_model_no_migration_and_no_route
    assert "models.py" not in package_files          <- E2-B adds models.py      (criterion A)
    assert "repository.py" not in package_files      <- E2-B adds repository.py  (criterion D)
    assert "business_authority" not in metadata_source
                                                     <- E2-B registers its models (criterion H)

test_nothing_in_the_repository_wires_a_production_business_authority_resolver
    for every production source outside the business_authority package:
        assert "business_authority" not in source
                                                     <- app/models_metadata.py must import the
                                                        models for SQLAlchemy/Alembic discovery
```

**This was an implementation-time TEST-CONTRACT contradiction.** PF-1A-E2-B mandates all four
artifacts (acceptance criteria A, D, H, I) and names those exact files as allowed areas in section
11, while criterion V simultaneously required every existing PF-1A-E2-A test to pass unmodified.
Both could not hold.

**PF-1A-E2-A's own authoritative scope text already assigned the now-permitted persistence
artifacts to PF-1A-E2-B.** Section 17, *Explicit exclusions (PF-1A-E2-A)*, annotates each with the
package that delivers it:

```text
- SQLAlchemy persistence for any new authority object                (PF-1A-E2-B)
- any Alembic migration                                              (PF-1A-E2-B)
- a database-backed authority repository or provider                 (PF-1A-E2-B)
- registration in backend/app/models_metadata.py                     (PF-1A-E2-B)
```

The two assertions were therefore statements about **E2-A's own delivered scope**, correct when
written and expiring by design the moment the successor package E2-A itself names does the work.

### 12.2 What C1 changed — exactly two assertions, in one file

**Only the two stale phase-local structural assertions were revised.** No other test was touched.

**Reconciliation 1 — the persistence phase assertion.**

| | |
| --- | --- |
| Before | `test_the_package_adds_no_model_no_migration_and_no_route` asserted that the Business Authority production package contains no `models.py`, no `repository.py`, no `routes.py` and no `schemas.py`, **and** that `app/models_metadata.py` does not mention `business_authority`. |
| After | Renamed `test_the_package_adds_no_route_and_no_api_schema_surface`. It asserts that the package contains no `routes.py` and no `schemas.py`. The `models.py`, `repository.py` and `models_metadata.py` prohibitions are removed. |
| Why the survivor matters | The HTTP-route and API-schema exclusion belongs to a **later consumer package**, not to E2-B, so it is still in force in every phase and is still asserted. |
| Not weakened | The separate tests prohibiting a production configuration **write** path (`test_no_module_in_the_package_defines_a_configuration_write_path`, `test_the_authority_configuration_port_defines_no_write_operation`) are untouched and remain the stronger guarantee. |

**Reconciliation 2 — the production resolver wiring assertion.**

| | |
| --- | --- |
| Before | `test_nothing_in_the_repository_wires_a_production_business_authority_resolver` scanned every production source outside the Business Authority package and asserted none contains the string `business_authority`. |
| After | The **same repository-wide structural scan is retained**, with **exactly one file exempted**: `app/models_metadata.py`, matched by path identity rather than by name, prefix, directory or pattern. That file is additionally asserted, on its docstring-stripped code, to reach **none** of `resolve_current_authority`, `resolve_authority_as_of`, `build_production_resolver`, `build_production_business_authority_resolver`, `build_authority_configuration_provider`, `AuthorityConfigurationPort`, `kernel` or `resolver`. |
| Why not narrowed to a function-name check | Consumer wiring can be introduced by importing the kernel, the resolver, a provider or the composition seam under any name. The broad scan is what makes accidental wiring visible, so it was retained rather than replaced by a weaker substring test for one resolver function. |
| Why the exemption is sound | An ORM/metadata import is model **discovery**, not consumer wiring: it binds no resolver, calls no resolution entry point, reaches no actor-person or HR provider, and cannot produce an authorization decision. E2-A section 17 assigns that registration to E2-B by name. |

The Business Authority package itself remains excluded from that outside-package scan exactly as
before, and no other module is exempted.

**Non-vacuity, measured rather than assumed:** the scan covers **130** production files outside the
package; **exactly one** of them (`models_metadata.py`) references `business_authority`; and that
file's code does still contain the string, so the exemption branch is genuinely exercised and the
inner consumer-symbol assertions are not passing over an empty input.

### 12.3 What C1 did NOT change

```text
1. No E2-A semantic rule changed.
2. No fail-closed behaviour changed - no reason code, rank, stage, evidence obligation or
   result-selection rule was touched.
3. No ADMIN protection changed. An Application/Login Role alone still grants no business
   authority, and no implicit ADMIN bypass exists.
4. No PF-1A-E1 permission, grant, route or compatibility-matrix protection changed.
   31 permissions / 6 roles / 110 grants, all E1 tests unmodified and green.
5. No synthetic/reference provider production-reachability protection changed. The synthetic
   providers remain under backend/tests/ and unreachable from every production import path.
6. Production Business Authority resolution REMAINS UNAVAILABLE until authoritative
   actor-person and HR providers exist; the production composition still refuses to compose.
7. No E2-A runtime source file changed. No E2-B production implementation changed.
8. No E1 source or test changed.
9. No route, schema, OpenAPI surface, business event, migration or frontend change was
   introduced by C1.
```

### 12.4 How criterion V is now read

**Acceptance criterion V is henceforth interpreted as: all PF-1A-E2-A semantic and security
behaviour remains green, with these two phase-transition assertions EXPLICITLY RECONCILED rather
than pretending they remained literally unmodified.**

The original E2-A form of both assertions is preserved verbatim in section 12.1 above, and the
reconciled tests carry docstrings recording what they used to assert and why that changed.
**Historical PF-1A-E2-A acceptance evidence is not rewritten**:
`docs/agent/acceptance/pf-1a-e2-a-business-authority-resolution-contract-and-domain-kernel-acceptance.md`
is untouched by C1, and nothing anywhere claims these tests always had their new form.

## 13. Deferred and minor items

```text
1. Decimal is not a supported PUBLISHED payload representation.
   `parameter_payload` is JSON, so a Python `Decimal` inside a stored payload is not
   JSON-representable and the seeding helper raises rather than silently coercing it. E2-A's
   evaluator accepts a Decimal from the REQUEST context, which this package never persists, so no
   evaluator behaviour is affected. The parity corpus uses JSON-native numbers in stored payloads
   and the round-trip test proves nested structures, high-magnitude integers, fractional values and
   Unicode survive exactly. Recorded as a limitation rather than fixed: registering a
   Decimal-producing JSONB loader would break round-trip fidelity for genuine floats.

2. The downgrade is DESTRUCTIVE of published authority configuration by construction, because the
   tables it drops are the only record of it. It is intended for development and for this
   unreleased chain only. Nothing is lost today (the store holds no seeded data and no production
   configuration exists), but once PF-1A-E3 can publish real configuration a downgrade must be
   treated as a data-destroying operation and gated accordingly. Recorded per section 5.4.

3. The `pg_locks`-verified lock-timeout test takes ~250 ms of real waiting. This is deliberate:
   it is a REAL, database-produced timeout rather than an injected exception.
```

---

## 14. Acceptance criteria status

| | Criterion | Status |
| --- | --- | --- |
| A | stable identity separated from immutable published version identity | MET |
| B | append-only lineage/retraction/provenance; no version UPDATE; closure derived | MET |
| C | `active_flag` immutable, NOT NULL, stored, no UPDATE path, never filtered | MET |
| D | raw identity-only discovery + complete lineage; no excluded predicate; failures never empty | MET |
| E | defect visibility for all 14 class A fixtures, including A-17 | MET |
| F | schema permits gaps, contradictions, dangling/duplicated retractions, bad provenance; nothing normalised | MET |
| G | E2-A business-authority SEMANTICS reused UNCHANGED — no kernel/domain/ports/contract/evidence/lineage/material/scope/evaluator/defect meaning redesigned; the only E2-A production-source modification is `resolver.py`, narrowly for correction C2/F4's withdrawal of the duplicate production-composition seam; E2-A test/fixture modifications are narrow, documented, controller-authorized phase-boundary reconciliations (C1, then C2/F4); E1 compatibility untouched | MET |
| H | models registered in `models_metadata.py` | MET |
| I | exactly one migration, parented on the verified head, altering nothing, seeding nothing | MET |
| J | person XOR position enforced structurally; B1-02/B1-03 proved by E2-A at S7 | MET |
| K | referential/version/provenance integrity per 5.6, with the B2 rationale recorded | MET |
| L | deterministic, totally ordered, parameterized queries; no arbitrary first-row selection | MET |
| M | evaluator payloads persist as structured data; E2-A validation authoritative | MET |
| N | full parity across the 64-scenario corpus | MET |
| N2 | determinism survives persistence | MET |
| N3 | three-class assignment total and exclusive; 14/12/3 asserted | MET |
| N4 | taxonomy correctly scoped; 29/12/46 and the disjoint partition asserted | MET |
| O | evidence dereferenceable and byte-identical after later versions/retraction/correction | MET |
| P | production seam binds only the config provider and refuses to compose | MET |
| Q | no record claims a production-callable resolver | MET |
| R | no production mutation surface anywhere | MET |
| S | no authority configuration, assignment or bootstrap holder seeded; Q-10 untouched | MET |
| T | no HTTP route, schema, business event or frontend change | MET |
| U | no CRM/Hiring-owned HR or organisation master; no provider-specific HR detail | MET |
| V | every E1 protection intact; every E2-A semantic/security behaviour green | MET, with the two phase-transition assertions explicitly reconciled under C1 — see section 12.4 |
| W | empty-database migration passes; `current` == `heads`; exactly one head | MET |
| X | full backend regression; tracked-secret scan; `git diff --check` clean | MET — 882 passed / 0 failed at candidate `481a860`; **887 passed / 0 failed after correction C2** (the +5 is the five regression tests C2 added; no test was removed, skipped or xfailed). Tracked-secret scan and `git diff --check` clean. |
| Y | Docker clean start (infrastructure/schema changed) | MET — the isolated `pbl-crm-e2b` project was built and started from an empty volume, and migrated from base to head |
| Z | fresh independent bounded review returns ACCEPTED with no blocking findings | **NOT MET.** Initial bounded independent review of candidate `481a860` -> `CORRECTION_REQUIRED`, findings F1-F4 (section 15). **C2** substantively corrected F1-F4 plus a separately discovered test-only autocommit-pool-contamination leak (section 15.6). Post-C2 review -> `CORRECTION_REQUIRED` (P2), documentation/evidence staleness -> **C3** (section 16). Post-C3 review -> `CORRECTION_REQUIRED` (P2), residual active-state/inventory contradiction -> **C4** (section 17). Post-C4 review -> `CORRECTION_REQUIRED` (P2), stale current-summary omitting C4 -> **C5** (section 18). Post-C5 review (packet-only) -> `CORRECTION_REQUIRED` (P2), unsupported secret-scan provenance explanation -> **C6** (section 19). Post-C6 review -> `CORRECTION_REQUIRED` (P2), duplicated/stale current-summary sections stopping at C5/C6 -> **C7** (section 20). Post-C7 review -> `CORRECTION_REQUIRED` (P2), residual noncanonical mutable numbered-correction summaries outside the canonical CURRENT CONTROL STATE block -> **C8** (section 21). Post-C8 review -> no new material functional, security, persistence, migration, parity, E2-A or E1 defect identified; F1-F4 and the test-only autocommit-pool contamination all remain CLOSED. **D1** (project-owner decision) -> the feature branch was synced with current main (merge `6de6fb0`, bringing PR #18 and PR #19 / ADR-035 into the review base) and a documentation-only correction **C9** was directed -> **C9** (section 22) reconciles the endpoint drift that sync created and applies the authorized narrow C7/C8 historical labelling. **Post-C9 fresh bounded review -> `CORRECTION_REQUIRED`.** It independently found **D1 CLOSED** and every substantive finding CLOSED — F1, F2, F3, F4 and the test-only autocommit-pool contamination — and identified no new material runtime, persistence, concurrency, migration, production-composition, security, parity, E2-A-semantic, E1-compatibility or main-synchronization defect. It returned `CORRECTION_REQUIRED` **solely for D2**: the canonical current-state blocks incorrectly applied ADR-035 retroactively to this already-running package. **C10** (section 23) corrects D2, documentation-only, across the same three governing documents; it reruns no deterministic suite. At every stage the reviewer found no additional material code, migration, persistence, production-composition, E2-A-semantic or E1-compatibility defect, and did not itself re-run any deterministic test. **A fresh bounded independent post-C10 review has NOT yet been performed, so Criterion Z remains NOT MET.** For present repository/review status, endpoints, inventory, lifecycle and deterministic evidence, see the CURRENT CONTROL STATE (section 0). |


---

## 15. Independent review of candidate `481a860`, and controller-authorized correction C2

### 15.1 The review result, stated as it happened

```text
Reviewed candidate    481a860297ca2a5e6c6b3fd2e87ed3a19581ba28
Baseline              22a4b28a2679503187a9db4cd5be580a8eac39ec   (unchanged)
Independent reviewer  external, read-only
Review result         CORRECTION_REQUIRED
Findings accepted     F1 (P1), F2 (P2), F3 (P2), F4 (P2)
Correction pass       C2 - the ONE bounded correction authorized after that review
Outcome               all four corrected; acceptance still PENDING a fresh independent
                      bounded re-review of the corrected candidate
```

**The candidate did not pass.** This section exists so no later reader can mistake C2's closure of
the four findings for the review having returned `ACCEPTED`.

C2 is a narrowly scoped authorization covering exactly these four findings plus the tests and
documentation needed to prove their closure. It is **not** authorization to revisit accepted E2-A
semantics, to alter the migration or schema, or to add E3 publication/write functionality. None of
those was done: **the migration file, the twelve-table schema, the constraint set, the model
registration and every E1 runtime, source and test file are untouched by C2**, and no second
Alembic revision exists.

### 15.2 F1 (P1) — `get_lineage()` was not snapshot-consistent

**The defect.** `PostgresAuthorityConfigurationProvider.get_lineage()` issued **two** PostgreSQL
statements — `repository.load_versions(...)` then `repository.load_retractions(...)`. Under
ordinary READ COMMITTED a snapshot is taken *per statement*, so a publication committing between
them could be half-seen. The provider then labelled that combination `completeness = COMPLETE`,
which is precisely the promise E2-B makes about complete lineage.

**The correction — one statement, one snapshot.** `repository.load_versions` and
`repository.load_retractions` are replaced by a single `repository.load_lineage(...)` that reads
**both** collections in **one `db.execute` round trip**, so PostgreSQL's own single-statement
snapshot is the consistency boundary. The physical shape is a `UNION ALL` over the version table
and the retraction table, discriminated by an integer `row_kind`, wrapped in an outer `SELECT`
carrying the existing `COUNT(*) OVER ()` completeness guard:

```sql
SELECT lineage.*, COUNT(*) OVER () AS total_rows
FROM (
    SELECT 0 AS row_kind, v.id, <shared>, <version-only>, NULL AS retraction_id, NULL AS retracted_at
    FROM <version table> v WHERE v.object_id = :object_id
    UNION ALL
    SELECT 1 AS row_kind, r.id, <shared>, NULL AS <version-only...>, r.retraction_id, r.retracted_at
    FROM <retraction table> r WHERE r.object_id = :object_id
) lineage
ORDER BY lineage.row_kind, lineage.effective_from, lineage.object_version,
         lineage.retraction_id, lineage.id
```

Three properties of that shape were deliberate:

```text
NATIVE TYPES PRESERVED    each absent column is an UNTYPED `NULL`, so PostgreSQL resolves the
                          union column's type from the branch that has one. `timestamptz` stays
                          `timestamptz`, `boolean` stays `boolean`, `jsonb` stays `jsonb`. Nothing
                          is serialized, stringified or re-parsed, and this module restates no
                          type name it would then have to keep in step with the migration.
NO ISOLATION-LEVEL CHANGE the caller-owned Session's isolation level is NOT mutated. `SET
                          TRANSACTION ISOLATION LEVEL REPEATABLE READ` on an arbitrary shared
                          Session is unsafe when its transaction has already begun and can leak
                          isolation state; the one-statement solution avoids the question.
ORDER PRESERVED           within the version rows the ORDER BY degenerates to
                          `effective_from, object_version, id` (retraction_id is constant NULL
                          there); within the retraction rows to `object_version, retraction_id,
                          id` (effective_from is constant NULL there) - the same two total orders
                          the two reads produced before.
```

**No semantic logic was added.** Splitting the returned rows back into two collections by their
discriminator is structural decoding, not judgement. Every version is still returned whatever its
state, every retraction is still returned as a FACT, nothing is filtered, ranked, coalesced,
normalised or hidden, ordering is still total and deterministic, a read failure still raises
`AuthorityConfigurationPortError` (fail-closed), and truncation is still detected by the unchanged
`COUNT(*) OVER ()` guard.

**Deterministic two-connection proof.**
`test_one_lineage_read_never_straddles_a_concurrent_publication` forces the exact dangerous
interleaving on **three separate, explicitly checked-out PostgreSQL connections** (asserted to be
three distinct backend PIDs, so no two parties can share one physical connection):

```text
1. seed authority AUTHORITY_ID with version 0001 only, no retractions.
2. WRITER connection: LOCK TABLE <retraction table> IN ACCESS EXCLUSIVE MODE, then - still
   UNCOMMITTED - publish BOTH halves of one lineage change: version 0002 correcting 0001, and a
   retraction of 0001. The VERSION table is deliberately left unlocked.
3. CONTROL connection proves the hybrid is genuinely available at that instant: it reads the
   version table WITHOUT waiting and sees the PRE-commit set ['0001'], while the retraction table
   is locked. A versions-then-retractions reader would therefore compose exactly the hybrid.
4. READER connection enters get_lineage and BLOCKS. The test does not sleep and hope: it waits
   until PostgreSQL itself reports an ungranted lock request on that table, then asserts the
   reader thread is still alive. That is the deterministic proof the interleaving occurred.
5. Only then does the writer COMMIT.
6. The reader's material must be one of the two states that genuinely existed, never a mixture.
```

**Result: PASS**, and the test was proved to be a real regression test rather than a vacuous one.
Against a faithful copy of the pre-C2 two-statement implementation, temporarily restored for one
proof run, it FAILS with exactly the hybrid the finding describes:

```text
AssertionError: a lineage read straddled a concurrent publication:
    versions=['0001'], retractions=['r-concurrent-publication']
```

The corrected implementation returns `versions={0001, 0002}` with the retraction — coherent, and
`COMPLETE`.

**Explicit boundary, as the review stated.** This guarantees coherence WITHIN one `get_lineage`
call. It does **not** attempt whole-resolution transactional consistency across the several
provider calls one resolution makes; the independent reviewer identified that as a future
PF-1A-E3 concern and C2 does not address it. `repository.load_lineage`'s docstring records the
boundary in the same terms.

The existing within-statement truncation and read-error tests are retained unchanged and still
pass. `test_the_kernel_re_sorts_even_without_a_provider_order_by` — the mutation-style check that
the kernel re-sorts even with the provider's ORDER BY removed — now patches `load_lineage`, so it
remains a live check rather than silently patching a function nothing calls.

### 15.3 F2 (P2) — the `lock_timeout` test could contaminate the connection pool

**The defect.** `test_a_real_lock_timeout_raises_a_port_error` issued a **session-level**
`SET lock_timeout = '250ms'` on the SHARED `store_db` session, then rolled back and issued
`RESET lock_timeout`. A SQLAlchemy `Session` **releases its physical connection to the pool when
its transaction ends**, so the `RESET` can execute on a *different* checkout while the original
pooled connection keeps the setting. The independent reviewer reproduced a full-suite failure in
an unrelated Commercial Offer test with `LockNotAvailable`.

**The mechanism, reproduced directly.** A throwaway probe run inside the E2-B container confirmed
the divergence that makes the pattern unsafe — `SET` and `RESET` landing on two different physical
PostgreSQL backends:

```text
SET landed on backend 11553; RESET landed on backend 11554
```

**The correction — a dedicated connection and `SET LOCAL`.** The timeout test no longer touches
`store_db`'s session configuration at all:

```text
DEDICATED CONNECTION   the connection is checked out EXPLICITLY (`engine.connect()`) and closed by
                       this test, so no other test can be handed it mid-experiment. A Session is
                       bound to that connection for the provider call.
SET LOCAL              the timeout is `SET LOCAL` inside the reading transaction, so PostgreSQL
                       itself reverts it at ROLLBACK. There is NO separate cleanup statement left
                       to misdirect - the failure mode is removed rather than made less likely.
NO POOL DISPOSAL       `engine.dispose()` is NOT used as a substitute for correct cleanup.
```

**The cleanup is PROVEN, not assumed**, on the same physical connection and before it is released:

```text
same backend PID asserted before and after the timeout exercise (pg_backend_pid());
`SHOW lock_timeout` asserted back at the captured server default on THAT connection;
a sweep of six freshly drawn pooled sessions asserted clean.
```

A companion structural test, `test_the_timeout_test_never_sets_a_session_level_lock_timeout`,
reads this module's own executable source and asserts that every `lock_timeout` statement in it is
`SET LOCAL` and that no `RESET` appears at all, so the fix cannot silently regress.

**Same-process regression sequence — PASS.** In one pytest process, in this order:

```text
tests/test_business_authority_store_provider.py::test_a_real_lock_timeout_raises_a_port_error
tests/test_business_authority_store_provider.py::test_the_timeout_test_never_sets_a_session_level_lock_timeout
tests/test_commercial_offers_api.py::test_latest_credit_review_drives_advisory_submission_readiness
                                                            3 passed
```

### 15.4 F3 (P2) — criterion N2 did not exercise real concurrency

**The defect.** `test_determinism_survives_table_reorganisation_and_concurrent_resolutions` opened
two sessions and resolved through them **one after the other**. That is a second *sequential*
resolution wearing two sessions: it could not detect shared mutable state, an order that depends
on interleaved reads, or a non-re-entrant provider, because none of those conditions was ever
created. Criterion N2 asks for concurrent resolutions.

**The correction — two genuinely parallel resolutions, with the overlap proved.**

```text
SEPARATE SESSIONS       each worker builds its own SessionLocal; no SQLAlchemy Session is shared
                        between threads.
SEPARATE CONNECTIONS    the two backend PIDs are asserted DISTINCT, so the two resolutions cannot
                        have run over one physical connection.
REAL PARALLELISM        two threads, started together and joined together.
BARRIER INSIDE THE      a `threading.Barrier(2)` is tripped INSIDE the provider, during the first
PROVIDER PATH           `get_lineage` of each resolution - not before the resolver is called.
                        Neither thread can pass it until the other is also inside a resolution.
FAILS ON SERIALIZATION  the barrier carries a timeout, so a serialized run does not quietly
                        degrade into a weaker test.
DETERMINISTIC FAILURE   worker exceptions are collected under a lock and re-asserted on the main
                        thread; the barrier is aborted on failure so the peer cannot hang.
FULL EQUALITY           both concurrent results are compared to the serialized baseline using
                        `serialize_result` - the canonical whole-result form, not a subset.
```

**Result: PASS**, and proved non-vacuous: with the two workers temporarily started and joined one
at a time, the test FAILS deterministically —

```text
AssertionError: a concurrent resolution failed: BrokenBarrierError()
assert not [BrokenBarrierError(), BrokenBarrierError()]
```

The `VACUUM (FULL, ANALYZE)` table-reorganisation half of N2 is retained in the same test,
unchanged.

### 15.5 F4 (P2) — two independent production composition seams

**The defect.** The candidate independently defined **both** `resolver.build_production_resolver()`
and `production_composition.build_production_business_authority_resolver(db)`, and described both
as the production composition seam. Only the second bound PostgreSQL. Both refused safely on the
day, which is exactly why the duplication was worth removing rather than tolerating: two
successor-facing seams drift apart the moment a later package adds the actor-person and HR
providers to one of them, and a consumer that bound the other would then get a resolver whose
dependency assembly nobody had reviewed.

**The correction — one canonical implementation.**

```text
CANONICAL     production_composition.build_production_business_authority_resolver(db)
COMPATIBILITY none. `resolver.build_production_resolver()` is WITHDRAWN rather than kept as an
              alias, because it had no caller anywhere in the repository, its historical import
              path could not be preserved in any case, and a second public name that a later
              package could bind is precisely the drift hazard the finding names.
```

The canonical seam lives in `production_composition.py` and not in `resolver.py` because it must
**bind** the E2-B authority configuration provider, and that provider is persistence-bound while
`resolver.py` is deliberately not. Placing it the other way round would have inverted the
dependency direction — the persistence-free E2-A module reaching into the SQLAlchemy-bound E2-B
module — and required a deferred in-function import to dodge a circular import. **No circular
import was introduced, and the E2-A kernel remains entirely free of SQLAlchemy** (the existing
E2-A source-level assertions that prove this are unchanged and still green).

`ProductionCompositionUnavailableError` remains defined in `resolver.py`. It is E2-A's ONE refusal
signal, raised now from exactly ONE seam; a shared exception type is not a duplicated
implementation. Its docstring records where the seam went and why.

The canonical refusal message now names **both** phases' sections
(`PF-1A-E2-A section 9.6, PF-1A-E2-B section 5.3`), because it is now the only refusal either
phase has.

**What the canonical path does, and the tests that prove each:**

```text
binds the PostgreSQL AuthorityConfigurationPort supplied by E2-B     PROVED AT RUNTIME
binds NO synthetic/reference actor-person or HR provider             PROVED STRUCTURALLY
names both absent authoritative dependencies in its refusal          PROVED
refuses to compose; produces no callable resolver                    PROVED
no environment variable / settings flag / feature toggle / provider  PROVED
argument selects a provider
```

- `test_ns_pr_02_there_is_exactly_one_production_composition_implementation` walks the **AST of
  every production module in the package** and asserts that exactly ONE function anywhere raises
  `ProductionCompositionUnavailableError`, and that it is
  `production_composition.build_production_business_authority_resolver`. A future thin delegating
  compatibility wrapper would still leave that count at one; a second separately authored refusal
  would not. It also asserts the withdrawn factory is genuinely gone, not merely unused.
- `test_ns_pr_02_the_canonical_seam_genuinely_binds_postgresql` records the seam's actual call to
  `build_authority_configuration_provider`, asserts it received the session and returned a
  `PostgresAuthorityConfigurationProvider`, and then **uses that provider to read this PostgreSQL
  store** — so the binding is observed at runtime, not inferred from source. It asserts the
  refusal still raises and that no resolver object is produced.
- The pre-existing `test_ns_pr_02_the_production_composition_refuses_to_compose`,
  `test_ns_pr_02_the_seam_takes_no_provider_and_reads_no_configuration_switch` and the three
  `NS-PR-01` unreachability tests are retained unchanged and still pass.

**Narrowest successor-phase reconciliation of two E2-A phase-local assertions.** Both named the
withdrawn factory by name; both are re-pointed at the canonical seam and carry an in-place comment
recording what they used to assert and why it changed. Nothing they guaranteed was weakened:

| E2-A test | Was | Now |
| --- | --- | --- |
| `test_no_environment_variable_flag_or_toggle_can_select_a_synthetic_provider` | `inspect.signature(resolver.build_production_resolver).parameters == {}` | the canonical seam's ONLY parameter is `db` (no `*args`, no `**kwargs`), its module consults no `environ`/`getenv`/`settings`/`feature_flag`/`toggle`, **and** `resolver` no longer offers a second seam to bind instead. The unchanged `resolver`-source scan is retained. |
| `test_the_production_composition_refuses_to_compose` | called `resolver.build_production_resolver()` | calls the canonical seam, still asserting the refusal raises and its message contains `"authoritative"` and `"9.6"`. No database round trip occurs: constructing the read-only provider issues no statement. |

**None of the properties the review listed as must-not-weaken was weakened:** no
environment/config synthetic switch, no synthetic production import, no ADMIN bypass, no
current-authorization caller-controlled `as_of`, no route/API consumer, and fail-closed production
refusal — all still asserted and green.

### 15.6 One further defect, found WHILE verifying C2: an autocommit connection leaked to the pool

**This was not one of the four review findings. It was found by the C2 verification itself**, when
the full backend regression failed on the two new/altered tests that use `LOCK TABLE` and
`SET LOCAL`. It is recorded here rather than quietly fixed, because it is a real pre-existing
cross-test contamination defect of exactly the F2 family and because the F1/F2 corrections are what
exposed it.

**The defect.** The criterion N2 determinism test needs autocommit for `VACUUM (FULL)`, which
cannot run inside a transaction block. It obtained it by taking a `raw_connection()` and calling
`set_autocommit(True)` on the DBAPI connection directly. **The pool's reset-on-return issues a
ROLLBACK but does not restore autocommit**, so that connection went back into the pool STILL IN
AUTOCOMMIT. Any later test that drew it found:

```text
LOCK TABLE   rejected outright - psycopg.errors.NoActiveSqlTransaction:
             "LOCK TABLE can only be used in transaction blocks"
SET LOCAL    SILENTLY INEFFECTIVE - it has no transaction block to act in, so
             `SHOW lock_timeout` returned '0' instead of '250ms'
```

Both symptoms were observed in the full regression run:

```text
FAILED tests/test_business_authority_store_provider.py::test_one_lineage_read_never_straddles_a_concurrent_publication
       psycopg.errors.NoActiveSqlTransaction: LOCK TABLE can only be used in transaction blocks
FAILED tests/test_business_authority_store_provider.py::test_a_real_lock_timeout_raises_a_port_error
       AssertionError: assert '0' == '250ms'
```

The silent half is the dangerous one: a `SET LOCAL` that does nothing does not announce itself.

**The correction — scope the autocommit rather than undo it.** The N2 test now uses
`engine.connect().execution_options(isolation_level="AUTOCOMMIT")`, the supported form: SQLAlchemy
restores the connection's original isolation level when it is returned to the pool. This is the
same remedy shape as F2 — scope the state to something that ends, rather than issue a cleanup
statement that can miss.

**Guard test.** `test_no_e2b_test_returns_a_connection_to_the_pool_in_autocommit` draws a spread of
pooled connections and asserts each DBAPI connection's `autocommit` flag is `False`. The flag is
read **directly**, because `Connection.get_isolation_level()` asks the server for the transaction
isolation level and never reports autocommit at all — a first attempt at this guard using that API
passed while the leak was still present, and was replaced.

**Verified in both directions.** With the leaking `raw_connection()`/`set_autocommit(True)` form
temporarily restored and the two modules run in one process:

```text
3 failed, 59 passed
  test_one_lineage_read_never_straddles_a_concurrent_publication      (LOCK TABLE rejected)
  test_a_real_lock_timeout_raises_a_port_error                        (SET LOCAL ineffective)
  test_no_e2b_test_returns_a_connection_to_the_pool_in_autocommit     (the guard itself)
```

With the corrected form: **62 passed**.

**Scope.** This touches one test file (`test_business_authority_store_non_store_parity.py`) and
adds one guard test. No production code, migration, schema, constraint or E1 file is involved.

**Historical PF-1A-E2-A evidence is deliberately NOT rewritten.**
`docs/agent/acceptance/pf-1a-e2-a-business-authority-resolution-contract-and-domain-kernel-acceptance.md`
and `docs/continuity/PF_1A_E2_A_IMPLEMENTATION_HANDOFF_2026-09-04.md` still name
`build_production_resolver()` as the seam that refused at the time they were written, which is
what was true then. C2 leaves them exactly as they are, following the same principle C1 followed.
One ACTIVE file carrying a now-stale reference — the docstring of
`backend/tests/fixtures/pf_1a_e2_a_reference_providers.py` — is updated to name the canonical seam,
with a one-line note of what it used to name, because that is live test code rather than a dated
evidence record.

### 15.7 What C2 did NOT touch

```text
migration parent, one-head structure and the migration file itself   UNCHANGED
the twelve-table schema and every structural constraint              UNCHANGED
class A storability; absence of semantic SQL constraints             UNCHANGED
integer id + TEXT stable object_id interpretation of ADR-007         UNCHANGED
raw discovery; immutable dereference (`load_version`)                UNCHANGED
the C1 test reconciliation and the models_metadata exact-path        UNCHANGED
  exemption
absence of routes / frontend / OpenAPI / business events             UNCHANGED
the PF-1A-E1 permission and grant boundary                           UNCHANGED
absence of any production configuration write path                   UNCHANGED
no UPDATE/DELETE-denying database triggers were added                UNCHANGED
E2-A kernel, ports, domain, lineage, material, scope, evaluators,    UNCHANGED
  evidence, contract and defects modules
```

No new Alembic revision was created and none was authorized.

---

## 16. Correction C3 — active evidence/state reconciliation

**HISTORICAL SNAPSHOT AS OF C3.** This section records the state, review verdict and next-gate
expectation exactly as they stood immediately after correction C3, before corrections C4 through C7
existed. It is preserved as historical evidence; for present repository and review status, see the
CURRENT CONTROL STATE (section 0).

**Status: documentation-only correction, applied after a fresh bounded independent re-review of
the C2-corrected candidate.**

### 16.1 What the fresh re-review found

The fresh independent bounded re-review examined the C2-corrected candidate and found **NO
additional material code, migration, persistence or production-composition defect**. It considered
findings F1 (P1), F2 (P2), F3 (P2) and F4 (P2) — sections 15.2-15.5 — together with the separately
discovered autocommit-pool-contamination correction (section 15.6), **SUBSTANTIVELY CLOSED**.

**Its verdict was nevertheless `CORRECTION_REQUIRED`.** Active documentation and evidence in this
record, the package definition document and the implementation handoff still described the
SUPERSEDED pre-C2 committed/uncommitted state and the SUPERSEDED pre-C2 test counts (144 focused /
882 full backend / 799 secret-scan files, and an over-general "nothing is committed" framing) as if
they were the current result for the corrected candidate, rather than clearly labelling them as
historical. That is a genuine documentation defect: a later reader could not tell, without
independently re-deriving it, which numbers describe the candidate actually being reviewed.

**This does not mean the independent reviewer re-ran any deterministic test.** The reviewer
evaluated evidence and documentation; the counts recorded in section 9.2 above are this package's
own tool output, run and recorded by the implementation side, not something the reviewer executed
itself.

### 16.2 What correction C3 changed

**Documentation only.** C3 edits exactly three files:

```text
docs/agent/pf-1a/PF_1A_E2_B_PERSISTED_PUBLISHED_AUTHORITY_STORE_AND_RUNTIME_WIRING.md
docs/agent/acceptance/pf-1a-e2-b-persisted-published-authority-store-acceptance.md   (this file)
docs/continuity/PF_1A_E2_B_IMPLEMENTATION_HANDOFF_2026-09-04.md
```

It changes no production code, no test, no migration or schema, no E1 file, no E2-A semantic
module, and none of C2's runtime corrections (F1-F4, or the autocommit-pool-contamination fix).
Every historical evidence value C3 touches is RECONCILED — explicitly labelled as pre-C2/original
— never erased or rewritten as though it never occurred.

### 16.3 Current committed / uncommitted boundary

```text
Baseline                     22a4b28a2679503187a9db4cd5be580a8eac39ec   (last commit on main
                                                                       before this package)
Reviewed candidate           481a860297ca2a5e6c6b3fd2e87ed3a19581ba28
Candidate status              COMMITTED to this feature branch and PUSHED to
                             origin/pf-1a-e2-b-persisted-published-authority-store-runtime-wiring.
                             NOT merged to main; main is untouched.
Correction C2                 a further working-tree layer on top of the committed candidate,
                             currently UNCOMMITTED and UNPUSHED, touching exactly the twelve
                             files enumerated in the implementation handoff section 1 - all
                             twelve are MODIFICATIONS of files already present in the committed
                             candidate, none is a new file beyond it.
Correction C3 (this record)   documentation-only; edits three of those twelve files (the
                             documentation records) and adds no new file to the set.
```

### 16.4 Review status, stated without ambiguity

```text
481a860                received CORRECTION_REQUIRED   (F1 P1, F2 P2, F3 P2, F4 P2)
C2                      corrected all four, plus the separately discovered autocommit-pool-
                        contamination defect (section 15.6)
Fresh C2 re-review      found NO additional material code/migration/persistence/composition
                        defect; considered F1-F4 and the autocommit correction SUBSTANTIVELY
                        CLOSED; verdict nevertheless CORRECTION_REQUIRED, for the
                        documentation/evidence staleness recorded in section 16.1
C3                      documentation-only reconciliation of that finding
PF-1A-E2-B status       NOT ACCEPTED
Criterion Z             NOT MET
Next gate               a FURTHER FRESH bounded independent re-review of this
                        documentation-corrected candidate
```

**PF-1A-E2-B remains NOT ACCEPTED. Criterion Z remains NOT MET.**

---

## 17. Correction C4 — residual active-state/inventory reconciliation

**HISTORICAL SNAPSHOT AS OF C4.** This section records the state, review verdict and next-gate
expectation exactly as they stood immediately after correction C4, before correction C5 through C7
existed. It is preserved as historical evidence; for present repository and review status, see the
CURRENT CONTROL STATE (section 0).

**Status: documentation-only correction, applied after a FURTHER FRESH bounded independent
re-review of the C3-corrected candidate.**

### 17.1 What the post-C3 re-review found

The post-C3 bounded independent re-review examined the C3-corrected candidate and found **NO
additional material code, migration, persistence or production-composition defect**. Findings F1
(P1), F2 (P2), F3 (P2) and F4 (P2) (sections 15.2-15.5), and the separately discovered
autocommit-pool-contamination correction (section 15.6), remain **SUBSTANTIVELY CLOSED**. The
deterministic results in section 9.2 were supplied as evidence only and were **not** re-run by the
independent reviewer.

**Its verdict was nevertheless `CORRECTION_REQUIRED` (P2)**, identifying four classes of residual
active-state/inventory contradiction:

```text
A. The package definition document's section 1 status banner, its "Document status" field, and
   its section 15 "Package status" paragraph still read, in active/current tense, as
   pre-implementation status ("PROPOSED... NOT IMPLEMENTED... NOT YET STARTABLE") rather than
   being clearly labelled as historical, definition-time status superseded by that document's
   section 1.0.
B. Section 10 above claimed `backend/app/models_metadata.py` is "the only pre-existing file this
   package modifies" - untrue of the effective C2-corrected candidate, which also modifies the
   pre-existing `resolver.py` (C2/F4) and pre-existing E2-A test/fixture files.
C. Criterion G in the table above (section 14) read "no E2-A file in the diff" - false for the
   same reason: `resolver.py` and E2-A test/fixture files are in the effective diff.
D. The implementation handoff's section 3 committed-candidate inventory did not explicitly
   enumerate every file candidate `481a860` actually committed relative to baseline - in
   particular the three E2-B documentation records and the C1 security-boundary test
   reconciliation - so the full 21-file baseline-to-working-tree inventory could not be confirmed
   from section 3 alone.
```

### 17.2 What correction C4 changed

**Documentation only.** C4 edits exactly the same three files C3 edited:

```text
docs/agent/pf-1a/PF_1A_E2_B_PERSISTED_PUBLISHED_AUTHORITY_STORE_AND_RUNTIME_WIRING.md
docs/agent/acceptance/pf-1a-e2-b-persisted-published-authority-store-acceptance.md   (this file)
docs/continuity/PF_1A_E2_B_IMPLEMENTATION_HANDOFF_2026-09-04.md
```

It changes no production code, no test, no migration or schema, no E1 behaviour, no E2-A semantic
behaviour (kernel, domain, ports, contract, evidence, lineage, material, scope or evaluators), and
none of C2's runtime corrections (F1-F4, or the autocommit-pool-contamination fix). Historical
proposal/definition-time material named in class A above is preserved in the package definition
document and explicitly labelled as historical; it is never erased or rewritten as though it never
existed. Section 10 above and criterion G in section 14 are corrected precisely, replacing one
absolute claim with a precise account distinguishing the original candidate, C1, and C2/F4 -
never replacing one false absolute with another.

### 17.3 Baseline-to-working-tree inventory (established from `git`, not inferred from prose)

```text
Baseline -> committed candidate 481a860 (git diff --name-status, 19 files):
  6 production ADDED    (migration, models.py, postgres_provider.py, production_composition.py,
                          repository.py, store_contract.py)
  1 production MODIFIED (models_metadata.py)
  8 test ADDED           (pf_1a_e2_b_corpus.py, pf_1a_e2_b_store.py, store_coverage.py,
                          store_non_store_parity.py, store_parity.py, store_provider.py,
                          store_schema.py, store_wiring.py)
  1 test MODIFIED        (test_business_authority_security_boundary.py, C1 reconciliation baked
                          into the committed candidate)
  3 documentation records (acceptance.md ADDED, this package's definition document MODIFIED,
                          the implementation handoff ADDED)

Committed candidate -> current working tree (git status --short, 12 files, all MODIFIED):
  postgres_provider.py, production_composition.py, repository.py                    (already
                          counted above as production ADDED by 481a860; C2/F1/F4 modify them
                          further)
  resolver.py                                                                       (pre-existing
                          since PF-1A-E2-A, NOT touched by 481a860; first modified here, C2/F4)
  pf_1a_e2_a_reference_providers.py                                                 (pre-existing
                          since PF-1A-E2-A, NOT touched by 481a860; first modified here, C2/F4)
  test_business_authority_security_boundary.py                                      (already
                          counted above as test MODIFIED by 481a860 via C1; C2/F4 re-points it
                          further)
  test_business_authority_store_non_store_parity.py, test_business_authority_store_provider.py,
  test_business_authority_store_wiring.py                                           (already
                          counted above as test ADDED by 481a860; C2 modifies them further)
  the three documentation records                                                   (already
                          counted above; C2/C3/C4 modify them further)

Union (distinct files touched from baseline to the current working tree): 21 - the 19 above plus
the two pre-existing E2-A files (resolver.py, pf_1a_e2_a_reference_providers.py) that 481a860
never touched and the working-tree layer touches for the first time. A file legitimately appears
in both the baseline->481a860 list and the 481a860->working-tree list where 481a860 introduced or
modified it and the correction layer modified it again; the two lists are not disjoint and are not
forced to be.
```

### 17.4 Review status, stated without ambiguity

```text
481a860                 received CORRECTION_REQUIRED   (F1 P1, F2 P2, F3 P2, F4 P2)
C2                       corrected all four, plus the separately discovered autocommit-pool-
                        contamination defect (section 15.6)
Post-C2 re-review        found NO additional material code/migration/persistence/composition
                        defect; considered F1-F4 and the autocommit correction SUBSTANTIVELY
                        CLOSED; verdict nevertheless CORRECTION_REQUIRED, for the
                        documentation/evidence staleness recorded in section 16.1
C3                       documentation-only reconciliation of that finding
Post-C3 re-review        AGAIN found NO additional material code/migration/persistence/
                        composition defect; AGAIN considered F1-F4 and the autocommit
                        correction SUBSTANTIVELY CLOSED; verdict nevertheless
                        CORRECTION_REQUIRED (P2), for the residual active-state/inventory
                        contradictions recorded in section 17.1
C4                       documentation-only reconciliation of those four residual classes
PF-1A-E2-B status        NOT ACCEPTED
Criterion Z              NOT MET
Next gate                a FURTHER FRESH bounded independent re-review of this
                        documentation-corrected candidate
```

**PF-1A-E2-B remains NOT ACCEPTED. Criterion Z remains NOT MET.**

---

## 18. Correction C5 — current-summary closure

**HISTORICAL SNAPSHOT AS OF C5.** This section records the state, review verdict and next-gate
expectation exactly as they stood immediately after correction C5, before correction C6 through C7
existed. It is preserved as historical evidence; for present repository and review status, see the
CURRENT CONTROL STATE (section 0).

**Status: documentation-only correction, applied after a further FRESH bounded independent
re-review of the C4-corrected candidate.**

### 18.1 What the post-C4 re-review found

The post-C4 bounded independent re-review examined the C4-corrected candidate and found **NO
additional material code, migration, persistence or production-composition defect**. Findings F1
(P1), F2 (P2), F3 (P2) and F4 (P2) (sections 15.2-15.5), and the separately discovered
autocommit-pool-contamination correction (section 15.6), remain **SUBSTANTIVELY CLOSED**. The
deterministic results in section 9.2 were supplied as evidence only and were **not** re-run by the
independent reviewer.

**Its verdict was nevertheless `CORRECTION_REQUIRED` (P2)**, with a single finding: several active/
current-tense summaries across this record, the package definition document and the implementation
handoff still described the repository state as of C3 or as of C4 (for example the top-of-document
status banner reading "DOCUMENTATION RECONCILED UNDER C3", and inventory annotations such as
"record, C2 then C3") rather than the actual current state, which by that point already also
included C4.

### 18.2 What correction C5 changed

**Documentation only.** C5 edits exactly the same three files C3 and C4 edited:

```text
docs/agent/pf-1a/PF_1A_E2_B_PERSISTED_PUBLISHED_AUTHORITY_STORE_AND_RUNTIME_WIRING.md
docs/agent/acceptance/pf-1a-e2-b-persisted-published-authority-store-acceptance.md   (this file)
docs/continuity/PF_1A_E2_B_IMPLEMENTATION_HANDOFF_2026-09-04.md
```

It changes no production code, no test, no migration or schema, no E1 behaviour, no E2-A semantic
behaviour (kernel, domain, ports, contract, evidence, lineage, material, scope or evaluators), and
none of C2's runtime corrections (F1-F4, or the autocommit-pool-contamination fix). It does not
reopen or restate C2, C3 or C4's own substantive content; it reconciles every remaining
active-tense summary across the three documents so each now reads the correction layer as
C2/C3/C4/C5 collectively — one still-uncommitted, still-unpushed 12-file working-tree layer sitting
on top of the committed-and-pushed-but-not-merged candidate `481a860`, not a thirteenth file and
not a separate Git layer. Historical C3-only and C4-only snapshots in sections 16 and 17 above are
preserved and explicitly labelled as historical; they are not rewritten.

### 18.3 Review status, stated without ambiguity

```text
481a860                  received CORRECTION_REQUIRED   (F1 P1, F2 P2, F3 P2, F4 P2)
C2                        corrected all four, plus the separately discovered autocommit-pool-
                         contamination defect (section 15.6)
Post-C2 re-review         found NO additional material code/migration/persistence/composition
                         defect; considered F1-F4 and the autocommit correction SUBSTANTIVELY
                         CLOSED; verdict nevertheless CORRECTION_REQUIRED, for the
                         documentation/evidence staleness recorded in section 16.1
C3                        documentation-only reconciliation of that finding
Post-C3 re-review         AGAIN found NO additional material code/migration/persistence/
                         composition defect; AGAIN considered F1-F4 and the autocommit
                         correction SUBSTANTIVELY CLOSED; verdict nevertheless
                         CORRECTION_REQUIRED (P2), for the residual active-state/inventory
                         contradictions recorded in section 17.1
C4                        documentation-only reconciliation of those four residual classes
Post-C4 re-review         AGAIN found NO additional material code/migration/persistence/
                         composition defect; AGAIN considered F1-F4 and the autocommit
                         correction SUBSTANTIVELY CLOSED; verdict nevertheless
                         CORRECTION_REQUIRED (P2), because several active/current summaries
                         still omitted C4, recorded in section 18.1
C5                        documentation-only reconciliation of that finding, closing the
                         current-summary omissions across all three documents
PF-1A-E2-B status         NOT ACCEPTED
Criterion Z               NOT MET
Next gate                 a FRESH bounded independent re-review of this C5-corrected
                         candidate, not yet performed
```

**PF-1A-E2-B remains NOT ACCEPTED. Criterion Z remains NOT MET.**

---

## 19. Correction C6 — secret-scan provenance reconciliation

**HISTORICAL SNAPSHOT AS OF C6.** This section records the state, review verdict and next-gate
expectation exactly as they stood immediately after correction C6, before correction C7 existed. It
is preserved as historical evidence; for present repository and review status, see the CURRENT
CONTROL STATE (section 0).

**Status: documentation-only correction, applied after a fresh bounded independent re-review of
the C5-corrected candidate.**

### 19.1 What the post-C5 re-review found

The post-C5 bounded independent re-review was **PACKET-ONLY**: deterministic tests were not
rerun. It re-examined the full post-C5 effective candidate and found **NO additional material
runtime, migration, persistence, composition, E2-A-semantic or E1-compatibility defect**. Findings
F1 (P1), F2 (P2), F3 (P2) and F4 (P2) (sections 15.2-15.5), and the separately discovered
autocommit-pool-contamination correction (section 15.6), remain **SUBSTANTIVELY CLOSED**.
Whole-resolution snapshot consistency across multiple provider calls remains, as already recorded
in section 15.2, outside the claimed F1 boundary.

**Its verdict was nevertheless `CORRECTION_REQUIRED` (P2)**, with a single finding: the current
secret-scan evidence in this record (section 9.2), the package definition document (section 1.0B)
and the implementation handoff (section 14.0) correctly reported "801 files scanned, no findings"
but incorrectly explained the change from the earlier 799-file count as "799 -> +2, the two files
C2 added" or materially equivalent wording. That explanation is not supported by the established
current inventory: baseline -> HEAD is 19 changed files, HEAD -> working tree is exactly 12
MODIFIED files, and the baseline-to-working-tree union is 21 distinct files; C2, C3, C4 and C5 did
not add files to the working tree. **The reviewer did not dispute the current 801-file /
no-findings result itself — only the unsupported provenance explanation attached to it.**

### 19.2 What correction C6 changed

**Documentation only.** C6 edits exactly the same three files C3, C4 and C5 edited:

```text
docs/agent/pf-1a/PF_1A_E2_B_PERSISTED_PUBLISHED_AUTHORITY_STORE_AND_RUNTIME_WIRING.md
docs/agent/acceptance/pf-1a-e2-b-persisted-published-authority-store-acceptance.md   (this file)
docs/continuity/PF_1A_E2_B_IMPLEMENTATION_HANDOFF_2026-09-04.md
```

It removes the unsupported "799 -> +2, the two files C2 added" explanation everywhere it appeared
as a CURRENT statement, retaining "801 files scanned, no findings" unchanged. **It does NOT invent
a replacement causal explanation** for why the scan enumerated two more files than the earlier
799-file count; no repository evidence available to this correction establishes that cause, and
none is guessed at. It changes no production code, no test, no migration or schema, no E1
behaviour, no E2-A semantic behaviour (kernel, domain, ports, contract, evidence, lineage, material,
scope or evaluators), and none of C2's runtime corrections (F1-F4, or the autocommit-pool-
contamination fix). It does not reopen or restate C2, C3, C4 or C5's own substantive content; it
corrects only the secret-scan provenance defect named in section 19.1. The current correction layer
remains **C2/C3/C4/C5/C6 collectively** — one still-uncommitted, still-unpushed 12-file
working-tree layer sitting on top of the committed-and-pushed-but-not-merged candidate `481a860`,
not a thirteenth file and not a separate Git layer. Historical C3-only, C4-only and C5-only
snapshots in sections 16, 17 and 18 above are preserved and explicitly labelled as historical; they
are not rewritten.

### 19.3 Review status, stated without ambiguity

```text
481a860                  received CORRECTION_REQUIRED   (F1 P1, F2 P2, F3 P2, F4 P2)
C2                        corrected all four, plus the separately discovered autocommit-pool-
                         contamination defect (section 15.6)
Post-C2 re-review         found NO additional material code/migration/persistence/composition
                         defect; considered F1-F4 and the autocommit correction SUBSTANTIVELY
                         CLOSED; verdict nevertheless CORRECTION_REQUIRED, for the
                         documentation/evidence staleness recorded in section 16.1
C3                        documentation-only reconciliation of that finding
Post-C3 re-review         AGAIN found NO additional material code/migration/persistence/
                         composition defect; AGAIN considered F1-F4 and the autocommit
                         correction SUBSTANTIVELY CLOSED; verdict nevertheless
                         CORRECTION_REQUIRED (P2), for the residual active-state/inventory
                         contradictions recorded in section 17.1
C4                        documentation-only reconciliation of those four residual classes
Post-C4 re-review         AGAIN found NO additional material code/migration/persistence/
                         composition defect; AGAIN considered F1-F4 and the autocommit
                         correction SUBSTANTIVELY CLOSED; verdict nevertheless
                         CORRECTION_REQUIRED (P2), because several active/current summaries
                         still omitted C4, recorded in section 18.1
C5                        documentation-only reconciliation of that finding, closing the
                         current-summary omissions across all three documents
Post-C5 re-review         PACKET-ONLY (deterministic tests not rerun); AGAIN found NO additional
                         material runtime/migration/persistence/composition/E2-A/E1 defect; F1-F4
                         and the autocommit correction remain SUBSTANTIVELY CLOSED; verdict
                         nevertheless CORRECTION_REQUIRED (P2), for the unsupported secret-scan
                         provenance recorded in section 19.1
C6                        documentation-only correction of that finding; removes the unsupported
                         "two files C2 added" explanation without inventing a replacement cause
PF-1A-E2-B status         NOT ACCEPTED
Criterion Z               NOT MET
Next gate                 a FRESH bounded independent re-review of this C6-corrected
                         candidate, not yet performed
```

**PF-1A-E2-B remains NOT ACCEPTED. Criterion Z remains NOT MET.**

---

## 20. Correction C7 — canonical current-state normalization

**HISTORICAL SNAPSHOT AS OF C7.** This section records the state, review verdict and next-gate
expectation exactly as they stood immediately after correction C7, before corrections C8 and C9
existed. It is preserved as historical evidence; its endpoint identities and "not yet performed"
next gate describe that earlier point and are NOT updated to current values. For present
repository and review status, see the CURRENT CONTROL STATE (section 0).

**Status: documentation-only correction, applied after a fresh bounded independent re-review of
the C6-corrected candidate.** That re-review found the C6 secret-scan provenance defect itself
CLOSED — current evidence correctly states "801 files scanned, no findings" with no invented causal
explanation — and **no additional material runtime, migration, persistence, production-composition,
E2-A-semantic or E1-compatibility defect**. Findings F1-F4 (sections 15.2-15.5) and the separately
discovered autocommit-pool-contamination correction (section 15.6) remain SUBSTANTIVELY CLOSED. The
reviewer did not rerun deterministic tests.

### 20.1 What the post-C6 re-review found

**Its verdict was nevertheless `CORRECTION_REQUIRED` (P2)**, with a single finding: this record,
the package definition document and the implementation handoff each maintained more than one
section that independently claimed to describe CURRENT/active repository or review status, and
several of those sections stopped at C5 or C6 rather than reflecting the true current state — a
structural documentation defect in which each new correction made other supposedly-current
summaries stale. Named examples: acceptance record (this document) section 14 Criterion Z stopped
at C5; the implementation handoff sections 1, 3 and 13 read as current but stopped before C6; and
the package definition document's section 15 package-status paragraph and historical-snapshot
supersession pointers named specific later corrections (C4, C5, C6) rather than pointing at a
stable, generic present-state reference.

### 20.2 What correction C7 changed

**Documentation only.** C7 edits exactly the same three files C3, C4, C5 and C6 edited:

```text
docs/agent/pf-1a/PF_1A_E2_B_PERSISTED_PUBLISHED_AUTHORITY_STORE_AND_RUNTIME_WIRING.md
docs/agent/acceptance/pf-1a-e2-b-persisted-published-authority-store-acceptance.md   (this file)
docs/continuity/PF_1A_E2_B_IMPLEMENTATION_HANDOFF_2026-09-04.md
```

C7 establishes exactly one authoritative CURRENT CONTROL STATE block per document (section 0 here).
Sections that previously carried their own independent "current" framing were converted to one of:
a labelled HISTORICAL SNAPSHOT of an earlier correction point (sections 9.2, 16, 17, 18, 19), or a
short pointer to section 0 with no restated chain (the top-of-document status banner, criterion Z
in section 14). Brittle numbered supersession pointers ("superseded by section 18 (C5)", "see
section 19 (C6) below") were replaced with a stable pointer to this document's CURRENT CONTROL
STATE, so a future correction does not require revisiting every historical pointer again.

It changes no production code, no test, no migration or schema, no E1 behaviour, no E2-A semantic
behaviour, and none of C2's runtime corrections (F1-F4, or the autocommit-pool-contamination fix).
It does not reopen or restate C2, C3, C4, C5 or C6's own substantive content; their historical
records (sections 16, 17, 18, 19) are preserved exactly as they described the state at each point,
with only their own forward-pointing cross-reference future-proofed as described above. The
current correction layer remains **C2/C3/C4/C5/C6/C7 collectively** — one still-uncommitted,
still-unpushed 12-file working-tree layer sitting on top of the committed-and-pushed-but-not-merged
candidate `481a860`, not a thirteenth file and not a separate Git layer. C7 itself edits only the
same three documentation files already inside that 12-file set.

### 20.3 Review status, stated without ambiguity

```text
481a860                  received CORRECTION_REQUIRED   (F1 P1, F2 P2, F3 P2, F4 P2)
C2                        corrected all four, plus the separately discovered autocommit-pool-
                         contamination defect (section 15.6)
Post-C2 re-review         found NO additional material defect; verdict nevertheless
                         CORRECTION_REQUIRED, documentation/evidence staleness -> C3 (16.1)
Post-C3 re-review         AGAIN found NO additional material defect; verdict nevertheless
                         CORRECTION_REQUIRED (P2), residual active-state/inventory
                         contradictions -> C4 (17.1)
Post-C4 re-review         AGAIN found NO additional material defect; verdict nevertheless
                         CORRECTION_REQUIRED (P2), stale current-summary omitting C4 -> C5 (18.1)
Post-C5 re-review         PACKET-ONLY; AGAIN found NO additional material defect; verdict
                         nevertheless CORRECTION_REQUIRED (P2), unsupported secret-scan
                         provenance -> C6 (19.1)
Post-C6 re-review         AGAIN found NO additional material defect; verdict nevertheless
                         CORRECTION_REQUIRED (P2), duplicated/stale current-summary sections
                         stopping at C5/C6 -> C7 (this section, 20.1)
PF-1A-E2-B status         NOT ACCEPTED
Criterion Z               NOT MET
Next gate                 a FRESH bounded independent re-review of this C7-corrected
                         candidate, not yet performed
```

**PF-1A-E2-B remains NOT ACCEPTED. Criterion Z remains NOT MET.** For the full, current, consolidated
repository and review state, see the CURRENT CONTROL STATE (section 0).

---

## 21. Correction C8 — noncanonical mutable-summary elimination

**HISTORICAL SNAPSHOT AS OF C8.** This section records the state, review verdict and next-gate
expectation exactly as they stood immediately after correction C8, before correction C9 existed.
It is preserved as historical evidence; its endpoint identities and "not yet performed" next gate
describe that earlier point and are NOT updated to current values. For present repository and
review status, see the CURRENT CONTROL STATE (section 0).

**Status: documentation-only correction, applied after a fresh bounded independent re-review of
the C7-corrected candidate.** That re-review found **no additional material runtime, migration,
persistence, production-composition, E2-A-semantic or E1-compatibility defect**. Findings F1-F4
(sections 15.2-15.5) and the separately discovered autocommit-pool-contamination correction
(section 15.6) remain SUBSTANTIVELY CLOSED. The reviewer did not rerun deterministic tests.

### 21.1 What the post-C7 re-review found

**Its verdict was nevertheless `CORRECTION_REQUIRED` (P2)**, with a single finding: the package
definition document and the implementation handoff still maintained noncanonical mutable
numbered-correction summaries outside their respective canonical CURRENT CONTROL STATE blocks, so
the same staleness mechanism C7 was meant to close could recur. Named examples: the package
definition document's section 1 banner still pointed to "section 1.0 and corrections C2-C6"
(already stale because C7 existed) and its section 1.0 heading enumerated only C2-C6; the
implementation handoff's section 1 independently restated present candidate status and the full
C2/C3/C4/C5/C6/C7 correction-layer chain instead of pointing to CURRENT CONTROL STATE; and its
section 3 repeatedly described itself as "kept current through" specific correction numbers,
maintaining a second mutable present-state chronology outside the canonical block.

### 21.2 What correction C8 changed

**Documentation only.** C8 edits exactly the same three files C3, C4, C5, C6 and C7 edited:

```text
docs/agent/pf-1a/PF_1A_E2_B_PERSISTED_PUBLISHED_AUTHORITY_STORE_AND_RUNTIME_WIRING.md
docs/agent/acceptance/pf-1a-e2-b-persisted-published-authority-store-acceptance.md   (this file)
docs/continuity/PF_1A_E2_B_IMPLEMENTATION_HANDOFF_2026-09-04.md
```

C8 removed the remaining noncanonical present-state pointers the post-C7 review identified: the
package definition document's section 1 banner and section 1.0 heading no longer enumerate specific
correction numbers as a present-state supersession chain; the implementation handoff's section 1
now defers present repository/review status to its own CURRENT CONTROL STATE block instead of
restating it; and the implementation handoff's section 3 is now explicitly labelled inventory
evidence for the 19/12/21 file relationship rather than a second, independently mutating
current-review chronology. The canonical CURRENT CONTROL STATE block (section 0 here) remains the
sole mutable operational-state source per document. Acceptance criterion Z (this record's section
14) is the one deliberate exception, because an acceptance-criteria table is expected to show its
own history; it is not treated as a competing present-state summary.

It changes no production code, no test, no migration or schema, no E1 behaviour, no E2-A semantic
behaviour, and none of C2's runtime corrections (F1-F4, or the autocommit-pool-contamination fix).
It does not reopen or restate C2, C3, C4, C5, C6 or C7's own substantive content; their historical
records (sections 16, 17, 18, 19, 20) are preserved exactly as they described the state at each
point. The current correction layer remains **C2/C3/C4/C5/C6/C7/C8 collectively** — one
still-uncommitted, still-unpushed 12-file working-tree layer sitting on top of the
committed-and-pushed-but-not-merged candidate `481a860`, not a thirteenth file and not a separate
Git layer. C8 itself edits only the same three documentation files already inside that 12-file set.

### 21.3 Review status, stated without ambiguity

```text
481a860                  received CORRECTION_REQUIRED   (F1 P1, F2 P2, F3 P2, F4 P2)
C2                        corrected all four, plus the separately discovered autocommit-pool-
                         contamination defect (section 15.6)
Post-C2 re-review         found NO additional material defect; verdict nevertheless
                         CORRECTION_REQUIRED, documentation/evidence staleness -> C3 (16.1)
Post-C3 re-review         AGAIN found NO additional material defect; verdict nevertheless
                         CORRECTION_REQUIRED (P2), residual active-state/inventory
                         contradictions -> C4 (17.1)
Post-C4 re-review         AGAIN found NO additional material defect; verdict nevertheless
                         CORRECTION_REQUIRED (P2), stale current-summary omitting C4 -> C5 (18.1)
Post-C5 re-review         PACKET-ONLY; AGAIN found NO additional material defect; verdict
                         nevertheless CORRECTION_REQUIRED (P2), unsupported secret-scan
                         provenance -> C6 (19.1)
Post-C6 re-review         AGAIN found NO additional material defect; verdict nevertheless
                         CORRECTION_REQUIRED (P2), duplicated/stale current-summary sections
                         stopping at C5/C6 -> C7 (20.1)
Post-C7 re-review         AGAIN found NO additional material defect; verdict nevertheless
                         CORRECTION_REQUIRED (P2), residual noncanonical mutable
                         numbered-correction summaries -> C8 (this section, 21.1)
PF-1A-E2-B status         NOT ACCEPTED
Criterion Z               NOT MET
Next gate                 a FRESH bounded independent re-review of this C8-corrected
                         candidate, not yet performed
```

**PF-1A-E2-B remains NOT ACCEPTED. Criterion Z remains NOT MET.** For the full, current, consolidated
repository and review state, see the CURRENT CONTROL STATE (section 0).

---

## 22. Correction C9 — review-endpoint reconciliation after the main sync

**HISTORICAL SNAPSHOT AS OF C9.** This section records the state, review verdict and next-gate
expectation exactly as they stood immediately after correction C9. It PREDATES the post-C9
independent review and correction C10, and its next-gate statement is therefore the one that was
true then, not now. It is preserved as historical evidence and is NOT updated to current values.
For present repository, lifecycle and review status, see the CURRENT CONTROL STATE (section 0).

**Status: documentation-only correction, applied after a fresh bounded independent re-review of
the C8-corrected candidate and a project-owner decision (D1).** The post-C8 re-review found **no
new material functional, security, persistence, migration, parity, E2-A-semantic or
E1-compatibility defect**. Findings F1, F2, F3 and F4 (sections 15.2-15.5) and the separately
discovered test-only autocommit-pool-contamination correction (section 15.6) all remain
**CLOSED**. The reviewer did not rerun deterministic tests, and C9 reran none either.

### 22.1 What changed underneath the package, and why that mattered

Between the post-C8 review and this correction, `main` advanced and the feature branch was synced
with it:

```text
PR #18   f32e989   DEV-ORCH reviewer requalification closure
PR #19   5d737c0   ADR-035, functional/documentation reconciliation policy   <- current main
         6de6fb0   "Sync PF-1A-E2-B branch with current main"                <- current local HEAD
                   (merge of origin candidate 481a860 with 5d737c0)
```

That sync did not touch the package's own work — `git diff --name-only 481a860 6de6fb0` reports
only eight main-side files — but it **moved the review base**, and the canonical CURRENT CONTROL
STATE blocks did not follow. They still named `22a4b28` as "protected baseline" and `481a860` as
the "committed+pushed candidate", and bound the 19/12/21 inventory to those two commits. After the
sync four distinct endpoints existed and only two were recorded, so a reader could not tell which
commit the package is now reviewed against, nor that the pushed origin ref had become stale.

This was a **documentation/current-state defect only**. No code, test, migration, contract,
authorization behaviour or deterministic result was affected by it, and none is affected by its
correction.

### 22.2 D1 — the project-owner decision

```text
D1   The feature branch was synced with current main (merge 6de6fb0, bringing PR #18 and
     PR #19 / ADR-035 into the review base), and a documentation-only correction C9 was
     directed - scoped to the three package documents, and additionally authorizing the
     narrow C7/C8 historical labelling described in 22.3.
```

### 22.3 What correction C9 changed

**Documentation only.** C9 edits exactly the same three files C3 through C8 edited:

```text
docs/agent/pf-1a/PF_1A_E2_B_PERSISTED_PUBLISHED_AUTHORITY_STORE_AND_RUNTIME_WIRING.md
docs/agent/acceptance/pf-1a-e2-b-persisted-published-authority-store-acceptance.md   (this file)
docs/continuity/PF_1A_E2_B_IMPLEMENTATION_HANDOFF_2026-09-04.md
```

```text
1. All three canonical CURRENT CONTROL STATE blocks now distinguish FOUR endpoints -
   historical inception baseline 22a4b28, current main / review base 5d737c0, current local
   feature HEAD 6de6fb0, and current origin feature ref 481a860 - and state explicitly that
   481a860 is stale relative to the local HEAD because it predates the sync.
2. The 19/12/21 inventory is bound to the correct endpoints: 19 = current main 5d737c0 ->
   local HEAD 6de6fb0; 12 = local HEAD 6de6fb0 -> working tree; 21 = current main 5d737c0 ->
   working tree, the union of the other two, which overlap in 10. The COUNTS are unchanged;
   only their endpoints are corrected. The same 19 paths are also what 22a4b28 -> 481a860
   reports, which is why the counts stayed arithmetically correct while their labels went stale.
3. The implementation handoff's section 3 endpoint labels are corrected while its factual file
   inventory - the 6+1+8+1+3 = 19 committed breakdown, the 12 further-modified files, the
   10-file overlap and the 2 files unique to the working-tree layer - is preserved.
4. The correction-layer composition is updated to C2/C3/C4/C5/C6/C7/C8/C9.
5. The post-C8 review -> D1 -> C9 chronology is appended to each canonical block and to
   acceptance criterion Z.
6. Criterion Z is updated through C9 and remains NOT MET.
7. Correction records C7 and C8 - which still carried then-current statements such as a next
   gate "not yet performed" - now carry the same concise HISTORICAL SNAPSHOT label already used
   for C3 through C6, so those older statements cannot compete with the canonical CURRENT
   CONTROL STATE. Their historical facts and endpoint values are preserved exactly and are
   deliberately NOT updated to current values.
8. The next gate is stated as a fresh post-C9 independent bounded review.
```

C9 changes no production code, no test, no migration or schema, no E1 behaviour, no E2-A semantic
behaviour, and none of C2's runtime corrections. It does not reopen or restate the substantive
content of C2 through C8; their historical records (sections 16 through 21) are preserved as they
described the state at each point, with C7 and C8 gaining only the historical label described
above. The current correction layer remains **C2/C3/C4/C5/C6/C7/C8/C9 collectively** — one
still-uncommitted, still-unpushed 12-file working-tree layer, not a thirteenth file and not a
separate Git layer. C9 itself edits only the same three documentation files already inside that
12-file set.

### 22.4 Review status, stated without ambiguity

```text
481a860                  received CORRECTION_REQUIRED   (F1 P1, F2 P2, F3 P2, F4 P2)
C2                        corrected all four, plus the separately discovered autocommit-pool-
                         contamination defect (section 15.6)
Post-C2 re-review         found NO additional material defect; verdict nevertheless
                         CORRECTION_REQUIRED, documentation/evidence staleness -> C3 (16.1)
Post-C3 re-review         AGAIN found NO additional material defect; verdict nevertheless
                         CORRECTION_REQUIRED (P2), residual active-state/inventory
                         contradictions -> C4 (17.1)
Post-C4 re-review         AGAIN found NO additional material defect; verdict nevertheless
                         CORRECTION_REQUIRED (P2), stale current-summary omitting C4 -> C5 (18.1)
Post-C5 re-review         PACKET-ONLY; AGAIN found NO additional material defect; verdict
                         nevertheless CORRECTION_REQUIRED (P2), unsupported secret-scan
                         provenance -> C6 (19.1)
Post-C6 re-review         AGAIN found NO additional material defect; verdict nevertheless
                         CORRECTION_REQUIRED (P2), duplicated/stale current-summary sections
                         stopping at C5/C6 -> C7 (20.1)
Post-C7 re-review         AGAIN found NO additional material defect; verdict nevertheless
                         CORRECTION_REQUIRED (P2), residual noncanonical mutable
                         numbered-correction summaries -> C8 (21.1)
Post-C8 re-review         AGAIN found NO new material functional, security, persistence,
                         migration, parity, E2-A or E1 defect; F1-F4 and the test-only
                         autocommit-pool contamination all remain CLOSED
D1                        project-owner decision: branch synced with current main (6de6fb0,
                         bringing ADR-035 into the review base); documentation-only C9
                         directed, including the narrow C7/C8 historical labelling
C9                        endpoint reconciliation (this section, 22.1-22.3)
PF-1A-E2-B status         NOT ACCEPTED
Criterion Z               NOT MET
Next gate                 a FRESH bounded independent re-review of this C9-corrected
                         candidate, not yet performed
```

**PF-1A-E2-B remains NOT ACCEPTED. Criterion Z remains NOT MET.** For the full, current,
consolidated repository and review state, see the CURRENT CONTROL STATE (section 0).

---

## 23. Correction C10 — pre-ADR-035 in-flight lifecycle reconciliation

**Status: documentation-only correction, applied after the fresh post-C9 bounded independent
review.** That review returned **`CORRECTION_REQUIRED`** with a single material finding, **D2**.

### 23.1 What the post-C9 review found

It independently confirmed **CLOSED**: F1, F2, F3, F4, the separately discovered test-only
autocommit-pool-contamination leak, and **D1** (post-sync repository identity, corrected by C9). It
identified **no new material runtime, persistence, concurrency, migration,
production-composition, security, parity, PF-1A-E2-A-semantic, PF-1A-E1-compatibility or
main-synchronization defect.**

**D2, the sole material finding.** Each governing document's ACTIVE canonical CURRENT CONTROL
STATE said, in substance, that "ADR-035 now governs this package's two-phase
(FUNCTIONAL_CORRECTION -> FINAL_ACCEPTANCE) review lifecycle". That is incorrect for this
already-running review sequence: PF-1A-E2-B entered independent review and correction **before**
ADR-035 was integrated, and the wording retroactively applied a lifecycle the package has never
been run under.

### 23.2 The transitional rule C10 establishes

```text
ADR-035 IS integrated and authoritative on current main for applicable work going forward, and
is present in this package's synchronized current-main baseline (5d737c0, PR #19).

ADR-035 is NOT applied retroactively to PF-1A-E2-B. This already-running package is CLOSED under
the strict PRE-ADR-035 Criterion-Z process that has governed its C1-C10 sequence throughout:

  - C1-C10 are NOT converted into ADR-035 Phase 1 / Phase 2 states;
  - FUNCTIONAL_REVIEW_COMPLETE is NOT required and is NOT a gate for this package;
  - FUNCTIONAL_CORRECTION -> FINAL_ACCEPTANCE is NOT this package's closure lifecycle;
  - the valid top-level bounded-review verdict remains exactly
      ACCEPTED / CORRECTION_REQUIRED / MODEL_ESCALATION_REQUIRED;
  - Criterion Z becomes MET only when a fresh bounded independent review returns ACCEPTED.

This is a PACKAGE-SPECIFIC TRANSITIONAL EXCEPTION for an in-flight package. It does not weaken,
rewrite, contradict or suspend ADR-035, and it says nothing about any later applicable work.
```

### 23.3 What correction C10 changed

**Documentation only.** C10 edits exactly the same three governing files C3 through C9 edited:

```text
docs/agent/pf-1a/PF_1A_E2_B_PERSISTED_PUBLISHED_AUTHORITY_STORE_AND_RUNTIME_WIRING.md
docs/agent/acceptance/pf-1a-e2-b-persisted-published-authority-store-acceptance.md   (this file)
docs/continuity/PF_1A_E2_B_IMPLEMENTATION_HANDOFF_2026-09-04.md
```

```text
1. The incorrect active ADR-035 lifecycle claim is replaced, in all three canonical CURRENT
   CONTROL STATE blocks, by the transitional rule in 23.2. All three now materially agree.
2. Correction composition updated to C2/C3/C4/C5/C6/C7/C8/C9/C10.
3. The post-C9 -> D2 -> C10 chronology is appended to each canonical block and to criterion Z.
4. Criterion Z is updated through C10 and remains NOT MET.
5. The C9 correction records gain a HISTORICAL SNAPSHOT AS OF C9 label, the same narrow
   treatment already applied to C3-C8, so their then-current "post-C9 review not yet performed"
   next gate cannot compete with the canonical block. C9's historical facts, endpoint values and
   original next-gate statement are preserved exactly and are NOT rewritten.
6. The sole current next gate is a fresh bounded independent POST-C10 review.
```

**C10 does not reopen D1**, whose closure by C9 the post-C9 review independently confirmed, and it
does not reopen any functional finding. It changes no production code, no test, no migration or
schema, no CI, no script, no configuration, no ADR-035 document, and none of C2's runtime
corrections. The repository endpoints and the 19/12/21 inventory established by C9 are preserved
unchanged. The current correction layer remains **C2/C3/C4/C5/C6/C7/C8/C9/C10 collectively** — one
still-uncommitted, still-unpushed 12-file working-tree layer, not a thirteenth file and not a
separate Git layer.

**No deterministic suite was rerun for C10.** The evidence figures in the CURRENT CONTROL STATE
(section 0) and section 9.2 are unchanged, including the tracked-secret scan's "801 files scanned,
no findings", for which no causal provenance is asserted.

**PF-1A-E2-B remains NOT ACCEPTED. Criterion Z remains NOT MET.** The next gate is a FRESH bounded
independent post-C10 review, not yet performed. For the full, current, consolidated repository,
lifecycle and review state, see the CURRENT CONTROL STATE (section 0).
