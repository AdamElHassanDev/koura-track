"""Straighten a photographed facade from matched image and output control points."""

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "road-to-assetto"))
from roadtoassetto.photo_projection import fit_homography


def rectify(image, controls):
    source = np.asarray(controls["image_points_px"], dtype=float)
    target = np.asarray(controls["rectified_points_px"], dtype=float)
    size = tuple(controls["output_size_px"])
    if len(size) != 2 or any(type(value) is not int or value < 2 for value in size):
        raise ValueError("output_size_px must be a positive integer width and height")
    image = ImageOps.exif_transpose(image).convert("RGB")
    matrix, residuals = fit_homography(target, source)
    if (source < 0).any() or (source > image.size).any():
        raise ValueError("Control points leave the photograph")
    if (target < 0).any() or (target > size).any():
        raise ValueError("Control points leave the rectified image")
    error = float(residuals.max())
    if error > 3:
        raise ValueError(f"Facade control points disagree by {error:.2f} px")
    result = image.transform(size, Image.Transform.PERSPECTIVE, matrix.ravel()[:8], Image.Resampling.BICUBIC)
    return result, error


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image", type=Path)
    parser.add_argument("controls", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    with Image.open(args.image) as image:
        result, error = rectify(image, json.loads(args.controls.read_text(encoding="utf-8")))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    result.save(args.output, quality=96)
    print(f"Maximum control-point residual {error:.3f} px. Saved {args.output}")


if __name__ == "__main__":
    main()
