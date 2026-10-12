from __future__ import annotations

import logging
from datetime import datetime, time, timedelta

from src import config
from src.domain.event import Event, EventQuery

logger = logging.getLogger(__name__)

_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS events (
    slug TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    starts_at TIMESTAMPTZ NOT NULL,
    url TEXT NOT NULL,
    image TEXT NULL,
    topic TEXT NOT NULL,
    format TEXT NOT NULL,
    online BOOLEAN NOT NULL DEFAULT false,
    imported_at TIMESTAMPTZ NOT NULL DEFAULT now()
)
"""
_CREATE_INDEX_SQL = "CREATE INDEX IF NOT EXISTS events_starts_at_idx ON events (starts_at)"
_KNOWN_SQL = "SELECT slug FROM events WHERE slug = ANY($1::text[])"
_UPSERT_SQL = """
INSERT INTO events (slug, title, starts_at, url, image, topic, format, online)
VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
ON CONFLICT (slug) DO UPDATE SET title = EXCLUDED.title, starts_at = EXCLUDED.starts_at,
    url = EXCLUDED.url, image = EXCLUDED.image, topic = EXCLUDED.topic, format = EXCLUDED.format,
    online = EXCLUDED.online
"""


def build_where(query: EventQuery, with_facet_filters: bool = True) -> tuple[str, list]:
    """WHERE и параметры для фильтров каталога. Даты - целые дни по Уфе, включительно.
    with_facet_filters=False - без тематики/формата/онлайна: для подсчёта фасетов."""
    clauses: list[str] = []
    params: list = []

    def param(value) -> str:
        params.append(value)
        return f"${len(params)}"

    if query.date_from is not None:
        clauses.append(f"starts_at >= {param(datetime.combine(query.date_from, time.min, config.LOCAL_TZ))}")
    if query.date_to is not None:
        end = datetime.combine(query.date_to + timedelta(days=1), time.min, config.LOCAL_TZ)
        clauses.append(f"starts_at < {param(end)}")
    if query.text.strip():
        clauses.append(f"title ILIKE {param('%' + query.text.strip() + '%')}")
    if with_facet_filters:
        if query.topics:
            clauses.append(f"topic = ANY({param(list(query.topics))}::text[])")
        if query.formats:
            clauses.append(f"format = ANY({param(list(query.formats))}::text[])")
        if query.online is not None:
            clauses.append(f"online = {param(query.online)}")
    return (" WHERE " + " AND ".join(clauses)) if clauses else "", params


class PostgresEventsRepository:
    """EventsStore поверх PostgreSQL: таблица events в той же базе, нативный SQL через asyncpg."""

    def __init__(self, dsn: str) -> None:
        self._dsn = dsn
        self._pool = None

    async def _get_pool(self):
        if self._pool is None:
            import asyncpg

            self._pool = await asyncpg.create_pool(self._dsn, min_size=1, max_size=5)
            await self._pool.execute(_CREATE_TABLE_SQL)
            await self._pool.execute(_CREATE_INDEX_SQL)
        return self._pool

    async def connect(self) -> None:
        await self._get_pool()

    async def known_slugs(self, slugs: list[str]) -> set[str]:
        if not slugs:
            return set()
        pool = await self._get_pool()
        return {row["slug"] for row in await pool.fetch(_KNOWN_SQL, slugs)}

    async def save_many(self, events: list[Event]) -> None:
        if not events:
            return
        pool = await self._get_pool()
        await pool.executemany(
            _UPSERT_SQL,
            [(e.slug, e.title, e.starts_at, e.url, e.image, e.topic, e.format, e.online) for e in events],
        )
        logger.info("Events: сохранено %d мероприятий", len(events))

    async def find(self, query: EventQuery) -> list[Event]:
        where, params = build_where(query)
        order = "DESC" if query.newest_first else "ASC"
        params.append(query.limit)
        sql = (
            "SELECT slug, title, starts_at, url, image, topic, format, online FROM events"
            f"{where} ORDER BY starts_at {order} LIMIT ${len(params)}"
        )
        pool = await self._get_pool()
        rows = await pool.fetch(sql, *params)
        return [Event(**dict(row)) for row in rows]

    async def facets(self, query: EventQuery) -> dict[str, dict[str, int]]:
        where, params = build_where(query, with_facet_filters=False)
        pool = await self._get_pool()
        result: dict[str, dict[str, int]] = {}
        for column in ("topic", "format"):
            rows = await pool.fetch(f"SELECT {column} AS value, count(*) AS n FROM events{where} GROUP BY {column}", *params)
            result[column] = {row["value"]: row["n"] for row in rows}
        return result
