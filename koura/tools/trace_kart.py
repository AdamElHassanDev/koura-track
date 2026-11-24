"""Survey the Karting Mania asphalt ribbon from the project's private aerial crop.

Follow the asphalt-to-verge transitions on both sides of a seed route. Where a
shadow, apron or bright tyre barrier obscures the transition, use reviewed
pixel controls. The survey exports both boundaries and a 2 m width profile.
"""

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from pyproj import Geod
from scipy.interpolate import PchipInterpolator, splev, splprep
from scipy.ndimage import gaussian_filter1d, map_coordinates, uniform_filter1d
from shapely.geometry import LineString, Point, Polygon

KOURA = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOURA))
from kart_pts import TRACK as SEED_POINTS


NORTH = 34.328694
WEST = 35.851135
DEG_PER_PIXEL_X = 0.0000026823
DEG_PER_PIXEL_Y = 0.0000022148
SOURCE_SIZE = (1536, 1792)
SECTION_SPACING_PX = 2.7

# These ranges are fractions along the seed route. Their two boundaries are
# surveyed separately. Coordinates are in the full-sized source, never in a
# resized review crop.
OUTER_CONTROLS = (
    # Verge on the western straight. Fence-pole shadows are across the asphalt.
    ((0.0, 0.166), [(330, 1482), (330, 1410), (330, 1373), (327, 1333),
                     (325, 1295), (322, 1250), (321, 1210), (316, 1163),
                     (314, 1125), (315, 1075), (315, 1025), (318, 997),
                     (322, 978), (327, 959), (334, 941)]),
    # Northern service canopy and mixed-colour tyres beyond the asphalt.
    ((0.195, 0.266), [(459, 856), (478, 851), (499, 843), (519, 836),
                       (538, 830), (558, 830), (579, 831), (600, 837),
                       (619, 846), (635, 858), (648, 874)]),
    # The base of the pale fence follows the actual outside edge here.
    ((0.256, 0.304), [(664, 895), (674, 915), (684, 932),
                       (692, 948), (700, 969), (710, 992)]),
    # The club-side apex meets the entrance apron in a continuous paved field.
    ((0.324, 0.427), [(741, 1090), (737, 1110), (728, 1127), (715, 1143),
                       (697, 1155), (673, 1167), (640, 1176), (613, 1180),
                       (586, 1182), (560, 1183), (539, 1182), (511, 1179),
                       (485, 1177), (460, 1174), (442, 1170), (423, 1167)]),
    # Right edge of the inner southwest straight, at the tree shadow.
    ((0.686, 0.819), [(399, 1090), (395, 1115), (392, 1140),
                       (396, 1162), (397, 1180), (398, 1200), (399, 1235), (400, 1265),
                       (400, 1297), (401, 1338), (403, 1374),
                       (407, 1409), (414, 1432), (424, 1440)]),
    # Southeast switchback under trees and the lowest end by the stone wall.
    ((0.903, 1.0), [(520, 1342), (528, 1363), (533, 1384), (536, 1408),
                     (532, 1432), (523, 1455), (511, 1478), (495, 1495),
                     (476, 1512), (458, 1520), (437, 1530), (417, 1538),
                     (397, 1541), (375, 1545), (356, 1541), (341, 1527),
                     (333, 1510), (330, 1496)]),
)
INNER_CONTROLS = (
    # Upstream asphalt edge is separate from the bright tyre line.
    ((0.0, 0.161), [(369, 1481), (364, 1465), (361, 1445), (359, 1411),
                     (359, 1370), (357, 1330),
                       (354, 1297), (349, 1265), (347, 1229), (343, 1185),
                       (341, 1140), (342, 1100), (344, 1055), (347, 1015),
                       (353, 978), (359, 957)]),
    # Painted inside edge sweeps around into the main straight.
    ((0.255, 0.343), [(642, 900), (657, 933), (671, 963), (683, 993),
                       (693, 1024), (699, 1052), (702, 1077), (699, 1097),
                       (690, 1115), (677, 1128), (659, 1138), (642, 1144)]),
    ((0.337, 0.428), [(661, 1137), (641, 1143), (623, 1146), (602, 1147),
                       (580, 1147), (553, 1148), (522, 1148), (490, 1148),
                       (470, 1144), (455, 1139)]),
    # End of the diagonal, before the trees shade the lower hairpin apron.
    ((0.509, 0.566), [(585, 1106), (595, 1111.5), (612, 1119.5),
                       (622, 1122.5), (639, 1121), (654, 1116), (668, 1107)]),
    # Inner edge of the parallel strip below the line of tyres.
    ((0.600, 0.661), [(565, 891), (546, 889), (525, 889), (514, 890),
                       (504, 891.5), (487, 893.5), (472, 893.5), (462, 895),
                       (446, 899), (431, 907)]),
    # Southwest straight. Use the asphalt edge in front of the tyre row.
    ((0.715, 0.819), [(359, 1139), (360, 1175), (361, 1210), (364, 1248),
                       (366, 1280), (369, 1313), (372, 1345), (373, 1375),
                       (374, 1405), (377, 1430), (382, 1448)]),
    # Edge of the lowest grass island under the canopy shadow.
    ((0.891, 1.0), [(474, 1347), (480, 1341), (488, 1345), (497, 1356),
                     (506, 1372), (512, 1390), (513, 1411), (507, 1431),
                     (493, 1451), (477, 1467), (458, 1481), (435, 1491),
                     (413, 1499), (391, 1501), (376, 1498), (365, 1488),
                     (359, 1474), (357, 1460)]),
)

# Independent visible landmarks on the two asphalt edges. The controls used
# for fitting are deliberately not included in this review.
VISIBLE_CHECKPOINTS = {
    "outer": [
        ("west straight at field boundary", (315, 1088)),
        ("outside northeast curve at fence", (688, 938)),
        ("end of north retaining edge", (626, 851)),
        ("west approach to northern infield", (416, 1009)),
        ("grass edge at inside hairpin tip", (641, 1085)),
        ("south grass tongue by raised curb", (439, 1439)),
        ("southern return at grass-to-asphalt transition", (433, 1331)),
    ],
    "inner": [
        ("outer west verge past power line", (346, 1029)),
        ("inner west straight in sunlight", (369, 1324)),
        ("western verge in front of tyres", (357, 1382)),
        ("asphalt below the upper infield tyre row", (495, 892)),
        ("inside curb on east approach", (700, 1064)),
        ("middle hairpin before the canopy shadow", (603, 1115)),
        ("grass edge opposite apex", (437, 1084)),
        ("grass peninsula in the south", (478, 1340)),
    ],
}

OCCLUDED_SECTIONS = (
    "Clubhouse-side boundary through the shared paved apron and tree shadow",
    "Southeast switchback outside edge under trees",
    "Inside edge of the southern grass island under trees",
)


def seed_sections():
    source = np.array(SEED_POINTS, dtype=float)
    spline, _ = splprep(np.vstack((source, source[0])).T, s=len(source) * 0.8, per=True)
    dense = np.array(splev(np.linspace(0, 1, 12000, endpoint=False), spline)).T
    length = np.linalg.norm(np.diff(np.vstack((dense, dense[0])), axis=0), axis=1).sum()
    centre = resample_ring(dense, round(length / SECTION_SPACING_PX))
    tangent = np.roll(centre, -2, axis=0) - np.roll(centre, 2, axis=0)
    normal = np.column_stack((-tangent[:, 1], tangent[:, 0]))
    normal /= np.linalg.norm(normal, axis=1)[:, None]
    return centre, normal


def resample_ring(points, count):
    closed = np.vstack((points, points[0]))
    cumulative = np.r_[0., np.cumsum(np.linalg.norm(np.diff(closed, axis=0), axis=1))]
    targets = np.arange(count) * (cumulative[-1] / count)
    return np.column_stack([
        np.interp(targets, cumulative, closed[:, dim]) for dim in range(points.shape[1])
    ])


def edge_offsets(gray, seed, normals):
    """Follow the colour transition between asphalt and its darker verge."""
    rays = np.arange(0, 40, 0.5)
    offsets = np.arange(5, 35, 0.5)
    points = seed[:, None, :] + normals[:, None, :] * rays[None, :, None]
    colours = map_coordinates(gray, [points[..., 1], points[..., 0]], order=1)
    colours = gaussian_filter1d(colours, 1.2, axis=1)
    at = (offsets * 2).astype(int)
    contrast = np.clip(colours[:, at - 4] - colours[:, at + 4], -30, 60)
    gradient = np.clip(colours[:, at - 1] - colours[:, at + 1], -8, 21)
    asphalt = np.clip((colours[:, at - 6] - 120) / 20, 0, 4)
    scores = contrast + gradient + 2 * asphalt - 0.04 * (offsets - 16) ** 2
    penalty = 1.65 * (offsets[:, None] - offsets[None, :]) ** 2

    previous = scores[0] - 0.25 * (offsets - 16) ** 2
    history = []
    for score in scores[1:]:
        transitions = previous[:, None] - penalty
        history.append(transitions.argmax(axis=0))
        previous = score + transitions.max(axis=0)
    candidates = [int(previous.argmax())]
    for row in reversed(history):
        candidates.append(int(row[candidates[-1]]))
    return gaussian_filter1d(offsets[candidates[::-1]], 1.65, mode="wrap")


def apply_controls(seed, normals, measured, groups):
    """Interpolate reviewed pixel offsets where the source transition is ambiguous."""
    tangent = np.column_stack((normals[:, 1], -normals[:, 0]))
    for (start, stop), controls in groups:
        first, last = round(start * len(seed)), round(stop * len(seed))
        indexes = np.arange(first, last)
        projected = {}
        for control in controls:
            vector = np.asarray(control) - seed[indexes]
            along = np.einsum("ij,ij->i", vector, tangent[indexes])
            across = np.einsum("ij,ij->i", vector, normals[indexes])
            # The same lane can come back close to the control in a hairpin.
            # The detected boundary supplies a weak prior where distance ties.
            score = along ** 2 + 0.18 * (across - measured[indexes]) ** 2
            score[across < 0] = np.inf
            if not np.isfinite(score).any():
                raise ValueError(f"Control {control} does not lie on the selected side")
            best = int(score.argmin())
            projected[int(indexes[best])] = across[best]
        controls_at = np.array(sorted(projected))
        controls_to = np.array([projected[i] for i in controls_at])
        if len(controls_at) < 2:
            raise ValueError("Edge control range has too few independent points")
        lo, hi = int(controls_at[0]), int(controls_at[-1])
        x = np.arange(lo, hi + 1)
        sample = PchipInterpolator(controls_at, controls_to)(x)
        measured[x] = sample
        # Blend the ends into the edge-detector result across two metres.
        collar = np.arange(1, 4)
        weight = (4 - collar) / 4
        for direction, joint in ((-1, lo), (1, hi)):
            side = (joint + direction * collar) % len(seed)
            measured[side] = weight * measured[joint] + (1 - weight) * measured[side]
    return measured


def georeference(pixels):
    return np.column_stack((NORTH - pixels[:, 1] * DEG_PER_PIXEL_Y,
                            WEST + pixels[:, 0] * DEG_PER_PIXEL_X))


def pixel_scale():
    ellipsoid = Geod(ellps="WGS84")
    east = ellipsoid.inv(WEST, NORTH, WEST + DEG_PER_PIXEL_X, NORTH)[2]
    north = ellipsoid.inv(WEST, NORTH, WEST, NORTH - DEG_PER_PIXEL_Y)[2]
    return np.array([east, north])


def loop_segments(points):
    return np.linalg.norm(np.roll(points, -1, axis=0) - points, axis=1)


def cross_sections(points, edges):
    bounds = []
    tangent = np.roll(points, -1, axis=0) - np.roll(points, 1, axis=0)
    for point, vector in zip(points, tangent):
        normal = np.array([-vector[1], vector[0]])
        normal *= 16 / np.linalg.norm(normal)
        cut = LineString([point - normal, point + normal])
        boundaries = []
        for edge in edges:
            section = cut.intersection(edge)
            if isinstance(section, Point):
                boundaries.append(np.asarray(section.coords[0]))
                continue
            candidates = [p for p in getattr(section, "geoms", ()) if isinstance(p, Point)]
            if not candidates:
                raise ValueError(f"Missing edge in the width section at survey point {point}")
            nearest = min(candidates, key=lambda p: p.distance(Point(point)))
            boundaries.append(np.asarray(nearest.coords[0]))
        bounds.append(boundaries)
    return np.asarray(bounds)


def width_profile(outer, inner):
    scale = pixel_scale()
    midpoint = (outer + inner) / 2
    metric = uniform_filter1d(midpoint, size=5, axis=0, mode="wrap") * scale
    edges = [LineString(np.vstack((edge, edge[0])) * scale) for edge in (outer, inner)]
    centre = cross_sections(metric, edges).mean(axis=1)
    centre = uniform_filter1d(centre, size=5, axis=0, mode="wrap")
    length = loop_segments(centre).sum()
    points = resample_ring(centre, round(length / 2))
    bounds = cross_sections(points, edges)
    widths = np.linalg.norm(bounds[:, 0] - bounds[:, 1], axis=1)
    return points / scale, widths, loop_segments(points)


def review(outer, inner):
    scale = pixel_scale()
    checks = []
    for key, pixels in (("outer", outer), ("inner", inner)):
        line = LineString(np.vstack((pixels, pixels[0])) * scale)
        for description, point in VISIBLE_CHECKPOINTS[key]:
            gap = line.distance(Point(np.asarray(point) * scale))
            checks.append({"edge": key, "description": description, "source_px": point,
                           "offset_m": round(gap, 3), "within_half_metre": bool(gap <= 0.5)})
    return checks


def draw_overlay(image, output, edges, centre, checks):
    image = image.copy()
    draw = ImageDraw.Draw(image)
    colours = ("#ed006a", "#00f367", "#13c3fb")
    for ring, colour in zip((*edges, centre), colours):
        line = [tuple(point) for point in ring]
        draw.line(line + line[:1], fill=colour, width=1)
    for check in checks:
        x, y = check["source_px"]
        colour = "#fff03a" if check["within_half_metre"] else "#ff3000"
        draw.ellipse((x - 2, y - 2, x + 2, y + 2), outline=colour)
    image.save(output / "trace_overlay.png")
    image.crop((295, 805, 760, 1560)).resize((930, 1510)).save(output / "trace_overlay_crop.png")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    root = KOURA.parent
    parser.add_argument("--image", type=Path, default=root / "handoff/evidence/karting_mania_aerial.png")
    parser.add_argument("--output", type=Path, default=root / "out/kart")
    args = parser.parse_args()
    with Image.open(args.image) as source:
        if source.size != SOURCE_SIZE:
            parser.error(f"expected the georeferenced {SOURCE_SIZE[0]} × {SOURCE_SIZE[1]} aerial crop")
        image = source.convert("RGB")

    # Work on the 510 × 780 survey window to stay comfortably under the build budget.
    crop_origin = np.array([270, 795])
    crop = image.crop((270, 795, 780, 1575))
    grayscale = np.asarray(crop, dtype=np.float32).mean(axis=2)
    seed, normals = seed_sections()
    edges = []
    for sign, controls in ((-1, OUTER_CONTROLS), (1, INNER_CONTROLS)):
        outward = sign * normals
        offsets = edge_offsets(grayscale, seed - crop_origin, outward)
        offsets = apply_controls(seed, outward, offsets, controls)
        ring = seed + outward * gaussian_filter1d(offsets, 0.95, mode="wrap")[:, None]
        edges.append(ring[::2])
    outer, inner = edges
    outer_shape, inner_shape = map(Polygon, edges)
    if not outer_shape.is_valid or not inner_shape.is_valid or not outer_shape.contains(inner_shape):
        raise ValueError("Survey edges do not form one valid asphalt ribbon")
    ribbon = Polygon(outer, [inner])
    centre, widths, spacing = width_profile(outer, inner)
    length = float(spacing.sum())
    if not ribbon.covers(LineString(np.vstack((centre, centre[0])))):
        raise ValueError("The surveyed centreline crosses the asphalt boundary")
    checks = review(outer, inner)
    source_hash = hashlib.sha256(args.image.read_bytes()).hexdigest()
    count = sum(point["within_half_metre"] for point in checks)
    output = args.output
    output.mkdir(exist_ok=True, parents=True)
    data = {
        "centreline": np.round(np.column_stack((georeference(centre), widths)), 8).tolist(),
        "closed": True,
        "asphalt": {
            "outer": np.round(georeference(outer), 8).tolist(),
            "inner": np.round(georeference(inner), 8).tolist(),
        },
        "length_m": round(length, 2),
    }
    (output / "trace_geometry.json").write_text(json.dumps(data, indent=2) + "\n")
    evidence = {
        "source_sha256": source_hash,
        "source_size_px": SOURCE_SIZE,
        "actual_station_spacing_m": round(length / len(centre), 4),
        "station_spacing_range_m": [round(float(spacing.min()), 2), round(float(spacing.max()), 2)],
        "width_min_m": round(float(widths.min()), 2),
        "width_max_m": round(float(widths.max()), 2),
        "checkpoints_within_half_metre": count,
        "checkpoints": checks,
        "occluded_sections": OCCLUDED_SECTIONS,
        "half_metre_whole_edge_verified": False,
    }
    (output / "trace_review.json").write_text(json.dumps(evidence, indent=2) + "\n")
    draw_overlay(image, output, edges, centre, checks)
    print(f"{length:.2f} m; {len(centre)} stations; widths {widths.min():.2f}–{widths.max():.2f} m")
    print(f"Visible checkpoints within 0.5 m: {count}/{len(checks)}. Occluded sections require review.")


if __name__ == "__main__":
    main()
