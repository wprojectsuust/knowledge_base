from __future__ import annotations

from typing import Protocol

from src.domain.data import Data


class DataRepository(Protocol):
    """Абстракция над реляционным хранилищем документов (PostgreSQL). Асинхронный,
    так как реализация поверх asyncpg."""

    async def get(self, id_: int) -> Data | None:
        ...

    async def get_many(self, ids: list[int]) -> list[Data]:
        ...

    async def save(self, data: Data) -> None:
        ...

    async def delete(self, id_: int) -> None:
        ...
