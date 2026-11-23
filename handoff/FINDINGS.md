# Findings

Everything here was measured or read on 2026-11-23 unless marked **unverified**.

## The area

Village centres from OpenStreetMap (lat, lon):

| Village | Lat | Lon |
|---|---|---|
| Btouratij | 34.3616 | 35.8390 |
| Nakhleh | 34.3653 | 35.8271 |
| Bechmizzine | 34.3200 | 35.7961 |
| Amioun | 34.3001 | 35.8167 |
| Kousba | 34.2984 | 35.8503 |
| Btorram | 34.3326 | 35.8100 |
| Kfar Aaqqa | 34.3037 | 35.8362 |
| Bsarma | 34.3342 | 35.8412 |
| Kfar Hazir | 34.3121 | 35.7732 |

**These tiers were the first sketch. The stages now used are S1, S2, S3 in `PLAN.md` and `inputs/zone.json`.** S1 is the T1 box; S3 is the T2 box widened west.

The loop, in the owner's order (Btouratij, Aaba, Bishmizzine, Kfar Hazir, Amioun, Kousba, Bsarma, Aaba, Btouratij), routed on main roads: 25.6 km (15.1 km primary, 9.3 km secondary, 1.0 km tertiary). The shortcut from near Bishmizzine to Amioun is the direct secondary road, 4.7 km, of which 3.0 km is not already on the loop. Online listings place Clutch N' Carb on the Amioun to Bechmezzine main road, which matches. Map in `evidence/loop_on_map.png`, geometry in `evidence/loop.json` and `inputs/zone.json`. Owner-confirmed on the map, 2026-11-23: the loop, the shortcut, the stage 1 box (34.352 to 34.381 N, 35.818 to 35.852 E, 10.0 km²) and two local loops inside it: Btouratij, up the main road to the junction at the start of Ras Masqa (34.3757, 35.8463), west up to Nakhle and back down to Btouratij (6.0 km), and a loop inside Nakhle (2.6 km). Added at the owner's request and not yet checked by them: the main road from Kousba towards Tourza, 5.4 km (1.0 km secondary, 4.4 km primary), ending at the turn-off that climbs to Tourza (34.28315, 35.89348). Karting Mania kart track: not in OpenStreetMap; found on aerial imagery at 34.3261, 35.8525 (`evidence/karting_mania_aerial.png`), reached by a 1.4 km road off Tripoli Street and lying just west of a straight north-south road that the owner calls the Dabbousi Farms road (3.4 km from the track to the loop at Aaba). Kfar Hazir (34.3121, 35.7732) and Aaba (34.3488, 35.8343) are added to the village list; the S3 box was widened west to 35.762 to include Kfar Hazir.

Proposed tiers (south, west, north, east). Road lengths count every OSM way that touches the box, so they overstate a little.

| Tier | Box | Size | All roads | Main roads |
|---|---|---|---|---|
| T0 Btouratij | 34.357, 35.8335, 34.366, 35.8445 | 1.0 x 1.0 km | 8 km built in trial | |
| T1 Btouratij + Nakhle (as first measured; stage 1 is now this box extended north to 34.381 and east to 35.852) | 34.352, 35.818, 34.374, 35.850 | 2.9 x 2.4 km | about 70 km | about 27 km |
| T2 named villages | 34.288, 35.785, 34.376, 35.862 | 7.1 x 9.8 km | about 436 km | about 206 km |
| T3 wider Koura | 34.275, 35.755, 34.395, 35.875 | 11.0 x 13.3 km | about 830 km | about 396 km |

"Main roads" means motorway to unclassified. The rest is mostly `residential` (380 km in T3).

Terrain in the trial square runs from 176 to 289 m above sea level. The whole of T3 lies in UTM zone 36N (EPSG:32636).

## Source data, per layer

**Roads (OpenStreetMap).** T3 has 2,464 road ways. Tagging is thin: 261 have `surface`, 140 `oneway`, 48 `name`, 43 `lanes`, 16 `bridge`, 7 `maxspeed`, 2 `width`. Widths and lane counts must therefore come from road class defaults, aerial imagery or dashcam. Overlaid on 0.5 m aerial imagery in Amioun, centrelines sit on the roads with offsets of roughly 0 to 5 m (`evidence/amioun_esri_z18_osm_overlay.jpg`).

**Buildings.** OSM has only 1,334 footprints in T3, 8 with a floor count, none with a height. The Overture buildings dataset has 17,828 for the same box (16,494 from Microsoft's machine-learned footprints plus the OSM ones), again with no heights. openlaps already merges Microsoft footprints with OSM. Heights have to be estimated.

**Elevation.** No open lidar or national high-resolution model for Lebanon was found. Copernicus GLO-30 is available without login (tile `Copernicus_DSM_COG_10_N34_00_E035_00_DEM` on the public AWS bucket returned HTTP 200). It is a 30 m **surface** model: it includes trees and roofs. openlaps strips those and smooths road profiles, but camber, kerbs and bumps cannot come from it. FABDEM (a bare-earth version of the same data, non-commercial licence) is worth trying through openlaps' `--dem` flag. **Unverified:** that it downloads cleanly for this tile.

**Aerial imagery.** Esri World Imagery serves real detail to zoom 18 here (0.49 m per pixel at this latitude) and its metadata dates the capture 2024-01-02. Zoom 19 returns tiles; zoom 20 returned a 2.5 KB tile, probably a placeholder. Fine for personal use, not redistributable. openlaps would otherwise fall back to Sentinel-2 at 10 m, which is what the blurry trial image shows (`evidence/btouratij_poc_cenital.jpg`).

**Land cover and trees.** ESA WorldCover 10 m and the Meta/WRI 1 m canopy-height map both cover the area and openlaps already uses both. The trial placed 1,091 trees and shrubs from real canopy heights.

**Online video.** Driving and drone videos of Btouratij exist on YouTube, plus 4K bicycle rides through nearby roads. Listed in `DASHCAM.md`. Not yet watched.

**Street-level photos.** **Unknown.** Mapillary needs an access token (the anonymous request returned 403) and the KartaView query returned nothing usable. Check both with a token before assuming there is none. openlaps has `tools/referencias.py` for Panoramax, Mapillary and Wikimedia Commons.

**Google Photorealistic 3D Tiles.** openlaps can stream them into the game at runtime through a free Cesium ion token. **Unverified** whether Koura has coverage; rural Lebanon probably does not. Treat as an optional experiment the owner can try, not a planned source.

## This machine

- Fedora 45, Ryzen 7 7800X3D, 30 GB RAM, Radeon RX 6800-class GPU, 475 GB free on `/home`.
- System Python is 3.15, which is too new for the generator's dependencies. Python 3.12 through `uv` works (this is how the trial ran).
- Blender and GDAL command-line tools are not installed and are not needed.
- Assetto Corsa: `/mnt/Linux_HDD/SteamLibrary/steamapps/common/assettocorsa`
  - Custom Shaders Patch 0.2.11, build 3465
  - Proton prefix: `/mnt/Linux_HDD/SteamLibrary/steamapps/compatdata/244210/pfx`, running GE-Proton9-20
  - Game documents (config, logs): `<prefix>/drive_c/users/steamuser/Documents/Assetto Corsa/` with `cfg/` and `logs/`
  - Tracks go in `<AC>/content/tracks/<track_id>/`
  - `sdk/editor/ksEditor.exe` exists but is not needed
- Content Manager is in use: its data folder is `<prefix>/drive_c/users/steamuser/AppData/Local/AcTools Content Manager/`, `cfg/race.ini` carries its `__CM_` keys, and the game folder has both `AssettoCorsa.exe` and `AssettoCorsa_original.exe`, which suggests it replaced the launcher. **Unverified:** that starting the game from Steam opens it.
- Lua apps live in `<AC>/apps/lua/`. `steam`, `protontricks-launch`, `gamescope`, `ffmpeg` and `exiftool` are installed. The desktop session is KDE on Wayland.
- Last game session ended with `CLEAN EXIT` in `logs/log.txt` on 2026-11-15, so the install works.

## The trial build

Command (Python 3.12 environment with openlaps installed with `pip install -e`):

```
openlaps --centro 34.3616,35.8390 --tam 1000 --nombre btouratij_poc --titulo "Btouratij POC" --ac --salida <out>
```

Result (`evidence/run.log`, `evidence/btouratij_poc.json`):

- 109 s, including first-time downloads
- 8.2 km of road, 40 junctions (the log also reports "30.3 km de asfalto, 0.9 km de terracería" at an earlier stage; the difference from 8.2 km is unexplained)
- 211 buildings (7 OSM, 204 Microsoft), 150 street lamps, 24 signs
- 680 meshes, 293 textures (50 MB), 76 MB track folder
- Terrain: 2 m grid, 64 tiles of 128 m, ground texture at 0.5 m per pixel

Problems visible without loading the game:

- It auto-selected the `eu` style, so roofs are pitched and no olive trees are placed. Koura has flat concrete roofs mixed with red tile, and olive groves.
- Ground texture comes from 10 m satellite data.
- The description text is in Spanish.
- Free-roam mode writes no AI line and no cameras, and the boundary wall is removed in the game export, so a car can drive off the map edge.

## Defects found by reading the openlaps code

Full detail with quoted code is in `specs/openlaps-change-specs.md`.

1. The game export deletes every collider in the `col` group to remove the boundary wall. That also removes collision from lamp posts, sign posts, tree trunks and pylon bases.
2. The profile field `lane_mult` only moves road markings. It does not narrow roads.
3. Vegetation never receives OSM land use, so orchards do not get olive trees.
4. OSM way ids and building ids are dropped before roads and buildings are built, so nothing can be overridden by id today.
5. There is no option to pin the map origin from the command line. It can be pinned by calling `pipeline.run(proj=...)`.
6. Separately built pieces do not agree in road height at their seams.
7. Imagery errors are swallowed and the build silently falls back to 10 m satellite colour.
8. Above 24 km² the corridor code turns imagery and canopy data off.
9. Terrain has no draw distance, and each 128 m terrain tile has its own material and texture.

## Memory limit found while building the preview (2026-11-23)

`roads.armonizar_calzadas` rasterises every road surface onto one grid over the whole build rectangle at 0.5 m cells and keeps about ten full-size arrays. For the 12.3 x 11.8 km stage 2 rectangle that is 23,707 x 22,079 cells, 3.9 GB per array, far more than this machine's 30 GB, and the first preview attempt was killed for it. With 1.5 m cells the same build peaked under 21 GB and finished in 21 minutes. For the real stage 2 build, work package 6 must make this step work in blocks (for example 1 km squares with a 10 m overlap) at 0.5 m, or limit the grid to the zone polygon's pieces. Always run builds with a memory cap (`ulimit -v 21000000`) so a failure is a clean error with a traceback and never freezes the desktop.
