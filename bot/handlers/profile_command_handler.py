import os

from aiogram import F
from aiogram.types import Message
from dotenv import load_dotenv

from bot.dispatcher import dp

# in this module use .env vars, load it
load_dotenv()


# this handler work in admin chat only
@dp.message("profile", F.chat.id == int(os.getenv("CHAT_ID")))
async def profile_command_handler(message: Message):
    pass
