from __future__ import annotations

import os
import subprocess
from .protocol import log


def command() -> list[str]:
    sdk = os.environ.get("ANDROID_HOME", os.environ.get("ANDROID_SDK_ROOT", ""))
    executable = os.path.join(sdk, "platform-tools", "adb") if sdk else "adb"
    args = [executable if os.path.exists(executable) else "adb"]
    serial = os.environ.get("ANDROID_SERIAL", "").strip()
    if serial:
        args += ["-s", serial]
    return args


def run(args: list[str], timeout: int = 30, *, binary: bool = False):
    log("running " + " ".join(args))
    try:
        completed = subprocess.run(args, capture_output=True, timeout=timeout, check=False)
    except FileNotFoundError as exc:
        raise RuntimeError(f"Command not found: {exc.filename}") from exc
    if completed.returncode:
        raise RuntimeError(f"Command failed ({completed.returncode}): {' '.join(args)}\n{completed.stderr.decode('utf-8', 'replace')[-4000:]}")
    return completed.stdout if binary else completed.stdout.decode("utf-8", "replace")


def require_device() -> None:
    if run(command() + ["get-state"], timeout=10).strip() != "device":
        raise RuntimeError("No ready Android device. Connect USB debugging and accept the RSA prompt.")
