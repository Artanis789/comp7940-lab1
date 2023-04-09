from telegram.ext import (Application, CommandHandler, MessageHandler,
                          filters, ContextTypes)
from telegram import Update
import openai
import mysql.connector
import os
import logging
import time
import redis
import json
import requests
from wrapt_timeout_decorator import *

db_config = {
    'host': os.environ['DB_HOST'],
    'user': os.environ['DB_USER'],
    'password': os.environ['DB_PWD'],
    'port': os.environ['DB_PORT']
}

redis1 = redis.Redis(host=os.environ['REDIS_HOST'],
                     password=os.environ['REDIS_PASSWORD'],
                     port=os.environ['REDIS_PORT'])


def select_all(sql) -> list:
    logging.info(sql)
    db = mysql.connector.connect(**db_config)
    cursor = db.cursor()
    cursor.execute(sql)
    rows = cursor.fetchall()
    cursor.close()
    db.close()
    return rows


def select_one(sql):
    logging.info(sql)
    db = mysql.connector.connect(**db_config)
    cursor = db.cursor()
    cursor.execute(sql)
    row = cursor.fetchone()
    cursor.close()
    db.close()
    return row


def execute_sql(sql) -> None:
    logging.info(sql)
    db = mysql.connector.connect(**db_config)
    cursor = db.cursor()
    cursor.execute(sql)
    db.commit()
    cursor.close()
    db.close()


def init_database():
    logging.info("init database")
    while True:
        try:
            time.sleep(2)
            db = mysql.connector.connect(**db_config)
            break
        except Exception as e:
            logging.info("MySQL is not activate yet, try reconnect.")

    execute_sql(f"CREATE DATABASE IF NOT EXISTS {os.environ['DATABASE']};")

    db_config["database"] = os.environ['DATABASE']

    logging.info(db_config)

    execute_sql("DROP TABLE IF EXISTS images;")

    execute_sql(
        "CREATE TABLE images (id serial PRIMARY KEY, prompt VARCHAR(255), image VARCHAR(255));")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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
        "/image_del: Delete an image record from database"

    logging.info("help command")
    await update.message.reply_text(help_message)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logging.info("start command")

    context_json = json.dumps(
        [{"role": "system", "content": "You are a helpful chatbot"}])
    redis1.set("context", context_json)
    await update.message.reply_text("Hello, what can I do for you?")


async def end(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logging.info("end command")
    redis1.delete("context")
    await update.message.reply_text("Good bye~~")

@timeout(90)
def make_request(messages) -> str:
    response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=messages
        )
    result = response.choices[0].message.content
    return result


def chat_completion(msg) -> str:
    data = redis1.get('context')
    if data:
        context = json.loads(data)
        assert isinstance(context, list)

        context.append({"role": "user", "content": msg})
        logging.info(f'Using context, context:\n{context}')

        result = make_request(context)

        context.append({"role": "assistant",
                        "content": result})

        redis1.set('context', json.dumps(context))

        result += '\n\n\nYou are chat me with a context, please remember to use /end command to stop the conversation.'
    else:
        logging.info("Not using context.")
        messages = [{"role": "user", "content": msg}]
        result = make_request(messages)
    return result


async def gpt_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        msg = update.message.text
        logging.info(msg)
        start = time.time()
        result = chat_completion(msg)
        logging.info(f"Request cost {time.time() - start}seconds")
        await update.message.reply_text(result)

    except BaseException as e:
        logging.info(e)
        await update.message.reply_text(
            f"Something wrong with chatbot, please retry!")


async def image(prompt) -> str:
    response = openai.Image.create(
        prompt=prompt,
        n=1,
        size="1024x1024"
    )
    image_url = response['data'][0]['url']
    return image_url


async def download_img(url):
    rsp = requests.get(url)
    img = rsp.content
    rsp.close()
    return img


async def save_image(prompt: str, img: bytes):
    file_name = f"{prompt.replace(' ', '_')}.jpg"
    with open(f'/images/{file_name}', 'wb') as f:
        f.write(img)

    sql = f'INSERT INTO images (prompt, image) VALUES ("{prompt}", "{file_name}");'
    execute_sql(sql)


async def image_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Please enter a prompt")
        return
    try:
        prompt = " ".join(context.args)
        logging.info(prompt)
        start = time.time()
        image_url = await image(prompt)
        logging.info(f"Request cost {time.time() - start}seconds")
        img = await download_img(image_url)
        await save_image(prompt, img)
        await update.message.reply_photo(
            img, caption="Here is the picture generating for you. I already save it in database, you can type /image_log to ckeck the history.\n")

    except Exception as e:
        logging.info(str(e))
        await update.message.reply_text(
            f"Something wrong with chatbot, please retry!")


async def image_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        sql = f'select * from images;'

        imgs = select_all(sql)

        result = 'Here are the image records:\n'
        for i, img in enumerate(imgs, start=1):
            result += f'{i}. {img[1]}\n'
        result += "\n\nYou can use /image_review command to check an image record."
        await update.message.reply_text(result)
    except Exception as e:
        logging.info(e)
        await update.message.reply_text("Something wrong with database!")


async def image_review(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 1:
        await update.message.reply_text("Please Enter the id of an image record!")
        return
    id = context.args[0]
    if not id.isdigit():
        await update.message.reply_text(
            "To review an image, please enter the id of it, use /image_log command to check the id.")
        return
    id = int(id)
    sql = f'SELECT * FROM images WHERE id={id};'
    try:
        row = select_one(sql)
    except Exception as e:
        logging.info(e)
        await update.message.reply_text(
            "Something wrong with the database.")

    if row is not None:
        file_name = row[2]
        with open(f'/images/{file_name}', 'rb') as f:
            img = f.read()
        await update.message.reply_photo(
            img, caption="Here is the image you want review.\n")
    else:
        await update.message.reply_text(
            f"I'm sorry, I can't find this record...")


async def image_del(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 1:
        await update.message.reply_text(
            "To delete an image record, please enter the id of it.")
        return

    arg = context.args[0]
    if not arg.isdigit():
        await update.message.reply_text(
            "To delete an image record, please enter the id of it.")
        return
    id = int(arg)
    sql = f'DELETE FROM images WHERE id={id};'

    try:
        execute_sql(sql)
        await update.message.reply_text("Successfully delete an image record!")
    except Exception as e:
        logging.info(e)
        await update.message.reply_text(
            'Failed to delete an item, please try again!')


def main():
    application = Application.builder().token(
        os.environ["ACCESS_TOKEN"]).concurrent_updates(True).build()

    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                        level=logging.INFO)

    init_database()

    application.add_handler(CommandHandler("help", help_command, block=False))
    application.add_handler(CommandHandler("start", start, block=False))
    application.add_handler(CommandHandler("end", end, block=False))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), gpt_reply, block=False))
    application.add_handler(CommandHandler("image", image_reply, block=False))
    application.add_handler(CommandHandler("image_log", image_list, block=False))
    application.add_handler(CommandHandler("image_review", image_review, block=False))
    application.add_handler(CommandHandler("image_del", image_del, block=False))

    # To start the bot:
    application.run_polling()


if __name__ == "__main__":
    main()
