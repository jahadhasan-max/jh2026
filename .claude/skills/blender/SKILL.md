---
name: blender
description: Make 3D models, renders, turntables and cinematic animations with Blender run headless from Python (bpy). Bootstraps Blender in about a minute with no GUI, gives scene-building helpers (cameras with cuts and DOF, animated glow materials, bloom, voxels, text, export to glb/stl/obj/fbx/usd), resumable frame rendering, contact sheets for review, and MP4 encoding. Use for any request involving Blender, 3D scenes, 3D video or animation, product or logo renders, or .blend/.glb/.stl output.
---

# Blender (headless, agent-operated)

You drive Blender through Python scripts, without a window. Everything here was
proven while making `blender-setup/claude_birth/born_from_code.mp4`: a 20 s,
nine-camera film rendered on a 4-core cloud container. That scene,
`blender-setup/claude_birth/build_scene.py`, is the full worked example to copy
from.

All paths below are relative to this skill folder: `.claude/skills/blender/`.

## Setup (once per machine, idempotent)

```bash
.claude/skills/blender/scripts/bootstrap.sh       # prints the python path; ~1 min the first time
.claude/skills/blender/scripts/selftest.sh        # optional: full pipeline check, prints PASS (~45 s)
```

The script installs the `bpy` wheel from PyPI into a venv at `~/.cache/blender-agent/`.
- Why not the official download: **download.blender.org is blocked** in cloud
  sessions, and PyPI is not.
- `bpy` 5.x needs **CPython 3.13**; the script picks it via `uv`.
- On Linux it also tries to add libEGL so EEVEE can run (see Rendering).
- On macOS it works the same way. If the user has desktop Blender open with an
  MCP server, prefer that for live work (see the last section).

## The loop

1. **Write one build script** that creates the whole scene from scratch and saves a `.blend`:
   `scripts/bpyrun my_scene.py out/scene.blend`. Start from `examples/turntable.py`
   or the film script. Import helpers with `import agentkit as ak`; `bpyrun` puts
   it on the path. Never hand-edit a `.blend`: change the script and rebuild,
   which takes seconds.
2. **Check it textually.** `scripts/bpyrun scripts/inspect_scene.py out/scene.blend [frame]`
   prints one JSON line (the last line) with camera cuts, object counts and the
   bounding box.
3. **Preview stills** from every act or shot (about 1 s each):
   `scripts/bpyrun scripts/render.py out/scene.blend prev 30 120 200 300 --preview`.
4. **Look at them in one image.** Run `scripts/sheet.sh prev sheet.png 2`, then Read `sheet.png`.
   Fix the script, rebuild, and re-preview until every shot is right. This
   catches framing, scale and lighting bugs before the long render.
5. **Full render in the background** with `run_in_background`; it resumes if killed:
   `scripts/bpyrun scripts/render.py out/scene.blend frames > render.log 2>&1`.
   Check progress with `ls frames | wc -l`. While it runs, encode a partial clip
   so the user sees something early.
6. **Encode:** `scripts/encode.sh frames film.mp4 24 [score.wav]`. Send the result with SendUserFile.

To change part of a finished film, edit the script, rebuild, delete only the
frames at or after the first affected frame, and rerun `render.py`; it skips the
frames that still exist. Before trusting the kept frames, re-render one and
compare it with `ffmpeg -i old.png -i new.png -lavfi psnr -f null -` (it should
report `inf`).

## Measured speeds (4 CPU cores, Cycles CPU)

| Job | Time |
|---|---|
| bootstrap (first time) | ~60 s |
| build a 1,200-object animated scene | ~2 s |
| preview frame (640×360, 12 samples) | ~1 s |
| final frame 1280×720, 24 samples + denoise: emissive text on black | ~2 s |
| final frame, same settings: 260 lit voxels, floor, DOF | ~7–8 s |
| 480-frame film | ~45 min |

Budget the render before promising a delivery time, and tell the user the
estimate. 1080p costs about 2.2× as much; motion blur about 2×.

## Rendering facts

- **Use Cycles on the CPU.** EEVEE needs a GPU context. With only Mesa's software
  `llvmpipe` it runs, but slowly: a default cube took 39 s to render. Without
  libEGL it fails silently.
- Use `ak.render_settings()` defaults: 24 samples, adaptive sampling,
  OpenImageDenoise, 4 bounces, caustics off, persistent data on. On mostly-dark
  emissive scenes 16–24 samples is plenty.
- Use the AgX view transform with the look `"AgX - Medium High Contrast"` for a
  filmic grade.
- Use `ak.bloom()` for the glow. **Blender 5 compositor changes:** the tree is a
  node group assigned to `scene.compositing_node_group`, and the output is a
  `NodeGroupOutput`. The Glare node's settings are **input sockets**: `Type` is
  a menu socket set with strings like `"Bloom"`. There is no `glare_type`
  property, and the default type, Streaks, looks cheap.

## Animation techniques that work

- **Keyframes:** use `ak.key(obj, "location" | "rotation_euler" | "scale" | "color" | ..., frame, value, "BEZIER"|"LINEAR"|"CONSTANT")`.
  It sets the interpolation through user preferences, because Blender 5's layered
  actions moved F-curves (`action.fcurves` is gone).
- **Per-object animated colour and glow from one shared material:**
  `ak.object_color_material(k_emit)`. Keyframe `obj.color = (r, g, b, glow)`;
  alpha × k_emit is the emission strength. This drove the cooling voxels, the
  heating code glyphs and the title reveal.
- **Fades:** `ak.fade_material()` mixes from transparent to a surface by object
  alpha. Use it for floors that appear mid-shot instead of popping in.
- **Morphing between two shapes:** give both shapes the same number of points,
  sort each by angle around its own centre, and pair them by index. The
  transition then flows instead of crossing. Stagger start frames and add an
  outward midpoint keyframe so the pieces fly in arcs.
- **Parent groups to an empty** (a rig) for whole-shape moves such as landing,
  squash and settle, while children keep their own keys.
- **Camera cuts:** use `ak.camera(name, lens, [(frame, loc, aim)...], fstop, focus=obj?, parent=pivot?)`
  plus `ak.cut(frame, cam)`. Cuts are timeline markers bound to cameras.
  - For an orbit, parent the camera to an empty that rotates about Z (`ak.orbit_rig`).
  - For a tracking shot, key the camera at `object position + offset` and pass
    `focus=obj`, so it rack-focuses on the object.
- **Blinks and small reactions:** change colour instead of scale. Scaling a
  voxel to zero leaves a hole showing the hollow inside.
- **Keep randomness reproducible:** seed with `random.seed(n)`. Give new elements
  their **own** `random.Random(m)`. Drawing from the shared RNG shifts every
  later object, which invalidates frames you already rendered.

## Modelling notes

- **Voxel or block shapes:** share one mesh, `ak.bevel_cube_mesh(size*0.96, 0.025, 2)`,
  across hundreds of objects. Use **flat** shading; smooth shading makes the
  blocks look like pillows. Build hollow shells to save objects.
- **Text:** `ak.text()` creates font objects; the built-in font has only ASCII
  characters. Rotate them 90° about X to face a camera looking along +Y. For a
  letter-by-letter reveal, make one object per letter and space them by
  `obj.dimensions.x` after `view_layer.update()`.
- **Export:** `ak.export("model.glb"|".stl"|".obj"|".fbx"|".usdz")`. STL is for
  3D printing: make the mesh watertight and real-world scaled (1 unit = 1 m).

## Sound

`blender-setup/claude_birth/soundtrack.py` synthesizes a score with numpy,
locked to frame times (`f2s(frame)`): drones, clicks, risers, impacts, pads,
plucks, chimes and a convolution reverb. Copy it and re-time the events to the
new picture. Check it with
`ffmpeg -i score.wav -lavfi showspectrumpic=s=1200x300 spec.png` and Read the
image; the hits should line up with the cuts.

## Look and story defaults (what made the film read well)

- Give the piece a five-act structure with a camera change every 2–3 s. Mix
  wide, tracking, top-down, frontal push-in, orbit, low hero and close-up shots.
- Use a near-black warm void, emissive subjects, a warm key light and a cool
  rim light (teal against orange), and a glossy dark floor for reflections.
- Make motion carry meaning. Things heat up as they approach a source (`ak.heat()`)
  and cool as they settle; land with squash and stretch; end on a held wide shot
  with the title.
- Do not recreate trademarked characters exactly. Make an original, stylised
  interpretation and say so.

## Live Blender on the user's machine (optional)

If a session runs on the user's computer, and the user has desktop Blender plus
a Blender MCP server, you can edit their open scene live. Options:
- the official Blender Lab server at projects.blender.org/lab/blender_mcp
- `claude mcp add blender uvx blender-mcp` (ahujasid), plus its Blender add-on

Keep to **one** lean MCP server: tool schemas cost context on every turn, and
blenderwright alone is about 48k tokens. These servers execute Python inside
Blender, so save the user's work first. The same scripts here also run under
desktop Blender with `blender -b --python script.py -- args`.
