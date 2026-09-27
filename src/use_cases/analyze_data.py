from src.domain.data import Data
from src.services.llm_service import LLMService, parse_string_list


class AnalyzeDataByLLMForUser:
    def __init__(self, llm_service: LLMService) -> None:
        self._llm_service = llm_service

    def execute(self, prompt: str, data: list[Data]) -> str:
        context = "\n\n".join(f"[ID: {item.id} | Источник: {item.source}]\n{item.content}" for item in data)
        full_prompt = (
            "Ты - официальный консультант Уфимского университета науки и технологий (УУНиТ).\n"
            "Ответь на вопрос пользователя вежливо, точно и структурированно, основываясь "
            "на фактах и контактах из контекста базы знаний ниже.\n\n"
            f"Контекст:\n{context}\n\n"
            f"Вопрос: {prompt}"
        )
        return self._llm_service.generate(full_prompt)


class AnalyzeDataByLLMForNewData:
    """Вызывает LLM и просит составить вопросы по data, по которым этот фрагмент можно будет найти.
    Эти вопросы уйдут в векторную бд (используется в NewData)"""

    def __init__(self, llm_service: LLMService) -> None:
        self._llm_service = llm_service

    def execute(self, data: Data) -> list[str]:
        prompt = (
            "К тебе поступает фрагмент базы знаний:\n"
            f"Источник: {data.source}\n"
            f'Содержимое: "{data.content}"\n\n'
            "Сгенерируй ровно 5 различных естественных поисковых вопросов "
            "(коротких, живых, разговорных, с разными формулировками), ответом на которые является этот фрагмент.\n"
            "Верни ответ СТРОГО в формате JSON-массива строк, например:\n"
            '["где найти деканат", "как пройти в кабинет деканата"]'
        )
        raw = self._llm_service.generate(prompt)
        return parse_string_list(raw)
