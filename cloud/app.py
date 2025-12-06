"""Leaderboard UI and stats for the Whac-a-Mole embedded project.
Device ingestion happens over MQTT (see mqtt_worker.py)."""

import asyncio
import json
from datetime import datetime
from typing import Optional

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse

from storage import DataStore

app = FastAPI(
    title="Whac-a-Mole Cloud Backend",
    description="MQTT-first backend with an optional web leaderboard for humans.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

store = DataStore()


@app.get("/api/health")
def health() -> dict:
    stats = store.stats()
    return {
        "status": "ok",
        "server_time": datetime.utcnow(),
        "sessions": stats.total_sessions,
    }


@app.get("/api/leaderboard")
def get_leaderboard(limit: int = 10):
    """Returns top scores aggregated by player."""
    return store.leaderboard(limit=limit)


@app.get("/api/stats")
def get_stats():
    return store.stats()


@app.get("/leaderboard", response_class=HTMLResponse)
def leaderboard_page(request: Request, limit: int = 20) -> HTMLResponse:
    entries = store.leaderboard(limit=limit)
    stats = store.stats()
    avg_display = f"{stats.average_score:.1f}" if stats.average_score is not None else "N/A"
    best_display = stats.best_score if stats.best_score is not None else "N/A"
    rows = "\n".join(
        f"<tr><td>{idx}</td><td>{e.player}</td><td>{e.best_score}</td>"
        f"<td>{e.average_score:.1f}</td><td>{e.sessions}</td>"
        f"<td>{e.last_played.isoformat() if e.last_played else 'N/A'}</td></tr>"
        for idx, e in enumerate(entries, start=1)
    )
    html = f"""
    <!doctype html>
    <html>
    <head>
        <meta charset="utf-8"/>
        <title>Whac-a-Mole Leaderboard</title>
        <style>
            body {{
                font-family: 'Segoe UI', sans-serif;
                background: linear-gradient(120deg, #0f172a, #1f2937);
                color: #e2e8f0;
                padding: 24px;
            }}
            .card {{
                background: rgba(255, 255, 255, 0.06);
                border-radius: 12px;
                padding: 16px 20px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.25);
                margin-bottom: 16px;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin-top: 8px;
            }}
            th, td {{
                padding: 10px;
                border-bottom: 1px solid rgba(255,255,255,0.08);
                text-align: left;
            }}
            th {{
                text-transform: uppercase;
                letter-spacing: 0.08em;
                font-size: 12px;
                color: #cbd5e1;
            }}
            tr:hover td {{
                background: rgba(255,255,255,0.04);
            }}
            h1 {{ margin: 0; }}
            .stats span {{
                display: inline-block;
                margin-right: 16px;
                font-size: 14px;
                color: #cbd5e1;
            }}
        </style>
    </head>
    <body>
        <div class="card">
            <h1>Whac-a-Mole Leaderboard</h1>
            <div class="stats">
                <span>Sessions: {stats.total_sessions}</span>
                <span>Players: {stats.total_players}</span>
                <span>Best: {best_display}</span>
                <span>Average: {avg_display}</span>
            </div>
        </div>
        <div class="card">
            <table>
                <thead><tr><th>#</th><th>Player</th><th>Best</th><th>Avg</th><th>Sessions</th><th>Last Played</th></tr></thead>
                <tbody>
                    {rows}
                </tbody>
            </table>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html)


@app.get("/api/events/stream")
async def stream_events(device_id: Optional[str] = None):
    """
    Optional Server-Sent Events endpoint streaming recent live game_events.
    Works best when mqtt_worker and this app share the same DataStore instance
    (e.g. same process) or when game_events are fed into this process.
    """

    async def event_generator():
        last_ts = 0
        while True:
            events = (
                store.recent_game_events(device_id, limit=200)
                if device_id
                else store.recent_all_game_events(limit=200)
            )
            new_events = [e for e in events if e.ts > last_ts]
            if new_events:
                last_ts = max(e.ts for e in new_events)
                for event in new_events:
                    payload = {
                        "device_id": event.device_id or device_id,
                        "pop": event.pop,
                        "level": event.level,
                        "outcome": event.outcome,
                        "reaction_ms": event.reaction_ms,
                        "lives_left": event.lives_left,
                        "ts": event.ts,
                    }
                    yield f"data: {json.dumps(payload)}\n\n"
            await asyncio.sleep(1.0)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
