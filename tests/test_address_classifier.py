import pytest

from tg_safe_monitor.address_classifier import AddressClassifier, AddressType


class FakeRpcClient:
    def __init__(self, code_by_address: dict[str, str]) -> None:
        self.code_by_address = {key.lower(): value for key, value in code_by_address.items()}

    async def get_code(self, address: str, block_tag: str = "latest") -> str:
        return self.code_by_address[address.lower()]


class FakeSafeClient:
    def __init__(self, safe_addresses: set[str]) -> None:
        self.safe_addresses = {address.lower() for address in safe_addresses}

    async def is_safe(self, address: str) -> bool:
        return address.lower() in self.safe_addresses


@pytest.mark.asyncio
async def test_classify_returns_eoa_when_code_is_empty() -> None:
    classifier = AddressClassifier(
        rpc_client=FakeRpcClient({"0x1111111111111111111111111111111111111111": "0x"}),
        safe_client=FakeSafeClient(set()),
    )

    result = await classifier.classify("0x1111111111111111111111111111111111111111")

    assert result.address_type == AddressType.EOA


@pytest.mark.asyncio
async def test_classify_returns_safe_when_code_exists_and_safe_probe_matches() -> None:
    address = "0xb3696a817D01C8623E66D156B6798291fa10a46d"
    classifier = AddressClassifier(
        rpc_client=FakeRpcClient({address: "0x6001600101"}),
        safe_client=FakeSafeClient({address}),
    )

    result = await classifier.classify(address)

    assert result.address_type == AddressType.SAFE


@pytest.mark.asyncio
async def test_classify_returns_contract_when_code_exists_and_not_safe() -> None:
    address = "0xbd216513d74c8cf14cf4747e6aaa6420ff64ee9e"
    classifier = AddressClassifier(
        rpc_client=FakeRpcClient({address: "0x6001600101"}),
        safe_client=FakeSafeClient(set()),
    )

    result = await classifier.classify(address)

    assert result.address_type == AddressType.CONTRACT
