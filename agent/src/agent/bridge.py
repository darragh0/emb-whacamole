"""UART ↔ MQTT bridge for the Whac-a-Mole device.

Reads JSON lines from the device over UART and publishes them to MQTT topics expected
by the cloud backend. Also subscribes to commands/config on MQTT and forwards them to
the device over UART (one JSON object per line).
"""

from __future__ import annotations

import json
import logging
import threading
import time
from typing import Any, Dict, List, Optional, Tuple

import paho.mqtt.client as mqtt
from serial import Serial, SerialException

RECONNECT_TIMEOUT_SECS = 600
RECONNECT_RETRY_INTERVAL = 2  # seconds

GAME_EVENTS_TOPIC = "whac/{device_id}/game_events"
STATUS_TOPIC = "whac/{device_id}/status"
TELEMETRY_TOPIC = "whac/{device_id}/telemetry/{sensor}"
SESSIONS_TOPIC = "whac/{device_id}/events"
CONFIG_REQUEST_TOPIC = "whac/{device_id}/config_request"
COMMAND_TOPIC = "whac/{device_id}/commands"


class Bridge:
    """Bridge UART JSON lines to MQTT and commands back to UART."""

    def __init__(
        self,
        *,
        serial_port: str,
        baud_rate: int = 115200,
        device_id: str = "whacamole-dev",
        mqtt_host: str = "localhost",
        mqtt_port: int = 1883,
        mqtt_client: Optional[mqtt.Client] = None,
        serial_cls=Serial,
    ) -> None:
        self.serial_port = serial_port
        self.baud_rate = baud_rate
        self.device_id = device_id
        self.mqtt_host = mqtt_host
        self.mqtt_port = mqtt_port
        self._log = logging.getLogger("Bridge")
        self._mqtt = mqtt_client or mqtt.Client(client_id=f"bridge-{device_id}")
        self._serial_cls = serial_cls
        self._serial: Optional[Serial] = None
        self._stop_event = threading.Event()
        self._serial_lock = threading.Lock()

    def run(self) -> None:
        """Start the bridge."""
        if not self._open_serial():
            return
        self._setup_mqtt()
        self._connect_mqtt()

        uart_thread = threading.Thread(target=self._uart_loop, daemon=True)
        uart_thread.start()

        try:
            while not self._stop_event.is_set():
                time.sleep(0.5)
        finally:
            self._stop_event.set()
            uart_thread.join(timeout=1.0)
            self._mqtt.loop_stop()
            if self._serial:
                self._serial.close()
            self._log.info("Bridge stopped")

    def _open_serial(self) -> bool:
        self._log.info("Opening serial %s (%d baud)", self.serial_port, self.baud_rate)
        try:
            self._serial = self._serial_cls(self.serial_port, self.baud_rate, timeout=0.1)
        except SerialException as exc:
            self._log.error("Failed to open serial port: %s", exc)
            return False
        self._log.info("Serial connected")
        return True

    def _setup_mqtt(self) -> None:
        self._mqtt.on_connect = self._on_mqtt_connect
        self._mqtt.on_disconnect = self._on_mqtt_disconnect
        self._mqtt.on_message = self._on_mqtt_message
        self._mqtt.reconnect_delay_set(min_delay=1, max_delay=30)

    def _connect_mqtt(self) -> None:
        self._log.info("Connecting to MQTT %s:%d", self.mqtt_host, self.mqtt_port)
        try:
            self._mqtt.connect_async(self.mqtt_host, self.mqtt_port, keepalive=30)
            self._mqtt.loop_start()
        except Exception as exc:  # noqa: BLE001
            self._log.error("MQTT connection failed: %s", exc)

    def _on_mqtt_connect(self, client: mqtt.Client, userdata, flags, rc) -> None:  # noqa: ARG002
        if rc == 0:
            self._log.info("Connected to MQTT %s:%d", self.mqtt_host, self.mqtt_port)
            topic = COMMAND_TOPIC.format(device_id=self.device_id)
            client.subscribe(topic, qos=1)
            self._log.info("Subscribed to commands on %s", topic)
        else:
            self._log.warning("MQTT connect returned rc=%s", rc)

    def _on_mqtt_disconnect(self, client: mqtt.Client, userdata, rc) -> None:  # noqa: ARG002
        self._log.warning("MQTT disconnected (rc=%s), attempting reconnect", rc)

    def _on_mqtt_message(self, client: mqtt.Client, userdata, msg: mqtt.MQTTMessage) -> None:  # noqa: ARG002
        if msg.topic != COMMAND_TOPIC.format(device_id=self.device_id):
            return
        payload = msg.payload.decode("utf-8", errors="replace")
        self._log.info("MQTT command received: %s", payload)
        self._handle_command_payload(payload)

    def _uart_loop(self) -> None:
        """Continuously read UART and push to MQTT."""
        assert self._serial is not None
        while not self._stop_event.is_set():
            try:
                line_bytes = self._serial.readline()
            except SerialException as exc:
                self._log.error("Serial read error: %s", exc)
                if not self._wait_for_reconnect():
                    self._stop_event.set()
                    break
                continue

            if not line_bytes:
                continue

            line = line_bytes.decode("utf-8", errors="replace").strip()
            if not line:
                continue

            try:
                msg = json.loads(line)
            except json.JSONDecodeError as exc:
                self._log.warning("Ignoring invalid JSON from device: %s (err: %s)", line, exc)
                continue

            self._handle_uart_message(msg)

    def _wait_for_reconnect(self) -> bool:
        """Wait for serial device to reconnect. Returns True if reconnected."""
        start = time.monotonic()
        self._log.info("Waiting for device to reconnect (timeout: %ds)...", RECONNECT_TIMEOUT_SECS)

        while time.monotonic() - start < RECONNECT_TIMEOUT_SECS:
            try:
                self._serial = self._serial_cls(self.serial_port, self.baud_rate, timeout=0.1)
            except SerialException:
                time.sleep(RECONNECT_RETRY_INTERVAL)
            else:
                self._log.info("Reconnected to %s", self.serial_port)
                return True

        self._log.error("Reconnect timeout after %ds", RECONNECT_TIMEOUT_SECS)
        return False

    def _handle_uart_message(self, msg: Dict[str, Any]) -> None:
        mapped = self._map_uart_message(msg)
        if not mapped:
            self._log.debug("Dropping unmapped UART message: %s", msg)
            return

        topic, payload = mapped
        self._log.debug("UART -> MQTT %s : %s", topic, payload)
        try:
            self._mqtt.publish(topic, payload=payload, qos=1)
        except Exception as exc:  # noqa: BLE001
            self._log.error("Failed to publish to MQTT: %s", exc)

    def _map_uart_message(self, msg: Dict[str, Any]) -> Optional[Tuple[str, str]]:
        # Ensure device id travels with the payload.
        if "device_id" not in msg:
            msg["device_id"] = self.device_id

        msg_type = msg.get("type")
        event_type = msg.get("event_type")

        if msg_type == "config_request" or event_type == "config_request":
            topic = CONFIG_REQUEST_TOPIC.format(device_id=self.device_id)
            return topic, json.dumps(msg)

        if msg_type == "telemetry":
            sensor = msg.get("sensor") or msg.get("sensor_type")
            if not sensor:
                self._log.warning("Telemetry message missing sensor field: %s", msg)
                return None
            topic = TELEMETRY_TOPIC.format(device_id=self.device_id, sensor=sensor)
            return topic, json.dumps(msg)

        if msg_type == "session":
            topic = SESSIONS_TOPIC.format(device_id=self.device_id)
            return topic, json.dumps(msg)

        if msg_type == "status" or event_type in {"session_start", "session_end", "lvl_complete"}:
            payload = self._coerce_status(msg)
            topic = STATUS_TOPIC.format(device_id=self.device_id)
            return topic, json.dumps(payload)

        if msg_type == "game_event" or event_type == "pop_result":
            payload = self._coerce_game_event(msg)
            if payload is None:
                return None
            topic = GAME_EVENTS_TOPIC.format(device_id=self.device_id)
            return topic, json.dumps(payload)

        return None

    def _coerce_game_event(self, msg: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        pop = self._first_present(msg, ["pop", "mole_id", "mole"])
        level = self._first_present(msg, ["level", "lvl"])
        if pop is None:
            self._log.warning("game_event missing pop/mole field: %s", msg)
            return None
        reaction_ms = self._first_present(msg, ["reaction_ms", "reaction"]) or 0
        lives_left = self._first_present(msg, ["lives_left", "lives"]) or 0
        ts = self._first_present(msg, ["ts", "timestamp", "time"]) or self._now_ms()
        outcome_raw = msg.get("outcome") or ""
        outcome = str(outcome_raw).upper() if outcome_raw else "UNKNOWN"

        return {
            "device_id": msg.get("device_id", self.device_id),
            "pop": self._to_int(pop, 0),
            "level": self._to_int(level, 0),
            "outcome": outcome,
            "reaction_ms": self._to_int(reaction_ms, 0),
            "lives_left": self._to_int(lives_left, 0),
            "ts": self._to_int(ts, self._now_ms()),
        }

    def _coerce_status(self, msg: Dict[str, Any]) -> Dict[str, Any]:
        event_type = msg.get("event_type")
        state = msg.get("state")
        if not state:
            if event_type == "session_start":
                state = "playing"
            elif event_type == "session_end":
                state = "idle"
            else:
                state = "playing"
        ts = self._first_present(msg, ["ts", "timestamp", "time"]) or self._now_ms()
        payload: Dict[str, Any] = {
            "device_id": msg.get("device_id", self.device_id),
            "state": state,
            "level": self._to_int(self._first_present(msg, ["level", "lvl"]), 0),
            "pop_index": self._to_int(msg.get("pop_index"), 0),
            "lives_left": self._to_int(self._first_present(msg, ["lives_left", "lives"]), 0),
            "ts": self._to_int(ts, self._now_ms()),
        }
        if event_type == "session_end" and "win" in msg:
            payload["win"] = msg["win"]
        return payload

    def _handle_command_payload(self, payload: str) -> None:
        # Support legacy single-byte commands (e.g., "P" from older cloud)
        trimmed = payload.strip()
        if trimmed.upper() == "P":
            commands = [{"command": "pause"}]
        else:
            try:
                data = json.loads(payload)
            except json.JSONDecodeError as exc:
                self._log.warning("Ignoring invalid MQTT command JSON: %s (err: %s)", payload, exc)
                return
            commands = self._build_commands_from_payload(data)

        if not commands:
            self._log.warning("No commands generated from payload: %s", data)
            return

        for cmd in commands:
            self._write_command(cmd)

    def _build_commands_from_payload(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        cmds: List[Dict[str, Any]] = []

        if "command" in data:
            command = data["command"]
            cmd_payload: Dict[str, Any] = {"command": command}
            if "value" in data:
                cmd_payload["value"] = data["value"]
            cmds.append(cmd_payload)

        cfg = data.get("config")
        if isinstance(cfg, dict):
            if cfg.get("pause") is True:
                cmds.append({"command": "pause"})
            if cfg.get("pause") is False or cfg.get("resume") is True:
                cmds.append({"command": "resume"})
            if cfg.get("set_level") is not None:
                cmds.append({"command": "set_level", "value": cfg.get("set_level")})
            if cfg.get("set_pop_duration") is not None:
                cmds.append({"command": "set_pop_duration", "value": cfg.get("set_pop_duration")})
            if cfg.get("set_lives") is not None:
                cmds.append({"command": "set_lives", "value": cfg.get("set_lives")})
            if cfg.get("set_send_events") is not None:
                cmds.append({"command": "set_send_events", "value": cfg.get("set_send_events")})
            if cfg.get("sensor_config") is not None:
                cmds.append({"command": "sensor_config", "value": cfg.get("sensor_config")})

        return cmds

    def _write_command(self, cmd: Dict[str, Any]) -> None:
        if not self._serial:
            self._log.warning("Serial not available; dropping command: %s", cmd)
            return
        line = json.dumps(cmd)
        self._log.info("UART <= %s", line)
        try:
            with self._serial_lock:
                self._serial.write((line + "\n").encode("utf-8"))
        except SerialException as exc:
            self._log.error("Failed to write command to serial: %s", exc)

    @staticmethod
    def _to_int(value: Any, default: int) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _first_present(msg: Dict[str, Any], keys: List[str]) -> Any:
        for key in keys:
            if key in msg and msg[key] is not None:
                return msg[key]
        return None

    @staticmethod
    def _now_ms() -> int:
        return int(time.time() * 1000)


def main() -> None:
    from .argparser import get_args
    from .logging_conf import init_logging

    init_logging()
    args = get_args()
    bridge = Bridge(**args)
    bridge.run()


if __name__ == "__main__":
    main()
