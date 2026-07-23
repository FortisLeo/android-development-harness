#!/usr/bin/env python3
"""Local MCP server entry point for Android build and final UI validation."""
from __future__ import annotations
import sys
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from mcp_server.adb_client import command, run, require_device
    from mcp_server.artifacts import accessibility, collect, screenshot
    from mcp_server.build import build, debug_apk
    from mcp_server.config import project_path, state_path, package_name
    from mcp_server.maestro import baseline, create_and_run, create_flow, run_flow
    from mcp_server.project_state import initialize as initialize_state
    from mcp_server.protocol import error, result, serve
else:
    from .adb_client import command, run, require_device
    from .artifacts import accessibility, collect, screenshot
    from .build import build, debug_apk
    from .config import project_path, state_path, package_name
    from .maestro import baseline, create_and_run, create_flow, run_flow
    from .project_state import initialize as initialize_state
    from .protocol import error, result, serve

TOOLS = {
    "android_initialize_project_state": {"description": "Create .android_harness in the Android project root with flows, screenshots, artifacts, and reports directories.", "inputSchema": {"type": "object", "properties": {"project_dir": {"type": "string"}}}},
    "android_status": {"description": "List connected Android devices.", "inputSchema": {"type": "object", "properties": {}}},
    "android_install_apk": {"description": "Install an APK on the selected device.", "inputSchema": {"type": "object", "properties": {"apk_path": {"type": "string"}}, "required": ["apk_path"]}},
    "android_launch_app": {"description": "Launch an Android package.", "inputSchema": {"type": "object", "properties": {"package": {"type": "string"}}, "required": ["package"]}},
    "android_reset_app": {"description": "Clear data for the target app only.", "inputSchema": {"type": "object", "properties": {"package": {"type": "string"}}, "required": ["package"]}},
    "android_screenshot": {"description": "Capture a PNG screenshot.", "inputSchema": {"type": "object", "properties": {"output_path": {"type": "string"}}, "required": ["output_path"]}},
    "android_dump_accessibility": {"description": "Dump UI Automator accessibility XML.", "inputSchema": {"type": "object", "properties": {"output_path": {"type": "string"}}, "required": ["output_path"]}},
    "android_collect_artifacts": {"description": "Collect screenshot, accessibility XML, logcat, and device metadata.", "inputSchema": {"type": "object", "properties": {"package": {"type": "string"}, "artifact_dir": {"type": "string"}}, "required": ["package"]}},
    "android_logcat": {"description": "Read recent logcat, optionally filtered.", "inputSchema": {"type": "object", "properties": {"lines": {"type": "integer"}, "contains": {"type": "string"}}}},
    "android_tap": {"description": "Tap coordinates.", "inputSchema": {"type": "object", "properties": {"x": {"type": "integer"}, "y": {"type": "integer"}}, "required": ["x", "y"]}},
    "android_input_text": {"description": "Input text.", "inputSchema": {"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"]}},
    "android_swipe": {"description": "Swipe between coordinates.", "inputSchema": {"type": "object", "properties": {"x1": {"type": "integer"}, "y1": {"type": "integer"}, "x2": {"type": "integer"}, "y2": {"type": "integer"}, "duration_ms": {"type": "integer"}}, "required": ["x1", "y1", "x2", "y2"]}},
    "android_press_back": {"description": "Press Android Back.", "inputSchema": {"type": "object", "properties": {}}},
    "android_assert_accessibility": {"description": "Assert accessibility XML values.", "inputSchema": {"type": "object", "properties": {"xml_path": {"type": "string"}, "text": {"type": "array", "items": {"type": "string"}}, "content_desc": {"type": "array", "items": {"type": "string"}}, "resource_id": {"type": "array", "items": {"type": "string"}}}, "required": ["xml_path"]}},
    "android_compare_screenshots": {"description": "Compare screenshot bytes.", "inputSchema": {"type": "object", "properties": {"expected_path": {"type": "string"}, "actual_path": {"type": "string"}}, "required": ["expected_path", "actual_path"]}},
    "android_run_maestro_flow": {"description": "Run a Maestro YAML flow.", "inputSchema": {"type": "object", "properties": {"flow_path": {"type": "string"}, "output_dir": {"type": "string"}, "debug": {"type": "boolean"}}, "required": ["flow_path"]}},
    "android_create_maestro_flow": {"description": "Create a Maestro flow with screenshot checkpoints.", "inputSchema": {"type": "object", "properties": {"flow_path": {"type": "string"}, "content": {"type": "string"}, "overwrite": {"type": "boolean"}}, "required": ["flow_path", "content"]}},
    "android_create_and_run_maestro_flow": {"description": "Create and immediately run a Maestro flow on a connected device.", "inputSchema": {"type": "object", "properties": {"flow_path": {"type": "string"}, "content": {"type": "string"}, "overwrite": {"type": "boolean"}, "output_dir": {"type": "string"}}, "required": ["flow_path", "content"]}},
    "android_create_baseline_from_flow": {"description": "Run a passing Maestro flow and create baseline artifacts.", "inputSchema": {"type": "object", "properties": {"flow_path": {"type": "string"}, "package": {"type": "string"}, "baseline_dir": {"type": "string"}, "reset_app": {"type": "boolean"}}, "required": ["flow_path", "package", "baseline_dir"]}},
    "android_build_project": {"description": "Run allowlisted Gradle tasks during the coding phase; no device UI testing.", "inputSchema": {"type": "object", "properties": {"project_dir": {"type": "string"}, "tasks": {"type": "array", "items": {"type": "string"}}, "timeout": {"type": "integer"}}, "required": ["project_dir"]}},
    "android_find_debug_apk": {"description": "Find a built debug APK.", "inputSchema": {"type": "object", "properties": {"project_dir": {"type": "string"}}, "required": ["project_dir"]}},
    "android_run_final_ui_validation": {"description": "Final gate after coding checks: build, install, run Maestro, collect artifacts, and optionally create baselines.", "inputSchema": {"type": "object", "properties": {"project_dir": {"type": "string"}, "apk_path": {"type": "string"}, "package": {"type": "string"}, "flow_path": {"type": "string"}, "artifact_dir": {"type": "string"}, "baseline_dir": {"type": "string"}, "reset_app": {"type": "boolean"}}, "required": ["project_dir", "apk_path", "package", "flow_path", "artifact_dir"]}},
}


def dispatch(name: str, args: dict[str, Any]) -> dict[str, Any]:
    if name == "android_initialize_project_state":
        return result(initialize_state(args.get("project_dir")))
    if name == "android_status":
        return result({"devices": run([command()[0], "devices", "-l"], timeout=10)})
    if name not in {"android_compare_screenshots", "android_assert_accessibility", "android_build_project", "android_find_debug_apk", "android_create_maestro_flow", "android_initialize_project_state"}:
        require_device()
    if name == "android_install_apk":
        apk = project_path(args["apk_path"], must_exist=True); return result({"output": run(command()+["install", "-r", str(apk)], timeout=180)})
    if name == "android_launch_app":
        package = package_name(args["package"]); return result({"package": package, "output": run(command()+["shell", "monkey", "-p", package, "1"])})
    if name == "android_reset_app":
        package = package_name(args["package"]); return result({"package": package, "output": run(command()+["shell", "pm", "clear", package])})
    if name == "android_screenshot": return result(screenshot(args["output_path"]))
    if name == "android_dump_accessibility": return result(accessibility(args["output_path"]))
    if name == "android_collect_artifacts": return result(collect(args["package"], args.get("artifact_dir")))
    if name == "android_logcat":
        out = run(command()+["logcat", "-d", "-v", "threadtime", "-t", str(min(int(args.get("lines", 500)), 5000))]); needle=args.get("contains")
        return result({"logcat": "\n".join(line for line in out.splitlines() if needle in line) if needle else out})
    if name == "android_tap": return result({"output": run(command()+["shell", "input", "tap", str(int(args["x"])), str(int(args["y"]))])})
    if name == "android_input_text": return result({"output": run(command()+["shell", "input", "text", args["text"]])})
    if name == "android_swipe": return result({"output": run(command()+["shell", "input", "swipe", *[str(int(args[key])) for key in ("x1", "y1", "x2", "y2")], str(int(args.get("duration_ms", 300)))])})
    if name == "android_press_back": return result({"output": run(command()+["shell", "input", "keyevent", "4"])})
    if name == "android_assert_accessibility":
        import xml.etree.ElementTree as ET
        nodes=list(ET.parse(project_path(args["xml_path"], must_exist=True)).getroot().iter()); missing=[]
        for key, attr in (("text","text"),("content_desc","content-desc"),("resource_id","resource-id")):
            for value in args.get(key, []):
                if value not in [node.attrib.get(attr, "") for node in nodes]: missing.append(f"{attr}={value!r}")
        return error("Missing accessibility nodes: "+", ".join(missing)) if missing else result({"pass":True,"nodes":len(nodes)})
    if name == "android_compare_screenshots":
        expected=project_path(args["expected_path"],must_exist=True); actual=project_path(args["actual_path"],must_exist=True); same=expected.read_bytes()==actual.read_bytes()
        return result({"pass":same,"exact_match":same,"expected_bytes":expected.stat().st_size,"actual_bytes":actual.stat().st_size})
    if name == "android_run_maestro_flow": return result(run_flow(args["flow_path"],args.get("output_dir"),bool(args.get("debug",False))))
    if name == "android_create_maestro_flow": return result(create_flow(args["flow_path"],args["content"],bool(args.get("overwrite",False))))
    if name == "android_create_and_run_maestro_flow": return result(create_and_run(args["flow_path"],args["content"],bool(args.get("overwrite",False)),args.get("output_dir")))
    if name == "android_create_baseline_from_flow": return result(baseline(args["flow_path"],args["package"],args["baseline_dir"],bool(args.get("reset_app",True))))
    if name == "android_build_project": return result(build(args["project_dir"],args.get("tasks"),int(args.get("timeout",900))))
    if name == "android_find_debug_apk": return result(debug_apk(args["project_dir"]))
    if name == "android_run_final_ui_validation":
        project=args["project_dir"]; checks=build(project,["test","assembleDebug"])
        if not checks["pass"]: raise RuntimeError("Coding checks failed; final UI validation was not started.\n"+checks["output"])
        apk=project_path(args["apk_path"],must_exist=True); package=package_name(args["package"]); flow=project_path(args["flow_path"],must_exist=True); out=state_path(args["artifact_dir"])
        run(command()+["install","-r",str(apk)],timeout=180); run(command()+["shell","pm","clear",package]); run(command()+["shell","monkey","-p",package,"1"])
        maestro=run_flow(str(flow),str(out/"maestro"),True); artifacts=collect(package,str(out))
        if not maestro["pass"]: raise RuntimeError("Maestro validation failed.\n"+maestro["output"])
        return result({"pass":True,"phase":"final-ui-validation","coding_checks":checks,"maestro":maestro,"artifacts":artifacts,"baseline":baseline(str(flow),package,args["baseline_dir"],False) if args.get("baseline_dir") else None})
    raise RuntimeError(f"Unknown tool: {name}")


if __name__ == "__main__":
    serve(TOOLS, dispatch)
