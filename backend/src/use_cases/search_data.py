import logging

from src import config
from src.domain.data import Data
from src.domain.official_document import DOCUMENTS_PAGE_URL
from src.logging_utils import preview
from src.services.data_store_service import DataStoreService
from src.services.embedding_service import EmbeddingService
from src.services.vector_search_service import VectorSearchService

logger = logging.getLogger(__name__)

# Порции списка официальных документов (ImportDocuments) - длинные перечни названий, по
# эмбеддингам похожи почти на любой вопрос. Больше двух в выдаче - и они вытесняют фрагменты
# с настоящим ответом («правила пересдачи» -> четыре списка приказов вместо FAQ).
MAX_DOCUMENT_LISTS = 2
_CANDIDATES_FACTOR = 3  # кандидатов на запрос с запасом - на место отброшенных списков


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
        per_query: list[list[int]] = []
        for question in really_question:
            embedding = await self._embedding_service.encode(question)
            ranked: list[int] = []

            searches = [division, None] if division else [None]
            for division_filter in searches:
                scored = await self._vector_search_service.search_with_scores(
                    embedding, self._n_results * _CANDIDATES_FACTOR, division=division_filter
                )
                logger.debug(
                    "SearchDataByListOfStr: по %s (division=%s) сходство: %s",
                    preview(question, 60),
                    division_filter,
                    [(id_, round(score, 3)) for id_, score in scored],
                )
                for id_, score in scored:
                    if score >= config.SEARCH_SIMILARITY_THRESHOLD and id_ not in ranked:
                        ranked.append(id_)
            per_query.append(ranked)

        candidates = list(dict.fromkeys(id_ for ranked in per_query for id_ in ranked))
        by_id = {item.id: item for item in await self._data_store_service.get_many(candidates)}

        # по каждому запросу - до n_results лучших, но списков документов на всю выдачу не больше двух
        result: list[Data] = []
        chosen: set[int] = set()
        lists_taken = 0
        for ranked in per_query:
            taken = 0
            for id_ in ranked:
                item = by_id.get(id_)
                if taken >= self._n_results or item is None:
                    continue
                if id_ in chosen:
                    taken += 1
                    continue
                if item.source.startswith(DOCUMENTS_PAGE_URL):
                    if lists_taken >= MAX_DOCUMENT_LISTS:
                        continue
                    lists_taken += 1
                chosen.add(id_)
                result.append(item)
                taken += 1

        logger.info(
            "SearchDataByListOfStr: итог - %d фрагментов (из них списков документов: %d)", len(result), lists_taken
        )
        return result


class SearchDataById:
    def __init__(self, data_store_service: DataStoreService) -> None:
        self._data_store_service = data_store_service

    async def execute(self, id_: int) -> Data | None:
        data = await self._data_store_service.get(id_)
        logger.debug("SearchDataById: id=%s -> %s", id_, "найдено" if data is not None else "не найдено")
        return data
