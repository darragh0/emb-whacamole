from typing import Literal, TypedDict


class SessionStartJson(TypedDict):
    event_type: Literal["session_start"]
    time: int


class PopResultJson(TypedDict):
    event_type: Literal["pop_result"]
    mole_id: int  # 0-7
    outcome: Literal["hit", "miss", "late"]
    reaction_ms: int
    lives: int
    lvl: int  # 1-8


class LevelCompleteJson(TypedDict):
    event_type: Literal["lvl_complete"]
    lvl: int  # 1-8


class SessionEndJson(TypedDict):
    event_type: Literal["session_end"]
    win: bool


class ApiOk(TypedDict):
    ok: bool


type GameEvent = SessionStartJson | PopResultJson | LevelCompleteJson | SessionEndJson
