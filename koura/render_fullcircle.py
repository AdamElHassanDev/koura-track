"""Render route views and flag sky where the 30 m elevation model projects land."""

import argparse
from collections import OrderedDict
from dataclasses import dataclass
from io import BytesIO
import json
import mmap
import os
from pathlib import Path
import re
import struct
import sys

import numpy as np
from numba import njit
from PIL import Image, ImageDraw
from scipy.ndimage import binary_erosion
from shapely.geometry import Point

from verify_background import EDGE_TOLERANCE_M, sample_mesh

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "openlaps"))
from openlaps.geo import LocalProjection


STEP_M = 500
EYE_HEIGHT_M = 1.2
MAX_ROAD_SNAP_M = 8.0
NEAR_M = 0.08
RANGE_M = 3000.0
DEM_STEP_M = 15.0
DEM_MIN_RANGE_M = 1.0
DEM_CHECK_BATCH = 512
TEXTURE_CACHE_BYTES = 256 * 1024**2
ROAD_NAME = re.compile(r"^\d+[A-Z0-9]+_calzada_")
GROUND_NAME = re.compile(r"^(?:\d+[A-Z0-9]+_)?(?:terreno|suelo_fondo|horizonte|calzada|agua)_")
VIEW_AXES = {"north": (2, -1), "east": (0, 1), "south": (2, 1), "west": (0, -1)}
SUN = np.asarray([0.4, 0.8, 0.35], dtype=np.float32)
SUN /= np.linalg.norm(SUN)


@dataclass(frozen=True)
class Mesh:
    name: str
    attributes: dict
    indices: int
    texture: int
    mode: str


class Scene:
    """Map GLB geometry and decode only the textures used in a rendered view."""

    def __init__(self, path, inspect=None):
        self.path = path
        self.inspected = inspect is not None
        settings = json.loads(inspect.read_text()) if self.inspected else {}
        self.settings = {row["name"]: row for row in settings.get("meshes", [])}

    def __enter__(self):
        with self.path.open("rb") as file:
            magic, version, size = struct.unpack("<III", file.read(12))
            length, chunk = struct.unpack("<II", file.read(8))
            if (magic, version, chunk) != (0x46546C67, 2, 0x4E4F534A):
                raise ValueError(f"{self.path} is not a glTF 2 binary scene")
            self.meta = json.loads(file.read(length))
            bin_size, bin_chunk = struct.unpack("<II", file.read(8))
            self.binary = file.tell()
            if bin_chunk != 0x004E4942 or self.binary + bin_size != size:
                raise ValueError(f"{self.path} has an invalid binary mesh buffer")
            self.data = mmap.mmap(file.fileno(), 0, access=mmap.ACCESS_READ)
        self.textures = OrderedDict()
        self.texture_bytes = 0
        records = self._meshes()
        if not records:
            raise ValueError(f"No visible mesh primitives in {self.path}")
        # Alpha-blended graphics are drawn after opaque geometry, as in the fork's renderer.
        records.sort(key=lambda row: row[0].mode == "BLEND")
        meshes, bounds, spheres, lod = zip(*records)
        self.meshes = meshes
        self.ground = np.array([bool(GROUND_NAME.match(mesh.name)) for mesh in meshes])
        self.minimum, self.maximum = np.asarray(bounds, dtype=np.float32).transpose(1, 0, 2)
        self.center = (self.minimum + self.maximum) * 0.5
        self.radius = (self.maximum - self.minimum) * 0.5
        self.sphere = np.asarray(spheres, dtype=np.float32)
        self.lod = np.asarray(lod, dtype=np.float32)
        return self

    def __exit__(self, *exc):
        self.data.close()

    def _meshes(self):
        records = []
        for node in self.meta["nodes"]:
            if "mesh" not in node:
                continue
            name = node["name"]
            setting = self.settings.get(name, {})
            if not (setting.get("rend", True) and setting.get("vis", True)):
                continue
            for part in self.meta["meshes"][node["mesh"]]["primitives"]:
                attrib = part["attributes"]
                mat = self.meta["materials"][part["material"]]
                texture = mat["pbrMetallicRoughness"]["baseColorTexture"]["index"]
                source = self.meta["textures"][texture]["source"]
                bounds = self.meta["accessors"][attrib["POSITION"]]
                lo, hi = bounds["min"], bounds["max"]
                sphere = setting.get("bs", [(a + b) / 2 for a, b in zip(lo, hi)])[:3]
                records.append((Mesh(name, attrib, part["indices"], source, mat.get("alphaMode", "OPAQUE")),
                                (lo, hi), sphere, setting.get("lod", [0, 0])[1]))
        return records

    def accessor(self, key):
        item = self.meta["accessors"][key]
        view = self.meta["bufferViews"][item["bufferView"]]
        dtype = {5123: "<u2", 5125: "<u4", 5126: "<f4"}[item["componentType"]]
        width = {"SCALAR": 1, "VEC2": 2, "VEC3": 3}[item["type"]]
        offset = self.binary + view.get("byteOffset", 0) + item.get("byteOffset", 0)
        return np.ndarray((item["count"], width), dtype=dtype, buffer=self.data, offset=offset)

    def texture(self, key, transparent):
        cache_key = (key, transparent)
        if cache_key in self.textures:
            self.textures.move_to_end(cache_key)
            return self.textures[cache_key]
        item = self.meta["images"][key]
        view = self.meta["bufferViews"][item["bufferView"]]
        begin = self.binary + view.get("byteOffset", 0)
        with Image.open(BytesIO(self.data[begin:begin + view["byteLength"]])) as image:
            colour = np.asarray(image.convert("RGBA" if transparent else "RGB"))
        if transparent:
            colour = colour.astype(np.float32) / 255.0
        while self.textures and self.texture_bytes + colour.nbytes > TEXTURE_CACHE_BYTES:
            _, dropped = self.textures.popitem(last=False)
            self.texture_bytes -= dropped.nbytes
        if colour.nbytes <= TEXTURE_CACHE_BYTES:
            self.textures[cache_key] = colour
            self.texture_bytes += colour.nbytes
        return colour

    def road_position(self, xz):
        on_road = []
        nearby = np.flatnonzero(
            (self.minimum[:, (0, 2)] - MAX_ROAD_SNAP_M <= xz).all(axis=1)
            & (self.maximum[:, (0, 2)] + MAX_ROAD_SNAP_M >= xz).all(axis=1)
        )
        for index in nearby:
            mesh = self.meshes[index]
            if ROAD_NAME.match(mesh.name):
                pos = self.accessor(mesh.attributes["POSITION"])
                faces = self.accessor(mesh.indices).reshape(-1, 3)
                on_road.append(nearest_road(pos, faces, xz))
        if not on_road:
            return None
        offset2, level, x, z = min(on_road, key=lambda item: (item[0], -item[1]))
        if offset2 > MAX_ROAD_SNAP_M ** 2:
            return None
        return np.array([x, level + EYE_HEIGHT_M, z], dtype=np.float32), float(np.sqrt(offset2))

    def visible(self, eye, axis, sign, width, height):
        side = 2 - axis
        center = self.center - eye
        far = center[:, axis] * sign + self.radius[:, axis]
        # A 90 degree view has horizontal tangent one. Preserve the 3 km test
        # surroundings and the built distant horizon for the supporting images.
        visible = ((far > NEAR_M)
                   & (np.abs(center[:, side]) - self.radius[:, side] <= far)
                   & (np.abs(center[:, 1]) - self.radius[:, 1] <= far * height / width))
        distance = np.linalg.norm(self.sphere - eye, axis=1)
        visible &= (self.lod == 0) | (distance <= self.lod)
        return np.flatnonzero(visible)

    def ground_levels(self, eye, direction, width, height, points):
        """Sample the highest rendered ground under the reference hit coordinates."""
        result = np.full(len(points), np.nan)
        axis, sign = VIEW_AXES[direction]
        visible = self.visible(eye, axis, sign, width, height)
        for index in visible[self.ground[visible]]:
            lower = self.minimum[index, (0, 2)] - EDGE_TOLERANCE_M
            upper = self.maximum[index, (0, 2)] + EDGE_TOLERANCE_M
            inside = ((points >= lower) & (points <= upper)).all(axis=1)
            if not inside.any():
                continue
            mesh = self.meshes[index]
            xyz = self.accessor(mesh.attributes["POSITION"])[:, (0, 2, 1)].astype(np.float64)
            faces = self.accessor(mesh.indices).reshape(-1, 3)
            levels = sample_mesh(xyz[faces], points[inside])
            result[inside] = np.fmax(result[inside], levels)
        return result

    def draw(self, eye, direction, width, height):
        axis, sign = VIEW_AXES[direction]
        side, right = 2 - axis, sign if axis == 0 else -sign
        depth = np.full((height, width), 1e18)
        sky = np.linspace(0.55, 0.85, height)[:, None]
        colour = np.empty((height, width, 3))
        colour[:, :, 0], colour[:, :, 1], colour[:, :, 2] = sky * 0.75, sky * 0.85, 0.95
        for index in self.visible(eye, axis, sign, width, height):
            mesh = self.meshes[index]
            attrib = mesh.attributes
            pos = self.accessor(attrib["POSITION"])
            camera = np.column_stack(((pos[:, side] - eye[side]) * right,
                                      pos[:, 1] - eye[1], (pos[:, axis] - eye[axis]) * sign))
            front = camera[:, 2] >= NEAR_M
            if not front.any():
                continue
            uv = self.accessor(attrib["TEXCOORD_0"])
            faces = self.accessor(mesh.indices).reshape(-1, 3)
            alpha, blend = mesh.mode == "MASK", mesh.mode == "BLEND"
            texture = self.texture(mesh.texture, alpha or blend)
            normals = self.accessor(attrib["NORMAL"])
            shade = 0.45 + 0.65 * np.clip(normals @ SUN, 0.0, 1.0)
            if alpha:
                shade.fill(0.95)
            if not (alpha or blend):
                shade /= 255.0
            if front.all():
                draw_mesh(camera, uv, shade, faces, texture, alpha, blend, depth, colour)
                continue
            count = front[faces].sum(axis=1)
            draw_mesh(camera, uv, shade, faces[count == 3], texture, alpha, blend, depth, colour)
            crossing = faces[(count > 0) & (count < 3)]
            if len(crossing):
                xyz, cropped_uv, light, cropped_faces = clip_near(camera, uv, shade, crossing)
                draw_mesh(xyz, cropped_uv, light, cropped_faces, texture, alpha, blend, depth, colour)
        fog = np.clip((depth - 900) / 9000, 0, 0.45)
        fog[depth > 1e17] = 0
        colour = colour * (1.0 - fog[:, :, None]) + np.array([0.75, 0.82, 0.92]) * fog[:, :, None]
        return Image.fromarray((np.clip(colour, 0, 1) * 255).astype(np.uint8)), depth


@njit(cache=True)
def nearest_road(points, faces, xz):
    best, height, snap_x, snap_z = np.inf, -np.inf, xz[0], xz[1]
    for face in faces:
        a, b, c = points[face[0]], points[face[1]], points[face[2]]
        ux, uz = b[0] - a[0], b[2] - a[2]
        vx, vz = c[0] - a[0], c[2] - a[2]
        det = ux * vz - uz * vx
        if abs(det) < 1e-9:
            continue
        px, pz = xz[0] - a[0], xz[1] - a[2]
        u, v = (px * vz - pz * vx) / det, (ux * pz - uz * px) / det
        if u >= -1e-6 and v >= -1e-6 and u + v <= 1.0 + 1e-6:
            z = a[1] + u * (b[1] - a[1]) + v * (c[1] - a[1])
            if best > 0.0 or z > height:
                best, height, snap_x, snap_z = 0.0, z, xz[0], xz[1]
        elif best > 0.0:
            for j in range(3):
                p, q = points[face[j]], points[face[(j + 1) % 3]]
                dx, dz = q[0] - p[0], q[2] - p[2]
                den = dx * dx + dz * dz
                if den <= 1e-12:
                    continue
                t = min(1.0, max(0.0, ((xz[0] - p[0]) * dx + (xz[1] - p[2]) * dz) / den))
                x, z = p[0] + t * dx, p[2] + t * dz
                distance = (x - xz[0]) ** 2 + (z - xz[1]) ** 2
                if distance < best:
                    best, height, snap_x, snap_z = distance, p[1] + t * (q[1] - p[1]), x, z
    return best, height, snap_x, snap_z


@njit(cache=True)
def clip_near(xyz, uv, shade, faces):
    vertices = np.empty((len(faces) * 4, 3), dtype=np.float32)
    tex = np.empty((len(vertices), 2), dtype=np.float32)
    light = np.empty(len(vertices), dtype=np.float32)
    triangles = np.empty((len(faces) * 2, 3), dtype=np.int32)
    end, out = 0, 0
    for face in faces:
        start = end
        for j in range(3):
            a, b = face[(j + 2) % 3], face[j]
            front_a, front_b = xyz[a, 2] >= NEAR_M, xyz[b, 2] >= NEAR_M
            if front_a != front_b:
                # Adjacent triangles traverse the same edge in opposite
                # directions. Start at the front vertex on both sides.
                near, far = (a, b) if front_a else (b, a)
                t = (NEAR_M - xyz[near, 2]) / (xyz[far, 2] - xyz[near, 2])
                vertices[end] = xyz[near] + t * (xyz[far] - xyz[near])
                vertices[end, 2] = NEAR_M
                tex[end] = uv[near] + t * (uv[far] - uv[near])
                light[end] = shade[near] + t * (shade[far] - shade[near])
                end += 1
            if front_b:
                vertices[end], tex[end], light[end] = xyz[b], uv[b], shade[b]
                end += 1
        for k in range(start + 1, end - 1):
            triangles[out, 0], triangles[out, 1], triangles[out, 2] = start, k, k + 1
            out += 1
    return vertices[:end], tex[:end], light[:end], triangles[:out]


@njit(cache=True)
def raster(x, y, z, uv, shade, faces, texture, alpha, blend, depth, colour):
    """Draw with the fork's perspective, textures and depth, using symmetric edge tests."""
    height, width = depth.shape
    th, tw = texture.shape[:2]
    for a, b, c in faces:
        x0, x1, x2 = np.float64(x[a]), np.float64(x[b]), np.float64(x[c])
        y0, y1, y2 = np.float64(y[a]), np.float64(y[b]), np.float64(y[c])
        area = (x1 - x0) * (y2 - y0) - (x2 - x0) * (y1 - y0)
        if abs(area) < 1e-9:
            continue
        left = max(0, int(np.floor(min(x0, x1, x2))))
        right = min(width - 1, int(np.floor(max(x0, x1, x2))))
        top = max(0, int(np.floor(min(y0, y1, y2))))
        bottom = min(height - 1, int(np.floor(max(y0, y1, y2))))
        iz0, iz1, iz2 = 1.0 / z[a], 1.0 / z[b], 1.0 / z[c]
        for py in range(top, bottom + 1):
            dy0, dy1, dy2 = y0 - py - 0.5, y1 - py - 0.5, y2 - py - 0.5
            for px in range(left, right + 1):
                dx0, dx1, dx2 = x0 - px - 0.5, x1 - px - 0.5, x2 - px - 0.5
                # Computing all three as edge products avoids subtraction
                # rounding that can open a crack between two shared edges.
                w0 = (dx1 * dy2 - dx2 * dy1) / area
                w1 = (dx2 * dy0 - dx0 * dy2) / area
                w2 = (dx0 * dy1 - dx1 * dy0) / area
                if min(w0, w1, w2) < -1e-10:
                    continue
                a0, a1, a2 = w0 * iz0, w1 * iz1, w2 * iz2
                distance = 1.0 / (a0 + a1 + a2)
                if distance >= depth[py, px]:
                    continue
                u = (a0 * uv[a, 0] + a1 * uv[b, 0] + a2 * uv[c, 0]) * distance
                v = (a0 * uv[a, 1] + a1 * uv[b, 1] + a2 * uv[c, 1]) * distance
                texel = texture[int((v - np.floor(v)) * th) % th, int((u - np.floor(u)) * tw) % tw]
                if alpha and texel[3] < 0.5:
                    continue
                light = w0 * shade[a] + w1 * shade[b] + w2 * shade[c]
                if blend:
                    opacity = texel[3]
                    for channel in range(3):
                        colour[py, px, channel] = (colour[py, px, channel] * (1.0 - opacity)
                                                    + texel[channel] * light * opacity)
                else:
                    depth[py, px] = distance
                    for channel in range(3):
                        colour[py, px, channel] = texel[channel] * light


def draw_mesh(xyz, uv, shade, faces, texture, alpha, blend, depth, colour):
    height, width = depth.shape
    if not len(faces):
        return
    scale = (width / 2.0) / np.maximum(xyz[:, 2], NEAR_M)
    x = width / 2.0 + xyz[:, 0] * scale
    y = height / 2.0 - xyz[:, 1] * scale
    raster(x, y, xyz[:, 2], uv, shade, faces, texture, alpha, blend, depth, colour)


def dem_rays(dem, proj, eye, direction, width, columns):
    axis, sign = VIEW_AXES[direction]
    right = sign if axis == 0 else -sign
    tangent = (2 * (np.asarray(columns) + 0.5) / width - 1)[:, None]
    ray = np.r_[np.arange(DEM_MIN_RANGE_M, RANGE_M, DEM_STEP_M), RANGE_M][None, :]
    forward = ray / np.sqrt(1.0 + tangent * tangent)
    side = forward * tangent * right
    x, z = (forward * sign, side) if axis == 0 else (side, forward * sign)
    x, z = x + eye[0], z + eye[2]
    model = dem.sample(proj, x, -z, order=1)
    # Align the reference viewpoint to the local model surface when a cell
    # contains treetops or buildings above the real road camera.
    reference_eye = max(float(eye[1]), float(dem.sample(proj, eye[0], -eye[2])) + EYE_HEIGHT_M)
    return x, z, forward, model, reference_eye


def dem_pixels(dem, proj, eye, direction, width, height):
    """Project each valid land segment into its screen column."""
    _, _, forward, model, reference_eye = dem_rays(dem, proj, eye, direction, width, np.arange(width))
    land = np.isfinite(model) & (model > 0)
    row = height / 2.0 - (model - reference_eye) * (width / 2.0) / forward
    low, high = np.minimum(row[:, :-1], row[:, 1:]), np.maximum(row[:, :-1], row[:, 1:])
    start = np.clip(np.ceil(np.nan_to_num(low) - 0.5), 0, height).astype(int)
    end = np.clip(np.floor(np.nan_to_num(high) - 0.5) + 1, 0, height).astype(int)
    columns, segments = np.where(land[:, :-1] & land[:, 1:] & (end > start))
    lines = np.zeros((width, height + 1), dtype=np.int32)
    np.add.at(lines, (columns, start[columns, segments]), 1)
    np.add.at(lines, (columns, end[columns, segments]), -1)
    return (np.cumsum(lines[:, :-1], axis=1) > 0).T


def skyline_disagreements(scene, dem, proj, eye, direction, depth, missing):
    """Resolve skyline-only flags using a vertical ray into the rendered mesh.

    A flag is a height disagreement only if the same XY as the first DEM
    intersection is covered by active ground, its actual elevation projects
    below the flagged pixel, and geometry is rendered at that lower projection.
    Terrain silhouettes can move several pixels when a 30 m DEM averages a cut.
    """
    height = depth.shape[0]
    hit = depth < 1e17
    first_hit = np.where(hit.any(axis=0), hit.argmax(axis=0), -1)
    row, col = np.where(missing & (np.arange(height)[:, None] < first_hit))
    resolved = np.zeros_like(missing)
    maximum = None
    for begin in range(0, len(row), DEM_CHECK_BATCH):
        batch = slice(begin, begin + DEM_CHECK_BATCH)
        confirmed, difference = match_skyline_rays(scene, dem, proj, eye, direction, depth, row[batch], col[batch])
        resolved[row[batch][confirmed], col[batch][confirmed]] = True
        if difference is not None:
            maximum = max(maximum or 0.0, difference)
    return resolved, maximum


def match_skyline_rays(scene, dem, proj, eye, direction, depth, row, col):
    height, width = depth.shape
    matched = np.zeros(len(row), dtype=bool)
    fx = width / 2
    x, z, forward, model, ref_eye = dem_rays(dem, proj, eye, direction, width, col)
    offset = model - (ref_eye + ((height / 2 - row - 0.5) / fx)[:, None] * forward)
    land = np.isfinite(model) & (model > 0)
    inside = land[:, 1:] & land[:, :-1]
    crossing = (offset[:, 1:] * offset[:, :-1] <= 0) & (offset[:, 1:] != offset[:, :-1]) & inside
    rays = np.flatnonzero(crossing.any(axis=1))
    if not len(rays):
        return matched, None
    at = crossing[rays].argmax(axis=1)
    fraction = offset[rays, at] / (offset[rays, at] - offset[rays, at + 1])

    def interpolate(values):
        start, end = values[rays, at], values[rays, at + 1]
        return start + fraction * (end - start)

    xy = np.column_stack([interpolate(x), interpolate(z)])
    distance = interpolate(forward)
    ground = scene.ground_levels(eye, direction, width, height, xy)
    projected = height / 2 - (ground - eye[1]) * fx / distance
    lower = np.isfinite(projected) & (projected > row[rays] + 0.5) & (projected < height)
    tests = np.flatnonzero(lower)
    if not len(tests):
        return matched, None
    screen_rows = np.clip(np.floor(projected[tests]).astype(int)[:, None] + [-1, 0, 1], 0, height - 1)
    screen_cols = col[rays[tests], None]
    # Adjacent pixel centres have different ray directions. Accept the nearest
    # depth within one projected pixel at this range, or a closer occluder.
    visible = depth[screen_rows, screen_cols].min(axis=1) <= distance[tests] * (1 + 1 / fx)
    confirmed = tests[visible]
    matched[rays[confirmed]] = True
    maximum = None
    if len(confirmed):
        maximum = float(np.abs(interpolate(model)[confirmed] - ground[confirmed]).max())
    return matched, maximum


def station_locations(routes, proj, names):
    for name in names:
        route = routes[name]
        lat, lon = np.asarray(route["polyline"], dtype=float).T
        x, y = proj.to_local(lon, lat)
        points = np.column_stack([x, -y])
        if route.get("closed") and not np.array_equal(points[0], points[-1]):
            points = np.vstack((points, points[0]))
        chainage = np.r_[0.0, np.cumsum(np.linalg.norm(np.diff(points, axis=0), axis=1))]
        keep = np.r_[True, np.diff(chainage) > 1e-6]
        chainage, points = chainage[keep], points[keep]
        distance = np.arange(0.0, chainage[-1], STEP_M)
        if not route.get("closed"):
            distance = np.append(distance, chainage[-1])
        samples = np.column_stack([np.interp(distance, chainage, col) for col in points.T])
        for metres, xz in zip(distance, samples):
            yield name, float(metres), xz


def kn5_inspection(glb, chosen):
    if chosen is not None:
        return chosen
    default = glb.parent / "verify" / "kn5.json"
    return default if default.is_file() else None


def evidence_pairs(baseline, comparison, samples, output, width, height):
    candidates = [sample for sample in samples if sample[0] == "loop"] or samples
    horizontal = [0, 2]
    center = np.mean([eye[horizontal] for _, _, eye in candidates], axis=0)
    for i in np.unique(np.linspace(0, len(candidates), 4, endpoint=False).astype(int)):
        name, distance, eye = candidates[i]
        ix = int(np.argmax(np.abs(center - eye[horizontal])))
        axis = horizontal[ix]
        sign = 1 if center[ix] >= eye[axis] else -1
        direction = next(label for label, axes in VIEW_AXES.items() if axes == (axis, sign))
        before, _ = baseline.draw(eye, direction, width, height)
        after, _ = comparison.draw(eye, direction, width, height)
        pair = Image.new("RGB", (width * 2, height + 24), "#15171c")
        pair.paste(before, (0, 24))
        pair.paste(after, (width, 24))
        caption = f"{name} {distance / 1000:.2f} km, {direction}"
        pen = ImageDraw.Draw(pair)
        pen.text((8, 6), f"Before   {caption}", fill="white")
        pen.text((width + 8, 6), f"After   {caption}", fill="white")
        pair.save(output / f"pair-{name}-{round(distance):05d}-{direction}.jpg", quality=92)


def verify_glb(args, proj, routes, names, complete_for_stage, dem, detailed_scope=None):
    records, samples, excluded = [], [], []
    with Scene(args.glb, kn5_inspection(args.glb, args.inspect)) as scene:
        for name, distance, xz in station_locations(routes, proj, names):
            inside = proj.xmin <= xz[0] <= proj.xmax and proj.ymin <= -xz[1] <= proj.ymax
            if not inside and args.stage != "S2":
                continue  # The short trial stages deliberately clip their test routes.
            if detailed_scope is not None and not detailed_scope.covers(Point(xz[0], -xz[1])):
                excluded.append({"route": name, "metres": round(distance, 2),
                                 "reason": "outside the bridge trial detailed area"})
                continue
            position = scene.road_position(xz) if inside else None
            station = {"route": name, "metres": round(distance, 2)}
            if position is None:
                lon, lat = proj.to_lonlat(xz[0], -xz[1])
                status = "missing_road" if inside else "outside_stage"
                station.update(latitude=float(lat), longitude=float(lon), status=status)
            else:
                eye, snap = position
                lon, lat = proj.to_lonlat(eye[0], -eye[2])
                station.update(latitude=float(lat), longitude=float(lon), road_snap_m=round(snap, 3),
                               status="pass", views={})
                samples.append((name, distance, eye))
                for direction in VIEW_AXES:
                    frame, depth = scene.draw(eye, direction, args.width, args.height)
                    reference = dem_pixels(dem, proj, eye, direction, args.width, args.height)
                    sky = depth > 1e17
                    raw_missing = reference & sky
                    # Ignore the one-pixel reference fringe at the 30 m model
                    # silhouette. Keep its raw count and flag all interior holes.
                    missing = binary_erosion(reference, structure=np.ones((3, 3))) & sky
                    disagreement, model_difference = skyline_disagreements(
                        scene, dem, proj, eye, direction, depth, missing
                    )
                    hard_missing = missing & ~disagreement
                    label = f"{name}-{round(distance):05d}-{direction}"
                    file = f"{label}.jpg"
                    frame.save(args.out / file, quality=88)
                    if hard_missing.any() or disagreement.any():
                        image = np.array(frame)
                        image[disagreement] = [255, 185, 30]
                        image[hard_missing] = [255, 55, 200]
                        Image.fromarray(image).save(args.out / f"{label}-diagnostic.png")
                    if hard_missing.any():
                        station["status"] = "ground_gap"
                    station["views"][direction] = {
                        "image": file,
                        "reference_land_pixels": int(reference.sum()),
                        "raw_missing_pixels": int(raw_missing.sum()),
                        "interior_missing_pixels": int(missing.sum()),
                        "dem_skyline_disagreement_pixels": int(disagreement.sum()),
                        "unresolved_missing_pixels": int(hard_missing.sum()),
                        "maximum_dem_mesh_difference_m": model_difference,
                    }
            records.append(station)
            print(f"{name} {distance / 1000:.3f} km {station['status']}", flush=True)
        if args.before and samples:
            with Scene(args.before, kn5_inspection(args.before, args.before_inspect)) as baseline:
                evidence_pairs(baseline, scene, samples, args.out, max(720, args.width), max(405, args.height))
    good = bool(records) and all(row["status"] == "pass" for row in records)
    status = "fail"
    if good:
        status = "pass" if complete_for_stage else "incomplete"
    return {
        "status": status,
        "complete_for_stage": complete_for_stage,
        "inspection_lod_applied": scene.inspected,
        "distance_m": RANGE_M,
        "reference_minimum_distance_m": DEM_MIN_RANGE_M,
        "reference_step_m": DEM_STEP_M,
        "reference_erosion_pixels": 1,
        "reference_eye": "Higher of exported camera and local Copernicus surface plus 1.2 m",
        "camera_height_m": EYE_HEIGHT_M,
        "fov_horizontal_degrees": 90,
        "stations": records,
        "excluded_trial_stations": excluded,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("glb", type=Path)
    parser.add_argument("--out", type=Path, default=ROOT / "out" / "S2" / "renders" / "fullcircle")
    parser.add_argument("--stage", default="S2")
    parser.add_argument("--route", action="append", help="Limit a trial run to this route. Repeat as needed.")
    parser.add_argument("--inspect", type=Path, help="Optional KN5 inspector JSON for visible meshes and draw distance")
    parser.add_argument("--before", type=Path, help="Baseline GLB for matching before and after images")
    parser.add_argument("--before-inspect", type=Path, help="Optional baseline KN5 inspector JSON")
    parser.add_argument("--width", type=int, default=384)
    parser.add_argument("--height", type=int, default=216)
    args = parser.parse_args()
    if args.width < 32 or args.height < 32:
        parser.error("Render dimensions must be at least 32 pixels")

    os.environ.setdefault("OPENLAPS_CACHE", str(ROOT / "cache"))
    from openlaps.sources import rasters

    zone = json.loads((ROOT / "handoff" / "inputs" / "zone.json").read_text(encoding="utf-8"))
    origin = zone["origin"]
    stage = zone["stages"][args.stage]
    frame = stage["expected"]["rect_local_m"]
    proj = LocalProjection.marco(origin["lat"], origin["lon"], frame)
    routes = zone["routes"]
    required_routes = list(routes) if args.stage == "S2" else stage.get("must_contain_routes", list(routes))
    names = list(dict.fromkeys(args.route)) if args.route else required_routes
    if set(names).difference(routes):
        parser.error("Unknown named route")
    dem = rasters.copernicus_dem(proj.bbox().padded(5000))
    args.out.mkdir(exist_ok=True, parents=True)
    detailed_scope = None
    if args.stage == "B":
        from stages import stage_zone

        detailed_scope = stage_zone(zone, args.stage, proj)
    report = verify_glb(args, proj, routes, names, set(names) == set(required_routes), dem, detailed_scope)
    (args.out / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    gaps = sum(row["status"] == "ground_gap" for row in report["stations"])
    missing = sum(row["status"] == "missing_road" for row in report["stations"])
    outside = sum(row["status"] == "outside_stage" for row in report["stations"])
    views = sum(len(row.get("views", {})) for row in report["stations"])
    print(f"{report['status']}: {views} views, {gaps} stations with ground gaps, "
          f"{missing} stations without road, {outside} stations outside the stage")
    return int(report["status"] == "fail")


if __name__ == "__main__":
    raise SystemExit(main())
