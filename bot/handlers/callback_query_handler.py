import logging

from aiogram.types import CallbackQuery

from bot.dispatcher import dp
from bot.routers.CallBackDataRouter import CallBackDataRouter


@dp.callback_query()
async def callback_query_handler(query: CallbackQuery):
    await CallBackDataRouter().handle(query.message, query.data)

logging.info("callback_query_handler.py successful load now")
