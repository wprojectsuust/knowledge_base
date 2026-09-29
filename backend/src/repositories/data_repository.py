from __future__ import annotations

from typing import Protocol

from src.domain.data import Data


class DataRepository(Protocol):
    """Абстракция над реляционным хранилищем документов (PostgreSQL). Асинхронный,
    так как реализация поверх asyncpg."""

    async def connect(self) -> None:
        ...

    async def get(self, id_: int) -> Data | None:
        ...

    async def get_many(self, ids: list[int]) -> list[Data]:
        ...

    async def save(self, data: Data) -> int:
        ...

    async def delete(self, id_: int) -> None:
        ...

    async def existing_sources(self, sources: list[str]) -> set[str]:
        """Какие из источников уже есть в базе (например, уже загруженные новости)."""
        ...

    async def sources_with_prefix(self, prefix: str) -> dict[str, int]:
        """source -> id записей, чей источник начинается с prefix (например, порции списка документов)."""
        ...
