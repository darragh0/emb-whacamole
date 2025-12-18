"""
Dashboard entry point - MQTT subscriber and device state management.

This module coordinates the real-time dashboard backend:
    1. Subscribes to MQTT topics for device state and game events
    2. Maintains in-memory device state (status, sessions, game progress)
    3. Updates leaderboard on session completion
    4. Runs timeout watchdog to detect offline devices

Architecture:
    MQTT Broker --> handle_message() --> DeviceState (in-memory)
                                     --> Leaderboard (persisted to JSON)
"""

import threading
import time
from typing import Any, Final

import uvicorn

from .env import APP_PORT, APP_ROOT_PATH
from .leaderboard import add_entry, calculate_score
from .leaderboard import init as init_leaderboard
from .mqtt import subscribe
from .state import (
    DEV_LOCK,
    MAX_PAST_SESSIONS,
    DeviceState,
    Session,
    devices,
)

# Device considered offline if no MQTT message received within this window
DEVICE_TIMEOUT_MS: Final = 30_000

# How often to check for timed-out devices (seconds)
TIMEOUT_CHECK_INTERVAL: Final = 5


def handle_message(data: dict[str, Any], topic: str) -> None:
    """Route MQTT messages to appropriate handlers based on topic.

    Topics:
        whac/<device_id>/state       -> handle_state()
        whac/<device_id>/game_events -> handle_game_event()
    """
    if "/state" in topic:
        handle_state(data)
    elif "/game_events" in topic:
        handle_game_event(data)


def handle_state(data: dict[str, Any]) -> None:
    """Handle device state messages from Python agent.

    Auto-discovers new devices and updates connection status.
    Agent publishes state on connect, disconnect, and serial errors.
    """
    if "device_id" not in data:
        return

    device_id = data["device_id"]
    status = data.get("status")
    ts = data.get("ts", int(time.time() * 1000))

    with DEV_LOCK:
        # Auto-discover: create DeviceState on first message from device
        if device_id not in devices:
            devices[device_id] = DeviceState(device_id=device_id, last_seen=ts)

        device = devices[device_id]
        device.last_seen = ts

        # Preserve error/offline status from agent; otherwise mark online
        if status in ("serial_error", "offline"):
            device.status = status
        else:
            device.status = "online"


def handle_game_event(data: dict[str, Any]) -> None:
    """Handle game events from embedded device (via agent).

    Tracks session lifecycle and calculates scores:
        session_start -> Create new Session, set game_state="playing"
        pop_result    -> Append to current session events
        lvl_complete  -> Append to current session events
        session_end   -> Finalize session, calculate score, update leaderboard
    """
    if "device_id" not in data:
        return

    device_id = data["device_id"]
    event_type = data.get("event_type")
    ts = data.get("ts", int(time.time() * 1000))

    with DEV_LOCK:
        # Auto-discover device if first event
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

                # Archive session (keep last N sessions for history)
                device.past_sessions.insert(0, device.current_session)
                device.past_sessions = device.past_sessions[:MAX_PAST_SESSIONS]
            device.current_session = None

        elif device.current_session:
            # Mid-session event (pop_result, lvl_complete)
            device.current_session.events.append(data)


def check_device_timeouts() -> None:
    """Background watchdog thread to detect offline devices.

    Marks devices as "offline" if no MQTT message received within DEVICE_TIMEOUT_MS.
    Catches cases where agent crashes without sending disconnect message.
    """
    while True:
        time.sleep(TIMEOUT_CHECK_INTERVAL)
        now = int(time.time() * 1000)
        with DEV_LOCK:
            for device in devices.values():
                if device.status == "online" and (now - device.last_seen) > DEVICE_TIMEOUT_MS:
                    device.status = "offline"


def main() -> None:
    """Application entry point.

    1. Load persisted leaderboard from disk
    2. Subscribe to MQTT topics (wildcard '+' matches any device_id)
    3. Start background threads for MQTT and timeout watchdog
    4. Launch FastAPI server via uvicorn
    """
    init_leaderboard()

    # Subscribe to all device topics using MQTT wildcards
    topics = ["whac/+/game_events", "whac/+/state"]
    client = subscribe(topics, handle_message)

    # Daemon threads auto-terminate when main exits
    threading.Thread(target=client.loop_forever, daemon=True).start()
    threading.Thread(target=check_device_timeouts, daemon=True).start()

    uvicorn.run("dashboard.app:app", host="0.0.0.0", port=APP_PORT, root_path=APP_ROOT_PATH)  # noqa: S104


if __name__ == "__main__":
    main()
