# Contract Call Monitoring Implementation Plan

> **For Hermes:** Use subagent-driven-development and test-driven-development when executing this plan.

**Goal:** Add support for monitoring direct Ethereum mainnet transactions sent to configured contract addresses and post Telegram alerts for newly observed calls.

**Architecture:** Keep Safe monitoring intact and add a second monitor path for contract addresses. A dedicated RPC-backed contract monitor should scan newly mined blocks from an ENV-configured mainnet RPC, filter transactions where `tx.to` matches any monitored contract address, persist seen transaction hashes, and alert only for new direct calls.

**Tech Stack:** Python 3.12, uv, python-telegram-bot, psycopg/Postgres, Ethereum JSON-RPC over HTTP.

---

## Product assumptions to confirm

1. Monitoring is for **direct L1 transactions only** where `transaction.to == monitored_contract_address`.
2. **Internal calls** (contract-to-contract calls), traces, and event-log-based detection are out of scope initially.
3. Start with **Ethereum mainnet only** using one ENV-configured RPC URL.
4. Initial version should monitor **mined transactions**, not mempool/pending txs.
5. When a contract is added, bootstrap should start from the **current block** (or a small configurable confirmation-safe offset) and should **not backfill historical transactions**.
6. Separate bot commands are acceptable, e.g. `/addcontract`, `/remcontract`, `/listcontracts`.

---

## Design outline

### Data model changes

Current storage is Safe-specific (`monitored_safes`, `seen_transactions`). Add contract-specific storage rather than overloading the Safe tables.

Proposed new tables:

- `monitored_contracts`
  - `contract_address TEXT PRIMARY KEY`
  - `added_by_user_id BIGINT`
  - `added_by_username TEXT`
  - `start_block BIGINT NOT NULL`
  - `added_at TIMESTAMPTZ NOT NULL`
- `seen_contract_transactions`
  - `contract_address TEXT NOT NULL`
  - `tx_hash TEXT NOT NULL`
  - `block_number BIGINT NOT NULL`
  - `first_seen_at TIMESTAMPTZ NOT NULL`
  - `PRIMARY KEY (contract_address, tx_hash)`
- `monitor_state`
  - `monitor_key TEXT PRIMARY KEY`
  - `monitor_value TEXT NOT NULL`

`monitor_state` should store the contract scanner cursor, e.g. `ethereum_mainnet_last_scanned_block`.

### Runtime design

Add a dedicated `EthereumRpcClient` with methods such as:

- `get_block_number()`
- `get_block_with_transactions(block_number)`

Add a `ContractMonitorService` that:

- validates and normalizes contract addresses
- stores new monitored contracts with a start block
- scans blocks from the stored cursor up to the current chain head minus optional confirmation lag
- filters txs where `to` equals a monitored contract
- records seen tx hashes to avoid duplicate alerts

Add a dedicated `ContractMonitorLoop` that runs alongside the existing Safe loop.

### Message format

Initial contract alert should include:

- contract address
- tx hash
- block number
- from
- to
- value
- function selector (first 4 bytes of calldata if present)
- calldata length

This avoids requiring ABI decoding for v1.

### Performance approach

Important: **scan each new block once**, then filter for all monitored contracts in memory. Do not perform one RPC query per contract. This keeps the design viable as the contract watchlist grows.

---

## Proposed implementation tasks

### Task 1: Add failing config and model tests

**Objective:** Establish config and model behavior for RPC-backed contract monitoring.

**Files:**
- Modify: `tests/test_config.py`
- Create: `tests/test_contract_service.py`
- Modify: `src/tg_safe_monitor/models.py`

**Test targets:**
- `ETHEREUM_RPC_URL` is required
- contract addresses are normalized to checksum addresses
- bootstrap starts at the chosen start block and does not backfill old txs
- only txs with `to == monitored_contract` alert

### Task 2: Add contract monitoring models

**Objective:** Introduce contract-specific dataclasses without breaking Safe monitoring.

**Files:**
- Modify: `src/tg_safe_monitor/models.py`

**Add:**
- `MonitoredContract`
- `ContractCallTransaction`
- `ContractMonitorNotification`
- `AddContractResult`

### Task 3: Extend repository interface and storage

**Objective:** Persist monitored contracts, seen contract txs, and monitor cursor state.

**Files:**
- Modify: `src/tg_safe_monitor/storage.py`
- Modify: `tests/test_service.py` if repository test doubles need interface updates

**Add repository methods:**
- `add_contract(...)`
- `remove_contract(...)`
- `list_contracts()`
- `list_contract_addresses()`
- `is_contract_monitored(...)`
- `record_seen_contract_transaction(...)`
- `has_seen_contract_transaction(...)`
- `get_monitor_state(key)`
- `set_monitor_state(key, value)`

### Task 4: Add Ethereum RPC client

**Objective:** Fetch new blocks and transactions from an ENV-configured mainnet RPC.

**Files:**
- Create: `src/tg_safe_monitor/ethereum_rpc.py`
- Create: `tests/test_ethereum_rpc.py`

**Methods:**
- `get_block_number()`
- `get_block_with_transactions(block_number: int)`

Use JSON-RPC methods:
- `eth_blockNumber`
- `eth_getBlockByNumber` with `true` for full tx objects

### Task 5: Add contract monitor service

**Objective:** Implement add/remove/list/poll logic for monitored contracts.

**Files:**
- Create: `src/tg_safe_monitor/contract_service.py`
- Create: `tests/test_contract_service.py`

**Behavior:**
- `add_contract()` stores the normalized address and current start block
- `poll_once()` loads the last scanned block, scans forward, filters direct calls, records seen txs, and returns notifications
- scanner cursor advances only after a block is processed successfully

### Task 6: Add Telegram command handling for contracts

**Objective:** Let group users manage contract monitoring from Telegram.

**Files:**
- Modify: `src/tg_safe_monitor/bot_logic.py`
- Modify: `src/tg_safe_monitor/bot.py`
- Create/Modify tests for command responses

**Commands:**
- `/addcontract <address>`
- `/remcontract <address>`
- `/listcontracts`

### Task 7: Add contract alert formatting

**Objective:** Format readable Telegram alerts for direct contract calls.

**Files:**
- Modify: `src/tg_safe_monitor/messages.py`
- Add tests for alert text formatting

### Task 8: Wire runtime and config

**Objective:** Run Safe and contract monitoring together.

**Files:**
- Modify: `src/tg_safe_monitor/config.py`
- Modify: `src/tg_safe_monitor/app.py`
- Modify: `.env.example`
- Modify: `README.md`

**Add env vars:**
- `ETHEREUM_RPC_URL`
- optional `ETHEREUM_CONFIRMATION_BLOCKS` (default small positive integer)

### Task 9: End-to-end verification

**Objective:** Verify Safe monitoring still works and contract monitoring works on a live high-volume contract.

**Files:**
- Tests only / docs only

**Checks:**
- `uv run pytest`
- add sample contract watch for `0xbd216513d74c8cf14cf4747e6aaa6420ff64ee9e`
- confirm no historical spam on add
- confirm new direct calls alert once

---

## Open questions for Val

1. Do you want **separate commands** (`/addcontract`, `/remcontract`, `/listcontracts`) or a generic target model eventually?
2. Should alerts fire only for **mined txs** (recommended) or also for **pending mempool txs**?
3. On add, is it acceptable to **start from current block forward only** rather than backfilling history?
4. Should we include only **successful mined txs**, or alert on **all mined direct calls** including reverted txs if we can detect them?
5. Is a simple v1 alert with **tx hash / from / value / selector / block** enough, or do you want **ABI-based decoded method names/arguments** soon?
6. Support optional **human labels** for monitored addresses so operators can distinguish them easily in commands, lists, and alerts.

---

## Recommendation

My recommended v1 defaults are:

- Ethereum mainnet only
- one `ETHEREUM_RPC_URL`
- mined txs only
- direct calls only (`tx.to == contract`)
- no internal traces
- no historical backfill on add; start from current block
- alert on all newly mined direct calls
- separate Telegram commands for contracts
- optional human-readable labels for monitored addresses
- include 4-byte selector, not full ABI decoding yet

## Label support update

Labels should be part of v1 so humans can distinguish multiple monitored addresses quickly.

Recommended behavior:

- `/addcontract <address> [label...]`
- `/addsafe <address> [label...]`
- store nullable `label` on monitored addresses
- show `label (0x...)` in list output and alert messages when label is present
- if no label is set, fall back to raw checksum address

Schema updates should therefore include an optional `label TEXT` column for monitored contracts, and ideally also for monitored safes to keep the UX consistent.
