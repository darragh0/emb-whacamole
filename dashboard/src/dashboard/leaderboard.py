"""Leaderboard persistence and scoring logic.

Maintains top scores across sessions, persisted to JSON file.
Thread-safe for concurrent access from MQTT handler and API.
"""

import json
import threading
from dataclasses import asdict, dataclass
from typing import Any, Final

from .env import DATA_DIR

# Persistent storage location
LEADERBOARD_FILE: Final = DATA_DIR / "leaderboard.json"

# Thread safety for concurrent access
LEADERBOARD_LOCK: Final = threading.Lock()

# Keep only top N scores
MAX_ENTRIES: Final = 5


@dataclass
class LeaderboardEntry:
    """Single leaderboard entry with score, device, and timestamp."""

    score: int
    device_id: str
    timestamp: int  # Unix timestamp (ms) when session ended


# In-memory leaderboard (loaded from disk at startup)
leaderboard: list[LeaderboardEntry] = []


def calculate_score(events: list[dict[str, Any]]) -> int:
    """Calculate score from session events (100 * level * speed_bonus per hit)."""
    score = 0
    for event in events:
        if event.get("event_type") == "pop_result" and event.get("outcome") == "hit":
            lvl = event.get("lvl", 1)
            reaction_ms = event.get("reaction_ms", 1000)
            speed_bonus = max(0.5, 2 - (reaction_ms / 1000))
            score += int(100 * lvl * speed_bonus)
    return score


def add_entry(device_id: str, score: int, timestamp: int) -> None:
    """Add new score entry, maintaining sorted order and max size.

    Called when a game session ends. Automatically persists to disk.
    """
    with LEADERBOARD_LOCK:
        entry = LeaderboardEntry(score=score, device_id=device_id, timestamp=timestamp)
        leaderboard.append(entry)
        leaderboard.sort(key=lambda e: e.score, reverse=True)
        del leaderboard[MAX_ENTRIES:]  # Keep only top N
        _save()


def get_leaderboard() -> list[dict[str, Any]]:
    """Return leaderboard as list of dicts (for JSON serialization)."""
    with LEADERBOARD_LOCK:
        return [asdict(e) for e in leaderboard]


def _save() -> None:
    """Persist current leaderboard to JSON file."""
    data = [asdict(e) for e in leaderboard]
    LEADERBOARD_FILE.write_text(json.dumps(data, indent=2))


def init() -> None:
    """Load leaderboard from disk at startup.

    Must be called once before accepting requests. Creates empty
    leaderboard if file doesn't exist.
    """
    global leaderboard  # noqa: PLW0603
    if LEADERBOARD_FILE.exists():
        data = json.loads(LEADERBOARD_FILE.read_text())
        leaderboard = [LeaderboardEntry(**e) for e in data]
