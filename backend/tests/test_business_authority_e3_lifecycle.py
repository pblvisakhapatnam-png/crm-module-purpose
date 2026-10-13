"""PF-1A-E3: the governed lifecycle and the preventive self-escalation invariant."""

from __future__ import annotations

import pytest
from sqlalchemy import text

from app.modules.authorization.business_authority import configuration_contract as e3
from app.modules.authorization.business_authority import (
    configuration_repository as ctx_store,
)
from app.modules.authorization.business_authority.configuration_domain import (
    ConfigurationGovernanceError,
)
from tests.fixtures import pf_1a_e3_reference_context as ctx
from tests.fixtures.pf_1a_e3_reference_context import (  # noqa: F401
    ADMIN_A,
    ADMIN_B,
    PLAIN,
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

AUTHORITY = e3.BUSINESS_AUTHORITY
ROLE = e3.BUSINESS_AUTHORITY_ROLE
RULE = e3.BUSINESS_AUTHORITY_RULE
ASSIGNMENT = e3.BUSINESS_AUTHORITY_ASSIGNMENT


def _protected(env):
    """An UPDATE of the protected authority itself: protected-meta-authority-affecting."""

    return env.service.propose(
        ADMIN_A,
        proposal(
            AUTHORITY,
            ctx.AUTH_PROTECTED,
            e3.CHANGE_UPDATE,
            {
                "authority_code": ctx.PROTECTED_AUTHORITY_CODE,
                "authority_name": "Renamed governance capability",
                "description": "",
                "is_protected_meta_authority": True,
            },
            previous="0001",
        ),
    )


def test_governed_create_update_and_deactivate_work_for_all_four_families(env) -> None:
    publish(env, proposal(ROLE, "e3-nr", e3.CHANGE_CREATE, role_payload()))
    publish(
        env,
        proposal(
            AUTHORITY,
            "e3-na",
            e3.CHANGE_CREATE,
            {
                "authority_code": "E3-NEW-ORDINARY",
                "authority_name": "New ordinary",
                "description": "",
                "is_protected_meta_authority": False,
            },
            hours=1.1,
        ),
    )
    publish(
        env,
        proposal(
            RULE,
            "e3-nu",
            e3.CHANGE_CREATE,
            {
                "business_authority_role_object_id": "e3-nr",
                "business_authority_object_id": "e3-na",
                "scope_type": "GLOBAL",
                "scope_id": None,
                "parameter_evaluator_type": "NONE",
                "parameter_payload": None,
            },
            hours=1.2,
        ),
    )
    publish(
        env,
        proposal(
            ASSIGNMENT,
            "e3-ns",
            e3.CHANGE_CREATE,
            assignment_payload("e3-nr", person_id=ctx.PLAIN_PERSON),
            hours=1.3,
        ),
    )
    publish(
        env,
        proposal(
            ROLE, "e3-nr", e3.CHANGE_UPDATE, role_payload("E3_RENAMED"), hours=0.9,
            previous=current_version(env.db, ROLE, "e3-nr"),
        ),
    )
    publish(
        env,
        proposal(
            ROLE, "e3-nr", e3.CHANGE_DEACTIVATE, role_payload("E3_RENAMED"), hours=0.8,
            previous=current_version(env.db, ROLE, "e3-nr"),
        ),
    )
    publish(
        env,
        proposal(
            ASSIGNMENT,
            "e3-ns",
            e3.CHANGE_DEACTIVATE,
            assignment_payload("e3-nr", person_id=ctx.PLAIN_PERSON),
            hours=0.7,
            previous=current_version(env.db, ASSIGNMENT, "e3-ns"),
        ),
    )

    rows = version_rows(env.db, ROLE, "e3-nr")
    # Three DISTINCT opaque identities in publication order, strictly increasing under the
    # comparison the unchanged PF-1A-E2 kernel uses. Their spelling is deliberately not
    # asserted: nothing may depend on a version identifier looking like a sequence.
    versions = [row["object_version"] for row in rows]
    assert len(versions) == 3 and len(set(versions)) == 3
    assert versions == sorted(versions)
    assert [row["active_flag"] for row in rows] == [True, True, False]
    assert len(version_rows(env.db, AUTHORITY, "e3-na")) == 1
    assert len(version_rows(env.db, RULE, "e3-nu")) == 1
    assert [r["active_flag"] for r in version_rows(env.db, ASSIGNMENT, "e3-ns")] == [True, False]


def test_an_ordinary_unrelated_non_protected_change_remains_single_person(env) -> None:
    outcome = env.service.propose(
        ADMIN_A,
        proposal(
            ASSIGNMENT,
            "e3-ord",
            e3.CHANGE_CREATE,
            assignment_payload(ctx.ROLE_ORDINARY, person_id=ctx.PLAIN_PERSON),
        ),
    )
    assert outcome.accepted, outcome.refusal_reason
    risk = outcome.evaluation.risk
    assert (risk.is_self_affecting, risk.affects_protected_meta_authority) == (False, False)
    assert risk.authorization_required is False

    authorized = env.service.authorize(ADMIN_A, outcome.configuration_change_id)
    assert authorized.accepted
    assert authorized.evaluation.authorizer_is_different_person is False
    assert env.service.activate(ADMIN_A, outcome.configuration_change_id).accepted


def test_the_initiator_can_never_authorize_their_own_escalating_change(env) -> None:
    proposed = _protected(env)
    assert proposed.accepted, proposed.refusal_reason
    assert proposed.evaluation.risk.authorization_required is True

    refused = env.service.authorize(ADMIN_A, proposed.configuration_change_id)
    assert refused.accepted is False
    assert refused.refusal_reason == e3.SAME_PERSON_AUTHORIZATION_FORBIDDEN

    blocked = env.service.activate(ADMIN_A, proposed.configuration_change_id)
    assert blocked.refusal_reason == e3.AUTHORIZATION_MISSING
    assert blocked.lifecycle_status == e3.LIFECYCLE_PENDING
    assert len(version_rows(env.db, AUTHORITY, ctx.AUTH_PROTECTED)) == 1


def test_a_different_but_ineligible_person_cannot_authorize(env) -> None:
    proposed = _protected(env)
    refused = env.service.authorize(PLAIN, proposed.configuration_change_id)
    assert refused.accepted is False
    assert refused.refusal_reason == e3.AUTHORIZER_NOT_ELIGIBLE
    assert refused.evaluation.authorizer_is_different_person is True


def test_a_different_currently_eligible_holder_can_authorize_and_it_then_activates(env) -> None:
    proposed = _protected(env)
    authorized = env.service.authorize(ADMIN_B, proposed.configuration_change_id)
    assert authorized.accepted, authorized.refusal_reason
    assert authorized.evaluation.authorizer_is_different_person is True

    activated = env.service.activate(ADMIN_A, proposed.configuration_change_id)
    assert activated.accepted, activated.refusal_reason
    assert activated.published_object_version == e3.allocate_object_version(
        "0001", proposed.configuration_change_id
    )
    assert activated.published_object_version != "0001", "it superseded, it did not overwrite"
    assert activated.published_object_version > "0001", "the successor must sort after it"


def test_protected_impact_is_derived_from_the_data_flag_not_the_code_string(env) -> None:
    """The decoy carries the suggestive administration CODE with the flag FALSE, and the
    protected authority carries an unremarkable code with the flag TRUE."""

    decoy = env.service.propose(
        ADMIN_A,
        proposal(
            AUTHORITY,
            ctx.AUTH_DECOY,
            e3.CHANGE_UPDATE,
            {
                "authority_code": ctx.DECOY_AUTHORITY_CODE,
                "authority_name": "Still not protected",
                "description": "",
                "is_protected_meta_authority": False,
            },
            previous="0001",
        ),
    )
    assert decoy.accepted, decoy.refusal_reason
    assert decoy.evaluation.risk.affects_protected_meta_authority is False
    assert decoy.evaluation.risk.authorization_required is False
    assert _protected(env).evaluation.risk.affects_protected_meta_authority is True


def test_setting_the_protected_flag_and_clearing_it_are_both_protected(env) -> None:
    setting = env.service.propose(
        ADMIN_A,
        proposal(
            AUTHORITY,
            "e3-new-protected",
            e3.CHANGE_CREATE,
            {
                "authority_code": "E3-BRAND-NEW-PROTECTED",
                "authority_name": "New protected capability",
                "description": "",
                "is_protected_meta_authority": True,
            },
        ),
    )
    assert setting.evaluation.risk.affects_protected_meta_authority is True

    clearing = env.service.propose(
        ADMIN_A,
        proposal(
            AUTHORITY,
            ctx.AUTH_PROTECTED,
            e3.CHANGE_UPDATE,
            {
                "authority_code": ctx.PROTECTED_AUTHORITY_CODE,
                "authority_name": "Quietly unprotected",
                "description": "",
                "is_protected_meta_authority": False,
            },
            hours=1.1,
            previous="0001",
        ),
    )
    assert clearing.evaluation.risk.affects_protected_meta_authority is True
    assert clearing.evaluation.risk.authorization_required is True


def test_a_self_affecting_privilege_increase_requires_independence(env) -> None:
    """Isolated from protection: the initiator broadens their OWN ordinary assignment."""

    ctx.bootstrap_version(
        env.db,
        ASSIGNMENT,
        "e3-own",
        "0001",
        assignment_payload(
            ctx.ROLE_ORDINARY, person_id=ctx.ADMIN_A_PERSON, scope_id="branch-west"
        ),
    )
    proposed = env.service.propose(
        ADMIN_A,
        proposal(
            ASSIGNMENT,
            "e3-own",
            e3.CHANGE_UPDATE,
            assignment_payload(ctx.ROLE_ORDINARY, person_id=ctx.ADMIN_A_PERSON),
            previous="0001",
        ),
    )
    risk = proposed.evaluation.risk
    assert (risk.is_self_affecting, risk.affects_protected_meta_authority) == (True, False)
    assert risk.privilege_increasing is True
    assert risk.authorization_required is True


def _own_ordinary_assignment(env, object_id: str = "e3-eff-own") -> None:
    """An ORDINARY role the initiator holds through a live, currently effective assignment.

    Ordinary rather than protected on purpose: what these tests isolate is whether the CURRENTLY
    EFFECTIVE version is recognised, so nothing below may be decided by the protection flag.
    """

    ctx.bootstrap_version(
        env.db,
        ASSIGNMENT,
        object_id,
        "0001",
        assignment_payload(ctx.ROLE_ORDINARY, person_id=ctx.ADMIN_A_PERSON),
    )


def _rename_the_ordinary_role(env):
    """A change that is self-affecting exactly when the initiator holds ROLE_ORDINARY now."""

    return env.service.propose(
        ADMIN_A,
        proposal(
            ROLE,
            ctx.ROLE_ORDINARY,
            e3.CHANGE_UPDATE,
            role_payload("E3_RENAMED_ORDINARY"),
            previous="0001",
        ),
    )


def test_a_future_effective_inactive_successor_does_not_erase_the_current_self_holder(
    env,
) -> None:
    """THE EFFECTIVENESS REGRESSION, in its most direct form.

    The initiator holds ROLE_ORDINARY through an assignment that is effective TODAY. A
    later-published successor of that same assignment is INACTIVE and takes effect in a month.

    A governed-write view that ranked rows by publication order would read only that successor,
    conclude the initiator holds nothing, and let them rename their own role single-handed. The
    successor changes nothing about today: `lineage.evaluate_lineage` closes the live version at
    the successor's start, which is a month away, so the live version is still the one effective
    at `as_of` and the change is still self-affecting - at proposal, at authorization AND at the
    final activation-time recomputation.
    """

    _own_ordinary_assignment(env)
    ctx.bootstrap_version(
        env.db,
        ASSIGNMENT,
        "e3-eff-own",
        "0002",
        assignment_payload(ctx.ROLE_ORDINARY, person_id=ctx.ADMIN_A_PERSON),
        active_flag=False,
        effective_from=hours_from_now(24 * 30),
    )

    proposed = _rename_the_ordinary_role(env)
    assert proposed.accepted, proposed.refusal_reason
    risk = proposed.evaluation.risk
    assert risk.is_self_affecting is True
    assert "INITIATOR_HOLDS_THE_TARGET_ROLE" in risk.derivation
    assert risk.authorization_required is True

    refused = env.service.authorize(ADMIN_A, proposed.configuration_change_id)
    assert refused.accepted is False
    assert refused.refusal_reason == e3.SAME_PERSON_AUTHORIZATION_FORBIDDEN

    blocked = env.service.activate(ADMIN_A, proposed.configuration_change_id)
    assert blocked.accepted is False
    assert blocked.refusal_reason == e3.AUTHORIZATION_MISSING
    assert len(version_rows(env.db, ROLE, ctx.ROLE_ORDINARY)) == 1

    # An independent currently-eligible holder is what unblocks it, and the activation-time
    # recomputation still classifies it as self-affecting rather than quietly downgrading it.
    assert env.service.authorize(ADMIN_B, proposed.configuration_change_id).accepted
    activated = env.service.activate(ADMIN_A, proposed.configuration_change_id)
    assert activated.accepted, activated.refusal_reason
    assert activated.evaluation.risk.is_self_affecting is True


def test_a_future_effective_reassignment_does_not_erase_the_current_self_holder(env) -> None:
    """The same regression with the successor ACTIVE but reassigned to someone else.

    Publication order says "this assignment now targets the outsider". Effectiveness says the
    initiator still holds it for another month. The second is the one that decides whether the
    initiator can approve their own change today.
    """

    _own_ordinary_assignment(env)
    ctx.bootstrap_version(
        env.db,
        ASSIGNMENT,
        "e3-eff-own",
        "0002",
        assignment_payload(ctx.ROLE_ORDINARY, person_id=ctx.OUTSIDER_PERSON),
        effective_from=hours_from_now(24 * 30),
    )

    proposed = _rename_the_ordinary_role(env)
    assert proposed.evaluation.risk.is_self_affecting is True
    assert proposed.evaluation.risk.authorization_required is True
    assert (
        env.service.authorize(ADMIN_A, proposed.configuration_change_id).refusal_reason
        == e3.SAME_PERSON_AUTHORIZATION_FORBIDDEN
    )


def test_a_future_effective_rule_successor_does_not_erase_the_current_protected_linkage(
    env,
) -> None:
    """The protected half of the same regression.

    `RULE_ADMIN` grants the PROTECTED meta-authority from the governance role today. A
    later-published successor re-points that rule at an ORDINARY authority, a month from now. A
    publication-order view would read only the successor and conclude the governance role carries
    nothing protected, so editing that role would stop being a protected change.
    """

    ctx.bootstrap_version(
        env.db,
        RULE,
        ctx.RULE_ADMIN,
        "0002",
        {
            "business_authority_role_object_id": ctx.ROLE_ADMIN,
            "business_authority_object_id": ctx.AUTH_ORDINARY,
            "scope_type": "GLOBAL",
            "scope_id": None,
            "parameter_evaluator_type": "NONE",
            "parameter_payload": None,
        },
        effective_from=hours_from_now(24 * 30),
    )

    proposed = env.service.propose(
        ADMIN_A,
        proposal(
            ROLE,
            ctx.ROLE_ADMIN,
            e3.CHANGE_UPDATE,
            role_payload("E3_RENAMED_GOVERNANCE_ROLE"),
            previous="0001",
        ),
    )
    assert proposed.accepted, proposed.refusal_reason
    risk = proposed.evaluation.risk
    assert risk.affects_protected_meta_authority is True
    assert "TARGET_ROLE_CARRIES_A_PROTECTED_META_AUTHORITY" in risk.derivation
    assert risk.authorization_required is True
    assert (
        env.service.authorize(ADMIN_A, proposed.configuration_change_id).refusal_reason
        == e3.SAME_PERSON_AUTHORIZATION_FORBIDDEN
    )


def test_an_already_effective_inactive_successor_does_release_the_former_holder(env) -> None:
    """THE CONTROL, and it matters as much as the three regressions above.

    The correction must not turn every edit into a two-person process - ADR-033 warns against
    exactly that. Here the successor is inactive AND already effective, so the initiator
    genuinely holds nothing now, the change is genuinely ordinary, and it publishes
    single-person.
    """

    _own_ordinary_assignment(env, "e3-eff-lapsed")
    ctx.bootstrap_version(
        env.db,
        ASSIGNMENT,
        "e3-eff-lapsed",
        "0002",
        assignment_payload(ctx.ROLE_ORDINARY, person_id=ctx.ADMIN_A_PERSON),
        active_flag=False,
        effective_from=hours_ago(2),
    )

    proposed = _rename_the_ordinary_role(env)
    assert proposed.accepted, proposed.refusal_reason
    risk = proposed.evaluation.risk
    assert risk.is_self_affecting is False
    assert risk.authorization_required is False
    assert env.service.authorize(ADMIN_A, proposed.configuration_change_id).accepted
    assert env.service.activate(ADMIN_A, proposed.configuration_change_id).accepted


def test_authorization_recomputes_and_detects_proposal_time_drift(env) -> None:
    """Ordinary at proposal; the position's incumbent then becomes the initiator, so the same
    person authorizing it is now refused."""

    proposed = env.service.propose(
        ADMIN_A,
        proposal(
            ASSIGNMENT,
            "e3-seat",
            e3.CHANGE_CREATE,
            assignment_payload(ctx.ROLE_ORDINARY, position_id=ctx.SEAT_POSITION),
        ),
    )
    assert proposed.accepted, proposed.refusal_reason
    assert proposed.evaluation.risk.is_self_affecting is False

    env.hr.incumbents[ctx.SEAT_POSITION] = ctx.ADMIN_A_PERSON

    refused = env.service.authorize(ADMIN_A, proposed.configuration_change_id)
    assert refused.evaluation.risk.is_self_affecting is True
    assert refused.evaluation.dependencies_current is False
    assert refused.refusal_reason == e3.SAME_PERSON_AUTHORIZATION_FORBIDDEN


def test_activation_recomputes_and_refuses_a_change_that_became_escalating(env) -> None:
    """Ordinary when raised AND when authorized; an incumbency change then makes it
    self-affecting before activation."""

    proposed = env.service.propose(
        ADMIN_A,
        proposal(
            ASSIGNMENT,
            "e3-seat",
            e3.CHANGE_CREATE,
            assignment_payload(ctx.ROLE_ORDINARY, position_id=ctx.SEAT_POSITION),
        ),
    )
    authorized = env.service.authorize(ADMIN_A, proposed.configuration_change_id)
    assert authorized.accepted
    assert authorized.evaluation.risk.authorization_required is False

    env.hr.incumbents[ctx.SEAT_POSITION] = ctx.ADMIN_A_PERSON

    refused = env.service.activate(ADMIN_A, proposed.configuration_change_id)
    assert refused.refusal_reason == e3.RISK_INCREASED_SINCE_AUTHORIZATION
    assert refused.lifecycle_status == e3.LIFECYCLE_PENDING
    assert version_rows(env.db, ASSIGNMENT, "e3-seat") == []


def test_an_authorizer_who_loses_the_authority_before_activation_no_longer_counts(env) -> None:
    proposed = _protected(env)
    assert env.service.authorize(ADMIN_B, proposed.configuration_change_id).accepted

    # Synthetic bootstrap revokes ADMIN-B's own protected assignment.
    ctx.bootstrap_version(
        env.db,
        ASSIGNMENT,
        ctx.ASSIGN_ADMIN_B,
        "0002",
        assignment_payload(ctx.ROLE_ADMIN, person_id=ctx.ADMIN_B_PERSON),
        active_flag=False,
        effective_from=hours_ago(2),
    )

    refused = env.service.activate(ADMIN_A, proposed.configuration_change_id)
    assert refused.refusal_reason == e3.AUTHORIZER_NO_LONGER_ELIGIBLE
    assert refused.lifecycle_status == e3.LIFECYCLE_PENDING


def test_a_refused_later_attempt_cannot_lend_its_context_to_an_earlier_authorization(
    env,
) -> None:
    """THE EVIDENCE-BINDING REGRESSION.

    B authorizes at context F1. The published configuration then drifts to F2. A - who is the
    initiator and therefore can never authorize this change - attempts authorization at F2 and
    is refused, which durably records ITS OWN evaluation, carrying F2's fingerprint and F2's
    freshly recomputed risk verdict.

    If activation read "the latest AUTHORIZATION evaluation" it would now find F2's evidence
    sitting beside B's still-recorded authorizer identity, conclude the context had not drifted,
    and publish a protected change that nobody ever authorized in the context it publishes into:
    an approver from one context, a fingerprint from another. Activation must instead load the
    evaluation B's authorization is BOUND to, see F1, and refuse.

    An INELIGIBLE third party's refused attempt is included for the same reason: neither kind of
    refusal may refresh the evidence activation relies on.
    """

    proposed = _protected(env)
    authorized = env.service.authorize(ADMIN_B, proposed.configuration_change_id)
    assert authorized.accepted, authorized.refusal_reason
    bound_fingerprint = authorized.evaluation.dependency_fingerprint

    # F1 -> F2: unrelated published configuration changes. B stays eligible throughout.
    ctx.bootstrap_version(env.db, ROLE, "e3-drifted", "0001", role_payload("E3_DRIFTED"))

    same_person = env.service.authorize(ADMIN_A, proposed.configuration_change_id)
    assert same_person.accepted is False
    assert same_person.refusal_reason == e3.SAME_PERSON_AUTHORIZATION_FORBIDDEN
    ineligible = env.service.authorize(PLAIN, proposed.configuration_change_id)
    assert ineligible.accepted is False
    assert ineligible.refusal_reason == e3.AUTHORIZER_NOT_ELIGIBLE

    # Both refusals recorded their own evaluations, and one of them IS now the latest.
    stages = [
        row["evaluation_stage"]
        for row in ctx_store.load_evaluations(env.db, proposed.configuration_change_id)
    ]
    assert stages.count(e3.STAGE_AUTHORIZATION) == 3
    latest = ctx_store.latest_evaluation(
        env.db, proposed.configuration_change_id, e3.STAGE_AUTHORIZATION
    )
    assert latest["authorization_satisfied"] is False
    assert latest["dependency_fingerprint"] != bound_fingerprint

    # Neither refusal touched the recorded authorizer or the evaluation it is bound to.
    record = ctx_store.load_change(env.db, proposed.configuration_change_id)
    assert record["authorized_by_person_id"] == ctx.ADMIN_B_PERSON
    assert record["authorized_by_actor_user_public_id"] == ctx.ADMIN_B_ACTOR
    bound = ctx_store.load_bound_evaluation(
        env.db, proposed.configuration_change_id, record["authorized_evaluation_id"]
    )
    assert bound["authorization_satisfied"] is True
    assert bound["dependency_fingerprint"] == bound_fingerprint

    # Activation therefore stays blocked on the authorization B actually gave, at F1.
    refused = env.service.activate(ADMIN_A, proposed.configuration_change_id)
    assert refused.accepted is False
    assert refused.refusal_reason == e3.AUTHORIZATION_CONTEXT_DRIFTED
    assert len(version_rows(env.db, AUTHORITY, ctx.AUTH_PROTECTED)) == 1

    # Only a fresh SUCCESSFUL authorization by an eligible different person, at F2, unblocks it.
    reauthorized = env.service.authorize(ADMIN_B, proposed.configuration_change_id)
    assert reauthorized.accepted, reauthorized.refusal_reason
    rebound = ctx_store.load_change(env.db, proposed.configuration_change_id)
    assert rebound["authorized_evaluation_id"] != record["authorized_evaluation_id"]
    assert env.service.activate(ADMIN_A, proposed.configuration_change_id).accepted


def test_activation_refuses_when_the_bound_authorization_evidence_cannot_be_verified(
    env,
) -> None:
    """The binding is VERIFIED at activation, not merely present.

    Repointing the binding at a REFUSED evaluation - the shape a tampered or corrupted record
    would take - must refuse, and must refuse as an evidence-integrity failure rather than
    silently as a missing approval.
    """

    proposed = _protected(env)
    assert env.service.authorize(ADMIN_B, proposed.configuration_change_id).accepted
    refused_attempt = env.service.authorize(PLAIN, proposed.configuration_change_id)
    assert refused_attempt.accepted is False

    refused_evaluation = [
        row
        for row in ctx_store.load_evaluations(
            env.db, proposed.configuration_change_id, stage=e3.STAGE_AUTHORIZATION
        )
        if row["authorization_satisfied"] is False
    ][-1]
    env.db.execute(
        text(
            f"UPDATE {e3.CONFIGURATION_CHANGE_TABLE} SET authorized_evaluation_id = :eid "
            "WHERE configuration_change_id = :cid"
        ),
        {"eid": refused_evaluation["evaluation_id"], "cid": proposed.configuration_change_id},
    )
    env.db.commit()

    blocked = env.service.activate(ADMIN_A, proposed.configuration_change_id)
    assert blocked.refusal_reason == e3.AUTHORIZATION_EVIDENCE_UNVERIFIABLE
    assert len(version_rows(env.db, AUTHORITY, ctx.AUTH_PROTECTED)) == 1

    # An absent binding refuses too, and stays distinguishable from a verifiable one.
    env.db.execute(
        text(
            f"UPDATE {e3.CONFIGURATION_CHANGE_TABLE} SET authorized_evaluation_id = NULL "
            "WHERE configuration_change_id = :cid"
        ),
        {"cid": proposed.configuration_change_id},
    )
    env.db.commit()
    assert (
        env.service.activate(ADMIN_A, proposed.configuration_change_id).refusal_reason
        == e3.AUTHORIZATION_EVIDENCE_UNVERIFIABLE
    )


def test_another_changes_successful_authorization_cannot_satisfy_this_one(env) -> None:
    """The binding resolves by evaluation identity AND owning change, never by identity alone."""

    borrower = _protected(env)
    donor = env.service.propose(
        ADMIN_A,
        proposal(ROLE, "e3-donor", e3.CHANGE_CREATE, role_payload("E3_DONOR"), hours=1.4),
    )
    donor_authorization = env.service.authorize(ADMIN_B, donor.configuration_change_id)
    assert donor_authorization.accepted

    donor_record = ctx_store.load_change(env.db, donor.configuration_change_id)
    env.db.execute(
        text(
            f"UPDATE {e3.CONFIGURATION_CHANGE_TABLE} SET "
            "authorized_by_person_id = :person, "
            "authorized_by_actor_user_public_id = :actor, "
            "authorized_evaluation_id = :eid "
            "WHERE configuration_change_id = :cid"
        ),
        {
            "person": ctx.ADMIN_B_PERSON,
            "actor": ctx.ADMIN_B_ACTOR,
            "eid": donor_record["authorized_evaluation_id"],
            "cid": borrower.configuration_change_id,
        },
    )
    env.db.commit()

    blocked = env.service.activate(ADMIN_A, borrower.configuration_change_id)
    assert blocked.refusal_reason == e3.AUTHORIZATION_EVIDENCE_UNVERIFIABLE
    assert len(version_rows(env.db, AUTHORITY, ctx.AUTH_PROTECTED)) == 1


def _own_assignment_with_interval(env, *, effective_from, declared_effective_to=None):
    """A published assignment the initiator holds, over a DECLARED interval.

    Deliberately an ORDINARY authority, so nothing below is decided by protection: what is being
    isolated is temporal broadening of a self-affecting assignment.
    """

    ctx.bootstrap_version(
        env.db,
        ASSIGNMENT,
        "e3-temporal",
        "0001",
        assignment_payload(ctx.ROLE_ORDINARY, person_id=ctx.ADMIN_A_PERSON),
        effective_from=effective_from,
        declared_effective_to=declared_effective_to,
    )


def _identical_payload_update(env, *, effective_from, declared_effective_to=None):
    """An UPDATE whose PAYLOAD is byte-identical, varying only the declared interval."""

    return env.service.propose(
        ADMIN_A,
        proposal(
            ASSIGNMENT,
            "e3-temporal",
            e3.CHANGE_UPDATE,
            assignment_payload(ctx.ROLE_ORDINARY, person_id=ctx.ADMIN_A_PERSON),
            previous="0001",
            effective_from=effective_from,
            declared_effective_to=declared_effective_to,
        ),
    )


def test_an_identical_payload_over_an_unchanged_interval_stays_single_person(env) -> None:
    """The CONTROL for the four temporal cases below.

    ADR-033 warns explicitly against turning every configuration edit into a two-person process,
    so a genuinely unchanged republication must remain provably non-increasing.
    """

    start, end = hours_ago(48), hours_ago(2)
    _own_assignment_with_interval(env, effective_from=start, declared_effective_to=end)
    outcome = _identical_payload_update(env, effective_from=start, declared_effective_to=end)

    assert outcome.accepted, outcome.refusal_reason
    risk = outcome.evaluation.risk
    assert risk.is_self_affecting is True
    assert risk.privilege_increasing is False
    assert risk.authorization_required is False


def test_an_identical_payload_starting_earlier_is_a_privilege_increase(env) -> None:
    """It grants the same authority over time it did not previously cover."""

    _own_assignment_with_interval(
        env, effective_from=hours_ago(48), declared_effective_to=hours_ago(2)
    )
    outcome = _identical_payload_update(
        env, effective_from=hours_ago(72), declared_effective_to=hours_ago(2)
    )

    risk = outcome.evaluation.risk
    assert (risk.is_self_affecting, risk.privilege_increasing) == (True, True)
    assert risk.authorization_required is True
    assert "TEMPORAL_SCOPE_STARTS_EARLIER" in risk.derivation

    refused = env.service.authorize(ADMIN_A, outcome.configuration_change_id)
    assert refused.refusal_reason == e3.SAME_PERSON_AUTHORIZATION_FORBIDDEN


def test_an_identical_payload_ending_later_is_a_privilege_increase(env) -> None:
    _own_assignment_with_interval(
        env, effective_from=hours_ago(48), declared_effective_to=hours_ago(24)
    )
    outcome = _identical_payload_update(
        env, effective_from=hours_ago(48), declared_effective_to=hours_ago(1)
    )

    risk = outcome.evaluation.risk
    assert (risk.is_self_affecting, risk.privilege_increasing) == (True, True)
    assert risk.authorization_required is True
    assert "TEMPORAL_SCOPE_ENDS_LATER" in risk.derivation


def test_an_identical_payload_dropping_a_declared_end_is_a_privilege_increase(env) -> None:
    """Finite -> unbounded: the largest broadening of all, and the easiest to mistake for
    housekeeping because not one payload field changes."""

    _own_assignment_with_interval(
        env, effective_from=hours_ago(48), declared_effective_to=hours_ago(24)
    )
    outcome = _identical_payload_update(
        env, effective_from=hours_ago(48), declared_effective_to=None
    )

    risk = outcome.evaluation.risk
    assert (risk.is_self_affecting, risk.privilege_increasing) == (True, True)
    assert risk.authorization_required is True
    assert "TEMPORAL_SCOPE_BECOMES_UNBOUNDED" in risk.derivation


def test_an_identical_payload_over_a_strictly_narrower_interval_is_not_an_increase(
    env,
) -> None:
    """The PROVEN narrowing: a later start AND an earlier end, payload unchanged.

    TWO SEPARATE QUESTIONS, AND THIS TEST IS THE PLACE THEY ARE MOST EASILY CONFUSED.

    The RISK question - does this grant more than what it supersedes? - is correctly answered NO.
    Classifying a narrowing as an increase would be conservative in the useless direction: it would
    demand a second person to REDUCE someone's own authority, which is exactly the "every edit
    becomes two-person" outcome ADR-033 warns against. That classification is asserted below and is
    deliberately unchanged.

    The PUBLICATION question - may the resulting immutable lineage be written at all? - is a
    different question with a different answer here, and an earlier revision of this test wrongly
    read the first as proof of the second. PF-1A-E3's UPDATE APPENDS rather than retracting and
    republishing, so the predecessor keeps its declared end of -2h while the new version starts at
    -36h, and PF-1A-E2-A 11.4 reads that pair as an EXPLICIT OVERLAP. Publishing it would fail
    every later resolution of this object closed and - the authority graph being
    whole-configuration - would block governed administration outright, with no correction or
    retraction path in this package able to repair it.

    So the change is legitimately single-person AND legitimately unpublishable, and the refusal is
    reported as the publication-validity failure it is rather than as a risk verdict.
    """

    _own_assignment_with_interval(
        env, effective_from=hours_ago(48), declared_effective_to=hours_ago(2)
    )
    outcome = _identical_payload_update(
        env, effective_from=hours_ago(36), declared_effective_to=hours_ago(6)
    )

    risk = outcome.evaluation.risk
    assert risk.is_self_affecting is True
    assert risk.privilege_increasing is False
    assert risk.authorization_required is False
    assert "TEMPORAL_SCOPE_IS_UNCHANGED_OR_NARROWED" not in risk.derivation
    assert "PUBLISHED_CONTENT_AND_TEMPORAL_SCOPE_ARE_UNCHANGED_OR_NARROWED" in risk.derivation

    # Single-person authorization is genuinely RECORDED, so the change reaches the publication
    # decision on its own merits rather than being stopped by an authorization question.
    authorized = env.service.authorize(ADMIN_A, outcome.configuration_change_id)
    assert authorized.accepted, authorized.refusal_reason
    assert authorized.evaluation.risk.privilege_increasing is False

    refused = env.service.activate(ADMIN_A, outcome.configuration_change_id)
    assert refused.accepted is False
    assert refused.refusal_reason == e3.PUBLICATION_LINEAGE_INVALID
    assert refused.published_object_version is None
    assert refused.lifecycle_status == e3.LIFECYCLE_PENDING
    # The activation-time risk verdict is still "not an increase": the refusal did NOT come from
    # reclassifying the narrowing, which would have been the wrong fix.
    assert refused.evaluation.risk.privilege_increasing is False

    # Nothing was appended, nothing became ACTIVE, and the prior lineage is exactly as it was.
    assert [row["object_version"] for row in version_rows(env.db, ASSIGNMENT, "e3-temporal")] == [
        "0001"
    ]
    record = ctx_store.load_change(env.db, outcome.configuration_change_id)
    assert record["lifecycle_status"] == e3.LIFECYCLE_PENDING
    assert record["published_object_version"] is None
    assert record["activated_at"] is None
    assert authoritative_predecessor(env.db, ASSIGNMENT, "e3-temporal") == "0001"

    # The refusal is durable governance evidence, not a swallowed exception.
    activation = ctx_store.latest_evaluation(
        env.db, outcome.configuration_change_id, e3.STAGE_ACTIVATION
    )
    assert activation["refusal_reason"] == e3.PUBLICATION_LINEAGE_INVALID
    assert activation["authorization_satisfied"] is False


def test_a_narrowing_that_leaves_a_valid_lineage_stays_single_person_and_publishes(
    env,
) -> None:
    """THE CONTROL for the publication check, and it matters as much as the refusal above.

    A correction that refused every narrowing would be a different defect, not extra safety. Here
    the predecessor declares NO end, so the new version's later start simply CLOSES it at that
    start under 11.4 - an ordinary, valid supersession. The interval is still narrowed in
    entitlement terms (a later start and a newly declared end), so the change is still provably
    non-increasing and still single-person, and it genuinely publishes.

    The narrowing rule therefore remains usable rather than theoretical; what the correction blocks
    is the specific APPEND that would contradict a still-declared predecessor end, not narrowing.
    """

    _own_assignment_with_interval(
        env, effective_from=hours_ago(48), declared_effective_to=None
    )
    outcome = _identical_payload_update(
        env, effective_from=hours_ago(36), declared_effective_to=hours_ago(6)
    )

    risk = outcome.evaluation.risk
    assert risk.is_self_affecting is True
    assert risk.privilege_increasing is False
    assert risk.authorization_required is False
    assert "PUBLISHED_CONTENT_AND_TEMPORAL_SCOPE_ARE_UNCHANGED_OR_NARROWED" in risk.derivation

    assert env.service.authorize(ADMIN_A, outcome.configuration_change_id).accepted
    activated = env.service.activate(ADMIN_A, outcome.configuration_change_id)
    assert activated.accepted, activated.refusal_reason

    rows = version_rows(env.db, ASSIGNMENT, "e3-temporal")
    assert [row["object_version"] for row in rows] == [
        "0001",
        activated.published_object_version,
    ]
    # The row that was validated is the row that was written: interval, provenance and active
    # semantics all as the governed activation proposed them.
    published = rows[1]
    assert published["publication_reference_type"] == "CONFIGURATION_CHANGE"
    assert published["publication_reference_id"] == outcome.configuration_change_id
    assert published["corrects_object_version"] is None
    assert published["active_flag"] is True
    assert published["declared_effective_to"] is not None
    assert authoritative_predecessor(env.db, ASSIGNMENT, "e3-temporal") == (
        activated.published_object_version
    )


def test_an_unbounded_predecessor_cannot_be_broadened_at_its_end(env) -> None:
    """An already-unbounded end cannot be extended, so only the start can broaden."""

    _own_assignment_with_interval(env, effective_from=hours_ago(48), declared_effective_to=None)
    unchanged = _identical_payload_update(
        env, effective_from=hours_ago(48), declared_effective_to=None
    )
    assert unchanged.evaluation.risk.privilege_increasing is False

    narrowed = env.service.propose(
        ADMIN_A,
        proposal(
            ASSIGNMENT,
            "e3-temporal-2",
            e3.CHANGE_CREATE,
            assignment_payload(ctx.ROLE_ORDINARY, person_id=ctx.PLAIN_PERSON),
            hours=5,
        ),
    )
    # A CREATE is never provably non-increasing, whatever its interval looks like.
    assert narrowed.evaluation.risk.privilege_increasing is True
    assert "NOT_PROVABLY_NON_INCREASING" in narrowed.evaluation.risk.derivation


def test_material_drift_after_authorization_rejects_the_stale_authorization(env) -> None:
    proposed = _protected(env)
    assert env.service.authorize(ADMIN_B, proposed.configuration_change_id).accepted

    # Unrelated published configuration changes; the authorizer stays eligible.
    ctx.bootstrap_version(env.db, ROLE, "e3-unrelated", "0001", role_payload("E3_UNRELATED"))

    refused = env.service.activate(ADMIN_A, proposed.configuration_change_id)
    assert refused.refusal_reason == e3.AUTHORIZATION_CONTEXT_DRIFTED

    # Fresh independent authorization under the new context lets it proceed.
    assert env.service.authorize(ADMIN_B, proposed.configuration_change_id).accepted
    assert env.service.activate(ADMIN_A, proposed.configuration_change_id).accepted


def test_unavailable_hr_or_actor_state_fails_closed(env) -> None:
    ctx.bootstrap_version(
        env.db,
        ASSIGNMENT,
        "e3-seat-existing",
        "0001",
        assignment_payload(ctx.ROLE_ORDINARY, position_id=ctx.SEAT_POSITION),
    )
    env.hr.incumbency_available = False
    refused = env.service.propose(
        ADMIN_A, proposal(ROLE, "e3-x", e3.CHANGE_CREATE, role_payload())
    )
    assert refused.accepted is False
    assert refused.refusal_reason == e3.AUTHORITY_CONTEXT_UNAVAILABLE
    assert refused.configuration_change_id is None

    env.hr.incumbency_available = True
    env.actors.available = False
    refused = env.service.propose(
        ADMIN_A, proposal(ROLE, "e3-x", e3.CHANGE_CREATE, role_payload())
    )
    assert refused.refusal_reason == e3.AUTHORITY_CONTEXT_UNAVAILABLE


def test_the_proposal_time_flags_cannot_authorize_or_activate_by_themselves(env) -> None:
    """Rewriting the stored preliminary flags to "ordinary" changes nothing, because
    authorization and activation both recompute."""

    proposed = _protected(env)
    env.db.execute(
        text(
            f"UPDATE {e3.CONFIGURATION_CHANGE_TABLE} SET "
            "proposal_time_is_self_affecting = FALSE, "
            "proposal_time_affects_protected_meta_authority = FALSE, "
            "proposal_time_privilege_increasing = FALSE, "
            "proposal_time_authorization_required = FALSE "
            "WHERE configuration_change_id = :cid"
        ),
        {"cid": proposed.configuration_change_id},
    )
    env.db.commit()

    refused = env.service.authorize(ADMIN_A, proposed.configuration_change_id)
    assert refused.evaluation.risk.authorization_required is True
    assert refused.refusal_reason == e3.SAME_PERSON_AUTHORIZATION_FORBIDDEN
    assert env.service.activate(ADMIN_A, proposed.configuration_change_id).accepted is False
    assert len(version_rows(env.db, AUTHORITY, ctx.AUTH_PROTECTED)) == 1


def test_a_duplicate_active_assignment_is_rejected_at_the_governed_write_boundary(env) -> None:
    payload = assignment_payload(ctx.ROLE_ORDINARY, person_id=ctx.PLAIN_PERSON)
    publish(env, proposal(ASSIGNMENT, "e3-a1", e3.CHANGE_CREATE, payload))
    duplicate = env.service.propose(
        ADMIN_A, proposal(ASSIGNMENT, "e3-a2", e3.CHANGE_CREATE, payload, hours=0.5)
    )
    assert duplicate.accepted is False
    assert duplicate.refusal_reason == e3.DUPLICATE_ACTIVE_ASSIGNMENT


def test_a_rejected_change_is_durable_and_can_never_activate(env) -> None:
    proposed = _protected(env)
    rejected = env.service.reject(ADMIN_B, proposed.configuration_change_id, "not required")
    assert rejected.accepted
    assert rejected.lifecycle_status == e3.LIFECYCLE_REJECTED

    stored = (
        env.db.execute(
            text(
                f"SELECT lifecycle_status, rejection_reason FROM "
                f"{e3.CONFIGURATION_CHANGE_TABLE} WHERE configuration_change_id = :cid"
            ),
            {"cid": proposed.configuration_change_id},
        )
        .mappings()
        .one()
    )
    assert stored["lifecycle_status"] == e3.LIFECYCLE_REJECTED
    assert stored["rejection_reason"] == "not required"

    blocked = env.service.activate(ADMIN_B, proposed.configuration_change_id)
    assert blocked.refusal_reason == e3.LIFECYCLE_STATE_INVALID


def test_a_reference_to_a_missing_object_is_refused(env) -> None:
    refused = env.service.propose(
        ADMIN_A,
        proposal(
            ASSIGNMENT,
            "e3-dangling",
            e3.CHANGE_CREATE,
            assignment_payload("e3-role-that-does-not-exist", person_id=ctx.PLAIN_PERSON),
        ),
    )
    assert refused.refusal_reason == e3.REFERENCED_OBJECT_MISSING


def test_a_structurally_invalid_request_raises_rather_than_being_recorded(env) -> None:
    with pytest.raises(ConfigurationGovernanceError):
        env.service.propose(
            ADMIN_A,
            proposal(
                ASSIGNMENT,
                "e3-bad",
                e3.CHANGE_CREATE,
                {
                    "business_authority_role_object_id": ctx.ROLE_ORDINARY,
                    "person_id": ctx.PLAIN_PERSON,
                    "position_id": "also-a-position",
                    "scope_type": "GLOBAL",
                    "scope_id": None,
                },
            ),
        )
    with pytest.raises(ConfigurationGovernanceError):
        env.service.propose(ADMIN_A, proposal(ROLE, "e3-r", e3.CHANGE_UPDATE, role_payload()))
