"""PF-1A-E2-A section 18: SECURITY / BOUNDARY, and the E1 compatibility edge.

Covers non-store scenarios NS-PR-01 and NS-PR-02.

THE E2-A / E2-B / E3 SPLIT IS A SECURITY BOUNDARY, NOT A CONVENIENCE
(section 5). Resolving existing published authority and CHANGING who has
authority are distinct security problems with distinct failure modes. Neither
E2-A nor E2-B may expose any production path that creates, edits, deactivates
or otherwise mutates published authority configuration.
"""

from __future__ import annotations

import ast
import inspect
import io
import tokenize
from pathlib import Path

import pytest

import app
from app.core.database import SessionLocal
from app.modules.authorization import contract as e1_contract
from app.modules.authorization.business_authority import (
    contract,
    domain,
    evaluators,
    evidence,
    kernel,
    lineage,
    material,
    ports,
    production_composition,
    resolver,
    scope,
)
from app.modules.authorization.business_authority.ports import AuthorityConfigurationPort
from tests.fixtures.pf_1a_e2_a_corpus import covers

_PACKAGE_MODULES = (
    contract,
    domain,
    evaluators,
    evidence,
    kernel,
    lineage,
    material,
    ports,
    resolver,
    scope,
)

_APP_ROOT = Path(app.__file__).resolve().parent
_BUSINESS_AUTHORITY_ROOT = (
    _APP_ROOT / "modules" / "authorization" / "business_authority"
)


def _code_only(source: str) -> str:
    """Return `source` with DOCSTRINGS and COMMENTS removed, code intact.

    The source-level assertions below search for things that must not appear
    in CODE - an E1 role constant, a literal ADMIN comparison, an environment
    read. They must not fire on PROSE: this file and the package it inspects
    both discuss those very things at length in their docstrings, and a naive
    substring scan over raw source would make an accurate comment a test
    failure.

    Other string literals are deliberately KEPT, because a literal "ADMIN" in
    code is exactly what these tests exist to catch.
    """

    tree = ast.parse(source)
    docstring_spans: list[tuple[int, int]] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        body = getattr(node, "body", None)
        if not body:
            continue
        first = body[0]
        if (
            isinstance(first, ast.Expr)
            and isinstance(first.value, ast.Constant)
            and isinstance(first.value.value, str)
        ):
            docstring_spans.append((first.lineno, first.end_lineno or first.lineno))

    blanked = [
        "" if any(start <= number <= end for start, end in docstring_spans) else line
        for number, line in enumerate(source.splitlines(), start=1)
    ]
    without_docstrings = "\n".join(blanked) + "\n"

    kept = [
        token
        for token in tokenize.generate_tokens(io.StringIO(without_docstrings).readline)
        if token.type != tokenize.COMMENT
    ]
    return tokenize.untokenize(kept)


def _package_sources() -> dict[str, str]:
    return {
        module.__name__: _code_only(inspect.getsource(module)) for module in _PACKAGE_MODULES
    }


def _all_production_sources() -> dict[Path, str]:
    return {
        path: path.read_text(encoding="utf-8")
        for path in _APP_ROOT.rglob("*.py")
    }


# ===========================================================================
# An Application/Login Role alone - including ADMIN - grants NO business authority
# ===========================================================================


def test_the_kernel_imports_no_e1_role_constant_and_no_e1_permission_constant() -> None:
    """Section 6: if an implementation finds itself importing an E1 role
    constant into the authority kernel, THAT IS A DEFECT."""

    for name, source in _package_sources().items():
        assert "app.modules.authorization.contract" not in source, name
        assert "ALL_PERMISSION_CODES" not in source, name
        assert "KNOWN_ROLE_CODES" not in source, name
        assert "require_permission" not in source, name
        assert "require_roles" not in source, name


def test_no_e1_login_role_code_appears_anywhere_in_the_business_authority_package() -> None:
    """A Business Authority is never derived, inferred or defaulted from an
    Application/Login Role code, including ADMIN. The six codes must not appear
    at all - not in a mapping, not in a comparison, not in a default."""

    for role_code in e1_contract.KNOWN_ROLE_CODES:
        for name, source in _package_sources().items():
            assert f'"{role_code}"' not in source, f"{role_code} appears in {name}"
            assert f"'{role_code}'" not in source, f"{role_code} appears in {name}"


def test_there_is_no_implicit_admin_bypass_of_any_kind() -> None:
    """No hidden ADMIN bypass, in permissions or in business authority
    (attack surface 2, 3)."""

    for name, source in _package_sources().items():
        assert "ADMIN" not in source, f"ADMIN appears in {name}"


def test_the_kernel_receives_no_role_information_to_bypass_with() -> None:
    """The structural version of the same guarantee: there is no parameter,
    field or port through which an Application/Login Role could reach the
    kernel at all."""

    signature = inspect.signature(kernel.resolve)
    assert set(signature.parameters) == {
        "request",
        "as_of",
        "authority_configuration_port",
        "actor_person_port",
        "hr_reference_port",
    }
    assert "role_codes" not in domain.AuthenticatedActor.__dataclass_fields__


def test_the_protected_meta_authority_is_a_data_field_not_a_code_string_comparison() -> None:
    """ADR-033: `is_protected_meta_authority` is an EXPLICIT, DATA-DRIVEN
    classification field on the Business Authority payload. It is NEVER a
    hard-coded comparison against the literal AUTHORITY_CONFIGURATION_ADMIN
    (attack surface 4)."""

    assert "is_protected_meta_authority" in domain.BusinessAuthorityPayload.__dataclass_fields__
    for name, source in _package_sources().items():
        assert "AUTHORITY_CONFIGURATION_ADMIN" not in source, name


# ===========================================================================
# NS-PR-01  synthetic providers are PRODUCTION-UNREACHABLE
# ===========================================================================


@covers("NS-PR-01")
def test_the_reference_providers_live_only_under_the_test_tree() -> None:
    """Section 9.6 and section 20: reference/synthetic provider implementations
    belong under `backend/tests/`, never under a production package path, so
    the unreachability property is STRUCTURAL rather than merely asserted."""

    fixtures = Path(__file__).resolve().parent / "fixtures"
    for name in (
        "pf_1a_e2_a_reference_providers.py",
        "pf_1a_e2_a_scenarios.py",
        "pf_1a_e2_a_corpus.py",
    ):
        assert (fixtures / name).exists(), name

    # And nothing resembling one exists inside the production package.
    production_files = {path.name for path in _BUSINESS_AUTHORITY_ROOT.rglob("*.py")}
    assert not any("reference_provider" in name for name in production_files)
    assert not any("synthetic" in name for name in production_files)


@covers("NS-PR-01")
def test_no_production_module_imports_a_reference_or_synthetic_provider() -> None:
    """Not importable from, and not reachable through, any production module or
    the production wiring."""

    for path, source in _all_production_sources().items():
        assert "pf_1a_e2_a" not in source, f"{path} references an E2-A test fixture"
        assert "tests.fixtures" not in source, f"{path} imports from the test fixture tree"
        assert "from tests" not in source, f"{path} imports from the test tree"


@covers("NS-PR-01")
def test_no_environment_variable_flag_or_toggle_can_select_a_synthetic_provider() -> None:
    """Not selectable by any environment variable, settings flag, feature
    toggle or dependency override. The production composition seam takes NO
    input and consults NONE."""

    resolver_source = _code_only(inspect.getsource(resolver))
    for forbidden in ("environ", "getenv", "settings", "feature_flag", "toggle", "getattr("):
        assert forbidden not in resolver_source, forbidden

    # RECONCILED UNDER CONTROLLER-AUTHORIZED CORRECTION C2 (5 September 2026),
    # independent review finding F4. This assertion used to read
    # `inspect.signature(resolver.build_production_resolver).parameters == {}`.
    # PF-1A-E2-B supplies the authority configuration provider, so the seam
    # must BIND it, and a seam that binds a persistence-backed provider cannot
    # live in this deliberately persistence-free module. There is now exactly
    # ONE production composition seam,
    # `production_composition.build_production_business_authority_resolver`,
    # and the phase-local `resolver.build_production_resolver()` - which bound
    # nothing and authored a second refusal - was withdrawn rather than left
    # as a second successor-facing binding point.
    #
    # WHAT THIS ASSERTION STILL GUARANTEES, unchanged: the seam's ONLY
    # parameter is the database session it must bind, so there is no
    # environment variable, settings flag, feature toggle, provider argument
    # or dependency override for a caller to switch a synthetic provider in
    # through - and the seam's own module consults none either.
    signature = inspect.signature(
        production_composition.build_production_business_authority_resolver
    )
    assert list(signature.parameters) == ["db"]
    assert not any(
        parameter.kind
        in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD)
        for parameter in signature.parameters.values()
    )
    seam_source = _code_only(inspect.getsource(production_composition))
    for forbidden in ("environ", "getenv", "settings", "feature_flag", "toggle"):
        assert forbidden not in seam_source, forbidden

    # ...and this module no longer offers a second one to bind instead.
    assert not hasattr(resolver, "build_production_resolver")


@covers("NS-PR-01")
def test_the_kernel_reads_no_clock_no_environment_and_holds_no_database_session() -> None:
    """Kernel purity (10.3), asserted as a source-level property so a later
    edit that introduces one is caught rather than merely discouraged."""

    kernel_source = _code_only(inspect.getsource(kernel))
    for forbidden in (
        "datetime.now",
        "utcnow",
        "time.time",
        "os.environ",
        "getenv",
        "Session",
        "sqlalchemy",
        "execute(",
        "SELECT ",
        "fastapi",
        "HTTPException",
        "requests.",
        "httpx",
    ):
        assert forbidden not in kernel_source, f"{forbidden} appears in the kernel"


@covers("NS-PR-01")
def test_no_module_in_the_package_couples_to_sql_http_or_persistence() -> None:
    for name, source in _package_sources().items():
        for forbidden in ("sqlalchemy", "fastapi", "alembic", "psycopg", "get_db"):
            assert forbidden not in source, f"{forbidden} appears in {name}"


# ===========================================================================
# NS-PR-02  the PRODUCTION composition's own behaviour
# ===========================================================================


@covers("NS-PR-02")
def test_the_production_composition_refuses_to_compose() -> None:
    """Section 9.6 permits exactly two behaviours; THIS PACKAGE CHOOSES (a),
    refusing to compose at all, so no resolver object exists.

    Silent substitution of a synthetic provider is a blocking defect, and
    refusing to compose makes the absence impossible to overlook.
    """

    # RECONCILED UNDER CONTROLLER-AUTHORIZED CORRECTION C2 (5 September 2026),
    # independent review finding F4: this called the withdrawn phase-local
    # `resolver.build_production_resolver()`. It now exercises the ONE
    # canonical seam, which additionally BINDS the PostgreSQL authority
    # configuration provider before refusing. No database round trip is made -
    # constructing the read-only provider issues no statement - so this
    # remains an E2-A-side structural assertion.
    session = SessionLocal()
    try:
        with pytest.raises(resolver.ProductionCompositionUnavailableError) as raised:
            production_composition.build_production_business_authority_resolver(session)
    finally:
        session.close()

    message = str(raised.value)
    assert "authoritative" in message
    assert "9.6" in message


@covers("NS-PR-02")
def test_nothing_in_the_repository_wires_a_production_business_authority_resolver() -> None:
    """No production composition binds the resolver, and no record may describe
    E2 as delivering a production-callable business-authority resolver while
    the authoritative actor-person and HR providers do not exist.

    THE REPOSITORY-WIDE STRUCTURAL SCAN IS RETAINED DELIBERATELY. Narrowing
    this to "no module calls `build_production_resolver`" would be a much
    weaker test: consumer wiring can be introduced by importing the kernel,
    the resolver, a provider or the composition seam under any name. Scanning
    every production source for ANY reference to the package is what makes
    accidental consumer wiring visible, so the scan stays and only one file is
    exempted.

    THE ONE EXEMPTION, added under controller-authorized reconciliation C1
    (5 September 2026): `app/models_metadata.py`. PF-1A-E2-B is REQUIRED to
    register its persistence models there so SQLAlchemy and Alembic can
    discover the tables, and E2-A section 17 assigns that registration to
    PF-1A-E2-B by name. An ORM/metadata import is model DISCOVERY, not
    consumer wiring: it binds no resolver, calls no resolution entry point,
    reaches no actor-person or HR provider, and cannot produce an
    authorization decision. The exemption is EXACTLY that one file - no
    directory, no prefix and no pattern - so a genuine consumer appearing
    anywhere else still fails here.

    Everything this test was protecting is therefore still protected: no
    production consumer outside the package wires or calls a Business
    Authority resolver; no synthetic/reference provider becomes
    production-reachable; and the production composition still refuses to
    compose while the authoritative providers are absent.
    """

    # Exactly one file, matched by identity rather than by name, prefix or
    # directory, so nothing else can drift into the exemption.
    metadata_registration = _APP_ROOT / "models_metadata.py"

    for path, source in _all_production_sources().items():
        if path.parent == _BUSINESS_AUTHORITY_ROOT:
            continue
        if path == metadata_registration:
            # Model registration only: it must import the models, and it must
            # not reach the resolver, the kernel or any provider.
            registration_code = _code_only(source)
            for consumer_symbol in (
                "resolve_current_authority",
                "resolve_authority_as_of",
                "build_production_resolver",
                "build_production_business_authority_resolver",
                "build_authority_configuration_provider",
                "AuthorityConfigurationPort",
                "kernel",
                "resolver",
            ):
                assert consumer_symbol not in registration_code, (
                    f"{path} reaches {consumer_symbol!r}; the metadata exemption covers model "
                    "registration only, never consumer wiring"
                )
            continue
        assert "business_authority" not in source, (
            f"{path} references the business authority package; no production consumer may wire "
            "or call a Business Authority resolver while the authoritative actor-person and HR "
            "providers are absent"
        )


# ===========================================================================
# No write path to published authority configuration, anywhere
# ===========================================================================


def test_the_authority_configuration_port_defines_no_write_operation() -> None:
    """The port defines NO create/update/deactivate/publish/delete operation,
    and E2-A implements none (9.3.3, acceptance criterion Q)."""

    operations = {
        name
        for name in dir(AuthorityConfigurationPort)
        if not name.startswith("_")
    }
    assert operations == {
        "find_business_authority_ids_by_code",
        "find_rule_ids_for_authority",
        "find_assignment_ids_for_role",
        "get_lineage",
        "get_published_version",
    }


def test_no_module_in_the_package_defines_a_configuration_write_path() -> None:
    """Any write surface - function, repository method, or fixture helper
    reachable from production - that mutates published authority configuration
    outside a future governed Configuration Change is a blocking finding
    (attack surface 34)."""

    forbidden_prefixes = (
        "def create_",
        "def update_",
        "def publish_",
        "def deactivate_",
        "def delete_",
        "def retract_",
        "def activate_",
    )
    for name, source in _package_sources().items():
        for prefix in forbidden_prefixes:
            assert prefix not in source, f"{prefix!r} appears in {name}"


def test_the_package_adds_no_route_and_no_api_schema_surface() -> None:
    """No HTTP route and no request/response schema surface, in ANY phase.

    RECONCILED AT THE E2-A -> E2-B PHASE BOUNDARY, under controller-authorized
    reconciliation C1 (5 September 2026). This test previously also asserted
    that `models.py`, `repository.py` and a `models_metadata.py` registration
    could never exist. Those were PHASE-LOCAL assertions about what PF-1A-E2-A
    itself delivered, and E2-A section 17 assigns all four of them to
    PF-1A-E2-B by name:

        - SQLAlchemy persistence for any new authority object   (PF-1A-E2-B)
        - any Alembic migration                                 (PF-1A-E2-B)
        - a database-backed authority repository or provider    (PF-1A-E2-B)
        - registration in backend/app/models_metadata.py        (PF-1A-E2-B)

    So they expire by design the moment the successor package lands, and
    keeping them would have made a conforming PF-1A-E2-B impossible rather
    than protecting anything. See
    `docs/agent/acceptance/pf-1a-e2-b-persisted-published-authority-store-acceptance.md`
    for the full reconciliation record, which preserves the original E2-A form
    rather than pretending this test always looked like this.

    WHAT SURVIVES UNCHANGED, and why it is the part that mattered: the
    Business Authority package exposes NO HTTP route and NO API schema
    surface. That exclusion belongs to a later consumer package, not to E2-B,
    so it is still in force and is still asserted here. The separate tests
    prohibiting a production configuration WRITE path are untouched and
    remain the stronger guarantee.
    """

    package_files = sorted(path.name for path in _BUSINESS_AUTHORITY_ROOT.glob("*.py"))
    assert "routes.py" not in package_files
    assert "schemas.py" not in package_files


def test_configuration_change_is_a_forward_compatible_reference_shape_only() -> None:
    """E2 defines the value's shape and NEVER creates such a record; E3 will
    populate it (11.7). Every E2 fixture uses BOOTSTRAP_PROVENANCE, explicitly
    labelled as synthetic test provenance."""

    from tests.fixtures.pf_1a_e2_a_reference_providers import (
        SYNTHETIC_PROVENANCE_ID,
        version,
    )

    assert contract.CONFIGURATION_CHANGE in contract.PUBLICATION_REFERENCE_TYPES
    default_version = version("0001")
    assert default_version.publication_reference_type == contract.BOOTSTRAP_PROVENANCE
    # Labelled in the fixture itself, so no reader can mistake it for a
    # production bootstrap or a resolution of Q-10 (11.7, section 23).
    assert "SYNTHETIC" in SYNTHETIC_PROVENANCE_ID
    assert "NOT-A-PRODUCTION-BOOTSTRAP" in SYNTHETIC_PROVENANCE_ID


# ===========================================================================
# E1 REGRESSION - the compatibility facts of section 6 are untouched
# ===========================================================================


def test_the_e1_permission_contract_is_unchanged_by_this_package() -> None:
    """Section 6: E2-A must not add any Business Authority code to the E1
    permission contract, nor add, remove, rename, widen or narrow any E1
    permission or any of the 110 grants.

    Asserted against the frozen `ROLE_PERMISSION_COMPATIBILITY_MATRIX`, not against
    `ALL_PERMISSION_CODES`: since Slice 9D the latter derives from the effective matrix and
    legitimately grows, while the baseline must not. Checking the baseline is what this test
    actually means."""

    assert len(e1_contract.ROLE_PERMISSION_COMPATIBILITY_MATRIX) == 31
    assert len(e1_contract.KNOWN_ROLE_CODES) == 6

    grants = sum(
        len(role_codes)
        for role_codes in e1_contract.ROLE_PERMISSION_COMPATIBILITY_MATRIX.values()
    )
    assert grants == 110

    # No business-authority code leaked into the application-permission space.
    for authority_code in ("CREDIT_ASSESSOR", "CREDIT_APPROVER", "AUTHORITY_CONFIGURATION_ADMIN"):
        assert authority_code not in e1_contract.ALL_PERMISSION_CODES


def test_the_two_gates_remain_separate_layers() -> None:
    """The intended consumer pattern keeps `require_permission(...)` and
    business-authority resolution as two gates with distinct meanings, neither
    substituting for the other. E2-A implements no consumer, and nothing here
    replaces, wraps, bypasses or weakens `require_permission(...)`."""

    from app.modules.authorization import dependencies

    dependency_source = _code_only(inspect.getsource(dependencies))
    assert "business_authority" not in dependency_source
    assert "resolve_current_authority" not in dependency_source
