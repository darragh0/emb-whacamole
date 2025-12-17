import os
import sys
from pathlib import Path
from typing import Final, NamedTuple

from dotenv import load_dotenv

from . import __prog__

_PORT_MIN: Final = 1
_PORT_MAX: Final = 65535


class _EnvConf(NamedTuple):
    mqtt_broker: str
    mqtt_port: int
    app_port: int
    app_root_path: str
    data_dir: Path


def _validate_port(name: str) -> int:
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


def _validate_broker(name: str) -> str:
    val = os.getenv(name)
    if val is None or not val.strip():
        msg = f"\x1b[96m{name}\x1b[0m is not set"
        raise ValueError(msg)

    return val


def _validate_root_path(name: str) -> str:
    val = os.getenv(name, "")
    if not val:
        return ""

    if not val.startswith("/"):
        msg = f"\x1b[96m{name}\x1b[0m must start with '/': {val}"
        raise ValueError(msg)

    if val.endswith("/"):
        msg = f"\x1b[96m{name}\x1b[0m must not end with '/': {val}"
        raise ValueError(msg)

    return val


def _validate_data_dir(name: str) -> Path:
    val = os.getenv(name, ".")
    path = Path(val)

    if path.exists() and not path.is_dir():
        msg = f"\x1b[96m{name}\x1b[0m is not a directory: {val}"
        raise ValueError(msg)

    if not path.exists():
        try:
            path.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            msg = f"\x1b[96m{name}\x1b[0m cannot be created: {e}"
            raise ValueError(msg) from e

    return path


def _load_env() -> _EnvConf:
    load_dotenv()

    errs: list[str] = []
    mbroker: str | None = None
    mport: int | None = None
    aport: int | None = None
    root_path: str | None = None
    data_dir: Path | None = None

    try:
        mbroker = _validate_broker("MQTT_BROKER")
    except ValueError as e:
        errs.append(str(e))

    try:
        mport = _validate_port("MQTT_PORT")
    except ValueError as e:
        errs.append(str(e))

    try:
        aport = _validate_port("APP_PORT")
    except ValueError as e:
        errs.append(str(e))

    try:
        root_path = _validate_root_path("APP_ROOT_PATH")
    except ValueError as e:
        errs.append(str(e))

    try:
        data_dir = _validate_data_dir("DATA_DIR")
    except ValueError as e:
        errs.append(str(e))

    if errs:
        print("".join(f"\x1b[1;91m{__prog__}: env-error:\x1b[0m {e}\n" for e in errs), end="", file=sys.stderr)
        sys.exit(1)

    return _EnvConf(
        mqtt_broker=mbroker,  # type: ignore[arg-type]
        mqtt_port=mport,  # type: ignore[arg-type]
        app_port=aport,  # type: ignore[arg-type]
        app_root_path=root_path,  # type: ignore[arg-type]
        data_dir=data_dir,  # type: ignore[arg-type]
    )


BROKER: Final
MQTT_PORT: Final
APP_PORT: Final
APP_ROOT_PATH: Final
DATA_DIR: Final
BROKER, MQTT_PORT, APP_PORT, APP_ROOT_PATH, DATA_DIR = _load_env()
