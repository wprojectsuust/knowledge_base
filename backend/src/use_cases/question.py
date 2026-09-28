import logging

from src.domain.division import detect_division
from src.domain.schedule import ScheduleRequest
from src.services.question_cache_service import QuestionCacheService
from src.use_cases.analyze_data import AnalyzeDataByLLMForUser
from src.use_cases.get_really_questions import GetReallyQuestions
from src.use_cases.get_schedule import GetSchedule
from src.use_cases.search_data import SearchDataByListOfStr

logger = logging.getLogger(__name__)


class Question:
    """Входная точка, оркестратор подзадач. Кэширует вопрос-ответ в Postgres, чтобы
    не тратить токены LLM и CPU на эмбеддинг повторно на одинаковые вопросы.

    Запросы расписания (group+date) не попадают в этот кэш - дата может быть выражена
    относительно ("завтра"), и тот же текст завтра будет значить другой день. У расписания
    свой кэш с TTL (ScheduleCacheService), этого достаточно."""

    def __init__(
        self,
        get_really_questions: GetReallyQuestions,
        search_data: SearchDataByListOfStr,
        analyze_data: AnalyzeDataByLLMForUser,
        question_cache_service: QuestionCacheService,
        get_schedule: GetSchedule,
    ) -> None:
        self._get_really_questions = get_really_questions
        self._search_data = search_data
        self._analyze_data = analyze_data
        self._question_cache_service = question_cache_service
        self._get_schedule = get_schedule

    @staticmethod
    def _cache_key(question: str) -> str:
        return question.strip().lower()

    async def execute(self, question: str) -> str:
        cache_key = self._cache_key(question)
        cached_answer = await self._question_cache_service.get(cache_key)
        if cached_answer is not None:
            logger.info("Question: кэш-хит для вопроса=%s", question)
            return cached_answer

        logger.info("Question: получен вопрос=%s", question)
        really_questions_or_schedule = await self._get_really_questions.execute(question)

        if isinstance(really_questions_or_schedule, ScheduleRequest):
            return await self._get_schedule.execute(
                question, really_questions_or_schedule.group, really_questions_or_schedule.date
            )

        really_questions = really_questions_or_schedule
        division = detect_division(question)
        division_slug = division.slug if division else None
        if division_slug:
            logger.debug("Question: обнаружен Division по ключевым словам: %s", division_slug)

        data = await self._search_data.execute(really_questions, division=division_slug)
        logger.info("Question: найдено документов=%d (id=%s)", len(data), [item.id for item in data])
        answer = await self._analyze_data.execute(question, data)
        await self._question_cache_service.save(cache_key, answer)
        return answer
