#!/usr/bin/env bash
# Encode a PNG frame folder (0001.png, 0002.png, ...) to an MP4 that plays everywhere.
#   encode.sh frames_dir out.mp4 [FPS=24] [audio.wav]
set -euo pipefail
DIR="$1"; OUT="$2"; FPS="${3:-24}"; AUDIO="${4:-}"
START=$(ls "$DIR" | grep -E '^[0-9]{4}\.png$' | sort | head -1 | sed 's/\.png//; s/^0*//')
A=(); [ -n "$AUDIO" ] && A=(-i "$AUDIO" -c:a aac -b:a 192k -shortest)
ffmpeg -loglevel error -y -framerate "$FPS" -start_number "${START:-1}" -i "$DIR/%04d.png" "${A[@]}" \
  -c:v libx264 -preset slow -crf 18 -pix_fmt yuv420p -movflags +faststart "$OUT"
ffprobe -v error -show_entries format=duration:stream=codec_name,width,height -of compact "$OUT"
