"""The governed Configuration Change lifecycle and its atomic publication (PF-1A-E3).

FOUR OPERATIONS, ONE INVARIANT.

    propose     records a pending change and PRELIMINARY risk evidence.
    authorize   RECOMPUTES risk against current state and, if the preventive rule is satisfied,
                records who authorized it AND binds that record to the exact successful
                evaluation which established it.
    reject      closes a pending change permanently, as a durable audit record.
    activate    RECOMPUTES risk AGAIN, atomically with publication, behind the governance-wide
                publication boundary; asks the UNCHANGED PF-1A-E2-A kernel whether the object's
                complete lineage would still be valid WITH the exact version it is about to append;
                and only then appends exactly one immutable version to the published store under
                CONFIGURATION_CHANGE provenance.

THE INVARIANT: no stored risk boolean is ever read as final. `proposal_time_*` is audit
history. The authorization-time verdict is audit history by the time activation runs. Each
stage rebuilds the whole authoritative context from scratch and decides on that. This closes
the drift gap: a change that was ordinary when raised, and ordinary when authorized, does not
activate as ordinary once it has become self-affecting or protected.

WHY ELIGIBILITY GOES THROUGH THE UNCHANGED KERNEL. "May this person administer authority
configuration?" is a business-authority resolution question, and this package must not answer
it a second way. The service asks the PF-1A-E2-A kernel, with the authoritative actor-person
and HR providers its composition was given, and then dereferences the exact authority version
the kernel cited to read the DATA-DRIVEN protection flag off it. A kernel result that fails
closed makes the whole governed action fail closed; it never degrades to "not eligible, carry
on".

ONE AUTHORIZATION, BOUND. A successful authorization is persisted as one self-contained fact:
the authorizer's identity together with the identity of the exact successful AUTHORIZATION
evaluation that established it. Activation loads THAT evaluation and no other. Reading "the most
recent AUTHORIZATION evaluation" instead would let a later REFUSED attempt - which legitimately
records its own evaluation, against its own freshly recomputed context - lend its fingerprint and
risk verdict to an approver who never saw that context, assembling an authorization that never
happened out of two halves that separately did.

ONE INSTANT PER OPERATION. Each operation captures a single timezone-aware UTC instant and uses
it for every kernel call, every HR lookup, every evaluation record and, on activation, for
`published_at`. No component consults a second clock.
"""

from __future__ import annotations

import uuid
from collections.abc import Mapping, Sequence
from dataclasses import replace
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.modules.authorization.business_authority import configuration_policy as policy
from app.modules.authorization.business_authority import configuration_repository as store
from app.modules.authorization.business_authority.configuration_contract import (
    AUTHORITY_CONTEXT_UNAVAILABLE,
    BUSINESS_AUTHORITY,
    BUSINESS_AUTHORITY_ASSIGNMENT,
    CHANGE_CREATE,
    CHANGE_DEACTIVATE,
    CHANGE_PAYLOAD_FIELDS,
    CHANGE_REJECTED_BY_GOVERNANCE_DECISION,
    CHANGE_TYPES,
    CHANGE_UPDATE,
    CONCURRENT_ACTIVATION_IN_PROGRESS,
    DUPLICATE_ACTIVE_ASSIGNMENT,
    INITIATOR_NOT_ELIGIBLE,
    LIFECYCLE_ACTIVE,
    LIFECYCLE_PENDING,
    LIFECYCLE_REJECTED,
    LIFECYCLE_STATE_INVALID,
    OBJECT_FAMILIES,
    OUTCOME_REFUSED,
    PUBLICATION_REFERENCE_TYPE,
    REFERENCED_OBJECT_MISSING,
    STABLE_REFERENCE_FIELDS,
    STAGE_ACTIVATION,
    STAGE_AUTHORIZATION,
    STAGE_PROPOSAL,
    STAGE_REJECTION,
    SUCCESSFUL_EVALUATION_OUTCOMES,
    allocate_object_version,
)
from app.modules.authorization.business_authority.configuration_domain import (
    AuthorityContext,
    ConfigurationChangeOutcome,
    ConfigurationChangeProposal,
    ConfigurationGovernanceError,
    GovernanceEvaluation,
    PublishedRow,
)
from app.modules.authorization.business_authority.contract import (
    OUTCOME_ALLOW,
    STATUS_FAIL_CLOSED,
)
from app.modules.authorization.business_authority.domain import (
    AuthenticatedActor,
    AuthorityResolutionRequest,
    BusinessContext,
)
from app.modules.authorization.business_authority.kernel import resolve


def _now() -> datetime:
    """The ONE server-controlled clock read this module performs.

    A module-level function purely so a deterministic test can prove one governed operation
    consults it exactly once.
    """

    return datetime.now(timezone.utc)


def _new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4()}"


class GovernedAuthorityConfigurationService:
    """Proposal, authorization, rejection and atomic activation.

    Constructing this service requires all three authoritative dependencies. There is
    deliberately no default, no fallback and no optional argument: a service that could be
    built without an actor-person or HR provider would be a service that could authorize a
    configuration change without knowing who was acting.
    """

    def __init__(
        self,
        db: Session,
        *,
        authority_configuration_port: Any,
        actor_person_port: Any,
        hr_reference_port: Any,
        hr_staleness_threshold_seconds: int | None = None,
    ) -> None:
        absent = [
            name
            for name, value in (
                ("authority_configuration_port", authority_configuration_port),
                ("actor_person_port", actor_person_port),
                ("hr_reference_port", hr_reference_port),
            )
            if value is None
        ]
        if absent:
            raise ConfigurationGovernanceError(
                "governed authority configuration requires every authoritative dependency; "
                f"absent: {sorted(absent)}"
            )
        self._db = db
        self._configuration_port = authority_configuration_port
        self._actor_person_port = actor_person_port
        self._hr_reference_port = hr_reference_port
        self._staleness = hr_staleness_threshold_seconds

    # -- context --------------------------------------------------------------

    def _load_context(
        self, as_of: datetime, extra_positions: Sequence[str] = ()
    ) -> AuthorityContext:
        """Rebuild the whole authoritative context from scratch, as at ONE instant.

        The authority graph is DERIVED, not read: the raw material goes to the unchanged
        PF-1A-E2-A lineage kernel, which decides which version of each object is effective at
        `as_of` and which is the authoritative predecessor. An object whose lineage that kernel
        cannot establish lands in `unresolved`, and every governed operation then refuses with
        `AUTHORITY_CONTEXT_UNAVAILABLE` rather than proceeding on a graph nobody could verify.
        """

        rows, assertions = store.load_published_material(self._db)
        codes = store.load_protected_candidate_codes(self._db)

        positions: set[str] = {str(value) for value in extra_positions if value}
        for row in rows:
            if row.object_family == BUSINESS_AUTHORITY_ASSIGNMENT and not row.retracted:
                if row.payload.get("position_id") is not None:
                    positions.add(str(row.payload["position_id"]))

        incumbency: dict[str, str | None] = {}
        unresolved: list[str] = []
        for position_id in sorted(positions):
            lookup = self._hr_reference_port.get_incumbency(position_id, as_of)
            if getattr(lookup, "is_ok", False) and lookup.value is not None:
                incumbency[position_id] = getattr(lookup.value, "person_id", None)
            else:
                # A position whose current occupant cannot be established could be the very
                # thing that makes a change self-affecting, so the whole governed action fails
                # closed rather than guessing.
                incumbency[position_id] = None
                unresolved.append(f"INCUMBENCY:{position_id}")

        effective_state = policy.derive_effective_state(rows, assertions, as_of)
        unresolved.extend(effective_state.unresolved)

        fingerprint = policy.dependency_fingerprint(rows, assertions, incumbency, codes)
        reference: dict[str, Any] = {
            "as_of": as_of.isoformat(),
            "published_version_count": len(rows),
            "published_versions": sorted(
                f"{row.object_family}/{row.object_id}@{row.object_version}" for row in rows
            ),
            "retraction_assertion_count": len(assertions),
            "effective_object_count": len(effective_state.effective_rows),
            "incumbency": {key: incumbency[key] for key in sorted(incumbency)},
            "protected_candidate_codes": list(codes),
            "dependency_fingerprint": fingerprint,
        }
        return AuthorityContext(
            as_of=as_of,
            rows=rows,
            incumbent_person_by_position=incumbency,
            protected_candidate_codes=codes,
            unresolved=tuple(sorted(unresolved)),
            fingerprint=fingerprint,
            context_reference=reference,
            retractions=assertions,
            effective_state=effective_state,
        )

    # -- eligibility -----------------------------------------------------------

    def _person_for(self, actor_user_public_id: str, as_of: datetime) -> str | None:
        lookup = self._actor_person_port.resolve_actor_person(actor_user_public_id, as_of)
        if not getattr(lookup, "is_ok", False) or lookup.value is None:
            return None
        return getattr(lookup.value, "person_id", None)

    def _holds_protected(
        self, actor_user_public_id: str, as_of: datetime, context: AuthorityContext
    ) -> tuple[bool, bool]:
        """(eligible, resolvable).

        `resolvable` is false when the kernel failed closed on any candidate, or when a cited
        authority version could not be dereferenced. A caller must treat a false `resolvable`
        as an unavailable context, never as "no".
        """

        eligible = False
        for authority_code in context.protected_candidate_codes:
            result = resolve(
                request=AuthorityResolutionRequest(
                    authenticated_actor=AuthenticatedActor(
                        actor_user_public_id=actor_user_public_id
                    ),
                    authority_code=authority_code,
                    business_context=BusinessContext(),
                    hr_staleness_threshold_seconds=self._staleness,
                ),
                as_of=as_of,
                authority_configuration_port=self._configuration_port,
                actor_person_port=self._actor_person_port,
                hr_reference_port=self._hr_reference_port,
            )
            if result.resolution_status == STATUS_FAIL_CLOSED:
                return False, False
            if result.outcome != OUTCOME_ALLOW:
                continue
            cited = result.established_state.requested_authority
            if cited is None:
                return False, False
            try:
                version = self._configuration_port.get_published_version(
                    BUSINESS_AUTHORITY, cited.object_id, cited.object_version
                )
            except KeyError:
                return False, False
            if getattr(version.payload, "is_protected_meta_authority", None) is True:
                eligible = True
        return eligible, True

    def _actor_state(
        self, actor: AuthenticatedActor, as_of: datetime, context: AuthorityContext
    ) -> tuple[str | None, bool, bool]:
        person_id = self._person_for(actor.actor_user_public_id, as_of)
        if person_id is None:
            return None, False, False
        eligible, resolvable = self._holds_protected(
            actor.actor_user_public_id, as_of, context
        )
        return person_id, eligible, resolvable

    # -- persistence helpers ----------------------------------------------------

    def _persist(self, configuration_change_id: str, e: GovernanceEvaluation) -> str:
        """Append ONE evaluation and return its identity.

        The identity is returned rather than discarded because a successful authorization must
        be BOUND to the exact evaluation that established it, in the same transaction that
        records the authorizer.
        """

        evaluation_id = _new_id("cce")
        store.insert_evaluation(
            self._db,
            {
                "evaluation_id": evaluation_id,
                "configuration_change_id": configuration_change_id,
                "evaluation_stage": e.stage,
                "evaluated_at": e.evaluated_at,
                "acting_person_id": e.acting_person_id,
                "acting_actor_user_public_id": e.acting_actor_user_public_id,
                "recomputed_is_self_affecting": e.risk.is_self_affecting,
                "recomputed_affects_protected_meta_authority": (
                    e.risk.affects_protected_meta_authority
                ),
                "recomputed_privilege_increasing": e.risk.privilege_increasing,
                "recomputed_authorization_required": e.risk.authorization_required,
                "authorizer_eligible": e.authorizer_eligible,
                "authorizer_is_different_person": e.authorizer_is_different_person,
                "dependencies_current": e.dependencies_current,
                "authorization_satisfied": e.authorization_satisfied,
                "outcome": e.outcome,
                "refusal_reason": e.refusal_reason,
                "dependency_fingerprint": e.dependency_fingerprint,
                "context_reference": dict(e.context_reference),
                "risk_derivation": list(e.risk.derivation),
            },
        )
        return evaluation_id

    def _validate(self, proposal: ConfigurationChangeProposal) -> None:
        if proposal.configuration_object_family not in OBJECT_FAMILIES:
            raise ConfigurationGovernanceError(
                f"unknown configuration object family: "
                f"{proposal.configuration_object_family!r}"
            )
        if proposal.change_type not in CHANGE_TYPES:
            raise ConfigurationGovernanceError(f"unknown change type: {proposal.change_type!r}")
        if not proposal.configuration_object_id:
            raise ConfigurationGovernanceError("a configuration object identity is required")
        unknown = sorted(
            set(proposal.change_payload)
            - set(CHANGE_PAYLOAD_FIELDS[proposal.configuration_object_family])
        )
        if unknown:
            raise ConfigurationGovernanceError(f"unknown change payload fields: {unknown}")
        if proposal.effective_from.utcoffset() is None:
            raise ConfigurationGovernanceError("effective_from must be timezone-aware")
        if (
            proposal.declared_effective_to is not None
            and proposal.declared_effective_to <= proposal.effective_from
        ):
            raise ConfigurationGovernanceError(
                "declared_effective_to must be later than effective_from"
            )
        if proposal.configuration_object_family == BUSINESS_AUTHORITY_ASSIGNMENT:
            person = proposal.change_payload.get("person_id")
            position = proposal.change_payload.get("position_id")
            if (person is None) == (position is None):
                raise ConfigurationGovernanceError(
                    "an assignment must name exactly one of person_id or position_id"
                )
        if proposal.change_type in (CHANGE_UPDATE, CHANGE_DEACTIVATE) and not (
            proposal.previous_object_version_expected
        ):
            raise ConfigurationGovernanceError(
                "an UPDATE or DEACTIVATE must state the version it expects to supersede"
            )

    def _references_present(self, proposal: ConfigurationChangeProposal) -> bool:
        for name, family in STABLE_REFERENCE_FIELDS[proposal.configuration_object_family]:
            value = proposal.change_payload.get(name)
            if value is None:
                continue
            if not store.stable_identity_exists(self._db, family, str(value)):
                return False
        return True

    @staticmethod
    def _positions(proposal: ConfigurationChangeProposal) -> tuple[str, ...]:
        value = proposal.change_payload.get("position_id")
        return (str(value),) if value else ()

    @staticmethod
    def _proposal_from(record: Mapping[str, Any]) -> ConfigurationChangeProposal:
        return ConfigurationChangeProposal(
            configuration_object_family=record["configuration_object_family"],
            configuration_object_id=record["configuration_object_id"],
            change_type=record["change_type"],
            change_payload=dict(record["change_payload"] or {}),
            effective_from=record["effective_from"],
            declared_effective_to=record["declared_effective_to"],
            previous_object_version_expected=record["previous_object_version_expected"],
        )

    def _bound_authorization(self, record: Mapping[str, Any]) -> dict[str, Any] | None:
        """The ONE successful AUTHORIZATION evaluation this change's authorizer is bound to.

        Returns None - never a "close enough" substitute - when the binding is absent or fails
        any check below, and the caller then refuses. Every check is a way the stored evidence
        could fail to be what the authorizer fields claim:

            the change carries no authorizer, or no bound evaluation identity;
            the bound identity resolves to nothing FOR THIS CHANGE;
            the bound evaluation is not an AUTHORIZATION at all;
            it did not conclude that authorization was satisfied;
            its outcome is not one of the successful outcomes;
            its acting identities are not the recorded authorizer's.

        There is deliberately no fallback to the latest AUTHORIZATION evaluation. That fallback
        is precisely the defect this method exists to remove.
        """

        evaluation_id = record["authorized_evaluation_id"]
        person_id = record["authorized_by_person_id"]
        actor_id = record["authorized_by_actor_user_public_id"]
        if not evaluation_id or person_id is None or not actor_id:
            return None

        bound = store.load_bound_evaluation(
            self._db, record["configuration_change_id"], str(evaluation_id)
        )
        if bound is None:
            return None
        if bound["evaluation_stage"] != STAGE_AUTHORIZATION:
            return None
        if bound["authorization_satisfied"] is not True:
            return None
        if bound["outcome"] not in SUCCESSFUL_EVALUATION_OUTCOMES:
            return None
        if bound["acting_person_id"] != person_id:
            return None
        if bound["acting_actor_user_public_id"] != actor_id:
            return None
        return bound

    def _terminal(self, record: Mapping[str, Any], reason: str) -> ConfigurationChangeOutcome:
        return ConfigurationChangeOutcome(
            accepted=False,
            configuration_change_id=record["configuration_change_id"],
            lifecycle_status=record["lifecycle_status"],
            evaluation=None,
            refusal_reason=reason,
        )

    def _unavailable(self, stage, context, person, actor, cid, status, reason=None):
        evaluation = policy.unresolved_context_evaluation(
            stage=stage, context=context, person=person, actor=actor
        )
        if reason is not None:
            evaluation = replace(evaluation, refusal_reason=reason)
        if cid is not None:
            self._persist(cid, evaluation)
            self._db.commit()
        else:
            self._db.rollback()
        return ConfigurationChangeOutcome(
            accepted=False,
            configuration_change_id=cid,
            lifecycle_status=status,
            evaluation=evaluation,
            refusal_reason=evaluation.refusal_reason,
        )

    # -- propose ----------------------------------------------------------------

    def propose(
        self, actor: AuthenticatedActor, proposal: ConfigurationChangeProposal
    ) -> ConfigurationChangeOutcome:
        self._validate(proposal)
        as_of = _now()
        try:
            context = self._load_context(as_of, self._positions(proposal))
            person_id, eligible, resolvable = self._actor_state(actor, as_of, context)
            if person_id is None or not resolvable or not context.is_resolved:
                return self._unavailable(
                    STAGE_PROPOSAL, context, person_id, actor.actor_user_public_id, None, None
                )

            blocking: str | None = None
            if not eligible:
                blocking = INITIATOR_NOT_ELIGIBLE
            elif not self._references_present(proposal):
                blocking = REFERENCED_OBJECT_MISSING
            elif policy.conflicting_active_assignment(proposal, context) is not None:
                blocking = DUPLICATE_ACTIVE_ASSIGNMENT

            risk = policy.classify_risk(proposal, context, person_id)
            evaluation = policy.evaluate_proposal(
                context=context,
                risk=risk,
                person=person_id,
                actor=actor.actor_user_public_id,
                eligible=eligible,
                blocking_reason=blocking,
            )
            if evaluation.outcome == OUTCOME_REFUSED:
                # Nothing is persisted for a refused proposal: there is no governed record to
                # attach evidence to, and creating one would manufacture a pending change
                # nobody was permitted to raise.
                self._db.rollback()
                return ConfigurationChangeOutcome(
                    accepted=False,
                    configuration_change_id=None,
                    lifecycle_status=None,
                    evaluation=evaluation,
                    refusal_reason=evaluation.refusal_reason,
                )

            cid = _new_id("cc")
            store.insert_change(
                self._db,
                {
                    "configuration_change_id": cid,
                    "configuration_object_family": proposal.configuration_object_family,
                    "configuration_object_id": proposal.configuration_object_id,
                    "change_type": proposal.change_type,
                    "change_payload": dict(proposal.change_payload),
                    "proposed_active_flag": proposal.change_type != CHANGE_DEACTIVATE,
                    "effective_from": proposal.effective_from,
                    "declared_effective_to": proposal.declared_effective_to,
                    "previous_object_version_expected": (
                        proposal.previous_object_version_expected
                    ),
                    "proposal_time_is_self_affecting": risk.is_self_affecting,
                    "proposal_time_affects_protected_meta_authority": (
                        risk.affects_protected_meta_authority
                    ),
                    "proposal_time_privilege_increasing": risk.privilege_increasing,
                    "proposal_time_authorization_required": risk.authorization_required,
                    "proposal_context_snapshot": dict(context.context_reference),
                    "proposal_dependency_fingerprint": context.fingerprint,
                    "initiated_by_person_id": person_id,
                    "initiated_by_actor_user_public_id": actor.actor_user_public_id,
                    "initiated_at": as_of,
                    "lifecycle_status": LIFECYCLE_PENDING,
                },
            )
            self._persist(cid, evaluation)
            self._db.commit()
            return ConfigurationChangeOutcome(
                accepted=True,
                configuration_change_id=cid,
                lifecycle_status=LIFECYCLE_PENDING,
                evaluation=evaluation,
            )
        except Exception:
            self._db.rollback()
            raise

    # -- authorize ---------------------------------------------------------------

    def authorize(
        self, actor: AuthenticatedActor, configuration_change_id: str
    ) -> ConfigurationChangeOutcome:
        as_of = _now()
        try:
            record = store.load_change(self._db, configuration_change_id, for_update=True)
            if record is None:
                raise ConfigurationGovernanceError(
                    f"unknown Configuration Change: {configuration_change_id!r}"
                )
            if record["lifecycle_status"] != LIFECYCLE_PENDING:
                outcome = self._terminal(record, LIFECYCLE_STATE_INVALID)
                self._db.commit()
                return outcome

            proposal = self._proposal_from(record)
            context = self._load_context(as_of, self._positions(proposal))
            person_id, eligible, resolvable = self._actor_state(actor, as_of, context)
            if person_id is None or not resolvable or not context.is_resolved:
                return self._unavailable(
                    STAGE_AUTHORIZATION,
                    context,
                    person_id,
                    actor.actor_user_public_id,
                    configuration_change_id,
                    LIFECYCLE_PENDING,
                )

            risk = policy.classify_risk(proposal, context, record["initiated_by_person_id"])
            evaluation = policy.evaluate_authorization(
                context=context,
                risk=risk,
                initiator_person_id=record["initiated_by_person_id"],
                person=person_id,
                actor=actor.actor_user_public_id,
                eligible=eligible,
                proposal_fingerprint=record["proposal_dependency_fingerprint"],
            )
            # The evaluation is appended FIRST so the authorizer record can be bound to its
            # identity in the same transaction. A REFUSED attempt stops here: it leaves its own
            # durable evidence and touches no authorizer field, so it can neither create an
            # authorization nor re-point an existing one at its own recomputed context.
            evaluation_id = self._persist(configuration_change_id, evaluation)
            if evaluation.authorization_satisfied:
                store.record_authorization(
                    self._db,
                    configuration_change_id,
                    person_id=person_id,
                    actor_id=actor.actor_user_public_id,
                    at=as_of,
                    evaluation_id=evaluation_id,
                )
            self._db.commit()
            return ConfigurationChangeOutcome(
                accepted=evaluation.authorization_satisfied,
                configuration_change_id=configuration_change_id,
                lifecycle_status=LIFECYCLE_PENDING,
                evaluation=evaluation,
                refusal_reason=evaluation.refusal_reason,
            )
        except Exception:
            self._db.rollback()
            raise

    # -- reject -------------------------------------------------------------------

    def reject(
        self, actor: AuthenticatedActor, configuration_change_id: str, reason: str
    ) -> ConfigurationChangeOutcome:
        as_of = _now()
        try:
            record = store.load_change(self._db, configuration_change_id, for_update=True)
            if record is None:
                raise ConfigurationGovernanceError(
                    f"unknown Configuration Change: {configuration_change_id!r}"
                )
            if record["lifecycle_status"] != LIFECYCLE_PENDING:
                outcome = self._terminal(record, LIFECYCLE_STATE_INVALID)
                self._db.commit()
                return outcome

            proposal = self._proposal_from(record)
            context = self._load_context(as_of, self._positions(proposal))
            person_id, eligible, resolvable = self._actor_state(actor, as_of, context)
            if person_id is None or not resolvable or not context.is_resolved:
                return self._unavailable(
                    STAGE_REJECTION,
                    context,
                    person_id,
                    actor.actor_user_public_id,
                    configuration_change_id,
                    LIFECYCLE_PENDING,
                )

            risk = policy.classify_risk(proposal, context, record["initiated_by_person_id"])
            evaluation = replace(
                policy.evaluate_proposal(
                    context=context,
                    risk=risk,
                    person=person_id,
                    actor=actor.actor_user_public_id,
                    eligible=eligible,
                    blocking_reason=None if eligible else INITIATOR_NOT_ELIGIBLE,
                    stage=STAGE_REJECTION,
                ),
                authorization_satisfied=False,
                outcome=OUTCOME_REFUSED,
                refusal_reason=(
                    CHANGE_REJECTED_BY_GOVERNANCE_DECISION
                    if eligible
                    else INITIATOR_NOT_ELIGIBLE
                ),
                authorizer_is_different_person=person_id != record["initiated_by_person_id"],
            )
            if eligible:
                store.record_rejection(
                    self._db,
                    configuration_change_id,
                    status=LIFECYCLE_REJECTED,
                    person_id=person_id,
                    at=as_of,
                    reason=reason,
                )
            self._persist(configuration_change_id, evaluation)
            self._db.commit()
            return ConfigurationChangeOutcome(
                accepted=eligible,
                configuration_change_id=configuration_change_id,
                lifecycle_status=LIFECYCLE_REJECTED if eligible else LIFECYCLE_PENDING,
                evaluation=evaluation,
                refusal_reason=None if eligible else INITIATOR_NOT_ELIGIBLE,
            )
        except Exception:
            self._db.rollback()
            raise

    # -- activate -------------------------------------------------------------------

    def activate(
        self, actor: AuthenticatedActor, configuration_change_id: str
    ) -> ConfigurationChangeOutcome:
        """Recompute, then publish, atomically or not at all.

        THE GOVERNANCE-WIDE PUBLICATION BOUNDARY IS TAKEN FIRST, BEFORE ANY READ. Every read
        this transaction performs - the Configuration Change row, the published store and its
        retraction assertions, the protected candidate codes, the kernel's own reads through the
        configuration provider, the lineage-derived authoritative predecessor, the allocation
        anchor and its recorded `published_at`, the duplicate check and the bound authorization
        evidence - happens after it, and it is held until the same commit or rollback that
        decides whether anything was published. The final risk recomputation, the predecessor
        check and the publication-ordering check are therefore all made against one state that
        no concurrent governed activation can move.

        Why governance-wide and not merely per-object: two activations of two DIFFERENT stable
        objects can be mutually risk-dependent - two assignments that would duplicate each
        other, a rule and the authority it grants from - and under READ COMMITTED each could
        validate against a snapshot taken before the other published, so both would publish. A
        per-object lock cannot see that pair at all, because they take different keys. It is
        retained below as secondary defence and for the precise contention evidence it gives.

        The boundary serializes governed activation against THIS application's database. It is
        not, and must not be described as, serialization of any external HR/organisation or
        actor-person system; those are handled by failing closed, and the production composition
        still refuses to compose while they are absent.

        Everything from that boundary to the commit happens in ONE transaction. Both advisory
        locks are transaction-scoped, so there is no window in which the check has passed and
        the effect has not yet happened.

        THE LAST QUESTION ASKED BEFORE ANYTHING IS WRITTEN IS WHETHER THE RESULT WOULD BE VALID.
        Once the predecessor, the allocation anchor and the recorded instant have established the
        EXACT immutable version this activation would append, that version and the object's whole
        existing material go to the unchanged PF-1A-E2-A kernel. A publication the kernel would
        immediately classify as defective is refused with PUBLICATION_LINEAGE_INVALID: no version
        row is written, the change stays PENDING, and the prior lineage is left exactly as it was.
        PF-1A-E3 has no correction or retraction path, so a defective lineage it published could
        not be repaired by anything this package offers - which is precisely why it must never
        publish one.
        """

        as_of = _now()
        try:
            if not store.try_lock_governance_publication(self._db):
                # Refused before ANY state was read, so there is no lifecycle status this can
                # honestly report. Governed activation is a rare, deliberate path; a caller that
                # meets a concurrent one simply retries.
                self._db.rollback()
                return ConfigurationChangeOutcome(
                    accepted=False,
                    configuration_change_id=configuration_change_id,
                    lifecycle_status=None,
                    refusal_reason=CONCURRENT_ACTIVATION_IN_PROGRESS,
                )

            record = store.load_change(self._db, configuration_change_id, for_update=True)
            if record is None:
                raise ConfigurationGovernanceError(
                    f"unknown Configuration Change: {configuration_change_id!r}"
                )
            if record["lifecycle_status"] != LIFECYCLE_PENDING:
                outcome = self._terminal(record, LIFECYCLE_STATE_INVALID)
                self._db.commit()
                return outcome

            family = record["configuration_object_family"]
            object_id = record["configuration_object_id"]
            proposal = self._proposal_from(record)

            if not store.try_lock_object(self._db, family, object_id):
                outcome = self._terminal(record, CONCURRENT_ACTIVATION_IN_PROGRESS)
                self._db.commit()
                return outcome

            context = self._load_context(as_of, self._positions(proposal))
            person_id, eligible, resolvable = self._actor_state(actor, as_of, context)
            if person_id is None or not resolvable or not context.is_resolved or not eligible:
                reason = (
                    INITIATOR_NOT_ELIGIBLE
                    if (person_id is not None and resolvable and context.is_resolved)
                    else AUTHORITY_CONTEXT_UNAVAILABLE
                )
                return self._unavailable(
                    STAGE_ACTIVATION,
                    context,
                    person_id,
                    actor.actor_user_public_id,
                    configuration_change_id,
                    LIFECYCLE_PENDING,
                    reason,
                )

            # The RECORDED authorizer's continuing eligibility, re-established NOW. Someone who
            # has since lost the authority, or whose actor no longer maps to them, no longer
            # counts.
            authorizer_person = record["authorized_by_person_id"]
            authorizer_actor = record["authorized_by_actor_user_public_id"]
            authorizer_ok = False
            if authorizer_person is not None and authorizer_actor:
                if self._person_for(authorizer_actor, as_of) == authorizer_person:
                    still, ok_now = self._holds_protected(authorizer_actor, as_of, context)
                    authorizer_ok = bool(still and ok_now)

            # THE BOUND successful authorization - not the latest AUTHORIZATION evaluation. Its
            # fingerprint and its risk verdict are the ones the recorded authorizer actually
            # saw, so a later refused attempt against a drifted context cannot supply either.
            bound = self._bound_authorization(record)

            # TWO SEPARATE QUESTIONS, DELIBERATELY READ FROM TWO SEPARATE PLACES.
            #
            # The expected predecessor is compared against the AUTHORITATIVE PREDECESSOR the
            # unchanged PF-1A-E2-A kernel derives - the temporally last version of the validated
            # CURRENT ASSERTED lineage. A retracted version is not an answer to that question,
            # however great its spelling, and a lineage the kernel cannot establish has already
            # failed this activation closed above through `context.unresolved`.
            #
            # The ALLOCATION ANCHOR is the object's all-time lexicographic maximum, retracted
            # versions included, because the kernel validates provenance across every published
            # version and the new identity must sort after all of them. Anchoring the allocation
            # on the predecessor instead would mint an identity that could sort BEFORE a retracted
            # row - contradictory provenance, published by the very act meant to be safe.
            #
            # No version identifier is parsed anywhere here, so a predecessor published as "v1",
            # as a UUID, or by any other authorized mechanism supersedes exactly like one PF-1A-E3
            # allocated itself.
            predecessor = policy.authoritative_predecessor(context, family, object_id)
            anchor = store.allocation_anchor(self._db, family, object_id)
            if record["change_type"] == CHANGE_CREATE:
                # An absent predecessor IS an unpublished object - it has never been published, or
                # every version it had was retracted. Either way the current asserted lineage is
                # empty and there is nothing for a CREATE to collide with.
                lineage_ok = predecessor is None
            else:
                lineage_ok = (
                    predecessor is not None
                    and record["previous_object_version_expected"] == predecessor
                )

            # THE EXACT IMMUTABLE VERSION THIS ACTIVATION WOULD APPEND, constructed ONCE, from the
            # anchor and the instant already established above. The same object is handed to the
            # prospective lineage evaluation below and to the store's writer, so what was validated
            # and what is written cannot be two constructions that merely agree.
            proposed_version = PublishedRow(
                object_family=family,
                object_id=object_id,
                object_version=allocate_object_version(
                    anchor.object_version, configuration_change_id
                ),
                active_flag=bool(record["proposed_active_flag"]),
                retracted=False,
                effective_from=record["effective_from"],
                declared_effective_to=record["declared_effective_to"],
                payload=dict(record["change_payload"] or {}),
                corrects_object_version=None,
                publication_reference_type=PUBLICATION_REFERENCE_TYPE,
                publication_reference_id=configuration_change_id,
                published_at=as_of,
            )

            # WOULD THE RESULTING LINEAGE STILL BE VALID? Asked of the UNCHANGED PF-1A-E2-A kernel,
            # over the object's COMPLETE prospective material, inside the same governance-wide
            # boundary that read that material - and asked for CREATE, UPDATE and DEACTIVATE alike,
            # because an append is an append whichever change type produced it.
            #
            # This is separate from, and never substituted for, the risk classification. A change
            # may correctly grant nothing new and still be unpublishable: PF-1A-E3's UPDATE appends
            # rather than retracting and republishing, so a narrower interval that starts before a
            # still-asserted predecessor's declared end leaves an EXPLICIT OVERLAP under 11.4.
            # Publishing it would fail every later resolution of the object closed and - the
            # authority graph being whole-configuration - would block governed administration
            # outright. It is refused before the version row is written and before the change moves
            # to ACTIVE, so the prior lineage is left exactly as it was.
            publication_defects = policy.prospective_publication_defects(
                context, proposed_version
            )

            risk = policy.classify_risk(proposal, context, record["initiated_by_person_id"])
            evaluation = policy.evaluate_activation(
                context=context,
                risk=risk,
                initiator_person_id=record["initiated_by_person_id"],
                recorded_authorizer_person_id=authorizer_person,
                authorization_evidence_verified=bound is not None,
                authorizer_still_eligible=authorizer_ok,
                authorization_fingerprint=(
                    bound["dependency_fingerprint"] if bound is not None else None
                ),
                authorization_required_at_authorization=(
                    bound["recomputed_authorization_required"] if bound is not None else None
                ),
                person=person_id,
                actor=actor.actor_user_public_id,
                lineage_ok=lineage_ok,
                references_present=self._references_present(proposal),
                conflicting_assignment_object_id=policy.conflicting_active_assignment(
                    proposal, context
                ),
                # The captured instant is the one that will be recorded as `published_at`. It is
                # never advanced, substituted or re-read to satisfy this check.
                publication_timestamp_monotonic=policy.publication_time_is_non_decreasing(
                    anchor, as_of
                ),
                publication_lineage_valid=not publication_defects,
            )

            published_version: str | None = None
            if evaluation.authorization_satisfied:
                store.ensure_stable_identity(self._db, family, object_id)
                # THE ROW THE KERNEL JUST APPROVED, written unchanged. Its identity was allocated
                # from the SAME all-time anchor read above, inside the same governance-wide
                # boundary, so it is strictly lexicographically greater than every version already
                # published for this object - retracted ones included. PF-1A-E2's kernel requires
                # that ordering: it reads `published_at` as non-decreasing in `object_version` order
                # across every published version, so an identity that sorted before an earlier one
                # would be contradictory provenance and would fail an unchanged-kernel resolution
                # closed - a real regression, not a theoretical one. The matching timestamp half of
                # that same rule was checked immediately above, against this anchor and this
                # instant, and the prospective evaluation then checked the whole resulting lineage.
                published_version = proposed_version.object_version
                store.insert_published_version(self._db, proposed_version)
                store.record_activation(
                    self._db,
                    configuration_change_id,
                    status=LIFECYCLE_ACTIVE,
                    version=published_version,
                    at=as_of,
                )

            self._persist(configuration_change_id, evaluation)
            self._db.commit()
            return ConfigurationChangeOutcome(
                accepted=evaluation.authorization_satisfied,
                configuration_change_id=configuration_change_id,
                lifecycle_status=(
                    LIFECYCLE_ACTIVE
                    if evaluation.authorization_satisfied
                    else LIFECYCLE_PENDING
                ),
                evaluation=evaluation,
                refusal_reason=evaluation.refusal_reason,
                published_object_version=published_version,
            )
        except Exception:
            # No partial publication and no false ACTIVE state can survive a failure: the
            # version row, the lifecycle update and the evaluation record are all in the one
            # transaction being discarded here.
            self._db.rollback()
            raise
