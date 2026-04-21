import pytest

from tg_safe_monitor.bot_logic import CommandService
from tg_safe_monitor.models import SafeTransaction
from tg_safe_monitor.service import SafeMonitorSettings


class FakeMonitorService:
    def __init__(self) -> None:
        self.add_calls = []
        self.remove_calls = []
        self.safe_addresses = ["0xB3696A817D01C8623E66D156B6798291fa10a46d"]

    async def add_safe(self, safe_address: str, *, added_by_user_id: int, added_by_username: str | None):
        self.add_calls.append((safe_address, added_by_user_id, added_by_username))

        class Result:
            safe_address = "0xB3696A817D01C8623E66D156B6798291fa10a46d"
            bootstrap_transaction_count = 3

        return Result()

    def remove_safe(self, safe_address: str) -> bool:
        self.remove_calls.append(safe_address)
        return safe_address.lower() == self.safe_addresses[0].lower()

    def list_safe_addresses(self) -> list[str]:
        return list(self.safe_addresses)


@pytest.mark.asyncio
async def test_add_safe_command_confirms_bootstrap_behavior() -> None:
    service = FakeMonitorService()
    commands = CommandService(service)

    message = await commands.handle_add_safe(
        "0xb3696a817D01C8623E66D156B6798291fa10a46d",
        user_id=55,
        username="val",
    )

    assert "Added safe" in message
    assert "Found 3 existing transaction" in message
    assert "will not trigger alerts" in message
    assert service.add_calls == [
        ("0xb3696a817D01C8623E66D156B6798291fa10a46d", 55, "val")
    ]


def test_list_safes_command_lists_monitored_safes() -> None:
    service = FakeMonitorService()
    commands = CommandService(service)

    message = commands.handle_list_safes()

    assert "Currently monitored safes" in message
    assert service.safe_addresses[0] in message


def test_remove_safe_command_confirms_success() -> None:
    service = FakeMonitorService()
    commands = CommandService(service)

    message = commands.handle_remove_safe("0xB3696A817D01C8623E66D156B6798291fa10a46d")

    assert "Removed safe" in message
