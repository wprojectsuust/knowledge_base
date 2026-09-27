import logging

from src.domain.data import Data
from src.logging_utils import preview
from src.services.llm_service import LLMService, parse_string_list

logger = logging.getLogger(__name__)


class AnalyzeDataByLLMForUser:
    def __init__(self, llm_service: LLMService) -> None:
        self._llm_service = llm_service

    async def execute(self, prompt: str, data: list[Data]) -> str:
        logger.debug(
            "AnalyzeDataByLLMForUser: вопрос=%s, найдено документов=%d, id=%s",
            preview(prompt),
            len(data),
            [item.id for item in data],
        )
        context = "\n\n".join(f"[ID: {item.id} | Источник: {item.source}]\n{item.content}" for item in data)
        full_prompt = (
            "Ты - официальный консультант Уфимского университета науки и технологий (УУНиТ).\n"
            "Ответь на вопрос пользователя вежливо, точно и структурированно, основываясь "
            "на фактах и контактах из контекста базы знаний ниже.\n"
            "Обязательно укажи источник (поле 'Источник' у соответствующего фрагмента контекста) "
            "для каждого факта, который используешь в ответе.\n"
            "Ответы кэшируются и могут быть показаны другому пользователю - поэтому НЕ обращайся "
            "к пользователю по имени и не упоминай никакую личную информацию о нём, даже если "
            "она есть в вопросе.\n\n"
            f"Контекст:\n{context}\n\n"
            f"Вопрос: {prompt}"
        )
        answer = await self._llm_service.generate(full_prompt)
        logger.debug("AnalyzeDataByLLMForUser: ответ=%s", preview(answer))
        return answer


class AnalyzeDataByLLMForNewData:
    """Вызывает LLM и просит составить вопросы по data, по которым этот фрагмент можно будет найти.
    Эти вопросы уйдут в векторную бд (используется в NewData)"""

    def __init__(self, llm_service: LLMService) -> None:
        self._llm_service = llm_service

    async def execute(self, data: Data) -> list[str]:
        logger.debug("AnalyzeDataByLLMForNewData: источник=%s содержимое=%s", data.source, preview(data.content))
        prompt = (
            "К тебе поступает фрагмент базы знаний:\n"
            f"Источник: {data.source}\n"
            f'Содержимое: "{data.content}"\n\n'
            "Сгенерируй ровно 5 различных естественных поисковых вопросов "
            "(коротких, живых, разговорных, с разными формулировками), ответом на которые является этот фрагмент.\n"
            "Верни ответ СТРОГО в формате JSON-массива строк, например:\n"
            '["где найти деканат", "как пройти в кабинет деканата"]'
        )
        raw = await self._llm_service.generate(prompt)
        questions = parse_string_list(raw)
        logger.debug("AnalyzeDataByLLMForNewData: сгенерировано %d вопросов: %s", len(questions), questions)
        return questions
