# Testing the Live Score Graph

## Quick Test (No Hardware)

```bash
# Terminal 1 - Start dashboard
cd dashboard
python -m dashboard

# Terminal 2 - Run mock game
cd dashboard
python mock_game.py
```

Open dashboard in browser → Watch live score chart appear during gameplay.

---

## Full Test (With Hardware)

### 1. Start Dashboard (on alderaan)

```bash
ssh jayjay@alderaan.software-engineering.ie
cd ~/emb-whacamole/dashboard
python -m dashboard
```

### 2. Start Agent (on laptop with board)

```bash
cd agent
cp .env.example .env  # Ensure MQTT_BROKER=alderaan.software-engineering.ie
agent /dev/ttyUSB0    # or your serial port
```

### 3. Open Dashboard

Go to: **https://alderaan.software-engineering.ie/jj/**

### 4. Play a Game

Press buttons on the board to play.

### 5. Verify These Features

| Feature | Where to Check |
|---------|----------------|
| **Live score chart** | Appears in device card during gameplay |
| **Live score counter** | Shows "X pts" above the chart |
| **Point colors** | 🟢 Hit, 🔴 Miss, 🟡 Late |
| **Full analysis chart** | Click "View Game Analysis" on a past session |

### Expected Result

```
┌─────────────────────────────────────┐
│ LIVE SCORE                  847 pts │
│ ┌─────────────────────────────────┐ │
│ │      🟢──🟢                     │ │
│ │   🟢──   🔴                     │ │
│ │ 🟢                              │ │
│ └─────────────────────────────────┘ │
│ [HIT/MISS/LATE event log below]     │
└─────────────────────────────────────┘
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| No chart appears | Check browser console for JS errors |
| Device not showing | Check agent is connected to MQTT |
| Chart not updating | Ensure dashboard is polling `/devices` |
