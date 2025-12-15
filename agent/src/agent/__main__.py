import contextlib

from agent.misc.env import get_env_vars

from .bridge import Bridge
from .misc import get_cli_args, init_logging


def main() -> None:
    args = get_cli_args()
    init_logging(args.log_level)
    bridge = Bridge(**get_env_vars(), serial_port=args.serial_port, baud_rate=args.baud_rate)

    with contextlib.suppress(KeyboardInterrupt):
        bridge.run()
