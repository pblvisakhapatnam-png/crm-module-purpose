#!/usr/bin/env python3
"""Validate the repository's contract fixture JSON files.

TE-2CI.1 validation tooling. This is a deterministic, cross-platform check that runs identically
on Windows, Linux and inside a container. It has no third-party dependencies and needs no
database, network access or running application.

Which files are checked
-----------------------

Files are enumerated with `git ls-files --cached --others --exclude-standard`, so the check covers
the **proposed tree**: everything already committed, plus new files that are not ignored. That is
deliberate. A fixture added in a working branch is part of the change under review and must be
validated before it is committed, not after. Ignored paths are excluded by the same rule, so local
scratch files and generated artifacts are never inspected.

In CI, where the working tree is a clean checkout, this is exactly the set of committed files.

What it checks
--------------

1. Every candidate fixture JSON file parses (which also rejects JSON comments and trailing
   commas) and is readable, pretty-printed text.
2. The frozen Accepted Commercial Offer -> Work Order shell fixture pack satisfies the invariants
   documented in `docs/planning/HANDOFF_FIXTURE_VALIDATION_CHECKLIST.md`: core identity
   continuity, Account traceability, Commercial Offer line identity, Work Order source-line
   identity, shell status, and the negative-path expectations.
3. No fixture carries an obvious committed secret or a real-data marker.

What it deliberately does not do
--------------------------------

It only looks under `docs/agent/fixtures`; unrelated JSON elsewhere in the repository is not a
contract fixture and is left alone. It does not validate against a database schema, does not load
fixtures as seed data, and does not promote, freeze or otherwise change any contract. Fixtures are
contract examples only. See `docs/agent/fixtures/accepted-offer-work-order/README.md`.

Usage
-----

    python scripts/validate_contract_fixtures.py

Exit codes: 0 = all rules pass, 1 = at least one rule failed, 2 = the check could not run.

Every failure is reported as `<file>: [<RULE-ID>] <message>` so the affected file and the violated
rule are both explicit.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Iterable, Sequence

DEFAULT_REPO_ROOT = Path(__file__).resolve().parents[1]

# Only fixtures under this directory are validated. Package manifests, lock files and tsconfig
# elsewhere in the repository are not contract fixtures.
FIXTURE_ROOT = "docs/agent/fixtures"

# The frozen Accepted Offer -> Work Order pack. Slice 6D.1 froze the handoff contract and Slice
# 6D.3 created these examples; the pack is expected to be complete, so a missing file is itself a
# failure rather than a silently skipped check.
HANDOFF_DIR = f"{FIXTURE_ROOT}/accepted-offer-work-order"
HANDOFF_FILES = {
    "handoff": "accepted-commercial-offer-handoff-example.json",
    "shell_output": "work-order-shell-output-example.json",
    "partial_award": "partial-award-selected-lines-example.json",
    "negative_missing_account": "negative-missing-account-traceability-example.json",
    "negative_invalid_line": "negative-invalid-line-selection-example.json",
}

# The production MVP shell status for these examples. The current prototype maps shell creation to
# HANDOFF_CREATED; the fixtures record that mapping as a note, and neither value may silently
# become PENDING_CUSTOMER_MASTER.
EXPECTED_SHELL_STATUS = "HANDOFF_RECEIVED"
FORBIDDEN_SHELL_STATUS = "PENDING_CUSTOMER_MASTER"

SAFE_PAN_GSTIN_PLACEHOLDER = "PLACEHOLDER_NOT_REAL"

# Reserved, non-routable documentation hosts. A fixture link pointing anywhere else would be
# either a real document location or an unowned external host.
ALLOWED_URL_HOSTS = ("example.invalid", "example.com", "example.org", "example.net")

REAL_PAN_PATTERN = re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b")
REAL_GSTIN_PATTERN = re.compile(r"\b[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][0-9A-Z]{3}\b")
URL_PATTERN = re.compile(r"https?://([^/\s\"']+)", re.IGNORECASE)
EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
PRIVATE_KEY_PATTERN = re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")
JWT_PATTERN = re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b")

# Key names that must never appear anywhere in a fixture, at any nesting depth. These carry
# credential material by definition.
FORBIDDEN_KEY_SUBSTRINGS = (
    "password",
    "passwd",
    "secret",
    "api_key",
    "apikey",
    "access_token",
    "refresh_token",
    "auth_token",
    "private_key",
    "client_secret",
    "authorization",
    "credential",
)

GIT_DISCOVERY_ARGS = ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"]
GIT_DISCOVERY_LABEL = "git ls-files --cached --others --exclude-standard"


class FixtureCheckError(RuntimeError):
    """The validator could not run (missing repository, git failure, unreadable file)."""


def discover_fixture_files(repo_root: Path) -> tuple[list[Path], str]:
    """Return candidate fixture JSON paths, sorted, so runs are byte-for-byte repeatable.

    `--cached --others --exclude-standard` covers committed files plus new, non-ignored files, so
    a fixture added in a working branch is validated before it is committed. Ignored paths are
    excluded by the same rule.

    Where git is not on PATH -- for example inside a minimal Python container -- the fallback is a
    sorted walk of the fixture directory. The source used is printed, so a run can never be
    misread as having covered more than it did.
    """
    try:
        completed = subprocess.run(
            GIT_DISCOVERY_ARGS + ["--", FIXTURE_ROOT],
            cwd=repo_root,
            capture_output=True,
            check=True,
        )
    except FileNotFoundError:
        fixture_dir = repo_root / FIXTURE_ROOT
        if not fixture_dir.is_dir():
            raise FixtureCheckError(
                f"git is unavailable and {FIXTURE_ROOT} does not exist."
            ) from None
        return sorted(fixture_dir.rglob("*.json")), "directory walk (git unavailable)"
    except subprocess.CalledProcessError as exc:
        raise FixtureCheckError(
            f"git ls-files failed: {exc.stderr.decode(errors='replace').strip()}"
        ) from exc

    names = [name for name in completed.stdout.decode("utf-8").split("\0") if name]
    # `--others` can list a path twice when it is both cached and present in the working tree on
    # some git versions; de-duplicate so a file is never reported twice.
    paths = {repo_root / name for name in names if name.endswith(".json")}
    return sorted(paths), GIT_DISCOVERY_LABEL


def iter_key_value_pairs(node: Any, path: str = "$") -> Iterable[tuple[str, str, Any]]:
    """Yield (json_path, key, value) for every mapping entry, at any depth."""
    if isinstance(node, dict):
        for key, value in node.items():
            child_path = f"{path}.{key}"
            yield child_path, str(key), value
            yield from iter_key_value_pairs(value, child_path)
    elif isinstance(node, list):
        for index, value in enumerate(node):
            yield from iter_key_value_pairs(value, f"{path}[{index}]")


def check_parses_and_is_readable(
    path: Path, repo_root: Path, failures: list[str]
) -> Any | None:
    """Rules FIX-000/FIX-001/FIX-002: the file is readable, parses, and is pretty-printed."""
    relative = path.relative_to(repo_root).as_posix()
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        # A file that git knows about but cannot be read -- most often deleted from the working
        # tree while still in the index -- is a reviewable defect in the proposed change, not a
        # reason to abandon the whole run.
        failures.append(f"{relative}: [FIX-000] could not be read: {exc}")
        return None

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        failures.append(
            f"{relative}: [FIX-001] does not parse as JSON "
            f"(line {exc.lineno}, column {exc.colno}: {exc.msg}). "
            "JSON comments and trailing commas are not permitted."
        )
        return None

    if "\n" not in raw.strip():
        failures.append(f"{relative}: [FIX-002] is not pretty-printed across multiple lines.")
    if "\t" in raw:
        failures.append(f"{relative}: [FIX-002] uses tab indentation; use spaces.")
    if not raw.endswith("\n"):
        failures.append(f"{relative}: [FIX-002] does not end with a newline.")

    return data


def check_no_secrets_or_real_data(
    path: Path, repo_root: Path, data: Any, failures: list[str]
) -> None:
    """Rules FIX-010..FIX-017: no committed secret and no real-data marker."""
    relative = path.relative_to(repo_root).as_posix()
    raw = path.read_text(encoding="utf-8")

    for json_path, key, value in iter_key_value_pairs(data):
        lowered = key.lower()
        for forbidden in FORBIDDEN_KEY_SUBSTRINGS:
            if forbidden not in lowered:
                continue
            # A boolean or numeric value cannot be credential material, so an assertion flag such
            # as `"no_secrets": true` is not a finding. Anything else under a credential-named key
            # is -- including a container, which could hide one.
            if isinstance(value, bool) or isinstance(value, (int, float)) or value is None:
                break
            failures.append(
                f"{relative}: [FIX-010] key {json_path} contains {forbidden!r} and carries a "
                "value; fixtures must never carry credential material."
            )
            break

        # `safe_demo_data` / `contains_real_customer_data` are the pack's own declarations that a
        # fixture is fictional. Flipping either one is treated as a real-data marker.
        if key == "safe_demo_data" and value is not True:
            failures.append(
                f"{relative}: [FIX-011] {json_path} must be true; every committed fixture "
                "is fictional demo data."
            )
        if key == "contains_real_customer_data" and value is not False:
            failures.append(
                f"{relative}: [FIX-011] {json_path} must be false; real customer data must "
                "never be committed."
            )

    if PRIVATE_KEY_PATTERN.search(raw):
        failures.append(f"{relative}: [FIX-012] contains a PEM private-key block.")
    if JWT_PATTERN.search(raw):
        failures.append(f"{relative}: [FIX-013] contains a JSON Web Token.")

    for match in REAL_PAN_PATTERN.finditer(raw):
        failures.append(
            f"{relative}: [FIX-014] contains a real-shaped PAN {match.group(0)!r}; "
            f"use {SAFE_PAN_GSTIN_PLACEHOLDER}."
        )
    for match in REAL_GSTIN_PATTERN.finditer(raw):
        failures.append(
            f"{relative}: [FIX-015] contains a real-shaped GSTIN {match.group(0)!r}; "
            f"use {SAFE_PAN_GSTIN_PLACEHOLDER}."
        )

    for match in URL_PATTERN.finditer(raw):
        host = match.group(1).split("@")[-1].split(":")[0].lower()
        if not any(host == allowed or host.endswith("." + allowed) for allowed in ALLOWED_URL_HOSTS):
            failures.append(
                f"{relative}: [FIX-016] links to host {host!r}; fixture document links must "
                f"use a reserved documentation host ({', '.join(ALLOWED_URL_HOSTS)})."
            )

    for match in EMAIL_PATTERN.finditer(raw):
        domain = match.group(0).rsplit("@", 1)[1].lower()
        if not any(domain == allowed or domain.endswith("." + allowed) for allowed in ALLOWED_URL_HOSTS):
            failures.append(
                f"{relative}: [FIX-017] contains email address {match.group(0)!r}; fixtures "
                "must not carry real personal or customer contact data."
            )


def _require(condition: bool, failures: list[str], relative: str, rule: str, message: str) -> bool:
    if not condition:
        failures.append(f"{relative}: [{rule}] {message}")
    return condition


def check_handoff_pack(packs: dict[str, Any], failures: list[str]) -> None:
    """Rules HOF-001..HOF-022: the frozen handoff pack's documented invariants."""
    handoff = packs["handoff"]
    shell = packs["shell_output"]
    partial = packs["partial_award"]
    negative_account = packs["negative_missing_account"]
    negative_line = packs["negative_invalid_line"]

    handoff_name = f"{HANDOFF_DIR}/{HANDOFF_FILES['handoff']}"
    shell_name = f"{HANDOFF_DIR}/{HANDOFF_FILES['shell_output']}"
    partial_name = f"{HANDOFF_DIR}/{HANDOFF_FILES['partial_award']}"
    negative_account_name = f"{HANDOFF_DIR}/{HANDOFF_FILES['negative_missing_account']}"
    negative_line_name = f"{HANDOFF_DIR}/{HANDOFF_FILES['negative_invalid_line']}"

    header = handoff.get("header") or {}
    handoff_lines = handoff.get("lines") or []

    # --- Core identity continuity (checklist: Identity Continuity Check) ---
    _require(
        header.get("commercial_offer_public_id") == shell.get("linked_commercial_offer_public_id"),
        failures,
        shell_name,
        "HOF-001",
        "linked_commercial_offer_public_id must equal the handoff header's "
        f"commercial_offer_public_id ({header.get('commercial_offer_public_id')!r}).",
    )
    _require(
        header.get("opportunity_public_id") == shell.get("linked_opportunity_public_id"),
        failures,
        shell_name,
        "HOF-002",
        "linked_opportunity_public_id must equal the handoff header's opportunity_public_id.",
    )
    _require(
        header.get("account_public_id") == shell.get("linked_account_public_id"),
        failures,
        shell_name,
        "HOF-003",
        "linked_account_public_id must equal the handoff header's account_public_id.",
    )
    _require(
        header.get("accepted_offer_reference") == shell.get("accepted_offer_reference"),
        failures,
        shell_name,
        "HOF-004",
        "accepted_offer_reference must be stable across the handoff and output examples.",
    )
    _require(
        bool(header.get("correlation_id")) and header.get("correlation_id") == shell.get("correlation_id"),
        failures,
        shell_name,
        "HOF-005",
        "correlation_id must be present and stable across the handoff and output examples.",
    )

    # --- Account traceability (checklist: Account Traceability Check) ---
    _require(
        bool(header.get("account_public_id")),
        failures,
        handoff_name,
        "HOF-006",
        "a valid handoff example must carry account_public_id.",
    )
    _require(
        bool((partial.get("accepted_commercial_offer") or {}).get("account_public_id")),
        failures,
        partial_name,
        "HOF-006",
        "a valid handoff example must carry account_public_id.",
    )

    # --- Commercial Offer line identity (checklist: Line Identity Check) ---
    _require(
        len(handoff_lines) > 0,
        failures,
        handoff_name,
        "HOF-007",
        "the handoff example must contain at least one Commercial Offer line.",
    )
    sequences: list[Any] = []
    handoff_line_ids: list[str] = []
    for index, line in enumerate(handoff_lines):
        line_id = line.get("commercial_offer_line_public_id")
        _require(
            bool(line_id),
            failures,
            handoff_name,
            "HOF-008",
            f"lines[{index}] is missing commercial_offer_line_public_id; line identity is the "
            "frozen attachment point for Work Order lines.",
        )
        _require(
            line.get("line_sequence") is not None,
            failures,
            handoff_name,
            "HOF-009",
            f"lines[{index}] is missing line_sequence.",
        )
        _require(
            bool(line.get("line_status")),
            failures,
            handoff_name,
            "HOF-009",
            f"lines[{index}] is missing line_status.",
        )
        if line_id:
            handoff_line_ids.append(line_id)
        sequences.append(line.get("line_sequence"))

    _require(
        len(set(handoff_line_ids)) == len(handoff_line_ids),
        failures,
        handoff_name,
        "HOF-010",
        "Commercial Offer line public IDs must be unique.",
    )
    _require(
        sequences == sorted(s for s in sequences if s is not None) and len(set(sequences)) == len(sequences),
        failures,
        handoff_name,
        "HOF-010",
        "line_sequence values must be unique and in ascending order.",
    )

    # --- Work Order source-line identity (checklist: Source-Line Identity Check) ---
    shell_source_ids: list[str] = []
    for index, line in enumerate(shell.get("work_order_lines") or []):
        source_id = line.get("source_commercial_offer_line_public_id")
        _require(
            bool(source_id),
            failures,
            shell_name,
            "HOF-011",
            f"work_order_lines[{index}] is missing source_commercial_offer_line_public_id.",
        )
        if source_id:
            shell_source_ids.append(source_id)

    _require(
        sorted(shell_source_ids) == sorted(handoff_line_ids),
        failures,
        shell_name,
        "HOF-012",
        "every Work Order line must trace to a Commercial Offer line in the handoff example, "
        f"and none may be invented (handoff lines: {sorted(handoff_line_ids)}, "
        f"Work Order source lines: {sorted(shell_source_ids)}).",
    )

    # --- Partial award (checklist: selected versus excluded lines) ---
    selected_ids = list(partial.get("selected_line_public_ids") or [])
    available = partial.get("available_offer_lines") or []
    available_by_id = {
        line.get("commercial_offer_line_public_id"): line
        for line in available
        if line.get("commercial_offer_line_public_id")
    }
    excluded_ids = [
        line.get("commercial_offer_line_public_id")
        for line in (partial.get("excluded_lines") or [])
    ]
    partial_shell = partial.get("work_order_shell") or {}
    partial_source_ids = [
        line.get("source_commercial_offer_line_public_id")
        for line in (partial_shell.get("work_order_lines") or [])
    ]

    _require(
        bool(selected_ids),
        failures,
        partial_name,
        "HOF-013",
        "the partial-award example must identify selected lines.",
    )
    for selected in selected_ids:
        _require(
            selected in available_by_id,
            failures,
            partial_name,
            "HOF-013",
            f"selected line {selected!r} is not present in available_offer_lines.",
        )
        line = available_by_id.get(selected) or {}
        _require(
            line.get("line_status") == "AWARDED",
            failures,
            partial_name,
            "HOF-014",
            f"selected line {selected!r} must be AWARDED, not {line.get('line_status')!r}; "
            "a Work Order line must never derive from a non-awarded or cancelled source line.",
        )

    _require(
        sorted(partial_source_ids) == sorted(selected_ids),
        failures,
        partial_name,
        "HOF-015",
        "Work Order lines must be created for exactly the selected lines "
        f"(selected: {sorted(selected_ids)}, created from: {sorted(partial_source_ids)}).",
    )
    for excluded in excluded_ids:
        _require(
            excluded not in partial_source_ids,
            failures,
            partial_name,
            "HOF-015",
            f"excluded line {excluded!r} must not produce a Work Order line.",
        )

    # --- Shell status (checklist: Status Check) ---
    for name, shell_node in ((shell_name, shell), (partial_name, partial_shell)):
        status = shell_node.get("work_order_status")
        _require(
            status == EXPECTED_SHELL_STATUS,
            failures,
            name,
            "HOF-016",
            f"work_order_status must be {EXPECTED_SHELL_STATUS!r} in the production MVP "
            f"examples, not {status!r}.",
        )
        _require(
            status != FORBIDDEN_SHELL_STATUS,
            failures,
            name,
            "HOF-016",
            f"{FORBIDDEN_SHELL_STATUS!r} must not be used as the initial shell status.",
        )

    # --- Negative paths (checklist: Negative-Path Checks) ---
    missing_account_request = negative_account.get("invalid_handoff_request") or {}
    _require(
        missing_account_request.get("account_public_id") is None,
        failures,
        negative_account_name,
        "HOF-017",
        "the missing-Account example must have a null account_public_id.",
    )
    account_rejection = negative_account.get("expected_rejection") or {}
    _require(
        account_rejection.get("should_reject") is True,
        failures,
        negative_account_name,
        "HOF-018",
        "the missing-Account example must expect rejection.",
    )
    _require(
        account_rejection.get("work_order_created") is False,
        failures,
        negative_account_name,
        "HOF-018",
        "the missing-Account example must not create a Work Order shell.",
    )
    _require(
        (negative_account.get("expected_business_event_or_audit_behavior") or {}).get(
            "success_business_event_created"
        )
        is False,
        failures,
        negative_account_name,
        "HOF-019",
        "a rejected handoff must not record a success business event.",
    )

    line_request = negative_line.get("invalid_handoff_request") or {}
    line_rejection = negative_line.get("expected_rejection") or {}
    _require(
        line_rejection.get("should_reject") is True,
        failures,
        negative_line_name,
        "HOF-020",
        "the invalid-line example must expect rejection.",
    )
    _require(
        line_rejection.get("work_order_created") is False,
        failures,
        negative_line_name,
        "HOF-020",
        "the invalid-line example must not create a Work Order shell.",
    )
    _require(
        line_rejection.get("partial_silent_success_allowed") is False,
        failures,
        negative_line_name,
        "HOF-021",
        "an invalid line selection must not be allowed to partially succeed silently.",
    )
    _require(
        (negative_line.get("expected_business_event_or_audit_behavior") or {}).get(
            "success_business_event_created"
        )
        is False,
        failures,
        negative_line_name,
        "HOF-019",
        "a rejected handoff must not record a success business event.",
    )

    selected_negative_ids = list(line_request.get("selected_line_public_ids") or [])
    reasons = negative_line.get("invalid_line_reasons") or []
    _require(
        bool(reasons),
        failures,
        negative_line_name,
        "HOF-022",
        "the invalid-line example must state why each invalid line is invalid.",
    )
    for reason in reasons:
        invalid_id = reason.get("commercial_offer_line_public_id")
        _require(
            invalid_id in selected_negative_ids,
            failures,
            negative_line_name,
            "HOF-022",
            f"invalid_line_reasons names {invalid_id!r}, which is not in "
            "selected_line_public_ids; the example would not exercise the rejection.",
        )
        _require(
            bool(reason.get("reason")),
            failures,
            negative_line_name,
            "HOF-022",
            f"invalid line {invalid_id!r} has no stated reason.",
        )


def validate_repository(repo_root: Path) -> tuple[int, list[str], list[str]]:
    """Run every rule. Returns (exit_code, info_lines, failures)."""
    info: list[str] = []

    try:
        fixture_paths, discovery_source = discover_fixture_files(repo_root)
    except FixtureCheckError as exc:
        return 2, info, [f"Contract fixture validation could not run: {exc}"]

    if not fixture_paths:
        return (
            2,
            info,
            [
                "Contract fixture validation could not run: no JSON fixtures found under "
                f"{FIXTURE_ROOT}."
            ],
        )

    failures: list[str] = []
    parsed: dict[str, Any] = {}

    for path in fixture_paths:
        data = check_parses_and_is_readable(path, repo_root, failures)
        if data is None:
            continue
        parsed[path.relative_to(repo_root).as_posix()] = data
        check_no_secrets_or_real_data(path, repo_root, data, failures)

    # The frozen pack's cross-file invariants are validated only when every one of its files
    # parsed. A missing or unparsable file is already reported above; running them on a partial
    # pack would add confusing follow-on errors.
    packs: dict[str, Any] = {}
    missing: list[str] = []
    for key, filename in HANDOFF_FILES.items():
        relative = f"{HANDOFF_DIR}/{filename}"
        if relative in parsed:
            packs[key] = parsed[relative]
        else:
            missing.append(relative)

    if missing:
        for relative in missing:
            failures.append(
                f"{relative}: [HOF-000] is missing or did not parse; the frozen Accepted Offer "
                "-> Work Order fixture pack must be complete."
            )
    else:
        check_handoff_pack(packs, failures)

    info.append(
        f"Contract fixture validation: {len(fixture_paths)} candidate fixture file(s) checked "
        f"(discovered via {discovery_source})."
    )
    for path in fixture_paths:
        info.append(f"  - {path.relative_to(repo_root).as_posix()}")

    return (1 if failures else 0), info, failures


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--repo-root",
        default=str(DEFAULT_REPO_ROOT),
        help="Repository root to validate (defaults to this script's repository).",
    )
    args = parser.parse_args(argv)

    exit_code, info, failures = validate_repository(Path(args.repo_root).resolve())

    for line in info:
        print(line)

    if exit_code == 2:
        for failure in failures:
            print(failure, file=sys.stderr)
        return 2

    if failures:
        print("", file=sys.stderr)
        print(f"{len(failures)} contract fixture rule failure(s):", file=sys.stderr)
        for failure in failures:
            print(f"  {failure}", file=sys.stderr)
        return 1

    print("All contract fixture rules passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
