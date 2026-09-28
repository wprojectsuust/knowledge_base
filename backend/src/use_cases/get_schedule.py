import logging

from src import config
from src.services.data_store_service import DataStoreService
from src.services.embedding_service import EmbeddingService
from src.services.schedule_cache_service import ScheduleCacheService
from src.services.schedule_service import ScheduleService
from src.services.vector_search_service import VectorSearchService

logger = logging.getLogger(__name__)


class GetSchedule:
    """Собирает ответ на запрос расписания: тянет день (с кэшем в Postgres, TTL), формирует
    текст с временем/предметом/местом проведения, и для каждого уникального места проведения
    ищет в базе знаний "как добраться" - добавляет в ответ, только если нашлось с достаточной
    уверенностью (порог косинусового сходства, см. config.SCHEDULE_DIRECTIONS_SIMILARITY_THRESHOLD)."""

    def __init__(
        self,
        schedule_service: ScheduleService,
        schedule_cache_service: ScheduleCacheService,
        embedding_service: EmbeddingService,
        vector_search_service: VectorSearchService,
        data_store_service: DataStoreService,
    ) -> None:
        self._schedule_service = schedule_service
        self._schedule_cache_service = schedule_cache_service
        self._embedding_service = embedding_service
        self._vector_search_service = vector_search_service
        self._data_store_service = data_store_service

    async def execute(self, group: str, date: str) -> str:
        logger.info("GetSchedule: group=%s date=%s", group, date)

        day_schedule = await self._schedule_cache_service.get(group, date)
        if day_schedule is not None:
            logger.debug("GetSchedule: кэш-хит")
        else:
            day_schedule = await self._schedule_service.get_day_schedule(group, date)
            if day_schedule is None:
                return f"Не удалось найти расписание для группы {group} на {date}."
            await self._schedule_cache_service.save(day_schedule)

        lines = [f"Расписание {day_schedule.group} на {day_schedule.day_label}:"]
        if not day_schedule.lessons:
            lines.append("Пар нет.")
        else:
            for lesson in day_schedule.lessons:
                venue_part = f" ({lesson.venue})" if lesson.venue else ""
                lines.append(f"- {lesson.time}: {lesson.subject}{venue_part}")

        venues = {lesson.venue for lesson in day_schedule.lessons if lesson.venue}
        for venue in venues:
            directions = await self._find_directions(venue)
            if directions:
                lines.append(f"\nКак добраться до {venue}: {directions}")

        return "\n".join(lines)

    async def _find_directions(self, venue: str) -> str | None:
        embedding = await self._embedding_service.encode(f"как добраться до {venue}")
        scored = await self._vector_search_service.search_with_scores(embedding, n_results=3)
        matched_ids = [
            id_ for id_, score in scored if score >= config.SCHEDULE_DIRECTIONS_SIMILARITY_THRESHOLD
        ]
        if not matched_ids:
            logger.debug("GetSchedule: для '%s' ничего не прошло порог уверенности", venue)
            return None

        matches = await self._data_store_service.get_many(matched_ids)
        return matches[0].content if matches else None
