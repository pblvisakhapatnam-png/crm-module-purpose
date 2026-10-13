"""Focused tests for scripts/ci-compose-cleanup.sh (correction TE-2CI.2-C1).

The script's whole job is to issue a precise, label-scoped sequence of Docker commands, so
these tests assert on exactly that: which commands are issued, in which order, with which
arguments, and what the exit code is. A fake `docker` is placed first on PATH and records
every invocation, which keeps the tests hermetic -- no Docker daemon, no containers, no
network, and nothing that could touch a real Compose project.

Standard library only, matching the other two validator suites.

Bash selection: the script under test is bash, and on Windows `shutil.which("bash")` usually
finds C:\\Windows\\System32\\bash.exe, the WSL launcher, which cannot open a Windows path such as
D:\\dev\\... . Each candidate is therefore probed by running the real script and checking it
behaves as documented, so an unusable bash is passed over rather than producing a suite of
unrelated failures. Set CI_COMPOSE_CLEANUP_TEST_BASH to force a particular executable. The suite
skips only when no candidate works.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CLEANUP_SCRIPT = REPO_ROOT / "scripts" / "ci-compose-cleanup.sh"

CI_PROJECT = "pbl-crm-hiring-ci-31865333180"
LOCAL_PROJECT = "pbl-crm-hiring"
PROJECT_LABEL = f"com.docker.compose.project={CI_PROJECT}"

# The exact teardown command. `--profile e2e` is load-bearing (correction TE-2CI.2-C2): `down -v`
# removes named volumes only for services in scope, and the `e2e` service is profile-gated, so
# without it the `e2e-node-modules` volume survives teardown.
EXPECTED_DOWN_CALL = "compose --profile e2e down -v --remove-orphans"


def _bash_can_run_the_script(candidate: str) -> bool:
    """True only if this bash can actually execute the script at its real path.

    `shutil.which("bash")` on Windows commonly resolves to C:\\Windows\\System32\\bash.exe, the
    WSL launcher, which cannot open a Windows path such as D:\\dev\\... . It exists and starts,
    so a mere existence check passes and every test then fails for an unrelated reason. Probing
    with the actual script and asserting the documented rejection behaviour is the only check
    that reflects how the tests use it.
    """
    try:
        result = subprocess.run(
            [candidate, str(CLEANUP_SCRIPT), "definitely-not-a-ci-project"],
            capture_output=True,
            text=True,
            timeout=60,
            env={**os.environ, "GITHUB_ACTIONS": "true"},
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return result.returncode == 2 and "refusing to act" in result.stderr


def _select_bash() -> str | None:
    """Pick a usable bash: explicit override first, then PATH, then known Git Bash locations."""
    candidates = []

    override = os.environ.get("CI_COMPOSE_CLEANUP_TEST_BASH")
    if override:
        candidates.append(override)

    on_path = shutil.which("bash")
    if on_path:
        candidates.append(on_path)

    # Git for Windows ships bash but does not put it on PATH for every shell.
    git_exe = shutil.which("git")
    if git_exe:
        git_root = Path(git_exe).resolve().parent.parent
        candidates.extend(str(git_root / sub / "bash.exe") for sub in ("bin", "usr/bin"))
    candidates.extend(
        [
            r"C:\Program Files\Git\bin\bash.exe",
            r"C:\Program Files\Git\usr\bin\bash.exe",
        ]
    )

    seen = set()
    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        if _bash_can_run_the_script(candidate):
            return candidate
    return None


BASH = _select_bash()

# A fake `docker` that records every invocation and answers from files on disk, so a test can
# describe the "before" state and then assert on what the script did about it.
#
#   containers / networks / volumes  one id per line; an empty file means "none"
#   stubborn_containers              `docker rm` does not actually remove them
#   stubborn_networks                `docker compose down` does not remove the network
#   stubborn_volumes                 `docker compose down` does not remove the volume
#   settle_networks_after            the network clears itself after this many `network ls
#                                     --quiet` queries -- models a resource the daemon is still
#                                     auto-removing, which the verification loop's bounded
#                                     re-check exists to tell apart from one that is truly stuck
#   profile_gated_volumes            `docker compose down -v` clears volumes only when the `e2e`
#                                     profile is active -- models real Compose behaviour, where
#                                     `down -v` removes named volumes only for services in scope
#                                     and a profile-gated service is out of scope unless its
#                                     profile is named
#
FAKE_DOCKER = """#!/bin/sh
dir="$FAKE_DOCKER_DIR"
printf '%s\\n' "$*" >> "$dir/calls.log"

has_quiet() {
  for arg in "$@"; do
    if [ "$arg" = "--quiet" ]; then
      return 0
    fi
  done
  return 1
}

# True only for an actual `--profile e2e` pair, so `--profile something-else` does not pass.
has_e2e_profile() {
  prev=""
  for arg in "$@"; do
    if [ "$prev" = "--profile" ] && [ "$arg" = "e2e" ]; then
      return 0
    fi
    prev="$arg"
  done
  return 1
}

cmd="$1"
shift

case "$cmd" in
  ps)
    if has_quiet "$@"; then cat "$dir/containers"; else sed 's/^/  /' "$dir/containers"; fi
    ;;
  network)
    shift
    if has_quiet "$@"; then
      if [ -f "$dir/settle_networks_after" ]; then
        count_file="$dir/network_query_count"
        count=0
        [ -f "$count_file" ] && count=$(cat "$count_file")
        count=$((count + 1))
        echo "$count" > "$count_file"
        threshold=$(cat "$dir/settle_networks_after")
        if [ "$count" -ge "$threshold" ]; then
          : > "$dir/networks"
        fi
      fi
      cat "$dir/networks"
    else
      sed 's/^/  /' "$dir/networks"
    fi
    ;;
  volume)
    shift
    if has_quiet "$@"; then cat "$dir/volumes"; else sed 's/^/  /' "$dir/volumes"; fi
    ;;
  rm)
    if [ ! -f "$dir/stubborn_containers" ]; then
      : > "$dir/containers"
    fi
    if [ -f "$dir/rm_errors" ]; then
      echo "Error response from daemon: No such container" >&2
      exit 1
    fi
    ;;
  compose)
    if [ ! -f "$dir/stubborn_networks" ]; then
      : > "$dir/networks"
    fi
    if [ ! -f "$dir/stubborn_containers" ]; then
      : > "$dir/containers"
    fi
    if [ ! -f "$dir/stubborn_volumes" ]; then
      if [ -f "$dir/profile_gated_volumes" ]; then
        # Out of scope without the profile, exactly as the real `e2e` service's
        # `e2e-node-modules` volume was on hosted run 31871165805.
        if has_e2e_profile "$@"; then
          : > "$dir/volumes"
        fi
      else
        : > "$dir/volumes"
      fi
    fi
    ;;
  *)
    echo "fake docker: unexpected command '$cmd'" >&2
    exit 99
    ;;
esac
"""


@unittest.skipUnless(BASH, "bash is required to run the cleanup script under test")
class CiComposeCleanupTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.state = Path(self._tmp.name)

        bin_dir = self.state / "bin"
        bin_dir.mkdir()
        fake = bin_dir / "docker"
        fake.write_text(FAKE_DOCKER, encoding="utf-8", newline="\n")
        fake.chmod(0o755)
        self.bin_dir = bin_dir

        for name in ("containers", "networks", "volumes", "calls.log"):
            (self.state / name).write_text("", encoding="utf-8", newline="\n")

    def given(self, *, containers=(), networks=(), volumes=()) -> None:
        def write(name: str, values) -> None:
            text = "".join(f"{value}\n" for value in values)
            (self.state / name).write_text(text, encoding="utf-8", newline="\n")

        write("containers", containers)
        write("networks", networks)
        write("volumes", volumes)

    def run_cleanup(
        self,
        project: str | None = CI_PROJECT,
        github_actions: str | None = "true",
    ) -> subprocess.CompletedProcess:
        env = dict(os.environ)
        env["PATH"] = f"{self.bin_dir}{os.pathsep}{env.get('PATH', '')}"
        env["FAKE_DOCKER_DIR"] = str(self.state)
        if github_actions is None:
            env.pop("GITHUB_ACTIONS", None)
        else:
            env["GITHUB_ACTIONS"] = github_actions
        # The verification loop's re-check interval defaults to 5s in production. Zero here keeps
        # every test -- including the ones that exhaust all 6 attempts -- fast and deterministic;
        # the loop's attempt count and behaviour are otherwise unchanged.
        env["CI_COMPOSE_CLEANUP_POLL_SECONDS"] = "0"
        argv = [BASH, str(CLEANUP_SCRIPT)]
        if project is not None:
            argv.append(project)
        return subprocess.run(argv, capture_output=True, text=True, env=env, timeout=120)

    @property
    def calls(self) -> list[str]:
        text = (self.state / "calls.log").read_text(encoding="utf-8")
        return [line for line in text.splitlines() if line.strip()]

    # -- fail-closed scope ------------------------------------------------------------

    def test_refuses_to_run_without_a_project_name(self) -> None:
        result = self.run_cleanup(project=None)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(self.calls, [], "Docker must not be touched when the input is rejected")

    def test_refuses_the_local_development_project(self) -> None:
        """The guard that stops this script ever removing a developer's stack or volumes."""
        result = self.run_cleanup(project=LOCAL_PROJECT)
        self.assertEqual(result.returncode, 2)
        self.assertIn("refusing to act", result.stderr)
        self.assertEqual(self.calls, [], "Docker must not be touched for an out-of-scope project")

    def test_refuses_a_project_that_merely_contains_the_ci_marker(self) -> None:
        result = self.run_cleanup(project="not-pbl-crm-hiring-ci-1")
        self.assertEqual(result.returncode, 2)
        self.assertEqual(self.calls, [])

    def test_refuses_a_malformed_project_name(self) -> None:
        result = self.run_cleanup(project="pbl-crm-hiring-ci-Bad Name")
        self.assertEqual(result.returncode, 2)
        self.assertEqual(self.calls, [])

    def test_refuses_the_bare_prefix(self) -> None:
        """A prefix match alone accepted this and went on to issue Docker commands."""
        result = self.run_cleanup(project="pbl-crm-hiring-ci-")
        self.assertEqual(result.returncode, 2)
        self.assertEqual(self.calls, [])

    def test_refuses_a_non_numeric_run_id(self) -> None:
        result = self.run_cleanup(project="pbl-crm-hiring-ci-test-4242")
        self.assertEqual(result.returncode, 2)
        self.assertEqual(self.calls, [])

    def test_refuses_a_trailing_attempt_suffix(self) -> None:
        """The project name is run-id only; an attempt suffix is no longer a valid shape."""
        result = self.run_cleanup(project="pbl-crm-hiring-ci-31865333180-2")
        self.assertEqual(result.returncode, 2)
        self.assertEqual(self.calls, [])

    def test_refuses_to_run_outside_github_actions(self) -> None:
        result = self.run_cleanup(github_actions=None)
        self.assertEqual(result.returncode, 2)
        self.assertIn("refusing to run outside GitHub Actions", result.stderr)
        self.assertEqual(self.calls, [])

    def test_refuses_when_github_actions_is_not_true(self) -> None:
        result = self.run_cleanup(github_actions="false")
        self.assertEqual(result.returncode, 2)
        self.assertEqual(self.calls, [])

    # -- cleanup behaviour ------------------------------------------------------------

    def test_removes_labelled_containers_then_tears_the_project_down(self) -> None:
        self.given(containers=["aaa111", "bbb222"], networks=["net1"], volumes=["vol1"])

        result = self.run_cleanup()
        self.assertEqual(result.returncode, 0, result.stderr)

        rm_calls = [call for call in self.calls if call.startswith("rm ")]
        self.assertEqual(len(rm_calls), 1)
        self.assertEqual(rm_calls[0], "rm --force --volumes aaa111 bbb222")

        down_calls = [call for call in self.calls if call.startswith("compose ")]
        self.assertEqual(down_calls, [EXPECTED_DOWN_CALL])

        # Ordering is the entire point of correction C1: the one-off container has to be gone
        # before `down` runs, or the network stays attached.
        self.assertLess(self.calls.index(rm_calls[0]), self.calls.index(down_calls[0]))

    def test_teardown_activates_the_e2e_profile_so_its_volume_is_in_scope(self) -> None:
        """Correction TE-2CI.2-C2, from hosted run 31871165805.

        The `e2e` service is gated behind the Compose `e2e` profile, and `down -v` removes named
        volumes only for services in scope. Teardown without the profile therefore left
        `pbl-crm-hiring-ci-31871165805_e2e-node-modules` behind, and verification correctly failed
        the job.

        `profile_gated_volumes` makes the fake `docker compose down` behave the same way, so this
        is a behavioural test, not a string check: drop `--profile e2e` from the script and the
        volume survives, verification reports residue and this test fails on the exit code.
        """
        (self.state / "profile_gated_volumes").write_text("", encoding="utf-8", newline="\n")
        self.given(
            containers=[],
            networks=[],
            volumes=[f"{CI_PROJECT}_e2e-node-modules", f"{CI_PROJECT}_postgres-data"],
        )

        result = self.run_cleanup()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            [call for call in self.calls if call.startswith("compose ")], [EXPECTED_DOWN_CALL]
        )
        self.assertIn("no container, network or volume remains", result.stdout)

    def test_the_profile_gate_in_the_fake_docker_actually_gates(self) -> None:
        """Guards the test above from passing vacuously.

        If `profile_gated_volumes` did not really withhold removal, the test above would pass
        whether or not the script named the profile, and would prove nothing. This drives the fake
        directly: without the profile the volume must survive, with it the volume must go.
        """
        (self.state / "profile_gated_volumes").write_text("", encoding="utf-8", newline="\n")
        self.given(containers=[], networks=[], volumes=[f"{CI_PROJECT}_e2e-node-modules"])

        env = dict(os.environ)
        env["FAKE_DOCKER_DIR"] = str(self.state)
        docker = str(self.bin_dir / "docker")

        subprocess.run(
            [BASH, docker, "compose", "down", "-v", "--remove-orphans"], env=env, timeout=60
        )
        self.assertTrue(
            (self.state / "volumes").read_text(encoding="utf-8").strip(),
            "a profile-gated volume must survive a teardown that does not name the profile",
        )

        subprocess.run(
            [BASH, docker, "compose", "--profile", "e2e", "down", "-v", "--remove-orphans"],
            env=env,
            timeout=60,
        )
        self.assertEqual(
            (self.state / "volumes").read_text(encoding="utf-8").strip(),
            "",
            "naming the profile must bring the volume into scope and remove it",
        )

    def test_never_invokes_removal_with_an_empty_argument_list(self) -> None:
        self.given(containers=[], networks=["net1"], volumes=[])

        result = self.run_cleanup()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual([call for call in self.calls if call.startswith("rm ")], [])
        self.assertIn(EXPECTED_DOWN_CALL, self.calls)

    def test_tolerates_a_container_vanishing_between_discovery_and_removal(self) -> None:
        """The `--rm` race: `docker rm` fails for a container that already removed itself.

        Under `set -e` that aborted the script before teardown and before verification. Cleanup
        must continue and let the final verification decide.
        """
        (self.state / "rm_errors").write_text("", encoding="utf-8", newline="\n")
        self.given(containers=["aaa111"], networks=["net1"], volumes=["vol1"])

        result = self.run_cleanup()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(EXPECTED_DOWN_CALL, self.calls)
        self.assertIn("Continuing; final verification decides", result.stderr)

    def test_a_failed_removal_that_leaves_residue_still_fails(self) -> None:
        """Tolerating the race must not become tolerating a genuine failure."""
        (self.state / "rm_errors").write_text("", encoding="utf-8", newline="\n")
        (self.state / "stubborn_containers").write_text("", encoding="utf-8", newline="\n")
        self.given(containers=["aaa111"], networks=[], volumes=[])

        result = self.run_cleanup()
        self.assertEqual(result.returncode, 1)
        self.assertIn("residual containers", result.stderr)

    def test_every_docker_query_is_scoped_to_the_exact_project_label(self) -> None:
        self.given(containers=["aaa111"], networks=["net1"], volumes=["vol1"])
        self.run_cleanup()

        queries = [
            call
            for call in self.calls
            if call.startswith(("ps ", "network ls", "volume ls"))
        ]
        self.assertTrue(queries)
        for call in queries:
            self.assertIn(f"--filter label={PROJECT_LABEL}", call)

    def test_never_prunes_globally(self) -> None:
        self.given(containers=["aaa111"], networks=["net1"], volumes=["vol1"])
        self.run_cleanup()

        for call in self.calls:
            self.assertNotIn("prune", call)
            self.assertNotIn("system", call)

    # -- verification -----------------------------------------------------------------

    def test_fails_when_a_network_survives_teardown(self) -> None:
        """Genuinely stuck residue -- exhausts every re-check attempt and still fails."""
        (self.state / "stubborn_networks").write_text("", encoding="utf-8", newline="\n")
        self.given(containers=["aaa111"], networks=["net1"], volumes=[])

        result = self.run_cleanup()
        self.assertEqual(result.returncode, 1)
        self.assertIn("residual networks", result.stderr)
        self.assertIn(PROJECT_LABEL, result.stderr)

        query_calls = [call for call in self.calls if call.startswith("network ls --quiet")]
        self.assertEqual(
            len(query_calls), 6, "a permanently stuck network should exhaust all 6 re-check attempts"
        )

    def test_settles_after_a_transient_removal_delay(self) -> None:
        """The bounded re-check: a network still clearing itself is not reported as residue.

        Models the daemon completing removal of a resource `down` had already reported as
        released, shortly after the first check -- the exact "Resource is still in use" timing
        the correction exists for. `stubborn_networks` keeps `compose down` from clearing it
        immediately; `settle_networks_after=2` clears it on the second verification query.
        """
        (self.state / "stubborn_networks").write_text("", encoding="utf-8", newline="\n")
        (self.state / "settle_networks_after").write_text("2", encoding="utf-8", newline="\n")
        self.given(containers=[], networks=["net1"], volumes=[])

        result = self.run_cleanup()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("no container, network or volume remains", result.stdout)
        self.assertIn("still settling", result.stderr)

        query_calls = [call for call in self.calls if call.startswith("network ls --quiet")]
        self.assertEqual(
            len(query_calls), 2, "should stop re-checking as soon as the resource clears"
        )

    def test_fails_when_a_container_survives_removal(self) -> None:
        (self.state / "stubborn_containers").write_text("", encoding="utf-8", newline="\n")
        self.given(containers=["aaa111"], networks=[], volumes=[])

        result = self.run_cleanup()
        self.assertEqual(result.returncode, 1)
        self.assertIn("residual containers", result.stderr)
        self.assertIn("still holds resources after teardown", result.stderr)

    def test_fails_when_a_volume_survives_teardown(self) -> None:
        (self.state / "stubborn_volumes").write_text("", encoding="utf-8", newline="\n")
        self.given(containers=[], networks=[], volumes=["vol1"])

        result = self.run_cleanup()
        self.assertEqual(result.returncode, 1)
        self.assertIn("residual volumes", result.stderr)
        self.assertIn(PROJECT_LABEL, result.stderr)

    def test_reports_success_when_nothing_remains(self) -> None:
        self.given(containers=["aaa111"], networks=["net1"], volumes=["vol1"])
        result = self.run_cleanup()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("no container, network or volume remains", result.stdout)


if __name__ == "__main__":
    unittest.main()
