from datetime import datetime
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram import Bot, Dispatcher
import asyncio
from aiogram.filters import Command
from future.backports.datetime import timedelta

import database

token = "8250049999:AAGZYbqKzYZgwK-q2QlUtW3iJNQbOQ3DFUY"

bot = Bot(token = token)
dp = Dispatcher()

help_commands ='''
<b>/help</b> - выводит все обрабатываемые команды
<b>/description</b> - выводит описание бота
<b>/Ruslanchik</b> - бот любит Руслана
<b>/fa_fa_watafa</b> - подшарить за крутотень'''

description_commands = '''🌟 Ваш цифровой помощник для групповых чатов

Устали от бесконечных обсуждений без результата? Я помогу вашей группе перейти от слов к делу!

Что я умею:
🔹 Автоматически фиксировать важные договорённости
🔹 Напоминать о запланированных встречах и событиях  
🔹 Отвечать на уточняющие вопросы по текущим обсуждениям
🔹 Структурировать организационные моменты
🔹 Снижать информационный шум в чате

Я работаю как невидимый ассистент — интегрируюсь в беседу естественно, не нарушая динамику общения. Просто добавьте меня в группу, и я начну помогать!'''

kb = ReplyKeyboardMarkup(resize_keyboard=True,
                         keyboard=[[KeyboardButton(text = '/help'),KeyboardButton(text = '/description')],
                         [KeyboardButton(text = '/fa_fa_watafa'),KeyboardButton(text = '/Ruslanchik')]])

async def on_startup(bot: Bot):
    print("Бот запущен")
    await database.init_db()

async def on_shutdown(bot: Bot):
    print("🛑 Бот останавливается...")
    await bot.session.close()
    print("✅ Бот успешно остановлен")

@dp.message(Command("start"))
async def command_start(message: Message):
    await bot.send_message(message.chat.id,
                        "<i>Всем привет я</i> <b>Русланчик</b>",
                           parse_mode="HTML",
                           reply_markup=kb)

@dp.message(Command("description"))
async def command_description(message: Message):
    await message.answer(description_commands)

@dp.message(Command("help"))
async def command_help(message: Message):
    await message.reply(help_commands, parse_mode="html")

@dp.message(Command("fa_fa_watafa"))
async def command_fa_fa_watafa(message: Message):
    await bot.send_photo(message.chat.id,"https://avatars.mds.yandex.net/i?id=3baa06b8ed6f875ef012664afe718776_l-5174967-images-thumbs&n=13",
                         caption="fa fa watafa")

@dp.message(Command("Ruslanchik"))
async def command_Ruslanchik(message: Message):
    await message.answer("@smglvrus, лошарик")


@dp.message(Command("add"))
async def command_add(message: Message):
    try:
        arr_of_arg = message.text.split(' ', 4)
        if len(arr_of_arg) < 5:
            await message.answer("Недостаточно аргументов, посмотрите пример")
            return

        _, date, start_time, end_time, activity = arr_of_arg

        if not await validate_date(date):
            await message.answer("❌ Неправильный формат даты. Используйте ГГГГ-ММ-ДД или 'сегодня', 'завтра'")
            return

        if not await validate_time(start_time) or not await validate_time(end_time):
            await message.answer("❌ Неправильный формат времени. Используйте ЧЧ:ММ")
            return

        success, result_message = await database.add_activity(message.from_user.id,date, start_time, end_time, activity)

        if success:
            response = (
                f"✅ <b>Занятие добавлено!</b>\n\n"
                f"📅 <b>Дата:</b> {date}\n"
                f"⏰ <b>Время:</b> {start_time} - {end_time}\n"
                f"🎯 <b>Занятие:</b> {activity}"
            )

        else:
            response = result_message

        await message.answer(response, parse_mode="html")

    except Exception as e:
        await message.answer(f"❌ Ошибка {str(e)}")

async def parse_time(date: str):
    today = datetime.now().date()

    if date.lower() == "сегодня":
        return today.strftime("%Y-%m-%d")
    elif date.lower() == "завтра":
        return (today+timedelta(days = 1)).strftime("%Y-%m-%d")
    elif date.lower() == "послезавтра":
        return (today+ timedelta(days = 2)).strftime("%Y-%m-%d")

    return date

async def validate_date(date: str):
    prep_date = await parse_time(date)

    try:
        datetime.strptime(prep_date, "%Y-%m-%d")
        return True
    except:
        return False

async def validate_time(time : str):
    try:
        datetime.strptime(time, "%H:%M")
        return True
    except:
        return False



async def main():
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())