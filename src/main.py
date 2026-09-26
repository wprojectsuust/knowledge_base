from dataclasses import dataclass


@dataclass
class Data:
    id: int
    source: str
    content: str


class Question:
    """Входная точка, оркестратор подзадач"""

    @staticmethod
    def execute(question: str) -> str:
        ...


class GetReallyQuestion:
    """Выделяет реальный вопрос из промпта юзера"""

    @staticmethod
    def execute(question: str) -> str:
        ...


class SearchDataByText:
    """Будет искать И в chromabd И в S3 через сервисы -> репо"""

    @staticmethod
    def execute(really_question: str) -> Data:
        ...


class AnalyzeDataByLLMForUser:
    @staticmethod
    def execute(prompt: str, data: Data) -> str:
        ...


class NewData:
    # TODO: Анализирует Data через AnalyzeDataByLLMForNewData, данные добавляет в хранилище (типа S3),
    #  вопросы из AnalyzeDataByLLMForNewData уходят в векторную базу (типа chromabd).
    #  В векторной базе векторы вопросов линкуют к данным по id
    @staticmethod
    def execute(data: Data) -> bool:
        ...


class SearchDataById:
    @staticmethod
    def execute(id_: int) -> Data | None:
        ...


class RemoveDataById:
    @staticmethod
    def execute(data: Data) -> bool:
        ...


class AnalyzeDataByLLMForNewData:
    # TODO: Вызывает LLM через сервис и просит составить вопросы по data, которые могут быть близки к промпту.
    #  Эти вопросы уйдут в векторную бд. (это в NewData)
    @staticmethod
    def execute(data: Data) -> list[str]:
        ...
