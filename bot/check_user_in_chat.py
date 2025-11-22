from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest


async def get_user_id_by_username(bot: Bot, chat_id:int, username: str):
    try:
        user = await bot.get_chat(2032633606)
        return user.id
    except TelegramBadRequest as e:
        # Можно уточнить тип ошибки
        if "user not found" in str(e).lower():
            print(f"Пользователь @{username} не найден")
        elif "username not found" in str(e).lower():
            print(f"Юзернейм @{username} не существует")
        else:
            print(f"Ошибка при поиске @{username}: {e}")
        return None

    except Exception as e:
        # Отлавливаем другие возможные ошибки
        print(f"Неожиданная ошибка при поиске @{username}: {e}")
        return None

async def user_in_chat(bot: Bot, chat_id: int, user_id: int):
    try:
        member = await bot.get_chat_member(chat_id, user_id)
        return member.status in ['member', 'administrator', 'creator', 'restricted']

    except TelegramBadRequest as e:
        if "user not found" in str(e).lower() or "chat not found" in str(e).lower():
            return False
        print(f"Ошибка при проверке пользователя: {e}")
        return False

async def check_user_in_chat_by_username(bot: Bot, chat_id: int,us_id:int) -> dict:
    # if username[0] == '@':
    #     username = username[1:]
    # user_id = await get_user_id_by_username(bot,chat_id, username)
    try:
        user_id = await bot.get_chat(us_id)
    except TelegramBadRequest as e:
        if "user not found" in str(e).lower():
            print(f"Пользователь не найден")
        elif "username not found" in str(e).lower():
            print(f"Юзернейм {us_id} не существует")
        else:
            print(f"Ошибка при поиске {us_id}: {e}")

    username = user_id.username
    user_id = user_id.id
    if not user_id:
        return {'found' : False, 'message' : f'Пользователь @{username} не найден в Telegram'}

    in_chat = await user_in_chat(bot, chat_id, user_id)

    if in_chat:
        return {'found' : True,
                'user_id': user_id,
                'chat_id': chat_id,
                'in_chat': True,
                'message': ''}
    else:
        return  {'found' : True,
                'user_id': user_id,
                'chat_id': chat_id,
                'in_chat': False,
                'message': f'Пользователь @{username} не в этом чате'}
