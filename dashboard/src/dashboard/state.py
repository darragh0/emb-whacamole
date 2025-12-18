"""
Shared in-memory state between MQTT handler and API endpoints.

Thread Safety:
    All access to `devices` dict must be protected by DEV_LOCK.
    MQTT handler thread and FastAPI request handlers run concurrently.

Data Flow:
    MQTT messages -> handle_message() -> updates DeviceState
    API requests  -> get_devices()    -> reads DeviceState
"""

import threading
from dataclasses import dataclass, field
from typing import Any, Final

from dashboard.types import DevGameState, DevStatus

# Number of completed sessions to retain per device (for session history display)
MAX_PAST_SESSIONS: Final = 5

# Global lock protecting the devices dictionary (multiple threads access it)
DEV_LOCK: Final = threading.Lock()


@dataclass
class Session:
    """
    Tracks a single game session from session_start to session_end.

    Events are accumulated as they arrive from the device. Score is
    calculated from events when session ends.
    """
    events: list[dict[str, Any]] = field(default_factory=list)
    started_at: int = 0   # Unix timestamp (ms)
    ended_at: int = 0     # Unix timestamp (ms)
    won: bool | None = None


@dataclass
class DeviceState:
    """
    In-memory state for a single Whac-A-Mole device.

    Auto-discovered when first message is received from a device.
    Tracks connection status, game state, and session history.
    """
    device_id: str                                           # Unique ID from chip USN
    status: DevStatus = "offline"                            # online/offline/serial_error
    game_state: DevGameState = "idle"                        # idle/playing
    last_seen: int = 0                                       # Last MQTT message timestamp (ms)
    current_session: Session | None = None                   # Active session (if playing)
    past_sessions: list[Session] = field(default_factory=list)  # Recent completed sessions


# Global device registry - keyed by device_id
# Protected by DEV_LOCK for thread safety
devices: dict[str, DeviceState] = {}
