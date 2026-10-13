"""Fail-closed defect records and the TOTAL canonical defect sort key.

PF-1A-E2-A section 15.5.

Section 12.2 orders STAGES. That is not enough: two relevant defects with
different reason codes can arise at the SAME stage, and without a further
tie-break the reported reason would depend on provider order, SQL row order,
dictionary iteration order, path traversal order or concurrency (F-08). This
module defines the total order that removes that dependence.

    result_level_reason on a DENY + FAIL_CLOSED result is EXACTLY the reason
    code of the FIRST defect under this order - never "the first defect
    observed".

The SAME single order also sequences the partial/failed evaluation evidence
(16.5), deliberately, so that the first item in that collection and the
result-level reason can never disagree about which defect is first.

PROHIBITED as any component of the key: a process/memory address, an object
identity hash, a provider row number, a query or iteration position, a
wall-clock reading, a randomly generated UUID, a thread/task id, or any other
value not derived from stable, reproducible domain data (attack surface 25a).
Every component below is a string drawn from canonical domain identifiers or
from the defect record's own declared fields.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.modules.authorization.business_authority.contract import (
    OBJECT_FAMILY_RANK,
    REASON_CODE_RANK,
    STAGE_RANK,
    SUBJECT_FORM_DEPENDENCY,
    SUBJECT_FORM_OBJECT,
    SUBJECT_FORM_PATH,
    SUBJECT_TOKEN_RANK,
)
from app.modules.authorization.business_authority.domain import ObjectVersionRef

# The canonical subject key is a fixed-arity tuple of strings behind its form
# rank, so the three forms of 15.5 are mutually orderable and every comparison
# is between like types. Nine components is exactly what form (b) needs.
_SUBJECT_KEY_ARITY = 9


@dataclass(frozen=True)
class CanonicalSubject:
    """WHAT a defect is about, in one of the three mutually-orderable forms."""

    form_rank: int
    components: tuple[str, ...]

    @property
    def sort_key(self) -> tuple[int, tuple[str, ...]]:
        return (self.form_rank, self.components)


def _pad(values: list[str]) -> tuple[str, ...]:
    return tuple(values + [""] * (_SUBJECT_KEY_ARITY - len(values)))


def object_subject(
    object_family: str, object_id: str, object_version: str | None = None
) -> CanonicalSubject:
    """Form (a) OBJECT-BACKED SUBJECT.

    `object_version` is included ONLY when it has been established. When the
    defect concerns the object's lineage AS A WHOLE rather than one version,
    it sorts as the empty/lowest value, so lineage-level defects precede
    version-level defects for the same object.
    """

    family_rank = OBJECT_FAMILY_RANK[object_family]
    return CanonicalSubject(
        form_rank=SUBJECT_FORM_OBJECT,
        components=_pad([f"{family_rank:02d}", object_id, object_version or ""]),
    )


def path_subject(
    business_authority_role_id: str | None = None,
    business_authority_role_version: str | None = None,
    business_authority_id: str | None = None,
    business_authority_version: str | None = None,
    business_authority_rule_id: str | None = None,
    business_authority_rule_version: str | None = None,
    business_authority_assignment_id: str | None = None,
    business_authority_assignment_version: str | None = None,
) -> CanonicalSubject:
    """Form (b) PATH-BACKED SUBJECT.

    Assembled ONLY from the stable IDs and versions ALREADY ESTABLISHED for
    that candidate path, in the fixed field order of section 15.4, with
    unestablished trailing fields sorting as the empty/lowest value.
    """

    return CanonicalSubject(
        form_rank=SUBJECT_FORM_PATH,
        components=_pad(
            [
                business_authority_role_id or "",
                business_authority_role_version or "",
                business_authority_id or "",
                business_authority_version or "",
                business_authority_rule_id or "",
                business_authority_rule_version or "",
                business_authority_assignment_id or "",
                business_authority_assignment_version or "",
            ]
        ),
    )


def dependency_subject(subject_token: str, canonical_request_key: str) -> CanonicalSubject:
    """Form (c) PROVIDER / ABSENCE / DEPENDENCY SUBJECT.

    `subject_token` comes from the CLOSED, fixed-rank vocabulary in
    `contract.SUBJECT_TOKEN_RANK`; `canonical_request_key` is built only from
    canonical request identifiers already established.
    """

    token_rank = SUBJECT_TOKEN_RANK[subject_token]
    return CanonicalSubject(
        form_rank=SUBJECT_FORM_DEPENDENCY,
        components=_pad([f"{token_rank:02d}", canonical_request_key]),
    )


def canonical_request_key(
    authority_code: str,
    actor_user_public_id: str,
    person_id: str | None,
    scope_type: str | None,
    scope_id: str | None,
) -> str:
    """The canonical request identity used by form (c).

    Built only from canonical request identifiers already established:
    the requested authority_code, the authenticated actor's application-user
    public identifier, the canonical person_id where S1 has succeeded, and the
    canonical scope identity of the business context. It contains no
    credential, no provider identifier and no clock reading.
    """

    return "|".join(
        [
            authority_code,
            actor_user_public_id,
            person_id or "",
            scope_type or "",
            scope_id or "",
        ]
    )


@dataclass(frozen=True)
class DefectRecord:
    """One fail-closed defect, with everything the 15.5 order needs.

    `established` records the evidence items that WERE successfully
    established before this defect was reached, in the order established. It
    never contains a fabricated, placeholder or guessed object/version pair
    (16.4).
    """

    reason_code: str
    stage: str
    subject: CanonicalSubject
    detail: str
    established: tuple[ObjectVersionRef, ...] = ()

    @property
    def sort_key(self) -> tuple[int, tuple[int, tuple[str, ...]], int, tuple[str, ...]]:
        """The canonical defect sort key, compared lexicographically.

            1. stage_rank
            2. canonical_subject_key
            3. reason_code_rank
            4. evidence_discriminator

        Component 4 is used only when 1-3 are still equal. It is built from
        the defect record's own stable declared fields, in a fixed field
        order, and contains no nondeterministic value of any kind. It exists
        because one subject can legitimately carry two defects with the same
        reason code - a single version missing both its
        publication_reference_id and its published_at is the worked example -
        and the order must still be total.
        """

        return (
            STAGE_RANK[self.stage],
            self.subject.sort_key,
            REASON_CODE_RANK[self.reason_code],
            (self.detail,),
        )


def order_defects(defects: tuple[DefectRecord, ...]) -> tuple[DefectRecord, ...]:
    """Sort defects into the one total order. The first is the decisive one."""

    return tuple(sorted(defects, key=lambda defect: defect.sort_key))
