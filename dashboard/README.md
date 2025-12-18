# Dashboard

MQTT backend + dashboard for the Whac-A-Mole game.

## Configuration

Copy `.env.example` to `.env` and configure:

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `MQTT_BROKER` | Yes | - | MQTT broker hostname |
| `MQTT_PORT` | Yes | - | MQTT broker port |
| `APP_PORT` | Yes | - | Dashboard server port |
| `APP_ROOT_PATH` | No | `""` | URL prefix for reverse proxy (e.g., `/jj`) |
| `DATA_DIR` | No | `.` | Directory for leaderboard data |

### `APP_ROOT_PATH`

Use this when deploying behind a reverse proxy that strips a URL prefix:

- **Local development**: Leave empty or unset
- **Behind proxy at `/jj`**: Set to `/jj`

The proxy should strip the prefix before forwarding to uvicorn. The `root_path` setting ensures URL generation works correctly.

### `DATA_DIR`

Directory where `leaderboard.json` is stored. Created automatically if it doesn't exist.
