#!/usr/bin/env bash
set -Eeuo pipefail
# Run on macOS from the harness directory. Does not install an emulator.
command -v brew >/dev/null 2>&1 || { echo 'Homebrew is required: https://brew.sh' >&2; exit 1; }
brew install --cask temurin@17 2>/dev/null || true
brew install --cask android-commandlinetools 2>/dev/null || true
brew install android-platform-tools 2>/dev/null || true
SDKROOT="${ANDROID_HOME:-$HOME/Library/Android/sdk}"
mkdir -p "$SDKROOT"
cat <<EOF
Mac setup attempted. Add to ~/.zshrc if needed:
export ANDROID_HOME="$SDKROOT"
export ANDROID_SDK_ROOT="$SDKROOT"
export PATH="$SDKROOT/platform-tools:$SDKROOT/cmdline-tools/latest/bin:\$PATH"
Then run: adb devices
EOF
