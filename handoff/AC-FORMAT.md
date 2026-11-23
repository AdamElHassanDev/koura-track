# Assetto Corsa track format: rules and known crash causes

Collected from the three reference projects' code and notes. Items marked **[game]** were confirmed in game by their authors on CSP 0.2.11. Everything else is read from code. The full source is `docs/ac-format.md` and `docs/known-issues.md` in mapcreator.

**These are mostly mapcreator's conventions, and openlaps does some things differently.** openlaps writes KN5 version 5, defines a `WALL` key in `surfaces.ini` (the trial track has it as `SURFACE_9`), and uses the same mesh for physics and visuals. Do not change openlaps to match this file unless the game shows a fault. Use this file to diagnose problems, not as a checklist.

## Track folder

```
<track_id>/
  <track_id>.kn5          geometry, materials, embedded textures
  models.ini              optional; lists several kn5 files on one origin
  map.png
  data/surfaces.ini  lighting.ini  map.ini  (traffic.json for CSP traffic)
  ui/ui_track.json  preview.png  outline.png
  ai/fast_lane.ai         only for tracks with a route
  extension/ext_config.ini   CSP settings
```

`models.ini` entries: `[MODEL_0] FILE=… POSITION=0,0,0 ROTATION=0,0,0`.

## KN5 file

- Header `sc6969`, int32 version (5 or 6; version 6 adds one int32 0). Little-endian. Strings are int32 length plus ASCII.
- Textures: count, then `{int32 active, name, uint32 length, bytes}`. The bytes are a complete DDS file (DXT1 opaque, DXT5 with alpha, mipmaps, sides divisible by 4).
- Materials: name, shader, blend byte, alpha-tested byte, depth mode, then properties (name plus 10 floats) and texture slots.
- Nodes, depth-first: class 1 is a dummy with a 4x4 matrix, class 2 is a mesh with 44-byte vertices (position, normal, UV, tangent) and 16-bit indices.
- **At most 65,535 vertices per mesh.** Split below that.
- **A mesh node with children crashes the game.** Keep a flat tree: one root dummy, everything else a childless child.
- Axes: x east, y up, z = minus north, metres from a local origin. Triangles counter-clockwise seen from above.
- Compute tangents from the UV direction. A fixed tangent breaks normal maps on vertical walls.
- Float precision: sub-millimetre cracks were found 4.4 km from the origin. Never place a terrain vertex at a crossing its neighbours do not share.
- Each mesh carries `lodIn` and `lodOut` distances. Use them on large maps.

## Physics by mesh name

- A mesh is collidable when its name starts with a digit plus a surface key: `1ROAD_…`, `1GRASS_…`, `1WALL_…`.
- Each physics mesh name must contain exactly one key, and no key may contain another.
- mapcreator deliberately defines no `WALL` key in `surfaces.ini`: any physics mesh named WALL is a solid barrier already, and defining the key is reported to make walls driveable. openlaps does define one. If cars can drive through or onto walls in the probe, this is the first thing to test.
- Invisible colliders: a `1WALL_…` mesh with the renderable flag off.
- `surfaces.ini` sections are numbered from `[SURFACE_0]`.
- **Never** set `WAV_PITCH=extended-0`; plain AC crashes on it.
- Never use `grass.wav` on a road surface; CSP then draws its dirt as grass.
- Keep objects at scale 1.

## Marker objects

- `AC_PIT_0` is required. CSP crashes without it. **[reported]**
- `AC_START_n` and `AC_PIT_n` number from 0 with no leading zeros (`AC_PIT_1`, not `AC_PIT_01`).
- `pitboxes` in `ui_track.json` must equal the number of `AC_PIT_n` markers.
- A track with no spawn markers fails with "cannot have 0 cars in race.ini".
- Place spawns about 0.3 m above the road, +Z forward. **[game]**
- Circuits also need `AC_TIME_0_L` / `AC_TIME_0_R`; point-to-point needs `AC_AB_START_L/R` and `AC_AB_FINISH_L/R`. Free roam needs neither.
- `ui_track.json`: `geotags` are two strings; `length` carries a unit.

## AI line (only if a route is added later)

- `fast_lane.ai` version 7. Points 0.4 m above the surface; points on the surface crashed the game. Space them about 5 m apart; 1 m spacing inflated the measured track length by a third on a long road. **[game]**

## CSP `ext_config.ini`

- Goes in `<track>/extension/`.
- `[GRASS_FX]` with `GRASS_MATERIALS` and `OCCLUDING_MATERIALS`. On open pasture it cost about 5% frame rate. **[game]**
- `[RAIN_FX]` with puddle, soaking and rough material lists.
- `[TREES] LIST_0=trees/trees.txt`. **No comment lines in `trees.txt`**; CSP 0.2.11 then loads no trees. **[game]** Tree FX trees have no collision, so add invisible trunk colliders near roads. About 2,500 trees per km cost about 60% of frame rate on a GTX 1660 Ti. **[game]**
- A track's own `[TYRES_FX]` replaces CSP's generic one entirely; include all colour pairs.
- Do not use `[WIND] DYNAMIC_CABLES` (wires drawn far too thick) or `ksPerPixel_tilingfix`. **[game]**
- Track scripts need `ALLOW_TRACK_SCRIPTS=1`. openlaps sets it and ships `vivo.lua`, which calls a local server on ports 8789 and 8790.

## Materials

- Specular is added on top of the texture, so black lettering washes out in headlights. Use no specular on signs.
- Near-white textures clip at night under CSP exposure. Cap whites around 200 to 224 of 255.

## Road geometry lessons

- On a 30 m elevation model, cross-slope read from the data is noise. Cap camber by road width and keep a small crown.
- Smooth the road profile along the road with a filter several cells long, and cap grade (mapcreator uses 15%).
- A surface model shows bridges, embankments and trees as humps. Filter them out near crossings.
- Triangulate terrain with the road outline as fixed edges, or holes appear at skewed junctions.
- At junctions, side roads must share the main road's edge vertices exactly. Check for gaps or steps over 5 cm.

## Size measurements from the reference projects

- openlaps here: 1 km² gives 680 meshes and a 76 MB folder.
- road-to-assetto: one heavily forested kilometre gave 185 meshes, 2.95 M vertices and a 203 MB track file.
- mapcreator: a 12.8 km road is 420k vertices and 29 MB; a 63 km build peaks near 2.7 GB of memory.

## In-game checks

- `logs/log.txt` must contain `Creating physics track: <id>` (with CSP) or `LOADING MODEL content/tracks/<id>`, plus `STARTING PHYSICS ENGINE`, and no `ERROR:` line naming the track.
- `logs/custom_shaders_patch.log` marks failures with "FAILED".
- mapcreator's `mc_probe.lua` teleports the car to listed points, waits 1.2 s, and records wheel contact, surface validity and a downward raycast. Note that CSP 0.2.11 faces the car against the direction vector passed to `physics.setCarPosition`, so pass it reversed.
