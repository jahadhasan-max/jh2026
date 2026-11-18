#!/usr/bin/env bash
# Tile rendered frames into one contact-sheet image to review a whole sequence in one Read.
#   sheet.sh frames_dir out.png [COLS] [frame numbers...]
# No frame numbers = every PNG in the folder. Tiles are 640x360.
set -euo pipefail
DIR="$1"; OUT="$2"; COLS="${3:-2}"; shift $(( $# < 3 ? $# : 3 ))
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
i=0
if [ $# -gt 0 ]; then
  for f in "$@"; do ln -s "$(cd "$DIR" && pwd)/$(printf '%04d' "$f").png" "$TMP/$(printf '%04d' $i).png"; i=$((i+1)); done
else
  for f in "$DIR"/*.png; do ln -s "$(cd "$(dirname "$f")" && pwd)/$(basename "$f")" "$TMP/$(printf '%04d' $i).png"; i=$((i+1)); done
fi
ROWS=$(( (i + COLS - 1) / COLS ))
ffmpeg -loglevel error -y -framerate 1 -i "$TMP/%04d.png" \
  -vf "scale=640:360:force_original_aspect_ratio=decrease,pad=640:360:(ow-iw)/2:(oh-ih)/2,tile=${COLS}x${ROWS}" \
  -frames:v 1 "$OUT"
echo "$OUT ($i frames, ${COLS}x${ROWS})"
