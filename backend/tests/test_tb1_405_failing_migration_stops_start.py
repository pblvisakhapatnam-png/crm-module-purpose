"""TB-1 TB1-405 item 1: a migration that fails stops the backend's start at once, with its message.

Before, any failure of `alembic upgrade head` was retried 60 times, two seconds apart, as if the database were not
yet up. Now only reaching the database is retried; the migration runs once.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import pytest
from sqlalchemy.exc import OperationalError

from app import startup

BACKEND_ROOT = Path(__file__).resolve().parents[1]
FAKE_FAILURE = "tb1-405 probe: this migration fails"


def test_the_backend_stops_at_once_when_its_migration_fails(tmp_path: Path) -> None:
    """The backend's own entry point, on the test database, with an `alembic` that fails.

    The old start retried for two minutes, longer than the timeout below.
    """
    fake_alembic = tmp_path / "alembic"
    fake_alembic.write_text(f"#!/bin/sh\necho '{FAKE_FAILURE}' >&2\nexit 3\n", encoding="utf-8")
    fake_alembic.chmod(0o755)
    env = {
        **os.environ,
        "PATH": f"{tmp_path}{os.pathsep}{os.environ.get('PATH', '')}",
        "PYTHONDONTWRITEBYTECODE": "1",
    }

    started = time.monotonic()
    try:
        result = subprocess.run(
            [sys.executable, "-m", "app.startup"],
            cwd=BACKEND_ROOT,
            env=env,
            capture_output=True,
            text=True,
            timeout=60,
        )
    except subprocess.TimeoutExpired:
        pytest.fail("the backend went on retrying a migration that failed")

    output = result.stdout + result.stderr
    assert result.returncode != 0, output
    assert FAKE_FAILURE in output  # Alembic's own error reaches the log
    assert "alembic exit status 3" in output
    assert "does not retry" in output
    assert "attempt" not in output
    assert time.monotonic() - started < 30


class _Connection:
    def __enter__(self) -> _Connection:
        return self

    def __exit__(self, *exc_info: object) -> bool:
        return False

    def execute(self, statement: object) -> None:
        return None


class _Engine:
    """Refuses the first `refusals` connections, as a server still starting does."""

    def __init__(self, refusals: int) -> None:
        self.refusals = refusals
        self.connections = 0

    def connect(self) -> _Connection:
        self.connections += 1
        if self.connections <= self.refusals:
            raise OperationalError("SELECT 1", {}, ConnectionRefusedError("not accepting connections yet"))
        return _Connection()


@pytest.fixture
def recorded(monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    calls = SimpleNamespace(sleeps=[], runs=[], returncode=0)

    def run(command: list[str], check: bool) -> subprocess.CompletedProcess[str]:
        calls.runs.append(command)
        return subprocess.CompletedProcess(command, calls.returncode)

    monkeypatch.setattr(startup, "time", SimpleNamespace(sleep=calls.sleeps.append))
    monkeypatch.setattr(startup, "subprocess", SimpleNamespace(run=run, CalledProcessError=subprocess.CalledProcessError))
    return calls


def test_a_database_not_yet_up_is_waited_for_and_then_migrated_once(monkeypatch, recorded) -> None:
    engine = _Engine(refusals=2)
    monkeypatch.setattr(startup, "engine", engine)

    startup.wait_for_database_and_prepare()

    assert engine.connections == 3
    assert recorded.sleeps == [2, 2]
    assert recorded.runs == [["alembic", "upgrade", "head"]]


def test_a_failed_migration_is_not_retried(monkeypatch, recorded) -> None:
    monkeypatch.setattr(startup, "engine", _Engine(refusals=0))
    recorded.returncode = 1

    with pytest.raises(SystemExit, match="alembic exit status 1"):
        startup.wait_for_database_and_prepare()

    assert recorded.runs == [["alembic", "upgrade", "head"]]
    assert recorded.sleeps == []
