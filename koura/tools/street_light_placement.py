"""Plan roadside lattice lamps from the built road network."""

import json
import math
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import shapely
from shapely.geometry import LineString, Point, shape

OSM_PATH = Path(__file__).resolve().parents[1] / "data" / "osm_koura.json"
ROAD_SPACING = {
    "primary": 36.0,
    "secondary": 38.0,
    "tertiary": 40.0,
    "residential": 38.0,
    "unclassified": 44.0,
    "service": 44.0,
    "track": 50.0,
}
POST_CLEARANCE_M = 0.45
MIN_GENERATED_GAP_M = 12.0
AUTHORED_GAP_M = 18.0


@dataclass(frozen=True)
class StreetLightPlacement:
    x: float
    y: float
    heading_deg: float
    road_id: int | None
    road_class: str
    segment_index: int
    chainage_m: float
    way_ids: tuple[int, ...]


def _osm_road_classes(path):
    with path.open(encoding="utf-8") as stream:
        snapshot = json.load(stream)
    return {
        element["id"]: element["tags"]["highway"]
        for element in snapshot["elements"]
        if element["type"] == "way" and "highway" in element.get("tags", {})
    }


def _nearby_lamp(point, cells):
    row = math.floor(point.x / AUTHORED_GAP_M)
    column = math.floor(point.y / AUTHORED_GAP_M)
    for i in range(row - 1, row + 2):
        for j in range(column - 1, column + 2):
            if any(point.distance(other) < gap for other, gap in cells.get((i, j), ())):
                return True
    return False


def _add_lamp(point, gap, cells):
    row = math.floor(point.x / AUTHORED_GAP_M)
    column = math.floor(point.y / AUTHORED_GAP_M)
    cells[row, column].append((point, gap))


def _roadside_point(line, nominal, inset, half_width, side, is_clear):
    for shift in (0.0, -3.0, 3.0, -6.0, 6.0):
        chainage = nominal + shift
        if not inset <= chainage <= line.length - inset:
            continue
        center = line.interpolate(chainage)
        before = line.interpolate(max(0.0, chainage - 1.0))
        after = line.interpolate(min(line.length, chainage + 1.0))
        dx, dy = after.x - before.x, after.y - before.y
        length = math.hypot(dx, dy)
        if length < 1e-6:
            continue
        left_x, left_y = -dy / length, dx / length
        for direction in (side, -side):
            for verge in (0.8, 1.15, 1.55):
                offset = direction * (half_width + verge)
                point = Point(center.x + offset * left_x, center.y + offset * left_y)
                if is_clear(point):
                    heading = math.degrees(math.atan2(center.x - point.x, center.y - point.y)) % 360.0
                    return point, heading, chainage
    return None


def plan_street_lights(
    roads_sidecar: Path,
    authored_xy: Iterable[tuple[float, float]] = (),
    *,
    obstacle_tree: shapely.STRtree | None = None,
    osm_path: Path = OSM_PATH,
) -> list[StreetLightPlacement]:
    """Return projected east/north positions and clockwise headings from north.

    Estimated positions follow every road class in the clipped road sidecar.
    An optional obstacle index can add exact pavement, structure and other
    footprints in the same local CRS. The plan contains no elevation.
    """
    with Path(roads_sidecar).open(encoding="utf-8") as stream:
        data = json.load(stream)
    zone = shape(data["zone"]).buffer(-1.05)
    shapely.prepare(zone)
    osm_classes = _osm_road_classes(Path(osm_path))
    segments = data["segments"]
    lines = [LineString(segment["xy"]) for segment in segments]
    widths = [segment["half_width_m"] for segment in segments]
    road_footprints = [
        line.buffer(width + POST_CLEARANCE_M, cap_style="round", quad_segs=4)
        for line, width in zip(lines, widths)
    ]
    degree = Counter(node for segment in segments for node in segment["nodes"])
    junctions = {}
    for segment, width in zip(segments, widths):
        for node, xy in zip(segment["nodes"], (segment["xy"][0], segment["xy"][-1])):
            if degree[node] >= 3 and (node not in junctions or width > junctions[node][1]):
                junctions[node] = (xy, width)
    road_footprints.extend(
        Point(xy).buffer(1.4 * width + POST_CLEARANCE_M, quad_segs=4)
        for xy, width in junctions.values()
    )
    roads = shapely.STRtree(road_footprints)
    cells = defaultdict(list)
    for xy in authored_xy:
        _add_lamp(Point(xy), AUTHORED_GAP_M, cells)

    def is_clear(point):
        return (
            zone.covers(point)
            and not roads.query(point, predicate="intersects").size
            and (obstacle_tree is None or not obstacle_tree.query(
                point, predicate="dwithin", distance=POST_CLEARANCE_M
            ).size)
            and not _nearby_lamp(point, cells)
        )

    placements = []
    # Give junction approaches on through roads first choice of clear verges.
    for index in sorted(range(len(lines)), key=lambda i: (-widths[i], -lines[i].length, i)):
        line, width = lines[index], widths[index]
        if line.length < 4.0:
            continue
        way_ids = tuple(segments[index]["way_ids"])
        road_id = way_ids[0] if way_ids else None
        road_class = next((osm_classes[way] for way in way_ids if way in osm_classes), "local")
        interval = ROAD_SPACING.get(road_class.removesuffix("_link"), 42.0)
        count = max(1, round(line.length / interval))
        inset = min(7.0, line.length / 4)
        for station in range(count):
            chainage = line.length * (station + 0.5) / count
            side = 1 if (index + station) % 2 == 0 else -1
            candidate = _roadside_point(line, chainage, inset, width, side, is_clear)
            if candidate is not None:
                point, heading, actual_chainage = candidate
                _add_lamp(point, MIN_GENERATED_GAP_M, cells)
                placements.append(StreetLightPlacement(
                    point.x, point.y, heading, road_id, road_class, index, actual_chainage, way_ids
                ))
    return placements
