#!/bin/sh
# Bygger och kör datortesterna: protokoll mot Python, hela larmkedjan med alla 18 noder i topology.json.
set -e
cd "$(dirname "$0")/.."
python3 scripts/gen_topology.py >/dev/null
OUT=${TMPDIR:-/tmp}/resq_sim
mkdir -p "$OUT"
INC="-Ihost_test/fake -Isrc -Iinclude"
g++ -std=c++14 -Wall -Wextra $INC host_test/sim_test.cpp host_test/fake/fake_arduino.cpp host_test/crypto_host.cpp \
    src/node_controller.cpp src/led_guidance.cpp src/route.cpp src/protocol.cpp -lcrypto -o "$OUT/sim_test"
g++ -std=c++14 -Wall -Wextra -Isrc host_test/proto_dump.cpp host_test/crypto_host.cpp src/protocol.cpp -lcrypto -o "$OUT/proto_dump"
"$OUT/sim_test"
python3 - "$OUT/proto_dump" <<'PY'
import hashlib, hmac, struct, subprocess, sys
key = bytes(i * 17 for i in range(16))
for cmd, sender, nonce in [(1, 2, 12345), (2, 255, 4294967295), (1, 1, 1)]:
    out = subprocess.run([sys.argv[1], str(cmd), str(sender), str(nonce)], capture_output=True, text=True, check=True).stdout.strip()
    msg = bytes([cmd, sender]) + struct.pack("<I", nonce)
    want = msg + hmac.new(key, msg, hashlib.sha256).digest()[:8]
    assert bytes.fromhex(out) == want, (out, want.hex())
print("Signaturen från C++ == Python hmac/sha256 (3 paket, 14 byte vardera)")
PY
