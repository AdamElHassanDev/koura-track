"""Create the Stage 1 field checklists from the build's public map sources.

Run with .venv/bin/python koura/tools/make_checklists.py. Road lengths are
clipped to Stage 1. Any feature that touches both cores goes in Core A. For
an unreviewed road, in_imagery=no means its presence has yet to be confirmed.
Other unreviewed fields use pending unless the source has an applicable tag.
"""

import argparse
from collections import Counter
import csv
from hashlib import sha256
import json
import os
from pathlib import Path
import sys

import numpy as np
from shapely import normalize, to_wkb
from shapely.geometry import LineString, box
from shapely.ops import unary_union

ROOT = Path(__file__).resolve().parents[2]
KOURA = ROOT / "koura"
sys.path[:0] = [str(ROOT / "openlaps"), str(KOURA)]
os.environ.setdefault("OPENLAPS_CACHE", str(ROOT / "cache"))

from openlaps.buildings import collect
from openlaps.config import NETWORK
from openlaps.geo import LocalProjection
from openlaps.sources import msbuildings, osm
from stages import stage_zone


ROAD_FIELDS = (
    "way_id", "core", "length_m", "osm_class", "in_imagery", "width_m_measured",
    "surface", "markings", "edge_left", "edge_right", "lamps", "speed_bumps", "notes",
    "source", "status",
)
BUILDING_FIELDS = (
    "id", "core", "lat", "lon", "area_m2", "exists_now", "shape_ok", "levels",
    "open_ground_floor", "roof", "roof_colour", "wall_colour", "roof_items",
    "boundary_wall", "gate", "use", "sign_text", "facade_image", "source", "status",
)
PENDING = "pending"
STATUSES = {"todo", "done", "no_evidence"}
MS_SOURCE = "Microsoft Global ML Building Footprints"


def core_areas(zone, proj):
    def village_box(key):
        bounds = zone["fine_boxes"][key]
        return box(*proj.to_local(bounds["west"], bounds["south"]),
                   *proj.to_local(bounds["east"], bounds["north"]))

    loop_corridors = []
    for route in ("nakhle_big_loop", "nakhle_small_loop"):
        lat, lon = zip(*zone["routes"][route]["polyline"])
        loop_corridors.append(LineString(np.column_stack(proj.to_local(lon, lat))).buffer(60))
    return {"A": village_box("btouratij_core"),
            "B": unary_union([village_box("nakhle_core"), *loop_corridors])}


def core_name(geometry, cores):
    return next((name for name, area in cores.items() if area.intersects(geometry)), "S1")


def road_rows(data, proj, detailed, cores):
    for way in data["ways"]:
        tags = way["tags"]
        highway = tags.get("highway")
        # Keep restricted service ways in the audit so the cut-loop review can
        # check whether the restriction or classification still matches reality.
        if highway not in NETWORK:
            continue
        line = LineString(np.column_stack(proj.to_local(*zip(*way["coords"]))))
        inside = line.intersection(detailed)
        if not inside.length:
            continue
        road_id = way["id"]
        notes = ["Imagery check pending"]
        for key in ("name", "width", "surface", "lit", "access", "motor_vehicle", "motorcar"):
            if tags.get(key):
                notes.append(f"OSM {key}={tags[key]}")
        surface = tags.get("surface")
        yield dict.fromkeys(ROAD_FIELDS, PENDING) | {
            "way_id": road_id, "core": core_name(inside, cores), "length_m": f"{inside.length:.2f}",
            "osm_class": highway, "in_imagery": "no",
            "surface": surface if surface in {"asphalt", "concrete", "dirt"} else PENDING,
            "markings": "none" if tags.get("lane_markings") == "no" else PENDING,
            "notes": ". ".join(notes), "source": f"https://www.openstreetmap.org/way/{road_id}",
            "status": "todo",
        }


def building_use(tags):
    kind = tags.get("building", "yes")
    if kind in {"mosque", "church", "school"}:
        return kind
    if kind in {"cathedral", "chapel", "basilica"}:
        return "church"
    if tags.get("amenity") == "school":
        return "school"
    if tags.get("amenity") == "place_of_worship":
        return {"muslim": "mosque", "christian": "church"}.get(tags.get("religion"), "other")
    if kind == "retail" or tags.get("shop") not in (None, "", "no", "vacant"):
        return "shop"
    if kind in {"house", "detached", "semidetached_house", "terrace", "bungalow", "residential", "apartments"}:
        return "house"
    return PENDING if kind == "yes" else "other"


def building_rows(footprints, proj, detailed, cores):
    inside = [item for item in footprints if item["poly"].intersects(detailed)]
    osm_id_counts = Counter(item.get("osm_id") for item in inside)
    seen = set()
    for item in inside:
        osm_id = item.get("osm_id")
        poly = item["poly"]
        if osm_id and osm_id_counts[osm_id] == 1:
            key = osm_id
        else:
            # Microsoft provides footprints without IDs. Canonical geometry
            # also disambiguates multiple pieces of a single OSM feature.
            digest = sha256(to_wkb(normalize(poly), byte_order=0)).hexdigest()[:16]
            key = f"{osm_id or item['src']}-{digest}"
        if key in seen:
            continue
        seen.add(key)

        point = poly.centroid
        lon, lat = proj.to_lonlat(point.x, point.y)
        source = MS_SOURCE
        if osm_id:
            kind = {"w": "way", "r": "relation"}[osm_id[0]]
            source = f"https://www.openstreetmap.org/{kind}/{osm_id[1:]}"
        tags = item["tags"]
        roof = tags.get("roof:shape")
        yield dict.fromkeys(BUILDING_FIELDS, PENDING) | {
            "id": key, "core": core_name(poly, cores), "lat": f"{lat:.7f}", "lon": f"{lon:.7f}",
            "area_m2": f"{poly.area:.2f}", "levels": tags.get("building:levels") or PENDING,
            "roof": roof if roof in {"flat", "hipped", "gabled"} else PENDING,
            "roof_colour": tags.get("roof:colour") or PENDING,
            "wall_colour": tags.get("building:colour") or PENDING,
            "use": building_use(tags), "source": source, "status": "todo",
        }


def write_checklist(path, fields, review_fields, rows):
    rows = list(rows)
    if not rows:
        raise ValueError(f"No inventory rows for {path.name}")
    key = fields[0]
    previous = {}
    if path.exists():
        with path.open(encoding="utf-8", newline="") as stream:
            reader = csv.DictReader(stream)
            if tuple(reader.fieldnames or ()) != fields:
                raise ValueError(f"Unexpected columns in {path}")
            for row in reader:
                if row["status"] not in STATUSES or not row[key] or row[key] in previous:
                    raise ValueError(f"Invalid or repeated checklist ID or status in {path}: {row[key]}")
                previous[row[key]] = row

    for row in rows:
        old = previous.pop(str(row[key]), {})
        row.update({field: old[field] for field in review_fields if old.get(field)})
    if previous:
        print(f"  keeping {len(previous)} existing rows outside the current {path.name} source inventory")
        for row in previous.values():
            rows.append({field: row[field] or PENDING for field in fields})
    rows.sort(key=lambda row: (row["core"], str(row[key])))

    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(f".{os.getpid()}.tmp")
    with temporary.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    temporary.replace(path)
    counts = Counter(row["core"] for row in rows)
    print(f"{path.name}: {len(rows)} total ({counts['A']} Core A, {counts['B']} Core B, {counts['S1']} rest of S1)")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--osm", type=Path, default=KOURA / "data" / "osm_koura.json")
    parser.add_argument("--out", type=Path, default=KOURA / "overrides")
    args = parser.parse_args()

    zone = json.loads((ROOT / "handoff" / "inputs" / "zone.json").read_text(encoding="utf-8"))
    origin = zone["origin"]
    rect = zone["stages"]["S1"]["expected"]["rect_local_m"]
    proj = LocalProjection.marco(origin["lat"], origin["lon"], rect)
    detailed = stage_zone(zone, "S1", proj).intersection(box(*rect))
    cores = core_areas(zone, proj)

    snapshot = json.loads(args.osm.read_text(encoding="utf-8"))
    baseline = snapshot.get("build9_road_scope", {})
    if "S1" in baseline.get("stages", ()):
        snapshot["elements"] = snapshot["elements"][:baseline["element_count"]]
    data = osm.parse(snapshot)
    ms_polys = msbuildings.download(proj.bbox())
    if not ms_polys:
        raise ValueError("No Microsoft footprints returned for Stage 1")
    footprints = collect(data, ms_polys, proj, rect)

    write_checklist(args.out / "s1_roads.csv", ROAD_FIELDS, ROAD_FIELDS[4:],
                    road_rows(data, proj, detailed, cores))
    write_checklist(args.out / "s1_buildings.csv", BUILDING_FIELDS, BUILDING_FIELDS[5:],
                    building_rows(footprints, proj, detailed, cores))


if __name__ == "__main__":
    main()
