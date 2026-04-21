import pytest

from tg_safe_monitor.bot_logic import CommandService


class MonitoredAddress:
    def __init__(self, address: str, label: str | None = None) -> None:
        self.safe_address = address
        self.contract_address = address
        self.eoa_address = address
        self.label = label


class FakeClassifier:
    def __init__(self, classifications: dict[str, str]) -> None:
        self.classifications = {key.lower(): value for key, value in classifications.items()}

    async def classify(self, address: str):
        address_type = self.classifications[address.lower()]
        return type("Classified", (), {"address": address, "address_type": address_type})()


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


class FakeEoaMonitorService:
    def __init__(self) -> None:
        self.add_calls = []
        self.remove_calls = []
        self.eoas = [MonitoredAddress("0x1111111111111111111111111111111111111111", "Trader Wallet")]

    async def add_eoa(self, eoa_address: str, *, added_by_user_id: int, added_by_username: str | None, label: str | None = None):
        self.add_calls.append((eoa_address, added_by_user_id, added_by_username, label))
        return type(
            "Result",
            (),
            {
                "eoa_address": "0x1111111111111111111111111111111111111111",
                "start_block": 33333333,
                "label": label,
            },
        )()

    def remove_eoa(self, eoa_address: str) -> bool:
        self.remove_calls.append(eoa_address)
        return eoa_address.lower() == self.eoas[0].eoa_address.lower()

    def list_eoas(self):
        return list(self.eoas)


def make_commands(classifications: dict[str, str]) -> tuple[CommandService, FakeSafeMonitorService, FakeContractMonitorService, FakeEoaMonitorService]:
    safe_service = FakeSafeMonitorService()
    contract_service = FakeContractMonitorService()
    eoa_service = FakeEoaMonitorService()
    commands = CommandService(
        safe_service=safe_service,
        contract_service=contract_service,
        eoa_service=eoa_service,
        address_classifier=FakeClassifier(classifications),
    )
    return commands, safe_service, contract_service, eoa_service


@pytest.mark.asyncio
async def test_add_command_routes_safe_based_on_classifier() -> None:
    commands, safe_service, contract_service, eoa_service = make_commands(
        {"0xb3696a817d01c8623e66d156b6798291fa10a46d": "safe"}
    )

    message = await commands.handle_add(
        "0xb3696a817D01C8623E66D156B6798291fa10a46d",
        user_id=55,
        username="val",
        label="Treasury Safe",
    )

    assert "Added safe" in message
    assert "Treasury Safe" in message
    assert safe_service.add_calls == [
        ("0xb3696a817D01C8623E66D156B6798291fa10a46d", 55, "val", "Treasury Safe")
    ]
    assert contract_service.add_calls == []
    assert eoa_service.add_calls == []


@pytest.mark.asyncio
async def test_add_command_routes_contract_based_on_classifier() -> None:
    commands, safe_service, contract_service, eoa_service = make_commands(
        {"0xbd216513d74c8cf14cf4747e6aaa6420ff64ee9e": "contract"}
    )

    message = await commands.handle_add(
        "0xbd216513d74c8cf14cf4747e6aaa6420ff64ee9e",
        user_id=55,
        username="val",
        label="High Volume Contract",
    )

    assert "Added contract" in message
    assert "High Volume Contract" in message
    assert safe_service.add_calls == []
    assert contract_service.add_calls == [
        ("0xbd216513d74c8cf14cf4747e6aaa6420ff64ee9e", 55, "val", "High Volume Contract")
    ]
    assert eoa_service.add_calls == []


@pytest.mark.asyncio
async def test_add_command_routes_eoa_based_on_classifier() -> None:
    commands, safe_service, contract_service, eoa_service = make_commands(
        {"0x1111111111111111111111111111111111111111": "eoa"}
    )

    message = await commands.handle_add(
        "0x1111111111111111111111111111111111111111",
        user_id=55,
        username="val",
        label="Trader Wallet",
    )

    assert "Added EOA" in message
    assert "Trader Wallet" in message
    assert safe_service.add_calls == []
    assert contract_service.add_calls == []
    assert eoa_service.add_calls == [
        ("0x1111111111111111111111111111111111111111", 55, "val", "Trader Wallet")
    ]


def test_remove_command_removes_existing_safe_without_classifier_help() -> None:
    commands, safe_service, contract_service, eoa_service = make_commands({})

    message = commands.handle_remove("0xB3696A817D01C8623E66D156B6798291fa10a46d")

    assert "Removed safe" in message
    assert safe_service.remove_calls == ["0xB3696A817D01C8623E66D156B6798291fa10a46d"]
    assert contract_service.remove_calls == []
    assert eoa_service.remove_calls == []


def test_list_command_aggregates_all_monitored_address_types() -> None:
    commands, _, _, _ = make_commands({})

    message = commands.handle_list()

    assert "Safe" in message
    assert "Contract" in message
    assert "EOA" in message
    assert "[Treasury Safe (0xB3696A817D01C8623E66D156B6798291fa10a46d)](https://etherscan.io/address/0xB3696A817D01C8623E66D156B6798291fa10a46d)" in message
    assert "[High Volume Contract (0xbd216513d74c8cf14cf4747e6aaa6420ff64ee9e)](https://etherscan.io/address/0xbd216513d74c8cf14cf4747e6aaa6420ff64ee9e)" in message
    assert "[Trader Wallet (0x1111111111111111111111111111111111111111)](https://etherscan.io/address/0x1111111111111111111111111111111111111111)" in message
