from typing import Any, cast

import pytest

from tg_safe_monitor.config import Settings


def make_settings(**kwargs: object) -> Settings:
    settings_factory = cast(Any, Settings)
    return settings_factory(_env_file=None, **kwargs)


def test_settings_reads_database_url_from_env_alias() -> None:
    settings = make_settings(
        TELEGRAM_BOT_TOKEN="***",
        TELEGRAM_CHAT_ID=-1001234567890,
        DATABASE_URL="postgresql://user:***@db.example.com:5432/tg_safe_monitor",
        ETHEREUM_RPC_URL="https://mainnet.gateway.tenderly.co/example",
        ETHEREUM_CONFIRMATION_BLOCKS=3,
    )

    assert settings.database_url == "postgresql://user:***@db.example.com:5432/tg_safe_monitor"
    assert settings.ethereum_rpc_url == "https://mainnet.gateway.tenderly.co/example"
    assert settings.ethereum_confirmation_blocks == 3


def test_settings_requires_database_url() -> None:
    with pytest.raises(Exception):
        make_settings(
            TELEGRAM_BOT_TOKEN="***",
            TELEGRAM_CHAT_ID=-1001234567890,
            DATABASE_URL=None,
            ETHEREUM_RPC_URL="https://mainnet.gateway.tenderly.co/example",
        )


def test_settings_requires_ethereum_rpc_url() -> None:
    with pytest.raises(Exception):
        make_settings(
            TELEGRAM_BOT_TOKEN="***",
            TELEGRAM_CHAT_ID=-1001234567890,
            DATABASE_URL="postgresql://user:***@db.example.com:5432/tg_safe_monitor",
            ETHEREUM_RPC_URL=None,
        )
