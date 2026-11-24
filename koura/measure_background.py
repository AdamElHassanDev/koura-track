"""Measure the Stage 2 loop, line of sight, and proposed background ground."""

import argparse
from dataclasses import dataclass
import json
import math
import os
from pathlib import Path
import sys

import numpy as np
from numba import njit
from rasterio.features import shapes
from rasterio.transform import Affine
import shapely
from shapely.geometry import LineString, box, mapping, shape
from shapely.ops import polygonize, transform, unary_union


GRID_M = 30.0
OBSERVER_STEP_M = 100.0
EYE_HEIGHT_M = 1.2
RANGE_M = 3000.0
FILL_MARGIN_M = 100.0
ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class BackgroundCoverage:
    inside_loop: shapely.Geometry
    visible: shapely.Geometry
    fill: shapely.Geometry
    observer_count: int
    route_names: tuple[str, ...]
    land_mask_source: str
    max_outside_m: float | None


def _route_line(route, proj):
    lat, lon = np.asarray(route["polyline"], dtype=float).T
    line = np.column_stack(proj.to_local(lon, lat))
    if route.get("closed") and not np.array_equal(line[0], line[-1]):
        line = np.vstack([line, line[0]])
    return LineString(line)


def _observers(lines, frame):
    samples = []
    for line in lines:
        distances = np.arange(0.0, line.length, OBSERVER_STEP_M)
        if not line.is_closed:
            distances = np.append(distances, line.length)
        points = shapely.line_interpolate_point(line, distances)
        samples.extend(shapely.get_coordinates(points[shapely.covers(frame, points)]))
    return np.asarray(samples, dtype=float).reshape(-1, 2)


@njit(cache=True, inline="always")
def _cell_terms(grid, x, y):
    southwest = grid[y, x]
    east = grid[y, x + 1] - southwest
    north = grid[y + 1, x] - southwest
    cross = grid[y + 1, x + 1] - southwest - east - north
    return southwest, east, north, cross


@njit(cache=True)
def _line_visible(grid, x, y, eye_x, eye_y, eye_z):
    """Intersect the ray with each cell's bilinear elevation surface."""
    dx, dy = eye_x - x, eye_y - y
    x_step = -1 if dx < 0 else 1
    y_step = -1 if dy < 0 else 1
    column = x - int(dx < 0)
    row = y - int(dy < 0)
    x_stride = math.inf if dx == 0.0 else 1.0 / abs(dx)
    y_stride = math.inf if dy == 0.0 else 1.0 / abs(dy)
    next_x, next_y = x_stride, y_stride
    target_z = grid[y, x]
    rise = eye_z - target_z
    entry = 0.0

    while entry < 1.0:
        leave = min(next_x, next_y, 1.0)
        southwest, east, north, cross = _cell_terms(grid, column, row)
        u = x - column + dx * entry
        v = y - row + dy * entry
        start = southwest + east * u + north * v + cross * u * v - target_z - rise * entry
        slope = east * dx + north * dy + cross * (dx * v + dy * u) - rise
        curve = cross * dx * dy
        width = leave - entry
        finish = start + width * (slope + width * curve)
        if not math.isfinite(finish) or max(start, finish) > 1e-6:
            return False
        # A saddle cell can block the view between the two edge crossings.
        if curve < 0.0:
            peak = -slope / (2.0 * curve)
            if 0.0 < peak < width and start + peak * (slope + peak * curve) > 1e-6:
                return False
        entry = leave
        if next_x <= leave:
            column += x_step
            next_x += x_stride
        if next_y <= leave:
            row += y_step
            next_y += y_stride
    return True


@njit(cache=True)
def _viewshed(grid, observers, land, radius):
    seen = np.zeros(grid.shape, dtype=np.bool_)
    eyes = 0
    for eye_x, eye_y in observers:
        x0, y0 = int(math.floor(eye_x)), int(math.floor(eye_y))
        u, v = eye_x - x0, eye_y - y0
        southwest, east, north, cross = _cell_terms(grid, x0, y0)
        eye_z = southwest + east * u + north * v + cross * u * v + EYE_HEIGHT_M
        if not math.isfinite(eye_z):
            continue
        eyes += 1
        # The outside row and column keep the bilinear cells around the requested frame complete.
        for y in range(max(1, math.ceil(eye_y - radius)), min(grid.shape[0] - 1, math.floor(eye_y + radius) + 1)):
            half_width = math.sqrt(max(0.0, radius * radius - (y - eye_y) ** 2))
            first = max(1, math.ceil(eye_x - half_width))
            last = min(grid.shape[1] - 1, math.floor(eye_x + half_width) + 1)
            for x in range(first, last):
                if land[y, x] and not seen[y, x] and _line_visible(grid, x, y, eye_x, eye_y, eye_z):
                    seen[y, x] = True
    return seen, eyes


def _cells_polygon(mask, left, bottom):
    # Array rows grow northward in local UTM. The affine must do the same.
    geotransform = Affine(GRID_M, 0, left, 0, GRID_M, bottom)
    raster_shapes = shapes(mask.astype(np.uint8), mask=mask, transform=geotransform)
    polygons = []
    for polygon, _ in raster_shapes:
        geom = shape(polygon)
        polygons.append(geom if geom.is_valid else geom.buffer(0))
    return unary_union(polygons)


def coverage(zone, proj, detailed, dem, *, stage="S2", sea=None, max_outside_m=None):
    """Return local-metre polygons using the pinned origin and stage frame.

    S2 uses all named routes. The frame and detailed polygon are the supplied
    ones, so a smaller trial can reuse this measurement without changing S2.
    `max_outside_m` limits the buffered visible ground outside the loop only.
    """
    if max_outside_m is not None and (not math.isfinite(max_outside_m) or max_outside_m < 0):
        raise ValueError("The background route-distance limit must be nonnegative and finite")
    frame = box(proj.xmin, proj.ymin, proj.xmax, proj.ymax)
    routes = zone["routes"]
    configured = zone["stages"][stage].get("must_contain_routes")
    names = tuple(routes if stage == "S2" or not configured else configured)
    lines = [_route_line(routes[name], proj) for name in names]
    loop = _route_line(routes["loop"], proj)
    loop_area = unary_union(list(polygonize(unary_union([loop])))).intersection(frame)
    if loop_area.is_empty and frame.covers(loop):
        raise ValueError("The recorded loop does not enclose any land")
    eyes = _observers(lines, frame)
    if not len(eyes):
        raise ValueError("No named-route survey points fall inside the stage frame")

    left, bottom = proj.xmin - GRID_M, proj.ymin - GRID_M
    nx = math.ceil((proj.xmax - proj.xmin) / GRID_M) + 2
    ny = math.ceil((proj.ymax - proj.ymin) / GRID_M) + 2
    xx = left + (np.arange(nx) + 0.5) * GRID_M
    yy = bottom + (np.arange(ny) + 0.5) * GRID_M
    gx, gy = np.meshgrid(xx, yy)
    grid = np.asarray(dem.sample(proj, gx, gy), dtype=float)
    middle = np.isfinite(grid)
    if sea is not None and not sea.is_empty:
        middle &= ~shapely.intersects_xy(sea, gx, gy)
        land = frame.difference(sea)
        land_source = "OSM coastline"
    else:
        middle &= grid > 0
        land = frame if middle.all() else frame.intersection(_cells_polygon(middle, left, bottom))
        land_source = "positive, finite Copernicus cells"

    local_eyes = (eyes - [xx[0], yy[0]]) / GRID_M
    seen, observer_count = _viewshed(grid, local_eyes, middle, RANGE_M / GRID_M)
    if observer_count == 0:
        raise ValueError("The elevation raster has no valid observation points")
    visible = _cells_polygon(seen, left, bottom).intersection(land)
    inside = loop_area.intersection(land)
    distant = visible.buffer(FILL_MARGIN_M, quad_segs=4)
    if max_outside_m is not None:
        distant = distant.intersection(unary_union(lines).buffer(max_outside_m, quad_segs=4))
    fill = inside.union(distant).intersection(land).difference(detailed)
    return BackgroundCoverage(inside.difference(detailed), visible, fill, observer_count, names,
                              land_source, max_outside_m)


def measure(result, detailed, proj, osm_data, buildings):
    """Summarize projected road-centreline length and intersecting footprints."""
    from openlaps.config import DRIVABLE

    roads = []
    for way in osm_data["ways"]:
        if way["tags"].get("highway") in DRIVABLE and len(way["coords"]) >= 2:
            lon, lat = np.asarray(way["coords"], dtype=float).T
            roads.append(LineString(np.column_stack(proj.to_local(lon, lat))))
    way_index = shapely.STRtree(roads)
    footprint_index = shapely.STRtree([building["poly"] for building in buildings])

    def counts(area):
        nearby = way_index.query(area, predicate="intersects")
        lengths = shapely.length(shapely.intersection(way_index.geometries[nearby], area))
        return {
            "area_km2": round(area.area / 1e6, 4),
            "osm_drivable_way_km": round(float(lengths.sum()) / 1000, 4),
            "building_footprint_count": len(footprint_index.query(area, predicate="intersects")),
        }

    return {
        "observers": result.observer_count,
        "routes": result.route_names,
        "dem_sample_m": GRID_M,
        "eye_above_dem_m": EYE_HEIGHT_M,
        "observer_step_m": OBSERVER_STEP_M,
        "maximum_line_of_sight_m": RANGE_M,
        "visibility_model": "Cell-centre targets and exact bilinear line of sight on the sampled terrain",
        "visible_buffer_m": FILL_MARGIN_M,
        "maximum_outside_distance_to_route_m": result.max_outside_m,
        "land_mask": result.land_mask_source,
        "projection": {"epsg": proj.epsg, "origin_lat": proj.lat0, "origin_lon": proj.lon0},
        "inside_loop_uncovered": counts(result.inside_loop),
        "visible_land": counts(result.visible),
        "visible_uncovered": counts(result.visible.difference(detailed)),
        "selected_fill": counts(result.fill),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", nargs="?", default="S2")
    parser.add_argument("--out", type=Path, default=ROOT / "out" / "WP14" / "measurements")
    parser.add_argument("--osm", type=Path, default=ROOT / "koura" / "data" / "osm_koura.json")
    parser.add_argument("--max-outside-m", type=float)
    args = parser.parse_args()

    os.environ.setdefault("OPENLAPS_CACHE", str(ROOT / "cache"))
    sys.path.insert(0, str(ROOT / "openlaps"))
    from openlaps.buildings import collect
    from openlaps.cobertura import mar_desde_costa
    from openlaps.geo import LocalProjection
    from openlaps.sources import msbuildings, osm, rasters
    from stages import stage_zone

    zone = json.loads((ROOT / "handoff" / "inputs" / "zone.json").read_text())
    rect = zone["stages"][args.stage]["expected"]["rect_local_m"]
    origin = zone["origin"]
    proj = LocalProjection.marco(origin["lat"], origin["lon"], rect)
    detailed = stage_zone(zone, args.stage, proj)
    snapshot = json.loads(args.osm.read_text())
    baseline = snapshot.get("build9_road_scope", {})
    if args.stage in baseline.get("stages", ()):
        snapshot["elements"] = snapshot["elements"][:baseline["element_count"]]
    data = osm.parse(snapshot)
    coast = [np.column_stack(proj.to_local(*np.asarray(line).T)) for line in data["coast"]]
    sea = mar_desde_costa(coast, rect)
    dem = rasters.copernicus_dem(proj.bbox().padded(450))
    result = coverage(zone, proj, detailed, dem, stage=args.stage, sea=sea, max_outside_m=args.max_outside_m)
    footprints = collect(data, msbuildings.download(proj.bbox()), proj, rect)
    report = measure(result, detailed, proj, data, footprints)
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    features = []
    for name in ("inside_loop", "visible", "fill"):
        geom = transform(proj.to_lonlat, getattr(result, name))
        features.append({"type": "Feature", "properties": {"name": name}, "geometry": mapping(geom)})
    (args.out / "coverage.geojson").write_text(json.dumps({"type": "FeatureCollection", "features": features}) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
