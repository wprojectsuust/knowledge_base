import logging

from src.domain.schedule import DaySchedule
from src.logging_utils import preview
from src.services.llm_service import LLMService

logger = logging.getLogger(__name__)


class AnalyzeScheduleForUser:
    """Отвечает на вопрос пользователя по расписанию, используя факты (время/предмет/кабинет,
    как добраться) как контекст - ничего не придумывает сверх них.

    Если вопрос конкретный ("во сколько заканчиваются пары", "какая пара следующая") - отвечает
    по существу, а не перечисляет весь день. Если вопрос общий ("какое у меня расписание") -
    перечисляет все пары по порядку, как раньше."""

    def __init__(self, llm_service: LLMService) -> None:
        self._llm_service = llm_service

    async def execute(self, question: str, day_schedule: DaySchedule, directions: dict[str, str]) -> str:
        lessons_block = "\n".join(
            f"- {lesson.time}: {lesson.subject}" + (f" ({lesson.venue})" if lesson.venue else "")
            for lesson in day_schedule.lessons
        )
        directions_block = "\n".join(f"{venue}: {text}" for venue, text in directions.items())

        prompt = (
            "Ты - консультант УУНиТ по расписанию. Ниже факты о расписании студента, ничего "
            "от себя не придумывай, используй только их:\n\n"
            f"Группа: {day_schedule.group}\n"
            f"День: {day_schedule.day_label}\n"
            f"Пары:\n{lessons_block}\n"
            + (f"\nКак добраться:\n{directions_block}\n" if directions_block else "")
            + "\n"
            "Ответь на вопрос студента ТОЧНО на то, что он спросил. Если вопрос конкретный "
            "(например, во сколько заканчиваются или начинаются пары, какая пара следующая, "
            "в каком кабинете конкретная пара) - отвечай коротко и по делу, без перечисления "
            "всего дня. Если вопрос общий ('какое у меня расписание', 'что у меня сегодня') - "
            "перечисли все пары по порядку.\n\n"
            f"Вопрос: {question}"
        )
        logger.debug("AnalyzeScheduleForUser: вопрос=%s", preview(question))
        answer = await self._llm_service.generate(prompt)
        logger.debug("AnalyzeScheduleForUser: ответ=%s", preview(answer))
        return answer
