"""Check the shared detailed/background edge in an exported Koura GLB."""

import argparse
import json
import re
import struct
from pathlib import Path

import numpy as np
import shapely
from scipy.spatial import cKDTree


SAMPLE_SPACING_M = 5.0
MAX_STEP_M = 0.10
# The seam is stored in double precision and GLB vertex positions in float32.
EDGE_TOLERANCE_M = 0.002
GROUND_NAME = re.compile(r"^\d+[A-Z0-9]+_(terreno|suelo_fondo)_")
COMPONENT = {5123: "<u2", 5125: "<u4", 5126: "<f4"}


def line_parts(geometry):
    if geometry.geom_type == "LineString" and geometry.length > 0:
        yield geometry
    elif geometry.geom_type in {"MultiLineString", "GeometryCollection"}:
        for part in geometry.geoms:
            yield from line_parts(part)


def seam_samples(geometry):
    lines = list(line_parts(geometry))
    if not lines:
        raise ValueError("The coverage has no shared line to check")
    merged = shapely.line_merge(shapely.MultiLineString(lines))
    samples = []
    for line in line_parts(merged):
        count = int(np.ceil(line.length / SAMPLE_SPACING_M))
        sites = shapely.line_interpolate_point(line, np.linspace(0, line.length, count + 1))
        samples.append(shapely.get_coordinates(sites))
    return np.unique(np.concatenate(samples), axis=0), merged.length


def read_accessor(file, metadata, binary, key):
    accessor = metadata["accessors"][key]
    view = metadata["bufferViews"][accessor["bufferView"]]
    dtype = np.dtype(COMPONENT[accessor["componentType"]])
    width = {"SCALAR": 1, "VEC3": 3}[accessor["type"]]
    offset = binary + view.get("byteOffset", 0) + accessor.get("byteOffset", 0)
    file.seek(offset)
    return np.frombuffer(file.read(accessor["count"] * width * dtype.itemsize), dtype=dtype)


def sample_mesh(triangles, sites):
    """Return the highest physical triangle at each XY, within GLB rounding error."""
    result = np.full(len(sites), np.nan)
    xy = triangles[:, :, :2]
    a, b, c = xy.transpose(1, 0, 2)
    ab, ac, bc = b - a, c - a, c - b
    area = ab[:, 0] * ac[:, 1] - ab[:, 1] * ac[:, 0]
    valid = np.abs(area) > 1e-9
    if not valid.any():
        return result
    xy, triangles, a, ab, ac, bc, area = (array[valid] for array in (xy, triangles, a, ab, ac, bc, area))
    centroids = xy.mean(axis=1)
    reach = np.linalg.norm(xy - centroids[:, None], axis=2).max() + EDGE_TOLERANCE_M
    tolerance = EDGE_TOLERANCE_M / np.abs(area)
    u_tol = np.linalg.norm(ac, axis=1) * tolerance
    v_tol = np.linalg.norm(ab, axis=1) * tolerance
    sum_tol = np.linalg.norm(bc, axis=1) * tolerance
    candidates = cKDTree(centroids).query_ball_point(sites, reach)
    for i, found in enumerate(candidates):
        if not found:
            continue
        p = sites[i] - a[found]
        u = (p[:, 0] * ac[found, 1] - p[:, 1] * ac[found, 0]) / area[found]
        v = (ab[found, 0] * p[:, 1] - ab[found, 1] * p[:, 0]) / area[found]
        inside = (u >= -u_tol[found]) & (v >= -v_tol[found]) & (u + v <= 1 + sum_tol[found])
        if inside.any():
            z = triangles[np.asarray(found)[inside], :, 2]
            result[i] = (z[:, 0] + u[inside] * (z[:, 1] - z[:, 0]) + v[inside] * (z[:, 2] - z[:, 0])).max()
    return result


def ground_heights(glb, sites):
    bounds_tree = shapely.STRtree(shapely.points(sites))
    heights = {kind: np.full(len(sites), np.nan) for kind in ("terreno", "suelo_fondo")}
    with glb.open("rb") as file:
        head, version, _ = struct.unpack("<III", file.read(12))
        size, chunk = struct.unpack("<II", file.read(8))
        if head != 0x46546C67 or version != 2 or chunk != 0x4E4F534A:
            raise ValueError(f"{glb} is not a glTF 2 binary file")
        metadata = json.loads(file.read(size))
        _, chunk = struct.unpack("<II", file.read(8))
        if chunk != 0x004E4942:
            raise ValueError(f"{glb} has no binary mesh buffer")
        binary = file.tell()
        for node in metadata["nodes"]:
            match = GROUND_NAME.match(node.get("name", ""))
            if match is None or "mesh" not in node:
                continue
            height = heights[match[1]]
            for prim in metadata["meshes"][node["mesh"]]["primitives"]:
                position = prim["attributes"]["POSITION"]
                accessor = metadata["accessors"][position]
                xmin, _, zmin = accessor["min"]
                xmax, _, zmax = accessor["max"]
                t = EDGE_TOLERANCE_M
                bounds = shapely.box(xmin - t, -zmax - t, xmax + t, -zmin + t)
                nearby = bounds_tree.query(bounds)
                if not len(nearby):
                    continue
                xyz = read_accessor(file, metadata, binary, position).reshape(-1, 3)
                faces = read_accessor(file, metadata, binary, prim["indices"]).reshape(-1, 3)
                local = np.column_stack([xyz[:, 0], -xyz[:, 2], xyz[:, 1]]).astype(np.float64)
                measured = sample_mesh(local[faces], sites[nearby])
                height[nearby] = np.fmax(height[nearby], measured)
    return heights["terreno"], heights["suelo_fondo"]


def check_seam(glb, seam):
    sites, length = seam_samples(seam)
    detailed, background = ground_heights(glb, sites)
    detail_gap = ~np.isfinite(detailed)
    background_gap = ~np.isfinite(background)
    gap = detail_gap | background_gap
    delta = np.abs(detailed - background)
    stepped = delta > MAX_STEP_M
    failures = [
        {"xy_m": sites[i].tolist(), "detailed_gap": bool(detail_gap[i]),
         "background_gap": bool(background_gap[i]), "step_m": None if gap[i] else float(delta[i])}
        for i in np.flatnonzero(gap | stepped)
    ]
    return {
        "pass": not failures,
        "seam_length_m": length,
        "spacing_at_most_m": SAMPLE_SPACING_M,
        "samples": len(sites),
        "detailed_missing": int(detail_gap.sum()),
        "background_missing": int(background_gap.sum()),
        "steps_over_limit": int(stepped.sum()),
        "step_limit_m": MAX_STEP_M,
        "max_step_m": float(delta[~gap].max()) if (~gap).any() else None,
        "failures": failures,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("glb", type=Path)
    parser.add_argument("seam", type=Path, help="GeoJSON linework in local projected metres")
    parser.add_argument("--out", type=Path, help="Local JSON evidence path")
    args = parser.parse_args()
    data = json.loads(args.seam.read_text())
    geometry = shapely.geometry.shape(data["geometry"] if data["type"] == "Feature" else data)
    report = check_seam(args.glb, geometry)
    summary = {key: value for key, value in report.items() if key != "failures"}
    print(json.dumps(summary, indent=2))
    if args.out is not None:
        args.out.write_text(json.dumps(report, indent=2) + "\n")
    raise SystemExit(0 if report["pass"] else 1)


if __name__ == "__main__":
    main()
