# PF-1A-E3 Acceptance - Governed Authority Configuration and Self-Escalation Prevention

Backend only. No HTTP route, API schema, frontend, seed or production bootstrap. Q-10 remains
open.

## Automated checks

```text
docker compose up -d --build --force-recreate backend
docker compose exec -T backend alembic upgrade head
docker compose exec -T backend alembic heads     -> 20260906_0032 (head)
docker compose exec -T backend alembic current   -> 20260906_0032 (head)

docker compose exec -T backend pytest tests/test_business_authority_e3_contract.py \
  tests/test_business_authority_e3_lifecycle.py \
  tests/test_business_authority_e3_persistence.py \
  tests/test_business_authority_e3_atomicity.py \
  tests/test_business_authority_e3_security_boundary.py \
  tests/test_business_authority_e3_e2_compatibility.py

docker compose exec -T backend pytest -k "business_authority or authorization"   # predecessors
docker compose exec -T backend pytest                                            # full regression

git diff --check
python scripts/check_tracked_secrets.py
python scripts/validate_contract_fixtures.py
python -m unittest discover -s scripts/tests
```

### Expected result of the E3 suite

The six E3 files must be run **together, in one invocation**, against the real dockerized
PostgreSQL, and the run must end with a terminal summary showing **zero failed and zero errored
tests**. A skipped, deselected or collection-errored test is not a pass: every test here exercises
a governance rule, so a test that did not run is a rule that was not checked.

The R3 correction adds **16 tests** to three of those files - six in `..._contract.py`, four in
`..._lifecycle.py` and six in `..._atomicity.py` - and removes none. Six of the sixteen are pure
(no database); the other ten drive the real governed service. Nothing in the pre-existing suite is
weakened, skipped or relaxed by the correction; the four temporal privilege-increase tests, the
evidence-binding regression and both concurrency regressions all stand unchanged.

The R4 correction adds a further **10 tests** - four in `..._contract.py` (pure), one in
`..._lifecycle.py` and five in `..._atomicity.py` - and removes none. It **strengthens one existing
test** and weakens none: `test_an_identical_payload_over_a_strictly_narrower_interval_is_not_an_increase`
keeps every risk assertion it already made and now additionally proves that the resulting append is
refused before publication. That change is a correction, not a relaxation - the test previously
asserted that the same activation *succeeded*, which was the defect. Every other pre-existing
assertion in all six files stands unchanged, including the temporal privilege-increase set, the
evidence-binding regression, both concurrency regressions and the publication-time monotonicity
regression.

Reviewers should read the terminal summary and the per-file counts, not only the exit code. This
acceptance record states the expectation; the parsed counts and terminal summary belong in the
candidate-bound evidence packet.

Migration cycle is additionally verified in a throwaway database, never the development one:
`upgrade head`, `downgrade 20260904_0031` (empty governed state - succeeds), `upgrade head`,
then a downgrade WITH governed state present, which must fail with the recorded refusal.

## Obligations and where each is proved

| # | Obligation | Where |
| --- | --- | --- |
| 1 | governed CREATE/UPDATE/DEACTIVATE, all four families | lifecycle: all_four_families |
| 2 | no direct mutation of an old published row | persistence: earlier_row_untouched |
| 3 | proposal-time classification authorizes/activates nothing | lifecycle: proposal_time_flags |
| 4 | ordinary unrelated change stays single-person | lifecycle: remains_single_person |
| 5 | same-person authorization refused when required | lifecycle: never_authorize_own |
| 6 | different but ineligible person cannot authorize | lifecycle: ineligible_person |
| 7 | different eligible independent holder can authorize | lifecycle: eligible_holder |
| 8 | protection from the data flag, not the code string | lifecycle: data_flag_not_code_string; security: literal scan |
| 9 | setting AND clearing the flag are both protected | lifecycle: setting_and_clearing |
| 10 | self scope/role/assignment increase requires independence | lifecycle: self_affecting_increase |
| 11 | authorization detects proposal-time drift | lifecycle: proposal_time_drift |
| 12 | activation detects authorization-time drift | lifecycle: became_escalating |
| 13 | authorizer losing authority stops activation | lifecycle: authorizer_loses_authority |
| 14 | incumbency change changing self-affecting status handled | lifecycle: proposal_time_drift, became_escalating |
| 15 | unknown/unavailable authority or HR state fails closed | lifecycle: fails_closed |
| 16 | activation serialized and concurrency-safe | atomicity: governance boundary refusal, per-object lock refusal, stale writer, stale predecessor |
| 17 | activation failure leaves no partial publication | atomicity: failure_before_commit |
| 31 | a refused later attempt cannot lend its context to an earlier authorization | lifecycle: refused_attempt_cannot_lend_context |
| 32 | bound authorization evidence is verified, not merely present | lifecycle: bound_evidence_unverifiable; another_changes_authorization |
| 33 | temporal broadening (earlier start / later end / finite -> unbounded) is a privilege increase | lifecycle: starts_earlier, ends_later, dropping_declared_end |
| 34 | a proven temporal narrowing stays single-person | lifecycle: strictly_narrower, unchanged_interval control |
| 35 | two conflicting activations of DIFFERENT objects cannot both publish | atomicity: two_conflicting_activations (two sessions) |
| 36 | the governance boundary is taken before any state is read | atomicity: boundary_before_any_read |
| 37 | a non-numeric / UUID pre-E3 predecessor is supersedable by UPDATE and DEACTIVATE | atomicity: nonnumeric_predecessor, uuid_predecessor, stale_opaque_predecessor |
| 38 | no E3 module parses a version identifier as a number | contract: no_numeric_version_parsing |
| 40 | an allocated version is strictly lexicographically greater than every existing one, for arbitrary opaque predecessors | contract: allocation invariant over 12 adversarial predecessors |
| 41 | successive publications are strictly increasing, and `published_at` is non-decreasing in that order | atomicity: successive_publications_increasing; lifecycle: all_four_families; persistence: deactivation |
| 42 | an unchanged E2 kernel reads an E3 deactivation as DENY + RESOLVED, not FAIL_CLOSED | e2_compatibility: deactivation_removes_the_grant |
| 43 | one governed decision publishes at most one version (replay control is the lifecycle) | atomicity: already_activated_cannot_activate_again |
| 44 | the authority graph is derived through the unchanged E2 lineage/effectiveness kernel, not re-ranked locally | contract: authority_graph_derived_by_unchanged_kernel (imports are identity-checked; the append-order shortcut and its field are asserted absent) |
| 45 | a future-effective INACTIVE successor does not erase a currently effective self-holder | lifecycle: future_effective_inactive_successor (proposal, authorization AND activation) |
| 46 | a future-effective REASSIGNED successor does not erase a currently effective self-holder | lifecycle: future_effective_reassignment |
| 47 | a future-effective rule successor does not erase a currently effective protected linkage | lifecycle: future_effective_rule_successor |
| 48 | an ALREADY-effective inactive successor DOES release the former holder (the control) | lifecycle: already_effective_inactive_successor_releases |
| 49 | effective version and authoritative predecessor are separate answers | contract: derive_effective_state_separates; keeps_a_lapsed_predecessor |
| 50 | an unestablishable lineage fails every governed action closed, never "has nothing" | contract: fails_closed_on_unestablishable_lineage; atomicity: contradictory_lineage_fails_closed |
| 51 | a retracted version is never the authoritative predecessor, even as the lexical maximum | contract: retracted_never_predecessor; atomicity: predecessor_is_not_the_retracted_maximum |
| 52 | an expected predecessor retracted between authorization and activation is refused | atomicity: expected_predecessor_retracted_after_authorization |
| 53 | correction/retraction histories with non-numeric identities resolve correctly | atomicity: corrected_nonnumeric_lineage |
| 54 | allocation stays greater than every historical version even when the maximum is retracted | atomicity: predecessor_is_not_the_retracted_maximum (final assertion) |
| 55 | activation refuses when the allocation anchor's `published_at` is after the activation instant | atomicity: anchor_published_after_activation_instant; publication_time_floor_follows_the_retracted_anchor |
| 56 | publication-time monotonicity permits equality and fails closed on anything incomparable | contract: publication_time_monotonicity |
| 57 | an append that would leave the object's lineage defective under UNCHANGED E2 semantics is refused before publication, with nothing written and nothing ACTIVE | lifecycle: strictly_narrower (refusal half); atomicity: append_would_overlap_a_still_declared_predecessor_end |
| 58 | privilege-risk classification and publication validity stay SEPARATE answers - a narrowing is still non-increasing, and the refusal does not come from reclassifying it | lifecycle: strictly_narrower (risk half, at proposal AND at activation); contract: append_starting_before_a_still_declared_predecessor_end |
| 59 | prospective validation delegates to the unchanged kernel and is not hard-coded to the overlap shape (duplicate start, provenance ordering, ill-formed material) | contract: catches_defect_classes_other_than_the_overlap_shape; delegates_rather_than_re_deriving; atomicity: not_hard_coded_to_the_overlap_shape |
| 60 | the check blocks nothing ordinary: valid successions, adjacency and genuine narrowings still publish | contract: publishable_append_reports_no_prospective_defect; lifecycle: narrowing_that_leaves_a_valid_lineage_publishes; atomicity: adjacent_successor_publishes |
| 61 | CREATE, UPDATE and DEACTIVATE all get the same publication-validity rule | atomicity: deactivate_gets_the_same_publication_validity_rule; create_onto_fully_retracted_material; lifecycle: all_four_families (unchanged, still publishes) |
| 62 | the row that is prospectively validated is the row that is written | service constructs one `PublishedRow` and passes that object to both; repository writer takes the whole row and refuses a correction assertion or a non-CONFIGURATION_CHANGE provenance structurally; lifecycle: narrowing_that_leaves_a_valid_lineage_publishes asserts the stored interval/provenance/active semantics |
| 39 | downgrade locks every governed-writable table before counting | persistence: downgrade_lock_order; concurrent_writer_check_to_drop_window |
| 18 | publication carries CONFIGURATION_CHANGE provenance | persistence: provenance |
| 19 | unchanged E2 provider/kernel consumes an E3 publication | e2_compatibility (all) |
| 20 | historical versions stay dereferenceable | persistence: historical_dereference |
| 21 | DEACTIVATE emits a new inactive version | persistence: deactivation; lifecycle: all_four_families |
| 22 | REJECTED lifecycle records remain auditable | lifecycle: rejected_change_durable |
| 23 | duplicate/conflicting active assignments rejected | lifecycle: duplicate_active_assignment |
| 24 | production composition refuses while providers absent | security: composition_refuses; service dependency guard |
| 25 | no production bootstrap seed/default/fixture path | security: migration_seeds_nothing; synthetic context is test-only |
| 26 | downgrade harmless when empty, refuses once governed | persistence: downgrade_guard; isolated migration cycle |
| 27 | E1 compatibility facts unchanged | security: e1_permission_facts |
| 28 | existing E2-A/E2-B suites remain green | predecessor run |
| 29 | full backend regression green | full run |
| 30 | diff/whitespace, migration head, tracked-secret checks | script-level |

## Manual/judgement notes

- The synthetic bootstrap in `backend/tests/fixtures/pf_1a_e3_reference_context.py` writes the
  published store directly under `BOOTSTRAP_PROVENANCE` with an id that names itself as a test
  fixture. This is unavoidable and deliberate: the governed lifecycle cannot bootstrap itself,
  because proposing requires already holding a protected meta-authority. It is not a production
  bootstrap and does not answer Q-10.
- The concurrency proofs are deterministic rather than threaded, but they are genuinely
  multi-session: a second `SessionLocal()` holds the real advisory lock the service takes, and
  activation refuses immediately rather than blocking inside an open transaction. This exercises
  the production lock without a timing-dependent test.
  - `test_two_conflicting_activations_of_different_objects_cannot_both_publish` is the one that
    matters for the governance-wide boundary. It first proves directly that the two stable
    objects take *independent* per-object lock keys - so per-object locking alone would have let
    both proceed - then shows the governance-wide boundary refusing the second activation, and
    finally that once serialized the second sees the first's publication and refuses on the
    duplicate rule. Only one of the two conflicting objects ever publishes.
- The destructive-downgrade race proof uses a bounded `lock_timeout` rather than threads. The
  guard is *required* to wait for an in-flight governed writer, so the observable deterministic
  evidence that it waits is that it aborts on the timeout instead of returning a comfortable
  zero-state verdict. The same test first shows the uncommitted writer's row being invisible to
  the guard's session - which is precisely what a count-first guard would have read as "empty".
- Version identities are never asserted by spelling. Tests read a predecessor back with
  `current_version(...)` or compare against `allocate_object_version(maximum, change_id)`,
  because an expected predecessor is an opaque value a proposer was *told*, not a number anyone
  can compute. `version_rows(...)` orders by publication order (`id`), which is precisely what
  lets the ordering test assert that publication order and lexicographic order agree rather than
  assuming it.
- **Opacity and lexicographic ordering are both required, and the second was initially missed.**
  A focused validation run caught it: an allocator that produced unique but unordered identities
  left `test_an_e3_deactivation_removes_the_grant_through_the_unchanged_kernel` returning
  `DENY + FAIL_CLOSED` instead of `DENY + RESOLVED`, because `lineage.py` reads `published_at` as
  non-decreasing in `object_version` order and a successor that sorted before its predecessor is
  contradictory provenance. That compatibility expectation was **not** relaxed; the allocator was
  corrected to anchor on the lexicographic maximum and append, which satisfies both invariants at
  once. The contract test exercises the invariant against twelve adversarial predecessors -
  including `~~~~~~~~`, `zzzz...`, a UUID, a leading-space string and a non-ASCII string - because
  a scheme that only works for predecessors that look like numbers is the defect being excluded.
- **The R3 correction changes what "current" means, in three places, and each has a control.**
  Obligations 44-56 above were added by that correction. Two of them exist specifically to prove
  the correction did not over-rotate: `test_an_already_effective_inactive_successor_does_release_the_former_holder`
  shows a genuinely lapsed holder still releasing (ADR-033 warns against making every edit
  two-person), and `test_publication_time_monotonicity_permits_equality_and_fails_closed_otherwise`
  shows equality passing, because PF-1A-E2-A 11.8.3 requires non-decreasing rather than strictly
  increasing recorded times.
- **The effectiveness regressions are constructed so the old shortcut would demonstrably pass
  them.** Each seeds a currently effective version plus a later-published successor that is
  future-dated, inactive or reassigned - the exact shape a publication-order view reads as "the
  current one". They assert the risk *derivation strings*, not merely the boolean, so a test that
  happened to pass for an unrelated reason would still show which rule fired.
- **The predecessor/anchor regressions turn on a retracted lexical maximum**, which is the one
  configuration in which the two values provably differ. Note that PF-1A-E3 writes no retraction
  of its own, so those tests seed the assertion through the synthetic bootstrap - which is exactly
  the situation the correction is about: a retraction can only ever arrive from another authorized
  mechanism, so the governed writer must resolve its predecessor through the kernel rather than by
  taking the greatest identity it can see.
- **The publication-time check is proved with a bootstrapped future `published_at`**, not by
  manipulating the process clock. Fixing the *stored* provenance rather than the *reader's* clock
  keeps the test deterministic and models the real cause (a rollback, a restored backup, a
  mis-set container clock) without making the test depend on time passing.
- **The R4 correction is about the difference between two questions that look like one.**
  Obligations 57-62 above were added by it. `test_an_identical_payload_over_a_strictly_narrower_interval_is_not_an_increase`
  is the test to read first: its risk assertions are unchanged and still say the narrowing is *not*
  a privilege increase, and it now also proves that the append is refused - because
  `PUBLICATION_LINEAGE_INVALID` is a publication-validity answer, not a risk verdict. Reviewers
  should check specifically that the refusal was **not** obtained by reclassifying narrowings as
  increases; the test asserts `privilege_increasing is False` on the activation-time evaluation for
  exactly that reason.
- **The R4 controls are as important as the R4 refusals**, for the same reason ADR-033 gives: a
  check that refused every append onto a predecessor with a declared end would stop ordinary
  supersession dead. Three tests exist to prove it does not - an adjacent successor (11.4's explicit
  adjacency branch) publishes, a genuine narrowing inside an *unbounded* predecessor publishes
  single-person, and a `DEACTIVATE` that supersedes from the predecessor's declared end publishes.
- **The "not hard-coded to the overlap shape" evidence is deliberately behavioural, not textual.**
  A comment or a name proves nothing about which defect classes a check catches, so the proof is
  three structurally unrelated unchanged-E2 defects - a duplicate start (a lineage-level 11.6
  pre-check with no attributed version), `published_at` decreasing across the version order
  (11.8.3), and material rejected at the 9.3.3 DTO/port boundary - each refusing through the same
  path. A local interval-overlap rule would pass all three. One call-graph assertion supplements
  this by checking that the function actually calls `check_material_well_formed` and
  `evaluate_lineage`; it is asserted over the AST rather than over raw text, because the function's
  own docstring names both and a substring scan would pass on prose alone.
- `test_no_e1_login_role_code_reaches_the_e3_modules` uses a quoted-literal scan rather than the
  bare `"ADMIN" not in source` form the E2 suite uses for its own modules, because these modules
  legitimately contain the English word "administrator" in a refusal-reason constant. The
  substantive guarantee - no E1 role-code literal, no E1 contract import, no permission
  dependency - is asserted directly.

## Deferred

Route/schema/admin UI; production actor-person and HR/organisation providers; correction and
retraction of published versions; Q-10.

Also deferred, and recorded explicitly rather than left implicit by the R4 correction: **an
`UPDATE` that starts before a predecessor's finite declared end is now refused, and PF-1A-E3 offers
no action that would make it expressible.** Doing so needs either a retract-then-republish
supersession model or an `UPDATE` that explicitly closes its predecessor, both of which are design
decisions with their own authorization questions. Refusing the defective append is what this
package owes; expressing that change is a separate package.
