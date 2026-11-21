"""
Läser ut lamporna ur kartbilden: de orange trianglarna (pilarna) och de röda kryssen vid varje nod.
Regel: på varje nod är LEFT den triangel som ligger längst åt vänster i bilden (vid lika läge den övre)
och RIGHT den andra. LEFT lyser grönt och RIGHT gult. För varje väg ut från en nod väljs den triangel som
pekar bäst åt samma håll som vägen, och topology.json uppdateras med den lampan (lamp, exit_lamp).

Kör:  python3 tools/extract_lamps.py
Skapar sim/lamps.json (används av simulatorn), uppdaterar lamp i topology.json och skriver
docs/lampor_per_nod.md (kopplingstabell). Efter ändring måste korten laddas upp på nytt.
Kräver numpy, scipy och Pillow (bara för det här verktyget, inte för simulatorn).
"""
import itertools
import json
import math
import os

import numpy as np
from PIL import Image
from scipy import ndimage
from scipy.spatial import ConvexHull

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NODE_RADIUS = 95          # triangeln hör till närmaste nod inom så här många pixlar
WEAK = 0.5                # cos(60 grader): sämre än så markeras kopplingen som osäker

topo = json.load(open(os.path.join(ROOT, "topology.json"), encoding="utf-8"))
nodes = {n["id"]: n for n in topo["nodes"]}
img = np.array(Image.open(os.path.join(ROOT, "docs", "karta.png")).convert("RGB")).astype(int)
r, g, b = img[..., 0], img[..., 1], img[..., 2]


def unit(v):
    L = math.hypot(*v)
    return (v[0] / L, v[1] / L) if L else (0.0, 0.0)


# ---- trianglar -------------------------------------------------------------
orange = (abs(r - 237) < 14) & (abs(g - 161) < 14) & (abs(b - 57) < 22)
orange = ndimage.binary_opening(orange, iterations=1)
lab, cnt = ndimage.label(orange, structure=np.ones((3, 3)))
tris = []
for k in range(1, cnt + 1):
    ys, xs = np.nonzero(lab == k)
    if len(xs) < 250:
        continue
    pts = np.stack([xs, ys], 1).astype(float)
    hull = pts[ConvexHull(pts).vertices]
    best, area = None, -1
    for a, bb, c in itertools.combinations(range(len(hull)), 3):      # största triangeln i skrovet
        A, B, C = hull[a], hull[bb], hull[c]
        ar = abs((B[0] - A[0]) * (C[1] - A[1]) - (C[0] - A[0]) * (B[1] - A[1])) / 2
        if ar > area:
            best, area = (A, B, C), ar
    V = [np.array(v) for v in best]

    def angle(i):
        p, q, s = V[i], V[(i + 1) % 3], V[(i + 2) % 3]
        u1, u2 = q - p, s - p
        return math.acos(max(-1, min(1, u1 @ u2 / (np.linalg.norm(u1) * np.linalg.norm(u2)))))
    apex = min(range(3), key=angle)                                   # spetsen = minsta vinkeln
    base_mid = (V[(apex + 1) % 3] + V[(apex + 2) % 3]) / 2
    d = unit(tuple(V[apex] - base_mid))
    tris.append({"c": (xs.mean(), ys.mean()), "poly": [[round(float(v[0]), 1), round(float(v[1]), 1)] for v in V],
                 "dir": [round(d[0], 3), round(d[1], 3)], "area": int(len(xs))})

# ---- röda kryss ------------------------------------------------------------
red = (r > 170) & (g < 100) & (b < 85)

# ---- koppla till noder -----------------------------------------------------
per = {i: [] for i in nodes}
for t in tris:
    i = min(nodes, key=lambda i: math.hypot(nodes[i]["x"] - t["c"][0], nodes[i]["y"] - t["c"][1]))
    if math.hypot(nodes[i]["x"] - t["c"][0], nodes[i]["y"] - t["c"][1]) <= NODE_RADIUS:
        per[i].append(t)

out, report, problems = {}, [], []
for i, n in nodes.items():
    ts = per[i]
    if len(ts) != 2:
        problems.append(f"Nod {i}: hittade {len(ts)} trianglar (väntade 2)")
        continue
    ts.sort(key=lambda t: (round(t["c"][0] / 10), t["c"][1]))           # vänster->höger, vid lika läge uppifrån
    # mål: varje väg ut från noden (granne eller utgång) och åt vilket håll den ligger i bilden
    targets = []
    for k, e in enumerate(topo["edges"]):
        if e["from"] == i:
            targets.append((("edge", k), unit((nodes[e["to"]]["x"] - n["x"], nodes[e["to"]]["y"] - n["y"]))))
    if n.get("exit_m", 0) > 0:
        targets.append((("exit", i), (0.0, -1.0) if n.get("exit_dir") == "up" else (0.0, 1.0)))

    def cos(t, v):
        return t["dir"][0] * v[0] + t["dir"][1] * v[1]

    # välj triangel (0 = LEFT, 1 = RIGHT) per mål; olika mål ska få olika trianglar om det går
    best_choice, best_total = None, -9
    for choice in itertools.product((0, 1), repeat=len(targets)):
        total = sum(cos(ts[c], v) for c, (_, v) in zip(choice, targets))
        if len(targets) <= 2 and len(set(choice)) < len(choice):
            total -= 100                                                 # två mål på samma triangel: undvik
        if total > best_total + 1e-9:
            best_choice, best_total = choice, total
    worst = min([cos(ts[c], v) for c, (_, v) in zip(best_choice, targets)], default=1.0)
    if len(targets) > 2:
        problems.append(f"Nod {i}: {len(targets)} vägar ut men bara två pilar")
    left_idx, right_idx = 0, 1
    lamp_for = {}
    for c, (key, v) in zip(best_choice, targets):
        lamp_for[key] = "LEFT" if c == 0 else "RIGHT"
        if key[0] == "edge":
            topo["edges"][key[1]]["lamp"] = lamp_for[key]
        else:
            n["exit_lamp"] = lamp_for[key]
    sl = max([cos(ts[0], v) for key, v in targets if lamp_for[key] == "LEFT"], default=None)
    sr = max([cos(ts[1], v) for key, v in targets if lamp_for[key] == "RIGHT"], default=None)

    # röda krysset: röda pixlar nära noden
    ys, xs = np.nonzero(red[int(n["y"]) - 60:int(n["y"]) + 60, int(n["x"]) - 60:int(n["x"]) + 60])
    cross = None
    if len(xs) >= 12:
        cx, cy = xs.mean() + n["x"] - 60, ys.mean() + n["y"] - 60
        cross = {"x": round(float(cx), 1), "y": round(float(cy), 1),
                 "size": round(float(max(xs.max() - xs.min(), ys.max() - ys.min())) / 2 + 2, 1)}
    else:
        problems.append(f"Nod {i}: hittade inget rött kryss")

    out[str(i)] = {"triangles": [{"poly": t["poly"], "dir": t["dir"]} for t in ts],
                   "lamp_map": {"LEFT": 0, "RIGHT": 1},
                   "quality": round(float(worst), 2), "cross": cross}

    def deg(x):
        return "-" if x is None else f"{math.degrees(math.acos(max(-1, min(1, x)))):.0f}°"

    def name(t):
        dx, dy = t["dir"]
        if abs(dx) > abs(dy) * 1.8:
            return "höger" if dx > 0 else "vänster"
        if abs(dy) > abs(dx) * 1.8:
            return "ner" if dy > 0 else "upp"
        return ("höger" if dx > 0 else "vänster") + ("-ner" if dy > 0 else "-upp")
    report.append((i, n["name"], name(ts[left_idx]), deg(sl), name(ts[right_idx]), deg(sr), worst < WEAK))

topo["_info"] = ("Källa för kartan. Avstånd (m) är UPPSKATTADE ur kartbilden, ersätt med riktiga mått. "
                 "lamp = vilken pil på noden 'from' som pekar mot 'to' (LEFT = vänstra pilen = grön, RIGHT = högra pilen = gul); "
                 "lamporna sätts av tools/extract_lamps.py ur kartbilden. "
                 "exit_m > 0 markerar utgång (exit_dir bara för bilder). zone (valfritt): larm i en nod stänger alla noder i samma zon.")
with open(os.path.join(ROOT, "topology.json"), "w", encoding="utf-8") as f:
    json.dump(topo, f, ensure_ascii=False, indent=1)

with open(os.path.join(ROOT, "sim", "lamps.json"), "w", encoding="utf-8") as f:
    json.dump({"image": [int(img.shape[1]), int(img.shape[0])], "nodes": out}, f, separators=(",", ":"))

md = ["# Lampor per nod (kopplingstabell)", "",
      "Skapad av `tools/extract_lamps.py` ur kartbilden. Varje nod har två pilar (trianglar) i bilden.",
      "På varje nod är den **vänstra triangeln** den gröna pilen (LEFT, GPIO23) och den **högra** den gula pilen",
      "(RIGHT, GPIO22). Tabellen visar åt vilket håll respektive triangel pekar i bilden, och hur många grader fel",
      "den pekar mot det den ska visa (0° är rakt åt rätt håll). **Osäker** betyder mer än 60° fel: ingen av",
      "trianglarna pekar åt grannen (t.ex. vid trapphusen). Rita om pilen i bilden eller välj lampa för hand i `topology.json`.", "",
      "| Nod | Namn | Grön pil (LEFT) pekar | fel | Gul pil (RIGHT) pekar | fel | |", "|---|---|---|---|---|---|---|"]
for i, nm, ln, ls, rn, rs, weak in report:
    md.append(f"| {i} | {nm} | {ln} | {ls} | {rn} | {rs} | {'**osäker**' if weak else ''} |")
with open(os.path.join(ROOT, "docs", "lampor_per_nod.md"), "w", encoding="utf-8") as f:
    f.write("\n".join(md) + "\n")

print(f"{len(tris)} trianglar hittade, {len(out)} av {len(nodes)} noder har två trianglar")
for i, nm, ln, ls, rn, rs, weak in report:
    print(f"nod {i:2d}  grön(LEFT) pekar {ln:11s} {ls:>5s}   gul(RIGHT) pekar {rn:11s} {rs:>5s}  {'OSÄKER' if weak else ''}")
for p in problems:
    print("PROBLEM:", p)
