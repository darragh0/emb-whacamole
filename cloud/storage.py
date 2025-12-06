from __future__ import annotations

import json
import os
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import fcntl

from models import GamePopEvent, GameSession, LeaderboardEntry, Stats, StatusMessage, TelemetryBatch

LIVE_EVENT_LIMIT = 200
TELEMETRY_LIMIT = 200


class DataStore:
    """
    Lightweight JSON-backed store so the backend can run on small servers.
    This is intentionally simple: in-memory list with periodic writes to disk.
    """

    def __init__(self, path: Path | str | None = None) -> None:
        base = Path(__file__).parent
        self.path = Path(path) if path else base / "data" / "store.json"
        self.sessions: List[GameSession] = []
        self.live_events: Dict[str, List[GamePopEvent]] = {}
        self.status: Dict[str, StatusMessage] = {}
        self.telemetry: Dict[Tuple[str, str], List[TelemetryBatch]] = {}
        self._lock = threading.Lock()
        self.load()

    @contextmanager
    def _file_lock(self, mode: str):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, mode) as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            yield f
            f.flush()
            os.fsync(f.fileno())
            fcntl.flock(f, fcntl.LOCK_UN)

    def load(self) -> None:
        if not self.path.exists():
            self.sessions = []
            return
        with self._file_lock("r") as f:
            raw = json.load(f)
            self.sessions = [GameSession.model_validate(item) for item in raw]

    def save(self) -> None:
        payload = [s.model_dump(mode="json") for s in self.sessions]
        with self._file_lock("w") as f:
            json.dump(payload, f, indent=2)

    def add_session(self, session: GameSession) -> None:
        """Insert or replace a session keyed by (session_id, device_id)."""
        with self._lock:
            for idx, existing in enumerate(self.sessions):
                if (
                    existing.session_id == session.session_id
                    and existing.device_id == session.device_id
                ):
                    self.sessions[idx] = session
                    self.save()
                    return
            self.sessions.append(session)
            self.save()

    def _append_bounded(self, buf: List, item, limit: int) -> None:
        buf.append(item)
        if len(buf) > limit:
            # Drop oldest to cap memory.
            del buf[0 : len(buf) - limit]

    def add_game_event(self, device_id: str, event: GamePopEvent) -> None:
        """Store recent live events per device (not persisted to disk)."""
        with self._lock:
            buf = self.live_events.setdefault(device_id, [])
            self._append_bounded(buf, event, LIVE_EVENT_LIMIT)

    def recent_game_events(self, device_id: str, limit: int = 50) -> List[GamePopEvent]:
        with self._lock:
            if device_id not in self.live_events:
                return []
            return list(self.live_events[device_id][-limit:])

    def recent_all_game_events(self, limit: int = 200) -> List[GamePopEvent]:
        with self._lock:
            collected: List[GamePopEvent] = []
            for events in self.live_events.values():
                collected.extend(events)
            collected.sort(key=lambda e: e.ts)
            return collected[-limit:]

    def update_status(self, device_id: str, status: StatusMessage) -> None:
        with self._lock:
            self.status[device_id] = status

    def get_status(self, device_id: str) -> Optional[StatusMessage]:
        with self._lock:
            return self.status.get(device_id)

    def add_telemetry(self, device_id: str, sensor: str, batch: TelemetryBatch) -> None:
        key = (device_id, sensor)
        with self._lock:
            buf = self.telemetry.setdefault(key, [])
            self._append_bounded(buf, batch, TELEMETRY_LIMIT)

    def recent_telemetry(
        self, device_id: str, sensor: str, limit: int = 50
    ) -> List[TelemetryBatch]:
        key = (device_id, sensor)
        with self._lock:
            if key not in self.telemetry:
                return []
            return list(self.telemetry[key][-limit:])

    def leaderboard(self, limit: int = 10) -> List[LeaderboardEntry]:
        with self._lock:
            by_player: Dict[str, Dict[str, float | int | None]] = {}
            for session in self.sessions:
                player = session.player or "anon"
                metrics = by_player.setdefault(
                    player,
                    {"best": None, "total": 0, "count": 0, "last": None},
                )
                metrics["total"] += session.total_score
                metrics["count"] += 1
                metrics["best"] = (
                    session.total_score
                    if metrics["best"] is None
                    else max(metrics["best"], session.total_score)
                )
                if metrics["last"] is None or (
                    session.ended_at and session.ended_at > metrics["last"]
                ):
                    metrics["last"] = session.ended_at or session.started_at

            entries = [
                LeaderboardEntry(
                    player=player,
                    best_score=int(metrics["best"]) if metrics["best"] is not None else 0,
                    average_score=metrics["total"] / metrics["count"]
                    if metrics["count"]
                    else 0.0,
                    sessions=metrics["count"],
                    last_played=metrics["last"],
                )
                for player, metrics in by_player.items()
            ]
            entries.sort(key=lambda e: e.best_score, reverse=True)
            return entries[:limit]

    def stats(self) -> Stats:
        with self._lock:
            if not self.sessions:
                return Stats(
                    total_sessions=0,
                    total_players=0,
                    best_score=None,
                    average_score=None,
                )
            best = max(s.total_score for s in self.sessions)
            average = sum(s.total_score for s in self.sessions) / len(self.sessions)
            players = {s.player or "anon" for s in self.sessions}
            return Stats(
                total_sessions=len(self.sessions),
                total_players=len(players),
                best_score=best,
                average_score=average,
            )
