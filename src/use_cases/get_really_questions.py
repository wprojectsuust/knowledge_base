import logging

from src.logging_utils import preview
from src.services.llm_service import LLMService, parse_string_list

logger = logging.getLogger(__name__)


class GetReallyQuestions:
    """Выделяет реальные вопросы из промпта юзера - они же будут потом превращаться в embending и искаться в
    векторной базе"""

    def __init__(self, llm_service: LLMService) -> None:
        self._llm_service = llm_service

    def execute(self, question: str) -> list[str]:
        logger.debug("GetReallyQuestions: вход=%s", preview(question))
        prompt = (
            "Пользователь написал сообщение консультанту УУНиТ. Выдели из него реальные "
            "поисковые вопросы, по которым можно найти ответ в базе знаний вуза.\n"
            f'Сообщение: "{question}"\n\n'
            "Верни ответ СТРОГО в формате JSON-массива строк, например:\n"
            '["где находится деканат", "как записаться на пересдачу"]'
        )
        raw = self._llm_service.generate(prompt)
        really_questions = parse_string_list(raw)
        logger.debug("GetReallyQuestions: выделено %d вопросов: %s", len(really_questions), really_questions)
        return really_questions
