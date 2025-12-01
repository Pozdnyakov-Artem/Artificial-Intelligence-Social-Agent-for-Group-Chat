from aiogram import Bot
from sklearn.metrics.pairwise import cosine_similarity


async def send_private_warning(bot: Bot, user_id: int, original_message: str, chat_title: str, chat_id: int):
    try:
        text = original_message if len(original_message) < 20 else original_message[:20] + "..."
        warning_text = (
            f"👮‍♂️ <b>Помошник из чата \"{chat_title}\"</b>\n\n"
            f"Ваше сообщение было удалено:\n"
            f"<i>\"{text}\"</i>\n\n"
            f"<b>Причина:</b> не соответствует теме чата\n\n"
            f"Пожалуйста, придерживайтесь основной темы обсуждения."
        )

        await bot.send_message(chat_id=user_id, text=warning_text, parse_mode="HTML")
    except Exception as e:
        await bot.send_message(chat_id,f"Не удалось отправить личное предупреждение о несоответствие его сообщения контексту пользователю {user_id}")

async def check_similarity_of_the_mes_and_top(chat_id: int, text: str, database, model, confidence_threshold: float):
    context = await database.get_last_messages(chat_id)
    if len(context) == 0:
        return True

    context = ','.join([message[0] for message in context])

    embedding_context = model.encode([context])

    if cosine_similarity(model.encode([text]), embedding_context)[0][0] > confidence_threshold:
        return True

    return False