from time import time


def time_now_ms() -> int:
    """Return time in milliseconds since the Epoch."""
    return int(time() * 1000)
