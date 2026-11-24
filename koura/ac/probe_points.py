"""Sample probe positions along a surveyed route on the exported road mesh."""

import argparse
import json
from pathlib import Path
import sys

import numpy as np
from scipy.spatial import cKDTree

from paths import PROJECT

sys.path.insert(0, str(PROJECT / "koura"))
from openlaps.geo import LocalProjection
from ride import heights, road_tris


def sample(points, step, closed):
    local = np.asarray(points, dtype=float)
    if closed and not np.array_equal(local[0], local[-1]):
        local = np.vstack([local, local[0]])
    lengths = np.linalg.norm(np.diff(local, axis=0), axis=1)
    retained = np.r_[True, lengths > 0.001]
    local = local[retained]
    if len(local) < 2:
        raise ValueError("A probe path needs two distinct positions")
    chainage = np.r_[0.0, np.cumsum(np.linalg.norm(np.diff(local, axis=0), axis=1))]
    total = chainage[-1]
    stations = np.arange(0.0, total, step)
    if not closed:
        stations = np.r_[stations, total]
    forward, backward = stations + 0.8, stations - 0.8
    if closed:
        forward %= total
        backward %= total

    def interpolate(distances):
        return np.column_stack([np.interp(distances, chainage, coordinates) for coordinates in local.T])

    direction = interpolate(forward) - interpolate(backward)
    direction /= np.linalg.norm(direction, axis=1, keepdims=True)
    return stations, interpolate(stations), direction


def points_for_paths(glb, projection, paths, step, surface):
    triangles = road_tris(glb, f"1{surface}_" if surface else "calzada")
    if not len(triangles):
        raise ValueError(f"No {surface or 'road'} triangles in {glb}")
    index = cKDTree(triangles.mean(axis=1)[:, [0, 2]])
    results = []
    for name, geographic, closed in paths:
        coords = np.asarray(geographic, dtype=float)
        x, y = projection.to_local(coords[:, 1], coords[:, 0])
        stations, local, directions = sample(np.column_stack([x, -y]), step, closed)
        altitude = heights(triangles, index, 9.0, local[:, 0], local[:, 1])
        missing = np.flatnonzero(~np.isfinite(altitude))
        if len(missing):
            distances = ", ".join(f"{stations[i]:.1f}" for i in missing[:6])
            raise ValueError(f"{name}: {len(missing)} sample(s) miss {surface or 'road'} at metres {distances}")
        for point, direction, level, distance in zip(local, directions, altitude, stations):
            results.append({
                "name": f"{name} {distance:.1f} m",
                "pos": [float(point[0]), float(level + 1.0), float(point[1])],
                "dir": [float(direction[0]), 0.0, float(direction[1])],
            })
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("glb", type=Path)
    parser.add_argument("--routes", nargs="+", help="Named routes in zone.json")
    parser.add_argument("--kart-survey", type=Path, help="Use the surveyed Karting Mania centreline and KART surface")
    parser.add_argument("--every-m", type=float)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    if args.kart_survey and args.routes:
        parser.error("select either named routes or a Karting Mania survey")
    step = args.every_m if args.every_m is not None else (20.0 if args.kart_survey else 250.0)
    if not np.isfinite(step) or step < 1.0:
        parser.error("--every-m must be at least one metre")
    zone = json.loads((PROJECT / "handoff/inputs/zone.json").read_text())
    origin = zone["origin"]
    projection = LocalProjection.marco(origin["lat"], origin["lon"], (-100, -100, 100, 100))
    if args.kart_survey:
        kart = json.loads(args.kart_survey.read_text())
        paths = [("Karting Mania", kart["centreline"], kart["closed"])]
    else:
        names = args.routes or list(zone["routes"])
        paths = [(name, zone["routes"][name]["polyline"], zone["routes"][name]["closed"]) for name in names]
    points = points_for_paths(args.glb, projection, paths, step, "KART" if args.kart_survey else None)
    path = args.out or args.glb.with_suffix(".probe.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"points": points, "quit": True, "screenshots_every": 10}, indent=2) + "\n")
    print(f"{len(points)} points written to {path}")


if __name__ == "__main__":
    main()
