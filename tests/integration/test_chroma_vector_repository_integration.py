"""Интеграционные тесты: реальный ChromaDB (embedded/persistent), никаких моков.

Не требует докера - chromadb пишет во временную директорию на диске. По умолчанию
pytest эти тесты пропускает (см. addopts в pyproject.toml) - запуск явный:
`pytest -m integration`.
"""

import pytest

from src.repositories.chroma_vector_repository import ChromaVectorRepository

pytestmark = pytest.mark.integration


def test_add_query_delete_roundtrip_against_real_chroma(tmp_path) -> None:
    repo = ChromaVectorRepository(persist_path=str(tmp_path), collection_name="integration-test")
    embedding = [0.1, 0.2, 0.3]

    repo.add(1, embedding)
    assert repo.query(embedding, n_results=1) == [1]

    repo.delete(1)
    assert repo.query(embedding, n_results=1) == []


def test_query_with_division_filter_against_real_chroma(tmp_path) -> None:
    repo = ChromaVectorRepository(persist_path=str(tmp_path), collection_name="integration-test-division")
    embedding = [0.1, 0.2, 0.3]

    repo.add(1, embedding, division="iimrt")
    repo.add(2, embedding, division="fti")

    assert repo.query(embedding, n_results=6, division="iimrt") == [1]
    assert set(repo.query(embedding, n_results=6)) == {1, 2}
