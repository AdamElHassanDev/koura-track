"""Build Karting Mania's surveyed kerbs, barriers, lights, and paint.

Every feature takes a geographic line, polygon or position as supplied by the
site survey. Kerb indices and sides refer to the order in the stored centreline,
regardless of the circuit's race direction. An explicit kerb edge is ordered
with the verge on the indicated left or right. Dimensions are in metres above
the sampled road or ground. Timing metadata does not place paint.
"""

from dataclasses import dataclass

import numpy as np
from shapely import segmentize
from shapely.geometry import LineString, Point, Polygon
from shapely.geometry.polygon import orient
from shapely.ops import substring

from openlaps.koura_scenery import MATERIALS, _RoadSurface, _face_up, _material, _number
from openlaps.roads import box_mesh, triangulate_polygon, wall_strip


STEEL = "#626870"
RUBBER = "#353436"
RED = "#b1372f"
WHITE = "#e5e0d5"


@dataclass
class Mesh:
    group: str
    material: str
    pos: np.ndarray
    uv: np.ndarray
    faces: np.ndarray
    physics: str | None = None


def _points(proj, rows, minimum, label):
    if not isinstance(rows, list) or len(rows) < minimum:
        raise ValueError(f"{label} requires at least {minimum} latitude/longitude positions")
    if any(not isinstance(row, (list, tuple)) or len(row) != 2 for row in rows):
        raise ValueError(f"{label} positions must be [latitude, longitude]")
    lat, lon = np.array([
        [_number(row[0], -90, 90, label), _number(row[1], -180, 180, label)] for row in rows
    ]).T
    xy = np.column_stack(proj.to_local(lon, lat))
    if not np.isfinite(xy).all():
        raise ValueError(f"{label} is outside the local projection")
    return xy


def _line(xy, label):
    if not np.all(np.linalg.norm(np.diff(xy, axis=0), axis=1) > 0.0001):
        raise ValueError(f"{label} repeats a point")
    line = LineString(xy)
    if not line.is_simple or not 0.05 <= line.length <= 1500:
        raise ValueError(f"{label} must be a simple site line no longer than 1,500 m")
    return line


def _samples(line, stations):
    return np.array([line.interpolate(float(s)).coords[0] for s in stations])


def _normal(line, stations, side):
    near = _samples(line, np.maximum(stations - 0.1, 0))
    far = _samples(line, np.minimum(stations + 0.1, line.length))
    delta = far - near
    n = np.linalg.norm(delta, axis=1)
    if (n < 0.001).any():
        raise ValueError("Kart kerb has an unresolved bend")
    return side * np.column_stack((-delta[:, 1], delta[:, 0])) / n[:, None]


def _kerb_edge(proj, data, item, side):
    if "edge" in item:
        if "from_index" in item or "to_index" in item:
            raise ValueError("Kerb needs either a surveyed edge or centreline indices")
        return _line(_points(proj, item["edge"], 2, "kerb edge"), "kerb edge")
    centre = data.get("centreline")
    if (not isinstance(centre, list) or len(centre) < 3
            or any(not isinstance(row, list) or len(row) != 3 for row in centre)):
        raise ValueError("Indexed kerbs require the surveyed centreline")
    first, last = item.get("from_index"), item.get("to_index")
    if not all(type(i) is int and 0 <= i < len(centre) for i in (first, last)) or first == last:
        raise ValueError("Kerb start and end indices must be distinct and on the centreline")
    width = np.array([_number(row[2], 2.5, 20, "centreline width") for row in centre]) / 2
    xy = _points(proj, [row[:2] for row in centre], 3, "kerb centreline")
    tangent = np.roll(xy, -1, axis=0) - np.roll(xy, 1, axis=0)
    direction = np.linalg.norm(tangent, axis=1)
    if (direction < 0.001).any():
        raise ValueError("Kerb centreline has a duplicate or unresolved bend")
    normal = side * np.column_stack((-tangent[:, 1], tangent[:, 0])) / direction[:, None]
    indices = first + np.arange((last - first) % len(centre) + 1)
    indices %= len(centre)
    expected = (xy + normal * width[:, None])[indices]
    asphalt = data.get("asphalt")
    if not isinstance(asphalt, dict):
        raise ValueError("Indexed kerbs require the surveyed asphalt edges")
    rings = []
    for key in ("inner", "outer"):
        points = _points(proj, asphalt.get(key), 3, f"kart asphalt {key} edge")
        if np.linalg.norm(points[0] - points[-1]) > 0.0001:
            points = np.vstack([points, points[0]])
        rings.append(_line(points, f"kart asphalt {key} edge"))

    controls = [Point(p) for p in expected]
    ring = min(rings, key=lambda path: sum(path.distance(p) for p in controls))
    if any(ring.distance(p) > 1.5 for p in controls):
        raise ValueError("Indexed kerb widths disagree with the surveyed asphalt")

    length = ring.length
    chainage = np.array([ring.project(p) for p in controls])
    steps = (np.diff(chainage) + length / 2) % length - length / 2
    span = steps.sum()
    if not 0.05 <= abs(span) < length or (np.sign(span) * steps < -0.25).any():
        raise ValueError("Indexed kerb cannot consistently follow one asphalt edge")
    if span < 0:
        ring = LineString(ring.coords[::-1])
    start = ring.project(controls[0])
    end = start + abs(span)
    run = substring(ring, start, min(end, length))
    points = list(run.coords)
    if end > length + 1e-8:
        points.extend(list(substring(ring, 0, end - length).coords)[1:])
    return _line(np.asarray(points), "indexed kerb edge")


def _ground(height, xy, label):
    ground = np.asarray(height(xy), float)
    if not np.isfinite(ground).all():
        raise ValueError(f"{label} has no built surface underneath")
    return ground


def _palette(item, default, alternating):
    colour = item.get("colour", default)
    if not isinstance(colour, str):
        raise ValueError("Kart scenery colour must be a material name or RGB hex")
    return (RED, WHITE) if colour == "red_white" and alternating else (colour,)


def _kerb(proj, data, item, surface):
    side_name = item.get("side")
    if side_name not in ("left", "right"):
        raise ValueError("Kerb requires an explicit left or right side")
    side = 1 if side_name == "left" else -1
    line = _kerb_edge(proj, data, item, side)
    width = _number(item.get("width_m", 0.45), 0.14, 1.5, "kerb width")
    lift = _number(item.get("height_m", 0.035), 0.005, 0.04, "kerb height")
    stripe = _number(item.get("stripe_m", 0.7), 0.15, 10, "kerb stripe")
    colours = _palette(item, "red_white", True)
    ends = np.r_[np.arange(0, line.length, stripe), line.length]
    road = surface.sampler(line.buffer(0.5), None)
    for colour_index, (start, end) in enumerate(zip(ends[:-1], ends[1:])):
        run = substring(line, start, end)
        sampled = np.asarray(run.coords, float)
        distances = start + np.r_[0, np.linalg.norm(np.diff(sampled, axis=0), axis=1).cumsum()]
        stations = np.unique(np.r_[distances, np.linspace(start, end, int(np.ceil((end - start) / 0.45)) + 1)])
        xy = _samples(line, stations)
        normal = _normal(line, stations, side)
        # At the toe overlap a few centimetres onto asphalt. Tie the profile
        # to the road from that same side of the surveyed edge.
        toe = xy - normal * 0.04
        z = _ground(road, toe, "kerb toe")
        along = np.minimum(1, np.minimum(stations, line.length - stations) / 0.30)
        offsets = np.array([-0.04, width * 0.22, width * 0.72, width])
        strip = xy[:, None, :] + offsets[None, :, None] * normal[:, None, :]
        crown = z[:, None] + 0.002 + along[:, None] * np.array([0, lift - 0.002, lift - 0.002, 0])
        pos = np.column_stack([strip.reshape(-1, 2), crown.ravel()])
        cells = np.arange(len(pos)).reshape(-1, 4)
        a, b, c, d = (grid.ravel() for grid in (cells[:-1, :-1], cells[:-1, 1:], cells[1:, 1:], cells[1:, :-1]))
        faces = _face_up(pos[:, :2], np.vstack([np.c_[a, b, c], np.c_[a, c, d]]))
        yield Mesh("banqueta", colours[colour_index % len(colours)], pos, pos[:, :2], faces, "KERB")


def _tread(radius, depth):
    """Low-poly ring with a shallow shoulder and visible hollow sidewall."""
    angles = np.linspace(0, 2 * np.pi, 10, endpoint=False)
    unit = np.column_stack([np.cos(angles), np.sin(angles)])
    profile = [(0.94, 0), (1, 0.16), (1, 0.83), (0.92, 1), (0.56, 1), (0.56, 0)]
    pos = np.vstack([np.column_stack([unit * radius * r, np.full(len(unit), depth * h)]) for r, h in profile])
    around = np.arange(len(unit))
    next_corner = np.roll(around, -1)
    bands = []
    for row in range(len(profile)):
        first = row * len(unit)
        second = ((row + 1) % len(profile)) * len(unit)
        bands.append(np.c_[first + around, first + next_corner, second + next_corner])
        bands.append(np.c_[first + around, second + next_corner, second + around])
    return pos, np.vstack(bands)


def _box(group, material, center, size, yaw=0, physics=None):
    pos, uv, faces = box_mesh(center, size, yaw)
    return Mesh(group, material, pos, uv, faces, physics)


def _painted_top(polygon, height, lift, material, group="rayas", physics=None):
    xy, faces = triangulate_polygon(polygon, 0.65)
    z = _ground(height, xy, group) + lift
    return Mesh(group, material, np.column_stack([xy, z]), xy, _face_up(xy, faces), physics)


def _wall_face(line, height, lift, material, group, physics):
    xy = np.asarray(segmentize(line, 0.8).coords, float)[:, :2]
    pos, uv, faces = wall_strip(np.column_stack([xy, _ground(height, xy, group) - 0.05]),
                               lift + 0.05, both=material == "invisible")
    return Mesh(group, material, pos, uv, faces, physics)


def _barrier(proj, item, surface, terrain):
    kind = item.get("type")
    if kind not in ("tyre", "block", "fence", "wall"):
        raise ValueError("Kart barrier type must be tyre, block, fence or wall")
    line = _line(_points(proj, item.get("line"), 2, "barrier line"), "barrier line")
    lift = _number(item.get("height_m"), 0.15, 5.0, "barrier height")
    default_width = {"tyre": 0.57, "block": 0.46, "wall": 0.26, "fence": 0.12}[kind]
    width = _number(item.get("width_m", default_width), 0.08, 1.6, "barrier width")
    outline = orient(line.buffer(width / 2, cap_style="flat", join_style="mitre", mitre_limit=2), 1)
    bounds = (outline.exterior, *outline.interiors)
    height = surface.sampler(outline, terrain)
    if kind == "wall":
        material, = _palette(item, "concrete", False)
        yield _painted_top(outline, height, lift, material, "barreras", "WALL")
        for edge in bounds:
            yield _wall_face(edge, height, lift, material, "barreras", "WALL")
        return

    if kind == "fence":
        material, = _palette(item, STEEL, False)
        count = int(np.ceil(line.length / 2.35))
        posts = _samples(line, np.linspace(0, line.length, count + 1))
        base = _ground(height, posts, "fence posts")
        for xy, z in zip(posts, base):
            yield _box("barreras", material, (*xy, z - 0.05), (width, width, lift + 0.05))
        # Use the surveyed line for rails, even at bends between post centres.
        xy = np.asarray(segmentize(line, 0.8).coords)
        rail_grade = _ground(height, xy, "fence rails")
        for level in (0.25, 0.58, 0.94):
            bottom = np.column_stack([xy, rail_grade + lift * level])
            pos, uv, faces = wall_strip(bottom, 0.025, both=False)
            yield Mesh("barreras", material, np.vstack([pos, pos]), np.vstack([uv, uv]),
                       np.vstack([faces, faces[:, ::-1] + len(pos)]))
        yield _wall_face(line, height, lift, "invisible", "col", "WALL")
        return

    colours = _palette(item, RUBBER if kind == "tyre" else "red_white", True)
    spacing = width if kind == "tyre" else 1.10
    count = max(1, int(np.ceil(line.length / spacing)))
    limits = np.linspace(0, line.length, count + 1)
    midpoints = (limits[1:] + limits[:-1]) / 2
    locations = _samples(line, midpoints)
    base = _ground(height, locations, kind)
    if kind == "tyre":
        layers = max(1, round(lift / 0.20))
        depth = lift / layers
        tread, faces = _tread(width / 2, depth * 0.98)
        for i, (xy, z) in enumerate(zip(locations, base)):
            for layer in range(layers):
                pos = tread + (*xy, z + depth * layer)
                yield Mesh("barreras", colours[i % len(colours)], pos, tread[:, :2], faces)
    else:
        corners = _samples(line, limits)
        delta = np.diff(corners, axis=0)
        for i, (xy, z, direction) in enumerate(zip(locations, base, delta)):
            yaw = float(np.arctan2(direction[1], direction[0]))
            length = float(np.linalg.norm(direction))
            yield _box("barreras", colours[i % len(colours)], (*xy, z - 0.05),
                       (length, width, lift + 0.05), yaw)

    # Give a continuous physical backstop at the barrier's footprint instead of
    # solving thousands of individual tyres or catching a wheel between blocks.
    for edge in bounds:
        yield _wall_face(edge, height, lift, "invisible", "col", "WALL")


def _pole(proj, entry, surface, terrain):
    item = {"position": entry} if isinstance(entry, list) else entry
    if not isinstance(item, dict):
        raise ValueError("Floodlight pole requires a surveyed position")
    x, y = _points(proj, [item.get("position")], 1, "floodlight pole")[0]
    xy = np.array([[x, y]])
    height = _number(item.get("height_m", 8), 2, 24, "floodlight height")
    reach = _number(item.get("range_m", 40), 10, 120, "floodlight range")
    strength = _number(item.get("intensity", 9), 0.1, 30, "floodlight intensity")
    colour = item.get("light_rgb", [242, 234, 220])
    if not isinstance(colour, list) or len(colour) != 3:
        raise ValueError("Floodlight RGB requires three channel values")
    rgb = tuple(_number(c, 0, 255, "floodlight RGB") for c in colour)
    road = surface.sampler(Polygon([(x - 1, y - 1), (x - 1, y + 1), (x + 1, y + 1), (x + 1, y - 1)]), terrain)
    z = _ground(road, xy, "floodlight pole")[0]
    meshes = [
        _box("mobiliario", STEEL, (x, y, z - 0.08), (0.18, 0.18, height + 0.08), physics="WALL"),
        _box("mobiliario", STEEL, (x, y, z + height - 0.14), (0.85, 0.24, 0.14)),
        _box("mobiliario", "lampara", (x, y, z + height - 0.17), (0.67, 0.20, 0.04)),
    ]
    return meshes, ((x, y, z + height - 0.18), (0, 0, -1), rgb, strength, reach)


def _marking(proj, item, surface):
    if ("line" in item) == ("ring" in item):
        raise ValueError("Kart paint needs exactly one surveyed line or ring")
    pattern = item.get("pattern", "solid")
    if pattern not in ("solid", "checkered"):
        raise ValueError("Kart paint pattern must be solid or checkered")
    if "ring" in item:
        xy = _points(proj, item["ring"], 3, "marking ring")
        footprint = Polygon(xy)
    else:
        if pattern == "checkered":
            raise ValueError("Checkered markings need all four surveyed corners")
        line = _line(_points(proj, item["line"], 2, "marking line"), "marking line")
        width = _number(item.get("width_m"), 0.02, 3.0, "marking width")
        footprint = line.buffer(width / 2, cap_style="flat", join_style="mitre", mitre_limit=2)
    if not footprint.is_valid or footprint.area < 1e-4:
        raise ValueError("Invalid kart marking outline")
    height = surface.sampler(footprint, None)
    if pattern == "solid":
        material, = _palette(item, WHITE, False)
        yield _painted_top(footprint, height, 0.01, material)
        return

    if len(xy) != 4 or not np.isclose(footprint.area, footprint.convex_hull.area):
        raise ValueError("Checkered marking must have four ordered convex corners")
    columns, rows = item.get("columns"), item.get("rows")
    if type(columns) is not int or type(rows) is not int or not 1 <= columns <= 100 or not 1 <= rows <= 12:
        raise ValueError("Checkered marking needs observed column and row counts")
    a, b, c, d = xy

    def grid(u, v):
        return (1 - v) * (a + u * (b - a)) + v * (d + u * (c - d))

    for i in range(columns):
        for j in range(rows):
            u0, u1 = i / columns, (i + 1) / columns
            v0, v1 = j / rows, (j + 1) / rows
            cell = Polygon([grid(u0, v0), grid(u1, v0), grid(u1, v1), grid(u0, v1)])
            yield _painted_top(cell, height, 0.01, WHITE if (i + j) % 2 == 0 else "#292827")


def build(scene, proj, terrain, data, *, log=print):
    """Attach reviewed kart detail after road and terrain heights are final."""
    groups = ("kerbs", "barriers", "poles", "markings")
    counts = {}
    for kind in groups:
        entries = data.get(kind, [])
        if not isinstance(entries, list) or (kind != "poles" and not all(isinstance(e, dict) for e in entries)):
            raise ValueError(f"Kart {kind} must be an array of surveyed objects")
        counts[kind] = len(entries)
    if not any(counts.values()):
        return counts

    meshes, lights = [], []
    if counts["kerbs"]:
        asphalt = _RoadSurface(scene, {"KART"})
        for item in data["kerbs"]:
            meshes.extend(_kerb(proj, data, item, asphalt))
    surface = _RoadSurface(scene, {"ROAD", "KART", "PITLANE", "GRAVEL"})
    for item in data.get("barriers", []):
        meshes.extend(_barrier(proj, item, surface, terrain))
    for item in data.get("poles", []):
        pieces, light = _pole(proj, item, surface, terrain)
        meshes.extend(pieces)
        lights.append(light)
    if counts["markings"]:
        asphalt = _RoadSurface(scene, {"ROAD", "KART", "PITLANE"})
        for item in data["markings"]:
            meshes.extend(_marking(proj, item, asphalt))

    for material in {m.material for m in meshes}:
        named = MATERIALS.get(material, material)
        if named not in scene.materials and (not material.startswith("#") or len(material) != 7
                                              or any(c not in "0123456789abcdefABCDEF" for c in material[1:])):
            raise ValueError(f"Unknown kart material {material!r}")
    for mesh in meshes:
        material = _material(scene, mesh.material)
        scene.add(mesh.group, material, mesh.pos, mesh.uv, mesh.faces, phys=mesh.physics)
    scene.lights.extend(lights)
    log("  Kart scenery: " + ", ".join(f"{count} {name}" for name, count in counts.items()))
    return counts
