from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, MessageHandler, Filters, CallbackContext
import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
required_channel_id = '@bazarrgani_ahoura'


def start(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    welcome_text = "سلام 🙋‍♂️ \n به ربات ماینر بات خوش اومدی . \n برای استفاده از ربات لطفا در کانال زیر عضو شو. "
    keyboard = [
        [InlineKeyboardButton("کانال ماینر بات", url="https://t.me/bazarrgani_ahoura"),
         InlineKeyboardButton("جوین شدم ✅", callback_data="check_channel")]
    ]
    context.bot.send_message(
        chat_id=user_id, text=welcome_text, reply_markup=InlineKeyboardMarkup(keyboard))


def callback_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    user_id = query.from_user.id
    orderDelivery = """نکته : قیمت ها با دلار روز محاسبه می‌شود و برای بروزترین قیمت به کانال مراجعه کنید 
        برای ثبت سفارش ، نام خانوادگی به همراه شماره تماس ، شهر سکونت و تعداد مورد درخواست را ارسال کنید تا کارشناسان ما در اسرع وقت با شما تماس  حاصل نمایند. 
        - حداکثر زمان پاسخگویی ۴۸ ساعت می‌باشد.
        پیشاپیش از صبر و شکیبایی شما سپاسگزاریم 🙏🌹
        تحویل سفارش ها از طریق پست یا مراجعه حضوری به نزدیک‌ترین نماینده ما در آن استان انجام می شود."""

    if query.data == 'check_channel':
        is_member = context.bot.get_chat_member(required_channel_id, user_id).status in [
            'member', "owner", "administrator"]
        if is_member:
            keyboard = ReplyKeyboardMarkup([
                ["مدل چهار کانال 🚀", "مدل دو کانال 🚀"],
                ["مدل شش کانال 🚀"],
                ["اخذ نمایندگی 👨‍💼", "ارتباط با ما 📧"]
            ], resize_keyboard=True)
            context.bot.send_message(
                chat_id=user_id, text="چه کمکی از دستم برمیاد ؟ 😎", reply_markup=keyboard)
        else:
            keyboard = [
                [InlineKeyboardButton("کانال ماینر بات", url="https://t.me/bazarrgani_ahoura"),
                 InlineKeyboardButton("جوین شدم ✅", callback_data="check_channel")]
            ]
            context.bot.send_message(
                chat_id=user_id, text="شما عضو کانال ماینر بات نیستید ❌🤨", reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data == 'income1':
        faq_text = """- دستگاه  چهار کانال ماهانه بین ۵.۵ تا ۶.۵ میلیون تومان درآمد دارد که درامد خود را میتوانید از بین ۶ رمزارز  BTC, LTC , ETH , MATIC , DOGE , TRX, انتخاب کنید که چه ارزی را تحت عنوان درامد دریافت کنید. همچنین این قابلیت وجود دارد که بعد از هر برداشت رمز ارز انتخابی خود را تغییر دهید. 

    - با توجه به فعالیت اخیر دستگاه درآمد شما ارتباط زیادی با کوین انتخابی شما دارد و در شرایط فعلی بازار کوین MATIC بازدهی بیشتری داشته است ."""
        context.bot.send_message(chat_id=user_id, text=faq_text)
    elif query.data == 'income2':
        faq_text = """- دستگاه دو کانال ماهانه بین ۳.۵ تا ۴.۵ میلیون تومان درآمد دارد که درامد خود را میتوانید از بین 8 رمزارز  BTC , LTC , ETH , DOT, LINK, MATIC , DOGE , TRX, انتخاب کنید که چه ارزی را تحت عنوان درامد دریافت کنید. همچنین این قابلیت وجود دارد که بعد از هر برداشت رمز ارز انتخابی خود را تغییر دهید.
        
        - با توجه به فعالیت اخیر دستگاه درآمد شما ارتباط زیادی با کوین انتخابی شما دارد و در شرایط فعلی بازار کوین MATIC بازدهی بیشتری داشته است ."""
        context.bot.send_message(chat_id=user_id, text=faq_text)

    elif query.data == 'income3':
        faq_text = """درآمد دستگاه\nدرامد این دستگاه ماهانه 333 تا 344 دلار می باشد.\nدرامد ماهیانه به تومان: تقریبا ۱۸ میلیون تومان\nپرداخت به صورت هر 9 روز و به مبلغ 100 دلار می باشد.\nحالت پرداخت درآمد به صورت یکی از ده ارز زیر و به صورت انتخابی خودتان می باشد:\nBTC\nETH\nLTC\nSOL\nDOT\nTRX\nMATIC\nAVAX\nXRP\nDOGE"""
        context.bot.send_message(chat_id=user_id, text=faq_text)

    elif query.data == "fourChannelDeviceSetupCallback":
        four_channel_device_video_url = "https://ahuraminer.com/wp-content/uploads/2024/12/four-channel-device.mp4"
        context.bot.send_video(
            chat_id=user_id, video=four_channel_device_video_url)
    elif query.data == "sixChannelDeviceSetupCallback":
        six_channel_device_video_url = "https://ahuraminer.com/wp-content/uploads/2024/12/six-channel-device.mp4"
        context.bot.send_video(
            chat_id=user_id, video=six_channel_device_video_url)
    elif query.data == "twoChannelDeviceSetupCallback":
        local_video_path = os.path.join("asset", "two-channel-device.mp4")

        if os.path.exists(local_video_path):
            try:
                # Send the video to the user
                context.bot.send_video(
                    chat_id=user_id, video=open(local_video_path, "rb"))
            except Exception as e:
                context.bot.send_message(
                    chat_id=user_id, text="خطای غیرمنتظره‌ای رخ داده است.")
        else:
            context.bot.send_message(
                chat_id=user_id, text="ویدیو در دسترس نیست. لطفاً فایل را بررسی کنید.")

    elif query.data == "power_internet":
        faq_text = """- مصرف برق دستگاه ۱۰۰ وات که معادل یک لامپ ۱۰۰ می‌باشد و با یک آداپتور لپ تاپ 5 آمپر تغذیه می‌شود .
        - با توجه به مصرف برق پایین دستگاه،  هیچگونه محدودیتی بابت استفاده برق خانگی در منزل وجود ندارد .
         مصرف اینترنت دستگاه ماهانه ۳ گیگ می‌باشد .
        - مورد مهم اینکه دستگاه برای فعالیت هیچ گونه نیازی به فیلترشکن ندارد."""
        context.bot.send_message(chat_id=user_id, text=faq_text)

    elif query.data == "tools":
        faq_text = """۱_ کابل شبکه(LAN) 
        ۲_مودم ( مخابرات - سیم کارت )
        ۳_ ولت
        نکته : دستگاه به صورت وایرلس هم قابل استفاده است، اما با توجه به وضعیت اینترنت کشور ، استفاده از کابل شبکه (LAN) برای اتصال به شبکه انتخاب بهتری است."""
        context.bot.send_message(chat_id=user_id, text=faq_text)

    elif query.data == "setup_maintenance":
        faq_text = """۱_ استفاده از محافظ‌ برق جهت جلوگیری از نوسانات برق.
        ۲_ دور از رطوبت و گرد و خاک نگهداری شود.
        ۳_ این دستگاه کاملا بی سر و صدا بوده و دارای فن خنک کننده می‌باشد، در نتیجه به هیچ گونه سایلنت باکس و تهویه نیازی ندارد. 
        ۴_ از اتصالات کابل‌ها اطمینان حاصل فرمایید. 
        ۵_ از آدرس ولت کوین انتخابی خود مطمئن شوید که مربوط به همان شبکه بلاک چین می‌باشد."""

        context.bot.send_message(chat_id=user_id, text=faq_text)

    elif query.data == "warranty":
        faq_text = """تمامی دستگاها توسط فروشگاه : 
- دارای 30 روز مهلت تست
- دارای 12 ماه گارانتی 
- 36 ماه خدمات پس از فروش و پشتیبانی آنلاین
- در تمامی مراحل راه اندازی دستگاه ، کارشناسان ما کنار شما خواهند بود و چنانچه دستگاه  مشکل فنی و راه اندازی داشته باشد، دستگاه کاملا تعویض میگردد و تمامی هزینه ها به عهده فروشگاه می‌باشد."""
        context.bot.send_message(chat_id=user_id, text=faq_text)

    elif query.data == "order_delivery1":
        faq_text = """قیمت دستگاه دو کانال 
        990$ \n""" + orderDelivery
        context.bot.send_message(chat_id=user_id, text=faq_text)
    elif query.data == "order_delivery2":
        faq_text = """قیمت دستگاه چهار کانال 
        موجود نیست \n""" + orderDelivery
        context.bot.send_message(chat_id=user_id, text=faq_text)
    elif query.data == "order_delivery3":
        faq_text = """قیمت دستگاه شش کانال
        4600$ \n""" + orderDelivery
        context.bot.send_message(chat_id=user_id, text=faq_text)


def handle_messages(update: Update, context: CallbackContext):
    """Safely handle incoming text messages with error handling and optimizations."""
    message = update.effective_message
    user = update.effective_user

    # Ensure both message and user exist
    if not message or not user:
        context.bot.logger.warning(f"Non-message update received: {update}")
        return

    user_id = user.id
    text = message.text or ""  # handle None safely

    # Base keyboard (always present)
    keyboard = [
        [InlineKeyboardButton("مصرف برق و اینترنت دستگاه 💡",
                              callback_data="power_internet")],
        [InlineKeyboardButton("نحوه نگهداری دستگاه 🔧",
                              callback_data="setup_maintenance")],
        [InlineKeyboardButton("گارانتی دستگاه 🔒", callback_data="warranty")],
    ]

    try:
        if text == "مدل چهار کانال 🚀":
            faq_text = (
                "Ram 8 to finally\n"
                "پردازنده ۵ هسته 1.8GHz 64 BIT\n"
                "Overclock\n"
                "دارای ۲ پورت USB3\n"
                "دارای ۲ پورت USB2\n"
                "دارای پورت HDMI\n"
                "ساخت کشور چین"
            )
            extra_buttons = [
                InlineKeyboardButton(
                    "نحوه اطلاع از قیمت ، ثبت سفارش و تحویل دستگاه 💵", callback_data="order_delivery2"),
                InlineKeyboardButton(
                    "درآمد دستگاه 💰", callback_data="income1"),
                InlineKeyboardButton(
                    "نحوه راه اندازی دستگاه 🛠", callback_data="fourChannelDeviceSetupCallback"),
            ]
            keyboard.append(extra_buttons)

            with open("asset/four-channels.jpg", "rb") as photo:
                context.bot.send_photo(chat_id=user_id, photo=photo)

            context.bot.send_message(
                chat_id=user_id, text=faq_text, reply_markup=InlineKeyboardMarkup(keyboard))

        elif text == "مدل دو کانال 🚀":
            faq_text = (
                "مدل دو کانال\n"
                "حافظه RM4\n"
                "پردازنده 4 هسته 1.5GHz 64 BT\n"
                "پشتیبانی از کابل شبکه و وایرلس\n"
                "دارای دو پورت usb3 و usb2\n"
                "دارای دو کانال خروجی مالی\n"
                "پشتیبانی از کابل HDMI\n"
                "ساخت کشور چین"
            )
            extra_buttons = [
                InlineKeyboardButton(
                    "نحوه اطلاع از قیمت ، ثبت سفارش و تحویل دستگاه 💵", callback_data="order_delivery1"),
                InlineKeyboardButton(
                    "درآمد دستگاه 💰", callback_data="income2"),
                InlineKeyboardButton(
                    "نحوه راه اندازی دستگاه 🛠", callback_data="twoChannelDeviceSetupCallback"),
            ]
            keyboard.append(extra_buttons)

            with open("asset/two-channels.jpg", "rb") as photo:
                context.bot.send_photo(chat_id=user_id, photo=photo)

            context.bot.send_message(
                chat_id=user_id, text=faq_text, reply_markup=InlineKeyboardMarkup(keyboard))

        elif text == "مدل شش کانال 🚀":
            faq_text = (
                "از لحاظ سخت افزار ، کاملا قدرتمند و ماندگار هست‌.\n\n"
                "مصرف برق دستگاه فوق نصف مصرف لپ تاپ هست و فقط با اتصال کابل شبکه به اینترنت متصل میشود.\n\n"
                "پردازنده 5 هسته ای\n"
                "رم 8\n"
                "128 گیگ حافظه ssd\n"
                "متصل به BTC pay server\n"
                "6 خروجی کانال تائید تراکنش\n"
                "پورت hdmi\n"
                "پورت vga\n"
                "4 خروجی usb3\n"
                "اتصال خودکار به BTC Core"
            )
            extra_buttons = [
                InlineKeyboardButton(
                    "نحوه اطلاع از قیمت ، ثبت سفارش و تحویل دستگاه 💵", callback_data="order_delivery3"),
                InlineKeyboardButton(
                    "درآمد دستگاه 💰", callback_data="income3"),
                InlineKeyboardButton(
                    "نحوه راه اندازی دستگاه 🛠", callback_data="sixChannelDeviceSetupCallback"),
            ]
            keyboard.append(extra_buttons)

            with open("asset/six-channels.jpg", "rb") as photo:
                context.bot.send_photo(chat_id=user_id, photo=photo)

            context.bot.send_message(
                chat_id=user_id, text=faq_text, reply_markup=InlineKeyboardMarkup(keyboard))

        elif text == "اخذ نمایندگی 👨‍💼":
            faq_text = (
                "اعطای نمایندگی:\n\n"
                "🎯 چگونه به شبکه بزرگ فروش بازرگانی اهورا بپیوندیم؟!\n\n"
                "✅ اخذ نمایندگی کل استان و یا شهرستان:\n"
                "اشخاصی که در عرصه کسب و کار فعال می‌باشند...\n\n"
                "✅ شرایط لازم جهت اخذ نمایندگی بازرگانی اهورا:\n"
                "۱. تعهد به بازرگانی اهورا و مشتریان\n"
                "۲. داشتن حداقل امکانات\n"
                "۳. توانایی فروش\n"
                "۴. حفظ ارتباط با مشتری و بازرگانی\n\n"
                "✅ مدارک لازم:\n"
                "۱. درخواست کتبی\n"
                "۲. تصویر شناسنامه و کارت ملی\n"
                "۳. آدرس دقیق متقاضی"
            )
            context.bot.send_message(chat_id=user_id, text=faq_text)

        elif text == "ارتباط با ما 📧":
            context.bot.send_message(
                chat_id=user_id,
                text=(
                    "@Ahouraadmin01 \n"
                    "@Abolfazl_lashkari ادمین های ما\n"
                    "📞 09154039200 - لشکری\n"
                    "📞 09051352153 - خسروانی"
                ),
            )

        else:
            context.bot.send_message(
                chat_id=user_id, text="دستور تعریف نشده 😶")

    except Exception as e:
        # Catch any unexpected errors so bot never crashes
        context.bot.logger.error(f"Error handling message: {e}", exc_info=True)
        context.bot.send_message(
            chat_id=user_id, text="مشکلی پیش آمد. لطفا دوباره امتحان کنید ❗")


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
