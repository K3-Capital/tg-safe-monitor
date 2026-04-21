# tg-safe-monitor

Telegram bot that monitors:

- **Gnosis Safe multisig transactions**
- **direct Ethereum mainnet contract calls**

and posts to a Telegram group when a **new** matching transaction appears.

## What it does

- listens for Telegram commands in one configured group chat
- lets users add/remove monitored Safe addresses and monitored contract addresses
- supports optional human-readable labels for monitored addresses
- fetches Safe multisig transactions from the Safe Transaction Service API
- scans Ethereum mainnet blocks over JSON-RPC for direct calls to monitored contracts
- records existing Safe transactions when a Safe is first added
- starts contract monitoring from the current block when a contract is first added
- **does not** alert for historical transactions
- alerts only when a previously unseen matching transaction appears later

## Commands

- `/addsafe <safe_address> [label]`
- `/remsafe <safe_address>`
- `/listsafes`
- `/addcontract <contract_address> [label]`
- `/remcontract <contract_address>`
- `/listcontracts`
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
- `DATABASE_URL` — PostgreSQL connection string used for bot state
- `ETHEREUM_RPC_URL` — Ethereum mainnet JSON-RPC endpoint for contract-call monitoring
- `ETHEREUM_CONFIRMATION_BLOCKS` — optional confirmation lag before contract-call alerts
- `LOG_LEVEL` — runtime log level

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

The container expects an external PostgreSQL database via `DATABASE_URL` and an Ethereum RPC via `ETHEREUM_RPC_URL`.

## Add a Safe workflow

When a user adds a Safe, the bot:

1. fetches current Safe transactions from the Safe API
2. stores them as already known
3. confirms how many historical transactions were found
4. starts alerting only for newly discovered transactions from that point forward

## Add a Contract workflow

When a user adds a contract, the bot:

1. stores the checksum contract address and optional label
2. records the current mainnet block as the starting point
3. does **not** backfill historical calls
4. scans new blocks for direct transactions where `tx.to == contract_address`
5. alerts only once per newly seen transaction hash

Optional labels are shown in list output and alerts as `Label (0x...)`.
