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
    label: str | None = None


@dataclass(slots=True)
class AddSafeResult:
    safe_address: str
    bootstrap_transaction_count: int
    label: str | None = None


@dataclass(slots=True)
class MonitorNotification:
    safe_address: str
    transaction: SafeTransaction
    label: str | None = None


@dataclass(slots=True)
class ContractCallTransaction:
    tx_hash: str
    block_number: int
    from_address: str
    to_address: str | None
    value: str
    input_data: str
    selector: str | None
    success: bool | None = None


@dataclass(slots=True)
class MonitoredContract:
    contract_address: str
    added_by_user_id: int | None
    added_by_username: str | None
    start_block: int
    added_at: str
    label: str | None = None


@dataclass(slots=True)
class AddContractResult:
    contract_address: str
    start_block: int
    label: str | None = None


@dataclass(slots=True)
class ContractMonitorNotification:
    contract_address: str
    transaction: ContractCallTransaction
    label: str | None = None
