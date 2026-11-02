"""Useful private-chat commands and Telegram's native Menu button."""

import logging

from telegram import BotCommand, BotCommandScopeAllPrivateChats, MenuButtonCommands, Update
from telegram.error import TelegramError
from telegram.ext import Application, ContextTypes

from .content import MENU_TEXTS, TRADE_SUPPORT_TEXT
from .handlers import (
    LIGHTNING_TEXT, require_membership, send_text, show_trade_room,
)
from .keyboards import contact_keyboard, lightning_menu_keyboard, main_keyboard, trade_section_keyboard

logger = logging.getLogger(__name__)

USER_COMMANDS = (
    BotCommand("menu", "🏠 منوی اصلی"),
    BotCommand("trade", "📈 اتاق ترید و دریافت اشتراک"),
    BotCommand("nodes", "⚡ دستگاه‌های لایتنینگ"),
    BotCommand("support", "💬 پشتیبانی"),
    BotCommand("help", "❓ راهنمای استفاده"),
    BotCommand("deletephone", "🗑 حذف شماره و UID پرونده"),
)


def cancel_input(context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data.pop("trade_awaiting_uid", None)
    context.user_data.pop("phone_requested_until", None)


async def configure_command_menu(application: Application) -> None:
    # Menu styling and localization are controlled by Telegram, not bot CSS.
    try:
        for language in ("", "fa"):
            await application.bot.set_my_commands(
                USER_COMMANDS, scope=BotCommandScopeAllPrivateChats(), language_code=language,
            )
        await application.bot.set_chat_menu_button(menu_button=MenuButtonCommands())
    except TelegramError as error:
        # Temporary menu-setup failure must not stop polling.
        logger.warning("Could not configure Telegram command menu (%s)", type(error).__name__)


async def trade_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    cancel_input(context)
    if update.effective_user and await require_membership(context, update.effective_user.id):
        await show_trade_room(context, update.effective_user.id)


async def nodes_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    cancel_input(context)
    if update.effective_user and await require_membership(context, update.effective_user.id):
        context.user_data["active_section"] = "lightning"
        await send_text(context, update.effective_user.id, LIGHTNING_TEXT, lightning_menu_keyboard())


async def support_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    cancel_input(context)
    if update.effective_user is None:
        return
    if context.user_data.get("active_section") == "lightning":
        await send_text(context, update.effective_user.id, MENU_TEXTS["ارتباط با ما 📧"], contact_keyboard())
    else:
        await send_text(context, update.effective_user.id, TRADE_SUPPORT_TEXT, trade_section_keyboard())


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    cancel_input(context)
    if update.effective_user is None:
        return
    await send_text(context, update.effective_user.id,
                    "❓ راهنمای ربات اهوراماین\n\n"
                    "🏠 /menu — بازگشت به منوی اصلی\n"
                    "📈 /trade — اتاق ترید و دریافت اشتراک\n"
                    "⚡ /nodes — معرفی دستگاه‌های لایتنینگ\n"
                    "💬 /support — ارتباط با پشتیبانی\n"
                    "🗑 /deletephone — حذف شماره و UID پرونده؛ سابقهٔ تخصیص اشتراک برای جلوگیری از استفادهٔ تکراری حفظ می‌شود.\n\n"
                    "برای ورود به ترید، ابتدا شمارهٔ خود را با دکمهٔ اشتراک‌گذاری ارسال کنید. "
                    "برای اشتراک رایگان، UID را در بخش بررسی حساب وارد کنید. رمز عبور یا کلید API نفرستید.\n\n"
                    f"شناسهٔ تلگرام شما: {update.effective_user.id}",
                    main_keyboard())


async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    cancel_input(context)
    if update.effective_user:
        await send_text(context, update.effective_user.id,
                        "❓ دستور شناخته نشد\n\nاز دکمهٔ Menu کنار کادر پیام استفاده کنید یا /help را بفرستید.", main_keyboard())
