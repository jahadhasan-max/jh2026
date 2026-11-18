"""Print a compact JSON summary of a .blend, so the scene can be checked without a window.

    bpyrun inspect_scene.py scene.blend [frame]

Prints one JSON line (the last line of output). Reports render settings, camera cuts, object counts, animated objects, and the
world-space bounding box at `frame` (default: frame_start).
"""
import json
import os
import sys

import bpy
from mathutils import Vector

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import agentkit as ak  # noqa: E402

args = ak.argv()
if not args:
    sys.exit(__doc__)
bpy.ops.wm.open_mainfile(filepath=args[0])
s = bpy.context.scene
frame = int(args[1]) if len(args) > 1 else s.frame_start
s.frame_set(frame)

types, animated = {}, 0
lo, hi = Vector((1e9,) * 3), Vector((-1e9,) * 3)
for o in s.objects:
    types[o.type] = types.get(o.type, 0) + 1
    if o.animation_data and o.animation_data.action:
        animated += 1
    if o.type in {"MESH", "FONT", "CURVE"} and o.visible_get():
        for c in o.bound_box:
            w = o.matrix_world @ Vector(c)
            lo = Vector(map(min, lo, w))
            hi = Vector(map(max, hi, w))

r = s.render
info = {
    "file": os.path.abspath(args[0]),
    "frames": [s.frame_start, s.frame_end],
    "fps": r.fps,
    "seconds": round((s.frame_end - s.frame_start + 1) / r.fps, 2),
    "engine": r.engine,
    "resolution": [r.resolution_x, r.resolution_y, r.resolution_percentage],
    "samples": s.cycles.samples if r.engine == "CYCLES" else None,
    "active_camera": s.camera.name if s.camera else None,
    "camera_cuts": sorted([[m.frame, m.camera.name] for m in s.timeline_markers if m.camera]),
    "object_types": types,
    "animated_objects": animated,
    "materials": len(bpy.data.materials),
    "compositor": bool(getattr(s, "compositing_node_group", None)),
    f"bbox_at_frame_{frame}": [[round(v, 2) for v in lo], [round(v, 2) for v in hi]] if lo.x < 1e9 else None,
}
print(json.dumps(info))  # one line: read it with `| tail -1`
