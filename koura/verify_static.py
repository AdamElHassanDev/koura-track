"""Run the static Koura build checks and keep reports and raw evidence in out/."""

import argparse
import json
import math
import os
import re
import subprocess
import sys
import tomllib
from collections import Counter
from pathlib import Path

import shapely
from shapely.geometry import LineString

from verify_network import build_zone, verify_network


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
FORK = ROOT / "openlaps"
NAMES = {
    1: "Aerial imagery",
    2: "KN5 structure",
    3: "Mesh index budget",
    4: "Required markers",
    5: "Physical colliders and boundary",
    6: "Terrain draw distance",
    7: "Road steps, seams and holes",
    8: "Slivers and grade breaks",
    9: "Traffic lanes",
    10: "Draw-call estimate",
    11: "Track size",
    12: "Lebanon scenery",
    13: "Fork tests",
    14: "Named route coverage",
    15: "Free-roam scripts",
    16: "Route lengths and scale",
    17: "Road connectivity",
    18: "Start points",
    19: "Road smoothness against build 9",
    20: "Loop climb against build 9",
}
TRAFFIC_ERRORS = (
    "dentro_de_un_cruce", "toques_de_mas", "cruces_sin_entrada", "cruces_sin_salida",
    "cruces_vacios", "entradas_sin_salida", "entradas_sin_reglas", "entradas_sin_luz",
)


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def optional_json(path):
    return read_json(path) if path.is_file() else {}


def match_int(pattern, value):
    result = re.search(pattern, value, re.MULTILINE)
    return int(result[1].replace(",", "")) if result else None


def run(script, arguments, log, *, cwd=ROOT, env=None):
    args = [str(value) for value in (script, *arguments)]
    with log.open("w", encoding="utf-8") as output:
        result = subprocess.run(
            [sys.executable, *args], cwd=cwd, env=env, stdout=output, stderr=subprocess.STDOUT,
            check=False,
        )
    return result.returncode, log.read_text(encoding="utf-8", errors="replace")


def outcome(ok):
    return "pass" if ok else "fail"


def texture_stats(inspection):
    return {
        "meshes": len(inspection["meshes"]),
        "triangles": sum(mesh["t"] for mesh in inspection["meshes"]),
        "textures": len(inspection["textures"]),
        "texture_bytes": sum(texture["size"] for texture in inspection["textures"]),
    }


def mesh_group(name):
    return re.sub(r"^\d+[A-Z0-9]+_", "", name).split("_")[0]


def traffic_measurements(track, stage, sidecar, geo, tool_output):
    summary = dict(re.findall(r"^(\w+): ([\d.]+)$", tool_output, re.MULTILINE))
    if not all(key in summary for key in TRAFFIC_ERRORS):
        raise ValueError("Traffic report is missing error counters")
    errors = {key: float(summary[key]) for key in TRAFFIC_ERRORS if float(summary[key])}
    raw_lanes = read_json(track / "data/traffic.json")["lanes"]
    lanes = [lane for lane in raw_lanes if not lane["name"].startswith("~")]
    malformed = [
        lane["id"] for lane in lanes
        if len(lane["points"]) < 2 or any(
            len(point) != 3 or not all(math.isfinite(number) for number in point)
            for point in lane["points"]
        )
    ]
    stats = {"lanes": len(lanes), "errors": errors, "malformed": malformed}
    zone = build_zone(stage, sidecar, geo)
    if zone is None:
        return "unavailable", stats
    # traffic.json rounds each coordinate to the nearest centimetre.
    rounded_zone = zone.buffer(0.01)
    shapely.prepare(rounded_zone)
    outside = [
        lane["id"] for lane in lanes if lane["id"] not in malformed and not rounded_zone.covers(
            LineString((x, -z) for x, _, z in lane["points"])
        )
    ]
    stats.update({"outside_zone": outside, "coordinate_tolerance_m": 0.01})
    return outcome(lanes and not (errors or malformed or outside)), stats


def style_measurements(log, geo):
    region = "lb" if (
        geo.get("vivo_opc", {}).get("region") == "lb" or re.search(r"^Región: Lebanon\b", log, re.M)
    ) else geo.get("vivo_opc", {}).get("region")
    olives = match_int(r"^\s*vegetación[^\n]*\bolivo ([\d,]+)", log)
    built = match_int(r"edificios construidos:\s*([\d,]+)", log)
    footprints = match_int(r"zona externa:[^\n]*\(([\d,]+) de [\d,]+ edificios\)", log)
    if footprints is None:
        footprints = match_int(r"edificios:[^\n]*=\s*([\d,]+)", log)
    difference = 100 * abs(built - footprints) / footprints if footprints and built is not None else None
    stats = {"region": region, "olives": olives, "buildings": built, "expected_footprints": footprints,
             "building_difference_pct": difference}
    if not log:
        return "unavailable", stats
    return outcome(region == "lb" and olives and difference is not None and difference <= 10), stats


def verify(stage, output, name, build_log, report, baseline, config):
    track = output / "assetto_corsa" / name
    glb = output / f"{name}.glb"
    kn5 = track / f"{name}.kn5"
    sidecar = output / f"{name}.roads.json"
    geo_path = track / "openlaps_geo.json"
    evidence = report.parent / "verify"
    evidence.mkdir(exist_ok=True, parents=True)
    progress = (ROOT / "handoff/PROGRESS.md").read_text(encoding="utf-8")
    reserve_lifted = bool(re.search(r"^\|[^\n]*\|\s*Road-height reserve lifted\s*\|", progress, re.M))
    options = config.get("verification", {})
    env = os.environ.copy()
    env.setdefault("OPENLAPS_CACHE", str(ROOT / config["cache"]))
    env.setdefault("OPENBLAS_NUM_THREADS", "1")
    checks = {}

    def add(number, status, measured, *raw, hard=True):
        checks[number] = {
            "name": NAMES[number], "status": status, "hard": hard, "measured": measured,
            "raw_output_paths": [os.path.relpath(path, report.parent) for path in raw if path.exists()],
        }

    def tool(number, script, arguments, log_name=None, *, cwd=ROOT, hard=True):
        raw = evidence / (log_name or f"{Path(script).stem}.log")
        rc, captured = run(script, arguments, raw, cwd=cwd, env=env)
        if rc:
            for index in number if isinstance(number, tuple) else (number,):
                add(index, "fail", {"exit_code": rc}, raw, hard=hard)
        return rc, captured, raw

    geo = optional_json(geo_path)
    log = build_log.read_text(encoding="utf-8", errors="replace") if build_log.is_file() else ""
    imagery = re.search(r"^\s*ortofoto lb_xyz:\s*(\d+) ok,\s*(\d+) failed\b", log, re.M)
    if imagery:
        ok, failed = map(int, imagery.groups())
        add(1, outcome(ok > 0 and failed * 100 <= ok), {"ok": ok, "failed": failed}, build_log)
    else:
        add(1, "not_applicable" if baseline else "unavailable", {"reason": "No lb_xyz tile counters"}, build_log)

    rc, captured, raw = tool(2, FORK / "tools/kn5_check.py", [kn5])
    if rc == 0:
        add(2, outcome("KN5 OK" in captured), {"has_kn5_ok": "KN5 OK" in captured}, raw)

    inspect_json = evidence / "kn5.json"
    ui_path = track / "ui/ui_track.json"
    lod_required = options.get("terrain_lod_required", False)
    rc, _, raw = tool((3, 4, 5, 6, 11), FORK / "tools/kn5_inspect.py", [kn5, "--json", inspect_json])
    if rc == 0:
        inspection = read_json(inspect_json)
        meshes = inspection["meshes"]
        max_vertices = max((mesh["v"] for mesh in meshes), default=0)
        add(3, outcome(0 < max_vertices <= 65000), {"max_vertices": max_vertices}, inspect_json)
        markers = Counter(item[1] for item in inspection["dummies"])
        pits = sum(count for key, count in markers.items() if re.fullmatch(r"AC_PIT_\d+", key))
        pitboxes = optional_json(ui_path).get("pitboxes")
        good_pits = pitboxes is not None and str(pitboxes).isdigit() and pits == int(pitboxes)
        add(4, outcome(markers["AC_PIT_0"] == markers["AC_START_0"] == 1 and good_pits),
            {"pit_markers": pits, "pitboxes": pitboxes, "AC_PIT_0": markers["AC_PIT_0"],
             "AC_START_0": markers["AC_START_0"]}, inspect_json, ui_path)
        physics = [mesh["name"] for mesh in meshes if re.match(r"^\d+WALL_", mesh["name"])]
        col = sum(mesh_group(mesh) == "col" for mesh in physics)
        boundary = sum(mesh_group(mesh) == "limite" for mesh in physics)
        collision_status = outcome(col > 0 and boundary > 0)
        if baseline and collision_status == "fail":
            collision_status = "expected_fail"
        elif col and not boundary:
            # Legacy tracks put trunks and the edge wall in a shared mesh group.
            collision_status = "unavailable"
        add(5, collision_status, {"scenery_collider_meshes": col, "boundary_meshes": boundary}, inspect_json)

        terrain = [mesh for mesh in meshes if mesh_group(mesh["name"]) == "terreno"]
        underlayer = [mesh for mesh in meshes if mesh_group(mesh["name"]) in {"horizonte", "suelo_base"}]
        all_lod = bool(terrain and underlayer) and all(mesh["lod"][1] > 0 for mesh in terrain) and all(
            mesh["lod"][1] == 0 for mesh in underlayer
        )
        lod_status = outcome(all_lod) if lod_required else ("pass" if all_lod else "expected_fail")
        add(6, lod_status, {"terrain_meshes": len(terrain), "terrain_with_lod": sum(m["lod"][1] > 0 for m in terrain),
                            "underlayer_meshes": len(underlayer),
                            "underlayer_with_lod": sum(m["lod"][1] > 0 for m in underlayer)},
            inspect_json, hard=lod_required)

        stats = texture_stats(inspection)
        stats["kn5_bytes"] = kn5.stat().st_size
        stats["track_tree_bytes"] = sum(path.stat().st_size for path in track.rglob("*") if path.is_file())
        size_required = stage in {"S2", "S3"}
        add(11, outcome(not size_required or stats["kn5_bytes"] < 2_000_000_000), stats,
            inspect_json, kn5, hard=size_required)
        try:
            network_checks = verify_network(stage, sidecar, inspection, geo, glb=glb if glb.is_file() else None)
        except (KeyError, OSError, ValueError) as error:
            for number in (14, 16, 17, 18):
                add(number, "unavailable", {"reason": str(error)}, sidecar, geo_path, inspect_json)
        else:
            network_raw = evidence / "network.json"
            network_raw.write_text(json.dumps(network_checks, indent=2, allow_nan=False) + "\n", encoding="utf-8")
            for number, result in network_checks.items():
                add(number, result["status"], result["measured"], network_raw, sidecar, geo_path, inspect_json)
    else:
        for number in (14, 16, 17, 18):
            add(number, "unavailable", {"reason": "KN5 inspection failed"}, raw)

    stats_path = output / f"{name}.json"
    road_km = optional_json(stats_path).get("carreteras", {}).get("km")
    resolution = str(float(geo.get("vivo_opc", {}).get("res", 0))).removesuffix(".0")
    ref = options.get("surface", {}).get(resolution)
    rc, captured, raw = tool(7, HERE / "verify_surface.py", [glb], "surface.json")
    if rc == 0:
        stats = json.loads(captured)
        totals = {"road_km": road_km, "terrain_res_m": resolution}
        for key in ("steps", "seams", "holes"):
            totals[f"{key}_sites"] = stats[key]["sites"]
            totals[f"{key}_cells"] = stats[key]["hits"]
            totals[f"{key}_sites_per_km"] = stats[key]["sites"] / road_km if road_km else None
        status = "unavailable"
        if road_km and ref:
            totals["reference_steps_per_km"] = ref["step_sites"] / ref["road_km"]
            totals["reference_seams_per_km"] = ref["seam_sites"] / ref["road_km"]
            status = outcome(
                stats["holes"]["hits"] == 0
                and totals["steps_sites_per_km"] <= totals["reference_steps_per_km"]
                and totals["seams_sites_per_km"] <= totals["reference_seams_per_km"]
            )
        add(7, status, totals, raw, stats_path)

    rc, captured, raw = tool(8, FORK / "tools/defectos.py", [glb])
    if rc == 0:
        steep = match_int(r"; ([\d,]+) con pendiente >", captured)
        breaks = match_int(r"^\s*escalones en la calzada[^\n]*:\s*([\d,]+)", captured)
        stats = {"road_km": road_km, "terrain_res_m": resolution, "steep_triangles": steep,
                 "grade_break_pairs": breaks}
        status = "unavailable"
        if road_km and ref and steep is not None and breaks is not None:
            stats.update({"steep_per_km": steep / road_km, "breaks_per_km": breaks / road_km,
                          "reference_steep_per_km": ref["steep_triangles"] / ref["road_km"],
                          "reference_breaks_per_km": ref["grade_break_pairs"] / ref["road_km"]})
            status = outcome(stats["steep_per_km"] <= stats["reference_steep_per_km"] and
                             stats["breaks_per_km"] <= stats["reference_breaks_per_km"])
        add(8, status, stats, raw, stats_path)

    rc, captured, raw = tool(9, FORK / "tools/trafico_check.py", [track])
    if rc == 0:
        try:
            status, stats = traffic_measurements(track, stage, sidecar, geo, captured)
        except (KeyError, OSError, ValueError) as error:
            add(9, "fail", {"reason": str(error)}, raw, geo_path, sidecar)
        else:
            add(9, status, stats, raw, geo_path, sidecar, track / "data/traffic.json")

    draw_cap = options.get("draw_calls_p95")
    rc, captured, raw = tool(10, FORK / "tools/rendimiento_ac.py", [kn5, "--grupos"], hard=draw_cap is not None)
    if rc == 0:
        calls = re.search(r"a la vista:\s*([\d,]+) llamadas \(p95 ([\d,]+)\)", captured)
        if calls:
            median, p95 = (int(number.replace(",", "")) for number in calls.groups())
            add(10, outcome(draw_cap is None or p95 <= draw_cap), {"median": median, "p95": p95, "cap": draw_cap},
                raw, hard=draw_cap is not None)
        else:
            add(10, "unavailable", {"reason": "Draw-call counters missing"}, raw, hard=draw_cap is not None)

    status, style = style_measurements(log, geo)
    add(12, status, style, build_log, geo_path)

    rc, captured, raw = tool(13, "-m", ["pytest", "-q"], "pytest.log", cwd=FORK)
    if rc == 0:
        passed = match_int(r"(\d+) passed", captured)
        skipped = match_int(r"(\d+) skipped", captured) or 0
        add(13, outcome(passed and passed > 0), {"passed": passed, "skipped": skipped}, raw)

    extension = track / "extension"
    ext = extension / "ext_config.ini"
    scripts = sorted(str(path.relative_to(track)) for path in extension.rglob("*") if path.name.lower() == "vivo.lua")
    live_directive = re.compile(r"^\s*SCRIPT\s*=\s*vivo\.lua\s*(?:[;#].*)?$", re.I | re.M)
    references = bool(ext.is_file() and live_directive.search(ext.read_text(encoding="utf-8", errors="replace")))
    add(15, outcome(track.is_dir() and not scripts and not references),
        {"vivo_scripts": scripts, "vivo_directive": references}, ext, *[track / script for script in scripts])

    if stage not in {"S2", "S3"} or reserve_lifted:
        reason = "Road-height reserve lifted" if reserve_lifted else "Stage has no whole-loop build 9 comparison"
        for number in (19, 20):
            add(number, "not_applicable", {"reason": reason})
    else:
        ref9 = options.get("build9", {})
        rc, captured, raw = tool(19, HERE / "survey.py", [glb, "--out", evidence / "survey.json"])
        if rc == 0:
            classes = {key: float(percent) for key, percent in re.findall(
                r"^\s*(\w+)\s+[\d.]+ km\s+>2%:\s*([\d.]+)%", captured, re.M
            )}
            reference = ref9.get("slope_change_over_2_pct", {})
            changes = {key: round(value - reference[key], 8) for key, value in classes.items()
                       if key in reference}
            unreferenced = sorted(classes.keys() - reference.keys())
            status = "unavailable" if not changes or unreferenced else outcome(
                all(value <= 0.2 for value in changes.values())
            )
            add(19, status, {"slope_over_2_pct": classes, "change_percentage_points": changes,
                             "unreferenced_classes": unreferenced}, raw, evidence / "survey.json")

        rc, captured, raw = tool(20, HERE / "elevation.py", [glb])
        if rc == 0:
            climb = match_int(r"^loop\s+\S+\s+\|\s+[-\d]+\.\.[-\d]+\s+(\d+)\s+", captured)
            reference = ref9.get("loop_climb_m")
            status = "unavailable" if climb is None or reference is None else outcome(abs(climb - reference) <= 5)
            add(20, status, {"loop_climb_m": climb, "reference_m": reference}, raw)

    return checks


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", help="Build stage, for example S1, S2, K or poc")
    parser.add_argument("--out", type=Path, help="Build directory (default: out/<stage>)")
    parser.add_argument("--name", help="Track ID, required if the build directory contains multiple tracks")
    parser.add_argument("--build-log", type=Path, help="Build log (default: build.log in the build directory)")
    parser.add_argument("--report", type=Path, help="Report path (default: verify.json in the build directory)")
    parser.add_argument("--baseline", action="store_true", help="Identify an unmodified openlaps trial")
    args = parser.parse_args()
    output = (args.out or ROOT / "out" / args.stage).resolve()
    if args.name:
        name = args.name
    else:
        tracks = sorted(path.name for path in (output / "assetto_corsa").glob("*") if path.is_dir())
        if len(tracks) != 1:
            parser.error(f"expected one track in {output / 'assetto_corsa'}; specify --name")
        name = tracks[0]
    report = (args.report or output / "verify.json").resolve()
    build_log = (args.build_log or output / "build.log").resolve()
    with (HERE / "config.toml").open("rb") as stream:
        config = tomllib.load(stream)
    checks = verify(args.stage, output, name, build_log, report, args.baseline, config)
    summary = dict(sorted(Counter(check["status"] for check in checks.values()).items()))
    hard_failures = [number for number, check in sorted(checks.items())
                     if check["hard"] and check["status"] in {"fail", "unavailable"}]
    payload = {"stage": args.stage, "track": name, "stock_baseline": args.baseline, "summary": summary,
               "hard_failures": hard_failures, "checks": dict(sorted(checks.items()))}
    temporary = report.with_suffix(".json.part")
    temporary.write_text(json.dumps(payload, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    temporary.replace(report)
    print(f"{args.stage}/{name}: " + ", ".join(f"{value} {status}" for status, value in summary.items()))
    for number in hard_failures:
        print(f"  {number:2}: {checks[number]['status']:12} {checks[number]['name']}")
    print(f"Report: {report}")
    return int(bool(hard_failures))


if __name__ == "__main__":
    sys.exit(main())
