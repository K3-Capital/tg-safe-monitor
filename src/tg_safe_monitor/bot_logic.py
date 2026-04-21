from __future__ import annotations

from .messages import format_bootstrap_message


class CommandService:
    def __init__(self, monitor_service) -> None:
        self.monitor_service = monitor_service

    async def handle_add_safe(self, safe_address: str, *, user_id: int, username: str | None) -> str:
        result = await self.monitor_service.add_safe(
            safe_address,
            added_by_user_id=user_id,
            added_by_username=username,
        )
        return format_bootstrap_message(result.safe_address, result.bootstrap_transaction_count)

    def handle_remove_safe(self, safe_address: str) -> str:
        removed = self.monitor_service.remove_safe(safe_address)
        if removed:
            return f"Removed safe {safe_address} from monitoring."
        return f"Safe {safe_address} was not being monitored."

    def handle_list_safes(self) -> str:
        safes = self.monitor_service.list_safe_addresses()
        if not safes:
            return "No safes are currently being monitored."
        lines = ["Currently monitored safes:"]
        lines.extend(f"- {safe_address}" for safe_address in safes)
        return "\n".join(lines)
