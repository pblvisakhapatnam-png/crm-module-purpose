"""PF-1A-E2-A section 18: the PURE-KERNEL INVARIANT seam.

Covers non-store scenarios NS-K-01 (three mandatory executable parts) and
NS-K-02.

NS-K-01 replaces the WITHDRAWN authority-store fixture A-03. The residual
">1 effective version at one as_of" clause of 11.6 is proved UNREACHABLE from
any provider input by the single-effective-version theorem of 11.4a, so there
is no state to seed on any provider and no parity to owe. The clause itself is
NOT deleted: it is retained as a DEFENSIVE KERNEL INVARIANT, and an
implementation that removes it as "dead code" has removed the one guard that
would catch its own regression.
"""

from __future__ import annotations

import itertools

from app.modules.authorization.business_authority import kernel, lineage
from app.modules.authorization.business_authority.contract import (
    AUTHORITY_VERSION_AMBIGUOUS,
    INTERNAL_CONTRACT_VIOLATION,
    OUTCOME_DENY,
    REASON_CODE_RANK,
    STATUS_FAIL_CLOSED,
)
from app.modules.authorization.business_authority.domain import (
    AuthenticatedActor,
    AuthorityResolutionRequest,
)
from app.modules.authorization.business_authority.lineage import (
    AssertedInterval,
    is_effective,
)
from tests.fixtures.pf_1a_e2_a_corpus import covers
from tests.fixtures.pf_1a_e2_a_reference_providers import (
    T0,
    T1,
    T2,
    T3,
    TICK,
    ReferenceActorPersonProvider,
    ReferenceAuthorityConfigurationProvider,
    ReferenceHrProvider,
    authority_payload,
    version,
)
from tests.fixtures.pf_1a_e2_a_scenarios import run, world

# The DECLARED, BOUNDED family of lineage shapes the property test enumerates.
_STARTS = (T0, T1, T2, T3)
_DECLARED_ENDS = (None, T1, T2, T3)
_MAX_VERSIONS = 3

# Every boundary instant of the section 18 TEMPORAL block.
_BOUNDARY_INSTANTS = tuple(
    instant
    for start in _STARTS
    for instant in (start - TICK, start, start + TICK)
) + (T3 + TICK,)


# ===========================================================================
# NS-K-01 (a)  UNREACHABILITY - the executable form of the 11.4a theorem
# ===========================================================================


@covers("NS-K-01")
def test_at_most_one_version_is_effective_for_every_shape_passing_the_pre_checks() -> None:
    """The 11.4a theorem, executed rather than merely argued.

    For EVERY shape in the declared bounded family that passes the
    duplicate-start, nonsensical-interval and explicit-overlap conditions, AT
    MOST ONE version of the current asserted lineage is EFFECTIVE at any
    instant.

    This deliberately computes effectiveness from the derived intervals
    directly, rather than reading the kernel's own single-version answer,
    so it tests the THEOREM and not the implementation's assumption of it.
    """

    shapes_checked = 0

    for count in range(1, _MAX_VERSIONS + 1):
        for starts in itertools.permutations(_STARTS, count):
            # DUPLICATE START pre-check: `permutations` already guarantees
            # distinct starts, which is exactly the condition the theorem
            # assumes has passed.
            for ends in itertools.product(_DECLARED_ENDS, repeat=count):
                versions = tuple(
                    version(
                        f"{index:04d}",
                        start,
                        payload=authority_payload(),
                        declared_effective_to=end,
                    )
                    for index, (start, end) in enumerate(zip(starts, ends))
                )

                # NONSENSICAL DECLARED INTERVAL pre-check.
                if any(
                    v.declared_effective_to is not None
                    and v.declared_effective_to <= v.effective_from
                    for v in versions
                ):
                    continue

                intervals, defects = lineage._derive_asserted_intervals(versions)
                # EXPLICIT OVERLAP branch.
                if defects:
                    continue

                shapes_checked += 1
                for instant in _BOUNDARY_INSTANTS:
                    effective = [
                        interval
                        for interval in intervals
                        if is_effective(interval, instant)
                    ]
                    assert len(effective) <= 1, (
                        f"{len(effective)} versions effective at {instant} for "
                        f"starts={starts} ends={ends}"
                    )

    # A guard against the enumeration silently collapsing to nothing.
    assert shapes_checked > 100, f"only {shapes_checked} shapes were actually checked"


# ===========================================================================
# NS-K-01 (b)  DEFENSIVE BRANCH - the guard exists, is wired, and is reached
# ===========================================================================


@covers("NS-K-01")
def test_the_residual_multiplicity_clause_is_reachable_by_injection_and_fails_closed(
    monkeypatch,
) -> None:
    """Reaches the 11.6 residual clause by injecting a fabricated internal
    state directly - it is unreachable through any port, WHICH IS PRECISELY
    THE POINT.

    The expected reason code is NORMATIVE, not implementer's choice:
    AUTHORITY_VERSION_AMBIGUOUS - not AUTHORITY_LINEAGE_CONTRADICTORY, which is
    reserved for the contradictions the pre-checks and the overlap branch DO
    reach, and not INTERNAL_CONTRACT_VIOLATION, which is reserved for a
    violated kernel invariant that is not about authority-version
    multiplicity (11.4a consequence 3).
    """

    def fabricate_overlapping_intervals(current_asserted):
        # Two OPEN-ENDED intervals over the same instants, with NO defect
        # reported - a state no conforming provider can present.
        return (
            tuple(
                AssertedInterval(version=published, asserted_effective_to=None)
                for published in current_asserted
            ),
            [],
        )

    monkeypatch.setattr(lineage, "_derive_asserted_intervals", fabricate_overlapping_intervals)

    authority = world()[0]
    two_versions = type(authority)(
        object_family=authority.object_family,
        object_id=authority.object_id,
        versions=(
            version("0001", T0, payload=authority_payload()),
            version("0002", T1, payload=authority_payload()),
        ),
        retraction_assertions=(),
        completeness=authority.completeness,
    )

    result = run(world(authority=two_versions), as_of=T2)

    assert result.outcome == OUTCOME_DENY
    assert result.resolution_status == STATUS_FAIL_CLOSED
    assert result.result_level_reason == AUTHORITY_VERSION_AMBIGUOUS
    # Ordinary 16.4 failure evidence.
    assert result.partial_evaluations
    assert result.partial_evaluations[0].reason_code == AUTHORITY_VERSION_AMBIGUOUS


@covers("NS-K-01")
def test_the_defensive_guard_has_not_been_removed_as_dead_code() -> None:
    """The clause must be RETAINED, not deleted. A future refactor of ordering,
    closure or retraction validation that broke the theorem would then fail
    closed loudly instead of silently granting authority from an ambiguous
    lineage."""

    import inspect

    source = inspect.getsource(lineage._select_effective)
    assert "AUTHORITY_VERSION_AMBIGUOUS" in source
    assert "len(effective) > 1" in source


# ===========================================================================
# NS-K-01 (c)  RANK TOTALITY
# ===========================================================================


@covers("NS-K-01")
def test_authority_version_ambiguous_carries_an_explicit_declared_rank() -> None:
    """Even though no provider can produce the state, the code keeps its
    declared reason_code_rank exactly as any other fail-closed code does
    (11.4a consequence 3, 15.5 totality)."""

    assert AUTHORITY_VERSION_AMBIGUOUS in REASON_CODE_RANK
    assert isinstance(REASON_CODE_RANK[AUTHORITY_VERSION_AMBIGUOUS], int)


# ===========================================================================
# NS-K-02  a violated kernel invariant that is NOT version multiplicity
# ===========================================================================


@covers("NS-K-02")
def test_a_missing_authenticated_actor_fails_closed_with_internal_contract_violation() -> None:
    """A violated kernel invariant that is not authority-version multiplicity
    fails closed with INTERNAL_CONTRACT_VIOLATION and is NEVER degraded to a
    plain DENY (14.3)."""

    result = run(world(), actor_id="")

    assert result.outcome == OUTCOME_DENY
    assert result.resolution_status == STATUS_FAIL_CLOSED
    assert result.result_level_reason == INTERNAL_CONTRACT_VIOLATION
    assert result.result_level_reason != AUTHORITY_VERSION_AMBIGUOUS


@covers("NS-K-02")
def test_an_allow_that_lost_its_qualifying_paths_fails_closed_rather_than_granting(
    monkeypatch,
) -> None:
    """The result-assembly self-check, proved to be WIRED rather than merely
    written.

    ALLOW is only ever valid with RESOLVED and with at least one qualifying
    path. Injecting a loss of the qualifying paths after the outcome was
    decided must produce INTERNAL_CONTRACT_VIOLATION, not a grant.
    """

    monkeypatch.setattr(kernel, "order_paths", lambda paths: ())

    result = run(world())
    assert result.outcome == OUTCOME_DENY
    assert result.resolution_status == STATUS_FAIL_CLOSED
    assert result.result_level_reason == INTERNAL_CONTRACT_VIOLATION


@covers("NS-K-02")
def test_the_kernel_never_returns_allow_with_fail_closed_or_deny_without_a_reason() -> None:
    """ALLOW is only ever valid with RESOLVED; FAIL_CLOSED always implies DENY.
    Uncertainty is never converted into permission (section 14)."""

    from app.modules.authorization.business_authority.contract import (
        OUTCOME_ALLOW,
        STATUS_RESOLVED,
    )

    request = AuthorityResolutionRequest(
        authenticated_actor=AuthenticatedActor(actor_user_public_id="actor-0001"),
        authority_code="CREDIT_ASSESSOR",
    )
    for materials in (world(), [], None):
        result = kernel.resolve(
            request=request,
            as_of=T2,
            authority_configuration_port=(
                ReferenceAuthorityConfigurationProvider(materials) if materials else None
            ),
            actor_person_port=ReferenceActorPersonProvider(),
            hr_reference_port=ReferenceHrProvider(),
        )
        if result.outcome == OUTCOME_ALLOW:
            assert result.resolution_status == STATUS_RESOLVED
            assert result.qualifying_paths
        if result.resolution_status == STATUS_FAIL_CLOSED:
            assert result.outcome == OUTCOME_DENY
            assert result.result_level_reason
            assert result.ordered_defects
