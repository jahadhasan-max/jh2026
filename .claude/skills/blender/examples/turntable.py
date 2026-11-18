"""Template: a model on a floor, a 360° orbit camera, saved + exported.
Copy this as the starting point for a new scene.

    bpyrun examples/turntable.py out_dir [frames=48]
Writes out_dir/turntable.blend, turntable.glb, turntable.stl.
"""
import math
import os

import agentkit as ak
import bpy

args = ak.argv()
out = os.path.abspath(args[0] if args else "turntable_out")
n = int(args[1]) if len(args) > 1 else 48
os.makedirs(out, exist_ok=True)

ak.reset(frames=(1, n), fps=24)
ak.world((0.03, 0.03, 0.035), 0.5)
ak.render_settings(res=(1280, 720), samples=24)
ak.bloom(strength=0.25, dispersion=0)

# model: a bevelled block creature built from voxels sharing one mesh
ORANGE = ak.hex_color("#D97757")
vox = ak.bevel_cube_mesh(0.29, 0.02, 2, "Vox")
vox.materials.append(ak.material("Clay", ORANGE, rough=0.4))
body = ak.empty("Model")
cells = [(x, 0, z) for x in range(6) for z in range(4)] + [(0, 0, -1), (5, 0, -1)]
for i, (x, y, z) in enumerate(cells):
    o = ak.link(bpy.data.objects.new(f"vox_{i}", vox))
    o.location = ((x - 2.5) * 0.3, y * 0.3, (z + 1.5) * 0.3)
    o.parent = body

bpy.ops.mesh.primitive_plane_add(size=30)
bpy.context.object.data.materials.append(ak.material("Floor", (0.02, 0.02, 0.022), rough=0.25))

ak.area_light("Key", (-3, -4, 5), (1, 0.95, 0.9), 4, 600, target=(0, 0, 0.8))
ak.area_light("Rim", (3, 4, 3), (0.6, 0.75, 1.0), 3, 800, target=(0, 0, 0.8))

# constant-speed spin so the clip loops (orbit_rig() eases in/out instead)
rig = ak.empty("Orbit", (0, 0, 0.8))
ak.key(rig, "rotation_euler", 1, (0, 0, 0), "LINEAR")
ak.key(rig, "rotation_euler", n + 1, (0, 0, math.radians(360)), "LINEAR")
cam = ak.camera("Cam", 45, [(1, (0, -6, 1.6), (0, 0, 0.8))], fstop=5.6, parent=rig)
ak.cut(1, cam)

ak.save(os.path.join(out, "turntable.blend"))
ak.export(os.path.join(out, "turntable.glb"))
ak.export(os.path.join(out, "turntable.stl"))
print("BUILT", out)
