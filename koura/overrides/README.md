# Local map overrides

The build reads these five JSON files by default. Use `koura/build.py S1 --overrides DIR` to select a separate surveyed set. Keep photo textures and local models in the ignored `koura/overrides/private/` directory, with paths relative to the corresponding JSON file. Save source links and frame times beside the entries. Coordinates are ordered latitude, longitude, and any height in these files is relative to the ground or road.

- `roads.json` merges OSM tags from objects keyed by way ID. `add` takes an ID, tags and a lat/lon node list whose ends snap within 3 m. `remove` lists IDs. `move` maps IDs to new node lists while preserving shared junctions. The road sidecar records the resulting way IDs.
- `buildings.json` supports `by_osm_id` (prefix ways with `w` and relations with `r`), `by_point`, `add`, and `remove`. Building detail fields include `levels`, `roof`, `colour`, `roof_colour`, and `facades`. A facade has a zero-based exterior `edge`, an `image`, and a `fit` of `stretch` or `tile`. Added buildings use their authored ring order. Existing footprints use the exterior counterclockwise order. A `sign` can reference a shopfront image or provide `text` for a fascia.
- `walls.json` entries have an `id`, a lat/lon `line`, `height_m`, `material`, optional `thickness_m`, and `collider`. Give each gate gap a `start_m` and `end_m` measured along the line.
- `landmarks.json` entries have an `id`, location, `heading_deg`, `size_m`, `collider`, and either a local model or a shape. Model JSON contains vertices in footprint fractions and zero-based triangular faces, with vertical coordinates relative to the placement base. Shapes can combine boxes, cylinders, cones, and ellipsoids.
- `junctions.json` accepts surveyed roundabouts and `island_junction` outlines. Supply lat/lon rings for irregular islands and splitters. Set the sloped kerb to at most 8 cm. Islands and their monuments sample the finished asphalt.

Include `source` and `state` for each surveyed wall, landmark or junction. An entry marked `todo` is skipped. The build logs matches, rejected records and the amount of wall built.
