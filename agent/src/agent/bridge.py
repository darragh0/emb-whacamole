"""UART-to-MQTT bridge for embedded device communication."""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any

from paho.mqtt.client import Client, MQTTMessage
from serial import Serial, SerialException

if TYPE_CHECKING:
    from logging import Logger


class Bridge:
    """Bridges UART device to MQTT broker."""

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
        self.device_id = device_id

        self._log = logging.getLogger("Bridge")
        self._serial = None
        self._mqtt = Client(client_id=f"agent-{device_id}")
        self._mqtt.on_message = self._on_message

    def run(self) -> None:
        """Connect to MQTT and UART, then process events."""

        self._log.info("Connecting to MQTT broker %s", self.mqtt_broker)
        self._mqtt.connect(self.mqtt_broker, self.mqtt_port)
        self._mqtt.subscribe(f"whac/{self.device_id}/commands")
        self._mqtt.loop_start()

        self._log.info("Connecting to %s (%d baud)", self.serial_port, self.baud_rate)
        try:
            self._serial = Serial(self.serial_port, self.baud_rate, timeout=0.1)
        except SerialException as e:
            self._log.error("Failed to connect to serial port: %s", e)
            self._mqtt.loop_stop()
            return

        self._log.info("Connected to %s", self.serial_port)

        try:
            self._read_events()
        finally:
            self._mqtt.loop_stop()
            if self._serial is not None:
                self._serial.close()
            self._log.info("Shutdown complete")

    def _read_events(self) -> None:
        """Read and process events from serial port."""

        while self._serial:
            try:
                line_bytes = self._serial.readline()
            except SerialException as e:
                self._log.error("Serial read error: %s", e)
                break

            if not line_bytes:
                continue

            line = line_bytes.decode("utf-8", errors="replace").strip()
            if line.startswith("{"):
                self._process_event(line)

    def _process_event(self, jsonl: str) -> None:
        """Process and publish a JSON event from the device."""

        try:
            decoded = json.loads(jsonl)
        except json.JSONDecodeError as e:
            self._log.warning("Invalid JSON: %s (error: %s)", jsonl, e)
            return

        self._log.info("[Device -> MQTT] %s", decoded)
        self._mqtt.publish(f"whac/{self.device_id}/game_events", jsonl)

    def _on_message(self, client: Client, userdata: Any, message: MQTTMessage) -> None:  # noqa: ANN401
        """Forward MQTT command to serial device as single-byte command."""
        _ = client, userdata
        if self._serial is None:
            return

        cmd = message.payload.decode().strip()
        if cmd == "P":
            self._log.info("[MQTT -> Device] %s", cmd)
            self._serial.write(b"P")
