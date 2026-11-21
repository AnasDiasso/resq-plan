#!/bin/sh
# Bygger node_host: noden som ett datorprogram (Serial via stdin/stdout). Skriver sökvägen.
set -e
cd "$(dirname "$0")/.."
python3 scripts/gen_topology.py >/dev/null
OUT=${TMPDIR:-/tmp}/resq_sim
mkdir -p "$OUT"
g++ -std=c++14 -Wall -Wextra -Ihost_test/fake -Isrc -Iinclude host_test/node_host.cpp host_test/fake/fake_arduino_stdio.cpp \
    src/node_controller.cpp src/led_guidance.cpp src/route.cpp src/protocol.cpp host_test/crypto_host.cpp -lcrypto -o "$OUT/node_host"
echo "$OUT/node_host"
