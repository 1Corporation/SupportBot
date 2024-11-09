"""
Все классы ниже - 'адаптеры'
Как только бот-помощник будет изменен, все эти классы будут сильно изменены/удалены,
Так как не изолированы от воздействия из вне

Если нарушена обратная совместимость с ботом-помощником, в первую очередь смотрите сюда
Скорее всего вам будет легче удалить это, и написать новую имплементацию
"""

import os
import time
import logging
from typing import List, Dict

from aiogram.types import Message
from dotenv import load_dotenv

from bot.routers.RouterInterface import RouterInterface
from utils import Singleton, DatabaseConnection

# in this module use .env vars, load it
load_dotenv()


class TicketsRouter(RouterInterface, Singleton):
    """
    Наследует Singleton (Одиночка) паттерн
    Реализует интерфейс RouterInterface, основная документация в нем
    Конкретно этот роутер определяет, является ли сообщение командой 'взял' 'закрыл' и игнорирует прочие сообщения
    """

    # Константы
    GET_COMMAND = "взял"
    CLOSE_COMMAND = "закрыл"
    ID_START_WITH = "#id"  # С этих символов начинается айди пользователя. Костыль для дополнительной стандартизации

    # noinspection PyUnusedLocal
    async def handle(self, message: Message, *args, **kwargs) -> None:
        """
        Распределяет, куда дальше пойдет сообщение
        :param message: aiogram Message object
        :param args: args
        :param kwargs: kwargs
        :return: None
        """

        logging.debug("TicketsRouter handle method work now")

        # Сообщение может не иметь текста и вызывать ошибку, исправим
        if not message.text:
            return

        # Стандартизируем текст
        text = message.text.lower()
        split_text = text.split()

        # stop method if message no valid
        if not self.__validate_message(*split_text):
            await self.__answer_to_ticket(message)
            return

        command = split_text[0]

        # message routing
        if command == self.GET_COMMAND:
            await self.__get_ticket(message)
            return

        await self.__close_ticket(message)

    def __validate_message(self, *args: List[str]) -> bool:
        """
        Метод проверки является ли сообщение командой 'взял', 'закрыл'
        :param text: Текст сообщения
        :return: bool - Является ли сообщение командой
        """

        return len(args) == 2 \
            and args[0] in [self.GET_COMMAND, self.CLOSE_COMMAND] \
            and args[1][:3] == self.ID_START_WITH

    # noinspection PyMethodMayBeStatic

    async def __answer_to_ticket(self, message: Message) -> None:
        """
        Метод, вызывающийся в случае, если в сообщении нет ни одной из команд (взял, закрыл)
        :param message: aiogram.types. Message
        :return: None
        """

        # Проверяем, находится ли юзер в состоянии диалога
        if not AdminStates.exists(message.from_user.id):
            return

        # TODO: Узнай у Александра, обязательно ли ответ на тикет должен быть ответом на сообщение.
        # Может добавить дополнительную валидацию?
        if not message.reply_to_message:  # Опционально
            return

        # После валидаций, точно знаем что помощник находится в диалоге с человеком

        connect = DatabaseConnection().connect
        cursor = await connect.cursor()

        # Проверим, есть ли этот помогатор в базе данных
        result_set = await cursor.execute("SELECT user_id FROM helpers WHERE user_id=?", (message.from_user.id,))
        if not await result_set.fetchone():  # Если его нет, ну соболезную, все уже пошло через жопу
            return

        # Делаем запись
        await connect.execute("INSERT INTO messages VALUES (?, ?)", (message.from_user.id, time.time()))
        await connect.commit()

    # noinspection PyMethodMayBeStatic
    async def __get_ticket(self, message: Message) -> None:
        """
        Производит создание тикета в базе данных, для дальнейшего анализа
        :param message: aiogram.types. Message
        :return: None
        """

        helper_id = message.from_user.id
        # гениальный мув, чтобы добыть айди человека, просившего помощь
        # Делим текст на два, получаем из него вторую часть (в котором содержится ID),
        # откидываем первые 3 символа и приводим к int
        ticket_author_id = int(message.text.split()[1][3:])

        # Добавляем user_id в AdminStates
        try:
            AdminStates.add_to_state(helper_id, ticket_author_id)
        except ValueError as e:
            logging.warning(
                f"ValueError, попытка взять тикет который уже взяли до этого. \
                Аргументы ошибки: {e.args}, \
                инфа по умнику: {message.from_user.username}, {message.from_user.full_name}")
            await message.reply("Попытка взять тикет, который вы взяли до этого.")
            return

        connect = DatabaseConnection().connect
        cursor = await connect.cursor()

        # Проверим, есть ли этот помогатор в базе данных
        result_set = await cursor.execute("SELECT user_id FROM helpers WHERE user_id=?", (helper_id,))
        if not await result_set.fetchone():  # Если его нет, добавим
            await connect.execute("INSERT INTO helpers VALUES (?, ?)", (helper_id, message.from_user.full_name))

        # Создаем запись в базе данных
        await connect.execute(
            "INSERT INTO tickets VALUES (?, ?, ?, ?)", (
                helper_id,
                ticket_author_id,
                time.time(),
                None)
        )
        await connect.commit()

        # Отправляем сообщение о том, что тикет успешно взят
        await message.reply(os.getenv("GET_TICKET_MESSAGE"))

    # noinspection PyMethodMayBeStatic
    async def __close_ticket(self, message: Message):

        helper_id = message.from_user.id
        # гениальный мув, чтобы добыть айди человека, просившего помощь Делим текст на два,
        # получаем из него вторую часть (в котором содержится ID), откидываем первые 3 символа и приводим к int
        ticket_author_id = int(message.text.split()[1][3:])

        try:
            AdminStates.remove_from_state(helper_id, ticket_author_id)
        except ValueError as e:
            logging.critical(
                f"ValueError, попытка удалить несуществующий тикет. \
                Аргументы ошибки: {e.args}, \
                инфа по умнику: {message.from_user.username}, {message.from_user.full_name}")
            await message.reply("Попытка удалить не существующий тикет. Как вы это сделали?!")
            return

        # TODO: Оптимизировать запрос
        # Даже не буду никакие ошибки хандлить, если что-то пошло через жопу, то точно еще 40 строк назад.
        # Сохранил в отдельную переменную, так как запрос звучит крипова
        database_request = """
        UPDATE tickets
        SET end_time = ?
        WHERE helper_id = ? AND
        ticket_author_id = ? AND 
        start_time = (SELECT MAX(start_time) FROM tickets WHERE ticket_author_id = ? AND helper_id = ?)  
        """

        # Взял именно максимальное значение start_time, так как исходя из всех условий которые есть в коде
        # Должна обновиться только самая последняя запись
        connect = DatabaseConnection().connect

        await connect.execute(
            database_request, (
                time.time(),
                helper_id,
                ticket_author_id,
                ticket_author_id,
                helper_id
            ))

        await connect.commit()

        # Если все ок, отправляем сообщение
        await message.reply(os.getenv("CLOSE_TICKET_MESSAGE"))


class State:
    """
    В этом классе хранится вся информация о статусе помощника в данный момент
    """

    def __init__(self) -> None:
        # Потенциальная утечка памяти, но кого волнует пара мб оперативки?
        self.__tickets: List[int] = []

    def add_ticket(self, ticket_id: int) -> None:
        """
        Добавляет новый тикет в список тикетов
        :param ticket_id: айди автора тикета
        :return: None
        :raise ValueError: в случае, если происходит попытка добавить в список тикетов уже существующий тикет
        """

        # Проверяем, не существует ли этот тикет
        if ticket_id in self.__tickets:
            raise ValueError("Попытка добавить уже существующий тикет, в список тикетов")

        # Если нет
        self.__tickets.append(ticket_id)

    def remove_ticket(self, ticket_id: int) -> None:
        """
        Добавляет новый тикет в список тикетов
        :param ticket_id: айди автора тикета
        :return: None
        :raise ValueError: в случае, если происходит попытка удалить из списка тикетов уже существующий тикет
        """

        # Ищем тикет в списке тикетов
        for i in range(len(self.__tickets)):
            if self.__tickets[i] == ticket_id:
                del self.__tickets[i]
                return

        # Если не нашли
        raise ValueError("Попытка удалить не существующий тикет из списка тикетов")

    def exists(self) -> bool:
        """
        Возвращает bool, true если в списке есть tickets, иначе false
        :return: bool
        """

        return bool(len(self.__tickets))


class AdminStates:
    """
    Этот класс хранит в себе статусы помощников отвечающих на сообщения
    """

    __states: Dict[int, State] = {}

    # Выведен за ненадобностью, нарушает приватность State
    # @classmethod
    # def get_state(cls, user_id: int) -> Optional[State]:
    #     """
    #     Возвращает State из словаря, если запись существует. Иначе вернет None
    #     :param user_id: телеграм айди помощника
    #     :return: State или None
    #     """
    #     return cls.__states.get(user_id)

    @classmethod
    def add_to_state(cls, user_id: int, ticket_author_id: int) -> None:
        """
        Если нет такого State - создаст, и добавит новый тикет, иначе просто добавит новый тикет
        :param user_id: - айди помощника
        :param ticket_author_id: айди автора тикета
        :return: None
        """

        state = cls.__states.get(user_id)

        # Проверка существования State, если не существует - создаем новый
        if not state:
            state = State()
            cls.__states[user_id] = state

        state.add_ticket(ticket_author_id)

    @classmethod
    def remove_from_state(cls, user_id: int, ticket_author_id: int) -> None:
        """
        Удалит State помощника
        :param user_id: телеграм айди помощника
        :param ticket_author_id: телеграм айди автора тикета
        :return: None
        :raise KeyError: при попытке удалить не существующий State
        """

        state = cls.__states.get(user_id)
        # Проверим, существует ли State
        if state:
            state.remove_ticket(ticket_author_id)
            return

        raise KeyError("Попытка удалить запись из несуществующего State")

    @classmethod
    def exists(cls, user_id: int) -> bool:
        """
        Возвращает bool, если у помощника есть стейт, а так же см. документацию State.exists
        :param user_id:
        :return: bool
        """

        state = cls.__states.get(user_id)
        if not state:
            return False
        return state.exists()
