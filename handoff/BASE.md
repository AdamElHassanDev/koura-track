# The base you are taking over

Written 2026-11-24 for the agent that continues this project. It describes what exists today. Where this file and an older handoff file disagree, this file is right; tell the owner about the disagreement in `PROGRESS.md`.

Read it fully once. After that, `PROGRESS.md` is the running record.

## 1. In one paragraph

A drivable map of the whole stage 2 ground exists and is installed in the game as `koura_preview` (build 9). The work so far went almost entirely into the road surface, because the owner judged everything else secondary until the roads drove well. Roads are now smooth and follow the 30 m height model. Scenery is generic: correct footprints and positions, wrong appearance. Your job is the scenery and detail, to the standard in `DETAIL-STANDARD.md`. The road heights are being finished by someone else (section 4) and you must not change them.

## 2. What the owner has said, in order

The owner tests by driving and reports by voice, so names are spelled as heard. Every quote is from 2026-11-23 or 2026-11-24.

| After | The owner said |
|---|---|
| Trial, 1 km | "excellent start, more detail than I anticipated road-wise" |
| Build 1 | "Not bad", hills "close, but some are a bit less drastic than they should be"; "weird bumps, either like speed bumps... extremely high, or like an inverted speed bump going into the ground suddenly" |
| Build 2 | "rather than it being smooth road up and down, it's very patchy. I want it to be smooth road so we can drive fast. Some houses aren't there." "intersections... feel like a glitched up mess"; "The carting track is an absolute joke"; "the farther we get away from the center of the village... the worse it gets, especially near Amioun"; "road surface must be excellent to drive on" |
| Build 3 | road "a lot better definitely now, but still could be smoother"; "the curbs are way too strong... The car gets broken if you get near"; junctions "horrible, especially the one in [Btouratij], the village with the statue. You basically drew parking strips" |
| Build 4 | "The road surface itself should be super smooth. Compare it to the same level of Spa-Francorchamps... If you have it about camber and whatnot, yes, keep it, but have the road surface itself be smooth, not jaggedy"; "I care most about the bits and bumps. These are essential to me." |
| Build 8 | "intersections are a lot better, so is road surface. But you have lost a lot of detail and elevation change. Things that should have high elevation are very flat. Keep the smooth road surface, but get the most accurate elevation change possible. That is crucial to me." |
| Build 8 | "Elevation change is critical... I have to feel like I'm driving on the road. It needs to be recognizable." |
| Build 8, for you | "try to get the most detail visually possible... images of the homes to put them in, or structure around them, so the road actually feels like or reminds you of when you drive on it in real life, so you know the direction better rather than it being just regular models" |
| Build 8, for you | "the dead parts of the map in the center where there is no terrain should be filled with grass and olive trees. Vegetation and walls must also be accurate... The scenery needs to feel very real." |

| Build 9 | "The map definitely feels a lot better." Long straights with a steady climb feel "very flat" (example: Aaba to Kfar Hazir), while short steep climbs feel right. The road there matches the height model, so this is road-height work and waits for the phone recording |

Build 9 loads and drives (owner, 2026-11-24).

What this tells you about the owner: they notice the road surface first, then junctions, then whether the place is recognisable. They want causes found, not spots patched ("Don't fix just it. Try to find the root cause."). They do not want to be asked questions during work.

## 3. What exists

### Files

| Path | What it is | Tracked in git |
|---|---|---|
| `openlaps/` | The generator fork, branch `koura`, six commits on top of `d9e713c`. Has its own git history | No. Its changes reach GitHub as `koura/openlaps_koura.patch` |
| `koura/build.py` | Builds a stage. The only way to build | Yes |
| `koura/kart_pts.py` | Karting Mania traced from the aerial image: `TRACK` (77 points, 0.246 m per pixel), `PADDOCK`, `ENTR2` | Yes |
| `koura/survey.py`, `ride.py`, `grade.py`, `elevation.py` | Road measuring tools (section 6) | Yes |
| `koura/data/osm_koura.json` | Map-data snapshot. Covers stage 2, not all of stage 3 | Yes |
| `koura/setup.sh` | Fresh-machine setup. Never run end to end | Yes |
| `handoff/inputs/zone.json` | Origin, stages, routes, start points. Never change `origin` | Yes |
| `.venv/` | Python 3.12 environment | No |
| `cache/` | Downloaded imagery, height model, canopy | No |
| `out/<stage>/` | Build output: `<id>.glb`, `assetto_corsa/<id>/`, top-down image | No |
| `out_s2.log` | Log of the last stage 2 build | No |
| `recordings/owner/` | The owner's files. Read only for you | No |
| `.bootstrap/gh/bin/gh` | GitHub CLI, logged in as the owner | No |

### Commands that work today

```bash
# build (always under the memory cap; S2 takes about 17 to 20 minutes and about 22 GB)
(ulimit -v 22000000; .venv/bin/python -u koura/build.py S2 --name koura_preview --title "Koura preview" > out_s2.log 2>&1)
(ulimit -v 22000000; .venv/bin/python -u koura/build.py S1)      # 3 minutes

# check the track file
.venv/bin/python openlaps/tools/kn5_check.py out/S2/assetto_corsa/koura_preview/koura_preview.kn5     # must print KN5 OK
find out/S2/assetto_corsa/koura_preview -name "*.lua"                                                # must print nothing

# measure the roads
.venv/bin/python koura/survey.py    out/S2/koura_preview.glb --out handoff/evidence/survey.json
.venv/bin/python koura/elevation.py out/S2/koura_preview.glb
.venv/bin/python koura/ride.py      out/S2/koura_preview.glb
.venv/bin/python koura/grade.py     out/S2/koura_preview.glb loop 15.3 17.4 --plot

# install in the game (only as allowed in section 5)
rsync -a --delete out/S2/assetto_corsa/koura_preview/ /mnt/Linux_HDD/SteamLibrary/steamapps/common/assettocorsa/content/tracks/koura_preview/
```

### Commands the older files name that do not exist yet

`koura/verify_static.py`, `koura/config.toml`, `koura/ac/*.py`, `koura/overrides/*.json`, `koura/tools/make_checklists.py`, `koura/tools/trace_kart.py`. Each is created by the work package that describes it. Until `koura/verify_static.py` exists, the check after every build is the "check the track file" and "measure the roads" blocks above, and `PROGRESS.md` must say "interim checks" beside the result. Writing `verify_static.py` is your first task (section 8).

### Stages

| Stage | Ground | Build time | Use |
|---|---|---|---|
| `S2` | Whole map, 27.5 km², 197.5 km of road, 6,153 buildings, 39,350 trees | 17 to 20 min | What the owner drives |
| `S1` | The green box, 10 km² | 3 min | Detail work in Btouratij and Nakhle |
| `K` | Karting Mania, 0.55 km² | 1 min | Kart track work |
| `A` | Amioun to Kousba highway strip | 1 min | Road tests |
| `P` | Kousba east hairpin | 30 s | Road tests |
| `B` | Aaba bridge on the Btouratij to Aaba road | 30 s | Road tests |

Stage 2 ground is: the stage 1 box, a strip 250 m either side of every named route, a 450 m disc on each of six village centres, and the kart site. Everything else inside the 12.3 by 11.8 km rectangle is empty. That is the "dead ground" the owner means.

### Build 9, measured

| Measure | Value | How |
|---|---|---|
| Track file valid, 11 start slots, no live-mode script | Yes | `kn5_check.py`, file listing |
| Size | 721 MB folder, 11,253 meshes, 4,215 textures | build log |
| Main highways: length with a slope change over 2 % in 8 m | 0.9 % (worst 4.6 %) | `survey.py` |
| Secondary / tertiary / unclassified / residential | 1.0 / 1.2 / 0.9 / 1.5 % (worst 11.6 / 5.6 / 10.0 / 15.3 %) | `survey.py` |
| Loop: road climbs, model climbs, difference | 417 m, 458 m, RMS 0.68 m, max 4.4 m | `elevation.py` |
| Shortcut: road climbs, model climbs | 47 m, 65 m. Not explained yet | `elevation.py` |
| Frame rate | Never measured | |
| Loaded in the game | Yes, the owner drove build 9 on 2026-11-24 | owner |

### What is good

- The road network is complete and connected for stage 2, at true positions, with a pinned origin.
- The road surface is smooth through junctions. One smoothing pass covers the whole network, so a street keeps its own line across every side street.
- Hairpins and forks no longer have pits.
- No pavements and no kerbs. The owner asked for this: kerbs damaged the car and the paved strips looked like parking strips. Do not bring them back without the owner asking.
- Holes inside roads are paved (78 places).
- Karting Mania is one traced surface on one plane.
- Ground texture is 0.5 m aerial imagery.
- Region profile `lb`: flat roofs with water tanks, stone colours, olives placed from the canopy height model.

### What is wrong or missing (your work)

| Problem | Where | Work package |
|---|---|---|
| Every building is a generic box with a generic wall texture | Everywhere | WP9, WP12, WP13 |
| About 1 roof in 10 has no footprint, and newer buildings are missing | Checked in central Btouratij only | WP8, WP12 |
| No ground, grass or trees inside the loop | The whole middle of the map | WP14 |
| Trees come from a canopy height model, not from the image: positions approximate, species guessed, no rows | Everywhere | WP12, WP13 |
| No stone walls, terraces, retaining walls, fences or gates | Everywhere | WP12, WP13 |
| Junction shapes are generic wide patches: no islands, no real kerb lines, no statue at the Btouratij junction | Every junction | WP8, WP12, WP13 |
| Bridges have no side walls (they are built as ordinary road) | Every OSM bridge; first seen at the Aaba bridge, 34.3535, 35.8358 | WP12, WP13: add walls as scenery objects. Do not turn `KOURA_PUENTES` on |
| Some of the 78 paved holes may be real islands or yards | Counted in the build log line containing `huecos dentro de la calzada`; positions are not logged yet, so add logging first | WP8 |
| Kart track: no tyre walls, kerbs, concrete colour, pit building, timing, driving direction; slope is a guess (2.5 %) | Karting Mania | WP11 |
| New places missing: Knots, Clutch N' Carb and others | `inputs/recent_places.json` | WP9 |
| Frame rate unknown; build needs 22 GB | Stage 2 | WP6 |
| No automated in-game check | | WP1 |
| A dip the owner filmed in `recordings/owner/bumps_2026-11-23.mp4` was never located | Unknown | Not yours: section 4 |
| Worst remaining road spots | 34.30341, 35.85864 (11.6 %); 34.29912, 35.84988 (11.0 %); full list in `evidence/survey.json` | Not yours: section 4 |

## 4. Reserved: road heights

**You must not change how road heights are computed.** The owner is recording the real roads with a phone (pressure sensor and GPS). When the recording arrives, the road profiles will be fitted to it in the reserved code. If you edit the same code, one of the two pieces of work is lost.

Reserved, in `openlaps/openlaps/roads.py`:

- the functions `_elevation`, `_alisar_red`, `_merge_forks`, `_acuerdos_verticales`, `_altura_cruce`, `suavizar_rodadura`, `armonizar_calzadas`, `alisar_picos`, `_pista_kart` (height part only);
- the default values of `KOURA_SPLINE_L`, `KOURA_SIGMA`, `KOURA_SUAVIZAR`, `KOURA_BANDA`, `KOURA_CELDA`, `KOURA_PASA`, `KOURA_PLANO`, `KOURA_PERFIL`, `KOURA_PUENTES`, `KOURA_TAPAR`;
- `koura/elevation.py`, `survey.py`, `grade.py`, `ride.py` (you may run them; do not change what they measure).

Open to you:

- everything about the road in plan view through override files: width, lanes, added, removed and moved roads, junction outlines, islands, markings, surface material and colour;
- everything beside the road: walls, verges, poles, signs, buildings, trees;
- the terrain away from the road, provided it still meets the road edge without a step.

If your work seems to need a change in reserved code, do not make it. Write the need in `PROGRESS.md` under `For the road-height work` with the place (latitude, longitude) and what you saw.

The reserve ends when a row in `PROGRESS.md` says "Road-height reserve lifted". Until you see that row, it holds.

**Never store an absolute height.** Every object you add is positioned by latitude and longitude (or local x, y) and takes its height from the terrain or the road at build time. An override may store a height above ground ("wall 1.8 m high", "building 3 floors") but never a height above sea level or a local z. Reason: the road heights will change by up to a few metres when the recording is fitted, and everything must move with them on a rebuild.

Because of this, anything that touches the road edge (retaining walls, cuttings, bridge walls, driveways) can be built now but must be looked at again after the reserve is lifted. Mark those rows `recheck after heights` in the checklists.

## 5. Sharing the machine and the game

The owner uses this desktop and drives the map while you work. Another agent may be working on the road heights at the same time.

1. **One large build at a time.** Before starting `S2` or `S1`, run `pgrep -af "koura/build.py"`. If a build is running, wait for it. Two stage 2 builds do not fit in 30 GB and the machine freezes.
2. **Stop a build by process id only**: find the python process with `pgrep -af "koura/build.py"` and `kill <pid>`. Never use `pkill` with a pattern. Never stop a build you did not start.
3. **Build into your own output name while you work**: `--name koura_wip`. Use `--name koura_preview` only for a build that is going to the owner.
4. **Installing over `koura_preview`** is allowed at the end of a work package, when the checks pass, and when the game is not running (`pgrep -f acs.exe` prints nothing). Then add a `CHANGELOG.md` entry with the next build number. Never install while the game is running: the owner may be mid-drive.
5. **`recordings/owner/` is read only.** Never delete, move or rename anything in it. It is ignored by git; keep it that way.
6. **Do not start the game** unless the owner's prompt for that session says the game is free (this matters for WP1).
7. Tests are small stages first. Use `K`, `A`, `P`, `B`, or add a new small stage to `zone.json` for the place you are working on. Run `S2` once at the end of the work package.

## 6. The measuring tools

| Tool | What it answers | Read it as |
|---|---|---|
| `survey.py` | Where is the road not smooth? Walks every OSM road on the built mesh | Worst slope change in 8 m per road, with coordinates. Target: nothing over 2 % |
| `elevation.py` | Does the road climb as much as the ground? | Road climb against the 30 m model per route, and the difference. The model includes roofs and trees, so the road should climb slightly less |
| `ride.py` | How does it feel at speed on the named routes? | Share of the route over 0.5 g vertical at 100 km/h |
| `grade.py` | What does one stretch look like? | Text plot of slope along a route between two distances in km |

Rule for you: run `survey.py` and `elevation.py` after every stage 2 build and put the per-class figures in `PROGRESS.md`. If either gets worse than build 9 by more than 0.2 percentage points on any class, or the loop climb changes by more than 5 m, your change touched the road. Find out how and undo that part.

## 7. Lessons already paid for

Do not repeat these.

1. Narrower lanes and pavements in the `lb` region profile broke junction surfaces. Lane and pavement widths stay at the generator's defaults.
2. A weld-and-relax pass on steep triangles (`alisar_picos`) moved roads by 2.3 m and fixed nothing. The steep triangles are thin slivers, not bumps.
3. Finer junction meshes, a tangent plane per junction and larger ironing radius each measured as no help on their own.
4. Smoothing harder flattens hills. The owner noticed at once.
5. Building bridges as separate decks leaves a band of ground across the road, because the decks skip every smoothing pass.
6. A metric that has not been checked against a place the owner complained about is not evidence. Two early metrics counted corners and steady slopes as bumps.
7. Killing only the shell wrapper of a build leaves the python process running and holding 20 GB.
8. The owner's complaint is usually about a class of thing, not the one place named. Look for every other place with the same cause.
9. A file check is not an in-game check. Say which one you did, every time.

## 8. Your order of work

One work package per session, as `RUN.md` says. The order below replaces every older order in `PLAN.md` and `RUN.md`.

| # | Package | What is already there | What is left |
|---|---|---|---|
| 1 | WP0 Setup and baseline | Environment, fork, OSM snapshot | `koura/verify_static.py`, baseline table with build 9 as the baseline, `pytest` run, snapshot extended to the stage 3 rectangle |
| 2 | WP8 OSM ids and override files | Nothing | All of it. Every later package writes into these files |
| 3 | WP6 Performance | Memory cap, coarser merge grid for large stages | All of the rest. Needed before the ground is enlarged |
| 4 | WP14 Ground inside the loop | Nothing | All of it. New package, owner's request |
| 5 | WP9 Footage and recent places | Videos listed | All of it, plus the owner's own video when it arrives (`DASHCAM.md`) |
| 6 | WP12 Btouratij and Nakhle fine detail | Nothing | All of it. Longest package; the owner's first priority |
| 7 | WP11 Karting Mania | Traced surface on one plane | Walls, kerbs, colour, pit building, timing, layout as its own circuit |
| 8 | WP13 Detail outside the green box | Nothing | All of it |
| 9 | WP2, WP3, WP4, WP5, WP7 | First versions in use (see `PROGRESS.md`) | Bring each to its gate, in that order, one per session |
| 10 | WP10 remaining items | | Speed bumps, night lighting, traffic |
| any time | WP1 Game launch and probe | Nothing | Only in a session where the owner says the game is free |

Why this order differs from the old one: stage 1 and stage 2 already build, so the packages that produce them (WP2 to WP5, WP7) only need finishing, and none of that finishing is visible to the owner. What the owner asked for is visible detail and no empty ground. Override files come first because all detail is stored in them.

## 9. What "done" looks like for the owner

From `DETAIL-STANDARD.md`, shortened to the five things the owner will check when driving:

1. The road is smooth and the hills feel real (not yours, but do not break it). One thing here is yours: a steady climb on a long straight reads as flat when nothing beside the road shows the slope. Walls, terraces, poles and buildings stepping up the hill are what make a 2 % grade visible, so on long straights place them with care.
2. At every junction the owner knows which village it is from the buildings.
3. Turning the camera full circle anywhere on a route shows land, trees and buildings, never the edge of the world.
4. Olive groves, walls and terraces are where they really are.
5. The kart track can be lapped and timed.
