"""TB-1 TB1-400: `alembic revision --autogenerate` and `alembic check` are refused.

The models describe only some of the tables (`app/models_metadata.py`), so comparing them with the database
proposes dropping the rest. Each command runs on a copy of the migration environment in a temporary folder:
were the refusal gone, the revision Alembic writes would land in the copy, not among the real migrations.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[1]
RULE = "db/notes/migration-rules.md"


@pytest.fixture
def alembic_copy(tmp_path: Path) -> Path:
    shutil.copy(BACKEND_ROOT / "alembic.ini", tmp_path / "alembic.ini")
    shutil.copytree(BACKEND_ROOT / "alembic", tmp_path / "alembic", ignore=shutil.ignore_patterns("__pycache__"))
    return tmp_path


def _alembic(copy: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, "PYTHONPATH": str(BACKEND_ROOT), "PYTHONDONTWRITEBYTECODE": "1"}
    return subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        cwd=copy,
        env=env,
        capture_output=True,
        text=True,
        timeout=180,
    )


def _revision_files(copy: Path) -> list[str]:
    return sorted(path.name for path in (copy / "alembic" / "versions").glob("*.py"))


@pytest.mark.parametrize(
    "command",
    [["revision", "--autogenerate", "-m", "tb1 400 probe"], ["check"]],
    ids=["revision-autogenerate", "check"],
)
def test_comparing_the_models_with_the_database_is_refused(alembic_copy: Path, command: list[str]) -> None:
    before = _revision_files(alembic_copy)

    result = _alembic(alembic_copy, *command)

    output = result.stdout + result.stderr
    assert result.returncode != 0, output
    assert RULE in output, output
    assert _revision_files(alembic_copy) == before
