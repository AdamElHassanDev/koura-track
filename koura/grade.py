"""Grade waviness along a stretch of a route: how much the slope wobbles. A race-track-smooth road changes slope
slowly. Prints the largest slope change within 8 m and within 30 m, and the RMS of slope change per 10 m.
  python koura/grade.py <glb> <route> <km from> <km to> [--plot]"""
import sys, json, os
import numpy as np
from scipy.spatial import cKDTree
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "openlaps"))
import ride
from openlaps.geo import LocalProjection
glb, route, k0, k1 = sys.argv[1], sys.argv[2], float(sys.argv[3]), float(sys.argv[4])
zone = json.load(open(os.path.join(ride.ROOT, "handoff/inputs/zone.json"))); O = zone["origin"]
proj = LocalProjection.marco(O["lat"], O["lon"], (-100, -100, 100, 100))
T = ride.road_tris(glb); tree = cKDTree(T.mean(axis=1)[:, [0, 2]])
pl = np.array(zone["routes"][route]["polyline"], float); x, y = proj.to_local(pl[:, 1], pl[:, 0]); P = np.c_[x, y]
s = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))]); keep = np.concatenate([[True], np.diff(s) > 1e-6]); P, s = P[keep], s[keep]
S = np.arange(k0 * 1000, k1 * 1000, 2.0); C = np.c_[np.interp(S, s, P[:, 0]), np.interp(S, s, P[:, 1])]
tg = np.gradient(C, axis=0); tg /= np.linalg.norm(tg, axis=1, keepdims=True); nr = np.c_[-tg[:, 1], tg[:, 0]]
for lane, o in (("L", 1.5), ("R", -1.5)):
    h = ride.heights(T, tree, 9.0, (C + nr * o)[:, 0], -(C + nr * o)[:, 1])
    ok = np.isfinite(h); h = np.interp(S, S[ok], h[ok])
    sl = np.gradient(h, S) * 100
    d8 = np.abs(sl[4:] - sl[:-4]); d30 = np.abs(sl[15:] - sl[:-15]); d10 = sl[5:] - sl[:-5]
    print(f"{route} {k0}-{k1} km lane {lane}: holes {100 * (~ok).mean():.1f}%  slope change max in 8 m {d8.max():.1f}%  "
          f"p95 {np.percentile(d8, 95):.2f}%  max in 30 m {d30.max():.1f}%  RMS per 10 m {np.sqrt((d10 ** 2).mean()):.2f}%")
    if "--plot" in sys.argv and lane == "L":
        for i in range(0, len(S), 5):
            print(f"  {S[i]:7.0f} {h[i]:8.2f} {sl[i]:5.1f}% " + "#" * int(max(0, min(70, (sl[i] + 6) * 4))))
