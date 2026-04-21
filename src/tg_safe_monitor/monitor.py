from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable

from .messages import format_new_transaction_message
from .service import SafeMonitorService

logger = logging.getLogger(__name__)


class SafeMonitorLoop:
    def __init__(
        self,
        service: SafeMonitorService,
        *,
        send_message: Callable[[str], Awaitable[None]],
        poll_interval_seconds: int,
    ) -> None:
        self.service = service
        self.send_message = send_message
        self.poll_interval_seconds = poll_interval_seconds
        self._stop_event = asyncio.Event()

    async def run(self) -> None:
        while not self._stop_event.is_set():
            try:
                notifications = await self.service.poll_once()
                for notification in notifications:
                    await self.send_message(format_new_transaction_message(notification))
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Monitor poll failed")

            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=self.poll_interval_seconds)
            except TimeoutError:
                continue

    def stop(self) -> None:
        self._stop_event.set()
