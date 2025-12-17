#!/usr/bin/env python3
"""
Mock game simulator - sends fake MQTT events to test the dashboard.
Run this while the dashboard is running to see the live score chart in action.

Usage:
    python mock_game.py [--device-id DEVICE_ID] [--broker BROKER] [--port PORT]
"""

import argparse
import json
import random
import time

import paho.mqtt.client as mqtt


def simulate_game(client: mqtt.Client, device_id: str) -> None:
    """Simulate a full game session with random outcomes."""
    base_topic = f"whac/{device_id}"

    # Publish device online
    client.publish(f"{base_topic}/state", "online", qos=1)
    print(f"[{device_id}] Device online")
    time.sleep(0.5)

    # Start session
    client.publish(
        f"{base_topic}/game_events",
        json.dumps({"event_type": "session_start"}),
        qos=1,
    )
    print(f"[{device_id}] Session started")
    time.sleep(1)

    lives = 5
    level = 1
    pop_num = 0

    # Simulate levels 1-8 (or until lives run out)
    while level <= 8 and lives > 0:
        pops_in_level = 10
        print(f"\n[{device_id}] === Level {level} ===")

        for pop_in_level in range(1, pops_in_level + 1):
            if lives <= 0:
                break

            pop_num += 1
            mole_id = random.randint(0, 7)

            # Simulate outcome (higher levels = harder = more misses)
            hit_chance = max(0.4, 0.9 - (level * 0.05))
            rand = random.random()

            if rand < hit_chance:
                outcome = "hit"
                # Faster reactions at lower levels, slower at higher
                base_reaction = 200 + (level * 30)
                reaction_ms = random.randint(base_reaction, base_reaction + 300)
            elif rand < hit_chance + 0.15:
                outcome = "miss"
                reaction_ms = 0
                lives -= 1
            else:
                outcome = "late"
                reaction_ms = random.randint(800, 1500)
                lives -= 1

            event = {
                "event_type": "pop_result",
                "mole_id": mole_id,
                "outcome": outcome,
                "reaction_ms": reaction_ms,
                "lives": lives,
                "lvl": level,
                "pop": pop_in_level,
                "pops_total": pops_in_level,
            }

            client.publish(f"{base_topic}/game_events", json.dumps(event), qos=1)

            outcome_symbol = "✓" if outcome == "hit" else "✗" if outcome == "miss" else "⏱"
            print(
                f"  Pop {pop_num:2d}: {outcome_symbol} {outcome.upper():4s} "
                f"mole={mole_id} reaction={reaction_ms:4d}ms lives={lives}"
            )

            # Wait between pops (faster at higher levels)
            delay = max(0.3, 1.0 - (level * 0.08))
            time.sleep(delay)

            if lives <= 0:
                break

        # Level complete (if we didn't run out of lives)
        if lives > 0:
            client.publish(
                f"{base_topic}/game_events",
                json.dumps({"event_type": "lvl_complete", "lvl": level}),
                qos=1,
            )
            print(f"[{device_id}] Level {level} complete!")
            level += 1
            time.sleep(1)

    # Session end
    won = lives > 0 and level > 8
    client.publish(
        f"{base_topic}/game_events",
        json.dumps({"event_type": "session_end", "win": str(won).lower()}),
        qos=1,
    )
    print(f"\n[{device_id}] Session ended: {'VICTORY!' if won else 'GAME OVER'}")
    time.sleep(2)


def main() -> None:
    parser = argparse.ArgumentParser(description="Mock game simulator for dashboard testing")
    parser.add_argument("--device-id", default="mock-device-001", help="Device ID to simulate")
    parser.add_argument("--broker", default="localhost", help="MQTT broker host")
    parser.add_argument("--port", type=int, default=1883, help="MQTT broker port")
    parser.add_argument("--games", type=int, default=1, help="Number of games to simulate")
    args = parser.parse_args()

    print(f"Connecting to MQTT broker at {args.broker}:{args.port}...")
    client = mqtt.Client(
        client_id=f"mock-{args.device_id}",
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
    )

    try:
        client.connect(args.broker, args.port, 60)
        client.loop_start()
        print("Connected!\n")

        for game_num in range(1, args.games + 1):
            print(f"{'='*50}")
            print(f"  GAME {game_num}/{args.games}")
            print(f"{'='*50}")
            simulate_game(client, args.device_id)

            if game_num < args.games:
                print("\nStarting next game in 3 seconds...")
                time.sleep(3)

    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        # Publish offline status
        client.publish(f"whac/{args.device_id}/state", "offline", qos=1)
        time.sleep(0.5)
        client.loop_stop()
        client.disconnect()
        print("\nDisconnected.")


if __name__ == "__main__":
    main()
