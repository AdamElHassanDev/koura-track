"""Plan-view checks over the same clipped road network used to build the scene."""

import heapq
import itertools
import json
import math
import os
import re
from collections import defaultdict
from contextlib import contextmanager
from pathlib import Path

import numpy as np
import shapely
from openlaps.geo import LocalProjection
from pyproj import Geod
from shapely.geometry import LineString, Point, box, mapping, shape
from stages import stage_zone

ZONE_PATH = Path(__file__).resolve().parents[1] / "handoff/inputs/zone.json"
ROUTE_TOLERANCE_M = 8.0
SAMPLE_STEP_M = 10.0


@contextmanager
def record_network(roads, path, requested_spawns=()):
    """Capture the generator's built centreline runs without retaining the scene."""
    path = Path(path)
    temporary = path.with_suffix(".json.part")
    original = roads.build_roads

    def capture(net, *args, **kwargs):
        result = original(net, *args, **kwargs)
        segments = []
        for edge in net.edges:
            for start, end in net.ranges(edge):
                # A junction patch supplies the connection across a trimmed edge end.
                # At the zone boundary each clipped run ends at its own dead end.
                a = f"run:{len(segments)}:a"
                b = f"run:{len(segments)}:b"
                if abs(start - edge.s0) < 1e-6 and net.node_inside(edge.a):
                    a = f"node:{edge.a}"
                    start = 0.0
                if abs(end - edge.s1) < 1e-6 and net.node_inside(edge.b):
                    b = f"node:{edge.b}"
                    end = edge.length
                chainage = np.r_[start, edge.s[(edge.s > start) & (edge.s < end)], end]
                xy = np.column_stack([
                    np.interp(chainage, edge.s, edge.P[:, dim]) for dim in (0, 1)
                ])
                segments.append({
                    "nodes": [a, b],
                    "xy": xy.round(4).tolist(),
                    "half_width_m": edge.hw,
                })
        zone = getattr(net, "zona", None)
        if zone is None:
            zone = box(*net.rect)
        data = {
            "zone": mapping(zone),
            "requested_spawns": list(requested_spawns),
            "segments": segments,
        }
        with temporary.open("w") as stream:
            json.dump(data, stream, separators=(",", ":"), allow_nan=False)
        return result

    roads.build_roads = capture
    try:
        yield
        os.utime(temporary, None)
        temporary.replace(path)
    finally:
        roads.build_roads = original
        temporary.unlink(missing_ok=True)


def _projection(geo):
    return LocalProjection.marco(geo["lat0"], geo["lon0"], geo["rect"])


def build_zone(stage, sidecar, geo):
    """Use the actual zone if recorded, or the standard stage extent for legacy builds."""
    sidecar = Path(sidecar)
    if sidecar.is_file():
        return shape(json.loads(sidecar.read_text())["zone"])
    if not geo:
        return None
    zone = json.loads(ZONE_PATH.read_text())
    rect = box(*geo["rect"])
    if stage not in zone["stages"]:
        return rect
    return stage_zone(zone, stage, _projection(geo)).intersection(rect)


class BuiltNetwork:
    def __init__(self, segments):
        self.lines = [LineString(segment["xy"]) for segment in segments]
        self.ends = [tuple(segment["nodes"]) for segment in segments]
        self.widths = [segment["half_width_m"] for segment in segments]
        self.index = shapely.STRtree(self.lines)
        self.adj = defaultdict(list)
        for line, (a, b) in zip(self.lines, self.ends):
            self.adj[a].append((b, line.length))
            self.adj[b].append((a, line.length))

        self.components = {}
        for node in self.adj:
            if node in self.components:
                continue
            self.components[node] = node
            queue = [node]
            for current in queue:
                for next_node, _ in self.adj[current]:
                    if next_node not in self.components:
                        self.components[next_node] = node
                        queue.append(next_node)
        self.component_lengths = defaultdict(float)
        self.component_points = {}
        for line, (a, _) in zip(self.lines, self.ends):
            component = self.components[a]
            self.component_lengths[component] += line.length
            self.component_points.setdefault(component, line.coords[0])

    def nearby(self, point, distance):
        return self.index.query(point, predicate="dwithin", distance=distance).tolist()

    def _paths_from(self, start, limit, cache):
        if start not in cache:
            distances = {start: 0.0}
            queue = [(0.0, start)]
            while queue:
                distance, node = heapq.heappop(queue)
                if distance > distances[node]:
                    continue
                for next_node, length in self.adj[node]:
                    cost = distance + length
                    if cost <= limit and cost < distances.get(next_node, math.inf):
                        distances[next_node] = cost
                        heapq.heappush(queue, (cost, next_node))
            cache[start] = distances
        return cache[start]

    def distance(self, previous, following, limit, cache):
        """Bounded network distance between two interior projections."""
        i, along_i, _ = previous
        j, along_j, _ = following
        result = abs(along_i - along_j) if i == j else math.inf
        for a, left in zip(self.ends[i], (along_i, self.lines[i].length - along_i)):
            if left >= result or left > limit:
                continue
            paths = self._paths_from(a, limit, cache)
            for b, right in zip(self.ends[j], (along_j, self.lines[j].length - along_j)):
                result = min(result, left + paths.get(b, math.inf) + right)
        return result


def _route_samples(network, route, proj):
    lat, lon = zip(*route["polyline"])
    line = LineString(np.column_stack(proj.to_local(lon, lat)))
    if route["closed"] and line.coords[0] != line.coords[-1]:
        line = LineString([*line.coords, line.coords[0]])
    chainage = np.r_[np.arange(0.0, line.length, SAMPLE_STEP_M), line.length]
    points = shapely.line_interpolate_point(line, chainage)
    candidates = []
    uncovered = []
    nearest_offsets = []
    for metres, point in zip(chainage, points):
        options = [
            (idx, network.lines[idx].project(point), network.lines[idx].distance(point))
            for idx in network.nearby(point, ROUTE_TOLERANCE_M)
        ]
        if options:
            nearest_offsets.append(min(option[2] for option in options))
        else:
            lon, lat = proj.to_lonlat(point.x, point.y)
            uncovered.append({"km": round(metres / 1000, 4), "lat": float(lat), "lon": float(lon)})
        candidates.append(options)
    return chainage, candidates, uncovered, nearest_offsets


def _match_route(network, chainage, candidates, closed):
    """Find a continuous local road match, including the closing turn on a loop."""
    limit = 3 * SAMPLE_STEP_M + 2 * ROUTE_TOLERANCE_M
    cache = {}
    best = None
    first_choices = [[first] for first in candidates[0]] if closed else [candidates[0]]
    for first in first_choices:
        costs = {candidate: (candidate[2], 0.0, candidate[0]) for candidate in first}
        remaining = [*candidates[1:-1], first if closed else candidates[-1]]
        for options, interval in zip(remaining, np.diff(chainage)):
            next_costs = {}
            for following in options:
                for previous, (score, total_length, start_idx) in costs.items():
                    length = network.distance(previous, following, limit, cache)
                    if length > 3 * interval + 2 * ROUTE_TOLERANCE_M:
                        continue
                    candidate = (
                        score + following[2] + abs(length - interval),
                        total_length + length,
                        start_idx,
                    )
                    if candidate < next_costs.get(following, (math.inf,)):
                        next_costs[following] = candidate
            costs = next_costs
            if not costs:
                break
        if costs:
            winner = min(costs.values())
            best = winner if best is None else min(best, winner)
    return best


def _linear_distances(zone, proj, built_zone):
    points = {}
    for name, position in (zone["villages"] | zone["key_points"]).items():
        xy = proj.to_local(position["lon"], position["lat"])
        if built_zone.covers(Point(*xy)):
            points[name] = (position, np.array(xy))
    pairs = sorted(
        itertools.combinations(points, 2),
        key=lambda pair: np.linalg.norm(points[pair[0]][1] - points[pair[1]][1]),
        reverse=True,
    )[:3]
    geod = Geod(ellps="WGS84")
    measurements = []
    for a, b in pairs:
        ll0, xy0 = points[a]
        ll1, xy1 = points[b]
        _, _, geodesic = geod.inv(ll0["lon"], ll0["lat"], ll1["lon"], ll1["lat"])
        if geodesic == 0:
            continue
        length = float(np.linalg.norm(xy0 - xy1))
        measurements.append({
            "pair": [a, b], "scene_m": length, "wgs84_m": geodesic,
            "difference_pct": 100 * abs(length - geodesic) / geodesic,
        })
    return measurements


def _pit_dummies(inspection):
    return sorted(
        (int(name.rsplit("_", 1)[1]), matrix)
        for _, name, _, matrix, _ in inspection.get("dummies", ())
        if re.fullmatch(r"AC_PIT_\d+", name)
    )


def _spawn_checks(pits, network, glb, requested_spawns, proj):
    if not pits:
        return {"status": "fail", "measured": {"reason": "No AC_PIT_n markers"}}
    xy = np.array([(matrix[12], -matrix[14]) for _, matrix in pits])
    marker_z = np.array([matrix[13] for _, matrix in pits])
    heights = np.full(len(pits), np.nan)
    if glb is not None and Path(glb).is_file():
        from ride import heights as mesh_heights
        from ride import road_tris
        from scipy.spatial import cKDTree

        triangles = road_tris(glb)
        centroids = triangles.mean(axis=1)[:, [0, 2]]
        radius = np.linalg.norm(triangles[:, :, [0, 2]] - centroids[:, None, :], axis=2).max()
        # The measures are taken only at the pits. Use the full encompassing radius.
        heights = mesh_heights(triangles, cKDTree(centroids), radius, xy[:, 0], -xy[:, 1])

    slots = []
    for (slot, matrix), point, z, ground in zip(pits, shapely.points(xy), marker_z, heights):
        best_offset = math.inf
        alignment = None
        if network is not None:
            nearby = network.nearby(point, max(network.widths, default=0.0) + 0.1)
            for idx in sorted(nearby, key=lambda i: network.lines[i].distance(point)):
                line = network.lines[idx]
                offset = line.distance(point)
                if offset > network.widths[idx] + 0.1:
                    continue
                along = line.project(point)
                p = line.interpolate(max(0.0, along - 2.0))
                q = line.interpolate(min(line.length, along + 2.0))
                tangent = np.array([q.x - p.x, q.y - p.y])
                forward = np.array([matrix[8], -matrix[10]])
                denominator = np.linalg.norm(tangent) * np.linalg.norm(forward)
                if denominator:
                    alignment = math.degrees(math.acos(np.clip(abs(tangent @ forward) / denominator, 0, 1)))
                    best_offset = offset
                    break
        height_above = float(z - ground) if np.isfinite(ground) else None
        item = {
            "slot": slot,
            "centreline_offset_m": best_offset if np.isfinite(best_offset) else None,
            "heading_error_deg": alignment,
            "height_above_road_m": height_above,
        }
        if slot < len(requested_spawns) and proj is not None:
            request = requested_spawns[slot]
            original = Point(*proj.to_local(request["lon"], request["lat"]))
            item.update({"requested": request["name"], "request_offset_m": original.distance(point)})
        slots.append(item)

    expected = len(requested_spawns) or None
    count_ok = expected is None or [slot for slot, _ in pits] == list(range(expected))
    surface_ok = glb is None or all(
        item["height_above_road_m"] is not None and -0.1 <= item["height_above_road_m"] <= 0.75
        for item in slots
    )
    heading_ok = network is None or all(
        item["heading_error_deg"] is not None and item["heading_error_deg"] <= 15
        for item in slots
    )
    status = "pass" if count_ok and surface_ok and heading_ok else "fail"
    if status == "pass" and (network is None or glb is None):
        status = "unavailable"
    return {"status": status, "measured": {"expected_named_slots": expected, "markers": slots}}


def verify_network(stage, sidecar, inspection, geo, *, glb=None):
    """Return structured results for static checks 14, 16, 17 and 18."""
    zone = json.loads(ZONE_PATH.read_text())
    sidecar = Path(sidecar)
    proj = _projection(geo) if geo else None
    coverage = {}
    connectivity = {}
    lengths = {}
    network = None
    requested_spawns = []
    route_names = {
        "S1": ("nakhle_big_loop", "nakhle_small_loop"),
        "S2": tuple(zone["routes"]),
        "S3": tuple(zone["routes"]),
    }.get(stage, ())
    pits = _pit_dummies(inspection)
    built_zone = build_zone(stage, sidecar, geo)
    if built_zone is not None and proj is not None:
        requested_spawns = [
            s for s in zone["spawn_points"]
            if built_zone.contains(Point(*proj.to_local(s["lon"], s["lat"])))
        ]
    if sidecar.is_file() and (glb is None or sidecar.stat().st_mtime_ns >= Path(glb).stat().st_mtime_ns):
        data = json.loads(sidecar.read_text())
        network = BuiltNetwork(data["segments"])
        requested_spawns = data["requested_spawns"]

    route_components = set()
    if proj is not None and network is not None and network.lines:
        for name in route_names:
            route = zone["routes"][name]
            chainage, candidates, uncovered, offsets = _route_samples(network, route, proj)
            match = None if uncovered else _match_route(network, chainage, candidates, route["closed"])
            coverage[name] = {
                "samples": len(chainage), "max_covered_offset_m": max(offsets, default=None),
                "uncovered": uncovered, "connected_chain": match is not None,
                "closed": route["closed"],
            }
            if match is not None:
                _, length, start_line = match
                route_components.add(network.components[network.ends[start_line][0]])
                ref = route["length_km"]
                lengths[name] = {
                    "built_km": length / 1000, "reference_km": ref,
                    "difference_pct": 100 * abs(length / 1000 - ref) / ref,
                }

        if pits:
            matrix = pits[0][1]
            start_line = network.index.nearest(Point(matrix[12], -matrix[14]))
            main = network.components[network.ends[start_line][0]]
            islands = []
            for component, length in network.component_lengths.items():
                if component != main:
                    lon, lat = proj.to_lonlat(*network.component_points[component])
                    islands.append({"length_m": length, "lat": float(lat), "lon": float(lon)})
            islands.sort(key=lambda island: -island["length_m"])
            connectivity = {
                "spawn_component_length_m": network.component_lengths[main],
                "all_named_routes_on_spawn_component": route_components <= {main} and len(lengths) == len(route_names),
                "other_components": islands,
            }

    coverage_status = "not_applicable"
    if route_names:
        coverage_status = "unavailable" if network is None or proj is None else (
            "pass" if coverage and all(route["connected_chain"] for route in coverage.values()) else "fail"
        )
    scales = _linear_distances(zone, proj, built_zone) if built_zone is not None and proj is not None else []
    distance_status = "not_applicable"
    if route_names or len(scales) == 3:
        if network is None and route_names or proj is None:
            distance_status = "unavailable"
        else:
            measurements = [*lengths.values(), *scales]
            distance_status = "pass" if (
                len(lengths) == len(route_names) and len(scales) == 3
                and all(row["difference_pct"] < 1 for row in measurements)
            ) else "fail"
    connected_status = "unavailable" if network is None or proj is None else "fail"
    if (connectivity.get("all_named_routes_on_spawn_component")
            and all(island["length_m"] <= 150 for island in connectivity["other_components"])):
        connected_status = "pass"

    missing_graph = {"reason": "Built road-network sidecar unavailable; rebuild to capture it"}
    return {
        14: {"status": coverage_status, "measured": coverage or (missing_graph if route_names else {})},
        16: {"status": distance_status, "measured": {"route_lengths": lengths, "scale": scales}},
        17: {"status": connected_status, "measured": connectivity or missing_graph},
        18: _spawn_checks(pits, network, glb, requested_spawns, proj),
    }
