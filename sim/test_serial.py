#!/usr/bin/env python3
"""
Testar seriekopplingen (pyserial) utan riktigt kort: noden körs som datorprogram på andra sidan av en
virtuell serieport (pty). Kräver Linux eller macOS och pyserial.   python3 sim/test_serial.py
"""
import http.client
import json
import os
import pty
import subprocess
import sys
import time
import tty

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "sim"))
try:
    import serial  # noqa: F401
except ImportError:
    sys.exit("pyserial saknas: pip install pyserial")
import server  # noqa: E402

host = subprocess.run([ROOT + "/host_test/build_node_host.sh"], capture_output=True, text=True, check=True).stdout.strip()
master, slave = pty.openpty()
tty.setraw(slave)                       # inget eko, precis som en riktig USB-port
proc = subprocess.Popen([host, "3"], stdin=master, stdout=master, stderr=subprocess.DEVNULL)
hub = server.build([os.ttyname(slave)], [])
srv = server.start(hub, "127.0.0.1", 0)
PORT = srv.server_address[1]


def api(method, path, body=None):
    c = http.client.HTTPConnection("127.0.0.1", PORT, timeout=5)
    c.request(method, path, body=json.dumps(body) if body is not None else None,
              headers={"Content-Type": "application/json"})
    r = c.getresponse()
    return json.loads(r.read())


def fail(msg):
    st = api("GET", "/api/state")
    print("FEL:", msg, st["alarms"], st["boards"])
    proc.kill()
    os._exit(1)


def wait(pred, what, t=8):
    t0 = time.time()
    while time.time() - t0 < t:
        s = api("GET", "/api/state")
        if pred(s):
            return s
        time.sleep(0.1)
    fail(what)


s = wait(lambda s: s["boards"] and s["boards"][0]["node_id"] == 3, "kortet presenterar sig över serieporten")
api("POST", "/api/click", {"id": 9})
wait(lambda s: s["alarms"] == [9] and s["boards"][0]["signal"] == "RIGHT", "larm 9 ska nå kortet och ge gul pil")
api("POST", "/api/click", {"id": 3})
wait(lambda s: s["alarms"] == [3, 9] and s["boards"][0]["signal"] == "X", "knapptryck på kortet ska ge X")
api("POST", "/api/click", {"id": 3})
wait(lambda s: s["alarms"] == [9], "avstängning av kortets larm", t=6)
print("OK: seriekopplingen (HELLO, larm till kortet, knapptryck, avstängning)")
proc.kill()
os._exit(0)
