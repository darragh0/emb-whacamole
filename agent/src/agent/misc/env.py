import os
import sys
from typing import Final, TypedDict

from dotenv import load_dotenv

from agent.__init__ import __prog__

from .utils import cerr

_PORT_MIN: Final = 1
_PORT_MAX: Final = 65535


class _MqttConf(TypedDict):
    mqtt_broker: str
    mqtt_port: int


def _ensure_valid_port(name: str) -> int:
    val = os.getenv(name)
    if val is None or not val.strip():
        msg = f"[cyan]{name}[/] is not set"
        raise ValueError(msg)

    try:
        port = int(val)
    except ValueError as e:
        msg = f"[cyan]{name}[/] is not an integer: {val}"
        raise ValueError(msg) from e
    else:
        if not (_PORT_MIN <= port <= _PORT_MAX):
            msg = f"[cyan]{name}[/] is out of range: {val}"
            raise ValueError(msg)

    return port


def _ensure_valid_broker(name: str) -> str:
    val = os.getenv(name)
    if val is None or not val.strip():
        msg = f"[cyan]{name}[/] is not set"
        raise ValueError(msg)

    return val


def get_env_vars() -> _MqttConf:
    load_dotenv()

    errs: list[str] = []
    broker: str | None = None
    port: int | None = None

    try:
        broker = _ensure_valid_broker("MQTT_BROKER")
    except ValueError as e:
        errs.append(str(e))

    try:
        port = _ensure_valid_port("MQTT_PORT")
    except ValueError as e:
        errs.append(str(e))

    if broker is None or port is None:
        cerr.print("".join(f"[bold bright_red]{__prog__}: env-error:[/] {e}\n" for e in errs), end="")
        sys.exit(1)

    return {"mqtt_broker": broker, "mqtt_port": port}
