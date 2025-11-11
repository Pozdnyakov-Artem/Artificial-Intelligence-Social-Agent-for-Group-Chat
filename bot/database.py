import asyncio
import aiosqlite
from datetime import datetime

async def init_db():
    async with aiosqlite.connect("database.db") as db:
        await db.execute('''
        CREATE TABLE IF NOT EXISTS schedules (
        ID INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        date DATE NOT NULL,
        start_time TIME NOT NULL,
        end_time TIME NOT NULL,
        activity_name TEXT NOT NULL
        )''')
        await db.commit()
    print("✅ База данных с временными интервалами инициализирована")

async def check_time_conflict(user_id: int, date: str, start_time: str, end_time: str):
    async with aiosqlite.connect("database.db") as db:
        quary = '''
        SELECT date, start_time, end_time, activity_name from schedules
        WHERE user_id = ? AND date = ?
        and (
            (start_time <= ? AND end_time >= ?) OR
            (start_time >= ? AND end_time <= ?) OR
            (start_time <= ? AND end_time <= ?) OR
            (start_time >= ? AND end_time >= ?))'''

        params = [user_id, date, start_time, end_time, start_time, end_time, start_time, end_time, start_time, end_time]

        cursir = await db.execute(quary, params)
        conflict = await cursir.fetchall()
        return conflict

async def add_activity(user_id: int, date: str, start_time: str, end_time: str,
                       activity_name: str):
    if datetime.strptime(start_time, "%H:%M") > datetime.strptime(end_time, "%H:%M"):
        return False, "❌ Время окончания должно быть позже времени начала"

    conflicts = await check_time_conflict(user_id, date, start_time, end_time)

    if conflicts:
        conflict_info = "\n".join([f"• {c[3]} - {c[0]} {c[1]}:{c[2]}" for c in conflicts])
        return False, f"❌ Время пересекается с существующими занятиями:\n{conflict_info}"

    async with aiosqlite.connect("database.db") as db:
        try:
            await db.execute('''
            INSERT INTO schedules (user_id, date, start_time, end_time, activity_name)
            VALUES (?, ?, ?, ?, ?)''', (user_id, date, start_time, end_time, activity_name))
            await db.commit()
            return True, "✅ Занятие успешно добавлено!"
        except Exception as e:
            return False, f"❌ Ошибка при добавлении {str(e)}"

async def get_activity_by_date(user_id: int, date: str):
    async with aiosqlite.connect("database.db") as db:
        cursor = await db.execute('''
        SELECT start_time, end_time, activity_name from schedules
        WHERE user_id = ? AND date = ?
        ORDER BY start_time''', (user_id, date))

    return await cursor.fetchall()

