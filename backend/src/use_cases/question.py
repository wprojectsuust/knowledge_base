import logging

from src.domain.clarification import ClarificationRequest, KnownFact, compose_question
from src.domain.campus import Route
from src.domain.division import detect_division
from src.domain.route import RouteRequest
from src.domain.schedule import ScheduleRequest
from src.services.question_cache_service import QuestionCacheService
from src.use_cases.analyze_data import AnalyzeDataByLLMForUser
from src.use_cases.build_route import BuildRoute
from src.use_cases.get_really_questions import GetReallyQuestions
from src.use_cases.get_schedule import GetSchedule
from src.use_cases.search_data import SearchDataByListOfStr

logger = logging.getLogger(__name__)


class Question:
    """Входная точка, оркестратор подзадач. Кэширует вопрос-ответ в Postgres, чтобы
    не тратить токены LLM и CPU на эмбеддинг повторно на одинаковые вопросы.

    Запросы расписания (group+date) не попадают в этот кэш - дата может быть выражена
    относительно ("завтра"), и тот же текст завтра будет значить другой день. У расписания
    свой кэш с TTL (ScheduleCacheService), этого достаточно.

    Если для ответа не хватает сведений о студенте (например, группы), возвращается
    ClarificationRequest - фронт спрашивает студента и присылает тот же вопрос с facts.
    Уточнения не кэшируются. Известные facts склеиваются с вопросом в один текст, поэтому
    кэш ключуется и по ним тоже."""

    def __init__(
        self,
        get_really_questions: GetReallyQuestions,
        search_data: SearchDataByListOfStr,
        analyze_data: AnalyzeDataByLLMForUser,
        question_cache_service: QuestionCacheService,
        get_schedule: GetSchedule,
        build_route: BuildRoute | None = None,
    ) -> None:
        self._get_really_questions = get_really_questions
        self._search_data = search_data
        self._analyze_data = analyze_data
        self._question_cache_service = question_cache_service
        self._get_schedule = get_schedule
        self._build_route = build_route

    @staticmethod
    def _cache_key(question: str) -> str:
        return question.strip().lower()

    async def execute(self, question: str, facts: list[KnownFact] | None = None) -> str | ClarificationRequest | Route:
        facts = facts or []
        question = compose_question(question, facts)
        cache_key = self._cache_key(question)
        cached_answer = await self._question_cache_service.get(cache_key)
        if cached_answer is not None:
            logger.info("Question: кэш-хит для вопроса=%s", question)
            return cached_answer

        logger.info("Question: получен вопрос=%s", question)
        really_questions_or_schedule = await self._get_really_questions.execute(question)

        if isinstance(really_questions_or_schedule, ClarificationRequest):
            if really_questions_or_schedule.field not in {fact.field for fact in facts}:
                return really_questions_or_schedule
            # LLM переспрашивает уже известное - не зацикливаемся, ищем по исходному тексту
            logger.warning("Question: повторное уточнение поля %s, игнорирую", really_questions_or_schedule.field)
            really_questions_or_schedule = [question]

        if isinstance(really_questions_or_schedule, RouteRequest):
            request = really_questions_or_schedule
            route = await self._build_route.execute(request.source, request.target) if self._build_route else None
            if route is None:
                place = request.target.removeprefix("place:")
                return (
                    f"Не нашёл «{place}» на карте кампуса. Маршрут можно проложить до кабинета "
                    "(корпус-кабинет), корпуса, КПП, спортзала, буфета, библиотеки и других отмеченных мест."
                )
            # маршрут не кэшируем: строится мгновенно и детерминированно
            return route

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
