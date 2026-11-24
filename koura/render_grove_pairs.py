"""Compare the ten 300 m grove plots with their exact positions in the exported GLB."""

import argparse
import json
import math
from pathlib import Path
import re

from numba import njit
import numpy as np
from PIL import Image, ImageDraw

from render_fullcircle import Scene, SUN


CROWNS = {"olivo": "#e8c753", "encino": "#74dc9a", "pino": "#73bcf0"}
TREE_MESH = re.compile(r"(?:^|_)arboles_fondo_veg_(olivo|encino|pino)_")
PLOT_NAME = re.compile(r"grove-\d{2}")


@njit(cache=True)
def raster_orthographic(vertices, faces, uv, shade, texture, cutout, blend, depth, colour):
    height, width = depth.shape
    th, tw = texture.shape[:2]
    for a, b, c in faces:
        xa, ya, ha = vertices[a]
        xb, yb, hb = vertices[b]
        xc, yc, hc = vertices[c]
        area = (xb - xa) * (yc - ya) - (yb - ya) * (xc - xa)
        if abs(area) < 1e-7:
            continue
        x0, x1 = max(0, int(math.floor(min(xa, xb, xc)))), min(width, int(math.ceil(max(xa, xb, xc))))
        y0, y1 = max(0, int(math.floor(min(ya, yb, yc)))), min(height, int(math.ceil(max(ya, yb, yc))))
        for y in range(y0, y1):
            for x in range(x0, x1):
                px, py = x + 0.5, y + 0.5
                wb = ((px - xa) * (yc - ya) - (py - ya) * (xc - xa)) / area
                wc = ((xb - xa) * (py - ya) - (yb - ya) * (px - xa)) / area
                wa = 1.0 - wb - wc
                if min(wa, wb, wc) < -1e-8:
                    continue
                level = ha * wa + hb * wb + hc * wc
                if level < depth[y, x]:
                    continue
                u = uv[a, 0] * wa + uv[b, 0] * wb + uv[c, 0] * wc
                v = uv[a, 1] * wa + uv[b, 1] * wb + uv[c, 1] * wc
                tx = int((u - math.floor(u)) * tw) % tw
                ty = int((v - math.floor(v)) * th) % th
                colour_sample = texture[ty, tx]
                if cutout and colour_sample[3] < 0.5:
                    continue
                light = shade[a] * wa + shade[b] * wb + shade[c] * wc
                opacity = colour_sample[3] if blend else 1.0
                for channel in range(3):
                    colour[y, x, channel] = (colour_sample[channel] * light * opacity
                                            + colour[y, x, channel] * (1.0 - opacity))
                if not blend:
                    depth[y, x] = level


def _exported_centres(positions, faces, low, high):
    """The projected ends of each vertical card triangle share a crown centre."""
    triangle = positions[faces][:, :, (0, 2)]
    centres = np.round((triangle.min(axis=1) + triangle.max(axis=1)) * 0.5, decimals=2)
    keep = (centres > low).all(axis=1) & (centres < high).all(axis=1)
    return centres[keep]


def top_down(scene, plot, size):
    side = float(plot["side_m"])
    center = np.array([plot["x"], -plot["y"]], dtype=float)
    low, high = center - side / 2, center + side / 2
    xmin, xmax = scene.minimum[:, (0, 2)], scene.maximum[:, (0, 2)]
    selected = np.flatnonzero((xmin < high).all(axis=1) & (xmax > low).all(axis=1))
    colour = np.full((size, size, 3), [0.18, 0.22, 0.26], np.float32)
    depth = np.full((size, size), -np.inf, dtype=np.float32)
    exported = {name: [] for name in CROWNS}
    for index in selected:
        mesh = scene.meshes[index]
        vertices = scene.accessor(mesh.attributes["POSITION"])
        faces = scene.accessor(mesh.indices).reshape(-1, 3)
        species = TREE_MESH.search(mesh.name)
        if species:
            exported[species[1]].append(_exported_centres(vertices, faces, low, high))
            continue
        xy = (vertices[:, (0, 2)] - low) * (size / side)
        screen = np.column_stack((xy, vertices[:, 1])).astype(np.float32)
        cutout, blend = mesh.mode == "MASK", mesh.mode == "BLEND"
        texture = scene.texture(mesh.texture, cutout or blend)
        uv = scene.accessor(mesh.attributes["TEXCOORD_0"])
        normals = scene.accessor(mesh.attributes["NORMAL"])
        shade = 0.45 + 0.65 * np.clip(normals @ SUN, 0.0, 1.0)
        if cutout:
            shade.fill(0.95)
        if not (cutout or blend):
            shade /= 255.0
        raster_orthographic(screen, faces, uv, shade, texture, cutout, blend, depth, colour)
    image = Image.fromarray((np.clip(colour, 0, 1) * 255).astype(np.uint8))
    counts = {}
    draw = ImageDraw.Draw(image)
    for species, dots in exported.items():
        coords = np.unique(np.concatenate(dots), axis=0) if dots else np.empty((0, 2))
        counts[species] = len(coords)
        for x, y in (coords - low) * size / side:
            draw.ellipse((x - 2, y - 2, x + 2, y + 2), outline=CROWNS[species], width=1)
    return image, counts, np.count_nonzero(np.isfinite(depth)) / depth.size


def _plate(directory, plot, exported, counts, size):
    names = ("Aerial source", "Selected crowns", "Exported ground and tree centres")
    plot_name = plot["name"]
    with Image.open(directory / f"{plot_name}-source.png") as image:
        source = image.convert("RGB").resize((size, size), Image.Resampling.LANCZOS)
    with Image.open(directory / f"{plot_name}-crowns.png") as image:
        crowns = image.convert("RGB").resize((size, size), Image.Resampling.LANCZOS)
    border, header, gutter, footer = 12, 55, 8, 39
    width = size * 3 + border * 2 + gutter * 2
    plate = Image.new("RGB", (width, size + header + footer), "#182027")
    draw = ImageDraw.Draw(plate)
    draw.text((border, 8), (f"{plot_name.title()}   {plot['lat']:.6f}, {plot['lon']:.6f}"
                            f"    {plot['side_m']:g} m square, north up"), fill="#f2f5f7")
    for i, (title, panel) in enumerate(zip(names, (source, crowns, exported), strict=True)):
        x = border + i * (size + gutter)
        draw.text((x, header - 21), title, fill="#f2f5f7")
        plate.paste(panel, (x, header))
    expected = plot["counts"]
    x = border
    for species, label in (("olivo", "Olive"), ("encino", "Oak"), ("pino", "Pine")):
        line = f"{label}  {counts[species]} exported / {expected.get(species, 0)} selected"
        draw.text((x, size + header + 12), line, fill=CROWNS[species])
        x += round(draw.textlength(line)) + 22
    return plate


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("glb", type=Path)
    parser.add_argument("plots", type=Path, help="plots.json beside the private aerial reference images")
    parser.add_argument("out", type=Path, help="Private directory for the comparison plates and report")
    parser.add_argument("--inspect", type=Path, help="Optional KN5 inspection JSON for visibility filtering")
    parser.add_argument("--pixels", type=int, default=600, help="Width per panel in pixels")
    args = parser.parse_args()
    if not 384 <= args.pixels <= 1024:
        parser.error("--pixels must be between 384 and 1024")
    plots = json.loads(args.plots.read_text())
    args.out.mkdir(parents=True, exist_ok=True)
    records = []
    with Scene(args.glb, args.inspect) as scene:
        for plot in plots:
            name = plot["name"]
            if not PLOT_NAME.fullmatch(name) or plot["side_m"] != 300:
                raise ValueError(f"Invalid WP14 grove plot: {name}")
            exported, counts, cover = top_down(scene, plot, args.pixels)
            plate = _plate(args.plots.parent, plot, exported, counts, args.pixels)
            filename = f"{name}-pair.jpg"
            plate.save(args.out / filename, quality=94)
            expected = {key: plot["counts"].get(key, 0) for key in CROWNS}
            records.append({"name": name, "pair": filename, "expected": expected, "exported": counts,
                            "counts_match": counts == expected, "drawn_ground_share": round(cover, 4)})
    matches = bool(records) and all(row["counts_match"] for row in records)
    report = {"plots": records, "count": len(records), "all_counts_match": matches,
              "ten_comparisons": len(records) >= 10}
    (args.out / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(f"{len(records)} grove comparisons, {'matching' if matches else 'mismatched'} exported counts")
    return 0 if matches else 1


if __name__ == "__main__":
    raise SystemExit(main())
