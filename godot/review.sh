#!/usr/bin/env bash
# Render the art fixture without starting or modifying a game server.
set -euo pipefail
project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
output_dir="$project_dir/art/captures"
mkdir -p "$output_dir"
review_log="$(mktemp /tmp/nexus-review.XXXXXX.log)"
godot --headless --path "$project_dir" --log-file "$review_log" --check-only --script res://main.gd
if rg -q 'SCRIPT ERROR|^ERROR:' "$review_log"; then
    exit 1
fi
for camera in overview detail hero bridge campus courtyard; do
    extra_args=()
    if [[ "$camera" != overview ]]; then
        extra_args+=("--$camera")
    fi
    xvfb-run -a -s '-screen 0 1280x720x24' godot --path "$project_dir" \
        --log-file "$review_log" --rendering-driver opengl3 -- \
        --art-preview --shot "--shot-path=$output_dir/$camera.png" "${extra_args[@]}" "$@"
    if rg -q 'SCRIPT ERROR|^ERROR:' "$review_log"; then
        exit 1
    fi
done
