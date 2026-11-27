# Distributed Evacuation System – ESP32

A distributed wireless evacuation guidance system built using ESP32-WROOM-32, ESP-NOW, and Python.

The system consists of ESP32 nodes (18 in the current building map) that communicate directly without requiring a Wi-Fi router, internet connection, or central controller.

Each node can independently detect alarms, communicate with other nodes, and calculate the fastest available evacuation route to the nearest exit using Dijkstra's algorithm.

The project also includes an interactive Python simulator with 2D and 3D building visualization, alarm propagation, route animation, and support for connecting physical ESP32 boards.


> This project is a prototype intended for development, experimentation, and educational purposes. It is not a certified fire alarm or life-safety system and must not replace approved evacuation equipment or emergency systems.

## Features

- 18 nodes in the current topology. The firmware accepts up to 32.
- Wireless communication using ESP-NOW broadcast.
- No Wi-Fi router or internet connection required.
- HMAC-SHA256 message authentication.
- Replay protection and invalid-message rejection.
- Distributed alarm handling without a central controller.
- Independent route calculation on every node.
- Dijkstra-based shortest-path routing.
- Automatic route recalculation when nodes enter an alarm state.
- Python-based interactive simulator.
- 2D and 3D building visualization.
- Animated alarm propagation and evacuation routes.
- Simulation of unavailable or disconnected nodes.
- Serial communication with physical ESP32 boards.
- Automated firmware, network, and simulator tests.
- Optional presence detection with a 24 GHz mmWave radar sensor.
- Bidirectional people counter with two laser beams (in development).

## Table of Contents

- [Quick Start](#quick-start)
- [Windows](#windows)
- [Hardware](#hardware)
- [Sensors](#sensors)
- [System Architecture](#system-architecture)
- [Communication Protocol](#communication-protocol)
- [Evacuation Routing](#evacuation-routing)
- [Building Topology](#building-topology)
- [Project Structure](#project-structure)
- [Installation](#installation)
- [ESP32 Firmware](#esp32-firmware)
- [Python Simulator](#python-simulator)
- [Physical Hardware Integration](#physical-hardware-integration)
- [Testing](#testing)
- [Security](#security)
- [Troubleshooting](#troubleshooting)
- [Limitations](#limitations)
- [Future Development](#future-development)
- [License](#license)
- [Technology Stack](#technology-stack)

## Quick Start

There are two ways to run the project. You can start with the simulator, which needs no hardware, and add real boards later.

The commands below use `python3` (Linux and macOS). **On Windows, type `python` instead of `python3`.** See [Windows](#windows) for the other differences.

### Option A: Simulator only (no hardware needed)

You only need **Python 3.9 or newer** and a web browser.

1. Clone the repository and open a terminal in the project folder:

   ```bash
   git clone https://github.com/AnasDiasso/resq-plan.git
   cd resq-plan
   ```

2. Start the simulator:

   ```bash
   python3 sim/server.py
   ```

3. Open <http://127.0.0.1:8000> in your browser.

4. Click a node on the map to trigger an alarm and watch the other nodes light the arrow toward the nearest exit. Drag nodes off the map to simulate blocked areas, and switch to the 3D view to see the floors stacked.

No packages need to be installed for the simulator. Only `pyserial` is optional, and only if you want to connect real boards.

### Option B: Real ESP32 boards

You need the hardware from the [Hardware](#hardware) section, [PlatformIO](https://platformio.org/install) (the VS Code extension or the command-line `pio`), and a USB data cable for each board.

1. **Wire each node** as described in [Wiring](#wiring).

2. **Create your configuration.** From the project folder, run the following, replacing `1` with the board's node number:

   ```bash
   python3 tools/setup.py 1
   ```

   The script writes `NODE_ID`, `ESPNOW_CHANNEL` and `GROUP_KEY` to `.env`. The first time, it creates a random `GROUP_KEY`. Leave out the number and it asks for one.

3. **Build and upload to the first board.** Connect the board over USB, then run:

   ```bash
   pio run --target upload
   ```

   Or click **Upload** (the arrow) in the PlatformIO toolbar in VS Code. The build generates `include/secrets.h` from `.env` and `include/topology.h` from `topology.json` automatically.

4. **Repeat for every other board.** Run `tools/setup.py` again with the next node number and upload. The script keeps the same `GROUP_KEY` and `ESPNOW_CHANNEL`, so all boards match. See [Flashing multiple nodes](#flashing-multiple-nodes).

5. **Test it.** Power the boards, press the button on one node, and its red X should light. The other nodes should light the arrow toward the nearest exit. Use `pio device monitor` to watch a board's serial output.

6. **Optional: link the boards to the simulator.** Connect a board over USB and run:

   ```bash
   pip install pyserial
   python3 sim/server.py --port auto
   ```

   See [Physical Hardware Integration](#physical-hardware-integration).

## Windows

Everything except the C++ host tests works directly on Windows. The steps are the same as in [Quick Start](#quick-start), with the differences below.

### 1. Install the tools

- **Python 3.9 or newer** from [python.org](https://www.python.org/downloads/windows/). In the installer, tick **Add python.exe to PATH** before clicking **Install Now**.
- **Git** from [git-scm.com](https://git-scm.com/download/win). The default options are fine.
- **VS Code** with the **PlatformIO IDE** extension, if you will flash boards. Restart VS Code after installing it. The first start takes a few minutes.
- **USB driver** for your board's USB chip: [CP210x](https://www.silabs.com/developers/usb-to-uart-bridge-vcp-drivers) or [CH340](https://www.wch-ic.com/downloads/CH341SER_EXE.html). The chip name is printed on the board, next to the USB connector.

Check the install in a new terminal:

```powershell
python --version
git --version
```

If `python` opens the Microsoft Store instead, open **Settings → Apps → Advanced app settings → App execution aliases**, turn off the two `python` aliases, and open a new terminal. You can also use the launcher `py` instead of `python`.

### 2. Use `python`, not `python3`

Run every Python command in this README with `python` (or `py`):

```powershell
python sim\server.py
python tools\setup.py 1
pip install pyserial
```

Forward slashes (`sim/server.py`) also work in PowerShell and Command Prompt.

### 3. Create `.env` by hand (optional)

`python tools\setup.py` is the easiest way. To copy the template instead:

```powershell
# PowerShell
Copy-Item .env.example .env
```

```bat
:: Command Prompt
copy .env.example .env
```

Then open `.env` in VS Code and fill it in. Create a group key with:

```powershell
python -c "import secrets; print(secrets.token_hex(16))"
```

### 4. Run `pio` from the PlatformIO terminal

The PlatformIO extension does not add `pio` to your normal terminal. Either:

- Click the PlatformIO icon (the ant) in the VS Code sidebar, then **Miscellaneous → New Terminal**. `pio` works in that terminal.
- Or skip the command line and use the **Build** (✓), **Upload** (→) and **Serial Monitor** (plug) buttons in the blue status bar at the bottom of VS Code.

### 5. Find the board's COM port

1. Connect the board over USB.
2. Open **Device Manager** (right-click the Start button).
3. Expand **Ports (COM & LPT)**. The board shows up as `Silicon Labs CP210x ... (COM3)` or `USB-SERIAL CH340 (COM5)`.

Use that name with the simulator:

```powershell
python sim\server.py --port COM3
```

If the board does not appear, or appears under **Other devices** with a yellow warning sign, install the USB driver from step 1 and try another cable. Some cables only carry power.

Only one program can use a COM port at a time. Close the PlatformIO Serial Monitor before you start the simulator with `--port`, and stop the simulator before you upload new firmware.

### 6. Tests on Windows

The simulator and the firmware build run on Windows, but the automated tests do not run natively:

- `host_test/run_sim.sh` and the node program used by `sim/test_sim.py` need `sh`, `g++` and OpenSSL.
- `sim/test_serial.py` uses a virtual serial port (`pty`), which exists only on Linux and macOS.

To run them on Windows, use [WSL](https://learn.microsoft.com/windows/wsl/install) (Windows Subsystem for Linux):

```powershell
wsl --install
```

Restart, open **Ubuntu** from the Start menu, and run:

```bash
sudo apt update
sudo apt install -y python3 python3-pip g++ libssl-dev
cd /mnt/c/Users/<your-name>/path/to/resq-plan
pip install pyserial
sh host_test/run_sim.sh
python3 sim/test_sim.py
```

You do not have to run the tests locally. GitHub runs all of them automatically on every pull request (see [Testing](#testing)).

## Hardware

Each node consists of:

- ESP32-WROOM-32 development board.
- One momentary push button.
- One red LED for the alarm indicator.
- One green LED for LEFT direction.
- One yellow LED for RIGHT direction.
- Three current-limiting resistors (220–330 Ω).
- Optional: HMMD 24 GHz mmWave radar sensor for presence detection.
- Optional: two laser beams (laser + receiver each) for the people counter.

### Wiring

| Component         | ESP32 GPIO | Connection                     |
| ----------------- | ---------- | ------------------------------ |
| Alarm button      | GPIO4      | Button between GPIO4 and GND   |
| Red X             | GPIO2      | LED through 220–330 Ω resistor |
| Green LEFT arrow  | GPIO23     | LED through 220–330 Ω resistor |
| Yellow RIGHT arrow| GPIO22     | LED through 220–330 Ω resistor |
| mmWave sensor TX  | GPIO16     | Sensor TX to ESP32 RX (UART2)  |
| mmWave sensor RX  | GPIO17     | Sensor RX to ESP32 TX (UART2)  |
| mmWave sensor 3V3 | 3V3        | Power                          |
| mmWave sensor GND | GND        | Ground                         |
| Laser beam 1      | TODO       | Not connected in the firmware yet |
| Laser beam 2      | TODO       | Not connected in the firmware yet |

Each LED is wired GPIO → resistor → LED long leg → LED short leg → GND. The button uses the internal pull-up resistor:

```cpp
pinMode(4, INPUT_PULLUP);
```

The pins are defined in [src/led_guidance.cpp](src/led_guidance.cpp) and [src/node_controller.cpp](src/node_controller.cpp). [docs/lampor_per_nod.md](docs/lampor_per_nod.md) lists which arrow points where on every node.

### Indicator States

| Indicator    | Meaning                                  |
| ------------ | ---------------------------------------- |
| Red X        | This node, or another node in the same stairwell, has an alarm |
| Green LEFT   | Evacuation direction is left             |
| Yellow RIGHT | Evacuation direction is right            |
| All LEDs off | No available route or no active indication |

## Sensors

Both sensors are optional and work independently of the alarm and routing system.

### mmWave Presence Detection

An HMMD 24 GHz mmWave radar detects whether someone is moving near the node. The code is in [src/mmwave_presence.cpp](src/mmwave_presence.cpp), and the wiring is in [Wiring](#wiring).

How it works:

- The sensor reports signal energy in 16 zones of 70 cm each, up to 11.2 m. The first zone (0–70 cm) is always noisy and is skipped.
- For the first 3 seconds after start, the node learns the normal noise level in each zone. Keep the area in front of the sensor empty during this time if possible.
- Movement is detected when the energy in a zone rises clearly above its normal level.
- Presence is held for 5 seconds after the last movement.
- The normal level keeps adapting over time, so a permanent change in the background (for example a fan) stops counting as presence after a few minutes.

The node prints the status to the serial monitor whenever it changes:

```text
HMMD mmWave startad
Räknar rörelse upp till 1120 cm
NARVARO
INGEN NARVARO
```

Sensitivity and range are set at the top of `mmwave_presence.cpp` (`SENSITIVITY_FACTOR`, `SENSITIVITY_MARGIN`, `MAX_DISTANCE_CM`, `HOLD_MS`).

The presence status is not yet used by the alarm or the LEDs.

### People Counter

> **In development.** The counting logic is implemented, but it is not yet connected to any pins or called from `main.cpp`.

Two laser beams across a doorway count how many people go in and out. The code is in [src/people_counter.cpp](src/people_counter.cpp).

Mount beam 1 on the outside and beam 2 on the inside of the doorway, a short distance apart, so that a person blocks them one after the other.

| Order the beams are blocked | Counted as |
| --------------------------- | ---------- |
| Beam 1, then beam 2         | One person in  |
| Beam 2, then beam 1         | One person out |

- A crossing must be finished within 3 seconds, otherwise it is discarded.
- A person who blocks one beam and turns back is not counted.
- Unclear patterns, such as both beams blocked at the same moment from idle, are discarded and the counter waits until both beams are clear.
- The current occupancy never goes below zero.

Usage:

```cpp
PeopleCounter counter;                    // optional timeout in ms, default 3000
counter.update(beam1Blocked, beam2Blocked, millis());   // call often, e.g. in loop()
counter.getTotalEntered();
counter.getTotalExited();
counter.getCurrentOccupancy();
counter.reset();
```

## System Architecture

The system consists of three main components:

1. **ESP32 nodes** – Handle button input, LED control, wireless communication, and local route calculations.
2. **Building topology** – Defines nodes, connections, distances, exits, and directional indicators.
3. **Python simulator** – Visualizes the building, simulates network behavior, and optionally communicates with physical ESP32 boards.

Every ESP32 independently calculates its evacuation route. There is no central controller responsible for routing decisions.

## Communication Protocol

Nodes communicate using ESP-NOW broadcast on a shared Wi-Fi channel. No access point or router is required.

### Message Authentication

Messages are authenticated using HMAC-SHA256 and a shared group key. Each packet is 14 bytes and contains:

- Message type (alarm or cancel).
- Sender node ID.
- Random nonce.
- Authentication tag (the first 8 bytes of the HMAC-SHA256).

### Alarm Transmission

The communication protocol includes:

- Three transmissions of each message, to tolerate packet loss.
- Repeated alarm announcements every 10 seconds while the alarm is active.
- An alarm that lasts 5 minutes unless it is cancelled.
- A second cancel message 2 seconds after the first.
- Authentication of incoming messages.
- Replay protection.
- Rejection of messages with invalid authentication.

Messages must pass authentication and replay checks before being accepted.

## Evacuation Routing

Each node independently calculates the fastest available route to the nearest exit using Dijkstra's shortest-path algorithm.

Nodes currently in an alarm state are excluded from route calculations. If a node belongs to a `zone` in `topology.json`, an alarm closes every node in that zone.

### Routing Rules

1. The node that triggers an alarm displays a red X. If it is in a stairwell, every node in that stairwell displays a red X.
2. All other nodes calculate the fastest available route to an exit.
3. The appropriate directional arrow is illuminated.
4. If no valid route exists, all indicators remain off.

Distances are based on the building topology rather than straight-line measurements.

## Building Topology

The building layout is defined in [topology.json](topology.json). It contains 18 nodes. Distances are estimated from the map image and given in meters. The firmware converts them to decimeters.

`topology.json` is the source. The build turns it into `include/topology.h`, so edit the JSON, never the header. After a change, every board must be flashed again.

### Exits

There are two exits:

| Node | Location               |
| ---- | ---------------------- |
| 1    | Ground-floor entrance  |
| 4    | Ground-floor entrance  |

### Stairwells

The stairwell connections are:

```text
3 → 2 → 1
6 → 5 → 4
```

### Corridor Connections

```text
3 ↔ 7
6 ↔ 13
```

The two southern rooms on floor 3 each have a door with a node on either side: 15 ↔ 17 (door at x ≈ 704) and 16 ↔ 18 (door at x ≈ 914). People in those rooms go through the door to 17 or 18 and on to the corridor at 11 or 12, instead of straight through the wall.

### Directional Lamp Extraction

Lamp positions are extracted from orange triangles in the original building map ([docs/karta.png](docs/karta.png)). This tool needs extra packages that the simulator does not:

```bash
pip install numpy scipy Pillow
python3 tools/extract_lamps.py
```

It writes `sim/lamps.json`, updates the `lamp` fields in `topology.json`, and regenerates `docs/lampor_per_nod.md`.

> [!WARNING]
> Nodes 15–18 are set by hand: 15 and 16 were moved, and 17 and 18 have no triangles in `docs/karta.png`. Running `tools/extract_lamps.py` overwrites their entries in `sim/lamps.json` and their `lamp` fields in `topology.json`. Back up both files first, or restore nodes 15–18 by hand afterwards.

The extraction rules are:

- On each node, the triangle furthest to the left is LEFT / Green, the other is RIGHT / Yellow.
- For each path out of a node, the triangle pointing most closely along that path is chosen.

The simulator uses a clean version of the map without directional triangles ([docs/karta_ren.png](docs/karta_ren.png)). Regenerate it after replacing the map:

```bash
pip install opencv-python numpy scipy
python3 tools/make_clean_map.py
```

## Project Structure

```text
resq-plan/
│
├── platformio.ini          # ESP32 build settings
├── topology.json           # Building map: nodes, edges, exits, lamps
├── .env.example            # Template for .env (copy, never commit .env)
├── README.md
├── CONTRIBUTING.md
│
├── src/                    # ESP32 firmware
│   ├── main.cpp
│   ├── node_controller.*   # Button, alarm state, serial events
│   ├── route.*             # Dijkstra routing
│   ├── led_guidance.*      # LED output
│   ├── protocol.*          # Packet format, HMAC, replay protection
│   ├── radio.h, radio_espnow.*
│   ├── crypto_esp.cpp
│   ├── mmwave_presence.*   # mmWave presence detection
│   └── people_counter.*    # Laser-beam people counter
│
├── include/                # Generated at build time (secrets.h, topology.h)
│
├── scripts/                # PlatformIO pre-build scripts
│   ├── load_env.py         # .env → include/secrets.h
│   └── gen_topology.py     # topology.json → include/topology.h
│
├── tools/
│   ├── setup.py            # Creates .env for a board
│   ├── extract_lamps.py
│   ├── make_clean_map.py
│   ├── make_topology.py
│   └── render_map.py
│
├── sim/                    # Python simulator
│   ├── server.py
│   ├── routing.py
│   ├── lamps.json
│   ├── web/index.html
│   ├── requirements.txt
│   ├── test_sim.py
│   └── test_serial.py
│
├── host_test/              # Firmware compiled and tested on a computer
│   ├── run_sim.sh
│   ├── compare.py
│   ├── build_node_host.sh
│   └── ...
│
└── docs/
    ├── karta.png           # Original map
    ├── karta_ren.png       # Map without triangles (used by the simulator)
    ├── lampor_per_nod.md
    └── scenarier/
```

## Installation

### Requirements

- Python 3.9 or newer.
- PlatformIO.
- Visual Studio Code or another compatible development environment.
- ESP32-WROOM-32 development boards.
- USB cables for programming.
- Optional: `pyserial` for physical hardware integration.

On Windows, see [Windows](#windows) first.

### 1. Clone the Repository

```bash
git clone https://github.com/AnasDiasso/resq-plan.git
cd resq-plan
```

### 2. Create Configuration

```bash
python3 tools/setup.py 1
```

This creates the `.env` configuration file. Example:

```env
NODE_ID=1
ESPNOW_CHANNEL=1
GROUP_KEY=0123456789abcdef0123456789abcdef
```

- `NODE_ID` must exist in `topology.json` (1–18) and be unique for each board.
- `ESPNOW_CHANNEL` is 1–13 and must be the same on all boards.
- `GROUP_KEY` is 32 hex characters and must be the same on all boards. Never use the example above.

To change the channel, run `python3 tools/setup.py 1 --kanal 6`.

You can also copy `.env.example` to `.env` and fill it in by hand.

### 3. Secrets Header

You do not need to create `include/secrets.h` yourself. `scripts/load_env.py` runs before every build, checks `.env`, and writes the header. If a value is missing or invalid, the build stops with a message saying what to fix.

To generate it by hand:

```bash
python3 scripts/load_env.py
```

> [!IMPORTANT]
> Never commit `.env` or `include/secrets.h`. Both are listed in `.gitignore`, and CI fails if either is tracked. See [CONTRIBUTING.md](CONTRIBUTING.md#keeping-secrets-out-of-git).

### 4. Install Optional Python Dependencies

For physical serial communication:

```bash
pip install -r sim/requirements.txt
```

The simulator itself uses only the Python standard library.

## ESP32 Firmware

Compile:

```bash
pio run
```

Upload:

```bash
pio run --target upload
```

Serial monitor (115200 baud):

```bash
pio device monitor
```

On Windows, run these in the PlatformIO terminal or use the status-bar buttons. See [Windows](#4-run-pio-from-the-platformio-terminal).

Each physical board must be configured with its own unique node ID before compilation.

### Flashing multiple nodes

The node ID is compiled into the firmware, so each board is flashed separately:

1. Connect **one** board over USB.
2. Run `python3 tools/setup.py <node-number>`.
3. Run `pio run --target upload`, or click **Upload**.
4. Label the board with its node number so it ends up in the right place in the building.
5. Unplug it and repeat with the next board and node number.

`tools/setup.py` keeps `GROUP_KEY` and `ESPNOW_CHANNEL` from the existing `.env`, so only `NODE_ID` changes.

### Common upload problems

- **Port not found or permission denied (Linux):** add your user to the `dialout` group (`sudo usermod -aG dialout $USER`), then log out and back in.
- **Port not found (Windows/macOS):** install the USB driver for your board's chip (CP210x or CH340) and use a cable that carries data, not just power. On Windows, check **Device Manager → Ports (COM & LPT)**.
- **Port busy / access denied (Windows):** close the Serial Monitor and stop the simulator. Only one program can use a COM port.
- **Upload hangs on "Connecting...":** hold the **BOOT** button on the ESP32 while the upload starts, then release it.

## Python Simulator

The simulator provides an interactive environment for testing the evacuation system without requiring physical ESP32 hardware.

Start the simulator:

```bash
python3 sim/server.py
```

Open the following address in your browser: <http://127.0.0.1:8000>

Options:

| Option            | Meaning                                                |
| ----------------- | ------------------------------------------------------ |
| `--port <port>`   | Connect a board (`COM3`, `/dev/ttyUSB0` or `auto`). Can be repeated. |
| `--http <number>` | Web port (default 8000)                                |
| `--host <addr>`   | Address to listen on (default `127.0.0.1`, this computer only) |
| `--exec "<cmd>"`  | Run a node as a computer program (used by the tests)   |

### 2D Visualization

The 2D view displays the building layout and the current state of every node.

- Active directional indicators.
- Red alarm crosses.
- Grey inactive indicators.
- Animated alarm propagation.
- Pulsating alarm indicators.
- Animated route highlighting when hovering over a path.

### Interactive Node Removal

Nodes can be dragged away from the building map to simulate unavailable areas.

- Dragging nodes away from their original positions.
- Visualizing unavailable areas using two shades of grey.
- Double-clicking or dragging nodes back into position.
- A **Restore All** function to restore the complete map.

### 3D Visualization

The 3D view displays the building as vertically stacked floor planes.

- Adjustable viewing angle using a tilt slider.
- Dashed stairwell connections rendered behind the floor planes.
- Red glow effects on floors containing active alarms.
- Visualization of connections between different floors.

## Physical Hardware Integration

The simulator can communicate with physical ESP32 boards through serial connections (115200 baud). Communication uses an event-based serial protocol with `EVT` lines. It requires `pyserial`:

```bash
pip install pyserial
```

Close the PlatformIO Serial Monitor first. Only one program can use the port.

### Connect a Specific Board

Windows (find the number in Device Manager, see [Windows](#5-find-the-boards-com-port)):

```powershell
python sim\server.py --port COM3
```

Linux:

```bash
python3 sim/server.py --port /dev/ttyUSB0
```

macOS:

```bash
python3 sim/server.py --port /dev/cu.usbserial-0001
```

Several boards:

```bash
python3 sim/server.py --port COM3 --port COM5
```

Each connected board must have a different `NODE_ID`.

### Automatic Port Detection

```bash
python3 sim/server.py --port auto
```

This looks for common ESP32 USB chips (CP210x, CH340, FTDI, Espressif) on all operating systems.

### Connection Status

The simulator uses colored rings to identify physical boards:

| Ring Color | Meaning                         |
| ---------- | ------------------------------- |
| Blue       | Board detected                  |
| Green      | Board successfully matched      |
| Red        | Communication error or mismatch |

This allows physical hardware behavior to be compared with the simulated network.

## Testing

The project includes automated tests for the firmware, communication protocol, routing algorithms, and simulator. The tests compile the firmware C++ code for the computer, using fake Arduino functions from `host_test/fake/`.

| Test | Command | What it checks |
| ---- | ------- | -------------- |
| Protocol and network | `sh host_test/run_sim.sh` | C++ HMAC matches Python, and a simulated 18-node network handles packet loss, wrong keys, replay attempts, alarm propagation, cancellation and route recalculation. |
| Routing reference | `python3 host_test/compare.py` | C++ routing matches an independent Python Dijkstra for all single alarms, all pairs and random groups. |
| Simulator | `python3 sim/test_sim.py` | Simulator routing matches the firmware, and the full chain server ↔ node works over the serial protocol. |
| Serial | `python3 sim/test_serial.py` | The `pyserial` connection, using a virtual serial port instead of a real board. |

Requirements: Python 3, `g++`, OpenSSL development files (`libssl-dev` on Ubuntu, `brew install openssl` on macOS), and `pip install -r sim/requirements.txt`.

These tests run on Linux and macOS. On Windows, run them in WSL. See [Tests on Windows](#6-tests-on-windows).

GitHub Actions runs all of them, plus a firmware build and a check that no secret files are committed, on every pull request and every push to `main`. See [.github/workflows/ci.yml](.github/workflows/ci.yml).

## Security

Security is an important part of the communication architecture. The system uses HMAC-SHA256 to authenticate messages using a shared group key.

Important security considerations:

- Use a sufficiently strong, randomly generated group key. `tools/setup.py` creates one for you.
- Never expose secrets in public repositories.
- Validate incoming message lengths and formats.
- Verify message authentication before processing messages.
- Maintain replay-protection state.
- Generate unpredictable nonces.
- Handle duplicate messages safely.
- Prevent unauthorized alarm cancellation.

A shared group key also means that compromise of one node may compromise the authentication credentials of the entire network.

HMAC authentication does not provide encryption or guarantee message delivery.

## Troubleshooting

| Problem                       | Possible Cause                  | Suggested Solution                        |
| ----------------------------- | ------------------------------- | ----------------------------------------- |
| Build stops with `[load_env]` | `.env` missing or invalid       | Run `tools/setup.py` and read the message |
| ESP32 does not compile        | Missing dependencies            | Check PlatformIO configuration            |
| `secrets.h` is missing        | Configuration not generated     | Run `scripts/load_env.py`                 |
| Nodes cannot communicate      | Different ESP-NOW channels      | Check `ESPNOW_CHANNEL`                    |
| Messages are rejected         | Incorrect group key             | Check `.env`                              |
| Incorrect node identification | Incorrect node ID               | Verify `NODE_ID`                          |
| Incorrect evacuation route    | Incorrect topology              | Inspect `topology.json`                   |
| Wrong directional arrow       | Incorrect lamp extraction       | Run `tools/extract_lamps.py`              |
| Simulator does not start      | Python too old or port 8000 busy | Use Python 3.9+, or `--http 8080`        |
| `python` opens Microsoft Store (Windows) | App execution alias  | Turn off the alias, or use `py`           |
| `pio` is not recognized (Windows) | Not on PATH                 | Use the PlatformIO terminal               |
| Serial port not found         | Incorrect port or driver        | Check USB cable, driver and port name     |
| Access denied on COM port     | Port used by another program    | Close the Serial Monitor                  |
| Red connection ring           | Communication error or mismatch | Check node ID and serial events           |

## Limitations

The project is a prototype and has several limitations:

- Building distances are estimated.
- Wireless communication can be affected by interference and physical obstacles.
- ESP-NOW broadcast does not guarantee message delivery.
- Hardware failures may affect available evacuation routes.
- Incorrect topology data can produce incorrect route calculations.
- The simulator cannot reproduce all real-world building and emergency conditions.
- The system has not been certified for life-safety applications.

A real deployment would require extensive hardware validation, fault-tolerance testing, independent safety assessment, and applicable regulatory certification.

## Future Development

Potential improvements include:

- Automatic node discovery.
- Battery and power monitoring.
- Wireless signal-quality diagnostics.
- Improved handling of simultaneous alarms.
- More robust network recovery.
- Persistent alarm history and event logging.
- Support for larger and more complex buildings.
- Improved map calibration.
- Expanded hardware-in-the-loop testing.

## License

Specify the project license before public distribution.

If the project is open source, consider including an appropriate license file such as `LICENSE`.

## Technology Stack

| Component              | Technology         |
| ---------------------- | ------------------ |
| Microcontroller        | ESP32-WROOM-32     |
| Firmware               | C++ / Arduino      |
| Build system           | PlatformIO         |
| Wireless communication | ESP-NOW            |
| Authentication         | HMAC-SHA256        |
| Routing                | Dijkstra's algorithm |
| Simulator              | Python 3           |
| Serial communication   | PySerial (optional) |
| Building topology      | JSON               |

## Project Goal

Demonstrate a distributed evacuation guidance system in which every node can independently detect alarms, communicate with other nodes, and calculate evacuation routes without depending on a central controller.


## Author

Anas Diasso – [GitHub profile](https://github.com/AnasDiasso)

Kelly Li – [GitHub profile](https://github.com/kellywy)

MartinVasilevski – [GitHub profile](https://github.com/MartinVasilevski)

Sally Shir Ali – [GitHub profile](https://github.com/Sally-zsa)

Said Mousa Isman 