from __future__ import annotations

import asyncio

from src.repositories.vector_repository import VectorRepository


class VectorSearchService:
    """Прокси к VectorRepository - изолирует юз-кейсы от конкретной реализации векторной БД.

    Chroma (embedded/persistent режим) синхронна и делает блокирующий disk I/O, поэтому
    вызовы уходят в отдельный поток через asyncio.to_thread - не блокируем event loop."""

    def __init__(self, vector_repository: VectorRepository) -> None:
        self._vector_repository = vector_repository

    async def search(self, embedding: list[float], n_results: int = 6) -> list[int]:
        return await asyncio.to_thread(self._vector_repository.query, embedding, n_results)

    async def index(self, id_: int, embedding: list[float]) -> None:
        await asyncio.to_thread(self._vector_repository.add, id_, embedding)

    async def remove(self, id_: int) -> None:
        await asyncio.to_thread(self._vector_repository.delete, id_)
