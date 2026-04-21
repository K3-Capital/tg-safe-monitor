import pytest

from tg_safe_monitor.bot_logic import CommandService


class MonitoredAddress:
    def __init__(self, address: str, label: str | None = None) -> None:
        self.safe_address = address
        self.contract_address = address
        self.label = label


class FakeSafeMonitorService:
    def __init__(self) -> None:
        self.add_calls = []
        self.remove_calls = []
        self.safes = [MonitoredAddress("0xB3696A817D01C8623E66D156B6798291fa10a46d", "Treasury Safe")]

    async def add_safe(self, safe_address: str, *, added_by_user_id: int, added_by_username: str | None, label: str | None = None):
        self.add_calls.append((safe_address, added_by_user_id, added_by_username, label))
        return type(
            "Result",
            (),
            {
                "safe_address": "0xB3696A817D01C8623E66D156B6798291fa10a46d",
                "bootstrap_transaction_count": 3,
                "label": label,
            },
        )()

    def remove_safe(self, safe_address: str) -> bool:
        self.remove_calls.append(safe_address)
        return safe_address.lower() == self.safes[0].safe_address.lower()

    def list_safes(self):
        return list(self.safes)


class FakeContractMonitorService:
    def __init__(self) -> None:
        self.add_calls = []
        self.remove_calls = []
        self.contracts = [MonitoredAddress("0xbd216513d74c8cf14cf4747e6aaa6420ff64ee9e", "High Volume Contract")]

    async def add_contract(self, contract_address: str, *, added_by_user_id: int, added_by_username: str | None, label: str | None = None):
        self.add_calls.append((contract_address, added_by_user_id, added_by_username, label))
        return type(
            "Result",
            (),
            {
                "contract_address": "0xbd216513d74c8cf14cf4747e6aaa6420ff64ee9e",
                "start_block": 22222222,
                "label": label,
            },
        )()

    def remove_contract(self, contract_address: str) -> bool:
        self.remove_calls.append(contract_address)
        return contract_address.lower() == self.contracts[0].contract_address.lower()

    def list_contracts(self):
        return list(self.contracts)


@pytest.mark.asyncio
async def test_add_safe_command_confirms_bootstrap_behavior() -> None:
    safe_service = FakeSafeMonitorService()
    commands = CommandService(safe_service=safe_service, contract_service=FakeContractMonitorService())

    message = await commands.handle_add_safe(
        "0xb3696a817D01C8623E66D156B6798291fa10a46d",
        user_id=55,
        username="val",
        label="Treasury Safe",
    )

    assert "Added safe" in message
    assert "Treasury Safe" in message
    assert "Found 3 existing transaction" in message
    assert "will not trigger alerts" in message
    assert safe_service.add_calls == [
        ("0xb3696a817D01C8623E66D156B6798291fa10a46d", 55, "val", "Treasury Safe")
    ]


def test_list_safes_command_lists_monitored_safes() -> None:
    service = FakeSafeMonitorService()
    commands = CommandService(safe_service=service, contract_service=FakeContractMonitorService())

    message = commands.handle_list_safes()

    assert "Currently monitored safes" in message
    assert "Treasury Safe" in message
    assert service.safes[0].safe_address in message


def test_remove_safe_command_confirms_success() -> None:
    service = FakeSafeMonitorService()
    commands = CommandService(safe_service=service, contract_service=FakeContractMonitorService())

    message = commands.handle_remove_safe("0xB3696A817D01C8623E66D156B6798291fa10a46d")

    assert "Removed safe" in message


@pytest.mark.asyncio
async def test_add_contract_command_accepts_optional_label() -> None:
    contract_service = FakeContractMonitorService()
    commands = CommandService(safe_service=FakeSafeMonitorService(), contract_service=contract_service)

    message = await commands.handle_add_contract(
        "0xbd216513d74c8cf14cf4747e6aaa6420ff64ee9e",
        user_id=55,
        username="val",
        label="High Volume Contract",
    )

    assert "Added contract" in message
    assert "High Volume Contract" in message
    assert "current block" in message.lower()
    assert contract_service.add_calls == [
        ("0xbd216513d74c8cf14cf4747e6aaa6420ff64ee9e", 55, "val", "High Volume Contract")
    ]


def test_list_contracts_command_lists_monitored_contracts() -> None:
    contract_service = FakeContractMonitorService()
    commands = CommandService(safe_service=FakeSafeMonitorService(), contract_service=contract_service)

    message = commands.handle_list_contracts()

    assert "Currently monitored contracts" in message
    assert "High Volume Contract" in message
    assert contract_service.contracts[0].contract_address in message
