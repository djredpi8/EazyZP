from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher

from .config import BOT_TOKEN
from .handlers import router
from .services.calendar import CalendarService
from .storage.db import init_db


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    await init_db()

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(router)

    calendar = CalendarService()
    dp.workflow_data["calendar"] = calendar

    try:
        await dp.start_polling(bot)
    finally:
        await calendar.close()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
