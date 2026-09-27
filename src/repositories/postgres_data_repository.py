from __future__ import annotations

from src.domain.data import Data

_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS documents (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    source TEXT NOT NULL,
    content TEXT NOT NULL
)
"""

_SELECT_ONE_SQL = "SELECT id, source, content FROM documents WHERE id = $1"
_SELECT_MANY_SQL = "SELECT id, source, content FROM documents WHERE id = ANY($1::int[])"
_INSERT_SQL = "INSERT INTO documents (source, content) VALUES ($1, $2) RETURNING id"
_DELETE_SQL = "DELETE FROM documents WHERE id = $1"


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

            self._pool = await asyncpg.create_pool(self._dsn)
            await self._pool.execute(_CREATE_TABLE_SQL)
        return self._pool

    @staticmethod
    def _row_to_data(row) -> Data:
        return Data(id=row["id"], source=row["source"], content=row["content"])

    async def get(self, id_: int) -> Data | None:
        pool = await self._get_pool()
        row = await pool.fetchrow(_SELECT_ONE_SQL, id_)
        return self._row_to_data(row) if row is not None else None

    async def get_many(self, ids: list[int]) -> list[Data]:
        if not ids:
            return []
        pool = await self._get_pool()
        rows = await pool.fetch(_SELECT_MANY_SQL, ids)
        return [self._row_to_data(row) for row in rows]

    async def save(self, data: Data) -> int:
        pool = await self._get_pool()
        return await pool.fetchval(_INSERT_SQL, data.source, data.content)

    async def delete(self, id_: int) -> None:
        pool = await self._get_pool()
        await pool.execute(_DELETE_SQL, id_)
