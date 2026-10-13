"""PF-1A-E3: the write-path boundary, the data-driven protection flag, and no bootstrap."""

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
    configuration_composition,
    configuration_contract,
    configuration_domain,
    configuration_models,
    configuration_policy,
    configuration_repository,
    configuration_service,
    repository as e2_repository,
    resolver,
)
from app.modules.authorization.business_authority.configuration_domain import (
    ConfigurationGovernanceError,
)
from app.modules.authorization.business_authority.ports import AuthorityConfigurationPort

_APP_ROOT = Path(app.__file__).resolve().parent
_PACKAGE_ROOT = _APP_ROOT / "modules" / "authorization" / "business_authority"
_MIGRATION = (
    _APP_ROOT.parent
    / "alembic"
    / "versions"
    / "20260906_0032_pf_1a_e3_governed_authority_configuration.py"
)

_E3_MODULES = (
    configuration_contract,
    configuration_domain,
    configuration_policy,
    configuration_models,
    configuration_repository,
    configuration_service,
    configuration_composition,
)


def _code_only(source: str) -> str:
    """Return `source` with DOCSTRINGS and COMMENTS removed, code intact.

    The assertions below search for things that must not appear in CODE. Both this file and the
    modules it inspects discuss those very things at length in prose, so a naive substring scan
    over raw source would make an accurate comment a test failure. Other string literals are
    deliberately KEPT, because a literal in code is exactly what these tests exist to catch.
    """

    spans: list[tuple[int, int]] = []
    for node in ast.walk(ast.parse(source)):
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
            spans.append((first.lineno, first.end_lineno or first.lineno))
    blanked = [
        "" if any(start <= number <= end for start, end in spans) else line
        for number, line in enumerate(source.splitlines(), start=1)
    ]
    kept = [
        token
        for token in tokenize.generate_tokens(io.StringIO("\n".join(blanked) + "\n").readline)
        if token.type != tokenize.COMMENT
    ]
    return tokenize.untokenize(kept)


def _e3_sources() -> dict[str, str]:
    return {module.__name__: _code_only(inspect.getsource(module)) for module in _E3_MODULES}


def test_the_e2_authority_configuration_port_still_defines_no_write_operation() -> None:
    """PF-1A-E3 adds its governed writer WITHOUT widening the read port."""

    assert {name for name in dir(AuthorityConfigurationPort) if not name.startswith("_")} == {
        "find_business_authority_ids_by_code",
        "find_rule_ids_for_authority",
        "find_assignment_ids_for_role",
        "get_lineage",
        "get_published_version",
    }


def test_the_e2_repository_still_has_no_write_path() -> None:
    source = _code_only(inspect.getsource(e2_repository))
    for forbidden in (
        "INSERT ",
        "UPDATE ",
        "DELETE ",
        "def create_",
        "def publish_",
        "def insert_",
    ):
        assert forbidden not in source, f"{forbidden!r} appeared in the E2 repository"


def test_the_governed_writer_lives_only_in_the_e3_repository() -> None:
    sources = _e3_sources()
    prefix = "app.modules.authorization.business_authority."
    assert "INSERT INTO" in sources[prefix + "configuration_repository"]
    for name in ("configuration_policy", "configuration_domain", "configuration_contract"):
        assert "INSERT" not in sources[prefix + name]


def test_protection_is_never_a_literal_authority_code_comparison_in_production_code() -> None:
    """ADR-033: `is_protected_meta_authority` is an explicit, data-driven classification field,
    never a hard-coded comparison against a literal administration code."""

    literal = "AUTHORITY" + "_CONFIGURATION_ADMIN"
    for name, source in _e3_sources().items():
        assert literal not in source, name
    assert literal not in _code_only(_MIGRATION.read_text(encoding="utf-8"))
    assert (
        "is_protected_meta_authority"
        in _e3_sources()["app.modules.authorization.business_authority.configuration_policy"]
    )


def test_no_e1_login_role_code_reaches_the_e3_modules() -> None:
    """A Business Authority is never derived, inferred or defaulted from an Application/Login
    Role code. Not even ADMIN.

    The scan is a BARE SUBSTRING scan over executable source, matching the predecessor boundary
    exactly, so a role code cannot slip in incidentally inside a longer identifier. That is not
    a hypothetical: `CHANGE_REJECTED_BY_ADMINISTRATOR` was renamed to
    `CHANGE_REJECTED_BY_GOVERNANCE_DECISION` for precisely this reason. Naming the governance
    DECISION rather than the acting role is also the more accurate name, so nothing was
    sacrificed to satisfy the scan.

    Docstrings and comments are stripped first: these modules deliberately discuss both
    vocabularies in prose so a later reader cannot collapse them.
    """

    for role_code in e1_contract.KNOWN_ROLE_CODES:
        for name, source in _e3_sources().items():
            assert role_code not in source, f"{name} names the login role {role_code}"
    for name, source in _e3_sources().items():
        assert "authorization.contract" not in source, name
        assert "KNOWN_ROLE_CODES" not in source, name
        assert "require_permission" not in source, name
        assert "require_roles" not in source, name


def test_the_package_still_exposes_no_route_and_no_api_schema_surface() -> None:
    names = sorted(path.name for path in _PACKAGE_ROOT.glob("*.py"))
    assert "routes.py" not in names
    assert "schemas.py" not in names


def test_the_migration_seeds_nothing_at_all() -> None:
    """Not a role, authority, rule, assignment, Configuration Change or bootstrap holder."""

    source = _code_only(_MIGRATION.read_text(encoding="utf-8"))
    for forbidden in ("INSERT INTO", "bulk_insert", "op.execute("):
        assert forbidden not in source, forbidden


def test_no_e3_module_reaches_the_test_tree_or_a_synthetic_provider() -> None:
    for module in _E3_MODULES:
        raw = inspect.getsource(module)
        assert "tests." not in raw, module.__name__
        assert "import tests" not in raw, module.__name__
    names = {path.name for path in _PACKAGE_ROOT.rglob("*.py")}
    assert not any("reference_provider" in name or "synthetic" in name for name in names)


def test_the_governed_production_composition_refuses_to_compose() -> None:
    """Section 9.6 permits refusing to compose or returning a deterministic fail-closed object.
    THIS SEAM REFUSES: an unusable object cannot be misused."""

    session = SessionLocal()
    try:
        with pytest.raises(
            configuration_composition.GovernedConfigurationCompositionUnavailableError
        ) as raised:
            configuration_composition.build_governed_authority_configuration_service(session)
    finally:
        session.close()
    message = str(raised.value)
    assert "authoritative" in message
    assert "9.6" in message
    assert "Q-10" in message


def test_the_writer_seam_does_not_reuse_the_resolver_composition_refusal() -> None:
    """PF-1A-E2-B's invariant is that exactly ONE function in this package raises the RESOLVER
    composition error, so a successor cannot add a second resolver-assembly point. PF-1A-E3
    composes a WRITER, not a resolver, so it must refuse through its own type - otherwise a
    genuinely different seam would be indistinguishable from a duplicate of that one.

    The two types are kept unrelated in both directions, so a caller handling one failure can
    never silently swallow the other.
    """

    writer_error = configuration_composition.GovernedConfigurationCompositionUnavailableError
    resolver_error = resolver.ProductionCompositionUnavailableError
    assert writer_error is not resolver_error
    assert not issubclass(writer_error, resolver_error)
    assert not issubclass(resolver_error, writer_error)
    assert issubclass(writer_error, RuntimeError)

    source = _code_only(inspect.getsource(configuration_composition))
    assert "ProductionCompositionUnavailableError" not in source


def test_the_governed_seam_takes_no_switch_through_which_a_provider_could_be_selected() -> None:
    signature = inspect.signature(
        configuration_composition.build_governed_authority_configuration_service
    )
    assert list(signature.parameters) == ["db"]
    assert not any(
        parameter.kind in (parameter.VAR_POSITIONAL, parameter.VAR_KEYWORD)
        for parameter in signature.parameters.values()
    )
    source = _code_only(inspect.getsource(configuration_composition))
    for forbidden in ("environ", "getenv", "settings", "feature_flag", "toggle"):
        assert forbidden not in source, forbidden


def test_the_service_cannot_be_built_without_every_authoritative_dependency() -> None:
    session = SessionLocal()
    try:
        for absent in ("authority_configuration_port", "actor_person_port", "hr_reference_port"):
            kwargs = {
                "authority_configuration_port": object(),
                "actor_person_port": object(),
                "hr_reference_port": object(),
            }
            kwargs[absent] = None
            with pytest.raises(ConfigurationGovernanceError):
                configuration_service.GovernedAuthorityConfigurationService(session, **kwargs)
    finally:
        session.close()


def test_the_e1_permission_compatibility_facts_are_unchanged() -> None:
    """The frozen PF-1A-E1 baseline is still exactly 31 permissions and 110 grants.

    Asserted against `ROLE_PERMISSION_COMPATIBILITY_MATRIX` specifically, not against
    `ALL_PERMISSION_CODES`. Since Slice 9D those are different things: the baseline matrix is
    frozen E1 evidence, while `ALL_PERMISSION_CODES` derives from the effective matrix and grows
    as later packages add permissions. Asserting the baseline is the stronger statement - it is
    what "unchanged by this package" actually means - and it keeps this test meaningful rather
    than turning it into a number that every future slice has to bump.
    """
    assert len(e1_contract.ROLE_PERMISSION_COMPATIBILITY_MATRIX) == 31
    assert len(e1_contract.KNOWN_ROLE_CODES) == 6
    grants = sum(
        len(role_codes)
        for role_codes in e1_contract.ROLE_PERMISSION_COMPATIBILITY_MATRIX.values()
    )
    assert grants == 110

    # Every baseline code is still enforced: the effective matrix is a superset that preserves
    # each baseline entry's grant set exactly, never shadowing or narrowing one.
    for permission_code, role_codes in e1_contract.ROLE_PERMISSION_COMPATIBILITY_MATRIX.items():
        assert e1_contract.EFFECTIVE_ROLE_PERMISSION_MATRIX[permission_code] == role_codes
