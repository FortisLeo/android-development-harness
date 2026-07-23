from __future__ import annotations
import os, subprocess
from .config import project_path

def build(project_dir: str, tasks: list[str] | None=None, timeout: int=900) -> dict:
    project=project_path(project_dir,must_exist=True); wrapper=project/("gradlew.bat" if os.name=="nt" else "gradlew")
    if not wrapper.is_file() or (os.name!="nt" and not os.access(wrapper,os.X_OK)): raise RuntimeError(f"Executable Gradle wrapper not found: {wrapper}")
    allowed={"assembleDebug","test","lint","check","testDebugUnitTest","assembleDebugAndroidTest"}; selected=tasks or ["assembleDebug","test"]
    if not selected or any(t not in allowed for t in selected): raise RuntimeError(f"Unsupported Gradle task. Allowed: {sorted(allowed)}")
    p=subprocess.run([str(wrapper),*selected],cwd=project,capture_output=True,text=True,timeout=min(timeout,1800),check=False); output=(p.stdout+"\n"+p.stderr).strip()
    return {"pass":p.returncode==0,"project":str(project),"tasks":selected,"exit_code":p.returncode,"output":output[-16000:]}

def debug_apk(project_dir: str) -> dict:
    project=project_path(project_dir,must_exist=True); apks=sorted((project/"app"/"build"/"outputs"/"apk").glob("**/*-debug.apk"))
    if not apks: raise RuntimeError("No debug APK found")
    return {"apk_path":str(apks[-1]),"candidates":[str(p) for p in apks]}
