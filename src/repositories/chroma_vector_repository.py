from __future__ import annotations

from uuid import uuid4


class ChromaVectorRepository:
    """VectorRepository поверх персистентного локального ChromaDB.

    Хранит только id+embedding: один data_id может быть проиндексирован несколькими
    векторами (по числу сгенерированных вопросов), поэтому у каждого вектора свой
    уникальный chroma-id, а data_id лежит в metadata и используется для группировки
    и удаления."""

    def __init__(self, persist_path: str, collection_name: str = "uunit_knowledge") -> None:
        import chromadb

        self._client = chromadb.PersistentClient(path=persist_path)
        self._collection = self._client.get_or_create_collection(collection_name)

    def query(self, embedding: list[float], n_results: int = 6) -> list[int]:
        count = self._collection.count()
        if count == 0:
            return []

        results = self._collection.query(query_embeddings=[embedding], n_results=min(n_results, count))
        return [int(metadata["data_id"]) for metadata in results["metadatas"][0]]

    def add(self, id_: int, embedding: list[float]) -> None:
        vector_id = f"{id_}-{uuid4().hex}"
        self._collection.add(ids=[vector_id], embeddings=[embedding], metadatas=[{"data_id": id_}])

    def delete(self, id_: int) -> None:
        self._collection.delete(where={"data_id": id_})
