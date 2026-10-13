"""PF-1A-E2-A corrections C2-1, C2-2, C2-3 and C2-4.

Independent review returned CORRECTION_REQUIRED against the frozen pre-C2
candidate. Four material findings, each closed here with the invariant it
protects and a negative control so the positive assertions cannot pass
vacuously.

C2-1  ANCESTRY TERMINATED ON AN UNVERIFIED CLAIM. The upward traversal
      validated every organisation unit it PASSED THROUGH - contract status,
      value type, identity binding, freshness - but not the ancestor it
      TERMINATED ON. A subordinate unit could therefore satisfy an ANCESTRY
      operand by merely DECLARING the operand's scope as its
      `parent_org_unit_id`, while that ancestor had no canonical record at all.
      A fail-open: an unverifiable claim by the subordinate granted authority
      over the superior. The ANCESTRY self-match had the same shape, answering
      from two identifiers without consulting the canonical reference once.

C2-2  NON-CONFORMING TEMPORAL VALUES. A naive `effective_from` raised an
      uncaught TypeError when compared against the timezone-aware authorization
      instant, and a naive `published_at` was accepted and allowed
      authorization. Every datetime participating in authoritative
      interpretation must conform BEFORE it is compared or used.

C2-3  EVIDENCE RECORDED AFTER THE CHECKS THAT REJECT IT. The established
      version of a Rule, Role or Assignment was appended to the candidate trail
      only AFTER the active-flag and reference-mismatch checks had passed, so
      the two most common ordinary denials reported a partial that named the
      object but not the version the decision was actually taken on.

C2-4  ONE CANDIDATE SPLIT ACROSS SEVERAL PARTIALS. A lineage breaking several
      structural rules emitted one partial evaluation per defect, so
      `partial_evaluations` read as though more candidates had been examined
      than actually were - and the candidate key had to be padded with the
      reason code and detail TEXT to keep those duplicates distinct under the
      16.4 accounting.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.modules.authorization.business_authority.contract import (
    AUTHORITY_CONFIGURATION_UNAVAILABLE,
    BUSINESS_AUTHORITY_ASSIGNMENT,
    BUSINESS_AUTHORITY_ROLE,
    BUSINESS_AUTHORITY_RULE,
    HR_REFERENCE_STALE,
    HR_REFERENCE_UNAVAILABLE,
    INTERNAL_CONTRACT_VIOLATION,
    ORG_UNIT_STATE_AMBIGUOUS,
    ORG_UNIT_STATE_MISSING,
    OTHER_NONQUALIFICATION,
    OUTCOME_ALLOW,
    OUTCOME_DENY,
    PUBLICATION_PROVENANCE_INVALID,
    ROLE_NOT_ACTIVE,
    RULE_NOT_ACTIVE,
    SCOPE_ANCESTRY,
    STATUS_FAIL_CLOSED,
    STATUS_RESOLVED,
)
from app.modules.authorization.business_authority.domain import BusinessContext
from app.modules.authorization.business_authority.evidence import serialize_result
from app.modules.authorization.business_authority.resolver import resolve_authority_as_of
from app.modules.authorization.business_authority.scope import SCOPE_KIND_ORG_UNIT
from app.modules.hr_reference.contract import (
    ActorPersonReference,
    is_conforming_instant,
    is_utc_normalized_instant,
)
from tests.fixtures.pf_1a_e2_a_reference_providers import (
    ACTOR_ID,
    ORDER_REVERSED,
    ORDER_SHUFFLED,
    ORG_BRANCH,
    ORG_DIVISION,
    ORG_ROOT,
    PERSON_ID,
    RECORDED_AT,
    T3,
    ReferenceActorPersonProvider,
    ReferenceAuthorityConfigurationProvider,
    ReferenceHrProvider,
    assignment_payload,
    retraction,
    role_payload,
    rule_payload,
    version,
)
from tests.fixtures.pf_1a_e2_a_scenarios import (
    ROLE_ID,
    RULE_ID,
    T0,
    T2,
    V1,
    V2,
    assignment_material,
    role_material,
    rule_material,
    run,
    world,
)

# A datetime that names no instant. Every C2-2 case injects exactly one of
# these into an otherwise entirely valid world, so nothing but the temporal
# shape can explain the difference in outcome.
NAIVE = datetime(2026, 6, 1, 12, 0, 0)

# An aware instant carrying a NON-ZERO offset, denoting exactly the same
# moment as `RECORDED_AT`. Whether it conforms depends entirely on WHICH FIELD
# it appears in, and that field-by-field split is what the C2 final
# reconciliation established:
#
#   E2-A 8.1     effective_from is "inclusive, timezone-aware" - no UTC rule,
#                so a +05:30 value CONFORMS and must be preserved, not rejected
#                and not rewritten.
#   E2-A 11.1    the single as_of "is timezone-aware and normalized to UTC" -
#                so a +05:30 value does NOT conform.
#   E2-A 11.8.3  published_at and retracted_at are "timezone-aware, normalized
#                to UTC, and NOT NULL" - so a +05:30 value does NOT conform.
IST = timezone(timedelta(hours=5, minutes=30))
NON_UTC = RECORDED_AT.astimezone(IST)

# The SAME absolute instant as the T2 authorization instant, expressed at
# +05:30. Used to prove the kernel compares by absolute instant and does not
# reinterpret the wall-clock reading: if it silently treated 17:30+05:30 as
# 17:30Z, this would fall five and a half hours AFTER T2 and stop being
# effective.
T2_AS_IST = T2.astimezone(IST)

THRESHOLD_SECONDS = 3600
FRESH = T2
STALE = T2 - timedelta(seconds=THRESHOLD_SECONDS + 1)


# ===========================================================================
# C2-1  THE TERMINATING ANCESTOR IS AUTHORITATIVE STATE, NOT A CLAIM
# ===========================================================================
# Shape of every case below: the request context is ORG_BRANCH, the rule's
# ANCESTRY operand names ORG_DIVISION, and ORG_BRANCH resolves perfectly while
# DECLARING ORG_DIVISION as its parent. Only the ancestor's own canonical
# answer varies. Under the pre-C2 kernel every one of these ALLOWED.

_ANCESTRY_CONTEXT = BusinessContext(scope_type=SCOPE_KIND_ORG_UNIT, scope_id=ORG_BRANCH)


def _ancestry_world():
    return world(rule=rule_material(scope_type=SCOPE_ANCESTRY, scope_id=ORG_DIVISION))


def _ancestry_run(hr_port, **kwargs):
    return run(
        _ancestry_world(),
        business_context=_ANCESTRY_CONTEXT,
        hr_reference_port=hr_port,
        **kwargs,
    )


def test_the_terminating_ancestor_is_resolved_and_a_verified_one_still_allows() -> None:
    """THE NEGATIVE CONTROL FOR THE WHOLE C2-1 GROUP.

    An ancestry chain whose ancestor IS canonically present, about the unit
    asked for and fresh still grants exactly as before. Without this, every
    assertion below could be satisfied by a kernel that had simply stopped
    granting on ancestry altogether.
    """

    result = _ancestry_run(ReferenceHrProvider())

    assert result.outcome == OUTCOME_ALLOW
    assert result.resolution_status == STATUS_RESOLVED


def test_a_declared_parent_with_no_canonical_record_can_never_allow() -> None:
    """THE PRIMARY C2-1 CASE.

    ORG_BRANCH declares ORG_DIVISION as its parent, and no canonical record for
    ORG_DIVISION exists. The claim is the SUBORDINATE's; believing it grants
    authority over a superior unit the reference cannot even confirm exists.
    """

    hr_port = ReferenceHrProvider(org_parents={ORG_BRANCH: ORG_DIVISION})
    result = _ancestry_run(hr_port)

    assert result.outcome == OUTCOME_DENY
    assert result.resolution_status == STATUS_FAIL_CLOSED
    assert result.result_level_reason == ORG_UNIT_STATE_MISSING
    assert result.qualifying_paths == ()


@pytest.mark.parametrize(
    ("ancestor_result", "expected_reason"),
    [
        ("MISSING", ORG_UNIT_STATE_MISSING),
        ("AMBIGUOUS", ORG_UNIT_STATE_AMBIGUOUS),
        ("UNAVAILABLE", HR_REFERENCE_UNAVAILABLE),
        ("STALE", HR_REFERENCE_STALE),
    ],
)
def test_every_unusable_ancestor_answer_fails_closed(
    ancestor_result: str, expected_reason: str
) -> None:
    """Each failure mode keeps its OWN reason code.

    An unusable ancestor is never collapsed into a single generic code, and -
    critically - it is never ordinary nonqualification, because "the reference
    could not tell us" is not "the unit is not an ancestor".
    """

    hr_port = ReferenceHrProvider(org_unit_results={ORG_DIVISION: ancestor_result})
    result = _ancestry_run(hr_port)

    assert result.outcome == OUTCOME_DENY
    assert result.resolution_status == STATUS_FAIL_CLOSED
    assert result.result_level_reason == expected_reason


def test_an_ancestor_response_about_a_different_unit_fails_closed() -> None:
    """Identity binding applies to the TERMINATING unit too (FU-1 + C2-1).

    The response is fresh, well typed and contract-conforming; it is simply
    about ORG_ROOT rather than the ORG_DIVISION that was asked for. Accepting
    it would terminate the walk on a unit nobody requested.
    """

    hr_port = ReferenceHrProvider(returned_org_unit_ids={ORG_DIVISION: ORG_ROOT})
    result = _ancestry_run(hr_port)

    assert result.outcome == OUTCOME_DENY
    assert result.resolution_status == STATUS_FAIL_CLOSED
    assert result.result_level_reason == HR_REFERENCE_UNAVAILABLE
    # The foreign identity is never echoed outward.
    assert ORG_ROOT not in serialize_result(result)


def test_a_stale_terminating_ancestor_fails_closed_under_the_supplied_threshold() -> None:
    """The SAME threshold and the SAME as_of that govern every other hop.

    Only the ancestor's snapshot is aged; ORG_BRANCH stays fresh, so a kernel
    that checked freshness on traversed hops alone would still have allowed.
    """

    hr_port = ReferenceHrProvider(
        snapshot_at=FRESH,
        org_unit_snapshots={ORG_BRANCH: FRESH, ORG_DIVISION: STALE},
    )
    result = _ancestry_run(
        hr_port,
        actor_person_port=ReferenceActorPersonProvider(snapshot_at=FRESH),
        hr_staleness_threshold_seconds=THRESHOLD_SECONDS,
    )

    assert result.outcome == OUTCOME_DENY
    assert result.resolution_status == STATUS_FAIL_CLOSED
    assert result.result_level_reason == HR_REFERENCE_STALE

    # And the SAME world with a fresh ancestor still allows, so the assertion
    # above is about the ancestor rather than about some other stale seam.
    fresh_everywhere = ReferenceHrProvider(
        snapshot_at=FRESH,
        org_unit_snapshots={ORG_BRANCH: FRESH, ORG_DIVISION: FRESH},
    )
    allowed = _ancestry_run(
        fresh_everywhere,
        actor_person_port=ReferenceActorPersonProvider(snapshot_at=FRESH),
        hr_staleness_threshold_seconds=THRESHOLD_SECONDS,
    )
    assert allowed.outcome == OUTCOME_ALLOW


def test_the_terminating_ancestor_appears_in_the_paths_hr_evidence() -> None:
    """The grant rested on the ancestor, so the record must say so.

    A unit that decides an ALLOW and is absent from the evidence is exactly the
    gap that let the unverified claim go unnoticed.
    """

    result = _ancestry_run(ReferenceHrProvider())

    assert result.outcome == OUTCOME_ALLOW
    hr_evidence = result.qualifying_paths[0].hr_evidence
    assert hr_evidence.org_unit_version_ids == (
        f"org-version-{ORG_BRANCH}",
        f"org-version-{ORG_DIVISION}",
    )


def test_the_ancestry_self_match_also_resolves_the_scope_canonically() -> None:
    """"The context IS the operand's scope" is a TERMINATION, not a shortcut.

    Identifier equality is not evidence that a scope exists. Here the context
    and the operand both name ORG_BRANCH, and ORG_BRANCH has no canonical
    record; the pre-C2 kernel answered from the two strings alone and allowed.
    """

    self_match_world = world(rule=rule_material(scope_type=SCOPE_ANCESTRY, scope_id=ORG_BRANCH))
    hr_port = ReferenceHrProvider(org_unit_results={ORG_BRANCH: "MISSING"})

    result = run(
        self_match_world,
        business_context=_ANCESTRY_CONTEXT,
        hr_reference_port=hr_port,
    )

    assert result.outcome == OUTCOME_DENY
    assert result.resolution_status == STATUS_FAIL_CLOSED
    assert result.result_level_reason == ORG_UNIT_STATE_MISSING


def test_a_verified_ancestry_self_match_still_allows_and_records_the_unit() -> None:
    """The negative control for the self-match, and its evidence obligation."""

    self_match_world = world(rule=rule_material(scope_type=SCOPE_ANCESTRY, scope_id=ORG_BRANCH))

    result = run(
        self_match_world,
        business_context=_ANCESTRY_CONTEXT,
        hr_reference_port=ReferenceHrProvider(),
    )

    assert result.outcome == OUTCOME_ALLOW
    assert result.qualifying_paths[0].hr_evidence.org_unit_version_ids == (
        f"org-version-{ORG_BRANCH}",
    )


@pytest.mark.parametrize("order", [ORDER_REVERSED, ORDER_SHUFFLED])
def test_ancestor_resolution_is_deterministic_under_provider_ordering(order: str) -> None:
    """Provider row order changes nothing about the ancestor's verification."""

    unverified = _ancestry_run(
        ReferenceHrProvider(org_parents={ORG_BRANCH: ORG_DIVISION}), order=order
    )
    verified = _ancestry_run(ReferenceHrProvider(), order=order)

    assert unverified.resolution_status == STATUS_FAIL_CLOSED
    assert unverified.result_level_reason == ORG_UNIT_STATE_MISSING
    assert verified.outcome == OUTCOME_ALLOW


# ===========================================================================
# C2-2  EVERY AUTHORITATIVE INSTANT MUST CONFORM BEFORE IT IS USED
# ===========================================================================


def test_a_naive_datetime_is_never_a_usable_instant_under_either_rule() -> None:
    """A naive datetime names no instant, so it conforms nowhere.

    The two predicates differ only on the non-UTC AWARE case, which
    `test_the_two_temporal_predicates_are_not_the_same_rule` pins.
    """

    for predicate in (is_conforming_instant, is_utc_normalized_instant):
        assert predicate(RECORDED_AT) is True
        assert predicate(NAIVE) is False
        assert predicate(None) is False
        assert predicate("2026-06-01T12:00:00Z") is False
        assert predicate(0) is False
        assert predicate(True) is False


# --- the AWARE-ONLY fields: 8.1 requires awareness and NOT UTC -------------


def test_a_non_utc_but_aware_effective_from_conforms_and_is_not_reinterpreted() -> None:
    """E2-A 8.1: `effective_from   inclusive, timezone-aware`. No UTC rule.

    Rejecting a valid +05:30 business-effective instant would invent a
    requirement the contract does not state for this field, and would refuse
    conforming configuration data.

    The instant chosen is the SAME ABSOLUTE MOMENT as the authorization
    instant, expressed at +05:30, so this also proves the kernel does not
    reinterpret the wall-clock reading: 8.1's boundary is INCLUSIVE, so an
    `effective_from` equal to `as_of` is effective, while a value silently
    re-read as UTC would land five and a half hours later and confer nothing.
    """

    non_utc_world = world(
        rule=rule_material(versions=(version(V1, T2_AS_IST, payload=rule_payload()),))
    )
    result = run(non_utc_world)

    assert result.outcome == OUTCOME_ALLOW
    assert result.resolution_status == STATUS_RESOLVED


def test_a_non_utc_but_aware_declared_effective_to_conforms() -> None:
    """Same table as `effective_from` (8.1), same requirement.

    Awareness is required by necessary implication - I-6 and the 11.4
    asserted-interval rule COMPARE this value - but 8.1 and 11.2 state no UTC
    rule for it, so none is enforced.
    """

    non_utc_world = world(
        rule=rule_material(
            versions=(
                version(
                    V1,
                    T0,
                    payload=rule_payload(),
                    declared_effective_to=T3.astimezone(IST),
                ),
            )
        )
    )
    result = run(non_utc_world)

    assert result.outcome == OUTCOME_ALLOW
    assert result.resolution_status == STATUS_RESOLVED


def test_a_non_utc_but_aware_canonical_snapshot_conforms() -> None:
    """E2-A 7 / 9.1 / 9.2 state no UTC rule for `canonical_snapshot_at`.

    Awareness is required only because the staleness rule subtracts it from
    `as_of`. With a threshold configured and a fresh +05:30 snapshot, the
    freshness question is answerable and answered.
    """

    fresh_non_utc = FRESH.astimezone(IST)
    result = run(
        world(),
        actor_person_port=ReferenceActorPersonProvider(snapshot_at=fresh_non_utc),
        hr_reference_port=ReferenceHrProvider(snapshot_at=fresh_non_utc),
        hr_staleness_threshold_seconds=THRESHOLD_SECONDS,
    )

    assert result.outcome == OUTCOME_ALLOW
    assert result.resolution_status == STATUS_RESOLVED


# --- the UTC-NORMALIZED fields: 11.1 and 11.8.3 say so in terms ------------


def test_a_non_utc_but_aware_published_at_is_nonconforming_provenance() -> None:
    """E2-A 11.8.3: published_at is "timezone-aware, normalized to UTC".

    A +05:30 value is comparable, but it is not the UTC-normalized provenance
    11.8.3 requires. It is reported as invalid provenance and is NOT rewritten
    to UTC to manufacture conformance - doing so would erase the very evidence
    the check exists to surface.
    """

    non_utc_world = world(
        rule=rule_material(versions=(version(V1, T0, payload=rule_payload(), published_at=NON_UTC),))
    )
    result = run(non_utc_world)

    assert result.outcome == OUTCOME_DENY
    assert result.resolution_status == STATUS_FAIL_CLOSED
    assert result.result_level_reason == PUBLICATION_PROVENANCE_INVALID
    assert result.qualifying_paths == ()


def test_a_non_utc_but_aware_retracted_at_is_nonconforming_provenance() -> None:
    """11.8.3 names retracted_at in the same sentence as published_at."""

    non_utc_world = world(
        rule=rule_material(
            versions=(version(V1, T0, payload=rule_payload()),),
            retractions=(retraction("retraction-1", V1, retracted_at=NON_UTC),),
        )
    )
    result = run(non_utc_world)

    assert result.outcome == OUTCOME_DENY
    assert result.resolution_status == STATUS_FAIL_CLOSED
    assert result.result_level_reason == PUBLICATION_PROVENANCE_INVALID


def test_a_non_utc_but_aware_as_of_is_nonconforming() -> None:
    """E2-A 11.1: the single as_of "is timezone-aware and normalized to UTC".

    10.2 defines no input-normalization step at the historical boundary, so a
    caller-supplied +05:30 instant is not silently reinterpreted into a
    conforming one: it fails closed, exactly as a naive one does.
    """

    port = ReferenceAuthorityConfigurationProvider(world())
    reference = ActorPersonReference(
        actor_user_public_id=ACTOR_ID,
        person_id=PERSON_ID,
        canonical_snapshot_at=RECORDED_AT,
        reference_evidence="test",
    )

    result = resolve_authority_as_of(
        reference,
        "CREDIT_ASSESSOR",
        None,
        T2_AS_IST,
        authority_configuration_port=port,
        hr_reference_port=ReferenceHrProvider(),
    )

    assert result.outcome == OUTCOME_DENY
    assert result.resolution_status == STATUS_FAIL_CLOSED
    assert result.result_level_reason == INTERNAL_CONTRACT_VIOLATION


def test_the_two_temporal_predicates_are_not_the_same_rule() -> None:
    """THE CONTROL THAT KEEPS THE TWO REQUIREMENTS APART.

    If these ever collapse into one predicate, either a conforming +05:30
    `effective_from` starts being rejected or a nonconforming +05:30
    `published_at` starts being accepted. Both are contract violations, in
    opposite directions.
    """

    assert is_conforming_instant(NON_UTC) is True
    assert is_utc_normalized_instant(NON_UTC) is False

    assert is_conforming_instant(RECORDED_AT) is True
    assert is_utc_normalized_instant(RECORDED_AT) is True

    # A fixed zero-offset timezone is UTC-normalized even though it is not the
    # `timezone.utc` singleton: the value asserts a zero offset, which is what
    # "normalized to UTC" constrains.
    zero_offset = RECORDED_AT.astimezone(timezone(timedelta(0)))
    assert is_utc_normalized_instant(zero_offset) is True

    for junk in (NAIVE, None, "2026-06-01T12:00:00Z", 0, True):
        assert is_conforming_instant(junk) is False
        assert is_utc_normalized_instant(junk) is False


def test_no_temporal_exception_escapes_for_any_malformed_field() -> None:
    """G. Malformed temporal provider material NEVER raises out of the kernel.

    Every field is swept with both a naive datetime and a non-datetime value.
    A result object must come back every time, always DENY, and never an
    ALLOW - the failure mode the review actually reproduced was an uncaught
    `TypeError`, so "it returned a result at all" is the assertion that matters
    here.
    """

    junk_values = (NAIVE, "not-a-datetime", 0)
    results = []

    for junk in junk_values:
        results.append(run(world(rule=rule_material(versions=(version(V1, junk, payload=rule_payload()),)))))
        results.append(
            run(
                world(
                    rule=rule_material(
                        versions=(version(V1, T0, payload=rule_payload(), declared_effective_to=junk),)
                    )
                )
            )
        )
        results.append(
            run(
                world(
                    rule=rule_material(
                        versions=(version(V1, T0, payload=rule_payload(), published_at=junk),)
                    )
                )
            )
        )
        results.append(
            run(
                world(
                    rule=rule_material(
                        versions=(version(V1, T0, payload=rule_payload()),),
                        retractions=(retraction("retraction-1", V1, retracted_at=junk),),
                    )
                )
            )
        )
        results.append(run(world(), hr_reference_port=ReferenceHrProvider(snapshot_at=junk)))
        results.append(
            run(world(), actor_person_port=ReferenceActorPersonProvider(snapshot_at=junk))
        )

        port = ReferenceAuthorityConfigurationProvider(world())
        reference = ActorPersonReference(
            actor_user_public_id=ACTOR_ID,
            person_id=PERSON_ID,
            canonical_snapshot_at=RECORDED_AT,
            reference_evidence="test",
        )
        results.append(
            resolve_authority_as_of(
                reference,
                "CREDIT_ASSESSOR",
                None,
                junk,
                authority_configuration_port=port,
                hr_reference_port=ReferenceHrProvider(),
            )
        )

    assert len(results) == len(junk_values) * 7
    for result in results:
        assert result.outcome == OUTCOME_DENY
        assert result.resolution_status == STATUS_FAIL_CLOSED
        assert result.qualifying_paths == ()


def test_a_naive_effective_from_fails_closed_instead_of_raising() -> None:
    """Business-effective time. The pre-C2 kernel raised TypeError here."""

    naive_world = world(
        rule=rule_material(versions=(version(V1, NAIVE, payload=rule_payload()),))
    )
    result = run(naive_world)

    assert result.outcome == OUTCOME_DENY
    assert result.resolution_status == STATUS_FAIL_CLOSED
    assert result.result_level_reason == AUTHORITY_CONFIGURATION_UNAVAILABLE


def test_a_naive_declared_effective_to_fails_closed() -> None:
    """The optional end of a business-effective interval is compared too."""

    naive_world = world(
        rule=rule_material(
            versions=(version(V1, T0, payload=rule_payload(), declared_effective_to=NAIVE),)
        )
    )
    result = run(naive_world)

    assert result.outcome == OUTCOME_DENY
    assert result.resolution_status == STATUS_FAIL_CLOSED
    assert result.result_level_reason == AUTHORITY_CONFIGURATION_UNAVAILABLE


def test_a_naive_published_at_fails_closed_and_never_authorizes() -> None:
    """Recorded provenance. The pre-C2 kernel ACCEPTED this and allowed."""

    naive_world = world(
        rule=rule_material(versions=(version(V1, T0, payload=rule_payload(), published_at=NAIVE),))
    )
    result = run(naive_world)

    assert result.outcome == OUTCOME_DENY
    assert result.resolution_status == STATUS_FAIL_CLOSED
    assert result.result_level_reason == PUBLICATION_PROVENANCE_INVALID


def test_a_naive_retracted_at_fails_closed() -> None:
    """A retraction whose recorded instant is unusable is invalid provenance.

    It is never quietly dropped, which would leave its target version standing.
    """

    naive_world = world(
        rule=rule_material(
            versions=(version(V1, T0, payload=rule_payload()),),
            retractions=(retraction("retraction-1", V1, retracted_at=NAIVE),),
        )
    )
    result = run(naive_world)

    assert result.outcome == OUTCOME_DENY
    assert result.resolution_status == STATUS_FAIL_CLOSED
    assert result.result_level_reason == PUBLICATION_PROVENANCE_INVALID


def test_a_naive_canonical_snapshot_fails_closed_rather_than_skipping_freshness() -> None:
    """An unanswerable freshness question is not a passed freshness check.

    The subtraction in the staleness rule would raise on a naive snapshot, so
    the state is simply not established.
    """

    result = run(world(), hr_reference_port=ReferenceHrProvider(snapshot_at=NAIVE))

    assert result.outcome == OUTCOME_DENY
    assert result.resolution_status == STATUS_FAIL_CLOSED
    assert result.result_level_reason == HR_REFERENCE_UNAVAILABLE

    # No staleness threshold is configured above, deliberately: a
    # non-conforming instant is a provider-contract failure in its own right,
    # not merely a freshness check that happened to be unanswerable. The same
    # world with a conforming snapshot allows.
    assert run(world(), hr_reference_port=ReferenceHrProvider()).outcome == OUTCOME_ALLOW


def test_a_naive_org_unit_snapshot_fails_closed_during_ancestry() -> None:
    """The same rule at the organisation-reference seam."""

    hr_port = ReferenceHrProvider(org_unit_snapshots={ORG_DIVISION: NAIVE})
    result = _ancestry_run(hr_port)

    assert result.outcome == OUTCOME_DENY
    assert result.resolution_status == STATUS_FAIL_CLOSED
    assert result.result_level_reason == HR_REFERENCE_UNAVAILABLE


def test_a_naive_historical_as_of_fails_closed_rather_than_raising() -> None:
    """The caller-supplied historical instant is validated at kernel entry.

    `resolve_current_authority` captures a conforming instant itself, so this
    is the one path by which a non-conforming authorization instant can arrive.
    It must produce a deterministic fail-closed result, never an exception
    escaping into the caller.
    """

    port = ReferenceAuthorityConfigurationProvider(world())
    reference = ActorPersonReference(
        actor_user_public_id=ACTOR_ID,
        person_id=PERSON_ID,
        canonical_snapshot_at=RECORDED_AT,
        reference_evidence="test",
    )

    result = resolve_authority_as_of(
        reference,
        "CREDIT_ASSESSOR",
        None,
        NAIVE,
        authority_configuration_port=port,
        hr_reference_port=ReferenceHrProvider(),
    )

    assert result.outcome == OUTCOME_DENY
    assert result.resolution_status == STATUS_FAIL_CLOSED
    assert result.result_level_reason == INTERNAL_CONTRACT_VIOLATION


def test_the_historical_resolver_still_reconstructs_at_a_conforming_instant() -> None:
    """The negative control for the entry-point check."""

    port = ReferenceAuthorityConfigurationProvider(world())
    reference = ActorPersonReference(
        actor_user_public_id=ACTOR_ID,
        person_id=PERSON_ID,
        canonical_snapshot_at=RECORDED_AT,
        reference_evidence="test",
    )

    result = resolve_authority_as_of(
        reference,
        "CREDIT_ASSESSOR",
        None,
        T2,
        authority_configuration_port=port,
        hr_reference_port=ReferenceHrProvider(),
    )

    assert result.outcome == OUTCOME_ALLOW
    assert result.resolution_status == STATUS_RESOLVED


# ===========================================================================
# C2-3  THE ESTABLISHED VERSION IS EVIDENCE BEFORE IT IS JUDGED
# ===========================================================================


def _established_versions(partial) -> dict[str, str]:
    return {ref.object_family: ref.object_version for ref in partial.established}


def _partial_for(result, reason_code: str):
    matches = [p for p in result.partial_evaluations if p.reason_code == reason_code]
    assert len(matches) == 1, [p.reason_code for p in result.partial_evaluations]
    return matches[0]


def test_an_inactive_rule_partial_names_the_version_it_was_judged_on() -> None:
    inactive = world(
        rule=rule_material(
            versions=(version(V1, T0, payload=rule_payload(), active_flag=False),)
        )
    )
    result = run(inactive)

    assert result.outcome == OUTCOME_DENY
    assert result.resolution_status == STATUS_RESOLVED
    partial = _partial_for(result, RULE_NOT_ACTIVE)
    assert _established_versions(partial)[BUSINESS_AUTHORITY_RULE] == V1


def test_an_inactive_role_partial_names_the_version_it_was_judged_on() -> None:
    inactive = world(
        role=role_material(
            versions=(
                version(
                    V1,
                    T0,
                    payload=role_payload(),
                    active_flag=False,
                ),
            )
        )
    )
    result = run(inactive)

    assert result.resolution_status == STATUS_RESOLVED
    partial = _partial_for(result, ROLE_NOT_ACTIVE)
    established = _established_versions(partial)
    # The Rule that reached the Role is retained too, so the record shows the
    # whole path the decision was taken on - not only the failing object.
    assert established[BUSINESS_AUTHORITY_RULE] == V1
    assert established[BUSINESS_AUTHORITY_ROLE] == V1


def test_a_reference_mismatch_partial_names_the_version_that_points_elsewhere() -> None:
    """The C1-1 historical-reference case, now with the deciding version.

    "This assignment's current version references another role" is unusable
    evidence without saying WHICH version does so.
    """

    mismatched = world(
        assignment=assignment_material(
            versions=(
                version(V1, T0, payload=assignment_payload(role_id=ROLE_ID)),
                version(
                    V2,
                    T0 + timedelta(days=1),
                    payload=assignment_payload(role_id="role-elsewhere"),
                ),
            )
        )
    )
    result = run(mismatched)

    assert result.resolution_status == STATUS_RESOLVED
    partial = _partial_for(result, OTHER_NONQUALIFICATION)
    assert _established_versions(partial)[BUSINESS_AUTHORITY_ASSIGNMENT] == V2
    assert partial.nonqualification_explanation


def test_recording_the_version_early_does_not_make_the_candidate_qualify() -> None:
    """THE NEGATIVE CONTROL FOR C2-3.

    The trail is audit evidence, never permission. An inactive rule appears in
    the evidence with its version and still produces no qualifying path.
    """

    inactive = world(
        rule=rule_material(
            versions=(version(V1, T0, payload=rule_payload(), active_flag=False),)
        )
    )
    result = run(inactive)

    assert result.outcome == OUTCOME_DENY
    assert result.qualifying_paths == ()
    assert result.complete_nonqualifying_paths == ()


# ===========================================================================
# C2-4  ONE PARTIAL EVALUATION PER LOGICAL CANDIDATE
# ===========================================================================


def _multi_defect_world():
    """One Rule lineage that breaks SEVERAL structural rules at once.

    Two published versions share one `object_version`, and both carry absent
    recorded provenance - genuinely several independent defects against a
    single candidate.
    """

    return world(
        rule=rule_material(
            versions=(
                version(V1, T0, payload=rule_payload(), published_at=None),
                version(V1, T0 + timedelta(days=1), payload=rule_payload(), published_at=None),
            )
        )
    )


def test_one_broken_candidate_produces_exactly_one_partial_evaluation() -> None:
    result = run(_multi_defect_world())

    assert result.resolution_status == STATUS_FAIL_CLOSED
    assert len(result.partial_evaluations) == 1


def test_that_single_partial_carries_every_defect_that_ended_the_candidate() -> None:
    """Grouping must not LOSE a defect - only stop duplicating the candidate."""

    result = run(_multi_defect_world())

    partial = result.partial_evaluations[0]
    assert len(partial.defects) > 1
    # The decisive defect is the first, and is what the reason code and the
    # 16.5 ordering continue to read.
    assert partial.defect is partial.defects[0]
    assert partial.reason_code == partial.defects[0].reason_code
    assert partial.last_stage_reached == partial.defects[0].stage


def test_every_defect_is_still_reported_individually_in_the_total_order() -> None:
    """`ordered_defects` is unchanged: grouping is an evidence concern only."""

    result = run(_multi_defect_world())

    partial = result.partial_evaluations[0]
    ordered = result.ordered_defects
    assert len(ordered) >= len(partial.defects)
    for defect in partial.defects:
        assert defect in ordered
    assert result.result_level_reason == ordered[0].reason_code


def test_the_candidate_key_no_longer_depends_on_diagnostic_text() -> None:
    """Canonical identity only.

    A key padded with the reason code and the detail STRING made the 16.4
    accounting depend on wording that exists for humans, not for identity.
    """

    result = run(_multi_defect_world())

    key = result.partial_evaluations[0].candidate_key
    assert key == (BUSINESS_AUTHORITY_RULE, RULE_ID)
    for defect in result.partial_evaluations[0].defects:
        assert defect.reason_code not in key
        assert defect.detail not in key


def test_two_distinct_broken_candidates_remain_two_partials() -> None:
    """THE NEGATIVE CONTROL FOR C2-4.

    Grouping is per CANDIDATE, not per object family: two genuinely different
    broken Rules must still be two partial evaluations, with distinct keys.
    """

    second_rule = "rule-second"
    two_broken = world(
        rule=rule_material(versions=(version(V1, T0, payload=rule_payload(), published_at=None),)),
        extra=(
            rule_material(
                object_id=second_rule,
                versions=(version(V1, T0, payload=rule_payload(), published_at=None),),
            ),
        ),
    )
    result = run(two_broken)

    assert result.resolution_status == STATUS_FAIL_CLOSED
    assert len(result.partial_evaluations) == 2
    assert len({p.candidate_key for p in result.partial_evaluations}) == 2


def test_a_broken_role_reached_through_two_rules_stays_two_candidates() -> None:
    """The candidate key carries the whole established path prefix.

    Two Rules referencing ONE broken Role are two candidates. Once the
    reason/detail padding was removed, keying the role failure on the role
    alone would have collided them and tripped the 16.4 accounting.
    """

    second_rule = "rule-second"
    shared_broken_role = world(
        role=role_material(
            versions=(
                version(
                    V1,
                    T0,
                    payload=role_payload(),
                    published_at=None,
                ),
            )
        ),
        extra=(rule_material(object_id=second_rule, role_id=ROLE_ID),),
    )
    result = run(shared_broken_role)

    assert result.resolution_status == STATUS_FAIL_CLOSED
    assert result.result_level_reason == PUBLICATION_PROVENANCE_INVALID
    keys = [p.candidate_key for p in result.partial_evaluations]
    assert len(keys) == len(set(keys)) == 2
    # And no kernel-invariant violation was raised by the 16.4 accounting.
    assert INTERNAL_CONTRACT_VIOLATION not in [d.reason_code for d in result.ordered_defects]


def test_the_grouped_partial_still_retains_its_established_trail() -> None:
    """C2-4 must not undo FU-2: grouping changes count, not content."""

    result = run(_multi_defect_world())

    partial = result.partial_evaluations[0]
    assert partial.hr_evidence is not None
    assert any(
        ref.object_family == "BUSINESS_AUTHORITY" for ref in partial.established
    ), partial.established


def test_an_unbroken_world_produces_no_partial_evaluations_at_all() -> None:
    """The baseline the whole C2-4 group is measured against."""

    result = run(world())

    assert result.outcome == OUTCOME_ALLOW
    assert result.partial_evaluations == ()
    assert len(result.qualifying_paths) == 1
