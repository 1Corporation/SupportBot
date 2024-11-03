import os
import datetime
from typing import Optional

from aiogram import F
from aiogram.types import Message
from dotenv import load_dotenv

from bot.dispatcher import dp
from utils import DatabaseConnection

# in this module use .env vars, load it
load_dotenv()

# consts
SECONDS_IN_DAY = 86400
SECONDS_IN_HOUR = 3600


# this handler work in admin chat only
@dp.message("profile", F.chat.id == int(os.getenv("CHAT_ID")))
async def profile_command_handler(message: Message):
    await __send_profile_message(message)


def __get_helper_id(message: Message) -> Optional[int]:
    """

    :param message: aiogram Message object
    :return: Optional[int] ID помощника, или если не получилось получить None
    """

    # Получаем id человека, чью статистику мы хотим увидеть
    if len(message.text) == 2:
        # Если команда вызвана с аргументом, проверим валиден ли переданный юзер айди
        try:
            helper_id = int(message.text.split()[1])
        except ValueError:
            return

    else:
        # Если команда вызвана без аргументов, показываем статистику автора команды.
        helper_id = message.from_user.id

    return helper_id


async def __send_profile_message(message: Message) -> None:
    """
    Создание такого сообщения это очень большой и страшный процесс, поэтому я сливаю его в отдельную функцию
    :param message: aiogram Message object
    :return: None
    """

    helper_id = __get_helper_id(message)

    # Если нету helper_id, остановим функцию
    if not helper_id:
        await message.reply("Вы ввели недопустимый userId в аргументы команды! \
         \n\n Чтобы видеть userId's людей, используйте: "
                            "Settings -> Advanced -> Experimental Settings -> Show Peer IDs in Profile")
        return

    # Высчитываю границы в которых нужно будет искать действия помощника
    day_started_at = datetime.datetime.now().replace(hour=0, minute=0, second=0).timestamp()
    # day_ended_at = day_started_at + SECONDS_IN_DAY  # Может понадобиться в будущем

    connect = DatabaseConnection().connect
    cursor = await connect.cursor()

    # Получаем нужные значения из базы данных
    list_of_tickets = await (await cursor.execute(
        "SELECT (tickets_author_id, start_time, end_time) \
        FROM tickets WHERE helper_id = ? AND start_time > ? \
        ORDER BY start_time", (
            helper_id, day_started_at))).fetchall()

    list_of_messages = await (await cursor.execute(
        "SELECT (time_at) FROM messages \
        WHERE helper_id = ? AND time_at = ? \
        ORDER BY time_at", (
            helper_id, day_started_at))).fetchall()

    # Проверим, а есть ли данные по этому помощнику
    if len(list_of_tickets) == 0:
        await message.reply("Не найдено данных по этому помощнику")
        return

    # Эта строка отправится в сообщении
    message_string = f"Статистика помощника {helper_id} за {datetime.datetime.now().date()}: \n\n"

    amount_of_opened_tickets = len(list_of_tickets)
    amount_of_closed_tickets = len([ticket for ticket in list_of_tickets if ticket[2] is not None])
    amount_of_messages = len(list_of_messages)

    message_string += f"Открыто тикетов: {amount_of_opened_tickets} \
        \nЗакрыто тикетов: {amount_of_closed_tickets} \
        \nОтправлено сообщений в поддержку: {amount_of_messages}\n\n"

    current_hour = 10  # В 10 часов начинается рабочий день
    end_of_work_day = 21

    for message in list_of_messages:
        hour_of_message = message // 3600

        # Если до первого сообщения не было других, проставляем на все часы до этого красный цвет
        if hour_of_message > current_hour:
            while hour_of_message > current_hour:
                message_string += f"🔴 {current_hour}:00 🔴\n"
                current_hour += 1

        # если в этот час было сообщение, ставим зеленую галочку
        if hour_of_message == current_hour:
            message_string += f"🟢 {current_hour}:00 🟢\n"
            current_hour += 1

    # Если остались часы до конца рабочего дня, добавим красных
    while current_hour < end_of_work_day + 1:
        message_string += f"🔴 {current_hour}:00 🔴\n"
        current_hour += 1

    await message.reply(message_string)
