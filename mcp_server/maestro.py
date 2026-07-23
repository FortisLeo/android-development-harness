from __future__ import annotations
import shutil, subprocess
from .adb_client import command, run, require_device
from .config import allowed_project_path, artifact_dir, package_name

def executable():
    path=shutil.which("maestro")
    if not path: raise RuntimeError("Maestro CLI not found. Install it and ensure maestro is on PATH.")
    return path

def run_flow(flow_path: str, output_dir: str|None=None, debug: bool=False) -> dict:
    require_device(); flow=allowed_project_path(flow_path,must_exist=True)
    if flow.suffix.lower() not in {".yaml",".yml"}: raise RuntimeError("Maestro flow must be YAML")
    cmd=[executable(),"test",str(flow)]; cwd=None
    if output_dir:
        out=artifact_dir(output_dir); cwd=str(out); cmd += ["--format","junit","--output",str(out/"maestro-results.xml")]
    if debug: cmd.append("--debug-output")
    p=subprocess.run(cmd,capture_output=True,text=True,timeout=600,cwd=cwd,check=False); output=(p.stdout+"\n"+p.stderr).strip()
    return {"pass":p.returncode==0,"flow":str(flow),"exit_code":p.returncode,"output":output[-12000:]}

def create_flow(path: str, content: str, overwrite: bool=False) -> dict:
    flow=allowed_project_path(path)
    if flow.suffix.lower() not in {".yaml",".yml"} or not content.strip(): raise RuntimeError("Flow must be non-empty YAML")
    if "takeScreenshot:" not in content: raise RuntimeError("Flow must include takeScreenshot checkpoints")
    if flow.exists() and not overwrite: raise RuntimeError(f"Flow exists: {flow}")
    flow.parent.mkdir(parents=True,exist_ok=True); flow.write_text(content); return {"path":str(flow),"bytes":flow.stat().st_size,"screenshot_steps":content.count("takeScreenshot:")}

def create_and_run(path: str, content: str, overwrite=False, output_dir=None) -> dict:
    require_device(); return {"created":create_flow(path,content,overwrite),"execution":run_flow(path,output_dir,True)}

def baseline(flow_path: str, package: str, destination: str, reset=True) -> dict:
    require_device(); package=package_name(package); out=artifact_dir(destination)
    if reset: run(command()+["shell","pm","clear",package])
    result=run_flow(flow_path,str(out/"maestro"),True)
    if not result["pass"]: raise RuntimeError("Maestro flow failed; no baseline created\\n"+result["output"])
    (out/"flow-final.png").write_bytes(run(command()+["exec-out","screencap","-p"],binary=True))
    run(command()+["shell","uiautomator","dump","/sdcard/window.xml"])
    (out/"flow-final-accessibility.xml").write_bytes(run(command()+["exec-out","cat","/sdcard/window.xml"],binary=True))
    return {"pass": True, "baseline_dir": str(out), "maestro": result}
