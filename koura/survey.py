"""Drives every road of the map numerically and reports where the surface is bad.

  python koura/survey.py out/S2/koura_preview.glb [--n 40] [--out handoff/evidence/survey.json]

Every OSM road in cache/osm_koura.json that has built road under it is walked every 2 m along its centre line.
For each road: the largest change of slope within 8 m (a kink: felt as a bump or a dip) and within 30 m (a wave),
and holes (no road under the line). Roads are grouped by name and class, worst first. A race-track-smooth road
stays under about 2 % in 8 m. Sharp bends of the line itself are not counted."""
import sys, os, json, argparse
import numpy as np
from scipy.spatial import cKDTree
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "..", "openlaps"))
import ride
from openlaps.geo import LocalProjection

p = argparse.ArgumentParser(); p.add_argument("glb"); p.add_argument("--n", type=int, default=40); p.add_argument("--out", default="")
a = p.parse_args()
zone = json.load(open(os.path.join(ride.ROOT, "handoff/inputs/zone.json"))); O = zone["origin"]
proj = LocalProjection.marco(O["lat"], O["lon"], (-100, -100, 100, 100))
T = ride.road_tris(a.glb); tree = cKDTree(T.mean(axis=1)[:, [0, 2]])
osm = json.load(open(os.path.join(ride.ROOT, "cache/osm_koura.json")))
CLS = {"motorway", "trunk", "primary", "secondary", "tertiary", "unclassified", "residential", "living_street", "service", "track",
       "motorway_link", "trunk_link", "primary_link", "secondary_link", "tertiary_link", "road"}
rows = []; tot = {}
for el in osm["elements"]:
    t = el.get("tags", {})
    if el.get("type") != "way" or t.get("highway") not in CLS or "geometry" not in el or len(el["geometry"]) < 2:
        continue
    x, y = proj.to_local(np.array([g["lon"] for g in el["geometry"]]), np.array([g["lat"] for g in el["geometry"]]))
    P = np.c_[x, y]; s = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))])
    keep = np.concatenate([[True], np.diff(s) > 1e-6]); P, s = P[keep], s[keep]
    if len(s) < 2 or s[-1] < 30:
        continue
    S = np.arange(0, s[-1], 2.0); C = np.c_[np.interp(S, s, P[:, 0]), np.interp(S, s, P[:, 1])]
    h = ride.heights(T, tree, 9.0, C[:, 0], -C[:, 1]); ok = np.isfinite(h)
    if ok.sum() < 12:
        continue                      # not built (outside the zone)
    i0, i1 = np.flatnonzero(ok)[[0, -1]]; S, C, h, ok = S[i0:i1 + 1], C[i0:i1 + 1], h[i0:i1 + 1], ok[i0:i1 + 1]
    if len(S) < 20:
        continue
    hf = np.interp(S, S[ok], h[ok]); sl = np.gradient(hf, S) * 100
    tg = np.gradient(C, axis=0); hd = np.unwrap(np.arctan2(tg[:, 1], tg[:, 0]))
    turn = np.zeros(len(S), bool); turn[4:-4] = np.abs(hd[8:] - hd[:-8]) > np.radians(25)
    turn = np.convolve(turn.astype(int), np.ones(9, int), "same") > 0
    d8 = np.zeros(len(S)); d8[2:-2] = np.abs(sl[4:] - sl[:-4]); d8[turn] = 0
    d30 = np.zeros(len(S)); d30[8:-7] = np.abs(sl[15:] - sl[:-15]); d30[turn] = 0
    k = int(np.argmax(d8)); lon, lat = proj.to_lonlat(C[k, 0], C[k, 1])
    cls = t["highway"]; c = tot.setdefault(cls, [0.0, 0, 0, 0])
    c[0] += (S[-1] - S[0]) / 1000; c[1] += int((d8 > 2).sum()); c[2] += int((d8 > 5).sum()); c[3] += len(S)
    rows.append({"way": el["id"], "name": t.get("name:en") or t.get("name") or "", "class": cls, "km": round((S[-1] - S[0]) / 1000, 2),
                 "kink8_max": round(float(d8.max()), 1), "wave30_max": round(float(d30.max()), 1), "holes_pct": round(100 * float((~ok).mean()), 1),
                 "over2_m": int((d8 > 2).sum() * 2), "worst_lat": round(float(lat), 5), "worst_lon": round(float(lon), 5)})
print(f"{len(rows)} roads walked, {sum(r['km'] for r in rows):.0f} km")
print("by class: km, share of length with a slope change over 2 % in 8 m, over 5 %")
for cls, c in sorted(tot.items(), key=lambda kv: -kv[1][0]):
    print(f"  {cls:16s} {c[0]:6.1f} km   >2%: {100 * c[1] / c[3]:5.1f}%   >5%: {100 * c[2] / c[3]:5.1f}%")
big = [r for r in rows if r["class"] in ("trunk", "primary", "secondary", "tertiary")]
for title, lst in (("worst main roads", big), ("worst of all roads", rows)):
    print(title + " (kink in 8 m, wave in 30 m, metres over 2 %, holes, place):")
    for r in sorted(lst, key=lambda r: -r["kink8_max"])[:a.n]:
        print(f"  {r['kink8_max']:5.1f}%  {r['wave30_max']:5.1f}%  {r['over2_m']:4d} m  {r['holes_pct']:4.1f}%  {r['class']:12s} {r['km']:5.2f} km  "
              f"{r['worst_lat']},{r['worst_lon']}  way {r['way']} {r['name'][:28]}")
if a.out:
    json.dump(sorted(rows, key=lambda r: -r["kink8_max"]), open(a.out, "w"), indent=0, ensure_ascii=False)
