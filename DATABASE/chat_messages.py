import aiosqlite


class DBOfMessage:
    def __init__(self, path):
        self.path = path

    async def init_db(self):
        async with aiosqlite.connect(self.path) as db:
            await db.execute('''
            CREATE TABLE IF NOT EXISTS messages(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_chat INTEGER,
            text TEXT NOT NULL)''')

            await db.commit()

    async def save_message(self, id_chat, text):
        async with aiosqlite.connect(self.path) as db:
            cursor = await db.execute('''
            INSERT INTO messages(id_chat, text)
            VALUES(?, ?)''', (id_chat, text))

            await db.commit()
            return cursor.lastrowid

    async def delete_message_from_chat(self, id_chat, amount = None):
        async with aiosqlite.connect(self.path) as db:
            cursor = await db.execute('''
            DELETE FROM messages
            WHERE id_chat = ?
            LIMIT ?''', (id_chat, amount if amount else 50))

            await db.commit()
            return await cursor.fetchall()

    async def get_last_messages(self, id_chat):
        async with aiosqlite.connect(self.path) as db:
            cursor = await db.execute('''
            SELECT text FROM messages
            WHERE id_chat = ?''', (id_chat,))

            return await cursor.fetchall()