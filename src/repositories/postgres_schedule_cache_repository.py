from __future__ import annotations

import json
import logging

from src.domain.schedule import DaySchedule, ScheduleLesson

logger = logging.getLogger(__name__)

_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS schedule_cache (
    group_name TEXT NOT NULL,
    schedule_date DATE NOT NULL,
    payload JSONB NOT NULL,
    cached_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (group_name, schedule_date)
)
"""

_SELECT_SQL = """
SELECT payload FROM schedule_cache
WHERE group_name = $1 AND schedule_date = $2 AND cached_at > now() - make_interval(secs => $3)
"""

_UPSERT_SQL = """
INSERT INTO schedule_cache (group_name, schedule_date, payload, cached_at)
VALUES ($1, $2, $3, now())
ON CONFLICT (group_name, schedule_date) DO UPDATE SET payload = EXCLUDED.payload, cached_at = now()
"""


def _day_schedule_to_payload(day_schedule: DaySchedule) -> str:
    return json.dumps(
        {
            "day_label": day_schedule.day_label,
            "lessons": [
                {"time": lesson.time, "subject": lesson.subject, "venue": lesson.venue}
                for lesson in day_schedule.lessons
            ],
        },
        ensure_ascii=False,
    )


def _payload_to_day_schedule(group: str, date: str, payload: dict) -> DaySchedule:
    return DaySchedule(
        group=group,
        date=date,
        day_label=payload["day_label"],
        lessons=[
            ScheduleLesson(time=item["time"], subject=item["subject"], venue=item.get("venue"))
            for item in payload["lessons"]
        ],
    )


class PostgresScheduleCacheRepository:
    """ScheduleCacheRepository поверх PostgreSQL: доступ через asyncpg, нативный SQL без ORM.

    TTL реализован прямо в SELECT (cached_at > now() - интервал) - протухшая запись просто
    не находится, как cache miss, без отдельной уборки/cron."""

    def __init__(self, dsn: str, ttl_seconds: int) -> None:
        self._dsn = dsn
        self._ttl_seconds = ttl_seconds
        self._pool = None

    async def _get_pool(self):
        if self._pool is None:
            import asyncpg

            logger.debug("ScheduleCache: создаю пул подключений")
            self._pool = await asyncpg.create_pool(self._dsn)
            await self._pool.execute(_CREATE_TABLE_SQL)
            logger.debug("ScheduleCache: таблица schedule_cache готова")
        return self._pool

    async def connect(self) -> None:
        await self._get_pool()

    async def get(self, group: str, date: str) -> DaySchedule | None:
        pool = await self._get_pool()
        logger.debug("ScheduleCache get: group=%s date=%s", group, date)
        row = await pool.fetchrow(_SELECT_SQL, group, date, self._ttl_seconds)
        if row is None:
            logger.debug("ScheduleCache get: miss (нет записи или протухла)")
            return None
        payload = json.loads(row["payload"])
        return _payload_to_day_schedule(group, date, payload)

    async def save(self, day_schedule: DaySchedule) -> None:
        pool = await self._get_pool()
        logger.debug("ScheduleCache save: group=%s date=%s", day_schedule.group, day_schedule.date)
        payload = _day_schedule_to_payload(day_schedule)
        await pool.execute(_UPSERT_SQL, day_schedule.group, day_schedule.date, payload)
