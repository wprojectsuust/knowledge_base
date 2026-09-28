from __future__ import annotations

from typing import Protocol


class QuestionCacheRepository(Protocol):
    """Кэш вопрос -> ответ. Нужен, чтобы не тратить токены LLM и CPU на эмбеддинг
    заново на повторяющиеся вопросы. Реализация - PostgreSQL, отдельная таблица."""

    async def connect(self) -> None:
        ...

    async def get(self, question: str) -> str | None:
        ...

    async def save(self, question: str, answer: str) -> None:
        ...
