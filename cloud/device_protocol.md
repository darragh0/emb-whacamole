# Device <-> Cloud Protocol (MQTT-first)

The device communicates only over MQTT. HTTP is reserved for human-facing pages (leaderboard UI).

## Broker
- Host/port configured via `MQTT_BROKER` / `MQTT_PORT` (defaults: `localhost:1883`).
- QoS 1 for reliability on all topics. Config messages are retained so reconnecting devices immediately get the latest settings.

## Topics
- Publish game sessions: `whac/<device_id>/events`
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
    "send_events": true
  }
}
```

## Notes for firmware
- Use QoS 1 on publishes and subscribes.
- Use ISO-8601 timestamps with `Z` for UTC.
- Always include `device_id` in payloads (backend also derives it from the topic).
- On reconnect, resubscribe to `whac/<device_id>/commands` to receive retained config.
