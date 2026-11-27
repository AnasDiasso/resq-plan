"""
Jämför C++-motorn (route.cpp) mot en oberoende Python-referens (framåt-Dijkstra med heapq).
Testar alla enskilda larm, alla par av larm och slumpade grupper. Kör: python3 host_test/compare.py
"""
import heapq, itertools, json, os, random, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
subprocess.check_call(["python3", os.path.join(ROOT, "scripts", "gen_topology.py"), ROOT], stdout=subprocess.DEVNULL)
subprocess.check_call(["g++", "-std=c++11", "-Wall", "-Wextra", "-I" + ROOT + "/include", "-I" + ROOT + "/src",
                       ROOT + "/host_test/sim_main.cpp", ROOT + "/src/route.cpp", "-o", "/tmp/sim_cmp"])
T = json.load(open(os.path.join(ROOT, "topology.json"), encoding="utf-8"))
ids = [n["id"] for n in T["nodes"]]
exit_dm = {n["id"]: round(n.get("exit_m", 0) * 10) for n in T["nodes"]}
out_edges = {i: [] for i in ids}
for e in T["edges"]:
    out_edges[e["from"]].append((e["to"], round(e["m"] * 10), e["lamp"]))

zone_of = {n["id"]: n.get("zone") for n in T["nodes"]}
def closed(alarms):
    c = set(alarms)
    for a in alarms:
        if zone_of[a]: c |= {i for i in ids if zone_of[i] == zone_of[a]}
    return c

def ref(src, alarms):
    """Kortaste väg från src till utsidan. Returnerar meter*10, None (ingen väg) eller 'X' (larmar själv eller i larmande zon)."""
    cl = closed(alarms)
    if src in cl: return "X"
    return dist_from(src, cl)

def dist_from(src, blocked):
    """Framåt-Dijkstra från src; noder i 'blocked' får inte beträdas (src själv får starta) och utgångar där räknas inte."""
    dist = {src: 0}; pq = [(0, src)]; best = None
    while pq:
        d, u = heapq.heappop(pq)
        if d > dist.get(u, 1e18): continue
        if exit_dm[u] > 0 and u not in blocked:
            tot = d + exit_dm[u]
            if best is None or tot < best: best = tot
        for v, w, _ in out_edges[u]:
            if v in blocked: continue
            nd = d + w
            if nd < dist.get(v, 1e18):
                dist[v] = nd; heapq.heappush(pq, (nd, v))
    return best

def check(blocked):
    args = [str(b) for b in sorted(blocked)]
    res = subprocess.run(["/tmp/sim_cmp"] + args, capture_output=True, text=True, check=True).stdout.split("\n")
    rows = {}
    for line in res:
        if not line: continue
        i, mode, nxt, m = line.split(); rows[int(i)] = (mode, nxt, round(float(m) * 10))
    for i in ids:
        mode, nxt, dm = rows[i]
        want = ref(i, blocked)
        cl = closed(blocked)
        if want == "X":
            assert mode == "X", (blocked, i, rows[i])
        elif want is None:
            assert mode == "INGEN", (blocked, i, rows[i])
        else:
            assert mode in ("LEFT", "RIGHT"), (blocked, i, rows[i])
            assert dm == want, (blocked, i, rows[i], want)
            # vald pil måste höra till en kant (eller utgången) som ger exakt den längden
            if nxt == "UT":
                assert exit_dm[i] == dm
                assert i not in cl and any(n["id"] == i and n.get("exit_lamp") == mode for n in T["nodes"])
            else:
                nx = int(nxt)
                w = [(w, l) for v, w, l in out_edges[i] if v == nx]
                assert w and w[0][1] == mode and nx not in cl, (blocked, i, rows[i])
                assert w[0][0] + dist_from(nx, cl) == dm, (blocked, i, rows[i])
    return True

n = 0
check(set()); n += 1
for a in ids: check({a}); n += 1
for a, b in itertools.combinations(ids, 2): check({a, b}); n += 1
random.seed(1)
for _ in range(300):
    check(set(random.sample(ids, random.randint(3, 8)))); n += 1
print(f"OK: {n} scenarier, C++ == Python-referens (längd och pil) för alla {len(ids)} noder")
