import asyncio
from BOT.core import TelegramBot


async def main():
    bot  = TelegramBot(token)
    await bot.start()

if __name__ == '__main__':
    asyncio.run(main())