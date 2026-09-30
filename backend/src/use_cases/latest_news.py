import logging

from src.domain.data import Data
from src.domain.news import NEWS_SOURCE_PREFIX, newest_first
from src.services.data_store_service import DataStoreService

logger = logging.getLogger(__name__)

_CANDIDATES = 30  # из последних импортированных выбираем самые свежие по дате публикации


class LatestNews:
    """Самые свежие новости uust.ru из базы знаний - для вопросов «какие есть мероприятия», на
    которые поиск по смыслу новости не находит."""

    def __init__(self, data_store_service: DataStoreService) -> None:
        self._data_store_service = data_store_service

    async def execute(self, limit: int = 5) -> list[Data]:
        candidates = await self._data_store_service.latest_with_prefix(NEWS_SOURCE_PREFIX, _CANDIDATES)
        news = newest_first(candidates, limit)
        logger.info("LatestNews: %d новостей из %d последних", len(news), len(candidates))
        return news
