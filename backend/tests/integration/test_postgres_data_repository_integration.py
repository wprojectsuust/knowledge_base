"""Интеграционные тесты: реальный PostgreSQL, никаких моков.

Требует поднятой БД (см. docker-compose.yml / `make up`) и переменных POSTGRES_*
в окружении (см. .env.example). По умолчанию pytest эти тесты пропускает
(см. addopts в pyproject.toml) - запуск явный: `pytest -m integration`.
"""

import os

import pytest

from src.domain.data import Data
from src.repositories.postgres_data_repository import PostgresDataRepository

pytestmark = pytest.mark.integration


def _dsn() -> str:
    user = os.environ.get("POSTGRES_USER", "uunit")
    password = os.environ.get("POSTGRES_PASSWORD", "uunit")
    host = os.environ.get("POSTGRES_HOST", "localhost")
    port = os.environ.get("POSTGRES_PORT", "5432")
    database = os.environ.get("POSTGRES_DB", "uunit")
    return f"postgresql://{user}:{password}@{host}:{port}/{database}"


@pytest.fixture
async def repo() -> PostgresDataRepository:
    repository = PostgresDataRepository(dsn=_dsn())
    await repository.connect()
    return repository


async def test_save_get_and_delete_roundtrip_against_real_postgres(repo: PostgresDataRepository) -> None:
    data = Data(source="integration-test", content="Данные для интеграционного теста", division="iimrt")

    new_id = await repo.save(data)
    try:
        fetched = await repo.get(new_id)
        assert fetched == Data(
            id=new_id, source="integration-test", content="Данные для интеграционного теста", division="iimrt"
        )

        many = await repo.get_many([new_id, -1])
        assert many == [fetched]
    finally:
        await repo.delete(new_id)

    assert await repo.get(new_id) is None


async def test_get_returns_none_for_unknown_id(repo: PostgresDataRepository) -> None:
    assert await repo.get(-1) is None
