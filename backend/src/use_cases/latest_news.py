import logging
from datetime import datetime

from src import config
from src.domain.data import Data
from src.domain.event import EventQuery
from src.domain.news import NEWS_SOURCE_PREFIX, newest_first
from src.services.data_store_service import DataStoreService
from src.services.events_service import EventsService

logger = logging.getLogger(__name__)

_CANDIDATES = 30  # из последних импортированных выбираем самые свежие по дате публикации
_UPCOMING_EVENTS = 8
# id сводки мероприятий в контексте - отрицательный, чтобы не совпасть с id фрагментов базы
_EVENTS_DIGEST_ID = -1


class LatestNews:
    """Что происходит в университете - для вопросов «какие есть мероприятия», на которые поиск по
    смыслу почти ничего не находит: сводка ближайших событий из каталога мероприятий (если он
    подключён) и самые свежие новости uust.ru из базы знаний."""

    def __init__(self, data_store_service: DataStoreService, events_service: EventsService | None = None) -> None:
        self._data_store_service = data_store_service
        self._events_service = events_service

    async def execute(self, limit: int = 5) -> list[Data]:
        candidates = await self._data_store_service.latest_with_prefix(NEWS_SOURCE_PREFIX, _CANDIDATES)
        news = newest_first(candidates, limit)
        digest = await self._upcoming_events()
        logger.info("LatestNews: %d новостей из %d последних, сводка мероприятий: %s", len(news), len(candidates), bool(digest))
        return ([digest] if digest else []) + news

    async def _upcoming_events(self) -> Data | None:
        if self._events_service is None:
            return None
        today = datetime.now(config.LOCAL_TZ).date()
        events = await self._events_service.find(EventQuery(date_from=today, limit=_UPCOMING_EVENTS))
        if not events:
            return None
        lines = "\n".join(
            f"- {event.starts_at.astimezone(config.LOCAL_TZ):%d.%m %H:%M} - {event.title} "
            f"({event.topic}, {event.format}{', онлайн' if event.online else ''}): {event.url}"
            for event in events
        )
        return Data(
            id=_EVENTS_DIGEST_ID,
            source="https://uust.ru/events/",
            content=f"Ближайшие мероприятия УУНиТ (каталог мероприятий, вкладка «Мероприятия»):\n{lines}",
        )
