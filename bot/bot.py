from datetime import datetime
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram import Bot, Dispatcher
import asyncio
from aiogram.filters import Command
from future.backports.datetime import timedelta
from arguments import token, description_commands, help_commands
import database_of_activity
import numpy as np
from check_user_in_chat import check_user_in_chat_by_username
import database_of_chat_users
from find_geopos import OSMGeocoder
from find_places import OSMPlacesFinder

bot = Bot(token = token)
dp = Dispatcher()

kb = ReplyKeyboardMarkup(resize_keyboard=True,
                         keyboard=[[KeyboardButton(text = '/help'),KeyboardButton(text = '/description')],
                         [KeyboardButton(text = '/fa_fa_watafa'),KeyboardButton(text = '/Ruslanchik')]])

users = np.array([],dtype = int)

async def on_startup(bot: Bot):
    print("Бот запущен")
    await database_of_activity.init_db_activity()
    await database_of_chat_users.init_db_chats_users()

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

@dp.message(Command("add_users"))
async def command_add_users(message: Message):
    try:
        arr_of_arg = message.text.split(' ')
        if len(arr_of_arg) == 1:
            await message.answer("Недостаточно аргументов, посмотрите пример")
            return

        user_ids = arr_of_arg[1:]

        chat_id = message.chat.id

        text = ''''''

        for user_id in user_ids:
            us_id = int(user_id)
            result = await check_user_in_chat_by_username(bot,chat_id, us_id)
            if not result['found'] or not result['in_chat']:
                text+='\n'+result['message']
                continue

            username = await bot.get_chat(us_id)
            username = username.username
            print(username)

            success, mes = await database_of_chat_users.add_user_id_to_db(chat_id, us_id, username)
            text+='\n'+mes
        await message.answer(text)

    except Exception as e:
        await message.answer(f"❌ Ошибка {str(e)}")

@dp.message(Command("подходящее_время_для_встреч"))
async def command_find_free_time(message: Message):
    chat_id = message.chat.id
    chat_users = await database_of_chat_users.get_users_of_chat(chat_id)

    if len(chat_users) == 0:
        await message.answer("Вы не добавили пользователей чата. Добавьте через команду <b>/add_users</b>", parse_mode="HTML")
        return
    chat_users = [user[0] for user in chat_users]
    # print(chat_users)
    cells_time_users = await database_of_activity.find_common_free_time(chat_users, 7)
    await print_free_time(bot,chat_id,cells_time_users)

@dp.message(Command("add_activity"))
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

        success, result_message = await database_of_activity.add_activity(message.from_user.id,date, start_time, end_time, activity)

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

@dp.message(Command("find_geopos"))
async def command_find_geopos(message: Message):

    address = message.text.replace("/find_geopos", "")
    finder = OSMGeocoder()
    coords = await finder.address_to_coordinates(address)
    await message.answer(f"{coords}")

@dp.message(Command("find_places_near"))
async def command_find_places(message: Message):
    address = message.text.replace("/find_places_near", "")
    finder = OSMGeocoder()
    coords = await finder.address_to_coordinates(address)
    if not coords:
        await message.answer("Некорректный адрес")
        return
    lat, lng = coords
    finder2 = OSMPlacesFinder()
    places = await finder2.get_top_5_places(lat, lng)
    result_text = await finder2.format_results(places)

    await message.answer(f"{result_text}", parse_mode="HTML")

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


async def print_free_time(bot, chat_id, free_periods):
    if not free_periods:
        # print("Нет свободных промежутков в указанный период")
        await bot.send_message(chat_id,"Нет свободных промежутков в указанный период")
        return

    text = '''
    СВОБОДНЫЕ ПРОМЕЖУТКИ\n
    '''
    for i, (start, end) in enumerate(free_periods, 1):
        duration = end - start
        duration_hours = duration.total_seconds() / 3600

        text += f"{i}. {start.strftime('%d.%m.%Y %H:%M')} - {end.strftime('%H:%M')}\n"
        text += f"   Длительность: {duration_hours:.1f} часов\n"
        text += f"   День недели: {start.strftime('%A')}\n\n"

    await bot.send_message(chat_id,text)
    return


async def main():
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())