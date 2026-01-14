## Hourly LLM Check-in Bot

This service runs a Telegram bot that asks for hourly check-ins during daytime,
parses the reply with xAI, and logs it into `track/activities.db` via `track/track.py`.

## Setup

Environment variables:
- `TELEGRAM_BOT_TOKEN` (required)
- `XAI_API_KEY` (required)
- `XAI_MODEL` (optional, default: `grok-2-latest`)
- `XAI_TIMEOUT_SECONDS` (optional; set for long reasoning timeouts)
- `TELEGRAM_CHAT_ID` (optional; if unset, send `/start` once to register)
- `TIMEZONE` (optional, e.g. `America/Los_Angeles`)
- `DAY_START_HOUR` (optional, default: `9`, 0-23)
- `DAY_END_HOUR` (optional, default: `18`, 0-23)
- `CHECKIN_PROMPT` (optional)
- `CHECKIN_TTL_MINUTES` (optional, default: `120`)
- `STATE_PATH` (optional, default: `bot_state.json`)
- `LOG_LEVEL` (optional, default: `INFO`)
- `LOG_VERBOSE` (optional; set to `1` to include polling logs)
- `LOG_DIR` (optional; folder to write `hourly_llm_checkin.log`)

Run:
```bash
uv run python main.py
```

## Usage

- Send `/start` in your bot chat to register the chat ID.
- The bot sends an hourly prompt during daytime.
- Reply in natural language. Include duration and quadrant (Q1-4) for best results.
- Send `/checkin` to request a prompt immediately.
- Send `/list` or `/list 5` to see recent entries.
- State (chat ID + last prompt timestamp) is stored in `bot_state.json` by default.

## Tests

```bash
python -m unittest
```
