"""Prepare and verify distant terrain collision and overhead views in Assetto Corsa."""

import argparse
import json
import re
import sys
from pathlib import Path

import numpy as np
from scipy.spatial import cKDTree

from paths import PROJECT

sys.path.insert(0, str(PROJECT / "koura"))
sys.path.insert(0, str(PROJECT / "openlaps" / "tools"))
from render import load_glb
from ride import heights


def prepare(glb):
    meshes, _, markers, _ = load_glb(glb)
    triangles = np.concatenate([
        mesh["pos"][mesh["idx"]] for mesh in meshes
        if re.match(r"^1[A-Z]+_terreno_", mesh["name"])
    ])
    centers = triangles.mean(axis=1)[:, [0, 2]]
    index = cKDTree(centers)
    road = markers["AC_START_0"]
    points = [
        {"name": name, "pos": (np.asarray(node["translation"]) + [0, 1, 0]).tolist(),
         "dir": node["extras"]["forward"]}
        for name, node in sorted(markers.items()) if re.fullmatch(r"AC_START_\d+", name)
    ]
    for offset in (-300, 300):
        start = np.asarray(road["translation"])
        eye = start + [offset, 300, 0]
        distance = np.linalg.norm(centers - eye[[0, 2]], axis=1)
        far = centers[(distance > 1680) & (distance < 2400)]
        if not len(far):
            raise ValueError("No terrain targets outside the 1500 m draw distance")
        # Locate uneven but near enough targets in distinct parts of the distant terrain.
        ordered = np.unique(np.round(far / 80) * 80, axis=0)
        spread = ordered[np.linspace(0, len(ordered) - 1, min(len(ordered), 36)).astype(int)]
        target_x, target_z = far.mean(axis=0)
        near = centers[np.argmin(distance)].reshape(1, 2)
        xy = np.vstack([near, spread])
        levels = heights(triangles, index, 10, xy[:, 0], xy[:, 1])
        rays = [
            {"name": "near control" if i == 0 else f"distant terrain {i}",
             "pos": [float(x), float(y + 15), float(z)], "expected_distance_m": 15}
            for i, ((x, z), y) in enumerate(zip(xy, levels)) if np.isfinite(y)
        ]
        if len(rays) < 4:
            raise ValueError("Not enough reachable terrain targets")
        points.append({
            "name": f"300 m overview {offset:+}", "pos": (start + [0, 1, 0]).tolist(),
            "dir": road["extras"]["forward"], "terrain_rays": rays,
            "camera": {"pos": eye.tolist(), "target": [target_x, start[1], target_z], "fov": 49},
        })
    return {"points": points, "quit": True, "screenshots_every": 1}


def validate(plan, results):
    views = []
    for point, row in zip(plan["points"], results["results"], strict=True):
        if "camera" not in point:
            continue
        offset = float(np.linalg.norm(np.asarray(point["camera"]["pos"]) - row["camera_position"]))
        rays = row["terrain_rays"]
        good = [
            ray for ray in rays if ray["camera_distance_m"] > 1500
            and abs(ray["distance_m"] - ray["expected_distance_m"]) <= 0.25
        ]
        views.append({"name": point["name"], "camera_error_m": offset, "hits_beyond_1500_m": len(good),
                      "count": len(rays), "rays": rays, "fps": row["fps"],
                      "pass": bool(row["camera_owned"] and offset < 1 and len(good) >= 3
                                   and len(rays) == len(point["terrain_rays"]))})
    return {"pass": bool(views) and all(view["pass"] for view in views), "views": views}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="GLB to prepare points, or results.json to check")
    parser.add_argument("output", type=Path)
    parser.add_argument("--plan", type=Path, help="Previously generated plan for checking results")
    args = parser.parse_args()
    if args.plan:
        report = validate(json.loads(args.plan.read_text()), json.loads(args.source.read_text()))
    else:
        report = prepare(args.source)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    raise SystemExit(0 if report.get("pass", True) else 1)


if __name__ == "__main__":
    main()
