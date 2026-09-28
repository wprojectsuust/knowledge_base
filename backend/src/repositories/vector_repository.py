from __future__ import annotations

from typing import Protocol


class VectorRepository(Protocol):
    """Абстракция над векторной БД (ChromaDB): хранит только id + embedding (+ опциональный
    division-тег в metadata для доп. индекса), без контента - контент подтягивается
    отдельно из DataRepository."""

    def query(self, embedding: list[float], n_results: int = 6, division: str | None = None) -> list[int]:
        ...

    def query_with_scores(self, embedding: list[float], n_results: int = 6) -> list[tuple[int, float]]:
        """Как query(), но возвращает (id, косинусовое сходство) - нужно там, где важен
        порог уверенности, а не только топ-N по релевантности."""
        ...

    def add(self, id_: int, embedding: list[float], division: str | None = None) -> None:
        ...

    def delete(self, id_: int) -> None:
        ...
