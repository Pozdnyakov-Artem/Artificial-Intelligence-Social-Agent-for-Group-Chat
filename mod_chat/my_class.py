import asyncio
import numpy as np
from aiogram import filters
from aiogram.handlers import MessageHandler
from aiogram.types import Update
from telegram.ext import ContextTypes, CommandHandler, Application
from transformers import pipeline, AutoTokenizer, AutoModel
from sklearn.metrics.pairwise import cosine_similarity
from collections import defaultdict, deque
from datetime import datetime, timedelta
import sqlite3


class ConversationTopicManager:
    def __init__(self):
        # Модель для определения темы
        self.topic_classifier = pipeline(
            "zero-shot-classification",
            model="MoritzLaurer/mDeBERTa-v3-base-mnli-xnli"
        )

        # Модель для эмбеддингов (сравнения схожести)
        self.tokenizer = AutoTokenizer.from_pretrained('cointegrated/rubert-tiny')
        self.model = AutoModel.from_pretrained('cointegrated/rubert-tiny')

        # История сообщений для определения основной темы
        self.conversation_history = deque(maxlen=50)
        self.current_main_topic = None
        self.topic_confidence = 0.0
        self.topic_established = False

        # Кандидаты тем
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

        # Настройки
        self.min_messages_for_topic = 5
        self.similarity_threshold = 0.7
        self.topic_confidence_threshold = 0.8

    def get_embedding(self, text):
        """Получение векторного представления текста"""
        inputs = self.tokenizer(text, return_tensors='pt',
                                truncation=True, padding=True, max_length=512)
        outputs = self.model(**inputs)
        embedding = outputs.last_hidden_state.mean(dim=1).detach().numpy()
        return embedding

    def calculate_similarity(self, text1, text2):
        """Вычисление схожести двух текстов"""
        emb1 = self.get_embedding(text1)
        emb2 = self.get_embedding(text2)
        return cosine_similarity(emb1, emb2)[0][0]

    async def analyze_conversation_topic(self):
        """Анализ основной темы разговора на основе истории"""
        if len(self.conversation_history) < self.min_messages_for_topic:
            return None, 0.0

        # Объединяем последние сообщения для анализа
        recent_messages = list(self.conversation_history)[-10:]
        conversation_text = " ".join([msg['text'] for msg in recent_messages])

        try:
            # Определяем тему
            result = self.topic_classifier(
                conversation_text,
                self.topic_candidates,
                multi_label=False
            )

            main_topic = result['labels'][0]
            confidence = result['scores'][0]

            return main_topic, confidence

        except Exception as e:
            print(f"Topic analysis error: {e}")
            return None, 0.0

    async def check_message_relevance(self, text):
        """Проверка релевантности сообщения текущей теме"""
        if not self.topic_established or not self.current_main_topic:
            return True, "Тема еще не определена"

        # Сравниваем с основной темой
        similarity = self.calculate_similarity(text, self.current_main_topic)

        if similarity >= self.similarity_threshold:
            return True, f"Сообщение соответствует теме '{self.current_main_topic}'"
        else:
            return False, f"Сообщение не соответствует теме '{self.current_main_topic}'"

    async def process_message(self, text, user_id):
        """Обработка нового сообщения"""
        # Добавляем в историю
        self.conversation_history.append({
            'text': text,
            'user_id': user_id,
            'timestamp': datetime.now()
        })

        # Определяем/обновляем основную тему
        main_topic, confidence = await self.analyze_conversation_topic()

        if main_topic and confidence >= self.topic_confidence_threshold:
            self.current_main_topic = main_topic
            self.topic_confidence = confidence
            self.topic_established = True

        # Проверяем релевантность текущего сообщения
        is_relevant, reason = await self.check_message_relevance(text)

        return {
            'is_relevant': is_relevant,
            'reason': reason,
            'current_topic': self.current_main_topic,
            'topic_confidence': self.topic_confidence,
            'topic_established': self.topic_established
        }


# Инициализация менеджера тем
TOPIC_MANAGER = ConversationTopicManager()

class AdaptiveTopicManager:
    def __init__(self):
        self.topic_manager = ConversationTopicManager()
        self.user_stats = defaultdict(lambda: {'relevant': 0, 'irrelevant': 0})
        self.topic_keywords = defaultdict(list)
        self.session_start = datetime.now()

    async def handle_new_message(self, update, context):
        message = update.message
        text = message.text
        user_id = message.from_user.id

        # Обрабатываем сообщение
        result = await self.topic_manager.process_message(text, user_id)

        # Если тема установлена, проверяем релевантность
        if result['topic_established'] and not result['is_relevant']:
            await self.handle_irrelevant_message(update, result, user_id)
        else:
            await self.handle_relevant_message(update, result, user_id)

        # Обновляем статистику
        self.update_user_stats(user_id, result['is_relevant'])

        # Периодически объявляем текущую тему
        await self.announce_topic_if_needed(update, result)

    async def handle_irrelevant_message(self, update, result, user_id):
        """Обработка нерелевантного сообщения"""
        message = update.message

        # Удаляем сообщение
        await message.delete()

        # Отправляем предупреждение
        warning_text = (
            f"🚫 {message.from_user.first_name}, ваше сообщение не соответствует теме!\n"
            f"📌 Текущая тема: {result['current_topic']}\n"
            f"💡 Пожалуйста, придерживайтесь обсуждения этой темы"
        )

        warning_msg = await message.reply_text(warning_text)

        # Увеличиваем счетчик нарушений
        self.user_stats[user_id]['irrelevant'] += 1

        # Проверяем на необходимость мута
        if self.user_stats[user_id]['irrelevant'] >= 3:
            await self.apply_penalty(update, user_id)

        # Удаляем предупреждение через время
        await asyncio.sleep(10)
        await warning_msg.delete()

    async def handle_relevant_message(self, update, result, user_id):
        """Обработка релевантного сообщения"""
        if result['topic_established']:
            # Поощряем релевантные сообщения
            self.user_stats[user_id]['relevant'] += 1

            # Изредка подтверждаем соответствие теме
            if np.random.random() < 0.1:  # 10% chance
                affirmation = await update.message.reply_text(
                    f"✅ Отлично! Сообщение соответствует теме '{result['current_topic']}'"
                )
                await asyncio.sleep(5)
                await affirmation.delete()

    async def apply_penalty(self, update, user_id):
        """Применение штрафов за нарушения"""
        violation_count = self.user_stats[user_id]['irrelevant']

        if violation_count == 3:
            penalty_msg = await update.message.reply_text(
                f"⚠️ Внимание! Превышено количество нарушений. "
                f"Следующее нарушение - мут на 5 минут."
            )
            await asyncio.sleep(8)
            await penalty_msg.delete()

        elif violation_count >= 4:
            # Здесь можно реализовать мут через Telegram API
            mute_msg = await update.message.reply_text(
                f"🔇 Пользователь получил мут на 5 минут за нарушения темы."
            )
            await asyncio.sleep(8)
            await mute_msg.delete()

    async def announce_topic_if_needed(self, update, result):
        """Объявление темы при необходимости"""
        if (result['topic_established'] and
                result['topic_confidence'] > 0.85 and
                len(TOPIC_MANAGER.conversation_history) % 15 == 0):
            announcement = await update.message.reply_text(
                f"🎯 Текущая тема обсуждения: {result['current_topic']}\n"
                f"📊 Уверенность: {result['topic_confidence']:.1%}\n"
                f"💬 Пожалуйста, придерживайтесь этой темы"
            )
            await asyncio.sleep(15)
            await announcement.delete()

    def update_user_stats(self, user_id, is_relevant):
        """Обновление статистики пользователя"""
        if is_relevant:
            self.user_stats[user_id]['relevant'] += 1
        else:
            self.user_stats[user_id]['irrelevant'] += 1


# Инициализация адаптивного менеджера
ADAPTIVE_MANAGER = AdaptiveTopicManager()


class SimplifiedTopicBot:
    def __init__(self, token):
        self.application = Application.builder().token(token).build()
        # Создаем непосредственно ConversationTopicManager
        self.topic_manager = ConversationTopicManager()
        self.user_stats = defaultdict(lambda: {'relevant': 0, 'irrelevant': 0})
        self.setup_handlers()

    def setup_handlers(self):
        self.application.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            self.handle_new_message
        ))
        self.application.add_handler(CommandHandler("topic", self.show_current_topic))
        self.application.add_handler(CommandHandler("reset_topic", self.reset_topic))

    async def handle_new_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка нового сообщения"""
        message = update.message
        text = message.text
        user_id = message.from_user.id

        # Обрабатываем сообщение
        result = await self.topic_manager.process_message(text, user_id)

        # Если тема установлена, проверяем релевантность
        if result['topic_established'] and not result['is_relevant']:
            await self.handle_irrelevant_message(update, result, user_id)
        else:
            await self.handle_relevant_message(update, result, user_id)

    async def show_current_topic(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показывает текущую тему разговора"""
        # Теперь доступ через self.topic_manager
        if self.topic_manager.topic_established:
            await update.message.reply_text(
                f"🎯 Текущая тема: {self.topic_manager.current_main_topic}\n"
                f"📊 Уверенность: {self.topic_manager.topic_confidence:.1%}\n"
                f"💬 Сообщений в истории: {len(self.topic_manager.conversation_history)}"
            )
        else:
            await update.message.reply_text(
                "🤔 Тема еще не определена. Продолжайте общение, "
                "и я автоматически определю основную тему."
            )

    async def handle_irrelevant_message(self, update, result, user_id):
        """Обработка нерелевантного сообщения"""
        message = update.message
        await message.delete()

        warning_text = (
            f"🚫 {message.from_user.first_name}, ваше сообщение не соответствует теме!\n"
            f"📌 Текущая тема: {result['current_topic']}\n"
            f"💡 Пожалуйста, придерживайтесь обсуждения этой темы"
        )

        warning_msg = await message.reply_text(warning_text)
        await asyncio.sleep(10)
        await warning_msg.delete()

    async def handle_relevant_message(self, update, result, user_id):
        """Обработка релевантного сообщения"""
        if result['topic_established'] and np.random.random() < 0.1:
            affirmation = await update.message.reply_text(
                f"✅ Отлично! Сообщение соответствует теме '{result['current_topic']}'"
            )
            await asyncio.sleep(5)
            await affirmation.delete()

    async def reset_topic(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Сбрасывает текущую тему"""
        self.topic_manager.current_main_topic = None
        self.topic_manager.topic_established = False
        self.topic_manager.conversation_history.clear()

        await update.message.reply_text(
            "🔄 Тема сброшена. Начинается новое обсуждение!\n"
            "Я автоматически определю основную тему из ваших сообщений."
        )

    def run(self):
        """Запуск бота"""
        print("Бот с контролем темы запущен...")
        self.application.run_polling()

token = "8250049999:AAGZYbqKzYZgwK-q2QlUtW3iJNQbOQ3DFUY"
# Запуск бота
if __name__ == "__main__":
    bot = SimplifiedTopicBot(token)
    bot.run()