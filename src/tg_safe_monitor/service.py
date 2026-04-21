from __future__ import annotations

from dataclasses import dataclass

from eth_utils import is_address, to_checksum_address

from .models import AddSafeResult, MonitorNotification
from .storage import MonitorRepository


class SafeAlreadyMonitoredError(ValueError):
    pass


@dataclass(slots=True)
class SafeMonitorSettings:
    poll_interval_seconds: int = 60


class SafeMonitorService:
    def __init__(self, repository: MonitorRepository, safe_client, settings: SafeMonitorSettings) -> None:
        self.repository = repository
        self.safe_client = safe_client
        self.settings = settings

    async def add_safe(
        self,
        safe_address: str,
        *,
        added_by_user_id: int | None,
        added_by_username: str | None,
        label: str | None = None,
    ) -> AddSafeResult:
        normalized = self.normalize_safe_address(safe_address)
        if self.repository.is_safe_monitored(normalized):
            raise SafeAlreadyMonitoredError(f"Safe {normalized} is already being monitored")
        transactions = await self.safe_client.list_transactions(normalized)
        self.repository.add_safe(
            normalized,
            added_by_user_id=added_by_user_id,
            added_by_username=added_by_username,
            bootstrap_transaction_count=len(transactions),
            label=label,
        )
        for transaction in transactions:
            self.repository.record_seen_transaction(normalized, transaction.tx_uid)
        return AddSafeResult(
            safe_address=normalized,
            bootstrap_transaction_count=len(transactions),
            label=label,
        )

    def remove_safe(self, safe_address: str) -> bool:
        return self.repository.remove_safe(self.normalize_safe_address(safe_address))

    def list_safe_addresses(self) -> list[str]:
        return self.repository.list_safe_addresses()

    def list_safes(self):
        return self.repository.list_safes()

    def is_safe_monitored(self, safe_address: str) -> bool:
        return self.repository.is_safe_monitored(self.normalize_safe_address(safe_address))

    async def poll_once(self) -> list[MonitorNotification]:
        notifications: list[MonitorNotification] = []
        for monitored_safe in self.repository.list_safes():
            transactions = await self.safe_client.list_transactions(monitored_safe.safe_address)
            unseen = [
                transaction
                for transaction in transactions
                if not self.repository.has_seen_transaction(monitored_safe.safe_address, transaction.tx_uid)
            ]
            for transaction in reversed(unseen):
                self.repository.record_seen_transaction(monitored_safe.safe_address, transaction.tx_uid)
                notifications.append(
                    MonitorNotification(
                        safe_address=monitored_safe.safe_address,
                        transaction=transaction,
                        label=monitored_safe.label,
                    )
                )
        return notifications

    @staticmethod
    def normalize_safe_address(safe_address: str) -> str:
        if not is_address(safe_address):
            raise ValueError(f"Invalid safe address: {safe_address}")
        return to_checksum_address(safe_address)
