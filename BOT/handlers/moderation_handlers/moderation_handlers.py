from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message
from sentence_transformers import SentenceTransformer
from .utils_for_moderator import check_similarity_of_the_mes_and_top, send_private_warning


class ModerationHandlers:
    def __init__(self, bot, database_of_messages):
        self.bot = bot
        self.model = SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')
        self.confidence_threshold = 0.25
        self.database = database_of_messages
        self.router = Router()
        self.register_handlers()

    def register_handlers(self):
        self.router.message.register(self.cmd_set_topic, Command("set_topic"))
        self.router.message.register(self.check_mes, ~F.command)


    async def cmd_set_topic(self, message: Message):
        await self.database.delete_message_from_chat(message.chat.id)
        text = message.text.replace("/set_topic", "").rstrip().lstrip()
        if len(text) == 0:
            await message.answer("Вы не указали новую тему")

        await self.database.save_message(message.chat.id, text)

        await message.answer(f"Вы установили новую тему: {text}")

    async def check_mes(self, message: Message):
        if len(message.text.split()) < 3:
            return

        if not await check_similarity_of_the_mes_and_top(message.chat.id, message.text, self.database, self.model, self.confidence_threshold):
            await send_private_warning(self.bot, message.from_user.id, message.text, message.chat.title, message.chat.id)
            await message.delete()
            return

        await self.database.save_message(message.chat.id, message.text)