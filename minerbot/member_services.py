"""Private account details, persistent support tickets and report summaries."""
import time

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.error import TelegramError
from telegram.ext import ContextTypes

from .handlers import send_text
from .keyboards import main_keyboard, trade_section_keyboard

ACCOUNT_LABEL = "👤 حساب من"
TICKETS_LABEL = "🎫 تیکت‌های پشتیبانی"
STATUS = {"submitted": "ارسال‌شده", "unavailable": "بررسی ناموفق", "not_referred": "معرف تأیید نشد",
          "below_threshold": "واریز کمتر از حد لازم", "eligible": "واجد شرایط"}
TICKET_STATUS = {"open": "در انتظار پاسخ", "answered": "پاسخ داده شد", "closed": "بسته‌شده"}


def store(context):
    return context.bot_data["contacts"]


def cancel(context):
    for key in ("ticket_until", "trade_awaiting_uid", "phone_requested_until"):
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
    await send_text(context, uid, "\n\n".join(lines), main_keyboard())


async def performance_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    cancel(context)
    await show_dashboard(context, update.effective_user.id)


async def show_dashboard(context, user_id):
    from .performance import show_dashboard as show_live_dashboard
    await show_live_dashboard(context, user_id)


async def tickets_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    cancel(context)
    await show_tickets(context, update.effective_user.id)


async def show_tickets(context, user_id):
    rows = [[InlineKeyboardButton("✍️ تیکت جدید", callback_data="ticket:new")]]
    for ticket in store(context).tickets(user_id):
        rows.append([InlineKeyboardButton(f"#{ticket['id']} · {TICKET_STATUS[ticket['status']]}",
                                          callback_data=f"ticket:view:{ticket['id']}")])
    rows.append([InlineKeyboardButton("🏠 منوی اصلی", callback_data="home")])
    await send_text(context, user_id,
                    "🎫 تیکت‌های پشتیبانی\n\n۱۰ تیکت اخیر شما؛ برای مشاهدهٔ متن و پاسخ یک تیکت را انتخاب کنید."
                    "\nبرای ادامهٔ گفتگو پس از پاسخ، تیکت جدیدی با شمارهٔ تیکت قبلی ثبت کنید.", InlineKeyboardMarkup(rows))


async def new_ticket(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    cancel(context)
    context.user_data['ticket_until'] = time.time() + 600
    await send_text(context, update.effective_user.id,
                    "✍️ تیکت جدید\n\nمشکل خود را در یک پیام متنی تا ۲۰۰۰ کاراکتر بنویسید."
                    " رمز، کلید API یا اطلاعات حساس نفرستید. پیام برای پاسخ‌گویی ذخیره می‌شود."
                    "\nمهلت ارسال: ۱۰ دقیقه؛ لغو: /tickets", None)


async def ticket_input(update, context) -> bool:
    until = context.user_data.get('ticket_until')
    if until is None:
        return False
    if time.time() > until:
        cancel(context)
        await send_text(context, update.effective_user.id, "⌛ مهلت تمام شد؛ /tickets را بزنید.", None)
        return True
    try:
        ticket_id = store(context).create_ticket(update.effective_user.id, update.effective_message.text or '', time.time())
    except ValueError as error:
        text = ("حداکثر ۳ تیکت باز و هر دقیقه یک تیکت مجاز است." if str(error) == 'ticket_limit'
                else "پیام باید بین ۱ تا ۲۰۰۰ کاراکتر باشد.")
        await send_text(context, update.effective_user.id, text, None)
        return True
    cancel(context)
    await send_text(context, update.effective_user.id, f"✅ تیکت #{ticket_id} ثبت شد. پاسخ در همین ربات و /tickets قابل مشاهده است.", None)
    return True


async def ticket_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if not update.effective_chat or update.effective_chat.type != 'private':
        return
    action = query.data.split(':')
    cancel(context)
    if action == ['ticket', 'new']:
        await new_ticket(update, context)
        return
    if len(action) != 3 or not action[2].isdigit():
        return
    if action[1] == 'list':
        await show_tickets(context, query.from_user.id)
        return
    if len(action[2]) > 18:
        return
    uid, ticket_id = query.from_user.id, int(action[2])
    ticket = store(context).ticket(ticket_id, uid)
    if ticket is None:
        await send_text(context, uid, "تیکت پیدا نشد.", None)
        return
    if action[1] == 'close':
        store(context).close_ticket(ticket_id, uid)
        await show_tickets(context, uid)
    elif action[1] == 'view':
        # Split into separate messages to stay below Telegram's UTF-16 limit.
        await send_text(context, uid, f"🎫 تیکت #{ticket_id} · {TICKET_STATUS[ticket['status']]}\n\n{ticket['body']}", None)
        await send_text(context, uid, f"💬 پاسخ پشتیبانی\n\n{ticket['reply'] or 'هنوز پاسخی ثبت نشده است.'}",
                        InlineKeyboardMarkup([[InlineKeyboardButton("🔒 بستن تیکت", callback_data=f"ticket:close:{ticket_id}")],
                                              [InlineKeyboardButton("🎫 تیکت‌ها", callback_data='ticket:list:0')]]))
    elif action[1] == 'list':
        await show_tickets(context, uid)


def admin(update, context):
    return update.effective_user.id in context.bot_data['settings'].trade_admin_ids


async def ticket_queue(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not admin(update, context):
        return
    rows = store(context).tickets(None)
    await send_text(context, update.effective_user.id,
                    "🎫 صف پشتیبانی\n\n" + ('\n\n'.join(f"#{t['id']}\n{t['body'][:200]}" for t in rows) or 'تیکت بازی نیست.') +
                    "\n\nپاسخ: /replyticket شماره متن پاسخ", None)


async def reply_ticket(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not admin(update, context):
        return
    args = (update.effective_message.text or '').split(maxsplit=2)
    if len(args) != 3 or not args[1].isascii() or not args[1].isdigit() or len(args[1]) > 18 or len(args[2].encode('utf-16-le')) > 4000:
        await send_text(context, update.effective_user.id, "روش پاسخ: /replyticket شماره متن پاسخ (حداکثر ۲۰۰۰ کاراکتر)", None)
        return
    ticket_id = int(args[1])
    ticket = store(context).ticket(ticket_id, None)
    if not ticket or not store(context).reply_ticket(ticket_id, args[2], time.time()):
        await send_text(context, update.effective_user.id, "تیکت باز پیدا نشد؛ ممکن است قبلاً پاسخ داده شده باشد.", None)
        return
    delivered = True
    try:
        await send_text(context, ticket['user_id'], f"💬 پاسخ تیکت #{ticket_id}\n\n{args[2]}\n\nمشاهدهٔ تیکت‌ها: /tickets", None)
    except TelegramError:
        delivered = False
    await send_text(context, update.effective_user.id,
                    "✅ پاسخ ذخیره و ارسال شد." if delivered else "پاسخ ذخیره شد؛ ارسال پیام ممکن نشد. کاربر می‌تواند در /tickets آن را ببیند.", None)
