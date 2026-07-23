from __future__ import annotations

import shutil
import subprocess
from .adb_client import command, run, require_device
from .config import flow_path, package_name, project_path, state_path


def executable() -> str:
    path = shutil.which("maestro")
    if not path:
        raise RuntimeError("Maestro CLI not found. Install it and ensure maestro is on PATH.")
    return path


def run_flow(path: str, output_dir: str | None = None, debug: bool = False) -> dict:
    require_device()
    flow = flow_path(path)
    if not flow.is_file():
        raise RuntimeError(f"Flow not found: {flow}")
    command_line = [executable(), "test", str(flow)]
    working_dir = None
    if output_dir:
        out = state_path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        working_dir = str(out)
        command_line += ["--format", "junit", "--output", str(out / "maestro-results.xml")]
    if debug:
        command_line.append("--debug-output")
    completed = subprocess.run(command_line, capture_output=True, text=True, timeout=600, cwd=working_dir, check=False)
    output = (completed.stdout + "\n" + completed.stderr).strip()
    return {"pass": completed.returncode == 0, "flow": str(flow), "exit_code": completed.returncode, "output": output[-12000:]}


def create_flow(path: str, content: str, overwrite: bool = False) -> dict:
    flow = flow_path(path)
    if not content.strip() or "takeScreenshot:" not in content:
        raise RuntimeError("Flow must be non-empty YAML with takeScreenshot checkpoints")
    if flow.exists() and not overwrite:
        raise RuntimeError(f"Flow exists: {flow}")
    flow.write_text(content)
    return {"path": str(flow), "bytes": flow.stat().st_size, "screenshot_steps": content.count("takeScreenshot:")}


def create_and_run(path: str, content: str, overwrite: bool = False, output_dir: str | None = None) -> dict:
    require_device()
    return {"created": create_flow(path, content, overwrite), "execution": run_flow(path, output_dir, True)}


def baseline(flow: str, package: str, destination: str, reset: bool = True) -> dict:
    require_device()
    package = package_name(package)
    out = state_path(destination)
    if reset:
        run(command() + ["shell", "pm", "clear", package])
    result = run_flow(flow, str(out / "maestro"), True)
    if not result["pass"]:
        raise RuntimeError("Maestro flow failed; no baseline created\n" + result["output"])
    (out / "flow-final.png").write_bytes(run(command() + ["exec-out", "screencap", "-p"], binary=True))
    run(command() + ["shell", "uiautomator", "dump", "/sdcard/window.xml"])
    (out / "flow-final-accessibility.xml").write_bytes(run(command() + ["exec-out", "cat", "/sdcard/window.xml"], binary=True))
    return {"pass": True, "baseline_dir": str(out), "maestro": result}
