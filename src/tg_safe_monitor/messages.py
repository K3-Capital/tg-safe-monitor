from __future__ import annotations

from .models import MonitorNotification, SafeTransaction


def format_bootstrap_message(safe_address: str, existing_count: int) -> str:
    tx_word = "transaction" if existing_count == 1 else "transactions"
    return (
        f"Added safe {safe_address}.\n"
        f"Found {existing_count} existing {tx_word}; these were recorded as already known and will not trigger alerts.\n"
        "I will only post newly discovered transactions from now on."
    )


def format_new_transaction_message(notification: MonitorNotification) -> str:
    tx = notification.transaction
    status = "executed" if tx.executed else "pending"
    lines = [
        "New Safe transaction detected.",
        f"Safe: {notification.safe_address}",
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
