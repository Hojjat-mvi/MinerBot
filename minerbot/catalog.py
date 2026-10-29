"""Shared catalog rendering so cards and detail screens use the same figures."""

from typing import TypedDict

from .content import PRODUCTS


class Product(TypedDict):
    description: str
    image: str
    order_callback: str
    income_callback: str
    setup_callback: str
    price_usdt: int
    monthly_income_usd: int
    source_url: str
    source_checked: str


CONVERSION_NOTE = "درآمد: معادل تقریبی با فرض ۱ دلار ≈ ۱ USDT؛ پیش از کسر هزینه‌ها."
CATALOG_NOTE = "ارقام موقت کاتالوگ سایت؛ قیمت نهایی و عملکرد باید تأیید شوند."
PERSIAN_DIGITS = str.maketrans("0123456789,", "۰۱۲۳۴۵۶۷۸۹٬")


def amount(value: int) -> str:
    return f"{value:,}".translate(PERSIAN_DIGITS)


def financial_lines(product: Product) -> str:
    return (
        f"💵 قیمت کاتالوگ: {amount(product['price_usdt'])} USDT\n"
        f"💰 درآمد تقریبی ماهانه: ≈ {amount(product['monthly_income_usd'])} USDT"
    )


def product_card(product: Product) -> str:
    return f"{product['description']}\n\n{financial_lines(product)}\n\n{CONVERSION_NOTE}\n{CATALOG_NOTE}"


def financial_details(product: Product, *, income: bool = False) -> str:
    title = "💰 درآمد دستگاه" if income else "💵 قیمت و روش سفارش"
    text = f"{title}\n\n{product['description'].splitlines()[0]}\n\n{financial_lines(product)}\n\n{CONVERSION_NOTE}\n{CATALOG_NOTE}"
    if not income:
        text += "\n\nبرای ثبت درخواست، از بخش «ارتباط با ما» نام خانوادگی، شمارهٔ تماس، شهر و تعداد دستگاه را برای مشاور فروش ارسال کنید."
    return text + f"\n\nمنبع: {product['source_url']}\nتاریخ بررسی: {product['source_checked']}"


def catalog_summary() -> str:
    lines = ["💵 قیمت و درآمد دستگاه‌ها", ""]
    for product in sorted(PRODUCTS.values(), key=lambda item: item["price_usdt"]):
        lines.extend([product["description"].splitlines()[0], financial_lines(product), ""])
    return "\n".join(lines) + f"\n{CONVERSION_NOTE}\n{CATALOG_NOTE}"
