# Agent

UART-to-MQTT bridge for the Whac-A-Mole game.

## Installation

### Requirements

- Python >= 3.13

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
