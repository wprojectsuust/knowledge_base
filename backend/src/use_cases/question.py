import asyncio
import logging

from src.domain.answer import Answer
from src.domain.clarification import ClarificationRequest, KnownFact, compose_question
from src.domain.dialog import DialogTurn
from src.domain.plan import QuestionPlan, SearchTask
from src.domain.progress import Progress, no_progress
from src.domain.route import RouteRequest
from src.domain.schedule import ScheduleRequest
from src.services.llm_service import LLMUnavailableError
from src.services.question_cache_service import QuestionCacheService
from src.use_cases.analyze_data import AnalyzeDataByLLMForUser
from src.use_cases.build_route import BuildRoute
from src.use_cases.compose_answer import ComposeAnswer
from src.use_cases.get_schedule import GetSchedule
from src.use_cases.plan_question import PlanQuestion
from src.use_cases.research_answer import ResearchAnswer
from src.use_cases.search_data import SearchDataByListOfStr

logger = logging.getLogger(__name__)


class Question:
    """Входная точка, оркестратор подзадач.

    Сообщение разбирается в план (PlanQuestion): поиск по базе знаний, расписание, маршрут -
    в любом сочетании. Части выполняются ПАРАЛЛЕЛЬНО, ответы склеиваются в один. Если для
    ответа не хватает сведений о студенте, возвращается ClarificationRequest - фронт спрашивает
    и присылает тот же вопрос с facts (они склеиваются с вопросом в один текст).

    Поиск по базе знаний - со «вторым шансом» (ResearchAnswer): не нашлось сразу - LLM ищет ещё
    другими запросами или уточняет, о ком речь. Ход работы («Ищу в базе знаний», «Смотрю
    расписание») сообщается через progress - фронт показывает его, пока ответ готовится.

    Кэш вопрос-ответ в Postgres - только для чистого поиска по базе знаний без истории чата:
    - расписание может быть относительным («завтра»), у него свой кэш с TTL;
    - маршрут строится мгновенно и детерминированно;
    - с историей тот же текст («а туда как пройти?») значит разное."""

    def __init__(
        self,
        plan_question: PlanQuestion,
        search_data: SearchDataByListOfStr,
        analyze_data: AnalyzeDataByLLMForUser,
        question_cache_service: QuestionCacheService,
        get_schedule: GetSchedule,
        build_route: BuildRoute | None = None,
        compose_answer: ComposeAnswer | None = None,
    ) -> None:
        self._plan_question = plan_question
        self._research_answer = ResearchAnswer(search_data, analyze_data)
        self._question_cache_service = question_cache_service
        self._get_schedule = get_schedule
        self._build_route = build_route
        self._compose_answer = compose_answer

    @staticmethod
    def _cache_key(question: str) -> str:
        return question.strip().lower()

    async def execute(
        self,
        question: str,
        facts: list[KnownFact] | None = None,
        history: list[DialogTurn] | None = None,
        progress: Progress = no_progress,
    ) -> Answer | ClarificationRequest:
        facts = facts or []
        history = history or []
        question = compose_question(question, facts)
        cache_key = self._cache_key(question)

        if not history:
            cached_answer = await self._question_cache_service.get(cache_key)
            if cached_answer is not None:
                logger.info("Question: кэш-хит для вопроса=%s", question)
                return Answer(text=cached_answer)

        logger.info("Question: получен вопрос=%s (реплик в истории: %d)", question, len(history))
        await progress("Разбираю вопрос")
        plan = await self._plan_question.execute(question, history=history)

        if plan.clarification is not None:
            if plan.clarification.field not in {fact.field for fact in facts}:
                return plan.clarification
            # LLM переспрашивает уже известное - не зацикливаемся
            logger.warning("Question: повторное уточнение поля %s, игнорирую", plan.clarification.field)
            plan = QuestionPlan(search=plan.search, schedule=plan.schedule, route=plan.route)
        if plan.reply is not None:
            # тривиальный вопрос («через сколько это?») - ответ уже есть, без поиска и без кэша:
            # он зависит от диалога и текущего времени
            logger.info("Question: тривиальный вопрос, ответ из диалога без поиска")
            return Answer(text=plan.reply)
        if plan == QuestionPlan():
            plan = QuestionPlan(search=SearchTask(question=question, queries=(question,)))

        # части независимы - выполняем одновременно, порядок в ответе: расписание, база, маршрут
        schedule_part, search_part, route_part = await asyncio.gather(
            self._schedule_part(plan.schedule, question, progress),
            # уточняем только один раз: студент уже что-то сообщал о себе - отвечаем тем, что есть
            self._search_part(plan.search, progress, can_clarify=not facts),
            self._route_part(plan.route, progress),
        )
        if isinstance(search_part, ClarificationRequest):
            return search_part
        if plan.route is not None and route_part is None and search_part is None:
            # места нет на карте («главный корпус» - другой кампус) - ищем ответ в базе знаний,
            # там есть адреса корпусов, вместо «не нашёл на карте»
            logger.info("Question: место %s не на карте, отвечаю по базе знаний", plan.route.target)
            search_part = await self._search_part(
                SearchTask(question=question, queries=(question,)), progress, can_clarify=False
            )
            if isinstance(search_part, ClarificationRequest):
                search_part = None
            place = plan.route.target.removeprefix("place:")
            note = f"На карте кампуса УГАТУ «{place}» не отмечено, поэтому маршрут не показываю."
            search_part = f"{search_part}\n\n_{note}_" if search_part else note
        route_text, route = route_part if route_part else (None, None)
        parts = [part for part in (schedule_part, search_part, route_text) if part]
        text = await self._compose(question, parts, route_text, progress)

        only_search = plan.schedule is None and plan.route is None
        if only_search and search_part and not history:
            await self._question_cache_service.save(cache_key, text)
        return Answer(text=text, route=route)

    async def _compose(self, question: str, parts: list[str], route_text: str | None, progress: Progress) -> str:
        """Несколько частей - сводим в один ответ на исходный вопрос (иначе «смогу ли я поспать
        подольше, если…» остаётся без ответа: каждая часть отвечала только на свою подзадачу).
        Шаблонный маршрут идёт как есть, его ИИ не пересказывает."""
        joined = "\n\n".join(parts)
        if len(parts) < 2 or self._compose_answer is None:
            return joined
        await progress("Собираю ответ")
        try:
            composed = await self._compose_answer.execute(question, parts)
        except LLMUnavailableError:
            logger.warning("Question: не удалось свести части в один ответ, отдаю их как есть")
            return joined
        return f"{composed}\n\n{route_text}" if route_text else composed

    async def _schedule_part(self, request: ScheduleRequest | None, question: str, progress: Progress) -> str | None:
        if request is None:
            return None
        await progress(f"Смотрю расписание {request.group}")
        return await self._get_schedule.execute(request.question or question, request.group, request.date)

    async def _search_part(
        self, task: SearchTask | None, progress: Progress, can_clarify: bool
    ) -> str | ClarificationRequest | None:
        if task is None:
            return None
        return await self._research_answer.execute(task, progress=progress, can_clarify=can_clarify)

    async def _route_part(self, request: RouteRequest | None, progress: Progress):
        if request is None or self._build_route is None:
            return None
        await progress("Прокладываю маршрут")
        route = await self._build_route.execute(request.source, request.target)
        if route is None:
            return None
        return route.text(), route
