#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [[ -f "$ROOT_DIR/config/device.env" ]]; then source "$ROOT_DIR/config/device.env"; fi
export ANDROID_HOME="${ANDROID_HOME:-${ANDROID_SDK_ROOT:-$HOME/Library/Android/sdk}}"
export ANDROID_SDK_ROOT="${ANDROID_SDK_ROOT:-$ANDROID_HOME}"
export PATH="$ANDROID_HOME/platform-tools:$ANDROID_HOME/emulator:$ANDROID_HOME/cmdline-tools/latest/bin:$PATH"
ADB=(adb)
if [[ -n "${ANDROID_SERIAL:-}" ]]; then ADB+=( -s "$ANDROID_SERIAL" ); fi

fail(){ echo "ERROR: $*" >&2; exit 1; }
require_cmd(){ command -v "$1" >/dev/null 2>&1 || fail "Missing command: $1"; }
require_device(){
  require_cmd adb
  [[ "$("${ADB[@]}" get-state 2>/dev/null || true)" == "device" ]] || fail "No ready device. Enable USB debugging, accept the prompt, then run status."
}
