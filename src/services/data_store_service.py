from __future__ import annotations

from src.domain.data import Data
from src.repositories.data_repository import DataRepository


class DataStoreService:
    """Прокси к DataRepository - изолирует юз-кейсы от конкретной реализации хранилища данных."""

    def __init__(self, data_repository: DataRepository) -> None:
        self._data_repository = data_repository

    async def get(self, id_: int) -> Data | None:
        return await self._data_repository.get(id_)

    async def get_many(self, ids: list[int]) -> list[Data]:
        return await self._data_repository.get_many(ids)

    async def save(self, data: Data) -> int:
        return await self._data_repository.save(data)

    async def remove(self, id_: int) -> None:
        await self._data_repository.delete(id_)
