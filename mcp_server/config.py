from __future__ import annotations
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_ROOT = Path(os.environ.get("ANDROID_HARNESS_ARTIFACT_ROOT", ROOT / "artifacts")).expanduser().resolve()
PROJECT_ROOT = Path(os.environ.get("ANDROID_PROJECT_ROOT", os.getcwd())).expanduser().resolve()


def allowed_project_path(value: str, *, must_exist: bool = False) -> Path:
    candidate = Path(value).expanduser().resolve()
    roots = [ROOT, PROJECT_ROOT]
    roots.extend(Path(item).expanduser().resolve() for item in os.environ.get("ANDROID_HARNESS_PROJECT_ROOTS", "").split(os.pathsep) if item)
    if candidate != ROOT and not any(candidate == root or root in candidate.parents for root in roots):
        raise RuntimeError("Path must be inside the harness or configured Android project root")
    if must_exist and not candidate.exists():
        raise RuntimeError(f"Path not found: {candidate}")
    return candidate


def artifact_dir(value: str | None = None) -> Path:
    candidate = Path(value or (ARTIFACT_ROOT / "latest")).expanduser().resolve()
    if candidate != ARTIFACT_ROOT and ARTIFACT_ROOT not in candidate.parents:
        raise RuntimeError(f"Artifact directory must be inside {ARTIFACT_ROOT}")
    candidate.mkdir(parents=True, exist_ok=True)
    return candidate


def package_name(value: str) -> str:
    if not value or len(value) > 255 or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_." for c in value):
        raise RuntimeError("Invalid Android package name")
    return value
