from dataclasses import asdict
from importlib.resources import files
from pathlib import Path
from typing import Any, Final

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from dashboard.env import APP_ROOT_PATH
from dashboard.leaderboard import get_leaderboard
from dashboard.mqtt import pub_cmd
from dashboard.state import DEV_LOCK, devices
from dashboard.types import StatusOk

LVL_MIN: Final = 1
LVL_MAX: Final = 8

STATIC_DIR: Final = Path(str(files("dashboard") / "static"))
BASE_TAG: Final = f'<base href="{APP_ROOT_PATH}/">' if APP_ROOT_PATH else ""

app: Final = FastAPI()

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
async def dashboard() -> HTMLResponse:
    html = (STATIC_DIR / "html" / "dashboard.html").read_text()
    html = html.replace("<head>", f"<head>\n  {BASE_TAG}", 1) if BASE_TAG else html
    return HTMLResponse(html)


@app.get("/devices")
async def get_devices() -> list[dict[str, Any]]:
    with DEV_LOCK:
        return [asdict(dev) for dev in devices.values()]


@app.get("/leaderboard")
async def get_leaderboard_endpoint() -> list[dict[str, Any]]:
    return get_leaderboard()


@app.post("/command/{device_id}/pause")
async def post_pause_command(device_id: str) -> StatusOk:
    return pub_cmd(device_id, "P")


@app.post("/command/{device_id}/reset")
async def post_reset_command(device_id: str) -> StatusOk:
    return pub_cmd(device_id, "R")


@app.post("/command/{device_id}/start")
async def post_start_command(device_id: str) -> StatusOk:
    return pub_cmd(device_id, "S")


@app.post("/command/{device_id}/level/{level}")
async def post_level_command(device_id: str, level: int) -> StatusOk:
    if level < LVL_MIN or level > LVL_MAX:
        raise HTTPException(status_code=400, detail="Level must be between 1 and 8")

    return pub_cmd(device_id, str(level))
