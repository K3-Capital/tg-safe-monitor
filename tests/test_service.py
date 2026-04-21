from dataclasses import dataclass

import pytest

from tg_safe_monitor.models import SafeTransaction
from tg_safe_monitor.service import SafeMonitorService, SafeMonitorSettings
from tg_safe_monitor.storage import InMemoryMonitorRepository


@dataclass
class FakeSafeClient:
    responses: dict[str, list[list[SafeTransaction]]]

    def __post_init__(self) -> None:
        self.responses = {safe.lower(): sequences for safe, sequences in self.responses.items()}
        self.calls: dict[str, int] = {safe: 0 for safe in self.responses}

    async def list_transactions(self, safe_address: str) -> list[SafeTransaction]:
        key = safe_address.lower()
        index = self.calls.get(key, 0)
        sequence = self.responses[key]
        if index >= len(sequence):
            index = len(sequence) - 1
        self.calls[key] = self.calls.get(key, 0) + 1
        return sequence[index]


@pytest.fixture()
def repo() -> InMemoryMonitorRepository:
    return InMemoryMonitorRepository()


def tx(uid: str, *, executed: bool = False, nonce: int = 1) -> SafeTransaction:
    return SafeTransaction(
        safe_address="0xb3696a817d01c8623e66d156b6798291fa10a46d",
        tx_uid=uid,
        safe_tx_hash=uid,
        nonce=nonce,
        to="0x1111111111111111111111111111111111111111",
        value="0",
        executed=executed,
        transaction_hash=None,
        operation=0,
        submission_date="2026-04-21T18:00:00Z",
        proposer=None,
        confirmations_submitted=0,
    )


@pytest.mark.asyncio
async def test_add_safe_bootstraps_existing_transactions_without_alerting(repo: InMemoryMonitorRepository) -> None:
    client = FakeSafeClient(
        {
            "0xB3696A817D01C8623E66D156B6798291fa10a46d": [
                [tx("safe-tx-1"), tx("safe-tx-2", executed=True, nonce=2)]
            ]
        }
    )
    service = SafeMonitorService(
        repo,
        client,
        SafeMonitorSettings(poll_interval_seconds=60),
    )

    result = await service.add_safe(
        "0xb3696a817D01C8623E66D156B6798291fa10a46d",
        added_by_user_id=42,
        added_by_username="val",
    )

    normalized_safe = service.normalize_safe_address("0xb3696a817D01C8623E66D156B6798291fa10a46d")

    assert result.safe_address == normalized_safe
    assert result.bootstrap_transaction_count == 2
    assert repo.list_safes()[0].safe_address == normalized_safe
    assert repo.has_seen_transaction(normalized_safe, "safe-tx-1")
    assert repo.has_seen_transaction(normalized_safe, "safe-tx-2")


@pytest.mark.asyncio
async def test_poll_once_notifies_only_new_transactions(repo: InMemoryMonitorRepository) -> None:
    safe = "0xB3696A817D01C8623E66D156B6798291fa10a46d"
    client = FakeSafeClient(
        {
            safe: [
                [tx("safe-tx-1")],
                [tx("safe-tx-2", nonce=2), tx("safe-tx-1")],
            ]
        }
    )
    service = SafeMonitorService(repo, client, SafeMonitorSettings(poll_interval_seconds=60))
    await service.add_safe(safe, added_by_user_id=42, added_by_username="val")

    notifications = await service.poll_once()

    normalized_safe = service.normalize_safe_address(safe)

    assert len(notifications) == 1
    assert notifications[0].transaction.tx_uid == "safe-tx-2"
    assert repo.has_seen_transaction(normalized_safe, "safe-tx-2")


@pytest.mark.asyncio
async def test_remove_safe_stops_future_monitoring(repo: InMemoryMonitorRepository) -> None:
    safe = "0xB3696A817D01C8623E66D156B6798291fa10a46d"
    client = FakeSafeClient(
        {
            safe: [
                [tx("safe-tx-1")],
                [tx("safe-tx-2", nonce=2), tx("safe-tx-1")],
            ]
        }
    )
    service = SafeMonitorService(repo, client, SafeMonitorSettings(poll_interval_seconds=60))
    await service.add_safe(safe, added_by_user_id=42, added_by_username="val")

    removed = service.remove_safe(safe)
    notifications = await service.poll_once()

    assert removed is True
    assert notifications == []
    assert repo.list_safes() == []
