import logging

from src import config
from src.domain.data import Data
from src.logging_utils import preview
from src.services.data_store_service import DataStoreService
from src.services.embedding_service import EmbeddingService
from src.services.vector_search_service import VectorSearchService

logger = logging.getLogger(__name__)


class SearchDataByListOfStr:
    """Ищет по embedding'ам вопросов в векторной БД (получает id-ы), затем батчем подтягивает
    сами данные из хранилища (PostgreSQL).

    Если передан division (обнаруженный по ключевым словам в вопросе пользователя), сначала
    приоритетно ищутся документы с этим тегом, а затем - обычный поиск без фильтра как fallback
    (мягкая приоритизация, а не жёсткий фильтр - чтобы неверно определённый или отсутствующий
    у документа тег не давал пустой результат).

    Фрагменты с косинусовым сходством ниже config.SEARCH_SIMILARITY_THRESHOLD отбрасываются:
    лучше честно сказать "в базе нет", чем подсунуть LLM нерелевантный контекст."""

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

    async def execute(self, really_question: list[str], division: str | None = None) -> list[Data]:
        logger.debug("SearchDataByListOfStr: вопросы=%s, division=%s", really_question, division)
        seen: set[int] = set()
        ids: list[int] = []
        for question in really_question:
            embedding = await self._embedding_service.encode(question)

            searches = [division, None] if division else [None]
            for division_filter in searches:
                scored = await self._vector_search_service.search_with_scores(
                    embedding, self._n_results, division=division_filter
                )
                logger.debug(
                    "SearchDataByListOfStr: по %s (division=%s) сходство: %s",
                    preview(question, 60),
                    division_filter,
                    [(id_, round(score, 3)) for id_, score in scored],
                )
                for id_, score in scored:
                    if score >= config.SEARCH_SIMILARITY_THRESHOLD and id_ not in seen:
                        seen.add(id_)
                        ids.append(id_)

        result = await self._data_store_service.get_many(ids)
        logger.info(
            "SearchDataByListOfStr: итог - %d уникальных id, подтянуто %d документов", len(ids), len(result)
        )
        return result


class SearchDataById:
    def __init__(self, data_store_service: DataStoreService) -> None:
        self._data_store_service = data_store_service

    async def execute(self, id_: int) -> Data | None:
        data = await self._data_store_service.get(id_)
        logger.debug("SearchDataById: id=%s -> %s", id_, "найдено" if data is not None else "не найдено")
        return data
