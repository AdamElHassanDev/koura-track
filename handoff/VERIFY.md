# Verification

Two rings. The inner ring runs after every build and needs no game. The outer ring runs at stage ends.

Paths used below:

```
AC    = /mnt/Linux_HDD/SteamLibrary/steamapps/common/assettocorsa
PFX   = /mnt/Linux_HDD/SteamLibrary/steamapps/compatdata/244210/pfx
DOCS  = $PFX/drive_c/users/steamuser/Documents/Assetto Corsa
OUT   = out/<stage>            contains <id>.glb and assetto_corsa/<id>/
TRACK = $OUT/assetto_corsa/<id>
```

## Inner ring: `koura/verify_static.py <stage>`

State on 2026-11-24: this script and the `koura/ac/` scripts below are not written yet (WP0 and WP1 create them). Until then use the interim checks in `BASE.md` section 3. The openlaps tools named in the table (`kn5_check.py`, `kn5_inspect.py`, `escalones.py`, `defectos.py`, `trafico_check.py`, `rendimiento_ac.py`, `render.py`, `comparar_ruta.py`) do exist in `openlaps/tools/`. Add two checks when writing the script: 19, road smoothness by `koura/survey.py`, no class worse than build 9 by more than 0.2 percentage points; 20, road climb by `koura/elevation.py`, loop climb within 5 m of build 9. Both stop applying when the road-height reserve is lifted and new reference numbers are recorded.

It runs each tool, parses the output, and writes `out/<stage>/verify.json` with one entry per check: name, pass or fail, the number measured, and the raw output path. It exits non-zero if any hard check fails.

| # | Check | Command | Hard pass condition |
|---|---|---|---|
| 1 | Aerial imagery was really used | read the build log | contains the summary line `ortofoto lb_xyz: <ok> ok, <failed> failed` with failed at most 1% of ok. openlaps swallows imagery errors and silently falls back to 10 m satellite colour, so this line is the only proof. "Sentinel-2" appearing in the log is normal: the distant horizon uses it |
| 2 | Track file is structurally valid | `python openlaps/tools/kn5_check.py $TRACK/<id>.kn5` | prints `KN5 OK` |
| 3 | No mesh over the index limit | `kn5_inspect.py --json` | every mesh `v` ≤ 65000 |
| 4 | Required markers | same JSON, `dummies` | `AC_PIT_0` and `AC_START_0` present; count of `AC_PIT_n` equals `pitboxes` in `ui/ui_track.json` |
| 5 | Colliders survived export | same JSON, physics meshes | at least one physics mesh in the collider group for tree trunks and posts, and one for the boundary wall. Unmodified openlaps deletes all of them from the game export |
| 6 | Terrain has a draw distance | same JSON | from work package 6 on: every `terreno` mesh has `lod[1]` > 0, and the under-layer meshes have `lod[1]` = 0 |
| 7 | Steps, seams, holes | `python openlaps/tools/escalones.py $OUT/<id>.glb` | zero holes; steps and seams per km of road not above the baseline recorded in work package 0 |
| 8 | Slivers and grade breaks | `python openlaps/tools/defectos.py $OUT/<id>.glb` | count per km of road not above the baseline |
| 9 | Traffic file | `python openlaps/tools/trafico_check.py $TRACK` | no errors; lanes lie inside the zone |
| 10 | Draw-call estimate | `python openlaps/tools/rendimiento_ac.py $TRACK/<id>.kn5 --grupos` | recorded always; hard limit applies once calibrated in work package 6 |
| 11 | Size | `du`, mesh and texture counts | recorded; no hard limit until S2, then track file under 2 GB |
| 12 | Style | build log and JSON | region is `lb`; species counts include `olivo`; building count within 10% of footprints inside the zone |
| 14 | Every named route is fully built | for each route in `zone.json` whose stage contains it (S1: `nakhle_big_loop`, `nakhle_small_loop`; S2 and S3: all seven), walk its `polyline` every 10 m and measure the distance to the nearest built road centreline in the road network | every sample within 8 m of a built road, and the built roads under the samples form one connected chain (closed for routes marked `closed`). Do not route by the names in `order`; they are labels, and several are not villages |
| 15 | No live-mode script | look in `$TRACK/extension/` | no `vivo.lua`; `ext_config.ini` has no `SCRIPT=vivo.lua` |
| 16 | Distances are true | for each route in `zone.json` built in this stage, compare the built road length under the polyline with `length_km`; also measure three straight-line distances between `key_points` or village points in the built scene against the same distances computed from lat/lon | every difference under 1% |
| 17 | One connected road network | build a graph of all built drivable roads in the stage and count connected pieces | exactly one piece contains the spawn point and every route; any other piece is listed with its length and position, and none is longer than 150 m. Fix by adding the missing link in `roads.json`, never by deleting the island unless imagery shows no road there |
| 18 | Start points | `AC_PIT_n` markers | one per entry in `zone.json` `spawn_points` that lies inside the stage, each on a road, facing along it |
| 13 | Tests | `python -m pytest -q` in the fork | all pass |

Soft checks, looked at by an agent and saved as images in `out/<stage>/renders/`:

- `tools/render.py` from six fixed viewpoints listed in `zone.json` (add them in work package 5): Btouratij centre, the Btouratij to Nakhle road, a junction, a hillside, a village edge, an overview from 300 m up.
- `tools/comparar_ruta.py` contact sheet along the stage's main road.
- The baked top-down image next to the aerial imagery for the same box. Roads must line up within about 3 m.

The numbers in checks 7 and 8 are measured on unmodified openlaps output, which has some hits of its own. The rule is "do not get worse per km, and look at every hit on a main road with `render.py`".

## Outer ring: in the game

Only if work package 1 succeeded. Otherwise list these as "owner must check" in `PROGRESS.md`.

1. `koura/ac/install.py <stage>`: copy `$TRACK` to `$AC/content/tracks/<id>/`, delete `$AC/cache/ai_grids/<id>__*` and `ai_payloads/<id>__*` if present.
2. `koura/ac/probe_points.py <stage>`: write `$DOCS/koura_probe/points.json`.
3. `koura/ac/race_ini.py prepare <id>`: back up and patch `$DOCS/cfg/race.ini`.
4. `koura/ac/launch.py`: start the game, wait for the result file or a timeout, then always restore `race.ini`.
5. `koura/ac/probe_report.py`: read `$DOCS/koura_probe/results.json` and the logs.

Pass conditions:

| Check | Source | Pass |
|---|---|---|
| Track loaded | `$DOCS/logs/log.txt` | a line equal to or starting with `Creating physics track: <id>`, and a line `STARTING PHYSICS ENGINE` |
| No track errors | `log.txt` | no line containing both `<id>` and `ERROR:`, except `NO STAT FOR <id>` |
| No patch errors | `$DOCS/logs/custom_shaders_patch.log` | no line that names `<id>` or `ext_config` and contains `ERROR`, `FAILED` or the explosion emoji |
| Car lands where sent | probe results | distance between requested and actual position ≤ 3 m at every point |
| Wheels on the ground | probe results | for each wheel, car height minus contact height between -0.5 and 1.0 m |
| Collision exists | probe results | downward raycast hits at every point |
| Right surface | probe results | wheel surface index maps to a road surface key at every on-road point. Do not use the `valid_track` flag alone: in openlaps' `surfaces.ini` it is 1 for road-type keys and 0 for grass, sand, dirt, gravel, water and wall, and probe points near verges would fail for no reason |
| Frame rate | probe results | minimum and median recorded. Default target: median at least 60 at the owner's resolution |
| Screenshots | probe app | saved every tenth point to `out/<stage>/ingame/` and looked at by an agent |

There is no racing line on a free-roam track, so the spline-based checks in mapcreator's probe (lateral offset, progress) are removed.

## What only the owner can judge

After each stage, ask the owner for these, and do not wait for the answer before continuing:

1. Does it feel like the real roads: slopes, widths, corners.
2. Which buildings are wrong enough to matter.
3. Frame rate while driving with traffic on.
