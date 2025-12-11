"""Shared state between MQTT handler and API endpoints."""

import threading
from dataclasses import dataclass, field
from typing import Any, Final

from dashboard.types import DevGameState, DevStatus

MAX_PAST_SESSIONS: Final = 5
DEV_LOCK: Final = threading.Lock()


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
    status: DevStatus = "offline"
    game_state: DevGameState = "idle"
    last_seen: int = 0
    current_session: Session | None = None
    past_sessions: list[Session] = field(default_factory=list)


devices: dict[str, DeviceState] = {}
