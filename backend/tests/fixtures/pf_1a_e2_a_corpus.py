"""The PF-1A-E2-A verification manifest, as machine-checkable data.

PF-1A-E2-A sections 9.7, 9.7.0 and 18; PF-1A-E2-B sections 5.7 and 5.7A.

The manifests in those documents are a COVERAGE CONTRACT, not illustrative
examples. This module restates them as data so the coverage test can check the
implementation against them mechanically rather than by reading prose - which
is exactly the check that would have caught F-10.1, where one manifest ID
covered two malformed shapes and only one of them had an executing test.

THREE PAIRWISE-DISJOINT GROUPS (9.7.0), and the first question about any item
is which group it is in:

    MALFORMED AUTHORITY-STORE FIXTURES   subject: a MALFORMED or CONTRADICTORY
        published authority-store state one this contract requires the kernel
        to REJECT AS INVALID. Classified A / B1 / B2.
    VALID-SHAPE PARITY SCENARIOS         subject: a VALID published
        authority-store state. NO class label, not a negative fixture, still
        fully parity-owed.
    NON-STORE SCENARIOS                  subject: a provider, a request input,
        resolver orchestration or the resolution clock, deterministic defect
        ordering, evidence, or a pure-kernel invariant. NO class label.

A FAIL-CLOSED OUTCOME NEVER BY ITSELF PUTS AN ITEM IN THE FIRST GROUP, and
READING valid stored rows never does either. Store PARTICIPATION and store
SUBJECTHOOD are two INDEPENDENT dimensions, recorded in two separate fields.

RETIRED IDS ARE NEVER REUSED. A-03, A-12, A-16, A-18, A-19 and A-20 are
retired, each recorded below with the scenario that now carries its
obligation, so a later reader tracing an old citation lands on the replacement
rather than on silence.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, TypeVar

# ---------------------------------------------------------------------------
# Verification classes and boundaries
# ---------------------------------------------------------------------------

CLASS_A = "A"
CLASS_B1 = "B1"
CLASS_B2 = "B2"

# The BOUNDARY a class B1 fixture is proved at. Naming it is mandatory, and a
# test that exercises a different boundary than the one named does NOT
# discharge the obligation (9.7 class B1, requirement 2).
BOUNDARY_PURE_KERNEL = "PURE_KERNEL"
BOUNDARY_DTO_PORT = "DTO_PORT_WELL_FORMEDNESS"
BOUNDARY_PROVIDER_PORT = "PROVIDER_PORT"
BOUNDARY_NONE = "NONE"


@dataclass(frozen=True)
class AuthorityStoreFixture:
    """One MALFORMED authority-store negative fixture.

    Answers all seven questions a fresh chat must be able to answer from the
    repository alone (9.7 classification rule). `pg_may_store` is never "N/A":
    an item that would need one is, by construction, not an authority-store
    fixture at all.
    """

    fixture_id: str
    shape: str
    verification_class: str
    pg_may_store: bool
    e2a_boundary: str
    e2a_fixture_name: str | None
    pg_parity_required: bool
    expected_reason_code: str | None
    rationale: str = ""


@dataclass(frozen=True)
class ValidShapeScenario:
    """One VALID stored shape. No class label; full parity still owed."""

    scenario_id: str
    shape: str
    pg_parity_required: bool = True


@dataclass(frozen=True)
class NonStoreScenario:
    """One non-store resolver/provider conformance scenario.

    `pg_data_participates` and `subject_is_store_state` are INDEPENDENT
    dimensions: neither may be inferred from the other. `subject_is_store_state`
    is NO on every row by construction - a YES would mean the item belongs in
    the authority-store manifest instead.
    """

    scenario_id: str
    seam: str
    condition: str
    pg_data_participates: bool
    subject_is_store_state: bool
    parity_required: bool
    expected: str


# The CLOSED list of seams a non-store scenario may sit on. No new provider
# surface may be invented in order to classify a scenario; a scenario that does
# not sit on one of these is a contract gap to raise, not a licence to add a
# seam (9.7.0).
SEAM_ACTOR_PERSON = "actor->person mapping/provider validity (9.1)"
SEAM_HR_REFERENCE = "HR provider availability/freshness/ambiguity (9.2)"
SEAM_AUTHORITY_PORT = "authority configuration port read/transport and fact-fidelity (9.3, 9.5)"
SEAM_PROVIDER_REACHABILITY = "provider reachability and composition (9.6)"
SEAM_REQUEST_INPUT = "request/scope/evaluator input (12, 13)"
SEAM_RESOLVER_ORCHESTRATION = "resolver orchestration, the resolution clock and the two entry points (10, 11.1, 11.5, 11.8)"
SEAM_AGGREGATION = "aggregation, relevance and the total defect order (15)"
SEAM_EVIDENCE = "the evidence contract (16)"
SEAM_KERNEL_INVARIANT = "pure-kernel invariants (11, 15.5)"

CLOSED_SEAMS = (
    SEAM_ACTOR_PERSON,
    SEAM_HR_REFERENCE,
    SEAM_AUTHORITY_PORT,
    SEAM_PROVIDER_REACHABILITY,
    SEAM_REQUEST_INPUT,
    SEAM_RESOLVER_ORCHESTRATION,
    SEAM_AGGREGATION,
    SEAM_EVIDENCE,
    SEAM_KERNEL_INVARIANT,
)

# ---------------------------------------------------------------------------
# Retired IDs, with their replacements. Never reused.
# ---------------------------------------------------------------------------

RETIRED_FIXTURE_IDS = {
    "A-03": "NS-K-01 (proved unreachable on every provider by the 11.4a theorem)",
    "A-12": "NS-RS-01 (its rows are VALID; the subject is the resolver, not the store)",
    "A-16": "NS-PT-01 (the subject is the port's read/transport behaviour)",
    "A-18": "NS-AP-01..03 and NS-HR-01..12 (one scenario per fail-closed reason code)",
    "A-19": "NS-RQ-02 (the subject is request-side input)",
    "A-20": "NS-RQ-01 (likewise request-side input)",
}

# ---------------------------------------------------------------------------
# Group 1 - MALFORMED AUTHORITY-STORE FIXTURES (A / B1 / B2)
# ---------------------------------------------------------------------------

_A = CLASS_A
_K = BOUNDARY_PURE_KERNEL

AUTHORITY_STORE_FIXTURES: dict[str, AuthorityStoreFixture] = {
    fixture.fixture_id: fixture
    for fixture in (
        # -- class A: persistable semantic contradictions, full parity owed --
        AuthorityStoreFixture(
            "A-01", "explicit cross-version overlap", _A, True, _K,
            "LINEAGE AND CLOSURE, EXPLICIT END AFTER SUCCESSOR", True,
            "AUTHORITY_LINEAGE_CONTRADICTORY",
        ),
        AuthorityStoreFixture(
            "A-02", "duplicate temporal start", _A, True, _K,
            "LINEAGE AND CLOSURE, DUPLICATE START", True, "AUTHORITY_LINEAGE_CONTRADICTORY",
        ),
        AuthorityStoreFixture(
            "A-04", "dangling retraction (missing target version)", _A, True, _K,
            "RAW DISCOVERY AND RETRACTION", True, "AUTHORITY_LINEAGE_CONTRADICTORY",
        ),
        AuthorityStoreFixture(
            "A-05", "duplicated retraction of one version", _A, True, _K,
            "RAW DISCOVERY AND RETRACTION", True, "AUTHORITY_LINEAGE_CONTRADICTORY",
        ),
        AuthorityStoreFixture(
            "A-06", "correction target exists but is not retracted", _A, True, _K,
            "LINEAGE AND CLOSURE", True, "AUTHORITY_LINEAGE_CONTRADICTORY",
        ),
        AuthorityStoreFixture(
            "A-07", "correction target does not exist", _A, True, _K,
            "LINEAGE AND CLOSURE", True, "AUTHORITY_LINEAGE_CONTRADICTORY",
        ),
        AuthorityStoreFixture(
            "A-08", "provenance: retracted_at before target published_at", _A, True, _K,
            "RECORDED TIME, PROVENANCE VALIDITY", True, "PUBLICATION_PROVENANCE_INVALID",
        ),
        AuthorityStoreFixture(
            "A-09", "provenance: correction published before target retracted", _A, True, _K,
            "RECORDED TIME, PROVENANCE VALIDITY", True, "PUBLICATION_PROVENANCE_INVALID",
        ),
        AuthorityStoreFixture(
            "A-10", "provenance: published_at decreasing across versions", _A, True, _K,
            "RECORDED TIME, PROVENANCE VALIDITY", True, "PUBLICATION_PROVENANCE_INVALID",
        ),
        AuthorityStoreFixture(
            "A-11", "reference to a stable identity carrying no material", _A, True,
            BOUNDARY_PROVIDER_PORT, "DIRECT COVERAGE, dangling-reference case", True,
            "AUTHORITY_REFERENCE_DANGLING",
        ),
        AuthorityStoreFixture(
            "A-13", "unknown parameter_evaluator_type", _A, True, _K, "EVALUATORS", True,
            "EVALUATOR_UNKNOWN",
        ),
        AuthorityStoreFixture(
            "A-14", "malformed / type-invalid parameter_payload", _A, True, _K, "EVALUATORS", True,
            "EVALUATOR_PAYLOAD_INVALID",
        ),
        AuthorityStoreFixture(
            "A-15", "unsupported scope_type value", _A, True, _K, "SCOPE AND COMPOSITION", True,
            "SCOPE_SEMANTICS_UNSUPPORTED",
        ),
        AuthorityStoreFixture(
            "A-17", "malformed retraction on the ONLY code/reference-bearing version", _A, True, _K,
            "RAW DISCOVERY, MALFORMED RETRACTION CANNOT HIDE A VERSION", True,
            "AUTHORITY_LINEAGE_CONTRADICTORY",
        ),
        # -- class B1: structurally rejected by a store, provable HERE -------
        AuthorityStoreFixture(
            "B1-01", "duplicate (object_id, object_version)", CLASS_B1, False, _K,
            "DUPLICATE-OBJECT-VERSION", False, "AUTHORITY_LINEAGE_CONTRADICTORY",
        ),
        AuthorityStoreFixture(
            "B1-02", "assignment with BOTH targets", CLASS_B1, False, _K,
            "ASSIGNMENT-TARGET-BOTH", False, "ASSIGNMENT_TARGET_INVALID",
        ),
        AuthorityStoreFixture(
            "B1-03", "assignment with NEITHER target", CLASS_B1, False, _K,
            "ASSIGNMENT-TARGET-NEITHER", False, "ASSIGNMENT_TARGET_INVALID",
        ),
        AuthorityStoreFixture(
            "B1-04", "declared_effective_to < effective_from", CLASS_B1, False, _K,
            "INTERVAL-END-BEFORE-START", False, "AUTHORITY_LINEAGE_CONTRADICTORY",
        ),
        AuthorityStoreFixture(
            "B1-05", "declared_effective_to == effective_from", CLASS_B1, False, _K,
            "INTERVAL-END-EQUALS-START", False, "AUTHORITY_LINEAGE_CONTRADICTORY",
        ),
        AuthorityStoreFixture(
            "B1-06", "NULL effective_from", CLASS_B1, False, BOUNDARY_DTO_PORT,
            "VERSION-ABSENT-EFFECTIVE-FROM", False, "AUTHORITY_CONFIGURATION_UNAVAILABLE",
        ),
        AuthorityStoreFixture(
            "B1-07", "NULL active_flag", CLASS_B1, False, BOUNDARY_DTO_PORT,
            "VERSION-ABSENT-ACTIVE-FLAG", False, "AUTHORITY_CONFIGURATION_UNAVAILABLE",
        ),
        AuthorityStoreFixture(
            "B1-08a", "NULL published_at on a version", CLASS_B1, False, _K,
            "PROVENANCE-ABSENT-PUBLISHED-AT", False, "PUBLICATION_PROVENANCE_INVALID",
        ),
        AuthorityStoreFixture(
            "B1-08b", "NULL retracted_at on a retraction", CLASS_B1, False, _K,
            "PROVENANCE-ABSENT-RETRACTED-AT", False, "PUBLICATION_PROVENANCE_INVALID",
        ),
        AuthorityStoreFixture(
            "B1-09a", "ABSENT publication_reference_type", CLASS_B1, False, _K,
            "PROVENANCE-ABSENT-TYPE", False, "PUBLICATION_PROVENANCE_INVALID",
        ),
        AuthorityStoreFixture(
            "B1-09b", "absent publication_reference_id", CLASS_B1, False, _K,
            "PROVENANCE-ABSENT-REFERENCE-ID", False, "PUBLICATION_PROVENANCE_INVALID",
        ),
        AuthorityStoreFixture(
            "B1-10", "publication_reference_type outside the two values", CLASS_B1, False, _K,
            "PROVENANCE-UNKNOWN-TYPE", False, "PUBLICATION_PROVENANCE_INVALID",
        ),
        # -- class B2: persistence-only, NO provider-neutral counterpart -----
        AuthorityStoreFixture(
            "B2-01", "version row with no stable-identity parent row", CLASS_B2, False,
            BOUNDARY_NONE, None, False, None,
            rationale=(
                "object_id lives on the LineageMaterial CONTAINER (9.3.2) and versions[] is "
                "grouped UNDER it, so a version cannot be provider-neutrally orphaned from its "
                "object: the contract has no field in which that state could be expressed. The "
                "foreign key protects the store's own two-table parent/child representation, "
                "which this contract deliberately does not model."
            ),
        ),
        AuthorityStoreFixture(
            "B2-02", "retraction row with no object stable-identity parent row", CLASS_B2, False,
            BOUNDARY_NONE, None, False, None,
            rationale=(
                "Identical to B2-01: retraction_assertions[] is likewise grouped under the "
                "LineageMaterial container, so a retraction cannot be provider-neutrally "
                "orphaned from its object."
            ),
        ),
        AuthorityStoreFixture(
            "B2-03", "rule/assignment referencing a non-existent stable identity ROW", CLASS_B2,
            False, BOUNDARY_NONE, None, False, None,
            rationale=(
                "get_lineage for an identity the provider holds nothing for returns COMPLETE "
                "material with an EMPTY versions[] (9.3.2). A reference to a stable identity ROW "
                "that does not exist therefore DECODES, at the provider-neutral boundary, to "
                "exactly the class A dangling-reference state of fixture A-11, which is already "
                "owed full parity and already carries a direct test. Its counterpart COLLAPSES "
                "ONTO an existing fixture rather than going untested, so there is no DISTINCT "
                "malformed state left to place."
            ),
        ),
    )
}

# ---------------------------------------------------------------------------
# Group 2 - VALID-SHAPE PARITY SCENARIOS (no class label, full parity owed)
# ---------------------------------------------------------------------------

VALID_SHAPE_SCENARIOS: dict[str, ValidShapeScenario] = {
    scenario.scenario_id: scenario
    for scenario in (
        ValidShapeScenario("V-01", "null-end successor closure"),
        ValidShapeScenario("V-02", "explicit adjacency"),
        ValidShapeScenario("V-03", "explicit end before successor -> VALID GAP, per family"),
        ValidShapeScenario("V-04", "later reactivation after that gap"),
        ValidShapeScenario("V-05", "inactive-but-effective versions in all four families"),
        ValidShapeScenario("V-06", "an INACTIVE version still closes its predecessor"),
        ValidShapeScenario("V-07", "exact half-open boundary instants for every shape"),
        ValidShapeScenario("V-08", "raw discovery over VALID retraction facts"),
        ValidShapeScenario("V-09", "recorded-time versus business-effective reconstruction"),
        ValidShapeScenario("V-10", "valid scope operands, each alone"),
        ValidShapeScenario("V-11", "scope COMPOSITION over valid operands"),
        ValidShapeScenario("V-12", "evaluator satisfaction and LEGITIMATE non-satisfaction"),
    )
}

# ---------------------------------------------------------------------------
# Group 3 - NON-STORE RESOLVER / PROVIDER CONFORMANCE SCENARIOS (46)
# ---------------------------------------------------------------------------


def _ns(
    scenario_id: str,
    seam: str,
    condition: str,
    pg_data: bool,
    parity: bool,
    expected: str,
) -> NonStoreScenario:
    # `subject_is_store_state` is NO on every row by construction - it is the
    # 5.7A entry criterion - and is written out per scenario rather than
    # inferred from `pg_data_participates`, because conflating the two is the
    # imprecision F-10.3b corrected.
    return NonStoreScenario(
        scenario_id=scenario_id,
        seam=seam,
        condition=condition,
        pg_data_participates=pg_data,
        subject_is_store_state=False,
        parity_required=parity,
        expected=expected,
    )


NON_STORE_SCENARIOS: dict[str, NonStoreScenario] = {
    scenario.scenario_id: scenario
    for scenario in (
        # -- actor -> canonical person seam ---------------------------------
        _ns("NS-AP-01", SEAM_ACTOR_PERSON, "no mapping", False, True, "ACTOR_PERSON_MAPPING_MISSING"),
        _ns("NS-AP-02", SEAM_ACTOR_PERSON, "more than one mapping", False, True, "ACTOR_PERSON_MAPPING_AMBIGUOUS"),
        _ns("NS-AP-03", SEAM_ACTOR_PERSON, "port unbound", False, True, "ACTOR_PERSON_PROVIDER_NOT_CONFIGURED"),
        _ns("NS-AP-04", SEAM_ACTOR_PERSON, "client-supplied identity hint", False, False, "the supplied value influences nothing"),
        # -- canonical HR reference seam ------------------------------------
        _ns("NS-HR-01", SEAM_HR_REFERENCE, "HR port unbound", False, True, "HR_REFERENCE_PROVIDER_NOT_CONFIGURED"),
        _ns("NS-HR-02", SEAM_HR_REFERENCE, "HR port unavailable", False, True, "HR_REFERENCE_UNAVAILABLE"),
        _ns("NS-HR-03", SEAM_HR_REFERENCE, "snapshot older than a SUPPLIED threshold", False, True, "HR_REFERENCE_STALE"),
        _ns("NS-HR-04", SEAM_HR_REFERENCE, "employment state MISSING", False, True, "EMPLOYMENT_STATE_MISSING"),
        _ns("NS-HR-05", SEAM_HR_REFERENCE, "employment state AMBIGUOUS", False, True, "EMPLOYMENT_STATE_AMBIGUOUS"),
        _ns("NS-HR-06", SEAM_HR_REFERENCE, "position state MISSING", True, True, "POSITION_STATE_MISSING"),
        _ns("NS-HR-07", SEAM_HR_REFERENCE, "position state AMBIGUOUS", True, True, "POSITION_STATE_AMBIGUOUS"),
        _ns("NS-HR-08", SEAM_HR_REFERENCE, "no incumbent at as_of", True, True, "INCUMBENCY_MISSING"),
        _ns("NS-HR-09", SEAM_HR_REFERENCE, "more than one incumbent at as_of", True, True, "INCUMBENCY_AMBIGUOUS"),
        _ns("NS-HR-10", SEAM_HR_REFERENCE, "org unit state MISSING", True, True, "ORG_UNIT_STATE_MISSING"),
        _ns("NS-HR-11", SEAM_HR_REFERENCE, "org unit state AMBIGUOUS", True, True, "ORG_UNIT_STATE_AMBIGUOUS"),
        _ns("NS-HR-12", SEAM_HR_REFERENCE, "ancestry cycle / depth exhaustion", True, True, "ORG_HIERARCHY_UNRESOLVABLE"),
        # -- request / scope / evaluator input seam --------------------------
        _ns("NS-RQ-01", SEAM_REQUEST_INPUT, "required canonical scope absent from the request", True, True, "SCOPE_CONTEXT_MISSING"),
        _ns("NS-RQ-02", SEAM_REQUEST_INPUT, "required fact absent / wrong type / unit-currency-basis incompatible", True, True, "EVALUATOR_FACTS_INVALID"),
        # -- authority configuration PORT and provider-fidelity seam ---------
        _ns("NS-PT-01", SEAM_AUTHORITY_PORT, "raised error / UNAVAILABLE / truncated read", True, True, "AUTHORITY_CONFIGURATION_UNAVAILABLE"),
        _ns("NS-PR-01", SEAM_PROVIDER_REACHABILITY, "synthetic providers production-unreachable", False, False, "unreachable from every production path"),
        _ns("NS-PR-02", SEAM_PROVIDER_REACHABILITY, "production composition without authoritative providers", False, False, "refuses to compose"),
        _ns("NS-PR-03", SEAM_AUTHORITY_PORT, "a provider that supplies judgements instead of facts", True, False, "the conformance test rejects it"),
        # -- resolver orchestration, clock and entry-point seam --------------
        _ns("NS-RS-01", SEAM_RESOLVER_ORCHESTRATION, "requested authority_code has no grant-eligible version at as_of", True, True, "AUTHORITY_CODE_NOT_CONFIGURED"),
        _ns("NS-RS-02", SEAM_RESOLVER_ORCHESTRATION, "one live resolution, one server-captured instant", True, True, "one instant governs every stage"),
        _ns("NS-RS-03", SEAM_RESOLVER_ORCHESTRATION, "the two entry points' parameter surfaces", False, False, "no as_of and no recorded-time bound on the current path"),
        _ns("NS-RS-04", SEAM_RESOLVER_ORCHESTRATION, "only the recorded timestamps are shifted", True, True, "nothing changes"),
        # -- aggregation, relevance and result-level reason seam -------------
        _ns("NS-AG-01", SEAM_AGGREGATION, "two valid qualifying paths", True, True, "ALLOW, both retained"),
        _ns("NS-AG-02", SEAM_AGGREGATION, "valid plus normal-nonqualifying", True, True, "ALLOW, nonqualifying retained in full"),
        _ns("NS-AG-03", SEAM_AGGREGATION, "valid plus RELEVANT corrupt", True, True, "DENY + FAIL_CLOSED"),
        _ns("NS-AG-04", SEAM_AGGREGATION, "IRRELEVANT corrupt, plus its companion", True, True, "unaffected; companion fails closed"),
        _ns("NS-AG-05", SEAM_AGGREGATION, "no path qualifies", True, True, "the correct result-level reason"),
        # -- deterministic defect ordering seam ------------------------------
        _ns("NS-DO-01", SEAM_AGGREGATION, "two different defects at the same stage", True, True, "the 15.5 total order selects"),
        _ns("NS-DO-02", SEAM_AGGREGATION, "one subject carrying two reason codes", True, True, "reason_code_rank decides"),
        _ns("NS-DO-03", SEAM_AGGREGATION, "defects across families at one stage", True, True, "object_family_rank orders"),
        _ns("NS-DO-04", SEAM_AGGREGATION, "shuffled order, reversed traversal, repeated runs", True, True, "byte-identical"),
        _ns("NS-DO-05", SEAM_AGGREGATION, "head of the ordered partial collection", True, True, "carries the result_level_reason"),
        _ns("NS-DO-06", SEAM_AGGREGATION, "the declared rank tables themselves", False, False, "total and collision-free"),
        # -- evidence contract seam ------------------------------------------
        _ns("NS-EV-01", SEAM_EVIDENCE, "any ALLOW result", True, True, "all four pairs and every evaluation"),
        _ns("NS-EV-02", SEAM_EVIDENCE, "complete nonqualifying paths, scope and parameter denials", True, True, "four pairs plus the decisive reason"),
        _ns("NS-EV-03", SEAM_EVIDENCE, "any partial evaluation", True, True, "established items, exact stage, NO fabricated pairs"),
        _ns("NS-EV-04", SEAM_EVIDENCE, "DENY + RESOLVED with zero complete paths", True, True, "still explains itself"),
        _ns("NS-EV-05", SEAM_EVIDENCE, "collection membership and ordering under shuffled output", True, True, "exactly one collection each, deterministic"),
        _ns("NS-EV-06", SEAM_EVIDENCE, "serialized evidence of every scenario", True, True, "no secret, credential or provider identifier"),
        _ns("NS-EV-07", SEAM_EVIDENCE, "later versions, a retraction and a correction", True, True, "byte-identical dereference; 11.8.1 asymmetry"),
        # -- pure-kernel invariant seam --------------------------------------
        _ns("NS-K-01", SEAM_KERNEL_INVARIANT, "the single-effective-version theorem", False, False, "three executable parts"),
        _ns("NS-K-02", SEAM_KERNEL_INVARIANT, "a violated non-multiplicity kernel invariant", False, False, "INTERNAL_CONTRACT_VIOLATION"),
    )
}


# ---------------------------------------------------------------------------
# The coverage decorator
# ---------------------------------------------------------------------------

_F = TypeVar("_F", bound=Callable[..., Any])

COVERS_ATTRIBUTE = "pf_1a_e2_a_covers"
BOUNDARY_ATTRIBUTE = "pf_1a_e2_a_boundary"


def covers(*ids: str, boundary: str | None = None) -> Callable[[_F], _F]:
    """Record which manifest IDs a test discharges.

    The coverage test walks every `test_business_authority_*` module and reads
    these attributes, so the mapping between the manifest and the tests is
    checked mechanically. Marking is on the REAL test function pytest collects
    and runs, so a marked test that is skipped or xfailed is detectable.

    `boundary` is mandatory for a class B1 fixture and must equal the boundary
    the manifest names for it: a DTO-boundary fixture asserted through a kernel
    call, or vice versa, does not discharge the obligation (9.7 class B1).
    """

    def decorate(function: _F) -> _F:
        setattr(function, COVERS_ATTRIBUTE, tuple(ids))
        if boundary is not None:
            setattr(function, BOUNDARY_ATTRIBUTE, boundary)
        return function

    return decorate
