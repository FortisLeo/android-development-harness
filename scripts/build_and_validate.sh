#!/usr/bin/env bash
set -Eeuo pipefail
source "$(cd "$(dirname "$0")" && pwd)/common.sh"
[[ -x "$ROOT_DIR/gradlew" ]] || fail "Run this from the Android repository or set PROJECT_DIR to one containing gradlew"
PROJECT_DIR="${PROJECT_DIR:-$PWD}"; cd "$PROJECT_DIR"
./gradlew assembleDebug
APK="${APK_PATH:-$(find app/build/outputs/apk/debug -maxdepth 1 -name '*.apk' -print -quit)}"
[[ -n "$APK" && -f "$APK" ]] || fail "Debug APK not found"
"$ROOT_DIR/scripts/validate.sh" "${APP_ID:?Set APP_ID}" "$APK" "${ARTIFACT_DIR:-$ROOT_DIR/artifacts/latest}"
