# Cloud

MQTT backend + dashboard for the Whack-A-Mole game.

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

# Now you should be able to run `cloud` directly
```

## Configuration

Copy `.env.example` to `.env` and set the MQTT broker details:

```bash
cp .env.example .env
```

Required environment variables:

- `MQTT_BROKER` - MQTT broker URL
- `MQTT_PORT` - MQTT broker port (default: 1883)

## Files

```
.
├── data
│   └── events.jsonl              # Game events log (JSONL)
├── src
│   └── cloud
│       ├── app.py                # FastAPI app, routes, static files
│       ├── __init__.py
│       ├── __main__.py           # Entry point (MQTT subscriber + uvicorn)
│       ├── mqtt.py               # MQTT subscribe/publish
│       ├── types.py              # TypedDict definitions for events
│       └── utils.py              # Config, paths, error handling
├── static
│   ├── html
│   │   └── dashboard.html        # Dashboard UI
│   └── ico
│       └── favicon.ico
├── .env.example
├── pyproject.toml
└── ruff.toml
```
