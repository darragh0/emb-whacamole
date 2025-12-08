"""Dashboard API."""

import json
from typing import Annotated, Final

from fastapi import FastAPI, Form
from fastapi.staticfiles import StaticFiles
from starlette.responses import FileResponse

from cloud.env import DATA_FILE
from cloud.types import ApiOk

from .mqtt import send_pause

app: Final = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

EVENTS_PER_PAGE: Final = 20


@app.get("/")
async def dashboard() -> FileResponse:
    """Return dashboard HTML."""
    return FileResponse("static/html/dashboard.html")


def read_events(limit: int = EVENTS_PER_PAGE) -> list[str]:
    """Read recent events (newest first).

    Optional Args:
        limit: No. events to return

    Returns:
        List of raw JSON strings
    """
    return [] if not DATA_FILE.is_file() else DATA_FILE.read_text().splitlines()[-limit:][::-1]


@app.get("/events")
async def get_events() -> list[str]:
    """Return recent events as JSON string array."""
    return read_events()


@app.post("/command/{device_id}")
async def post_command(device_id: str, command: Annotated[str, Form()]) -> ApiOk:
    """Send command to device via MQTT and log it.

    Args:
        device_id: Recipient device ID
        command: Command to send
    """

    DATA_FILE.parent.mkdir(exist_ok=True)
    with DATA_FILE.open("a") as f:
        f.write(json.dumps({"event_type": "command", "cmd": command}) + "\n")

    send_pause(device_id)
    return {"ok": True}
