from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, Update
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, MessageHandler, Filters, CallbackContext

import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
required_channel_id = '@feghtesad'


def start(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    welcome_text = "سلام خوش اومدی به ماینربات برای استفاده از ربات لطفا عضو کانال زیر شو"

    # Create inline keyboard
    keyboard = [
        [InlineKeyboardButton("Join Channel", url="https://t.me/feghtesad"),
         InlineKeyboardButton("Check Channel", callback_data="check_channel")]
    ]

    # Send the message with inline keyboard
    context.bot.send_message(chat_id=user_id, text=welcome_text,
                             reply_markup=InlineKeyboardMarkup(keyboard))


def stop(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    # Implement logic to stop sending updates to this user
    # You might want to remove the user from a database or update a setting
    context.bot.send_message(
        chat_id=user_id, text="You have unsubscribed from the bot. If you want to receive updates again, use /start.")


def callback_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    user_id = query.from_user.id

    if query.data == 'check_channel':
        # Check if the user is a member of the required channel
        is_member = context.bot.get_chat_member(
            required_channel_id, user_id).status in ['member', 'administrator']
        if is_member:
            # Create keyboard directly without embedding it in a list
            keyboard = ReplyKeyboardMarkup(
                [["دستگاه : BTCLN 21M", "دستگاه : BTCLN21M PRO"]])

            context.bot.send_message(
                chat_id=user_id, text="چه کاری میتونم برات انجام بدم؟", reply_markup=keyboard)
        else:
            context.bot.send_message(user_id, "شما عضو کانال نیستید!")


def handle_messages(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id

    if update.message.text == "دستگاه : BTCLN 21M":
        # Sub-menu 1
        context.bot.send_message(
            chat_id=user_id, text="مشخصات دستگاه\nمدل BTCLN 21M\nحافظه RM4\nپردازنده 4 هسته 1.5GHz 64 BT\nپشتیبانی از کابل شبکه و وایرلس\nدارای دو پورت usb3 و usb2\nدارای دو کانال خروجی مالی\nپشتیبانی از کابل HDMI\nساخت کشور چین")
    elif update.message.text == "دستگاه : BTCLN21M PRO":
        # Sub-menu 2
        context.bot.send_message(
            chat_id=user_id, text="مدل دستگاه BTCLN21M PRO\nRam 8 to finally\nپردازنده ۵ هسته 1.8GHz 64 BIT\nOverclock\nدارای ۲ پورت USB3\nدارای ۲ پورت USB2\nدارای پورت HDMI\nساخت کشور چین")
    else:
        context.bot.send_message(
            chat_id=user_id, text="I don't understand that command. Please use the provided buttons.")


def main():
    updater = Updater(TOKEN)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("stop", stop))
    dp.add_handler(CallbackQueryHandler(callback_handler))
    dp.add_handler(MessageHandler(Filters.text & ~
                   Filters.command, handle_messages))

    updater.start_polling()
    updater.idle()


if __name__ == "__main__":
    main()
