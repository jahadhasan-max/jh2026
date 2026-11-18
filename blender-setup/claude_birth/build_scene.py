"""
"Born from Code": a 20-second cinematic Blender scene.

Act I    (f1-96)    Genesis: glyphs of code rain through a dark void.
Act II   (f97-200)  Convergence: the code spirals into a vortex and feeds a core.
Act III  (f201-264) Birth: the core ignites and blooms into a Claude-style starburst.
Act IV   (f265-376) Morph: the starburst voxels fly apart and assemble a pixel creature.
Act V    (f377-480) Awakening: it lands, blinks, and the title writes itself in.

Usage:  python build_scene.py <out.blend>
"""
import bpy, bmesh, math, random, sys, os
from mathutils import Vector, Matrix

random.seed(7)
OUT = os.path.abspath(sys.argv[-1] if sys.argv[-1].endswith(".blend") else "claude_birth.blend")

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.frame_start, scene.frame_end = 1, 480
scene.render.fps = 24
prefs = bpy.context.preferences

# ---------------------------------------------------------------- helpers
def key(obj, path, frame, value, interp="BEZIER"):
    prefs.edit.keyframe_new_interpolation_type = interp
    setattr(obj, path, value)
    obj.keyframe_insert(path, frame=frame)

def lin(c):  # sRGB hex-ish 0-1 -> linear
    return tuple(((x + 0.055) / 1.055) ** 2.4 if x > 0.04045 else x / 12.92 for x in c)

ORANGE = lin((0.851, 0.467, 0.341))      # #D97757
HOT    = (1.0, 0.55, 0.28)
CREAM  = lin((0.94, 0.93, 0.90))
EYE    = (0.012, 0.010, 0.009)
CORE_W = Vector((0, 0, 3.0))              # world position of the birth core

def object_color_material(name, k_emit, rough=0.45, metallic=0.0, emission_only=False):
    """Material whose colour = object colour and emission = object alpha * k_emit.
    Lets us animate colour/glow per object with plain keyframes."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    info = nt.nodes.new("ShaderNodeObjectInfo")
    mul = nt.nodes.new("ShaderNodeMath"); mul.operation = "MULTIPLY"; mul.inputs[1].default_value = k_emit
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

def link(obj):
    scene.collection.objects.link(obj)
    return obj

def empty(name, loc):
    e = link(bpy.data.objects.new(name, None))
    e.location = loc
    return e

# ---------------------------------------------------------------- world, render, colour
world = bpy.data.worlds.new("Void"); scene.world = world
world.use_nodes = True
bg = world.node_tree.nodes["Background"]
bg.inputs["Color"].default_value = (*lin((0.035, 0.03, 0.028)), 1)
bg.inputs["Strength"].default_value = 0.35

r = scene.render
r.engine = "CYCLES"
scene.cycles.device = "CPU"
scene.cycles.samples = 24
scene.cycles.adaptive_threshold = 0.05
scene.cycles.use_denoising = True
scene.cycles.max_bounces = 4
scene.cycles.diffuse_bounces = 2
scene.cycles.glossy_bounces = 2
scene.cycles.transmission_bounces = 2
scene.cycles.caustics_reflective = False
scene.cycles.caustics_refractive = False
r.resolution_x, r.resolution_y = 1280, 720
r.use_persistent_data = True
r.film_transparent = False
try:
    scene.view_settings.view_transform = "AgX"
    for look in ("AgX - Medium High Contrast", "AgX - Punchy", "Medium High Contrast"):
        try:
            scene.view_settings.look = look; break
        except TypeError:
            pass
except TypeError:
    pass

# Compositor: bloom + a touch of lens dispersion (Blender 5 node-group compositor)
try:
    tree = bpy.data.node_groups.new("Grade", "CompositorNodeTree")
    tree.interface.new_socket("Image", in_out="OUTPUT", socket_type="NodeSocketColor")
    scene.compositing_node_group = tree
    rl = tree.nodes.new("CompositorNodeRLayers")
    glare = tree.nodes.new("CompositorNodeGlare")
    for name, val in (("Type", "Bloom"), ("Quality", "High"), ("Threshold", 1.0), ("Smoothness", 0.3),
                      ("Clamp", True), ("Maximum", 6.0), ("Strength", 0.45), ("Size", 0.8), ("Saturation", 1.0)):
        if name in glare.inputs:
            glare.inputs[name].default_value = val
    lens = tree.nodes.new("CompositorNodeLensdist")
    if "Dispersion" in lens.inputs: lens.inputs["Dispersion"].default_value = 0.012
    if "Distortion" in lens.inputs: lens.inputs["Distortion"].default_value = -0.01
    go = tree.nodes.new("NodeGroupOutput")
    tree.links.new(rl.outputs["Image"], glare.inputs["Image"])
    tree.links.new(glare.outputs["Image"], lens.inputs["Image"])
    tree.links.new(lens.outputs["Image"], go.inputs[0])
except Exception as e:
    print("compositor setup skipped:", e)

# ---------------------------------------------------------------- materials
M_GLYPH = object_color_material("Glyph", 12, emission_only=True)
M_VOX   = object_color_material("Voxel", 30, rough=0.38)
M_CORE  = object_color_material("Core", 80, emission_only=True)
M_EMBER = object_color_material("Ember", 40, emission_only=True)
M_TITLE = object_color_material("Title", 14, emission_only=True)

# floor that fades in: mix(transparent -> dark gloss) by object alpha
M_FLOOR = bpy.data.materials.new("Floor"); M_FLOOR.use_nodes = True
nt = M_FLOOR.node_tree; nt.nodes.clear()
fi = nt.nodes.new("ShaderNodeObjectInfo")
tr = nt.nodes.new("ShaderNodeBsdfTransparent")
fb = nt.nodes.new("ShaderNodeBsdfPrincipled")
fb.inputs["Base Color"].default_value = (0.012, 0.011, 0.010, 1)
fb.inputs["Roughness"].default_value = 0.22
mx = nt.nodes.new("ShaderNodeMixShader")
fo = nt.nodes.new("ShaderNodeOutputMaterial")
nt.links.new(fi.outputs["Alpha"], mx.inputs[0])
nt.links.new(tr.outputs[0], mx.inputs[1]); nt.links.new(fb.outputs[0], mx.inputs[2])
nt.links.new(mx.outputs[0], fo.inputs["Surface"])

# ---------------------------------------------------------------- shared voxel mesh (bevelled cube)
def bevel_cube_mesh(size, width, segs, name):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=size)
    bmesh.ops.bevel(bm, geom=bm.edges[:] + bm.verts[:], offset=width, segments=segs, affect="EDGES")
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    return me  # flat shading keeps the voxels crisp

V = 0.30
VOX_MESH = bevel_cube_mesh(V * 0.96, 0.025, 2, "VoxelMesh")
VOX_MESH.materials.append(M_VOX)

# ---------------------------------------------------------------- the pixel creature (target shape)
# 12 wide x 4 deep x 7 tall hollow body, two slit eyes, side nubs, four legs.
fig = []  # (x, y, z, is_eye) in rig space
for ix in range(12):
    for iy in range(4):
        for iz in range(7):
            if not (ix in (0, 11) or iy in (0, 3) or iz in (0, 6)):
                continue
            eye = iy == 0 and ix in (3, 8) and iz in (4, 5)
            fig.append(((ix - 5.5) * V, (iy - 1.5) * V, (iz + 2.5) * V, eye))
for ix in (-1, 12):                      # arm nubs
    for iy in (1, 2):
        for iz in (3, 4):
            fig.append(((ix - 5.5) * V, (iy - 1.5) * V, (iz + 2.5) * V, False))
for ix in (1, 3, 8, 10):                 # legs
    for iy in (1, 2):
        for iz in (0, 1):
            fig.append(((ix - 5.5) * V, (iy - 1.5) * V, (iz + 0.5) * V, False))
N = len(fig)
FIG_C = Vector((0, 0, 1.4))

# ---------------------------------------------------------------- the starburst (birth shape), same N
RIG_Z = 0.8                                 # creature forms floating, then lands
C = CORE_W - Vector((0, 0, RIG_Z))          # core in rig space
rays = []
for k in range(12):
    a = k * (2 * math.pi / 12) + random.uniform(-0.12, 0.12)
    rays.append((a, random.uniform(1.7, 3.0)))
total_len = sum(L for _, L in rays)
burst = []
n_center = 24
for i in range(n_center):
    d = Vector((random.gauss(0, 1), random.gauss(0, 0.6), random.gauss(0, 1))).normalized() * random.uniform(0, 0.38)
    burst.append((C + d, random.uniform(0.75, 1.0)))
remaining = N - n_center
for k, (a, L) in enumerate(rays):
    cnt = round(remaining * L / total_len) if k < len(rays) - 1 else remaining - sum(
        round(remaining * L2 / total_len) for _, L2 in rays[:-1])
    dirv = Vector((math.cos(a), 0, math.sin(a)))
    perp = Vector((-math.sin(a), 0, math.cos(a)))
    for j in range(cnt):
        t = (j + random.random()) / cnt
        d = 0.35 + (t ** 1.25) * (L - 0.35)
        w = 0.26 * (1 - d / L) + 0.03
        p = C + dirv * d + perp * random.uniform(-w, w) + Vector((0, random.uniform(-0.12, 0.12), 0))
        burst.append((p, 1.0 - 0.55 * (d / L)))
assert len(burst) == N, (len(burst), N)

def ang(p, c):
    return math.atan2(p.z - c.z, p.x - c.x)

fig_sorted = sorted(fig, key=lambda f: ang(Vector(f[:3]), FIG_C))
burst_sorted = sorted(burst, key=lambda b: ang(b[0], C))

def rot_about(p, c, theta):  # rotate around Y axis through c
    return c + Matrix.Rotation(theta, 3, "Y") @ (p - c)

rig = empty("CreatureRig", (0, 0, RIG_Z))
voxels, eyes = [], []
for i, ((fx, fy, fz, is_eye), (bp, bs)) in enumerate(zip(fig_sorted, burst_sorted)):
    o = link(bpy.data.objects.new(f"vox_{i:03d}", VOX_MESH))
    o.parent = rig
    F = Vector((fx, fy, fz))
    ign = 200 + random.randint(0, 6)             # ignition
    S0 = bp
    S1 = rot_about(bp, C, math.radians(16))
    m0 = 266 + int(30 * (i / N)) + random.randint(0, 8)   # morph start, sweeps around the ring
    m1 = m0 + random.randint(34, 46)
    out_dir = (bp - C).normalized() if (bp - C).length > 1e-4 else Vector((0, -1, 0))
    mid = (S1 + F) / 2 + out_dir * random.uniform(0.7, 1.6) + Vector((0, random.uniform(-0.9, 0.5), random.uniform(0, 0.6)))
    # position
    key(o, "location", 1, C.copy())
    key(o, "location", ign, C.copy())
    key(o, "location", ign + 18, S0)
    key(o, "location", 262, S1, "LINEAR")
    key(o, "location", m0, S1)
    key(o, "location", (m0 + m1) // 2, mid)
    key(o, "location", m1, F)
    # scale
    key(o, "scale", 1, (0, 0, 0))
    key(o, "scale", ign, (0, 0, 0))
    key(o, "scale", ign + 14, (bs,) * 3)
    key(o, "scale", m0, (bs,) * 3)
    key(o, "scale", m1, (1, 1, 1))
    # rotation
    r0 = Vector([random.uniform(-0.5, 0.5) for _ in range(3)])
    key(o, "rotation_euler", ign + 18, r0)
    key(o, "rotation_euler", m0, r0)
    key(o, "rotation_euler", (m0 + m1) // 2, Vector([random.uniform(-3.2, 3.2) for _ in range(3)]))
    key(o, "rotation_euler", m1, (0, 0, 0))
    # colour / glow: white-hot at birth, cooling to clay orange as it settles
    key(o, "color", 1, (*HOT, 1.0))
    key(o, "color", ign + 10, (*HOT, 1.0))
    key(o, "color", 262, (*HOT, 0.55))
    key(o, "color", m1 - 6, (*ORANGE, 0.12))
    final = EYE if is_eye else ORANGE
    key(o, "color", m1 + 14, (*final, 0.0 if is_eye else 0.015))
    voxels.append(o)
    if is_eye:
        eyes.append(o)

# landing: drop, squash, settle
key(rig, "location", 352, (0, 0, RIG_Z))
key(rig, "location", 366, (0, 0, 0), "BEZIER")
key(rig, "scale", 366, (1, 1, 1))
key(rig, "scale", 370, (1.07, 1.07, 0.88))
key(rig, "scale", 378, (0.98, 0.98, 1.04))
key(rig, "scale", 386, (1, 1, 1))
# blinks
for b in (412, 456):                      # blink: eyes flash to skin colour and back
    for e in eyes:
        key(e, "color", b - 3, (*EYE, 0.0))
        key(e, "color", b, (*ORANGE, 0.015))
        key(e, "color", b + 4, (*EYE, 0.0))

# ---------------------------------------------------------------- code glyph rain + vortex
TOKENS = list("{}()[]<>/;=+*#&|01!?:") + ["=>", "fn", "def", "if", "{ }", "0x1F", "//", "&&", "</>", "let", "::", "++", "λ"]
glyphs = []
for i in range(260):
    tok = random.choice(TOKENS)
    cu = bpy.data.curves.new(f"g{i}", "FONT")
    cu.body = tok if tok != "λ" else "L"
    cu.align_x, cu.align_y = "CENTER", "CENTER"
    cu.size = random.uniform(0.32, 0.75)
    cu.extrude = 0.012
    o = link(bpy.data.objects.new(f"glyph_{i:03d}", cu))
    o.data.materials.append(M_GLYPH)
    rad = random.uniform(1.2, 9.0); a0 = random.uniform(0, 2 * math.pi)
    z0 = random.uniform(3.0, 16.0)
    speed = random.uniform(0.02, 0.065)
    p0 = Vector((rad * math.cos(a0), rad * math.sin(a0), z0))
    p96 = p0 - Vector((0, 0, speed * 95))
    key(o, "location", 1, p0, "LINEAR")
    key(o, "location", 96, p96, "LINEAR")
    spin = random.uniform(-0.6, 0.6)
    key(o, "rotation_euler", 1, (math.radians(90), 0, spin), "LINEAR")
    key(o, "rotation_euler", 96, (math.radians(90), 0, spin + 0.15), "BEZIER")
    # spiral into the core
    arrive = random.randint(150, 198)
    r96 = math.hypot(p96.x, p96.y); a96 = math.atan2(p96.y, p96.x)
    turns = random.uniform(1.0, 1.8) * 2 * math.pi
    steps = 7
    for s in range(1, steps + 1):
        t = s / steps
        f = int(96 + t * (arrive - 96))
        rr = r96 * (1 - t) ** 1.4
        aa = a96 + t * turns
        zz = p96.z + (CORE_W.z - p96.z) * (t ** 1.6)
        key(o, "location", f, (rr * math.cos(aa), rr * math.sin(aa), zz))
    key(o, "rotation_euler", arrive, (math.radians(20), 0, spin + turns * 1.1))
    key(o, "scale", 1, (1, 1, 1))
    key(o, "scale", arrive - 20, (1, 1, 1))
    key(o, "scale", arrive, (0, 0, 0))
    base = CREAM if random.random() < 0.8 else ORANGE
    a_base = random.uniform(0.18, 0.4)
    key(o, "color", 1, (*base, a_base))
    key(o, "color", arrive - 25, (*base, a_base))
    key(o, "color", arrive, (*HOT, 1.4))
    glyphs.append(o)

# ---------------------------------------------------------------- core + its light
bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=4, radius=1, location=CORE_W)
core = bpy.context.object; core.name = "Core"
core.data.materials.append(M_CORE)
for p in core.data.polygons: p.use_smooth = True
for f, s, a in ((1, 0, 0.2), (120, 0, 0.2), (160, 0.12, 0.35), (196, 0.38, 0.6), (204, 0.75, 1.6), (214, 0.3, 0.9), (226, 0.0, 0.2)):
    key(core, "scale", f, (s, s, s)); key(core, "color", f, (*HOT, a))

core_light = link(bpy.data.objects.new("CoreLight", bpy.data.lights.new("CoreLight", "POINT")))
core_light.location = CORE_W
core_light.data.color = HOT
core_light.data.shadow_soft_size = 0.3
for f, e in ((1, 0), (130, 0), (196, 900), (204, 6000), (230, 900), (290, 150), (340, 0)):
    key(core_light.data, "energy", f, e)

# ---------------------------------------------------------------- embers from the ignition
bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=1)
ember_mesh = bpy.context.object.data; ember_mesh.materials.append(M_EMBER)
bpy.data.objects.remove(bpy.context.object)
for i in range(140):
    o = link(bpy.data.objects.new(f"ember_{i:03d}", ember_mesh))
    d = Vector((random.gauss(0, 1), random.gauss(0, 1), random.gauss(0, 1))).normalized()
    s = random.uniform(0.012, 0.035)
    p1 = CORE_W + d * random.uniform(1.5, 6.0)
    p2 = p1 + Vector((random.uniform(-0.6, 0.6), random.uniform(-0.6, 0.6), random.uniform(1.0, 3.0)))
    st = 202 + random.randint(0, 6)
    key(o, "location", 1, CORE_W); key(o, "location", st, CORE_W)
    key(o, "location", st + 26, p1); key(o, "location", 480, p2, "LINEAR")
    key(o, "scale", 1, (0, 0, 0)); key(o, "scale", st, (0, 0, 0)); key(o, "scale", st + 4, (s, s, s))
    key(o, "scale", 480, (s * 0.6,) * 3)
    key(o, "color", st, (*HOT, 1.0)); key(o, "color", st + 60, (*ORANGE, 0.45)); key(o, "color", 480, (*ORANGE, 0.25))

# ---------------------------------------------------------------- floor
bpy.ops.mesh.primitive_plane_add(size=80, location=(0, 0, 0))
floor = bpy.context.object; floor.name = "Floor"
floor.data.materials.append(M_FLOOR)
key(floor, "color", 1, (1, 1, 1, 0)); key(floor, "color", 290, (1, 1, 1, 0)); key(floor, "color", 335, (1, 1, 1, 1))

# ---------------------------------------------------------------- title, letter by letter
TITLE = "Claude Code"
letters, x = [], 0.0
for i, ch in enumerate(TITLE):
    if ch == " ":
        x += 0.42; continue
    cu = bpy.data.curves.new(f"t{i}", "FONT"); cu.body = ch; cu.size = 0.95; cu.extrude = 0.02
    cu.align_y = "BOTTOM"
    o = link(bpy.data.objects.new(f"title_{i:02d}", cu)); o.data.materials.append(M_TITLE)
    bpy.context.view_layer.update()
    o["x"] = x
    x += o.dimensions.x + 0.06
    letters.append(o)
for j, o in enumerate(letters):
    o.location = (o["x"] - x / 2, 2.6, 3.7)
    o.rotation_euler = (math.radians(90), 0, 0)
    st = 428 + j * 3
    key(o, "scale", 1, (0, 0, 0)); key(o, "scale", st, (0, 0, 0)); key(o, "scale", st + 8, (1, 1, 1))
    key(o, "color", st, (*HOT, 1.6)); key(o, "color", st + 14, (*CREAM, 0.55))

# ---------------------------------------------------------------- lights for the creature
def area(name, loc, color, size, keys, target=(0, 0, 1.3)):
    L = link(bpy.data.objects.new(name, bpy.data.lights.new(name, "AREA")))
    L.location = loc; L.data.size = size; L.data.color = color
    t = L.constraints.new("TRACK_TO"); t.target = empty(name + "_tgt", target)
    t.track_axis = "TRACK_NEGATIVE_Z"; t.up_axis = "UP_Y"
    for f, e in keys:
        key(L.data, "energy", f, e)
    return L
area("Key", (-4.5, -5.5, 6.0), (1.0, 0.93, 0.85), 5, ((1, 0), (285, 0), (335, 900)))
area("Rim", (3.5, 5.0, 4.0), (0.55, 0.72, 1.0), 3, ((1, 0), (285, 0), (335, 1400)))
area("Glyphwash", (0, -4, 18), (0.9, 0.85, 0.8), 14, ((1, 250), (190, 250), (230, 0)), target=(0, 0, 6))

# ---------------------------------------------------------------- cameras
cams = []
def camera(name, lens, keys, fstop=2.8, focus=None, parent=None, interp="BEZIER"):
    cd = bpy.data.cameras.new(name); cd.lens = lens
    cd.sensor_width = 36
    c = link(bpy.data.objects.new(name, cd))
    tgt = empty(name + "_aim", keys[0][2]) if focus is None else focus
    con = c.constraints.new("TRACK_TO"); con.target = tgt
    con.track_axis = "TRACK_NEGATIVE_Z"; con.up_axis = "UP_Y"
    cd.dof.use_dof = True; cd.dof.focus_object = tgt; cd.dof.aperture_fstop = fstop
    if parent: c.parent = parent
    for f, loc, aim in keys:
        key(c, "location", f, loc, interp)
        if focus is None:
            key(tgt, "location", f, aim, interp)
    cams.append(c)
    return c

def cut(frame, cam):
    m = scene.timeline_markers.new(cam.name, frame=frame); m.camera = cam

# I-a: wide low angle, looking up into the rain
camA = camera("A_Wide", 22, [(1, (0, -17, 0.5), (0, 0, 8.5)), (60, (0, -14.5, 1.5), (0, 0, 8.0))], fstop=8)
# I-b: tracking shot riding with a single falling glyph (rack focus on it)
hero_g = glyphs[17]
def glyph_pos(g, f):
    scene.frame_set(f); return g.matrix_world.translation.copy()
gp49, gp96 = glyph_pos(hero_g, 49), glyph_pos(hero_g, 96)
off = Vector((1.3, -2.6, 0.9))
camB = camera("B_Ride", 55, [(49, gp49 + off, None), (96, gp96 + off * 0.8, None)], fstop=1.6, focus=hero_g, interp="LINEAR")
# II-a: top-down into the vortex, slowly rotating
piv_c = empty("C_Pivot", (0, 0, 0))
key(piv_c, "rotation_euler", 97, (0, 0, 0), "LINEAR"); key(piv_c, "rotation_euler", 152, (0, 0, math.radians(-55)), "LINEAR")
camC = camera("C_Top", 24, [(97, (0.01, -0.6, 21), (0, 0, 3)), (152, (0.01, -0.4, 17), (0, 0, 3))], fstop=11, parent=piv_c)
# II-b: three-quarter side view of the funnel, pushing in
camD = camera("D_Funnel", 30, [(153, (6.5, -8.0, 5.2), (0, 0, 4.2)), (200, (4.0, -5.6, 3.5), (0, 0, 3.0))], fstop=4)
# III: dead-on frontal for the birth bloom
camE = camera("E_Birth", 40, [(201, (0, -10.5, 3.1), (0, 0, 3.0)), (264, (0, -8.2, 3.0), (0, 0, 3.0))], fstop=5.6)
# IV-a: orbit while the starburst morphs
piv_f = empty("F_Pivot", (0, 0, 2.6))
key(piv_f, "rotation_euler", 265, (0, 0, math.radians(-70))); key(piv_f, "rotation_euler", 332, (0, 0, math.radians(18)))
camF = camera("F_Orbit", 30, [(265, (0, -8.5, 1.4), (0, 0, 2.6))], fstop=5.6, parent=piv_f)
# IV-b: low heroic angle as it lands
camG = camera("G_Low", 22, [(333, (2.8, -5.2, 0.25), (0, 0, 1.9)), (376, (2.2, -4.6, 0.3), (0, 0, 1.6))], fstop=4)
# V-a: close-up on the face, catching the first blink
camH = camera("H_Face", 36, [(377, (-1.8, -7.2, 1.7), (0, -0.6, 1.8)), (426, (-0.9, -5.9, 1.6), (0, -0.6, 1.55))], fstop=2.8)
# V-b: final wide pull-back with the title
camI = camera("I_Final", 32, [(427, (0, -9.5, 2.0), (0, 0, 2.7)), (480, (0, -12.0, 2.6), (0, 0, 3.0))], fstop=8)

for f, c in ((1, camA), (49, camB), (97, camC), (153, camD), (201, camE), (265, camF), (333, camG), (377, camH), (427, camI)):
    cut(f, c)
scene.camera = camA
scene.frame_set(1)

bpy.ops.wm.save_as_mainfile(filepath=OUT)
print(f"SAVED {OUT}  voxels={N} glyphs={len(glyphs)} cams={len(cams)}")
