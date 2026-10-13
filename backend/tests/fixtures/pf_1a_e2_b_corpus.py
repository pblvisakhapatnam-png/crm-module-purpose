"""The PF-1A-E2-B verification obligations, as machine-checkable data.

PF-1A-E2-B sections 5.6, 5.7, 5.7A and 9.

E2-B does not restate the three-group taxonomy: `pf_1a_e2_a_corpus` already
carries it, and duplicating it here would let the two copies drift. This
module adds only what is E2-B's own:

    STORE_COVERS_ATTRIBUTE   a SEPARATE coverage marker, so an E2-B test never
                             accidentally satisfies - or fails - an E2-A
                             coverage rule written for E2-A's own boundaries.
                             In particular E2-A asserts that every test
                             covering a class B1 fixture declares a BOUNDARY
                             and exercises the kernel or the DTO port; an E2-B
                             structural-rejection test does neither, because
                             its subject is the SHIPPED SCHEMA.
    EXPECTED_CONSTRAINTS     the structural constraint set of section 5.6,
                             exactly - "no more, no less". Adding a constraint
                             silently moves a class A fixture into B1/B2 and
                             suppresses a defect class the kernel owns;
                             removing one silently strips a rejection proof.
    EXPECTED_INDEXES         the indexes supporting authority_code discovery,
                             stable-reference discovery, per-object lineage
                             retrieval and version dereference.
    PARITY_CORPUS            the 64 scenarios the central parity proof covers.

WHY EVERY ONE OF THE 87 MANIFEST IDS HAS AN E2-B TEST, including the ones
whose semantics E2-A proves:

    class A   (14)  storable here, read back byte-identical, resolved through
                    the wired kernel, and parity-tested.
    class B1  (12)  the INSERT must FAIL against the shipped schema. E2-A
                    proves the fail-closed semantics at its named boundary;
                    E2-B proves the rejection.
    class B2   (3)  the INSERT must FAIL, and there is deliberately NO E2-A
                    counterpart to prove.
    V         (12)  valid stored shapes, parity-tested.
    NS        (46)  38 parity-tested through both compositions; the other 8
                    carry the E2-B half section 5.7A states for them - a
                    reachability, surface or cross-reference assertion, never
                    a weakened parity test.
"""

from __future__ import annotations

import ast
import inspect
from collections.abc import Callable
from types import FunctionType, ModuleType
from typing import Any, TypeVar

from tests.fixtures.pf_1a_e2_a_corpus import (
    AUTHORITY_STORE_FIXTURES,
    CLASS_A,
    CLASS_B1,
    CLASS_B2,
    NON_STORE_SCENARIOS,
    VALID_SHAPE_SCENARIOS,
)

# ---------------------------------------------------------------------------
# The E2-B coverage marker
# ---------------------------------------------------------------------------

STORE_COVERS_ATTRIBUTE = "pf_1a_e2_b_covers"
STORE_PARITY_ATTRIBUTE = "pf_1a_e2_b_parity"

_F = TypeVar("_F", bound=Callable[..., Any])


def store_covers(*ids: str, parity: bool = False) -> Callable[[_F], _F]:
    """Record which manifest IDs an E2-B test discharges.

    `parity=True` additionally records that the test drives the scenario
    through BOTH named compositions and requires them to agree, so the
    coverage test can check the parity corpus is exactly the 64 scenarios
    section 9 defines rather than a convenient subset.
    """

    def decorate(function: _F) -> _F:
        setattr(function, STORE_COVERS_ATTRIBUTE, tuple(ids))
        if parity:
            setattr(function, STORE_PARITY_ATTRIBUTE, True)
        return function

    return decorate



# ---------------------------------------------------------------------------
# Source inspection that reads CODE, not prose
# ---------------------------------------------------------------------------


def executable_source(subject: ModuleType | FunctionType) -> str:
    """The subject's source with every docstring and comment removed.

    Several E2-B assertions are about what the production code DOES - that no
    discovery query applies a retraction predicate, that nothing issues an
    UPDATE, that no one-row shortcut hides multiplicity. Those modules
    deliberately DESCRIBE the forbidden constructs at length in their
    docstrings, precisely so a later reader understands why each is absent, so
    a naive substring scan over raw source would find the prose and fail.
    Parsing to an AST and unparsing drops comments outright and lets the
    docstring nodes be removed explicitly, leaving only executable code.
    """

    tree = ast.parse(inspect.getsource(subject))
    for node in ast.walk(tree):
        if not isinstance(
            node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
        ):
            continue
        body = node.body
        if (
            body
            and isinstance(body[0], ast.Expr)
            and isinstance(body[0].value, ast.Constant)
            and isinstance(body[0].value.value, str)
        ):
            node.body = body[1:] or [ast.Pass()]
    return ast.unparse(tree)

# ---------------------------------------------------------------------------
# Derived obligation sets
# ---------------------------------------------------------------------------


def _by_class(verification_class: str) -> tuple[str, ...]:
    return tuple(
        sorted(
            fixture.fixture_id
            for fixture in AUTHORITY_STORE_FIXTURES.values()
            if fixture.verification_class == verification_class
        )
    )


CLASS_A_FIXTURES = _by_class(CLASS_A)
CLASS_B1_FIXTURES = _by_class(CLASS_B1)
CLASS_B2_FIXTURES = _by_class(CLASS_B2)

VALID_SHAPE_IDS = tuple(sorted(VALID_SHAPE_SCENARIOS))

PARITY_YES_NON_STORE_IDS = tuple(
    sorted(
        scenario.scenario_id
        for scenario in NON_STORE_SCENARIOS.values()
        if scenario.parity_required
    )
)
PARITY_NO_NON_STORE_IDS = tuple(
    sorted(
        scenario.scenario_id
        for scenario in NON_STORE_SCENARIOS.values()
        if not scenario.parity_required
    )
)

# Section 9, "PARITY ... has exactly THREE parts and no others".
PARITY_CORPUS = tuple(sorted(CLASS_A_FIXTURES + VALID_SHAPE_IDS + PARITY_YES_NON_STORE_IDS))

# Every manifest ID E2-B must discharge with an executing test of its own.
ALL_E2B_OBLIGATIONS = tuple(
    sorted(
        set(AUTHORITY_STORE_FIXTURES) | set(VALID_SHAPE_SCENARIOS) | set(NON_STORE_SCENARIOS)
    )
)

# Section 5.7's CLOSED, unconditional justified exclusion list. Nothing on it
# is conditional on what the implemented kernel turns out to do.
JUSTIFIED_PARITY_EXCLUDED_REASON_CODES = {
    "ASSIGNMENT_TARGET_INVALID": (
        "class B1: the assignment person/position XOR CHECK makes both shapes "
        "(B1-02, B1-03) unstorable here; E2-A fixtures ASSIGNMENT-TARGET-BOTH and "
        "ASSIGNMENT-TARGET-NEITHER prove the semantics at the PURE KERNEL boundary, stage S7."
    ),
    "AUTHORITY_VERSION_AMBIGUOUS": (
        "kernel-internal: proved unreachable from any provider input by the E2-A 11.4a "
        "single-effective-version theorem, so no store can present the state; covered by "
        "non-store scenario NS-K-01."
    ),
    "INTERNAL_CONTRACT_VIOLATION": (
        "kernel-internal self-check: by definition not a provider-supplied state; covered by "
        "non-store scenario NS-K-02."
    ),
}


# ---------------------------------------------------------------------------
# The structural constraint and index manifest of section 5.6
# ---------------------------------------------------------------------------
# `contype` values are PostgreSQL's own: p = primary key, u = unique,
# c = check, f = foreign key.

_FAMILIES = (
    ("authority", "authz_business_authority"),
    ("role", "authz_business_authority_role"),
    ("rule", "authz_business_authority_rule"),
    ("assignment", "authz_business_authority_assignment"),
)


def _expected_constraints() -> dict[str, set[tuple[str, str]]]:
    expected: dict[str, set[tuple[str, str]]] = {}

    for short, stable in _FAMILIES:
        version = f"{stable}_version"
        retraction = f"{stable}_retraction"

        # Stable identity: its own primary key and the uniqueness that makes
        # `object_id` a usable foreign-key target.
        expected[stable] = {
            ("p", f"{stable}_pkey"),
            ("u", f"uq_ba_{short}_object_id"),
        }

        # Version: the immutable identity/version key, the SINGLE-ROW interval
        # shape check, the closed provenance domain, and the foreign key to the
        # STABLE identity row (class B2-01).
        expected[version] = {
            ("p", f"{version}_pkey"),
            ("u", f"uq_ba_{short}_version_object_version"),
            ("c", f"ck_ba_{short}_version_interval"),
            ("c", f"ck_ba_{short}_publication_reference_type"),
            ("f", f"fk_ba_{short}_version_object_id"),
        }

        # Retraction: the closed provenance domain and the foreign key to the
        # STABLE identity row (class B2-02). Deliberately NO uniqueness over
        # (object_id, object_version) and NO foreign key to a VERSION row: a
        # duplicated retraction (A-05) and a dangling retraction (A-04) must
        # remain storable for the kernel to classify.
        expected[retraction] = {
            ("p", f"{retraction}_pkey"),
            ("c", f"ck_ba_{short}_retraction_publication_reference_type"),
            ("f", f"fk_ba_{short}_retraction_object_id"),
        }

    # Rule and Assignment additionally reference the STABLE identity of the
    # role/authority they name - never a specific version, which would break
    # correction (E2-A invariant I-5). These are class B2-03.
    expected["authz_business_authority_rule_version"] |= {
        ("f", "fk_ba_rule_version_role_reference"),
        ("f", "fk_ba_rule_version_authority_reference"),
    }
    expected["authz_business_authority_assignment_version"] |= {
        ("f", "fk_ba_assignment_version_role_reference"),
        # Person XOR Position: exactly one non-null (class B1-02, B1-03).
        ("c", "ck_ba_assignment_version_target_xor"),
    }
    return expected


EXPECTED_CONSTRAINTS = _expected_constraints()


def _expected_indexes() -> dict[str, set[str]]:
    expected: dict[str, set[str]] = {}
    for short, stable in _FAMILIES:
        version = f"{stable}_version"
        retraction = f"{stable}_retraction"
        # Every unique/primary-key constraint above is backed by an index;
        # `uq_ba_{short}_version_object_version` leads on `object_id`, which is
        # what serves per-object LINEAGE RETRIEVAL and version DEREFERENCE.
        expected[stable] = {f"{stable}_pkey", f"uq_ba_{short}_object_id"}
        expected[version] = {f"{version}_pkey", f"uq_ba_{short}_version_object_version"}
        expected[retraction] = {
            f"{retraction}_pkey",
            f"ix_ba_{short}_retraction_object_id",
        }

    # Discovery indexes: authority_code, and the two stable-reference columns.
    expected["authz_business_authority_version"].add("ix_ba_authority_version_authority_code")
    expected["authz_business_authority_rule_version"].add("ix_ba_rule_version_authority_reference")
    expected["authz_business_authority_assignment_version"].add(
        "ix_ba_assignment_version_role_reference"
    )
    return expected


EXPECTED_INDEXES = _expected_indexes()

# The E1 tables this package must leave untouched (section 7).
E1_PROTECTED_TABLES = (
    "role",
    "app_user",
    "user_role",
    "authz_permission",
    "authz_role_permission",
)
