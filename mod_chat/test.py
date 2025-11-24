import asyncio
import aiohttp
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

token = "8250049999:AAGZYbqKzYZgwK-q2QlUtW3iJNQbOQ3DFUY"

class ChatModerator:
    def __init__(self, perspective_api_key):
        self.api_key = perspective_api_key
        self.api_url = "https://commentanalyzer.googleapis.com/v1alpha1/comments:analyze"

    async def analyze_toxicity(self, text):
        """Анализ текста на токсичность через Perspective API"""
        params = {
            'key': self.api_key
        }

        data = {
            'comment': {'text': text},
            'languages': ['ru'],
            'requestedAttributes': {
                'TOXICITY': {},
                'SEVERE_TOXICITY': {},
                'IDENTITY_ATTACK': {},
                'INSULT': {},
                'PROFANITY': {},
                'THREAT': {}
            }
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.api_url, params=params, json=data) as response:
                    result = await response.json()

                    scores = {}
                    for attribute, details in result.get('attributeScores', {}).items():
                        scores[attribute] = details['summaryScore']['value']

                    return scores

        except Exception as e:
            print(f"Error analyzing text: {e}")
            return None


# Инициализация бота
MODERATOR = ChatModerator("YOUR_PERSPECTIVE_API_KEY")


async def moderate_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик сообщений с модерацией"""
    message = update.message
    text = message.text

    if not text:
        return

    # Анализ текста
    scores = await MODERATOR.analyze_toxicity(text)

    if scores:
        # Проверка пороговых значений
        toxicity_score = scores.get('TOXICITY', 0)
        insult_score = scores.get('INSULT', 0)

        if toxicity_score > 0.7 or insult_score > 0.7:
            # Сообщение слишком токсично - удаляем и предупреждаем
            await message.delete()
            warning_msg = await message.reply_text(
                "⚠️ Ваше сообщение было удалено за нарушение правил чата."
            )

            # Удаляем предупреждение через 5 секунд
            await asyncio.sleep(5)
            await warning_msg.delete()

            # Логируем событие
            print(f"Deleted toxic message: {text[:50]}...")
            return

    # Если сообщение прошло модерацию, можно выполнить дополнительные действия
    print(f"Message approved: {text[:50]}...")


def main():
    """Запуск бота"""
    application = Application.builder().token(token).build()

    # Добавляем обработчик для всех текстовых сообщений
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        moderate_message
    ))

    application.run_polling()


if __name__ == "__main__":
    main()