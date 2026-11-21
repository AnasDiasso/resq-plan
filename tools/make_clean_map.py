#!/usr/bin/env python3
"""
Skapar docs/karta_ren.png: kartan utan de orange trianglarna och de röda kryssen vid noderna.
Simulatorn ritar sedan trianglarna och kryssen själv ovanpå (position och form ur sim/lamps.json).
Kör om efter att docs/karta.png har bytts: python3 tools/make_clean_map.py
"""
import json
import os

import cv2
import numpy as np
from scipy import ndimage

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
bgr = cv2.imread(os.path.join(ROOT, "docs", "karta.png"), cv2.IMREAD_COLOR)
rgb = bgr[..., ::-1].astype(int)
r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]

orange = (abs(r - 237) < 30) & (abs(g - 161) < 40) & (abs(b - 57) < 50)       # lite bredare än vid utläsningen: kantpixlar
red = (r > 150) & (g < 130) & (b < 120) & (r - g > 80)
blue = (b > 190) & (r < 110) & (g < 160)                                       # nodprickens blå färg
topo = json.load(open(os.path.join(ROOT, "topology.json"), encoding="utf-8"))
near = np.zeros(r.shape, bool)                                              # rött räknas bara nära en nod
for n in topo["nodes"]:
    x, y = int(n["x"]), int(n["y"])
    near[max(0, y - 80):y + 80, max(0, x - 80):x + 80] = True
mask = (orange | ((red | blue) & near)) 
# bara de delar som sitter vid en nod (annars skulle t.ex. röda symboler utanför noderna försvinna)
lab, cnt = ndimage.label(ndimage.binary_dilation(mask, iterations=2))
keep = np.zeros(r.shape, bool)
for i in range(1, cnt + 1):
    ys, xs = np.nonzero(lab == i)
    cx, cy = xs.mean(), ys.mean()
    if any(abs(cx - n["x"]) < 90 and abs(cy - n["y"]) < 90 for n in topo["nodes"]):
        keep |= (lab == i)
mask8 = (ndimage.binary_dilation(keep, iterations=3) * 255).astype(np.uint8)
out = cv2.inpaint(bgr, mask8, 6, cv2.INPAINT_NS)
cv2.imwrite(os.path.join(ROOT, "docs", "karta_ren.png"), out)
print(f"docs/karta_ren.png skapad ({int(mask8.astype(bool).sum())} pixlar ifyllda)")
