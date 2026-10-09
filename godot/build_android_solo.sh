#!/usr/bin/env bash
# Build an offline debug APK without changing global Godot/Android settings.
set -euo pipefail
BUILD_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/android-solo" && pwd)"
PROJECT_DIR="$(cd "$BUILD_DIR/.." && pwd)"
export ANDROID_HOME="${ANDROID_HOME:-$BUILD_DIR/.sdk}"
export JAVA_HOME="${JAVA_HOME:-/usr/lib/jvm/java-17-openjdk-amd64}"
export GRADLE_USER_HOME="$BUILD_DIR/.gradle-home"
if [[ -z "${NEXUS_PYTHON:-}" ]]; then
    for candidate in "$BUILD_DIR"/.tools/python/cpython-3.13-*/bin/python3.13; do
        if [[ -x "$candidate" ]]; then export NEXUS_PYTHON="$candidate"; break; fi
    done
fi
if [[ ! -d "$ANDROID_HOME/platforms/android-35" ]]; then
    echo "Android SDK 35 missing. See godot/android-solo/README.md." >&2
    exit 1
fi
if [[ -n "${NEXUS_GRADLE:-}" ]]; then
    GRADLE_BIN="$NEXUS_GRADLE"
elif command -v gradle >/dev/null; then
    GRADLE_BIN="$(command -v gradle)"
else
    GRADLE_BIN=""
    for candidate in "$BUILD_DIR"/.tools/gradle-8.14.3/bin/gradle "$HOME"/.gradle/wrapper/dists/gradle-8.14.3-all/*/gradle-8.14.3/bin/gradle; do
        if [[ -x "$candidate" ]]; then GRADLE_BIN="$candidate"; break; fi
    done
fi
if [[ -z "$GRADLE_BIN" ]]; then
    echo "Gradle 8.14.3 missing: install it or set NEXUS_GRADLE to its executable." >&2
    exit 1
fi
"$GRADLE_BIN" -p "$BUILD_DIR" --console=plain :app:assembleDebug "$@"
"$ANDROID_HOME/build-tools/35.0.0/apksigner" verify "$BUILD_DIR/app/build/outputs/apk/debug/app-debug.apk"
mkdir -p "$PROJECT_DIR/builds"
cp "$BUILD_DIR/app/build/outputs/apk/debug/app-debug.apk" "$PROJECT_DIR/builds/nexus-city-solo-debug.apk"
echo "APK: $PROJECT_DIR/builds/nexus-city-solo-debug.apk"
