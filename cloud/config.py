from __future__ import annotations

import json
import os
import threading
from contextlib import contextmanager
from copy import deepcopy
from pathlib import Path
from typing import Dict

import fcntl

from models import ConfigUpdate, DeviceConfig


DEFAULT_CONFIG: Dict[str, object] = {
    "difficulty": "normal",
    "game_duration_ms": 60_000,
    "mole_up_ms": 1_200,
    "send_events": True,
    "set_level": None,
    "set_lives": None,
    "set_pop_duration": None,
    "pause": False,
    "resume": False,
    "sensor_config": {},
}


class ConfigManager:
    """
    Holds the latest configuration for devices.
    Stored on disk so boards can reboot without losing settings.
    """

    def __init__(self, path: Path | str | None = None) -> None:
        base = Path(__file__).parent
        self.path = Path(path) if path else base / "data" / "config.json"
        self.default_config: Dict[str, object] = deepcopy(DEFAULT_CONFIG)
        self.device_overrides: Dict[str, Dict[str, object]] = {}
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
            return
        with self._file_lock("r") as f:
            raw = json.load(f)
            self.default_config = raw.get("default_config", deepcopy(DEFAULT_CONFIG))
            self.device_overrides = raw.get("device_overrides", {})

    def save(self) -> None:
        payload = {
            "default_config": self.default_config,
            "device_overrides": self.device_overrides,
        }
        with self._file_lock("w") as f:
            json.dump(payload, f, indent=2)

    def get(self, device_id: str | None) -> DeviceConfig:
        with self._lock:
            merged = deepcopy(self.default_config)
            if device_id and device_id in self.device_overrides:
                merged.update(self.device_overrides[device_id])
            return DeviceConfig(device_id=device_id or "unknown", config=merged)

    def update(self, update: ConfigUpdate) -> DeviceConfig:
        with self._lock:
            if update.device_id:
                override = self.device_overrides.get(update.device_id, {})
                override.update(update.config)
                self.device_overrides[update.device_id] = override
            else:
                self.default_config.update(update.config)
            self.save()
            return self.get(update.device_id)
