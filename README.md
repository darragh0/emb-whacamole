# emb-whackamole

Whack-A-Mole game for Analog Devices' [MAX32655 MCU](https://www.analog.com/en/products/max32655.html).

## Architecture

```
┌─────────────┐     MQTT      ┌─────────────┐
│   cloud/    │<------------->│   agent/    │
│  Dashboard  │               │   Bridge    │
└─────────────┘               └─────────────┘
                                     ^
                                     ¦ UART
                                     ∨
                              ┌─────────────┐
                              │    emb/     │
                              │   Device    │
                              └─────────────┘
```

## Components

| Directory | Description                                                                                        |
| --------- | -------------------------------------------------------------------------------------------------- |
| `emb/`    | **FreeRTOS firmware** – Runs game loop; sends JSON events over UART; receives b"P" (Pause) command |
| `agent/`  | **Python UART-MQTT bridge** – Bidirectional relay between device & cloud                           |
| `cloud/`  | **MQTT backend + web dashboard** – Persists events to JSONL; sends commands to device              |

## Installation

### Agent/Cloud

Follow these steps to install agent or cloud locally:

#### Requirements

- Python >= 3.12

#### Using uv

```bash
uv sync && . ./.venv/bin/activate
```

#### Using pip

```bash
python3 -m venv venv
. venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install .        # or `pip install -e .` for development

# Now you should be able to run `cloud/agent` directly
```

#### Configuration

Copy `.env.example` to `.env` and set the MQTT broker details:

```bash
cp .env.example .env
```

Required environment variables:

- `MQTT_BROKER` - MQTT broker URL
- `MQTT_PORT` - MQTT broker port (default: 1883)

## License

Apache-2.0 (see [LICENSE](./LICENSE))
