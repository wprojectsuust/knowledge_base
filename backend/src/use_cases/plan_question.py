import json
import logging
import re
from datetime import date, datetime

from src import config

from src.domain.clarification import ClarificationRequest
from src.domain.dialog import DialogTurn, format_history
from src.domain.event import TOPICS, normalize_topic
from src.domain.plan import EventsTask, QuestionPlan, SearchTask
from src.domain.route import RouteRequest
from src.domain.schedule import ScheduleRequest
from src.logging_utils import preview
from src.services.llm_service import LLMService

logger = logging.getLogger(__name__)

_WEEKDAYS = ("понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье")

_REPLY_RULES = (
    '- "reply": "<готовый ответ>" - ТОЛЬКО если ответ целиком выводится из диалога выше и текущих даты и '
    "времени, без новых сведений о вузе: уточнение или пересчёт прошлого ответа («через сколько это?», «а во "
    "сколько начинается первая?», «сколько это в минутах?», «повтори номер кабинета»), благодарность, "
    "приветствие, «что ты умеешь». Тогда все остальные ключи - null.\n"
    "  Не отвечай сам на вопросы о вузе (правила, сроки, места, люди, документы, расписание на другой день), "
    "даже если уверен в ответе, - это search/schedule/route: факты берутся только из базы знаний. Если в "
    "сообщении есть хоть одна такая часть - reply null. Сомневаешься - reply null.\n"
)

_EVENTS_RULES = (
    '- "events": {"question": "<что спросили о мероприятиях>", "keywords": ["<0-3 основы слов из названия '
    'события, например хакатон, олимпиад, концерт>"], "date_from": "YYYY-MM-DD или null", "date_to": '
    '"YYYY-MM-DD или null", "topic": "<тематика или null>"} - вопросы о мероприятиях вуза: что проходит, '
    "какие будут/были конкурсы, олимпиады, хакатоны, фестивали, конференции, концерты, когда и где событие. "
    "Ищется в каталоге мероприятий (там даты и тематики), не в базе знаний. «На этой неделе», «в октябре» - "
    "переведи в даты; без указания времени - даты null. keywords пусты, если спросили вообще («какие есть "
    f"мероприятия»). Тематика - одна из: {', '.join(TOPICS[:-1])}.\n"
    "  Как участвовать, правила, стипендии и документы - это search (можно вместе с events).\n"
)

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
        keys = '"reply", "search", "schedule", "route", "events"' + (', "clarify"' if can_clarify else "")
        now = datetime.now(config.LOCAL_TZ)
        return (
            "Ты - планировщик консультанта УУНиТ. Разбери сообщение студента на части, которые нужно "
            "выполнить, чтобы на него ответить.\n\n"
            f"{dialog}"
            f'Сообщение: "{question}"\n\n'
            f"Ответь СТРОГО одним JSON-объектом с ключами {keys}. Ключ, который не нужен, - null. "
            "Нужных частей может быть несколько сразу.\n"
            '- "search": {"question": "<самостоятельная формулировка части сообщения, на которую отвечает '
            'база знаний вуза>", "queries": ["<2-4 коротких поисковых запроса>"]} - запросы - перефразировки '
            "вопроса простыми словами и синонимами, не придумывай новых тем («телефон садится» -> «где зарядить "
            "телефон», а не «IT-отдел вуза»). Для любых вопросов "
            "об учёбе, документах, подразделениях, правилах.\n"
            '- "schedule": {"group": "<группа>", "date": "YYYY-MM-DD", "question": "<что именно спросили '
            'про расписание>"} - расписание КОНКРЕТНОЙ группы на КОНКРЕТНУЮ дату.\n'
            f"  Сегодня {now.date().isoformat()} ({_WEEKDAYS[now.weekday()]}), сейчас {now:%H:%M}. Относительные даты ('завтра', день недели) переводи в "
            "абсолютные. Группу приводи к формату ИСУ: заглавные буквы, дефис между буквами и цифрами "
            "('топ106б' -> ТОП-106Б).\n"
            '- "route": {"from": "<откуда или null - тогда от КПП>", "to": "<куда>"} - ТОЛЬКО если прямо '
            "спрашивают, как пройти/дойти/добраться до места на территории («где деканат» - это search, "
            "не route). Обозначения: kpp - КПП; 7-404 - кабинет 404 в корпусе 7; 7 - корпус 7; 7@3 - 3 этаж "
            "корпуса 7; place:<id> - ТОЛЬКО id из списка ниже, свои не придумывай.\n"
            f"{places}"
            + _EVENTS_RULES
            + (_CLARIFY_RULES if can_clarify else "")
            + _REPLY_RULES
            + "\nВсе формулировки - самостоятельные, понятные без диалога. В question части сохраняй "
            "смысл и условия студента целиком («смогу ли я поспать подольше, если…», а не просто "
            "«какие пары»).\n"
            'Пример: "какие завтра пары у ТОП-106Б и где деканат ФИРТ" -> {"search": {"question": '
            '"где находится деканат ФИРТ", "queries": ["деканат ФИРТ", "где деканат ФИРТ"]}, "schedule": '
            '{"group": "ТОП-106Б", "date": "<завтра>", "question": "какие пары"}, "route": null, "events": null, "reply": null'
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

        events = None
        if isinstance(raw_events := data.get("events"), dict):
            events = EventsTask(
                question=str(raw_events.get("question") or "").strip() or question,
                keywords=tuple(
                    str(word).strip().lower() for word in raw_events.get("keywords") or [] if str(word).strip()
                )[:3],
                date_from=_parse_date(raw_events.get("date_from")),
                date_to=_parse_date(raw_events.get("date_to")),
                topic=topic if (topic := normalize_topic(raw_events.get("topic"))) != "Другое" else None,
            )

        clarification = None
        if can_clarify and isinstance(raw_clarify := data.get("clarify"), dict):
            field = str(raw_clarify.get("field") or "").strip()
            clarify_question = str(raw_clarify.get("question") or "").strip()
            if _FIELD.match(field) and clarify_question:
                clarification = ClarificationRequest(field=field, question=clarify_question)

        plan = QuestionPlan(
            search=search, schedule=schedule, route=route, events=events, clarification=clarification
        )
        reply = str(data.get("reply") or "").strip()
        if reply and plan == QuestionPlan():
            # ответ из диалога - только когда больше ничего не нужно: «спасибо, а где деканат?» - это search
            return QuestionPlan(reply=reply)
        return plan if plan != QuestionPlan() else fallback


def _parse_date(value) -> date | None:
    text = str(value or "").strip()
    if not _ISO_DATE.match(text):
        return None
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None
