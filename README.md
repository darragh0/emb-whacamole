# emb-whacamole

Whac-A-Mole game for Analog Devices' [MAX32655 MCU](https://www.analog.com/en/products/max32655.html).

## Architecture

```
┌──────────────┐     MQTT      ┌─────────────┐
│  dashboard/  │<------------->│   agent/    │
│  Dashboard   │               │   Bridge    │
└──────────────┘               └─────────────┘
                                     ^
                                     ¦ UART
                                     ∨
                               ┌─────────────┐
                               │    emb/     │
                               │   Device    │
                               └─────────────┘
```

## Components

| Directory    | Description                                                                                        |
| ------------ | -------------------------------------------------------------------------------------------------- |
| `emb/`       | **FreeRTOS firmware** – Runs game loop; sends JSON events over UART; receives b"P" (Pause) command |
| `agent/`     | **Python UART-MQTT bridge** – Bidirectional relay between device & dashboard                       |
| `dashboard/` | **MQTT backend + web dashboard** – Persists events to JSONL; sends commands to device              |

## Installation

### Agent/Dashboard

Follow these steps to install agent or dashboard locally:

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

# Now you should be able to run `dashboard/agent` directly
```

#### Configuration

Copy `.env.example` to `.env` and set the MQTT broker details:

```bash
cp .env.example .env
```

Required environment variables:

- `MQTT_BROKER` - MQTT broker URL
- `MQTT_PORT` - MQTT broker port (default: 1883)

  
<img width="1080" height="1309" alt="whack" src="https://github.com/user-attachments/assets/bdc11a24-db09-459a-9b3d-74d809fd2ee0" />


## License

Apache-2.0 (see [LICENSE](./LICENSE))
