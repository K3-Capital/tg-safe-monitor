from __future__ import annotations

from .models import ContractMonitorNotification, MonitorNotification


def format_target(label: str | None, address: str) -> str:
    return f"{label} ({address})" if label else address


def format_bootstrap_message(safe_address: str, existing_count: int, label: str | None = None) -> str:
    tx_word = "transaction" if existing_count == 1 else "transactions"
    target = format_target(label, safe_address)
    return (
        f"Added safe {target}.\n"
        f"Found {existing_count} existing {tx_word}; these were recorded as already known and will not trigger alerts.\n"
        "I will only post newly discovered transactions from now on."
    )


def format_contract_bootstrap_message(contract_address: str, start_block: int, label: str | None = None) -> str:
    target = format_target(label, contract_address)
    return (
        f"Added contract {target}.\n"
        f"Monitoring will start from the current block {start_block}.\n"
        "Historical transactions will not trigger alerts."
    )


def format_new_transaction_message(notification: MonitorNotification) -> str:
    tx = notification.transaction
    status = "executed" if tx.executed else "pending"
    lines = [
        "New Safe transaction detected.",
        f"Safe: {format_target(notification.label, notification.safe_address)}",
        f"Status: {status}",
        f"Nonce: {tx.nonce if tx.nonce is not None else 'unknown'}",
        f"To: {tx.to or 'unknown'}",
        f"Value: {tx.value or '0'}",
    ]
    if tx.safe_tx_hash:
        lines.append(f"Safe tx hash: {tx.safe_tx_hash}")
    if tx.transaction_hash:
        lines.append(f"Execution tx hash: {tx.transaction_hash}")
    if tx.confirmations_submitted is not None:
        lines.append(f"Confirmations submitted: {tx.confirmations_submitted}")
    if tx.submission_date:
        lines.append(f"Submitted: {tx.submission_date}")
    return "\n".join(lines)


def format_new_contract_call_message(notification: ContractMonitorNotification) -> str:
    tx = notification.transaction
    lines = [
        "New direct contract call detected.",
        f"Contract: {format_target(notification.label, notification.contract_address)}",
        f"Tx hash: {tx.tx_hash}",
        f"Block: {tx.block_number}",
        f"From: {tx.from_address}",
        f"To: {tx.to_address or 'unknown'}",
        f"Value: {tx.value}",
    ]
    if tx.selector:
        lines.append(f"Selector: {tx.selector}")
    lines.append(f"Calldata length: {len(tx.input_data) - 2 if tx.input_data.startswith('0x') else len(tx.input_data)}")
    return "\n".join(lines)
