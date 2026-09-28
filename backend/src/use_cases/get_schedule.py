import logging

from src import config
from src.services.data_store_service import DataStoreService
from src.services.embedding_service import EmbeddingService
from src.services.schedule_cache_service import ScheduleCacheService
from src.services.schedule_service import ScheduleService
from src.services.vector_search_service import VectorSearchService
from src.use_cases.analyze_schedule import AnalyzeScheduleForUser

logger = logging.getLogger(__name__)


class GetSchedule:
    """Собирает ответ на запрос расписания: тянет день (с кэшем в Postgres, TTL), для каждого
    уникального места проведения ищет в базе знаний "как добраться" (только при достаточной
    уверенности - см. config.SCHEDULE_DIRECTIONS_SIMILARITY_THRESHOLD), и просит LLM ответить
    на исходный вопрос пользователя этими фактами - не просто перечислить весь день, если
    спросили что-то конкретное (см. AnalyzeScheduleForUser)."""

    def __init__(
        self,
        schedule_service: ScheduleService,
        schedule_cache_service: ScheduleCacheService,
        embedding_service: EmbeddingService,
        vector_search_service: VectorSearchService,
        data_store_service: DataStoreService,
        analyze_schedule: AnalyzeScheduleForUser,
    ) -> None:
        self._schedule_service = schedule_service
        self._schedule_cache_service = schedule_cache_service
        self._embedding_service = embedding_service
        self._vector_search_service = vector_search_service
        self._data_store_service = data_store_service
        self._analyze_schedule = analyze_schedule

    async def execute(self, question: str, group: str, date: str) -> str:
        logger.info("GetSchedule: group=%s date=%s", group, date)

        day_schedule = await self._schedule_cache_service.get(group, date)
        if day_schedule is not None:
            logger.debug("GetSchedule: кэш-хит")
        else:
            day_schedule = await self._schedule_service.get_day_schedule(group, date)
            if day_schedule is None:
                return f"Не удалось найти расписание для группы {group} на {date}."
            await self._schedule_cache_service.save(day_schedule)

        if not day_schedule.lessons:
            return f"{day_schedule.day_label}: пар нет."

        venues = {lesson.venue for lesson in day_schedule.lessons if lesson.venue}
        directions: dict[str, str] = {}
        for venue in venues:
            found = await self._find_directions(venue)
            if found:
                directions[venue] = found

        return await self._analyze_schedule.execute(question, day_schedule, directions)

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
