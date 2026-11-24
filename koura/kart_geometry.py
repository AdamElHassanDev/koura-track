"""Project surveyed Karting Mania outlines into the existing Koura road scene."""

import json
from pathlib import Path

import numpy as np
from shapely.geometry import LineString, Polygon
from shapely.ops import unary_union


def project_ring(proj, points):
    array = np.asarray(points, dtype=float)
    if array.ndim != 2 or array.shape[1] != 2 or len(array) < 3:
        raise ValueError("Karting Mania rings require at least three [latitude, longitude] positions")
    if not np.isfinite(array).all() or np.any(np.abs(array[:, 0]) > 90) or np.any(np.abs(array[:, 1]) > 180):
        raise ValueError("Karting Mania contains an invalid geographic coordinate")
    return np.column_stack(proj.to_local(array[:, 1], array[:, 0]))


def surveyed_geometry(data, proj):
    if data.get("closed") is not True:
        raise ValueError("Karting Mania centreline must be closed")
    asphalt = data["asphalt"]
    outer, inner = (project_ring(proj, asphalt[key]) for key in ("outer", "inner"))
    outline = Polygon(outer, [inner])
    if not outline.is_valid or not 2000 < outline.area < 15000:
        raise ValueError("Karting Mania asphalt outline is invalid or has an implausible area")
    centreline = data["centreline"]
    centre = project_ring(proj, [row[:2] for row in centreline])
    width = np.asarray([row[2] for row in centreline], dtype=float)
    if not np.isfinite(width).all() or np.any(width < 2.5) or np.any(width > 20):
        raise ValueError("Karting Mania contains an invalid surveyed width")
    line = LineString(np.vstack([centre, centre[0]]))
    if not line.is_simple or not outline.covers(line):
        raise ValueError("Karting Mania centreline must stay inside the asphalt")
    materials = {
        "pit": ("kart_asphalt", "PITLANE"),
        "asphalt": ("kart_asphalt", "ROAD"),
        "gravel": ("grava", "GRAVEL"),
    }
    areas = [outline]
    surfaces = [(outline, "kart_asphalt", "KART")]
    for entry in data.get("aprons", []):
        if isinstance(entry, dict):
            coords, surface = entry["ring"], entry["surface"]
        else:
            coords, surface = entry, "asphalt"
        apron = Polygon(project_ring(proj, coords))
        if not apron.is_valid or apron.area < 1:
            raise ValueError("Karting Mania apron has an invalid outline")
        material, physics = materials[surface]
        new = apron.difference(unary_union(areas))
        if new.area > 1:
            surfaces.append((new, material, physics))
        areas.append(apron)
    paved_area = unary_union(areas)
    # Ground between separate lanes is intentional, including the infield.
    no_auto_fill = Polygon(outline.exterior).union(paved_area).buffer(4.0)
    return {"name": "Karting Mania", "poly": paved_area, "surfaces": surfaces,
            "length": line.length, "outline": outline, "no_auto_fill": no_auto_fill}


def read_layout(path, proj):
    path = Path(path)
    data = json.loads(path.read_text(encoding="utf-8"))
    return data, surveyed_geometry(data, proj)
