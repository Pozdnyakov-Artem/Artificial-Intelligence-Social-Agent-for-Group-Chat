from aiogram import Router, Bot
from aiogram.filters import Command
from aiogram.types import Message
from BOT.handlers.schedule_handlers.utils_for_schedule_handlers import validate_time, print_free_time, validate_date


class ScheduleHandlers:
    def __init__(self, bot: Bot, database_of_activity, database_of_users):
        self.bot = bot
        self.router = Router()
        self.register_handlers()
        self.database = database_of_activity
        self.database_of_users = database_of_users

    def register_handlers(self):
        self.router.message.register(self.cmd_schedule, Command("schedule"))
        self.router.message.register(self.cmd_find_free_time, Command("find_free_time"))
        self.router.message.register(self.cmd_schedule_add, Command("schedule_add"))
        self.router.message.register(self.cmd_schedule_delete, Command("schedule_delete"))

    async def cmd_schedule(self, message: Message):
        text = message.text.replace("/schedule", "").rstrip().lstrip()

        if await validate_date(text):
            result = await self.database.schedule_on_day(message.from_user.id, text)

            if not result:
                await message.answer("На этот день ничего не запланировано")
                return

            msg = ""

            for act in result:
                msg += f"Начало: {act[0]}  Конец: {act[1]}  {act[2]}\n"

            await message.answer(msg)
        else:
            await message.answer("Вы ввели некорректную дату")

    async def cmd_find_free_time(self, message: Message):
        chat_id = message.chat.id
        chat_users = await self.database_of_users.get_users_of_chat(chat_id)

        if len(chat_users) == 0:
            await message.answer("Вы не добавили пользователей чата. Добавьте через команду <b>/add_users</b>",
                                 parse_mode="HTML")
            return
        chat_users = [user[0] for user in chat_users]
        # print(chat_users)
        cells_time_users = await self.database.find_common_free_time(chat_users, 7)
        await print_free_time(self.bot, chat_id, cells_time_users)

    async def cmd_schedule_add(self, message: Message):
        try:
            arr_of_arg = message.text.split(' ', 4)
            if len(arr_of_arg) < 5:
                await message.answer("Недостаточно аргументов, посмотрите пример")
                return

            _, date, start_time, end_time, activity = arr_of_arg

            if not await validate_date(date):
                await message.answer("❌ Неправильный формат даты. Используйте ГГГГ-ММ-ДД или 'сегодня', 'завтра'")
                return

            if not await validate_time(start_time) or not await validate_time(end_time):
                await message.answer("❌ Неправильный формат времени. Используйте ЧЧ:ММ")
                return

            success, result_message = await self.database.add_activity(message.from_user.id, date, start_time,
                                                                              end_time, activity)

            if success:
                response = (
                    f"✅ <b>Занятие добавлено!</b>\n\n"
                    f"📅 <b>Дата:</b> {date}\n"
                    f"⏰ <b>Время:</b> {start_time} - {end_time}\n"
                    f"🎯 <b>Занятие:</b> {activity}"
                )

            else:
                response = result_message

            await message.answer(response, parse_mode="html")

        except Exception as e:
            await message.answer(f"❌ Ошибка {str(e)}")

    async def cmd_schedule_delete(self, message: Message):
        id_user = message.from_user.id
        name_activity = message.text.replace("/delete_activity", "").rstrip().lstrip()
        del_row = await self.database.delete_activity(name_activity, id_user)

        if del_row:
            await message.answer(f"{name_activity} успешно удаленно из расписания")
            return

        await message.answer(f"В вашем расписание нет {name_activity}")