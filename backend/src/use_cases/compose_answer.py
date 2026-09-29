import logging

from src.logging_utils import preview
from src.services.llm_service import LLMService

logger = logging.getLogger(__name__)


class ComposeAnswer:
    """Сводит ответы нескольких частей (расписание, база знаний, маршрут) в один ответ на
    ИСХОДНЫЙ вопрос студента. Нужен, когда вопрос требует связать факты между собой:
    «смогу ли я поспать подольше, если…» не принадлежит ни одной части по отдельности."""

    def __init__(self, llm_service: LLMService) -> None:
        self._llm_service = llm_service

    async def execute(self, question: str, parts: list[str]) -> str:
        facts = "\n\n".join(f"--- Часть {i} ---\n{part}" for i, part in enumerate(parts, start=1))
        prompt = (
            "Ты - консультант УУНиТ. Студент задал вопрос, по нему уже собраны факты из разных "
            "источников (расписание, база знаний, маршрут по кампусу). Составь ОДИН связный ответ.\n"
            "Правила:\n"
            "- Первой фразой прямо ответь на сам вопрос студента (если вопрос «да/нет» - начни с да/нет "
            "и почему), связывая факты между собой.\n"
            "- Потом коротко детали. Используй только факты ниже, ничего не придумывай.\n"
            "- Сохрани пометки [Источник: ...] у фактов, которые используешь.\n"
            "- Шаги маршрута не пересказывай - они будут показаны отдельно под ответом, достаточно "
            "сослаться на маршрут.\n"
            "- Не здоровайся.\n\n"
            f"Вопрос студента: {question}\n\n"
            f"Факты:\n{facts}"
        )
        answer = await self._llm_service.generate(prompt)
        logger.debug("ComposeAnswer: %s", preview(answer))
        return answer
