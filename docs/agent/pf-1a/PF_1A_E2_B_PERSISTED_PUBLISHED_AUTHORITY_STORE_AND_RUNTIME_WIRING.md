# PF-1A-E2-B — Persisted Published Authority Store & Runtime Wiring

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

## 1. Status

**HISTORICAL DEFINITION-TIME STATUS (recorded before implementation began; for authoritative present
repository and review status, see the CURRENT CONTROL STATE, section 1.0G): PROPOSED PACKAGE
DEFINITION. NOT IMPLEMENTED. NOT INDEPENDENTLY ACCEPTED. NOT YET STARTABLE.**

**CURRENT STATUS: IMPLEMENTED and under independent-review correction; NOT ACCEPTED.** For the
authoritative, present repository and review status — protected baseline, committed candidate,
working-tree correction layer, file inventory, deterministic evidence and the next review gate —
see the **CURRENT CONTROL STATE** block in section 1.0G. No reader should treat the banner line
above as a description of the present state; it describes this document's status at the time the
definition itself was first written, before PF-1A-E2-A existed and before this package was
implemented.

This document remains the architecture/contract-definition artefact: sections 2 onward define
*what* PF-1A-E2-B must implement, and that normative definition is unchanged by implementation
having since occurred. Section 1.0 records what was actually built against it. No runtime code,
database schema, Alembic migration, API route, business event, permission rule or frontend screen
is created, changed or authorized by the DEFINITION sections of this document; the actual runtime
artefacts the implementation created are inventoried in section 1.0 and the acceptance/handoff
records it cross-references.

```text
Package ID:        PF-1A-E2-B
Package name:      Persisted Published Authority Store & Runtime Wiring
Predecessor:       PF-1A-E2-A (Business Authority Resolution Contract & Domain Kernel)
                   - itself a PROPOSED definition at the time this document was written
Successor:         PF-1A-E3 (Governed Authority Configuration, Publication and
                   Self-Escalation Prevention)
Definition-time
repository state:  main @ b6e58994ca4486819312457e89adec22ad720495
Document status:   HISTORICAL DEFINITION-TIME STATUS (recorded before this package's own
                   implementation; for present repository and review status, see the CURRENT
                   CONTROL STATE, section 1.0G): proposed definition. Correction cycles 1, 2 and 3 were
                   applied to the predecessor package after three independent reviews. That package's final
                   independent re-review found F-10 PARTIALLY_RESOLVED and the package's
                   correction/model ceilings were exhausted. A NEW human-authorized work package,
                   PF-1A-E2 F-10 DEFINITION CLOSURE, then completed F-10 through the THREE-CLASS
                   fixture taxonomy of E2-A section 9.7 and the TOTAL per-fixture manifest in
                   section 5.7 below. A re-review of THAT package found F-10 still
                   PARTIALLY_RESOLVED with three residual blocking findings (F-10.1, F-10.2,
                   F-10.3) and exhausted its ceilings; a further NEW human-authorized package,
                   PF-1A-E2 F-10 FINAL DEFINITION CLOSURE, closed all three - the missing
                   pure-kernel fixture for an absent publication_reference_type, the deferred A-03
                   classification (decided: unreachable, withdrawn, replaced by NS-K-01), and the
                   scope of the A/B1/B2 taxonomy (now authority-store only, with the new
                   section 5.7A non-store scenario table). Pending re-review under
                   docs/agent/architecture/INDEPENDENT_IMPLEMENTATION_REVIEW_WORKFLOW.md
```

### 1.0 Implementation outcome and correction history (recorded 4 September 2026; independent
reviews and corrections recorded from 5 September 2026 — see the CURRENT CONTROL STATE, section
1.0G, for the current correction layer)

**IMPLEMENTED AND CORRECTED UNDER C2; NOT ACCEPTED.** See the CURRENT CONTROL STATE (section 1.0G)
for the authoritative present repository and review status. Acceptance is recorded by the
independent reviewer, never by the implementation agent. The paragraphs below record what was
actually done at implementation time and under C2; the sections after them are the definition,
unchanged.

**The reviewed candidate `481a860297ca2a5e6c6b3fd2e87ed3a19581ba28` returned
`CORRECTION_REQUIRED`** from the independent bounded review (the independent reviewer), with four accepted
findings. All four are corrected in the one authorized bounded correction pass C2; see section 1.0A
below and section 15 of the acceptance record. **The candidate did not pass review, and no
statement here says it did.**

```text
Historical inception baseline     22a4b28a2679503187a9db4cd5be580a8eac39ec
  (protected main at the time)    The commit this package was branched from and originally
                                  reviewed against; NO LONGER the review base. For the current
                                  main/review base and the other endpoints, see the CURRENT
                                  CONTROL STATE (section 1.0G).
Branch                            pf-1a-e2-b-persisted-published-authority-store-runtime-wiring
Alembic head DISCOVERED at start  20260831_0030
  verified from                   backend/alembic/versions/ (29 revisions, single linear chain),
                                  `alembic heads`, and `alembic current` against a PostgreSQL 17
                                  database built from empty. NOT taken from this document.
New revision                      20260904_0031
down_revision                     20260831_0030
Production composition option     (a) REFUSE TO COMPOSE - the option section 5.3 recommends,
                                  and the one PF-1A-E2-A had already taken, so the new provider is
                                  bound into that existing seam rather than opening a second one.
```

Twelve tables were created - for each of the four object families, a stable identity table, an
immutable published version table and an append-only retraction assertion table. Four retraction
tables rather than one shared polymorphic table, because 5.6 requires a foreign key to the STABLE
identity of the retracted object and a shared table would have needed a discriminator CHECK that
5.6 does not list.

Verification results, in full, are in
`docs/agent/acceptance/pf-1a-e2-b-persisted-published-authority-store-acceptance.md`; the
implementation handoff is `docs/continuity/PF_1A_E2_B_IMPLEMENTATION_HANDOFF_2026-09-04.md`.

**Original implementation-time headline figures (4-5 September 2026, after reconciliation C1,
BEFORE the independent review and BEFORE correction C2 — historical, and superseded for the
current corrected candidate by the post-C2 figures in section 1.0B below):** 144 focused E2-B
tests pass; 87 of 87 manifest IDs carry an executing E2-B test; the parity-marked set is exactly
the 64-scenario corpus; the 117 existing PF-1A-E1 tests pass unmodified; the PF-1A-E2-A focused
suite is 356 passed; full backend regression is 882 passed, 0 failed. Before controller
reconciliation C1 those last two figures were 354 passed / 2 failed and 880 passed / 2 failed; the
+2 is exactly the two reconciled assertions turning green, and no test was added, removed, skipped
or xfailed by C1. **These 144/882 figures remain an accurate record of that earlier state; they
are not the current result for the C2-corrected candidate.**

**The one material blocker raised on 4 September 2026 is CLOSED by controller-authorized
reconciliation C1 (5 September 2026).** It was an implementation-time TEST-CONTRACT contradiction at
the E2-A -> E2-B phase boundary, not an E2-B semantic implementation defect, and it is recorded in
full in section 12 of
`docs/agent/acceptance/pf-1a-e2-b-persisted-published-authority-store-acceptance.md`. In summary:

Two PF-1A-E2-A tests carried PHASE-LOCAL structural assertions - that the Business Authority package
could never contain `models.py` or `repository.py`, that `models_metadata.py` could never mention
`business_authority`, and that no production source outside the package could reference it. PF-1A-E2-A
section 17 assigns all four of those artifacts to PF-1A-E2-B by name, so the assertions expire by
design once this package lands; keeping them would have made a conforming PF-1A-E2-B impossible
rather than protecting anything.

Under C1 the controller authorized revising ONLY those two stale assertions, in
`backend/tests/test_business_authority_security_boundary.py`. The persistence prohibitions were
removed and the still-valid route/API-schema exclusion retained (the test is renamed to
`test_the_package_adds_no_route_and_no_api_schema_surface`); and the repository-wide production
scan was RETAINED with exactly one file exempted, `app/models_metadata.py`, guarded by inner
assertions that the exemption covers model registration only and never consumer wiring.

**No E2-A semantic rule, fail-closed behaviour, reason code, evidence obligation, ADMIN protection,
E1 permission/grant/route protection or synthetic-provider production-reachability protection
changed.** Production Business Authority resolution remains unavailable until the authoritative
actor-person and HR providers exist. No E2-A or E2-B runtime source was changed by C1.

**Criterion V is henceforth read as:** all PF-1A-E2-A semantic and security behaviour remains green,
with these two phase-transition assertions EXPLICITLY RECONCILED rather than pretending they
remained literally unmodified. The original E2-A form of both is preserved in the acceptance record;
historical E2-A acceptance evidence is not rewritten.

### 1.0A Independent review result and correction C2 (5 September 2026)

```text
Reviewed candidate    481a860297ca2a5e6c6b3fd2e87ed3a19581ba28
Baseline              22a4b28a2679503187a9db4cd5be580a8eac39ec   (unchanged by C2)
Independent reviewer  external, read-only
Review result         CORRECTION_REQUIRED
Findings              F1 (P1)  get_lineage() issued TWO statements, so under READ COMMITTED it
                               could return a combination of pre-commit versions and post-commit
                               retractions - a state that never existed - labelled COMPLETE.
                      F2 (P2)  the real-lock-timeout test set a SESSION-level `lock_timeout` on
                               the SHARED store session; a Session releases its connection at
                               transaction end, so the later `RESET` could land on a different
                               checkout and leave a contaminated pooled connection behind.
                      F3 (P2)  the criterion N2 test opened two sessions but resolved through them
                               SEQUENTIALLY, so it never exercised concurrent resolutions.
                      F4 (P2)  two independently authored production composition seams existed -
                               `resolver.build_production_resolver()` and
                               `production_composition.build_production_business_authority_resolver(db)`
                               - and only the second bound PostgreSQL.
Correction pass       C2 - the ONE bounded correction authorized after that review
Status after C2       all four corrected and proved; ACCEPTANCE STILL PENDING a FRESH independent
                      bounded re-review of the corrected candidate
```

**How each was corrected**, in one line each; the full evidence, including the deterministic proofs
that each new test genuinely fails against the defective behaviour, is section 15 of
`docs/agent/acceptance/pf-1a-e2-b-persisted-published-authority-store-acceptance.md`:

```text
F1  `repository.load_versions` + `load_retractions` are replaced by ONE `load_lineage(...)` that
    reads both collections in ONE `db.execute` (a typed-NULL `UNION ALL` with an integer row_kind
    discriminator, wrapped in the existing COUNT(*) OVER () completeness guard), so PostgreSQL's
    own single-statement snapshot is the consistency boundary. No isolation level is mutated on a
    caller-owned Session. No semantic logic added: splitting the returned rows by discriminator is
    structural decoding. Proved by a three-connection test that forces the interleaving with a
    real committing writer and waits on PostgreSQL's own ungranted-lock report; that test fails
    with the exact hybrid against a faithful copy of the two-statement implementation.
F2  the timeout test now checks out its OWN connection and uses `SET LOCAL` inside the reading
    transaction, so PostgreSQL reverts it at ROLLBACK and there is no separate cleanup statement
    to misdirect. Restoration is proved on the SAME backend PID before release, plus a clean sweep
    of freshly drawn pooled sessions; a companion source-level test forbids session-level `SET`
    and any `RESET` in that module.
F3  criterion N2 now runs two resolutions in two threads on two separate connections (distinct
    backend PIDs asserted), with a `threading.Barrier(2)` tripped INSIDE the provider during each
    resolution's first lineage acquisition, so a serialized run raises `BrokenBarrierError` and
    FAILS rather than passing weakly. Both results are compared to the serialized baseline in full.
F4  `production_composition.build_production_business_authority_resolver(db)` is the ONE canonical
    seam; `resolver.build_production_resolver()` is WITHDRAWN (it had no caller, and a second
    public name is the drift hazard the finding names). An AST test asserts exactly one function
    in the package raises the refusal; a runtime test observes the seam binding the PostgreSQL
    provider and then reading this store. Two E2-A phase-local assertions that named the withdrawn
    factory are re-pointed at the canonical seam - the narrowest reconciliation - with no
    weakening of the no-toggle, no-synthetic, no-ADMIN-bypass, no-caller-`as_of`, no-consumer or
    fail-closed-refusal properties.
```

**C2 changed no migration, no schema, no constraint, no model registration, no E1 file and no E2-A
semantic module.** No second Alembic revision exists. One baseline E2-A file is touched -
`resolver.py` - solely to withdraw the duplicate seam under F4; its two resolution entry points,
its error type and all its semantics are unchanged.

### 1.0B Deterministic evidence detail (established at C2; consolidated into CURRENT CONTROL STATE, section 1.0G)

```text
E2-B focused suite (6 modules)       149 passed   (144 -> +5 regression tests added by C2)
PF-1A-E2-A focused suite             356 passed   (unchanged since reconciliation C1)
PF-1A-E1 compatibility suite         117 passed   (unchanged, unmodified)
Full backend regression              887 passed, 0 failed   (882 -> +5, the five C2 regression
                                     tests; no test removed, skipped or xfailed)
Alembic heads / current              20260904_0031 (head)   - unchanged, no second revision
Tracked-secret scan                  801 files scanned, no findings
Contract fixture validator           all rules passed
Repository script test suite         58 tests, OK
git diff --check                     clean
python -m compileall                 OK (new + changed sources)
```

These figures were established at C2 and remain unchanged through C3/C4/C5/C6/C7, since none of
those corrections touched production code, tests, or the migration; they are consolidated in the
CURRENT CONTROL STATE (section 1.0G), which is authoritative if this detail and that block ever
appear to diverge. The 144/882/799 figures in section 1.0 above remain the accurate historical
record of the ORIGINAL implementation, before the independent review and before C2; they are
superseded, not wrong, and are retained for that reason. Full detail is section 15 of the
acceptance record.

### 1.0C Correction C3 — active evidence/state reconciliation

**HISTORICAL SNAPSHOT AS OF C3.** This section records the state, review verdict and next-gate
expectation exactly as they stood immediately after correction C3, before corrections C4 through C7
existed. It is preserved as historical evidence; for present repository and review status, see the
document's CURRENT CONTROL STATE (section 1.0G).

**Status: documentation-only correction, applied after a fresh bounded independent re-review of
the C2-corrected candidate.** That re-review found NO additional material code, migration,
persistence or production-composition defect, and considered findings F1-F4 (section 1.0A) plus
the separately discovered autocommit-pool-contamination correction (acceptance record section
15.6) SUBSTANTIVELY CLOSED. **Its verdict was nevertheless `CORRECTION_REQUIRED`**, because active
documentation and evidence across this document, the acceptance record and the implementation
handoff still described the SUPERSEDED pre-C2 committed/uncommitted state and the SUPERSEDED
pre-C2 test counts (144/882/799, and an over-general "nothing is committed" framing) as if they
were the current result, rather than clearly labelling them as historical.

**Current committed / uncommitted boundary.** Baseline `22a4b28a2679503187a9db4cd5be580a8eac39ec`
is the last commit on `main` before this package. The reviewed candidate
`481a860297ca2a5e6c6b3fd2e87ed3a19581ba28` **IS committed** to this feature branch and **pushed**
to `origin/pf-1a-e2-b-persisted-published-authority-store-runtime-wiring`; it is **not** merged to
`main`, which remains untouched. Correction C2 is the current **UNCOMMITTED and UNPUSHED**
working-tree layer on top of that committed candidate, touching exactly the twelve files
enumerated in the implementation handoff's section 1 — all twelve are MODIFICATIONS of files
already present in the committed candidate; none is a new file beyond it. Correction C3 (this
record) is documentation-only and adds no further production or test file to that set; it edits
three of the twelve files already in it (the three documentation records).

**Correction C3 changes documentation only.** It does not touch, and was not authorized to touch,
any production code, any test, the migration or schema, any E1 file, any E2-A semantic module, or
any C2 runtime correction (F1-F4, or the autocommit-pool-contamination fix). It edits exactly
three files: this document, the acceptance record, and the implementation handoff. Every
historical evidence value it reconciles is explicitly labelled as pre-C2/original — never erased
or rewritten as though it never occurred.

**PF-1A-E2-B remains NOT ACCEPTED. Criterion Z remains NOT MET.** The independent reviewer
evaluated evidence and documentation; it did not itself re-run any deterministic test — the counts
in section 1.0B are this package's own tool output, not a claim about what the reviewer executed.
The next gate is a FURTHER FRESH bounded independent re-review of this documentation-corrected
candidate.

**Start precondition.** PF-1A-E2-B may begin only after PF-1A-E2-A has been implemented,
independently reviewed, ACCEPTED and integrated on `main`.

**The exact protected-`main` baseline commit for E2-B is established only after E2-A integration,
and the actual Alembic head that E2-B's migration will parent onto is discovered at that time.
Neither may be predicted, invented or copied from this document.** The definition-time head in this
repository is `20260831_0030` (PF-1A-E1), and PF-1A-E2-A adds no migration, so `20260831_0030` is
the *expected* parent — but the implementation package must verify the actual head from
`backend/alembic/versions/` and `alembic heads` at start, exactly as PF-1A-E1 did, and use whatever
it finds. If another package has integrated a migration in the meantime, the discovered head wins
and the migration slot must be reconfirmed with the controller.

### 1.0D Correction C4 — residual active-state/inventory reconciliation

**HISTORICAL SNAPSHOT AS OF C4.** This section records the state, review verdict and next-gate
expectation exactly as they stood immediately after correction C4, before correction C5 through C7
existed. It is preserved as historical evidence; for present repository and review status, see the
document's CURRENT CONTROL STATE (section 1.0G).

**Status: documentation-only correction, applied after a FURTHER FRESH bounded independent
re-review of the C3-corrected candidate.** That re-review found **NO additional material code,
migration, persistence or production-composition defect**: findings F1-F4 (section 1.0A) and the
separately discovered autocommit-pool-contamination correction (acceptance record section 15.6)
remain SUBSTANTIVELY CLOSED, and the deterministic results in section 1.0B were supplied as
evidence only and were **not** re-run by the independent reviewer.

**Its verdict was nevertheless `CORRECTION_REQUIRED` (P2)**, because active documentation across
this document, the acceptance record and the implementation handoff still contained four classes
of residual contradiction with the post-C3 candidate state:

```text
A. This document's section 1 status banner, its "Document status" field, and section 15's
   "Package status" paragraph still read as CURRENT pre-implementation status ("PROPOSED... NOT
   IMPLEMENTED... NOT YET STARTABLE") rather than being clearly labelled as historical,
   definition-time status superseded by this section and section 1.0.
B. The acceptance record's section 10 claimed `backend/app/models_metadata.py` is "the only
   pre-existing file this package modifies" - no longer true of the effective, C2-corrected
   candidate, which also modifies the pre-existing `resolver.py` (C2/F4) and pre-existing E2-A
   test/fixture files (section 1.0A, section 1.0C).
C. The acceptance record's criterion G parenthetical, "no E2-A file in the diff", is false for
   the same reason: `resolver.py` and E2-A test/fixture files are in the effective diff.
D. The implementation handoff's section 3 committed-candidate inventory did not explicitly
   enumerate every file candidate `481a860` actually committed relative to baseline - in
   particular the three E2-B documentation records and the C1 security-boundary test
   reconciliation - so a reader could not confirm the full 21-file baseline-to-working-tree
   inventory from section 3 alone.
```

**Correction C4 changes documentation only.** It edits exactly the same three files C3 edited:

```text
docs/agent/pf-1a/PF_1A_E2_B_PERSISTED_PUBLISHED_AUTHORITY_STORE_AND_RUNTIME_WIRING.md   (this file)
docs/agent/acceptance/pf-1a-e2-b-persisted-published-authority-store-acceptance.md
docs/continuity/PF_1A_E2_B_IMPLEMENTATION_HANDOFF_2026-09-04.md
```

It changes no production code, no test, no migration or schema, no E1 behaviour, no E2-A semantic
behaviour (kernel, domain, ports, contract, evidence, lineage, material, scope or evaluators), and
none of C2's runtime corrections (F1-F4, or the autocommit-pool-contamination fix). Historical
proposal/definition-time material named in class A above is preserved and explicitly labelled as
historical; it is never erased or rewritten as though it never existed. The normative definition
itself (sections 2 onward) is unchanged by C4.

**PF-1A-E2-B remains NOT ACCEPTED. Criterion Z remains NOT MET.** The independent reviewer
evaluated evidence and documentation; it did not itself re-run any deterministic test. The next
gate is a FURTHER FRESH bounded independent re-review of this documentation-corrected candidate.

### 1.0E Correction C5 — current-summary closure

**HISTORICAL SNAPSHOT AS OF C5.** This section records the state, review verdict and next-gate
expectation exactly as they stood immediately after correction C5, before correction C6 through C7
existed. It is preserved as historical evidence; for present repository and review status, see the
document's CURRENT CONTROL STATE (section 1.0G).

**Status: documentation-only correction, applied after a further FRESH bounded independent
re-review of the C4-corrected candidate.** That re-review found **NO additional material code,
migration, persistence or production-composition defect**: findings F1-F4 (section 1.0A) and the
separately discovered autocommit-pool-contamination correction (acceptance record section 15.6)
remain SUBSTANTIVELY CLOSED, and the deterministic results in section 1.0B were supplied as
evidence only and were **not** re-run by the independent reviewer.

**Its verdict was nevertheless `CORRECTION_REQUIRED` (P2)**, with a single finding: several active/
current-tense summaries across this document, the acceptance record and the implementation handoff
still described the repository state as of C3 or as of C4 (for example "documentation reconciled
under C3", "Correction C2 (+documentation-only C3)...") rather than the actual current state,
which by that point already also included C4.

**Correction C5 changes documentation only.** It edits exactly the same three files C3 and C4
edited:

```text
docs/agent/pf-1a/PF_1A_E2_B_PERSISTED_PUBLISHED_AUTHORITY_STORE_AND_RUNTIME_WIRING.md   (this file)
docs/agent/acceptance/pf-1a-e2-b-persisted-published-authority-store-acceptance.md
docs/continuity/PF_1A_E2_B_IMPLEMENTATION_HANDOFF_2026-09-04.md
```

It changes no production code, no test, no migration or schema, no E1 behaviour, no E2-A semantic
behaviour (kernel, domain, ports, contract, evidence, lineage, material, scope or evaluators), and
none of C2's runtime corrections (F1-F4, or the autocommit-pool-contamination fix). It does not
reopen or restate C2, C3 or C4's own substantive content; it reconciles every remaining
active-tense summary across the three documents so each now reads the correction layer as
C2/C3/C4/C5 collectively — one still-uncommitted, still-unpushed 12-file working-tree layer
sitting on top of the committed-and-pushed-but-not-merged candidate `481a860`, not a thirteenth
file and not a separate Git layer. Historical C3-only and C4-only snapshots elsewhere in this
document (sections 1.0C and 1.0D above) are preserved and explicitly labelled as historical; they
are not rewritten.

**PF-1A-E2-B remains NOT ACCEPTED. Criterion Z remains NOT MET.** The independent reviewer
evaluated evidence and documentation; it did not itself re-run any deterministic test — the counts
in section 1.0B remain this package's own tool output, not something the reviewer executed. The
next gate is a FRESH bounded independent re-review of this C5-corrected candidate.

### 1.0F Correction C6 — secret-scan provenance reconciliation

**HISTORICAL SNAPSHOT AS OF C6.** This section records the state, review verdict and next-gate
expectation exactly as they stood immediately after correction C6, before correction C7 existed. It
is preserved as historical evidence; for present repository and review status, see the document's
CURRENT CONTROL STATE (section 1.0G).

**Status: documentation-only correction, applied after a fresh bounded independent re-review of
the C5-corrected candidate.** That re-review was PACKET-ONLY: deterministic tests were not rerun.
The full post-C5 effective candidate was re-examined; findings F1-F4 (section 1.0A) and the
separately discovered autocommit-pool-contamination correction (acceptance record section 15.6)
remain SUBSTANTIVELY CLOSED, and **no additional material runtime, migration, persistence,
composition, E2-A-semantic or E1-compatibility defect was found**. Whole-resolution snapshot
consistency across multiple provider calls remains, as already recorded in section 1.0A, outside
the claimed F1 boundary.

**Its verdict was nevertheless `CORRECTION_REQUIRED` (P2)**, with a single finding: the current
secret-scan evidence in this document (section 1.0B), the acceptance record (section 9.2) and the
implementation handoff (section 14.0) correctly reported "801 files scanned, no findings" but
incorrectly explained the change from the earlier 799-file count as "799 -> +2, the two files C2
added" or materially equivalent wording. That explanation is not supported by the established
current inventory: baseline -> HEAD is 19 changed files, HEAD -> working tree is exactly 12
MODIFIED files, and the baseline-to-working-tree union is 21 distinct files; C2, C3, C4 and C5 did
not add files to the working tree. **The reviewer did not dispute the current 801-file / no-findings
result itself — only the unsupported provenance explanation attached to it.**

**Correction C6 changes documentation only.** It edits exactly the same three files C3, C4 and C5
edited:

```text
docs/agent/pf-1a/PF_1A_E2_B_PERSISTED_PUBLISHED_AUTHORITY_STORE_AND_RUNTIME_WIRING.md   (this file)
docs/agent/acceptance/pf-1a-e2-b-persisted-published-authority-store-acceptance.md
docs/continuity/PF_1A_E2_B_IMPLEMENTATION_HANDOFF_2026-09-04.md
```

It removes the unsupported "799 -> +2, the two files C2 added" explanation everywhere it appeared
as a CURRENT statement, retaining "801 files scanned, no findings" unchanged. **It does NOT invent a
replacement causal explanation** for why the scan enumerated two more files than the earlier
799-file count; no repository evidence available to this correction establishes that cause, and
none is guessed at. It changes no production code, no test, no migration or schema, no E1
behaviour, no E2-A semantic behaviour (kernel, domain, ports, contract, evidence, lineage, material,
scope or evaluators), and none of C2's runtime corrections (F1-F4, or the autocommit-pool-
contamination fix). It does not reopen or restate C2, C3, C4 or C5's own substantive content. The
current correction layer remains **C2/C3/C4/C5/C6 collectively** — one still-uncommitted,
still-unpushed 12-file working-tree layer sitting on top of the committed-and-pushed-but-not-merged
candidate `481a860`, not a thirteenth file and not a separate Git layer. Historical C3-only,
C4-only and C5-only snapshots elsewhere in this document (sections 1.0C, 1.0D and 1.0E above) are
preserved and explicitly labelled as historical; they are not rewritten.

**PF-1A-E2-B remains NOT ACCEPTED. Criterion Z remains NOT MET.** The independent reviewer
evaluated evidence and documentation only; it did not itself re-run any deterministic test — the
counts in section 1.0B remain this package's own tool output, not something the reviewer executed.
The next gate is a FRESH bounded independent re-review of this C6-corrected candidate, not yet
performed.

### 1.0G CURRENT CONTROL STATE — authoritative present-state summary (established by correction C7;
updated by C8 and C9)

**This is the single authoritative summary of present repository and review status for this
document.** Every other section of this document that touches repository, correction-layer or
review status is either normative package definition, or a labelled HISTORICAL SNAPSHOT of an
earlier point in this same correction sequence (sections 1.0, 1.0B, 1.0C, 1.0D, 1.0E, 1.0F, 1.0H,
1.0I), and each points back here rather than restating or duplicating this summary. The acceptance
record and the implementation handoff each carry their own CURRENT CONTROL STATE block, kept in
agreement with this one.

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

  No causal explanation for the 799 -> 801 tracked-secret-scan file-count change is asserted.
  These figures are unchanged by C10, which is documentation-only and reran no deterministic
  test. No deterministic suite was rerun for C10.

Review state (chronological):
  - initial independent review of 481a860   -> CORRECTION_REQUIRED, findings F1-F4
  - C2                                          substantively corrected F1-F4, plus a separately
                                                 discovered test-only autocommit-pool-contamination
                                                 leak
  - post-C2 independent review               -> documentation-only P2 finding -> C3
  - post-C3 independent review               -> residual documentation-only P2 finding -> C4
  - post-C4 independent review               -> stale current-summary P2 finding -> C5
  - post-C5 independent review               -> secret-scan provenance P2 finding -> C6
  - post-C6 independent review               -> stale duplicated-current-summary P2 finding -> C7
  - post-C7 independent review               -> residual noncanonical mutable-summary P2 finding
                                                 -> C8
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
                                                 (section 1.0J)
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
                                                 documentation only (section 1.0K, this
                                                 correction)
  - fresh post-C10 independent bounded review   NOT YET PERFORMED

Current status:
  PF-1A-E2-B: NOT ACCEPTED.
  Criterion Z: NOT MET.

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

For any other section of this document, the acceptance record, or the implementation handoff that
discusses present repository or review status: this block is authoritative. A historical snapshot
section may still describe what was true at an earlier correction point, but its own supersession
pointer references this block by name (CURRENT CONTROL STATE, section 1.0G) rather than a specific
later-numbered correction, so that a future correction does not require revisiting every historical
pointer again.

### 1.0H Correction C7 — canonical current-state normalization

**HISTORICAL SNAPSHOT AS OF C7.** This section records the state, review verdict and next-gate
expectation exactly as they stood immediately after correction C7, before corrections C8 and C9
existed. It is preserved as historical evidence; its endpoint identities and "not yet performed"
next gate describe that earlier point and are NOT updated to current values. For present
repository and review status, see the CURRENT CONTROL STATE (section 1.0G).

**Status: documentation-only correction, applied after a fresh bounded independent re-review of
the C6-corrected candidate.** That re-review found the C6 secret-scan provenance defect itself
CLOSED — current evidence correctly states "801 files scanned, no findings" with no invented causal
explanation — and **no additional material runtime, migration, persistence, production-composition,
E2-A-semantic or E1-compatibility defect**. Findings F1-F4 (section 1.0A) and the separately
discovered autocommit-pool-contamination correction (acceptance record section 15.6) remain
SUBSTANTIVELY CLOSED. The reviewer did not rerun deterministic tests.

**Its verdict was nevertheless `CORRECTION_REQUIRED` (P2)**, with a single finding: this document,
the acceptance record and the implementation handoff each maintained more than one section that
independently claimed to describe CURRENT/active repository or review status, and several of those
sections stopped at C5 or C6 rather than reflecting the true current state — a structural
documentation defect in which each new correction made other supposedly-current summaries stale.

**Correction C7 changes documentation only.** It edits exactly the same three files C3, C4, C5 and
C6 edited:

```text
docs/agent/pf-1a/PF_1A_E2_B_PERSISTED_PUBLISHED_AUTHORITY_STORE_AND_RUNTIME_WIRING.md   (this file)
docs/agent/acceptance/pf-1a-e2-b-persisted-published-authority-store-acceptance.md
docs/continuity/PF_1A_E2_B_IMPLEMENTATION_HANDOFF_2026-09-04.md
```

C7 establishes exactly one authoritative CURRENT CONTROL STATE block per document (section 1.0G
here). Sections that previously carried their own independent "current" framing were converted to
one of: a labelled HISTORICAL SNAPSHOT of an earlier correction point (1.0B, 1.0C, 1.0D, 1.0E,
1.0F), unchanged normative package-definition text with its present-state claim replaced by a
pointer to 1.0G (section 1, section 15), or a short pointer to 1.0G with no restated chain. Brittle
numbered supersession pointers ("superseded by C5", "see C6 for current state") were replaced with
a stable pointer to this document's CURRENT CONTROL STATE, so a future correction does not require
revisiting every historical pointer again.

It changes no production code, no test, no migration or schema, no E1 behaviour, no E2-A semantic
behaviour, and none of C2's runtime corrections (F1-F4, or the autocommit-pool-contamination fix).
It does not reopen or restate C2, C3, C4, C5 or C6's own substantive content; their historical
records (sections 1.0A-1.0F) are preserved exactly as they described the state at each point, with
only their own forward-pointing cross-reference future-proofed as described above. The current
correction layer remains **C2/C3/C4/C5/C6/C7 collectively** — one still-uncommitted, still-unpushed
12-file working-tree layer sitting on top of the committed-and-pushed-but-not-merged candidate
`481a860`, not a thirteenth file and not a separate Git layer. C7 itself edits only the same three
documentation files already inside that 12-file set.

**PF-1A-E2-B remains NOT ACCEPTED. Criterion Z remains NOT MET.** The independent reviewer
evaluated evidence and documentation only; it did not itself re-run any deterministic test — the
counts in section 1.0G remain this package's own tool output, not something a reviewer executed.
The next gate is a FRESH bounded independent re-review of this C7-corrected candidate, not yet
performed.

### 1.0I Correction C8 — noncanonical mutable-summary elimination

**HISTORICAL SNAPSHOT AS OF C8.** This section records the state, review verdict and next-gate
expectation exactly as they stood immediately after correction C8, before correction C9 existed.
It is preserved as historical evidence; its endpoint identities and "not yet performed" next gate
describe that earlier point and are NOT updated to current values. For present repository and
review status, see the CURRENT CONTROL STATE (section 1.0G).

**Status: documentation-only correction, applied after a fresh bounded independent re-review of
the C7-corrected candidate.** That re-review found **no additional material runtime, migration,
persistence, production-composition, E2-A-semantic or E1-compatibility defect**. Findings F1-F4
(section 1.0A) and the separately discovered autocommit-pool-contamination correction (acceptance
record section 15.6) remain SUBSTANTIVELY CLOSED. The reviewer did not rerun deterministic tests.

**Its verdict was nevertheless `CORRECTION_REQUIRED` (P2)**, with a single finding: this document,
the acceptance record and the implementation handoff still maintained noncanonical mutable
numbered-correction summaries outside the canonical CURRENT CONTROL STATE block, so the same
staleness mechanism C7 was meant to close could recur. Specifically: this document's own section 1
banner still pointed to "section 1.0 and corrections C2-C6" — already stale because C7 existed —
and section 1.0's own heading enumerated only C2-C6; the implementation handoff's section 1
independently restated present candidate status and the full C2/C3/C4/C5/C6/C7 correction-layer
chain instead of pointing to CURRENT CONTROL STATE, and its section 3 repeatedly described itself
as "kept current through" specific correction numbers, maintaining a second mutable present-state
chronology outside the canonical block.

**Correction C8 changes documentation only.** It edits exactly the same three files C3, C4, C5, C6
and C7 edited:

```text
docs/agent/pf-1a/PF_1A_E2_B_PERSISTED_PUBLISHED_AUTHORITY_STORE_AND_RUNTIME_WIRING.md   (this file)
docs/agent/acceptance/pf-1a-e2-b-persisted-published-authority-store-acceptance.md
docs/continuity/PF_1A_E2_B_IMPLEMENTATION_HANDOFF_2026-09-04.md
```

C8 removed the remaining noncanonical present-state pointers the post-C7 review identified: this
document's section 1 banner and section 1.0 heading no longer enumerate specific correction numbers
as a present-state supersession chain; the implementation handoff's section 1 now defers present
repository/review status to its own CURRENT CONTROL STATE block instead of restating it; and the
implementation handoff's section 3 is now explicitly labelled inventory evidence for the 19/12/21
file relationship rather than a second, independently mutating current-review chronology. The
canonical CURRENT CONTROL STATE block (section 1.0G here) remains the sole mutable operational-state
source per document. Acceptance criterion Z is the one deliberate exception, because an
acceptance-criteria table is expected to show its own history; it is not treated as a competing
present-state summary.

It changes no production code, no test, no migration or schema, no E1 behaviour, no E2-A semantic
behaviour, and none of C2's runtime corrections (F1-F4, or the autocommit-pool-contamination fix).
It does not reopen or restate C2, C3, C4, C5, C6 or C7's own substantive content; their historical
records (sections 1.0A-1.0F, 1.0H) are preserved exactly as they described the state at each point.
The current correction layer remains **C2/C3/C4/C5/C6/C7/C8 collectively** — one still-uncommitted,
still-unpushed 12-file working-tree layer sitting on top of the committed-and-pushed-but-not-merged
candidate `481a860`, not a thirteenth file and not a separate Git layer. C8 itself edits only the
same three documentation files already inside that 12-file set.

**PF-1A-E2-B remains NOT ACCEPTED. Criterion Z remains NOT MET.** The independent reviewer
evaluated evidence and documentation only; it did not itself re-run any deterministic test — the
counts in section 1.0G remain this package's own tool output, not something a reviewer executed.
The next gate is a FRESH bounded independent re-review of this C8-corrected candidate, not yet
performed.

### 1.0J Correction C9 — review-endpoint reconciliation after the main sync

**HISTORICAL SNAPSHOT AS OF C9.** This section records the state, review verdict and next-gate
expectation exactly as they stood immediately after correction C9. It PREDATES the post-C9
independent review and correction C10, and its next-gate statement is therefore the one that was
true then, not now. It is preserved as historical evidence and is NOT updated to current values.
For present repository, lifecycle and review status, see the CURRENT CONTROL STATE (section 1.0G).

**Status: documentation-only correction, applied after a fresh bounded independent re-review of
the C8-corrected candidate and a project-owner decision (D1).** That re-review found **no new
material functional, security, persistence, migration, parity, E2-A-semantic or E1-compatibility
defect**. Findings F1-F4 (section 1.0A) and the separately discovered test-only
autocommit-pool-contamination correction (acceptance record section 15.6) all remain **CLOSED**.
The reviewer did not rerun deterministic tests, and C9 reran none either.

**What changed underneath the package.** Between the post-C8 review and this correction, `main`
advanced and the feature branch was synced with it — PR #18 (`f32e989`), PR #19 (`5d737c0`, which
integrated ADR-035), then merge `6de6fb0` "Sync PF-1A-E2-B branch with current main". The sync did
not touch this package's own work (`git diff --name-only 481a860 6de6fb0` reports only eight
main-side files), but it **moved the review base**, and the canonical CURRENT CONTROL STATE blocks
did not follow: they still named `22a4b28` as "protected baseline" and `481a860` as the
"committed+pushed candidate", and bound the 19/12/21 inventory to those two commits. Four distinct
endpoints existed and only two were recorded, so a reader could not tell which commit the package
is now reviewed against, nor that the pushed origin ref had become stale. That is a
documentation/current-state defect only; no code, test, migration, contract, authorization
behaviour or deterministic result was affected by it or by its correction.

**D1 — the project-owner decision.** The branch was synced with current main as above, and a
documentation-only correction C9 was directed, scoped to the three package documents and
additionally authorizing the narrow C7/C8 historical labelling below.

**Correction C9 changes documentation only.** It edits exactly the same three files C3 through C8
edited:

```text
docs/agent/pf-1a/PF_1A_E2_B_PERSISTED_PUBLISHED_AUTHORITY_STORE_AND_RUNTIME_WIRING.md   (this file)
docs/agent/acceptance/pf-1a-e2-b-persisted-published-authority-store-acceptance.md
docs/continuity/PF_1A_E2_B_IMPLEMENTATION_HANDOFF_2026-09-04.md
```

```text
1. All three canonical CURRENT CONTROL STATE blocks now distinguish FOUR endpoints -
   historical inception baseline 22a4b28, current main / review base 5d737c0, current local
   feature HEAD 6de6fb0, and current origin feature ref 481a860 - and state explicitly that
   481a860 is stale relative to the local HEAD because it predates the sync.
2. The 19/12/21 inventory is bound to the correct endpoints. The COUNTS are unchanged; only
   their endpoints are corrected. The same 19 paths are also what 22a4b28 -> 481a860 reports,
   which is why the counts stayed arithmetically correct while their labels went stale.
3. The implementation handoff's section 3 endpoint labels are corrected while its factual file
   inventory is preserved.
4. The correction-layer composition is updated to C2/C3/C4/C5/C6/C7/C8/C9.
5. The post-C8 review -> D1 -> C9 chronology is appended to each canonical block and to
   acceptance criterion Z.
6. Criterion Z is updated through C9 and remains NOT MET.
7. Correction records C7 (section 1.0H) and C8 (section 1.0I) - which still carried then-current
   statements such as a next gate "not yet performed" - now carry the same concise HISTORICAL
   SNAPSHOT label already used for C3 through C6. Their historical facts and endpoint values are
   preserved exactly and are deliberately NOT updated to current values.
8. The next gate is stated as a fresh post-C9 independent bounded review.
```

It changes no production code, no test, no migration or schema, no E1 behaviour, no E2-A semantic
behaviour, and none of C2's runtime corrections (F1-F4, or the autocommit-pool-contamination fix).
It does not reopen or restate the substantive content of C2 through C8; their historical records
(sections 1.0A-1.0F, 1.0H, 1.0I) are preserved as they described the state at each point, with
1.0H and 1.0I gaining only the historical label described above. The current correction layer
remains **C2/C3/C4/C5/C6/C7/C8/C9 collectively** — one still-uncommitted, still-unpushed 12-file
working-tree layer, not a thirteenth file and not a separate Git layer. C9 itself edits only the
same three documentation files already inside that 12-file set.

**PF-1A-E2-B remains NOT ACCEPTED. Criterion Z remains NOT MET.** The next gate is a FRESH bounded
independent re-review of this C9-corrected candidate, not yet performed. For the authoritative
present repository and review status, see the CURRENT CONTROL STATE (section 1.0G).

### 1.0K Correction C10 — pre-ADR-035 in-flight lifecycle reconciliation

**Status: documentation-only correction, applied after the fresh post-C9 bounded independent
review.** That review returned **`CORRECTION_REQUIRED`** with a single material finding, **D2**.

**What the post-C9 review found.** It independently confirmed **CLOSED**: F1, F2, F3, F4, the
separately discovered test-only autocommit-pool-contamination leak, and **D1** (post-sync
repository identity, corrected by C9). It identified **no new material runtime, persistence,
concurrency, migration, production-composition, security, parity, PF-1A-E2-A-semantic,
PF-1A-E1-compatibility or main-synchronization defect**.

**D2 — the sole material finding.** Each governing document's ACTIVE canonical CURRENT CONTROL
STATE said, in substance, that "ADR-035 now governs this package's two-phase
(FUNCTIONAL_CORRECTION -> FINAL_ACCEPTANCE) review lifecycle". That is incorrect for this
already-running review sequence: PF-1A-E2-B entered independent review and correction **before**
ADR-035 was integrated, and the wording retroactively applied a lifecycle the package has never
been run under.

**The transitional rule C10 establishes.**

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

**Correction C10 changes documentation only.** It edits exactly the same three files C3 through C9
edited:

```text
docs/agent/pf-1a/PF_1A_E2_B_PERSISTED_PUBLISHED_AUTHORITY_STORE_AND_RUNTIME_WIRING.md   (this file)
docs/agent/acceptance/pf-1a-e2-b-persisted-published-authority-store-acceptance.md
docs/continuity/PF_1A_E2_B_IMPLEMENTATION_HANDOFF_2026-09-04.md
```

```text
1. The incorrect active ADR-035 lifecycle claim is replaced, in all three canonical CURRENT
   CONTROL STATE blocks, by the transitional rule above. All three now materially agree.
2. The correction-layer composition is updated to C2/C3/C4/C5/C6/C7/C8/C9/C10.
3. The post-C9 review -> D2 -> C10 chronology is appended to each canonical block and to
   acceptance criterion Z.
4. Criterion Z is updated through C10 and remains NOT MET.
5. Correction record C9 (section 1.0J) - which still carried its then-current next-gate statement
   - now carries the same concise HISTORICAL SNAPSHOT label already used for C3 through C8. Its
   historical facts, endpoint values and original next-gate wording are preserved exactly and are
   deliberately NOT updated to current values.
6. The sole next gate is stated as a fresh post-C10 independent bounded review.
```

**C10 does not reopen D1**, whose closure by C9 the post-C9 review independently confirmed, and it
does not reopen any functional finding. It changes no production code, no test, no migration or
schema, no CI, no script, no configuration, no ADR-035 document, no E1 behaviour, no E2-A semantic
behaviour, and none of C2's runtime corrections (F1-F4, or the autocommit-pool-contamination fix).
The repository endpoints and the 19/12/21 inventory established by C9 are preserved unchanged. The
historical records of C2 through C9 (sections 1.0A-1.0F, 1.0H, 1.0I, 1.0J) are preserved as they
described the state at each point, with 1.0J gaining only the historical label described above. The
current correction layer remains **C2/C3/C4/C5/C6/C7/C8/C9/C10 collectively** — one
still-uncommitted, still-unpushed 12-file working-tree layer, not a thirteenth file and not a
separate Git layer. C10 itself edits only the same three documentation files already inside that
12-file set.

**No deterministic suite was rerun for C10.** The evidence figures in the CURRENT CONTROL STATE
(section 1.0G) are unchanged, including the tracked-secret scan's "801 files scanned, no findings",
for which no causal provenance is asserted.

**PF-1A-E2-B remains NOT ACCEPTED. Criterion Z remains NOT MET.** The next gate is a FRESH bounded
independent post-C10 review, not yet performed. For the authoritative present repository, lifecycle
and review status, see the CURRENT CONTROL STATE (section 1.0G).

### 1.1 Correction record

Three independent reviews returned `CORRECTION_REQUIRED` on this definition pair, and a fourth
(final) re-review of the predecessor package returned `CORRECTION_REQUIRED` with F-10 recorded as
`PARTIALLY_RESOLVED`. Every finding was accepted as a **definition defect**; none required a new PBL
business decision. This document is the reconciled result of all of them, not an addendum, and does
not depend on any correction brief to be understood.

**Cycle 1 — six findings.**

```text
F-02  the authority configuration port prefiltered to "effective" rows, so a SQL WHERE clause could
      hide a lineage defect the kernel is required to detect. E2-B now supplies COMPLETE lineage
      material plus identity-only candidate discovery.
      Corrected in sections 5.2, 5.6, 9, 10, 13, 15 - extended by F-07 below.
F-04  this document previously instructed runtime wiring to compose the resolver with synthetic
      actor-person and HR providers, and then claimed E2-B hands consumers a working resolution
      capability. Corrected in sections 5.3, 6, 9, 10, 13, 16.                        RESOLVED
F-01  active_flag is an immutable published value, not temporal effectiveness. Persistence
      consequences in sections 5.1, 5.6, 9.                                            RESOLVED
F-05  a valid effective-time gap is valid history. The schema must not forbid it. Section 5.6 -
      extended by F-09 below.
F-03  scope composition and path aggregation are E2-A semantics; the parity corpus must cover them.
      Section 9 - extended by F-08 below.
F-06  denial and failure evidence are first-class and must survive persistence unchanged.
      Sections 9, 10, 15.                                                              RESOLVED
```

**Cycle 2 — three findings, all now resolved.**

```text
F-07  discovery still excluded versions carrying a retraction assertion, and this document
      explicitly directed a SQL EXISTS that did so - meaning a malformed retraction could remove
      the only requested-code-bearing or reference-bearing version in the WHERE clause, hiding its
      own defect. Discovery is now RAW. The recorded-time (published_at / retracted_at) versus
      business-effective-time boundary is also now defined in E2-A section 11.8 and constrains what
      the store may do with those columns.
      Corrected in sections 5.2, 5.6, 9, 10.D, 13, 15.

F-08  E2-A's result-level fail-closed reason selection was not total within one stage. E2-A section
      15.5 now defines the canonical defect sort key. E2-B's obligation is parity: the PostgreSQL
      path must produce the identical result_level_reason and identical evidence ordering as the
      reference provider, including under shuffled physical row order and concurrency.
      Corrected in sections 9, 10.N, 13, 15.

F-09  E2-A's closure formula normalized explicit overlaps away. E2-A section 11.4 now distinguishes
      successor closure, valid gaps, explicit adjacency and CONTRADICTORY EXPLICIT OVERLAP. E2-B
      must STORE all of those shapes without "helpfully" normalizing any of them, and must prove
      the kernel classifies each identically to the reference provider.
      Corrected in sections 5.6, 9, 10.F, 13, 15.
```

**Cycle 3 — one finding, partially resolved at the time; closed by the F-10 closure package below.**

```text
F-10  this document's VERIFICATION contract was internally impossible. Section 5.6 mandated
      structural constraints that reject several malformed shapes at write time - unique
      (object_id, object_version), the assignment person_id XOR position_id CHECK, and
      declared_effective_to > effective_from - while section 9 and acceptance criterion 10.N
      simultaneously required those SAME shapes to be seeded in PostgreSQL and agreed between the
      reference and PostgreSQL providers: "end <= start" appeared in the 10.N parity list, DEFECT
      VISIBILITY asked for "a duplicate (object_id, object_version) surfaced through the provider",
      and the parity corpus demanded "each fail-closed reason code" including
      ASSIGNMENT_TARGET_INVALID, which the XOR CHECK makes unreachable. Section 9's own partial
      carve-out for end <= start contradicted 10.N and 13.16 rather than reconciling them. No
      conforming implementation could satisfy both sides.
      Cycle 3 introduced two verification lanes provider-neutrally in E2-A section 9.7, with a
      per-fixture assignment for this store in the new section 5.7 here, applied throughout
      sections 5.6, 9, 10.E/F/N/N3, 13 and 15. That removed the original impossible parity
      obligations but left a residual gap, recorded immediately below.
```

**F-10 definition closure — a NEW human-authorized work package, not a fourth correction cycle.**

The predecessor package's final independent re-review recorded F-10 as `PARTIALLY_RESOLVED`. The
residual gap was in **this** document's section 5.7: four structural shapes were assigned to "Lane B"
and pointed at E2-A section 18 for their supposed direct-kernel counterpart, where no such fixture
or expected reason existed — and for two of them no such fixture could exist at all.

```text
NULL effective_from                                  no E2-A fixture, no expected reason defined
NULL active_flag                                     no E2-A fixture, no expected reason defined
version row lacking its stable-identity parent       NOT REPRESENTABLE at the E2-A boundary:
                                                     object_id is carried on the LineageMaterial
                                                     CONTAINER (E2-A 9.3.2), not per version
retraction lacking its object stable-identity parent NOT REPRESENTABLE, for the same reason
```

The closure splits the old "Lane B" into **two genuinely different things**, giving a total
three-class taxonomy (E2-A section 9.7):

```text
A    persistable semantic contradiction                          -> FULL PostgreSQL parity owed
B1   DB-rejected structure WITH a provider-neutral counterpart   -> DB rejection test HERE + a
                                                                    named, executed E2-A test at a
                                                                    NAMED boundary (DTO/port
                                                                    well-formedness, or kernel),
                                                                    with a NORMATIVE expected
                                                                    reason; excluded from parity
B2   persistence-only structural invariant, NO counterpart       -> DB rejection test HERE only;
                                                                    excluded from parity AND from
                                                                    every E2-A fixture manifest;
                                                                    written rationale mandatory
```

`NULL effective_from` and `NULL active_flag` became **B1 at the DTO/port well-formedness boundary**
(E2-A 9.3.3/9.3.4), failing closed as `AUTHORITY_CONFIGURATION_UNAVAILABLE` — not invented reason
codes, and explicitly not described as kernel fixtures. The three missing-stable-identity-ROW
foreign keys became **B2**, because E2-A 9.3.2 now states that an object identity carrying no
material returns COMPLETE material with an empty `versions[]`, so a "missing stable identity row"
decodes to the already-class-A `AUTHORITY_REFERENCE_DANGLING` state rather than to a distinct one.

Section 5.7 was rewritten as a **total, exclusive, seven-column manifest** covering every named
negative fixture. Sections 5.6, 9, 10.E/F/J/K/N/N3, 13.16a, 15 and 16 were reconciled to it, and no
contradictory two-lane language survives.

The closure changed no E2-A semantic rule and weakened no fail-closed behaviour. It settled only
which test proves which rule when PostgreSQL is structurally incapable of holding the malformed
shape — and, for three constraints, recorded honestly that there is no semantic rule to prove
because the provider-neutral contract does not model what the constraint protects.

**F-10 FINAL definition closure — a further NEW human-authorized work package.**

The re-review of the manifest above returned `CORRECTION_REQUIRED` with F-10 still
`PARTIALLY_RESOLVED`, naming three residual blocking defects. All three were in **this** section
5.7, and all three were defects in the manifest's **totality and executability** rather than in any
semantic rule:

```text
F-10.1  B1-09 grouped TWO malformed shapes under one ID - "absent publication_reference_type or
        publication_reference_id" - and promised a named, executed E2-A test for the pair. E2-A
        section 18 named the absent _id shape but not the absent _type shape, so one B1 shape had
        no direct E2-A coverage at all.
        CLOSED. The provenance B1 entries are split ONE SHAPE PER ID: B1-08 -> B1-08a / B1-08b and
        B1-09 -> B1-09a / B1-09b. B1-09a (an ABSENT publication_reference_type) now has a named,
        mandatory, executing pure-kernel E2-A fixture, PROVENANCE-ABSENT-TYPE, with a normative
        expected result. E2-A 9.3.4, 9.7, 11.6, 11.7, 18, 19.L5, 22.17f, 24 and 25 carry it.

F-10.2  A-03 deferred its class, its "PG may store" answer and its expected reason code to
        implementation time through a "RESOLUTION PROCEDURE". A manifest that defers a required
        classification is not total, so this table was not the binding artefact it claimed to be.
        CLOSED, decided as the former branch (b). E2-A 11.4a now PROVES, from the closure and
        interval rules E2-A already states, that at most one version of a current asserted lineage
        can be EFFECTIVE at any instant once the duplicate-start, nonsensical-interval and
        explicit-overlap conditions have passed. The residual state is therefore unreachable on
        EVERY provider, not merely unstorable here. A-03 is REMOVED from this manifest, from the
        parity corpus and from the fixture counts; its ID is retired; and the invariant it was
        trying to exercise is carried by pure-kernel self-check NS-K-01 in the new section 5.7A.
        AUTHORITY_VERSION_AMBIGUOUS moves onto the justified parity-exclusion list as
        KERNEL-INTERNAL, with its normative reason-code assignment stated in E2-A 11.4a.

F-10.3  Class A is DEFINED as a persistable semantic contradiction whose raw rows PostgreSQL stores
        and returns, and every class A record carried a mandatory INSERT/read-back obligation. Yet
        A-16 (an induced read failure), A-18 (actor/HR provider states), A-19 and A-20 (request-side
        inputs) recorded their own PostgreSQL storability as "N/A" while keeping the class A label.
        Their subject is not authority-store data, so class A's defining test was not executable for
        them and they belonged to no class under the document's own definitions.
        CLOSED. E2-A 9.7.0 now scopes the taxonomy normatively - A/B1/B2 classifies ONLY negative
        fixtures whose subject is the published authority-store / read-repository data contract -
        and this document gains section 5.7A, NON-STORE RESOLVER / PROVIDER CONFORMANCE SCENARIOS,
        a normative table with its own seven columns. A-16, A-18, A-19 and A-20 were moved there,
        expanded into individually named scenarios, and their IDs retired. The re-check of the
        REMAINING A/B1/B2 entries against the same entry test was recorded at the time as finding
        no further failure. That statement was wrong about one entry, A-12, and is corrected by the
        direct correction recorded immediately below; it is preserved here as the accurate record of
        what was claimed then.
```

Retired IDs are **never reused**: `A-03`, `A-16`, `A-18`, `A-19`, `A-20` — joined by `A-12` in the
direct correction below. Each is recorded in section 5.7 with the scenario that now carries its
obligation, so an older citation resolves rather than dangles.

Sections 5.6, 5.7, the new 5.7A, 9, 10.E/N/N3/N4, 13.16a/16b/16c and 15 were reconciled. No E2-A
semantic rule changed, no fail-closed behaviour weakened, no reason code invented or removed, and
no genuinely applicable parity obligation dropped.

**Owner-authorized direct correction — F-10.3a and F-10.3b.**

The independent review of the F-10 FINAL definition closure accepted F-10.1 and F-10.2 as
`RESOLVED` and left two material findings against F-10.3 itself. Both are closed here under a
one-time, human-authorized direct correction, scoped to these two definition documents. No semantic
rule, fail-closed behaviour, reason code, contract, migration plan or exclusion was changed by it.

```text
F-10.3a  A-12 and the closure-parity text violated the taxonomy's own declared universe.
         A-12 ("the requested authority_code has no grant-eligible-by-lineage version at as_of,
         including an as_of inside a VALID GAP") was labelled a class A PERSISTABLE SEMANTIC
         CONTRADICTION. Nothing about it is malformed: E2-A 11.5 states explicitly that a temporal
         gap is VALID lineage, every row involved is valid, and what is under test is the RESOLVER's
         deliberate asymmetry at an as_of - not a contradictory stored shape. It therefore failed
         the 5.7 entry test, which admits only MALFORMED or CONTRADICTORY published authority-store
         state. Separately, section 9 and criterion 10.N described VALID closure shapes - null-end
         successor closure, explicit adjacency, the valid gap, reactivation after it - as "CLASS A",
         which attaches a NEGATIVE-FIXTURE label to states that are not defects at all.
         CLOSED. A-12 is REMOVED from A/B1/B2 and its ID retired; its resolver/as_of obligation,
         including AUTHORITY_CODE_NOT_CONFIGURED and its full PostgreSQL parity, is carried
         unchanged by NON-STORE scenario NS-RS-01 (5.7A). Valid stored shapes are recognised as a
         THIRD, separately named group - VALID-SHAPE PARITY SCENARIOS, V-01 to V-12 in 5.7 - which
         carries no class label, is not a negative fixture, and remains fully parity-owed. Only
         genuinely malformed PostgreSQL-storable contradictions (explicit overlap A-01, duplicate
         temporal start A-02, and the rest) remain class A.

F-10.3b  The non-store table was not TOTAL over the orchestration, ordering and evidence scenarios
         the current normative text already makes mandatory. Twenty scenarios covered the actor,
         HR, request, port and kernel-invariant seams, but obligations E2-A 18 and section 9 state
         as mandatory - the server-controlled live as_of and the single-clock rule, the prohibition
         on a caller-selected as_of / recorded-time cutoff / historical resolver as a live
         authorization path, the client-supplied person_id trust boundary, synthetic-provider
         production unreachability, the provider-supplies-facts-not-judgements conformance rule,
         multiple legitimate qualifying paths, relevant-corrupt-not-masked-by-a-valid-path,
         result-level reason selection, the total defect ORDER cases, and the complete /
         nonqualifying / partial evidence and evidence-ordering cases - carried no scenario ID and
         appeared in neither table.
         CLOSED. 5.7A now carries forty-six scenarios across ten seam groups, each with a stable ID,
         a named seam, its input/condition, BOTH store-participation answers, an executable test
         obligation, an expected outcome/status/reason/evidence and an explicit parity statement.
         The two store-participation answers are now separate columns, because conflating them is
         what let a scenario that merely READS valid PostgreSQL rows be mistaken for one whose
         malformed SUBJECT is stored state.
```

Final counts after this direct correction: **14 class A + 12 class B1 + 3 class B2 = 29
authority-store negative fixtures**, plus **12 valid-shape parity scenarios** (V-01 to V-12, 5.7)
and **46 non-store scenarios** (5.7A). Sections 5.7, 5.7A, 9, 10.E/N/N3/N4, 13.16c, 15 and 16 were
reconciled to them.

**Owner-authorized direct correction — F-10.3-DC-01 and F-10.3-DC-02.**

The independent review of the correction immediately above returned two further blocking findings
against the same F-10.3 work. Both are closed here under a second one-time, human-authorized direct
correction scoped to these two definition documents. Neither creates a business decision, invents or
removes a reason code, changes a class or a count, or alters any settled F-10.1, F-10.2, F-10.3,
F-10.3a or F-10.3b outcome.

```text
F-10.3-DC-01  A UNIT/CURRENCY/BASIS MISMATCH HAD TWO CONTRADICTORY NORMATIVE OUTCOMES.
              Section 5.7's VALID-SHAPE scenario V-12 listed "unit/currency mismatch" among the
              shapes producing an ordinary path-level EVALUATOR_CONDITION_NOT_SATISFIED, while E2-A
              13 and 18 require exactly that mismatch to FAIL CLOSED with EVALUATOR_FACTS_INVALID,
              which E2-A 14.3 lists as DENY + FAIL_CLOSED. NS-RQ-02 meanwhile covered only the
              ABSENT and WRONG-TYPED request facts, so the mismatch had no correct home.
              CLOSED. The mismatch is REMOVED from V-12, which now covers only genuine valid-shape
              non-satisfaction and states its input precondition explicitly - facts present,
              correctly typed AND unit/currency/basis-COMPATIBLE. The mismatch is carried by the
              EXISTING non-store scenario NS-RQ-02, EXTENDED rather than given a new ID, so no count
              changes: PG-DATA = YES (a VALID stored evaluator and payload must be read to reach
              S9), SUBJ = NO (the malformed input is the request, not stored state), PARITY = YES,
              outcome DENY, resolution status FAIL_CLOSED, reason EVALUATOR_FACTS_INVALID at stage
              S9, with ordinary E2-A 16.4 deterministic failure evidence. Sections 5.7, 5.7A and 9
              are reconciled; no statement anywhere now treats the incompatibility as ordinary
              non-satisfaction.

F-10.3-DC-02  "SUBJ = NO" WAS BEING READ AS "NO MALFORMED ROW MAY EXIST IN THE FIXTURE".
              NS-PR-03, NS-AG-03, NS-AG-04 and NS-DO-01..05 are DEFINED to compose
              already-classified class A malformed authority-store rows as ingredients - and
              NS-DO-01..05 must be built from class A defect shapes, because B1 and B2 shapes cannot
              be seeded here at all. Yet section 9 stated flatly that "NO MALFORMED ROW IS SEEDED to
              produce any of these", 5.7 spoke only of a scenario that reads VALID rows, and
              NS-PR-03's own rationale said no malformed row is stored or read back. Both could not
              be true, and as written the prescribed tests were impossible to author.
              CLOSED. PG-DATA participation and SUBJ classification are stated as two INDEPENDENT
              DIMENSIONS, neither inferable from the other. SUBJ = NO means the malformed or
              negative condition UNDER TEST is not authority-store state; it does not mean every
              participating row is valid. Already-classified class A malformed rows may participate
              as CONTROLLED INGREDIENTS where a scenario's defined semantics require them, keeping
              their own class and their own section 5.7 obligations and reclassifying nothing. Four
              prohibitions are stated explicitly in 5.7A and section 9: the ingredient is never the
              scenario's SUBJECT; no new malformed persisted shape may be introduced without an
              A/B1/B2 classification; the non-store taxonomy is never an escape from the 5.7 fixture
              manifest; and the ingredient is never suppressed or normalized against the existing
              raw-discovery and fail-closed rules. The A/B1/B2 fixture obligations are unchanged.
```

Counts are unchanged by this correction: **14 class A + 12 class B1 + 3 class B2 = 29**
authority-store negative fixtures, **12** valid-shape parity scenarios (V-01 to V-12) and **46**
non-store scenarios, thirty-eight of them parity-YES. Sections 5.7, 5.7A and 9 were reconciled; no
reason code, class, parity obligation or expected outcome changed beyond the single contradiction
each finding names.

## 2. Objective

Persist the already-accepted PF-1A-E2-A domain model in PostgreSQL, and supply a database-backed,
**read-only** authority configuration provider that feeds the **unchanged** E2-A kernel with
complete, faithful lineage facts — so that business authority resolution can answer from durable
published configuration rather than only from in-memory reference fixtures.

E2-B changes *where the published authority configuration facts come from*. It changes nothing about
*what resolution means*. If the kernel needs to change to accommodate persistence, that is evidence
the E2-A boundary was drawn wrongly, and it must be raised as a reconciliation finding rather than
absorbed silently.

**E2-B does not deliver a production-callable business-authority resolver.** Business authority
resolution additionally requires an authoritative actor→canonical-person provider and an
authoritative canonical HR/organisation provider. Neither exists at E2-B, and supplying either is a
later authorized package. Section 5.3 defines the production dependency seam and its mandatory
refuse-or-fail-closed behaviour; section 16 states the handoff in those terms.

## 3. Authoritative inputs

```text
docs/agent/pf-1a/PF_1A_E2_A_BUSINESS_AUTHORITY_RESOLUTION_CONTRACT_AND_DOMAIN_KERNEL.md
    - the accepted semantic contract this package persists. Read it in full FIRST; this document
      does not restate its invariants except where persistence changes how they are enforced.
      Sections that bind this package most directly: 5.1 (semantics vs facts), 8.2 (active_flag),
      9.3 (RAW candidate discovery and the lineage material contract, INCLUDING 9.3.2's rule for an
      object identity carrying no material and 9.3.4's DTO-required / DTO-optional split), 9.5 (what
      a provider may store and may not judge), 9.6 (test-only providers), 9.7 (provider structural
      capability and the THREE VERIFICATION CLASSES A / B1 / B2 - which malformed shapes this store
      must be able to hold and parity-test, which it may instead reject structurally while E2-A
      proves the semantics directly, and which it may reject structurally with no provider-neutral
      counterpart to prove at all),
      11.4 (the asserted-interval closure rule:
      successor closure, gaps, adjacency, explicit overlap), 11.5-11.6 (gaps versus contradictions),
      11.8 (recorded time versus business-effective time, and recorded-timestamp validity),
      12.4 (scope composition), 15.3 (aggregation precedence), 15.5 (the TOTAL fail-closed defect
      order), 16 (evidence, including 16.5 ordering).
docs/agent/pf-1a/PF_1A_E1_EXPLICIT_PERMISSION_COMPATIBILITY_FOUNDATION.md
docs/continuity/PF_1A_E1_INTEGRATION_CLOSURE_2026-09-02.md
docs/agent/contracts/organization-authority-authorization-contract.md        ORA-001 (APPROVED)
docs/agent/contracts/resource-master-reference-contract.md                   RMR-001 (APPROVED)
docs/agent/pf-1f-hr/PF_1A_AUTHORITY_CONFIGURATION_MODEL.md                   ADR-033 model
docs/agent/pf-1f-hr/PF_1F_HR_CANONICAL_REFERENCE_MODEL.md                    canonical HR contract
docs/agent/pf-1f-hr/PF_1F_HR_DECISION_GATE.md                                sections A and B
docs/agent/ARCHITECTURE_DECISIONS.md      ADR-007 (IDs), ADR-017, ADR-023, ADR-026,
                                          ADR-028 (PostgreSQL only - never T-SQL, never a
                                          dual-dialect layer), ADR-030, ADR-032, ADR-033
docs/agent/CODING_STANDARDS.md            module structure, PostgreSQL SQL rules, naming
docs/agent/TESTING_STRATEGY.md            sections 6 and 13
docs/agent/architecture/PRODUCTION_READINESS_GATES.md
docs/agent/architecture/INDEPENDENT_IMPLEMENTATION_REVIEW_WORKFLOW.md
docs/agent/architecture/BOUNDED_INDEPENDENT_REVIEW_METHOD.md
docs/continuity/OPEN_QUESTIONS.md          Q-09, Q-10
```

Runtime code to read before implementing:

```text
the whole PF-1A-E2-A implementation as integrated (kernel, ports, DTOs, reason codes, fixtures)
backend/app/models_metadata.py
backend/app/modules/authorization/models.py     AuthzPermission, AuthzRolePermission (E1 - do not
                                                 alter; note the id/public_id/timestamp conventions)
backend/app/modules/authorization/repository.py  the existing text()-SQL repository pattern
backend/alembic/versions/20260831_0030_explicit_permission_compatibility_foundation.py
                                                 the current head at definition time, and the
                                                 reference example for a self-contained migration
backend/app/core/database.py                     Base, session/`get_db` conventions
backend/tests/conftest.py                        session fixtures and the business_event boundary
```

## 4. Terminology

The four concepts defined in PF-1A-E2-A section 4 apply unchanged and must never be collapsed:
**Application/Login Role**, **Application Permission**, **Business Authority Role**, **Business
Authority**. Two persistence-specific consequences:

```text
- The existing `role` table means Application/Login Role. A Business Authority Role is a DIFFERENT
  table with a DIFFERENT identifier space. There must be no foreign key, join, view, mapping table
  or coincidental code equality between them. A reviewer finding such a link should treat it as a
  blocking defect.
- Table and column names must make the distinction obvious at a glance. Prefer
  `authz_business_authority_role` over `authz_authority_role` or `authz_role`.
```

## 5. Scope

### 5.1 Persistence of the accepted E2-A model

Persist each of the four object families with **stable object identity separated from immutable
published version identity**:

```text
stable identity table    one row per stable object; identity only, never versioned
version table             one row per published version; immutable business meaning
```

Indicative shape (names and exact columns are engineering decisions for the implementation package;
the separation and the invariants are not):

```text
authz_business_authority_role            / authz_business_authority_role_version
authz_business_authority                 / authz_business_authority_version
authz_business_authority_rule            / authz_business_authority_rule_version
authz_business_authority_assignment      / authz_business_authority_assignment_version
authz_business_authority_version_retraction   append-only retraction assertions (E2-A 11.3)
```

Conventions to follow (ADR-007 and the existing E1 models): integer identity primary key, a UUID
`public_id` where a record is externally referenceable, timezone-aware UTC timestamps, explicit
foreign keys, lowercase snake_case names, no hard deletes.

Version rows carry, at minimum, the fields E2-A section 8.1 defines: the stable object reference,
the version number, the family-specific business payload, `effective_from`, nullable
`declared_effective_to`, `active_flag`, publication provenance (`publication_reference_type`,
`publication_reference_id`, `published_at`) and nullable `corrects_object_version`.

**`active_flag` persistence (F-01).** `active_flag` is an immutable published value on a version
row (E2-A 8.2). Consequences for the schema:

```text
- It is a plain, NOT NULL, stored boolean on the VERSION row. It is never a computed column, never
  a view-derived projection, never inferred from effective_from/declared_effective_to, and never
  stored on the stable-identity row.
- No UPDATE path exists for it, or for any other column of a published version row (section 5.2).
  Deactivation is a NEW version row with active_flag = false.
- The store applies NO active_flag filter anywhere. Inactive versions are returned in lineage
  material like any other version, because an inactive version legitimately closes its predecessor
  in derived closure (E2-A 11.4) and excluding it would silently re-open a deactivated object.
```

Assignment version rows carry `person_id` **XOR** `position_id`, plus `scope_type` / `scope_id`.
Rule version rows carry the role and authority **stable** references, scope,
`parameter_evaluator_type` and the evaluator `parameter_payload`.

`person_id`, `position_id` and canonical scope identifiers are **canonical platform identifiers
stored as opaque values**. They are not foreign keys to any local table, because PF-1A owns no
Employee/Organisation/Position master (ADR-026, ADR-032, `RMR-001`). Do not create one, and do not
create a "convenience" local mirror table.

### 5.2 Database-backed read-side provider — facts only (F-02)

Implement the E2-A **authority configuration port** (E2-A section 9.3) against PostgreSQL. The port
is candidate discovery plus complete lineage material. It is **not** a set of `list_effective_*`
operations, and reintroducing one is a blocking defect.

```text
find_business_authority_ids_by_code(authority_code)
find_rule_ids_for_authority(business_authority_id)
find_assignment_ids_for_role(business_authority_role_id)
get_lineage(object_family, object_id)
get_published_version(object_family, object_id, object_version)
```

Binding rules, restated in persistence terms:

```text
DISCOVERY FROM RAW PUBLISHED FACTS (identity only, deliberately a superset)     (F-07)
    - Returns STABLE IDENTITIES ONLY, never versions.
    - The WHERE clause may reference ONLY the structurally trustworthy storage keys / index columns
      named in E2-A 9.3.1 - object family, stable identity, authority_code, stable reference - and
      must match if ANY RAW published version row satisfies it (typically a plain EXISTS over the
      version table).
    - The EXISTS must NOT be qualified by a NOT EXISTS over the retraction table, and must NOT be
      qualified by effective time, active_flag, scope, parameters, provenance, or any "latest
      version" notion. Any such predicate is a BLOCKING DEFECT, because it would decide, in SQL, a
      question E2-A reserves for the kernel - and because the excluded fact can itself BE the defect
      the kernel must detect.
    - Stated as the concrete case a reviewer should probe: if the ONLY version carrying the
      requested authority_code (or the only version carrying a relevant stable reference) is
      targeted by a retraction assertion, that object MUST still be discovered. Whether the
      retraction is valid is a kernel judgement made after get_lineage, not a WHERE clause.
    - Earlier drafts of this document directed a retraction-excluding EXISTS. That instruction is
      WITHDRAWN and must not be reintroduced.

LINEAGE MATERIAL (complete)
    - get_lineage returns EVERY published version row of the object - retracted, inactive,
      superseded, future-dated, all of them - plus EVERY retraction assertion for that object.
      The retraction assertions are returned as FACTS the kernel validates, never applied as a
      filter by the store.
    - It computes nothing: no derived closure, no effectiveness, no ranking, no deduplication, no
      tie-break, no "latest".
    - published_at and retracted_at are returned as immutable recorded-time provenance evidence and
      validation input (E2-A 11.8). The store never uses either as a filter, never treats either as
      a business-effective bound, and never exposes a "known as at" cutoff parameter on any port
      operation.
    - If the full set cannot be read, it returns completeness = UNAVAILABLE. A truncated list
      presented as COMPLETE is a blocking defect.

DEREFERENCE
    - get_published_version returns the immutable content of a version regardless of retraction or
      correction (E2-A 9.3.2, 11.3).

GENERAL
    - READ-ONLY in production terms. No create/update/deactivate/publish/delete operation is
      exposed by the repository, the service layer, any dependency, or any route (there are no
      routes here).
    - Every query is parameterized. No string interpolation of caller-controlled values.
    - PostgreSQL SQL only (ADR-028). No T-SQL, no dual-dialect branch, no compatibility layer.
    - Deterministic ordering is applied IN THE QUERY (explicit total ORDER BY over canonical
      identifiers, effective_from and version numbers), so the provider never returns an
      order-dependent result. The kernel re-sorts canonically regardless (E2-A 9.3.3).
    - `first()` / `LIMIT 1` / `scalar()` / `DISTINCT ON` must NEVER be used where uniqueness or
      ambiguity matters. The provider returns everything it found; the kernel fails closed on
      multiplicity. Hiding ambiguity by selecting one row is a blocking defect.
    - A read error, timeout or partial result surfaces as completeness = UNAVAILABLE or a raised
      provider error, which the kernel maps to AUTHORITY_CONFIGURATION_UNAVAILABLE. It is NEVER
      returned as an empty result set.
```

**No semantic duplication.** The provider must not contain a second implementation of
effectiveness, closure, activity, gap-versus-contradiction, scope composition or aggregation. Those
live in the E2-A kernel (E2-A 5.1). A provider that "helpfully" pre-validates lineage is a blocking
defect even when its answers agree, because two copies drift.

### 5.3 Runtime wiring and the production dependency seam (F-04)

Business authority resolution has three dependencies: the authority configuration port (this
package supplies it), the actor→canonical-person port, and the canonical HR/organisation port. Only
the first exists after E2-B.

```text
TEST / REFERENCE COMPOSITION  (permitted, and the only place synthetic providers may appear)
    - Composes the unchanged E2-A kernel with the E2-B PostgreSQL configuration provider and the
      E2-A TEST-ONLY reference actor-person and HR providers.
    - Lives under backend/tests/ (or an equivalent explicitly test-only location), never under a
      production package path.
    - This is how the parity corpus in section 9 is executed. It is a test harness, not a product.

PRODUCTION COMPOSITION SEAM  (defined here, deliberately not satisfiable yet)
    - E2-B defines the production dependency seam - the explicit place where authoritative
      providers will later be bound - and binds ONLY the PostgreSQL authority configuration
      provider to it.
    - Because no authoritative actor-person or HR provider exists, the production composition MUST
      do exactly one of:
          (a) REFUSE TO COMPOSE: the factory/provider raises a configuration error at wiring time,
              so no resolver object is ever produced; or
          (b) FAIL CLOSED DETERMINISTICALLY: if a resolver object exists, every call returns
              DENY + FAIL_CLOSED with ACTOR_PERSON_PROVIDER_NOT_CONFIGURED /
              HR_REFERENCE_PROVIDER_NOT_CONFIGURED (E2-A 14.3), producing normal evidence with the
              stage that could not be reached (E2-A 16.4).
      The implementation package chooses one and records the choice. Option (a) is recommended
      because an unusable object cannot be misused.
    - It is a BLOCKING DEFECT for a production composition to bind, import, fall back to, default
      to, or be configurable into a synthetic/reference actor-person or HR provider. A test must
      prove the synthetic providers are unreachable from production imports and from the production
      dependency wiring.
    - No environment variable, settings flag, feature toggle or dependency-override may switch a
      production composition onto synthetic identity or HR state.

OTHER WIRING
    - The kernel is reused UNCHANGED. Any required kernel change is a reconciliation finding.
    - SQLAlchemy model registration in backend/app/models_metadata.py so Alembic discovers the
      tables.
    - No HTTP route, request/response schema, OpenAPI surface, business event or frontend change.
```

### 5.4 Migration

```text
- Exactly ONE bounded Alembic revision.
- Its down_revision is the ACTUAL head discovered when the package starts (see section 1), verified
  from backend/alembic/versions/ and `alembic heads` - never inferred from a filename alone and
  never taken from this document.
- It creates only the new authority tables, their constraints and their indexes.
- It alters NO existing table, column, index or constraint. In particular it does not touch `role`,
  `app_user`, `user_role`, `authz_permission` or `authz_role_permission`.
- It seeds NO authority configuration of any kind. Not a catalogue, not a rule, not an assignment,
  not a bootstrap holder. Deterministic tests create their own synthetic data.
- It must be reviewed for a clean upgrade from an EMPTY database and must leave exactly one head.
```

### 5.5 Structured evaluator payload persistence

`parameter_payload` is stored as structured data — `JSONB` is the recommended PostgreSQL
representation, because the payload shape legitimately varies per evaluator type (E2-A section 13)
and forcing every authority into one universal monetary column set is explicitly rejected by
ADR-033.

```text
- The DATABASE stores the payload. The KERNEL validates it. E2-A validation remains semantically
  authoritative and runs at evaluation time regardless of what the store accepted.
- A NOT NULL / valid-JSON constraint is appropriate. A database-side schema check per evaluator type
  is NOT required and must not become a second, drifting source of truth.
- The payload is declarative data only. It must never carry code, an expression string, SQL, a
  template, or anything else interpreted as executable logic.
```

### 5.6 Structural versus semantic integrity

Be explicit about which invariants the database enforces and which the kernel must enforce
fail-closed. Enforce structurally what can be enforced structurally; do not pretend the rest is
covered, and — critically — **do not enforce structurally anything that would pre-empt a kernel
decision or forbid valid history**.

```text
ENFORCEABLE STRUCTURALLY (database)
    Each item below rejects a WRITE. Every defect shape it thereby makes unstorable is EITHER a
    CLASS B1 or a CLASS B2 fixture under E2-A 9.7, and section 5.7 here assigns each one
    explicitly. In both cases this store proves the rejection and the shape is excluded from the
    PostgreSQL parity corpus; the difference is what proves the SEMANTICS:
        B1 - a provider-neutral counterpart exists, and a NAMED, EXECUTED E2-A test proves the
             fail-closed response at a NAMED boundary (E2-A section 18);
        B2 - no provider-neutral counterpart exists, so there is nothing for E2-A to prove, and a
             written rationale in 5.7 records why.
    Either way the exclusion from parity is verification PLACEMENT, never a semantic exemption, and
    it must be recorded openly in the acceptance record. The class is stated per constraint below.

    unique (object_id, object_version) per family - an IMMUTABLE IDENTITY/VERSION KEY;
                                                                                 [B1 -> B1-01]
    person_id XOR position_id on an assignment version (CHECK: exactly one non-null);
                                                                                 [B1 -> B1-02, B1-03]
    declared_effective_to IS NULL OR declared_effective_to > effective_from (CHECK; E2-A I-6 - a
      SINGLE-ROW interval-shape check, and the ONLY interval condition safe to enforce
      structurally);                                                             [B1 -> B1-04, B1-05]
    NOT NULL on effective_from and active_flag;                                   [B1 -> B1-06, B1-07]
    NOT NULL on publication_reference_type;                                       [B1 -> B1-09a]
    NOT NULL on publication_reference_id;                                         [B1 -> B1-09b]
    NOT NULL, timezone-aware published_at on every version row and retracted_at on every retraction
      row (E2-A 11.8.3) - stored faithfully, never defaulted to "now" on read, never rewritten;
                                                                                 [B1 -> B1-08a, B1-08b]
    publication_reference_type restricted to the two defined values (a closed enum domain);
                                                                                 [B1 -> B1-10]
    foreign keys from every version row to its stable identity row;                [B2 -> B2-01]
    foreign keys from rule/assignment version rows to the STABLE identity of the role/authority they
      reference (never to a specific version, which would break correction).      [B2 -> B2-03]
      NOTE the exact reach of this FK, because the distinction is the whole reason it is B2 rather
      than B1: it rejects a reference to a stable identity ROW that does not exist at all, and that
      rejection has NO distinct provider-neutral counterpart, because E2-A 9.3.2 returns COMPLETE
      material with an empty versions[] for an identity carrying nothing - which is exactly the
      class A AUTHORITY_REFERENCE_DANGLING state. The FK does NOT reject - and must not be extended
      to reject - a reference to a stable identity row that EXISTS but carries no lineage material,
      which IS that class A state and must remain storable and parity-tested;
    foreign key from a retraction row to the stable identity of the object it retracts (again to the
      STABLE identity only - see the prohibition on a version-level retraction FK below);
                                                                                 [B2 -> B2-02]
    no-UPDATE discipline on published version rows and retraction rows (see below);
    indexes supporting authority_code discovery, stable-reference discovery, per-object lineage
      retrieval and version dereference.

NOT ENFORCEABLE STRUCTURALLY - the KERNEL detects and FAILS CLOSED
    "exactly one effective version at as_of" (an interval-overlap condition across rows, against a
      DERIVED closure). NOTE (F-10.2): the two reachable ways this can be violated - a duplicate
      temporal start and a contradictory explicit overlap - are the separate entries below and are
      class A fixtures A-02 and A-01. The RESIDUAL form of the condition, ">1 effective version
      after those checks have passed", is proved unreachable on every provider by E2-A 11.4a; the
      kernel retains it as a defensive invariant (reason AUTHORITY_VERSION_AMBIGUOUS) but there is
      NO storable state and therefore NO fixture for it here - see NS-K-01 in section 5.7A;
    duplicate effective_from across the current asserted lineage;
    CONTRADICTORY EXPLICIT OVERLAP - declared_effective_to strictly later than the next valid
      successor's effective_from (E2-A 11.4). This is a MULTI-ROW condition against derived closure
      and must NOT be enforced structurally, precisely so the kernel can report it (F-09);
    contradictory or forked publication lineage;
    a correcting version whose corrected target is not retracted, or does not exist;
    a retraction referencing a version that does not exist (the store must NOT reject this; see
      below);
    more than one retraction assertion for the same (object_id, object_version) (likewise storable
      by design);
    impossible recorded provenance - retracted_at before its target's published_at, a correcting
      version published before its target's retracted_at, or decreasing published_at within one
      lineage's publication order (E2-A 11.8.3) (F-07);
    a dangling reference to a stable identity with no lineage material;
    the VALIDITY of a retraction assertion, and therefore which versions form the current asserted
      lineage at all;
    ambiguous or missing canonical HR state;
    ambiguous actor->person mapping;
    unknown evaluator type or invalid payload;
    unsupported scope semantics, missing required scope context, unresolvable org hierarchy;
    scope composition and cross-path aggregation outcomes;
    result-level fail-closed reason selection under the total defect order (E2-A 15.5) (F-08).

MUST NOT BE ENFORCED STRUCTURALLY, AND MUST NOT BE NORMALIZED (F-05, F-02, F-07, F-09)
    - Do NOT add any constraint that forbids a TEMPORAL GAP between one version's
      declared_effective_to and the next version's effective_from. A gap is valid history
      (E2-A 11.5). A "contiguity" or "no gap" constraint would reject legitimate configuration.
    - Do NOT add a constraint or trigger that rejects a second version overlapping an earlier one.
      Overlap detection belongs to the kernel against derived closure, and a database-side rejection
      would silently prevent the kernel from ever reporting AUTHORITY_LINEAGE_CONTRADICTORY - which
      is exactly the defect class the parity tests must be able to exercise.
    - Do NOT add a unique constraint, partial index, exclusion constraint or trigger on
      (stable_object_id, effective_from) - or on any equivalent "one version may start at a given
      instant" rule - in order to reject DUPLICATE TEMPORAL STARTS. Duplicate-start classification
      and its PostgreSQL parity are required (E2-A 11.4, 9.7 class A; fixture A-02), so temporal
      start is
      deliberately NOT a structural identity key here. The unique (object_id, object_version) key
      above is a different thing - an immutable IDENTITY/VERSION key - and remains mandatory; do not
      reason from one to the other.
    - Do NOT add a foreign key, CHECK or trigger on corrects_object_version. A correcting version
      whose target does not exist, or whose target is not retracted, is a CLASS A defect E2-A 11.6
      requires the KERNEL to detect (fixtures A-06 and A-07), and the parity corpus must be able to
      seed both shapes.
    - Do NOT "helpfully" NORMALIZE any stored lineage shape (F-09). The store must persist and return
      exactly what was published, for every one of the E2-A 11.4 shapes:
          V1 [t0, null) + V2 from t2        (successor closes a NULL end)
          V1 [t0, t2)   + V2 from t2        (explicit adjacency)
          V1 [t0, t1)   + V2 from t2, t1<t2 (valid gap, then reactivation)
          V1 [t0, t3)   + V2 from t2, t2<t3 (CONTRADICTORY EXPLICIT OVERLAP - must be STORABLE)
          two versions sharing one effective_from (duplicate start - must be STORABLE)
      In particular: never truncate a declared_effective_to to the successor's effective_from on
      write or on read; never rewrite a NULL declared end into a concrete one; never coalesce, merge,
      split, reorder or renumber versions. A store that normalizes any of these makes the
      corresponding kernel classification untestable and is a blocking defect.
    - Do NOT store a derived asserted_effective_to column, materialized view, or trigger-maintained
      "is_current" flag. Closure is derived per resolution (E2-A 11.4); storing it creates a second
      source of truth that can disagree with the kernel.
    - Do NOT add a CHECK or partial index that presumes only active versions matter.
    - Do NOT add a constraint, trigger, view or query predicate that treats a retraction assertion as
      removing its target row from the store, from discovery, or from lineage material. A retracted
      version remains a stored, discoverable, returnable and dereferenceable fact (F-07).
    - Do NOT enforce "one retraction per version" structurally (a unique constraint on
      (object_id, object_version) over retraction rows), and do NOT enforce structurally that a
      retraction's target version exists. Both are conditions E2-A 11.6 requires the KERNEL to detect
      and fail closed on, and the parity corpus must be able to seed a DUPLICATED retraction and a
      DANGLING retraction in PostgreSQL. Enforcing either structurally would suppress a defect class
      the kernel owns - the same mistake, in a different place, as the withdrawn
      retraction-excluding EXISTS in 5.2. (Note the FK above is to the STABLE IDENTITY row, which is
      safe; an FK to the specific version row is NOT, because it would forbid a dangling retraction.)
    - Do NOT enforce the E2-A 11.8.3 recorded-timestamp relationships structurally in a way that
      REJECTS the write. The parity corpus must be able to seed impossible provenance so the kernel
      can be proved to fail closed on it. (A single-row NOT NULL / timezone-aware check is fine; a
      cross-row ordering constraint is not.)
    - Do NOT constrain parameter_evaluator_type to a closed enum/CHECK/lookup FK of "known"
      evaluator types, and do NOT add a per-type payload schema check (5.5). E2-A's EVALUATOR_UNKNOWN
      and EVALUATOR_PAYLOAD_INVALID are CLASS A defects (A-13, A-14) the KERNEL must classify at
      evaluation time,
      so an unknown type and a malformed payload must both be storable and parity-testable. A
      NOT NULL / valid-JSON constraint on the payload is the permitted limit.
    - Do NOT constrain scope_type to a closed enum/CHECK/lookup FK of supported scope semantics.
      E2-A's SCOPE_SEMANTICS_UNSUPPORTED is likewise a CLASS A defect (A-15) the kernel must
      classify, and a
      database enum would make it unseedable and therefore unparity-testable.
```

**Structural rejection and the three verification classes, stated so it is neither generalized nor
forgotten (F-10).** A structural constraint that rejects a defect at write time necessarily makes
that defect unseedable in PostgreSQL, so the parity corpus cannot exercise the fail-closed handling
of it *through this store*. Earlier drafts of this document tried to describe that trade as a single
narrow exception for `declared_effective_to > effective_from`, which was wrong twice over: it
understated the case (the mandatory identity-uniqueness, XOR, NOT NULL, enum-domain and
stable-identity foreign keys above have the same effect) and it left section 9 and criterion 10.N
demanding PostgreSQL parity for shapes the schema forbids. Cycle 3 resolved that with two lanes, but
assumed every rejected shape had an equivalent malformed input testable directly against the kernel.
For three of the constraints above that is simply false, and asserting it produced obligations no
implementation could discharge. Both problems are now resolved by the **three verification classes
of E2-A section 9.7**, with the binding, TOTAL per-fixture assignment for this store in **section
5.7** below.

The rule that governs which side of the line a constraint may sit on:

```text
A structural constraint is PERMITTED - and its defects become CLASS B1 or CLASS B2 - only when it
protects ROW IDENTITY or ROW SHAPE and is fully decidable from the row (or key) itself: an immutable
identity/version uniqueness key, a mandatory XOR/check-shape condition, NOT NULL, a closed enum
domain, a single-row interval-shape check, or a foreign key to a STABLE IDENTITY ROW. Such a
condition is rejected loudly at write and hides nothing at read time.

A structural constraint is FORBIDDEN when it would pre-empt a CROSS-ROW or DERIVED SEMANTIC
judgement the kernel owns: overlap, duplicate temporal start, retraction validity, retraction
uniqueness, correction targets, recorded-provenance ordering, dangling references to a stable
identity carrying no material, or "exactly one effective version". Rejecting one of those at write
would suppress a defect class the kernel owns while wearing the costume of the same safeguard, and
is a blocking defect - see the "MUST NOT BE ENFORCED STRUCTURALLY" list above.

WHICH OF B1 / B2 a permitted constraint produces is decided by E2-A 9.7's deciding test, applied to
the constraint's OWN invariant: could any conforming provider, using only the E2-A 9.3.2 / 9.3.4
fields and without inventing a persistence-specific field, present a state the kernel would classify
DIFFERENTLY from an already-classified state?  YES -> B1.  NO -> B2.
```

For every **class B1** defect class, all four of the following are required, and none may be dropped:

```text
- an E2-B test asserts the STRUCTURAL REJECTION (the INSERT fails, with the expected constraint);
- a NAMED, ACTUALLY-EXECUTED E2-A test (E2-A section 18, DIRECT E2-A MALFORMED-INPUT COVERAGE)
  proves the provider-neutral fail-closed response for the equivalent malformed input, at the
  BOUNDARY named for that fixture - PURE KERNEL, or DTO / PORT WELL-FORMEDNESS - with a NORMATIVE
  expected reason code;
- the shape is EXPLICITLY EXCLUDED from the PostgreSQL parity corpus of section 9, because no
  conforming implementation of this store can truthfully return a row its schema forbids storing;
  and
- the E2-B acceptance record names the defect class, the constraint that rejects it, the covering
  E2-A test and that test's boundary, so the exclusion is visible rather than inferred.
```

For every **class B2** defect class, all five of the following are required, and none may be
dropped:

```text
- an E2-B test asserts the STRUCTURAL REJECTION (the INSERT fails, with the expected constraint);
- the shape is EXPLICITLY EXCLUDED from the PostgreSQL parity corpus of section 9;
- the shape is EXPLICITLY EXCLUDED from E2-A's semantic fixture and parity manifests - it appears
  NOWHERE in E2-A section 18, and E2-A asserts that absence deliberately;
- section 5.7 and the acceptance record carry a SHORT NORMATIVE RATIONALE explaining why there is no
  meaningful provider-neutral malformed-input counterpart; and
- NO E2-A reason code and NO DTO field/shape is invented solely to mirror the database
  implementation detail.
```

The exclusion is a statement about PostgreSQL's structural capability and about the provider-neutral
contract's own shape, never about the semantics. E2-A's rules still bind every provider, a future
provider whose schema can hold a B1 shape inherits a class A obligation for it automatically, and a
future change to E2-A 9.3.2 / 9.3.4 that makes a B2 state expressible converts it to B1 with a
mandatory E2-A test.

**Class B2 is not an escape hatch.** It applies only to invariants over this store's own
representation of identity and parentage — the three foreign keys marked `[B2]` above, which exist
solely because 5.1 splits stable identity into its own physical row. A malformed *business* state is
never B2. A B2 entry whose rationale is missing, circular, or amounts to "E2-A has no test for it"
is the F-10 defect reappearing and is a blocking finding.

**No-UPDATE discipline.** Published version rows and retraction rows are append-only. The
repository exposes no UPDATE or DELETE statement against them, and a test asserts that no code path
in the package issues one. A database-level guarantee (for example a rule/trigger that raises on
UPDATE or DELETE) is **optional and encouraged**; if adopted, it must not interfere with the test
fixtures' ability to INSERT the deliberately contradictory lineages the parity corpus requires.

A PostgreSQL exclusion constraint over an effective range is **not** required and must not be
adopted casually, for the reason stated above: the asserted closure of a version is *derived*, so a
range-exclusion constraint over stored columns would not express the real invariant and would
suppress a defect class the kernel owns. If an implementation believes it can express a genuine,
non-suppressing subset of the invariant structurally, it may — but it must not present that as
covering the whole invariant, must not prevent the corpus from inserting contradictory lineage, and
the kernel-side fail-closed detection remains mandatory either way.

### 5.7 The TOTAL verification-class manifest for this store (F-10)

E2-A section 9.7 defines the three classes provider-neutrally, and E2-A section 9.7.0 scopes them.
This section applies them to the PostgreSQL store described in 5.1-5.6 and is **binding and TOTAL**
for its scope: every **authority-store** negative fixture named anywhere in this document or in E2-A
section 18 appears exactly once below, in exactly one class. No fixture may appear in more than one
class, in none, or with its class left implicit, and no fixture's class, storability, expected reason
code or parity obligation may be deferred to implementation time.

**Scope of this manifest — normative (F-10.3, corrected by F-10.3a).** Per E2-A 9.7.0, the A/B1/B2
taxonomy classifies **only negative fixtures whose subject is a MALFORMED OR CONTRADICTORY state of
the published authority-store / read-repository data contract** — a raw published version record, a
retraction assertion, a stable-identity reference, or a stored field on one of those. That is the
only universe in which "can PostgreSQL store it?" is a meaningful question, and class A's defining
obligation (store the raw rows, read them back byte-identical, resolve through the wired kernel) is
only executable there.

Two things follow, and both were violated before F-10.3a:

- an item whose stored rows are **entirely valid** is not a negative fixture at all, however
  fail-closed its resolver outcome may be. It is a VALID-SHAPE PARITY SCENARIO (V-01 to V-12 below)
  when its subject is the stored state itself, or a NON-STORE scenario (5.7A) when its subject is a
  seam; either way it carries no A/B1/B2 label;
- a scenario that merely **reads** PostgreSQL rows while exercising a malformed provider, request,
  clock, orchestration, ordering or evidence condition is NOT an authority-store fixture. Store
  PARTICIPATION and store SUBJECTHOOD are different questions, and 5.7A answers them in two separate
  columns for exactly that reason. The rows such a scenario reads are usually valid; where its own
  defined semantics require it — NS-PR-03, NS-AG-03, NS-AG-04 and NS-DO-01..05 — an
  ALREADY-CLASSIFIED class A malformed row participates as a CONTROLLED INGREDIENT, keeping its own
  class and its own obligations in this manifest and reclassifying nothing.       (F-10.3-DC-02)

```text
ENTRY TEST, applied to every negative/conformance item before any class is assigned. BOTH questions
must be YES, and the first is the one A-12 failed:
    (i)  Is the item's SUBJECT a MALFORMED or CONTRADICTORY published authority-store state - one
         this store could, in principle, be asked to hold and return through get_lineage /
         discovery, and which this document requires the kernel to reject as invalid?
    (ii) Is that malformed state a property of raw published authority-store DATA, rather than of a
         provider, a request input, resolver orchestration, evidence handling or a kernel invariant?

    BOTH YES   -> classify A / B1 / B2 below, and answer all seven authority-store questions.
    (i) is NO  -> the stored state under test is VALID. It is a VALID-SHAPE PARITY SCENARIO (V-01 to
                  V-12 below) when its subject is that stored state, or a NON-STORE scenario (5.7A)
                  when its subject is a seam. No class label; not a negative fixture; still fully
                  parity-owed.
    (ii) is NO -> NON-STORE RESOLVER / PROVIDER CONFORMANCE SCENARIO. It goes in section 5.7A,
                  carries NO class label, and answers the eight non-store questions instead.

"N/A" IS NEVER AN ANSWER TO "PG may store". An item that would need one is, by construction, not an
authority-store fixture. That contradiction is exactly what the fourth review found in A-16, A-18,
A-19 and A-20, and it is why those IDs are retired. A-12 failed the test differently and just as
fatally: its "PG may store" answer was an honest YES, but there was no malformed state to store -
E2-A 11.5 states explicitly that the gap it rests on is VALID lineage.
```

Moving an item to 5.7A, or recognising it as a valid-shape scenario, removes **only** a PostgreSQL
*malformed-state* storage obligation that was never executable for it. It removes no fail-closed
rule, no normative expected reason code, no evidence obligation and no genuinely applicable parity
obligation; 5.7A restates each of those per scenario, naming the providers where parity applies, and
the V-list below stays inside the parity corpus in full.

**Retired IDs — never reused.**

```text
A-03   residual ">1 effective version at one as_of".  WITHDRAWN: proved unreachable on every
       provider by the E2-A 11.4a single-effective-version theorem, so there is no state to seed
       here and no parity to owe. The invariant is carried by NS-K-01 (5.7A).            (F-10.2)
A-12   requested authority_code with no grant-eligible-by-lineage version at as_of, including an
       as_of inside a VALID GAP.  MOVED to NS-RS-01 (5.7A). Every row involved is VALID - E2-A 11.5
       says so in terms - so there is no malformed authority-store state to classify; what is under
       test is the RESOLVER's deliberate asymmetry at an as_of over valid lineage. The
       DENY + FAIL_CLOSED / AUTHORITY_CODE_NOT_CONFIGURED expectation, the PostgreSQL seeding of the
       VALID rows, and the FULL parity obligation are all carried unchanged by NS-RS-01. Nothing
       about this move weakens 11.5's asymmetry or the code it produces.                (F-10.3a)
A-16   induced read failure / timeout / truncated read.  MOVED to NS-PT-01 (5.7A): the subject is
       the authority configuration PORT's read/transport behaviour, not a stored row.    (F-10.3)
A-18   actor-person and HR/organisation fail-closed states.  MOVED to NS-AP-01..03 and
       NS-HR-01..12 (5.7A), one scenario per fail-closed reason code.                    (F-10.3)
A-19   evaluator facts absent / type-invalid in the supplied business context.  MOVED to NS-RQ-02
       (5.7A): the subject is request-side input.                                        (F-10.3)
A-20   scope context missing for a non-GLOBAL operand.  MOVED to NS-RQ-01 (5.7A): likewise
       request-side input.                                                               (F-10.3)
```

**Counts after closure**, asserted by the coverage test in section 9:

```text
CLASS A     14   A-01, A-02, A-04 to A-11, A-13 to A-15, A-17
CLASS B1    12   B1-01 to B1-07, B1-08a, B1-08b, B1-09a, B1-09b, B1-10
CLASS B2     3   B2-01, B2-02, B2-03
            --
            29   authority-store negative fixtures, total

VALID-SHAPE 12   V-01 to V-12      (below in this section; no class label, FULL parity owed)

NON-STORE   46   NS-AP-01..04, NS-HR-01..12, NS-RQ-01..02, NS-PT-01, NS-PR-01..03,
                 NS-RS-01..04, NS-AG-01..05, NS-DO-01..06, NS-EV-01..07, NS-K-01..02
                                   (section 5.7A)
```

Class A IDs are deliberately NOT renumbered to close the gaps left by the retired entries. Stable
IDs keep every cross-reference in both documents, in the acceptance record and in any review packet
resolvable; renumbering would silently repoint them.

```text
CLASS A   PERSISTABLE SEMANTIC CONTRADICTION
          PostgreSQL can and must store the raw shape; the read path returns the raw facts; the
          PostgreSQL-backed and reference-backed resolutions must agree on classification, reason
          and evidence ordering. FULL parity is owed.

CLASS B1  DATABASE-REJECTED STRUCTURE, WITH a provider-neutral E2-A counterpart
          a 5.6 structural constraint makes the row unstorable, AND the equivalent malformed state
          IS representable through E2-A's own DTO fields. This store proves the REJECTION; a named,
          executed E2-A test proves the fail-closed response at the NAMED boundary; the shape is
          EXCLUDED from the PostgreSQL parity corpus and the exclusion is named in the acceptance
          record. Not a semantic exemption.

CLASS B2  PERSISTENCE-ONLY STRUCTURAL INVARIANT, with NO provider-neutral counterpart
          a 5.6 structural constraint makes the row unstorable, AND after persistence decoding there
          is no DISTINCT malformed state E2-A can express, because the provider-neutral contract does
          not model what the constraint protects. This store proves the REJECTION; the shape is
          excluded from the parity corpus AND from every E2-A fixture manifest; a written rationale
          is mandatory. Not a semantic exemption either - it is a statement that there is no
          semantic obligation to place, tested against E2-A 9.7's deciding test.
```

Index, for scanning. Every row's subject is a MALFORMED authority-store state, so no cell reads
"N/A" and no row describes a valid stored shape. The per-fixture records follow.

| ID | Fixture / defect shape | Class | PG may store | E2-A representable (boundary) | E2-A fixture name | PG parity |
| --- | --- | --- | --- | --- | --- | --- |
| A-01 | explicit cross-version overlap | A | YES | YES (kernel) | §18 LINEAGE AND CLOSURE, EXPLICIT END AFTER SUCCESSOR | YES |
| A-02 | duplicate temporal start | A | YES | YES (kernel) | §18 LINEAGE AND CLOSURE, DUPLICATE START | YES |
| A-04 | dangling retraction (missing target version) | A | YES | YES (kernel) | §18 RAW DISCOVERY AND RETRACTION | YES |
| A-05 | duplicated retraction of one version | A | YES | YES (kernel) | §18 RAW DISCOVERY AND RETRACTION | YES |
| A-06 | correction target exists but is not retracted | A | YES | YES (kernel) | §18 LINEAGE AND CLOSURE | YES |
| A-07 | correction target does not exist | A | YES | YES (kernel) | §18 LINEAGE AND CLOSURE | YES |
| A-08 | provenance: retracted_at before target published_at | A | YES | YES (kernel) | §18 RECORDED TIME, PROVENANCE VALIDITY | YES |
| A-09 | provenance: correction published before target retracted | A | YES | YES (kernel) | §18 RECORDED TIME, PROVENANCE VALIDITY | YES |
| A-10 | provenance: published_at decreasing across versions | A | YES | YES (kernel) | §18 RECORDED TIME, PROVENANCE VALIDITY | YES |
| A-11 | reference to a stable identity carrying no material | A | YES | YES (provider port) | §18 DIRECT COVERAGE, dangling-reference case | YES |
| A-13 | unknown parameter_evaluator_type | A | YES | YES (kernel) | §18 EVALUATORS | YES |
| A-14 | malformed / type-invalid parameter_payload | A | YES | YES (kernel) | §18 EVALUATORS | YES |
| A-15 | unsupported scope_type value | A | YES | YES (kernel) | §18 SCOPE AND COMPOSITION | YES |
| A-17 | malformed retraction on the ONLY code/reference-bearing version | A | YES | YES (kernel) | §18 RAW DISCOVERY, MALFORMED RETRACTION CANNOT HIDE A VERSION | YES |
| B1-01 | duplicate (object_id, object_version) | B1 | NO | YES (kernel) | DUPLICATE-OBJECT-VERSION | NO |
| B1-02 | assignment with BOTH targets | B1 | NO | YES (kernel, S7) | ASSIGNMENT-TARGET-BOTH | NO |
| B1-03 | assignment with NEITHER target | B1 | NO | YES (kernel, S7) | ASSIGNMENT-TARGET-NEITHER | NO |
| B1-04 | declared_effective_to < effective_from | B1 | NO | YES (kernel) | INTERVAL-END-BEFORE-START | NO |
| B1-05 | declared_effective_to == effective_from | B1 | NO | YES (kernel) | INTERVAL-END-EQUALS-START | NO |
| B1-06 | NULL effective_from | B1 | NO | YES (DTO/port well-formedness) | VERSION-ABSENT-EFFECTIVE-FROM | NO |
| B1-07 | NULL active_flag | B1 | NO | YES (DTO/port well-formedness) | VERSION-ABSENT-ACTIVE-FLAG | NO |
| B1-08a | NULL published_at on a version | B1 | NO | YES (kernel) | PROVENANCE-ABSENT-PUBLISHED-AT | NO |
| B1-08b | NULL retracted_at on a retraction | B1 | NO | YES (kernel) | PROVENANCE-ABSENT-RETRACTED-AT | NO |
| B1-09a | **absent publication_reference_type** | B1 | NO | YES (kernel) | **PROVENANCE-ABSENT-TYPE** | NO |
| B1-09b | absent publication_reference_id | B1 | NO | YES (kernel) | PROVENANCE-ABSENT-REFERENCE-ID | NO |
| B1-10 | publication_reference_type outside the two values | B1 | NO | YES (kernel) | PROVENANCE-UNKNOWN-TYPE | NO |
| B2-01 | version row with no stable-identity parent row | B2 | NO | **NO** | none, by design | NO |
| B2-02 | retraction row with no object stable-identity parent row | B2 | NO | **NO** | none, by design | NO |
| B2-03 | rule/assignment referencing a non-existent stable identity ROW | B2 | NO | **NO** | none, by design | NO |

The `E2-A fixture name` column is one-to-one with the ID column for class B1: twelve B1 IDs, twelve
distinct named fixtures, twelve executing tests. F-10.1 arose precisely because one ID (`B1-09`)
covered two shapes and only one of them had a fixture, so this column is a mandatory part of the
manifest, not annotation.

#### Class A records — must be STORABLE and must be parity-tested

Every class A record shares the same three test obligations, so they are stated once rather than
repeated fourteen times:

```text
REQUIRED POSTGRESQL TEST   §9 STORAGE INTEGRITY - CLASS A STORABILITY (the INSERT succeeds and the
                           rows read back byte-identical) AND §9 DEFECT VISIBILITY (seed in
                           PostgreSQL, resolve through the wired kernel, assert the expected code).
REQUIRED E2-A TEST         the corresponding case in E2-A §18 (LINEAGE AND CLOSURE / RAW DISCOVERY
                           AND RETRACTION / RECORDED TIME / SCOPE AND COMPOSITION / EVALUATORS, as
                           applicable - and, for A-11, the dangling-reference case inside DIRECT
                           E2-A MALFORMED-INPUT COVERAGE, which a class A shape may legitimately
                           also carry), executed through the reference provider. ACTOR BOUNDARY and
                           POSITION ASSIGNMENT are no longer cited here: their subjects are
                           actor/HR provider answers, which are NON-STORE scenarios (5.7A), never
                           class A fixtures.
PG PARITY REQUIRED         YES - the same declarative scenario runs through both providers and must
                           agree on outcome, resolution_status, result_level_reason, all three
                           evidence collections and their ordering, and established_state.
```

```text
ID    FIXTURE / DEFECT SHAPE                        EXPECTED CLASSIFICATION / REASON
A-01  explicit cross-version overlap: a version's   DENY + FAIL_CLOSED
      declared_effective_to is strictly later than  AUTHORITY_LINEAGE_CONTRADICTORY
      its next valid successor's effective_from
      (E2-A 11.4); every row structurally valid
A-02  duplicate temporal start: two versions of one DENY + FAIL_CLOSED
      object sharing an effective_from, with        AUTHORITY_LINEAGE_CONTRADICTORY
      different object_version. Storable BY DESIGN:
      5.6 forbids any uniqueness/exclusion
      constraint on (stable_object_id,
      effective_from)
A-04  dangling retraction: a retraction assertion   DENY + FAIL_CLOSED
      targeting an object_version that does not     AUTHORITY_LINEAGE_CONTRADICTORY
      exist for an EXISTING object. Storable BY
      DESIGN: 5.6 forbids a retraction FK to a
      specific version row
A-05  duplicated retraction: two assertions for one DENY + FAIL_CLOSED
      (object_id, object_version). Storable BY      AUTHORITY_LINEAGE_CONTRADICTORY
      DESIGN: 5.6 forbids retraction uniqueness
A-06  correcting version whose corrects_object_     DENY + FAIL_CLOSED
      version target EXISTS but is not retracted.   AUTHORITY_LINEAGE_CONTRADICTORY
      Storable BY DESIGN: 5.6 forbids any FK/CHECK
      on corrects_object_version
A-07  correcting version whose corrects_object_     DENY + FAIL_CLOSED
      version target does not exist                 AUTHORITY_LINEAGE_CONTRADICTORY
A-08  impossible provenance: a retraction's         DENY + FAIL_CLOSED
      retracted_at precedes its target's            PUBLICATION_PROVENANCE_INVALID
      published_at (E2-A 11.8.3)
A-09  impossible provenance: a correcting version's DENY + FAIL_CLOSED
      published_at precedes its target's            PUBLICATION_PROVENANCE_INVALID
      retracted_at (E2-A 11.8.3)
A-10  impossible provenance: published_at decreases DENY + FAIL_CLOSED
      across increasing object_version within one   PUBLICATION_PROVENANCE_INVALID
      lineage (E2-A 11.8.3)
A-11  a rule/assignment references a stable         DENY + FAIL_CLOSED
      identity that carries NO lineage material.    AUTHORITY_REFERENCE_DANGLING
      In PostgreSQL: the stable identity ROW EXISTS
      and has no version rows - which the 5.6 FK
      permits and MUST NOT be extended to reject.
      Boundary note: provider port - get_lineage
      returns COMPLETE material with an empty
      versions[] (E2-A 9.3.2)
A-13  parameter_evaluator_type not in the evaluator DENY + FAIL_CLOSED
      registry. Storable BY DESIGN: 5.6 forbids a   EVALUATOR_UNKNOWN
      closed enum/CHECK/lookup FK on that column
A-14  parameter_payload malformed, incomplete or    DENY + FAIL_CLOSED
      type-invalid for its evaluator. Storable BY   EVALUATOR_PAYLOAD_INVALID
      DESIGN: 5.6 permits only NOT NULL/valid-JSON
A-15  scope_type value the scope evaluator does not DENY + FAIL_CLOSED
      support. Storable BY DESIGN: 5.6 forbids a    SCOPE_SEMANTICS_UNSUPPORTED
      closed enum/CHECK/lookup FK on scope_type
A-17  a malformed retraction (A-04, A-05 or A-08)   DENY + FAIL_CLOSED with THAT DEFECT'S OWN code
      targeting the ONLY requested-code-bearing     (AUTHORITY_LINEAGE_CONTRADICTORY or
      version, and - companion case - the ONLY      PUBLICATION_PROVENANCE_INVALID).
      reference-bearing version of a candidate      EXPLICITLY NOT AUTHORITY_CODE_NOT_CONFIGURED,
      Rule/Assignment                               NOT NO_CANDIDATE_ASSIGNMENT, NOT an empty
                                                    candidate set. The highest-value regression
                                                    test in this package (§9)

Fourteen class A fixtures: A-01, A-02, A-04 to A-11, A-13 to A-15, A-17. The gaps at A-03, A-12 and
A-16 to A-20 are the retired IDs recorded above; they are not oversights and must not be refilled.

Every one of the fourteen is a state this document REQUIRES the kernel to reject as invalid. That is
the property A-12 lacked, and it is the property to test any proposed new class A entry against: if
the kernel's correct answer over the seeded rows is "this configuration is valid, and here is what it
means at this as_of", the item is a valid-shape or non-store scenario, not a class A fixture.
```

#### VALID-SHAPE PARITY SCENARIOS — the third group (F-10.3a)

These are scenarios whose subject IS authority-store state and whose stored rows are **entirely
valid**. They are equally owed parity, because misclassifying one is the mirror-image defect of
misclassifying a contradiction. They are **NOT negative fixtures and carry no A/B1/B2 class label**,
and any sentence describing one as "class A" is the F-10.3a defect.

They were previously carried as an unnumbered prose list, which is how four of them
(null-end successor closure, explicit adjacency, the valid gap, reactivation) came to be described
as "CLASS A" in section 9 and criterion 10.N alongside the two genuine class A lineage
contradictions. Stable IDs are assigned here so the coverage test can assert the three-group
partition mechanically rather than by reading prose.

```text
ID    VALID STORED SHAPE UNDER TEST                                          PARITY
V-01  null-end successor closure: V1 [t0, null) with V2 from t2 -> V1        YES
      asserted end = t2, derived not stored, V1's row unmutated (E2-A 11.4)
V-02  explicit adjacency: V1 [t0, t2), V2 from t2 -> no gap and no overlap;  YES
      exactly at t2 only V2 is effective
V-03  explicit end before successor -> VALID GAP: V1 [t0, t1), V2 from t2,   YES
      t1 < t2 -> V1 asserted end = t1, neither truncated nor extended; the
      per-family gap behaviour of E2-A 11.5 for Assignment / Rule / Role
      (ASSIGNMENT_NOT_EFFECTIVE / RULE_NOT_EFFECTIVE / ROLE_NOT_EFFECTIVE,
      all NORMAL nonqualification, never fail-closed and never reported as
      overlap or as a dangling reference). The REQUESTED authority's
      asymmetric fail-closed case is NOT here: it is NS-RS-01 (5.7A)
V-04  later reactivation after that gap: V2 becoming effective at t2 keeps    YES
      the lineage VALID and DOES grant when otherwise eligible
V-05  inactive-but-effective versions in all four families, each producing    YES
      its own *_NOT_ACTIVE reason as NORMAL nonqualification, plus the
      AUTHORITY_NOT_ACTIVE result-level short-circuit (E2-A 15.3)
V-06  an INACTIVE version still closes its predecessor in derived closure -   YES
      active_flag never participates in the temporal rule (E2-A 8.2)
V-07  exact half-open boundary instants for every shape above: at each start; YES
      one tick before each start; one tick before each asserted end; exactly
      at each asserted end; at a gap start; one tick inside a gap; one tick
      before a gap end; and a future-dated version conferring nothing before
      its effective_from
V-08  raw discovery over VALID retraction facts: an object whose ONLY         YES
      code-bearing version is retracted, and one whose ONLY reference-bearing
      version is retracted, are each STILL DISCOVERED, their complete lineage
      reaches the kernel, and the kernel decides the outcome (E2-A 9.3.1)
V-09  recorded-time versus business-effective-time RECONSTRUCTION over valid  YES
      rows: a version published AFTER a historical as_of that nonetheless
      participates in resolve_authority_as_of(that as_of); a retraction
      recorded today that removes its target from an older reconstruction; a
      valid later correction that CHANGES what an old business as_of
      reconstructs while previously captured evidence stays byte-identical -
      both answers provable, neither overwriting the other (E2-A 11.8.1)
V-10  valid scope operands, each alone: GLOBAL; exact match; exact mismatch   YES
      (RULE_SCOPE_NOT_MATCHED / ASSIGNMENT_SCOPE_NOT_MATCHED, normal);
      ancestry match and ancestry non-match
V-11  scope COMPOSITION over valid operands: GLOBAL rule INTERSECT EXACT      YES
      assignment; EXACT rule INTERSECT GLOBAL assignment; both EXACT and
      equal; both EXACT and different (SCOPE_COMPOSITION_NOT_SATISFIED,
      normal); ancestry INTERSECT exact; and a case proving there is NO
      union/widening behaviour (E2-A 12.4)
V-12  evaluator satisfaction and LEGITIMATE non-satisfaction over a valid     YES
      stored evaluator and payload, the supplied facts being present,
      correctly typed AND unit/currency/basis-COMPATIBLE: NONE; a numeric
      band at each boundary under each inclusivity flag; percentage band;
      exact-value set membership and non-membership
      (EVALUATOR_CONDITION_NOT_SATISFIED, normal). A unit/currency/basis
      INCOMPATIBILITY is NOT in this scenario: E2-A 13 makes it malformed
      evaluator INPUT, and it is NON-STORE scenario NS-RQ-02 (5.7A) ->
      DENY + FAIL_CLOSED / EVALUATOR_FACTS_INVALID          (F-10.3-DC-01)
```

```text
WHAT IS DELIBERATELY *NOT* IN THIS LIST, and why. Mixed-path aggregation and the same-stage
multi-defect ordering cases used to appear in the prose list this table replaces. Their subject is
resolver ORCHESTRATION and the E2-A 15.5 total defect ORDER, not a stored shape - varying the stored
rows is the way those scenarios are DRIVEN, not what they are ABOUT. They are therefore NON-STORE
scenarios NS-AG-01..05 and NS-DO-01..06 (5.7A), with their parity obligation restated there in full.
Nothing was dropped by the move.
```

A-03 IS DECIDED AND WITHDRAWN (F-10.2). The earlier draft of this section left A-03's class,
storability, expected reason code and parity obligation conditional on reading the implemented
kernel later. That deferral is withdrawn: the question was always answerable from rules E2-A already
stated, and it is now answered there.

```text
DECISION: the residual state is UNREACHABLE, on every provider. E2-A 11.4a proves, from the 11.4
asserted-interval rule and the 11.2 EFFECTIVE predicate, that once the duplicate-start,
nonsensical-interval and explicit-overlap conditions have passed, asserted_effective_to(V) is
non-null and <= next_start(V) for every version with a successor - so a version that is effective at
an instant strictly bounds that instant below every later version's start, and AT MOST ONE version
of a current asserted lineage can be EFFECTIVE at any instant. Read the theorem there; it is short.

CONSEQUENCES HERE, all normative:
  - there is NO storable state to seed, so A-03 is REMOVED from this manifest, from the parity
    corpus, from the DEFECT VISIBILITY block of section 9 and from the fixture counts;
  - A-03 is NOT class B2 either. B2 is about a STORE's structural rejection, and nothing here is
    rejected by the schema - the state simply cannot be composed at all, by anyone;
  - the E2-A 11.6 residual clause is NOT deleted. It is retained as a defensive kernel invariant and
    verified as pure-kernel self-check NS-K-01 (section 5.7A), with three executable parts;
  - the reason code is settled NORMATIVELY rather than by observation:
    AUTHORITY_VERSION_AMBIGUOUS, per E2-A 11.4a;
  - AUTHORITY_VERSION_AMBIGUOUS therefore joins the justified parity-exclusion list below as
    KERNEL-INTERNAL - excluded because no provider can present the state, never because the state
    would be tolerated;
  - the ID A-03 is retired and must not be reused.
```

A-12 IS DECIDED AND WITHDRAWN (F-10.3a). A-12 was classified class A - a PERSISTABLE SEMANTIC
CONTRADICTION - and carried class A's defining obligation to store a raw CONTRADICTORY state and
read it back. There is no contradictory state to store. Its rows are valid, and E2-A 11.5 says so in
terms: a temporal gap is VALID lineage, not corruption.

```text
DECISION: A-12's subject is the RESOLVER, not the store. E2-A 11.5's deliberate asymmetry says that
when the REQUESTED authority_code has no grant-eligible-by-lineage version at as_of - whether
because its lineage has not started, has ended, or sits in a VALID GAP - the question itself cannot
be established, so the answer is DENY + FAIL_CLOSED / AUTHORITY_CODE_NOT_CONFIGURED rather than the
ordinary nonqualification the other three families produce. Every row read to reach that answer is
well formed. What is being tested is the kernel's as_of evaluation over VALID lineage.

CONSEQUENCES HERE, all normative:
  - A-12 is REMOVED from this manifest, from the class A counts and from the class A block of the
    DEFECT VISIBILITY list in section 9. Its ID is retired and must not be reused;
  - NOTHING ELSE about it changes. The obligation moves INTACT to NON-STORE scenario NS-RS-01
    (5.7A): the same seeded VALID rows, the same DENY + FAIL_CLOSED, the same
    AUTHORITY_CODE_NOT_CONFIGURED, the same E2-A 16.4 evidence, and the same FULL PostgreSQL parity
    between the reference-backed and PostgreSQL-backed compositions;
  - AUTHORITY_CODE_NOT_CONFIGURED therefore does NOT join the justified parity-exclusion list. It
    remains parity-covered, now through NS-RS-01. A reviewer finding that code missing from the
    parity corpus has found a real defect, not a consequence of this move;
  - NS-RS-01's PG DATA column is YES - valid authority rows are stored and read to drive it - while
    its STORE-STATE SUBJECT column is NO. That pair of answers is the whole point of the split, and
    A-12 is the worked example of why one column could not carry both facts;
  - the E2-A 11.5 asymmetry itself is UNCHANGED and must not be softened. Reclassifying where the
    scenario is proved is verification placement, exactly as class B1 exclusion is; it is not a
    licence to make the requested authority behave like the other three families.
```

#### Class B1 records — structurally rejected, but provable directly against E2-A

Shared obligations, stated once:

```text
REQUIRED POSTGRESQL TEST   §9 STORAGE INTEGRITY - CLASS B1 STRUCTURAL REJECTION: the INSERT FAILS,
                           and the test names the constraint that rejected it. Run against the
                           MIGRATED SCHEMA EXACTLY AS SHIPPED - never with a constraint disabled,
                           deferred, dropped or ALTERed in a fixture.
PG PARITY REQUIRED         NO, by construction - no conforming implementation of this schema can
                           return a row the schema forbids storing. The exclusion is recorded in the
                           acceptance record's verification-class manifest.
REQUIRED E2-A TEST         the NAMED case in E2-A §18 DIRECT E2-A MALFORMED-INPUT COVERAGE, executed
                           (not skipped, not xfailed) at the BOUNDARY named per fixture below. A
                           test that exercises a different boundary does NOT discharge this.
```

```text
ID     FIXTURE                      REJECTED BY (5.6)          E2-A BOUNDARY + EXPECTED RESULT
B1-01  two version records sharing  unique identity/version    PURE KERNEL. versions[] is a LIST
       one object_version within    key per family             (E2-A 9.3.2), so two entries with one
       one object's material                                   object_version are constructible.
                                                               DENY + FAIL_CLOSED
                                                               AUTHORITY_LINEAGE_CONTRADICTORY
                                                               (E2-A 9.3.3, 11.6)
B1-02  assignment version carrying  person XOR position        PURE KERNEL, stage S7. person_id and
       BOTH person_id and           CHECK                      position_id are BOTH DTO-optional
       position_id                                             (E2-A 9.3.4) precisely so this is
                                                               constructible.
                                                               DENY + FAIL_CLOSED
                                                               ASSIGNMENT_TARGET_INVALID (I-4)
B1-03  assignment version carrying  person XOR position        PURE KERNEL, stage S7.
       NEITHER target               CHECK                      DENY + FAIL_CLOSED
                                                               ASSIGNMENT_TARGET_INVALID (I-4)
B1-04  declared_effective_to <      single-row interval        PURE KERNEL, the 11.4 NONSENSICAL
       effective_from               CHECK                      DECLARED INTERVAL pre-check.
                                                               DENY + FAIL_CLOSED
                                                               AUTHORITY_LINEAGE_CONTRADICTORY (I-6)
B1-05  declared_effective_to ==     single-row interval        PURE KERNEL, same pre-check.
       effective_from (the empty    CHECK                      DENY + FAIL_CLOSED
       interval)                                               AUTHORITY_LINEAGE_CONTRADICTORY (I-6)
B1-06  a version record with NO     NOT NULL on                DTO / PORT WELL-FORMEDNESS. This is a
       effective_from               effective_from             DTO-REQUIRED field (E2-A 9.3.4): the
                                                               material cannot be constructed, the
                                                               port surfaces ill-formed material, and
                                                               the resolution is DENY + FAIL_CLOSED
                                                               AUTHORITY_CONFIGURATION_UNAVAILABLE
                                                               (E2-A 9.3.3). EXPLICITLY NOT a kernel
                                                               fixture, and NO new reason code is
                                                               invented for it
B1-07  a version record with NO     NOT NULL on active_flag    DTO / PORT WELL-FORMEDNESS, exactly as
       active_flag                                             B1-06.
                                                               DENY + FAIL_CLOSED
                                                               AUTHORITY_CONFIGURATION_UNAVAILABLE
B1-08a a version record with NO     NOT NULL on published_at   PURE KERNEL. These provenance fields
       published_at                                            are DTO-OPTIONAL and kernel-validated
                                                               (E2-A 9.3.4) because E2-A 11.6/11.7
                                                               ALREADY classify their absence.
                                                               E2-A fixture
                                                               PROVENANCE-ABSENT-PUBLISHED-AT.
                                                               DENY + FAIL_CLOSED
                                                               PUBLICATION_PROVENANCE_INVALID
B1-08b a retraction record with NO  NOT NULL on retracted_at   PURE KERNEL, as B1-08a. E2-A fixture
       retracted_at                                            PROVENANCE-ABSENT-RETRACTED-AT.
                                                               DENY + FAIL_CLOSED
                                                               PUBLICATION_PROVENANCE_INVALID
B1-09a a published version (and,    NOT NULL on provenance     PURE KERNEL. E2-A 9.3.4 keeps
       companion case, a retraction type                       publication_reference_type both
       assertion) whose publication                            OPTIONAL and OPEN precisely so an
       _reference_type is ABSENT                               ABSENT type is constructible and
       ALTOGETHER, with the other                              reaches the kernel. E2-A fixture
       provenance fields present                               PROVENANCE-ABSENT-TYPE (E2-A §18),
       and well formed                                         MANDATORY and EXECUTING.
                                                               DENY + FAIL_CLOSED
                                                               PUBLICATION_PROVENANCE_INVALID,
                                                               with ordinary deterministic failure
                                                               evidence (E2-A 16.4) and ordinary
                                                               15.5 defect ordering.
                                                               THIS IS THE F-10.1 CLOSURE: it is
                                                               NOT discharged by B1-10, because a
                                                               kernel that only checks membership
                                                               in the two defined values passes
                                                               B1-10 and fails this one. It is NOT
                                                               a DTO fixture and must not be
                                                               relocated to DTO-only rejection.
B1-09b a version record with NO     NOT NULL on provenance id  PURE KERNEL, as B1-09a. E2-A fixture
       publication_reference_id,                               PROVENANCE-ABSENT-REFERENCE-ID.
       with a valid type present                               DENY + FAIL_CLOSED
                                                               PUBLICATION_PROVENANCE_INVALID
B1-10  publication_reference_type   closed enum CHECK          PURE KERNEL. The DTO carries this as
       PRESENT but outside the two                             an OPEN value (E2-A 9.3.4), not a
       defined values                                          language-level closed enum, precisely
                                                               so an unknown value is constructible.
                                                               E2-A fixture
                                                               PROVENANCE-UNKNOWN-TYPE.
                                                               DENY + FAIL_CLOSED
                                                               PUBLICATION_PROVENANCE_INVALID
```

**Why the provenance entries are split one shape per ID (F-10.1).** The previous `B1-08` and
`B1-09` each grouped two malformed shapes, and the promised "named, executed E2-A test" for the pair
existed for only one shape of each — the absent `publication_reference_type` had none at all. A
manifest ID that covers two shapes cannot be checked mechanically against a test, so the grouping
itself was the defect. Every B1 ID now names exactly one shape and exactly one E2-A fixture, and
section 9's conformance test asserts that mapping is one-to-one in both directions.

**Why B1-06 and B1-07 differ from B1-08a to B1-10**, recorded because the asymmetry looks arbitrary
until it is explained and a later agent will otherwise "tidy" it: E2-A already assigns a semantic
classification to absent or unknown *provenance* (11.6, 11.7, 11.8.3), so those fields must be
DTO-optional and the kernel must classify them. E2-A assigns **no** semantic classification to a
version lacking `effective_from` or `active_flag`, because such a record is not a published version
at all — and inventing `AUTHORITY_EFFECTIVE_FROM_MISSING` to mirror a `NOT NULL` constraint is
exactly the fabrication E2-A 9.7 prohibits. Their absence is therefore a well-formedness failure at
the port, surfacing through the reason code that already exists for a provider that cannot supply
conforming material.

#### Class B2 records — structurally rejected, with NO provider-neutral counterpart

Shared obligations, stated once:

```text
REQUIRED POSTGRESQL TEST   §9 STORAGE INTEGRITY - CLASS B2 STRUCTURAL REJECTION: the INSERT FAILS,
                           naming the foreign key that rejected it, against the shipped schema.
REQUIRED E2-A TEST         NONE, AND NONE MAY BE FABRICATED. E2-A §18 asserts these fixtures are
                           ABSENT from its corpus, so a later agent cannot add an invented one.
PG PARITY REQUIRED         NO.
E2-A MANIFEST              EXCLUDED - these appear in no E2-A semantic fixture or parity manifest.
```

```text
ID     FIXTURE                                    REJECTED BY (5.6)
B2-01  a version row whose stable-identity        FK from every version row to its stable identity
       PARENT ROW does not exist                  row
B2-02  a retraction row whose object stable-      FK from a retraction row to the stable identity of
       identity PARENT ROW does not exist         the object it retracts
B2-03  a rule/assignment version referencing a    FK from rule/assignment version rows to the STABLE
       role/authority STABLE IDENTITY ROW that    identity of the role/authority they reference
       does not exist

RATIONALE (mandatory under E2-A 9.7 class B2 requirement 4; this is the whole justification and must
not be paraphrased away):

    All three constraints exist ONLY because section 5.1 represents stable object identity as a
    SEPARATE PHYSICAL ROW from its versions. That split is a persistence representation choice. The
    provider-neutral contract does not share it:

    - E2-A 9.3.2 carries object_id on the LineageMaterial CONTAINER and groups versions[] and
      retraction_assertions[] UNDER it. A version or a retraction assertion therefore CANNOT be
      provider-neutrally orphaned from its object - the contract has no field in which that state
      could be expressed at all. B2-01 and B2-02 have no counterpart, full stop.
    - E2-A 9.3.2 further states that get_lineage for an object identity the provider holds nothing
      for returns COMPLETE material with an EMPTY versions[]. So a reference to a stable identity
      ROW that does not exist DECODES, at the provider-neutral boundary, to exactly the same state
      as a reference to a stable identity that exists and carries no material - which is fixture
      A-11, already owed FULL parity and already carrying a direct E2-A test
      (AUTHORITY_REFERENCE_DANGLING). B2-03's counterpart does not go untested; it COLLAPSES ONTO an
      existing class A fixture, so there is no DISTINCT malformed state left to place.

    Applying E2-A 9.7's deciding test: could any conforming provider, using only the 9.3.2/9.3.4
    fields and without inventing a persistence-specific field, present a state the kernel would
    classify DIFFERENTLY from an already-classified state? For all three: NO. Hence B2, not B1.

    What these foreign keys protect is this store's own parent/child referential integrity - a real
    and worthwhile invariant, worth a rejection test, but not a semantic rule of E2-A.

RE-EXAMINATION TRIGGER. If a future change to E2-A 9.3.2 or 9.3.4 ever makes one of these states
expressible - for example by moving object_id onto each version record, or by adding an explicit
"identity exists" signal to the port - that fixture STOPS being class B2 and becomes class B1 the
same day, acquiring a mandatory, named, executed E2-A test. A B2 classification is only ever as
valid as the DTO shape it rests on.
```

#### Not negative fixtures, and therefore not class-assigned

```text
structural invariant          "stable identity never versioned" and "published version
assertions                    immutability including active_flag" are invariant assertions, not
                              malformed-input fixtures (E2-A §18).
VALID-SHAPE PARITY            V-01 to V-12, tabulated after the class A records. Their subject IS
SCENARIOS                     authority-store state, but that state is VALID, so there is nothing
                              to classify as malformed. They carry no class label, are owed FULL
                              parity, and are the third group of the section 9 partition.
```

Note that `INTERNAL_CONTRACT_VIOLATION` and the withdrawn A-03 invariant are no longer parked here
as unclassified leftovers. Both are negative scenarios with real executable obligations, and both
now sit in section 5.7A as `NS-K-02` and `NS-K-01` respectively.

#### Consequences that must be honoured elsewhere in this document

```text
- The PostgreSQL parity corpus (section 9) covers every CLASS A fixture, every VALID-SHAPE scenario
  V-01 to V-12, and every 5.7A NON-STORE scenario whose parity column says YES - and NO class B1 or
  B2 fixture. The corpus therefore has THREE parts with different subjects: the class A part varies
  the MALFORMED stored state; the V part varies the VALID stored state; and the non-store part
  varies a provider, request, clock, orchestration or evidence condition while both compositions use
  the same synthetic actor/HR providers. Before F-10.3a this was described as "exactly two parts",
  with the V part folded into class A - which is how valid closure shapes came to carry a
  negative-fixture label.
- "Every fail-closed reason code" is NOT a parity obligation as stated bare, and that bare phrasing
  was part of the F-10 defect. The obligation is: the combined corpus (class A + the parity-YES
  entries of 5.7A) covers every fail-closed reason code of E2-A 14.3 EXCEPT those on an explicit,
  justified exclusion list, where each excluded code must be justified as either (i) CLASS B1/B2 -
  EVERY shape producing it is structurally rejected by 5.6 (name the constraint and, for B1, the
  covering E2-A test and its boundary), or (ii) KERNEL-INTERNAL - it is a kernel self-check or a
  state no provider can present, rather than a store-supplied or provider-supplied one (name the
  E2-A test / 5.7A scenario). The exclusion list is now CLOSED and unconditional:
      ASSIGNMENT_TARGET_INVALID     class B1, person/position XOR CHECK (B1-02, B1-03), covered by
                                    E2-A fixtures ASSIGNMENT-TARGET-BOTH / -NEITHER at stage S7
      AUTHORITY_VERSION_AMBIGUOUS   kernel-internal: proved unreachable from any provider input by
                                    E2-A 11.4a; covered by 5.7A scenario NS-K-01
      INTERNAL_CONTRACT_VIOLATION   kernel-internal self-check; covered by 5.7A scenario NS-K-02
  Nothing on this list is conditional on what the implemented kernel turns out to do. A test asserts
  the implemented exclusion list is exactly this list, so it can neither grow silently nor be padded
  to excuse a missing scenario.
- AUTHORITY_CONFIGURATION_UNAVAILABLE is NOT on that exclusion list. It is not reachable through any
  class A fixture either - the induced-read-failure shape that used to carry it (former A-16) is now
  the NON-STORE scenario NS-PT-01, whose parity column is YES, so the code stays in the combined
  parity corpus through that route. B1-06 and B1-07 also produce it at the DTO/port boundary, and
  neither of those routes removes it from parity.
- Several codes remain in parity through some other route even though SOME of their shapes are B1 -
  notably AUTHORITY_LINEAGE_CONTRADICTORY (class A via overlap, duplicate start, retraction and
  correction defects), PUBLICATION_PROVENANCE_INVALID (class A via impossible recorded timestamps)
  and AUTHORITY_CONFIGURATION_UNAVAILABLE (5.7A via NS-PT-01). Do NOT read a single B1 shape as
  removing its reason code from parity.
- The class split is CLASSIFIED PER SHAPE, never per reason code, and never per table.
- SCOPE IS CHECKED BEFORE CLASS. Run the 5.7 entry test first, BOTH questions. An item whose
  subject is a provider, a request input, orchestration, evidence handling or a pure-kernel
  invariant is a 5.7A scenario and gets no class; forcing a class onto it produces an "N/A"
  storability cell and an unexecutable class-A storage obligation, which is the F-10.3 defect. An
  item whose stored state is VALID is a V-scenario (or, when its subject is a seam, a 5.7A scenario)
  and likewise gets no class; forcing a class onto it produces an honest "PG may store: YES" beside
  a class A label whose defining obligation - store a CONTRADICTORY state - has no contradiction to
  store, which is the F-10.3a defect. A fail-closed OUTCOME never by itself makes an item a negative
  fixture: A-12 produced AUTHORITY_CODE_NOT_CONFIGURED from entirely valid rows.
- If an implementation adds a structural constraint not listed in 5.6, it must state which class it
  moves each affected fixture into and why - and if that fixture is class A above, the constraint is
  forbidden, not the classification.
- If an implementation REMOVES a 5.6 constraint, the affected fixture moves from B1 or B2 into class
  A and acquires a full parity obligation. Neither direction is an implementation preference; both
  are reconciliation findings against 5.6/5.7.
- A NON-STORE scenario never becomes class A merely because a test runs it against the
  PostgreSQL-backed composition, and never becomes class A merely because it READS valid stored
  rows. Both facts are recorded explicitly, in two separate 5.7A columns, because one column could
  not carry them: PG DATA answers "does this scenario need authority rows stored and read to reach
  its condition?", and STORE-STATE SUBJECT answers "is the malformed or negative subject under test
  itself stored authority state?". NS-RS-01 answers YES then NO; NS-PT-01 answers YES then NO;
  NS-AP-01 answers NO then NO. STORE-STATE SUBJECT is NO for every row of 5.7A by construction -
  that is the entry criterion - and section 9 asserts it, so a YES appearing there means a fixture
  has been filed in the wrong table. The distinguishing question is always "is there a raw stored
  MALFORMED shape whose acceptance or rejection is the point?", never "does a PostgreSQL object
  appear anywhere in the test".
```

### 5.7A NON-STORE RESOLVER / PROVIDER CONFORMANCE SCENARIOS (F-10.3, extended by F-10.3b)

Section 5.7 classifies negative fixtures whose subject is MALFORMED stored authority data, and
tabulates the VALID stored shapes (V-01 to V-12) alongside them. This section is the **binding,
TOTAL** table for every other negative or conformance scenario the E2 pair requires: those whose
subject is a **provider**, a **request input**, **resolver orchestration or the resolution clock**,
**deterministic defect ordering**, **evidence**, or a **pure-kernel invariant**. They carry **no
A/B1/B2 class**, because there is no malformed stored shape for the store to accept or reject — and
that absence of a class is the *only* thing their exclusion from 5.7 means.

```text
THIS IS NOT A LOWER TIER OF OBLIGATION. Every scenario below carries an explicit executable test
obligation at an ALREADY-DEFINED seam, an expected outcome / resolution_status / reason / evidence
where one is meaningful, and an explicit parity statement. Nothing that was previously required of
former fixtures A-12, A-16, A-18, A-19 and A-20 has been dropped; it has been restated where it is
actually executable.

TOTALITY (F-10.3b). This table is total over the scenarios the CURRENT normative text of E2-A and
this document already makes MANDATORY and whose malformed or negative subject is not stored
authority state. It was not, before this correction: twenty scenarios covered the actor, HR,
request, port and kernel-invariant seams, while obligations E2-A 18 and section 9 state in the
imperative - the server-captured live as_of and the single-clock rule, the prohibition on a
caller-selected as_of or recorded-time cutoff, the client-supplied person_id trust boundary,
synthetic-provider production unreachability, the provider-supplies-facts-not-judgements rule,
multiple legitimate qualifying paths, relevant-corrupt-not-masked-by-a-valid-path, result-level
reason selection, the total defect ORDER cases, and the complete / nonqualifying / partial evidence
and evidence-ordering cases - carried no scenario ID and sat in neither table. They do now.

This is an ID-assignment and reconciliation exercise, NOT a new requirement set. Every scenario
below already existed as an imperative obligation somewhere in E2-A 18 or section 9; each row cites
where. No speculative or defensive scenario has been added to lengthen the table, and no optional
completeness improvement has been converted into a normative requirement.

SEAMS. Every scenario sits on an interface E2-A already defines: actor->person mapping/provider
validity (E2-A 9.1); HR provider availability / freshness / ambiguity (E2-A 9.2); the authority
configuration port's read/transport behaviour and provider fact-fidelity (E2-A 9.3.1, 9.3.3, 9.5);
provider reachability and composition (E2-A 9.6); request/scope/evaluator input (E2-A 12, 13);
resolver orchestration, the resolution clock and the two entry points (E2-A 10, 11.1, 11.5, 11.8);
aggregation, relevance and the TOTAL defect order (E2-A 15); the evidence contract (E2-A 16); and
pure-kernel invariants (E2-A 11, 15.5). NO NEW PROVIDER SURFACE MAY BE INVENTED to classify a
scenario. If a future scenario does not sit on one of these, that is a contract gap to raise against
E2-A, not a licence to add a seam here.

COLUMN MEANINGS. The first two used to be one column, and conflating them is how a scenario that
merely READS PostgreSQL rows could be mistaken for one whose malformed SUBJECT is stored state - the
F-10.3b imprecision. THEY ARE INDEPENDENT DIMENSIONS: no value of one constrains the value of the
other, and neither may be inferred from the other (F-10.3-DC-02).
  PG-DATA            does the scenario need authority-store rows to be STORED AND READ in order to
                     reach its condition at all? YES or NO - never blank. YES does not imply
                     anything is malformed: NS-RS-01, NS-RQ-01 and every NS-AG/NS-DO/NS-EV row read
                     real rows, and in NS-RS-01, NS-RQ-01/02 and the NS-EV rows those rows are
                     entirely VALID. Nor does YES imply that everything read is valid: NS-PR-03,
                     NS-AG-03, NS-AG-04 and NS-DO-01..05 REQUIRE, by their own defined semantics,
                     ALREADY-CLASSIFIED class A malformed rows as CONTROLLED INGREDIENTS.
  SUBJ               is the malformed / negative SUBJECT under test itself authority-store state?
                     By construction this is NO for every row in this table - it is the 5.7A entry
                     criterion - and section 9 asserts it. A YES here means the item was filed in
                     the wrong table and belongs in 5.7. It is written out per row rather than
                     stated once, because the one thing this correction is meant to prevent is a
                     later reader inferring the answer from the PG-DATA column.
                     SUBJ = NO MEANS: the malformed or negative condition THE SCENARIO IS TESTING is
                     not authority-store state. IT DOES NOT MEAN: every authority-store row
                     participating in the test is valid. A class A malformed row used as an
                     INGREDIENT keeps its own A/B1/B2 classification and discharges its own 5.7
                     storability, reason-code and parity obligations there; its presence does NOT
                     convert the enclosing resolver / provider / orchestration scenario into an
                     A/B1/B2 scenario. A non-store scenario must NOT: (1) treat its malformed store
                     ingredient as the scenario's actual non-store SUBJECT; (2) introduce a NEW
                     malformed persisted shape that has no A/B1/B2 classification; (3) use this
                     table as an escape hatch from the 5.7 authority-store fixture manifest; or
                     (4) suppress or normalize the malformed ingredient contrary to the existing
                     raw-discovery and fail-closed rules.                        (F-10.3-DC-02)
  PARITY             is AGREEMENT between two named compositions required? Where YES, the two
                     compositions are: (i) kernel + E2-A reference/in-memory authority provider +
                     synthetic actor/HR providers; and (ii) kernel + E2-B PostgreSQL authority
                     provider + THE SAME synthetic actor/HR providers. The identical driving
                     condition is applied to both, and they must agree on outcome,
                     resolution_status, result_level_reason, all three evidence collections and
                     their ordering, and established_state - exactly the E2-A 16 contract.
                     PARITY = NO never means "tested once and loosely". It means an AGREEMENT test
                     has no meaningful second side - a surface/structural assertion, or a state no
                     provider can present - and each such row says which of those it is and where
                     it is asserted instead.
```

#### Actor → canonical person seam (E2-A 9.1, 9.6)

```text
ID         CONDITION / INPUT           PG-DATA  SUBJ  EXPECTED RESULT                        PARITY
NS-AP-01   the actor-person provider   NO       NO    DENY + FAIL_CLOSED,                    YES
           returns NO mapping for the                 ACTOR_PERSON_MAPPING_MISSING, at stage
           authenticated actor at                     S1
           as_of
NS-AP-02   the provider returns MORE   NO       NO    DENY + FAIL_CLOSED,                    YES
           THAN ONE mapping. One must                 ACTOR_PERSON_MAPPING_AMBIGUOUS, at
           NEVER be picked                            stage S1
NS-AP-03   no actor-person provider is NO       NO    DENY + FAIL_CLOSED,                    YES
           bound in the composition                   ACTOR_PERSON_PROVIDER_NOT_CONFIGURED,
           (E2-A 9.6)                                 at S1
NS-AP-04   a caller supplies a         NO       NO    the supplied value influences NOTHING: NO
           person_id (or any                          identity comes only from the
           client-controlled identity                 authenticated actor through the port
           hint) alongside the request

NS-AP-01..03 all carry E2-A 16.4 partial evidence: established items only, the exact failed stage,
the deterministic reason, and NO fabricated object/version pairs.
EXECUTABLE OBLIGATION, NS-AP-01..03: an E2-A test (§18 ACTOR BOUNDARY) driving the reference
composition, and - because PARITY is YES - the same declarative condition driven through the
PostgreSQL-backed composition in §9, asserting identical results.
EXECUTABLE OBLIGATION, NS-AP-04: the trust-boundary assertion E2-A §18 ACTOR BOUNDARY already
states ("a test proving no client-supplied person_id can influence the identity authorized"),
asserted TWICE and independently - once against the E2-A kernel/entry surface, and once against the
WIRED path in §9 SECURITY / BOUNDARY, because wiring is exactly where such a parameter could be
reintroduced. PARITY is NO because this is a surface/trust assertion with no second side to compare
outcomes against, not because one side is exempt.
RATIONALE FOR BEING OUTSIDE A/B1/B2: the subject is the actor-person port's own response, or the
identity trust boundary in front of it. No authority-store row expresses "the actor has no canonical
person" or "a caller passed an identity hint"; asking whether PostgreSQL can store either is not a
meaningful question.
```

#### Canonical HR reference seam (E2-A 9.2, 9.6)

```text
ID         CONDITION / INPUT           PG-DATA  SUBJ  EXPECTED RESULT                        PARITY
NS-HR-01   no HR provider is bound     NO       NO    HR_REFERENCE_PROVIDER_NOT_CONFIGURED   YES
           (E2-A 9.6)
NS-HR-02   the HR port is unavailable  NO       NO    HR_REFERENCE_UNAVAILABLE               YES
           / raises
NS-HR-03   canonical_snapshot_at is    NO       NO    HR_REFERENCE_STALE                     YES
           older than the configured
           staleness threshold (the
           threshold VALUE stays a
           deferred policy parameter -
           the test supplies one, it
           invents no default)
NS-HR-04   get_employment_state        NO       NO    EMPLOYMENT_STATE_MISSING               YES
           returns MISSING
NS-HR-05   get_employment_state is     NO       NO    EMPLOYMENT_STATE_AMBIGUOUS             YES
           AMBIGUOUS
NS-HR-06   get_position returns        YES      NO    POSITION_STATE_MISSING                 YES
           MISSING
NS-HR-07   get_position is AMBIGUOUS   YES      NO    POSITION_STATE_AMBIGUOUS               YES
NS-HR-08   get_incumbency returns no   YES      NO    INCUMBENCY_MISSING                     YES
           incumbent at as_of for a
           position-based assignment
NS-HR-09   get_incumbency returns more YES      NO    INCUMBENCY_AMBIGUOUS                   YES
           than one incumbent at as_of
NS-HR-10   get_org_unit returns        YES      NO    ORG_UNIT_STATE_MISSING                 YES
           MISSING where scope
           evaluation needs it
NS-HR-11   get_org_unit is AMBIGUOUS   YES      NO    ORG_UNIT_STATE_AMBIGUOUS               YES
NS-HR-12   organisation ancestry       YES      NO    ORG_HIERARCHY_UNRESOLVABLE             YES
           cannot be resolved: cycle,
           depth exhaustion, or a
           missing link in the chain

All twelve are DENY + FAIL_CLOSED, with E2-A 16.4 partial evidence and 15.5 defect ordering. Stages,
per E2-A 12.2: NS-HR-04/05 at S2; NS-HR-06 to NS-HR-09 at S7; NS-HR-10 to NS-HR-12 at S8;
NS-HR-01 to NS-HR-03 at whichever stage first consults the HR port in the scenario, recorded
explicitly by the test rather than assumed.
PG-DATA, and why it is not uniform (F-10.3b): NS-HR-06 to NS-HR-12 fail at S7/S8, which the
resolution can only REACH once a VALID rule and assignment have been stored and read, so the
PostgreSQL-backed composition genuinely stores and reads authority rows for them. NS-HR-01 to
NS-HR-05 fail at or before S2, ahead of any authority read. In every one of the twelve the rows, if
any, are VALID and the malformed subject is the HR port's answer - hence SUBJ = NO throughout. Where
a test chooses to drive NS-HR-01..03 at a later stage instead, it records that choice and its
PG-DATA consequence explicitly, rather than leaving the column to be inferred.
EXECUTABLE OBLIGATION: E2-A tests in §18 (ACTOR BOUNDARY, POSITION ASSIGNMENT, and the ancestry
cases of SCOPE AND COMPOSITION) through the reference composition, plus the same conditions through
the PostgreSQL-backed composition in §9 asserting identical results.
RATIONALE FOR BEING OUTSIDE A/B1/B2: the subject is canonical HR/organisation state supplied by the
HR port. E2-B persists NO HR data at all (section 8 prohibits it), so there is no raw authority-store
shape to store or reject.
NOTE ON NS-HR-08/09: a position ASSIGNMENT VERSION is authority-store data and its malformed shapes
are class B1 (B1-02, B1-03); what is non-store here is the INCUMBENCY answer the HR port gives about
that position. Do not conflate the two.
```

#### Request / scope / evaluator input seam (E2-A 12, 13)

```text
ID         CONDITION / INPUT           PG-DATA  SUBJ  EXPECTED RESULT                        PARITY
NS-RQ-01   a non-GLOBAL scope operand  YES      NO    DENY + FAIL_CLOSED,                    YES
           on a well-formed, VALID                    SCOPE_CONTEXT_MISSING, at stage S8
           STORED rule/assignment
           requires a canonical scope
           the supplied
           business_context does not
           carry
NS-RQ-02   a business fact the VALID   YES      NO    DENY + FAIL_CLOSED,                    YES
           stored evaluator requires                  EVALUATOR_FACTS_INVALID, at stage S9 -
           is ABSENT from, of the                     including the unit/currency/basis case,
           WRONG TYPE in, or supplied                 which is malformed evaluator INPUT and
           by the business_context in                 is NEVER reported as
           a UNIT / CURRENCY / BASIS                  EVALUATOR_CONDITION_NOT_SATISFIED
           INCOMPATIBLE with the one
           the stored payload declares

PG-DATA is YES for both, and that is the point of the split introduced by F-10.3b: a VALID stored
rule/assignment and a VALID stored evaluator must exist and be read for the resolution to reach S8
and S9 at all. The rows are stored normally and are not what the scenario varies, so SUBJ is NO.
NS-RQ-02 CARRIES THREE MALFORMED REQUEST CONDITIONS, NOT TWO (F-10.3-DC-01): the required business
fact ABSENT; the required business fact of the WRONG TYPE; and the required business fact supplied
in a UNIT, CURRENCY or BASIS INCOMPATIBLE with the one the VALID stored payload declares. E2-A 13
states that units, currency and basis are explicit, must match the supplied fact, and are never
coerced or converted implicitly - so an incompatibility is malformed evaluator INPUT, not a declared
comparison that legitimately returned false. All three produce DENY + FAIL_CLOSED /
EVALUATOR_FACTS_INVALID at stage S9 with ordinary E2-A 16.4 deterministic failure evidence, and none
of them is EVALUATOR_CONDITION_NOT_SATISFIED. The existing ID was EXTENDED rather than split, so the
non-store count is unchanged at forty-six.
EXECUTABLE OBLIGATION: E2-A tests in §18 (SCOPE AND COMPOSITION; EVALUATORS) plus the same
conditions through the PostgreSQL-backed composition in §9.
RATIONALE FOR BEING OUTSIDE A/B1/B2: the defect is in the CALLER'S REQUEST, not in stored
configuration. Contrast the genuinely malformed stored-shape neighbours, which ARE class A: an
unsupported scope_type VALUE on a stored rule is A-15, an unknown evaluator TYPE is A-13 and a
malformed evaluator PAYLOAD is A-14. Contrast also the VALID stored neighbours V-10 to V-12, where
the operand and the evaluator are well formed AND the request is complete - which for V-12 includes
the supplied facts being unit/currency/basis-COMPATIBLE - and the legitimate non-match is an
ordinary RESOLVED nonqualification.
```

#### Authority configuration PORT and provider-fidelity seam (E2-A 9.3.1, 9.3.3, 9.5, 9.6)

```text
ID         CONDITION / INPUT           PG-DATA  SUBJ  EXPECTED RESULT                        PARITY
NS-PT-01   the authority configuration YES      NO    DENY + FAIL_CLOSED,                    YES
           port fails as a PORT rather                AUTHORITY_CONFIGURATION_UNAVAILABLE -
           than returning bad data: a                 NEVER an empty candidate set, NEVER
           raised error, a timeout,                   DENY + RESOLVED
           completeness = UNAVAILABLE,
           or a truncated read that
           must not be reported
           COMPLETE
NS-PR-01   the synthetic/reference     NO       NO    they are UNREACHABLE: not importable   NO
           actor, person and HR                       from and not reachable through any
           providers, and any                         production module or the production
           production import path or                  wiring, and no env var, settings flag,
           configuration switch that                  feature toggle or dependency override
           could reach one                            selects one
NS-PR-02   the PRODUCTION composition  NO       NO    it either REFUSES TO COMPOSE or        NO
           is exercised with no                       returns DENY + FAIL_CLOSED with
           authoritative actor-person                 ACTOR_PERSON_PROVIDER_NOT_CONFIGURED /
           / HR provider available                    HR_REFERENCE_PROVIDER_NOT_CONFIGURED
                                                      on every call - whichever option was
                                                      chosen, asserted explicitly
NS-PR-03   a provider that supplies    YES      NO    the conformance test REJECTS such a    NO
           JUDGEMENTS instead of                      provider. Given lineage material
           FACTS: prefiltering to the                 containing duplicate effective
           effective row, computing                   versions, an explicit overlap, a
           closure, effectiveness,                    dangling retraction, an unretracted
           ranking or deduplication,                  correction target and invalid
           or applying any excluded                   provenance, the kernel fails closed on
           discovery predicate                        each
           (retraction, effective
           time, active_flag, scope,
           parameter, provenance,
           latest version)

EXECUTABLE OBLIGATION, NS-PT-01, both sides:
  E2-A   §18 LINEAGE AND CLOSURE, final case: the reference provider returns
         completeness = UNAVAILABLE, and separately raises, and the resolution fails closed.
  E2-B   §9 induces the failure at the WIRED PostgreSQL read repository - a forced read error, a
         forced timeout, and a deliberately truncated read - and asserts the same code, and
         specifically that a truncated read is never reported as COMPLETE.
  PG-DATA is YES: the E2-B half runs against the wired PostgreSQL repository over ordinary VALID
  rows. Before F-10.3b this row read NO with a footnote explaining that it ran against PostgreSQL
  anyway; the two columns now say the two things separately, so no footnote is needed.
EXECUTABLE OBLIGATION, NS-PR-01: E2-A §18 SECURITY / BOUNDARY (reference/synthetic providers
unreachable from production runtime paths, E2-A 9.6) AND §9 RUNTIME WIRING / PROVIDER REACHABILITY
here. PARITY is NO because this is a structural reachability assertion - there is no resolution
outcome for two compositions to agree about - and it is asserted independently on both sides.
EXECUTABLE OBLIGATION, NS-PR-02: §9 RUNTIME WIRING / PROVIDER REACHABILITY and criterion 10.P. It is
distinct from NS-AP-03 / NS-HR-01, which assert the FAIL-CLOSED REASON CODE when a provider is
unbound in a test composition; NS-PR-02 asserts what the PRODUCTION composition does about it, which
may legitimately be to refuse to compose at all (section 5.3). PARITY is NO for the same reason.
EXECUTABLE OBLIGATION, NS-PR-03: E2-A §18 LINEAGE AND CLOSURE ("PROVIDER CANNOT HIDE A DEFECT") and
RAW DISCOVERY AND RETRACTION, plus §9 PROVIDER FIDELITY here, including the assertion that no
discovery query contains a NOT EXISTS over the retraction table. PARITY is NO in the AGREEMENT
sense: this is not one condition compared across two providers but the SAME conformance assertion
run independently against EACH provider, and both must pass. Note the deliberate division of labour:
NS-PR-03 proves the PROVIDER does not hide a defect; class A fixture A-17 and V-08 prove what the
KERNEL then does with the defect and with a valid retraction respectively.
RATIONALE FOR BEING OUTSIDE A/B1/B2: in none of the four is a malformed row the SUBJECT under test.
The subjects are the port's error propagation contract, provider reachability, production
composition behaviour, and provider fact-fidelity. NS-PT-01, NS-PR-01 and NS-PR-02 store and read no
malformed row at all. NS-PR-03 DOES, and legitimately (F-10.3-DC-02): its conformance condition is
defined over lineage material containing duplicate effective versions, an explicit overlap, a
dangling retraction, an unretracted correction target and invalid provenance - already-classified
class A shapes used as CONTROLLED INGREDIENTS, each keeping its own class and its own 5.7
obligations. What NS-PR-03 is ABOUT is whether the PROVIDER passes such material through as raw
FACTS instead of judging it away, which is not a question about whether this store can hold the
shape. The former A-16 recorded its own storability as "N/A" while
carrying a class A label whose defining obligation is "the INSERT succeeds and the rows read back
byte-identical" - an obligation with no malformed INSERT to perform.
```

#### Resolver orchestration, clock and entry-point seam (E2-A 10, 11.1, 11.5, 11.8)

```text
ID         CONDITION / INPUT           PG-DATA  SUBJ  EXPECTED RESULT                        PARITY
NS-RS-01   the REQUESTED               YES      NO    DENY + FAIL_CLOSED,                    YES
           authority_code has no                      AUTHORITY_CODE_NOT_CONFIGURED - E2-A
           grant-eligible-by-lineage                  11.5's deliberate asymmetry, never an
           version at as_of - lineage                 ordinary nonqualification and never
           not started, ended, or an                  reported as overlap or as a dangling
           as_of inside a VALID GAP.                  reference
           Every stored row is VALID.
           Replaces the withdrawn
           fixture A-12
NS-RS-02   one live resolution, with   YES      NO    exactly ONE server-captured instant    YES
           real I/O latency between                   governs every stage; no component
           port calls                                 consults a second clock
NS-RS-03   the two entry points'       NO       NO    resolve_current_authority exposes NO   NO
           parameter surfaces                         as_of and no recorded-time bound;
                                                      NEITHER operation exposes a
                                                      published_at cutoff / as-known-at
                                                      parameter; the historical resolver is
                                                      not a live authorization path
NS-RS-04   only the RECORDED           YES      NO    NOTHING changes: same outcome, same    YES
           timestamps of an otherwise                 resolution_status, same reason, same
           unchanged valid lineage are                path set. Recorded time is never a
           shifted, keeping them valid                lineage filter
           under E2-A 11.8.3

EXECUTABLE OBLIGATION, NS-RS-01: E2-A §18 LINEAGE AND CLOSURE, GAP BEHAVIOUR PER FAMILY - the
REQUESTED-authority branch specifically, distinguished there from the ASSIGNMENT_NOT_EFFECTIVE /
RULE_NOT_EFFECTIVE / ROLE_NOT_EFFECTIVE branches which are normal nonqualification and belong to
V-03 - plus, because PARITY is YES, the same VALID rows seeded in PostgreSQL and resolved through
the wired kernel in §9, asserting the identical code, evidence and ordering. This is the FULL
obligation A-12 carried, moved without subtraction.
EXECUTABLE OBLIGATION, NS-RS-02: E2-A §18 TEMPORAL ("one as_of governs everything - a test proving
no component consults a second clock"), and the same assertion through the PostgreSQL-backed
composition in §9, where real read latency between port calls makes a second clock actually
observable. This is the parity-relevant half of attack-surface item 5.
EXECUTABLE OBLIGATION, NS-RS-03: E2-A §18 ACTOR BOUNDARY and RECORDED TIME ("NO recorded-knowledge
replay"), plus §9 SECURITY / BOUNDARY here ("the current-authorization path still accepts no
caller-selected as_of after wiring"). PARITY is NO: it is a parameter-surface assertion with no
outcome to compare, asserted independently on both sides. A caller-selected as_of reaching a current
decision after wiring is attack-surface item 4 and is a blocking finding.
EXECUTABLE OBLIGATION, NS-RS-04: E2-A §18 RECORDED TIME ("published_at / retracted_at are NEVER used
as a lineage filter"), plus §9 PROVIDER FIDELITY here. Its sibling V-09 covers the RECONSTRUCTION
behaviour those same timestamps legitimately participate in; the two must not be collapsed, because
one asserts that recorded time changes nothing and the other asserts what business-effective time
correctly changes.
RATIONALE FOR BEING OUTSIDE A/B1/B2: in all four, every stored row is VALID. What is under test is
the resolver's evaluation at an as_of, the clock it uses, the parameters it exposes, and what it
refuses to treat as a filter. There is no malformed stored shape whose acceptance or rejection is
the point - which is precisely why A-12's class A label could never be discharged.
```

#### Aggregation, relevance and result-level reason seam (E2-A 15.1, 15.2, 15.3)

```text
ID         CONDITION / INPUT           PG-DATA  SUBJ  EXPECTED RESULT                        PARITY
NS-AG-01   two independently VALID     YES      NO    ALLOW + RESOLVED, BOTH paths retained  YES
           qualifying paths for one                   in deterministic order. Multiplicity
           request                                    is not ambiguity
NS-AG-02   one valid qualifying path   YES      NO    ALLOW + RESOLVED; the qualifying path  YES
           plus one                                   retained AND the nonqualifying path
           normally-nonqualifying path                retained in full under E2-A 16.3
NS-AG-03   one valid qualifying path   YES      NO    DENY + FAIL_CLOSED. The valid path     YES
           plus a RELEVANT corrupt                    does NOT rescue it; the qualifying
           object (a class A shape                    path's established evidence is still
           used as an ingredient)                     retained
NS-AG-04   an IRRELEVANT corrupt       YES      NO    first case: result UNAFFECTED (ALLOW,  YES
           object, provably irrelevant                or the ordinary denial). Companion
           by the identity-only tests                 case: DENY + FAIL_CLOSED
           of E2-A 15.2; and a
           companion in which the same
           object's irrelevance would
           depend on the defective
           field
NS-AG-05   candidate paths exist and   YES      NO    DENY + RESOLVED with the correct       YES
           none qualifies; and,                       result-level reason:
           separately, no assignment                  NO_CANDIDATE_ASSIGNMENT, a promoted
           candidate targets the                      single shared path-level reason, or
           person at all                              NO_QUALIFYING_PATH

EXECUTABLE OBLIGATION for all five: E2-A §18 MIXED PATHS AND AGGREGATION through the reference
composition, and the identical scenarios through the PostgreSQL-backed composition in §9, agreeing
on outcome, resolution_status, result_level_reason, all three evidence collections and their
ordering, and established_state. The §18 requirement that shuffling every provider's return order
and reversing traversal direction changes nothing applies to all five and is asserted with them.
WHY NS-AG-03 AND NS-AG-04 ARE NOT CLASS A, which is the subtle case (F-10.3b): each COMPOSES a
malformed stored object, and that object is already independently classified in 5.7 - its
storability, its expected reason code and its own parity obligation are discharged there. What
NS-AG-03 and NS-AG-04 add, and what they are ABOUT, is the AGGREGATION PRECEDENCE and RELEVANCE
rules of E2-A 15.2/15.3: that a valid path never rescues relevant corruption, and that irrelevance
must be decidable from identity alone. Classifying them as class A would double-count the stored
shape and, worse, would suggest their obligation is discharged by seeding a row - which is precisely
what it is not.
RATIONALE FOR BEING OUTSIDE A/B1/B2: the subject is resolver orchestration over candidate paths, not
a stored shape's acceptance or rejection. Varying stored rows is how these scenarios are DRIVEN, not
what they are ABOUT.
```

#### Deterministic defect ordering seam (E2-A 15.4, 15.5)

```text
ID         CONDITION / INPUT           PG-DATA  SUBJ  EXPECTED RESULT                        PARITY
NS-DO-01   two relevant Rules carrying YES      NO    the result_level_reason is the one the YES
           two DIFFERENT fail-closed                  E2-A 15.5 total order selects, and it
           defects detected at the                    is the same in every run
           SAME stage S4
NS-DO-02   ONE object carrying two     YES      NO    the reason_code_rank tie-break         YES
           distinct fail-closed                       decides, deterministically
           defects
NS-DO-03   defects on objects of       YES      NO    ordering is by object_family_rank,     YES
           DIFFERENT families at one                  never by discovery order
           stage
NS-DO-04   the same logical state      YES      NO    identical result_level_reason and      YES
           presented in shuffled                      identical partial-evaluation ordering
           provider row order; the                    every time, and BYTE-IDENTICAL
           candidate graph traversed                  serialized output across runs - no
           in reverse; the identical                  set/dict iteration, address, hash-seed
           scenario run N times                       or clock dependence
NS-DO-05   any multi-defect scenario,  YES      NO    the FIRST item always carries exactly  YES
           inspected at the head of                   the result_level_reason, so the two
           the ordered partial/failed                 can never disagree
           collection
NS-DO-06   the declared rank tables    NO       NO    every fail-closed reason code of E2-A  NO
           themselves, over the whole                 14.3 has an explicit reason_code_rank,
           corpus                                     and no two distinct defects in the
                                                      corpus produce an equal canonical
                                                      defect sort key

EXECUTABLE OBLIGATION, NS-DO-01 to NS-DO-05: E2-A §18 TOTAL FAIL-CLOSED DEFECT ORDER through the
reference composition, and the identical scenarios through the PostgreSQL-backed composition in §9,
asserting the PostgreSQL path reports the identical result_level_reason and identical
partial-evaluation ordering. Each must be BUILT FROM CLASS A defect shapes, since B1 and B2 shapes
cannot be seeded in PostgreSQL at all - hence PG-DATA YES.
EXECUTABLE OBLIGATION, NS-DO-06: the totality coverage assertion of E2-A §18 (TOTALITY, under TOTAL
FAIL-CLOSED DEFECT ORDER). PARITY is NO because it asserts a property of the kernel's declared rank
tables, not an outcome two compositions could disagree about; PG-DATA is NO because no row need be
stored to read a declared rank.
RATIONALE FOR BEING OUTSIDE A/B1/B2: the subject is the E2-A 15.5 TOTAL ORDER - which of several
simultaneously-detected defects is reported, and in what sequence the evidence is laid out. The
individual stored defects are already class A fixtures in 5.7 with their own storage and parity
obligations; these six assert what the kernel does when more than one of them is present at once,
and that the database is never what decides the answer (attack-surface item 14).
```

#### Evidence contract seam (E2-A 16)

```text
ID         CONDITION / INPUT           PG-DATA  SUBJ  EXPECTED RESULT                        PARITY
NS-EV-01   any ALLOW result            YES      NO    all four object/version pairs,         YES
                                                      per-object active/effective
                                                      evaluation, HR evidence, scope
                                                      operands plus composed results, and
                                                      parameter evaluation - E2-A 16.2
NS-EV-02   any COMPLETE NONQUALIFYING  YES      NO    the same four pairs PLUS its decisive  YES
           path, proved specifically                  path-level reason - E2-A 16.3
           for a scope denial and for
           a parameter denial
NS-EV-03   any PARTIAL / failed        YES      NO    established items, the exact failed or YES
           evaluation                                 absent stage, the deterministic
                                                      reason, and NO fabricated pairs -
                                                      absent pairs are ABSENT, never null
                                                      placeholders - E2-A 16.4
NS-EV-04   a DENY + RESOLVED in which  YES      NO    it still explains what was established YES
           ZERO complete paths existed                and why no path existed:
                                                      established_state populated,
                                                      last_stage_reached correct
NS-EV-05   every candidate touched     YES      NO    each candidate appears in EXACTLY ONE  YES
           during a resolution, and                   of the three collections; ordering of
           every collection's ordering                all four collections is deterministic
           under shuffled provider                    - E2-A 16.5
           output
NS-EV-06   the serialized evidence of  YES      NO    no secret, no credential and no        YES
           every scenario in the                      provider-specific identifier appears
           corpus                                     anywhere in it
NS-EV-07   a captured result, after    YES      NO    every cited (object_id,                YES
           further versions AND a                     object_version) still dereferences to
           retraction AND a valid                     BYTE-IDENTICAL content; a retracted
           correction are published                   version is excluded from resolution
                                                      yet still dereferenceable; and the
                                                      E2-A 11.8.1 asymmetry holds - the
                                                      historical resolver may now
                                                      reconstruct a different answer for the
                                                      same business as_of while the captured
                                                      evidence is unchanged, both provable

EXECUTABLE OBLIGATION for all seven: E2-A §18 EVIDENCE through the reference composition, and the
same assertions through the PostgreSQL-backed composition in §9 (EVIDENCE DURABILITY for NS-EV-07,
the parity corpus for the rest), agreeing field for field and order for order.
NS-EV-06 additionally carries an INDEPENDENT assertion on the PostgreSQL-backed composition, not
merely an agreement one: a provider-specific identifier could only ever leak on that side, so
agreement between the two compositions is necessary but not sufficient and both are asserted.
NS-EV-07 SHARES ITS SEEDED STATE with V-09 but asserts a different thing: V-09 asserts what the
historical resolver RECONSTRUCTS from valid rows, NS-EV-07 asserts that previously captured evidence
remains dereferenceable and byte-identical while that reconstruction changes. Neither discharges the
other.
RATIONALE FOR BEING OUTSIDE A/B1/B2: the subject is the E2-A 16 evidence contract - what a result
must carry, how it must be ordered, and what it must never carry or fabricate. Nothing here is a
malformed stored shape; several of these scenarios are driven by entirely valid state and a
successful ALLOW.
```

#### Pure-kernel invariant seam (E2-A 11, 15.5)

```text
ID         CONDITION / INPUT           PG-DATA  SUBJ  EXPECTED RESULT                        PARITY
NS-K-01    the                         NO       NO    see the three-part obligation below    NO
           SINGLE-EFFECTIVE-VERSION
           invariant of E2-A 11.4a.
           Replaces the withdrawn
           fixture A-03
NS-K-02    a violated kernel invariant NO       NO    DENY + FAIL_CLOSED,                    NO
           that is NOT                                INTERNAL_CONTRACT_VIOLATION - never
           authority-version                          degraded to a plain DENY (E2-A 14.3)
           multiplicity

NS-K-01 EXECUTABLE OBLIGATION, three parts, ALL MANDATORY (E2-A §18, NON-STORE block):
  (a) UNREACHABILITY. An enumerative/property test over a declared, bounded family of lineage shapes
      - up to N versions, each with a NULL or non-NULL declared end, distinct starts, evaluated at
      every boundary instant of the E2-A §18 TEMPORAL block - asserting that for EVERY shape passing
      the duplicate-start, nonsensical-interval and explicit-overlap conditions, AT MOST ONE version
      of the current asserted lineage is EFFECTIVE. This is the executable form of the E2-A 11.4a
      theorem.
  (b) DEFENSIVE BRANCH. A test that reaches the E2-A 11.6 residual clause by injecting a fabricated
      internal state directly - it is unreachable through any port, which is precisely the point -
      and asserts DENY + FAIL_CLOSED with result_level_reason AUTHORITY_VERSION_AMBIGUOUS and
      ordinary E2-A 16.4 failure evidence. This proves the guard exists and is wired, so a later
      refactor cannot delete it as dead code and silently lose the only detector of its own
      regression.
  (c) RANK TOTALITY. An assertion that AUTHORITY_VERSION_AMBIGUOUS carries an explicit declared
      reason_code_rank (E2-A 15.5), even though no provider can produce it.
NS-K-01 / NS-K-02 RATIONALE FOR BEING OUTSIDE A/B1/B2: neither state can be presented by ANY
provider. NS-K-01's is proved impossible by the E2-A 11.4a theorem, and NS-K-02's is by definition a
kernel-internal contract violation. There is nothing for a store to accept or reject, so PARITY is
NO for both - not as an exemption, but because a parity test would have no second side to run.
```

#### Totality and conformance obligations for this table

```text
- The table is TOTAL over non-store negative/conformance scenarios: FORTY-SIX scenarios in ten seam
  groups - NS-AP-01..04, NS-HR-01..12, NS-RQ-01..02, NS-PT-01, NS-PR-01..03, NS-RS-01..04,
  NS-AG-01..05, NS-DO-01..06, NS-EV-01..07, NS-K-01..02.
- Totality is defined against the CURRENT normative text, not against every conceivable defensive
  test: a scenario belongs here when E2-A or this document ALREADY states it as a mandatory
  conformance or acceptance obligation AND its malformed/negative subject is not stored authority
  state. Adding a scenario nobody has required is padding; omitting one that is required is the
  F-10.3b defect. Every row above cites the §18 or §9 obligation it carries.
- Every scenario ID has an executing E2-A test, asserted by the §9 coverage test - not skipped, not
  xfailed. Where a scenario's obligation also has an E2-B half (NS-PT-01, NS-PR-01..03, NS-RS-02/03,
  NS-EV-06/07 and every parity-YES row), that half is asserted in §9 as well.
- Every row answers BOTH store questions explicitly. PG-DATA may be YES or NO. SUBJ is NO on EVERY
  row, by construction - a YES would mean the item belongs in 5.7 - and §9 asserts that invariant
  rather than leaving it to be assumed. SUBJ = NO is a statement about the scenario's SUBJECT, never
  about whether every participating row is valid: where a scenario's defined semantics require it,
  an already-classified class A malformed row participates as a controlled ingredient and keeps its
  own class (F-10.3-DC-02).
- No scenario ID appears in the 5.7 A/B1/B2 manifest or in the 5.7 V-list, and no 5.7 fixture or
  V-scenario ID appears here. The three groups - 5.7 A/B1/B2, 5.7 V-01..V-12, and this table - are
  pairwise disjoint, and together they are the whole negative, valid-shape and conformance corpus of
  both documents; §9 asserts disjointness and exhaustiveness.
- Every parity-YES scenario is in the §9 parity corpus alongside the class A fixtures and the
  V-scenarios, and names the two compositions it runs on. Thirty-eight of the forty-six are
  parity-YES; the eight that are not (NS-AP-04, NS-PR-01..03, NS-RS-03, NS-DO-06, NS-K-01, NS-K-02)
  each state above why an agreement test has no second side, and each still carries an executable
  obligation.
- Adding a scenario to this table requires naming its seam from the closed list above. A scenario
  that needs a new seam is a reconciliation finding against E2-A, raised as such.
- Retired 5.7 IDs map here as recorded in 5.7: A-12 -> NS-RS-01; A-16 -> NS-PT-01; A-18 ->
  NS-AP-01..03 and NS-HR-01..12; A-19 -> NS-RQ-02; A-20 -> NS-RQ-01; A-03 -> NS-K-01.
```

## 6. Explicit exclusions (PF-1A-E2-B)

```text
- Configuration Change proposal / authorization / activation implementation      (PF-1A-E3)
- activation-time risk recomputation                                              (PF-1A-E3)
- preventive self-escalation workflow                                             (PF-1A-E3)
- protected meta-authority administration workflow                                (PF-1A-E3)
- any generic authority CRUD API, admin service or write endpoint                 (PF-1A-E3)
- ANY HTTP route, schema or OpenAPI surface at all
- authority administration frontend, or any frontend change
- an AUTHORITATIVE actor->person provider backed by a real identity/HR link       (later package)
- an AUTHORITATIVE canonical HR/organisation provider                             (later package)
- live SharePoint provider implementation
- live Plum provider implementation
- Source Binding / reconciliation implementation
- resolution of Q-10, any real bootstrap holder, or any production bootstrap
- production authority assignments or any real authority configuration data
- delegation
- HR-change lifecycle automation (leaver/transfer suspension, pending-approval reassignment)
- consumer business-workflow retrofit (credit assessment/approval, Commercial Offer approval,
  T&C deviation approval, Work Order release, Customer Master activation)
- any change to the PF-1A-E2-A kernel semantics, including any provider-side re-implementation of
  effectiveness, closure, activity, gap/contradiction classification, scope composition or
  aggregation
- any change to PF-1A-E1 runtime, contract, permissions, matrix, routes or tests
```

If persistence work appears to require any of the above, stop and raise it; do not extend scope.

Because the two authoritative provider dependencies are excluded, **E2-B must not describe itself,
in any document, handoff, acceptance record or code comment, as delivering a production-usable
business-authority resolver.** See sections 5.3 and 16.

## 7. PF-1A-E1 compatibility boundary (immutable)

Unchanged from PF-1A-E2-A section 6, and repeated here because E2-B is the package that actually
touches the database and `models_metadata.py` and therefore has the most opportunity to break it.

E2-B **must not**:

```text
- add any Business Authority code to backend/app/modules/authorization/contract.py;
- alter any of the 31 application permissions or the 110 role-permission grants;
- alter the six transitional Application/Login Roles, or the `role` / `app_user` / `user_role`
  tables;
- alter authz_permission or authz_role_permission, their columns, constraints or seeded rows;
- introduce an implicit ADMIN bypass;
- derive a Business Authority from an Application/Login Role, in code or through a schema link;
- reintroduce require_roles(...) into any route module;
- weaken, relax, delete or skip any assertion in the E1 route-migration guard or any other E1 test;
- replace, wrap or bypass require_permission(...).
```

The E1 facts that must remain true and be re-demonstrated: 31 permissions, six transitional roles,
110 grants, 76 permission-protected route entries, 11 authenticated-only exceptions, no privilege
widening or narrowing, no implicit ADMIN bypass, `ACCOUNT_TAX_VERIFY` FINANCE_USER-only, fail-closed
handling of unknown/unmapped/inactive inputs.

**Do not freeze historical totals as acceptance targets.** The recorded E1 closure figures (focused
authorization suite 117/117, full backend regression 382/382, Alembic head `20260831_0030`) describe
the state at E1 integration. E2-A and E2-B each add tests, so the full-suite total legitimately
rises. The acceptance condition is *every existing E1 and E2-A test still passes, unmodified, and
the compatibility facts above are unchanged*.

## 8. HR / organisation ownership boundary

Unchanged from PF-1A-E2-A section 7. Restated in persistence terms because this is where the
boundary is most easily broken by a well-intentioned schema:

```text
- Do NOT create a local employee, person, organisation-unit, position or incumbency table, view or
  materialized cache. PF-1A owns no HR master (ADR-026, ADR-032, RMR-001).
- person_id / position_id / org-unit scope identifiers are stored as OPAQUE canonical values with
  no local foreign key and no local join target.
- Do NOT store any provider identifier, provider field name, SharePoint Item ID, Plum field value,
  employee name, raw provider timestamp or Source Binding reference in any authority table.
- Do NOT persist canonical HR snapshots "for performance". Freshness and fail-closed behaviour
  belong to the HR-reference boundary, and a local copy would silently defeat the staleness control.
- Evidence produced by a resolution is returned to the caller; E2-B does not persist decisions or
  their evidence. A future consumer package stores its own decision record.
```

`READY_FOR_PF_1A_DESIGN_IMPLEMENTATION` is MET; `READY_FOR_PRODUCTION_AUTHORITY_ACTIVATION` is NOT
MET and is unaffected by anything E2-B does. Synthetic/reference HR providers remain sufficient for
E2-B's **tests**, and are confined to them by section 5.3. Real SharePoint population, a live Plum
interface and an authoritative actor-person link are out of scope.

## 9. Deterministic test strategy

E2-B's tests run against the real dockerized PostgreSQL, consistent with the repository's existing
backend test approach.

```text
SCHEMA / MIGRATION
    upgrade from an EMPTY database to the new head succeeds;
    `alembic current` == `alembic heads`, exactly one head;
    every new table, unique constraint, CHECK constraint, foreign key and index exists as specified;
    no existing table/column/constraint/index changed (explicitly assert the E1 authz_* and identity
      tables are untouched);
    the migration seeds NO authority configuration rows (assert the new tables are empty after
      upgrade);
    NO constraint forbids a temporal gap, and NO constraint/trigger rejects an overlapping version -
      a test INSERTS each of the five E2-A 11.4 lineage shapes successfully (null-end successor,
      explicit adjacency, explicit end before successor producing a gap, EXPLICIT OVERLAP with
      declared end after the successor's start, and duplicate start), proving the kernel - not the
      schema - is what classifies them (F-05, F-02, F-09). Only TWO of those five are CLASS A
      negative fixtures - A-01 (explicit overlap) and A-02 (duplicate start). The other three -
      null-end successor closure, explicit adjacency, and explicit end before successor producing a
      valid gap - are VALID-SHAPE PARITY SCENARIOS V-01, V-02 and V-03 of section 5.7 and carry NO
      class label, because nothing about them is malformed; calling them "class A" was the F-10.3a
      defect. The remaining E2-A 11.4 shape, end <= start, is CLASS B1 (B1-04, B1-05) and its INSERT
      is asserted to FAIL instead (F-10);
    NO NORMALIZATION: after inserting each of those shapes, read the rows straight back and assert
      every stored effective_from / declared_effective_to is BYTE-IDENTICAL to what was written - in
      particular that an explicit declared_effective_to LATER than the successor's effective_from is
      still stored as written and has not been truncated to the successor's start (F-09);
    NO retraction-suppressing structure: a duplicated retraction and a dangling retraction can both
      be INSERTED, and a retracted version's row is still stored, discoverable and dereferenceable
      (F-07);
    no stored/derived asserted_effective_to, is_current flag or equivalent exists;
    downgrade behaviour is considered and its decision recorded.

STORAGE INTEGRITY - CLASS B1 STRUCTURAL REJECTION (F-10)
    Each case asserts the WRITE FAILS against the MIGRATED SCHEMA EXACTLY AS SHIPPED, naming the
    constraint that rejected it. Each is EXCLUDED from the parity corpus below, and its
    provider-neutral behaviour is covered by the NAMED, EXECUTED E2-A test at the boundary section
    5.7 states for it (E2-A §18 DIRECT E2-A MALFORMED-INPUT COVERAGE):
        B1-01  duplicate (object_id, object_version) rejected;
        B1-02  assignment with BOTH person_id and position_id rejected;
        B1-03  assignment with NEITHER rejected;
        B1-04  declared_effective_to < effective_from rejected;
        B1-05  declared_effective_to == effective_from rejected (the same single-row interval CHECK);
        B1-06  NULL effective_from rejected;
        B1-07  NULL active_flag rejected;
        B1-08a NULL published_at on a version row rejected;
        B1-08b NULL retracted_at on a retraction row rejected;
        B1-09a NULL publication_reference_type rejected;
        B1-09b NULL publication_reference_id rejected;
        B1-10  publication_reference_type outside the two defined values rejected.
    A companion assertion, for each of the TWELVE B1 fixtures, names the E2-A test that covers it
    and its boundary, and asserts that test exists and is neither skipped nor xfailed. The
    fixture-name-to-ID mapping is asserted ONE-TO-ONE IN BOTH DIRECTIONS (F-10.1): no E2-A test may
    be cited as covering two manifest IDs, and no manifest ID may be left without its own distinctly
    named test. B1-09a (absent publication_reference_type, E2-A fixture PROVENANCE-ABSENT-TYPE) and
    B1-10 (unknown publication_reference_type, E2-A fixture PROVENANCE-UNKNOWN-TYPE) are asserted to
    be two distinct executing tests over two distinct inputs; citing one for both is the exact defect
    this split exists to prevent.

STORAGE INTEGRITY - CLASS B2 STRUCTURAL REJECTION (F-10)
    Each case asserts the WRITE FAILS against the shipped schema, naming the FOREIGN KEY that
    rejected it. Each is excluded from the parity corpus AND has NO E2-A counterpart test, by
    design (section 5.7 class B2 rationale). A companion assertion proves no such E2-A fixture has
    been fabricated:
        B2-01  version row referencing a non-existent stable identity ROW rejected;
        B2-02  retraction row referencing a non-existent OBJECT stable identity ROW rejected;
        B2-03  rule/assignment referencing a non-existent role/authority stable identity ROW
               rejected.
    A further assertion pins the distinction these three depend on: a rule/assignment referencing a
    stable identity row that DOES exist but carries NO version rows is ACCEPTED by the schema and is
    fixture A-11 - so the FK is proved NOT to have been extended into class A territory.

STORAGE INTEGRITY - CLASS A STORABILITY (the store must NOT reject these) (F-07, F-09, F-10)
    a duplicated retraction and a dangling retraction (targeting a non-existent VERSION of an
      EXISTING object) are ACCEPTED by the schema and surfaced to the kernel, which fails closed on
      each - they are NOT rejected structurally (F-07);
    a correcting version whose corrects_object_version target does not exist, and one whose target
      is not retracted, are both ACCEPTED by the schema (no FK or CHECK on corrects_object_version);
    a rule/assignment referencing a stable identity ROW THAT EXISTS but has no version rows is
      ACCEPTED, and reaches the kernel as AUTHORITY_REFERENCE_DANGLING - the stable-identity FK must
      not be mistaken for covering this case;
    published_at / retracted_at are NOT NULL, timezone-aware, stored faithfully and never rewritten;
      impossible recorded provenance (E2-A 11.8.3) is storable and is classified by the kernel, not
      by a cross-row constraint (F-07);
    an unknown parameter_evaluator_type and a malformed parameter_payload are both storable (no
      closed-enum CHECK, no lookup FK, no per-type schema check), and an unsupported scope_type
      value is storable, so EVALUATOR_UNKNOWN / EVALUATOR_PAYLOAD_INVALID /
      SCOPE_SEMANTICS_UNSUPPORTED remain kernel classifications and remain parity-testable (F-10);
    two versions of one object sharing an effective_from are storable - a test asserts NO unique
      constraint, partial index, exclusion constraint or trigger exists on
      (stable_object_id, effective_from) (F-10);
    active_flag is NOT NULL, stored, and has no UPDATE path (F-01);
    no code path in the package issues an UPDATE or DELETE against a version or retraction row;
    JSONB payload round-trips exactly, including nested structures and numeric precision.

PROVIDER FIDELITY (F-02) - the provider supplies FACTS, not judgements
    get_lineage returns EVERY version of the object, including retracted, inactive, future-dated and
      superseded versions, plus every retraction assertion - proved by seeding one object with all
      four kinds and asserting the returned set is complete;
    the provider computes NO closure, effectiveness, ranking or deduplication (asserted by giving it
      a lineage whose "obvious" answer differs from the raw set and checking the raw set comes back);
    discovery returns STABLE IDS ONLY and is a superset over RAW published facts: an object whose
      authority_code appears on an older, now-superseded version is still discovered;
    discovery applies NO retraction, effective-time, active_flag, scope, parameter, provenance or
      "latest version" predicate - one seeded case per excluded predicate, each asserting the object
      is still discovered (F-07);
    RETRACTION IS NOT A DISCOVERY FILTER (F-07): an object whose ONLY authority_code-bearing version
      is targeted by a retraction assertion is STILL returned by find_business_authority_ids_by_code,
      and an object whose ONLY reference-bearing version is retracted is STILL returned by
      find_rule_ids_for_authority / find_assignment_ids_for_role. A test inspects the generated SQL
      (or the repository code) and asserts there is NO NOT EXISTS over the retraction table in any
      discovery query;
    published_at / retracted_at are never used as a filter: shifting only the recorded timestamps
      (keeping them valid) changes no discovery result and no lineage set, and no port operation
      exposes a recorded-time cutoff parameter (F-07);
    a read failure surfaces as completeness = UNAVAILABLE / a raised error and maps to
      AUTHORITY_CONFIGURATION_UNAVAILABLE, NEVER to an empty result;
    a truncated read is never reported as COMPLETE;
    every list is returned under an explicit total ORDER BY, and the result does not change when
      rows are inserted in a different physical order;
    no query uses first()/LIMIT 1/scalar()/DISTINCT ON where uniqueness matters - a multiplicity
      condition surfaces to the kernel and fails closed rather than being silently resolved.

DEFECT VISIBILITY (F-02, F-07, F-09, F-10) - the store cannot hide what the kernel must catch
    ALL of the following are CLASS A: every row involved is structurally valid, so PostgreSQL must
    be able to hold the state, and every one of them is a state E2-A REQUIRES THE KERNEL TO REJECT,
    so this test is genuinely executable. For EACH of the FOURTEEN class A authority-store fixtures
    of section 5.7 (A-01, A-02, A-04 to A-11, A-13 to A-15, A-17) - duplicate
    effective_from; CONTRADICTORY EXPLICIT OVERLAP (declared end later than the next valid
    successor's start); a dangling retraction; a DUPLICATED retraction; a correcting version whose
    target is not retracted; a correcting version whose target does not exist; a reference to a
    stable identity ROW that exists but carries no lineage material; an unknown evaluator type; a
    malformed payload; an unsupported scope_type; each impossible recorded-timestamp relationship of
    E2-A 11.8.3; and the malformed retraction on the ONLY code/reference-bearing version -
        seed that state in PostgreSQL, resolve through the wired kernel, and assert the SAME
        fail-closed reason code the E2-A reference provider produces for the same logical state,
        which is the code section 5.7 states for that fixture.

    NO LONGER IN THIS BLOCK (F-10.3a): "a requested authority_code with no grant-eligible-by-lineage
    version at as_of" was listed above as class A fixture A-12. Nothing about that state is
    malformed - E2-A 11.5 states that a temporal gap is VALID lineage - so there is no contradictory
    state to seed and class A's defining obligation had nothing to bite on. It is now NON-STORE
    scenario NS-RS-01 (section 5.7A), still seeded in PostgreSQL, still resolved through the wired
    kernel, still expected to produce DENY + FAIL_CLOSED / AUTHORITY_CODE_NOT_CONFIGURED, and still
    owed FULL parity - covered by the NON-STORE CONFORMANCE block below. The rows it seeds are
    VALID, which is the whole reason it moved.

    ALSO NOT IN THIS BLOCK (F-10.3): an INDUCED READ FAILURE is no longer listed here. It is not a
    seeded stored state at all and is now NON-STORE scenario NS-PT-01 (section 5.7A), exercised by
    forcing an error, a timeout and a truncated read at the WIRED PostgreSQL read repository and
    asserting AUTHORITY_CONFIGURATION_UNAVAILABLE, never an empty result and never DENY + RESOLVED.
    Likewise the actor-person/HR states, the request-side scope-context and evaluator-facts states,
    the resolver/as_of and clock behaviour, provider reachability and fact-fidelity, aggregation and
    relevance, the total defect ORDER cases, the evidence-contract cases and the kernel invariants
    are all NON-STORE scenarios (NS-AP-*, NS-HR-*, NS-RQ-*, NS-PR-*, NS-RS-*, NS-AG-*, NS-DO-*,
    NS-EV-*, NS-K-*), covered by the NON-STORE CONFORMANCE block below. Several of them DO seed
    rows - NS-RS-01, NS-RQ-01/02, NS-AG-*, NS-DO-* and NS-EV-* all need stored authority data - but
    the rows they seed are either VALID or already independently classified in 5.7, and the subject
    under test is the resolver, not the row. Nothing was dropped; the obligations moved to where
    they are executable.

    AND NOT IN THIS BLOCK, BECAUSE IT CANNOT EXIST (F-10.2): the former A-03 residual-multiplicity
    state is NOT seeded, here or anywhere. E2-A 11.4a proves no lineage can present it on any
    provider. Attempting to construct one - by bypassing derived closure, by hand-editing kernel
    internals inside a persistence test, or by disabling a pre-check - proves nothing about this
    store and is prohibited. The invariant is covered by NS-K-01.

    NOT IN THIS BLOCK, DELIBERATELY (F-10): no CLASS B1 and no CLASS B2 fixture is seeded here. In
    particular a duplicate (object_id, object_version) pair is NOT "surfaced through the provider",
    an invalid assignment target is not seeded, an end <= start interval is not seeded, a NULL
    effective_from / active_flag / provenance value is not seeded, and no missing-stable-identity-row
    reference is seeded. Every one of those is rejected at write time by a section 5.6 constraint. An
    earlier draft of this section asked for the duplicate pair to be surfaced through the provider
    while section 5.6 mandated the constraint that makes it unstorable; that contradiction is
    withdrawn. Class B1 coverage is the structural-rejection tests above plus the named, executed
    E2-A tests at their stated boundaries (5.7); class B2 coverage is the structural-rejection tests
    above and nothing else, because there is no provider-neutral counterpart to test (5.7 rationale).
    Do not attempt to seed any of them by disabling, deferring or dropping a constraint in a fixture:
    that would prove nothing about the shipped schema and would silently convert a B1/B2 exclusion
    into a fake class A pass.

    RETRACTION CANNOT HIDE A VERSION (F-07): for a dangling retraction, a duplicated retraction and a
    retraction with impossible provenance, where the retraction targets the ONLY
    requested-code-bearing version - and, as a companion case, the ONLY reference-bearing version of
    a candidate Rule/Assignment - assert the resolution through PostgreSQL fails closed with the
    lineage/provenance defect's own reason code, and NOT with AUTHORITY_CODE_NOT_CONFIGURED, NOT with
    NO_CANDIDATE_ASSIGNMENT, and NOT with an empty candidate set. This is the exact defect the
    withdrawn retraction-excluding EXISTS in section 5.2 would have produced, so it is the highest-
    value regression test in this package.

VALID-SHAPE CONFORMANCE (F-10.3a) - the section 5.7 V-scenarios, which seed VALID rows
    For each of V-01 to V-12, seed the VALID stored shape in PostgreSQL, resolve through the wired
    kernel, and assert the expected outcome, resolution_status, reason and evidence, exactly as the
    E2-A reference provider produces them:
        V-01..V-04     derived closure over valid lineage: null-end successor closure; explicit
                       adjacency; explicit end before successor (valid gap) with its per-family
                       normal nonqualification; later reactivation after that gap;
        V-05..V-06     active-state: inactive-but-effective versions in all four families with their
                       own *_NOT_ACTIVE reasons and the AUTHORITY_NOT_ACTIVE short-circuit, and an
                       inactive version still closing its predecessor in derived closure;
        V-07           the exact half-open boundary instants of every shape above, plus a
                       future-dated version conferring nothing before its effective_from;
        V-08           raw discovery over valid retraction facts - retracted-only code-bearing and
                       reference-bearing versions still DISCOVERED;
        V-09           recorded-time-versus-business-effective-time RECONSTRUCTION;
        V-10..V-12     valid scope operands, scope composition, and evaluator satisfaction and
                       legitimate non-satisfaction over facts that are present, correctly typed and
                       unit/currency/basis-COMPATIBLE - the incompatible case is NS-RQ-02, not V-12
                       (F-10.3-DC-01).
    ALL TWELVE ARE PARITY SCENARIOS and none carries an A/B1/B2 class label. A test asserting a
    V-scenario as a "class A fixture" is the F-10.3a defect: class A's defining obligation is to
    store a CONTRADICTORY state, and these states are valid.

NON-STORE CONFORMANCE (F-10.3, extended by F-10.3b) - the section 5.7A scenarios, whose malformed
or negative SUBJECT is never a stored row
    For every one of the FORTY-SIX scenarios in section 5.7A, drive the stated condition and assert
    the expected outcome, resolution_status, reason code and E2-A 16.4 evidence:
        NS-AP-01..04   actor-person seam: no mapping; ambiguous mapping; provider unbound; and the
                       client-supplied person_id trust boundary, asserted against the WIRED path
                       here as well as against the E2-A surface;
        NS-HR-01..12   HR seam: provider unbound; unavailable; stale; employment/position/
                       incumbency/org-unit missing and ambiguous; org hierarchy unresolvable;
        NS-RQ-01..02   request-side: missing canonical scope for a non-GLOBAL operand on a
                       well-formed STORED rule/assignment; and a business fact for a VALID STORED
                       evaluator that is missing, type-invalid, or supplied in a unit/currency/basis
                       incompatible with the one the payload declares - all three failing closed
                       with EVALUATOR_FACTS_INVALID, never EVALUATOR_CONDITION_NOT_SATISFIED
                       (F-10.3-DC-01);
        NS-PT-01       authority configuration port: forced read error, forced timeout, and a
                       deliberately truncated read - the last asserted NEVER to be reported as
                       COMPLETE;
        NS-PR-01..03   provider reachability and fidelity: synthetic providers unreachable from
                       production imports and wiring and unselectable by any switch; the production
                       composition either refusing to compose or failing closed deterministically;
                       and a provider that supplies judgements instead of facts being REJECTED by
                       the conformance test - PROVIDER FIDELITY above is the E2-B half of NS-PR-03;
        NS-RS-01..04   resolver, clock and entry-point seam: the requested authority with no
                       grant-eligible-by-lineage version at as_of over VALID rows (the former A-12);
                       one server-captured instant governing every stage under real read latency;
                       the entry-point parameter surfaces exposing no as_of and no recorded-time
                       bound after wiring; and recorded timestamps never acting as a lineage filter;
        NS-AG-01..05   aggregation and relevance: two valid qualifying paths; valid plus normally
                       nonqualifying; valid plus RELEVANT-corrupt failing closed; IRRELEVANT-corrupt
                       leaving the result unaffected with its fail-closed companion; and the
                       result-level reason selected when no path qualifies;
        NS-DO-01..06   deterministic defect ordering: same-stage two-defect selection; one subject
                       with two reason codes; cross-family ordering; shuffled/reversed/repeated runs
                       producing byte-identical output; the first ordered item always carrying the
                       result_level_reason; and reason-rank totality;
        NS-EV-01..07   the evidence contract: ALLOW evidence; complete-nonqualifying evidence for a
                       scope denial and a parameter denial; partial evidence with no fabricated
                       pairs; a zero-path DENY + RESOLVED still explaining itself; one-collection
                       membership and deterministic ordering; no secret or provider-specific
                       identifier anywhere; and durability across later versions, a retraction and a
                       correction - EVIDENCE DURABILITY below is the E2-B half of NS-EV-07;
        NS-K-01/02     pure-kernel invariants; these are E2-A-side obligations and are asserted here
                       only as a cross-reference check that the named E2-A tests exist and execute.
    For every scenario whose 5.7A PARITY column says YES - thirty-eight of the forty-six - the
    identical driving condition runs through BOTH named compositions: reference authority provider
    and PostgreSQL authority provider, each with the SAME synthetic actor/HR providers. The two must
    agree on outcome, resolution_status, result_level_reason, all three evidence collections with
    their ordering, and established_state.
    NO MALFORMED ROW IS THE SUBJECT of any of these - and that, NOT "no malformed row anywhere in
    the fixture", is the rule (F-10.3-DC-02). PG-DATA participation and SUBJ classification are
    INDEPENDENT dimensions. Several of these scenarios legitimately store and read authority rows:
    NS-RS-01, NS-RQ-01 and NS-RQ-02 need VALID rows to reach their condition, and NS-EV-* are driven
    from valid state; while NS-PR-03, NS-AG-03, NS-AG-04 and NS-DO-01..05 REQUIRE, by their own
    defined semantics, ALREADY-CLASSIFIED class A malformed rows as CONTROLLED INGREDIENTS - indeed
    NS-DO-01..05 must be built from class A defect shapes, since B1 and B2 shapes cannot be seeded
    here at all. Such an ingredient keeps its own A/B1/B2 classification and discharges its own
    section 5.7 storability, reason-code and parity obligations there; its presence does not make
    the enclosing resolver / provider / orchestration scenario an authority-store fixture, and does
    not double-count the stored shape. What IS prohibited: (1) treating the ingredient as the
    scenario's actual non-store SUBJECT; (2) seeding a NEW malformed persisted shape that carries no
    A/B1/B2 classification; (3) using this block as an escape hatch from the section 5.7 fixture
    manifest; and (4) suppressing or normalizing the ingredient contrary to the raw-discovery and
    fail-closed rules above. The 5.7A PG-DATA column records which scenarios need stored rows; the
    SUBJ column records that in none of them is the malformed subject UNDER TEST a stored row. A
    test that seeds a malformed row, makes THAT row's acceptance or rejection the thing it proves,
    and then claims to be discharging a 5.7A obligation has confused the two columns.

PARITY (the central proof of this package) - CLASS A, THE VALID SHAPES, AND THE PARITY-YES
NON-STORE SCENARIOS (F-10, corrected by F-10.3a/b)
    The parity corpus has exactly THREE parts and no others:
        (i)   the CLASS A set of section 5.7 - the fourteen fixtures A-01, A-02, A-04 to A-11,
              A-13 to A-15, A-17. This part varies the MALFORMED stored state.
        (ii)  the VALID-SHAPE PARITY SCENARIOS of section 5.7 - V-01 to V-12. This part varies the
              VALID stored state. It was previously folded into part (i) and described as "class A",
              which attached a negative-fixture label to states that are not defects; naming it
              separately changes no obligation, only the label.
        (iii) the section 5.7A scenarios whose PARITY column says YES - thirty-eight of the
              forty-six: NS-AP-01..03, NS-HR-01..12, NS-RQ-01..02, NS-PT-01, NS-RS-01/02/04,
              NS-AG-01..05, NS-DO-01..05 and NS-EV-01..07. This part varies a provider, request,
              clock, orchestration or evidence condition while both compositions use the same
              synthetic actor/HR providers.
    It contains no class B1 and no class B2 fixture, because no conforming
    implementation of this schema can return a row the schema forbids storing; B1 shapes are covered
    by the structural-rejection tests above plus the named, executed E2-A tests at their stated
    boundaries, and B2 shapes by the structural-rejection tests alone. It also contains none of the
    eight parity-NO non-store scenarios (NS-AP-04, NS-PR-01..03, NS-RS-03, NS-DO-06, NS-K-01,
    NS-K-02): each is a surface/structural assertion or a state no provider can present, so a parity
    test would have no second side to run, and each carries its own executable obligation in 5.7A
    instead. Excluding any of them here is
    verification placement, not a semantic exemption, and sections 5.7 and 5.7A plus the acceptance
    record state each exclusion explicitly - with a written rationale for every B2 entry.

    one shared, declarative scenario corpus is executed twice: once through the E2-A reference
    in-memory provider, once through the E2-B PostgreSQL provider. For EVERY scenario the two must
    agree on: outcome, resolution_status, result-level reason, the set and ORDER of qualifying
    paths, the set and ORDER of COMPLETE NONQUALIFYING paths and their decisive reasons, the set and
    ORDER of PARTIAL/FAILED evaluations and their stages and reasons, the established_state header,
    and every evidence field (F-06).
    The corpus must cover, at minimum, the class A part of the E2-A section 18 matrix:
        temporal boundaries, including the EXACT HALF-OPEN boundary instants;
        DERIVED CLOSURE, every branch of the E2-A 11.4 asserted-interval rule as its own parity
        scenario - null-end successor closure (V-01), explicit adjacency (V-02), explicit end before
        successor producing a valid gap (V-03), later reactivation after that gap (V-04), explicit
        end AFTER the successor's start (contradictory explicit overlap -> fail closed, never
        normalized: CLASS A fixture A-01) and duplicate start (CLASS A fixture A-02). All six are
        parity scenarios, but only the last TWO are class A: the first four are VALID-SHAPE
        scenarios and carry no class label. Describing all six as "CLASS A" was the F-10.3a defect
        and must not be reintroduced. The end <= start branch
        (including end == start) is CLASS B1 (B1-04, B1-05) and is deliberately NOT a parity
        scenario: the INSERT is asserted to FAIL in PostgreSQL by the STORAGE INTEGRITY - CLASS B1
        tests above, and the kernel's I-6 fail-closed behaviour is proved by E2-A's permanent direct
        test at the PURE KERNEL boundary (E2-A 18, DIRECT E2-A MALFORMED-INPUT COVERAGE) (F-09,
        F-10);
        VALID GAPS and reactivation after a gap, per family (V-03, V-04) - and, SEPARATELY, the
        asymmetric AUTHORITY_CODE_NOT_CONFIGURED case for the REQUESTED authority, which is
        NON-STORE scenario NS-RS-01 rather than a stored-shape fixture, because its rows are valid
        and its subject is the resolver (F-05, F-10.3a);
        RAW DISCOVERY AND RETRACTION cases - retracted-only code-bearing version, retracted-only
        reference-bearing version, malformed/duplicated/dangling retractions, and each excluded
        discovery predicate (F-07);
        RECORDED TIME versus BUSINESS-EFFECTIVE TIME - a version published after a historical as_of
        that nonetheless participates in reconstructing it; a retraction recorded today that removes
        its target from an older reconstruction; the same corrected-reconstruction behaviour on both
        providers; and each impossible recorded-timestamp relationship failing closed (F-07);
        retraction and correction; ACTIVE-STATE cases for all four families including the
        inactive-effective-version nonqualification and the AUTHORITY_NOT_ACTIVE short-circuit
        (F-01); dangling references; person and position assignments; incumbency ambiguity; every
        scope operand and every SCOPE COMPOSITION case including GLOBAL ∩ EXACT both ways and two
        differing EXACT operands (F-03); evaluator cases; MIXED-PATH AGGREGATION - valid+valid,
        valid+normal-nonqualifying, valid+relevant-corrupt (fail closed), irrelevant-corrupt
        (unaffected), no-path (F-03);
        TOTAL DEFECT ORDER cases (F-08), which are NON-STORE scenarios NS-DO-01 to NS-DO-05 - two
        different defects at the SAME stage on two Rules; one subject carrying two reason codes;
        defects across families at one stage; shuffled/reversed/repeated runs - each asserting the
        PostgreSQL path reports the identical result_level_reason and identical partial-evaluation
        ordering as the reference provider. Each such scenario must be BUILT FROM class A defect
        shapes, since B1 and B2 shapes cannot be seeded in PostgreSQL at all - but being built from
        class A shapes does not make the scenario itself class A: its subject is the E2-A 15.5 total
        order, not the acceptance or rejection of any one row (F-10.3b);
        MIXED-PATH AGGREGATION and RELEVANCE, likewise NON-STORE scenarios NS-AG-01 to NS-AG-05, and
        the EVIDENCE-contract scenarios NS-EV-01 to NS-EV-07, driven identically through both
        compositions;
        the parity-YES NON-STORE scenarios of section 5.7A, driven identically through both
        compositions (see the NON-STORE CONFORMANCE block above);
        and each fail-closed reason code of E2-A 14.3 EXCEPT the codes on the explicit, JUSTIFIED
        exclusion list of section 5.7 - every excluded code justified either as CLASS B1/B2 (naming
        the 5.6 constraint that makes EVERY shape producing it unstorable, and for B1 the covering
        E2-A test and its boundary) or as KERNEL-INTERNAL (naming the E2-A test / 5.7A scenario that
        exercises it). That list is CLOSED and unconditional: ASSIGNMENT_TARGET_INVALID (class B1,
        person/position XOR CHECK, fixtures B1-02/B1-03), AUTHORITY_VERSION_AMBIGUOUS
        (kernel-internal, unreachable from any provider by E2-A 11.4a, covered by NS-K-01) and
        INTERNAL_CONTRACT_VIOLATION (kernel-internal self-check, covered by NS-K-02). Nothing on it
        is conditional on what the implemented kernel turns out to do.
        AUTHORITY_CONFIGURATION_UNAVAILABLE is NOT excluded: it is covered through NON-STORE
        scenario NS-PT-01, whose parity column is YES, even though B1-06/B1-07 also produce it at
        the DTO/port boundary. AUTHORITY_CODE_NOT_CONFIGURED is NOT excluded either, and this is the
        one to check after F-10.3a: it used to reach parity through class A fixture A-12, and now
        reaches it through NON-STORE scenario NS-RS-01, whose parity column is YES. A reviewer who
        finds that code missing from the parity corpus has found a real regression, not a
        consequence of the reclassification. A test
        asserts the implemented exclusion list equals the acceptance record's verification-class
        manifest, so it can neither grow silently nor be padded to excuse a missing scenario (F-10).

VERIFICATION CLASS CONFORMANCE (F-10)
    TAXONOMY SCOPE AND PARTITION FIRST (F-10.3, corrected by F-10.3a/b): a coverage test partitions
      the union of both documents' named negative, valid-shape and conformance items into exactly
      THREE DISJOINT and EXHAUSTIVE groups - AUTHORITY-STORE NEGATIVE fixtures (section 5.7,
      A/B1/B2), VALID-SHAPE PARITY scenarios (section 5.7, V-01 to V-12) and NON-STORE scenarios
      (section 5.7A). It asserts the pairwise intersections are empty, the union is the whole
      corpus, every 5.7 A/B1/B2 entry has a YES/NO (never "N/A") answer to "PG may store", every
      V-entry carries no class label, and every 5.7A entry has a named seam drawn from the closed
      list in 5.7A, an executable obligation, and BOTH store answers. A classified fixture whose
      storability is "N/A", a valid stored shape carrying a class label, a 5.7A row whose SUBJ
      answer is YES, or a non-store scenario with no obligation, each fails this test;
    NO FAIL-CLOSED OUTCOME IMPLIES A NEGATIVE FIXTURE (F-10.3a): a specific assertion proves that
      every A/B1/B2 entry seeds a state E2-A requires the kernel to REJECT AS INVALID, and that no
      entry whose seeded rows are VALID carries a class label. NS-RS-01 is the worked example - it
      produces DENY + FAIL_CLOSED / AUTHORITY_CODE_NOT_CONFIGURED from entirely valid rows and must
      appear in 5.7A, never in 5.7;
    COUNTS: the test asserts 14 class A, 12 class B1, 3 class B2 (29 authority-store negative
      fixtures), 12 valid-shape parity scenarios (V-01 to V-12) and 46 non-store scenarios, matching
      sections 5.7 and 5.7A exactly, and asserts that no retired ID (A-03, A-12, A-16, A-18, A-19,
      A-20) has been reused;
    every AUTHORITY-STORE negative fixture is assigned to exactly one
      CLASS by section 5.7 - the assignment is TOTAL (no fixture
      unassigned) and EXCLUSIVE (no fixture in more than one class) - and none has its class,
      storability, expected reason or parity obligation left conditional on the implemented kernel;
    every CLASS A fixture and every VALID-SHAPE scenario V-01 to V-12 appears in the parity corpus,
      and NO class B1 or B2 fixture appears there;
    every parity-YES NON-STORE scenario appears in the parity corpus - thirty-eight of the
      forty-six - and the eight parity-NO scenarios (NS-AP-04, NS-PR-01..03, NS-RS-03, NS-DO-06,
      NS-K-01, NS-K-02) do not, each carrying instead the executable obligation 5.7A states for it;
    every CLASS B1 fixture has BOTH a structural-rejection test here AND a named, actually-executed
      E2-A test - a test asserts each named E2-A test exists and is neither skipped nor xfailed, so
      a defect class cannot silently lose coverage in the gap between packages - AND that the named
      E2-A test exercises the BOUNDARY section 5.7 states for it (DTO/port well-formedness for
      B1-06/B1-07; pure kernel for B1-01 to B1-05, B1-08a, B1-08b, B1-09a, B1-09b and B1-10) - AND
      that the ID-to-fixture-name mapping is ONE-TO-ONE IN BOTH DIRECTIONS, with B1-09a
      (PROVENANCE-ABSENT-TYPE) and B1-10 (PROVENANCE-UNKNOWN-TYPE) proved to be two distinct
      executing tests over two distinct inputs (F-10.1);
    every CLASS B2 fixture has a structural-rejection test here, a NON-EMPTY written rationale in
      section 5.7 and in the acceptance record, and NO E2-A fixture - a test asserts no E2-A fixture
      has been fabricated for B2-01, B2-02 or B2-03, because a fabricated one would necessarily rest
      on an invented DTO field or reason code (E2-A 9.7);
    B2 REMAINS JUSTIFIED: a test asserts the E2-A 9.3.4 DTO-required / DTO-optional split and the
      E2-A 9.3.2 empty-material rule are exactly as those sections declare, since the B2 rationale
      depends on both. If either changes, the affected fixture is reclassified to B1 with a
      mandatory E2-A test rather than left as B2;
    no fixture is seeded by disabling, deferring, dropping or otherwise circumventing a shipped
      constraint - a test asserts the fixtures run against the migrated schema exactly as shipped;
    the schema introduces NO structural constraint beyond those listed in section 5.6 - a test
      enumerates the actual constraints/indexes on the new tables and asserts the set matches, so a
      "helpful" addition cannot silently move a class A fixture into B1 or B2, and a silent removal
      cannot strip a rejection proof;
    the acceptance record carries the section 5.7 verification-class manifest, the section 5.7
      VALID-SHAPE scenario list AND the section 5.7A non-store scenario table in full, naming for
      each B1 class the rejecting constraint, the covering E2-A test and its boundary; for each B2
      class the rejecting constraint and its written rationale; for each non-store scenario its
      seam, obligation, BOTH store answers, expected result and parity requirement; plus the
      justified fail-closed reason-code exclusion list - and a test asserts the implemented
      exclusion list equals that manifest.

DETERMINISM UNDER PERSISTENCE (F-08)
    the result_level_reason and every evidence ordering are unchanged when: rows are INSERTED in a
      different physical order; the table is reorganised/VACUUMed so physical order differs; an
      ORDER BY is deliberately removed from a provider query in a mutation-style test (the KERNEL's
      canonical re-sort must still produce the same answer); the same scenario runs repeatedly,
      producing BYTE-IDENTICAL serialized output; and two resolutions run concurrently against the
      same seeded state.

EVIDENCE DURABILITY (F-06, F-07)
    capture a result; then publish further synthetic versions AND a retraction AND a correction;
    prove every cited (object_id, object_version) still dereferences to byte-identical content;
    prove a retracted version is excluded from resolution but still dereferenceable;
    prove the intended, deliberate asymmetry of E2-A 11.8.1: after that valid correction,
      resolve_authority_as_of(the SAME historical business as_of) may now reconstruct a DIFFERENT
      answer, while the previously captured immutable decision evidence is unchanged and still fully
      dereferenceable - both answers provable, neither overwriting the other;
    prove denial and partial-evaluation evidence survives persistence unchanged: a scope denial and
      a parameter denial each still carry all four object/version pairs, and a partial evaluation
      still carries no fabricated pairs.

RUNTIME WIRING / PROVIDER REACHABILITY (F-04)
    the PRODUCTION composition either refuses to compose, or returns DENY + FAIL_CLOSED with
      ACTOR_PERSON_PROVIDER_NOT_CONFIGURED / HR_REFERENCE_PROVIDER_NOT_CONFIGURED on every call -
      whichever option the implementation chose, asserted explicitly;
    the synthetic/reference actor-person and HR providers are NOT importable from, and NOT reachable
      through, any production module or the production dependency wiring;
    no environment variable, settings flag, feature toggle or dependency override can switch a
      production composition onto a synthetic provider;
    the test/reference composition (kernel + PostgreSQL provider + synthetic HR/actor providers)
      exists only under the test tree.

SECURITY / BOUNDARY
    no repository/service/dependency function writes published authority configuration;
    an Application/Login Role alone (including ADMIN) grants no business authority through the
      persisted path;
    no schema link exists between `role` and any Business Authority Role table;
    the current-authorization path still accepts no caller-selected as_of after wiring;
    no client-supplied person_id can influence the identity authorized;
    test fixture/seed helpers are unreachable from production runtime paths;
    tracked-secret scan passes; no credential or personal data appears in fixtures.

REGRESSION
    every existing PF-1A-E1 test passes unmodified;
    every existing PF-1A-E2-A test passes unmodified;
    full backend regression passes;
    tests leave no residual rows (follow the existing conftest/session-boundary discipline).
```

## 10. Acceptance criteria (PF-1A-E2-B implementation)

```text
A.  The accepted E2-A model is persisted in PostgreSQL with stable object identity separated from
    immutable published version identity.
B.  Append-only publication lineage, retraction and provenance are persisted; no published version
    row is ever updated, and asserted closure is DERIVED rather than stored.
C.  active_flag is persisted as an immutable, NOT NULL, stored value on the version row, with no
    UPDATE path, no derived/computed variant, and no filtering of inactive versions anywhere in the
    store.                                                                                   (F-01)
D.  The database-backed provider implements the E2-A port as RAW CANDIDATE DISCOVERY (stable
    identities only, superset semantics over raw published facts) plus COMPLETE LINEAGE MATERIAL. No
    discovery query contains a NOT EXISTS over the retraction table or any effective-time,
    active_flag, scope, parameter, provenance or "latest version" predicate; retraction assertions
    are returned as facts, never applied as filters; published_at / retracted_at are stored and
    returned as recorded-time evidence and are never used to filter, and no port operation exposes a
    recorded-time cutoff. The provider computes no closure or effectiveness and duplicates no E2-A
    semantic rule. Read failures surface as UNAVAILABLE and never as an empty result. (F-02, F-07)
E.  Defect visibility is proved for every CLASS A defect class (section 5.7: the fourteen fixtures
    A-01, A-02, A-04 to A-11, A-13 to A-15 and A-17): the same logical state seeded in PostgreSQL
    produces the same fail-closed reason code as the
    E2-A reference provider — including fixture A-17, where a dangling, duplicated or
    impossibly-provenanced retraction targets the ONLY requested-code-bearing or ONLY
    reference-bearing version and must fail closed on that defect and never report an absent
    candidate. Every one of the fourteen seeds a state E2-A requires the kernel to REJECT AS
    INVALID; a state whose rows are valid is not a class A fixture, however fail-closed its outcome.
    Class B1 and class B2 shapes are not seeded here; their coverage is criterion N3. VALID-SHAPE
    scenarios V-01 to V-12 are seeded, but as valid state and under criterion N; NON-STORE scenarios
    are covered by criterion N4. The former A-03 is not seeded anywhere, because E2-A 11.4a proves
    the state cannot exist on any provider. The former A-12 is still seeded — with VALID rows, as
    NON-STORE scenario NS-RS-01 — and still expected to produce DENY + FAIL_CLOSED /
    AUTHORITY_CODE_NOT_CONFIGURED with full parity; only its classification changed.
                                                              (F-02, F-07, F-10, F-10.2/10.3/10.3a)
F.  The schema permits valid temporal gaps, permits contradictory lineage — including a
    CONTRADICTORY EXPLICIT OVERLAP and a duplicate start — to be STORED, and permits a duplicated or
    dangling retraction, a correcting version with a missing or unretracted target, a reference to
    an existing stable identity carrying no lineage material, an unknown evaluator type, a malformed
    payload, an unsupported scope_type and impossible recorded provenance to be stored, so that
    classification remains the kernel's. Nothing is normalized on write or on read: every stored
    effective_from / declared_effective_to reads back byte-identical to what was published, and an
    explicit declared end later than the successor's start is never truncated. No contiguity
    constraint, no overlap-rejecting constraint/trigger, no uniqueness constraint or exclusion
    constraint on (stable_object_id, effective_from), no retraction-uniqueness or
    retraction-to-version FK, no FK/CHECK on corrects_object_version, no closed-enum constraint on
    parameter_evaluator_type or scope_type, and no stored derived-closure or is_current artefact
    exists.                                                              (F-05, F-07, F-09, F-10)
G.  The E2-A kernel is reused UNCHANGED; any kernel diff is justified as a reconciliation finding
    and independently reviewed as such.
H.  Models are registered in backend/app/models_metadata.py.
I.  Exactly one bounded Alembic migration, parented on the ACTUAL head discovered at package start,
    altering no existing schema object and seeding no authority configuration.
J.  Assignment person_id XOR position_id is enforced structurally; both the BOTH and the NEITHER
    shapes are therefore CLASS B1 (B1-02, B1-03), with ASSIGNMENT_TARGET_INVALID proved directly
    against the kernel at stage S7 by E2-A rather than through this store, which is possible because
    E2-A 9.3.4 keeps person_id and position_id DTO-optional (section 5.7).                  (F-10)
K.  Referential, version and provenance integrity are enforced as set out in section 5.6, with the
    non-structural half detected and failed closed by the kernel, and with section 5.7 stating
    unambiguously which of the three classes each defect shape falls in — including, for each of
    the three stable-identity foreign keys, the written rationale for why the rejection it performs
    is a persistence-only invariant (class B2) rather than a semantic one.                  (F-10)
L.  Queries are deterministic, totally ordered and parameterized; no arbitrary first-row selection
    where uniqueness or ambiguity matters; PostgreSQL SQL only.
M.  Evaluator payloads persist as structured data while E2-A validation remains semantically
    authoritative.
N.  Reference-provider / PostgreSQL-provider parity is demonstrated across the full parity corpus of
    section 9, which is exactly THREE parts: (i) the CLASS A set of section 5.7 — the fourteen
    fixtures A-01, A-02, A-04 to A-11, A-13 to A-15, A-17, which vary the MALFORMED stored state;
    (ii) the VALID-SHAPE PARITY SCENARIOS V-01 to V-12 of section 5.7, which vary the VALID stored
    state and carry NO class label; and (iii) the parity-YES NON-STORE scenarios of section 5.7A —
    thirty-eight of forty-six: NS-AP-01..03, NS-HR-01..12, NS-RQ-01..02, NS-PT-01, NS-RS-01/02/04,
    NS-AG-01..05, NS-DO-01..05 and NS-EV-01..07 — including active-state,
    every PERSISTABLE branch of the derived-closure rule (successor closure, adjacency, gap and
    reactivation as V-01 to V-04; explicit overlap and duplicate start as class A fixtures A-01 and
    A-02 — describing all six as "class A" was the F-10.3a defect), raw discovery/retraction,
    recorded-time-versus-business-effective-time, scope-composition, mixed-path aggregation and
    same-stage multi-defect cases — agreeing on outcome, status, result-level reason, all three
    evidence collections with their ordering, the established_state header, and every evidence
    field. The `end <= start` branch is deliberately NOT a parity scenario: it is class B1
    (B1-04/B1-05), proved by structural rejection here plus E2-A's direct kernel-boundary test
    (criterion N3). The eight parity-NO non-store scenarios (NS-AP-04, NS-PR-01..03, NS-RS-03,
    NS-DO-06, NS-K-01, NS-K-02) are deliberately NOT parity scenarios either: each is a
    surface/structural assertion or a state no provider can present, so a parity test would have no
    second side (criterion N4). Parity
    covers every fail-closed reason code of E2-A 14.3 except the codes on the
    explicit, justified, CLOSED exclusion list of section 5.7 — ASSIGNMENT_TARGET_INVALID (class
    B1), AUTHORITY_VERSION_AMBIGUOUS (kernel-internal, NS-K-01) and INTERNAL_CONTRACT_VIOLATION
    (kernel-internal, NS-K-02) — each justified as class B1/B2 (naming the
    constraint, and for B1 the covering E2-A test and its boundary) or kernel-internal (naming the
    E2-A test / 5.7A scenario). AUTHORITY_CODE_NOT_CONFIGURED is NOT on that list: it stays in
    parity through NS-RS-01. No entry on that list is conditional.
                                                       (F-01, F-03, F-05 to F-10, F-10.3a/10.3b)
N2. Determinism survives persistence: result_level_reason and every evidence ordering are unchanged
    under differing physical row order, table reorganisation, removed provider ORDER BY, repeated
    runs (byte-identical output) and concurrent resolutions — proving the E2-A total defect order
    (E2-A 15.5), not the database, decides which defect is first.                          (F-08)
N3. The THREE-CLASS verification assignment of section 5.7 is TOTAL and EXCLUSIVE over the
    AUTHORITY-STORE negative corpus of both documents: every named authority-store negative fixture
    sits in exactly one of A / B1 / B2, none is unclassified, none records its storability as "N/A",
    and none defers its class, storability, expected reason or parity obligation to implementation
    time, and none seeds a state whose rows are VALID — a fail-closed outcome alone never makes an
    item a negative fixture (F-10.3a). The counts are asserted: 14 class A, 12 class B1, 3 class B2.
      • every CLASS A fixture is parity-tested;
      • no class B1 or B2 fixture appears in the parity corpus;
      • every CLASS B1 fixture has both a structural-rejection test here and a named,
        actually-executed (not skipped, not xfailed) E2-A test, and that test exercises the
        BOUNDARY section 5.7 names for it — DTO/port well-formedness for B1-06 and B1-07, pure
        kernel for the rest — with the expected reason code stated normatively rather than chosen
        by the implementer, and with the ID-to-fixture-name mapping ONE-TO-ONE in both directions.
        In particular B1-09a (absent publication_reference_type, fixture PROVENANCE-ABSENT-TYPE) is
        a distinct executing pure-kernel test expecting DENY + FAIL_CLOSED /
        PUBLICATION_PROVENANCE_INVALID with ordinary deterministic failure evidence, and is NOT
        discharged by B1-09b or by B1-10;                                                (F-10.1)
      • every CLASS B2 fixture has a structural-rejection test here, a non-empty written rationale
        for why no meaningful provider-neutral counterpart exists, NO E2-A fixture, and no invented
        E2-A reason code or DTO shape; a test asserts no such E2-A fixture has been fabricated, and
        that the E2-A 9.3.2 / 9.3.4 properties the rationale rests on are unchanged.
    No fixture is seeded by circumventing a shipped constraint; the actual constraint/index set on
    the new tables matches section 5.6 exactly, so nothing has silently migrated between classes in
    either direction; and the acceptance record carries the full section 5.7 manifest together with
    the justified fail-closed reason-code exclusion list. A structural rejection is never recorded
    as satisfying an E2-A semantic rule, and class B2 is never recorded as satisfying one either —
    it records that there is no semantic rule to satisfy.                                  (F-10)
N4. The A/B1/B2 taxonomy is correctly SCOPED, and every valid-shape and non-store scenario is
    covered. The union of section 5.7's A/B1/B2 manifest, section 5.7's V-01 to V-12 list and
    section 5.7A is the whole negative, valid-shape and conformance corpus of both documents, and
    the three groups are pairwise disjoint; a coverage test asserts the partition is disjoint and
    exhaustive, that the counts are 29 authority-store negative fixtures, 12 valid-shape parity
    scenarios and 46 non-store scenarios, and that no retired
    ID (A-03, A-12, A-16, A-18, A-19, A-20) has been reused. Every section 5.7A scenario carries a
    seam drawn from the closed list in that section, an executable test obligation, an expected
    outcome/status/reason/evidence where meaningful, BOTH store answers (PG-DATA and SUBJ, the
    latter NO on every row by construction), and an explicit parity statement; every
    parity-YES scenario is demonstrated through both named compositions; and NS-K-01's three
    executable parts (unreachability property test, defensive-branch assertion returning
    AUTHORITY_VERSION_AMBIGUOUS, and reason-rank totality) and NS-K-02 exist and execute in E2-A.
    The 5.7A table is TOTAL over the scenarios the CURRENT normative text of E2-A §18 and section 9
    already makes mandatory and whose malformed or negative subject is not stored authority state —
    specifically including the actor-to-person trust boundary, synthetic/production provider
    reachability, the server-captured live as_of and single-clock rule, the prohibition on a
    caller-selected as_of or recorded-time cutoff and on the historical resolver as a live
    authorization path, provider fact-fidelity, aggregation across multiple legitimate qualifying
    paths, relevant-corrupt state not being masked by a valid path, result-level reason selection,
    deterministic defect ordering, and complete / nonqualifying / partial denial evidence with its
    deterministic ordering. No
    sentence in this document claims that every negative or conformance scenario carries an A/B1/B2
    class, that a valid stored shape carries one, or that PostgreSQL must store a provider-failure,
    HR-state, request-input, orchestration, ordering or evidence scenario.
                                                            (F-10.2, F-10.3, F-10.3a, F-10.3b)
O.  Old immutable evidence remains dereferenceable and byte-identical after later versions,
    retractions and corrections; denial and partial-evaluation evidence survive persistence
    unchanged, with no fabricated object/version pairs.                                      (F-06)
P.  The production composition seam binds only the authority configuration provider and either
    refuses to compose or fails closed deterministically with the provider-not-configured reason
    codes. Synthetic/reference actor-person and HR providers are proved unreachable from production
    imports and wiring, and cannot be selected by any configuration switch.                  (F-04)
Q.  No document, handoff, acceptance record or comment produced by this package claims a
    production-callable business-authority resolver.                                         (F-04)
R.  No production mutation surface for published authority configuration exists anywhere.
S.  No production authority configuration, assignment or bootstrap holder is seeded; Q-10 remains
    untouched and unanswered.
T.  No HTTP route, schema, business event or frontend change is introduced.
U.  No CRM/Hiring/Authorization-owned HR or organisation master is created, and no provider-specific
    HR detail is persisted.
V.  Every PF-1A-E1 protection is intact and unmodified (section 7), re-demonstrated with real
    evidence; every PF-1A-E2-A test passes unmodified.
W.  Empty-database migration validation passes; `alembic current` == `alembic heads`; exactly one
    head remains.
X.  Full backend regression passes; tracked-secret scan passes; `git diff --check` is clean.
Y.  Docker clean start passes (infrastructure/schema changed).
Z.  A fresh, independent bounded review returns ACCEPTED with no blocking findings.
```

Acceptance is recorded by the independent reviewer, never by the implementation agent.

## 11. Allowed and disallowed file areas (for the future E2-B implementation package)

Indicative, to be confirmed in the bounded implementation package. **This document does not
authorize any of these edits; it scopes them.**

Allowed:

```text
backend/app/modules/authorization/business_authority/    persistence models, PostgreSQL repository,
                                                         DB-backed configuration provider, and the
                                                         PRODUCTION composition seam (which binds
                                                         no synthetic provider - section 5.3)
backend/app/models_metadata.py                            model registration only - one import line
                                                          group; no other change
backend/alembic/versions/<new revision>_pf_1a_e2_b_*.py   exactly one new revision
backend/tests/test_business_authority_*.py                persistence, provider-fidelity,
                                                          defect-visibility, wiring and parity tests
backend/tests/fixtures/pf_1a_e2_*.py                      synthetic scenario corpus, DB fixtures and
                                                          the TEST-ONLY composition that may bind
                                                          synthetic actor-person / HR providers
docs/agent/pf-1a/                                          this package's documents
docs/agent/acceptance/pf-1a-e2-b-*.md
docs/continuity/                                           handoff / review / closure records
```

Disallowed (high risk — changing any of these without separate authorization is a blocking finding):

```text
backend/app/modules/authorization/contract.py       E1 permission catalogue/matrix
backend/app/modules/authorization/dependencies.py   require_permission(...)
backend/app/modules/authorization/service.py        has_permission(...)
backend/app/modules/authorization/repository.py     E1 repository
backend/app/modules/authorization/models.py         AuthzPermission / AuthzRolePermission
backend/app/modules/identity/**                      AppUser / AuthUser / Role / UserRole /
                                                     dependencies (in particular: do NOT add
                                                     person_id to AppUser or AuthUser)
backend/alembic/versions/<all existing revisions>    never edit a released revision
backend/app/modules/{accounts,commercial_offers,leads,opportunities,work_orders,
                     terms_and_conditions,events,documents,workflow}/**
backend/app/main.py                                  no new router is mounted by this package
backend/tests/test_authorization_*.py                existing E1 tests
backend/tests/fixtures/pf_1a_e1_baseline_authorization.py
frontend/**
docs/agent/contracts/**                              approved contracts (ORA-001, RMR-001, ...)
docs/agent/pf-1f-hr/**                               PF-1F-HR accepted documents
```

The accepted E2-A kernel, ports, reason codes and evidence DTOs are also effectively disallowed:
they may be imported and reused, never edited. A required change there is a reconciliation finding
against E2-A, raised and reviewed as such, not an E2-B edit.

Shared-file note: `backend/app/models_metadata.py` and the Alembic head are **shared resources**.
Per `INDEPENDENT_IMPLEMENTATION_REVIEW_WORKFLOW.md` ("Parallel branch controls"), only one active
package may own the migration head at a time, and the controller assigns the slot. If the assigned
parent is no longer valid when implementation begins, stop and report rather than re-parenting
unilaterally.

## 12. Documentation obligations at implementation time

```text
- this package document, updated with the actual implementation outcome (including the ACTUAL
  baseline commit, the ACTUAL migration revision id and its ACTUAL parent, and which production
  composition option - refuse-to-compose or fail-closed - was chosen);
- docs/agent/acceptance/pf-1a-e2-b-*.md acceptance record, which MUST carry the section 5.7
  verification-class manifest in full: every CLASS B1 defect class with the constraint that rejects
  it, the named E2-A test that proves its fail-closed semantics and that test's BOUNDARY; every
  CLASS B2 defect class with the constraint that rejects it and its written rationale for why no
  meaningful provider-neutral counterpart exists; the statement that both are excluded from
  PostgreSQL parity for structural reasons and not exempted semantically; and, in the same manifest,
  the JUSTIFIED fail-closed reason-code exclusion list, each entry marked class B1/B2 (naming the
  constraint, and for B1 the covering E2-A test) or kernel-internal (naming the E2-A test);
- a docs/continuity/ implementation handoff recording baseline commit, proposed scope, exact test
  commands and real counts, self-review findings, limitations and deferred items - including an
  explicit statement of the two unmet authoritative-provider dependencies;
- a docs/continuity/ closure record at integration;
- PLAN.md / NEXT_STEPS.md / AGENT_HANDOFF.md current-state reconciliation AT PACKAGE CLOSURE - not
  by this definition document, which must not touch them.
```

## 13. Independent-review attack surface

A reviewer of the E2-B implementation must attack at least the following, in addition to
re-checking the E2-A attack surface (that document's section 22) against the wired system. Each is
a blocking finding if reachable.

```text
1.  Any write path to published authority configuration - repository method, service function,
    dependency, admin helper, or a test/seed helper reachable from production runtime.
2.  A schema or code link between the `role` (Application/Login Role) table and any Business
    Authority Role table; or a Business Authority derived from an E1 role code.
3.  Any hidden ADMIN bypass surviving into the persisted path.
4.  Client-supplied person_id, or a caller-selected as_of, reaching a current authorization decision
    after wiring.
5.  More than one clock/instant used once real I/O latency exists between port calls.
6.  A published version row that can be UPDATEd to close, correct, deactivate or reactivate it; any
    UPDATE or DELETE against a version or retraction row.
7.  active_flag persisted as a computed/derived column, on the stable-identity row, as a mutable
    field, or filtered out anywhere in the store.                                            (F-01)
8.  A `list_effective_*` operation, or any provider query filtering by effective time, active_flag,
    scope, parameters or "latest version"; discovery returning versions instead of stable
    identities; discovery narrowed by anything other than the stable identity/reference/code
    columns.                                                                                 (F-02)
8a. A NOT EXISTS over the retraction table - or any equivalent anti-join, filtered index, view or
    ORM default scope - inside a discovery query, so that a MALFORMED retraction can remove the only
    requested-code-bearing or reference-bearing version before the kernel ever sees it. Read the
    generated SQL, not just the repository docstring. Probe: seed a dangling/duplicated retraction on
    that sole version and check the result is the lineage defect's own reason code, not
    AUTHORITY_CODE_NOT_CONFIGURED / NO_CANDIDATE_ASSIGNMENT / an empty candidate set.        (F-07)
8b. published_at or retracted_at used as a filter, a business-effective bound or a "known as at"
    cutoff; a recorded-time parameter exposed on any port operation; recorded timestamps defaulted,
    rewritten or regenerated on read rather than stored faithfully; a cross-row recorded-timestamp
    constraint that REJECTS impossible provenance at write time and thereby prevents the kernel from
    being proved to fail closed on it.                                                       (F-07)
9.  get_lineage omitting retracted, inactive, future-dated or superseded versions; omitting
    retraction assertions; returning a truncated set as COMPLETE; or computing closure,
    effectiveness, ranking or deduplication in SQL or in the repository.                     (F-02)
10. Any E2-A semantic rule re-implemented, approximated or pre-validated inside the provider.
11. A provider error, timeout or UNAVAILABLE completeness degraded to an empty result or to
    DENY + RESOLVED.                                                                          (F-02)
12. A schema constraint, trigger or index that forbids a valid temporal gap, rejects overlapping
    versions, enforces uniqueness or exclusion on (stable_object_id, effective_from) and so rejects
    duplicate temporal starts, enforces retraction uniqueness, foreign-keys a retraction to a
    specific version row, constrains corrects_object_version, closes parameter_evaluator_type or
    scope_type to a known-value enum, rejects impossible recorded provenance at write time, stores a
    derived asserted_effective_to / is_current artefact, or otherwise prevents the kernel from
    classifying lineage - thereby suppressing a defect class or rejecting valid history.
                                                                     (F-05, F-07, F-09, F-10)
12a. NORMALIZATION on write or on read: an explicit declared_effective_to truncated to the
    successor's effective_from; a NULL declared end rewritten to a concrete value; versions
    coalesced, merged, split, reordered or renumbered; a retracted row physically deleted or hidden
    behind a default scope. Probe by inserting V1 [t0, t3) with V2 from t2 (t0 < t2 < t3), reading
    the rows straight back, and asserting they are byte-identical - then asserting the kernel reports
    AUTHORITY_LINEAGE_CONTRADICTORY rather than resolving V1 as [t0, t2).                    (F-09)
13. first()/LIMIT 1/scalar()/DISTINCT ON hiding multiplicity or ambiguity.
14. Non-deterministic ordering: a result that depends on physical row order, insertion order, table
    reorganisation, concurrency, or an ORDER BY that is not total; a result_level_reason that moves
    when two defects share a stage and the rows are reordered - i.e. the E2-A 15.5 total defect
    order being effectively supplied by the database instead of by the kernel.               (F-08)
15. A parity gap: any scenario where the PostgreSQL provider and the E2-A reference provider
    disagree on outcome, status, result-level reason, qualifying-path set/order, complete
    nonqualifying-path set/order or their reasons, partial-evaluation set/order or their stages,
    established_state, or any evidence field.                                          (F-03, F-06)
16. A parity corpus that omits active-state cases, any PERSISTABLE branch of the derived-closure
    rule (successor closure, adjacency, gap and reactivation as V-01 to V-04; EXPLICIT OVERLAP and
    duplicate start as class A fixtures A-01/A-02), raw-discovery/retraction cases,
    recorded-time-versus-business-effective-time cases, scope-composition cases, mixed-path
    aggregation cases (NS-AG-*), same-stage multi-defect ordering cases (NS-DO-*), or the
    evidence-contract cases (NS-EV-*); or that omits a fail-closed reason code without that code
    appearing on the section 5.7 justified exclusion list; or an exclusion list padded with a code
    that IS reachable. Probe AUTHORITY_CODE_NOT_CONFIGURED specifically: it moved from class A
    fixture A-12 to non-store scenario NS-RS-01 and must still be parity-covered through that route.
                                             (F-01, F-03, F-05, F-07 to F-10, F-10.3a, F-10.3b)
16a. VERIFICATION CLASS ERRORS (section 5.7 and E2-A 9.7). A parity obligation stated for a shape
    this schema forbids storing - the cycle-3 defect itself, so read section 9 and criterion 10.N
    against section 5.6 line by line rather than trusting either in isolation. Also: a class B1 or
    B2 fixture smuggled into the parity corpus by disabling, deferring or dropping a constraint in a
    fixture, or by an ALTER in a test setup, so a "pass" says nothing about the shipped schema; a
    class B1 shape whose named E2-A test does not exist, is skipped, is xfailed, or was deleted
    "because the database prevents that"; a class B1 shape whose E2-A test exercises a DIFFERENT
    boundary than 5.7 names for it - in particular B1-06/B1-07 (missing effective_from /
    active_flag) asserted as kernel fixtures rather than at the DTO/port well-formedness boundary,
    or B1-02/B1-03/B1-04/B1-05/B1-08a/B1-08b/B1-09a/B1-09b/B1-10 quietly moved into a DTO validator
    so they can never reach the kernel; a class B1 shape with no NORMATIVE expected reason code,
    left to the
    implementer to choose; a class A shape reclassified into B1 or B2 by adding a structural
    constraint that suppresses it; a fixture in more than one class or in none; a class manifest
    missing from the acceptance record; a structural rejection described anywhere as satisfying an
    E2-A semantic rule rather than as a verification-placement decision.                     (F-10)
16b. CLASS B2 ABUSE (section 5.7 and E2-A 9.7). B2 used as a semantic escape hatch rather than as a
    statement about this store's own identity/parentage representation. Probe each of the three B2
    entries with E2-A 9.7's deciding test yourself: could a conforming provider present that state
    through the E2-A 9.3.2/9.3.4 fields at all? For B2-01 and B2-02 the answer must be no because
    object_id is on the LineageMaterial CONTAINER; for B2-03 it must be no because the state decodes
    onto class A fixture A-11. If any answer is yes, the fixture is B1 or A and the classification
    is wrong. Also: a B2 entry with a missing, circular or "E2-A has no test for it" rationale; a
    FOURTH structural constraint quietly classified B2 without that test being applied; an invented
    E2-A reason code, DTO field or fake DTO shape added to mirror one of these foreign keys; the
    stable-identity FK extended to also reject a stable identity row that exists with no version
    rows, which would silently swallow class A fixture A-11; a change to E2-A 9.3.2 or 9.3.4 that
    makes a B2 state expressible without the fixture being reclassified to B1.               (F-10)
16c. TAXONOMY SCOPE ERRORS (section 5.7 entry test, 5.7A, E2-A 9.7.0). Any manifest row whose
    "PG may store" cell reads "N/A" while carrying an A/B1/B2 label - that combination is
    self-contradictory and is the exact F-10.3 defect. Conversely: a scenario moved into 5.7A and
    left without a named seam, an executable obligation, an expected result, BOTH store answers or a
    parity statement, which converts a category fix into silent coverage loss; a 5.7A scenario
    attached to a seam not on that section's closed list, i.e. an invented provider surface; an item
    appearing in more than one of the three groups or in none; a retired ID (A-03, A-12, A-16, A-18,
    A-19, A-20) reused for a new fixture; the
    parity corpus quietly reduced to class A only, dropping the V-scenarios or the parity-YES
    non-store scenarios that former A-12/A-16/A-18/A-19/A-20 used to carry - check specifically that
    AUTHORITY_CONFIGURATION_UNAVAILABLE, AUTHORITY_CODE_NOT_CONFIGURED, the actor/HR codes,
    SCOPE_CONTEXT_MISSING and EVALUATOR_FACTS_INVALID are still parity-covered through NS-PT-01,
    NS-RS-01, NS-AP-*, NS-HR-* and NS-RQ-*;
    and any sentence anywhere in either document still claiming that EVERY negative or conformance
    scenario carries an A/B1/B2 class, or that PostgreSQL must store a provider-failure, HR-state or
    request-input scenario.                                                              (F-10.3)

16e. VALID STATE WEARING A NEGATIVE-FIXTURE LABEL (F-10.3a). Class A's defining obligation is to
    store a CONTRADICTORY state and read it back; an entry whose seeded rows are entirely VALID
    cannot discharge it, however fail-closed its resolver outcome. Probe each A/B1/B2 entry with one
    question: does E2-A require the kernel to REJECT this state as invalid? For A-01, A-02, A-04 to
    A-11, A-13 to A-15 and A-17 the answer must be yes. If any entry's honest answer is "no, the
    configuration is valid and this is simply what it means at this as_of", the entry is a V-scenario
    or a 5.7A scenario and the classification is wrong - that is exactly how A-12 came to be class A.
    Also: a V-scenario (V-01 to V-12) described anywhere as "class A"; a valid closure, gap,
    adjacency or reactivation shape quietly dropped from the parity corpus on the grounds that it
    "is not a negative fixture"; the E2-A 11.5 asymmetry softened - the REQUESTED authority must
    still fail closed with AUTHORITY_CODE_NOT_CONFIGURED inside a valid gap - on the pretext that
    NS-RS-01 is "only" a conformance scenario.                                          (F-10.3a)

16f. NON-STORE TABLE NOT TOTAL (F-10.3b). A mandatory obligation stated in E2-A §18 or section 9
    whose malformed/negative subject is not stored authority state, and which carries no 5.7A
    scenario ID. Probe the categories the correction was written against, and confirm each has a
    live ID and an executing test: actor-to-person trust boundary (NS-AP-04);
    synthetic-versus-production provider reachability and the production composition's behaviour
    (NS-PR-01, NS-PR-02); provider fact-fidelity (NS-PR-03); server-captured live as_of and the
    single-clock rule (NS-RS-02); no caller-selected as_of, no recorded-time cutoff, historical
    resolver not a live authorization path (NS-RS-03); recorded time never a lineage filter
    (NS-RS-04); multiple legitimate qualifying paths (NS-AG-01); relevant-corrupt state not masked
    by a valid path (NS-AG-03); result-level reason selection (NS-AG-05); deterministic defect
    ordering (NS-DO-01..06); complete, nonqualifying and partial denial evidence and its
    deterministic ordering (NS-EV-01..05). Also probe the inverse: a scenario ID invented for an
    obligation no current normative sentence actually states, which is padding rather than totality.
                                                                                        (F-10.3b)
16d. DEFERRED CLASSIFICATION, and the A-03 decision. Any manifest entry whose class, storability,
    expected reason code or parity obligation is written as conditional on what the implemented
    kernel turns out to do. Probe the specific case: A-03 must be ABSENT from the manifest, the
    parity corpus, the DEFECT VISIBILITY block and the counts; its ID must be recorded as retired
    and unreused; no test may attempt to seed a residual-multiplicity state, including by disabling
    a pre-check or hand-editing kernel internals inside a persistence test; NS-K-01 must exist with
    all three executable parts; and AUTHORITY_VERSION_AMBIGUOUS must be on the CLOSED
    parity-exclusion list as kernel-internal rather than merely unmentioned. Read E2-A 11.4a and
    check the theorem yourself rather than accepting the conclusion - if the theorem is wrong, the
    fixture must come back as class A with full parity, and that is a reconciliation finding against
    E2-A 11.4, not a local fix here.                                                     (F-10.2)
17. Evidence that stops dereferencing, or changes content, after later versions/retractions/
    corrections; a denial that loses its four object/version pairs through persistence; a partial
    evaluation that gains fabricated placeholder pairs.                                       (F-06)
18. A production composition that binds, imports, defaults to, falls back to, or can be configured
    into a synthetic/reference actor-person or HR provider; a synthetic provider importable from a
    production module; a feature flag or environment variable that switches identity/HR state.
                                                                                              (F-04)
19. A production composition that neither refuses to compose nor fails closed deterministically -
    for example one that silently returns DENY + RESOLVED, or that appears usable.            (F-04)
20. Any claim, in code comments, docs, handoff or acceptance records, that E2-B delivers a
    production-callable or production-usable business-authority resolver.                     (F-04)
21. A kernel change smuggled in as "needed for persistence".
22. A local HR/person/organisation/position table, view, cache or foreign key.
23. Provider-specific HR detail (SharePoint Item ID, Plum field, employee name, raw provider
    timestamp, Source Binding reference) persisted in any authority table.
24. Any executable expression, SQL fragment, template or code stored in parameter_payload.
25. Unparameterized SQL, string-interpolated identifiers, or any injection-capable query
    construction.
26. T-SQL constructs, a dual-dialect branch or a per-dialect compatibility layer (ADR-028).
27. A migration that alters an existing table/column/constraint/index, edits a released revision,
    creates a second head, or seeds any authority configuration.
28. A migration parent taken from documentation rather than the actual verified head.
29. Any production authority data, real assignment, or a real bootstrap/meta-authority holder
    appearing in the migration or in a non-test path.
30. Synthetic bootstrap provenance presented or relied upon as production bootstrap, or as a
    resolution of Q-10.
31. Any weakening of E1 permissions, the compatibility matrix, the route inventory or the
    route-migration guard - including indirectly, through a shared import or a changed constant.
32. Test residue: rows left behind in the new tables or in business_event after a test run.
33. Configuration-governance functionality (proposal, authorization, activation, self-escalation
    control) partially implemented here instead of in E3.
```

Risk classification for the bounded review method: **high** — security/authorization boundary,
schema/migration risk, and workflow/lifecycle/state-machine characteristics. Apply the core rubric
of `BOUNDED_INDEPENDENT_REVIEW_METHOD.md` section G with the workflow/lifecycle overlay
(section H.2), and treat the list above plus E2-A section 22 as package-specific overlay items.

## 14. Business-decision assessment

```text
Q-10 (first production AUTHORITY_CONFIGURATION_ADMIN holder)
    OPEN. A genuine PBL governance decision. Blocks production authority activation and any real
    bootstrap. Does NOT block PF-1A-E2-B implementation or its synthetic testing. E2-B must not
    seed, choose, imply or pre-empt a real holder, and must not describe its synthetic fixtures as
    resolving it.

Q-09 (stable Plum Employee ID reliability)
    OPEN, and NOT a business decision. A source-capability/reconciliation question. Blocks nothing
    here; canonical person_id is platform-owned.

Deferred parameter values (HR staleness threshold; evidence retention)
    Remain deferred policy parameters. Do not invent defaults; fail closed on missing or stale
    required state.

Absence of authoritative actor-person and HR providers
    NOT a business decision and NOT a blocker to this package. It is a scheduled engineering
    dependency, handled by the production dependency seam in section 5.3, and the reason E2-B does
    not deliver a production-usable resolver.

Raw discovery, recorded-time semantics, total defect ordering, non-normalizing storage of the
E2-A 11.4 lineage shapes
    Engineering/persistence problems raised by the second independent review (F-07, F-08, F-09) and
    settled in E2-A sections 9.3.1, 11.4, 11.8 and 15.5 and in sections 5.2, 5.6 and 9 here. NOT PBL
    decisions. The deliberate exclusion of point-in-time recorded-knowledge ("as known at") replay
    from E2 is a scope decision recorded in E2-A 11.8.1; if PBL later requires audit replay, that is
    separately authorized work and does not reopen this package.

Which malformed shapes PostgreSQL may reject structurally, and where the excluded ones are proved
    An engineering VERIFICATION-CONTRACT problem raised by the third independent review, found only
    partly closed by the fourth, and settled by the THREE CLASSES in E2-A section 9.7 with the
    binding, TOTAL assignment in section 5.7 here. NOT a PBL decision: it concerns which constraints
    a relational schema enforces, which test demonstrates which rule, and - for the three
    stable-identity foreign keys - whether the invariant a constraint protects exists in the
    provider-neutral contract at all. No fail-closed behaviour, no reason code and no semantic rule
    changed; no reason code was invented and none was removed.

The scope of that verification taxonomy, the reachability of the residual multiplicity state, and
per-shape provenance coverage (the three F-10 FINAL closure items)
    Engineering VERIFICATION-CONTRACT problems raised by the fourth independent review and settled
    by the F-10 FINAL closure in E2-A 9.7.0, 11.4a, 11.7 and 18 and in sections 5.6, 5.7, the new
    5.7A, 9, 10.E/N/N3/N4, 13.16c/16d and 15 here. NONE is a PBL decision:
      - WHICH universe a storability class applies to is settled by inspecting E2-A's own port
        contract, not by business policy;
      - WHETHER ">1 effective version after the pre-checks" is reachable is a THEOREM over rules
        E2-A already stated (11.4a). Deferring it to implementation time was a defect, not a genuine
        open choice, and deciding it invented no rule;
      - WHETHER an ABSENT publication_reference_type and an UNKNOWN one are the same malformed state
        is a question of fact about the contract's own DTO shape.
    No fail-closed behaviour, reason code, evidence obligation or genuinely applicable parity
    obligation was added, removed or weakened in settling them; the only thing removed was a
    PostgreSQL storage obligation that was never executable for a subject this store never holds.
```

**No unresolved PBL business decision blocks PF-1A-E2-B.** If one is discovered during
implementation or review, stop and escalate rather than choosing a business answer.

## 15. Standalone continuation contract

*A fresh implementation or review chat should be able to act safely from the repository plus this
section and the E2-A document, with no dependence on any prior conversation.*

**Package status — HISTORICAL DEFINITION-TIME STATUS.** For present repository and review status,
see the document's CURRENT CONTROL STATE (section 1.0G). At definition time, PF-1A-E2-B was a
**proposed definition**, corrected three times after three independent reviews (section 1.1), and
was **not startable yet**; it could start only after PF-1A-E2-A was implemented, independently
reviewed, ACCEPTED and integrated on `main`. That precondition has since been met, and this package
has since been implemented and undergone independent review and correction; see the CURRENT
CONTROL STATE (section 1.0G) for the full present-state record. This document remains the
normative definition below and is not itself acceptance of anything; PF-1A-E2-B is not accepted
merely because implementation occurred.

**Source-of-truth precedence.**

```text
1. Current explicit human instruction or approved decision
2. Frozen contracts and approved architecture decisions (ORA-001, RMR-001, ADR-026/028/030/032/033)
3. Accepted requirements and active acceptance criteria
4. Current module contracts and active implementation documentation (the ACCEPTED E2-A document
   first, then this one)
5. Current source/reference documents
6. Historical continuity records and superseded drafts
```

**Predecessors and dependencies.** PF-1A-E1 COMPLETE and INTEGRATED. PF-1F-HR-E1 COMPLETE
(`READY_FOR_PF_1A_DESIGN_IMPLEMENTATION` MET; `READY_FOR_PRODUCTION_AUTHORITY_ACTIVATION` NOT MET).
PF-1A-E2-A must be accepted and integrated before this package begins; its accepted kernel and
contract are the specification E2-B persists. **Two authoritative providers — actor→canonical-person
and canonical HR/organisation — do not exist and are supplied by a later authorized package;**
E2-B defines the production seam for them and must not substitute synthetic providers.

**Terminology.** The four concepts from E2-A section 4 — Application/Login Role, Application
Permission, Business Authority Role, Business Authority — must never be collapsed, and must be
visibly distinct in table and column names. Section 4 above.

**Settled invariants that must not be reopened.**

```text
- Business consumers request authority by authority_code only.
- No Business Authority is ever derived from an Application/Login Role, including ADMIN.
- Backend authorization is authoritative.
- PF-1A owns no Employee/Organisation/Position master; canonical HR identifiers are opaque here.
- Provider-specific HR detail never crosses the canonical boundary or reaches a table.
- Published authority versions are immutable; history is append-only; closure is DERIVED, never
  stored.
- active_flag is an immutable published value on a version row, not temporal effectiveness, never
  computed, never filtered out by the store.
- A valid temporal GAP is valid history; the schema must permit it, and must also permit
  contradictory lineage to be STORED - including a CONTRADICTORY EXPLICIT OVERLAP (declared end
  later than the next valid successor's start), a duplicate start, a duplicated or dangling
  retraction, a correcting version with a missing or unretracted target, a reference to an existing
  stable identity carrying no lineage material, an unknown evaluator type, a malformed payload, an
  unsupported scope_type, and impossible recorded provenance - so the kernel can classify each of
  them. These are the CLASS A shapes of section 5.7 (the fourteen fixtures A-01, A-02, A-04 to A-11,
  A-13 to A-15, A-17) and each is owed FULL PostgreSQL parity. The VALID lineage shapes themselves -
  successor closure, adjacency, the gap, reactivation - are equally owed parity but are NOT class A:
  they are the VALID-SHAPE PARITY SCENARIOS V-01 to V-12 of section 5.7 and carry no class label.
- THE TAXONOMY IS SCOPED, AND THERE ARE THREE GROUPS, NOT TWO (E2-A 9.7.0; entry test in section
  5.7). A/B1/B2 classifies ONLY negative fixtures whose subject is a MALFORMED OR CONTRADICTORY
  published authority-store state - the only universe in which "can PostgreSQL store it?" is a
  meaningful question and in which class A's store-the-contradiction obligation is executable.
  A VALID stored shape is a VALID-SHAPE PARITY SCENARIO (V-01 to V-12, section 5.7): no class label,
  not a negative fixture, still fully parity-owed. Everything whose subject is a SEAM - actor and HR
  provider states, authority-configuration PORT read/transport failure and provider fact-fidelity,
  provider reachability, request-side scope and evaluator input, resolver/as_of and clock behaviour,
  aggregation and relevance, deterministic defect ordering, the evidence contract, and pure-kernel
  invariants - is a NON-STORE scenario in section 5.7A, carrying no class but a named seam, an
  executable obligation, an expected result, BOTH store answers and an explicit parity statement.
  "N/A" is never a storability answer for a classified fixture. A FAIL-CLOSED OUTCOME NEVER BY
  ITSELF MAKES AN ITEM A NEGATIVE FIXTURE: the former A-12 produced AUTHORITY_CODE_NOT_CONFIGURED
  from entirely valid rows and is now NS-RS-01. Moving an item to 5.7A, or recognising it as a
  V-scenario, drops only an unexecutable MALFORMED-state storage obligation; it drops no fail-closed
  rule, expected reason, evidence obligation or applicable parity requirement.
- NO CLASSIFICATION IS DEFERRED. In particular the residual ">1 effective version" state is DECIDED,
  not conditional: E2-A 11.4a proves it unreachable on every provider, so it is absent from the
  manifest, the parity corpus and the counts, its former ID A-03 is retired, and the invariant is
  carried by pure-kernel self-check NS-K-01 with AUTHORITY_VERSION_AMBIGUOUS as its normative code.
- THREE VERIFICATION CLASSES (E2-A 9.7; binding, TOTAL assignment in section 5.7). Semantic validity
  is provider-neutral; verification PLACEMENT is not.
      CLASS B1 - twelve shapes this schema rejects at write time that ARE representable
      provider-neutrally, ONE SHAPE PER MANIFEST ID: a duplicate (object_id, object_version); an
      assignment carrying both targets; one carrying neither; declared_effective_to < effective_from;
      declared_effective_to == effective_from; an absent published_at; an absent retracted_at; an
      ABSENT publication_reference_type; an absent publication_reference_id; a
      publication_reference_type outside the two defined values; and - at the
      DTO/port well-formedness boundary rather than the kernel - a missing effective_from or
      active_flag. Prove the DB rejection here, rely on E2-A's permanent direct tests AT THE NAMED
      BOUNDARY for the semantics, and EXCLUDE them from the parity corpus, naming each exclusion and
      its covering E2-A test in the acceptance record. The ID-to-fixture mapping is one-to-one: an
      absent provenance TYPE and an unknown provenance TYPE are two different malformed states with
      two different fixtures (B1-09a / B1-10), and one never discharges the other.
      CLASS B2 - the three stable-identity FOREIGN KEYS (a version row, a retraction row, or a
      rule/assignment reference whose stable identity ROW does not exist). These have NO
      provider-neutral counterpart: E2-A 9.3.2 carries object_id on the LineageMaterial CONTAINER,
      so a version or retraction cannot be orphaned at that boundary, and an identity carrying no
      material decodes to class A fixture A-11. Prove the DB rejection here, exclude them from the
      parity corpus AND from every E2-A fixture manifest, and record the written rationale.
  Never treat a structural rejection as satisfying an E2-A semantic rule; never delete an E2-A
  direct test because the schema now rejects the shape; never add a structural constraint that would
  move a class A shape into B1 or B2; and never use B2 for a malformed BUSINESS state - apply E2-A
  9.7's deciding test first; and never use the 9.7.0 scope statement as an escape hatch either -
  a scenario that leaves A/B1/B2 keeps every obligation except the MALFORMED-STATE storage one,
  restated in 5.7A or in the V-list.
  Every MALFORMED authority-store negative fixture carries exactly one class, every valid-shape
  scenario carries none and stays in the parity corpus, every non-store scenario carries
  a seam, an obligation and both store answers, and every fail-closed
  reason code omitted from parity sits on section 5.7's explicit, justified, CLOSED exclusion list:
  ASSIGNMENT_TARGET_INVALID (class B1, B1-02/B1-03), AUTHORITY_VERSION_AMBIGUOUS (kernel-internal,
  NS-K-01) and INTERNAL_CONTRACT_VIOLATION (kernel-internal, NS-K-02). Nothing on it is conditional.
- NOTHING IS NORMALIZED. What was published is what is stored and what is returned, byte-identical.
  Never truncate an explicit declared end to a successor's start, never rewrite a NULL end, never
  merge/split/reorder/renumber versions, never hide a retracted row.
- E2-A owns semantics; E2-B owns facts. The provider supplies complete lineage material and RAW,
  identity-only candidate discovery, and duplicates no semantic rule. Retraction is a FACT to
  return, never a discovery or lineage filter - no NOT EXISTS over the retraction table, anywhere.
- published_at / retracted_at are recorded-time evidence and kernel validation input only. They are
  never a filter, never a business-effective bound, and no port operation exposes a recorded-time
  cutoff. The historical resolver performs corrected business-effective reconstruction, not
  recorded-knowledge replay (E2-A 11.8).
- Scope composition (intersection, GLOBAL as top), path aggregation precedence and the TOTAL
  fail-closed defect order (E2-A 15.5) are E2-A semantics; E2-B only proves parity and determinism
  on them - the database must never be what decides which defect is reported first.
- Denial and failure evidence are first-class and must survive persistence unchanged, with no
  fabricated object/version pairs.
- A historical decision retains its decision-time authority snapshot, dereferenceable forever.
- Missing, stale, ambiguous or contradictory authoritative state fails closed.
- is_protected_meta_authority is a data field, never a hard-coded code-string comparison.
- Administering authority and holding a business authority are separate capabilities.
- Synthetic/reference providers are test-only and are never bound by a production composition.
- PostgreSQL is the only supported runtime (ADR-028); write PostgreSQL SQL, never T-SQL.
- ADR-007 identifier conventions apply.
```

**Unresolved business decisions.** Q-10 (open, blocks production activation only) and Q-09 (open,
not a business decision). Neither blocks this package. Section 14.

**E1 compatibility boundary.** Section 7, in full. Preserve the protections; do not adopt historical
test totals as targets.

**HR/organisation ownership boundary.** Section 8, in full — including the specific persistence
prohibitions (no local HR table, no foreign key on canonical identifiers, no snapshot caching).

**E2-A / E2-B / E3 split and why.** Resolving existing published authority and changing who holds
authority are distinct security problems. E2-A defines and implements the semantics with no
persistence; E2-B persists that accepted model and supplies a read-only PostgreSQL provider of
facts to an unchanged kernel; E3 implements governed Configuration Change, authorization,
publication, activation-time risk recomputation and preventive self-escalation control. E2-B must
contain no part of E3.

**Current-versus-historical temporal rule.** Unchanged from E2-A: `resolve_current_authority`
captures one server-side instant and accepts no caller-selected `as_of`; `resolve_authority_as_of`
is for audit/reconstruction/testing only and must never authorize a new current action. Wiring must
not create a path that reintroduces a caller-controlled instant.

**Canonical time semantics.** Half-open intervals: `effective_from <= as_of AND
(asserted_effective_to IS NULL OR as_of < asserted_effective_to)`, plus not validly retracted.
Asserted closure is derived from the append-only lineage per the E2-A 11.4 asserted-interval rule —
successor closure for a NULL end, honoured declared end otherwise, valid gap when the declared end is
earlier than the successor's start, valid adjacency when equal, fail closed when later — and is never
stored on the row. Effectiveness is temporal only; `active_flag` is a separate, third
grant-eligibility condition (E2-A 8.2). Recorded time (`published_at`, `retracted_at`) is a separate
axis: stored faithfully, validated by the kernel (E2-A 11.8.3), never an authorization clock and
never a filter.

**Fail-closed taxonomy.** Two dimensions (`ALLOW`/`DENY` × `RESOLVED`/`FAIL_CLOSED`) with E2-A's
path-level and result-level reason codes, its aggregation precedence and its TOTAL defect order
(E2-A 15.5) selecting `result_level_reason` and sequencing the partial/failed evidence. The persisted
provider must lead to exactly the same codes AND the same ordering as the reference provider for
every equivalent state **this store can hold** — that equivalence is the parity test, its scope is
the class A set of section 5.7 **plus the valid-shape scenarios V-01 to V-12 of section 5.7 plus the
parity-YES non-store scenarios of section 5.7A**, and it
must hold under differing physical row order and
concurrency. States the schema forbids storing are class B1 or class B2: B1 is proved by a rejection
test here plus E2-A's direct test at the boundary 5.7 names, B2 by the rejection test alone with a
written rationale, and both are excluded from parity by construction rather than by omission. States
no provider can present at all (NS-K-01, NS-K-02) are excluded for a third, different reason: a
parity test would have no second side to run. Any
fail-closed reason code absent from the parity corpus must appear on section 5.7's explicit,
justified exclusion list — class B1/B2 (naming the constraint, and for B1 the covering E2-A test) or
kernel-internal (naming the E2-A test / 5.7A scenario) — never simply unmentioned.

**Publication immutability and lineage.** No UPDATE to a published version row, ever, including its
`active_flag`. Retraction and correction are append-only. Retracted versions remain stored,
discoverable, returnable in lineage material and dereferenceable — a retraction never removes
anything from the store. A valid later correction may change what the historical resolver
reconstructs for an older business `as_of`, while previously captured decision evidence stays
byte-identical; both answers must remain provable (E2-A 11.8.1).

**Evidence requirements.** All four object/version pairs per qualifying path AND per complete
nonqualifying path; partial/failed evaluations carrying established items, the failed stage and the
deterministic reason with no fabricated pairs; the `established_state` header; deterministic
ordering of all collections — per E2-A section 16, preserved verbatim through persistence.

**Allowed implementation discretion.** Exact table and column names (subject to section 4); index
selection; the JSONB payload column shape; repository query construction (parameterized,
deterministic, PostgreSQL, subject to section 5.2); whether to add an optional database-level
no-UPDATE guarantee (subject to 5.6); which of the two production-composition options in 5.3 to
adopt; test file organisation; the downgrade decision, provided it is recorded.

**Explicitly NOT discretionary: the structural constraint set.** It is exactly the list in section
5.6 — no more, no less. Adding a constraint silently moves fixtures from class A into B1 or B2 and
suppresses a defect class the kernel owns; removing one silently strips a B1/B2 rejection proof and
converts the fixture into an untested class A obligation. A constraint change is a reconciliation
finding against sections 5.6/5.7, raised and reviewed as such, never an implementation preference —
and a NEW constraint must be run through E2-A 9.7's deciding test to determine whether its defects
are B1 or B2, rather than being labelled by resemblance to an existing entry.

**Prohibited reinterpretation.** Anything in "settled invariants" above; the E2-A kernel semantics;
any provider-side re-implementation of E2-A rules; the E2-A/E2-B/E3 boundary; the exclusions in
section 6; the E1 boundary in section 7; the HR boundary in section 8; binding a synthetic provider
in production; inventing a business answer to Q-10.

**Out of scope.** Section 6, in full.

**What must be freshly established when implementation begins.**

```text
- the ACTUAL protected-main baseline commit AFTER E2-A integration (never the definition-time
  commit b6e58994ca4486819312457e89adec22ad720495, and never a predicted future SHA);
- the ACTUAL current Alembic head, verified from backend/alembic/versions/ AND `alembic heads`,
  to be used as this package's migration parent (expected to be 20260831_0030 because E2-A adds no
  migration - but verify, and if it differs, reconfirm the migration slot with the controller);
- the ACTUAL current test counts and E1/E2-A inventories, read from the repository;
- the ACTUAL accepted E2-A port signatures, reason codes and evidence DTOs, read from the
  integrated code rather than from this document;
- the branch/worktree assigned by the controller for the implementation package.
```

**Required independent-review posture.** Bounded, packet-based review per
`BOUNDED_INDEPENDENT_REVIEW_METHOD.md`; risk classification high; core rubric plus the
workflow/lifecycle overlay plus section 13's attack surface and E2-A section 22. The implementation
agent never records acceptance of its own package. Integration follows the ADR-031 protected gate
(pull request, branch current with `main`, `Required validation` reporting success on the exact
commit proposed for merge, project-owner confirmation).

**Completion / handoff condition.** PF-1A-E2-B is complete when: the accepted E2-A model is
persisted without normalization; the read-only PostgreSQL provider implements the E2-A port as
complete lineage material plus RAW identity-only discovery, with no retraction-excluding predicate
and no recorded-time filter; the unchanged kernel is wired to it; the production composition seam
refuses to compose or fails closed deterministically, with synthetic providers proved unreachable
from production; exactly one bounded migration applies cleanly from an empty database and leaves a
single head; the section 9 tests exist and pass, including provider fidelity, CLASS A defect
visibility for all fourteen class A fixtures (including retraction-cannot-hide-a-version), CLASS B1
structural-rejection tests for all twelve B1 fixtures with
their named, boundary-correct, one-to-one E2-A counterparts, CLASS B2 structural-rejection tests
with their
written rationales and their asserted absence of any fabricated E2-A fixture, VALID-SHAPE
conformance for all twelve V-scenarios, NON-STORE conformance
for all forty-six section 5.7A scenarios, a TOTAL and EXCLUSIVE
three-class assignment under section 5.7 together with a disjoint, exhaustive three-group partition
(5.7 A/B1/B2, 5.7 V-01..V-12, 5.7A) of
the whole negative, valid-shape and conformance corpus, determinism under persistence, and full
reference/PostgreSQL parity across all three evidence collections for every class A fixture, every
V-scenario and every parity-YES non-store scenario; every
acceptance criterion
in section 10 is demonstrated with real, recorded evidence; every E1 and E2-A protection is intact;
a fresh independent review returns ACCEPTED with no blocking findings; and the package is integrated
on `main` through the protected gate.

## 16. Completion and handoff boundary

E2-B hands to PF-1A-E3 a durable, read-only published-authority store with immutable versions,
append-only lineage and retraction, forward-compatible `CONFIGURATION_CHANGE` provenance references
that no E2 code creates, and a wired resolution path that E3's governed activation can publish into
without redesigning resolution.

E2-B hands to future consumer packages **a resolution capability whose configuration dependency is
satisfied and whose identity and HR dependencies are not.** Concretely:

```text
DELIVERED       the E2-A kernel, unchanged, wired to a durable PostgreSQL read-side provider of
                published authority configuration; the evidence structure consumers must store with
                their own decisions; a defined production dependency seam.

NOT DELIVERED   an authoritative actor->canonical-person provider; an authoritative canonical HR/
                organisation provider. Until a later authorized package supplies both, the
                production composition refuses to compose or fails closed deterministically
                (section 5.3), and NO consumer route or service may call business-authority
                resolution as a real authorization gate.

THEREFORE       E2-B does NOT hand consumers a production-callable business-authority resolver, and
                no record produced by this package may say that it does.
```

E2-B also hands forward its **verification-class manifest** (section 5.7), **its valid-shape parity
scenario list** (section 5.7, V-01 to V-12) **and its non-store
scenario table** (section 5.7A), all recorded in the
acceptance record: which defect classes this schema rejects structurally, which constraint rejects
each, which of those are class B1 with a named E2-A test and its boundary, which are class B2
with a written rationale for why no provider-neutral counterpart exists, and — separately — which
negative scenarios have no stored subject at all, on which already-defined seam each sits, what
executable obligation and expected result each carries, and which of them are owed parity between
which compositions — plus, separately again, which stored shapes are VALID and therefore parity-owed
without carrying any class label. It also hands forward the retired-ID record (A-03, A-12, A-16,
A-18, A-19, A-20) so
those identifiers are never reused and older citations remain resolvable. Any later package that
changes the constraint set — E3's governed publication most obviously — inherits the obligation to
re-derive that manifest, because adding a constraint moves a fixture out of parity and removing one
strips a rejection proof. A later package that changes E2-A's provider-neutral DTO shape (9.3.2,
9.3.4) inherits a second obligation: to re-run E2-A 9.7's deciding test over every class B2 entry,
because a B2 classification is only ever as valid as the DTO shape it rests on. The semantic rules
themselves remain E2-A's and remain provider-neutral; only the placement of their proof — and, for
class B2, the honest finding that there is no semantic obligation to place — is store-specific.

E2-B hands nothing to production: no route, no real configuration, no assignments, no bootstrap
holder, no authoritative identity or HR provider, no claim on
`READY_FOR_PRODUCTION_AUTHORITY_ACTIVATION`, and no answer to Q-10.
