#!/usr/bin/env python3
"""Basic committed-credential check for the repository.

TE-2CI.1 validation tooling. Deterministic, cross-platform, no third-party dependencies and no
network access, so the result is identical on a developer machine and on a CI runner.

Which files are checked
-----------------------

Files are enumerated with `git ls-files --cached --others --exclude-standard`, so the check covers
the **proposed tree**: everything already committed, plus new files that are not ignored. A
credential added in a working branch is caught before it is committed rather than after.

Ignored paths are excluded by the same rule, which is what keeps a local `.env`, virtualenv, cache
or build artifact out of scope. `.env` is gitignored, so this check never opens it.

In CI, where the working tree is a clean checkout, this is exactly the set of committed files.

Scope
-----

This is a guard against committing a credential, not a history scanner and not a replacement for a
managed secret-scanning service. It cannot find a secret that was committed and later removed.

Rules
-----

SEC-001  A credential-bearing file path must not be in the tree at all (`.env`, private keys, key
         stores). The file's contents are not inspected; its presence is the finding.
SEC-002  No PEM private-key block.
SEC-003  No provider credential matching a well-known issued-token format (AWS, GitHub classic and
         fine-grained tokens, Slack, Google, Stripe) or a JSON Web Token.
SEC-004  No assignment of a credential-named variable to a concrete-looking value.

Known limit, recorded 13 September 2026: every rule above keys on a credential NAME, a known token
format, or a file path. A real credential used as a bare literal - `_login(user, "S@l3suser123_1")`
- has none of those, and is not detected. Flagging every credential-shaped string across the tree
would produce false positives at a rate that gets this check ignored. A green result therefore
means "no credential in the shapes below", not "no credential". See
docs/agent/DEFERRED_REQUIREMENTS.md, "What the committed-credential check does not cover".
SEC-005  No connection URL carrying an inline credential.

SEC-004 and SEC-005 recognise placeholder values by shape -- `change-this...`, `example`,
`placeholder`, `your-...`, `${VAR}`, `<value>`, `dummy`, `not-real`, `xxxx` -- so documentation and
`.env.example` remain honest about naming their fields without tripping the gate. This is a
value-shape rule, deliberately not a path or directory exclusion: no file in scope is exempt from
scanning, and adding a blanket exclusion to silence a finding is not an accepted fix.

Usage
-----

    python scripts/check_tracked_secrets.py

Exit codes: 0 = no finding, 1 = at least one finding, 2 = the check could not run.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path
from typing import Sequence

DEFAULT_REPO_ROOT = Path(__file__).resolve().parents[1]

# Files that must never be in the tree, matched against the repository-relative POSIX path.
FORBIDDEN_PATH_PATTERNS = (
    re.compile(r"(^|/)\.env$"),
    re.compile(r"(^|/)\.env\.(local|production|prod|staging)$"),
    re.compile(r"\.(pem|key|pfx|p12|jks|keystore|ppk)$"),
    re.compile(r"(^|/)id_(rsa|dsa|ecdsa|ed25519)$"),
    re.compile(r"(^|/)\.npmrc$"),
    re.compile(r"(^|/)\.pypirc$"),
)

# `.env.example` is explicitly permitted: it is the documented template of variable *names* and
# carries only placeholder values, which SEC-004 independently verifies.
ALLOWED_PATH_EXCEPTIONS = frozenset({".env.example"})

PRIVATE_KEY_PATTERN = re.compile(r"-----BEGIN (?:[A-Z]+ )?PRIVATE KEY-----")

ISSUED_CREDENTIAL_PATTERNS = {
    "AWS access key id": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    # Classic and OAuth-style GitHub tokens.
    "GitHub token": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}\b"),
    # Fine-grained personal access token. Underscores are part of the body, so the trailing
    # boundary is expressed as "not a token character" rather than \b.
    "GitHub fine-grained token": re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}(?![A-Za-z0-9_])"),
    "Slack token": re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b"),
    "Google API key": re.compile(r"\bAIza[0-9A-Za-z_\-]{35}\b"),
    "Stripe live key": re.compile(r"\bsk_live_[0-9a-zA-Z]{16,}\b"),
    "JSON Web Token": re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b"),
}

_CREDENTIAL_NAME = r"""
    password | passwd | pwd | secret | secret_key | api[_-]?key |
    access[_-]?token | refresh[_-]?token | auth[_-]?token |
    client[_-]?secret | private[_-]?key | connection[_-]?string
"""

# A credential-named field assigned a **quoted string literal**: `password: "..."`, PASSWORD='...',
# "apiKey": "...", db_password = "...". The name may carry a prefix or suffix (`db_password`,
# `SERVICE_API_KEY`), which is why the boundary is a word-character run rather than \b.
QUOTED_CREDENTIAL_PATTERN = re.compile(
    rf"""(?ix)
    ["']? \b (?P<name> [A-Za-z0-9]* _? (?: {_CREDENTIAL_NAME} ) _? [A-Za-z0-9]* ) \b ["']?
    \s* [:=] \s*
    (?P<quote>["']) (?P<value> [^"']{{4,}} ) (?P=quote)
    """
)

# An environment-file style assignment: the whole line is `NAME=value`, optionally exported. Two
# shape rules keep ordinary source code out of scope, because environment syntax and code differ
# consistently: the name is upper-case, and there is no whitespace around `=`. So
# `PASSWORD_ITERATIONS = 240000` (a Python constant) and `password=settings.postgres_password,`
# (an identifier reference) are both correctly out of scope, while `API_KEY=<value>` is in it.
ENV_CREDENTIAL_PATTERN = re.compile(
    rf"""(?x)
    ^ [ \t]* (?:export[ \t]+)?
    (?P<name> [A-Z0-9_]* (?: {_CREDENTIAL_NAME.upper()} ) [A-Z0-9_]* )
    =
    (?P<value> [^\s#]{{8,}} ) [ \t]* $
    """
)

# A connection URL carrying inline credentials, e.g. postgresql://user:placeholder@host/db.
URL_INLINE_CREDENTIAL_PATTERN = re.compile(
    r"""(?ix)
    [a-z][a-z0-9+.\-]* :// [^\s:/@"']+ : (?P<value> [^\s:/@"']+ ) @
    """
)

# A trailing segment that makes the name describe a credential rather than hold one:
# PASSWORD_ALGORITHM, api_key_header, SECRET_FIELD_NAME. Matched against the name's last
# underscore-separated word, so it never exempts a bare `password` or `api_key`.
NON_CREDENTIAL_NAME_SUFFIXES = frozenset(
    {
        "algorithm", "algo", "iterations", "length", "len", "size", "bytes", "field",
        "fields", "label", "name", "names", "regex", "pattern", "patterns", "header",
        "headers", "hash", "column", "columns", "placeholder", "prompt", "input", "error",
        "message", "policy", "rule", "rules", "type", "types", "format", "min", "max",
        "count", "enabled", "required",
    }
)
# "key" is deliberately absent: it is the last segment of API_KEY and PRIVATE_KEY, which must
# stay in scope.

# A value with any of these shapes is a placeholder, not a credential. `${VAR}`, `{{VAR}}`,
# `%VAR%`, `<value>` and `{VAR}` are interpolation markers -- the last covers Python format strings
# and f-strings, where the value is a variable name rather than a secret. Each is anchored to the
# whole value, so a real credential that merely contains a brace is still reported. The final
# alternation lists archetypal non-secret literals: a credential whose value is the word "password"
# or "changeme" is by definition not a real one. These are value-shape judgements, applied
# uniformly to every file in scope, not an exemption for any particular path.
PLACEHOLDER_VALUE_PATTERN = re.compile(
    r"""(?ix)
    ^(?:
        .*change.* | .*example.* | .*placeholder.* | .*sample.* | .*dummy.* |
        .*not[-_]?real.* | .*redacted.* | .*your[-_].* | .*todo.* | .*fixme.* |
        \$\{.*\} | \$[A-Za-z_][A-Za-z0-9_]* | <.*> | \{\{.*\}\} | %[A-Za-z_]+% |
        \{[A-Za-z_][A-Za-z0-9_]*\} |
        x{4,} | \*{4,} | \.{3,} | [-_]{4,} |
        .*ci[-_]not[-_]a[-_]real.* | .*\bfake\b.* | .*fictional.* |
        password | passw0rd | pass | passwd | secret | changeme | test | testing |
        admin | none | null | empty | string
    )$
    """
)

MAX_SCANNED_BYTES = 5 * 1024 * 1024

GIT_DISCOVERY_ARGS = ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"]
GIT_DISCOVERY_LABEL = "git ls-files --cached --others --exclude-standard"


class SecretCheckError(RuntimeError):
    """The check could not run."""


def looks_like_a_credential(value: str) -> bool:
    """Shape gate for SEC-004/SEC-005: does this value resemble issued credential material?

    Issued credentials are long and mix letter classes. An English-language literal such as
    `wrong-password` in a negative test is neither, so it is not reported. A value that is
    genuinely a credential but shaped like prose would be missed here; that is the accepted limit
    of a basic check, and is why it is described as a guard rather than a scanner.
    """
    if PLACEHOLDER_VALUE_PATTERN.match(value):
        return False
    if len(value) >= 16:
        return True
    return len(value) >= 8 and any(c.isdigit() for c in value) and any(c.isalpha() for c in value)


def discover_candidate_files(repo_root: Path) -> list[Path]:
    """Return the proposed tree: committed files plus new, non-ignored files.

    `--cached --others --exclude-standard` is what makes this a check of the change under review
    rather than only of what is already committed, while still honouring .gitignore so local
    secrets and generated artifacts are never opened.
    """
    try:
        completed = subprocess.run(
            GIT_DISCOVERY_ARGS,
            cwd=repo_root,
            capture_output=True,
            check=True,
        )
    except FileNotFoundError as exc:
        raise SecretCheckError(
            "git is required: this check is defined over the repository's proposed tree."
        ) from exc
    except subprocess.CalledProcessError as exc:
        raise SecretCheckError(
            f"git ls-files failed: {exc.stderr.decode(errors='replace').strip()}"
        ) from exc

    names = {name for name in completed.stdout.decode("utf-8").split("\0") if name}
    return sorted(repo_root / name for name in names)


def read_text_or_none(path: Path) -> str | None:
    """Return file text, or None when the file is binary, oversized or unreadable."""
    try:
        if path.stat().st_size > MAX_SCANNED_BYTES:
            return None
        raw = path.read_bytes()
    except OSError:
        return None
    if b"\0" in raw:
        return None
    return raw.decode("utf-8", errors="replace")


def check_path_rule(relative: str, findings: list[str]) -> None:
    if relative in ALLOWED_PATH_EXCEPTIONS:
        return
    for pattern in FORBIDDEN_PATH_PATTERNS:
        if pattern.search(relative):
            findings.append(
                f"{relative}:0: [SEC-001] a credential-bearing file must not be committed. "
                "Remove it from the repository and add it to .gitignore."
            )
            return


def check_content_rules(relative: str, text: str, findings: list[str]) -> None:
    for line_number, line in enumerate(text.splitlines(), start=1):
        if PRIVATE_KEY_PATTERN.search(line):
            findings.append(f"{relative}:{line_number}: [SEC-002] PEM private-key block.")

        for label, pattern in ISSUED_CREDENTIAL_PATTERNS.items():
            match = pattern.search(line)
            if match:
                # The matched value is never echoed: reporting a finding must not itself put the
                # credential into a CI log or artifact.
                findings.append(
                    f"{relative}:{line_number}: [SEC-003] {label} detected "
                    f"({len(match.group(0))} characters, value withheld)."
                )

        for pattern in (QUOTED_CREDENTIAL_PATTERN, ENV_CREDENTIAL_PATTERN):
            for match in pattern.finditer(line):
                value = match.group("value")
                if not looks_like_a_credential(value):
                    continue
                last_segment = match.group("name").lower().rstrip("_").rsplit("_", 1)[-1]
                if last_segment in NON_CREDENTIAL_NAME_SUFFIXES:
                    continue
                findings.append(
                    f"{relative}:{line_number}: [SEC-004] {match.group('name')!r} is assigned a "
                    f"credential-shaped value ({len(value)} characters, value withheld). Use a "
                    "placeholder here and supply the real value through the environment."
                )

        for match in URL_INLINE_CREDENTIAL_PATTERN.finditer(line):
            if not looks_like_a_credential(match.group("value")):
                continue
            findings.append(
                f"{relative}:{line_number}: [SEC-005] a connection URL carries an inline "
                f"credential ({len(match.group('value'))} characters, value withheld). Supply "
                "the credential through the environment instead."
            )


def check_repository(repo_root: Path) -> tuple[int, str, list[str]]:
    """Run every rule. Returns (exit_code, summary_line, findings)."""
    try:
        candidates = discover_candidate_files(repo_root)
    except SecretCheckError as exc:
        return 2, "", [f"Committed-credential check could not run: {exc}"]

    findings: list[str] = []
    scanned = 0
    skipped = 0

    for path in candidates:
        relative = path.relative_to(repo_root).as_posix()
        check_path_rule(relative, findings)

        if not path.exists():
            continue
        text = read_text_or_none(path)
        if text is None:
            skipped += 1
            continue
        scanned += 1
        check_content_rules(relative, text, findings)

    summary = (
        f"Committed-credential check: {len(candidates)} file(s) in the proposed tree "
        f"({GIT_DISCOVERY_LABEL}); {scanned} scanned as text, {skipped} skipped as binary or "
        "oversized."
    )
    return (1 if findings else 0), summary, findings


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--repo-root",
        default=str(DEFAULT_REPO_ROOT),
        help="Repository root to check (defaults to this script's repository).",
    )
    args = parser.parse_args(argv)

    exit_code, summary, findings = check_repository(Path(args.repo_root).resolve())

    if exit_code == 2:
        for finding in findings:
            print(finding, file=sys.stderr)
        return 2

    print(summary)

    if findings:
        print("", file=sys.stderr)
        print(f"{len(findings)} committed-credential finding(s):", file=sys.stderr)
        for finding in findings:
            print(f"  {finding}", file=sys.stderr)
        print(
            "\nEvery finding must be resolved by removing the credential, not by adding an "
            "exclusion. If a finding is genuinely a false positive, record the evidence in the "
            "TE-2CI acceptance document before changing this check.",
            file=sys.stderr,
        )
        return 1

    print("No committed-credential findings.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
