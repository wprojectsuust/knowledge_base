from __future__ import annotations

from src.domain.event import Event, EventQuery, RawEvent
from src.repositories.events_repository import EventsSource, EventsStore


class EventsService:
    """Прокси к источнику и каталогу мероприятий - юз-кейсы не знают про uust.ru и Postgres."""

    def __init__(self, source: EventsSource, store: EventsStore) -> None:
        self._source = source
        self._store = store

    async def latest_from_site(self, pages: int) -> list[RawEvent]:
        return await self._source.latest(pages)

    async def known_slugs(self, slugs: list[str]) -> set[str]:
        return await self._store.known_slugs(slugs)

    async def save_many(self, events: list[Event]) -> None:
        await self._store.save_many(events)

    async def find(self, query: EventQuery) -> list[Event]:
        return await self._store.find(query)

    async def facets(self, query: EventQuery) -> dict[str, dict[str, int]]:
        return await self._store.facets(query)
