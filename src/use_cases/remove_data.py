from src.services.data_store_service import DataStoreService
from src.services.vector_search_service import VectorSearchService


class RemoveDataById:
    def __init__(self, data_store_service: DataStoreService, vector_search_service: VectorSearchService) -> None:
        self._data_store_service = data_store_service
        self._vector_search_service = vector_search_service

    async def execute(self, id_: int) -> bool:
        await self._data_store_service.remove(id_)
        self._vector_search_service.remove(id_)
        return True
