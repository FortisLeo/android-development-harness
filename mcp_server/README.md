# Android MCP server

This local MCP server exposes safe Android build and final UI-validation actions to OpenCode.

## Lifecycle rule

The automation has two strict phases:

1. **Coding phase:** implementation agents edit code and create/update Maestro flows and accessibility assertions. The build agent runs Gradle/unit/instrumentation/lint checks and builds the debug APK. No Maestro, ADB UI testing, screenshots, accessibility dumps, or baselines run here.
2. **Final UI validation phase:** only after coding checks pass, the build agent calls `android_run_final_ui_validation`. This installs the APK, runs Maestro on a connected device/emulator, collects screenshots/accessibility/logcat, compares or creates baselines, and returns evidence.

A connected device is required only for final UI validation and device-specific tools.

## Tools

### Device/artifact tools

- `android_status`
- `android_install_apk`
- `android_launch_app`
- `android_reset_app`
- `android_screenshot`
- `android_dump_accessibility`
- `android_collect_artifacts`
- `android_logcat`
- `android_tap`
- `android_input_text`
- `android_swipe`
- `android_press_back`
- `android_assert_accessibility`
- `android_compare_screenshots`

### Maestro tools

- `android_run_maestro_flow`
- `android_create_maestro_flow`
- `android_create_and_run_maestro_flow`
- `android_create_baseline_from_flow`

These remain available for explicit operations. Normal feature automation should use the final gate instead of running them during coding.

### Build and final gate tools

- `android_build_project` — allowlisted Gradle wrapper tasks only; coding phase only
- `android_find_debug_apk`
- `android_run_final_ui_validation` — the only combined final device-validation gate

## Safety

The server uses `ANDROID_SERIAL` when set. It checks `adb get-state` before device operations. It never factory-resets, unlocks, wipes an emulator, or modifies unrelated applications. `android_reset_app` only runs `pm clear` for the supplied target package. Generated artifacts are restricted to `ANDROID_HARNESS_ARTIFACT_ROOT` (default: this project's `artifacts/`). Project paths are restricted to the harness, `ANDROID_PROJECT_ROOT`, or `ANDROID_HARNESS_PROJECT_ROOTS`.

## OpenCode configuration

The project-local `opencode.json` registers this server:

```json
"android": {
  "type": "local",
  "command": ["python3", "mcp_server/android_mcp.py"],
  "enabled": true
}
```

## macOS setup

Install Java 17, Android platform-tools, and Maestro on the Mac. Ensure `adb` and `maestro` are on PATH, then connect the phone with USB debugging enabled:

```bash
adb devices
maestro --version
export ANDROID_SERIAL=<device-serial>
```

The server does not require an emulator when using a physical device.
