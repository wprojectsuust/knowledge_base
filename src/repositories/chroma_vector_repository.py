from __future__ import annotations

import logging
from uuid import uuid4

logger = logging.getLogger(__name__)


class ChromaVectorRepository:
    """VectorRepository поверх персистентного локального ChromaDB.

    Хранит только id+embedding (+ опциональный division-тег в metadata): один data_id
    может быть проиндексирован несколькими векторами (по числу сгенерированных вопросов),
    поэтому у каждого вектора свой уникальный chroma-id, а data_id (и, если задан, division)
    лежат в metadata и используются для группировки/фильтрации и удаления."""

    def __init__(self, persist_path: str, collection_name: str = "uunit_knowledge") -> None:
        import chromadb

        logger.info("Chroma: открываю персистентный клиент path=%s collection=%s", persist_path, collection_name)
        self._client = chromadb.PersistentClient(path=persist_path)
        self._collection = self._client.get_or_create_collection(collection_name)
        logger.info("Chroma: коллекция готова, векторов в ней: %d", self._collection.count())

    def query(self, embedding: list[float], n_results: int = 6, division: str | None = None) -> list[int]:
        count = self._collection.count()
        logger.debug(
            "Chroma query: в коллекции %d векторов, n_results=%d, division=%s", count, n_results, division
        )
        if count == 0:
            return []

        where = {"division": division} if division else None
        results = self._collection.query(query_embeddings=[embedding], n_results=min(n_results, count), where=where)
        found_ids = [int(metadata["data_id"]) for metadata in results["metadatas"][0]]
        logger.debug("Chroma query: найдено data_id=%s", found_ids)
        return found_ids

    def add(self, id_: int, embedding: list[float], division: str | None = None) -> None:
        vector_id = f"{id_}-{uuid4().hex}"
        metadata: dict[str, int | str] = {"data_id": id_}
        if division:
            metadata["division"] = division
        logger.debug("Chroma add: data_id=%s vector_id=%s division=%s", id_, vector_id, division)
        self._collection.add(ids=[vector_id], embeddings=[embedding], metadatas=[metadata])

    def delete(self, id_: int) -> None:
        logger.debug("Chroma delete: data_id=%s", id_)
        self._collection.delete(where={"data_id": id_})
