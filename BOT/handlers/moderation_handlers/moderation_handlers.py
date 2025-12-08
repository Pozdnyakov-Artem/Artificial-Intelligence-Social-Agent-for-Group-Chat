from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message
from sentence_transformers import SentenceTransformer
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from .utils_for_moderator import check_similarity_of_the_mes_and_top, send_private_warning, toxicity_testing


class ModerationHandlers:
    def __init__(self, bot, database_of_messages):
        self.bot = bot
        self.model = SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')
        self.model2 = AutoModelForSequenceClassification.from_pretrained('cointegrated/rubert-tiny-toxicity')
        self.tokenizer = AutoTokenizer.from_pretrained('cointegrated/rubert-tiny-toxicity')
        self.confidence_threshold = 0.35
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
            return

        await self.database.save_message(message.chat.id, text)

        await message.answer(f"Вы установили новую тему: {text}")

    async def check_mes(self, message: Message):

        if any(toxicity_testing(message.text,self.model2, self.tokenizer) > 0.6):
            await message.delete()
            warning_text2 = (
                f"👮‍♂️ <b>Помошник из чата \"{message.chat.title}\"</b>\n\n"
                f"Ваше сообщение было удалено:\n"
                f"<b>Причина:</b> деструктивное сообщение\n\n"
                f"Пожалуйста, не используйте нецензурную брань."
            )
            await self.bot.send_message(message.from_user.id,warning_text2, parse_mode="HTML")
            return

        if len(message.text.split()) < 3:
            return

        if not await check_similarity_of_the_mes_and_top(message.chat.id, message.text, self.database, self.model, self.confidence_threshold):
            await send_private_warning(self.bot, message.from_user.id, message.text, message.chat.title, message.chat.id)
            await message.delete()
            return

        await self.database.save_message(message.chat.id, message.text)