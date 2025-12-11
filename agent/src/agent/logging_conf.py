from __future__ import annotations

import logging
import time
from logging import _levelToName
from typing import ClassVar, Literal, cast, override

from .utils import cerr, cout

type LogLevel = Literal[10, 20, 30, 40, 50]


class RichStyleHandler(logging.Handler):
    """Logging handler with Rich markup support and custom format."""

    LEVEL_COLORS: ClassVar = {
        logging.DEBUG: "green",
        logging.INFO: "cyan",
        logging.WARNING: "yellow",
        logging.ERROR: "red",
        logging.CRITICAL: "bold red",
    }

    @override
    def __init__(self) -> None:
        super().__init__()
        self._stdout = cout
        self._stderr = cerr

    @override
    def emit(self, record: logging.LogRecord) -> None:
        fmted = RichStyleHandler.fmt_msg(self.format(record), cast("LogLevel", record.levelno))
        if fmted is None:
            self.handleError(record)
            return

        cons = self._stderr if record.levelno >= logging.WARNING else self._stdout
        cons.print(fmted)

    @classmethod
    def fmt_msg(cls, msg: str, lvlno: LogLevel) -> str | None:
        try:
            color = RichStyleHandler.LEVEL_COLORS[lvlno]
            lvl = _levelToName[lvlno][:3].upper()
            time_str = time.strftime("%X")
            msg = f"[{color}]{msg}[/]" if lvlno >= logging.WARNING else msg
        except KeyError:
            return None

        return f"[dim][{color}][{lvl}][/] [white]({time_str})[/] ::[/] {msg}"


def init_logging() -> None:
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(message)s",
        handlers=[RichStyleHandler()],
    )
