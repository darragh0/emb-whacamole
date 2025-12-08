from argparse import ArgumentParser
from typing import TypedDict, cast

from rich_argparse import RichHelpFormatter


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
        "--baud",
        type=int,
        default=115200,
        help="baud rate (default: [yellow]115200[/])",
        dest="baud_rate",
        metavar="RATE",
    )
    arg("--device-id", default="whacamole-dev", help='device ID (default: [green]"whacamole-dev"[/])', metavar="ID")
    return parser


class Args(TypedDict):
    serial_port: str
    baud_rate: int
    device_id: str


def get_args() -> Args:
    """Create & return the argument parser."""
    parser = _mk_parser()
    args = parser.parse_args()
    return cast("Args", args.__dict__)
