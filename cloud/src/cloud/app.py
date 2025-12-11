"""Dashboard API."""

from dataclasses import asdict
from typing import Any, Final

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.responses import FileResponse

from cloud.mqtt import send_pause
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
