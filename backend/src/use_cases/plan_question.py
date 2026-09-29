import json
import logging
import re
from datetime import datetime

from src import config

from src.domain.clarification import ClarificationRequest
from src.domain.dialog import DialogTurn, format_history
from src.domain.plan import QuestionPlan, SearchTask
from src.domain.route import RouteRequest
from src.domain.schedule import ScheduleRequest
from src.logging_utils import preview
from src.services.llm_service import LLMService

logger = logging.getLogger(__name__)

_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_FIELD = re.compile(r"^[a-z_]+$")

_CLARIFY_RULES = (
    '- "clarify": {"field": "<поле латиницей>", "question": "<короткий вежливый вопрос>"} - ТОЛЬКО если '
    "студент просит СВОИ конкретные данные ('какое у меня завтра расписание', 'во сколько кончаются мои "
    "пары'), а нужных сведений о нём нет ни в сообщении, ни в блоке 'Известно о студенте', ни в диалоге. "
    "Поле: group (учебная группа), faculty (факультет или институт), course (курс) или другое слово.\n"
    "  НЕ уточняй общие вопросы о том, как что-то сделать или где найти - ответ одинаков для всех: "
    "'как узнать расписание своей группы', 'что делать, если пропустил пару', 'где мой деканат' - "
    "это search.\n"
)


class PlanQuestion:
    """Разбирает сообщение студента в план (QuestionPlan): какие части нужны для ответа - поиск
    по базе знаний, расписание группы на дату, маршрут по кампусу, уточнение сведений о студенте.
    В одном сообщении их может быть несколько сразу.

    Всё решается ОДНИМ LLM-вызовом: и классификация, и разбиение на части, и перефразирование
    с учётом диалога («а туда как пройти?» -> маршрут до места из прошлого ответа)."""

    def __init__(self, llm_service: LLMService, places_hint: str = "") -> None:
        self._llm_service = llm_service
        # какие места есть на карте кампуса и как их называть в route (см. CampusService)
        self._places_hint = places_hint

    async def execute(
        self, question: str, can_clarify: bool = True, history: list[DialogTurn] | None = None
    ) -> QuestionPlan:
        logger.debug("PlanQuestion: вход=%s, реплик в истории=%d", preview(question), len(history or []))
        raw = await self._llm_service.generate(self._prompt(question, can_clarify, history or []))
        plan = self._parse(raw, question, can_clarify)
        logger.debug("PlanQuestion: план=%s", plan)
        return plan

    def _prompt(self, question: str, can_clarify: bool, history: list[DialogTurn]) -> str:
        dialog = (
            "Предыдущие сообщения этого чата (только для понимания контекста - «туда», «он», "
            f"«а завтра?»; отвечать на них не нужно):\n{format_history(history)}\n\n"
            if history
            else ""
        )
        places = f"  Известные места:\n{self._places_hint}\n" if self._places_hint else ""
        keys = '"search", "schedule", "route"' + (', "clarify"' if can_clarify else "")
        return (
            "Ты - планировщик консультанта УУНиТ. Разбери сообщение студента на части, которые нужно "
            "выполнить, чтобы на него ответить.\n\n"
            f"{dialog}"
            f'Сообщение: "{question}"\n\n'
            f"Ответь СТРОГО одним JSON-объектом с ключами {keys}. Ключ, который не нужен, - null. "
            "Нужных частей может быть несколько сразу.\n"
            '- "search": {"question": "<самостоятельная формулировка части сообщения, на которую отвечает '
            'база знаний вуза>", "queries": ["<2-4 коротких поисковых запроса>"]} - для любых вопросов '
            "об учёбе, документах, подразделениях, правилах.\n"
            '- "schedule": {"group": "<группа>", "date": "YYYY-MM-DD", "question": "<что именно спросили '
            'про расписание>"} - расписание КОНКРЕТНОЙ группы на КОНКРЕТНУЮ дату.\n'
            f"  Сегодня {datetime.now(config.LOCAL_TZ).date().isoformat()}. Относительные даты ('завтра', день недели) переводи в "
            "абсолютные. Группу приводи к формату ИСУ: заглавные буквы, дефис между буквами и цифрами "
            "('топ106б' -> ТОП-106Б).\n"
            '- "route": {"from": "<откуда или null - тогда от КПП>", "to": "<куда>"} - ТОЛЬКО если прямо '
            "спрашивают, как пройти/дойти/добраться до места на территории («где деканат» - это search, "
            "не route). Обозначения: kpp - КПП; 7-404 - кабинет 404 в корпусе 7; 7 - корпус 7; 7@3 - 3 этаж "
            "корпуса 7; place:<id> - ТОЛЬКО id из списка ниже, свои не придумывай.\n"
            f"{places}"
            + (_CLARIFY_RULES if can_clarify else "")
            + "\nВсе формулировки - самостоятельные, понятные без диалога. В question части сохраняй "
            "смысл и условия студента целиком («смогу ли я поспать подольше, если…», а не просто "
            "«какие пары»).\n"
            'Пример: "какие завтра пары у ТОП-106Б и где деканат ФИРТ" -> {"search": {"question": '
            '"где находится деканат ФИРТ", "queries": ["деканат ФИРТ", "где деканат ФИРТ"]}, "schedule": '
            '{"group": "ТОП-106Б", "date": "<завтра>", "question": "какие пары"}, "route": null'
            + (', "clarify": null' if can_clarify else "")
            + "}"
        )

    @staticmethod
    def _parse(raw: str, question: str, can_clarify: bool) -> QuestionPlan:
        fallback = QuestionPlan(search=SearchTask(question=question, queries=(question,)))
        start, end = raw.find("{"), raw.rfind("}")
        if start == -1 or end <= start:
            logger.warning("PlanQuestion: LLM не выдержала формат, ищу по исходному тексту: %s", preview(raw))
            return fallback
        try:
            data = json.loads(raw[start : end + 1])
        except json.JSONDecodeError:
            logger.warning("PlanQuestion: невалидный JSON, ищу по исходному тексту: %s", preview(raw))
            return fallback
        if not isinstance(data, dict):
            return fallback

        search = None
        if isinstance(raw_search := data.get("search"), dict):
            queries = tuple(str(q).strip() for q in raw_search.get("queries") or [] if str(q).strip())
            search_question = str(raw_search.get("question") or "").strip() or question
            search = SearchTask(question=search_question, queries=queries or (search_question,))

        schedule = None
        if isinstance(raw_schedule := data.get("schedule"), dict):
            group = str(raw_schedule.get("group") or "").strip()
            day = str(raw_schedule.get("date") or "").strip()
            if group and _ISO_DATE.match(day):
                schedule = ScheduleRequest(group=group, date=day, question=str(raw_schedule.get("question") or "").strip())

        route = None
        if isinstance(raw_route := data.get("route"), dict) and str(raw_route.get("to") or "").strip():
            source = raw_route.get("from")
            route = RouteRequest(source=str(source).strip() if source else None, target=str(raw_route["to"]).strip())

        clarification = None
        if can_clarify and isinstance(raw_clarify := data.get("clarify"), dict):
            field = str(raw_clarify.get("field") or "").strip()
            clarify_question = str(raw_clarify.get("question") or "").strip()
            if _FIELD.match(field) and clarify_question:
                clarification = ClarificationRequest(field=field, question=clarify_question)

        plan = QuestionPlan(search=search, schedule=schedule, route=route, clarification=clarification)
        return plan if plan != QuestionPlan() else fallback
