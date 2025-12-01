import aiosqlite

class ChatUsersDB:
    def __init__(self, path):
        self.path = path


    async def init_db(self):
        async with aiosqlite.connect(self.path) as db:
            await db.execute('''
            CREATE TABLE IF NOT EXISTS chats_users (
            ID INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL)''')
            await db.commit()
        print("✅ База данных с пользователями чатов инициализирована")

    async def check_user_exist_in_chat_in_db(self, chat_id:int , user_id: int):
        async with aiosqlite.connect(self.path) as db:
            try:
                query = '''
                            SELECT 1 FROM chats_users 
                            WHERE chat_id = ? AND user_id = ?'''

                cursor = await db.execute(query, (chat_id, user_id))
                result = await cursor.fetchone()

                return result is not None
            except Exception as e:
                print(f"❌ Ошибка при проверке {str(e)}")
                return False


    async def add_user_id_to_db(self, chat_id:int, user_id:int, user_name:str):

        if await self.check_user_exist_in_chat_in_db(chat_id, user_id):
            return False, f'❌ Пользователь @{user_name} уже был добавлен'

        async with aiosqlite.connect(self.path) as db:
            try:
                await db.execute('''
                INSERT INTO chats_users (chat_id, user_id) VALUES (?, ?)''',
                                 (chat_id, user_id))
                await db.commit()
                return True, f'✅ Пользователь @{user_name} успешно добавлен'

            except Exception as e:
                return False, f"❌ Ошибка при добавлении {str(e)}"


    async def get_users_of_chat(self, chat_id:int):
        async with aiosqlite.connect(self.path) as db:
            try:
                query = '''
                SELECT user_id FROM chats_users
                WHERE chat_id = ?'''
                cursor = await db.execute(query, (chat_id,))
                result = await cursor.fetchall()
                return result
            except Exception as e:
                raise f"❌ Ошибка при получение id пользователей чата {str(e)}"