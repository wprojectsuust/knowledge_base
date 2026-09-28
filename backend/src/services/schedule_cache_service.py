from __future__ import annotations

from src.domain.schedule import DaySchedule
from src.repositories.schedule_cache_repository import ScheduleCacheRepository


class ScheduleCacheService:
    """Прокси к ScheduleCacheRepository - изолирует юз-кейсы от конкретной реализации кэша."""

    def __init__(self, repository: ScheduleCacheRepository) -> None:
        self._repository = repository

    async def connect(self) -> None:
        await self._repository.connect()

    async def get(self, group: str, date: str) -> DaySchedule | None:
        return await self._repository.get(group, date)

    async def save(self, day_schedule: DaySchedule) -> None:
        await self._repository.save(day_schedule)
