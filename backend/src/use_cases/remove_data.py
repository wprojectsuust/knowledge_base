import logging

from src.services.data_store_service import DataStoreService
from src.services.question_cache_service import QuestionCacheService
from src.services.vector_search_service import VectorSearchService

logger = logging.getLogger(__name__)


class RemoveDataById:
    def __init__(
        self,
        data_store_service: DataStoreService,
        vector_search_service: VectorSearchService,
        question_cache_service: QuestionCacheService | None = None,
    ) -> None:
        self._data_store_service = data_store_service
        self._vector_search_service = vector_search_service
        self._question_cache_service = question_cache_service

    async def execute(self, id_: int) -> bool:
        logger.info("RemoveDataById: удаляю id=%s (PostgreSQL + Chroma)", id_)
        await self._data_store_service.remove(id_)
        await self._vector_search_service.remove(id_)
        if self._question_cache_service is not None:
            # ответы, собранные по удалённому документу, больше не верны
            await self._question_cache_service.clear()
        return True
