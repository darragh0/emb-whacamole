"""
UART-MQTT Bridge for Whac-A-Mole embedded device.

This module bridges communication between the MAX32655 embedded device
(via UART/serial) and the MQTT broker (for dashboard integration).

Data Flow:
    Device -> UART -> Bridge -> MQTT -> Dashboard
    Dashboard -> MQTT -> Bridge -> UART -> Device

Protocol:
    - Device sends JSONL events over UART (one JSON object per line)
    - Bridge publishes events to MQTT topic: whac/<device_id>/game_events
    - Dashboard sends commands via MQTT topic: whac/<device_id>/cmd
    - Bridge forwards single-byte commands to device via UART

Connection Handling:
    - Auto-reconnect on serial disconnect (10 minute timeout)
    - Heartbeat messages every 20s to indicate bridge is alive
    - Graceful cleanup on shutdown (unpause, send 'D' to start buffering)
"""

from __future__ import annotations

import json
import logging
import time
from json import JSONDecodeError
from typing import TYPE_CHECKING, Any, ClassVar, Final

from rich.status import Status
from serial import Serial, SerialException
from serial.tools import list_ports

from agent.mqtt import MqttClient

if TYPE_CHECKING:
    from logging import Logger


RECONNECT_TIMEOUT: Final = 600  # 10 min sto reconnect before giving up
RECONNECT_RETRY_INTERVAL: Final = 2  # Secs between reconnect attempts

DEVICE_ID_TIMEOUT: Final = 10  # Secs to wait for identify response
DEVICE_ID_RETRY_INTERVAL: Final = 0.1

# Heartbeat to indicate bridge is alive (MQTT retained message)
HEARTBEAT_INTERVAL: Final = 20


class Bridge:
    """
    Bridges UART device to MQTT broker.

    Manages the full lifecycle of device communication:
        1. Connect to serial port
        2. Request device ID (identify handshake)
        3. Setup MQTT with device-specific topics
        4. Forward events (Device -> MQTT) and commands (MQTT -> Device)
        5. Handle disconnects with auto-reconnect
        6. Graceful cleanup on shutdown
    """

    TOPIC_NAMESPACE: ClassVar = "whac"
    BYTES_ENCODING: ClassVar = "ascii"

    # Format: {byte: description} for logging/validation
    BOARD_COMMANDS: ClassVar[dict[bytes, str]] = {
        b"I": "identify",
        b"P": "pause toggle",
        b"R": "reset game",
        b"S": "start game",
        b"D": "disconnect (start buffering)",
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
    _mqtt: MqttClient

    def __init__(self, *, mqtt_broker: str, mqtt_port: int, serial_port: str, baud_rate: int) -> None:
        self.mqtt_broker = mqtt_broker
        self.mqtt_port = mqtt_port
        self.serial_port = serial_port
        self.baud_rate = baud_rate
        self.device_id: str

        self._log = logging.getLogger("Bridge")
        self._serial: Serial
        self._mqtt: MqttClient
        self._paused: bool = False

    # ==================== Public API ====================

    def run(self) -> None:
        try:
            if not self._connect_to_serial():
                return

            if not self._request_device_id():
                self._serial.close()
                return

            # Setup MQTT now that we have device_id for topic routing
            self._mqtt = MqttClient(
                broker=self.mqtt_broker,
                port=self.mqtt_port,
                device_id=self.device_id,
                topic=Bridge.TOPIC_NAMESPACE,
                on_command=self._handle_command,
                last_will="offline",  # Auto-publish on ungraceful disconnect
            )

            if not self._mqtt.connect():
                self._serial.close()
                return

            self._mqtt.publish_state("online").wait_for_publish()

            try:
                self._read_events()
            finally:
                self._cleanup_before_disconnect()
                self._mqtt.publish_state("offline").wait_for_publish()
                self._mqtt.disconnect()
                self._serial.close()

        finally:
            self._log.info("Shutdown complete")

    # ==================== Event Processing ====================

    def _read_events(self) -> None:
        """Read JSONL events from serial and publish to MQTT.

        - Normal events: Parse JSON, publish to MQTT
        - Serial errors: Attempt reconnect or exit
        """
        self._log.debug("Listening for events")

        last_heartbeat = time.monotonic()
        while True:
            try:
                jsonl = self._serial_read_jsonl()
            except SerialException:
                if not self._device_connected():
                    self._log.critical("Device unplugged, exiting")
                elif self._wait_for_reconnect():
                    self._mqtt.publish_state("online").wait_for_publish()
                    continue
                else:
                    self._mqtt.publish_state("serial_error").wait_for_publish()
                return
            except (UnicodeDecodeError, JSONDecodeError):
                # Malformed data - skip and continue (logged in _serial_read_jsonl)
                pass
            else:
                if jsonl is not None:
                    self._mqtt.publish_event(jsonl)

            now = time.monotonic()
            if now - last_heartbeat >= HEARTBEAT_INTERVAL:
                self._mqtt.publish_state("online")
                last_heartbeat = now

    def _wait_for_reconnect(self) -> bool:
        """Wait for serial device to reconnect. Returns True if reconnected."""

        self._log.debug("Waiting for device to reconnect")

        with Status("") as status:
            start = time.monotonic()
            while (elapsed := time.monotonic() - start) < RECONNECT_TIMEOUT:
                left = int(RECONNECT_TIMEOUT - elapsed)
                status.update(f"  [dim]>[/] Reconnecting ({left}s remaining)")
                try:
                    self._serial = Serial(self.serial_port, self.baud_rate, timeout=0.1)
                    self._serial.reset_input_buffer()
                except (OSError, SerialException, BaseException):  # noqa: BLE001
                    time.sleep(RECONNECT_RETRY_INTERVAL)
                else:
                    status.stop()
                    self._log.info("Reconnected to %s", self.serial_port)
                    # Re-identify to flush any buffered events on device
                    self._serial_write(b"I", ctx="re-identifying after reconnect")
                    return True

        self._log.critical("Failed to reconnect (timeout after %ds)", RECONNECT_TIMEOUT)
        return False

    def _request_device_id(self) -> bool:
        """Send identify command and wait for response. Returns True on success."""

        self._log.debug("Requesting device ID")
        if not self._serial_write(b"I", ctx="requesting device ID"):  # Identify
            self._log.critical("Failed to get device ID")
            return False

        start = time.monotonic()
        while (time.monotonic() - start) < DEVICE_ID_TIMEOUT:
            try:
                jsonl = self._serial_read_jsonl(ctx="getting device ID")
            except (SerialException, UnicodeDecodeError):
                return False
            except JSONDecodeError:
                continue  # Could be a partial line (e.g. if connecting while device middle of game)

            if jsonl is None:
                continue

            if jsonl.get("event_type") == "identify" and "device_id" in jsonl:
                self.device_id = jsonl["device_id"]
                self._log.info("Device ID received: [bright_green]%s[/]", self.device_id)
                return True

            time.sleep(DEVICE_ID_RETRY_INTERVAL)

        self._log.critical("Failed to get device ID (timeout after %ds)", DEVICE_ID_TIMEOUT)
        return False

    def _handle_command(self, byte: bytes) -> None:
        """Handle MQTT command (callback from MqttClient).

        Args:
            byte: Single-byte MQTT Command
        """

        if byte not in Bridge.BOARD_COMMANDS:
            self._log.warning("[MQTT -> Device] INVALID COMMAND: %r", byte)
            return

        desc = Bridge.BOARD_COMMANDS[byte]
        self._log.info("[bright_white on grey30][MQTT -> Device][/] %r (%s)", byte, desc)

        if not self._serial_write(byte):
            return

        match byte:
            case b"P":
                self._paused = not self._paused

    def _connect_to_serial(self) -> bool:
        """Connect to serial port. Returns True on success."""

        self._log.debug("Connecting to serial port %s (%d baud)", self.serial_port, self.baud_rate)
        try:
            self._serial = Serial(self.serial_port, self.baud_rate, timeout=0.1)
            self._serial.reset_input_buffer()
        except (OSError, SerialException, BaseException) as e:  # noqa: BLE001
            self._log.critical("Failed to connect to serial port: %s", e)
            return False

        self._log.info("Connected to %s", self.serial_port)
        return True

    def _serial_read_jsonl(self, *, ctx: str = "reading line") -> dict[str, Any] | None:
        """Read line (as bytes) from serial device and decode as JSON.

        Args:
            ctx: Context for logging

        Returns:
            Decoded JSON line from serial device. If empty line (no bytes), returns None

        Raises:
            SerialException: Serial read error
            UnicodeDecodeError: Decode error
            JSONDecodeError: Invalid JSON
        """

        try:
            line_bytes = self._serial.readline()
        except SerialException as e:
            self._log.error("Serial error while %s: %s", ctx, e)
            raise

        if not line_bytes:
            return None

        try:
            line = line_bytes.decode(Bridge.BYTES_ENCODING).strip()
        except UnicodeDecodeError as e:
            self._log.error("Decode error (%s) while %s: %s", Bridge.BYTES_ENCODING, ctx, e)
            raise

        try:
            jsonl = json.loads(line)
            if not isinstance(jsonl, dict):
                msg = f"expected dict, got {type(jsonl)}"
                raise JSONDecodeError(msg, doc=jsonl, pos=0)  # noqa: TRY301

        except JSONDecodeError as e:
            self._log.warning(
                "[bright_yellow on grey30][IGNORING][/] Invalid JSON received (%s): %s (error: %s)",
                ctx,
                line,
                e,
            )
            raise

        return jsonl

    def _serial_write(self, byte: bytes, *, ctx: str | None = None) -> bool:
        """Write byte to serial device.

        Args:
            byte: Command byte to write to serial device
            ctx: Context for logging

        Returns:
            True on success
        """

        try:
            self._serial.write(byte)
        except SerialException as e:
            ctx = f"writing {byte!r}" if ctx is None else ctx
            self._log.error("Serial error while %s: %s", ctx, e)
            return False

        return True

    def _device_connected(self) -> bool:
        """Return True if serial device is physically connected."""

        available = [p.device for p in list_ports.comports()]
        return self.serial_port in available

    def _cleanup_before_disconnect(self) -> None:
        """Send unpause and disconnect command before disconnecting.

        Only sends commands if device is still physically connected.
        If unplugged, device has reset anyway so no point sending commands.
        """

        if not self._device_connected():
            self._log.debug("Skipping cleanup commands")
            return

        if self._paused:
            self._log.info("[bright_white on grey30][Agent -> Device][/] Unpausing device before disconnect")
            if self._serial_write(b"P", ctx="attempting to unpause device"):
                self._paused = False

        # Notify device to start buffering events
        self._log.info("[bright_white on grey30][Agent -> Device][/] Sending disconnect command")
        self._serial_write(b"D", ctx="attempting to disconnect device")
