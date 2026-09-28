from __future__ import annotations

from typing import Protocol

from src.domain.news import NewsHeadline


class NewsRepository(Protocol):
    """Источник новостей вуза (сайт uust.ru)."""

    async def latest(self, limit: int) -> list[NewsHeadline]:
        """Свежие новости, от новых к старым."""
        ...

    async def article_text(self, url: str) -> str | None:
        """Текст новости или None, если страницу не удалось скачать/разобрать."""
        ...
