# End-to-End Test Guide

How to validate the path from device UART → MQTT → cloud (and commands back), with and without hardware.

## Prereqs
- MQTT broker (`mosquitto` installed; run `mosquitto -v`).
- Virtual envs for `cloud/` and `agent/`.
  - From repo root:
    ```bash
    cd cloud
    python -m venv venv && . venv/bin/activate
    pip install -r requirements.txt
    deactivate

    cd ../agent
    python -m venv venv && . venv/bin/activate
    pip install -e .
    deactivate
    ```
- For simulation (no hardware): `socat` to create paired PTYs (`sudo apt install socat`).

## With a real board
All commands are from the repo root unless noted.

1) Start broker (new terminal):
```bash
mosquitto -v
```
2) Cloud worker (new terminal):
```bash
cd cloud
source venv/bin/activate
python mqtt_worker.py
```
3) Optional leaderboard UI (same venv or another terminal):
```bash
cd cloud
. venv/bin/activate
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```
4) Bridge (new terminal):
```bash
cd agent
. venv/bin/activate
python -m agent.bridge --serial-port /dev/ttyACM0 --device-id dev1 --mqtt-host localhost --mqtt-port 1883
```
5) Flash/run firmware; verify events:
```bash
mosquitto_sub -t "whac/dev1/#" -v
```
6) Send commands back to board:
```bash
mosquitto_pub -t "whac/dev1/commands" -m '{"command":"pause"}' -q 1
mosquitto_pub -t "whac/dev1/commands" -m '{"command":"set_pop_duration","value":900}' -q 1
```

## Without hardware (UART simulated)
1) Create paired PTYs (new terminal):
```bash
socat -d -d PTY,raw,echo=0 PTY,raw,echo=0
# note /dev/pts/X and /dev/pts/Y from output
```
2) Broker + cloud worker: same as steps 1–2 above.
3) Bridge on one end:
```bash
cd agent
. venv/bin/activate
python -m agent.bridge -s /dev/pts/X --device-id devsim
```
4) Feed fake firmware JSON on the other end (from another terminal):
```bash
printf '{"type":"game_event","pop":3,"level":1,"outcome":"HIT","reaction_ms":120,"lives_left":4,"ts":1717}\n' > /dev/pts/Y
printf '{"type":"status","state":"playing","level":1,"pop_index":7,"lives_left":4,"ts":1718}\n' > /dev/pts/Y
```
5) Observe MQTT:
```bash
mosquitto_sub -t "whac/devsim/#" -v
```
6) Command round-trip (appears on `/dev/pts/Y`):
```bash
mosquitto_pub -t "whac/devsim/commands" -m '{"command":"pause"}' -q 1
```

## Notes
- Topics: `whac/<device_id>/game_events`, `/status`, `/telemetry/<sensor>`, `/events`, `/commands`.
- Bridge preserves payload JSON for `cloud/mqtt_worker.py` parsing.
