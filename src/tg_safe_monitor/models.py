from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class SafeTransaction:
    safe_address: str
    tx_uid: str
    safe_tx_hash: str | None
    nonce: int | None
    to: str | None
    value: str | None
    executed: bool
    transaction_hash: str | None
    operation: int | None
    submission_date: str | None
    proposer: str | None
    confirmations_submitted: int | None


@dataclass(slots=True)
class MonitoredSafe:
    safe_address: str
    added_by_user_id: int | None
    added_by_username: str | None
    bootstrap_transaction_count: int
    added_at: str


@dataclass(slots=True)
class AddSafeResult:
    safe_address: str
    bootstrap_transaction_count: int


@dataclass(slots=True)
class MonitorNotification:
    safe_address: str
    transaction: SafeTransaction
