import json

from mqtt_worker import MQTTBackend
from storage import DataStore, LIVE_EVENT_LIMIT, TELEMETRY_LIMIT


def make_backend(tmp_path):
    store = DataStore(path=tmp_path / "store.json")
    backend = MQTTBackend("localhost", 1883, store=store)
    return backend, store


def test_handle_game_event_appends_and_truncates(tmp_path):
    backend, store = make_backend(tmp_path)
    for idx in range(LIVE_EVENT_LIMIT + 3):
        backend._handle_game_event(
            "dev1",
            json.dumps(
                {
                    "pop": idx,
                    "level": 1,
                    "outcome": "HIT",
                    "reaction_ms": 123,
                    "lives_left": 4,
                    "ts": idx,
                }
            ),
        )

    events = store.recent_game_events("dev1", limit=LIVE_EVENT_LIMIT + 10)
    assert len(events) == LIVE_EVENT_LIMIT
    # Oldest events should drop first.
    assert events[0].pop == 3
    assert events[-1].pop == LIVE_EVENT_LIMIT + 2
    # Device id is stamped from topic/device context.
    assert all(e.device_id == "dev1" for e in events)


def test_handle_status_and_telemetry(tmp_path):
    backend, store = make_backend(tmp_path)

    backend._handle_status(
        "dev2",
        json.dumps(
            {"state": "playing", "level": 2, "pop_index": 7, "lives_left": 4, "ts": 99}
        ),
    )
    status = store.get_status("dev2")
    assert status is not None
    assert status.state == "playing"
    assert status.pop_index == 7

    for idx in range(TELEMETRY_LIMIT + 5):
        backend._handle_telemetry(
            "dev2",
            "heart_rate",
            json.dumps({"samples": [80 + idx], "ts": idx}),
        )

    batches = store.recent_telemetry("dev2", "heart_rate", limit=TELEMETRY_LIMIT + 5)
    assert len(batches) == TELEMETRY_LIMIT
    assert batches[-1].samples == [80 + TELEMETRY_LIMIT + 4]
    assert all(b.device_id == "dev2" for b in batches)
