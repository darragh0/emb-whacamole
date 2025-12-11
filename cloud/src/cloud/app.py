"""Dashboard API."""

from dataclasses import asdict
from typing import Any, Final

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from starlette.responses import FileResponse

from cloud.mqtt import send_level, send_pause, send_reset, send_start
from cloud.state import devices, devices_lock

app: Final = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def dashboard() -> FileResponse:
    return FileResponse("static/html/dashboard.html")


@app.get("/devices")
async def get_devices() -> list[dict[str, Any]]:
    with devices_lock:
        return [asdict(dev) for dev in devices.values()]


@app.post("/command/{device_id}")
async def post_command(device_id: str) -> dict[str, bool]:
    # can add more commands later, but just pause for now ig
    send_pause(device_id)
    return {"ok": True}


@app.post("/command/{device_id}/reset")
async def post_reset_command(device_id: str) -> dict[str, bool]:
    send_reset(device_id)
    return {"ok": True}


@app.post("/command/{device_id}/start")
async def post_start_command(device_id: str) -> dict[str, bool]:
    send_start(device_id)
    return {"ok": True}


@app.post("/command/{device_id}/level/{level}")
async def post_level_command(device_id: str, level: int) -> dict[str, bool]:
    if level < 1 or level > 8:
        raise HTTPException(status_code=400, detail="Level must be between 1 and 8")

    send_level(device_id, level)
    return {"ok": True}
