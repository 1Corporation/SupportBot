import io
import datetime
import calendar
from collections import Counter

from aiogram.types import Message, BufferedInputFile
from matplotlib import pyplot as plt
import matplotlib.dates as mdates

from utils import Singleton, DatabaseConnection
from bot.routers.RouterInterface import RouterInterface


class CallBackDataRouter(RouterInterface, Singleton):
    """
    Этот класс является роутером для всех callback query
    Базируется на паттерне Singleton (Одиночка) и реализует интерфейс RouterInterface

    Общий синтаксис для всех callback data строк:
    1. К callback data применяется метод .split() с делителем _. Т.е. каждый отдельный аргумент должен быть разделен _
    2. Первый аргумент в callback data будет являться названием вызываемого метода
    3. Все остальные переданные аргументы будут переданы как *args в вызываемый метод

    Допустим у нас есть callback data send_hello_message
    Для метода handle это будет звучать как: self.__send("hello", "message")
    Все методы этого роутера должны быть приватными асинхронными (кроме handle соответственно)
    Прошу придерживаться этого правила либо полностью переписать роутер с 0 (конкретно не желательно)
    """

    def init(self) -> None:
        """
        Инициализатор вместо __init__. Требование от singleton паттерна.
        :return: None
        """
        # Ключ - название метода, значение - сам метод
        # noinspection PyAttributeOutsideInit
        self.methods = {
            "monthstats": self.__month_stats,
            "logs": self.__logs,
        }

    async def handle(self, message: Message, *args, **kwargs) -> None:
        """
        Метод интерфейса RouterInterface. Его поведение расписано в документации к классу
        :param message: aiogram Message object
        :param args: args
        :param kwargs: kwargs
        :return: None
        """

        arguments = args[0].split("_")
        method_name = arguments[0]
        method_args = arguments[1:]
        method = self.methods.get(method_name)

        if not method:
            raise KeyError(f"Невалидная callback data. Метод {method_name} не найден")

        await method(message, *method_args)

    # noinspection PyMethodMayBeStatic
    async def __month_stats(self, message: Message, user_id) -> None:
        """
        Этот метод почти полностью повторяет имплементацию метода __send_profile_message из profile_command_handler.py
        за исключением нескольких моментов. Если изменять что-то в этом методе, то лучше копировать
        __send_profile_message и заново переделывать его. Мне лень придумывать как здесь не наговнокодить.
        Вообще зачем оно здесь?
        :param message: aiogram Message object
        :param user_id: user id помощника
        :return:
        """
        connect = DatabaseConnection().connect
        cursor = await connect.cursor()

        helper_id = int(user_id)
        month_started_at = (datetime.datetime.now() - datetime.timedelta(days=30)).timestamp()

        full_name = await (await cursor.execute(
            """
            SELECT full_name FROM helpers
            WHERE user_id = ?
            """, (helper_id,)
        )).fetchone()

        list_of_tickets = await (await cursor.execute(
            "SELECT ticket_author_id, start_time, end_time \
            FROM tickets WHERE helper_id = ? AND start_time > ? \
            ORDER BY start_time", (
                helper_id, month_started_at))).fetchall()

        list_of_messages = await (await cursor.execute(
            "SELECT time_at FROM messages \
            WHERE helper_id = ? AND time_at > ? \
            ORDER BY time_at", (
                helper_id, month_started_at))).fetchall()

        # Проверим, а есть ли данные по этому помощнику
        if len(list_of_tickets) == 0:
            await message.reply("Не найдено данных по этому помощнику")
            return

        # Эта строка отправится в сообщении
        message_string = \
            f"📊 Статистика помощника <code>{full_name[0]}</code> за этот месяц: \n\n"

        amount_of_opened_tickets = len(list_of_tickets)
        amount_of_closed_tickets = len([ticket for ticket in list_of_tickets if ticket[2] is not None])
        amount_of_messages = len(list_of_messages)

        message_string += f"📖 Открыто тикетов: {amount_of_opened_tickets} \
            \n📂 Закрыто тикетов: {amount_of_closed_tickets} \
            \n💬 Отправлено сообщений в поддержку: {amount_of_messages}\n\n"

        plt.figure(figsize=(10, 5))
        args = [[i[1] for i in list_of_tickets], [j[0] for j in list_of_messages]]
        colors = ['red', 'orange', 'purple']  # Цвета для каждого графика
        names = ["Сообщения", "Тикеты"]  # Легенды для графиков (в порядке их инициализации
        labels = [names[i] for i in range(len(args))]  # Названия графиков

        for idx, timestamps in enumerate(args):
            if not timestamps:
                continue
            # Преобразование временных меток в datetime и округление до часов
            dates = [datetime.datetime.fromtimestamp(ts).replace(hour=0, minute=0, second=0, microsecond=0) for ts in
                     timestamps]
            date_counts = Counter(dates)

            # Получим количество дней в этом месяце
            date_now = datetime.datetime.now()
            _, amount_of_days_in_month = calendar.monthrange(date_now.year, date_now.month)

            # Определение диапазона дат для текущего графика. Ограничиваем рабочим днем (10 - 21)
            min_date = min(dates).replace(day=1)
            max_date = max(dates).replace(day=amount_of_days_in_month)
            hours_range = [min_date + datetime.timedelta(days=i)
                           for i in range(int((max_date - min_date).total_seconds() // 86400) + 1)
                           ]

            # Заполнение нулями для пропущенных часов
            counts = [date_counts.get(date, 0) for date in hours_range]

            # Построение линии на графике для текущего списка
            # noinspection PyTypeChecker
            plt.plot(hours_range, counts, color=colors[idx % len(colors)], marker='o', linestyle='-', label=labels[idx])

        # Настройки осей и формата даты
        plt.style.use("dark_background")
        plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%d %b %H:%M'))
        plt.gca().xaxis.set_major_locator(mdates.DayLocator(interval=5))
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

        await message.answer_photo(
            BufferedInputFile(img_buf.read(), filename="caption.png"),
            caption=message_string,
            parse_mode='html',
        )

    # noinspection PyMethodMayBeStatic
    async def __logs(self, message: Message, user_id, page) -> None:
        await message.answer("Разраб даун, пока без логов. Спасибо!")
