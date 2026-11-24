"""Add the Btouratij lattice lights along the built Koura road network."""

import argparse
from collections import Counter, defaultdict
import io
import json
from pathlib import Path
import re
import struct
import sys

import numpy as np
from PIL import Image
from scipy.spatial import cKDTree
from scipy.spatial.transform import Rotation
import shapely

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "openlaps")]

from koura.ride import heights, road_tris
from openlaps.export_ac import ext_config, write_kn5
from openlaps.geo import LocalProjection
from openlaps.koura_scenery import _shape
from openlaps.mesh import Scene, vertex_normals
from street_light_placement import plan_street_lights


REFERENCE_ID = "btouratij-mosque-b2-lattice-lamp"


def read_glb(path):
    data = path.read_bytes()
    length = struct.unpack_from("<I", data, 12)[0]
    return json.loads(data[20:20 + length]), memoryview(data)[28 + length:]


def buffer_view(doc, binary, index):
    view = doc["bufferViews"][index]
    start = view.get("byteOffset", 0)
    return binary[start:start + view["byteLength"]]


def asset_materials(scene, doc, binary):
    materials = {mat["name"]: mat for mat in doc["materials"]}

    def image(texture_index, name):
        texture = doc["textures"][texture_index]
        embedded = doc["images"][texture["source"]]
        data = buffer_view(doc, binary, embedded["bufferView"])
        scene.images[name] = Image.open(io.BytesIO(data)).copy()
        return name

    for name, settings in (
        ("muro", {}),
        ("lampara", {"ambient": 0.6, "diffuse": 0.5, "specular": 0.2}),
    ):
        mat = materials[name]
        diffuse = image(mat["pbrMetallicRoughness"]["baseColorTexture"]["index"], name + ".png")
        if "normalTexture" in mat:
            settings["normal"] = image(mat["normalTexture"]["index"], name + "_normal.png")
        scene.material(name, diffuse, **settings)


def footprints(doc, binary):
    """Read projected roadway, roof, wall-footprint and water triangles."""
    def array(accessor):
        row = doc["accessors"][accessor]
        data = buffer_view(doc, binary, row["bufferView"])
        dtype = {5126: "<f4", 5123: "<u2", 5125: "<u4"}[row["componentType"]]
        columns = 3 if row["type"] == "VEC3" else 1
        return np.frombuffer(data, dtype, row["count"] * columns, row.get("byteOffset", 0))

    triangles = []
    for node in doc["nodes"]:
        name = node.get("name", "")
        if "mesh" not in node or not (
            name.startswith(("edificios_", "1WATER_", "1WALL_barreras_"))
            or (name.startswith("1") and "_calzada_" in name)
        ):
            continue
        primitive = doc["meshes"][node["mesh"]]["primitives"][0]
        position = array(primitive["attributes"]["POSITION"]).reshape(-1, 3)[:, (0, 2)].copy()
        position[:, 1] *= -1
        faces = array(primitive["indices"]).reshape(-1, 3)
        parts = shapely.polygons(position[faces])
        triangles.append(parts[shapely.area(parts) > 0.0001])
    return shapely.STRtree(np.concatenate(triangles))


def install_layer(site, output):
    terrain_path = site / "koura_combined.glb"
    survey_path = site / "authoring-set/s1_details.json"
    original_track = site / "assetto_corsa/koura_combined"
    out_track = output / "assetto_corsa/koura_combined"
    authoring = json.loads(survey_path.read_text())["street_lamps"]
    fixture = next(lamp for lamp in authoring if lamp["id"] == REFERENCE_ID)
    zone = json.loads((ROOT / "handoff/inputs/zone.json").read_text())
    origin = zone["origin"]
    projection = LocalProjection.marco(origin["lat"], origin["lon"], (-1, -1, 1, 1))
    existing = [projection.to_local(lamp["lon"], lamp["lat"]) for lamp in authoring]
    scene = Scene()
    scene.group_lod["mobiliario"] = 245
    doc, binary = read_glb(terrain_path)
    asset_materials(scene, doc, binary)
    obstacles = footprints(doc, binary)
    del doc, binary
    placements = plan_street_lights(site / "koura_combined.roads.json", existing, obstacle_tree=obstacles)
    del obstacles
    if not placements:
        raise ValueError("No clear roadside lamp sites")
    xy = np.array([(lamp.x, lamp.y) for lamp in placements])
    terrain = road_tris(terrain_path, "_terreno_")
    horizontal = terrain[:, :, (0, 2)]
    centres = horizontal.mean(1)
    tree = cKDTree(centres)
    maximum = np.linalg.norm(horizontal - centres[:, None], axis=2).max() + 0.1
    levels = heights(terrain, tree, maximum, xy[:, 0], -xy[:, 1])
    del terrain, horizontal, centres, tree

    size = np.array(fixture["size_m"])
    parts = defaultdict(list)
    for material, pos, uv, faces in _shape(scene, fixture["shape"], size):
        parts[material].append((pos, uv, faces))
    templates = {}
    for material, source in parts.items():
        pos = np.concatenate([part[0] for part in source])
        uv = np.concatenate([part[1] for part in source])
        offsets = np.cumsum([0, *[len(part[0]) for part in source[:-1]]])
        faces = np.concatenate([part[2] + start for part, start in zip(source, offsets)])
        templates[material] = (pos, uv, faces, vertex_normals(pos, faces))

    lights = fixture["lights"]
    coverage = Counter()
    for lamp, z in zip(placements, levels):
        if not np.isfinite(z):
            continue
        xyz = np.array([lamp.x, lamp.y, z])
        rotation = Rotation.from_euler("z", -lamp.heading_deg, degrees=True)
        for material, (pos, uv, faces, normals) in templates.items():
            scene.add("mobiliario", material, rotation.apply(pos) + xyz, uv, faces,
                      normals=rotation.apply(normals))
        for light in lights:
            offset = rotation.apply(np.array(light["offset"]) * size)
            rgb = tuple((np.array(light["rgb"]) / 255).round(5))
            scene.lights.append((xyz + offset, (0, 0, -1), rgb, light["intensity"], light["range_m"]))
        coverage[lamp.road_class] += 1
    if not coverage:
        raise ValueError("No streetlight sites are on the built terrain")

    filename = "koura_street_lights.kn5"
    write_kn5(scene, out_track / filename)
    models = original_track / "models.ini"
    content = models.read_text().rstrip()
    index = 1 + max(map(int, re.findall(r"^\[MODEL_(\d+)\]", content, flags=re.M)))
    (out_track / "models.ini").write_text(
        f"{content}\n\n[MODEL_{index}]\nFILE={filename}\nPOSITION=0,0,0\nROTATION=0,0,0\n",
        newline="\r\n",
    )
    ext = out_track / "extension/ext_config.ini"
    original = (original_track / "extension/ext_config.ini").read_text().rstrip()
    start = 1 + max(map(int, re.findall(r"^\[LIGHT_(\d+)\]", original, flags=re.M)))
    sections = ext_config(scene, origin["lat"], origin["lon"]).split("[LIGHT_0]", 1)[1]
    sections = re.sub(r"\[LIGHT_(\d+)\]", lambda m: f"[LIGHT_{int(m[1])+start}]",
                      "[LIGHT_0]" + sections)
    # Original beam, color and range. Limit how far the repeated units draw
    # together on a long road with distant views.
    sections = sections.replace("FADE_AT=600", "FADE_AT=140").replace("FADE_SMOOTH=200", "FADE_SMOOTH=40")
    ext.write_text(original + "\n\n" + sections, newline="\r\n")
    return {
        "fixture": REFERENCE_ID,
        "street_lamps": sum(coverage.values()),
        "by_road_class": dict(coverage),
        "skipped_without_terrain": int(np.isnan(levels).sum()),
        "emitter_count": len(scene.lights),
        "original_emitters": start,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("combined_build", type=Path)
    parser.add_argument("staged_build", type=Path, help="Private copy of combined track folder")
    args = parser.parse_args()
    if args.combined_build.resolve() == args.staged_build.resolve():
        parser.error("Provide a separate staged directory")
    print(json.dumps(install_layer(args.combined_build, args.staged_build), indent=2))


if __name__ == "__main__":
    main()
