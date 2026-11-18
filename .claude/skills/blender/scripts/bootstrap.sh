#!/usr/bin/env bash
# Make a Python with Blender's `bpy` module available. Idempotent and quiet:
# progress goes to stderr, the interpreter path is the only thing on stdout.
#
#   PY=$(.claude/skills/blender/scripts/bootstrap.sh)
#
# Env: BPY_VERSION (default 5.3.0), BLENDER_AGENT_HOME (default ~/.cache/blender-agent)
set -euo pipefail
BPY_VERSION="${BPY_VERSION:-5.3.0}"
HOME_DIR="${BLENDER_AGENT_HOME:-$HOME/.cache/blender-agent}"
VENV="$HOME_DIR/venv-$BPY_VERSION"
PY="$VENV/bin/python"
log() { echo "[blender] $*" >&2; }

if [ -x "$PY" ] && "$PY" -c "import bpy, sys; sys.exit(bpy.app.version_string != '$BPY_VERSION')" 2>/dev/null; then
  echo "$PY"; exit 0
fi

mkdir -p "$HOME_DIR"
log "installing bpy $BPY_VERSION into $VENV (about a minute, ~400 MB)"
# bpy 5.x wheels are built for CPython 3.13 only.
if command -v uv >/dev/null 2>&1; then
  uv venv -q --allow-existing -p 3.13 "$VENV"
  uv pip install -q -p "$PY" "bpy==$BPY_VERSION"
else
  PY313=$(command -v python3.13 || true)
  [ -n "$PY313" ] || { log "need uv or python3.13 on PATH"; exit 1; }
  "$PY313" -m venv "$VENV"
  "$PY" -m pip install -q "bpy==$BPY_VERSION"
fi

# Linux only: EEVEE and the GPU module need libEGL. Cycles on the CPU works without it.
if [ "$(uname)" = "Linux" ] && ! ldconfig -p 2>/dev/null | grep -q 'libEGL.so.1'; then
  if command -v apt-get >/dev/null 2>&1 && [ "$(id -u)" = "0" ]; then
    PKGS="libegl1 libgl1-mesa-dri libegl-mesa0"
    apt-get install -y -q $PKGS >/dev/null 2>&1 \
      || { apt-get update -q >/dev/null 2>&1 && apt-get install -y -q $PKGS >/dev/null 2>&1; } \
      || log "could not install EGL libs: EEVEE unavailable, Cycles still works"
  else
    log "libEGL missing: EEVEE unavailable, Cycles still works"
  fi
fi

"$PY" -c "import bpy, sys; print('[blender] ready: bpy', bpy.app.version_string, file=sys.stderr)"
echo "$PY"
