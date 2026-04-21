# tg-safe-monitor

Telegram bot that monitors Gnosis Safe multisig transactions and posts to a Telegram group when a **new** transaction appears.

## What it does

- listens for Telegram commands in one configured group chat
- lets users add/remove monitored Safe addresses
- fetches Safe multisig transactions from the Safe Transaction Service API
- records all existing transactions when a Safe is first added
- **does not** alert for historical transactions
- alerts only when a previously unseen transaction appears later

## Commands

- `/addsafe <safe_address>`
- `/remsafe <safe_address>`
- `/listsafes`
- `/status`
- `/help`

## Configuration

Copy `.env.example` to `.env` and fill in the values:

- `TELEGRAM_BOT_TOKEN` — Telegram bot token
- `TELEGRAM_CHAT_ID` — target group chat id where the bot runs and posts alerts
- `TG_ADMIN_USER_IDS` — optional comma-separated allowlist; leave empty to allow any group member
- `SAFE_API_TOKEN` — Safe API authorization token sent as the raw `Authorization` header value
- `SAFE_API_BASE_URL` — Safe transaction service base URL
- `POLL_INTERVAL_SECONDS` — polling interval for new transactions
- `SQLITE_PATH` — SQLite database file path
- `LOG_LEVEL` — runtime log level

## Local development with uv

This project uses **uv** for Python version and package management.

### First-time setup

```bash
uv python pin 3.12
uv sync --extra dev
```

### Run tests

```bash
uv run pytest
```

### Run the bot locally

```bash
uv run python -m tg_safe_monitor
```

## Docker deployment

```bash
docker compose up --build -d
```

Persistent data is stored in `./data` via the mounted SQLite volume.

## Add a Safe workflow

When a user adds a Safe, the bot:

1. fetches current Safe transactions from the Safe API
2. stores them as already known
3. confirms how many historical transactions were found
4. starts alerting only for newly discovered transactions from that point forward
