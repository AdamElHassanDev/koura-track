"""Compare located street footage with the exported Koura scene."""

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageOps
from pyproj import Geod

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "koura"))
sys.path.insert(0, str(ROOT / "openlaps"))
sys.path.insert(0, str(ROOT / "openlaps" / "tools"))
from openlaps.geo import LocalProjection
from render import load_glb, render
from render_fullcircle import EYE_HEIGHT_M, MAX_ROAD_SNAP_M, Scene


def locate(glb, projection, manifest, rows):
    poses = []
    geodesic = Geod(ellps="WGS84")
    with Scene(glb) as scene:
        for row in rows:
            lat, lon = float(row["lat"]), float(row["lon"])
            x, y = projection.to_local(lon, lat)
            position = scene.road_position(np.array([x, -y]))
            if position is None:
                raise ValueError(f"No built road within {MAX_ROAD_SNAP_M:g} m of frame at {row['time_s']} s")
            eye, offset = position
            eye[1] += float(row.get("camera_height_m", 1.45)) - EYE_HEIGHT_M
            bearing = float(row["bearing_deg"])
            after_lon, after_lat, _ = geodesic.fwd(lon, lat, bearing, 30)
            tx, ty = projection.to_local(after_lon, after_lat)
            direction = np.array([tx - x, 30 * math.tan(math.radians(row.get("pitch_deg", 0))), -ty + y])
            image = Path(row["image"])
            if not image.is_absolute():
                image = manifest.parent / image
            if not image.is_file():
                raise ValueError(f"Missing source frame: {image}")
            poses.append((eye, eye + direction, image, float(offset)))
    return poses


def comparison(glb, manifest, output, *, width=580, height=326):
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    rows = payload["frames"]
    if not rows:
        raise ValueError("No source frames in the manifest")
    zone = json.loads((ROOT / "handoff" / "inputs" / "zone.json").read_text(encoding="utf-8"))
    origin = zone["origin"]
    proj = LocalProjection.marco(origin["lat"], origin["lon"], (-100, -100, 100, 100))
    poses = locate(glb, proj, manifest, rows)
    meshes, textures, _, _ = load_glb(glb)
    gap, header = 8, 27
    row_height = header + height + gap
    sheet = Image.new("RGB", (width * 2 + gap, row_height * len(rows)), "#171b20")
    draw = ImageDraw.Draw(sheet)
    report = []
    for i, (row, (eye, target, file, offset)) in enumerate(zip(rows, poses, strict=True)):
        fov = float(row.get("fov_deg", 76))
        if not 30 <= fov <= 130:
            raise ValueError(f"Invalid horizontal FOV for footage frame at {row['time_s']} s")
        with Image.open(file) as photo:
            source = ImageOps.fit(photo.convert("RGB"), (width, height), Image.Resampling.LANCZOS)
        built = render(meshes, textures, eye, target, width, height, fov=fov)
        y = i * row_height
        seconds = int(row["time_s"])
        timestamp = f"{seconds // 60:02d}:{seconds % 60:02d}"
        label = row.get("place", "Btouratij")
        draw.text((8, y + 7), f"Footage   {timestamp}   {label}", fill="white")
        draw.text((width + gap + 8, y + 7), "Exported scene", fill="white")
        sheet.paste(source, (0, y + header))
        sheet.paste(built, (width + gap, y + header))
        report.append({
            "time_s": row["time_s"], "lat": row["lat"], "lon": row["lon"], "place": label,
            "bearing_deg": row["bearing_deg"], "road_snap_m": round(offset, 3), "fov_deg": fov,
            "camera_height_m": row.get("camera_height_m", 1.45), "pitch_deg": row.get("pitch_deg", 0),
            "image": str(file), "confidence": row.get("confidence"),
        })
    output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output, quality=94)
    result = {"source": payload.get("source"), "frames": report}
    output.with_suffix(".json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("glb", type=Path)
    parser.add_argument("manifest", type=Path, help="JSON with a source URL and located frames")
    parser.add_argument("out", type=Path, help="Output comparison JPEG")
    args = parser.parse_args()
    result = comparison(args.glb, args.manifest, args.out)
    print(f"{len(result['frames'])} located footage comparisons saved to {args.out}")


if __name__ == "__main__":
    main()
