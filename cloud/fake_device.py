"""
Simple fake device that publishes sample game sessions over MQTT for demo/testing.
"""

import json
import os
import time
import uuid
from datetime import datetime, timezone
from random import randint

import paho.mqtt.client as mqtt

MQTT_BROKER = os.getenv("MQTT_BROKER", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
DEVICE_ID = os.getenv("DEVICE_ID", "fake-board-01")

EVENT_TOPIC = f"whac/{DEVICE_ID}/events"
CONFIG_REQ_TOPIC = f"whac/{DEVICE_ID}/config_request"
COMMANDS_TOPIC = f"whac/{DEVICE_ID}/commands"


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_session(session_num: int) -> dict:
    total = randint(5, 20)
    events = []
    for _ in range(randint(3, 8)):
        mole = randint(0, 7)
        hit = randint(0, 1) == 1
        reaction = randint(200, 900) if hit else None
        delta = 1 if hit else 0
        events.append(
            {
                "mole": mole,
                "hit": hit,
                "reaction_ms": reaction,
                "score_delta": delta,
                "ts": iso_now(),
            }
        )
    return {
        "session_id": str(session_num),
        "device_id": DEVICE_ID,
        "player": "demo",
        "difficulty": "normal",
        "duration_ms": 60000,
        "started_at": iso_now(),
        "ended_at": iso_now(),
        "total_score": total,
        "events": events,
        "sensors": {"heart_rate_bpm": randint(80, 120)},
    }


def on_connect(client: mqtt.Client, userdata, flags, rc):
    print(f"[fake] Connected rc={rc}, subscribing to {COMMANDS_TOPIC}")
    client.subscribe(COMMANDS_TOPIC, qos=1)
    # Request current config on connect
    client.publish(CONFIG_REQ_TOPIC, payload=b"", qos=1)


def on_message(client: mqtt.Client, userdata, msg: mqtt.MQTTMessage):
    print(f"[fake] Command received on {msg.topic}: {msg.payload.decode('utf-8')}")


def main():
    client = mqtt.Client(client_id=f"fake-device-{uuid.uuid4()}")
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(MQTT_BROKER, MQTT_PORT, keepalive=30)
    client.loop_start()

    session = 1
    try:
        while True:
            payload = build_session(session)
            client.publish(EVENT_TOPIC, json.dumps(payload), qos=1)
            print(f"[fake] Published session {session} to {EVENT_TOPIC}")
            session += 1
            time.sleep(5)
    except KeyboardInterrupt:
        print("[fake] Stopping")
    finally:
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    main()
