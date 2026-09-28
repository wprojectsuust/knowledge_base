import logging
import re
from datetime import date

from src.domain.clarification import ClarificationRequest
from src.domain.route import RouteRequest
from src.domain.schedule import ScheduleRequest
from src.logging_utils import preview
from src.services.llm_service import LLMService, parse_string_list

logger = logging.getLogger(__name__)

_SCHEDULE_MARKER_RE = re.compile(r"^rasp-(?P<group>.+)-(?P<date>\d{4}-\d{2}-\d{2})$")
_ROUTE_MARKER_RE = re.compile(r"^route:\s*(?:(?P<source>.+?)\s*->\s*)?(?P<target>.+)$", re.IGNORECASE)
_CLARIFY_MARKER_RE = re.compile(r"^clarify-(?P<field>[a-z_]+):\s*(?P<question>.+)$", re.DOTALL)

_CLARIFY_INSTRUCTION = (
    "Если студент просит СВОИ конкретные данные (например, 'какое у меня завтра расписание', "
    "'во сколько кончаются мои пары'), а нужных сведений о нём нет ни в сообщении, ни в блоке "
    "'Известно о студенте', ответь СТРОГО одной строкой: clarify-<поле>: <короткий вежливый вопрос>\n"
    "НЕ уточняй, если это общий вопрос о том, как что-то сделать или где что-то найти - ответ на "
    "него одинаков для всех: 'как узнать расписание своей группы', 'что делать, если пропустил "
    "пару', 'где мой деканат' - это обычный поиск по базе знаний.\n"
    "Поле - латиницей: group (учебная группа), faculty (факультет или институт), "
    "course (курс) или другое подходящее слово.\n"
    "Пример: clarify-group: В какой группе вы учитесь?\n"
    "Не уточняй то, без чего можно ответить в общем виде.\n\n"
)


class GetReallyQuestions:
    """Разбирает сообщение пользователя. Возможные исходы:
    - запрос расписания конкретной группы на конкретную дату -> ScheduleRequest;
    - для ответа не хватает сведений о студенте (например, группы) -> ClarificationRequest;
    - обычный вопрос -> реальные поисковые вопросы для векторного поиска (list[str]).

    Всё решается одним LLM-вызовом, а не несколькими - чтобы не умножать токены на
    каждый вопрос ради проверок "это не про расписание?" / "всего ли хватает?"."""

    def __init__(self, llm_service: LLMService, places_hint: str = "") -> None:
        self._llm_service = llm_service
        # какие места есть на карте кампуса и как их называть в маркере route (см. CampusService)
        self._places_hint = places_hint

    async def execute(self, question: str, can_clarify: bool = True) -> list[str] | ScheduleRequest | ClarificationRequest | RouteRequest:
        logger.debug("GetReallyQuestions: вход=%s", preview(question))
        today = date.today().isoformat()
        prompt = (
            "Пользователь написал сообщение консультанту УУНиТ.\n"
            f'Сообщение: "{question}"\n\n'
            "Если сообщение - вопрос о расписании конкретной учебной группы на конкретную дату, "
            "ответь СТРОГО одной строкой в формате: rasp-<группа>-<дата в формате YYYY-MM-DD>\n"
            f"Сегодня {today}. Относительные даты ('завтра', 'послезавтра', день недели) "
            "разрешай сам в абсолютную дату.\n"
            "Группу приводи к официальному формату ИСУ: заглавные буквы, дефис между буквами и "
            "цифрами, как в справочнике (например 'топ106б' -> ТОП-106Б).\n"
            "Пример: rasp-1-1.1.1.-26А-2026-09-30\n\n"
            + self._route_instruction()
            + (_CLARIFY_INSTRUCTION if can_clarify else "")
            + "Иначе - выдели из сообщения реальные поисковые вопросы, по которым можно найти "
            "ответ в базе знаний вуза, и верни ответ СТРОГО в формате JSON-массива строк, "
            "например:\n"
            '["где находится деканат", "как записаться на пересдачу"]'
        )
        raw = await self._llm_service.generate(prompt)

        schedule_request = self._parse_schedule_marker(raw)
        if schedule_request is not None:
            logger.debug("GetReallyQuestions: обнаружен запрос расписания %s", schedule_request)
            return schedule_request

        route_request = self._parse_route_marker(raw)
        if route_request is not None:
            logger.debug("GetReallyQuestions: запрос маршрута %s", route_request)
            return route_request

        clarification = self._parse_clarify_marker(raw) if can_clarify else None
        if clarification is not None:
            logger.debug("GetReallyQuestions: нужно уточнение %s", clarification)
            return clarification

        really_questions = parse_string_list(raw)
        logger.debug("GetReallyQuestions: выделено %d вопросов: %s", len(really_questions), really_questions)
        return really_questions

    @staticmethod
    def _parse_schedule_marker(raw: str) -> ScheduleRequest | None:
        match = _SCHEDULE_MARKER_RE.match(raw.strip())
        if not match:
            return None
        return ScheduleRequest(group=match.group("group"), date=match.group("date"))

    @staticmethod
    def _parse_clarify_marker(raw: str) -> ClarificationRequest | None:
        match = _CLARIFY_MARKER_RE.match(raw.strip())
        if not match:
            return None
        return ClarificationRequest(field=match.group("field"), question=match.group("question").strip())

    def _route_instruction(self) -> str:
        places = f"Известные места:\n{self._places_hint}\n" if self._places_hint else ""
        return (
            "Если студент спрашивает, как пройти/дойти/добраться до места на территории "
            "(кабинет, корпус, буфет, библиотека...), ответь СТРОГО одной строкой:\n"
            "route: <откуда> -> <куда>\n"
            "Если откуда не сказано - только route: <куда> (тогда маршрут от КПП).\n"
            "Обозначения: kpp - КПП; 7-404 - кабинет 404 в корпусе 7; 7 - вход в корпус 7; "
            "7@3 - 3 этаж корпуса 7; place:<id> - место из списка ниже.\n"
            f"{places}"
            "Пример: 'как пройти из 7-404 в 1-101' -> route: 7-404 -> 1-101\n\n"
        )

    @staticmethod
    def _parse_route_marker(raw: str) -> RouteRequest | None:
        match = _ROUTE_MARKER_RE.match(raw.strip())
        if not match:
            return None
        source = match.group("source")
        return RouteRequest(source=source.strip() if source else None, target=match.group("target").strip())
