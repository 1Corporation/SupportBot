import os

from aiogram import F
from aiogram.types import Message
from aiogram.filters import Command

from bot.dispatcher import dp
from utils import DatabaseConnection


@dp.message(Command("set_nickname"), F.chat.id == int(os.getenv("CHAT_ID")))
async def set_nickname_handler(message: Message) -> None:
    """
    Меняет full_name помощника в базе данных на новый
    :param message: aiogram Message object
    :return: None
    """

    helper_id = message.from_user.id
    full_name = " ".join(message.text.split()[1:])  # получим fullname

    connect = DatabaseConnection().connect
    await connect.execute("""
    INSERT INTO helpers (user_id, full_name) VALUES (?, ?)
    ON CONFLICT (user_id)
    DO UPDATE SET
        full_name = excluded.full_name
    """, helper_id, full_name)

    await connect.commit()
