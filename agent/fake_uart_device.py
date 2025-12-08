#!/usr/bin/env python3
"""Simulates a UART device using a virtual serial port pair (pty)."""
import json
import os
import pty
import sys
import time
from threading import Thread


def device_loop(master_fd):
    """Simulate device sending JSON messages and receiving commands."""
    print(f"[fake-device] Virtual device ready on fd {master_fd}")
    
    # Send some sample messages
    messages = [
        {"type": "status", "state": "idle", "level": 0, "pop_index": 0, "lives_left": 3, "ts": int(time.time() * 1000)},
        {"event_type": "pop_result", "mole_id": 2, "outcome": "hit", "reaction_ms": 450, "lives": 3, "lvl": 1},
        {"type": "telemetry", "sensor": "heart_rate", "samples": [75, 78, 80], "ts": int(time.time() * 1000)},
        {"event_type": "pop_result", "mole_id": 5, "outcome": "miss", "reaction_ms": 0, "lives": 2, "lvl": 1},
    ]
    
    for msg in messages:
        line = json.dumps(msg) + "\n"
        os.write(master_fd, line.encode())
        print(f"[fake-device] Sent: {line.strip()}")
        time.sleep(2)
    
    # Listen for commands
    print("[fake-device] Listening for commands...")
    while True:
        try:
            data = os.read(master_fd, 1024)
            if data:
                cmd = data.decode().strip()
                print(f"[fake-device] Received command: {cmd}")
        except OSError:
            break
        time.sleep(0.1)


def main():
    master, slave = pty.openpty()
    slave_name = os.ttyname(slave)
    
    print(f"[fake-device] Virtual serial port created: {slave_name}")
    print(f"[fake-device] Use this port with the bridge: --serial-port {slave_name}")
    
    # Start device simulation in background
    device_thread = Thread(target=device_loop, args=(master,), daemon=True)
    device_thread.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[fake-device] Stopping...")
        os.close(master)
        os.close(slave)


if __name__ == "__main__":
    main()
