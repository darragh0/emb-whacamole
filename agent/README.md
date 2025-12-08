# Bridge (UART ↔ MQTT)

Serial-to-MQTT bridge for the Whac-A-Mole board. It reads JSON lines from the device over UART and publishes to MQTT topics used by the cloud backend, and forwards MQTT commands/config back to the device over UART.

## Installation

### Requirements

- Python >= 3.10

### Using uv

```bash
uv sync && . ./.venv/bin/activate
```

### Using pip

```bash
python3 -m venv venv
. venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install .        # or `pip install -e .` for development

# Now you should be able to run `agent` directly
```

## Files

```
.
├── config
│   └── logging.json                      # Config for console logging (stdout/stderr)
├── pyproject.toml
├── README.md
├── ruff.toml
└── src
    └── agent
         ├── argparser.py                  # CLI flags (serial, MQTT, device ID)
         ├── bridge.py                     # UART ↔ MQTT logic
         ├── test_bridge.py                # Mapping/command unit tests
         ├── __init__.py
         ├── logging_conf.py               # Logging config (for logging.json, can ignore this)
         └── __main__.py                   # Entry point (`python -m agent`)
```

## Usage

```bash
# Start the bridge (examples)
python -m agent.bridge --serial-port /dev/ttyACM0 --device-id dev1 --mqtt-host localhost --mqtt-port 1883
# or with defaults from env MQTT_BROKER / MQTT_PORT
agent -s /dev/ttyACM0 --device-id dev1
```

Supported flags:
- `-s/--serial-port` (required)
- `--baud` (default: 115200)
- `--device-id` (used to build `whac/<device_id>/…` topics)
- `--mqtt-host` (default: `MQTT_BROKER` env or `localhost`)
- `--mqtt-port` (default: `MQTT_PORT` env or `1883`)

## Testing

### Unit Tests

Run the bridge unit tests to verify message mapping and command handling:

```bash
cd agent
./venv/bin/python -m pytest src/agent/test_bridge.py -v
```

### Integration Testing (Without Physical Board)

Use the fake UART device simulator to test the full bridge flow:

**Terminal 1** - Start MQTT broker:
```bash
mosquitto -v
# or with Docker: docker run -p 1883:1883 eclipse-mosquitto
```

**Terminal 2** - Start cloud worker:
```bash
cd cloud
./venv/bin/python mqtt_worker.py
```

**Terminal 3** - Start fake UART device:
```bash
cd agent
python3 fake_uart_device.py
# Note the virtual serial port printed (e.g., /dev/pts/5)
```

**Terminal 4** - Start bridge with the virtual port:
```bash
cd agent
./venv/bin/python -m agent.bridge -s /dev/pts/5 --device-id test-dev
```

You should see:
- Fake device sending game events, status, and telemetry
- Bridge forwarding messages to MQTT topics
- Cloud worker receiving and storing events

**Terminal 5** - Send test commands:
```bash
# Pause the game
mosquitto_pub -t "whac/test-dev/commands" -m '{"command":"pause"}' -q 1

# Resume
mosquitto_pub -t "whac/test-dev/commands" -m '{"command":"resume"}' -q 1

# Set level
mosquitto_pub -t "whac/test-dev/commands" -m '{"command":"set_level","value":3}' -q 1
```

### Alternative: Test with Cloud Fake Device

Skip the UART simulation and test MQTT directly:

```bash
# Terminal 1: mosquitto -v
# Terminal 2: cd cloud && ./venv/bin/python mqtt_worker.py
# Terminal 3: cd cloud && python3 fake_device.py
```

## End-to-end pipeline (With Physical Board)

1. Start MQTT broker (e.g., `mosquitto` or `docker run -p 1883:1883 eclipse-mosquitto`).
2. Start cloud worker: `python cloud/mqtt_worker.py` (from repo root).
3. (Optional) Start leaderboard UI: `uvicorn cloud.app:app --host 0.0.0.0 --port 8000 --reload`.
4. Flash/run the firmware in `emb/` on the board.
5. Run the bridge (see command above). It will:
   - UART → MQTT: publish device JSON to `whac/<device_id>/game_events`, `/status`, `/telemetry/<sensor>`, `/events`, `/config_request` (depending on `type`/`event_type` fields).
   - MQTT → UART: subscribe to `whac/<device_id>/commands` and forward JSON commands to the board (one line per command).

Example MQTT commands that propagate back to the board (newline-terminated JSON on UART):
```bash
# Pause
mosquitto_pub -t "whac/dev1/commands" -m '{"command":"pause"}' -q 1
# Resume
mosquitto_pub -t "whac/dev1/commands" -m '{"command":"resume"}' -q 1
# Adjust pop duration mid-game
mosquitto_pub -t "whac/dev1/commands" -m '{"command":"set_pop_duration","value":900}' -q 1
# Using config payload (matches cloud/config.py):
mosquitto_pub -t "whac/dev1/commands" -m '{"config":{"pause":true,"set_pop_duration":900,"set_lives":6}}' -q 1 -r
```
