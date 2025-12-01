from datetime import datetime, timedelta


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
    print(len(date))
    if len(date) != 10 and date not in ["сегодня", "завтра", "послезавтра"]:
        return False
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