import datetime as dt
import json

from src.domain.schedule import DaySchedule, ScheduleLesson
from src.repositories.postgres_schedule_cache_repository import PostgresScheduleCacheRepository

sample_schedule = DaySchedule(
    group="1-1.1.1.-26А",
    date="2026-09-30",
    day_label="Среда 30.09.2026",
    lessons=[ScheduleLesson(time="09:00", subject="Матанализ", venue="ауд. 305")],
)


def _make_repo() -> PostgresScheduleCacheRepository:
    return PostgresScheduleCacheRepository(dsn="postgresql://uunit:uunit@localhost:5432/uunit", ttl_seconds=3600)


async def test_creates_schedule_cache_table_on_first_use(fake_asyncpg_pool) -> None:
    fake_asyncpg_pool.fetchrow.return_value = None
    repo = _make_repo()

    await repo.get("1-1.1.1.-26А", "2026-09-30")

    create_table_call = fake_asyncpg_pool.execute.call_args_list[0]
    assert "CREATE TABLE IF NOT EXISTS schedule_cache" in create_table_call.args[0]


async def test_get_returns_none_on_cache_miss(fake_asyncpg_pool) -> None:
    fake_asyncpg_pool.fetchrow.return_value = None
    repo = _make_repo()

    assert await repo.get("1-1.1.1.-26А", "2026-09-30") is None


async def test_get_deserializes_cached_payload(fake_asyncpg_pool) -> None:
    payload = json.dumps(
        {"day_label": "Среда 30.09.2026", "lessons": [{"time": "09:00", "subject": "Матанализ", "venue": "ауд. 305"}]}
    )
    fake_asyncpg_pool.fetchrow.return_value = {"payload": payload}
    repo = _make_repo()

    result = await repo.get("1-1.1.1.-26А", "2026-09-30")

    assert result == sample_schedule
    args, _ = fake_asyncpg_pool.fetchrow.call_args
    assert args[1] == "1-1.1.1.-26А"
    assert args[2] == dt.date(2026, 9, 30)
    assert args[3] == 3600


async def test_save_upserts_serialized_payload(fake_asyncpg_pool) -> None:
    repo = _make_repo()

    await repo.save(sample_schedule)

    args, _ = fake_asyncpg_pool.execute.call_args_list[-1]
    assert "INSERT INTO schedule_cache" in args[0]
    assert "ON CONFLICT (group_name, schedule_date) DO UPDATE" in args[0]
    assert args[1] == "1-1.1.1.-26А"
    assert args[2] == dt.date(2026, 9, 30)
    assert json.loads(args[3]) == {
        "day_label": "Среда 30.09.2026",
        "lessons": [{"time": "09:00", "subject": "Матанализ", "venue": "ауд. 305"}],
    }
