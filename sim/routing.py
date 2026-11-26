"""
Vägval i Python: samma regler som noden (src/route.cpp), inklusive samma val vid lika långa vägar.
Testas mot C++-koden i sim/test_sim.py.
"""
import json

INF = float("inf")


class Topology:
    def __init__(self, path):
        with open(path, encoding="utf-8") as f:
            t = json.load(f)
        self.nodes = {n["id"]: n for n in t["nodes"]}
        self.order = [n["id"] for n in t["nodes"]]
        self.exit_dm = {i: int(round(n.get("exit_m", 0) * 10)) for i, n in self.nodes.items()}
        self.exit_lamp = {i: n.get("exit_lamp", "RIGHT") for i, n in self.nodes.items()}
        self.edges = [(e["from"], e["to"], int(round(e["m"] * 10)), e["lamp"]) for e in t["edges"]]
        self.zone = {i: n.get("zone") for i, n in self.nodes.items()}

    def closed(self, alarms):
        """Larmande noder, plus alla noder i samma zon (om zoner används)."""
        c = set(alarms)
        for a in alarms:
            z = self.zone.get(a)
            if z:
                c |= {i for i in self.order if self.zone[i] == z}
        return c


def compute(topo, alarms):
    """Returnerar {nod-id: dict(mode, next, dm)}.
    mode: 'X' (larmar eller ligger i en zon som larmar), 'LEFT', 'RIGHT', 'NONE' (ingen väg ut), 'OFF' (inga larm).
    next: nästa nod-id, 'UT' (ut här) eller None."""
    alarms = set(alarms)
    if not alarms:
        return {i: {"mode": "OFF", "next": None, "dm": 0} for i in topo.order}

    closed = topo.closed(alarms)
    dist = {i: (topo.exit_dm[i] if (i not in closed and topo.exit_dm[i] > 0) else INF) for i in topo.order}
    done = set()
    while True:                                     # Dijkstra baklänges från utsidan
        u, best = None, INF
        for i in topo.order:
            if i not in done and dist[i] < best:
                u, best = i, dist[i]
        if u is None:
            break
        done.add(u)
        for frm, to, dm, _ in topo.edges:
            if to == u and frm not in closed and dist[u] + dm < dist[frm]:
                dist[frm] = dist[u] + dm

    out = {}
    for i in topo.order:
        if i in closed:                              # larmar själv, eller samma zon som ett larm
            out[i] = {"mode": "X", "next": None, "dm": 0}
            continue
        best_total, best_next, best_lamp = INF, None, None
        if topo.exit_dm[i] > 0 and i not in closed:
            best_total, best_next, best_lamp = topo.exit_dm[i], "UT", topo.exit_lamp[i]
        for frm, to, dm, lamp in topo.edges:         # kantordningen avgör vid lika långa vägar, som i C++
            if frm != i or to in closed or dist[to] == INF:
                continue
            if dm + dist[to] < best_total:
                best_total, best_next, best_lamp = dm + dist[to], to, lamp
        if best_total == INF:
            out[i] = {"mode": "NONE", "next": None, "dm": 0}
        else:
            out[i] = {"mode": best_lamp, "next": best_next, "dm": best_total}
    return out


def path_of(res, start):
    """Nodernas väg ut: [start, nästa, ..., 'UT'] (tom om ingen väg)."""
    path, cur = [start], start
    for _ in range(64):
        r = res.get(cur)
        if not r or r["mode"] in ("X", "NONE", "OFF"):
            return [] if r and r["mode"] in ("NONE", "OFF") else path
        nxt = r["next"]
        if nxt == "UT":
            path.append("UT")
            return path
        path.append(nxt)
        cur = nxt
    return []
