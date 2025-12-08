# Agent (UART ↔ MQTT Bridge)

Serial-to-MQTT bridge for the Whac-A-Mole board. Reads JSON lines from the device over UART and publishes them to MQTT topics used by the cloud backend, and forwards MQTT commands/config back to the device over UART.

## Installation

### Requirements
- Python >= 3.12

### Using uv
```bash
uv sync && . ./.venv/bin/activate
```

### Using pip
```bash
python3 -m venv venv
. venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install .        # or `pip install -e .` for development
```

## Files
```
.
├── config
│   └── logging.json                      # Config for console logging (stdout/stderr)
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

### Integration (no board, UART simulated)
Use socat to create paired PTYs:
```bash
socat -d -d PTY,raw,echo=0 PTY,raw,echo=0
# note the two PTYs (e.g., /dev/pts/6 and /dev/pts/7)
```
- Broker: `mosquitto -v`
- Cloud: `cd cloud && . venv/bin/activate && python mqtt_worker.py`
- Bridge: `cd agent && . venv/bin/activate && python -m agent.bridge -s /dev/pts/6 --device-id devsim`
- Inject firmware JSON on the other PTY:
```bash
printf '{"type":"game_event","pop":3,"level":1,"outcome":"HIT","reaction_ms":120,"lives_left":4,"ts":1717}\n' > /dev/pts/7
printf '{"type":"status","state":"playing","level":1,"pop_index":7,"lives_left":4,"ts":1718}\n' > /dev/pts/7
```
- Watch MQTT: `mosquitto_sub -t "whac/devsim/#" -v`
- Send command round-trip: `mosquitto_pub -t "whac/devsim/commands" -m '{"command":"pause"}' -q 1`

## End-to-end (with board)
1. Start MQTT broker (`mosquitto -v` or `docker run -p 1883:1883 eclipse-mosquitto`).
2. Start cloud worker: `python cloud/mqtt_worker.py` (from repo root).
3. (Optional) Start leaderboard UI: `uvicorn cloud.app:app --host 0.0.0.0 --port 8000 --reload`.
4. Flash/run firmware.
5. Run the bridge (command above). It will:
   - UART → MQTT: publish device JSON to `whac/<device_id>/game_events`, `/status`, `/telemetry/<sensor>`, `/events`, `/config_request` (based on `type`/`event_type`).
   - MQTT → UART: subscribe to `whac/<device_id>/commands` and forward JSON commands to the board (one line per command).

Example MQTT commands that propagate back to the board:
```bash
mosquitto_pub -t "whac/dev1/commands" -m '{"command":"pause"}' -q 1
mosquitto_pub -t "whac/dev1/commands" -m '{"command":"resume"}' -q 1
mosquitto_pub -t "whac/dev1/commands" -m '{"command":"set_pop_duration","value":900}' -q 1
mosquitto_pub -t "whac/dev1/commands" -m '{"config":{"pause":true,"set_pop_duration":900,"set_lives":6}}' -q 1 -r
```
