---
created: 2026-11-18
tags: [blender, 3d, claude, setup]
---

# Blender with Claude

![[demo_render.png]]

## Status
- [x] Blender 5.3 running headless in a Claude Code cloud session (installed as the `bpy` Python module, because blender.org downloads are blocked there)
- [x] Test scene built, exported, and rendered (Cycles on the CPU, 1280×720, 64 samples, about 22 s)
- [ ] Set up live Blender control on the MacBook (MCP server + add-on)
- [ ] Choose a skill pack

## Files
- Scene: [[demo_scene.blend]]
- Web / AR model: [[demo_scene.glb]]
- Script that builds everything: [[demo_scene.py]]

Run the script yourself:
```bash
blender --background --python demo_scene.py -- ./output
```

## Two ways to work
1. **Live, on the MacBook.** Install Blender from blender.org, then add an MCP server so Claude Code can drive the open Blender window:
   ```bash
   claude mcp add blender uvx blender-mcp
   ```
   Then install that project's Blender add-on and turn it on.
2. **Headless, in the cloud.** Claude writes Python scripts that build the scene and sends back renders plus `.blend`, `.glb` and `.stl` files. No Blender window needed.

## Options found on GitHub (unverified, community projects)
### MCP servers (live control)
- Official Blender Lab server: projects.blender.org/lab/blender_mcp. It warns that it runs AI-written code without safeguards.
- [ahujasid/blender-mcp](https://github.com/ahujasid/blender-mcp): the most widely used one (recently renamed `mcp-for-blender`)
- [kleer001/blender-mcp](https://github.com/kleer001/blender-mcp/): 175 typed tools, tested on Blender 4.2
- [HoldMyBeer-gg/blenderwright](https://github.com/HoldMyBeer-gg/blenderwright): a very large toolset, about 48k tokens of context unless you filter it
- [djeada/blender-mcp-server](https://github.com/djeada/blender-mcp-server)

### Skill packs
- [elithril/blender-kiln](https://github.com/elithril/blender-kiln): describe an object or show a photo and get a clean model (games, web, AR, 3D printing)
- [EL4CTEO/blender-skills](https://github.com/el4cteo/blender-skills): 28 pipeline skills that also work headless with no MCP server
- [majidmanzarpour/blender-game-skills](https://github.com/majidmanzarpour/blender-game-skills): concept art to rigged game assets
- [czlonkowski/blender-web-3d-skill](https://github.com/czlonkowski/blender-web-3d-skill): Blender plus three.js for the web
- [RobLe3/cc-blender-skill](https://github.com/RobLe3/cc-blender-skill), [arjun988/blender-skills](https://github.com/arjun988/blender-skills)

## Blender source code (for reference)
[blender/blender](https://github.com/blender/blender): about 4.5M lines of code (4.0M C/C++, 0.5M Python), about 21k files, about 1.5 GB with full history. You only need it to modify Blender itself.
