from __future__ import annotations

from .messages import format_bootstrap_message, format_contract_bootstrap_message, format_target


class CommandService:
    def __init__(self, safe_service, contract_service) -> None:
        self.safe_service = safe_service
        self.contract_service = contract_service

    async def handle_add_safe(
        self,
        safe_address: str,
        *,
        user_id: int,
        username: str | None,
        label: str | None = None,
    ) -> str:
        result = await self.safe_service.add_safe(
            safe_address,
            added_by_user_id=user_id,
            added_by_username=username,
            label=label,
        )
        return format_bootstrap_message(result.safe_address, result.bootstrap_transaction_count, result.label)

    def handle_remove_safe(self, safe_address: str) -> str:
        removed = self.safe_service.remove_safe(safe_address)
        if removed:
            return f"Removed safe {safe_address} from monitoring."
        return f"Safe {safe_address} was not being monitored."

    def handle_list_safes(self) -> str:
        safes = self.safe_service.list_safes()
        if not safes:
            return "No safes are currently being monitored."
        lines = ["Currently monitored safes:"]
        lines.extend(f"- {format_target(safe.label, safe.safe_address)}" for safe in safes)
        return "\n".join(lines)

    async def handle_add_contract(
        self,
        contract_address: str,
        *,
        user_id: int,
        username: str | None,
        label: str | None = None,
    ) -> str:
        result = await self.contract_service.add_contract(
            contract_address,
            added_by_user_id=user_id,
            added_by_username=username,
            label=label,
        )
        return format_contract_bootstrap_message(result.contract_address, result.start_block, result.label)

    def handle_remove_contract(self, contract_address: str) -> str:
        removed = self.contract_service.remove_contract(contract_address)
        if removed:
            return f"Removed contract {contract_address} from monitoring."
        return f"Contract {contract_address} was not being monitored."

    def handle_list_contracts(self) -> str:
        contracts = self.contract_service.list_contracts()
        if not contracts:
            return "No contracts are currently being monitored."
        lines = ["Currently monitored contracts:"]
        lines.extend(f"- {format_target(contract.label, contract.contract_address)}" for contract in contracts)
        return "\n".join(lines)
