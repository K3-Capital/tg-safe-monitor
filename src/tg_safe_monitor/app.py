from __future__ import annotations

import asyncio
import logging

from .bot import build_application
from .bot_logic import CommandService
from .config import Settings
from .monitor import SafeMonitorLoop
from .safe_api import SafeApiClient
from .service import SafeMonitorService, SafeMonitorSettings
from .storage import PostgresMonitorRepository

logger = logging.getLogger(__name__)


def run() -> None:
    settings = Settings()
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )

    repository = PostgresMonitorRepository(settings.database_url)
    safe_client = SafeApiClient(settings.safe_api_base_url, token=settings.safe_api_token)
    monitor_service = SafeMonitorService(
        repository,
        safe_client,
        SafeMonitorSettings(poll_interval_seconds=settings.poll_interval_seconds),
    )
    command_service = CommandService(monitor_service)
    application = build_application(settings, command_service)

    async def post_init(app) -> None:
        async def send_message(text: str) -> None:
            await app.bot.send_message(chat_id=settings.telegram_chat_id, text=text)

        monitor_loop = SafeMonitorLoop(
            monitor_service,
            send_message=send_message,
            poll_interval_seconds=settings.poll_interval_seconds,
        )
        task = asyncio.create_task(monitor_loop.run(), name="safe-monitor-loop")
        app.bot_data["monitor_loop"] = monitor_loop
        app.bot_data["monitor_task"] = task
        logger.info("Started monitor loop for chat %s", settings.telegram_chat_id)

    async def post_shutdown(app) -> None:
        monitor_loop = app.bot_data.get("monitor_loop")
        monitor_task = app.bot_data.get("monitor_task")
        if monitor_loop is not None:
            monitor_loop.stop()
        if monitor_task is not None:
            monitor_task.cancel()
            try:
                await monitor_task
            except asyncio.CancelledError:
                pass
        await safe_client.aclose()
        logger.info("Shutdown complete")

    application.post_init = post_init
    application.post_shutdown = post_shutdown
    application.run_polling(allowed_updates=["message"])
