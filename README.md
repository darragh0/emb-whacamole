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
> If you are running the dashboard locally, you'll need to set the `APP_PORT` environment variable (to the port to run the dashboard on)

## License

[Apache-2.0][license-url]
