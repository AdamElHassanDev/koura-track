Read-only code audit, 2026-11-23, of the commit pinned in REFERENCES.md. Nothing was executed.

Short version: mapcreator is a good source of knowledge, a pure-Python KN5 writer, an AI-line writer and a validator. It is not a free-roam generator. Everything is built around one routed centreline: side roads get 100 m stubs that are closed off, and terrain only reaches 700 m from the route. For a 12 x 12 km network you would reuse the format modules and the lessons, and write your own network meshing.

I only read files and ran nothing from the repo. Repo root: `<clone>/mapcreator`. Paths below are relative to it. I skipped `docs/ac-format.md` lines 519–607, 688–784 and 959–1020 (ramp/bridge JSON schemas, rail/paths, police liveries); a keyword search of those ranges found nothing more about AC format.

Status tags: **[game]** = the doc says it was confirmed in game (milestones M3/M4, CSP 0.2.11). **[unconfirmed]** = the doc marks it "to confirm in game". **[code]** = read from source.

---

## 1. AC track format (`docs/ac-format.md`, `core/kn5.py`, `core/package.py`, `pipeline/track_stage.py`)

**Not covered anywhere in this repo:** `cameras.ini`, `ai/pit_lane.ai`, `AC_TIME_n_L/R` sector dummies, track lights or `[LIGHTING]` lamps, normal-map or multilayer shaders, and `map.ini` field meanings. They write `ksEmissive = 0` on every material. Don't take any of those from this repo.

### Folder layout (ac-format.md lines 5–25)
- **Multi-layout track:**
  - `<id>_forward.kn5`, `<id>_reverse.kn5`, each holding the full geometry.
  - `models_forward.ini` / `models_reverse.ini`, each `[MODEL_0] FILE=… POSITION=0,0,0 ROTATION=0,0,0`.
  - Per layout: `<layout>/data/{surfaces,map,lighting,groove,crew,ai_hints}.ini`, `<layout>/ai/fast_lane.ai`, `<layout>/map.png`.
  - `ui/<layout>/{ui_track.json, preview.png, outline.png}`, plus `extension/`.
- **Single layout:** `<id>.kn5` with `data/`, `ai/`, `ui/` at the root and no `models_*.ini`.
- Content Manager silently drops a layout that lacks either its `models_<layout>.ini` or its `ui/<layout>/ui_track.json` (dev-handover.md line 91).
- Plain AC without CSP would not load the multi-layout tracks, and they don't support it [game].
- Their ini files are written with CRLF line endings.

### KN5 binary (`core/kn5.py` lines 1–246) [code; rendering confirmed in game]
- **Header:** `"sc6969"`, int32 version 6, then an extra int32 0 (present when version > 5). Little-endian. Strings are int32 length + ASCII.
- **Textures:** int32 count; each is `{int32 active=1, str name, uint32 len, bytes}`. The bytes are a whole DDS file.
- **Materials:** int32 count; each is `{str name, str shader, u8 blend (0 opaque / 1 alpha blend / 2 alpha-to-coverage), u8 alphaTested, int32 depthMode}`.
  - Then int32 nProps; each prop is `{str name, f32 A, f32 B[2], f32 C[3], f32 D[4]}` (10 floats). Scalars go in A and 3-vectors in C.
  - Then int32 nMaps; each is `{str sampler, int32 slot, str texture}`.
- **Node tree, depth-first:** each node is `int32 class, str name, int32 childCount, u8 active`.
  - Class 1 (dummy): `f32 matrix[16]`, row-major; rows are the X, Y, Z axes, then the translation.
  - Class 2 (mesh): `u8 castShadows, u8 visible, u8 transparent, uint32 nVerts`, then 44-byte vertices `{pos[3], normal[3], uv[2], tangent[3]}`; then `uint32 nIdx` with u16 indices; then `uint32 materialId, uint32 layer, f32 lodIn, f32 lodOut, f32 sphereCentre[3], f32 radius, u8 renderable`.
- **Their tree:** one identity root dummy, with every mesh and `AC_*` dummy as a flat, childless child. **A mesh with children crashes the game.**
- **Limit:** at most 65,535 vertices per mesh, because indices are u16. The index-count field itself is u32 (`MAX_VERTICES`, line 33).
- They always write lodIn = lodOut = 0 (always drawn), layer 0 and transparent 0.
- Tangents are computed as dP/du, Gram-Schmidt against the normal.
- The writer rejects non-ASCII or duplicate names, missing textures and non-finite positions. A reader for diffing is at lines 280–330.
- **Axes:** x = east, y = up, z = −north, in metres around a local origin. That is a rotation, not a mirror. Triangles wind counter-clockwise seen from above, so normals point up [game]. `core/scene.py` has `Z_SIGN = -1`.
- **Dummy frame:** +Z forward, +Y up, X = Y × Z (`dummy_matrix`).
- **Mesh size guidance:**
  - Road chunks are 200 m. Neighbouring chunks share their boundary vertex row, so there is no gap or step.
  - Terrain is gathered into meshes of about 24,000 triangles.
  - Stubs, trunk colliders and furniture are packed per 400 m by material.
  - Measured sizes: Grasstree Hill (12.8 km) is about 420k vertices / 636k triangles and a 29 MB KN5. Lyell Highway is about 1.9M vertices, quoted at 97 / ~122 / ~247 MB per KN5 in different tables (dev-handover.md line 82 and the known-issues tables).

### Materials and shaders (`track_stage.py` lines 31–49 and 90–118)
- Shader is `ksPerPixel`, or `ksPerPixelAT` with DXT5 for alpha-tested materials (`ALPHA_REF` 0.5).
- Properties written: `ksAmbient, ksDiffuse, ksSpecular, ksSpecularEXP, ksEmissive(0,0,0), ksAlphaRef`, plus one `txDiffuse` sampler.

| Material | Amb | Diff | Spec | SpecEXP |
|---|---|---|---|---|
| road | 0.35 | 0.42 | 0.06 | 28 |
| kerb | 0.35 | 0.42 | 0.04 | 20 |
| gravel | 0.36 | 0.44 | 0.02 | 15 |
| grass, terrain | 0.36 | 0.44 | 0.005 | 18 |
| walls (fallback) | 0.4 | 0.6 | 0.05 | 10 |
| roof | 0.38 | 0.55 | 0.2 | 20 |
| water | 0.25 | 0.35 | 0.8 | 90 |

- **Shader gotcha (Content Manager's re-implementation):** `txColor*(ksAmbient*ambient + ksDiffuse*light + ksEmissive) + ksSpecular*(N·H)^EXP*light`. Specular is added on top of the texture, untextured, so black lettering lifts in headlights. Use no specular on signs and liveries (ac-format.md lines 833 and 910).
- Near-white textures at the fallback diffuse 0.6 clip at night under CSP exposure. Cap whites at about 200–224 (lines 829–831 and 907–909).

### Textures (`core/textures.py`) [code]
- All procedural (Pillow + numpy). DXT1 for opaque, DXT5 for alpha. Mip chain down to 4 px, written as a single legacy DDS header; sides must be divisible by 4. Needs Pillow ≥ 11.2 for the DXT encoder.
- PNG atlases (furniture, closures, police cars) are converted to DDS before being embedded in the KN5.
- `map.png`, `preview.png` and `outline.png` stay PNG.
- Road textures map u 0→1 across the carriageway and repeat every 12 m along it (gravel 24 m, 512×2048).

### Physics mesh naming and surfaces (lines 45–73 and 113–152; `package.py` lines 18–56)
- Names start with `1` plus the KEY: `1ROAD_###`, `1GRAVEL_###`, `1GRASS_…`, `1WALL_…`.
- Each physics mesh name must contain **exactly one** KEY, and no KEY may contain another.
- **There is deliberately no `WALL` KEY.** Defining one is reported to make walls driveable; any physics mesh named WALL is a solid barrier anyway.
- Invisible colliders are `1WALL_*` with `isRenderable = 0`. Meshes without a leading digit are visual only.
- `surfaces.ini` values:
  - `ROAD`: friction 0.98, everything else 0.
  - `GRASS`: friction 0.75, `grass.wav`, `DIRT_ADDITIVE=1`, `IS_VALID_TRACK=0`, `SIN_HEIGHT=0.03`, `SIN_LENGTH=0.5`, vibration 0.2/0.6, `_EXT_SURFACE_TYPE=GRASS`.
  - `GRAVEL` (`SURFACE_2`): friction 0.80, damping 0.01, `gravel.wav`, dirt 0.8, valid track, `SIN_HEIGHT 0.01`, `SIN_LENGTH 0.5` (inverse, so a 2 m wavelength), vibration 0.1/0.35, plus `_EXT_SURFACE_TYPE=GRAVEL`, `_EXT_SURFACE_TYPE_MODIFIER=REGULAR`, `_EXT_PERLIN_NOISE=1`, octaves 3, persistence 0.5.
- Surface gotchas:
  - **Never `WAV_PITCH=extended-0`**: it switches on CSP's extended physics, and plain AC crashes on it.
  - Never `grass.wav` on a road: CSP then draws its dirt as grass.
  - At friction 0.88 the AI drove gravel at tarmac pace [game], hence 0.80 [unconfirmed].

### Logic dummies (lines 99–111; `core/layout.py`; `validate.py` line 39)
- The validator requires `AC_PIT_0, AC_START_0, AC_HOTLAP_START_0, AC_AB_START_L/R, AC_AB_FINISH_L/R`. "The track won't load without AC_PIT_0."
- **Grid:** `AC_PIT_k` and `AC_START_k` share each grid spot, up to 8. Spot 0 is on the centreline 8 m behind the start gate. Behind it come pairs 8 m apart, 2 m either side of the centreline where both half-widths are at least 3 m; otherwise single file. No spot is closer than 8 m to the road's end.
- **Spawns** sit 0.3 m above the road, facing +Z along the driving direction [game: all four wheels loaded].
- **Gates:** 0.5 m outside each road edge (L = left of the driving direction). Start gate 50 m in. The finish gate leaves a run-off of real road: 250 m, or 15% of a short route, never under 50 m [game]. `AC_HOTLAP_START_0` sits 30 m before the start gate.
- **`ui_track.json`:**
  - `pitboxes` must equal the number of `AC_PIT_n` dummies. Content Manager offers that number minus one as AI opponents.
  - `geotags` must be two strings, and `length` must carry a unit ("12.80 km").
  - `"priority": 1` marks the default layout.

### `fast_lane.ai`, version 7 (lines 241–307; `ai_line.py` lines 656–685)
- **Header:** `int32 7, N, 0, 0`.
- **Points:** N × `{f32 pos[3], f32 cumulative length, i32 id}`.
- **Extras:** int32 N, then N × 18 floats: speed (m/s), gas, brake, lateral g (0), radius, side left, side right, camber (0), direction (±1), normal[3], length to next, forward[3], tag (0), grade.
- **Trailer:** int32 `hasGrid = 0`; the game builds and caches the grid itself.
- Side left and side right are distances from the line to each road edge, so they sum to the width.
- **Gotchas:**
  - Points must sit **0.4 m above the surface**. Points on the surface crashed the game in another generator.
  - Space points about **5 m** apart. AC measures the spline in float32: 1 m spacing inflated `TRACK LENGTH` by +32.8% on a 63 km road, 5 m by +1.3% [game].
  - End the line 40 m before the road's end, behind an invisible end wall.
  - AC's AI ignores the speeds in the file (it ran 220 km/h against a 130 cap) [game].
- **`data/ai_hints.ini`:** `[HINT_n] START/END/VALUE`, where START and END are fractions of the spline. A hint scales the curvature-derived corner speed, so **only 0 stops a car on a straight**. Their run-off ramp is 0.5, then 0.2, then 0 for the last 60 m [game].
- **Edge margins** from the AI line grow with speed: 1.2 m at 60 km/h, 2.5 m at 120, 3.3 m at 200 [game: fixed cars running off].

### `map.png` / `map.ini` (`package.py` lines 123–141) [code]
- Centreline drawn in AC X/Z, north up, at most 1600 px.
- `[PARAMETERS] WIDTH, HEIGHT, MARGIN=20, SCALE_FACTOR (m/px), MAX_SIZE=1600, X_OFFSET, Z_OFFSET, DRAWING_SIZE=5`.
- What `SCALE_FACTOR` means to the game is listed as unknown (known-issues.md line 15).

### Other ini files (`package.py`) [code]
- `lighting.ini`: `SUN_PITCH_ANGLE=50`, `SUN_HEADING_ANGLE=16`.
- `groove.ini`: `GROOVES_NUMBER=0`.
- `crew.ini`: `SIDE=1`.

### `extension/ext_config.ini` (`package.py` lines 217–282)
- `[GRASS_FX]`: `GRASS_MATERIALS` and `OCCLUDING_MATERIALS` (the road occludes grass); optional custom atlas `TEXTURE=grass_fx/x.dds`, `TEXTURE_GRID=8,4`, `MASK_BLUR=2`, configurations A–D (CSP allows at most four besides the base), `[GRASS_FX_ADJUSTMENT_n]`.
- `[RAIN_FX]`: `PUDDLES_MATERIALS` (road and gravel), `SOAKING_MATERIALS` (seal), `ROUGH_MATERIALS` (grass and gravel).
- `[TYRES_FX]` dirt, grass and soil colour pairs. A track's own section switches CSP's generic one off entirely, so include all three pairs.
- **Water:** `[INCLUDE: common/materials_track.ini]` + `[Material_Water] Materials=water, Type=LAKE|SEA`.
- **Tree FX:** `[TREES] LIST_0=trees/trees.txt`, `SURFACE_MATERIALS=terrain, grass`.
  - `trees.txt` lines: `tree: m.bin; pos=x,y,z; angle=…; size=…; width=…`.
  - **No comment lines:** CSP 0.2.11 then loaded no trees at all [game].
  - The `.bin` model format is documented in the `core/treefx.py` docstring.
  - Tree FX trees have no physics, so they add invisible 8-sided trunk prisms within 20 m of the road.
- **Night reflectors:** `[MATERIAL_ADJUSTMENT_n] CONDITION=NIGHT_SMOOTH KEY_0=ksDiffuse VALUE_0 / VALUE_0_OFF` with `[INCLUDE: common/conditions.ini]`.
- **Not used:** `[WIND] DYNAMIC_CABLES` (redraws wires about 8 times thicker [game]) and `ksPerPixel_tilingfix` (breaks wheel-path textures).
- **Frame-rate costs** [game, GTX 1660 Ti at 1440p]:
  - Tree FX at about 2,500 trees/km costs about 60% of frame rate.
  - About 0.3% per extra tree model.
  - Grass FX on pasture costs about 5%.
  - 7 AI cars cost about 1%.

---

## 2. Top 20 from `docs/known-issues.md`, with fixes
1. **Coarse DEM camber is noise.** On a 4 m road the two samples are 3 m apart and catch the hillside. Fix: camber cap tied to width (4% up to 5 m, 7% from 6.4 m) and always keep ≥ 0.5% crown (lines 85–88; ac-format line 81).
2. **No superelevation on coarse DEM stretches.** Real curves are banked; the maintainer chose not to add design banking, so the AI needs hints instead (line 128).
3. **The OSM line runs up a cutting**, giving a 5.3 m height error and a 1 g sag. Fix: take heights from the flat road strip beside the line on LiDAR (lines 356–361).
4. **A bare-earth DEM shows embankments or pre-bridge ground** (+7.9 m hump, 38.6% grade). Fix: bridge humps near crossings with a grey-scale opening (lines 362–367).
5. **Coarse DEM in general.** Profile filter of max(default, 8 × cell), 15% grade cap, flat camber, no guard rails (`profile_stage.py` lines 75–110; data-sources.md line 61).
6. **Terrain holes from unconstrained Delaunay** at skewed junctions. Fix: constrained Delaunay with the road outline as edges (lines 194–195).
7. **Sub-millimetre cracks after float32 rounding**, found 4.4 km from the origin. Fix: never put a terrain vertex at a crossing neither neighbour has; share an existing edge end, or sit 2 cm inside both (line 196).
8. **Seams at junctions.** Stubs share the mainline edge vertices exactly. Each stub is checked for gap or step under 5 cm, no hole within 3 m, and no ground more than 2 cm above it. A stub that fails is dropped and the meshes rebuilt (ac-format lines 409–414).
9. **Overlapping side-road mouths.** Merge them into one cluster patch; arms that join within 100 m are dropped (lines 185–191).
10. **Flares fold** on the inside of tight bends. Redraw at half, then quarter radius, else drop the stub (line 192).
11. **AI runs 1.0–1.3 m wide at speed.** Fix: speed-dependent edge margin [game: fixed] (lines 96–99).
12. **AI goes off at crest-plus-descent bends.** Fix: grip-based pace hints in `ai_hints.ini` (lines 112–117).
13. **AI slides out where the line apexes early on a descent.** Fix: keep 3.85 m from the outside edge there [game: fixed] (lines 118–127).
14. **AI at the end of a point-to-point line** turns round or crawls off. Fix: run-off, line ends 40 m short, final hint 0, end walls (lines 38–40 and 51–55).
15. **Plain AC without CSP:** won't load multi-layout tracks, rebuilds the AI grid for 4 min on every load, and its AI crashed on the open line. Requiring CSP is the "fix" (line 35).
16. **Pit boxes are the grid spots on the road**, so practice AI bump cars still standing ahead (lines 58–59).
17. **Tree FX cost:** about 60% of frame rate at 2,500 trees/km, mostly trees near the road. Thin with distance bands and a per-km cap. The billboard fade distance is unknown (lines 37 and 134–147).
18. **Grass FX cost:** pasture greens hit 5.4%. Visible rows from texture repeat were fixed by warping UVs; blocky class edges by dithering (lines 154–157).
19. **Night washout** of signs and props. Remove specular and lower whites and night diffuse (ac-format lines 827–836 and 902–919).
20. **Memory and size:** a 63 km build peaks at 2.5–2.7 GiB; KN5s reach 120–250 MB; float32 drift grows with distance from the origin (lines 8 and 108).

---

## 3. Single route or a network?
**Single route.** `job.py` takes 2 to 25 ordered waypoints (`MAX_WAYPOINTS = 25`) and a 64 km maximum (the hard limit is 75). `graph.route()` finds the shortest class-weighted path through them, and everything downstream (centreline, `Ribbon`, `build_ribbon`, the terrain footprint) works from that one polyline.

How it treats other roads:
- Side roads become **100 m stubs closed off the stage** with tape, boards, bales or police cars (`core/junctions.py`, `core/stubs.py`).
- A roundabout is drawn whole only if the route drives it.
- Roads crossing the route are drawn for about 150 m.
- Terrain is a corridor 700 m either side of the route; "the world ends there".

`RoadGraph` (`providers/osm/graph.py` lines 38–47) is a general OSM graph with one-way rules and could feed a network mesher. But mapcreator has no code that meshes a network or a whole area.

---

## 4. Data sources (`docs/data-sources.md`)
- **Global, usable in Lebanon:**
  - OSM (Geofabrik has a Lebanon extract; the index builder is region-agnostic).
  - ESA WorldCover 10 m trees (`providers/esa/worldcover.py`).
  - Meta/WRI canopy mask (global, by quadkey).
  - Poly Haven / ambientCG textures.
  - Copernicus GLO-30, which is listed (line 67) but **has no provider**.
- **Australia-only:** theLIST (DEM, canopy, TASVEG, buildings, power), GA DEM-S and 5 m, Vicmap, the Queensland and NSW DEMs, NVIS, SVTM, and the GraphHopper deploy config.
- **Adding GLO-30 or a custom GeoTIFF is easy.** `BlockRaster` (`providers/raster.py`) already reads any GeoTIFF by tile, reprojects and caches; `GaDemS` is about 10 lines on top of it (`resolution_m = 30`). The Region/provider split keeps `core/` untouched. You would need to:
  - Write a provider subclass of `BlockRaster` for the local GLO-30 file.
  - Add a Lebanon `Region` with EPSG:32636 (UTM 36N); `australia()` hard-codes `28300 + zone` EPSG codes.
  - Change `region_for` / `same_region`, which raise `OutOfArea` outside Australia.
  - Change `LONLAT_CRS = 7844` (GDA2020) in `providers/base.py` and the 4326→7844 remap in `raster.py`; both should become 4326 for Lebanon.
  - Set the `height_datum`/`country` defaults ("AHD", "Australia").
- **Caveats for GLO-30:**
  - At 30 m it takes the coarse branch (`resolution_m > FINE_DEM_M = 5`): heavy profile smoothing, 15% grade cap, no camber.
  - It is a **surface model that includes trees and buildings**, so roads under canopy or in villages will bump unless you burn the road profile into it. That last point is my inference, not the repo's.

---

## 5. Harness (`harness/`)
- **Two kinds of subcommand:**
  - File-only, which would port to Linux with path config: `install` (copies into `content/tracks` and deletes `cache/ai_grids` and `ai_payloads` entries for the track), `check-log`, `results`, `probe-install`, `probe-points`, `probe-report`, `watch-report`, `prepare`/`restore`.
  - Windows-bound: `probe` (`ctypes.windll` + `OpenFileMappingW` on `Local\acpmf_physics` / `acpmf_graphics`), `_documents()` (`SHGetKnownFolderPath`, though it falls back to `~/Documents`), and `showroom`/`install-cm`/`launch`/`race`, which `Popen` Content Manager.exe with `acmanager://race/config?configFile=<tempfile>`.
- **`prepare`/`restore`** patch `Documents/Assetto Corsa/cfg/race.ini` directly "for starting AC without CM". That is the path most portable to Proton.
- **`check-log`:** `log.txt` must contain `Creating physics track: <id>` (with CSP) or `LOADING MODEL content/tracks/<id>`, plus `STARTING PHYSICS ENGINE`, and no `ERROR:` lines naming the track. In `custom_shaders_patch.log`, failures are marked with an explosion emoji or "FAILED"; it also reports the `Setting chunks for:` and `Loading trees:` lines.
- **`mc_probe.lua`** (CSP app):
  - Reads `points.json` from `ac.getFolder(ac.FolderID.ACDocuments)/mapcreator_probe` and presses Drive (`ac.tryToStart` when `sim.isInMainMenu`).
  - Teleports with `physics.setCarPosition`, passing the **reversed** direction because CSP 0.2.11 faces the car against the vector it is given. Waits 1.2 s to settle.
  - Records each wheel's `contactPoint`, `surfaceValidTrack` and `surfaceSectionIndex`, `wheelsOutside`, `physics.raycastTrack` downward (finds collision holes), `ac.worldCoordinateToTrack` (lateral offset and progress), `ac.getSim().fps`, and optional screenshots.
  - Writes `results.json` with `io.save`, deletes the points with `io.deleteFile` (`os.remove` is a stub in the sandbox), and can call `ac.shutdownAssettoCorsa()`.
  - The report fails on a teleport off by more than 3 m, a wheel gap over 1 m, an invalid surface, a raycast miss, or lateral offset over 1.
- **`mc_watch.lua`:** runs only if a `watch.on` file exists. Logs every car's position, heading, speed, `splinePosition`, laps, `isAIControlled`, wheel loads, damage and fps: 4 Hz for the first 15 s, then 1 Hz. Rewrites `watch.json` every 5 s.
- **Under Proton (my inference, not tested by the repo):** the Lua apps only use CSP's Documents folder, so they should work as-is inside the prefix (`.../compatdata/244210/pfx/drive_c/users/steamuser/Documents/Assetto Corsa/`). The Python side needs `ac_docs` and `ac_root` pointed into the prefix and Steam library. The shared-memory probe and the Content Manager launch need replacing.

---

## 6. Workflow advice (`docs/dev-handover.md`, `CLAUDE.md`)
- Each stage writes to disk and can be rerun alone (`mapcreator <stage> job.json`).
- A static `validate` stage reads every file back: spawn and AI-point heights measured against the actual road triangles, a ground-hole check within 100 m of a road, gates, surface KEYs, `pitboxes`.
- Order of in-game checks: look in the showroom first, install, launch, probe wheel loads, results, check-log, then the reverse layout, then 8-car AI races and watch-report.
- If a track won't load, load another generator's demo track (road-to-assetto) as a control, then diff the KN5s with `kn5.read`.
- Record in-game answers and move lasting ones into known-issues.
- Keep "questions only the game can answer" as named defaults in one place each (handover table, lines 113–128).
- Build with no GPU, Blender or game. No Google/Esri/Bing/Mapbox data.
- When changing the AI line, re-measure `TRACK LENGTH` and compare frame rates in interleaved sessions; their PC lost about 2.4% per run as it warmed.

## 7. KN5 writing
Pure Python (numpy + struct) in `core/kn5.py`, about 330 lines including a reader. There is no Blender, ksEditor or Windows dependency (`architecture.md` line 39). Textures are made procedurally with Pillow and numpy and encoded to DDS in `core/textures.py`. The format was re-implemented from descriptions; the sources are listed in `THIRD_PARTY_NOTICES.md` lines 21–31: road-to-assetto, ac-track-studio, actools.

## 8. Security skim
- `subprocess.Popen([cm_path, *args])` at `harness/ac_harness.py` line 104 (no shell).
- `subprocess.run(["taskkill", …])` at `service/worker.py` line 449.
- Tests use `subprocess` for `git ls-files` and dummy child processes.
- No `os.system`, `eval`/`exec`, `shell=True`, pickle or `yaml.load`.
- Network hosts:
  - Data: `data.source.coop`, `services.thelist.tas.gov.au`, `listdata.thelist.tas.gov.au`, `dea-public-data.s3.ap-southeast-2.amazonaws.com`, `services.ga.gov.au`, `tiles-ap1.arcgis.com` (Vicmap), `esa-worldcover.s3.eu-central-1.amazonaws.com`, `dataforgood-fb-data.s3.amazonaws.com`, `spatial-img.information.qld.gov.au`, `maps.six.nsw.gov.au`, `overpass-api.de`.
  - Web front end: `tiles.openfreemap.org`, `challenges.cloudflare.com` (Turnstile).
  - Placeholders (`*.example.org`) and internal `graphhopper`/`egress`.
- Nothing unexpected. The egress allowlist is in `deploy/examples/egress-allowlist.txt`.

---

## Verdict for the Koura free-roam map
- **Reuse as code (Apache-2.0, keep attribution):**
  - `core/kn5.py`: writer and reader.
  - `core/textures.py`: `to_dds`.
  - `ai_line.write`/`read`: fast_lane v7.
  - `package.py`: `surfaces_ini`, `ext_config_ini`, `ui_track_json`, `map_files`, `models_ini`.
  - `core/treefx.py`: Tree FX `.bin`/`trees.txt`.
  - `providers/raster.py`: `BlockRaster`, for a local GLO-30 file.
  - `providers/osm/index.py`: OSM to SQLite with R*Tree.
  - The KN5-level checks in `core/validate.py`, especially the ground-hole and spawn-height checks.
  - `harness/csp_app/mc_probe` and `mc_watch`: the Lua apps should port to Proton, but this is untested.
- **Reuse as knowledge:**
  - The format reference and naming rules in section 1.
  - No children on mesh nodes; u16 indices.
  - No `WALL` KEY; no `extended-0`.
  - AI points 0.4 m above the road, 5 m apart.
  - Hints only slow bends; only 0 stops a car.
  - No comment lines in `trees.txt`.
  - Constrained terrain triangulation and shared seam vertices.
  - Coarse-DEM smoothing and grade caps.
  - Frame-rate budgets for trees and grass.
- **Write your own:**
  - A network or area mesher: junction polygons for real intersections, terrain over the whole 12 km box, chunked into meshes under 65,535 vertices.
  - Free-roam logic: a single `AC_START`/`AC_PIT` set, probably no A/B gates.
  - `cameras.ini`, lights, and the Lebanon region/CRS plumbing.
  - A DEM-under-canopy fix for GLO-30.