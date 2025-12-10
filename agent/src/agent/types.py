from __future__ import annotations

from typing import Literal, TypedDict

type DevStatus = Literal["online", "serial_error", "offline"]


class StandardPayload(TypedDict):
    device_id: str
    ts: int


class StatusPayload(StandardPayload):
    status: DevStatus
