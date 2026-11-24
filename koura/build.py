"""Koura build driver. Reads handoff/inputs/zone.json, pins the origin, builds the stage's zone polygon and
calls the fork's pipeline.  Usage (from the project root):

    (ulimit -v 21000000; .venv/bin/python koura/build.py S1)        # or S2

Options: --res N (terrain grid, default from zone.json), --buf M (override route buffer), --name ID,
--no-imagery, --no-canopy, --overrides DIR, --out DIR, --fine-kart-imagery.
Kart site: --kart-survey PATH, --kart-layout (requires surveyed timing and pit positions).
Performance profile: --performance baseline|lod|horizon|atlas|full.
Background ground trial: --background on stages with a background part.
"""
import sys, os, json, math, time, subprocess
from pathlib import Path
from functools import partial
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("OPENLAPS_CACHE", os.path.join(ROOT, "cache"))
sys.path.insert(0, os.path.join(ROOT, "openlaps")); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from concurrent.futures import ThreadPoolExecutor
from shapely.geometry import Point
from openlaps import pipeline
from openlaps.__main__ import parser
from openlaps.geo import BBox, LocalProjection
from openlaps.sources import osm as OSM, rasters
import kart_pts
from kart_geometry import read_layout
from stages import stage_zone
from verify_network import record_network
from openlaps import roads as _roads

ZONE = json.load(open(os.path.join(ROOT, "handoff", "inputs", "zone.json")))
def opt(name, default=None):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default
STAGE = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("-") else "S1"
RES = opt("--res", str(ZONE["stages"][STAGE].get("terrain_res_m", 4)))
BUF = float(opt("--buf", 0)) or None
TIMED_KART = "--kart-layout" in sys.argv
NAME = opt("--name", "koura_karting_mania" if TIMED_KART else "koura")
OUT = str(Path(opt("--out", Path(ROOT, "out", STAGE))).resolve())
log = lambda *a: print(*a, flush=True)
PERFORMANCE_STEPS = ("baseline", "lod", "horizon", "atlas", "full")
performance = opt("--performance", "full")
if performance not in PERFORMANCE_STEPS:
    raise SystemExit(f"--performance must be one of: {', '.join(PERFORMANCE_STEPS)}")
perf_step = PERFORMANCE_STEPS.index(performance)

# ---- pinned origin and build rectangle (local metres) from zone.json
O = ZONE["origin"]
rect = tuple(float(v) for v in ZONE["stages"][STAGE]["expected"]["rect_local_m"])
proj = LocalProjection.marco(O["lat"], O["lon"], rect)
bbox = proj.bbox()
zona = stage_zone(ZONE, STAGE, proj, BUF)
log(f"stage {STAGE}: rect {rect}, zone {zona.area / 1e6:.2f} km2 (expected {ZONE['stages'][STAGE]['expected']['zone_km2']}), origin {O['lat']},{O['lon']}")

def fetch_osm():
    cache = Path(ROOT, "cache", "osm_koura.json")
    snapshot = Path(ROOT, "koura", "data", "osm_koura.json")
    for path in (snapshot, cache):
        if path.exists():
            data = json.loads(path.read_text())
            # The generator smooths the full graph before clipping it. Keep
            # the original graph inputs for the established stages.
            baseline = data.get("build9_road_scope", {})
            if STAGE in baseline.get("stages", ()):
                data["elements"] = data["elements"][:baseline["element_count"]]
            return data
    # Recover the full S3 snapshot if neither local copy is present.
    r3 = tuple(float(v) for v in ZONE["stages"]["S3"]["expected"]["rect_local_m"])
    big = LocalProjection.marco(O["lat"], O["lon"], r3).bbox().padded(300)
    els, seen, N = [], set(), 3
    for i in range(N):
        for j in range(N):
            q = BBox(big.south + (big.north - big.south) * i / N, big.west + (big.east - big.west) * j / N,
                     big.south + (big.north - big.south) * (i + 1) / N, big.west + (big.east - big.west) * (j + 1) / N)
            qt = OSM.query(q); ok = False
            for attempt in range(12):
                ep = OSM.ENDPOINTS[(attempt + 1) % len(OSM.ENDPOINTS)]
                try:
                    r = subprocess.run(["curl", "-s", "-m", "200", "-A", "osm-research-script/1.0", "--data-urlencode", "data=" + qt, ep],
                                       capture_output=True, timeout=220)
                    d = json.loads(r.stdout)
                    if "elements" in d and not d.get("remark", "").startswith("runtime error"):
                        ok = True; break
                except Exception:  # noqa
                    pass
                time.sleep(6 + 4 * attempt)
            if not ok:
                raise SystemExit(f"OSM tile {i},{j} failed")
            for el in d["elements"]:
                key = (el["type"], el["id"])
                if key not in seen:
                    seen.add(key); els.append(el)
            log(f"  osm tile {i},{j}: {len(d['elements'])} elements via {ep}")
            time.sleep(3)
    data = {"elements": els, "fetched": time.strftime("%Y-%m-%d")}
    json.dump(data, open(cache, "w"))
    return data

def px2ll(p):
    return {"lon": 35.851135 + p[0] * 0.0000026823, "lat": 34.328694 - p[1] * 0.0000022148}

def inject_kart(data):
    """Rough Karting Mania from hand-placed points on evidence/karting_mania_aerial.png (replaced by WP11)."""
    els = data["elements"]; nid = [-1000]; ids = {}
    def node(p):
        if p not in ids:
            nid[0] -= 1; ids[p] = nid[0]
        return ids[p]
    def way(wid, pts, width, name):
        return {"type": "way", "id": wid, "tags": {"highway": "service", "width": str(width), "surface": "asphalt", "name": name, "lanes": "1"},
                "nodes": [node(p) for p in pts], "geometry": [px2ll(p) for p in pts]}
    e0 = px2ll(kart_pts.ENTR2[0]); best = None; c = math.cos(math.radians(34.33))
    for el in els:
        if el["type"] != "way" or "geometry" not in el or el.get("tags", {}).get("highway") not in ("unclassified", "residential", "tertiary", "secondary", "service", "track"):
            continue
        g = el["geometry"]
        for k in range(len(g) - 1):
            ax, ay = (g[k]["lon"] - e0["lon"]) * 111320 * c, (g[k]["lat"] - e0["lat"]) * 111320
            bx, by = (g[k + 1]["lon"] - e0["lon"]) * 111320 * c, (g[k + 1]["lat"] - e0["lat"]) * 111320
            dx, dy = bx - ax, by - ay; L2 = dx * dx + dy * dy
            t = 0 if L2 == 0 else max(0, min(1, -(ax * dx + ay * dy) / L2))
            d = math.hypot(ax + t * dx, ay + t * dy)
            if best is None or d < best[0]:
                best = (d, el, k, t)
    d, el, k, t = best; g = el["geometry"]
    jn = {"lon": g[k]["lon"] + t * (g[k + 1]["lon"] - g[k]["lon"]), "lat": g[k]["lat"] + t * (g[k + 1]["lat"] - g[k]["lat"])}
    jid = node(("join",))
    el["geometry"].insert(k + 1, jn); el["nodes"].insert(k + 1, jid)
    log(f"  kart entrance joined to way {el['id']} at {d:.1f} m")
    wE = way(-4, kart_pts.ENTR2, 5, "Karting Mania entrance"); wE["nodes"][0] = jid; wE["geometry"][0] = jn
    els += [wE]
    return data


def connect_crossings(data):
    """Roads that cross, or end within 4 m of another road, without sharing a point in the map data. The generator
    then builds two unrelated roads on top of each other at different heights and merges them with a pit or a
    step of up to 2 m (the owner's "big bumps or recessions"), and the roads are not connected for driving.
    A shared point is added so the place becomes a normal junction. Bridges, tunnels and layered ways are left."""
    import shapely
    from shapely.geometry import LineString as LS, Point as PT
    DRIV = {"motorway", "trunk", "primary", "secondary", "tertiary", "unclassified", "residential", "living_street", "service", "track", "road",
            "motorway_link", "trunk_link", "primary_link", "secondary_link", "tertiary_link"}
    ways = [el for el in data["elements"] if el.get("type") == "way" and el.get("tags", {}).get("highway") in DRIV and "geometry" in el
            and len(el["geometry"]) >= 2 and not any(k in el["tags"] for k in ("bridge", "tunnel", "layer", "covered"))]
    lines, xy = [], []
    for el in ways:
        x, y = proj.to_local(np.array([g["lon"] for g in el["geometry"]]), np.array([g["lat"] for g in el["geometry"]]))
        xy.append(np.c_[x, y]); lines.append(LS(np.c_[x, y]))
    tree = shapely.STRtree(lines)
    uso = {}
    for el in ways:
        for n in el["nodes"]:
            uso[n] = uso.get(n, 0) + 1
    nid = [-900000]; ins = {}          # way index -> [(dist along, x, y, node id)]
    def nuevo(i, j, pt):
        nid[0] -= 1
        for k in (i, j):
            ins.setdefault(k, []).append((float(lines[k].project(pt)), pt.x, pt.y, nid[0]))
        return nid[0]
    def cerca_de_nodo_comun(i, j, pt, r=3.0):
        com = set(ways[i]["nodes"]) & set(ways[j]["nodes"])
        if not com:
            return False
        ni = np.array([k for k, n in enumerate(ways[i]["nodes"]) if n in com])
        return bool((np.hypot(xy[i][ni, 0] - pt.x, xy[i][ni, 1] - pt.y) < r).any())
    nx_ = ne_ = 0
    a, b = tree.query(lines, predicate="crosses")
    for i, j in zip(a.tolist(), b.tolist()):
        if i >= j:
            continue
        g = lines[i].intersection(lines[j])
        for pt in ([g] if g.geom_type == "Point" else [q for q in getattr(g, "geoms", []) if q.geom_type == "Point"]):
            if not cerca_de_nodo_comun(i, j, pt):
                nuevo(i, j, pt); nx_ += 1
    # loose ends close to another road
    for i, el in enumerate(ways):
        for end in (0, -1):
            n = el["nodes"][end]
            if uso.get(n, 0) != 1:
                continue
            pt = PT(xy[i][end])
            for j in tree.query(pt.buffer(4.0)).tolist():
                if j == i or lines[j].distance(pt) > 4.0 or cerca_de_nodo_comun(i, j, pt, 6.0):
                    continue
                q = lines[j].interpolate(lines[j].project(pt))
                nid[0] -= 1
                ins.setdefault(j, []).append((float(lines[j].project(q)), q.x, q.y, nid[0]))
                lon, lat = proj.to_lonlat(q.x, q.y)
                el["nodes"][end] = nid[0]; el["geometry"][end] = {"lat": float(lat), "lon": float(lon)}
                ne_ += 1
                break
    for k, lst in ins.items():
        el = ways[k]; P = xy[k]
        s_ = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))])
        for d, x, y, n in sorted(lst, reverse=True):
            seg = int(np.clip(np.searchsorted(s_, d, side="right"), 1, len(s_) - 1))
            lon, lat = proj.to_lonlat(x, y)
            el["nodes"].insert(seg, n); el["geometry"].insert(seg, {"lat": float(lat), "lon": float(lon)})
    log(f"  map data repaired: {nx_} unconnected crossings joined, {ne_} loose road ends joined to the road beside them")
    return data


def kart_polygon():
    """Asphalt outline of Karting Mania in local metres: the traced racing line widened to the track width, plus
    the paddock strip. Built as one smooth surface by openlaps.roads._pista_kart."""
    from scipy.interpolate import splprep, splev
    from shapely.geometry import LinearRing, Polygon
    from shapely.ops import unary_union
    def loc(pts):
        ll = [px2ll(p) for p in pts]
        x, y = proj.to_local(np.array([q["lon"] for q in ll]), np.array([q["lat"] for q in ll]))
        return np.c_[x, y]
    P = loc(kart_pts.TRACK)
    tck, _ = splprep([np.r_[P[:, 0], P[0, 0]], np.r_[P[:, 1], P[0, 1]]], s=len(P) * 0.15, per=True)
    xs, ys = splev(np.linspace(0, 1, 1200), tck)
    ring = LinearRing(np.c_[xs, ys])
    poly = unary_union([ring.buffer(kart_pts.TRACK_WIDTH_M / 2, join_style=1), Polygon(loc(kart_pts.PADDOCK))]).buffer(0)
    return poly, ring.length

def prefetch_imagery(ground):
    """Download every zoom 18 tile under the zone (plus 150 m) in parallel, so the build only reads from disk."""
    r = rasters.XYZRaster("lb_xyz", log=log)
    z = ground.buffer(150)
    x0, y0, x1, y1 = z.bounds
    lon, lat = proj.to_lonlat(np.array([x0, x1]), np.array([y0, y1]))
    px, py = r.tiles_for_lonlat(lon, lat)
    txs = range(int(px.min() // 256), int(px.max() // 256) + 1); tys = range(int(py.min() // 256), int(py.max() // 256) + 1)
    import shapely
    todo = []
    for tx in txs:
        for ty in tys:
            lo = (tx + 0.5) / r.n * 360 - 180
            la = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * (ty + 0.5) / r.n))))
            cx, cy = proj.to_local(lo, la)
            if z.distance(Point(float(cx), float(cy))) < 130:
                todo.append((tx, ty))
    t0 = time.time()
    with ThreadPoolExecutor(8) as ex:
        res = list(ex.map(lambda t: r.fetch_tile(*t) is not None, todo))
    log(f"  imagery prefetch: {sum(res)} of {len(todo)} tiles on disk in {time.time() - t0:.0f} s")
    return sum(res), len(todo)

argv = ["--bbox", f"{bbox.south},{bbox.west},{bbox.north},{bbox.east}", "--modo", "libre", "--ac", "--res", RES, "--mpp", "0.5",
        "--region", "lb", "--nombre", NAME, "--titulo", opt("--title", "Koura"), "--salida", OUT]
if "--no-imagery" in sys.argv: argv.append("--sin-orto")
if "--no-canopy" in sys.argv: argv.append("--sin-dosel")
args = parser().parse_args(argv)
args.koura_terrain_lod = 1500 if perf_step >= 1 else 0
args.koura_horizon_underlayer = perf_step >= 2
args.koura_terrain_atlas = perf_step >= 3
args.koura_material_library = perf_step < 4
log(f"  performance profile: {performance}")
if "--background" in sys.argv:
    from background_roads import find_connectors
    from measure_background import coverage, measure

    background_part = next((part for part in ZONE["stages"][STAGE]["parts"]
                            if part["type"] == "background"), None)
    if background_part is None:
        raise SystemExit(f"Stage {STAGE} has no background ground definition")

    def measure_ground(active_proj, detailed, dem, osm_data, buildings, sea):
        result = coverage(ZONE, active_proj, detailed, dem, stage=STAGE, sea=sea,
                          max_outside_m=background_part.get("max_outside_m"))
        report = measure(result, detailed, active_proj, osm_data, buildings)
        evidence = Path(OUT, f"{NAME}.background.json")
        evidence.parent.mkdir(parents=True, exist_ok=True)
        evidence.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        log(f"  fondo: {result.fill.area / 1e6:.2f} km² medidos desde {result.observer_count} puntos")
        if not args.sin_orto and not result.fill.is_empty:
            prefetch_imagery(result.fill)
        return result

    args.koura_background_coverage = measure_ground
    args.koura_background_link_audit = find_connectors
    args.koura_draw_distances = {"calzada": 1800, "edificios": 1500, "rayas": 1100}
args.koura_overrides = Path(opt("--overrides", Path(ROOT, "koura", "overrides"))).resolve()
if "--overrides" in sys.argv and not args.koura_overrides.is_dir():
    raise SystemExit(f"Override directory does not exist: {args.koura_overrides}")
if (TIMED_KART or "--fine-kart-imagery" in sys.argv) and not args.sin_orto:
    fine = ZONE["fine_boxes"]["karting_mania"]
    sw = proj.to_local(fine["west"], fine["south"])
    ne = proj.to_local(fine["east"], fine["north"])
    args.koura_fine_ground = {
        "fine_boxes": [(*sw, *ne)],
        "fine_ortho": rasters.XYZRaster("lb_xyz", log=log, zoom=19),
    }
kart_path = Path(opt("--kart-survey", args.koura_overrides / "karting_mania.json"))
kart_data = None
if kart_path.is_file():
    kart_data, kart = read_layout(kart_path, proj)
elif TIMED_KART or "--kart-survey" in sys.argv:
    raise SystemExit(f"Karting Mania survey file does not exist: {kart_path}")

if TIMED_KART:
    from kart_layout import TRACK_ID, prepare_layout, write_layout
    from openlaps.koura_scenery import _RoadSurface

    if STAGE != "K" or NAME != TRACK_ID:
        raise SystemExit(f"--kart-layout requires stage K and track ID {TRACK_ID}")
    required = ("direction", "start_line", "grid", "pit_lane", "pit_boxes", "hotlap_start")
    missing = [field for field in required if not kart_data.get(field)]
    if missing:
        raise SystemExit(f"Karting Mania timing survey is missing: {', '.join(missing)}")

    def prepare_kart(scene, active_proj, terrain):
        surface = _RoadSurface(scene, {"KART", "PITLANE"}).sampler(kart["poly"], None)
        return prepare_layout(scene, active_proj, kart_data, surface, lambda xy: terrain.height(*xy.T))

    args.koura_layout = (prepare_kart, partial(write_layout, material_library=args.koura_material_library))
    args.sin_trafico = True
args.zona_fn = lambda p: zona
sp = [s for s in ZONE["spawn_points"] if zona.contains(Point(*[float(v) for v in proj.to_local(s["lon"], s["lat"])]))]
args.spawns = [tuple(float(v) for v in proj.to_local(s["lon"], s["lat"])) for s in sp]
for i, s in enumerate(sp): log(f"slot {i}: {s['name']}")
os.environ.setdefault("KOURA_CELDA", "0.5" if zona.area < 12e6 and (rect[2] - rect[0]) * (rect[3] - rect[1]) < 30e6 else "1.5")
if "--no-imagery" not in sys.argv: prefetch_imagery(zona)
raw = connect_crossings(inject_kart(fetch_osm()))
from openlaps import config as _C
_C.CURB_HEIGHT = 0.05      # owner: kerbs were too high and broke the car; low enough to ride over
_C.SIDEWALK_CLASSES = set()  # owner: the grey paved strips at junctions looked like parking strips and the kerbs broke the car.
                             # Koura village roads have almost no pavements; WP12 adds real ones where they exist
if kart_data is None:
    polygon, length = kart_polygon()
    kart = {"poly": polygon, "name": "Karting Mania", "length": length}
if zona.covers(kart["poly"].centroid):
    if kart_data is not None and not zona.covers(kart["poly"]):
        raise SystemExit("The selected stage cuts through the surveyed Karting Mania site")
    _roads.KART = kart
    log(f"  Karting Mania: racing line {kart['length']:.1f} m, paved area {kart['poly'].area:.0f} m2")
    if kart_data is not None and any(kart_data.get(key) for key in ("kerbs", "barriers", "poles", "markings")):
        from kart_scenery import build as build_kart_scenery

        args.koura_kart_scenery = partial(build_kart_scenery, data=kart_data)
t0 = time.time()
with record_network(_roads, Path(OUT) / f"{NAME}.roads.json", sp):
    pipeline.run(args, proj=proj, osm_data=OSM.parse(raw))
log(f"BUILD DONE in {time.time() - t0:.0f} s")
