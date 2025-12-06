# Bridge

A simple Serial-to-MQTT bridge for the Whac-A-Mole game.

Build, flash, and run `../emb/` code, then observe logs to see data being transferred over UART.

> [!WARNING]
> Pending integration with code for MQTT interaction

## Files

```
.
├── config
│   └── logging.json                      # Config for console logging (stdout/stderr)
├── pyproject.toml
├── README.md
├── ruff.toml
└─── src
     └── agent
         ├── argparser.py                  # Argument parser setup
         ├── bridge.py                     # Main serial interaction code
         ├── __init__.py
         ├── logging_conf.py               # Logging config (for logging.json, can ignore this)
         └── __main__.py                   # Main entry point
```
