"""
MQTT-first backend worker.
Listens for device events/config requests on MQTT and persists them via storage.py.
Sends commands/config responses back over MQTT command topics.
"""

import json
import os
import signal
import sys
import threading
import time
from typing import Optional

import paho.mqtt.client as mqtt

from config import ConfigManager
from models import ConfigUpdate, GameSession
from storage import DataStore

MQTT_BROKER = os.getenv("MQTT_BROKER", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
MQTT_KEEPALIVE = 30

# Topic templates
EVENTS_TOPIC = "whac/+/events"  # + matches device_id
CONFIG_REQ_TOPIC = "whac/+/config_request"
COMMAND_TOPIC_FMT = "whac/{device_id}/commands"


class MQTTBackend:
    """Handles MQTT subscriptions and message routing."""

    def __init__(self, broker: str, port: int) -> None:
        self.broker = broker
        self.port = port
        self.client = mqtt.Client()
        self.store = DataStore()
        self.config = ConfigManager()
        self._stop_event = threading.Event()
        self._setup_handlers()

    def _setup_handlers(self) -> None:
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_disconnect = self.on_disconnect

    def start(self) -> None:
        self.client.connect(self.broker, self.port, keepalive=MQTT_KEEPALIVE)
        self.client.loop_start()
        # Keep main thread alive until stopped.
        while not self._stop_event.is_set():
            time.sleep(0.5)

    def stop(self) -> None:
        self._stop_event.set()
        self.client.loop_stop()
        self.client.disconnect()

    def on_connect(self, client: mqtt.Client, userdata, flags, rc) -> None:
        if rc == 0:
            print(f"[mqtt] Connected to broker {self.broker}:{self.port}")
            client.subscribe(EVENTS_TOPIC, qos=1)
            client.subscribe(CONFIG_REQ_TOPIC, qos=1)
        else:
            print(f"[mqtt] Connect failed with code {rc}")

    def on_disconnect(self, client: mqtt.Client, userdata, rc) -> None:
        print(f"[mqtt] Disconnected (rc={rc}), reconnecting...")

    def on_message(self, client: mqtt.Client, userdata, msg: mqtt.MQTTMessage) -> None:
        topic = msg.topic
        payload = msg.payload.decode("utf-8")
        print(f"[mqtt] Received on {topic}: {payload}")
        try:
            device_id = self._extract_device_id(topic)
        except ValueError:
            print(f"[mqtt] Ignoring topic with no device id: {topic}")
            return

        if topic.endswith("/events"):
            self._handle_event(device_id, payload)
        elif topic.endswith("/config_request"):
            self._handle_config_request(device_id)

    def _extract_device_id(self, topic: str) -> str:
        parts = topic.split("/")
        if len(parts) < 3 or parts[0] != "whac":
            raise ValueError("invalid topic")
        return parts[1]

    def _handle_event(self, device_id: str, payload: str) -> None:
        try:
            data = json.loads(payload)
            # Ensure device_id is present to guard against mismatched payloads.
            data.setdefault("device_id", device_id)
            session = GameSession.model_validate(data)
        except Exception as exc:  # noqa: BLE001
            print(f"[mqtt] Failed to parse event payload: {exc}")
            return

        self.store.add_session(session)
        print(
            f"[mqtt] Stored session {session.session_id} for {session.device_id} score={session.total_score}"
        )

    def _handle_config_request(self, device_id: str) -> None:
        cfg = self.config.get(device_id)
        topic = COMMAND_TOPIC_FMT.format(device_id=device_id)
        payload = json.dumps(cfg.model_dump())
        # qos=1 to ensure delivery; retain so reconnecting devices get the latest config.
        result = self.client.publish(topic, payload=payload, qos=1, retain=True)
        if result.rc != mqtt.MQTT_ERR_SUCCESS:
            print(f"[mqtt] Failed to publish config for {device_id}: rc={result.rc}")
        else:
            print(f"[mqtt] Sent config to {topic}")

    def apply_config_update(self, update: ConfigUpdate) -> None:
        """
        Optional helper to push config updates published by an admin tool.
        Not wired to an endpoint here but available for future CLI use.
        """
        updated = self.config.update(update)
        topic = COMMAND_TOPIC_FMT.format(device_id=update.device_id or "+")
        payload = json.dumps(updated.model_dump())
        self.client.publish(topic, payload=payload, qos=1, retain=True)


def main() -> None:
    backend = MQTTBackend(MQTT_BROKER, MQTT_PORT)

    def _graceful_shutdown(signum, frame) -> None:  # noqa: ARG001
        print(f"[mqtt] Shutting down on signal {signum}")
        backend.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, _graceful_shutdown)
    signal.signal(signal.SIGTERM, _graceful_shutdown)
    backend.start()


if __name__ == "__main__":
    main()
