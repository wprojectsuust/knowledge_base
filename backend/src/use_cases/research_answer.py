import json
import logging
import re

from src.domain.clarification import ClarificationRequest
from src.domain.data import Data
from src.domain.division import detect_division
from src.domain.news import is_news_question
from src.domain.plan import SearchTask
from src.domain.progress import Progress, no_progress
from src.logging_utils import preview
from src.use_cases.analyze_data import AnalyzeDataByLLMForUser
from src.use_cases.latest_news import LatestNews
from src.use_cases.search_data import SearchDataByListOfStr

logger = logging.getLogger(__name__)

_FIELD = re.compile(r"^[a-z_]+$")

_SEARCH_RULE = (
    "Если прямого ответа во фрагментах нет, но его можно получить через другие сведения из базы знаний "
    "(например, чтобы узнать возраст декана, сначала узнать, кто декан, затем найти его дату рождения), "
    'вместо ответа верни ТОЛЬКО JSON {"search": ["<1-3 коротких поисковых запроса>"], "status": '
    '"<что ищешь, 2-6 слов, например: Ищу, кто декан ФИРТ>"}. Запросы должны отличаться от уже сделанных.\n'
)
_CLARIFY_RULE = (
    "Если непонятно, о ком или о чём спрашивают, а во фрагментах несколько подходящих вариантов (например, "
    'деканы разных факультетов), вместо ответа верни ТОЛЬКО JSON {"clarify": {"field": "<поле латиницей: '
    'faculty, group, course…>", "question": "<короткий вежливый вопрос>"}}.\n'
)
_ANSWER_RULE = (
    "Если нужные даты есть (например, дата рождения), вычисли по ним ответ сам (возраст, сколько дней "
    "осталось) и коротко покажи расчёт.\n"
)


class ResearchAnswer:
    """Ответ по базе знаний со «вторым шансом»: если с первого поиска прямого ответа нет, LLM может
    попросить поискать ещё (другими запросами) - «сколько лет декану» -> «кто декан» -> «дата
    рождения» -> посчитать. Или уточнить, о ком речь.

    Каждый шаг - один вызов LLM: если ответ нашёлся сразу, лишних вызовов нет. Найденное копится,
    на последнем шаге LLM обязана ответить тем, что есть. Повтор уже сделанных запросов не ищем."""

    def __init__(
        self,
        search_data: SearchDataByListOfStr,
        analyze_data: AnalyzeDataByLLMForUser,
        max_extra_searches: int = 2,
        latest_news: LatestNews | None = None,
    ) -> None:
        self._search_data = search_data
        self._analyze_data = analyze_data
        self._latest_news = latest_news
        self._max_extra_searches = max_extra_searches

    async def execute(
        self, task: SearchTask, progress: Progress = no_progress, can_clarify: bool = False
    ) -> str | ClarificationRequest:
        division = detect_division(task.question)
        division_slug = division.slug if division else None
        found: dict[int | None, Data] = {}
        searched: set[str] = set()
        queries = list(task.queries)

        if self._latest_news is not None and is_news_question(task.question):
            # «какие есть мероприятия»: свежие новости - первыми в контексте, поиск дополняет
            await progress("Смотрю свежие новости")
            for item in await self._latest_news.execute():
                found.setdefault(item.id, item)

        await progress("Ищу в базе знаний")
        for step in range(self._max_extra_searches + 1):
            fresh = [query for query in queries if query.strip().lower() not in searched]
            searched.update(query.strip().lower() for query in fresh)
            if fresh:
                for item in await self._search_data.execute(fresh, division=division_slug):
                    found.setdefault(item.id, item)
            logger.info("ResearchAnswer: шаг %d, запросы=%s, всего фрагментов=%d", step, fresh, len(found))

            last = step == self._max_extra_searches or (step > 0 and not fresh)
            instructions = _ANSWER_RULE
            if not last:
                instructions += _SEARCH_RULE
            if can_clarify and step == 0:
                instructions += _CLARIFY_RULE

            await progress("Читаю найденное")
            raw = await self._analyze_data.execute(task.question, list(found.values()), instructions)
            action = self._parse_action(raw)
            if action is None:
                return raw

            if "clarify" in action and can_clarify and step == 0:
                clarify = action["clarify"] if isinstance(action["clarify"], dict) else {}
                field = str(clarify.get("field") or "").strip()
                question = str(clarify.get("question") or "").strip()
                if _FIELD.match(field) and question:
                    return ClarificationRequest(field=field, question=question)

            if last:
                # LLM нарушила правило «ответь» - не показываем студенту JSON
                logger.warning("ResearchAnswer: на последнем шаге вместо ответа %s", preview(raw))
                break
            queries = [str(query).strip() for query in action.get("search") or [] if str(query).strip()]
            status = str(action.get("status") or "").strip()
            logger.info("ResearchAnswer: второй шанс - %s, запросы=%s", status, queries)
            await progress(status or f"Ищу: {', '.join(queries)[:60]}")

        return (
            "Не удалось найти ответ в базе знаний. Обратитесь к тьютору или куратору группы, "
            "в дирекцию своего института или деканат факультета."
        )

    @staticmethod
    def _parse_action(raw: str) -> dict | None:
        """JSON-действие ({"search": …} / {"clarify": …}) или None, если это обычный ответ."""
        text = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        if not (text.startswith("{") and text.endswith("}")):
            return None
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            return None
        if isinstance(data, dict) and ("search" in data or "clarify" in data):
            return data
        return None
