from src.domain.data import Data


class NewData:
    # TODO: Анализирует Data через AnalyzeDataByLLMForNewData, данные добавляет в хранилище (типа S3),
    #  вопросы из AnalyzeDataByLLMForNewData уходят в векторную базу (типа chromabd).
    #  В векторной базе векторы вопросов линкуют к данным по id
    @staticmethod
    def execute(data: Data) -> bool:
        ...
