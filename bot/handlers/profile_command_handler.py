import os
import io
import datetime
import logging
from typing import Optional
from collections import Counter

from aiogram import F
from aiogram.types import Message
from aiogram.utils.keyboard import InlineKeyboardBuilder, InlineKeyboardButton
from aiogram.types import BufferedInputFile
from aiogram.filters import Command
from dotenv import load_dotenv
from matplotlib import pyplot as plt
import matplotlib.dates as mdates

from bot.dispatcher import dp
from utils import DatabaseConnection

# in this module use .env vars, load it
load_dotenv()

# consts
SECONDS_IN_DAY = 86400
SECONDS_IN_HOUR = 3600


# this handler work in admin chat only
@dp.message(Command("profile"), F.chat.id == int(os.getenv("CHAT_ID")))
async def profile_command_handler(message: Message) -> None:
    """
    Покажет статистику по помощнику за этот день
    :param message: aiogram types Message
    :return: None
    """
    logging.debug("profile_command_handler work now")
    await __send_profile_message(message)


def __get_helper_id(message: Message) -> Optional[int]:
    """

    :param message: aiogram Message object
    :return: Optional[int] ID помощника, или если не получилось получить None
    """

    # Получаем id человека, чью статистику мы хотим увидеть
    if len(message.text.split()) == 2:
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
        "SELECT ticket_author_id, start_time, end_time \
        FROM tickets WHERE helper_id = ? AND start_time > ? \
        ORDER BY start_time", (
            helper_id, day_started_at))).fetchall()

    list_of_messages = await (await cursor.execute(
        "SELECT time_at FROM messages \
        WHERE helper_id = ? AND time_at > ? \
        ORDER BY time_at", (
            helper_id, day_started_at))).fetchall()

    # Проверим, а есть ли данные по этому помощнику
    if len(list_of_tickets) == 0:
        await message.reply("Не найдено данных по этому помощнику")
        return

    # Эта строка отправится в сообщении
    message_string = f"📊 Статистика помощника <code>{helper_id}</code> за <b>{datetime.datetime.now().date()}</b>: \n\n"

    amount_of_opened_tickets = len(list_of_tickets)
    amount_of_closed_tickets = len([ticket for ticket in list_of_tickets if ticket[2] is not None])
    amount_of_messages = len(list_of_messages)

    message_string += f"📖 Открыто тикетов: {amount_of_opened_tickets} \
        \n📂 Закрыто тикетов: {amount_of_closed_tickets} \
        \n💬 Отправлено сообщений в поддержку: {amount_of_messages}\n\n"

    current_hour = int(os.getenv("WORK_DAY_STARTED_AT"))  # В это время начинается рабочий день
    end_of_work_day = int(os.getenv("WORK_DAY_END_AT"))

    for msg in list_of_messages:
        hour_of_message = (msg[0] - day_started_at) // 3600

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

    # Создаем inline keyboard
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text="Статистика за месяц", callback_data=f"monthstats_{helper_id}"),
        InlineKeyboardButton(text="Логи", callback_data=f"logs_{helper_id}_1")
    )

    # Создаем InputFile
    photo = BufferedInputFile(
        get_graphic([i[0] for i in list_of_messages], [j[1] for j in list_of_tickets]).read(),
        filename="activity_plot.png"
    )

    await message.answer_photo(photo, caption=message_string, parse_mode="html", reply_markup=builder.as_markup())


def get_graphic(*args) -> io.BytesIO:
    """
    Вернет картинку с графиком для дневной активности. Округление до часов.
    Я ненавижу этот кусок кода.
    :param args: Точки времени на графике
    :return:
    """

    plt.figure(figsize=(10, 5))
    colors = ['red', 'orange', 'purple']  # Цвета для каждого графика
    names = ["Сообщения", "Тикеты"]  # Легенды для графиков (в порядке их инициализации
    labels = [names[i] for i in range(len(args))]  # Названия графиков

    for idx, timestamps in enumerate(args):
        if not timestamps:
            continue
        # Преобразование временных меток в datetime и округление до часов
        dates = [datetime.datetime.fromtimestamp(ts).replace(minute=0, second=0, microsecond=0) for ts in timestamps]
        date_counts = Counter(dates)

        # Определение диапазона дат для текущего графика. Ограничиваем рабочим днем (10 - 21)
        min_date = min(dates).replace(hour=int(os.getenv("WORK_DAY_STARTED_AT")))
        max_date = max(dates).replace(hour=int(os.getenv("WORK_DAY_END_AT")))
        hours_range = [min_date + datetime.timedelta(hours=i)
                       for i in range(int((max_date - min_date).total_seconds() // 3600) + 1)
                       ]

        # Заполнение нулями для пропущенных часов
        counts = [date_counts.get(date, 0) for date in hours_range]

        # Построение линии на графике для текущего списка
        plt.plot(hours_range, counts, color=colors[idx % len(colors)], marker='o', linestyle='-', label=labels[idx])

    # Настройки осей и формата даты
    plt.style.use("dark_background")
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%d %b %H:%M'))
    plt.gca().xaxis.set_major_locator(mdates.HourLocator(interval=1))
    plt.gcf().autofmt_xdate()
    plt.ylabel('Активность')
    plt.title('Активность по часам')
    plt.grid(True)
    plt.legend()  # Добавляем легенду для различения графиков

    # Сохранение графика в буфер
    img_buf = io.BytesIO()
    plt.savefig(img_buf, format='png')
    img_buf.seek(0)  # Сброс указателя на начало файла
    plt.close()  # Закрываем график, чтобы освободить память

    return img_buf


logging.info("profile_command_handler.py successful load now")
