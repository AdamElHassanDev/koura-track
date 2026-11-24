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
| 2026-11-23 | Owner drove the fourth build | "Better, but still the bumps on the highway are very strong, especially the ones that go down then up", near junctions; the Aaba highway junction "horrible"; "all highways map wide". Wants the road surface "super smooth", compared to Spa, camber kept; "I care most about the bits and bumps"; elevation changes as accurate as possible | **Owner drove it** |
| 2026-11-23 | Road smoothness: cause found and fixed, seventh build installed as `koura_preview` | Tools: `koura/grade.py` (slope wobble on a stretch), `koura/survey.py` (walks every OSM road on the built mesh; output `handoff/evidence/survey.json`, worst first with lat/lon). Fixes in the fork: `RoadNetwork._alisar_red` (one smoothing spline over the whole network, `KOURA_SPLINE_L` 45 m; streets stay smooth through junctions and share junction heights), run again after `_merge_forks` with the overlapping part of hairpin and fork legs held at their shared height (before: 2-3 m pits with a 12 m ramp); `KOURA_BANDA` 0.5 m (merge pass no longer pulls roads 1.6 m apart together); `KOURA_PERFIL` 3 (longer profile filter, measured as little effect). `build.py connect_crossings` found 0 unconnected crossings. Test stages `A` (highway strip) and `P` (Kousba hairpin) build in under a minute | Share of length with a slope change over 2% in 8 m / over 5%, build 5 -> build 7: primary 1.3/0.3 -> 0.4/0.0; secondary 1.5/0.5 -> 0.6/0.0; tertiary 1.8/0.4 -> 0.9/0.0; residential 1.9/0.5 -> 1.2/0.2. Worst kink on the map 45% -> 13.7%. Aaba highway stretch (loop 15.3-17.4 km) worst 15.8% -> 7.4% left lane, 8.0% right. Target for "Spa smooth": nothing over 2%. **Not loaded in game yet** |
| 2026-11-23 | Next on smoothness (**reserved**: road-height work only, see `BASE.md` section 4; not for the detail agent) | Work down `survey.json` from the top with the test-stage method: build a small stage round the spot with `KOURA_DUMP`, compare designed `e.Z` with the mesh, fix the stage that adds the kink. Known left: junction patches on the Aaba highway stretch (7-8%), right-lane holes there (10.9% of that lane has no road under a 1.5 m offset: the two bare slivers between carriageways), short residential stubs | |
| 2026-11-23 | Eighth build installed as `koura_preview`; repo public | Hole filler now grows the road outline by 0.5 m before looking for holes (the two bare slivers at the Aaba highway junction were not quite enclosed): 78 holes paved, 10,797 m2. Check a few of the larger ones: some may be real islands or yards. Smoothness unchanged from build 7. Repo: https://github.com/AdamElHassanDev/koura-track with `README.md`, `koura/setup.sh` (not run end to end on a fresh machine; the patch was checked to apply to the pinned commit) and the OSM snapshot `koura/data/osm_koura.json`. `gh` is in `.bootstrap/gh/bin/gh`, logged in as the owner | `KN5 OK`, 11 pit markers, no `vivo.lua`; junction checked in a top-down render of test stage `A`. **Not loaded in game yet** |
| 2026-11-24 | Ninth build installed as `koura_preview`: real heights restored, bridges as road | Owner drove build 8: surface and junctions better, but hills flattened. Cause: the profile filter multiplier (`KOURA_PERFIL` 3) and a 45 m network spline. Now `KOURA_PERFIL` 1, `KOURA_SPLINE_L` 30. New tool `koura/elevation.py`: road against the raw 30 m model, loop climb 417 m against 458 m (the model includes roofs and trees), difference RMS 0.68 m, max 4.4 m; other routes RMS 0.25 to 0.87 m. Smoothness cost: primary 0.9 % of length over 2 % in 8 m (was 0.4 %), residential 1.5 % (was 1.2 %), worst 15.3 %. Bridges are built as ordinary road (`KOURA_PUENTES` 0): the separate decks skipped every smoothing pass and left a ground band across the road at the Aaba bridge; side walls of bridges are gone as a result. Limit reached: the road now follows the 30 m model, so remaining height errors are the model's. No finer free model exists for Lebanon; paid 5 m (Airbus WorldDEM Neo) is roughly 550 to 1,100 euros for the area. Next: the owner records the roads with a phone (Sensor Logger: location, barometer, orientation; export to `recordings/owner/`), then fit road profiles to it. File checks only (KN5 OK, 11 pit boxes); not driven. |
| 2026-11-24 | Handoff prepared for the detail agent | New `BASE.md` (state of the base, owner's words after each drive, reserved code, shared-machine rules, order of work). New WP14 (ground inside the loop). Road heights reserved until a row here says "Road-height reserve lifted". Stale instructions corrected in `START_HERE.md`, `RUN.md`, `PLAN.md`, `VERIFY.md`, `DETAIL-STANDARD.md`, `DASHCAM.md`. Open: shortcut climbs 47 m against 65 m in the model, not explained; owner's verdict on build 9 pending | Documents only |
| 2026-11-23 | WP0 Setup and baseline | Partly done: environment, fork, OSM snapshot (covers S2, not all of S3). Not done: `pytest`, baseline table, `verify_static.py`, `config.toml`. **Next** | |
| | WP1 Game launch spike and probe | Not started. Only in a session where the owner says the game is free | |
| | WP2 Export fixes | First version in use: edge wall and colliders kept, no live-mode script, 11 start points. Not done: rename to group `limite`, gate | |
| | WP3 Lebanon profile | First version in use: region `lb`, flat roofs, tanks, stone colours, olives. Lane and pavement widths deliberately left at defaults. Gate not run | |
| | WP4 Aerial imagery reader | First version in use: `XYZRaster`, zoom 18, lazy. The `ortofoto lb_xyz:` summary line and gate not done | |
| | WP5 Zone build and **stage 1** | S1 builds in 3 minutes from `zone.json` with the pinned origin. Render viewpoints and gate not done | |
| | WP6 Performance work | Not started, except a memory cap and a coarser merge grid on large stages. Frame rate never measured | |
| | WP7 **Stage 2**, the loop | S2 builds in 17 to 20 minutes and is installed (build 9). Gate not run | |
| | WP8 OSM ids and override files | Not started | |
| | WP9 Footage and recordings | Online videos listed, not downloaded or watched | |
| | WP10 Stage 3 and detail passes | Not started | |
| | WP11 Karting Mania kart track | Traced (`koura/kart_pts.py`, about 1.5 m accuracy) and built as one surface on one plane. Not done: walls, kerbs, colour, pit building, timing, own layout, real slope | |
| | WP12 Btouratij and Nakhle fine-detail pass | Not started | |
| | WP13 Detail pass outside the green box | Not started | |
| | WP14 Ground inside the loop | Not started | |

**Next package:** WP0 (finish it: `koura/verify_static.py`, baseline table with build 9 as the baseline, `pytest`, OSM snapshot for the stage 3 rectangle). Then WP8. Order: `BASE.md` section 8.

## For the road-height work

The detail agent lists here any place where the road heights look wrong, with latitude, longitude and what was seen. It does not fix them (`BASE.md` section 4).

| Date | Place | What was seen |
|---|---|---|
| 2026-11-24 | Shortcut route, whole length | Road climbs 47 m, model 65 m (`koura/elevation.py`) |
| 2026-11-24 | 34.30341, 35.85864 and 34.29912, 35.84988 | Slope change of 11.6 % and 11.0 % in 8 m on secondary roads (`survey.json`) |

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
| Should the kart track be flat, sloped or terraced? | One plane, slope capped at 2.5 % |
| Which hills still feel too flat or too steep after build 9? | None known; wait for the phone recording |
| Where is the dip filmed in `recordings/owner/bumps_2026-11-23.mp4`? | Unknown; road-height work |

## Owner must check (append here whenever the game ring is unavailable)

