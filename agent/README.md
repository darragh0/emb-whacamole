# Agent

UART-to-MQTT bridge for the Whac-A-Mole game.

## Configuration

Copy `.env.example` to `.env` and configure:

| Variable      | Description          |
| ------------- | -------------------- |
| `MQTT_BROKER` | MQTT broker hostname |
| `MQTT_PORT`   | MQTT broker port     |

## Files

```
.
├── pyproject.toml
├── README.md
└── src/
    └── agent/
        ├── __init__.py
        ├── __main__.py        # Entry point
        ├── bridge.py          # UART-to-MQTT bridge
        ├── mqtt.py            # MQTT client wrapper
        └── misc/              # Unimportant miscellaneous stuff
```
