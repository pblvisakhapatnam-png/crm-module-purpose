"""THE production composition seam, and its deliberate refusal to compose.

PF-1A-E2-B section 5.3; PF-1A-E2-A section 9.6.

THIS MODULE HOLDS THE ONE CANONICAL PRODUCTION COMPOSITION IMPLEMENTATION.
`build_production_business_authority_resolver` is the single place where the
three dependencies of business authority resolution are assembled, and the
single place that refuses when they are not all present. Until PF-1A-E2-B the
package also carried `resolver.build_production_resolver()`, which bound
nothing and raised a SEPARATELY AUTHORED refusal; two independent
successor-facing seams drift apart the moment a later package adds the
actor-person and HR providers to one of them, so it was withdrawn (independent
review finding F4). If a later package needs a second public name, it must be
a thin delegating wrapper around the function below, never a second assembly.

Business authority resolution has THREE dependencies. After PF-1A-E2-B
exactly one of them exists:

    authority configuration port    SATISFIED HERE, by the PostgreSQL
                                    read-only provider.
    actor -> canonical person port  NOT DELIVERED. A later authorized package.
    canonical HR / organisation     NOT DELIVERED. A later authorized package.

Section 5.3 permits exactly two behaviours for a production composition that
lacks an authoritative provider: (a) REFUSE TO COMPOSE at wiring time, so no
resolver object is ever produced, or (b) produce a resolver that
deterministically returns DENY + FAIL_CLOSED with
ACTOR_PERSON_PROVIDER_NOT_CONFIGURED / HR_REFERENCE_PROVIDER_NOT_CONFIGURED on
every call.

    THIS PACKAGE CHOOSES OPTION (a), the option section 5.3 recommends,
    and it chooses it for the reason stated there: AN UNUSABLE OBJECT CANNOT
    BE MISUSED. PF-1A-E2-A had already made the same choice for the same
    reason under section 9.6, so this ONE seam discharges both phases'
    obligation rather than each phase keeping a seam of its own.

WHY THE PROVIDER IS STILL BUILT BEFORE THE REFUSAL. The seam's purpose is to
be the explicit, single place a later package binds an authoritative provider.
Constructing the configuration provider here - and then refusing, loudly,
because the other two dependencies are absent - proves the binding point
exists and is wired to PostgreSQL, without producing anything callable.

WHAT NO CODE PATH IN THIS MODULE DOES, and a test proves each:

    it never imports a synthetic/reference actor-person or HR provider. Those
        live under `backend/tests/`, so the unreachability is STRUCTURAL: a
        production module cannot import what is not on the production import
        path;
    it reads no environment variable, no settings flag and no feature toggle,
        and accepts no provider argument, so there is no switch through which
        a synthetic provider could be selected;
    it exposes no `as_of`, no recorded-time cutoff and no client-supplied
        person identity.

**PF-1A-E2-B DOES NOT DELIVER A PRODUCTION-CALLABLE BUSINESS-AUTHORITY
RESOLVER.** No consumer route or service may call business authority
resolution as a real authorization gate until a later authorized package
supplies both missing providers (section 16, acceptance criteria P and Q).
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.modules.authorization.business_authority.postgres_provider import (
    PostgresAuthorityConfigurationProvider,
)
from app.modules.authorization.business_authority.resolver import (
    ProductionCompositionUnavailableError,
)


def build_authority_configuration_provider(
    db: Session,
) -> PostgresAuthorityConfigurationProvider:
    """The ONE production dependency PF-1A-E2-B satisfies.

    Returns a READ-ONLY provider of published authority configuration facts.
    It is safe to construct on its own - it can answer configuration reads and
    nothing else - and it is what PF-1A-E3's governed publication will later
    publish into.

    Holding this provider confers no authority and authorizes nothing: it
    supplies facts to the kernel, and the kernel cannot run without the two
    dependencies below.
    """

    return PostgresAuthorityConfigurationProvider(db)


def build_production_business_authority_resolver(db: Session) -> None:
    """THE production composition seam - which deliberately REFUSES to compose.

    Option (a) of section 5.3, and of PF-1A-E2-A section 9.6. This is the ONE
    canonical implementation: the one place the dependencies are assembled and
    the one place the refusal is authored. The authority configuration
    provider IS bound here, and the refusal that follows names precisely which
    dependencies are still absent, so the gap is impossible to overlook and
    impossible to satisfy accidentally with a synthetic substitute.

    This function never returns. Its return annotation is `None` because there
    is no resolver object to hand back, and there must not be one.
    """

    # Bound: this is the seam, and this is the one dependency E2-B supplies.
    build_authority_configuration_provider(db)

    # NOT bound, and deliberately not substitutable:
    raise ProductionCompositionUnavailableError(
        "PF-1A-E2-B binds the PostgreSQL authority configuration provider, but no "
        "authoritative actor-person provider and no authoritative canonical "
        "HR/organisation provider exists yet (PF-1A-E2-A section 9.6, PF-1A-E2-B "
        "section 5.3). A production Business Authority resolver cannot be composed, "
        "and a synthetic/reference provider must never be substituted."
    )
