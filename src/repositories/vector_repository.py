from __future__ import annotations

from typing import Protocol

from src.domain.data import Data


class VectorRepository(Protocol):
    """Абстракция над векторной БД (ChromaDB). Реализация - следующий пункт TODO."""

    def query(self, embedding: list[float], n_results: int = 6) -> list[Data]:
        ...

    def add(self, id_: int, embedding: list[float], data: Data) -> None:
        ...

    def delete(self, id_: int) -> None:
        ...
