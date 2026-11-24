# Plan

Revised 2026-11-23 after the owner asked for Btouratij and Nakhle first, then the rest of the loop. This file holds the design and the rules. The step-by-step work is in `WORK-PACKAGES.md`. The checks every build must pass are in `VERIFY.md`.

## 1. What gets built, in three stages

All three stages are one map that grows. Each stage is a superset of the one before, built from the same origin, so nothing is thrown away.

| Stage | Detailed ground | Detailed area | Build rectangle | Contents |
|---|---|---|---|---|
| S1 | Btouratij and Nakhle box, north to the junction at the start of Ras Masqa | 10.0 km² | 3.6 x 4.1 km | Every road, however small, every building and tree in the box. Holds the 6.0 km Btouratij–Ras Masqa junction–Nakhle loop and the 2.6 km loop inside Nakhle |
| S2 | S1 plus the loop | 27.5 km² | 12.3 x 11.8 km | S1, a 250 m strip each side of the 25.6 km loop road, of the 4.7 km Bishmizzine to Amioun shortcut and of the 5.4 km Kousba road towards Tourza (ends at the turn-off that climbs to Tourza), of the 1.4 km karting access road and of the 3.4 km Dabbousi Farms road, the Karting Mania kart track itself, and a 450 m disc around each village centre on them |
| S3 | Whole named area | 96.5 km² | 12.8 x 11.8 km | Everything between the villages. Stretch goal |

Stage extents live in `inputs/zone.json`. The loop's village order was given by the owner: Btouratij, Aaba, Bishmizzine, Kfar Hazir, Amioun, Kousba, Bsarma, Aaba, Btouratij, mostly on main roads, plus a shortcut from near Bishmizzine straight to Amioun (the road Clutch N' Carb is on). The road geometry between those villages is computed from the map, preferring primary and secondary roads: 15.1 km primary, 9.3 km secondary, 1.0 km tertiary. The owner checked the drawing on 2026-11-23 and confirmed the loop and shortcut as correct, then confirmed the stage 1 box and its two local loops from `evidence/nakhle_loops_map.png` (green box, red big loop, purple small loop). The Tourza road was added at the owner's request and its end point is computed; see `evidence/loop_on_map.png`. Nakhle is not on the main loop; it is inside stage 1. Also added at the owner's request on 2026-11-23, computed and not yet checked by them: the right turn off the Kousba to Bsarma road to the Karting Mania kart track, and the straight Dabbousi Farms road from the track up to Aaba (purple and teal on `evidence/loop_on_map.png`).

**Three detail standards.** Extreme in the Btouratij and Nakhle cores, detailed everywhere else in stages 1 and 2, background in stage 3 only. The table is at the top of work package 13.

Outside the detailed ground but inside the build rectangle, the map shows coarse terrain with satellite colour (openlaps calls this the horizon). Cars cannot leave the detailed ground: an invisible wall follows its edge.

## 2. Design decisions

**D1. Fork openlaps.** Clone at the pinned commit into `./openlaps/`, work on branch `koura`. It is MIT licensed, builds a road network over an area, writes the track in pure Python, and ran here. Its identifiers and comments are Spanish; leave them. New code may be English.

**D2. One run, one origin, one road network.** Do not build separate pieces and join them. The code reading showed that separately built pieces disagree in road height at their seams, and that openlaps' piece baker produces no merged road network, so no traffic and no minimap (`specs/openlaps-change-specs.md` D3, D5). Instead, every stage is a single `pipeline.run` call with:
- the origin pinned at the centre of the full extent (34.3305, 35.8295) through `LocalProjection.marco`, so no stage reaches more than about 9 km from it, and
- a zone polygon that limits where detail is generated.

The zone polygon is openlaps' existing corridor mechanism (`zona` in `pipeline.py`), which already limits roads, terrain tiles, buildings, vegetation, the boundary wall and the horizon fill. Today it only accepts a buffered route in stage and circuit modes. The work is to let it accept any polygon in free-roam mode.

**D3. Never change the origin.** It is not at Btouratij, so the spawn point is pinned separately (work package 2), and any code that assumes "the origin is the middle of the area" must be found and checked (search the fork for `hypot(` and for comments saying `el origen local es el centro`). Every override file, probe point and recording is keyed by OSM id or by lat/lon, never by local metres.

**D4. Lebanon style profile `lb`.** New region in `regions.py` with a detection box ahead of the Europe check. Flat concrete roofs with rooftop water tanks as the base, a share of red-tile hipped roofs on low houses, olive trees in orchards and on farmland, pine, oak and cypress elsewhere, Mediterranean dry and wet seasons, Latin sign text. Details in work package 3.

**D5. Aerial imagery at 0.5 m through a lazy tile reader.** Esri World Imagery, zoom 18. The reader must decode tiles on demand: one array for the S2 build rectangle (12.3 x 11.8 km) would be about 1.7 GB at 0.5 m and 7 GB at 0.25 m. Ground texture resolution is forced to 0.5 m per pixel, and 0.25 m inside the `fine_boxes` of `zone.json` (work package 12 step 1). Imagery colours terrain only; roads keep tiling asphalt.

**D6. Elevation.** Copernicus GLO-30 as openlaps fetches it, with openlaps' road-first smoothing. FABDEM is tried once at S1 through `--dem` and kept only if the static step report improves. GPS tracks from the owner later replace the profile along recorded roads (work package 9).

**D7. Overrides are files, applied at two hook points.** `koura/overrides/roads.json` keyed by OSM way id, merged into way tags right after OSM parsing. `koura/overrides/buildings.json` keyed by OSM id, or by lat/lon for footprints that have no id. This needs OSM ids carried through parsing, which openlaps currently drops (work package 8).

**D8. Performance is designed in before S2.** Terrain gets a draw distance, the coarse horizon is kept under the detailed ground so culled tiles do not leave holes, and terrain tiles share one material per 512 m block instead of one per 128 m tile. The budget is not invented: it is calibrated at S1 by comparing openlaps' static draw-call estimate with a real frame-rate reading.

**D9. Verification has two rings.**
- Inner ring, every build, no game: openlaps' own tools (`kn5_check.py`, `escalones.py`, `defectos.py`, `trafico_check.py`, `rendimiento_ac.py`, `render.py`) plus `pytest`.
- Outer ring, at stage ends: load the track in the game, run the probe app, read the logs.

**D10. The game ring must not stall the run.** Work package 1 is a time-boxed spike to launch the game from a shell. If it fails, continue on the inner ring, mark every result "not game-verified", and list what the owner must drive.

**D11. Free roam needs no racing line.** No `fast_lane.ai`. Keep `traffic.json` for CSP's Traffic mode.

**D12. Live mode is the fallback for S3, not the plan.** openlaps can stream extra ground beyond a baked track at runtime (`--excluir`, `vivo.lua`). It needs a local server running while driving, never frees physics memory and shows no horizon. Use it only if S3 cannot hold frame rate as a baked track.

## 3. Existing tools used, and for what

| Need | Tool | Where |
|---|---|---|
| Generate roads, terrain, buildings, trees, track files | openlaps | fork |
| Track-file structure check | `tools/kn5_check.py` | openlaps |
| Track-file listing, lod and physics names | `tools/kn5_inspect.py` | openlaps |
| Steps, seams and holes in drivable surfaces | `tools/escalones.py` | openlaps, reads the `.glb` |
| Slivers and sharp grade breaks | `tools/defectos.py` | openlaps, reads the `.glb` |
| Draw-call and triangle estimate | `tools/rendimiento_ac.py` | openlaps |
| Traffic file check | `tools/trafico_check.py` | openlaps |
| Driver-view images without the game | `tools/render.py`, `tools/comparar_ruta.py` | openlaps |
| Street-level reference photos | `tools/referencias.py` | openlaps; Mapillary needs a token |
| Photo against render comparison | `tools/comparar_fotos.py` | openlaps |
| In-game probe app | `harness/csp_app/mc_probe` | mapcreator, adapted |
| Facade photo straightening | `roadtoassetto/photo_projection.py`, `scripts/import_facade_photo.py` | road-to-assetto |
| Video frames | `ffmpeg` | installed |
| Photo metadata | `exiftool` | installed |
| Running Windows programs in the game prefix | `protontricks-launch`, GE-Proton9-20 | installed |
| Landmark modelling | Blender | optional, work package 10 only |

## 4. Repository layout to create

```
openlaps/                 fork, branch koura (its own git clone)
koura/
  config.toml             machine paths: game root, game documents, cache
  build.py                wrapper: reads zone.json, pins origin, builds zone polygon, calls pipeline.run
  verify_static.py        runs the inner-ring tools, writes out/<stage>/verify.json
  overrides/roads.json  buildings.json  facades/
  ac/install.py  race_ini.py  launch.py  probe_points.py  probe_report.py
  ac/koura_probe/         the adapted in-game app
handoff/                  this folder
recordings/               owner's GPS, video, photos (not in git)
cache/  out/              not in git
```

`handoff/inputs/zone.json` is the source for stage extents; `koura/build.py` reads it from there.

## 5. Order and parallel lanes

**Superseded on 2026-11-24.** The order now in force is in `BASE.md` section 8. The text below is kept to show which packages depend on which.

```
WP0 setup and baseline
 ├─ lane A: WP1 game launch spike and probe
 ├─ lane B: WP2 export fixes  →  WP3 Lebanon profile
 ├─ lane C: WP4 aerial imagery reader
 └─ lane D: WP8 OSM ids and override files
WP5 zone build and STAGE 1   (needs B, C; uses A if it succeeded)
WP6 performance work, calibrated on S1
WP7 STAGE 2, the loop
WP9 recordings (whenever the owner supplies them; needs D)
WP11 Karting Mania kart track (needs D; part of stage 2)
WP12 Btouratij and Nakhle fine-detail pass (needs stage 1, D and WP9)
WP13 detail pass for everything outside the green box (needs stage 2)
WP10 stage 3 and detail passes
```

**Without sub-agents, do them in this order:** WP0, WP2, WP3, WP4, WP5 (stage 1), WP1, WP6, WP8, WP9, WP12 (stage 1 fine detail), WP7 (stage 2), WP11 (kart track), WP13 (detail outside stage 1), WP10. The owner's first priority is detail in Btouratij, so WP12 comes before the loop. That gets stage 1 built soonest and puts the game spike after there is something worth loading.

Lanes A to D touch different files except `pipeline.py` and `buildings.py`, where B and D edit different functions. Run them as separate sub-agents in git worktrees of the fork and merge in the order B, C, D. Use a fresh reviewer sub-agent on each merged work package: give it the diff and `VERIFY.md`, not the author's summary.

## 6. Working rules

1. Find code by searching for the quoted text in `specs/`, not by line number. Line numbers there are from commit `d9e713c` and shift after the first edit.
2. Run `python -m pytest -q` in the fork after every change. Tests run offline.
3. Every build goes through `koura/build.py`, never the bare CLI, so the origin is always pinned.
4. Every build is followed by `koura/verify_static.py` (until it exists: the interim checks in `BASE.md` section 3). A work package is not done until its gate in `WORK-PACKAGES.md` passes and the evidence file exists.
5. Back up the game's `cfg/race.ini` before touching it and restore it afterwards, every time, including on failure.
6. Never write into the game folder except: the track folder under `content/tracks/`, the probe app under `apps/lua/koura_probe/`, and `steam_appid.txt`.
7. Do not stop to ask the owner. Each open question has a default in `PROGRESS.md`; use it and record that you did.
8. `git init` the project root. Commit after each work package. The fork is a separate clone; commit there on branch `koura`.
9. Fetch OpenStreetMap data once for the whole S3 rectangle in work package 0, save it, and feed every build from that snapshot. This keeps way ids in override files stable and avoids repeated large queries to public servers.
10. Record in `PROGRESS.md`, for each claim, how it was checked: static, render, probe, or owner drove it.
