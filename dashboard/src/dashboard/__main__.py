import threading
import time
from typing import Any, Final

import uvicorn

from .env import APP_PORT, APP_ROOT_PATH
from .leaderboard import add_entry, calculate_score
from .mqtt import subscribe
from .state import (
    DEV_LOCK,
    MAX_PAST_SESSIONS,
    DeviceState,
    Session,
    devices,
)

DEVICE_TIMEOUT_MS: Final = 30_000  # 30 seconds - mark offline if no message received
TIMEOUT_CHECK_INTERVAL: Final = 5  # Secs between timeout checks


def handle_message(data: dict[str, Any], topic: str) -> None:
    """Route MQTT messages to appropriate handlers."""

    if "/state" in topic:
        handle_state(data)
    elif "/game_events" in topic:
        handle_game_event(data)


def handle_state(data: dict[str, Any]) -> None:
    """Handle device state messages."""

    if "device_id" not in data:
        return

    device_id = data["device_id"]
    status = data.get("status")
    ts = data.get("ts", int(time.time() * 1000))

    with DEV_LOCK:
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

    if "device_id" not in data:
        return

    device_id = data["device_id"]
    event_type = data.get("event_type")
    ts = data.get("ts", int(time.time() * 1000))

    with DEV_LOCK:
        if device_id not in devices:
            devices[device_id] = DeviceState(device_id=device_id)

        device = devices[device_id]
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

                score = calculate_score(device.current_session.events)
                add_entry(device_id, score, ts)

                device.past_sessions.insert(0, device.current_session)
                device.past_sessions = device.past_sessions[:MAX_PAST_SESSIONS]
            device.current_session = None

        elif device.current_session:
            device.current_session.events.append(data)


def check_device_timeouts() -> None:
    """Mark devices offline if they haven't sent messages recently."""
    while True:
        time.sleep(TIMEOUT_CHECK_INTERVAL)
        now = int(time.time() * 1000)
        with DEV_LOCK:
            for device in devices.values():
                if device.status == "online" and (now - device.last_seen) > DEVICE_TIMEOUT_MS:
                    device.status = "offline"


def main() -> None:
    """Start MQTT subscriber and web server."""
    topics = ["whac/+/game_events", "whac/+/state"]
    client = subscribe(topics, handle_message)
    threading.Thread(target=client.loop_forever, daemon=True).start()
    threading.Thread(target=check_device_timeouts, daemon=True).start()

    uvicorn.run("dashboard.app:app", host="0.0.0.0", port=APP_PORT, root_path=APP_ROOT_PATH)  # noqa: S104


if __name__ == "__main__":
    main()
