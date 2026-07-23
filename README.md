# Android Development Harness

This repository contains only the reusable Android MCP server, OpenCode configuration, and setup documentation. Per-Android-project flows, screenshots, baselines, artifacts, and reports are created under `.android_harness/` in the Android project root and are not stored in this repository.

## Per-project state

From the Android application repository, set:

```bash
export ANDROID_PROJECT_ROOT="$PWD"
python3 /path/to/android-development-harness/mcp_server/android_mcp.py
```

The MCP server creates:

```text
your-android-app/
└── .android_harness/
    ├── flows/
    ├── screenshots/
    │   ├── baseline/
    │   └── actual/
    ├── artifacts/
    ├── reports/
    └── README.md
```

The project `.android_harness/` directory should normally be added to the Android app repository’s `.gitignore` unless you want to version Maestro flows and approved baselines. The MCP source repository itself has no runtime `flows/`, `screenshots/`, or `artifacts/` directories.

## Lifecycle

1. Coding phase: implement code, create/update `.android_harness/flows/` Maestro flows and accessibility assertions, run Gradle/unit/instrumentation/lint checks, and build the APK. Do not run device UI validation.
2. Final validation phase: after coding checks pass, require a connected device/emulator, run Maestro, collect screenshots/accessibility/logcat, compare baselines, and create baselines only after a passing flow.

## MCP configuration

The project-local `opencode.json` registers the Android MCP server:

```json
"android": {
  "type": "local",
  "command": ["python3", "mcp_server/android_mcp.py"],
  "enabled": true
}
```

The server exposes Android device, build, Maestro, artifact, accessibility, screenshot, baseline, and final-validation tools.
