from telegram.ext import (Updater, CommandHandler, MessageHandler,
                          Filters, CallbackContext)
from telegram import Update
import openai
import mysql.connector
import os
import logging
from wrapt_timeout_decorator import *
import time
import redis

db_config = {
    'host': os.environ['DB_HOST'],
    'user': os.environ['DB_USER'],
    'password': os.environ['DB_PWD'],
    'database': os.environ['DATABASE'],
}

redis1 = redis.Redis(host=os.environ['REDIS_HOST'],
                     password=os.environ['REDIS_PASSWORD'],
                     port=os.environ['REDIS_PORT'])


def main():
    updater = Updater(token=(os.environ['ACCESS_TOKEN']), use_context=True)
    dispatcher = updater.dispatcher

    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                        level=logging.INFO)
    logging.info(f"OPENAI_API_KEY={openai.api_key}")

    # register a dispatcher to handle message: here we register an echo dispatcher
    gpt_handler = MessageHandler(Filters.text & (~Filters.command), gpt_reply)

    dispatcher.add_handler(gpt_handler)
    # on different commands - answer in Telegram
    dispatcher.add_handler(CommandHandler("help", help_command))
    dispatcher.add_handler(CommandHandler("cook", cook))
    dispatcher.add_handler(CommandHandler("menu", cook_list))
    dispatcher.add_handler(CommandHandler("menu_add", cook_add))
    dispatcher.add_handler(CommandHandler("menu_del", cook_del))
    dispatcher.add_handler(CommandHandler("menu_update", cook_update))
    dispatcher.add_handler(CommandHandler("image", image_reply))
    dispatcher.add_handler(CommandHandler("image_log", image_list))
    dispatcher.add_handler(CommandHandler("image_clear", image_clear))

    # To start the bot:
    updater.start_polling()
    updater.idle()


def help_command(update: Update, context: CallbackContext) -> None:
    """Send a message when the command /help is issued."""

    help_message = "Hello, I'm a smart chatbot powered by ChatGPT.\n" +\
        "I have prepared some interesting commands for you:\n\n" +\
        "/cook: Enter the name of the dish you are interested in, I'll give you a video.\n\n" +\
        "/menu: list the menu.\n\n" +\
        "/menu_add: Enter the name and the video site of the dish to add new item to the menu.\n" +\
        "Example: /menu_add 鱼香肉丝 https://www.cook-video/example\n\n" +\
        "/menu_del: Enter the name of the dish to delete it from the menu.\n" +\
        "Example: /menu_del 鱼香肉丝\n\n" +\
        "/menu_update: Enter the name and a new url to update a dish.\n" +\
        "Example: /menu_update 鱼香肉丝 https://www.new-cook-video/example\n\n" +\
        "/image: Enter a prompt, I can generate a realistic image for you\n" +\
        "Example: /image a lovely cat\n\n" +\
        "/image_log: list the history of generated images.\n\n" +\
        "/image_clear: clear all records!"

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
    for i, row in enumerate(rows, start=1):
        result += f'{i}. {row[1]}\n'

    update.message.reply_text(result)


def cook_add(update: Update, context: CallbackContext):
    if len(context.args) < 2:
        update.message.reply_text(
            "To add new item, please enter name and url of the video.")
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
            update.message.reply_text(
                'Failed to add new item to menu, please try again')


def cook_del(update: Update, context: CallbackContext):
    if len(context.args) < 1:
        update.message.reply_text(
            "To delete an item, please enter the name of it.")
    else:
        name = context.args[0]
        sql = f'DELETE FROM cooking_list WHERE name="{name}";'
        logging.info(f'\n{sql}')

        db = mysql.connector.connect(**db_config)
        cursor = db.cursor()
        try:
            cursor.execute(sql)
            db.commit()
            cursor.close()
            db.close()
            update.message.reply_text("Successfully delete an item from menu!")
        except Exception as e:
            logging.debug(e)
            update.message.reply_text(
                'Failed to delete an item, please try again!')


def cook_update(update: Update, context: CallbackContext):
    if len(context.args) < 2:
        update.message.reply_text(
            "To update an item, please enter the name of the item and a new url.")
    else:
        name = context.args[0]
        url = context.args[1]
        sql = f'UPDATE cooking_list SET url = "{url}" WHERE name = "{name}";'
        logging.info(f'\n{sql}')

        db = mysql.connector.connect(**db_config)
        cursor = db.cursor()
        try:
            cursor.execute(sql)
            db.commit()
            cursor.close()
            db.close()
            update.message.reply_text("Successfully update an item from menu!")
        except Exception as e:
            logging.debug(e)
            update.message.reply_text(
                'Failed to update an item, please try again!')


@timeout(60)
def chat(msg):
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "user", "content": msg},
        ]
    )
    return response


def gpt_reply(update: Update, context: CallbackContext):
    try:
        msg = update.message.text
        logging.info(msg)
        start = time.time()
        response = chat(msg)
        logging.info(f"Request cost {time.time() - start}seconds")
        result = ""
        for choice in response.choices:
            result += choice.message.content
        update.message.reply_text(result)

    except Exception as e:
        logging.info(str(e))
        update.message.reply_text(
            f"Something wrong with chatbot, please retry!")


@timeout(60)
def image(prompt):
    response = openai.Image.create(
        prompt=prompt,
        n=1,
        size="1024x1024"
    )
    image_url = response['data'][0]['url']
    return image_url


def save_image(name: str, url: str):
    redis1.set(name, url)


def image_reply(update: Update, context: CallbackContext):
    try:
        prompt = " ".join(context.args)
        logging.info(prompt)
        start = time.time()
        image_url = image(prompt)
        logging.info(f"Request cost {time.time() - start}seconds")
        save_image(prompt, image_url)
        update.message.reply_text(
            f'Here is the url of generated image:\n{image_url}')

    except Exception as e:
        logging.info(str(e))
        update.message.reply_text(
            f"Something wrong with chatbot, please retry!")


def image_list(update: Update, context: CallbackContext):
    imgs = redis1.keys()
    result = 'Here are the image records:\n'
    for i, name in enumerate(imgs, start=1):
        result += f'{name.decode("utf-8")}\n'
        result += f'{redis1.get(name).decode("utf-8")}\n\n\n'

    update.message.reply_text(result)


def image_clear(update: Update, context: CallbackContext):
    redis1.flushdb()
    update.message.reply_text("Successfully clear all records!")


if __name__ == "__main__":
    main()
