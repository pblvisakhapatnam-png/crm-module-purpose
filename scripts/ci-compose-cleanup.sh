#!/usr/bin/env bash
#
# Project-scoped Compose cleanup for the TE-2CI `compose-e2e` job
# (corrections TE-2CI.2-C1 and TE-2CI.2-C2).
#
# Why this exists
# ---------------
# Two separate defects, both found on hosted runs, each one leaving a resource behind that a
# bare `docker compose down -v --remove-orphans` did not remove.
#
# 1. TE-2CI.2-C1, hosted run 31865333180, job 94968525849. `down` on its own is not sufficient
#    after a *cancelled* run. When the job is cancelled while
#    `docker compose --profile e2e run --rm e2e` is still running, that one-off container can
#    outlive the cancelled step for long enough to keep the project network attached. `down`
#    then reports
#
#        Network pbl-crm-hiring_default  Resource is still in use
#
#    and still exits successfully, leaving the network behind.
#
# 2. TE-2CI.2-C2, hosted run 31871165805. `down -v` removes named volumes only for services
#    that are *in scope*, and the `e2e` service is gated behind the Compose `e2e` profile. With
#    the profile inactive that service is out of scope, so its `e2e-node-modules` volume is not
#    removed. That run passed every substantive check, including Playwright, and then failed
#    verification because `pbl-crm-hiring-ci-31871165805_e2e-node-modules` survived teardown.
#
# A GitHub-hosted runner is disposable, so nothing accumulates there; but the workflow claimed
# the stronger guarantee that a run leaves no containers, networks or volumes on a reused or
# self-hosted runner, and that guarantee was not met in either case.
#
# This script makes it deterministic: every container carrying the project label is removed
# first -- the one-off `compose run` container included -- so nothing is still attached when
# the project is torn down; teardown activates the `e2e` profile so the profile-owned volume is
# in scope; and the result is then verified, with a short bounded re-check for a resource that
# is still settling, rather than assumed.
#
# Note that defect 2 was caught by this script's own verification step rather than by a later
# run tripping over the residue. That is the verification working as designed: the previous
# teardown would have reported success and left the volume behind silently.
#
# Fail-closed scope
# -----------------
# The script acts only on the exact project-name shape the `compose-e2e` job produces,
# `pbl-crm-hiring-ci-<numeric run id>`, and only when GITHUB_ACTIONS=true. A prefix match alone
# was too broad: it accepted the bare prefix and any hand-typed suffix. The local development
# project `pbl-crm-hiring` cannot match, so this script can never remove a developer's containers,
# networks or volumes -- including the retained `mssql-data` TE-2B rollback volume, which is not
# even declared in docker-compose.yml.
#
# It acts only on an exact `com.docker.compose.project` label match. It never runs
# `docker system prune`, never prunes containers, networks or volumes globally, and never names
# a resource explicitly.
#
# Usage:
#   bash scripts/ci-compose-cleanup.sh <compose-project-name>

set -euo pipefail

# The only project-name shape this script will act on: the literal CI prefix followed by a numeric
# GitHub run id, anchored at both ends. A bare prefix, an extra suffix or any hand-typed variation
# is refused. Anything rejected here exits 2 without touching Docker at all.
readonly REQUIRED_PROJECT_PATTERN='^pbl-crm-hiring-ci-[0-9]+$'

project="${1:-}"

if [[ -z "$project" ]]; then
  echo "ci-compose-cleanup: a Compose project name is required." >&2
  echo "Usage: bash scripts/ci-compose-cleanup.sh pbl-crm-hiring-ci-<run-id>" >&2
  exit 2
fi

if [[ ! "$project" =~ $REQUIRED_PROJECT_PATTERN ]]; then
  echo "ci-compose-cleanup: refusing to act on Compose project '${project}'." >&2
  echo "Only the CI project shape 'pbl-crm-hiring-ci-<numeric run id>' is in scope, so this" >&2
  echo "script cannot remove local development containers, networks or retained volumes." >&2
  exit 2
fi

# Second, independent gate: this is CI-only tooling and has no legitimate local use. Requiring the
# runner's own marker means a valid-looking project name typed on a workstation is still refused.
if [[ "${GITHUB_ACTIONS:-}" != "true" ]]; then
  echo "ci-compose-cleanup: refusing to run outside GitHub Actions (GITHUB_ACTIONS is not 'true')." >&2
  echo "This script tears down CI Compose projects only; it is not a local cleanup tool." >&2
  exit 2
fi

# Run from the repository root so `docker compose` finds docker-compose.yml regardless of the
# caller's working directory.
cd "$(dirname "${BASH_SOURCE[0]}")/.."

readonly PROJECT_LABEL="com.docker.compose.project=${project}"
export COMPOSE_PROJECT_NAME="$project"

echo "ci-compose-cleanup: tearing down Compose project '${project}'."

# Step 1 -- remove every container carrying the project label, whether or not Compose still
# considers it part of the project. A one-off `compose run` container left by a cancelled step
# is exactly the case `down` alone does not resolve.
#
# The id list is built so that an empty result produces a genuinely empty array rather than an
# array holding one empty string: `docker rm` is therefore never invoked with an empty argument
# list, and the ids are passed as array elements rather than relying on word splitting.
containers_raw="$(docker ps --all --quiet --filter "label=${PROJECT_LABEL}")"
containers=()
if [[ -n "$containers_raw" ]]; then
  mapfile -t containers <<< "$containers_raw"
fi

if (( ${#containers[@]} > 0 )); then
  echo "ci-compose-cleanup: force-removing ${#containers[@]} container(s) labelled ${PROJECT_LABEL}."
  # A `--rm` container can exit and auto-remove itself between discovery and removal, which is
  # exactly the cancellation case this script exists for. `docker rm` then reports "No such
  # container" and returns non-zero for a container that is already gone. Under `set -e` that
  # would abort before teardown and before verification -- turning a harmless race into a failed
  # step and, worse, skipping the cleanup still to be done. Tolerate it, keep going, and let the
  # verification below decide whether the project is actually clean.
  if ! docker rm --force --volumes "${containers[@]}"; then
    echo "ci-compose-cleanup: docker rm reported an error; a container may have exited and removed" >&2
    echo "itself between discovery and removal. Continuing; final verification decides the outcome." >&2
  fi
else
  echo "ci-compose-cleanup: no containers carry ${PROJECT_LABEL}."
fi

# Step 2 -- with nothing attached, the project's network and volumes can be removed cleanly.
#
# `--profile e2e` is required, not decorative. `down -v` removes named volumes only for services
# in scope, and the `e2e` service is gated behind that profile in docker-compose.yml, so with the
# profile inactive its `e2e-node-modules` volume is simply not considered. Activating the profile
# brings the service -- and therefore its volume -- into scope. `down` only removes, so naming the
# profile here never starts the E2E container.
#
# `-v` is safe here and only here: the CI project was created by this job in this runner.
echo "ci-compose-cleanup: running docker compose --profile e2e down -v --remove-orphans."
docker compose --profile e2e down -v --remove-orphans

# Step 3 -- verify rather than assume. Anything still carrying the project label is residue,
# and the step fails so a reused runner cannot quietly accumulate it.
#
# A container the daemon is still auto-removing -- the same `--rm` race step 1 tolerates -- can
# briefly still appear in these queries even though it is already clearing itself, and `down` can
# have logged its own "Resource is still in use" while that settles. Querying only once would
# read that transient state as permanent residue. A short, bounded re-check tells "still going"
# apart from "stuck" without weakening the assertion: it can only shorten a report that would
# otherwise have been a false positive, and a genuine survivor is still reported and still fails
# the step once the attempts are exhausted.
#
# The interval is overridable only so the test suite can run this loop without waiting on wall
# clock time; production always uses the 5-second default.
readonly POLL_ATTEMPTS=6
readonly POLL_INTERVAL_SECONDS="${CI_COMPOSE_CLEANUP_POLL_SECONDS:-5}"

left_containers=""
left_networks=""
left_volumes=""

for (( attempt = 1; attempt <= POLL_ATTEMPTS; attempt++ )); do
  left_containers="$(docker ps --all --quiet --filter "label=${PROJECT_LABEL}")"
  left_networks="$(docker network ls --quiet --filter "label=${PROJECT_LABEL}")"
  left_volumes="$(docker volume ls --quiet --filter "label=${PROJECT_LABEL}")"

  if [[ -z "$left_containers$left_networks$left_volumes" ]]; then
    break
  fi

  if (( attempt < POLL_ATTEMPTS )); then
    echo "ci-compose-cleanup: resources for ${PROJECT_LABEL} still settling (attempt ${attempt}/${POLL_ATTEMPTS}); rechecking in ${POLL_INTERVAL_SECONDS}s." >&2
    sleep "$POLL_INTERVAL_SECONDS"
  fi
done

residue=0

if [[ -n "$left_containers" ]]; then
  residue=1
  echo "ci-compose-cleanup: residual containers for ${PROJECT_LABEL}:" >&2
  docker ps --all --filter "label=${PROJECT_LABEL}" --format '  {{.ID}}  {{.Names}}  {{.Status}}' >&2
fi

if [[ -n "$left_networks" ]]; then
  residue=1
  echo "ci-compose-cleanup: residual networks for ${PROJECT_LABEL}:" >&2
  docker network ls --filter "label=${PROJECT_LABEL}" --format '  {{.ID}}  {{.Name}}' >&2
fi

if [[ -n "$left_volumes" ]]; then
  residue=1
  echo "ci-compose-cleanup: residual volumes for ${PROJECT_LABEL}:" >&2
  docker volume ls --filter "label=${PROJECT_LABEL}" --format '  {{.Name}}' >&2
fi

if (( residue != 0 )); then
  echo "ci-compose-cleanup: Compose project '${project}' still holds resources after teardown." >&2
  exit 1
fi

echo "ci-compose-cleanup: no container, network or volume remains for '${project}'."
