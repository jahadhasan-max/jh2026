#!/usr/bin/env bash
# End-to-end check of the toolkit: bootstrap -> build -> inspect -> render -> sheet -> encode.
#   selftest.sh [work_dir]
# Prints PASS on success. Takes about 1-2 minutes on 4 CPU cores once bpy is installed.
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL="$(dirname "$DIR")"
W="${1:-$(mktemp -d)}"; mkdir -p "$W"
step() { echo "== $*" >&2; }

step bootstrap;  "$DIR/bootstrap.sh" >/dev/null
step build;      "$DIR/bpyrun" "$SKILL/examples/turntable.py" "$W/scene" 12 2>&1 | grep -q BUILT
for f in turntable.blend turntable.glb turntable.stl; do test -s "$W/scene/$f"; done
step inspect;    "$DIR/bpyrun" "$DIR/inspect_scene.py" "$W/scene/turntable.blend" | tee "$W/inspect.json" | grep -q '"camera_cuts"'
step render;     "$DIR/bpyrun" "$DIR/render.py" "$W/scene/turntable.blend" "$W/frames" 1-12 --preview 2>&1 | grep -q RENDERED
test "$(ls "$W/frames" | wc -l)" -eq 12
step resume;     "$DIR/bpyrun" "$DIR/render.py" "$W/scene/turntable.blend" "$W/frames" 1-12 --preview 2>&1 | grep -q "RENDERED 0 frames"
step sheet;      "$DIR/sheet.sh" "$W/frames" "$W/sheet.png" 4 1 4 7 10 >/dev/null; test -s "$W/sheet.png"
step encode;     "$DIR/encode.sh" "$W/frames" "$W/turntable.mp4" 24 >/dev/null; test -s "$W/turntable.mp4"
echo "PASS ($W)"
