Read-only code audit, 2026-11-23, of the commit pinned in REFERENCES.md. Nothing was executed.

**Corrections found later (see `specs/openlaps-change-specs.md`):** the `geo.py` line references in this report are wrong (the file has 80 lines; see `geo.py` `BBox.around` and `LocalProjection`). The "12 x 12 km, 144 km²" sizing was the brief given to the reader, not a measurement; the named-village box is about 68 km². The live-mode baking idea in the verdict was rejected: see PLAN.md decision D2.

# openlaps (v0.4.0) as a base for a 12 km x 12 km Koura free-roam map

The short answer: the pipeline is solid and runs on Linux, but it was built for areas of a few km², not 144 km². I only read files; I didn't run, install or test anything.

Repo root: `<clone>/openlaps`. References below are `file:line` relative to that root.

**One correction first:** Koura (about 34.3N, 35.8E) does not fall to `generic`. `regions.detect` returns the **EU** profile for anything with 34.0–71.5N and -25–45E (`openlaps/regions.py:300-301`). The EU profile (`regions.py:129-130`) has pitched roofs and its species list leaves out `olivo`. Olive trees picked for fields at latitudes below 41.8 (`vegetation.py:44-46`) are therefore swapped for `encino` (oak) by `map_species` (`regions.py:339-346`). That is a poor fit for Koura's olive groves.

---

## 1. How the pipeline works (`openlaps/pipeline.py:110-473`)

**Inputs**
- Either `--centro lat,lon` plus `--tam` (side length in metres), or `--bbox` given as south,west,north,east (`__main__.py:17-20`).
- `BBox.around` builds the box (`geo.py:351`). Everything is projected to local UTM centred on the area (`geo.py:376-392`).

**Stages**
1. **Downloads**, all in parallel with 8 threads (`pipeline.py:145-186`): OSM, DEM, WorldCover, orthophoto *or* Sentinel‑2, a Sentinel‑2 water index (NDWI), canopy height, Microsoft buildings, Catastro or Overture (only for profiles that use them), and a 5 km horizon (DEM plus Sentinel‑2). CC0 textures and materials load meanwhile (`pipeline.py:562-572`).
2. **Terrain object** (`pipeline.py:209`). Terrain resolution is automatic: 2 m up to 2.5 km², 3 m up to 8 km², otherwise 4 m (`pipeline.py:130`).
3. **Buildings and urban mask** from OSM landuse plus WorldCover "built" cells (`pipeline.py:212-254`).
4. **Road network** (`roads.RoadNetwork`, `pipeline.py:258`), then `build_roads` (`pipeline.py:280`).
5. **Terrain**: flatten urban blocks, carve under roads, cover tunnels, carve water and ditches, then tiled meshes with baked textures (`pipeline.py:321-351`). OSM barriers, boundary wall, power lines and fences follow (`pipeline.py:353-361`).
6. **Buildings, edges and wear, street lamps, signs, vegetation, horizon** (`pipeline.py:364-405`).
7. **Export** (`pipeline.py:420-473`):
   - always: `<name>.glb`, `<name>_cenital.jpg` (top-down view), `<name>_cobertura.jpg` (land-cover panel), `<name>.json`;
   - with `--ac`: the AC track folder.
   - Traffic data is built before export (`pipeline.py:414-417`).

**Modes**
- **`libre`** (free roam): `_place_free` puts 12 start grid spots, 8 pit spots, a hotlap start and a timing line on a long straight near the centre (`pipeline.py:810-847`). It writes no AI line and no TV cameras.
- **`tramo`** (A‑B stage, needs `--ruta`):
  - routes along the network (`roads.route`, `roads.py:3271`);
  - start and finish gantries, AB_START/FINISH dummies, side roads closed with fences (`pipeline.py:757-807`);
  - co‑driver pace notes (`notas.py`), TV cameras, `fast_lane.ai`.
  - Above 24 km² it builds only a **220 m corridor** each side of the route and drops the orthophoto and canopy layers (`pipeline.py:132-139`, `476-488`).
- **`circuito`**: the same as `tramo` but closed, with `AC_TIME_0` timing lines and run type "clockwise".

## 2. Area-size limits

**Hard caps**
- **CLI: none.** `--tam` is a plain float (`__main__.py:20`).
- **GUI: 24 km².** `MAX_KM2 = 24.0` (`gui/generador.py:49`, enforced at `:89-91`); the sliders stop at 8000 m (`gui/web/index.html:63-65`).
- **Per mesh: 65,000 vertices**, because AC uses 16‑bit indices (`mesh.py:16`, `export_ac.py:181`). Meshes are split automatically, so this doesn't limit area.

**Practical limits for 12 x 12 km** (my estimates from the code, not measured)
- **Terrain mesh:** 4 m grid gives about 3001 x 3001 ≈ 9 M vertices and 18 M triangles.
- **Terrain tiles:** 128 m tiles (`--tesela`, `terrain.py:407-477`) give about 94 x 94 ≈ **8,800 tiles**. Each has its *own* multilayer material, a baked texture at `mpp` (0.5 m/px without an orthophoto, so 256 px per tile) and a mask (`terrain.py:441-454`). That is roughly 576 Mpx of baked ground, likely **over 1 GB of DDS**.
- **Memory:** the whole KN5 is built in one in‑memory buffer (`export_ac.py:94`, `191-192`), and every tile is kept as a PIL image plus PNG bytes (`terrain.py:444-447`). Expect very high RAM use.
- **No distance culling on terrain:** the `terreno` group has no entry in `GROUP_LOD` (`mesh.py:19-23`), so lodOut is 0 and every terrain tile is always drawn. Its cell size is effectively infinite (`mesh.py:25`).
  - The roadmap says AC performance depends on mesh count (`ROADMAP.md:93-100`). A 12 km map would have tens of thousands of draw calls.
  - "Large areas: LOD by distance, coarser tiles away from roads" is listed only as an idea (`ROADMAP.md:247`).
- **Canopy height** is a 1 m raster over the whole box (`rasters.py:365-385`), sampled every 1.5 m (`vegetation.py:79-92`). That's about 144 Mpx, around 600 MB of float32.
- **Overpass:** one query for the whole box, with `[timeout:180]` (`sources/osm.py:25-49`), but each mirror gets only about 20 s (`osm.py` download timeout=20, a 3 s stagger between mirrors). The fallback is the official OSM API, which splits the box into quarters on HTTP 400 (`osm.py:~157-165`).
- **AC boundary:** the invisible boundary wall is removed from the AC export (`pipeline.py:440-442`), so in AC you can drive off the edge of the map.

**Live (`vivo`) mode** (`openlaps/vivo.py`, `openlaps/vivo_ac.lua`)
- **Pieces:** `L = 256` m pieces, generated with a 64 m margin, then cut exactly at the edge and stitched to neighbours. OSM arrives in 1024 m tiles. Several worker processes generate the most urgent piece, predicted from the car's position and speed (`vivo.py:1-20`, `38-45`).
- **Local server:** each piece runs the full `pipeline.run(..., pedazo=...)` (`vivo.py:108-139`). A local HTTP server on 127.0.0.1:8790 (`vivo.py:1617`) serves the `.olv` binary pieces (`vivo.py:512-543`).
- **Seed track:** `--semilla-ac` builds a seed track. It contains the pieces around the start baked into the KN5, plus a hidden "library" of one tiny mesh per material (`export_ac.py:249-260`, `vivo.py:1304-1402`).
- **In-game script:** `vivo_ac.lua` polls the server with `web.get`, builds physics via `physics.addTrackSurface` and meshes via `createMesh`. It loads within about 430 m and unloads beyond about 640 m (`vivo_ac.lua:1-29`, `320-370`, `1030-1040`).
- **Normal tracks too:** every regular AC export also carries `vivo.lua` in standby, so live mode can extend beyond a baked rectangle (`export_ac.py:373-377`).

**Could live mode cover 12 km?** Yes, in principle. The README says "no area limit" (`README.md:75`), and `--zona W,H` prewarms a fixed area with no CLI cap (`vivo.py:1645-1646`). That is about 47 x 47 ≈ 2,200 pieces; at the README's 8–10 s per piece with 4 workers, about 1.5 h to prewarm once, cached afterwards.

**Live-mode limitations**
- The Python server must be running locally while you drive, so this isn't a self-contained track you can share or run online.
- It needs CSP with `ALLOW_TRACK_SCRIPTS=1` and extended surfaces (`export_ac.py:244-246`).
- **Physics is never freed** once created, because freeing it crashed Embree (`vivo_ac.lua:68-72`). Memory grows as you explore.
- The horizon is disabled (`--sin-horizonte` is forced at `vivo.py:1658`) and the view range is about 430–640 m, so there are no distant valley views.
- The GUI caps the prewarm zone at 24 km² (`gui/envivo.py:48-56`).
- The roadmap states traffic in live mode has no traffic lights yet (`ROADMAP.md:110-117`).

## 3. Data sources for your area (EU or generic profile)

**Elevation**
- Copernicus GLO‑30, a *surface* model (includes trees and roofs), read as COG through GDAL `/vsicurl` from `copernicus-dem-30m.s3.amazonaws.com` (`rasters.py:141-188`).
- It is converted to bare ground with a 70 m grey opening, masked by WorldCover tree and built classes (`terrain.py:58-71`), then resampled on a 10 m working grid (`terrain.py:35-56`).
- **`--dem` override:** any GeoTIFF rasterio can open, in any CRS (bounds go 4326 → `ds.crs`), band 1 only, nodata filled with the median (`rasters.py:203-213`). It is treated as bare ground unless you pass `--dem-es-superficie` (`pipeline.py:46-48`).
- The **5 km horizon always uses Copernicus**, even with `--dem` (`pipeline.py:185`).

**Ground imagery**
- National orthophoto sources are only PNOA, Géoplateforme (WMS) and NAIP (ArcGIS), hard-coded in `ORTHO_WMS` and `ORTHO_ARCGIS` (`rasters.py:391-402`). EU and generic profiles have `ortho=""`.
- So you get **Sentinel‑2 L2A true colour at 10 m** via the Element84 STAC search (`earth-search.aws.element84.com`), filtered to under 10 % cloud and mixing up to 3 scenes (`rasters.py:219-313`).
- **There is no option to supply your own orthophoto GeoTIFF or an XYZ tile URL.** Adding one means a new entry in `ORTHO_WMS`/`ORTHO_ARCGIS` (WMS GetMap or ArcGIS exportImage only) or a new reader.
- **Season trap:** `seca` (the default) searches Nov–Apr and `lluvias` searches Jul–Oct (`rasters.py:245-246`). Those are Mexican seasons; in Lebanon Nov–Apr is the wet, green, cloudy half of the year.

**Land cover and water**
- ESA WorldCover 2021 at 10 m from `esa-worldcover.s3.eu-central-1.amazonaws.com` (`rasters.py:148-200`).
- Water also uses a Sentinel‑2 NDWI index (`rasters.py:316-350`).

**Canopy**
- Meta/WRI 1 m canopy height from `dataforgood-fb-data.s3.amazonaws.com` (`rasters.py:365-385`).
- Trees are placed from it (`vegetation.py:109-113`, `159+`).

**Buildings**
- Sources: OSM, plus Microsoft Global ML footprints added where they don't overlap OSM. The Microsoft index CSV comes from `minedbuildings.z5.web.core.windows.net`, tiles are cached as `.csv.gz`, and a SQLite index is built locally (`sources/msbuildings.py:15-122`, `buildings.py:72-82`). Catastro and Overture are profile-gated (Spain and US only).
- Both Microsoft and canopy tile lookups check only the four bbox corners (`msbuildings.py:75`, `rasters.py:368`). That's fine at 12 km.
- **Height order** (`buildings.py:295-320`):
  1. OSM `height`;
  2. `building:levels` x 3.0 m + 0.3;
  3. Microsoft or Overture `height`;
  4. type rules: church 12–18 m; industrial or retail 6–9 m; barn 4.5–6.5 m; shed 2.6 m; footprint over 600 m² gives 7–11 m;
  5. otherwise a random pick from the profile's `levels_default`.

**Textures**
- ambientCG CC0, 1K JPG zips (asphalt, paving, concrete, plaster, gravel, leaf litter, grass, rock) and leaf/bark cutouts (`sources/cc0.py:137-201`, `foliage.py:238-256`).
- Everything else is procedural.

**Every external host in the code**

| Purpose | Hosts |
|---|---|
| OSM | `maps.mail.ru` (Overpass), `overpass-api.de`, `overpass.kumi.systems`, `overpass.private.coffee`, `api.openstreetmap.org` |
| Rasters | `copernicus-dem-30m.s3.amazonaws.com`, `esa-worldcover.s3.eu-central-1.amazonaws.com`, `earth-search.aws.element84.com` (scene hrefs come from its response, usually Sentinel COG buckets on S3), `dataforgood-fb-data.s3.amazonaws.com` |
| Buildings | `minedbuildings.z5.web.core.windows.net` (tile URLs come from its CSV) |
| Textures | `ambientcg.com` |
| Region-gated (not used for Lebanon) | `www.ign.es`, `servicios.idee.es`, `data.geopf.fr`, `imagery.nationalmap.gov`, `elevation.nationalmap.gov`, `ovc.catastro.meh.es`, `overturemaps-us-west-2.s3.amazonaws.com`, `stac.overturemaps.org` |
| Google 3D | `api.cesium.com`, then the Google tile hosts it returns |
| GUI | `nominatim.openstreetmap.org` (`gui/app.py:78,146`), `tile.openstreetmap.org`, `tiles.maps.eox.at`, `fonts.googleapis.com`, `cdnjs.cloudflare.com` |
| Viewer | `cdn.jsdelivr.net` (three.js) |
| Windows launcher | `github.com/astral-sh/uv` releases, `go.microsoft.com` (WebView2 installer) (`packaging/lanzador/OpenLaps.cs:107,493`) |
| `tools/referencias.py` only | Panoramax, Mapillary, Wikimedia Commons |

## 4. Google 3D (`openlaps/google3d.py`, `openlaps/google3d_ac.lua`, `openlaps/gui/google3d.py`)

- **What it is:** Google Photorealistic 3D Tiles, reached through Cesium ion asset `2275207` (`google3d.py:49`).
- **What it needs:** a free **Cesium ion token** with that asset added to the account, passed as `--token` or `CESIUM_ION_TOKEN` (`google3d.py:13-14`, `1581`, `1603`). The token gets the Google URL and key from `api.cesium.com/v1/assets/2275207/endpoint` (`google3d.py:123-127`). Draco decoding needs the `DracoPy` extra (`pyproject.toml:36`).
- **How it gets into AC:**
  - A local server on 127.0.0.1:8772 picks tiles within `--radio` (500 m) of the car, converts them to track coordinates and holds them **in memory only**.
  - It trims them against openlaps roads and walls, and fills gaps where the Google mesh ends in mid-air (`google3d.py:1-20`, `50-70`).
  - `--instalar` puts `google3d_ac.lua` into `extension/` and adds a `[SCRIPT_n]` entry (`google3d.py:79-91`).
  - The Lua script polls `/lista` and `/malla/<id>`, creates meshes with `createMesh`, and hides openlaps' own buildings and horizon (`google3d_ac.lua:1-40`, `95`, `122`, `202`).
- **Limits:** it is visual only (physics stays openlaps). It is runtime-only by design to respect Google's terms, so you can't bake or distribute it. Whether rural Koura has photorealistic coverage is unknown.
- **GUI side:** the GUI launches it as a subprocess, passing the token through the environment (`gui/google3d.py:54-63`), and stops it with Windows `taskkill` (`gui/google3d.py:80`).

## 5. KN5 and AC files (`openlaps/export_ac.py`)

**How the KN5 is written**
- **Pure Python** with struct, numpy and Pillow: header `sc6969` version 5, embedded DDS textures, materials, a node tree (`export_ac.py:87-193`).
- The DDS encoder (DXT1/DXT5 with mipmaps) is numba-compiled (`dds.py:1-25`).
- **No Blender, ksEditor or wine is needed.**
- Shaders used: `ksPerPixel`, `ksPerPixelAT`, `ksPerPixelNM`, and `ksMultilayer_fresnel_nm` for terrain (`export_ac.py:83-84`).

**Files written** (`export_ac.py:354-450`)
- Track root:
  - `<id>.kn5`, `models.ini`;
  - `map.png`, `openlaps_geo.json`, `ATRIBUCIONES.txt`;
  - `NOTAS.txt` (stages only).
- `data/`:
  - `surfaces.ini`, `lighting.ini`, `map.ini`;
  - `traffic.json` (unless `--sin-trafico`);
  - `cameras.ini` (only if cameras exist, i.e. stages);
  - `notas.json` (stages only).
- `ui/`: `ui_track.json`, `outline.png`, `preview.png`.
- `ai/`: `fast_lane.ai` (v7) and `pit_lane.ai`, **only when there is a route**. Free roam gets no AI line.
- `extension/`: `ext_config.ini`, `vivo.lua`, `notas.lua` (stages only).

**Surfaces** (`export_ac.py:196-246`)
- Keys: ROAD, PITLANE, PAVEMENT, KERB, GRASS, SAND, DIRT, GRAVEL, WATER, WALL, LOOSE, MXGRAVA, MXTIERRA, MXARENA, MXPASTO, MXCOBBLE, MXVADO, MXROCA.
- The loose surfaces get CSP `_EXT_SURFACE_TYPE` (gravel, sand or grass) and Perlin noise; `ALLOW_TRACK_SCRIPTS=1` is set.

**`ext_config.ini`** (`export_ac.py:309-336`)
- `[GRASS_FX]` on terrain materials, `[RAIN_FX]` puddles, roughness and lines.
- `ksTree` shader replacement for vegetation; trees are meshes, not CSP `[TREES]`.
- Night emissive adjustments for facades and lamps, and one `[LIGHT_n]` per street lamp.

**Physics vs visual mesh**
- They are the **same mesh**. Meshes that carry physics are named `1<KEY>_<group>_<material>_c<x>_<y>…` (`export_glb.py:29-30`, `mesh.py:124-125`).
- Ground physics comes per triangle from the land-cover map, with rock above 38° slope (`terrain.py:485-490`).

**Road geometry**
- **Resolution:** 1.5 m along the road (`roads.py:38`). Across, there is a vertex at each edge and the centre, plus one about every 3.6 m on wide roads; unpaved roads get extra vertices at each wheel rut (`roads.py:1317-1328`).
- **Smoothing in plan:** the centreline is relaxed within a tube around the OSM line (`_suavizar_planta`, `roads.py:118`).
- **Vertical profile:** DEM sampled along whole road chains, median filtered, then Gaussian with a per-class sigma of 5–45 m (`config.py:40-62`). Vertical curves are fitted to design speed (`roads.py:404-437`). Junction heights are weighted by road priority, x3 per level (`roads.py:980-1052`).
- **A second pass** fits one continuous surface across roads and junctions (`armonizar_calzadas`, `roads.py:1464`).
- **Camber:** superelevation only on rural classes, up to 8 %, computed as v²/127R, smoothed and ramped to zero 20 m from each junction (`roads.py:1190-1205`). Paved roads have **no crown** otherwise. Unpaved roads get crown, ruts, potholes and width noise (`roads.py:336-374`).
- **Junctions:** built polygons with merged clusters and corner fillets (`roads.py:1977+`, `1757`, `2272`).

**Kerbs, sidewalks, walls**
- Urban sidewalks with chamfered curbs (`roads.py:2678+`; 1.8 m wide, 16 cm high per `config.py:100-101`).
- The **KERB surface is defined but never assigned** to any geometry, so there are no racing kerbs.

**Barriers**
- Rural guardrails by heuristic where the embankment drop exceeds 2.5 m (6 m if OSM already has guardrails), plus delineator posts (`roads.py:2912-2967`).
- OSM `guard_rail`, `wall`, `retaining_wall` and `jersey_barrier` are built with collision (`barriers.py:1-25`).

**Bridges and tunnels**
- Bridge decks with WALL-physics parapets (`roads.py:2992-3071`).
- Tunnels are built by default only for primary-and-above roads (`config.py:30-36`); 5.8 m clearance (`roads.py:3073-3171`).
- Fords where dirt roads cross streams (`roads.py:375-379`, `601`).

## 6. Road width, lanes, markings, and a Lebanon profile

**Width and lanes**
- Width comes from OSM `width` (if between 2.5 and 40 m), otherwise lanes x lane width (`roads.py:819-851`).
- Lanes come from OSM `lanes` (1–8), or the per-class default in `config.ROAD_CLASS` (`config.py:40-62`). Shoulders are included in the stored half-width field but not in the default width calculation.
- Lane width is multiplied by the profile's `lane_mult`.

**Markings** (`roads.py:2470-2540`)
- Only marked classes get lines (`config.py:65-66`), and never on dirt or cobbles.
- Overtaking (dashed vs solid centre line) is decided from sight distance against the DEM, using `pass_sight`.
- Driving is right-hand only; there is no driving-side field. Lebanon drives on the right, so that's fine.
- Tags such as `lanes`, `overtaking`, `lane_markings` and `turn:lanes` for markings are still to do (`ROADMAP.md:219`).

**`Region` fields** (`regions.py:20-71`)

| Group | Fields |
|---|---|
| Identity | `code`, `name`, `country` |
| Markings | `center_mat`, `left_edge_mat`, `line_w`, `line_w_fast`, `dash_rural`, `dash_urban`, `curb_yellow_corners` |
| Signs | `stop_text`, `curve_sign`, `speed_unit` |
| Buildings | `roof`, `roof_colors`, `tinaco` (rooftop water tanks), `facade_colors`, `levels_default`, `facade_style`, `roof_kind`, `flat_from_floors`, `tower_floors` |
| Road look | `asphalt_tone`, `pass_sight`, `delineator`, `delineator_gap` |
| Vegetation | `species` |
| Data sources | `ortho`, `dem`, `cadastre`, `heights`, `ortho_mpp` |
| Streets | `lane_mult`, `rural_sin_asfalto`, `sidewalk_w`, `center_double`, `parking_default` |
| Other | `attribution`, `sub`, `sub_name`, `sub_name_en` |

**Example (Mexico, `regions.py:74-85`):**
```python
MX = Region(code="mx", name="México", country="Mexico",
    center_mat="raya_amarilla", left_edge_mat="raya_amarilla",
    line_w=0.15, line_w_fast=0.15, dash_rural=(5.0, 10.0), dash_urban=(3.0, 5.0),
    curb_yellow_corners=True, stop_text="ALTO", curve_sign="diamond",
    roof="flat", tinaco=True, facade_colors=[...], levels_default=(1, 1, 2, 2, 3),
    species=("encino", "pino", "arbusto", "tropical", "palma", "organo", "maguey"),
    rural_sin_asfalto=True)
```

**What an `lb` profile needs**
- Add it to the `REGIONS` dict (`regions.py:134`) and a detect box placed *before* the EU check in `detect` (`regions.py:289-302`).
- Suggested values: `roof="flat"`, `tinaco=True` (Lebanese rooftop tanks), `species` including `"olivo"`, `levels_default` of about (2, 2, 3, 3, 4), `lane_mult` below 1 for narrow village roads, and a sensible `stop_text`.
- **Problems outside regions.py:**
  - Vegetation logic is either Mexican or "EU" (`vegetation.py:24-50`).
  - The Sentinel‑2 season windows need changing.
  - The STOP sign text is drawn with whatever `_font` resolves to (`textures.py:516`). Arabic script would need a suitable font and possibly shaping; I didn't check what `_font` loads.

## 7. Dependencies, platform, install, CLI flags

**Dependencies and platform**
- Python ≥ 3.11 (`pyproject.toml:12`).
- Required: `mapbox_earcut`, `numba`, `numpy>=2`, `pillow`, `pyproj`, `rasterio>=1.4`, `scipy`, `shapely>=2` (`pyproject.toml:13-22`).
- Extras: `overture` (pyarrow), `google3d` (DracoPy), `gui` (pywebview), `dev` (pytest, ruff) (`pyproject.toml:31-38`).
- **The CLI and generator are OS-independent.** The README gives Linux install steps (`README.md:31`), and the Unix code path exists (`procesos.py`).
- The **GUI is Windows-only**: ctypes `windll`, `winreg`, `mklink /J`, `taskkill`, `explorer`, WebView2.
- `vivo --ac-carpeta` defaults to a Windows Steam path; if that path doesn't exist, nothing is installed (`vivo.py:1653-1654`, `1676`).

**Installing into AC**
- Copy `salida/assetto_corsa/<name>/` to `<AC>/content/tracks/`, or junction it there (`docs/assetto-corsa.md:6-17`).
- CSP is required for live mode, traffic, GrassFX and the loose-surface physics; plain tracks load without CSP (`README.md:142-145`).
- Cache: `~/.cache/openlaps`, or set `OPENLAPS_CACHE` (`sources/cache.py:10`).

**`openlaps` CLI flags** (`__main__.py:15-60`)

| Flag | Meaning |
|---|---|
| `--centro lat,lon` | Centre of the area |
| `--bbox s,w,n,e` | Area as a box (alternative to `--centro`) |
| `--tam` | Side length in metres (default 1000) |
| `--modo libre\|tramo\|circuito` | Free roam, stage, circuit |
| `--ruta "lat,lon;..."` | Waypoints for stage or circuit |
| `--corredor auto\|m\|0` | Corridor width for stages (auto: 220 m above 24 km²; 0 = full rectangle) |
| `--dem file.tif` | Local elevation GeoTIFF |
| `--dem-es-superficie` | Local DEM includes trees and roofs |
| `--temporada seca\|lluvias` | Season ("dry" or "rainy", Mexican months) |
| `--res` | Terrain mesh resolution in m (auto 2–4) |
| `--tesela` | Terrain tile size in m (default 128) |
| `--mpp` | Ground texture metres per pixel (auto 0.25 with orthophoto, 0.5 without) |
| `--region` | Profile: auto, mx, es, fr, us, eu, generic |
| `--subregion` | Style within a country (auto, no, or a code) |
| `--vegetacion` | Vegetation density multiplier |
| `--terraceria auto\|osm\|rural` | Unpaved roads: inferred, OSM-tagged only, or all minor rural roads |
| `--sin-cunetas` | No ditches beside dirt roads |
| `--veredas` | OSM paths and bridleways become drivable dirt tracks |
| `--tuneles principales\|todos\|ninguno` | Which tunnels to build |
| `--sin-orto` | No national orthophoto |
| `--sin-microsoft` | No Microsoft footprints |
| `--sin-satelite` | No Sentinel‑2 |
| `--sin-dosel` | No canopy height |
| `--sin-horizonte` | No 5 km horizon |
| `--sin-catastro` | No Spanish Catastro |
| `--sin-overture` | No Overture heights |
| `--sin-cc0` | No ambientCG textures |
| `--sin-trafico` | No `traffic.json` |
| `--ac` | Also export the AC folder |
| `--nombre` | Track id (no spaces) |
| `--titulo` | Display name in game |
| `--salida` | Output folder |

**`openlaps.vivo` flags** (`vivo.py:1622-1656`)

| Flag | Meaning |
|---|---|
| `--centro` | Start point, the shared origin |
| `--puerto` | Server port (8790) |
| `--trabajadores` | Worker processes |
| `--radio` | Generate pieces within this distance (300 m) |
| `--radio-fondo` | Background prewarm radius (1200 m, or 600 with `--zona`) |
| `--pedazo-m` | Piece size (256 m) |
| `--margen` | Margin before cropping (64 m) |
| `--pad-osm` | Extra OSM margin (200 m) |
| `--tesela-osm` | OSM download tile (1024 m) |
| `--intervalo` | Scheduler interval (0.25 s) |
| `--r-carga`, `--r-soltar` | AC load and unload radii (430 m, 640 m) |
| `--t-foco` | How often the AC script reports position (0.5 s) |
| `--zona W,H` | Prewarm this whole area first |
| `--excluir X0,Y0,X1,Y1` | Already-baked box to skip |
| `--carpeta` | Pieces folder |
| `--nuevo` | Delete cached pieces for this centre |
| `--piloto-ac m`, `--piloto-kmh` | Autopilot test route length and speed |
| `--semilla-ac` | Build and install the AC seed track |
| `--nombre-ac` | Seed track folder name |
| `--ac-carpeta` | AC install folder |
| (other) | Unknown flags pass through to `openlaps` |

**`openlaps.google3d` flags** (`google3d.py:1575-1592`)

| Flag | Meaning |
|---|---|
| `pista` | AC track folder (positional) |
| `--glb` | The track's `.glb` |
| `--token` | Cesium ion token |
| `--radio` | Radius around the car (500 m) |
| `--error`, `--error-cerca` | Acceptable geometric error (far, and within 150 m) |
| `--max` | Max tiles at once |
| `--cache` | Converted tiles kept in memory |
| `--sin-burda` | Skip the coarse first pass |
| `--vivo` | Live-mode pieces folder instead of `--glb` |
| `--vivo-url` | Live server URL |
| `--puerto` | Port (8772) |
| `--instalar`, `--quitar` | Only install or remove the script |

## 8. Known limitations relevant to you

From `ROADMAP.md`:
- Large-area LOD and coarser distant terrain: idea only (`:247`).
- OSM lane and marking tags not read (`:219`).
- Roundabouts lack an island and banking (`:221`).
- No real sign placement from OSM `traffic_sign` (`:231`).
- Terrain shader too shiny; stretched texture on embankments (`:229`).
- Cliffs show a stretched texture (`:227`).
- Horizon uses Sentinel‑2 only (`:230`).
- Building variety limited (`:223-224`).
- Rally corridor and pace notes "not tested in game" (`:212`).
- Unpaved phase 1 "missing in-game testing" (`:161`).
- Terrain stays at 2–4 m with no adaptive mesh near roads (`:182-183`).
- Traffic: no protected-turn signals, live-mode traffic has no traffic lights, no `.aip` export for AssettoServer (`:232`, `:117`).

From `docs/assetto-corsa.md`: the workflow is Windows/PowerShell-centric; `tools/probar_ac.ps1` writes `race.ini` and launches `acs.exe` (`:29-38`).

From the code:
- 30 m DSM elevation on steep Koura roads is the main fidelity limit; use `--dem` if you can get better data.
- No custom orthophoto option.
- No AI or cameras in free roam.
- Boundary wall stripped in AC.
- Static exports always write the `.glb` as well.

## 9. Security skim

- **subprocess:** GUI only, with list arguments and no `shell=True`. Launches python, `taskkill`, `tasklist`, `cmd /c mklink /J` and `rmdir`, `explorer`, `acs.exe` (`gui/generador.py:153,178`; `gui/envivo.py:132,172`; `gui/google3d.py:60,80`; `gui/assetto.py:74,126,187,240`; `gui/app.py:401`). `tools/rendimiento_ac.py:30` runs `kn5_inspect.py`.
- **Not found:** `os.system`, `eval`/`exec`, pickle or marshal. `np.load` uses `allow_pickle=False` (`rasters.py:120`).
- **ctypes:** Windows APIs only (`procesos.py:31-37`, `gui/marco.py`, `gui/ajustes.py`, `gui/textos.py`, `gui/app.py:774`).
- **Deletes:** `shutil.rmtree` on live-pieces folders and in the GUI disk-space cleanup (`vivo.py:1662`, `gui/espacio.py:128,176,262`).
- **Writes outside cache and output:**
  - copies the seed track into `<AC>/content/tracks` (`vivo.py:1516-1524`);
  - hard-links or copies CSP's traffic tool files into the track (`trafico_vivo.py:128-138`);
  - GUI junctions into AC, edits `Documents/Assetto Corsa/cfg/race.ini` with a backup (`gui/assetto.py:207-218`), and writes `%APPDATA%`/`%LOCALAPPDATA%\OpenLaps`.
- **Network listeners:** all HTTP servers bind to 127.0.0.1 (`vivo.py:1617`, `google3d.py:1571`, `gui/servidor.py:151`, `gui/app.py:714-719`), but the vivo server sends `Access-Control-Allow-Origin: *`.
- **In-game scripts:** every exported track includes `vivo.lua`, which makes `web.get` calls to localhost (8789 and 8790), and enables `ALLOW_TRACK_SCRIPTS`.
- **Windows launcher:** downloads `uv` from GitHub and the WebView2 installer from Microsoft, then pip-installs pinned requirements (`OpenLaps.cs:107-124`, `447`, `493-498`).
- **External hosts:** no unexpected hosts beyond the table in section 3.

---

## Verdict

**Fork it, but for its components rather than its large-area capability.** The OSM road builder, junction and elevation smoothing, DEM and land-cover handling, pure‑Python KN5 and DDS writer, surfaces and CSP config are high quality and run on Linux with no Blender or ksEditor. 144 km² in one static KN5 is well beyond what it was built and tuned for (the GUI caps at 24 km², and the README gives timings for 800 m areas).

**Five biggest gaps for the Koura map**
1. **No large-area scaling.** Every 128 m terrain tile gets its own material and texture with no distance LOD (`terrain.py:441-454`, `mesh.py:19-25`), and everything is built in memory. You would need coarser LOD terrain away from roads and shared texture atlases, or a split into several KN5s.
2. **Live mode is not a shippable track.** It needs a local Python server, never frees physics, has no horizon, and has a view range of about 640 m.
3. **Imagery and elevation quality.** Only 10 m Sentinel‑2 (with Mexican seasons) and 30 m Copernicus DSM, with no hook for a custom orthophoto or XYZ source. The horizon ignores `--dem`.
4. **No Lebanon profile.** Koura auto-selects EU, so roofs come out pitched and olive trees become oaks. A real `lb` profile needs flat roofs, olive trees, narrower lanes, signage, and Mediterranean season logic in `vegetation.py` and `rasters.py`.
5. **Few buildings, and free-roam essentials missing.** Building heights are mostly random guesses (Microsoft footprints help only if they cover Lebanon well; I didn't verify that). There is no AI line, no cameras and no AC boundary wall in free roam. The 30 m DEM will also misplace steep switchback roads.

**Key files:** `<clone>/openlaps/openlaps/pipeline.py`, `.../openlaps/export_ac.py`, `.../openlaps/regions.py`, `.../openlaps/sources/rasters.py`, `.../openlaps/vivo.py`, `.../openlaps/google3d.py`, `.../ROADMAP.md`