from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any, ClassVar, Literal, TypedDict

from paho.mqtt.client import Client, ConnectFlags, DisconnectFlags, MQTTMessage
from paho.mqtt.enums import CallbackAPIVersion, MQTTErrorCode

from .misc import time_now_ms

if TYPE_CHECKING:
    from collections.abc import Callable
    from logging import Logger

    from paho.mqtt.properties import Properties
    from paho.mqtt.reasoncodes import ReasonCode

    type Topic = Literal["state", "commands", "game_events"]
    type CommandCallback = Callable[[bytes], None]

    type DevStatus = Literal["online", "serial_error", "offline"]

    class CommonPayload(TypedDict):
        device_id: str
        ts: int

    class StatusPayload(CommonPayload):
        status: DevStatus


class MqttClient:
    """Wrapper around paho-mqtt with connection management."""

    KEEPALIVE: ClassVar = 30

    broker: str
    port: int
    device_id: str
    topic: str
    on_command: CommandCallback

    _log: Logger
    _client: Client

    def __init__(
        self,
        *,
        broker: str,
        port: int,
        device_id: str,
        topic: str,
        on_command: CommandCallback,
        last_will: DevStatus,
    ) -> None:
        self.broker = broker
        self.port = port
        self.device_id = device_id
        self.topic = topic
        self.on_command = on_command

        self._log = logging.getLogger("MqttClient")
        self._client = Client(
            client_id=f"bridge-{device_id}",
            callback_api_version=CallbackAPIVersion.VERSION2,
        )
        self._client.on_message = self._on_message
        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        self._client.reconnect_delay_set(min_delay=1, max_delay=30)

        # Set last will
        pload = self._status_payload(last_will)
        topic = f"{self.topic}/{self.device_id}/state"
        self._client.will_set(topic, payload=json.dumps(pload), qos=2, retain=False)
        self._log.debug("Last will set to [bright_yellow]%s[/]", last_will)

    def connect(self) -> bool:
        """Connect to MQTT broker. Return True on success."""

        self._log.debug("Connecting to MQTT broker [bright_magenta]%s:%d[/]", self.broker, self.port)
        res1 = self._client.connect(self.broker, self.port, keepalive=MqttClient.KEEPALIVE)

        if res1 != MQTTErrorCode.MQTT_ERR_SUCCESS:
            self._log.critical("MQTT connect failed with rc=%s", res1)
            return False

        if (res2 := self._client.loop_start()) != MQTTErrorCode.MQTT_ERR_SUCCESS:
            self._log.critical("MQTT connect (loop start) failed with rc=%s", res2)
            return False

        self._log.info("Connected to [bright_magenta]%s:%d[/]", self.broker, self.port)
        return True

    def disconnect(self) -> None:
        """Disconnect from MQTT broker and stop loop."""

        self._log.debug("Disconnecting from MQTT broker [bright_magenta]%s:%d[/]", self.broker, self.port)
        res1 = self._client.disconnect()

        if res1 != MQTTErrorCode.MQTT_ERR_SUCCESS:
            self._log.critical("MQTT disconnect failed with rc=%s", res1)
            return

        if (res2 := self._client.loop_stop()) != MQTTErrorCode.MQTT_ERR_SUCCESS:
            self._log.critical("MQTT disconnect (loop start) failed with rc=%s", res2)
            return

        self._log.info("Disconnected from [bright_magenta]%s:%d", self.broker, self.port)

    def publish_state(self, status: DevStatus) -> None:
        """Publish device state to MQTT.

        Args:
            status: Device status
        """

        self._pub("state", self._status_payload(status), frm="Agent", to="MQTT")

    def publish_event(self, event: Any) -> None:  # noqa: ANN401
        """Publish game event to MQTT.

        Args:
            event: Game event
        """

        pload = event | self._common_payload()
        self._pub("game_events", pload, frm="Device", to="MQTT")

    ################################################# Utility Methods ##################################################

    def _common_payload(self) -> CommonPayload:
        """Return common payload for outgoing MQTT messages."""
        return {"device_id": self.device_id, "ts": time_now_ms()}

    def _status_payload(self, status: DevStatus) -> StatusPayload:
        """Return status payload for bridge state messages."""
        return {**self._common_payload(), "status": status}

    def _pub(self, topic: str, pload: CommonPayload | StatusPayload, *, frm: str, to: str) -> None:
        """Publish payload to given topic.

        Args:
            topic: MQTT topic
            pload: Payload

        Keywords Args:
            frm: Source
            to: Destination
        """
        self._log.debug("[bright_white on grey30][%s -> %s][/] %s", frm, to, pload)
        res = self._client.publish(f"{self.topic}/{self.device_id}/{topic}", json.dumps(pload), qos=2)

        if res.rc != MQTTErrorCode.MQTT_ERR_SUCCESS:
            self._log.error("MQTT publish failed with rc=%s", res.rc)

    def _sub(self, client: Client, topic: str) -> None:
        """Subscribe to given topic.

        Args:
            client: MQTT client
            topic: MQTT topic
        """

        self._log.debug("Subscribing to topic: [bright_green]%s[/]", topic)
        res, _ = client.subscribe(topic, qos=2)

        if res != MQTTErrorCode.MQTT_ERR_SUCCESS:
            self._log.error("MQTT subscribe failed with rc=%s", res)
            return

        self._log.info("Subscribed to topic: [bright_green]%s[/]", topic)

    ############################################### Paho MQTT Callbacks ################################################

    def _on_connect(
        self,
        client: Client,
        userdata: Any,  # noqa: ANN401
        connect_flags: ConnectFlags,
        reason_code: ReasonCode,
        properties: Properties | None = None,
    ) -> None:
        """Handle MQTT connection."""

        if reason_code.is_failure:
            self._log.warning("MQTT connect failed with rc=%s", reason_code)
            return

        self._sub(client, f"{self.topic}/{self.device_id}/commands")
        self._sub(client, f"{self.topic}/all/commands")
        _ = userdata, connect_flags, properties

    def _on_disconnect(
        self,
        client: Client,
        userdata: Any,  # noqa: ANN401
        disconnect_flags: DisconnectFlags,
        reason_code: ReasonCode,
        properties: Properties | None = None,
    ) -> None:
        """Handle MQTT disconnection."""

        if reason_code.is_failure:
            self._log.warning("MQTT disconnect failed with rc=%s", reason_code)

        _ = client, userdata, disconnect_flags, properties

    def _on_message(self, client: Client, userdata: Any, message: MQTTMessage) -> None:  # noqa: ANN401
        """Forward MQTT command to registered callback."""

        self.on_command(message.payload)
        _ = client, userdata
