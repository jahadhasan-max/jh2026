"""Render frames from the built .blend.
Usage: python render_frames.py scene.blend out_dir [frames...|start-end] [--preview]
Skips frames that already exist, so it can resume after an interruption."""
import bpy, sys, os
args = sys.argv[1:]
blend, out = args[0], os.path.abspath(args[1])
preview = "--preview" in args
spec = [a for a in args[2:] if a != "--preview"]
bpy.ops.wm.open_mainfile(filepath=blend)
s = bpy.context.scene
frames = []
for a in spec:
    if "-" in a:
        lo, hi = map(int, a.split("-")); frames += list(range(lo, hi + 1))
    else:
        frames.append(int(a))
frames = frames or list(range(s.frame_start, s.frame_end + 1))
if preview:
    s.render.resolution_percentage = 50
    s.cycles.samples = 12
os.makedirs(out, exist_ok=True)
for f in frames:
    path = os.path.join(out, f"{f:04d}.png")
    if os.path.exists(path):
        continue
    s.frame_set(f)
    s.render.filepath = path
    bpy.ops.render.render(write_still=True)
    print("FRAME", f, flush=True)
