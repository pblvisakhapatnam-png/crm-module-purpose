"""PF-1A-E1 explicit permission compatibility foundation - deterministic proof tests.

These tests are the central deterministic invariant this package exists to prove: the
new ORA-owned `authz_permission` / `authz_role_permission` compatibility mapping must
resolve to exactly the same allow/deny outcome, for every one of the six existing
transitional application roles against every explicit permission code, as the
pre-PF-1A-E1 `require_roles(*SOME_ROLES)` route guards did. See
`app.modules.authorization.contract.ROLE_PERMISSION_COMPATIBILITY_MATRIX`, which is the
single source of truth this file checks the seeded database against.
"""

from __future__ import annotations

import pytest

from app.core.database import SessionLocal
from app.modules.authorization.contract import (
    ACCOUNT_TAX_CAPTURE,
    ACCOUNT_TAX_VERIFY,
    ALL_PERMISSION_CODES,
    EFFECTIVE_ROLE_PERMISSION_MATRIX,
    EVENTS_READ,
    IDENTITY_ROLE_CATALOG_READ,
    KNOWN_ROLE_CODES,
    ROLE_ADMIN,
    ROLE_FINANCE_USER,
    ROLE_OPERATIONS_USER,
    ROLE_PERMISSION_COMPATIBILITY_MATRIX,
    ROLE_SALES_MANAGER,
    ROLE_SALES_USER,
)
from app.modules.authorization.repository import list_role_permission_matrix
from app.modules.authorization.service import UnknownPermissionCodeError, has_permission


def test_seeded_database_matches_the_compatibility_matrix_for_every_role_and_permission() -> None:
    """For every effective permission code x all 6 known roles, the DB-backed `has_permission`
    result must equal membership in `EFFECTIVE_ROLE_PERMISSION_MATRIX`.

    A full cell-by-cell equivalence check over the calculated union of the frozen PF-1A-E1
    baseline and every permission added since. A route that gained or lost access relative to
    the pre-PF-1A-E1 role guards, a seed-migration typo, or an inactive/missing row would all
    surface here as a mismatch.

    The effective matrix is the right source here, not the baseline: this test is about what the
    live database actually enforces. It deliberately does not hardcode a cell count - that would
    have to be edited by every package that adds a permission, and a number nobody can derive is
    a number nobody checks.
    """
    db = SessionLocal()
    try:
        mismatches: list[str] = []
        assert set(ALL_PERMISSION_CODES) == set(EFFECTIVE_ROLE_PERMISSION_MATRIX), (
            "ALL_PERMISSION_CODES has drifted from EFFECTIVE_ROLE_PERMISSION_MATRIX; the "
            "iteration below would then silently skip codes."
        )
        for permission_code in ALL_PERMISSION_CODES:
            expected_roles = set(EFFECTIVE_ROLE_PERMISSION_MATRIX[permission_code])
            for role_code in KNOWN_ROLE_CODES:
                expected = role_code in expected_roles
                actual = has_permission(db, [role_code], permission_code)
                if actual != expected:
                    mismatches.append(f"{permission_code} / {role_code}: expected={expected} actual={actual}")

        assert mismatches == [], "compatibility mismatch(es): " + "; ".join(mismatches)
    finally:
        db.close()


def test_seeded_database_grants_no_extra_permission_beyond_the_contract() -> None:
    """The inverse direction of the check above: the seeded database must not grant a
    role a permission the contract does not list for it (a stray/duplicate seed row).
    """
    db = SessionLocal()
    try:
        db_matrix = list_role_permission_matrix(db)
        for role_code, granted_codes in db_matrix.items():
            for permission_code in granted_codes:
                expected_roles = EFFECTIVE_ROLE_PERMISSION_MATRIX.get(permission_code, ())
                assert role_code in expected_roles, (
                    f"database grants {role_code} -> {permission_code}, "
                    "which is not present in EFFECTIVE_ROLE_PERMISSION_MATRIX"
                )
    finally:
        db.close()


def test_admin_is_not_an_implicit_universal_permission_holder() -> None:
    """ADMIN must never receive a permission merely because it is ADMIN.

    ACCOUNT_TAX_VERIFY is deliberately restricted to FINANCE_USER only, exactly as the
    pre-existing `ACCOUNT_TAX_VERIFICATION_ROLES = ("FINANCE_USER",)` route-body check
    already was. If ADMIN ever gains this permission, some code path has reintroduced
    an implicit "ADMIN can do everything" bypass instead of consulting the
    compatibility mapping.
    """
    db = SessionLocal()
    try:
        assert has_permission(db, [ROLE_ADMIN], ACCOUNT_TAX_VERIFY) is False
        assert has_permission(db, [ROLE_SALES_USER], ACCOUNT_TAX_VERIFY) is False
        assert has_permission(db, [ROLE_SALES_MANAGER], ACCOUNT_TAX_VERIFY) is False
        assert has_permission(db, [ROLE_OPERATIONS_USER], ACCOUNT_TAX_VERIFY) is False
        assert has_permission(db, [ROLE_FINANCE_USER], ACCOUNT_TAX_VERIFY) is True

        # A second, independent negative example: EVENTS_READ and
        # IDENTITY_ROLE_CATALOG_READ both deliberately exclude every Sales/Finance/
        # Operations role, not just ADMIN's usual peers.
        assert has_permission(db, [ROLE_SALES_USER], EVENTS_READ) is False
        assert has_permission(db, [ROLE_SALES_USER], IDENTITY_ROLE_CATALOG_READ) is False
        assert has_permission(db, [ROLE_ADMIN], IDENTITY_ROLE_CATALOG_READ) is True
    finally:
        db.close()


def test_broader_permission_does_not_imply_narrower_permission() -> None:
    """SALES_USER holds ACCOUNT_TAX_CAPTURE (can capture PAN/GST) but must not thereby
    hold ACCOUNT_TAX_VERIFY (can set a final verification state); the two are governed
    by deliberately different role sets and must not collapse into one broad check.
    """
    db = SessionLocal()
    try:
        assert has_permission(db, [ROLE_SALES_USER], ACCOUNT_TAX_CAPTURE) is True
        assert has_permission(db, [ROLE_SALES_USER], ACCOUNT_TAX_VERIFY) is False
    finally:
        db.close()


def test_unknown_role_code_grants_no_permission() -> None:
    db = SessionLocal()
    try:
        assert has_permission(db, ["NOT_A_REAL_ROLE"], IDENTITY_ROLE_CATALOG_READ) is False
    finally:
        db.close()


def test_empty_role_codes_grants_no_permission() -> None:
    db = SessionLocal()
    try:
        assert has_permission(db, [], IDENTITY_ROLE_CATALOG_READ) is False
    finally:
        db.close()


def test_unknown_permission_code_raises_instead_of_silently_resolving() -> None:
    """A typo'd permission code must fail loudly, never silently deny (masking a bug as
    an access-denial) or silently allow (a security hole).
    """
    db = SessionLocal()
    try:
        with pytest.raises(UnknownPermissionCodeError):
            has_permission(db, [ROLE_ADMIN], "NOT_A_REAL_PERMISSION")
    finally:
        db.close()


def test_require_permission_rejects_unknown_permission_code_at_construction_time() -> None:
    """`require_permission(...)` is called once, at route-module import time, with a
    literal permission code. An unregistered code must fail then - as an import-time
    error any test run or app startup will surface - rather than at first request time.
    """
    from app.modules.authorization.dependencies import require_permission

    with pytest.raises(ValueError):
        require_permission("NOT_A_REAL_PERMISSION")


def test_every_seeded_role_code_is_a_known_transitional_role() -> None:
    """Guards against a future edit widening the compatibility matrix to a role code
    that does not exist in the `role` table (which would seed an orphaned/undeliverable
    grant, or fail the migration's FK constraint outright).
    """
    for permission_code, role_codes in ROLE_PERMISSION_COMPATIBILITY_MATRIX.items():
        for role_code in role_codes:
            assert role_code in KNOWN_ROLE_CODES, f"{permission_code} maps to unrecognized role {role_code!r}"
