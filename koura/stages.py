"""Construct the detailed-ground polygon from the stage definition."""

import numpy as np
from shapely.geometry import LineString, Point, box
from shapely.ops import unary_union


def _parts(zone, stage, proj, buffer_m):
    for part in zone["stages"][stage]["parts"]:
        kind = part["type"]
        if kind == "stage":
            yield from _parts(zone, part["ref"], proj, buffer_m)
        elif kind == "box":
            sw = proj.to_local(part["west"], part["south"])
            ne = proj.to_local(part["east"], part["north"])
            yield box(*sw, *ne)
        elif kind == "disc":
            village = zone["villages"][part["village"]]
            xy = proj.to_local(village["lon"], village["lat"])
            yield Point(*xy).buffer(part["metres"], quad_segs=8)
        elif kind == "route_buffer":
            lat, lon = zip(*zone["routes"][part["route"]]["polyline"])
            xy = np.column_stack(proj.to_local(lon, lat))
            yield LineString(xy).buffer(buffer_m or part["metres"], quad_segs=4)


def stage_zone(zone, stage, proj, buffer_m=None):
    return unary_union(list(_parts(zone, stage, proj, buffer_m))).buffer(0)
