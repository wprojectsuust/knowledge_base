import logging

from src.domain.data import Data
from src.services.data_store_service import DataStoreService
from src.services.embedding_service import EmbeddingService
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
    ) -> None:
        self._analyze_data = analyze_data
        self._embedding_service = embedding_service
        self._vector_search_service = vector_search_service
        self._data_store_service = data_store_service

    async def execute(self, data: Data) -> int | None:
        logger.info("NewData: начинаю обработку, источник=%s", data.source)
        questions = self._analyze_data.execute(data)
        if not questions:
            logger.warning("NewData: LLM не сгенерировал вопросов для индексации, данные НЕ сохранены")
            return None

        new_id = await self._data_store_service.save(data)
        logger.info("NewData: сохранено в PostgreSQL, id=%d, division=%s", new_id, data.division)
        for question in questions:
            embedding = self._embedding_service.encode(question)
            await self._vector_search_service.index(new_id, embedding, division=data.division)
        logger.info("NewData: проиндексировано %d векторов для id=%d", len(questions), new_id)
        return new_id
