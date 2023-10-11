from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, MessageHandler, Filters, CallbackContext
import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
required_channel_id = '@bazarrgani_ahora'


def start(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id

    welcome_text = "سلام 🙋‍♂️ \n به ربات ماینر بات خوش اومدی . \n برای استفاده از ربات لطفا در کانال زیر عضو شو. "

    keyboard = [
        [InlineKeyboardButton("کانال ماینر بات", url="https://t.me/bazarrgani_ahora"),
         InlineKeyboardButton("جوین شدم ✅", callback_data="check_channel")]
    ]

    context.bot.send_message(
        chat_id=user_id, text=welcome_text, reply_markup=InlineKeyboardMarkup(keyboard))


def callback_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    user_id = query.from_user.id

    if query.data == 'check_channel':

        is_member = context.bot.get_chat_member(required_channel_id, user_id).status in [
            'member', "administrator"]
        if is_member:
            keyboard = ReplyKeyboardMarkup(
                [["دستگاه BTCLN21M PRO", "دستگاه BTCLN 21M"],
                 ["درآمد دستگاه", "مصرف برق و اینترنت دستگاه"],
                 ["ابزار لازم برای راه اندازی دستگاه",
                     "نحوه راه‌ اندازی و نگهداری دستگاه", "گارانتی دستگاه"],
                 ["نحوه اطلاع از قیمت ، ثبت سفارش و تحویل دستگاه"]]
            )
            context.bot.send_message(
                chat_id=user_id, text="چه کمکی از دستم برمیاد ؟ 😎", reply_markup=keyboard)
        else:
            context.bot.send_message(
                user_id, "شما عضو کانال ماینر بات نیستید ❌🤨")
            keyboard = [
                [InlineKeyboardButton("کانال ماینر بات", url="https://t.me/bazarrgani_ahora"),
                 InlineKeyboardButton("جوین شدم ✅", callback_data="check_channel")]
            ]
            context.bot.send_message(
                chat_id=user_id, reply_markup=InlineKeyboardMarkup(keyboard))


def handle_messages(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id

    if update.message.text == "دستگاه BTCLN21M PRO":
        faq_text = """Ram 8 to finally
        پردازنده ۵ هسته 1.8GHz 64 BIT
        Overclock
        دارای ۲ پورت USB3
        دارای ۲ پورت USB2
        دارای پورت HDMI
        ساخت کشور چین"""

        context.bot.send_message(chat_id=user_id, text=faq_text)

    elif update.message.text == "دستگاه BTCLN 21M":
        faq_text = """مدل BTCLN 21M 
        حافظه RM4
        پردازنده 4 هسته 1.5GHz 64 BT
        پشتیبانی از کابل شبکه و وایرلس
        دارای دو پورت usb3 و usb2
        دارای دو کانال خروجی مالی 
        پشتیبانی از کابل HDMI
        ساخت کشور چین"""

        context.bot.send_message(chat_id=user_id, text=faq_text)

    elif update.message.text == "درآمد دستگاه":
        faq_text = """- دستگاه BTCLN 21 M ماهانه بین ۳.۵ تا ۴.۵ میلیون تومان درآمد دارد که درامد خود را میتوانید از بین ۶ رمزارز  BTC , LTC , ETH , MATIC , DOGE , TRX, انتخاب کنید که چه ارزی را تحت عنوان درامد دریافت کنید. همچنین این قابلیت وجود دارد که بعد از هر برداشت رمز ارز انتخابی خود را تغییر دهید. 
        - با توجه به فعالیت اخیر دستگاه درآمد شما ارتباط زیادی با کوین انتخابی شما دارد و در شرایط فعلی بازار کوین MATIC \n\n - دستگاه  BTCLN 21 M PRO ماهانه بین ۵.۵ تا ۶.۵ میلیون تومان درآمد دارد که درامد خود را میتوانید از بین ۶ رمزارز  BTC , LTC , ETH , MATIC , DOGE , TRX, انتخاب کنید که چه ارزی را تحت عنوان درامد دریافت کنید. همچنین این قابلیت وجود دارد که بعد از هر برداشت رمز ارز انتخابی خود را تغییر دهید. 

- با توجه به فعالیت اخیر دستگاه درآمد شما ارتباط زیادی با کوین انتخابی شما دارد و در شرایط فعلی بازار کوین MATIC بازدهی بیشتری داشته است . بازدهی بیشتری داشته است ."""
        context.bot.send_message(chat_id=user_id, text=faq_text)

    elif update.message.text == "مصرف برق و اینترنت دستگاه":
        faq_text = """- مصرف برق دستگاه ۱۰۰ وات که معادل یک لامپ ۱۰۰ می‌باشد و با یک آداپتور تایپ سی ۵ ولت ۳ آمپر تغذیه می‌شود .
        - با توجه به مصرف برق پایین دستگاه،  هیچگونه محدودیتی بابت استفاده برق خانگی در منزل وجود ندارد .
         مصرف اینترنت دستگاه ماهانه ۳ گیگ می‌باشد .
        - مورد مهم اینکه دستگاه برای فعالیت هیچ گونه نیازی به فیلترشکن ندارد."""
        context.bot.send_message(chat_id=user_id, text=faq_text)

    elif update.message.text == "ابزار لازم برای راه اندازی دستگاه":
        faq_text = """۱_ کابل شبکه(LAN) 
        ۲_مودم ( مخابرات - سیم کارت )
        ۳_ ولت
        نکته : دستگاه به صورت وایرلس هم قابل استفاده است، اما با توجه به وضعیت اینترنت کشور ، استفاده از کابل شبکه (LAN) برای اتصال به شبکه انتخاب بهتری است."""
        context.bot.send_message(chat_id=user_id, text=faq_text)

    elif update.message.text == "نحوه راه‌ اندازی و نگهداری دستگاه":
        faq_text = """۱_ استفاده از محافظ‌ برق جهت جلوگیری از نوسانات برق.
        ۲_ دور از رطوبت و گرد و خاک نگهداری شود.
        ۳_ این دستگاه کاملا بی سر و صدا بوده و دارای فن خنک کننده می‌باشد، در نتیجه به هیچ گونه سایلنت باکس و تهویه نیازی ندارد. 
        ۴_ از اتصالات کابل‌ها اطمینان حاصل فرمایید. 
        ۵_ از آدرس ولت کوین انتخابی خود مطمئن شوید که مربوط به همان شبکه بلاک چین می‌باشد."""

        context.bot.send_message(chat_id=user_id, text=faq_text)

    elif update.message.text == "گارانتی دستگاه":
        faq_text = """_ دستگاه BTCLN21M توسط فروشگاه دارای ۱۲ ماه گارانتی قطعات می‌باشد .
        _ در تمامی مراحل راه اندازی دستگاه ، کارشناسان ما کنار شما خوهند بود، چنانچه دستگاه در راه اندازی به مشکل بخورد دستگاه فوق تعویض میگردد و تمامی هزینه ها به عهده فروشگاه می‌باشد."""
        context.bot.send_message(chat_id=user_id, text=faq_text)

    elif update.message.text == "نحوه اطلاع از قیمت ، ثبت سفارش و تحویل دستگاه":
        faq_text = """قیمت دستگاه BTCLN 21 M 
        39/900/000
        قیمت دستگاه BTCLN 21 M PRO
        59/900/000
        نکته : قیمت ها با دلار روز محاسبه می‌شود و برای بروزترین قیمت به کانال مراجعه کنید 
        برای ثبت سفارش ، نام خانوادگی به همراه شماره تماس ، شهر سکونت و تعداد مورد درخواست را ارسال کنید تا کارشناسان ما در اسرع وقت با شما تماس  حاصل نمایند. 
        - حداکثر زمان پاسخگویی ۴۸ ساعت می‌باشد.
        پیشاپیش از صبر و شکیبایی شما سپاسگزاریم 🙏🌹
        تحویل سفارش ها از طریق پست یا مراجعه حضوری به نزدیک‌ترین نماینده ما در آن استان انجام می شود."""
        context.bot.send_message(chat_id=user_id, text=faq_text)

    else:
        context.bot.send_message(chat_id=user_id, text="دستور تعریف نشده 😶")


def create_keyboard(buttons, category):
    return [
        [InlineKeyboardButton(str(
            button), callback_data=f"{category}_{str(button).lower().replace(' ', '_')}") for button in row]
        for row in buttons
    ]


def main():
    updater = Updater(TOKEN)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CallbackQueryHandler(callback_handler))
    dp.add_handler(MessageHandler(Filters.text & ~
                   Filters.command, handle_messages))

    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
