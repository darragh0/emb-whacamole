# Demo Cheat Sheet - Whac-A-Mole IoT Project

Quick reference for interview. Maps spec requirements to code locations.

---

## Scoring Categories Quick Reference

| Category (Weight) | Where to Demo |
|-------------------|---------------|
| Project Demo (15%) | Live game on device + dashboard |
| Real-time (20%) | `game.c`, task priorities, 5ms polling |
| Comms/Resilience (20%) | `agent.c` buffering, `bridge.py` reconnect |
| Innovation (30%) | Leaderboard, analytics, multi-device |
| Code Quality (15%) | Comments, modularity, clean architecture |

---

## Requirement Mapping

### 1. FreeRTOS on MAX32655 with Maxim SDK
**Spec**: "Maxim SDK framework running on MAX32655 feather board"

| File | What It Shows |
|------|---------------|
| `emb/project.mk` | SDK configuration |
| `emb/src/main.c` | `vTaskStartScheduler()` call |
| `emb/FreeRTOSConfig.h` | RTOS configuration |

---

### 2. Different Threads at Different Priorities
**Spec**: "Control/data acquisition and agent functionality must run in different threads at different priorities"

| Task | Priority | File:Line | Purpose |
|------|----------|-----------|---------|
| Pause | `configMAX_PRIORITIES - 1` (4) | `uart_cmd.c:115` | Highest - instant pause response |
| Game | `configMAX_PRIORITIES - 2` (3) | `main.c` | Real-time game control |
| Agent | `configMAX_PRIORITIES - 3` (2) | `main.c` | Event forwarding to UART |
| Idle | 0 | Built-in | FreeRTOS idle task |

**Key Point**: Game task runs at higher priority than Agent task so button polling is never delayed by UART transmission.

---

### 3. Bi-directional Queuing Mechanism
**Spec**: "Bi-directional queuing mechanism must be implemented"

```
┌─────────────┐  event_queue   ┌─────────────┐
│  Game Task  │ ─────────────> │ Agent Task  │   (Game -> Agent)
└─────────────┘                └─────────────┘
       ^
       │ cmd_queue
       │
┌─────────────┐
│  UART ISR   │   (Agent -> Game via ISR)
└─────────────┘
```

| Queue | Direction | File:Line | Purpose |
|-------|-----------|-----------|---------|
| `event_queue` | Game → Agent | `rtos_queues.c:11` | Game events (pop_result, lvl_complete) |
| `cmd_queue` | ISR → Game | `rtos_queues.c:12` | Commands (reset, start, set_level) |

**Code to show**:
- Queue creation: `rtos_queues.c:11-12`
- Sending to queue: `game.c` (search `xQueueSend`)
- Receiving from queue: `agent.c:139`, `game.c` (search `xQueueReceive`)

---

### 4. Real-time Control Aspect
**Spec**: "Must have a real-time control aspect"

**Our Implementation**: Whac-A-Mole game with deterministic button polling

| Aspect | File:Line | Detail |
|--------|-----------|--------|
| 5ms button polling | `game.c` (game loop) | `MS_SLEEP(5)` - deterministic sampling |
| LED multiplexing | `led.c` | Charlieplexing 9 LEDs with 4 pins |
| Reaction time measurement | `game.c` | `xTaskGetTickCount()` for ms precision |
| Priority inversion prevention | Task priorities | Game > Agent ensures no UART delays |

**Key Point**: Button press detection within 5ms worst-case latency.

---

### 5. Cloud Backend Communication
**Spec**: "Communicate with cloud back-end for data aggregation and accept commands"

**MQTT Topics**:
```
whac/<device_id>/game_events  → Dashboard (events from device)
whac/<device_id>/state        → Dashboard (online/offline status)
whac/<device_id>/commands     ← Dashboard (commands to device)
```

| Component | File | Purpose |
|-----------|------|---------|
| Dashboard MQTT sub | `dashboard/mqtt.py:48` | Subscribe to events |
| Dashboard MQTT pub | `dashboard/mqtt.py:27` | Publish commands |
| Agent MQTT client | `agent/mqtt.py` | Bridge device to broker |

**Data Flow**:
```
Device → UART → Agent → MQTT → Dashboard
Dashboard → MQTT → Agent → UART → Device
```

---

### 6. Agent Disconnect Tolerance & Data Buffering
**Spec**: "Real-time control must execute correctly whether or not agent is attached. Buffer acquired data."

**THIS IS KEY FOR RESILIENCE MARKS**

| Feature | File:Line | Detail |
|---------|-----------|--------|
| Ring buffer (100 events) | `agent.c:26-31` | `evbuf_push()`, `evbuf_pop()` |
| Connection state flag | `agent.c:14` | `agent_connected` volatile bool |
| Timeout detection | `agent.c:124-127` | 60s timeout marks disconnected |
| Buffer flush on reconnect | `agent.c:134-135` | `send_identify()` then `evbuf_flush()` |
| Disconnect command | `uart_cmd.c:52-55` | 'D' command starts buffering |
| Agent reconnect | `bridge.py:200-165` | 10-min auto-reconnect with retry |

**Demo Scenario**:
1. Start game, generate some events
2. Disconnect USB cable (or Ctrl+C agent)
3. Continue playing - game works fine
4. Reconnect - buffered events appear in dashboard

---

### 7. Proprietary Protocol
**Spec**: "Invent proprietary protocol for communication between agent and embedded device"

**Our Protocol**: Single-byte commands + JSON Lines events

**Commands (Agent → Device)**:
| Byte | Command | Handler |
|------|---------|---------|
| `I` | Identify | Returns device ID |
| `P` | Pause toggle | Suspends/resumes game |
| `R` | Reset | Resets game state |
| `S` | Start | Starts new session |
| `1-8` | Set level | Changes difficulty |
| `D` | Disconnect | Starts buffering |

**Events (Device → Agent)** - JSON Lines:
```json
{"event_type":"identify","device_id":"a1b2c3d4e5"}
{"event_type":"session_start"}
{"event_type":"pop_result","mole_id":3,"outcome":"hit","reaction_ms":245,"lives":5,"lvl":1,"pop":1,"pops_total":5}
{"event_type":"lvl_complete","lvl":1}
{"event_type":"session_end","win":"true"}
```

| Protocol Element | File:Line |
|------------------|-----------|
| Command definitions | `bridge.py:71-85` |
| Event JSON formatting | `agent.c:81-114` |
| Command parsing | `uart_cmd.c:47-84` |

---

## Innovation Points (30% of grade)

Features beyond basic requirements:

| Feature | Files | Description |
|---------|-------|-------------|
| **Leaderboard** | `leaderboard.py` | Persistent top scores with scoring algorithm |
| **Live Dashboard** | `static/js/main.js` | Real-time device status, game state |
| **Multi-device Support** | `__main__.py:107` | MQTT wildcards `whac/+/...` |
| **Reaction Time Analytics** | `leaderboard.py:42-87` | Speed bonus scoring |
| **Auto-discovery** | `__main__.py:68-70` | Devices appear automatically |
| **Subpath Deployment** | `app.py:36-37` | Works behind reverse proxy |

---

## Quick Code Tour (10 min interview)

### Embedded (C) - 30 seconds each
1. `main.c` - Task creation, scheduler start
2. `game.c` - Game loop, button polling, event generation
3. `agent.c` - Event forwarding, buffering logic
4. `uart_cmd.c` - ISR, command dispatch

### Agent (Python) - 30 seconds each
1. `bridge.py:111-157` - `run()` lifecycle
2. `bridge.py:161-198` - Event loop with reconnect
3. `mqtt.py` - MQTT wrapper

### Dashboard (Python) - 30 seconds each
1. `__main__.py:149-168` - Entry point, MQTT subscription
2. `app.py` - REST API endpoints
3. `leaderboard.py:42-87` - Scoring algorithm

---

## Common Interview Questions

**Q: How do you ensure real-time performance?**
> Game task at priority 3, Agent at priority 2. Button polling at 5ms intervals. FreeRTOS preemption ensures game is never blocked by UART.

**Q: What happens if WiFi/agent disconnects?**
> Device continues running. Events buffered in ring buffer (100 events). On reconnect, agent sends 'I', device responds with ID then flushes buffer.

**Q: How do commands reach the device?**
> Dashboard → REST API → MQTT publish → Agent subscribes → UART write → ISR receives → Queue to game task.

**Q: Why JSON for events but single bytes for commands?**
> Commands are latency-sensitive (pause must be instant). Events contain structured data that benefits from JSON. Asymmetric by design.

**Q: How is the score calculated?**
> `100 * level * speed_bonus` per hit. Speed bonus: 2x at 0ms, 1x at 1000ms. Perfect level bonus: 500 * level. Lives bonus: +10% per remaining life.
