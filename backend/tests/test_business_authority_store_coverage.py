"""PF-1A-E2-B section 9: VERIFICATION CLASS CONFORMANCE, for THIS store.

The E2-A coverage module already asserts the three-group taxonomy is total,
exclusive and pairwise disjoint. This module asserts the different thing E2-B
owes: that E2-B ITSELF discharges every obligation the manifest places on a
store, and that the parity corpus is exactly the sixty-four scenarios section
9 defines rather than a convenient subset of them.

    every one of the 87 manifest IDs has an EXECUTING E2-B test;
    the PARITY-marked set is EXACTLY the 64: 14 class A + 12 valid-shape +
        38 parity-YES non-store;
    NO class B1 and NO class B2 fixture appears in the parity corpus, because
        no conforming implementation of this schema can return a row the
        schema forbids storing;
    the justified fail-closed reason-code exclusion list is EXACTLY the closed
        three, so it can neither grow silently nor be padded to excuse a
        missing scenario.

A separate coverage marker is used throughout, deliberately. E2-A asserts that
every test covering a class B1 fixture declares a BOUNDARY and exercises the
kernel or the DTO port; an E2-B structural-rejection test does neither,
because its subject is the SHIPPED SCHEMA. Sharing one marker would make each
package's rules contradict the other's.
"""

from __future__ import annotations

import importlib
from pathlib import Path

from app.modules.authorization.business_authority.contract import FAIL_CLOSED_REASONS
from tests.fixtures.pf_1a_e2_a_corpus import (
    AUTHORITY_STORE_FIXTURES,
    CLASS_A,
    CLASS_B1,
    CLASS_B2,
    NON_STORE_SCENARIOS,
    RETIRED_FIXTURE_IDS,
    VALID_SHAPE_SCENARIOS,
)
from tests.fixtures.pf_1a_e2_b_corpus import (
    ALL_E2B_OBLIGATIONS,
    CLASS_A_FIXTURES,
    CLASS_B1_FIXTURES,
    CLASS_B2_FIXTURES,
    JUSTIFIED_PARITY_EXCLUDED_REASON_CODES,
    PARITY_CORPUS,
    PARITY_NO_NON_STORE_IDS,
    PARITY_YES_NON_STORE_IDS,
    STORE_COVERS_ATTRIBUTE,
    STORE_PARITY_ATTRIBUTE,
    VALID_SHAPE_IDS,
    store_covers,
)

_TEST_ROOT = Path(__file__).resolve().parent


def _store_test_modules():
    """Every `test_business_authority_store_*` module, imported for inspection."""

    return [
        importlib.import_module(f"tests.{path.stem}")
        for path in sorted(_TEST_ROOT.glob("test_business_authority_store_*.py"))
    ]


def _store_coverage_index() -> dict[str, list[tuple[str, object]]]:
    index: dict[str, list[tuple[str, object]]] = {}
    for module in _store_test_modules():
        for name, member in vars(module).items():
            if not name.startswith("test_") or not callable(member):
                continue
            for identifier in getattr(member, STORE_COVERS_ATTRIBUTE, ()):
                index.setdefault(identifier, []).append((f"{module.__name__}::{name}", member))
    return index


def _parity_marked_ids() -> set[str]:
    marked: set[str] = set()
    for module in _store_test_modules():
        for name, member in vars(module).items():
            if not name.startswith("test_") or not callable(member):
                continue
            if getattr(member, STORE_PARITY_ATTRIBUTE, False):
                marked.update(getattr(member, STORE_COVERS_ATTRIBUTE, ()))
    return marked


# ===========================================================================
# COUNTS - asserted against the binding manifest, never against a local copy
# ===========================================================================


@store_covers()
def test_the_manifest_counts_are_the_ones_this_store_was_scoped_against() -> None:
    assert len(CLASS_A_FIXTURES) == 14
    assert len(CLASS_B1_FIXTURES) == 12
    assert len(CLASS_B2_FIXTURES) == 3
    assert len(AUTHORITY_STORE_FIXTURES) == 29
    assert len(VALID_SHAPE_IDS) == 12
    assert len(NON_STORE_SCENARIOS) == 46
    assert len(PARITY_YES_NON_STORE_IDS) == 38
    assert len(PARITY_NO_NON_STORE_IDS) == 8
    assert len(PARITY_CORPUS) == 64
    assert len(ALL_E2B_OBLIGATIONS) == 87


@store_covers()
def test_the_parity_corpus_has_exactly_three_parts_and_no_others() -> None:
    assert set(PARITY_CORPUS) == (
        set(CLASS_A_FIXTURES) | set(VALID_SHAPE_IDS) | set(PARITY_YES_NON_STORE_IDS)
    )
    assert set(PARITY_CORPUS).isdisjoint(set(CLASS_B1_FIXTURES) | set(CLASS_B2_FIXTURES))
    assert set(PARITY_CORPUS).isdisjoint(set(PARITY_NO_NON_STORE_IDS))


# ===========================================================================
# EVERY manifest ID has an EXECUTING E2-B test
# ===========================================================================


@store_covers()
def test_every_manifest_id_has_an_executing_e2b_test() -> None:
    """Including class B1 and class B2, whose SEMANTICS E2-A proves.

    E2-B's obligation for those is the structural REJECTION, and it is a
    separate obligation from E2-A's: a defect class must not silently lose
    coverage in the gap between the two packages.
    """

    index = _store_coverage_index()
    missing = [identifier for identifier in ALL_E2B_OBLIGATIONS if identifier not in index]
    assert missing == [], f"manifest IDs with no executing E2-B test: {missing}"


@store_covers()
def test_the_parity_marked_tests_cover_exactly_the_sixty_four_scenarios() -> None:
    """Neither a subset nor a superset.

    A missing entry is a real parity gap. An extra one would mean a class B1
    or B2 shape, or a parity-NO scenario, had been smuggled into the corpus -
    which for B1/B2 could only be done by circumventing a shipped constraint.
    """

    assert _parity_marked_ids() == set(PARITY_CORPUS)


@store_covers()
def test_no_class_b1_or_b2_fixture_is_parity_marked() -> None:
    """Stated separately from the set equality above, because this is the
    property a reviewer probes directly: no conforming implementation of this
    schema can return a row the schema forbids storing, so a B1/B2 shape in
    the parity corpus would necessarily have been seeded by disabling,
    deferring or dropping a constraint."""

    marked = _parity_marked_ids()
    for fixture_id in CLASS_B1_FIXTURES + CLASS_B2_FIXTURES:
        assert fixture_id not in marked, fixture_id


@store_covers()
def test_no_e2b_test_claims_an_unknown_or_retired_identifier() -> None:
    known = set(ALL_E2B_OBLIGATIONS)
    for identifier, entries in _store_coverage_index().items():
        assert identifier in known, f"{identifier} (claimed by {entries[0][0]}) is not in any group"
        assert identifier not in RETIRED_FIXTURE_IDS, f"{identifier} is a retired ID"


@store_covers()
def test_no_e2b_covering_test_is_skipped_or_xfailed() -> None:
    """The coverage is MANDATORY PERMANENTLY. It may never be deleted,
    skipped, xfailed or weakened on the grounds that "the database already
    prevents that" - that reasoning is exactly what class B1 exists to
    refute."""

    for identifier, entries in _store_coverage_index().items():
        for test_name, function in entries:
            marks = {getattr(mark, "name", "") for mark in getattr(function, "pytestmark", [])}
            assert marks.isdisjoint({"skip", "skipif", "xfail"}), (
                f"{test_name} covering {identifier} is skipped or xfailed"
            )


# ===========================================================================
# The JUSTIFIED fail-closed reason-code exclusion list - CLOSED, and checked
# ===========================================================================


def _reason_codes_the_corpus_covers() -> set[str]:
    """Every fail-closed code the parity corpus is expected to produce.

    Read from the BINDING manifest data rather than from this module's own
    opinion: class A fixtures declare their expected reason code, and each
    parity-YES non-store scenario declares its expected result.
    """

    covered = {
        fixture.expected_reason_code
        for fixture in AUTHORITY_STORE_FIXTURES.values()
        if fixture.verification_class == CLASS_A and fixture.expected_reason_code
    }
    for scenario_id in PARITY_YES_NON_STORE_IDS:
        expected = NON_STORE_SCENARIOS[scenario_id].expected
        if expected in FAIL_CLOSED_REASONS:
            covered.add(expected)
    return covered


@store_covers()
def test_the_implemented_exclusion_list_is_exactly_the_closed_manifest_list() -> None:
    """Nothing on it is conditional on what the implemented kernel turns out
    to do, and nothing may be added to excuse a missing scenario."""

    excluded = set(FAIL_CLOSED_REASONS) - _reason_codes_the_corpus_covers()
    assert excluded == set(JUSTIFIED_PARITY_EXCLUDED_REASON_CODES), excluded

    assert set(JUSTIFIED_PARITY_EXCLUDED_REASON_CODES) == {
        "ASSIGNMENT_TARGET_INVALID",
        "AUTHORITY_VERSION_AMBIGUOUS",
        "INTERNAL_CONTRACT_VIOLATION",
    }
    for code, justification in JUSTIFIED_PARITY_EXCLUDED_REASON_CODES.items():
        # Each entry names WHY, and names the covering test or scenario.
        assert len(justification) > 80, code
        assert ("class B1" in justification) or ("kernel-internal" in justification), code


@store_covers()
def test_the_codes_a_reviewer_should_probe_specifically_are_still_parity_covered() -> None:
    """Attack surface 16 and 16c name these four by name, because each moved
    or nearly moved during the F-10 closures:

        AUTHORITY_CODE_NOT_CONFIGURED       moved from class A fixture A-12 to
                                            non-store scenario NS-RS-01;
        AUTHORITY_CONFIGURATION_UNAVAILABLE moved from former A-16 to NS-PT-01;
        SCOPE_CONTEXT_MISSING               moved from former A-20 to NS-RQ-01;
        EVALUATOR_FACTS_INVALID             moved from former A-19 to NS-RQ-02.

    A reviewer finding any of them missing from the parity corpus has found a
    real regression, not a consequence of the reclassification.
    """

    covered = _reason_codes_the_corpus_covers()
    for code in (
        "AUTHORITY_CODE_NOT_CONFIGURED",
        "AUTHORITY_CONFIGURATION_UNAVAILABLE",
        "SCOPE_CONTEXT_MISSING",
        "EVALUATOR_FACTS_INVALID",
    ):
        assert code in covered, code

    marked = _parity_marked_ids()
    for scenario_id in ("NS-RS-01", "NS-PT-01", "NS-RQ-01", "NS-RQ-02"):
        assert scenario_id in marked, scenario_id


# ===========================================================================
# The taxonomy this store was scoped against has not been edited underneath it
# ===========================================================================


@store_covers()
def test_the_class_assignment_this_store_relies_on_is_unchanged() -> None:
    """If a fixture's class changed, this store's obligations changed with it:
    a class A shape moving to B1 would remove a parity obligation, and a B1
    shape moving to A would add one that this schema cannot discharge. Either
    direction is a reconciliation finding, not an implementation preference.
    """

    for fixture in AUTHORITY_STORE_FIXTURES.values():
        if fixture.verification_class == CLASS_A:
            assert fixture.pg_may_store is True, fixture.fixture_id
            assert fixture.pg_parity_required is True, fixture.fixture_id
        else:
            assert fixture.verification_class in (CLASS_B1, CLASS_B2), fixture.fixture_id
            assert fixture.pg_may_store is False, fixture.fixture_id
            assert fixture.pg_parity_required is False, fixture.fixture_id

    # Class B2 rests entirely on two E2-A properties. If either changed, the
    # affected fixture becomes class B1 with a mandatory E2-A test.
    from app.modules.authorization.business_authority.domain import (
        LineageMaterial,
        PublishedObjectVersion,
    )

    assert "object_id" in LineageMaterial.__dataclass_fields__
    assert "object_id" not in PublishedObjectVersion.__dataclass_fields__
    assert LineageMaterial().versions == ()
    assert LineageMaterial().completeness == "COMPLETE"
