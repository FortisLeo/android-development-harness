#!/usr/bin/env python3
"""Local MCP server for safe Android device testing via ADB.

Transport: MCP JSON-RPC over stdin/stdout. Logs go to stderr.
The server intentionally operates only on the selected ADB device and never
wipes a device or touches unrelated applications.
"""
from __future__ import annotations

import base64
import datetime as dt
import json
import os
import pathlib
import shutil
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parents[1]
ARTIFACT_ROOT = pathlib.Path(os.environ.get("ANDROID_HARNESS_ARTIFACT_ROOT", ROOT / "artifacts")).resolve()
PROJECT_ROOT = pathlib.Path(os.environ.get("ANDROID_PROJECT_ROOT", os.getcwd())).resolve()


def allowed_project_path(path: str, *, must_exist: bool = False) -> pathlib.Path:
    candidate = pathlib.Path(path).expanduser().resolve()
    allowed = [ROOT, PROJECT_ROOT]
    extra = os.environ.get("ANDROID_HARNESS_PROJECT_ROOTS", "")
    allowed.extend(pathlib.Path(item).expanduser().resolve() for item in extra.split(os.pathsep) if item)
    if candidate != ROOT and not any(candidate == parent or parent in candidate.parents for parent in allowed):
        raise RuntimeError("Path must be inside the harness or configured Android project root")
    if must_exist and not candidate.exists():
        raise RuntimeError(f"Path not found: {candidate}")
    return candidate


def log(message: str) -> None:
    print(f"[android-mcp] {message}", file=sys.stderr, flush=True)


def result(value: Any) -> dict[str, Any]:
    return {"content": [{"type": "text", "text": json.dumps(value, indent=2, ensure_ascii=False)}]}


def error(message: str) -> dict[str, Any]:
    return {"isError": True, "content": [{"type": "text", "text": message}]}


def run(command: list[str], timeout: int = 30, *, binary: bool = False) -> str | bytes:
    log("running " + " ".join(command))
    try:
        completed = subprocess.run(command, capture_output=True, timeout=timeout, check=False)
    except FileNotFoundError as exc:
        raise RuntimeError(f"Command not found: {exc.filename}") from exc
    output = completed.stdout if binary else completed.stdout.decode("utf-8", "replace")
    if completed.returncode:
        stderr = completed.stderr.decode("utf-8", "replace")
        raise RuntimeError(f"Command failed ({completed.returncode}): {' '.join(command)}\n{stderr[-4000:]}")
    return output


def adb() -> list[str]:
    sdk = pathlib.Path(os.environ.get("ANDROID_HOME", os.environ.get("ANDROID_SDK_ROOT", "")))
    executable = sdk / "platform-tools" / "adb" if sdk else pathlib.Path("adb")
    command = [str(executable)] if executable.exists() else ["adb"]
    serial = os.environ.get("ANDROID_SERIAL", "").strip()
    if serial:
        command += ["-s", serial]
    return command


def require_device() -> None:
    output = run(adb() + ["get-state"], timeout=10).strip()
    if output != "device":
        raise RuntimeError("No ready Android device. Connect USB debugging and accept the RSA prompt.")


def safe_artifact_dir(path: str | None) -> pathlib.Path:
    candidate = pathlib.Path(path or (ARTIFACT_ROOT / dt.datetime.now().strftime("%Y%m%d-%H%M%S"))).expanduser().resolve()
    if candidate != ARTIFACT_ROOT and ARTIFACT_ROOT not in candidate.parents:
        raise RuntimeError(f"Artifact directory must be inside {ARTIFACT_ROOT}")
    candidate.mkdir(parents=True, exist_ok=True)
    return candidate


def package_name(value: str) -> str:
    if not value or len(value) > 255 or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_." for c in value):
        raise RuntimeError("Invalid Android package name")
    return value


def safe_path(path: str, *, must_exist: bool = False) -> pathlib.Path:
    candidate = pathlib.Path(path).expanduser().resolve()
    if must_exist and not candidate.exists():
        raise RuntimeError(f"Path not found: {candidate}")
    return candidate


def maestro_executable() -> str:
    executable = shutil.which("maestro")
    if not executable:
        raise RuntimeError("Maestro CLI not found. Install it and ensure `maestro` is on PATH.")
    return executable


def run_maestro(flow_path: str, *, output_dir: str | None = None, debug: bool = False) -> dict[str, Any]:
    require_device()
    flow = allowed_project_path(flow_path, must_exist=True)
    if flow.suffix.lower() not in {".yaml", ".yml"}:
        raise RuntimeError("Maestro flow must be a .yaml or .yml file")
    command = [maestro_executable(), "test", str(flow)]
    working_dir = None
    if output_dir:
        directory = safe_artifact_dir(output_dir)
        working_dir = str(directory)
        command += ["--format", "junit", "--output", str(directory / "maestro-results.xml")]
    if debug:
        command.append("--debug-output")
    completed = subprocess.run(command, capture_output=True, text=True, timeout=600, check=False, cwd=working_dir)
    output = (completed.stdout + "\n" + completed.stderr).strip()
    return {"pass": completed.returncode == 0, "flow": str(flow), "exit_code": completed.returncode, "output": output[-12000:]}


def create_maestro_flow(flow_path: str, content: str, *, overwrite: bool = False) -> dict[str, Any]:
    flow = allowed_project_path(flow_path)
    if flow.suffix.lower() not in {".yaml", ".yml"}:
        raise RuntimeError("Maestro flow must be a .yaml or .yml file")
    if flow.exists() and not overwrite:
        raise RuntimeError(f"Flow exists; set overwrite=true to replace it: {flow}")
    if not content.strip():
        raise RuntimeError("Flow content cannot be empty")
    if "takeScreenshot:" not in content:
        raise RuntimeError("Flow must include at least one takeScreenshot step so every important screen can have a baseline")
    flow.parent.mkdir(parents=True, exist_ok=True)
    flow.write_text(content)
    return {"path": str(flow), "bytes": flow.stat().st_size, "screenshot_steps": content.count("takeScreenshot:")}


def create_and_run_maestro_flow(flow_path: str, content: str, *, overwrite: bool = False, output_dir: str | None = None) -> dict[str, Any]:
    require_device()
    created = create_maestro_flow(flow_path, content, overwrite=overwrite)
    executed = run_maestro(flow_path, output_dir=output_dir, debug=True)
    return {"created": created, "execution": executed}


def create_baseline_from_flow(flow_path: str, package: str, baseline_dir: str, *, reset_app: bool = True) -> dict[str, Any]:
    require_device()
    package = package_name(package)
    baseline = safe_artifact_dir(baseline_dir)
    baseline.mkdir(parents=True, exist_ok=True)
    if reset_app:
        run(adb() + ["shell", "pm", "clear", package], timeout=30)
    flow_result = run_maestro(flow_path, output_dir=str(baseline / "maestro"))
    if not flow_result["pass"]:
        raise RuntimeError("Maestro flow failed; no baseline was created.\n" + flow_result["output"])
    screenshot = baseline / "flow-final.png"
    screenshot.write_bytes(run(adb() + ["exec-out", "screencap", "-p"], timeout=30, binary=True))
    accessibility = baseline / "flow-final-accessibility.xml"
    run(adb() + ["shell", "uiautomator", "dump", "/sdcard/window.xml"], timeout=30)
    accessibility.write_bytes(run(adb() + ["exec-out", "cat", "/sdcard/window.xml"], timeout=30, binary=True))
    return {"pass": True, "flow": str(safe_path(flow_path)), "baseline_dir": str(baseline), "screenshots": [str(screenshot)], "accessibility": [str(accessibility)], "maestro": flow_result}

def build_project(project_dir: str, *, tasks: list[str] | None = None, timeout: int = 900) -> dict[str, Any]:
    project = allowed_project_path(project_dir, must_exist=True)
    wrapper = project / ("gradlew.bat" if os.name == "nt" else "gradlew")
    if not wrapper.is_file():
        raise RuntimeError(f"Gradle wrapper not found: {wrapper}")
    if os.name != "nt" and not os.access(wrapper, os.X_OK):
        raise RuntimeError(f"Gradle wrapper is not executable: {wrapper}")
    selected = tasks or ["assembleDebug", "test"]
    allowed_tasks = {"assembleDebug", "test", "lint", "check", "testDebugUnitTest", "assembleDebugAndroidTest"}
    if not selected or any(task not in allowed_tasks for task in selected):
        raise RuntimeError(f"Unsupported Gradle task. Allowed tasks: {sorted(allowed_tasks)}")
    completed = subprocess.run([str(wrapper), *selected], cwd=project, capture_output=True, text=True, timeout=timeout, check=False)
    output = (completed.stdout + "\n" + completed.stderr).strip()
    return {"pass": completed.returncode == 0, "project": str(project), "tasks": selected, "exit_code": completed.returncode, "output": output[-16000:]}


def find_debug_apk(project_dir: str) -> dict[str, Any]:
    project = allowed_project_path(project_dir, must_exist=True)
    apks = sorted((project / "app" / "build" / "outputs" / "apk").glob("**/*-debug.apk"))
    if not apks:
        raise RuntimeError(f"No debug APK found under {project / 'app' / 'build' / 'outputs' / 'apk'}")
    return {"apk_path": str(apks[-1]), "candidates": [str(path) for path in apks]}


def full_ui_validation(project_dir: str, apk_path: str, package: str, flow_path: str, artifact_dir: str, *, baseline_dir: str | None = None, reset_app: bool = True) -> dict[str, Any]:
    """Final gate: only call after coding/build checks are complete."""
    require_device()
    package = package_name(package)
    apk = allowed_project_path(apk_path, must_exist=True)
    flow = allowed_project_path(flow_path, must_exist=True)
    build_result = build_project(project_dir, tasks=["test", "assembleDebug"])
    if not build_result["pass"]:
        raise RuntimeError("Project checks failed; UI validation was not started.\n" + build_result["output"])
    run(adb() + ["install", "-r", str(apk)], timeout=180)
    if reset_app:
        run(adb() + ["shell", "pm", "clear", package], timeout=30)
    run(adb() + ["shell", "monkey", "-p", package, "1"], timeout=30)
    maestro = run_maestro(str(flow), output_dir=str(safe_artifact_dir(artifact_dir) / "maestro"), debug=True)
    artifacts = collect(package, artifact_dir)
    if not maestro["pass"]:
        raise RuntimeError("Maestro validation failed after project checks passed.\n" + maestro["output"])
    baseline = None
    if baseline_dir:
        baseline = create_baseline_from_flow(str(flow), package, baseline_dir, reset_app=False)
    return {"pass": True, "phase": "final-ui-validation", "build": build_result, "maestro": maestro, "artifacts": artifacts, "baseline": baseline}


def collect(package: str, artifact_dir: str | None = None) -> dict[str, Any]:
    require_device()
    package = package_name(package)
    directory = safe_artifact_dir(artifact_dir)
    (directory / "collected-at.txt").write_text(dt.datetime.now(dt.timezone.utc).isoformat())
    operations: list[tuple[str, list[str], bool]] = [
        ("screenshot.png", adb() + ["exec-out", "screencap", "-p"], True),
        ("windows.txt", adb() + ["shell", "dumpsys", "window", "windows"], False),
        ("properties.txt", adb() + ["shell", "getprop"], False),
        ("package.txt", adb() + ["shell", "dumpsys", "package", package], False),
        ("meminfo.txt", adb() + ["shell", "dumpsys", "meminfo", package], False),
        ("logcat.txt", adb() + ["logcat", "-d", "-v", "threadtime", "-t", "5000"], False),
    ]
    run(adb() + ["shell", "uiautomator", "dump", "/sdcard/window.xml"], timeout=30)
    try:
        xml = run(adb() + ["exec-out", "cat", "/sdcard/window.xml"], timeout=30, binary=True)
        (directory / "accessibility.xml").write_bytes(xml if isinstance(xml, bytes) else xml.encode())
    except RuntimeError:
        (directory / "accessibility.xml").write_text("")
    for filename, command, binary in operations:
        try:
            output = run(command, timeout=30, binary=binary)
            (directory / filename).write_bytes(output if isinstance(output, bytes) else output.encode())
        except RuntimeError as exc:
            (directory / filename).write_text(f"collection failed: {exc}\\n")
    metadata = {"package": package, "serial": os.environ.get("ANDROID_SERIAL"), "collected_at": dt.datetime.now(dt.timezone.utc).isoformat(), "files": sorted(p.name for p in directory.iterdir())}
    (directory / "metadata.json").write_text(json.dumps(metadata, indent=2))
    return {"artifact_dir": str(directory), "files": metadata["files"]}


TOOLS = {
    "android_status": {"description": "List connected Android devices and selected device metadata.", "inputSchema": {"type": "object", "properties": {}}},
    "android_install_apk": {"description": "Install an APK on the selected device. Does not uninstall or wipe apps.", "inputSchema": {"type": "object", "properties": {"apk_path": {"type": "string"}}, "required": ["apk_path"]}},
    "android_launch_app": {"description": "Launch an Android package.", "inputSchema": {"type": "object", "properties": {"package": {"type": "string"}}, "required": ["package"]}},
    "android_reset_app": {"description": "Clear data for the target app only.", "inputSchema": {"type": "object", "properties": {"package": {"type": "string"}}, "required": ["package"]}},
    "android_screenshot": {"description": "Capture a PNG screenshot from the selected device.", "inputSchema": {"type": "object", "properties": {"output_path": {"type": "string"}}, "required": ["output_path"]}},
    "android_dump_accessibility": {"description": "Dump the current UI Automator accessibility hierarchy as XML.", "inputSchema": {"type": "object", "properties": {"output_path": {"type": "string"}}, "required": ["output_path"]}},
    "android_collect_artifacts": {"description": "Collect screenshot, accessibility XML, logcat, device properties, window state, package and memory data.", "inputSchema": {"type": "object", "properties": {"package": {"type": "string"}, "artifact_dir": {"type": "string"}}, "required": ["package"]}},
    "android_logcat": {"description": "Read recent device logcat, optionally filtered by package text.", "inputSchema": {"type": "object", "properties": {"lines": {"type": "integer", "default": 500}, "contains": {"type": "string"}}}},
    "android_tap": {"description": "Tap a screen coordinate on the selected device.", "inputSchema": {"type": "object", "properties": {"x": {"type": "integer"}, "y": {"type": "integer"}}, "required": ["x", "y"]}},
    "android_input_text": {"description": "Input text using ADB shell quoting.", "inputSchema": {"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"]}},
    "android_swipe": {"description": "Swipe between two screen coordinates.", "inputSchema": {"type": "object", "properties": {"x1": {"type": "integer"}, "y1": {"type": "integer"}, "x2": {"type": "integer"}, "y2": {"type": "integer"}, "duration_ms": {"type": "integer", "default": 300}}, "required": ["x1", "y1", "x2", "y2"]}},
    "android_press_back": {"description": "Press the Android back button.", "inputSchema": {"type": "object", "properties": {}}},
    "android_assert_accessibility": {"description": "Assert text, content descriptions, or resource IDs exist in a collected accessibility XML file.", "inputSchema": {"type": "object", "properties": {"xml_path": {"type": "string"}, "text": {"type": "array", "items": {"type": "string"}}, "content_desc": {"type": "array", "items": {"type": "string"}}, "resource_id": {"type": "array", "items": {"type": "string"}}}, "required": ["xml_path"]}},
    "android_compare_screenshots": {"description": "Compare two screenshots with an exact byte comparison and report dimensions/file sizes.", "inputSchema": {"type": "object", "properties": {"expected_path": {"type": "string"}, "actual_path": {"type": "string"}}, "required": ["expected_path", "actual_path"]}},
    "android_run_maestro_flow": {"description": "Run a Maestro YAML flow on the connected device and optionally write JUnit results.", "inputSchema": {"type": "object", "properties": {"flow_path": {"type": "string"}, "output_dir": {"type": "string"}, "debug": {"type": "boolean"}}, "required": ["flow_path"]}},
    "android_create_maestro_flow": {"description": "Create a Maestro YAML flow and require screenshot steps for baseline coverage.", "inputSchema": {"type": "object", "properties": {"flow_path": {"type": "string"}, "content": {"type": "string"}, "overwrite": {"type": "boolean"}}, "required": ["flow_path", "content"]}},
    "android_create_and_run_maestro_flow": {"description": "Create/update a Maestro flow for a new UI feature and run it immediately on the connected device. Fails if no device, Maestro, or screenshot step is present.", "inputSchema": {"type": "object", "properties": {"flow_path": {"type": "string"}, "content": {"type": "string"}, "overwrite": {"type": "boolean"}, "output_dir": {"type": "string"}}, "required": ["flow_path", "content"]}},
    "android_create_baseline_from_flow": {"description": "Require a connected device, run a Maestro flow, and save baseline final screenshot/accessibility artifacts. Fails without a device or if the flow fails.", "inputSchema": {"type": "object", "properties": {"flow_path": {"type": "string"}, "package": {"type": "string"}, "baseline_dir": {"type": "string"}, "reset_app": {"type": "boolean"}}, "required": ["flow_path", "package", "baseline_dir"]}},
    "android_build_project": {"description": "Run allowlisted Gradle wrapper tasks. This is a coding/build phase operation and does not run UI/device validation.", "inputSchema": {"type": "object", "properties": {"project_dir": {"type": "string"}, "tasks": {"type": "array", "items": {"type": "string"}}, "timeout": {"type": "integer"}}, "required": ["project_dir"]}},
    "android_find_debug_apk": {"description": "Find the built debug APK in an Android project.", "inputSchema": {"type": "object", "properties": {"project_dir": {"type": "string"}}, "required": ["project_dir"]}},
    "android_run_final_ui_validation": {"description": "Final gate only: after coding and project checks are complete, build checks, install APK, run Maestro, collect screenshot/accessibility/logcat artifacts, and optionally create baselines. Never use this during implementation iterations.", "inputSchema": {"type": "object", "properties": {"project_dir": {"type": "string"}, "apk_path": {"type": "string"}, "package": {"type": "string"}, "flow_path": {"type": "string"}, "artifact_dir": {"type": "string"}, "baseline_dir": {"type": "string"}, "reset_app": {"type": "boolean"}}, "required": ["project_dir", "apk_path", "package", "flow_path", "artifact_dir"]}},
}


def dispatch(name: str, args: dict[str, Any]) -> dict[str, Any]:
    require_device() if name not in {"android_compare_screenshots", "android_assert_accessibility"} else None
    if name == "android_status":
        return result({"devices": run(adb()[:1] + ["devices", "-l"], timeout=10)})
    if name == "android_install_apk":
        path = pathlib.Path(args["apk_path"]).expanduser().resolve()
        if not path.is_file(): raise RuntimeError(f"APK not found: {path}")
        return result({"output": run(adb() + ["install", "-r", str(path)], timeout=180)})
    if name == "android_launch_app":
        package = package_name(args["package"])
        return result({"package": package, "output": run(adb() + ["shell", "monkey", "-p", package, "1"], timeout=30)})
    if name == "android_reset_app":
        package = package_name(args["package"])
        return result({"package": package, "output": run(adb() + ["shell", "pm", "clear", package], timeout=30)})
    if name == "android_screenshot":
        path = pathlib.Path(args["output_path"]).expanduser().resolve(); path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(run(adb() + ["exec-out", "screencap", "-p"], timeout=30, binary=True))
        return result({"path": str(path), "bytes": path.stat().st_size})
    if name == "android_dump_accessibility":
        path = pathlib.Path(args["output_path"]).expanduser().resolve(); path.parent.mkdir(parents=True, exist_ok=True)
        run(adb() + ["shell", "uiautomator", "dump", "/sdcard/window.xml"], timeout=30)
        raw = run(adb() + ["exec-out", "cat", "/sdcard/window.xml"], timeout=30, binary=True); path.write_bytes(raw)
        return result({"path": str(path), "bytes": path.stat().st_size})
    if name == "android_collect_artifacts": return result(collect(args["package"], args.get("artifact_dir")))
    if name == "android_logcat":
        out = run(adb() + ["logcat", "-d", "-v", "threadtime", "-t", str(min(int(args.get("lines", 500)), 5000))], timeout=30)
        contains = args.get("contains"); out = "\n".join(line for line in out.splitlines() if contains in line) if contains else out
        return result({"logcat": out})
    if name == "android_tap": return result({"output": run(adb() + ["shell", "input", "tap", str(int(args["x"])), str(int(args["y"]))])})
    if name == "android_input_text": return result({"output": run(adb() + ["shell", "input", "text", args["text"]])})
    if name == "android_swipe": return result({"output": run(adb() + ["shell", "input", "swipe", *[str(int(args[k])) for k in ("x1", "y1", "x2", "y2")], str(int(args.get("duration_ms", 300)))])})
    if name == "android_press_back": return result({"output": run(adb() + ["shell", "input", "keyevent", "4"])})
    if name == "android_assert_accessibility":
        path = pathlib.Path(args["xml_path"]).expanduser().resolve(); root = ET.parse(path).getroot(); nodes = list(root.iter())
        missing = []
        for key, attr in (("text", "text"), ("content_desc", "content-desc"), ("resource_id", "resource-id")):
            for value in args.get(key, []):
                if value not in [node.attrib.get(attr, "") for node in nodes]: missing.append(f"{attr}={value!r}")
        if missing: return error("Missing accessibility nodes: " + ", ".join(missing))
        return result({"pass": True, "nodes": len(nodes)})
    if name == "android_compare_screenshots":
        expected = pathlib.Path(args["expected_path"]).expanduser().resolve(); actual = pathlib.Path(args["actual_path"]).expanduser().resolve()
        if not expected.is_file() or not actual.is_file(): raise RuntimeError("Both screenshot paths must exist")
        same = expected.read_bytes() == actual.read_bytes()
        return result({"pass": same, "exact_match": same, "expected_bytes": expected.stat().st_size, "actual_bytes": actual.stat().st_size})
    if name == "android_run_maestro_flow":
        return result(run_maestro(args["flow_path"], output_dir=args.get("output_dir"), debug=bool(args.get("debug", False))))
    if name == "android_create_maestro_flow":
        return result(create_maestro_flow(args["flow_path"], args["content"], overwrite=bool(args.get("overwrite", False))))
    if name == "android_create_and_run_maestro_flow":
        return result(create_and_run_maestro_flow(args["flow_path"], args["content"], overwrite=bool(args.get("overwrite", False)), output_dir=args.get("output_dir")))
    if name == "android_create_baseline_from_flow":
        return result(create_baseline_from_flow(args["flow_path"], args["package"], args["baseline_dir"], reset_app=bool(args.get("reset_app", True))))
    if name == "android_build_project":
        return result(build_project(args["project_dir"], tasks=args.get("tasks"), timeout=min(int(args.get("timeout", 900)), 1800)))
    if name == "android_find_debug_apk":
        return result(find_debug_apk(args["project_dir"]))
    if name == "android_run_final_ui_validation":
        return result(full_ui_validation(args["project_dir"], args["apk_path"], args["package"], args["flow_path"], args["artifact_dir"], baseline_dir=args.get("baseline_dir"), reset_app=bool(args.get("reset_app", True))))
    raise RuntimeError(f"Unknown tool: {name}")


def main() -> None:
    for line in sys.stdin:
        try:
            request = json.loads(line)
            method = request.get("method")
            request_id = request.get("id")
            if method == "initialize":
                response = {"protocolVersion": "2024-11-05", "capabilities": {"tools": {}}, "serverInfo": {"name": "android-agent-harness", "version": "0.1.0"}}
            elif method == "notifications/initialized":
                continue
            elif method == "tools/list":
                response = {"tools": [{"name": name, **spec} for name, spec in TOOLS.items()]}
            elif method == "tools/call":
                params = request.get("params", {}); response = dispatch(params["name"], params.get("arguments", {}))
            else:
                response = {"error": {"code": -32601, "message": f"Method not found: {method}"}}
            if request_id is not None:
                print(json.dumps({"jsonrpc": "2.0", "id": request_id, "result": response}), flush=True)
        except Exception as exc:
            log(f"error: {exc}")
            if "request_id" in locals() and request_id is not None:
                print(json.dumps({"jsonrpc": "2.0", "id": request_id, "error": {"code": -32000, "message": str(exc)}}), flush=True)


if __name__ == "__main__":
    main()
