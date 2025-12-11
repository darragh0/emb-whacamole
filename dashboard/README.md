# Dashboard

MQTT backend + dashboard for the Whac-A-Mole game.

## Configuration

Along with the MQTT broker details ([outlined here](../README.md#configuration)), you can also change the dashboard's port:

- `APP_PORT` - App port (default: 8080)

## Files

```
.
├── data
│   └── events.jsonl              # Game events log (JSONL)
├── src
│   └── dashboard
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
