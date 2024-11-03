from aiogram.types import Message

from utils import Singleton
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
            "month_stats": self.__month_stats,
            "logs": self.__logs
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

        await method(*method_args)

    async def __month_stats(self, message: Message, user_id) -> None:
        pass

    async def __logs(self, message: Message, user_id, page) -> None:
        pass
