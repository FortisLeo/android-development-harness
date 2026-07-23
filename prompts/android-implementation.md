# Android implementation contract

Implement only the approved plan and requested scope. Read existing patterns first, preserve architecture, and make the smallest safe diff. Add or update behavior tests for changed logic. For every UI change, create or update the matching Maestro YAML flow and accessibility assertions under the target Android project's `.android_harness/` directory.

Do not run Gradle, tests, Maestro, ADB, screenshots, accessibility dumps, or device commands; the build worker owns validation. Do not modify signing, release, secrets, production configuration, unrelated apps, or unrelated files. Do not commit, push, merge, or open a PR.

Before handing back, inspect the diff and report:
- files changed and why
- tests and UI flow/assertions added or updated
- assumptions and risks
- anything the build worker must verify
