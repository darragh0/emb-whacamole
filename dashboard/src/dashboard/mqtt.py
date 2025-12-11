"""MQTT helpers."""

from __future__ import annotations

import json
import os
import socket
from typing import TYPE_CHECKING, Any, Final

from paho.mqtt.client import Client, ConnectFlags
from paho.mqtt.enums import CallbackAPIVersion

from .env import get_env_vars

if TYPE_CHECKING:
    from collections.abc import Callable

    from paho.mqtt.client import MQTTMessage
    from paho.mqtt.properties import Properties
    from paho.mqtt.reasoncodes import ReasonCode


BROKER: Final
PORT: Final
BROKER, PORT = get_env_vars()


def subscribe(topics: list[str], handler: Callable[[dict[str, Any], str], None]) -> Client:
    client_id = f"dashboard-{socket.gethostname()}-{os.getpid()}"
    mqttc = Client(client_id=client_id, callback_api_version=CallbackAPIVersion.VERSION2)

    def on_connect(
        client: Client,
        userdata: Any,  # noqa: ANN401
        flags: ConnectFlags,
        reason_code: ReasonCode,
        properties: Properties | None = None,
    ) -> None:
        _ = client, userdata, flags, properties
        if not reason_code.is_failure:
            print(f"[MQTT] Connected to {BROKER}:{PORT}")
            for t in topics:
                mqttc.subscribe(t)
                print(f"[MQTT] Subscribed to {t}")
        else:
            print(f"[MQTT] Connection failed: {reason_code}")

    def on_message(
        client: Client,
        userdata: Any,  # noqa: ANN401
        message: MQTTMessage,
    ) -> None:
        _ = client, userdata
        print(f"[MQTT] Received message on {message.topic}")
        handler(json.loads(message.payload.decode()), message.topic)

    mqttc.on_connect = on_connect
    mqttc.on_message = on_message
    print(f"[MQTT] Connecting to {BROKER}:{PORT}...")
    mqttc.connect(BROKER, PORT)
    return mqttc
