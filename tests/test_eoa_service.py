from dataclasses import dataclass

import pytest

from tg_safe_monitor.eoa_service import EoaMonitorService
from tg_safe_monitor.storage import InMemoryMonitorRepository


@dataclass(slots=True)
class FakeRpcTransaction:
    tx_hash: str
    block_number: int
    from_address: str
    to_address: str | None
    value: str
    input_data: str
    success: bool | None = None


class FakeEthereumRpcClient:
    def __init__(self) -> None:
        self.current_block = 100
        self.blocks: dict[int, list[FakeRpcTransaction]] = {}

    async def get_block_number(self) -> int:
        return self.current_block

    async def get_block_with_transactions(self, block_number: int):
        return self.blocks.get(block_number, [])


@pytest.mark.asyncio
async def test_add_eoa_starts_from_current_block_without_backfill() -> None:
    repository = InMemoryMonitorRepository()
    rpc = FakeEthereumRpcClient()
    service = EoaMonitorService(repository, rpc_client=rpc, confirmation_blocks=0)

    result = await service.add_eoa(
        "0x1111111111111111111111111111111111111111",
        added_by_user_id=1,
        added_by_username="val",
        label="Trader Wallet",
    )

    assert result.eoa_address == "0x1111111111111111111111111111111111111111"
    assert result.label == "Trader Wallet"
    assert result.start_block == 100


@pytest.mark.asyncio
async def test_poll_once_alerts_for_new_transactions_signed_by_monitored_eoa() -> None:
    repository = InMemoryMonitorRepository()
    rpc = FakeEthereumRpcClient()
    service = EoaMonitorService(repository, rpc_client=rpc, confirmation_blocks=0)

    await service.add_eoa(
        "0x1111111111111111111111111111111111111111",
        added_by_user_id=1,
        added_by_username="val",
        label="Trader Wallet",
    )

    rpc.current_block = 101
    rpc.blocks[101] = [
        FakeRpcTransaction(
            tx_hash="0xaaa",
            block_number=101,
            from_address="0x1111111111111111111111111111111111111111",
            to_address="0x2222222222222222222222222222222222222222",
            value="1",
            input_data="0x",
            success=False,
        ),
        FakeRpcTransaction(
            tx_hash="0xbbb",
            block_number=101,
            from_address="0x3333333333333333333333333333333333333333",
            to_address="0x2222222222222222222222222222222222222222",
            value="1",
            input_data="0x",
        ),
    ]

    notifications = await service.poll_once()

    assert len(notifications) == 1
    assert notifications[0].label == "Trader Wallet"
    assert notifications[0].transaction.tx_hash == "0xaaa"
