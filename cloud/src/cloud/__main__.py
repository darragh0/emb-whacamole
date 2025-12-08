"""Cloud backend entry point."""

from __future__ import annotations

import json
import threading
from typing import TYPE_CHECKING

import uvicorn

from cloud.app import DATA_FILE
from cloud.mqtt import subscribe

if TYPE_CHECKING:
    from cloud.types import GameEvent


def handle_event(data: GameEvent) -> None:
    """Append event to JSONL file.

    Args:
        data: Game event
    """
    DATA_FILE.parent.mkdir(exist_ok=True)
    with DATA_FILE.open("a") as f:
        f.write(f"{json.dumps(data)}\n")


def main() -> None:
    """Start MQTT subscriber and web server."""

    client = subscribe(["whac/+/game_events"], handle_event)
    threading.Thread(target=client.loop_forever, daemon=True).start()
    uvicorn.run("cloud.app:app", host="0.0.0.0", port=8000)  # noqa: S104
