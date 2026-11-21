"""
Ritar vad varje nod visar på kartan, med exakt samma beräkning som noden (route.cpp).
Kör:  python3 tools/render_map.py <ut.png> <larmande nod-id> [fler id ...]
"""
import json, math, os, subprocess, sys
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
out = sys.argv[1]; alarms = [int(a) for a in sys.argv[2:]]
subprocess.check_call(["python3", ROOT + "/scripts/gen_topology.py", ROOT], stdout=subprocess.DEVNULL)
subprocess.check_call(["g++", "-std=c++11", "-I" + ROOT + "/include", "-I" + ROOT + "/src",
                       ROOT + "/host_test/sim_main.cpp", ROOT + "/src/route.cpp", "-o", "/tmp/sim_render"])
rows = subprocess.run(["/tmp/sim_render"] + [str(a) for a in alarms], capture_output=True, text=True, check=True).stdout.split("\n")
T = json.load(open(ROOT + "/topology.json", encoding="utf-8"))
node = {n["id"]: n for n in T["nodes"]}

im = Image.open(ROOT + "/docs/karta_ren.png").convert("RGB")
# tona ned kartan så att pilarna syns
im = Image.blend(im, Image.new("RGB", im.size, (255, 255, 255)), 0.45)
d = ImageDraw.Draw(im)
try:
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 22)
    big = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 34)
except OSError:
    font = big = ImageFont.load_default()
GREEN, YELLOW, RED = (0, 150, 60), (235, 170, 0), (215, 0, 0)

def arrow(p, q, col, w=7):
    d.line([p, q], fill=col, width=w)
    ang = math.atan2(q[1]-p[1], q[0]-p[0]); L = 24
    for s in (-0.5, 0.5):
        d.line([q, (q[0]-L*math.cos(ang+s), q[1]-L*math.sin(ang+s))], fill=col, width=w)

# stängda zoner (trapphus med larm): röd ring runt noderna
zones = {n["id"]: n.get("zone") for n in node.values()}
for a in alarms:
    z = zones.get(a)
    for n in node.values():
        if (z and zones[n["id"]] == z) and n["id"] != a:
            d.ellipse([n["x"]-30, n["y"]-30, n["x"]+30, n["y"]+30], outline=RED, width=4)

for line in rows:
    if not line: continue
    i, mode, nxt, m = line.split(); i = int(i); n = node[i]; p = (n["x"], n["y"])
    if mode == "X":
        d.line([p[0]-26, p[1]-26, p[0]+26, p[1]+26], fill=RED, width=10)
        d.line([p[0]-26, p[1]+26, p[0]+26, p[1]-26], fill=RED, width=10)
    elif mode == "INGEN":
        d.text((p[0]-20, p[1]-45), "?", fill=RED, font=big)
    else:
        col = GREEN if mode == "LEFT" else YELLOW
        if nxt == "UT":
            sgn = -1 if n.get("exit_dir") == "up" else 1
            arrow((p[0], p[1]), (p[0], p[1]+sgn*60), col, 9)
            d.text((p[0]+14, p[1]+sgn*34-12), "UT", fill=col, font=font)
        else:
            q = node[int(nxt)]
            vx, vy = q["x"]-p[0], q["y"]-p[1]; L = math.hypot(vx, vy)
            k = min(70, L*0.45) / L                    # kort pil åt rätt håll
            arrow(p, (p[0]+vx*k, p[1]+vy*k), col)
    d.ellipse([p[0]-12, p[1]-12, p[0]+12, p[1]+12], fill=(30, 90, 220), outline=(255, 255, 255), width=2)
    d.text((p[0]+16, p[1]-30), str(i), fill=(0, 0, 0), font=font)

d.rectangle([20, 20, 760, 105], fill=(255, 255, 255), outline=(0, 0, 0))
d.text((32, 28), "Larm från nod " + ", ".join(map(str, alarms)) + ":  rött X = larmar", fill=(0, 0, 0), font=font)
d.text((32, 62), "grön = LEFT-pil   gul = RIGHT-pil   UT = ut genom utgången", fill=(0, 0, 0), font=font)
im.save(out)
print("sparade", out)
