from __future__ import annotations

import aiosqlite

DB_PATH = "bot.db"


async def init_db() -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS user_salary (
                user_id INTEGER PRIMARY KEY,
                salary INTEGER NOT NULL
            )
            """
        )
        await db.commit()


async def get_salary(user_id: int) -> int | None:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT salary FROM user_salary WHERE user_id = ?",
            (user_id,),
        ) as cursor:
            row = await cursor.fetchone()
    if row:
        return int(row[0])
    return None


async def set_salary(user_id: int, salary: int) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO user_salary (user_id, salary) VALUES (?, ?)"
            " ON CONFLICT(user_id) DO UPDATE SET salary = excluded.salary",
            (user_id, salary),
        )
        await db.commit()
