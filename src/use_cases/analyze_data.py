from src.domain.data import Data


class AnalyzeDataByLLMForUser:
    @staticmethod
    def execute(prompt: str, data: list[Data]) -> str:
        ...


class AnalyzeDataByLLMForNewData:
    # TODO: Вызывает LLM через сервис и просит составить вопросы по data, которые могут быть близки к промпту.
    #  Эти вопросы уйдут в векторную бд. (это в NewData)
    @staticmethod
    def execute(data: Data) -> list[str]:
        ...
