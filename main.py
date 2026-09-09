import asyncio
import logging
from aiogram import Bot, Dispatcher

import config
import database as db
from handlers import router

logging.basicConfig(level=logging.INFO)


async def main():
    if not config.BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN topilmadi. .env faylida BOT_TOKEN ni kiriting.")
    if not config.CHANNEL_ID:
        raise RuntimeError("CHANNEL_ID topilmadi. .env faylida CHANNEL_ID ni kiriting.")

    await db.init_db()

    bot = Bot(token=config.BOT_TOKEN)
    dp = Dispatcher()

    dp.include_router(router)

    print("🚀 Bot muvaffaqiyatli ishga tushdi va xavfsiz rejimda ishlamoqda!")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
