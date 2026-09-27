from __future__ import annotations

from typing import Protocol

from src.domain.schedule import DaySchedule


class ScheduleRepository(Protocol):
    """Абстракция над источником расписания (ИСУ УУНиТ)."""

    async def get_day_schedule(self, group: str, date: str) -> DaySchedule | None:
        ...
