# koura/

The project's own code. The map generator itself lives in `openlaps/` (created by `setup.sh`, not tracked here).

| File | What it does |
|---|---|
| `setup.sh` | One-time setup: clones the generator at the pinned commit, applies `openlaps_koura.patch`, creates `.venv`. |
| `build.py` | Builds a stage into an Assetto Corsa track folder. `python koura/build.py <stage> [--name ID] [--title T] [--no-imagery] [--no-canopy] [--res N]` |
| `kart_pts.py` | Karting Mania traced by hand from aerial imagery, in image pixels. |
| `openlaps_koura.patch` | Every change made to the generator, as one diff against the pinned commit. |
| `data/osm_koura.json` | Snapshot of the OpenStreetMap data the map is built from. |
| `ride.py` | Walks the named routes on the built road surface: vertical g at speed, kinks, holes. |
| `grade.py` | Slope wobble on one stretch of a route, with an optional text plot. |
| `elevation.py` | Compares each route's heights and total climb with the raw height model. |
| `survey.py` | Walks every road of the map and lists the worst places with coordinates. |

## Stages

Defined in `handoff/inputs/zone.json`.

| Stage | Area | Build time | Use |
|---|---|---|---|
| `S1` | Btouratij and Nakhle, 10 km² | 3 min | the detailed village box |
| `S2` | the whole map, 27.5 km² | 20 min, 22 GB | what gets installed |
| `K` | Karting Mania | 1 min | kart track work |
| `A` | Amioun to Kousba highway strip | 1 min | road smoothness tests |
| `P` | Kousba east hairpin | 30 s | one known bad spot |

Always build under a memory cap, for example `(ulimit -v 22000000; .venv/bin/python koura/build.py S2)`.

## Tuning switches

Environment variables read by the patched generator. The defaults are the values in use.

| Variable | Default | Effect |
|---|---|---|
| `KOURA_SPLINE_L` | 30 | Length scale (m) of the network-wide grade smoothing. 0 turns it off. |
| `KOURA_SIGMA` | 5 | Radius (m) of the surface ironing. |
| `KOURA_SUAVIZAR` | 1 | Surface ironing on or off. |
| `KOURA_BANDA` | 0.5 | How far (m) the merge pass may pull two road pieces together. |
| `KOURA_CELDA` | 0.5 or 1.5 | Grid cell (m) of the merge pass; `build.py` picks 1.5 for large stages to save memory. |
| `KOURA_TAPAR` | 1 | Pave small holes inside roads. |
| `KOURA_PASA` | 1 | Through streets keep their own height at junctions. |
| `KOURA_PLANO` | 1 | One tangent plane per junction. |
| `KOURA_PERFIL` | 1 | Multiplier on the per-street profile filter. Above 1 flattens real hills. |
| `KOURA_PUENTES` | 0 | 1 builds OSM bridges as separate decks (they leave a ground band across the road). |
| `KOURA_DUMP` | unset | Path to write the designed network heights to, for debugging. |

## Measuring a build

```bash
.venv/bin/python koura/survey.py out/S2/koura_preview.glb --out handoff/evidence/survey.json
.venv/bin/python koura/ride.py   out/S2/koura_preview.glb
.venv/bin/python koura/grade.py  out/S2/koura_preview.glb loop 15.3 17.4 --plot
```
