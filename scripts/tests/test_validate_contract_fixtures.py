"""Tests for scripts/validate_contract_fixtures.py.

Standard library only (unittest), no network and no database. Each test copies the real fixture
pack into a throwaway git repository and then injects one defect, so a rule is proved to fail on
exactly the condition it describes. The repository's own fixtures are never modified.

Run with:

    python -m unittest discover -s scripts/tests -v
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = SCRIPTS_DIR.parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import validate_contract_fixtures as validator  # noqa: E402

FIXTURE_SOURCE = REPO_ROOT / validator.FIXTURE_ROOT
HANDOFF_REL = validator.HANDOFF_DIR


def git_available() -> bool:
    try:
        subprocess.run(["git", "--version"], capture_output=True, check=True)
    except (OSError, subprocess.CalledProcessError):
        return False
    return True


@unittest.skipUnless(git_available(), "git is required: discovery is defined over the git tree")
class FixtureValidatorTestCase(unittest.TestCase):
    """Base class providing a disposable repository seeded with the real fixture pack."""

    def setUp(self) -> None:
        self._tmp = tempfile.mkdtemp(prefix="te2ci-fixtures-")
        self.repo = Path(self._tmp)
        self.addCleanup(shutil.rmtree, self._tmp, ignore_errors=True)
        subprocess.run(["git", "init", "-q"], cwd=self.repo, check=True)

        destination = self.repo / validator.FIXTURE_ROOT
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(FIXTURE_SOURCE, destination)
        subprocess.run(
            ["git", "add", "-A"], cwd=self.repo, check=True, capture_output=True
        )

    def path(self, filename: str) -> Path:
        return self.repo / HANDOFF_REL / filename

    def load(self, filename: str) -> dict:
        return json.loads(self.path(filename).read_text(encoding="utf-8"))

    def save(self, filename: str, data: dict) -> None:
        self.path(filename).write_text(
            json.dumps(data, indent=2) + "\n", encoding="utf-8"
        )

    def run_validator(self) -> tuple[int, list[str], list[str]]:
        return validator.validate_repository(self.repo)

    def assertRule(self, failures: list[str], rule: str) -> None:
        self.assertTrue(
            any(rule in failure for failure in failures),
            f"expected a {rule} failure; got: {failures}",
        )

    def assertPasses(self) -> None:
        exit_code, _info, failures = self.run_validator()
        self.assertEqual(exit_code, 0, f"unexpected failures: {failures}")


class Baseline(FixtureValidatorTestCase):
    def test_unmodified_pack_passes(self) -> None:
        self.assertPasses()

    def test_untracked_non_ignored_fixture_is_inspected(self) -> None:
        """A fixture added in a working branch must be validated before it is committed."""
        new_fixture = self.repo / validator.FIXTURE_ROOT / "proposed" / "new-example.json"
        new_fixture.parent.mkdir(parents=True, exist_ok=True)
        new_fixture.write_text("{ not valid json ,, }", encoding="utf-8")
        # Deliberately not staged.
        exit_code, _info, failures = self.run_validator()
        self.assertEqual(exit_code, 1)
        self.assertRule(failures, "FIX-001")
        self.assertTrue(any("new-example.json" in f for f in failures))

    def test_ignored_fixture_is_not_inspected(self) -> None:
        (self.repo / ".gitignore").write_text("**/scratch/\n", encoding="utf-8")
        scratch = self.repo / validator.FIXTURE_ROOT / "scratch" / "local.json"
        scratch.parent.mkdir(parents=True, exist_ok=True)
        scratch.write_text("{ broken ,, }", encoding="utf-8")
        self.assertPasses()


class MalformedAndMissing(FixtureValidatorTestCase):
    def test_malformed_json_is_reported(self) -> None:
        self.path("work-order-shell-output-example.json").write_text(
            '{ "a": 1,, }', encoding="utf-8"
        )
        exit_code, _info, failures = self.run_validator()
        self.assertEqual(exit_code, 1)
        self.assertRule(failures, "FIX-001")

    def test_missing_frozen_pack_file_is_reported(self) -> None:
        self.path("partial-award-selected-lines-example.json").unlink()
        exit_code, _info, failures = self.run_validator()
        self.assertEqual(exit_code, 1)
        self.assertRule(failures, "HOF-000")


class HandoffInvariants(FixtureValidatorTestCase):
    def test_identity_mismatch_is_reported(self) -> None:
        shell = self.load("work-order-shell-output-example.json")
        shell["linked_commercial_offer_public_id"] = "DEMO-CO-PUBLIC-999"
        self.save("work-order-shell-output-example.json", shell)
        exit_code, _info, failures = self.run_validator()
        self.assertEqual(exit_code, 1)
        self.assertRule(failures, "HOF-001")

    def test_source_line_mismatch_is_reported(self) -> None:
        shell = self.load("work-order-shell-output-example.json")
        shell["work_order_lines"][1]["source_commercial_offer_line_public_id"] = "DEMO-CO-LINE-999"
        self.save("work-order-shell-output-example.json", shell)
        exit_code, _info, failures = self.run_validator()
        self.assertEqual(exit_code, 1)
        self.assertRule(failures, "HOF-012")

    def test_missing_account_traceability_is_reported(self) -> None:
        handoff = self.load("accepted-commercial-offer-handoff-example.json")
        handoff["header"]["account_public_id"] = None
        self.save("accepted-commercial-offer-handoff-example.json", handoff)
        exit_code, _info, failures = self.run_validator()
        self.assertEqual(exit_code, 1)
        self.assertRule(failures, "HOF-006")

    def test_invalid_shell_status_is_reported(self) -> None:
        shell = self.load("work-order-shell-output-example.json")
        shell["work_order_status"] = validator.FORBIDDEN_SHELL_STATUS
        self.save("work-order-shell-output-example.json", shell)
        exit_code, _info, failures = self.run_validator()
        self.assertEqual(exit_code, 1)
        self.assertRule(failures, "HOF-016")

    def test_work_order_line_from_excluded_line_is_reported(self) -> None:
        partial = self.load("partial-award-selected-lines-example.json")
        excluded_id = partial["excluded_lines"][0]["commercial_offer_line_public_id"]
        partial["work_order_shell"]["work_order_lines"][0][
            "source_commercial_offer_line_public_id"
        ] = excluded_id
        self.save("partial-award-selected-lines-example.json", partial)
        exit_code, _info, failures = self.run_validator()
        self.assertEqual(exit_code, 1)
        self.assertRule(failures, "HOF-015")

    def test_selected_line_must_be_awarded(self) -> None:
        partial = self.load("partial-award-selected-lines-example.json")
        partial["available_offer_lines"][0]["line_status"] = "CANCELLED"
        self.save("partial-award-selected-lines-example.json", partial)
        exit_code, _info, failures = self.run_validator()
        self.assertEqual(exit_code, 1)
        self.assertRule(failures, "HOF-014")

    def test_negative_path_weakening_is_reported(self) -> None:
        negative = self.load("negative-invalid-line-selection-example.json")
        negative["expected_rejection"]["partial_silent_success_allowed"] = True
        self.save("negative-invalid-line-selection-example.json", negative)
        exit_code, _info, failures = self.run_validator()
        self.assertEqual(exit_code, 1)
        self.assertRule(failures, "HOF-021")

    def test_missing_account_negative_example_given_an_account(self) -> None:
        negative = self.load("negative-missing-account-traceability-example.json")
        negative["invalid_handoff_request"]["account_public_id"] = "DEMO-ACCOUNT-X"
        self.save("negative-missing-account-traceability-example.json", negative)
        exit_code, _info, failures = self.run_validator()
        self.assertEqual(exit_code, 1)
        self.assertRule(failures, "HOF-017")


class RealDataMarkers(FixtureValidatorTestCase):
    def test_real_shaped_pan_is_reported(self) -> None:
        shell = self.load("work-order-shell-output-example.json")
        shell["work_order_lines"][0]["gstn"] = "ABCDE1234F"
        self.save("work-order-shell-output-example.json", shell)
        exit_code, _info, failures = self.run_validator()
        self.assertEqual(exit_code, 1)
        self.assertRule(failures, "FIX-014")

    def test_non_documentation_url_is_reported(self) -> None:
        handoff = self.load("accepted-commercial-offer-handoff-example.json")
        handoff["documents"][0]["safe_placeholder_url"] = "https://files.contoso.co.in/doc-1"
        self.save("accepted-commercial-offer-handoff-example.json", handoff)
        exit_code, _info, failures = self.run_validator()
        self.assertEqual(exit_code, 1)
        self.assertRule(failures, "FIX-016")

    def test_falsified_safe_demo_declaration_is_reported(self) -> None:
        handoff = self.load("accepted-commercial-offer-handoff-example.json")
        handoff["fixture_metadata"]["contains_real_customer_data"] = True
        self.save("accepted-commercial-offer-handoff-example.json", handoff)
        exit_code, _info, failures = self.run_validator()
        self.assertEqual(exit_code, 1)
        self.assertRule(failures, "FIX-011")

    def test_credential_key_is_reported(self) -> None:
        handoff = self.load("accepted-commercial-offer-handoff-example.json")
        handoff["header"]["api_key"] = "some-value-here"
        self.save("accepted-commercial-offer-handoff-example.json", handoff)
        exit_code, _info, failures = self.run_validator()
        self.assertEqual(exit_code, 1)
        self.assertRule(failures, "FIX-010")


@unittest.skipUnless(git_available(), "git is required")
class RealRepository(unittest.TestCase):
    def test_actual_repository_fixtures_pass(self) -> None:
        exit_code, info, failures = validator.validate_repository(REPO_ROOT)
        self.assertEqual(exit_code, 0, f"unexpected failures: {failures}")
        self.assertTrue(
            any("candidate fixture file(s) checked" in line for line in info),
            f"expected a discovery summary; got: {info}",
        )


if __name__ == "__main__":
    unittest.main()
