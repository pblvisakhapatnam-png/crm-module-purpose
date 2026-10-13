"""Focused tests for `app.modules.authorization.repository`, independent of the full
compatibility-matrix equivalence proof in `test_authorization_compatibility_matrix.py`.
"""

from __future__ import annotations

from app.core.database import SessionLocal
from app.modules.authorization.contract import (
    ACCOUNT_TAX_VERIFY,
    IDENTITY_ROLE_CATALOG_READ,
    ROLE_ADMIN,
    ROLE_FINANCE_USER,
    ROLE_SALES_USER,
)
from app.modules.authorization.repository import (
    list_active_permission_codes_for_role_codes,
    list_role_permission_matrix,
)


def test_list_active_permission_codes_returns_union_across_multiple_roles() -> None:
    db = SessionLocal()
    try:
        finance_only = list_active_permission_codes_for_role_codes(db, [ROLE_FINANCE_USER])
        admin_only = list_active_permission_codes_for_role_codes(db, [ROLE_ADMIN])
        combined = list_active_permission_codes_for_role_codes(db, [ROLE_FINANCE_USER, ROLE_ADMIN])

        assert ACCOUNT_TAX_VERIFY in finance_only
        assert ACCOUNT_TAX_VERIFY not in admin_only
        assert IDENTITY_ROLE_CATALOG_READ in admin_only
        assert IDENTITY_ROLE_CATALOG_READ not in finance_only

        # The union of two roles' permissions must be a superset of each individually,
        # and must not silently drop a permission one of the roles holds on its own.
        assert finance_only.issubset(combined)
        assert admin_only.issubset(combined)
        assert ACCOUNT_TAX_VERIFY in combined
        assert IDENTITY_ROLE_CATALOG_READ in combined
    finally:
        db.close()


def test_list_active_permission_codes_returns_empty_set_for_no_roles() -> None:
    db = SessionLocal()
    try:
        assert list_active_permission_codes_for_role_codes(db, []) == set()
    finally:
        db.close()


def test_list_active_permission_codes_ignores_unrecognized_role_codes_mixed_with_real_ones() -> None:
    db = SessionLocal()
    try:
        mixed = list_active_permission_codes_for_role_codes(db, ["NOT_A_REAL_ROLE", ROLE_SALES_USER])
        sales_only = list_active_permission_codes_for_role_codes(db, [ROLE_SALES_USER])
        assert mixed == sales_only
    finally:
        db.close()


def test_list_role_permission_matrix_returns_every_seeded_role() -> None:
    db = SessionLocal()
    try:
        matrix = list_role_permission_matrix(db)
        # Every one of the six transitional roles is granted at least one permission
        # today, so every one of them must appear as a key.
        for role_code in (
            "ADMIN",
            "SALES_USER",
            "SALES_MANAGER",
            "FINANCE_USER",
            "OPERATIONS_USER",
            "MANAGEMENT_READ_ONLY",
        ):
            assert role_code in matrix
            assert matrix[role_code], f"{role_code} unexpectedly has zero permissions"
    finally:
        db.close()
