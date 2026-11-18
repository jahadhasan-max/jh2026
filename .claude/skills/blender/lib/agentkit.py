"""agentkit: small helpers for building Blender 5.x scenes from scripts.

Written for an agent working headless: every helper is plain bpy, works without a
window, and encodes a workaround that was found the hard way (see SKILL.md).

    import agentkit as ak
    ak.reset(frames=(1, 120), fps=24)
    ak.world((0.02, 0.02, 0.025), 0.4)
    ak.render_settings(res=(1280, 720), samples=24)
    ak.bloom()
"""
import math
import os
import sys

import bpy
import bmesh
from mathutils import Vector

# ---------------------------------------------------------------- basics

def argv():
    """Script arguments, under both `bpyrun script.py a b` and `blender -b --python script.py -- a b`."""
    if "--" in sys.argv:
        return sys.argv[sys.argv.index("--") + 1:]
    return sys.argv[1:]


def reset(frames=(1, 250), fps=24):
    """Empty factory scene with the given frame range."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    s = bpy.context.scene
    s.frame_start, s.frame_end = frames
    s.render.fps = fps
    return s


def lin(rgb):
    """sRGB 0-1 triple (as picked from a hex code) to linear, which is what Blender colours take."""
    return tuple(((c + 0.055) / 1.055) ** 2.4 if c > 0.04045 else c / 12.92 for c in rgb)


def hex_color(h):
    h = h.lstrip("#")
    return lin(tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)))


def link(obj):
    bpy.context.scene.collection.objects.link(obj)
    return obj


def empty(name, loc=(0, 0, 0)):
    e = link(bpy.data.objects.new(name, None))
    e.location = loc
    return e


def key(obj, path, frame, value, interp="BEZIER"):
    """Set a property and keyframe it. `interp` is BEZIER, LINEAR or CONSTANT.

    Uses the new-keyframe preference instead of touching F-curves, because
    Blender 5's layered actions moved fcurves to action.layers[].strips[].channelbags.
    """
    bpy.context.preferences.edit.keyframe_new_interpolation_type = interp
    setattr(obj, path, value)
    obj.keyframe_insert(path, frame=frame)


def save(path):
    bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(path))


def export(path, selected_only=False):
    """Export by extension: .glb/.gltf, .stl, .obj, .fbx, .usd/.usdc/.usdz."""
    path = os.path.abspath(path)
    ext = os.path.splitext(path)[1].lower()
    if ext in (".glb", ".gltf"):
        bpy.ops.export_scene.gltf(filepath=path, use_selection=selected_only,
                                  export_format="GLB" if ext == ".glb" else "GLTF_SEPARATE")
    elif ext == ".stl":
        bpy.ops.wm.stl_export(filepath=path, export_selected_objects=selected_only)
    elif ext == ".obj":
        bpy.ops.wm.obj_export(filepath=path, export_selected_objects=selected_only)
    elif ext == ".fbx":
        bpy.ops.preferences.addon_enable(module="io_scene_fbx")
        bpy.ops.export_scene.fbx(filepath=path, use_selection=selected_only)
    elif ext in (".usd", ".usdc", ".usdz"):
        bpy.ops.wm.usd_export(filepath=path, selected_objects_only=selected_only)
    else:
        raise ValueError(f"unsupported export format: {ext}")
    return path

# ---------------------------------------------------------------- look

def world(color=(0.02, 0.02, 0.022), strength=0.4):
    w = bpy.data.worlds.new("World")
    bpy.context.scene.world = w
    w.use_nodes = True
    bg = w.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = (*color, 1)
    bg.inputs["Strength"].default_value = strength
    return w


def render_settings(res=(1280, 720), samples=24, engine="CYCLES", denoise=True, bounces=4,
                    look="AgX - Medium High Contrast"):
    """Sensible CPU-Cycles defaults. EEVEE works only if libEGL exists, and via
    software GL it is slower than Cycles on a 4-core box, so prefer Cycles."""
    s = bpy.context.scene
    r = s.render
    r.engine = engine
    r.resolution_x, r.resolution_y = res
    r.resolution_percentage = 100
    r.use_persistent_data = True
    if engine == "CYCLES":
        c = s.cycles
        c.device = "CPU"
        c.samples = samples
        c.adaptive_threshold = 0.05
        c.use_denoising = denoise
        c.max_bounces = bounces
        c.diffuse_bounces = c.glossy_bounces = c.transmission_bounces = min(2, bounces)
        c.caustics_reflective = c.caustics_refractive = False
    try:
        s.view_settings.view_transform = "AgX"
        s.view_settings.look = look
    except TypeError:
        pass
    return s


def bloom(threshold=1.0, strength=0.45, size=0.8, dispersion=0.012):
    """Bloom + slight lens dispersion. Blender 5 compositor = a node group on
    scene.compositing_node_group, and Glare settings are input *sockets*
    (Type is a menu socket: "Bloom", "Fog Glow", "Streaks", ...), not properties."""
    s = bpy.context.scene
    tree = bpy.data.node_groups.new("Grade", "CompositorNodeTree")
    tree.interface.new_socket("Image", in_out="OUTPUT", socket_type="NodeSocketColor")
    s.compositing_node_group = tree
    rl = tree.nodes.new("CompositorNodeRLayers")
    g = tree.nodes.new("CompositorNodeGlare")
    for name, val in (("Type", "Bloom"), ("Quality", "High"), ("Threshold", threshold), ("Smoothness", 0.3),
                      ("Clamp", True), ("Maximum", 6.0), ("Strength", strength), ("Size", size)):
        if name in g.inputs:
            g.inputs[name].default_value = val
    last = g
    tree.links.new(rl.outputs["Image"], g.inputs["Image"])
    if dispersion:
        lens = tree.nodes.new("CompositorNodeLensdist")
        if "Dispersion" in lens.inputs:
            lens.inputs["Dispersion"].default_value = dispersion
        tree.links.new(g.outputs["Image"], lens.inputs["Image"])
        last = lens
    out = tree.nodes.new("NodeGroupOutput")
    tree.links.new(last.outputs["Image"], out.inputs[0])
    return tree

# ---------------------------------------------------------------- materials & meshes

def material(name, color, rough=0.5, metallic=0.0, emission=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metallic
    if emission:
        b.inputs["Emission Color"].default_value = (*color, 1)
        b.inputs["Emission Strength"].default_value = emission
    return m


def object_color_material(name, k_emit=20.0, rough=0.45, metallic=0.0, emission_only=False):
    """Material driven by the *object's* colour: base = obj.color.rgb,
    emission strength = obj.color.alpha * k_emit.

    One shared material, per-object animated colour and glow with plain keyframes:
        key(obj, "color", f, (r, g, b, glow))
    """
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    info = nt.nodes.new("ShaderNodeObjectInfo")
    mul = nt.nodes.new("ShaderNodeMath")
    mul.operation = "MULTIPLY"
    mul.inputs[1].default_value = k_emit
    nt.links.new(info.outputs["Alpha"], mul.inputs[0])
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    if emission_only:
        em = nt.nodes.new("ShaderNodeEmission")
        nt.links.new(info.outputs["Color"], em.inputs["Color"])
        nt.links.new(mul.outputs[0], em.inputs["Strength"])
        nt.links.new(em.outputs[0], out.inputs["Surface"])
    else:
        b = nt.nodes.new("ShaderNodeBsdfPrincipled")
        b.inputs["Roughness"].default_value = rough
        b.inputs["Metallic"].default_value = metallic
        nt.links.new(info.outputs["Color"], b.inputs["Base Color"])
        nt.links.new(info.outputs["Color"], b.inputs["Emission Color"])
        nt.links.new(mul.outputs[0], b.inputs["Emission Strength"])
        nt.links.new(b.outputs[0], out.inputs["Surface"])
    return m


def fade_material(name, color=(0.012, 0.011, 0.010), rough=0.22):
    """Surface that fades in from fully transparent by obj.color.alpha (0..1). Good for floors."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    info = nt.nodes.new("ShaderNodeObjectInfo")
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    b = nt.nodes.new("ShaderNodeBsdfPrincipled")
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Roughness"].default_value = rough
    mx = nt.nodes.new("ShaderNodeMixShader")
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(info.outputs["Alpha"], mx.inputs[0])
    nt.links.new(tr.outputs[0], mx.inputs[1])
    nt.links.new(b.outputs[0], mx.inputs[2])
    nt.links.new(mx.outputs[0], out.inputs["Surface"])
    return m


def bevel_cube_mesh(size=1.0, width=0.03, segments=2, name="BevelCube", smooth=False):
    """Shared mesh for voxels/blocks. Flat shading keeps the blocks crisp; smooth
    shading on a lightly bevelled cube looks like a pillow."""
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=size)
    bmesh.ops.bevel(bm, geom=bm.edges[:] + bm.verts[:], offset=width, segments=segments, affect="EDGES")
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = smooth
    return me


def text(body, name=None, size=1.0, extrude=0.01, align=("CENTER", "CENTER"), mat=None):
    cu = bpy.data.curves.new(name or f"txt_{body}", "FONT")
    cu.body = body
    cu.size = size
    cu.extrude = extrude
    cu.align_x, cu.align_y = align
    o = link(bpy.data.objects.new(name or f"txt_{body}", cu))
    if mat:
        o.data.materials.append(mat)
    return o

# ---------------------------------------------------------------- lights & cameras

def area_light(name, loc, color=(1, 1, 1), size=3.0, energy=500, target=(0, 0, 1)):
    L = link(bpy.data.objects.new(name, bpy.data.lights.new(name, "AREA")))
    L.location = loc
    L.data.size = size
    L.data.color = color
    L.data.energy = energy
    t = L.constraints.new("TRACK_TO")
    t.target = empty(name + "_tgt", target)
    t.track_axis, t.up_axis = "TRACK_NEGATIVE_Z", "UP_Y"
    return L


def camera(name, lens, keys, fstop=4.0, focus=None, parent=None, interp="BEZIER"):
    """Animated camera aimed by a Track To constraint with depth of field.

    keys: [(frame, location, aim_point), ...]. With `focus=<object>` the camera
    tracks and focuses that object instead and aim points are ignored.
    """
    cd = bpy.data.cameras.new(name)
    cd.lens = lens
    cd.sensor_width = 36
    c = link(bpy.data.objects.new(name, cd))
    tgt = focus or empty(name + "_aim", keys[0][2])
    con = c.constraints.new("TRACK_TO")
    con.target = tgt
    con.track_axis, con.up_axis = "TRACK_NEGATIVE_Z", "UP_Y"
    cd.dof.use_dof = True
    cd.dof.focus_object = tgt
    cd.dof.aperture_fstop = fstop
    if parent:
        c.parent = parent
    for f, loc, aim in keys:
        key(c, "location", f, loc, interp)
        if focus is None:
            key(tgt, "location", f, aim, interp)
    return c


def orbit_rig(name, center, start_deg, end_deg, f0, f1):
    """Empty that spins about Z between two frames; parent a camera to it for an orbit."""
    p = empty(name, center)
    key(p, "rotation_euler", f0, (0, 0, math.radians(start_deg)))
    key(p, "rotation_euler", f1, (0, 0, math.radians(end_deg)))
    return p


def cut(frame, cam):
    """Switch the active camera at `frame` (timeline marker bound to the camera)."""
    m = bpy.context.scene.timeline_markers.new(cam.name, frame=frame)
    m.camera = cam
    if frame <= bpy.context.scene.frame_start:
        bpy.context.scene.camera = cam
    return m


def world_pos(obj, frame):
    """Evaluated world position of an animated object at a frame."""
    bpy.context.scene.frame_set(frame)
    return obj.matrix_world.translation.copy()

# ---------------------------------------------------------------- colour ramps

def mix(a, b, t):
    return tuple(a[i] + (b[i] - a[i]) * t for i in range(len(a)))


def heat(base, x, mid=(0.69, 0.18, 0.095), hot=(1.0, 0.55, 0.28)):
    """base -> mid -> hot as x goes 0 -> 1 (things heating up as they approach a source)."""
    return mix(base, mid, x / 0.55) if x < 0.55 else mix(mid, hot, (x - 0.55) / 0.45)
