from __future__ import annotations

import os
from pathlib import Path

CODE_ROOT = Path(__file__).resolve().parents[1]
STATE_DIR_NAME = ".android_harness"


def project_root(value: str | None = None, *, must_exist: bool = True) -> Path:
    """Resolve the Android app root, never the harness source root by default."""
    candidate = Path(value or os.environ.get("ANDROID_PROJECT_ROOT", os.getcwd())).expanduser().resolve()
    if must_exist and not candidate.is_dir():
        raise RuntimeError(f"Android project root not found: {candidate}")
    if candidate == CODE_ROOT or CODE_ROOT in candidate.parents:
        raise RuntimeError("ANDROID_PROJECT_ROOT must point to the Android app repository, not the harness source repository")
    return candidate


def state_root(value: str | None = None) -> Path:
    root = project_root()
    state = root / STATE_DIR_NAME
    state.mkdir(parents=True, exist_ok=True)
    for name in ("flows", "screenshots", "screenshots/baseline", "screenshots/actual", "artifacts", "reports"):
        (state / name).mkdir(parents=True, exist_ok=True)
    return state


def project_path(value: str, *, must_exist: bool = False) -> Path:
    candidate = Path(value).expanduser()
    root = project_root()
    if not candidate.is_absolute():
        candidate = root / candidate
    candidate = candidate.resolve()
    if candidate != root and root not in candidate.parents:
        raise RuntimeError(f"Path must be inside Android project root: {root}")
    if must_exist and not candidate.exists():
        raise RuntimeError(f"Path not found: {candidate}")
    return candidate


def state_path(value: str | None = None, *, must_exist: bool = False) -> Path:
    state = state_root()
    candidate = Path(value or "artifacts/latest").expanduser()
    if not candidate.is_absolute():
        candidate = state / candidate
    candidate = candidate.resolve()
    if candidate != state and state not in candidate.parents:
        raise RuntimeError(f"Path must be inside {state}")
    if must_exist and not candidate.exists():
        raise RuntimeError(f"Path not found: {candidate}")
    candidate.parent.mkdir(parents=True, exist_ok=True)
    return candidate


def flow_path(value: str) -> Path:
    candidate = project_path(value)
    if candidate.suffix.lower() not in {".yaml", ".yml"}:
        raise RuntimeError("Maestro flow must be YAML")
    if STATE_DIR_NAME not in candidate.parts:
        candidate = state_root() / "flows" / candidate.name
    candidate.parent.mkdir(parents=True, exist_ok=True)
    return candidate


def package_name(value: str) -> str:
    if not value or len(value) > 255 or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_." for c in value):
        raise RuntimeError("Invalid Android package name")
    return value
