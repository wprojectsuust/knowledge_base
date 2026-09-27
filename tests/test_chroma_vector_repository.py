import sys
import types
from unittest.mock import MagicMock


def _install_fake_chromadb() -> MagicMock:
    fake_collection = MagicMock()
    fake_client = MagicMock()
    fake_client.get_or_create_collection.return_value = fake_collection

    fake_module = types.ModuleType("chromadb")
    fake_module.PersistentClient = MagicMock(return_value=fake_client)
    sys.modules["chromadb"] = fake_module
    return fake_collection


def test_query_returns_data_ids_from_metadata() -> None:
    fake_collection = _install_fake_chromadb()
    fake_collection.count.return_value = 2
    fake_collection.query.return_value = {"metadatas": [[{"data_id": 1}, {"data_id": 2}]]}

    from src.repositories.chroma_vector_repository import ChromaVectorRepository

    repo = ChromaVectorRepository(persist_path="/tmp/whatever")

    result = repo.query([0.1, 0.2], n_results=6)

    assert result == [1, 2]
    fake_collection.query.assert_called_once_with(query_embeddings=[[0.1, 0.2]], n_results=2)


def test_query_returns_empty_when_collection_empty() -> None:
    fake_collection = _install_fake_chromadb()
    fake_collection.count.return_value = 0

    from src.repositories.chroma_vector_repository import ChromaVectorRepository

    repo = ChromaVectorRepository(persist_path="/tmp/whatever")

    assert repo.query([0.1, 0.2]) == []
    fake_collection.query.assert_not_called()


def test_add_stores_embedding_with_data_id_metadata() -> None:
    fake_collection = _install_fake_chromadb()

    from src.repositories.chroma_vector_repository import ChromaVectorRepository

    repo = ChromaVectorRepository(persist_path="/tmp/whatever")

    repo.add(42, [0.1, 0.2])

    _, kwargs = fake_collection.add.call_args
    assert kwargs["embeddings"] == [[0.1, 0.2]]
    assert kwargs["metadatas"] == [{"data_id": 42}]
    assert len(kwargs["ids"]) == 1


def test_delete_removes_all_vectors_for_data_id() -> None:
    fake_collection = _install_fake_chromadb()

    from src.repositories.chroma_vector_repository import ChromaVectorRepository

    repo = ChromaVectorRepository(persist_path="/tmp/whatever")

    repo.delete(42)

    fake_collection.delete.assert_called_once_with(where={"data_id": 42})
