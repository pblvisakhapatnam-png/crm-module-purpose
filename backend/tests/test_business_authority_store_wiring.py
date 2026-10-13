"""PF-1A-E2-B section 9: RUNTIME WIRING, SECURITY / BOUNDARY and REGRESSION.

The eight parity-NO non-store scenarios carry their obligation HERE rather
than in the parity corpus, and for a stated reason in each case: a
reachability, surface or cross-reference assertion has no meaningful second
side to compare against. PARITY = NO never means "tested once and loosely".

    NS-AP-04   the identity trust boundary, asserted against the WIRED path -
               wiring is exactly where a client-supplied person identity could
               be reintroduced.
    NS-PR-01   the synthetic/reference providers are UNREACHABLE from every
               production import path and from the production wiring.
    NS-PR-02   the PRODUCTION composition, exercised with no authoritative
               actor-person or HR provider available.
    NS-RS-03   the two entry points' parameter surfaces, after wiring.
    NS-DO-06   the declared rank tables' totality - an E2-A-side obligation,
               cross-referenced here.
    NS-K-01    the single-effective-version theorem, its defensive branch and
    NS-K-02    the internal-contract self-check - both E2-A-side, likewise
               cross-referenced.

THE HEADLINE FACT THIS MODULE PROVES, and which no record produced by this
package may contradict: **PF-1A-E2-B DOES NOT DELIVER A PRODUCTION-CALLABLE
BUSINESS-AUTHORITY RESOLVER.** It binds the PostgreSQL authority
configuration provider into the production seam and the seam then REFUSES TO
COMPOSE, because the authoritative actor-person and HR/organisation providers
do not exist.
"""

from __future__ import annotations

import ast
import importlib
import inspect
from pathlib import Path

import pytest
from sqlalchemy import text

import app.modules.authorization.business_authority as business_authority_package
from app.modules.authorization import contract as e1_contract
from app.modules.authorization.business_authority import (
    postgres_provider,
    production_composition,
    repository,
    store_contract,
)
from app.modules.authorization.business_authority import resolver as resolver_module
from app.modules.authorization.business_authority.postgres_provider import (
    PostgresAuthorityConfigurationProvider,
)
from app.modules.authorization.business_authority.resolver import (
    ProductionCompositionUnavailableError,
    resolve_authority_as_of,
    resolve_current_authority,
)
from app.modules.authorization.business_authority.store_contract import ALL_STORE_TABLES
from tests.fixtures.pf_1a_e2_a_corpus import COVERS_ATTRIBUTE
from tests.fixtures.pf_1a_e2_a_reference_providers import PERSON_ID, T2
from tests.fixtures.pf_1a_e2_a_scenarios import world
from tests.fixtures.pf_1a_e2_b_corpus import (
    E1_PROTECTED_TABLES,
    executable_source,
    store_covers,
)
from tests.fixtures.pf_1a_e2_b_store import (  # noqa: F401  (store_db is a fixture)
    assert_parity,
    run_through_postgres,
    seed_materials,
    store_db,
)

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
_PRODUCTION_ROOT = _BACKEND_ROOT / "app"

# The test-only modules that may bind synthetic actor/HR providers. They live
# under `backend/tests/`, which is what makes their production unreachability
# STRUCTURAL rather than merely asserted.
_SYNTHETIC_PROVIDER_MODULES = (
    "tests.fixtures.pf_1a_e2_a_reference_providers",
    "tests.fixtures.pf_1a_e2_a_scenarios",
    "tests.fixtures.pf_1a_e2_b_store",
)


def _production_modules():
    """Every module on the production import path, imported for introspection.

    Found by walking the FILES under `app/`, each imported by its dotted name; a
    package's `__init__.py` is imported as the package. `pkgutil.walk_packages`
    did this until 9 October 2026, but it does not descend into a directory
    without an `__init__.py`, and `app/core`, `app/modules` and `app/shared` are
    namespace packages: it reached four top-level modules and none of the
    business modules (found during TB-1 CS-11, 8 October 2026).
    """

    modules = []
    for path in sorted(_PRODUCTION_ROOT.rglob("*.py")):
        parts = path.relative_to(_BACKEND_ROOT).with_suffix("").parts
        if parts[-1] == "__init__":
            parts = parts[:-1]
        modules.append(importlib.import_module(".".join(parts)))
    return modules


def _e2a_coverage_index() -> dict[str, list[str]]:
    """manifest id -> [E2-A test names], for the cross-reference assertions."""

    index: dict[str, list[str]] = {}
    for path in sorted(Path(__file__).resolve().parent.glob("test_business_authority_*.py")):
        module = importlib.import_module(f"tests.{path.stem}")
        for name, member in vars(module).items():
            if not name.startswith("test_") or not callable(member):
                continue
            for identifier in getattr(member, COVERS_ATTRIBUTE, ()):
                index.setdefault(identifier, []).append(f"{module.__name__}::{name}")
    return index


# ===========================================================================
# NS-PR-02  the PRODUCTION composition
# ===========================================================================


@store_covers("NS-PR-02")
def test_ns_pr_02_the_production_composition_refuses_to_compose(store_db) -> None:
    """OPTION (a) OF SECTION 5.3, recorded explicitly as the choice made.

    Section 5.3 permits either refusing to compose or failing closed
    deterministically. This package refuses, because an unusable object cannot
    be misused - and because PF-1A-E2-A had already made the same choice, so
    binding the new provider into the existing seam keeps ONE behaviour rather
    than two.
    """

    with pytest.raises(ProductionCompositionUnavailableError) as caught:
        production_composition.build_production_business_authority_resolver(store_db)

    message = str(caught.value)
    # The refusal NAMES what is missing, so the gap cannot be overlooked.
    assert "actor-person" in message
    assert "HR/organisation" in message
    assert "must never be substituted" in message

    # The one dependency E2-B DOES satisfy is genuinely bound and usable on
    # its own - it answers configuration reads, and nothing else.
    provider = production_composition.build_authority_configuration_provider(store_db)
    assert isinstance(provider, PostgresAuthorityConfigurationProvider)
    seed_materials(store_db, world())
    assert list(provider.find_business_authority_ids_by_code("CREDIT_ASSESSOR"))


@store_covers("NS-PR-02")
def test_ns_pr_02_there_is_exactly_one_production_composition_implementation() -> None:
    """ONE canonical seam, proved from the SOURCE of every production module in
    the package (independent review finding F4).

    Until PF-1A-E2-B there were two: `resolver.build_production_resolver()`,
    which bound nothing, and
    `production_composition.build_production_business_authority_resolver(db)`,
    which binds PostgreSQL. Both refused, so both were safe THAT DAY - and
    that is exactly why the duplication was worth removing rather than
    tolerating. Two successor-facing seams drift apart the moment a later
    package adds the actor-person and HR providers to one of them, and a
    consumer that happened to bind the other would then get a resolver whose
    dependency assembly nobody had reviewed.

    The assertion is structural: exactly one function ANYWHERE in the package
    raises the refusal, and it is the canonical seam. A compatibility name
    would be permitted only as a thin DELEGATING wrapper - one that calls the
    function below rather than raising for itself - and such a wrapper would
    still leave this count at one.
    """

    package_root = Path(business_authority_package.__file__).resolve().parent
    raisers = []
    for path in sorted(package_root.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for inner in ast.walk(node):
                if not isinstance(inner, ast.Raise) or inner.exc is None:
                    continue
                raised = inner.exc.func if isinstance(inner.exc, ast.Call) else inner.exc
                if isinstance(raised, ast.Name) and (
                    raised.id == "ProductionCompositionUnavailableError"
                ):
                    raisers.append((path.name, node.name))

    assert raisers == [
        ("production_composition.py", "build_production_business_authority_resolver")
    ], raisers

    # The withdrawn phase-local factory is genuinely gone, not merely unused.
    assert not hasattr(resolver_module, "build_production_resolver")
    assert "build_production_resolver" not in executable_source(resolver_module)


@store_covers("NS-PR-02")
def test_ns_pr_02_the_canonical_seam_genuinely_binds_postgresql(store_db, monkeypatch) -> None:
    """The canonical path BINDS the E2-B provider before it refuses - observed
    at runtime, not inferred from the source.

    This is the half of finding F4 that matters for a successor: the seam a
    later package will extend must already be the one wired to PostgreSQL, so
    that adding the two missing providers there produces a resolver reading
    real published configuration rather than nothing.
    """

    bound: list[object] = []
    real_builder = production_composition.build_authority_configuration_provider

    def recording_builder(db):
        provider = real_builder(db)
        bound.append((db, provider))
        return provider

    monkeypatch.setattr(
        production_composition, "build_authority_configuration_provider", recording_builder
    )

    with pytest.raises(ProductionCompositionUnavailableError):
        production_composition.build_production_business_authority_resolver(store_db)

    assert len(bound) == 1, "the canonical seam did not bind the configuration provider"
    session, provider = bound[0]
    assert session is store_db
    assert isinstance(provider, PostgresAuthorityConfigurationProvider)

    # ...and the provider it bound really reads this PostgreSQL store.
    seed_materials(store_db, world())
    assert list(provider.find_business_authority_ids_by_code("CREDIT_ASSESSOR"))

    # ...and none of it produced a callable resolver. The seam's declared
    # return type is None (a string under `from __future__ import
    # annotations`) and, as the raise above shows, it never returns at all.
    assert (
        inspect.signature(
            production_composition.build_production_business_authority_resolver
        ).return_annotation
        == "None"
    )


@store_covers("NS-PR-02")
def test_ns_pr_02_the_seam_takes_no_provider_and_reads_no_configuration_switch() -> None:
    """No environment variable, settings flag, feature toggle or dependency
    override can switch a production composition onto synthetic identity or HR
    state - because the seam accepts no such input and consults none."""

    signature = inspect.signature(
        production_composition.build_production_business_authority_resolver
    )
    assert list(signature.parameters) == ["db"]

    source = executable_source(production_composition)
    for switch in ("os.environ", "getenv", "get_settings", "settings.", "ENABLE_", "FEATURE_"):
        assert switch not in source, switch


# ===========================================================================
# NS-PR-01  synthetic providers are UNREACHABLE from production
# ===========================================================================


@store_covers("NS-PR-01")
def test_ns_pr_01_no_production_module_imports_a_synthetic_provider() -> None:
    """STRUCTURAL, not merely asserted: the reference providers live under
    `backend/tests/`, so no production module can import them."""

    modules = _production_modules()
    # The scan reaches every file of the application, so it cannot again pass
    # having read only the four top-level modules.
    assert {Path(module.__file__).resolve() for module in modules} == {
        path.resolve() for path in _PRODUCTION_ROOT.rglob("*.py")
    }

    offenders = []
    for module in modules:
        try:
            source = inspect.getsource(module)
        except OSError:  # inspect finds no lines in an empty file; nothing else is skipped
            assert not Path(module.__file__).read_text(encoding="utf-8-sig").strip(), module.__name__
            continue
        for marker in ("tests.fixtures", "ReferenceActorPersonProvider", "ReferenceHrProvider",
                       "ReferenceAuthorityConfigurationProvider", "JudgingAuthority"):
            if marker in source:
                offenders.append((module.__name__, marker))
    assert offenders == [], offenders


@store_covers("NS-PR-01")
def test_ns_pr_01_the_synthetic_providers_live_only_under_the_test_tree() -> None:
    for module_name in _SYNTHETIC_PROVIDER_MODULES:
        module = importlib.import_module(module_name)
        location = Path(module.__file__).resolve()
        assert location.is_relative_to(_BACKEND_ROOT / "tests"), location
        assert not location.is_relative_to(_PRODUCTION_ROOT), location


@store_covers("NS-PR-01")
def test_ns_pr_01_the_business_authority_package_exposes_no_synthetic_binding() -> None:
    """Every module of the production subpackage, read as CODE rather than as
    prose."""

    # The synthetic providers by NAME. A broader "Reference" scan would be
    # wrong: the kernel legitimately imports the CANONICAL HR reference DTOs
    # (`ActorPersonReference`, `PositionVersionReference` and their siblings),
    # which are contract types, not providers.
    synthetic_names = (
        "ReferenceActorPersonProvider",
        "ReferenceHrProvider",
        "ReferenceAuthorityConfigurationProvider",
        "JudgingAuthorityConfigurationProvider",
    )

    package_root = Path(business_authority_package.__file__).resolve().parent
    for path in sorted(package_root.glob("*.py")):
        module = importlib.import_module(
            f"app.modules.authorization.business_authority.{path.stem}"
            if path.stem != "__init__"
            else "app.modules.authorization.business_authority"
        )
        source = executable_source(module)
        assert "tests." not in source, path.name
        for synthetic in synthetic_names:
            assert synthetic not in source, f"{path.name} binds {synthetic}"


# ===========================================================================
# NS-AP-04 and NS-RS-03  the identity and temporal trust boundaries, WIRED
# ===========================================================================


@store_covers("NS-AP-04")
def test_ns_ap_04_no_client_supplied_identity_hint_influences_the_wired_resolution(
    store_db,
) -> None:
    """The supplied value influences NOTHING.

    The business context is the one caller-controlled structure the kernel
    consumes, so a hostile identity hint is driven through it against the
    PostgreSQL-backed path and the resolved canonical person is asserted
    unchanged. This is asserted against the WIRED path specifically, because
    wiring is where such a parameter could be reintroduced.
    """

    from app.modules.authorization.business_authority.domain import BusinessContext

    hostile = BusinessContext(
        declared_facts={
            "person_id": "person-9999",
            "actor_user_public_id": "someone-else",
            "canonical_person": "person-9999",
        }
    )
    result = run_through_postgres(store_db, world(), business_context=hostile)
    assert result.established_state.person_id == PERSON_ID

    # And no DTO the wired path consumes offers a person identity at all.
    from app.modules.authorization.business_authority.domain import AuthenticatedActor

    assert set(AuthenticatedActor.__dataclass_fields__) == {"actor_user_public_id"}
    assert "person_id" not in BusinessContext.__dataclass_fields__


@store_covers("NS-RS-03")
def test_ns_rs_03_the_current_path_still_accepts_no_as_of_after_wiring() -> None:
    """The separation is STRUCTURAL, and wiring did not soften it.

    `resolve_current_authority` exposes no `as_of` and no recorded-time bound
    through any signature, DTO field or keyword pass-through; the historical
    resolver is a separate entry point and is not a live authorization path.
    """

    current = inspect.signature(resolve_current_authority)
    assert "as_of" not in current.parameters
    for forbidden in ("as_at", "known_as_at", "published_before", "recorded_at", "cutoff"):
        assert forbidden not in current.parameters, forbidden
    assert not any(
        parameter.kind is inspect.Parameter.VAR_KEYWORD
        for parameter in current.parameters.values()
    ), "a **kwargs pass-through could smuggle an as_of through"

    historical = inspect.signature(resolve_authority_as_of)
    assert "as_of" in historical.parameters
    for forbidden in ("as_at", "known_as_at", "published_before", "recorded_at", "cutoff"):
        assert forbidden not in historical.parameters, forbidden

    # Neither entry point is renamed or aliased into the other.
    assert resolve_current_authority is not resolve_authority_as_of


# ===========================================================================
# NS-DO-06, NS-K-01, NS-K-02  E2-A-side obligations, cross-referenced
# ===========================================================================


@store_covers("NS-DO-06", "NS-K-01", "NS-K-02")
def test_the_kernel_side_obligations_exist_and_execute() -> None:
    """These three have no second side for a parity test to run against:
    NS-DO-06 asserts a property of the kernel's declared rank tables, and
    NS-K-01/NS-K-02 exercise states NO provider can present. E2-B's obligation
    is to prove the named E2-A tests exist and are neither skipped nor
    xfailed, so a defect class cannot silently lose coverage in the gap
    between the two packages.
    """

    index = _e2a_coverage_index()
    for identifier in ("NS-DO-06", "NS-K-01", "NS-K-02"):
        assert index.get(identifier), f"{identifier} has no executing E2-A test"

    for path in sorted(Path(__file__).resolve().parent.glob("test_business_authority_*.py")):
        module = importlib.import_module(f"tests.{path.stem}")
        for name, member in vars(module).items():
            if not name.startswith("test_") or not callable(member):
                continue
            covered = set(getattr(member, COVERS_ATTRIBUTE, ()))
            if not covered & {"NS-DO-06", "NS-K-01", "NS-K-02"}:
                continue
            marks = {getattr(mark, "name", "") for mark in getattr(member, "pytestmark", [])}
            assert marks.isdisjoint({"skip", "skipif", "xfail"}), name


# ===========================================================================
# SECURITY / BOUNDARY
# ===========================================================================


@store_covers()
def test_an_application_login_role_alone_grants_no_business_authority(store_db) -> None:
    """Not even ADMIN. A Business Authority is never derived, defaulted or
    inferred from an Application/Login Role, in code or through a schema
    link."""

    # No E1 role constant, permission catalogue import or route guard reaches
    # the business-authority package's CODE. Docstrings are stripped first:
    # these modules deliberately EXPLAIN the four-concept distinction at
    # length, naming both vocabularies in prose so a later reader cannot
    # collapse them.
    package_root = Path(business_authority_package.__file__).resolve().parent
    for path in sorted(package_root.glob("*.py")):
        module = importlib.import_module(
            f"app.modules.authorization.business_authority.{path.stem}"
            if path.stem != "__init__"
            else "app.modules.authorization.business_authority"
        )
        source = executable_source(module)
        for role_code in e1_contract.KNOWN_ROLE_CODES:
            assert role_code not in source, f"{path.name} names the login role {role_code}"
        assert "authorization.contract" not in source, path.name
        assert "require_permission" not in source, path.name
        assert "require_roles" not in source, path.name

    # And with the store EMPTY, an ADMIN actor still resolves to nothing.
    result = run_through_postgres(store_db, [], as_of=T2)
    assert result.outcome == "DENY"


@store_covers()
def test_no_repository_or_provider_function_writes_published_configuration() -> None:
    """Acceptance criterion R, restated at the wiring boundary: the seam hands
    out a READ-ONLY provider, and nothing beneath it can write."""

    provider_source = executable_source(postgres_provider)
    repository_source = executable_source(repository)
    for forbidden in ("INSERT", "UPDATE", "DELETE", "COMMIT", "FLUSH"):
        assert forbidden not in provider_source.upper(), forbidden
        assert forbidden not in repository_source.upper(), forbidden


@store_covers()
def test_no_authority_table_persists_provider_specific_hr_detail(store_db) -> None:
    """Section 8: `person_id`, `position_id` and scope identifiers are OPAQUE
    canonical values. No SharePoint item id, no Plum field, no employee name,
    no raw provider timestamp and no Source Binding reference has a column."""

    columns = (
        store_db.execute(
            text(
                "SELECT table_name, column_name FROM information_schema.columns "
                "WHERE table_schema = current_schema() AND table_name = ANY(:tables)"
            ),
            {"tables": list(ALL_STORE_TABLES)},
        )
        .mappings()
        .all()
    )
    names = {row["column_name"] for row in columns}
    forbidden = {
        "employee_name",
        "employee_id",
        "sharepoint_item_id",
        "plum_field",
        "plum_employee_id",
        "source_binding_id",
        "source_system",
        "source_record_key",
        "provider_timestamp",
        "designation",
        "department",
        "reporting_manager",
    }
    assert forbidden.isdisjoint(names), forbidden & names

    # And no local HR/person/organisation/position master table was created.
    tables = (
        store_db.execute(
            text(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = current_schema() AND table_type = 'BASE TABLE'"
            )
        )
        .scalars()
        .all()
    )
    for forbidden_table in ("employee", "person", "org_unit", "position", "incumbency"):
        assert forbidden_table not in tables, forbidden_table


@store_covers()
def test_the_parameter_payload_never_carries_anything_executable(store_db) -> None:
    """Attack surface 24. The payload is declarative DATA: never code, an
    expression string, SQL, a template or anything interpreted as logic.

    Proved structurally rather than by keyword-blocking a value: nothing in
    this package ever evaluates, compiles or executes a payload.
    """

    for module in (repository, postgres_provider, production_composition):
        source = executable_source(module)
        for forbidden in ("eval(", "exec(", "compile(", "__import__", "subprocess", "importlib"):
            assert forbidden not in source, f"{module.__name__}: {forbidden}"


# ===========================================================================
# REGRESSION - the PF-1A-E1 compatibility boundary (section 7)
# ===========================================================================


@store_covers()
def test_the_e1_permission_catalogue_and_grant_matrix_are_unchanged(store_db) -> None:
    """31 permissions, six transitional Application/Login Roles, 110 grants.

    Asserted against BOTH the contract module and the live database, because
    E2-B is the package that actually touches the schema and
    `models_metadata.py` and therefore has the most opportunity to break them.
    """

    assert len(e1_contract.ROLE_PERMISSION_COMPATIBILITY_MATRIX) == 31
    assert len(e1_contract.KNOWN_ROLE_CODES) == 6
    grants = sum(
        len(role_codes) for role_codes in e1_contract.ROLE_PERMISSION_COMPATIBILITY_MATRIX.values()
    )
    assert grants == 110

    # Scoped to the baseline codes by name. Since Slice 9D the live tables also hold
    # post-baseline permissions, so an unscoped COUNT(*) would assert "no package may ever add
    # a permission" - a different and wrong claim. What E2-B must not do is disturb the 31.
    baseline_codes = list(e1_contract.ROLE_PERMISSION_COMPATIBILITY_MATRIX)
    assert (
        store_db.execute(
            text(
                "SELECT COUNT(*) FROM authz_permission "
                "WHERE is_active IS TRUE AND permission_code = ANY(:codes)"
            ),
            {"codes": baseline_codes},
        ).scalar_one()
        == 31
    )
    assert (
        store_db.execute(
            text(
                "SELECT COUNT(*) FROM authz_role_permission rp "
                "JOIN authz_permission p ON p.id = rp.permission_id "
                "WHERE rp.is_active IS TRUE AND p.permission_code = ANY(:codes)"
            ),
            {"codes": baseline_codes},
        ).scalar_one()
        == 110
    )
    assert store_db.execute(text("SELECT COUNT(*) FROM role")).scalar_one() == 6

    # ACCOUNT_TAX_VERIFY remains FINANCE_USER-only.
    assert e1_contract.ROLE_PERMISSION_COMPATIBILITY_MATRIX["ACCOUNT_TAX_VERIFY"] == (
        "FINANCE_USER",
    )


@store_covers()
def test_no_business_authority_code_was_added_to_the_e1_contract() -> None:
    """The two vocabularies must never be collapsed, and E2-B adds nothing to
    the E1 catalogue."""

    source = e1_contract.__file__
    text_source = Path(source).read_text(encoding="utf-8")
    assert "business_authority" not in text_source
    assert "BUSINESS_AUTHORITY" not in text_source

    # Nor does the store contract reach into the E1 catalogue.
    assert "authz_permission" not in executable_source(store_contract)
    assert "authz_role_permission" not in executable_source(store_contract)


@store_covers()
def test_the_store_and_the_e1_tables_share_no_column_or_constraint_name(store_db) -> None:
    """A coincidental name collision would be harmless; a shared identifier
    space would not. This asserts the two remain physically separate."""

    for table in E1_PROTECTED_TABLES:
        assert table not in ALL_STORE_TABLES
    assert len(set(ALL_STORE_TABLES)) == 12
