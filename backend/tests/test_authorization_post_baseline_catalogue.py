"""Post-baseline permission catalogue - the mechanism, without any post-baseline permission.

PF-1A-E1's `ROLE_PERMISSION_COMPATIBILITY_MATRIX` is frozen evidence: it is compared against
`tests/fixtures/pf_1a_e1_baseline_authorization.py`, a fixture derived independently from the
pre-E1 commit, and that independence is the entire proof. Adding a post-E1 permission to it would
make the comparison vacuous from that point on - the proof would be checking a moved goalpost
against itself.

But `require_permission()` rejects any code absent from `ALL_PERMISSION_CODES`, which derived
from that same frozen matrix. So no package could add a permission without damaging E1's evidence.

This package resolves that with a disjoint union:

    ROLE_PERMISSION_COMPATIBILITY_MATRIX   frozen; 31 permissions / 110 grants; never gains an entry
    POST_BASELINE_ROLE_PERMISSION_MATRIX   live; empty here; grows as packages add permissions
    EFFECTIVE_ROLE_PERMISSION_MATRIX       the union; what require_permission actually enforces

`POST_BASELINE_ROLE_PERMISSION_MATRIX` is deliberately **empty** in this package. Nothing about
the enforced access matrix changes here: `EFFECTIVE` equals the baseline exactly, so this is a
pure mechanism change with zero behavioural effect, reviewable as such. Slice 9D adds the first
real entries.
"""

from __future__ import annotations

import pytest

from app.modules.authorization.contract import (
    ALL_PERMISSION_CODES,
    EFFECTIVE_ROLE_PERMISSION_MATRIX,
    KNOWN_ROLE_CODES,
    PERMISSION_DESCRIPTIONS,
    POST_BASELINE_ROLE_PERMISSION_MATRIX,
    ROLE_PERMISSION_COMPATIBILITY_MATRIX,
    assert_permission_matrices_are_disjoint,
)


# ===========================================================================
# The frozen baseline stays frozen
# ===========================================================================


def test_the_pf_1a_e1_baseline_matrix_is_untouched() -> None:
    """31 permissions and 110 grants, unchanged. This is the whole reason for the split."""
    assert len(ROLE_PERMISSION_COMPATIBILITY_MATRIX) == 31
    grants = sum(len(roles) for roles in ROLE_PERMISSION_COMPATIBILITY_MATRIX.values())
    assert grants == 110


def test_the_baseline_gains_nothing_when_a_package_adds_permissions() -> None:
    """The mechanism's central promise, asserted from the other side.

    In the prerequisite package the post-baseline half was empty and the effective matrix
    equalled the baseline exactly. Slice 9D adds the first five entries, so the effective matrix
    is now larger - but every code it added must be in the post-baseline half and **none** in
    the frozen one. This is the assertion that would catch a future package adding to the wrong
    matrix, which is the one thing the split exists to prevent.
    """
    added = set(EFFECTIVE_ROLE_PERMISSION_MATRIX) - set(ROLE_PERMISSION_COMPATIBILITY_MATRIX)
    assert added == set(POST_BASELINE_ROLE_PERMISSION_MATRIX)
    assert added, "no post-baseline permission is declared; this test has stopped proving anything"

    for code in added:
        assert code not in ROLE_PERMISSION_COMPATIBILITY_MATRIX

    assert set(ALL_PERMISSION_CODES) == set(ROLE_PERMISSION_COMPATIBILITY_MATRIX) | added


# ===========================================================================
# The union is calculated, never hardcoded
# ===========================================================================


def test_the_effective_matrix_is_the_calculated_union_of_the_two_halves() -> None:
    """Deliberately calculated. A future package adding a permission should not have to edit a
    total here, and a total that must be hand-edited is one that stops being checked."""
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
    assert sum(len(roles) for roles in EFFECTIVE_ROLE_PERMISSION_MATRIX.values()) == expected_grants


def test_the_effective_matrix_preserves_every_baseline_grant_set_exactly() -> None:
    """The union must not shadow, widen or narrow a baseline entry."""
    for permission_code, role_codes in ROLE_PERMISSION_COMPATIBILITY_MATRIX.items():
        assert EFFECTIVE_ROLE_PERMISSION_MATRIX[permission_code] == role_codes


def test_all_permission_codes_derives_from_the_effective_matrix() -> None:
    assert set(ALL_PERMISSION_CODES) == set(EFFECTIVE_ROLE_PERMISSION_MATRIX)
    assert len(ALL_PERMISSION_CODES) == len(EFFECTIVE_ROLE_PERMISSION_MATRIX)


def test_every_effective_permission_is_described_and_names_known_roles() -> None:
    assert set(PERMISSION_DESCRIPTIONS) == set(EFFECTIVE_ROLE_PERMISSION_MATRIX)
    for permission_code, role_codes in EFFECTIVE_ROLE_PERMISSION_MATRIX.items():
        unknown = set(role_codes) - set(KNOWN_ROLE_CODES)
        assert unknown == set(), f"{permission_code} grants unknown role(s) {sorted(unknown)}"


# ===========================================================================
# The disjointness guard, driven with synthetic bad input
# ===========================================================================


def test_the_disjointness_guard_accepts_genuinely_disjoint_matrices() -> None:
    assert_permission_matrices_are_disjoint({"A": ("ADMIN",)}, {"B": ("ADMIN",)})


def test_the_disjointness_guard_rejects_an_overlapping_code() -> None:
    """The failure this guard exists for: a code in both halves, where dict merging would let
    the post-baseline entry silently shadow the frozen baseline one - corrupting E1's evidence
    while every count still looked plausible."""
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
    `contract` must fail - so the call site must exist in the module source, not just the
    function."""
    from pathlib import Path

    from app.modules.authorization import contract as contract_module

    assert_permission_matrices_are_disjoint(
        ROLE_PERMISSION_COMPATIBILITY_MATRIX, POST_BASELINE_ROLE_PERMISSION_MATRIX
    )

    source = Path(contract_module.__file__).read_text(encoding="utf-8")
    assert (
        "assert_permission_matrices_are_disjoint(\n    ROLE_PERMISSION_COMPATIBILITY_MATRIX" in source
    ), "the disjointness guard is defined but no longer invoked at module import time"
