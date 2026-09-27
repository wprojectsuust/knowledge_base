from __future__ import annotations

from src.domain.data import Data
from src.repositories.data_repository import DataRepository


class DataStoreService:
    """Прокси к DataRepository - изолирует юз-кейсы от конкретной реализации хранилища данных."""

    def __init__(self, data_repository: DataRepository) -> None:
        self._data_repository = data_repository

    def get(self, id_: int) -> Data | None:
        return self._data_repository.get(id_)

    def get_many(self, ids: list[int]) -> list[Data]:
        return self._data_repository.get_many(ids)

    def save(self, data: Data) -> None:
        self._data_repository.save(data)

    def remove(self, id_: int) -> None:
        self._data_repository.delete(id_)
