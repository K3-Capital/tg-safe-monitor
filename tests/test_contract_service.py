from dataclasses import dataclass

import pytest

from tg_safe_monitor.contract_service import ContractMonitorService
from tg_safe_monitor.storage import InMemoryMonitorRepository


@dataclass(slots=True)
class FakeRpcTransaction:
    tx_hash: str
    block_number: int
    from_address: str
    to_address: str | None
    value: str
    input_data: str


class FakeEthereumRpcClient:
    def __init__(self) -> None:
        self.current_block = 100
        self.blocks: dict[int, list[FakeRpcTransaction]] = {}
        self.receipts: dict[str, bool] = {}

    async def get_block_number(self) -> int:
        return self.current_block

    async def get_block_with_transactions(self, block_number: int):
        return self.blocks.get(block_number, [])

    async def get_transaction_receipt(self, tx_hash: str):
        success = self.receipts.get(tx_hash)
        if success is None:
            return None
        return {"status": "0x1" if success else "0x0"}


@pytest.mark.asyncio
async def test_add_contract_starts_from_current_block_without_backfill() -> None:
    repository = InMemoryMonitorRepository()
    rpc = FakeEthereumRpcClient()
    service = ContractMonitorService(repository, rpc_client=rpc, confirmation_blocks=0)

    result = await service.add_contract(
        "0xbd216513d74c8cf14cf4747e6aaa6420ff64ee9e",
        added_by_user_id=1,
        added_by_username="val",
        label="High Volume Contract",
    )

    assert result.contract_address == "0xbD216513d74C8cf14cf4747E6AaA6420FF64ee9e"
    assert result.label == "High Volume Contract"
    assert result.start_block == 100


@pytest.mark.asyncio
async def test_poll_once_alerts_only_for_successful_direct_calls_to_monitored_contract() -> None:
    repository = InMemoryMonitorRepository()
    rpc = FakeEthereumRpcClient()
    service = ContractMonitorService(repository, rpc_client=rpc, confirmation_blocks=0)

    await service.add_contract(
        "0xbd216513d74c8cf14cf4747e6aaa6420ff64ee9e",
        added_by_user_id=1,
        added_by_username="val",
        label="High Volume Contract",
    )

    rpc.current_block = 102
    rpc.blocks[101] = [
        FakeRpcTransaction(
            tx_hash="0xaaa",
            block_number=101,
            from_address="0x1111111111111111111111111111111111111111",
            to_address="0xbd216513d74c8cf14cf4747e6aaa6420ff64ee9e",
            value="1",
            input_data="0xa9059cbb00000000",
        ),
        FakeRpcTransaction(
            tx_hash="0xddd",
            block_number=101,
            from_address="0x1111111111111111111111111111111111111111",
            to_address="0xbd216513d74c8cf14cf4747e6aaa6420ff64ee9e",
            value="1",
            input_data="0xa9059cbb00000000",
        ),
        FakeRpcTransaction(
            tx_hash="0xbbb",
            block_number=101,
            from_address="0x1111111111111111111111111111111111111111",
            to_address="0x2222222222222222222222222222222222222222",
            value="1",
            input_data="0x",
        ),
    ]
    rpc.receipts["0xaaa"] = True
    rpc.receipts["0xddd"] = False
    rpc.blocks[102] = [
        FakeRpcTransaction(
            tx_hash="0xccc",
            block_number=102,
            from_address="0x1111111111111111111111111111111111111111",
            to_address=None,
            value="0",
            input_data="0xabcdef",
        )
    ]

    notifications = await service.poll_once()

    assert len(notifications) == 1
    assert notifications[0].label == "High Volume Contract"
    assert notifications[0].transaction.tx_hash == "0xaaa"
    assert notifications[0].transaction.selector == "0xa9059cbb"
