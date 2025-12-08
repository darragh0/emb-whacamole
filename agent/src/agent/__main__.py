import contextlib

from agent.env import get_env_vars

from .argparser import get_args
from .bridge import Bridge
from .logging_conf import init_logging


def main() -> None:
    init_logging()
    broker, port = get_env_vars()
    args = get_args()
    bridge = Bridge(mqtt_broker=broker, mqtt_port=port, **args)

    with contextlib.suppress(KeyboardInterrupt):
        bridge.run()
