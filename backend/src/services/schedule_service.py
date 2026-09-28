from __future__ import annotations

from src.domain.schedule import DaySchedule
from src.repositories.schedule_repository import ScheduleRepository


class ScheduleService:
    """Прокси к ScheduleRepository - изолирует юз-кейсы от конкретного источника расписания."""

    def __init__(self, repository: ScheduleRepository) -> None:
        self._repository = repository

    async def resolve_group(self, group: str) -> str | None:
        return await self._repository.resolve_group(group)

    async def get_day_schedule(self, group: str, date: str) -> DaySchedule | None:
        return await self._repository.get_day_schedule(group, date)
