"""Tests for scripts/check_tracked_secrets.py.

Standard library only (unittest), no network and no database, so they run anywhere the validator
itself runs. Each test builds a throwaway git repository in a temporary directory, because the
check is defined over git's view of the tree and mocking that away would test nothing.

Run with:

    python -m unittest discover -s scripts/tests -v
"""

from __future__ import annotations

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

import check_tracked_secrets as checker  # noqa: E402

# Sample credentials are assembled from fragments at runtime rather than written as literals.
# This file is itself part of the proposed tree the checker scans, so a whole literal here would
# make the repository fail its own security gate. Splitting the value is the honest fix: the
# alternative -- excluding this path from the scan -- is exactly what the check forbids.
GOOGLE_API_KEY = "AIza" + "SyB1cD3fG7hJ9kL2mN4pQ6rS8tU0vW2xY4z"
AWS_ACCESS_KEY_ID = "AKIA" + "IOSFODNN7EXAMPLE"
SLACK_TOKEN = "xoxb" + "-1234567890-abcdefghijklm"
STRIPE_LIVE_KEY = "sk_" + "live_4eC39HqLyjWDarjtT1zdp7dc"
GITHUB_FINE_GRAINED_PAT = "github" + "_pat_11ABCDEFG0aBcDeFgHiJkL_mNoPqRsTuVwXyZ0123456789abcdefghij"
JSON_WEB_TOKEN = (
    "eyJ" + "hbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJ" + "zdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4ifQ."
    "SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
)
PEM_HEADER = "-----BEGIN OPENSSH " + "PRIVATE KEY-----"
ASSIGNED_SECRET_VALUE = "Zx8Kq2" + "Lm9Pv4Rt7B"
URL_INLINE_SECRET = "Tr0ub4" + "dor3xKq"


def git_available() -> bool:
    try:
        subprocess.run(["git", "--version"], capture_output=True, check=True)
    except (OSError, subprocess.CalledProcessError):
        return False
    return True


@unittest.skipUnless(git_available(), "git is required: the check is defined over the git tree")
class SecretCheckTestCase(unittest.TestCase):
    """Base class providing a disposable git repository."""

    def setUp(self) -> None:
        self._tmp = tempfile.mkdtemp(prefix="te2ci-secret-")
        self.repo = Path(self._tmp)
        self.addCleanup(shutil.rmtree, self._tmp, ignore_errors=True)
        subprocess.run(["git", "init", "-q"], cwd=self.repo, check=True)

    def write(self, relative: str, content: str) -> Path:
        path = self.repo / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def stage(self, *relatives: str, force: bool = False) -> None:
        args = ["git", "add"]
        if force:
            args.append("-f")
        args.extend(relatives)
        subprocess.run(args, cwd=self.repo, check=True, capture_output=True)

    def run_check(self) -> tuple[int, str, list[str]]:
        return checker.check_repository(self.repo)

    def assertRule(self, findings: list[str], rule: str, needle: str = "") -> None:
        matching = [f for f in findings if rule in f and needle in f]
        self.assertTrue(
            matching,
            f"expected a {rule} finding containing {needle!r}; got: {findings}",
        )


class DiscoveryScope(SecretCheckTestCase):
    def test_untracked_non_ignored_file_is_inspected(self) -> None:
        """A new file in a working branch is part of the change and must be checked."""
        self.write("app/new_settings.py", f'API_KEY = "{GOOGLE_API_KEY}"\n')
        # Deliberately not staged.
        exit_code, _summary, findings = self.run_check()
        self.assertEqual(exit_code, 1)
        self.assertRule(findings, "SEC-003", "app/new_settings.py")

    def test_ignored_env_file_is_not_read(self) -> None:
        """A gitignored .env must never enter the candidate set, let alone be opened."""
        self.write(".gitignore", ".env\nnode_modules/\n")
        self.write(".env", f"POSTGRES_PASSWORD={ASSIGNED_SECRET_VALUE}\n")
        self.stage(".gitignore")

        candidates = [p.name for p in checker.discover_candidate_files(self.repo)]
        self.assertNotIn(".env", candidates)

        exit_code, _summary, findings = self.run_check()
        self.assertEqual(exit_code, 0, f"unexpected findings: {findings}")

    def test_ignored_directory_contents_are_excluded(self) -> None:
        self.write(".gitignore", "node_modules/\n")
        self.write("node_modules/pkg/secret.js", f'const apiKey = "{ASSIGNED_SECRET_VALUE}";\n')
        self.stage(".gitignore")

        exit_code, _summary, findings = self.run_check()
        self.assertEqual(exit_code, 0, f"unexpected findings: {findings}")

    def test_committed_files_are_inspected(self) -> None:
        self.write("app/settings.py", f'db_password = "{ASSIGNED_SECRET_VALUE}"\n')
        self.stage("app/settings.py")
        exit_code, _summary, findings = self.run_check()
        self.assertEqual(exit_code, 1)
        self.assertRule(findings, "SEC-004", "app/settings.py")


class ForbiddenPaths(SecretCheckTestCase):
    def test_committed_env_file_is_a_finding(self) -> None:
        """Force-adding .env past .gitignore must still be caught."""
        self.write(".gitignore", ".env\n")
        self.write(".env", f"POSTGRES_PASSWORD={ASSIGNED_SECRET_VALUE}\n")
        self.stage(".gitignore")
        self.stage(".env", force=True)

        exit_code, _summary, findings = self.run_check()
        self.assertEqual(exit_code, 1)
        self.assertRule(findings, "SEC-001", ".env")

    def test_private_key_file_path_is_a_finding(self) -> None:
        self.write("deploy/server.pem", "not-actually-a-key\n")
        exit_code, _summary, findings = self.run_check()
        self.assertEqual(exit_code, 1)
        self.assertRule(findings, "SEC-001", "deploy/server.pem")

    def test_env_example_is_permitted(self) -> None:
        self.write(
            ".env.example",
            "POSTGRES_PASSWORD=ChangeThisStrongPassword123!\nJWT_SECRET=change-this-in-real-use\n",
        )
        exit_code, _summary, findings = self.run_check()
        self.assertEqual(exit_code, 0, f"unexpected findings: {findings}")


class ContentRules(SecretCheckTestCase):
    def test_pem_private_key_block(self) -> None:
        self.write("app/key.txt", f"{PEM_HEADER}\nabc\n")
        exit_code, _summary, findings = self.run_check()
        self.assertEqual(exit_code, 1)
        self.assertRule(findings, "SEC-002", "app/key.txt")

    def test_issued_tokens_are_detected(self) -> None:
        cases = {
            "aws.txt": AWS_ACCESS_KEY_ID,
            "slack.txt": SLACK_TOKEN,
            "stripe.txt": STRIPE_LIVE_KEY,
        }
        for name, token in cases.items():
            self.write(name, f"value = {token}\n")
        exit_code, _summary, findings = self.run_check()
        self.assertEqual(exit_code, 1)
        for name in cases:
            with self.subTest(name=name):
                self.assertRule(findings, "SEC-003", name)

    def test_github_fine_grained_pat_is_detected(self) -> None:
        """Modern github_pat_ tokens are not matched by the classic gh*_ pattern."""
        self.write("ci/notes.md", f"token: {GITHUB_FINE_GRAINED_PAT}\n")

        exit_code, _summary, findings = self.run_check()
        self.assertEqual(exit_code, 1)
        self.assertRule(findings, "SEC-003", "ci/notes.md")
        self.assertTrue(
            any("GitHub fine-grained token" in f for f in findings),
            f"expected the fine-grained token label; got: {findings}",
        )

    def test_jwt_is_detected(self) -> None:
        self.write("app/token.txt", f"auth = {JSON_WEB_TOKEN}\n")
        exit_code, _summary, findings = self.run_check()
        self.assertEqual(exit_code, 1)
        self.assertRule(findings, "SEC-003", "app/token.txt")

    def test_credential_assignment_quoted_and_env_forms(self) -> None:
        self.write("app/settings.py", f'db_password = "{ASSIGNED_SECRET_VALUE}"\n')
        self.write("config/service.env", f"SERVICE_API_KEY={ASSIGNED_SECRET_VALUE}\n")
        exit_code, _summary, findings = self.run_check()
        self.assertEqual(exit_code, 1)
        self.assertRule(findings, "SEC-004", "app/settings.py")
        self.assertRule(findings, "SEC-004", "config/service.env")

    def test_inline_url_credential(self) -> None:
        self.write(
            "deploy.sh",
            f"DATABASE_URL=postgresql://svc:{URL_INLINE_SECRET}@prod-db.internal:5432/app\n",
        )
        exit_code, _summary, findings = self.run_check()
        self.assertEqual(exit_code, 1)
        self.assertRule(findings, "SEC-005", "deploy.sh")


class ValueWithholding(SecretCheckTestCase):
    def test_matched_values_are_never_echoed(self) -> None:
        """A finding must not copy the credential into the log or artifact."""
        self.write("a.py", f'API_KEY = "{GOOGLE_API_KEY}"\n')
        self.write("b.py", f'db_password = "{ASSIGNED_SECRET_VALUE}"\n')
        self.write("c.sh", f"DATABASE_URL=postgresql://svc:{URL_INLINE_SECRET}@host:5432/app\n")
        self.write("d.md", f"token: {GITHUB_FINE_GRAINED_PAT}\n")

        exit_code, summary, findings = self.run_check()
        self.assertEqual(exit_code, 1)

        haystack = summary + "\n".join(findings)
        for secret in (
            GOOGLE_API_KEY,
            ASSIGNED_SECRET_VALUE,
            URL_INLINE_SECRET,
            GITHUB_FINE_GRAINED_PAT,
        ):
            self.assertNotIn(secret, haystack, "a finding leaked the credential value")
        self.assertIn("value withheld", haystack)


class AcceptedValues(SecretCheckTestCase):
    def test_placeholders_are_accepted(self) -> None:
        self.write(
            ".env.example",
            "POSTGRES_PASSWORD=ChangeThisStrongPassword123!\n"
            "JWT_SECRET=change-this-in-real-use\n"
            "API_KEY=your-key-here\n"
            "CLIENT_SECRET=${CLIENT_SECRET}\n",
        )
        self.write("docs/example.md", 'password: "<your-password>"\n')
        exit_code, _summary, findings = self.run_check()
        self.assertEqual(exit_code, 0, f"unexpected findings: {findings}")

    def test_documented_seed_credential_is_accepted(self) -> None:
        """The prototype seed password is public, documented and not a real credential."""
        self.write(
            "e2e/tests/fixtures/auth.ts",
            'export async function login(page, username, password = "password") {}\n',
        )
        exit_code, _summary, findings = self.run_check()
        self.assertEqual(exit_code, 0, f"unexpected findings: {findings}")

    def test_negative_test_literals_and_code_references_are_accepted(self) -> None:
        self.write("tests/test_auth.py", 'json={"username": "admin1", "password": "wrong-password"}\n')
        self.write(
            "app/database.py",
            "    return URL.create(\n        password=settings.postgres_password,\n    )\n",
        )
        self.write("app/security.py", 'PASSWORD_ALGORITHM = "pbkdf2_sha256"\nPASSWORD_ITERATIONS = 240000\n')
        exit_code, _summary, findings = self.run_check()
        self.assertEqual(exit_code, 0, f"unexpected findings: {findings}")


@unittest.skipUnless(git_available(), "git is required")
class RealRepository(unittest.TestCase):
    def test_actual_repository_has_no_findings(self) -> None:
        exit_code, summary, findings = checker.check_repository(REPO_ROOT)
        self.assertEqual(exit_code, 0, f"unexpected findings: {findings}")
        self.assertIn("proposed tree", summary)


if __name__ == "__main__":
    unittest.main()
