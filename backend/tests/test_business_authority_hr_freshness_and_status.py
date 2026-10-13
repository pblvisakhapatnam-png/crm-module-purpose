"""PF-1A-E2-A corrections C1-2 and C1-4: every HR state actually relied upon.

C1-2 — STALENESS MUST APPLY TO EVERY HR STATE USED.
    The supplied threshold was enforced for actor/person and employment state
    but not for Position, Incumbency or Organisation Unit ancestry. The
    controller reproduced ALLOW + RESOLVED with fresh actor/employment state and
    STALE Position/Incumbency, and separately with stale Organisation Unit
    ancestry, under the same supplied threshold.

C1-4 — AN UNKNOWN / ILL-FORMED LOOKUP STATUS MUST NEVER FAIL OPEN.
    The controller reproduced `HrLookup(status="BOGUS", value=<fresh ACTIVE
    employment>)` proceeding to ALLOW + RESOLVED. The HR contract defines a
    CLOSED lookup-status vocabulary; a response outside it is not authoritative
    state and must never be trusted merely because a value is also attached.

Both corrections share one rule, and these tests exist to prove it holds at
EVERY seam rather than at the two that happened to be checked first: every
canonical HR/reference response actually relied upon is validated and
freshness-checked against the SAME supplied threshold and the SAME
authoritative `as_of`.
"""

from __future__ import annotations

from datetime import timedelta

from app.modules.authorization.business_authority.contract import (
    EMPLOYMENT_STATE_MISSING,
    HR_REFERENCE_STALE,
    HR_REFERENCE_UNAVAILABLE,
    INCUMBENCY_MISSING,
    ORG_HIERARCHY_UNRESOLVABLE,
    ORG_UNIT_STATE_MISSING,
    OUTCOME_ALLOW,
    OUTCOME_DENY,
    POSITION_STATE_MISSING,
    SCOPE_ANCESTRY,
    STATUS_FAIL_CLOSED,
)
from app.modules.authorization.business_authority.domain import BusinessContext
from app.modules.authorization.business_authority.scope import SCOPE_KIND_ORG_UNIT
from tests.fixtures.pf_1a_e2_a_reference_providers import (
    ORG_BRANCH,
    ORG_DIVISION,
    ORG_ROOT,
    POSITION_ID,
    T2,
    ReferenceActorPersonProvider,
    ReferenceHrProvider,
)
from tests.fixtures.pf_1a_e2_a_scenarios import (
    assignment_material,
    rule_material,
    run,
    world,
)

# ONE supplied threshold, used by every test in this module. It is SUPPLIED,
# never defaulted: the kernel invents no staleness value of its own.
THRESHOLD_SECONDS = 3600

FRESH = T2
JUST_INSIDE = T2 - timedelta(seconds=THRESHOLD_SECONDS - 1)
EXACTLY_AT_THRESHOLD = T2 - timedelta(seconds=THRESHOLD_SECONDS)
STALE = T2 - timedelta(seconds=THRESHOLD_SECONDS + 1)

BOGUS_STATUS = "BOGUS"


def _position_world():
    return world(assignment=assignment_material(person_id=None, position_id=POSITION_ID))


def _ancestry_world():
    return world(rule=rule_material(scope_type=SCOPE_ANCESTRY, scope_id=ORG_ROOT))


def _ancestry_context() -> BusinessContext:
    # ORG_BRANCH -> ORG_DIVISION -> ORG_ROOT, so the traversal reads the FIRST
    # hop (ORG_BRANCH) and then a DEEPER hop (ORG_DIVISION).
    return BusinessContext(scope_type=SCOPE_KIND_ORG_UNIT, scope_id=ORG_BRANCH)


def _fresh_actor():
    return ReferenceActorPersonProvider(snapshot_at=FRESH)


def _resolve(materials, hr_port, *, business_context=None, threshold=THRESHOLD_SECONDS):
    return run(
        materials,
        as_of=T2,
        business_context=business_context,
        actor_person_port=_fresh_actor(),
        hr_reference_port=hr_port,
        hr_staleness_threshold_seconds=threshold,
    )


# ===========================================================================
# C1-2  STALE POSITION AND STALE INCUMBENCY, with everything else fresh
# ===========================================================================


def test_a_stale_position_fails_closed_even_when_actor_and_employment_are_fresh() -> None:
    """The exact controller reproduction: fresh actor, fresh employment, STALE
    Position - which previously resolved to ALLOW."""

    stale_position = ReferenceHrProvider(snapshot_at=FRESH, position_snapshot_at=STALE)
    result = _resolve(_position_world(), stale_position)

    assert result.outcome == OUTCOME_DENY
    assert result.resolution_status == STATUS_FAIL_CLOSED
    assert result.result_level_reason == HR_REFERENCE_STALE
    # Stale state is NOT reported as absent state.
    assert result.result_level_reason != POSITION_STATE_MISSING


def test_a_stale_incumbency_fails_closed_even_when_the_position_is_fresh() -> None:
    stale_incumbency = ReferenceHrProvider(snapshot_at=FRESH, incumbency_snapshot_at=STALE)
    result = _resolve(_position_world(), stale_incumbency)

    assert result.resolution_status == STATUS_FAIL_CLOSED
    assert result.result_level_reason == HR_REFERENCE_STALE
    assert result.result_level_reason != INCUMBENCY_MISSING


def test_a_position_path_with_every_hr_state_fresh_still_grants() -> None:
    """The correction must deny the STALE case without breaking the fresh one.

    Without this control, a fix that simply rejected every position path would
    pass both tests above.
    """

    result = _resolve(_position_world(), ReferenceHrProvider(snapshot_at=FRESH))
    assert result.outcome == OUTCOME_ALLOW


# ===========================================================================
# C1-2  STALE ORGANISATION UNIT ANCESTRY, at the first hop and a deeper hop
# ===========================================================================


def test_a_stale_first_organisation_unit_hop_fails_closed() -> None:
    stale_first = ReferenceHrProvider(
        snapshot_at=FRESH, org_unit_snapshots={ORG_BRANCH: STALE}
    )
    result = _resolve(_ancestry_world(), stale_first, business_context=_ancestry_context())

    assert result.resolution_status == STATUS_FAIL_CLOSED
    assert result.result_level_reason == HR_REFERENCE_STALE
    # A stale hop is not an unresolvable hierarchy and not a missing unit.
    assert result.result_level_reason != ORG_HIERARCHY_UNRESOLVABLE
    assert result.result_level_reason != ORG_UNIT_STATE_MISSING


def test_a_stale_deeper_organisation_unit_hop_fails_closed() -> None:
    """The first hop is fresh and the SECOND is stale, so a check applied only
    to the entry hop would not catch it."""

    stale_deeper = ReferenceHrProvider(
        snapshot_at=FRESH,
        org_unit_snapshots={ORG_BRANCH: FRESH, ORG_DIVISION: STALE},
    )
    result = _resolve(_ancestry_world(), stale_deeper, business_context=_ancestry_context())

    assert result.resolution_status == STATUS_FAIL_CLOSED
    assert result.result_level_reason == HR_REFERENCE_STALE


def test_an_ancestry_path_with_every_hop_fresh_still_grants() -> None:
    result = _resolve(
        _ancestry_world(),
        ReferenceHrProvider(snapshot_at=FRESH),
        business_context=_ancestry_context(),
    )
    assert result.outcome == OUTCOME_ALLOW


# ===========================================================================
# C1-2  THE THRESHOLD BOUNDARY, at every seam
# ===========================================================================


def test_a_snapshot_exactly_at_the_threshold_is_not_stale() -> None:
    """The comparison is strictly greater-than, so an age of exactly the
    supplied threshold is still usable. Asserted at every seam, because an
    off-by-one applied at one seam and not another is precisely the class of
    defect this correction closes.
    """

    at_boundary = ReferenceHrProvider(
        snapshot_at=EXACTLY_AT_THRESHOLD,
        position_snapshot_at=EXACTLY_AT_THRESHOLD,
        incumbency_snapshot_at=EXACTLY_AT_THRESHOLD,
        org_unit_snapshots={
            ORG_BRANCH: EXACTLY_AT_THRESHOLD,
            ORG_DIVISION: EXACTLY_AT_THRESHOLD,
        },
    )
    boundary_actor = ReferenceActorPersonProvider(snapshot_at=EXACTLY_AT_THRESHOLD)

    result = run(
        _position_world(),
        as_of=T2,
        actor_person_port=boundary_actor,
        hr_reference_port=at_boundary,
        hr_staleness_threshold_seconds=THRESHOLD_SECONDS,
    )
    assert result.outcome == OUTCOME_ALLOW

    ancestry = run(
        _ancestry_world(),
        as_of=T2,
        business_context=_ancestry_context(),
        actor_person_port=boundary_actor,
        hr_reference_port=at_boundary,
        hr_staleness_threshold_seconds=THRESHOLD_SECONDS,
    )
    assert ancestry.outcome == OUTCOME_ALLOW


def test_a_snapshot_immediately_inside_the_threshold_is_fresh() -> None:
    just_inside = ReferenceHrProvider(
        snapshot_at=JUST_INSIDE,
        position_snapshot_at=JUST_INSIDE,
        incumbency_snapshot_at=JUST_INSIDE,
        org_unit_snapshots={ORG_BRANCH: JUST_INSIDE, ORG_DIVISION: JUST_INSIDE},
    )
    result = run(
        _position_world(),
        as_of=T2,
        actor_person_port=ReferenceActorPersonProvider(snapshot_at=JUST_INSIDE),
        hr_reference_port=just_inside,
        hr_staleness_threshold_seconds=THRESHOLD_SECONDS,
    )
    assert result.outcome == OUTCOME_ALLOW


def test_one_second_past_the_threshold_is_stale_at_every_seam() -> None:
    """The mirror of the boundary test: one tick over, and each seam fails
    closed on its own."""

    seams = {
        "actor": (ReferenceActorPersonProvider(snapshot_at=STALE), ReferenceHrProvider(snapshot_at=FRESH)),
        "employment": (_fresh_actor(), ReferenceHrProvider(snapshot_at=STALE)),
        "position": (
            _fresh_actor(),
            ReferenceHrProvider(snapshot_at=FRESH, position_snapshot_at=STALE),
        ),
        "incumbency": (
            _fresh_actor(),
            ReferenceHrProvider(snapshot_at=FRESH, incumbency_snapshot_at=STALE),
        ),
    }
    for label, (actor_port, hr_port) in seams.items():
        result = run(
            _position_world(),
            as_of=T2,
            actor_person_port=actor_port,
            hr_reference_port=hr_port,
            hr_staleness_threshold_seconds=THRESHOLD_SECONDS,
        )
        assert result.resolution_status == STATUS_FAIL_CLOSED, label
        assert result.result_level_reason == HR_REFERENCE_STALE, label


def test_no_default_threshold_is_invented_at_any_seam() -> None:
    """WITH NO THRESHOLD SUPPLIED the kernel applies none, at every seam.

    The identical deeply-stale state resolves, which is what proves no default
    value was quietly assumed anywhere (section 7, section 23).
    """

    deeply_stale = ReferenceHrProvider(
        snapshot_at=STALE,
        position_snapshot_at=STALE,
        incumbency_snapshot_at=STALE,
        org_unit_snapshots={ORG_BRANCH: STALE, ORG_DIVISION: STALE},
    )
    stale_actor = ReferenceActorPersonProvider(snapshot_at=STALE)

    position = run(
        _position_world(),
        as_of=T2,
        actor_person_port=stale_actor,
        hr_reference_port=deeply_stale,
    )
    assert position.outcome == OUTCOME_ALLOW

    ancestry = run(
        _ancestry_world(),
        as_of=T2,
        business_context=_ancestry_context(),
        actor_person_port=stale_actor,
        hr_reference_port=deeply_stale,
    )
    assert ancestry.outcome == OUTCOME_ALLOW


def test_every_seam_is_evaluated_against_the_one_authoritative_as_of() -> None:
    """The staleness check must not introduce a second clock: every HR call is
    made at, and compared against, the SAME single instant (11.1)."""

    actor_port = _fresh_actor()
    hr_port = ReferenceHrProvider(snapshot_at=FRESH)
    result = run(
        _ancestry_world(),
        as_of=T2,
        business_context=_ancestry_context(),
        actor_person_port=actor_port,
        hr_reference_port=hr_port,
        hr_staleness_threshold_seconds=THRESHOLD_SECONDS,
    )

    assert result.outcome == OUTCOME_ALLOW
    assert set(actor_port.observed_as_of) == {T2}
    assert set(hr_port.observed_as_of) == {T2}
    assert result.as_of == T2


# ===========================================================================
# C1-4  A NON-CONTRACT LOOKUP STATUS, WITH A PLAUSIBLE VALUE ATTACHED
# ===========================================================================


def test_the_bogus_status_fixture_really_does_attach_a_plausible_fresh_value() -> None:
    """The premise of every C1-4 test below, asserted once.

    If the fixture returned no value, the tests would pass for the wrong
    reason: they must prove the STATUS is what is rejected, not the absence of
    a value.
    """

    provider = ReferenceHrProvider(snapshot_at=FRESH, employment_status_override=BOGUS_STATUS)
    lookup = provider.get_employment_state("person-0001", T2)

    assert lookup.status == BOGUS_STATUS
    assert lookup.value is not None
    assert lookup.value.employment_status == "ACTIVE"
    assert lookup.value.canonical_snapshot_at == FRESH


def test_an_unknown_actor_person_status_fails_closed() -> None:
    result = run(
        world(),
        as_of=T2,
        actor_person_port=ReferenceActorPersonProvider(
            snapshot_at=FRESH, status_override=BOGUS_STATUS
        ),
        hr_reference_port=ReferenceHrProvider(snapshot_at=FRESH),
        hr_staleness_threshold_seconds=THRESHOLD_SECONDS,
    )
    assert result.outcome == OUTCOME_DENY
    assert result.resolution_status == STATUS_FAIL_CLOSED
    assert result.result_level_reason == HR_REFERENCE_UNAVAILABLE


def test_an_unknown_employment_status_fails_closed() -> None:
    """The exact controller reproduction, which previously reached ALLOW."""

    result = _resolve(
        world(),
        ReferenceHrProvider(snapshot_at=FRESH, employment_status_override=BOGUS_STATUS),
    )
    assert result.outcome == OUTCOME_DENY
    assert result.resolution_status == STATUS_FAIL_CLOSED
    assert result.result_level_reason == HR_REFERENCE_UNAVAILABLE
    # NEVER silently mapped onto a known state.
    assert result.result_level_reason != EMPLOYMENT_STATE_MISSING


def test_an_unknown_position_status_fails_closed() -> None:
    result = _resolve(
        _position_world(),
        ReferenceHrProvider(snapshot_at=FRESH, position_status_override=BOGUS_STATUS),
    )
    assert result.resolution_status == STATUS_FAIL_CLOSED
    assert result.result_level_reason == HR_REFERENCE_UNAVAILABLE
    assert result.result_level_reason != POSITION_STATE_MISSING


def test_an_unknown_incumbency_status_fails_closed() -> None:
    result = _resolve(
        _position_world(),
        ReferenceHrProvider(snapshot_at=FRESH, incumbency_status_override=BOGUS_STATUS),
    )
    assert result.resolution_status == STATUS_FAIL_CLOSED
    assert result.result_level_reason == HR_REFERENCE_UNAVAILABLE
    assert result.result_level_reason != INCUMBENCY_MISSING


def test_an_unknown_organisation_unit_status_fails_closed() -> None:
    result = _resolve(
        _ancestry_world(),
        ReferenceHrProvider(snapshot_at=FRESH, org_unit_status_override=BOGUS_STATUS),
        business_context=_ancestry_context(),
    )
    assert result.resolution_status == STATUS_FAIL_CLOSED
    assert result.result_level_reason == HR_REFERENCE_UNAVAILABLE
    assert result.result_level_reason != ORG_UNIT_STATE_MISSING
    assert result.result_level_reason != ORG_HIERARCHY_UNRESOLVABLE


def test_an_unknown_status_fails_closed_regardless_of_the_value_attached() -> None:
    """Several differently-shaped non-contract statuses, all rejected.

    A single hard-coded "BOGUS" comparison would pass the tests above; this
    asserts the check is membership in the CLOSED vocabulary rather than a
    denylist.
    """

    for status in ("BOGUS", "ok", "Ok", "PRESENT", "FOUND", "", "OK ", "UNKNOWN"):
        result = _resolve(
            world(), ReferenceHrProvider(snapshot_at=FRESH, employment_status_override=status)
        )
        assert result.resolution_status == STATUS_FAIL_CLOSED, status
        assert result.result_level_reason == HR_REFERENCE_UNAVAILABLE, status


def test_the_four_contract_failure_statuses_keep_their_own_specific_codes() -> None:
    """C1-4 must not have flattened the closed vocabulary into one code.

    MISSING and AMBIGUOUS remain distinguishable per seam (14.4 distinction 1);
    only a status OUTSIDE the vocabulary takes the provider-failure code.
    """

    specific = {
        "MISSING": EMPLOYMENT_STATE_MISSING,
        "AMBIGUOUS": "EMPLOYMENT_STATE_AMBIGUOUS",
        "UNAVAILABLE": HR_REFERENCE_UNAVAILABLE,
        "STALE": HR_REFERENCE_STALE,
    }
    for status, expected in specific.items():
        result = _resolve(world(), ReferenceHrProvider(employment_result=status))
        assert result.result_level_reason == expected, status
