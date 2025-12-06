"""Simple UART bridge for embedded device communication.

Reads JSON events from device over UART and logs them.
"""

from __future__ import annotations

import json
import logging

from serial import Serial, SerialException


class Bridge:
    """Bridges UART device to cloud backend."""

    serial_port: str
    baud_rate: int
    device_id: str

    def __init__(
        self,
        *,
        serial_port: str,
        baud_rate: int = 115200,
        device_id: str = "whacamole-dev",
    ) -> None:
        self.serial_port = serial_port
        self.baud_rate = baud_rate
        self.device_id = device_id
        self._log = logging.getLogger("Bridge")

    def run(self) -> None:
        """Connect to UART & process events."""

        self._log.info("Connecting to %s (%d baud)", self.serial_port, self.baud_rate)

        try:
            serial = Serial(self.serial_port, self.baud_rate, timeout=0.1)
        except SerialException as e:
            self._log.error("Failed to connect to serial port: %s", e)
            return
        else:
            self._log.info("Connected to %s", self.serial_port)

        try:
            self._read_events(serial)
        finally:
            serial.close()
            self._log.info("Shutdown complete")

    def _read_events(self, serial: Serial) -> None:
        """Read and process events from serial port."""
        while True:
            try:
                line_bytes = serial.readline()
            except SerialException as e:
                self._log.error("Serial read error: %s", e)
                break
            except Exception:  # noqa: BLE001
                self._log.exception("Unexpected error reading serial")
                break

            if not line_bytes:
                continue

            line = line_bytes.decode("utf-8", errors="replace").strip()

            # Only log json lines (events)
            if line.startswith("{"):
                self._process_event(line)

    def _process_event(self, jsonl: str) -> None:
        """Process a JSON event from the device.

        Args:
            jsonl: JSON line to decode
        """
        try:
            decoded = json.loads(jsonl)
        except json.JSONDecodeError as e:
            self._log.warning("ignoring invalid JSON from device: %s (error: %s)", jsonl, e)
            return

        self._log.info("[Serial JSON] %s", decoded)

        # TODO: Add MQTT support
        #
        # When adding MQTT:
        #   1. Make run() and _read_events()
        #   2. Add ThreadPoolExecutor for blocking serial I/O
        #   3. Connect to MQTT broker: Client(broker, port, identifier=f"bridge-{device_id}")
        #   4. Run serial reading and MQTT concurrently: asyncio.gather(read_task, mqtt_task)
        #   5. Publish events: await mqtt.publish(f"whac/{device_id}/events", json_line, qos=1)
        #   6. Subscribe to commands: await mqtt.subscribe(f"whac/{device_id}/commands")
        #   7. Forward commands to serial: serial.write(command.encode() + b"\n")
        #
        # Example command from MQTT to device:
        #   {"command":"pause"}
        #   {"command":"start"}
        #   {"command":"reset"}
