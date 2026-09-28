from __future__ import annotations

from typing import Protocol

from src.domain.schedule import DaySchedule


class ScheduleRepository(Protocol):
    """Абстракция над источником расписания (ИСУ УУНиТ)."""

    async def resolve_group(self, group: str) -> str | None:
        """Название группы как в справочнике («топ106б» -> «ТОП-106Б») или None, если такой нет."""
        ...

    async def get_day_schedule(self, group: str, date: str) -> DaySchedule | None:
        ...
