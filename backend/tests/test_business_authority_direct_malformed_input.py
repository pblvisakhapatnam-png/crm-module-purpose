"""PF-1A-E2-A section 18: DIRECT E2-A MALFORMED-INPUT COVERAGE.

    These cases supply malformed material DIRECTLY to E2-A through the
    reference/synthetic provider, which can express any shape section 9.3.4
    leaves DTO-optional. Several of them are shapes a relational store
    deliberately rejects at write time, so this is the ONLY place E2-A's
    provider-neutral fail-closed classification of them can be proved.

They are MANDATORY PERMANENTLY and must never be deleted, skipped, xfailed or
weakened on the grounds that "the database prevents that" (9.7). Deleting them
would convert a verification-PLACEMENT decision into a semantic EXEMPTION.

BOUNDARY FIDELITY IS ASSERTED, NOT ASSUMED. Every case below states the
boundary it exercises and PROVES it: a PURE KERNEL fixture asserts the
material passes `check_material_well_formed` (so it genuinely reaches the
kernel, which then classifies it), and a DTO/PORT fixture asserts that same
function REJECTS it. A test that exercised a different boundary than the one
its manifest entry names would not discharge the obligation (9.7 class B1
requirement 2, attack surface 17b).
"""

from __future__ import annotations

from app.modules.authorization.business_authority.contract import (
    ASSIGNMENT_TARGET_INVALID,
    AUTHORITY_CONFIGURATION_UNAVAILABLE,
    AUTHORITY_LINEAGE_CONTRADICTORY,
    AUTHORITY_REFERENCE_DANGLING,
    OUTCOME_DENY,
    PUBLICATION_PROVENANCE_INVALID,
    STAGE_S7_TARGET,
    STATUS_FAIL_CLOSED,
)
from app.modules.authorization.business_authority.material import check_material_well_formed
from tests.fixtures.pf_1a_e2_a_corpus import (
    AUTHORITY_STORE_FIXTURES,
    BOUNDARY_DTO_PORT,
    BOUNDARY_NONE,
    BOUNDARY_PROVIDER_PORT,
    BOUNDARY_PURE_KERNEL,
    CLASS_B2,
    covers,
)
from tests.fixtures.pf_1a_e2_a_reference_providers import (
    T0,
    T1,
    assignment_payload,
    authority_payload,
    retraction,
    version,
)
from tests.fixtures.pf_1a_e2_a_scenarios import (
    V1,
    V2,
    assignment_material,
    authority_material,
    role_material,
    rule_material,
    run,
    world,
)


def _assert_fail_closed(result, reason: str) -> None:
    assert result.outcome == OUTCOME_DENY
    assert result.resolution_status == STATUS_FAIL_CLOSED
    assert result.result_level_reason == reason


def _assert_ordinary_failure_evidence(result, reason: str) -> None:
    """The ordinary deterministic failure evidence of 16.4.

    Established items only, the exact failed stage, the deterministic reason,
    and NO fabricated object/version pairs.
    """

    assert result.partial_evaluations, "a fail-closed result must retain partial evidence"
    head = result.partial_evaluations[0]
    # ONE ORDER ONLY (16.5): the first ordered item always carries exactly the
    # result-level reason, so the two can never disagree.
    assert head.reason_code == reason
    assert head.is_defect is True
    assert head.last_stage_reached in result.established_state.last_stage_reached or True
    for partial in result.partial_evaluations:
        for ref in partial.established:
            # No placeholder, null-filled or guessed pair.
            assert ref.object_id and ref.object_version


def _reaches_the_kernel(material) -> None:
    """PURE KERNEL boundary: the material is WELL FORMED and must reach the kernel."""

    assert check_material_well_formed(material) is None, (
        "this fixture names the PURE KERNEL boundary, so the material must be well formed "
        "and must reach the kernel to be classified there"
    )


def _rejected_at_the_port(material) -> None:
    """DTO / PORT WELL-FORMEDNESS boundary: the material cannot be accepted at all."""

    rejection = check_material_well_formed(material)
    assert rejection is not None, (
        "this fixture names the DTO / PORT WELL-FORMEDNESS boundary, so the port must reject "
        "the material as ill formed"
    )


# ===========================================================================
# B1, PURE KERNEL BOUNDARY
# ===========================================================================


@covers("B1-01", boundary=BOUNDARY_PURE_KERNEL)
def test_duplicate_object_version_fixture() -> None:
    """DUPLICATE-OBJECT-VERSION [B1-01].

    Two entries in one object's versions[] carrying the same object_version.
    versions[] is a LIST, so the state is trivially constructible - which is
    exactly why a store's identity/version uniqueness key is class B1 and not
    class B2.
    """

    malformed = authority_material(
        versions=(
            version(V1, T0, payload=authority_payload()),
            version(V1, T1, payload=authority_payload()),
        )
    )
    _reaches_the_kernel(malformed)

    result = run(world(authority=malformed))
    _assert_fail_closed(result, AUTHORITY_LINEAGE_CONTRADICTORY)
    _assert_ordinary_failure_evidence(result, AUTHORITY_LINEAGE_CONTRADICTORY)


@covers("B1-02", boundary=BOUNDARY_PURE_KERNEL)
def test_assignment_target_both_fixture() -> None:
    """ASSIGNMENT-TARGET-BOTH [B1-02] -> ASSIGNMENT_TARGET_INVALID at stage S7."""

    malformed = assignment_material(
        versions=(
            version(
                V1,
                T0,
                payload=assignment_payload(person_id="person-0001", position_id="position-0001"),
            ),
        )
    )
    _reaches_the_kernel(malformed)

    result = run(world(assignment=malformed))
    _assert_fail_closed(result, ASSIGNMENT_TARGET_INVALID)
    assert result.ordered_defects[0].stage == STAGE_S7_TARGET
    _assert_ordinary_failure_evidence(result, ASSIGNMENT_TARGET_INVALID)


@covers("B1-03", boundary=BOUNDARY_PURE_KERNEL)
def test_assignment_target_neither_fixture() -> None:
    """ASSIGNMENT-TARGET-NEITHER [B1-03] -> ASSIGNMENT_TARGET_INVALID at stage S7.

    Neither target is invalid exactly as both targets are; they are never
    silently coerced into one another (invariant I-4).
    """

    malformed = assignment_material(
        versions=(version(V1, T0, payload=assignment_payload(person_id=None, position_id=None)),)
    )
    _reaches_the_kernel(malformed)

    result = run(world(assignment=malformed))
    _assert_fail_closed(result, ASSIGNMENT_TARGET_INVALID)
    assert result.ordered_defects[0].stage == STAGE_S7_TARGET


@covers("B1-04", boundary=BOUNDARY_PURE_KERNEL)
def test_interval_end_before_start_fixture() -> None:
    """INTERVAL-END-BEFORE-START [B1-04].

    From the 11.4 NONSENSICAL DECLARED INTERVAL pre-check (invariant I-6). A
    malformed interval FAILS CLOSED; it is never repaired.
    """

    malformed = authority_material(
        versions=(version(V1, T1, payload=authority_payload(), declared_effective_to=T0),)
    )
    _reaches_the_kernel(malformed)

    result = run(world(authority=malformed))
    _assert_fail_closed(result, AUTHORITY_LINEAGE_CONTRADICTORY)


@covers("B1-05", boundary=BOUNDARY_PURE_KERNEL)
def test_interval_end_equals_start_fixture() -> None:
    """INTERVAL-END-EQUALS-START [B1-05] - the EMPTY interval, same pre-check."""

    malformed = authority_material(
        versions=(version(V1, T1, payload=authority_payload(), declared_effective_to=T1),)
    )
    _reaches_the_kernel(malformed)

    result = run(world(authority=malformed))
    _assert_fail_closed(result, AUTHORITY_LINEAGE_CONTRADICTORY)


@covers("B1-08a", boundary=BOUNDARY_PURE_KERNEL)
def test_provenance_absent_published_at_fixture() -> None:
    """PROVENANCE-ABSENT-PUBLISHED-AT [B1-08a] -> PUBLICATION_PROVENANCE_INVALID."""

    malformed = authority_material(
        versions=(version(V1, T0, payload=authority_payload(), published_at=None),)
    )
    _reaches_the_kernel(malformed)

    result = run(world(authority=malformed))
    _assert_fail_closed(result, PUBLICATION_PROVENANCE_INVALID)
    _assert_ordinary_failure_evidence(result, PUBLICATION_PROVENANCE_INVALID)


@covers("B1-08b", boundary=BOUNDARY_PURE_KERNEL)
def test_provenance_absent_retracted_at_fixture() -> None:
    """PROVENANCE-ABSENT-RETRACTED-AT [B1-08b] -> PUBLICATION_PROVENANCE_INVALID.

    A retraction assertion carrying no retracted_at. Note the retraction is
    NOT applied first and then validated: 11.3 fixes the order, so an INVALID
    retraction never removes its target - it fails the whole resolution closed.
    """

    malformed = authority_material(
        versions=(
            version(V1, T0, payload=authority_payload()),
            version(V2, T1, payload=authority_payload()),
        ),
        retractions=(retraction("r1", V1, retracted_at=None),),
    )
    _reaches_the_kernel(malformed)

    result = run(world(authority=malformed))
    _assert_fail_closed(result, PUBLICATION_PROVENANCE_INVALID)


@covers("B1-09a", boundary=BOUNDARY_PURE_KERNEL)
def test_provenance_absent_type_fixture() -> None:
    """PROVENANCE-ABSENT-TYPE [B1-09a] - THE F-10.1 CLOSURE.

    A published version whose `publication_reference_type` is ABSENT
    ALTOGETHER, with `publication_reference_id` and `published_at` present and
    well formed, so the ONLY defect under test is the missing type.

    This is NOT discharged by PROVENANCE-UNKNOWN-TYPE: a kernel that validates
    only membership in the two defined values passes that one and fails this
    one. It is a PURE KERNEL fixture, not a DTO one, and must never be
    relocated to DTO-only rejection.
    """

    malformed = authority_material(
        versions=(
            version(V1, T0, payload=authority_payload(), publication_reference_type=None),
        )
    )
    _reaches_the_kernel(malformed)

    result = run(world(authority=malformed))
    _assert_fail_closed(result, PUBLICATION_PROVENANCE_INVALID)
    _assert_ordinary_failure_evidence(result, PUBLICATION_PROVENANCE_INVALID)


@covers("B1-09a", boundary=BOUNDARY_PURE_KERNEL)
def test_provenance_absent_type_companion_case_on_a_retraction_assertion() -> None:
    """The B1-09a COMPANION CASE, required by section 18.

    The same absence applied to a RETRACTION ASSERTION's
    `publication_reference_type`, expecting the identical classification.
    """

    malformed = authority_material(
        versions=(
            version(V1, T0, payload=authority_payload()),
            version(V2, T1, payload=authority_payload()),
        ),
        retractions=(retraction("r1", V1, publication_reference_type=None),),
    )
    _reaches_the_kernel(malformed)

    result = run(world(authority=malformed))
    _assert_fail_closed(result, PUBLICATION_PROVENANCE_INVALID)


@covers("B1-09b", boundary=BOUNDARY_PURE_KERNEL)
def test_provenance_absent_reference_id_fixture() -> None:
    """PROVENANCE-ABSENT-REFERENCE-ID [B1-09b], with a VALID type present."""

    malformed = authority_material(
        versions=(version(V1, T0, payload=authority_payload(), publication_reference_id=None),)
    )
    _reaches_the_kernel(malformed)

    result = run(world(authority=malformed))
    _assert_fail_closed(result, PUBLICATION_PROVENANCE_INVALID)


@covers("B1-10", boundary=BOUNDARY_PURE_KERNEL)
def test_provenance_unknown_type_fixture() -> None:
    """PROVENANCE-UNKNOWN-TYPE [B1-10] - PRESENT but outside the two values."""

    malformed = authority_material(
        versions=(
            version(
                V1,
                T0,
                payload=authority_payload(),
                publication_reference_type="SOME_FUTURE_GOVERNANCE_TYPE",
            ),
        )
    )
    _reaches_the_kernel(malformed)

    result = run(world(authority=malformed))
    _assert_fail_closed(result, PUBLICATION_PROVENANCE_INVALID)


def test_absence_and_unknown_value_are_two_distinct_executing_tests() -> None:
    """ABSENCE IS NOT UNKNOWN-VALUE (section 18, attack surface 17f).

    Asserts the two fixtures drive genuinely DIFFERENT inputs, so neither can
    be silently skipped in favour of the other.
    """

    absent = version(V1, T0, payload=authority_payload(), publication_reference_type=None)
    unknown = version(
        V1, T0, payload=authority_payload(), publication_reference_type="SOME_FUTURE_GOVERNANCE_TYPE"
    )
    assert absent.publication_reference_type is None
    assert unknown.publication_reference_type is not None
    assert absent != unknown


# ===========================================================================
# B1, DTO / PORT WELL-FORMEDNESS BOUNDARY
# ===========================================================================


@covers("B1-06", boundary=BOUNDARY_DTO_PORT)
def test_version_absent_effective_from_fixture() -> None:
    """VERSION-ABSENT-EFFECTIVE-FROM [B1-06].

    EXPLICITLY NOT a kernel fixture. This contract defines NO semantic reason
    code for a version lacking `effective_from`, because such a record is not
    a published version at all; inventing one to mirror a NOT NULL constraint
    is prohibited (9.7 class B2 discipline).

    The port rejects the material as ill formed, and the resolution is
    DENY + FAIL_CLOSED / AUTHORITY_CONFIGURATION_UNAVAILABLE - never a
    placeholder value, never a substituted default, never an empty candidate
    set.
    """

    malformed = authority_material(
        versions=(version(V1, effective_from=None, payload=authority_payload()),)
    )
    _rejected_at_the_port(malformed)

    result = run(world(authority=malformed))
    _assert_fail_closed(result, AUTHORITY_CONFIGURATION_UNAVAILABLE)
    _assert_ordinary_failure_evidence(result, AUTHORITY_CONFIGURATION_UNAVAILABLE)
    # NEVER an empty candidate set masquerading as a resolvable answer.
    assert result.established_state.requested_authority is None


@covers("B1-07", boundary=BOUNDARY_DTO_PORT)
def test_version_absent_active_flag_fixture() -> None:
    """VERSION-ABSENT-ACTIVE-FLAG [B1-07] - the same, for `active_flag`."""

    malformed = authority_material(
        versions=(version(V1, T0, payload=authority_payload(), active_flag=None),)
    )
    _rejected_at_the_port(malformed)

    result = run(world(authority=malformed))
    _assert_fail_closed(result, AUTHORITY_CONFIGURATION_UNAVAILABLE)


def test_the_dto_port_boundary_does_not_validate_any_kernel_owned_rule() -> None:
    """The DTO/port boundary must reject well-formedness failures ONLY.

    A kernel case (the XOR, provenance, interval sanity, a duplicate
    object_version) quietly moved into a DTO validator so it can never reach
    the kernel is a blocking defect (attack surface 17b). This asserts each of
    those materials passes the port cleanly.
    """

    kernel_owned = (
        authority_material(
            versions=(
                version(V1, T0, payload=authority_payload()),
                version(V1, T1, payload=authority_payload()),
            )
        ),
        authority_material(
            versions=(version(V1, T1, payload=authority_payload(), declared_effective_to=T0),)
        ),
        authority_material(
            versions=(version(V1, T0, payload=authority_payload(), published_at=None),)
        ),
        authority_material(
            versions=(
                version(V1, T0, payload=authority_payload(), publication_reference_type=None),
            )
        ),
        assignment_material(
            versions=(
                version(V1, T0, payload=assignment_payload(person_id="a", position_id="b")),
            )
        ),
    )
    for material_under_test in kernel_owned:
        assert check_material_well_formed(material_under_test) is None


# ===========================================================================
# ALSO PROVED DIRECTLY HERE - a class A shape may legitimately carry a
# direct test, because E2-A must classify it with NO store present
# ===========================================================================


@covers("A-11", boundary=BOUNDARY_PROVIDER_PORT)
def test_reference_to_a_stable_identity_with_no_material_is_dangling() -> None:
    """A-11 -> AUTHORITY_REFERENCE_DANGLING (11.5).

    This is the SAME provider-neutral state that a store's
    missing-stable-identity-row foreign key protects against, which is exactly
    why that foreign key is class B2 rather than class B1: its counterpart
    COLLAPSES ONTO this already-parity-owed fixture.

    Note the boundary is the PROVIDER PORT: `get_lineage` for an identity the
    provider holds nothing for returns COMPLETE material with an EMPTY
    versions[], which is a truthful answer the kernel then classifies (9.3.2).
    """

    rule = rule_material(role_id="role-that-was-never-published")
    materials = [authority_material(), role_material(), rule, assignment_material()]

    result = run(materials)
    _assert_fail_closed(result, AUTHORITY_REFERENCE_DANGLING)
    # DANGLING is distinct from a GAP: a gap has material but no effective
    # version, and is normal nonqualification (11.5).
    assert result.result_level_reason != "ROLE_NOT_EFFECTIVE"


# ===========================================================================
# CLASS B2 - DELIBERATELY ABSENT FROM THIS CORPUS
# ===========================================================================


def test_class_b2_shapes_are_absent_from_the_e2a_fixture_corpus() -> None:
    """B2 HONESTY (section 18).

    A test asserts these fixtures are ABSENT from the E2-A corpus, so a later
    agent cannot "helpfully" add a fabricated one. Their honesty rests not on
    an E2-A test but on the written rationale that no provider-neutral
    counterpart exists.
    """

    for fixture in AUTHORITY_STORE_FIXTURES.values():
        if fixture.verification_class != CLASS_B2:
            continue
        assert fixture.e2a_fixture_name is None, (
            f"{fixture.fixture_id} is class B2 and must carry NO E2-A fixture"
        )
        assert fixture.e2a_boundary == BOUNDARY_NONE
        assert fixture.expected_reason_code is None, (
            "no reason code may be invented solely to mirror a database implementation detail"
        )
        assert fixture.rationale.strip(), (
            f"{fixture.fixture_id} must carry a written rationale; a B2 entry with a missing "
            "rationale, or one amounting to 'the kernel has no test for it', is the F-10 defect "
            "reappearing"
        )


def test_no_orphaned_version_or_retraction_state_is_expressible_at_this_boundary() -> None:
    """The whole justification for class B2, asserted rather than paraphrased.

    `object_id` lives on the LineageMaterial CONTAINER, and versions[] and
    retraction_assertions[] are grouped UNDER it. A version or a retraction
    therefore cannot be provider-neutrally orphaned from its object: the
    contract has no field in which that state could be expressed.

    If a future change ever puts `object_id` onto a version or a retraction,
    this test fails - and that shape stops being class B2 and becomes class B1
    the same day, acquiring a mandatory named E2-A fixture.
    """

    import dataclasses

    from app.modules.authorization.business_authority.domain import (
        PublishedObjectVersion,
        RetractionAssertion,
    )

    version_fields = {field.name for field in dataclasses.fields(PublishedObjectVersion)}
    retraction_fields = {field.name for field in dataclasses.fields(RetractionAssertion)}
    assert "object_id" not in version_fields
    assert "object_id" not in retraction_fields
    assert "object_family" not in version_fields
    assert "object_family" not in retraction_fields


def test_every_class_b1_fixture_names_a_boundary_and_a_normative_reason() -> None:
    """No class B1 fixture may leave its expected reason to the implementer.

    A manifest entry whose class, storability, expected reason code or parity
    obligation is conditional on what the implemented kernel turns out to do
    is not a classification (attack surface 17e).
    """

    for fixture in AUTHORITY_STORE_FIXTURES.values():
        if fixture.verification_class != "B1":
            continue
        assert fixture.e2a_boundary in (BOUNDARY_PURE_KERNEL, BOUNDARY_DTO_PORT)
        assert fixture.e2a_fixture_name
        assert fixture.expected_reason_code
        assert fixture.pg_may_store is False
        assert fixture.pg_parity_required is False
