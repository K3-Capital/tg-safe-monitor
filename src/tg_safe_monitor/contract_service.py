from __future__ import annotations

import asyncio
from collections.abc import Mapping

from eth_utils import is_address, to_checksum_address

from .models import AddContractResult, ContractCallTransaction, ContractMonitorNotification
from .storage import MonitorRepository

LAST_SCANNED_BLOCK_KEY = "ethereum_mainnet_contract_last_scanned_block"


class ContractAlreadyMonitoredError(ValueError):
    pass


class ContractMonitorService:
    def __init__(self, repository: MonitorRepository, rpc_client, confirmation_blocks: int = 0) -> None:
        self.repository = repository
        self.rpc_client = rpc_client
        self.confirmation_blocks = confirmation_blocks

    async def add_contract(
        self,
        contract_address: str,
        *,
        added_by_user_id: int | None,
        added_by_username: str | None,
        label: str | None = None,
    ) -> AddContractResult:
        normalized = self.normalize_contract_address(contract_address)
        if await asyncio.to_thread(self.repository.is_contract_monitored, normalized):
            raise ContractAlreadyMonitoredError(f"Contract {normalized} is already being monitored")
        current_block = await self.rpc_client.get_block_number()
        await asyncio.to_thread(
            self.repository.add_contract,
            normalized,
            added_by_user_id=added_by_user_id,
            added_by_username=added_by_username,
            start_block=current_block,
            label=label,
        )
        if await asyncio.to_thread(self.repository.get_monitor_state, LAST_SCANNED_BLOCK_KEY) is None:
            await asyncio.to_thread(self.repository.set_monitor_state, LAST_SCANNED_BLOCK_KEY, str(current_block))
        return AddContractResult(contract_address=normalized, start_block=current_block, label=label)

    def remove_contract(self, contract_address: str) -> bool:
        return self.repository.remove_contract(self.normalize_contract_address(contract_address))

    def list_contracts(self):
        return self.repository.list_contracts()

    def list_contract_addresses(self) -> list[str]:
        return self.repository.list_contract_addresses()

    async def poll_once(self) -> list[ContractMonitorNotification]:
        monitored_contracts = await asyncio.to_thread(self.repository.list_contracts)
        if not monitored_contracts:
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

        contract_map = {contract.contract_address.lower(): contract for contract in monitored_contracts}
        notifications: list[ContractMonitorNotification] = []

        for block_number in range(last_scanned_block + 1, head_block + 1):
            transactions = await self.rpc_client.get_block_with_transactions(block_number)
            for transaction in transactions:
                normalized_transaction = self._normalize_transaction(transaction)
                if not normalized_transaction.to_address:
                    continue
                if not is_address(normalized_transaction.to_address):
                    continue
                normalized_to = to_checksum_address(normalized_transaction.to_address)
                contract = contract_map.get(normalized_to.lower())
                if contract is None:
                    continue
                if await asyncio.to_thread(self.repository.has_seen_contract_transaction, contract.contract_address, normalized_transaction.tx_hash):
                    continue
                receipt = await self.rpc_client.get_transaction_receipt(normalized_transaction.tx_hash)
                if not self._receipt_succeeded(receipt):
                    continue
                await asyncio.to_thread(
                    self.repository.record_seen_contract_transaction,
                    contract.contract_address,
                    normalized_transaction.tx_hash,
                    normalized_transaction.block_number,
                )
                notifications.append(
                    ContractMonitorNotification(
                        contract_address=contract.contract_address,
                        transaction=normalized_transaction,
                        label=contract.label,
                    )
                )
            await asyncio.to_thread(self.repository.set_monitor_state, LAST_SCANNED_BLOCK_KEY, str(block_number))

        return notifications

    @staticmethod
    def normalize_contract_address(contract_address: str) -> str:
        if not is_address(contract_address):
            raise ValueError(f"Invalid contract address: {contract_address}")
        return to_checksum_address(contract_address)

    @staticmethod
    def _receipt_succeeded(receipt: Mapping[str, object] | None) -> bool:
        if not receipt:
            return False
        status = receipt.get("status")
        if isinstance(status, str):
            return int(status, 16) == 1 if status.startswith("0x") else int(status) == 1
        if isinstance(status, int):
            return status == 1
        return False

    @staticmethod
    def _normalize_transaction(transaction: object) -> ContractCallTransaction:
        if isinstance(transaction, ContractCallTransaction):
            return transaction
        input_data = getattr(transaction, "input_data")
        selector = input_data[:10] if input_data and input_data.startswith("0x") and len(input_data) >= 10 else None
        return ContractCallTransaction(
            tx_hash=getattr(transaction, "tx_hash"),
            block_number=getattr(transaction, "block_number"),
            from_address=getattr(transaction, "from_address"),
            to_address=getattr(transaction, "to_address"),
            value=str(getattr(transaction, "value")),
            input_data=input_data,
            selector=selector,
            success=getattr(transaction, "success", None),
        )
