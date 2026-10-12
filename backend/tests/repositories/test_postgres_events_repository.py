from datetime import date, datetime

from src import config
from src.domain.event import EventQuery
from src.repositories.postgres_events_repository import PostgresEventsRepository, build_where


def test_where_has_whole_days_in_ufa_time_and_all_filters() -> None:
    where, params = build_where(
        EventQuery(date_from=date(2026, 10, 1), date_to=date(2026, 10, 31), topics=("Спорт и здоровье",),
                   formats=("Конкурс",), online=True, text="шахматы")
    )

    assert "starts_at >= $1" in where and "starts_at < $2" in where
    assert params[0] == datetime(2026, 10, 1, tzinfo=config.LOCAL_TZ)
    assert params[1] == datetime(2026, 11, 1, tzinfo=config.LOCAL_TZ)  # 31 октября - включительно
    assert params[2:] == ["%шахматы%", ["Спорт и здоровье"], ["Конкурс"], True]


def test_facets_ignore_topic_and_format_filters_so_counts_stay_useful() -> None:
    where, params = build_where(EventQuery(topics=("Спорт и здоровье",)), with_facet_filters=False)

    assert where == "" and params == []


async def test_find_orders_and_limits(fake_asyncpg_pool) -> None:
    fake_asyncpg_pool.fetch.return_value = []

    await PostgresEventsRepository("postgresql://x").find(EventQuery(newest_first=True, limit=10))

    sql, *params = fake_asyncpg_pool.fetch.call_args.args
    assert "ORDER BY starts_at DESC LIMIT $1" in sql and params == [10]
