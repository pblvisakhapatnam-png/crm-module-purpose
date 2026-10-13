"""PF-1A-E3: an E3 publication is consumed through the UNCHANGED E2 provider and kernel."""

from __future__ import annotations

from datetime import datetime, timezone

from app.modules.authorization.business_authority import configuration_contract as e3
from app.modules.authorization.business_authority.contract import (
    OUTCOME_ALLOW,
    OUTCOME_DENY,
    STATUS_RESOLVED,
)
from app.modules.authorization.business_authority.domain import (
    AuthenticatedActor,
    AuthorityResolutionRequest,
    BusinessContext,
)
from app.modules.authorization.business_authority.kernel import resolve
from tests.fixtures import pf_1a_e3_reference_context as ctx
from tests.fixtures.pf_1a_e3_reference_context import (  # noqa: F401
    ADMIN_A,
    assignment_payload,
    current_version,
    env,
    proposal,
    publish,
    version_rows,
)

ASSIGNMENT = e3.BUSINESS_AUTHORITY_ASSIGNMENT


def _resolve(env, actor_id: str, authority_code: str):
    """Drive the UNCHANGED kernel against the UNCHANGED PostgreSQL provider."""

    return resolve(
        request=AuthorityResolutionRequest(
            authenticated_actor=AuthenticatedActor(actor_user_public_id=actor_id),
            authority_code=authority_code,
            business_context=BusinessContext(),
        ),
        as_of=datetime.now(timezone.utc),
        authority_configuration_port=env.provider,
        actor_person_port=env.actors,
        hr_reference_port=env.hr,
    )


def test_the_person_holds_nothing_before_the_governed_change_activates(env) -> None:
    before = _resolve(env, ctx.PLAIN_ACTOR, ctx.ORDINARY_AUTHORITY_CODE)
    assert before.outcome == OUTCOME_DENY
    assert before.resolution_status == STATUS_RESOLVED


def test_the_unchanged_kernel_grants_authority_from_an_e3_published_assignment(env) -> None:
    cid = publish(
        env,
        proposal(
            ASSIGNMENT,
            "e3-compat",
            e3.CHANGE_CREATE,
            assignment_payload(ctx.ROLE_ORDINARY, person_id=ctx.PLAIN_PERSON),
            hours=2,
        ),
    )
    after = _resolve(env, ctx.PLAIN_ACTOR, ctx.ORDINARY_AUTHORITY_CODE)
    assert after.outcome == OUTCOME_ALLOW
    assert after.resolution_status == STATUS_RESOLVED
    assert after.qualifying_paths

    # The version the kernel consumed is the one E3 published, with E3 provenance. Its identity
    # is the OPAQUE one E3 minted - the kernel neither parses it nor cares what it looks like.
    published = env.provider.get_published_version(
        ASSIGNMENT, "e3-compat", e3.allocate_object_version(None, cid)
    )
    assert published.publication_reference_type == "CONFIGURATION_CHANGE"
    assert published.publication_reference_id == cid
    assert published.payload.person_id == ctx.PLAIN_PERSON


def test_an_e3_deactivation_removes_the_grant_through_the_unchanged_kernel(env) -> None:
    publish(
        env,
        proposal(
            ASSIGNMENT,
            "e3-compat",
            e3.CHANGE_CREATE,
            assignment_payload(ctx.ROLE_ORDINARY, person_id=ctx.PLAIN_PERSON),
            hours=3,
        ),
    )
    assert _resolve(env, ctx.PLAIN_ACTOR, ctx.ORDINARY_AUTHORITY_CODE).outcome == OUTCOME_ALLOW

    publish(
        env,
        proposal(
            ASSIGNMENT,
            "e3-compat",
            e3.CHANGE_DEACTIVATE,
            assignment_payload(ctx.ROLE_ORDINARY, person_id=ctx.PLAIN_PERSON),
            hours=2,
            previous=current_version(env.db, ASSIGNMENT, "e3-compat"),
        ),
    )
    after = _resolve(env, ctx.PLAIN_ACTOR, ctx.ORDINARY_AUTHORITY_CODE)
    assert after.outcome == OUTCOME_DENY
    assert after.resolution_status == STATUS_RESOLVED
    # Both versions remain stored: deactivation publishes, it never deletes.
    assert len(version_rows(env.db, ASSIGNMENT, "e3-compat")) == 2
