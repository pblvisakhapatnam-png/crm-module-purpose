"""PF-1A-E2-A: closed vocabularies, the reason-rank table and the DTO split.

Covers the section 18 TOTALITY assertion (NS-DO-06) and the section 19.L2
requirement that the 9.3.4 DTO-required/DTO-optional split holds EXACTLY as
declared - because a change to that split can turn a class B2 shape into a
representable class B1 shape and would silently strip it of all E2-A coverage.
"""

from __future__ import annotations

import dataclasses
from datetime import datetime

import pytest

from app.modules.authorization.business_authority import contract
from app.modules.authorization.business_authority.domain import (
    AuthenticatedActor,
    BusinessAuthorityAssignmentPayload,
    LineageMaterial,
    PublishedObjectVersion,
    RetractionAssertion,
)
from tests.fixtures.pf_1a_e2_a_corpus import covers

# ---------------------------------------------------------------------------
# Closed vocabularies
# ---------------------------------------------------------------------------


def test_the_four_object_families_carry_a_fixed_closed_ranking() -> None:
    assert contract.OBJECT_FAMILIES == (
        contract.BUSINESS_AUTHORITY,
        contract.BUSINESS_AUTHORITY_ROLE,
        contract.BUSINESS_AUTHORITY_RULE,
        contract.BUSINESS_AUTHORITY_ASSIGNMENT,
    )
    # The exact ranking of 15.5 form (a). Reordering it changes which defect is
    # reported for a same-stage multi-family collision, so it is asserted
    # literally rather than derived from the tuple above.
    assert contract.OBJECT_FAMILY_RANK == {
        "BUSINESS_AUTHORITY": 0,
        "BUSINESS_AUTHORITY_ROLE": 1,
        "BUSINESS_AUTHORITY_RULE": 2,
        "BUSINESS_AUTHORITY_ASSIGNMENT": 3,
    }


def test_stage_ranks_are_s0_to_s9_in_order() -> None:
    assert contract.STAGES == ("S0", "S1", "S2", "S3", "S4", "S5", "S6", "S7", "S8", "S9")
    assert [contract.STAGE_RANK[stage] for stage in contract.STAGES] == list(range(10))


def test_publication_reference_types_are_exactly_the_two_defined_values() -> None:
    # CONFIGURATION_CHANGE is a FORWARD-COMPATIBLE reference shape only in E2:
    # E3 populates it, and E2 never creates such a record.
    assert contract.PUBLICATION_REFERENCE_TYPES == (
        "BOOTSTRAP_PROVENANCE",
        "CONFIGURATION_CHANGE",
    )


def test_the_evaluator_registry_types_are_the_four_named_ones() -> None:
    assert contract.REGISTERED_EVALUATOR_TYPES == (
        "NONE",
        "NUMERIC_BAND",
        "PERCENTAGE_BAND",
        "EXACT_VALUE_SET",
    )


def test_outcome_and_status_are_two_orthogonal_dimensions() -> None:
    # Never collapsed into a single boolean.
    assert contract.OUTCOME_ALLOW != contract.STATUS_RESOLVED
    assert {contract.OUTCOME_ALLOW, contract.OUTCOME_DENY} == {"ALLOW", "DENY"}
    assert {contract.STATUS_RESOLVED, contract.STATUS_FAIL_CLOSED} == {"RESOLVED", "FAIL_CLOSED"}


def test_every_fail_closed_reason_code_of_section_14_3_is_present() -> None:
    # The list is asserted literally, so removing or renaming a code is a test
    # failure rather than a silent narrowing of the taxonomy.
    assert set(contract.FAIL_CLOSED_REASONS) == {
        "ACTOR_PERSON_PROVIDER_NOT_CONFIGURED",
        "HR_REFERENCE_PROVIDER_NOT_CONFIGURED",
        "ACTOR_PERSON_MAPPING_MISSING",
        "ACTOR_PERSON_MAPPING_AMBIGUOUS",
        "HR_REFERENCE_UNAVAILABLE",
        "HR_REFERENCE_STALE",
        "EMPLOYMENT_STATE_MISSING",
        "EMPLOYMENT_STATE_AMBIGUOUS",
        "POSITION_STATE_MISSING",
        "POSITION_STATE_AMBIGUOUS",
        "INCUMBENCY_MISSING",
        "INCUMBENCY_AMBIGUOUS",
        "ORG_UNIT_STATE_MISSING",
        "ORG_UNIT_STATE_AMBIGUOUS",
        "ORG_HIERARCHY_UNRESOLVABLE",
        "AUTHORITY_CODE_NOT_CONFIGURED",
        "AUTHORITY_CONFIGURATION_UNAVAILABLE",
        "AUTHORITY_VERSION_AMBIGUOUS",
        "AUTHORITY_LINEAGE_CONTRADICTORY",
        "AUTHORITY_REFERENCE_DANGLING",
        "PUBLICATION_PROVENANCE_INVALID",
        "ASSIGNMENT_TARGET_INVALID",
        "SCOPE_SEMANTICS_UNSUPPORTED",
        "SCOPE_CONTEXT_MISSING",
        "EVALUATOR_UNKNOWN",
        "EVALUATOR_PAYLOAD_INVALID",
        "EVALUATOR_FACTS_INVALID",
        "INTERNAL_CONTRACT_VIOLATION",
    }


_SPECIFIC_PATH_LEVEL_REASONS = {
    "ASSIGNMENT_NOT_EFFECTIVE",
    "ASSIGNMENT_NOT_ACTIVE",
    "ASSIGNMENT_TARGET_NOT_THIS_PERSON",
    "ROLE_NOT_EFFECTIVE",
    "ROLE_NOT_ACTIVE",
    "RULE_NOT_EFFECTIVE",
    "RULE_NOT_ACTIVE",
    "RULE_SCOPE_NOT_MATCHED",
    "ASSIGNMENT_SCOPE_NOT_MATCHED",
    "SCOPE_COMPOSITION_NOT_SATISFIED",
    "EVALUATOR_CONDITION_NOT_SATISFIED",
}


def test_every_path_level_reason_of_section_14_1_is_present() -> None:
    """The eleven SPECIFIC reasons of 14.1, plus the ONE bounded fallback.

    The split is asserted rather than a flat set, because the two groups have
    different standing: a specific reason MUST be used wherever it applies, and
    the fallback exists only so the taxonomy does not grow a new permanent code
    for every rare, fully understood variant.
    """

    assert set(contract.PATH_LEVEL_REASONS) == _SPECIFIC_PATH_LEVEL_REASONS | {
        "OTHER_NONQUALIFICATION"
    }
    assert contract.OTHER_NONQUALIFICATION not in _SPECIFIC_PATH_LEVEL_REASONS


def test_there_is_exactly_one_bounded_fallback_and_no_fail_closed_equivalent() -> None:
    """There is deliberately NO `OTHER_FAIL_CLOSED`.

    INTERNAL_CONTRACT_VIOLATION remains the defensive kernel-invariant
    fail-closed category already defined by 14.3, and the fallback must never
    be able to stand in for uncertainty of any kind.
    """

    fallbacks = [code for code in contract.ALL_REASON_CODES if code.startswith("OTHER_")]
    assert fallbacks == ["OTHER_NONQUALIFICATION"]

    assert contract.OTHER_NONQUALIFICATION in contract.PATH_LEVEL_REASONS
    assert contract.OTHER_NONQUALIFICATION not in contract.FAIL_CLOSED_REASONS
    assert contract.OTHER_NONQUALIFICATION not in contract.RESULT_LEVEL_RESOLVED_REASONS
    assert contract.INTERNAL_CONTRACT_VIOLATION in contract.FAIL_CLOSED_REASONS


def test_the_fallback_ranks_last_among_path_level_reasons() -> None:
    """Where a specific reason also applies it is the specific one that must be
    used, and the rank table makes that preference visible."""

    fallback_rank = contract.REASON_CODE_RANK[contract.OTHER_NONQUALIFICATION]
    for reason in _SPECIFIC_PATH_LEVEL_REASONS:
        assert contract.REASON_CODE_RANK[reason] < fallback_rank, reason


def test_inactive_and_ineffective_are_separate_codes_for_every_family() -> None:
    # Distinction 3 of 14.4. Never report one as the other, and never merge
    # them into a single "not applicable" code.
    for family in ("ASSIGNMENT", "ROLE", "RULE"):
        assert f"{family}_NOT_EFFECTIVE" in contract.PATH_LEVEL_REASONS
        assert f"{family}_NOT_ACTIVE" in contract.PATH_LEVEL_REASONS


# ---------------------------------------------------------------------------
# NS-DO-06  the declared rank tables themselves
# ---------------------------------------------------------------------------


@covers("NS-DO-06")
def test_every_fail_closed_reason_code_has_an_explicit_declared_rank() -> None:
    missing = [
        code for code in contract.FAIL_CLOSED_REASONS if code not in contract.REASON_CODE_RANK
    ]
    assert missing == [], f"fail-closed reason codes with no declared rank: {missing}"


@covers("NS-DO-06")
def test_every_reason_code_of_any_kind_has_an_explicit_declared_rank() -> None:
    # 16.5 orders nonqualifying partial evaluations by reason_code_rank, so the
    # path-level and result-level codes need ranks as well.
    missing = [code for code in contract.ALL_REASON_CODES if code not in contract.REASON_CODE_RANK]
    assert missing == []


@covers("NS-DO-06")
def test_reason_ranks_are_unique_so_the_third_sort_component_is_total() -> None:
    ranks = [contract.REASON_CODE_RANK[code] for code in contract.ALL_REASON_CODES]
    assert len(ranks) == len(set(ranks)), "two reason codes share one rank"


@covers("NS-DO-06")
def test_reason_ranks_are_not_alphabetical_and_not_definition_order() -> None:
    """The rank must be an explicit integer assigned deliberately (15.5).

    Deriving it from the code's spelling, or from accidental enum/tuple order,
    is called out as a defect by attack surface 25a. This asserts the table is
    not either of those by construction.
    """

    alphabetical = sorted(contract.FAIL_CLOSED_REASONS)
    by_rank = sorted(contract.FAIL_CLOSED_REASONS, key=lambda c: contract.REASON_CODE_RANK[c])
    assert by_rank != alphabetical

    definition_order = list(contract.FAIL_CLOSED_REASONS)
    assert by_rank != definition_order


@covers("NS-DO-06")
def test_the_subject_token_vocabulary_is_closed_and_ranked() -> None:
    assert set(contract.SUBJECT_TOKEN_RANK) == set(contract.SUBJECT_TOKENS)
    assert sorted(contract.SUBJECT_TOKEN_RANK.values()) == list(range(len(contract.SUBJECT_TOKENS)))


def test_the_three_subject_forms_are_mutually_orderable() -> None:
    assert (
        contract.SUBJECT_FORM_OBJECT
        < contract.SUBJECT_FORM_PATH
        < contract.SUBJECT_FORM_DEPENDENCY
    )


# ---------------------------------------------------------------------------
# 9.3.4  the DTO-required / DTO-optional split, asserted EXACTLY as declared
# ---------------------------------------------------------------------------

_VERSION_DTO_REQUIRED = {"object_version", "effective_from", "active_flag", "payload"}
_VERSION_DTO_OPTIONAL = {
    "declared_effective_to",
    "corrects_object_version",
    "publication_reference_type",
    "publication_reference_id",
    "published_at",
}
_RETRACTION_DTO_REQUIRED = {"retraction_id", "object_version"}
_RETRACTION_DTO_OPTIONAL = {
    "retracted_at",
    "publication_reference_type",
    "publication_reference_id",
}
_MATERIAL_DTO_REQUIRED = {
    "object_family",
    "object_id",
    "versions",
    "retraction_assertions",
    "completeness",
}


def _field_names(cls: type) -> set[str]:
    return {field.name for field in dataclasses.fields(cls)}


def test_the_material_dto_carries_exactly_the_declared_fields() -> None:
    assert _field_names(LineageMaterial) == _MATERIAL_DTO_REQUIRED
    assert _field_names(PublishedObjectVersion) == _VERSION_DTO_REQUIRED | _VERSION_DTO_OPTIONAL
    assert (
        _field_names(RetractionAssertion) == _RETRACTION_DTO_REQUIRED | _RETRACTION_DTO_OPTIONAL
    )


def test_every_dto_optional_field_is_constructible_as_absent() -> None:
    """The property that makes every class B1 fixture constructible.

    A DTO that rejected any of these - or that defaulted a missing provenance
    type to BOOTSTRAP_PROVENANCE - would make the kernel rule it already owns
    permanently unreachable and untestable (9.3.4, attack surface 17f).
    """

    published = PublishedObjectVersion(
        object_version="0001",
        effective_from=datetime(2026, 1, 1),
        active_flag=True,
        payload=object(),
        declared_effective_to=None,
        corrects_object_version=None,
        publication_reference_type=None,
        publication_reference_id=None,
        published_at=None,
    )
    for name in _VERSION_DTO_OPTIONAL:
        assert getattr(published, name) is None, name

    assertion = RetractionAssertion(
        retraction_id="r1",
        object_version="0001",
        retracted_at=None,
        publication_reference_type=None,
        publication_reference_id=None,
    )
    for name in _RETRACTION_DTO_OPTIONAL:
        assert getattr(assertion, name) is None, name


def test_the_assignment_payload_does_not_enforce_the_person_position_xor() -> None:
    """Both targets and neither target must BOTH be constructible.

    The XOR is a SEMANTIC rule the kernel enforces at S7 (invariant I-4). A
    convenience validator here would make B1-02 and B1-03 unconstructible and
    is a blocking defect.
    """

    both = BusinessAuthorityAssignmentPayload(person_id="p", position_id="pos")
    neither = BusinessAuthorityAssignmentPayload(person_id=None, position_id=None)
    assert (both.person_id, both.position_id) == ("p", "pos")
    assert (neither.person_id, neither.position_id) == (None, None)


def test_the_version_dto_does_not_validate_the_declared_interval() -> None:
    """end < start and the empty end == start must both be constructible.

    9.3.4 states this explicitly: the DTO must NOT validate the
    declared_effective_to / effective_from relationship, or fixtures B1-04 and
    B1-05 become unconstructible.
    """

    start = datetime(2026, 6, 1)
    earlier = datetime(2026, 1, 1)
    for end in (earlier, start):
        published = PublishedObjectVersion(
            object_version="0001", effective_from=start, active_flag=True, payload=object(),
            declared_effective_to=end,
        )
        assert published.declared_effective_to == end


def test_publication_reference_type_is_an_open_value_not_a_closed_enum() -> None:
    """BOTH an ABSENT type and an UNKNOWN type must be constructible (9.3.4).

    A kernel that validates only membership in the two defined values passes
    the unknown-value fixture while failing the absent-type one. That is
    precisely the F-10.1 gap, so the DTO must carry the field OPEN.
    """

    unknown = PublishedObjectVersion(
        object_version="0001",
        effective_from=datetime(2026, 1, 1),
        active_flag=True,
        payload=object(),
        publication_reference_type="SOMETHING_ELSE_ENTIRELY",
    )
    assert unknown.publication_reference_type == "SOMETHING_ELSE_ENTIRELY"


def test_published_versions_are_immutable_including_active_flag() -> None:
    """Invariant I-2, in code: `frozen=True`.

    No path mutates a published version's content after publication, for any
    reason, including correction and including its `active_flag` (I-8).
    """

    published = PublishedObjectVersion(
        object_version="0001",
        effective_from=datetime(2026, 1, 1),
        active_flag=True,
        payload=object(),
    )
    for name, value in (
        ("active_flag", False),
        ("effective_from", datetime(2027, 1, 1)),
        ("object_version", "0002"),
        ("published_at", datetime(2027, 1, 1)),
    ):
        with pytest.raises(dataclasses.FrozenInstanceError):
            setattr(published, name, value)


def test_the_authenticated_actor_carries_no_person_identity_and_no_role_codes() -> None:
    """The actor is never trusted to state who it is canonically (7.1, 9.1).

    There is also deliberately no role_codes field: a Business Authority is
    never derived from an Application/Login Role, including ADMIN, so the
    kernel has no legitimate use for one (section 6).
    """

    fields = _field_names(AuthenticatedActor)
    assert fields == {"actor_user_public_id"}
    assert "person_id" not in fields
    assert "role_codes" not in fields


def test_an_allow_carries_no_result_level_reason_and_none_was_invented() -> None:
    """Section 14 defines result-level reasons for DENY + RESOLVED (14.2) and
    for DENY + FAIL_CLOSED (14.3), and defines NONE for a grant.

    The empty value on an ALLOW is a deliberate absence: the reason a grant
    happened is the qualifying paths themselves, which 16.2 requires in full.
    Inventing an "ALLOWED" reason code to fill the field would add a value the
    taxonomy does not define.
    """

    from tests.fixtures.pf_1a_e2_a_scenarios import run, world

    granted = run(world())
    assert granted.outcome == contract.OUTCOME_ALLOW
    assert granted.result_level_reason == ""
    assert granted.qualifying_paths

    assert "ALLOWED" not in contract.ALL_REASON_CODES
    assert "GRANTED" not in contract.ALL_REASON_CODES
