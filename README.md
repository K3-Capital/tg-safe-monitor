# tg-safe-monitor

Telegram bot that monitors:

- **Gnosis Safe multisig transactions**
- **direct Ethereum mainnet contract calls**
- **EOA-signed Ethereum mainnet transactions**

and posts to a Telegram group when a **new** matching transaction appears.

## What it does

- listens for Telegram commands in one configured group chat
- lets users add/remove/list monitored addresses with a simple generic command surface
- automatically classifies an added address as a:
  - Safe
  - contract
  - EOA
- supports optional human-readable labels for monitored addresses
- fetches Safe multisig transactions from the Safe Transaction Service API
- scans Ethereum mainnet blocks over JSON-RPC for:
  - direct calls to monitored contracts
  - transactions signed by monitored EOAs
- records existing Safe transactions when a Safe is first added
- starts contract/EOA monitoring from the current block when first added
- **does not** alert for historical transactions
- skips **reverted contract transactions** to reduce noise
- alerts only when a previously unseen matching transaction appears later

## Commands

- `/add <address> [label]`
- `/remove <address>`
- `/list`
- `/status`
- `/help`

## Configuration

Copy `.env.example` to `.env` and fill in the values:

- `TELEGRAM_BOT_TOKEN` — Telegram bot token
- `TELEGRAM_CHAT_ID` — target group chat id where the bot runs and posts alerts
- `TG_ADMIN_USER_IDS` — optional comma-separated allowlist; leave empty to allow any group member
- `SAFE_API_TOKEN` — Safe API authorization token sent as the raw `Authorization` header value
- `SAFE_API_BASE_URL` — Safe transaction service base URL used for Safe monitoring and Safe detection
- `POLL_INTERVAL_SECONDS` — polling interval for new transactions
- `ETHEREUM_RPC_URL` — Ethereum mainnet JSON-RPC endpoint for contract/EOA monitoring
- `ETHEREUM_CONFIRMATION_BLOCKS` — optional confirmation lag before contract/EOA alerts
- `LOG_LEVEL` — runtime log level

Optional database settings:

- `DATABASE_URL` — PostgreSQL connection string used for bot state
- `POSTGRES_DB` — local docker-compose Postgres database name
- `POSTGRES_USER` — local docker-compose Postgres username
- `POSTGRES_PASSWORD` — local docker-compose Postgres password

## Local development with uv

This project uses **uv** for Python version and package management.

### First-time setup

```bash
cp .env.example .env
uv sync --extra dev
```

Use your existing DigitalOcean/Postgres connection string and mainnet RPC, for example:

```bash
DATABASE_URL="postgresql://user:***@db-host:25060/defaultdb?sslmode=require"
ETHEREUM_RPC_URL="https://mainnet.gateway.tenderly.co/your-key"
```

### Run quality checks

```bash
uv run ruff check .
uv run pyright
uv run pytest -q
```

### Run the bot locally

```bash
uv run python -m tg_safe_monitor
```

## Docker deployment

### Local testing with bundled Postgres

```bash
docker compose up --build -d
```

This starts:

- `postgres` — a local Postgres service for testing
- `tg-safe-monitor` — the bot, configured to use that local DB by default

### Using an external Postgres database

Set `DATABASE_URL` in `.env` and run the same command:

```bash
docker compose up --build -d
```

If `DATABASE_URL` is present, the bot will use it instead of the bundled local default.

## Add workflow

When a user adds an address, the bot:

1. normalizes the checksum address
2. classifies it as Safe / contract / EOA
3. stores the optional human label
4. bootstraps the monitor correctly for that address type
5. starts alerting only for newly discovered matching transactions from that point forward

## Alert links

- **Safe transactions:** include a Safe App link
- **Contract transactions:** include an Etherscan tx link
- **EOA transactions:** include an Etherscan tx link

Optional labels are shown in list output and alerts as `Label (0x...)`.
