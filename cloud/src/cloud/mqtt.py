"""MQTT helpers."""

from __future__ import annotations

import contextlib
import json
from typing import TYPE_CHECKING, Any, Final

from paho.mqtt import publish
from paho.mqtt.client import Client

from .utils import get_env_vars

if TYPE_CHECKING:
    from collections.abc import Callable

    import paho.mqtt.client as mqtt
    from paho.mqtt.client import ConnectFlags
    from paho.mqtt.properties import Properties
    from paho.mqtt.reasoncodes import ReasonCode

    from cloud.types import GameEvent


BROKER: Final
PORT: Final
BROKER, PORT = get_env_vars()


def send_pause(device_id: str) -> None:
    """Publish pause (toggle) command to device.

    Args:
        device_id: Recipient device ID
    """
    publish.single(
        f"whac/{device_id}/commands",
        "P",
        hostname=BROKER,
        port=PORT,
    )


def subscribe(topics: list[str], handler: Callable[[GameEvent], None]) -> Client:
    """Subscribe to topics.

    Args:
        topics: List of topics to subscribe to
        handler: Handler for incoming messages

    Returns:
        MQTT client
    """
    mqttc = Client()

    def on_connect(
        client: Client,
        userdata: Any,  # noqa: ANN401
        flags: ConnectFlags,
        reason_code: ReasonCode,
        properties: Properties | None = None,
    ) -> None:
        _ = client, userdata, flags, reason_code, properties
        for t in topics:
            mqttc.subscribe(t)

    def on_message(
        client: Client,
        userdata: Any,  # noqa: ANN401
        message: mqtt.MQTTMessage,
    ) -> None:
        _ = client, userdata
        with contextlib.suppress(json.JSONDecodeError):
            handler(json.loads(message.payload.decode()))

    mqttc.on_connect = on_connect
    mqttc.on_message = on_message
    mqttc.connect(BROKER, PORT)
    return mqttc
