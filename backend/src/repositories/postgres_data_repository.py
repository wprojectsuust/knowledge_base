from __future__ import annotations

import logging

from src.domain.data import Data
from src.logging_utils import preview

logger = logging.getLogger(__name__)

_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS documents (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    source TEXT NOT NULL,
    content TEXT NOT NULL
)
"""

# CREATE TABLE IF NOT EXISTS не трогает уже существующую таблицу - для тех, кто успел
# развернуть БД до появления division, докатываем колонку отдельно и идемпотентно.
_ADD_DIVISION_COLUMN_SQL = "ALTER TABLE documents ADD COLUMN IF NOT EXISTS division TEXT NULL"

_SELECT_ONE_SQL = "SELECT id, source, content, division FROM documents WHERE id = $1"
_SELECT_MANY_SQL = "SELECT id, source, content, division FROM documents WHERE id = ANY($1::int[])"
_INSERT_SQL = "INSERT INTO documents (source, content, division) VALUES ($1, $2, $3) RETURNING id"
_DELETE_SQL = "DELETE FROM documents WHERE id = $1"
_EXISTING_SOURCES_SQL = "SELECT DISTINCT source FROM documents WHERE source = ANY($1::text[])"


class PostgresDataRepository:
    """DataRepository поверх PostgreSQL: доступ через asyncpg, нативный SQL без ORM.

    id генерируется базой (GENERATED ALWAYS AS IDENTITY) - save() всегда создаёт
    новую запись и возвращает присвоенный id, клиент id не передаёт."""

    def __init__(self, dsn: str) -> None:
        self._dsn = dsn
        self._pool = None

    async def _get_pool(self):
        if self._pool is None:
            import asyncpg

            logger.debug("PostgreSQL: создаю пул подключений")
            self._pool = await asyncpg.create_pool(self._dsn, min_size=1, max_size=10)
            await self._pool.execute(_CREATE_TABLE_SQL)
            await self._pool.execute(_ADD_DIVISION_COLUMN_SQL)
            logger.debug("PostgreSQL: таблица documents готова")
        return self._pool

    async def connect(self) -> None:
        await self._get_pool()

    @staticmethod
    def _row_to_data(row) -> Data:
        return Data(id=row["id"], source=row["source"], content=row["content"], division=row["division"])

    async def get(self, id_: int) -> Data | None:
        pool = await self._get_pool()
        logger.debug("SQL get: id=%s", id_)
        row = await pool.fetchrow(_SELECT_ONE_SQL, id_)
        logger.debug("SQL get: id=%s -> %s", id_, "найдено" if row is not None else "не найдено")
        return self._row_to_data(row) if row is not None else None

    async def get_many(self, ids: list[int]) -> list[Data]:
        if not ids:
            return []
        pool = await self._get_pool()
        logger.debug("SQL get_many: ids=%s", ids)
        rows = await pool.fetch(_SELECT_MANY_SQL, ids)
        logger.debug("SQL get_many: запрошено %d, найдено %d", len(ids), len(rows))
        return [self._row_to_data(row) for row in rows]

    async def save(self, data: Data) -> int:
        pool = await self._get_pool()
        logger.debug(
            "SQL save: source=%s division=%s content=%s", data.source, data.division, preview(data.content)
        )
        new_id = await pool.fetchval(_INSERT_SQL, data.source, data.content, data.division)
        logger.debug("SQL save: присвоен id=%s", new_id)
        return new_id

    async def delete(self, id_: int) -> None:
        pool = await self._get_pool()
        logger.debug("SQL delete: id=%s", id_)
        await pool.execute(_DELETE_SQL, id_)

    async def existing_sources(self, sources: list[str]) -> set[str]:
        if not sources:
            return set()
        pool = await self._get_pool()
        rows = await pool.fetch(_EXISTING_SOURCES_SQL, sources)
        logger.debug("SQL existing_sources: из %d уже есть %d", len(sources), len(rows))
        return {row["source"] for row in rows}
