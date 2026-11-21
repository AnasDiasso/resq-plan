"""
PlatformIO pre-script: läser .env och skapar include/secrets.h.
Du redigerar bara .env. secrets.h genereras om vid varje bygge och ska inte checkas in.
Kan köras för hand:  python3 scripts/load_env.py [projektmapp]
"""
import json
import os
import re
import sys

REQUIRED = ["NODE_ID", "ESPNOW_CHANNEL", "GROUP_KEY"]
EXAMPLE_GROUP_KEY = "3A91C75E08D2B46F1DA872E3954B0CF6"   # exempelnyckeln från äldre kod, ska inte användas


def parse_env(path):
    values = {}
    with open(path, encoding="utf-8") as f:
        for n, raw in enumerate(f, 1):
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                raise ValueError(f".env rad {n}: förväntade NYCKEL=värde")
            key, val = line.split("=", 1)
            key, val = key.strip(), val.strip()
            if len(val) >= 2 and val[0] == val[-1] and val[0] in "\"'":
                val = val[1:-1]
            values[key] = val
    return values


def generate(project_dir):
    env_path = os.path.join(project_dir, ".env")
    if not os.path.isfile(env_path):
        return False, ".env saknas. Kopiera .env.example till .env och fyll i dina värden (cp .env.example .env)."
    try:
        v = parse_env(env_path)
    except ValueError as e:
        return False, str(e)

    missing = [k for k in REQUIRED if not v.get(k)]
    if missing:
        return False, "Saknas i .env: " + ", ".join(missing)
    placeholders = [k for k, val in v.items() if "CHANGE_ME" in val]
    if placeholders:
        return False, "Byt ut CHANGE_ME i .env för: " + ", ".join(placeholders)

    try:
        node_id = int(v["NODE_ID"])
        if not 1 <= node_id <= 255:
            raise ValueError
    except ValueError:
        return False, "NODE_ID måste vara ett heltal 1-255."
    topo = os.path.join(project_dir, "topology.json")
    if os.path.isfile(topo):
        with open(topo, encoding="utf-8") as f:
            ids = [n["id"] for n in json.load(f).get("nodes", [])]
        if node_id not in ids:
            return False, f"NODE_ID {node_id} finns inte i topology.json (giltiga: {min(ids)}-{max(ids)})."

    try:
        channel = int(v["ESPNOW_CHANNEL"])
        if not 1 <= channel <= 13:
            raise ValueError
    except ValueError:
        return False, "ESPNOW_CHANNEL måste vara ett heltal 1-13 (samma på alla noder)."

    key_hex = v["GROUP_KEY"].replace(" ", "").replace(":", "")
    if not re.fullmatch(r"[0-9a-fA-F]{32}", key_hex):
        return False, ("GROUP_KEY måste vara 32 hex-tecken (16 byte). "
                       "Skapa en med: python3 -c \"import secrets; print(secrets.token_hex(16))\"")
    if key_hex.upper() == EXAMPLE_GROUP_KEY:
        return False, "GROUP_KEY är exempelnyckeln från äldre kod. Skapa din egen (se .env.example)."
    key_bytes = ", ".join(f"0x{key_hex[i:i+2].upper()}" for i in range(0, 32, 2))

    header = f"""// GENERERAD AV scripts/load_env.py FRÅN .env. REDIGERA INTE HÄR, ändra .env.
// Den här filen ska inte checkas in.
#pragma once
#include <stdint.h>

#define NODE_ID {node_id}
const uint8_t ESPNOW_CHANNEL = {channel};
const uint8_t GROUP_KEY[16] = {{ {key_bytes} }};
"""
    out_dir = os.path.join(project_dir, "include")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "secrets.h")
    old = None
    if os.path.isfile(out_path):
        with open(out_path, encoding="utf-8") as f:
            old = f.read()
    if old != header:
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(header)
        try:
            os.chmod(out_path, 0o600)
        except OSError:
            pass
    return True, f"include/secrets.h skapad från .env (nod {node_id}, kanal {channel})"


def _run(project_dir, env=None):
    ok, msg = generate(project_dir)
    print(f"[load_env] {msg}")
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
