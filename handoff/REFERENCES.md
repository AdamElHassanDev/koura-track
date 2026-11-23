# References

## Code, pinned to the commits that were read

| Project | Commit | Licence | Use |
|---|---|---|---|
| https://github.com/theopenlaps/openlaps | `d9e713c66c01417fb035c65b81d77093094742c6` (v0.4.0, 2026-11-22) | MIT | Base to fork |
| https://github.com/Forcky/mapcreator | `efe4a7cf9961fc36b2d4fa1739e4c7fb349aa378` (2026-11-21) | Apache-2.0 | Probe apps, validator, format notes |
| https://github.com/gottschalkfelix4-source/road-to-assetto | `dba1c5ea7aa915b614d0bde1dce5270009589590` (2026-10-23) | Apache-2.0 | Facade photos, hillside buildings, section seams |

All three are small, recent projects with few users. openlaps and mapcreator were skimmed for security: both call `subprocess` with fixed argument lists (no shell) in their GUI, harness and worker code, and neither uses `eval`, `exec`, pickle or unexpected network hosts. road-to-assetto was not skimmed for security and has not been run. openlaps' game output includes a Lua script that talks to `127.0.0.1` only.

The full audit reports are in `audits/`. Read those before re-reading the source.

Also seen, not needed:

- https://github.com/nendotools/ac-track-tools : Blender add-on for track setup; its direct track-file export is marked experimental.
- https://github.com/moppius/blender-assetto-corsa-tools : Blender track-file exporter, last updated 2022 for Blender 3.0.
- University of Stuttgart thesis, "Creating Assetto Corsa tracks based on OpenStreetMaps and height data": https://elib.uni-stuttgart.de/items/fc8ede6f-9a01-4a5e-98d9-763ac1ea9179

## Key files inside openlaps

| File | What |
|---|---|
| `openlaps/pipeline.py` | Stages; area and mode logic; boundary wall removal at lines 440 to 442 |
| `openlaps/regions.py` | Style profiles; `detect` at line 289; `REGIONS` at line 134 |
| `openlaps/sources/rasters.py` | Elevation, imagery (`ORTHO_WMS`, `ORTHO_ARCGIS` near line 391), Sentinel-2 seasons near line 245 |
| `openlaps/roads.py` | Road network, profiles, junctions, camber |
| `openlaps/terrain.py` | Terrain tiles; one material per tile at lines 441 to 454 |
| `openlaps/mesh.py` | Mesh grouping and draw distances, lines 16 to 25 |
| `openlaps/export_ac.py` | Track-file and game-folder writer |
| `openlaps/vivo.py`, `vivo_ac.lua` | Live mode and seed-track baking |
| `openlaps/vegetation.py` | Species choice; olive rule at lines 44 to 46 |
| `openlaps/google3d.py` | Optional Google 3D tiles at runtime |
| `docs/assetto-corsa.md`, `ROADMAP.md` | Install notes and known gaps |

Useful openlaps options: `--centro lat,lon`, `--tam` metres, `--bbox s,w,n,e`, `--modo libre|tramo|circuito`, `--region`, `--dem file.tif`, `--dem-es-superficie`, `--res` terrain grid, `--tesela` tile size, `--mpp` ground texture resolution, `--vegetacion` density, `--sin-horizonte`, `--sin-trafico`, `--ac`, `--nombre`, `--titulo`, `--salida`. Cache directory: `OPENLAPS_CACHE`.

## Data

- OpenStreetMap through Overpass; Lebanon extract at https://download.geofabrik.de/asia/lebanon.html
- Copernicus GLO-30: `https://copernicus-dem-30m.s3.amazonaws.com/Copernicus_DSM_COG_10_N34_00_E035_00_DEM/Copernicus_DSM_COG_10_N34_00_E035_00_DEM.tif`
- Esri World Imagery tiles: `https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}`
- Overture buildings: `overturemaps download --bbox=35.755,34.275,35.875,34.395 -f geojson --type=building`
- Microsoft building footprints: https://github.com/microsoft/GlobalMLBuildingFootprints
- ESA WorldCover and Meta/WRI canopy height: fetched by openlaps

## Documentation

- CSP track configuration wiki: https://github.com/ac-custom-shaders-patch/acc-extension-config/wiki
- CSP docs: https://cup.acstuff.club/docs/csp/tracks/grass-fx and https://cup.acstuff.club/docs/csp/tracks/rainfx
- Track basics tutorial: https://assettocorsamods.net/threads/build-your-first-track-basic-guide.12/
- `surfaces.ini` notes: https://www.sites.google.com/site/hagn99/assettocorsa/modding/tracks/data/surfaces-ini
