#!/usr/bin/env python3
"""
Skapar .env åt dig, så att du bara behöver trycka på Upload i PlatformIO.

  python3 tools/setup.py 10        # kortet ska vara nod 10 (finns i topology.json)
  python3 tools/setup.py           # frågar efter nodnumret

Första gången skapas en slumpad GROUP_KEY. För nästa kort kör du bara om med ett nytt nodnummer:
nyckeln och kanalen behålls, så att alla kort får samma. Kör med --kanal 6 för att byta kanal.
"""
import json
import os
import re
import secrets
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV = os.path.join(ROOT, ".env")

nodes = {n["id"]: n["name"] for n in json.load(open(os.path.join(ROOT, "topology.json"), encoding="utf-8"))["nodes"]}
args = sys.argv[1:]
channel = None
if "--kanal" in args:
    i = args.index("--kanal")
    channel = args[i + 1]
    del args[i:i + 2]

old = {}
if os.path.exists(ENV):
    for line in open(ENV, encoding="utf-8"):
        m = re.match(r"\s*([A-Z_]+)\s*=\s*(.*?)\s*$", line)
        if m:
            old[m.group(1)] = m.group(2)

if args:
    node = args[0]
else:
    print("Noder på kartan:", ", ".join(f"{i}" for i in sorted(nodes)))
    node = input("Vilket nodnummer ska det här kortet ha? ").strip()
if not node.isdigit() or int(node) not in nodes:
    sys.exit(f"Nod {node!r} finns inte i topology.json. Välj bland: {', '.join(map(str, sorted(nodes)))}")

key = old.get("GROUP_KEY", "")
if not re.fullmatch(r"[0-9a-fA-F]{32}", key):
    key = secrets.token_hex(16)
    print("Skapade en ny GROUP_KEY.")
else:
    print("Behåller din befintliga GROUP_KEY (samma på alla kort).")
channel = channel or old.get("ESPNOW_CHANNEL", "1")
if not channel.isdigit() or not 1 <= int(channel) <= 13:
    sys.exit("Kanalen ska vara 1-13.")

with open(ENV, "w", encoding="utf-8") as f:
    f.write(f"NODE_ID={node}\nESPNOW_CHANNEL={channel}\nGROUP_KEY={key}\n")
print(f".env klar: nod {node} ({nodes[int(node)]}), kanal {channel}.")
print("Nästa steg: koppla kortet med USB och klicka Upload (pilen) i PlatformIO.")
