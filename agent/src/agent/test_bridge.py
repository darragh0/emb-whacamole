import json
import threading
import time
import unittest

from .bridge import Bridge, COMMAND_TOPIC, GAME_EVENTS_TOPIC, STATUS_TOPIC, TELEMETRY_TOPIC


class FakeMQTTClient:
    def __init__(self) -> None:
        self.published = []
        self.subscriptions = []

    def publish(self, topic, payload=None, qos=0):
        self.published.append((topic, payload, qos))

        class Result:
            rc = 0

        return Result()

    def subscribe(self, topic, qos=0):
        self.subscriptions.append((topic, qos))


class FakeSerial:
    def __init__(self) -> None:
        self.written = []

    def write(self, data: bytes):
        self.written.append(data)


class LineSerial:
    def __init__(self, lines):
        self.lines = lines

    def readline(self):
        if self.lines:
            return self.lines.pop(0)
        time.sleep(0.01)
        return b""


class BridgeTests(unittest.TestCase):
    def test_game_event_from_uart_publishes_to_mqtt(self):
        mqtt = FakeMQTTClient()
        bridge = Bridge(serial_port="dummy", device_id="dev1", mqtt_client=mqtt)
        bridge._handle_uart_message(
            {
                "event_type": "pop_result",
                "mole_id": 3,
                "outcome": "hit",
                "reaction_ms": 120,
                "lives": 4,
                "lvl": 2,
            }
        )

        topic, payload, qos = mqtt.published[0]
        self.assertEqual(topic, GAME_EVENTS_TOPIC.format(device_id="dev1"))
        body = json.loads(payload)
        self.assertEqual(body["pop"], 3)
        self.assertEqual(body["level"], 2)
        self.assertEqual(body["outcome"], "HIT")
        self.assertEqual(body["lives_left"], 4)
        self.assertIn("ts", body)
        self.assertEqual(qos, 1)

    def test_status_and_telemetry_routes(self):
        mqtt = FakeMQTTClient()
        bridge = Bridge(serial_port="dummy", device_id="dev2", mqtt_client=mqtt)

        bridge._handle_uart_message(
            {"type": "status", "state": "playing", "level": 1, "pop_index": 2, "lives_left": 5, "ts": 42}
        )
        bridge._handle_uart_message(
            {"type": "telemetry", "sensor": "heart_rate", "samples": [80, 81], "ts": 99}
        )

        status_topic, status_payload, _ = mqtt.published[0]
        tele_topic, tele_payload, _ = mqtt.published[1]

        self.assertEqual(status_topic, STATUS_TOPIC.format(device_id="dev2"))
        status = json.loads(status_payload)
        self.assertEqual(status["state"], "playing")
        self.assertEqual(status["level"], 1)
        self.assertEqual(status["pop_index"], 2)

        self.assertEqual(tele_topic, TELEMETRY_TOPIC.format(device_id="dev2", sensor="heart_rate"))
        telemetry = json.loads(tele_payload)
        self.assertEqual(telemetry["sensor"], "heart_rate")
        self.assertEqual(telemetry["samples"], [80, 81])

    def test_mqtt_command_translates_to_uart_lines(self):
        mqtt = FakeMQTTClient()
        ser = FakeSerial()
        bridge = Bridge(serial_port="dummy", device_id="dev3", mqtt_client=mqtt)
        bridge._serial = ser

        bridge._handle_command_payload(
            json.dumps({"config": {"pause": True, "set_pop_duration": 900, "set_lives": 6}})
        )
        # Include direct command as well.
        bridge._handle_command_payload(json.dumps({"command": "resume"}))
        # Legacy single-byte pause
        bridge._handle_command_payload("P")

        lines = [line.decode("utf-8").strip() for line in ser.written]
        # Raw 'P' writes remain raw bytes, not JSON lines
        raw_entries = [b for b in ser.written if b == b"P"]
        json_entries = [line for line in lines if line != ""]

        self.assertGreaterEqual(len(raw_entries), 2)  # pause + resume mapped to P
        self.assertIn(json.dumps({"command": "set_pop_duration", "value": 900}), json_entries)
        self.assertIn(json.dumps({"command": "set_lives", "value": 6}), json_entries)

    def test_invalid_uart_json_is_ignored(self):
        mqtt = FakeMQTTClient()
        bridge = Bridge(serial_port="dummy", device_id="dev4", mqtt_client=mqtt)
        bridge._serial = LineSerial([b'{"broken": \n'])

        t = threading.Thread(target=bridge._uart_loop, daemon=True)
        t.start()
        time.sleep(0.05)
        bridge._stop_event.set()
        t.join(timeout=1.0)

        self.assertEqual(mqtt.published, [])


if __name__ == "__main__":
    unittest.main()
