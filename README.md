# Distributed Evacuation System – ESP32

A distributed wireless evacuation guidance system built using ESP32-WROOM-32, ESP-NOW, and Python.

The system consists of up to 18 ESP32 nodes that communicate directly without requiring a Wi-Fi router, internet connection, or central controller.

Each node can independently detect alarms, communicate with other nodes, and calculate the fastest available evacuation route to the nearest exit using Dijkstra's algorithm.

The project also includes an interactive Python simulator with 2D and 3D building visualization, alarm propagation, route animation, and support for connecting physical ESP32 boards.


> This project is a prototype intended for development, experimentation, and educational purposes. It is not a certified fire alarm or life-safety system and must not replace approved evacuation equipment or emergency systems.

## Features

- Supports up to 18 ESP32-WROOM-32 nodes.
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

## Table of Contents

- [Quick Start](#quick-start)
- [Hardware](#hardware)
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

### Option A: Simulator only (no hardware needed)

You only need **Python 3** and a web browser.

1. Clone the repository and open a terminal in the project folder:

   ```bash
   git clone https://github.com/AnasDiasso/resq-plan.git
   cd resq-plan
   ```

2. Start the simulator:

   ```bash
   python simulator/server.py
   ```

   On Linux and macOS you may need to use `python3` instead of `python`.

3. Open <http://127.0.0.1:8000> in your browser.

4. Click a node on the map to trigger an alarm and watch the other nodes light the arrow toward the nearest exit. Drag nodes off the map to simulate blocked areas, and switch to the 3D view to see the floors stacked.

No packages need to be installed for the simulator. Only `pyserial` is optional, and only if you want to connect real boards.

### Option B: Real ESP32 boards

You need the hardware from the [Hardware](#hardware) section, [PlatformIO](https://platformio.org/install) (the VS Code extension or the command-line `pio`), and a USB data cable for each board.

1. **Wire each node** as described in [Wiring](#wiring).

2. **Create your configuration.** From the project folder, run:

   ```bash
   python tools/setup.py
   ```

   The script asks for (or sets) `NODE_ID`, `ESPNOW_CHANNEL` and `GROUP_KEY` and writes them to `.env`.

3. **Build and upload to the first board.** Connect the board over USB, then run:

   ```bash
   pio run --target upload
   ```

   `include/secrets.h` is generated from `.env` as part of the build. If it is missing, run `python tools/generate_secrets.py` manually.

4. **Repeat for every other board.** Each board needs its own `NODE_ID` (1, 2, 3, …) and every board must use the same `GROUP_KEY` and `ESPNOW_CHANNEL`. See [Flashing multiple nodes](#flashing-multiple-nodes).

5. **Test it.** Power the boards, press the button on one node, and its red X should light. The other nodes should light the arrow toward the nearest exit. Use `pio device monitor` to watch a board's serial output.

6. **Optional: link the boards to the simulator.** Connect a board over USB and run:

   ```bash
   python simulator/server.py --port auto
   ```

   See [Physical Hardware Integration](#physical-hardware-integration).

## Hardware

Each node consists of:

- ESP32-WROOM-32 development board.
- One momentary push button.
- One red LED for the alarm indicator.
- One green LED for LEFT direction.
- One yellow LED for RIGHT direction.
- Three current-limiting resistors (220–330 Ω).

### Wiring

| Component         | ESP32 GPIO | Connection                     |
| ----------------- | ---------- | ------------------------------ |
| Alarm button      | GPIO4      | Button between GPIO4 and GND   |
| Red X             | GPIO2      | LED through 220–330 Ω resistor |
| Green LEFT arrow  | GPIO23     | LED through 220–330 Ω resistor |
| Yellow RIGHT arrow| GPIO22     | LED through 220–330 Ω resistor |

The button uses the internal pull-up resistor:

```cpp
pinMode(4, INPUT_PULLUP);
```

### Indicator States

| Indicator    | Meaning                                  |
| ------------ | ---------------------------------------- |
| Red X        | This node has triggered an alarm         |
| Green LEFT   | Evacuation direction is left             |
| Yellow RIGHT | Evacuation direction is right            |
| All LEDs off | No available route or no active indication |

## System Architecture

The system consists of three main components:

1. **ESP32 nodes** – Handle button input, LED control, wireless communication, and local route calculations.
2. **Building topology** – Defines nodes, connections, distances, exits, and directional indicators.
3. **Python simulator** – Visualizes the building, simulates network behavior, and optionally communicates with physical ESP32 boards.

Every ESP32 independently calculates its evacuation route. There is no central controller responsible for routing decisions.

## Communication Protocol

Nodes communicate using ESP-NOW broadcast on a shared Wi-Fi channel. No access point or router is required.

### Message Authentication

Messages are authenticated using HMAC-SHA256 and a shared group key.

The message data includes:

- Node ID.
- Message type.
- Random nonce.
- Authentication signature.

### Alarm Transmission

The communication protocol includes:

- Three transmissions of each alarm message.
- Repeated alarm announcements every 10 seconds.
- Two transmissions when an alarm is cancelled.
- Authentication of incoming messages.
- Replay protection.
- Rejection of messages with invalid authentication.

Messages must pass authentication and replay checks before being accepted.

## Evacuation Routing

Each node independently calculates the fastest available route to the nearest exit using Dijkstra's shortest-path algorithm.

Nodes currently in an alarm state are excluded from route calculations.

### Routing Rules

1. The node that triggers an alarm displays a red X.
2. All other nodes calculate the fastest available route to an exit.
3. The appropriate directional arrow is illuminated.
4. If no valid route exists, all indicators remain off.

Distances are based on the building topology rather than straight-line measurements.

## Building Topology

The building layout is defined in `topology.json`. The topology contains 16 nodes and supports the distributed routing system. All distances are estimated and specified in decimeters.

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

### Directional Lamp Extraction

Lamp positions are extracted from orange triangles in the original building map.

```bash
python tools/extract_lamps.py
```

The extraction rules are:

- Left-pointing orange triangle = LEFT / Green.
- Right-pointing orange triangle = RIGHT / Yellow.

The simulator uses a clean version of the map without directional triangles. Generate it using:

```bash
python tools/make_clean_map.py
```

## Project Structure

```text
project/
│
├── platformio.ini
├── topology.json
├── README.md
│
├── .env
│
├── src/
│   └── main.cpp
│
├── include/
│   └── secrets.h
│
├── tools/
│   ├── setup.py
│   ├── extract_lamps.py
│   ├── make_clean_map.py
│   └── generate_secrets.py
│
├── simulator/
│   ├── server.py
│   ├── simulator.py
│   └── ...
│
├── tests/
│   ├── test_routing.py
│   ├── test_protocol.py
│   ├── test_network.py
│   ├── test_simulator.py
│   └── test_serial.py
│
└── assets/
    ├── original_map.png
    └── clean_map.png
```

> **Note:** The structure above describes the intended organization. Adjust filenames to match the actual repository.

## Installation

### Requirements

- Python 3.
- PlatformIO.
- Visual Studio Code or another compatible development environment.
- ESP32-WROOM-32 development boards.
- USB cables for programming.
- Optional: `pyserial` for physical hardware integration.

### 1. Clone the Repository

```bash
git clone https://github.com/AnasDiasso/resq-plan.git
cd resq-plan
```

### 2. Create Configuration

```bash
python tools/setup.py
```

This creates the `.env` configuration file. Example:

```env
NODE_ID=1
ESPNOW_CHANNEL=6
GROUP_KEY=your-secret-group-key
```

Each ESP32 must have a unique `NODE_ID`. All nodes in the same network must use the same group key and compatible ESP-NOW channel settings.

### 3. Generate Secrets

Generate the firmware configuration header:

```bash
python tools/generate_secrets.py
```

This creates `include/secrets.h`, which contains the configuration values required by the firmware.

> [!IMPORTANT]
> Never commit `.env` or `secrets.h` to a public repository.

### 4. Install Optional Python Dependencies

For physical serial communication:

```bash
pip install pyserial
```

The simulator is designed to use the Python standard library wherever possible.

## ESP32 Firmware

Compile:

```bash
pio run
```

Upload:

```bash
pio run --target upload
```

Serial monitor:

```bash
pio device monitor
```

Each physical board must be configured with its own unique node ID before compilation.

### Flashing multiple nodes

The node ID is compiled into the firmware, so each board is flashed separately:

1. Connect **one** board over USB.
2. Set that board's number in `.env` (`NODE_ID=1`), or run `python tools/setup.py` again.
3. Run `pio run --target upload`.
4. Label the board with its node number so it ends up in the right place in the building.
5. Unplug it, increment `NODE_ID`, and repeat with the next board.

Keep `GROUP_KEY` and `ESPNOW_CHANNEL` identical for all boards. Only `NODE_ID` changes.

### Common upload problems

- **Port not found or permission denied (Linux):** add your user to the `dialout` group (`sudo usermod -aG dialout $USER`), then log out and back in.
- **Port not found (Windows/macOS):** install the USB driver for your board's chip (CP210x or CH340) and use a cable that carries data, not just power.
- **Upload hangs on "Connecting...":** hold the **BOOT** button on the ESP32 while the upload starts, then release it.

## Python Simulator

The simulator provides an interactive environment for testing the evacuation system without requiring physical ESP32 hardware.

Start the simulator:

```bash
python simulator/server.py
```

Open the following address in your browser: <http://127.0.0.1:8000>

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

The simulator can communicate with physical ESP32 boards through serial connections. Communication uses an event-based serial protocol with `EVT` lines.

### Connect a Specific Board

Windows:

```bash
python simulator/server.py --port COM3
```

Linux:

```bash
python simulator/server.py --port /dev/ttyUSB0
```

### Automatic Port Detection

```bash
python simulator/server.py --port auto
```

### Connection Status

The simulator uses colored rings to identify physical boards:

| Ring Color | Meaning                         |
| ---------- | ------------------------------- |
| Blue       | Board detected                  |
| Green      | Board successfully matched      |
| Red        | Communication error or mismatch |

This allows physical hardware behavior to be compared with the simulated network.

## Testing

The project includes automated tests for the firmware, communication protocol, routing algorithms, and simulator.

- **C++ and Python reference tests** – The C++ implementation is compared against a Python reference implementation to verify consistent behavior.
- **Simulated network tests** – A simulated 16-node network is used to test packet loss, incorrect authentication keys, replay attempts, alarm propagation, alarm cancellation, and route recalculation.
- **Simulator tests** – End-to-end tests verify the simulator's functionality and interaction with the underlying system.
- **Serial communication tests** – Tests verify communication between the simulator and physical ESP32 boards.

### Run Tests

For a pytest-based setup:

```bash
python -m pytest tests/ -v
```

If the project uses Python's standard-library test runner instead:

```bash
python -m unittest discover -s tests -v
```

## Security

Security is an important part of the communication architecture. The system uses HMAC-SHA256 to authenticate messages using a shared group key.

Important security considerations:

- Use a sufficiently strong, randomly generated group key.
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
| ESP32 does not compile        | Missing dependencies            | Check PlatformIO configuration            |
| `secrets.h` is missing        | Configuration not generated     | Run `generate_secrets.py`                 |
| Nodes cannot communicate      | Different ESP-NOW channels      | Check `ESPNOW_CHANNEL`                    |
| Messages are rejected         | Incorrect group key             | Check `.env`                              |
| Incorrect node identification | Incorrect node ID               | Verify `NODE_ID`                          |
| Incorrect evacuation route    | Incorrect topology              | Inspect `topology.json`                   |
| Wrong directional arrow       | Incorrect lamp extraction       | Run `extract_lamps.py`                    |
| Simulator does not start      | Python environment issue        | Check dependencies                        |
| Serial port not found         | Incorrect port                  | Check USB connection and port name        |
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