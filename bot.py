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
            # define main keyboard buttons
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
        faq_text = """- دستگاه  BTCLN 21 M PRO ماهانه بین ۵.۵ تا ۶.۵ میلیون تومان درآمد دارد که درامد خود را میتوانید از بین ۶ رمزارز  BTC , LTC , ETH , MATIC , DOGE , TRX, انتخاب کنید که چه ارزی را تحت عنوان درامد دریافت کنید. همچنین این قابلیت وجود دارد که بعد از هر برداشت رمز ارز انتخابی خود را تغییر دهید. 

    - با توجه به فعالیت اخیر دستگاه درآمد شما ارتباط زیادی با کوین انتخابی شما دارد و در شرایط فعلی بازار کوین MATIC بازدهی بیشتری داشته است ."""
        context.bot.send_message(chat_id=user_id, text=faq_text)
    elif query.data == 'income2':
        faq_text = """- دستگاه دو کانال ماهانه بین ۳.۵ تا ۴.۵ میلیون تومان درآمد دارد که درامد خود را میتوانید از بین 8 رمزارز  BTC , LTC , ETH , MATIC , DOGE , TRX, انتخاب کنید که چه ارزی را تحت عنوان درامد دریافت کنید. همچنین این قابلیت وجود دارد که بعد از هر برداشت رمز ارز انتخابی خود را تغییر دهید.
        
        - با توجه به فعالیت اخیر دستگاه درآمد شما ارتباط زیادی با کوین انتخابی شما دارد و در شرایط فعلی بازار کوین MATIC بازدهی بیشتری داشته است ."""
        context.bot.send_message(chat_id=user_id, text=faq_text)

    elif query.data == 'income3':
        faq_text = """درآمد دستگاه\nدرامد این دستگاه ماهانه 333 تا 344 دلار می باشد.\nدرامد ماهیانه به تومان: تقریبا ۱۸ میلیون تومان\nپرداخت به صورت هر 9 روز و به مبلغ 100 دلار می باشد.\nحالت پرداخت درآمد به صورت یکی از ده ارز زیر و به صورت انتخابی خودتان می باشد:\nBTC\nETH\nLTC\nSOL\nDOT\nTRX\nMATIC\nAVAX\nXRP\nDOGE"""    
        context.bot.send_message(chat_id=user_id, text=faq_text)

    elif query.data == "power_internet":
        faq_text = """- مصرف برق دستگاه ۱۰۰ وات که معادل یک لامپ ۱۰۰ می‌باشد و با یک آداپتور تایپ سی ۵ ولت ۳ آمپر تغذیه می‌شود .
        - با توجه به مصرف برق پایین دستگاه،  هیچگونه محدودیتی بابت استفاده برق خانگی در منزل وجود ندارد .
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
        faq_text = """_ تمامی دستگاه ها توسط فروشگاه دارای ۱۲ ماه گارانتی سخت افزاری و نرم افزاری می‌باشد .

  _ در تمامی مراحل راه اندازی دستگاه ، کارشناسان ما کنار شما خواهند بود و چنانچه دستگاه  مشکل فنی و راه اندازی داشته باشد، دستگاه کاملا تعویض میگردد و تمامی هزینه ها به عهده فروشگاه می‌باشد."""
        context.bot.send_message(chat_id=user_id, text=faq_text)

    elif query.data == "order_delivery1":
        faq_text = """قیمت دستگاه دو کانال 
        990$ \n""" + orderDelivery
        context.bot.send_message(chat_id=user_id, text=faq_text)
    elif query.data == "order_delivery2":
        faq_text = """قیمت دستگاه چهار کانال PRO
        موجود نیست \n""" + orderDelivery
        context.bot.send_message(chat_id=user_id, text=faq_text)
    elif query.data == "order_delivery3":
        faq_text = """قیمت دستگاه شش کانال
        4600$ \n""" + orderDelivery
        context.bot.send_message(chat_id=user_id, text=faq_text)


def handle_messages(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    keyboard = [
        [InlineKeyboardButton(
            "مصرف برق و اینترنت دستگاه 💡", callback_data="power_internet")],
        [InlineKeyboardButton(
            "ابزار لازم برای راه اندازی دستگاه 🛠", callback_data="tools")
         ],
        [InlineKeyboardButton(
            "نحوه راه‌ اندازی و نگهداری دستگاه 🔧", callback_data="setup_maintenance")],
        [InlineKeyboardButton("گارانتی دستگاه 🔒", callback_data="warranty")],

    ]

    if update.message.text == "مدل چهار کانال 🚀":
        faq_text = """Ram 8 to finally
        پردازنده ۵ هسته 1.8GHz 64 BIT
        Overclock
        دارای ۲ پورت USB3
        دارای ۲ پورت USB2
        دارای پورت HDMI
        ساخت کشور چین"""

        incomeButton1 = InlineKeyboardButton(
            "درآمد دستگاه 💰", callback_data="income1")
        orderDeliveryButton = InlineKeyboardButton(
            "نحوه اطلاع از قیمت ، ثبت سفارش و تحویل دستگاه 💵", callback_data="order_delivery2")
        keyboard.append([orderDeliveryButton, incomeButton1])
        # local_photo_path = 'asset/four-channels.jpg'
        # context.bot.send_photo(chat_id=user_id, photo=open(
        #     local_photo_path, 'rb'))

        context.bot.send_message(
            chat_id=user_id, text=faq_text, reply_markup=InlineKeyboardMarkup(keyboard))

    elif update.message.text == "مدل دو کانال 🚀":
        faq_text = """مدل دو کانال 
        حافظه RM4
        پردازنده 4 هسته 1.5GHz 64 BT
        پشتیبانی از کابل شبکه و وایرلس
        دارای دو پورت usb3 و usb2
        دارای دو کانال خروجی مالی 
        پشتیبانی از کابل HDMI
        ساخت کشور چین"""

        incomeButton2 = InlineKeyboardButton(
            "درآمد دستگاه 💰", callback_data="income2")
        orderDeliveryButton = InlineKeyboardButton(
            "نحوه اطلاع از قیمت ، ثبت سفارش و تحویل دستگاه 💵", callback_data="order_delivery1")
        keyboard.append([orderDeliveryButton, incomeButton2])
        local_photo_path = 'asset/two-channels.jpg'
        context.bot.send_photo(chat_id=user_id, photo=open(
            local_photo_path, 'rb'))

        context.bot.send_message(
            chat_id=user_id, text=faq_text, reply_markup=InlineKeyboardMarkup(keyboard))

    elif update.message.text == "مدل شش کانال 🚀":
        faq_text = """از لحاظ سخت افزار ، کاملا قدرتمند و ماندگار هست‌ .

        مصرف برق دستگاه فوق نصف مصرف لپ تاپ هست و فقط با اتصال کابل شبکه به اینترنت متصل میشود.

        پردازنده 5 هسته ای
        رم 8
        128 گیگ حافظه ssd
        متصل به BTC pay server
        6 خروجی کانال تائید تراکنش 
        پورت hdmi
        پورت vga
        4 خروجی usb3
        اتصال خودکار به BTC Core"""

        incomeButton3 = InlineKeyboardButton(
            "درآمد دستگاه 💰", callback_data="income3")
        orderDeliveryButton = InlineKeyboardButton(
            "نحوه اطلاع از قیمت ، ثبت سفارش و تحویل دستگاه 💵", callback_data="order_delivery3")
        keyboard.append([orderDeliveryButton,incomeButton3])
        local_photo_path = 'asset/six-channels.jpg'
        context.bot.send_photo(chat_id=user_id, photo=open(
            local_photo_path, 'rb'))

        context.bot.send_message(
            chat_id=user_id, text=faq_text, reply_markup=InlineKeyboardMarkup(keyboard))

    elif update.message.text == "اخذ نمایندگی 👨‍💼":
        faq_text = """اعطای نمایندگی : 

        🎯 چگونه به شبکه بزرگ فروش بازرگانی اهورا بپیوندیم؟!

        ✅ اخذ نمایندگی کل استان و یا شهرستان: 

        اشخاصی که در عرصه کسب و کار ، فعال می باشند در جستجوی این هستند که از رقیبان خود سبقت بگیرند تا بتوانند محصولات با کیفیت و خدمات بهتری را عرضه کنند.

        اخذ نمایندگی انحصاری و معتبر همیشه در اولویت قرار دارد، اخذ نمایندگی برندهای معتبر و اخذ نمایندگی انحصاری کار آسانی نمی باشد.

        در زمان های گذشته می توانستید به راحتی از برندهای معتبر نمایندگی بگیرید ولی اکنون باید مذاکره های پیچیده و تخصصی داشته باشید تا بتوانید نمایندگی بگیرید.

        نماینده: شخص حقوقی ایرانی که مطابق مفاد دارای قرارداد به عنوان نماینده فروش محصولات آن شرکت در استان یا شهرستان خود است.


        ✅شرایط لازم جهت اخذ نمایندگی بازرگانی اهورا : 

        ۱.داشتن تعهد به بازرگانی اهورا و مشتریان
        ۲.داشتن حداقل امکانات
        ۳.توانایی فروش
        ۴.حفظ ارتباط با مشتری و بازرگانی


        ✅مدارک لازم برای صدور گواهی فعالیت نمایندگی :

        ۱.درخواست کتبی متقاضی دریافت اخذ نمایندگی 
        ۲.تصویر برابر با اصل شناسنامه و کارت ملی
        ۳.ادرس دقیق متقاضی

        ✅ تعهدات نمایندگی
        ۱. کلیه مسئولیت های کالا از زمان تحویل
        ۲.فروش در سریع ترین زمان ممکن
        ۳.پشتیبانی از محصولات
        ۴.همکاری با کارشناسان فروش و ارائه گزارشات لازم

        ✅روش فروش کالا
        نمایندگی میتواند با استفاده از روش های زیر کالا را به فروش برساند

        ۱.بازاریابی مدرن
        ۲.فروش در فضای مجازی
        ۳.فروش در بازار های محلی"""
        context.bot.send_message(chat_id=user_id, text=faq_text)

    elif update.message.text == "ارتباط با ما 📧":
        context.bot.send_message(
            chat_id=user_id, text="@Ahouraadmin01 \n @Seagroup01 ادمین های ما \n")

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
