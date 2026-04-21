from __future__ import annotations

import asyncio

from eth_utils.address import is_address, to_checksum_address

from .models import AddEoaResult, EoaMonitorNotification, EoaTransaction
from .storage import MonitorRepository

LAST_SCANNED_BLOCK_KEY = "ethereum_mainnet_eoa_last_scanned_block"


class EoaAlreadyMonitoredError(ValueError):
    pass


class EoaMonitorService:
    def __init__(self, repository: MonitorRepository, rpc_client, confirmation_blocks: int = 0) -> None:
        self.repository = repository
        self.rpc_client = rpc_client
        self.confirmation_blocks = confirmation_blocks

    async def add_eoa(
        self,
        eoa_address: str,
        *,
        added_by_user_id: int | None,
        added_by_username: str | None,
        label: str | None = None,
    ) -> AddEoaResult:
        normalized = self.normalize_eoa_address(eoa_address)
        if await asyncio.to_thread(self.repository.is_eoa_monitored, normalized):
            raise EoaAlreadyMonitoredError(f"EOA {normalized} is already being monitored")
        current_block = await self.rpc_client.get_block_number()
        await asyncio.to_thread(
            self.repository.add_eoa,
            normalized,
            added_by_user_id=added_by_user_id,
            added_by_username=added_by_username,
            start_block=current_block,
            label=label,
        )
        if await asyncio.to_thread(self.repository.get_monitor_state, LAST_SCANNED_BLOCK_KEY) is None:
            await asyncio.to_thread(self.repository.set_monitor_state, LAST_SCANNED_BLOCK_KEY, str(current_block))
        return AddEoaResult(eoa_address=normalized, start_block=current_block, label=label)

    def remove_eoa(self, eoa_address: str) -> bool:
        return self.repository.remove_eoa(self.normalize_eoa_address(eoa_address))

    def list_eoas(self):
        return self.repository.list_eoas()

    async def poll_once(self) -> list[EoaMonitorNotification]:
        monitored_eoas = await asyncio.to_thread(self.repository.list_eoas)
        if not monitored_eoas:
            return []
        current_block = await self.rpc_client.get_block_number()
        head_block = max(current_block - self.confirmation_blocks, 0)
        state = await asyncio.to_thread(self.repository.get_monitor_state, LAST_SCANNED_BLOCK_KEY)
        if state is None:
            await asyncio.to_thread(self.repository.set_monitor_state, LAST_SCANNED_BLOCK_KEY, str(head_block))
            return []
        last_scanned_block = int(state)
        if head_block <= last_scanned_block:
            return []
        eoa_map = {eoa.eoa_address.lower(): eoa for eoa in monitored_eoas}
        notifications: list[EoaMonitorNotification] = []
        for block_number in range(last_scanned_block + 1, head_block + 1):
            transactions = await self.rpc_client.get_block_with_transactions(block_number)
            for transaction in transactions:
                normalized_tx = self._normalize_transaction(transaction)
                if not normalized_tx.from_address or not is_address(normalized_tx.from_address):
                    continue
                normalized_from = to_checksum_address(normalized_tx.from_address)
                monitored = eoa_map.get(normalized_from.lower())
                if monitored is None:
                    continue
                if await asyncio.to_thread(self.repository.has_seen_eoa_transaction, monitored.eoa_address, normalized_tx.tx_hash):
                    continue
                await asyncio.to_thread(self.repository.record_seen_eoa_transaction, monitored.eoa_address, normalized_tx.tx_hash, normalized_tx.block_number)
                notifications.append(EoaMonitorNotification(eoa_address=monitored.eoa_address, transaction=normalized_tx, label=monitored.label))
            await asyncio.to_thread(self.repository.set_monitor_state, LAST_SCANNED_BLOCK_KEY, str(block_number))
        return notifications

    @staticmethod
    def normalize_eoa_address(eoa_address: str) -> str:
        if not is_address(eoa_address):
            raise ValueError(f"Invalid EOA address: {eoa_address}")
        return to_checksum_address(eoa_address)

    @staticmethod
    def _normalize_transaction(transaction: object) -> EoaTransaction:
        if isinstance(transaction, EoaTransaction):
            return transaction
        return EoaTransaction(
            tx_hash=getattr(transaction, "tx_hash"),
            block_number=getattr(transaction, "block_number"),
            from_address=getattr(transaction, "from_address"),
            to_address=getattr(transaction, "to_address"),
            value=str(getattr(transaction, "value")),
            input_data=getattr(transaction, "input_data"),
            success=getattr(transaction, "success", None),
        )
