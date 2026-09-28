from __future__ import annotations

import logging

from src.logging_utils import preview

logger = logging.getLogger(__name__)

_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS question_cache (
    question TEXT PRIMARY KEY,
    answer TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
)
"""

_SELECT_SQL = "SELECT answer FROM question_cache WHERE question = $1"
_CLEAR_SQL = "TRUNCATE question_cache"
_UPSERT_SQL = """
INSERT INTO question_cache (question, answer) VALUES ($1, $2)
ON CONFLICT (question) DO UPDATE SET answer = EXCLUDED.answer, created_at = now()
"""


class PostgresQuestionCacheRepository:
    """QuestionCacheRepository поверх PostgreSQL: доступ через asyncpg, нативный SQL без ORM.

    Отдельная таблица (question_cache) в той же базе, что и documents - не тянем
    отдельный сервис ради простого key-value кэша."""

    def __init__(self, dsn: str) -> None:
        self._dsn = dsn
        self._pool = None

    async def _get_pool(self):
        if self._pool is None:
            import asyncpg

            logger.debug("QuestionCache: создаю пул подключений")
            self._pool = await asyncpg.create_pool(self._dsn, min_size=1, max_size=10)
            await self._pool.execute(_CREATE_TABLE_SQL)
            logger.debug("QuestionCache: таблица question_cache готова")
        return self._pool

    async def connect(self) -> None:
        await self._get_pool()

    async def get(self, question: str) -> str | None:
        pool = await self._get_pool()
        logger.debug("QuestionCache get: question=%s", preview(question, 80))
        answer = await pool.fetchval(_SELECT_SQL, question)
        logger.debug("QuestionCache get: %s", "hit" if answer is not None else "miss")
        return answer

    async def save(self, question: str, answer: str) -> None:
        pool = await self._get_pool()
        logger.debug("QuestionCache save: question=%s", preview(question, 80))
        await pool.execute(_UPSERT_SQL, question, answer)

    async def clear(self) -> None:
        pool = await self._get_pool()
        logger.debug("QuestionCache clear: база знаний изменилась, сбрасываю кэш ответов")
        await pool.execute(_CLEAR_SQL)
