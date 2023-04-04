## chatbot.py
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
import configparser
import logging
import os
import openai
import redis
global redis1


def main():
# Load your token and create an Updater for your Bot
    config = configparser.ConfigParser()
    config.read('config.ini')

    openai.api_key = config['CHATGPT']["API"]

    updater = Updater(token=(config['TELEGRAM']['ACCESS_TOKEN']), use_context=True)
    dispatcher = updater.dispatcher

    global redis1
    redis1 = redis.Redis(host=(config['REDIS']['HOST']), password=(config['REDIS']['PASSWORD']), port=(config['REDIS']['REDISPORT']))
# You can set this logging module, so you will know when and why things do not work as expected
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO)
# register a dispatcher to handle message: here we register an echo dispatcher
    echo_handler = MessageHandler(Filters.text & (~Filters.command), echo)
    dispatcher.add_handler(echo_handler)
# on different commands - answer in Telegram
    dispatcher.add_handler(CommandHandler("add", add))
    dispatcher.add_handler(CommandHandler("help", help_command))
    dispatcher.add_handler(CommandHandler("hello", hello_Kevin))
    dispatcher.add_handler(CommandHandler("ai", gpt_reply))

# To start the bot:
    updater.start_polling()
    updater.idle()
def echo(update, context):
    reply_message = update.message.text.upper()
    logging.info("Update: " + str(update))
    logging.info("context: " + str(context))
    context.bot.send_message(chat_id=update.effective_chat.id, text= reply_message)

# Define a few command handlers. These usually take the two arguments update and
# context. Error handlers also receive the raised TelegramError object in error.
def help_command(update: Update, context: CallbackContext) -> None:
    """Send a message when the command /help is issued."""
    update.message.reply_text('Helping you helping you.')
def add(update: Update, context: CallbackContext) -> None:
    """Send a message when the command /add is issued."""
    try:
        global redis1
        logging.info(context.args[0])
        msg = context.args[0] # /add keyword <-- this should store the keyword
        redis1.incr(msg)
        update.message.reply_text('You have said ' + msg + ' for ' + redis1.get(msg).decode('UTF-8') + ' times.')
    except (IndexError, ValueError):
        update.message.reply_text('Usage: /add <keyword>')

def hello_Kevin(update: Update, context: CallbackContext) -> None:
    """Send a message when the command /hello is issued."""
    try:
        global redis1
        logging.info(context.args[0])
        msg = context.args[0] # /add keyword <-- this should store the keyword
        redis1.incr(msg)
        update.message.reply_text('Good day,' + msg + '!')
    except (IndexError, ValueError):
        update.message.reply_text('Usage: /hello <keyword>')

def gpt_reply(update: Update, context: CallbackContext):
    try:
        msg = " ".join(context.args) 
        logging.info(msg)

        response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
                {"role": "system", "content": "You are a chatbot"},
                {"role": "user", "content": msg},
            ]
        )

        result = ""
        for choice in response.choices:
            result += choice.message.content
        update.message.reply_text(result)
        
    except Exception as e:
        logging.info(str(e))

if __name__ == '__main__':
    main()

import os
def main():
    updater = Updater(token=(os.environ['ACCESS_TOKEN']),use_context=True)
    dispatcher = updater.dispatcher

    global redisl
    redisl = redis.Redis(host=(os.environ['HOST']),password=(os.environ['PASSWORD']),port=(os.environ['REDISPORT']))

    openai.api_key(host=(os.environ['API']))
    