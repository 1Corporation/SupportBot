import os
import logging

from aiogram import F
from aiogram.types import Message
from dotenv import load_dotenv

from bot.dispatcher import dp
from bot.routers.TicketsRouter import TicketsRouter

# in this module use .env vars, load it
load_dotenv()


# this handler work in admin chat only
@dp.message(F.chat.id == int(os.getenv("CHAT_ID")))
async def main_handler(message: Message):
    logging.debug(
        f"main_handler work now! user - {message.from_user.username}, {message.from_user.full_name}, {message.from_user.id}. No chat info. Handle only CHAT_ID chat.")

    try:
        await TicketsRouter().handle(message)
    except Exception as e:  # TicketsRouter().handle() can raise exceptions. Except this
        await message.reply(
            f"Script raise error <span>{type(e)}</span> with arguments <span>{e.args}</span>. Please report this to developer - @Justiks",
            parse_mode="html")
        raise


logging.info("main_handler.py successful load now")

