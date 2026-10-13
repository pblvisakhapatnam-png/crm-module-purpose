from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from .audit_events import (
    AuditEventCleanupError,
    DEFAULT_E2E_ACTORS,
    capture_business_event_boundary,
    delete_login_events_after,
    find_unlisted_login_events_after,
)
from .auth_tokens import TestTokenError, issue_test_bearer_token
from .cleanup import CleanupStorageError, CleanupValidationError, cleanup_manifest
from .manifest import ManifestValidationError, MANIFEST_VERSION, validate_manifest_dict
from .scenarios import SCENARIO_DESCRIPTIONS, SCENARIOS, run_scenario
from .status import check_manifest_status
from .store import list_runs, load_manifest, save_manifest


def _cmd_seed(args: argparse.Namespace) -> int:
    if args.scenario not in SCENARIOS:
        print(f"Unknown scenario {args.scenario!r}.", file=sys.stderr)
        print("Known scenarios:", file=sys.stderr)
        for name, description in sorted(SCENARIO_DESCRIPTIONS.items()):
            print(f"  {name}: {description}", file=sys.stderr)
        return 2

    try:
        manifest = run_scenario(args.scenario)
    except Exception as exc:  # noqa: BLE001 -- surfaced to the caller as a clean CLI failure
        print(f"Seeding scenario {args.scenario!r} failed: {exc}", file=sys.stderr)
        return 1

    if not args.no_save_local:
        save_manifest(manifest)

    if args.manifest_out:
        Path(args.manifest_out).write_text(json.dumps(manifest, indent=2, default=str), encoding="utf-8")

    if args.json:
        print(json.dumps(manifest, indent=2, default=str))
    else:
        _print_manifest_summary(manifest)

    return 0


def _cmd_event_boundary(args: argparse.Namespace) -> int:
    try:
        print(capture_business_event_boundary())
    except Exception as exc:  # noqa: BLE001 -- surfaced to the caller as a clean CLI failure
        print(f"Capturing the business_event boundary failed: {exc}", file=sys.stderr)
        return 1
    return 0


def _cmd_issue_test_token(args: argparse.Namespace) -> int:
    try:
        token = issue_test_bearer_token()
    except TestTokenError as exc:
        print(f"Could not issue a test token: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:  # noqa: BLE001 -- surfaced to the caller as a clean CLI failure
        print(f"Issuing a test token failed: {exc}", file=sys.stderr)
        return 1
    # Exactly one line on stdout: the token and nothing else, so a caller can capture it
    # directly without parsing surrounding text.
    print(token)
    return 0


def _cmd_cleanup_login_events(args: argparse.Namespace) -> int:
    actors = tuple(actor.strip() for actor in str(args.actors).split(",") if actor.strip())
    try:
        deleted = delete_login_events_after(int(args.after_id), actors)
        residual = find_unlisted_login_events_after(int(args.after_id), actors)
    except AuditEventCleanupError as exc:
        print(f"Refusing to clean up login events: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:  # noqa: BLE001 -- surfaced to the caller as a clean CLI failure
        print(f"Login-event cleanup failed: {exc}", file=sys.stderr)
        return 1

    print(
        f"Deleted {deleted} login event(s) above id {args.after_id} "
        f"for actor(s): {', '.join(actors)}."
    )

    if residual:
        # Deliberately not deleted: an unrecognised actor may be a real user. Reported so a
        # future spec using a seed user missing from the allowlist fails the run instead of
        # leaking audit rows silently.
        print(
            f"{len(residual)} identity login event(s) above id {args.after_id} were NOT "
            "created by an allowlisted E2E actor and have been left in place:",
            file=sys.stderr,
        )
        for row in residual:
            print(
                f"  id={row['id']} event_name={row['event_name']} "
                f"payload_username={row['payload_username']!r}",
                file=sys.stderr,
            )
        print(
            "If these are genuine E2E test users, add them to BOTH allowlist copies: "
            "DEFAULT_E2E_ACTORS in backend/tooling/smoke_data/audit_events.py and $e2eActors "
            "in scripts/run-e2e.ps1. Otherwise investigate the source of these logins.",
            file=sys.stderr,
        )
        return 3

    return 0


def _print_manifest_summary(manifest: dict) -> None:
    print(f"Run id:    {manifest['run_id']}")
    print(f"Scenario:  {manifest['scenario']}")
    print(f"Created:   {manifest['created_at']}")
    print(f"Actor:     {manifest['actor']['username']} ({manifest['actor']['public_id']})")
    print("Records:")
    for key, record in manifest["records"].items():
        offer = record.get("commercial_offer") or {}
        print(f"  - {key}: offer {offer.get('offer_code', '?')} [{record.get('commercial_offer_status', '?')}]")
        for work_order in record.get("work_orders", []) or []:
            print(f"      work order: {work_order.get('work_order_code', '?')}")
        if record.get("blocked_reason"):
            print(f"      blocked_reason: {record['blocked_reason']}")
    if manifest.get("urls"):
        print("URLs:")
        for label, url in manifest["urls"].items():
            print(f"  - {label}: {url}")


def _cmd_cleanup(args: argparse.Namespace) -> int:
    if not args.run_id and not args.manifest:
        print("cleanup requires either --run-id or --manifest.", file=sys.stderr)
        return 2
    if args.run_id and args.manifest:
        print("Pass only one of --run-id or --manifest, not both.", file=sys.stderr)
        return 2

    try:
        if args.manifest:
            manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
        else:
            manifest = load_manifest(args.run_id)
        validate_manifest_dict(manifest)
    except FileNotFoundError as exc:
        print(f"Cleanup failed: {exc}", file=sys.stderr)
        return 1
    except (json.JSONDecodeError, ManifestValidationError, ValueError) as exc:
        print(f"Cleanup failed: manifest or run id is malformed or unsafe: {exc}", file=sys.stderr)
        return 1

    try:
        counts = cleanup_manifest(manifest)
    except CleanupValidationError as exc:
        print(f"Cleanup failed: {exc}", file=sys.stderr)
        return 1
    except CleanupStorageError as exc:
        # The database half succeeded and is already committed; only the files failed. Reported as
        # a failure with a non-zero exit because the orphaned keys in this message are the only
        # surviving record of them - a later run finds no rows and cannot rediscover them.
        print(f"Cleanup INCOMPLETE for run {manifest['run_id']}: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001 -- surfaced to the caller as a clean CLI failure
        print(f"Cleanup failed due to a database error: {exc}", file=sys.stderr)
        return 1

    print(f"Cleanup complete for run {manifest['run_id']}:")
    total = 0
    for table, count in counts.items():
        total += count
        # "deleted" is accurate for every key in counts: row counts per table, plus
        # documents_storage_deleted for stored files. Any key whose meaning is NOT "n rows or
        # files removed" must not be added to counts - a failure count printed here would read as
        # a success, which is exactly the defect independent review found in the previous version.
        print(f"  - {table}: {count} deleted")
    if total == 0:
        print("  (no rows matched -- this run may already have been cleaned up; that is not an error)")

    # Deliberately does not delete the local run manifest file: keeping it means a
    # repeated `cleanup --run-id` against an already-cleaned run stays idempotent
    # (reports zero deletions, exits 0) instead of failing with "manifest not found".

    return 0


def _cmd_status(args: argparse.Namespace) -> int:
    if not args.run_id and not args.manifest:
        print("status requires either --run-id or --manifest.", file=sys.stderr)
        return 2
    if args.run_id and args.manifest:
        print("Pass only one of --run-id or --manifest, not both.", file=sys.stderr)
        return 2

    try:
        if args.manifest:
            manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
        else:
            manifest = load_manifest(args.run_id)
    except FileNotFoundError as exc:
        print(f"Status check failed: {exc}", file=sys.stderr)
        return 1
    except (json.JSONDecodeError, ManifestValidationError, ValueError) as exc:
        print(f"Status check failed: manifest or run id is malformed or unsafe: {exc}", file=sys.stderr)
        return 1

    try:
        result = check_manifest_status(manifest)
    except (ManifestValidationError, CleanupValidationError) as exc:
        # CleanupValidationError comes from _collect_ids, which status shares with cleanup. Without
        # it here a manifest carrying a non-UUID id was reported as a database error, sending the
        # operator to look at PostgreSQL for a fault in their own file. The exit code was right and
        # the diagnosis was wrong, which is the worse half to get wrong.
        print(f"Status check failed: manifest or run id is malformed or unsafe: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001 -- surfaced to the caller as a clean CLI failure
        print(f"Status check failed due to a database error: {exc}", file=sys.stderr)
        return 1

    print(f"Status for run {manifest['run_id']} (scenario={manifest['scenario']}):")
    for key in result["expected"]:
        print(f"  - {key}: {result['found'][key]}/{result['expected'][key]} present")

    residue = result["residue"]
    # Reported separately from this run's own residue, and never attributed to it: an orphaned
    # quote document cannot be traced to whoever created it, so folding it into this run's verdict
    # would blame the operator for someone else's leftover and teach them to ignore the warning.
    orphans = residue.get("orphaned_quote_documents", 0)
    leftovers = {
        key: count
        for key, count in residue.items()
        if count and key != "orphaned_quote_documents"
    }
    if leftovers:
        print("  attached records still present:")
        for key, count in sorted(leftovers.items()):
            print(f"  - {key}: {count}")
    if orphans:
        print(
            f"  NOTE: {orphans} orphaned quote document(s) exist in this database, not "
            "attributable to any run. Unrelated to this run's own result below."
        )

    if result["all_present"]:
        print("All anchor records are present.")
        return 0

    if args.require_present:
        # Asked for explicitly, because the two states below both used to exit 0. A caller that
        # needs the data there - vendor-demo preflight, say - was told "fine" by a run that had
        # been cleaned up outside the wrapper and had nothing left to demonstrate.
        print(
            "Anchor records are missing and --require-present was given: this run's data is not "
            "available.",
            file=sys.stderr,
        )
        return 1

    # The anchors being gone is the normal post-cleanup state, so report on what actually
    # matters then: whether anything survived them. These record types are not foreign-key
    # bound to their parents, so a leftover here is silent and would otherwise look like a
    # successful reset - see status.check_manifest_status.
    if result["all_absent"]:
        if result["residue_clear"]:
            # Deliberately careful wording. Residue is checked through each record's parent,
            # so this covers what is still identifiable - not anything attached to a record the
            # cleanup discovered and deleted without the manifest ever naming it.
            print(
                "This run's anchor records are gone and nothing was found attached to the "
                "records still identifiable."
            )
            return 0
        print(
            "This run's anchor records are gone, but attached records listed above SURVIVED. "
            "That is a cleanup defect, not an ordinary empty result -- report it rather than "
            "deleting the rows by hand.",
            file=sys.stderr,
        )
        return 1

    print("Some anchor records are missing -- a reset is recommended before demonstrating.")
    return 1


def _cmd_list_runs(_: argparse.Namespace) -> int:
    runs = list_runs()
    if not runs:
        print("No local smoke-data run manifests found.")
        return 0
    for run in runs:
        print(f"{run['run_id']}  scenario={run['scenario']}  created_at={run['created_at']}  path={run['manifest_path']}")
    return 0


def _cmd_scenarios(_: argparse.Namespace) -> int:
    print(f"Manifest version: {MANIFEST_VERSION}")
    print("Available scenarios:")
    for name, description in sorted(SCENARIO_DESCRIPTIONS.items()):
        print(f"  {name}: {description}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m tooling.smoke_data",
        description=(
            "TE-1 reusable smoke/regression test-data harness. Seeds and cleans up demo "
            "records by calling the same service-layer functions the real API routes use. "
            "This is testing/tooling code only; it is not part of the public API."
        ),
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    seed_parser = subparsers.add_parser("seed", help="Seed a named scenario and print/save its manifest.")
    seed_parser.add_argument("--scenario", required=True, help="Scenario name (see 'scenarios' command).")
    seed_parser.add_argument("--json", action="store_true", help="Print the manifest as JSON only (no summary text).")
    seed_parser.add_argument("--manifest-out", help="Also write the manifest JSON to this file path.")
    seed_parser.add_argument(
        "--no-save-local",
        action="store_true",
        help="Do not persist the manifest under backend/.smoke-runs/ (disables later 'cleanup --run-id').",
    )
    seed_parser.set_defaults(func=_cmd_seed)

    cleanup_parser = subparsers.add_parser("cleanup", help="Delete every record created by one seed run.")
    cleanup_parser.add_argument("--run-id", help="Run id of a locally-saved manifest under backend/.smoke-runs/.")
    cleanup_parser.add_argument("--manifest", help="Path to a manifest JSON file (alternative to --run-id).")
    cleanup_parser.set_defaults(func=_cmd_cleanup)

    status_parser = subparsers.add_parser(
        "status", help="Read-only check of whether a seeded run's anchor records still exist."
    )
    status_parser.add_argument("--run-id", help="Run id of a locally-saved manifest under backend/.smoke-runs/.")
    status_parser.add_argument("--manifest", help="Path to a manifest JSON file (alternative to --run-id).")
    status_parser.add_argument(
        "--require-present",
        action="store_true",
        help=(
            "Exit non-zero unless every anchor record still exists. Without it, status exits 0 "
            "both when the data is all there and when it has all been cleaned up - two opposite "
            "states a caller cannot tell apart from the exit code alone."
        ),
    )
    status_parser.set_defaults(func=_cmd_status)

    event_boundary_parser = subparsers.add_parser(
        "event-boundary",
        help="Print the current maximum business_event id (the pre-run boundary for E2E cleanup).",
    )
    event_boundary_parser.set_defaults(func=_cmd_event_boundary)

    issue_test_token_parser = subparsers.add_parser(
        "issue-test-token",
        help=(
            "Print a short-lived bearer token for the fixed local readonly1 seed identity "
            "only -- no username parameter, no other identity is ever issued a token. Refuses "
            "to run unless APP_ENV is an explicit local development/test value. Skips "
            "/api/auth/login and creates no UserLoginSucceeded business_event. "
            "Testing/tooling only; never reachable through any API route."
        ),
    )
    issue_test_token_parser.set_defaults(func=_cmd_issue_test_token)

    login_events_parser = subparsers.add_parser(
        "cleanup-login-events",
        help=(
            "Delete login audit events created above a captured boundary by the named E2E "
            "test actors. Never deletes business events or pre-existing rows."
        ),
    )
    login_events_parser.add_argument(
        "--after-id",
        required=True,
        type=int,
        help="Boundary id from 'event-boundary'. Only rows with a strictly greater id are eligible.",
    )
    login_events_parser.add_argument(
        "--actors",
        default=",".join(DEFAULT_E2E_ACTORS),
        help=f"Comma-separated usernames to restrict deletion to (default: {','.join(DEFAULT_E2E_ACTORS)}).",
    )
    login_events_parser.set_defaults(func=_cmd_cleanup_login_events)

    list_parser = subparsers.add_parser("list-runs", help="List locally-saved seed run manifests.")
    list_parser.set_defaults(func=_cmd_list_runs)

    scenarios_parser = subparsers.add_parser("scenarios", help="List the available scenario catalogue.")
    scenarios_parser.set_defaults(func=_cmd_scenarios)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
