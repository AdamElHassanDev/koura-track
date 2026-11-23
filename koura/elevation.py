"""How faithful the built road is to the real heights.

  python koura/elevation.py out/S2/koura_preview.glb [--routes loop,...]

Walks each route every 5 m on the built road and on the raw Copernicus 30 m model at the same points, and prints:
  - the height range and total climb of both (a flattened road climbs less);
  - the difference between them (RMS and largest);
  - the steepest 100 m of each.
The 30 m model includes roofs and tree tops, so a metre or two of difference in villages is expected. What must
not happen is the road climbing clearly less than the ground it follows."""
import sys, os, json, argparse
import numpy as np
from scipy.spatial import cKDTree
from scipy.ndimage import uniform_filter1d
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
os.environ.setdefault("OPENLAPS_CACHE", os.path.join(ROOT, "cache"))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(ROOT, "openlaps"))
import ride
from openlaps.geo import LocalProjection, BBox
from openlaps.sources import rasters

p = argparse.ArgumentParser(); p.add_argument("glb"); p.add_argument("--routes", default="")
a = p.parse_args()
zone = json.load(open(os.path.join(ROOT, "handoff/inputs/zone.json"))); O = zone["origin"]
proj = LocalProjection.marco(O["lat"], O["lon"], tuple(zone["stages"]["S2"]["expected"]["rect_local_m"]))
dem = rasters.copernicus_dem(proj.bbox().padded(300), log=lambda *k: None)
T = ride.road_tris(a.glb); tree = cKDTree(T.mean(axis=1)[:, [0, 2]])

def climb(h):          # total ascent, ignoring ripples under half a metre
    up, ref = 0.0, h[0]
    for v in h[1:]:
        if v > ref + 0.5: up += v - ref; ref = v
        elif v < ref - 0.5: ref = v
    return up

print(f"{'route':18s} {'km':>5s} | {'road: low..high':>17s} {'climb':>6s} {'steepest':>8s} | {'30 m model: low..high':>21s} {'climb':>6s} {'steepest':>8s} | {'diff RMS':>8s} {'max':>5s}")
for name in ([r for r in a.routes.split(",") if r] or list(zone["routes"])):
    pl = np.array(zone["routes"][name]["polyline"], float); x, y = proj.to_local(pl[:, 1], pl[:, 0]); P = np.c_[x, y]
    s = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))]); keep = np.concatenate([[True], np.diff(s) > 1e-6]); P, s = P[keep], s[keep]
    S = np.arange(0, s[-1], 5.0); C = np.c_[np.interp(S, s, P[:, 0]), np.interp(S, s, P[:, 1])]
    h = ride.heights(T, tree, 9.0, C[:, 0], -C[:, 1]); ok = np.isfinite(h)
    if ok.sum() < 20:
        continue
    S, C, h = S[ok], C[ok], h[ok]
    d = np.asarray(dem.sample(proj, C[:, 0], C[:, 1], order=1), float)
    d = uniform_filter1d(d, 7, mode="nearest")          # the model is 30 m: 35 m running mean along the road
    n = 20                                              # 100 m
    g_r = np.abs(h[n:] - h[:-n]).max() if len(h) > n else 0; g_d = np.abs(d[n:] - d[:-n]).max() if len(d) > n else 0
    df = h - d; df -= np.median(df)
    print(f"{name:18s} {S[-1] / 1000:5.1f} | {h.min():7.0f}..{h.max():<7.0f} {climb(h):6.0f} {g_r:7.1f}% | {d.min():10.0f}..{d.max():<8.0f} {climb(d):6.0f} {g_d:7.1f}% | {np.sqrt((df ** 2).mean()):8.2f} {np.abs(df).max():5.1f}")
