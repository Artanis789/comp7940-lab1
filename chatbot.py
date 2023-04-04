from telegram.ext import (Updater, CommandHandler, MessageHandler,
                          Filters, CallbackContext)
from telegram import Update
import openai
import mysql.connector
import os
import logging

db_config = {
    'host': os.environ['DB_HOST'],
    'user': os.environ['DB_USER'],
    'password': os.environ['DB_PWD'],
    'database': os.environ['DATABASE'],
}


def main():
    openai.api_key = os.environ['GPT_API']
    updater = Updater(token=(os.environ['ACCESS_TOKEN']), use_context=True)
    dispatcher = updater.dispatcher

    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                        level=logging.INFO)
    logging.info(f"API-KEY = {os.environ['GPT_API']}")

    # register a dispatcher to handle message: here we register an echo dispatcher
    echo_handler = MessageHandler(Filters.text & (~Filters.command), echo)

    dispatcher.add_handler(echo_handler)
    # on different commands - answer in Telegram
    dispatcher.add_handler(CommandHandler("help", help_command))
    dispatcher.add_handler(CommandHandler("cook", cook))
    dispatcher.add_handler(CommandHandler("list", cook_list))
    dispatcher.add_handler(CommandHandler("add", cook_add))
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

    help_message = "Hello, I'm a smart chatbot powered by ChatGPT, You can talk to me about anything.\n" +\
        "I also prepare some interesting commands for you to learn how to cook:\n\n" +\
        "/cook: Enter the name of the dish you are interested in, I'll give you a video.\n\n" +\
        "/list: list the menu.\n\n" +\
        "/add: Enter the name and the video site of the dish to add new item to the menu.\n" +\
        "Example: /add 鱼香肉丝 https://www.bilibili.com/video/BV1KT4y1Y78z/"

    update.message.reply_text(help_message)


def cook(update: Update, context: CallbackContext) -> None:
    cook_name = context.args[0]
    db = mysql.connector.connect(**db_config)
    cursor = db.cursor()
    cursor.execute(f'SELECT * FROM cooking_list WHERE name="{cook_name}";')
    logging.info(f'SELECT * FROM cooking_list WHERE name="{cook_name}";')
    row = cursor.fetchone()
    cursor.close()
    db.close()
    if row is not None:
        update.message.reply_text(
            f"You can go to {row[-1]} to learn how to cook {cook_name}.")
    else:
        update.message.reply_text(
            f"I'm sorry, I don't know how to cook {cook_name}...")

def cook_list(update: Update, context: CallbackContext) -> None:
    db = mysql.connector.connect(**db_config)
    cursor = db.cursor()
    cursor.execute('SELECT * FROM cooking_list;')
    rows = cursor.fetchall()
    cursor.close()
    db.close()

    result = 'Here is the menu:\n'
    for row in rows:
        result += f'{row[0]}. {row[1]}\n'

    update.message.reply_text(result)

def cook_add(update: Update, context: CallbackContext):
    if len(context.args) < 2:
        update.message.reply_text("To add new item, please enter name and url of the video.")
    else:
        name = context.args[0]
        url = context.args[1]
        sql = f'INSERT INTO cooking_list (name, url) VALUES ("{name}", "{url}");'
        logging.info(f'\n{sql}')

        db = mysql.connector.connect(**db_config)
        cursor = db.cursor()
        try:
            cursor.execute(sql)
            db.commit()
            cursor.close()
            db.close()
            update.message.reply_text("Successfully add a new item to menu!")
        except Exception as e:
            logging.debug(e)
            update.message.reply_text('Fail to add new item to menu, please try again')


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
