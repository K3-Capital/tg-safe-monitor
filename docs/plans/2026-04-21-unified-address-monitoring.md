# Unified Address Monitoring Iteration Plan

> **For Hermes:** Use test-driven-development when executing this plan. Keep the existing Safe and contract monitoring working while adding generic address handling.

**Goal:** Let non-technical users add a single address and have the bot automatically classify it as a Safe, contract, or EOA, then monitor the correct activity type with the right links and noise filters.

**Architecture:** Keep Safe monitoring as a Safe Transaction Service integration, keep block-scanning for Ethereum mainnet activity, and add an address-classification layer plus EOA monitoring. Use one generic command surface for users, while preserving old specialized commands as aliases for compatibility.

**Tech Stack:** Python 3.12, uv, PostgreSQL, python-telegram-bot, Safe Transaction Service API, Ethereum JSON-RPC.

---

## Requirements captured from Val

1. Users should be able to add **just an address** and the bot should determine whether it is:
   - a Gnosis Safe
   - a smart contract
   - an EOA
2. EOAs should alert on **transactions signed from that EOA**.
3. Contract monitoring should **skip reverting transactions** to reduce noise.
4. EOA and contract alerts should include an **Etherscan tx link**.
5. Safe alerts should include a **Safe App tx link** using the Safe address + `safeTxHash`.
6. Labels remain important and should continue to work for all monitored addresses.

---

## Recommended product defaults

- Add generic commands:
  - `/add <address> [label...]`
  - `/remove <address>`
  - `/list`
- Keep old commands as aliases:
  - `/addsafe`, `/addcontract`, etc.
- Address classification rules:
  1. normalize checksum address
  2. call `eth_getCode`
  3. if code is empty => EOA
  4. if code exists => probe Safe API to determine if it is a Safe
  5. if Safe probe fails / returns not found => generic contract
- Safe links:
  - `https://app.safe.global/transactions/tx?safe=eth:{safe_address}&id=multisig_{safe_address}_{safe_tx_hash}`
- Contract + EOA links:
  - `https://etherscan.io/tx/{tx_hash}`

---

## Design changes

### 1. Address classification layer

Add a new service/module that decides address type:

- `src/tg_safe_monitor/address_classifier.py`

Suggested interface:

```python
class AddressType(str, Enum):
    SAFE = "safe"
    CONTRACT = "contract"
    EOA = "eoa"

@dataclass(slots=True)
class ClassifiedAddress:
    address: str
    address_type: AddressType
```

Methods:

- `classify(address: str) -> ClassifiedAddress`

Implementation logic:

1. validate + checksum the address
2. `eth_getCode(address, "latest")`
3. if result is `0x` => EOA
4. else probe Safe API, ideally via `/safes/{address}/`
5. if Safe exists => Safe
6. otherwise => contract

### 2. EOA persistence

Add new storage for EOAs.

Suggested tables:

- `monitored_eoas`
  - `eoa_address TEXT PRIMARY KEY`
  - `added_by_user_id BIGINT`
  - `added_by_username TEXT`
  - `label TEXT`
  - `start_block BIGINT NOT NULL`
  - `added_at TIMESTAMPTZ NOT NULL`
- `seen_eoa_transactions`
  - `eoa_address TEXT NOT NULL`
  - `tx_hash TEXT NOT NULL`
  - `block_number BIGINT NOT NULL`
  - `first_seen_at TIMESTAMPTZ NOT NULL`
  - `PRIMARY KEY (eoa_address, tx_hash)`

Repository additions:

- `add_eoa(...)`
- `remove_eoa(...)`
- `list_eoas()`
- `is_eoa_monitored(...)`
- `record_seen_eoa_transaction(...)`
- `has_seen_eoa_transaction(...)`

### 3. Unified block-scanning strategy

Refactor Ethereum block scanning so blocks are scanned once and checked for both:

- contract targets by `tx.to`
- EOA targets by `tx.from`

This likely means introducing a unified Ethereum activity scanner service instead of separate contract-only logic.

Suggested module:

- `src/tg_safe_monitor/ethereum_activity_service.py`

Behavior per tx:

- if `tx.from` matches a monitored EOA => create EOA notification
- if `tx.to` matches a monitored contract => fetch receipt, require `status == 1`, then create contract notification
- if both match different monitored entities, allow both notifications if appropriate

### 4. Receipt lookup for contracts

Current block tx objects do not include success status. To skip reverted contract calls, add:

- `eth_getTransactionReceipt`

Important optimization:

- fetch receipts **only for candidate contract-target txs**, not for every tx in every block

### 5. Generic command UX

Replace the mental model from “user chooses monitor type” to “user gives address”.

New generic commands:

- `/add <address> [label...]`
- `/remove <address>`
- `/list`

Recommended behavior for `/add`:

1. classify address
2. route to the correct backend service
3. respond with a type-aware confirmation, e.g.
   - `Added Safe Treasury Safe (0x...)`
   - `Added contract Uniswap Router (0x...)`
   - `Added EOA Market Maker Hot Wallet (0x...)`

Old commands should remain supported as aliases to reduce breakage.

### 6. Link formatting

#### Safe

Use Safe App link when `safeTxHash` exists:

```text
https://app.safe.global/transactions/tx?safe=eth:{safe_address}&id=multisig_{safe_address}_{safe_tx_hash}
```

#### Contract / EOA

Use Etherscan:

```text
https://etherscan.io/tx/{tx_hash}
```

---

## Implementation tasks

### Task 1: Write failing tests for classification and generic commands

**Files:**
- create `tests/test_address_classifier.py`
- extend `tests/test_bot_logic.py`
- create `tests/test_eoa_service.py`

Test cases:

- EOA address is classified from empty code
- contract address is classified from non-empty code + non-Safe
- Safe address is classified from non-empty code + Safe API success
- `/add <address> label` routes to correct service
- `/list` shows Safe/contract/EOA entries with labels

### Task 2: Add EOA models and storage

**Files:**
- modify `src/tg_safe_monitor/models.py`
- modify `src/tg_safe_monitor/storage.py`

Add:

- `MonitoredEoa`
- `AddEoaResult`
- `EoaMonitorNotification`

### Task 3: Add address classifier

**Files:**
- create `src/tg_safe_monitor/address_classifier.py`
- create tests for classifier

Dependencies:

- `EthereumRpcClient` for `eth_getCode`
- Safe API client for Safe detection

### Task 4: Add EOA monitoring service

**Files:**
- create `src/tg_safe_monitor/eoa_service.py`
- create tests

Behavior:

- bootstrap from current block
- no historical backfill
- notify on newly mined txs where `from == monitored_eoa`

### Task 5: Refactor Ethereum scanner to support both EOA and contracts

**Files:**
- modify or replace `src/tg_safe_monitor/contract_service.py`
- modify `src/tg_safe_monitor/ethereum_rpc.py`
- modify `src/tg_safe_monitor/monitor.py`

Add RPC method:

- `get_transaction_receipt(tx_hash)`

Logic:

- scan blocks once
- match EOAs by `from`
- match contracts by `to`
- require receipt success for contract alerts

### Task 6: Add generic command surface

**Files:**
- modify `src/tg_safe_monitor/bot.py`
- modify `src/tg_safe_monitor/bot_logic.py`

Add:

- `/add`
- `/remove`
- `/list`

Keep aliases:

- `/addsafe`, `/addcontract`, etc.

### Task 7: Add link-rich messages

**Files:**
- modify `src/tg_safe_monitor/messages.py`
- add tests

Rules:

- Safe -> Safe App link
- Contract -> Etherscan link
- EOA -> Etherscan link
- labels visible everywhere

### Task 8: Wire app runtime

**Files:**
- modify `src/tg_safe_monitor/app.py`
- maybe add a unified activity loop rather than separate EOA/contract loops

Recommended runtime direction:

- Safe loop remains separate
- EOA + contract monitoring share one Ethereum activity loop

### Task 9: Full verification

**Checks:**

- `uv run pytest`
- add sample contract `0xbd216513d74c8cf14cf4747e6aaa6420ff64ee9e`
- test a known EOA sender example
- confirm contract reverts do not alert
- confirm links format correctly in generated messages

---

## Open questions

### Question 1: EOA reverted transactions

For EOAs, should we alert on:

- **all mined signed transactions**, even if they revert, or
- **only successful mined transactions**?

My recommendation: **all mined signed transactions** for EOAs, because the user intent is the interesting part there.

### Question 2: Generic commands naming

Do you want the primary non-technical commands to be:

- `/add`, `/remove`, `/list`

or something slightly more explicit like:

- `/addaddress`, `/removeaddress`, `/listaddresses`

My recommendation: **`/add`, `/remove`, `/list`**, while keeping the specialized commands as compatibility aliases.

---

## Suggested next execution order

1. classifier tests
2. EOA storage/models
3. generic command tests
4. unified EVM activity scanner
5. link formatting tests
6. docs update
7. deploy
