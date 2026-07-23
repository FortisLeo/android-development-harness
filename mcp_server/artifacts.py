from __future__ import annotations
import datetime as dt
import json
from .adb_client import command, run, require_device
from .config import artifact_dir, package_name

def collect(package: str, destination: str | None = None) -> dict:
    require_device(); package=package_name(package); directory=artifact_dir(destination)
    (directory/"collected-at.txt").write_text(dt.datetime.now(dt.timezone.utc).isoformat())
    run(command()+["shell","uiautomator","dump","/sdcard/window.xml"], timeout=30)
    (directory/"accessibility.xml").write_bytes(run(command()+["exec-out","cat","/sdcard/window.xml"], timeout=30, binary=True))
    operations={"screenshot.png":(command()+["exec-out","screencap","-p"],True),"windows.txt":(command()+["shell","dumpsys","window","windows"],False),"properties.txt":(command()+["shell","getprop"],False),"package.txt":(command()+["shell","dumpsys","package",package],False),"meminfo.txt":(command()+["shell","dumpsys","meminfo",package],False),"logcat.txt":(command()+["logcat","-d","-v","threadtime","-t","5000"],False)}
    for name,(cmd,binary) in operations.items():
        try:
            data=run(cmd,timeout=30,binary=binary); (directory/name).write_bytes(data if isinstance(data,bytes) else data.encode())
        except RuntimeError as exc: (directory/name).write_text(f"collection failed: {exc}\n")
    metadata={"package":package,"serial":__import__('os').environ.get("ANDROID_SERIAL"),"collected_at":dt.datetime.now(dt.timezone.utc).isoformat(),"files":sorted(p.name for p in directory.iterdir())}
    (directory/"metadata.json").write_text(json.dumps(metadata,indent=2)); return {"artifact_dir":str(directory),"files":metadata["files"]}

def screenshot(path: str) -> dict:
    from .config import artifact_dir
    target=artifact_dir(path); target=target/"screenshot.png" if target.suffix=="" else target
    target.write_bytes(run(command()+["exec-out","screencap","-p"],binary=True)); return {"path":str(target),"bytes":target.stat().st_size}

def accessibility(path: str) -> dict:
    from .config import artifact_dir
    target=artifact_dir(path); target=target/"accessibility.xml" if target.suffix=="" else target
    run(command()+["shell","uiautomator","dump","/sdcard/window.xml"]); target.write_bytes(run(command()+["exec-out","cat","/sdcard/window.xml"],binary=True)); return {"path":str(target),"bytes":target.stat().st_size}
