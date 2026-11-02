"""Admin-confirmed text broadcasts; users can opt out without losing bot access."""

import asyncio
import logging
import secrets
import time

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.error import Forbidden, NetworkError, RetryAfter, TelegramError
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)


def is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    return bool(update.effective_user and update.effective_user.id in context.bot_data["settings"].trade_admin_ids)


async def remember_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user, chat = update.effective_user, update.effective_chat
    if user is None or chat is None or chat.type != "private" or user.is_bot or chat.id != user.id:
        return
    store = context.bot_data["contacts"]
    store.remember_user(user.id)
    text = (update.effective_message.text or "") if update.effective_message else ""
    if text.split(maxsplit=1) and text.split(maxsplit=1)[0].split("@")[0] == "/start":
        store.subscribe_user(user.id, True)


async def stop_broadcasts(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user:
        context.bot_data["contacts"].subscribe_user(update.effective_user.id, False)
        await context.bot.send_message(update.effective_user.id, "🔕 پیام‌های همگانی غیرفعال شد. خدمات ربات همچنان در دسترس است. برای فعال‌سازی دوباره /subscribe را بفرستید.")


async def subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user:
        context.bot_data["contacts"].subscribe_user(update.effective_user.id, True)
        await context.bot.send_message(update.effective_user.id, "🔔 دریافت اطلاعیه‌های اهوراماین فعال شد. برای لغو، /stop را بفرستید.")


async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(update, context):
        return
    message = update.effective_message
    if message is None:
        return
    parts = (message.text or "").split(maxsplit=1)
    body = parts[1] if len(parts) == 2 else (message.reply_to_message.text if message.reply_to_message else "")
    if not body or len(body.encode("utf-16-le")) // 2 > 4000:
        await context.bot.send_message(update.effective_user.id, "یک متن حداکثر ۴۰۰۰ کاراکتری با دستور /broadcast ارسال کنید، یا روی پیام متنی ریپلای کنید و /broadcast بفرستید.")
        return
    body = body.strip() + "\n\n🔕 لغو اطلاعیه‌ها: /stop"
    store = context.bot_data["contacts"]
    draft_id = secrets.token_hex(12)
    store.draft_broadcast(draft_id, update.effective_user.id, body, time.time())
    # A preview is sent only to the requesting admin, never to the audience.
    await context.bot.send_message(update.effective_user.id, body)
    await context.bot.send_message(update.effective_user.id,
        f"👁 پیش‌نمایش پیام بالا\nمخاطبان فعلی: {store.broadcast_audience()} نفر\nارسال فقط پس از تأیید شما شروع می‌شود. پیش‌نویس ۱۰ دقیقه اعتبار دارد.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ ارسال همگانی", callback_data=f"broadcast:send:{draft_id}")],
            [InlineKeyboardButton("❌ لغو", callback_data=f"broadcast:cancel:{draft_id}")],
        ]))


async def broadcast_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query is None:
        return
    await query.answer()
    if not is_admin(update, context) or update.effective_chat is None or update.effective_chat.type != "private":
        return
    parts = str(query.data).split(":")
    if len(parts) != 3 or parts[1] not in {"send", "cancel"}:
        return
    store = context.bot_data["contacts"]
    draft_id, admin_id = parts[2], update.effective_user.id
    if parts[1] == "cancel":
        cancelled = store.cancel_broadcast(draft_id, admin_id)
        await context.bot.send_message(admin_id, "پیش‌نویس لغو شد؛ پیام ارسال نشد." if cancelled else "این پیش‌نویس قابل لغو نیست؛ وضعیت را با /broadcaststatus ببینید.")
        return
    task = context.bot_data.get("broadcast_task")
    if (task and not task.done()) or not store.confirm_broadcast(draft_id, admin_id, time.time()):
        await context.bot.send_message(admin_id, "ارسال شروع نشد؛ پیش‌نویس منقضی/استفاده شده یا ارسال دیگری در حال اجراست.")
        return
    info = store.broadcast_info(draft_id, admin_id)
    context.bot_data["broadcast_active_id"] = draft_id
    context.bot_data["broadcast_task"] = asyncio.create_task(send_broadcast(context.application, info))
    context.bot_data["broadcast_task"].add_done_callback(report_task_failure)
    await context.bot.send_message(admin_id, "📣 ارسال آغاز شد. وضعیت: /broadcaststatus")


async def send_broadcast(application, info: dict) -> None:
    store = application.bot_data["contacts"]
    completed = False
    try:
        while True:
            user_id = store.next_broadcast_recipient(info["id"])
            if user_id is None:
                completed = True
                break
            if not store.is_subscribed(user_id):
                store.record_delivery(info["id"], user_id, "skipped")
                continue
            outcome = "failed"
            for attempt in range(3):
                try:
                    if not store.is_subscribed(user_id):
                        outcome = "skipped"
                        break
                    await application.bot.send_message(user_id, info["body"])
                    outcome = "sent"
                    break
                except RetryAfter as error:
                    seconds = error.retry_after.total_seconds() if hasattr(error.retry_after, "total_seconds") else error.retry_after
                    await asyncio.sleep(float(seconds) + 1)
                except Forbidden:
                    store.subscribe_user(user_id, False)
                    break
                except NetworkError:
                    outcome = "uncertain"  # Delivery may have succeeded; never blindly resend.
                    break
                except TelegramError:
                    break
            store.record_delivery(info["id"], user_id, outcome)
            await asyncio.sleep(0.1)
    except asyncio.CancelledError:
        raise
    except Exception as error:
        logger.error("Broadcast stopped (%s)", type(error).__name__)
    finally:
        store.finish_broadcast(info["id"], "completed" if completed else "interrupted")
    if completed:
        counts = store.delivery_counts(info["id"])
        try:
            await application.bot.send_message(info["admin_id"],
                f"📣 ارسال پایان یافت\nموفق: {counts.get('sent', 0)}\nناموفق: {counts.get('failed', 0)}\nنامشخص: {counts.get('uncertain', 0)}\nلغوشده توسط کاربر: {counts.get('skipped', 0)}")
        except TelegramError:
            pass


async def broadcast_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(update, context):
        return
    store = context.bot_data["contacts"]
    draft_id = store.latest_broadcast(update.effective_user.id)
    if draft_id is None:
        await context.bot.send_message(update.effective_user.id, "هنوز ارسالی ثبت نشده است.")
        return
    info = store.broadcast_info(draft_id, update.effective_user.id)
    counts = store.delivery_counts(draft_id)
    await context.bot.send_message(update.effective_user.id,
        f"وضعیت: {info['state']}\nموفق: {counts.get('sent', 0)}\nناموفق: {counts.get('failed', 0)}\nنامشخص: {counts.get('uncertain', 0)}\nدر انتظار: {counts.get('pending', 0)}")


async def shutdown_broadcasts(application) -> None:
    task = application.bot_data.get("broadcast_task")
    if task and not task.done():
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


async def cancel_broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(update, context):
        return
    draft_id = context.bot_data.get("broadcast_active_id")
    info = context.bot_data["contacts"].broadcast_info(draft_id, update.effective_user.id) if draft_id else None
    task = context.bot_data.get("broadcast_task")
    if info is None or task is None or task.done():
        await context.bot.send_message(update.effective_user.id, "ارسال فعالی برای توقف ندارید.")
        return
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    context.bot_data["contacts"].finish_broadcast(draft_id, "interrupted")
    await context.bot.send_message(update.effective_user.id, "⏹ ارسال متوقف شد. پیام‌هایی که قبلاً ارسال شده‌اند قابل بازگردانی نیستند.")


def report_task_failure(task) -> None:
    if not task.cancelled():
        error = task.exception()
        if error is not None:
            logger.error("Broadcast task failed (%s)", type(error).__name__)
