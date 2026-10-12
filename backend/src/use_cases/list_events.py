from dataclasses import dataclass

from src.domain.event import FORMATS, TOPICS, Event, EventQuery
from src.services.events_service import EventsService


@dataclass(frozen=True, kw_only=True)
class EventsPage:
    events: list[Event]
    # сколько событий в каждой тематике/формате при текущих датах и поиске - цифры на чипах фильтров
    topics: dict[str, int]
    formats: dict[str, int]


class ListEvents:
    """Каталог мероприятий с фильтрацией по дате, тематике, формату и поиском по названию."""

    def __init__(self, events_service: EventsService) -> None:
        self._events_service = events_service

    async def execute(self, query: EventQuery) -> EventsPage:
        events = await self._events_service.find(query)
        facets = await self._events_service.facets(query)
        return EventsPage(
            events=events,
            topics={topic: facets.get("topic", {}).get(topic, 0) for topic in TOPICS},
            formats={fmt: facets.get("format", {}).get(fmt, 0) for fmt in FORMATS},
        )
