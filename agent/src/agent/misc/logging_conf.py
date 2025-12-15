from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING, ClassVar, Final, Literal, cast, override

from .utils import cerr, cout

if TYPE_CHECKING:
    type LogLvl = Literal[10, 20, 30, 40, 50]


LOG_ABBREV_2_LVL: Final[dict[str, LogLvl]] = {
    "DBG": logging.DEBUG,
    "INF": logging.INFO,
    "WRN": logging.WARNING,
    "ERR": logging.ERROR,
    "CRT": logging.CRITICAL,
}


LOG_LVL_2_COLOR: Final = {
    logging.DEBUG: "green",
    logging.INFO: "cyan",
    logging.WARNING: "yellow",
    logging.ERROR: "red",
    logging.CRITICAL: "bold red",
}


class _RichStyleHandler(logging.Handler):
    """Logging handler with Rich markup support and custom format."""

    LVL_2_ABBREV: ClassVar = {v: k for k, v in LOG_ABBREV_2_LVL.items()}

    @override
    def __init__(self) -> None:
        super().__init__()
        self._stdout = cout
        self._stderr = cerr

    @override
    def emit(self, record: logging.LogRecord) -> None:
        fmted = _RichStyleHandler._fmt_msg(self.format(record), cast("LogLvl", record.levelno))
        if fmted is None:
            self.handleError(record)
            return

        cons = self._stderr if record.levelno >= logging.WARNING else self._stdout
        cons.print(fmted)

    @classmethod
    def _fmt_msg(cls, msg: str, lvlno: LogLvl) -> str | None:
        try:
            color = LOG_LVL_2_COLOR[lvlno]
            lvl_abbrev = _RichStyleHandler.LVL_2_ABBREV[lvlno]
            time_str = time.strftime("%X")
            msg = f"[{color}]{msg}[/]" if lvlno >= logging.WARNING else msg
        except KeyError:
            return None

        return f"[dim][{color}][{lvl_abbrev}][/] [white]({time_str})[/] ::[/] {msg}"


def init_logging(lvl: LogLvl) -> None:
    """Initialize logging.

    Args:
        lvl: Logging level
    """
    logging.basicConfig(
        level=lvl,
        format="%(message)s",
        handlers=[_RichStyleHandler()],
    )
