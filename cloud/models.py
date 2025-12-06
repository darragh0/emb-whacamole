from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class ReactionEvent(BaseModel):
    """Single mole appearance and response."""

    mole: int = Field(ge=0, le=7)
    hit: bool
    reaction_ms: Optional[int] = Field(default=None, ge=0)
    score_delta: int = 0
    ts: datetime


class GameSession(BaseModel):
    """Full game session as reported by the device."""

    model_config = ConfigDict(extra="ignore")  # Allow firmware to add fields without breaking.

    session_id: str
    device_id: str
    player: str = "anon"
    difficulty: str = "normal"
    duration_ms: Optional[int] = Field(default=None, ge=0)
    started_at: datetime = Field(default_factory=datetime.utcnow)
    ended_at: Optional[datetime] = None
    total_score: int = 0
    events: List[ReactionEvent] = Field(default_factory=list)
    sensors: Dict[str, Any] = Field(default_factory=dict)
    notes: Optional[str] = None


class ConfigUpdate(BaseModel):
    """POST body for updating defaults or per-device configuration."""

    device_id: Optional[str] = None
    config: Dict[str, Any]


class DeviceConfig(BaseModel):
    """Response wrapper for configuration requests."""

    device_id: str
    config: Dict[str, Any]


class LeaderboardEntry(BaseModel):
    player: str
    best_score: int
    average_score: float
    sessions: int
    last_played: Optional[datetime] = None


class Stats(BaseModel):
    """Lightweight stats for dashboards."""

    total_sessions: int
    total_players: int
    best_score: Optional[int]
    average_score: Optional[float]


class GamePopEvent(BaseModel):
    """Per-pop live event sent during gameplay."""

    model_config = ConfigDict(extra="ignore")

    device_id: Optional[str] = None
    pop: int = Field(ge=0)
    level: int = Field(ge=0)
    outcome: str
    reaction_ms: int = Field(ge=0)
    lives_left: int = Field(ge=0)
    ts: int = Field(ge=0)  # ms since epoch


class StatusMessage(BaseModel):
    """Heartbeat/status published every few seconds."""

    model_config = ConfigDict(extra="ignore")

    device_id: Optional[str] = None
    state: str
    level: int = Field(ge=0)
    pop_index: int = Field(ge=0)
    lives_left: int = Field(ge=0)
    ts: int = Field(ge=0)


class TelemetryBatch(BaseModel):
    """Small batch of sensor readings."""

    model_config = ConfigDict(extra="ignore")

    device_id: Optional[str] = None
    samples: List
    ts: int = Field(ge=0)
