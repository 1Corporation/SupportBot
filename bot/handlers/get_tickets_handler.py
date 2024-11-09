from aiogram.filters.command import Command
from aiogram.types import Message

from bot.dispatcher import dp
from utils import DatabaseConnection
from bot.routers.TicketsRouter import AdminStates


# TODO: Сделай рефактор кода: импорт AdminStates нарушает SOLID
@dp.message(Command("get_tickets"))
async def get_tickets_handler(message: Message):
    await get_tickets_executor(message)


async def get_tickets_executor(message: Message) -> None:
    """
    Обработчик для команды get_tickets. Отправляет пользователю все его открытые тикеты в данный момент.
    :param message:
    :return:
    """
    # Получаем аргументы переданные вместе с командой
    args = message.text.split()[1:]

    connect = DatabaseConnection().connect  # В будущем пригодится

    # Получаем id помощника
    if not len(args):
        helper_id = message.from_user.id
    else:
        full_name = " ".join(args)

        cursor = await connect.cursor()
        result = await (await cursor.execute("""
        SELECT user_id FROM helpers 
        WHERE full_name = ? 
        """, (full_name, ))).fetchone()

        if not result:
            await message.reply(f"Помощник {full_name} не был найден в базе данных")
            return

        helper_id = result[0]

    tickets = AdminStates.show_tickets(helper_id)

    if not len(tickets):
        await message.reply("Для данного помощника не найдено ни одного тикета!")
        return

    result = f"✍️ Тикеты помощника <code>{helper_id}</code>: \n\n"
    for ticket in tickets:
        result += f"📖 Тикет <code>#ID{ticket}</code>\n"

    await message.reply(result, parse_mode="html")
