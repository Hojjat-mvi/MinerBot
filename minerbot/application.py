"""Application construction and polling entry point."""

import logging

from telegram import Update
from telegram.error import TelegramError
from telegram.ext import Application, CallbackQueryHandler, ChatJoinRequestHandler, CommandHandler, MessageHandler, TypeHandler, filters

from .config import Settings, load_settings
from .xt import XTVerifier
from .broadcasts import (
    remember_user, stop_broadcasts, subscribe, broadcast_command,
    broadcast_callback, broadcast_status, shutdown_broadcasts, cancel_broadcast_command,
)
from .channel_setup import channel_id_command, discover_channel_id
from .commands import configure_command_menu, trade_command, nodes_command, support_command, help_command, unknown_command
from .member_services import account_command, tickets_command, performance_command, new_ticket, ticket_callback, ticket_queue, reply_ticket
from .performance import performance_callback, performance_admin
from .rewards import reward_join_request
from .contacts import ContactStore
from .logging_setup import configure_logging
from .handlers import callback_handler, handle_error, handle_messages, handle_contact, delete_phone, menu, start


async def initialize_runtime(application: Application) -> None:
    application.bot_data["contacts"].interrupt_broadcasts()
    await configure_command_menu(application)


def build_application(settings: Settings) -> Application:
    application = Application.builder().token(settings.token).post_init(initialize_runtime).post_stop(shutdown_broadcasts).build()
    application.bot_data["contacts"] = ContactStore(settings.data_dir / "contacts.sqlite3")
    application.bot_data["settings"] = settings
    application.bot_data["xt_verifier"] = XTVerifier(settings)
    application.add_handler(TypeHandler(Update, remember_user), group=-1)
    for name, handler in (("account", account_command), ("tickets", tickets_command),
                          ("performance", performance_command), ("newticket", new_ticket),
                          ("ticketqueue", ticket_queue), ("replyticket", reply_ticket)):
        application.add_handler(CommandHandler(name, handler, filters=filters.ChatType.PRIVATE))
    application.add_handler(CallbackQueryHandler(ticket_callback, pattern=r"^ticket:"))
    application.add_handler(CallbackQueryHandler(performance_callback, pattern=r"^perf:"))
    application.add_handler(CommandHandler(["perfsetup", "addtrade", "voidtrade", "perftrades"], performance_admin, filters=filters.ChatType.PRIVATE))
    application.add_handler(CommandHandler("stop", stop_broadcasts, filters=filters.ChatType.PRIVATE))
    application.add_handler(CommandHandler("subscribe", subscribe, filters=filters.ChatType.PRIVATE))
    application.add_handler(CommandHandler("broadcast", broadcast_command, filters=filters.ChatType.PRIVATE))
    application.add_handler(CommandHandler("broadcaststatus", broadcast_status, filters=filters.ChatType.PRIVATE))
    application.add_handler(CommandHandler("cancelbroadcast", cancel_broadcast_command, filters=filters.ChatType.PRIVATE))
    application.add_handler(CallbackQueryHandler(broadcast_callback, pattern=r"^broadcast:"))
    application.add_handler(CommandHandler("start", start, filters=filters.ChatType.PRIVATE))
    application.add_handler(CommandHandler("menu", menu, filters=filters.ChatType.PRIVATE))
    application.add_handler(CommandHandler("trade", trade_command, filters=filters.ChatType.PRIVATE))
    application.add_handler(CommandHandler("nodes", nodes_command, filters=filters.ChatType.PRIVATE))
    application.add_handler(CommandHandler("support", support_command, filters=filters.ChatType.PRIVATE))
    application.add_handler(CommandHandler("help", help_command, filters=filters.ChatType.PRIVATE))
    application.add_handler(CommandHandler("deletephone", delete_phone, filters=filters.ChatType.PRIVATE))
    application.add_handler(MessageHandler(filters.ChatType.PRIVATE & filters.CONTACT, handle_contact))
    application.add_handler(CommandHandler("channelid", channel_id_command, filters=filters.ChatType.PRIVATE))
    application.add_handler(MessageHandler(filters.UpdateType.CHANNEL_POST & filters.TEXT, discover_channel_id))
    application.add_handler(ChatJoinRequestHandler(reward_join_request))
    application.add_handler(CallbackQueryHandler(callback_handler))
    application.add_handler(MessageHandler(filters.ChatType.PRIVATE & filters.TEXT & ~filters.COMMAND, handle_messages))
    application.add_handler(MessageHandler(filters.ChatType.PRIVATE & filters.COMMAND, unknown_command))
    application.add_error_handler(handle_error)
    return application


def main() -> None:
    try:
        settings = load_settings()
    except ValueError as error:
        raise SystemExit(str(error)) from None
    configure_logging(settings)
    try:
        build_application(settings).run_polling(allowed_updates=["message", "callback_query", "chat_join_request", "channel_post"])
    except TelegramError as error:
        logging.getLogger(__name__).error("Telegram startup stopped (%s)", type(error).__name__)
        raise SystemExit("Check Telegram credentials, network access, and that only one instance is polling.") from None
