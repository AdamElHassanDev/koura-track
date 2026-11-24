"""Prepare and write the standalone, timed Karting Mania layout.

Inputs are geographical, in WGS84 latitude/longitude order. Supply the observed
`direction` (clockwise or anticlockwise), `start_line` ([lat, lon] at its centre),
`grid` and `pit_boxes` (numbered [lat, lon] positions), and `hotlap_start`
([lat, lon] before the last corner). The `centreline` and `pit_lane` entries
are ordered [lat, lon, full_width_m] rows. The pit lane must be ordered in
travel direction. The centreline is reoriented to match the surveyed direction.

Optional replay `cameras` have a `position` and `look_at` in latitude/longitude
and a relative `height_m`. Without these, replay views follow three portions
of the circuit. The mesh sample callbacks provide all heights at build time,
in local east/north/up units. No absolute height goes into the override file.
"""
from __future__ import annotations

from configparser import ConfigParser
from dataclasses import dataclass
import io
import json
from pathlib import Path
import re

import numpy as np
from openlaps import export_ac
from shapely.geometry import LinearRing, LineString


TRACK_ID = "koura_karting_mania"
AI_SPACING_M = 5.0
AI_LIFT_M = 0.4
SPAWN_LIFT_M = 0.3
TIMING_LIFT_M = 0.5
MARKER = re.compile(r"AC_(?:(?:START|PIT|HOTLAP_START)_\d+|(?:TIME_\d+|AB_START|AB_FINISH)_[LR])$")


def _local(proj, rows, name, columns, minimum):
    if not isinstance(rows, (list, tuple)) or len(rows) < minimum:
        raise ValueError(f"{name} requires at least {minimum} position(s)")
    try:
        values = np.asarray(rows, dtype=float)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{name} requires numeric latitude/longitude rows") from error
    if (
        values.ndim != 2 or values.shape[1] != columns
        or not np.isfinite(values).all() or np.any(np.abs(values[:, 0]) > 90)
        or np.any(np.abs(values[:, 1]) > 180)
    ):
        raise ValueError(f"Invalid latitude/longitude or row shape in {name}")
    x, y = proj.to_local(values[:, 1], values[:, 0])
    xy = np.column_stack((x, y))
    if not np.isfinite(xy).all():
        raise ValueError(f"{name} contains a point outside the local projection")
    return xy, values[:, 2:]


def _lift(xy, height_at, offset, label):
    z = np.asarray(height_at(xy), dtype=float)
    if z.shape != (len(xy),) or not np.isfinite(z).all():
        raise ValueError(f"{label} has a point without a built surface below it")
    return np.column_stack((xy, z + offset))


@dataclass(frozen=True)
class _Line:
    xy: np.ndarray
    half_width: np.ndarray
    distances: np.ndarray
    closed: bool

    @classmethod
    def from_points(cls, xy, half_width, name, closed=False):
        if np.any(half_width <= 0):
            raise ValueError(f"{name} widths must be positive")
        if closed:
            if np.linalg.norm(xy[0] - xy[-1]) <= 0.001:
                if not np.isclose(half_width[0], half_width[-1], atol=0.001, rtol=0):
                    raise ValueError(f"{name} has different widths at its duplicate end")
                xy, half_width = xy[:-1], half_width[:-1]
            xy = np.vstack((xy, xy[0]))
            half_width = np.r_[half_width, half_width[0]]
        adjacent = np.linalg.norm(np.diff(xy, axis=0), axis=1)
        if np.any(adjacent < 0.001):
            raise ValueError(f"{name} has repeated neighbouring points")
        if not LineString(xy).is_simple:
            raise ValueError(f"{name} crosses itself")
        return cls(xy, half_width, np.r_[0.0, adjacent.cumsum()], closed)

    @property
    def length(self):
        return self.distances[-1]

    def sample(self, distance):
        return (
            np.stack([np.interp(distance, self.distances, axis) for axis in self.xy.T], axis=-1),
            np.interp(distance, self.distances, self.half_width),
        )

    def tangent(self, distance):
        nearby = np.asarray(distance)[..., None] + [-1.0, 1.0]
        if self.closed:
            nearby %= self.length
        ends, _ = self.sample(nearby)
        direction = ends[..., 1, :] - ends[..., 0, :]
        norms = np.linalg.norm(direction, axis=-1, keepdims=True)
        if (norms < 0.001).any():
            raise ValueError("Unresolved travel direction on the measured path")
        return direction / norms

    def project(self, xy):
        delta = np.diff(self.xy, axis=0)
        relative = xy[:, None, :] - self.xy[:-1]
        length = np.diff(self.distances)
        fraction = np.clip(np.sum(relative * delta, axis=-1) / (length * length), 0.0, 1.0)
        residual = relative - delta * fraction[..., None]
        nearest = np.argmin(np.sum(residual * residual, axis=-1), axis=1)
        rows = np.arange(len(xy))
        return (
            self.distances[nearest] + length[nearest] * fraction[rows, nearest],
            np.linalg.norm(residual[rows, nearest], axis=-1),
        )

    def station_of(self, xy, label):
        distance, offset = self.project(xy)
        _, half_width = self.sample(distance)
        if np.any(offset > half_width):
            raise ValueError(f"{label} is outside its surveyed lane")
        return distance

    def from_start(self, station):
        # Insert the surveyed crossing as point zero, without changing the path.
        interior = self.distances[:-1]
        offset = (interior - station) % self.length
        offsets = np.r_[0.0, np.sort(offset[(offset > 0.001) & (offset < self.length - 0.001)])]
        xy, widths = self.sample((offsets + station) % self.length)
        return _Line.from_points(xy, widths, "start-relative centreline", closed=True)


@dataclass(frozen=True)
class KartLayout:
    """Runtime layout data. Arrays here use local east/north/up coordinates."""

    route: np.ndarray
    half_widths: np.ndarray
    fast_lane: np.ndarray
    fast_lane_half_widths: np.ndarray
    pit_lane: np.ndarray
    pit_lane_half_widths: np.ndarray
    pitboxes: int
    length_m: float


def _read_trace(data, key, proj, *, direction=None):
    closed = direction is not None
    xy, widths = _local(proj, data.get(key), key, columns=3, minimum=3)
    if closed:
        # Closed circuits can be supplied with or without a repeated endpoint.
        ccw = LinearRing(xy).is_ccw
        if ccw != (direction == "anticlockwise"):
            xy, widths = xy[::-1], widths[::-1]
    return _Line.from_points(xy, widths[:, 0] / 2.0, key, closed)


def _spawn(path, xy, surface, prefix):
    direction = path.tangent(path.station_of(xy, prefix))
    points = _lift(xy, surface, SPAWN_LIFT_M, prefix)
    return [
        (f"{prefix}_{i}", point, forward)
        for i, (point, forward) in enumerate(zip(points, direction))
    ]


def _timing_gate(path, station, sector, surface):
    centre, half_width = path.sample(station)
    forward = path.tangent(station)
    left = np.array([-forward[1], forward[0]])
    edges = centre + np.array([[1], [-1]]) * left * half_width
    midpoint = _lift(centre[None], surface, TIMING_LIFT_M, "timing line")[0]
    # The endpoints are at the edges. A sample there can hit the verge if the
    # edge and its float32 rendering differ, so use the paired centre height.
    points = np.column_stack((edges, np.repeat(midpoint[2], 2)))
    return [(f"AC_TIME_{sector}_{side}", point, forward) for side, point in zip("LR", points)]


def _camera_views(proj, data, path, road_height, terrain_height):
    explicit = data.get("cameras")
    if explicit is None:
        stations = (np.arange(3) + 0.5) * path.length / 3
        near, widths = path.sample(stations)
        forward = path.tangent(stations)
        outside = np.column_stack((forward[:, 1], -forward[:, 0]))
        positions = near + outside * (widths + 5.0)[:, None]
        targets = near
        if terrain_height is None:
            heights = _lift(near, road_height, 6.0, "replay camera")[:, 2]
        else:
            heights = _lift(positions, terrain_height, 6.0, "replay camera")[:, 2]
    else:
        if not isinstance(explicit, list) or len(explicit) < 3 or not all(isinstance(r, dict) for r in explicit):
            raise ValueError("Supply at least three replay camera objects")
        positions, _ = _local(proj, [r.get("position") for r in explicit], "cameras", 2, 3)
        targets, _ = _local(proj, [r.get("look_at") for r in explicit], "camera targets", 2, 3)
        offsets = np.asarray([r.get("height_m", 6.0) for r in explicit], dtype=float)
        if not np.isfinite(offsets).all() or np.any(offsets <= 0):
            raise ValueError("Replay cameras require positive relative heights")
        if terrain_height is None:
            nearest, _ = path.project(positions)
            anchors, _ = path.sample(nearest)
            heights = _lift(anchors, road_height, offsets, "replay camera")[:, 2]
        else:
            heights = _lift(positions, terrain_height, offsets, "replay camera")[:, 2]
    eyes = np.column_stack((positions, heights))
    aim = _lift(targets, road_height, 0.5, "replay camera target")
    if np.any(np.linalg.norm(eyes[:, :2] - aim[:, :2], axis=1) < 0.01):
        raise ValueError("Replay camera position and target must differ horizontally")
    return [(eye, target, i / len(eyes), (i + 1) / len(eyes))
            for i, (eye, target) in enumerate(zip(eyes, aim))]


def _ai_line(path, surface):
    count = max(3, int(round(path.length / AI_SPACING_M)) + 1)
    xy, width = path.sample(np.linspace(0.0, path.length, count))
    return _lift(xy, surface, AI_LIFT_M, "AI line"), width


def prepare_layout(scene, proj, data, surface_height, terrain_height=None):
    """Put surveyed timing and spawn dummies on the built surfaces before export.

    `surface_height` receives a NumPy array of local east/north points and
    returns one elevation per point (NaN for an uncovered point). It must see
    the finished racing and pit surfaces. `terrain_height` has the same
    signature. The caller should pass the game-visible terrain sampler.
    """
    if not isinstance(data, dict) or data.get("closed") is not True:
        raise ValueError("A timed Karting Mania layout requires a closed trace")
    direction = data.get("direction")
    if direction not in ("clockwise", "anticlockwise"):
        raise ValueError("Karting Mania needs an observed clockwise or anticlockwise direction")
    main = _read_trace(data, "centreline", proj, direction=direction)
    pit = _read_trace(data, "pit_lane", proj)
    start, _ = _local(proj, [data.get("start_line")], "start_line", 2, 1)
    main = main.from_start(main.station_of(start, "start_line")[0])
    # Both pit ends must join the racing lane; overlapping road and pit
    # half-widths demonstrate a plan-view connection, independent of heights.
    near, offset = main.project(pit.xy[[0, -1]])
    _, main_width = main.sample(near)
    if np.any(offset > main_width + pit.half_width[[0, -1]]):
        raise ValueError("Surveyed pit entry and exit must meet the traced racing lane")
    grid, _ = _local(proj, data.get("grid"), "grid", 2, 1)
    pit_boxes, _ = _local(proj, data.get("pit_boxes"), "pit_boxes", 2, 1)
    hotlap, _ = _local(proj, [data.get("hotlap_start")], "hotlap_start", 2, 1)
    markers = [
        *_spawn(main, grid, surface_height, "AC_START"),
        *_spawn(pit, pit_boxes, surface_height, "AC_PIT"),
        *_spawn(main, hotlap, surface_height, "AC_HOTLAP_START"),
        *_timing_gate(main, 0, 0, surface_height),
        *_timing_gate(main, main.length / 2, 1, surface_height),
    ]
    cameras = _camera_views(proj, data, main, surface_height, terrain_height)
    fast, fast_widths = _ai_line(main, surface_height)
    pit_line, pit_widths = _ai_line(pit, surface_height)
    route = _lift(main.xy, surface_height, 0.0, "centreline")
    # Reject unready inputs above before touching the scene.
    scene.dummies[:] = [dummy for dummy in scene.dummies if not MARKER.fullmatch(dummy[0])]
    for name, pos, forward in markers:
        scene.dummy(name, pos, forward)
    scene.cameras[:] = cameras
    return KartLayout(route, main.half_width, fast, fast_widths, pit_line, pit_widths,
                      len(pit_boxes), float(main.length))


def _surfaces():
    cfg = ConfigParser(interpolation=None)
    cfg.optionxform = str
    cfg.read_string(export_ac.surfaces_ini(extendido=False))
    racing = None
    for section in cfg.sections():
        if section.startswith("SURFACE_"):
            cfg[section]["IS_VALID_TRACK"] = "0"
            if cfg[section]["KEY"] == "KART":
                racing = section
    if racing is None:
        racing = f"SURFACE_{len(cfg.sections())}"
        cfg[racing] = dict(cfg["SURFACE_0"])
    cfg[racing].update(KEY="KART", FRICTION="1.0", IS_VALID_TRACK="1")
    cfg["_SCRIPTING_PHYSICS"] = {"ALLOW_TRACK_SCRIPTS": "1"}
    output = io.StringIO()
    cfg.write(output, space_around_delimiters=False)
    return output.getvalue()


def write_layout(scene, out_dir, layout, base_info, *, log=print, material_library=True):
    """Export the prepared kart-only scene as a complete standalone AC track."""

    physics = {key[2] for key, pieces in scene.pieces.items() if pieces}
    if not {"KART", "PITLANE"} <= physics:
        raise ValueError("Standalone kart export needs finished KART and PITLANE meshes")
    info = {
        **base_info,
        "name": "Karting Mania North",
        "description": "Karting Mania North circuit in Kousba, Koura, Lebanon.",
        "city": "Kousba",
        "length": layout.length_m,
        "width": f"{2 * float(np.median(layout.half_widths)):.1f} m",
        "pitboxes": layout.pitboxes,
        "run": "circuit",
        "closed": True,
        "ai_hw": None,  # use the surveyed pit lane in place of the stock pit stub
        "trafico": None,
        "notas": None,
    }
    root = Path(export_ac.write_track(scene, out_dir, TRACK_ID, info, [], layout.route, log=log,
                                      material_library=material_library))
    (root / "ai" / "fast_lane.ai").write_bytes(
        export_ac._ai_bytes(layout.fast_lane, layout.fast_lane_half_widths)
    )
    (root / "ai" / "pit_lane.ai").write_bytes(
        export_ac._ai_bytes(layout.pit_lane, layout.pit_lane_half_widths)
    )
    (root / "data" / "surfaces.ini").write_text(_surfaces(), encoding="utf-8", newline="\r\n")
    ui_file = root / "ui" / "ui_track.json"
    ui = json.loads(ui_file.read_text(encoding="utf-8"))
    ui["length"] = f"{layout.length_m:.1f} m"
    ui_file.write_text(json.dumps(ui, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return root
