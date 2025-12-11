from __future__ import annotations

import json
import logging
import time
from json import JSONDecodeError
from typing import TYPE_CHECKING, Any, ClassVar, Final, Literal

from paho.mqtt.client import Client, ConnectFlags, DisconnectFlags, MQTTMessage
from paho.mqtt.enums import CallbackAPIVersion
from rich.status import Status
from serial import Serial, SerialException
from serial.tools import list_ports

from agent.logging_conf import RichStyleHandler

from .utils import time_now_ms

if TYPE_CHECKING:
    from logging import Logger

    from paho.mqtt.properties import Properties
    from paho.mqtt.reasoncodes import ReasonCode

    from .types import CommonPayload, DevStatus, StatusPayload

RECONNECT_TIMEOUT_SECS: Final = 600
RECONNECT_RETRY_INTERVAL: Final = 2
DEVICE_ID_TIMEOUT_SECS: Final = 10
DEVICE_ID_RETRY_INTERVAL: Final = 0.1
HEARTBEAT_INTERVAL_SECS: Final = 20


class Bridge:
    """Bridges UART device to MQTT broker."""

    type Topic = Literal["state", "commands", "game_events"]

    TOPIC_NAMESPACE: ClassVar = "whac"
    BYTES_ENCODING: ClassVar = "ascii"
    AGENT_COMMANDS: ClassVar[dict[bytes, str]] = {
        b"H": "heartbeat request",
    }
    BOARD_COMMANDS: ClassVar[dict[bytes, str]] = {
        b"I": "identify",
        b"P": "pause toggle",
        b"R": "reset game",
        b"S": "start game",
        b"1": "set level 1",
        b"2": "set level 2",
        b"3": "set level 3",
        b"4": "set level 4",
        b"5": "set level 5",
        b"6": "set level 6",
        b"7": "set level 7",
        b"8": "set level 8",
    }

    mqtt_broker: str
    mqtt_port: int
    serial_port: str
    baud_rate: int
    device_id: str

    _log: Logger
    _serial: Serial
    _mqtt: Client

    def __init__(
        self,
        *,
        mqtt_broker: str,
        mqtt_port: int,
        serial_port: str,
        baud_rate: int,
    ) -> None:
        self.mqtt_broker = mqtt_broker
        self.mqtt_port = mqtt_port
        self.serial_port = serial_port
        self.baud_rate = baud_rate
        self.device_id: str

        self._log = logging.getLogger("Bridge")
        self._serial: Serial
        self._mqtt: Client
        self._paused: bool = False

    ####################################################### Pub ########################################################

    def run(self) -> None:
        """Connect to MQTT and UART, then process events."""

        # Connect to serial
        self._log.info("Connecting to serial port %s (%d baud)", self.serial_port, self.baud_rate)
        try:
            self._serial = Serial(self.serial_port, self.baud_rate, timeout=0.1)
        except SerialException as e:
            self._log.error("Failed to connect to serial port: %s", e)
            return

        self._log.info("Connected to %s", self.serial_port)

        if not self._request_device_id():
            self._log.error("Failed to get device ID from device")
            self._serial.close()
            return

        # Setup MQTT now that we have device_id
        self._mqtt = Client(
            client_id=f"bridge-{self.device_id}",
            callback_api_version=CallbackAPIVersion.VERSION2,
        )
        self._mqtt.on_message = self._on_message
        self._mqtt.on_connect = self._on_connect
        self._mqtt.on_disconnect = self._on_disconnect
        self._mqtt.reconnect_delay_set(min_delay=1, max_delay=30)

        # MQTT will
        pload = self._status_payload("offline")
        topic = self._topic("state")
        self._mqtt.will_set(topic, payload=json.dumps(pload), qos=2, retain=False)

        self._log.info("Connecting to MQTT broker [bright_magenta]%s:%d[/]", self.mqtt_broker, self.mqtt_port)
        self._mqtt.connect_async(self.mqtt_broker, self.mqtt_port, keepalive=30)
        self._mqtt.loop_start()

        self._publish_state("online")

        try:
            self._read_events()
        finally:
            self._cleanup_before_disconnect()
            self._mqtt.loop_stop()
            self._serial.close()
            # Just for logging purposes
            # ---
            pload = self._status_payload("offline")
            self._log.debug("[bright_white on grey30][Agent -> MQTT][/] %s", pload)
            # ---
            self._log.info("Shutdown complete")

    def _read_events(self) -> None:
        """Read and process events from serial port."""
        last_heartbeat = time.monotonic()

        while True:
            try:
                line_bytes = self._serial.readline()
            except SerialException as e:
                self._log.error("Serial read error: %s", e)

                status: DevStatus
                if not self._device_connected():
                    self._log.error("Device unplugged, exiting")
                    status = "offline"
                elif self._wait_for_reconnect():
                    self._publish_state("online")
                    continue
                else:
                    status = "serial_error"

                self._publish_state(status)
                self._cleanup_before_disconnect()
                self._serial.close()
                return

            try:
                line = line_bytes.decode(Bridge.BYTES_ENCODING, errors="replace").strip()
            except UnicodeDecodeError as e:
                self._log.error("Decode error (%s) while reading line: %s", Bridge.BYTES_ENCODING, e)
                continue

            if line.startswith("{"):
                self._process_event(line)

            now = time.monotonic()
            if now - last_heartbeat >= HEARTBEAT_INTERVAL_SECS:
                self._publish_state("online")
                last_heartbeat = now

    def _wait_for_reconnect(self) -> bool:
        """Wait for serial device to reconnect. Returns True if reconnected."""

        with Status("") as status:
            start = time.monotonic()
            while (elapsed := time.monotonic() - start) < RECONNECT_TIMEOUT_SECS:
                left = int(RECONNECT_TIMEOUT_SECS - elapsed)
                status.update(f"  [dim]>[/] Reconnecting ({left}s remaining)")
                try:
                    self._serial = Serial(self.serial_port, self.baud_rate, timeout=0.1)
                except SerialException:
                    time.sleep(RECONNECT_RETRY_INTERVAL)
                else:
                    status.stop()
                    self._log.info("Reconnected to %s", self.serial_port)
                    return True

        self._log.error("Reconnect timeout after %ds", RECONNECT_TIMEOUT_SECS)
        return False

    def _request_device_id(self) -> bool:
        """Send identify command and wait for response. Returns True on success."""

        self._log.info("Requesting device ID")

        try:
            self._serial.write(b"I")  # Identify
        except SerialException as e:
            self._log.error("Serial error while requesting device ID: %s", e)
            return False

        with Status("") as status:
            start = time.monotonic()
            while (elapsed := time.monotonic() - start) < DEVICE_ID_TIMEOUT_SECS:
                left = int(DEVICE_ID_TIMEOUT_SECS - elapsed)
                status.update(f" [dim]>[/] Waiting for device ID ({left}s remaining)")

                try:
                    line_bytes = self._serial.readline()
                    line = line_bytes.decode(Bridge.BYTES_ENCODING, errors="replace").strip()

                except SerialException as e:
                    status.stop()
                    self._log.error("Serial error while getting device ID: %s", e)
                    return False

                except UnicodeDecodeError as e:
                    fmted = RichStyleHandler.fmt_msg(
                        f"Decode error ({Bridge.BYTES_ENCODING}) while getting device ID: {e}",
                        logging.WARNING,
                    )
                    status.console.log(fmted)

                else:
                    if line.startswith("{"):
                        try:
                            event = json.loads(line)
                            if event.get("event_type") == "identify" and "device_id" in event:
                                self.device_id = event["device_id"]
                                status.stop()
                                self._log.info("Device ID: %s", self.device_id)
                                return True
                        except JSONDecodeError as e:
                            fmted = RichStyleHandler.fmt_msg(f"Invalid JSON: {line} (error: {e})", logging.ERROR)
                            status.console.log(fmted)

                time.sleep(DEVICE_ID_RETRY_INTERVAL)

        self._log.error("Device ID request timeout after %ds", DEVICE_ID_TIMEOUT_SECS)
        return False

    def _process_event(self, jsonl: str) -> None:
        """Process and publish JSON event from the device."""
        try:
            event = json.loads(jsonl)
        except JSONDecodeError as e:
            self._log.warning("Invalid JSON: %s (error: %s)", jsonl, e)
            return

        self._publish_event(event)

    def _publish_event(self, pload: dict[str, Any]) -> None:
        """Publish game event to MQTT (enriches with device_id and timestamp)."""
        pload |= self._common_payload()
        topic = self._topic("game_events")
        self._log.debug("[bright_white on grey30][Device -> MQTT][/] %s", pload)
        self._mqtt.publish(topic, json.dumps(pload), qos=2)

    def _publish_state(self, status: DevStatus) -> None:
        """Publish current device state to MQTT."""
        pload = self._status_payload(status)
        topic = self._topic("state")
        self._log.debug("[bright_white on grey30][Agent -> MQTT][/] %s", pload)
        self._mqtt.publish(topic, payload=json.dumps(pload), qos=2, retain=False)

    ####################################################### Sub ########################################################

    def _on_message(self, client: Client, userdata: Any, message: MQTTMessage) -> None:  # noqa: ANN401
        """Forward MQTT command to serial device as single-byte command."""
        byte = message.payload

        # Special case -- heartbeat (not forwarded to device)
        if byte in Bridge.AGENT_COMMANDS:
            match byte:
                case b"H":
                    self._log.debug("[bright_white on grey30][MQTT -> Agent][/] Heartbeat request")
                    self._publish_state("online")
                    return

        if byte not in Bridge.BOARD_COMMANDS:
            self._log.warning("[MQTT -> Device] INVALID COMMAND: %r", byte)
            return

        desc = Bridge.BOARD_COMMANDS[byte]
        self._log.info("[bright_white on grey30][MQTT -> Device][/] %r (%s)", byte, desc)

        try:
            self._serial.write(byte)
        except SerialException as e:
            self._log.error("Serial error while sending command: %s", e)
            return

        if byte == b"P":
            self._paused = not self._paused

        _ = client, userdata

    ################################################ Utility Functions #################################################

    def _status_payload(self, status: DevStatus) -> StatusPayload:
        """Return status payload for bridge state messages."""
        return {**self._common_payload(), "status": status}

    def _common_payload(self) -> CommonPayload:
        """Return common payload for outgoing MQTT messages."""
        return {"device_id": self.device_id, "ts": time_now_ms()}

    def _topic(self, topic: Bridge.Topic) -> str:
        """Return MQTT topic string for a given topic type.

        Args:
            topic: Topic type
        """
        return f"{Bridge.TOPIC_NAMESPACE}/{self.device_id}/{topic}"

    def _device_connected(self) -> bool:
        """Check if serial device is physically connected."""
        available = [p.device for p in list_ports.comports()]
        return self.serial_port in available

    def _cleanup_before_disconnect(self) -> None:
        """Send unpause if device is paused before disconnecting."""
        if self._paused:
            try:
                self._log.info("[bright_white on grey30][Agent -> Device][/] Unpausing device before disconnect")
                self._serial.write(b"P")
                self._paused = False
            except SerialException:
                self._log.error("Failed to unpause device before disconnect")

    ############################################### Connection Callbacks ###############################################

    def _on_connect(
        self,
        client: Client,
        userdata: Any,  # noqa: ANN401
        connect_flags: ConnectFlags,
        reason_code: ReasonCode,
        properties: Properties | None = None,
    ) -> None:
        """Handle MQTT connection."""

        if not reason_code.is_failure:
            self._log.info("Connected to [bright_magenta]%s:%d[/]", self.mqtt_broker, self.mqtt_port)
            client.subscribe(self._topic("commands"), qos=2)
            client.subscribe(f"{Bridge.TOPIC_NAMESPACE}/all/commands", qos=2)
            return

        self._log.warning("MQTT connect failed with rc=%s", reason_code)
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

        if not reason_code.is_failure:
            self._log.info("Disconnected from MQTT %s:%d", self.mqtt_broker, self.mqtt_port)
            return

        self._log.warning("MQTT disconnect failed with rc=%s", reason_code)
        _ = client, userdata, disconnect_flags, properties
