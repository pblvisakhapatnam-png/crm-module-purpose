"""PF-1A-E1 C1-01 correction: independent baseline-equivalence proof.

`test_authorization_compatibility_matrix.py` proves that the candidate runtime
`ROLE_PERMISSION_COMPATIBILITY_MATRIX` and the candidate migration-seeded database agree
with EACH OTHER. That is necessary but not sufficient: a mistake copied consistently into
both `contract.py` and the seed migration would still pass that check.

This file proves something the other file cannot: that BOTH the candidate contract and the
candidate seeded database independently match `tests.fixtures.pf_1a_e1_baseline_authorization`,
a snapshot derived directly from the pre-PF-1A-E1 baseline commit
(`3c69355858ab352e246a8775f8a463ca7c9c15be`) rather than from any candidate source. See that
fixture module's docstring for exactly how it was derived and how to independently
re-verify it.

Neither proof below imports its expected value from `app.modules.authorization.contract`.
"""

from __future__ import annotations

from app.core.database import SessionLocal
from app.modules.authorization.contract import (
    POST_BASELINE_ROLE_PERMISSION_MATRIX,
    ROLE_PERMISSION_COMPATIBILITY_MATRIX,
)
from app.modules.authorization.repository import list_role_permission_matrix
from app.modules.authorization.service import has_permission
from tests.fixtures.pf_1a_e1_baseline_authorization import (
    BASELINE_COMMIT,
    BASELINE_PERMISSION_ROLE_MATRIX,
    BASELINE_ROLE_CODES,
)


def test_baseline_snapshot_has_the_expected_shape() -> None:
    """Sanity-check the fixture itself before trusting it as ground truth."""
    assert BASELINE_COMMIT == "3c69355858ab352e246a8775f8a463ca7c9c15be"
    assert len(BASELINE_ROLE_CODES) == 6
    assert len(BASELINE_PERMISSION_ROLE_MATRIX) == 31
    assert len(BASELINE_ROLE_CODES) * len(BASELINE_PERMISSION_ROLE_MATRIX) == 186


def test_runtime_contract_matrix_exactly_matches_the_baseline_snapshot() -> None:
    """PROOF A: the candidate `ROLE_PERMISSION_COMPATIBILITY_MATRIX` (contract.py) exactly
    matches the independently baseline-derived snapshot - same 31 permission codes, and for
    each one, the exact same set of granted roles. Covers both directions: a role missing
    from the candidate that the baseline granted, and a role the candidate grants that the
    baseline did not.
    """
    candidate_codes = set(ROLE_PERMISSION_COMPATIBILITY_MATRIX.keys())
    baseline_codes = set(BASELINE_PERMISSION_ROLE_MATRIX.keys())

    missing_from_candidate = baseline_codes - candidate_codes
    extra_in_candidate = candidate_codes - baseline_codes
    assert missing_from_candidate == set(), f"permission code(s) dropped from contract.py: {missing_from_candidate}"
    assert extra_in_candidate == set(), f"permission code(s) added to contract.py without baseline evidence: {extra_in_candidate}"

    mismatches: list[str] = []
    for permission_code, baseline_roles in BASELINE_PERMISSION_ROLE_MATRIX.items():
        candidate_roles = set(ROLE_PERMISSION_COMPATIBILITY_MATRIX[permission_code])
        expected_roles = set(baseline_roles)
        if candidate_roles != expected_roles:
            widened = candidate_roles - expected_roles
            narrowed = expected_roles - candidate_roles
            mismatches.append(
                f"{permission_code}: widened={sorted(widened)} narrowed={sorted(narrowed)}"
            )

    assert mismatches == [], "contract.py diverges from the baseline snapshot: " + "; ".join(mismatches)


def test_seeded_database_exactly_matches_the_baseline_snapshot() -> None:
    """PROOF B: the migration-seeded `authz_role_permission` / `authz_permission` database
    exactly matches the independently baseline-derived snapshot, for all 186 cells, checked
    directly through `has_permission(...)` (never through the candidate contract module as
    the expected value).
    """
    db = SessionLocal()
    try:
        mismatches: list[str] = []
        for permission_code, baseline_roles in BASELINE_PERMISSION_ROLE_MATRIX.items():
            expected_roles = set(baseline_roles)
            for role_code in BASELINE_ROLE_CODES:
                expected = role_code in expected_roles
                actual = has_permission(db, [role_code], permission_code)
                if actual != expected:
                    mismatches.append(f"{permission_code} / {role_code}: expected={expected} actual={actual}")

        assert mismatches == [], "seeded database diverges from the baseline snapshot: " + "; ".join(mismatches)
    finally:
        db.close()


def test_seeded_database_grants_no_permission_the_baseline_snapshot_does_not_grant() -> None:
    """Inverse/no-extra-grant proof for PROOF B: the seeded database must not grant a role a
    permission the baseline snapshot did not, **for every permission the baseline snapshot
    actually knows about**. A stray/duplicate seed row, or a seed row for the wrong role,
    would surface here even if every cell the baseline snapshot names happens to be correct.

    Scope note (Slice 9D). Permissions added after PF-1A-E1 are legitimately absent from the
    baseline snapshot, so this test can no longer treat every unknown code as corruption - that
    would make it assert "no package may ever add a permission", which is a different and wrong
    claim. It is narrowed to baseline codes.

    The narrowing classifies rather than skips. A code absent from the baseline must be present
    in `POST_BASELINE_ROLE_PERMISSION_MATRIX` to be excused; a grant for a code in *neither* is
    still an offender, because that is a genuinely unexplained row - exactly what this test
    exists to catch. A silent `continue` here would reintroduce the vacuous-pass failure mode
    Slice 9B spent three correction rounds removing.
    """
    db = SessionLocal()
    try:
        db_matrix = list_role_permission_matrix(db)
        offenders: list[str] = []
        excused_post_baseline = 0
        for role_code, granted_codes in db_matrix.items():
            if role_code not in BASELINE_ROLE_CODES:
                # A grant to a role code the baseline snapshot has never heard of is its own
                # defect, reported below rather than silently skipped.
                for permission_code in granted_codes:
                    offenders.append(f"{role_code} (unknown baseline role) -> {permission_code}")
                continue
            for permission_code in granted_codes:
                expected_roles = BASELINE_PERMISSION_ROLE_MATRIX.get(permission_code)
                if expected_roles is None:
                    post_baseline_roles = POST_BASELINE_ROLE_PERMISSION_MATRIX.get(permission_code)
                    if post_baseline_roles is None:
                        offenders.append(
                            f"{role_code} -> {permission_code} (in neither the baseline snapshot "
                            "nor POST_BASELINE_ROLE_PERMISSION_MATRIX)"
                        )
                    elif role_code not in post_baseline_roles:
                        offenders.append(
                            f"{role_code} -> {permission_code} (post-baseline matrix does not "
                            "grant this role)"
                        )
                    else:
                        excused_post_baseline += 1
                elif role_code not in expected_roles:
                    offenders.append(f"{role_code} -> {permission_code} (baseline snapshot does not grant this)")

        assert offenders == [], "database grants beyond the baseline snapshot: " + "; ".join(offenders)

        # The excusal path must be the one actually taken for post-baseline grants, and it must
        # account for all of them. If this drifts, the loop above is excusing rows for the wrong
        # reason - or silently examining nothing.
        expected_post_baseline_grants = sum(
            len(role_codes) for role_codes in POST_BASELINE_ROLE_PERMISSION_MATRIX.values()
        )
        assert excused_post_baseline == expected_post_baseline_grants, (
            f"excused {excused_post_baseline} post-baseline grant(s) but "
            f"POST_BASELINE_ROLE_PERMISSION_MATRIX declares {expected_post_baseline_grants}"
        )
    finally:
        db.close()


def test_admin_does_not_hold_account_tax_verify_at_baseline_or_in_the_candidate() -> None:
    """A concrete, independently-sourced negative example, matching the pre-existing
    `ACCOUNT_TAX_VERIFICATION_ROLES = ("FINANCE_USER",)` baseline in-body check: the
    baseline snapshot, the candidate contract and the seeded database must all agree that
    ADMIN does not hold ACCOUNT_TAX_VERIFY.
    """
    assert "ADMIN" not in BASELINE_PERMISSION_ROLE_MATRIX["ACCOUNT_TAX_VERIFY"]
    assert "ADMIN" not in ROLE_PERMISSION_COMPATIBILITY_MATRIX["ACCOUNT_TAX_VERIFY"]

    db = SessionLocal()
    try:
        assert has_permission(db, ["ADMIN"], "ACCOUNT_TAX_VERIFY") is False
        assert has_permission(db, ["FINANCE_USER"], "ACCOUNT_TAX_VERIFY") is True
    finally:
        db.close()
