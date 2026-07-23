from __future__ import annotations

from pathlib import Path
from .config import project_root


def initialize(project_dir: str | None = None) -> dict:
    root = project_root(project_dir)
    state = root / ".android_harness"
    for name in ("flows", "screenshots/baseline", "screenshots/actual", "artifacts", "reports"):
        (state / name).mkdir(parents=True, exist_ok=True)
    readme = state / "README.md"
    if not readme.exists():
        readme.write_text("""# Android harness state\n\nGenerated runtime state for the Android MCP server.\n\n- `flows/` — Maestro flows\n- `screenshots/baseline/` — approved visual baselines\n- `screenshots/actual/` — current validation screenshots\n- `artifacts/` — logs and test artifacts\n- `reports/` — validation reports\n""")
    return {"project_root": str(root), "state_root": str(state), "directories": ["flows", "screenshots/baseline", "screenshots/actual", "artifacts", "reports"]}
