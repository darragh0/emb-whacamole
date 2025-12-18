"""MQTT helpers."""

from __future__ import annotations

import json
import os
import socket
from typing import TYPE_CHECKING, Any

from paho.mqtt import publish
from paho.mqtt.client import Client, ConnectFlags, DisconnectFlags
from paho.mqtt.enums import CallbackAPIVersion

if TYPE_CHECKING:
    from collections.abc import Callable

    from paho.mqtt.client import MQTTMessage
    from paho.mqtt.properties import Properties
    from paho.mqtt.reasoncodes import ReasonCode

    from dashboard.types import StatusOk


from .env import BROKER, MQTT_PORT


def pub_cmd(device_id: str, cmd: str) -> StatusOk:
    """Publish a command to a given device.

    Args:
        device_id: Device ID
        cmd: Command

    Returns:
        StatusOk for caller to return
    """
    publish.single(
        f"whac/{device_id}/commands",
        cmd,
        hostname=BROKER,
        port=MQTT_PORT,
        qos=2,
    )

    return {"ok": True}


def subscribe(topics: list[str], handler: Callable[[dict[str, Any], str], None]) -> Client:
    """Subscribe to MQTT topics.

    Args:
        topics: List of topics to subscribe to
        handler: Callback for when message is received
    """

    client_id = f"dashboard-{socket.gethostname()}-{os.getpid()}"
    mqttc = Client(client_id=client_id, callback_api_version=CallbackAPIVersion.VERSION2)
    mqttc.reconnect_delay_set(min_delay=1, max_delay=30)

    def on_connect(
        client: Client,
        userdata: Any,  # noqa: ANN401
        flags: ConnectFlags,
        reason_code: ReasonCode,
        properties: Properties | None = None,
    ) -> None:
        _ = client, userdata, flags, properties
        if not reason_code.is_failure:
            print(f"[MQTT] Connected to {BROKER}:{MQTT_PORT}")
            for t in topics:
                mqttc.subscribe(t)
                print(f"[MQTT] Subscribed to {t}")
        else:
            print(f"[MQTT] Connection failed: {reason_code}")

    def on_disconnect(
        client: Client,
        userdata: Any,  # noqa: ANN401
        disconnect_flags: DisconnectFlags,
        reason_code: ReasonCode,
        properties: Properties | None = None,
    ) -> None:
        _ = client, userdata, disconnect_flags, properties
        if reason_code.is_failure:
            print(f"[MQTT] Disconnected unexpectedly: {reason_code}, will reconnect...")
        else:
            print(f"[MQTT] Disconnected: {reason_code}")

    def on_message(
        client: Client,
        userdata: Any,  # noqa: ANN401
        message: MQTTMessage,
    ) -> None:
        _ = client, userdata
        try:
            print(f"[MQTT] Received message on {message.topic}")
            handler(json.loads(message.payload.decode()), message.topic)
        except Exception as e:
            print(f"[MQTT] Error processing message on {message.topic}: {e}")

    mqttc.on_connect = on_connect
    mqttc.on_disconnect = on_disconnect
    mqttc.on_message = on_message
    print(f"[MQTT] Connecting to {BROKER}:{MQTT_PORT}...")
    mqttc.connect(BROKER, MQTT_PORT)
    return mqttc
