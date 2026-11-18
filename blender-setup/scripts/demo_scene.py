"""Build a small demo scene in headless Blender, save it, export GLB, and render a PNG.
Usage: python demo_scene.py <output_dir>
"""
import sys, math, os
import bpy

out = os.path.abspath(sys.argv[-1] if len(sys.argv) > 1 else ".")
os.makedirs(out, exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene

def mat(name, color, metallic=0.0, rough=0.5):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Metallic"].default_value = metallic
    b.inputs["Roughness"].default_value = rough
    return m

# Floor
bpy.ops.mesh.primitive_plane_add(size=20)
bpy.context.object.data.materials.append(mat("Floor", (0.8, 0.78, 0.74), rough=0.9))

# Bevelled cube, glossy sphere, torus
bpy.ops.mesh.primitive_cube_add(size=1.6, location=(-2.2, 0, 0.8))
c = bpy.context.object
c.modifiers.new("Bevel", "BEVEL").width = 0.12
c.modifiers["Bevel"].segments = 4
c.data.materials.append(mat("Coral", (0.95, 0.38, 0.30), rough=0.4))
bpy.ops.object.shade_smooth()

bpy.ops.mesh.primitive_uv_sphere_add(radius=1.0, location=(0, 0.4, 1.0), segments=64, ring_count=32)
bpy.ops.object.shade_smooth()
bpy.context.object.data.materials.append(mat("Chrome", (0.9, 0.9, 0.92), metallic=1.0, rough=0.12))

bpy.ops.mesh.primitive_torus_add(location=(2.3, 0, 0.35), major_radius=0.9, minor_radius=0.35)
bpy.ops.object.shade_smooth()
bpy.context.object.data.materials.append(mat("Teal", (0.10, 0.55, 0.60), rough=0.3))

# Lights
bpy.ops.object.light_add(type="AREA", location=(3, -4, 6))
key = bpy.context.object
key.data.energy = 1500; key.data.size = 4
key.rotation_euler = (math.radians(45), 0, math.radians(35))
world = bpy.data.worlds.new("World"); scene.world = world
world.use_nodes = True
world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.6

# Camera
bpy.ops.object.camera_add(location=(0, -9, 4.5))
cam = bpy.context.object
cam.rotation_euler = (math.radians(68), 0, 0)
scene.camera = cam

# Render settings (CPU Cycles works without a GPU)
scene.render.engine = "CYCLES"
scene.cycles.device = "CPU"
scene.cycles.samples = 64
scene.cycles.use_denoising = True
scene.render.resolution_x, scene.render.resolution_y = 1280, 720
scene.render.filepath = os.path.join(out, "demo_render.png")

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(out, "demo_scene.blend"))
bpy.ops.export_scene.gltf(filepath=os.path.join(out, "demo_scene.glb"))
bpy.ops.render.render(write_still=True)
print("DONE", out)
