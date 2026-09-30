import logging
from datetime import datetime

from src import config

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
        # id - внутренний номер базы, не источник: увидев его, LLM цитирует «[Источник: ID 140]»
        context = "\n\n".join(
            f"[Источник: {item.source}]\n{item.content}" if item.source.strip() else f"[Фрагмент]\n{item.content}"
            for item in data
        )
        full_prompt = (
            "Ты - официальный консультант Уфимского университета науки и технологий (УУНиТ).\n"
            "Ответь на вопрос пользователя вежливо, точно и структурированно, основываясь "
            "на фактах и контактах из контекста базы знаний ниже.\n"
            "Для фактов из фрагментов с полем 'Источник' укажи его в конце абзаца или пункта строго в "
            "формате [Источник: <как в контексте>]. Фрагменты без источника - проверенные факты базы "
            "знаний: используй их без ссылок и никаких номеров фрагментов не упоминай.\n"
            "Оформляй ответ в Markdown: короткие абзацы, списки, **жирным** - главное.\n"
            "Используй ТОЛЬКО фрагменты, которые прямо отвечают на вопрос. Фрагменты, которые не "
            "относятся к вопросу, полностью игнорируй и не упоминай - даже как 'полезную информацию'.\n"
            "Если ответа на вопрос в контексте нет, честно скажи об этом одной фразой и посоветуй, "
            "куда обратиться: к тьютору или куратору группы, в дирекцию своего института или "
            "деканат факультета. Не придумывай факты.\n"
            "Не здоровайся, сразу переходи к ответу.\n"
            f"Сегодня {datetime.now(config.LOCAL_TZ):%d.%m.%Y}. Если фрагмент - новость, учитывай её дату: "
            "прошедшие события называй прошедшими, не выдавай их за предстоящие.\n"
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
