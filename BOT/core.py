from aiogram import Bot, Dispatcher

from BOT.handlers.base_handlers.base_handlers import BaseHandlers
from BOT.handlers.map_handlers.map_handlers import MapHandlers
from BOT.handlers.moderation_handlers.moderation_handlers import ModerationHandlers
from BOT.handlers.schedule_handlers.schedule_handlers import ScheduleHandlers
from BOT.handlers.user_handlers.user_handlers import UserHandlers

from DATABASE.chat_messages import DBOfMessage
from DATABASE.chat_users import ChatUsersDB
from DATABASE.user_schedule import ScheduleUserDB


class TelegramBot:
    def __init__(self, token):
        self.bot = Bot(token)
        self.dp = Dispatcher()
        self._init_databases()
        self._init_handlers()
        self.dp.startup.register(self.on_startup)
        self.dp.shutdown.register(self.on_shutdown)
        self._register_routers()

    def _init_databases(self):
        self.chat_messages_db = DBOfMessage("./data/chat_messages.db")
        self.user_schedule_db = ScheduleUserDB("./data/user_schedule.db")
        self.chat_users_db = ChatUsersDB("./data/chat_users.db")

    def _init_handlers(self):
        self.base_handlers = BaseHandlers()

        self.moderation_handlers = ModerationHandlers(
            bot=self.bot,
            database_of_messages=self.chat_messages_db,
        )

        self.schedule_handlers = ScheduleHandlers(
            bot=self.bot,
            database_of_activity=self.user_schedule_db,
            database_of_users=self.chat_users_db
        )

        self.map_handlers = MapHandlers()

        self.user_handlers = UserHandlers(
            bot=self.bot,
            database=self.chat_users_db,
        )

    def _register_routers(self):
        self.dp.include_router(self.base_handlers.router)
        self.dp.include_router(self.user_handlers.router)
        self.dp.include_router(self.schedule_handlers.router)
        self.dp.include_router(self.map_handlers.router)
        self.dp.include_router(self.moderation_handlers.router)

    async def on_startup(self):
        print("=" * 50)
        print("🤖 Запуск бота для организации встреч")
        print("=" * 50)

        # 1. Инициализация баз данных
        print("🔧 Инициализация баз данных...")
        await self.chat_messages_db.init_db()
        await self.user_schedule_db.init_db()
        await self.chat_users_db.init_db()
        print("✅ Базы данных готовы")

        print("=" * 50)
        print("🚀 Бот успешно запущен и готов к работе!")
        print(f"🤖 ID бота: {self.bot.id}")
        print("=" * 50)

    async def on_shutdown(self):
        print("\n🛑 Завершение работы бота...")
        print("👋 Бот завершил работу")

    async def start(self):
        try:
            await self.bot.delete_webhook(drop_pending_updates=True)
            await self.dp.start_polling(
                self.bot,
                allowed_updates=self.dp.resolve_used_update_types()
            )
        except Exception as e:
            print(f"Критическая ошибка при запуске: {e}")
            raise
        finally:
            await self.on_shutdown()

