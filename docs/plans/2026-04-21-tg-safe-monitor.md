# tg-safe-monitor Implementation Plan

> **For Hermes:** Implement with TDD. Keep the runtime simple: one async Python process with a Telegram bot plus a polling monitor loop.

**Goal:** Build a Dockerized Telegram bot that monitors configured Gnosis Safe addresses, records existing transactions at add-time, and posts only for newly discovered multisig transactions.

**Architecture:** Python async service using `python-telegram-bot`, `httpx`, and SQLite. Telegram commands manage monitored safes inside one configured group chat. A background polling loop reads all configured safes from SQLite, fetches Safe API transactions, records new transaction IDs, and posts notifications for newly seen items.

**Tech Stack:** Python 3.12, `python-telegram-bot`, `httpx`, `pydantic-settings`, SQLite, pytest, Docker.

---

## Deliverables

- Telegram command bot for one group chat
- Safe API client with pagination support
- SQLite persistence for safes + seen transactions
- Bootstrap-on-add behavior with no retroactive alerts
- New transaction notifications only
- Docker deployment files and `.env.example`
- Tests for bootstrap, detection, add/remove/list behavior
