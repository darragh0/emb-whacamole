import json
import threading
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Final

LEADERBOARD_FILE: Final = Path("data/leaderboard.json")
LEADERBOARD_LOCK: Final = threading.Lock()
MAX_ENTRIES: Final = 5


@dataclass
class LeaderboardEntry:
    score: int
    device_id: str
    timestamp: int


leaderboard: list[LeaderboardEntry] = []


def calculate_score(events: list[dict[str, Any]]) -> int:
    """getting score from session events."""
    score = 0
    lives_remaining = 5
    level_hits = {}

    for event in events:
        event_type = event.get("event_type")

        if event_type == "pop_result":
            outcome = event.get("outcome")
            if outcome == "hit":
                lvl = event.get("lvl", 1)
                reaction_ms = event.get("reaction_ms", 1000)

                base_points = 100
                level_multiplier = lvl
                speed_bonus = max(0.5, 2 - (reaction_ms / 1000))

                score += int(base_points * level_multiplier * speed_bonus)

                level_hits.setdefault(lvl, {"hits": 0, "misses": 0})
                level_hits[lvl]["hits"] += 1
            elif outcome == "miss":
                lvl = event.get("lvl", 1)
                level_hits.setdefault(lvl, {"hits": 0, "misses": 0})
                level_hits[lvl]["misses"] += 1
                lives_remaining = event.get("lives", lives_remaining)

        elif event_type == "lvl_complete":
            lvl = event.get("lvl", 1)
            if lvl in level_hits and level_hits[lvl]["misses"] == 0:
                score += 500 * lvl

    lives_bonus = 1 + (lives_remaining * 0.1)
    return int(score * lives_bonus)


def add_entry(device_id: str, score: int, timestamp: int) -> None:
    """persists this storage to the json"""
    with LEADERBOARD_LOCK:
        entry = LeaderboardEntry(score=score, device_id=device_id, timestamp=timestamp)
        leaderboard.append(entry)
        leaderboard.sort(key=lambda e: e.score, reverse=True)
        del leaderboard[MAX_ENTRIES:]
        _save()


def get_leaderboard() -> list[dict[str, Any]]:
    """Get current leaderboard."""
    with LEADERBOARD_LOCK:
        return [asdict(e) for e in leaderboard]


def _save() -> None:
    """Persist leaderboard to disk."""
    LEADERBOARD_FILE.parent.mkdir(parents=True, exist_ok=True)
    data = [asdict(e) for e in leaderboard]
    LEADERBOARD_FILE.write_text(json.dumps(data, indent=2))


def _load() -> None:
    """Load leaderboard from disk."""
    global leaderboard
    if LEADERBOARD_FILE.exists():
        data = json.loads(LEADERBOARD_FILE.read_text())
        leaderboard = [LeaderboardEntry(**e) for e in data]


_load()
