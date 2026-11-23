"""Preview build of the Koura S2 zone with a patched openlaps copy. Not the plan's implementation: a quick
drivable preview. Run from preview/openlaps with the Python 3.12 env:  python ../build_preview.py [--res N] [--buf M]"""
import sys, os, json, math, time, dataclasses, subprocess
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "openlaps"))
import numpy as np
from shapely.geometry import LineString, Point, box
from shapely.ops import unary_union
from openlaps import regions, pipeline
from openlaps.__main__ import parser
from openlaps.geo import BBox
from openlaps.sources import osm as OSM
from kart_pts import A, B, SL, ENTR

ZONE = json.load(open("/home/adamelhassan/Dev/Personal/Assetto_Mant2a/handoff/inputs/zone.json"))
RES = sys.argv[sys.argv.index("--res") + 1] if "--res" in sys.argv else "4"
BUF = float(sys.argv[sys.argv.index("--buf") + 1]) if "--buf" in sys.argv else None
OUT = os.path.join(HERE, "out")
V = ZONE["villages"]

def parts_ll():
    """S2 parts as (kind, data) in lat/lon."""
    s1 = ZONE["stages"]["S1"]["parts"][0]
    out = [("box", s1)]
    for p in ZONE["stages"]["S2"]["parts"]:
        if p["type"] == "route_buffer":
            out.append(("line", (ZONE["routes"][p["route"]]["polyline"], BUF or p["metres"])))
        elif p["type"] == "disc":
            v = V[p["village"]]; out.append(("disc", (v["lat"], v["lon"], p["metres"])))
        elif p["type"] == "box":
            out.append(("box", p))
    return out

def zona_fn(proj):
    gs = []
    for k, d in parts_ll():
        if k == "box":
            x0, y0 = proj.to_local(d["west"], d["south"]); x1, y1 = proj.to_local(d["east"], d["north"])
            gs.append(box(float(x0), float(y0), float(x1), float(y1)))
        elif k == "line":
            pl, m = d
            x, y = proj.to_local([p[1] for p in pl], [p[0] for p in pl])
            gs.append(LineString(np.column_stack([x, y])).buffer(m, quad_segs=4))
        else:
            x, y = proj.to_local(d[1], d[0]); gs.append(Point(float(x), float(y)).buffer(d[2], quad_segs=8))
    # kart access/entrance: make sure the entrance driveway is inside
    return unary_union(gs).buffer(0)

# bbox: lat/lon bounds of everything + ~300 m
lats, lons = [], []
for k, d in parts_ll():
    if k == "box": lats += [d["south"], d["north"]]; lons += [d["west"], d["east"]]
    elif k == "line": lats += [p[0] for p in d[0]]; lons += [p[1] for p in d[0]]
    else: lats.append(d[0]); lons.append(d[1])
mlat = 550 / 111320.0; mlon = 550 / (111320.0 * math.cos(math.radians(34.33)))
bbox = BBox(min(lats) - mlat, min(lons) - mlon, max(lats) + mlat, max(lons) + mlon)
print("bbox", bbox.south, bbox.west, bbox.north, bbox.east, flush=True)

def fetch_osm(bb):
    cache = os.path.join(HERE, "osm_raw.json")
    if os.path.exists(cache):
        return json.load(open(cache))
    big = bb.padded(200)
    els, seen = [], set()
    N = 3
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
                except Exception as e:  # noqa
                    pass
                time.sleep(6 + 4 * attempt)
            if not ok:
                raise SystemExit(f"OSM quarter {i},{j} failed")
            for el in d["elements"]:
                key = (el["type"], el["id"])
                if key not in seen:
                    seen.add(key); els.append(el)
            print(f"  osm tile {i},{j}: {len(d['elements'])} elements via {ep}", flush=True)
            time.sleep(3)
    data = {"elements": els}
    json.dump(data, open(cache, "w"))
    return data

def px2ll(p):
    return {"lon": 35.851135 + p[0] * 0.0000026823, "lat": 34.328694 - p[1] * 0.0000022148}

def inject_kart(data):
    els = data["elements"]
    nid = [-1000]
    ids = {}
    def node(p):
        if p not in ids:
            nid[0] -= 1; ids[p] = nid[0]
        return ids[p]
    def way(wid, pts, width, name):
        return {"type": "way", "id": wid, "tags": {"highway": "service", "width": str(width), "surface": "asphalt", "name": name, "lanes": "1"},
                "nodes": [node(p) for p in pts], "geometry": [px2ll(p) for p in pts]}
    # join the entrance to the nearest existing highway way: insert a node into it
    e0 = px2ll(ENTR[0]); best = None
    c = math.cos(math.radians(34.33))
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
    d, el, k, t = best
    g = el["geometry"]
    jn = {"lon": g[k]["lon"] + t * (g[k + 1]["lon"] - g[k]["lon"]), "lat": g[k]["lat"] + t * (g[k + 1]["lat"] - g[k]["lat"])}
    jid = node(("join",))
    el["geometry"].insert(k + 1, jn); el["nodes"].insert(k + 1, jid)
    print(f"  kart entrance joined to way {el['id']} ({el['tags'].get('highway')}) at {d:.1f} m", flush=True)
    wA = way(-1, A, 8, "Karting Mania"); wB = way(-2, B, 6, "Karting Mania"); wS = way(-3, SL, 6, "Karting Mania")
    wE = way(-4, ENTR, 5, "Karting Mania entrance")
    wE["nodes"][0] = jid; wE["geometry"][0] = jn
    els += [wA, wB, wS, wE]
    return data

argv = ["--bbox", f"{bbox.south},{bbox.west},{bbox.north},{bbox.east}", "--modo", "libre", "--ac", "--res", RES,
        "--sin-dosel", "--sin-orto", "--nombre", "koura_preview", "--titulo", "Koura preview", "--salida", OUT]
args = parser().parse_args(argv)
args.zona_fn = zona_fn
regions.EU = dataclasses.replace(regions.EU, roof="flat", tinaco=True)
regions.REGIONS["eu"] = regions.EU
print("detect ->", regions.detect(34.33, 35.83).code, regions.detect(34.33, 35.83).roof, flush=True)

from openlaps.geo import LocalProjection
proj0 = LocalProjection(bbox)
sx, sy = proj0.to_local([s["lon"] for s in ZONE["spawn_points"]], [s["lat"] for s in ZONE["spawn_points"]])
args.spawns = [(float(a), float(b)) for a, b in zip(sx, sy)]
for s in ZONE["spawn_points"]: print("slot", s["slot"], s["name"], flush=True)

raw = inject_kart(fetch_osm(bbox))
t0 = time.time()
pipeline.run(args, osm_data=OSM.parse(raw))
print(f"BUILD DONE in {time.time() - t0:.0f} s", flush=True)
