"""Bounded-memory equivalent of openlaps/tools/escalones.py for large stages."""

import argparse
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
from numba import njit
from scipy.ndimage import binary_closing

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "openlaps" / "tools"))
from escalones import _rasterizar
from render import load_glb


@njit(cache=True)
def overlap_cells(heights, counts, x0, z0, cell):
    hits = []
    for i in range(counts.shape[0]):
        for j in range(counts.shape[1]):
            count = counts[i, j]
            if count < 2:
                continue
            values = np.sort(heights[i, j, :count])
            worst = 0.0
            for k in range(1, count):
                change = values[k] - values[k - 1]
                if 0.03 <= change <= 0.6:
                    worst = max(worst, change)
            if worst:
                hits.append((x0 + (i + 0.5) * cell, z0 + (j + 0.5) * cell, worst))
    return hits


@njit(cache=True)
def seam_cells(heights, counts, width, depth, x0, z0, cell):
    hits = []
    for i in range(width):
        for j in range(depth):
            for di, dj in ((1, 0), (0, 1)):
                if i + di >= counts.shape[0] or j + dj >= counts.shape[1]:
                    continue
                worst = np.float32(0)
                for a in range(counts[i, j]):
                    nearest = np.float32(0.6)
                    for b in range(counts[i + di, j + dj]):
                        change = np.float32(abs(heights[i, j, a] - heights[i + di, j + dj, b]))
                        nearest = min(nearest, change)
                    if nearest < np.float32(0.6):
                        worst = max(worst, nearest)
                if worst > np.float32(0.05):
                    hits.append((x0 + (i + 0.5 + di / 2) * cell, z0 + (j + 0.5 + dj / 2) * cell, worst))
    return hits


def tiles(triangles, cell, layers, halo):
    # Keep the grid anchored at the global minimum, as in the original tool.
    tile = 256
    low = triangles[:, :, (0, 2)].min(axis=1)
    high = triangles[:, :, (0, 2)].max(axis=1)
    origin = low.min(axis=0)
    limits = ((high.max(axis=0) - origin) / cell).astype(int) + 2
    first = np.maximum(0, ((low - origin) / cell).astype(int) - halo) // tile
    last = np.minimum(limits - 1, ((high - origin) / cell).astype(int) + halo + 1) // tile
    buckets = defaultdict(list)
    for index, ((left, top), (right, bottom)) in enumerate(zip(first.tolist(), last.tolist())):
        for i in range(left, right + 1):
            for j in range(top, bottom + 1):
                buckets[i, j].append(index)

    for (i, j), indexes in sorted(buckets.items()):
        begin = np.array([i * tile, j * tile])
        end = np.minimum(begin + tile, limits)
        start = np.maximum(begin - halo, 0)
        stop = np.minimum(end + halo, limits)
        width, depth = stop - start
        x0, z0 = origin + start * cell
        heights = np.full((width, depth, layers), np.nan)
        counts = np.zeros((width, depth), dtype=np.int64)
        _rasterizar(triangles[indexes], x0, z0, width, depth, cell, heights, counts)
        yield heights, counts, begin - start, end - start, x0, z0


def grouped(hits):
    """Count the original 4 m greedy groups using neighbouring spatial buckets."""
    bins = defaultdict(list)
    groups = []
    for x, z, delta in sorted(hits, key=lambda hit: -hit[2]):
        ix, iz = math.floor(x / 4), math.floor(z / 4)
        candidates = (
            index
            for bx in range(ix - 1, ix + 2)
            for bz in range(iz - 1, iz + 2)
            for index in bins.get((bx, bz), ())
        )
        match = min(
            (index for index in candidates if (groups[index][0] - x)**2 + (groups[index][1] - z)**2 < 16),
            default=None,
        )
        if match is None:
            bins[ix, iz].append(len(groups))
            groups.append([x, z, delta, 1])
        else:
            groups[match][3] += 1
    return groups


def measure(glb):
    meshes = load_glb(glb)[0]
    roads = []
    solid = []
    for mesh in meshes:
        name = mesh["name"]
        if not name.startswith("1") or name.startswith(("1WALL", "1GRASS")):
            continue
        triangles = mesh["pos"][mesh["idx"]]
        solid.append(triangles)
        if "calzada" in name:
            roads.append(triangles)
    del meshes
    steps, seams, holes = [], [], []
    if solid:
        triangles = np.concatenate(solid, dtype=np.float64)
        for heights, counts, _, _, x0, z0 in tiles(triangles, 0.5, 6, 0):
            steps.extend(overlap_cells(heights, counts, x0, z0, 0.5))
        del triangles
    if roads:
        triangles = np.concatenate(roads, dtype=np.float64)
        structure = np.ones((3, 3), dtype=bool)
        # Closing by two cells uses a four-cell halo, as erosion follows dilation.
        for heights, counts, begin, end, x0, z0 in tiles(triangles, 0.2, 4, 4):
            i0, j0 = begin
            i1, j1 = end
            covered = counts > 0
            missing = binary_closing(covered, structure=structure, iterations=2) & ~covered
            x, z = np.nonzero(missing[i0:i1, j0:j1])
            holes.extend(zip(x0 + (x + i0 + 0.5) * 0.2, z0 + (z + j0 + 0.5) * 0.2, np.full(len(x), 0.2)))
            seams.extend(seam_cells(heights[i0:, j0:], counts[i0:, j0:], i1 - i0, j1 - j0,
                                    x0 + i0 * 0.2, z0 + j0 * 0.2, 0.2))
    results = {}
    for name, hits in (("steps", steps), ("seams", seams), ("holes", holes)):
        hits.sort(key=lambda hit: hit[:2])
        groups = grouped(hits)
        results[name] = {"hits": len(hits), "sites": len(groups), "largest_sites": sorted(groups, key=lambda site: -site[3])[:20]}
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("glb")
    print(json.dumps(measure(parser.parse_args().glb), indent=2))
