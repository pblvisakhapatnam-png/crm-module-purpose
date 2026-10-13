"""Provider-neutral HR / actor-person PORTS (protocols only).

PF-1A-E2-A sections 9.1 and 9.2. No implementation of any real provider lives
here, and none may. The reference/synthetic implementations used to make the
kernel's semantics deterministically provable are TEST-ONLY and live under
`backend/tests/fixtures/` (PF_1A_E2_A 9.6), so their production
unreachability is structural rather than merely asserted.
"""

from __future__ import annotations

from datetime import datetime
from typing import Protocol, runtime_checkable

from app.modules.hr_reference.contract import HrLookup


@runtime_checkable
class ActorPersonPort(Protocol):
    """Resolves an authenticated application actor to its canonical person.

    The input is ALWAYS the authenticated actor's own application-user public
    identifier. A client-supplied person_id, employee code, username or
    display name is never accepted as the identity being authorized
    (PF_1A_E2_A 9.1).

    Returns an `HrLookup` whose value, when OK, is an `ActorPersonReference`.
    MISSING and AMBIGUOUS are distinct answers with distinct reason codes; a
    provider must never pick one of several mappings.
    """

    def resolve_actor_person(self, actor_user_public_id: str, as_of: datetime) -> HrLookup: ...


@runtime_checkable
class CanonicalHrReferencePort(Protocol):
    """The four canonical HR/organisation operations authority resolution needs.

    Expressed against PF_1F_HR_CANONICAL_REFERENCE_MODEL.md sections A-D.
    Every response carries `canonical_snapshot_at`; every operation may return
    an explicit UNAVAILABLE / STALE / MISSING / AMBIGUOUS outcome, each of
    which fails closed with its own reason code (PF_1A_E2_A 9.2).
    """

    def get_employment_state(self, person_id: str, as_of: datetime) -> HrLookup: ...

    def get_position(self, position_id: str, as_of: datetime) -> HrLookup: ...

    def get_incumbency(self, position_id: str, as_of: datetime) -> HrLookup: ...

    def get_org_unit(self, org_unit_id: str, as_of: datetime) -> HrLookup: ...
