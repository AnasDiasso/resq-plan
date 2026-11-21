"""
PlatformIO pre-script: läser topology.json och skapar include/topology.h.
Redigera topology.json, inte topology.h. Kan köras för hand:  python3 scripts/gen_topology.py
"""
import json
import os
import sys

MAX_NODES = 32
LAMPS = {"LEFT": 0, "RIGHT": 1}


def generate(project_dir):
    path = os.path.join(project_dir, "topology.json")
    if not os.path.isfile(path):
        return False, "topology.json saknas."
    try:
        with open(path, encoding="utf-8") as f:
            t = json.load(f)
    except ValueError as e:
        return False, f"topology.json är inte giltig JSON: {e}"

    nodes = t.get("nodes", [])
    edges = t.get("edges", [])
    if not 1 <= len(nodes) <= MAX_NODES:
        return False, f"topology.json: antal noder måste vara 1-{MAX_NODES} (hittade {len(nodes)})."
    ids = [n.get("id") for n in nodes]
    if any(not isinstance(i, int) or not 1 <= i <= 255 for i in ids) or len(set(ids)) != len(ids):
        return False, "topology.json: node-id måste vara unika heltal 1-255."
    index = {i: k for k, i in enumerate(ids)}

    exits = [n for n in nodes if n.get("exit_m", 0) > 0]
    if not exits:
        return False, "topology.json: minst en nod måste vara utgång (exit_m > 0)."
    for n in exits:
        if n.get("exit_lamp") not in LAMPS:
            return False, f"Nod {n['id']}: exit_lamp måste vara LEFT eller RIGHT."

    seen = set()
    for e in edges:
        a, b = e.get("from"), e.get("to")
        if a not in index or b not in index or a == b:
            return False, f"Kant {a}->{b}: okänd nod eller kant till sig själv."
        if (a, b) in seen:
            return False, f"Kant {a}->{b} finns två gånger."
        seen.add((a, b))
        if e.get("lamp") not in LAMPS:
            return False, f"Kant {a}->{b}: lamp måste vara LEFT eller RIGHT."
        if not isinstance(e.get("m"), (int, float)) or e["m"] <= 0:
            return False, f"Kant {a}->{b}: m (meter) måste vara > 0."

    # Varning (inget fel): samma pil för två olika grannar går inte att skilja åt på noden.
    warn = []
    for nid in ids:
        lamps = {}
        for e in edges:
            if e["from"] == nid:
                lamps.setdefault(e["lamp"], []).append(e["to"])
        for lamp, tos in lamps.items():
            if len(tos) > 1:
                warn.append(f"Nod {nid}: pilen {lamp} används för flera grannar ({', '.join(map(str, tos))})")
    for w in warn:
        print(f"[gen_topology] VARNING: {w}")

    def dm(m):                      # decimeter, heltal
        return int(round(m * 10))

    n = len(nodes)
    # Zonmask: nod k stänger alla noder i samma zon (utan zon: bara sig själv).
    zmask = []
    for x in nodes:
        z = x.get("zone")
        zmask.append(sum(1 << index[y["id"]] for y in nodes if z and y.get("zone") == z) or (1 << index[x["id"]]))
    zmask = [m | (1 << k) for k, m in enumerate(zmask)]
    lines = []
    lines.append("// GENERERAD AV scripts/gen_topology.py FRÅN topology.json. REDIGERA INTE HÄR.")
    lines.append("#pragma once")
    lines.append("#include <stdint.h>")
    lines.append("")
    lines.append(f"#define TOPO_N {n}")
    lines.append(f"#define TOPO_E {len(edges)}")
    lines.append("// Lampa: 0 = LEFT (grön), 1 = RIGHT (gul). Avstånd i decimeter.")
    lines.append("static const uint8_t  TOPO_ID[TOPO_N]        = { " + ", ".join(str(i) for i in ids) + " };")
    lines.append("static const uint16_t TOPO_EXIT_DM[TOPO_N]   = { " +
                 ", ".join(str(dm(x.get("exit_m", 0))) for x in nodes) + " };")
    lines.append("static const uint8_t  TOPO_EXIT_LAMP[TOPO_N] = { " +
                 ", ".join(str(LAMPS.get(x.get("exit_lamp", "RIGHT"))) for x in nodes) + " };")
    lines.append("// Zon: larm i nod k stänger alla noder i TOPO_ZONE_MASK[k] (bit = nodindex).")
    lines.append("static const uint32_t TOPO_ZONE_MASK[TOPO_N] = { " + ", ".join(f"0x{m:08X}u" for m in zmask) + " };")
    lines.append("static const uint8_t  TOPO_E_FROM[TOPO_E]    = { " + ", ".join(str(index[e["from"]]) for e in edges) + " };")
    lines.append("static const uint8_t  TOPO_E_TO[TOPO_E]      = { " + ", ".join(str(index[e["to"]]) for e in edges) + " };")
    lines.append("static const uint16_t TOPO_E_DM[TOPO_E]      = { " + ", ".join(str(dm(e["m"])) for e in edges) + " };")
    lines.append("static const uint8_t  TOPO_E_LAMP[TOPO_E]    = { " + ", ".join(str(LAMPS[e["lamp"]]) for e in edges) + " };")
    body = "\n".join(lines) + "\n"

    out_dir = os.path.join(project_dir, "include")
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, "topology.h")
    old = None
    if os.path.isfile(out):
        with open(out, encoding="utf-8") as f:
            old = f.read()
    if old != body:
        with open(out, "w", encoding="utf-8") as f:
            f.write(body)
    return True, f"include/topology.h skapad ({n} noder, {len(edges)} riktade kanter, {len(exits)} utgångar)"


def _run(project_dir, env=None):
    ok, msg = generate(project_dir)
    print(f"[gen_topology] {msg}")
    if not ok:
        if env is not None:
            env.Exit(1)
        sys.exit(1)


try:
    Import("env")                  # finns bara när PlatformIO kör skriptet
    _PIO_ENV = env                 # noqa: F821
except NameError:
    _PIO_ENV = None

if _PIO_ENV is not None:
    _run(_PIO_ENV["PROJECT_DIR"], _PIO_ENV)
elif __name__ == "__main__":
    _run(sys.argv[1] if len(sys.argv) > 1 else os.getcwd())
