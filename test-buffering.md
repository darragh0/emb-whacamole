# Event Buffering Test Plan

## Overview

This document describes how to test the event buffering feature that stores game events when the Python agent is disconnected, then flushes them on reconnect.

## Prerequisites

- MAX32655 feather board with ADI ISE I/O board
- Firmware rebuilt with buffering changes
- Python agent environment set up
- MQTT broker running

## Test Cases

---

### Test 1: Basic Buffering (Agent Disconnect Mid-Game)

**Purpose:** Verify events are buffered when agent disconnects and flushed on reconnect.

**Steps:**

1. Start the Python agent:
   ```bash
   cd agent && python -m agent
   ```

2. Start a game by pressing any button on the board

3. Play 2-3 moles (hit or miss some)

4. **While game is running**, stop the agent with `Ctrl+C`
   - Agent should send 'D' command before exiting
   - Board continues running (LEDs still work)

5. Continue playing 3-4 more moles on the board

6. Restart the agent:
   ```bash
   python -m agent
   ```

7. Watch the agent logs

**Expected Result:**
- On reconnect, agent requests identify ('I' command)
- Device responds with identify event
- **Buffered events appear immediately** (the 3-4 moles played while disconnected)
- Subsequent events stream normally

**Pass Criteria:**
- [ ] Game continues working while agent is down
- [ ] Buffered events are received on reconnect
- [ ] Event order is preserved (FIFO)
- [ ] No duplicate events

---

### Test 2: Timeout Fallback (Agent Crash)

**Purpose:** Verify 60s timeout marks agent as disconnected if 'D' command not received.

**Steps:**

1. Start the Python agent

2. Start a game on the board

3. **Kill the agent forcefully** (simulating crash):
   ```bash
   kill -9 $(pgrep -f "python -m agent")
   ```
   This prevents the 'D' command from being sent.

4. Wait 60+ seconds (timeout period)

5. Play a few moles during this time

6. Restart the agent

**Expected Result:**
- After 60s timeout, device starts buffering
- Events played after timeout are buffered
- Events are flushed on reconnect

**Pass Criteria:**
- [ ] Device detects disconnect via timeout
- [ ] Events after timeout are buffered
- [ ] Buffered events flush on reconnect

---

### Test 3: Buffer Capacity (Ring Buffer Overflow)

**Purpose:** Verify ring buffer overwrites oldest events when full (100 events max).

**Steps:**

1. Start agent, then disconnect it (`Ctrl+C`)

2. Play through **multiple full games** while disconnected:
   - Each game = ~90 events (session_start + 80 pop_results + 8 lvl_complete + session_end)
   - Play 2+ full games to exceed 100 event buffer

3. Reconnect the agent

**Expected Result:**
- Only the most recent ~100 events are received
- Oldest events are lost (overwritten)
- No crash or corruption

**Pass Criteria:**
- [ ] Device doesn't crash with buffer overflow
- [ ] Most recent events are preserved
- [ ] ~100 events received (buffer size)

---

### Test 4: Rapid Connect/Disconnect

**Purpose:** Verify correct behavior with rapid connection state changes.

**Steps:**

1. Start agent, play 2 moles

2. Disconnect agent (`Ctrl+C`)

3. Play 2 moles

4. Reconnect agent (wait for identify)

5. Immediately disconnect again (`Ctrl+C`)

6. Play 2 more moles

7. Reconnect agent

**Expected Result:**
- Each reconnect flushes buffered events
- Each disconnect starts buffering
- No events lost or duplicated

**Pass Criteria:**
- [ ] All events accounted for
- [ ] No duplicates
- [ ] Correct event ordering

---

### Test 5: Device Standalone Operation

**Purpose:** Verify game works completely without agent ever connected.

**Steps:**

1. Power on the board **without** starting the agent

2. Play a complete game (all 8 levels or lose all lives)

3. Start the agent after game completes

**Expected Result:**
- Game plays normally without agent
- On agent connect, buffered events from the game are flushed
- Device responds to identify

**Pass Criteria:**
- [ ] Game fully playable without agent
- [ ] LEDs and buttons work correctly
- [ ] Events buffered and flushed on first connect

---

## Verification Commands

### Check MQTT Messages (Dashboard)

Watch events arrive at the dashboard:
```bash
mosquitto_sub -h localhost -t "whac/+/game_events" -v
```

### Check Agent Logs

Agent logs show:
- `[Agent -> Device] b'D' (disconnect)` on disconnect
- `[Agent -> Device] b'I' (identify)` on reconnect
- Buffered events appearing after identify response

### Check Buffer Count (Debug)

If you add debug logging to `event_buffer_flush()`:
```c
void event_buffer_flush(void) {
    printf("{\"debug\":\"flushing %d buffered events\"}\n", event_buffer.count);
    // ... rest of function
}
```

---

## Troubleshooting

| Issue | Possible Cause | Solution |
|-------|---------------|----------|
| No events on reconnect | Buffer not flushing | Check `identify_requested` triggers flush |
| Events lost during disconnect | 'D' not received | Check agent cleanup runs before close |
| Game freezes on disconnect | Blocking on UART | Verify `xQueueSend(..., 0)` non-blocking |
| Buffer overflow crash | Buffer index error | Check modulo arithmetic in ring buffer |

---

## Summary Table

| Test | Description | Key Validation |
|------|-------------|----------------|
| 1 | Basic buffering | Events stored and flushed |
| 2 | Timeout fallback | 60s timeout triggers buffering |
| 3 | Buffer overflow | Ring buffer overwrites oldest |
| 4 | Rapid connect/disconnect | State transitions correct |
| 5 | Standalone operation | No agent required for gameplay |
