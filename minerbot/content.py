"""Catalog snapshot from the supplied Ahura product page (2026-10-27)."""

PRODUCTS = {
    'مدل چهار کانال 🚀': {
        'description': """مدل چهار کانال 🚀

• ۴ کانال
• مصرف اینترنت درج‌شده: ماهانه ۳ گیگابایت

مدلی متعادل از نظر تعداد کانال، ابعاد و اتصال‌ها.""",
        'image': 'four-channels.jpg',
        'order_callback': 'order_delivery2',
        'income_callback': 'income1',
        'setup_callback': 'fourChannelDeviceSetupCallback',
        'price_usdt': 1400,
        'monthly_income_usd': 75,
        'source_url': 'https://ahuraminer.com/products/lightning-nodes',
        'source_checked': '2026-10-27',
    },
    'مدل دو کانال 🚀': {
        'description': """مدل دو کانال 🚀

• ۲ کانال
• مصرف اینترنت درج‌شده: ماهانه ۳ گیگابایت

مدل جمع‌وجور برای شروع کار با شبکهٔ لایتنینگ.""",
        'image': 'two-channels.jpg',
        'order_callback': 'order_delivery1',
        'income_callback': 'income2',
        'setup_callback': 'twoChannelDeviceSetupCallback',
        'price_usdt': 1020,
        'monthly_income_usd': 50,
        'source_url': 'https://ahuraminer.com/products/lightning-nodes',
        'source_checked': '2026-10-27',
    },
    'مدل شش کانال 🚀': {
        'description': """مدل شش کانال 🚀

• ۶ کانال
• مصرف اینترنت درج‌شده: ماهانه ۳ گیگابایت

ظرفیت بیشتر برای مدیریت کانال‌ها و خروجی‌های متنوع تصویر.""",
        'image': 'six-channels.jpg',
        'order_callback': 'order_delivery3',
        'income_callback': 'income3',
        'setup_callback': 'sixChannelDeviceSetupCallback',
        'price_usdt': 4050,
        'monthly_income_usd': 250,
        'source_url': 'https://ahuraminer.com/products/lightning-nodes',
        'source_checked': '2026-10-27',
    },
    'مدل ده کانال 🚀': {
        'description': """مدل ده کانال 💎

• ۱۰ کانال
• درگاه‌های LAN، HDMI، VGA، USB و Audio
• مصرف برق تقریبی: ۶۰ وات
• مصرف اینترنت وابسته به شرایط شبکه

مدل پرچم‌دار خانوادهٔ اهورا با بیشترین تعداد کانال و درگاه ارتباطی.""",
        'image': '',
        'order_callback': 'order_delivery4',
        'income_callback': 'income4',
        'setup_callback': 'tenChannelDeviceSetupCallback',
        'price_usdt': 6750,
        'monthly_income_usd': 410,
        'source_url': 'https://ahuraminer.com/products/lightning-nodes',
        'source_checked': '2026-10-27',
    },
}

CALLBACK_TEXTS = {
    'power_internet': """⚡ برق و اینترنت

• مصرف برق تقریبی درج‌شده در سایت: ۶۰ وات
• اینترنت مدل‌های ۲، ۴ و ۶ کانال: ماهانه حدود ۳ گیگابایت
• اینترنت مدل ۱۰ کانال: وابسته به شرایط شبکه

مشخصات نسخهٔ تحویلی را پیش از خرید با مشاور بررسی کنید.""",
    'tools': """🔌 وسایل موردنیاز

• مودم ثابت یا سیم‌کارتی
• کابل شبکه (LAN)
• کیف پول سازگار با رمزارز انتخابی

برای اتصال پایدارتر، استفاده از کابل شبکه پیشنهاد می‌شود. پشتیبانی از وای‌فای به مدل دستگاه بستگی دارد.""",
    'setup_maintenance': """🔧 راهنمای نگهداری

• از محافظ برق استفاده کنید.
• دستگاه را دور از رطوبت و گردوغبار نگه دارید.
• مسیر گردش هوا و فن را باز بگذارید.
• اتصال کابل‌ها را بررسی کنید.
• پیش از برداشت، آدرس کیف پول و شبکهٔ رمزارز را بررسی کنید.

برای راهنمایی دربارهٔ محل نصب، با پشتیبانی تماس بگیرید.""",
    'warranty': """🛡 گارانتی و پشتیبانی

شرایط اعلام‌شدهٔ فروشگاه:
• ۳۰ روز مهلت تست
• ۱۲ ماه گارانتی
• ۳۶ ماه خدمات پس از فروش و پشتیبانی آنلاین
• همراهی کارشناسان در راه‌اندازی دستگاه

برای اطلاع از شرایط تعویض و هزینه‌های مربوط، پیش از خرید با مشاور فروش هماهنگ کنید.""",
    'tenChannelDeviceSetupCallback': """🎬 راه‌اندازی مدل ده کانال

برای دریافت آموزش مخصوص این مدل، از بخش «ارتباط با ما» با پشتیبانی تماس بگیرید.""",
}

SETUP_VIDEOS = {
    'fourChannelDeviceSetupCallback': 'https://ahuraminer.com/wp-content/uploads/2024/12/four-channel-device.mp4',
    'sixChannelDeviceSetupCallback': 'https://ahuraminer.com/wp-content/uploads/2024/12/six-channel-device.mp4',
    'twoChannelDeviceSetupCallback': 'two-channel-device.mp4',
}

MENU_TEXTS = {
    'اخذ نمایندگی 👨\u200d💼': """🤝 درخواست نمایندگی

برای دریافت نمایندگی استان یا شهرستان، با مشاور فروش تماس بگیرید.

شرایط اعلام‌شده:
• تجربه و توانایی فروش
• داشتن امکانات اولیهٔ کسب‌وکار
• تعهد به مشتریان و حفظ ارتباط با مجموعه

مدارک اعلام‌شده:
• درخواست کتبی
• مدارک هویتی
• نشانی دقیق متقاضی

پیش از ارسال مدارک، مراحل و شرایط را با مشاور هماهنگ کنید.""",
    'ارتباط با ما 📧': """💬 ارتباط با ما

🛟 پشتیبانی

آیدی: @poshtibaniahura02
شماره: 09153362103

آیدی: @Ahouraadmin01
شماره: 09051352153

آیدی: @Abolfazl_lashkari
شماره: 09154039200

🛍 فروش

آیدی: @Ahuraadmin01
شماره: 09150370080

آیدی: @AhuraSalesManager
شماره: 09150370070

برای شروع گفت‌وگو، یکی از دکمه‌های زیر را انتخاب کنید.""",
}

SUPPORT_CONTACTS = (
    ("poshtibaniahura02", "09153362103"),
    ("Ahouraadmin01", "09051352153"),
    ("Abolfazl_lashkari", "09154039200"),
)
SALES_CONTACTS = (
    ("Ahuraadmin01", "09150370080"),
    ("AhuraSalesManager", "09150370070"),
)

VIP_SUBSCRIPTION_TEXT = """💳 اشتراک کانال VIP

💵 هزینهٔ اشتراک:
• یک‌ماهه: ۱۰۰ دلار
• سه‌ماهه: ۲۵۰ دلار
• شش‌ماهه: ۴۰۰ دلار
• یک‌ساله: ۷۰۰ دلار

💬 برای دریافت اشتراک، به یکی از آیدی‌های پشتیبانی زیر پیام دهید:

@poshtibaniahura02
09153362103

@Ahouraadmin01
09051352153

@Abolfazl_lashkari
09154039200

برای شروع گفت‌وگو از دکمه‌های زیر استفاده کنید."""
