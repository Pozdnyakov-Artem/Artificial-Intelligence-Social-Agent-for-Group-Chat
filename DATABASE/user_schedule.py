from sqlite3 import DatabaseError
import aiosqlite
from datetime import datetime, timedelta
import pandas as pd

class ScheduleUserDB:
    def __init__(self,path):
        self.path = path

    async def init_db(self):
        async with aiosqlite.connect(self.path) as db:
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

    async def check_time_conflict(self,user_id: int, date: str, start_time: str, end_time: str):
        async with aiosqlite.connect(self.path) as db:
            quary = '''
            SELECT date, start_time, end_time, activity_name from schedules
            WHERE user_id = ? AND date = ?
            and (
                ? < end_time AND ? > start_time)'''

            params = [user_id, date, start_time, end_time]

            cursor = await db.execute(quary, params)
            conflict = await cursor.fetchall()
            return conflict

    async def add_activity(self,user_id: int, date: str, start_time: str, end_time: str,
                           activity_name: str):
        if datetime.strptime(start_time, "%H:%M") > datetime.strptime(end_time, "%H:%M"):
            return False, "❌ Время окончания должно быть позже времени начала"

        conflicts = await self.check_time_conflict(user_id, date, start_time, end_time)

        if conflicts:
            conflict_info = "\n".join([f"• {c[3]} - {c[0]} {c[1]}:{c[2]}" for c in conflicts])
            return False, f"❌ Время пересекается с существующими занятиями:\n{conflict_info}"

        async with aiosqlite.connect(self.path) as db:
            try:
                await db.execute('''
                INSERT INTO schedules (user_id, date, start_time, end_time, activity_name)
                VALUES (?, ?, ?, ?, ?)''', (user_id, date, start_time, end_time, activity_name))
                await db.commit()
                return True, "✅ Занятие успешно добавлено!"
            except Exception as e:
                return False, f"❌ Ошибка при добавлении {str(e)}"

    async def get_activity_by_date(self, user_id: int, date: str):
        async with aiosqlite.connect(self.path) as db:
            cursor = await db.execute('''
            SELECT start_time, end_time, activity_name from schedules
            WHERE user_id = ? AND date = ?
            ORDER BY start_time''', (user_id, date))

        return await cursor.fetchall()


    async def get_activities_from_db(self,user_ids, days_range: int = 7):
        if not user_ids:
            return pd.DataFrame(columns=['user_id', 'start_time', 'end_time'])

        period_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        period_end = period_start + timedelta(days=days_range)

        start_date = period_start.strftime('%Y-%m-%d')
        end_date = period_end.strftime('%Y-%m-%d')

        placeholders = ','.join(['?' for _ in user_ids])

        query = """
        SELECT 
            user_id,
            datetime(date || ' ' || start_time) as start_datetime,
            datetime(date || ' ' || end_time) as end_datetime
        FROM schedules 
        WHERE user_id IN ({})
            AND date >= ?
            AND date <= ?
        ORDER BY start_datetime
        """.format(placeholders)

        try:
            async with aiosqlite.connect(self.path) as db:
                params = [*user_ids, start_date, end_date]
                # print(params)
                cursor = await db.execute(query, params)
                rows = await cursor.fetchall()

                if not rows:
                    return pd.DataFrame(columns=['user_id', 'start_time', 'end_time'])

                df = pd.DataFrame(rows, columns=['user_id', 'start_time', 'end_time'])

                df['start_time'] = pd.to_datetime(df['start_time'])
                df['end_time'] = pd.to_datetime(df['end_time'])

                return df

        except Exception as e:
            raise DatabaseError(f"Ошибка при получении временных ячеек пользователей: {str(e)}") from e

    async def merge_overlapping_periods(self,df, period_start, period_end):
        if df.empty:
            return []

        sorted_df = df.sort_values('start_time').reset_index(drop=True)

        merged_periods = []
        current_start = sorted_df.iloc[0]['start_time']
        current_end = sorted_df.iloc[0]['end_time']

        for i in range(1, len(sorted_df)):
            next_start = sorted_df.iloc[i]['start_time']
            next_end = sorted_df.iloc[i]['end_time']

            if next_start <= current_end:
                current_end = max(current_end, next_end)
            else:
                merged_periods.append((current_start, current_end))
                current_start = next_start
                current_end = next_end

        merged_periods.append((current_start, current_end))

        merged_periods = [
            (max(start, period_start), min(end, period_end))
            for start, end in merged_periods
        ]

        return merged_periods


    async def find_gaps_between_periods(self, occupied_periods,period_start,period_end):
        free_periods = []

        if not occupied_periods:
            return [(period_start, period_end)]

        first_occupied_start = occupied_periods[0][0]
        if period_start < first_occupied_start:
            free_periods.append((period_start, first_occupied_start))

        for i in range(len(occupied_periods) - 1):
            current_end = occupied_periods[i][1]
            next_start = occupied_periods[i + 1][0]

            if current_end < next_start:
                free_periods.append((current_end, next_start))

        last_occupied_end = occupied_periods[-1][1]
        if last_occupied_end < period_end:
            free_periods.append((last_occupied_end, period_end))

        return free_periods


    async def find_common_free_time(self, user_ids,days_range,workday_start = 9,workday_end = 20):

        activities_df = await self.get_activities_from_db(user_ids, days_range)

        if activities_df.empty:
            # print("Нет данных об активностях для указанных пользователей")
            all_free_periods = []
            for day_offset in range(days_range):
                current_day = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=day_offset)
                period_start = current_day.replace(hour=workday_start, minute=0)
                period_end = current_day.replace(hour=workday_end, minute=0)
                all_free_periods.append((period_start, period_end))
            return all_free_periods

        all_free_periods = []

        for day_offset in range(days_range):
            current_day = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=day_offset)

            period_start = current_day.replace(hour=workday_start, minute=0)
            period_end = current_day.replace(hour=workday_end, minute=0)

            day_activities = activities_df[
                (activities_df['start_time'] < period_end) &
                (activities_df['end_time'] > period_start)
                ].copy()

            if not day_activities.empty:
                occupied_periods = await self.merge_overlapping_periods(day_activities, period_start, period_end)

                day_free_periods = await self.find_gaps_between_periods(occupied_periods, period_start, period_end)
                all_free_periods.extend(day_free_periods)
            else:
                all_free_periods.append((period_start, period_end))

        return all_free_periods

    async def delete_activity(self, name_activity, user_id):
        async with aiosqlite.connect("database.db") as db:
            cursor = await db.execute('''
            DELETE FROM schedules
            WHERE user_id = ? AND activity_name = ?
            LIMIT 1''', (user_id, name_activity))

            await db.commit()
            return cursor.rowcount


    async def schedule_on_day(self, user_id, date):
        async with aiosqlite.connect(self.path) as db:
            cursor = await db.execute('''
            SELECT start_time, end_time, activity_name
            FROM schedules
            WHERE user_id = ? AND date = ?
            ORDER BY start_time DESC''', (user_id, date))

            return await cursor.fetchall()