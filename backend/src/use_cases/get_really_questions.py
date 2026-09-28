import logging
import re
from datetime import date

from src.domain.schedule import ScheduleRequest
from src.logging_utils import preview
from src.services.llm_service import LLMService, parse_string_list

logger = logging.getLogger(__name__)

_SCHEDULE_MARKER_RE = re.compile(r"^rasp-(?P<group>.+)-(?P<date>\d{4}-\d{2}-\d{2})$")


class GetReallyQuestions:
    """Разбирает сообщение пользователя: либо это запрос расписания конкретной группы на
    конкретную дату (тогда возвращается ScheduleRequest), либо обычный вопрос - тогда
    выделяются реальные поисковые вопросы для векторного поиска (list[str]).

    Обе задачи решаются одним LLM-вызовом, а не двумя - чтобы не удваивать токены на
    каждый вопрос ради проверки "это не про расписание?"."""

    def __init__(self, llm_service: LLMService) -> None:
        self._llm_service = llm_service

    async def execute(self, question: str) -> list[str] | ScheduleRequest:
        logger.debug("GetReallyQuestions: вход=%s", preview(question))
        today = date.today().isoformat()
        prompt = (
            "Пользователь написал сообщение консультанту УУНиТ.\n"
            f'Сообщение: "{question}"\n\n'
            "Если сообщение - вопрос о расписании конкретной учебной группы на конкретную дату, "
            "ответь СТРОГО одной строкой в формате: rasp-<группа>-<дата в формате YYYY-MM-DD>\n"
            f"Сегодня {today}. Относительные даты ('завтра', 'послезавтра', день недели) "
            "разрешай сам в абсолютную дату.\n"
            "Пример: rasp-1-1.1.1.-26А-2026-09-30\n\n"
            "Иначе - выдели из сообщения реальные поисковые вопросы, по которым можно найти "
            "ответ в базе знаний вуза, и верни ответ СТРОГО в формате JSON-массива строк, "
            "например:\n"
            '["где находится деканат", "как записаться на пересдачу"]'
        )
        raw = await self._llm_service.generate(prompt)

        schedule_request = self._parse_schedule_marker(raw)
        if schedule_request is not None:
            logger.debug("GetReallyQuestions: обнаружен запрос расписания %s", schedule_request)
            return schedule_request

        really_questions = parse_string_list(raw)
        logger.debug("GetReallyQuestions: выделено %d вопросов: %s", len(really_questions), really_questions)
        return really_questions

    @staticmethod
    def _parse_schedule_marker(raw: str) -> ScheduleRequest | None:
        match = _SCHEDULE_MARKER_RE.match(raw.strip())
        if not match:
            return None
        return ScheduleRequest(group=match.group("group"), date=match.group("date"))
