from src.domain.data import Data


class SearchDataByListOfStr:
    """Будет искать И в chromabd И в S3 через сервисы после -> репо"""

    @staticmethod
    def execute(really_question: list[str]) -> list[Data]:
        ...


class SearchDataById:
    @staticmethod
    def execute(id_: int) -> Data | None:
        ...
