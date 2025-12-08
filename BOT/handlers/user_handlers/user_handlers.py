from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from .utils_for_user_handlers import *

class UserHandlers:
    def __init__(self, bot, database):
        self.bot = bot
        self.router = Router()
        self.register_handlers()
        self.database = database

    def register_handlers(self):
        self.router.message.register(self.cmd_add_users, Command("add_users"))
        self.router.message.register(self.cmd_delete_users, Command("delete_users"))


    async def cmd_add_users(self,message: Message):
        try:
            arr_of_arg = message.text.split(' ')
            if len(arr_of_arg) == 1:
                await message.answer("Недостаточно аргументов, посмотрите пример")
                return

            user_ids = arr_of_arg[1:]

            chat_id = message.chat.id

            text = ''''''

            for user_id in user_ids:
                us_id = int(user_id)
                result = await check_user_in_chat_by_username(self.bot, chat_id, us_id)
                if not result['found'] or not result['in_chat']:
                    text += '\n' + result['message']
                    continue

                username = await self.bot.get_chat(us_id)
                username = username.username
                print(username)

                success, mes = await self.database.add_user_id_to_db(chat_id, us_id, username)
                text += '\n' + mes
            await message.answer(text)

        except Exception as e:
            await message.answer(f"❌ Ошибка {str(e)}")

    async def cmd_delete_users(self,message: Message):
        try:
            arr_of_arg = message.text.split(' ')
            if len(arr_of_arg) == 1:
                await message.answer("Недостаточно аргументов, посмотрите пример")
                return

            user_ids = arr_of_arg[1:]

            chat_id = message.chat.id

            text = ''''''

            for user_id in user_ids:
                us_id = int(user_id)
                result = await check_user_in_chat_by_username(self.bot, chat_id, us_id)
                if not result['found'] or not result['in_chat']:
                    text += '\n' + result['message']
                    continue

                success, mes = await self.database.delete_user_from_db(chat_id, us_id)
                text += '\n' + mes
            await message.answer(text)

        except Exception as e:
            await message.answer(f"❌ Ошибка {str(e)}")