"""Export a non-colliding verge finish on an already built Karting Mania track."""

import argparse
import json
from pathlib import Path
import sys

import numpy as np
from PIL import Image
import shapely

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "openlaps"))

from koura.kart_geometry import read_layout
from koura.ride import road_tris
from openlaps.export_ac import write_kn5
from openlaps.geo import LocalProjection
from openlaps.koura_scenery import _face_up
from openlaps.mesh import Scene
from openlaps.roads import iter_polys, triangulate_polygon
from openlaps.textures import edge_fade


def make_finish(glb, survey_path, output):
    zone = json.loads((ROOT / "handoff/inputs/zone.json").read_text())
    origin = zone["origin"]
    projection = LocalProjection.marco(origin["lat"], origin["lon"], (-1, -1, 1, 1))
    _, survey = read_layout(survey_path, projection)
    outline = survey["outline"]
    edge_inset, inner_inset = 0.025, 0.50
    strip = outline.buffer(-edge_inset).difference(outline.buffer(-inner_inset))
    apron = survey["poly"].difference(outline)
    if not apron.is_empty:
        strip = strip.difference(apron.buffer(inner_inset))

    # Conform the finish to each source face. This also follows short grade
    # changes without interpolating across a break in the underlying road.
    triangles = road_tris(glb, "1KART_calzada_kart_asphalt_")[:, :, (0, 2, 1)]
    triangles[:, :, 1] *= -1
    footprints = shapely.polygons(triangles[:, :, :2])
    candidates = shapely.intersects(strip, footprints) & (shapely.area(footprints) > 0)
    positions, coordinates, faces = [], [], []
    first = 0
    covered_area = 0.0
    for triangle, clipped in zip(triangles[candidates], shapely.intersection(footprints[candidates], strip)):
        for patch in iter_polys(clipped):
            if patch.area <= 1e-8:
                continue
            xy, patch_faces = triangulate_polygon(patch, 0.5)
            base = triangle[0]
            slope = np.linalg.solve(triangle[1:, :2] - base[:2], triangle[1:, 2] - base[2])
            z = base[2] + (xy - base[:2]) @ slope + 0.018
            dist = shapely.distance(shapely.points(xy), outline.boundary)
            blend = np.clip((dist - edge_inset) / (inner_inset - edge_inset), 0.004, 0.996)
            positions.append(np.column_stack((xy, z)))
            coordinates.append(np.column_stack((blend, (xy[:, 0] + xy[:, 1]) / 3)))
            faces.append(_face_up(xy, patch_faces) + first)
            first += len(xy)
            covered_area += patch.area

    if not faces or not np.isclose(covered_area, strip.area, rtol=0.001, atol=0.02):
        raise ValueError(f"Built asphalt covers {covered_area:.2f} of {strip.area:.2f} m² of the surveyed edge finish")

    scene = Scene()
    texture = np.array(edge_fade(128, (106, 99, 89)))
    texture[:, :, 3] = np.rint(texture[:, :, 3] * 0.72)
    scene.images["kart_edge_finish.png"] = Image.fromarray(texture)
    scene.material("kart_edge_finish", "kart_edge_finish.png", kind="blend", shadows=False, specular=0.01)
    scene.add("bordes", "kart_edge_finish", np.vstack(positions), np.vstack(coordinates), np.vstack(faces))
    write_kn5(scene, output)
    return {"area_m2": covered_area, "vertices": first, "colliding_meshes": 0, "width_m": inner_inset - edge_inset}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("built_glb", type=Path)
    parser.add_argument("kart_survey", type=Path)
    parser.add_argument("output_kn5", type=Path)
    args = parser.parse_args()
    report = make_finish(args.built_glb, args.kart_survey, args.output_kn5)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
