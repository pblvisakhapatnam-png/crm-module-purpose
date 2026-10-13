"""Slice 9D - Interaction Foundation.

This file covers two things:

1. The **authorization foundation correction** 9D had to make before it could add a single
   permission. PF-1A-E1's `ROLE_PERMISSION_COMPATIBILITY_MATRIX` is frozen evidence, compared
   against an independently derived fixture; adding a post-E1 permission to it would make that
   comparison vacuous. So the catalogue is now a disjoint union of a frozen baseline and a
   growing post-baseline matrix, and these tests pin that structure - including driving the
   disjointness guard with synthetic bad input, because a guard that has never been shown to
   fail is an assertion of intent rather than a control (Slice 9B, repeatedly).

2. The **9D migration's own seeding**: five permissions, nineteen grants, and the deliberate
   exclusion of Finance from message content.

Counts are asserted where they are genuinely frozen (the 31/110 baseline) and *calculated*
where they are not (the effective union). Hardcoding an effective total would force every future
package to bump a number, and a number nobody can derive is a number nobody checks.
"""

from __future__ import annotations

import pytest
from sqlalchemy import text

from app.core.database import SessionLocal
from app.modules.authorization.contract import (
    ALL_PERMISSION_CODES,
    EFFECTIVE_ROLE_PERMISSION_MATRIX,
    INTERACTION_CONTENT_READ,
    INTERACTION_CREATE,
    INTERACTION_DELETE,
    INTERACTION_READ,
    INTERACTION_UPDATE,
    KNOWN_ROLE_CODES,
    PERMISSION_DESCRIPTIONS,
    POST_BASELINE_ROLE_PERMISSION_MATRIX,
    ROLE_ADMIN,
    ROLE_FINANCE_USER,
    ROLE_MANAGEMENT_READ_ONLY,
    ROLE_OPERATIONS_USER,
    ROLE_PERMISSION_COMPATIBILITY_MATRIX,
    ROLE_SALES_MANAGER,
    ROLE_SALES_USER,
    assert_permission_matrices_are_disjoint,
)
from app.modules.authorization.service import has_permission

INTERACTION_PERMISSIONS = (
    INTERACTION_READ,
    INTERACTION_CONTENT_READ,
    INTERACTION_CREATE,
    INTERACTION_UPDATE,
    INTERACTION_DELETE,
)


# ===========================================================================
# The frozen baseline stays frozen
# ===========================================================================


def test_the_pf_1a_e1_baseline_matrix_is_untouched_by_this_slice() -> None:
    """31 permissions and 110 grants, unchanged. This is the whole reason for the split: if
    9D had added its five codes here instead, PROOF A in `test_authorization_baseline_
    equivalence.py` would be comparing a moved goalpost to itself from now on."""
    assert len(ROLE_PERMISSION_COMPATIBILITY_MATRIX) == 31
    grants = sum(len(roles) for roles in ROLE_PERMISSION_COMPATIBILITY_MATRIX.values())
    assert grants == 110

    for permission_code in INTERACTION_PERMISSIONS:
        assert permission_code not in ROLE_PERMISSION_COMPATIBILITY_MATRIX


def test_the_effective_matrix_is_the_calculated_union_of_the_two_halves() -> None:
    """Deliberately calculated, never hardcoded. A future package adding a permission should
    not have to edit a total here, and a total that must be hand-edited is one that stops
    being checked."""
    expected_codes = set(ROLE_PERMISSION_COMPATIBILITY_MATRIX) | set(
        POST_BASELINE_ROLE_PERMISSION_MATRIX
    )
    assert set(EFFECTIVE_ROLE_PERMISSION_MATRIX) == expected_codes
    assert len(EFFECTIVE_ROLE_PERMISSION_MATRIX) == len(
        ROLE_PERMISSION_COMPATIBILITY_MATRIX
    ) + len(POST_BASELINE_ROLE_PERMISSION_MATRIX)

    expected_grants = sum(
        len(roles) for roles in ROLE_PERMISSION_COMPATIBILITY_MATRIX.values()
    ) + sum(len(roles) for roles in POST_BASELINE_ROLE_PERMISSION_MATRIX.values())
    actual_grants = sum(len(roles) for roles in EFFECTIVE_ROLE_PERMISSION_MATRIX.values())
    assert actual_grants == expected_grants


def test_the_effective_matrix_preserves_every_baseline_grant_set_exactly() -> None:
    """The union must not shadow, widen or narrow a baseline entry."""
    for permission_code, role_codes in ROLE_PERMISSION_COMPATIBILITY_MATRIX.items():
        assert EFFECTIVE_ROLE_PERMISSION_MATRIX[permission_code] == role_codes


def test_all_permission_codes_derives_from_the_effective_matrix() -> None:
    assert set(ALL_PERMISSION_CODES) == set(EFFECTIVE_ROLE_PERMISSION_MATRIX)
    assert len(ALL_PERMISSION_CODES) == len(EFFECTIVE_ROLE_PERMISSION_MATRIX)


# ===========================================================================
# The disjointness guard, driven with synthetic bad input
# ===========================================================================


def test_the_disjointness_guard_accepts_genuinely_disjoint_matrices() -> None:
    assert_permission_matrices_are_disjoint({"A": ("ADMIN",)}, {"B": ("ADMIN",)})


def test_the_disjointness_guard_rejects_an_overlapping_code() -> None:
    """The failure this guard exists for: a code added to both halves, where dict merging
    would let the post-baseline entry silently shadow the frozen baseline one."""
    with pytest.raises(RuntimeError) as exc:
        assert_permission_matrices_are_disjoint(
            {"SHARED": ("ADMIN",), "A": ("ADMIN",)},
            {"SHARED": ("SALES_USER",)},
        )
    assert "SHARED" in str(exc.value)


def test_the_disjointness_guard_names_every_overlapping_code() -> None:
    with pytest.raises(RuntimeError) as exc:
        assert_permission_matrices_are_disjoint(
            {"ONE": ("ADMIN",), "TWO": ("ADMIN",)},
            {"ONE": ("ADMIN",), "TWO": ("ADMIN",)},
        )
    message = str(exc.value)
    assert "ONE" in message and "TWO" in message


def test_the_disjointness_guard_is_actually_wired_into_module_import() -> None:
    """Proves the guard is not merely defined. If the real matrices ever overlap, importing
    `contract` must fail - so calling it with the real values must be a no-op today, and the
    call site must exist in the module source."""
    assert_permission_matrices_are_disjoint(
        ROLE_PERMISSION_COMPATIBILITY_MATRIX, POST_BASELINE_ROLE_PERMISSION_MATRIX
    )

    from pathlib import Path

    from app.modules.authorization import contract as contract_module

    source = Path(contract_module.__file__).read_text(encoding="utf-8")
    assert "assert_permission_matrices_are_disjoint(\n    ROLE_PERMISSION_COMPATIBILITY_MATRIX" in source, (
        "the disjointness guard is defined but no longer invoked at module import time"
    )


# ===========================================================================
# The 9D permissions themselves
# ===========================================================================


def test_the_five_interaction_permissions_are_post_baseline_and_described() -> None:
    """A SUBSET check, not equality with the whole matrix.

    Corrected by Slice 9C (8 September 2026): the original assertion here was
    `set(POST_BASELINE_ROLE_PERMISSION_MATRIX) == set(INTERACTION_PERMISSIONS)`, which claimed
    9D's five permissions were the ENTIRE post-baseline matrix. That was only ever true because
    9D happened to be the first package to add to it - `POST_BASELINE_ROLE_PERMISSION_MATRIX` is
    explicitly documented (app.modules.authorization.contract) as "the live, growing half...
    grows as packages add permissions", so a second package (9C's DOCUMENT_READ/DOCUMENT_UPLOAD/
    DOCUMENT_CONTENT_READ) was always going to make the old equality false. This test now proves
    what it actually should: that interactions' own five permissions are present and described,
    without asserting anything about what else the shared matrix may also contain.
    """
    assert set(INTERACTION_PERMISSIONS).issubset(set(POST_BASELINE_ROLE_PERMISSION_MATRIX))
    for permission_code in INTERACTION_PERMISSIONS:
        assert permission_code in PERMISSION_DESCRIPTIONS
        assert PERMISSION_DESCRIPTIONS[permission_code].strip()


def test_the_interaction_grant_sets_are_exactly_as_designed() -> None:
    assert POST_BASELINE_ROLE_PERMISSION_MATRIX[INTERACTION_READ] == (
        ROLE_ADMIN,
        ROLE_SALES_USER,
        ROLE_SALES_MANAGER,
        ROLE_FINANCE_USER,
        ROLE_OPERATIONS_USER,
        ROLE_MANAGEMENT_READ_ONLY,
    )
    assert POST_BASELINE_ROLE_PERMISSION_MATRIX[INTERACTION_CONTENT_READ] == (
        ROLE_ADMIN,
        ROLE_SALES_USER,
        ROLE_SALES_MANAGER,
        ROLE_OPERATIONS_USER,
        ROLE_MANAGEMENT_READ_ONLY,
    )
    assert POST_BASELINE_ROLE_PERMISSION_MATRIX[INTERACTION_CREATE] == (
        ROLE_ADMIN,
        ROLE_SALES_USER,
        ROLE_SALES_MANAGER,
    )
    assert POST_BASELINE_ROLE_PERMISSION_MATRIX[INTERACTION_UPDATE] == (
        ROLE_ADMIN,
        ROLE_SALES_USER,
        ROLE_SALES_MANAGER,
    )
    assert POST_BASELINE_ROLE_PERMISSION_MATRIX[INTERACTION_DELETE] == (
        ROLE_ADMIN,
        ROLE_SALES_MANAGER,
    )

    # Corrected by Slice 9C: sum only interactions' own five keys, not the whole shared matrix -
    # see the docstring on the previous test for why summing the whole matrix stopped being a
    # valid check for one slice's own permissions the moment a second slice (9C) added its own.
    grants = sum(len(POST_BASELINE_ROLE_PERMISSION_MATRIX[code]) for code in INTERACTION_PERMISSIONS)
    assert grants == 19


def test_finance_sees_that_a_conversation_happened_but_not_what_it_said() -> None:
    """The deliberate asymmetry, pinned so it cannot drift into a contradiction.

    Customer message bodies and participant addresses are Restricted personal/statutory data
    and are need-to-know. Finance's work - receivables, activation, invoicing - is served by
    knowing a conversation occurred, its channel, subject and outcome. If Finance is later
    found to need message bodies, widen this grant explicitly and change this test with it.
    """
    assert ROLE_FINANCE_USER in POST_BASELINE_ROLE_PERMISSION_MATRIX[INTERACTION_READ]
    assert ROLE_FINANCE_USER not in POST_BASELINE_ROLE_PERMISSION_MATRIX[INTERACTION_CONTENT_READ]


def test_content_read_is_never_broader_than_read() -> None:
    """Reading a message body without being allowed to see the conversation exists would be
    incoherent. Content access must be a subset of metadata access."""
    assert set(POST_BASELINE_ROLE_PERMISSION_MATRIX[INTERACTION_CONTENT_READ]).issubset(
        set(POST_BASELINE_ROLE_PERMISSION_MATRIX[INTERACTION_READ])
    )


def test_every_interaction_grant_names_a_known_role() -> None:
    for permission_code, role_codes in POST_BASELINE_ROLE_PERMISSION_MATRIX.items():
        unknown = set(role_codes) - set(KNOWN_ROLE_CODES)
        assert unknown == set(), f"{permission_code} grants unknown role(s) {sorted(unknown)}"


# ===========================================================================
# The migration actually seeded them
# ===========================================================================


def test_the_migration_seeded_five_permissions_and_nineteen_grants() -> None:
    db = SessionLocal()
    try:
        permission_count = db.execute(
            text(
                "SELECT COUNT(*) FROM authz_permission "
                "WHERE is_active IS TRUE AND permission_code = ANY(:codes)"
            ),
            {"codes": list(INTERACTION_PERMISSIONS)},
        ).scalar_one()
        assert permission_count == 5

        grant_count = db.execute(
            text(
                "SELECT COUNT(*) FROM authz_role_permission rp "
                "JOIN authz_permission p ON p.id = rp.permission_id "
                "WHERE rp.is_active IS TRUE AND p.permission_code = ANY(:codes)"
            ),
            {"codes": list(INTERACTION_PERMISSIONS)},
        ).scalar_one()
        assert grant_count == 19
    finally:
        db.close()


def test_the_seeded_database_resolves_every_interaction_cell_as_designed() -> None:
    """Cell-by-cell, through the real `has_permission`, against the contract - so a seed typo
    or a missing row surfaces here rather than at first request."""
    db = SessionLocal()
    try:
        mismatches: list[str] = []
        for permission_code in INTERACTION_PERMISSIONS:
            expected_roles = set(POST_BASELINE_ROLE_PERMISSION_MATRIX[permission_code])
            for role_code in KNOWN_ROLE_CODES:
                expected = role_code in expected_roles
                actual = has_permission(db, [role_code], permission_code)
                if actual != expected:
                    mismatches.append(
                        f"{permission_code} / {role_code}: expected={expected} actual={actual}"
                    )
        assert mismatches == [], "; ".join(mismatches)
    finally:
        db.close()


def test_finance_is_denied_content_read_by_the_live_database() -> None:
    """The asymmetry above, proved against the database rather than only the contract."""
    db = SessionLocal()
    try:
        assert has_permission(db, [ROLE_FINANCE_USER], INTERACTION_READ) is True
        assert has_permission(db, [ROLE_FINANCE_USER], INTERACTION_CONTENT_READ) is False
    finally:
        db.close()


def test_admin_did_not_become_an_implicit_holder_of_every_interaction_permission() -> None:
    """ADMIN legitimately holds all five here, but by explicit grant. The proof that no
    implicit bypass was introduced is that a role deliberately excluded stays excluded."""
    db = SessionLocal()
    try:
        assert has_permission(db, [ROLE_FINANCE_USER], INTERACTION_CREATE) is False
        assert has_permission(db, [ROLE_OPERATIONS_USER], INTERACTION_CREATE) is False
        assert has_permission(db, [ROLE_SALES_USER], INTERACTION_DELETE) is False
        assert has_permission(db, [ROLE_MANAGEMENT_READ_ONLY], INTERACTION_DELETE) is False
    finally:
        db.close()


# ===========================================================================
# The tables the migration created
# ===========================================================================


def test_the_interaction_tables_and_their_indexes_exist() -> None:
    db = SessionLocal()
    try:
        tables = {
            row[0]
            for row in db.execute(
                text(
                    "SELECT table_name FROM information_schema.tables "
                    "WHERE table_name IN ('interaction', 'interaction_participant')"
                )
            )
        }
        assert tables == {"interaction", "interaction_participant"}

        indexes = {
            row[0]
            for row in db.execute(
                text("SELECT indexname FROM pg_indexes WHERE tablename LIKE 'interaction%'")
            )
        }
        for expected in (
            "ux_interaction_external_message",
            "ux_interaction_idempotency_key",
            "ix_interaction_linked_record",
            "ix_interaction_occurred_at",
            "ix_interaction_next_follow_up",
            "ix_interaction_participant_interaction",
            "ix_interaction_participant_contact",
        ):
            assert expected in indexes, f"missing index {expected}"
    finally:
        db.close()


def test_the_lead_activity_table_is_untouched_by_this_slice() -> None:
    """9D adds a second, different record type. It does not replace, migrate or deprecate
    Slice 2D Lead activities, and whether the two should ever merge is an open question with a
    data migration behind it."""
    db = SessionLocal()
    try:
        exists = db.execute(
            text(
                "SELECT COUNT(*) FROM information_schema.tables "
                "WHERE table_name = 'crm_lead_activity'"
            )
        ).scalar_one()
        assert exists == 1
    finally:
        db.close()
