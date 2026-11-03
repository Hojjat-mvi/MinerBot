"""Private account details and trade report shortcut."""
from telegram import Update
from telegram.ext import ContextTypes

from .handlers import send_text
from .keyboards import persistent_menu_keyboard, trade_menu_keyboard

ACCOUNT_LABEL = "👤 حساب من"
STATUS = {"submitted": "ارسال‌شده", "unavailable": "بررسی ناموفق", "not_referred": "معرف تأیید نشد",
          "below_threshold": "واریز کمتر از حد لازم", "eligible": "واجد شرایط"}


def store(context):
    return context.bot_data["contacts"]


def cancel(context):
    for key in ("trade_awaiting_uid", "phone_requested_until"):
        context.user_data.pop(key, None)


async def account_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    cancel(context)
    uid = update.effective_user.id
    record = store(context).account(uid)
    lines = ["👤 حساب من", f"شناسهٔ تلگرام: {uid}"]
    if record:
        phone = record["phone_number"]
        lines.extend([f"شمارهٔ ثبت‌شده: ***{phone[-4:]}", f"UID ثبت‌شده: {record['xt_uid'] or 'ثبت نشده'}",
                      f"آخرین نتیجهٔ ذخیره‌شده: {STATUS.get(record['xt_status'], 'بررسی نشده')}"])
        if record['xt_checked_at']:
            lines.append(f"زمان آخرین بررسی (UTC): {record['xt_checked_at']}")
    else:
        lines.append("شماره‌ای ثبت نشده است؛ برای ثبت شماره وارد اتاق ترید شوید.")
    lines.extend([f"اطلاعیه‌ها: {'فعال' if store(context).is_subscribed(uid) else 'غیرفعال'}",
                  "نتیجهٔ ذخیره‌شده تأیید لحظه‌ای حساب یا عضویت VIP نیست."])
    await send_text(context, uid, "\n\n".join(lines), trade_menu_keyboard() if context.user_data.get("active_section") == "trade" else persistent_menu_keyboard())


async def performance_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    cancel(context)
    from .handlers import require_membership, show_trade_results
    if await require_membership(context, update.effective_user.id):
        await show_trade_results(context, update.effective_user.id)
