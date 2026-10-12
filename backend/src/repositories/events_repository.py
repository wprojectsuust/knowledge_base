from __future__ import annotations

from typing import Protocol

from src.domain.event import Event, EventQuery, RawEvent


class EventsSource(Protocol):
    """Откуда берутся мероприятия (страницы uust.ru/events)."""

    async def latest(self, pages: int) -> list[RawEvent]:
        """События с первых pages страниц, от новых к старым."""
        ...


class EventsStore(Protocol):
    """Каталог мероприятий (PostgreSQL)."""

    async def known_slugs(self, slugs: list[str]) -> set[str]:
        ...

    async def save_many(self, events: list[Event]) -> None:
        ...

    async def find(self, query: EventQuery) -> list[Event]:
        ...

    async def facets(self, query: EventQuery) -> dict[str, dict[str, int]]:
        """Сколько событий по каждой тематике и формату - в пределах дат и поиска из query."""
        ...
