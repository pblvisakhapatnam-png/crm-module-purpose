"""PF-1A-E2-A section 18: RAW DISCOVERY AND RETRACTION, and RECORDED TIME.

Covers valid-shape scenarios V-08 and V-09, class A fixture A-17, and
non-store scenarios NS-PT-01, NS-PR-03, NS-RS-04 and NS-EV-07.

THE DISCOVERY BOUNDARY (F-07). E2-A owns whether a lineage fact is valid,
retracted, superseded, effective, active or otherwise relevant AFTER
validation. A provider must not decide any of those questions in order to
answer a discovery call, and the kernel must not re-apply at its own layer the
prefiltering the provider is forbidden to do.

THE HIGHEST-VALUE REGRESSION TEST IN THIS PACKAGE is A-17: a MALFORMED
retraction must not be able to make the only requested-code-bearing or only
reference-bearing version invisible, so that its own defect is reported as an
absent candidate.
"""

from __future__ import annotations

import pytest

from app.modules.authorization.business_authority.contract import (
    AUTHORITY_CODE_NOT_CONFIGURED,
    AUTHORITY_CONFIGURATION_UNAVAILABLE,
    AUTHORITY_LINEAGE_CONTRADICTORY,
    BUSINESS_AUTHORITY,
    BUSINESS_AUTHORITY_ASSIGNMENT,
    BUSINESS_AUTHORITY_RULE,
    NO_CANDIDATE_ASSIGNMENT,
    OUTCOME_ALLOW,
    OUTCOME_DENY,
    PUBLICATION_PROVENANCE_INVALID,
    STATUS_FAIL_CLOSED,
)
from tests.fixtures.pf_1a_e2_a_corpus import covers
from tests.fixtures.pf_1a_e2_a_reference_providers import (
    AUTHORITY_CODE,
    RECORDED_AT,
    T0,
    T1,
    T2,
    T3,
    JudgingAuthorityConfigurationProvider,
    ReferenceAuthorityConfigurationProvider,
    assignment_payload,
    authority_payload,
    retraction,
    rule_payload,
    version,
)
from tests.fixtures.pf_1a_e2_a_scenarios import (
    ASSIGNMENT_ID,
    AUTHORITY_ID,
    ROLE_ID,
    RULE_ID,
    V1,
    V2,
    assignment_material,
    authority_material,
    rule_material,
    run,
    world,
)

OTHER_CODE = "SOME_OTHER_AUTHORITY"


# ===========================================================================
# V-08  raw discovery over VALID retraction facts
# ===========================================================================


@covers("V-08")
def test_an_object_whose_only_code_bearing_version_is_retracted_is_still_discovered() -> None:
    """The kernel - not the provider - decides the outcome.

    The object's complete lineage must REACH the kernel, which is asserted
    directly through the provider's own record of the `get_lineage` calls it
    was asked to serve.
    """

    authority = authority_material(
        versions=(
            version(V1, T0, payload=authority_payload(AUTHORITY_CODE)),
            version(V2, T1, payload=authority_payload(OTHER_CODE)),
        ),
        retractions=(retraction("r1", V1),),
    )
    provider = ReferenceAuthorityConfigurationProvider(world(authority=authority))

    result = run(None, authority_configuration_port=provider, as_of=T2)

    assert (BUSINESS_AUTHORITY, AUTHORITY_ID) in provider.observed_lineage_calls
    # The kernel then decides: the surviving effective version carries a
    # different code, so the requested one is not established.
    assert result.result_level_reason == AUTHORITY_CODE_NOT_CONFIGURED


@covers("V-08")
def test_an_object_whose_only_reference_bearing_version_is_retracted_is_still_discovered() -> None:
    """The same rule, for graph expansion rather than requested-code discovery."""

    rule = rule_material(
        versions=(
            version(V1, T0, payload=rule_payload(authority_id=AUTHORITY_ID)),
            version(V2, T1, payload=rule_payload(authority_id="some-other-authority")),
        ),
        retractions=(retraction("r1", V1),),
    )
    provider = ReferenceAuthorityConfigurationProvider(world(rule=rule))

    run(None, authority_configuration_port=provider, as_of=T2)
    assert (BUSINESS_AUTHORITY_RULE, RULE_ID) in provider.observed_lineage_calls


@covers("V-08")
def test_discovery_applies_no_semantic_predicate_of_any_kind() -> None:
    """One case per EXCLUDED predicate (section 18 RAW DISCOVERY).

    Discovery may narrow only by object family, stable identity,
    `authority_code` and stable reference. It applies no active_flag,
    effective-interval, scope, parameter, evaluator-outcome, provenance or
    "latest version" predicate.
    """

    excluded_predicate_shapes = {
        "retracted": authority_material(
            versions=(version(V1, T0, payload=authority_payload()),),
            retractions=(retraction("r1", V1),),
        ),
        "inactive": authority_material(
            versions=(version(V1, T0, payload=authority_payload(), active_flag=False),)
        ),
        "not yet effective": authority_material(
            versions=(version(V1, T3, payload=authority_payload()),)
        ),
        "already ended": authority_material(
            versions=(version(V1, T0, payload=authority_payload(), declared_effective_to=T1),)
        ),
        "superseded / not the latest": authority_material(
            versions=(
                version(V1, T0, payload=authority_payload()),
                version(V2, T1, payload=authority_payload(OTHER_CODE)),
            )
        ),
        "invalid provenance": authority_material(
            versions=(version(V1, T0, payload=authority_payload(), published_at=None),)
        ),
    }

    for label, authority in excluded_predicate_shapes.items():
        provider = ReferenceAuthorityConfigurationProvider([authority])
        discovered = provider.find_business_authority_ids_by_code(AUTHORITY_CODE)
        assert list(discovered) == [AUTHORITY_ID], f"discovery excluded a candidate that is {label}"


# ===========================================================================
# A-17  MALFORMED RETRACTION CANNOT HIDE A VERSION
# ===========================================================================


def _malformed_retraction_shapes(code: str):
    """A dangling retraction, a duplicated retraction, and one with impossible
    provenance - each targeting the ONLY code-bearing version."""

    earlier = RECORDED_AT.replace(hour=11)
    return {
        "dangling": (
            (version(V1, T0, payload=authority_payload(code)),),
            (retraction("r1", "9999"),),
            AUTHORITY_LINEAGE_CONTRADICTORY,
        ),
        "duplicated": (
            (version(V1, T0, payload=authority_payload(code)),),
            (retraction("r1", V1), retraction("r2", V1)),
            AUTHORITY_LINEAGE_CONTRADICTORY,
        ),
        "impossible provenance": (
            (version(V1, T0, payload=authority_payload(code)),),
            (retraction("r1", V1, retracted_at=earlier),),
            PUBLICATION_PROVENANCE_INVALID,
        ),
    }


@covers("A-17")
def test_a_malformed_retraction_cannot_hide_the_only_code_bearing_version() -> None:
    for label, (versions, retractions, expected) in _malformed_retraction_shapes(
        AUTHORITY_CODE
    ).items():
        authority = authority_material(versions=versions, retractions=retractions)
        provider = ReferenceAuthorityConfigurationProvider(world(authority=authority))
        result = run(None, authority_configuration_port=provider, as_of=T2)

        assert result.resolution_status == STATUS_FAIL_CLOSED, label
        # THE DEFECT'S OWN REASON CODE - explicitly NOT an absent candidate.
        assert result.result_level_reason == expected, label
        assert result.result_level_reason != AUTHORITY_CODE_NOT_CONFIGURED, label
        assert result.result_level_reason != NO_CANDIDATE_ASSIGNMENT, label
        # The object was discovered and its lineage did reach the kernel.
        assert (BUSINESS_AUTHORITY, AUTHORITY_ID) in provider.observed_lineage_calls, label


@covers("A-17")
def test_a_malformed_retraction_cannot_hide_the_only_reference_bearing_version() -> None:
    """The companion case, over an Assignment discovered by stable reference."""

    assignment = assignment_material(
        versions=(version(V1, T0, payload=assignment_payload(role_id=ROLE_ID)),),
        retractions=(retraction("r1", V1), retraction("r2", V1)),
    )
    provider = ReferenceAuthorityConfigurationProvider(world(assignment=assignment))
    result = run(None, authority_configuration_port=provider, as_of=T2)

    assert result.resolution_status == STATUS_FAIL_CLOSED
    assert result.result_level_reason == AUTHORITY_LINEAGE_CONTRADICTORY
    assert result.result_level_reason != NO_CANDIDATE_ASSIGNMENT
    assert (BUSINESS_AUTHORITY_ASSIGNMENT, ASSIGNMENT_ID) in provider.observed_lineage_calls


# ===========================================================================
# NS-PR-03  provider FACT-FIDELITY
# ===========================================================================


def _assert_supplies_facts_not_judgements(provider, stored) -> None:
    """The conformance assertion a JUDGING provider must fail.

    Locating a fact is permitted; judging a fact is not (9.5). A conforming
    provider returns every stored version and every stored retraction
    assertion, and discovers an object whose only code-bearing version is
    retracted.
    """

    for material in stored:
        returned = provider.get_lineage(material.object_family, material.object_id)
        assert len(returned.versions) == len(material.versions), (
            "the provider dropped versions from lineage material"
        )
        assert len(returned.retraction_assertions) == len(material.retraction_assertions), (
            "the provider dropped retraction assertions, so the kernel could never tell a "
            "correct retraction from a malformed one"
        )
        assert {v.object_version for v in returned.versions} == {
            v.object_version for v in material.versions
        }


@covers("NS-PR-03")
def test_a_conforming_reference_provider_supplies_facts_not_judgements() -> None:
    stored = world(
        authority=authority_material(
            versions=(
                version(V1, T0, payload=authority_payload()),
                version(V2, T1, payload=authority_payload(), active_flag=False),
            ),
            retractions=(retraction("r1", V1),),
        )
    )
    _assert_supplies_facts_not_judgements(ReferenceAuthorityConfigurationProvider(stored), stored)


@covers("NS-PR-03")
def test_a_judging_provider_is_rejected_by_the_conformance_assertion() -> None:
    """A provider that prefilters to "the effective row" must FAIL conformance.

    Without this negative control the conformance assertion above could pass
    vacuously against any provider at all.
    """

    stored = world(
        authority=authority_material(
            versions=(
                version(V1, T0, payload=authority_payload()),
                version(V2, T1, payload=authority_payload(), active_flag=False),
            ),
            retractions=(retraction("r1", V1),),
        )
    )
    judging = JudgingAuthorityConfigurationProvider(stored)
    with pytest.raises(AssertionError):
        _assert_supplies_facts_not_judgements(judging, stored)


@covers("NS-PR-03")
def test_the_kernel_fails_closed_on_every_defect_a_judging_provider_would_hide() -> None:
    """Given RAW material containing each defect, the kernel detects it.

    Duplicate effective versions (a duplicate temporal start), an explicit
    overlap, a dangling retraction, an unretracted correction target and
    invalid provenance - the exact five shapes section 18 names.
    """

    shapes = {
        "duplicate start": (
            (
                version(V1, T0, payload=authority_payload()),
                version(V2, T0, payload=authority_payload()),
            ),
            (),
            AUTHORITY_LINEAGE_CONTRADICTORY,
        ),
        "explicit overlap": (
            (
                version(V1, T0, payload=authority_payload(), declared_effective_to=T3),
                version(V2, T2, payload=authority_payload()),
            ),
            (),
            AUTHORITY_LINEAGE_CONTRADICTORY,
        ),
        "dangling retraction": (
            (version(V1, T0, payload=authority_payload()),),
            (retraction("r1", "9999"),),
            AUTHORITY_LINEAGE_CONTRADICTORY,
        ),
        "unretracted correction target": (
            (
                version(V1, T0, payload=authority_payload()),
                version(V2, T2, payload=authority_payload(), corrects_object_version=V1),
            ),
            (),
            AUTHORITY_LINEAGE_CONTRADICTORY,
        ),
        "invalid provenance": (
            (version(V1, T0, payload=authority_payload(), publication_reference_id=None),),
            (),
            PUBLICATION_PROVENANCE_INVALID,
        ),
    }

    for label, (versions, retractions, expected) in shapes.items():
        authority = authority_material(versions=versions, retractions=retractions)
        result = run(world(authority=authority), as_of=T2 if label != "duplicate start" else T1)
        assert result.resolution_status == STATUS_FAIL_CLOSED, label
        assert result.result_level_reason == expected, label


# ===========================================================================
# NS-PT-01  the PORT's read/transport behaviour
# ===========================================================================


@covers("NS-PT-01")
def test_a_raised_provider_error_fails_closed_and_is_never_read_as_not_found() -> None:
    provider = ReferenceAuthorityConfigurationProvider(world()).with_failure(
        raise_on=frozenset({(BUSINESS_AUTHORITY, AUTHORITY_ID)})
    )
    result = run(None, authority_configuration_port=provider)

    assert result.outcome == OUTCOME_DENY
    assert result.resolution_status == STATUS_FAIL_CLOSED
    assert result.result_level_reason == AUTHORITY_CONFIGURATION_UNAVAILABLE
    # NEVER degraded to "no candidates found" and NEVER to DENY + RESOLVED.
    assert result.result_level_reason != AUTHORITY_CODE_NOT_CONFIGURED


@covers("NS-PT-01")
def test_a_failed_discovery_call_fails_closed() -> None:
    provider = ReferenceAuthorityConfigurationProvider(world()).with_failure(
        raise_on_discovery=True
    )
    result = run(None, authority_configuration_port=provider)
    assert result.resolution_status == STATUS_FAIL_CLOSED
    assert result.result_level_reason == AUTHORITY_CONFIGURATION_UNAVAILABLE


@covers("NS-PT-01")
def test_completeness_unavailable_fails_closed() -> None:
    """A provider that cannot return the complete set MUST say UNAVAILABLE."""

    provider = ReferenceAuthorityConfigurationProvider(world()).with_failure(
        unavailable_on=frozenset({(BUSINESS_AUTHORITY, AUTHORITY_ID)})
    )
    result = run(None, authority_configuration_port=provider)
    assert result.resolution_status == STATUS_FAIL_CLOSED
    assert result.result_level_reason == AUTHORITY_CONFIGURATION_UNAVAILABLE


@covers("NS-PT-01")
def test_a_truncated_read_presented_as_complete_is_detectable_and_prohibited() -> None:
    """A truncated list presented as COMPLETE is a blocking defect (9.3.2).

    The kernel cannot detect truncation from the material alone - that is
    precisely why the obligation sits on the PROVIDER. This asserts the
    conformance check catches such a provider, and that the correct behaviour
    (UNAVAILABLE, exercised above) is the one that fails the resolution closed.
    """

    stored = world(
        authority=authority_material(
            versions=(
                version(V1, T0, payload=authority_payload()),
                version(V2, T2, payload=authority_payload()),
            )
        )
    )
    truncating = ReferenceAuthorityConfigurationProvider(stored).with_failure(
        truncate_on=frozenset({(BUSINESS_AUTHORITY, AUTHORITY_ID)})
    )
    with pytest.raises(AssertionError):
        _assert_supplies_facts_not_judgements(truncating, stored)


# ===========================================================================
# NS-RS-04  recorded time is NEVER a lineage filter
# ===========================================================================


@covers("NS-RS-04")
def test_shifting_only_the_recorded_timestamps_changes_nothing() -> None:
    """Keeping them valid under 11.8.3, the outcome, status, reason and path
    set are all unchanged. `published_at` / `retracted_at` are recorded-time
    EVIDENCE and VALIDATION INPUT only - never a second business clock and
    never a filter (acceptance criterion F)."""

    def build(published_at):
        return world(
            authority=authority_material(
                versions=(version(V1, T0, payload=authority_payload(), published_at=published_at),)
            )
        )

    original = run(build(RECORDED_AT), as_of=T2)
    shifted = run(build(RECORDED_AT.replace(year=2027)), as_of=T2)

    assert original.outcome == shifted.outcome == OUTCOME_ALLOW
    assert original.resolution_status == shifted.resolution_status
    assert original.result_level_reason == shifted.result_level_reason
    assert [path.path_sort_key for path in original.qualifying_paths] == [
        path.path_sort_key for path in shifted.qualifying_paths
    ]


# ===========================================================================
# V-09  recorded time versus business-effective time RECONSTRUCTION
# ===========================================================================


@covers("V-09")
def test_a_version_published_after_a_historical_as_of_still_participates_in_it() -> None:
    """A version published TODAY that asserts a business-effective interval
    containing an older as_of DOES participate in reconstructing that instant.

    This is exactly what distinguishes CORRECTED BUSINESS-EFFECTIVE
    RECONSTRUCTION from point-in-time recorded-knowledge replay (11.8.1).
    """

    published_much_later = RECORDED_AT.replace(year=2027)
    authority = authority_material(
        versions=(version(V1, T0, payload=authority_payload(), published_at=published_much_later),)
    )
    result = run(world(authority=authority), as_of=T1)
    assert result.outcome == OUTCOME_ALLOW


@covers("V-09")
def test_a_retraction_recorded_today_removes_its_target_from_an_older_reconstruction() -> None:
    before = run(
        world(
            authority=authority_material(
                versions=(version(V1, T0, payload=authority_payload()),)
            )
        ),
        as_of=T1,
    )
    assert before.outcome == OUTCOME_ALLOW

    retracted_today = RECORDED_AT.replace(year=2027)
    after = run(
        world(
            authority=authority_material(
                versions=(version(V1, T0, payload=authority_payload()),),
                retractions=(retraction("r1", V1, retracted_at=retracted_today),),
            )
        ),
        as_of=T1,
    )
    # Every version retracted with no replacement: the reference is DANGLING.
    assert after.resolution_status == STATUS_FAIL_CLOSED
    assert after.outcome == OUTCOME_DENY


@covers("V-09")
def test_a_valid_later_correction_changes_what_an_old_business_as_of_reconstructs() -> None:
    """Asserted EXPLICITLY, so the behaviour is deliberate rather than accidental."""

    original_only = world(
        authority=authority_material(
            versions=(version(V1, T0, payload=authority_payload(AUTHORITY_CODE)),)
        )
    )
    assert run(original_only, as_of=T1).outcome == OUTCOME_ALLOW

    corrected_later = RECORDED_AT.replace(hour=13)
    after_correction = world(
        authority=authority_material(
            versions=(
                version(V1, T0, payload=authority_payload(AUTHORITY_CODE)),
                version(
                    V2,
                    T0,
                    payload=authority_payload(OTHER_CODE),
                    corrects_object_version=V1,
                    published_at=corrected_later,
                ),
            ),
            retractions=(retraction("r1", V1),),
        )
    )
    # The SAME business as_of now reconstructs a different answer, because the
    # corrected lineage is the best current understanding of what was
    # business-effective then.
    assert run(after_correction, as_of=T1).result_level_reason == AUTHORITY_CODE_NOT_CONFIGURED


# ===========================================================================
# NS-EV-07  evidence durability across later versions, retraction, correction
# ===========================================================================


@covers("NS-EV-07")
def test_cited_versions_stay_byte_identical_after_later_publications() -> None:
    """Evidence cited by a historical decision must remain dereferenceable and
    BYTE-IDENTICAL after later versions, retractions and corrections exist
    (16.5 DURABILITY), while the historical resolver may legitimately
    reconstruct a different answer for the same business as_of (11.8.1).

    Both answers are provable, and they are allowed to differ - that
    difference is exactly the audit signal a correction is supposed to
    produce. Neither of these two facts discharges the other.
    """

    original_version = version(V1, T0, payload=authority_payload(AUTHORITY_CODE))
    before_materials = world(authority=authority_material(versions=(original_version,)))
    provider_before = ReferenceAuthorityConfigurationProvider(before_materials)

    captured = run(None, authority_configuration_port=provider_before, as_of=T1)
    assert captured.outcome == OUTCOME_ALLOW
    cited = captured.qualifying_paths[0].business_authority.ref
    dereferenced_at_decision_time = provider_before.get_published_version(
        cited.object_family, cited.object_id, cited.object_version
    )

    # Publish further versions, a retraction and a valid correction.
    corrected_later = RECORDED_AT.replace(hour=13)
    after_materials = world(
        authority=authority_material(
            versions=(
                original_version,
                version(
                    V2,
                    T0,
                    payload=authority_payload(OTHER_CODE),
                    corrects_object_version=V1,
                    published_at=corrected_later,
                ),
            ),
            retractions=(retraction("r1", V1),),
        )
    )
    provider_after = ReferenceAuthorityConfigurationProvider(after_materials)

    # DEREFERENCE IS ALWAYS AVAILABLE: retraction affects RESOLUTION only.
    dereferenced_afterwards = provider_after.get_published_version(
        cited.object_family, cited.object_id, cited.object_version
    )
    assert dereferenced_afterwards == dereferenced_at_decision_time

    # ... while the reconstruction for the SAME business as_of has changed.
    reconstructed = run(None, authority_configuration_port=provider_after, as_of=T1)
    assert reconstructed.result_level_reason == AUTHORITY_CODE_NOT_CONFIGURED
    # The captured result object itself is unchanged.
    assert captured.outcome == OUTCOME_ALLOW
