from __future__ import annotations

import logging
from typing import Final

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import Application, ApplicationBuilder, CommandHandler, ContextTypes

from .bot_logic import CommandService
from .config import Settings

logger = logging.getLogger(__name__)

HELP_TEXT: Final[str] = (
    "Commands:\n"
    "/add <address> [label] - start monitoring an address\n"
    "/remove <address> - stop monitoring an address\n"
    "/list - list monitored addresses\n"
    "/status - show monitor status\n"
    "/help - show this help text"
)


def build_application(settings: Settings, command_service: CommandService) -> Application:
    application = ApplicationBuilder().token(settings.telegram_bot_token).build()

    async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not await _ensure_allowed(update, settings):
            return
        await _reply(update, HELP_TEXT)

    async def add_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not await _ensure_allowed(update, settings):
            return
        if not context.args:
            await _reply(update, "Usage: /add <address> [label]")
            return
        label = " ".join(context.args[1:]).strip() or None
        try:
            message = await command_service.handle_add(
                context.args[0],
                user_id=update.effective_user.id if update.effective_user else 0,
                username=update.effective_user.username if update.effective_user else None,
                label=label,
            )
        except ValueError as exc:
            message = str(exc)
        await _reply(update, message)

    async def remove_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not await _ensure_allowed(update, settings):
            return
        if not context.args:
            await _reply(update, "Usage: /remove <address>")
            return
        await _reply(update, command_service.handle_remove(context.args[0]))

    async def list_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not await _ensure_allowed(update, settings):
            return
        await _reply(update, command_service.handle_list())

    async def status_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not await _ensure_allowed(update, settings):
            return
        total = len(command_service.safe_service.list_safes()) + len(command_service.contract_service.list_contracts()) + len(command_service.eoa_service.list_eoas())
        await _reply(update, f"tg-safe-monitor is running. Monitoring {total} address(es).")

    application.add_handler(CommandHandler("start", help_handler))
    application.add_handler(CommandHandler("help", help_handler))
    application.add_handler(CommandHandler("add", add_handler))
    application.add_handler(CommandHandler("remove", remove_handler))
    application.add_handler(CommandHandler("list", list_handler))
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
        await _reply(update, "You are not allowed to manage monitored addresses in this chat.")
        return False
    return True


async def _reply(update: Update, text: str) -> None:
    if update.effective_message is not None:
        await update.effective_message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
