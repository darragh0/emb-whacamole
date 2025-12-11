import contextlib

from agent.env import get_env_vars

from .argparser import get_args
from .bridge import Bridge
from .logging_conf import init_logging


def main() -> None:
    init_logging()
    bridge = Bridge(**get_env_vars(), **get_args())

    with contextlib.suppress(KeyboardInterrupt):
        bridge.run()
