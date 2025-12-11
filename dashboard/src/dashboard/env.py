import os
import sys
from typing import Final, NamedTuple

from dotenv import load_dotenv

from . import __prog__

_PORT_MIN: Final = 1
_PORT_MAX: Final = 65535


class _MqttConf(NamedTuple):
    mqtt_broker: str
    mqtt_port: int
    app_port: int


def _ensure_valid_port(name: str) -> int:
    val = os.getenv(name)
    if val is None or not val.strip():
        msg = f"\x1b[96m{name}\x1b[0m is not set"
        raise ValueError(msg)

    try:
        port = int(val)
    except ValueError as e:
        msg = f"\x1b[96m{name}\x1b[0m is not an integer: {val}"
        raise ValueError(msg) from e
    else:
        if not (_PORT_MIN <= port <= _PORT_MAX):
            msg = f"\x1b[96m{name}\x1b[0m is out of range: {val}"
            raise ValueError(msg)

    return port


def _ensure_valid_broker(name: str) -> str:
    val = os.getenv(name)
    if val is None or not val.strip():
        msg = f"\x1b[96m{name}\x1b[0m is not set"
        raise ValueError(msg)

    return val


def _load_env() -> _MqttConf:
    load_dotenv()

    errs: list[str] = []
    mbroker: str | None = None
    mport: int | None = None
    aport: int | None = None

    try:
        mbroker = _ensure_valid_broker("MQTT_BROKER")
    except ValueError as e:
        errs.append(str(e))

    try:
        mport = _ensure_valid_port("MQTT_PORT")
    except ValueError as e:
        errs.append(str(e))

    try:
        aport = _ensure_valid_port("APP_PORT")
    except ValueError as e:
        errs.append(str(e))

    if mbroker is None or mport is None or aport is None:
        print("".join(f"\x1b[1;91m{__prog__}: env-error:\x1b[0m {e}\n" for e in errs), end="", file=sys.stderr)
        sys.exit(1)

    return _MqttConf(mqtt_broker=mbroker, mqtt_port=mport, app_port=aport)


BROKER: Final
MQTT_PORT: Final
APP_PORT: Final
BROKER, MQTT_PORT, APP_PORT = _load_env()
