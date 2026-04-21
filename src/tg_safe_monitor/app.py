from __future__ import annotations

import asyncio
import logging

from .address_classifier import AddressClassifier
from .bot import build_application
from .bot_logic import CommandService
from .config import Settings
from .contract_service import ContractMonitorService
from .eoa_service import EoaMonitorService
from .ethereum_rpc import EthereumRpcClient
from .monitor import ContractMonitorLoop, EoaMonitorLoop, SafeMonitorLoop
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
    rpc_client = EthereumRpcClient(settings.ethereum_rpc_url)
    classifier = AddressClassifier(rpc_client=rpc_client, safe_client=safe_client)
    safe_service = SafeMonitorService(repository, safe_client, SafeMonitorSettings(poll_interval_seconds=settings.poll_interval_seconds))
    contract_service = ContractMonitorService(repository, rpc_client=rpc_client, confirmation_blocks=settings.ethereum_confirmation_blocks)
    eoa_service = EoaMonitorService(repository, rpc_client=rpc_client, confirmation_blocks=settings.ethereum_confirmation_blocks)
    command_service = CommandService(safe_service=safe_service, contract_service=contract_service, eoa_service=eoa_service, address_classifier=classifier)
    application = build_application(settings, command_service)

    async def post_init(app) -> None:
        async def send_message(text: str) -> None:
            await app.bot.send_message(chat_id=settings.telegram_chat_id, text=text)

        loops = [
            SafeMonitorLoop(safe_service, send_message=send_message, poll_interval_seconds=settings.poll_interval_seconds),
            ContractMonitorLoop(contract_service, send_message=send_message, poll_interval_seconds=settings.poll_interval_seconds),
            EoaMonitorLoop(eoa_service, send_message=send_message, poll_interval_seconds=settings.poll_interval_seconds),
        ]
        tasks = [asyncio.create_task(loop.run()) for loop in loops]
        app.bot_data["monitor_loops"] = loops
        app.bot_data["monitor_tasks"] = tasks
        logger.info("Started monitor loops for chat %s", settings.telegram_chat_id)

    async def post_shutdown(app) -> None:
        for loop in app.bot_data.get("monitor_loops", []):
            loop.stop()
        for task in app.bot_data.get("monitor_tasks", []):
            task.cancel()
        for task in app.bot_data.get("monitor_tasks", []):
            try:
                await task
            except asyncio.CancelledError:
                pass
        await safe_client.aclose()
        await rpc_client.aclose()
        logger.info("Shutdown complete")

    application.post_init = post_init
    application.post_shutdown = post_shutdown
    application.run_polling(allowed_updates=["message"])
