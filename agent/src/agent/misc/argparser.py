from __future__ import annotations

from argparse import ArgumentParser
from typing import TYPE_CHECKING, NamedTuple, cast

from rich_argparse import RichHelpFormatter

from .logging_conf import LOG_ABBREV_2_LVL, LOG_LVL_2_COLOR

if TYPE_CHECKING:
    from .logging_conf import LogLvl


def _mk_parser() -> ArgumentParser:
    RichHelpFormatter.usage_markup = True
    RichHelpFormatter.styles.update(
        {
            "argparse.args": "cyan",
            "argparse.groups": "green bold",
            "argparse.metavar": "dim cyan",
            "argparse.usage": "dim cyan",
            "argparse.prog": "cyan bold",
        },
    )

    parser = ArgumentParser(
        description="UART bridge for Whac-A-Mole device",
        formatter_class=RichHelpFormatter,
        usage="%(prog)s [cyan]-s [dim]P[/] \\[options][/]",
    )

    arg = parser.add_argument

    arg("-s", "--serial-port", required=True, help="serial port (e.g. [cyan]/dev/ttyUSB0[/])", metavar="P")
    arg(
        "-b",
        "--baud",
        type=int,
        default=115200,
        help="baud rate (default: [yellow]115200[/])",
        dest="baud_rate",
        metavar="RATE",
    )

    log_lvl_choices = ", ".join(
        f"[{clr}]{abbr}[/]" for abbr, clr in zip(LOG_ABBREV_2_LVL, LOG_LVL_2_COLOR.values(), strict=True)
    )

    arg(
        "-l",
        "--log-level",
        type=str,
        default="DBG",
        help=f"base logging level (default: [yellow]INF[/])\t[{log_lvl_choices}]",
        choices=LOG_ABBREV_2_LVL,
        dest="log_level",
        metavar="L",
    )
    return parser


class _Args(NamedTuple):
    serial_port: str
    baud_rate: int
    log_level: LogLvl


def get_cli_args() -> _Args:
    """Create & return parsed arguments."""

    parser = _mk_parser()
    args = parser.parse_args()

    return _Args(
        serial_port=args.serial_port,
        baud_rate=args.baud_rate,
        log_level=LOG_ABBREV_2_LVL[cast("str", args.log_level)],
    )
