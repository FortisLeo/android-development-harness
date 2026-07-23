#!/usr/bin/env bash
set -Eeuo pipefail
source "$(cd "$(dirname "$0")" && pwd)/common.sh"
PACKAGE="${1:-${APP_ID:-}}"; APK="${2:-${APK_PATH:-}}"; OUT="${3:-${ARTIFACT_DIR:-$ROOT_DIR/artifacts/latest}}"
[[ -n "$PACKAGE" ]] || fail "Usage: $0 PACKAGE APK [ARTIFACT_DIR]"
[[ -n "$APK" ]] || fail "Usage: $0 PACKAGE APK [ARTIFACT_DIR]"
require_device
mkdir -p "$OUT"
"$ROOT_DIR/scripts/android_device.sh" install "$APK" | tee "$OUT/install.txt"
"$ROOT_DIR/scripts/android_device.sh" reset "$PACKAGE" | tee "$OUT/reset.txt"
"$ROOT_DIR/scripts/android_device.sh" launch "$PACKAGE" | tee "$OUT/launch.txt"
"$ROOT_DIR/scripts/android_device.sh" collect "$PACKAGE" "$OUT"
if grep -Eiq 'FATAL EXCEPTION|crash_dump|AndroidRuntime: FATAL' "$OUT/logcat.txt"; then echo 'FAIL: fatal crash markers found in logcat' >&2; exit 1; fi
echo "PASS: device validation completed; inspect $OUT"
