from __future__ import annotations

from src.domain.news import NewsHeadline
from src.repositories.news_repository import NewsRepository


class NewsService:
    """Прокси к NewsRepository - изолирует юз-кейсы от конкретного источника новостей."""

    def __init__(self, repository: NewsRepository) -> None:
        self._repository = repository

    async def latest(self, limit: int) -> list[NewsHeadline]:
        return await self._repository.latest(limit)

    async def article_text(self, url: str) -> str | None:
        return await self._repository.article_text(url)
