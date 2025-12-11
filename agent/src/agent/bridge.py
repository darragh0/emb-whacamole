"""UART-to-MQTT bridge for embedded device communication."""

from __future__ import annotations

import json
import logging
import time
from typing import TYPE_CHECKING, Any, ClassVar, Final, Literal, cast

from paho.mqtt.client import Client, ConnectFlags, DisconnectFlags, MQTTMessage
from paho.mqtt.enums import CallbackAPIVersion
from rich.status import Status
from serial import Serial, SerialException
from serial.tools import list_ports

from .utils import time_now_ms

if TYPE_CHECKING:
    from logging import Logger

    from paho.mqtt.properties import Properties
    from paho.mqtt.reasoncodes import ReasonCode

    from .types import DevStatus, StandardPayload, StatusPayload

RECONNECT_TIMEOUT_SECS: Final = 600
RECONNECT_RETRY_INTERVAL: Final = 2  # secs


class Bridge:
    """Bridges UART device to MQTT broker."""

    type Topic = Literal["state", "commands", "game_events"]

    TOPIC_NAMESPACE: ClassVar = "whac"
    VALID_COMMANDS: ClassVar[dict[bytes, str]] = {
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
    BYTES_ENCODING: ClassVar = "ascii"

    mqtt_broker: str
    mqtt_port: int
    serial_port: str
    baud_rate: int
    device_id: str

    _log: Logger
    _serial: Serial | None
    _mqtt: Client

    def __init__(
        self,
        *,
        mqtt_broker: str,
        mqtt_port: int,
        serial_port: str,
        baud_rate: int,
        device_id: str,
    ) -> None:
        self.mqtt_broker = mqtt_broker
        self.mqtt_port = mqtt_port
        self.serial_port = serial_port
        self.baud_rate = baud_rate
        self._device_id_received = False
        # fallback
        self.device_id = device_id

        self._log = logging.getLogger("Bridge")
        self._serial = None  # Initialize later in `self.run`
        self._mqtt = Client(client_id=f"bridge-{device_id}", callback_api_version=CallbackAPIVersion.VERSION2)

        self._mqtt.on_message = self._on_message
        self._mqtt.on_connect = self._on_connect
        self._mqtt.on_disconnect = self._on_disconnect
        self._mqtt.reconnect_delay_set(min_delay=1, max_delay=30)

    ####################################################### Pub ########################################################

    def run(self) -> None:
        """Connect to MQTT and UART, then process events."""

        # Connect to serial first to get device ID
        self._log.info("Connecting to %s (%d baud)", self.serial_port, self.baud_rate)
        try:
            self._serial = Serial(self.serial_port, self.baud_rate, timeout=0.1)
        except SerialException as e:
            self._log.error("Failed to connect to serial port: %s", e)
            return

        self._log.info("Connected to %s", self.serial_port)
        
        # Get device ID from first message
        self._get_device_id_from_serial()
        
        pload = self._payload(status="offline")
        topic = self._topic("state")
        self._mqtt.will_set(topic, payload=json.dumps(pload), qos=1, retain=True)

        self._log.info("Connecting to MQTT broker %s:%d", self.mqtt_broker, self.mqtt_port)
        self._mqtt.connect_async(self.mqtt_broker, self.mqtt_port, keepalive=30)
        self._mqtt.loop_start()
        
        self._publish_state("online")

        try:
            self._read_events()
        finally:
            self._mqtt.loop_stop()
            self._serial.close()
            self._log.info("Shutdown complete")

    def _read_events(self) -> None:
        """Read and process events from serial port."""

        while True:
            try:
                line_bytes = cast("Serial", self._serial).readline()
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
                cast("Serial", self._serial).close()
                return

            line = line_bytes.decode(Bridge.BYTES_ENCODING, errors="replace").strip()
            if line.startswith("{"):
                self._process_event(line)
            # Ignore other lines

    def _wait_for_reconnect(self) -> bool:
        """Wait for serial device to reconnect. Returns True if reconnected."""
        with Status("") as status:
            start = time.monotonic()
            while (elapsed := time.monotonic() - start) < RECONNECT_TIMEOUT_SECS:
                remaining = int(RECONNECT_TIMEOUT_SECS - elapsed)
                status.update(f"Reconnecting ({remaining}s remaining)")
                try:
                    self._serial = Serial(self.serial_port, self.baud_rate, timeout=0.1)
                except SerialException:
                    if self._serial is not None:
                        self._serial.close()
                    time.sleep(RECONNECT_RETRY_INTERVAL)
                else:
                    self._log.info("Reconnected to %s", self.serial_port)
                    return True

        self._log.error("Reconnect timeout after %ds", RECONNECT_TIMEOUT_SECS)
        return False

    def _get_device_id_from_serial(self) -> None:
        """Wait for first message from device to get hardware ID."""
        self._log.info("Waiting for device ID from hardware...")
        
        timeout_count = 0
        max_timeout = 100  # 10 seconds at 0.1s timeout - this is the max wait
        
        while not self._device_id_received and timeout_count < max_timeout:
            try:
                line_bytes = cast("Serial", self._serial).readline()
                line = line_bytes.decode(Bridge.BYTES_ENCODING, errors="replace").strip()
                
                if line.startswith("{"):
                    self._log.debug("Received JSON line: %s", line)
                    try:
                        event = json.loads(line)
                        if event.get("msg_type") == "device_id" and "device_id" in event:
                            self.device_id = event["device_id"]
                            self._device_id_received = True
                            self._log.info("Device ID received: %s", self.device_id)
                            return
                        else:
                            self._log.debug("Not a device_id message: %s", event)
                    except json.JSONDecodeError as e:
                        self._log.debug("JSON decode error: %s", e)
                        
                timeout_count += 1
            except SerialException as e:
                self._log.error("Serial error while getting device ID: %s", e)
                break
        
        if not self._device_id_received:
            self._log.warning("Failed to get device ID from hardware, using fallback: %s", self.device_id)

    def _process_event(self, jsonl: str) -> None:
        """Process and publish a JSON event from the device."""

        try:
            event = json.loads(jsonl)
        except json.JSONDecodeError as e:
            self._log.warning("Invalid JSON: %s (error: %s)", jsonl, e)
            return

        # Skip device identification messages
        if event.get("msg_type") == "device_id":
            return

        # Enrich with device_id and timestamp
        event |= self._payload()

        self._log.debug("[bright_white on grey30][Device -> MQTT][/] %s", event)
        topic = self._topic("game_events")
        self._mqtt.publish(topic, json.dumps(event), qos=1)

    def _publish_state(self, status: DevStatus | None = None) -> None:
        """Publish current device state to MQTT.

        Optional Args:
            status: Device status (connected, serial_error, offline)
        """
        pload = self._payload(status=status)
        topic = self._topic("state")
        self._log.debug("[bright_white on grey30][Agent -> MQTT][/] %s", pload)
        self._mqtt.publish(topic, payload=json.dumps(pload), qos=1, retain=True)

    ####################################################### Sub ########################################################

    def _on_message(self, client: Client, userdata: Any, message: MQTTMessage) -> None:  # noqa: ANN401
        """Forward MQTT command to serial device as single-byte command."""

        byte = message.payload
        if byte not in Bridge.VALID_COMMANDS:
            self._log.warning('[MQTT -> Device] INVALID COMMAND: "%s"', byte)
            return

        desc = Bridge.VALID_COMMANDS[byte]
        try:
            payload_str = byte.decode(Bridge.BYTES_ENCODING)
        except UnicodeDecodeError:
            payload_str = repr(byte)

        self._log.info("[bright_white on grey30][MQTT -> Device][/] %s (%s)", payload_str, desc)
        cast("Serial", self._serial).write(byte)

        _ = client, userdata

    ################################################ Utility Functions #################################################

    def _payload(self, *, status: DevStatus | None = None) -> StandardPayload | StatusPayload:
        """Return a JSON payload to be sent.

        Optional Keyword Arguments:
            status: Device status
        """
        pload: StandardPayload = {"device_id": self.device_id, "ts": time_now_ms()}
        if status is not None:
            return {**pload, "status": status}
        return pload

    def _topic(self, topic: Bridge.Topic) -> str:
        """Return a MQTT topic string for a given topic type.

        Args:
            topic: Topic type
        """
        return f"{Bridge.TOPIC_NAMESPACE}/{self.device_id}/{topic}"

    def _device_connected(self) -> bool:
        """Check if the serial device is still physically connected."""
        available = [p.device for p in list_ports.comports()]
        return self.serial_port in available

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
            self._log.info("Connected to MQTT %s:%d", self.mqtt_broker, self.mqtt_port)
            topic = self._topic("commands")
            client.subscribe(topic, qos=1)
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

        self._log.warning("MQTT disconnected (rc=%s), will attempt reconnect", reason_code)
        _ = client, userdata, disconnect_flags, properties
