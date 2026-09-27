from __future__ import annotations

from typing import Protocol


class VectorRepository(Protocol):
    """Абстракция над векторной БД (ChromaDB): хранит только id + embedding, без контента -
    контент подтягивается отдельно из DataRepository. Реализация - следующий пункт TODO."""

    def query(self, embedding: list[float], n_results: int = 6) -> list[int]:
        ...

    def add(self, id_: int, embedding: list[float]) -> None:
        ...

    def delete(self, id_: int) -> None:
        ...
