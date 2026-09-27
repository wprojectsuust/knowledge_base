from __future__ import annotations

from typing import Protocol

from src.domain.data import Data


class DataRepository(Protocol):
    """Абстракция над хранилищем сырых данных (S3). Реализация - следующий пункт TODO."""

    def get(self, id_: int) -> Data | None:
        ...

    def save(self, data: Data) -> None:
        ...

    def delete(self, id_: int) -> None:
        ...
