#!/usr/bin/env python3
"""
Tester för simulatorn. Kör:  python3 sim/test_sim.py
 1. sim/routing.py ger exakt samma vägval som noden (C++) för alla enskilda larm, par och slumpade grupper.
 2. Hela kedjan: servern + en riktig nodlogik (host_test/node_host, samma C++ som på kortet) via Serial-protokollet:
    klick på virtuell nod, knapptryck på "riktiga kortet", avstängning, rensa, och att kortets lampor
    alltid stämmer med simuleringen.
"""
import http.client
import itertools
import json
import os
import random
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "sim"))
import routing  # noqa: E402
import server   # noqa: E402

checks = 0


def check(cond, msg):
    global checks
    checks += 1
    if not cond:
        print("FEL:", msg)
        sys.exit(1)


# ---------------------------------------------------------------- 1. routing.py mot C++
subprocess.check_call(["python3", ROOT + "/scripts/gen_topology.py", ROOT], stdout=subprocess.DEVNULL)
subprocess.check_call(["g++", "-std=c++11", "-I" + ROOT + "/include", "-I" + ROOT + "/src",
                       ROOT + "/host_test/sim_main.cpp", ROOT + "/src/route.cpp", "-o", "/tmp/sim_routing_cmp"])
topo = routing.Topology(os.path.join(ROOT, "topology.json"))
ids = topo.order


def cpp(alarms):
    out = subprocess.run(["/tmp/sim_routing_cmp"] + [str(a) for a in sorted(alarms)],
                         capture_output=True, text=True, check=True).stdout.split("\n")
    rows = {}
    for line in out:
        if line:
            i, mode, nxt, m = line.split()
            rows[int(i)] = (mode, nxt, round(float(m) * 10))
    return rows


def same(alarms):
    c, p = cpp(alarms), routing.compute(topo, alarms)
    for i in ids:
        mode, nxt, dm = c[i]
        r = p[i]
        want_mode = {"NONE": "INGEN"}.get(r["mode"], r["mode"])
        want_next = "-" if r["next"] is None else str(r["next"])
        check((mode, nxt) == (want_mode, want_next) and (dm == r["dm"] or mode in ("X", "INGEN")),
              f"larm {sorted(alarms)} nod {i}: C++ {c[i]} != Python {r}")


n = 0
for a in ids:
    same({a}); n += 1
for a, b in itertools.combinations(ids, 2):
    same({a, b}); n += 1
random.seed(3)
for _ in range(300):
    same(set(random.sample(ids, random.randint(3, 8)))); n += 1
print(f"OK: routing.py == C++ i {n} larmscenarier (nästa nod, pil och längd för alla noder)")

# ---------------------------------------------------------------- 1b. hall, dörrar och rum
# Hallen (7, 10, 12) leder till trapphusen. Dörrar (8, 9, 11, 13) och rum (14-18) är inte genomfart.
SCENARIOS = [
    ({3}, 7, [7, 10, 12, 6, 5, 4, "UT"]),                 # 1: vänster trapphus stängt
    ({7}, 8, [8, 10, 12, 6, 5, 4, "UT"]),                 # 2: hallen vid dörr 1 larmar
    ({8, 9}, 14, [14, 15, 17, 11, 12, 6, 5, 4, "UT"]),    # 3: båda dörrarna till rum 14 larmar
    ({3}, 13, [13, 6, 5, 4, "UT"]),                      # dörr 4 går direkt till trapphuset vid 6
    ({12}, 13, [13, 6, 5, 4, "UT"]),                     # ... även när hallen vid 12 larmar
    ({6}, 13, [13, 12, 10, 7, 3, 2, 1, "UT"]),           # trapphuset vid 6 stängt: via hallen
    ({7, 18}, 16, [16, 11, 12, 6, 5, 4, "UT"]),          # rum 16: ut genom egna dörren vid 11 när 18 larmar
    ({17, 18}, 16, [16, 11, 12, 6, 5, 4, "UT"]),
]
for alarms, start, want in SCENARIOS:
    got = routing.path_of(routing.compute(topo, alarms), start)
    check(got == want, f"larm {sorted(alarms)} nod {start}: väg {got}, väntade {want}")
    check(cpp(alarms)[start][1] == str(want[1]), f"larm {sorted(alarms)} nod {start}: C++ går till {cpp(alarms)[start][1]}, väntade {want[1]}")

kind = {i: topo.nodes[i].get("kind") for i in ids}
check(all(kind[i] in ("stair", "hall", "door", "room") for i in ids), "alla noder ska ha kind")
for a in ids:                                            # inget enskilt larm får lämna en annan nod utan väg ut
    none = [i for i, r in routing.compute(topo, {a}).items() if r["mode"] == "NONE"]
    check(not none, f"larm {a}: frågetecken på {none}")
through = [i for i in ids if kind[i] in ("stair", "hall")]
random.seed(5)
groups = [{a} for a in ids] + [set(p) for p in itertools.combinations(ids, 2)] + \
         [set(random.sample(ids, random.randint(3, 8))) for _ in range(300)]
n_paths = 0
for alarms in groups:
    res = routing.compute(topo, alarms)
    for i in through:
        path = routing.path_of(res, i)
        bad = [j for j in path[1:] if j != "UT" and kind[j] in ("door", "room")]
        check(not bad, f"larm {sorted(alarms)}: vägen från {kind[i]} {i} går via dörr/rum {bad}: {path}")
        n_paths += 1
print(f"OK: {len(SCENARIOS)} scenarier, och {n_paths} vägar från hall och trapphus går aldrig via dörr eller rum")

# ---------------------------------------------------------------- 1c. vägen ut från en nod som larmar
for alarms, start, want in [({3}, 3, [3, 7, 10, 12, 6, 5, 4, "UT"]),   # trapphuset stängt: via hallen
                            ({7}, 7, [7, 3, 2, 1, "UT"]),
                            ({3}, 1, [1, "UT"]),                       # står vid utgången: ut där
                            ({3}, 2, [])]:                             # plan 2 i stängt trapphus: ingen väg
    got = routing.escape(topo, alarms, start)[0]
    check(got == want, f"larm {sorted(alarms)}: vägen ut från nod {start} är {got}, väntade {want}")
n_esc = 0
for alarms in groups:
    res = routing.compute(topo, alarms)
    closed = topo.closed(alarms)
    for i in closed:
        path, dm = routing.escape(topo, alarms, i, res)
        check(not [j for j in path[1:] if j in closed], f"larm {sorted(alarms)}: vägen ut från {i} går genom stängd nod: {path}")
        if path and path[1] != "UT":                     # lika lång som kanten + grannens väg ut
            e = next(d for f, t, d, _ in topo.edges if f == i and t == path[1])
            check(dm == e + res[path[1]]["dm"], f"larm {sorted(alarms)}: fel längd från {i}")
        n_esc += 1
print(f"OK: vägen ut från noder som larmar ({n_esc} fall) går aldrig genom en stängd nod")

# ---------------------------------------------------------------- 2. hela kedjan
host = subprocess.run([ROOT + "/host_test/build_node_host.sh"], capture_output=True, text=True, check=True).stdout.strip()
REAL = 3
hub = server.build([], [f"{host} {REAL}"])
srv = server.start(hub, "127.0.0.1", 0)
PORT = srv.server_address[1]


def api(method, path, body=None):
    c = http.client.HTTPConnection("127.0.0.1", PORT, timeout=5)
    c.request(method, path, body=json.dumps(body) if body is not None else None,
              headers={"Content-Type": "application/json"})
    r = c.getresponse()
    data = r.read()
    c.close()
    try:
        return r.status, json.loads(data)
    except ValueError:
        return r.status, data.decode()


def state():
    return api("GET", "/api/state")[1]


def wait(pred, what, timeout=4.0):
    t0 = time.time()
    while time.time() - t0 < timeout:
        s = state()
        if pred(s):
            return s
        time.sleep(0.05)
    check(False, "timeout: " + what + "\n" + json.dumps(state()["boards"]) + json.dumps(state()["alarms"]))


def node(s, i):
    return next(n for n in s["nodes"] if n["id"] == i)


def expected_signal(alarms):
    r = routing.compute(topo, set(alarms))[REAL]["mode"]
    return {"X": "X", "LEFT": "LEFT", "RIGHT": "RIGHT"}.get(r, "OFF")


def board_matches(alarms, what):
    want = expected_signal(alarms)
    s = wait(lambda s: s["boards"][0]["signal"] == want, f"{what}: kortet ska visa {want}")
    return s


s = wait(lambda s: s["boards"] and s["boards"][0]["node_id"] == REAL, "kortet presenterar sig")
check(node(s, REAL)["real"], "nod 3 ska vara ett riktigt kort")
check(s["alarms"] == [], "inga larm från start")

# a) klick på virtuell nod 9
api("POST", "/api/click", {"id": 9})
s = wait(lambda s: s["alarms"] == [9], "larm nod 9")
board_matches({9}, "larm 9")
check(node(s, REAL)["mode"] == "RIGHT", "nod 3 ska peka ner för trappan vid larm 9")

# b) knapptryck på riktiga kortet (klick på dess nod) -> larm från kortet
api("POST", "/api/click", {"id": REAL})
s = wait(lambda s: s["alarms"] == [3, 9], "kortets egna larm syns i simuleringen")
check(node(s, REAL)["mode"] == "X", "nod 3 ska visa X")
board_matches({3, 9}, "eget larm")
check(any("knapp på kortet" in e["text"] for e in s["events"]), "händelsen 'knapp på kortet' ska loggas")

# c) tryck igen: X blinkar, sedan släcks kortets larm
api("POST", "/api/click", {"id": REAL})
s = wait(lambda s: s["alarms"] == [9], "avstängning av kortets larm", timeout=4)
board_matches({9}, "efter avstängning")

# d) slå av nod 9, allt släckt
api("POST", "/api/click", {"id": 9})
wait(lambda s: s["alarms"] == [], "alla larm borta")
board_matches(set(), "inga larm")

# e) slumpade klick på virtuella noder: kortet ska alltid visa samma som simuleringen
random.seed(11)
active = set()
for step in range(40):
    nid = random.choice([i for i in ids if i != REAL])
    api("POST", "/api/click", {"id": nid})
    active ^= {nid}
    wait(lambda s: sorted(s["alarms"]) == sorted(active), f"steg {step}: larmmängd {sorted(active)}")
    board_matches(active, f"steg {step} larm {sorted(active)}")
n_fuzz = 40

# f) efter pausen ska simulatorn säga att kortet stämmer
time.sleep(server.MATCH_GRACE_S + 0.3)
s = state()
check(node(s, REAL)["match"] is True, "kortet ska markeras som 'stämmer' när allt är lugnt")

# g) rensa alla
api("POST", "/api/clear")
wait(lambda s: s["alarms"] == [], "rensa")
board_matches(set(), "efter rensa")

# h) SSE-ström
c = http.client.HTTPConnection("127.0.0.1", PORT, timeout=5)
c.request("GET", "/api/stream")
r = c.getresponse()
check(r.status == 200 and "text/event-stream" in r.getheader("Content-Type"), "SSE-rubrik")
line = r.fp.readline().decode()
check(line.startswith("data: ") and len(json.loads(line[6:])["nodes"]) == len(ids), "SSE skickar status direkt")
c.close()

# i) felaktiga anrop
check(api("POST", "/api/click", {"id": "x"})[0] == 400, "id som inte är heltal ska ge 400")
check(api("POST", "/api/click", {"id": 99})[0] == 200 and state()["alarms"] == [], "okänd nod ignoreras")
check(api("GET", "/finns-inte")[0] == 404, "okänd sökväg ska ge 404")
st = http.client.HTTPConnection("127.0.0.1", PORT, timeout=5)
st.request("GET", "/"); r = st.getresponse(); body = r.read().decode()
check(r.status == 200 and "resQ-simulator" in body, "startsidan ska levereras")
st.request("GET", "/karta.png"); r = st.getresponse(); png = r.read()
check(r.status == 200 and png[:4] == b"\x89PNG", "kartbilden ska levereras")
st.request("GET", "/lamps.json"); r = st.getresponse(); lj = r.read()
check(r.status == 200, "lamps.json ska levereras")
LJ = json.loads(lj)
topo_ids = [n["id"] for n in json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "topology.json")))["nodes"]]
check(sorted(int(k) for k in LJ["nodes"]) == sorted(topo_ids), "lamps.json har alla noder")
check(all(len(v["triangles"]) == 2 and sorted(v["lamp_map"].values()) == [0, 1] for v in LJ["nodes"].values()),
      "varje nod har 2 trianglar med olika lampor")
check(all(v["cross"] for v in LJ["nodes"].values()), "varje nod har ett kryss")

check(sorted(map(tuple, state()["links"])) == [(1, 2), (2, 3), (4, 5), (5, 6)], "trapphusen förbinder våningarna (links)")

# i2) dra bort och sätt tillbaka noder
api("POST", "/api/clear", {})
api("POST", "/api/click", {"id": 9})
s9 = node(state(), 9)
check(s9["mode"] == "X" and s9["path"] == [9, 7, 3, 2, 1, "UT"] and s9["meters"] == 54.9, f"nod 9 som larmar ska visa vägen ut härifrån: {s9}")
before = {n["id"]: (n["mode"], n["next"]) for n in state()["nodes"] if n["id"] != 9}
check(api("POST", "/api/remove", {"id": 9})[0] == 200, "remove svarar 200")
s9 = [n for n in state()["nodes"] if n["id"] == 9][0]
check(s9["removed"] and s9["mode"] == "OFF" and state()["alarms"] == [], "borttagen nod släcks och dess larm försvinner")
api("POST", "/api/click", {"id": 9})
check(state()["alarms"] == [], "borttagen nod kan inte larma")
check(api("POST", "/api/remove", {"id": "x"})[0] == 400, "remove med fel id ger 400")
api("POST", "/api/restore", {"id": 9})
check(not [n for n in state()["nodes"] if n["id"] == 9][0]["removed"], "nod satt tillbaka")
api("POST", "/api/click", {"id": 9})
check(state()["alarms"] == [9], "återsatt nod kan larma igen")
api("POST", "/api/clear", {})

# j) larm går ut efter tiden (utan kort)
server.ALARM_S = 0.2
h2 = server.build([], [])
threading_started = server.threading.Thread(target=h2.expire_loop, daemon=True); threading_started.start()
h2.click(5)
check(h2.alarms.keys() == {5}, "larm 5 skapat")
t0 = time.time()
while h2.alarms and time.time() - t0 < 8:
    time.sleep(0.2)
check(not h2.alarms, "larmet ska gå ut av sig självt")

print(f"OK: hela kedjan (server + nodlogik): {checks} kontroller, {n_fuzz} slumpade klick, kortet stämde med simuleringen hela tiden")
