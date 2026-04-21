from __future__ import annotations

import logging
from typing import Final

from telegram import Update
from telegram.ext import Application, ApplicationBuilder, CommandHandler, ContextTypes

from .bot_logic import CommandService
from .config import Settings
from .service import SafeAlreadyMonitoredError

logger = logging.getLogger(__name__)

HELP_TEXT: Final[str] = (
    "Commands:\n"
    "/addsafe <safe_address> - start monitoring a Safe\n"
    "/remsafe <safe_address> - stop monitoring a Safe\n"
    "/listsafes - list monitored Safes\n"
    "/status - show monitor status\n"
    "/help - show this help text"
)


def build_application(settings: Settings, command_service: CommandService) -> Application:
    application = ApplicationBuilder().token(settings.telegram_bot_token).build()

    async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not await _ensure_allowed(update, settings):
            return
        await _reply(update, HELP_TEXT)

    async def add_safe_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not await _ensure_allowed(update, settings):
            return
        if not context.args:
            await _reply(update, "Usage: /addsafe <safe_address>")
            return
        try:
            message = await command_service.handle_add_safe(
                context.args[0],
                user_id=update.effective_user.id if update.effective_user else 0,
                username=update.effective_user.username if update.effective_user else None,
            )
        except SafeAlreadyMonitoredError as exc:
            message = str(exc)
        except ValueError as exc:
            message = str(exc)
        await _reply(update, message)

    async def remove_safe_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not await _ensure_allowed(update, settings):
            return
        if not context.args:
            await _reply(update, "Usage: /remsafe <safe_address>")
            return
        await _reply(update, command_service.handle_remove_safe(context.args[0]))

    async def list_safes_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not await _ensure_allowed(update, settings):
            return
        await _reply(update, command_service.handle_list_safes())

    async def status_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not await _ensure_allowed(update, settings):
            return
        count = len(command_service.monitor_service.list_safe_addresses())
        await _reply(update, f"tg-safe-monitor is running. Monitoring {count} safe(s).")

    application.add_handler(CommandHandler("start", help_handler))
    application.add_handler(CommandHandler("help", help_handler))
    application.add_handler(CommandHandler("addsafe", add_safe_handler))
    application.add_handler(CommandHandler("remsafe", remove_safe_handler))
    application.add_handler(CommandHandler("listsafes", list_safes_handler))
    application.add_handler(CommandHandler("status", status_handler))
    return application


async def _ensure_allowed(update: Update, settings: Settings) -> bool:
    chat = update.effective_chat
    user = update.effective_user
    if chat is None or user is None:
        return False
    if chat.id != settings.telegram_chat_id:
        logger.info("Ignoring command from unexpected chat %s", chat.id)
        return False
    if settings.tg_admin_user_ids and user.id not in settings.tg_admin_user_ids:
        await _reply(update, "You are not allowed to manage monitored safes in this chat.")
        return False
    return True


async def _reply(update: Update, text: str) -> None:
    if update.effective_message is not None:
        await update.effective_message.reply_text(text)
