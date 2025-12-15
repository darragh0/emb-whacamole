<div align="center">
  <a href="./assets/img/whacamole.png" target="_blank">
    <img src="./assets/img/whacamole.png" alt="Embedded Whac-A-Mole Logo" width="650">
  </a>
</div>

<br />
<p align="center">A Whac-A-Mole game for Analog Devices' [MAX32655 MCU](https://www.analog.com/en/products/max32655.html)</p>
<br />

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

| Directory    | Description                                                                                           |
| ------------ | ----------------------------------------------------------------------------------------------------- |
| `emb/`       | **FreeRTOS firmware** – Runs game loop; sends JSON events over UART; receives commands from dashboard |
| `agent/`     | **Python UART-MQTT bridge** – Bidirectional relay between device & dashboard                          |
| `dashboard/` | **Web dashboard (as MQTT backend)** – Persists events to JSONL; sends commands to device              |

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

> [!NOTE]
> If you are running the dashboard locally, you will need to set the `APP_PORT` environment variable (to the port you want to run the dashboard on).

## License

Apache-2.0 (see [LICENSE](./LICENSE))
