"""Explicit, admin-authorized discovery of private channel IDs."""

import hashlib
import secrets
import time

from telegram import Update
from telegram.constants import ChatMemberStatus
from telegram.error import TelegramError
from telegram.ext import ContextTypes

PREFIX = "AHURA-CHANNEL-ID:"


async def channel_id_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    settings = context.bot_data["settings"]
    if user is None or user.id not in settings.trade_admin_ids:
        return
    now = time.time()
    pending = context.bot_data.setdefault("channel_setup_requests", {})
    # Replace this admin's previous requests and discard expired setup codes.
    for digest, request in list(pending.items()):
        if request["expires"] <= now or request["admin_id"] == user.id:
            pending.pop(digest, None)
    code = PREFIX + secrets.token_urlsafe(24)
    digest = hashlib.sha256(code.encode()).hexdigest()
    pending[digest] = {"admin_id": user.id, "expires": now + 600}
    await context.bot.send_message(
        chat_id=user.id,
        text=("🔎 دریافت شناسهٔ کانال خصوصی\n\nکد زیر را دقیقاً به‌صورت یک پیام جدید در کانال VIP منتشر کنید. "
              "ربات و شما باید ادمین همان کانال باشید. کد ۱۰ دقیقه اعتبار دارد؛ "
              "شناسه فقط در همین گفت‌وگوی خصوصی ارسال می‌شود.\n\n" + code),
    )


async def discover_channel_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.channel_post
    if message is None or message.chat.type != "channel":
        return
    text = (message.text or "").strip()
    if not text.startswith(PREFIX):
        return
    pending = context.bot_data.get("channel_setup_requests", {})
    digest = hashlib.sha256(text.encode()).hexdigest()
    request = pending.get(digest)
    if request is None:
        return
    if request["expires"] <= time.time():
        pending.pop(digest, None)
        return
    admin_id = request["admin_id"]
    if admin_id not in context.bot_data["settings"].trade_admin_ids:
        pending.pop(digest, None)
        return
    try:
        member = await context.bot.get_chat_member(message.chat.id, admin_id)
    except TelegramError:
        return
    if member.status not in {ChatMemberStatus.OWNER, ChatMemberStatus.ADMINISTRATOR}:
        return
    pending.pop(digest, None)
    await context.bot.send_message(
        chat_id=admin_id,
        text=(f"✅ شناسهٔ عددی کانال:\n{message.chat.id}\n\n"
              f"در فایل .env سرور قرار دهید:\nXT_REWARD_CHANNEL_ID={message.chat.id}\n\n"
              "سپس کانتینر ربات را بازسازی کنید. تنظیمات کانال خودکار تغییر نکرده‌اند."),
    )
    try:
        await message.delete()
    except TelegramError:
        pass
