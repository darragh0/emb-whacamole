import logging
import time
from typing import TYPE_CHECKING, ClassVar, override

from .utils import cerr, cout

if TYPE_CHECKING:
    from rich.console import Console


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
        try:
            color = self.LEVEL_COLORS[record.levelno]
            lvl = record.levelname[:3].upper()
            time_str = time.strftime("%X")
            msg = self.format(record)

            # Color actual message for >=WARNING only
            cons: Console
            if record.levelno >= logging.WARNING:
                msg = f"[{color}]{msg}[/]"
                cons = self._stderr
            else:
                cons = self._stdout

            cons.print(f"[dim][{color}][{lvl}][/] [white]({time_str})[/] ::[/] {msg}")
        except Exception:  # noqa: BLE001 (standard logging.Handler pattern)
            self.handleError(record)


def init_logging() -> None:
    logging.basicConfig(level=logging.DEBUG, handlers=[RichStyleHandler()])
