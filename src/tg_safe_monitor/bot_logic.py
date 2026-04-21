from __future__ import annotations

from .messages import (
    format_address_link,
    format_bootstrap_message,
    format_contract_bootstrap_message,
    format_eoa_bootstrap_message,
)
from .models import AddressType


class CommandService:
    def __init__(self, safe_service, contract_service, eoa_service, address_classifier) -> None:
        self.safe_service = safe_service
        self.contract_service = contract_service
        self.eoa_service = eoa_service
        self.address_classifier = address_classifier

    async def handle_add(self, address: str, *, user_id: int, username: str | None, label: str | None = None) -> str:
        classified = await self.address_classifier.classify(address)
        address_type = AddressType(classified.address_type)
        if address_type is AddressType.SAFE:
            result = await self.safe_service.add_safe(address, added_by_user_id=user_id, added_by_username=username, label=label)
            return format_bootstrap_message(result.safe_address, result.bootstrap_transaction_count, result.label)
        if address_type is AddressType.CONTRACT:
            result = await self.contract_service.add_contract(address, added_by_user_id=user_id, added_by_username=username, label=label)
            return format_contract_bootstrap_message(result.contract_address, result.start_block, result.label)
        result = await self.eoa_service.add_eoa(address, added_by_user_id=user_id, added_by_username=username, label=label)
        return format_eoa_bootstrap_message(result.eoa_address, result.start_block, result.label)

    def handle_remove(self, address: str) -> str:
        if self.safe_service.remove_safe(address):
            return f"Removed safe {address} from monitoring."
        if self.contract_service.remove_contract(address):
            return f"Removed contract {address} from monitoring."
        if self.eoa_service.remove_eoa(address):
            return f"Removed EOA {address} from monitoring."
        return f"Address {address} was not being monitored."

    def handle_list(self) -> str:
        safes = self.safe_service.list_safes()
        contracts = self.contract_service.list_contracts()
        eoas = self.eoa_service.list_eoas()
        if not safes and not contracts and not eoas:
            return "No addresses are currently being monitored."
        lines = ["Currently monitored addresses:"]
        lines.extend(f"- Safe: {format_address_link(item.safe_address, item.label)}" for item in safes)
        lines.extend(f"- Contract: {format_address_link(item.contract_address, item.label)}" for item in contracts)
        lines.extend(f"- EOA: {format_address_link(item.eoa_address, item.label)}" for item in eoas)
        return "\n".join(lines)
