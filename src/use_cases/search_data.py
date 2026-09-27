from src.domain.data import Data
from src.services.data_store_service import DataStoreService
from src.services.embedding_service import EmbeddingService
from src.services.vector_search_service import VectorSearchService


class SearchDataByListOfStr:
    """Ищет по embedding'ам вопросов в векторной БД (получает id-ы), затем батчем подтягивает
    сами данные из хранилища (типа S3)"""

    def __init__(
        self,
        embedding_service: EmbeddingService,
        vector_search_service: VectorSearchService,
        data_store_service: DataStoreService,
        n_results: int = 6,
    ) -> None:
        self._embedding_service = embedding_service
        self._vector_search_service = vector_search_service
        self._data_store_service = data_store_service
        self._n_results = n_results

    def execute(self, really_question: list[str]) -> list[Data]:
        seen: set[int] = set()
        ids: list[int] = []
        for question in really_question:
            embedding = self._embedding_service.encode(question)
            for id_ in self._vector_search_service.search(embedding, self._n_results):
                if id_ not in seen:
                    seen.add(id_)
                    ids.append(id_)
        return self._data_store_service.get_many(ids)


class SearchDataById:
    def __init__(self, data_store_service: DataStoreService) -> None:
        self._data_store_service = data_store_service

    def execute(self, id_: int) -> Data | None:
        return self._data_store_service.get(id_)
