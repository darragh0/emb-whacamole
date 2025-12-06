import json
import logging
import sys
from logging.config import dictConfig
from pathlib import Path
from typing import ClassVar, Final

FILE_DIR: Final = Path(__file__).parent
BASE_DIR: Final = FILE_DIR.parents[1]
CONFIG_PATH: Final = BASE_DIR / "config" / "logging.json"


class StdFormatter(logging.Formatter):
    """Logging formatter for stdout & stderr."""

    _COLORS: ClassVar = {
        logging.DEBUG: "\x1b[92m",
        logging.INFO: "\x1b[96m",
        logging.WARNING: "\x1b[93m",
        logging.ERROR: "\x1b[91m",
        logging.CRITICAL: "\x1b[1;91m",
    }

    def __init__(self, *, fmt: str | None = None, datefmt: str | None = None) -> None:
        super().__init__(fmt=fmt, datefmt=datefmt)

    def format(self, record: logging.LogRecord) -> str:
        fmt: str | None = None
        if self._fmt is not None:
            lvl_clr = StdFormatter._COLORS[record.levelno]
            msg_clr = StdFormatter._COLORS[record.levelno] if record.levelno > logging.INFO else ""
            fmt = (
                self._fmt.replace("<color>", lvl_clr)
                .replace("</color>", "\x1b[0m")
                .replace("<color_if_err>", msg_clr)
                .replace("</color_if_err>", "\x1b[0m")
            )
        else:
            fmt = None

        fmted: str = logging.Formatter(fmt=fmt, datefmt=self.datefmt).format(record)
        return fmted


class DismissErrorsFilter(logging.Filter):
    """Filter for dismissing errors."""

    def filter(self, record: logging.LogRecord) -> bool:
        return record.levelno < logging.WARNING


def init_logging() -> None:
    """Initialize logging for application."""

    sys.path.append(str(FILE_DIR))
    if not CONFIG_PATH.is_file():
        msg = f"\x1b[1;91merror:\x1b[0m logging config file moved or deleted -- need \x1b[96m{CONFIG_PATH}\x1b[0m"
        print(msg, file=sys.stderr)
        sys.exit(1)

    with Path.open(CONFIG_PATH) as file:
        cfg = json.load(file)
        dictConfig(cfg)
