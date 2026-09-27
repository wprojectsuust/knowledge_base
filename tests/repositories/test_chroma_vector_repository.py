from unittest.mock import MagicMock

from src.repositories.chroma_vector_repository import ChromaVectorRepository


def _make_repo() -> ChromaVectorRepository:
    return ChromaVectorRepository(persist_path="/tmp/whatever")


def test_query_returns_data_ids_from_metadata(fake_chromadb: MagicMock) -> None:
    fake_chromadb.count.return_value = 2
    fake_chromadb.query.return_value = {"metadatas": [[{"data_id": 1}, {"data_id": 2}]]}

    repo = _make_repo()
    result = repo.query([0.1, 0.2], n_results=6)

    assert result == [1, 2]
    fake_chromadb.query.assert_called_once_with(query_embeddings=[[0.1, 0.2]], n_results=2, where=None)


def test_query_returns_empty_when_collection_empty(fake_chromadb: MagicMock) -> None:
    fake_chromadb.count.return_value = 0

    repo = _make_repo()

    assert repo.query([0.1, 0.2]) == []
    fake_chromadb.query.assert_not_called()


def test_add_stores_embedding_with_data_id_metadata(fake_chromadb: MagicMock) -> None:
    repo = _make_repo()

    repo.add(42, [0.1, 0.2])

    _, kwargs = fake_chromadb.add.call_args
    assert kwargs["embeddings"] == [[0.1, 0.2]]
    assert kwargs["metadatas"] == [{"data_id": 42}]
    assert len(kwargs["ids"]) == 1


def test_add_with_division_includes_it_in_metadata(fake_chromadb: MagicMock) -> None:
    repo = _make_repo()

    repo.add(42, [0.1, 0.2], division="iimrt")

    _, kwargs = fake_chromadb.add.call_args
    assert kwargs["metadatas"] == [{"data_id": 42, "division": "iimrt"}]


def test_query_with_division_filters_using_where_clause(fake_chromadb: MagicMock) -> None:
    fake_chromadb.count.return_value = 3
    fake_chromadb.query.return_value = {"metadatas": [[{"data_id": 5}]]}

    repo = _make_repo()
    result = repo.query([0.1, 0.2], n_results=6, division="iimrt")

    assert result == [5]
    fake_chromadb.query.assert_called_once_with(
        query_embeddings=[[0.1, 0.2]], n_results=3, where={"division": "iimrt"}
    )


def test_delete_removes_all_vectors_for_data_id(fake_chromadb: MagicMock) -> None:
    repo = _make_repo()

    repo.delete(42)

    fake_chromadb.delete.assert_called_once_with(where={"data_id": 42})
