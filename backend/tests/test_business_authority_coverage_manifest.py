"""PF-1A-E2-A section 18: VERIFICATION CLASS ASSIGNMENT.

This module is the mechanical check that the implementation actually
discharges the manifests, rather than merely appearing to. It is the check
that would have caught F-10.1, where one manifest ID covered two malformed
shapes and only one of them had an executing test.

    TAXONOMY SCOPE FIRST (9.7.0). A coverage test partitions the whole
    negative, valid-shape and conformance corpus into exactly THREE
    pairwise-disjoint, exhaustive groups.

Everything asserted here is a property of the CORPUS, not of any one
resolution: which group each item is in, that every non-B2 item has a named
executing test, that each class B1 test exercises the boundary its manifest
entry names, and that no item sits in two groups or in none.
"""

from __future__ import annotations

import importlib
import inspect
from pathlib import Path

from tests.fixtures.pf_1a_e2_a_corpus import (
    AUTHORITY_STORE_FIXTURES,
    BOUNDARY_ATTRIBUTE,
    BOUNDARY_DTO_PORT,
    BOUNDARY_NONE,
    BOUNDARY_PURE_KERNEL,
    CLASS_A,
    CLASS_B1,
    CLASS_B2,
    CLOSED_SEAMS,
    COVERS_ATTRIBUTE,
    NON_STORE_SCENARIOS,
    RETIRED_FIXTURE_IDS,
    VALID_SHAPE_SCENARIOS,
)

_TEST_ROOT = Path(__file__).resolve().parent


def _corpus_test_modules():
    """Every `test_business_authority_*` module, imported for introspection."""

    modules = []
    for path in sorted(_TEST_ROOT.glob("test_business_authority_*.py")):
        modules.append(importlib.import_module(f"tests.{path.stem}"))
    return modules


def _coverage_index() -> dict[str, list[tuple[str, object]]]:
    """manifest id -> [(qualified test name, function), ...]."""

    index: dict[str, list[tuple[str, object]]] = {}
    for module in _corpus_test_modules():
        for name, member in vars(module).items():
            if not name.startswith("test_") or not callable(member):
                continue
            for identifier in getattr(member, COVERS_ATTRIBUTE, ()):
                index.setdefault(identifier, []).append(
                    (f"{module.__name__}::{name}", member)
                )
    return index


# ===========================================================================
# TAXONOMY SCOPE  - three pairwise-disjoint, exhaustive groups (9.7.0)
# ===========================================================================


def test_the_three_groups_are_pairwise_disjoint() -> None:
    """No item appears in more than one of the three groups, and none appears
    in none of them."""

    store = set(AUTHORITY_STORE_FIXTURES)
    valid = set(VALID_SHAPE_SCENARIOS)
    non_store = set(NON_STORE_SCENARIOS)

    assert store & valid == set()
    assert store & non_store == set()
    assert valid & non_store == set()


def test_the_group_counts_match_the_binding_manifest() -> None:
    """14 / 12 / 3 authority-store fixtures, 12 valid-shape scenarios and 46
    non-store scenarios (E2-B 5.7 "Counts after closure", 5.7A totality)."""

    by_class: dict[str, list[str]] = {}
    for fixture in AUTHORITY_STORE_FIXTURES.values():
        by_class.setdefault(fixture.verification_class, []).append(fixture.fixture_id)

    assert len(by_class[CLASS_A]) == 14
    assert len(by_class[CLASS_B1]) == 12
    assert len(by_class[CLASS_B2]) == 3
    assert len(AUTHORITY_STORE_FIXTURES) == 29
    assert len(VALID_SHAPE_SCENARIOS) == 12
    assert len(NON_STORE_SCENARIOS) == 46


def test_retired_manifest_ids_are_never_reused() -> None:
    """A-03, A-12, A-16, A-18, A-19 and A-20 are retired, each recorded with
    the scenario that now carries its obligation, so a later reader tracing an
    old citation lands on the replacement rather than on silence."""

    assert set(RETIRED_FIXTURE_IDS) == {"A-03", "A-12", "A-16", "A-18", "A-19", "A-20"}
    live_ids = set(AUTHORITY_STORE_FIXTURES) | set(VALID_SHAPE_SCENARIOS) | set(
        NON_STORE_SCENARIOS
    )
    for retired, replacement in RETIRED_FIXTURE_IDS.items():
        assert retired not in live_ids, f"{retired} was reused"
        assert replacement.strip(), f"{retired} records no replacement"


# ===========================================================================
# The AUTHORITY-STORE group: exactly one class, and never "N/A" storability
# ===========================================================================


def test_every_authority_store_fixture_carries_exactly_one_class() -> None:
    for fixture in AUTHORITY_STORE_FIXTURES.values():
        assert fixture.verification_class in (CLASS_A, CLASS_B1, CLASS_B2), fixture.fixture_id


def test_no_classified_fixture_records_its_storability_as_not_applicable() -> None:
    """An item that would need an "N/A" storability answer is, by
    construction, not an authority-store fixture at all. That contradiction is
    exactly what the fourth review found in A-16, A-18, A-19 and A-20 (9.7.0).
    """

    for fixture in AUTHORITY_STORE_FIXTURES.values():
        assert isinstance(fixture.pg_may_store, bool), fixture.fixture_id


def test_class_a_shapes_are_storable_and_owed_full_parity() -> None:
    for fixture in AUTHORITY_STORE_FIXTURES.values():
        if fixture.verification_class != CLASS_A:
            continue
        assert fixture.pg_may_store is True, fixture.fixture_id
        assert fixture.pg_parity_required is True, fixture.fixture_id
        assert fixture.expected_reason_code, fixture.fixture_id


def test_class_b1_and_b2_shapes_are_not_storable_and_are_parity_excluded() -> None:
    """Exclusion from a store's parity corpus is a VERIFICATION-PLACEMENT
    decision, never a semantic exemption (9.7)."""

    for fixture in AUTHORITY_STORE_FIXTURES.values():
        if fixture.verification_class == CLASS_A:
            continue
        assert fixture.pg_may_store is False, fixture.fixture_id
        assert fixture.pg_parity_required is False, fixture.fixture_id


def test_a_fail_closed_outcome_is_not_by_itself_a_class_label() -> None:
    """F-10.3a. Probe each entry with one question: does this contract require
    the kernel to REJECT that state as INVALID?

    NS-RS-01 is the worked example of the answer being "no": valid rows, a
    correct DENY + FAIL_CLOSED / AUTHORITY_CODE_NOT_CONFIGURED, and no class.
    """

    assert "NS-RS-01" in NON_STORE_SCENARIOS
    assert "NS-RS-01" not in AUTHORITY_STORE_FIXTURES
    assert "A-12" not in AUTHORITY_STORE_FIXTURES

    # AUTHORITY_CODE_NOT_CONFIGURED is the outcome of a VALID configuration
    # read at an as_of, so no authority-store fixture may claim it.
    for fixture in AUTHORITY_STORE_FIXTURES.values():
        assert fixture.expected_reason_code != "AUTHORITY_CODE_NOT_CONFIGURED", fixture.fixture_id


def test_the_valid_shape_group_carries_no_class_label_and_stays_parity_owed() -> None:
    """Calling a valid stored shape "class A" is the F-10.3a defect; dropping
    one from the parity corpus because it "is not a negative fixture" is the
    mirror error."""

    for scenario in VALID_SHAPE_SCENARIOS.values():
        assert not hasattr(scenario, "verification_class")
        assert scenario.pg_parity_required is True, scenario.scenario_id


# ===========================================================================
# The NON-STORE group: a named seam, both store answers, a parity statement
# ===========================================================================


def test_every_non_store_scenario_sits_on_an_already_defined_seam() -> None:
    """NO NEW PROVIDER SURFACE MAY BE INVENTED in order to classify a
    scenario. A scenario that does not sit on a seam this contract already
    defines is a contract gap to raise, not a licence to add a seam (9.7.0)."""

    for scenario in NON_STORE_SCENARIOS.values():
        assert scenario.seam in CLOSED_SEAMS, f"{scenario.scenario_id}: {scenario.seam}"


def test_every_non_store_scenario_answers_both_store_questions_separately() -> None:
    """Store PARTICIPATION and store SUBJECTHOOD are two INDEPENDENT
    dimensions: neither may be inferred from the other (F-10.3-DC-02).

    `subject_is_store_state` is NO on every row by construction - it is the
    5.7A entry criterion - and is asserted rather than left to be assumed.
    """

    for scenario in NON_STORE_SCENARIOS.values():
        assert isinstance(scenario.pg_data_participates, bool), scenario.scenario_id
        assert scenario.subject_is_store_state is False, scenario.scenario_id
        assert scenario.expected.strip(), scenario.scenario_id


def test_the_two_store_dimensions_are_genuinely_independent() -> None:
    """Both values of PG-DATA occur, so the column carries information rather
    than mirroring the class label."""

    values = {scenario.pg_data_participates for scenario in NON_STORE_SCENARIOS.values()}
    assert values == {True, False}


def test_exactly_the_eight_named_scenarios_owe_no_parity() -> None:
    """PARITY = NO never means "tested once and loosely". It means an
    AGREEMENT test has no meaningful second side - a surface/structural
    assertion, or a state no provider can present (5.7A column meanings)."""

    no_parity = {
        scenario.scenario_id
        for scenario in NON_STORE_SCENARIOS.values()
        if not scenario.parity_required
    }
    assert no_parity == {
        "NS-AP-04",
        "NS-PR-01",
        "NS-PR-02",
        "NS-PR-03",
        "NS-RS-03",
        "NS-DO-06",
        "NS-K-01",
        "NS-K-02",
    }
    assert len(NON_STORE_SCENARIOS) - len(no_parity) == 38


# ===========================================================================
# EVERY non-B2 item has a NAMED, EXECUTING test
# ===========================================================================


def test_every_class_a_fixture_has_an_executing_e2a_test() -> None:
    """A class A shape may legitimately carry a direct E2-A test too: E2-A must
    classify it with NO store present."""

    index = _coverage_index()
    missing = [
        fixture.fixture_id
        for fixture in AUTHORITY_STORE_FIXTURES.values()
        if fixture.verification_class == CLASS_A and fixture.fixture_id not in index
    ]
    assert missing == [], f"class A fixtures with no executing E2-A test: {missing}"


def test_every_valid_shape_and_non_store_scenario_has_an_executing_test() -> None:
    index = _coverage_index()
    missing = [
        identifier
        for identifier in list(VALID_SHAPE_SCENARIOS) + list(NON_STORE_SCENARIOS)
        if identifier not in index
    ]
    assert missing == [], f"scenarios with no executing E2-A test: {missing}"


def test_class_b2_fixtures_have_no_e2a_test_by_design() -> None:
    """They appear NOWHERE in section 18's DIRECT E2-A MALFORMED-INPUT
    COVERAGE, so a later agent cannot "helpfully" add a fabricated one."""

    index = _coverage_index()
    for fixture in AUTHORITY_STORE_FIXTURES.values():
        if fixture.verification_class != CLASS_B2:
            continue
        assert fixture.fixture_id not in index, fixture.fixture_id
        assert fixture.rationale.strip(), fixture.fixture_id


def test_no_covering_test_is_skipped_or_xfailed() -> None:
    """The class B1 coverage is MANDATORY PERMANENTLY and may never be
    deleted, skipped, xfailed or weakened on the grounds that "the database
    already prevents that" (9.7)."""

    for identifier, entries in _coverage_index().items():
        for test_name, function in entries:
            marks = getattr(function, "pytestmark", [])
            names = {getattr(mark, "name", "") for mark in marks}
            assert "skip" not in names, f"{test_name} covering {identifier} is skipped"
            assert "skipif" not in names, f"{test_name} covering {identifier} is skipped"
            assert "xfail" not in names, f"{test_name} covering {identifier} is xfailed"


def test_no_test_claims_coverage_of_an_unknown_or_retired_identifier() -> None:
    known = set(AUTHORITY_STORE_FIXTURES) | set(VALID_SHAPE_SCENARIOS) | set(
        NON_STORE_SCENARIOS
    )
    for identifier, entries in _coverage_index().items():
        assert identifier in known, f"{identifier} (claimed by {entries[0][0]}) is not in any group"


# ===========================================================================
# CLASS B1: one shape per ID, one named fixture per ID, and BOUNDARY FIDELITY
# ===========================================================================


def test_the_class_b1_fixture_name_to_manifest_id_mapping_is_one_to_one() -> None:
    """F-10.1 arose precisely because one ID (`B1-09`) covered two shapes and
    only one of them had a fixture. A test that discharges two manifest IDs, or
    a manifest ID with no distinctly named covering test, fails this
    assertion."""

    b1 = [
        fixture
        for fixture in AUTHORITY_STORE_FIXTURES.values()
        if fixture.verification_class == CLASS_B1
    ]
    names = [fixture.e2a_fixture_name for fixture in b1]
    assert len(names) == len(set(names)) == 12

    index = _coverage_index()
    for fixture in b1:
        assert fixture.fixture_id in index, f"{fixture.fixture_id} has no covering test"


def test_every_class_b1_fixture_names_its_boundary_and_its_test_exercises_that_boundary() -> None:
    """BOUNDARY FIDELITY (section 18, 9.7 class B1 requirement 2).

    A DTO-boundary fixture asserted through a kernel call, or vice versa, does
    NOT discharge the obligation - in particular a DTO/port well-formedness
    case dressed up as a kernel fixture, or a kernel case quietly moved into a
    DTO validator so it can never reach the kernel (attack surface 17b).
    """

    index = _coverage_index()
    for fixture in AUTHORITY_STORE_FIXTURES.values():
        if fixture.verification_class != CLASS_B1:
            continue
        assert fixture.e2a_boundary in (BOUNDARY_PURE_KERNEL, BOUNDARY_DTO_PORT)

        for test_name, function in index[fixture.fixture_id]:
            declared = getattr(function, BOUNDARY_ATTRIBUTE, None)
            assert declared == fixture.e2a_boundary, (
                f"{test_name} covers {fixture.fixture_id}, whose manifest boundary is "
                f"{fixture.e2a_boundary}, but declares {declared}"
            )
            # And the test body genuinely exercises that boundary.
            source = inspect.getsource(function)
            expected_helper = (
                "_reaches_the_kernel"
                if fixture.e2a_boundary == BOUNDARY_PURE_KERNEL
                else "_rejected_at_the_port"
            )
            assert expected_helper in source, (
                f"{test_name} does not exercise the {fixture.e2a_boundary} boundary"
            )


def test_the_two_dto_boundary_fixtures_are_exactly_the_two_named_ones() -> None:
    """This contract defines NO semantic reason code for a version lacking
    `effective_from` or `active_flag`, and inventing one to mirror a NOT NULL
    constraint is prohibited. Everything else class B1 is a PURE KERNEL
    fixture."""

    dto_boundary = {
        fixture.fixture_id
        for fixture in AUTHORITY_STORE_FIXTURES.values()
        if fixture.e2a_boundary == BOUNDARY_DTO_PORT
    }
    assert dto_boundary == {"B1-06", "B1-07"}

    for fixture_id in dto_boundary:
        fixture = AUTHORITY_STORE_FIXTURES[fixture_id]
        assert fixture.expected_reason_code == "AUTHORITY_CONFIGURATION_UNAVAILABLE"


def test_absence_and_unknown_value_are_two_distinct_manifest_entries() -> None:
    """ABSENCE IS NOT UNKNOWN-VALUE (F-10.1). Two distinct executing tests over
    two distinct inputs, and neither skipped in favour of the other."""

    absent = AUTHORITY_STORE_FIXTURES["B1-09a"]
    unknown = AUTHORITY_STORE_FIXTURES["B1-10"]

    assert absent.e2a_fixture_name == "PROVENANCE-ABSENT-TYPE"
    assert unknown.e2a_fixture_name == "PROVENANCE-UNKNOWN-TYPE"
    assert absent.e2a_boundary == unknown.e2a_boundary == BOUNDARY_PURE_KERNEL
    assert absent.expected_reason_code == unknown.expected_reason_code

    index = _coverage_index()
    absent_tests = {name for name, _ in index["B1-09a"]}
    unknown_tests = {name for name, _ in index["B1-10"]}
    assert absent_tests and unknown_tests
    assert absent_tests.isdisjoint(unknown_tests)


def test_the_five_provenance_shapes_are_separately_named_and_separately_tested() -> None:
    """The provenance B1 fixtures were split one-shape-per-ID so no single
    manifest ID can again cover two shapes of which only one is actually
    tested."""

    provenance_ids = ["B1-08a", "B1-08b", "B1-09a", "B1-09b", "B1-10"]
    index = _coverage_index()
    names = set()
    for fixture_id in provenance_ids:
        fixture = AUTHORITY_STORE_FIXTURES[fixture_id]
        assert fixture.expected_reason_code == "PUBLICATION_PROVENANCE_INVALID"
        assert fixture.e2a_fixture_name not in names
        names.add(fixture.e2a_fixture_name)
        assert fixture_id in index
    assert len(names) == 5


# ===========================================================================
# B2 RE-EXAMINATION trigger
# ===========================================================================


def test_class_b2_entries_carry_a_rationale_and_no_invented_reason_code() -> None:
    """A B2 entry whose rationale is missing, circular, or amounting to "no
    kernel test exists" is a blocking finding (attack surface 17c). No reason
    code and no DTO field may be invented solely to mirror a database
    implementation detail."""

    for fixture in AUTHORITY_STORE_FIXTURES.values():
        if fixture.verification_class != CLASS_B2:
            continue
        assert fixture.e2a_fixture_name is None
        assert fixture.e2a_boundary == BOUNDARY_NONE
        assert fixture.expected_reason_code is None
        rationale = fixture.rationale.lower()
        assert len(rationale) > 100, fixture.fixture_id
        assert "no kernel test" not in rationale, fixture.fixture_id
        # The rationale must explain WHY there is no counterpart, and the
        # contract gives exactly two such justifications: either the state is
        # INEXPRESSIBLE because object_id lives on the LineageMaterial
        # container (B2-01, B2-02), or it DECODES ONTO an already-classified
        # class A fixture and so leaves no DISTINCT malformed state to place
        # (B2-03, which collapses onto A-11). Anything else is B2 being used
        # as a semantic escape hatch.
        anchors = ("object_id", "LineageMaterial", "A-11")
        assert any(anchor in fixture.rationale for anchor in anchors), fixture.fixture_id
