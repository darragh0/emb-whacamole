<div align="center">
  <a href="./assets/img/whacamole.png" target="_blank">
    <img src="./assets/img/whacamole.png" alt="Embedded Whac-A-Mole Logo" width="650">
  </a>
</div>

<br />

<div align="center">

<p>
    A Whac-A-Mole game for Analog Devices'
    <a href="https://www.analog.com/en/products/max32655.html">MAX32655 MCU</a>
</p>

[![License][license-img]][license-url]&nbsp;
[![SDK][sdk-img]][sdk-url]&nbsp;
[![Python][py-img]][py-url]

</div>

[license-img]: https://img.shields.io/github/license/darragh0/emb-whacamole?style=flat-square&logo=apache&label=%20&color=red
[license-url]: https://github.com/darragh0/emb-whacamole?tab=Apache-2.0-1-ov-file
[sdk-img]: https://img.shields.io/badge/MaximSDK-3DB385?style=flat-square&logo=task&logoColor=white
[sdk-url]: https://github.com/analogdevicesinc/msdk
[py-img]: https://img.shields.io/badge/3.12%2B-blue?style=flat-square&logo=python&logoColor=FFFD85
[py-url]: https://www.python.org/

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                  Cloud Server (alderaan)                     │
│  ┌─────────────────┐      ┌────────────────────────────┐    │
│  │    Mosquitto    │◄────►│    Dashboard (FastAPI)     │    │
│  │  MQTT Broker    │      │  • Web UI & Device Control │    │
│  │    :1883        │      │  • Live Score Charts       │    │
│  └────────┬────────┘      │  • Game Analytics          │    │
│           │               │  • Leaderboard             │    │
│           │               │         :8088              │    │
│           │               └────────────────────────────┘    │
└───────────┼─────────────────────────────────────────────────┘
            │ MQTT
            │
┌───────────┼───────────┐
│  Laptop   │           │
│  ┌────────▼────────┐  │
│  │  Python Agent   │  │
│  │ (UART ↔ MQTT)   │  │
│  └────────┬────────┘  │
└───────────┼───────────┘
            │ USB Serial (115200 baud)
            │
┌───────────▼───────────┐
│  MAX32655 Device      │
│  ┌─────────────────┐  │
│  │    FreeRTOS     │  │
│  │  ┌───────────┐  │  │
│  │  │ Game Task │──────► 5ms polling, deterministic timing
│  │  │   (P3)    │  │  │
│  │  └─────┬─────┘  │  │
│  │        │ Queue  │  │
│  │  ┌─────▼─────┐  │  │
│  │  │Agent Task │  │  │
│  │  │   (P2)    │  │  │
│  │  └───────────┘  │  │
│  └────────┬────────┘  │
│           │ I2C       │
│  ┌────────▼────────┐  │
│  │  MAX7325 GPIO   │  │
│  │  8 LEDs + 8 Btns│  │
│  └─────────────────┘  │
└───────────────────────┘
```

## Components

| Directory    | Description                                                                                           |
| ------------ | ----------------------------------------------------------------------------------------------------- |
| `emb/`       | **FreeRTOS firmware** – Runs game loop; sends JSON events over UART; receives commands from dashboard |
| `agent/`     | **Python UART-MQTT bridge** – Bidirectional relay between device & dashboard                          |
| `dashboard/` | **Web dashboard (as MQTT backend)** – Persists events to JSONL; sends commands to device              |

## Innovation Highlights

### Real-Time Performance Guarantees

- **5ms maximum detection latency** – Deterministic button polling using FreeRTOS `vTaskDelay()`
- **Priority-based task scheduling** – Pause (P4) > Game (P3) > Agent (P2) prevents timing jitter
- **Autonomous operation** – Game continues during network outages with 32-event buffer
- **Tick-accurate timing** – 1ms FreeRTOS tick rate for precise reaction time measurement

### Advanced Game Analytics

- **Live score line graph** – Real-time chart showing score progression during gameplay
- **Per-button performance heatmaps** – Visual breakdown of hit rate by button position
- **Reaction time analysis** – Average, best, and distribution of player response times
- **Practice recommendations** – AI-style suggestions based on player weaknesses
- **Session history** – Track past games with expandable event logs and score charts

### Intelligent Scoring System

```
score = (base_points × level_multiplier × speed_bonus) + level_bonuses
      × lives_multiplier

Where:
  • speed_bonus = max(0.5, 2 - reaction_time/1000)  → Faster = higher score
  • level_multiplier = 1-8                          → Harder = more points
  • perfect_level_bonus = 500 × level               → No misses = big bonus
  • lives_multiplier = 1 + (lives × 0.1)            → Preserve lives = 1.5x max
```

### Robust Communication Protocol

| Direction | Format | Example |
|-----------|--------|---------|
| Device → Cloud | JSON events | `{"event_type":"pop_result","mole_id":3,"outcome":"hit","reaction_ms":245}` |
| Cloud → Device | Single-byte commands | `P` (pause), `R` (reset), `S` (start), `1-8` (level) |

- **Hardware-based device ID** – Uses chip's unique serial number (USN), no hardcoding
- **Auto-reconnect** – Exponential backoff up to 30s on connection loss
- **Last-will testament** – MQTT publishes "offline" status if agent crashes
- **QoS 2 messaging** – Exactly-once delivery for critical events

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
> If you are running the dashboard locally, you'll need to set the `APP_PORT` environment variable (to the port to run the dashboard on)

## License

[Apache-2.0][license-url]
