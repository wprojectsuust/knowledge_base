import logging

from src.domain.data import Data
from src.services.data_store_service import DataStoreService
from src.services.embedding_service import EmbeddingService
from src.services.question_cache_service import QuestionCacheService
from src.services.vector_search_service import VectorSearchService
from src.use_cases.analyze_data import AnalyzeDataByLLMForNewData

logger = logging.getLogger(__name__)


class NewData:
    """Анализирует Data через AnalyzeDataByLLMForNewData, данные добавляет в хранилище (PostgreSQL,
    id присваивается базой), вопросы из AnalyzeDataByLLMForNewData уходят в векторную базу (типа chromabd).
    В векторной базе id векторов линкуют к данным по присвоенному id"""

    def __init__(
        self,
        analyze_data: AnalyzeDataByLLMForNewData,
        embedding_service: EmbeddingService,
        vector_search_service: VectorSearchService,
        data_store_service: DataStoreService,
        question_cache_service: QuestionCacheService | None = None,
    ) -> None:
        self._analyze_data = analyze_data
        self._embedding_service = embedding_service
        self._vector_search_service = vector_search_service
        self._data_store_service = data_store_service
        self._question_cache_service = question_cache_service

    async def execute(self, data: Data) -> int | None:
        logger.info("NewData: начинаю обработку, источник=%s", data.source)
        questions = await self._analyze_data.execute(data)
        if not questions:
            logger.warning("NewData: LLM не сгенерировал вопросов для индексации, данные НЕ сохранены")
            return None

        new_id = await self._data_store_service.save(data)
        logger.info("NewData: сохранено в PostgreSQL, id=%d, division=%s", new_id, data.division)
        for question in questions:
            embedding = await self._embedding_service.encode(question)
            await self._vector_search_service.index(new_id, embedding, division=data.division)
        logger.info("NewData: проиндексировано %d векторов для id=%d", len(questions), new_id)
        if self._question_cache_service is not None:
            # закэшированные «в базе этого нет» могли стать неправдой
            await self._question_cache_service.clear()
        return new_id
