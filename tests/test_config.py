import pytest

from tg_safe_monitor.config import Settings


def test_settings_reads_database_url_from_env_alias() -> None:
    settings = Settings(
        TELEGRAM_BOT_TOKEN="token",
        TELEGRAM_CHAT_ID=-1001234567890,
        DATABASE_URL="postgresql://user:pass@db.example.com:5432/tg_safe_monitor",
    )

    assert settings.database_url == "postgresql://user:pass@db.example.com:5432/tg_safe_monitor"


def test_settings_requires_database_url() -> None:
    with pytest.raises(Exception):
        Settings(
            TELEGRAM_BOT_TOKEN="token",
            TELEGRAM_CHAT_ID=-1001234567890,
        )