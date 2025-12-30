from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass

import aiohttp

LOGGER = logging.getLogger(__name__)

API_URL = "https://isdayoff.ru/api/getdata"
TIMEOUT = aiohttp.ClientTimeout(total=7)
TTL_SECONDS = 24 * 60 * 60


@dataclass
class CalendarResult:
    raw: str
    fetched_at: float


class CalendarService:
    def __init__(self) -> None:
        self._cache: dict[tuple[int, int], CalendarResult] = {}
        self._lock = asyncio.Lock()
        self._session: aiohttp.ClientSession | None = None

    async def start(self) -> None:
        if self._session is None:
            self._session = aiohttp.ClientSession(timeout=TIMEOUT)

    async def close(self) -> None:
        if self._session:
            await self._session.close()
            self._session = None

    async def get_month(self, year: int, month: int) -> str:
        await self.start()
        key = (year, month)
        now = time.time()
        async with self._lock:
            cached = self._cache.get(key)
            if cached and now - cached.fetched_at < TTL_SECONDS:
                return cached.raw
        raw = await self._fetch_month(year, month)
        async with self._lock:
            self._cache[key] = CalendarResult(raw=raw, fetched_at=now)
        return raw

    async def _fetch_month(self, year: int, month: int) -> str:
        if not self._session:
            raise RuntimeError("Session is not initialized")
        params = {"year": str(year), "month": f"{month:02d}", "pre": "1"}
        try:
            async with self._session.get(API_URL, params=params) as response:
                if response.status != 200:
                    LOGGER.warning("Calendar API error: status %s", response.status)
                    raise CalendarError("bad status")
                data = await response.text()
        except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
            LOGGER.warning("Calendar API request failed: %s", exc)
            raise CalendarError("request failed") from exc
        if data in {"100", "101", "199"}:
            LOGGER.warning("Calendar API returned error code: %s", data)
            raise CalendarError("calendar error code")
        return data


class CalendarError(Exception):
    pass
