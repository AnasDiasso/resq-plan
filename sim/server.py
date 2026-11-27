#!/usr/bin/env python3
"""
resQ-simulator: en karta i webbläsaren som visar vad som händer mellan noderna.

  python3 sim/server.py                          bara simulering (alla noder virtuella)
  python3 sim/server.py --port COM3              koppla ett riktigt kort (USB) till kartan
  python3 sim/server.py --port COM3 --port COM5  flera kort
  python3 sim/server.py --exec "host_test/node_host 3"   nod som datorprogram (test utan kort)

Öppna sedan http://127.0.0.1:8000. Klicka på en nod för att larma/stänga av den.
Riktiga kort kopplas via USB (Serial 115200) och ska heta olika NODE_ID. Stäng PlatformIOs Serial Monitor
först, eftersom bara ett program kan använda porten.
Kräver bara Python 3.9+. Seriekopplingen kräver också:  pip install pyserial
"""
import argparse
import json
import os
import shlex
import subprocess
import sys
import threading
import time
from collections import deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import routing  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ALARM_S = 300            # larm gäller 5 minuter, som i noden
MATCH_GRACE_S = 1.5      # så länge väntar vi innan vi jämför kortets lampor med simuleringen
BAUD = 115200


# ---------------------------------------------------------------------------
# Kort (riktigt via USB, eller datorprogram för test)
# ---------------------------------------------------------------------------
class Board(threading.Thread):
    def __init__(self, hub, label):
        super().__init__(daemon=True)
        self.hub = hub
        self.label = label
        self.node_id = None
        self.connected = False
        self.signal = None
        self.signal_since = 0.0
        self.wlock = threading.Lock()

    def write(self, text):
        raise NotImplementedError


class SerialBoard(Board):
    def __init__(self, hub, port):
        super().__init__(hub, port)
        self.port = port
        self.ser = None

    def write(self, text):
        with self.wlock:
            if self.ser is not None:
                try:
                    self.ser.write(text.encode())
                except Exception:
                    pass

    def run(self):
        try:
            import serial
        except ImportError:
            self.hub.log("pyserial saknas. Installera med: pip install pyserial", "fel")
            return
        while True:
            try:
                self.ser = serial.Serial(self.port, BAUD, timeout=0.3)
                self.connected = True
                self.hub.log(f"Ansluten till {self.port}", "info")
                self.hub.changed()
                time.sleep(2.0)                       # kortet startar om när porten öppnas
                self.write("h\n")                     # be kortet presentera sig
                buf = b""
                while True:
                    chunk = self.ser.read(256)
                    if chunk:
                        buf += chunk
                        while b"\n" in buf:
                            line, buf = buf.split(b"\n", 1)
                            self.hub.on_line(self, line.decode(errors="replace").strip())
            except Exception as e:
                if self.connected:
                    self.hub.log(f"Tappade kontakten med {self.port}: {e}", "fel")
                self.connected = False
                self.ser = None
                self.hub.changed()
                time.sleep(3.0)


class ProcBoard(Board):
    def __init__(self, hub, cmd):
        super().__init__(hub, cmd)
        self.cmd = cmd
        self.proc = None

    def write(self, text):
        with self.wlock:
            if self.proc and self.proc.stdin:
                try:
                    self.proc.stdin.write(text)
                    self.proc.stdin.flush()
                except Exception:
                    pass

    def run(self):
        self.proc = subprocess.Popen(shlex.split(self.cmd), stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                     text=True, bufsize=1)
        self.connected = True
        self.hub.log(f"Startade {self.cmd}", "info")
        self.hub.changed()
        for line in self.proc.stdout:
            self.hub.on_line(self, line.strip())
        self.connected = False
        self.hub.log(f"{self.cmd} avslutades", "fel")
        self.hub.changed()


# ---------------------------------------------------------------------------
# Hubben: all gemensam status
# ---------------------------------------------------------------------------
class Hub:
    def __init__(self, topo):
        self.topo = topo
        self.cond = threading.Condition(threading.RLock())
        self.version = 0
        self.alarms = {}                   # nod-id -> {"until": tid, "origin": str}
        self.removed = set()               # noder som dragits bort från sin plats (grop på kartan)
        self.boards = []
        self.events = deque(maxlen=300)
        self.last_change = 0.0

    # --- hjälp ---
    def changed(self):
        with self.cond:
            self.version += 1
            self.last_change = time.monotonic()
            self.cond.notify_all()

    def log(self, text, kind="info"):
        with self.cond:
            self.events.appendleft({"t": time.strftime("%H:%M:%S"), "kind": kind, "text": text})
            self.version += 1
            self.cond.notify_all()

    def node_name(self, i):
        n = self.topo.nodes.get(i)
        return f"nod {i}" + (f" ({n['name']})" if n else "")

    def board_for(self, node_id):
        for b in self.boards:
            if b.connected and b.node_id == node_id:
                return b
        return None

    def to_boards(self, text, skip=None):
        for b in self.boards:
            if b.connected and b is not skip:
                b.write(text)

    # --- händelser från korten ---
    def on_line(self, board, line):
        if not line:
            return
        if not line.startswith("EVT "):
            if line.startswith(("VARNING", "INGEN VAG", "OBS")):
                self.log(f"{board.label}: {line}", "varning")
            return
        parts = line.split()
        name = parts[1] if len(parts) > 1 else ""
        try:
            nid = int(parts[2]) if len(parts) > 2 else None
        except ValueError:
            nid = None
        extra = parts[3] if len(parts) > 3 else ""

        with self.cond:
            if name == "HELLO":
                board.node_id = nid
                board.connected = True
                self.log(f"Kortet på {board.label} är {self.node_name(nid)}", "info")
                for aid, a in list(self.alarms.items()):      # ge kortet de larm det missat (t.ex. efter omstart)
                    if aid != nid:
                        board.write(f"a{aid}\n")
            elif name == "STATE":
                if extra and extra != "-":
                    for s in extra.split(","):
                        if s.isdigit() and int(s) not in self.alarms and int(s) in self.topo.nodes:
                            self.alarms[int(s)] = {"until": time.monotonic() + ALARM_S, "origin": f"kort {board.label}"}
            elif name == "ALARM_ON" and nid in self.topo.nodes:
                if extra != "sim" and nid not in self.alarms:
                    self.alarms[nid] = {"until": time.monotonic() + ALARM_S, "origin": extra or "kort"}
                    self.log(f"Larm från {self.node_name(nid)} ({'knapp på kortet' if extra == 'own' else 'radio' if extra == 'radio' else extra})", "larm")
            elif name == "ALARM_OFF" and nid in self.topo.nodes:
                if extra != "sim" and nid in self.alarms:
                    del self.alarms[nid]
                    self.log(f"Larmet från {self.node_name(nid)} är slut ({'avstängt' if extra in ('own', 'radio') else extra})", "info")
            elif name == "CANCEL_START":
                self.log(f"{self.node_name(nid)} stänger av sitt larm (X blinkar)", "info")
            elif name == "SIGNAL":
                board.signal = extra
                board.signal_since = time.monotonic()
            self.changed()

    # --- kommandon från webbläsaren ---
    def remove(self, nid):
        """Drar bort en virtuell nod från sin plats: lamporna släcks, den kan inte larma och tar inte emot larm.
        Övriga noders vägval ändras inte (kortens karta är fast, det finns inget grannsystem än)."""
        if nid not in self.topo.nodes:
            return False
        with self.cond:
            if self.board_for(nid) is not None:
                self.log(f"{self.node_name(nid)} har ett riktigt kort och kan inte dras bort", "info")
                return False
            if nid in self.removed:
                return True
            self.removed.add(nid)
            if nid in self.alarms:
                del self.alarms[nid]
                self.to_boards(f"d{nid}\n")
            self.log(f"{self.node_name(nid)} borttagen från sin plats (platsen är ledig)", "info")
            self.changed()
            return True

    def restore(self, nid):
        if nid not in self.topo.nodes:
            return
        with self.cond:
            if nid in self.removed:
                self.removed.discard(nid)
                self.log(f"{self.node_name(nid)} satt tillbaka på sin plats", "info")
                self.changed()

    def click(self, nid):
        if nid not in self.topo.nodes or nid in self.removed:
            return
        with self.cond:
            real = self.board_for(nid)
            if real is not None:                               # riktigt kort: tryck på dess knapp
                self.log(f"Tryck på knappen på kortet ({self.node_name(nid)})", "info")
                real.write("b\n")
                return
            if nid in self.alarms:                             # virtuell nod: stäng av
                del self.alarms[nid]
                self.log(f"Larm från {self.node_name(nid)} avstängt (simulerat)", "info")
                self.to_boards(f"d{nid}\n")
            else:
                self.alarms[nid] = {"until": time.monotonic() + ALARM_S, "origin": "simulerad"}
                self.log(f"Larm från {self.node_name(nid)} (simulerat)", "larm")
                self.to_boards(f"a{nid}\n")
            self.changed()

    def clear(self):
        with self.cond:
            self.alarms.clear()
            self.to_boards("c\n")
            self.log("Alla larm rensade", "info")
            self.changed()

    def expire_loop(self):
        while True:
            time.sleep(1.0)
            now = time.monotonic()
            with self.cond:
                gone = [i for i, a in self.alarms.items() if now > a["until"] + 3]
                for i in gone:
                    del self.alarms[i]
                    self.log(f"Larmet från {self.node_name(i)} gick ut (5 min)", "info")
                if gone:
                    self.changed()

    # --- tillstånd till webbläsaren ---
    def snapshot(self):
        with self.cond:
            now = time.monotonic()
            res = routing.compute(self.topo, set(self.alarms))
            nodes = []
            for i in self.topo.order:
                n = self.topo.nodes[i]
                r = res[i]
                board = self.board_for(i)
                expected = {"X": "X", "LEFT": "LEFT", "RIGHT": "RIGHT"}.get(r["mode"], "OFF")
                match = None
                if board is not None and board.signal is not None and now - self.last_change > MATCH_GRACE_S \
                        and now - board.signal_since > 0:
                    match = (board.signal == expected)
                gone = i in self.removed
                if gone:
                    r = {"mode": "OFF", "next": None, "dm": 0}
                path = routing.path_of(res, i) if (r["mode"] in ("LEFT", "RIGHT") and not gone) else []
                meters = r["dm"] / 10.0
                if r["mode"] == "X" and not gone:          # vägen ut för den som står vid larmet (noden visar ändå X)
                    path, dm = routing.escape(self.topo, self.alarms, i, res)
                    meters = dm / 10.0
                nodes.append({
                    "id": i, "name": n["name"], "floor": n["floor"], "x": n["x"], "y": n["y"],
                    "exit_dir": n.get("exit_dir", "down"),
                    "mode": r["mode"], "next": r["next"], "meters": meters, "path": path,
                    "removed": gone,
                    "real": board is not None,
                    "real_signal": board.signal if board is not None else None,
                    "match": match,
                })
            return {
                "version": self.version,
                "alarms": sorted(self.alarms),
                "nodes": nodes,
                "links": sorted({tuple(sorted((a, b))) for a, b, _, _ in self.topo.edges
                                 if self.topo.nodes[a]["floor"] != self.topo.nodes[b]["floor"]}),   # trapphus mellan våningar
                "boards": [{"label": b.label, "node_id": b.node_id, "connected": b.connected,
                            "signal": b.signal} for b in self.boards],
                "events": list(self.events)[:60],
            }


# ---------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------
def make_handler(hub):
    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *a):
            pass

        def _send(self, code, body, ctype):
            if isinstance(body, str):
                body = body.encode()
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _file(self, path, ctype):
            try:
                with open(path, "rb") as f:
                    self._send(200, f.read(), ctype)
            except OSError:
                self._send(404, "saknas", "text/plain; charset=utf-8")

        def do_GET(self):
            if self.path in ("/", "/index.html"):
                self._file(os.path.join(ROOT, "sim", "web", "index.html"), "text/html; charset=utf-8")
            elif self.path == "/karta.png":
                ren = os.path.join(ROOT, "docs", "karta_ren.png")      # kartan utan trianglar och kryss
                self._file(ren if os.path.exists(ren) else os.path.join(ROOT, "docs", "karta.png"), "image/png")
            elif self.path == "/lamps.json":
                self._file(os.path.join(ROOT, "sim", "lamps.json"), "application/json")
            elif self.path == "/api/state":
                self._send(200, json.dumps(hub.snapshot()), "application/json")
            elif self.path == "/api/stream":
                self._stream()
            else:
                self._send(404, "saknas", "text/plain; charset=utf-8")

        def _stream(self):
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Connection", "close")
            self.end_headers()
            self.close_connection = True
            try:
                while True:
                    self.wfile.write(("data: " + json.dumps(hub.snapshot()) + "\n\n").encode())
                    self.wfile.flush()
                    with hub.cond:
                        hub.cond.wait(timeout=1.0)           # ny status direkt, annars en gång per sekund
            except (BrokenPipeError, ConnectionResetError, OSError):
                return

        def do_POST(self):
            try:
                n = int(self.headers.get("Content-Length", "0"))
                data = json.loads(self.rfile.read(n) or b"{}") if n else {}
            except (ValueError, OSError):
                return self._send(400, '{"error":"ogiltig JSON"}', "application/json")
            if self.path == "/api/click":
                nid = data.get("id")
                if not isinstance(nid, int):
                    return self._send(400, '{"error":"id saknas"}', "application/json")
                hub.click(nid)
                self._send(200, '{"ok":true}', "application/json")
            elif self.path in ("/api/remove", "/api/restore"):
                nid = data.get("id")
                if not isinstance(nid, int):
                    return self._send(400, '{"error":"id saknas"}', "application/json")
                ok = hub.remove(nid) if self.path == "/api/remove" else (hub.restore(nid) or True)
                self._send(200, json.dumps({"ok": bool(ok)}), "application/json")
            elif self.path == "/api/clear":
                hub.clear()
                self._send(200, '{"ok":true}', "application/json")
            else:
                self._send(404, '{"error":"saknas"}', "application/json")

    return Handler


class Server(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True


def build(args_ports, args_exec, topo_path=None):
    hub = Hub(routing.Topology(topo_path or os.path.join(ROOT, "topology.json")))
    for p in args_ports:
        hub.boards.append(SerialBoard(hub, p))
    for c in args_exec:
        hub.boards.append(ProcBoard(hub, c))
    return hub


def start(hub, host, port):
    threading.Thread(target=hub.expire_loop, daemon=True).start()
    for b in hub.boards:
        b.start()
    srv = Server((host, port), make_handler(hub))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def main():
    ap = argparse.ArgumentParser(description="resQ-simulator")
    ap.add_argument("--port", action="append", default=[], help="seriell port till ett kort, t.ex. COM3 eller /dev/ttyUSB0 (kan anges flera gånger)")
    ap.add_argument("--exec", action="append", default=[], help="kör en nod som datorprogram (test)")
    ap.add_argument("--http", type=int, default=8000, help="webbport (standard 8000)")
    ap.add_argument("--host", default="127.0.0.1", help="adress att lyssna på (standard bara den här datorn)")
    a = ap.parse_args()

    if "auto" in a.port:                                  # hitta ESP32-kort själv (vanliga USB-chip: CP210x, CH340, FTDI, Espressif)
        a.port = [x for x in a.port if x != "auto"]
        try:
            from serial.tools import list_ports
            found = [p.device for p in list_ports.comports()
                     if p.vid in (0x10C4, 0x1A86, 0x0403, 0x303A) and p.device not in a.port]
        except ImportError:
            sys.exit("--port auto kräver pyserial: pip install pyserial")
        if not found:
            print("Hittade inget ESP32-kort på USB. Sitter sladden i? (Prova annars --port <port> för hand.)")
        else:
            print("Hittade kort på:", ", ".join(found))
        a.port += found

    hub = build(a.port, a.exec)
    if not a.port and not a.exec:
        print("Inget kort anslutet: alla noder är virtuella (bara simulering).")
        try:
            from serial.tools import list_ports
            ports = [p.device for p in list_ports.comports()]
            if ports:
                print("Hittade serieportar:", ", ".join(ports), " (koppla med --port <port>)")
        except ImportError:
            print("Vill du koppla ett riktigt kort? pip install pyserial, och kör sedan med --port <port>")
    start(hub, a.host, a.http)
    print(f"Öppna http://{a.host}:{a.http}   (Ctrl+C avslutar)")
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
