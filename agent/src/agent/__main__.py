import contextlib

from agent.misc.env import get_env_vars

from .bridge import Bridge
from .misc import get_cli_args, init_logging


def main() -> None:
    init_logging()
    bridge = Bridge(**get_env_vars(), **get_cli_args())

    with contextlib.suppress(KeyboardInterrupt):
        bridge.run()
