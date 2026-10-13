"""The governed-configuration production seam, and its refusal to compose (PF-1A-E3).

Governed configuration has the SAME three dependencies business authority resolution has, and
for a stronger reason: deciding whether a configuration change may publish requires knowing who
is acting, whether they currently hold a protected meta-authority, and whether the change
affects them.

    authority configuration store   SATISFIED. The PF-1A-E2-B read-only provider, bound here,
                                    is what PF-1A-E3 publishes into.
    actor -> canonical person       NOT DELIVERED. A later authorized package.
    canonical HR / organisation     NOT DELIVERED. A later authorized package.

PF-1A-E2-A section 9.6 permits two behaviours for a production composition missing an
authoritative provider: refuse to compose, or return a deterministic fail-closed object. THIS
SEAM REFUSES TO COMPOSE, for the reason that decision gives: an unusable object cannot be
misused. A governed configuration service is the one object in this package that could WRITE
authority, so producing a partially-wired one would be worse here than anywhere else.

WHY THIS SEAM RAISES ITS OWN ERROR TYPE, AND NOT THE RESOLVER'S. PF-1A-E2-B established, as a
structural invariant, that exactly ONE function in this package raises
`ProductionCompositionUnavailableError`: the canonical RESOLVER composition seam
`production_composition.build_production_business_authority_resolver`. That invariant exists so
a successor cannot quietly add a second resolver-assembly point that a consumer might bind
instead. PF-1A-E3 is not a second resolver seam - it composes a WRITER - so reusing the
resolver's refusal type would have made a genuinely different seam indistinguishable from a
duplicate of that one. The refusal below is therefore its own type, and the resolver invariant
is left counting exactly one raiser, as intended.

The refusal is not weakened by being differently typed: it is unconditional, it is raised before
any service object can exist, and it names precisely which dependencies are absent.

WHAT NO CODE PATH IN THIS MODULE DOES: it imports no reference or synthetic provider (those live
only under the repository's backend verification tree, so the unreachability is structural); it
reads no environment variable, settings value or feature toggle; it accepts no provider
argument; and it exposes no `as_of` or recorded-time cutoff.

**PF-1A-E3 DOES NOT DELIVER A PRODUCTION-CALLABLE GOVERNED CONFIGURATION SERVICE.** No route,
service or job may administer authority configuration until a later authorized package supplies
both missing providers. That is a separate question from Q-10 (who the first protected
meta-authority holder is), which this package does not answer and must not be read as answering.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.modules.authorization.business_authority.production_composition import (
    build_authority_configuration_provider,
)


class GovernedConfigurationCompositionUnavailableError(RuntimeError):
    """A governed configuration WRITER composition was attempted without its providers.

    Deliberately its own type, and deliberately NOT a subclass of the resolver's
    `ProductionCompositionUnavailableError`: the two seams compose different things - one reads
    published authority, one changes it - and PF-1A-E2-B's one-canonical-resolver-seam
    invariant is about the resolver alone. Keeping the types distinct lets a caller that means
    to handle a resolver-composition failure not silently swallow a writer-composition failure,
    and vice versa.

    There is no condition under which this error is not raised by the seam below. Silent
    substitution of a synthetic provider is a blocking defect and is structurally prevented:
    the reference/synthetic providers live outside the production import path.
    """


def build_governed_authority_configuration_service(db: Session) -> None:
    """THE governed-configuration production seam - which deliberately REFUSES.

    The authority configuration provider IS bound here, so the binding point is real and
    demonstrably wired to PostgreSQL. The refusal that follows names precisely which
    dependencies remain absent, so the gap cannot be overlooked and cannot be satisfied
    accidentally by a synthetic substitute.

    This function never returns. Its return annotation is `None` because there is no service
    object to hand back, and there must not be one.
    """

    build_authority_configuration_provider(db)

    raise GovernedConfigurationCompositionUnavailableError(
        "PF-1A-E3 binds the PostgreSQL authority configuration provider, but no authoritative "
        "actor-person provider and no authoritative canonical HR/organisation provider exists "
        "yet (PF-1A-E2-A section 9.6, PF-1A-E2-B section 5.3). A governed authority "
        "configuration service cannot be composed, and a synthetic/reference provider must "
        "never be substituted. This refusal is not, and must not be read as, an answer to open "
        "question Q-10."
    )
