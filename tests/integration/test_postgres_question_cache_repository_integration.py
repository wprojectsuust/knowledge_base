"""Интеграционные тесты: реальный PostgreSQL, никаких моков.

Требует поднятой БД (см. docker-compose.yml / `make up`). По умолчанию pytest эти
тесты пропускает (см. addopts в pyproject.toml) - запуск явный: `pytest -m integration`.
"""

import os

import pytest

from src.repositories.postgres_question_cache_repository import PostgresQuestionCacheRepository

pytestmark = pytest.mark.integration


def _dsn() -> str:
    user = os.environ.get("POSTGRES_USER", "uunit")
    password = os.environ.get("POSTGRES_PASSWORD", "uunit")
    host = os.environ.get("POSTGRES_HOST", "localhost")
    port = os.environ.get("POSTGRES_PORT", "5432")
    database = os.environ.get("POSTGRES_DB", "uunit")
    return f"postgresql://{user}:{password}@{host}:{port}/{database}"


async def test_save_and_get_roundtrip_against_real_postgres() -> None:
    repo = PostgresQuestionCacheRepository(dsn=_dsn())
    await repo.connect()
    question = "интеграционный тестовый вопрос, которого не должно быть в базе"

    assert await repo.get(question) is None

    await repo.save(question, "интеграционный тестовый ответ")
    assert await repo.get(question) == "интеграционный тестовый ответ"

    await repo.save(question, "обновлённый ответ")
    assert await repo.get(question) == "обновлённый ответ"
