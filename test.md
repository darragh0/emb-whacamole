● Based on the project spec and thorough codebase exploration, here are the most innovative aspects for your presentation. Innovation is 30% of your grade—the highest weighted category—so these points are critical.

---

Top Innovation Highlights

1. Lock-Free SPSC Ring Buffer for Offline Resilience

emb/src/agent.c:20-42

- True lock-free design using single-producer/single-consumer pattern
- Device continues playing when disconnected—buffers up to 100 events
- Auto-flush on reconnect—no data loss during network outages
- This is an industrial IoT pattern applied to a game

2. Deterministic Real-Time Game Loop with ms-Precision Timing

emb/src/game.c:141-187

- 5ms polling interval without hardware timers or interrupts
- Records exact reaction time (down to 5ms granularity)
- Adaptive difficulty: window shrinks from 1500ms → 275ms across levels
- Software debouncing integrated into the timing loop

3. Three-Tier Fault-Tolerant Architecture

Device Buffer (100 events) → MQTT Broker → Dashboard (persistent)

- System survives: agent disconnect, broker restart, dashboard crash
- Each layer independently buffers—cascading resilience

4. Priority-Based Multi-Task Scheduling with ISR Integration

emb/src/uart_cmd.c:34-88

- Game task (P3) > Agent task (P2) for hard real-time guarantees
- Pause runs at highest priority (configMAX_PRIORITIES - 1)—instant response
- Uses FreeRTOS ISR-safe primitives: xQueueSendFromISR, xTaskNotifyFromISR
- Context switch optimization: portYIELD_FROM_ISR(woken)

5. Hardware Abstraction via Logical Pin Mapping

emb/src/leds.c:6-15, emb/src/btns.c:5-14

- Physical pin layout ≠ logical game layout
- PCB can be redesigned without code changes
- Inline bitwise operations for zero-overhead abstraction

6. Speed-Based Scoring Algorithm

dashboard/src/dashboard/leaderboard.py:37-46

- Score: 100 × level × speed_bonus per hit
- Speed bonus: 2x at 0ms → 0.5x at 1000ms reaction time
- Faster reactions = higher multiplier

---

Innovation Slide Summary

| Innovation                      | Why It Matters                              |
| ------------------------------- | ------------------------------------------- |
| Lock-free ring buffer           | No mutexes in real-time path; works offline |
| ms-precision polling loop       | Hard real-time without HW timers            |
| 3-tier buffering                | Survives any single failure                 |
| Priority-based ISR integration  | Game never blocked by I/O                   |
| Logical-physical pin decoupling | Hardware-independent code                   |
| Speed-based scoring             | Rewards fast reactions                      |

---

Key Talking Point

"We treated a simple game as an opportunity to demonstrate production-grade embedded patterns: lock-free concurrency, offline tolerance, priority-based scheduling, and hardware abstraction—techniques typically found in industrial IoT systems."

This frames your project as engineering-focused rather than feature-focused, which aligns with the rubric's emphasis on real-time implementation and resilience.
