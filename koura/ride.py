"""Ride quality along the routes: what a car feels, measured on the built road surface.

  python koura/ride.py out/S2/koura_preview.glb [--routes loop,shortcut] [--v 100] [--n 25] [--csv file]

For every route in handoff/inputs/zone.json the line is walked every metre, in both lanes (1.5 m either side of
the line). The height of the drivable road mesh is read under each point (inside the triangle, not the nearest
vertex). Reported:
  - holes: points with no road under them (grass or terrain shows through the road);
  - steps: a kink of more than 4 cm over one metre (the steady grade is removed);
  - vertical g at speed v, from the curvature of the profile over a 6 m base. Real fast roads stay under 0.3 g.
"""
import argparse, json, os, struct, sys
import numpy as np
from scipy.spatial import cKDTree

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "openlaps"))
from openlaps.geo import LocalProjection  # noqa: E402


def road_tris(path, clave="calzada"):
    data = open(path, "rb").read()
    jl = struct.unpack_from("<I", data, 12)[0]
    js = json.loads(data[20:20 + jl])
    binb = memoryview(data)[20 + jl + 8:]

    def acc(i):
        a = js["accessors"][i]; v = js["bufferViews"][a["bufferView"]]
        dt = {5126: np.float32, 5123: np.uint16, 5125: np.uint32}[a["componentType"]]
        n = {"SCALAR": 1, "VEC2": 2, "VEC3": 3}[a["type"]]
        arr = np.frombuffer(binb, dt, a["count"] * n, v.get("byteOffset", 0) + a.get("byteOffset", 0))
        return arr.reshape(-1, n) if n > 1 else arr
    out = []
    for node in js["nodes"]:
        nm = node.get("name", "")
        if "mesh" not in node or clave not in nm or not nm.startswith("1"):
            continue
        pr = js["meshes"][node["mesh"]]["primitives"][0]
        pos = acc(pr["attributes"]["POSITION"]).astype(np.float64)
        idx = acc(pr["indices"]).astype(np.int64).reshape(-1, 3)
        out.append(pos[idx])
    return np.concatenate(out)          # (n, 3, 3) as x, y(up), z(= -north)


def heights(T, tree, rmax, X, Zn):
    """Road height under each (x, -north) point; nan where there is no road."""
    h = np.full(len(X), np.nan)
    cand = tree.query_ball_point(np.c_[X, Zn], rmax)
    for i, c in enumerate(cand):
        if not c:
            continue
        t = T[c]
        a, b, cc = t[:, 0], t[:, 1], t[:, 2]
        v0x, v0z = b[:, 0] - a[:, 0], b[:, 2] - a[:, 2]
        v1x, v1z = cc[:, 0] - a[:, 0], cc[:, 2] - a[:, 2]
        px, pz = X[i] - a[:, 0], Zn[i] - a[:, 2]
        den = v0x * v1z - v1x * v0z
        ok = np.abs(den) > 1e-9
        den = np.where(ok, den, 1.0)
        u = (px * v1z - v1x * pz) / den
        w = (v0x * pz - px * v0z) / den
        m = ok & (u >= -1e-6) & (w >= -1e-6) & (u + w <= 1 + 1e-6)
        if m.any():
            y = a[m, 1] + u[m] * (b[m, 1] - a[m, 1]) + w[m] * (cc[m, 1] - a[m, 1])
            h[i] = y.max()
    return h


def main():
    p = argparse.ArgumentParser()
    p.add_argument("glb"); p.add_argument("--routes", default="")
    p.add_argument("--v", type=float, default=100.0); p.add_argument("--n", type=int, default=25)
    p.add_argument("--base", type=float, default=3.0); p.add_argument("--csv", default="")
    p.add_argument("--terrain", action="store_true", help="also count where the ground pokes up through the road")
    a = p.parse_args()
    zone = json.load(open(os.path.join(ROOT, "handoff/inputs/zone.json")))
    O = zone["origin"]
    proj = LocalProjection.marco(O["lat"], O["lon"], (-100, -100, 100, 100))
    T = road_tris(a.glb)
    cen = T.mean(axis=1)[:, [0, 2]]
    rmax = float(np.percentile(np.linalg.norm(T[:, :, [0, 2]] - cen[:, None, :], axis=2).max(axis=1), 99.9)) + 0.1
    tree = cKDTree(cen)
    print(f"{len(T):,} road triangles, search radius {rmax:.1f} m, speed {a.v:.0f} km/h")
    v = a.v / 3.6
    if a.terrain:
        TT = road_tris(a.glb, "_terreno_")
        tcen = TT.mean(axis=1)[:, [0, 2]]
        trm = float(np.percentile(np.linalg.norm(TT[:, :, [0, 2]] - tcen[:, None, :], axis=2).max(axis=1), 99.9)) + 0.1
        ttree = cKDTree(tcen)
        print(f"{len(TT):,} ground triangles")
    k = int(a.base)
    rows = []
    want = [r for r in a.routes.split(",") if r] or list(zone["routes"])
    for name in want:
        pl = np.array(zone["routes"][name]["polyline"], float)
        x, y = proj.to_local(pl[:, 1], pl[:, 0])
        P = np.c_[x, y]
        s = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))])
        keep = np.concatenate([[True], np.diff(s) > 1e-6]); P, s = P[keep], s[keep]
        S = np.arange(0, s[-1], 1.0)
        C = np.c_[np.interp(S, s, P[:, 0]), np.interp(S, s, P[:, 1])]
        tg = np.gradient(C, axis=0); tg /= np.maximum(np.linalg.norm(tg, axis=1, keepdims=True), 1e-9)
        nr = np.c_[-tg[:, 1], tg[:, 0]]
        # where the route line turns sharply (a turn at a junction) nobody drives the line at speed: a point is
        # left out when the heading changes more than 20 degrees within 8 m either side
        hd = np.unwrap(np.arctan2(tg[:, 1], tg[:, 0]))
        w = 8
        turn = np.zeros(len(S), bool)
        turn[w:-w] = np.abs(hd[2 * w:] - hd[:-2 * w]) > np.radians(20)
        turn = np.convolve(turn.astype(int), np.ones(2 * w + 1, int), "same") > 0
        tot = {"m": 0, "hole": 0, "step": 0, "g3": 0, "g5": 0, "g10": 0}
        for lane, off in (("L", 1.5), ("R", -1.5)):
            Q = C + nr * off
            h = heights(T, tree, rmax, Q[:, 0], -Q[:, 1])
            hole = np.isnan(h)
            if a.terrain:
                ht = heights(TT, ttree, trm, Q[:, 0], -Q[:, 1])
                pk = (~hole) & np.isfinite(ht) & (ht > h + 0.005)
                tot["poke"] = tot.get("poke", 0) + int(pk.sum())
                tot["pokemax"] = max(tot.get("pokemax", 0.0), float((ht - h)[pk].max()) if pk.any() else 0.0)
                tot["gap"] = tot.get("gap", 0) + int((hole & np.isfinite(ht)).sum())
            hf = np.interp(S, S[~hole], h[~hole]) if (~hole).sum() > 2 else np.zeros_like(S)
            dz = np.zeros_like(hf); dz[1:-1] = np.abs(hf[2:] - 2 * hf[1:-1] + hf[:-2])   # kink over 1 m, grade removed
            dz[hole] = 0
            g = np.zeros_like(hf)
            g[k:-k] = (hf[2 * k:] - 2 * hf[k:-k] + hf[:-2 * k]) / (k * k) * v * v / 9.81
            kl = 12                      # long waves: dips and crests 20-40 m long, felt at speed
            gl = np.zeros_like(hf)
            gl[kl:-kl] = (hf[2 * kl:] - 2 * hf[kl:-kl] + hf[:-2 * kl]) / (kl * kl) * v * v / 9.81
            gl[turn] = 0
            tot["l15"] = tot.get("l15", 0) + int((np.abs(gl) > 0.15).sum())
            tot["l30"] = tot.get("l30", 0) + int((np.abs(gl) > 0.30).sum())
            g[turn] = 0; dz[turn] = 0
            tot["m"] += len(S); tot["hole"] += int(hole.sum()); tot["step"] += int((dz > 0.04).sum())
            for key, lim in (("g3", 0.3), ("g5", 0.5), ("g10", 1.0)):
                tot[key] += int((np.abs(g) > lim).sum())
            for i in range(len(S)):
                if hole[i] or dz[i] > 0.04 or abs(g[i]) > 0.5:
                    rows.append((name, lane, S[i], Q[i, 0], Q[i, 1], hf[i], g[i], dz[i], bool(hole[i])))
        m = tot["m"]
        print(f"{name:18s} {s[-1] / 1000:5.1f} km  no road {100 * tot['hole'] / m:4.1f}%  steps>4cm {tot['step']:5d}  "
              f">0.3g {100 * tot['g3'] / m:4.1f}%  >0.5g {100 * tot['g5'] / m:4.1f}%  >1g {100 * tot['g10'] / m:4.1f}%"
              + f"  long waves >0.15g {100 * tot['l15'] / m:4.1f}% >0.3g {100 * tot['l30'] / m:4.1f}%"
              + (f"  ground above road {100 * tot.get('poke', 0) / m:4.1f}% (max {tot.get('pokemax', 0) * 100:.0f} cm)" if a.terrain else ""))
    # worst places, grouped within 40 m
    rows.sort(key=lambda r: -(abs(r[6]) + 20 * r[7] + (0.6 if r[8] else 0)))
    seen, shown = [], 0
    print("worst places (route, lane, km along, lat, lon, g, step cm, hole):")
    for r in rows:
        if any((r[3] - q[0]) ** 2 + (r[4] - q[1]) ** 2 < 40 ** 2 for q in seen):
            continue
        seen.append((r[3], r[4]))
        lon, lat = proj.to_lonlat(r[3], r[4])
        print(f"  {r[0]:16s} {r[1]} {r[2] / 1000:6.2f} km  {float(lat):.5f},{float(lon):.5f}  x={r[3]:7.0f} y={r[4]:7.0f}  "
              f"{r[6]:+5.1f} g  {r[7] * 100:4.0f} cm  {'HOLE' if r[8] else ''}")
        shown += 1
        if shown >= a.n:
            break
    if a.csv:
        np.savetxt(a.csv, np.array([(r[2], r[3], r[4], r[5], r[6], r[7], r[8]) for r in rows], float), fmt="%.3f", delimiter=",")


if __name__ == "__main__":
    main()
