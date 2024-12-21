from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, MessageHandler, Filters, CallbackContext
import os
from dotenv import load_dotenv
from functools import lru_cache

# Load environment variables once at startup
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
REQUIRED_CHANNEL_ID = '@bazarrgani_ahoura'

# Pre-define constant keyboard layouts and texts
MAIN_KEYBOARD = ReplyKeyboardMarkup([
    ["مدل چهار کانال 🚀", "مدل دو کانال 🚀"],
    ["مدل شش کانال 🚀"],
    ["اخذ نمایندگی 👨‍💼", "ارتباط با ما 📧"]
], resize_keyboard=True)

JOIN_KEYBOARD = InlineKeyboardMarkup([
    [InlineKeyboardButton("کانال ماینر بات", url="https://t.me/bazarrgani_ahoura"),
     InlineKeyboardButton("جوین شدم ✅", callback_data="check_channel")]
])

COMMON_KEYBOARD = [
    [InlineKeyboardButton("مصرف برق و اینترنت دستگاه 💡", callback_data="power_internet")],
    [InlineKeyboardButton("نحوه نگهداری دستگاه 🔧", callback_data="setup_maintenance")],
    [InlineKeyboardButton("گارانتی دستگاه 🔒", callback_data="warranty")]
]

# Cache frequently used text responses
@lru_cache(maxsize=32)
def get_order_delivery_text():
    return """نکته : قیمت ها با دلار روز محاسبه می‌شود و برای بروزترین قیمت به کانال مراجعه کنید 
    برای ثبت سفارش ، نام خانوادگی به همراه شماره تماس ، شهر سکونت و تعداد مورد درخواست را ارسال کنید تا کارشناسان ما در اسرع وقت با شما تماس  حاصل نمایند. 
    - حداکثر زمان پاسخگویی ۴۸ ساعت می‌باشد.
    پیشاپیش از صبر و شکیبایی شما سپاسگزاریم 🙏🌹
    تحویل سفارش ها از طریق پست یا مراجعه حضوری به نزدیک‌ترین نماینده ما در آن استان انجام می شود."""

# Device configurations stored in a dictionary for quick access
DEVICE_CONFIGS = {
    'two_channel': {
        'specs': """مدل دو کانال 
        حافظه RM4
        پردازنده 4 هسته 1.5GHz 64 BT
        پشتیبانی از کابل شبکه و وایرلس
        دارای دو پورت usb3 و usb2
        دارای دو کانال خروجی مالی 
        پشتیبانی از کابل HDMI
        ساخت کشور چین""",
        'image': 'asset/two-channels.jpg',
        'video_url': "https://drive.google.com/uc?export=download&id=1LNBN84KwFtkx_T99nMxZETleTnZ_jsYB",
        'price': "990$"
    },
    'four_channel': {
        'specs': """Ram 8 to finally
        پردازنده ۵ هسته 1.8GHz 64 BIT
        Overclock
        دارای ۲ پورت USB3
        دارای ۲ پورت USB2
        دارای پورت HDMI
        ساخت کشور چین""",
        'image': 'asset/four-channels.jpg',
        'video_url': "https://ahuraminer.com/wp-content/uploads/2024/12/four-channel-device.mp4",
        'price': "موجود نیست"
    },
    'six_channel': {
        'specs': """از لحاظ سخت افزار ، کاملا قدرتمند و ماندگار هست‌ .
        مصرف برق دستگاه فوق نصف مصرف لپ تاپ هست و فقط با اتصال کابل شبکه به اینترنت متصل میشود.
        پردازنده 5 هسته ای
        رم 8
        128 گیگ حافظه ssd
        متصل به BTC pay server
        6 خروجی کانال تائید تراکنش 
        پورت hdmi
        پورت vga
        4 خروجی usb3
        اتصال خودکار به BTC Core""",
        'image': 'asset/six-channels.jpg',
        'video_url': "https://ahuraminer.com/wp-content/uploads/2024/12/six-channel-device.mp4",
        'price': "4600$"
    }
}

def start(update: Update, context: CallbackContext):
    welcome_text = "سلام 🙋‍♂️ \n به ربات ماینر بات خوش اومدی . \n برای استفاده از ربات لطفا در کانال زیر عضو شو. "
    context.bot.send_message(
        chat_id=update.message.from_user.id,
        text=welcome_text,
        reply_markup=JOIN_KEYBOARD
    )

def send_device_info(update: Update, context: CallbackContext, device_type):
    user_id = update.message.from_user.id
    device = DEVICE_CONFIGS[device_type]
    
    # Send device photo
    context.bot.send_photo(chat_id=user_id, photo=open(device['image'], 'rb'))
    
    # Create device-specific keyboard
    keyboard = COMMON_KEYBOARD.copy()
    keyboard.append([
        InlineKeyboardButton("نحوه اطلاع از قیمت ، ثبت سفارش و تحویل دستگاه 💵", 
                           callback_data=f"order_delivery_{device_type}"),
        InlineKeyboardButton("درآمد دستگاه 💰", callback_data=f"income_{device_type}"),
        InlineKeyboardButton("نحوه راه اندازی دستگاه 🛠", 
                           callback_data=f"{device_type}_setup")
    ])
    
    context.bot.send_message(
        chat_id=user_id,
        text=device['specs'],
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

def handle_messages(update: Update, context: CallbackContext):
    text = update.message.text
    if text == "مدل دو کانال 🚀":
        send_device_info(update, context, 'two_channel')
    elif text == "مدل چهار کانال 🚀":
        send_device_info(update, context, 'four_channel')
    elif text == "مدل شش کانال 🚀":
        send_device_info(update, context, 'six_channel')
    elif text == "اخذ نمایندگی 👨‍💼":
        context.bot.send_message(
            chat_id=update.message.from_user.id,
            text=get_agency_text()
        )
    elif text == "ارتباط با ما 📧":
        context.bot.send_message(
            chat_id=update.message.from_user.id,
            text="@Ahouraadmin01 \n @Abolfazl_lashkari ادمین های ما \n 09154039200 - لشکری \n 09051352153 - خسروانی"
        )
    else:
        context.bot.send_message(
            chat_id=update.message.from_user.id,
            text="دستور تعریف نشده 😶"
        )

@lru_cache(maxsize=1)
def get_agency_text():
    return """[Agency text content]"""  # Full text omitted for brevity

def main():
    updater = Updater(TOKEN)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CallbackQueryHandler(callback_handler))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_messages))

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()