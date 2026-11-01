"""Native Telegram inline buttons; their surface follows the user's theme."""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup

from .config import Settings
from .content import PRODUCTS
from .catalog import Product

TRAINING_LABEL = "آموزش کار با صرافی XT"
FREE_LABEL = "اشتراک رایگان"
MONTHLY_LABEL = "اشتراک ماهانه"

LIGHTNING_LABEL = "⚡ دستگاه‌های لایتنینگ"
TRADE_LABEL = "📈 اتاق ترید اهورا ماین"

PRODUCT_IDS = {product["order_callback"].removeprefix("order_delivery"): label for label, product in PRODUCTS.items()}


def button(text: str, data: str, style: str | None = None) -> InlineKeyboardButton:
    return InlineKeyboardButton(text, callback_data=data, style=style)


def channel_keyboard(settings: Settings) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(f"📢 عضویت در {channel}", url=url, style="primary")]
        for channel, url in settings.required_channels
    ]
    rows.append([button("✅ عضو شدم؛ بررسی کن", "check_channel", "success")])
    return InlineKeyboardMarkup(rows)


def lightning_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [button("🔹 مدل دو کانال", "product:1", "primary"), button("🔹 مدل چهار کانال", "product:2", "primary")],
        [button("💎 مدل شش کانال", "product:3", "primary"), button("💎 مدل ده کانال", "product:4", "primary")],
        [button("💵 قیمت و درآمد همهٔ مدل‌ها", "prices", "success")],
        [button("🤝 درخواست نمایندگی", "agency"), button("💬 ارتباط با ما", "contact")],
    ])


def navigation_keyboard(product_id: str | None = None) -> InlineKeyboardMarkup:
    rows = []
    if product_id in PRODUCT_IDS:
        rows.append([button("↩️ بازگشت به دستگاه", f"product:{product_id}")])
    rows.append([button("⚡ دستگاه‌های لایتنینگ", "lightning")])
    rows.append([button("🏠 منوی اصلی", "home")])
    return InlineKeyboardMarkup(rows)


def contact_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💬 گفت‌وگو با پشتیبانی", url="https://t.me/Ahouraadmin01", style="success")],
        [InlineKeyboardButton("💬 مشاور فروش", url="https://t.me/Abolfazl_lashkari", style="primary")],
        [button("⚡ دستگاه‌های لایتنینگ", "lightning")],
        [button("🏠 منوی اصلی", "home")],
    ])


def product_keyboard(product: Product) -> InlineKeyboardMarkup:
    product_id = product["order_callback"].removeprefix("order_delivery")

    def detail(label: str, topic: str, style: str | None = None) -> InlineKeyboardButton:
        return button(label, f"info:{product_id}:{topic}", style)

    return InlineKeyboardMarkup([
        [detail("💵 قیمت و روش سفارش", product["order_callback"], "success")],
        [detail("💰 درآمد دستگاه", product["income_callback"]), detail("🎬 آموزش راه‌اندازی", product["setup_callback"])],
        [detail("⚡ برق و اینترنت", "power_internet"), detail("🛡 گارانتی", "warranty")],
        [detail("🔧 نگهداری دستگاه", "setup_maintenance"), detail("🔌 وسایل موردنیاز", "tools")],
        [button("💬 مشاوره خرید", "contact", "primary")],
        [button("⚡ دستگاه‌های لایتنینگ", "lightning")],
        [button("🏠 منوی اصلی", "home")],
    ])


def lightning_menu_keyboard() -> ReplyKeyboardMarkup:
    """Show device shortcuts while allowing Telegram to dismiss the keyboard."""
    return ReplyKeyboardMarkup([
        [KeyboardButton("مدل دو کانال 🚀", style="primary"), KeyboardButton("مدل چهار کانال 🚀", style="primary")],
        [KeyboardButton("مدل شش کانال 🚀", style="primary"), KeyboardButton("مدل ده کانال 🚀", style="primary")],
        [KeyboardButton("💵 قیمت و درآمد دستگاه‌ها", style="success")],
        [KeyboardButton("اخذ نمایندگی 👨‍💼"), KeyboardButton("ارتباط با ما 📧")],
        [KeyboardButton("🏠 منوی اصلی")],
    ], resize_keyboard=True, is_persistent=False, one_time_keyboard=False,
       input_field_placeholder="یک دستگاه یا گزینه را انتخاب کنید…")


def trade_menu_keyboard() -> ReplyKeyboardMarkup:
    """Show trade shortcuts while allowing Telegram to dismiss the keyboard."""
    return ReplyKeyboardMarkup([
        [KeyboardButton(TRAINING_LABEL, style="primary")],
        [KeyboardButton(FREE_LABEL, style="success")],
        [KeyboardButton(MONTHLY_LABEL)],
        [KeyboardButton("🏠 منوی اصلی")],
    ], resize_keyboard=True, is_persistent=False, one_time_keyboard=False,
       input_field_placeholder="یک گزینه را انتخاب کنید…")




def main_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [button(LIGHTNING_LABEL, "lightning", "primary")],
        [button(TRADE_LABEL, "trade", "success")],
    ])


def persistent_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup([
        [KeyboardButton(LIGHTNING_LABEL, style="primary")],
        [KeyboardButton(TRADE_LABEL, style="success")],
    ], resize_keyboard=True, is_persistent=False, one_time_keyboard=False,
       input_field_placeholder="بخش موردنظر را انتخاب کنید…")


def trade_keyboard(referral_url: str = "") -> InlineKeyboardMarkup:
    rows = []
    if referral_url.startswith("https://"):
        rows.append([InlineKeyboardButton("🔗 ثبت‌نام با کد اهوراماین", url=referral_url, style="primary")])
    return InlineKeyboardMarkup(rows + [
        [button("🔎 بررسی شرایط حساب XT", "trade:check", "success")],
        [button("↩️ بازگشت به اتاق ترید", "trade")],
        [button("💬 ارتباط با پشتیبانی", "contact")],
        [button("🏠 منوی اصلی", "home")],
    ])


def reward_keyboard(invite_url: str) -> InlineKeyboardMarkup:
    """Only attach this keyboard after a fresh successful XT eligibility check."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎁 عضویت در کانال خصوصی اهوراماین", url=invite_url, style="success")],
        [button("🏠 منوی اصلی", "home")],
    ])


def trade_section_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [button("💬 ارتباط با پشتیبانی", "contact")],
        [button("↩️ بازگشت به اتاق ترید", "trade")],
        [button("🏠 منوی اصلی", "home")],
    ])
