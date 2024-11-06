import asyncio
import logging
import os

from dotenv import load_dotenv
from aiogram import Bot

from bot.dispatcher import dp
from utils import DatabaseConnection


load_dotenv()


def set_loggers() -> None:
    """
    Устанавливает логгеры и логхендлеры
    :return: None
    """
    file_log = logging.FileHandler('Log.log')
    console_out = logging.StreamHandler()

    logging.basicConfig(handlers=(file_log, console_out),
                        format='[%(asctime)s | %(levelname)s]: %(message)s',
                        datefmt='%m.%d.%Y %H:%M:%S',
                        level=logging.DEBUG)


async def main():
    set_loggers()
    telegram_bot = Bot(os.getenv("BOT_TOKEN"))
    await DatabaseConnection().get_connection()
    import bot.handlers  # load handlers
    await dp.start_polling(telegram_bot)


if __name__ == '__main__':
    asyncio.run(main())
