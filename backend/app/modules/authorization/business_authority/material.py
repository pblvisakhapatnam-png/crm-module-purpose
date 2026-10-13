"""The DTO / PORT WELL-FORMEDNESS boundary.

PF-1A-E2-A sections 9.3.3 and 9.3.4.

This module owns exactly ONE question, and it is not a semantic one:

    Is this material a published-version record at all?

A record missing a DTO-REQUIRED constituent (9.3.4) is not a published
version; it is a provider that failed to supply conforming material. Such
material is rejected HERE, at the port boundary, and the resolution fails
closed with AUTHORITY_CONFIGURATION_UNAVAILABLE (9.3.3). No placeholder value
is substituted for the missing field, and NO new reason code is invented -
inventing `AUTHORITY_EFFECTIVE_FROM_MISSING` to mirror a NOT NULL constraint
is exactly the fabrication section 9.7 prohibits.

WHAT THIS MODULE MUST NEVER DO. It must not validate anything the kernel
already owns: not the person/position XOR, not provenance presence, not
provenance enum membership, not the declared_effective_to / effective_from
relationship, not identity uniqueness, and not any referential relationship.
Each of those already has a semantic classification in this contract, and
rejecting it here would make that rule permanently unreachable and untestable
(9.3.4), destroying the class B1 coverage the verification contract depends on
(attack surface 17b).

THE BOUNDARY SPLIT, stated once so a test can assert which side it exercises:

    DTO / PORT WELL-FORMEDNESS   B1-06 (absent effective_from),
                                 B1-07 (absent active_flag)
                                 -> AUTHORITY_CONFIGURATION_UNAVAILABLE
    PURE KERNEL                  B1-01..B1-05, B1-08a, B1-08b, B1-09a,
                                 B1-09b, B1-10
                                 -> the specific fail-closed code each names
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from app.modules.authorization.business_authority.contract import (
    COMPLETENESS_COMPLETE,
    COMPLETENESS_UNAVAILABLE,
    OBJECT_FAMILIES,
)
from app.modules.authorization.business_authority.domain import (
    LineageMaterial,
    PublishedObjectVersion,
    RetractionAssertion,
)
from app.modules.hr_reference.contract import is_conforming_instant

# Report kinds. Both surface as AUTHORITY_CONFIGURATION_UNAVAILABLE; they are
# distinguished only so the evidence can say which of the two conditions the
# provider presented.
MATERIAL_ILL_FORMED = "ILL_FORMED_MATERIAL"
MATERIAL_UNAVAILABLE = "COMPLETENESS_UNAVAILABLE"


@dataclass(frozen=True)
class MaterialRejection:
    """Why the port could not accept this material as conforming facts.

    DELIBERATELY CARRIES NO LIST INDEX, NO ITERATION POSITION AND NO PROVIDER
    PROSE (correction FU-4). `subject` names the offending record by its own
    canonical identity where it has one, and `field` names the DTO-required
    constituent that was absent or ill-typed. Both are drawn from a closed set
    of kernel-owned strings, so the resulting canonical evidence is stable
    under provider row reordering and identical across providers that fail the
    same way.
    """

    kind: str
    subject: str
    field: str

    @property
    def detail(self) -> str:
        return f"{self.subject}: {self.field}"


# The record whose identity could not itself be established. Using a fixed
# token rather than a position keeps the evidence deterministic when the
# provider reorders its rows.
_UNIDENTIFIED_VERSION = "an unidentified version record"
_UNIDENTIFIED_RETRACTION = "an unidentified retraction assertion"


def _bad(kind: str, subject: str, field: str) -> MaterialRejection:
    return MaterialRejection(kind=kind, subject=subject, field=field)


def _version_subject(version: object) -> str:
    object_version = getattr(version, "object_version", None)
    if isinstance(object_version, str) and object_version:
        return f"version {object_version}"
    return _UNIDENTIFIED_VERSION


def _check_version(version: object) -> MaterialRejection | None:
    if not isinstance(version, PublishedObjectVersion):
        return _bad(MATERIAL_ILL_FORMED, _UNIDENTIFIED_VERSION, "is not a published version record")

    subject = _version_subject(version)

    # DTO-REQUIRED: object_version, effective_from, active_flag, payload.
    if not isinstance(version.object_version, str) or not version.object_version:
        return _bad(MATERIAL_ILL_FORMED, subject, "object_version is absent or ill-typed")
    # A NAIVE datetime is ill-typed here, not merely unusual: it names no
    # instant, so comparing it against the authorization instant would either
    # raise or silently guess a timezone (correction C2-2). It is rejected at
    # this boundary for exactly the reason an absent value is - such a record
    # is not a published version - and takes the same existing reason code.
    if not is_conforming_instant(version.effective_from):
        return _bad(
            MATERIAL_ILL_FORMED,
            subject,
            "effective_from is absent, ill-typed or not a timezone-aware instant",
        )

    # `declared_effective_to` is DTO-OPTIONAL, so ABSENT is legitimate ("no
    # known end") and is not checked here. A PRESENT value must still be a
    # conforming instant, because 11.4 compares it against effective_from and
    # against the next successor's start.
    if version.declared_effective_to is not None and not is_conforming_instant(
        version.declared_effective_to
    ):
        return _bad(
            MATERIAL_ILL_FORMED,
            subject,
            "declared_effective_to is present but is not a timezone-aware instant",
        )
    # `bool` is checked exactly: an int, a string or None is not an active_flag.
    if not isinstance(version.active_flag, bool):
        return _bad(MATERIAL_ILL_FORMED, subject, "active_flag is absent or ill-typed")
    if version.payload is None:
        return _bad(MATERIAL_ILL_FORMED, subject, "payload is absent")

    # DELIBERATELY NOT CHECKED HERE, because the kernel already classifies
    # each of them: declared_effective_to versus effective_from (I-6),
    # corrects_object_version, publication_reference_type / _id, published_at
    # (11.6, 11.7, 11.8.3), and the assignment person/position XOR (I-4).
    return None


def _check_retraction(assertion: object) -> MaterialRejection | None:
    if not isinstance(assertion, RetractionAssertion):
        return _bad(
            MATERIAL_ILL_FORMED, _UNIDENTIFIED_RETRACTION, "is not a retraction assertion"
        )

    retraction_id = assertion.retraction_id
    subject = (
        f"retraction assertion {retraction_id}"
        if isinstance(retraction_id, str) and retraction_id
        else _UNIDENTIFIED_RETRACTION
    )

    # DTO-REQUIRED: retraction_id, object_version.
    if not isinstance(assertion.retraction_id, str) or not assertion.retraction_id:
        return _bad(MATERIAL_ILL_FORMED, subject, "retraction_id is absent or ill-typed")
    if not isinstance(assertion.object_version, str) or not assertion.object_version:
        return _bad(MATERIAL_ILL_FORMED, subject, "object_version is absent or ill-typed")

    # retracted_at and provenance are DTO-OPTIONAL and kernel-validated.
    return None


def check_material_well_formed(material: object) -> MaterialRejection | None:
    """Return why this material cannot be accepted, or None if it conforms.

    A `None` return means the material is WELL FORMED and must reach the
    kernel, which then classifies its semantic content. It emphatically does
    not mean the material is valid.
    """

    if not isinstance(material, LineageMaterial):
        return _bad(MATERIAL_ILL_FORMED, "the material", "is not lineage material")

    if material.completeness == COMPLETENESS_UNAVAILABLE:
        # An explicit, honest "I cannot return the complete set". This is the
        # correct provider behaviour, and it still fails the resolution closed.
        return _bad(MATERIAL_UNAVAILABLE, "the material", "completeness is UNAVAILABLE")

    if material.completeness != COMPLETENESS_COMPLETE:
        return _bad(
            MATERIAL_ILL_FORMED, "the material", "completeness is absent or outside the two defined values"
        )

    if not isinstance(material.object_family, str) or material.object_family not in OBJECT_FAMILIES:
        return _bad(
            MATERIAL_ILL_FORMED, "the material", "object_family is absent or outside the four families"
        )

    if not isinstance(material.object_id, str) or not material.object_id:
        return _bad(MATERIAL_ILL_FORMED, "the material", "object_id is absent or ill-typed")

    if not isinstance(material.versions, Sequence) or isinstance(material.versions, (str, bytes)):
        return _bad(MATERIAL_ILL_FORMED, "the material", "versions is absent or is not a sequence")

    if not isinstance(material.retraction_assertions, Sequence) or isinstance(
        material.retraction_assertions, (str, bytes)
    ):
        return _bad(
            MATERIAL_ILL_FORMED, "the material", "retraction_assertions is absent or is not a sequence"
        )

    # Records are checked in a CANONICAL order rather than provider order, so
    # that a provider which reorders its rows cannot change WHICH rejection is
    # reported and therefore cannot change the canonical evidence (FU-4).
    for version in sorted(
        material.versions, key=lambda v: str(getattr(v, "object_version", "") or "")
    ):
        rejection = _check_version(version)
        if rejection is not None:
            return rejection

    for assertion in sorted(
        material.retraction_assertions,
        key=lambda a: (
            str(getattr(a, "object_version", "") or ""),
            str(getattr(a, "retraction_id", "") or ""),
        ),
    ):
        rejection = _check_retraction(assertion)
        if rejection is not None:
            return rejection

    return None
