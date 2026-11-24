# Work packages

Read `PLAN.md` first. Each package lists what it changes, the steps, the gate, the evidence to save, and what to do if it fails. "Spec A1" and the like refer to sections of `specs/openlaps-change-specs.md`; "Harness 2" refers to `specs/ingame-harness-specs.md`. Those files quote the code to change.

Paths: `AC`, `PFX`, `DOCS` as defined in `VERIFY.md`.

---

## WP0. Setup and baseline

**Changes:** project root only. No fork edits.

**Steps**

1. `git init` in the project root. The `.gitignore` is already there.
2. Bootstrap Python 3.12 (system Python 3.15 does not work, and `uv` is not installed system-wide):
   ```
   python3 -m venv .bootstrap && .bootstrap/bin/pip install uv
   .bootstrap/bin/uv venv --python 3.12 .venv
   git clone https://github.com/theopenlaps/openlaps
   git -C openlaps checkout -b koura d9e713c66c01417fb035c65b81d77093094742c6
   .bootstrap/bin/uv pip install --python .venv/bin/python -e "./openlaps[dev]"
   export OPENLAPS_CACHE=$PWD/cache
   ```
3. Run the fork's tests: `cd openlaps && ../.venv/bin/python -m pytest -q`. Record pass count and time.
4. Clone the two reference projects next to it for reading and for the files borrowed later, at the commits in `REFERENCES.md`: `mapcreator/`, `road-to-assetto/`. Add both to `.gitignore`. Do not install them.
5. Rebuild the trial with the unmodified fork, to confirm the environment:
   ```
   .venv/bin/openlaps --centro 34.3616,35.8390 --tam 1000 --nombre btouratij_poc --ac --salida out/poc
   ```
   Expect about two minutes and output matching `evidence/btouratij_poc.json` (8.2 km of road, 40 junctions, about 211 buildings).
6. Run every inner-ring tool from `VERIFY.md` by hand on `out/poc` and save each raw output under `out/poc/verify/`. Note the exact output format of each; `koura/verify_static.py` will parse these.
7. Record the baseline in `PROGRESS.md`: steps, seams, holes and grade breaks per km of road; draw calls median and p95; meshes; triangles; texture MB; collider meshes present (expect none in the game export: that is the defect fixed in WP2).
8. **OSM snapshot.** `pipeline.run` accepts `osm_data`. Read how the fork's OSM source returns data (`sources/osm.py`: the raw element list before `parse`, and its on-disk cache format) and save one snapshot covering the S3 rectangle plus 300 m to `cache/osm_koura.json`, fetched in four quarter-boxes with a pause between them. Record the date. If `osm_data` cannot take it directly, write the snapshot into the fork's cache under the keys it would use. Only if neither works, fall back to the Geofabrik extract in WP7.
9. **Baseline at the stage resolutions.** Terrain grid size is chosen automatically from the rectangle area (2 m up to 2.5 km², 3 m up to 8 km², else 4 m), so a 1 km trial is not comparable with a stage build. Rebuild the trial three times with `--res 2`, `--res 3` and `--res 4` and record checks 7 and 8 for each. Stages set `--res` explicitly from `terrain_res_m` in `zone.json`.
10. Write `koura/config.toml` with `ac_root`, `ac_docs`, `cache`, and `koura/verify_static.py` implementing the table in `VERIFY.md`. Checks 5 and 6 are expected to fail on the baseline; mark them "expected fail until WP2 / WP6".

**Gate:** tests pass; trial rebuilds; `out/poc/verify.json` exists with every check filled in.

**Evidence:** `out/poc/verify.json`, baseline table in `PROGRESS.md`.

**If it fails:** a dependency problem on Python 3.12 is the likely cause. Pin the failing package to the version in the fork's lock or CI file; do not move to another Python version without recording why.

---

## WP1. Game launch spike and probe (lane A, time-boxed to 90 minutes)

**Purpose:** find out whether an agent can start the game on this machine, load a track and get data back. Three questions must be answered and written down, whatever the outcome:

1. Does `acs.exe` start from a shell in this Proton prefix?
2. Does Custom Shaders Patch load when started that way?
3. Does a Lua app with `LAZY = NONE` run without anyone opening its window?

**Changes:** `koura/ac/*`, files under `$AC/apps/lua/koura_probe/`, `$AC/steam_appid.txt`, `$AC/content/tracks/btouratij_poc/`. `$DOCS/cfg/race.ini` is patched and restored.

**Facts already known**

- Steam, `protontricks-launch` and `gamescope` are installed. The session is KDE on Wayland. GE-Proton9-20 is in `~/.steam/root/compatibilitytools.d/`.
- Content Manager is installed in the prefix: its data folder is `$PFX/drive_c/users/steamuser/AppData/Local/AcTools Content Manager/`, and `race.ini` carries its `__CM_` keys. `$AC` contains both `AssettoCorsa.exe` and `AssettoCorsa_original.exe`, which suggests Content Manager replaced the launcher, so starting the game from Steam probably opens Content Manager. That is a guess.
- Lua apps on this install live in `$AC/apps/lua/`. `$DOCS/cfg/python.ini` only lists Python apps.
- The game window will open on the owner's desktop. Do this when they are not using the machine, or say so in the session notes.
- Steam must be running and logged in.

**Steps**

1. `koura/ac/install.py`: copy `out/poc/assetto_corsa/btouratij_poc` to `$AC/content/tracks/`.
2. `koura/ac/race_ini.py prepare <track> [--car abarth500]` and `restore`. Follow Harness 1 (`_patched_race_ini`) and Harness 4:
   - read with `utf-8-sig`, keep key case, write without spaces around `=`;
   - back up once to `race.ini.koura-backup`;
   - remove every `CAR_n` except `CAR_0`, every `SESSION_n` except `SESSION_0`, every `CONDITION_n`, `[EVENT]`, `[SPECIAL_EVENT]`, the key `_EXT_SETUP_FILENAME` in `CAR_0`, and any `__CM_CUSTOM_MODE` line;
   - set `[RACE] TRACK=<id>, CONFIG_TRACK=` (empty; a layout name on a single-layout track hangs the game), `MODEL=<car>, CARS=1, PENALTIES=0`;
   - set `[CAR_0] MODEL=-, SKIN=<first folder in $AC/content/cars/<car>/skins>, SETUP=`;
   - set `[SESSION_0] NAME=Practice, TYPE=1, DURATION_MINUTES=0, SPAWN_SET=PIT`;
   - set `ACTIVE=0` in `[REMOTE]`, `[REPLAY]`, `[BENCHMARK]`, `[RESTART]`; set `[AUTOSPAWN] ACTIVE=1`.
3. Adapt the probe app. Copy `mapcreator/harness/csp_app/mc_probe/` to `koura/ac/koura_probe/`, rename ids, keep `LAZY = NONE`, and change (Harness 2):
   - data folder `ac.getFolder(ac.FolderID.ACDocuments) .. '/koura_probe'`;
   - remove the `ac.worldCoordinateToTrack` call and the `lateral` and `progress` fields;
   - keep the reversed direction vector in `physics.setCarPosition` (CSP 0.2.11 faces the car against the vector it is given), the 1.2 s settle time, wheel contact, surface index, raycast, frame rate, screenshots, the `status.json` writes and `ac.shutdownAssettoCorsa()` when `quit` is set;
   - keep `ac.tryToStart(true)` while `sim.isInMainMenu`, which presses Drive.
   Install to `$AC/apps/lua/koura_probe/`.
4. Hand-write a three-point `points.json` for the trial track at its spawn (read `AC_START_0` from `kn5_inspect.py --json`; position plus 1.0 m in y; direction from the marker matrix). Schema in Harness 1.
5. `koura/ac/launch.py`. Write `244210` to `$AC/steam_appid.txt` if missing. Try these in order, each with a 180 s timeout, stopping at the first that produces `status.json`:
   - a. Direct, through Proton:
     ```
     cd "$AC" && STEAM_COMPAT_CLIENT_INSTALL_PATH=$HOME/.steam/steam \
       STEAM_COMPAT_DATA_PATH=/mnt/Linux_HDD/SteamLibrary/steamapps/compatdata/244210 \
       $HOME/.steam/root/compatibilitytools.d/GE-Proton9-20/proton run acs.exe
     ```
   - b. `cd "$AC" && protontricks-launch --appid 244210 acs.exe`
   - c. `steam -applaunch 244210`, which probably opens Content Manager and needs a person to press Go. Use only to confirm the track loads at all.
   After each attempt: wait for `$DOCS/koura_probe/status.json` with `state` `done`, or the timeout; then end the game process (`pkill -f 'acs\.exe'`) and run `race_ini.py restore` in a `finally` block.
6. `koura/ac/probe_report.py` implementing the outer-ring table in `VERIFY.md`.
7. Write the three answers, the working launch command and the time from launch to results into `PROGRESS.md`.

**Gate:** either the probe report passes on the trial track, or the three questions are answered with the exact failure output and the decision "game ring unavailable" is recorded.

**Evidence:** `out/poc/ingame/results.json`, copies of `log.txt` and `custom_shaders_patch.log`, screenshots.

**If it fails:** continue without the outer ring. Every later gate then reads "inner ring passes; owner must drive", and the list of things for the owner to check accumulates in `PROGRESS.md`. If only question 3 fails (the app does not run unopened), try enabling the app once by hand through the in-game app bar, which CSP remembers, and record that the owner has to do that once.

---

## WP2. Export fixes for free roam (lane B)

**Changes:** `openlaps/openlaps/barriers.py`, `mesh.py`, `pipeline.py`, `export_ac.py`.

**Steps**

1. **Keep colliders in the game export.** Spec E2. The game export deletes the whole `col` group to remove the boundary wall, which also deletes lamp posts, sign posts, tree trunks and pylon bases.
   - In `barriers.boundary`, change both `scene.add("col", "invisible", ...)` calls to group `"limite"`.
   - In `mesh.py`, add `"limite": 0` to `GROUP_LOD` and `"limite"` to `NO_SHADOW`.
   - In `pipeline.py`, replace the block that deletes `k[0] == "col"` so that nothing is deleted by default. Add a flag `--sin-muro` that deletes group `"limite"` only.
2. **Pin the spawn.** Spec E1. Add an optional target to `_place_free`: when `args.salida_en` (a local x, y) is set, score candidate road stretches by distance to it instead of distance to the origin. Add CLI flag `--salida-en lat,lon`. Keep the rule that skips tunnels and bridges.
3. **English text.** Spec E3. Translate the description and the traffic sentence, map the tag `libre` to `free-roam`, set `info["city"] = "Koura"`, keep the tag `traffic-planner-ready` exactly. Translate `pipeline.ATTRIBUTION`.
4. **Probe points export.** After the road network is final, write `out/<stage>/probe_points.json`: one point every 150 m along every road edge with runs inside the zone, plus one at each junction, as lat/lon plus local x, y, z and a unit direction. `koura/ac/probe_points.py` converts to game axes (x = east, y = up, z = minus north) and adds 1.0 m of height. Mark each point with its road class so reports can be filtered to main roads.
5. Add tests for 1 and 2 beside the existing ones.

**Owner-reported edge bug (drove the trial on 2026-11-23), fix it in this package.** At the edge of the map a Spanish message appeared ("Limite de la zona: activa el modo en vivo en Ajustes CSP (OpenLaps · Modo en vivo)") and the car could not go back. Cause, read in the code: `export_ac.py` writes a standby copy of the live-mode script into every track (`V.escribir_lua(..., modo_espera=True, ...)` and appends `[SCRIPT_0] SCRIPT=vivo.lua` to `ext_config.ini`). That script draws the message within 18 m of the edge (`cercaBorde = m < 18` in `vivo_ac.lua`) and also moves the car back to a "safe" spot when it thinks the car is falling (`physics.setCarPosition(0, seguro.pos ...)`). The trial also had no edge wall, because the export deleted it (step 1). What the owner wants: no message, no script taking over the car; an invisible wall, or simply grass to run onto, and always able to turn round and drive back.
   - Add a flag `--sin-vivo` (set by `koura/build.py` for every build). With it, do not call `V.escribir_lua`, do not append the `[SCRIPT_0]` block, and delete any `extension/vivo.lua` left in the output folder.
   - Keep the invisible edge wall from step 1 (group `limite`, physics `WALL`). Make sure it is never closer than 6 m to a road edge that continues past the zone: where a road crosses the zone edge, end the road mesh at the edge, put the wall across it, and place a row of plastic barriers or a mound 10 m before it as a visible cue.
   - The ground just inside the wall must be drivable grass at terrain height, so a car that hits the wall can reverse and turn.
   - Test: add a probe point 5 m inside the wall on a cut road; the car must rest there with wheels on ground, and `ext_config.ini` must contain no `vivo.lua`.

**Start points, so every part can be reached.** `zone.json` has a `spawn_points` list (Btouratij, Nakhle, Ras Masqa junction, Aaba, Bishmizzine, Kfar Hazir, Amioun, Kousba, Bsarma, Tourza turn-off, Karting Mania paddock). For each one inside the stage being built, snap to the nearest road at least 5 m wide and write one `AC_PIT_n` and one `AC_START_n` marker there, in list order, so Btouratij is slot 0. Set `pitboxes` in `ui_track.json` to the count. The owner picks the start in Content Manager by choosing the grid or pit position. Mention in the track description which slot is which place.

**Gate:** rebuild the trial through the CLI; no `vivo.lua` in the output and no `SCRIPT=vivo.lua` line; `verify_static` check 5 passes (collider meshes present, boundary wall present); spawn is on the main road through Btouratij; `pytest` passes.

**Evidence:** `out/poc2/verify.json`, a `render.py` image at the spawn.

**If it fails:** if keeping the boundary wall breaks the live-mode extension (the reason upstream removed it), keep the wall and note that live mode needs `--sin-muro`.

---

## WP3. Lebanon profile (lane B, after WP2)

**Changes:** `openlaps/openlaps/regions.py`, `roads.py` (`_attrs`), `buildings.py`, `vegetation.py`, `foliage.py`, `textures.py`, `sources/rasters.py`, `pipeline.py`, `__main__.py`, `tests/test_geo_regions.py`.

**Steps**

1. **Profile.** Spec A1 to A6. Add `LB = Region(code="lb", name="Lebanon", country="Lebanon", ...)`:
   - `roof="pitched"`, `flat_from_floors=3`, plus the new `pitched_share` below, so low houses are sometimes tiled and everything else is flat;
   - `tinaco=True`, `facade_style="eu"`, `levels_default=(2, 2, 3, 3, 4)`;
   - facade colours: eight values (tests require exactly eight if subregions are added) in limestone, cream, pale grey and white;
   - `species=("olivo", "pino", "encino", "arbusto", "cipres")`;
   - `stop_text="STOP"`, `curve_sign="triangle"`, `delineator="plain"`, white markings;
   - `ortho="lb_xyz"`, `ortho_mpp=0.5` (reader arrives in WP4; until then it falls back and check 1 fails, which is expected);
   - attribution lines for the imagery.
   Add to `REGIONS`. In `detect`, add `if 33.0 <= lat <= 34.7 and 35.0 <= lon <= 36.7: return LB` before the Europe box. Update the `--region` help text. Add `(34.33, 35.82, "lb")` to `tests/test_geo_regions.py`.
2. **Roof mix.** Spec A5. Add `pitched_share: float = 0.0` to `Region`; set 0.3 for `lb`. In `buildings.build`, after `floors` is computed and before the `roof:shape` override, set `pitched = _h((i, "roofmix")) < R.pitched_share` for buildings that are not churches or sheds, under 1500 m², and below `flat_from_floors`.
3. **Road width.** Spec F2. `lane_mult` currently moves markings only. In `_attrs`, compute `carriage` from `e.lane_w` in both places. Then set `lane_mult` for `lb` so that defaults match Koura: start at 0.9 and correct in WP9 from footage. Check that other regions are unchanged (their `lane_mult` is 1.0).
4. **Seasons.** Spec B4. Add `s2_months` to `Region`; for `lb` use dry June 1 to October 15 and wet December 1 to March 31. Build the Sentinel-2 date ranges from it with year wrap, add the region code to the STAC cache key, and bump the cache `version` on `sentinel2` and `sentinel2_ndwi`. The default season for `lb` builds is dry.
5. **Olives in orchards.** Spec C1 to C3. Vegetation never sees OSM land use.
   - In `pipeline.py` before the vegetation call, build `huertos` from OSM areas tagged `landuse=orchard`, or `landuse=farmland` with `trees=olive_trees` or `crop=olives`.
   - Pass it to `V.build` and on to `_build_from_canopy` as `orchards=None`.
   - Inside orchards, any canopy point taller than 1.5 m is `olivo`. Where the canopy map shows fewer than one tree per 100 m², add a 7 m grid of olives 3.5 to 5 m tall.
   - Remove the rule that reclasses trees over 6 m as forest when they are inside an orchard.
6. **Other species.** Add `_choose_lb` and dispatch on `active().code == "lb"`: forest is pine 50%, oak 30%, cypress 20%; shrubland is shrub; grass and crop land is olive 60%, otherwise oak or shrub; built-up land is cypress, olive and pine, never "tropical".
7. **Cypress.** Spec C3 item 4 lists every place a new species must be registered: `vegetation.SPECIES` `(12.0, 0.25)`, `foliage.LEAF`, `foliage.LEAF_ASSETS`, a narrow column variant of the `pine()` sprite, the kind lists in `photo_sprite` and `tree_sprite`, the material registration tuple in `textures.py`, the `big` set in `_emit`, and a `map_species` fallback `"cipres": "pino"`. Bump `foliage.SPRITE_VERSION`.

**Gate:** trial rebuild auto-detects `lb`; check 12 passes; renders show flat roofs with water tanks, some tiled roofs, olive trees in the groves east of Btouratij; `pytest` passes.

**Evidence:** `out/poc3/verify.json`, six renders, the species counts from the build log.

**If it fails:** cypress is the riskiest item (new sprite). If it does not render correctly within an hour, leave it out and map `cipres` to `pino`.

---

## WP4. Aerial imagery reader (lane C)

**Changes:** `openlaps/openlaps/sources/rasters.py`, `pipeline.py` (two places), a new test.

**Steps**

1. Spec B1, B3, B5. Add:
   ```python
   ORTHO_XYZ = {"lb_xyz": ("https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}", 18)}
   ```
   and a class `XYZRaster` with one public method matching the existing raster contract:
   `sample(proj, x, y, order=1, mode="nearest") -> float32 array of shape x.shape + (3,)`, where `x`, `y` are local metres from `proj.ox`, `proj.oy` in `EPSG:proj.epsg`, and missing pixels are 0 (the painter treats an RGB sum of 15 or less as missing).
2. Inside `sample`: convert to EPSG:3857; find the tile range covering the request; fetch each tile with `cache.fetch(url, ext=".jpg")` using a thread pool of 4; decode into a least-recently-used dictionary capped at about 400 tiles; assemble a local mosaic; call `map_coordinates`. Tile maths:
   - `tx = floor((lon + 180) / 360 * 2^z)`, `ty = floor((1 - asinh(tan(lat)) / pi) / 2 * 2^z)`;
   - tile size in metres `256 * 2 * pi * 6378137 / (256 * 2^z)`; origin `(-20037508.3428, 20037508.3428)`.
3. When one `sample` call covers more than 600 tiles (the land-cover panel samples the whole rectangle at once), drop to a lower zoom for that call.
4. In `ortho()`, add at the top: `if source in ORTHO_XYZ: return XYZRaster(...)`. No other caller changes.
5. Force 0.5 m ground texture: in `pipeline.py`, `mpp = args.mpp or (min(0.25, R.ortho_mpp) ...)` becomes `R.ortho_mpp` when the source is an XYZ source.
6. Remove the coupling that turns imagery and canopy off above 24 km² when the imagery source is lazy (Spec D4, the block that sets `args.sin_orto = args.sin_dosel = True`). Keep canopy off only if memory is a problem at S2; measure first.
7. Mirror the call in `precargar` so live mode would also work.
8. Be a polite client: at most 4 concurrent requests, a generic user agent, everything cached to disk, never refetch a cached tile. A zoom-18 tile covers about 126 m here, so the S2 detailed ground needs roughly 1,100 tiles and the whole S2 rectangle about 3,900. Fetch tiles only where the painter asks for them.
9. **Fail loudly.** The existing pipeline treats a `None` return as "no imagery" and falls back to 10 m satellite colour without saying so, and a lazy reader would otherwise hide failed tiles as procedural colour. So: at construction, fetch one tile at the box centre and return `None` if it fails; count tiles fetched, served from cache and failed; and log one line at the end of the build, `ortofoto lb_xyz: <ok> ok, <failed> failed`. `verify_static` check 1 reads that line.
10. Test with a fake tile server fixture (the fork's tests are offline): a 2 x 2 tile mosaic sampled at known points.

**Gate:** trial rebuild log contains the `ortofoto lb_xyz:` summary with zero failed tiles; check 1 passes; the baked top-down image shows individual roofs and lines up with OSM roads within about 3 m; peak memory recorded.

**Evidence:** `out/poc4/` top-down image beside `evidence/btouratij_poc_cenital.jpg`, `verify.json`.

**If it fails:** if the tile host refuses automated requests, do not work around it. Fall back to Sentinel-2 at 10 m, record it, and ask the owner whether they have another imagery source.

---

## WP5. Zone build and stage 1

**Changes:** `openlaps/openlaps/pipeline.py`, `__main__.py`, `tests/test_rally.py`; new `koura/build.py`.

**Steps**

1. **Zone in free roam.** Spec D4. Today the corridor only exists for stage and circuit modes with a route.
   - Add `zona_externa=None` to `pipeline.run`. When given (a shapely polygon in local metres), use it as `zona` and skip the route-derived buffer.
   - Everything that already consumes `zona` then applies: `net.acotar`, `solo_en_zona`, the building filter, water, `terr.zona`, `BR.boundary(..., zona)`, vegetation exclusion, horizon fill.
   - `ancho_corredor` stays as is for route modes. Update `tests/test_rally.py` only if its free-roam assertion breaks.
   - Check that `traffic.json` lanes are limited to the zone (they derive from the bounded network; confirm with `trafico_check.py --zona`).
2. **`koura/build.py <stage>`.**
   - Read `handoff/inputs/zone.json`. Build the stage polygon in local metres: boxes, route buffers and village discs, unioned. For `route_buffer`, buffer the dense `polyline` stored in `zone.json` directly. It follows the road; do not thin it to sparse waypoints, because a straight-line buffer between distant points can leave the real road and the zone edge would then wall the loop off.
   - Compare the polygon area and rounded rectangle with the `expected` values in `zone.json` (S1 10.0 km², S2 27.5 km², S3 96.5 km²) and stop if they differ by more than 2%: that means the projection or origin is wrong.
   - Round the polygon's bounds outward to multiples of 512 m to get the rectangle.
   - `proj = LocalProjection.marco(origin.lat, origin.lon, rect)`.
   - Build the argument namespace the CLI would build (`--modo libre --ac --region lb --mpp 0.5 --res <terrain_res_m> --salida-en <spawn> --nombre koura --titulo "Koura"`), and call `pipeline.run(args, proj=proj, zona_externa=polygon, osm_data=<snapshot>)`.
   - Tee the log to `out/<stage>/build.log`; record wall time and peak memory (`resource.getrusage`).
   - The track id is always `koura`, so each stage replaces the last in the game.
3. Add the six render viewpoints to `zone.json` (lat, lon, height, look-at) and have `verify_static.py` render them.
4. **Build S1.** `python koura/build.py S1 && python koura/verify_static.py S1`.
5. **FABDEM trial.** Download the FABDEM tile for N34 E035 if it is reachable without an account, rebuild S1 with `--dem`, and compare checks 7 and 8. Keep the better one and record the numbers. Time-box to 30 minutes.
6. If WP1 succeeded, run the outer ring on S1 with all probe points on main roads plus every fifth point on minor roads.
7. Calibrate the performance budget (feeds WP6): record the static draw-call median and p95 and, from the probe, median and minimum frame rate at the same points.

**Gate (stage 1):** inner ring passes on S1; outer ring passes or is listed for the owner; build time, memory, track size, draw calls and frame rate recorded.

**Evidence:** `out/S1/verify.json`, `out/S1/renders/`, `out/S1/ingame/`, a stage 1 row in `PROGRESS.md`.

**If it fails:** if the zone polygon breaks free-roam placement, S1 is a plain rectangle and can be built with `zona_externa=None`; do that to deliver S1, and fix the zone path before WP7.

---

## WP6. Performance work

**Changes:** `openlaps/openlaps/mesh.py`, `terrain.py`, `extras.py`, `export_ac.py`.

Do this on S1, where a real frame-rate number exists, before building S2.

**Steps**

1. **Terrain draw distance.** Spec D1. Add `"terreno": 1500` to `GROUP_LOD`. Because terrain tiles have no radius compensation, the distance is measured from the tile centre.
2. **Fill under culled terrain.** Spec D1. The horizon drops every cell inside the rectangle, so culled tiles would leave holes. Keep the horizon cells that lie under the detailed ground (they already sit 1 m below final terrain) behind a flag, default on for zone builds. Their draw distance stays 0, meaning always drawn.
3. **Physics beyond the draw distance.** Unknown from code: whether the game still collides with a physics mesh past its draw distance. Test it in the game by teleporting to a point more than 1500 m from the camera start and checking the raycast. If collision is lost, either raise the terrain draw distance on road-adjacent tiles or split physics into an invisible always-on copy. If the game ring is unavailable, choose the safe option: tiles within 60 m of any road get no draw distance.
4. **Shared terrain materials.** Spec D2. Group tiles into 4 x 4 blocks (512 m). One atlas texture, one mask and one material per block, named `terreno_b{bx}_{by}`; keep the `terreno_` prefix because other code keys on it. Meshes stay one per 128 m tile so culling still works. UVs become block-relative; `rep = block_m / 2`. At 0.5 m per pixel a block atlas is 1024 x 1024.
5. **Material library.** Spec D1 last note. `agregar_biblioteca` adds one tiny mesh per material including every terrain material. It exists for live mode. Skip terrain materials there, or skip the library entirely when live mode is not used.
6. **Vegetation.** Check tree count per km² in the build log. If the static estimate shows vegetation dominating draw calls, lower `--vegetacion` for areas more than 150 m from any road rather than globally.
7. Rebuild S1 after each of 1 to 5 and record draw calls, meshes, materials, textures and, if available, frame rate.

**Memory (found on 2026-11-23, see the last section of `FINDINGS.md`).** `roads.armonizar_calzadas` needs one 0.5 m grid over the whole rectangle and cannot run for stage 2 as written. Change `_superficie_comun` to process the rectangle in 1 km blocks with a 10 m overlap, keeping cells aligned to multiples of the cell size as the existing comment requires, and store the result fields per block (`realce_en` and `_muestra` then look up the block for each point). Until that works, `koura/build.py` passes a 1.5 m cell for stage 2 and 0.5 m for stage 1. Every build runs under `ulimit -v 21000000`.

**Gate:** S1 with all changes shows no visual holes in renders or in game, check 6 passes, and draw calls drop. Set the hard limit for check 10 as the S1 draw-call p95 that held the target frame rate, and write it into `verify_static.py`.

**Evidence:** a before and after table in `PROGRESS.md`; renders from 300 m up looking across the map.

**If it fails:** if atlasing causes visible seams between blocks, keep per-tile textures and rely on the draw distance alone.

---

## WP7. Stage 2: the loop

**Changes:** `koura/build.py` (OSM source), `handoff/inputs/zone.json` if the owner corrected the loop.

**Steps**

1. **OSM source.** Use the snapshot saved in WP0. Only if that could not be made to work: download `lebanon-latest.osm.pbf` from Geofabrik once and add a reader that produces the element list `osm.parse` expects. Do not send S2-sized queries to public Overpass servers; openlaps' own query gives each mirror only about 20 s.
2. **Prove the corridor on a short stretch first.** Upstream marks its corridor path as untested in game. Add a temporary stage `S1b` to `zone.json`: S1 plus 2 km of route buffer south through Aaba. Build, run both rings. Look specifically at:
   - side roads cut at the zone edge: they must end at the invisible wall, not in mid-air;
   - the boundary wall following the zone outline with no gaps;
   - terrain meeting the horizon under-layer at the zone edge with no visible step.
3. **Build S2.** `python koura/build.py S2`. Expect roughly 2.5 times S1 in detailed area. Watch memory: the whole track file is assembled in memory.
4. Inner ring. Check 7 on S2 is the important one: 25.6 km of loop, 3 km of shortcut, 5.4 km of Tourza road, 1.4 km of karting access road and 3.4 km of Dabbousi Farms road with zero holes. Check 14 proves the loop is still a loop after the zone cut.
5. Outer ring: every main-road point on the loop, plus screenshots every 500 m. If the game ring is unavailable, produce a `comparar_ruta.py` contact sheet of the whole loop instead.
6. Remove `S1b`.

**Gate (stage 2):** both rings pass around the whole loop; draw calls within the limit from WP6 at every probe point; track file under 2 GB.

**Evidence:** `out/S2/verify.json`, loop contact sheet, `out/S2/ingame/`.

**If it fails**
- Over the draw-call limit in the villages only: reduce village disc radius from 450 m to 300 m in `zone.json`.
- Over memory or file size: split the output into several track files on the same origin, listed in `models.ini`. The split is of the finished scene by 2 km grid cell, not of the build, so heights still agree.
- The corridor path is broken in ways that cannot be fixed in a day: build S2 as the plain 6.7 x 9.2 km rectangle with `--vegetacion 0.5`, and accept the larger size.

---

## WP8. OSM ids and override files (lane D)

**Added 2026-11-24.** Besides the files in the steps below, create three more, because `DETAIL-STANDARD.md` section 5 stores its work in them. Each is read by `koura/build.py`, every entry is positioned by latitude and longitude, and no entry holds an absolute height.

- `koura/overrides/walls.json`: lines with `height_m` above ground, `material`, `collider` (default true), optional `gaps` for gates and driveways, `source`, `state`.
- `koura/overrides/landmarks.json`: one-off objects (statues, monuments, shrines, fountains, entrance signs): position, heading, size, model file or shape description, `collider`, `source`, `state`.
- `koura/overrides/junctions.json`: per junction, the real outline: roundabout centre and diameters, islands as polygons with their content, splitter islands, kerb height (at most 0.08 m, sloped). This changes the road in plan view only; in `roads.py` it may add geometry on top of the built surface but must not change the reserved height functions (`BASE.md` section 4).

Add one of each to this package's gate build: one wall with a gate gap, one landmark with a collider, one roundabout with an island (use the Btouratij junction with the statue).

**Changes:** `openlaps/openlaps/sources/osm.py`, `roads.py`, `buildings.py`, `pipeline.py`; new `koura/overrides/*.json`.

**Steps**

1. **Road overrides.** Spec F3. In `pipeline.py` right after `osm = f_osm.result()`, and in `red_de_calles`, merge `koura/overrides/roads.json` into way tags:
   ```json
   {"123456789": {"width": 5.5, "lanes": 1, "surface": "asphalt", "oneway": "no", "maxspeed": 40},
    "add": [{"id": "koura_1", "tags": {"highway": "residential", "width": "4"}, "nodes": [[34.36, 35.84], [34.3603, 35.8402]]}],
    "remove": ["987654321"], "move": {"123456789": [[34.36, 35.84], [34.3604, 35.8403]]}}
   ```
   `add` creates a way that OSM lacks (join its end nodes to existing nodes within 3 m), `remove` drops a way, `move` replaces a way's geometry. WP11 and WP12 depend on these.
   Values are written as OSM tag strings, so the existing width, lane and surface logic applies. Widths outside 2.5 to 40 m are ignored by `_attrs`; validate the file and report rejected entries.
2. **Way ids on edges.** Spec F3. Change the `raw` tuples in `_build_graph` to carry `w["id"]`, update every unpacking the spec lists, add `way_ids: list` to `Edge`, and concatenate in `_merge_deg2`. Needed by WP9 for per-road elevation.
3. **Building ids.** Spec H2. Keep `el["id"]` and type in `osm.parse` for areas; propagate as `osm_id` in `buildings.collect`.
4. **Building overrides.** At the end of `collect`, apply `koura/overrides/buildings.json`:
   ```json
   {"by_osm_id": {"w987654": {"levels": 3, "roof": "flat", "colour": "#e8e0d0"}},
    "by_point": [{"lat": 34.3621, "lon": 35.8388, "levels": 2, "roof": "hipped", "roof_colour": "#a8543a"}],
    "add": [], "remove": []}
   ```
   Write values into `b["tags"]` (`building:levels`, `roof:shape`, `building:colour`, `roof:colour`), because OSM tags outrank the `height` field (Spec H1). Match `by_point` entries to the footprint containing the point, else the nearest within 3 m.
5. **Facade slot.** Spec H3. Allow an override to name a texture per wall: `"facades": [{"edge": 0, "image": "facades/church_west.jpg", "fit": "stretch"}]`. Build that ring segment with its own `wall_strip` call and material named `fachada_foto_<hash>` (the `fachada_` prefix keeps CSP rain and night settings working). `stretch` maps the photo once across the wall; default tiling is 4 m by 3 m.
6. **Adding and removing buildings.** The source data is older than the place (imagery 2024-01, footprints older), so new buildings are missing and demolished ones remain. Give `add` and `remove` a real schema:
   ```json
   "add": [{"name": "Knots", "ring": [[34.36, 35.84], [34.36, 35.8401], [34.3601, 35.8401], [34.3601, 35.84]], "levels": 1, "roof": "flat", "colour": "#f0f0f0",
            "sign": {"text": "Knots", "edge": 0, "image": "facades/knots_sign.jpg"}}],
   "remove": [{"osm_id": "w123"}, {"lat": 34.36, "lon": 35.84}]
   ```
   An added ring becomes a footprint exactly like a parsed one. A `sign` puts a shopfront texture on the named wall through the facade slot of step 5; with no image, render the text onto a plain fascia band. An added building also clears trees and scatter inside its ring plus 2 m.
7. An overrides report in every build log: how many entries applied, how many matched nothing.

**Gate:** a test build with one road width override, one added road, one removed road, one moved road, one building levels override, one facade image, one added building with a sign and one removed building shows all eight in `render.py`; unmatched entries are reported; `pytest` passes.

**Evidence:** three before and after renders.

---

## WP9. Footage and recordings

See `DASHCAM.md` for sources and how each is used. There are two sources: existing online videos of Btouratij (driving point-of-view and drone footage, by Saed Elhassan), and new recordings by the owner with GPS. Start with the online videos, because they exist now.

**Changes:** `koura/footage/*` (new tools), `koura/overrides/*`, `recordings/`.

**Steps**

1. **Collect.** Download the videos listed in `DASHCAM.md` to `recordings/online/<video-id>/` for private reference (`yt-dlp`, installed with `uv pip`). Keep the source address and title in a `source.txt` beside each. Do not redistribute them.
2. **Frames.** `ffmpeg` to one frame per second for driving video, one per two seconds for drone video. Drop near-duplicate frames.
3. **Locate driving video without GPS.** Online video has no position data. For each video, an agent watches a contact sheet, identifies the route from landmarks against the map, and writes `route.json`: a list of (time, lat, lon) anchor points at recognisable places such as junctions, the church, the square. Interpolate along the OSM road between anchors. Accuracy of about 10 m is enough for the review step.
4. **Review into overrides.** For each road, from frames: carriageway width (estimate against car width and lane lines), lane count, surface, markings, speed bumps, roadside walls, pavement presence. For each building passed: floors, roof type, wall colour. Write to the override files from WP8. This is agent review work; run one sub-agent per video with a fixed checklist and have a second agent spot-check 10%.
5. **Drone footage: building heights and facades.** From frames where a building is seen obliquely, count floors and read roof type for every building in view; drone footage covers many buildings per frame, so this is the fastest way to fill `buildings.json` for Btouratij. Save square-on wall views as facade candidates.
6. **Drone footage: 3D reconstruction, experimental, time-boxed to half a day.** If a video orbits or sweeps the village with steady overlap, run structure-from-motion on its frames (COLMAP, or OpenDroneMap in a container). The result is a point cloud with no real-world scale or position. Register it to the map with at least six ground control points picked on building corners visible in both the cloud and the aerial imagery. If the registered model's residual error is under 2 m, use it for two things: a height for every building it covers, and a surface model of the village finer than 30 m, fed through `--dem` with `--dem-es-superficie`. If the video is cinematic (fast pans, cuts, zooms), reconstruction will fail; record that and move on.
7. **Facades.** For each landmark and each building on the owner's street: choose the best square-on frame, pick the four wall corners, straighten with the homography code from road-to-assetto (`photo_projection.py`: at least 4 points, refuse fits over 3 px error), save to `koura/overrides/facades/`, and reference it from `buildings.json`.
8. **Owner GPS tracks, when they arrive.** Spec G.
   - Parse GPX; convert altitude to the elevation model's datum (GPX altitude is often ellipsoidal; the geoid offset near Koura is roughly 20 to 25 m, to be checked against the model at three open, flat points rather than assumed).
   - Smooth altitude along distance; match to OSM ways.
   - Add `gpx_z` to `RoadNetwork`; right after the `self.dem_z(...)` call in `_elevation`, replace heights for chain points within 6 m of a track, masked by way id; use a smaller smoothing sigma on those chains; blend to model height over 50 m at each end.
9. Rebuild S1, then S2, with overrides. Use `tools/comparar_fotos.py` where frames have a known pose.

9. **Find places newer than the source data.** The owner named Knots as an example and wants all such places on the map, not only the ones they list. Do a discovery sweep before placing anything, for S1 first, then along the loop, shortcut and Tourza road:
   - Search the web and image search for each village name in English, French and Arabic spellings (Btouratij بتوراتيج, Nakhle نخلة, Aaba عابا, Bishmizzine بشمزين, Kfar Hazir كفرحزير, Amioun أميون, Kousba كوسبا, Bsarma بصرما, Ras Masqa راس مسقا, Koura الكورة) with: new, opening, now open, افتتاح, shop, cafe, restaurant, gym, pharmacy, supermarket, petrol station, car dealer, showroom.
   - Check map listings (Google Maps, OpenStreetMap notes and recent edits) for businesses whose first review or photo is later than 2024-01, and their street-level photos.
   - Check business pages on Facebook, Instagram and TikTok for location, shopfront photos and opening date. A web search did not find Knots on 2026-11-23, so small places will mostly be on these.
   - Scan the newest dashcam and drone videos frame by frame along each road for signs and buildings the aerial imagery does not show.
   Append every find to `inputs/recent_places.json` with its source link, date and how sure the position is. Save the shopfront images used under `koura/overrides/facades/` (personal use only, never published). If a tool cannot open a site, record the place as "seen in search, not located" instead of dropping it.
10. **Place them.** For each entry in `inputs/recent_places.json`:
   - find its position: the owner's pin if given, else locate it in the newest footage and place it against neighbouring footprints;
   - if a footprint already exists there, add a `by_point` override with the shopfront as a facade and the sign text;
   - if the building is new, add it under `add` with a ring traced from the footage (drone frames first), floors counted, and its sign;
   - if the ground under it shows a field or trees in the imagery, the `add` entry clears the vegetation; note it so the ground texture can be patched in work package 10.
   - a place with no usable position is listed for the owner, never guessed onto the map.
   Compare footage date against imagery date for every video used, and prefer the newest source when they disagree. Write what was added and what could not be placed into `PROGRESS.md` under "Owner must check".

**Gate:** for the main street of Btouratij, a side-by-side sheet of ten video frames and the matching `render.py` or in-game views, sent to the owner.

**Evidence:** `out/S1/compare/`, counts of overrides by source.

**If it fails:** if route location from landmarks is too slow or unreliable, ask the owner to name the route of each video; that is a one-line answer per video.

---

## WP10. Stage 3 and detail passes

Only after stage 2 is accepted. In priority order. Item 1 is replaced by WP14 (the owner asked for the empty middle of the loop to be filled, at once, not as an optional extra); items 2, 3 and 6 are now part of WP12 and WP13 because `DETAIL-STANDARD.md` requires walls and landmarks there. What stays here: items 4, 5 and 7.

1. **S3 as a baked track**, if the WP6 limit suggests it fits (S3 has 3.5 times the detailed area of S2). Otherwise offer the live-mode extension beyond the S2 ground (`--excluir` with the S2 rectangle, `--centro` equal to the pinned origin) and explain its limits.
2. Retaining walls, terraces and building plinths on slopes: port the approach from road-to-assetto's `building_bases.py` and `hillside*.py`. Koura is steep; buildings currently sit on carved flats.
3. Stone and concrete walls along roads, from the WP9 review.
4. Speed bumps at reviewed positions (openlaps has a `tope` feature).
5. Night: street lamps are already placed with lights; check the count against the patch's light limits at S2.
6. Hand-modelled landmarks: model in Blender, export glTF, convert to a second track file with the fork's writer, list it in `models.ini`. This is the only use of Blender.
7. Traffic: confirm CSP Traffic mode works with `traffic.json` at S2 and set a recommended car count in the description.

---

## WP11. Karting Mania, Kousba: the kart track in full detail

**Owner, 2026-11-24, after driving build 9:** "have [the agent] focus on the details of the carting track as well, because it needs to be super accurate. Right now, not so much." An earlier verdict on the first version was "an absolute joke". Treat every item in step 11 as required, not as polish.

**What the base has, and why it is not accurate enough.** `koura/kart_pts.py` holds a hand trace of 77 points, good to about 1.5 m, with one width (8 m) for the whole lap; `roads._pista_kart` lays it on a single plane with the slope capped at 2.5 % (the height model says 6 %; the real slope is unknown). There are no kerbs, tyre walls, fences, painted lines, start line, pit lane, buildings or timing. Step 2 below (trace to 0.5 m with the real width at every point) replaces the hand trace; do not keep the 77 points as the final shape. The single plane may stay only if the onboard videos show the site is that flat; `_pista_kart`'s plan shape and surface are yours to change, its height is reserved only until the reserve is lifted, so record the slopes you see in the videos under `For the road-height work` in `PROGRESS.md`.

**Accuracy targets, all measured and reported:** asphalt edge within 0.5 m of the aerial image all the way round; width at every 2 m from the image, not one value; lap length measured and compared with onboard lap videos (count seconds between landmarks against the trace); every corner's inside and outside kerb present where the videos show one; start line, grid and pit lane where the videos show them; direction of travel from the videos.

Read `DETAIL-STANDARD.md` first. It defines what counts as done.

The owner asked for this track "with extreme details". It is not in OpenStreetMap at all, so nothing appears unless this package is done. Do it after WP8 (it uses the override files) and before the stage 2 build in WP7 is called finished.

**Facts measured on 2026-11-23**

- Track centre: 34.3261, 35.8525. Site box in `zone.json` (S2 parts): 34.3247 to 34.3287 N, 35.8511 to 35.8553 E.
- Aerial image saved at `evidence/karting_mania_aerial.png`: 1536 x 1792 px, north edge 34.328694, south edge 34.324725, west edge 35.851135, east edge 35.855255. That is 0.247 m per pixel east-west and 0.246 m north-south. Pixel (px, py) maps to lon = 35.851135 + px x 0.0000026823, lat = 34.328694 - py x 0.0000022148 (linear is accurate to a few centimetres over this size).
- What the image shows: one closed asphalt ribbon about 7 to 9 m wide with a long outer run on the west side, a large hairpin complex in the north around a grass infield, and a small hairpin complex in the south; a red-roofed building and a larger white building east of the track; a gravel car park east of those; the entrance road coming from the east, from the straight Dabbousi Farms road.
- A web listing gives the lap length as 1,091 m. The ribbon in the image looks much shorter than that (roughly 500 to 700 m). Measure your trace and record the number; do not stretch the trace to match the listing.
- Access: route `kart_access` in `zone.json` (1.4 km from Tripoli Street) and route `dabbousi_road` (3.4 km, from the track north along the straight road, then west to the loop at Aaba). Both are ordinary OSM roads and are built by WP7.

**Steps**

1. **Collect references first.** Search YouTube, Instagram, Facebook and TikTok for `Karting Mania Kousba`, `Karting Mania North`, `كارتينغ مانيا كوسبا`. Download onboard laps and any drone clip with `yt-dlp` into `recordings/online/karting_mania/`. Extract one frame per second. Note from them: direction of travel, where the start line is, kerb colours and where kerbs exist, barrier type per section (tyres, plastic blocks, concrete, fence), where the pit entry and exit are, what the buildings look like, floodlight pole positions, signs and banners. Write this into `koura/overrides/karting_mania_notes.md` with frame file names as evidence.
2. **Trace the track from the aerial image.** Write `koura/tools/trace_kart.py`:
   - Load the image at full size (1536 x 1792; do not use a thumbnail). The track surface is a warm light grey, about RGB (207, 183, 160): sampled values on the ribbon are (205,180,158), (209,187,164), (225,203,179). Make the mask from pixels within a colour distance of about 30 of (207, 183, 160) and tune by eye; shadows across the ribbon are darker and must be filled in by hand. Keep only the connected region that contains pixel (430, 1050), which lies on the west run. The car park and entrance road east of the buildings have a similar colour: draw a polygon around them on an overlay, check the polygon does not touch the ribbon, and remove what is inside it from the mask (keep it as an `aprons` polygon).
   - Fill small holes, then compute the skeleton (`skimage.morphology.skeletonize`) and the distance transform (`scipy.ndimage.distance_transform_edt`). The skeleton is the centreline; twice the distance value at each skeleton pixel is the local width.
   - Order the skeleton pixels into one closed loop, drop spurs shorter than 5 m, resample every 2 m, smooth with a 5-point moving average, convert to lat/lon.
   - Save `koura/overrides/karting_mania.json`: `{"centreline": [[lat, lon, width_m], ...], "closed": true, "direction": "clockwise or anticlockwise from step 1", "start_line": [lat, lon], "pit_lane": [[lat, lon, width_m], ...], "aprons": [polygons of extra asphalt such as the paddock], "kerbs": [{"from_index": i, "to_index": j, "side": "left|right", "colour": "red_white"}], "barriers": [{"type": "tyre|block|fence|wall", "line": [[lat, lon], ...], "height_m": 0.8}], "buildings": [{"ring": [...], "levels": n, "roof": "...", "colour": "..."}], "poles": [[lat, lon]], "signs": [...]}`.
   - Save an overlay image (trace drawn on the aerial) to `out/kart/trace_overlay.png` and look at it. The centreline must stay inside the asphalt everywhere and the drawn edges must sit within 0.5 m of the visible edges. If the automatic trace fails on the tight parallel sections, place the points by hand: read pixel coordinates off the image and type them in. That is acceptable; a wrong automatic trace is not.
3. **Feed the track into the build.** Checked on 2026-11-23: the fork has no handling of `highway=raceway` at all (the word does not occur in the code, and `DRIVABLE` in `openlaps/config.py` does not list it), so a raceway way would be silently dropped. Therefore add the trace through the road overrides `add` list from WP8 as `highway=service` plus the tag `koura:kart=yes`, id `koura_kart_1`, with a `width_profile` (one width per node). In `roads.py`, make a way with `koura:kart=yes` behave as: width taken per node from `width_profile`; no centre line, no edge lines; no street lamps; no pavement; left out of `traffic.json`; excluded from the junction solver except at its two ends.
3b. **Connect it to the road network.** The track is otherwise an island: route `kart_access` ends on the straight road east of the site, and the entrance driveway and the car park are not in OSM. Trace the entrance driveway from the aerial image (it runs west from the straight road at about 34.3262, 35.8546 to the car park) and add it as a second `add` way, `koura_kart_entrance`, `highway=service`, width 5 m, whose east end node is joined to OSM way 442038076. Add the car park and paddock as `aprons`, and a short link from the car park onto the track at the pit entrance seen in the videos.
4. **Keep parallel sections apart.** The ribbon runs beside itself 8 to 12 m apart in several places. Check that terrain carving, verge generation and the boundary wall do not merge or cut the neighbouring section. Run `escalones.py` and `defectos.py` on a build of the site box alone and fix every hit inside it; the "not worse than baseline" rule does not apply here, the target is zero.
5. **Height.** The 30 m elevation data cannot describe a 200 m site. Fit one tilted plane through the elevation samples inside the site box and use it as the base. Then adjust from the onboard videos: where a video shows a clear climb or drop, add it as a height offset per centreline index in `karting_mania.json` (`"z_offset_m"`). Cross-fall is zero unless a video shows banking. Record in `PROGRESS.md` that track height is estimated, not surveyed.
6. **Surfaces.** Track asphalt gets its own physics mesh name and `surfaces.ini` key (`KART`, grip 1.0, valid track). Kerbs get a kerb surface with vibration. Infield and verges are grass. The paddock and car park are separate asphalt and gravel keys. Follow the naming rules in `AC-FORMAT.md`.
7. **Detail objects**, all from step 1 evidence, each with a collider where a kart or car could hit it: red and white kerbs as slightly raised strips (at most 4 cm, chamfered); tyre barriers as rows of stacked tyres; plastic blocks; catch fences; the start line, grid slots and any painted markings as decals 1 cm above the surface; floodlight poles with lights for night; the two buildings with photo facades through the WP8 facade slot; the entrance gate and the `Karting Mania` sign; the car park with painted bays if visible; the grass infield with the trees seen in the image at their real positions.
8. **Ground texture.** Terrain colour inside the site box comes from zoom 19 imagery at 0.25 m per pixel, using the per-tile texture resolution added in WP12 step 1 (do that step first if WP12 has not run). Terrain mesh resolution stays the stage value: the fork takes one `res` for the whole run (`T.Terrain(proj, dem, lc, dem_is_dtm, res, ...)`), and the track surface is its own road mesh, so it does not depend on terrain resolution.
9. **Start position.** Add two extra pit slots in the kart paddock so the owner can start a session there. Keep `pitboxes` in `ui_track.json` equal to the marker count (VERIFY check 4).
10. **A real, timed track layout. Required.** The owner's words: "Karting Mania should be copy paste exact as it is in real life. Everything like a real track." Besides being part of the free-roam map, build it as a second track folder `koura_karting_mania` that contains only the kart site (site box plus 150 m of surroundings, same origin, same meshes) and works like any circuit in the game:
   - `AC_START_n` grid slots on the real grid markings, `AC_PIT_n` in the real pit lane, `AC_TIME_0_L/R` at the real start line and `AC_TIME_1_L/R` halfway round, `AC_HOTLAP_START_0` before the last corner. Follow `AC-FORMAT.md` for names and orientation.
   - `data/surfaces.ini` with the `KART` surface valid and everything else off-track, so cut laps are invalidated.
   - `ai/fast_lane.ai` and `ai/pit_lane.ai`: generate from the traced centreline with the fork's writer if it has one (search `fast_lane` in the three reference repos; mapcreator documents the format); otherwise record it once in game with the built-in AI line recorder and note that the owner must do that step.
   - `map.png` outline from the trace, `ui_track.json` with the measured length and width, track cameras (`data/cameras.ini`) at three or more points, pit count equal to the marker count.
   - The direction of travel, pit entry and exit, and start line position come from the videos in step 1, not from guesses. If the videos disagree, use the newest.
11. **Exactness standard for this site.** Asphalt edge within 0.5 m of the aerial image everywhere (not 1 m); every kerb, barrier run, tyre stack, fence, pole, marshal post, sign, banner, painted line, building, canopy, table area and parking bay that appears in the aerial image or any video is present at its real position; track width per point from the trace; colours sampled from the videos. Keep a checklist `koura/overrides/karting_mania_items.csv` (item, position, source frame, status) and finish with no `todo` rows. Anything seen in video that cannot be positioned is listed for the owner, never dropped.

**Gate:** trace overlay within 0.5 m of the visible edges all the way round; the `koura_karting_mania` layout loads, a lap is timed and a cut lap is invalidated (probe or owner); the items checklist has no `todo` rows; measured lap length recorded; zero step, seam or hole hits inside the site box; a top-down `render.py` image next to the aerial image shows the same shape, buildings and car park; a `comparar_ruta.py` sheet of one full lap; the road network contains a drivable route from the loop to the kart paddock (route it with `roads.route` from the Tripoli Street turn-off in `zone.json` `key_points` to the track's first node); in-game probe points every 20 m of the lap all land on the `KART` surface (or "owner must check" if WP1 failed).

**Evidence:** `out/kart/trace_overlay.png`, the lap sheet, the top-down pair, `karting_mania_notes.md`.

**If it fails:** if the build cannot keep the parallel sections apart, build the kart track as its own small mesh set with the fork's writer (flat ribbon, kerbs, barriers) and place it as a second file in `models.ini` on a flattened pad, instead of through the road network.

---

## WP12. Btouratij and Nakhle fine-detail pass

Read `DETAIL-STANDARD.md` first. It defines what counts as done.

The owner's words: "It is critical to me that in the detailed zone, the green one, especially in Btouratij, the houses and roads and small details are extremely detailed." The generator alone does not meet that: it gives correct road positions and building footprints with generic looks. This package is the manual, item-by-item pass that closes the gap. It is long and repetitive by design. Do it in the order below and never skip the checklist.

**Areas**

- Core A, Btouratij village: 34.3560 to 34.3665 N, 35.8320 to 35.8470 E (`fine_boxes.btouratij_core` in `zone.json`). Highest standard.
- Core B, Nakhle village (`fine_boxes.nakhle_core`: 34.3610 to 34.3715 N, 35.8230 to 35.8345 E) and the two confirmed loops (`nakhle_big_loop`, `nakhle_small_loop`), 60 m each side of the road.
- The rest of the green box (stage 1): the standard below marked "all of S1".

**Sources, in this order of trust:** the owner's own recordings; the Saed Alhassan street tour and drone videos listed in `DASHCAM.md`; other online videos and photos; Esri imagery at zoom 19 (about 0.25 m, the same service as WP4 with `z=19`); OpenStreetMap; footprints. When two disagree, the newer one wins.

**Steps**

1. **Sharper ground in the fine boxes.** `zone.json` has a `fine_boxes` list (Btouratij core, Nakhle core, Karting Mania). Checked on 2026-11-23: the fork uses one terrain mesh resolution per run (`res`) and one texture resolution per run (`mpp`, passed to `terr.build_mesh(..., mpp=mpp, ...)`, which calls `painter.paint_tile(x0, y0, x1, y1, mpp, self)` once per tile). Do not attempt mixed mesh resolution. Do this instead:
   - Keep S1 terrain at 2 m.
   - In `Terrain.build_mesh`, accept an optional list of local-metre rectangles `fino` and a value `mpp_fino`; for a tile that intersects any rectangle call `paint_tile` with `mpp_fino` (0.25), otherwise with `mpp` (0.5). `koura/build.py` converts `fine_boxes` to local metres and passes them.
   - Make the WP4 reader fetch zoom 19 for those tiles only. First check zoom 19 is real: download one zoom 19 tile and its zoom 18 parent, upscale the parent 2x and compare; if they are near-identical, zoom 19 is only an upscale and this step is skipped (record that).
   - Measure texture memory and build time before and after. If the track folder for S1 grows by more than 1 GB, limit `fine_boxes` to the Btouratij core.
2. **Make the checklists.** Write `koura/tools/make_checklists.py` that reads the OSM snapshot and the footprints and writes two files:
   - `koura/overrides/s1_roads.csv`: one row per road way inside S1. Columns: `way_id, core, length_m, osm_class, in_imagery (yes/no), width_m_measured, surface, markings, edge_left, edge_right, lamps, speed_bumps, notes, source, status`.
   - `koura/overrides/s1_buildings.csv`: one row per footprint inside S1. Columns: `id, core, lat, lon, area_m2, exists_now, shape_ok, levels, open_ground_floor, roof (flat|hipped|gabled), roof_colour, wall_colour, roof_items (tank, solar, dish), boundary_wall, gate, use (house|shop|mosque|church|school|other), sign_text, facade_image, source, status`.
   `status` is `todo`, `done` or `no_evidence`. Nothing is ever left blank.
3. **Roads, all of S1.** For every row: measure the width on zoom 19 imagery at three places and enter the median; set surface (asphalt, concrete, dirt); set markings (most village streets have none, and the generator must not paint any when the row says none); set each edge to one of `wall`, `kerb`, `open`, `drop`. Write the results into `roads.json`.
3b. **Cut loops (owner feedback from the trial drive: "a lot of loops where just a small part of the loop is cut off").** List every place where a road leaves the S1 zone and comes back in within 400 m of road length, and every block whose ring of streets is broken by a missing piece. For the first kind, bulge the S1 zone outwards to include the missing piece (add a small box to the S1 `parts` in `zone.json`; never move the origin). For the second, the missing piece is a road OSM lacks or has mis-tagged (`footway`, `path`, `track`, private `service`): check it on imagery and add or retag it in `roads.json`. Save the list to `out/S1/cut_loops.md`.
4. **Missing and wrong roads, all of S1.** Lay the OSM roads over zoom 19 imagery in 500 m squares, save each overlay to `out/S1/road_audit/`, and look at every square. Add every drivable street, lane and driveway longer than 15 m that OSM lacks to `roads.json` under `add`; move OSM lines that are more than 2 m off the visible road; remove ways that do not exist. The owner asked for "all the small roads and little roads".
5. **Buildings, cores A and B.** For every row: confirm it still exists and its outline matches the imagery within 1.5 m (fix the ring if not; add missing buildings; remove demolished ones); count floors from footage or from shadow length; set roof type and colours sampled from imagery and footage; note pilotis, rooftop tanks and solar panels; record the boundary wall and gate. Write into `buildings.json`.
6. **Facades, core A.** Every building that faces a road covered by any video gets a photo facade on the road-facing wall, using the WP8 facade slot and the road-to-assetto straightening code (`DASHCAM.md` explains frame choice). Buildings with no footage get the Lebanon profile's procedural facade and `no_evidence` in the checklist, and are listed for the owner to film.
7. **Landmarks and monuments, cores A and B.** Statues, busts, memorials, shrines, fountains, village entrance arches and name signs (the owner named statues specifically; see the list in `DETAIL-STANDARD.md`): each is its own small model with the recognisable shape, sized from a person or car in the photo. Mosques (two are marked in OSM between Nakhle and Btouratij), any church, the school, shops with signs, petrol stations: model each as its own override with correct height, minaret or tower as simple geometry, and its sign. Add each to `inputs/recent_places.json` if it is newer than the imagery.
8. **Roadside detail, cores A and B.** From footage and imagery: boundary walls and fences along every road (height and material: stone, block, plaster, railings); gates; electricity and telephone poles with wires between them; street lamps at their seen positions instead of generated spacing; speed bumps; road signs and mirrors at blind corners; shop signs; rubbish containers; stairways and retaining walls. Each type is an entry list in `koura/overrides/s1_details.json` with lat, lon, heading and size. Solid ones get colliders.
9. **Trees, cores A and B.** Detect individual tree crowns on zoom 19 imagery (dark green blobs 2 to 10 m wide) and plant one tree per crown at that position and size, olives in groves, other species near houses. Remove generated trees that stand where the imagery shows none.
10. **Review loop.** After every 30 checklist rows, rebuild S1 and produce `comparar_ruta.py` sheets for the roads touched, next to video frames of the same spots. Fix what differs most. Repeat until every row in cores A and B is `done` or `no_evidence`.

**Gate:** both checklist files have no `todo` rows in cores A and B; the road audit overlays show no missing street; a side-by-side sheet (video frame, render) for every 50 m of the Btouratij main street and of both Nakhle loops; all VERIFY checks pass on the rebuilt S1; `PROGRESS.md` lists the `no_evidence` buildings and roads as a filming list for the owner.

**Evidence:** the two CSV files, `out/S1/road_audit/`, the side-by-side sheets.

**Honest limit, to repeat to the owner:** streets that appear in no video get correct geometry and plausible, not real, house fronts. The filming list from the gate is how that gets fixed.

---

## WP13. Detail pass for everything outside the green box

Read `DETAIL-STANDARD.md` first. It defines what counts as done.

The owner's words: "I want the extreme detail area to be detailed, but the areas outside to also be detailed. Not as extreme, but still detailed." This is the same kind of work as WP12 at a lighter standard, applied to all stage 2 ground outside S1: the loop, the shortcut, the Tourza road, the karting access road, the Dabbousi Farms road and the village centres on them. Do it after WP7 and WP11.

**The three standards, side by side**

| Item | Extreme (S1 cores, WP12) | Detailed (rest of S1, and all of S2: this package) | Background (S3 only) |
|---|---|---|---|
| Roads present | every street, lane and driveway over 15 m | every public road and street in the S2 ground; driveways where they are visible from a road | whatever OSM has |
| Road width, surface, markings | measured per road at 3 points | measured per road for every road in the S2 ground | class default |
| Road edges (wall, kerb, open, drop) | every road | both sides of every road in the S2 ground | none |
| Buildings exist and outline right | every one checked | every one in the S2 ground checked; missing and demolished ones fixed | footprint data as is |
| Floors, roof type, colours | every one, from footage | every one in the S2 ground, from imagery and footage | profile defaults |
| Photo facades | every road-facing wall that appears in video | every wall facing a named route that appears in video, plus all landmarks and signed shops | none |
| Landmarks (mosques, churches, schools, petrol stations, big shops) | all, with signs | all in the S2 ground, with signs | none |
| New places (`recent_places.json`) | all | all | none |
| Walls, fences, gates | all | along every road in the S2 ground | none |
| Poles, wires, lamps, signs, speed bumps | at seen positions | lamps, speed bumps, road signs and poles at seen positions wherever video exists; generated only where there is no video | generated |
| Trees | one per crown seen in imagery | every grove and roadside tree from imagery in the S2 ground | generated |
| Ground texture | 0.25 m | 0.5 m | 0.5 m or satellite |

**Steps**

1. Extend `make_checklists.py` from WP12 to write `koura/overrides/s2_roads.csv` and `koura/overrides/s2_buildings.csv` with the same columns, plus a column `route` naming the nearest route in `zone.json` and `dist_to_route_m`. Every row inside the S2 ground is reviewed; nothing is left at a default. The owner's words: "no, not just along the route. Try to get it similar, like detailed, very similar, like I'm driving on it." The test for this package is what a driver sees: at every point of every route, the view forward and to both sides must match the video of that spot in road shape, building positions, heights, roof types, colours, walls, trees and signs.
2. Work route by route, in this order: `loop` (start at Btouratij, go in the owner's order), `shortcut`, `dabbousi_road`, `kart_access`, `tourza_spur`. For each route, in 500 m sections:
   - overlay OSM roads on zoom 18 imagery, fix position errors over 3 m, add missing side-road mouths so junctions look right;
   - fill the road rows (width, surface, markings, edges);
   - fill the building rows from imagery, and from video where a video covers the section;
   - add landmarks, signed shops, petrol stations and anything in `recent_places.json`;
   - add walls, speed bumps, lamps and signs seen in video;
   - rebuild that section's stage and make one `comparar_ruta.py` sheet for it, placed next to video frames of the same positions; list the five biggest differences per section and fix them before moving on.
   Buildings and terrain further than the S2 ground but visible from the road (hillsides, skyline villages, large buildings) are checked on each sheet too: if a visible hillside village is missing or wrong, widen that part of the zone in `zone.json` by adding a disc, and record it.
3. Village centres (the 450 m discs at Aaba, Bishmizzine, Kfar Hazir, Amioun, Kousba, Bsarma): after the routes, review every road and building in each disc to the "Detailed" column. Amioun and Kousba are the largest; do them last.
4. Run the new-places sweep from WP9 step 9 for each village if it was not already done for it.
5. Record per route in `PROGRESS.md`: sections done, which had video, which were imagery only.

**Gate:** no `todo` rows in the two S2 checklist files; one sheet per 500 m section of every route; all VERIFY checks pass on S2; a list for the owner of sections that had no video.

**Evidence:** the CSV files and the section sheets under `out/S2/sections/`.

**If usage runs short:** stop at a route boundary, not mid-route, and record the next section to do.

---

## WP14. Ground inside the loop: no dead ground

Read `DETAIL-STANDARD.md` section "3. No dead ground" first.

The owner's words: "the dead parts of the map in the center where there is no terrain should be filled with grass and olive trees."

**The problem.** Stage 2 ground is the stage 1 box, a strip 250 m either side of each named route, a 450 m disc on six village centres and the kart site: 27.5 km² of a 144.7 km² rectangle. From the road the driver sees the edge of that strip, and beyond it nothing. The largest hole is the middle of the loop.

**What to build.** Ground everywhere the driver can see from any named route, at background quality:

| Item | Background quality |
|---|---|
| Terrain | 6 to 8 m mesh, no carving except where a road crosses it |
| Ground texture | Aerial image at about 1 m per pixel |
| Trees | Olive groves, pines and oaks where the image and the canopy model show them, as cheap billboards or low models, at the real density. Rows where the groves are in rows |
| Buildings | Footprint boxes with flat roofs and the `lb` colours. No detail |
| Roads | Every road that joins two points of the stage 2 network is built as a normal drivable road. Dead-end tracks appear in the ground texture only |
| Collision | Ground only. No tree or post colliders out here |

**Steps**

1. Needs WP6 done (draw distance on terrain, draw-call limit known). If WP6 is not done, stop and do WP6.
2. Measure before designing. Write to `PROGRESS.md`: the area inside the loop polygon that is not stage 2 ground; the area visible from the routes (run a line-of-sight calculation on the 30 m height model from a point every 100 m along each route, eye height 1.2 m, range 3 km); the km of road and number of buildings in each.
3. Choose the area to fill: the visible area, grown by 100 m, plus the whole inside of the loop. If that is more than the WP6 limit allows, keep the inside of the loop and cut the outside by distance from the route.
4. Read how the fork builds terrain at different resolutions (`terrain.py`, `pipeline.py`, search for `terrain_res` and `zona`). Choose the first of these that works and record why:
   - a. a second quality class inside one build: a `background` part type in `zone.json` that `koura/build.py` turns into a second zone polygon, with coarse terrain and no detail passes there;
   - b. a second track file: build the background ground as its own coarse build of the same rectangle with the same pinned origin, with the stage 2 zone cut out, and list both files in `models.ini`;
   - c. the generator's live-mode ground for the area outside stage 2, as WP10 item 1 described, only if a and b both fail.
5. The stage 2 edge wall: stage 2 has a collision wall round its outline so the car cannot drive off the ground. Where background ground now continues beyond the outline, the visible wall (if any) must go and the collision wall must move to the outer edge of the background ground, or stay where it is if the background ground has no collision. Decide, write it down, and check that a car cannot fall off the world anywhere.
6. The seam: where background ground meets stage 2 ground the two must meet without a gap or a step higher than 10 cm. Check the whole seam with a script (sample both meshes every 5 m along the stage 2 outline) and look at six places in `render.py`.
7. Trees: place olives from the image, not only the canopy model. A grove in the image must be a grove in the map. Compare ten 300 m squares side by side (image, top-down render) and keep the sheets out of git.
8. Build stage 2 with the background ground. Record build time, peak memory, track size, draw calls.
9. Full-circle check: for one point every 500 m along every route, render four views (north, east, south, west) at eye height. No view may show the end of the ground against the sky where the height model says there is land within 3 km.

**Gate:** the full-circle check passes at every point; the seam check shows no gap and no step over 10 cm; `survey.py` and `elevation.py` are no worse than build 9; the track file is under 2 GB; build memory stays under 22 GB; the owner is sent four before-and-after view pairs.

**Evidence:** `out/S2/renders/fullcircle/` (not in git), the seam report, the numbers from steps 2 and 8 in `PROGRESS.md`.

**If it fails:** if memory or draw calls do not allow the chosen area, reduce in this order: tree density beyond 1 km from the route, terrain mesh to 12 m, the area outside the loop. Never reduce the inside of the loop below "ground and trees present". If no approach in step 4 works, record what each one did under `Blocked` and stop.
