"""Dashboard API."""

from dataclasses import asdict
from typing import Any, Final

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from paho.mqtt import publish
from starlette.responses import FileResponse

from cloud.mqtt import BROKER, PORT
from cloud.state import devices, devices_lock

LVL_MIN: Final = 1
LVL_MAX: Final = 8

app: Final = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def dashboard() -> FileResponse:
    return FileResponse("static/html/dashboard.html")


@app.get("/devices")
async def get_devices() -> list[dict[str, Any]]:
    with devices_lock:
        return [asdict(dev) for dev in devices.values()]


@app.post("/command/{device_id}/pause")
async def post_pause_command(device_id: str) -> dict[str, bool]:
    publish.single(
        f"whac/{device_id}/commands",
        "P",
        hostname=BROKER,
        port=PORT,
        qos=2,
    )
    return {"ok": True}


@app.post("/command/{device_id}/reset")
async def post_reset_command(device_id: str) -> dict[str, bool]:
    publish.single(
        f"whac/{device_id}/commands",
        "R",
        hostname=BROKER,
        port=PORT,
        qos=2,
    )
    return {"ok": True}


@app.post("/command/{device_id}/start")
async def post_start_command(device_id: str) -> dict[str, bool]:
    publish.single(
        f"whac/{device_id}/commands",
        "S",
        hostname=BROKER,
        port=PORT,
        qos=2,
    )

    return {"ok": True}


@app.post("/command/{device_id}/level/{level}")
async def post_level_command(device_id: str, level: int) -> dict[str, bool]:
    if level < LVL_MIN or level > LVL_MAX:
        raise HTTPException(status_code=400, detail="Level must be between 1 and 8")

    publish.single(
        f"whac/{device_id}/commands",
        str(level),
        hostname=BROKER,
        port=PORT,
        qos=2,
    )

    return {"ok": True}
