"""PF-1A-E3: activation is serialized, atomic, and leaves nothing behind on failure."""

from __future__ import annotations

import uuid

import pytest

from app.core.database import SessionLocal
from app.modules.authorization.business_authority import configuration_contract as e3
from app.modules.authorization.business_authority import configuration_repository as store
from tests.fixtures import pf_1a_e3_reference_context as ctx
from tests.fixtures.pf_1a_e3_reference_context import (  # noqa: F401
    ADMIN_A,
    assignment_payload,
    authoritative_predecessor,
    current_version,
    env,
    hours_ago,
    hours_from_now,
    proposal,
    publish,
    role_payload,
    version_rows,
)

ROLE = e3.BUSINESS_AUTHORITY_ROLE
ASSIGNMENT = e3.BUSINESS_AUTHORITY_ASSIGNMENT


def test_a_concurrent_activation_holding_the_object_lock_is_refused_not_queued(env) -> None:
    """Deterministic rather than threaded: a second session holds the per-object advisory
    lock, and activation refuses immediately instead of blocking inside an open transaction."""

    proposed = env.service.propose(
        ADMIN_A, proposal(ROLE, "e3-lock", e3.CHANGE_CREATE, role_payload())
    )
    assert env.service.authorize(ADMIN_A, proposed.configuration_change_id).accepted

    other = SessionLocal()
    try:
        store.lock_object(other, ROLE, "e3-lock")
        refused = env.service.activate(ADMIN_A, proposed.configuration_change_id)
        assert refused.accepted is False
        assert refused.refusal_reason == e3.CONCURRENT_ACTIVATION_IN_PROGRESS
        assert version_rows(env.db, ROLE, "e3-lock") == []
    finally:
        other.rollback()
        other.close()

    # Once the lock is released the same change activates normally.
    activated = env.service.activate(ADMIN_A, proposed.configuration_change_id)
    assert activated.accepted, activated.refusal_reason
    assert activated.published_object_version == e3.allocate_object_version(
        None, proposed.configuration_change_id
    )


def test_two_conflicting_activations_of_different_objects_cannot_both_publish(env) -> None:
    """THE GOVERNANCE-WIDE SERIALIZATION REGRESSION.

    Two DIFFERENT stable assignment objects proposing the same role, the same target, the same
    scope and an overlapping interval. Neither is published yet, so both proposals are
    legitimately accepted - the duplicate rule is a published-state rule.

    Per-object locking cannot serialize this pair at all: two different stable object ids take
    two different lock keys, which the first block below proves directly. Under READ COMMITTED
    each activation could then validate against a snapshot taken before the other published, and
    both would publish a duplicate active assignment.

    A second, genuinely separate database session holding the governance-wide publication
    boundary is therefore what must stop the second activation - and once the pair IS serialized,
    the second one sees the first's publication and refuses on the duplicate rule.
    """

    payload = assignment_payload(ctx.ROLE_ORDINARY, person_id=ctx.PLAIN_PERSON)
    first = env.service.propose(
        ADMIN_A, proposal(ASSIGNMENT, "e3-conflict-1", e3.CHANGE_CREATE, payload, hours=6)
    )
    second = env.service.propose(
        ADMIN_A, proposal(ASSIGNMENT, "e3-conflict-2", e3.CHANGE_CREATE, payload, hours=5)
    )
    assert first.accepted and second.accepted, (first.refusal_reason, second.refusal_reason)
    assert env.service.authorize(ADMIN_A, first.configuration_change_id).accepted
    assert env.service.authorize(ADMIN_A, second.configuration_change_id).accepted

    probe = SessionLocal()
    try:
        # Independent keys, so the narrower lock would have let both proceed concurrently.
        assert store.try_lock_object(probe, ASSIGNMENT, "e3-conflict-1") is True
        assert store.try_lock_object(probe, ASSIGNMENT, "e3-conflict-2") is True
    finally:
        probe.rollback()
        probe.close()

    other = SessionLocal()
    try:
        store.lock_governance_publication(other)
        refused = env.service.activate(ADMIN_A, second.configuration_change_id)
        assert refused.accepted is False
        assert refused.refusal_reason == e3.CONCURRENT_ACTIVATION_IN_PROGRESS
        assert version_rows(env.db, ASSIGNMENT, "e3-conflict-2") == []
    finally:
        other.rollback()
        other.close()

    assert env.service.activate(ADMIN_A, first.configuration_change_id).accepted

    blocked = env.service.activate(ADMIN_A, second.configuration_change_id)
    assert blocked.accepted is False
    assert blocked.refusal_reason == e3.DUPLICATE_ACTIVE_ASSIGNMENT
    assert len(version_rows(env.db, ASSIGNMENT, "e3-conflict-1")) == 1
    assert version_rows(env.db, ASSIGNMENT, "e3-conflict-2") == []


def test_the_governance_boundary_is_taken_before_any_state_is_read(env) -> None:
    """A refusal at the boundary reports no lifecycle status, because none was read.

    Reporting one would mean the transaction had read governed state before the boundary that
    exists to make every such read consistent.
    """

    proposed = env.service.propose(
        ADMIN_A, proposal(ROLE, "e3-boundary", e3.CHANGE_CREATE, role_payload())
    )
    assert env.service.authorize(ADMIN_A, proposed.configuration_change_id).accepted

    other = SessionLocal()
    try:
        store.lock_governance_publication(other)
        refused = env.service.activate(ADMIN_A, proposed.configuration_change_id)
        assert refused.refusal_reason == e3.CONCURRENT_ACTIVATION_IN_PROGRESS
        assert refused.lifecycle_status is None
        assert refused.evaluation is None
        # Nothing was published and no activation evidence was recorded.
        assert version_rows(env.db, ROLE, "e3-boundary") == []
        assert (
            store.latest_evaluation(
                env.db, proposed.configuration_change_id, e3.STAGE_ACTIVATION
            )
            is None
        )
    finally:
        other.rollback()
        other.close()

    assert env.service.activate(ADMIN_A, proposed.configuration_change_id).accepted


def test_an_update_supersedes_a_nonnumeric_pre_e3_predecessor(env) -> None:
    """PF-1A-E2 defines `object_version` as OPAQUE, and a pre-PF-1A-E3 publication may read
    "v1". Reducing the predecessor question to "the highest number" would make every such object
    permanently unmanageable: no UPDATE could ever state a matching expected predecessor."""

    ctx.bootstrap_version(env.db, ROLE, "e3-opaque", "v1", role_payload("E3_OPAQUE"))
    assert current_version(env.db, ROLE, "e3-opaque") == "v1"

    cid = publish(
        env,
        proposal(
            ROLE, "e3-opaque", e3.CHANGE_UPDATE, role_payload("E3_OPAQUE_UPDATED"),
            previous="v1",
        ),
    )
    rows = version_rows(env.db, ROLE, "e3-opaque")
    assert [row["object_version"] for row in rows] == [
        "v1",
        e3.allocate_object_version("v1", cid),
    ]
    assert [row["role_code"] for row in rows] == ["E3_OPAQUE", "E3_OPAQUE_UPDATED"]
    assert rows[1]["publication_reference_id"] == cid
    # The nonnumeric predecessor is carried through byte for byte, and the successor sorts
    # after it under the comparison the unchanged kernel uses.
    assert rows[1]["object_version"].startswith("v1")
    assert rows[1]["object_version"] > rows[0]["object_version"]


def test_a_deactivate_supersedes_a_uuid_pre_e3_predecessor(env) -> None:
    predecessor = str(uuid.uuid4())
    ctx.bootstrap_version(
        env.db,
        ASSIGNMENT,
        "e3-opaque-assignment",
        predecessor,
        assignment_payload(ctx.ROLE_ORDINARY, person_id=ctx.PLAIN_PERSON),
    )

    cid = publish(
        env,
        proposal(
            ASSIGNMENT,
            "e3-opaque-assignment",
            e3.CHANGE_DEACTIVATE,
            assignment_payload(ctx.ROLE_ORDINARY, person_id=ctx.PLAIN_PERSON),
            previous=predecessor,
        ),
    )
    rows = version_rows(env.db, ASSIGNMENT, "e3-opaque-assignment")
    assert [row["object_version"] for row in rows] == [
        predecessor,
        e3.allocate_object_version(predecessor, cid),
    ]
    assert [row["active_flag"] for row in rows] == [True, False]
    assert rows[1]["object_version"] > rows[0]["object_version"]


def test_successive_publications_are_strictly_lexicographically_increasing(env) -> None:
    """THE ORDERING REGRESSION the unchanged PF-1A-E2 kernel depends on.

    `lineage.py` compares `object_version` lexicographically and requires `published_at` to be
    NON-DECREASING in that order. An allocator that produced merely unique identities would let
    a later publication sort before an earlier one, and the kernel would then read the pair as
    contradictory provenance and fail an otherwise clean resolution CLOSED.

    Publication order is read from the store's append order (`id`), and the identities in that
    order must already be sorted. `published_at` is checked alongside, because it is the
    combination of the two that 11.8.3 actually constrains.
    """

    created = publish(env, proposal(ROLE, "e3-order", e3.CHANGE_CREATE, role_payload("A")))
    identities = [created]
    for index, code in enumerate(("B", "C", "D"), start=1):
        identities.append(
            publish(
                env,
                proposal(
                    ROLE,
                    "e3-order",
                    e3.CHANGE_UPDATE,
                    role_payload(code),
                    hours=1 - (index * 0.1),
                    previous=current_version(env.db, ROLE, "e3-order"),
                ),
            )
        )

    rows = version_rows(env.db, ROLE, "e3-order")
    versions = [row["object_version"] for row in rows]
    assert len(versions) == 4
    assert versions == sorted(versions), "publication order and lexicographic order disagree"
    assert all(later > earlier for earlier, later in zip(versions, versions[1:]))
    assert len(set(versions)) == 4

    published_at = [row["published_at"] for row in rows]
    assert published_at == sorted(published_at), "published_at decreases across the order"

    # Each identity extends its immediate predecessor, which is what makes the ordering hold for
    # ANY predecessor syntax rather than only for ones that happen to look like numbers.
    for earlier, later in zip(versions, versions[1:]):
        assert later.startswith(earlier)
    assert current_version(env.db, ROLE, "e3-order") == versions[-1]


def test_an_already_activated_change_can_never_activate_a_second_time(env) -> None:
    """The governed lifecycle is what prevents a replay, not the identity allocator.

    An allocator anchored on the current maximum would, on a second run, allocate a DIFFERENT
    longer identity rather than colliding, so the replay control has to be - and is - the
    PENDING-to-ACTIVE transition taken under the change row's own lock inside the publishing
    transaction.
    """

    proposed = env.service.propose(
        ADMIN_A, proposal(ROLE, "e3-replay", e3.CHANGE_CREATE, role_payload())
    )
    assert env.service.authorize(ADMIN_A, proposed.configuration_change_id).accepted
    first = env.service.activate(ADMIN_A, proposed.configuration_change_id)
    assert first.accepted

    replay = env.service.activate(ADMIN_A, proposed.configuration_change_id)
    assert replay.accepted is False
    assert replay.refusal_reason == e3.LIFECYCLE_STATE_INVALID
    assert replay.lifecycle_status == e3.LIFECYCLE_ACTIVE

    rows = version_rows(env.db, ROLE, "e3-replay")
    assert len(rows) == 1, "one governed decision published more than one version"
    assert rows[0]["object_version"] == first.published_object_version


def test_an_expected_predecessor_that_is_not_the_current_opaque_identity_is_refused(
    env,
) -> None:
    """The comparison is against the EXACT current identity, not against "something opaque"."""

    ctx.bootstrap_version(env.db, ROLE, "e3-opaque-stale", "v1", role_payload("E3_STALE"))
    publish(
        env,
        proposal(
            ROLE, "e3-opaque-stale", e3.CHANGE_UPDATE, role_payload("E3_MOVED_ON"),
            previous="v1",
        ),
    )

    stale = env.service.propose(
        ADMIN_A,
        proposal(
            ROLE, "e3-opaque-stale", e3.CHANGE_UPDATE, role_payload("E3_TOO_LATE"), hours=0.5,
            previous="v1",
        ),
    )
    assert env.service.authorize(ADMIN_A, stale.configuration_change_id).accepted
    refused = env.service.activate(ADMIN_A, stale.configuration_change_id)
    assert refused.refusal_reason == e3.LINEAGE_PRECONDITION_FAILED
    assert len(version_rows(env.db, ROLE, "e3-opaque-stale")) == 2


def test_a_stale_second_writer_cannot_publish_an_incompatible_next_version(env) -> None:
    """Two changes proposed against the same absent object. The first publishes; the second's
    expected predecessor no longer matches, so it is refused rather than overwriting."""

    first = env.service.propose(
        ADMIN_A, proposal(ROLE, "e3-race", e3.CHANGE_CREATE, role_payload("A"))
    )
    second = env.service.propose(
        ADMIN_A, proposal(ROLE, "e3-race", e3.CHANGE_CREATE, role_payload("B"), hours=0.9)
    )
    assert env.service.authorize(ADMIN_A, first.configuration_change_id).accepted
    assert env.service.authorize(ADMIN_A, second.configuration_change_id).accepted
    assert env.service.activate(ADMIN_A, first.configuration_change_id).accepted

    refused = env.service.activate(ADMIN_A, second.configuration_change_id)
    assert refused.accepted is False
    assert refused.refusal_reason == e3.LINEAGE_PRECONDITION_FAILED

    rows = version_rows(env.db, ROLE, "e3-race")
    assert len(rows) == 1
    assert rows[0]["role_code"] == "A"
    assert rows[0]["publication_reference_id"] == first.configuration_change_id


def test_an_update_whose_expected_predecessor_is_stale_is_refused(env) -> None:
    published = env.service.propose(
        ADMIN_A, proposal(ROLE, "e3-seq", e3.CHANGE_CREATE, role_payload())
    )
    assert env.service.authorize(ADMIN_A, published.configuration_change_id).accepted
    assert env.service.activate(ADMIN_A, published.configuration_change_id).accepted

    stale = env.service.propose(
        ADMIN_A,
        proposal(ROLE, "e3-seq", e3.CHANGE_UPDATE, role_payload("X"), hours=0.9, previous="0009"),
    )
    assert env.service.authorize(ADMIN_A, stale.configuration_change_id).accepted
    refused = env.service.activate(ADMIN_A, stale.configuration_change_id)
    assert refused.refusal_reason == e3.LINEAGE_PRECONDITION_FAILED
    assert len(version_rows(env.db, ROLE, "e3-seq")) == 1


def test_the_authoritative_predecessor_is_not_the_retracted_lexical_maximum(env) -> None:
    """THE PREDECESSOR-VERSUS-ANCHOR REGRESSION.

    Two published versions, `aaa` and `zzz`. `zzz` is retracted, so under PF-1A-E2 semantics it
    is no longer part of the current asserted lineage and cannot be superseded - but it is still
    the lexicographic maximum, still stored, and still provenance the kernel validates.

    The two questions therefore have two different answers, and an implementation that used one
    value for both would be wrong whichever value it picked. Taking the maximum as the
    predecessor would let an UPDATE supersede a version that was withdrawn in error; taking the
    predecessor as the allocation anchor would mint `aaa...`, which sorts BEFORE the stored `zzz`
    and is exactly the contradictory provenance the ordering rule exists to prevent.
    """

    ctx.bootstrap_version(env.db, ROLE, "e3-retracted", "aaa", role_payload("E3_SURVIVING"))
    ctx.bootstrap_version(
        env.db,
        ROLE,
        "e3-retracted",
        "zzz",
        role_payload("E3_MISTAKE"),
        effective_from=hours_ago(24 * 80),
    )
    ctx.bootstrap_retraction(env.db, ROLE, "e3-retracted", "zzz")

    assert current_version(env.db, ROLE, "e3-retracted") == "zzz", "still the lexical maximum"
    assert authoritative_predecessor(env.db, ROLE, "e3-retracted") == "aaa"

    # An UPDATE naming the retracted maximum is refused, however current it looks.
    stale = env.service.propose(
        ADMIN_A,
        proposal(
            ROLE, "e3-retracted", e3.CHANGE_UPDATE, role_payload("E3_FROM_RETRACTED"),
            previous="zzz",
        ),
    )
    assert env.service.authorize(ADMIN_A, stale.configuration_change_id).accepted
    refused = env.service.activate(ADMIN_A, stale.configuration_change_id)
    assert refused.accepted is False
    assert refused.refusal_reason == e3.LINEAGE_PRECONDITION_FAILED
    assert len(version_rows(env.db, ROLE, "e3-retracted")) == 2

    # One naming the surviving authoritative version publishes - and is still allocated from the
    # ALL-TIME anchor, so it sorts after the retracted row too.
    cid = publish(
        env,
        proposal(
            ROLE, "e3-retracted", e3.CHANGE_UPDATE, role_payload("E3_CORRECTED"), hours=0.5,
            previous="aaa",
        ),
    )
    versions = [row["object_version"] for row in version_rows(env.db, ROLE, "e3-retracted")]
    assert versions == ["aaa", "zzz", e3.allocate_object_version("zzz", cid)]
    assert all(versions[-1] > earlier for earlier in versions[:-1])
    assert authoritative_predecessor(env.db, ROLE, "e3-retracted") == versions[-1]


def test_an_expected_predecessor_retracted_after_authorization_is_refused(env) -> None:
    """A retraction between authorization and activation moves the predecessor, and activation
    recomputes it rather than trusting what was true when the change was raised."""

    ctx.bootstrap_version(env.db, ROLE, "e3-late-retraction", "aaa", role_payload("E3_FIRST"))
    ctx.bootstrap_version(
        env.db,
        ROLE,
        "e3-late-retraction",
        "bbb",
        role_payload("E3_SECOND"),
        effective_from=hours_ago(24 * 80),
    )

    proposed = env.service.propose(
        ADMIN_A,
        proposal(
            ROLE, "e3-late-retraction", e3.CHANGE_UPDATE, role_payload("E3_THIRD"),
            previous="bbb",
        ),
    )
    assert env.service.authorize(ADMIN_A, proposed.configuration_change_id).accepted

    ctx.bootstrap_retraction(env.db, ROLE, "e3-late-retraction", "bbb")

    refused = env.service.activate(ADMIN_A, proposed.configuration_change_id)
    assert refused.accepted is False
    assert refused.refusal_reason == e3.LINEAGE_PRECONDITION_FAILED
    # The expectation is stale even though it is STILL the lexicographic maximum.
    assert current_version(env.db, ROLE, "e3-late-retraction") == "bbb"
    assert authoritative_predecessor(env.db, ROLE, "e3-late-retraction") == "aaa"
    assert len(version_rows(env.db, ROLE, "e3-late-retraction")) == 2


def test_a_corrected_nonnumeric_lineage_resolves_its_authoritative_predecessor(env) -> None:
    """Correction is retract-then-republish, and the identities involved are not numbers.

    `v1` is retracted; `v2-corrected` corrects it. The predecessor is the correcting version, the
    retracted one can never be superseded again, and the identity minted next still extends the
    all-time maximum. Nothing here is reachable by an implementation that reads a version
    identifier as a sequence number.
    """

    ctx.bootstrap_version(
        env.db,
        ROLE,
        "e3-corrected",
        "v1",
        role_payload("E3_WRONG"),
        published_at=hours_ago(24 * 60),
    )
    ctx.bootstrap_retraction(
        env.db, ROLE, "e3-corrected", "v1", retracted_at=hours_ago(24 * 50)
    )
    ctx.bootstrap_version(
        env.db,
        ROLE,
        "e3-corrected",
        "v2-corrected",
        role_payload("E3_RIGHT"),
        effective_from=hours_ago(24 * 60),
        published_at=hours_ago(24 * 40),
        corrects_object_version="v1",
    )

    assert current_version(env.db, ROLE, "e3-corrected") == "v2-corrected"
    assert authoritative_predecessor(env.db, ROLE, "e3-corrected") == "v2-corrected"

    stale = env.service.propose(
        ADMIN_A,
        proposal(
            ROLE, "e3-corrected", e3.CHANGE_UPDATE, role_payload("E3_FROM_RETRACTED"),
            previous="v1",
        ),
    )
    assert env.service.authorize(ADMIN_A, stale.configuration_change_id).accepted
    assert (
        env.service.activate(ADMIN_A, stale.configuration_change_id).refusal_reason
        == e3.LINEAGE_PRECONDITION_FAILED
    )

    cid = publish(
        env,
        proposal(
            ROLE, "e3-corrected", e3.CHANGE_UPDATE, role_payload("E3_NEXT"), hours=0.5,
            previous="v2-corrected",
        ),
    )
    versions = [row["object_version"] for row in version_rows(env.db, ROLE, "e3-corrected")]
    assert versions[-1] == e3.allocate_object_version("v2-corrected", cid)
    assert all(versions[-1] > earlier for earlier in versions[:-1])


def test_activation_refuses_when_the_anchor_was_published_after_the_activation_instant(
    env,
) -> None:
    """THE PUBLICATION-TIME MONOTONICITY REGRESSION.

    A newly minted identity always sorts after the object's all-time anchor, and PF-1A-E2-A
    11.8.3 requires `published_at` to be non-decreasing in that order. A clock rollback, a
    restored backup or a mis-set container clock can leave the anchor recorded AHEAD of the
    activation instant, and publishing then would write provenance the unchanged kernel reads as
    contradictory - failing a later, otherwise clean resolution CLOSED.

    The correct outcome is refusal. Advancing or substituting the timestamp to get past the check
    would manufacture exactly the conformance being verified.
    """

    ctx.bootstrap_version(
        env.db,
        ROLE,
        "e3-clock",
        "v1",
        role_payload("E3_CLOCK"),
        published_at=hours_from_now(24),
    )

    proposed = env.service.propose(
        ADMIN_A,
        proposal(
            ROLE, "e3-clock", e3.CHANGE_UPDATE, role_payload("E3_CLOCK_MOVED"), previous="v1"
        ),
    )
    assert env.service.authorize(ADMIN_A, proposed.configuration_change_id).accepted

    refused = env.service.activate(ADMIN_A, proposed.configuration_change_id)
    assert refused.accepted is False
    assert refused.refusal_reason == e3.PUBLICATION_TIMESTAMP_NOT_MONOTONIC
    assert refused.lifecycle_status == e3.LIFECYCLE_PENDING
    assert refused.published_object_version is None

    # No incompatible version was written and no ACTIVE state was reached.
    assert [row["object_version"] for row in version_rows(env.db, ROLE, "e3-clock")] == ["v1"]
    record = store.load_change(env.db, proposed.configuration_change_id)
    assert record["lifecycle_status"] == e3.LIFECYCLE_PENDING
    assert record["published_object_version"] is None
    assert record["activated_at"] is None
    # The refusal is recorded as ordinary governance evidence, not swallowed.
    activation = store.latest_evaluation(
        env.db, proposed.configuration_change_id, e3.STAGE_ACTIVATION
    )
    assert activation["refusal_reason"] == e3.PUBLICATION_TIMESTAMP_NOT_MONOTONIC


def test_the_publication_time_floor_follows_the_retracted_anchor(env) -> None:
    """The floor comes from the ALL-TIME anchor even when that anchor has been retracted.

    The kernel validates recorded provenance across every published version, retracted ones
    included, so a retracted row's `published_at` still constrains what may be published after
    it. The predecessor here is perfectly valid and perfectly stated; it is the clock that
    refuses.
    """

    ctx.bootstrap_version(env.db, ROLE, "e3-clock-retracted", "aaa", role_payload("E3_A"))
    ctx.bootstrap_version(
        env.db,
        ROLE,
        "e3-clock-retracted",
        "zzz",
        role_payload("E3_Z"),
        effective_from=hours_ago(24 * 80),
        published_at=hours_from_now(24),
    )
    ctx.bootstrap_retraction(
        env.db, ROLE, "e3-clock-retracted", "zzz", retracted_at=hours_from_now(25)
    )
    assert authoritative_predecessor(env.db, ROLE, "e3-clock-retracted") == "aaa"

    proposed = env.service.propose(
        ADMIN_A,
        proposal(
            ROLE, "e3-clock-retracted", e3.CHANGE_UPDATE, role_payload("E3_NEXT"),
            previous="aaa",
        ),
    )
    assert env.service.authorize(ADMIN_A, proposed.configuration_change_id).accepted
    refused = env.service.activate(ADMIN_A, proposed.configuration_change_id)
    assert refused.refusal_reason == e3.PUBLICATION_TIMESTAMP_NOT_MONOTONIC
    assert len(version_rows(env.db, ROLE, "e3-clock-retracted")) == 2


def _authorize_and_activate(env, outcome):
    """Take one accepted proposal all the way to the publication decision, single-person."""

    authorized = env.service.authorize(ADMIN_A, outcome.configuration_change_id)
    assert authorized.accepted, authorized.refusal_reason
    return env.service.activate(ADMIN_A, outcome.configuration_change_id)


def test_an_adjacent_successor_publishes_so_the_publication_check_blocks_nothing_ordinary(
    env,
) -> None:
    """THE CONTROL for prospective publication validation.

    A check that refused every append onto a predecessor with a declared end would stop ordinary
    supersession dead. 11.4 has an explicit ADJACENCY branch: a successor whose start EQUALS the
    predecessor's declared end is valid, and it must keep publishing.
    """

    declared_end = hours_ago(6)
    ctx.bootstrap_version(
        env.db,
        ROLE,
        "e3-adjacent",
        "0001",
        role_payload("E3_ADJACENT"),
        effective_from=hours_ago(48),
        declared_effective_to=declared_end,
    )

    cid = publish(
        env,
        proposal(
            ROLE,
            "e3-adjacent",
            e3.CHANGE_UPDATE,
            role_payload("E3_ADJACENT_NEXT"),
            previous="0001",
            effective_from=declared_end,
        ),
    )
    versions = [row["object_version"] for row in version_rows(env.db, ROLE, "e3-adjacent")]
    assert versions == ["0001", e3.allocate_object_version("0001", cid)]
    assert authoritative_predecessor(env.db, ROLE, "e3-adjacent") == versions[-1]


def test_an_append_that_would_overlap_a_still_declared_predecessor_end_is_refused(env) -> None:
    """THE R20 REGRESSION, driven through the real governed service.

    The predecessor declares an end of -2h and is not retracted; the new version starts at -36h.
    PF-1A-E3 APPENDS rather than retracting and republishing, so both stay asserted and 11.4 reads
    the pair as an EXPLICIT OVERLAP. Everything else about this activation is in order - the
    expected predecessor is exactly right, the references exist, the recorded clock is fine, the
    authorization was properly given - which is precisely why the refusal has to be its own answer
    rather than being folded into one of those.
    """

    ctx.bootstrap_version(
        env.db,
        ROLE,
        "e3-overlap",
        "0001",
        role_payload("E3_OVERLAP"),
        effective_from=hours_ago(48),
        declared_effective_to=hours_ago(2),
    )
    proposed = env.service.propose(
        ADMIN_A,
        proposal(
            ROLE,
            "e3-overlap",
            e3.CHANGE_UPDATE,
            role_payload("E3_OVERLAP"),
            previous="0001",
            effective_from=hours_ago(36),
            declared_effective_to=hours_ago(6),
        ),
    )
    assert proposed.accepted, proposed.refusal_reason

    refused = _authorize_and_activate(env, proposed)
    assert refused.accepted is False
    assert refused.refusal_reason == e3.PUBLICATION_LINEAGE_INVALID
    assert refused.published_object_version is None
    assert refused.lifecycle_status == e3.LIFECYCLE_PENDING

    # No append, no ACTIVE state, and the object still resolves exactly as it did before.
    assert [row["object_version"] for row in version_rows(env.db, ROLE, "e3-overlap")] == ["0001"]
    record = store.load_change(env.db, proposed.configuration_change_id)
    assert record["lifecycle_status"] == e3.LIFECYCLE_PENDING
    assert record["published_object_version"] is None
    assert record["activated_at"] is None
    assert authoritative_predecessor(env.db, ROLE, "e3-overlap") == "0001"

    # Governed administration of OTHER objects is unaffected, which is what "the prior lineage was
    # left untouched" has to mean in a whole-configuration authority graph.
    publish(env, proposal(ROLE, "e3-overlap-unrelated", e3.CHANGE_CREATE, role_payload()))


def test_the_publication_check_is_not_hard_coded_to_the_overlap_shape(env) -> None:
    """A STRUCTURALLY DIFFERENT unchanged-E2 defect, refused through the same path.

    Two versions of one asserted lineage sharing an `effective_from` is 11.6's duplicate-start
    pre-check, not an interval overlap: it is a LINEAGE-level defect with no attributed version,
    reached before closure is derived at all. A local "do these intervals overlap?" rule would let
    this append straight through, so it is the case that proves the check delegates to the kernel's
    whole verdict rather than to one anticipated shape.

    The republication is otherwise entirely ordinary - identical payload, unchanged declared scope,
    so it is provably non-increasing and single-person - which is what makes it a fair test of the
    publication check specifically.
    """

    start = hours_ago(24)
    ctx.bootstrap_version(
        env.db,
        ROLE,
        "e3-duplicate-start",
        "0001",
        role_payload("E3_DUPLICATE"),
        effective_from=start,
    )
    proposed = env.service.propose(
        ADMIN_A,
        proposal(
            ROLE,
            "e3-duplicate-start",
            e3.CHANGE_UPDATE,
            role_payload("E3_DUPLICATE"),
            previous="0001",
            effective_from=start,
        ),
    )
    assert proposed.accepted, proposed.refusal_reason
    assert proposed.evaluation.risk.privilege_increasing is False

    refused = _authorize_and_activate(env, proposed)
    assert refused.refusal_reason == e3.PUBLICATION_LINEAGE_INVALID
    assert [
        row["object_version"] for row in version_rows(env.db, ROLE, "e3-duplicate-start")
    ] == ["0001"]
    assert authoritative_predecessor(env.db, ROLE, "e3-duplicate-start") == "0001"


def test_a_deactivate_gets_the_same_publication_validity_rule_as_an_update(env) -> None:
    """DEACTIVATE publishes an immutable version too, so it takes the identical check.

    A `DEACTIVATE` is provably non-increasing by construction - it withdraws a grant - and it would
    be an easy exemption to make. It must not be one: the append it writes can leave exactly the
    same overlapping lineage, and an unpublishable lineage is unpublishable whichever change type
    produced it.
    """

    declared_end = hours_ago(2)
    ctx.bootstrap_version(
        env.db,
        ASSIGNMENT,
        "e3-deactivate-overlap",
        "0001",
        assignment_payload(ctx.ROLE_ORDINARY, person_id=ctx.PLAIN_PERSON),
        effective_from=hours_ago(48),
        declared_effective_to=declared_end,
    )
    proposed = env.service.propose(
        ADMIN_A,
        proposal(
            ASSIGNMENT,
            "e3-deactivate-overlap",
            e3.CHANGE_DEACTIVATE,
            assignment_payload(ctx.ROLE_ORDINARY, person_id=ctx.PLAIN_PERSON),
            previous="0001",
            effective_from=hours_ago(36),
        ),
    )
    assert proposed.accepted, proposed.refusal_reason
    assert proposed.evaluation.risk.privilege_increasing is False

    refused = _authorize_and_activate(env, proposed)
    assert refused.refusal_reason == e3.PUBLICATION_LINEAGE_INVALID
    assert [
        row["object_version"]
        for row in version_rows(env.db, ASSIGNMENT, "e3-deactivate-overlap")
    ] == ["0001"]

    # A DEACTIVATE that leaves a valid lineage still publishes, so nothing was exempted the wrong
    # way either: the same object, superseded from EXACTLY its declared end (11.4's adjacency
    # branch) rather than from before it.
    cid = publish(
        env,
        proposal(
            ASSIGNMENT,
            "e3-deactivate-overlap",
            e3.CHANGE_DEACTIVATE,
            assignment_payload(ctx.ROLE_ORDINARY, person_id=ctx.PLAIN_PERSON),
            previous="0001",
            effective_from=declared_end,
        ),
    )
    rows = version_rows(env.db, ASSIGNMENT, "e3-deactivate-overlap")
    assert [row["object_version"] for row in rows] == [
        "0001",
        e3.allocate_object_version("0001", cid),
    ]
    assert [row["active_flag"] for row in rows] == [True, False]


def test_a_create_onto_fully_retracted_material_is_validated_against_that_material(env) -> None:
    """The CREATE path is prospectively validated too, over the object's COMPLETE material.

    An object whose only version has been retracted has an EMPTY current asserted lineage, so a
    CREATE is the correct governed action - but the retracted row is still stored, still
    dereferenceable and still provenance the kernel validates. The prospective evaluation therefore
    sees it, and the publication is checked against the whole material rather than against the
    current asserted subset.
    """

    ctx.bootstrap_version(env.db, ROLE, "e3-create-after-retraction", "aaa", role_payload("E3_A"))
    ctx.bootstrap_retraction(env.db, ROLE, "e3-create-after-retraction", "aaa")
    assert authoritative_predecessor(env.db, ROLE, "e3-create-after-retraction") is None

    cid = publish(
        env,
        proposal(
            ROLE, "e3-create-after-retraction", e3.CHANGE_CREATE, role_payload("E3_FRESH")
        ),
    )
    versions = [
        row["object_version"] for row in version_rows(env.db, ROLE, "e3-create-after-retraction")
    ]
    # Allocated from the ALL-TIME anchor, so it still sorts after the retracted row.
    assert versions == ["aaa", e3.allocate_object_version("aaa", cid)]
    assert versions[-1] > versions[0]


def test_a_contradictory_published_lineage_fails_every_governed_action_closed(env) -> None:
    """An unestablishable lineage is never read as "this object has nothing".

    Two versions of one object sharing an `effective_from` is a kernel-detected contradiction
    with no single current answer. The governed action refuses with an unavailable context rather
    than guessing which of them is current - and the refusal reaches even a change about a
    completely different object, because the authority graph as a whole could not be established.
    """

    ctx.bootstrap_version(env.db, ROLE, "e3-contradictory", "aaa", role_payload("E3_ONE"))
    ctx.bootstrap_version(env.db, ROLE, "e3-contradictory", "bbb", role_payload("E3_TWO"))

    refused = env.service.propose(
        ADMIN_A, proposal(ROLE, "e3-unrelated-object", e3.CHANGE_CREATE, role_payload())
    )
    assert refused.accepted is False
    assert refused.refusal_reason == e3.AUTHORITY_CONTEXT_UNAVAILABLE
    assert refused.configuration_change_id is None
    assert "CONTEXT_UNRESOLVED" in refused.evaluation.risk.derivation


def test_a_failure_before_commit_leaves_no_publication_and_no_false_active_state(
    env, monkeypatch
) -> None:
    proposed = env.service.propose(
        ADMIN_A, proposal(ROLE, "e3-boom", e3.CHANGE_CREATE, role_payload())
    )
    assert env.service.authorize(ADMIN_A, proposed.configuration_change_id).accepted

    def explode(*args, **kwargs):
        raise RuntimeError("injected failure after the version row was written")

    monkeypatch.setattr(store, "record_activation", explode)
    with pytest.raises(RuntimeError):
        env.service.activate(ADMIN_A, proposed.configuration_change_id)
    monkeypatch.undo()

    assert version_rows(env.db, ROLE, "e3-boom") == []
    record = store.load_change(env.db, proposed.configuration_change_id)
    assert record["lifecycle_status"] == e3.LIFECYCLE_PENDING
    assert record["published_object_version"] is None
    assert (
        store.latest_evaluation(
            env.db, proposed.configuration_change_id, e3.STAGE_ACTIVATION
        )
        is None
    )

    # The change is still activatable afterwards, so the rollback left it usable.
    assert env.service.activate(ADMIN_A, proposed.configuration_change_id).accepted
