"""Async Telegram handlers for the Persian inline catalog."""

import logging
import time

from telegram import Update
from telegram.constants import ChatMemberStatus, ParseMode
from telegram.error import TelegramError
from telegram.ext import ContextTypes

from .config import ASSET_DIR, Settings
from .catalog import Product, catalog_summary, financial_details, product_card
from .content import CALLBACK_TEXTS, MENU_TEXTS, PRODUCTS, SETUP_VIDEOS, VIP_SUBSCRIPTION_TEXT, TRADE_PERFORMANCE_TEXT, TRADE_SUPPORT_TEXT
from .keyboards import (
    PRODUCT_IDS, channel_keyboard, contact_keyboard, main_keyboard,
    navigation_keyboard, product_keyboard, persistent_menu_keyboard,
    lightning_menu_keyboard, trade_keyboard, trade_menu_keyboard, reward_keyboard, LIGHTNING_LABEL, TRADE_LABEL,
    FREE_LABEL, TRAINING_LABEL, MONTHLY_LABEL, trade_section_keyboard, phone_keyboard, subscription_keyboard,
    SUBSCRIPTIONS_LABEL, RESULTS_LABEL, subscription_menu_keyboard,
)
from .presentation import rtl_html, telegram_text_parts
from .xt import XTUnavailable, normalize_uid
from .contacts import normalize_phone
from .rewards import issue_reward, RewardConflict

logger = logging.getLogger(__name__)
HOME_TEXT = "🏠 به اهوراماین خوش آمدید\n\nیکی از دو بخش زیر را انتخاب کنید:\n⚡ دستگاه‌های لایتنینگ: معرفی، قیمت و درآمد دستگاه‌ها\n📈 ترید با اهوراماین: بررسی شرایط حساب XT"
LIGHTNING_TEXT = "⚡ دستگاه‌های لایتنینگ\n\nمدل موردنظر را برای مشاهدهٔ مشخصات، قیمت و درآمد تقریبی انتخاب کنید."
UNKNOWN_TEXT = "🔎 گزینه پیدا نشد\n\nلطفاً یکی از دو بخش زیر را انتخاب کنید. گزینه‌های دستگاه‌ها و مشاوره در بخش لایتنینگ قرار دارند."


def settings_for(context: ContextTypes.DEFAULT_TYPE) -> Settings:
    return context.bot_data["settings"]


async def send_text(context: ContextTypes.DEFAULT_TYPE, user_id: int, text: str, keyboard, *, bold_lines: tuple[str, ...] = ()) -> None:
    parts = telegram_text_parts(text, bold_lines=bold_lines)
    for index, part in enumerate(parts):
        await context.bot.send_message(
            chat_id=user_id, text=part, parse_mode=ParseMode.HTML,
            reply_markup=keyboard if index == len(parts) - 1 else None,
        )


async def require_membership(context: ContextTypes.DEFAULT_TYPE, user_id: int) -> bool:
    settings = settings_for(context)
    accepted = {ChatMemberStatus.MEMBER, ChatMemberStatus.OWNER, ChatMemberStatus.ADMINISTRATOR}
    for channel, _ in settings.required_channels:
        member = await context.bot.get_chat_member(channel, user_id)
        if member.status not in accepted:
            await send_text(context, user_id,
                            "📢 عضویت شما در همهٔ کانال‌ها تأیید نشده است\n\nلطفاً در همهٔ کانال‌های زیر عضو شوید و دوباره دکمهٔ بررسی را بزنید.",
                            channel_keyboard(settings))
            return False
    return True


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data.pop("ticket_until", None)
    if update.effective_user is None:
        return
    user_id = update.effective_user.id
    context.user_data.pop("phone_requested_until", None)
    context.user_data.pop("trade_awaiting_uid", None)
    context.user_data["active_section"] = "home"
    # Keep the persistent menu available while inline buttons handle details.
    await send_text(context, user_id,
                    HOME_TEXT,
                    persistent_menu_keyboard())
    await send_text(context, user_id,
                    "📢 عضویت در کانال‌ها\n\nابتدا در همهٔ کانال‌های زیر عضو شوید؛ سپس دکمهٔ «عضو شدم؛ بررسی کن» را بزنید.",
                    channel_keyboard(settings_for(context)))


async def show_product(context: ContextTypes.DEFAULT_TYPE, user_id: int, product: Product) -> None:
    context.user_data["active_section"] = "lightning"
    if not product["image"]:
        await send_text(context, user_id, product_card(product), product_keyboard(product))
        return
    with (ASSET_DIR / product["image"]).open("rb") as photo:
        await context.bot.send_photo(
            chat_id=user_id, photo=photo, caption=rtl_html(product_card(product)),
            parse_mode=ParseMode.HTML, reply_markup=product_keyboard(product),
        )


async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query is None:
        return
    await query.answer()
    chat = getattr(update, "effective_chat", None)
    if chat is not None and chat.type != "private":
        return
    user_id = query.from_user.id
    data = query.data
    if not isinstance(data, str):
        return
    context.user_data.pop("ticket_until", None)
    if data in {"member:account", "member:tickets"}:
        from .member_services import account_command, tickets_command
        await (account_command if data == "member:account" else tickets_command)(update, context)
        return
    if not await require_membership(context, user_id):
        return
    context.user_data.pop("trade_awaiting_uid", None)
    context.user_data.pop("phone_requested_until", None)
    if data == "lightning":
        context.user_data["active_section"] = "lightning"
        await send_text(context, user_id, LIGHTNING_TEXT, lightning_menu_keyboard())
        return
    if data == "trade":
        await show_trade_room(context, user_id)
        return
    if data == "trade:subscriptions":
        await show_subscriptions(context, user_id)
        return
    if data == "trade:results":
        await show_trade_results(context, user_id)
        return
    if data in {"trade:free", "trade:check"}:
        await show_trade(context, user_id, begin_check=data == "trade:check")
        return
    if data in {"trade:training", "trade:monthly"}:
        await show_trade_section(context, user_id, training=data == "trade:training")
        return
    if data == "check_channel":
        await send_text(context, user_id, HOME_TEXT, persistent_menu_keyboard())
        return
    if data == "home":
        context.user_data["active_section"] = "home"
        context.user_data.pop("phone_requested_until", None)
        await send_text(context, user_id, HOME_TEXT, persistent_menu_keyboard())
        return
    if data == "prices":
        await send_text(context, user_id, catalog_summary(), navigation_keyboard())
        return
    if data == "contact" and context.user_data.get("active_section") == "trade":
        await send_text(context, user_id, TRADE_SUPPORT_TEXT, trade_section_keyboard())
        return
    if data in {"contact", "agency"}:
        key = "ارتباط با ما 📧" if data == "contact" else "اخذ نمایندگی 👨‍💼"
        await send_text(context, user_id, MENU_TEXTS[key], contact_keyboard())
        return
    if data.startswith("product:"):
        label = PRODUCT_IDS.get(data.removeprefix("product:"))
        if label:
            await show_product(context, user_id, PRODUCTS[label])
        else:
            await send_text(context, user_id, UNKNOWN_TEXT, main_keyboard())
        return

    product_id = None
    if data.startswith("info:"):
        parts = data.split(":", 2)
        if len(parts) != 3 or parts[1] not in PRODUCT_IDS:
            await send_text(context, user_id, UNKNOWN_TEXT, main_keyboard())
            return
        _, product_id, data = parts
        product = PRODUCTS[PRODUCT_IDS[product_id]]
        allowed_topics = {product["order_callback"], product["income_callback"], product["setup_callback"],
                          "power_internet", "warranty", "setup_maintenance", "tools"}
        if data not in allowed_topics:
            await send_text(context, user_id, UNKNOWN_TEXT, navigation_keyboard(product_id))
            return
    # Legacy callback IDs remain usable on messages sent by the old bot.
    navigation = navigation_keyboard(product_id)
    financial_product = next((product for product in PRODUCTS.values()
                              if data in {product["order_callback"], product["income_callback"]}), None)
    if financial_product:
        await send_text(context, user_id,
                        financial_details(financial_product, income=data == financial_product["income_callback"]),
                        navigation)
    elif data in CALLBACK_TEXTS:
        await send_text(context, user_id, CALLBACK_TEXTS[data], navigation)
    elif data in SETUP_VIDEOS:
        video = SETUP_VIDEOS[data]
        caption = rtl_html("🎬 آموزش راه‌اندازی دستگاه\n\nاگر هنگام راه‌اندازی به مشکلی برخوردید، با پشتیبانی تماس بگیرید.")
        if video.startswith("https://"):
            await context.bot.send_video(
                chat_id=user_id, video=video, caption=caption,
                parse_mode=ParseMode.HTML, reply_markup=navigation,
            )
        else:
            path = ASSET_DIR / video
            if not path.is_file():
                await send_text(context, user_id,
                                "🎬 ویدیو در دسترس نیست\n\nلطفاً برای دریافت آموزش با پشتیبانی تماس بگیرید.", navigation)
                return
            with path.open("rb") as file:
                await context.bot.send_video(
                    chat_id=user_id, video=file, caption=caption,
                    parse_mode=ParseMode.HTML, reply_markup=navigation,
                )
    else:
        await send_text(context, user_id, UNKNOWN_TEXT, main_keyboard())


async def handle_messages(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_message is None or update.effective_user is None:
        return
    user_id = update.effective_user.id
    text = (update.effective_message.text or "").strip()
    text = {"↩️ دریافت اشتراک": SUBSCRIPTIONS_LABEL,
            "↩️ بازگشت به اتاق ترید": TRADE_LABEL}.get(text, text)
    from .member_services import account_command, tickets_command, ticket_input
    if text in {"👤 حساب من", "🎫 تیکت‌های پشتیبانی"}:
        await (account_command if text == "👤 حساب من" else tickets_command)(update, context)
        return
    navigation = {LIGHTNING_LABEL, TRADE_LABEL, FREE_LABEL, TRAINING_LABEL, MONTHLY_LABEL,
                  SUBSCRIPTIONS_LABEL, RESULTS_LABEL, "🏠 منوی اصلی", "💵 قیمت و درآمد دستگاه‌ها", "💬 پشتیبانی"}
    if text in navigation or text in PRODUCTS or text in MENU_TEXTS:
        context.user_data.pop("ticket_until", None)
    elif await ticket_input(update, context):
        return
    # Accept buttons already sent during the user's earlier menu edits.
    text = {
        "🆓 اشتراک رایگان": FREE_LABEL,
        "🎁 اشتراک رایگان": FREE_LABEL,
        "💳 اشتراک ماهانه": MONTHLY_LABEL,
        "عضویت رایگان کانال VIP": FREE_LABEL,
        "اشتراک با پرداخت هزینه": MONTHLY_LABEL,
        "دریافت اشتراک": SUBSCRIPTIONS_LABEL,
        "برآیند معاملات": RESULTS_LABEL,
        "اشتراک رایگان": FREE_LABEL,
        "آموزش کار با صرافی XT": TRAINING_LABEL,
        "اشتراک ماهانه": MONTHLY_LABEL,
        "🧑🏻‍🏫 اموزش کار با صرافی": TRAINING_LABEL,
        "␚ اشتراک ماهانه": MONTHLY_LABEL,
        "📈 ترید با اهوراماین": TRADE_LABEL,
        "اتاق ترید اهورا": TRADE_LABEL,
    }.get(text, text)
    if not await require_membership(context, user_id):
        return
    # Keep existing reply-keyboard messages working during the UI transition.
    product = PRODUCTS.get(text)
    if text in {LIGHTNING_LABEL, TRADE_LABEL, FREE_LABEL, TRAINING_LABEL, MONTHLY_LABEL, SUBSCRIPTIONS_LABEL, RESULTS_LABEL, "🏠 منوی اصلی", "💬 پشتیبانی"} or product or text in MENU_TEXTS or text == "💵 قیمت و درآمد دستگاه‌ها":
        context.user_data.pop("trade_awaiting_uid", None)
        context.user_data.pop("phone_requested_until", None)
    elif context.user_data.get("phone_requested_until"):
        await require_trade_phone(context, user_id)
        return
    elif context.user_data.get("trade_awaiting_uid"):
        await check_trade_uid(context, user_id, text)
        return
    if text == LIGHTNING_LABEL:
        context.user_data["active_section"] = "lightning"
        await send_text(context, user_id, LIGHTNING_TEXT, lightning_menu_keyboard())
    elif text == TRADE_LABEL:
        await show_trade_room(context, user_id)
    elif text == "💬 پشتیبانی":
        if await require_trade_phone(context, user_id):
            await send_text(context, user_id, TRADE_SUPPORT_TEXT, subscription_keyboard())
    elif text == SUBSCRIPTIONS_LABEL:
        await show_subscriptions(context, user_id)
    elif text == RESULTS_LABEL:
        await show_trade_results(context, user_id)
    elif text == FREE_LABEL:
        await show_trade(context, user_id)
    elif text in {TRAINING_LABEL, MONTHLY_LABEL}:
        await show_trade_section(context, user_id, training=text == TRAINING_LABEL)
    elif text == "🏠 منوی اصلی":
        context.user_data["active_section"] = "home"
        context.user_data.pop("phone_requested_until", None)
        await send_text(context, user_id, HOME_TEXT, persistent_menu_keyboard())
    elif text == "💵 قیمت و درآمد دستگاه‌ها":
        await send_text(context, user_id, catalog_summary(), navigation_keyboard())
    elif product:
        await show_product(context, user_id, product)
    elif text == "ارتباط با ما 📧" and context.user_data.get("active_section") == "trade":
        await send_text(context, user_id, TRADE_SUPPORT_TEXT, trade_section_keyboard())
    elif text in MENU_TEXTS:
        await send_text(context, user_id, MENU_TEXTS[text], contact_keyboard())
    else:
        await send_text(context, user_id, UNKNOWN_TEXT, main_keyboard())


async def handle_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Request URLs and update bodies can contain secrets or personal information.
    logger.error("Update failed (%s)", type(context.error).__name__)
    if isinstance(update, Update) and update.effective_user:
        try:
            await send_text(context, update.effective_user.id,
                            "⚠️ مشکلی در انجام درخواست پیش آمد\n\nلطفاً کمی بعد دوباره تلاش کنید یا با پشتیبانی تماس بگیرید.",
                            trade_section_keyboard() if context.user_data.get("active_section") == "trade" else contact_keyboard())
        except TelegramError:
            logger.warning("Could not deliver the error notification")


async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data.pop("ticket_until", None)
    if update.effective_user and await require_membership(context, update.effective_user.id):
        context.user_data.pop("trade_awaiting_uid", None)
        context.user_data.pop("phone_requested_until", None)
        context.user_data["active_section"] = "home"
        await send_text(context, update.effective_user.id, HOME_TEXT, persistent_menu_keyboard())


async def show_trade(context: ContextTypes.DEFAULT_TYPE, user_id: int, *, begin_check: bool = False) -> None:
    if not await require_trade_phone(context, user_id):
        return
    settings = settings_for(context)
    if not settings.xt_ready:
        await send_text(context, user_id,
                        "📈 ترید با اهوراماین\n\nبررسی خودکار حساب XT هنوز فعال نشده است. برای راهنمایی با پشتیبانی تماس بگیرید.",
                        trade_keyboard(settings_for(context).xt_referral_url))
        return
    if begin_check:
        context.user_data["trade_awaiting_uid"] = time.monotonic() + 600
        await send_text(context, user_id,
                        "🔎 بررسی شرایط حساب XT\n\nشناسهٔ عددی حساب XT خود (UID) را ارسال کنید.\nUID ارسالی برای پیگیری اشتراک در کنار شماره و شناسهٔ تلگرام شما ذخیره می‌شود.\nفقط UID لازم است؛ رمز عبور یا کلید API خود را ارسال نکنید.\n\nبررسی شامل کد دعوت اهوراماین و مجموع واریز حداقل ۱۰۰ USDT است.",
                        trade_keyboard(settings_for(context).xt_referral_url))
    else:
        await send_text(context, user_id,
                        "🎁 عضویت رایگان کانال VIP\n\n" + VPN_REMINDER +
                        "\n\n🔗 با لینک زیر داخل صرافی xt ثبت نام کنید و بعد از ثبت نام حساب خود را ۱۰۰ دلار شارژ کنید" +
                        "\nکد دعوت اهوراماین: " + settings.xt_referral_code +
                        "\n\n🔎 برای دریافت اشتراک رایگان گزینه بررسی شرایط حساب را بزنید و بعد UID حساب صرافی خودتان را ارسال کنید" +
                        "\n\n✅ شرایط تأیید: ثبت‌نام با کد دعوت اهوراماین و مجموع واریز حداقل ۱۰۰ USDT.",
                        trade_keyboard(settings.xt_referral_url), bold_lines=(VPN_REMINDER,))


async def check_trade_uid(context: ContextTypes.DEFAULT_TYPE, user_id: int, text: str) -> None:
    if not await require_trade_phone(context, user_id):
        return
    now = time.monotonic()
    if now > context.user_data.get("trade_awaiting_uid", 0):
        context.user_data.pop("trade_awaiting_uid", None)
        await send_text(context, user_id, "⏱ زمان ارسال شناسه تمام شد\n\nدوباره دکمهٔ بررسی را بزنید.", trade_keyboard(settings_for(context).xt_referral_url))
        return
    uid = normalize_uid(text)
    if uid is None:
        await send_text(context, user_id, "🔎 شناسهٔ نامعتبر\n\nلطفاً فقط UID عددی حساب XT خود را ارسال کنید.", trade_keyboard(settings_for(context).xt_referral_url))
        return
    if now < context.user_data.get("trade_next_check_at", 0):
        await send_text(context, user_id, "⏱ لطفاً چند ثانیه صبر کنید\n\nسپس دوباره UID را ارسال کنید.", trade_keyboard(settings_for(context).xt_referral_url))
        return
    if not context.bot_data["contacts"].take_xt_slot(user_id, time.time()):
        await send_text(context, user_id, "⏱ لطفاً چند ثانیه صبر کنید و دوباره تلاش کنید.", trade_section_keyboard())
        return
    if context.bot_data["contacts"].binding_conflicts(user_id, uid):
        await send_text(context, user_id, "⚠️ امکان استفاده از این UID برای این حساب تلگرام وجود ندارد. با پشتیبانی تماس بگیرید.", trade_section_keyboard())
        return
    context.user_data["trade_next_check_at"] = now + 15
    context.bot_data["contacts"].save_uid(user_id, uid, status="submitted")
    try:
        result = await context.bot_data["xt_verifier"].verify(uid)
    except XTUnavailable:
        context.bot_data["contacts"].save_uid(user_id, uid, status="unavailable")
        await send_text(context, user_id,
                        "⚠️ بررسی حساب انجام نشد\n\nدر حال حاضر پاسخ معتبری از صرافی دریافت نشد. کمی بعد دوباره تلاش کنید یا با پشتیبانی تماس بگیرید.",
                        trade_keyboard(settings_for(context).xt_referral_url))
        return
    status = "not_referred" if not result.referred else ("eligible" if result.sufficient_deposit else "below_threshold")
    context.bot_data["contacts"].save_uid(user_id, uid, status=status)
    context.user_data.pop("trade_awaiting_uid", None)
    if not result.referred:
        text = "❌ کد دعوت تأیید نشد\n\nحساب واردشده با کد دعوت اهوراماین مطابقت ندارد. برای بررسی بیشتر با پشتیبانی تماس بگیرید."
    elif not result.sufficient_deposit:
        text = "🔎 نتیجهٔ بررسی حساب\n\n✅ کد دعوت اهوراماین تأیید شد.\n❌ مجموع واریز ثبت‌شده به حداقل ۱۰۰ USDT نرسیده است."
    else:
        try:
            state, link = await issue_reward(context, user_id, uid)
        except (TelegramError, RewardConflict):
            await send_text(context, user_id, "⚠️ ساخت درخواست عضویت انجام نشد. با پشتیبانی تماس بگیرید.", trade_section_keyboard())
            return
        if state == "invite":
            await send_text(context, user_id,
                            "🎉 شرایط حساب تأیید شد\n\nUID شما به این حساب تلگرام اختصاص یافت.\nاین درخواست عضویت فقط برای حساب تلگرام شما معتبر است و ۱۰ دقیقه اعتبار دارد. پس از ارسال درخواست، شرایط شما دوباره بررسی می‌شود.",
                            reward_keyboard(link))
            return
        if state == "conflict":
            text = "⚠️ امکان تخصیص این UID وجود ندارد. با پشتیبانی تماس بگیرید."
        else:
            text = "✅ شرایط حساب تأیید شد\n\nعضویت امن کانال هنوز پیکربندی نشده است. با پشتیبانی تماس بگیرید."
    await send_text(context, user_id, text, trade_keyboard(settings_for(context).xt_referral_url))


VPN_REMINDER = "لطفا vpn خود را خاموش کنید"


async def show_trade_room(context: ContextTypes.DEFAULT_TYPE, user_id: int) -> None:
    if not await require_trade_phone(context, user_id):
        return
    await send_text(context, user_id,
                    "📈 اتاق ترید اهورا\n\nیکی از گزینه‌های زیر را انتخاب کنید:\n• 🎟 دریافت اشتراک\n• 📊 برآیند معاملات\n• 🎓 آموزش کار با صرافی XT",
                    trade_menu_keyboard())


async def show_trade_section(context: ContextTypes.DEFAULT_TYPE, user_id: int, *, training: bool) -> None:
    if not await require_trade_phone(context, user_id):
        return
    text = (
        "🎓 آموزش کار با صرافی XT\n\nمحتوای آموزشی به‌زودی در این بخش قرار می‌گیرد. برای راهنمایی فعلاً با پشتیبانی تماس بگیرید."
        if training else
        VIP_SUBSCRIPTION_TEXT
    )
    await send_text(context, user_id, text, trade_section_keyboard() if training else subscription_keyboard())


async def require_trade_phone(context: ContextTypes.DEFAULT_TYPE, user_id: int) -> bool:
    context.user_data["active_section"] = "trade"
    if context.bot_data["contacts"].has_contact(user_id):
        return True
    context.user_data.pop("trade_awaiting_uid", None)
    context.user_data["phone_requested_until"] = time.monotonic() + 600
    await send_text(context, user_id,
                    "📱 ثبت شماره برای ورود به اتاق ترید\n\nبرای استفاده از بخش ترید، شمارهٔ حساب تلگرام خود را با دکمهٔ زیر به اشتراک بگذارید.\nبا زدن دکمه، با ذخیرهٔ شماره در اهوراماین برای ثبت‌نام و پیگیری خدمات ترید موافقت می‌کنید. UID صرافی که بعداً ارسال می‌کنید نیز به همین پرونده اضافه می‌شود.\nشماره را تایپ نکنید و مخاطب شخص دیگری را نفرستید.\n\nبرای حذف شماره و UID پرونده، دستور /deletephone را بفرستید. سابقهٔ تخصیص اشتراک برای جلوگیری از استفادهٔ تکراری نگهداری می‌شود. می‌توانید بدون ثبت شماره از بخش لایتنینگ استفاده کنید.",
                    phone_keyboard())
    return False


async def handle_contact(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = getattr(update, "effective_chat", None)
    if chat is not None and chat.type != "private":
        return
    message, user = update.effective_message, update.effective_user
    if message is None or user is None:
        return
    if not await require_membership(context, user.id):
        return
    if time.monotonic() > context.user_data.get("phone_requested_until", 0):
        await send_text(context, user.id, "📱 ابتدا وارد اتاق ترید شوید و دکمهٔ اشتراک‌گذاری شماره را بزنید.", persistent_menu_keyboard())
        return
    contact = message.contact
    if contact is None or contact.user_id != user.id or not normalize_phone(contact.phone_number):
        await send_text(context, user.id, "⚠️ لطفاً فقط شمارهٔ حساب خود را با دکمهٔ «اشتراک‌گذاری شمارهٔ من» ارسال کنید.", phone_keyboard())
        return
    context.bot_data["contacts"].save(user.id, contact.phone_number)
    context.user_data.pop("phone_requested_until", None)
    # Remove the contact message from the chat when Telegram permits it.
    try:
        await message.delete()
    except TelegramError:
        pass
    await send_text(context, user.id, "✅ شمارهٔ شما ثبت شد.", trade_menu_keyboard())
    await show_trade_room(context, user.id)


async def delete_phone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user is None:
        return
    user_id = update.effective_user.id
    context.user_data.pop("ticket_until", None)
    context.bot_data["contacts"].delete(user_id)
    context.user_data.pop("phone_requested_until", None)
    context.user_data.pop("trade_awaiting_uid", None)
    await send_text(context, user_id, "🗑 شماره و UID پروندهٔ شما حذف شدند و دعوت‌های استفاده‌نشده غیرفعال شدند. سابقهٔ تخصیص اشتراک برای جلوگیری از استفادهٔ تکراری حفظ می‌شود. برای ورود دوباره به ترید باید شماره را به اشتراک بگذارید.", persistent_menu_keyboard())


async def show_subscriptions(context: ContextTypes.DEFAULT_TYPE, user_id: int) -> None:
    if not await require_trade_phone(context, user_id):
        return
    await send_text(context, user_id,
                    "🎟 دریافت اشتراک\n\nنوع اشتراک موردنظر را انتخاب کنید:\n🎁 عضویت رایگان کانال VIP\n💳 اشتراک با پرداخت هزینه",
                    subscription_menu_keyboard())


async def show_trade_results(context: ContextTypes.DEFAULT_TYPE, user_id: int) -> None:
    if not await require_trade_phone(context, user_id):
        return
    from .member_services import show_dashboard
    await show_dashboard(context, user_id)
