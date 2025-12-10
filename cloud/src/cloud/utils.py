from sys import stderr


def pwarn(msg: str) -> None:
    print(f"\x1b[93mcloud: warning:\x1b[0m {msg}", file=stderr)
