from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .manifest import is_valid_run_id

# backend/.smoke-runs -- local-only, ignored by git, holds one JSON file per seed run
# so `cleanup --run-id ...` and `list-runs` work without the caller keeping the manifest.
RUNS_DIR = Path(__file__).resolve().parents[2] / ".smoke-runs"


def runs_dir() -> Path:
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    return RUNS_DIR


def manifest_path_for_run(run_id: str) -> Path:
    if not is_valid_run_id(run_id):
        raise ValueError(f"Refusing to build a path for an unsafe/malformed run id: {run_id!r}")
    return runs_dir() / f"{run_id}.json"


def save_manifest(manifest: dict[str, Any]) -> Path:
    run_id = manifest.get("run_id")
    if not is_valid_run_id(run_id):
        raise ValueError(f"Refusing to persist a manifest with an unsafe/malformed run id: {run_id!r}")
    path = manifest_path_for_run(run_id)
    path.write_text(json.dumps(manifest, indent=2, default=str), encoding="utf-8")
    return path


def load_manifest(run_id: str) -> dict[str, Any]:
    path = manifest_path_for_run(run_id)
    if not path.exists():
        raise FileNotFoundError(
            f"No local manifest found for run id {run_id!r} at {path}. "
            "Pass --manifest <path> instead if you have the manifest file from elsewhere."
        )
    return json.loads(path.read_text(encoding="utf-8"))


def list_runs() -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for path in sorted(runs_dir().glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        if not isinstance(data, dict):
            continue
        results.append(
            {
                "run_id": data.get("run_id"),
                "scenario": data.get("scenario"),
                "created_at": data.get("created_at"),
                "manifest_path": str(path),
            }
        )
    return results
