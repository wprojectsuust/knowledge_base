from __future__ import annotations

from src.repositories.question_cache_repository import QuestionCacheRepository


class QuestionCacheService:
    """Прокси к QuestionCacheRepository - изолирует юз-кейсы от конкретной реализации кэша."""

    def __init__(self, repository: QuestionCacheRepository) -> None:
        self._repository = repository

    async def connect(self) -> None:
        await self._repository.connect()

    async def get(self, question: str) -> str | None:
        return await self._repository.get(question)

    async def save(self, question: str, answer: str) -> None:
        await self._repository.save(question, answer)
