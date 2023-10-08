import os

import telebot

BOT_TOKEN = os.environ.get('BOT_TOKEN')

bot = telebot.TeleBot(BOT_TOKEN)
bot.set_webhook()

@bot.message_handler(commands=['start','hello'])
def send_welcome(message):
    bot.reply_to(message,"hello this is a test for first command")


@bot.message_handler(func=lambda msg:True)
def echo_all(message):
    bot.reply_to(message,message.text)

bot.infinity_polling()