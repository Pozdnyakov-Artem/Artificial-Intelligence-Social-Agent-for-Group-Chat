from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from .utils_for_base_handlers import about_command, help_command, examples, key_board


class BaseHandlers:
    def __init__(self):
        self.router = Router()
        self.register_handlers()

    def register_handlers(self):
        self.router.message.register(self.cmd_start, Command("start"))
        self.router.message.register(self.cmd_help, Command("help"))
        self.router.message.register(self.cmd_examples, Command("examples"))
        self.router.message.register(self.cmd_about, Command("about"))

    async def cmd_start(self, message: Message):
        await message.answer("<i> Привет я</i> <b>Бот Помошник</b>, помогаю фильтровать чат и назначать встречи. Более подробно обо мне можно узнать в /about  а о моих командах в /examples",
                               parse_mode="HTML",
                               reply_markup=key_board)

    async def cmd_about(self, message: Message):
        await message.answer(about_command)

    async def cmd_help(self, message: Message):
        await message.answer(help_command, parse_mode="html")

    async def cmd_examples(self, message: Message):
        await message.answer(examples, parse_mode="HTML")