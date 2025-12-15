from time import time

from rich.console import Console

# Handles
cout = Console()
cerr = Console(stderr=True)


def time_now_ms() -> int:
    """Return time in milliseconds since the Epoch."""
    return int(time() * 1000)
