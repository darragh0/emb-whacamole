"""Cloud backend entry point."""

from __future__ import annotations

import threading
import time
from typing import Any

import uvicorn

from cloud.mqtt import subscribe
from cloud.state import (
    MAX_PAST_SESSIONS,
    DeviceState,
    Session,
    devices,
    devices_lock,
)


def handle_message(data: dict[str, Any], topic: str) -> None:
    """Route MQTT messages to appropriate handlers."""
    if "/state" in topic:
        handle_state(data)
    elif "/game_events" in topic:
        handle_game_event(data)


def handle_state(data: dict[str, Any]) -> None:
    """Handle device state messages."""
    device_id = data["device_id"]
    if device_id is None:
        return

    status = data.get("status")
    ts = data.get("ts", int(time.time() * 1000))

    with devices_lock:
        if device_id not in devices:
            devices[device_id] = DeviceState(device_id=device_id, last_seen=ts)

        device = devices[device_id]
        device.last_seen = ts

        if status in ("serial_error", "offline"):
            device.status = status
        else:
            device.status = "online"


def handle_game_event(data: dict[str, Any]) -> None:
    """Handle game events - auto-discover devices, update state."""

    device_id = data.get("device_id")
    event_type = data.get("event_type")
    ts = data.get("ts", int(time.time() * 1000))

    if not device_id:
        return

    with devices_lock:
        if device_id not in devices:
            devices[device_id] = DeviceState(device_id=device_id)

        device = devices[device_id]
        device.status = "online"
        device.last_seen = ts

        if event_type == "session_start":
            device.game_state = "playing"
            device.current_session = Session(started_at=ts)

        elif event_type == "session_end":
            device.game_state = "idle"
            if device.current_session:
                device.current_session.ended_at = ts
                device.current_session.won = data.get("win") == "true"
                device.current_session.events.append(data)
                device.past_sessions.insert(0, device.current_session)
                device.past_sessions = device.past_sessions[:MAX_PAST_SESSIONS]
            device.current_session = None

        elif device.current_session:
            device.current_session.events.append(data)


def main() -> None:
    """Start MQTT subscriber and web server."""
    topics = ["whac/+/game_events", "whac/+/state"]
    client = subscribe(topics, handle_message)
    threading.Thread(target=client.loop_forever, daemon=True).start()

    uvicorn.run("cloud.app:app", host="0.0.0.0", port=8001)  # noqa: S104


if __name__ == "__main__":
    main()
