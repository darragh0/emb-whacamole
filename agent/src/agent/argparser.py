import os
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

    arg("-s", "--serial-port", required=True, help="serial port (e.g. /dev/ttyUSB0)", metavar="P")
    arg(
        "--baud",
        type=int,
        default=115200,
        help="baud rate (default: 115200)",
        dest="baud_rate",
        metavar="RATE",
    )
    arg("--device-id", default="whacamole-dev", help='device ID (default: "whacamole-dev")', metavar="ID")
    arg(
        "--mqtt-host",
        default=os.getenv("MQTT_BROKER", "localhost"),
        help="MQTT broker host (default: env MQTT_BROKER or localhost)",
        metavar="HOST",
    )
    arg(
        "--mqtt-port",
        type=int,
        default=int(os.getenv("MQTT_PORT", "1883")),
        help="MQTT broker port (default: env MQTT_PORT or 1883)",
        metavar="PORT",
    )
    return parser


class Args(TypedDict):
    serial_port: str
    baud_rate: int
    device_id: str
    mqtt_host: str
    mqtt_port: int


def get_args() -> Args:
    """Create & return the argument parser."""
    parser = _mk_parser()
    args = parser.parse_args()
    return cast("Args", args.__dict__)
