"""
Engångsverktyg: skapar topology.json från kartans pixelkoordinater.
Kör:  python3 tools/make_topology.py
Efteråt är topology.json källan. Redigera den för hand (riktiga avstånd, lampor, utgångar).
Avstånden här är UPPSKATTADE ur kartbilden (M_PER_PX) och trappor schablonmässigt (STAIR_M).
"""
import json, math

M_PER_PX = 0.05     # uppskattad skala: 1 pixel i kartbilden = 0,05 m  (ersätt med riktiga mått)
STAIR_M = 12.0      # uppskattad gångväg per trappa mellan två plan (m)
EXIT_M = 12.0       # uppskattad sträcka ut från utgångsnoden (m)

# id: (namn, plan, x, y)   plan 1 = entréplanet (nod 1 och 4), plan 3 = översta planet.
# Korridoren/rummen i nedre delen av bilden (nod 7-16) ligger på samma plan som nod 3 och 6.
N = {
 1: ("Trapphus vä plan 1 (entré)", 1, 380, 248),
 2: ("Trapphus vä plan 2", 2, 375, 495),
 3: ("Trapphus vä plan 3", 3, 368, 795),
 4: ("Trapphus hö plan 1 (entré)", 1, 1082, 232),
 5: ("Trapphus hö plan 2", 2, 1082, 505),
 6: ("Trapphus hö plan 3", 3, 1065, 790),
 7: ("Korridor/rum plan 3 – korridor vä (B1)", 3, 385, 950),
 8: ("Korridor/rum plan 3 – dörr 1 (B2)", 3, 430, 1020),
 9: ("Korridor/rum plan 3 – dörr 2 (B3)", 3, 598, 1015),
 10: ("Korridor/rum plan 3 – korridor mitt (B4)", 3, 678, 955),
 11: ("Korridor/rum plan 3 – dörr 3 (B5)", 3, 737, 1020),
 12: ("Korridor/rum plan 3 – dörr 4 (B6)", 3, 990, 1035),
 13: ("Korridor/rum plan 3 – korridor hö (B7)", 3, 1125, 1060),
 14: ("Korridor/rum plan 3 – rum söder 1 (B8)", 3, 468, 1240),
 15: ("Korridor/rum plan 3 – rum söder 2 (B9)", 3, 705, 1240),
 16: ("Korridor/rum plan 3 – rum söder 3 (B10)", 3, 915, 1240),
}
EXITS = {1, 4}    # entréplanets trapphusnoder = utgångar (trapporna går ner mot dem)
ZONES = {}   # valfritt: {nod-id: "zonnamn"}. Larm i en nod stänger då alla noder i samma zon. Används inte just nu.

def px(a, b):
    return math.hypot(N[a][2]-N[b][2], N[a][3]-N[b][3])

def geo_lamp(a, b):
    """LEFT/RIGHT efter grannens läge på kartan (dominerande axel)."""
    dx, dy = N[b][2]-N[a][2], N[b][3]-N[a][3]
    if abs(dx) >= abs(dy):
        return "LEFT" if dx < 0 else "RIGHT"
    return "LEFT" if dy < 0 else "RIGHT"

edges = []
def both(a, b, lamp_a=None, lamp_b=None, m=None):
    m = m if m is not None else round(px(a, b)*M_PER_PX, 1)
    edges.append({"from": a, "to": b, "m": m, "lamp": lamp_a or geo_lamp(a, b)})
    edges.append({"from": b, "to": a, "m": m, "lamp": lamp_b or geo_lamp(b, a)})
def one(a, b, lamp=None, m=None):
    m = m if m is not None else round(px(a, b)*M_PER_PX, 1)
    edges.append({"from": a, "to": b, "m": m, "lamp": lamp or geo_lamp(a, b)})

# Trappor: bara nedåt mot entréplanet (3->2->1 och 6->5->4). Pil längs trappan = RIGHT (gul).
for a, b in [(3, 2), (2, 1), (6, 5), (5, 4)]:
    one(a, b, "RIGHT", STAIR_M)
# Ingen väg över mitten: den vita ytan mellan trapphusen är ett tomrum. Trapphusen är bara kopplade
# via korridoren på plan 3 (nod 3 <-> 7 och nod 13 <-> 6). Pil mot korridoren = LEFT (grön).
both(3, 7, "LEFT", "LEFT")
both(6, 13, "LEFT", "RIGHT")      # nod 13 har två vägar: västerut längs korridoren (LEFT) och in till trapphuset (RIGHT)
# Korridoren i x-ordning
for a, b in [(7, 8), (8, 9), (9, 10), (10, 11), (11, 12), (12, 13)]:
    both(a, b)
# Rum bara in mot korridoren (återvändsgränder, ingen pil in i rummen)
for a, b in [(14, 8), (15, 11), (16, 12)]:
    one(a, b)

doc = {
 "_info": "Källa för kartan. Avstånd (m) är UPPSKATTADE ur kartbilden, ersätt med riktiga mått. "
          "lamp = vilken pil på noden 'from' som pekar mot 'to' (LEFT=grön, RIGHT=gul). "
          "exit_m > 0 markerar utgång (exit_dir bara för bilder). zone (valfritt): larm i en nod stänger alla noder i samma zon.",
 "nodes": [{"id": i, "name": N[i][0], "floor": N[i][1], "x": N[i][2], "y": N[i][3],
            **({"zone": ZONES[i]} if i in ZONES else {}),
            **({"exit_m": EXIT_M, "exit_lamp": "RIGHT", "exit_dir": "up"} if i in EXITS else {})} for i in sorted(N)],
 "edges": edges,
}
with open("topology.json", "w", encoding="utf-8") as f:
    json.dump(doc, f, ensure_ascii=False, indent=1)
print(len(N), "noder,", len(edges), "riktade kanter")
