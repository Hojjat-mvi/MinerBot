"""Application construction and polling entry point."""

import logging

from telegram.error import TelegramError
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, MessageHandler, filters

from .config import Settings, load_settings
from .xt import XTVerifier
from .contacts import ContactStore
from .logging_setup import configure_logging
from .handlers import callback_handler, handle_error, handle_messages, handle_contact, delete_phone, menu, start


def build_application(settings: Settings) -> Application:
    application = Application.builder().token(settings.token).build()
    application.bot_data["contacts"] = ContactStore(settings.data_dir / "contacts.sqlite3")
    application.bot_data["settings"] = settings
    application.bot_data["xt_verifier"] = XTVerifier(settings)
    application.add_handler(CommandHandler("start", start, filters=filters.ChatType.PRIVATE))
    application.add_handler(CommandHandler("menu", menu, filters=filters.ChatType.PRIVATE))
    application.add_handler(CommandHandler("deletephone", delete_phone, filters=filters.ChatType.PRIVATE))
    application.add_handler(MessageHandler(filters.ChatType.PRIVATE & filters.CONTACT, handle_contact))
    application.add_handler(CallbackQueryHandler(callback_handler))
    application.add_handler(MessageHandler(filters.ChatType.PRIVATE & filters.TEXT & ~filters.COMMAND, handle_messages))
    application.add_error_handler(handle_error)
    return application


def main() -> None:
    try:
        settings = load_settings()
    except ValueError as error:
        raise SystemExit(str(error)) from None
    configure_logging(settings)
    try:
        build_application(settings).run_polling()
    except TelegramError as error:
        logging.getLogger(__name__).error("Telegram startup stopped (%s)", type(error).__name__)
        raise SystemExit("Check Telegram credentials, network access, and that only one instance is polling.") from None
