Cloud backend for the Whack-a-Mole project. Device communication is MQTT-only (events + commands). An optional FastAPI app serves a leaderboard UI for humans.

## Stack
- Python 3.11+, paho-mqtt client for device ingest/commands.
- Optional FastAPI + Uvicorn only for the leaderboard UI/stats (no device ingestion over HTTP).
- JSON file persistence to keep dependencies low; can be swapped for SQLite/Postgres if needed.

## Layout
- `mqtt_worker.py` - MQTT client: subscribes to device topics, stores sessions, responds with config/commands.
- `app.py` - Optional FastAPI app that serves a leaderboard UI and stats (no device ingest).
- `models.py` - Pydantic models for request/response validation.
- `storage.py` - JSON-backed data store plus leaderboard/stats helpers.
- `config.py` - Holds default/per-device configuration and persists it.
- `device_protocol.md` - Message formats and topic/path conventions.
- `data/` - Runtime data (sessions + config). Git-ignored except for `.gitkeep`.

## Running the MQTT worker (device path)
```bash
cd cloud
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python mqtt_worker.py
```
- Environment variables:
  - `MQTT_BROKER` (default: `localhost`)
  - `MQTT_PORT` (default: `1883`)

## Starting a local MQTT broker (mosquitto)
- Docker: `docker run -p 1883:1883 eclipse-mosquitto`
- Native (Debian/Ubuntu): `sudo apt install mosquitto` then `mosquitto -v`
- Course server: use the provided broker host/port (set `MQTT_BROKER`/`MQTT_PORT` accordingly).

## Running the leaderboard UI (optional, human-facing)
```bash
cd cloud
source .venv/bin/activate
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```
- Leaderboard UI: `http://localhost:8000/leaderboard`
- Stats API (for dashboards): `http://localhost:8000/api/leaderboard`, `http://localhost:8000/api/stats`, `http://localhost:8000/api/health`

## Key endpoints
- Device path is MQTT-only. See `device_protocol.md` for topics/payloads.
- HTTP endpoints are only for humans/dashboards:
  - `GET /api/leaderboard` - Aggregated scores by player.
  - `GET /api/stats` - Summary counts for dashboards.
  - `GET /leaderboard` - Minimal HTML leaderboard for humans.

## Fake device for demos
Publish sample sessions to MQTT to exercise the backend and leaderboard:
```bash
cd cloud
source .venv/bin/activate
python fake_device.py
# set MQTT_BROKER/MQTT_PORT/DEVICE_ID if needed
```

## Adapting firmware
- Send ISO-8601 timestamps (`Z` for UTC).
- Always include `device_id`; `session_id` can be a UUID or incrementing counter.
- Extra fields are ignored by the backend so firmware can evolve without breaking ingestion.
