Read-only code audit, 2026-11-23, of the commit pinned in REFERENCES.md. Nothing was executed.

I read the files and ran none of the project's code. In short, its photo path is a manual, validated mapping of a single photo onto a single wall. It does not automatically turn photos or video into textures, and it has no video support at all. What sets it apart from other generators is a lot of careful work on visual detail, plus a pure-Python KN5 writer.

## 1. Photos to facades and road textures

**`scripts/import_facade_photo.py`**
- **Input:** a building ID, a surface ID (one wall), a photo, and required licence and source text. Valid IDs come from `data/<track>/building_surfaces.json`, a catalogue of the official Hessen 3D building models (LoD2: roof shapes and walls, no fine detail).
- **Optional `--corners`:** you give 8 numbers, the four facade corners in pixels that you pick by hand. Pillow's `Image.Transform.PERSPECTIVE` straightens the photo to 2048×2048. Without corners it is only shrunk to at most 4096 px. There is no automatic straightening and no detection of the facade in the photo.
- **Output:** a JPG under `photos/` and an entry in `facade_overrides.json` holding `building_id`, `surface_id`, texture, licence, source and `flip_u`.

**Applying it** (`roadtoassetto/buildings.py:724` and `:955-968`)
- An overridden wall gets its own material. Its UVs simply stretch the photo across the wall's horizontal extent and full height, so a non-rectangular wall such as a gable distorts the image.
- If the override has a `projection` block, it calls `projected_photo_uv` instead.

**`roadtoassetto/photo_projection.py`** (107 lines, numpy only, worth borrowing)
- `fit_homography` maps at least 4 points measured in metres on the facade plane to pixel positions in the photo. It normalises the points first so large coordinates don't break the maths, and returns the error for each point.
- `projected_photo_uv` is strict. It checks that the facade frame axes are at right angles, that every wall vertex lies within 3 cm of the photo plane, that all points fall inside the image, and that the fit error is at most 3 px (configurable up to 10). It refuses any projection that crosses behind the camera.
- A comment notes that long triangles need extra subdivision for the perspective to look right.

**`scripts/register_local_facades_v06.py`**
- This is a review of one Wikimedia CC0 photo with 5 hand-read control points. It drew the errors onto the image, found that the gable apex didn't fit the lower corners (overhang, occlusion, an approximate model ridge), and set `registered: False`.
- It shows their attitude: a photo that doesn't fit is refused rather than forced. It also shows how fragile single-plane photo mapping is.

**`roadtoassetto/real_surfaces.py`** (roads and ground: no photo is projected onto them)
- Roads use the ambientCG CC0 scan Asphalt023S at its true 1.25 m tile size.
- Ground uses AC's `ksMultilayer` shader: a mask blends grass, gravel and asphalt scans. The mask comes from the aerial photo's colour and infrared channels (a vegetation index), smoothed in metres.
- Aerial photo brightness is deliberately kept out of the ground colour. A comment says an earlier version projected the aerial photo and made old shadows and cars look "melted across road embankments".

**`roadtoassetto/road_wear.py`**
- Patches, resealed cracks and manhole covers are all generated procedurally (seeded random numbers, maths-made cast-iron texture and normal map).
- They are clipped to the exported road triangles, raised at most 1.8 mm, and have no collision.
- Placement is illustrative, not taken from photos.

**AI provider** (`webapp/ai.py`, `roadtoassetto/ai_materials.py`)
- An optional OpenAI or OpenAI-compatible image endpoint generates exactly three tileable 1024² textures from fixed generic prompts: plaster, clay roof tiles and asphalt.
- No location or photos are sent.
- `normal_from_albedo` derives a rough bump map from each image's brightness.
- Plaster detail is multiplied over each building's existing blurred facade colour.
- Registered facade photos are left untouched. The AI is not used for recognition, straightening or filling in missing views.

## 2. Blender and the KN5

**Blender is used only for previews and an editable source file.**
- `scripts/blender_source.py` runs headless with `blender --background --python`. It rebuilds the materials from `scene.json`, including a node-graph copy of `ksMultilayer`, renders 1280×720 with Cycles (optional GPU), and saves a `.blend`.
- The version is Blender 4.5.9, pinned with a SHA256 checksum in the `Dockerfile`.
- Everything else is pure Python: geometry, textures and KN5 export, using numpy, scipy, shapely, pyproj, rasterio, Pillow and osmium. `scripts/build.py` says "without requiring Blender for the export".

**`roadtoassetto/kn5.py`** (133 lines, pure Python KN5 v6 writer)
- It embeds textures, writes materials with shader name, properties and texture slots, then mesh nodes and `AC_*` marker nodes.
- It computes normals, and tangents from the UV directions (the comment says a fixed tangent breaks normal maps on vertical facades).
- It rejects degenerate triangles and meshes with more than 65,535 vertices (16-bit indices).
- The layout follows an Apache-2.0 exporter by KinG-InFeT and RaduMC's format notes (see `THIRD_PARTY.md`).

**`roadtoassetto/inspect_kn5.py`** is a bounds-checked reader for KN5 v5 and v6. It is used after every export and also works on stock game files.

## 3. Buildings and slopes

**`roadtoassetto/buildings.py`**
- Buildings are not generated from footprints. They come from official Hessen LoD2 data fetched as GML, so roof types are whatever the survey contains (gable, hip and so on); there is no roof-type logic.
- Each polygon is triangulated with holes using shapely's constrained Delaunay.
- Roofs: far or flat roofs are textured from the aerial photo. Close roofs get CC0 tile scans aligned to the slope (`roof_materials`, around lines 926-943).
- Walls: storey heights are estimated from the low roof edges (`floor_layout`). Facades are split into plinth, ground, upper and plain gable bands.
- Close walls facing the street get real 3D detail: recessed windows from an atlas with frames and sills, shutters, doors with entrance steps cut to the terrain, eave fascias, gutters and downpipes.
- Building colour is decided per building (`architectural_palette`).
- Mesh parts are grouped by name and material and split before 64,000 vertices.

**Sitting on slopes**
- `building_bases.py` adds inferred basement or plinth walls between each building's lowest wall edges and the exported terrain. The source walls are never moved.
- `hillside.py` and `hillside_render.py` plan platforms, retaining walls, stairs and handrails between the house edge and the street or pavement grade.
- `hillside_banks.py` adds stepped retaining walls with gravel benches at steep street edges, with the last bench meeting the sampled ground.
- `ground_details.py` resamples the terrain more finely near the road, adds aprons in front of houses, and forces terrain triangles to meet the paving exactly.
- Every module carries a text note marking its output as inferred, not surveyed.

## 4. Road details and what carries over to another country

- **`road_markings.py`:** there is no automatic line generator. Markings come only from hand-reviewed observations in `marking_observations.json` (UTM coordinates, a confidence level, a position error of 2 m or less, lines no longer than 40 m), tied to the SHA256 hash of the source image. If that image changes, a re-review is required. Markings are clipped onto the actual road triangles. Reusable: the pattern of placing markings you traced yourself from your own imagery, and the clipping to road triangles.
- **`road_alignment.py`:** hand-measured cross-sections from aerial imagery (centre offset and width at each station) correct the OSM centreline, which is then smoothed. It is tied to an OSM hash and checks the route endpoints. Reusable for Lebanon: OSM geometry there is often rough, and you could measure offsets and widths from your dashcam footage or satellite images.
- **`junction_mouths.py`:** short visual stubs for side roads at OSM junction nodes, with their heights taken from the terrain. They are not drivable, and the main road's collision is never changed. Reusable.
- **`structures.py`:** OSM `bridge=*`/`tunnel=*` sections become concrete decks, parapets, piers, tunnel linings and portals with collision. Heights come from the portal and abutment ground plus the surface elevation model, because the bare-earth model is not a bridge deck. The approach is generic.
- **`german_streets.py`:** kerbs, paving styles and drains. The method is reusable; the parameters are German.
- **`long_track.py`:** about 1 km sections with a 50 m overlap and 160 m padding, all in one shared coordinate frame and loaded through `models.ini`. It checks that road vertices, UVs and normals match exactly at each seam and welds the terrain seams. This is well worth reusing.

## 5. Validation without the game

**No game needed**
- `scripts/validate.py` reads the KN5 back and checks the actual geometry.
- `verify_street_contacts.py` checks every overlap between paving and terrain for gaps or floating at their vertices.
- `verify_building_bases.py` is an independent geometry check that does not use the planner's code.
- `verify_visual_release.py` checks the ZIP contents.
- The `test_*.py` files are unittest suites. Many of them write a KN5, read it back and compare. `test_scenery_performance.py` compares checksums against an earlier generator version.

**With the game running** (both Windows-only)
- `physics_smoke.py` reads AC's `Local\acpmf_physics` shared memory three times and passes if all four wheel loads stay above 100 N, meaning the car sits on the ground at spawn.
- `record_load_test.py` scans AC's `log.txt` for "LOADING MODEL" and "STARTING PHYSICS ENGINE" and fails on unexpected `ERROR:` lines.

There is no driving test and no frame-rate test.

## 6. Size and performance (`docs/performance-0.15.md`, README)

- One heavily forested section of about 1 km with no buildings came to 185 meshes, about 2.95 M vertices, 2.44 M triangles and 113 textures, producing a **203 MB KN5**. The build took 83 s (down from 120 s in 0.14) on Windows with Python 3.12.
- The real hard limit is 65,535 vertices per mesh; they split at 63,000–64,000 vertices.
- Sections are capped at 2 km² (`webapp/server.py:98`).
- The documented container size is 8 GiB RAM and 4 cores.
- In a 64.8 km test, only 8 of 65 section models were checked before the run was stopped. A full export over 50 km and in-game drivability and frame rate are explicitly unverified (README lines 219-223).

## Worth borrowing for a Lebanon map with dashcam facades and road textures

1. **`photo_projection.py` as it stands:** homography fitting with point normalisation and strict refusals (on the wall plane, inside the image, error under 3 px). Feed it corners you pick in a dashcam frame. Neither repo has wall models like Hessen's LoD2, so you would supply the walls yourself (for example, extruded OSM footprints).
2. **The `import_facade_photo.py` flow:** four hand-picked corners, Pillow perspective straightening to 2048², stored as one override per wall with licence and source. It is simple and works for phone photos.
3. **The `real_surfaces.py` principle:** never bake aerial or dashcam brightness, shadows or cars into the road or ground colour. Use metric-scale tileable scans for colour, and use imagery only to decide which material goes where (the `ksMultilayer` mask). Dashcam road frames are better turned into tileable asphalt and concrete samples than projected onto the road.
4. **Pure-Python `kn5.py` and `inspect_kn5.py`:** correct tangents from UVs, strict checks, and no Blender in the export path. Blender then only produces previews.
5. **Hillside modules** (`building_bases.py`, `hillside*.py`, terrain-contact constraints in `ground_details.py`): North Lebanese villages are steep, and plinths, terraces and retaining walls matter more there than in Hessen.
6. **The hand-reviewed alignment and marking files** (`road_alignment.py`, `road_markings.py`): a good fit for correcting rough OSM roads with widths and markings you measure from your own footage.
7. **`long_track.py` sectioning with seam checks** and the `models.ini` multi-model layout, plus the 63k-vertex batching. For size, budget roughly 200 MB of KN5 per heavily vegetated km.
8. **`physics_smoke.py` and `record_load_test.py`:** cheap in-game smoke tests (Windows only), alongside headless read-back checks of the KN5.

One gap: nothing in the repo handles video. Extracting frames from the dashcam footage, knowing where each frame was taken, and matching walls between frames are all left to you.