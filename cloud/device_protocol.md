# Device <-> Cloud Protocol (MQTT-first)

The device communicates only over MQTT. HTTP is reserved for human-facing pages (leaderboard UI).

## Broker
- Host/port configured via `MQTT_BROKER` / `MQTT_PORT` (defaults: `localhost:1883`).
- Use QoS 1 for reliability on commands/config. Telemetry/events can use QoS 0 or 1; keep payloads small.
- Only the commands/config topic is retained so reconnecting devices immediately get the latest settings.

## Topics
- Publish full game sessions (end-of-game summary): `whac/<device_id>/events`
- Publish per-pop live events: `whac/<device_id>/game_events`
- Publish optional sensor telemetry: `whac/<device_id>/telemetry/heart_rate`, `whac/<device_id>/telemetry/accel` (extend as needed)
- Publish heartbeat/status: `whac/<device_id>/status`
- Request config/commands: `whac/<device_id>/config_request`
- Receive commands/config: `whac/<device_id>/commands` (published by backend, retained)

`<device_id>` is an alphanumeric string set by firmware (e.g., `max-board-01`).

## Payload: game session (publish to `whac/<device_id>/events`)
JSON object validated by `GameSession`:
```json
{
  "session_id": "uuid-or-counter",
  "device_id": "max-board-01",
  "player": "alice",
  "difficulty": "normal",
  "duration_ms": 60000,
  "started_at": "2024-05-24T12:00:00Z",
  "ended_at": "2024-05-24T12:01:00Z",
  "total_score": 12,
  "events": [
    { "mole": 3, "hit": true, "reaction_ms": 420, "score_delta": 1, "ts": "2024-05-24T12:00:05.123Z" },
    { "mole": 6, "hit": false, "reaction_ms": null, "score_delta": 0, "ts": "2024-05-24T12:00:07.800Z" }
  ],
  "sensors": { "heart_rate_bpm": 95 }
}
```
- `session_id`: UUID or incrementing integer (used for de-duplication with `device_id`).
- `events`: optional; send only `total_score` if bandwidth is tight.
- Extra keys are ignored (backend is forward-compatible).

## Payload: per-pop event (publish to `whac/<device_id>/game_events`)
Short JSON message per mole appearance / button press:
```json
{
  "pop": 3,
  "level": 2,
  "outcome": "HIT",
  "reaction_ms": 420,
  "lives_left": 4,
  "ts": 1717156255123
}
```
- `outcome`: one of `HIT`, `LATE`, `MISS`.
- `ts`: milliseconds since epoch (UTC). Firmware can also send ISO-8601 if easier.
- Keep payload small; QoS 0 or 1 is fine.

## Payload: heartbeat/status (publish to `whac/<device_id>/status`)
Sent every few seconds while idle or playing:
```json
{
  "state": "playing",
  "level": 2,
  "pop_index": 7,
  "lives_left": 4,
  "ts": 1717156255123
}
```
- `state`: `idle | playing | paused`.

## Payload: telemetry (publish to `whac/<device_id>/telemetry/...`)
Examples (shape can evolve; keep batches small, ~5–10 Hz):
```json
{ "samples": [82, 83, 82], "ts": 1717156255123 }
```
```json
{ "samples": [[0.01, 0.02, 1.01], [-0.02, 0.01, 0.99]], "ts": 1717156255123 }
```
- Backend stores recent slices in a ring buffer; it does not retain unbounded telemetry.

## Payload: config request (publish to `whac/<device_id>/config_request`)
Empty payload is fine. Backend responds on `whac/<device_id>/commands` (retained).

## Payload: commands/config (backend publishes retained)
```json
{
  "device_id": "max-board-01",
  "config": {
    "difficulty": "normal",
    "game_duration_ms": 60000,
    "mole_up_ms": 1200,
    "send_events": true,
    "pause": false,
    "set_level": null,
    "set_lives": null,
    "set_pop_duration": null,
    "sensor_config": { "hr_hz": 5, "accel_hz": 10 }
  }
}
```
- Fields are optional. Examples:
  - `pause: true` then later `pause: false` (or `resume` flag) to resume.
  - `set_pop_duration: 900` to change mole-up time mid-game (ms).
  - `set_level: 3` to jump difficulty.
  - `set_lives: 6` to add/remove lives.
  - `set_send_events: false` to silence live streams if bandwidth is tight.
  - `sensor_config` to adjust telemetry rates on the fly.

## Notes for firmware
- Use QoS 1 on commands/config. Live streams can be QoS 0 or 1.
- Use ISO-8601 timestamps with `Z` for UTC.
- Always include `device_id` in payloads (backend also derives it from the topic).
- On reconnect, resubscribe to `whac/<device_id>/commands` to receive retained config.
- Keep live messages short; avoid blocking the game loop while publishing.

## Demo flow (for assessors)
1. Start a game; watch `whac/<device_id>/game_events` drive live HIT/LATE/MISS on the UI (real-time acquisition).
2. From a terminal, send a mid-game command (real-time control), e.g.:
   ```bash
   mosquitto_pub -t "whac/max-board-01/commands" -m '{"config":{"set_pop_duration":800}}' -q 1 -r
   ```
   or pause/resume:
   ```bash
   mosquitto_pub -t "whac/max-board-01/commands" -m '{"config":{"pause":true}}' -q 1 -r
   mosquitto_pub -t "whac/max-board-01/commands" -m '{"config":{"pause":false}}' -q 1 -r
   ```
3. Finish the game; the full summary still lands on `whac/<device_id>/events` and updates the leaderboard.
