from telegram.ext import (Updater, CommandHandler, MessageHandler,
                          Filters, CallbackContext)
from telegram import Update
import openai
import os
import logging
import redis
global redis1


def main():
    openai.api_key = os.environ['GPT_API']
    updater = Updater(token=(os.environ['ACCESS_TOKEN']), use_context=True)
    dispatcher = updater.dispatcher

    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                        level=logging.INFO)
    logging.info(f"API-KEY = {os.environ['GPT_API']}")
    global redis1
    redis1 = redis.Redis(host=os.environ['REDIS_HOST'],
                         password=os.environ['REDIS_PASSWORD'],
                         port=os.environ['REDIS_PORT'])

    # register a dispatcher to handle message: here we register an echo dispatcher
    echo_handler = MessageHandler(Filters.text & (~Filters.command), echo)

    dispatcher.add_handler(echo_handler)
    # on different commands - answer in Telegram
    dispatcher.add_handler(CommandHandler("help", help_command))
    dispatcher.add_handler(CommandHandler("ai", gpt_reply))

    # To start the bot:
    updater.start_polling()
    updater.idle()


def echo(update: Update, context: CallbackContext):
    reply_message = update.message.text.upper()
    logging.info("Update: " + str(update))
    logging.info("context: " + str(context))
    context.bot.send_message(
        chat_id=update.effective_chat.id, text=reply_message)

# Define a few command handlers. These usually take the two arguments update and
# context. Error handlers also receive the raised TelegramError object in error.
def help_command(update: Update, context: CallbackContext) -> None:
    """Send a message when the command /help is issued."""
    update.message.reply_text('Helping you helping you.')


def gpt_reply(update: Update, context: CallbackContext):
    try:
        msg = " ".join(context.args) 
        logging.info(msg)

        response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
                {"role": "user", "content": msg},
            ]
        )
        result = ""
        for choice in response.choices:
            result += choice.message.content
        update.message.reply_text(result)
        
    except Exception as e:
        logging.debug(str(e))
        update.message.reply_text("Something wrong with chatgpt!")


if __name__ == "__main__":
    main()
