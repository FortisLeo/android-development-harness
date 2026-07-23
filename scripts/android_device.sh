#!/usr/bin/env bash
set -Eeuo pipefail
source "$(cd "$(dirname "$0")" && pwd)/common.sh"
usage(){ echo "usage: $0 status|install APK|launch PACKAGE|reset PACKAGE|collect PACKAGE DIR" >&2; exit 2; }
status(){ require_cmd adb; adb devices -l; if [[ -n "${ANDROID_SERIAL:-}" ]]; then require_device; echo "serial=$ANDROID_SERIAL"; "${ADB[@]}" shell getprop ro.product.model; "${ADB[@]}" shell getprop ro.build.version.release; fi; }
install_apk(){ require_device; [[ -f "$1" ]] || fail "APK not found: $1"; "${ADB[@]}" install -r "$1"; }
launch(){ require_device; "${ADB[@]}" shell monkey -p "$1" 1 >/dev/null; }
reset_app(){ require_device; "${ADB[@]}" shell pm clear "$1"; }
collect(){
  local package="$1" dir="$2"; require_device; mkdir -p "$dir"
  date -Is > "$dir/collected-at.txt"
  "${ADB[@]}" shell uiautomator dump /sdcard/window.xml >/dev/null 2>&1 || true
  "${ADB[@]}" pull /sdcard/window.xml "$dir/accessibility.xml" >/dev/null 2>&1 || true
  "${ADB[@]}" exec-out screencap -p > "$dir/screenshot.png"
  "${ADB[@]}" shell dumpsys window windows > "$dir/windows.txt" 2>&1 || true
  "${ADB[@]}" shell getprop > "$dir/properties.txt"
  "${ADB[@]}" shell dumpsys package "$package" > "$dir/package.txt" 2>&1 || true
  "${ADB[@]}" shell dumpsys meminfo "$package" > "$dir/meminfo.txt" 2>&1 || true
  "${ADB[@]}" logcat -d -v threadtime -t 5000 > "$dir/logcat.txt" 2>&1 || true
  python3 - "$dir" "$package" "${ANDROID_SERIAL:-}" <<'PY'
import datetime,json,pathlib,sys
d=pathlib.Path(sys.argv[1]); json.dump({'package':sys.argv[2],'serial':sys.argv[3] or None,'collected_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'files':sorted(p.name for p in d.iterdir())},open(d/'metadata.json','w'),indent=2)
PY
  echo "Artifacts: $dir"
}
case "${1:-}" in status) status;; install) [[ $# == 2 ]] || usage; install_apk "$2";; launch) [[ $# == 2 ]] || usage; launch "$2";; reset) [[ $# == 2 ]] || usage; reset_app "$2";; collect) [[ $# == 3 ]] || usage; collect "$2" "$3";; *) usage;; esac
