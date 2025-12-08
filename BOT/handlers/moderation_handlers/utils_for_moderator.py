from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError, TelegramNotFound, TelegramRetryAfter
from sklearn.metrics.pairwise import cosine_similarity
import torch

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
    except TelegramForbiddenError:
        print(f"User {user_id} not found or blocked the bot")
    except TelegramRetryAfter as e:
        print(f"Flood control.")
    except Exception as e:
        print(f"Failed to send warning to {user_id}: {e}")
        try:
            await bot.send_message(
                chat_id=chat_id,
                text=f"⚠️ Не удалось отправить предупреждение пользователю"
            )
        except Exception as inner_e:
            print(f"Also failed to send error notification: {inner_e}")

async def check_similarity_of_the_mes_and_top(chat_id: int, text: str, database, model, confidence_threshold: float):
    context = await database.get_last_messages(chat_id)
    if len(context) == 0:
        return True

    context = ','.join([message[0] for message in context])

    embedding_context = model.encode([context])

    print(cosine_similarity(model.encode([text]), embedding_context)[0][0])

    if cosine_similarity(model.encode([text]), embedding_context)[0][0] > confidence_threshold:
        return True

    return False

def toxicity_testing(text, model, tokenizer):
    if text is None or not text.strip():
        return 0.0
    with torch.no_grad():
        inputs = tokenizer(text, return_tensors='pt', truncation=True, padding=True)
        proba = torch.sigmoid(model(**inputs).logits).numpy()
    if isinstance(text, str):
        proba = proba[0]
    proba[0] = 1-proba[0]
    # print(proba)
    return proba