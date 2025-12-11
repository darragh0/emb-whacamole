from typing import Literal, TypedDict

type DevStatus = Literal["online", "serial_error", "offline"]
type DevGameState = Literal["playing", "idle"]


class StatusOk(TypedDict):
    ok: bool
