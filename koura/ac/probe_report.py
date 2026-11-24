"""Check Assetto Corsa runtime logs, collision, wheel surfaces and frame rate."""

import argparse
import json
import math
import statistics
from pathlib import Path

from paths import game_paths
from race_ini import case_preserving_parser


ROAD_SURFACES = {"ROAD", "PITLANE", "MXCOBBLE", "MXVADO", "KART"}


def read_lines(path):
    if not path.is_file():
        return []
    # The CSP writer can leave a NUL-filled prefix after restarting the game.
    return path.read_text(errors="replace").replace("\x00", "").splitlines()


def report(track, directory, surfaces_ini, minimum_fps=60, expected_surfaces=ROAD_SURFACES):
    logs = read_lines(directory / "log.txt")
    csp = read_lines(directory / "custom_shaders_patch.log")
    marker = f"Creating physics track: {track}"
    track_loaded = any(line.strip() == marker or line.strip().startswith(marker + " [") for line in logs)
    track_errors = [line for line in logs if track in line and "ERROR:" in line
                    and f"NO STAT FOR {track}" not in line]
    csp_errors = [line for line in csp if (track in line or "ext_config" in line.lower())
                  and ("ERROR" in line.upper() or "FAILED" in line.upper() or "💥" in line)]
    csp_version = next((line[line.index("CSP v"):].strip() for line in csp
                        if "CSP v" in line and "enabled" in line), None)
    data = json.loads((directory / "results.json").read_text())
    expected = json.loads((directory / "status.json").read_text()).get("points")
    results = data["results"]
    cp = case_preserving_parser()
    with surfaces_ini.open(encoding="utf-8-sig") as f:
        cp.read_file(f)
    surfaces = {int(section.removeprefix("SURFACE_")): cp[section]["KEY"]
                for section in cp.sections() if section.startswith("SURFACE_")}
    fps = [row["fps"] for row in results if row.get("fps") is not None and math.isfinite(row["fps"])]
    fps_median = statistics.median(fps) if fps else None
    point_checks = []
    for row in results:
        drift = math.dist(row["requested"], row["position"])
        gaps = [row["position"][1] - wheel["contact"][1] for wheel in row["wheels"]]
        keys = [surfaces.get(wheel["surface"]) for wheel in row["wheels"]]
        point_checks.append({
            "i": row["i"], "drift_m": drift, "wheel_gaps_m": gaps, "surface_keys": keys,
            "lands": drift <= 3, "wheels": len(gaps) == 4 and all(-0.5 <= gap <= 1 for gap in gaps),
            "collision": row["raycast_m"] >= 0,
            "road_surface": len(keys) == 4 and all(key in expected_surfaces for key in keys),
        })
    checks = {
        "track_loaded": track_loaded and any(line.strip() == "STARTING PHYSICS ENGINE" for line in logs),
        "no_track_errors": not track_errors,
        "csp_loaded": bool(csp_version),
        "no_csp_track_errors": not csp_errors,
        "all_points": len(results) == expected and bool(results),
        "frame_rate": len(fps) == len(results) and fps_median is not None and fps_median >= minimum_fps,
        "screenshots": bool(list(directory.glob("shot_*.png"))),
    }
    for key in ("lands", "wheels", "collision", "road_surface"):
        checks[key] = bool(point_checks) and all(point[key] for point in point_checks)
    return {
        "pass": all(checks.values()), "track": track, "checks": checks, "points": point_checks,
        "track_errors": track_errors, "csp_errors": csp_errors, "csp": csp_version,
        "minimum_fps": min(fps, default=None), "median_fps": fps_median, "target_fps": minimum_fps,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("track")
    parser.add_argument("directory", type=Path)
    parser.add_argument("--layout")
    parser.add_argument("--minimum-fps", type=float, default=60)
    parser.add_argument("--surface", action="append", help="Required surface key (can be repeated)")
    args = parser.parse_args()
    root, _, _ = game_paths()
    folder = root / "content" / "tracks" / args.track
    if args.layout:
        folder /= args.layout
    result = report(args.track, args.directory, folder / "data" / "surfaces.ini", args.minimum_fps,
                    set(args.surface) if args.surface else ROAD_SURFACES)
    (args.directory / "report.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["pass"] else 1)


if __name__ == "__main__":
    main()
