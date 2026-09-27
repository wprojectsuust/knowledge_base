from __future__ import annotations

from src.repositories.vector_repository import VectorRepository


class VectorSearchService:
    """Прокси к VectorRepository - изолирует юз-кейсы от конкретной реализации векторной БД."""

    def __init__(self, vector_repository: VectorRepository) -> None:
        self._vector_repository = vector_repository

    def search(self, embedding: list[float], n_results: int = 6) -> list[int]:
        return self._vector_repository.query(embedding, n_results)

    def index(self, id_: int, embedding: list[float]) -> None:
        self._vector_repository.add(id_, embedding)

    def remove(self, id_: int) -> None:
        self._vector_repository.delete(id_)
