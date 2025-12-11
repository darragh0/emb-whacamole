"""Shared state between MQTT handler and API endpoints."""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Any, Final, Literal

MAX_PAST_SESSIONS: Final = 5


@dataclass
class Session:
    """Tracks a game session."""

    events: list[dict[str, Any]] = field(default_factory=list)
    started_at: int = 0
    ended_at: int = 0
    won: bool | None = None


@dataclass
class DeviceState:
    """Tracks state of a device."""

    device_id: str
    status: Literal["online", "serial_error", "offline"] = "online"
    game_state: Literal["playing", "idle"] = "idle"
    last_seen: int = 0
    current_session: Session | None = None
    past_sessions: list[Session] = field(default_factory=list)


devices: dict[str, DeviceState] = {}
devices_lock = threading.Lock()
