"""Render frames from a .blend, resumably.

    bpyrun render.py scene.blend out_dir [FRAMES...] [--preview] [--samples N] [--percent P]

FRAMES: numbers and/or ranges (12 40-60). Default: the scene's whole range.
Frames that already exist in out_dir are skipped, so a killed render can be
restarted with the same command, and only changed frames need deleting.
--preview = 50% resolution, 12 samples (about 1 s/frame on 4 CPU cores).
"""
import os
import sys
import time

import bpy

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import agentkit as ak  # noqa: E402

args = ak.argv()
if len(args) < 2:
    sys.exit(__doc__)
blend, out = args[0], os.path.abspath(args[1])
opts, frames = {}, []
it = iter(args[2:])
for a in it:
    if a == "--preview":
        opts["preview"] = True
    elif a in ("--samples", "--percent"):
        opts[a[2:]] = int(next(it))
    elif "-" in a:
        lo, hi = map(int, a.split("-"))
        frames += range(lo, hi + 1)
    else:
        frames.append(int(a))

bpy.ops.wm.open_mainfile(filepath=blend)
s = bpy.context.scene
frames = frames or list(range(s.frame_start, s.frame_end + 1))
if opts.get("preview"):
    s.render.resolution_percentage = 50
    if s.render.engine == "CYCLES":
        s.cycles.samples = 12
if "samples" in opts and s.render.engine == "CYCLES":
    s.cycles.samples = opts["samples"]
if "percent" in opts:
    s.render.resolution_percentage = opts["percent"]

os.makedirs(out, exist_ok=True)
t_all = time.time()
done = 0
for f in frames:
    path = os.path.join(out, f"{f:04d}.png")
    if os.path.exists(path):
        continue
    t = time.time()
    s.frame_set(f)
    s.render.filepath = path
    bpy.ops.render.render(write_still=True)
    done += 1
    print(f"FRAME {f} {time.time() - t:.1f}s", flush=True)
print(f"RENDERED {done} frames in {time.time() - t_all:.0f}s -> {out}", flush=True)
