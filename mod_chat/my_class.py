import asyncio
import logging
from collections import deque, defaultdict
from datetime import datetime
from typing import Optional, Dict, Any
from concurrent.futures import ThreadPoolExecutor

import numpy as np

# Импорты aiogram
from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import Message, ReplyKeyboardRemove
from aiogram.filters import Command, CommandStart
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
import torch
# Импорты для нейросетей
from transformers import pipeline, AutoTokenizer, AutoModel
from sklearn.metrics.pairwise import cosine_similarity

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ConversationTopicManager:
    """
    МЕНЕДЖЕР ТЕМЫ РАЗГОВОРА НА AIOGRAM
    Управляет определением и контролем темы беседы
    """

    def __init__(self):
        # 🔧 НАСТРОЙКИ СИСТЕМЫ
        self.min_messages_for_topic = 5
        self.similarity_threshold = 0.6
        self.confidence_threshold = 0.7
        self.inactivity_timeout = 1800  # 30 минут
        self.max_topic_duration = 7200  # 2 часа

        # 📊 ДАННЫЕ СИСТЕМЫ
        self.conversation_history = deque(maxlen=50)
        self.current_main_topic = None
        self.topic_confidence = 0.0
        self.topic_established = False
        self.topic_start_time = None
        self.last_message_time = None

        # 🎯 ВОЗМОЖНЫЕ ТЕМЫ
        self.topic_candidates = [
            "программирование и технологии",
            "искусственный интеллект и машинное обучение",
            "наука и исследования",
            "образование и учеба",
            "бизнес и стартапы",
            "искусство и творчество",
            "музыка и аудио",
            "кино и сериалы",
            "игры и гейминг",
            "спорт и активность",
            "путешествия и туризм",
            "еда и кулинария",
            "здоровье и медицина",
            "психология и отношения",
            "хобби и увлечения"
        ]

        # 🧠 МОДЕЛИ НЕЙРОСЕТЕЙ
        self.topic_classifier = None
        self.tokenizer = None
        self.model = None

        # 🔄 ПУЛ ПОТОКОВ ДЛЯ АСИНХРОННОЙ ОБРАБОТКИ НЕЙРОСЕТЕЙ
        self.thread_pool = ThreadPoolExecutor(max_workers=2)

        # 🔄 ИНИЦИАЛИЗАЦИЯ МОДЕЛЕЙ
        asyncio.create_task(self._initialize_models())

    async def _initialize_models(self):
        """АСИНХРОННАЯ ЗАГРУЗКА МОДЕЛЕЙ"""
        try:
            logger.info("🔄 Загрузка моделей нейросетей...")

            # Используем легкую модель для быстрой загрузки
            def load_classifier():
                return pipeline(
                    "zero-shot-classification",
                    model="valhalla/distilbart-mnli-12-1"
                )

            def load_embedding_model():
                tokenizer = AutoTokenizer.from_pretrained('cointegrated/rubert-tiny')
                model = AutoModel.from_pretrained('cointegrated/rubert-tiny')
                return tokenizer, model

            # Загружаем модели в отдельном потоке
            loop = asyncio.get_event_loop()
            self.topic_classifier = await loop.run_in_executor(self.thread_pool, load_classifier)
            self.tokenizer, self.model = await loop.run_in_executor(self.thread_pool, load_embedding_model)

            logger.info("✅ Модели успешно загружены!")

        except Exception as e:
            logger.error(f"❌ Ошибка загрузки моделей: {e}")
            self.topic_classifier = None

    def _get_text_embedding_sync(self, text: str) -> np.ndarray:
        """СИНХРОННОЕ СОЗДАНИЕ ВЕКТОРНОГО ПРЕДСТАВЛЕНИЯ ТЕКСТА"""
        try:
            if self.tokenizer is None or self.model is None:
                return np.zeros((1, 312))

            inputs = self.tokenizer(
                text,
                return_tensors='pt',
                truncation=True,
                padding=True,
                max_length=512
            )

            with torch.no_grad():
                outputs = self.model(**inputs)
                embedding = outputs.last_hidden_state.mean(dim=1).detach().numpy()

            return embedding

        except Exception as e:
            logger.error(f"Ошибка создания эмбеддинга: {e}")
            return np.zeros((1, 312))

    async def get_text_embedding(self, text: str) -> np.ndarray:
        """АСИНХРОННОЕ СОЗДАНИЕ ВЕКТОРНОГО ПРЕДСТАВЛЕНИЯ ТЕКСТА"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.thread_pool, self._get_text_embedding_sync, text)

    def _calculate_similarity_sync(self, text1: str, text2: str) -> float:
        """СИНХРОННОЕ ВЫЧИСЛЕНИЕ СХОЖЕСТИ ДВУХ ТЕКСТОВ"""
        try:
            emb1 = self._get_text_embedding_sync(text1)
            emb2 = self._get_text_embedding_sync(text2)
            similarity = cosine_similarity(emb1, emb2)[0][0]
            return similarity

        except Exception as e:
            logger.error(f"Ошибка вычисления схожести: {e}")
            return 0.0

    async def calculate_similarity(self, text1: str, text2: str) -> float:
        """АСИНХРОННОЕ ВЫЧИСЛЕНИЕ СХОЖЕСТИ ДВУХ ТЕКСТОВ"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.thread_pool, self._calculate_similarity_sync, text1, text2)

    async def analyze_conversation_topic(self) -> tuple[Optional[str], float]:
        """АСИНХРОННЫЙ АНАЛИЗ ОСНОВНОЙ ТЕМЫ РАЗГОВОРА"""
        if len(self.conversation_history) < self.min_messages_for_topic:
            return None, 0.0

        if self.topic_classifier is None:
            return None, 0.0

        try:
            recent_messages = list(self.conversation_history)[-10:]
            conversation_text = " ".join([msg['text'] for msg in recent_messages])

            def classify_text():
                return self.topic_classifier(
                    conversation_text,
                    self.topic_candidates,
                    multi_label=False
                )

            # Асинхронный вызов классификации
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(self.thread_pool, classify_text)

            main_topic = result['labels'][0]
            confidence = result['scores'][0]

            logger.info(f"🎯 Определена тема: {main_topic} (уверенность: {confidence:.2f})")
            return main_topic, confidence

        except Exception as e:
            logger.error(f"Ошибка анализа темы: {e}")
            return None, 0.0

    async def check_message_relevance(self, text: str) -> tuple[bool, str]:
        """АСИНХРОННАЯ ПРОВЕРКА РЕЛЕВАНТНОСТИ СООБЩЕНИЯ"""
        if not self.topic_established or not self.current_main_topic:
            return True, "Тема еще не установлена"

        try:
            similarity = await self.calculate_similarity(text, self.current_main_topic)

            if similarity >= self.similarity_threshold:
                return True, f"Сообщение соответствует теме '{self.current_main_topic}'"
            else:
                return False, f"Сообщение не соответствует теме '{self.current_main_topic}'"

        except Exception as e:
            logger.error(f"Ошибка проверки релевантности: {e}")
            return True, "Ошибка проверки"

    async def process_message(self, text: str, user_id: int) -> Dict[str, Any]:
        """АСИНХРОННАЯ ОБРАБОТКА НОВОГО СООБЩЕНИЯ"""
        current_time = datetime.now()

        # 🔄 ПРОВЕРКА СБРОСА ТЕМЫ
        reset_reason = await self._check_topic_reset(current_time)
        if reset_reason:
            await self._reset_topic(reset_reason)

        # 💾 СОХРАНЕНИЕ СООБЩЕНИЯ
        self.conversation_history.append({
            'text': text,
            'user_id': user_id,
            'timestamp': current_time
        })

        self.last_message_time = current_time

        logger.info(f"💬 Сообщение от {user_id}: {text[:50]}...")

        # 🎯 АСИНХРОННОЕ ОПРЕДЕЛЕНИЕ ТЕМЫ
        main_topic, confidence = await self.analyze_conversation_topic()

        if main_topic and confidence >= self.confidence_threshold:
            self.current_main_topic = main_topic
            self.topic_confidence = confidence
            self.topic_established = True
            if not self.topic_start_time:
                self.topic_start_time = current_time

        # 🔍 АСИНХРОННАЯ ПРОВЕРКА РЕЛЕВАНТНОСТИ
        is_relevant, reason = await self.check_message_relevance(text)

        return {
            'is_relevant': is_relevant,
            'reason': reason,
            'current_topic': self.current_main_topic,
            'topic_confidence': confidence,
            'topic_established': self.topic_established,
            'topic_reset': bool(reset_reason),
            'reset_reason': reset_reason,
            'history_size': len(self.conversation_history)
        }

    async def _check_topic_reset(self, current_time: datetime) -> Optional[str]:
        """ПРОВЕРКА НЕОБХОДИМОСТИ СБРОСА ТЕМЫ"""
        if not self.topic_established:
            return None

        # 🕒 ПРОВЕРКА НЕАКТИВНОСТИ
        if self.last_message_time:
            inactivity = (current_time - self.last_message_time).total_seconds()
            if inactivity > self.inactivity_timeout:
                return "inactivity_timeout"

        # ⏰ ПРОВЕРКА МАКСИМАЛЬНОЙ ДЛИТЕЛЬНОСТИ
        if self.topic_start_time:
            topic_age = (current_time - self.topic_start_time).total_seconds()
            if topic_age > self.max_topic_duration:
                return "max_duration_reached"

        return None

    async def _reset_topic(self, reason: str):
        """СБРОС ТЕМЫ"""
        old_topic = self.current_main_topic

        self.current_main_topic = None
        self.topic_confidence = 0.0
        self.topic_established = False
        self.topic_start_time = None

        logger.info(f"🔄 Тема '{old_topic}' сброшена. Причина: {reason}")


class TopicBot:
    """
    ОСНОВНОЙ КЛАСС БОТА НА AIOGRAM
    """

    def __init__(self, token: str):
        # 🤖 ИНИЦИАЛИЗАЦИЯ AIOGRAM
        self.bot = Bot(
            token=token,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML)
        )
        self.dp = Dispatcher()
        self.router = Router()

        # 🧠 МЕНЕДЖЕР ТЕМЫ
        self.topic_manager = ConversationTopicManager()

        # 📊 СТАТИСТИКА ПОЛЬЗОВАТЕЛЕЙ
        self.user_stats = defaultdict(lambda: {'relevant': 0, 'irrelevant': 0})

        # 🎛️ НАСТРОЙКА ОБРАБОТЧИКОВ
        self._setup_handlers()

        logger.info("🤖 Бот на aiogram инициализирован!")

    def _setup_handlers(self):
        """НАСТРОЙКА ОБРАБОТЧИКОВ СООБЩЕНИЙ"""

        # 📨 ОБРАБОТКА ТЕКСТОВЫХ СООБЩЕНИЙ
        self.router.message.register(
            self.handle_message,
            F.text & ~F.command
        )

        # ⌨️ КОМАНДЫ
        self.router.message.register(self.cmd_start, CommandStart())
        self.router.message.register(self.cmd_topic, Command("topic"))
        self.router.message.register(self.cmd_reset, Command("reset_topic"))
        self.router.message.register(self.cmd_stats, Command("stats"))
        self.router.message.register(self.cmd_help, Command("help"))

        # 📋 РЕГИСТРАЦИЯ РОУТЕРА
        self.dp.include_router(self.router)

    async def handle_message(self, message: Message):
        """
        ОБРАБОТКА ТЕКСТОВЫХ СООБЩЕНИЙ
        Вызывается при каждом сообщении пользователя
        """
        user = message.from_user
        text = message.text

        # 🚫 ПРОПУСК КОРОТКИХ СООБЩЕНИЙ
        if len(text.strip()) < 3:
            await message.answer("❌ Сообщение слишком короткое для анализа")
            return

        logger.info(f"👤 {user.full_name} ({user.id}): {text}")

        try:
            # 🧠 АСИНХРОННАЯ ОБРАБОТКА В МЕНЕДЖЕРЕ ТЕМЫ
            result = await self.topic_manager.process_message(text, user.id)

            # 🔄 УВЕДОМЛЕНИЕ О СБРОСЕ ТЕМЫ
            if result.get('topic_reset'):
                await self._notify_topic_change(message, result)

            # ✅/❌ ОБРАБОТКА РЕЛЕВАНТНОСТИ
            if result['topic_established'] and not result['is_relevant']:
                await self.handle_irrelevant_message(message, result, user)
            else:
                await self.handle_relevant_message(message, result, user)

        except Exception as e:
            logger.error(f"Ошибка обработки сообщения: {e}")
            await message.answer("❌ Произошла ошибка при обработке сообщения")

    async def handle_irrelevant_message(self, message: Message, result: dict, user):
        """
        ОБРАБОТКА НЕРЕЛЕВАНТНОГО СООБЩЕНИЯ
        """
        # 1. 🗑️ УДАЛЕНИЕ СООБЩЕНИЯ
        try:
            await message.delete()
            logger.info(f"🚫 Удалено сообщение от {user.full_name}")
        except Exception as e:
            logger.error(f"Ошибка удаления сообщения: {e}")

        # 2. ⚠️ ПРЕДУПРЕЖДЕНИЕ
        warning_text = (
            f"🚫 {user.full_name}, ваше сообщение не соответствует текущей теме!\n\n"
            f"📌 <b>Текущая тема:</b> {result['current_topic']}\n"
            f"💡 <b>Пожалуйста, придерживайтесь обсуждения этой темы</b>\n\n"
            f"<i>Сообщение будет автоматически удалено через 10 секунд</i>"
        )

        try:
            warning_msg = await message.answer(warning_text)

            # 3. 📊 ОБНОВЛЕНИЕ СТАТИСТИКИ
            self.user_stats[user.id]['irrelevant'] += 1

            # 4. ⏰ УДАЛЕНИЕ ПРЕДУПРЕЖДЕНИЯ
            await asyncio.sleep(10)
            await warning_msg.delete()

            # 5. 🔇 ПРОВЕРКА ШТРАФОВ
            await self._check_user_penalties(message, user.id)

        except Exception as e:
            logger.error(f"Ошибка отправки предупреждения: {e}")

    async def handle_relevant_message(self, message: Message, result: dict, user):
        """
        ОБРАБОТКА РЕЛЕВАНТНОГО СООБЩЕНИЯ
        """
        # 📊 ОБНОВЛЕНИЕ СТАТИСТИКИ
        self.user_stats[user.id]['relevant'] += 1

        # 🎉 СЛУЧАЙНОЕ ПОДТВЕРЖДЕНИЕ (10% шанс)
        if result['topic_established'] and np.random.random() < 0.1:
            affirmation_text = (
                f"✅ Отлично, {user.full_name}! Сообщение соответствует теме "
                f"'{result['current_topic']}'"
            )

            try:
                affirmation_msg = await message.answer(affirmation_text)
                await asyncio.sleep(5)
                await affirmation_msg.delete()
            except Exception as e:
                logger.error(f"Ошибка отправки подтверждения: {e}")

        # 📢 ПЕРИОДИЧЕСКОЕ ОБЪЯВЛЕНИЕ ТЕМЫ
        if (result['topic_established'] and
                len(self.topic_manager.conversation_history) % 15 == 0):
            await self._announce_current_topic(message, result)

    async def _notify_topic_change(self, message: Message, result: dict):
        """
        УВЕДОМЛЕНИЕ О СМЕНЕ ТЕМЫ
        """
        reset_reason = result.get('reset_reason', 'unknown')

        reason_messages = {
            'inactivity_timeout': "💤 Обсуждение прервалось из-за неактивности",
            'max_duration_reached': "⏰ Тема автоматически сброшена по времени",
            'new_dialog_detected': "🔄 Обнаружено начало нового обсуждения",
        }

        message_text = reason_messages.get(reset_reason, "🔄 Тема сброшена")
        full_text = f"{message_text}\nТеперь я буду следить за новой темой вашего обсуждения!"

        try:
            notification = await message.answer(full_text)
            await asyncio.sleep(8)
            await notification.delete()
        except Exception as e:
            logger.error(f"Ошибка уведомления о смене темы: {e}")

    async def _announce_current_topic(self, message: Message, result: dict):
        """
        ОБЪЯВЛЕНИЕ ТЕКУЩЕЙ ТЕМЫ
        """
        announcement_text = (
            f"🎯 <b>Текущая тема обсуждения:</b> {result['current_topic']}\n"
            f"📊 <b>Уверенность:</b> {result['topic_confidence']:.1%}\n"
            f"💬 <b>Пожалуйста, придерживайтесь этой темы</b>\n\n"
            f"<i>Это сообщение исчезнет через 15 секунд</i>"
        )

        try:
            announcement = await message.answer(announcement_text)
            await asyncio.sleep(15)
            await announcement.delete()
        except Exception as e:
            logger.error(f"Ошибка объявления темы: {e}")

    async def _check_user_penalties(self, message: Message, user_id: int):
        """
        ПРОВЕРКА И ПРИМЕНЕНИЕ ШТРАФОВ
        """
        violations = self.user_stats[user_id]['irrelevant']

        if violations == 2:
            # ⚠️ ВТОРОЕ ПРЕДУПРЕЖДЕНИЕ
            warning_text = "⚠️ <b>Второе предупреждение!</b>\nСледующее нарушение - мут на 5 минут."

            try:
                warning_msg = await message.answer(warning_text)
                await asyncio.sleep(8)
                await warning_msg.delete()
            except Exception as e:
                logger.error(f"Ошибка отправки предупреждения: {e}")

        elif violations >= 3:
            # 🔇 УВЕДОМЛЕНИЕ О МУТЕ
            mute_text = "🔇 <b>Пользователь получил мут на 5 минут</b>\nЗа многократные нарушения темы разговора"

            try:
                mute_msg = await message.answer(mute_text)
                await asyncio.sleep(8)
                await mute_msg.delete()

                # Здесь можно добавить реальный мут через restrict_chat_member
                # await self.bot.restrict_chat_member(...)

            except Exception as e:
                logger.error(f"Ошибка отправки уведомления о муте: {e}")

    # 🔧 КОМАНДЫ БОТА

    async def cmd_start(self, message: Message):
        """КОМАНДА /start"""
        welcome_text = """
🤖 <b>Бот контроля темы разговора</b> 🎯

Я помогаю поддерживать тематику обсуждения в чате:
• Автоматически определяю основную тему
• Слежу за соответствием сообщений
• Удаляю нерелевантные сообщения

<b>Основные команды:</b>
/topic - показать текущую тему
/stats - ваша статистика  
/reset_topic - сбросить тему
/help - подробная справка

Просто общайтесь - я все сделаю автоматически! 🚀
        """
        await message.answer(welcome_text)

    async def cmd_topic(self, message: Message):
        """КОМАНДА /topic - ПОКАЗАТЬ ТЕКУЩУЮ ТЕМУ"""
        if self.topic_manager.topic_established:
            response_text = (
                f"🎯 <b>Текущая тема:</b> {self.topic_manager.current_main_topic}\n"
                f"📊 <b>Уверенность:</b> {self.topic_manager.topic_confidence:.1%}\n"
                f"💬 <b>Сообщений в истории:</b> {len(self.topic_manager.conversation_history)}\n"
                f"🕒 <b>Тема установлена:</b> {self.topic_manager.topic_start_time.strftime('%H:%M:%S') if self.topic_manager.topic_start_time else 'Нет'}"
            )
        else:
            response_text = (
                "🤔 <b>Тема еще не определена</b>\n\n"
                "Продолжайте общение, и я автоматически определю основную тему "
                "из ваших сообщений. Нужно около 5 сообщений для начала анализа."
            )

        await message.answer(response_text)

    async def cmd_reset(self, message: Message):
        """КОМАНДА /reset_topic - СБРОСИТЬ ТЕМУ"""
        self.topic_manager.current_main_topic = None
        self.topic_manager.topic_established = False
        self.topic_manager.topic_start_time = None
        self.topic_manager.conversation_history.clear()

        response_text = (
            "🔄 <b>Тема сброшена!</b>\n\n"
            "Начинается новое обсуждение! Я автоматически определю основную тему "
            "из ваших следующих сообщений."
        )

        await message.answer(response_text)
        logger.info("Тема сброшена пользователем")

    async def cmd_stats(self, message: Message):
        """КОМАНДА /stats - ПОКАЗАТЬ СТАТИСТИКУ"""
        user = message.from_user
        user_id = user.id

        stats = self.user_stats[user_id]
        total_messages = stats['relevant'] + stats['irrelevant']

        if total_messages > 0:
            relevance_rate = (stats['relevant'] / total_messages) * 100
        else:
            relevance_rate = 0

        response_text = (
            f"📊 <b>Ваша статистика, {user.full_name}:</b>\n\n"
            f"✅ <b>Релевантных сообщений:</b> {stats['relevant']}\n"
            f"❌ <b>Нерелевантных сообщений:</b> {stats['irrelevant']}\n"
            f"📈 <b>Соответствие теме:</b> {relevance_rate:.1f}%\n\n"
            f"💬 <b>Всего в истории:</b> {len(self.topic_manager.conversation_history)} сообщений"
        )

        await message.answer(response_text)

    async def cmd_help(self, message: Message):
        """КОМАНДА /help - ПОМОЩЬ"""
        help_text = """
🤖 <b>Бот контроля темы разговора</b> 🎯

<b>Как это работает:</b>
• Я автоматически определяю основную тему из ваших сообщений
• Слежу, чтобы обсуждение не уходило в сторону  
• Удаляю сообщения, не соответствующие теме

<b>Команды:</b>
/topic - показать текущую тему
/stats - ваша статистика
/reset_topic - сбросить тему
/help - эта справка

<b>Пример:</b>
Если вы обсуждаете программирование, сообщения о фильмах будут удаляться

<i>Бот работает полностью автоматически!</i>
        """
        await message.answer(help_text)

    async def run(self):
        """
        ЗАПУСК БОТА
        """
        logger.info("🚀 Запуск бота на aiogram...")
        print("🤖 Бот запущен! Нажмите Ctrl+C для остановки.")

        try:
            # 🗑️ УДАЛЕНИЕ WEBHOOK (на всякий случай)
            await self.bot.delete_webhook(drop_pending_updates=True)

            # 🔄 ЗАПУСК ОПРОСА
            await self.dp.start_polling(self.bot)

        except KeyboardInterrupt:
            logger.info("⏹️ Остановка бота по запросу пользователя")
        except Exception as e:
            logger.error(f"❌ Ошибка при работе бота: {e}")
        finally:
            # 🔒 ЗАКРЫТИЕ СЕССИИ
            await self.bot.session.close()
            # 🔒 ЗАКРЫТИЕ ПУЛА ПОТОКОВ
            self.topic_manager.thread_pool.shutdown(wait=True)


# 🚀 ТОЧКА ВХОДА
async def main():
    """
    ГЛАВНАЯ АСИНХРОННАЯ ФУНКЦИЯ
    """

    # 🔑 ВАШ ТОКЕН БОТА
    BOT_TOKEN = "8250049999:AAGZYbqKzYZgwK-q2QlUtW3iJNQbOQ3DFUY"

    if BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("❌ ОШИБКА: Замените BOT_TOKEN на реальный токен от @BotFather!")
        print("1. Напишите @BotFather в Telegram")
        print("2. Создайте бота командой /newbot")
        print("3. Скопируйте токен и вставьте в код")
        return

    # 🎛️ СОЗДАНИЕ И ЗАПУСК БОТА
    bot = TopicBot(BOT_TOKEN)
    await bot.run()


if __name__ == "__main__":
    # ▶️ ЗАПУСК АСИНХРОННОЙ ФУНКЦИИ
    asyncio.run(main())