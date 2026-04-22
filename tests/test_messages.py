from tg_safe_monitor.messages import (
    format_new_contract_call_message,
    format_new_eoa_transaction_message,
    format_new_transaction_message,
)
from tg_safe_monitor.models import (
    ContractCallTransaction,
    ContractMonitorNotification,
    EoaMonitorNotification,
    EoaTransaction,
    MonitorNotification,
    SafeTransaction,
)


def test_safe_message_includes_safe_app_link() -> None:
    notification = MonitorNotification(
        safe_address="0x693e444389F3cB953F8baD0EaC2CE2885df68De7",
        label="Ops Safe",
        transaction=SafeTransaction(
            safe_address="0x693e444389F3cB953F8baD0EaC2CE2885df68De7",
            tx_uid="0xa499f3d780f980b1cecea9d4bad9a1228492de376119fe242399dc713e7f14d0",
            safe_tx_hash="0xa499f3d780f980b1cecea9d4bad9a1228492de376119fe242399dc713e7f14d0",
            nonce=1,
            to="0x1111111111111111111111111111111111111111",
            value="0",
            executed=False,
            transaction_hash=None,
            operation=0,
            submission_date=None,
            proposer=None,
            confirmations_submitted=0,
        ),
    )

    message = format_new_transaction_message(notification)

    assert (
        "Safe App: [open](https://app.safe.global/transactions/tx?safe=eth:"
        "0x693e444389F3cB953F8baD0EaC2CE2885df68De7"
        "&id=multisig_0x693e444389F3cB953F8baD0EaC2CE2885df68De7_"
        "0xa499f3d780f980b1cecea9d4bad9a1228492de376119fe242399dc713e7f14d0)"
        in message
    )


def test_contract_message_includes_etherscan_link() -> None:
    notification = ContractMonitorNotification(
        contract_address="0xbd216513d74c8cf14cf4747e6aaa6420ff64ee9e",
        label="High Volume Contract",
        transaction=ContractCallTransaction(
            tx_hash="0xabc",
            block_number=1,
            from_address="0x1111111111111111111111111111111111111111",
            to_address="0xbd216513d74c8cf14cf4747e6aaa6420ff64ee9e",
            value="0",
            input_data="0xa9059cbb00000000",
            selector="0xa9059cbb",
            success=True,
        ),
    )

    message = format_new_contract_call_message(notification)

    assert "Etherscan: [open](https://etherscan.io/tx/0xabc)" in message


def test_eoa_message_includes_etherscan_link() -> None:
    notification = EoaMonitorNotification(
        eoa_address="0x1111111111111111111111111111111111111111",
        label="Trader Wallet",
        transaction=EoaTransaction(
            tx_hash="0xdef",
            block_number=1,
            from_address="0x1111111111111111111111111111111111111111",
            to_address="0x2222222222222222222222222222222222222222",
            value="0",
            input_data="0x",
            success=False,
        ),
    )

    message = format_new_eoa_transaction_message(notification)

    assert "Etherscan: [open](https://etherscan.io/tx/0xdef)" in message
