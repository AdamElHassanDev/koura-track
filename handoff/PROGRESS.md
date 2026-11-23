# Progress ledger

State how each item was checked: static, render, probe, or owner drove it.

| Date | Item | Result | Checked by |
|---|---|---|---|
| 2026-11-23 | Research pass, code reading, handoff folder | Done | n/a |
| 2026-11-23 | Trial build of 1 km Btouratij with unmodified openlaps | Built in 109 s, 76 MB, in `poc/btouratij_poc/` | Build log and top-down image only. **Not loaded in game** |
| 2026-11-23 | Scope set with the owner: loop, shortcut, stage 1 box and both Nakhle loops confirmed on the map. Added and not yet confirmed: Tourza road, karting access road, Dabbousi Farms road. Added work packages 11 (kart track) and 12 (fine detail) | Plan only | Owner saw maps for the confirmed items |
| 2026-11-23 | Trial track `btouratij_poc` copied into the game and driven by the owner | Loads and drives. Owner: "excellent start, more detail than I anticipated road-wise". Problems reported: small parts of street loops are cut off; distances "could be improved a bit"; at the map edge a Spanish live-mode message appears and the car cannot go back | **Owner drove it** |
| 2026-11-23 | Preview build `koura_preview` of the whole stage 2 ground (27.5 km², 198 km of road, 6,110 buildings, 11 start slots, rough Karting Mania from a hand-placed trace), made with quick patches to a copy of openlaps: zone polygon in free-roam mode, edge wall kept, no live-mode script, start points, road-smoothing grid coarsened to 1.5 m to fit in memory. Built in 21 minutes; 1.0 GB track file, 13 M triangles, 12,432 meshes. Copy in `poc/koura_preview/`, patch in `evidence/preview_patch.diff`, driver in `evidence/build_preview.py`, log in `evidence/preview_build.log`. This is NOT the plan's implementation: no Lebanon profile, no aerial imagery, no performance work, origin not pinned to `zone.json` | Track file check passes (`KN5 OK`), top-down image looked at. **Not loaded in game by anyone yet** | Static only |
| 2026-11-23 | Owner drove the first `koura_preview` | Loads and drives. Owner: "not bad"; hills mostly good, "only some places need some work" (less drastic than real); in some places sharp bumps like very high speed bumps, or sudden dips into the ground | **Owner drove it** |
| 2026-11-23 | Real base started in the project: `.venv` (Python 3.12), fork in `openlaps/` on branch `koura` (one commit; full diff against `d9e713c` in `koura/openlaps_koura.patch`), `koura/build.py` (pinned origin from `zone.json`, stage zone polygon, imagery prefetch, OSM snapshot `cache/osm_koura.json`, start points, rough kart track). Fork changes: free-roam zone polygon, edge wall kept, no live-mode script, start points, `XYZRaster` lazy Esri zoom 18 imagery, region `lb` (flat roofs, tanks, stone colours, olives; lane and pavement widths left at defaults because narrower values broke junction surfaces), olives from canopy peaks above 1.3 m, `KOURA_CELDA` | S1 builds in 131 s (10.0 km², 74 km of road, 1,879 buildings). S2 builds in 20 minutes under a 22 GB cap (27.5 km², 198 km of road, 6,110 buildings, 39,000 trees, 795 MB track, 12.7 M triangles, 11,658 meshes, 2,849 imagery tiles all ok). Installed in the game as `koura_preview`, replacing the first one | `KN5 OK`, 11 pit markers, no `vivo.lua`. **Not loaded in game yet** |
| 2026-11-23 | Sharp bumps investigation | `defectos.py` on S1: 1,322 of 316,359 road triangles steeper than 35% (same rate as the unmodified trial), 181 step vertices. A weld-and-relax pass (`roads.alisar_picos`, left in the code, call disabled) moved the road by up to 2.3 m and removed almost none: the flagged triangles are thin slivers, not the bumps. Real cause not found. Suspected: 30 m elevation data at stream crossings and next to buildings. Next step: a profile tool that walks each route and lists short sharp deviations with coordinates, then fix the road profile there | Static only |
| 2026-11-23 | Owner drove the second build and sent `recordings/owner/bumps_2026-11-23.mp4` | Owner: sudden crests and dips, road "very patchy", wants smooth road to drive fast ("road surface must be excellent"); junctions on the highway "a glitched up mess"; "roads where it's just grass in the middle" (location not given, not reproduced: route centre lines have road everywhere, no route runs on a dirt track, ground never pokes above the road); areas away from Btouratij worse, especially near Amioun; some houses missing; kart track "an absolute joke" | **Owner drove it** |
| 2026-11-23 | Ride-quality tool `koura/ride.py` | Walks every route in both lanes on the built road mesh, reports vertical g at 100 km/h (6 m base), kinks, holes, optional ground-above-road. Sharp turns of the route line are excluded. Findings: 79% of kicks sit within 12 m of a junction; edge profiles are 10 times cleaner than the mesh. Tried and measured as no help on their own (kept, harmless): finer junction meshes (`_refinar_interior`), one tangent plane per node (`KOURA_PLANO`). What works: `roads.suavizar_rodadura`, a local plane fit over the drivable surface (sigma 4 m, 3 passes, max 35 cm) | Share of route over 0.5 g, before -> after: loop 2.1 -> 0.4%, shortcut 0.5 -> 0.0, Nakhle big 1.6 -> 0.3, Nakhle small 2.4 -> 0.7, Tourza spur 4.5 -> 2.0, kart access 0.8 -> 0.4, Dabbousi 0.3 -> 0.0. Worst places left are on the Tourza spur (list printed by the tool). Static only |
| 2026-11-23 | Karting Mania rebuilt as one surface | `koura/kart_pts.py` `TRACK` (careful retrace on 3x gridded crops, about 1.5 m accuracy, 832 m line, 8 m wide) + `PADDOCK`; `roads._pista_kart` lays it on one plane (slope capped at 2.5%; the ground model says 6%, real slope unknown). Old street-based kart ways removed; only the entrance way is injected. Test stage `K` in `zone.json` builds it alone in 1 minute. Missing: tyre walls between bands, kerbs, concrete colour, pit building, timing, driving direction | Top-down render matches the aerial outline. Static only |
| 2026-11-23 | Missing houses checked | Footprints are OSM (1,245) + Microsoft (16,961). Overlay on the aerial image in central Btouratij: roughly 1 roof in 10 has no footprint; newer buildings are missing too. To do in WP8/WP12: add from the image | Checked by eye on one 550 m view |
| 2026-11-23 | Third build installed as `koura_preview` | S2, 1,184 s, 197.5 km of road, 13.1 M triangles, `KN5 OK`, 11 pit markers, no `vivo.lua` | **Not loaded in game yet** |
| 2026-11-23 | Owner drove the third build | Owner: road "a lot better definitely now, but still could be smoother"; the dip in the video "is still there" (location of the video not identified); junctions "horrible", grey paved strips look like parking strips, especially the Btouratij junction with the statue; kerbs too high, break the car; grass in the middle at the junction on the Amioun-Kousba road; new kart track not commented yet | **Owner drove it** |
| 2026-11-23 | Fourth build installed as `koura_preview` | Pavements and kerbs off (`config.SIDEWALK_CLASSES = set()`, `CURB_HEIGHT = 0.05` in `koura/build.py`); through streets keep their own height at junctions (`KOURA_PASA`); holes under 400 m2 inside roads paved (20 found, 991 m2); ironing sigma 5 m; `ride.py` also reports long waves (24 m base). Build 1,072 s, 11.4 M triangles | Over 0.5 g: loop 0.3%, shortcut 0.0, Nakhle big 0.4, Nakhle small 0.7, Tourza 2.0, kart access 0.3, Dabbousi 0.0. Long waves over 0.15 g: loop 1.7%, Nakhle small 6.0, Tourza 5.0. `KN5 OK`. **Not loaded in game yet** |
| 2026-11-23 | Known open problems for the next session | 1. Through-road and sigma changes did not move the numbers; the Tourza spur and Nakhle small loop are the roughest. 2. Two bare ground slivers remain between the split carriageways at the junction at local x=500, y=-3672 (34.2974, 35.8349); the hole filler did not catch them. 3. Junction shapes are untouched: wide patches, no real geometry. Needs per-junction work from imagery (WP8/WP12). 4. Kart track: walls, kerbs, colour, timing, real slope. 5. Missing houses (about 1 in 10). 6. Hills too gentle in places: owner has not said where | |
| 2026-11-23 | WP0 Setup and baseline | Partly done: environment, fork, OSM snapshot (covers S2, not all of S3). Not done: `pytest`, baseline table, `verify_static.py`, `config.toml` | |
| | WP1 Game launch spike and probe | Not started | |
| | WP2 Export fixes | Not started | |
| | WP3 Lebanon profile | Not started | |
| | WP4 Aerial imagery reader | Not started | |
| | WP5 Zone build and **stage 1** | Not started | |
| | WP6 Performance work | Not started | |
| | WP7 **Stage 2**, the loop | Not started | |
| | WP8 OSM ids and override files | Not started | |
| | WP9 Footage and recordings | Online videos listed, not downloaded or watched | |
| | WP10 Stage 3 and detail passes | Not started | |
| | WP11 Karting Mania kart track | Located on aerial imagery (34.3261, 35.8525); not traced | |
| | WP12 Btouratij and Nakhle fine-detail pass | Not started | |
| | WP13 Detail pass outside the green box | Not started | |

## Baseline numbers (fill in at WP0)

| Measure | Trial track, unmodified |
|---|---|
| Steps and seams per km of road | |
| Holes | |
| Grade breaks per km | |
| Draw calls, median / p95 | |
| Meshes / triangles / texture MB | 680 / 831,849 / 50 |
| Collider meshes in game export | expected 0 |

## Game ring answers (fill in at WP1)

1. Does `acs.exe` start from a shell in this prefix?
2. Does Custom Shaders Patch load that way?
3. Does a Lua app with `LAZY = NONE` run unopened?

Working launch command:

## Open questions for the owner, with the default used until answered

| Question | Default |
|---|---|
| Does the Kousba road towards Tourza end at the right turn-off (34.28315, 35.89348)? Loop, shortcut, stage 1 box and Nakhle loops were confirmed by the owner on 2026-11-23. | Yes, as computed |
| Where are the new places (Knots and others) that the 2024-01 imagery does not show? List them in `inputs/recent_places.json`. | Only what an agent can find in footage |
| Are the karting access road (right turn off Tripoli Street at 34.3152, 35.8498) and the Dabbousi Farms road (straight road from the track north, then west to Aaba) the ones you mean? | Yes, as computed |
| Where is your own house and street in Btouratij, for the highest detail? | Whole of core A treated equally |
| Which distances felt wrong on the trial drive (which road, too long or too short)? | Treated as unknown; VERIFY check 16 measures scale on every build |
| What frame rate and resolution should the map hold? | Median 60 at the current game settings |
| Do you have a Mapillary token? | No; skip street-photo lookup |
| Which online videos show which roads? | An agent locates them from landmarks |

## Owner must check (append here whenever the game ring is unavailable)

