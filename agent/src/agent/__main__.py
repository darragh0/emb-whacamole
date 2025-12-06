import contextlib

from .argparser import get_args
from .bridge import Bridge
from .logging_conf import init_logging


def main() -> None:
    init_logging()
    args = get_args()
    bridge = Bridge(**args)

    with contextlib.suppress(KeyboardInterrupt):
        bridge.run()
