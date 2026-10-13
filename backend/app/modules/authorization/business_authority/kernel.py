"""The PURE Business Authority resolution kernel.

PF-1A-E2-A sections 10.3, 12, 15 and 16.

PURITY, stated as a checklist a reviewer can run down this module against:
no database session, no SQL, no HTTP, no environment read, NO CLOCK READ, no
framework concern. The kernel is a deterministic function of the explicit
instant, the explicit request and the explicit port results. Only
`resolver.resolve_current_authority` reads a clock, and it does so exactly
once (10.1, 11.1). E2-B must be able to reuse this module UNCHANGED; any E2-B
change to it signals that the boundary was drawn wrongly and requires
reconciliation, not a quiet edit.

TRAVERSAL DOES NOT AFFECT THE RESULT (12.2). The kernel may traverse the
candidate graph in whichever direction is efficient, and re-sorts every
provider result canonically. Provider order, SQL row order, dictionary/set
iteration order, path traversal direction and concurrency must not change the
outcome, the status, the reason, the path sets or the evidence ordering.

AGGREGATION IS TOTAL (15.3). Every resolution lands in exactly one branch:

    1. any FAIL_CLOSED defect in RELEVANT authoritative state or a relevant
       dependency -> DENY + FAIL_CLOSED. A qualifying path elsewhere does NOT
       rescue it, and the reported reason is the reason of the FIRST defect
       under the TOTAL order of 15.5 - never the first one traversal happened
       to encounter;
    2. otherwise one or more COMPLETE QUALIFYING paths -> ALLOW + RESOLVED,
       with every qualifying path retained;
    3. otherwise DENY + RESOLVED, with a legible result-level reason.

RELEVANCE IS IDENTITY-ONLY (15.2). A record is provably irrelevant only when
the exclusion can be established WITHOUT relying on any defective, ambiguous,
contradictory or semantically interpreted field. That property is structural
here: candidates arrive through RAW, identity-only discovery (9.3.1), so an
object the provider never returned is one whose raw published facts carry
neither the requested `authority_code` nor any candidate stable reference.
Retraction is never an irrelevance test, and the kernel never re-applies at
its own layer the prefiltering the provider is forbidden to do.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, replace
from datetime import datetime
from typing import Any

from app.modules.authorization.business_authority import evaluators, lineage, scope
from app.modules.authorization.business_authority.contract import (
    ACTOR_PERSON_MAPPING_AMBIGUOUS,
    ACTOR_PERSON_MAPPING_MISSING,
    ACTOR_PERSON_PROVIDER_NOT_CONFIGURED,
    ASSIGNMENT_NOT_ACTIVE,
    ASSIGNMENT_NOT_EFFECTIVE,
    ASSIGNMENT_TARGET_INVALID,
    ASSIGNMENT_TARGET_NOT_THIS_PERSON,
    AUTHORITY_CODE_NOT_CONFIGURED,
    AUTHORITY_CONFIGURATION_UNAVAILABLE,
    AUTHORITY_NOT_ACTIVE,
    AUTHORITY_REFERENCE_DANGLING,
    AUTHORITY_VERSION_AMBIGUOUS,
    BUSINESS_AUTHORITY,
    BUSINESS_AUTHORITY_ASSIGNMENT,
    BUSINESS_AUTHORITY_ROLE,
    BUSINESS_AUTHORITY_RULE,
    EMPLOYMENT_NOT_ACTIVE,
    EMPLOYMENT_STATE_AMBIGUOUS,
    EMPLOYMENT_STATE_MISSING,
    HR_REFERENCE_PROVIDER_NOT_CONFIGURED,
    HR_REFERENCE_STALE,
    HR_REFERENCE_UNAVAILABLE,
    INCUMBENCY_AMBIGUOUS,
    INCUMBENCY_MISSING,
    INTERNAL_CONTRACT_VIOLATION,
    NO_CANDIDATE_ASSIGNMENT,
    NO_QUALIFYING_PATH,
    OTHER_NONQUALIFICATION,
    OUTCOME_ALLOW,
    OUTCOME_DENY,
    POSITION_STATE_AMBIGUOUS,
    POSITION_STATE_MISSING,
    ROLE_NOT_ACTIVE,
    ROLE_NOT_EFFECTIVE,
    RULE_NOT_ACTIVE,
    RULE_NOT_EFFECTIVE,
    STAGE_S0_ACTOR,
    STAGE_S1_PERSON,
    STAGE_S2_EMPLOYMENT,
    STAGE_S3_AUTHORITY,
    STAGE_S4_RULES,
    STAGE_S5_ROLES,
    STAGE_S6_ASSIGNMENTS,
    STAGE_S7_TARGET,
    STAGE_S8_SCOPE,
    STAGE_S9_PARAMETERS,
    STATUS_FAIL_CLOSED,
    STATUS_RESOLVED,
    SUBJECT_TOKEN_ACTOR_PERSON_PORT,
    SUBJECT_TOKEN_AUTHORITY_CONFIGURATION_PORT,
    SUBJECT_TOKEN_HR_EMPLOYMENT_PORT,
    SUBJECT_TOKEN_KERNEL_INVARIANT,
)
from app.modules.authorization.business_authority.defects import (
    DefectRecord,
    canonical_request_key,
    dependency_subject,
    object_subject,
    order_defects,
    path_subject,
)
from app.modules.authorization.business_authority.domain import (
    AuthorityResolutionRequest,
    LineageMaterial,
    ObjectVersionRef,
)
from app.modules.authorization.business_authority.evidence import (
    AuthorityResolutionResult,
    EstablishedState,
    EvaluatedBusinessContext,
    GrantEligibilityEvaluation,
    HrEvidence,
    ObjectEvidence,
    ParameterEvidence,
    PartialEvaluation,
    PathEvidence,
    ScopeEvidence,
    order_partials,
    order_paths,
)
from app.modules.authorization.business_authority.material import (
    MATERIAL_UNAVAILABLE,
    check_material_well_formed,
)
from app.modules.authorization.business_authority.ports import (
    AuthorityConfigurationPort,
    AuthorityConfigurationPortError,
)
from app.modules.hr_reference.contract import (
    EMPLOYMENT_ACTIVE,
    EMPLOYMENT_STATUSES,
    HR_LOOKUP_AMBIGUOUS,
    HR_LOOKUP_MISSING,
    HR_LOOKUP_STALE,
    HR_LOOKUP_STATUSES,
    HR_LOOKUP_UNAVAILABLE,
    ActorPersonReference,
    EmploymentStateReference,
    HrLookup,
    IncumbencyReference,
    PositionVersionReference,
    is_conforming_instant,
    is_snapshot_stale,
    is_utc_normalized_instant,
)
from app.modules.hr_reference.ports import ActorPersonPort, CanonicalHrReferencePort


@dataclass(frozen=True)
class _Trail:
    """The evidence ALREADY ESTABLISHED for the candidate currently being evaluated.

    PROGRESSIVE, CANDIDATE-SCOPED ACCOUNTING (correction FU-2). Whenever a
    candidate fails at any stage, its partial-evaluation record must retain
    EVERY canonical item established for it before the failure - not only the
    requested Business Authority. The trail is extended as each stage succeeds
    and is RESET to the enclosing candidate's trail at the start of every rule
    and every assignment, so one candidate can never inherit another's
    established state.
    """

    objects: tuple[ObjectEvidence, ...] = ()
    hr: HrEvidence | None = None
    scope: ScopeEvidence | None = None
    parameters: ParameterEvidence | None = None

    def plus_object(self, evidence: ObjectEvidence) -> "_Trail":
        return replace(self, objects=self.objects + (evidence,))

    def with_hr(self, hr: HrEvidence) -> "_Trail":
        return replace(self, hr=hr)

    def with_scope(self, scope_evidence: ScopeEvidence) -> "_Trail":
        return replace(self, scope=scope_evidence)

    def with_parameters(self, parameters: ParameterEvidence) -> "_Trail":
        return replace(self, parameters=parameters)


class _Established:
    """Mutable accumulator for one resolution. Never shared between resolutions."""

    def __init__(self) -> None:
        self.defects: list[DefectRecord] = []
        self.partials: list[PartialEvaluation] = []
        self.qualifying: list[PathEvidence] = []
        self.nonqualifying: list[PathEvidence] = []
        self.snapshots: list[datetime] = []
        self.person_id: str | None = None
        self.employment_state_version_id: str | None = None
        self.employment_status: str | None = None
        self.requested_authority: ObjectVersionRef | None = None
        self.requested_authority_eligibility: GrantEligibilityEvaluation | None = None
        self.rules_discovered = 0
        self.roles_referenced = 0
        self.assignments_discovered = 0
        self.last_stage = STAGE_S0_ACTOR
        self.rules_and_roles_established = False
        self.assignment_targeted_person = False
        # The evidence established for the candidate under evaluation right
        # now. Reset at every candidate boundary; see _Trail.
        self.trail = _Trail()

    def reached(self, stage: str) -> None:
        self.last_stage = stage

    def note_snapshot(self, snapshot: datetime | None) -> None:
        if snapshot is not None and snapshot not in self.snapshots:
            self.snapshots.append(snapshot)


@dataclass(frozen=True)
class _HrAnswer:
    """One validated canonical HR answer, or the reason it could not be used."""

    value: Any | None = None
    defect_reason: str | None = None
    detail: str = ""
    # Populated ONLY when the response was identity-bound to the requested
    # object but was too old to rely on. That is the one failure mode whose
    # subject genuinely IS the requested object, so citing its canonical
    # reference and snapshot in the evidence is correct and is required by
    # FU-2. A response that failed identity binding is NOT about the requested
    # object, so nothing from it is ever cited.
    observed_reference: str | None = None
    observed_snapshot_at: datetime | None = None


def _resolve_hr(
    lookup: HrLookup,
    *,
    expected_type: type,
    identity_attribute: str,
    expected_identity: str,
    reference_attribute: str,
    missing_reason: str,
    ambiguous_reason: str,
    as_of: datetime,
    threshold_seconds: int | None,
    vocabulary_attribute: str | None = None,
    vocabulary: tuple[str, ...] = (),
) -> _HrAnswer:
    """Validate ONE canonical HR/reference answer, and return it or a defect code.

    THIS IS THE ONLY PLACE AN HR ANSWER IS INTERPRETED. Every seam - actor to
    canonical person, employment state, Position Version, Incumbency - goes
    through it, because a per-seam copy of these four checks is exactly how one
    of them comes to be missed. Organisation Unit hops apply the identical
    rules inside the bounded ancestry traversal (`scope.evaluate_operand`).

    The four checks, in order, none of them skippable:

      1. THE STATUS MUST BE IN THE CLOSED VOCABULARY. A response whose status
         is outside `HR_LOOKUP_STATUSES` is NOT authoritative state, and must
         never be trusted merely because a plausible value is also attached. It
         is a provider-contract failure and takes the existing
         HR_REFERENCE_UNAVAILABLE classification - it is NEVER silently mapped
         onto OK, MISSING or any other known state, and no new reason code is
         invented for it.
      2. AN EXPLICIT FAILURE STATUS takes its own seam-specific code, so
         MISSING and AMBIGUOUS stay distinguishable (14.4 distinction 1).
      3. AN `OK` CARRYING A NON-CONFORMING VALUE is likewise a provider-contract
         failure, not an absence: the provider said it had an answer and did not
         supply one.
      4. FRESHNESS is checked against the SAME supplied threshold and the SAME
         authoritative `as_of` as every other HR state in this resolution.
    """

    if lookup.status not in HR_LOOKUP_STATUSES:
        return _HrAnswer(
            defect_reason=HR_REFERENCE_UNAVAILABLE,
            detail="the canonical response carried a status outside the closed lookup vocabulary",
        )

    explicit = {
        HR_LOOKUP_MISSING: missing_reason,
        HR_LOOKUP_AMBIGUOUS: ambiguous_reason,
        HR_LOOKUP_UNAVAILABLE: HR_REFERENCE_UNAVAILABLE,
        HR_LOOKUP_STALE: HR_REFERENCE_STALE,
    }.get(lookup.status)
    if explicit is not None:
        # `lookup.status` is a CLOSED-vocabulary value here, not provider prose.
        return _HrAnswer(
            defect_reason=explicit,
            detail=f"the canonical response reported {lookup.status}",
        )

    value = lookup.value
    if not isinstance(value, expected_type):
        return _HrAnswer(
            defect_reason=HR_REFERENCE_UNAVAILABLE,
            detail="the canonical response carried no conforming value",
        )

    # IDENTITY BINDING (correction FU-1). The response must be about the
    # canonical object that was REQUESTED. A provider returning a fresh,
    # otherwise-valid record for a DIFFERENT canonical identity has not
    # established the requested fact, and must never be able to authorize
    # through it. The mismatched identity is deliberately NOT echoed into
    # evidence: it belongs to an object this resolution did not ask about.
    if getattr(value, identity_attribute, None) != expected_identity:
        return _HrAnswer(
            defect_reason=HR_REFERENCE_UNAVAILABLE,
            detail="the canonical response identified a different object than the one requested",
        )

    # CLOSED-VOCABULARY CONTENT (correction FU-3). A value inside an
    # identity-bound, fresh response may still carry a state outside the
    # contract's own closed vocabulary. That is a provider-contract failure -
    # NOT a known-and-resolved answer - and it must never be silently mapped
    # onto a known state.
    if vocabulary_attribute is not None:
        if getattr(value, vocabulary_attribute, None) not in vocabulary:
            return _HrAnswer(
                defect_reason=HR_REFERENCE_UNAVAILABLE,
                detail=(
                    f"the canonical response carried a {vocabulary_attribute} outside its "
                    "closed vocabulary"
                ),
            )

    # AWARENESS ONLY. E2-A 7 / 9.1 / 9.2 describe `canonical_snapshot_at` as the
    # canonical freshness indicator and state no UTC-normalization requirement
    # for it, so none is invented here; awareness is required because the
    # staleness rule subtracts it from `as_of`, and a naive value would raise
    # rather than answer.
    if not is_conforming_instant(value.canonical_snapshot_at):
        return _HrAnswer(
            defect_reason=HR_REFERENCE_UNAVAILABLE,
            detail="the canonical response carried a snapshot that is not a timezone-aware instant",
        )

    observed_reference = getattr(value, reference_attribute, None)
    if is_snapshot_stale(value.canonical_snapshot_at, as_of, threshold_seconds):
        return _HrAnswer(
            defect_reason=HR_REFERENCE_STALE,
            detail="the canonical snapshot is older than the configured staleness threshold",
            observed_reference=observed_reference,
            observed_snapshot_at=value.canonical_snapshot_at,
        )

    return _HrAnswer(
        value=value,
        observed_reference=observed_reference,
        observed_snapshot_at=value.canonical_snapshot_at,
    )


def _evidence_for(
    family: str,
    object_id: str,
    version: Any,
    evaluation: lineage.LineageEvaluation,
) -> ObjectEvidence:
    """Build one object's evidence from its VALIDATED lineage evaluation.

    The recorded `retracted_at` of every valid retraction assertion that
    participated in establishing this object's current asserted lineage is
    carried here, in the deterministic canonical order the evaluation computed
    (16.2). It is RECORDED TIME, labelled as such by the field name, and is
    never an effective or authorization clock (11.8.4). Because it is taken
    from an evaluation that has already validated, an INVALID assertion can
    never reach successful evidence - it fails the resolution closed instead.
    """

    return ObjectEvidence(
        ref=ObjectVersionRef(
            object_family=family, object_id=object_id, object_version=version.object_version
        ),
        publication_reference_type=version.publication_reference_type,
        publication_reference_id=version.publication_reference_id,
        recorded_published_at=version.published_at,
        recorded_retracted_at_of_participating_assertions=evaluation.participating_retracted_at,
        grant_eligibility=GrantEligibilityEvaluation(
            lineage_valid=not evaluation.has_defect,
            effective_at_as_of=True,
            active_flag=version.active_flag,
        ),
    )


def _load_lineage(
    port: AuthorityConfigurationPort,
    family: str,
    object_id: str,
    as_of: datetime,
) -> tuple[lineage.LineageEvaluation | None, DefectRecord | None]:
    """Fetch and validate one object's complete lineage material.

    A raised provider error, a timeout, `completeness = UNAVAILABLE` and
    ILL-FORMED material all fail closed with
    AUTHORITY_CONFIGURATION_UNAVAILABLE (9.3.3). None of them is ever degraded
    to "no candidates found" and none is ever degraded to DENY + RESOLVED.
    """

    try:
        material = port.get_lineage(family, object_id)
    except AuthorityConfigurationPortError:
        # THE PROVIDER'S OWN EXCEPTION TEXT IS DELIBERATELY DISCARDED HERE
        # (correction FU-4). Exception wording is not stable domain data: it
        # varies across provider, library and runtime versions, may carry
        # provider-specific or sensitive detail, and would destroy the
        # byte-identical evidence the determinism rules require. The canonical
        # facts that matter - which object, which family, which stage - are
        # already carried by the defect's subject and stage.
        return None, DefectRecord(
            reason_code=AUTHORITY_CONFIGURATION_UNAVAILABLE,
            stage=_STAGE_FOR_FAMILY[family],
            subject=object_subject(family, object_id),
            detail="the authority configuration port failed while reading this object",
        )

    # IDENTITY BINDING (correction FU-1). Material returned for a DIFFERENT
    # object, or for a different object family, is not this object's
    # authoritative material and is never trusted as such.
    if isinstance(material, LineageMaterial) and (
        material.object_family != family or material.object_id != object_id
    ):
        return None, DefectRecord(
            reason_code=AUTHORITY_CONFIGURATION_UNAVAILABLE,
            stage=_STAGE_FOR_FAMILY[family],
            subject=object_subject(family, object_id),
            detail="the authority configuration port returned material for a different object",
        )

    rejection = check_material_well_formed(material)
    if rejection is not None:
        label = (
            "provider reported it cannot return complete material"
            if rejection.kind == MATERIAL_UNAVAILABLE
            else "provider supplied ill-formed material"
        )
        return None, DefectRecord(
            reason_code=AUTHORITY_CONFIGURATION_UNAVAILABLE,
            stage=_STAGE_FOR_FAMILY[family],
            subject=object_subject(family, object_id),
            detail=f"{label}: {rejection.detail}",
        )

    return lineage.evaluate_lineage(material, as_of), None


_STAGE_FOR_FAMILY = {
    BUSINESS_AUTHORITY: STAGE_S3_AUTHORITY,
    BUSINESS_AUTHORITY_RULE: STAGE_S4_RULES,
    BUSINESS_AUTHORITY_ROLE: STAGE_S5_ROLES,
    BUSINESS_AUTHORITY_ASSIGNMENT: STAGE_S6_ASSIGNMENTS,
}


def _lineage_defect_records(
    family: str, object_id: str, evaluation: lineage.LineageEvaluation
) -> list[DefectRecord]:
    return [
        DefectRecord(
            reason_code=defect.reason_code,
            stage=_STAGE_FOR_FAMILY[family],
            subject=object_subject(family, object_id, defect.object_version),
            detail=defect.detail,
        )
        for defect in evaluation.defects
    ]


def resolve(
    *,
    request: AuthorityResolutionRequest,
    as_of: datetime,
    authority_configuration_port: AuthorityConfigurationPort | None,
    actor_person_port: ActorPersonPort | None,
    hr_reference_port: CanonicalHrReferencePort | None,
) -> AuthorityResolutionResult:
    """Resolve one authority question at ONE explicit business-effective instant."""

    state = _Established()
    actor_id = request.authenticated_actor.actor_user_public_id
    context = request.business_context
    evaluated_context = EvaluatedBusinessContext(
        scope_type=context.scope_type,
        scope_id=context.scope_id,
        declared_fact_names=tuple(sorted(context.declared_facts)),
    )

    def request_key(person_id: str | None = None) -> str:
        return canonical_request_key(
            authority_code=request.authority_code,
            actor_user_public_id=actor_id,
            person_id=person_id,
            scope_type=context.scope_type,
            scope_id=context.scope_id,
        )

    def finish(outcome: str, status: str, reason: str) -> AuthorityResolutionResult:
        return _build_result(
            request=request,
            as_of=as_of,
            state=state,
            evaluated_context=evaluated_context,
            outcome=outcome,
            status=status,
            reason=reason,
        )

    def fail(defect: DefectRecord, trail: "_Trail | None" = None) -> AuthorityResolutionResult:
        if trail is not None:
            state.trail = trail
        state.defects.append(defect)
        state.partials.append(
            PartialEvaluation(
                established_objects=state.trail.objects,
                last_stage_reached=defect.stage,
                reason_code=defect.reason_code,
                is_defect=True,
                detail=defect.detail,
                defects=(defect,),
                candidate_key=("dependency",) + defect.subject.components,
                hr_evidence=state.trail.hr,
            )
        )
        return finish(OUTCOME_DENY, STATUS_FAIL_CLOSED, defect.reason_code)

    # -- S0  identify the authenticated actor -------------------------------
    state.reached(STAGE_S0_ACTOR)

    # THE ONE AUTHORIZATION INSTANT MUST CONFORM BEFORE ANY STAGE USES IT
    # (correction C2-2). 11.1 states it in terms: the single `as_of` "is
    # timezone-aware and normalized to UTC". Both halves are enforced, and
    # neither is repaired here - a non-UTC caller-supplied instant is NOT
    # converted, because 11.8 forbids silently reinterpreting a supplied
    # instant and 10.2 defines no input-normalization step at that boundary.
    #
    # `resolve_current_authority` captures a conforming UTC instant itself, so
    # this is reachable only through the historical resolver or a direct kernel
    # call - and such a call must fail closed deterministically rather than
    # escape as an uncaught TypeError from the first comparison that touches it.
    if not is_utc_normalized_instant(as_of):
        return fail(
            DefectRecord(
                reason_code=INTERNAL_CONTRACT_VIOLATION,
                stage=STAGE_S0_ACTOR,
                subject=dependency_subject(SUBJECT_TOKEN_KERNEL_INVARIANT, request_key()),
                detail="the supplied as_of is not a UTC-normalized timezone-aware instant",
            )
        )

    if not isinstance(actor_id, str) or not actor_id:
        # A kernel invariant, not a business answer: the caller must supply an
        # authenticated actor. Never degraded to a plain DENY (14.3).
        return fail(
            DefectRecord(
                reason_code=INTERNAL_CONTRACT_VIOLATION,
                stage=STAGE_S0_ACTOR,
                subject=dependency_subject(SUBJECT_TOKEN_KERNEL_INVARIANT, request_key()),
                detail="no authenticated actor was supplied to the kernel",
            )
        )

    # -- S1  resolve the canonical person -----------------------------------
    state.reached(STAGE_S1_PERSON)
    if actor_person_port is None:
        return fail(
            DefectRecord(
                reason_code=ACTOR_PERSON_PROVIDER_NOT_CONFIGURED,
                stage=STAGE_S1_PERSON,
                subject=dependency_subject(SUBJECT_TOKEN_ACTOR_PERSON_PORT, request_key()),
                detail="no authoritative actor-person provider is bound in this composition",
            )
        )

    person_answer = _resolve_hr(
        actor_person_port.resolve_actor_person(actor_id, as_of),
        expected_type=ActorPersonReference,
        # IDENTITY BINDING: the reference returned must be the mapping for the
        # AUTHENTICATED ACTOR that was asked about. A fresh, otherwise-valid
        # reference for a different actor - even one whose person holds the
        # requested authority - must never authorize this one (FU-1).
        identity_attribute="actor_user_public_id",
        expected_identity=actor_id,
        reference_attribute="person_id",
        missing_reason=ACTOR_PERSON_MAPPING_MISSING,
        ambiguous_reason=ACTOR_PERSON_MAPPING_AMBIGUOUS,
        as_of=as_of,
        threshold_seconds=request.hr_staleness_threshold_seconds,
    )
    if person_answer.defect_reason is not None:
        return fail(
            DefectRecord(
                reason_code=person_answer.defect_reason,
                stage=STAGE_S1_PERSON,
                subject=dependency_subject(SUBJECT_TOKEN_ACTOR_PERSON_PORT, request_key()),
                detail=f"the actor-person mapping was not established: {person_answer.detail}",
            ),
            trail=_Trail(
                hr=(
                    HrEvidence(
                        person_id=person_answer.observed_reference,
                        canonical_snapshot_at_values=(person_answer.observed_snapshot_at,),
                    )
                    if person_answer.observed_reference is not None
                    and person_answer.observed_snapshot_at is not None
                    else None
                )
            ),
        )

    actor_person = person_answer.value
    state.person_id = actor_person.person_id
    state.note_snapshot(actor_person.canonical_snapshot_at)
    person_id = actor_person.person_id

    # -- S2  establish employment state -------------------------------------
    state.reached(STAGE_S2_EMPLOYMENT)
    if hr_reference_port is None:
        return fail(
            DefectRecord(
                reason_code=HR_REFERENCE_PROVIDER_NOT_CONFIGURED,
                stage=STAGE_S2_EMPLOYMENT,
                subject=dependency_subject(SUBJECT_TOKEN_HR_EMPLOYMENT_PORT, request_key(person_id)),
                detail="no authoritative HR reference provider is bound in this composition",
            )
        )

    # The canonical person IS established from here on, so every later failure
    # retains it as evidence (FU-2).
    person_hr = HrEvidence(
        person_id=person_id,
        canonical_snapshot_at_values=(actor_person.canonical_snapshot_at,),
    )
    state.trail = _Trail(hr=person_hr)

    employment_answer = _resolve_hr(
        hr_reference_port.get_employment_state(person_id, as_of),
        expected_type=EmploymentStateReference,
        # IDENTITY BINDING: employment state returned for a DIFFERENT canonical
        # person is not this person's authoritative employment state (FU-1).
        identity_attribute="person_id",
        expected_identity=person_id,
        reference_attribute="employment_state_version_id",
        missing_reason=EMPLOYMENT_STATE_MISSING,
        ambiguous_reason=EMPLOYMENT_STATE_AMBIGUOUS,
        as_of=as_of,
        threshold_seconds=request.hr_staleness_threshold_seconds,
        # CLOSED-VOCABULARY CONTENT: an employment_status outside the contract's
        # own vocabulary is a provider-contract failure, never a known-and-
        # non-active answer (FU-3).
        vocabulary_attribute="employment_status",
        vocabulary=EMPLOYMENT_STATUSES,
    )
    if employment_answer.defect_reason is not None:
        return fail(
            DefectRecord(
                reason_code=employment_answer.defect_reason,
                stage=STAGE_S2_EMPLOYMENT,
                subject=dependency_subject(SUBJECT_TOKEN_HR_EMPLOYMENT_PORT, request_key(person_id)),
                detail=f"the employment state was not established: {employment_answer.detail}",
            ),
            trail=_Trail(
                hr=HrEvidence(
                    person_id=person_id,
                    employment_state_version_id=employment_answer.observed_reference,
                    canonical_snapshot_at_values=tuple(
                        value
                        for value in (
                            actor_person.canonical_snapshot_at,
                            employment_answer.observed_snapshot_at,
                        )
                        if value is not None
                    ),
                )
            ),
        )

    employment = employment_answer.value
    state.employment_state_version_id = employment.employment_state_version_id
    state.employment_status = employment.employment_status
    state.note_snapshot(employment.canonical_snapshot_at)

    base_hr = HrEvidence(
        person_id=person_id,
        employment_state_version_id=employment.employment_state_version_id,
        canonical_snapshot_at_values=(
            actor_person.canonical_snapshot_at,
            employment.canonical_snapshot_at,
        ),
    )
    state.trail = _Trail(hr=base_hr)

    if employment.employment_status != EMPLOYMENT_ACTIVE:
        # PERMITTED SHORT-CIRCUIT (15.3 branch 3a). An UNAMBIGUOUSLY RESOLVED
        # non-active employment state is a normal RESOLVED outcome, never a
        # fail-closed one: the system knows the answer, and the answer is no.
        # No path can qualify regardless, so the remainder of the candidate
        # graph becomes provably irrelevant under 15.2 without relying on any
        # defective field.
        return finish(OUTCOME_DENY, STATUS_RESOLVED, EMPLOYMENT_NOT_ACTIVE)

    # -- S3  establish the requested Business Authority ---------------------
    state.reached(STAGE_S3_AUTHORITY)
    if authority_configuration_port is None:
        return fail(
            DefectRecord(
                reason_code=AUTHORITY_CONFIGURATION_UNAVAILABLE,
                stage=STAGE_S3_AUTHORITY,
                subject=dependency_subject(
                    SUBJECT_TOKEN_AUTHORITY_CONFIGURATION_PORT, request_key(person_id)
                ),
                detail="no authority configuration provider is bound in this composition",
            )
        )

    try:
        authority_ids = sorted(
            set(
                authority_configuration_port.find_business_authority_ids_by_code(
                    request.authority_code
                )
            )
        )
    except AuthorityConfigurationPortError:
        return fail(
            DefectRecord(
                reason_code=AUTHORITY_CONFIGURATION_UNAVAILABLE,
                stage=STAGE_S3_AUTHORITY,
                subject=dependency_subject(
                    SUBJECT_TOKEN_AUTHORITY_CONFIGURATION_PORT, request_key(person_id)
                ),
                detail="the authority configuration port failed during authority discovery",
            )
        )

    establishing: list[tuple[str, Any, lineage.LineageEvaluation]] = []
    authority_candidate_trail = state.trail
    for authority_id in authority_ids:
        # RESET per authority candidate: person and employment are established,
        # the authority itself is not yet.
        state.trail = authority_candidate_trail
        evaluation, load_defect = _load_lineage(
            authority_configuration_port, BUSINESS_AUTHORITY, authority_id, as_of
        )
        if load_defect is not None:
            state.defects.append(load_defect)
            state.partials.append(
                _defect_partial(state, load_defect, (BUSINESS_AUTHORITY, authority_id))
            )
            continue

        assert evaluation is not None
        if evaluation.has_defect:
            lineage_defects = _lineage_defect_records(
                BUSINESS_AUTHORITY, authority_id, evaluation
            )
            state.defects.extend(lineage_defects)
            state.partials.append(
                _defect_partial(state, lineage_defects, (BUSINESS_AUTHORITY, authority_id))
            )
            continue

        if evaluation.is_dangling:
            defect = DefectRecord(
                reason_code=AUTHORITY_REFERENCE_DANGLING,
                stage=STAGE_S3_AUTHORITY,
                subject=object_subject(BUSINESS_AUTHORITY, authority_id),
                detail="a discovered Business Authority carries no lineage material",
            )
            state.defects.append(defect)
            state.partials.append(
                _defect_partial(state, defect, (BUSINESS_AUTHORITY, authority_id))
            )
            continue

        effective = evaluation.effective_version
        if effective is None:
            continue
        payload = effective.payload
        if getattr(payload, "authority_code", None) == request.authority_code:
            establishing.append((authority_id, effective, evaluation))

    if state.defects:
        # Branch 1 takes precedence: a defect in RELEVANT state is never
        # masked, and never converted into an ordinary denial.
        ordered = order_defects(tuple(state.defects))
        return finish(OUTCOME_DENY, STATUS_FAIL_CLOSED, ordered[0].reason_code)

    if len(establishing) > 1:
        # Two distinct stable Business Authority objects both effective for one
        # authority_code is contradictory authoritative state for ONE fact
        # (15.1). No tie-break is attempted and no object is preferred: a
        # defect is raised for EACH, so nothing is masked and the reported one
        # is chosen by the 15.5 total order rather than by discovery order.
        for authority_id, effective, _ in establishing:
            state.defects.append(
                DefectRecord(
                    reason_code=AUTHORITY_VERSION_AMBIGUOUS,
                    stage=STAGE_S3_AUTHORITY,
                    subject=object_subject(
                        BUSINESS_AUTHORITY, authority_id, effective.object_version
                    ),
                    detail="more than one Business Authority establishes this authority_code",
                )
            )
        ordered = order_defects(tuple(state.defects))
        return finish(OUTCOME_DENY, STATUS_FAIL_CLOSED, ordered[0].reason_code)

    if not establishing:
        # THE DELIBERATE ASYMMETRY OF 11.5. No grant-eligible-by-lineage
        # version establishes the requested authority_code at as_of - because
        # its lineage never started, has ended, or the instant sits inside a
        # VALID GAP. The other three families describe an ABSENT GRANT; this
        # one describes an UNKNOWN QUESTION, so it fails closed.
        return fail(
            DefectRecord(
                reason_code=AUTHORITY_CODE_NOT_CONFIGURED,
                stage=STAGE_S3_AUTHORITY,
                subject=dependency_subject(
                    SUBJECT_TOKEN_AUTHORITY_CONFIGURATION_PORT, request_key(person_id)
                ),
                detail="no grant-eligible-by-lineage version establishes this authority_code at as_of",
            )
        )

    authority_id, authority_version, authority_evaluation = establishing[0]
    state.requested_authority = ObjectVersionRef(
        BUSINESS_AUTHORITY, authority_id, authority_version.object_version
    )
    state.requested_authority_eligibility = GrantEligibilityEvaluation(
        lineage_valid=True,
        effective_at_as_of=True,
        active_flag=authority_version.active_flag,
    )

    if not authority_version.active_flag:
        # PERMITTED SHORT-CIRCUIT (15.3 branch 3a). An unambiguously inactive
        # effective version of the REQUESTED authority is a deliberate, known
        # configuration state - not corruption - and never fails closed.
        return finish(OUTCOME_DENY, STATUS_RESOLVED, AUTHORITY_NOT_ACTIVE)

    authority_evidence = _evidence_for(
        BUSINESS_AUTHORITY, authority_id, authority_version, authority_evaluation
    )
    # The requested Business Authority is now established; every candidate
    # expanded below starts from it (FU-2).
    state.trail = _Trail(objects=(authority_evidence,), hr=base_hr)

    # -- S4 to S9  expand the candidate graph -------------------------------
    _expand_candidates(
        state=state,
        request=request,
        as_of=as_of,
        person_id=person_id,
        actor_person=actor_person,
        employment=employment,
        authority_id=authority_id,
        authority_version=authority_version,
        authority_evidence=authority_evidence,
        authority_configuration_port=authority_configuration_port,
        hr_reference_port=hr_reference_port,
        request_key=request_key,
    )

    if state.defects:
        ordered = order_defects(tuple(state.defects))
        return finish(OUTCOME_DENY, STATUS_FAIL_CLOSED, ordered[0].reason_code)

    if state.qualifying:
        return finish(OUTCOME_ALLOW, STATUS_RESOLVED, "")

    # -- 15.3 branch 3: DENY + RESOLVED with a legible reason ---------------
    if state.rules_and_roles_established and not state.assignment_targeted_person:
        return finish(OUTCOME_DENY, STATUS_RESOLVED, NO_CANDIDATE_ASSIGNMENT)

    shared: list[str] = []
    for path in state.nonqualifying:
        if path.decisive_nonqualification_reason not in shared:
            shared.append(path.decisive_nonqualification_reason)  # type: ignore[arg-type]
    for partial in state.partials:
        if partial.reason_code not in shared:
            shared.append(partial.reason_code)

    if len(shared) == 1:
        # Every nonqualifying path and partial evaluation shares exactly one
        # path-level reason, so it is PROMOTED to the result level. This is
        # what makes a denial legible rather than a bare NO_QUALIFYING_PATH.
        return finish(OUTCOME_DENY, STATUS_RESOLVED, shared[0])

    return finish(OUTCOME_DENY, STATUS_RESOLVED, NO_QUALIFYING_PATH)




def _defect_partial(
    state: _Established,
    defect: DefectRecord | Sequence[DefectRecord],
    candidate: tuple[str, ...],
) -> PartialEvaluation:
    """ONE partial evaluation for ONE logical candidate (correction C2-4).

    A candidate may be ended by SEVERAL defects at once - a malformed lineage
    can break more than one structural rule - and all of them are carried here
    together. The DECISIVE one, which drives the reason code, the stage and the
    16.5 ordering, is the FIRST, which is the same defect these fields named
    before the grouping change.

    The candidate key is the candidate itself, with nothing appended. It
    previously carried the reason code and the detail text so that several
    partials for one candidate would not collide under the 16.4 accounting -
    padding that both concealed the duplication and made the key depend on
    diagnostic text rather than on canonical identity.
    """

    defects = (defect,) if isinstance(defect, DefectRecord) else tuple(defect)
    decisive = defects[0]
    return PartialEvaluation(
        established_objects=state.trail.objects,
        last_stage_reached=decisive.stage,
        reason_code=decisive.reason_code,
        is_defect=True,
        detail=decisive.detail,
        defects=defects,
        candidate_key=candidate,
        hr_evidence=state.trail.hr,
        scope_evaluation=state.trail.scope,
        parameter_evaluation=state.trail.parameters,
    )


def _expand_candidates(
    *,
    state: _Established,
    request: AuthorityResolutionRequest,
    as_of: datetime,
    person_id: str,
    actor_person: ActorPersonReference,
    employment: EmploymentStateReference,
    authority_id: str,
    authority_version: Any,
    authority_evidence: ObjectEvidence,
    authority_configuration_port: AuthorityConfigurationPort,
    hr_reference_port: CanonicalHrReferencePort,
    request_key: Any,
) -> None:
    """Stages S4 to S9 over every discovered candidate path."""

    context = request.business_context
    state.reached(STAGE_S4_RULES)

    try:
        rule_ids = sorted(set(authority_configuration_port.find_rule_ids_for_authority(authority_id)))
    except AuthorityConfigurationPortError:
        state.defects.append(
            DefectRecord(
                reason_code=AUTHORITY_CONFIGURATION_UNAVAILABLE,
                stage=STAGE_S4_RULES,
                subject=object_subject(BUSINESS_AUTHORITY, authority_id),
                detail="the authority configuration port failed during rule discovery",
            )
        )
        return

    state.rules_discovered = len(rule_ids)
    # The trail every rule candidate starts from: the requested Business
    # Authority plus the canonical person and employment state (FU-2).
    base_trail = state.trail

    for rule_id in rule_ids:
        # RESET per rule candidate, so one candidate never inherits another's
        # established state.
        state.trail = base_trail
        rule_evaluation, load_defect = _load_lineage(
            authority_configuration_port, BUSINESS_AUTHORITY_RULE, rule_id, as_of
        )
        if load_defect is not None:
            state.defects.append(load_defect)
            state.partials.append(
                _defect_partial(state, load_defect, (BUSINESS_AUTHORITY_RULE, rule_id))
            )
            continue

        assert rule_evaluation is not None
        if rule_evaluation.has_defect:
            lineage_defects = _lineage_defect_records(
                BUSINESS_AUTHORITY_RULE, rule_id, rule_evaluation
            )
            state.defects.extend(lineage_defects)
            state.partials.append(
                _defect_partial(state, lineage_defects, (BUSINESS_AUTHORITY_RULE, rule_id))
            )
            continue

        if rule_evaluation.is_dangling:
            defect = DefectRecord(
                reason_code=AUTHORITY_REFERENCE_DANGLING,
                stage=STAGE_S4_RULES,
                subject=object_subject(BUSINESS_AUTHORITY_RULE, rule_id),
                detail="a discovered Rule carries no lineage material",
            )
            state.defects.append(defect)
            state.partials.append(_defect_partial(state, defect, (BUSINESS_AUTHORITY_RULE, rule_id)))
            continue

        rule_version = rule_evaluation.effective_version
        if rule_version is None:
            # A VALID GAP in a Rule lineage: there is no grant relation
            # between the role and the authority right now. Normal
            # nonqualification, never corruption (11.5).
            state.partials.append(
                _nonqualification_partial(
                    state, STAGE_S4_RULES, RULE_NOT_EFFECTIVE, (BUSINESS_AUTHORITY_RULE, rule_id)
                )
            )
            continue

        # THE ESTABLISHED VERSION IS RECORDED BEFORE THE CHECKS THAT CAN REJECT
        # IT (correction C2-3). Establishing which version is effective is
        # itself an outcome of stages S1-S6, and it is exactly the fact an
        # auditor needs in order to understand a denial: "which Rule version
        # was in force, and why did it not qualify". Recording it only after
        # the active-flag and reference checks passed meant the two most
        # common ordinary denials - inactive, and a current version pointing
        # elsewhere - reported a partial that named the object but not the
        # version the decision was actually taken on. Recording it here does
        # NOT make the candidate qualify; nothing downstream reads the trail
        # as permission.
        rule_evidence = _evidence_for(
            BUSINESS_AUTHORITY_RULE, rule_id, rule_version, rule_evaluation
        )
        state.trail = state.trail.plus_object(rule_evidence)

        if not rule_version.active_flag:
            state.partials.append(
                _nonqualification_partial(
                    state,
                    STAGE_S4_RULES,
                    RULE_NOT_ACTIVE,
                    (BUSINESS_AUTHORITY_RULE, rule_id, rule_version.object_version),
                )
            )
            continue

        rule_payload = rule_version.payload

        # RAW SUPERSET DISCOVERY MUST NOT GRANT THROUGH A HISTORICAL PARENT
        # REFERENCE (correction C1-1, case A). This Rule was discovered because
        # SOME raw published version of it carries the requested authority's
        # stable id - which is exactly what 9.3.1 requires, and is NOT narrowed
        # here. But its CURRENT EFFECTIVE version, established only after the
        # complete lineage validated, may reference a different Business
        # Authority. That version must not participate in a grant path for THIS
        # authority.
        #
        # This is ordinary nonqualification, not corruption: every row is well
        # formed and the state is completely and unambiguously resolved. A
        # malformed historical retraction or correction would already have
        # failed the resolution closed above, before this check is reached.
        rule_authority_id = getattr(rule_payload, "business_authority_id", None)
        if rule_authority_id != authority_id:
            state.partials.append(
                _nonqualification_partial(
                    state,
                    STAGE_S4_RULES,
                    OTHER_NONQUALIFICATION,
                    (BUSINESS_AUTHORITY_RULE, rule_id, rule_version.object_version),
                    explanation=_reference_mismatch_explanation(
                        object_family=BUSINESS_AUTHORITY_RULE,
                        object_id=rule_id,
                        object_version=rule_version.object_version,
                        referenced_family=BUSINESS_AUTHORITY,
                        actual_reference=rule_authority_id,
                        expected_reference=authority_id,
                    ),
                )
            )
            continue

        # -- S5  establish the referenced Business Authority Role -----------
        state.reached(STAGE_S5_ROLES)
        role_id = getattr(rule_payload, "business_authority_role_id", None)
        state.roles_referenced += 1

        if not role_id:
            defect = DefectRecord(
                reason_code=AUTHORITY_REFERENCE_DANGLING,
                stage=STAGE_S5_ROLES,
                subject=object_subject(
                    BUSINESS_AUTHORITY_RULE, rule_id, rule_version.object_version
                ),
                detail="the effective Rule version references no Business Authority Role",
            )
            state.defects.append(defect)
            state.partials.append(_defect_partial(state, defect, (BUSINESS_AUTHORITY_RULE, rule_id)))
            continue

        # THE CANDIDATE KEY CARRIES THE WHOLE ESTABLISHED PATH PREFIX, not just
        # the object being evaluated. Two Rules may legitimately reference ONE
        # Role - the same Business Authority Role carrying the authority under
        # two different scopes or parameter bands - and each is a SEPARATE
        # candidate. Keying only on the role (or only on the assignment) would
        # make those candidates collide, and the 16.4 "exactly one collection"
        # accounting would then report a spurious INTERNAL_CONTRACT_VIOLATION
        # for an entirely ordinary configuration.
        #
        # It is established BEFORE the role lineage is loaded (correction C2-4)
        # so that the two failure branches immediately below use it as well.
        # They previously keyed on the role alone, which two Rules referencing
        # one broken Role would have collided on once the reason/detail padding
        # was removed.
        role_candidate = (BUSINESS_AUTHORITY_RULE, rule_id, BUSINESS_AUTHORITY_ROLE, role_id)

        role_evaluation, load_defect = _load_lineage(
            authority_configuration_port, BUSINESS_AUTHORITY_ROLE, role_id, as_of
        )
        if load_defect is not None:
            state.defects.append(load_defect)
            state.partials.append(_defect_partial(state, load_defect, role_candidate))
            continue

        assert role_evaluation is not None
        if role_evaluation.has_defect:
            lineage_defects = _lineage_defect_records(
                BUSINESS_AUTHORITY_ROLE, role_id, role_evaluation
            )
            state.defects.extend(lineage_defects)
            state.partials.append(_defect_partial(state, lineage_defects, role_candidate))
            continue

        if role_evaluation.is_dangling:
            # DANGLING, not a gap: NO lineage material exists for the
            # referenced stable id at all. The configuration is broken, not
            # merely quiet (11.5).
            defect = DefectRecord(
                reason_code=AUTHORITY_REFERENCE_DANGLING,
                stage=STAGE_S5_ROLES,
                subject=object_subject(BUSINESS_AUTHORITY_ROLE, role_id),
                detail="a referenced Business Authority Role carries no lineage material",
            )
            state.defects.append(defect)
            state.partials.append(_defect_partial(state, defect, role_candidate))
            continue

        role_version = role_evaluation.effective_version
        if role_version is None:
            # A GAP in a referenced role's lineage. Explicitly NOT corruption
            # and explicitly NOT a dangling reference (11.5).
            state.partials.append(
                _nonqualification_partial(
                    state, STAGE_S5_ROLES, ROLE_NOT_EFFECTIVE, role_candidate
                )
            )
            continue

        # Recorded before the rejecting check, for the reason given at the
        # Rule above (correction C2-3).
        role_evidence = _evidence_for(
            BUSINESS_AUTHORITY_ROLE, role_id, role_version, role_evaluation
        )
        state.trail = state.trail.plus_object(role_evidence)

        if not role_version.active_flag:
            state.partials.append(
                _nonqualification_partial(
                    state,
                    STAGE_S5_ROLES,
                    ROLE_NOT_ACTIVE,
                    role_candidate + (role_version.object_version,),
                )
            )
            continue

        role_trail = state.trail
        state.rules_and_roles_established = True

        # -- S6  discover candidate Assignments -----------------------------
        state.reached(STAGE_S6_ASSIGNMENTS)
        try:
            assignment_ids = sorted(
                set(authority_configuration_port.find_assignment_ids_for_role(role_id))
            )
        except AuthorityConfigurationPortError:
            state.defects.append(
                DefectRecord(
                    reason_code=AUTHORITY_CONFIGURATION_UNAVAILABLE,
                    stage=STAGE_S6_ASSIGNMENTS,
                    subject=object_subject(BUSINESS_AUTHORITY_ROLE, role_id),
                    detail="the authority configuration port failed during assignment discovery",
                )
            )
            continue

        state.assignments_discovered += len(assignment_ids)

        for assignment_id in assignment_ids:
            # RESET per assignment candidate, back to the established
            # Authority + Rule + Role.
            state.trail = role_trail
            _evaluate_assignment(
                state=state,
                request=request,
                as_of=as_of,
                person_id=person_id,
                actor_person=actor_person,
                employment=employment,
                assignment_id=assignment_id,
                rule_payload=rule_payload,
                authority_evidence=authority_evidence,
                role_evidence=role_evidence,
                rule_evidence=rule_evidence,
                authority_configuration_port=authority_configuration_port,
                hr_reference_port=hr_reference_port,
                context=context,
            )


def _complete_path_fallback(
    *, specific_reason: str | None, stage: str, path: PathEvidence
) -> tuple[str, str]:
    """Choose the decisive reason for a COMPLETE nonqualifying path (FU-5).

    An EXISTING SPECIFIC REASON ALWAYS WINS. The bounded fallback is used only
    when the path is fully resolved, carries no fail-closed defect, and no
    specific path-level reason applies - in which case reporting a complete
    path with NO reason at all would be strictly worse, because the denial
    would be unexplainable.

    The explanation uses the same fixed, kernel-owned template discipline as
    the partial-evaluation one: canonical identifiers only, stable for
    identical canonical input, no provider or user prose, and no part in
    ordering or eligibility.
    """

    if specific_reason is not None:
        return specific_reason, ""

    explanation = (
        f"the complete candidate path "
        f"{path.business_authority.ref.object_id}/"
        f"{path.business_authority.ref.object_version} -> "
        f"{path.business_authority_rule.ref.object_id}/"
        f"{path.business_authority_rule.ref.object_version} -> "
        f"{path.business_authority_role.ref.object_id}/"
        f"{path.business_authority_role.ref.object_version} -> "
        f"{path.business_authority_assignment.ref.object_id}/"
        f"{path.business_authority_assignment.ref.object_version} "
        f"was fully resolved and did not qualify at stage {stage}, and no "
        f"specific path-level nonqualification reason applies"
    )
    return OTHER_NONQUALIFICATION, explanation


def _candidate_hr_evidence(
    *,
    person_id: str,
    employment: EmploymentStateReference,
    actor_person: ActorPersonReference,
    snapshots: list,
    position_version_id: str | None = None,
    incumbency_id: str | None = None,
    org_unit_version_ids: tuple[str, ...] = (),
) -> HrEvidence:
    """The HR state established for one candidate at the point it is recorded.

    Used both for a qualifying/complete path and for a PARTIAL evaluation, so a
    failure part-way through S7 or S8 still retains the canonical Position,
    Incumbency and organisation-unit references and snapshots it had already
    established, plus the one responsible for the failure (FU-2).
    """

    return HrEvidence(
        person_id=person_id,
        employment_state_version_id=employment.employment_state_version_id,
        position_version_id=position_version_id,
        incumbency_id=incumbency_id,
        org_unit_version_ids=org_unit_version_ids,
        canonical_snapshot_at_values=tuple(snapshots),
    )


def _nonqualification_partial(
    state: _Established,
    stage: str,
    reason: str,
    candidate: tuple[str, ...],
    explanation: str = "",
) -> PartialEvaluation:
    return PartialEvaluation(
        established_objects=state.trail.objects,
        last_stage_reached=stage,
        reason_code=reason,
        is_defect=False,
        detail=f"candidate could not be completed at {stage}",
        candidate_key=candidate,
        hr_evidence=state.trail.hr,
        scope_evaluation=state.trail.scope,
        parameter_evaluation=state.trail.parameters,
        nonqualification_explanation=explanation,
    )


def _reference_mismatch_explanation(
    *,
    object_family: str,
    object_id: str,
    object_version: str,
    referenced_family: str,
    actual_reference: str | None,
    expected_reference: str,
) -> str:
    """The fixed, implementation-owned template for OTHER_NONQUALIFICATION.

    Discovery is deliberately a RAW SUPERSET over published facts (9.3.1), so an
    object is legitimately discovered through a HISTORICAL reference it no
    longer carries. Once its complete lineage has been validated and its
    current effective version established, that version may belong to a
    DIFFERENT parent - an ordinary, fully understood configuration change, not
    corruption and not a defect.

    The string is built only from canonical stable identifiers and family
    names. It never contains provider text, user text or an exception message,
    it is stable for the same canonical input, and it takes no part in result
    selection or evidence ordering.
    """

    return (
        f"the current effective {object_family} version "
        f"{object_id}/{object_version} references {referenced_family} "
        f"{actual_reference or '<none>'}, not the {referenced_family} "
        f"{expected_reference} this candidate path evaluates"
    )


def _evaluate_assignment(
    *,
    state: _Established,
    request: AuthorityResolutionRequest,
    as_of: datetime,
    person_id: str,
    actor_person: ActorPersonReference,
    employment: EmploymentStateReference,
    assignment_id: str,
    rule_payload: Any,
    authority_evidence: ObjectEvidence,
    role_evidence: ObjectEvidence,
    rule_evidence: ObjectEvidence,
    authority_configuration_port: AuthorityConfigurationPort,
    hr_reference_port: CanonicalHrReferencePort,
    context: Any,
) -> None:
    """Stages S6 to S9 for one candidate Assignment."""

    # EVERY canonical snapshot actually relied upon by THIS path, in the order
    # established: actor->person, employment, then Position and Incumbency where
    # a position path is taken, then every Organisation Unit ancestry hop
    # traversed for scope. Not the freshest, not the oldest, and nothing
    # silently omitted (16.2, correction C1-3B).
    hr_snapshots: list[datetime] = [
        actor_person.canonical_snapshot_at,
        employment.canonical_snapshot_at,
    ]

    role_id = role_evidence.ref.object_id
    # The full established path prefix, for the reason recorded at the role
    # candidate key above: one Assignment reached through two different Rules
    # is two distinct candidates, and each must be accounted for separately.
    candidate = (
        BUSINESS_AUTHORITY_RULE,
        rule_evidence.ref.object_id,
        BUSINESS_AUTHORITY_ROLE,
        role_id,
        BUSINESS_AUTHORITY_ASSIGNMENT,
        assignment_id,
    )

    evaluation, load_defect = _load_lineage(
        authority_configuration_port, BUSINESS_AUTHORITY_ASSIGNMENT, assignment_id, as_of
    )
    if load_defect is not None:
        state.defects.append(load_defect)
        state.partials.append(_defect_partial(state, load_defect, candidate))
        return

    assert evaluation is not None
    if evaluation.has_defect:
        lineage_defects = _lineage_defect_records(
            BUSINESS_AUTHORITY_ASSIGNMENT, assignment_id, evaluation
        )
        state.defects.extend(lineage_defects)
        state.partials.append(_defect_partial(state, lineage_defects, candidate))
        return

    if evaluation.is_dangling:
        defect = DefectRecord(
            reason_code=AUTHORITY_REFERENCE_DANGLING,
            stage=STAGE_S6_ASSIGNMENTS,
            subject=object_subject(BUSINESS_AUTHORITY_ASSIGNMENT, assignment_id),
            detail="a discovered Assignment carries no lineage material",
        )
        state.defects.append(defect)
        state.partials.append(_defect_partial(state, defect, candidate))
        return

    version = evaluation.effective_version
    if version is None:
        state.partials.append(
            _nonqualification_partial(
                state, STAGE_S6_ASSIGNMENTS, ASSIGNMENT_NOT_EFFECTIVE, candidate
            )
        )
        return

    # Recorded before the rejecting checks, for the reason given at the Rule
    # above (correction C2-3).
    assignment_evidence = _evidence_for(
        BUSINESS_AUTHORITY_ASSIGNMENT, assignment_id, version, evaluation
    )
    state.trail = state.trail.plus_object(assignment_evidence)

    if not version.active_flag:
        state.partials.append(
            _nonqualification_partial(
                state, STAGE_S6_ASSIGNMENTS, ASSIGNMENT_NOT_ACTIVE, candidate
            )
        )
        return

    payload = version.payload

    # RAW SUPERSET DISCOVERY MUST NOT GRANT THROUGH A HISTORICAL PARENT
    # REFERENCE (correction C1-1, case B) - the same rule as for the Rule
    # above, one level down. This Assignment was legitimately discovered
    # because some raw published version of it carries THIS role's stable id.
    # Its CURRENT EFFECTIVE version may reference a different Business
    # Authority Role, and that version must not participate in this role's
    # path.
    assignment_role_id = getattr(payload, "business_authority_role_id", None)
    if assignment_role_id != role_id:
        state.partials.append(
            _nonqualification_partial(
                state,
                STAGE_S6_ASSIGNMENTS,
                OTHER_NONQUALIFICATION,
                candidate + (version.object_version,),
                explanation=_reference_mismatch_explanation(
                    object_family=BUSINESS_AUTHORITY_ASSIGNMENT,
                    object_id=assignment_id,
                    object_version=version.object_version,
                    referenced_family=BUSINESS_AUTHORITY_ROLE,
                    actual_reference=assignment_role_id,
                    expected_reference=role_id,
                ),
            )
        )
        return

    # -- S7  resolve the assignment target against this person --------------
    state.reached(STAGE_S7_TARGET)
    target_person = getattr(payload, "person_id", None)
    target_position = getattr(payload, "position_id", None)

    if (target_person is None) == (target_position is None):
        # EXACTLY ONE of person_id / position_id must be present. Neither and
        # both are invalid and FAIL CLOSED; they are never silently coerced
        # (invariant I-4).
        defect = DefectRecord(
            reason_code=ASSIGNMENT_TARGET_INVALID,
            stage=STAGE_S7_TARGET,
            subject=object_subject(
                BUSINESS_AUTHORITY_ASSIGNMENT, assignment_id, version.object_version
            ),
            detail=(
                "assignment carries both person_id and position_id"
                if target_person is not None
                else "assignment carries neither person_id nor position_id"
            ),
        )
        state.defects.append(defect)
        state.partials.append(_defect_partial(state, defect, candidate))
        return

    position_version_id: str | None = None
    incumbency_id: str | None = None

    if target_person is not None:
        if target_person != person_id:
            state.partials.append(
                _nonqualification_partial(
                    state, STAGE_S7_TARGET, ASSIGNMENT_TARGET_NOT_THIS_PERSON, candidate
                )
            )
            return
    else:
        position_answer = _resolve_hr(
            hr_reference_port.get_position(target_position, as_of),
            expected_type=PositionVersionReference,
            # IDENTITY BINDING: a Position reference identifying a DIFFERENT
            # canonical position must never be used as this one (FU-1).
            identity_attribute="position_id",
            expected_identity=target_position,
            reference_attribute="position_version_id",
            missing_reason=POSITION_STATE_MISSING,
            ambiguous_reason=POSITION_STATE_AMBIGUOUS,
            as_of=as_of,
            threshold_seconds=request.hr_staleness_threshold_seconds,
        )
        if position_answer.defect_reason is not None:
            # The Position that CAUSED the failure is retained where it was
            # identity-bound (a stale answer); it is omitted where it was not
            # about the requested position at all (FU-1, FU-2).
            state.trail = state.trail.with_hr(
                _candidate_hr_evidence(
                    person_id=person_id,
                    employment=employment,
                    actor_person=actor_person,
                    snapshots=hr_snapshots
                    + [
                        value
                        for value in (position_answer.observed_snapshot_at,)
                        if value is not None
                    ],
                    position_version_id=position_answer.observed_reference,
                )
            )
            defect = DefectRecord(
                reason_code=position_answer.defect_reason,
                stage=STAGE_S7_TARGET,
                subject=object_subject(
                    BUSINESS_AUTHORITY_ASSIGNMENT, assignment_id, version.object_version
                ),
                detail=f"the position state was not established: {position_answer.detail}",
            )
            state.defects.append(defect)
            state.partials.append(_defect_partial(state, defect, candidate))
            return

        position = position_answer.value
        position_version_id = position.position_version_id
        hr_snapshots.append(position.canonical_snapshot_at)
        state.note_snapshot(position.canonical_snapshot_at)

        # INCUMBENCY IS RE-RESOLVED AT THE SAME as_of EVERY TIME, and is never
        # inferred from history: a position assignment NEVER confers authority
        # on a former incumbent (12.1, attack surface 20).
        incumbency_answer = _resolve_hr(
            hr_reference_port.get_incumbency(target_position, as_of),
            expected_type=IncumbencyReference,
            # IDENTITY BINDING: an incumbency whose own canonical position is a
            # DIFFERENT position must never be accepted for this one (FU-1).
            identity_attribute="position_id",
            expected_identity=target_position,
            reference_attribute="incumbency_id",
            missing_reason=INCUMBENCY_MISSING,
            ambiguous_reason=INCUMBENCY_AMBIGUOUS,
            as_of=as_of,
            threshold_seconds=request.hr_staleness_threshold_seconds,
        )
        if incumbency_answer.defect_reason is not None:
            state.trail = state.trail.with_hr(
                _candidate_hr_evidence(
                    person_id=person_id,
                    employment=employment,
                    actor_person=actor_person,
                    snapshots=hr_snapshots
                    + [
                        value
                        for value in (incumbency_answer.observed_snapshot_at,)
                        if value is not None
                    ],
                    position_version_id=position_version_id,
                    incumbency_id=incumbency_answer.observed_reference,
                )
            )
            defect = DefectRecord(
                reason_code=incumbency_answer.defect_reason,
                stage=STAGE_S7_TARGET,
                subject=object_subject(
                    BUSINESS_AUTHORITY_ASSIGNMENT, assignment_id, version.object_version
                ),
                detail=f"the incumbency was not established: {incumbency_answer.detail}",
            )
            state.defects.append(defect)
            state.partials.append(_defect_partial(state, defect, candidate))
            return

        incumbency = incumbency_answer.value
        incumbency_id = incumbency.incumbency_id
        hr_snapshots.append(incumbency.canonical_snapshot_at)
        state.note_snapshot(incumbency.canonical_snapshot_at)

        if incumbency.person_id != person_id:
            state.partials.append(
                _nonqualification_partial(
                    state, STAGE_S7_TARGET, ASSIGNMENT_TARGET_NOT_THIS_PERSON, candidate
                )
            )
            return

    state.assignment_targeted_person = True

    hr_evidence = _candidate_hr_evidence(
        person_id=person_id,
        employment=employment,
        actor_person=actor_person,
        snapshots=hr_snapshots,
        position_version_id=position_version_id,
        incumbency_id=incumbency_id,
    )
    state.trail = state.trail.with_hr(hr_evidence)

    # The path is now COMPLETE: all four (object_id, object_version) pairs are
    # established and the assignment target matches this person (12.2). S8 and
    # S9 decide whether it QUALIFIES or is a COMPLETE NONQUALIFYING path.
    path_key = path_subject(
        business_authority_role_id=role_evidence.ref.object_id,
        business_authority_role_version=role_evidence.ref.object_version,
        business_authority_id=authority_evidence.ref.object_id,
        business_authority_version=authority_evidence.ref.object_version,
        business_authority_rule_id=rule_evidence.ref.object_id,
        business_authority_rule_version=rule_evidence.ref.object_version,
        business_authority_assignment_id=assignment_evidence.ref.object_id,
        business_authority_assignment_version=assignment_evidence.ref.object_version,
    )

    # -- S8  evaluate composed scope ----------------------------------------
    state.reached(STAGE_S8_SCOPE)
    rule_operand = scope.evaluate_operand(
        operand_role=scope.OPERAND_RULE,
        scope_type=getattr(rule_payload, "scope_type", None),
        scope_id=getattr(rule_payload, "scope_id", None),
        context_scope_type=context.scope_type,
        context_scope_id=context.scope_id,
        hr_port=hr_reference_port,
        as_of=as_of,
        hr_unavailable_reason=HR_REFERENCE_UNAVAILABLE,
        hr_stale_reason=HR_REFERENCE_STALE,
        staleness_threshold_seconds=request.hr_staleness_threshold_seconds,
    )
    assignment_operand = scope.evaluate_operand(
        operand_role=scope.OPERAND_ASSIGNMENT,
        scope_type=getattr(payload, "scope_type", None),
        scope_id=getattr(payload, "scope_id", None),
        context_scope_type=context.scope_type,
        context_scope_id=context.scope_id,
        hr_port=hr_reference_port,
        as_of=as_of,
        hr_unavailable_reason=HR_REFERENCE_UNAVAILABLE,
        hr_stale_reason=HR_REFERENCE_STALE,
        staleness_threshold_seconds=request.hr_staleness_threshold_seconds,
    )
    composed = scope.compose(rule_operand, assignment_operand)

    traversed_org_units = (
        rule_operand.org_unit_versions_traversed
        + assignment_operand.org_unit_versions_traversed
    )
    for org_unit in traversed_org_units:
        hr_snapshots.append(org_unit.canonical_snapshot_at)
        state.note_snapshot(org_unit.canonical_snapshot_at)

    hr_evidence = HrEvidence(
        person_id=hr_evidence.person_id,
        employment_state_version_id=hr_evidence.employment_state_version_id,
        position_version_id=hr_evidence.position_version_id,
        incumbency_id=hr_evidence.incumbency_id,
        org_unit_version_ids=tuple(
            org_unit.org_unit_version_id for org_unit in traversed_org_units
        ),
        canonical_snapshot_at_values=tuple(hr_snapshots),
    )

    scope_evidence = ScopeEvidence(
        rule_scope_type=rule_operand.scope_type,
        rule_scope_id=rule_operand.scope_id,
        rule_operand_satisfied=rule_operand.satisfied,
        assignment_scope_type=assignment_operand.scope_type,
        assignment_scope_id=assignment_operand.scope_id,
        assignment_operand_satisfied=assignment_operand.satisfied,
        composed_satisfied=composed.satisfied,
        detail=composed.detail,
    )
    state.trail = state.trail.with_scope(scope_evidence).with_hr(hr_evidence)

    if composed.is_defect:
        defect = DefectRecord(
            reason_code=composed.defect_reason,  # type: ignore[arg-type]
            stage=STAGE_S8_SCOPE,
            subject=path_key,
            detail=composed.detail,
        )
        state.defects.append(defect)
        state.partials.append(_defect_partial(state, defect, candidate))
        return

    # -- S9  evaluate parameters --------------------------------------------
    state.reached(STAGE_S9_PARAMETERS)
    evaluator_result = evaluators.evaluate(
        getattr(rule_payload, "parameter_evaluator_type", None),
        getattr(rule_payload, "parameter_payload", None),
        dict(context.declared_facts),
    )
    parameter_evidence = ParameterEvidence(
        evaluator_type=evaluator_result.evaluator_type,
        satisfied=evaluator_result.satisfied,
        decisive_comparison=evaluator_result.decisive_comparison,
    )
    state.trail = state.trail.with_parameters(parameter_evidence)

    if evaluator_result.is_defect:
        defect = DefectRecord(
            reason_code=evaluator_result.defect_reason,  # type: ignore[arg-type]
            stage=STAGE_S9_PARAMETERS,
            subject=path_key,
            detail=evaluator_result.detail,
        )
        state.defects.append(defect)
        state.partials.append(_defect_partial(state, defect, candidate))
        return

    path = PathEvidence(
        business_authority_role=role_evidence,
        business_authority=authority_evidence,
        business_authority_rule=rule_evidence,
        business_authority_assignment=assignment_evidence,
        hr_evidence=hr_evidence,
        scope_evaluation=scope_evidence,
        parameter_evaluation=parameter_evidence,
    )

    if not composed.satisfied:
        # THE BOUNDED FALLBACK ON A COMPLETE PATH (correction FU-5). Scope
        # composition normally yields a SPECIFIC reason, and where it does that
        # reason is used unchanged. This branch covers a fully resolved,
        # well-understood non-match for which no specific reason applies. It is
        # retained as a defensive branch in the same spirit as the 11.4a
        # single-effective-version invariant: unreachable through the current
        # ports, and kept so a future scope predicate that legitimately has no
        # specific reason cannot silently produce a complete path with NO
        # reason at all.
        reason, explanation = _complete_path_fallback(
            specific_reason=composed.nonqualification_reason,
            stage=STAGE_S8_SCOPE,
            path=path,
        )
        state.nonqualifying.append(
            PathEvidence(
                business_authority_role=path.business_authority_role,
                business_authority=path.business_authority,
                business_authority_rule=path.business_authority_rule,
                business_authority_assignment=path.business_authority_assignment,
                hr_evidence=path.hr_evidence,
                scope_evaluation=path.scope_evaluation,
                parameter_evaluation=path.parameter_evaluation,
                decisive_nonqualification_reason=reason,
                nonqualification_explanation=explanation,
            )
        )
        return

    if not evaluator_result.satisfied:
        # The same bounded fallback at S9. EVALUATOR_CONDITION_NOT_SATISFIED is
        # the specific reason wherever it applies, and is used unchanged.
        reason, explanation = _complete_path_fallback(
            specific_reason=evaluator_result.nonqualification_reason,
            stage=STAGE_S9_PARAMETERS,
            path=path,
        )
        state.nonqualifying.append(
            PathEvidence(
                business_authority_role=path.business_authority_role,
                business_authority=path.business_authority,
                business_authority_rule=path.business_authority_rule,
                business_authority_assignment=path.business_authority_assignment,
                hr_evidence=path.hr_evidence,
                scope_evaluation=path.scope_evaluation,
                parameter_evaluation=path.parameter_evaluation,
                decisive_nonqualification_reason=reason,
                nonqualification_explanation=explanation,
            )
        )
        return

    state.qualifying.append(path)


def _build_result(
    *,
    request: AuthorityResolutionRequest,
    as_of: datetime,
    state: _Established,
    evaluated_context: EvaluatedBusinessContext,
    outcome: str,
    status: str,
    reason: str,
) -> AuthorityResolutionResult:
    """Assemble the result, order every collection, then CHECK THE INVARIANTS."""

    ordered_defects = order_defects(tuple(state.defects))
    qualifying = order_paths(tuple(state.qualifying))
    nonqualifying = order_paths(tuple(state.nonqualifying))
    partials = order_partials(tuple(state.partials))

    established_state = EstablishedState(
        person_id=state.person_id,
        employment_state_version_id=state.employment_state_version_id,
        employment_status=state.employment_status,
        requested_authority=state.requested_authority,
        requested_authority_eligibility=state.requested_authority_eligibility,
        rules_discovered=state.rules_discovered,
        roles_referenced=state.roles_referenced,
        assignments_discovered=state.assignments_discovered,
        complete_paths_evaluated=len(qualifying) + len(nonqualifying),
        canonical_snapshot_at_values=tuple(state.snapshots),
        last_stage_reached=state.last_stage,
    )

    result = AuthorityResolutionResult(
        outcome=outcome,
        resolution_status=status,
        result_level_reason=reason,
        authority_code=request.authority_code,
        as_of=as_of,
        actor_user_public_id=request.authenticated_actor.actor_user_public_id,
        established_state=established_state,
        business_context=evaluated_context,
        qualifying_paths=qualifying,
        complete_nonqualifying_paths=nonqualifying,
        partial_evaluations=partials,
        ordered_defects=ordered_defects,
    )

    violation = _kernel_invariant_violation(result)
    if violation is None:
        return result

    # A violated kernel invariant that is NOT authority-version multiplicity
    # fails closed with INTERNAL_CONTRACT_VIOLATION, and is NEVER degraded to
    # a plain DENY (14.3).
    violation_defect = DefectRecord(
        reason_code=INTERNAL_CONTRACT_VIOLATION,
        stage=state.last_stage,
        subject=dependency_subject(
            SUBJECT_TOKEN_KERNEL_INVARIANT,
            canonical_request_key(
                authority_code=request.authority_code,
                actor_user_public_id=request.authenticated_actor.actor_user_public_id,
                person_id=state.person_id,
                scope_type=evaluated_context.scope_type,
                scope_id=evaluated_context.scope_id,
            ),
        ),
        detail=violation,
    )
    return AuthorityResolutionResult(
        outcome=OUTCOME_DENY,
        resolution_status=STATUS_FAIL_CLOSED,
        result_level_reason=INTERNAL_CONTRACT_VIOLATION,
        authority_code=request.authority_code,
        as_of=as_of,
        actor_user_public_id=request.authenticated_actor.actor_user_public_id,
        established_state=established_state,
        business_context=evaluated_context,
        qualifying_paths=(),
        complete_nonqualifying_paths=(),
        partial_evaluations=(
            PartialEvaluation(
                established_objects=(),
                last_stage_reached=state.last_stage,
                reason_code=INTERNAL_CONTRACT_VIOLATION,
                is_defect=True,
                detail=violation,
                defects=(violation_defect,),
                candidate_key=("kernel-invariant",),
            ),
        ),
        ordered_defects=(violation_defect,),
    )


def _kernel_invariant_violation(result: AuthorityResolutionResult) -> str | None:
    """Cheap, explicit self-checks over the assembled result.

    These exist so that a future refactor that breaks one of them fails closed
    LOUDLY rather than silently granting authority. An implementation that
    removes them as "dead code" has removed the one guard that would catch its
    own regression.
    """

    if result.outcome == OUTCOME_ALLOW:
        if result.resolution_status != STATUS_RESOLVED:
            return "ALLOW was produced with a resolution_status other than RESOLVED"
        if not result.qualifying_paths:
            return "ALLOW was produced with no qualifying path"

    if result.resolution_status == STATUS_FAIL_CLOSED:
        if result.outcome != OUTCOME_DENY:
            return "FAIL_CLOSED was produced with an outcome other than DENY"
        if not result.ordered_defects:
            return "FAIL_CLOSED was produced with no recorded defect"
        if result.result_level_reason != result.ordered_defects[0].reason_code:
            return "result_level_reason is not the reason of the first defect under the total order"
        if result.result_level_reason == OTHER_NONQUALIFICATION:
            return "the bounded nonqualification fallback was reported as a fail-closed reason"

    # THE BOUNDED FALLBACK MAY CONTRIBUTE ONLY TO DENY + RESOLVED, and never to
    # a grant. It is an ORDINARY nonqualification, so - exactly like every
    # other path-level reason (15.1, NS-AG-02) - it may legitimately appear in
    # the evidence of a resolution whose ALLOW came from a DIFFERENT,
    # independently qualifying path. What it may never do is sit on a
    # qualifying path or be the result-level reason of an ALLOW.
    if result.result_level_reason == OTHER_NONQUALIFICATION and (
        result.outcome != OUTCOME_DENY or result.resolution_status != STATUS_RESOLVED
    ):
        return "the bounded nonqualification fallback was reported outside DENY + RESOLVED"

    for partial in result.partial_evaluations:
        if partial.reason_code != OTHER_NONQUALIFICATION:
            continue
        if partial.is_defect:
            return "the bounded nonqualification fallback was recorded as a defect"
        if not partial.nonqualification_explanation:
            return "the bounded nonqualification fallback carries no deterministic explanation"

    # THE FALLBACK ON A COMPLETE PATH IS PERMITTED (correction FU-5), under
    # exactly the same bounded conditions as on a partial: never on a
    # QUALIFYING path, and never without its deterministic explanation.
    for path in result.qualifying_paths:
        if path.decisive_nonqualification_reason is not None:
            return "a qualifying path carried a nonqualification reason"
        if path.nonqualification_explanation:
            return "a qualifying path carried a nonqualification explanation"

    for path in result.complete_nonqualifying_paths:
        if path.decisive_nonqualification_reason == OTHER_NONQUALIFICATION:
            if not path.nonqualification_explanation:
                return (
                    "a complete path carried the bounded nonqualification fallback with no "
                    "deterministic explanation"
                )
        elif path.nonqualification_explanation:
            return (
                "a complete path carried a bounded-fallback explanation without the bounded "
                "fallback reason"
            )

    # Every candidate the kernel touched appears in EXACTLY ONE of the three
    # evidence collections (16.4).
    seen: list[tuple[str, ...]] = []
    for path in result.qualifying_paths + result.complete_nonqualifying_paths:
        if path.candidate_key in seen:
            return "a candidate appears in more than one evidence collection"
        seen.append(path.candidate_key)
    for partial in result.partial_evaluations:
        if partial.candidate_key in seen:
            return "a candidate appears in more than one evidence collection"
        seen.append(partial.candidate_key)

    return None
