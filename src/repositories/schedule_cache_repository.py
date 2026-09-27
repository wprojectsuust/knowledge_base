from __future__ import annotations

from typing import Protocol

from src.domain.schedule import DaySchedule


class ScheduleCacheRepository(Protocol):
    """Кэш расписания по (группа, дата) с TTL - не дёргать живой сайт ИСУ на каждый запрос."""

    async def connect(self) -> None:
        ...

    async def get(self, group: str, date: str) -> DaySchedule | None:
        ...

    async def save(self, day_schedule: DaySchedule) -> None:
        ...
