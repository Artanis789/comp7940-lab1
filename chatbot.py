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
import json
import requests

db_config = {
    'host': os.environ['DB_HOST'],
    'user': os.environ['DB_USER'],
    'password': os.environ['DB_PWD'],
    'database': os.environ['DATABASE'],
}

redis1 = redis.Redis(host=os.environ['REDIS_HOST'],
                     password=os.environ['REDIS_PASSWORD'],
                     port=os.environ['REDIS_PORT'])


def init_database():
    logging.info("init database")
    db = mysql.connector.connect(**db_config)
    cursor = db.cursor()

    sql = "DROP TABLE IF EXISTS images;"
    logging.info(sql)
    cursor.execute(sql)

    sql = "CREATE TABLE images (id serial PRIMARY KEY, prompt VARCHAR(255), image VARCHAR(255));"
    logging.info(sql)
    cursor.execute(sql)

    db.commit()
    cursor.close()
    db.close()


def main():
    updater = Updater(token=(os.environ['ACCESS_TOKEN']), use_context=True)
    dispatcher = updater.dispatcher

    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                        level=logging.INFO)
    logging.info(f"OPENAI_API_KEY={openai.api_key}")
    init_database()

    # register a dispatcher to handle message: here we register an echo dispatcher
    gpt_handler = MessageHandler(Filters.text & (~Filters.command), gpt_reply)

    dispatcher.add_handler(gpt_handler)
    # on different commands - answer in Telegram
    dispatcher.add_handler(CommandHandler("help", help_command))
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("end", end))
    dispatcher.add_handler(CommandHandler("image", image_reply))
    dispatcher.add_handler(CommandHandler("image_log", image_list))
    dispatcher.add_handler(CommandHandler("image_review", image_review))
    dispatcher.add_handler(CommandHandler("image_del", image_del))

    # To start the bot:
    updater.start_polling()
    updater.idle()


def help_command(update: Update, context: CallbackContext) -> None:
    """Send a message when the command /help is issued."""

    help_message = "Hello, I'm a smart chatbot powered by ChatGPT.\n" +\
        "I have prepared some interesting commands for you:\n\n" +\
        "/start: Start a new conversation with a context\n\n" +\
        "/end: Finish current conversation\n\n" +\
        "/image: Enter a prompt, I can generate a realistic image for you, the image will be saved in the database\n" +\
        "Example: /image a lovely cat\n\n" +\
        "/image_log: List the history of generated images.\n\n" +\
        "/image_review: Enter an id of a image record, you can check the generated image again\n" +\
        "Example: /image_review 4\n\n" +\
        "image_del: Delete an image record from database"

    logging.info("help command")
    update.message.reply_text(help_message)


def start(update: Update, context: CallbackContext) -> None:
    logging.info("start command")

    context_json = json.dumps(
        [{"role": "system", "content": "You are a helpful chatbot"}])
    redis1.set("context", context_json)
    update.message.reply_text("Hello, what can I do for you?")


def end(update: Update, context: CallbackContext) -> None:
    logging.info("end command")
    redis1.delete("context")
    update.message.reply_text("Good bye~~")


@timeout(90)
def chat(msg):
    data = redis1.get('context')
    if data:
        context = json.loads(data)
        assert isinstance(context, list)

        context.append({"role": "user", "content": msg})
        logging.info(f'Using context, context:\n{context}')
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=context
        )
        context.append({"role": "assistant",
                        "content": response.choices[0].message.content})

        logging.info(f'context after response:\n{context}')
        redis1.set('context', json.dumps(context))

        result = response.choices[0].message.content
        result += '\n\n\nYou are chat me with a context, please remember to use /end command to stop the conversation.'
    else:
        logging.info(f'Not using context, message:\n{msg}')
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "user", "content": msg},
            ]
        )
        result = response.choices[0].message.content
    return result


def gpt_reply(update: Update, context: CallbackContext):
    try:
        msg = update.message.text
        start = time.time()
        result = chat(msg)
        logging.info(f"Request cost {time.time() - start}seconds")
        update.message.reply_text(result)

    except Exception as e:
        logging.info(e)
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


def download_img(url):
    rsp = requests.get(url)
    img = rsp.content
    rsp.close()
    return img


def save_image(prompt: str, img: bytes):
    prompt = prompt.replace(' ', '_')
    file_name = f"{prompt}.jpg"
    with open(f'/images/{file_name}', 'wb') as f:
        f.write(img)

    sql = f'INSERT INTO images (prompt, image) VALUES ("{prompt}", "{file_name}");'
    logging.info(sql)
    db = mysql.connector.connect(**db_config)
    cursor = db.cursor()
    cursor.execute(sql)
    db.commit()
    cursor.close()
    db.close()


def image_reply(update: Update, context: CallbackContext):
    if not context.args:
        update.message.reply_text("Please enter a prompt")
        return
    try:
        prompt = " ".join(context.args)
        logging.info(prompt)
        start = time.time()
        image_url = image(prompt)
        logging.info(f"Request cost {time.time() - start}seconds")
        img = download_img(image_url)
        save_image(prompt, img)
        update.message.reply_photo(
            img, caption="Here is the picture generating for you. I already save it in database, you can type /image_log to ckeck the history.\n")

    except Exception as e:
        logging.info(str(e))
        update.message.reply_text(
            f"Something wrong with chatbot, please retry!")


def image_list(update: Update, context: CallbackContext):
    sql = f'select * from images;'
    logging.info(sql)

    db = mysql.connector.connect(**db_config)
    cursor = db.cursor()
    cursor.execute(sql)
    imgs = cursor.fetchall()
    cursor.close()
    db.close()

    result = 'Here are the image records:\n'
    for i, img in enumerate(imgs, start=1):
        result += f'{i}. {img[1]}\n'
    result += "\n\nYou can use /image_review command to check an image record."
    update.message.reply_text(result)


def image_review(update: Update, context: CallbackContext):
    if len(context.args) < 1:
        update.message.reply_text("Please Enter the id of an image record!")
        return
    id = context.args[0]
    if not id.isdigit():
        update.message.reply_text(
            "To review an image, please enter the id of it, use /image_log command to check the id.")
        return
    id = int(id)
    sql = f'SELECT * FROM images WHERE id={id};'
    logging.info(sql)
    try:
        db = mysql.connector.connect(**db_config)
        cursor = db.cursor()
        cursor.execute(sql)

        row = cursor.fetchone()
        cursor.close()
        db.close()
    except Exception as e:
        logging.info(e)
        update.message.reply_text(
            "Something wrong with the database.")

    if row is not None:
        file_name = row[2]
        with open(f'/images/{file_name}', 'rb') as f:
            img = f.read()
        update.message.reply_photo(
            img, caption="Here is the image you want review.\n")
    else:
        update.message.reply_text(
            f"I'm sorry, I can't find this record...")


def image_del(update: Update, context: CallbackContext):
    if len(context.args) < 1:
        update.message.reply_text(
            "To delete an image record, please enter the id of it.")
        return

    arg = context.args[0]
    if not arg.isdigit():
        update.message.reply_text(
            "To delete an image record, please enter the id of it.")
        return
    id = int(arg)
    sql = f'DELETE FROM images WHERE id={id};'

    logging.info(f'\n{sql}')

    db = mysql.connector.connect(**db_config)
    cursor = db.cursor()
    try:
        cursor.execute(sql)
        db.commit()
        cursor.close()
        db.close()
        update.message.reply_text("Successfully delete an image record!")
    except Exception as e:
        logging.debug(e)
        update.message.reply_text(
            'Failed to delete an item, please try again!')


if __name__ == "__main__":
    main()
