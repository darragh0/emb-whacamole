"""FastAPI REST API for the Whac-A-Mole dashboard.

Provides endpoints for:
    - Serving the dashboard HTML/JS frontend
    - Querying device state and leaderboard
    - Sending commands to devices via MQTT

Commands are forwarded to devices through MQTT pub/sub. The Python agent
subscribed to the device's command topic receives the command and writes
it to the embedded device via UART.
"""

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

# Game level boundaries (embedded device supports levels 1-8)
LVL_MIN: Final = 1
LVL_MAX: Final = 8

# Static files bundled with package (HTML, JS, CSS)
STATIC_DIR: Final = Path(str(files("dashboard") / "static"))

# Inject <base> tag for subpath deployment (e.g., behind reverse proxy)
BASE_TAG: Final = f'<base href="{APP_ROOT_PATH}/">' if APP_ROOT_PATH else ""

app: Final = FastAPI()

# Mount static directory for JS/CSS assets
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
async def dashboard() -> HTMLResponse:
    """Serve main dashboard HTML with injected base tag for subpath support."""
    html = (STATIC_DIR / "html" / "dashboard.html").read_text()
    html = html.replace("<head>", f"<head>\n  {BASE_TAG}", 1) if BASE_TAG else html
    return HTMLResponse(html)


@app.get("/devices")
async def get_devices() -> list[dict[str, Any]]:
    """Return all known devices with their current state (polled by frontend)."""
    with DEV_LOCK:
        return [asdict(dev) for dev in devices.values()]


@app.get("/leaderboard")
async def get_leaderboard_endpoint() -> list[dict[str, Any]]:
    """Return top scores (persisted to disk, survives restart)."""
    return get_leaderboard()


# === Command Endpoints ===
# Commands are published to MQTT topic: whac/<device_id>/cmd
# The Python agent subscribed to this topic forwards to UART


@app.post("/command/{device_id}/pause")
async def post_pause_command(device_id: str) -> StatusOk:
    """Toggle pause state on device. Sends 'P' command."""
    return pub_cmd(device_id, "P")


@app.post("/command/{device_id}/reset")
async def post_reset_command(device_id: str) -> StatusOk:
    """Reset game to initial state. Sends 'R' command."""
    return pub_cmd(device_id, "R")


@app.post("/command/{device_id}/start")
async def post_start_command(device_id: str) -> StatusOk:
    """Start a new game session. Sends 'S' command."""
    return pub_cmd(device_id, "S")


@app.post("/command/{device_id}/level/{level}")
async def post_level_command(device_id: str, level: int) -> StatusOk:
    """Set difficulty level (1-8). Sends digit command."""
    if level < LVL_MIN or level > LVL_MAX:
        raise HTTPException(status_code=400, detail="Level must be between 1 and 8")

    return pub_cmd(device_id, str(level))
