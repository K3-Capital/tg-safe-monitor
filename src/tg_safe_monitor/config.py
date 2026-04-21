from __future__ import annotations

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    telegram_bot_token: str = Field(alias="TELEGRAM_BOT_TOKEN")
    telegram_chat_id: int = Field(alias="TELEGRAM_CHAT_ID")
    tg_admin_user_ids_raw: str = Field(default="", alias="TG_ADMIN_USER_IDS")
    safe_api_token: str = Field(default="", alias="SAFE_API_TOKEN")
    safe_api_base_url: str = Field(
        default="https://api.safe.global/tx-service/eth/api/v2",
        alias="SAFE_API_BASE_URL",
    )
    poll_interval_seconds: int = Field(default=60, alias="POLL_INTERVAL_SECONDS")
    database_url: str = Field(alias="DATABASE_URL")
    ethereum_rpc_url: str = Field(alias="ETHEREUM_RPC_URL")
    ethereum_confirmation_blocks: int = Field(default=0, alias="ETHEREUM_CONFIRMATION_BLOCKS")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    @property
    def tg_admin_user_ids(self) -> set[int]:
        if not self.tg_admin_user_ids_raw.strip():
            return set()
        return {int(part.strip()) for part in self.tg_admin_user_ids_raw.split(",") if part.strip()}

    @field_validator("safe_api_base_url", "ethereum_rpc_url")
    @classmethod
    def trim_url(cls, value: str) -> str:
        return value.rstrip("/")
