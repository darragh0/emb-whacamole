import os
import sys
from pathlib import Path
from typing import Final, NoReturn, cast

from dotenv import load_dotenv

PROJ_ROOT: Final = Path(__file__).parents[2]
DATA_FILE: Final = PROJ_ROOT / "data" / "events.jsonl"

PORT_MIN: Final = 1
PORT_MAX: Final = 65535


def _setup_err(msg: str, exit_code: int = 1) -> NoReturn:
    print(f"\x1b[1;91mcloud: setup-error:\x1b[0m {msg}", file=sys.stderr)
    sys.exit(exit_code)


def get_env_vars() -> tuple[str, int]:
    def ensure_valid_port(port: int) -> None:
        if not (PORT_MIN <= port <= PORT_MAX):
            raise ValueError

    load_dotenv()
    broker = os.getenv("MQTT_BROKER")
    port_raw = os.getenv("MQTT_PORT")

    for var, name in ((broker, "MQTT_BROKER"), (port_raw, "MQTT_PORT")):
        if var is None or var.strip() == "":
            _setup_err(f"\x1b[96m{name}\x1b[0m is missing")

    try:
        port = int(cast("str", port_raw))
        ensure_valid_port(port)
    except ValueError:
        _setup_err(f"\x1b[96mMQTT_PORT\x1b[0m is invalid: \x1b[91m{port_raw}\x1b[0m")

    return cast("str", broker), port
